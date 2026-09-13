"""Observed-query certificates, including floating ties and corrupted records."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_analytic_short_v59 import plan


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('certificate_v62', ROOT / 'scripts/lmta_trajectory_certificate_v62.py')
certificate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(certificate)


@pytest.fixture(scope='module', autouse=True)
def accounting(request):
    started, failures = perf_counter(), request.session.testsfailed
    data = dict(planner_work=Counter(), verification_work=Counter(), hand_graphs=0, verification_calls=0)
    original_verify = certificate.verify_decision

    def verify(*args, **kwargs):
        result = original_verify(*args, **kwargs)
        data['verification_work'].update(result['verification_work'])
        data['verification_calls'] += 1
        return result

    with patch.object(certificate, 'verify_decision', verify):
        yield data
    target = ROOT / 'reports/lmta_trajectory_v62.certificate_checks.json'
    report = json.loads(target.read_text()) if target.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_trajectory_certificate_v62.py',
        new_failures=request.session.testsfailed - failures, actual_planner_work=dict(data['planner_work']),
        verification_work=dict(data['verification_work']), verification_calls=data['verification_calls'],
        hand_graph_constructions=data['hand_graphs'], sampled_graphs=0, environment_calls=0,
        random_draws=0, learned_model_calls=0, gradient_steps=0, wall_seconds=perf_counter() - started,
        scope='All production hand-query generation and independent verification calls, including corruption probes; no main graphs or complete policy evaluations.'))
    target.write_text(json.dumps(report, indent=2) + '\n')


def decision(accounting, edges, statuses, budget, days, depth):
    graph = nx.DiGraph()
    graph.add_nodes_from(range(len(statuses)))
    graph.add_edges_from(edges)
    accounting['hand_graphs'] += 1
    result = plan(graph, tuple(statuses), budget, days, depth)
    work = {'planner_calls': 1, **result['counters']}
    accounting['planner_work'].update(work)
    row = dict(statuses=statuses, remaining_budget=budget, remaining_days=days,
               selected=result['selected'], planned_value=result['planned_value'],
               root_action_values=result['root_action_values'], decision_work=work)
    return row, dict(nodes=len(statuses), edges=[list(edge) for edge in sorted(graph.edges())]), 'LOOKAHEAD_%s_ANALYTIC' % depth


@pytest.mark.parametrize('statuses,budget,days,depth', [
    ([0, 0, 0, 0], 2, 3, 1), ([0, 0, 0, 0], 2, 3, 2),
    ([2, 1, 0, 0], 1, 2, 2), ([0, 0, 0, 0], 0, 2, 2),
    ([2, 2, 0, 0], 2, 1, 2)])
def test_independent_values_and_work_match_cold_hand_queries(statuses, budget, days, depth, accounting):
    row, graph, method = decision(accounting, [(0, 2), (1, 2), (2, 3)], statuses, budget, days, depth)
    checked = certificate.verify_decision(row, graph, method)
    assert checked['passed'], checked
    assert checked['maximum_Q_difference'] <= 1e-10
    assert checked['expected_decision_work'] == row['decision_work']
    if row['decision_work']['forced_choice']:
        assert checked['verification_work']['independent_action_value_evaluations'] == 0


@pytest.fixture(scope='module')
def tied_query(accounting):
    return decision(accounting, [], [0, 0, 0], 1, 1, 1)


def test_computed_tie_uses_reported_strict_choice(tied_query):
    source, graph, method = tied_query
    row = deepcopy(source)
    row['root_action_values'][1]['value'] = math.nextafter(1., math.inf)
    row['planned_value'] = row['root_action_values'][1]['value']
    row['selected'] = [1]
    checked = certificate.verify_decision(row, graph, method)
    assert checked['passed'] and checked['maximum_Q_difference'] == math.ulp(1.)


@pytest.mark.parametrize('corruption,error', [('q', 'root_Q_value'), ('work', 'decision_work'),
                                             ('choice', 'reported_strict_max_lex_choice')])
def test_corrupted_value_work_or_reported_choice_fails(tied_query, corruption, error):
    source, graph, method = tied_query
    row = deepcopy(source)
    if corruption == 'q':
        row['root_action_values'][0]['value'] += .01
        row['planned_value'] = row['root_action_values'][0]['value']
    elif corruption == 'work':
        row['decision_work']['action_value_evaluations'] += 1
    else:
        row['selected'] = [1]
    checked = certificate.verify_decision(row, graph, method)
    assert not checked['passed'] and checked['errors'][error] == 1
