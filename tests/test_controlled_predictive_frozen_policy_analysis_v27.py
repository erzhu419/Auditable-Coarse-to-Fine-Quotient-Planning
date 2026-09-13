from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_frozen_policy_v27 as analysis


def evaluation(total=0., first=0.):
    continuation = total - first
    return {"policy_evaluable": True, "v_pi": 1. - total, "v_star": 1., "total_regret": total,
        "first_action_regret": first, "continuation_regret": continuation,
        "first_action_wrong": first > 1e-10, "missing_probability": 0., "weighted_unobserved_choices": .1,
        "reach_probability_pass": True, "terminal_probability": 1.,
        "identity_residual": 0., "identities_pass": True, "missing_policy_frontier": [],
        "reachable_decisions": [{"reach_probability": .1, "local_regret": continuation / .1, "weighted_regret": continuation}]}


def test_true_reach_components_and_factorial_directions_use_stream_units():
    reps = []
    for index in range(2):
        totals = {"CACHED": .4, "VARIANCE": .2, "FRONTIER": .5, "FRONTIER_VARIANCE": .2 * index}
        context = {"arms": {arm: {"evaluation": evaluation(total)} for arm, total in totals.items()}}
        reps.append({"replicate_index": index, "base_seed": 922001 + index, "contexts": [context] * 22})
    result, _ = analysis.stream_statistics(reps, analysis.policy_metrics, analysis.POLICY_METRICS)
    assert result["arms"]["CACHED"]["continuation_regret"]["mean"] == .4  # weighted .1*4, not an unweighted panel sum
    comparisons = result["primary_comparisons"]["total_regret"]
    assert comparisons["FRONTIER_VARIANCE_minus_FRONTIER"]["mean"] == pytest.approx(-.4)
    assert comparisons["FRONTIER_VARIANCE_minus_VARIANCE"]["mean"] == pytest.approx(-.1)
    interaction = comparisons["structure_by_resampling_interaction"]
    assert interaction["mean"] == pytest.approx(-.2)
    assert interaction["count"] == 2 and interaction["degrees_of_freedom"] == 1
    assert interaction["standard_error"] == pytest.approx(.1)
    rate = result["primary_comparisons"]["optimal_policy_rate"]["FRONTIER_VARIANCE_minus_FRONTIER"]
    assert rate["mean"] == .5 and rate["improved"] == 1 and rate["same"] == 1 and rate["worse"] == 0


def fixture():
    plan = json.loads((ROOT / "reports/controlled_predictive_frozen_policy_plan_v27.json").read_text())
    arm = {"evaluation": evaluation(), "source_validation": {"passed": True},
        "first_action_validation": {"passed": True}, "source_valid": True}
    contexts = [{"identity": {key: fixed.get(key) for key in analysis.IDENTITY_FIELDS},
        **{key: fixed[key] for key in ("target_key", "panel", "requested_batch_count", "initial_batches")},
        "source_paired_complete": True, "source_validation": {"passed": True}, "source_valid": True,
        "paired_complete": True, "status": "POLICY_COMPLETE", "arms": {name: deepcopy(arm) for name in analysis.ARMS}}
        for fixed in plan["contexts"]]
    repetitions = [{**rep, "source_complete": True, "source_valid": True, "complete": True,
        "status": "REPETITION_COMPLETE", "contexts": deepcopy(contexts)} for rep in plan["replicates"]]
    costs = {arm: {"provider_counts": {"physical_draws": 8093696}, "whole_run_seconds": 10. + index} for index, arm in enumerate(analysis.ARMS)}
    account = {"local_physical_batches": 126464, "local_physical_draws": 32374784}
    _, streams = analysis.stream_statistics(repetitions, analysis.first_metrics, analysis.FIRST_METRICS)
    reference = {"all_actual_arm_costs": costs, "accounting": account, "repetitions": streams,
        "contexts": [{"identity": c["identity"], "point_estimates": {arm: {"target_wrong_action_rate": 0., "target_mean_local_regret": 0.} for arm in analysis.ARMS}} for c in contexts]}
    payload = {"plan": plan, "repetitions": repetitions, "plan_binding_validation": {"passed": True},
        "source_stream_validation": {"passed": True}, "source_analysis_accounting": {"analysis_seconds": .1},
        "status": "POLICY_COMPLETE", "source_valid_repetition_count": 64, "complete_repetition_count": 64,
        "source_actual_arm_costs": costs, "source_accounting": account,
        "accounting": {"historical_physical_batches": 126464, "historical_physical_draws": 32374784,
            "source_endpoint_reads": 1, "new_sampling_calls": 0, "new_replanning_calls": 0,
            "new_physical_batches": 0, "new_physical_draws": 0, "policy_evaluation_seconds": .3},
        "elapsed_seconds_before_report_serialization": 1.}
    return payload, reference


def test_missing_policy_excludes_whole_stream_but_keeps_first_action_and_all_costs():
    payload, reference = fixture()
    rep = payload["repetitions"][0]
    context = rep["contexts"][0]
    value = context["arms"]["FRONTIER_VARIANCE"]["evaluation"]
    value.update(policy_evaluable=False, v_pi=None, total_regret=None, continuation_regret=None,
        missing_probability=.25, terminal_probability=.75, identity_residual=None, identities_pass=None,
        missing_policy_frontier=[{"key": [1, [2]], "reach_probability": .25, "reason": "MISSING_ACTION"}])
    context.update(paired_complete=False, status="POLICY_UNAVAILABLE")
    rep.update(complete=False, status="REPETITION_INCOMPLETE")
    payload["complete_repetition_count"] = 63
    result = analysis.summarize(payload, reference)
    assert result["all_analysis_checks_passed"]
    assert result["source_valid_stream_count"] == 64 and result["complete_stream_count"] == 63
    assert result["V26_first_action_metric_reproduction"]["all_passed"]
    assert result["same_main_mask_first_action"]["complete_stream_count"] == 63
    assert len(result["incomplete_context_instances"]) == 1
    missing = result["availability_source_valid_streams"]["FRONTIER_VARIANCE"]
    assert missing["missing_probability"] == .25 / 1408 and missing["policy_unavailable_rate"] == 1 / 1408
    assert result["source_actual_arm_costs"] == reference["all_actual_arm_costs"]
    assert result["accounting"]["historical_physical_draws"] == 32374784
    assert result["accounting"]["new_physical_draws"] == 0 and result["accounting"]["policy_evaluation_seconds"] == .3


@pytest.mark.parametrize("failure", ["source", "reach"])
def test_source_or_reach_failure_cannot_enter_policy_mask_even_when_regret_is_zero(failure):
    payload, reference = fixture()
    rep = payload["repetitions"][0]
    context = rep["contexts"][0]
    arm = context["arms"]["CACHED"]
    if failure == "source":
        arm.update(source_valid=False, source_validation={"passed": False, "reason": "retained action mismatch"})
        context["source_valid"] = rep["source_valid"] = False
        payload["source_valid_repetition_count"] = 63
    else:
        arm["evaluation"].update(reach_probability_pass=False, terminal_probability=.75)
    context.update(paired_complete=False, status="INVALID")
    rep.update(complete=False, status="REPETITION_INVALID")
    payload["complete_repetition_count"] = 63
    result = analysis.summarize(payload, reference)
    assert result["complete_stream_count"] == 63
    assert result["source_valid_stream_count"] == (63 if failure == "source" else 64)
    assert result["checks"]["whole_stream_masks"]["passed"]
    assert result["V26_first_action_metric_reproduction"]["all_passed"]
    assert result["V26_first_action_metric_reproduction"]["per_context_full64_comparison_available"] == (failure == "reach")
    if failure == "reach":
        assert result["checks"]["true_reach_probability_conservation"]["failed"] == 1
    assert result["source_accounting"] == reference["accounting"]
    assert result["source_actual_arm_costs"]["CACHED"]["provider_counts"]["physical_draws"] == 8093696
