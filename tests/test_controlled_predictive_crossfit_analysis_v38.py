from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import analyze_controlled_predictive_crossfit_v38 as analysis
from test_controlled_predictive_budget_transfer_analysis_v35 import fixture as source_fixture
from test_controlled_predictive_new_starts_analysis_v28 import evaluation


def fixture():
    original=source_fixture()
    for rep in original["repetitions"]:
        for context in rep["contexts"]:
            for row in context["configurations"].values(): row["evaluation"]["initial_action"]="DOWN"
    _,qstreams=analysis.original_statistics(original["repetitions"],analysis.policy_metrics,("total_regret",))
    _,cstreams=analysis.original_statistics(original["repetitions"],analysis.cost_metrics,analysis.COST_METRICS)
    actual=analysis.all_actual_costs(original["repetitions"])
    old_diagnostics={"model_restore_calls":5120,"new_physical_draws":0,"whole_endpoint_seconds":20.}
    older_diagnostics={"model_restore_calls":5120,"new_physical_draws":0,"whole_endpoint_seconds":15.}
    reference={"original_quality_streams":qstreams,"original_cost_streams":cstreams,"all_original_actual_configuration_costs":actual,
        "original_source_accounting":original["accounting"],"accounting":old_diagnostics,"source_diagnostic_accounting":older_diagnostics}
    plan=json.loads((ROOT/"reports/controlled_predictive_crossfit_plan_v38.json").read_text())
    repetitions=[]
    for rep in original["repetitions"]:
        contexts=[]
        for old in rep["contexts"]:
            identity=old["identity"]; arms={}
            for arm,seconds in (("POOLED",.0001),("CROSSFIT",.0021)):
                row={"source_valid":True,"readout_validation":{"passed":True},"evaluation_validation":{"passed":True},"policy_evaluation":deepcopy(old["configurations"]["CACHED32"]["evaluation"]),
                    "readout":{"root_action":"DOWN","root_values":{"DOWN":1.,"LEFT":.9},
                        "accounting":{"whole_readout_seconds":seconds,"seconds_by_stage":{"partition":seconds/2,"root_readout":seconds/2},
                            "partitioned_h1_rows":4 if arm=="CROSSFIT" else 0,"retained_draws_partitioned":1024 if arm=="CROSSFIT" else 0}},
                    "costs":{"postprocess_seconds":seconds}}
                if arm=="POOLED": row["value_reproduction_validation"]={"passed":True}
                arms[arm]=row
            contexts.append({"identity":identity,"arms":arms,"run_order":list(analysis.ARMS if (rep["replicate_index"]+identity["context_index"])%2==0 else reversed(analysis.ARMS)),
                **{key:{"passed":True} for key in ("source_validation","restoration_validation","proposal_validation","retained_result_validation")},
                "source_valid":True,"complete":True,"accounting":{"readout_calls_POOLED":1,"readout_calls_CROSSFIT":1},"original_CACHED32_costs":old["configurations"]["CACHED32"]["costs"]})
        repetitions.append({"replicate_index":rep["replicate_index"],"base_seed":rep["base_seed"],"contexts":contexts,"source_valid":True,"complete":True})
    return {"plan":plan,"repetitions":repetitions,"original_repetitions":original["repetitions"],
        "original_all_actual_configuration_costs":actual,"original_source_accounting":original["accounting"],
        "source_diagnostic_accounting":old_diagnostics,"prior_diagnostic_accounting":older_diagnostics,
        "plan_binding_validation":{"passed":True},"source_endpoint_stream_complete":True,"all_proposals_closed_before_oracle":True,
        "endpoint_evaluation_replanning_calls":0,"proposal_stream_complete":True,"oracle_used_for_policy_construction":False,
        "accounting":{"source_endpoint_stream_reads":1,"source_endpoint_triple_records_read":2560,"proposal_records_written":2560,"proposal_records_read":2560,
            "model_restore_calls":2560,"candidate_policy_evaluation_calls":2560,"baseline_policy_evaluation_calls":0,
            "readout_calls_by_arm":{"POOLED":2560,"CROSSFIT":2560},"postprocess_seconds_by_arm":{"POOLED":.256,"CROSSFIT":5.376},
            "model_restore_seconds":1000.,"candidate_policy_evaluation_seconds":500.,
            "historical_physical_batches":1128448,"historical_physical_draws":288882688,
            **{key:0 for key in ("new_provider_calls","new_sampling_calls","new_physical_batches","new_physical_draws")}}},reference


def test_complete_paired_full_policy_and_actual_postprocess_preserve_all_original_costs():
    payload,reference=fixture(); result=analysis.summarize(payload,reference)
    assert result["all_analysis_checks_passed"],{k:v for k,v in result["checks"].items() if not v["passed"]}
    assert result["source_valid_stream_count"]==result["quality_complete_stream_count"]==16
    delta=result["primary_postprocess_cost"]["CROSSFIT_minus_POOLED"]["postprocess_seconds"]
    assert delta["mean"]==pytest.approx(.002) and delta["count"]==16
    assert result["booked_original_query_plus_postprocess"]["arms"]["CROSSFIT"]["historical_query_plus_postprocess_seconds"]["mean"]==pytest.approx(1.2341)
    assert result["accounting"]["model_restore_seconds"]==1000. and result["accounting"]["candidate_policy_evaluation_seconds"]==500.
    assert result["all_actual_postprocess_costs"]["CROSSFIT"]["postprocess_seconds"]==pytest.approx(5.376)
    assert result["all_actual_postprocess_costs"]["CROSSFIT"]["readout_seconds_by_field"]["partition"]==pytest.approx(2.688)
    assert result["all_original_actual_configuration_costs"]==reference["all_original_actual_configuration_costs"]
    assert result["prior_diagnostic_accounting"]==reference["source_diagnostic_accounting"]
    assert result["accounting"]["new_physical_draws"]==0 and result["accounting"]["historical_physical_draws"]==288882688
    assert len(result["boards"])==16 and len(result["queries"])==10


def test_missing_candidate_policy_retains_missing_mass_and_cost_without_zero_imputation():
    payload,reference=fixture()
    for rep in payload["repetitions"]:
        context=rep["contexts"][0]; row=context["arms"]["CROSSFIT"]
        row["policy_evaluation"].update(policy_evaluable=False,v_pi=None,total_regret=None,continuation_regret=None,identities_pass=None,
            terminal_probability=.75,missing_probability=.25,first_action_regret=.1,defined_continuation_regret=.2)
        context["complete"]=False; rep["complete"]=False
    result=analysis.summarize(payload,reference)
    assert result["all_analysis_checks_passed"]
    assert result["quality_complete_stream_count"]==0 and result["source_valid_stream_count"]==result["diagnostic_valid_stream_count"]==16
    assert result["same_quality_mask_postprocess_cost"]["stream_count"]==0
    assert result["primary_postprocess_cost"]["stream_count"]==16
    assert result["continuous_diagnostics"]["arms"]["CROSSFIT"]["missing_probability"]["mean"]==pytest.approx(.25/160)
    assert result["coverage"]["CROSSFIT"]["policy_unavailable_count"]==16
    assert result["original_quality_complete_stream_count"]==result["original_source_cost_stream_count"]==16
    assert result["all_actual_postprocess_costs"]["CROSSFIT"]["attempt_count"]==2560
    assert result["all_original_actual_configuration_costs"]==reference["all_original_actual_configuration_costs"]


def test_source_failed_pair_remains_in_unconditional_fees_and_old_statistics():
    payload,reference=fixture(); rep=payload["repetitions"][0]; context=rep["contexts"][0]
    context["proposal_validation"]={"passed":False}; context["arms"]["CROSSFIT"]["source_valid"]=False
    context["source_valid"]=context["complete"]=False; rep["source_valid"]=rep["complete"]=False
    result=analysis.summarize(payload,reference)
    assert result["all_analysis_checks_passed"]
    assert result["quality_complete_stream_count"]==result["source_valid_stream_count"]==15
    assert result["original_quality_complete_stream_count"]==16 and result["original_source_cost_stream_count"]==16
    assert result["all_actual_postprocess_costs"]["CROSSFIT"]["postprocess_seconds"]==pytest.approx(5.376)
    assert result["all_original_actual_configuration_costs"]["GAP24"]["actual_run_count"]==2560
    assert len(result["incomplete_context_instances"])==1 and len(result["stream_statuses"])==16


def test_full_policy_error_and_root_error_counts_are_distinct():
    context={"identity":{"context_index":3,"board_index":0},"arms":{
        "POOLED":{"policy_evaluation":{**evaluation(),"initial_action":"LEFT"}},
        "CROSSFIT":{"policy_evaluation":{**evaluation(.2),"initial_action":"RIGHT","first_action_regret":0.,"continuation_regret":.2}}}}
    changes=analysis.policy_changes([context])
    assert changes["full_policy_new_error"]["context_instance_count"]==1
    assert changes["root_action_new_error"]["context_instance_count"]==0
    assert changes["root_action_changed"]["context_instance_count"]==1
    stats=analysis.points([context],analysis.quality,analysis.QUALITY)
    assert stats["CROSSFIT_minus_POOLED"]["total_regret"]["mean"]==.2
    assert stats["CROSSFIT_minus_POOLED"]["first_action_regret"]["mean"]==0


def test_stream_interval_averages_queries_boards_then_paired_original_histories():
    reps=[]
    for index in range(2):
        contexts=[]
        for board in range(16):
            for query in range(10):
                arms={arm:{"policy_evaluation":evaluation(1. if index==0 and board==0 and arm=="CROSSFIT" else .2 if index==1 and arm=="POOLED" else 0.)} for arm in analysis.ARMS}
                contexts.append({"identity":{"context_index":10*board+query,"board_index":board},"arms":arms})
        reps.append({"replicate_index":index,"base_seed":index+1,"contexts":contexts})
    stats,_=analysis.stream_statistics(reps,analysis.quality,analysis.QUALITY)
    delta=stats["CROSSFIT_minus_POOLED"]["total_regret"]
    assert delta["count"]==2 and delta["degrees_of_freedom"]==1
    assert delta["mean"]==pytest.approx((1/16-.2)/2) and delta["standard_error"]==pytest.approx((1/16+.2)/2)
