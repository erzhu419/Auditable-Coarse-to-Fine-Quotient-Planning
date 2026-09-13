"""V20 empirical return-variance allocation under the unchanged V18 stop rule."""

import math
from time import perf_counter

from .controlled_predictive_score_cache_v18 import CachedGapPlannerState


class VarianceGapPlannerState(CachedGapPlannerState):
    """Change only which already observed row receives the next paid batch."""

    def select_resample(self, key, query_name, mode):
        if mode != "BALANCED":
            raise ValueError("V20 replaces the frozen BALANCED allocation call")
        started = perf_counter()
        engine_before = self.engine_seconds
        self._observe_state(key)
        cache = self.solve(query_name)
        gap_scores = self._gap_scores(query_name)
        query = self.queries[query_name]
        work = self.work_counts
        work["variance_selection_calls"] += 1
        incumbent = cache.policy[key]
        challengers = [action for action in self.profiles[key].legal_actions if action != incumbent]
        candidates = []
        if challengers:
            challenger = min(challengers, key=lambda action: (-gap_scores.q_upper[key, action], action))
            work["variance_competing_action_pairs"] += 1
            incoming = {}

            def score_and_propagate(pair, coefficient):
                if pair not in self.rows:
                    work["variance_unknown_frontiers"] += 1
                    return
                row = self.rows[pair]
                work["variance_observed_row_reads"] += 1
                # The cached radius is positive exactly when the original
                # physical range is positive for this observed row.
                if gap_scores.scale[pair] > 0:
                    n = 256 * self.batch_counts[pair]
                    returns = [query.reward_weight * reward + cache.lower[successor]
                               for _, successor, reward in row]
                    mean = math.fsum(weight * value for (weight, _, _), value in zip(row, returns))
                    variance = n / (n - 1) * math.fsum(
                        weight * (value - mean) ** 2 for (weight, _, _), value in zip(row, returns))
                    score = coefficient ** 2 * variance * (1 / n - 1 / (n + 256))
                    work.update(variance_rows_scored=1, variance_return_successor_reads=len(row),
                                variance_mean_terms=len(row), variance_centered_terms=len(row))
                    if score > 0:
                        candidates.append((score, self.batch_counts[pair], pair))
                        work["variance_positive_candidates"] += 1
                    else:
                        work["variance_zero_scores"] += 1
                else:
                    work["variance_physical_zero_range_rows"] += 1
                work["variance_propagation_successor_reads"] += len(row)
                for weight, successor, _ in row:
                    incoming.setdefault(successor, []).append(coefficient * weight)

            score_and_propagate((key, incumbent), 1.)
            score_and_propagate((key, challenger), -1.)
            work["variance_profile_order_entries"] += len(self.profiles)
            for current in sorted(self.profiles, key=lambda item: (-item[0], item[1])):
                if current not in incoming:
                    continue
                work["variance_reached_state_visits"] += 1
                contributions = incoming[current]
                coefficient = math.fsum(contributions)
                work["variance_net_contributions_merged"] += len(contributions)
                if coefficient == 0:
                    work["variance_cancelled_states"] += 1
                    continue
                if self.profiles[current].status == "ACTIVE":
                    score_and_propagate((current, cache.policy[current]), coefficient)
        else:
            work["variance_no_challenger_calls"] += 1
        if candidates:
            result = min(candidates, key=lambda item: (-item[0], item[1], item[2]))[2]
        else:
            work["variance_fallback_calls"] += 1
            result = super().select_resample(key, query_name, mode="BALANCED")
        # solve and fallback already time their work internally; replace their
        # nested additions with the elapsed time of this one whole selection.
        self.engine_seconds = engine_before + (perf_counter() - started)
        return result
