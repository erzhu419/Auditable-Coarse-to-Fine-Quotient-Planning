import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_projection_v23 as analysis
import analyze_controlled_predictive_repetitions_v22 as source_analysis

spec = importlib.util.spec_from_file_location("v22_analysis_fixture", ROOT / "tests/test_controlled_predictive_repetition_analysis_v22.py")
old_fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_fixture)


def test_difference_change_uses_the_paired_stream_contrast():
    fixed = {"target_key": [2, [2]], "panel": [[2, [2]]]}
    reps = []
    for r in range(2):
        values = {"FULL": {"CACHED": r == 1, "VARIANCE": r == 0},
                  "PROJECTED": {"CACHED": r == 0, "VARIANCE": True}}
        context = {"arms": {arm: {"evaluations": {model: old_fixture.evaluation(fixed, wrong=values[model][arm])
                                                    for model in analysis.MODELS}} for arm in analysis.ARMS}}
        reps.append({"replicate_index": r, "base_seed": 922001 + r, "complete": True, "contexts": [context] * 22})
    result, streams = analysis.stream_statistics(reps)
    wrong = result["target_wrong_action_rate"]
    assert len(streams) == 2
    assert wrong["allocation_difference_change"]["mean"] == 0.5
    assert wrong["allocation_difference_change"]["standard_error"] == pytest.approx(1.5)
    assert wrong["allocation_difference_change"]["degrees_of_freedom"] == 1
    assert wrong["CACHED_PROJECTED_minus_FULL"]["mean"] == 0
    assert wrong["VARIANCE_PROJECTED_minus_FULL"]["mean"] == 0.5


def fixture():
    source = old_fixture.fixture()
    for rep in source["repetitions"]:
        for context in rep["contexts"]:
            for current in context["arms"].values():
                provider = current["local"]["provider_counts"]
                provider["first_batch_requests"] = 1
                provider["repeat_batch_requests"] -= 1
                current["evaluation"]["target"]["actions"] = {action: {"observed": True,
                    "q_hat": 0.0, "q_star": 0.0, "A_transition_error": 0.0,
                    "D_continuation_error": 0.0, "total_error": 0.0} for action in ("LEFT", "RIGHT", "UP")}
    costs = source_analysis.arm_totals(source["repetitions"])
    source["accounting"]["provider_counts_by_arm"] = {arm: costs[arm]["provider_counts"] for arm in analysis.ARMS}
    reference = source_analysis.summarize(source)
    plan = json.loads((ROOT / "reports/controlled_predictive_projection_plan_v23.json").read_text())
    repetitions = []
    for rep in source["repetitions"]:
        contexts = []
        for context in rep["contexts"]:
            fixed = plan["contexts"][context["identity"]["context_index"]]
            row = {**context, "target_key": fixed["target_key"], "panel": fixed["panel"],
                   "source_paired_complete": True, "arms": {}}
            for arm in analysis.ARMS:
                current = context["arms"][arm]
                initial, n = fixed["initial_batches"], fixed["requested_batch_count"]
                projection = {"original_common_batches": initial, "original_endpoint_batches": initial + n,
                    "original_local_observation_batches": n, "retained_model_batches": initial + n - 2,
                    "retained_repeat_batches": n - 2, "retained_action_row_count": fixed["initial_observed_row_count"],
                    "masked_new_row_count": 1, "masked_observation_batches": 2, "masked_draws": 512,
                    "retained_new_successor_profile_count": 0, "removed_profile_count": 0,
                    "original_acquisition_cost_refunded": False, "new_provider_calls": 0,
                    "new_physical_draws": 0, "truth_calls": 0, "projection_seconds": 0.01,
                    "projection_work_counts": {"projection_calls": 1}}
                row["arms"][arm] = {"source_local": current["local"], "projection": projection,
                    "projection_validation": {"passed": True}, "full_control_validation": {"passed": True},
                    "evaluation_restoration": {model: {"passed": True} for model in analysis.MODELS},
                    "evaluations": {model: copy.deepcopy(current["evaluation"]) for model in analysis.MODELS}}
            contexts.append(row)
        repetitions.append({**rep, "contexts": contexts})
    return {"plan": plan, "status": "PROJECTION_COMPLETE", "repetitions": repetitions,
            "complete_repetition_count": 64, "elapsed_seconds_before_report_serialization": 1,
            "plan_binding_validation": {"passed": True}, "all_projected_endpoints_closed_before_oracle": True,
            "plan_snapshot_validation": [{"passed": True}] * 22,
            "source_actual_arm_costs": reference["all_actual_arm_costs"], "new_provider_calls": 0, "new_physical_draws": 0,
            "accounting": {"source_physical_batches": 63232, "source_physical_draws": 16187392,
                "new_provider_calls": 0, "new_physical_draws": 0,
                "projection_counts_by_arm": {arm: {"masked_new_row_count": 1408, "masked_observation_batches": 2816, "masked_draws": 720896} for arm in analysis.ARMS}},
            "restoration_validation": source["restoration_validation"]}, reference


def test_partial_projection_keeps_full_reproduction_and_all_acquisition_costs():
    payload, reference = fixture()
    context = payload["repetitions"][0]["contexts"][0]
    current = context["arms"]["VARIANCE"]
    current["projection_validation"] = {"passed": False, "reason": "fixture mismatch"}
    del current["projection"]
    del current["evaluations"]["PROJECTED"]
    context.update(paired_complete=False, status="PROJECTION_MISMATCH")
    payload["repetitions"][0].update(complete=False, status="REPETITION_INCOMPLETE")
    payload["complete_repetition_count"] = 63
    counts = payload["accounting"]["projection_counts_by_arm"]["VARIANCE"]
    counts.update(masked_new_row_count=1407, masked_observation_batches=2814, masked_draws=720384)
    result = analysis.summarize(payload, reference)
    assert result["complete_stream_count"] == 63
    assert result["FULL_reference_reproduction"]["all_passed"]
    assert result["checks"]["original_acquisition_costs_retained"]["passed"]
    assert result["retained_V22_acquisition_costs"]["VARIANCE"]["provider_counts"]["physical_draws"] == 8093696
    assert result["projection_retained_information"]["VARIANCE"]["masked_observation_batches"] == 2 * 1407
    assert len(result["incomplete_context_instances"]) == 1


def test_changed_A_or_reference_control_is_reported():
    payload, reference = fixture()
    projected = payload["repetitions"][0]["contexts"][0]["arms"]["VARIANCE"]["evaluations"]["PROJECTED"]
    projected["target"]["actions"]["LEFT"]["A_transition_error"] = 0.01
    projected["panel"]["states"][0]["selected_action_observed"] = False
    reference["contexts"][0]["point_estimates"]["CACHED"]["target_wrong_action_rate"] = 1.0
    result = analysis.summarize(payload, reference)
    assert not result["checks"]["retained_target_A_unchanged"]["passed"]
    assert not result["checks"]["FULL_reproduces_V22"]["passed"]
    assert result["complete_stream_point_estimates"]["contrasts"]["VARIANCE_PROJECTED_minus_FULL"]["panel_unobserved_selected_count"]["mean"] > 0
