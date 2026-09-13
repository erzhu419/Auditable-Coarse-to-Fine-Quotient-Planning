#!/usr/bin/env python3
"""Summarize retained V21 local interventions; no planning or truth access."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

ARMS = ("CACHED", "VARIANCE")
TOL = 1e-10
IDENTITY_FIELDS = ("context_index", "case_name", "sample_seed", "query_name", "group",
                   "source_v20_changed", "source_old_witness", "source_old_group")


def _mean(values):
    return math.fsum(values) / len(values) if values else None


def _deltas(values):
    return {"count": len(values), "mean": _mean(values),
            "minimum": min(values, default=None), "maximum": max(values, default=None),
            "reduced": sum(value < -TOL for value in values),
            "equal": sum(abs(value) <= TOL for value in values),
            "increased": sum(value > TOL for value in values)}


def _choice_summary(evaluations):
    observed_actions = [action for evaluation in evaluations for action in evaluation["target"]["actions"].values() if action["observed"]]
    return {
        "target": {"selected_optimal_count": sum(e["target"]["selected_action_in_true_optimal_set"] for e in evaluations),
                   "selected_observed_count": sum(e["target"]["selected_action_observed"] for e in evaluations),
                   "interval_closed_count": sum(e["target"]["interval_closed"] for e in evaluations),
                   "mean_local_regret": _mean([e["target"]["local_regret"] for e in evaluations]),
                   "maximum_local_regret": max((e["target"]["local_regret"] for e in evaluations), default=None),
                   "observed_action_count": len(observed_actions),
                   "mean_absolute_action_error_terms": {key: _mean([abs(action[key]) for action in observed_actions]) for key in ("A_transition_error", "D_continuation_error", "total_error")}},
        "fixed_panel": {
            "dependent_state_count": sum(e["panel"]["state_count"] for e in evaluations),
            "selected_optimal_count": sum(e["panel"]["selected_optimal_count"] for e in evaluations),
            "positive_regret_count": sum(e["panel"]["positive_regret_count"] for e in evaluations),
            "selected_observed_count": sum(s["selected_action_observed"] for e in evaluations for s in e["panel"]["states"]),
            "interval_closed_count": sum(s["interval_closed"] for e in evaluations for s in e["panel"]["states"]),
            "sum_local_regret": math.fsum(e["panel"]["sum_local_regret"] for e in evaluations),
            "mean_context_sum_local_regret": _mean([e["panel"]["sum_local_regret"] for e in evaluations]),
            "maximum_local_regret": max((e["panel"]["maximum_local_regret"] for e in evaluations), default=None)}}


def _pair_summary(contexts):
    result = {"complete_pair_count": len(contexts), "COMMON_START": _choice_summary([c["initial_evaluation"] for c in contexts])}
    for arm in ARMS:
        result[arm] = _choice_summary([c["arms"][arm]["evaluation"] for c in contexts])
        result[arm]["target_regret_change_from_common_start"] = _deltas([
            c["arms"][arm]["evaluation"]["target"]["local_regret"] - c["initial_evaluation"]["target"]["local_regret"] for c in contexts])
        result[arm]["panel_sum_regret_change_from_common_start"] = _deltas([
            c["arms"][arm]["evaluation"]["panel"]["sum_local_regret"] - c["initial_evaluation"]["panel"]["sum_local_regret"] for c in contexts])
    result["VARIANCE_minus_CACHED"] = {
        "target_local_regret": _deltas([c["arms"]["VARIANCE"]["evaluation"]["target"]["local_regret"] - c["arms"]["CACHED"]["evaluation"]["target"]["local_regret"] for c in contexts]),
        "panel_context_sum_local_regret": _deltas([c["arms"]["VARIANCE"]["evaluation"]["panel"]["sum_local_regret"] - c["arms"]["CACHED"]["evaluation"]["panel"]["sum_local_regret"] for c in contexts]),
        "whole_run_seconds": _deltas([c["arms"]["VARIANCE"]["local"]["accounting"]["whole_run_seconds"] - c["arms"]["CACHED"]["local"]["accounting"]["whole_run_seconds"] for c in contexts])}
    return result


def _compact_evaluation(evaluation):
    target, panel = evaluation["target"], evaluation["panel"]
    return {"target": {**{key: value for key, value in target.items() if key not in ("accounting", "actions")},
                       "actions": {action: {key: value for key, value in row.items() if key != "children"}
                                   for action, row in target["actions"].items()}},
            "panel": {key: value for key, value in panel.items() if key not in ("accounting",)}}


def summarize(payload):
    roster, contexts = payload["cohort_roster"], payload["contexts"]
    checks = defaultdict(list)
    checks["frozen_identities"] = [len(contexts) == roster["context_count"] == 22,
        [{key: c["identity"].get(key) for key in IDENTITY_FIELDS} for c in contexts] ==
        [{key: c.get(key) for key in IDENTITY_FIELDS} for c in roster["contexts"]]]
    checks["source_membership"] = [sum(c["identity"]["source_v20_changed"] for c in contexts) == 20,
        sum(c["identity"]["source_old_witness"] for c in contexts) == 10,
        Counter(c["identity"]["group"] for c in contexts) == {"improvement": 7, "regression": 13, "old_witness_only": 2}]
    checks["persistence_before_intervention_and_truth"] = [payload["common_snapshots_persisted_before_local_acquisition"], payload["all_endpoints_persisted_before_oracle"]]
    checks["warm_reproduction"] = [len(payload["reconstruction_validation"]["warm_prefixes"]) == 3] + [row["passed"] for row in payload["reconstruction_validation"]["warm_prefixes"]]
    eligible, complete, compact = [], [], []
    physical = {arm: Counter() for arm in ARMS}
    stages = {arm: Counter() for arm in ARMS}
    work = {arm: Counter() for arm in ARMS}
    whole_seconds = {arm: [] for arm in ARMS}
    stop = {arm: Counter() for arm in ARMS}
    for context in contexts:
        row = {key: value for key, value in context.items() if key not in ("arms", "initial_evaluation")}
        compact.append(row)
        if "arms" not in context:
            continue
        eligible.append(context)
        checks["rotating_arm_order"].append(context["run_order"] == list(ARMS if context["identity"]["context_index"] % 2 == 0 else reversed(ARMS)))
        K, initial, j = context["requested_batch_count"], context["initial_batches"], context["request_index"]
        quota = (128 - (initial - j)) // context["target_key"][0]
        checks["original_remaining_quota"].append(K == quota - j and K > 0 and initial + K <= 128)
        declared_panel = context["panel"]
        initial_evaluation = context["initial_evaluation"]
        evaluations = [initial_evaluation] + [context["arms"][arm]["evaluation"] for arm in ARMS]
        for evaluation in evaluations:
            target, panel = evaluation["target"], evaluation["panel"]
            checks["fixed_panel"].append([s["key"] for s in panel["states"]] == declared_panel and panel["state_count"] == len(declared_panel))
            checks["target_identity"].append(target["target_key"] == context["target_key"])
            checks["A_plus_D_identity"].append(target["identities_pass"] and target["maximum_absolute_identity_residual"] <= TOL)
            for action in target["actions"].values():
                if action["observed"]:
                    checks["A_plus_D_identity"].append(abs(action["q_hat"] - action["q_star"] - action["A_transition_error"] - action["D_continuation_error"]) <= TOL)
                else:
                    checks["unknown_action_terms"].append(all(action[key] is None for key in ("q_hat", "A_transition_error", "D_continuation_error", "total_error")))
        pair_complete = True
        row["initial_evaluation"] = _compact_evaluation(initial_evaluation)
        row["arms"] = {}
        for arm in ARMS:
            current = context["arms"][arm]
            local, validation = current["local"], current["source_validation"]
            n = local["completed_batches"]
            provider = local["provider_counts"]
            checks["batch_draw_accounting"].append(local["requested_batch_count"] == K and local["initial_batches"] == initial and local["final_batches"] == initial + n and 0 <= n <= K and local["actual_draws"] == 256 * n and provider.get("row_requests", 0) == n and provider.get("physical_draws", 0) == 256 * n and provider.get("first_batch_requests", 0) + provider.get("repeat_batch_requests", 0) == n)
            checks["completion_label"].append(local["completed_fixed_budget"] == (n == K))
            checks["source_reproduction"].append(validation["passed"])
            pair_complete &= local["completed_fixed_budget"] and validation["passed"]
            physical[arm].update(provider)
            stages[arm].update(local["accounting"]["seconds_by_stage"])
            work[arm].update(local["accounting"]["work_counts"])
            whole_seconds[arm].append(local["accounting"]["whole_run_seconds"])
            stop[arm]["local_arm_count"] += 1
            index = local["first_original_stop_index"]
            stop[arm]["gap_separated_during_local_intervention"] += index is not None
            stop[arm]["batches_taken_after_first_original_stop"] += n - index if index is not None else 0
            stop[arm][local["stop_reason"]] += 1
            row["arms"][arm] = {"local": local, "source_validation": validation, "evaluation": _compact_evaluation(current["evaluation"])}
        checks["complete_pair_label"].append(context["paired_complete"] == pair_complete)
        expected_status = "SOURCE_VALIDATION_MISMATCH" if not all(context["arms"][arm]["source_validation"]["passed"] for arm in ARMS) else "LOCAL_COMPLETE" if pair_complete else "FIXED_BUDGET_INCOMPLETE"
        checks["completion_label"].append(context["status"] == expected_status)
        if pair_complete:
            complete.append(context)
        cached, variance = (context["arms"][arm]["evaluation"] for arm in ARMS)
        row["VARIANCE_minus_CACHED"] = {
            "target_local_regret": variance["target"]["local_regret"] - cached["target"]["local_regret"],
            "panel_sum_local_regret": variance["panel"]["sum_local_regret"] - cached["panel"]["sum_local_regret"],
            "panel_state_regret_changes": [{"key": left["key"], "VARIANCE_minus_CACHED": right["local_regret"] - left["local_regret"],
                                           "CACHED_selected_action": left["selected_action"], "VARIANCE_selected_action": right["selected_action"]}
                                          for left, right in zip(cached["panel"]["states"], variance["panel"]["states"])]}
    accounting = payload["accounting"]
    checks["total_physical_work"] = [accounting["warm_prefix_count"] == 3, accounting["warm_conversion_count"] == 3,
        accounting["warm_physical_batches"] == 96, accounting["warm_physical_draws"] == 24576,
        accounting["retained_suffix_provider_calls"] == 0,
        accounting["local_physical_batches"] == sum(physical[arm]["row_requests"] for arm in ARMS),
        accounting["local_physical_draws"] == sum(physical[arm]["physical_draws"] for arm in ARMS),
        accounting["total_physical_draws_including_warm_regeneration"] == accounting["warm_physical_draws"] + accounting["local_physical_draws"],
        abs(accounting["local_allocation_wall_seconds"] - math.fsum(value for arm in ARMS for value in whole_seconds[arm])) <= TOL]
    checks["declared_pair_count"] = [payload["paired_complete_count"] == len(complete)]
    results = {name: {"passed": all(values), "checked": len(values), "failed": sum(not value for value in values)} for name, values in checks.items()}
    return {
        "schema": "controlled_predictive_local_analysis_v21", "status": payload["status"],
        "context_count": len(contexts), "status_counts": dict(Counter(c["status"] for c in contexts)),
        "group_counts": dict(Counter(c["identity"]["group"] for c in contexts)),
        "extracted_local_pair_count": len(eligible), "complete_pair_count": len(complete),
        "requested_K": {"minimum": min((c["requested_batch_count"] for c in eligible), default=None),
                        "maximum": max((c["requested_batch_count"] for c in eligible), default=None),
                        "sum_per_arm": sum(c["requested_batch_count"] for c in eligible)},
        "complete_pairs": _pair_summary(complete),
        "groups": {group: _pair_summary([c for c in complete if c["identity"]["group"] == group]) for group in ("improvement", "regression", "old_witness_only")},
        "all_local_arms": {arm: {"provider_counts": dict(physical[arm]), "seconds_by_stage": dict(stages[arm]),
            "work_counts": dict(work[arm]), "whole_run_seconds": math.fsum(whole_seconds[arm]),
            "mean_whole_run_seconds": _mean(whole_seconds[arm]), "original_stop_diagnostics": dict(stop[arm])} for arm in ARMS},
        "accounting": payload["accounting"], "reconstruction_validation": payload["reconstruction_validation"],
        "elapsed_seconds_before_report_serialization": payload["elapsed_seconds_before_report_serialization"],
        "checks": results, "all_analysis_checks_passed": all(row["passed"] for row in results.values()),
        "contexts": compact,
        "scope": "Posthoc common-observation and equal-batch local allocation comparison. Primary pairs require both arms complete K and source validation. Panel states are dependent fixed diagnostic states; target regret assumes true optimal continuation and is not complete-policy value. All arms contribute physical work even when excluded from primary pairs.",
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_local_v21.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_local_analysis_v21.json"))
    args = parser.parse_args()
    result = summarize(json.loads(args.input.read_text(encoding="utf-8")))
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "contexts": result["context_count"], "complete_pairs": result["complete_pair_count"], "all_analysis_checks_passed": result["all_analysis_checks_passed"]}))


if __name__ == "__main__":
    main()
