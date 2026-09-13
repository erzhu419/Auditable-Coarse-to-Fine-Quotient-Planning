#!/usr/bin/env python3
"""Summarize all retained CACHED endpoint action decompositions and old costs."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
from itertools import combinations
import json
import math
from pathlib import Path
from time import perf_counter

from analyze_controlled_predictive_repetitions_v22 import TOL, mean, differences, monte_carlo_interval
from analyze_controlled_predictive_budget_transfer_v35 import (
    stream_statistics as original_statistics, all_actual_costs, policy_metrics, cost_metrics, COST_METRICS, IDENTITY_FIELDS)

CONFIGURATIONS = ("CACHED24", "CACHED32")
MODES = ("RAW", "REMOVE_A", "REMOVE_D")
GROUPS = ("BOTH_CORRECT", "BOTH_WRONG", "24_WRONG_32_CORRECT", "24_CORRECT_32_WRONG")
MARGIN_FIELDS = ("q_hat_difference", "q_star_difference", "A_transition_error_difference", "D_continuation_error_difference", "total_error_difference")
ROOT_METRICS = ("root_action_regret", "root_wrong_rate")


def signed(values):
    available = [value for value in values if value is not None]
    return {**differences(available), "unavailable_count": len(values)-len(available),
        "mean_absolute": mean([abs(value) for value in available]),
        "minimum": min(available) if available else None, "maximum": max(available) if available else None}


def margin_summary(rows):
    return {"pair_count": len(rows), "fields": {key: signed([row.get(key) for row in rows]) for key in MARGIN_FIELDS},
        "opposite_sign_A_D_count": sum(row.get("opposite_sign_A_D") is True for row in rows),
        "cancelled_absolute_error": signed([row.get("cancelled_absolute_error") for row in rows])}


def identity_counts(contexts):
    counts = Counter(row["identity"]["context_index"] for row in contexts)
    return {"context_instance_count": len(contexts), "unique_context_count": len(counts),
        "instances_by_context_index": {str(key): value for key,value in sorted(counts.items())}}


def policy_group(context, field="policy_evaluation"):
    values = [context["configurations"][name].get(field) for name in CONFIGURATIONS]
    if any(not value or not value.get("policy_evaluable") or value.get("total_regret") is None for value in values): return None
    correct = [value["total_regret"] <= TOL for value in values]
    return ("BOTH_CORRECT" if all(correct) else "BOTH_WRONG" if not any(correct)
        else "24_WRONG_32_CORRECT" if correct[1] else "24_CORRECT_32_WRONG")


def group_counts(contexts, field="policy_evaluation"):
    groups = {name: [] for name in (*GROUPS, "UNAVAILABLE")}
    for context in contexts: groups[policy_group(context,field) or "UNAVAILABLE"].append(context)
    return {name: identity_counts(rows) for name,rows in groups.items()}


def mode_changes(contexts, name, mode):
    repaired, new, changed, delta = [], [], [], []
    for context in contexts:
        modes = context["configurations"][name]["diagnostic"]["modes"]
        raw, current = modes["RAW"], modes[mode]
        if raw["wrong"] and not current["wrong"]: repaired.append(context)
        if not raw["wrong"] and current["wrong"]: new.append(context)
        if raw["selected_action"] != current["selected_action"]: changed.append(context)
        delta.append(current["regret"]-raw["regret"])
    return {"root_action_repaired": identity_counts(repaired), "root_action_new_error": identity_counts(new),
        "root_choice_changed": identity_counts(changed), "root_regret_change": signed(delta)}


def root_means(contexts):
    boards = defaultdict(list)
    for context in contexts: boards[context["identity"]["board_index"]].append(context)
    def metric(context,name,mode,key):
        row=context["configurations"][name]["diagnostic"]["modes"][mode]
        return row["regret"] if key == "root_action_regret" else float(row["wrong"])
    return {name:{mode:{key:mean([mean([metric(context,name,mode,key) for context in rows]) for rows in boards.values()])
        for key in ROOT_METRICS} for mode in MODES} for name in CONFIGURATIONS}


def root_statistics(repetitions):
    streams = [{"replicate_index": rep["replicate_index"], "base_seed": rep["base_seed"],
        "configurations": root_means(rep["contexts"])} for rep in repetitions]
    return {"stream_count":len(streams),
        "unit":"one retained V35 suffix stream; average ten queries within each board, then sixteen fixed boards",
        "configurations":{name:{mode:{key:monte_carlo_interval([row["configurations"][name][mode][key] for row in streams])
            for key in ROOT_METRICS} for mode in MODES} for name in CONFIGURATIONS},
        "mode_minus_RAW":{name:{mode:{key:monte_carlo_interval([row["configurations"][name][mode][key]-row["configurations"][name]["RAW"][key]
            for row in streams]) for key in ROOT_METRICS} for mode in MODES[1:]} for name in CONFIGURATIONS},
        "CACHED32_minus_CACHED24":{mode:{key:monte_carlo_interval([row["configurations"]["CACHED32"][mode][key]-row["configurations"]["CACHED24"][mode][key]
            for row in streams]) for key in ROOT_METRICS} for mode in MODES}}, streams


def signed_points(contexts):
    result = {"coverage":identity_counts(contexts), "configurations":{}}
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
            "legal_actions":{action:{"action_count":len(values), "fields":{key:signed([row[key] for row in values]) for key in (
                "q_hat","q_star","A_transition_error","D_continuation_error","signed_total_error","batch_count")},
                "opposite_sign_A_D_count":sum(row["opposite_sign_A_D"] is True for row in values)} for action,values in sorted(actions.items())},
            "all_lexical_action_pairs":[{"actions":list(pair),**margin_summary(values)} for pair,values in sorted(pairs.items())]}
    cross=[context["cross_budget"] for context in contexts]
    result["fixed_pair_CACHED32_choice_minus_CACHED24_choice"]={"pair_count":len(cross),
        "same_action_pair_count":sum(row["actions"][0]==row["actions"][1] for row in cross),
        "before_at24":margin_summary([row["before_margin"] for row in cross]),
        "after_at32":margin_summary([row["after_margin"] for row in cross]),
        "change_32_minus_24":{key:signed([row["change"][key] for row in cross]) for key in MARGIN_FIELDS}}
    return result


def close(a,b):
    return a is not None and b is not None and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=TOL


def validate_margin(margin, actions):
    left,right=(actions[name] for name in margin["actions"])
    valid=[]
    for key in MARGIN_FIELDS:
        field=key.removesuffix("_difference")
        expected=left[field]-right[field] if left[field] is not None and right[field] is not None else None
        valid.append(margin[key] is None if expected is None else close(margin[key],expected))
    if margin["decomposable"]:
        valid.append(close(margin["q_hat_difference"]-margin["q_star_difference"],
            margin["A_transition_error_difference"]+margin["D_continuation_error_difference"]))
    return all(valid)


def validate_endpoint(row, exact_reference, checks):
    source=all(row.get(key,{}).get("passed") is True for key in ("source_validation","restoration_validation"))
    checks["endpoint_source_labels"].append(row["source_valid"] == source)
    diagnostic=row.get("diagnostic")
    required=("evaluation_validation","value_reproduction_validation","local_reproduction_validation","diagnostic_validation")
    valid=source and all(row.get(key,{}).get("passed") is True for key in required)
    policy=row.get("policy_evaluation")
    valid &= bool(policy and all(policy.get(key) is True for key in ("policy_evaluable","identities_pass","reach_probability_pass")))
    if not diagnostic: return source,False
    actions=diagnostic["actions"]
    reference=min(actions,key=lambda action:(-actions[action]["q_star"],action))
    exact=diagnostic["exact_reference_action"]==reference==exact_reference
    checks["fixed_exact_true_reference"].append(exact)
    available=all(action["decomposable"] for action in actions.values())
    checks["all_legal_action_mode_availability"].append(list(diagnostic["modes"])==list(MODES)
        and row["diagnostic_available"]==available and all(diagnostic["modes"][mode]["available"]==(mode=="RAW" or available) for mode in MODES))
    numerical=[]
    for action in actions.values():
        if action["decomposable"]:
            numerical.extend((close(action["q_hat"]-action["q_star"],action["A_transition_error"]+action["D_continuation_error"]),
                close(action["mode_values"]["REMOVE_A"],action["q_star"]+action["D_continuation_error"]),
                action["mode_values"]["REMOVE_D"]==action["q_hat_exact_continuation"]))
    for mode in MODES:
        current=diagnostic["modes"][mode]
        if current["available"]:
            chosen=min(actions,key=lambda action:(-actions[action]["mode_values"][mode],action))
            regret=actions[reference]["q_star"]-actions[chosen]["q_star"]
            numerical.extend((current["selected_action"]==chosen,current["regret"]==regret,current["wrong"]==(regret>TOL)))
    expected_pairs=[list(pair) for pair in combinations(sorted(actions),2)]
    numerical.append([margin["actions"] for margin in diagnostic["pair_margins"]]==expected_pairs)
    numerical.extend(validate_margin(margin,actions) for margin in (*diagnostic["pair_margins"],diagnostic["selected_minus_reference"]))
    margin=diagnostic["selected_minus_reference"]
    numerical.append(margin["actions"]==[diagnostic["original_selected_action"],reference])
    if policy and policy.get("policy_evaluable"):
        numerical.extend((close(margin["q_star_difference"],-policy["first_action_regret"]),
            diagnostic["original_selected_action"]==policy["initial_action"],
            close(policy["total_regret"],policy["first_action_regret"]+policy["continuation_regret"])))
    checks["signed_action_pair_and_mode_identities"].extend(numerical)
    return source,bool(valid and exact and available and all(numerical))


def validate_cross(context, checks):
    cross=context["cross_budget"]
    if not cross.get("available") or not cross.get("validation",{}).get("passed"): return False
    before,after=(context["configurations"][name]["diagnostic"] for name in CONFIGURATIONS)
    actions=[after["original_selected_action"],before["original_selected_action"]]
    valid=[cross["actions"]==cross["before_margin"]["actions"]==cross["after_margin"]["actions"]==actions,
        validate_margin(cross["before_margin"],before["actions"]),validate_margin(cross["after_margin"],after["actions"])]
    for key in MARGIN_FIELDS: valid.append(close(cross["change"][key],cross["after_margin"][key]-cross["before_margin"][key]))
    valid.extend((cross["change"]["q_star_difference"]==0.,close(cross["change"]["q_hat_difference"],
        cross["change"]["A_transition_error_difference"]+cross["change"]["D_continuation_error_difference"])))
    if actions[0]==actions[1]: valid.append(all(cross[field][key]==0. for field in ("before_margin","after_margin","change") for key in MARGIN_FIELDS))
    checks["fixed_cross_budget_pair_and_change_identities"].extend(valid)
    return all(valid)


def summarize(payload, reference):
    started=perf_counter(); plan=payload["plan"]; checks=defaultdict(list)
    identities=[{key:row[key] for key in IDENTITY_FIELDS} for row in plan["contexts"]]
    fixed_references={row["context_index"]:row["action"] for row in payload["exact_reference_actions"]}
    fixed={row["name"]:row for row in plan["configurations"]}
    checks["frozen_full_cohort_and_modes"]=[plan["compared_configurations"]==list(CONFIGURATIONS),plan["modes"]==list(MODES),
        len(identities)==plan["context_count"]==160,plan["board_count"]==16,plan["query_count"]==10,
        len(payload["repetitions"])==plan["replicate_count"]==16,
        [{key:rep[key] for key in ("replicate_index","base_seed")} for rep in payload["repetitions"]]==plan["replicates"],
        set(fixed_references)=={identity["context_index"] for identity in identities}]
    checks["source_binding_and_single_retained_stream"]=[payload["plan_binding_validation"]["passed"],payload["source_endpoint_stream_complete"]]
    complete, statuses, exclusions=[],[],[]
    for rep in payload["repetitions"]:
        roster=[context["identity"] for context in rep["contexts"]]==identities
        checks["retained_context_roster"].append(roster)
        source=roster and payload["plan_binding_validation"]["passed"]
        diagnostic=source
        for context in rep["contexts"]:
            flags=[validate_endpoint(context["configurations"][name],fixed_references[context["identity"]["context_index"]],checks) for name in CONFIGURATIONS]
            configuration_matches=all(context["configurations"][name]["configuration"]==fixed[name] for name in CONFIGURATIONS)
            checks["fixed_configuration_binding"].append(configuration_matches)
            context_source=all(flag[0] for flag in flags) and configuration_matches
            context_diagnostic=context_source and all(flag[1] for flag in flags) and validate_cross(context,checks)
            checks["context_common_diagnostic_labels"].append(context["source_valid"]==context_source and context["complete"]==context_diagnostic)
            source &= context_source; diagnostic &= context_diagnostic
            if not context_diagnostic: exclusions.append({"replicate_index":rep["replicate_index"],"identity":context["identity"],
                "configurations":{name:{"source_valid":flag[0],"diagnostic_complete":flag[1],
                    "status":context["configurations"][name]["status"]} for name,flag in zip(CONFIGURATIONS,flags)},
                "cross_budget_available":context["cross_budget"]["available"]})
        checks["whole_stream_diagnostic_labels"].append(rep["source_valid"]==source and rep["complete"]==diagnostic)
        statuses.append({"replicate_index":rep["replicate_index"],"base_seed":rep["base_seed"],"source_valid":source,"diagnostic_complete":diagnostic})
        if diagnostic: complete.append(rep)
    originals=payload["original_repetitions"]
    old_quality=[rep for rep in originals if rep["complete"]]; old_source=[rep for rep in originals if rep["source_valid"]]
    original_quality,quality_streams=original_statistics(old_quality,policy_metrics,("total_regret",))
    original_cost,cost_streams=original_statistics(old_source,cost_metrics,COST_METRICS)
    actual_costs=all_actual_costs(originals)
    checks["original_three_configuration_quality_exact"]=[quality_streams==reference["quality_streams"]]
    checks["original_three_configuration_cost_exact"]=[cost_streams==reference["cost_streams"],
        actual_costs==payload["original_all_actual_configuration_costs"]==reference["all_actual_configuration_costs"]]
    checks["original_accounting_exact"]=[payload["original_source_accounting"]==reference["accounting"]]
    check_accounting(payload,checks)
    stats,streams=root_statistics(complete)
    contexts=[context for rep in complete for context in rep["contexts"]]
    checked={key:{"passed":all(values),"checked":len(values),"failed":sum(not value for value in values)} for key,values in checks.items()}
    return {"schema":"acfqp.controlled_predictive_endpoint_errors_analysis.v36","configurations":list(CONFIGURATIONS),"modes":list(MODES),
        "diagnostic_complete_stream_count":len(complete),"source_valid_stream_count":sum(row["source_valid"] for row in statuses),
        "root_action_counterfactual_statistics":stats,"root_action_streams":streams,
        "whole_cohort_signed_decomposition":signed_points(contexts),
        "groups_descriptive":{group:signed_points([context for context in contexts if policy_group(context)==group]) for group in GROUPS},
        "original_full_policy_groups":group_counts([row for rep in old_quality for row in rep["contexts"]],"evaluation"),
        "common_diagnostic_full_policy_groups":group_counts(contexts),
        "original_quality_complete_stream_count":len(old_quality),"original_source_cost_stream_count":len(old_source),
        "original_primary_quality":original_quality,"original_independent_query_cost":original_cost,
        "original_quality_streams":quality_streams,"original_cost_streams":cost_streams,
        "all_original_actual_configuration_costs":actual_costs,"original_source_accounting":payload["original_source_accounting"],
        "accounting":payload["accounting"],"stream_statuses":statuses,"incomplete_context_instances":exclusions,
        "checks":checked,"all_analysis_checks_passed":all(row["passed"] for row in checked.values()),"analysis_seconds":perf_counter()-started,
        "scope":"All retained CACHED24/32 endpoints, including same-action pairs and correct policies. Main diagnostics share one complete whole-cohort suffix-stream mask. Three-mode corrections rank root actions against optimal continuation; they are not new full-policy values or deployable methods. Full-policy groups use original V35 total regret, and are descriptive. Intervals are pointwise Monte Carlo intervals conditional on the fixed V35 boards and prefixes. All original three-configuration fees, including GAP24 and excluded diagnostics, remain charged. No new samples or planner decisions; restoration and evaluation costs are separate. Rc=0 does not imply D=0. This is not a formal scientific Gate."}


def check_accounting(payload,checks):
    plan,account,old=payload["plan"],payload["accounting"],payload["original_source_accounting"]
    endpoints=[row for rep in payload["repetitions"] for context in rep["contexts"] for row in context["configurations"].values()]
    checks["all_retained_endpoints_and_diagnostic_calls"]=[len(endpoints)==plan["expected_endpoint_count"],
        account.get("source_endpoint_stream_reads",0)==1,account.get("source_endpoint_triple_records_read",0)==plan["expected_source_triples_read"]]
    for actual,expected in (("model_restore_calls","expected_model_restores"),("frozen_policy_evaluation_calls","expected_policy_evaluations"),
            ("local_decomposition_calls","expected_local_evaluations")):
        checks["all_retained_endpoints_and_diagnostic_calls"].append(account.get(actual,0)==sum(row["accounting"].get(actual,0) for row in endpoints)==plan[expected])
    actions=[action for row in endpoints for action in row.get("diagnostic",{}).get("actions",{}).values()]
    checks["all_legal_action_decomposition_accounting"]=[len(actions)==plan["expected_action_decompositions"],
        account.get("action_decompositions",0)==sum(row["decomposable"] for row in actions),
        account.get("numeric_diagnosis_calls",0)==sum(row["accounting"].get("numeric_diagnosis_calls",0) for row in endpoints)]
    checks["no_new_acquisition_or_policy_changes"]=[account.get(key)==0 and all(row["accounting"].get(key)==0 for row in endpoints)
        for key in ("new_provider_calls","new_sampling_calls","new_physical_batches","new_physical_draws")]
    checks["no_new_acquisition_or_policy_changes"].extend((payload["endpoint_evaluation_replanning_calls"]==0,payload["oracle_used_for_replay_selection"] is False))
    checks["complete_historical_physical_costs_retained"]=[account["historical_physical_"+unit]==plan["source_historical_physical_"+unit]
        ==old["historical_physical_"+unit]+old["total_physical_"+unit] for unit in ("batches","draws")]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=Path("reports/controlled_predictive_endpoint_errors_v36.json.gz"))
    parser.add_argument("--reference",type=Path,default=Path("reports/controlled_predictive_budget_transfer_analysis_v35.json"))
    parser.add_argument("--output",type=Path,default=Path("reports/controlled_predictive_endpoint_errors_analysis_v36.json"))
    args=parser.parse_args(); started=perf_counter()
    with gzip.open(args.input,"rt",encoding="utf-8") as reader: payload=json.load(reader)
    reference=json.loads(args.reference.read_text(encoding="utf-8")); read_seconds=perf_counter()-started
    result=summarize(payload,reference); result["analysis_result_read_seconds"]=read_seconds
    with args.output.open("x",encoding="utf-8") as writer: json.dump(result,writer,indent=2,allow_nan=False); writer.write("\n")
    print(json.dumps({"output":str(args.output),"diagnostic_complete_stream_count":result["diagnostic_complete_stream_count"],
        "all_analysis_checks_passed":result["all_analysis_checks_passed"]}))


if __name__=="__main__": main()
