#!/usr/bin/env python3
"""Compare the complete contemporary budget-cost curve with retained quality."""
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
    ARMS, COMPARISON, COST_METRICS, POLICY_METRICS, IDENTITY_FIELDS,
    policy_metrics, cost_metrics, stream_statistics, points, matched_budget, policy_changes)


def validation(row, budget, checks, source_binding=True):
    local, costs = row["local"], row["costs"]
    source = row["source_validation"]["passed"] and source_binding
    for key in ("reference_history_validation", "reference_policy_validation"):
        checks[key].append(row[key]["passed"])
        source &= row[key]["passed"]
    if budget == 32:
        checks["K32_reference_state_validation"].append(row["reference_state_validation"]["passed"])
        source &= row["reference_state_validation"]["passed"]
    checks["source_validity_labels"].append(row["source_valid"] == source)
    n = local["completed_batches"]
    checks["all_actual_batch_counts"].append(0 <= n <= budget and local["initial_batches"] == 32 and local["final_batches"] == 32+n
        and local["actual_draws"] == 256*n and local["provider_counts"].get("row_requests", 0) == n
        and local["provider_counts"].get("physical_draws", 0) == 256*n
        and local["provider_counts"].get("first_batch_requests", 0) + local["provider_counts"].get("repeat_batch_requests", 0) == n)
    checks["full_independent_query_cost"].append(costs["local_whole_run_seconds"] == local["accounting"]["whole_run_seconds"]
        and abs(costs["independent_query_seconds"] - math.fsum(costs[key] for key in COST_METRICS[1:])) <= TOL)
    value = row.get("evaluation")
    diagnostic = bool(value and row["evaluation_validation"]["passed"] and row["first_action_validation"]["passed"])
    reference = row["reference_value_validation"]["passed"]
    checks["retained_checkpoint_value_reproduction"].append(reference)
    if value:
        reach = value["reach_probability_pass"] and abs(value["terminal_probability"] + value["missing_probability"] - 1.) <= TOL
        checks["probability_conservation"].append(reach)
        checks["missing_policy_not_imputed"].append(value["policy_evaluable"] == (value["missing_probability"] == 0.)
            and (value["policy_evaluable"] or all(value[key] is None for key in ("v_pi", "total_regret", "continuation_regret"))))
        decomposition = not value["policy_evaluable"] or (value["identities_pass"] and abs(value["total_regret"] - value["first_action_regret"] - value["continuation_regret"]) <= TOL)
        checks["policy_regret_identity"].append(decomposition)
        diagnostic &= reach and decomposition
    return bool(source), bool(diagnostic and reference), bool(diagnostic and reference and value["policy_evaluable"])


def actual_costs(contexts):
    output = {}
    for arm in ARMS:
        rows = [context["arms"][arm] for context in contexts]
        providers, stages, work, stops = Counter(), Counter(), Counter(), Counter()
        for row in rows:
            local = row["local"]
            providers.update(local["provider_counts"])
            stages.update(local["accounting"]["seconds_by_stage"])
            work.update(local["accounting"]["work_counts"])
            stops[local["stop_reason"]] += 1
        output[arm] = {"actual_arm_count": len(rows), "provider_counts": dict(providers), "seconds_by_stage": dict(stages),
            "work_counts": dict(work), "stop_reasons": dict(stops),
            "completed_batches": sum(row["local"]["completed_batches"] for row in rows),
            "first_observation_batches": providers.get("first_batch_requests", 0), "repeat_observation_batches": providers.get("repeat_batch_requests", 0),
            "attributed_cost_totals": {key: math.fsum(row["costs"][key] for row in rows) for key in COST_METRICS}}
    return output


def source_stage_means(contexts):
    totals = actual_costs(contexts)
    return {arm: {"context_instance_count": len(contexts), "mean_seconds_by_stage": {
        key: seconds / len(contexts) for key, seconds in totals[arm]["seconds_by_stage"].items()}}
        for arm in ARMS}


def reference_projection(repetitions, reference_repetitions, arm):
    """Use the existing paired reducer with explicitly named output roles."""
    originals = {rep["replicate_index"]: rep for rep in reference_repetitions}
    return [{"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "contexts": [
        {"identity": current["identity"], "arms": {"CACHED": reference["arms"]["CACHED"], "GAP_FRONTIER": current["arms"][arm]}}
        for current, reference in zip(rep["contexts"], originals[rep["replicate_index"]]["contexts"])]} for rep in repetitions]


def comparison_to_full_budget(repetitions, reference_repetitions, arm, function, keys):
    result, _ = stream_statistics(reference_projection(repetitions, reference_repetitions, arm), function, keys)
    return {"stream_count": result["stream_count"], "current_arm": arm, "reference_arm": "CACHED", "reference_budget": 32,
        "current": result["arms"]["GAP_FRONTIER"], "reference": result["arms"]["CACHED"], "current_minus_reference": result[COMPARISON]}


def summarize(payload, reference):
    started = perf_counter()
    plan, repetitions = payload["plan"], payload["repetitions"]
    budgets = plan["budgets"]
    identities = [{key: row[key] for key in IDENTITY_FIELDS} for row in plan["contexts"]]
    checks = defaultdict(list)
    checks["frozen_complete_budget_cohort"] = [budgets == [4,8,16,24,32], plan["arms"] == list(ARMS),
        len(plan["boards"]) == plan["board_count"] == 16, len(identities) == plan["context_count"] == 160, plan["query_count"] == 10,
        len(repetitions) == plan["replicate_count"] == 16,
        [{key: rep[key] for key in ("replicate_index", "base_seed")} for rep in repetitions] == plan["replicates"]]
    by_budget = {budget: [] for budget in budgets}
    source_ids, quality_ids, statuses, exclusions = [], [], [], []
    per_budget_quality_ids = {budget: [] for budget in budgets}
    for rep in repetitions:
        same_ids = [context["identity"] for context in rep["contexts"]] == identities
        checks["frozen_context_order"].append(same_ids)
        source_flags, quality_flags = {budget: same_ids for budget in budgets}, {budget: same_ids for budget in budgets}
        contexts_by_budget = {budget: [] for budget in budgets}
        for context in rep["contexts"]:
            index = context["identity"]["context_index"]
            offset = (rep["replicate_index"] + index) % len(budgets)
            checks["budget_execution_rotation"].append(context["budget_run_order"] == budgets[offset:] + budgets[:offset])
            checks["canonical_retained_budget_order"].append([entry["budget"] for entry in context["budgets"]] == budgets)
            for budget_index, entry in enumerate(context["budgets"]):
                budget = entry["budget"]
                normalized = {"identity": context["identity"], "requested_batch_count": budget, "arms": entry["arms"]}
                contexts_by_budget[budget].append(normalized)
                rotation = (rep["replicate_index"] + index + budget_index) % 2
                checks["arm_execution_rotation"].append(entry["run_order"] == list(ARMS[rotation:] + ARMS[:rotation]))
                row_flags = [validation(entry["arms"][arm], budget, checks, payload["reference_binding_validation"]["passed"]) for arm in ARMS]
                source = all(flags[0] for flags in row_flags)
                matched, budget_type = matched_budget(normalized)
                complete = source and matched and all(flags[2] for flags in row_flags)
                checks["budget_pair_masks"].append(entry["source_valid"] == source and entry["budget_matched"] == matched and entry["paired_complete"] == complete)
                source_flags[budget] &= source
                quality_flags[budget] &= complete
                if not complete:
                    exclusions.append({"replicate_index": rep["replicate_index"], "identity": context["identity"], "budget": budget,
                        "source_valid": source, "budget_matched": matched, "budget_type": budget_type,
                        "evaluation_valid": all(flags[1] for flags in row_flags), "policy_evaluable": all(flags[2] for flags in row_flags)})
        for budget in budgets:
            by_budget[budget].append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "contexts": contexts_by_budget[budget]})
            if quality_flags[budget]: per_budget_quality_ids[budget].append(rep["replicate_index"])
        source, quality = all(source_flags.values()), all(quality_flags.values())
        if source: source_ids.append(rep["replicate_index"])
        if quality: quality_ids.append(rep["replicate_index"])
        statuses.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "common_source_valid": source,
            "common_quality_complete": quality, "source_valid_by_budget": source_flags, "quality_complete_by_budget": quality_flags})
    def selected(budget, ids):
        return [rep for rep in by_budget[budget] if rep["replicate_index"] in ids]
    curve, cross_budget = [], []
    old_curve = {row["supplemental_batches"]: row for row in reference["checkpoint_curve"]}
    for budget in budgets:
        quality_reps, cost_reps = selected(budget, quality_ids), selected(budget, source_ids)
        quality, _ = stream_statistics(quality_reps, policy_metrics, POLICY_METRICS)
        cost, _ = stream_statistics(cost_reps, cost_metrics, COST_METRICS)
        quality_cost, _ = stream_statistics(quality_reps, cost_metrics, COST_METRICS)
        quality_rows, cost_rows = ([context for rep in reps for context in rep["contexts"]] for reps in (quality_reps, cost_reps))
        reproduced, _ = stream_statistics(selected(budget, per_budget_quality_ids[budget]), policy_metrics, POLICY_METRICS)
        reproduction = reproduced == old_curve[budget]["quality"]
        checks["V33_pointwise_quality_reproduction"].append(reproduction)
        curve.append({"supplemental_batches": budget, "available_model_draws": 256*(32+budget),
            "common_quality_stream_count": len(quality_ids), "common_source_cost_stream_count": len(source_ids),
            "quality": quality, "independent_query_cost": cost, "same_quality_mask_cost": quality_cost,
            "quality_points": points(quality_rows, policy_metrics, POLICY_METRICS), "policy_changes": policy_changes(quality_rows),
            "source_cost_stage_means": source_stage_means(cost_rows),
            "V33_quality_reproduction": {"passed": reproduction, "numeric_comparison": "EXACT", "independent_per_budget_complete_stream_count": len(per_budget_quality_ids[budget])}})
        for arm in ARMS:
            cross_budget.append({"supplemental_batches": budget, "arm": arm,
                "quality": comparison_to_full_budget(quality_reps, selected(32, quality_ids), arm, policy_metrics, ("total_regret",)),
                "independent_query_cost": comparison_to_full_budget(cost_reps, selected(32, source_ids), arm, cost_metrics, ("independent_query_seconds",)),
                "same_quality_mask_cost": comparison_to_full_budget(quality_reps, selected(32, quality_ids), arm, cost_metrics, ("independent_query_seconds",))})
    all_rows = [context for budget in budgets for rep in by_budget[budget] for context in rep["contexts"]]
    actual = actual_costs(all_rows)
    checks["original_source_and_diagnostic_costs_retained"] = [payload["original_source_accounting"] == reference["original_source_accounting"],
        payload["source_diagnostic_accounting"] == reference["accounting"]]
    physical_checks(payload, actual, all_rows, checks)
    result_checks = {key: {"passed": all(values), "checked": len(values), "failed": sum(not value for value in values)} for key, values in checks.items()}
    return {"schema": "acfqp.controlled_predictive_budget_cost_analysis.v34", "common_quality_complete_stream_count": len(quality_ids),
        "common_source_cost_stream_count": len(source_ids), "budget_curve": curve, "all_budgets_vs_current_CACHED_K32": cross_budget,
        "stream_statuses": statuses, "excluded_budget_pair_instances": exclusions, "all_actual_arm_costs": actual,
        "all_actual_costs_by_budget": {str(budget): actual_costs([context for rep in by_budget[budget] for context in rep["contexts"]]) for budget in budgets},
        "original_source_accounting": payload["original_source_accounting"], "source_diagnostic_accounting": payload["source_diagnostic_accounting"],
        "accounting": payload["accounting"], "checks": result_checks,
        "all_analysis_checks_passed": all(row["passed"] for row in result_checks.values()), "analysis_seconds": perf_counter() - started,
        "scope": "All five budgets remain in the comparison. Quality uses one complete whole-stream mask across every context, method and budget; cost uses one source-valid whole-stream mask independently of policy availability. All physical runs and historical fees remain charged, including overlapping regenerated seeded draws. Quality reproduces retained V33 observations and adds no independent quality evidence. Pointwise paired suffix-stream intervals are conditional on the fixed boards/prefixes. All ten comparisons with contemporary CACHED K32 are auxiliary; no best or minimum budget is selected and no formal Gate is introduced."}


def physical_checks(payload, actual, rows, checks):
    plan, account = payload["plan"], payload["accounting"]
    old, diagnostic = payload["original_source_accounting"], payload["source_diagnostic_accounting"]
    checks["frozen_source_and_sampling_boundary"] = [payload["plan_binding_validation"]["passed"], payload["reference_binding_validation"]["passed"], payload["all_sampling_endpoints_closed_before_reference_values"],
        payload["all_prefix_snapshots_closed_before_local"], payload["all_sampling_endpoints_closed_before_oracle"], payload["endpoint_evaluation_replanning_calls"] == 0]
    prefixes = {row["board_index"]: row for row in payload["prefixes"]}
    preparations = {row["identity"]["context_index"]: row for row in payload["query_preparations"]}
    checks["fresh_prefix_and_preparation_once"] = [len(prefixes) == account["prefix_board_count"] == plan["board_count"],
        len(preparations) == account["prepared_query_count"] == plan["context_count"],
        account["prefix_physical_batches"] == plan["expected_prefix_batches"], account["prefix_physical_draws"] == plan["expected_prefix_draws"]]
    for context in rows:
        index, board = context["identity"]["context_index"], context["identity"]["board_index"]
        for row in context["arms"].values():
            checks["full_current_prefix_preparation_attribution"].append(row["costs"]["prefix_sampling_seconds"] == prefixes[board]["accounting"]["whole_seconds"]
                and row["costs"]["single_query_prepare_seconds"] == preparations[index]["accounting"]["whole_seconds"])
    checks["actual_prefix_and_preparation_time_totals"] = [abs(account["prefix_acquisition_seconds"] - math.fsum(row["accounting"]["whole_seconds"] for row in prefixes.values())) <= TOL,
        abs(account["single_query_preparation_seconds"] - math.fsum(row["accounting"]["whole_seconds"] for row in preparations.values())) <= TOL]
    checks["all_repeated_budget_runs_charged"] = [account["local_arm_run_count"] == sum(row["actual_arm_count"] for row in actual.values()) == plan["expected_arm_count"],
        account["local_physical_batches"] == sum(row["completed_batches"] for row in actual.values()) == plan["expected_local_batches"],
        account["local_physical_draws"] == sum(row["provider_counts"].get("physical_draws", 0) for row in actual.values()) == plan["expected_local_draws"],
        abs(account["local_allocation_wall_seconds"] - math.fsum(row["attributed_cost_totals"]["local_whole_run_seconds"] for row in actual.values())) <= TOL]
    checks["provider_counts_preserve_overlapping_draws"] = [row["provider_counts"] == account["provider_counts_by_arm"][arm] for arm, row in actual.items()]
    checks["all_fresh_physical_totals"] = [account["total_physical_batches"] == account["prefix_physical_batches"] + account["local_physical_batches"] == plan["expected_physical_batches"],
        account["total_physical_draws"] == account["prefix_physical_draws"] + account["local_physical_draws"] == plan["expected_physical_draws"]]
    checks["historical_chain_and_diagnostic_fees_retained"] = [old["historical_physical_batches"] + old["total_physical_batches"] == diagnostic["historical_physical_batches"] == account["historical_physical_batches"] == plan["source_historical_physical_batches"],
        old["historical_physical_draws"] + old["total_physical_draws"] == diagnostic["historical_physical_draws"] == account["historical_physical_draws"] == plan["source_historical_physical_draws"],
        diagnostic["new_physical_draws"] == 0]
    checks["cumulative_spending_and_reused_streams"] = [account["historical_plus_new_physical_batches"] == account["historical_physical_batches"] + account["total_physical_batches"] == plan["expected_cumulative_physical_batches"],
        account["historical_plus_new_physical_draws"] == account["historical_physical_draws"] + account["total_physical_draws"] == plan["expected_cumulative_physical_draws"],
        account["independent_new_samples"] == plan["expected_new_independent_draws"] == 0]
    checks["complete_endpoint_retention"] = [payload["source_and_new_endpoint_streams_complete"], account["endpoint_pair_records_written"] == account["endpoint_pair_records_reloaded"] == plan["expected_pair_count"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_budget_cost_v34.json.gz"))
    parser.add_argument("--reference", type=Path, default=Path("reports/controlled_predictive_budget_curve_analysis_v33.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_budget_cost_analysis_v34.json"))
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
    print(json.dumps({"output": str(args.output), "common_quality_complete_stream_count": result["common_quality_complete_stream_count"],
        "all_analysis_checks_passed": result["all_analysis_checks_passed"], "analysis_serialization_seconds": perf_counter() - started}))


if __name__ == "__main__":
    main()
