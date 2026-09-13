"""Budgeted row observations and partial-model interval planning for V12.

Only RowSampleProvider knows stochastic support. The planner sees sampled rows,
profiles their observed boards, and shares those observations across queries.
Intervals concern the sampled completion, not confidence in the true kernel.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import math
import random
from time import perf_counter
from typing import Callable, Mapping

from acfqp.domains.standard_2048 import (
    GOAL_RANK, Swipe2048Action, Swipe2048State, Swipe2048Status,
    step_v1 as _step_v1, swipe_board_v1, validate_board_v1,
)
from .controlled_predictive_quotient_v1 import Query


Key = tuple[int, tuple[int, ...]]
SampleRow = tuple[tuple[float, Key, float], ...]
Prior = Callable[[Key, Query], Mapping[str, float]]
ACTIONS = tuple(sorted(action.value for action in Swipe2048Action))
_ACTION_ENUMS = tuple(Swipe2048Action(action) for action in ACTIONS)
_BOARD_RADIX = 12 ** 16


def row_seed(seed: int, key: Key, action: str) -> int:
    """Injectively encode the frozen supported seed/horizon/action/board domain."""
    horizon, board = key
    if type(seed) is not int or seed < 0 or type(horizon) is not int or not 1 <= horizon <= 3:
        raise ValueError("row sampling requires a nonnegative seed and horizon in 1..3")
    validate_board_v1(board)
    if max(board) >= GOAL_RANK:
        raise ValueError("row sampling requires an ACTIVE board below the goal rank")
    return (seed * (_BOARD_RADIX * 16) + (horizon * 4 + ACTIONS.index(action)) * _BOARD_RADIX
            + sum(rank * 12 ** index for index, rank in enumerate(board)))


class RowSampleProvider:
    """Generate only the requested row with an independent deterministic stream."""

    def __init__(self, seed: int, samples_per_row: int = 256):
        if samples_per_row != 256:
            raise ValueError("V12 freezes 256 observations per requested row")
        self.seed = seed
        self.samples_per_row = samples_per_row
        self.work_counts: Counter = Counter()
        self.provider_seconds = 0.0

    def sample(self, key: Key, action: str) -> SampleRow:
        started = perf_counter()
        stream_seed = row_seed(self.seed, key, action)
        self.work_counts["row_requests"] += 1
        support = _step_v1(Swipe2048State(key[1], Swipe2048Status.ACTIVE), Swipe2048Action(action))
        self.work_counts.update(exact_transition_row_calls=1, support_entries_enumerated=len(support))
        sampled = random.Random(stream_seed).choices(
            support, weights=[float(outcome.probability) for outcome in support], k=self.samples_per_row,
        )
        counts = Counter(((key[0] - 1, outcome.next_state.board), outcome.merge_score / 2048.0)
                         for outcome in sampled)
        result = tuple((count / self.samples_per_row, successor, reward)
                       for (successor, reward), count in sorted(counts.items()))
        self.work_counts.update(physical_draws=self.samples_per_row,
                                sampled_successor_entries_returned=len(result))
        self.provider_seconds += perf_counter() - started
        return result


@dataclass(frozen=True)
class BoardProfile:
    status: str
    legal_actions: tuple[str, ...]
    immediate_rewards: tuple[tuple[str, float], ...]
    mass: int

    def reward(self, action: str) -> float:
        return next(reward for candidate, reward in self.immediate_rewards if candidate == action)


def profile(key: Key, work: Counter) -> BoardProfile:
    """Use only deterministic board mechanics, including for horizon-zero loss."""
    horizon, board = key
    validate_board_v1(board)
    if type(horizon) is not int or not 0 <= horizon <= 3:
        raise ValueError("V12 supports horizons 0..3")
    work.update(states_profiled=1, profile_board_validations=1, board_maximum_scans=1)
    maximum = max(board)
    if maximum >= GOAL_RANK:
        work["terminal_states_profiled"] += 1
        return BoardProfile("WON", (), (), 0)
    legal = []
    rewards = []
    for action, enum in zip(ACTIONS, _ACTION_ENUMS):
        _, reward, changed = swipe_board_v1(board, enum)
        work["deterministic_swipe_calls"] += 1
        if changed:
            if horizon == 0:
                work["terminal_states_profiled"] += 1
                return BoardProfile("CUTOFF", (), (), 0)
            legal.append(action)
            rewards.append((action, reward / 2048.0))
    if not legal:
        work["terminal_states_profiled"] += 1
        return BoardProfile("LOST", (), (), 0)
    work.update(active_states_profiled=1, board_mass_scans=1)
    return BoardProfile("ACTIVE", tuple(legal), tuple(rewards), sum(1 << rank for rank in board if rank))


def unknown_action_bounds(key: Key, observed: BoardProfile, action: str, query: Query) -> tuple[float, float]:
    """Bound an unobserved row by deterministic reward and remaining board mass."""
    remaining = key[0] - 1
    future_reward = (remaining * (observed.mass + 4) + 2 * remaining * (remaining - 1)) / 2048.0
    immediate = observed.reward(action)
    return (query.reward_weight * immediate - query.failure_penalty,
            query.reward_weight * (immediate + future_reward) + query.goal_bonus)


def _terminal(status: str, query: Query) -> float:
    return query.goal_bonus if status == "WON" else -query.failure_penalty if status == "LOST" else 0.0


@dataclass(frozen=True)
class RootInterval:
    lower: float
    upper: float
    action: str | None


@dataclass
class FrozenPolicy:
    policies: dict[str, dict[Key, str]]
    profiles: dict[Key, BoardProfile]
    work_counts: Counter = field(default_factory=Counter)
    fallback_seconds: float = 0.0

    def action(self, key: Key, query_name: str) -> str | None:
        self.work_counts["policy_action_calls"] += 1
        policy = self.policies[query_name]
        if key in policy:
            self.work_counts["known_policy_action_calls"] += 1
            return policy[key]
        if key in self.profiles:
            return None  # A known terminal state has no action.
        started = perf_counter()
        self.work_counts["fallback_calls"] += 1
        observed = profile(key, self.work_counts)
        action = (min(observed.legal_actions, key=lambda candidate: (-observed.reward(candidate), candidate))
                  if observed.status == "ACTIVE" else None)
        self.fallback_seconds += perf_counter() - started
        return action


@dataclass(frozen=True)
class PartialCheckpoint:
    budget: int
    known_rows: dict[tuple[Key, str], SampleRow]
    profiles: dict[Key, BoardProfile]
    frozen_policy: FrozenPolicy
    root_intervals: dict[str, RootInterval]
    work_counts: dict[str, int]
    provider_counts: dict[str, int]
    prior_diagnostics: dict
    provider_seconds: float
    prior_seconds: float
    checkpoint_copy_seconds: float
    elapsed_seconds: float
    stop_reason: str


def _solve(profiles: Mapping[Key, BoardProfile], rows: Mapping[tuple[Key, str], SampleRow],
           query: Query, work: Counter):
    lower, upper, q_lower, q_upper, policy = {}, {}, {}, {}, {}
    for key in sorted(profiles):
        observed = profiles[key]
        work["interval_state_visits"] += 1
        if observed.status != "ACTIVE":
            lower[key] = upper[key] = _terminal(observed.status, query)
            continue
        for action in observed.legal_actions:
            pair = (key, action)
            work["interval_action_evaluations"] += 1
            if pair in rows:
                row = rows[pair]
                work.update(interval_sampled_row_reads=1, interval_sampled_successor_reads=len(row))
                q_lower[pair] = math.fsum(weight * (query.reward_weight * reward + lower[successor])
                                         for weight, successor, reward in row)
                q_upper[pair] = math.fsum(weight * (query.reward_weight * reward + upper[successor])
                                         for weight, successor, reward in row)
            else:
                work["interval_unknown_action_bounds"] += 1
                q_lower[pair], q_upper[pair] = unknown_action_bounds(key, observed, action, query)
        action = min(observed.legal_actions, key=lambda candidate: (-q_lower[key, candidate], candidate))
        policy[key] = action
        lower[key] = q_lower[key, action]
        upper[key] = max(q_upper[key, candidate] for candidate in observed.legal_actions)
    return lower, upper, q_lower, q_upper, policy


def _frontier(root: Key, profiles: Mapping[Key, BoardProfile], rows: Mapping[tuple[Key, str], SampleRow],
              q_lower, q_upper, query: Query, work: Counter, prior: Prior | None,
              prior_elapsed: list[float]) -> tuple[Key, str] | None:
    prior_values: dict[Key, Mapping[str, float]] = {}

    def values(key: Key) -> Mapping[str, float]:
        if key not in prior_values:
            started = perf_counter()
            prior_values[key] = prior(key, query) if prior is not None else {}
            prior_elapsed[0] += perf_counter() - started
            work["prior_calls"] += int(prior is not None)
        return prior_values[key]

    reach = defaultdict(float, {root: 1.0})
    candidates = []
    for key in sorted(profiles, key=lambda value: (-value[0], value[1])):
        probability = reach[key]
        observed = profiles[key]
        if probability == 0 or observed.status != "ACTIVE":
            continue
        work["frontier_reachable_state_visits"] += 1
        best = max(q_upper[key, action] for action in observed.legal_actions)
        tied = [action for action in observed.legal_actions if q_upper[key, action] == best]
        action = (min(tied, key=lambda candidate: (-values(key).get(candidate, 0.0), candidate))
                  if prior is not None and len(tied) > 1 else tied[0])
        pair = (key, action)
        if pair in rows:
            work["frontier_sampled_row_visits"] += 1
            for weight, successor, _ in rows[pair]:
                work["frontier_sampled_successor_visits"] += 1
                reach[successor] += probability * weight
        else:
            work["frontier_unknown_action_candidates"] += 1
            candidates.append((probability * (q_upper[pair] - q_lower[pair]), pair))
    if not candidates:
        return None
    highest = max(score for score, _ in candidates)
    tied = [pair for score, pair in candidates if score == highest]
    if prior is not None and len(tied) > 1:
        return min(tied, key=lambda pair: (-values(pair[0]).get(pair[1], 0.0), pair))
    return min(tied)


def run_partial(root: Key, provider: RowSampleProvider, queries: Mapping[str, Query],
                budgets: tuple[int, ...] = (8, 32, 128), mode: str = "query_interval",
                prior: Prior | None = None) -> tuple[PartialCheckpoint, ...]:
    """Share one observed row set, freezing independent snapshots at each budget."""
    if mode not in {"query_interval", "bfs", "source_priority", "shuffled_source_priority"}:
        raise ValueError("unknown V12 acquisition mode")
    if not queries or any(min(q.reward_weight, q.failure_penalty, q.goal_bonus) < 0 for q in queries.values()):
        raise ValueError("V12 intervals require nonempty nonnegative queries")
    if not budgets or tuple(sorted(set(budgets))) != tuple(budgets) or budgets[0] < 0:
        raise ValueError("checkpoint budgets must be increasing nonnegative row counts")
    if mode in {"source_priority", "shuffled_source_priority"} and prior is None:
        raise ValueError("source-priority acquisition requires a source callback")
    started = perf_counter()
    work: Counter = Counter()
    profiles = {root: profile(root, work)}
    rows: dict[tuple[Key, str], SampleRow] = {}
    query_names = list(queries)
    cursor = 0
    checkpoints = []
    prior_elapsed = [0.0]
    checkpoint_copy_seconds = 0.0
    stopped = None
    search_prior = prior if mode in {"source_priority", "shuffled_source_priority"} else None

    for budget in budgets:
        while len(rows) < budget and stopped is None:
            if mode == "bfs":
                frontier = [(key, action) for key in sorted(profiles, key=lambda value: (-value[0], value[1]))
                            for action in profiles[key].legal_actions if (key, action) not in rows]
                work["breadth_first_state_scans"] += len(profiles)
                pair = frontier[0] if frontier else None
                if pair is None:
                    stopped = "NO_UNOBSERVED_ROWS"
                    break
            else:
                pair = None
                for _ in query_names:
                    name = query_names[cursor % len(query_names)]
                    cursor += 1
                    work["query_round_robin_visits"] += 1
                    lower, upper, q_lower, q_upper, _ = _solve(profiles, rows, queries[name], work)
                    if upper[root] - lower[root] <= 1e-10:
                        work["converged_query_visits_skipped"] += 1
                        continue
                    pair = _frontier(root, profiles, rows, q_lower, q_upper, queries[name], work,
                                     search_prior, prior_elapsed)
                    if pair is not None:
                        break
                if pair is None:
                    stopped = "ALL_QUERIES_CONVERGED"
                    break
            sampled = provider.sample(*pair)
            rows[pair] = sampled
            work["rows_acquired"] += 1
            for _, successor, _ in sampled:
                if successor not in profiles:
                    profiles[successor] = profile(successor, work)

        root_intervals = {}
        policies = {}
        for name in query_names:
            lower, upper, _, _, policies[name] = _solve(profiles, rows, queries[name], work)
            root_intervals[name] = RootInterval(lower[root], upper[root], policies[name].get(root))
        copy_started = perf_counter()
        snapshot_rows = dict(rows)
        snapshot_profiles = dict(profiles)
        frozen = FrozenPolicy(policies, snapshot_profiles)
        work.update(checkpoints_created=1, checkpoint_row_entries_copied=len(rows),
                    checkpoint_profile_entries_copied=len(profiles),
                    checkpoint_policy_entries_frozen=sum(map(len, policies.values())))
        provider_counts = dict(provider.work_counts)
        prior_diagnostics = dict(prior.diagnostics()) if prior is not None and hasattr(prior, "diagnostics") else {}
        snapshot_work = dict(work)
        checkpoint_copy_seconds += perf_counter() - copy_started
        checkpoints.append(PartialCheckpoint(
            budget, snapshot_rows, snapshot_profiles, frozen, root_intervals, snapshot_work,
            provider_counts, prior_diagnostics, provider.provider_seconds, prior_elapsed[0], checkpoint_copy_seconds,
            perf_counter() - started, stopped or "ROW_BUDGET",
        ))
    return tuple(checkpoints)
