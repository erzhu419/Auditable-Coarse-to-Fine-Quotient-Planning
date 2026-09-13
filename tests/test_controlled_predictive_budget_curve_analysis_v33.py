from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_budget_curve_v33 as analysis
import analyze_controlled_predictive_transfer_v32 as source_analysis
from test_controlled_predictive_transfer_analysis_v32 import fixture as source_fixture


def fixture():
    source = source_fixture()
    reference = source_analysis.summarize(source)
    plan = json.loads((ROOT / "reports/controlled_predictive_budget_curve_plan_v33.json").read_text())
    repetitions = []
    for rep in source["repetitions"]:
        contexts = []
        for context in rep["contexts"]:
            arms = {}
            for arm, row in context["arms"].items():
                arms[arm] = {"source_valid": True, "prefix_context_index": context["identity"]["context_index"], **{key: {"passed": True} for key in analysis.SOURCE_VALIDATIONS},
                    "reference_value_validation": {"passed": True}, "original_costs": row["costs"],
                    "original_local_accounting": row["local"]["accounting"], "accounting": {},
                    "checkpoints": [{"budget": budget, "spent_batches": 32+budget, "evaluation": deepcopy(row["evaluation"]),
                        "evaluation_validation": {"passed": True}, "policy_evaluable": True} for budget in plan["checkpoints"]]}
            contexts.append({"identity": context["identity"], "arms": arms})
        repetitions.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "contexts": contexts})
    prefix_evaluations = [{"context_index": context["identity"]["context_index"], "identity": context["identity"],
        "checkpoint": deepcopy(context["arms"]["CACHED"]["checkpoints"][0])} for context in repetitions[0]["contexts"]]
    return {"plan": plan, "repetitions": repetitions, "original_source_accounting": source["accounting"],
        "prefix_evaluations": prefix_evaluations, "plan_binding_validation": {"passed": True}, "source_endpoint_stream_complete": True,
        "oracle_used_for_replay_selection": False, "endpoint_evaluation_replanning_calls": 0,
        "accounting": {"new_provider_calls": 0, "new_sampling_calls": 0, "new_physical_draws": 0,
            "retained_batches_replayed": 163840, "retained_draws_replayed": 41943040,
            "prefix_policy_evaluation_calls": 160, "checkpoint_policy_evaluation_calls": 25600, "policy_evaluation_calls": 25760,
            "prefix_restores": 160, "policy_pair_records_written": 2560, "historical_physical_batches": 492544, "historical_physical_draws": 126091264}}, reference


def test_complete_curve_uses_available_draw_axis_and_K0_has_no_repeated_stream_inference():
    payload, reference = fixture()
    # A temporary new error at the same declared budget in every stream.
    for rep in payload["repetitions"]:
        value = analysis.checkpoint(rep["contexts"][0]["arms"]["GAP_FRONTIER"],4)["evaluation"]
        value.update(total_regret=.1, first_action_regret=.1, v_pi=.9, first_action_wrong=True, initial_action="UP")
    result = analysis.summarize(payload, reference)
    assert result["all_analysis_checks_passed"]
    assert result["common_curve_complete_stream_count"] == 16
    assert [point["available_model_draws"] for point in result["checkpoint_curve"]] == [8192,9216,10240,12288,14336,16384]
    first, second = result["checkpoint_curve"][:2]
    assert first["quality"]["confidence_intervals"] is None
    assert first["coverage"]["confidence_intervals"] is None and first["unique_prefix_context_count"] == 160
    delta = second["quality"][analysis.COMPARISON]["total_regret"]
    assert delta["count"] == 16 and delta["degrees_of_freedom"] == 15
    assert delta["mean"] == pytest.approx(.1/160)
    assert second["policy_changes_GAP_FRONTIER_vs_CACHED"]["policy_new_error"]["context_instance_count"] == 16
    assert second["policy_changes_vs_fixed_K0"]["GAP_FRONTIER"]["policy_new_error"]["unique_context_count"] == 1
    assert result["K32_source_reproduction"]["quality"]["passed"] and result["K32_source_reproduction"]["cost"]["passed"]
    assert result["accounting"]["new_physical_draws"] == 0 and result["accounting"]["retained_draws_replayed"] == 41943040


def test_missing_one_checkpoint_removes_entire_curve_quality_without_changing_endpoint_mask_or_fees():
    payload, reference = fixture()
    for rep in payload["repetitions"]:
        row = analysis.checkpoint(rep["contexts"][0]["arms"]["GAP_FRONTIER"],4)
        row["policy_evaluable"] = False
        row["evaluation"].update(policy_evaluable=False, v_pi=None, total_regret=None, continuation_regret=None,
            missing_probability=.25, terminal_probability=.75, identities_pass=None,
            first_action_regret=.1, defined_continuation_regret=.2)
    result = analysis.summarize(payload, reference)
    assert result["all_analysis_checks_passed"]
    assert result["common_curve_complete_stream_count"] == 0 and result["K32_complete_stream_count"] == 16
    assert result["source_valid_stream_count"] == 16
    assert all(point["common_quality_stream_count"] == 0 for point in result["checkpoint_curve"])
    assert result["checkpoint_curve"][1]["quality"][analysis.COMPARISON]["total_regret"]["mean"] is None
    assert all(point["coverage_diagnostic_stream_count"] == 16 for point in result["checkpoint_curve"])
    coverage = result["checkpoint_curve"][1]["coverage"]["arms"]["GAP_FRONTIER"]
    counts = result["checkpoint_curve"][1]["coverage_counts"]["GAP_FRONTIER"]
    assert counts["diagnostic_context_instance_count"] == 2560 and counts["policy_unavailable_instance_count"] == 16
    assert counts["policy_evaluable_instance_count"] == 2544 and counts["mean_missing_probability"] == pytest.approx(.25/160)
    assert coverage["missing_probability"]["mean"] == pytest.approx(.25/160)
    assert coverage["defined_regret_lower_bound"]["mean"] == pytest.approx(.3/160)
    assert result["K32_source_reproduction"]["quality"]["passed"]
    assert result["K32_source_reproduction"]["cost"]["passed"]
    assert result["all_original_arm_costs_including_failures"]["GAP_FRONTIER"]["attributed_cost_totals"] == reference["all_actual_arm_costs"]["GAP_FRONTIER"]["attributed_cost_totals"]


def test_failed_replay_stays_in_status_and_original_costs_and_new_sampling_is_detected():
    payload, reference = fixture()
    row = payload["repetitions"][0]["contexts"][0]["arms"]["CACHED"]
    row.update(source_valid=False, checkpoints=[])
    row["chronology_validation"]["passed"] = False
    result = analysis.summarize(payload, reference)
    assert not result["all_analysis_checks_passed"]
    assert len(result["stream_statuses"]) == 16
    assert result["common_curve_complete_stream_count"] == result["source_valid_stream_count"] == 15
    assert result["all_original_arm_costs_including_failures"]["CACHED"]["actual_arm_count_including_failures"] == 2560
    assert result["all_original_arm_costs_including_failures"]["CACHED"]["attributed_cost_totals"] == reference["all_actual_arm_costs"]["CACHED"]["attributed_cost_totals"]
    assert result["original_source_accounting"] == reference["accounting"]
    payload["accounting"]["new_physical_draws"] = 256
    assert not analysis.summarize(payload, reference)["checks"]["no_new_physical_sampling"]["passed"]
