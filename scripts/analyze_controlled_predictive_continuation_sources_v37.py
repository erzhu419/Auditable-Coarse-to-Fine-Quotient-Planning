#!/usr/bin/env python3
"""Separate retained continuation errors into observed-row and mask terms."""
from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
from itertools import combinations
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import TOL, mean, monte_carlo_interval
from analyze_controlled_predictive_endpoint_errors_v36 import signed, identity_counts, policy_group, group_counts, GROUPS, root_statistics as v36_statistics
from analyze_controlled_predictive_budget_transfer_v35 import (
    stream_statistics as v35_statistics, all_actual_costs, policy_metrics, cost_metrics, COST_METRICS, IDENTITY_FIELDS)

CONFIGURATIONS=("CACHED24","CACHED32")
MODES=("RAW","REMOVE_E","REMOVE_C")
ERROR_FIELDS=("A_transition_error","D_continuation_error","E_estimation_error","C_coverage_error")
MARGIN_FIELDS=tuple(key+"_difference" for key in ("q_hat","q_star",*ERROR_FIELDS))
ROOT_METRICS=("root_action_regret","root_wrong_rate")


def root_means(contexts):
    boards=defaultdict(list)
    for context in contexts: boards[context["identity"]["board_index"]].append(context)
    def value(context,name,mode,key):
        row=context["configurations"][name]["diagnostic"]["modes"][mode]
        return row["regret"] if key=="root_action_regret" else float(row["wrong"])
    return {name:{mode:{key:mean([mean([value(context,name,mode,key) for context in rows]) for rows in boards.values()])
        for key in ROOT_METRICS} for mode in MODES} for name in CONFIGURATIONS}


def root_statistics(repetitions):
    streams=[{"replicate_index":rep["replicate_index"],"base_seed":rep["base_seed"],"configurations":root_means(rep["contexts"])} for rep in repetitions]
    return {"stream_count":len(streams),"unit":"one retained V35 suffix stream; average ten queries per board, then sixteen fixed boards",
        "configurations":{name:{mode:{key:monte_carlo_interval([row["configurations"][name][mode][key] for row in streams])
            for key in ROOT_METRICS} for mode in MODES} for name in CONFIGURATIONS},
        "mode_minus_RAW":{name:{mode:{key:monte_carlo_interval([row["configurations"][name][mode][key]-row["configurations"][name]["RAW"][key]
            for row in streams]) for key in ROOT_METRICS} for mode in MODES[1:]} for name in CONFIGURATIONS},
        "CACHED32_minus_CACHED24":{mode:{key:monte_carlo_interval([row["configurations"]["CACHED32"][mode][key]-row["configurations"]["CACHED24"][mode][key]
            for row in streams]) for key in ROOT_METRICS} for mode in MODES}},streams


def margin_summary(rows):
    return {"pair_count":len(rows),"fields":{key:signed([row.get(key) for row in rows]) for key in MARGIN_FIELDS},
        "opposite_sign_E_C_count":sum(row.get("E_estimation_error_difference") is not None and row.get("C_coverage_error_difference") is not None
            and row["E_estimation_error_difference"]*row["C_coverage_error_difference"]<0
            and min(abs(row["E_estimation_error_difference"]),abs(row["C_coverage_error_difference"]))>TOL for row in rows)}


def mode_changes(contexts,name,mode):
    repaired,new,changed=[],[],[]; delta=[]
    for context in contexts:
        modes=context["configurations"][name]["diagnostic"]["modes"]; raw,current=modes["RAW"],modes[mode]
        if raw["wrong"] and not current["wrong"]: repaired.append(context)
        if not raw["wrong"] and current["wrong"]: new.append(context)
        if raw["selected_action"]!=current["selected_action"]: changed.append(context)
        delta.append(current["regret"]-raw["regret"])
    return {"root_action_repaired":identity_counts(repaired),"root_action_new_error":identity_counts(new),
        "root_choice_changed":identity_counts(changed),"root_regret_change":signed(delta)}


def signed_points(contexts):
    result={"coverage":identity_counts(contexts),"configurations":{}}
    for name in CONFIGURATIONS:
        rows=[context["configurations"][name] for context in contexts]
        actions,pairs=defaultdict(list),defaultdict(list)
        for row in rows:
            for action,value in row["diagnostic"]["actions"].items(): actions[action].append(value)
            for value in row["diagnostic"]["pair_margins"]: pairs[tuple(value["actions"])].append(value)
        result["configurations"][name]={
            "original_full_policy":{key:signed([row["policy_evaluation"][key] for row in rows]) for key in ("total_regret","first_action_regret","continuation_regret")},
            "root_mode_means":{mode:{"root_action_regret":mean([row["diagnostic"]["modes"][mode]["regret"] for row in rows]),
                "root_wrong_rate":mean([float(row["diagnostic"]["modes"][mode]["wrong"]) for row in rows])} for mode in MODES},
            "mode_minus_RAW":{mode:mode_changes(contexts,name,mode) for mode in MODES[1:]},
            "selected_minus_exact_reference":margin_summary([row["diagnostic"]["selected_minus_reference"] for row in rows]),
            "legal_actions":{action:{"action_count":len(values),"fields":{key:signed([row.get(key) for row in values]) for key in (
                "q_hat","q_star",*ERROR_FIELDS,"batch_count")}} for action,values in sorted(actions.items())},
            "all_lexical_action_pairs":[{"actions":list(pair),**margin_summary(values)} for pair,values in sorted(pairs.items())]}
    cross=[context["cross_budget"] for context in contexts]
    result["fixed_pair_CACHED32_choice_minus_CACHED24_choice"]={"pair_count":len(cross),
        "same_action_pair_count":sum(row["actions"][0]==row["actions"][1] for row in cross),
        "before_at24":margin_summary([row["before_margin"] for row in cross]),
        "after_at32":margin_summary([row["after_margin"] for row in cross]),
        "change_32_minus_24":{key:signed([row["change"][key] for row in cross]) for key in MARGIN_FIELDS}}
    return result


def close(left,right):
    return left is not None and right is not None and math.isfinite(left) and math.isfinite(right) and abs(left-right)<=TOL


def validate_margin(margin,actions):
    left,right=(actions[name] for name in margin["actions"]); checks=[]
    for key in MARGIN_FIELDS:
        field=key.removesuffix("_difference")
        expected=left[field]-right[field] if left[field] is not None and right[field] is not None else None
        checks.append(margin[key] is None if expected is None else close(margin[key],expected))
    if margin["decomposable"]:
        checks.extend((close(margin["D_continuation_error_difference"],margin["E_estimation_error_difference"]+margin["C_coverage_error_difference"]),
            close(margin["q_hat_difference"]-margin["q_star_difference"],margin["A_transition_error_difference"]+margin["E_estimation_error_difference"]+margin["C_coverage_error_difference"])))
    return all(checks)


def validate_endpoint(row,reference,checks):
    source=all(row.get(key,{}).get("passed") is True for key in ("source_validation","restoration_validation"))
    checks["endpoint_source_labels"].append(row["source_valid"]==source)
    diagnostic=row.get("diagnostic")
    valid=source and all(row.get(key,{}).get("passed") is True for key in ("local_reproduction_validation","legacy_diagnostic_reproduction_validation","diagnostic_validation","inherited_policy_validation"))
    policy=row.get("policy_evaluation")
    valid &= bool(policy and all(policy.get(key) is True for key in ("policy_evaluable","identities_pass","reach_probability_pass")))
    if not diagnostic: return source,False
    actions=diagnostic["actions"]
    exact=min(actions,key=lambda action:(-actions[action]["q_star"],action))
    numerical=[diagnostic["exact_reference_action"]==exact==reference]
    available=all(action["decomposable"] for action in actions.values())
    checks["all_legal_action_mode_availability"].append(list(diagnostic["modes"])==list(MODES)
        and row["diagnostic_available"]==available and all(diagnostic["modes"][mode]["available"]==(mode=="RAW" or available) for mode in MODES))
    for action in actions.values():
        if not action["decomposable"]: continue
        e,c,a,d=(action[field] for field in ("E_estimation_error","C_coverage_error","A_transition_error","D_continuation_error"))
        numerical.extend((close(d,e+c),close(action["q_hat"]-action["q_star"],a+e+c),c<=TOL,
            close(action["q_mask"],action["q_hat_exact_continuation"]+c),close(action["q_hat"]-action["q_mask"],e),
            action["mode_values"]["REMOVE_E"]==action["q_mask"],
            action["mode_values"]["REMOVE_C"]==action["q_hat_exact_continuation"]+e))
    for mode in MODES:
        current=diagnostic["modes"][mode]
        if current["available"]:
            chosen=min(actions,key=lambda action:(-actions[action]["mode_values"][mode],action))
            regret=actions[exact]["q_star"]-actions[chosen]["q_star"]
            numerical.extend((current["selected_action"]==chosen,current["regret"]==regret,current["wrong"]==(regret>TOL)))
    numerical.append([row["actions"] for row in diagnostic["pair_margins"]]==[list(pair) for pair in combinations(sorted(actions),2)])
    numerical.extend(validate_margin(margin,actions) for margin in (*diagnostic["pair_margins"],diagnostic["selected_minus_reference"]))
    margin=diagnostic["selected_minus_reference"]
    numerical.append(margin["actions"]==[diagnostic["original_selected_action"],exact])
    old_raw=row["original_v36_modes"]["RAW"]; raw=diagnostic["modes"]["RAW"]
    numerical.append(all(raw[key]==old_raw[key] for key in ("selected_action","selected_value","wrong","regret")))
    if policy and policy.get("policy_evaluable"):
        numerical.extend((close(margin["q_star_difference"],-policy["first_action_regret"]),diagnostic["original_selected_action"]==policy["initial_action"],
            close(policy["total_regret"],policy["first_action_regret"]+policy["continuation_regret"])))
    checks["continuation_components_signed_identities_and_exact_modes"].extend(numerical)
    return source,bool(valid and available and all(numerical))


def validate_cross(context,checks):
    cross=context["cross_budget"]
    if not cross.get("available") or not cross.get("validation",{}).get("passed"): return False
    before,after=(context["configurations"][name]["diagnostic"] for name in CONFIGURATIONS)
    actions=[after["original_selected_action"],before["original_selected_action"]]
    valid=[cross["actions"]==cross["before_margin"]["actions"]==cross["after_margin"]["actions"]==actions,
        validate_margin(cross["before_margin"],before["actions"]),validate_margin(cross["after_margin"],after["actions"])]
    for key in MARGIN_FIELDS: valid.append(close(cross["change"][key],cross["after_margin"][key]-cross["before_margin"][key]))
    change=cross["change"]
    valid.extend((change["q_star_difference"]==0.,close(change["D_continuation_error_difference"],change["E_estimation_error_difference"]+change["C_coverage_error_difference"]),
        close(change["q_hat_difference"],change["A_transition_error_difference"]+change["E_estimation_error_difference"]+change["C_coverage_error_difference"])))
    if actions[0]==actions[1]: valid.append(all(cross[field][key]==0. for field in ("before_margin","after_margin","change") for key in MARGIN_FIELDS))
    checks["fixed_cross_budget_E_C_change_identities"].extend(valid)
    return all(valid)


def summarize(payload,reference):
    started=perf_counter(); plan=payload["plan"]; checks=defaultdict(list)
    identities=[{key:row[key] for key in IDENTITY_FIELDS} for row in plan["contexts"]]
    references={row["context_index"]:row["action"] for row in payload["exact_reference_actions"]}
    fixed={row["name"]:row for row in plan["configurations"]}
    checks["frozen_full_H2_cohort_and_modes"]=[plan["compared_configurations"]==list(CONFIGURATIONS),plan["modes"]==list(MODES),
        len(identities)==plan["context_count"]==160,plan["board_count"]==16,plan["query_count"]==10,
        all(row["horizon"]==2 for row in plan["boards"]),len(payload["repetitions"])==plan["replicate_count"]==16,
        [{key:rep[key] for key in ("replicate_index","base_seed")} for rep in payload["repetitions"]]==plan["replicates"],
        set(references)=={identity["context_index"] for identity in identities}]
    checks["source_binding_and_single_retained_stream"]=[payload["plan_binding_validation"]["passed"],payload["source_endpoint_stream_complete"]]
    complete,statuses,exclusions=[],[],[]
    for rep in payload["repetitions"]:
        roster=[context["identity"] for context in rep["contexts"]]==identities
        checks["retained_context_roster"].append(roster)
        source=roster and payload["plan_binding_validation"]["passed"]; diagnostic=source
        for context in rep["contexts"]:
            flags=[validate_endpoint(context["configurations"][name],references[context["identity"]["context_index"]],checks) for name in CONFIGURATIONS]
            configuration_matches=all(context["configurations"][name]["configuration"]==fixed[name] for name in CONFIGURATIONS)
            checks["fixed_configuration_binding"].append(configuration_matches)
            context_source=all(flag[0] for flag in flags) and configuration_matches
            context_diagnostic=context_source and all(flag[1] for flag in flags) and validate_cross(context,checks)
            checks["context_common_diagnostic_labels"].append(context["source_valid"]==context_source and context["complete"]==context_diagnostic)
            source &= context_source; diagnostic &= context_diagnostic
            if not context_diagnostic: exclusions.append({"replicate_index":rep["replicate_index"],"identity":context["identity"],
                "configurations":{name:{"source_valid":flag[0],"diagnostic_complete":flag[1],"status":context["configurations"][name]["status"]}
                    for name,flag in zip(CONFIGURATIONS,flags)},"cross_budget_available":context["cross_budget"]["available"]})
        checks["whole_stream_diagnostic_labels"].append(rep["source_valid"]==source and rep["complete"]==diagnostic)
        statuses.append({"replicate_index":rep["replicate_index"],"base_seed":rep["base_seed"],"source_valid":source,"diagnostic_complete":diagnostic})
        if diagnostic: complete.append(rep)
    old_v36=[rep for rep in payload["original_v36_repetitions"] if rep["complete"]]
    original_root,original_root_streams=v36_statistics(old_v36)
    checks["original_V36_root_statistics_exact"]=[original_root_streams==reference["root_action_streams"],original_root==reference["root_action_counterfactual_statistics"]]
    old_groups=group_counts([row for rep in old_v36 for row in rep["contexts"]])
    checks["original_V36_full_policy_groups_exact"]=[old_groups==reference["common_diagnostic_full_policy_groups"]]
    original=payload["original_repetitions"]
    old_quality=[rep for rep in original if rep["complete"]]; old_cost=[rep for rep in original if rep["source_valid"]]
    quality,quality_streams=v35_statistics(old_quality,policy_metrics,("total_regret",))
    cost,cost_streams=v35_statistics(old_cost,cost_metrics,COST_METRICS)
    actual=all_actual_costs(original)
    checks["original_V35_three_configuration_quality_exact"]=[quality_streams==reference["original_quality_streams"]]
    checks["original_V35_three_configuration_cost_exact"]=[cost_streams==reference["original_cost_streams"],
        actual==payload["original_all_actual_configuration_costs"]==reference["all_original_actual_configuration_costs"]]
    checks["original_acquisition_and_diagnostic_accounting_exact"]=[payload["original_source_accounting"]==reference["original_source_accounting"],
        payload["source_diagnostic_accounting"]==reference["accounting"]]
    check_accounting(payload,checks)
    stats,streams=root_statistics(complete); contexts=[row for rep in complete for row in rep["contexts"]]
    checked={key:{"passed":all(values),"checked":len(values),"failed":sum(not value for value in values)} for key,values in checks.items()}
    return {"schema":"acfqp.controlled_predictive_continuation_sources_analysis.v37","configurations":list(CONFIGURATIONS),"modes":list(MODES),
        "diagnostic_complete_stream_count":len(complete),"source_valid_stream_count":sum(row["source_valid"] for row in statuses),
        "root_action_counterfactual_statistics":stats,"root_action_streams":streams,"whole_cohort_signed_decomposition":signed_points(contexts),
        "groups_descriptive":{group:signed_points([context for context in contexts if policy_group(context)==group]) for group in GROUPS},
        "common_diagnostic_full_policy_groups":group_counts(contexts),"original_V36_full_policy_groups":old_groups,
        "original_V36_complete_stream_count":len(old_v36),"original_V36_root_action_statistics":original_root,"original_V36_root_action_streams":original_root_streams,
        "original_V35_quality_complete_stream_count":len(old_quality),"original_V35_source_cost_stream_count":len(old_cost),
        "original_primary_quality":quality,"original_independent_query_cost":cost,"original_quality_streams":quality_streams,"original_cost_streams":cost_streams,
        "all_original_actual_configuration_costs":actual,"original_source_accounting":payload["original_source_accounting"],
        "source_diagnostic_accounting":payload["source_diagnostic_accounting"],"accounting":payload["accounting"],
        "stream_statuses":statuses,"incomplete_context_instances":exclusions,"checks":checked,
        "all_analysis_checks_passed":all(row["passed"] for row in checked.values()),"analysis_seconds":perf_counter()-started,
        "scope":"All retained H2 CACHED24/32 endpoints, using the same complete whole-cohort stream mask for three new root-action modes. E includes observed-row estimation and maximum-selection effects; C is the fixed observation-mask/structural-boundary deficit. Corrections use oracle information for root R0 diagnosis, not new full-policy values or deployable gains. Original V36 diagnostics and V35 three-configuration quality/cost preserve their separate masks and all charges. Groups are descriptive; pointwise suffix-stream intervals condition on fixed boards and prefixes. No new samples or full-policy evaluation. This is not a formal Gate."}


def check_accounting(payload,checks):
    plan,account,old=payload["plan"],payload["accounting"],payload["original_source_accounting"]
    endpoints=[row for rep in payload["repetitions"] for context in rep["contexts"] for row in context["configurations"].values()]
    checks["all_retained_endpoints_and_diagnostic_calls"]=[len(endpoints)==plan["expected_endpoint_count"],account.get("source_endpoint_stream_reads",0)==1,
        account.get("source_endpoint_triple_records_read",0)==plan["expected_source_triples_read"]]
    for actual,expected in (("model_restore_calls","expected_model_restores"),("local_decomposition_calls","expected_local_evaluations")):
        checks["all_retained_endpoints_and_diagnostic_calls"].append(account.get(actual,0)==sum(row["accounting"].get(actual,0) for row in endpoints)==plan[expected])
    actions=[action for row in endpoints for action in row.get("diagnostic",{}).get("actions",{}).values()]
    checks["all_legal_action_decomposition_accounting"]=[len(actions)==plan["expected_action_decompositions"],
        account.get("action_decompositions",0)==sum(action["decomposable"] for action in actions)]
    checks["no_new_acquisition_or_full_policy_evaluation"]=[account.get(key)==0 and all(row["accounting"].get(key)==0 for row in endpoints)
        for key in ("new_provider_calls","new_sampling_calls","new_physical_batches","new_physical_draws")]
    checks["no_new_acquisition_or_full_policy_evaluation"].extend((account.get("frozen_policy_evaluation_calls",0)==plan["expected_policy_evaluations"]==0,
        payload["endpoint_evaluation_replanning_calls"]==0,payload["oracle_used_for_replay_selection"] is False))
    checks["complete_historical_physical_costs_retained"]=[account["historical_physical_"+unit]==plan["source_historical_physical_"+unit]
        ==old["historical_physical_"+unit]+old["total_physical_"+unit] for unit in ("batches","draws")]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=Path("reports/controlled_predictive_continuation_sources_v37.json.gz"))
    parser.add_argument("--reference",type=Path,default=Path("reports/controlled_predictive_endpoint_errors_analysis_v36.json"))
    parser.add_argument("--output",type=Path,default=Path("reports/controlled_predictive_continuation_sources_analysis_v37.json"))
    args=parser.parse_args(); started=perf_counter()
    with gzip.open(args.input,"rt",encoding="utf-8") as reader: payload=json.load(reader)
    reference=json.loads(args.reference.read_text(encoding="utf-8")); seconds=perf_counter()-started
    result=summarize(payload,reference); result["analysis_result_read_seconds"]=seconds
    with args.output.open("x",encoding="utf-8") as writer: json.dump(result,writer,indent=2,allow_nan=False); writer.write("\n")
    print(json.dumps({"output":str(args.output),"diagnostic_complete_stream_count":result["diagnostic_complete_stream_count"],
        "all_analysis_checks_passed":result["all_analysis_checks_passed"]}))


if __name__=="__main__": main()
