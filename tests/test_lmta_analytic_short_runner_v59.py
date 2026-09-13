"""Compact source selection and charged short-window replay without model calls."""
import importlib.util
from itertools import count
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('analytic_short_runner_v59_test',
    Path(__file__).resolve().parents[1] / 'scripts/run_lmta_analytic_short_v59.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_source_loader_excludes_full_method_and_large_reference_Q(tmp_path):
    common = dict(graph_id=580000, statuses=[0, 0, 0], remaining_budget=2,
        remaining_days=3, reach_probability=1., root_action_values=[{'value': 2.75}])
    rows = [dict(common, method=method) for method in [*runner.SOURCE_METHODS, 'LOOKAHEAD_FULL_ANALYTIC']]
    rows.append(dict(common, graph_id=550000, method='LOOKAHEAD_1'))
    (tmp_path / 'states.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    queries = runner.read_queries(tmp_path, {580000})
    assert set(queries) == {(580000, 'LOOKAHEAD_1'), (580000, 'LOOKAHEAD_2')}
    for values in queries.values():
        assert len(values) == 1
        assert values[0] == {key: common[key] for key in (
            'statuses', 'remaining_budget', 'remaining_days', 'reach_probability')}


def references(method):
    case = dict(graph_id=580000, nodes=3, stratum='hand', p=.5, budget=2, horizon=3, method=method)
    rows = [dict(statuses=[0, 0, 0], remaining_budget=2, remaining_days=3, reach_probability=1.),
            dict(statuses=[2, 0, 0], remaining_budget=1, remaining_days=2, reach_probability=.5)]
    return case, rows


def install_fake_planner(monkeypatch, calls):
    def planned(graph, statuses, budget, days, depth):
        calls.append((statuses, budget, days, depth))
        return dict(selected=[1], planned_value=1., root_action_values=[dict(selected=[1], value=1.)],
                    counters=dict(action_value_evaluations=2, analytic_expectation_calls=2))
    monkeypatch.setattr(runner, 'plan', planned)
    ticks = count(0.)
    monkeypatch.setattr(runner, 'perf_counter', lambda: next(ticks))


@pytest.mark.parametrize('method,depth', [('LOOKAHEAD_1', 1), ('LOOKAHEAD_2', 2)])
def test_complete_replay_routes_depth_and_weights_each_original_query(method, depth, monkeypatch):
    calls = []
    install_fake_planner(monkeypatch, calls)
    source, old = references(method)
    case, rows = runner.replay(None, source, old, runner.PROTOCOL['limits'])
    assert calls == [((0, 0, 0), 2, 3, depth), ((2, 0, 0), 1, 2, depth)]
    assert case['method'] == method + '_ANALYTIC' and case['source_method'] == method
    assert all(row['method'] == case['method'] for row in rows)
    assert case['state_records'] == case['source_state_records'] == 2
    assert case['status'] == 'complete' and case['stop_reason'] is None
    assert case['decision_work']['action_value_evaluations'] == 4
    assert case['source_weighted_decision_work']['action_value_evaluations'] == 3.
    assert case['decision_seconds'] == 2. and case['source_weighted_decision_seconds'] == 1.5
    assert case['replay_seconds'] == case['decision_seconds'] + case['replay_overhead_seconds']


def test_limited_replay_keeps_paid_prefix_and_suppresses_full_weighted_cost(monkeypatch):
    calls = []
    install_fake_planner(monkeypatch, calls)
    source, old = references('LOOKAHEAD_2')
    limits = {**runner.PROTOCOL['limits'], 'max_planner_action_values': 2, 'max_policy_states': 1}
    case, rows = runner.replay(None, source, old, limits)
    assert len(calls) == len(rows) == case['state_records'] == 1
    assert case['source_state_records'] == 2 and case['status'] == 'resource_limit'
    assert case['stop_reason'] == 'max_planner_action_values'
    assert case['decision_work']['action_value_evaluations'] == 2 and case['decision_seconds'] == 1.
    assert rows[0]['selected'] == [1] and rows[0]['planned_value'] == 1.
    assert case['source_weighted_decision_work'] is None and case['source_weighted_decision_seconds'] is None
