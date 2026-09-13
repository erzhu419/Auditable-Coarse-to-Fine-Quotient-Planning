from collections import defaultdict
from copy import deepcopy
from itertools import combinations
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import analyze_controlled_predictive_continuation_sources_v37 as analysis
from test_controlled_predictive_endpoint_errors_analysis_v36 import endpoint as old_endpoint, fixture as old_fixture
from test_controlled_predictive_signed_errors_v25 import _target


def margin(left,right,actions):
    a,b=actions[left],actions[right]
    return {"actions":[left,right],"decomposable":a["decomposable"] and b["decomposable"],
        **{field:a[key]-b[key] if a[key] is not None and b[key] is not None else None
            for field in analysis.MARGIN_FIELDS for key in (field.removesuffix("_difference"),)}}


def endpoint(old=None,components=None,q_masks=None):
    old=old or old_endpoint(); row=deepcopy(old); diagnostic=row["diagnostic"]
    row["inherited_policy_validation"]={"passed":True}; row["legacy_diagnostic_reproduction_validation"]={"passed":True}; row["original_v36_modes"]=deepcopy(old["diagnostic"]["modes"])
    for action,value in diagnostic["actions"].items():
        e,c=(components or {}).get(action,(value["D_continuation_error"],0.))
        value.update(E_estimation_error=e,C_coverage_error=c)
        value["q_mask"]=(q_masks or {}).get(action,value["q_hat_exact_continuation"]+c)
        value["mode_values"]={"RAW":value["lower"],"REMOVE_E":value["q_mask"],"REMOVE_C":value["q_hat_exact_continuation"]+e}
    actions=diagnostic["actions"]; best=max(value["q_star"] for value in actions.values()); modes={}
    for mode in analysis.MODES:
        choice=min(actions,key=lambda action:(-actions[action]["mode_values"][mode],action))
        regret=best-actions[choice]["q_star"]
        modes[mode]={"available":True,"selected_action":choice,"selected_value":actions[choice]["mode_values"][mode],"regret":regret,"wrong":regret>analysis.TOL}
    diagnostic["modes"]=modes
    diagnostic["pair_margins"]=[margin(left,right,actions) for left,right in combinations(sorted(actions),2)]
    diagnostic["selected_minus_reference"]=margin(diagnostic["original_selected_action"],diagnostic["exact_reference_action"],actions)
    row["accounting"]["frozen_policy_evaluation_calls"]=0
    return row


def pair(before=None,after=None,index=0):
    before=before or endpoint(); after=after or endpoint(old_endpoint(name="CACHED32"))
    left,right=after["diagnostic"]["original_selected_action"],before["diagnostic"]["original_selected_action"]
    first=margin(left,right,before["diagnostic"]["actions"]); last=margin(left,right,after["diagnostic"]["actions"])
    cross={"actions":[left,right],"before_margin":first,"after_margin":last,
        "change":{key:last[key]-first[key] for key in analysis.MARGIN_FIELDS},"available":True,"validation":{"passed":True}}
    return {"identity":{"context_index":index,"board_index":0},"source_valid":True,"complete":True,
        "configurations":{"CACHED24":before,"CACHED32":after},"cross_budget":cross}


def fixture():
    old,older_reference=old_fixture()
    old_stats,old_streams=analysis.v36_statistics(old["repetitions"])
    reference={"root_action_counterfactual_statistics":old_stats,"root_action_streams":old_streams,
        "common_diagnostic_full_policy_groups":analysis.group_counts([row for rep in old["repetitions"] for row in rep["contexts"]]),
        "original_quality_streams":older_reference["quality_streams"],"original_cost_streams":older_reference["cost_streams"],
        "all_original_actual_configuration_costs":older_reference["all_actual_configuration_costs"],
        "original_source_accounting":old["original_source_accounting"],"accounting":old["accounting"]}
    original_v36=[]; current=[]; template=pair()
    for rep in old["repetitions"]:
        originals,contexts=[],[]
        for row in rep["contexts"]:
            originals.append({"identity":row["identity"],"configurations":{name:{"diagnostic":{"modes":config["diagnostic"]["modes"]},
                "policy_evaluation":config["policy_evaluation"]} for name,config in row["configurations"].items()}})
            context=deepcopy(template); context["identity"]=row["identity"]; contexts.append(context)
        original_v36.append({**{key:value for key,value in rep.items() if key!="contexts"},"contexts":originals})
        current.append({**{key:value for key,value in rep.items() if key!="contexts"},"contexts":contexts})
    account=deepcopy(old["accounting"]); account["frozen_policy_evaluation_calls"]=0
    payload={**old,"plan":json.loads((ROOT/"reports/controlled_predictive_continuation_sources_plan_v37.json").read_text()),
        "repetitions":current,"original_v36_repetitions":original_v36,"source_diagnostic_accounting":old["accounting"],"accounting":account}
    return payload,reference


def test_remove_E_uses_direct_q_mask_and_exact_ranking_not_subtraction_or_tolerance():
    old=old_endpoint(_target({"LEFT":(.3,.2,0.,8),"RIGHT":(.1,.3,.2,8,.6)}))
    row=endpoint(old,{"LEFT":(.2,-.2),"RIGHT":(.3,-.1)},{"LEFT":.3,"RIGHT":.1+.2})
    checks=defaultdict(list)
    assert analysis.validate_endpoint(row,"LEFT",checks)==(True,True)
    assert all(all(values) for values in checks.values())
    right=row["diagnostic"]["actions"]["RIGHT"]
    assert right["q_hat"]-right["E_estimation_error"]==.3
    assert right["q_mask"]>.3 and row["diagnostic"]["modes"]["REMOVE_E"]["selected_action"]=="RIGHT"
    right["mode_values"]["REMOVE_E"]=right["q_hat"]-right["E_estimation_error"]
    assert analysis.validate_endpoint(row,"LEFT",defaultdict(list))==(True,False)


def test_coverage_correction_repairs_but_estimation_correction_can_destroy_cancellation():
    old=old_endpoint(_target({"LEFT":(1.,0.,-.2,8),"RIGHT":(.9,0.,0.,8)}))
    before=endpoint(old,{"LEFT":(.1,-.3)})
    after=endpoint(old_endpoint(_target({"LEFT":(1.,0.,.1,9),"RIGHT":(.9,0.,0.,8)}),name="CACHED32"),{"LEFT":(.4,-.3)})
    context=pair(before,after); checks=defaultdict(list)
    assert analysis.validate_cross(context,checks)
    result=analysis.signed_points([context]); c24=result["configurations"]["CACHED24"]; c32=result["configurations"]["CACHED32"]
    assert c24["mode_minus_RAW"]["REMOVE_C"]["root_action_repaired"]["context_instance_count"]==1
    assert c24["mode_minus_RAW"]["REMOVE_E"]["root_action_repaired"]["context_instance_count"]==0
    assert c32["mode_minus_RAW"]["REMOVE_E"]["root_action_new_error"]["context_instance_count"]==1
    assert c32["mode_minus_RAW"]["REMOVE_E"]["root_regret_change"]["mean"]==pytest.approx(.1)
    assert "total_regret" not in c32["root_mode_means"]["REMOVE_E"]
    cross=result["fixed_pair_CACHED32_choice_minus_CACHED24_choice"]
    assert cross["change_32_minus_24"]["E_estimation_error_difference"]["mean"]==pytest.approx(.3)
    assert cross["change_32_minus_24"]["C_coverage_error_difference"]["mean"]==0
    assert analysis.policy_group(context)=="24_WRONG_32_CORRECT"
    assert c24["selected_minus_exact_reference"]["fields"]["C_coverage_error_difference"]["mean"]==.3


def test_full_cohort_retains_all_masks_old_three_modes_full_cost_and_zero_same_action_pairs():
    payload,reference=fixture(); result=analysis.summarize(payload,reference)
    assert result["all_analysis_checks_passed"],{k:v for k,v in result["checks"].items() if not v["passed"]}
    assert result["diagnostic_complete_stream_count"]==result["original_V36_complete_stream_count"]==16
    assert result["original_V35_quality_complete_stream_count"]==result["original_V35_source_cost_stream_count"]==16
    assert result["original_V36_root_action_streams"]==reference["root_action_streams"]
    assert result["whole_cohort_signed_decomposition"]["fixed_pair_CACHED32_choice_minus_CACHED24_choice"]["same_action_pair_count"]==2560
    assert set(result["root_action_counterfactual_statistics"]["configurations"]["CACHED24"])=={"RAW","REMOVE_E","REMOVE_C"}
    assert set(result["original_V36_root_action_statistics"]["configurations"]["CACHED24"])=={"RAW","REMOVE_A","REMOVE_D"}
    assert result["all_original_actual_configuration_costs"]["GAP24"]["actual_run_count"]==2560
    assert result["source_diagnostic_accounting"]["frozen_policy_evaluation_calls"]==5120
    assert result["accounting"]["frozen_policy_evaluation_calls"]==result["accounting"]["new_physical_draws"]==0


@pytest.mark.parametrize("failed_field", ["diagnostic_validation", "legacy_diagnostic_reproduction_validation"])
def test_failed_new_diagnostic_excludes_entire_stream_preserving_old_groups_quality_and_fees(failed_field):
    payload,reference=fixture(); rep=payload["repetitions"][0]; context=rep["contexts"][0]
    row=context["configurations"]["CACHED24"]
    row[failed_field]={"passed":False}; row["status"]="CONTINUATION_DIAGNOSTIC_INCOMPLETE"
    context["complete"]=False; rep["complete"]=False
    result=analysis.summarize(payload,reference)
    assert result["all_analysis_checks_passed"]
    assert result["diagnostic_complete_stream_count"]==15 and result["source_valid_stream_count"]==16
    assert result["original_V36_complete_stream_count"]==result["original_V35_quality_complete_stream_count"]==result["original_V35_source_cost_stream_count"]==16
    assert result["original_V36_full_policy_groups"]["BOTH_CORRECT"]["context_instance_count"]==2560
    assert result["common_diagnostic_full_policy_groups"]["BOTH_CORRECT"]["context_instance_count"]==2400
    assert result["all_original_actual_configuration_costs"]==reference["all_original_actual_configuration_costs"]
    assert result["source_diagnostic_accounting"]==reference["accounting"]
    assert len(result["stream_statuses"])==16 and len(result["incomplete_context_instances"])==1
    assert result["accounting"]["historical_physical_draws"]==288882688


def test_new_mode_paired_interval_uses_query_board_means_and_streams():
    repetitions=[]
    for index in range(2):
        contexts=[]
        for board in range(16):
            for query in range(10):
                context=pair(index=10*board+query); context["identity"]["board_index"]=board
                modes=context["configurations"]["CACHED24"]["diagnostic"]["modes"]
                if index==0 and board==0: modes["RAW"]["regret"]=1.
                if index==1: modes["REMOVE_C"]["regret"]=.2
                contexts.append(context)
        repetitions.append({"replicate_index":index,"base_seed":index+1,"contexts":contexts})
    stats,_=analysis.root_statistics(repetitions)
    delta=stats["mode_minus_RAW"]["CACHED24"]["REMOVE_C"]["root_action_regret"]
    assert delta["count"]==2 and delta["degrees_of_freedom"]==1
    assert delta["mean"]==pytest.approx((.2-1/16)/2) and delta["standard_error"]==pytest.approx((.2+1/16)/2)
