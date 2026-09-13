"""Exact tie refinement and phase accounting on bounded known/hand graphs."""
from collections import Counter
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_exact_v52 import ExactAIMSolver
from acfqp.science import lmta_tie_refinement_v55 as candidate


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def development_accounting(request):
    started = perf_counter()
    work = dict(solvers=[], plans=0, evaluations=[], returned_plan_work=Counter())
    original_init, original_plan = ExactAIMSolver.__init__, candidate.plan
    original_evaluate = candidate.evaluate
    before_failures = request.session.testsfailed

    def initialize(solver, *args, **kwargs):
        original_init(solver, *args, **kwargs)
        work['solvers'].append(solver)

    def planned(*args, **kwargs):
        work['plans'] += 1
        result = original_plan(*args, **kwargs)
        work['returned_plan_work'].update(result['counters'])
        return result

    def evaluated(*args, **kwargs):
        tick = perf_counter()
        result = original_evaluate(*args, **kwargs)
        case, rows = result
        work['evaluations'].append(dict(status=case['status'], state_records=len(rows),
            stop_reason=case['stop_reason'], evaluation_work=case['evaluation_work'],
            actual_test_seconds=perf_counter() - tick))
        return result

    with patch.object(ExactAIMSolver, '__init__', initialize), \
         patch.object(candidate, 'plan', planned), patch.object(candidate, 'evaluate', evaluated):
        yield
    total = Counter()
    for solver in work['solvers']:
        total.update(solver.counters)
    path = ROOT / 'reports/lmta_tie_refinement_v55.evaluator_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_tie_refinement_v55.py',
        new_failures=request.session.testsfailed - before_failures,
        environment_counters={}, model_evaluations=0, gradient_steps=0,
        planner_calls=work['plans'], solver_instances=len(work['solvers']),
        all_solver_counters=dict(total), returned_candidate_plan_counters=dict(work['returned_plan_work']),
        outer_evaluations=work['evaluations'], wall_seconds=perf_counter() - started,
        scope='All candidate/prefix controls and resource-limited test work is included. Returned-plan counters describe a subset of all_solver_counters and are not additive fees; no environment draws, main panel or learned models.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


def graph(n, edges=()):
    result = nx.DiGraph()
    result.add_nodes_from(range(n))
    result.add_edges_from(edges)
    return result


@pytest.fixture(scope='module')
def regression_graph():
    manifest = json.loads((ROOT / 'reports/lmta_scale_v54/manifest.json').read_text())
    row = next(row for row in manifest['graphs'] if row['graph_id'] == 540009)
    return graph(row['nodes'], row['edges'])


def assert_combined_ledger(result):
    for name in set(result['prefix_work']) | set(result['refinement_work']):
        assert result['counters'][name] == result['prefix_work'].get(name, 0) + result['refinement_work'].get(name, 0)
    assert 'forced_choice' not in result['refinement_work']
    assert result['counters']['refinement_calls'] == bool(result['refinement_action_values'])
    assert result['counters']['refined_root_actions'] == len(result['refinement_action_values'])


def test_known_root_tie_is_repaired_without_evaluating_untied_roots(regression_graph):
    initial, called_roots = (0,) * 7, []
    original = ExactAIMSolver.kernel

    def kernel(solver, statuses, selected):
        if tuple(statuses) == initial:
            called_roots.append(tuple(selected))
        return original(solver, statuses, selected)

    with patch.object(ExactAIMSolver, 'kernel', kernel):
        result = candidate.plan(regression_graph, initial, 2, 3)
    assert result['prefix_selected'] == [1] and result['selected'] == [5]
    assert result['planned_value'] == 5.
    assert result['refinement_action_values'] == [dict(selected=[1], value=5.40625),
                                                dict(selected=[5], value=5.5)]
    assert called_roots == [(node,) for node in range(7)] + [(1,), (5,)]
    assert result['prefix_work']['kernel_builds'] > 0 and result['refinement_work']['kernel_builds'] > 0
    assert_combined_ledger(result)


def test_unique_prefix_best_does_not_refine():
    result = candidate.plan(graph(4, [(0, 1), (0, 2), (0, 3)]), (0,) * 4, 1, 3)
    assert result['selected'] == result['prefix_selected'] == [0]
    assert result['planned_value'] == 4.
    assert result['refinement_action_values'] == []
    assert not any(result['refinement_work'].values())
    assert_combined_ledger(result)


@pytest.mark.parametrize('days', [1, 2])
def test_short_true_horizon_keeps_original_action_and_work_even_with_ties(days):
    g, initial = graph(4), (0,) * 4
    expected = candidate.prefix_plan(g, initial, 2, days, min(2, days))
    result = candidate.plan(g, initial, 2, days)
    assert result['selected'] == expected['selected']
    assert result['planned_value'] == expected['planned_value']
    assert result['root_action_values'] == expected['root_action_values']
    assert result['prefix_work'] == expected['counters']
    assert not any(result['refinement_work'].values())
    assert_combined_ledger(result)


def test_forced_choice_keeps_shortcut_and_only_prefix_charges_it():
    result = candidate.plan(graph(3, [(0, 1), (1, 2)]), (1, 0, 0), 0, 3)
    assert result['selected'] == result['prefix_selected'] == []
    assert result['planned_value'] is None and result['root_action_values'] == []
    assert result['refinement_action_values'] == []
    assert result['counters']['forced_choice'] == 1
    assert result['counters']['kernel_builds'] == result['counters']['dp_states'] == 0
    assert_combined_ledger(result)


def test_refinement_allocates_by_real_four_day_horizon_not_three_day_window():
    result = candidate.plan(graph(5), (0,) * 5, 4, 4)
    assert result['prefix_selected'] == result['selected'] == [0]
    assert result['planned_value'] == 2.
    assert result['refinement_action_values'] == [dict(selected=[node], value=3.) for node in range(5)]
    assert_combined_ledger(result)


def test_internal_zero_budget_still_propagates_during_refinement():
    g = graph(7, [(0, 1), (1, 2), (2, 3), (4, 5), (4, 6)])
    result = candidate.plan(g, (0,) * 7, 1, 3)
    assert result['planned_value'] == 3. and result['selected'] == [0]
    refined = {tuple(row['selected']): row['value'] for row in result['refinement_action_values']}
    assert refined == {(0,): 4., (1,): 3., (4,): 3.}
    assert_combined_ledger(result)


def test_resource_stop_preserves_both_completed_decision_stages(regression_graph):
    limits = dict(max_planner_action_values=1, max_policy_states=100000, max_wall_seconds=60.)
    case, rows = candidate.evaluate(regression_graph, 540009, 'sparse', .25, 2, 3,
                                    'LOOKAHEAD_2_TIE3', limits)
    assert case['status'] == 'resource_limit' and case['stop_reason'] == 'max_planner_action_values'
    assert len(rows) == case['state_records'] == case['decision_work']['planner_calls'] == 1
    row = rows[0]
    assert row['prefix_selected'] == [1] and row['selected'] == [5]
    assert row['value'] is None and row['reach_probability'] is None
    assert case['root_value'] is None and case['root_selected'] is None
    assert case['prefix_work'] == row['prefix_work'] and case['refinement_work'] == row['refinement_work']
    assert case['prefix_work']['action_value_evaluations'] > 0
    assert case['refinement_work']['action_value_evaluations'] > 0
    assert case['decision_work']['action_value_evaluations'] == (case['prefix_work']['action_value_evaluations']
                                                              + case['refinement_work']['action_value_evaluations'])
    assert case['evaluation_work']['kernel_builds'] == case['evaluation_work']['new_full_policy_backups'] == 0
    assert all(case[name] is None for name in ('expected_decision_work', 'expected_decision_seconds',
                                              'expected_prefix_work', 'expected_refinement_work'))
