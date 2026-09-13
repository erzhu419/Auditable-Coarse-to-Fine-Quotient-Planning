"""Balanced acquisition stays fixed while the gap diagnostic can stop a batch."""

from dataclasses import replace

import pytest

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_execution_v13 import ExactEnvironment
from acfqp.science.controlled_predictive_execution_v15 import evaluate_resampling_execution
from acfqp.science.controlled_predictive_execution_v17 import evaluate_balanced_gap_execution
from acfqp.science.controlled_predictive_gap_v16 import GapPlannerState
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider

BOARD = (0,) * 5 + (1,) + (0,) * 10
NEAR_FULL = (1, 1, 3, 3, 5, 6, 7, 8, 9, 3, 4, 5, 6, 7, 8, 9)


def fixture(complete=True, horizon=1, query=Query(1, 1, 0)):
    board = BOARD if horizon == 1 else NEAR_FULL
    root = horizon, board
    state = GapPlannerState(root, {"q": query})
    provider = BatchRowSampleProvider(71)
    if complete:
        for action in state.profiles[root].legal_actions:
            state.observe_batch(root, action, provider.sample(root, action))
    closure = build_development_closure(horizon=horizon, boards={"fixture": board})
    return state, ExactEnvironment.from_closure(closure)


def without_diagnostics(trace):
    """Keep every original V15 trace field, including children and observations."""
    return {key: ([{**edge, "node": without_diagnostics(edge["node"])} for edge in value]
                  if key == "children" else value)
            for key, value in trace.items() if key not in {"gap_assessments", "decision_kind"}}


def decision_nodes(trace):
    if "action" in trace:
        yield trace
        for edge in trace["children"]:
            yield from decision_nodes(edge["node"])


@pytest.mark.parametrize("complete", [False, True])
def test_continue_exactly_reproduces_v15_balanced_on_every_history(complete):
    state, environment = fixture(complete=complete, horizon=2)
    initial_batches, initial_work = state.spent_batches, dict(state.work_counts)
    original = evaluate_resampling_execution(state, BatchRowSampleProvider(71), "q", environment,
                                            mode="BALANCED", total_batch_cap=7)
    result = evaluate_balanced_gap_execution(state, BatchRowSampleProvider(71), "q", environment,
                                            mode="CONTINUE", total_batch_cap=7)
    assert without_diagnostics(result["trace"]) == without_diagnostics(original["trace"])
    assert result["root_metrics"] == original["root_metrics"]
    assert result["physical_audit"]["provider_counts"] == original["physical_audit"]["provider_counts"]
    for name in ("expected_total_batches", "maximum_total_batches", "expected_total_draws", "maximum_total_draws"):
        assert result["deployment"][name] == original["deployment"][name]
    assert result["deployment"]["maximum_total_batches"] <= 7
    assert result["deployment"]["expected_seconds_by_stage"]["gap_assessment"] > 0
    assert state.spent_batches == initial_batches and dict(state.work_counts) == initial_work


def test_gap_candidate_cannot_change_balanced_allocation(monkeypatch):
    state, environment = fixture()
    expected = evaluate_resampling_execution(state, BatchRowSampleProvider(71), "q", environment,
                                            mode="BALANCED", total_batch_cap=7)
    original = GapPlannerState.assess_gap
    monkeypatch.setattr(GapPlannerState, "assess_gap", lambda self, *args:
                        replace(original(self, *args), pair=None, candidate_count=0, separated=False))
    results = [evaluate_balanced_gap_execution(state, BatchRowSampleProvider(71), "q", environment,
                                             mode=mode, total_batch_cap=7)
               for mode in ("CONTINUE", "STOP")]
    for result in results:
        assert without_diagnostics(result["trace"]) == without_diagnostics(expected["trace"])
        assert result["root_metrics"] == expected["root_metrics"]
        assert result["deployment"]["expected_total_batches"] == 7
        assert result["deployment"]["expected_total_distinct_rows"] == 4
        assert result["physical_audit"]["provider_counts"]["physical_draws"] == 768
        assert all(item["kind"] == "REPEAT_OBSERVATION" and item["batch_index"] >= 1
                   for item in result["trace"]["requested_batches"])
    assert results[0]["trace"]["gap_assessments"] == results[1]["trace"]["gap_assessments"]


def test_only_stop_consumes_separation_before_structural_acquisition(monkeypatch):
    state, environment = fixture(complete=False)
    original = GapPlannerState.assess_gap
    monkeypatch.setattr(GapPlannerState, "assess_gap", lambda self, *args:
                        replace(original(self, *args), separated=True, gap=0.0))
    stopped = evaluate_balanced_gap_execution(state, BatchRowSampleProvider(71), "q", environment,
                                             mode="STOP", total_batch_cap=1)
    continued = evaluate_balanced_gap_execution(state, BatchRowSampleProvider(71), "q", environment,
                                               mode="CONTINUE", total_batch_cap=1)
    assert stopped["trace"]["acquisition_stop_reason"] == "HEURISTIC_GAP_SEPARATED"
    assert stopped["deployment"]["maximum_total_batches"] == 0
    assert stopped["trace"]["unresolved"]
    assert continued["deployment"]["maximum_total_batches"] == 1
    assert continued["trace"]["requested_batches"][0]["kind"] == "FIRST_OBSERVATION"
    assert continued["trace"]["requested_batches"][0]["batch_index"] == 0
    assert continued["trace"]["acquisition_stop_reason"] == "TOTAL_SAMPLE_CAP_EXHAUSTED"


def test_stop_is_reassessed_after_actual_child_is_reached(monkeypatch):
    state, environment = fixture(complete=False, horizon=2)
    original = GapPlannerState.assess_gap
    def root_only(self, key, query):
        return replace(original(self, key, query), separated=key == state.root)
    monkeypatch.setattr(GapPlannerState, "assess_gap", root_only)
    result = evaluate_balanced_gap_execution(state, BatchRowSampleProvider(71), "q", environment,
                                            mode="STOP", total_batch_cap=4)
    nodes = list(decision_nodes(result["trace"]))
    assert nodes[0]["acquisition_stop_reason"] == "HEURISTIC_GAP_SEPARATED"
    assert nodes[0]["requested_batches"] == []
    assert len(nodes) > 1 and any(node["requested_batches"] for node in nodes[1:])
    for node in nodes[1:]:
        assert node["gap_assessments"] and not node["gap_assessments"][0]["separated"]
        assert node["batches_before"] == 0  # Sibling samples stay history-local.
    for node in nodes:
        assert node["batches_after"] <= 4
        assert node["quota"] == (4 - node["batches_before"]) // node["key"][0]
        assert len(node["requested_batches"]) <= node["quota"]
    assert 0 < result["deployment"]["expected_total_batches"] <= result["deployment"]["maximum_total_batches"] <= 4
    assert state.spent_batches == 0


def test_empty_balanced_candidates_have_the_original_stop_reason():
    state, environment = fixture(query=Query(0, 0, 0))
    result = evaluate_balanced_gap_execution(state, BatchRowSampleProvider(71), "q", environment,
                                            mode="CONTINUE", total_batch_cap=7)
    assert result["trace"]["gap_assessments"][0]["separated"]
    assert result["trace"]["acquisition_stop_reason"] == "NO_POSITIVE_RANGE_OBSERVED_CANDIDATE"
    assert result["deployment"]["expected_total_batches"] == 4
    assert not result["physical_audit"]["provider_counts"]
