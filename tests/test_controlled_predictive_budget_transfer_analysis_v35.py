from copy import deepcopy
from itertools import permutations
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import analyze_controlled_predictive_budget_transfer_v35 as analysis
from test_controlled_predictive_transfer_analysis_v32 import fixture as source_fixture
from test_controlled_predictive_new_starts_analysis_v28 import evaluation


def fixture():
    source=source_fixture()
    plan=json.loads((ROOT/"reports/controlled_predictive_budget_transfer_plan_v35.json").read_text())
    prefixes=deepcopy(source["prefixes"])
    for prefix,board in zip(prefixes,plan["boards"]): prefix.update(name=board["name"],prefix_seed=board["prefix_seed"])
    preparations=deepcopy(source["query_preparations"])
    for row,context in zip(preparations,plan["contexts"]): row["identity"]={key:context[key] for key in analysis.IDENTITY_FIELDS}
    orders=list(permutations(analysis.CONFIGURATIONS)); repetitions=[]
    for original,rep in zip(source["repetitions"],plan["replicates"]):
        contexts=[]
        for old,fixed in zip(original["contexts"],plan["contexts"]):
            configurations={}
            for configuration in plan["configurations"]:
                row=deepcopy(old["arms"]["CACHED"]); budget=configuration["budget"]
                seconds=budget/1000*(1.02 if configuration["name"]=="GAP24" else 1.)
                row["configuration"]=configuration
                row["local"].update(arm=configuration["arm"],requested_batch_count=budget,completed_batches=budget,
                    initial_batches=32,final_batches=32+budget,actual_draws=256*budget)
                row["local"]["provider_counts"]={"row_requests":budget,"physical_draws":256*budget,"first_batch_requests":0,"repeat_batch_requests":budget}
                row["local"]["accounting"]={"whole_run_seconds":seconds,"seconds_by_stage":{"local_work":seconds},"work_counts":{"batches":budget}}
                row["costs"]={"prefix_sampling_seconds":1.,"single_query_prepare_seconds":.2,"local_whole_run_seconds":seconds,"independent_query_seconds":1.2+seconds}
                configurations[configuration["name"]]=row
            contexts.append({"identity":{key:fixed[key] for key in analysis.IDENTITY_FIELDS},"target_key":fixed["target_key"],
                "run_order":list(orders[(rep["replicate_index"]*160+fixed["context_index"])%6]),"configurations":configurations,
                "source_valid":True,"fixed_budget_complete":True,"complete":True})
        repetitions.append({**rep,"contexts":contexts,"source_valid":True,"complete":True})
    providers={configuration["name"]:{"row_requests":2560*configuration["budget"],"physical_draws":2560*configuration["budget"]*256,
        "first_batch_requests":0,"repeat_batch_requests":2560*configuration["budget"]} for configuration in plan["configurations"]}
    return {"plan":plan,"repetitions":repetitions,"prefixes":prefixes,"query_preparations":preparations,
        "plan_binding_validation":{"passed":True},"cohort_binding_validation":{"passed":True},
        "all_prefix_snapshots_closed_before_local":True,"all_sampling_endpoints_closed_before_oracle":True,"endpoint_evaluation_replanning_calls":0,
        "original_source_accounting":{"historical_physical_batches":492544,"historical_physical_draws":126091264,
            "total_physical_batches":430592,"total_physical_draws":110231552},
        "accounting":{"prefix_board_count":16,"prepared_query_count":160,"prefix_physical_batches":512,"prefix_physical_draws":131072,
            "prefix_acquisition_seconds":16.,"single_query_preparation_seconds":32.,"local_configuration_run_count":7680,
            "local_physical_batches":204800,"local_physical_draws":52428800,"total_physical_batches":205312,"total_physical_draws":52559872,
            "local_allocation_wall_seconds":2560*(.02448+.024+.032),"provider_counts_by_configuration":providers,
            "historical_physical_batches":923136,"historical_physical_draws":236322816,
            "historical_plus_new_physical_batches":1128448,"historical_plus_new_physical_draws":288882688,
            "endpoint_triple_records_written":2560,"endpoint_triple_records_reloaded":2560}}


def test_own_unequal_budgets_are_complete_and_all_three_comparisons_and_fees_remain():
    result=analysis.summarize(fixture())
    assert result["all_analysis_checks_passed"]
    assert result["quality_complete_stream_count"]==result["source_valid_stream_count"]==16
    assert set(result["primary_quality"]["comparisons"])=={"GAP24_minus_CACHED32","GAP24_minus_CACHED24","CACHED24_minus_CACHED32"}
    costs=result["primary_independent_query_cost"]["comparisons"]
    assert costs["GAP24_minus_CACHED32"]["independent_query_seconds"]["mean"]==pytest.approx(-.00752)
    assert costs["GAP24_minus_CACHED24"]["independent_query_seconds"]["mean"]==pytest.approx(.00048)
    assert costs["CACHED24_minus_CACHED32"]["independent_query_seconds"]["mean"]==pytest.approx(-.008)
    assert result["accounting"]["total_physical_draws"]==52559872 and result["accounting"]["historical_plus_new_physical_draws"]==288882688
    assert result["all_actual_configuration_costs"]["CACHED24"]["attributed_cost_totals"]["prefix_sampling_seconds"]==2560
    assert result["accounting"]["prefix_acquisition_seconds"]==16.
    assert len(result["boards"])==16 and len(result["queries"])==10


def test_three_pair_statistics_average_queries_boards_then_independent_suffix_streams():
    payload=fixture()
    for context in payload["repetitions"][0]["contexts"]:
        if context["identity"]["board_index"]==0:
            context["configurations"]["GAP24"]["evaluation"]={**evaluation(1.),"initial_action":"UP"}
            context["configurations"]["CACHED24"]["evaluation"]={**evaluation(.5),"initial_action":"UP"}
    for context in payload["repetitions"][1]["contexts"]:
        context["configurations"]["CACHED32"]["evaluation"]={**evaluation(.2),"initial_action":"UP"}
    stats,_=analysis.stream_statistics(payload["repetitions"][:2],analysis.policy_metrics,("total_regret",))
    main=stats["comparisons"]["GAP24_minus_CACHED32"]["total_regret"]
    assert main["count"]==2 and main["degrees_of_freedom"]==1
    assert main["mean"]==pytest.approx((1/16-.2)/2) and main["standard_error"]==pytest.approx((1/16+.2)/2)
    assert stats["comparisons"]["GAP24_minus_CACHED24"]["total_regret"]["mean"]==pytest.approx(.5/16/2)
    assert stats["comparisons"]["CACHED24_minus_CACHED32"]["total_regret"]["mean"]==pytest.approx((.5/16-.2)/2)


def test_normal_early_stop_is_source_valid_but_not_own_budget_complete_and_has_actual_fees():
    payload=fixture(); rep=payload["repetitions"][0]; context=rep["contexts"][0]; row=context["configurations"]["GAP24"]
    row["completed_requested_budget"]=False
    row["local"].update(completed_batches=23,final_batches=55,actual_draws=5888,completed_fixed_budget=False,stop_reason="NO_ELIGIBLE_CANDIDATE")
    row["local"]["provider_counts"].update(row_requests=23,physical_draws=5888,repeat_batch_requests=23)
    context.update(fixed_budget_complete=False,complete=False); rep["complete"]=False
    a=payload["accounting"]; provider=a["provider_counts_by_configuration"]["GAP24"]
    for key in ("row_requests","repeat_batch_requests"): provider[key]-=1
    provider["physical_draws"]-=256
    for key in ("local_physical_batches","total_physical_batches","historical_plus_new_physical_batches"): a[key]-=1
    for key in ("local_physical_draws","total_physical_draws","historical_plus_new_physical_draws"): a[key]-=256
    result=analysis.summarize(payload)
    assert result["all_analysis_checks_passed"]
    assert result["quality_complete_stream_count"]==15 and result["source_valid_stream_count"]==16
    assert result["same_quality_mask_cost"]["stream_count"]==15 and result["primary_independent_query_cost"]["stream_count"]==16
    assert result["accounting"]["total_physical_draws"]==52559872-256
    assert result["accounting"]["historical_physical_draws"]==236322816
    assert result["all_actual_configuration_costs"]["GAP24"]["actual_run_count"]==2560


def test_missing_policy_keeps_source_cost_and_diagnostics_without_imputing_quality():
    payload=fixture()
    for rep in payload["repetitions"]:
        context=rep["contexts"][0]
        context["configurations"]["CACHED32"]["evaluation"].update(policy_evaluable=False,v_pi=None,total_regret=None,continuation_regret=None,
            identities_pass=None,missing_probability=.25,terminal_probability=.75,first_action_regret=.1,defined_continuation_regret=.2)
        context["complete"]=False; rep["complete"]=False
    result=analysis.summarize(payload)
    assert result["all_analysis_checks_passed"]
    assert result["quality_complete_stream_count"]==0 and result["source_valid_stream_count"]==result["diagnostic_valid_stream_count"]==16
    assert result["same_quality_mask_cost"]["stream_count"]==0
    assert result["continuous_diagnostics"]["configurations"]["CACHED32"]["defined_regret_lower_bound"]["mean"]==pytest.approx(.3/160)
    assert result["all_actual_configuration_costs"]["CACHED32"]["provider_counts"]["physical_draws"]==20971520
    assert result["original_source_accounting"]==payload["original_source_accounting"]
