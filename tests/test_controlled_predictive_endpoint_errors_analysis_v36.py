from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import analyze_controlled_predictive_endpoint_errors_v36 as analysis
from run_controlled_predictive_endpoint_errors_v36 import cross_budget_pair
from acfqp.science.controlled_predictive_signed_errors_v25 import diagnose_target, _margin
from test_controlled_predictive_signed_errors_v25 import _target, _refresh_target
from test_controlled_predictive_budget_transfer_analysis_v35 import fixture as source_fixture
from test_controlled_predictive_new_starts_analysis_v28 import evaluation


def endpoint(target=None, name="CACHED24", continuation_regret=0.):
    target=target or _target({"DOWN":(1.,0.,0.,8),"LEFT":(.75,0.,0.,8),"RIGHT":(.5,0.,0.,8),"UP":(.25,0.,0.,8)})
    diagnostic=diagnose_target(target)
    reference=min(diagnostic["actions"],key=lambda action:(-diagnostic["actions"][action]["q_star"],action))
    diagnostic.update(exact_reference_action=reference,selected_minus_reference=_margin(target["selected_action"],reference,diagnostic["actions"]))
    policy={**evaluation(target["local_regret"]+continuation_regret),"initial_action":target["selected_action"],
        "first_action_regret":target["local_regret"],"continuation_regret":continuation_regret}
    accounting={key:0 for key in ("new_provider_calls","new_sampling_calls","new_physical_draws","new_physical_batches")}
    accounting.update(model_restore_calls=1,frozen_policy_evaluation_calls=1,local_decomposition_calls=1,numeric_diagnosis_calls=1,
        action_decompositions=sum(row["decomposable"] for row in diagnostic["actions"].values()))
    available=all(mode["available"] for mode in diagnostic["modes"].values())
    return {"configuration":{"name":name,"arm":"CACHED","budget":int(name[-2:])},"source_valid":True,
        **{key:{"passed":True} for key in ("source_validation","restoration_validation","evaluation_validation","value_reproduction_validation",
            "local_reproduction_validation","diagnostic_validation")},
        "diagnostic":diagnostic,"diagnostic_available":available,"local_evaluation":target,"policy_evaluation":policy,
        "status":"ENDPOINT_DIAGNOSTIC_COMPLETE" if available else "ENDPOINT_DIAGNOSTIC_INCOMPLETE","accounting":accounting}


def pair(before=None,after=None,index=0):
    before=before or endpoint(); after=after or endpoint(name="CACHED32")
    return {"identity":{"context_index":index,"board_index":0},"configurations":{"CACHED24":before,"CACHED32":after},
        "cross_budget":cross_budget_pair(before,after,analysis.TOL),"source_valid":True,"complete":True}


def fixture():
    original=source_fixture()
    for rep in original["repetitions"]:
        for context in rep["contexts"]:
            for row in context["configurations"].values(): row["evaluation"]["initial_action"]="DOWN"
    _,quality=analysis.original_statistics(original["repetitions"],analysis.policy_metrics,("total_regret",))
    _,cost=analysis.original_statistics(original["repetitions"],analysis.cost_metrics,analysis.COST_METRICS)
    actual=analysis.all_actual_costs(original["repetitions"])
    reference={"quality_streams":quality,"cost_streams":cost,"all_actual_configuration_costs":actual,"accounting":original["accounting"]}
    plan=json.loads((ROOT/"reports/controlled_predictive_endpoint_errors_plan_v36.json").read_text())
    template=pair(); repetitions=[]
    for rep in plan["replicates"]:
        contexts=[]
        for fixed in plan["contexts"]:
            context=deepcopy(template); context["identity"]={key:fixed[key] for key in analysis.IDENTITY_FIELDS}; contexts.append(context)
        repetitions.append({**rep,"contexts":contexts,"source_valid":True,"complete":True})
    account={"source_endpoint_stream_reads":1,"source_endpoint_triple_records_read":2560,
        "model_restore_calls":5120,"frozen_policy_evaluation_calls":5120,"local_decomposition_calls":5120,"numeric_diagnosis_calls":5120,
        "action_decompositions":20480,"historical_physical_batches":1128448,"historical_physical_draws":288882688,
        **{key:0 for key in ("new_provider_calls","new_sampling_calls","new_physical_batches","new_physical_draws")}}
    return {"plan":plan,"repetitions":repetitions,"original_repetitions":original["repetitions"],
        "original_source_accounting":original["accounting"],"original_all_actual_configuration_costs":actual,"accounting":account,
        "exact_reference_actions":[{"context_index":row["context_index"],"action":"DOWN"} for row in plan["contexts"]],
        "plan_binding_validation":{"passed":True},"source_endpoint_stream_complete":True,
        "endpoint_evaluation_replanning_calls":0,"oracle_used_for_replay_selection":False},reference


def test_exact_reference_separate_from_tolerance_labels_and_exact_mode_argmax():
    target=_target({"LEFT":(1.,0.,0.,8),"RIGHT":(1.+5e-11,0.,0.,8)})
    row=endpoint(target); checks=defaultdict(list)
    assert row["diagnostic"]["true_optimal_representative"]=="LEFT"
    assert row["diagnostic"]["exact_reference_action"]=="RIGHT"
    assert analysis.validate_endpoint(row,"RIGHT",checks)==(True,True)
    assert all(all(values) for values in checks.values())
    assert all(mode["selected_action"]=="RIGHT" and not mode["wrong"] for mode in row["diagnostic"]["modes"].values())
    row["diagnostic"]["exact_reference_action"]="LEFT"
    assert analysis.validate_endpoint(row,"RIGHT",defaultdict(list))==(True,False)


def test_full_policy_groups_do_not_treat_Rc_zero_as_D_zero_or_counterfactual_as_Vpi():
    correct=endpoint(); downstream_wrong=endpoint(continuation_regret=.2)
    cases=[pair(),pair(downstream_wrong,deepcopy(downstream_wrong),1),pair(downstream_wrong,correct,2),pair(correct,downstream_wrong,3)]
    assert [analysis.policy_group(context) for context in cases]==list(analysis.GROUPS)
    assert all(context["configurations"][name]["diagnostic"]["modes"]["RAW"]["regret"]==0 for context in cases for name in analysis.CONFIGURATIONS)
    cancellation=endpoint(_target({"LEFT":(1.,-.2,.4,8),"RIGHT":(.9,0.,0.,8)}))
    context=pair(cancellation,deepcopy(cancellation))
    result=analysis.signed_points([context])
    assert result["configurations"]["CACHED24"]["original_full_policy"]["continuation_regret"]["mean"]==0
    assert result["configurations"]["CACHED24"]["legal_actions"]["LEFT"]["fields"]["D_continuation_error"]["mean"]==.4
    change=result["configurations"]["CACHED24"]["mode_minus_RAW"]["REMOVE_D"]
    assert change["root_action_new_error"]["context_instance_count"]==1
    assert change["root_regret_change"]["mean"]==pytest.approx(.1)
    assert "total_regret" not in result["configurations"]["CACHED24"]["root_mode_means"]["REMOVE_D"]


def test_fixed_cross_budget_action_pair_and_same_action_zero_are_both_retained():
    before=endpoint(_target({"LEFT":(1.,-.4,.1,8),"RIGHT":(.9,0.,0.,8)}))
    after=endpoint(_target({"LEFT":(1.,-.1,.1,9),"RIGHT":(.9,0.,0.,8)}),name="CACHED32")
    changed=pair(before,after); same=pair(index=1)
    checks=defaultdict(list)
    assert analysis.validate_cross(changed,checks) and analysis.validate_cross(same,checks)
    cross=changed["cross_budget"]
    assert cross["actions"]==["LEFT","RIGHT"]
    assert cross["before_margin"]["q_hat_difference"]==pytest.approx(-.2)
    assert cross["after_margin"]["q_hat_difference"]==pytest.approx(.1)
    assert cross["change"]["A_transition_error_difference"]==pytest.approx(.3)
    assert cross["change"]["D_continuation_error_difference"]==cross["change"]["q_star_difference"]==0
    result=analysis.signed_points([changed,same])["fixed_pair_CACHED32_choice_minus_CACHED24_choice"]
    assert result["pair_count"]==2 and result["same_action_pair_count"]==1
    assert result["change_32_minus_24"]["q_hat_difference"]["mean"]==pytest.approx(.15)
    cross["after_margin"]["actions"].reverse()
    assert not analysis.validate_cross(changed,defaultdict(list))


def test_complete_cohort_reproduces_all_three_original_configurations_and_charges():
    payload,reference=fixture(); result=analysis.summarize(payload,reference)
    assert result["all_analysis_checks_passed"],{k:v for k,v in result["checks"].items() if not v["passed"]}
    assert result["diagnostic_complete_stream_count"]==result["original_quality_complete_stream_count"]==result["original_source_cost_stream_count"]==16
    assert result["original_quality_streams"]==reference["quality_streams"] and result["original_cost_streams"]==reference["cost_streams"]
    assert result["original_full_policy_groups"]["BOTH_CORRECT"]["context_instance_count"]==2560
    assert result["original_full_policy_groups"]["BOTH_CORRECT"]["unique_context_count"]==160
    assert result["whole_cohort_signed_decomposition"]["fixed_pair_CACHED32_choice_minus_CACHED24_choice"]["same_action_pair_count"]==2560
    assert result["all_original_actual_configuration_costs"]["GAP24"]["actual_run_count"]==2560
    assert result["accounting"]["historical_physical_draws"]==288882688 and result["accounting"]["new_physical_draws"]==0
    assert set(result["root_action_counterfactual_statistics"]["mode_minus_RAW"]["CACHED24"])=={"REMOVE_A","REMOVE_D"}


def test_unavailable_legal_action_excludes_whole_stream_without_losing_original_quality_or_gap_costs():
    payload,reference=fixture()
    rep=payload["repetitions"][0]; context=rep["contexts"][0]
    target=deepcopy(context["configurations"]["CACHED24"]["local_evaluation"])
    target["actions"]["UP"].update(observed=False,batch_count=0,q_hat=None,q_hat_exact_continuation=None,
        A_transition_error=None,D_continuation_error=None,total_error=None,identity_residual=None)
    row=endpoint(_refresh_target(target["actions"]))
    context["configurations"]["CACHED24"]=row; context["cross_budget"]=cross_budget_pair(row,context["configurations"]["CACHED32"],analysis.TOL)
    context["complete"]=False; rep["complete"]=False; payload["accounting"]["action_decompositions"]-=1
    assert not row["diagnostic"]["modes"]["REMOVE_A"]["available"] and row["diagnostic"]["modes"]["REMOVE_A"]["regret"] is None
    margin=analysis.margin_summary(row["diagnostic"]["pair_margins"])
    assert margin["fields"]["A_transition_error_difference"]["unavailable_count"]==3
    result=analysis.summarize(payload,reference)
    assert result["all_analysis_checks_passed"],{k:v for k,v in result["checks"].items() if not v["passed"]}
    assert result["diagnostic_complete_stream_count"]==15 and result["original_quality_complete_stream_count"]==result["original_source_cost_stream_count"]==16
    assert result["original_primary_quality"]["stream_count"]==16
    assert result["all_original_actual_configuration_costs"]==reference["all_actual_configuration_costs"]
    assert len(result["incomplete_context_instances"])==1 and len(result["stream_statuses"])==16


def test_root_stream_statistics_use_board_query_means_then_paired_stream_intervals():
    repetitions=[]
    for index in range(2):
        contexts=[]
        for board in range(16):
            for query in range(10):
                row=pair(index=10*board+query); row["identity"]["board_index"]=board
                if index==0 and board==0:
                    row["configurations"]["CACHED24"]["diagnostic"]["modes"]["RAW"]["regret"]=1.
                if index==1:
                    row["configurations"]["CACHED32"]["diagnostic"]["modes"]["RAW"]["regret"]=.2
                contexts.append(row)
        repetitions.append({"replicate_index":index,"base_seed":index+1,"contexts":contexts})
    stats,_=analysis.root_statistics(repetitions)
    delta=stats["CACHED32_minus_CACHED24"]["RAW"]["root_action_regret"]
    assert delta["count"]==2 and delta["degrees_of_freedom"]==1
    assert delta["mean"]==pytest.approx((.2-1/16)/2)
    assert delta["standard_error"]==pytest.approx((.2+1/16)/2)
