from copy import deepcopy

import pytest

from acfqp.science.controlled_predictive_frontier_v24 import FrontierGapPlannerState
from acfqp.science.controlled_predictive_frontier_variance_v26 import FrontierVarianceGapPlannerState
from acfqp.science.controlled_predictive_local_v21 import ARMS, run_local_allocation
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState
from acfqp.science.controlled_predictive_variance_v20 import VarianceGapPlannerState
from test_controlled_predictive_frontier_v24 import _snapshot, _Provider, ROOT, B, END


H1 = (1, ROOT[1])


def _complete_state(variable=True):
    state = CachedGapPlannerState(H1, {"q": Query(1, 1, 0)})
    rows = {"LEFT": ((.5, END, 2.), (.5, END, 4.)),
            "RIGHT": ((.5, END, 0.), (.5, END, 2.)),
            "DOWN": ((1., END, 0.),), "UP": ((1., END, 0.),)}
    if not variable:
        rows = {action: ((1., END, float(action == "LEFT")),) for action in rows}
    for action, row in rows.items():
        state.observe_batch(H1, action, row)
    state.observe_batch(H1, "LEFT", rows["LEFT"])
    return state, rows


def test_mro_reuses_original_selectors_and_variance_super_reaches_balanced():
    cls = FrontierVarianceGapPlannerState
    assert cls.__mro__[:4] == (cls, FrontierGapPlannerState, VarianceGapPlannerState, CachedGapPlannerState)
    assert cls.select_row is FrontierGapPlannerState.select_row
    assert cls.select_resample is VarianceGapPlannerState.select_resample
    assert cls.assess_gap is CachedGapPlannerState.assess_gap
    state, _ = _complete_state()
    state.__class__ = cls
    assert state.select_row(H1, "q") is None
    assert state.select_resample(H1, "q", mode="BALANCED") == (H1, "RIGHT")
    reference = state.clone()
    reference.__class__ = CachedGapPlannerState
    assert reference.select_resample(H1, "q", mode="BALANCED") == (H1, "LEFT")
    assert state.work_counts["frontier_to_balanced_fallbacks"] == 1
    assert state.work_counts["variance_fallback_calls"] == 0
    assert type(state.clone()) is cls


def test_original_structure_and_extra_frontier_both_precede_variance_repeat(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("an available new-row candidate entered repeat selection")
    monkeypatch.setattr(FrontierVarianceGapPlannerState, "select_resample", forbidden)
    empty = CachedGapPlannerState(H1, {"q": Query(1, 1, 0)})
    _, ordinary = run_local_allocation(empty, "FRONTIER_VARIANCE", _Provider({}), "q", H1, 1)
    assert ordinary["requested_batches"][0]["kind"] == "FIRST_OBSERVATION"
    assert ordinary["accounting"]["work_counts"]["frontier_original_structure_selected"] == 1
    snapshot = _snapshot()
    _, extra = run_local_allocation(snapshot, "FRONTIER_VARIANCE", _Provider(snapshot.rows), "risk", ROOT, 1)
    assert extra["requested_batches"] == [{"row_key": [[B[0], list(B[1])], "DOWN"],
        "batch_index": 0, "kind": "FIRST_OBSERVATION"}]
    assert extra["accounting"]["work_counts"]["frontier_extension_selected"] == 1


def test_no_positive_variance_uses_unchanged_balanced_fallback_once():
    snapshot, _ = _complete_state(variable=False)
    state = snapshot.clone()
    state.__class__ = FrontierVarianceGapPlannerState
    balanced = snapshot.select_resample(H1, "q", mode="BALANCED")
    assert state.select_row(H1, "q") is None
    assert state.select_resample(H1, "q", mode="BALANCED") == balanced
    assert state.work_counts["frontier_to_balanced_fallbacks"] == 1
    assert state.work_counts["variance_selection_calls"] == 1
    assert state.work_counts["variance_fallback_calls"] == 1
    assert state.work_counts["resampling_selection_calls"] == 1


def test_fixed_budget_repeat_indices_and_no_mutation_of_common_state():
    snapshot, rows = _complete_state()
    before = deepcopy(snapshot.__dict__)
    provider = _Provider({(H1, action): row for action, row in rows.items()})
    endpoint, report = run_local_allocation(snapshot, "FRONTIER_VARIANCE", provider, "q", H1, 3)
    assert snapshot.__dict__ == before
    assert report["completed_fixed_budget"] and report["completed_batches"] == 3
    assert report["initial_batches"] == 5 and report["final_batches"] == endpoint.spent_batches == 8
    assert report["actual_draws"] == report["provider_counts"]["physical_draws"] == 768
    assert report["requested_batches"][0] == {"row_key": [[H1[0], list(H1[1])], "RIGHT"],
        "batch_index": 1, "kind": "REPEAT_OBSERVATION"}
    counts = dict(snapshot.batch_counts)
    for row in report["requested_batches"]:
        key, action = row["row_key"]
        pair = (key[0], tuple(key[1])), action
        assert row["kind"] == "REPEAT_OBSERVATION" and row["batch_index"] == counts[pair]
        counts[pair] += 1
    assert endpoint.batch_counts == counts
    assert report["accounting"]["work_counts"]["frontier_to_balanced_fallbacks"] == 3
    assert report["accounting"]["work_counts"]["variance_selection_calls"] == 3
    assert report["accounting"]["work_counts"].get("variance_fallback_calls", 0) == 0
    with pytest.raises(ValueError, match="128-batch cap"):
        run_local_allocation(snapshot, "FRONTIER_VARIANCE", provider, "q", H1, 124)
    assert provider.work_counts["row_requests"] == 3


def test_original_three_arms_keep_semantics_after_combined_branch_execution():
    assert {arm: ARMS[arm] for arm in ("CACHED", "VARIANCE", "FRONTIER")} == {
        "CACHED": CachedGapPlannerState, "VARIANCE": VarianceGapPlannerState, "FRONTIER": FrontierGapPlannerState}
    snapshot = _snapshot()
    def execute(arm):
        return run_local_allocation(snapshot, arm, _Provider(snapshot.rows), "risk", ROOT, 3)[1]
    original = {arm: execute(arm) for arm in ("CACHED", "VARIANCE", "FRONTIER")}
    combined = execute("FRONTIER_VARIANCE")
    assert [row["kind"] for row in combined["requested_batches"]] == ["FIRST_OBSERVATION", "REPEAT_OBSERVATION", "REPEAT_OBSERVATION"]
    for arm, before in original.items():
        after = execute(arm)
        for field in ("requested_batches", "observed_batches", "gap_assessments", "final_action",
                      "lower", "upper", "initial_batches", "final_batches", "provider_counts"):
            assert after[field] == before[field]
