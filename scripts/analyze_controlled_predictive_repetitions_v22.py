#!/usr/bin/env python3
"""Analyze fixed V22 suffix repetitions, treating each stream as one replicate."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from statistics import stdev
from time import perf_counter

from scipy.stats import t

ARMS = ("CACHED", "VARIANCE")
TOL = 1e-10
IDENTITY_FIELDS = ("context_index", "case_name", "sample_seed", "query_name", "group",
                   "source_v20_changed", "source_old_witness", "source_old_group")
PRIMARY = ("target_wrong_action_rate", "target_mean_local_regret")


def mean(values):
    return math.fsum(values) / len(values) if values else None


def differences(values):
    return {"count": len(values), "mean": mean(values),
            "negative": sum(value < -TOL for value in values),
            "zero": sum(abs(value) <= TOL for value in values),
            "positive": sum(value > TOL for value in values)}


def monte_carlo_interval(values):
    """The caller supplies one paired mean difference per complete suffix stream."""
    result = differences(values)
    n = len(values)
    sd = stdev(values) if n >= 2 else None
    se = sd / math.sqrt(n) if sd is not None else None
    critical = float(t.ppf(0.975, n - 1)) if n >= 2 else None
    result.update(standard_deviation=sd, standard_error=se,
                  degrees_of_freedom=n - 1 if n >= 2 else None,
                  student_t_critical=critical,
                  confidence_interval_95=[result["mean"] - critical * se,
                                          result["mean"] + critical * se] if n >= 2 else None)
    return result


def metrics(evaluation):
    target, panel = evaluation["target"], evaluation["panel"]
    observed = [row for row in target["actions"].values() if row["observed"]]
    return {
        "target_wrong_action_rate": float(not target["selected_action_in_true_optimal_set"]),
        "target_mean_local_regret": target["local_regret"],
        "target_unobserved_selected_rate": float(not target["selected_action_observed"]),
        "target_unclosed_rate": float(not target["interval_closed"]),
        "panel_sum_local_regret": panel["sum_local_regret"],
        "panel_wrong_action_count": panel["state_count"] - panel["selected_optimal_count"],
        "panel_unobserved_selected_count": sum(not s["selected_action_observed"] for s in panel["states"]),
        "panel_unclosed_count": sum(not s["interval_closed"] for s in panel["states"]),
        **{f"mean_absolute_{key}": mean([abs(row[key]) for row in observed])
           for key in ("A_transition_error", "D_continuation_error", "total_error")}}


def point_estimates(contexts):
    values = {arm: [metrics(c["arms"][arm]["evaluation"]) for c in contexts] for arm in ARMS}
    keys = list(values["CACHED"][0]) if contexts else []
    return {"paired_context_instances": len(contexts),
        **{arm: {key: mean([row[key] for row in values[arm] if row[key] is not None]) for key in keys} for arm in ARMS},
        "VARIANCE_minus_CACHED": {key: differences([v[key] - c[key]
            for c, v in zip(values["CACHED"], values["VARIANCE"])
            if c[key] is not None and v[key] is not None]) for key in keys}}


def primary_statistics(repetitions):
    """First average all fixed contexts within a stream, then compute its MC interval."""
    complete = [rep for rep in repetitions if rep["complete"]]
    result = {"complete_replicate_count": len(complete), "unit": "one suffix stream, equal context weights"}
    for key in PRIMARY:
        values = {arm: [mean([metrics(c["arms"][arm]["evaluation"])[key] for c in rep["contexts"]])
                       for rep in complete] for arm in ARMS}
        result[key] = {f"{arm}_mean": mean(values[arm]) for arm in ARMS}
        result[key]["VARIANCE_minus_CACHED"] = monte_carlo_interval([
            variance - cached for cached, variance in zip(values["CACHED"], values["VARIANCE"])])
    return result


def arm_totals(repetitions):
    """All actual arms count, including partial pairs and excluded repetitions."""
    output = {}
    for arm in ARMS:
        locals_ = [c["arms"][arm]["local"] for rep in repetitions for c in rep["contexts"] if arm in c.get("arms", {})]
        maps = {field: Counter() for field in ("provider_counts", "seconds_by_stage", "work_counts")}
        reasons, stop_counts = Counter(), Counter()
        for local in locals_:
            maps["provider_counts"].update(local["provider_counts"])
            for field in ("seconds_by_stage", "work_counts"):
                maps[field].update(local["accounting"][field])
            reasons[local["stop_reason"]] += 1
            index = local["first_original_stop_index"]
            stop_counts["gap_separated"] += index is not None
            stop_counts["batches_after_first_original_stop"] += local["completed_batches"] - index if index is not None else 0
        seconds = [local["accounting"]["whole_run_seconds"] for local in locals_]
        output[arm] = {"actual_arm_count": len(locals_), **{key: dict(value) for key, value in maps.items()},
            "whole_run_seconds": math.fsum(seconds), "mean_arm_seconds": mean(seconds),
            "stop_reasons": dict(reasons), "original_stop_diagnostics": dict(stop_counts)}
    return output


def action_pair_points(contexts):
    output = {}
    for arm in ARMS:
        pairs = defaultdict(list)
        for context in contexts:
            for row in context["arms"][arm]["evaluation"]["target"]["pair_margins"]:
                pairs[tuple(row["actions"])].append(row)
        output[arm] = [{"actions": list(pair), "observed_both_count": sum(row["observed_both"] for row in rows),
            "mean_margins": {key: mean([row[key] for row in rows if row[key] is not None])
                            for key in ("q_star_difference", "q_hat_difference", "A_transition_error_difference",
                                        "D_continuation_error_difference", "total_error_difference")}}
            for pair, rows in sorted(pairs.items())]
    return output


def summarize(payload):
    started = perf_counter()
    plan, repetitions = payload["plan"], payload["repetitions"]
    contexts = plan["contexts"]
    planned = {row["context_index"]: row for row in contexts}
    identities = [{key: row.get(key) for key in IDENTITY_FIELDS} for row in contexts]
    checks = defaultdict(list)
    checks["frozen_cohort"] = [len(contexts) == plan["context_count"] == 22,
        Counter(c["group"] for c in contexts) == {"improvement": 7, "regression": 13, "old_witness_only": 2},
        sum(c["source_v20_changed"] for c in contexts) == 20, sum(c["source_old_witness"] for c in contexts) == 10,
        sum(c["requested_batch_count"] for c in contexts) == plan["batches_per_arm_per_replicate"] == 494]
    checks["frozen_repetitions"] = [len(repetitions) == plan["replicate_count"] == 64,
        [{"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"]} for rep in repetitions] ==
        plan["replicates"] == [{"replicate_index": r, "base_seed": 922001 + r} for r in range(64)]]
    checks["persisted_before_truth"] = [payload["all_sampling_endpoints_closed_before_oracle"], not payload["endpoint_reload_uses_provider"]]
    restoration = payload["restoration_validation"]
    checks["common_snapshot_restoration"] = [len(restoration["contexts"]) == 22, restoration["all_passed"]] + [row["status"] == "READY" for row in restoration["contexts"]]
    eligible, summaries, incomplete = [], [], []
    initial = {row["identity"]["context_index"]: row for row in payload["initial_evaluations"]}
    for rep in repetitions:
        rep_contexts = rep["contexts"]
        same_identities = [{key: c["identity"].get(key) for key in IDENTITY_FIELDS} for c in rep_contexts] == identities
        checks["replicate_identities"].append(same_identities)
        complete_pairs = 0
        for context in rep_contexts:
            index = context["identity"]["context_index"]
            fixed = planned[index]
            if not context["arms"]:
                incomplete.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], **context})
                continue
            K, initial_batches = fixed["requested_batch_count"], fixed["initial_batches"]
            checks["fixed_K"].append(context["requested_batch_count"] == K and context["initial_batches"] == initial_batches and initial_batches + K <= 128)
            checks["arm_rotation"].append(context["run_order"] == list(ARMS if (rep["replicate_index"] + index) % 2 == 0 else reversed(ARMS)))
            pair_complete = context["initial_snapshot_validation"]["passed"]
            for arm in ARMS:
                current = context["arms"][arm]
                local = current["local"]
                n, provider = local["completed_batches"], local["provider_counts"]
                reset = local["initial_batches_matches_common"] and local["initial_batches"] == initial_batches
                checks["reset_from_common"].append(reset)
                checks["provider_and_batch_accounting"].append(local["requested_batch_count"] == K and 0 <= n <= K and local["final_batches"] == initial_batches + n and local["actual_draws"] == n * 256 and provider.get("row_requests", 0) == n and provider.get("physical_draws", 0) == 256 * n and provider.get("first_batch_requests", 0) + provider.get("repeat_batch_requests", 0) == n)
                checks["completion_labels"].append(local["completed_fixed_budget"] == (n == K))
                checks["first_request_reproduction"].append(current["first_request_validation"]["passed"])
                restored = current["endpoint_restoration"]["passed"]
                checks["endpoint_restoration"].append(restored)
                pair_complete &= n == K and reset and current["first_request_validation"]["passed"] and restored
                if not restored:
                    continue
                evaluation = current["evaluation"]
                target, panel = evaluation["target"], evaluation["panel"]
                checks["fixed_target_and_panel"].append(target["target_key"] == fixed["target_key"] and [s["key"] for s in panel["states"]] == fixed["panel"])
                checks["A_plus_D_identity"].append(target["identities_pass"] and target["maximum_absolute_identity_residual"] <= TOL)
            checks["completion_labels"].append(context["paired_complete"] == pair_complete)
            complete_pairs += pair_complete
            if not pair_complete:
                incomplete.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
                    "identity": context["identity"], "status": context["status"], "requested_batch_count": K,
                    "arms": {arm: {"local": context["arms"][arm]["local"],
                                  "first_request_validation": context["arms"][arm]["first_request_validation"],
                                  "endpoint_restoration": context["arms"][arm]["endpoint_restoration"]} for arm in ARMS}})
        complete = same_identities and complete_pairs == len(contexts)
        checks["replicate_complete_label"].append(rep["complete"] == complete)
        checked_rep = {**rep, "complete": complete}
        if complete:
            eligible.append(checked_rep)
        values = {arm: {key: mean([metrics(c["arms"][arm]["evaluation"])[key]
                                  for c in rep_contexts if "evaluation" in c["arms"].get(arm, {})]) for key in PRIMARY} for arm in ARMS}
        summaries.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
            "status": rep["status"], "complete": complete, "complete_pair_count": complete_pairs,
            "evaluated_context_count_by_arm": {arm: sum("evaluation" in c["arms"].get(arm, {}) for c in rep_contexts) for arm in ARMS},
            **values, "VARIANCE_minus_CACHED": {key: values["VARIANCE"][key] - values["CACHED"][key]
                if values["VARIANCE"][key] is not None and values["CACHED"][key] is not None else None for key in PRIMARY},
            "primary_eligible": complete})
    all_costs = arm_totals(repetitions)
    all_complete_contexts = [c for rep in eligible for c in rep["contexts"]]
    context_points = []
    for fixed in contexts:
        index = fixed["context_index"]
        rows = [c for c in all_complete_contexts if c["identity"]["context_index"] == index]
        context_points.append({"identity": {key: fixed.get(key) for key in IDENTITY_FIELDS},
            "requested_batch_count": fixed["requested_batch_count"], "initial_batches": fixed["initial_batches"],
            "common_start": metrics(initial[index]) if index in initial else None,
            "point_estimates": point_estimates(rows), "target_action_pair_margins": action_pair_points(rows)})
    # Reconcile total physical work against every executed arm, not just primary-eligible streams.
    accounting = payload["accounting"]
    arm_count = sum(value["actual_arm_count"] for value in all_costs.values())
    checks["clone_reset_count"] = [accounting.get("local_arm_run_count", 0) == arm_count,
        accounting.get("reset_from_original_common_snapshot_count", 0) == arm_count]
    checks["source_snapshot_validation"] = [len(payload["plan_snapshot_validation"]) == 22] + [row["passed"] for row in payload["plan_snapshot_validation"]]
    checks["total_physical_work"] = [accounting["warm_provider_calls"] == 0, accounting["warm_physical_draws"] == 0,
        accounting["local_physical_batches"] == sum(value["provider_counts"].get("row_requests", 0) for value in all_costs.values()),
        accounting["local_physical_draws"] == sum(value["provider_counts"].get("physical_draws", 0) for value in all_costs.values()),
        abs(accounting.get("local_allocation_wall_seconds", 0) - math.fsum(value["whole_run_seconds"] for value in all_costs.values())) <= TOL]
    checks["physical_cost_by_arm"] = [accounting["provider_counts_by_arm"][arm] == all_costs[arm]["provider_counts"] for arm in ARMS]
    checks["complete_replicate_count"] = [payload["complete_repetition_count"] == len(eligible)]
    if len(eligible) == 64:
        checks["full_campaign_budget"] = [arm_count == plan["expected_arm_count"] == 2816,
            accounting["local_physical_batches"] == plan["expected_physical_batches"] == 63232,
            accounting["local_physical_draws"] == plan["expected_physical_draws"] == 16187392]
    results = {name: {"passed": all(values), "checked": len(values), "failed": sum(not value for value in values)} for name, values in checks.items()}
    output = {
        "schema": "acfqp.controlled_predictive_repetition_analysis.v22", "status": payload["status"],
        "declared_replicate_count": 64, "actual_replicate_count": len(repetitions), "complete_replicate_count": len(eligible),
        "excluded_replicate_count": len(repetitions) - len(eligible), "context_count": len(contexts),
        "group_counts": plan["group_counts"], "primary": primary_statistics(eligible),
        "complete_stream_point_estimates": point_estimates(all_complete_contexts),
        "groups": {group: point_estimates([c for c in all_complete_contexts if c["identity"]["group"] == group])
                   for group in ("improvement", "regression", "old_witness_only")},
        "contexts": context_points, "repetitions": summaries, "incomplete_context_instances": incomplete,
        "all_actual_arm_costs": all_costs, "accounting": accounting,
        "restoration_validation": payload["restoration_validation"], "checks": results,
        "plan_snapshot_validation": payload["plan_snapshot_validation"],
        "elapsed_seconds_before_report_serialization": payload["elapsed_seconds_before_report_serialization"],
        "all_analysis_checks_passed": all(row["passed"] for row in results.values()),
        "analysis_seconds": perf_counter() - started,
        "scope": "Conditional on the fixed exposed V21 common snapshots. The primary Monte Carlo unit is a complete suffix stream with equal weights for all22 contexts; only streams with all pairs matched are included. Context/group/A-D/panel estimates are secondary point estimates. Panel states are dependent and unweighted by reach probability. Local optimal-continuation action regret is not complete-policy value. Every actual arm is charged, including excluded streams; missing streams preclude an unconditional comparison.",
        "difference_direction": "VARIANCE minus CACHED; negative means improvement, positive regression, zero equality for all reported error, regret and unresolved-count metrics.",
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_repetitions_v22.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_repetition_analysis_v22.json"))
    args = parser.parse_args()
    started = perf_counter()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    read_seconds = perf_counter() - started
    result = summarize(payload)
    result["analysis_result_read_seconds"] = read_seconds
    started = perf_counter()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "complete_replicate_count": result["complete_replicate_count"],
        "all_analysis_checks_passed": result["all_analysis_checks_passed"],
        "analysis_serialization_seconds": perf_counter() - started}))


if __name__ == "__main__":
    main()
