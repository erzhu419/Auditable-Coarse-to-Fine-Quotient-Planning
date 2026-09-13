#!/usr/bin/env python3
"""Compare fixed-budget CACHED and VARIANCE queries on frozen new H2 starts."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import TOL, differences, mean, monte_carlo_interval

ARMS = ("CACHED", "VARIANCE")
POLICY_METRICS = ("total_regret", "first_action_regret", "continuation_regret", "optimal_policy_rate")
DIAGNOSTIC_METRICS = ("first_action_wrong_rate", "first_action_regret", "defined_regret_lower_bound",
    "missing_probability", "weighted_unobserved_choices", "policy_unavailable_rate", "completed_batches", "completed_requested_budget_rate")
COST_METRICS = ("independent_query_seconds", "prefix_sampling_seconds", "single_query_prepare_seconds", "local_whole_run_seconds")
IDENTITY_FIELDS = ("context_index", "board_index", "case_name", "query_name")


def policy_metrics(row):
    value = row["evaluation"]
    return {**{key: value[key] for key in POLICY_METRICS[:-1]}, "optimal_policy_rate": float(value["total_regret"] <= TOL)}


def diagnostic_metrics(row):
    value = row["evaluation"]
    return {"first_action_wrong_rate": float(value["first_action_wrong"]),
        "first_action_regret": value["first_action_regret"],
        "defined_regret_lower_bound": value["first_action_regret"] + value["defined_continuation_regret"],
        "missing_probability": value["missing_probability"], "weighted_unobserved_choices": value["weighted_unobserved_choices"],
        "policy_unavailable_rate": float(not value["policy_evaluable"]),
        "completed_batches": row["local"]["completed_batches"], "completed_requested_budget_rate": float(row["local"]["completed_fixed_budget"])}


def cost_metrics(row):
    return row["costs"]


def paired(values, metric, *, interval):
    result = monte_carlo_interval(values) if interval else differences(values)
    if metric in (*POLICY_METRICS, "first_action_wrong_rate", *COST_METRICS):
        high = metric == "optimal_policy_rate"
        result.update(improved=result["positive" if high else "negative"], same=result["zero"],
            worse=result["negative" if high else "positive"])
    return result


def stream_statistics(repetitions, value_function, keys):
    streams = []
    for rep in repetitions:
        boards = defaultdict(list)
        for context in rep["contexts"]:
            boards[context["identity"]["board_index"]].append(context)
        values = {arm: {key: mean([mean([value_function(c["arms"][arm])[key] for c in contexts])
            for contexts in boards.values()]) for key in keys} for arm in ARMS}
        streams.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "arms": values,
            "VARIANCE_minus_CACHED": {key: values["VARIANCE"][key] - values["CACHED"][key] for key in keys}})
    return {"stream_count": len(streams), "unit": "one suffix stream, equal weights over fixed boards and their ten queries",
        "arms": {arm: {key: {k: v for k, v in monte_carlo_interval([s["arms"][arm][key] for s in streams]).items()
            if k not in ("negative", "zero", "positive")} for key in keys} for arm in ARMS},
        "VARIANCE_minus_CACHED": {key: paired([s["VARIANCE_minus_CACHED"][key] for s in streams], key, interval=True) for key in keys}}, streams


def points(contexts, value_function, keys):
    values = {arm: [value_function(c["arms"][arm]) for c in contexts] for arm in ARMS}
    return {"paired_context_instances": len(contexts),
        **{arm: {key: mean([row[key] for row in values[arm]]) for key in keys} for arm in ARMS},
        "VARIANCE_minus_CACHED": {key: paired([v[key] - c[key] for c, v in zip(values["CACHED"], values["VARIANCE"])], key, interval=False) for key in keys}}


def all_actual_costs(repetitions):
    result = {}
    for arm in ARMS:
        rows = [c["arms"][arm] for rep in repetitions for c in rep["contexts"] if "local" in c["arms"].get(arm, {})]
        providers, stages, work, stops, gaps = Counter(), Counter(), Counter(), Counter(), Counter()
        for row in rows:
            local = row["local"]
            providers.update(local["provider_counts"])
            stages.update(local["accounting"]["seconds_by_stage"])
            work.update(local["accounting"]["work_counts"])
            stops[local["stop_reason"]] += 1
            index = local["first_original_stop_index"]
            gaps["gap_separated"] += index is not None
            gaps["batches_after_first_gap_separation"] += local["completed_batches"] - index if index is not None else 0
        result[arm] = {"actual_arm_count": len(rows), "provider_counts": dict(providers),
            "seconds_by_stage": dict(stages), "work_counts": dict(work), "stop_reasons": dict(stops),
            "gap_diagnostics": dict(gaps), "first_observation_batches": providers.get("first_batch_requests", 0),
            "repeat_observation_batches": providers.get("repeat_batch_requests", 0),
            "repeat_batches_on_new_rows": sum(row["local"]["repeat_batches_on_rows_absent_from_common"] for row in rows),
            "completed_batches": sum(row["local"]["completed_batches"] for row in rows),
            "completed_requested_budget_arm_count": sum(row["local"]["completed_fixed_budget"] for row in rows),
            "attributed_cost_totals": {key: math.fsum(row["costs"][key] for row in rows) for key in COST_METRICS},
            "mean_costs": {key: mean([row["costs"][key] for row in rows]) for key in COST_METRICS}}
    return result


def matched_budget(context):
    rows = [context["arms"][arm]["local"] for arm in ARMS]
    n = [row["completed_batches"] for row in rows]
    K = context["requested_batch_count"]
    complete_K = all(row["completed_fixed_budget"] and row["completed_batches"] == K for row in rows)
    shared_stop = n[0] == n[1] and n[0] < K and all(row["stop_reason"] == "NO_ELIGIBLE_CANDIDATE" and not row["completed_fixed_budget"] for row in rows)
    label = "both_complete_K" if complete_K else "shared_normal_stop" if shared_stop else "unequal_actual_batches" if n[0] != n[1] else "equal_unmatched_stop"
    return complete_K or shared_stop, label


def physical_checks(payload, costs, checks):
    plan, account = payload["plan"], payload["accounting"]
    prefixes = {row["board_index"]: row for row in payload["prefixes"]}
    preparations = {row["identity"]["context_index"]: row for row in payload["query_preparations"]}
    checks["physical_prefix_and_query_preparation_counts"] = [len(prefixes) == account["prefix_board_count"] == 16,
        len(preparations) == account["prepared_query_count"] == 160,
        account["prefix_physical_batches"] == plan["expected_prefix_batches"] == 512,
        account["prefix_physical_draws"] == plan["expected_prefix_draws"] == 131072]
    for board in plan["boards"]:
        row = prefixes[board["board_index"]]
        a = row["accounting"]
        checks["prefix_identity_and_samples"].append(row["name"] == board["name"] and row["prefix_seed"] == board["prefix_seed"]
            and row["validation"]["passed"] and a["physical_batches"] == a["provider_counts"]["row_requests"] == 32
            and a["physical_draws"] == a["provider_counts"]["physical_draws"] == 8192)
    for fixed in plan["contexts"]:
        row = preparations[fixed["context_index"]]
        a = row["accounting"]
        checks["single_query_preparation_without_new_samples"].append(row["identity"] == {key: fixed[key] for key in IDENTITY_FIELDS}
            and row["validation"]["passed"] and a["current_query"] == fixed["query_name"]
            and a["prepared_query_count"] == 1 and a["replayed_batches"] == a["retained_model_batches"] == 32
            and a["new_provider_calls"] == a["new_physical_draws"] == 0)
    for rep in payload["repetitions"]:
        for context in rep["contexts"]:
            identity = context["identity"]
            for row in context["arms"].values():
                checks["full_prefix_and_query_cost_attribution"].append(
                    row["costs"]["prefix_sampling_seconds"] == prefixes[identity["board_index"]]["accounting"]["whole_seconds"]
                    and row["costs"]["single_query_prepare_seconds"] == preparations[identity["context_index"]]["accounting"]["whole_seconds"])
    checks["unique_preparation_time_totals"] = [
        abs(account["prefix_acquisition_seconds"] - math.fsum(row["accounting"]["whole_seconds"] for row in prefixes.values())) <= TOL,
        abs(account["single_query_preparation_seconds"] - math.fsum(row["accounting"]["whole_seconds"] for row in preparations.values())) <= TOL]
    checks["all_actual_local_work_retained"] = [
        account["local_arm_run_count"] == account["reset_from_prepared_query_count"] == sum(row["actual_arm_count"] for row in costs.values()) == plan["expected_arm_count"] == 5120,
        account["local_physical_batches"] == sum(row["completed_batches"] for row in costs.values()) <= plan["maximum_local_batches"],
        account["local_physical_draws"] == sum(row["provider_counts"].get("physical_draws", 0) for row in costs.values()) <= plan["maximum_local_draws"],
        abs(account["local_allocation_wall_seconds"] - math.fsum(row["attributed_cost_totals"]["local_whole_run_seconds"] for row in costs.values())) <= TOL]
    checks["per_arm_actual_provider_totals"] = [row["provider_counts"] == account["provider_counts_by_arm"][arm] for arm, row in costs.items()]
    checks["all_physical_totals"] = [account["total_physical_batches"] == account["prefix_physical_batches"] + account["local_physical_batches"] <= plan["maximum_physical_batches"] == 164352,
        account["total_physical_draws"] == account["prefix_physical_draws"] + account["local_physical_draws"] <= plan["maximum_physical_draws"] == 42074112]
    checks["retention_and_evaluator_boundary"] = [payload["all_prefix_snapshots_closed_before_local"], payload["endpoint_evaluation_replanning_calls"] == 0,
        account["endpoint_pair_records_written"] == account["endpoint_pair_records_reloaded"] == plan["expected_pair_count"] == 2560]


def summarize(payload):
    started = perf_counter()
    plan, repetitions = payload["plan"], payload["repetitions"]
    planned = {row["context_index"]: row for row in plan["contexts"]}
    identities = [{key: row[key] for key in IDENTITY_FIELDS} for row in plan["contexts"]]
    checks = defaultdict(list)
    checks["frozen_roster_and_queries"] = [len(plan["boards"]) == plan["board_count"] == 16,
        len(planned) == plan["context_count"] == 160, plan["query_count"] == 10,
        all([c["query_name"] for c in plan["contexts"] if c["board_index"] == b["board_index"]] == plan["source_query_order"] for b in plan["boards"]),
        [board["prefix_seed"] for board in plan["boards"]] == list(range(941001, 941017)),
        [board["generation_seed"] for board in plan["boards"]] == list(range(940001, 940017))]
    checks["frozen_streams_methods_and_budget"] = [len(repetitions) == plan["replicate_count"] == 16,
        [{"replicate_index": r["replicate_index"], "base_seed": r["base_seed"]} for r in repetitions] == plan["replicates"],
        [r["base_seed"] for r in repetitions] == list(range(942001, 942017)), plan["arms"] == list(ARMS),
        plan["primary_comparison"] == ["VARIANCE", "CACHED"], plan["primary_metrics"] == ["total_regret", "independent_query_seconds"],
        plan["prefix_batches_per_board"] == plan["requested_batches_per_arm"] == 32, plan["samples_per_batch"] == 256]
    checks["all_sampling_closed_before_truth"] = [payload["all_sampling_endpoints_closed_before_oracle"]]
    checked, incomplete, budget_types = [], [], Counter()
    for rep in repetitions:
        same_ids = [c["identity"] for c in rep["contexts"]] == identities
        checks["retained_context_order"].append(same_ids)
        sources, budgets, diagnostics, policies = [], [], [], []
        for context in rep["contexts"]:
            fixed = planned[context["identity"]["context_index"]]
            fixed_equal = all(context[key] == fixed[key] for key in ("target_key", "requested_batch_count", "initial_batches"))
            checks["fixed_initial_and_requested_batches"].append(fixed_equal and context["initial_batches"] == context["requested_batch_count"] == 32)
            offset = (rep["replicate_index"] + fixed["context_index"]) % 2
            checks["arm_rotation"].append(context["run_order"] == list(ARMS[offset:] + ARMS[:offset]))
            source = fixed_equal and set(context["arms"]) == set(ARMS)
            diagnostic, policy = True, True
            for arm in ARMS:
                row = context["arms"][arm]
                local, costs = row["local"], row["costs"]
                n, K = local["completed_batches"], fixed["requested_batch_count"]
                actual_source = row["source_validation"]["passed"]
                checks["source_validity_labels"].append(row["source_valid"] == actual_source)
                checks["local_actual_batch_accounting"].append(0 <= n <= K and local["initial_batches"] == 32
                    and local["final_batches"] == 32 + n and local["actual_draws"] == 256*n
                    and local["provider_counts"].get("row_requests", 0) == n
                    and local["provider_counts"].get("physical_draws", 0) == 256*n)
                matched = n == K and local["completed_fixed_budget"]
                checks["completed_requested_budget_labels"].append(row["completed_requested_budget"] == matched)
                checks["independent_query_cost_components"].append(
                    costs["local_whole_run_seconds"] == local["accounting"]["whole_run_seconds"]
                    and abs(costs["independent_query_seconds"] - math.fsum(costs[key] for key in COST_METRICS[1:])) <= TOL)
                value = row.get("evaluation")
                eval_valid = bool(value and row["evaluation_validation"]["passed"] and row["first_action_validation"]["passed"])
                evaluable = bool(value and value["policy_evaluable"])
                if value:
                    reach = value["reach_probability_pass"] and abs(value["terminal_probability"] + value["missing_probability"] - 1.) <= TOL
                    checks["true_reach_probability_conservation"].append(reach)
                    checks["missing_policy_availability"].append(evaluable == (value["missing_probability"] == 0))
                    if evaluable:
                        decomposition = value["identities_pass"] and abs(value["total_regret"] - value["first_action_regret"] - value["continuation_regret"]) <= TOL
                        checks["frozen_policy_regret_decomposition"].append(decomposition)
                    else:
                        decomposition = True
                        checks["undefined_policy_not_imputed"].append(all(value[key] is None for key in ("v_pi", "total_regret", "continuation_regret")))
                    eval_valid &= reach and decomposition
                source &= actual_source
                diagnostic &= eval_valid
                policy &= evaluable and eval_valid
            source = bool(source)
            budget, budget_type = matched_budget(context)
            budget_types[budget_type] += 1
            complete = source and budget and policy
            checks["context_completion_labels"].append(context["source_valid"] == source and context["budget_matched"] == budget and context["paired_complete"] == complete)
            sources.append(source); budgets.append(budget); diagnostics.append(diagnostic); policies.append(policy)
            if not complete:
                incomplete.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
                    "identity": context["identity"], "source_valid": source, "budget_matched": budget,
                    "evaluation_valid": diagnostic, "policy_evaluable": policy, "status": context["status"],
                    "arms": {arm: {"completed_batches": row["local"]["completed_batches"], "stop_reason": row["local"]["stop_reason"],
                        "source_validation": row["source_validation"], "evaluation_validation": row["evaluation_validation"],
                        "first_action_validation": row["first_action_validation"],
                        "missing_probability": row.get("evaluation", {}).get("missing_probability"),
                        "missing_policy_frontier": row.get("evaluation", {}).get("missing_policy_frontier", [])}
                        for arm, row in context["arms"].items()}})
        source = same_ids and all(sources)
        budget = all(budgets)
        diagnostic = source and all(diagnostics)
        complete = source and budget and all(policies)
        checks["whole_stream_masks"].append(rep["source_valid"] == source and rep["budget_matched"] == budget and rep["complete"] == complete)
        checked.append({**rep, "source_valid": source, "budget_matched": budget, "diagnostics_valid": diagnostic, "complete": complete})
    source_reps = [r for r in checked if r["source_valid"]]
    matched_reps = [r for r in source_reps if r["budget_matched"]]
    policy_reps = [r for r in checked if r["complete"]]
    diagnostic_reps = [r for r in checked if r["diagnostics_valid"]]
    quality, quality_streams = stream_statistics(policy_reps, policy_metrics, ("total_regret",))
    cost_summary, cost_streams = stream_statistics(source_reps, cost_metrics, COST_METRICS)
    matched_cost, _ = stream_statistics(matched_reps, cost_metrics, COST_METRICS)
    quality_diagnostics, _ = stream_statistics(policy_reps, policy_metrics, POLICY_METRICS[1:])
    continuous, diagnostic_streams = stream_statistics(diagnostic_reps, diagnostic_metrics, DIAGNOSTIC_METRICS)
    all_costs = all_actual_costs(repetitions)
    physical_checks(payload, all_costs, checks)
    checks["reported_stream_and_budget_counts"] = [len(source_reps) == payload["source_valid_repetition_count"],
        len(policy_reps) == payload["complete_repetition_count"],
        payload["budget_counts"] == {"completed_K_pair": budget_types["both_complete_K"],
            "shared_normal_stop_pair": budget_types["shared_normal_stop"], "unequal_budget_pair": budget_types["unequal_actual_batches"]}]
    source_contexts = [c for r in source_reps for c in r["contexts"]]
    quality_contexts = [c for r in policy_reps for c in r["contexts"]]
    diagnostic_contexts = [c for r in diagnostic_reps for c in r["contexts"]]
    def selection(predicate):
        return {"quality_complete_stream_mask": points([c for c in quality_contexts if predicate(c["identity"])], policy_metrics, POLICY_METRICS),
            "cost_source_valid_mask": points([c for c in source_contexts if predicate(c["identity"])], cost_metrics, COST_METRICS),
            "continuous_diagnostics": points([c for c in diagnostic_contexts if predicate(c["identity"])], diagnostic_metrics, DIAGNOSTIC_METRICS)}
    result_checks = {name: {"passed": all(values), "checked": len(values), "failed": sum(not value for value in values)} for name, values in checks.items()}
    return {"schema": "acfqp.controlled_predictive_new_starts_analysis.v28", "status": payload["status"],
        "source_valid_stream_count": len(source_reps), "matched_budget_stream_count": len(matched_reps),
        "quality_complete_stream_count": len(policy_reps), "diagnostic_valid_stream_count": len(diagnostic_reps),
        "primary_quality": quality, "primary_independent_query_cost": cost_summary,
        "matched_budget_independent_query_cost": matched_cost, "same_quality_mask_diagnostics": quality_diagnostics,
        "continuous_diagnostics": continuous, "whole_cohort_points": selection(lambda identity: True),
        "boards": [{"board_index": b["board_index"], "case_name": b["name"], **selection(lambda identity: identity["board_index"] == b["board_index"])} for b in plan["boards"]],
        "contexts": [{"identity": identity, **selection(lambda row: row["context_index"] == identity["context_index"])} for identity in identities],
        "quality_streams": quality_streams, "cost_streams": cost_streams, "diagnostic_streams": diagnostic_streams,
        "stream_statuses": [{key: r[key] for key in ("replicate_index", "base_seed", "source_valid", "budget_matched", "diagnostics_valid", "complete", "status")} for r in checked],
        "incomplete_context_instances": incomplete, "all_actual_arm_costs": all_costs,
        "actual_budget_pair_counts": dict(budget_types),
        "accounting": payload["accounting"], "checks": result_checks,
        "all_analysis_checks_passed": all(row["passed"] for row in result_checks.values()),
        "elapsed_seconds_before_report_serialization": payload["elapsed_seconds_before_report_serialization"],
        "analysis_seconds": perf_counter() - started, "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Constructed new H2 development starts, conditional on the sixteen fixed boards and their shared prefixes. Each suffix stream is the Monte Carlo unit; board/query summaries are descriptive. Cost uses all source-valid streams even with valid early stops or undefined policies; actual physical and attributed costs retain every arm. Quality requires all160 matched, evaluable pairs. Defined-regret lower bounds are continuous coverage diagnostics, not complete policy values. Unobserved choices are true-reach expected counts. Independent query costs fully attribute prefix and single-query preparation, while physical preparation runs are counted once. Exact evaluation, retention and statistics are separate experimental overhead. No natural-play, unseen-descendant, full online algorithm or independent Gate claim."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/controlled_predictive_new_starts_v28.json.gz"))
    parser.add_argument("--output", type=Path, default=Path("reports/controlled_predictive_new_starts_analysis_v28.json"))
    args = parser.parse_args()
    started = perf_counter()
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    read_seconds = perf_counter() - started
    result = summarize(payload)
    result["analysis_result_read_seconds"] = read_seconds
    started = perf_counter()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "source_valid_stream_count": result["source_valid_stream_count"],
        "quality_complete_stream_count": result["quality_complete_stream_count"],
        "all_analysis_checks_passed": result["all_analysis_checks_passed"], "analysis_serialization_seconds": perf_counter() - started}))


if __name__ == "__main__":
    main()
