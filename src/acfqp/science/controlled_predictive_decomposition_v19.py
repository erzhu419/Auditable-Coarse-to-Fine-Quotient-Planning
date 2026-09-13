"""Evaluator-only decomposition of frozen, observed H2 action estimates."""

from collections import Counter
from dataclasses import asdict, dataclass
import math
from time import perf_counter

from .controlled_predictive_partial_v12 import _terminal


TOLERANCE = 1e-10
ACTIONS = ("LEFT", "RIGHT")
TERMS = ("q_hat", "q_star", "q_hat_exact_continuation", "A_transition_error",
         "continuation_error", "B_continuation_estimation_error",
         "C_continuation_policy_loss", "total_error", "residual_A_plus_continuation",
         "residual_B_plus_C", "residual_A_plus_B_plus_C")


class UnsupportedSnapshot(ValueError):
    """The retained snapshot does not contain the declared H2/H1 policy."""


def _key(key):
    return [key[0], list(key[1])]


def _delta(after, before):
    return {key: value - before.get(key, 0) for key, value in after.items()
            if value != before.get(key, 0)}


@dataclass
class _ExactSolution:
    values: dict
    q_values: dict


class ExactOracle:
    """A separate ground model and exact DP cache; never a planner input."""

    def __init__(self, statuses, rows):
        started = perf_counter()
        self.statuses = dict(statuses)
        self.rows = dict(rows)
        actions = {}
        for key, action in self.rows:
            actions.setdefault(key, []).append(action)
        self.actions = {key: tuple(value) for key, value in actions.items()}
        self.solutions = {}
        self.work_counts = Counter(ground_states_indexed=len(statuses),
                                   ground_rows_indexed=len(rows),
                                   ground_support_entries_indexed=sum(map(len, rows.values())))
        self.seconds_by_stage = Counter(oracle_construction=perf_counter() - started)

    @classmethod
    def from_closure(cls, closure):
        started = perf_counter()
        keys = {state: (closure.model.layers[state], board) for state, board in closure.boards.items()}
        result = cls(
            {keys[state]: status for state, status in closure.model.terminal.items()},
            {(keys[state], action): tuple((outcome.probability, keys[outcome.next_state], outcome.reward)
                                         for outcome in row)
             for (state, action), row in closure.model.rows.items()})
        result.seconds_by_stage["oracle_construction"] = perf_counter() - started
        return result

    def solution(self, query):
        started = perf_counter()
        if query in self.solutions:
            self.work_counts["exact_query_cache_hits"] += 1
            self.seconds_by_stage["exact_query_cache_lookup"] += perf_counter() - started
            return self.solutions[query]
        self.work_counts["exact_query_cache_initializations"] += 1
        values, q_values = {}, {}
        for key in sorted(self.statuses):
            self.work_counts["exact_dp_state_visits"] += 1
            status = self.statuses[key]
            if status != "ACTIVE":
                values[key] = _terminal(status, query)
                continue
            for action in self.actions[key]:
                row = self.rows[key, action]
                self.work_counts.update(exact_dp_row_reads=1, exact_dp_support_reads=len(row))
                q_values[key, action] = math.fsum(
                    weight * (query.reward_weight * reward + values[successor])
                    for weight, successor, reward in row)
            values[key] = max(q_values[key, action] for action in self.actions[key])
        result = _ExactSolution(values, q_values)
        self.solutions[query] = result
        self.seconds_by_stage["exact_dynamic_programming"] += perf_counter() - started
        return result

    def accounting(self):
        return {"work_counts": dict(self.work_counts), "seconds_by_stage": dict(self.seconds_by_stage),
                "total_seconds": math.fsum(self.seconds_by_stage.values()),
                "scope": "Evaluator-only oracle indexing, exact DP and query-cache access. Source closure construction is accounted separately by the caller."}


def evaluate_snapshot(state, query_name, target_key, exact_oracle):
    """Decompose Qhat-Qstar without acquiring data or modifying the snapshot.

    H1 continuation actions come only from this snapshot's empirical policy.
    A selected action may itself be unobserved; that fact and its structural
    interval are reported, rather than replacing it with an oracle action.
    """
    started = perf_counter()
    if target_key[0] != 2 or target_key not in state.profiles:
        raise UnsupportedSnapshot("The declared target must be a retained H2 state")
    if state.profiles[target_key].status != "ACTIVE":
        raise UnsupportedSnapshot("The declared target must be ACTIVE")
    if any((target_key, action) not in state.rows for action in ACTIONS):
        raise UnsupportedSnapshot("Both declared LEFT/RIGHT actions must have retained observations")
    oracle_work_before = Counter(exact_oracle.work_counts)
    oracle_seconds_before = Counter(exact_oracle.seconds_by_stage)
    clone_started = perf_counter()
    snapshot = state.clone()
    cache = snapshot.solve(query_name)
    clone_solve_seconds = perf_counter() - clone_started
    query = snapshot.queries[query_name]
    truth = exact_oracle.solution(query)
    if target_key not in exact_oracle.actions or any(action not in exact_oracle.actions[target_key] for action in ACTIONS):
        raise UnsupportedSnapshot("The ground model lacks one declared target action")
    decomposition_started = perf_counter()
    action_results = {}
    for action in ACTIONS:
        pair = target_key, action
        children = []
        for weight, successor, reward in snapshot.rows[pair]:
            if successor not in snapshot.profiles or successor not in truth.values:
                raise UnsupportedSnapshot("An empirical successor lacks its retained profile or ground value")
            observed = snapshot.profiles[successor]
            v_hat, v_star = cache.lower[successor], truth.values[successor]
            exact_oracle.work_counts["diagnostic_exact_value_lookups"] += 1
            chosen = None
            chosen_observed = None
            if observed.status == "ACTIVE":
                if successor[0] != 1 or successor not in cache.policy:
                    raise UnsupportedSnapshot("Active continuations must have a retained H1 policy")
                chosen = cache.policy[successor]
                if (successor, chosen) not in truth.q_values:
                    raise UnsupportedSnapshot("The retained H1 action is absent from the ground model")
                v_pi = truth.q_values[successor, chosen]
                exact_oracle.work_counts["diagnostic_exact_q_lookups"] += 1
                chosen_observed = (successor, chosen) in snapshot.rows
            else:
                v_pi = _terminal(observed.status, query)
            lower, upper = cache.lower[successor], cache.upper[successor]
            children.append({
                "key": _key(successor), "empirical_probability": weight, "immediate_reward": reward,
                "status": observed.status, "selected_action": chosen,
                "selected_action_observed": chosen_observed,
                "selected_action_batch_count": (snapshot.batch_counts.get((successor, chosen), 0)
                    if hasattr(snapshot, "batch_counts") else int(chosen_observed)) if chosen is not None else None,
                "empirical_lower": lower, "empirical_upper": upper,
                "empirical_interval_closed": upper - lower <= TOLERANCE,
                "v_hat": v_hat, "v_pi": v_pi, "v_star": v_star,
                "B_value_estimation_error": v_hat - v_pi,
                "C_policy_loss": v_pi - v_star,
                "weighted_B": weight * (v_hat - v_pi),
                "weighted_C": weight * (v_pi - v_star),
            })
        q_hat, q_star = cache.q_lower[pair], truth.q_values[pair]
        exact_oracle.work_counts["diagnostic_exact_q_lookups"] += 1
        q_hat_exact = math.fsum(child["empirical_probability"] * (
            query.reward_weight * child["immediate_reward"] + child["v_star"]) for child in children)
        transition = q_hat_exact - q_star
        continuation = math.fsum(child["empirical_probability"] * (child["v_hat"] - child["v_star"])
                                 for child in children)
        estimate = math.fsum(child["weighted_B"] for child in children)
        policy = math.fsum(child["weighted_C"] for child in children)
        total = q_hat - q_star
        action_results[action] = {
            "q_hat": q_hat, "q_star": q_star, "q_hat_exact_continuation": q_hat_exact,
            "A_transition_error": transition, "continuation_error": continuation,
            "B_continuation_estimation_error": estimate, "C_continuation_policy_loss": policy,
            "total_error": total,
            "residual_A_plus_continuation": total - math.fsum((transition, continuation)),
            "residual_B_plus_C": continuation - math.fsum((estimate, policy)),
            "residual_A_plus_B_plus_C": total - math.fsum((transition, estimate, policy)),
            "batch_count": snapshot.batch_counts[pair] if hasattr(snapshot, "batch_counts") else 1,
            "children": children,
        }
    margin = {term: action_results["LEFT"][term] - action_results["RIGHT"][term] for term in TERMS}
    best = truth.values[target_key]
    optimal = sorted(action for action in exact_oracle.actions[target_key]
                     if best - truth.q_values[target_key, action] <= TOLERANCE)
    decomposition_seconds = perf_counter() - decomposition_started
    residuals = [abs(row[name]) for row in (*action_results.values(), margin)
                 for name in TERMS if name.startswith("residual_")]
    return {
        "target_key": _key(target_key), "query_name": query_name, "query": asdict(query),
        "empirical": {"selected_action": cache.policy[target_key], "lower": cache.lower[target_key],
                      "upper": cache.upper[target_key],
                      "closed": cache.upper[target_key] - cache.lower[target_key] <= TOLERANCE},
        "local_true_optimal_actions": optimal, "actions": action_results, "left_minus_right": margin,
        "identities_pass": max(residuals) <= TOLERANCE,
        "maximum_absolute_identity_residual": max(residuals),
        "accounting": {"snapshot_clone_and_solve_seconds": clone_solve_seconds,
                       "snapshot_clone_and_solve_work": _delta(snapshot.work_counts, state.work_counts),
                       "oracle_work": _delta(exact_oracle.work_counts, oracle_work_before),
                       "oracle_seconds_by_stage": _delta(exact_oracle.seconds_by_stage, oracle_seconds_before),
                       "decomposition_seconds": decomposition_seconds,
                       "whole_evaluation_seconds": perf_counter() - started,
                       "scope": "Whole evaluation includes the diagnostic clone/solve, oracle query work and decomposition. Times are nested and must not be added again."},
        "scope": "Frozen H2 LEFT/RIGHT estimates only. Vpi evaluates the snapshot-selected H1 action with exact transitions and terminal values; it includes no later online acquisition. B includes any retained structural bound when that chosen H1 row is unobserved. C is sampled-support policy loss and is nonpositive, but its LEFT-minus-RIGHT difference can have either sign. Exact truth is evaluator-only; no snapshot mutation or new planning observations.",
    }
