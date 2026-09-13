"""Exact local updates of V16 gap scores, shared with V15 balanced selection."""

from dataclasses import dataclass
import math
from time import perf_counter

from .controlled_predictive_gap_v16 import GapPlannerState, _GapScores
from .controlled_predictive_mass_bound_v14 import mass_bound_unknown_action_bounds
from .controlled_predictive_partial_v12 import _terminal
from .controlled_predictive_resampling_v15 import AcquisitionScores


@dataclass
class _ScoreCache:
    scores: _GapScores
    radius: dict
    dirty: set

    def mappings(self):
        s = self.scores
        return (s.lower, s.upper, s.q_lower, s.q_upper, s.lower_policy,
                s.upper_policy, s.scale, self.radius)

    def clone(self):
        copied = [dict(mapping) for mapping in self.mappings()]
        return _ScoreCache(_GapScores(*copied[:7]), copied[7], set(self.dirty))


class CachedGapPlannerState(GapPlannerState):
    """Keep the frozen policy, score arithmetic, candidates and stopping rule."""

    def __init__(self, *args, **kwargs):
        started = perf_counter()
        super().__init__(*args, **kwargs)
        self.score_caches = {}
        self.work_counts["gap_cache_containers_initialized"] += 1
        self.engine_seconds = perf_counter() - started

    @classmethod
    def from_warm(cls, warm):
        started = perf_counter()
        child = super().from_warm(warm)
        child.score_caches = {}
        child.work_counts["gap_cache_containers_initialized"] += 1
        child.conversion_seconds = perf_counter() - started
        child.engine_seconds = warm.engine_seconds + child.conversion_seconds
        return child

    def _observe_state(self, key):
        new = key not in self.profiles
        super()._observe_state(key)
        if new:
            for cache in self.score_caches.values():
                cache.dirty.add(key)
            self.work_counts["dirty_gap_state_marks"] += len(self.score_caches)

    def observe_batch(self, key, action, batch):
        started = perf_counter()
        engine_before = self.engine_seconds
        super().observe_batch(key, action, batch)
        if self.score_caches:
            affected = {key}
            pending = [key]
            while pending:
                current = pending.pop()
                self.work_counts["gap_reverse_dependency_states_visited"] += 1
                for parent in self.reverse_dependencies.get(current, ()):
                    if parent not in affected:
                        affected.add(parent)
                        pending.append(parent)
            for cache in self.score_caches.values():
                before = len(cache.dirty)
                cache.dirty.update(affected)
                self.work_counts["dirty_gap_state_marks"] += len(cache.dirty) - before
        self.engine_seconds = engine_before + perf_counter() - started

    def clone(self):
        started = perf_counter()
        child = super().clone()
        child.score_caches = {name: cache.clone() for name, cache in self.score_caches.items()}
        child.work_counts.update(
            gap_cache_clone_calls=1,
            clone_gap_cache_entries_copied=sum(
                sum(map(len, cache.mappings())) + len(cache.dirty)
                for cache in self.score_caches.values()))
        child.clone_seconds = perf_counter() - started
        child.engine_seconds = self.engine_seconds + child.clone_seconds
        return child

    def _refresh_score_state(self, key, query, cache):
        """Use the same expressions and action iteration as frozen V16."""
        scores, observed, work = cache.scores, self.profiles[key], self.work_counts
        work["gap_score_state_visits"] += 1
        if observed.status != "ACTIVE":
            scores.lower[key] = scores.upper[key] = _terminal(observed.status, query)
            return
        for action in observed.legal_actions:
            pair = key, action
            lower, upper = mass_bound_unknown_action_bounds(key, observed, action, query)
            work.update(gap_score_action_evaluations=1, gap_physical_bound_evaluations=1)
            if pair not in self.rows:
                scores.q_lower[pair], scores.q_upper[pair] = lower, upper
                scores.scale[pair] = upper - lower
                continue
            row = self.rows[pair]
            radius = (upper - lower) / math.sqrt(256 * self.batch_counts[pair])
            scores.scale[pair] = cache.radius[pair] = radius
            work.update(gap_radius_evaluations=1, gap_score_row_reads=1,
                        gap_score_successor_reads=2 * len(row))
            scores.q_lower[pair] = math.fsum(
                weight * (query.reward_weight * reward + scores.lower[successor])
                for weight, successor, reward in row
            ) - radius
            scores.q_upper[pair] = math.fsum(
                weight * (query.reward_weight * reward + scores.upper[successor])
                for weight, successor, reward in row
            ) + radius
        scores.lower_policy[key] = min(
            observed.legal_actions, key=lambda action: (-scores.q_lower[key, action], action))
        scores.upper_policy[key] = min(
            observed.legal_actions, key=lambda action: (-scores.q_upper[key, action], action))
        scores.lower[key] = scores.q_lower[key, scores.lower_policy[key]]
        scores.upper[key] = scores.q_upper[key, scores.upper_policy[key]]

    def _gap_scores(self, query_name):
        work = self.work_counts
        work["gap_score_queries"] += 1
        if query_name not in self.score_caches:
            self.score_caches[query_name] = _ScoreCache(_GapScores({}, {}, {}, {}, {}, {}, {}), {}, set(self.profiles))
            work["gap_score_cache_initializations"] += 1
        cache = self.score_caches[query_name]
        if cache.dirty:
            work["gap_score_cache_updates"] += 1
            for key in sorted(cache.dirty):
                self._refresh_score_state(key, self.queries[query_name], cache)
            cache.dirty.clear()
        else:
            work["gap_score_cache_hits"] += 1
        return cache.scores

    def _acquisition_scores(self, query_name):
        """The V15 upper scores and known-row radii equal these V16 values."""
        scores = self._gap_scores(query_name)
        self.work_counts["resampling_score_cache_reuses"] += 1
        return AcquisitionScores(scores.upper, scores.q_upper, scores.upper_policy,
                                 self.score_caches[query_name].radius)
