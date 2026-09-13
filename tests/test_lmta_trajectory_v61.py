"""Check synchronous propagation, paired streams, frozen decisions and paid stops."""
from collections import Counter
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science import lmta_trajectory_v61 as candidate


LIMITS = dict(max_planner_action_values=2000000, max_decisions=100000, max_wall_seconds=60.)
ONE, TWO = candidate.DEPTHS


@pytest.fixture(scope='module', autouse=True)
def accounting(request):
    started, failures = perf_counter(), request.session.testsfailed
    data = dict(planner_work=Counter(), environment_work=Counter(), blocks=[], hand_graphs=0)
    original_plan, original_propagate, original_run = candidate.plan, candidate._propagate, candidate.run_block

    def planned(*args, **kwargs):
        result = original_plan(*args, **kwargs)
        data['planner_work'].update({'planner_calls': 1, **result['counters']})
        return result

    def propagated(*args, **kwargs):
        result = original_propagate(*args, **kwargs)
        data['environment_work'].update(result[2])
        return result

    def run(*args, **kwargs):
        case, rows = original_run(*args, **kwargs)
        data['blocks'].append(case)
        return case, rows

    with patch.object(candidate, 'plan', planned), patch.object(candidate, '_propagate', propagated), \
         patch.object(candidate, 'run_block', run):
        yield data
    target = Path(__file__).resolve().parents[1] / 'reports/lmta_trajectory_v61.simulation_checks.json'
    report = json.loads(target.read_text()) if target.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_trajectory_v61.py',
        new_failures=request.session.testsfailed - failures,
        actual_planner_work=dict(data['planner_work']), fixture_environment_work=dict(data['environment_work']),
        blocks=data['blocks'], hand_graph_constructions=data['hand_graphs'],
        sampled_graphs=0, learned_model_calls=0, gradient_steps=0,
        wall_seconds=perf_counter() - started,
        scope='Includes simulator calls and extra frozen-planner verification calls. Environment work includes hand propagation with deterministic uniforms and seeded trajectory draws. No main graph or main trajectory is run.'))
    target.write_text(json.dumps(report, indent=2) + '\n')


def graph(accounting, edges, nodes=4):
    accounting['hand_graphs'] += 1
    result = nx.DiGraph()
    result.add_nodes_from(range(nodes))
    result.add_edges_from(edges)
    return result


class Uniforms:
    def __init__(self, values):
        self.values = iter(values)
        self.draws = 0

    def random(self):
        self.draws += 1
        return next(self.values)


def test_synchronous_propagation_charges_unused_and_redundant_edges(accounting):
    g = graph(accounting, [(0, 2), (1, 2), (2, 3)])
    rng = Uniforms([.1, .2, .0])
    after, reward, work = candidate._propagate([1, 0, 0, 0], [1], sorted(g.edges()), dict(g.in_degree()), rng)
    assert after == [2, 2, 1, 0] and reward == 2
    assert work == dict(environment_calls=1, rng_draws=3, eligible_edge_attempts=2,
                        successful_edge_attempts=2, seeded_nodes=1, activated_targets=1)
    assert rng.draws == 3
    after, reward, work = candidate._propagate(after, [], sorted(g.edges()), dict(g.in_degree()), Uniforms([.9, .9, .9]))
    assert after == [2, 2, 2, 1] and reward == 1
    assert work['eligible_edge_attempts'] == work['successful_edge_attempts'] == 1


def stable(value):
    if isinstance(value, dict):
        return {key: stable(item) for key, item in value.items() if not key.endswith('_seconds')}
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


def test_pairing_does_not_depend_on_policy_execution_order(accounting):
    g = graph(accounting, [(0, 2), (1, 2), (2, 3)])
    forward = {method: candidate.run_block(g, -61, method, 1, 2, 3, LIMITS) for method in (ONE, TWO)}
    reverse = {method: candidate.run_block(g, -61, method, 1, 2, 3, LIMITS) for method in (TWO, ONE)}
    for method in (ONE, TWO):
        assert stable(forward[method][0]) == stable(reverse[method][0])
        assert stable(forward[method][1]) == stable(reverse[method][1])
        case, rows = forward[method]
        assert rows[0]['seed'] == 61000000 - 61000
        assert case['environment_work']['rng_draws'] == 9
        assert case['environment_work']['environment_calls'] == 3
        assert case['decision_records'] == 3


def test_recorded_path_uses_frozen_planner_and_hand_rewards(accounting):
    g = graph(accounting, [(0, 1), (1, 2)], nodes=3)
    case, rows = candidate.run_block(g, -62, ONE, 1, 2, 3, LIMITS)
    decisions = rows[0]['decisions']
    assert case['status'] == 'complete' and rows[0]['return'] == 3
    assert [row['statuses'] for row in decisions] == [[0, 0, 0], [2, 1, 0], [2, 2, 2]]
    assert [row['selected'] for row in decisions] == [[0], [2], []]
    assert [row['reward'] for row in decisions] == [2, 1, 0]
    for row in decisions:
        frozen = candidate.plan(g, tuple(row['statuses']), row['remaining_budget'], row['remaining_days'], 1)
        assert row['selected'] == frozen['selected']
        assert row['root_action_values'] == frozen['root_action_values']
        assert row['decision_work'] == {'planner_calls': 1, **frozen['counters']}


@pytest.mark.parametrize('overrides, reason', [
    ({'max_planner_action_values': 1, 'max_decisions': 1, 'max_wall_seconds': 0.}, 'max_planner_action_values'),
    ({'max_decisions': 1, 'max_wall_seconds': 0.}, 'max_decisions'),
    ({'max_wall_seconds': 0.}, 'max_wall_seconds')])
def test_limit_retains_paid_decision_before_drawing_environment(overrides, reason, accounting):
    g = graph(accounting, [(0, 2), (1, 2)], nodes=3)
    case, rows = candidate.run_block(g, -63, ONE, 2, 2, 3, {**LIMITS, **overrides})
    assert case['status'] == rows[0]['status'] == 'resource_limit'
    assert case['stop_reason'] == rows[0]['stop_reason'] == reason
    assert case['completed_replicates'] == 0 and case['trajectory_records'] == 1
    assert case['decision_records'] == case['decision_work']['planner_calls'] == 1
    assert case['decision_work']['action_value_evaluations'] == 3
    row = rows[0]['decisions'][0]
    assert rows[0]['return'] is row['next_statuses'] is row['reward'] is None
    assert not any(case['environment_work'].values())
    assert row['decision_work'] == case['decision_work']


def test_rng_draws_follow_decision_and_future_is_not_planner_input(accounting, monkeypatch):
    g = graph(accounting, [(0, 1)], nodes=2)
    events = []
    original_plan = candidate.plan

    class CausalRandom:
        def __init__(self, seed):
            self.seed = seed

        def random(self):
            assert events[-1] == 'decision'
            events.append('draw')
            return .5

    def plan(given_graph, statuses, b, h, depth):
        assert given_graph is g and isinstance(statuses, tuple)
        events.append('decision')
        return original_plan(given_graph, statuses, b, h, depth)

    monkeypatch.setattr(candidate.random, 'Random', CausalRandom)
    monkeypatch.setattr(candidate, 'plan', plan)
    case, _ = candidate.run_block(g, -64, ONE, 1, 2, 3, LIMITS)
    assert events == ['decision', 'draw'] * 3
    assert case['environment_work']['rng_draws'] == 3
