"""Analytic last-day rewards and paid full-search work on hand graphs only."""
from collections import Counter
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_exact_v52 import ExactAIMSolver
from acfqp.science import lmta_analytic_terminal_v56 as candidate
from acfqp.science import lmta_lookahead_v53 as control


@pytest.fixture(scope='module', autouse=True)
def development_accounting(request):
    started, solvers = perf_counter(), []
    plan_calls = Counter(candidate=0, control=0)
    original_init = ExactAIMSolver.__init__
    original_candidate, original_control = candidate.plan, control.plan
    before_failures = request.session.testsfailed

    def initialize(solver, *args, **kwargs):
        original_init(solver, *args, **kwargs)
        solvers.append(solver)

    def candidate_plan(*args, **kwargs):
        plan_calls['candidate'] += 1
        return original_candidate(*args, **kwargs)

    def control_plan(*args, **kwargs):
        plan_calls['control'] += 1
        return original_control(*args, **kwargs)

    with patch.object(ExactAIMSolver, '__init__', initialize), \
         patch.object(candidate, 'plan', candidate_plan), patch.object(control, 'plan', control_plan):
        yield
    counts = Counter()
    for solver in solvers:
        counts.update(solver.counters)
    path = Path(__file__).resolve().parents[1] / 'reports/lmta_analytic_terminal_v56.evaluator_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_analytic_terminal_v56.py',
        new_failures=request.session.testsfailed - before_failures,
        environment_counters={}, model_evaluations=0, gradient_steps=0,
        planner_calls=dict(plan_calls), solver_instances=len(solvers),
        all_solver_counters=dict(counts), wall_seconds=perf_counter() - started,
        scope='All hand-graph analytic candidate and V53 control calls are included. No graph generation samples, environment calls, model work, fresh panel or outer policy evaluation.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


def graph(n, edges=()):
    result = nx.DiGraph()
    result.add_nodes_from(range(n))
    result.add_edges_from(edges)
    return result


def assert_same_roots(result, expected):
    assert result['selected'] == expected['selected']
    assert result['planned_value'] == pytest.approx(expected['planned_value'], rel=0, abs=1e-12)
    assert [row['selected'] for row in result['root_action_values']] == [row['selected'] for row in expected['root_action_values']]
    assert [row['value'] for row in result['root_action_values']] == pytest.approx(
        [row['value'] for row in expected['root_action_values']], rel=0, abs=1e-12)


def test_terminal_overlap_uses_full_indegree_and_does_not_recount_old_activity():
    g = graph(5, [(0, 3), (1, 3), (2, 3), (4, 3)])
    # Two active parents give q=1-(3/4)^2; removed node 2 is no source.
    with patch.object(ExactAIMSolver, 'kernel', side_effect=AssertionError('terminal kernel called')):
        result = candidate.plan(g, (1, 0, 2, 0, 0), 1, 1)
    assert result['selected'] == [1]
    assert result['root_action_values'] == [dict(selected=[1], value=1.4375),
                                          dict(selected=[3], value=1.),
                                          dict(selected=[4], value=1.4375)]
    work = result['counters']
    assert work['analytic_expectation_calls'] == work['action_value_evaluations'] == 3
    assert work['analytic_probability_terms'] == work['target_probability_evaluations'] == 6
    assert work['dp_states'] == 1
    assert all(work[name] == 0 for name in ('kernel_builds', 'kernel_cache_hits',
                                           'transition_outcomes', 'bellman_expectation_terms'))


def test_zero_budget_inside_search_still_propagates_through_terminal_day():
    g = graph(7, [(0, 1), (1, 2), (2, 3), (4, 5), (4, 6)])
    result = candidate.plan(g, (0,) * 7, 1, 3)
    expected = control.plan(g, (0,) * 7, 1, 3, 3)
    assert_same_roots(result, expected)
    assert result['selected'] == [0] and result['planned_value'] == 4.
    q = {tuple(row['selected']): row['value'] for row in result['root_action_values']}
    assert q[(0,)] == 4. and q[(4,)] == 3.
    assert result['counters']['analytic_expectation_calls'] > 0
    assert result['counters']['kernel_builds'] > 0


def test_branching_full_search_preserves_values_and_charges_only_executed_work():
    g = graph(5, [(0, 2), (1, 2), (2, 3), (3, 4), (0, 4)])
    result = candidate.plan(g, (0,) * 5, 2, 3)
    expected = control.plan(g, (0,) * 5, 2, 3, 3)
    assert_same_roots(result, expected)
    actual, old = result['counters'], expected['counters']
    assert actual['dp_states'] == old['dp_states']
    assert actual['action_value_evaluations'] == old['action_value_evaluations']
    assert actual['action_value_evaluations'] == (actual['kernel_builds']
        + actual['kernel_cache_hits'] + actual['analytic_expectation_calls'])
    assert actual['kernel_builds'] < old['kernel_builds']
    assert actual['transition_outcomes'] < old['transition_outcomes']
    assert actual['bellman_expectation_terms'] < old['bellman_expectation_terms']
    assert actual['analytic_probability_terms'] > 0
    assert actual['target_probability_evaluations'] >= actual['analytic_probability_terms']


def test_real_horizon_allocation_and_strict_lexicographic_ties():
    result = candidate.plan(graph(5), (0,) * 5, 4, 4)
    assert result['selected'] == [0]
    assert result['planned_value'] == 4.
    assert result['root_action_values'] == [dict(selected=[node], value=4.) for node in range(5)]


def test_forced_root_skips_both_analytic_and_enumerated_values():
    g = graph(3, [(0, 1), (1, 2)])
    for state, budget, selected in [((1, 0, 0), 0, []),
                                     ((2, 2, 0), 1, [2]), ((2, 2, 2), 1, [])]:
        result = candidate.plan(g, state, budget, 3)
        assert result['selected'] == selected
        assert result['planned_value'] is None and result['root_action_values'] == []
        assert result['counters']['forced_choice'] == 1
        assert all(value == 0 for name, value in result['counters'].items() if name != 'forced_choice')
