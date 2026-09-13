#!/usr/bin/env python3
"""Analyze the full retained V32 checkpoint curve on one common stream mask."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import TOL
from analyze_controlled_predictive_transfer_v32 import (
    ARMS, COMPARISON, COST_METRICS, IDENTITY_FIELDS, POLICY_METRICS,
    policy_metrics, cost_metrics, stream_statistics, points, policy_changes)

SOURCE_VALIDATIONS = ("source_validation", "prefix_validation", "chronology_validation", "endpoint_validation")
COVERAGE_METRICS = ("policy_unavailable_rate", "missing_probability", "weighted_unobserved_choices", "defined_regret_lower_bound")


def checkpoint(row, budget):
    return next((value for value in row["checkpoints"] if value["budget"] == budget), None)


def valid_diagnostic(value):
    if value is None or not value["evaluation_validation"]["passed"] or not value.get("evaluation"):
        return False
    policy = value["evaluation"]
    if not (policy["reach_probability_pass"] and abs(policy["terminal_probability"] + policy["missing_probability"] - 1.) <= TOL):
        return False
    if policy["policy_evaluable"]:
        return bool(policy["identities_pass"] and abs(policy["total_regret"] - policy["first_action_regret"] - policy["continuation_regret"]) <= TOL)
    return all(policy[key] is None for key in ("v_pi", "total_regret", "continuation_regret"))


def valid_policy(value):
    return valid_diagnostic(value) and value["evaluation"]["policy_evaluable"]


def coverage_metrics(row):
    value = row["evaluation"]
    return {"policy_unavailable_rate": float(not value["policy_evaluable"]), "missing_probability": value["missing_probability"],
        "weighted_unobserved_choices": value["weighted_unobserved_choices"],
        "defined_regret_lower_bound": value["first_action_regret"] + value["defined_continuation_regret"]}


def projected_repetition(rep, budget):
    return {"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "contexts": [
        {"identity": context["identity"], "arms": {arm: {"evaluation": checkpoint(context["arms"][arm], budget)["evaluation"],
            "costs": context["arms"][arm]["original_costs"]} for arm in ARMS}} for context in rep["contexts"]]}


def original_cost_repetition(rep):
    return {"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "contexts": [
        {"identity": context["identity"], "arms": {arm: {"costs": context["arms"][arm]["original_costs"]} for arm in ARMS}}
        for context in rep["contexts"]]}


def old_costs_all(repetitions):
    result = {}
    for arm in ARMS:
        rows = [context["arms"][arm] for rep in repetitions for context in rep["contexts"]]
        stages, work = Counter(), Counter()
        for row in rows:
            stages.update(row["original_local_accounting"]["seconds_by_stage"])
            work.update(row["original_local_accounting"]["work_counts"])
        result[arm] = {"actual_arm_count_including_failures": len(rows), "seconds_by_stage": dict(stages), "work_counts": dict(work),
            "attributed_cost_totals": {key: math.fsum(row["original_costs"][key] for row in rows) for key in COST_METRICS}}
    return result


def within_arm_prefix_changes(repetitions, budget):
    result = {}
    for arm in ARMS:
        pairs = [{"identity": context["identity"], "arms": {"CACHED": {"evaluation": checkpoint(context["arms"][arm], 0)["evaluation"]},
            "GAP_FRONTIER": {"evaluation": checkpoint(context["arms"][arm], budget)["evaluation"]}}}
            for rep in repetitions for context in rep["contexts"]]
        result[arm] = policy_changes(pairs)
    return result


def summarize(payload, reference):
    started = perf_counter()
    plan, repetitions = payload["plan"], payload["repetitions"]
    budgets = plan["checkpoints"]
    identities = [{key: context[key] for key in IDENTITY_FIELDS} for context in plan["contexts"]]
    checks = defaultdict(list)
    prefixes = {row["context_index"]: row for row in payload["prefix_evaluations"]}
    checks["unique_prefix_evaluation_roster"] = [len(payload["prefix_evaluations"]) == len(prefixes) == plan["expected_prefix_evaluations"],
        [row["identity"] for row in payload["prefix_evaluations"]] == identities]
    checks["frozen_roster_and_checkpoint_curve"] = [budgets == [0, 4, 8, 16, 24, 32], plan["arms"] == list(ARMS),
        len(identities) == plan["context_count"] == 160, len(plan["boards"]) == plan["board_count"] == 16,
        plan["query_count"] == 10, len(repetitions) == plan["replicate_count"] == 16,
        [{key: rep[key] for key in ("replicate_index", "base_seed")} for rep in repetitions] == plan["replicates"]]
    source_reps, common_reps, endpoint_reps = [], [], []
    diagnostic_reps = {budget: [] for budget in budgets}
    statuses, exclusions = [], []
    for rep in repetitions:
        same_ids = [context["identity"] for context in rep["contexts"]] == identities
        checks["retained_context_order"].append(same_ids)
        source, common, endpoint = same_ids, same_ids, same_ids
        diagnostics = {budget: same_ids for budget in budgets}
        for context in rep["contexts"]:
            for arm in ARMS:
                row = context["arms"][arm]
                zero = checkpoint(row, 0)
                zero_bound = (row["prefix_context_index"] == context["identity"]["context_index"]
                    and zero is not None and zero.get("evaluation") == prefixes[row["prefix_context_index"]]["checkpoint"].get("evaluation"))
                checks["K0_reuses_bound_prefix_evaluation"].append(zero_bound)
                common &= zero_bound
                diagnostics[0] &= zero_bound
                actual_source = all(row[key]["passed"] for key in SOURCE_VALIDATIONS)
                checks["replay_source_validity_labels"].append(row["source_valid"] == actual_source)
                source &= actual_source
                checks["all_checkpoints_retained_in_order"].append([value["budget"] for value in row["checkpoints"]] == budgets)
                reference_passed = row["reference_value_validation"]["passed"]
                checks["K32_reference_value_validation"].append(reference_passed)
                endpoint &= valid_policy(checkpoint(row, 32)) and reference_passed
                for budget in budgets:
                    value = checkpoint(row, budget)
                    diagnostic_valid, policy_valid = valid_diagnostic(value), valid_policy(value)
                    diagnostics[budget] &= diagnostic_valid
                    common &= policy_valid and reference_passed
                    if value is not None and value.get("evaluation"):
                        policy = value["evaluation"]
                        checks["checkpoint_draw_count_and_labels"].append(value["spent_batches"] == plan["prefix_batches_per_board"] + budget
                            and value["policy_evaluable"] == policy["policy_evaluable"])
                        checks["policy_availability_and_no_imputation"].append(policy["policy_evaluable"] == (policy["missing_probability"] == 0.)
                            and (policy["policy_evaluable"] or all(policy[key] is None for key in ("v_pi", "total_regret", "continuation_regret"))))
                        if value["evaluation_validation"]["passed"]:
                            checks["policy_probability_and_regret_identities"].append(diagnostic_valid)
                    if not actual_source or not policy_valid or not reference_passed:
                        exclusions.append({"replicate_index": rep["replicate_index"], "identity": context["identity"], "arm": arm,
                            "budget": budget, "source_valid": actual_source, "evaluation_valid": diagnostic_valid,
                            "policy_evaluable": bool(value and value.get("evaluation", {}).get("policy_evaluable")), "K32_reference_value_valid": reference_passed})
        common, endpoint = source and common, source and endpoint
        if source: source_reps.append(rep)
        if common: common_reps.append(rep)
        if endpoint: endpoint_reps.append(rep)
        for budget in budgets:
            if source and diagnostics[budget]: diagnostic_reps[budget].append(rep)
        statuses.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "source_valid": source,
            "common_curve_complete": common, "K32_complete": endpoint,
            "diagnostic_valid_by_budget": {str(budget): source and diagnostics[budget] for budget in budgets}})
    curve = []
    for budget in budgets:
        projected = [projected_repetition(rep, budget) for rep in common_reps]
        quality, _ = stream_statistics(projected, policy_metrics, POLICY_METRICS)
        rows = [context for rep in projected for context in rep["contexts"]]
        coverage_projected = [projected_repetition(rep, budget) for rep in diagnostic_reps[budget]]
        coverage_rows = [context for rep in coverage_projected for context in rep["contexts"]]
        diagnostics, _ = stream_statistics(coverage_projected, coverage_metrics, COVERAGE_METRICS)
        coverage_counts = {arm: {"diagnostic_context_instance_count": len(coverage_rows),
            "unique_context_count": len({context["identity"]["context_index"] for context in coverage_rows}),
            "policy_evaluable_instance_count": sum(context["arms"][arm]["evaluation"]["policy_evaluable"] for context in coverage_rows),
            "policy_unavailable_instance_count": sum(not context["arms"][arm]["evaluation"]["policy_evaluable"] for context in coverage_rows),
            "mean_missing_probability": math.fsum(context["arms"][arm]["evaluation"]["missing_probability"] for context in coverage_rows) / len(coverage_rows) if coverage_rows else None}
            for arm in ARMS}
        point = points(rows, policy_metrics, POLICY_METRICS)
        entry = {"supplemental_batches": budget, "available_model_draws": plan["samples_per_batch"] * (plan["prefix_batches_per_board"] + budget),
            "common_quality_stream_count": len(common_reps), "quality": quality, "quality_points": point,
            "policy_changes_GAP_FRONTIER_vs_CACHED": policy_changes(rows), "policy_changes_vs_fixed_K0": within_arm_prefix_changes(common_reps, budget),
            "coverage_diagnostic_stream_count": len(diagnostic_reps[budget]), "coverage": diagnostics, "coverage_counts": coverage_counts}
        if budget == 0:
            entry["quality"] = {"unit": "fixed prefix policies evaluated once per context; no independent suffix observations", "arm_means": point["arm_means"],
                COMPARISON: {key: point[COMPARISON][key]["mean"] for key in POLICY_METRICS}, "confidence_intervals": None}
            entry["coverage"] = {"unit": "fixed prefix coverage; no independent suffix observations", "arm_means": points(coverage_rows, coverage_metrics, COVERAGE_METRICS)["arm_means"], "confidence_intervals": None}
            entry["unique_prefix_context_count"] = len({context["identity"]["context_index"] for rep in common_reps for context in rep["contexts"]})
        curve.append(entry)
    _, endpoint_streams = stream_statistics([projected_repetition(rep, 32) for rep in endpoint_reps], policy_metrics, ("total_regret",))
    _, cost_streams = stream_statistics([original_cost_repetition(rep) for rep in source_reps], cost_metrics, COST_METRICS)
    reproduction = {"quality": {"passed": endpoint_streams == reference["quality_streams"], "stream_count": len(endpoint_streams)},
        "cost": {"passed": cost_streams == reference["cost_streams"], "stream_count": len(cost_streams)}, "numeric_comparison": "EXACT"}
    checks["K32_original_stream_metrics_reproduced"] = [reproduction["quality"]["passed"], reproduction["cost"]["passed"]]
    accounting_checks(payload, reference, checks)
    all_costs = old_costs_all(repetitions)
    for arm in ARMS:
        checks["all_original_local_costs_retained"].append(all_costs[arm]["attributed_cost_totals"] == reference["all_actual_arm_costs"][arm]["attributed_cost_totals"]
            and all_costs[arm]["seconds_by_stage"] == reference["all_actual_arm_costs"][arm]["seconds_by_stage"]
            and all_costs[arm]["work_counts"] == reference["all_actual_arm_costs"][arm]["work_counts"])
    check_rows = {key: {"passed": all(values), "checked": len(values), "failed": sum(not value for value in values)} for key, values in checks.items()}
    return {"schema": "acfqp.controlled_predictive_budget_curve_analysis.v33", "source_valid_stream_count": len(source_reps),
        "common_curve_complete_stream_count": len(common_reps), "K32_complete_stream_count": len(endpoint_reps),
        "checkpoint_curve": curve, "metric_definitions": {"optimal_policy_rate": "mean V27 policy_optimal indicator (total_regret <= 1e-10)"}, "stream_statuses": statuses, "excluded_checkpoint_instances": exclusions,
        "K32_source_reproduction": reproduction, "all_original_arm_costs_including_failures": all_costs,
        "original_source_accounting": payload["original_source_accounting"], "accounting": payload["accounting"],
        "checks": check_rows, "all_analysis_checks_passed": all(row["passed"] for row in check_rows.values()),
        "analysis_seconds": perf_counter() - started,
        "scope": "All checkpoints use the same whole-stream quality mask over all 160 contexts, both methods and every checkpoint. K>0 intervals are pointwise paired suffix-stream Monte Carlo intervals conditional on the fixed V32 boards and prefixes, not a simultaneous curve or population claim. K0 reuses one evaluation per fixed prefix. The horizontal axis counts available model draws; historical full-budget fees remain and replay/evaluation costs are additional. This retained curve makes no runtime-saving claim, selects no best budget and introduces no Gate."}


def accounting_checks(payload, reference, checks):
    plan, account, old = payload["plan"], payload["accounting"], payload["original_source_accounting"]
    checks["bound_source_and_retained_policy_stream"] = [payload["plan_binding_validation"]["passed"], payload["source_endpoint_stream_complete"],
        not payload["oracle_used_for_replay_selection"], payload["endpoint_evaluation_replanning_calls"] == 0,
        account["policy_pair_records_written"] == plan["expected_pair_count"]]
    checks["source_accounting_retained_exactly"] = [old == reference["accounting"]]
    checks["no_new_physical_sampling"] = [account[key] == 0 for key in ("new_provider_calls", "new_sampling_calls", "new_physical_draws")]
    checks["historical_physical_costs_not_refunded"] = [old["historical_physical_batches"] + old["total_physical_batches"] == account["historical_physical_batches"] == plan["source_historical_physical_batches"],
        old["historical_physical_draws"] + old["total_physical_draws"] == account["historical_physical_draws"] == plan["source_historical_physical_draws"]]
    checks["retained_sample_processing_accounted"] = [account.get("retained_batches_replayed", 0) == plan["expected_retained_batches_replayed"],
        account.get("retained_draws_replayed", 0) == plan["expected_retained_draws_replayed"]]
    checks["unique_evaluations_and_checkpoint_references"] = [account["prefix_policy_evaluation_calls"] == plan["expected_prefix_evaluations"] == 160,
        account["prefix_restores"] == plan["expected_model_restores"],
        account["policy_evaluation_calls"] == account["prefix_policy_evaluation_calls"] + account["checkpoint_policy_evaluation_calls"] == plan["expected_evaluation_count"],
        sum(len(row["checkpoints"]) for rep in payload["repetitions"] for context in rep["contexts"] for row in context["arms"].values()) == plan["expected_checkpoint_reference_count"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_budget_curve_v33.json.gz"))
    parser.add_argument("--reference", type=Path, default=Path("reports/controlled_predictive_transfer_analysis_v32.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_budget_curve_analysis_v33.json"))
    args = parser.parse_args()
    started = perf_counter()
    with gzip.open(args.input, "rt", encoding="utf-8") as reader:
        payload = json.load(reader)
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    read_seconds = perf_counter() - started
    result = summarize(payload, reference)
    result["analysis_result_read_seconds"] = read_seconds
    started = perf_counter()
    with args.output.open("x", encoding="utf-8") as writer:
        json.dump(result, writer, indent=2, allow_nan=False)
        writer.write("\n")
    print(json.dumps({"output": str(args.output), "common_curve_complete_stream_count": result["common_curve_complete_stream_count"],
        "all_analysis_checks_passed": result["all_analysis_checks_passed"], "analysis_serialization_seconds": perf_counter() - started}))


if __name__ == "__main__":
    main()
