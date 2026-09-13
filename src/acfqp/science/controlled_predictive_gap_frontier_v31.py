"""H2 first observations ranked by their influence on a root action gap."""

import math
from time import perf_counter

from .controlled_predictive_score_cache_v18 import CachedGapPlannerState


class GapFrontierPlannerState(CachedGapPlannerState):
    """Prioritize unknown competing H1 actions; preserve execution and repeats.

    Scores use the empirical completion intervals, without sampling radii or
    exact transitions. This is a priority heuristic, not an error certificate.
    Other horizons and missing root rows use the original structural selector.
    """

    def select_row(self, key, query_name):
        started, engine_before = perf_counter(), self.engine_seconds
        work = self.work_counts
        work["gap_frontier_selection_calls"] += 1
        try:
            self._observe_state(key)
            profile = self.profiles[key]
            if key[0] == 2 and profile.status == "ACTIVE":
                cache = self.solve(query_name)
                incumbent = cache.policy[key]
                challengers = [action for action in profile.legal_actions if action != incumbent]
                work["gap_frontier_challenger_actions_considered"] += len(challengers)
                challenger = min(challengers, key=lambda action: (-cache.q_upper[key, action], action)) if challengers else None
                if challenger is not None and all((key, action) in self.rows for action in (incumbent, challenger)):
                    incoming = {}
                    for action, sign in ((incumbent, 1.), (challenger, -1.)):
                        row = self.rows[key, action]
                        work["gap_frontier_root_rows_read"] += 1
                        work["gap_frontier_root_outcomes_read"] += len(row)
                        for probability, successor, _ in row:
                            incoming.setdefault(successor, []).append(sign * probability)
                    candidates = []
                    for successor, terms in incoming.items():
                        coefficient = math.fsum(terms)
                        work["gap_frontier_successors_considered"] += 1
                        work["gap_frontier_signed_terms_merged"] += len(terms)
                        if coefficient == 0:
                            work["gap_frontier_cancelled_successors"] += 1
                            continue
                        child = self.profiles[successor]
                        if child.status != "ACTIVE":
                            work["gap_frontier_terminal_successors_skipped"] += 1
                            continue
                        for action in child.legal_actions:
                            pair = successor, action
                            work["gap_frontier_child_actions_considered"] += 1
                            if pair in self.rows:
                                continue
                            work["gap_frontier_unknown_actions_considered"] += 1
                            unresolved = max(0., cache.q_upper[pair] - cache.lower[successor])
                            score = abs(coefficient) * unresolved
                            if score > 0:
                                candidates.append((score, pair))
                                work["gap_frontier_positive_candidates"] += 1
                    if candidates:
                        work["gap_frontier_selected"] += 1
                        return min(candidates, key=lambda item: (-item[0], item[1]))[1]
                elif challenger is not None:
                    work["gap_frontier_unknown_root_fallbacks"] += 1
            work["gap_frontier_original_fallbacks"] += 1
            return super().select_row(key, query_name)
        finally:
            # solve and fallback already time their nested work; count it once.
            self.engine_seconds = engine_before + perf_counter() - started
