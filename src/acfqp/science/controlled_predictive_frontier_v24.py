"""Expose unknown rows on the existing gap witnesses before balanced repeats."""

from time import perf_counter

from .controlled_predictive_score_cache_v18 import CachedGapPlannerState


class FrontierGapPlannerState(CachedGapPlannerState):
    """Keep the original structural selector first and extend its empty result."""

    def select_row(self, key, query_name):
        started, engine_before = perf_counter(), self.engine_seconds
        work = self.work_counts
        work["frontier_selection_calls"] += 1
        try:
            pair = super().select_row(key, query_name)
            if pair is not None:
                work["frontier_original_structure_selected"] += 1
                return pair
            work["frontier_extension_calls"] += 1
            observed = self.profiles[key]
            if observed.status != "ACTIVE":
                work["frontier_to_balanced_fallbacks"] += 1
                return None
            # super.select_row already refreshed the empirical policy. Reuse it
            # and the V18 scores; assess_gap would repeat the candidate walk.
            incumbent = self.caches[query_name].policy[key]
            scores = self._gap_scores(query_name)
            challengers = [action for action in observed.legal_actions if action != incumbent]
            work["frontier_challenger_actions_considered"] += len(challengers)
            challenger = min(challengers, key=lambda action: (-scores.q_upper[key, action], action)) if challengers else None
            candidates = self._gap_candidates(key, incumbent, challenger, scores)
            work["frontier_candidate_entries_inspected"] += len(candidates)
            unknown = {pair: contribution for pair, contribution in candidates.items()
                       if pair not in self.rows and contribution > 0}
            work["frontier_unknown_candidates_considered"] += len(unknown)
            if unknown:
                work["frontier_extension_selected"] += 1
                return min(unknown, key=lambda pair: (-unknown[pair], pair))
            work["frontier_to_balanced_fallbacks"] += 1
            return None
        finally:
            # Include original selection and extension once, including early exits.
            self.engine_seconds = engine_before + perf_counter() - started
