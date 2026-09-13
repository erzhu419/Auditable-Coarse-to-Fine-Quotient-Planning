"""Bitwise frozen-query equality and actual terminal reuse on hand graphs."""
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

import networkx as nx
import pytest

from acfqp.science import lmta_probability_reuse_v64 as candidate
from acfqp.science.lmta_analytic_short_v59 import plan as frozen


@pytest.fixture(scope='module', autouse=True)
def accounting(request):
    started, failures = perf_counter(), request.session.testsfailed
    data = dict(candidate_work=Counter(), frozen_work=Counter(),
                candidate_planner_calls=0, frozen_planner_calls=0, hand_graph_constructions=0)
    yield data
    target = Path(__file__).resolve().parents[1]/'reports/lmta_probability_reuse_v64.planner_checks.json'
    report = json.loads(target.read_text()) if target.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_probability_reuse_v64.py',
        new_failures=request.session.testsfailed-failures, **data,
        environment_calls=0, random_draws=0, sampled_graphs=0, learned_model_calls=0,
        wall_seconds=perf_counter()-started,
        scope='All cold candidate and V59 reference hand-query calls; no main graph, trajectory, or full-policy evaluation.'))
    target.write_text(json.dumps(report,indent=2)+'\n')


def pair(accounting, edges, statuses, budget, days, depth):
    graph = nx.DiGraph()
    graph.add_nodes_from(range(len(statuses)))
    graph.add_edges_from(edges)
    accounting['hand_graph_constructions'] += 1
    old = frozen(graph, tuple(statuses), budget, days, depth)
    new = candidate.plan(graph, tuple(statuses), budget, days, depth)
    for label, result in [('frozen',old),('candidate',new)]:
        accounting[label+'_planner_calls'] += 1
        accounting[label+'_work'].update(result['counters'])
    assert old['selected']==new['selected']
    assert old['planned_value']==new['planned_value']
    assert old['root_action_values']==new['root_action_values']
    if old['planned_value'] is not None:
        assert old['planned_value'].hex()==new['planned_value'].hex()
    for before, after in zip(old['root_action_values'],new['root_action_values']):
        assert before['value'].hex()==after['value'].hex()
    for name, value in old['counters'].items():
        if name!='target_probability_evaluations':
            assert value==new['counters'][name], name
    work = new['counters']
    assert work['terminal_probability_lookups']==work['terminal_probability_cache_hits']+work['terminal_probability_cache_misses']
    assert work['analytic_probability_terms']==work['terminal_probability_lookups']+work['terminal_zero_source_terms']
    assert work['target_probability_evaluations']==(old['counters']['target_probability_evaluations']
        -old['counters']['analytic_probability_terms']+work['terminal_probability_cache_misses'])
    return old,new


@pytest.mark.parametrize('statuses,budget,days,depth', [
    ([0,0,0,0,0],2,3,1),([0,0,0,0,0],2,3,2),
    ([2,1,0,0,0],1,2,2),([1,1,0,0,0],2,1,1)])
def test_search_and_float_bits_match_supported_hand_queries(statuses,budget,days,depth,accounting):
    pair(accounting,[(0,2),(1,2),(0,3),(1,3),(2,4),(3,4)],statuses,budget,days,depth)


def test_terminal_reuse_charges_base_scan_updates_and_cached_powers(accounting):
    old,new = pair(accounting,[(0,2),(1,2),(0,3),(1,3)],[0,0,0,0],2,3,1)
    work = new['counters']
    assert work['terminal_base_states']==1 and work['terminal_base_parent_checks']==4
    assert work['terminal_selected_edge_checks']==work['terminal_selected_increments']==4
    assert work['terminal_probability_lookups']==4
    assert work['terminal_probability_cache_hits']==3 and work['terminal_probability_cache_misses']==1
    assert work['terminal_zero_source_terms']==8
    assert work['target_probability_evaluations']==1 < old['counters']['target_probability_evaluations']==12


def test_zero_source_indegree_zero_never_divides_or_populates_probability_cache(accounting):
    _,new = pair(accounting,[],[0,0,0],2,3,1)
    work = new['counters']
    assert work['terminal_zero_source_terms']==6
    assert work['terminal_probability_lookups']==work['terminal_probability_cache_misses']==0
    assert work['terminal_base_parent_checks']==work['terminal_selected_edge_checks']==0
    assert new['selected']==[0]


@pytest.mark.parametrize('statuses,budget,days', [([0,0,0],0,3),([2,0,0],2,1)])
def test_forced_root_does_not_do_terminal_reuse_work(statuses,budget,days,accounting):
    _,new = pair(accounting,[(0,1),(1,2)],statuses,budget,days,2)
    assert new['counters']['forced_choice']==1
    assert all(new['counters'][name]==0 for name in candidate.TERMINAL_COUNTERS)


def test_each_cold_call_rebuilds_its_probability_cache(accounting):
    edges,statuses = [(0,2),(1,2),(0,3),(1,3)],[0,0,0,0]
    _,first = pair(accounting,edges,statuses,2,3,1)
    _,second = pair(accounting,edges,statuses,2,3,1)
    assert first==second
    assert first['counters']['terminal_probability_cache_misses']==second['counters']['terminal_probability_cache_misses']==1
