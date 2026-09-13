"""Exact history-tree evaluation of fixed and execution-adaptive V13 planners.

Only the evaluator owns the true environment. The planner receives one actual
board at each decision and obtains data exclusively through its row provider.
Sibling histories have independent mutable observations and query caches.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import math
from time import perf_counter
from typing import Callable, Mapping

from .controlled_predictive_incremental_v13 import PlannerState
from .controlled_predictive_partial_v12 import FrozenPolicy, Key, SampleRow
from .controlled_predictive_quotient_v1 import Query


class ExactEnvironment:
    """Evaluator-only true state status and selected-action transition lookup."""

    def __init__(self, statuses: Mapping[Key, str], rows: Mapping[tuple[Key, str], SampleRow]):
        self._statuses = statuses
        self._rows = rows

    @classmethod
    def from_closure(cls, closure):
        keys = {state: (closure.model.layers[state], board) for state, board in closure.boards.items()}
        return cls({keys[state]: status for state, status in closure.model.terminal.items()},
                   {(keys[state], action): tuple((outcome.probability, keys[outcome.next_state], outcome.reward)
                                                for outcome in row)
                    for (state, action), row in closure.model.rows.items()})

    def status(self, key: Key) -> str:
        return self._statuses[key]

    def row(self, key: Key, action: str) -> SampleRow:
        return self._rows[key, action]


def _key(key: Key) -> list:
    return [key[0], list(key[1])]


def _pair(pair: tuple[Key, str]) -> list:
    return [_key(pair[0]), pair[1]]


def _difference(after, before) -> Counter:
    return Counter({key: value - before.get(key, 0) for key, value in after.items()
                    if value != before.get(key, 0)})


@dataclass
class _LocalCost:
    rows: int = 0
    seconds: Counter = field(default_factory=Counter)
    work: Counter = field(default_factory=Counter)
    fallback: int = 0
    unresolved: int = 0
    unobserved_action: int = 0


@dataclass
class _BranchResult:
    trace: dict
    metrics: dict[str, float]
    expected_rows: float = 0.0
    maximum_rows: int = 0
    expected_seconds: Counter = field(default_factory=Counter)
    maximum_seconds: float = 0.0
    expected_work: Counter = field(default_factory=Counter)
    expected_events: Counter = field(default_factory=Counter)
    event_probabilities: Counter = field(default_factory=Counter)
    expected_decisions: float = 0.0
    maximum_decisions: int = 0


def _weighted(children, getter) -> float:
    return math.fsum(probability * getter(child) for probability, _, child in children)


def _weighted_counts(local: Mapping, children, attr: str) -> Counter:
    names = set(local)
    for _, _, child in children:
        names.update(getattr(child, attr))
    return Counter({name: local.get(name, 0) + _weighted(children, lambda child: getattr(child, attr).get(name, 0))
                    for name in sorted(names)})


class _HistoryEvaluator:
    def __init__(self, environment: ExactEnvironment, query: Query, decide, fork):
        self.environment, self.query = environment, query
        self.decide, self.fork = decide, fork
        self.work = Counter()
        self.environment_seconds = 0.0
        self.branch_clone_seconds = 0.0
        self.branch_clone_work = Counter()
        self.local_seconds = Counter()
        self.local_work = Counter()

    def walk(self, key: Key, state, is_root: bool = False) -> _BranchResult:
        self.work["history_nodes"] += 1
        status = self.environment.status(key)
        if status != "ACTIVE":
            self.work["terminal_history_nodes"] += 1
            failure, success = float(status == "LOST"), float(status == "WON")
            return _BranchResult({"key": _key(key), "status": status},
                                 {"reward": 0.0, "failure": failure, "success": success,
                                  "value": self.query.goal_bonus * success - self.query.failure_penalty * failure})
        self.work["decision_history_nodes"] += 1
        trace, local = self.decide(key, state, is_root)
        self.local_seconds.update(local.seconds)
        self.local_work.update(local.work)
        # This is the first true row access: the action has already been chosen.
        started = perf_counter()
        row = self.environment.row(key, trace["action"])
        self.environment_seconds += perf_counter() - started
        self.work.update(selected_true_row_lookups=1, true_outcome_entries_enumerated=len(row))
        children = []
        trace["children"] = []
        for probability, successor, reward in row:
            if probability == 0:
                continue
            if self.fork and self.environment.status(successor) == "ACTIVE":
                child_state = state.clone()
                self.branch_clone_seconds += child_state.clone_seconds
                self.branch_clone_work.update(_difference(child_state.work_counts, state.work_counts))
                self.work["counterfactual_branch_clones"] += 1
            else:
                child_state = state
            child = self.walk(successor, child_state)
            children.append((probability, reward, child))
            trace["children"].append({"probability": probability, "reward": reward, "node": child.trace})
        metrics = {
            "reward": math.fsum(p * (reward + child.metrics["reward"]) for p, reward, child in children),
            "failure": _weighted(children, lambda child: child.metrics["failure"]),
            "success": _weighted(children, lambda child: child.metrics["success"]),
        }
        metrics["value"] = (self.query.reward_weight * metrics["reward"]
                            - self.query.failure_penalty * metrics["failure"]
                            + self.query.goal_bonus * metrics["success"])
        events = {"fallback_calls": local.fallback, "unresolved_decisions": local.unresolved,
                  "unobserved_action_executions": local.unobserved_action}
        return _BranchResult(
            trace, metrics,
            local.rows + _weighted(children, lambda child: child.expected_rows),
            local.rows + max((child.maximum_rows for _, _, child in children), default=0),
            _weighted_counts(local.seconds, children, "expected_seconds"),
            math.fsum(local.seconds.values()) + max((child.maximum_seconds for _, _, child in children), default=0),
            _weighted_counts(local.work, children, "expected_work"),
            _weighted_counts(events, children, "expected_events"),
            Counter({name: 1.0 if value else _weighted(children, lambda child: child.event_probabilities.get(name, 0))
                     for name, value in events.items()}),
            1 + _weighted(children, lambda child: child.expected_decisions),
            1 + max((child.maximum_decisions for _, _, child in children), default=0),
        )


def _result(branch: _BranchResult, evaluator: _HistoryEvaluator, initial_rows: int, elapsed: float) -> dict:
    expected, maximum = initial_rows + branch.expected_rows, initial_rows + branch.maximum_rows
    return {
        "root_action": branch.trace.get("action"), "root_metrics": branch.metrics, "trace": branch.trace,
        "deployment": {
            "initial_rows": initial_rows,
            "expected_additional_rows": branch.expected_rows, "maximum_additional_rows": branch.maximum_rows,
            "expected_total_rows": expected, "maximum_total_rows": maximum,
            "expected_total_draws": 256 * expected, "maximum_total_draws": 256 * maximum,
            "expected_seconds_by_stage": dict(branch.expected_seconds),
            "expected_suffix_seconds": math.fsum(branch.expected_seconds.values()),
            "maximum_suffix_seconds": branch.maximum_seconds,
            "expected_suffix_work_counts": dict(branch.expected_work),
            "expected_events": dict(branch.expected_events), "event_probabilities": dict(branch.event_probabilities),
            "expected_decisions": branch.expected_decisions, "maximum_decisions": branch.maximum_decisions,
            "scope": "Per episode: initial rows included; warm construction time is attributed by the runner. Query initialization clone is charged; counterfactual sibling clones are excluded.",
        },
        "physical_audit": {
            "history_work_counts": dict(evaluator.work),
            "selected_environment_lookup_seconds": evaluator.environment_seconds,
            "counterfactual_branch_clone_seconds": evaluator.branch_clone_seconds,
            "counterfactual_branch_clone_work_counts": dict(evaluator.branch_clone_work),
            "all_history_decision_seconds_by_stage": dict(evaluator.local_seconds),
            "all_history_decision_work_counts": dict(evaluator.local_work),
            "whole_evaluation_seconds": elapsed,
            "scope": "Actual complete history enumeration; repeated requests on alternative histories remain physical work.",
        },
    }


def evaluate_execution(warm_state: PlannerState, provider, query_name: str, environment: ExactEnvironment,
                       *, mode: str = "online", total_row_cap: int = 128) -> dict:
    """Evaluate one query with fixed upfront or per-decision reserved acquisition.

    The independent provider records suffix calls only. The warm state and its
    cumulative counters are never mutated or repeatedly charged along branches.
    """
    if mode not in {"online", "upfront"}:
        raise ValueError("execution mode must be online or upfront")
    if total_row_cap < len(warm_state.rows):
        raise ValueError("total row cap must include all warm observations")
    query = warm_state.queries[query_name]
    started = perf_counter()
    state = warm_state.clone()
    initial_clone_seconds = state.clone_seconds
    initial_clone_work = _difference(state.work_counts, warm_state.work_counts)
    provider_before = Counter(provider.work_counts)
    provider_seconds_before = provider.provider_seconds
    frozen: FrozenPolicy | None = None
    frozen_rows = None
    frozen_bounds = None

    def decide(key: Key, current: PlannerState, is_root: bool):
        nonlocal frozen, frozen_rows, frozen_bounds
        cost = _LocalCost()
        if is_root:
            cost.seconds["query_initialization_clone"] += initial_clone_seconds
            cost.work.update(initial_clone_work)
        before_work = Counter(current.work_counts)
        before_rows = len(current.rows)
        requested, observations = [], []
        before_provider_work = Counter(provider.work_counts)
        quota = ((total_row_cap - before_rows) // key[0] if mode == "online"
                 else total_row_cap - before_rows if is_root else 0)
        if mode == "online" or is_root:
            t = perf_counter()
            current.observe_state(key)
            cost.seconds["actual_state_profile"] += perf_counter() - t
            for _ in range(quota):
                t = perf_counter()
                pair = current.select_row(key, query_name)
                cost.seconds["solve_and_frontier"] += perf_counter() - t
                if pair is None:
                    break
                t = perf_counter()
                sampled = provider.sample(*pair)
                cost.seconds["acquisition"] += perf_counter() - t
                t = perf_counter()
                current.observe_row(*pair, sampled)
                cost.seconds["sampled_model_update_and_profiles"] += perf_counter() - t
                requested.append(_pair(pair))
                observations.append({"row_key": _pair(pair), "outcomes":
                                     [[weight, _key(successor), reward] for weight, successor, reward in sampled]})
            t = perf_counter()
            cache = current.solve(query_name)
            cost.seconds["solve_and_frontier"] += perf_counter() - t
            lower, upper = cache.lower[key], cache.upper[key]
            if mode == "upfront":
                t = perf_counter()
                frozen = FrozenPolicy({query_name: dict(cache.policy)}, dict(current.profiles))
                frozen_rows = current.rows
                frozen_bounds = (dict(cache.lower), dict(cache.upper))
                cost.seconds["current_query_policy_freeze"] += perf_counter() - t
                cost.work.update(policy_entries_frozen=len(cache.policy), profile_entries_frozen=len(current.profiles),
                                 interval_entries_frozen=len(cache.lower) + len(cache.upper))
            t = perf_counter()
            action = cache.policy[key]
            cost.seconds["action"] += perf_counter() - t
            fallback = False
            unobserved = (key, action) not in current.rows
        else:
            # All post-root actions are from the one frozen query policy.
            before_fallback_work = Counter(frozen.work_counts)
            t = perf_counter()
            fallback = key not in frozen.profiles
            action = frozen.action(key, query_name)
            cost.seconds["action_and_fallback"] += perf_counter() - t
            cost.work.update(_difference(frozen.work_counts, before_fallback_work))
            unobserved = (key, action) not in frozen_rows
            lower = frozen_bounds[0].get(key)
            upper = frozen_bounds[1].get(key)
        cost.rows = len(current.rows) - before_rows
        cost.work.update(_difference(current.work_counts, before_work))
        cost.work.update({"provider_" + name: value for name, value in
                          _difference(provider.work_counts, before_provider_work).items()})
        cost.fallback = int(fallback)
        cost.unresolved = int(lower is None or upper - lower > 1e-10)
        cost.unobserved_action = int(unobserved)
        cost.work["execution_action_decisions"] += 1
        return {
            "key": _key(key), "action": action, "quota": quota,
            "rows_before": before_rows, "rows_after": len(current.rows), "requested_rows": requested,
            "observed_rows": observations,
            "lower": lower, "upper": upper,
            "decision_kind": "ONLINE_LOCAL_ACQUISITION" if mode == "online" else "UPFRONT_ROOT_ACQUISITION" if is_root else "FROZEN_POLICY",
            "unresolved": bool(cost.unresolved), "unobserved_action": bool(unobserved), "fallback": fallback,
        }, cost

    evaluator = _HistoryEvaluator(environment, query, decide, fork=mode == "online")
    branch = evaluator.walk(warm_state.root, state, is_root=True)
    result = _result(branch, evaluator, len(warm_state.rows), perf_counter() - started)
    result.update(mode=mode, update_mode=warm_state.update_mode, query_name=query_name, total_row_cap=total_row_cap,
                  initial_query_clone_seconds=initial_clone_seconds)
    result["physical_audit"].update(provider_counts=dict(_difference(provider.work_counts, provider_before)),
                                    provider_seconds=provider.provider_seconds - provider_seconds_before,
                                    initial_query_clone_seconds=initial_clone_seconds)
    return result


def evaluate_frozen_policy(root: Key, query: Query, action_callback: Callable[[Key], str | None],
                           environment: ExactEnvironment, *, known_rows=None, known_policy_keys=None,
                           initial_rows: int = 0) -> dict:
    """Evaluate a fixed root policy through the same exact history recursion."""
    started = perf_counter()

    def decide(key, unused_state, is_root):
        t = perf_counter()
        action = action_callback(key)
        seconds = perf_counter() - t
        fallback = known_policy_keys is not None and key not in known_policy_keys
        unobserved = known_rows is not None and (key, action) not in known_rows
        return {"key": _key(key), "action": action, "quota": 0,
                "rows_before": initial_rows, "rows_after": initial_rows, "requested_rows": [], "observed_rows": [],
                "lower": None, "upper": None, "decision_kind": "FROZEN_POLICY",
                "unresolved": None, "unobserved_action": unobserved, "fallback": fallback}, _LocalCost(
                    seconds=Counter(action_and_fallback=seconds), work=Counter(execution_action_decisions=1),
                    fallback=int(fallback), unobserved_action=int(unobserved))

    evaluator = _HistoryEvaluator(environment, query, decide, fork=False)
    branch = evaluator.walk(root, None, is_root=True)
    return _result(branch, evaluator, initial_rows, perf_counter() - started)
