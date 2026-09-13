"""V13 incremental intervals with the frozen V14 mass-conservation goal bound.

Merges conserve tile mass and at most four mass units arrive per move. An
ACTIVE board with mass + 4 * remaining_horizon below 2048 therefore cannot
reach the goal. This only removes the goal term from unknown-action upper
bounds; sampled rows, terminal values, and acquisition mechanics stay V13.
"""

from __future__ import annotations

import math
from typing import Mapping

from .controlled_predictive_incremental_v13 import IntervalCache, PlannerState
from .controlled_predictive_partial_v12 import BoardProfile, Key, _terminal
from .controlled_predictive_quotient_v1 import Query


def mass_bound_unknown_action_bounds(
    key: Key, observed: BoardProfile, action: str, query: Query,
) -> tuple[float, float]:
    """Use observed ACTIVE-board mass, without examining stochastic support."""
    remaining = key[0] - 1
    future_reward = (remaining * (observed.mass + 4) + 2 * remaining * (remaining - 1)) / 2048.0
    immediate = observed.reward(action)
    goal_upper = 0.0 if observed.mass + 4 * key[0] < 2048 else query.goal_bonus
    return (query.reward_weight * immediate - query.failure_penalty,
            query.reward_weight * (immediate + future_reward) + goal_upper)


class MassBoundPlannerState(PlannerState):
    """Incremental-only candidate; inherited branch clones preserve this type."""

    def __init__(self, root: Key, queries: Mapping[str, Query], mode: str = "query_interval",
                 update_mode: str = "incremental"):
        if update_mode != "incremental":
            raise ValueError("V14 mass-bound planning supports only incremental updates")
        super().__init__(root, queries, mode, update_mode)

    def _update_state(self, key: Key, query: Query, cache: IntervalCache) -> None:
        """One numerical path for both first initialization and dirty updates."""
        observed = self.profiles[key]
        work = self.work_counts
        work["interval_state_visits"] += 1
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
                work["mass_bound_unknown_action_checks"] += 1
                if query.goal_bonus > 0 and observed.mass + 4 * key[0] < 2048:
                    work["mass_bound_nonzero_goal_terms_removed"] += 1
                cache.q_lower[pair], cache.q_upper[pair] = mass_bound_unknown_action_bounds(
                    key, observed, action, query,
                )
        action = min(observed.legal_actions, key=lambda candidate: (-cache.q_lower[key, candidate], candidate))
        cache.policy[key] = action
        cache.lower[key] = cache.q_lower[key, action]
        cache.upper[key] = max(cache.q_upper[key, candidate] for candidate in observed.legal_actions)

    def _recompute_state(self, key: Key, query: Query, cache: IntervalCache) -> None:
        self.work_counts["incremental_state_recomputations"] += 1
        self._update_state(key, query, cache)

    def _solve_query(self, query_name: str) -> IntervalCache:
        if query_name in self.caches:
            return super()._solve_query(query_name)
        query = self.queries[query_name]
        self.work_counts.update(query_cache_initializations=1, full_interval_recomputations=1)
        cache = IntervalCache({}, {}, {}, {}, {})
        for key in sorted(self.profiles):
            self._update_state(key, query, cache)
        self.caches[query_name] = cache
        return cache
