"""Hand-derived records and limit boundaries only; no environments or main panel."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('scale_analysis_v54', ROOT / 'scripts/analyze_lmta_scale_v54.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def certificate(method='LOOKAHEAD_2'):
    common = dict(graph_id=1, horizon=2, method=method, nodes=3, stratum='sparse', p=.25, budget=1)
    rows = [dict(**common, statuses=[0, 0, 0], remaining_budget=1, remaining_days=2,
        selected=[0], value=1.5, reach_probability=1., planned_value=1.5,
        root_action_values=[dict(selected=[node], value=value) for node, value in enumerate((1.5, 1.5, 1.))],
        decision_seconds=.1, decision_work=dict(planner_calls=1, forced_choice=0, action_value_evaluations=3))]
    for statuses, seconds in (([2, 0, 0], .2), ([2, 0, 1], .3)):
        rows.append(dict(**common, statuses=statuses, remaining_budget=0, remaining_days=1,
            selected=[], value=0., reach_probability=.5, planned_value=None, root_action_values=[],
            decision_seconds=seconds, decision_work=dict(planner_calls=1, forced_choice=1, action_value_evaluations=0)))
    work = Counter()
    for row in rows:
        work.update(row['decision_work'])
    case = dict(**common, status='complete', stop_reason=None, root_value=1.5, root_selected=[0],
        value_source='V54_full_policy_evaluation', control_method=None, state_records=3,
        decision_work=dict(work), expected_decision_work={name: sum(row['reach_probability'] * row['decision_work'][name]
            for row in rows) for name in work}, expected_decision_seconds=.35,
        decision_seconds=.6, evaluation_seconds=.4, wall_seconds=1., serialization_seconds=.02,
        last_limit_check_seconds=.7, evaluation_work=dict(new_full_policy_backups=3,
            retained_value_reads=0, occupancy_probability_terms=2))
    return case, rows, [(0, 2), (1, 2)], 3


def interrupted(reason='max_planner_action_values'):
    case, rows, edges, nodes = certificate()
    rows = rows[:1]
    rows[0].update(value=None, reach_probability=None)
    limits = deepcopy(analysis.LIMITS)
    if reason == 'max_planner_action_values':
        rows[0]['decision_work']['action_value_evaluations'] = limits[reason] + 7
    elif reason == 'max_policy_states':
        limits[reason] = 1
    else:
        case['last_limit_check_seconds'] = limits[reason]
        case.update(wall_seconds=60.1, evaluation_seconds=60.)
    if reason != 'max_wall_seconds':
        case.update(last_limit_check_seconds=.15, wall_seconds=.2, evaluation_seconds=.1)
    case.update(status='resource_limit', stop_reason=reason, root_value=None, root_selected=None,
        state_records=1, decision_work=deepcopy(rows[0]['decision_work']), decision_seconds=.1,
        expected_decision_work=None, expected_decision_seconds=None,
        evaluation_work=dict(new_full_policy_backups=0, retained_value_reads=0, occupancy_probability_terms=0))
    return case, rows, edges, nodes, limits


@pytest.mark.parametrize('method', analysis.METHODS)
def test_all_three_methods_use_new_full_policy_certificates(method):
    checked = analysis.verify_case(*certificate(method))
    assert checked['passed'] and checked['quality_verified'], checked
    assert checked['full_policy_equations'] == 3
    assert checked['planned_roots'] == 1 and checked['forced_roots'] == 2


def test_complete_case_uses_the_last_check_not_final_wall_to_enforce_time_limit():
    inputs = certificate()
    inputs[0].update(last_limit_check_seconds=59., wall_seconds=61., evaluation_seconds=60.4)
    report = analysis.verify_case(*inputs)
    assert report['passed'] and report['quality_verified'], report


@pytest.mark.parametrize('reason', list(analysis.LIMITS))
def test_each_limit_retains_the_whole_overshooting_decision_without_quality(reason):
    inputs = interrupted(reason)
    report = analysis.verify_case(*inputs)
    assert report['passed'] and not report['quality_verified'], report
    costs = analysis.case_accounting([inputs[0]])
    assert costs['decision_work'] == inputs[0]['decision_work']
    assert costs['decision_seconds'] == .1 and costs['expected_decision_work'] is None
    assert costs['resource_limited_cases'] == 1
    if reason == 'max_planner_action_values':
        assert costs['decision_work']['action_value_evaluations'] == 2000007


def test_false_resource_reason_is_invalid_but_actual_costs_remain():
    inputs = interrupted()
    inputs[0]['stop_reason'] = 'max_policy_states'
    checked = analysis.verify_case(*inputs)
    assert not checked['passed'] and checked['errors']['limit_boundary_and_reason'] == 1
    assert analysis.case_accounting([inputs[0]])['decision_work']['action_value_evaluations'] == 2000007


def test_resource_limit_still_checks_the_retained_paid_decision():
    inputs = interrupted()
    inputs[1][0]['root_action_values'][0]['value'] += .1
    checked = analysis.verify_case(*inputs)
    assert not checked['passed'] and checked['errors']['truncated_action_values'] == 1
    assert checked['planned_roots'] == 1 and checked['full_policy_equations'] == 0
    assert not checked['quality_verified']
    assert analysis.case_accounting([inputs[0]])['decision_work']['action_value_evaluations'] == 2000007


def test_one_limited_graph_invalidates_the_whole_stratum_not_only_its_own_row():
    panel = dict(nodes=7, stratum='sparse', expected_degree=1.5, p=.25, seeds=[101, 102])
    cases = []
    for graph, values in ((101, (4., 3.5, 5.)), (102, (2., 2., 2.))):
        for method, value in zip(analysis.METHODS, values):
            case = certificate(method)[0]
            case.update(graph_id=graph, root_value=value)
            cases.append(case)
    complete = analysis.stratum_summary(panel, cases, True)
    assert complete['quality_complete']
    assert complete['contrasts']['candidate_minus_myopic']['mean'] == -.25
    assert complete['contrasts']['candidate_minus_myopic']['negative_count'] == 1
    assert complete['contrasts']['headroom_fraction']['null_count'] == 1
    assert complete['sum_gain_over_sum_headroom'] == -.5
    cases[-1].update(status='resource_limit', root_value=None, expected_decision_work=None, expected_decision_seconds=None)
    partial = analysis.stratum_summary(panel, cases, True)
    assert not partial['quality_complete']
    assert partial['values'] is partial['contrasts'] is partial['per_graph'] is partial['sum_gain_over_sum_headroom'] is None
    assert partial['terminal_cases'] == 6 and partial['resource_limited_cases'] == 1
    assert partial['costs_by_method']['LOOKAHEAD_FULL']['case_records'] == 2
    assert partial['costs_by_method']['LOOKAHEAD_FULL']['wall_seconds'] == 2.


def test_partial_logs_preserve_work_without_claiming_complete_execution_or_evidence():
    case, rows, edges, _ = certificate()
    manifest = dict(schema='acfqp.lmta_scale.v54', status='complete', protocol=deepcopy(analysis.PROTOCOL),
        source_directory='reports/lmta_lookahead_v53', cold_decisions=True,
        graphs=[dict(graph_id=1, nodes=3, stratum='sparse', expected_degree=1.5, p=.25, edges=edges)],
        completed_cases=1, successful_cases=1, resource_limited_cases=0, total_state_records=3,
        new_environment_samples=0, new_environment_calls=0, new_RL_updates=0, new_MCTS_calls=0,
        source_read_seconds=.1, graph_generation_seconds=.1, whole_runner_seconds=1.5,
        runner_cpu_seconds=1.4, process_peak_rss_bytes=1000)
    old = dict(integrity={'passed': True}, accounting={'whole_runner_seconds': 12.})
    report = analysis.summarize(manifest, [case], rows, old)
    assert not report['integrity']['passed'] and not report['integrity']['terminal_execution_complete']
    assert not report['complete_quality_evidence']
    assert all(row['values'] is row['contrasts'] is None for row in report['strata'])
    assert report['accounting']['new_cases']['wall_seconds'] == 1.
    assert report['accounting']['retained_V53'] == old['accounting']
