"""Fresh-policy values and charged partial work on hand-computed graphs."""
from collections import Counter
from itertools import count
import json
import math
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_exact_v52 import ExactAIMSolver
from acfqp.science import lmta_scale_v54 as scale


LIMITS = dict(max_planner_action_values=2_000_000, max_policy_states=100_000,
              max_wall_seconds=60.)


@pytest.fixture(scope='module', autouse=True)
def development_accounting(request):
    started = perf_counter()
    work = dict(solvers=[], planner_calls=0, evaluations=[])
    original_init = ExactAIMSolver.__init__
    original_plan = scale.plan
    original_evaluate = scale.evaluate
    before_failures = request.session.testsfailed

    def initialize(solver, *args, **kwargs):
        original_init(solver, *args, **kwargs)
        work['solvers'].append(solver)

    def planned(*args, **kwargs):
        work['planner_calls'] += 1
        return original_plan(*args, **kwargs)

    def evaluated(*args, **kwargs):
        tick = perf_counter()
        result = original_evaluate(*args, **kwargs)
        case, rows = result
        work['evaluations'].append(dict(method=case['method'], status=case['status'],
            stop_reason=case['stop_reason'], state_records=len(rows),
            evaluation_work=case['evaluation_work'], actual_test_seconds=perf_counter() - tick))
        return result

    with patch.object(ExactAIMSolver, '__init__', initialize), \
         patch.object(scale, 'plan', planned), patch.object(scale, 'evaluate', evaluated):
        yield
    totals = Counter()
    for solver in work['solvers']:
        totals.update(solver.counters)
    path = Path(__file__).resolve().parents[1] / 'reports/lmta_scale_v54.development_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_scale_v54.py',
        new_failures=request.session.testsfailed - before_failures,
        environment_counters={}, model_evaluations=0, gradient_steps=0,
        planner_calls=work['planner_calls'], solver_instances=len(work['solvers']),
        all_solver_counters=dict(totals), outer_evaluations=work['evaluations'],
        wall_seconds=perf_counter() - started,
        scope='All hand-graph work, including resource-limited attempts, is charged. The clock-limit case uses mocked ledger times; actual_test_seconds and this wall_seconds use the real clock. No environments or main panel.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


def double_parent_graph():
    graph = nx.DiGraph()
    graph.add_nodes_from(range(3))
    graph.add_edges_from([(0, 2), (1, 2)])
    return graph


def run_case(method='LOOKAHEAD_2', **limit_changes):
    return scale.evaluate(double_parent_graph(), 54001, 'hand', .5, 2, 3,
                          method, {**LIMITS, **limit_changes})


def test_all_three_policies_are_new_full_evaluations_with_day_mass_one():
    for method in ('LOOKAHEAD_1', 'LOOKAHEAD_2', 'LOOKAHEAD_FULL'):
        case, rows = run_case(method)
        assert case['status'] == 'complete' and case['stop_reason'] is None
        assert case['root_value'] == 2.75 and case['root_selected'] == [0]
        assert case['value_source'] == 'V54_full_policy_evaluation' and case['control_method'] is None
        assert case['evaluation_work']['new_full_policy_backups'] == len(rows) == 6
        assert case['evaluation_work']['retained_value_reads'] == 0
        assert all(row[field] == case[field] for row in rows
                   for field in ('graph_id', 'method', 'nodes', 'stratum', 'p', 'budget', 'horizon'))
        assert 0. < case['last_limit_check_seconds'] <= case['wall_seconds']
        for days in (1, 2, 3):
            assert math.fsum(row['reach_probability'] for row in rows
                             if row['remaining_days'] == days) == 1.
        assert case['decision_work']['planner_calls'] == 6
        assert case['expected_decision_work']['planner_calls'] == 3.
        assert case['wall_seconds'] == pytest.approx(case['decision_seconds'] + case['evaluation_seconds'])


@pytest.mark.parametrize('limits,reason', [
    (dict(max_planner_action_values=1, max_policy_states=1), 'max_planner_action_values'),
    (dict(max_policy_states=1), 'max_policy_states')])
def test_limit_after_full_decision_keeps_overshoot_before_outer_kernel(limits, reason):
    case, rows = run_case(**limits)
    assert case['status'] == 'resource_limit' and case['stop_reason'] == reason
    assert case['root_value'] is None and case['root_selected'] is None
    assert case['expected_decision_work'] is None and case['expected_decision_seconds'] is None
    assert len(rows) == case['state_records'] == case['decision_work']['planner_calls'] == 1
    assert rows[0]['selected'] == [0] and rows[0]['planned_value'] == 2.75
    assert rows[0]['value'] is None and rows[0]['reach_probability'] is None
    assert case['decision_work']['action_value_evaluations'] > 1
    assert case['decision_work']['action_value_evaluations'] == rows[0]['decision_work']['action_value_evaluations']
    assert case['evaluation_work']['kernel_builds'] == 0
    assert case['evaluation_work']['new_full_policy_backups'] == 0
    assert case['decision_seconds'] == rows[0]['decision_seconds'] > 0.


def test_partial_policy_retains_completed_values_and_all_paid_decisions():
    case, rows = run_case('LOOKAHEAD_1', max_policy_states=4)
    assert case['status'] == 'resource_limit' and case['stop_reason'] == 'max_policy_states'
    assert len(rows) == case['decision_work']['planner_calls'] == 4
    completed = [row for row in rows if row['value'] is not None]
    assert len(completed) == case['evaluation_work']['new_full_policy_backups'] == 1
    assert completed[0]['remaining_days'] == 1 and completed[0]['value'] == 0.
    assert case['evaluation_work']['kernel_builds'] == 3
    assert all(row['reach_probability'] is None for row in rows)
    assert case['root_value'] is None and case['root_selected'] is None
    assert case['expected_decision_work'] is None and case['expected_decision_seconds'] is None
    summed = Counter()
    for row in rows:
        summed.update(row['decision_work'])
    assert case['decision_work'] == dict(summed)


def test_wall_limit_uses_the_same_post_decision_boundary_without_sleep():
    ticks = count(0., .25)
    with patch.object(scale, 'perf_counter', side_effect=lambda: next(ticks)):
        case, rows = run_case(max_wall_seconds=.5)
    assert case['status'] == 'resource_limit' and case['stop_reason'] == 'max_wall_seconds'
    assert len(rows) == 1 and rows[0]['selected'] == [0]
    assert case['decision_seconds'] == .25
    assert case['last_limit_check_seconds'] == .75
    assert case['evaluation_work']['kernel_builds'] == case['evaluation_work']['new_full_policy_backups'] == 0
    assert case['wall_seconds'] == case['decision_seconds'] + case['evaluation_seconds']
    assert case['root_value'] is None and case['expected_decision_work'] is None
