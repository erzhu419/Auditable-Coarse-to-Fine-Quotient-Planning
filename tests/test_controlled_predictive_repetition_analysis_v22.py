import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("repetition_analysis_v22", ROOT / "scripts/analyze_controlled_predictive_repetitions_v22.py")
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def evaluation(fixed, wrong=False):
    states = [{"key": key, "selected_action_observed": True, "interval_closed": True}
              for key in fixed["panel"]]
    return {"target": {"target_key": fixed["target_key"],
        "selected_action_in_true_optimal_set": not wrong, "local_regret": 0.1 if wrong else 0.0,
        "selected_action_observed": True, "interval_closed": True,
        "identities_pass": True, "maximum_absolute_identity_residual": 0.0,
        "actions": {"LEFT": {"observed": True, "A_transition_error": 0.0,
                             "D_continuation_error": 0.0, "total_error": 0.0}}, "pair_margins": []},
        "panel": {"states": states, "state_count": len(states), "selected_optimal_count": len(states),
                  "sum_local_regret": 0.0}}


def test_intervals_use_stream_means_not_the_context_instance_count():
    fixed = {"target_key": [2, [2]], "panel": [[2, [2]]]}
    reps = []
    for r in range(2):
        contexts = [{"arms": {arm: {"evaluation": evaluation(fixed, wrong=(r == 0 and arm == "VARIANCE" and i < 11) or (r == 1 and arm == "CACHED"))}
                              for arm in analysis.ARMS}} for i in range(22)]
        reps.append({"complete": True, "contexts": contexts})
    result = analysis.primary_statistics(reps)["target_wrong_action_rate"]["VARIANCE_minus_CACHED"]
    assert result["count"] == 2
    assert result["mean"] == -0.25
    assert result["standard_deviation"] == pytest.approx(math.sqrt(1.125))
    assert result["standard_error"] == pytest.approx(0.75)
    assert result["degrees_of_freedom"] == 1
    assert result["confidence_interval_95"] == pytest.approx([-9.779653552324, 9.279653552324])


def fixture():
    plan = json.loads((ROOT / "reports/controlled_predictive_repetition_plan_v22.json").read_text())
    initial = [{"identity": {k: row.get(k) for k in analysis.IDENTITY_FIELDS}, **evaluation(row)} for row in plan["contexts"]]
    reps = []
    for repetition in plan["replicates"]:
        contexts = []
        for fixed in plan["contexts"]:
            n, initial_batches = fixed["requested_batch_count"], fixed["initial_batches"]
            local = {"requested_batch_count": n, "completed_batches": n, "initial_batches": initial_batches,
                "initial_batches_matches_common": True, "final_batches": initial_batches + n,
                "actual_draws": 256 * n, "completed_fixed_budget": True,
                "stop_reason": "FIXED_BATCH_BUDGET_COMPLETE", "first_original_stop_index": None,
                "provider_counts": {"row_requests": n, "physical_draws": 256 * n,
                                    "first_batch_requests": 0, "repeat_batch_requests": n},
                "accounting": {"seconds_by_stage": {"resampling_selection": 0.2},
                               "work_counts": {"branch_clones": 1}, "whole_run_seconds": 1.0}}
            index = fixed["context_index"]
            contexts.append({"identity": {k: fixed.get(k) for k in analysis.IDENTITY_FIELDS},
                "requested_batch_count": n, "initial_batches": initial_batches,
                "run_order": list(analysis.ARMS if (repetition["replicate_index"] + index) % 2 == 0 else reversed(analysis.ARMS)),
                "paired_complete": True, "status": "PAIR_COMPLETE", "initial_snapshot_validation": {"passed": True},
                "arms": {arm: {"local": copy.deepcopy(local), "first_request_validation": {"passed": True},
                               "endpoint_restoration": {"passed": True}, "evaluation": evaluation(fixed)} for arm in analysis.ARMS}})
        reps.append({**repetition, "complete": True, "status": "REPETITION_COMPLETE", "contexts": contexts})
    totals = analysis.arm_totals(reps)
    return {"plan": plan, "status": "REPETITIONS_COMPLETE", "repetitions": reps, "initial_evaluations": initial,
        "all_sampling_endpoints_closed_before_oracle": True, "endpoint_reload_uses_provider": False,
        "restoration_validation": {"contexts": [{"context_index": i, "status": "READY"} for i in range(22)], "all_passed": True},
        "plan_snapshot_validation": [{"context_index": i, "passed": True} for i in range(22)],
        "complete_repetition_count": 64, "elapsed_seconds_before_report_serialization": 1.0,
        "accounting": {"local_arm_run_count": 2816, "reset_from_original_common_snapshot_count": 2816,
            "warm_provider_calls": 0, "warm_physical_draws": 0, "local_physical_batches": 63232,
            "local_physical_draws": 16187392, "local_allocation_wall_seconds": 2816,
            "provider_counts_by_arm": {arm: totals[arm]["provider_counts"] for arm in analysis.ARMS}}}


def test_one_incomplete_identity_excludes_its_whole_stream_but_keeps_all_work():
    payload = fixture()
    context = payload["repetitions"][0]["contexts"][0]
    local = context["arms"]["VARIANCE"]["local"]
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
    provider = payload["accounting"]["provider_counts_by_arm"]["VARIANCE"]
    provider["row_requests"] -= 1
    provider["repeat_batch_requests"] -= 1
    provider["physical_draws"] -= 256
    result = analysis.summarize(payload)
    assert result["all_analysis_checks_passed"]
    assert result["primary"]["complete_replicate_count"] == 63
    assert all(row["point_estimates"]["paired_context_instances"] == 63 for row in result["contexts"])
    assert len(result["incomplete_context_instances"]) == 1
    assert result["all_actual_arm_costs"]["VARIANCE"]["provider_counts"]["row_requests"] == 31615
    assert result["all_actual_arm_costs"]["VARIANCE"]["actual_arm_count"] == 1408


def test_failed_endpoint_restoration_cannot_enter_primary_and_is_still_charged():
    payload = fixture()
    context = payload["repetitions"][0]["contexts"][0]
    current = context["arms"]["VARIANCE"]
    current["endpoint_restoration"] = {"passed": False, "reason": "fixture mismatch"}
    del current["evaluation"]
    context.update(paired_complete=False, status="ENDPOINT_RESTORATION_MISMATCH")
    payload["repetitions"][0].update(complete=False, status="REPETITION_INCOMPLETE")
    payload["complete_repetition_count"] = 63
    result = analysis.summarize(payload)
    assert result["primary"]["complete_replicate_count"] == 63
    assert result["checks"]["endpoint_restoration"]["failed"] == 1
    assert result["checks"]["total_physical_work"]["passed"]
    assert result["all_actual_arm_costs"]["VARIANCE"]["provider_counts"]["physical_draws"] == 8093696
