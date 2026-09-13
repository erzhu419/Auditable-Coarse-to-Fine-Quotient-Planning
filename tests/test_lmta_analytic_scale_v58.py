"""Fresh analytic-policy evaluation and paid resource stops on hand graphs."""
from collections import Counter
import json
import math
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_exact_v52 import ExactAIMSolver
from acfqp.science import lmta_analytic_scale_v58 as candidate
from acfqp.science import lmta_scale_v54 as control


LIMITS = dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.)


@pytest.fixture(scope='module', autouse=True)
def development_accounting(request):
    started = perf_counter()
    record = dict(solvers=[], planner_calls=Counter(), evaluations=[], hand_graphs=0, mock_clock_evaluations=0)
    original_init = ExactAIMSolver.__init__
    original_planners = dict(lookahead=candidate.lookahead_plan, analytic=candidate.analytic_plan,
                             reference=control.plan)
    original_candidate, original_control = candidate.evaluate, control.evaluate
    before_failures = request.session.testsfailed

    def initialize(solver, *args, **kwargs):
        original_init(solver, *args, **kwargs)
        record['solvers'].append(solver)

    def planner(name):
        def measured(*args, **kwargs):
            record['planner_calls'][name] += 1
            return original_planners[name](*args, **kwargs)
        return measured

    def evaluator(source, function):
        def measured(*args, **kwargs):
            tick = perf_counter()
            case, rows = function(*args, **kwargs)
            record['evaluations'].append(dict(source=source, method=case['method'], status=case['status'],
                state_records=len(rows), decision_work=case['decision_work'], evaluation_work=case['evaluation_work'],
                actual_test_seconds=perf_counter() - tick))
            return case, rows
        return measured

    with patch.object(ExactAIMSolver, '__init__', initialize), \
         patch.object(candidate, 'lookahead_plan', planner('lookahead')), \
         patch.object(candidate, 'analytic_plan', planner('analytic')), \
         patch.object(control, 'plan', planner('reference')), \
         patch.object(candidate, 'evaluate', evaluator('V58', original_candidate)), \
         patch.object(control, 'evaluate', evaluator('V54', original_control)):
        yield record
    counts = Counter()
    for solver in record['solvers']:
        counts.update(solver.counters)
    path = Path(__file__).resolve().parents[1] / 'reports/lmta_analytic_scale_v58.evaluator_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_analytic_scale_v58.py',
        new_failures=request.session.testsfailed - before_failures,
        environment_counters={}, model_evaluations=0, gradient_steps=0,
        hand_graph_constructions=record['hand_graphs'], sampled_graphs=0,
        planner_calls=dict(record['planner_calls']), solver_instances=len(record['solvers']),
        all_solver_counters=dict(counts), outer_evaluations=record['evaluations'],
        mock_clock_evaluations=record['mock_clock_evaluations'], wall_seconds=perf_counter() - started,
        scope='All actual candidate/control planning and complete/partial outer evaluation is charged. One mocked evaluator clock checks wall limits; actual_test_seconds and wall_seconds use the real clock. No fresh panel, sampled graphs, environment or learned-model work.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


@pytest.fixture
def hand_graph(development_accounting):
    development_accounting['hand_graphs'] += 1
    graph = nx.DiGraph()
    graph.add_nodes_from(range(3))
    graph.add_edges_from([(0, 2), (1, 2)])
    return graph


def evaluate_hand(graph, method, limits=LIMITS):
    return candidate.evaluate(graph, -1, 'hand', .5, 2, 3, method, limits)


def assert_complete_case(case, rows):
    assert case['status'] == 'complete' and case['stop_reason'] is None
    assert case['root_value'] == 2.75 and case['root_selected'] == [0]
    assert case['value_source'] == 'V58_full_policy_evaluation'
    assert len(rows) == case['state_records'] == case['decision_work']['planner_calls']
    assert case['evaluation_work']['new_full_policy_backups'] == len(rows)
    assert case['evaluation_work']['retained_value_reads'] == 0
    assert case['evaluation_work']['kernel_builds'] > 0
    root = next(row for row in rows if row['statuses'] == [0, 0, 0] and row['remaining_days'] == 3)
    assert root['value'] == case['root_value'] and root['selected'] == case['root_selected']
    assert root['reach_probability'] == 1. and root['remaining_budget'] == 2
    assert root['root_action_values']
    for row in rows:
        assert all(row[key] == case[key] for key in ('graph_id', 'method', 'nodes', 'stratum', 'p', 'budget', 'horizon'))
        assert row['value'] is not None and row['reach_probability'] is not None
    for days in (1, 2, 3):
        assert math.fsum(row['reach_probability'] for row in rows if row['remaining_days'] == days) == 1.
    assert case['expected_decision_work']['planner_calls'] == 3.
    work = Counter()
    for row in rows:
        work.update(row['decision_work'])
    assert dict(work) == case['decision_work']
    assert case['wall_seconds'] == pytest.approx(case['decision_seconds'] + case['evaluation_seconds'], rel=0, abs=1e-12)
    assert 'cleanup_seconds' not in case


@pytest.mark.parametrize('depth', [1, 2])
def test_short_horizon_dispatch_keeps_frozen_planner_and_fresh_evaluation(depth, hand_graph):
    original, calls = candidate.lookahead_plan, []

    def recorded(graph, statuses, budget, days, actual_depth):
        calls.append((days, actual_depth))
        return original(graph, statuses, budget, days, actual_depth)

    with patch.object(candidate, 'lookahead_plan', recorded), \
         patch.object(candidate, 'analytic_plan', side_effect=AssertionError('wrong planner')):
        case, rows = evaluate_hand(hand_graph, f'LOOKAHEAD_{depth}')
    assert_complete_case(case, rows)
    assert len(calls) == len(rows)
    assert all(actual == min(depth, days) for days, actual in calls)
    assert 'analytic_expectation_calls' not in case['decision_work']


def test_analytic_full_matches_original_full_policy_with_independent_outer_work(hand_graph):
    with patch.object(candidate, 'lookahead_plan', side_effect=AssertionError('wrong planner')):
        case, rows = evaluate_hand(hand_graph, 'LOOKAHEAD_FULL_ANALYTIC')
    old_case, old_rows = control.evaluate(hand_graph, -1, 'hand', .5, 2, 3, 'LOOKAHEAD_FULL', LIMITS)
    assert_complete_case(case, rows)
    assert case['root_value'] == old_case['root_value']
    fields = ('statuses', 'remaining_budget', 'remaining_days', 'selected', 'value', 'reach_probability')
    assert [{key: row[key] for key in fields} for row in rows] == [{key: row[key] for key in fields} for row in old_rows]
    assert case['decision_work']['analytic_expectation_calls'] > 0
    assert case['decision_work']['analytic_probability_terms'] > 0
    assert 'analytic_expectation_calls' not in case['evaluation_work']


@pytest.mark.parametrize('actions,states,reason', [(1, 1, 'max_planner_action_values'),
                                                 (2000000, 1, 'max_policy_states')])
def test_soft_limits_keep_completed_decision_costs_without_a_quality_claim(actions, states, reason, hand_graph):
    limits = dict(max_planner_action_values=actions, max_policy_states=states, max_wall_seconds=60.)
    case, rows = evaluate_hand(hand_graph, 'LOOKAHEAD_FULL_ANALYTIC', limits)
    assert_partial_case(case, rows, reason)


def assert_partial_case(case, rows, reason):
    assert case['status'] == 'resource_limit' and case['stop_reason'] == reason
    assert len(rows) == case['state_records'] == case['decision_work']['planner_calls'] == 1
    assert case['root_value'] is None and case['root_selected'] is None
    assert case['expected_decision_work'] is None and case['expected_decision_seconds'] is None
    assert rows[0]['selected'] == [0] and rows[0]['root_action_values']
    assert rows[0]['value'] is None and rows[0]['reach_probability'] is None
    assert case['decision_work'] == rows[0]['decision_work']
    assert case['decision_work']['analytic_expectation_calls'] > 0
    assert case['decision_work']['action_value_evaluations'] > 0
    assert case['evaluation_work']['kernel_builds'] == case['evaluation_work']['new_full_policy_backups'] == 0


def test_wall_limit_uses_last_paid_check_before_final_bookkeeping(hand_graph, development_accounting):
    development_accounting['mock_clock_evaluations'] += 1
    limits = dict(LIMITS, max_wall_seconds=1.)
    with patch.object(candidate, 'perf_counter', side_effect=[0., 1., 2., 3., 4.]):
        case, rows = evaluate_hand(hand_graph, 'LOOKAHEAD_FULL_ANALYTIC', limits)
    assert_partial_case(case, rows, 'max_wall_seconds')
    assert case['last_limit_check_seconds'] == 3. and case['wall_seconds'] == 4.
    assert case['decision_seconds'] == 1. and case['evaluation_seconds'] == 3.
