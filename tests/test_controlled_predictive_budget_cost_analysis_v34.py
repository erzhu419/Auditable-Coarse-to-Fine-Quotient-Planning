from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_budget_cost_v34 as analysis
from test_controlled_predictive_transfer_analysis_v32 import fixture as source_fixture


def fixture():
    source = source_fixture()
    plan = json.loads((ROOT / "reports/controlled_predictive_budget_cost_plan_v34.json").read_text())
    repetitions = []
    totals = {arm: {"row_requests": 0, "physical_draws": 0, "first_batch_requests": 0, "repeat_batch_requests": 0} for arm in analysis.ARMS}
    for rep in source["repetitions"]:
        contexts = []
        for context in rep["contexts"]:
            entries = []
            index = context["identity"]["context_index"]
            for budget_index, budget in enumerate(plan["budgets"]):
                arms = {}
                for arm in analysis.ARMS:
                    row = deepcopy(context["arms"][arm])
                    seconds = budget / 1000 * (1. if arm == "CACHED" else 1.2)
                    row["local"].update(completed_batches=budget, initial_batches=32, final_batches=32+budget, actual_draws=256*budget)
                    row["local"]["provider_counts"] = {"row_requests": budget, "physical_draws": 256*budget, "first_batch_requests": 0, "repeat_batch_requests": budget}
                    row["local"]["accounting"] = {"whole_run_seconds": seconds, "seconds_by_stage": {"local_work": seconds}, "work_counts": {"batches": budget}}
                    row["costs"] = {"prefix_sampling_seconds": 1., "single_query_prepare_seconds": .2,
                        "local_whole_run_seconds": seconds, "independent_query_seconds": 1.2+seconds}
                    for key in ("reference_history_validation", "reference_policy_validation", "reference_value_validation"):
                        row[key] = {"passed": True}
                    if budget == 32: row["reference_state_validation"] = {"passed": True}
                    arms[arm] = row
                    for key,value in row["local"]["provider_counts"].items(): totals[arm][key] += value
                parity = (rep["replicate_index"] + index + budget_index) % 2
                entries.append({"budget": budget, "requested_batch_count": budget, "run_order": list(analysis.ARMS[parity:]+analysis.ARMS[:parity]),
                    "arms": arms, "source_valid": True, "budget_matched": True, "paired_complete": True})
            offset = (rep["replicate_index"] + index) % len(plan["budgets"])
            contexts.append({"identity": context["identity"], "target_key": context["target_key"],
                "budget_run_order": plan["budgets"][offset:]+plan["budgets"][:offset], "budgets": entries})
        repetitions.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "contexts": contexts})
    diagnostic = {"historical_physical_batches": 492544, "historical_physical_draws": 126091264, "new_physical_draws": 0, "retained_draws_replayed": 41943040}
    reference_quality, _ = analysis.stream_statistics(source["repetitions"], analysis.policy_metrics, analysis.POLICY_METRICS)
    reference = {"checkpoint_curve": [{"supplemental_batches": budget, "quality": deepcopy(reference_quality)} for budget in plan["budgets"]],
        "original_source_accounting": source["accounting"], "accounting": diagnostic}
    account = {"prefix_board_count": 16, "prepared_query_count": 160, "prefix_physical_batches": 512, "prefix_physical_draws": 131072,
        "prefix_acquisition_seconds": 16., "single_query_preparation_seconds": 32., "local_arm_run_count": 25600,
        "local_physical_batches": 430080, "local_physical_draws": 110100480, "total_physical_batches": 430592,
        "total_physical_draws": 110231552, "historical_physical_batches": 492544, "historical_physical_draws": 126091264,
        "historical_plus_new_physical_batches": 923136, "historical_plus_new_physical_draws": 236322816,
        "local_allocation_wall_seconds": 2560*84/1000*2.2, "provider_counts_by_arm": totals,
        "endpoint_pair_records_written": 12800, "endpoint_pair_records_reloaded": 12800, "independent_new_samples": 0}
    payload = {"plan": plan, "repetitions": repetitions, "prefixes": source["prefixes"], "query_preparations": source["query_preparations"],
        "plan_binding_validation": {"passed": True}, "reference_binding_validation": {"passed": True},
        "original_source_accounting": source["accounting"], "source_diagnostic_accounting": diagnostic, "accounting": account,
        "all_prefix_snapshots_closed_before_local": True, "all_sampling_endpoints_closed_before_oracle": True,
        "all_sampling_endpoints_closed_before_reference_values": True, "endpoint_evaluation_replanning_calls": 0,
        "source_and_new_endpoint_streams_complete": True}
    return payload, reference


def test_full_curve_ten_reference_points_and_fresh_overlapping_samples_are_all_charged():
    payload, reference = fixture()
    result = analysis.summarize(payload, reference)
    assert result["all_analysis_checks_passed"]
    assert result["common_quality_complete_stream_count"] == result["common_source_cost_stream_count"] == 16
    assert len(result["budget_curve"]) == 5 and len(result["all_budgets_vs_current_CACHED_K32"]) == 10
    first = result["budget_curve"][0]
    assert first["independent_query_cost"][analysis.COMPARISON]["independent_query_seconds"]["mean"] == pytest.approx(.0008)
    short = next(point for point in result["all_budgets_vs_current_CACHED_K32"] if point["arm"] == "GAP_FRONTIER" and point["supplemental_batches"] == 24)
    assert short["quality"]["current_minus_reference"]["total_regret"]["mean"] == 0.
    assert short["independent_query_cost"]["current_minus_reference"]["independent_query_seconds"]["mean"] == pytest.approx(-.0032)
    assert short["same_quality_mask_cost"]["stream_count"] == 16
    assert short["quality"]["current_minus_reference"]["total_regret"]["degrees_of_freedom"] == 15
    assert result["all_actual_arm_costs"]["CACHED"]["provider_counts"]["physical_draws"] == 55050240
    assert result["accounting"]["total_physical_draws"] == 110231552
    assert result["accounting"]["historical_plus_new_physical_draws"] == 236322816
    assert result["all_actual_arm_costs"]["CACHED"]["attributed_cost_totals"]["prefix_sampling_seconds"] == 12800.
    assert result["accounting"]["prefix_acquisition_seconds"] == 16.


def test_missing_one_budget_evaluation_preserves_source_cost_and_other_budget_reproduction():
    payload, reference = fixture()
    for rep in payload["repetitions"]:
        entry = rep["contexts"][0]["budgets"][0]
        row = entry["arms"]["CACHED"]
        row.pop("evaluation")
        row["evaluation_validation"]["passed"] = False
        row["first_action_validation"]["passed"] = False
        row["reference_value_validation"]["passed"] = False
        entry["paired_complete"] = False
    result = analysis.summarize(payload, reference)
    assert result["common_quality_complete_stream_count"] == 0 and result["common_source_cost_stream_count"] == 16
    assert result["budget_curve"][0]["independent_query_cost"]["stream_count"] == 16
    assert not result["budget_curve"][0]["V33_quality_reproduction"]["passed"]
    assert all(point["V33_quality_reproduction"]["passed"] for point in result["budget_curve"][1:])
    assert all(point["same_quality_mask_cost"]["stream_count"] == 0 for point in result["all_budgets_vs_current_CACHED_K32"])
    assert all(point["independent_query_cost"]["stream_count"] == 16 for point in result["all_budgets_vs_current_CACHED_K32"])
    assert result["accounting"]["total_physical_draws"] == 110231552
    assert result["all_actual_arm_costs"]["CACHED"]["actual_arm_count"] == 12800


def test_history_mismatch_excludes_one_entire_cost_stream_without_refunding_any_run():
    payload, reference = fixture()
    entry = payload["repetitions"][0]["contexts"][0]["budgets"][1]
    entry["arms"]["GAP_FRONTIER"]["reference_history_validation"]["passed"] = False
    entry["arms"]["GAP_FRONTIER"]["source_valid"] = False
    entry.update(source_valid=False, paired_complete=False)
    result = analysis.summarize(payload, reference)
    assert not result["all_analysis_checks_passed"]
    assert result["common_source_cost_stream_count"] == result["common_quality_complete_stream_count"] == 15
    assert all(point["independent_query_cost"]["stream_count"] == 15 for point in result["budget_curve"])
    assert len(result["stream_statuses"]) == 16
    assert result["all_actual_arm_costs"]["GAP_FRONTIER"]["provider_counts"]["physical_draws"] == 55050240
    assert result["original_source_accounting"] == payload["original_source_accounting"]
    assert result["source_diagnostic_accounting"] == payload["source_diagnostic_accounting"]

    # A campaign-wide reference binding failure invalidates every source stream.
    payload["reference_binding_validation"]["passed"] = False
    for rep in payload["repetitions"]:
        for context in rep["contexts"]:
            for budget in context["budgets"]:
                budget.update(source_valid=False, paired_complete=False)
                for row in budget["arms"].values():
                    row["source_valid"] = False
    failed = analysis.summarize(payload, reference)
    assert failed["common_source_cost_stream_count"] == failed["common_quality_complete_stream_count"] == 0
    assert failed["checks"]["source_validity_labels"]["passed"]
    assert all(point["independent_query_cost"]["stream_count"] == 0 for point in failed["budget_curve"])
    assert failed["all_actual_arm_costs"] == result["all_actual_arm_costs"]
    assert failed["accounting"]["total_physical_draws"] == 110231552
