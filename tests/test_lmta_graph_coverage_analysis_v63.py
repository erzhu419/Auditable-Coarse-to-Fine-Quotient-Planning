"""64-by-32 assembly and global-budget prefix checks; no new planner tests."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('graph_coverage_analysis_v63',ROOT/'scripts/analyze_lmta_graph_coverage_v63.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
WORK = Counter()


@pytest.fixture(scope='session',autouse=True)
def ledger():
    yield
    path = ROOT/'reports/lmta_graph_coverage_v63.analysis_checks.json'
    path.write_text(json.dumps(dict(schema='acfqp.lmta_graph_coverage_analysis_checks.v63',development_work=dict(WORK,
        production_planner_calls=0,independent_planner_queries=0,environment_calls=0,random_draws=0,
        new_generated_graphs=0,new_full_policy_evaluations=0,
        scope='Synthetic 64-graph by 32-pair aggregation and campaign prefixes; one paid partial hand-record has no environment step.')),indent=2)+'\n')


def fixture():
    graphs = [dict(graph_id=g,nodes=15,stratum='sparse',expected_degree=1.5,p=1.5/14,edges=[]) for g in A.IDS]
    cases, rows, used = [], [], 0
    for index,g in enumerate(A.IDS):
        for method in (A.METHODS if index%2==0 else A.METHODS[::-1]):
            two = method==A.METHODS[1]
            work = dict(action_value_evaluations=64 if two else 32,
                transition_outcomes=32 if two else 0,target_probability_evaluations=96 if two else 64)
            cases.append(dict(graph_id=g,method=method,status='complete',stop_reason=None,stop_scope=None,
                nodes=15,budget=2,horizon=3,requested_replicates=32,completed_replicates=32,trajectory_records=32,
                decision_records=0,total_return=32*(2+int(two)*(index%2)),decision_work=work,
                environment_work={'environment_calls':0,'rng_draws':0},decision_seconds=.1,environment_seconds=0.,
                wall_seconds=.11,prepare_gc_seconds=.01,cleanup_seconds=.01,decision_total_seconds=.11,
                block_seconds=.12,serialization_seconds=.01,last_limit_check_seconds=.1,
                effective_limits=dict(A.BLOCK_LIMITS),campaign_actions_before=used,campaign_elapsed_before=1.+len(cases)*.1))
            used += work['action_value_evaluations']
            for rep in range(32):
                rows.append(dict(graph_id=g,method=method,replicate=rep,status='complete',decisions=[],
                    **{'return':2+int(two)*(index%2)}))
    manifest = dict(schema='acfqp.lmta_graph_coverage.v63',status='complete',protocol=A.PROTOCOL,
        previous_source=A.PREVIOUS,calibration_source=A.CALIBRATION,cold_decisions=True,runtime={'gc_enabled':True},
        graphs=graphs,skipped_blocks=[],campaign_action_values=used,terminal_reason='finished_roster',
        campaign_stop_reason=None,campaign_elapsed_at_stop=None,completed_blocks=128,successful_blocks=128,
        resource_limited_blocks=0,trajectory_records=4096,completed_trajectories=4096,decision_records=0,
        new_graphs=64,new_full_policy_evaluations=0,new_RL_updates=0,new_MCTS_calls=0,
        source_read_seconds=.1,graph_generation_seconds=.1,data_output_seconds=.1,whole_runner_seconds=20.,unexecuted_prepare_gc_seconds=0.)
    return manifest,cases,rows


def test_complete_64_by_32_assembly_and_both_graph_intervals(monkeypatch):
    # Isolate aggregation; existing frozen certificate/physics checks are not rerun here.
    monkeypatch.setattr(A,'block_check',lambda *args:dict(errors={},verification={}))
    manifest,cases,rows = fixture()
    previous = dict(integrity={'passed':True},panels=[dict(nodes=15,stratum='sparse',complete_quality_evidence=True,
        quality=dict(paired_two_minus_one=dict(mean=.38,graph_standard_error=.2,fixed_panel_mc_standard_error=.05)),
        costs={m:dict(decision_work={'action_value_evaluations':1000}) for m in A.METHODS})])
    result = A.summarize(manifest,cases,rows,{},dict(passed=True,errors={},verification_work={}),previous)
    assert result['integrity']['passed'] and result['complete_trajectory_evidence'],result['integrity']
    paired = result['cohort']['quality']['paired_two_minus_one']
    assert paired['mean']==.5 and paired['degrees_of_freedom']==63
    assert paired['graph_standard_error']==pytest.approx((16/63)**.5/8)
    assert paired['fixed_panel_mc_standard_error']==0.
    assert paired['graph_historical_four_comparison_interval'][0]<paired['graph_primary_95_interval'][0]<.5
    assert result['cohort']['costs'][A.METHODS[0]]['mean_trajectory_work']['transition_outcomes']==0.
    assert result['cohort']['two_over_one_work_ratios']['transition_outcomes'] is None
    assert result['descriptive_comparison']['action_value_work_ratio']==6144/2000
    assert result['accounting']['completed_trajectories']==4096 and result['accounting']['missing_complete_trajectories']==0


def test_block_limit_then_campaign_limit_keeps_suffix_and_all_charged_work():
    manifest,cases,rows = fixture(); cases=cases[:2]
    for index,case in enumerate(cases):
        case.update(status='resource_limit',stop_reason='max_planner_action_values',completed_replicates=0,
            stop_scope='block' if index==0 else 'campaign',campaign_actions_before=index*2000000)
        case['decision_work']['action_value_evaluations']=2000000+(5 if index else 0)
    manifest.update(terminal_reason='campaign_resource_limit',campaign_stop_reason='max_planner_action_values',
        campaign_elapsed_at_stop=10.,campaign_action_values=4000005,
        skipped_blocks=[dict(graph_id=c['graph_id'],method=c['method']) for c in fixture()[1][2:]])
    assert not A.campaign_check(manifest,cases)
    cohort=A.cohort_summary(cases,[],True)
    assert cohort['quality'] is None and len(cohort['graph_ids'])==64
    assert sum(c['decision_work']['action_value_evaluations'] for c in cohort['costs'].values())==4000005
    assert cohort['costs'][A.METHODS[1]]['mean_trajectory_work'] is None
    manifest['skipped_blocks']=manifest['skipped_blocks'][1:]
    assert A.campaign_check(manifest,cases)['skipped_suffix_roster']==1
    cases[0]['stop_scope']='campaign'
    assert A.campaign_check(manifest,cases)['stop_scope_or_continued_campaign']==1


def test_wall_boundary_before_dispatch_preserves_all_skipped_blocks():
    manifest,cases,_ = fixture()
    manifest.update(terminal_reason='campaign_resource_limit',campaign_stop_reason='max_wall_seconds',
        campaign_elapsed_at_stop=300.01,whole_runner_seconds=300.02,campaign_action_values=0,
        skipped_blocks=[dict(graph_id=c['graph_id'],method=c['method']) for c in cases],unexecuted_prepare_gc_seconds=.01)
    assert not A.campaign_check(manifest,[])
    manifest['campaign_elapsed_at_stop']=299.99
    assert A.campaign_check(manifest,[])['campaign_terminal']==1


def test_effective_limit_charges_partial_decision_without_environment():
    work=dict(planner_calls=1,action_value_evaluations=0,forced_choice=1)
    decision=dict(statuses=[0],remaining_budget=2,remaining_days=3,selected=[0],planned_value=None,root_action_values=[],
        decision_work=work,decision_seconds=.1,next_statuses=None,reward=None,environment_work=dict.fromkeys(A.v61.ENV,0),environment_seconds=0.)
    row=dict(graph_id=630000,method=A.METHODS[0],replicate=0,seed=691000000,status='resource_limit',
        stop_reason='max_decisions',decisions=[decision],**{'return':None})
    graph=dict(graph_id=630000,nodes=1,edges=[])
    case=dict(graph_id=630000,method=A.METHODS[0],nodes=1,budget=2,horizon=3,requested_replicates=32,
        status='resource_limit',stop_reason='max_decisions',trajectory_records=1,completed_replicates=0,total_return=0,
        decision_records=1,decision_work=work,environment_work=dict.fromkeys(A.v61.ENV,0),decision_seconds=.1,environment_seconds=0.,
        wall_seconds=.12,prepare_gc_seconds=.01,cleanup_seconds=.01,decision_total_seconds=.11,block_seconds=.13,
        serialization_seconds=.01,last_limit_check_seconds=.11,effective_limits=dict(A.BLOCK_LIMITS,max_decisions=1))
    certificates={A.v61.key(dict(decision,graph_id=630000,method=A.METHODS[0])):deepcopy(decision)}
    result=A.block_check(case,[row],graph,certificates)
    WORK.update(result['verification'])
    assert not result['errors'],result
    assert result['verification']['certificate_queries']==1
    assert result['verification'].get('verification_random_draws',0)==0
