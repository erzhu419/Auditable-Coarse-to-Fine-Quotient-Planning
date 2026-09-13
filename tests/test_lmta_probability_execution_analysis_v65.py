"""Canonical independent checks, paired full cost, and incomplete cohort semantics."""
from collections import Counter
from copy import deepcopy
import importlib.util
from io import StringIO
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('probability_execution_analysis_v65',ROOT/'scripts/analyze_lmta_probability_execution_v65.py')
A=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(A)
WORK=Counter()


@pytest.fixture(scope='session',autouse=True)
def ledger():
    patch=pytest.MonkeyPatch();original=A.checker.verify_decision
    def counted(*args):
        result=original(*args);WORK.update(result['verification_work']);return result
    patch.setattr(A.checker,'verify_decision',counted)
    yield
    patch.undo()
    (ROOT/'reports/lmta_probability_execution_v65.analysis_checks.json').write_text(json.dumps(dict(
        schema='acfqp.lmta_probability_execution_analysis_checks.v65',development_work=dict(WORK,
            production_planner_calls=0,environment_calls=0,random_draws=0,new_generated_graphs=0,new_full_policy_evaluations=0,
            scope='Two-node hand queries checked independently plus synthetic cost and skipped-cohort records.')),indent=2)+'\n')


def hand_rows():
    work=dict.fromkeys(A.checker.COUNTERS,0)
    work.update(planner_calls=1,forced_choice=0,dp_states=1,action_value_evaluations=2,
        analytic_expectation_calls=2,analytic_probability_terms=2,target_probability_evaluations=2)
    decision=dict(statuses=[0,0],remaining_budget=1,remaining_days=1,selected=[0],planned_value=1.,
        root_action_values=[dict(selected=[0],value=1.),dict(selected=[1],value=1.)],decision_work=work,
        next_statuses=[2,0],reward=1)
    base=dict(graph_id=650000,method=A.METHOD,variant='BASELINE',replicate=0,status='complete',stop_reason=None,
        seed=711000000,decisions=[decision],**{'return':1})
    reuse=deepcopy(base);reuse['variant']='REUSE'
    reuse['decisions'][0]['decision_work'].update(dict.fromkeys(A.v64.TERMINAL,0))
    reuse['decisions'][0]['decision_work'].update(target_probability_evaluations=0,terminal_base_states=1,terminal_zero_source_terms=2)
    return [base,reuse],[dict(graph_id=650000,nodes=2,edges=[])]


def test_canonical_dedup_is_independent_and_bad_restored_count_has_no_certificate():
    rows,graphs=hand_rows();fees=Counter()
    certificates,result=A.certify(rows,graphs,StringIO(),fees)
    assert result['passed'] and fees['queries']==1 and result['independent_queries']==1
    identity=A.v61.key(dict(rows[0]['decisions'][0],graph_id=650000,method=A.METHOD))
    assert certificates['BASELINE'][identity]['decision_work']['target_probability_evaluations']==2
    assert certificates['REUSE'][identity]['decision_work']['target_probability_evaluations']==0
    rows[1]['decisions'][0]['decision_work']['target_probability_evaluations']=1
    certificates,result=A.certify([rows[1]],graphs,StringIO(),Counter())
    assert not result['passed'] and result['errors']['decision_work']==1
    assert not certificates['REUSE']


def test_valid_close_Q_change_is_preservation_failure_separate_from_integrity():
    rows,graphs=hand_rows()
    changed=rows[1]['decisions'][0]
    changed['root_action_values'][0]['value']-=1e-12
    changed['selected']=[1]
    certificates,checked=A.certify(rows,graphs,StringIO(),Counter())
    assert checked['passed'] and checked['distinct_result_differences']==1
    assert checked['independent_queries']==2 and all(certificates.values())
    pair=A.trajectory_preservation(rows)
    assert not pair['preserved'] and pair['errors']=={'exact_action_or_Q':1}
    assert rows[0]['return']==rows[1]['return']


def test_actual_cost_includes_overhead_and_has_both_order_strata():
    cases=[]
    for graph in A.IDS:
        for variant in A.VARIANTS:
            reuse=variant=='REUSE'
            cases.append(dict(graph_id=graph,variant=variant,prepare_gc_seconds=1.,wall_seconds=2. if reuse else 4.,
                cleanup_seconds=1.,serialization_seconds=4. if reuse else 1.,decision_total_seconds=3. if reuse else 5.))
    result=A.cost_summary(cases)
    assert result['full_cost_ratio']==pytest.approx(8/7)
    assert result['decision_cost_ratio']==pytest.approx(3/5)
    assert result['slower_graphs']==64 and result['faster_graphs']==result['tied_graphs']==0
    assert result['paired_geometric_ratio_95_interval']==pytest.approx([8/7,8/7])
    assert [s['graphs'] for s in result['order_strata']]==[32,32]
    assert all(s['ratio']==pytest.approx(8/7) for s in result['order_strata'])


def test_campaign_skip_keeps_all_graphs_and_nulls_quality_and_performance():
    order=[dict(graph_id=g,variant=v) for index,g in enumerate(A.IDS) for v in (A.VARIANTS if index%2==0 else A.VARIANTS[::-1])]
    manifest=dict(schema='acfqp.lmta_probability_execution.v65',status='complete',protocol=A.PROTOCOL,
        previous_source=A.PREVIOUS,cold_decisions=True,runtime={'gc_enabled':True},
        graphs=[dict(graph_id=g,nodes=15,stratum='sparse',expected_degree=1.5,p=1.5/14,edges=[]) for g in A.IDS],
        skipped_blocks=order,campaign_action_values=0,terminal_reason='campaign_resource_limit',
        campaign_stop_reason='max_wall_seconds',campaign_elapsed_at_stop=300.01,whole_runner_seconds=300.02,
        completed_blocks=0,successful_blocks=0,resource_limited_blocks=0,trajectory_records=0,completed_trajectories=0,
        decision_records=0,new_graphs=64,new_full_policy_evaluations=0,new_RL_updates=0,new_MCTS_calls=0,
        source_read_seconds=.1,source_snapshot_seconds=.1,graph_generation_seconds=.2,data_output_seconds=.01,unexecuted_prepare_gc_seconds=.01)
    previous=dict(integrity={'passed':True},action_and_value_preservation=True,complete_performance_evidence=True,
        timing={A.METHOD:{'ratio_median':.6}})
    checked=dict(passed=True,errors={},verification_work={},distinct_result_differences=0)
    result=A.summarize(manifest,[],[],{v:{} for v in A.VARIANTS},checked,previous)
    assert result['integrity']['passed'],result['integrity']
    assert not result['complete_trajectory_evidence'] and not result['complete_performance_evidence']
    assert result['quality'] is result['cost_comparison'] is result['action_and_trajectory_preservation'] is None
    assert len(result['skipped_blocks'])==128 and result['accounting']['missing_complete_trajectories']==4096
    assert result['accounting']['runner']['unexecuted_prepare_gc_seconds']==.01
    manifest['skipped_blocks']=order[1:]
    assert A.campaign_check(manifest,[])=={'skipped_suffix_roster':1}
