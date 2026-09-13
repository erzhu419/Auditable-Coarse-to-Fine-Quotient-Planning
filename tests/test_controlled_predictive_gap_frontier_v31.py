from copy import deepcopy

import pytest

from acfqp.science.controlled_predictive_gap_frontier_v31 import GapFrontierPlannerState
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState


def _key(horizon, rank):
    return horizon, (10,) * 15 + (rank,)


ROOT = _key(2, 1)
COMMON, A, B = (_key(1, rank) for rank in (2, 3, 4))
END = _key(0, 1)
LOST = (1, tuple(1 + (i + i // 4) % 2 for i in range(16)))


def _snapshot(common_probability=.5, right_probability=None):
    state = GapFrontierPlannerState(ROOT, {"q": Query(0, 1, 2)})
    for child in (COMMON, A, B):
        state.observe_batch(child, "DOWN", ((1., END, 0.),))
    right_probability = common_probability if right_probability is None else right_probability
    for action, child, probability in (("LEFT", A, common_probability), ("RIGHT", B, right_probability)):
        row = tuple(item for item in ((probability, COMMON, 0.), (1 - probability, child, 0.)) if item[0] > 0)
        state.observe_batch(ROOT, action, row)
    for action in ("DOWN", "UP"):
        state.observe_batch(ROOT, action, ((1., LOST, 0.),))
    return state


def test_shared_child_cancels_and_observed_lower_action_does_not_hide_unknown_competitor():
    state = _snapshot()
    cache = state.solve("q")
    assert cache.policy[ROOT] == "LEFT" and cache.policy[A] == "DOWN"
    assert (A, "DOWN") in state.rows and (A, "LEFT") not in state.rows
    assert state.select_row(ROOT, "q") == (A, "LEFT")
    # COMMON sorts before A; summing absolute reaches would wrongly select it.
    assert state.work_counts["gap_frontier_cancelled_successors"] == 1
    assert state.work_counts["gap_frontier_selected"] == 1


def test_net_reach_is_used_before_deterministic_pair_ties():
    state = _snapshot(.75, .25)
    # Net weights: COMMON=.5, A=.25, B=.75, all with the same action slack.
    assert state.select_row(ROOT, "q") == (B, "LEFT")
    tied = _snapshot(.5)
    assert tied.select_row(ROOT, "q") == (A, "LEFT")


def test_new_priority_overrides_existing_structural_candidate_and_only_charges_computation(monkeypatch):
    state = _snapshot()
    original = CachedGapPlannerState.select_row(state, ROOT, "q")
    assert original == (COMMON, "LEFT")
    before = deepcopy(state.rows), deepcopy(state.outcome_counts), state.spent_batches
    engine_before = state.engine_seconds
    gap_before = state.work_counts["gap_score_queries"]

    def forbidden(*args, **kwargs):
        pytest.fail("positive new priority unnecessarily called the original selector")

    monkeypatch.setattr(CachedGapPlannerState, "select_row", forbidden)
    assert state.select_row(ROOT, "q") == (A, "LEFT")
    assert (state.rows, state.outcome_counts, state.spent_batches) == before
    assert state.work_counts["gap_score_queries"] == gap_before
    assert state.work_counts["gap_frontier_root_rows_read"] == 2
    assert state.work_counts["gap_frontier_child_actions_considered"] == 8
    assert state.engine_seconds > engine_before


def test_unknown_root_and_no_positive_candidates_fall_back_to_original_and_preserve_repeats():
    unknown = GapFrontierPlannerState(ROOT, {"q": Query(0, 1, 2)})
    expected = CachedGapPlannerState.select_row(unknown.clone(), ROOT, "q")
    assert unknown.select_row(ROOT, "q") == expected
    assert unknown.work_counts["gap_frontier_unknown_root_fallbacks"] == 1

    cancelled = _snapshot(1.)
    reference = cancelled.clone()
    assert cancelled.select_row(ROOT, "q") == CachedGapPlannerState.select_row(reference, ROOT, "q")
    assert cancelled.work_counts["gap_frontier_original_fallbacks"] == 1
    assert cancelled.select_resample(ROOT, "q", mode="BALANCED") == reference.select_resample(ROOT, "q", mode="BALANCED")


def test_unknown_action_with_upper_at_current_lower_is_not_a_candidate():
    state = _snapshot()
    # Known actions attain the physical upper bound; remaining actions cannot
    # improve the current state's value, although their own intervals are wide.
    state.queries["q"] = Query(0, 1, 0)
    state.caches.clear()
    state.score_caches.clear()
    assert state.select_row(ROOT, "q") is None
    assert state.work_counts["gap_frontier_unknown_actions_considered"] > 0
    assert state.work_counts["gap_frontier_positive_candidates"] == 0
