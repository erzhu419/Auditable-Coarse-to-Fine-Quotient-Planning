"""Retained-query assembly and paired timing arithmetic without planner calls."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('probability_reuse_analysis_v64',ROOT/'scripts/analyze_lmta_probability_reuse_v64.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


@pytest.fixture(scope='session',autouse=True)
def ledger():
    yield
    path=ROOT/'reports/lmta_probability_reuse_v64.analysis_checks.json'
    path.write_text(json.dumps(dict(schema='acfqp.lmta_probability_reuse_analysis_checks.v64',development_work=dict(
        new_planner_calls=0,new_environment_calls=0,new_random_draws=0,new_generated_graphs=0,new_full_policy_evaluations=0,
        scope='Synthetic complete 12288-query/1536-block assembly, conditional failures, fee sums and occurrence order.')),indent=2)+'\n')


def fixture():
    source,queries,validation,timing = [],[],[],[]
    baseline = dict.fromkeys(A.LOGICAL,0)
    baseline.update(planner_calls=1,dp_states=1,action_value_evaluations=2,analytic_expectation_calls=2,
        analytic_probability_terms=2,target_probability_evaluations=2)
    candidate = dict(baseline,**dict.fromkeys(A.TERMINAL,0))
    candidate.update(target_probability_evaluations=1,terminal_probability_lookups=1,
        terminal_probability_cache_misses=1,terminal_zero_source_terms=1,terminal_base_states=1)
    for graph in A.IDS:
        for method in A.METHODS:
            old,new = [],[]
            for index in range(96):
                row=dict(graph_id=graph,method=method,query_index=index,statuses=[0,0],remaining_budget=1,
                    remaining_days=3,selected=[0],planned_value=1.,root_action_values=[dict(selected=[0],value=1.)],
                    decision_work=dict(baseline),decision_seconds=.01)
                old.append(row);new.append(dict(row,decision_work=dict(candidate)))
            source.extend(old);queries.extend(new)
            validation.append(dict(phase='validation',round=-1,graph_id=graph,method=method,variant='REUSE',position=0,
                status='complete',stop_reason=None,requested_queries=96,completed_queries=96,
                decision_work=A.sum_work(new),candidate_mismatch_count=0,comparison_errors={},decision_seconds=.96,
                loop_seconds=1.06,bookkeeping_seconds=.1,prepare_gc_seconds=.01,cleanup_seconds=.1,
                decision_total_seconds=1.06,block_seconds=1.16,serialization_seconds=.01,last_limit_check_seconds=1.))
    for round_id in range(6):
        for gi,graph in enumerate(A.IDS):
            for mi,method in enumerate(A.METHODS):
                for position,variant in enumerate(A.VARIANTS if (round_id+gi+mi)%2==0 else A.VARIANTS[::-1]):
                    duration=1.+gi if variant=='BASELINE' else 1.
                    timing.append(dict(validation[gi*2+mi],phase='timing',round=round_id,variant=variant,position=position,
                        decision_work={name:96*value for name,value in (baseline if variant=='BASELINE' else candidate).items()},
                        decision_seconds=duration,cleanup_seconds=.1*duration,decision_total_seconds=1.1*duration,
                        loop_seconds=duration+.1,bookkeeping_seconds=.1,block_seconds=1.1*duration+.1))
    graphs=[dict(graph_id=g) for g in A.IDS]
    manifest=dict(schema='acfqp.lmta_probability_reuse.v64',status='complete',protocol=A.PROTOCOL,
        previous_source=A.PREVIOUS,graphs=graphs,cold_decisions=True,runtime={'gc_enabled':True},
        validation_blocks=128,validation_queries=12288,timing_blocks=1536,timing_queries=147456,timing_dispatched=True,
        source_read_seconds=.1,graph_reconstruction_seconds=.1,data_output_seconds=.1,whole_runner_seconds=100.,
        new_graphs=0,new_environment_calls=0,new_environment_samples=0,new_RL_updates=0,new_MCTS_calls=0,new_full_policy_evaluations=0)
    warmup=dict(calls=[dict(variant=v,decision_work=dict(planner_calls=1,action_value_evaluations=2),decision_seconds=.01) for v in A.VARIANTS],
        prepare_gc_seconds=.01,cleanup_seconds=.01,wall_seconds=.03)
    return [manifest,validation,queries,timing,warmup,dict(status='complete',graphs=graphs),
        dict(integrity={'passed':True},complete_trajectory_evidence=True,cohort={'quality':{'retained_value':.48}}),source]


def test_complete_evidence_uses_ratio_of_sums_zero_work_and_separate_fees():
    result=A.summarize(*fixture())
    assert result['integrity']['passed'],result['integrity']
    assert result['action_and_value_preservation'] and result['complete_performance_evidence']
    method=result['timing'][A.METHODS[0]]
    assert method['ratio_median']==pytest.approx(1/32.5)
    assert method['ratio_minimum']==pytest.approx(method['ratio_maximum'])
    assert [s['paired_blocks'] for s in method['order_strata']]==[192,192]
    assert method['work']['BASELINE']['transition_outcomes']==0
    assert result['retained_V63_quality']=={'retained_value':.48}
    fees=result['accounting']['phase_work']
    assert fees['warmup']['planner_calls']==2 and fees['validation']['planner_calls']==12288
    assert fees['timing']['planner_calls']==147456
    assert fees['timing']['target_probability_evaluations']==221184


def test_output_failure_or_resource_prefix_disables_timing_and_value_reuse():
    inputs=fixture()
    inputs[0].update(timing_dispatched=False,timing_blocks=0,timing_queries=0)
    inputs[3],inputs[4]=[],None
    inputs[2][0]['selected']=[1]
    inputs[1][0].update(candidate_mismatch_count=1,comparison_errors={'retained_output_changed':1})
    result=A.summarize(*inputs)
    assert result['integrity']['passed'],result['integrity']
    assert not result['action_and_value_preservation'] and not result['complete_performance_evidence']
    assert result['timing'] is result['retained_V63_quality'] is None
    assert result['accounting']['phase_work']['validation']['planner_calls']==12288
    inputs=fixture()
    inputs[0].update(timing_dispatched=False,timing_blocks=0,timing_queries=0,validation_queries=12193)
    inputs[2]=inputs[2][:1]+inputs[2][96:]
    block=inputs[1][0]
    block.update(status='resource_limit',stop_reason='max_wall_seconds',completed_queries=1,
        decision_work=dict(inputs[2][0]['decision_work']),decision_seconds=.01,loop_seconds=60.01,
        bookkeeping_seconds=60.,decision_total_seconds=.11,block_seconds=60.11,last_limit_check_seconds=60.)
    inputs[3],inputs[4]=[],None
    result=A.summarize(*inputs)
    assert result['integrity']['passed'] and not result['action_and_value_preservation'],result['integrity']
    assert result['accounting']['validation_queries']==12193 and result['retained_V63_quality'] is None


def test_work_partition_and_recorded_block_sum_detect_actual_fee_errors():
    inputs=fixture()
    row=inputs[2][0]
    row['decision_work']['terminal_probability_cache_hits']=1
    checked=A.preserved_query(row,inputs[7][0])
    assert checked['errors']=={'probability_reuse_accounting':1}
    block=inputs[1][1]
    block['decision_work']['planner_calls']-=1
    assert A.block_check(block,inputs[2][96:192])['block_work_sum']==1
    block['decision_work']['planner_calls']+=1
    block['decision_total_seconds']+=1
    assert A.block_check(block,inputs[2][96:192])=={'block_time_partition':1}


def test_source_occurrences_keep_repeated_and_forced_queries_in_original_order():
    decision=dict(statuses=[0],remaining_budget=0,remaining_days=1,selected=[],planned_value=None,
        root_action_values=[],decision_work={'planner_calls':1,'forced_choice':1})
    trajectories=[dict(graph_id=630000,method=A.METHODS[0],replicate=rep,decisions=[deepcopy(decision)]) for rep in range(2)]
    rows=A.source_queries(trajectories)
    assert [r['query_index'] for r in rows]==[0,1]
    assert rows[0]['statuses']==rows[1]['statuses'] and len(rows)==2
    assert A.sum_work(rows)==dict(planner_calls=2,forced_choice=2)
