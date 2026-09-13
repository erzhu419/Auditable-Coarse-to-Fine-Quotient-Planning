from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_prefix_baseline_v29 as analysis
import analyze_controlled_predictive_new_starts_v28 as old_analysis
from test_controlled_predictive_new_starts_analysis_v28 import evaluation, fixture as old_fixture


def policy(total, first=None, action="LEFT"):
    first = total if first is None else first
    value = evaluation(total)
    value.update(first_action_regret=first, continuation_regret=total-first,
        defined_continuation_regret=total-first, first_action_wrong=first > 1e-10, initial_action=action)
    return {"evaluation": value}


def test_fixed_prefix_is_referenced_without_creating_independent_baseline_observations():
    baselines = {0: policy(.4)}
    reps = [{"replicate_index": index, "base_seed": 942001+index,
        "contexts": [{"identity": {"board_index": 0}, "prefix_context_index": 0,
            "arms": {"CACHED": policy(.8*index), "VARIANCE": policy(.4)}}]} for index in range(2)]
    result, streams = analysis.stream_statistics(reps, baselines, analysis.policy_metrics, ("total_regret",))
    comparison = result["comparisons"]["CACHED_minus_PREFIX"]["total_regret"]
    assert comparison["mean"] == 0 and comparison["count"] == 2
    assert comparison["standard_error"] == pytest.approx(.4) and comparison["degrees_of_freedom"] == 1
    assert result["arm_means"]["PREFIX"]["total_regret"] == .4
    assert all(stream["arms"]["PREFIX"]["total_regret"] == .4 for stream in streams)
    points = analysis.points([c for rep in reps for c in rep["contexts"]], baselines, analysis.policy_metrics, ("total_regret",))
    assert points["unique_prefix_context_count"] == 1 and points["endpoint_context_instances"] == 2


def test_policy_repair_and_new_error_are_distinct_from_first_action_changes():
    baselines = {0: policy(.2, 0., "RIGHT"), 1: policy(0., 0., "LEFT")}
    contexts = [{"prefix_context_index": 0, "arms": {"CACHED": policy(0., 0., "RIGHT"), "VARIANCE": policy(.2, .2, "RIGHT")}},
        {"prefix_context_index": 1, "arms": {"CACHED": policy(.1, .1, "RIGHT"), "VARIANCE": policy(0., 0., "LEFT")}}]
    result = analysis.change_statistics([{"contexts": contexts}], baselines)
    assert result["CACHED"]["policy_repaired_rate"]["context_instance_count"] == 1
    assert result["CACHED"]["policy_new_error_rate"]["context_instance_count"] == 1
    assert result["CACHED"]["first_action_repaired_rate"]["context_instance_count"] == 0
    assert result["CACHED"]["first_action_new_error_rate"]["context_instance_count"] == 1
    assert result["CACHED"]["initial_action_changed_rate"]["context_instance_count"] == 1
    assert result["VARIANCE"]["policy_new_error_rate"]["context_instance_count"] == 0
    assert result["VARIANCE"]["first_action_new_error_rate"]["context_instance_count"] == 1


def fixture():
    old = old_fixture()
    reference = old_analysis.summarize(old)
    plan = json.loads((ROOT / "reports/controlled_predictive_prefix_baseline_plan_v29.json").read_text())
    baselines = []
    for fixed in plan["contexts"]:
        baselines.append({"context_index": fixed["context_index"], "identity": {key: fixed[key] for key in analysis.IDENTITY_FIELDS},
            "source_valid": True, "source_validation": {"passed": True}, "first_action_validation": {"passed": True},
            "evaluation_validation": {"passed": True}, **policy(0.),
            "costs": {"prefix_sampling_seconds": 1., "single_query_prepare_seconds": .2, "independent_query_seconds": 1.2}})
    for rep in old["repetitions"]:
        for context in rep["contexts"]:
            context["prefix_context_index"] = context["identity"]["context_index"]
            context["prefix_binding_validation"] = {"passed": True}
            for row in context["arms"].values():
                row["evaluation"]["initial_action"] = "LEFT"
    payload = {"plan": plan, "prefix_baselines": baselines, "repetitions": old["repetitions"],
        "plan_binding_validation": {"passed": True}, "all_prefix_policies_bound_before_oracle": True,
        "source_actual_costs": reference["all_actual_arm_costs"], "source_accounting": reference["accounting"],
        "status": "PREFIX_BASELINE_COMPLETE", "elapsed_seconds_before_report_serialization": 1.,
        "accounting": {"historical_physical_batches": 164352, "historical_physical_draws": 42074112,
            "prefix_policy_evaluation_calls": 160, "endpoint_evaluation_calls": 0, "new_sampling_calls": 0,
            "new_physical_batches": 0, "new_physical_draws": 0, "new_planner_solves": 0, "new_model_restores": 0,
            "prefix_policy_evaluation_seconds": .4}}
    return payload, reference


def test_missing_prefix_excludes_shared_quality_but_preserves_original_endpoint_reproduction_and_fees():
    payload, reference = fixture()
    value = payload["prefix_baselines"][0]["evaluation"]
    value.update(policy_evaluable=False, v_pi=None, total_regret=None, continuation_regret=None,
        missing_probability=.25, terminal_probability=.75, identities_pass=None)
    result = analysis.summarize(payload, reference)
    assert result["all_analysis_checks_passed"]
    assert result["comparison_complete_stream_count"] == 0 and result["comparison_source_valid_stream_count"] == 16
    assert result["comparison_diagnostic_stream_count"] == 16
    assert len(result["prefix_baselines_once"]) == 160
    assert result["V28_endpoint_reproduction"]["all_passed"]
    assert result["V28_endpoint_reproduction"]["comparisons"]["quality"]["stream_count"] == 16
    assert result["primary_quality"]["comparisons"]["CACHED_minus_PREFIX"]["total_regret"]["mean"] is None
    delta = result["primary_independent_query_cost"]["comparisons"]["CACHED_minus_PREFIX"]["independent_query_seconds"]
    assert delta["mean"] == pytest.approx(.1) and delta["count"] == 16
    assert result["source_actual_costs"] == reference["all_actual_arm_costs"]
    assert result["source_accounting"] == reference["accounting"]
    assert result["accounting"]["historical_physical_draws"] == 42074112
    assert result["accounting"]["prefix_policy_evaluation_calls"] == 160 and result["accounting"]["new_physical_draws"] == 0
