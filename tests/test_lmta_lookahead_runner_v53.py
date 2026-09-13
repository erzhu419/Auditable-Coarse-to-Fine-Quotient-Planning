"""Hand-calculated outer-policy values, control reuse and occupancy costs."""
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_exact_v52 import ExactAIMSolver


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lookahead_runner_v53_test',
    ROOT / 'scripts/run_lmta_lookahead_v53.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture(scope='module', autouse=True)
def development_accounting(request):
    started = perf_counter()
    work = dict(solvers=[], source_counters=Counter(), cases=[], planner_calls=0)
    original_init = ExactAIMSolver.__init__
    original_plan = runner.plan
    before_failures = request.session.testsfailed

    def initialize(solver, *args, **kwargs):
        original_init(solver, *args, **kwargs)
        work['solvers'].append(solver)

    def planned(*args, **kwargs):
        work['planner_calls'] += 1
        return original_plan(*args, **kwargs)

    with patch.object(ExactAIMSolver, '__init__', initialize), patch.object(runner, 'plan', planned):
        yield work
    total = Counter()
    for solver in work['solvers']:
        total.update(solver.counters)
    path = ROOT / 'reports/lmta_lookahead_v53.development_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_lookahead_runner_v53.py',
        new_failures=request.session.testsfailed - before_failures,
        environment_counters={}, model_evaluations=0, gradient_steps=0,
        planner_calls=work['planner_calls'], solver_instances=len(work['solvers']),
        all_solver_counters=dict(total), retained_source_solver_counters=dict(work['source_counters']),
        outer_evaluations=work['cases'], wall_seconds=perf_counter() - started,
        scope='All small-graph planning, outer evaluation, and creation of V52 control rows is charged. Source counters are a subset of all_solver_counters, not an extra charge; no environments or main-panel results.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


@pytest.fixture(scope='module')
def evaluated_cases(development_accounting):
    graph = nx.DiGraph()
    graph.add_nodes_from(range(3))
    graph.add_edges_from([(0, 2), (1, 2)])
    retained = {}
    for method in runner.CONTROLS.values():
        solver = ExactAIMSolver(graph, method)
        assert solver.value((0, 0, 0), 2, 3) == 2.75
        retained[method] = {runner.key(row): row for row in solver.records()}
        development_accounting['source_counters'].update(solver.counters)
    results = {}
    for method in runner.METHODS:
        source_rows = retained.get(runner.CONTROLS.get(method), {})
        before_calls = development_accounting['planner_calls']
        case, states = runner.evaluate(graph, 53001, .5, 3, method, source_rows)
        actual_calls = development_accounting['planner_calls'] - before_calls
        results[method] = case, states, source_rows, actual_calls
        development_accounting['cases'].append(dict(method=method,
            wall_seconds=case['wall_seconds'], decision_seconds=case['decision_seconds'],
            evaluation_seconds=case['evaluation_seconds'], state_records=len(states),
            planner_calls=actual_calls, evaluation_work=case['evaluation_work']))
    return results


def test_exact_coverage_and_reach_mass_at_every_real_day(evaluated_cases):
    expected_reach = {((0, 0, 0), 2, 3): 1.,
                      ((2, 0, 0), 1, 2): .5, ((2, 0, 1), 1, 2): .5,
                      ((2, 2, 0), 0, 1): .25, ((2, 2, 1), 0, 1): .25,
                      ((2, 2, 2), 0, 1): .5}
    for case, states, _, _ in evaluated_cases.values():
        assert case['root_value'] == 2.75
        assert case['root_selected'] == [0]
        actual = {runner.key(row): row['reach_probability'] for row in states}
        assert actual == expected_reach
        for days in (1, 2, 3):
            assert math.fsum(row['reach_probability'] for row in states
                              if row['remaining_days'] == days) == 1.


def test_controls_reuse_bound_values_and_actions_without_free_planning(evaluated_cases):
    for method, (case, states, retained, _) in evaluated_cases.items():
        evaluation = case['evaluation_work']
        if method in runner.CONTROLS:
            assert case['value_source'] == 'V52_retained'
            assert case['control_method'] == runner.CONTROLS[method]
            assert evaluation['new_full_policy_backups'] == 0
            assert evaluation['retained_value_reads'] == len(states)
            for row in states:
                assert row['value'] == retained[runner.key(row)]['value']
                assert row['selected'] == retained[runner.key(row)]['selected']
        else:
            assert retained == {} and case['control_method'] is None
            assert case['value_source'] == 'V53_full_policy_evaluation'
            assert evaluation['new_full_policy_backups'] == len(states)
            assert evaluation['retained_value_reads'] == 0
        assert evaluation['kernel_builds'] > 0
        assert case['decision_work']['action_value_evaluations'] > 0
        assert case['decision_seconds'] > 0 and case['evaluation_seconds'] > 0


def test_unique_planning_calls_and_probability_weighted_costs_are_distinct(evaluated_cases):
    for case, states, _, actual_calls in evaluated_cases.values():
        assert actual_calls == case['decision_work']['planner_calls'] == len(states) == 6
        assert all(row['decision_work']['planner_calls'] == 1 for row in states)
        assert case['expected_decision_work']['planner_calls'] == 3.
        assert math.fsum(row['reach_probability'] * row['decision_work']['planner_calls']
                         for row in states) == 3.
        forced = [row for row in states if row['decision_work']['forced_choice']]
        assert len(forced) == 4
        assert all(row['decision_work']['dp_states'] == row['decision_work']['kernel_builds'] == 0
                   for row in forced)
        assert case['wall_seconds'] == pytest.approx(case['decision_seconds'] + case['evaluation_seconds'])
        assert case['decision_seconds'] == math.fsum(row['decision_seconds'] for row in states)
        assert case['expected_decision_seconds'] == math.fsum(
            row['reach_probability'] * row['decision_seconds'] for row in states)
