from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_signed_errors_v25 as analysis
from acfqp.science.controlled_predictive_signed_errors_v25 import diagnose_target
from test_controlled_predictive_signed_errors_v25 import _target, _refresh_target


def modes(raw, remove_a, remove_d):
    return {mode: {"available": True, "wrong": wrong, "regret": .25 * wrong,
        "raw_wrong_repaired": raw and not wrong, "raw_correct_new_error": not raw and wrong,
        "choice_changed": wrong != raw} for mode, wrong in zip(analysis.MODES, (raw, remove_a, remove_d))}


def test_three_modes_paired_directions_and_difference_changes_use_stream_units():
    reps = []
    for index in range(2):
        values = {"CACHED": modes(False, False, True), "VARIANCE": modes(True, True, False),
                  "FRONTIER": modes(index == 0, False, index == 1)}
        context = {"arms": {arm: {"diagnostic": {"modes": values[arm]}} for arm in analysis.ARMS}}
        reps.append({"replicate_index": index, "base_seed": 922001 + index, "contexts": [context] * 22})
    result, _ = analysis.primary_statistics(reps, reps)
    common = result["common_counterfactual_mask"]
    metric = "target_wrong_action_rate"
    assert common["RAW"]["comparisons"]["FRONTIER_minus_CACHED"][metric]["mean"] == .5
    assert common["REMOVE_A"]["comparisons"]["FRONTIER_minus_VARIANCE"][metric]["mean"] == -1
    assert common["REMOVE_D"]["comparisons"]["VARIANCE_minus_CACHED"][metric]["mean"] == -1
    did = result["excess_difference_changes"]["REMOVE_A"]["FRONTIER_minus_CACHED"][metric]
    assert did["mean"] == -.5 and did["count"] == 2 and did["degrees_of_freedom"] == 1
    assert did["standard_error"] == pytest.approx(.5)
    assert result["excess_difference_changes"]["REMOVE_D"]["FRONTIER_minus_VARIANCE"][metric]["mean"] == 1
    assert result["counterfactual_minus_RAW"]["REMOVE_A"]["FRONTIER"]["repair_rate"]["mean"] == .5


def fixture():
    plan = json.loads((ROOT / "reports/controlled_predictive_signed_errors_plan_v25.json").read_text())
    diagnostic = diagnose_target(_target({"LEFT": (1., -2., 1.5, 2), "RIGHT": (.75, 0., 0., 5)}))
    arm = {"diagnostic": diagnostic, "source_validation": {"passed": True},
        "diagnostic_validation": {"passed": True}, "raw_reproduction_validation": {"passed": True},
        "raw_valid": True, "counterfactual_available": True}
    contexts = [{"identity": {key: fixed.get(key) for key in analysis.IDENTITY_FIELDS},
        **{key: fixed[key] for key in ("target_key", "requested_batch_count", "initial_batches", "request_index")},
        "source_paired_complete": True, "source_validation": {"passed": True},
        "raw_valid": True, "paired_complete": True, "status": "DIAGNOSTIC_COMPLETE",
        "arms": {name: deepcopy(arm) for name in analysis.ARMS}} for fixed in plan["contexts"]]
    reps = [{**rep, "source_complete": True, "source_validation": {"passed": True},
        "raw_complete": True, "complete": True, "status": "REPETITION_COMPLETE", "contexts": deepcopy(contexts)} for rep in plan["replicates"]]
    costs = {arm: {"physical_draws": 8093696, "whole_run_seconds": 10. + index} for index, arm in enumerate(analysis.ARMS)}
    source_account = {"local_physical_batches": 94848, "local_physical_draws": 24281088}
    reference = {"all_actual_arm_costs": costs, "accounting": source_account,
        "repetitions": analysis.mode_streams(reps, "RAW"),
        "contexts": [{"identity": c["identity"], "point_estimates": {arm: {"target_wrong_action_rate": 1., "target_mean_local_regret": .25} for arm in analysis.ARMS}} for c in contexts]}
    return {"plan": plan, "repetitions": reps, "plan_binding_validation": {"passed": True},
        "status": "SIGNED_ERRORS_COMPLETE", "raw_complete_repetition_count": 64, "complete_repetition_count": 64,
        "source_actual_arm_costs": costs, "source_accounting": source_account, "source_analysis_accounting": {},
        "accounting": {"historical_physical_batches": 94848, "historical_physical_draws": 24281088,
            "new_provider_calls": 0, "new_oracle_calls": 0, "new_physical_draws": 0,
            "source_result_reads": 1, "model_restore_calls": 0, "source_endpoint_reads": 0},
        "new_provider_calls": 0, "new_oracle_calls": 0, "new_physical_draws": 0,
        "elapsed_seconds_before_report_serialization": 1.}, reference


def test_one_unknown_disables_both_counterfactual_streams_but_preserves_raw_and_all_costs():
    payload, reference = fixture()
    rep = payload["repetitions"][0]
    context = rep["contexts"][0]
    row = context["arms"]["FRONTIER"]
    actions = _target({"LEFT": (1., -2., 1.5, 2), "RIGHT": (.75, 0., 0., 5)})["actions"]
    actions["LEFT"].update(observed=False, q_hat=None, q_hat_exact_continuation=None,
        A_transition_error=None, D_continuation_error=None, total_error=None, identity_residual=None,
        batch_count=0, lower=.5, upper=2.)
    row.update(diagnostic=diagnose_target(_refresh_target(actions)), counterfactual_available=False)
    context.update(paired_complete=False, status="COUNTERFACTUAL_UNAVAILABLE")
    rep.update(complete=False, status="RAW_COMPLETE_COUNTERFACTUAL_INCOMPLETE")
    payload["complete_repetition_count"] = 63
    result = analysis.summarize(payload, reference)
    assert result["all_analysis_checks_passed"]
    assert result["raw_complete_stream_count"] == 64 and result["counterfactual_complete_stream_count"] == 63
    assert all(row["stream_count"] == 63 for row in result["primary"]["common_counterfactual_mask"].values())
    assert result["RAW_V24_metric_reproduction"]["all_passed"]
    assert len(result["unavailable_context_instances"]) == 1
    assert result["source_actual_arm_costs"] == reference["all_actual_arm_costs"]
    assert result["accounting"]["historical_physical_draws"] == 24281088
    assert result["accounting"]["new_physical_draws"] == 0


def test_raw_discordant_counts_distinguish_frontier_repairs_from_control_new_errors():
    contexts = []
    for values in ({"FRONTIER": modes(True, False, True), "CACHED": modes(False, True, False)},
                   {"FRONTIER": modes(False, True, False), "CACHED": modes(True, False, False)}):
        values["VARIANCE"] = values["CACHED"]
        contexts.append({"arms": {arm: {"diagnostic": {"modes": rows}} for arm, rows in values.items()}})
    result = analysis.discordant_groups(contexts)["FRONTIER_minus_CACHED"]
    adverse = result["frontier_wrong_control_correct"]
    assert adverse["context_instance_count"] == 1
    assert adverse["REMOVE_A"]["FRONTIER"] == {"repaired": 1, "new_error": 0}
    assert adverse["REMOVE_A"]["CACHED"] == {"repaired": 0, "new_error": 1}
    reverse = result["frontier_correct_control_wrong"]
    assert reverse["REMOVE_A"]["FRONTIER"]["new_error"] == 1
    assert reverse["REMOVE_D"]["CACHED"]["repaired"] == 1
    assert reverse["REMOVE_D"]["counterfactual_outcome_counts"] == {"both_correct": 1}
