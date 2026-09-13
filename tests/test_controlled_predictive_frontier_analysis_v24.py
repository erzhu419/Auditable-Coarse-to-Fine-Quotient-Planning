import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_frontier_v24 as analysis
import analyze_controlled_predictive_repetitions_v22 as old_analysis

spec = importlib.util.spec_from_file_location("v22_frontier_fixture", ROOT / "tests/test_controlled_predictive_repetition_analysis_v22.py")
old_fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_fixture)


def test_three_comparisons_use_stream_means_in_the_declared_direction():
    fixed = {"target_key": [2, [2]], "panel": [[2, [2]]]}
    reps = []
    for index in range(2):
        wrong = {"CACHED": False, "VARIANCE": True, "FRONTIER": index == 0}
        context = {"arms": {arm: {"evaluation": old_fixture.evaluation(fixed, wrong=wrong[arm])} for arm in analysis.ARMS}}
        reps.append({"replicate_index": index, "base_seed": 922001 + index, "complete": True, "contexts": [context] * 22})
    primary, _ = analysis.stream_statistics(reps)
    result = primary["target_wrong_action_rate"]
    assert result["FRONTIER_minus_CACHED"]["mean"] == 0.5
    assert result["FRONTIER_minus_VARIANCE"]["mean"] == -0.5
    assert result["VARIANCE_minus_CACHED"]["mean"] == 1.0
    assert result["FRONTIER_minus_CACHED"]["standard_error"] == pytest.approx(0.5)
    assert result["FRONTIER_minus_CACHED"]["count"] == 2
    assert result["FRONTIER_minus_CACHED"]["degrees_of_freedom"] == 1


def fixture():
    payload = old_fixture.fixture()
    reference = old_analysis.summarize(payload)
    payload["plan"] = json.loads((ROOT / "reports/controlled_predictive_frontier_plan_v24.json").read_text())
    payload["plan_binding_validation"] = {"passed": True}
    payload["source_reference_validation"] = {"all_passed": True}
    for rep in payload["repetitions"]:
        for context in rep["contexts"]:
            context["arms"]["FRONTIER"] = copy.deepcopy(context["arms"]["CACHED"])
            index = context["identity"]["context_index"]
            offset = (rep["replicate_index"] + index) % 3
            context["run_order"] = list(analysis.ARMS[offset:] + analysis.ARMS[:offset])
            for arm, current in context["arms"].items():
                current["source_reference_validation"] = {"passed": True, "applicable": arm != "FRONTIER"}
                current["local"]["repeat_batches_on_rows_absent_from_common"] = 0
            frontier = context["arms"]["FRONTIER"]["local"]
            frontier["accounting"]["whole_run_seconds"] = 1.5
            n = frontier["completed_batches"]
            frontier["accounting"]["work_counts"].update(frontier_selection_calls=n,
                frontier_extension_calls=n, frontier_to_balanced_fallbacks=n,
                frontier_original_structure_selected=0, frontier_extension_selected=0)
    total = analysis.costs(payload["repetitions"])
    payload["accounting"].update(local_arm_run_count=4224, reset_from_original_common_snapshot_count=4224,
        local_physical_batches=94848, local_physical_draws=24281088,
        local_allocation_wall_seconds=4928,
        provider_counts_by_arm={arm: total[arm]["provider_counts"] for arm in analysis.ARMS})
    return payload, reference


def test_incomplete_frontier_excludes_whole_stream_and_retains_all_three_costs():
    payload, reference = fixture()
    context = payload["repetitions"][0]["contexts"][0]
    local = context["arms"]["FRONTIER"]["local"]
    local["completed_batches"] -= 1
    local["final_batches"] -= 1
    local["actual_draws"] -= 256
    local.update(completed_fixed_budget=False, stop_reason="NO_ELIGIBLE_CANDIDATE")
    local["provider_counts"]["row_requests"] -= 1
    local["provider_counts"]["repeat_batch_requests"] -= 1
    local["provider_counts"]["physical_draws"] -= 256
    context.update(paired_complete=False, status="FIXED_BUDGET_INCOMPLETE")
    payload["repetitions"][0].update(complete=False, status="REPETITION_INCOMPLETE")
    payload["complete_repetition_count"] = 63
    payload["accounting"]["local_physical_batches"] -= 1
    payload["accounting"]["local_physical_draws"] -= 256
    counts = payload["accounting"]["provider_counts_by_arm"]["FRONTIER"]
    counts["row_requests"] -= 1
    counts["repeat_batch_requests"] -= 1
    counts["physical_draws"] -= 256
    result = analysis.summarize(payload, reference)
    assert result["all_analysis_checks_passed"]
    assert result["complete_stream_count"] == 63
    assert result["V22_control_metric_reproduction"]["all_passed"]
    assert result["all_actual_arm_costs"]["FRONTIER"]["provider_counts"]["row_requests"] == 31615
    assert result["all_actual_arm_costs"]["FRONTIER"]["actual_arm_count"] == 1408
    assert result["all_actual_arm_costs"]["FRONTIER"]["whole_run_seconds"] == 2112
    assert len(result["incomplete_context_instances"]) == 1


def test_historical_trace_failure_blocks_primary_even_when_metrics_match():
    payload, reference = fixture()
    context = payload["repetitions"][0]["contexts"][0]
    context["arms"]["CACHED"]["source_reference_validation"] = {"passed": False, "reason": "fixture request mismatch"}
    context.update(paired_complete=False, status="SOURCE_REFERENCE_MISMATCH")
    payload["repetitions"][0].update(complete=False, status="REPETITION_INCOMPLETE")
    payload["complete_repetition_count"] = 63
    payload["source_reference_validation"]["all_passed"] = False
    result = analysis.summarize(payload, reference)
    assert result["V22_control_metric_reproduction"]["all_passed"]
    assert result["complete_stream_count"] == 63
    assert result["checks"]["old_control_trace_reproduction"]["failed"] == 1
    assert result["checks"]["total_physical_work"]["passed"]
