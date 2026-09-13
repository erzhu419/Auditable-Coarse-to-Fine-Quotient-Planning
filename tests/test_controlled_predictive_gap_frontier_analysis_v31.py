from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_gap_frontier_v31 as analysis
from test_controlled_predictive_new_starts_analysis_v28 import fixture as old_fixture, evaluation


def fixture():
    payload = old_fixture()
    payload["plan"] = json.loads((ROOT / "reports/controlled_predictive_gap_frontier_plan_v31.json").read_text())
    payload["original_source_accounting"] = deepcopy(payload["accounting"])
    payload["restoration_records"] = [{"identity": row["identity"], "validation": {"passed": True},
        "accounting": {"whole_seconds": .03, "work_counts": {"restore": 1}}} for row in payload["query_preparations"]]
    payload["plan_binding_validation"] = {"passed": True}
    payload["all_restorations_passed"] = True
    payload["all_prefix_restorations_before_sampling"] = True
    payload["source_and_new_endpoint_lengths_valid"] = True
    for rep in payload["repetitions"]:
        for context in rep["contexts"]:
            context["arms"]["GAP_FRONTIER"] = context["arms"].pop("VARIANCE")
            context["run_order"] = ["GAP_FRONTIER" if arm == "VARIANCE" else arm for arm in context["run_order"]]
            for arm, row in context["arms"].items():
                row["evaluation"]["initial_action"] = "DOWN"
                row["costs"]["prefix_restore_seconds"] = .03
                row["costs"]["independent_query_seconds"] += .03
                if arm == "CACHED":
                    row["reference_validation"] = {"passed": True}
                    row["reference_value_validation"] = {"passed": True}
    account = payload["accounting"]
    account["provider_counts_by_arm"]["GAP_FRONTIER"] = account["provider_counts_by_arm"].pop("VARIANCE")
    account.update(prefix_physical_batches=0, prefix_physical_draws=0, historical_physical_batches=164352,
        historical_physical_draws=42074112, total_physical_batches=163840, total_physical_draws=41943040,
        prefix_restores=160, prefix_restore_seconds=4.8)
    return payload


def test_stream_weighting_and_full_four_component_independent_cost():
    payload = fixture()
    for context in payload["repetitions"][0]["contexts"]:
        if context["identity"]["board_index"] == 0:
            context["arms"]["GAP_FRONTIER"]["evaluation"] = {**evaluation(1.), "initial_action": "UP"}
    for context in payload["repetitions"][1]["contexts"]:
        context["arms"]["CACHED"]["evaluation"] = {**evaluation(.2), "initial_action": "UP"}
    stats, _ = analysis.stream_statistics(payload["repetitions"][:2], analysis.policy_metrics, ("total_regret",))
    delta = stats[analysis.COMPARISON]["total_regret"]
    assert delta["count"] == 2 and delta["degrees_of_freedom"] == 1
    assert delta["mean"] == pytest.approx((1/16-.2)/2)
    assert delta["standard_error"] == pytest.approx((1/16+.2)/2)
    result = analysis.summarize(payload)
    assert result["all_analysis_checks_passed"]
    assert result["primary_independent_query_cost"]["arms"]["CACHED"]["independent_query_seconds"]["mean"] == pytest.approx(1.33)
    assert result["primary_independent_query_cost"][analysis.COMPARISON]["independent_query_seconds"]["mean"] == pytest.approx(.02)
    assert result["accounting"]["prefix_restores"] == 160
    assert result["all_actual_arm_costs"]["CACHED"]["attributed_cost_totals"]["prefix_restore_seconds"] == pytest.approx(2560*.03)
    assert result["accounting"]["total_physical_draws"] == 41943040
    assert result["original_source_accounting"]["total_physical_draws"] == 42074112


@pytest.mark.parametrize("left,right,reasons,expected", [(0,0,("NO_ELIGIBLE_CANDIDATE",)*2,True),
    (12,12,("NO_ELIGIBLE_CANDIDATE",)*2,True), (12,11,("NO_ELIGIBLE_CANDIDATE",)*2,False),
    (0,0,("EXCEPTION",)*2,False), (32,32,("FIXED_BATCH_BUDGET_COMPLETE",)*2,True)])
def test_actual_budget_match_requires_full_K_or_same_normal_stop(left, right, reasons, expected):
    context = {"requested_batch_count": 32, "arms": {arm: {"local": {"completed_batches": n,
        "completed_fixed_budget": n == 32, "stop_reason": reason}} for arm, n, reason in zip(analysis.ARMS, (left,right), reasons)}}
    assert analysis.matched_budget(context)[0] == expected


def test_missing_policy_removes_quality_streams_without_refunding_costs_or_diagnostics():
    payload = fixture()
    for rep in payload["repetitions"]:
        context = rep["contexts"][0]
        context["arms"]["GAP_FRONTIER"]["evaluation"].update(policy_evaluable=False, v_pi=None,
            total_regret=None, continuation_regret=None, missing_probability=.25, terminal_probability=.75,
            identities_pass=None, first_action_regret=.1, defined_continuation_regret=.2)
        context.update(paired_complete=False, status="POLICY_EVALUATION_INCOMPLETE")
        rep.update(complete=False, status="REPETITION_RETAINED_WITH_INCOMPLETE_QUALITY")
    result = analysis.summarize(payload)
    assert result["all_analysis_checks_passed"]
    assert result["quality_complete_stream_count"] == 0 and result["source_valid_stream_count"] == 16
    assert result["diagnostic_valid_stream_count"] == 16
    assert result["primary_quality"][analysis.COMPARISON]["total_regret"]["mean"] is None
    assert len(result["incomplete_context_instances"]) == 16
    assert result["all_actual_arm_costs"]["GAP_FRONTIER"]["actual_arm_count"] == 2560
    assert result["accounting"]["total_physical_draws"] == 41943040


def test_CACHED_history_failure_excludes_source_stream_but_keeps_fresh_samples_and_old_costs():
    payload = fixture()
    rep = payload["repetitions"][0]
    context = rep["contexts"][0]
    context["arms"]["CACHED"]["reference_validation"]["passed"] = False
    context["arms"]["CACHED"]["source_valid"] = False
    context.update(source_valid=False, paired_complete=False)
    rep.update(source_valid=False, complete=False)
    result = analysis.summarize(payload)
    assert not result["all_analysis_checks_passed"]
    assert not result["checks"]["CACHED_reference_validation"]["passed"]
    assert result["quality_complete_stream_count"] == result["source_valid_stream_count"] == 15
    assert result["all_actual_arm_costs"]["CACHED"]["provider_counts"]["physical_draws"] == 20971520
    assert result["original_source_accounting"] == payload["original_source_accounting"]


def test_repair_and_new_errors_use_same_paired_full_policy_identity_mask():
    contexts = []
    for index, before, after in ((69,.1,0.), (7,0.,.2), (8,.3,.3)):
        contexts.append({"identity": {"context_index": index}, "arms": {arm: {"evaluation": {**evaluation(value),
            "initial_action": "UP" if value else "DOWN"}} for arm,value in zip(analysis.ARMS,(before,after))}})
    result = analysis.policy_changes(contexts*2)
    assert result["paired_context_instances"] == 6 and result["unique_context_count"] == 3
    assert result["policy_repaired"] == {"context_instance_count": 2, "unique_context_count": 1, "context_indices": [69]}
    assert result["policy_new_error"]["context_indices"] == [7]
    assert result["initial_action_changed"]["context_instance_count"] == 4


def test_missing_CACHED_evaluation_keeps_source_cost_streams_and_invalidates_quality_only():
    payload = fixture()
    for rep in payload["repetitions"]:
        context = rep["contexts"][0]
        cached = context["arms"]["CACHED"]
        cached.pop("evaluation")
        cached["evaluation_validation"]["passed"] = False
        cached["first_action_validation"]["passed"] = False
        cached["reference_value_validation"]["passed"] = False
        context.update(paired_complete=False, status="QUALITY_INCOMPLETE")
        rep.update(complete=False, status="REPETITION_RETAINED_WITH_ISSUES")
    result = analysis.summarize(payload)
    assert result["source_valid_stream_count"] == 16
    assert result["quality_complete_stream_count"] == result["diagnostic_valid_stream_count"] == 0
    assert result["checks"]["source_validity_labels"]["passed"]
    assert result["checks"]["whole_stream_masks"]["passed"]
    assert not result["checks"]["CACHED_reference_value_validation"]["passed"]
    assert result["primary_independent_query_cost"]["stream_count"] == 16
    assert result["accounting"]["total_physical_draws"] == 41943040
