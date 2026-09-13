"""Finite-window semantics on hand graphs; no main panel or environments."""
from collections import Counter
import json
import math
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_exact_v52 import ExactAIMSolver
from acfqp.science import lmta_lookahead_v53 as lookahead


@pytest.fixture(scope='module', autouse=True)
def development_accounting(request):
    started = perf_counter()
    solvers = []
    plan_calls = 0
    original_init = ExactAIMSolver.__init__
    original_plan = lookahead.plan
    before_failures = request.session.testsfailed

    def initialize(solver, *args, **kwargs):
        original_init(solver, *args, **kwargs)
        solvers.append(solver)

    def measured_plan(*args, **kwargs):
        nonlocal plan_calls
        plan_calls += 1
        return original_plan(*args, **kwargs)

    with patch.object(ExactAIMSolver, '__init__', initialize), \
         patch.object(lookahead, 'plan', measured_plan):
        yield
    counts = Counter()
    for solver in solvers:
        counts.update(solver.counters)
    path = Path(__file__).resolve().parents[1] / 'reports/lmta_lookahead_v53.development_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_lookahead_v53.py',
        new_failures=request.session.testsfailed - before_failures,
        environment_counters={}, model_evaluations=0, gradient_steps=0,
        planner_calls=plan_calls, solver_instances=len(solvers),
        standalone_V52_solver_instances=len(solvers) - plan_calls,
        all_solver_counters=dict(counts), wall_seconds=perf_counter() - started,
        scope='Hand-graph finite-depth calls and original V52 controls; every planner/kernel/DP enumeration is included, with no environment or main-panel evaluation.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


def graph(n, edges=()):
    result = nx.DiGraph()
    result.add_nodes_from(range(n))
    result.add_edges_from(edges)
    return result


def root_record(solver, state, budget, days):
    return next(row for row in solver.records() if row['statuses'] == list(state)
                and row['remaining_budget'] == budget and row['remaining_days'] == days)


def test_window_end_does_not_become_the_real_final_day_and_ties_take_first():
    result = lookahead.plan(graph(5), (0,) * 5, budget=3, remaining_days=3, depth=2)
    assert result['selected'] == [0]
    assert result['planned_value'] == 2.
    assert result['root_action_values'] == [dict(selected=[node], value=2.) for node in range(5)]
    assert result['counters']['forced_choice'] == 0


def test_chain_star_windows_count_propagation_after_budget_is_zero():
    g = graph(7, [(0, 1), (1, 2), (2, 3), (4, 5), (4, 6)])
    results = [lookahead.plan(g, (0,) * 7, 1, 3, depth) for depth in (1, 2, 3)]
    assert [r['selected'] for r in results] == [[4], [0], [0]]
    assert [r['planned_value'] for r in results] == [3., 3., 4.]
    by_action = [{tuple(row['selected']): row['value'] for row in result['root_action_values']}
                 for result in results]
    assert [values[(0,)] for values in by_action] == [2., 3., 4.]
    assert [values[(4,)] for values in by_action] == [3., 3., 3.]


def test_full_depth_matches_v52_optimal_and_depth_one_matches_myopic_action():
    g = graph(5, [(0, 2), (1, 2), (2, 3), (3, 4), (0, 4)])
    state = (0,) * 5
    optimal = ExactAIMSolver(g, 'AVERAGE_OPTIMAL')
    expected = optimal.value(state, 2, 3)
    full = lookahead.plan(g, state, 2, 3, depth=4)
    assert full['planned_value'] == expected
    assert full['selected'] == root_record(optimal, state, 2, 3)['selected']
    myopic = ExactAIMSolver(g, 'AVERAGE_MYOPIC')
    myopic.value(state, 2, 3)
    myopic_action = root_record(myopic, state, 2, 3)['selected']
    one = lookahead.plan(g, state, 2, 3, depth=1)
    assert one['selected'] == myopic_action
    immediate = math.fsum(probability * reward
                          for probability, _, reward in myopic.kernel(state, myopic_action))
    assert one['planned_value'] == immediate


@pytest.mark.parametrize('state,budget,selected', [((1, 0, 0), 0, []),
                                                  ((2, 2, 0), 1, [2]),
                                                  ((2, 2, 2), 1, [])])
def test_forced_root_action_skips_all_value_work(state, budget, selected):
    g = graph(3, [(0, 1), (1, 2)])
    for depth in (1, 2, 3):
        result = lookahead.plan(g, state, budget, 3, depth)
        assert result['selected'] == selected
        assert result['planned_value'] is None and result['root_action_values'] == []
        assert result['counters']['forced_choice'] == 1
        assert all(value == 0 for name, value in result['counters'].items() if name != 'forced_choice')
    if budget == 0:
        # Skipping a forced decision is distinct from assigning zero future reward.
        control = ExactAIMSolver(g, 'AVERAGE_OPTIMAL')
        assert control.value(state, 0, 3) == 2.
