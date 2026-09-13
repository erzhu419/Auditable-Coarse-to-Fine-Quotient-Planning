"""Cold invocation and timing boundaries on small hand graphs and mock clocks."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import pytest

from acfqp.science.lmta_exact_v52 import ExactAIMSolver
from acfqp.science import lmta_paired_timing_v57 as timing


LIMITS = dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.)


@pytest.fixture(scope='module', autouse=True)
def development_accounting(request):
    started = perf_counter()
    record = dict(solvers=[], planner_calls=Counter(), real_collections=0,
                  mock_collections=0, mock_clock_blocks=0)
    original_init, original_collect = ExactAIMSolver.__init__, timing.gc.collect
    original_full, original_analytic = timing.full_plan, timing.analytic_plan
    before_failures = request.session.testsfailed

    def initialize(solver, *args, **kwargs):
        original_init(solver, *args, **kwargs)
        record['solvers'].append(solver)

    def full_plan(*args, **kwargs):
        record['planner_calls']['LOOKAHEAD_FULL'] += 1
        return original_full(*args, **kwargs)

    def analytic_plan(*args, **kwargs):
        record['planner_calls']['LOOKAHEAD_FULL_ANALYTIC'] += 1
        return original_analytic(*args, **kwargs)

    def collect():
        record['real_collections'] += 1
        return original_collect()

    with patch.object(ExactAIMSolver, '__init__', initialize), \
         patch.object(timing, 'full_plan', full_plan), patch.object(timing, 'analytic_plan', analytic_plan), \
         patch.object(timing.gc, 'collect', collect):
        yield record
    counts = Counter()
    for solver in record['solvers']:
        counts.update(solver.counters)
    path = Path(__file__).resolve().parents[1] / 'reports/lmta_paired_timing_v57.kernel_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    report['attempts'].append(dict(test_module='tests/test_lmta_paired_timing_v57.py',
        new_failures=request.session.testsfailed - before_failures,
        environment_counters={}, model_evaluations=0, gradient_steps=0,
        planner_calls=dict(record['planner_calls']), solver_instances=len(record['solvers']),
        all_solver_counters=dict(counts), real_collector_calls=record['real_collections'],
        mock_collector_calls=record['mock_collections'], mock_clock_blocks=record['mock_clock_blocks'],
        wall_seconds=perf_counter() - started,
        scope='Every planner and hand-reference call executes the original solver and is charged. Mock clock/collector blocks test accounting identities, not performance; only wall_seconds is actual total test time. No main-panel benchmark, environment call or outer policy evaluation.'))
    path.write_text(json.dumps(report, indent=2) + '\n')


def graph_and_query(method):
    graph = nx.DiGraph()
    graph.add_nodes_from(range(3))
    graph.add_edges_from([(0, 2), (1, 2)])
    planner = timing.full_plan if method == 'LOOKAHEAD_FULL' else timing.analytic_plan
    args = (graph, (0, 0, 0), 1, 1, 1) if method == 'LOOKAHEAD_FULL' else (graph, (0, 0, 0), 1, 1)
    result = planner(*args)
    reference = dict(statuses=[0, 0, 0], remaining_budget=1, remaining_days=1,
        reach_probability=1., selected=result['selected'], planned_value=result['planned_value'],
        decision_work=dict(planner_calls=1, **result['counters']))
    return graph, reference


def identity(phase):
    return dict(graph_id=-1, nodes=3, stratum='hand', p=.5, budget=1, horizon=1,
                repetition=0, position=0, phase=phase)


@pytest.mark.parametrize('method', ['LOOKAHEAD_FULL', 'LOOKAHEAD_FULL_ANALYTIC'])
@pytest.mark.parametrize('phase', ['warmup', 'measured'])
def test_identical_cold_boundaries_with_mocked_time_and_collector(method, phase, development_accounting):
    record = development_accounting
    graph, reference = graph_and_query(method)
    second = deepcopy(reference)
    second['reach_probability'] = .25
    events = []
    name = 'full_plan' if method == 'LOOKAHEAD_FULL' else 'analytic_plan'
    original = getattr(timing, name)

    def planner(*args):
        assert timing.gc.isenabled()
        events.append('plan')
        return original(*args)

    def collect():
        events.append('collect')
        record['mock_collections'] += 1
        return 0

    before = len(record['solvers'])
    record['mock_clock_blocks'] += 1
    # prepare 2, plan [3,5], loop 15, cleanup 7, bookkeeping 7.
    clock = [0., 2., 10., 11., 14., 15., 17., 22., 24., 25., 25., 32.]
    with patch.object(timing, 'perf_counter', side_effect=clock), \
         patch.object(timing.gc, 'collect', collect), patch.object(timing, name, planner):
        case = timing.measure(graph, identity(phase), [reference, second], method, LIMITS)
    assert len(record['solvers']) - before == 2
    assert events == ['collect', 'plan', 'plan', 'collect']
    assert case['phase'] == phase and case['status'] == 'complete'
    assert case['query_seconds'] == [3., 5.] and case['query_count'] == 2
    assert case['output_mismatches'] == []
    assert case['prepare_gc_seconds'] == 2. and case['cleanup_seconds'] == 7.
    assert case['loop_seconds'] == 15. and case['decision_seconds'] == 8.
    assert case['decision_total_seconds'] == 15. and case['bookkeeping_seconds'] == 7.
    assert case['block_seconds'] == 22. and case['source_weighted_planning_seconds'] == 4.25
    assert case['last_limit_check_seconds'] == 14.
    assert case['decision_work'] == {name: 2 * count for name, count in reference['decision_work'].items()}


def test_output_drift_is_recorded_for_all_fields_without_hiding_paid_work():
    graph, reference = graph_and_query('LOOKAHEAD_FULL')
    wrong = deepcopy(reference)
    wrong['selected'] = [2]
    wrong['planned_value'] += 1.
    wrong['decision_work']['action_value_evaluations'] += 1
    case = timing.measure(graph, identity('measured'), [wrong], 'LOOKAHEAD_FULL', LIMITS)
    assert case['status'] == 'complete' and case['query_count'] == 1
    assert {row['field'] for row in case['output_mismatches']} == {'selected', 'planned_value', 'decision_work'}
    assert all(row['query_index'] == 0 for row in case['output_mismatches'])
    for row in case['output_mismatches']:
        assert row['expected'] == wrong[row['field']]
        assert row['actual'] == reference[row['field']]
    assert case['decision_work'] == reference['decision_work']
    assert case['decision_total_seconds'] == case['decision_seconds'] + case['cleanup_seconds']
    assert case['block_seconds'] == case['loop_seconds'] + case['cleanup_seconds']


@pytest.mark.parametrize('actions,states,reason', [(1, 1, 'max_planner_action_values'),
    (100, 1, 'max_policy_states'), (100, 100, 'max_wall_seconds')])
def test_partial_block_charges_completed_query_cleanup_and_retains_mismatches(
        actions, states, reason, development_accounting):
    record = development_accounting
    graph, reference = graph_and_query('LOOKAHEAD_FULL_ANALYTIC')
    wrong = deepcopy(reference)
    wrong['planned_value'] += 1.
    limits = dict(max_planner_action_values=actions, max_policy_states=states, max_wall_seconds=1.)

    def collect():
        record['mock_collections'] += 1
        return 0

    record['mock_clock_blocks'] += 1
    clock = [0., 1., 10., 11., 13., 15., 16., 16., 20.]
    with patch.object(timing, 'perf_counter', side_effect=clock), patch.object(timing.gc, 'collect', collect):
        case = timing.measure(graph, identity('measured'), [wrong, reference],
                              'LOOKAHEAD_FULL_ANALYTIC', limits)
    assert case['status'] == 'resource_limit' and case['stop_reason'] == reason
    assert case['source_state_records'] == 2 and case['query_count'] == 1
    assert case['query_seconds'] == [2.] and case['decision_work'] == reference['decision_work']
    assert case['source_weighted_planning_seconds'] is None
    assert case['output_mismatches'] == [dict(query_index=0, field='planned_value',
        expected=wrong['planned_value'], actual=reference['planned_value'])]
    assert case['last_limit_check_seconds'] == 5.
    assert case['cleanup_seconds'] == 4. and case['decision_total_seconds'] == 6.
    assert case['loop_seconds'] == 6. and case['block_seconds'] == 10.
