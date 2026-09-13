"""Hand-derived replay checks; no new graph generation, solver or environment."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
from time import perf_counter

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('analytic_terminal_analysis_v56', ROOT / 'scripts/analyze_lmta_analytic_terminal_v56.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)
EDGES = [(0, 2), (1, 2)]


@pytest.fixture(scope='session', autouse=True)
def record_work(request):
    started, work = perf_counter(), Counter()
    original = analysis.v53.independent_plan
    def wrapped(*args, **kwargs):
        work['independent_full_plan_calls'] += 1
        return original(*args, **kwargs)
    analysis.v53.independent_plan = wrapped
    yield
    analysis.v53.independent_plan = original
    path = ROOT / 'reports/lmta_analytic_terminal_v56.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    record['attempts'].append(dict(test_module='tests/test_lmta_analytic_terminal_analysis_v56.py',
        passed=len(request.session.items) - request.session.testsfailed, failed=request.session.testsfailed,
        wall_seconds=perf_counter() - started, independent_checker_calls=dict(work),
        environment_calls=0, neural_model_evaluations=0, gradient_steps=0, new_full_policy_evaluations=0,
        scope='Only hand-derived small replay records and independent finite-horizon decision checks; no main-panel queries.'))
    path.write_text(json.dumps(record, indent=2) + '\n')


def totals(rows, field='decision_work', weight=False):
    result = Counter()
    for row in rows:
        result.update({name: number * (row['reach_probability'] if weight else 1) for name, number in row[field].items()})
    return dict(result)


def fixture():
    common = dict(graph_id=1, nodes=3, stratum='sparse', p=.25, budget=1, horizon=2)
    old_work = dict(planner_calls=1, forced_choice=0, dp_states=6, action_value_evaluations=8,
        kernel_builds=8, kernel_cache_hits=0, transition_outcomes=10, target_probability_evaluations=14,
        bellman_expectation_terms=10)
    old_rows = [dict(**common, method=analysis.SOURCE_METHOD, statuses=[0, 0, 0], remaining_budget=1, remaining_days=2,
        value=1.5, selected=[0], reach_probability=1., planned_value=1.5,
        root_action_values=[dict(selected=[node], value=value) for node, value in enumerate((1.5, 1.5, 1.))],
        decision_work=old_work, decision_seconds=.3)]
    for status in ([2, 0, 0], [2, 0, 1]):
        old_rows.append(dict(**common, method=analysis.SOURCE_METHOD, statuses=status, remaining_budget=0, remaining_days=1,
            value=0., selected=[], reach_probability=.5, planned_value=None, root_action_values=[],
            decision_work=dict.fromkeys(old_work, 0) | {'planner_calls': 1, 'forced_choice': 1}, decision_seconds=.2))
    old_case = dict(**common, method=analysis.SOURCE_METHOD, status='complete', root_value=1.5, root_selected=[0],
        state_records=3, decision_work=totals(old_rows), expected_decision_work=totals(old_rows, weight=True),
        decision_seconds=.7, expected_decision_seconds=.5)
    rows = []
    for index, old in enumerate(old_rows):
        row = {key: deepcopy(value) for key, value in old.items() if key not in ('value', 'reach_probability')}
        row.update(method=analysis.METHOD, source_method=analysis.SOURCE_METHOD, decision_seconds=.1 if index == 0 else .01)
        row['decision_work'].update(analytic_expectation_calls=5 if index == 0 else 0,
            analytic_probability_terms=8 if index == 0 else 0,
            kernel_builds=3 if index == 0 else 0, transition_outcomes=5 if index == 0 else 0,
            bellman_expectation_terms=5 if index == 0 else 0)
        rows.append(row)
    weighted_rows = [dict(row, reach_probability=old['reach_probability']) for row, old in zip(rows, old_rows)]
    case = dict(**common, method=analysis.METHOD, source_method=analysis.SOURCE_METHOD, status='complete', stop_reason=None,
        source_state_records=3, state_records=3, decision_work=totals(rows), source_weighted_decision_work=totals(weighted_rows, weight=True),
        decision_seconds=.12, source_weighted_decision_seconds=.11, replay_seconds=.3, replay_overhead_seconds=.18,
        last_limit_check_seconds=.2, serialization_seconds=.01)
    return case, rows, old_case, old_rows


def test_complete_replay_preserves_values_and_conditions_policy_cost_interpretation():
    case, rows, old_case, old_rows = fixture()
    checked = analysis.verify_case(case, rows, old_case, old_rows, EDGES, 3)
    assert checked['passed'] and checked['policy_value_preserved'], checked
    assert checked['exact_action_matches'] == 3 and checked['candidate_policy_value'] == 1.5
    panel = dict(nodes=3, stratum='sparse', p=.25, seeds=[1])
    summary = analysis.stratum_summary(panel, [case], [old_case], [checked], True)
    assert summary['complete_fixed_query_workload'] and summary['policy_value_preserved']
    assert summary['fixed_query_workload_ratios']['actual_work']['kernel_builds'] == 3 / 8
    assert summary['preserved_policy_decision_cost_ratios']['seconds'] == pytest.approx(.22)


def test_tiny_reported_rounding_change_is_valid_but_breaks_action_preservation():
    case, rows, old_case, old_rows = fixture()
    rows[0]['root_action_values'][1]['value'] = math.nextafter(1.5, math.inf)
    rows[0].update(selected=[1], planned_value=rows[0]['root_action_values'][1]['value'])
    checked = analysis.verify_case(case, rows, old_case, old_rows, EDGES, 3)
    assert checked['passed'] and checked['value_agreement'], checked
    assert checked['root_action_changes'] == 1 and not checked['action_preserved']
    assert checked['candidate_policy_value'] is None and not checked['policy_value_preserved']
    panel = dict(nodes=3, stratum='sparse', p=.25, seeds=[1])
    summary = analysis.stratum_summary(panel, [case], [old_case], [checked], True)
    assert summary['fixed_query_workload_ratios'] is not None
    assert summary['preserved_policy_decision_cost_ratios'] is None


@pytest.mark.parametrize('failure,error', [('Q', 'Q_and_source_value_tolerance'),
    ('strict_choice', 'reported_strict_choice'), ('work_partition', 'action_value_work_partition'),
    ('search_scope', 'unchanged_search_scope')])
def test_invalid_values_selection_or_work_are_not_preservation_evidence(failure, error):
    case, rows, old_case, old_rows = fixture()
    row = rows[0]
    if failure == 'Q':
        row['root_action_values'][0]['value'] += .1
        row['planned_value'] += .1
    elif failure == 'strict_choice':
        row['selected'] = [1]  # Exact retained tie requires the lowest-index action.
    elif failure == 'work_partition':
        row['decision_work']['analytic_expectation_calls'] -= 1
    else:
        row['decision_work']['dp_states'] += 1
    checked = analysis.verify_case(case, rows, old_case, old_rows, EDGES, 3)
    assert not checked['passed'] and checked['errors'][error] > 0
    assert checked['candidate_policy_value'] is None
    assert analysis.costs([case])['decision_seconds'] == .12


def test_resource_stop_keeps_paid_queries_without_partial_workload_ratios():
    case, rows, old_case, old_rows = fixture()
    rows = rows[:1]
    case.update(status='resource_limit', stop_reason='max_policy_states', state_records=1,
        decision_work=totals(rows), source_weighted_decision_work=None, source_weighted_decision_seconds=None,
        decision_seconds=.1, replay_overhead_seconds=.2)
    checked = analysis.verify_case(case, rows, old_case, old_rows, EDGES, 3, dict(analysis.LIMITS, max_policy_states=1))
    assert checked['passed'] and not checked['policy_value_preserved'], checked
    assert checked['candidate_policy_value'] is None and checked['exact_action_matches'] == 1
    panel = dict(nodes=3, stratum='sparse', p=.25, seeds=[1])
    summary = analysis.stratum_summary(panel, [case], [old_case], [checked], True)
    assert summary['fixed_query_workload_ratios'] is summary['preserved_policy_decision_cost_ratios'] is None
    assert summary['new_costs']['decision_work']['analytic_expectation_calls'] == 5


def test_terminal_analytic_query_has_no_kernel_or_outcome_enumeration():
    case, rows, old_case, old_rows = fixture()
    old, row = old_rows[0], rows[0]
    for item in (old, row):
        item.update(remaining_days=1, horizon=1)
    old['decision_work'].update(dp_states=1, action_value_evaluations=3, kernel_builds=3,
        transition_outcomes=5, target_probability_evaluations=6, bellman_expectation_terms=5)
    row['decision_work'].update(dp_states=1, action_value_evaluations=3, analytic_expectation_calls=3,
        analytic_probability_terms=6, target_probability_evaluations=6, kernel_builds=0,
        transition_outcomes=0, bellman_expectation_terms=0)
    report = analysis.verify_row(row, old, EDGES, 3)
    assert report['passed'], report
