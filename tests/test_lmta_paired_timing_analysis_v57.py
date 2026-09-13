"""Synthetic ledgers only: no graph generation, environment, or planner calls."""
import copy
import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('timing_analysis_v57', ROOT / 'scripts/analyze_lmta_paired_timing_v57.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def source_row(index=0, graph=550000, nodes=7, method=A.FULL):
    status, number = [], index
    for _ in range(nodes):
        status.append(number % 3)
        number //= 3
    return dict(graph_id=graph, method=method, statuses=status,
        remaining_budget=2, remaining_days=3 if index == 0 else 1,
        reach_probability=1. if index == 0 else .001,
        decision_work=dict(planner_calls=1, action_value_evaluations=2, dp_states=1,
                           kernel_builds=2, kernel_cache_hits=0, transition_outcomes=3))


def case_for(rows, method=A.FULL, durations=None, cleanup=.002, **identity):
    durations = durations or [.001] * len(rows)
    seconds = math.fsum(durations)
    work = A.Counter()
    for row in rows:
        work.update(row['decision_work'])
    return dict(graph_id=550000, nodes=7, stratum='sparse', p=.25, budget=2, horizon=3,
        method=method, phase='measured', repetition=0, position=0,
        status='complete', stop_reason=None, source_state_records=len(rows), query_count=len(rows),
        query_seconds=durations, decision_work=dict(work), output_mismatches=[],
        prepare_gc_seconds=.003, decision_seconds=seconds, cleanup_seconds=cleanup,
        decision_total_seconds=seconds + cleanup, bookkeeping_seconds=.004,
        loop_seconds=seconds + .004, block_seconds=seconds + .004 + cleanup,
        last_limit_check_seconds=seconds + .003,
        source_weighted_planning_seconds=math.fsum(row['reach_probability'] * time for row, time in zip(rows, durations))) | identity


@pytest.fixture(scope='module')
def package():
    graphs, source = [], {method: [] for method in A.METHODS}
    source_by_graph = {method: {} for method in A.METHODS}
    for panel in A.PANELS:
        for graph in panel['seeds']:
            graphs.append(dict(graph_id=graph, nodes=panel['nodes'], stratum=panel['stratum'],
                               expected_degree=panel['expected_degree'], p=panel['p'], edges=[], panel='fresh'))
            count = 315 if graph < 550100 else 314
            for method in A.METHODS:
                rows = [source_row(i, graph, panel['nodes'], method) for i in range(count)]
                source_by_graph[method][graph] = rows
                source[method].extend(rows)
    assert len(source[A.FULL]) == 20112
    metadata = {row['graph_id']: row for row in graphs}
    cases = []
    for phase, repetition, graph, method, position in A.expected_order():
        rows = source_by_graph[method][graph]
        rows = rows[:1] if phase == 'warmup' else rows
        meta = {key: metadata[graph][key] for key in ('graph_id', 'nodes', 'stratum', 'p')}
        cases.append(case_for(rows, method, [.001 if method == A.FULL else .0008] * len(rows),
                              phase=phase, repetition=repetition, position=position, **meta))
    manifest = dict(schema='acfqp.lmta_paired_timing.v57', status='complete', protocol=A.PROTOCOL,
        source_directories=A.SOURCE_DIRS, graphs=graphs, cold_decisions=True, runtime=dict(gc_enabled=True),
        source_state_records=20112, completed_blocks=778, completed_measured_blocks=768,
        completed_warmup_blocks=10, successful_blocks=778, resource_limited_blocks=0,
        total_query_count=241354, source_read_seconds=.1, graph_reconstruction_seconds=.2,
        data_output_seconds=.3, whole_runner_seconds=300., runner_cpu_seconds=280.,
        process_peak_rss_bytes=10000000, data_bytes={'cases.jsonl': 100000},
        new_graphs=0, new_environment_samples=0, new_environment_calls=0, new_RL_updates=0,
        new_MCTS_calls=0, new_full_policy_evaluations=0, new_independent_DP_checks=0)
    old_manifest = dict(schema='acfqp.lmta_tie_refinement.v55', status='complete', graphs=graphs)
    new_manifest = dict(schema='acfqp.lmta_analytic_terminal.v56', status='complete', graphs=graphs,
                        source_full_state_records=20112)
    old_analysis = dict(integrity=dict(passed=True), fresh_complete_quality_evidence=True, accounting={'old_seconds': 100.})
    new_analysis = dict(integrity=dict(passed=True), policy_value_preserved_all=True, accounting={'old_seconds': 50.})
    return manifest, cases, old_manifest, old_analysis, source[A.FULL], new_manifest, new_analysis, source[A.ANALYTIC]


def test_full_frozen_sequence_and_separate_warmup_accounting(package):
    report = A.summarize(*package)
    assert report['integrity']['passed'], report['integrity']
    assert report['complete_performance_evidence']
    assert report['accounting']['warmup']['query_records'] == 10
    assert report['accounting']['measured']['query_records'] == 241344
    assert report['accounting']['all_blocks']['query_records'] == 241354
    assert report['accounting']['runner']['data_output_seconds'] == .3
    assert report['retained_source_accounting']['control'] == {'old_seconds': 100.}
    assert all('query_seconds' not in row for row in report['block_validation'])
    for stratum in report['strata']:
        assert len(stratum['repetitions']) == 6
        assert stratum['six_round_summary']['primary_ratio']['available_rounds'] == 6
        assert all(row['graph_pairs'] == 8 for row in stratum['order_effects']['FULL_then_ANALYTIC']['repetitions'])
        assert all(row['graph_pairs'] == 8 for row in stratum['order_effects']['ANALYTIC_then_FULL']['repetitions'])


@pytest.mark.parametrize('field', ['decision_work', 'decision_total_seconds', 'output_mismatches'])
def test_drift_or_mischarged_cleanup_is_invalid_but_costs_remain(field):
    source = [source_row()]
    case = case_for(source)
    if field == 'decision_work':
        case[field]['action_value_evaluations'] += 1
    elif field == 'decision_total_seconds':
        case[field] = case['decision_seconds']
    else:
        case[field] = [dict(query_index=0, field='selected', expected=[0], actual=[1])]
    assert not A.verify_case(case, source, [1.])['passed']
    fees = A.accounting([case])
    assert fees['query_records'] == 1
    assert fees['cleanup_seconds'] == .002


def test_postdecision_limit_charges_only_retained_prefix_and_cleanup():
    rows = [source_row(), source_row(1)]
    case = case_for(rows[:1])
    case.update(source_state_records=2, status='resource_limit', stop_reason='max_policy_states',
                source_weighted_planning_seconds=None)
    result = A.verify_case(case, rows, [1., .001], dict(A.LIMITS, max_policy_states=1))
    assert result['passed'], result
    assert A.accounting([case])['decision_work']['planner_calls'] == 1
    assert A.accounting([case])['decision_total_seconds'] == .003
    case['decision_work']['action_value_evaluations'] += 2
    assert not A.verify_case(case, rows, [1., .001], dict(A.LIMITS, max_policy_states=1))['passed']


def test_ratios_use_sums_and_cleanup_not_mean_query_ratios():
    pairs = []
    for full, analytic in ((1., 2.), (9., 3.)):
        pairs.append({A.FULL: dict(decision_total_seconds=full, block_seconds=full + 1,
                                   source_weighted_planning_seconds=full),
                      A.ANALYTIC: dict(decision_total_seconds=analytic, block_seconds=analytic + 2,
                                       source_weighted_planning_seconds=analytic)})
    result = A.paired_round(pairs)
    assert result['primary_ratio'] == .5
    assert result['primary_ratio'] != (2. + 3. / 9.) / 2
    assert result['absolute_saved_seconds'] == 5.
    assert result['block_ratio'] == .75
    source = [source_row()]
    full, analytic = case_for(source, durations=[1.], cleanup=.1), case_for(source, durations=[.9], cleanup=.4)
    result = A.paired_round([{A.FULL: full, A.ANALYTIC: analytic}])
    assert result['primary_ratio'] > 1 > result['source_weighted_planning_ratio']


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'wrong_order', 'source_not_preserved'])
def test_binding_failures_suppress_performance_without_refunding_actual_work(package, mutation):
    args = list(package)
    args[0] = copy.deepcopy(args[0])
    args[1] = list(args[1])
    if mutation == 'missing':
        args[1].pop()
    elif mutation == 'duplicate':
        args[1].append(args[1][-1])
    elif mutation == 'wrong_order':
        args[1][10], args[1][11] = args[1][11], args[1][10]
    else:
        args[6] = dict(args[6], policy_value_preserved_all=False)
    report = A.summarize(*args)
    assert not report['integrity']['passed']
    assert not report['complete_performance_evidence']
    assert all(row['repetitions'] is None for row in report['strata'])
    assert report['accounting']['all_blocks']['query_records'] == sum(len(row['query_seconds']) for row in args[1])
    assert report['accounting']['all_blocks']['cleanup_seconds'] > 0


def test_partial_stratum_has_no_performance_but_other_complete_strata_remain(package):
    args = list(package)
    args[0] = copy.deepcopy(args[0])
    args[1] = list(args[1])
    row = copy.deepcopy(args[1][10])
    # A completed final query can itself meet the soft time limit; all its costs remain paid.
    row.update(status='resource_limit', stop_reason='max_wall_seconds', last_limit_check_seconds=60.,
               source_weighted_planning_seconds=None, loop_seconds=60.1,
               bookkeeping_seconds=60.1-row['decision_seconds'], block_seconds=60.1+row['cleanup_seconds'])
    args[1][10] = row
    args[0].update(successful_blocks=777, resource_limited_blocks=1)
    report = A.summarize(*args)
    assert report['integrity']['passed'], report['integrity']
    assert report['strata'][0]['repetitions'] is None
    assert all(row['complete_performance_evidence'] for row in report['strata'][1:])
    assert report['accounting']['all_blocks']['resource_limited_cases'] == 1
