from collections import Counter
from copy import deepcopy
from time import perf_counter

import pytest

from acfqp.science.controlled_predictive_frontier_v24 import FrontierGapPlannerState
from acfqp.science.controlled_predictive_local_v21 import ARMS, run_local_allocation
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState
from acfqp.science.controlled_predictive_variance_v20 import VarianceGapPlannerState


def _key(horizon, rank):
    return horizon, (0,) * 5 + (rank,) + (0,) * 10


ROOT = _key(2, 1)
A, B, C = (_key(1, rank) for rank in (2, 3, 4))
END = _key(0, 1)
LOST_BOARD = tuple(1 + (i + i // 4) % 2 for i in range(16))
LOST, LOST_ABOVE = (0, LOST_BOARD), (1, LOST_BOARD)


def _snapshot(branch_probability=1.):
    state = CachedGapPlannerState(ROOT, {"risk": Query(0, 1, 0)})
    state.observe_batch(A, "LEFT", ((1., END, 0.),))
    for child in (B, C):
        state.observe_batch(child, "LEFT", ((.125, LOST, 0.), (.875, END, 0.)))
    state.observe_batch(ROOT, "LEFT", ((1., A, 0.),))
    row = ((branch_probability, B, 0.), (1 - branch_probability, C, 0.)) if branch_probability < 1 else ((1., B, 0.),)
    state.observe_batch(ROOT, "RIGHT", row)
    for action in ("DOWN", "UP"):
        state.observe_batch(ROOT, action, ((1., LOST_ABOVE, 0.),))
    assert state.select_row(ROOT, "risk") is None
    assert state.solve("risk").lower[ROOT] == state.solve("risk").upper[ROOT] == 0
    return state


@pytest.mark.parametrize("probability,expected", [(1., (B, "DOWN")), (.25, (C, "DOWN")), (.5, (B, "DOWN"))])
def test_existing_gap_unknown_frontier_uses_contribution_then_pair_order(probability, expected):
    base = _snapshot(probability)
    state = base.clone()
    state.__class__ = FrontierGapPlannerState
    before = deepcopy(state.rows), deepcopy(state.outcome_counts), state.spent_batches
    assessment = state.assess_gap(ROOT, "risk")
    assert assessment.incumbent == "LEFT" and assessment.challenger == "RIGHT"
    assessments_before = state.work_counts["gap_assessments"]
    score_queries_before = state.work_counts["gap_score_queries"]
    assert state.select_row(ROOT, "risk") == expected
    assert expected not in state.rows
    assert state.work_counts["gap_assessments"] == assessments_before
    assert state.work_counts["gap_score_queries"] == score_queries_before + 1
    assert state.work_counts["frontier_extension_selected"] == 1
    assert state.work_counts["frontier_to_balanced_fallbacks"] == 0
    assert (state.rows, state.outcome_counts, state.spent_batches) == before


def test_original_structural_candidate_has_priority_without_gap_extension(monkeypatch):
    state = FrontierGapPlannerState(ROOT, {"risk": Query(0, 1, 0)})
    expected = CachedGapPlannerState.select_row(state, ROOT, "risk")
    assert expected is not None
    def forbidden(*args, **kwargs):
        pytest.fail("original structural selection unnecessarily entered gap extension")
    monkeypatch.setattr(state, "_gap_scores", forbidden)
    monkeypatch.setattr(state, "_gap_candidates", forbidden)
    assert state.select_row(ROOT, "risk") == expected
    assert state.work_counts["frontier_original_structure_selected"] == 1
    assert state.work_counts["frontier_extension_calls"] == 0


def test_fully_observed_witness_returns_none_and_preserves_balanced_repeat_selection():
    state = _snapshot()
    state.observe_batch(B, "DOWN", ((1., END, 0.),))
    reference = state.clone()
    state.__class__ = FrontierGapPlannerState
    assert state.select_row(ROOT, "risk") is None
    assert state.work_counts["frontier_to_balanced_fallbacks"] == 1
    assert state.select_resample(ROOT, "risk", mode="BALANCED") == reference.select_resample(ROOT, "risk", mode="BALANCED")
    # Other known states still have unknown rows, but no witness reaches them.
    assert any((C, action) not in state.rows for action in state.profiles[C].legal_actions)


class _Provider:
    def __init__(self, rows):
        self.rows = dict(rows)
        self.work_counts = Counter()
        self.provider_seconds = 0.

    def sample_batch(self, key, action, index):
        started = perf_counter()
        self.work_counts.update(row_requests=1, physical_draws=256)
        self.work_counts["first_batch_requests" if index == 0 else "repeat_batch_requests"] += 1
        row = self.rows.setdefault((key, action), ((1., END, 0.),))
        self.provider_seconds += perf_counter() - started
        return row


def test_third_arm_uses_first_then_repeat_batches_with_exact_indices_and_fixed_budget():
    snapshot = _snapshot()
    before = deepcopy(snapshot.__dict__)
    endpoint, report = run_local_allocation(snapshot, "FRONTIER", _Provider(snapshot.rows), "risk", ROOT, 3)
    assert isinstance(endpoint, FrontierGapPlannerState)
    assert ARMS["CACHED"] is CachedGapPlannerState and ARMS["VARIANCE"] is VarianceGapPlannerState
    assert snapshot.__dict__ == before
    assert report["completed_batches"] == 3 and report["completed_fixed_budget"]
    assert report["actual_draws"] == report["provider_counts"]["physical_draws"] == 768
    first, *repeats = report["requested_batches"]
    assert first == {"row_key": [[B[0], list(B[1])], "DOWN"], "batch_index": 0, "kind": "FIRST_OBSERVATION"}
    assert all(row["kind"] == "REPEAT_OBSERVATION" for row in repeats)
    counts = dict(snapshot.batch_counts)
    for row in report["requested_batches"]:
        raw_key, action = row["row_key"]
        pair = (raw_key[0], tuple(raw_key[1])), action
        assert row["batch_index"] == counts.get(pair, 0)
        counts[pair] = counts.get(pair, 0) + 1
    assert endpoint.batch_counts == counts
    assert report["accounting"]["work_counts"]["frontier_extension_selected"] == 1
    assert report["accounting"]["work_counts"]["frontier_to_balanced_fallbacks"] == 2
    assert len(report["gap_assessments"]) == 3
    assert report["accounting"]["seconds_by_stage"]["structural_selection"] > 0


def test_no_positive_unknown_contribution_retains_original_no_candidate_termination():
    snapshot = CachedGapPlannerState(ROOT, {"zero": Query(0, 0, 0)})
    provider = _Provider({})
    endpoint, report = run_local_allocation(snapshot, "FRONTIER", provider, "zero", ROOT, 2)
    assert report["first_original_stop_index"] == 0
    assert report["completed_batches"] == 0 and report["stop_reason"] == "NO_ELIGIBLE_CANDIDATE"
    assert report["actual_draws"] == 0 and not provider.work_counts
    assert endpoint.spent_batches == snapshot.spent_batches
    assert report["accounting"]["work_counts"]["frontier_to_balanced_fallbacks"] == 1
