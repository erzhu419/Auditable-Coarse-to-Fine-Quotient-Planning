"""Exact cached scores after new support, ancestor updates and query changes."""

from copy import deepcopy

from acfqp.science.controlled_predictive_gap_v16 import GapPlannerState
from acfqp.science.controlled_predictive_mass_bound_v14 import MassBoundPlannerState
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState


def board(rank):
    return (0,) * 5 + (rank,) + (0,) * 10


ROOT, A, B = (3, board(1)), (2, board(2)), (2, board(3))
TAIL, NEW = (1, board(1)), (1, board(2))
END = (0, board(1))
QUERIES = {"q": Query(1, 5, 0), "alt": Query(.2, .25, 3)}


def assert_equal(full, cached, names=QUERIES):
    for name in names:
        assert cached._gap_scores(name) == full._gap_scores(name)
        assert cached._acquisition_scores(name) == full._acquisition_scores(name)
        assert cached.assess_gap(ROOT, name) == full.assess_gap(ROOT, name)
        assert cached.select_resample(ROOT, name, mode="BALANCED") == full.select_resample(ROOT, name, mode="BALANCED")


def test_scores_match_after_first_batches_repeats_new_support_and_query_switch():
    full, cached = GapPlannerState(ROOT, QUERIES), CachedGapPlannerState(ROOT, QUERIES)
    assert_equal(full, cached, ("q",))
    for key, action, row in (
        (ROOT, "DOWN", ((1., A, 0.),)),
        (ROOT, "RIGHT", ((1., B, 0.),)),
        (A, "DOWN", ((1., TAIL, 0.),)),
        (B, "DOWN", ((1., TAIL, 0.),)),
        (TAIL, "DOWN", ((1., END, 0.),)),
    ):
        for state in (full, cached):
            state.observe_batch(key, action, row)
        assert_equal(full, cached)
    for state in (full, cached):
        state.observe_batch(A, "DOWN", ((1., NEW, 0.),))
    assert all(cache.dirty == {ROOT, A, NEW} for cache in cached.score_caches.values())
    full_before, cached_before = full.work_counts["gap_score_state_visits"], cached.work_counts["gap_score_state_visits"]
    assert cached._gap_scores("q") == full._gap_scores("q")
    assert cached.work_counts["gap_score_state_visits"] - cached_before == 3
    assert full.work_counts["gap_score_state_visits"] - full_before == len(full.profiles) > 3
    assert_equal(full, cached)
    # The pooled first support is retained: a deeper update reaches both parents.
    new_end = (0, board(2))
    for state in (full, cached):
        state.observe_batch(TAIL, "DOWN", ((1., new_end, 0.),))
    assert all(cache.dirty == {ROOT, A, B, TAIL, new_end} for cache in cached.score_caches.values())
    assert_equal(full, cached)
    unseen = (1, board(4))
    for state in (full, cached):
        state.observe_state(unseen)
    assert all(cache.dirty == {unseen} for cache in cached.score_caches.values())
    assert_equal(full, cached)


def test_valid_gap_cache_reuses_upper_scores_without_a_second_dp():
    state = CachedGapPlannerState(ROOT, QUERIES)
    state.observe_batch(ROOT, "DOWN", ((1., A, 0.),))
    scores = state._gap_scores("q")
    work_before = dict(state.work_counts)
    acquired = state._acquisition_scores("q")
    assert acquired.upper is scores.upper and acquired.q_upper is scores.q_upper
    assert acquired.policy is scores.upper_policy
    assert acquired.radius == {(ROOT, "DOWN"): scores.scale[ROOT, "DOWN"]}
    assert state.work_counts["gap_score_state_visits"] == work_before["gap_score_state_visits"]
    assert state.work_counts["gap_score_row_reads"] == work_before["gap_score_row_reads"]
    assert state.work_counts["resampling_score_cache_reuses"] == 1
    assert state.work_counts["resampling_score_state_visits"] == 0


def test_conversion_and_clone_charge_cache_setup_and_preserve_history_isolation():
    warm = MassBoundPlannerState(ROOT, QUERIES)
    warm.observe_row(ROOT, "DOWN", ((1., A, 0.),))
    warm.solve("q")
    original_work = dict(warm.work_counts)
    state = CachedGapPlannerState.from_warm(warm)
    assert type(state) is CachedGapPlannerState and state.score_caches == {}
    assert state.work_counts["gap_cache_containers_initialized"] == 1
    assert state.conversion_seconds > 0
    assert state.engine_seconds == warm.engine_seconds + state.conversion_seconds
    assert state.spent_batches == 1 and dict(warm.work_counts) == original_work
    for name in QUERIES:
        state.assess_gap(ROOT, name)
    state.observe_batch(A, "DOWN", ((1., TAIL, 0.),))
    before = deepcopy(state.score_caches)
    clone = state.clone()
    expected_copies = sum(sum(map(len, cache.mappings())) + len(cache.dirty)
                          for cache in state.score_caches.values())
    assert type(clone) is CachedGapPlannerState and clone.score_caches == before
    assert clone.work_counts["clone_gap_cache_entries_copied"] == expected_copies > 0
    assert clone.clone_seconds > 0
    assert clone.engine_seconds == state.engine_seconds + clone.clone_seconds
    for name, cache in state.score_caches.items():
        assert clone.score_caches[name].dirty is not cache.dirty
        assert all(a is not b for a, b in zip(cache.mappings(), clone.score_caches[name].mappings()))
    clone.observe_batch(A, "DOWN", ((1., NEW, 0.),))
    clone.assess_gap(ROOT, "q")
    assert state.score_caches == before and state.spent_batches == 2
    assert clone.spent_batches == 3
    assert NEW not in state.profiles and NEW in clone.profiles
