#!/usr/bin/env python3
"""Compare paired retained-data root readouts with the deployed pooled continuation."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import TOL, mean, differences, monte_carlo_interval
from analyze_controlled_predictive_endpoint_errors_v36 import identity_counts
from analyze_controlled_predictive_budget_transfer_v35 import (
    stream_statistics as original_statistics, all_actual_costs, policy_metrics, cost_metrics, COST_METRICS, IDENTITY_FIELDS)

ARMS=("POOLED","CROSSFIT")
QUALITY=("total_regret","first_action_regret","continuation_regret","optimal_policy_rate")
DIAGNOSTICS=("policy_unavailable_rate","missing_probability","first_action_regret","defined_continuation_regret")


def policy_values(row):
    value=row["policy_evaluation"]
    return {**{key:value[key] for key in QUALITY[:3]},"optimal_policy_rate":float(value["total_regret"]<=TOL)}


def diagnostic_values(row):
    value=row["policy_evaluation"]
    return {"policy_unavailable_rate":float(not value["policy_evaluable"]),"missing_probability":value["missing_probability"],
        "first_action_regret":value["first_action_regret"],"defined_continuation_regret":value["defined_continuation_regret"]}


def cohort_means(contexts,function,keys):
    boards=defaultdict(list)
    for context in contexts: boards[context["identity"]["board_index"]].append(context)
    return {arm:{key:mean([mean([function(context,arm)[key] for context in rows]) for rows in boards.values()]) for key in keys} for arm in ARMS}


def stream_statistics(repetitions,function,keys):
    streams=[]
    for rep in repetitions:
        values=cohort_means(rep["contexts"],function,keys)
        streams.append({"replicate_index":rep["replicate_index"],"base_seed":rep["base_seed"],"arms":values,
            "CROSSFIT_minus_POOLED":{key:values["CROSSFIT"][key]-values["POOLED"][key] for key in keys}})
    return {"stream_count":len(streams),"unit":"one original adaptive V35 suffix history; average ten queries per board then sixteen fixed boards",
        "arms":{arm:{key:monte_carlo_interval([row["arms"][arm][key] for row in streams]) for key in keys} for arm in ARMS},
        "CROSSFIT_minus_POOLED":{key:monte_carlo_interval([row["CROSSFIT_minus_POOLED"][key] for row in streams]) for key in keys}},streams


def points(contexts,function,keys):
    return {**identity_counts(contexts),"arm_means":cohort_means(contexts,function,keys),
        "CROSSFIT_minus_POOLED":{key:differences([function(context,"CROSSFIT")[key]-function(context,"POOLED")[key] for context in contexts]) for key in keys}}


def quality(context,arm): return policy_values(context["arms"][arm])
def postprocess(context,arm): return context["arms"][arm]["costs"]
def diagnostics(context,arm): return diagnostic_values(context["arms"][arm])
def bookkeeping(context,arm):
    return {"historical_query_plus_postprocess_seconds":context["original_CACHED32_costs"]["independent_query_seconds"]+context["arms"][arm]["costs"]["postprocess_seconds"]}


def policy_changes(contexts):
    groups={key:[] for key in ("full_policy_repaired","full_policy_new_error","root_action_repaired","root_action_new_error","root_action_changed")}
    for context in contexts:
        before,after=(context["arms"][arm]["policy_evaluation"] for arm in ARMS)
        for prefix,field in (("full_policy","total_regret"),("root_action","first_action_regret")):
            old,new=before[field]>TOL,after[field]>TOL
            if old and not new: groups[prefix+"_repaired"].append(context)
            if not old and new: groups[prefix+"_new_error"].append(context)
        if before["initial_action"]!=after["initial_action"]: groups["root_action_changed"].append(context)
    return {key:identity_counts(rows) for key,rows in groups.items()}


def valid_policy(row,checks):
    value=row.get("policy_evaluation")
    diagnostic=bool(value and row.get("evaluation_validation",{}).get("passed"))
    if not value: return False,False
    reach=value["reach_probability_pass"] and abs(value["terminal_probability"]+value["missing_probability"]-1.)<=TOL
    missing=value["policy_evaluable"]==(value["missing_probability"]==0.) and (value["policy_evaluable"] or all(value[key] is None for key in ("v_pi","total_regret","continuation_regret")))
    decomposition=not value["policy_evaluable"] or (value["identities_pass"] and abs(value["total_regret"]-value["first_action_regret"]-value["continuation_regret"])<=TOL)
    action=row.get("readout") is not None and value["initial_action"]==row["readout"]["root_action"]
    checks["policy_reach_missingness_and_action"].extend((reach,missing,action))
    checks["full_policy_regret_decomposition"].append(decomposition)
    diagnostic &= reach and missing and decomposition and action
    return bool(diagnostic),bool(diagnostic and value["policy_evaluable"])


def all_postprocess_costs(repetitions):
    result={}
    for arm in ARMS:
        rows=[context["arms"][arm] for rep in repetitions for context in rep["contexts"]]
        timing,work=Counter(),Counter()
        for row in rows:
            account=(row.get("readout") or {}).get("accounting",{})
            timing.update(account.get("seconds_by_stage",{}))
            timing.update({key:value for key,value in account.items() if key.endswith("seconds") and isinstance(value,(int,float))})
            work.update({key:value for key,value in account.items() if not key.endswith("seconds") and isinstance(value,(int,float))})
        result[arm]={"record_count":len(rows),"attempt_count":sum(context.get("accounting",{}).get("readout_calls_"+arm,0) for rep in repetitions for context in rep["contexts"]),"postprocess_seconds":math.fsum(row["costs"]["postprocess_seconds"] for row in rows),
            "readout_seconds_by_field":dict(timing),"readout_work_counts":dict(work)}
    return result


def summarize(payload,reference):
    started=perf_counter(); plan=payload["plan"]; checks=defaultdict(list)
    identities=[{key:row[key] for key in IDENTITY_FIELDS} for row in plan["contexts"]]
    checks["frozen_full_cohort_and_readout_arms"]=[plan["arms"]==list(ARMS),plan["source_configuration"]=={"name":"CACHED32","arm":"CACHED","budget":32},
        plan["partition_seed"]==38,len(identities)==plan["context_count"]==160,plan["board_count"]==16,plan["query_count"]==10,
        len(payload["repetitions"])==plan["replicate_count"]==16,
        [{key:rep[key] for key in ("replicate_index","base_seed")} for rep in payload["repetitions"]]==plan["replicates"]]
    source_reps,quality_reps,diagnostic_reps,statuses,exclusions=[],[],[],[],[]
    original_lookup={(rep["replicate_index"],row["identity"]["context_index"]):row["configurations"]["CACHED32"]
        for rep in payload["original_repetitions"] for row in rep["contexts"]}
    for rep in payload["repetitions"]:
        source=[context["identity"] for context in rep["contexts"]]==identities and payload["plan_binding_validation"]["passed"]
        checks["retained_context_roster"].append([context["identity"] for context in rep["contexts"]]==identities)
        complete,diagnostic=source,source
        for context in rep["contexts"]:
            index=context["identity"]["context_index"]
            old=original_lookup[rep["replicate_index"],index]
            context_source=all(context.get(key,{}).get("passed") is True for key in ("source_validation","restoration_validation","proposal_validation","retained_result_validation")) and all(row["source_valid"] and row.get("readout_validation",{}).get("passed") is True for row in context["arms"].values())
            checks["source_valid_labels"].append(context["source_valid"]==context_source)
            checks["readout_execution_rotation"].append(context["run_order"]==list(ARMS if (rep["replicate_index"]+index)%2==0 else reversed(ARMS)))
            checks["original_CACHED32_query_cost_retained"].append(context["original_CACHED32_costs"]==old["costs"])
            flags={arm:valid_policy(context["arms"][arm],checks) for arm in ARMS}
            baseline=context["arms"]["POOLED"].get("value_reproduction_validation",{}).get("passed") is True
            checks["inherited_POOLED_policy_reproduction"].append(baseline)
            for arm,row in context["arms"].items():
                readout=row.get("readout")
                if readout:
                    checks["exact_score_argmax_and_readout_cost"].append(readout["root_action"]==min(readout["root_values"],key=lambda action:(-readout["root_values"][action],action))
                        and row["costs"]["postprocess_seconds"]==readout["accounting"]["whole_readout_seconds"])
            context_complete=context_source and baseline and all(flag[1] for flag in flags.values())
            context_diagnostic=context_source and baseline and all(flag[0] for flag in flags.values())
            checks["context_quality_labels"].append(context["complete"]==context_complete)
            source &= context_source; complete &= context_complete; diagnostic &= context_diagnostic
            if not context_complete: exclusions.append({"replicate_index":rep["replicate_index"],"identity":context["identity"],"source_valid":context_source,
                "POOLED_reproduced":baseline,"arms":{arm:{"evaluation_valid":flag[0],"policy_evaluable":flag[1],
                    "missing_probability":context["arms"][arm].get("policy_evaluation",{}).get("missing_probability")} for arm,flag in flags.items()}})
        checks["whole_stream_quality_source_labels"].append(rep["source_valid"]==source and rep["complete"]==complete)
        statuses.append({"replicate_index":rep["replicate_index"],"base_seed":rep["base_seed"],"source_valid":source,"quality_complete":complete,"diagnostics_valid":diagnostic})
        if source: source_reps.append(rep)
        if complete: quality_reps.append(rep)
        if diagnostic: diagnostic_reps.append(rep)
    quality_stats,quality_streams=stream_statistics(quality_reps,quality,QUALITY)
    cost_stats,cost_streams=stream_statistics(source_reps,postprocess,("postprocess_seconds",))
    quality_cost,_=stream_statistics(quality_reps,postprocess,("postprocess_seconds",))
    diagnostic_stats,_=stream_statistics(diagnostic_reps,diagnostics,DIAGNOSTICS)
    booked,_=stream_statistics(source_reps,bookkeeping,("historical_query_plus_postprocess_seconds",))
    quality_booked,_=stream_statistics(quality_reps,bookkeeping,("historical_query_plus_postprocess_seconds",))
    quality_rows=[row for rep in quality_reps for row in rep["contexts"]]
    diagnostic_rows=[row for rep in diagnostic_reps for row in rep["contexts"]]
    source_rows=[row for rep in source_reps for row in rep["contexts"]]
    def selection(predicate):
        selected=[row for row in quality_rows if predicate(row["identity"])]
        return {"quality":points(selected,quality,QUALITY),"policy_changes":policy_changes(selected),
            "postprocess_cost":points([row for row in source_rows if predicate(row["identity"])],postprocess,("postprocess_seconds",))}
    original=payload["original_repetitions"]
    old_quality=[rep for rep in original if rep["complete"]]; old_source=[rep for rep in original if rep["source_valid"]]
    original_quality,old_quality_streams=original_statistics(old_quality,policy_metrics,("total_regret",))
    original_cost,old_cost_streams=original_statistics(old_source,cost_metrics,COST_METRICS)
    actual=all_actual_costs(original); postprocess_actual=all_postprocess_costs(payload["repetitions"])
    checks["original_three_configuration_quality_and_cost_exact"]=[old_quality_streams==reference["original_quality_streams"],old_cost_streams==reference["original_cost_streams"],
        actual==payload["original_all_actual_configuration_costs"]==reference["all_original_actual_configuration_costs"]]
    checks["original_acquisition_and_V36_V37_diagnostic_costs_exact"]=[payload["original_source_accounting"]==reference["original_source_accounting"],
        payload["source_diagnostic_accounting"]==reference["accounting"],payload["prior_diagnostic_accounting"]==reference["source_diagnostic_accounting"]]
    check_accounting(payload,postprocess_actual,checks)
    checked={key:{"passed":all(values),"checked":len(values),"failed":sum(not value for value in values)} for key,values in checks.items()}
    return {"schema":"acfqp.controlled_predictive_crossfit_analysis.v38","arms":list(ARMS),
        "source_valid_stream_count":len(source_reps),"quality_complete_stream_count":len(quality_reps),"diagnostic_valid_stream_count":len(diagnostic_reps),
        "primary_full_policy_quality":quality_stats,"primary_postprocess_cost":cost_stats,"same_quality_mask_postprocess_cost":quality_cost,
        "continuous_diagnostics":diagnostic_stats,"coverage":{arm:{"diagnostic_context_instances":len(diagnostic_rows),
            "policy_evaluable_count":sum(row["arms"][arm]["policy_evaluation"]["policy_evaluable"] for row in diagnostic_rows),
            "policy_unavailable_count":sum(not row["arms"][arm]["policy_evaluation"]["policy_evaluable"] for row in diagnostic_rows)} for arm in ARMS},
        "booked_original_query_plus_postprocess":booked,"same_quality_mask_booked_total":quality_booked,
        "whole_cohort":selection(lambda identity:True),
        "boards":[{"board_index":board["board_index"],"case_name":board["name"],**selection(lambda identity:identity["board_index"]==board["board_index"])} for board in plan["boards"]],
        "queries":[{"query_name":name,**selection(lambda identity:identity["query_name"]==name)} for name in plan["source_query_order"]],
        "quality_streams":quality_streams,"postprocess_cost_streams":cost_streams,
        "original_quality_complete_stream_count":len(old_quality),"original_source_cost_stream_count":len(old_source),
        "original_three_configuration_quality":original_quality,"original_three_configuration_cost":original_cost,
        "original_quality_streams":old_quality_streams,"original_cost_streams":old_cost_streams,
        "all_original_actual_configuration_costs":actual,"all_actual_postprocess_costs":postprocess_actual,
        "original_source_accounting":payload["original_source_accounting"],"source_diagnostic_accounting":payload["source_diagnostic_accounting"],
        "prior_diagnostic_accounting":payload["prior_diagnostic_accounting"],"accounting":payload["accounting"],
        "stream_statuses":statuses,"incomplete_context_instances":exclusions,"checks":checked,"all_analysis_checks_passed":all(row["passed"] for row in checked.values()),
        "analysis_seconds":perf_counter()-started,
        "scope":"Paired root-only policy postprocessing of all retained CACHED32 adaptive histories. Deployed H1 actions remain pooled; full Vpi is evaluated only for candidates and POOLED values are inherited. Missing policies are not imputed. Quality uses one complete whole-stream mask; costs preserve their source-valid mask plus unconditional charges. Postprocess includes partition and readout, while restoration, validation, retention and oracle work are separate. Original query cost plus current postprocess is bookkeeping, not contemporaneous online end-to-end runtime. Non-overlapping folds conditional on adaptive acquisition are not independent unbiased data; suffix intervals condition on the fixed cohort and partition rule. All old configuration and diagnostic fees remain. Not a formal Gate."}


def check_accounting(payload,actual,checks):
    plan,account,old=payload["plan"],payload["accounting"],payload["original_source_accounting"]
    contexts=[row for rep in payload["repetitions"] for row in rep["contexts"]]
    checks["retained_endpoint_stream_and_proposal_closure"]=[payload["plan_binding_validation"]["passed"],payload["source_endpoint_stream_complete"],
        payload["all_proposals_closed_before_oracle"],payload["proposal_stream_complete"],account.get("source_endpoint_stream_reads",0)==1,
        account.get("source_endpoint_triple_records_read",0)==plan["expected_source_triples_read"],len(contexts)==plan["expected_pair_count"],
        account.get("proposal_records_written",0)==account.get("proposal_records_read",0)==plan["expected_proposals"]]
    checks["one_restore_and_candidate_evaluation_per_endpoint"]=[account.get("model_restore_calls",0)==plan["expected_model_restores"],
        account.get("candidate_policy_evaluation_calls",0)==plan["expected_candidate_policy_evaluations"],
        account.get("baseline_policy_evaluation_calls",0)==plan["expected_baseline_policy_evaluations"]==0]
    checks["all_actual_readout_costs_retained"]=[sum(row["attempt_count"] for row in actual.values())==plan["expected_readout_calls"]]
    for arm,row in actual.items():
        checks["all_actual_readout_costs_retained"].extend((row["attempt_count"]==account["readout_calls_by_arm"][arm],
            abs(row["postprocess_seconds"]-account["postprocess_seconds_by_arm"][arm])<=TOL))
    checks["no_new_environment_samples_or_evaluation_replanning"]=[account.get(key)==0 for key in ("new_provider_calls","new_sampling_calls","new_physical_batches","new_physical_draws")]
    checks["no_new_environment_samples_or_evaluation_replanning"].extend((payload["endpoint_evaluation_replanning_calls"]==0,payload["oracle_used_for_policy_construction"] is False))
    checks["historical_physical_costs_retained"]=[account["historical_physical_"+unit]==plan["source_historical_physical_"+unit]
        ==old["historical_physical_"+unit]+old["total_physical_"+unit] for unit in ("batches","draws")]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=Path("reports/controlled_predictive_crossfit_v38.json.gz"))
    parser.add_argument("--reference",type=Path,default=Path("reports/controlled_predictive_continuation_sources_analysis_v37.json"))
    parser.add_argument("--output",type=Path,default=Path("reports/controlled_predictive_crossfit_analysis_v38.json"))
    args=parser.parse_args(); started=perf_counter()
    with gzip.open(args.input,"rt",encoding="utf-8") as reader: payload=json.load(reader)
    reference=json.loads(args.reference.read_text(encoding="utf-8")); seconds=perf_counter()-started
    result=summarize(payload,reference); result["analysis_result_read_seconds"]=seconds
    with args.output.open("x",encoding="utf-8") as writer: json.dump(result,writer,indent=2,allow_nan=False); writer.write("\n")
    print(json.dumps({"output":str(args.output),"quality_complete_stream_count":result["quality_complete_stream_count"],
        "all_analysis_checks_passed":result["all_analysis_checks_passed"]}))


if __name__=="__main__": main()
