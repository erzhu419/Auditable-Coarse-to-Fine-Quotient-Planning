"""Stopping consumes no batch; continued gap acquisition pays every batch."""
from dataclasses import replace

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_execution_v13 import ExactEnvironment
from acfqp.science.controlled_predictive_execution_v16 import evaluate_gap_execution
from acfqp.science.controlled_predictive_gap_v16 import GapPlannerState
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider

BOARD = (0,) * 5 + (1,) + (0,) * 10
ROOT = (1, BOARD)


def fixture(complete=True):
    state = GapPlannerState(ROOT, {"q": Query(1, 1, 0)})
    provider = BatchRowSampleProvider(71)
    if complete:
        for action in state.profiles[ROOT].legal_actions:
            state.observe_batch(ROOT, action, provider.sample(ROOT, action))
    closure = build_development_closure(horizon=1, boards={"fixture": BOARD})
    return state, ExactEnvironment.from_closure(closure)


def test_continue_and_stop_are_identical_until_a_gap_is_separated():
    state, env = fixture()
    results = [evaluate_gap_execution(state, BatchRowSampleProvider(71), "q", env,
                                     mode=mode, total_batch_cap=7) for mode in ("CONTINUE", "STOP")]
    a, b = results
    assert a["root_metrics"] == b["root_metrics"]
    for key in ("requested_batches", "observed_batches", "gap_assessments", "batches_after", "action"):
        assert a["trace"][key] == b["trace"][key]
    assert all(not x["separated"] for x in a["trace"]["gap_assessments"])
    for r in results:
        assert r["deployment"]["maximum_total_batches"] == 7
        assert r["deployment"]["expected_total_distinct_rows"] == 4
        assert r["physical_audit"]["provider_counts"]["physical_draws"] == 768
    assert state.spent_batches == 4


def test_only_stop_consumes_separation_signal_before_structural_acquisition(monkeypatch):
    state, env = fixture(complete=False)
    original = GapPlannerState.assess_gap
    # Isolate consumption of the diagnostic; the core tests derive separation.
    monkeypatch.setattr(GapPlannerState, "assess_gap", lambda self, *args:
                        replace(original(self, *args), separated=True, gap=0.0))
    stopped = evaluate_gap_execution(state, BatchRowSampleProvider(71), "q", env,
                                     mode="STOP", total_batch_cap=1)
    continued = evaluate_gap_execution(state, BatchRowSampleProvider(71), "q", env,
                                       mode="CONTINUE", total_batch_cap=1)
    assert stopped["trace"]["acquisition_stop_reason"] == "HEURISTIC_GAP_SEPARATED"
    assert stopped["deployment"]["maximum_total_batches"] == 0
    assert stopped["trace"]["unresolved"]
    assert continued["deployment"]["maximum_total_batches"] == 1
    assert continued["trace"]["requested_batches"][0]["selection"] == "STRUCTURAL_FRONTIER"
    assert continued["trace"]["requested_batches"][0]["batch_index"] == 0
    assert stopped["deployment"]["expected_seconds_by_stage"]["gap_assessment"] > 0


def test_unknown_gap_frontier_is_a_first_batch_after_empirical_closure():
    state, env = fixture(complete=False)
    state.observe_batch(ROOT, "RIGHT", BatchRowSampleProvider(71).sample(ROOT, "RIGHT"))
    assert state.select_row(ROOT, "q") is None
    result = evaluate_gap_execution(state, BatchRowSampleProvider(71), "q", env,
                                    mode="STOP", total_batch_cap=2)
    request = result["trace"]["requested_batches"][0]
    assert request["selection"] == "GAP_FRONTIER"
    assert request["kind"] == "FIRST_OBSERVATION" and request["batch_index"] == 0
    assert result["deployment"]["expected_total_batches"] == result["deployment"]["expected_total_distinct_rows"] == 2


def test_empty_candidates_do_not_masquerade_as_separation(monkeypatch):
    state, env = fixture()
    original = GapPlannerState.assess_gap
    monkeypatch.setattr(GapPlannerState, "assess_gap", lambda self, *args:
                        replace(original(self, *args), pair=None, candidate_count=0))
    result = evaluate_gap_execution(state, BatchRowSampleProvider(71), "q", env, total_batch_cap=7)
    assert result["trace"]["acquisition_stop_reason"] == "NO_ELIGIBLE_CANDIDATE"
    assert not result["trace"]["gap_assessments"][0]["separated"]
    assert result["deployment"]["expected_total_batches"] == 4
