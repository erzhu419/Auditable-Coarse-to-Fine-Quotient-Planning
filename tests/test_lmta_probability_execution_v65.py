"""Paired online paths and paid partial blocks against frozen V61 execution."""
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

import networkx as nx
import pytest

from acfqp.science import lmta_probability_execution_v65 as candidate
from acfqp.science import lmta_trajectory_v61 as reference
from acfqp.science.lmta_probability_reuse_v64 import TERMINAL_COUNTERS


LIMITS = dict(max_planner_action_values=2000000,max_decisions=100000,max_wall_seconds=60.)


@pytest.fixture(scope='module',autouse=True)
def accounting(request):
    started,failures = perf_counter(),request.session.testsfailed
    data = dict(blocks=[],actual_planner_work=Counter(),actual_environment_work=Counter(),
                hand_graph_constructions=0)
    yield data
    target = Path(__file__).resolve().parents[1]/'reports/lmta_probability_execution_v65.simulation_checks.json'
    report = json.loads(target.read_text()) if target.exists() else {'attempts':[]}
    report['attempts'].append(dict(test_module='tests/test_lmta_probability_execution_v65.py',
        new_failures=request.session.testsfailed-failures,**data,sampled_graphs=0,learned_model_calls=0,
        full_policy_evaluations=0,wall_seconds=perf_counter()-started,
        scope='All hand-graph V61 reference, V65 baseline and V65 reuse complete/partial blocks. Planner and environment totals include reference work. No main graph or main trajectory runs.'))
    target.write_text(json.dumps(report,indent=2)+'\n')


def graph(accounting):
    accounting['hand_graph_constructions'] += 1
    result = nx.DiGraph()
    result.add_nodes_from(range(4))
    result.add_edges_from([(0,2),(1,2),(0,3),(1,3)])
    return result


def run(accounting,graph,variant,limits=LIMITS):
    if variant=='V61_REFERENCE':
        case,rows = reference.run_block(graph,-65,'LOOKAHEAD_2_ANALYTIC',2,2,3,limits)
    else:
        case,rows = candidate.run_block(graph,-65,variant,2,2,3,limits)
    accounting['blocks'].append(dict(label=variant,case=case))
    accounting['actual_planner_work'].update(case['decision_work'])
    accounting['actual_environment_work'].update(case['environment_work'])
    return case,rows


def stable(item,omit_work=False):
    if isinstance(item,dict):
        return {key:stable(value,omit_work) for key,value in item.items()
                if not key.endswith('_seconds') and key!='variant' and not (omit_work and key=='decision_work')}
    if isinstance(item,list):
        return [stable(value,omit_work) for value in item]
    return item


@pytest.fixture(scope='module')
def complete(accounting):
    hand = graph(accounting)
    return {variant:run(accounting,hand,variant) for variant in ('V61_REFERENCE','BASELINE','REUSE')}


def test_baseline_wrapper_preserves_frozen_execution_including_charged_work(complete):
    old_case,old_rows = complete['V61_REFERENCE']
    case,rows = complete['BASELINE']
    assert stable(case)==stable(old_case) and stable(rows)==stable(old_rows)
    assert case['variant']=='BASELINE' and case['method']=='LOOKAHEAD_2_ANALYTIC'
    assert case['completed_replicates']==2 and case['decision_records']==6
    assert case['environment_work']['environment_calls']==6
    assert case['environment_work']['rng_draws']==24
    assert candidate._propagate is reference._propagate


def test_reuse_follows_same_online_path_and_accounts_actual_probability_work(complete):
    old_case,old_rows = complete['BASELINE']
    case,rows = complete['REUSE']
    assert stable(case,True)==stable(old_case,True) and stable(rows,True)==stable(old_rows,True)
    assert all(row['variant']=='REUSE' and row['seed']==61000000-65000+row['replicate'] for row in rows)
    for old_trajectory,trajectory in zip(old_rows,rows):
        for old_decision,decision in zip(old_trajectory['decisions'],trajectory['decisions']):
            before,after = old_decision['decision_work'],decision['decision_work']
            assert {key:value for key,value in after.items() if key not in TERMINAL_COUNTERS
                    and key!='target_probability_evaluations'}=={
                        key:value for key,value in before.items() if key!='target_probability_evaluations'}
            assert after['target_probability_evaluations']==before['target_probability_evaluations']-before['analytic_probability_terms']+after['terminal_probability_cache_misses']
            assert after['terminal_probability_lookups']==after['terminal_probability_cache_hits']+after['terminal_probability_cache_misses']
    assert case['decision_work']['target_probability_evaluations']<old_case['decision_work']['target_probability_evaluations']


@pytest.mark.parametrize('variant',['BASELINE','REUSE'])
def test_soft_limit_retains_decision_without_environment_draw(variant,accounting):
    case,rows = run(accounting,graph(accounting),variant,{**LIMITS,'max_planner_action_values':1,'max_decisions':1})
    assert case['status']=='resource_limit' and case['stop_reason']=='max_planner_action_values'
    assert case['completed_replicates']==0 and case['decision_records']==case['decision_work']['planner_calls']==1
    assert case['decision_work']['action_value_evaluations']>=1
    assert len(rows)==1 and rows[0]['return'] is None
    decision = rows[0]['decisions'][0]
    assert decision['next_statuses'] is decision['reward'] is None
    assert decision['decision_work']==case['decision_work']
    assert not any(decision['environment_work'].values()) and not any(case['environment_work'].values())
