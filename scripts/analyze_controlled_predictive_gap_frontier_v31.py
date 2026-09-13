#!/usr/bin/env python3
"""Compare contemporary fixed-budget gap-frontier and CACHED allocations."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import TOL, mean, differences, monte_carlo_interval
from analyze_controlled_predictive_new_starts_v28 import IDENTITY_FIELDS, POLICY_METRICS, DIAGNOSTIC_METRICS, policy_metrics, diagnostic_metrics, cost_metrics

ARMS = ("CACHED", "GAP_FRONTIER")
COMPARISON = "GAP_FRONTIER_minus_CACHED"
COST_METRICS = ("independent_query_seconds", "prefix_sampling_seconds", "single_query_prepare_seconds", "prefix_restore_seconds", "local_whole_run_seconds")


def paired(values, metric, *, interval):
    result = monte_carlo_interval(values) if interval else differences(values)
    if metric in (*POLICY_METRICS, *COST_METRICS, "first_action_wrong_rate"):
        high = metric == "optimal_policy_rate"
        result.update(improved=result["positive" if high else "negative"], same=result["zero"], worse=result["negative" if high else "positive"])
    return result


def cohort_means(contexts, value_function, keys):
    boards = defaultdict(list)
    for context in contexts:
        boards[context["identity"]["board_index"]].append(context)
    return {arm: {key: mean([mean([value_function(c["arms"][arm])[key] for c in board]) for board in boards.values()]) for key in keys} for arm in ARMS}


def stream_statistics(repetitions, value_function, keys):
    streams = []
    for rep in repetitions:
        arms = cohort_means(rep["contexts"], value_function, keys)
        streams.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "arms": arms,
            COMPARISON: {key: arms["GAP_FRONTIER"][key] - arms["CACHED"][key] for key in keys}})
    return {"stream_count": len(streams), "unit": "one suffix stream conditional on fixed V28 boards and prefixes; equal query weights within each board and equal board weights",
        "arms": {arm: {key: {name: value for name, value in monte_carlo_interval([row["arms"][arm][key] for row in streams]).items()
            if name not in ("negative", "zero", "positive")} for key in keys} for arm in ARMS},
        COMPARISON: {key: paired([row[COMPARISON][key] for row in streams], key, interval=True) for key in keys}}, streams


def points(contexts, value_function, keys):
    return {"paired_context_instances": len(contexts), "unique_context_count": len({c["identity"]["context_index"] for c in contexts}),
        "arm_means": cohort_means(contexts, value_function, keys),
        COMPARISON: {key: paired([value_function(c["arms"]["GAP_FRONTIER"])[key] - value_function(c["arms"]["CACHED"])[key] for c in contexts], key, interval=False) for key in keys}}


def matched_budget(context):
    rows = [context["arms"][arm]["local"] for arm in ARMS]
    n, K = [row["completed_batches"] for row in rows], context["requested_batch_count"]
    full = all(row["completed_fixed_budget"] and row["completed_batches"] == K for row in rows)
    shared = n[0] == n[1] < K and all(row["stop_reason"] == "NO_ELIGIBLE_CANDIDATE" and not row["completed_fixed_budget"] for row in rows)
    return full or shared, "both_complete_K" if full else "shared_normal_stop" if shared else "unequal_actual_batches" if n[0] != n[1] else "equal_unmatched_stop"


def all_actual_costs(repetitions):
    result = {}
    for arm in ARMS:
        rows = [context["arms"][arm] for rep in repetitions for context in rep["contexts"] if "local" in context["arms"].get(arm, {})]
        providers, stages, work, stops = Counter(), Counter(), Counter(), Counter()
        for row in rows:
            local = row["local"]
            providers.update(local["provider_counts"])
            stages.update(local["accounting"]["seconds_by_stage"])
            work.update(local["accounting"]["work_counts"])
            stops[local["stop_reason"]] += 1
        result[arm] = {"actual_arm_count": len(rows), "provider_counts": dict(providers), "seconds_by_stage": dict(stages),
            "work_counts": dict(work), "stop_reasons": dict(stops),
            "completed_batches": sum(row["local"]["completed_batches"] for row in rows),
            "first_observation_batches": providers.get("first_batch_requests", 0), "repeat_observation_batches": providers.get("repeat_batch_requests", 0),
            "repeat_batches_on_new_rows": sum(row["local"]["repeat_batches_on_rows_absent_from_common"] for row in rows),
            "completed_requested_budget_arm_count": sum(row["local"]["completed_fixed_budget"] for row in rows),
            "attributed_cost_totals": {key: math.fsum(row["costs"][key] for row in rows) for key in COST_METRICS}}
    return result


def policy_changes(contexts):
    """Compare endpoint policies on the same complete stream mask."""
    repaired, new, first_repaired, first_new, changed = [], [], [], [], []
    for context in contexts:
        identity = context["identity"]
        before, after = (context["arms"][arm]["evaluation"] for arm in ARMS)
        original, current = before["total_regret"] <= TOL, after["total_regret"] <= TOL
        if not original and current: repaired.append(identity["context_index"])
        if original and not current: new.append(identity["context_index"])
        if before["first_action_wrong"] and not after["first_action_wrong"]: first_repaired.append(identity["context_index"])
        if not before["first_action_wrong"] and after["first_action_wrong"]: first_new.append(identity["context_index"])
        if before["initial_action"] != after["initial_action"]: changed.append(identity["context_index"])
    return {"paired_context_instances": len(contexts), "unique_context_count": len({c["identity"]["context_index"] for c in contexts}),
        **{key: {"context_instance_count": len(values), "unique_context_count": len(set(values)), "context_indices": sorted(set(values))}
           for key, values in (("policy_repaired", repaired), ("policy_new_error", new), ("first_action_repaired", first_repaired), ("first_action_new_error", first_new), ("initial_action_changed", changed))}}


def summarize(payload):
    started = perf_counter()
    plan, repetitions = payload["plan"], payload["repetitions"]
    planned = {row["context_index"]: row for row in plan["contexts"]}
    identities = [{key: row[key] for key in IDENTITY_FIELDS} for row in plan["contexts"]]
    checks = defaultdict(list)
    checks["frozen_roster_streams_and_comparison"] = [len(plan["boards"]) == plan["board_count"] == 16,
        len(planned) == plan["context_count"] == 160, plan["query_count"] == 10,
        len(repetitions) == plan["replicate_count"] == 16,
        [{key: rep[key] for key in ("replicate_index", "base_seed")} for rep in repetitions] == plan["replicates"],
        plan["arms"] == list(ARMS), plan["primary_comparison"] == ["GAP_FRONTIER", "CACHED"],
        plan["primary_metrics"] == ["total_regret", "independent_query_seconds"], plan["requested_batches_per_arm"] == 32, plan["samples_per_batch"] == 256,
        all([c["query_name"] for c in plan["contexts"] if c["board_index"] == board["board_index"]] == plan["source_query_order"] for board in plan["boards"])]
    checks["all_sampling_closed_before_truth"] = [payload["all_sampling_endpoints_closed_before_oracle"], payload["endpoint_evaluation_replanning_calls"] == 0]
    checked, incomplete, budget_types = [], [], Counter()
    for rep in repetitions:
        same_ids = [context["identity"] for context in rep["contexts"]] == identities
        checks["retained_context_order"].append(same_ids)
        sources, budgets, diagnostics, policies = [], [], [], []
        for context in rep["contexts"]:
            fixed = planned[context["identity"]["context_index"]]
            source = all(context[key] == fixed[key] for key in ("target_key", "requested_batch_count", "initial_batches")) and set(context["arms"]) == set(ARMS)
            offset = (rep["replicate_index"] + fixed["context_index"]) % 2
            checks["arm_execution_rotation"].append(context["run_order"] == list(ARMS[offset:] + ARMS[:offset]))
            diagnostic, policy = True, True
            for arm in ARMS:
                row = context["arms"][arm]
                local, costs = row["local"], row["costs"]
                n, K = local["completed_batches"], fixed["requested_batch_count"]
                actual_source = row["source_validation"]["passed"]
                value_reference_valid = True
                if arm == "CACHED":
                    for key in ("reference_validation", "reference_value_validation"):
                        checks["CACHED_" + key].append(row[key]["passed"])
                    actual_source &= row["reference_validation"]["passed"]
                    value_reference_valid = row["reference_value_validation"]["passed"]
                checks["source_validity_labels"].append(row["source_valid"] == actual_source)
                source &= actual_source
                checks["local_actual_batch_accounting"].append(0 <= n <= K and local["initial_batches"] == 32 and local["final_batches"] == 32+n
                    and local["actual_draws"] == 256*n and local["provider_counts"].get("row_requests", 0) == n
                    and local["provider_counts"].get("physical_draws", 0) == 256*n
                    and local["provider_counts"].get("first_batch_requests", 0) + local["provider_counts"].get("repeat_batch_requests", 0) == n)
                checks["completed_requested_budget_labels"].append(row["completed_requested_budget"] == (n == K and local["completed_fixed_budget"]))
                checks["independent_query_cost_components"].append(costs["local_whole_run_seconds"] == local["accounting"]["whole_run_seconds"]
                    and abs(costs["independent_query_seconds"] - math.fsum(costs[key] for key in COST_METRICS[1:])) <= TOL)
                value = row.get("evaluation")
                eval_valid = bool(value and row["evaluation_validation"]["passed"] and row["first_action_validation"]["passed"] and value_reference_valid)
                evaluable = bool(value and value["policy_evaluable"])
                if value:
                    reach = value["reach_probability_pass"] and abs(value["terminal_probability"] + value["missing_probability"] - 1.) <= TOL
                    checks["true_reach_probability_conservation"].append(reach)
                    checks["missing_policy_availability"].append(evaluable == (value["missing_probability"] == 0))
                    decomposition = True
                    if evaluable:
                        decomposition = value["identities_pass"] and abs(value["total_regret"] - value["first_action_regret"] - value["continuation_regret"]) <= TOL
                        checks["policy_regret_decomposition"].append(decomposition)
                    else:
                        checks["undefined_policy_not_imputed"].append(all(value[key] is None for key in ("v_pi", "total_regret", "continuation_regret")))
                    eval_valid &= reach and decomposition
                diagnostic &= eval_valid
                policy &= eval_valid and evaluable
            budget, budget_type = matched_budget(context)
            budget_types[budget_type] += 1
            complete = bool(source and budget and policy)
            checks["context_completion_labels"].append(context["source_valid"] == bool(source) and context["budget_matched"] == budget and context["paired_complete"] == complete)
            sources.append(bool(source)); budgets.append(budget); diagnostics.append(diagnostic); policies.append(policy)
            if not complete:
                incomplete.append({"replicate_index": rep["replicate_index"], "identity": context["identity"], "status": context["status"],
                    "source_valid": bool(source), "budget_matched": budget, "evaluation_valid": diagnostic, "policy_evaluable": policy,
                    "arms": {arm: {"source_validation": row["source_validation"], "completed_batches": row["local"]["completed_batches"],
                        "stop_reason": row["local"]["stop_reason"], "missing_probability": row.get("evaluation", {}).get("missing_probability")}
                        for arm, row in context["arms"].items()}})
        source, budget = same_ids and all(sources), all(budgets)
        diagnostic, complete = source and all(diagnostics), source and budget and all(policies)
        checks["whole_stream_masks"].append(rep["source_valid"] == source and rep["budget_matched"] == budget and rep["complete"] == complete)
        checked.append({**rep, "source_valid": source, "budget_matched": budget, "diagnostics_valid": diagnostic, "complete": complete})
    source_reps = [rep for rep in checked if rep["source_valid"]]
    matched_reps = [rep for rep in source_reps if rep["budget_matched"]]
    quality_reps = [rep for rep in checked if rep["complete"]]
    diagnostic_reps = [rep for rep in checked if rep["diagnostics_valid"]]
    quality, quality_streams = stream_statistics(quality_reps, policy_metrics, ("total_regret",))
    costs, cost_streams = stream_statistics(source_reps, cost_metrics, COST_METRICS)
    matched_costs, _ = stream_statistics(matched_reps, cost_metrics, COST_METRICS)
    components, _ = stream_statistics(quality_reps, policy_metrics, POLICY_METRICS[1:])
    continuous, _ = stream_statistics(diagnostic_reps, diagnostic_metrics, DIAGNOSTIC_METRICS)
    actual = all_actual_costs(repetitions)
    physical_checks(payload, actual, checks)
    source_contexts = [context for rep in source_reps for context in rep["contexts"]]
    quality_contexts = [context for rep in quality_reps for context in rep["contexts"]]
    def selection(predicate):
        qrows = [row for row in quality_contexts if predicate(row["identity"])]
        return {"quality_complete_stream_mask": points(qrows, policy_metrics, POLICY_METRICS),
            "cost_source_valid_mask": points([row for row in source_contexts if predicate(row["identity"])], cost_metrics, COST_METRICS),
            "policy_changes": policy_changes(qrows)}
    result_checks = {key: {"passed": all(values), "checked": len(values), "failed": sum(not value for value in values)} for key, values in checks.items()}
    return {"schema": "acfqp.controlled_predictive_gap_frontier_analysis.v31", "status": payload["status"],
        "source_valid_stream_count": len(source_reps), "matched_budget_stream_count": len(matched_reps), "quality_complete_stream_count": len(quality_reps),
        "diagnostic_valid_stream_count": len(diagnostic_reps), "primary_quality": quality, "primary_independent_query_cost": costs,
        "matched_budget_independent_query_cost": matched_costs, "same_quality_mask_components": components, "continuous_diagnostics": continuous,
        "whole_cohort_points": selection(lambda identity: True), "selected_context_69": selection(lambda identity: identity["context_index"] == 69),
        "quality_streams": quality_streams, "cost_streams": cost_streams,
        "stream_statuses": [{key: row[key] for key in ("replicate_index", "base_seed", "source_valid", "budget_matched", "diagnostics_valid", "complete", "status")} for row in checked],
        "incomplete_context_instances": incomplete, "actual_budget_pair_counts": dict(budget_types), "all_actual_arm_costs": actual,
        "original_source_accounting": payload["original_source_accounting"], "accounting": payload["accounting"], "checks": result_checks,
        "all_analysis_checks_passed": all(row["passed"] for row in result_checks.values()), "analysis_seconds": perf_counter() - started,
        "scope": "Fixed V28 development boards and shared prefixes; one complete suffix stream is the Monte Carlo unit. Endpoint costs include original prefix/preparation and newly measured restore/allocation. Every fresh sample, including contemporary CACHED reruns, is charged; all historical costs remain. Context69 is a secondary descriptive diagnostic. No independent cohort or formal Gate claim."}


def physical_checks(payload, actual, checks):
    plan, account, old = payload["plan"], payload["accounting"], payload["original_source_accounting"]
    checks["bound_source_plan_and_restorations"] = [payload["plan_binding_validation"]["passed"], payload["all_restorations_passed"], payload["all_prefix_restorations_before_sampling"]]
    restorations = {row["identity"]["context_index"]: row for row in payload["restoration_records"]}
    preparations = {row["identity"]["context_index"]: row for row in payload["query_preparations"]}
    prefixes = {row["board_index"]: row for row in payload["prefixes"]}
    identities = [{key: row[key] for key in IDENTITY_FIELDS} for row in plan["contexts"]]
    checks["restore_each_prefix_once"] = [len(restorations) == account["prefix_restores"] == plan["expected_prefix_restores"] == 160,
        [row["identity"] for row in payload["restoration_records"]] == identities,
        all(row["validation"]["passed"] for row in restorations.values()),
        abs(account["prefix_restore_seconds"] - math.fsum(row["accounting"]["whole_seconds"] for row in restorations.values())) <= TOL]
    for rep in payload["repetitions"]:
        for context in rep["contexts"]:
            index, board = context["identity"]["context_index"], context["identity"]["board_index"]
            for row in context["arms"].values():
                costs = row["costs"]
                checks["full_prefix_preparation_restore_attribution"].append(costs["prefix_sampling_seconds"] == prefixes[board]["accounting"]["whole_seconds"]
                    and costs["single_query_prepare_seconds"] == preparations[index]["accounting"]["whole_seconds"]
                    and costs["prefix_restore_seconds"] == restorations[index]["accounting"]["whole_seconds"])
    checks["historical_physical_costs_retained"] = [old["total_physical_batches"] == account["historical_physical_batches"] == plan["source_historical_physical_batches"],
        old["total_physical_draws"] == account["historical_physical_draws"] == plan["source_historical_physical_draws"]]
    checks["fresh_local_work_all_charged"] = [account["local_arm_run_count"] == sum(row["actual_arm_count"] for row in actual.values()) == plan["expected_arm_count"],
        account["local_physical_batches"] == sum(row["completed_batches"] for row in actual.values()) <= plan["maximum_new_physical_batches"],
        account["local_physical_draws"] == sum(row["provider_counts"].get("physical_draws", 0) for row in actual.values()) <= plan["maximum_new_physical_draws"],
        abs(account["local_allocation_wall_seconds"] - math.fsum(row["attributed_cost_totals"]["local_whole_run_seconds"] for row in actual.values())) <= TOL]
    checks["fresh_provider_counts_include_CACHED_reruns"] = [row["provider_counts"] == account["provider_counts_by_arm"][arm] for arm, row in actual.items()]
    checks["no_new_prefix_samples"] = [account["prefix_physical_batches"] == account["prefix_physical_draws"] == 0,
        account["total_physical_batches"] == account["local_physical_batches"], account["total_physical_draws"] == account["local_physical_draws"]]
    checks["retention_before_evaluation"] = [payload["source_and_new_endpoint_lengths_valid"], account["endpoint_pair_records_written"] == account["endpoint_pair_records_reloaded"] == plan["expected_pair_count"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_gap_frontier_v31.json.gz"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_gap_frontier_analysis_v31.json"))
    args = parser.parse_args()
    started = perf_counter()
    with gzip.open(args.input, "rt", encoding="utf-8") as reader:
        payload = json.load(reader)
    read_seconds = perf_counter() - started
    result = summarize(payload)
    result["analysis_result_read_seconds"] = read_seconds
    started = perf_counter()
    with args.output.open("x", encoding="utf-8") as writer:
        json.dump(result, writer, indent=2, allow_nan=False)
        writer.write("\n")
    print(json.dumps({"output": str(args.output), "quality_complete_stream_count": result["quality_complete_stream_count"],
        "all_analysis_checks_passed": result["all_analysis_checks_passed"], "analysis_serialization_seconds": perf_counter() - started}))


if __name__ == "__main__":
    main()
