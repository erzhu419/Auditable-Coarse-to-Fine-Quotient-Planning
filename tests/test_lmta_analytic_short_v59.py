"""Window-end semantics and analytic accounting on a fixed set of hand graphs."""
from collections import Counter
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_exact_v52 import ExactAIMSolver
from acfqp.science import lmta_analytic_short_v59 as candidate
from acfqp.science import lmta_lookahead_v53 as enumerated
from acfqp.science import lmta_analytic_terminal_v56 as full


@pytest.fixture(scope='module', autouse=True)
def development_accounting(request):
    started = perf_counter()
    record = dict(solvers=[], planner_calls=Counter(), hand_graphs=0)
    original_init = ExactAIMSolver.__init__
    planners = dict(candidate=candidate.plan, enumerated=enumerated.plan, full=full.plan)
    before_failures = request.session.testsfailed

    def initialize(solver, *args, **kwargs):
        original_init(solver, *args, **kwargs)
        record['solvers'].append(solver)

    def measure(name):
        def planned(*args, **kwargs):
            record['planner_calls'][name] += 1
            return planners[name](*args, **kwargs)
        return planned

    with patch.object(ExactAIMSolver, '__init__', initialize), \
         patch.object(candidate, 'plan', measure('candidate')), \
         patch.object(enumerated, 'plan', measure('enumerated')), \
         patch.object(full, 'plan', measure('full')):
        yield record
    counts = Counter()
    for solver in record['solvers']:
        counts.update(solver.counters)
    path = Path(__file__).resolve().parents[1] / 'reports/lmta_analytic_short_v59.kernel_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_analytic_short_v59.py',
        new_failures=request.session.testsfailed - before_failures,
        environment_counters={}, model_evaluations=0, gradient_steps=0,
        hand_graph_constructions=record['hand_graphs'], sampled_graphs=0,
        planner_calls=dict(record['planner_calls']), solver_instances=len(record['solvers']),
        standalone_solver_instances=len(record['solvers']) - sum(record['planner_calls'].values()),
        all_solver_counters=dict(counts), wall_seconds=perf_counter() - started,
        scope='All actual hand-graph candidate, original short-window and original analytic-full controls are included. No main-panel replay, environment, outer policy evaluation or learned-model work.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


@pytest.fixture
def make_graph(development_accounting):
    def create(nodes, edges=()):
        development_accounting['hand_graphs'] += 1
        graph = nx.DiGraph()
        graph.add_nodes_from(range(nodes))
        graph.add_edges_from(edges)
        return graph
    return create


def assert_values(result, expected):
    assert result['selected'] == expected['selected']
    assert result['planned_value'] == pytest.approx(expected['planned_value'], rel=0, abs=1e-12)
    assert [row['selected'] for row in result['root_action_values']] == [row['selected'] for row in expected['root_action_values']]
    assert [row['value'] for row in result['root_action_values']] == pytest.approx(
        [row['value'] for row in expected['root_action_values']], rel=0, abs=1e-12)


@pytest.mark.parametrize('depth', [1, 2])
def test_window_end_retains_real_three_day_budget_allocation_and_costs(depth, make_graph):
    graph = make_graph(5)
    result = candidate.plan(graph, (0,) * 5, 3, 3, depth)
    reference = enumerated.plan(graph, (0,) * 5, 3, 3, depth)
    assert_values(result, reference)
    assert result['selected'] == [0] and result['planned_value'] == float(depth)
    assert result['root_action_values'] == [dict(selected=[node], value=float(depth)) for node in range(5)]
    counts = result['counters']
    assert counts['dp_states'] == reference['counters']['dp_states']
    assert counts['action_value_evaluations'] == reference['counters']['action_value_evaluations']
    assert counts['target_probability_evaluations'] == reference['counters']['target_probability_evaluations']
    assert counts['action_value_evaluations'] == (counts['kernel_builds'] + counts['kernel_cache_hits']
                                               + counts['analytic_expectation_calls'])
    assert counts['kernel_builds'] == (0 if depth == 1 else 5)
    assert counts['analytic_expectation_calls'] == (5 if depth == 1 else 20)
    assert counts['analytic_probability_terms'] == (20 if depth == 1 else 60)


def test_last_window_reward_merges_parent_probabilities_without_old_activity_reward(make_graph):
    graph = make_graph(5, [(0, 3), (1, 3), (2, 3), (4, 3)])
    state = (1, 0, 2, 0, 0)
    with patch.object(ExactAIMSolver, 'kernel', side_effect=AssertionError('last-window kernel called')):
        result = candidate.plan(graph, state, 1, 3, 1)
    reference = enumerated.plan(graph, state, 1, 3, 1)
    assert_values(result, reference)
    assert result['selected'] == [1] and result['planned_value'] == 1.4375
    assert result['root_action_values'] == [dict(selected=[1], value=1.4375),
                                          dict(selected=[3], value=1.), dict(selected=[4], value=1.4375)]
    assert result['counters']['analytic_expectation_calls'] == 3
    assert result['counters']['analytic_probability_terms'] == 6
    assert result['counters']['kernel_builds'] == result['counters']['transition_outcomes'] == 0


def test_internal_exhausted_budget_keeps_the_second_day_propagation(make_graph):
    graph = make_graph(4, [(0, 1), (1, 2), (2, 3)])
    result = candidate.plan(graph, (0,) * 4, 1, 3, 2)
    reference = enumerated.plan(graph, (0,) * 4, 1, 3, 2)
    assert_values(result, reference)
    assert result['selected'] == [0] and result['planned_value'] == 3.
    assert result['root_action_values'] == [dict(selected=[0], value=3.), dict(selected=[1], value=3.),
                                          dict(selected=[2], value=2.), dict(selected=[3], value=1.)]
    assert result['counters']['analytic_expectation_calls'] == 4
    assert result['counters']['kernel_builds'] == 4


def test_depth_beyond_horizon_matches_frozen_analytic_full_including_counters(make_graph):
    graph = make_graph(5, [(0, 2), (1, 2), (2, 3), (3, 4), (0, 4)])
    result = candidate.plan(graph, (0,) * 5, 2, 3, 5)
    reference = full.plan(graph, (0,) * 5, 2, 3)
    assert result == reference


def test_forced_root_shortcut_needs_neither_kernel_nor_analytic_work(make_graph):
    graph = make_graph(3, [(0, 1), (1, 2)])
    for state, budget, selected in [((1, 0, 0), 0, []), ((2, 2, 0), 1, [2]), ((2, 2, 2), 1, [])]:
        result = candidate.plan(graph, state, budget, 3, 2)
        assert result['selected'] == selected and result['planned_value'] is None
        assert result['root_action_values'] == [] and result['counters']['forced_choice'] == 1
        assert all(value == 0 for name, value in result['counters'].items() if name != 'forced_choice')
