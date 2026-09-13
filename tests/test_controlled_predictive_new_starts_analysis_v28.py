from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_new_starts_v28 as analysis


def evaluation(total=0.):
    return {"policy_evaluable": True, "v_pi": 1. - total, "v_star": 1., "total_regret": total,
        "first_action_regret": total, "continuation_regret": 0., "defined_continuation_regret": 0.,
        "first_action_wrong": total > 1e-10, "missing_probability": 0., "weighted_unobserved_choices": .1,
        "terminal_probability": 1., "reach_probability_pass": True, "identities_pass": True,
        "missing_policy_frontier": []}


def test_quality_and_cost_differences_average_queries_then_boards_then_streams():
    reps = []
    for index in range(2):
        contexts = []
        for board in range(16):
            for query in range(10):
                rows = {}
                for arm in analysis.ARMS:
                    total = 1. if index == 0 and board == 0 and arm == "VARIANCE" else .2 if index == 1 and arm == "CACHED" else 0.
                    local = .1 if arm == "CACHED" else .12
                    rows[arm] = {"evaluation": evaluation(total), "costs": {"prefix_sampling_seconds": 1.,
                        "single_query_prepare_seconds": .2, "local_whole_run_seconds": local,
                        "independent_query_seconds": 1.2 + local}}
                contexts.append({"identity": {"board_index": board, "query_name": str(query)}, "arms": rows})
        reps.append({"replicate_index": index, "base_seed": 942001 + index, "contexts": contexts})
    quality, _ = analysis.stream_statistics(reps, analysis.policy_metrics, ("total_regret",))
    difference = quality["VARIANCE_minus_CACHED"]["total_regret"]
    assert difference["mean"] == pytest.approx((1/16 - .2)/2)
    assert difference["count"] == 2 and difference["degrees_of_freedom"] == 1
    assert difference["standard_error"] == pytest.approx((1/16 + .2)/2)
    costs, _ = analysis.stream_statistics(reps, analysis.cost_metrics, analysis.COST_METRICS)
    assert costs["VARIANCE_minus_CACHED"]["independent_query_seconds"]["mean"] == pytest.approx(.02)
    assert costs["arms"]["CACHED"]["independent_query_seconds"]["mean"] == 1.3


@pytest.mark.parametrize("left,right,left_reason,right_reason,expected", [
    (0, 0, "NO_ELIGIBLE_CANDIDATE", "NO_ELIGIBLE_CANDIDATE", True),
    (12, 12, "NO_ELIGIBLE_CANDIDATE", "NO_ELIGIBLE_CANDIDATE", True),
    (12, 11, "NO_ELIGIBLE_CANDIDATE", "NO_ELIGIBLE_CANDIDATE", False),
    (0, 0, "EXCEPTION", "EXCEPTION", False),
    (32, 32, "FIXED_BATCH_BUDGET_COMPLETE", "FIXED_BATCH_BUDGET_COMPLETE", True)])
def test_matched_actual_budget_accepts_only_shared_normal_stops_or_complete_K(left, right, left_reason, right_reason, expected):
    context = {"requested_batch_count": 32, "arms": {arm: {"local": {"completed_batches": n,
        "completed_fixed_budget": n == 32, "stop_reason": reason}} for arm, n, reason in zip(analysis.ARMS, (left, right), (left_reason, right_reason))}}
    matched, label = analysis.matched_budget(context)
    assert matched == expected
    if expected and left < 32:
        assert label == "shared_normal_stop"


def fixture():
    plan = json.loads((ROOT / "reports/controlled_predictive_new_starts_plan_v28.json").read_text())
    prefixes = [{"board_index": b["board_index"], "name": b["name"], "prefix_seed": b["prefix_seed"],
        "validation": {"passed": True}, "accounting": {"whole_seconds": 1., "physical_batches": 32,
            "physical_draws": 8192, "provider_counts": {"row_requests": 32, "physical_draws": 8192}}} for b in plan["boards"]]
    preparations = [{"identity": {key: c[key] for key in analysis.IDENTITY_FIELDS}, "validation": {"passed": True},
        "accounting": {"whole_seconds": .2, "current_query": c["query_name"], "prepared_query_count": 1,
            "replayed_batches": 32, "retained_model_batches": 32, "new_provider_calls": 0, "new_physical_draws": 0}} for c in plan["contexts"]]
    contexts = []
    for c in plan["contexts"]:
        arms = {}
        for arm, seconds in zip(analysis.ARMS, (.1, .12)):
            arms[arm] = {"source_validation": {"passed": True}, "source_valid": True, "completed_requested_budget": True,
                "evaluation": evaluation(), "evaluation_validation": {"passed": True}, "first_action_validation": {"passed": True},
                "local": {"completed_batches": 32, "initial_batches": 32, "final_batches": 64,
                    "actual_draws": 8192, "completed_fixed_budget": True, "stop_reason": "FIXED_BATCH_BUDGET_COMPLETE",
                    "first_original_stop_index": None, "repeat_batches_on_rows_absent_from_common": 0,
                    "provider_counts": {"row_requests": 32, "physical_draws": 8192, "first_batch_requests": 0, "repeat_batch_requests": 32},
                    "accounting": {"whole_run_seconds": seconds, "seconds_by_stage": {"selection": seconds}, "work_counts": {"clone": 1}}},
                "costs": {"prefix_sampling_seconds": 1., "single_query_prepare_seconds": .2,
                    "local_whole_run_seconds": seconds, "independent_query_seconds": 1.2 + seconds}}
        contexts.append({"identity": {key: c[key] for key in analysis.IDENTITY_FIELDS},
            **{key: c[key] for key in ("target_key", "requested_batch_count", "initial_batches")},
            "source_valid": True, "budget_matched": True, "paired_complete": True, "status": "PAIR_COMPLETE", "arms": arms})
    repetitions = []
    for rep in plan["replicates"]:
        rows = deepcopy(contexts)
        for c in rows:
            offset = (rep["replicate_index"] + c["identity"]["context_index"]) % 2
            c["run_order"] = list(analysis.ARMS[offset:] + analysis.ARMS[:offset])
        repetitions.append({**rep, "contexts": rows, "source_valid": True, "budget_matched": True, "complete": True, "status": "REPETITION_COMPLETE"})
    provider = {"row_requests": 81920, "physical_draws": 20971520, "first_batch_requests": 0, "repeat_batch_requests": 81920}
    return {"plan": plan, "prefixes": prefixes, "query_preparations": preparations, "repetitions": repetitions,
        "status": "NEW_STARTS_COMPLETE", "source_valid_repetition_count": 16, "complete_repetition_count": 16,
        "budget_counts": {"completed_K_pair": 2560, "shared_normal_stop_pair": 0, "unequal_budget_pair": 0},
        "all_sampling_endpoints_closed_before_oracle": True, "all_prefix_snapshots_closed_before_local": True,
        "endpoint_evaluation_replanning_calls": 0, "elapsed_seconds_before_report_serialization": 1.,
        "accounting": {"prefix_board_count": 16, "prepared_query_count": 160,
            "prefix_physical_batches": 512, "prefix_physical_draws": 131072,
            "prefix_acquisition_seconds": 16., "single_query_preparation_seconds": 32.,
            "local_arm_run_count": 5120, "reset_from_prepared_query_count": 5120,
            "local_physical_batches": 163840, "local_physical_draws": 41943040, "local_allocation_wall_seconds": 563.2,
            "provider_counts_by_arm": {arm: deepcopy(provider) for arm in analysis.ARMS},
            "total_physical_batches": 164352, "total_physical_draws": 42074112,
            "endpoint_pair_records_written": 2560, "endpoint_pair_records_reloaded": 2560, "evaluation_seconds": .3}}


def test_matching_zero_batch_stops_keep_quality_and_fully_attributed_independent_costs():
    payload = fixture()
    context = payload["repetitions"][0]["contexts"][0]
    for arm, row in context["arms"].items():
        row["completed_requested_budget"] = False
        local = row["local"]
        local.update(completed_batches=0, final_batches=32, actual_draws=0, completed_fixed_budget=False, stop_reason="NO_ELIGIBLE_CANDIDATE")
        local["provider_counts"] = {key: 0 for key in local["provider_counts"]}
        totals = payload["accounting"]["provider_counts_by_arm"][arm]
        totals["row_requests"] -= 32; totals["repeat_batch_requests"] -= 32; totals["physical_draws"] -= 8192
    for key in ("local_physical_batches", "total_physical_batches"):
        payload["accounting"][key] -= 64
    for key in ("local_physical_draws", "total_physical_draws"):
        payload["accounting"][key] -= 16384
    payload["budget_counts"].update(completed_K_pair=2559, shared_normal_stop_pair=1)
    result = analysis.summarize(payload)
    assert result["all_analysis_checks_passed"]
    assert result["quality_complete_stream_count"] == result["source_valid_stream_count"] == 16
    assert result["actual_budget_pair_counts"]["shared_normal_stop"] == 1
    assert result["primary_independent_query_cost"]["arms"]["CACHED"]["independent_query_seconds"]["mean"] == 1.3
    assert result["all_actual_arm_costs"]["CACHED"]["attributed_cost_totals"]["prefix_sampling_seconds"] == 2560
    assert result["accounting"]["prefix_acquisition_seconds"] == 16
    assert result["accounting"]["total_physical_draws"] == 42074112 - 16384


def test_missing_policies_can_remove_every_quality_stream_without_dropping_cost_or_continuous_diagnostics():
    payload = fixture()
    for rep in payload["repetitions"]:
        context = rep["contexts"][0]
        value = context["arms"]["VARIANCE"]["evaluation"]
        value.update(policy_evaluable=False, v_pi=None, total_regret=None, continuation_regret=None,
            missing_probability=.25, terminal_probability=.75, identities_pass=None,
            first_action_regret=.1, defined_continuation_regret=.2)
        context.update(paired_complete=False, status="POLICY_EVALUATION_INCOMPLETE")
        rep.update(complete=False, status="REPETITION_RETAINED_WITH_INCOMPLETE_QUALITY")
    payload["complete_repetition_count"] = 0
    result = analysis.summarize(payload)
    assert result["all_analysis_checks_passed"]
    assert result["quality_complete_stream_count"] == 0
    assert result["primary_quality"]["VARIANCE_minus_CACHED"]["total_regret"]["mean"] is None
    assert result["source_valid_stream_count"] == result["diagnostic_valid_stream_count"] == 16
    assert result["primary_independent_query_cost"]["stream_count"] == 16
    assert result["continuous_diagnostics"]["arms"]["VARIANCE"]["defined_regret_lower_bound"]["mean"] == pytest.approx(.3/160)
    assert "improved" not in result["continuous_diagnostics"]["VARIANCE_minus_CACHED"]["defined_regret_lower_bound"]
    assert len(result["incomplete_context_instances"]) == 16
    assert result["all_actual_arm_costs"]["VARIANCE"]["actual_arm_count"] == 2560
    assert result["accounting"]["total_physical_draws"] == 42074112 and result["accounting"]["evaluation_seconds"] == .3
