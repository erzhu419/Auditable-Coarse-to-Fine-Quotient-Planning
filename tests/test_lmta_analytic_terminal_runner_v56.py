"""Paid replay work and its separate weighting by the retained policy distribution."""
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('analytic_runner_v56_test',
    ROOT / 'scripts/run_lmta_analytic_terminal_v56.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@pytest.fixture(scope='module', autouse=True)
def accounting(request):
    start, work, calls = perf_counter(), Counter(), []
    original = runner.plan
    before_failures = request.session.testsfailed

    def tracked(*args, **kwargs):
        result = original(*args, **kwargs)
        work.update(result['counters'])
        calls.append(1)
        return result

    with patch.object(runner, 'plan', tracked):
        yield
    path = ROOT / 'reports/lmta_analytic_terminal_v56.runner_checks.json'
    report = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    report['attempts'].append(dict(test_module='tests/test_lmta_analytic_terminal_runner_v56.py',
        new_failures=request.session.testsfailed - before_failures, planner_calls=len(calls),
        all_planner_counters=dict(work), wall_seconds=perf_counter() - start,
        environment_samples=0, environment_calls=0, gradient_steps=0, new_full_policy_evaluations=0,
        scope='Hand-specified reference occupancy; all complete and intentionally limited replay work is charged.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


def fixture_data():
    graph = nx.DiGraph([(0, 2), (1, 2)])
    case = dict(graph_id=56001, nodes=3, stratum='hand', p=.5, budget=2, horizon=3)
    states = [((0, 0, 0), 2, 3, 1.), ((2, 0, 0), 1, 2, .5), ((2, 0, 1), 1, 2, .5),
              ((2, 2, 0), 0, 1, .25), ((2, 2, 1), 0, 1, .25), ((2, 2, 2), 0, 1, .5)]
    rows = [dict(statuses=list(s), remaining_budget=b, remaining_days=h, reach_probability=p)
            for s, b, h, p in states]
    return graph, case, rows


def test_complete_replay_keeps_order_and_weights_cost_without_claiming_policy_value():
    graph, old_case, old_rows = fixture_data()
    case, rows = runner.replay(graph, old_case, old_rows, runner.PROTOCOL['limits'])
    assert case['status'] == 'complete' and case['stop_reason'] is None
    assert [row['statuses'] for row in rows] == [row['statuses'] for row in old_rows]
    assert case['decision_work']['planner_calls'] == case['state_records'] == case['source_state_records'] == 6
    assert case['source_weighted_decision_work']['planner_calls'] == 3.
    for name, number in case['source_weighted_decision_work'].items():
        assert number == pytest.approx(math.fsum(new['decision_work'][name] * old['reach_probability']
                                               for new, old in zip(rows, old_rows)))
    assert case['source_weighted_decision_seconds'] == math.fsum(
        new['decision_seconds'] * old['reach_probability'] for new, old in zip(rows, old_rows))
    assert case['replay_seconds'] == pytest.approx(case['decision_seconds'] + case['replay_overhead_seconds'])
    assert 'root_value' not in case and all('value' not in row and 'reach_probability' not in row for row in rows)


def test_limit_is_checked_after_charging_a_full_decision_and_suppresses_full_weighting():
    graph, old_case, old_rows = fixture_data()
    limits = dict(runner.PROTOCOL['limits'], max_planner_action_values=1, max_policy_states=1)
    case, rows = runner.replay(graph, old_case, old_rows, limits)
    assert case['status'] == 'resource_limit' and case['stop_reason'] == 'max_planner_action_values'
    assert case['state_records'] == len(rows) == 1 and case['source_state_records'] == 6
    assert case['decision_work'] == rows[0]['decision_work']
    assert case['decision_work']['action_value_evaluations'] > 1
    assert case['decision_work']['analytic_expectation_calls'] > 0
    assert case['source_weighted_decision_work'] is None and case['source_weighted_decision_seconds'] is None
    assert rows[0]['selected'] == [0] and rows[0]['planned_value'] == 2.75
