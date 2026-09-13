"""Persistent V12-equivalent interval planning with reverse-dependency updates.

Both update modes consume exactly the same sampled-row API. Incremental mode
invalidates every initialized query only at new states and observed ancestors
of an inserted row. No source prior or unobserved stochastic support is used.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import math
from time import perf_counter
from typing import Mapping

from .controlled_predictive_partial_v12 import (
    BoardProfile, FrozenPolicy, Key, RootInterval, SampleRow,
    _frontier, _solve, _terminal, profile, unknown_action_bounds,
)
from .controlled_predictive_quotient_v1 import Query


@dataclass
class IntervalCache:
    lower: dict[Key, float]
    upper: dict[Key, float]
    q_lower: dict[tuple[Key, str], float]
    q_upper: dict[tuple[Key, str], float]
    policy: dict[Key, str]
    dirty: set[Key] = field(default_factory=set)

    def clone(self) -> IntervalCache:
        return IntervalCache(dict(self.lower), dict(self.upper), dict(self.q_lower),
                             dict(self.q_upper), dict(self.policy), set(self.dirty))


class PlannerState:
    """A branch-local observed model, query cursor, and mutable interval caches."""

    def __init__(self, root: Key, queries: Mapping[str, Query], mode: str = "query_interval",
                 update_mode: str = "incremental"):
        if mode not in {"bfs", "query_interval"}:
            raise ValueError("V13 supports bfs or query_interval without a source prior")
        if update_mode not in {"incremental", "full_recompute"}:
            raise ValueError("unknown V13 interval update mode")
        if not queries or any(min(q.reward_weight, q.failure_penalty, q.goal_bonus) < 0 for q in queries.values()):
            raise ValueError("V13 intervals require nonempty nonnegative queries")
        started = perf_counter()
        self.root = root
        self.queries = dict(queries)
        self.mode = mode
        self.update_mode = update_mode
        self.work_counts: Counter = Counter()
        self.profiles: dict[Key, BoardProfile] = {root: profile(root, self.work_counts)}
        self.rows: dict[tuple[Key, str], SampleRow] = {}
        self.row_order: list[tuple[Key, str]] = []
        self.reverse_dependencies: dict[Key, set[Key]] = {}
        self.caches: dict[str, IntervalCache] = {}
        self.cursor = 0
        self.stop_reason: str | None = None
        self.engine_seconds = perf_counter() - started
        self.clone_seconds = 0.0

    def _observe_state(self, key: Key) -> None:
        if key in self.profiles:
            return
        self.profiles[key] = profile(key, self.work_counts)
        if self.update_mode == "incremental":
            for cache in self.caches.values():
                cache.dirty.add(key)
            self.work_counts["dirty_query_state_marks"] += len(self.caches)

    def observe_state(self, key: Key) -> None:
        """Reveal just the board supplied by execution, without acquiring a row."""
        started = perf_counter()
        self._observe_state(key)
        self.engine_seconds += perf_counter() - started

    def observe_row(self, key: Key, action: str, row: SampleRow) -> None:
        """Insert one new immutable sample row and mark its observed ancestors."""
        started = perf_counter()
        pair = (key, action)
        if pair in self.rows:
            raise ValueError("V13 inserts new rows; it does not resample an observed row")
        self._observe_state(key)
        if action not in self.profiles[key].legal_actions:
            raise ValueError("sampled action must be legal at its supplied board")
        if not row or any(successor[0] != key[0] - 1 for _, successor, _ in row):
            raise ValueError("a sample row must have successors one horizon below its parent")
        for _, successor, _ in row:
            self._observe_state(successor)
            if self.update_mode == "incremental":
                parents = self.reverse_dependencies.setdefault(successor, set())
                if key not in parents:
                    self.work_counts["reverse_dependency_edges_inserted"] += 1
                    parents.add(key)
        self.rows[pair] = row
        self.row_order.append(pair)
        self.work_counts["rows_acquired"] += 1
        if self.update_mode == "incremental":
            affected = {key}
            pending = [key]
            while pending:
                current = pending.pop()
                self.work_counts["reverse_dependency_states_visited"] += 1
                for parent in self.reverse_dependencies.get(current, ()):
                    if parent not in affected:
                        affected.add(parent)
                        pending.append(parent)
            for cache in self.caches.values():
                before = len(cache.dirty)
                cache.dirty.update(affected)
                self.work_counts["dirty_query_state_marks"] += len(cache.dirty) - before
        self.stop_reason = None
        self.engine_seconds += perf_counter() - started

    def _recompute_state(self, key: Key, query: Query, cache: IntervalCache) -> None:
        """Preserve V12 action iteration, fsum expressions, and tie ordering."""
        observed = self.profiles[key]
        work = self.work_counts
        work.update(interval_state_visits=1, incremental_state_recomputations=1)
        if observed.status != "ACTIVE":
            cache.lower[key] = cache.upper[key] = _terminal(observed.status, query)
            return
        for action in observed.legal_actions:
            pair = (key, action)
            work["interval_action_evaluations"] += 1
            if pair in self.rows:
                row = self.rows[pair]
                work.update(interval_sampled_row_reads=1, interval_sampled_successor_reads=len(row))
                cache.q_lower[pair] = math.fsum(weight * (query.reward_weight * reward + cache.lower[successor])
                                                for weight, successor, reward in row)
                cache.q_upper[pair] = math.fsum(weight * (query.reward_weight * reward + cache.upper[successor])
                                                for weight, successor, reward in row)
            else:
                work["interval_unknown_action_bounds"] += 1
                cache.q_lower[pair], cache.q_upper[pair] = unknown_action_bounds(key, observed, action, query)
        action = min(observed.legal_actions, key=lambda candidate: (-cache.q_lower[key, candidate], candidate))
        cache.policy[key] = action
        cache.lower[key] = cache.q_lower[key, action]
        cache.upper[key] = max(cache.q_upper[key, candidate] for candidate in observed.legal_actions)

    def _solve_query(self, query_name: str) -> IntervalCache:
        query = self.queries[query_name]
        if query_name not in self.caches or self.update_mode == "full_recompute":
            if query_name not in self.caches:
                self.work_counts["query_cache_initializations"] += 1
            self.work_counts["full_interval_recomputations"] += 1
            cache = IntervalCache(*_solve(self.profiles, self.rows, query, self.work_counts))
            self.caches[query_name] = cache
            return cache
        cache = self.caches[query_name]
        if not cache.dirty:
            self.work_counts["query_cache_hits"] += 1
            return cache
        self.work_counts["incremental_query_updates"] += 1
        for key in sorted(cache.dirty):
            self._recompute_state(key, query, cache)
        cache.dirty.clear()
        return cache

    def solve(self, query_name: str) -> IntervalCache:
        """Return the current internal cache; use freeze/clone for independence."""
        started = perf_counter()
        cache = self._solve_query(query_name)
        self.engine_seconds += perf_counter() - started
        return cache

    def select_row(self, key: Key, query_name: str) -> tuple[Key, str] | None:
        """Select a query-interval frontier at the currently revealed board."""
        started = perf_counter()
        self._observe_state(key)
        cache = self._solve_query(query_name)
        if cache.upper[key] - cache.lower[key] <= 1e-10:
            pair = None
        else:
            pair = _frontier(key, self.profiles, self.rows, cache.q_lower, cache.q_upper,
                             self.queries[query_name], self.work_counts, None, [0.0])
        self.engine_seconds += perf_counter() - started
        return pair

    def next_row(self) -> tuple[Key, str] | None:
        """Keep V12's original-root BFS or multi-query round-robin trajectory."""
        started = perf_counter()
        pair = None
        if self.mode == "bfs":
            frontier = [(key, action) for key in sorted(self.profiles, key=lambda value: (-value[0], value[1]))
                        for action in self.profiles[key].legal_actions if (key, action) not in self.rows]
            self.work_counts["breadth_first_state_scans"] += len(self.profiles)
            if frontier:
                pair = frontier[0]
            else:
                self.stop_reason = "NO_UNOBSERVED_ROWS"
        else:
            names = list(self.queries)
            for _ in names:
                name = names[self.cursor % len(names)]
                self.cursor += 1
                self.work_counts["query_round_robin_visits"] += 1
                cache = self._solve_query(name)
                if cache.upper[self.root] - cache.lower[self.root] <= 1e-10:
                    self.work_counts["converged_query_visits_skipped"] += 1
                    continue
                pair = _frontier(self.root, self.profiles, self.rows, cache.q_lower, cache.q_upper,
                                 self.queries[name], self.work_counts, None, [0.0])
                if pair is not None:
                    break
            if pair is None:
                self.stop_reason = "ALL_QUERIES_CONVERGED"
        self.engine_seconds += perf_counter() - started
        return pair

    def sample_next(self, provider) -> bool:
        """Acquire one selected row; provider time is separate from engine time."""
        pair = self.next_row()
        if pair is None:
            return False
        self.observe_row(*pair, provider.sample(*pair))
        return True

    def freeze(self, root: Key | None = None) -> tuple[FrozenPolicy, dict[str, RootInterval]]:
        """Copy all declared query policies and intervals at the requested root."""
        started = perf_counter()
        key = self.root if root is None else root
        self._observe_state(key)
        policies, intervals = {}, {}
        for name in self.queries:
            cache = self._solve_query(name)
            policies[name] = dict(cache.policy)
            intervals[name] = RootInterval(cache.lower[key], cache.upper[key], cache.policy.get(key))
        frozen = FrozenPolicy(policies, dict(self.profiles))
        self.work_counts.update(policy_snapshots_created=1,
                                snapshot_policy_entries_copied=sum(map(len, policies.values())),
                                snapshot_profile_entries_copied=len(self.profiles))
        self.engine_seconds += perf_counter() - started
        return frozen, intervals

    def clone(self) -> PlannerState:
        """Fork mutable state; immutable rows and profiles share their values."""
        started = perf_counter()
        child = object.__new__(type(self))
        child.root = self.root
        child.queries = dict(self.queries)
        child.mode = self.mode
        child.update_mode = self.update_mode
        child.work_counts = self.work_counts.copy()
        child.profiles = dict(self.profiles)
        child.rows = dict(self.rows)
        child.row_order = list(self.row_order)
        child.reverse_dependencies = {key: set(parents) for key, parents in self.reverse_dependencies.items()}
        child.caches = {name: cache.clone() for name, cache in self.caches.items()}
        child.cursor = self.cursor
        child.stop_reason = self.stop_reason
        child.work_counts.update(branch_clones=1, clone_profile_entries_copied=len(self.profiles),
                                 clone_row_entries_copied=len(self.rows),
                                 clone_cache_entries_copied=sum(len(mapping) for cache in self.caches.values()
                                                               for mapping in (cache.lower, cache.upper, cache.q_lower,
                                                                               cache.q_upper, cache.policy, cache.dirty)))
        child.clone_seconds = perf_counter() - started
        child.engine_seconds = self.engine_seconds + child.clone_seconds
        return child
