"""History-local batches and heuristic resampling scores on the V14 planner.

The ordinary interval caches and execution policy remain V14. The separate
acquisition scores use a range/sqrt(sample_count) proxy without a confidence
level or a statistical coverage claim. Scores are deliberately not clipped to
physical value bounds. Every new batch contains 256 draws.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from time import perf_counter
from typing import Mapping

from .controlled_predictive_mass_bound_v14 import (
    MassBoundPlannerState, mass_bound_unknown_action_bounds,
)
from .controlled_predictive_partial_v12 import Key, SampleRow, _terminal
from .controlled_predictive_quotient_v1 import Query


Pair = tuple[Key, str]
CountKey = tuple[Key, float]


def _batch_counts(row: SampleRow) -> Counter[CountKey]:
    counts: Counter[CountKey] = Counter()
    for weight, successor, reward in row:
        count = int(weight * 256)
        if count <= 0 or count != weight * 256:
            raise ValueError("V15 observes positive integer counts from one 256-draw batch")
        counts[successor, reward] += count
    if sum(counts.values()) != 256:
        raise ValueError("a V15 observation batch must contain exactly 256 draws")
    return counts


@dataclass
class AcquisitionScores:
    upper: dict[Key, float]
    q_upper: dict[Pair, float]
    policy: dict[Key, str]
    radius: dict[Pair, float]


class ResamplingPlannerState(MassBoundPlannerState):
    """A V14 observed model with independent, cumulative row-batch counts."""

    def __init__(self, root: Key, queries: Mapping[str, Query], mode: str = "query_interval",
                 update_mode: str = "incremental"):
        started = perf_counter()
        super().__init__(root, queries, mode, update_mode)
        self.outcome_counts: dict[Pair, Counter[CountKey]] = {}
        self.batch_counts: dict[Pair, int] = {}
        self.spent_batches = 0
        self.conversion_seconds = 0.0
        self.engine_seconds = perf_counter() - started

    @classmethod
    def from_warm(cls, warm: MassBoundPlannerState) -> ResamplingPlannerState:
        """Clone and convert a first-batch-only V14 warm model; charge all work."""
        started = perf_counter()
        child = warm.clone()
        child.__class__ = cls
        child.outcome_counts = {pair: _batch_counts(row) for pair, row in child.rows.items()}
        child.batch_counts = {pair: 1 for pair in child.rows}
        child.spent_batches = len(child.rows)
        child.work_counts.update(warm_batch_conversions=1, conversion_rows_copied=len(child.rows),
                                 conversion_outcome_entries_copied=sum(map(len, child.outcome_counts.values())))
        child.conversion_seconds = perf_counter() - started
        child.engine_seconds = warm.engine_seconds + child.conversion_seconds
        return child

    def observe_row(self, key: Key, action: str, row: SampleRow) -> None:
        """Retain the inherited new-row interface without bypassing batch counts."""
        if (key, action) in self.rows:
            raise ValueError("use observe_batch to add draws to an already observed row")
        self.observe_batch(key, action, row)

    def observe_batch(self, key: Key, action: str, batch: SampleRow) -> None:
        """Pool one new batch and invalidate the changed row's observed ancestors."""
        started = perf_counter()
        engine_before = self.engine_seconds
        counts = _batch_counts(batch)
        if any(successor[0] != key[0] - 1 for successor, _ in counts):
            raise ValueError("batch successors must be one horizon below their parent")
        pair = (key, action)
        if pair not in self.rows:
            super().observe_row(key, action, batch)
            self.outcome_counts[pair] = counts
            self.batch_counts[pair] = 1
            self.work_counts["first_batch_observations_inserted"] += 1
        else:
            self.outcome_counts[pair].update(counts)
            self.batch_counts[pair] += 1
            total_draws = 256 * self.batch_counts[pair]
            self.rows[pair] = tuple((count / total_draws, successor, reward)
                                   for (successor, reward), count in sorted(self.outcome_counts[pair].items()))
            for successor, _ in counts:
                self._observe_state(successor)
                parents = self.reverse_dependencies.setdefault(successor, set())
                if key not in parents:
                    parents.add(key)
                    self.work_counts["reverse_dependency_edges_inserted"] += 1
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
            self.work_counts["repeat_batch_observations_inserted"] += 1
            self.work_counts["pooled_outcome_entries_written"] += len(self.rows[pair])
            self.stop_reason = None
        self.spent_batches += 1
        self.work_counts.update(batch_draws_inserted=256, batch_outcome_entries_read=len(batch))
        self.engine_seconds = engine_before + (perf_counter() - started)

    def clone(self) -> ResamplingPlannerState:
        """Copy all batch dictionaries; immutable profile and row values share."""
        started = perf_counter()
        child = super().clone()
        child.outcome_counts = {pair: counts.copy() for pair, counts in self.outcome_counts.items()}
        child.batch_counts = dict(self.batch_counts)
        child.spent_batches = self.spent_batches
        child.conversion_seconds = self.conversion_seconds
        child.work_counts.update(clone_batch_count_entries_copied=len(self.batch_counts),
                                 clone_outcome_count_entries_copied=sum(map(len, self.outcome_counts.values())))
        child.clone_seconds = perf_counter() - started
        child.engine_seconds = self.engine_seconds + child.clone_seconds
        return child

    def _acquisition_scores(self, query_name: str) -> AcquisitionScores:
        """Compute temporary heuristic scores; leave the V14 caches unchanged."""
        query = self.queries[query_name]
        scores = AcquisitionScores({}, {}, {}, {})
        work = self.work_counts
        work["resampling_score_queries"] += 1
        for key in sorted(self.profiles):
            observed = self.profiles[key]
            work["resampling_score_state_visits"] += 1
            if observed.status != "ACTIVE":
                scores.upper[key] = _terminal(observed.status, query)
                continue
            for action in observed.legal_actions:
                pair = key, action
                physical_lower, physical_upper = mass_bound_unknown_action_bounds(key, observed, action, query)
                work.update(resampling_score_action_evaluations=1, resampling_physical_bound_evaluations=1)
                if pair not in self.rows:
                    scores.q_upper[pair] = physical_upper
                    continue
                row = self.rows[pair]
                radius = (physical_upper - physical_lower) / math.sqrt(256 * self.batch_counts[pair])
                scores.radius[pair] = radius
                work.update(resampling_radius_evaluations=1, resampling_score_row_reads=1,
                            resampling_score_successor_reads=len(row))
                scores.q_upper[pair] = math.fsum(
                    weight * (query.reward_weight * reward + scores.upper[successor])
                    for weight, successor, reward in row
                ) + radius
            scores.upper[key] = max(scores.q_upper[key, action] for action in observed.legal_actions)
            scores.policy[key] = min(observed.legal_actions,
                                     key=lambda action: (-scores.q_upper[key, action], action))
        return scores

    def select_resample(self, key: Key, query_name: str, mode: str) -> Pair | None:
        """Choose an observed positive-range row on the scoring policy frontier."""
        if mode not in {"BALANCED", "DIRECTED"}:
            raise ValueError("V15 resampling selection is BALANCED or DIRECTED")
        started = perf_counter()
        self._observe_state(key)
        scores = self._acquisition_scores(query_name)
        reach = {key: 1.0}
        candidates = []
        work = self.work_counts
        work["resampling_selection_calls"] += 1
        for current in sorted(self.profiles, key=lambda item: (-item[0], item[1])):
            probability = reach.get(current, 0.0)
            if probability <= 0 or self.profiles[current].status != "ACTIVE":
                continue
            work["resampling_frontier_state_visits"] += 1
            pair = current, scores.policy[current]
            if pair not in self.rows:
                continue
            radius = scores.radius[pair]
            if radius > 0:
                candidates.append((pair, probability * radius))
            row = self.rows[pair]
            work.update(resampling_frontier_row_reads=1, resampling_frontier_successor_reads=len(row))
            for weight, successor, _ in row:
                reach[successor] = reach.get(successor, 0.0) + probability * weight
        work["resampling_candidates_considered"] += len(candidates)
        if not candidates:
            result = None
            work["resampling_empty_candidate_sets"] += 1
        elif mode == "BALANCED":
            result = min(candidates, key=lambda item: (self.batch_counts[item[0]], item[0]))[0]
        else:
            result = min(candidates, key=lambda item: (-item[1], item[0]))[0]
        self.engine_seconds += perf_counter() - started
        return result
