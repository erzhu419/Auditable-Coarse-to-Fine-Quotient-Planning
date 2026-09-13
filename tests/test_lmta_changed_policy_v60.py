"""Complete one-day-policy branches and paid incomplete decisions on a hand graph."""
from collections import Counter
import json
import math
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_exact_v52 import ExactAIMSolver
from acfqp.science import lmta_changed_policy_v60 as candidate


LIMITS = dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.)


@pytest.fixture(scope='module', autouse=True)
def development_accounting(request):
    started = perf_counter()
    record = dict(solvers=[], planner_calls=0, depths=[], evaluations=[], hand_graphs=0)
    original_init, original_plan, original_evaluate = ExactAIMSolver.__init__, candidate.plan, candidate.evaluate
    before_failures = request.session.testsfailed

    def initialize(solver, *args, **kwargs):
        original_init(solver, *args, **kwargs)
        record['solvers'].append(solver)

    def planned(*args, **kwargs):
        record['planner_calls'] += 1
        record['depths'].append(kwargs.get('depth', args[4] if len(args) > 4 else None))
        return original_plan(*args, **kwargs)

    def evaluated(*args, **kwargs):
        tick = perf_counter()
        case, rows = original_evaluate(*args, **kwargs)
        record['evaluations'].append(dict(status=case['status'], state_records=len(rows),
            decision_work=case['decision_work'], evaluation_work=case['evaluation_work'],
            actual_test_seconds=perf_counter() - tick))
        return case, rows

    with patch.object(ExactAIMSolver, '__init__', initialize), \
         patch.object(candidate, 'plan', planned), patch.object(candidate, 'evaluate', evaluated):
        yield record
    counts = Counter()
    for solver in record['solvers']:
        counts.update(solver.counters)
    path = Path(__file__).resolve().parents[1] / 'reports/lmta_changed_policy_v60.evaluator_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_changed_policy_v60.py',
        new_failures=request.session.testsfailed - before_failures,
        environment_counters={}, model_evaluations=0, gradient_steps=0,
        hand_graph_constructions=record['hand_graphs'], sampled_graphs=0,
        planner_calls=record['planner_calls'], planner_depths=record['depths'], solver_instances=len(record['solvers']),
        all_solver_counters=dict(counts), outer_evaluations=record['evaluations'],
        wall_seconds=perf_counter() - started,
        scope='All actual hand-graph cold decisions and complete/partial outer enumerations are included. Complete hand evidence is reused by two assertions without duplicate evaluation. No main graph, environmental samples or learned models.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


def hand_graph(record):
    record['hand_graphs'] += 1
    graph = nx.DiGraph()
    graph.add_nodes_from(range(3))
    graph.add_edges_from([(0, 2), (1, 2)])
    return graph


@pytest.fixture(scope='module')
def complete_case(development_accounting):
    graph = hand_graph(development_accounting)
    return candidate.evaluate(graph, -1, 'hand', .5, 2, 3, LIMITS)


def test_short_planned_value_is_distinct_from_complete_policy_return(complete_case, development_accounting):
    case, rows = complete_case
    root = next(row for row in rows if row['remaining_days'] == 3)
    assert case['status'] == 'complete' and case['stop_reason'] is None
    assert case['method'] == 'LOOKAHEAD_1_ANALYTIC' and case['value_source'] == 'V60_full_policy_evaluation'
    assert case['root_selected'] == root['selected'] == [0]
    assert root['planned_value'] == 1.5
    assert case['root_value'] == root['value'] == .5 * (1. + 1.5) + .5 * (2. + 1.) == 2.75
    assert all(depth == 1 for depth in development_accounting['depths'])
    assert 'cleanup_seconds' not in case


def test_complete_branch_closure_occupancy_and_costs_are_retained(complete_case):
    case, rows = complete_case
    actual = {(tuple(row['statuses']), row['remaining_budget'], row['remaining_days']):
              (row['selected'], row['value'], row['reach_probability']) for row in rows}
    assert actual == {((0, 0, 0), 2, 3): ([0], 2.75, 1.),
                      ((2, 0, 0), 1, 2): ([1], 1.5, .5),
                      ((2, 0, 1), 1, 2): ([1], 1., .5),
                      ((2, 2, 0), 0, 1): ([], 0., .25),
                      ((2, 2, 1), 0, 1): ([], 0., .25),
                      ((2, 2, 2), 0, 1): ([], 0., .5)}
    for days in (1, 2, 3):
        assert math.fsum(row['reach_probability'] for row in rows if row['remaining_days'] == days) == 1.
    for row in rows:
        assert all(row[key] == case[key] for key in ('graph_id', 'method', 'nodes', 'stratum', 'p', 'budget', 'horizon'))
    work = Counter()
    for row in rows:
        work.update(row['decision_work'])
    assert dict(work) == case['decision_work']
    assert case['state_records'] == case['decision_work']['planner_calls'] == 6
    assert case['decision_work']['kernel_builds'] == case['decision_work']['transition_outcomes'] == 0
    assert case['decision_work']['action_value_evaluations'] == case['decision_work']['analytic_expectation_calls'] == 5
    assert case['decision_work']['analytic_probability_terms'] == 8
    assert case['evaluation_work']['kernel_builds'] == case['evaluation_work']['new_full_policy_backups'] == 6
    assert case['evaluation_work']['transition_outcomes'] == 8
    assert case['evaluation_work']['retained_value_reads'] == 0
    assert case['expected_decision_work']['planner_calls'] == 3.
    assert case['expected_decision_work']['analytic_expectation_calls'] == 4.
    assert case['wall_seconds'] == pytest.approx(case['decision_seconds'] + case['evaluation_seconds'], rel=0, abs=1e-12)


@pytest.mark.parametrize('actions,states,reason', [(1, 1, 'max_planner_action_values'),
                                                 (100, 1, 'max_policy_states')])
def test_soft_stop_charges_finished_decision_before_any_quality_claim(actions, states, reason, development_accounting):
    graph = hand_graph(development_accounting)
    limits = dict(max_planner_action_values=actions, max_policy_states=states, max_wall_seconds=60.)
    case, rows = candidate.evaluate(graph, -1, 'hand', .5, 2, 3, limits)
    assert case['status'] == 'resource_limit' and case['stop_reason'] == reason
    assert case['root_value'] is None and case['root_selected'] is None
    assert case['expected_decision_work'] is None and case['expected_decision_seconds'] is None
    assert len(rows) == case['state_records'] == case['decision_work']['planner_calls'] == 1
    assert case['decision_work'] == rows[0]['decision_work']
    assert case['decision_work']['action_value_evaluations'] == 3
    assert case['decision_work']['analytic_expectation_calls'] == 3
    assert rows[0]['selected'] == [0] and rows[0]['planned_value'] == 1.5
    assert rows[0]['value'] is None and rows[0]['reach_probability'] is None
    assert case['evaluation_work']['kernel_builds'] == case['evaluation_work']['new_full_policy_backups'] == 0
