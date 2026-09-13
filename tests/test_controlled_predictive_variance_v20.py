"""Variance priority, shared effects, unchanged stopping and paid fallback."""

from copy import deepcopy
import math

from acfqp.science import controlled_predictive_variance_v20 as variance_module
from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_execution_v13 import ExactEnvironment
from acfqp.science.controlled_predictive_execution_v17 import evaluate_balanced_gap_execution
from acfqp.science.controlled_predictive_mass_bound_v14 import MassBoundPlannerState
from acfqp.science.controlled_predictive_partial_v12 import BoardProfile
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState
from acfqp.science.controlled_predictive_variance_v20 import VarianceGapPlannerState


def board(rank):
    return (0,) * 5 + (rank,) + (0,) * 10


H1, H2, END = (1, board(1)), (2, board(1)), (0, board(1))
COMMON, SECOND, WON = (1, board(2)), (1, board(3)), (1, (11,) + (0,) * 15)
QUERIES = {"q": Query(1, 1, 0)}


def row(low, high):
    return ((.5, END, low), (.5, END, high))


def selection(state):
    return state.select_resample(state.root, "q", mode="BALANCED")


def test_unbiased_sample_variance_and_batch_reduction_change_the_ranking():
    state = VarianceGapPlannerState(H1, QUERIES)
    # Population-variance ranking would prefer LEFT: 3.003/1536 > 1/512.
    # The declared unbiased correction reverses it: 3.003/1533 < 1/510.
    for _ in range(2):
        state.observe_batch(H1, "LEFT", row(0., 2 * math.sqrt(3.003)))
    state.observe_batch(H1, "RIGHT", row(0., 2.))
    assert selection(state) == (H1, "RIGHT")
    # Sufficient variance can outweigh LEFT's larger existing sample count.
    other = VarianceGapPlannerState(H1, QUERIES)
    for _ in range(2):
        other.observe_batch(H1, "LEFT", row(0., 4.))
    other.observe_batch(H1, "RIGHT", row(0., 1.))
    assert selection(other) == (H1, "LEFT")


def test_equal_positive_scores_use_the_declared_row_key_tie_order():
    state = VarianceGapPlannerState(H1, QUERIES)
    state.observe_batch(H1, "LEFT", row(1., 3.))
    state.observe_batch(H1, "RIGHT", row(0., 2.))
    assert selection(state) == (H1, "LEFT")
    assert state.work_counts["variance_positive_candidates"] == 2
    assert state.work_counts["variance_fallback_calls"] == 0


def test_shared_high_variance_successor_cancels_before_scoring():
    state = VarianceGapPlannerState(H2, QUERIES)
    state.observe_batch(COMMON, "DOWN", row(0., 20.))
    for action in ("LEFT", "RIGHT"):
        state.observe_batch(H2, action, ((.5, COMMON, 0.), (.5, WON, 0.)))
    assert selection(state) == (H2, "LEFT")
    assert state.work_counts["variance_cancelled_states"] == 2
    assert state.work_counts["variance_rows_scored"] == 2
    assert state.work_counts["variance_fallback_calls"] == 0


def test_unequal_shared_reach_uses_the_square_of_its_net_coefficient():
    state = VarianceGapPlannerState(H2, QUERIES)
    state.observe_batch(COMMON, "DOWN", row(2 - math.sqrt(2), 2 + math.sqrt(2)))
    state.observe_batch(H2, "LEFT", ((.75, COMMON, 0.), (.25, WON, 0.)))
    state.observe_batch(H2, "RIGHT", ((.25, COMMON, 0.), (.75, WON, 0.)))
    # Root row variance is .75; common variance is 2 with c=.5. Squaring c
    # gives .5, below .75; abs(c) or summed reach would incorrectly prefer it.
    assert selection(state) == (H2, "LEFT")
    assert state.work_counts["variance_rows_scored"] == 3
    assert state.work_counts["variance_fallback_calls"] == 0


def test_parent_variance_refreshes_when_only_a_child_observation_changes():
    state = VarianceGapPlannerState(H2, QUERIES)
    for child in (COMMON, SECOND):
        state.observe_batch(child, "DOWN", ((1., END, 1.),))
    state.observe_batch(H2, "LEFT", ((.5, COMMON, 0.), (.5, SECOND, 0.)))
    state.observe_batch(H2, "RIGHT", ((.5, WON, 0.), (.5, WON, 2.)))
    assert selection(state) == (H2, "RIGHT")
    state.observe_batch(COMMON, "DOWN", ((1., END, 9.),))
    assert state.batch_counts[H2, "LEFT"] == state.batch_counts[H2, "RIGHT"] == 1
    assert selection(state) == (H2, "LEFT")


def test_unknown_rows_are_not_scored_as_observed_zero_variance():
    state = VarianceGapPlannerState(H2, QUERIES)
    state.observe_batch(H2, "LEFT", ((1., COMMON, 0.),))
    chosen = selection(state)
    assert chosen in state.rows
    assert state.work_counts["variance_unknown_frontiers"] > 0
    assert state.work_counts["variance_fallback_calls"] == 1
    assert state.spent_batches == 1 and state.batch_counts == {(H2, "LEFT"): 1}


def complete_warm():
    warm = MassBoundPlannerState(H1, QUERIES)
    provider = BatchRowSampleProvider(71)
    for action in warm.profiles[H1].legal_actions:
        warm.observe_row(H1, action, provider.sample(H1, action))
    return warm


def test_zero_return_variance_keeps_v18_execution_stopping_and_actual_batch_cap():
    warm = complete_warm()
    environment = ExactEnvironment.from_closure(build_development_closure(horizon=1, boards={"fixture": H1[1]}))
    outputs = []
    for cls in (CachedGapPlannerState, VarianceGapPlannerState):
        state = cls.from_warm(warm)
        original = deepcopy(state.__dict__)
        result = evaluate_balanced_gap_execution(state, BatchRowSampleProvider(71), "q", environment,
                                                total_batch_cap=7)
        assert state.__dict__ == original
        assert result["deployment"]["maximum_total_batches"] == 7
        assert result["physical_audit"]["provider_counts"]["physical_draws"] == 768
        outputs.append(result)
    old, new = outputs
    assert new["trace"] == old["trace"] and new["root_metrics"] == old["root_metrics"]
    assert new["trace"]["acquisition_stop_reason"] == "TOTAL_SAMPLE_CAP_EXHAUSTED"
    assert new["deployment"]["expected_suffix_work_counts"]["variance_fallback_calls"] == 3
    assert new["deployment"]["expected_seconds_by_stage"]["resampling_score_and_selection"] > 0


def test_original_gap_stop_precedes_any_variance_allocation(monkeypatch):
    warm = VarianceGapPlannerState(H1, QUERIES)
    for action in warm.profiles[H1].legal_actions:
        warm.observe_batch(H1, action, ((1., END, float(action == "LEFT")),))
    assessment = warm.assess_gap(H1, "q")
    assert assessment.separated
    def should_not_allocate(*args, **kwargs):
        raise AssertionError("the existing separated gap must stop before allocation")
    monkeypatch.setattr(VarianceGapPlannerState, "select_resample", should_not_allocate)
    environment = ExactEnvironment.from_closure(build_development_closure(horizon=1, boards={"fixture": H1[1]}))
    result = evaluate_balanced_gap_execution(warm, BatchRowSampleProvider(71), "q", environment,
                                            total_batch_cap=128)
    assert result["trace"]["acquisition_stop_reason"] == "HEURISTIC_GAP_SEPARATED"
    assert result["deployment"]["maximum_total_batches"] == 4
    assert not result["physical_audit"]["provider_counts"]


def test_conversion_clone_isolation_and_selection_time_includes_fallback_once(monkeypatch):
    state = VarianceGapPlannerState.from_warm(complete_warm())
    state.assess_gap(H1, "q")
    before = deepcopy(state.__dict__)
    cloned = state.clone()
    assert type(cloned) is VarianceGapPlannerState
    cloned.observe_batch(H1, "LEFT", row(0., 2.))
    selection(cloned)
    assert state.__dict__ == before
    assert cloned.batch_counts[H1, "LEFT"] == 2 and state.batch_counts[H1, "LEFT"] == 1
    old_engine = state.engine_seconds
    ticks = iter((10., 14.))
    monkeypatch.setattr(variance_module, "perf_counter", lambda: next(ticks))
    assert selection(state) in state.rows
    assert state.engine_seconds == old_engine + 4.
    assert state.work_counts["variance_fallback_calls"] == 1
    assert state.work_counts["resampling_selection_calls"] == 1


def test_no_challenger_falls_back_without_inventing_a_competing_action():
    state = VarianceGapPlannerState(H1, QUERIES)
    observed = state.profiles[H1]
    state.profiles[H1] = BoardProfile(observed.status, ("LEFT",), (("LEFT", observed.reward("LEFT")),), observed.mass)
    state.observe_batch(H1, "LEFT", row(0., 2.))
    assert selection(state) == (H1, "LEFT")
    assert state.work_counts["variance_no_challenger_calls"] == 1
    assert state.work_counts["variance_fallback_calls"] == 1
    assert state.work_counts["variance_rows_scored"] == 0
