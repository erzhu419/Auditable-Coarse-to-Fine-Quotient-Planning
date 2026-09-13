from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_factorial_v26 as analysis
import analyze_controlled_predictive_frontier_v24 as old_analysis
from test_controlled_predictive_frontier_analysis_v24 import fixture as old_fixture
from test_controlled_predictive_repetition_analysis_v22 import evaluation


def test_pair_and_interaction_directions_use_equal_context_then_stream_means():
    fixed = {"target_key": [2, [2]], "panel": [[2, [2]]]}
    reps = []
    for index in range(2):
        wrong = {"CACHED": False, "VARIANCE": True, "FRONTIER": True, "FRONTIER_VARIANCE": index == 1}
        context = {"arms": {arm: {"evaluation": evaluation(fixed, wrong=wrong[arm])} for arm in analysis.ARMS}}
        reps.append({"replicate_index": index, "base_seed": 922001 + index, "complete": True, "contexts": [context] * 22})
    primary, streams = analysis.stream_statistics(reps)
    result = primary["target_wrong_action_rate"]
    assert result["FRONTIER_VARIANCE_minus_FRONTIER"]["mean"] == -.5
    assert result["FRONTIER_VARIANCE_minus_VARIANCE"]["mean"] == -.5
    interaction = result[analysis.INTERACTION]
    assert interaction["mean"] == -1.5 and interaction["count"] == 2
    assert interaction["standard_error"] == pytest.approx(.5) and interaction["degrees_of_freedom"] == 1
    assert primary["target_mean_local_regret"][analysis.INTERACTION]["mean"] == pytest.approx(-.15)
    assert streams[1]["comparisons"]["FRONTIER_VARIANCE_minus_CACHED"]["target_wrong_action_rate"] == 1


def fixture():
    payload, reference_v22 = old_fixture()
    reference = old_analysis.summarize(payload, reference_v22)
    payload["plan"] = json.loads((ROOT / "reports/controlled_predictive_factorial_plan_v26.json").read_text())
    for rep in payload["repetitions"]:
        for context in rep["contexts"]:
            context["arms"]["FRONTIER_VARIANCE"] = deepcopy(context["arms"]["FRONTIER"])
            offset = (rep["replicate_index"] + context["identity"]["context_index"]) % 4
            context["run_order"] = list(analysis.ARMS[offset:] + analysis.ARMS[:offset])
            for arm, row in context["arms"].items():
                target = row["evaluation"]["target"]
                target.update(selected_action="LEFT", local_true_optimal_actions=["LEFT"])
                target["actions"]["LEFT"]["batch_count"] = {"CACHED": 2, "VARIANCE": 8, "FRONTIER": 2, "FRONTIER_VARIANCE": 6}[arm]
            local = context["arms"]["FRONTIER_VARIANCE"]["local"]
            local["accounting"]["whole_run_seconds"] = 1.75
            local["accounting"]["work_counts"].update(variance_selection_calls=local["completed_batches"], variance_fallback_calls=2)
    total = analysis.costs(payload["repetitions"])
    payload["accounting"].update(local_arm_run_count=5632, reset_from_original_common_snapshot_count=5632,
        local_physical_batches=126464, local_physical_draws=32374784, local_allocation_wall_seconds=7392,
        provider_counts_by_arm={arm: total[arm]["provider_counts"] for arm in analysis.ARMS})
    return payload, reference


def test_incomplete_fourth_arm_excludes_whole_stream_and_retains_every_actual_cost():
    payload, reference = fixture()
    rep = payload["repetitions"][0]
    context = rep["contexts"][0]
    local = context["arms"]["FRONTIER_VARIANCE"]["local"]
    local["completed_batches"] -= 1
    local["final_batches"] -= 1
    local["actual_draws"] -= 256
    local.update(completed_fixed_budget=False, stop_reason="NO_ELIGIBLE_CANDIDATE")
    for provider in (local["provider_counts"], payload["accounting"]["provider_counts_by_arm"]["FRONTIER_VARIANCE"]):
        provider["row_requests"] -= 1
        provider["repeat_batch_requests"] -= 1
        provider["physical_draws"] -= 256
    payload["accounting"]["local_physical_batches"] -= 1
    payload["accounting"]["local_physical_draws"] -= 256
    context.update(paired_complete=False, status="FIXED_BUDGET_INCOMPLETE")
    rep.update(complete=False, status="REPETITION_INCOMPLETE")
    payload["complete_repetition_count"] = 63
    result = analysis.summarize(payload, reference)
    assert result["all_analysis_checks_passed"] and result["complete_stream_count"] == 63
    assert result["V24_control_metric_reproduction"]["all_passed"]
    assert len(result["incomplete_context_instances"]) == 1
    assert result["accounting"]["local_physical_draws"] == 32374784 - 256
    cost = result["all_actual_arm_costs"]["FRONTIER_VARIANCE"]
    assert cost["actual_arm_count"] == 1408 and cost["provider_counts"]["row_requests"] == 31615
    assert cost["whole_run_seconds"] == 2464


def test_actual_variance_fallback_is_separate_from_frontier_to_resampling_counter():
    payload, reference = fixture()
    result = analysis.summarize(payload, reference)
    assert result["all_analysis_checks_passed"] and result["complete_stream_count"] == 64
    cost = result["all_actual_arm_costs"]["FRONTIER_VARIANCE"]
    assert cost["allocation_transitions"] == {"frontier_to_resampling": 31616,
        "variance_selection_calls": 31616, "variance_to_balanced_fallbacks": 2816}
    points = result["complete_stream_point_estimates"]["FRONTIER_VARIANCE"]
    assert points["target_selected_row_batch_count"] == points["target_true_optimal_representative_batch_count"] == 6
    assert result["accounting"]["local_physical_draws"] == 32374784
