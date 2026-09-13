#!/usr/bin/env python3
"""Evaluate transfer of the fixed gap-frontier rule to frozen new boards."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import TOL
from analyze_controlled_predictive_new_starts_v28 import (
    IDENTITY_FIELDS, POLICY_METRICS, DIAGNOSTIC_METRICS, policy_metrics, diagnostic_metrics, cost_metrics)
from analyze_controlled_predictive_gap_frontier_v31 import (
    ARMS, COMPARISON, stream_statistics as paired_stream_statistics, points, matched_budget, policy_changes)

COST_METRICS = ("independent_query_seconds", "prefix_sampling_seconds", "single_query_prepare_seconds", "local_whole_run_seconds")


def stream_statistics(repetitions, value_function, keys):
    result, streams = paired_stream_statistics(repetitions, value_function, keys)
    result["unit"] = "one suffix stream conditional on the fixed new V32 boards and prefixes; equal query weights within board and equal board weights"
    return result, streams


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
            "work_counts": dict(work), "stop_reasons": dict(stops), "completed_batches": sum(row["local"]["completed_batches"] for row in rows),
            "first_observation_batches": providers.get("first_batch_requests", 0), "repeat_observation_batches": providers.get("repeat_batch_requests", 0),
            "repeat_batches_on_new_rows": sum(row["local"]["repeat_batches_on_rows_absent_from_common"] for row in rows),
            "completed_requested_budget_arm_count": sum(row["local"]["completed_fixed_budget"] for row in rows),
            "attributed_cost_totals": {key: math.fsum(row["costs"][key] for row in rows) for key in COST_METRICS}}
    return result


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
                eval_valid = bool(value and row["evaluation_validation"]["passed"] and row["first_action_validation"]["passed"])
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
    return {"schema": "acfqp.controlled_predictive_transfer_analysis.v32", "status": payload["status"],
        "source_valid_stream_count": len(source_reps), "matched_budget_stream_count": len(matched_reps), "quality_complete_stream_count": len(quality_reps),
        "diagnostic_valid_stream_count": len(diagnostic_reps), "primary_quality": quality, "primary_independent_query_cost": costs,
        "matched_budget_independent_query_cost": matched_costs, "same_quality_mask_components": components, "continuous_diagnostics": continuous,
        "whole_cohort_points": selection(lambda identity: True),
        "boards": [{"board_index": board["board_index"], "case_name": board["name"], **selection(lambda identity: identity["board_index"] == board["board_index"])} for board in plan["boards"]],
        "queries": [{"query_name": name, **selection(lambda identity: identity["query_name"] == name)} for name in plan["source_query_order"]],
        "quality_streams": quality_streams, "cost_streams": cost_streams,
        "stream_statuses": [{key: row[key] for key in ("replicate_index", "base_seed", "source_valid", "budget_matched", "diagnostics_valid", "complete", "status")} for row in checked],
        "incomplete_context_instances": incomplete, "actual_budget_pair_counts": dict(budget_types), "all_actual_arm_costs": actual,
        "original_source_accounting": payload["original_source_accounting"], "accounting": payload["accounting"], "checks": result_checks,
        "all_analysis_checks_passed": all(row["passed"] for row in result_checks.values()), "analysis_seconds": perf_counter() - started,
        "scope": "Frozen new constructed boards and common prefixes; one complete suffix stream is the Monte Carlo unit. Intervals are conditional on these boards and prefixes, not population intervals. Costs fully attribute current prefix acquisition, current single-query preparation and current local allocation. All new physical samples and prior V28/V31 costs remain charged. Board/query summaries are descriptive; no natural-play or formal Gate claim."}


def physical_checks(payload, actual, checks):
    plan, account, old = payload["plan"], payload["accounting"], payload["original_source_accounting"]
    checks["frozen_method_and_new_cohort_binding"] = [payload["plan_binding_validation"]["passed"], payload["cohort_binding_validation"]["passed"]]
    prefixes = {row["board_index"]: row for row in payload["prefixes"]}
    preparations = {row["identity"]["context_index"]: row for row in payload["query_preparations"]}
    checks["prefix_acquisition_and_preparation_once"] = [len(prefixes) == account["prefix_board_count"] == plan["board_count"],
        len(preparations) == account["prepared_query_count"] == plan["context_count"],
        account["prefix_physical_batches"] == plan["expected_prefix_batches"], account["prefix_physical_draws"] == plan["expected_prefix_draws"]]
    for board in plan["boards"]:
        row = prefixes[board["board_index"]]
        a = row["accounting"]
        checks["prefix_identity_and_actual_samples"].append(row["name"] == board["name"] and row["prefix_seed"] == board["prefix_seed"]
            and row["validation"]["passed"] and a["physical_batches"] == a["provider_counts"]["row_requests"] == plan["prefix_batches_per_board"]
            and a["physical_draws"] == a["provider_counts"]["physical_draws"] == plan["samples_per_batch"] * a["physical_batches"])
    for fixed in plan["contexts"]:
        row, index = preparations[fixed["context_index"]], fixed["context_index"]
        a = row["accounting"]
        checks["one_query_preparation_without_new_samples"].append(row["identity"] == {key: fixed[key] for key in IDENTITY_FIELDS}
            and row["validation"]["passed"] and a["current_query"] == fixed["query_name"] and a["prepared_query_count"] == 1
            and a["replayed_batches"] == a["retained_model_batches"] == fixed["initial_batches"]
            and a["new_provider_calls"] == a["new_physical_draws"] == 0)
    for rep in payload["repetitions"]:
        for context in rep["contexts"]:
            index, board = context["identity"]["context_index"], context["identity"]["board_index"]
            for row in context["arms"].values():
                costs = row["costs"]
                checks["full_current_prefix_and_preparation_attribution"].append(costs["prefix_sampling_seconds"] == prefixes[board]["accounting"]["whole_seconds"]
                    and costs["single_query_prepare_seconds"] == preparations[index]["accounting"]["whole_seconds"])
    checks["actual_preparation_time_totals"] = [abs(account["prefix_acquisition_seconds"] - math.fsum(row["accounting"]["whole_seconds"] for row in prefixes.values())) <= TOL,
        abs(account["single_query_preparation_seconds"] - math.fsum(row["accounting"]["whole_seconds"] for row in preparations.values())) <= TOL]
    checks["all_prior_physical_costs_retained"] = [old["historical_physical_batches"] + old["total_physical_batches"] == account["historical_physical_batches"] == plan["source_historical_physical_batches"],
        old["historical_physical_draws"] + old["total_physical_draws"] == account["historical_physical_draws"] == plan["source_historical_physical_draws"]]
    checks["all_new_local_work_charged"] = [account["local_arm_run_count"] == sum(row["actual_arm_count"] for row in actual.values()) == plan["expected_arm_count"],
        account["local_physical_batches"] == sum(row["completed_batches"] for row in actual.values()) <= plan["maximum_local_batches"],
        account["local_physical_draws"] == sum(row["provider_counts"].get("physical_draws", 0) for row in actual.values()) <= plan["maximum_local_draws"],
        abs(account["local_allocation_wall_seconds"] - math.fsum(row["attributed_cost_totals"]["local_whole_run_seconds"] for row in actual.values())) <= TOL]
    checks["all_new_provider_counts"] = [row["provider_counts"] == account["provider_counts_by_arm"][arm] for arm, row in actual.items()]
    checks["new_prefix_and_local_physical_totals"] = [account["total_physical_batches"] == account["prefix_physical_batches"] + account["local_physical_batches"] <= plan["maximum_physical_batches"],
        account["total_physical_draws"] == account["prefix_physical_draws"] + account["local_physical_draws"] <= plan["maximum_physical_draws"]]
    checks["retention_and_evaluator_boundary"] = [payload["all_prefix_snapshots_closed_before_local"],
        account["endpoint_pair_records_written"] == account["endpoint_pair_records_reloaded"] == plan["expected_pair_count"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_transfer_v32.json.gz"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_transfer_analysis_v32.json"))
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
