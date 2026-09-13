"""Value-gap acquisition using full heuristic score recomputation for V16.

The range/sqrt(N) scales have no confidence level or coverage claim. Execution
still follows the original empirical policy; these scores only decide whether
and where to acquire another paid batch.
"""

from dataclasses import dataclass
import math
from time import perf_counter

from .controlled_predictive_mass_bound_v14 import mass_bound_unknown_action_bounds
from .controlled_predictive_partial_v12 import Key, _terminal
from .controlled_predictive_resampling_v15 import Pair, ResamplingPlannerState


@dataclass(frozen=True)
class GapAssessment:
    incumbent: str | None
    challenger: str | None
    incumbent_lower: float
    challenger_upper: float | None
    gap: float | None
    separated: bool
    pair: Pair | None
    candidate_count: int


@dataclass
class _GapScores:
    lower: dict
    upper: dict
    q_lower: dict
    q_upper: dict
    lower_policy: dict
    upper_policy: dict
    scale: dict


class GapPlannerState(ResamplingPlannerState):
    """Use the inherited sampled model and caches, with temporary gap scores."""

    def _gap_scores(self, query_name: str) -> _GapScores:
        query = self.queries[query_name]
        scores = _GapScores({}, {}, {}, {}, {}, {}, {})
        work = self.work_counts
        work["gap_score_queries"] += 1
        for key in sorted(self.profiles):
            observed = self.profiles[key]
            work["gap_score_state_visits"] += 1
            if observed.status != "ACTIVE":
                scores.lower[key] = scores.upper[key] = _terminal(observed.status, query)
                continue
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
                scores.scale[pair] = radius
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
        return scores

    def _gap_candidates(self, key: Key, incumbent: str, challenger: str | None,
                        scores: _GapScores) -> dict[Pair, float]:
        """Sum both witness paths, stopping each path at any unknown row."""
        candidates: dict[Pair, float] = {}
        work = self.work_counts
        paths = [(incumbent, scores.lower_policy)]
        if challenger is not None:
            paths.append((challenger, scores.upper_policy))
        for first_action, continuation in paths:
            reach = {key: 1.0}
            for current in sorted(self.profiles, key=lambda item: (-item[0], item[1])):
                probability = reach.get(current, 0.0)
                if probability <= 0 or self.profiles[current].status != "ACTIVE":
                    continue
                work["gap_frontier_state_visits"] += 1
                pair = current, first_action if current == key else continuation[current]
                scale = scores.scale[pair]
                if scale > 0:
                    candidates[pair] = candidates.get(pair, 0.0) + probability * scale
                    work["gap_candidate_contributions"] += 1
                if pair not in self.rows:
                    work["gap_unknown_frontiers"] += 1
                    continue
                row = self.rows[pair]
                work.update(gap_frontier_row_reads=1, gap_frontier_successor_reads=len(row))
                for weight, successor, _ in row:
                    reach[successor] = reach.get(successor, 0.0) + probability * weight
        work["gap_candidates_considered"] += len(candidates)
        return candidates

    def assess_gap(self, key: Key, query_name: str) -> GapAssessment:
        """Refresh the empirical policy, then assess the current action gap.

        Candidates are computed even when separated, allowing the frozen
        NO_STOP comparator to use the identical allocation rule.
        """
        started = perf_counter()
        engine_before = self.engine_seconds
        cache = self.solve(query_name)
        scores = self._gap_scores(query_name)
        self.work_counts["gap_assessments"] += 1
        observed = self.profiles[key]
        if observed.status != "ACTIVE":
            result = GapAssessment(None, None, scores.lower[key], None, None, True, None, 0)
        else:
            incumbent = cache.policy[key]
            challengers = [action for action in observed.legal_actions if action != incumbent]
            challenger = min(challengers, key=lambda action: (-scores.q_upper[key, action], action)) if challengers else None
            lower = scores.q_lower[key, incumbent]
            upper = scores.q_upper[key, challenger] if challenger is not None else None
            gap = lower - upper if upper is not None else None
            separated = gap is None or gap >= 0.0
            candidates = self._gap_candidates(key, incumbent, challenger, scores)
            pair = min(candidates, key=lambda candidate: (-candidates[candidate], candidate)) if candidates else None
            result = GapAssessment(incumbent, challenger, lower, upper, gap, separated, pair, len(candidates))
        self.work_counts["gap_separated_assessments"] += int(result.separated)
        self.engine_seconds = engine_before + (perf_counter() - started)
        return result
