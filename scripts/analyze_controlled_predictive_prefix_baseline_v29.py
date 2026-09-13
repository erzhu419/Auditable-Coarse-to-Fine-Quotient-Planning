#!/usr/bin/env python3
"""Compare retained prefix policies with their already acquired V28 endpoints."""
from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import TOL, differences, mean, monte_carlo_interval
from analyze_controlled_predictive_new_starts_v28 import (
    IDENTITY_FIELDS, matched_budget, policy_metrics, stream_statistics as endpoint_stream_statistics)

ENDPOINTS = ("CACHED", "VARIANCE")
ARMS = ("PREFIX", *ENDPOINTS)
POLICY_METRICS = ("total_regret", "first_action_regret", "continuation_regret", "optimal_policy_rate")
COST_METRICS = ("independent_query_seconds",)
CHANGE_METRICS = ("policy_repaired_rate", "policy_new_error_rate", "first_action_repaired_rate",
    "first_action_new_error_rate", "initial_action_changed_rate")
DIAGNOSTIC_METRICS = ("missing_probability", "weighted_unobserved_choices", "defined_regret_lower_bound", "policy_unavailable_rate")


def cost_metrics(row):
    return row["costs"]


def diagnostic_metrics(row):
    value = row["evaluation"]
    return {"missing_probability": value["missing_probability"], "weighted_unobserved_choices": value["weighted_unobserved_choices"],
        "defined_regret_lower_bound": value["first_action_regret"] + value["defined_continuation_regret"],
        "policy_unavailable_rate": float(not value["policy_evaluable"])}


def row_for(context, arm, baselines):
    return baselines[context["prefix_context_index"]] if arm == "PREFIX" else context["arms"][arm]


def paired(values, metric, *, interval):
    result = monte_carlo_interval(values) if interval else differences(values)
    if metric in (*POLICY_METRICS, *COST_METRICS):
        high = metric == "optimal_policy_rate"
        result.update(improved=result["positive" if high else "negative"], same=result["zero"],
            worse=result["negative" if high else "positive"])
    return result


def cohort_means(contexts, baselines, value_function, keys):
    boards = defaultdict(list)
    for context in contexts:
        boards[context["identity"]["board_index"]].append(context)
    return {arm: {key: mean([mean([value_function(row_for(c, arm, baselines))[key] for c in rows])
        for rows in boards.values()]) for key in keys} for arm in ARMS}


def stream_statistics(repetitions, baselines, value_function, keys):
    streams = []
    for rep in repetitions:
        values = cohort_means(rep["contexts"], baselines, value_function, keys)
        streams.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "arms": values,
            "comparisons": {f"{arm}_minus_PREFIX": {key: values[arm][key] - values["PREFIX"][key] for key in keys} for arm in ENDPOINTS}})
    return {"stream_count": len(streams), "unit": "one V28 suffix stream conditional on the same fixed prefix policies",
        "arm_means": {arm: {key: mean([s["arms"][arm][key] for s in streams]) for key in keys} for arm in ARMS},
        "comparisons": {f"{arm}_minus_PREFIX": {key: paired([s["comparisons"][f"{arm}_minus_PREFIX"][key] for s in streams], key, interval=True)
            for key in keys} for arm in ENDPOINTS}}, streams


def changes(context, arm, baselines):
    before = baselines[context["prefix_context_index"]]["evaluation"]
    after = context["arms"][arm]["evaluation"]
    before_optimal, after_optimal = before["total_regret"] <= TOL, after["total_regret"] <= TOL
    return {"policy_repaired_rate": float(not before_optimal and after_optimal),
        "policy_new_error_rate": float(before_optimal and not after_optimal),
        "first_action_repaired_rate": float(before["first_action_wrong"] and not after["first_action_wrong"]),
        "first_action_new_error_rate": float(not before["first_action_wrong"] and after["first_action_wrong"]),
        "initial_action_changed_rate": float(before["initial_action"] != after["initial_action"])}


def change_statistics(repetitions, baselines):
    result = {}
    for arm in ENDPOINTS:
        rows = [c for r in repetitions for c in r["contexts"]]
        result[arm] = {key: {"context_instance_count": int(sum(changes(c, arm, baselines)[key] for c in rows)),
            "stream_interval": {name: value for name, value in monte_carlo_interval([
                mean([changes(c, arm, baselines)[key] for c in r["contexts"]]) for r in repetitions]).items()
                if name not in ("negative", "zero", "positive")}} for key in CHANGE_METRICS}
    return result


def points(contexts, baselines, value_function, keys):
    return {"endpoint_context_instances": len(contexts),
        "unique_prefix_context_count": len({c["prefix_context_index"] for c in contexts}),
        "arm_means": cohort_means(contexts, baselines, value_function, keys),
        "comparisons": {f"{arm}_minus_PREFIX": {key: paired([
            value_function(c["arms"][arm])[key] - value_function(baselines[c["prefix_context_index"]])[key] for c in contexts], key, interval=False)
            for key in keys} for arm in ENDPOINTS}}


def valid_policy(row):
    value = row.get("evaluation")
    if not value or not row["evaluation_validation"]["passed"]:
        return False
    return (value["policy_evaluable"] and value["identities_pass"] and value["reach_probability_pass"]
        and abs(value["terminal_probability"] + value["missing_probability"] - 1.) <= TOL
        and abs(value["total_regret"] - value["first_action_regret"] - value["continuation_regret"]) <= TOL)


def valid_diagnostic(row):
    value = row.get("evaluation")
    return bool(value and row["evaluation_validation"]["passed"] and row["first_action_validation"]["passed"]
        and value["reach_probability_pass"] and abs(value["terminal_probability"] + value["missing_probability"] - 1.) <= TOL
        and (not value["policy_evaluable"] or valid_policy(row)))


def endpoint_reproduction(repetitions, reference):
    cost_reps = [r for r in repetitions if r["source_valid"]]
    quality_reps = [r for r in repetitions if r["complete"]]
    checks = {}
    for name, reps, function, keys, source_key in (
        ("quality", quality_reps, policy_metrics, ("total_regret",), "quality_streams"),
        ("cost", cost_reps, cost_metrics, ("independent_query_seconds", "prefix_sampling_seconds", "single_query_prepare_seconds", "local_whole_run_seconds"), "cost_streams")):
        _, streams = endpoint_stream_statistics(reps, function, keys)
        checks[name] = {"stream_count": len(streams), "source_stream_count": len(reference[source_key]),
            "passed": streams == reference[source_key], "numeric_comparison": "EXACT"}
    return {"comparisons": checks, "all_passed": all(row["passed"] for row in checks.values())}


def summarize(payload, reference):
    started = perf_counter()
    plan, repetitions = payload["plan"], payload["repetitions"]
    baselines = {row["context_index"]: row for row in payload["prefix_baselines"]}
    identities = [{key: c[key] for key in IDENTITY_FIELDS} for c in plan["contexts"]]
    checks = defaultdict(list)
    checks["frozen_contexts_streams_and_comparisons"] = [len(plan["boards"]) == plan["board_count"] == 16,
        len(plan["contexts"]) == plan["context_count"] == 160, plan["query_count"] == 10,
        len(repetitions) == plan["replicate_count"] == 16,
        [{"replicate_index": r["replicate_index"], "base_seed": r["base_seed"]} for r in repetitions] == plan["replicates"],
        plan["primary_comparisons"] == [[arm, "PREFIX"] for arm in ENDPOINTS],
        plan["primary_metrics"] == ["total_regret", "independent_query_seconds"],
        all([c["query_name"] for c in plan["contexts"] if c["board_index"] == b["board_index"]] == plan["source_query_order"] for b in plan["boards"])]
    checks["one_prefix_per_fixed_context"] = [len(payload["prefix_baselines"]) == len(baselines) == 160,
        [row["identity"] for row in payload["prefix_baselines"]] == identities,
        all(row["context_index"] == row["identity"]["context_index"] for row in baselines.values())]
    checks["source_plan_binding"] = [payload["plan_binding_validation"]["passed"]]
    for baseline in baselines.values():
        checks["prefix_source_validity_labels"].append(baseline["source_valid"] == baseline["source_validation"]["passed"])
        costs = baseline["costs"]
        checks["prefix_full_independent_cost"].append(abs(costs["independent_query_seconds"] - costs["prefix_sampling_seconds"] - costs["single_query_prepare_seconds"]) <= TOL)
        value = baseline.get("evaluation")
        if value:
            checks["prefix_probability_conservation"].append(value["reach_probability_pass"] and abs(value["terminal_probability"] + value["missing_probability"] - 1.) <= TOL)
            checks["prefix_missing_values_not_imputed"].append(value["policy_evaluable"] == (value["missing_probability"] == 0)
                and (value["policy_evaluable"] or all(value[k] is None for k in ("v_pi", "total_regret", "continuation_regret"))))
            if value["policy_evaluable"]:
                checks["prefix_regret_decomposition"].append(valid_policy(baseline))
    quality_reps, cost_reps, diagnostic_reps, statuses, exclusions = [], [], [], [], []
    for rep in repetitions:
        identities_equal = [c["identity"] for c in rep["contexts"]] == identities
        checks["retained_endpoint_identities"].append(identities_equal)
        source = identities_equal and rep["source_valid"]
        quality = identities_equal and rep["complete"]
        diagnostics = True
        for context in rep["contexts"]:
            baseline = baselines[context["prefix_context_index"]]
            binding = context["prefix_context_index"] == context["identity"]["context_index"] and baseline["identity"] == context["identity"] and context["prefix_binding_validation"]["passed"]
            checks["prefix_endpoint_identity_binding"].append(binding)
            source_valid = binding and context["source_valid"] and baseline["source_valid"]
            budget, _ = matched_budget(context)
            checks["source_actual_budget_match"].append(context["budget_matched"] == budget)
            rows = [baseline, *(context["arms"][arm] for arm in ENDPOINTS)]
            diagnostics_valid = source_valid and all(valid_diagnostic(row) for row in rows)
            complete = source_valid and budget and diagnostics_valid and all(valid_policy(row) for row in rows)
            for arm in ENDPOINTS:
                end = context["arms"][arm]
                checks["baseline_endpoint_cost_components"].append(
                    baseline["costs"]["prefix_sampling_seconds"] == end["costs"]["prefix_sampling_seconds"]
                    and baseline["costs"]["single_query_prepare_seconds"] == end["costs"]["single_query_prepare_seconds"]
                    and abs(end["costs"]["independent_query_seconds"] - baseline["costs"]["independent_query_seconds"] - end["costs"]["local_whole_run_seconds"]) <= TOL)
            source &= source_valid
            quality &= complete
            diagnostics &= diagnostics_valid
            if not complete:
                exclusions.append({"replicate_index": rep["replicate_index"], "identity": context["identity"],
                    "source_valid": source_valid, "budget_matched": budget,
                    "prefix_policy_evaluable": baseline.get("evaluation", {}).get("policy_evaluable", False),
                    "prefix_missing_probability": baseline.get("evaluation", {}).get("missing_probability"),
                    "prefix_source_validation": baseline["source_validation"], "prefix_evaluation_validation": baseline["evaluation_validation"],
                    "endpoint_status": context["status"]})
        if source:
            cost_reps.append(rep)
        if quality:
            quality_reps.append(rep)
        if source and diagnostics:
            diagnostic_reps.append(rep)
        statuses.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
            "comparison_source_valid": bool(source), "comparison_complete": bool(quality), "comparison_diagnostics_valid": bool(source and diagnostics)})
    reproduction = endpoint_reproduction(repetitions, reference)
    checks["V28_endpoint_metric_reproduction"] = [reproduction["all_passed"]]
    account = payload["accounting"]
    checks["all_historical_fees_retained"] = [payload["source_actual_costs"] == reference["all_actual_arm_costs"], payload["source_accounting"] == reference["accounting"],
        account["historical_physical_batches"] == plan["historical_physical_batches"] == 164352,
        account["historical_physical_draws"] == plan["historical_physical_draws"] == 42074112]
    checks["one_evaluation_per_prefix_and_no_new_execution"] = [account["prefix_policy_evaluation_calls"] == plan["expected_prefix_evaluations"] == 160,
        payload["all_prefix_policies_bound_before_oracle"],
        *[account[key] == 0 for key in ("new_sampling_calls", "new_physical_batches", "new_physical_draws", "new_planner_solves", "new_model_restores", "endpoint_evaluation_calls")]]
    quality, quality_streams = stream_statistics(quality_reps, baselines, policy_metrics, ("total_regret",))
    cost, cost_streams = stream_statistics(cost_reps, baselines, cost_metrics, COST_METRICS)
    components, _ = stream_statistics(quality_reps, baselines, policy_metrics, POLICY_METRICS[1:])
    continuous, _ = stream_statistics(diagnostic_reps, baselines, diagnostic_metrics, DIAGNOSTIC_METRICS)
    source_contexts = [c for r in cost_reps for c in r["contexts"]]
    quality_contexts = [c for r in quality_reps for c in r["contexts"]]
    diagnostic_contexts = [c for r in diagnostic_reps for c in r["contexts"]]
    def selection(predicate):
        return {"quality_complete_mask": points([c for c in quality_contexts if predicate(c["identity"])], baselines, policy_metrics, POLICY_METRICS),
            "cost_source_valid_mask": points([c for c in source_contexts if predicate(c["identity"])], baselines, cost_metrics, COST_METRICS),
            "continuous_diagnostics": points([c for c in diagnostic_contexts if predicate(c["identity"])], baselines, diagnostic_metrics, DIAGNOSTIC_METRICS)}
    prefix_once = [{"identity": row["identity"], "source_valid": row["source_valid"], "costs": row["costs"],
        "evaluation": {key: row.get("evaluation", {}).get(key) for key in ("v_pi", "v_star", "total_regret", "first_action_regret", "continuation_regret", "policy_evaluable", "initial_action", "first_action_wrong", "missing_probability", "weighted_unobserved_choices", "defined_continuation_regret")}}
        for row in baselines.values()]
    result_checks = {name: {"passed": all(values), "checked": len(values), "failed": sum(not value for value in values)} for name, values in checks.items()}
    return {"schema": "acfqp.controlled_predictive_prefix_baseline_analysis.v29", "status": payload["status"],
        "comparison_source_valid_stream_count": len(cost_reps), "comparison_complete_stream_count": len(quality_reps),
        "comparison_diagnostic_stream_count": len(diagnostic_reps), "prefix_baselines_once": prefix_once,
        "primary_quality": quality, "primary_independent_query_cost": cost, "same_quality_mask_components": components,
        "policy_and_action_changes": change_statistics(quality_reps, baselines), "continuous_diagnostics": continuous,
        "whole_cohort_points": selection(lambda identity: True),
        "boards": [{"board_index": b["board_index"], "case_name": b["name"], **selection(lambda identity: identity["board_index"] == b["board_index"])} for b in plan["boards"]],
        "contexts": [{"identity": identity, **selection(lambda row: row["context_index"] == identity["context_index"])} for identity in identities],
        "quality_streams": quality_streams, "cost_streams": cost_streams, "stream_statuses": statuses,
        "incomplete_context_instances": exclusions, "V28_endpoint_reproduction": reproduction,
        "source_actual_costs": payload["source_actual_costs"], "source_accounting": payload["source_accounting"],
        "accounting": account, "checks": result_checks, "all_analysis_checks_passed": all(row["passed"] for row in result_checks.values()),
        "elapsed_seconds_before_report_serialization": payload["elapsed_seconds_before_report_serialization"], "analysis_seconds": perf_counter() - started,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False, "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Each of the160 prefix policies is evaluated once and referenced by sixteen retained suffix streams. Intervals describe paired endpoint-minus-fixed-prefix stream means, not repeated independent prefix observations. Policy repair/new error and first-action repair/new error are separate diagnostics. Costs reuse measured V28 components; added endpoint cost is acquisition expenditure, with no refund of historical work. Undefined prefix policies remain unavailable. These are fixed H2 retained-policy comparisons, not a validated adaptive stopping rule, full online algorithm or new scientific Gate."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_prefix_baseline_v29.json.gz"))
    parser.add_argument("--reference", type=Path, default=Path("reports/controlled_predictive_new_starts_analysis_v28.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_prefix_baseline_analysis_v29.json"))
    args = parser.parse_args()
    started = perf_counter()
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    read_seconds = perf_counter() - started
    result = summarize(payload, reference)
    result["analysis_result_read_seconds"] = read_seconds
    started = perf_counter()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "comparison_complete_stream_count": result["comparison_complete_stream_count"],
        "all_analysis_checks_passed": result["all_analysis_checks_passed"], "analysis_serialization_seconds": perf_counter() - started}))


if __name__ == "__main__":
    main()
