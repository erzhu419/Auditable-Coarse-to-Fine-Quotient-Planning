#!/usr/bin/env python3
"""Evaluate the three frozen budget configurations on the new V35 cohort."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
from itertools import permutations
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import TOL, mean, differences, monte_carlo_interval
from analyze_controlled_predictive_transfer_v32 import COST_METRICS, POLICY_METRICS, IDENTITY_FIELDS, policy_metrics, cost_metrics

CONFIGURATIONS = ("GAP24", "CACHED24", "CACHED32")
COMPARISONS = (("GAP24", "CACHED32"), ("GAP24", "CACHED24"), ("CACHED24", "CACHED32"))
DIAGNOSTICS = ("policy_unavailable_rate", "missing_probability", "weighted_unobserved_choices", "defined_regret_lower_bound")


def paired(values, metric, interval):
    result = monte_carlo_interval(values) if interval else differences(values)
    if metric in (*POLICY_METRICS, *COST_METRICS):
        high = metric == "optimal_policy_rate"
        result.update(improved=result["positive" if high else "negative"], same=result["zero"], worse=result["negative" if high else "positive"])
    return result


def cohort_means(contexts, function, keys):
    boards = defaultdict(list)
    for context in contexts: boards[context["identity"]["board_index"]].append(context)
    return {name: {key: mean([mean([function(context["configurations"][name])[key] for context in rows]) for rows in boards.values()])
        for key in keys} for name in CONFIGURATIONS}


def stream_statistics(repetitions, function, keys):
    streams = []
    for rep in repetitions:
        values = cohort_means(rep["contexts"], function, keys)
        streams.append({"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"], "configurations": values,
            "comparisons": {left+"_minus_"+right: {key: values[left][key]-values[right][key] for key in keys} for left,right in COMPARISONS}})
    return {"stream_count": len(streams), "unit": "one V35 suffix stream, averaging ten queries within each board then sixteen boards; conditional on fixed new boards and prefixes",
        "configurations": {name: {key: {k:v for k,v in monte_carlo_interval([row["configurations"][name][key] for row in streams]).items()
            if k not in ("negative", "zero", "positive")} for key in keys} for name in CONFIGURATIONS},
        "comparisons": {left+"_minus_"+right: {key: paired([row["comparisons"][left+"_minus_"+right][key] for row in streams],key,True)
            for key in keys} for left,right in COMPARISONS}}, streams


def points(contexts, function, keys):
    return {"paired_context_instances": len(contexts), "unique_context_count": len({row["identity"]["context_index"] for row in contexts}),
        "configuration_means": cohort_means(contexts,function,keys), "comparisons": {left+"_minus_"+right: {
            key: paired([function(row["configurations"][left])[key]-function(row["configurations"][right])[key] for row in contexts],key,False)
            for key in keys} for left,right in COMPARISONS}}


def policy_changes(contexts):
    result = {}
    for left,right in COMPARISONS:
        repaired,new,changed = [],[],[]
        for context in contexts:
            before,after = (context["configurations"][name]["evaluation"] for name in (right,left))
            old_optimal,new_optimal = before["total_regret"] <= TOL,after["total_regret"] <= TOL
            if not old_optimal and new_optimal: repaired.append(context["identity"]["context_index"])
            if old_optimal and not new_optimal: new.append(context["identity"]["context_index"])
            if before["initial_action"] != after["initial_action"]: changed.append(context["identity"]["context_index"])
        result[left+"_minus_"+right] = {"paired_context_instances": len(contexts), **{key: {"context_instance_count": len(values),
            "unique_context_count": len(set(values)), "context_indices": sorted(set(values))} for key,values in (
                ("policy_repaired",repaired),("policy_new_error",new),("initial_action_changed",changed))}}
    return result


def diagnostic_metrics(row):
    value = row["evaluation"]
    return {"policy_unavailable_rate": float(not value["policy_evaluable"]), "missing_probability": value["missing_probability"],
        "weighted_unobserved_choices": value["weighted_unobserved_choices"], "defined_regret_lower_bound": value["first_action_regret"]+value["defined_continuation_regret"]}


def valid_configuration(row, fixed, checks):
    local,cost = row["local"],row["costs"]
    source = row["source_validation"]["passed"] and row["configuration"] == fixed
    checks["configuration_binding_and_source_labels"].append(row["configuration"] == fixed and row["source_valid"] == source)
    n,K = local["completed_batches"],fixed["budget"]
    complete = local["completed_fixed_budget"] and n == K
    checks["actual_requested_and_completed_budgets"].append(local["arm"] == fixed["arm"] and local["requested_batch_count"] == K
        and local["initial_batches"] == 32 and 0 <= n <= K and local["final_batches"] == 32+n
        and row["completed_requested_budget"] == complete and local["actual_draws"] == 256*n
        and local["provider_counts"].get("physical_draws",0) == 256*n and local["provider_counts"].get("row_requests",0) == n
        and local["provider_counts"].get("first_batch_requests",0)+local["provider_counts"].get("repeat_batch_requests",0) == n
        and (complete or local["stop_reason"] == "NO_ELIGIBLE_CANDIDATE"))
    checks["full_current_query_cost_components"].append(cost["local_whole_run_seconds"] == local["accounting"]["whole_run_seconds"]
        and abs(cost["independent_query_seconds"]-math.fsum(cost[key] for key in COST_METRICS[1:])) <= TOL)
    value = row.get("evaluation")
    diagnostic = bool(value and row["evaluation_validation"]["passed"] and row["first_action_validation"]["passed"])
    if value:
        reach = value["reach_probability_pass"] and abs(value["terminal_probability"]+value["missing_probability"]-1.) <= TOL
        checks["policy_reach_and_missing_value_labels"].append(reach and value["policy_evaluable"] == (value["missing_probability"] == 0.)
            and (value["policy_evaluable"] or all(value[key] is None for key in ("v_pi","total_regret","continuation_regret"))))
        decomposition = not value["policy_evaluable"] or (value["identities_pass"] and abs(value["total_regret"]-value["first_action_regret"]-value["continuation_regret"]) <= TOL)
        checks["policy_regret_decomposition"].append(decomposition)
        diagnostic &= reach and decomposition
    return bool(source),bool(complete),bool(diagnostic),bool(diagnostic and value["policy_evaluable"])


def all_actual_costs(repetitions):
    result = {}
    for name in CONFIGURATIONS:
        rows = [context["configurations"][name] for rep in repetitions for context in rep["contexts"]]
        providers,stages,work,stops = Counter(),Counter(),Counter(),Counter()
        for row in rows:
            local = row["local"]
            providers.update(local["provider_counts"])
            stages.update(local["accounting"]["seconds_by_stage"])
            work.update(local["accounting"]["work_counts"])
            stops[local["stop_reason"]] += 1
        result[name] = {"actual_run_count": len(rows), "provider_counts": dict(providers), "seconds_by_stage": dict(stages), "work_counts": dict(work),
            "stop_reasons": dict(stops), "completed_batches": sum(row["local"]["completed_batches"] for row in rows),
            "completed_requested_budget_count": sum(row["completed_requested_budget"] for row in rows),
            "first_observation_batches": providers.get("first_batch_requests",0), "repeat_observation_batches": providers.get("repeat_batch_requests",0),
            "attributed_cost_totals": {key: math.fsum(row["costs"][key] for row in rows) for key in COST_METRICS}}
    return result


def summarize(payload):
    started = perf_counter()
    plan,repetitions = payload["plan"],payload["repetitions"]
    fixed = {row["name"]:row for row in plan["configurations"]}
    identities = [{key:row[key] for key in IDENTITY_FIELDS} for row in plan["contexts"]]
    checks = defaultdict(list)
    orders = list(permutations(CONFIGURATIONS))
    checks["frozen_new_cohort_and_three_configurations"] = [list(fixed) == list(CONFIGURATIONS), plan["comparisons"] == [list(pair) for pair in COMPARISONS],
        [(fixed[name]["arm"],fixed[name]["budget"]) for name in CONFIGURATIONS] == [("GAP_FRONTIER",24),("CACHED",24),("CACHED",32)],
        len(plan["boards"]) == plan["board_count"] == 16,len(identities) == plan["context_count"] == 160,plan["query_count"] == 10,
        len(repetitions) == plan["replicate_count"] == 16,
        [{key:rep[key] for key in ("replicate_index","base_seed")} for rep in repetitions] == plan["replicates"]]
    source_reps,quality_reps,diagnostic_reps,statuses,exclusions = [],[],[],[],[]
    for rep in repetitions:
        source = [context["identity"] for context in rep["contexts"]] == identities
        checks["retained_context_roster"].append(source)
        quality,diagnostic,fixed_budget = source,source,True
        for context in rep["contexts"]:
            checks["configuration_execution_rotation"].append(context["run_order"] == list(orders[(rep["replicate_index"]*plan["context_count"]+context["identity"]["context_index"])%6]))
            flags = [valid_configuration(context["configurations"][name],fixed[name],checks) for name in CONFIGURATIONS]
            context_source = all(row[0] for row in flags)
            context_budget = all(row[1] for row in flags)
            context_diagnostic = all(row[2] for row in flags)
            context_quality = context_source and context_budget and all(row[3] for row in flags)
            checks["three_configuration_context_masks"].append(context["source_valid"] == context_source and context["fixed_budget_complete"] == context_budget and context["complete"] == context_quality)
            source &= context_source; quality &= context_quality; diagnostic &= context_diagnostic; fixed_budget &= context_budget
            if not context_quality:
                exclusions.append({"replicate_index":rep["replicate_index"],"identity":context["identity"],"source_valid":context_source,
                    "fixed_budget_complete":context_budget,"diagnostics_valid":context_diagnostic,"configurations": {
                        name:{"source_valid":row[0],"own_requested_budget_complete":row[1],"evaluation_valid":row[2],"policy_evaluable":row[3],
                            "actual_batches":context["configurations"][name]["local"]["completed_batches"]} for name,row in zip(CONFIGURATIONS,flags)}})
        diagnostic &= source
        checks["whole_stream_masks"].append(rep["source_valid"] == source and rep["complete"] == quality)
        if source: source_reps.append(rep)
        if quality: quality_reps.append(rep)
        if diagnostic: diagnostic_reps.append(rep)
        statuses.append({"replicate_index":rep["replicate_index"],"base_seed":rep["base_seed"],"source_valid":source,
            "quality_complete":quality,"diagnostics_valid":diagnostic,"all_requested_budgets_complete":fixed_budget})
    quality,quality_streams = stream_statistics(quality_reps,policy_metrics,("total_regret",))
    components,_ = stream_statistics(quality_reps,policy_metrics,POLICY_METRICS[1:])
    cost,cost_streams = stream_statistics(source_reps,cost_metrics,COST_METRICS)
    quality_cost,_ = stream_statistics(quality_reps,cost_metrics,COST_METRICS)
    diagnostics,_ = stream_statistics(diagnostic_reps,diagnostic_metrics,DIAGNOSTICS)
    quality_rows = [row for rep in quality_reps for row in rep["contexts"]]
    source_rows = [row for rep in source_reps for row in rep["contexts"]]
    def selection(predicate):
        qrows = [row for row in quality_rows if predicate(row["identity"])]
        return {"quality_complete_mask":points(qrows,policy_metrics,POLICY_METRICS),
            "source_cost_mask":points([row for row in source_rows if predicate(row["identity"])],cost_metrics,COST_METRICS),
            "policy_changes":policy_changes(qrows)}
    actual = all_actual_costs(repetitions)
    physical_checks(payload,actual,checks)
    result_checks = {key:{"passed":all(values),"checked":len(values),"failed":sum(not value for value in values)} for key,values in checks.items()}
    return {"schema":"acfqp.controlled_predictive_budget_transfer_analysis.v35","configurations":list(fixed.values()),
        "source_valid_stream_count":len(source_reps),"quality_complete_stream_count":len(quality_reps),"diagnostic_valid_stream_count":len(diagnostic_reps),
        "primary_quality":quality,"same_quality_mask_components":components,"primary_independent_query_cost":cost,
        "same_quality_mask_cost":quality_cost,"continuous_diagnostics":diagnostics,"whole_cohort_points":selection(lambda identity:True),
        "boards":[{"board_index":board["board_index"],"case_name":board["name"],**selection(lambda identity:identity["board_index"]==board["board_index"])} for board in plan["boards"]],
        "queries":[{"query_name":name,**selection(lambda identity:identity["query_name"]==name)} for name in plan["source_query_order"]],
        "quality_streams":quality_streams,"cost_streams":cost_streams,"stream_statuses":statuses,"incomplete_context_instances":exclusions,
        "all_actual_configuration_costs":actual,"original_source_accounting":payload["original_source_accounting"],"accounting":payload["accounting"],
        "checks":result_checks,"all_analysis_checks_passed":all(row["passed"] for row in result_checks.values()),"analysis_seconds":perf_counter()-started,
        "scope":"Three frozen configurations on prospectively fixed new constructed boards and independently selected prefix/suffix streams. The quality mask requires every context and configuration to complete its own budget and have an evaluable policy. Source-valid cost is independent of evaluation; all actual fees also remain unconditional. Same-quality cost comparisons use the common quality cohort. Queries/configurations share paired randomness; physical draws are charged even when overlapping. Suffix-stream intervals condition on the fixed boards and prefixes, not a population or formal Gate claim."}


def physical_checks(payload,actual,checks):
    plan,account,old = payload["plan"],payload["accounting"],payload["original_source_accounting"]
    checks["frozen_method_new_cohort_and_evaluation_boundary"] = [payload["plan_binding_validation"]["passed"],payload["cohort_binding_validation"]["passed"],
        payload["all_prefix_snapshots_closed_before_local"],payload["all_sampling_endpoints_closed_before_oracle"],payload["endpoint_evaluation_replanning_calls"]==0]
    prefixes = {row["board_index"]:row for row in payload["prefixes"]}
    preparations = {row["identity"]["context_index"]:row for row in payload["query_preparations"]}
    checks["prefix_and_query_preparation_once"] = [len(prefixes)==account["prefix_board_count"]==plan["board_count"],
        len(preparations)==account["prepared_query_count"]==plan["context_count"],account["prefix_physical_batches"]==plan["expected_prefix_batches"],
        account["prefix_physical_draws"]==plan["expected_prefix_draws"]]
    for board in plan["boards"]:
        row=prefixes[board["board_index"]]; a=row["accounting"]
        checks["new_prefix_identity_and_samples"].append(row["name"]==board["name"] and row["prefix_seed"]==board["prefix_seed"] and row["validation"]["passed"]
            and a["physical_batches"]==a["provider_counts"]["row_requests"]==32 and a["physical_draws"]==a["provider_counts"]["physical_draws"]==8192)
    for context in plan["contexts"]:
        row=preparations[context["context_index"]]; a=row["accounting"]
        checks["single_query_preparation_without_extra_samples"].append(row["identity"]=={key:context[key] for key in IDENTITY_FIELDS} and row["validation"]["passed"]
            and a["prepared_query_count"]==1 and a["current_query"]==context["query_name"] and a["replayed_batches"]==a["retained_model_batches"]==32
            and a["new_provider_calls"]==a["new_physical_draws"]==0)
    for rep in payload["repetitions"]:
        for context in rep["contexts"]:
            index,board=context["identity"]["context_index"],context["identity"]["board_index"]
            for row in context["configurations"].values():
                checks["full_current_prefix_preparation_attribution"].append(row["costs"]["prefix_sampling_seconds"]==prefixes[board]["accounting"]["whole_seconds"]
                    and row["costs"]["single_query_prepare_seconds"]==preparations[index]["accounting"]["whole_seconds"])
    checks["actual_acquisition_preparation_time"] = [abs(account["prefix_acquisition_seconds"]-math.fsum(row["accounting"]["whole_seconds"] for row in prefixes.values()))<=TOL,
        abs(account["single_query_preparation_seconds"]-math.fsum(row["accounting"]["whole_seconds"] for row in preparations.values()))<=TOL]
    checks["all_actual_configuration_runs_charged"] = [account["local_configuration_run_count"]==sum(row["actual_run_count"] for row in actual.values())==plan["expected_run_count"],
        account["local_physical_batches"]==sum(row["completed_batches"] for row in actual.values())<=plan["expected_local_batches"],
        account["local_physical_draws"]==sum(row["provider_counts"].get("physical_draws",0) for row in actual.values())<=plan["expected_local_draws"],
        abs(account["local_allocation_wall_seconds"]-math.fsum(row["attributed_cost_totals"]["local_whole_run_seconds"] for row in actual.values()))<=TOL]
    checks["configuration_provider_totals"] = [row["provider_counts"]==account["provider_counts_by_configuration"][name] for name,row in actual.items()]
    checks["new_physical_totals"] = [account["total_physical_batches"]==account["prefix_physical_batches"]+account["local_physical_batches"]<=plan["expected_physical_batches"],
        account["total_physical_draws"]==account["prefix_physical_draws"]+account["local_physical_draws"]<=plan["expected_physical_draws"]]
    checks["historical_and_cumulative_costs_retained"] = [old["historical_physical_batches"]+old["total_physical_batches"]==account["historical_physical_batches"]==plan["source_historical_physical_batches"],
        old["historical_physical_draws"]+old["total_physical_draws"]==account["historical_physical_draws"]==plan["source_historical_physical_draws"],
        account["historical_plus_new_physical_batches"]==account["historical_physical_batches"]+account["total_physical_batches"]<=plan["expected_cumulative_physical_batches"],
        account["historical_plus_new_physical_draws"]==account["historical_physical_draws"]+account["total_physical_draws"]<=plan["expected_cumulative_physical_draws"]]
    checks["endpoint_retention_before_evaluation"] = [account["endpoint_triple_records_written"]==account["endpoint_triple_records_reloaded"]==plan["expected_triple_count"]]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=Path("reports/controlled_predictive_budget_transfer_v35.json.gz"))
    parser.add_argument("--output",type=Path,default=Path("reports/controlled_predictive_budget_transfer_analysis_v35.json"))
    args=parser.parse_args(); started=perf_counter()
    with gzip.open(args.input,"rt",encoding="utf-8") as reader: payload=json.load(reader)
    read_seconds=perf_counter()-started; result=summarize(payload); result["analysis_result_read_seconds"]=read_seconds; started=perf_counter()
    with args.output.open("x",encoding="utf-8") as writer:
        json.dump(result,writer,indent=2,allow_nan=False); writer.write("\n")
    print(json.dumps({"output":str(args.output),"quality_complete_stream_count":result["quality_complete_stream_count"],
        "all_analysis_checks_passed":result["all_analysis_checks_passed"],"analysis_serialization_seconds":perf_counter()-started}))


if __name__=="__main__": main()
