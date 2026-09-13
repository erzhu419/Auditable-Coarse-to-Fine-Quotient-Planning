from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_transfer_v32 as analysis
from test_controlled_predictive_new_starts_analysis_v28 import fixture as old_fixture, evaluation


def fixture():
    payload = old_fixture()
    plan = json.loads((ROOT / "reports/controlled_predictive_transfer_plan_v32.json").read_text())
    payload["plan"] = plan
    payload["original_source_accounting"] = {"historical_physical_batches": 164352, "historical_physical_draws": 42074112,
        "total_physical_batches": 163840, "total_physical_draws": 41943040}
    payload["plan_binding_validation"] = payload["cohort_binding_validation"] = {"passed": True}
    for prefix, board in zip(payload["prefixes"], plan["boards"]):
        prefix.update(board_index=board["board_index"], name=board["name"], prefix_seed=board["prefix_seed"])
    for preparation, fixed in zip(payload["query_preparations"], plan["contexts"]):
        preparation["identity"] = {key: fixed[key] for key in analysis.IDENTITY_FIELDS}
    for rep, fixed_rep in zip(payload["repetitions"], plan["replicates"]):
        rep.update(fixed_rep)
        for context, fixed in zip(rep["contexts"], plan["contexts"]):
            context["identity"] = {key: fixed[key] for key in analysis.IDENTITY_FIELDS}
            context.update({key: fixed[key] for key in ("target_key", "requested_batch_count", "initial_batches")})
            context["arms"]["GAP_FRONTIER"] = context["arms"].pop("VARIANCE")
            context["run_order"] = ["GAP_FRONTIER" if arm == "VARIANCE" else arm for arm in context["run_order"]]
            for row in context["arms"].values():
                row["evaluation"]["initial_action"] = "DOWN"
    account = payload["accounting"]
    account["provider_counts_by_arm"]["GAP_FRONTIER"] = account["provider_counts_by_arm"].pop("VARIANCE")
    account.update(historical_physical_batches=328192, historical_physical_draws=84017152)
    return payload


def test_new_prefix_paid_once_prepared_once_and_full_three_component_query_cost():
    result = analysis.summarize(fixture())
    assert result["all_analysis_checks_passed"]
    assert result["quality_complete_stream_count"] == result["source_valid_stream_count"] == 16
    assert result["accounting"]["prefix_board_count"] == 16 and result["accounting"]["prepared_query_count"] == 160
    assert result["accounting"]["prefix_physical_draws"] == 131072
    assert result["accounting"]["local_physical_draws"] == 41943040
    assert result["accounting"]["total_physical_draws"] == 42074112
    assert result["accounting"]["historical_physical_draws"] == 84017152
    assert result["primary_independent_query_cost"]["arms"]["CACHED"]["independent_query_seconds"]["mean"] == pytest.approx(1.3)
    assert result["all_actual_arm_costs"]["CACHED"]["attributed_cost_totals"]["prefix_sampling_seconds"] == 2560.
    assert "prefix_restore_seconds" not in result["all_actual_arm_costs"]["CACHED"]["attributed_cost_totals"]
    assert len(result["boards"]) == 16 and len(result["queries"]) == 10 and "selected_context_69" not in result
    assert all("reference_validation" not in key for key in result["checks"])


def test_stream_statistics_weight_queries_and_boards_and_use_stream_as_MC_unit():
    payload = fixture()
    for context in payload["repetitions"][0]["contexts"]:
        if context["identity"]["board_index"] == 0:
            context["arms"]["GAP_FRONTIER"]["evaluation"] = {**evaluation(1.), "initial_action": "UP"}
    for context in payload["repetitions"][1]["contexts"]:
        context["arms"]["CACHED"]["evaluation"] = {**evaluation(.2), "initial_action": "UP"}
    result, _ = analysis.stream_statistics(payload["repetitions"][:2], analysis.policy_metrics, ("total_regret",))
    delta = result[analysis.COMPARISON]["total_regret"]
    assert delta["count"] == 2 and delta["degrees_of_freedom"] == 1
    assert delta["mean"] == pytest.approx((1/16-.2)/2)
    assert delta["standard_error"] == pytest.approx((1/16+.2)/2)
    assert "V32" in result["unit"] and "V28" not in result["unit"]


def test_missing_CACHED_policy_excludes_quality_but_preserves_source_cost_and_continuous_diagnostics():
    payload = fixture()
    for rep in payload["repetitions"]:
        context = rep["contexts"][0]
        context["arms"]["CACHED"]["evaluation"].update(policy_evaluable=False, v_pi=None, total_regret=None,
            continuation_regret=None, missing_probability=.25, terminal_probability=.75, identities_pass=None,
            first_action_regret=.1, defined_continuation_regret=.2)
        context.update(paired_complete=False, status="POLICY_EVALUATION_INCOMPLETE")
        rep.update(complete=False, status="REPETITION_RETAINED_WITH_ISSUES")
    result = analysis.summarize(payload)
    assert result["all_analysis_checks_passed"]
    assert result["quality_complete_stream_count"] == 0 and result["source_valid_stream_count"] == 16
    assert result["diagnostic_valid_stream_count"] == 16 and len(result["incomplete_context_instances"]) == 16
    assert result["primary_quality"][analysis.COMPARISON]["total_regret"]["mean"] is None
    assert result["all_actual_arm_costs"]["CACHED"]["provider_counts"]["physical_draws"] == 20971520
    assert result["accounting"]["total_physical_draws"] == 42074112


def test_unequal_actual_stop_retains_source_costs_without_claiming_quality_match():
    payload = fixture()
    rep, context = payload["repetitions"][0], payload["repetitions"][0]["contexts"][0]
    row = context["arms"]["GAP_FRONTIER"]
    row["completed_requested_budget"] = False
    local = row["local"]
    local.update(completed_batches=31, final_batches=63, actual_draws=7936, completed_fixed_budget=False, stop_reason="NO_ELIGIBLE_CANDIDATE")
    local["provider_counts"].update(row_requests=31, physical_draws=7936, repeat_batch_requests=31)
    account = payload["accounting"]
    provider = account["provider_counts_by_arm"]["GAP_FRONTIER"]
    provider["row_requests"] -= 1; provider["physical_draws"] -= 256; provider["repeat_batch_requests"] -= 1
    account["local_physical_batches"] -= 1; account["total_physical_batches"] -= 1
    account["local_physical_draws"] -= 256; account["total_physical_draws"] -= 256
    context.update(budget_matched=False, paired_complete=False)
    rep.update(budget_matched=False, complete=False)
    result = analysis.summarize(payload)
    assert result["all_analysis_checks_passed"]
    assert result["source_valid_stream_count"] == 16 and result["quality_complete_stream_count"] == 15
    assert result["actual_budget_pair_counts"]["unequal_actual_batches"] == 1
    assert result["all_actual_arm_costs"]["GAP_FRONTIER"]["actual_arm_count"] == 2560
    assert result["accounting"]["total_physical_draws"] == 42074112-256
    assert result["accounting"]["historical_physical_draws"] == 84017152


def test_source_failure_preserves_all_new_and_historical_fees_and_rejects_historical_refund():
    payload = fixture()
    rep, context = payload["repetitions"][0], payload["repetitions"][0]["contexts"][0]
    cached = context["arms"]["CACHED"]
    cached["source_validation"]["passed"] = cached["source_valid"] = False
    context.update(source_valid=False, paired_complete=False)
    rep.update(source_valid=False, complete=False)
    result = analysis.summarize(payload)
    assert result["source_valid_stream_count"] == result["quality_complete_stream_count"] == 15
    assert result["all_actual_arm_costs"]["CACHED"]["actual_arm_count"] == 2560
    assert result["original_source_accounting"] == payload["original_source_accounting"]
    assert result["accounting"]["total_physical_draws"] == 42074112
    payload["accounting"]["historical_physical_draws"] -= 256
    assert not analysis.summarize(payload)["checks"]["all_prior_physical_costs_retained"]["passed"]
