"""Hand-derived small graph records; no solver, environment, or main-panel calls."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location('lookahead_analysis_v53',
    Path(__file__).resolve().parents[1] / 'scripts/analyze_lmta_lookahead_v53.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def certificate(method='LOOKAHEAD_2'):
    # Full target indegree is two: seeding node 0 yields reward 1 or 2 with equal probability.
    common = dict(graph_id=1, horizon=2, method=method)
    rows = [dict(**common, statuses=[0, 0, 0], remaining_budget=1, remaining_days=2,
        selected=[0], value=1.5, reach_probability=1., planned_value=1.5,
        root_action_values=[dict(selected=[node], value=value) for node, value in enumerate((1.5, 1.5, 1.))],
        decision_seconds=.1, decision_work=dict(planner_calls=1, forced_choice=0, dp_states=1))]
    for statuses, seconds in (([2, 0, 0], .2), ([2, 0, 1], .3)):
        rows.append(dict(**common, statuses=statuses, remaining_budget=0, remaining_days=1,
            selected=[], value=0., reach_probability=.5, planned_value=None, root_action_values=[],
            decision_seconds=seconds, decision_work=dict(planner_calls=1, forced_choice=1, dp_states=0)))
    work = Counter()
    for row in rows:
        work.update(row['decision_work'])
    expected = {name: sum(row['reach_probability'] * row['decision_work'][name] for row in rows) for name in work}
    control = analysis.CONTROLS.get(method)
    case = dict(**common, p=.25, budget=1, root_value=1.5, root_selected=[0],
        control_method=control, value_source='V52_retained' if control else 'V53_full_policy_evaluation',
        state_records=3, decision_work=dict(work), expected_decision_work=expected,
        decision_seconds=.6, expected_decision_seconds=.35, evaluation_seconds=.4, wall_seconds=1., serialization_seconds=.02,
        evaluation_work=dict(new_full_policy_backups=0 if control else 3,
            retained_value_reads=3 if control else 0, occupancy_probability_terms=2))
    source_rows = [dict(row, method=control) for row in rows] if control else []
    source_case = dict(case, method=control) if control else None
    return case, rows, [(0, 2), (1, 2)], 3, source_rows, source_case


@pytest.mark.parametrize('method', analysis.METHODS)
def test_complete_reachable_certificate_controls_and_expected_decision_work(method):
    inputs = certificate(method)
    checked = analysis.verify_case(*inputs)
    assert checked['passed'], checked
    assert checked['full_policy_equations'] == 3
    assert checked['planned_roots'] == 1 and checked['forced_roots'] == 2
    assert checked['maximum_bellman_residual'] == 0.
    accounting = analysis.case_accounting([inputs[0]])
    assert accounting['decision_work']['planner_calls'] == 3
    assert accounting['expected_decision_work']['planner_calls'] == 2
    assert accounting['expected_nonforced_planner_calls'] == 1
    assert accounting['decision_seconds'] == .6 and accounting['expected_decision_seconds'] == .35


def test_truncated_depth_does_not_replace_real_horizon_in_allocation():
    one = analysis.independent_plan((0, 0, 0, 0), 2, 3, 1, [], 4)
    two = analysis.independent_plan((0, 0, 0, 0), 2, 3, 2, [], 4)
    assert all(len(row['selected']) == 1 for row in one['root_action_values'])
    assert one['planned_value'] == 1. and two['planned_value'] == 2.


def test_only_root_forced_choice_skips_value_internal_zero_budget_still_propagates():
    edges = [(0, 1), (1, 2)]
    full = analysis.independent_plan((0, 0, 0), 1, 3, 2, edges, 3)
    assert full['selected'] == (0,) and full['planned_value'] == 3.
    forced = analysis.independent_plan((2, 1, 0), 0, 2, 2, edges, 3)
    assert forced == dict(selected=(), planned_value=None, root_action_values=[])


@pytest.mark.parametrize('failure,error', [('reach', 'state_reach'), ('truncated', 'truncated_action_values'),
    ('bellman', 'full_policy_bellman'), ('expected_work', 'expected_decision_work_sum'),
    ('control_drift', 'control_state_exact')])
def test_wrong_values_reach_or_accounting_are_invalid(failure, error):
    inputs = certificate('LOOKAHEAD_1' if failure == 'control_drift' else 'LOOKAHEAD_2')
    case, rows = inputs[:2]
    if failure == 'reach':
        rows[1]['reach_probability'], rows[2]['reach_probability'] = .4, .6
    elif failure == 'truncated':
        rows[0]['root_action_values'][0]['value'] += .1
    elif failure == 'bellman':
        rows[0]['value'] = case['root_value'] = 1.6
    elif failure == 'expected_work':
        case['expected_decision_work']['forced_choice'] = 2.  # Counts states instead of expected visits.
    else:
        rows[1]['value'] += 1e-12  # Below Bellman tolerance, still violates the exact retained anchor.
    report = analysis.verify_case(*inputs)
    assert not report['passed'] and report['errors'][error] > 0


def test_partial_panel_suppresses_contrasts_without_refunding_work():
    case, rows, edges, nodes, _, _ = certificate()
    graph = dict(graph_id=1, p=.25, nodes=nodes, edges=edges)
    old_manifest = dict(status='complete', protocol=deepcopy(analysis.v52.PROTOCOL), graphs=[graph])
    old_analysis = dict(integrity={'passed': True}, accounting={'cold_case_solve_seconds': 4.})
    manifest = dict(schema='acfqp.lmta_lookahead.v53', status='complete', protocol=deepcopy(analysis.PROTOCOL),
        source_directory='reports/lmta_exact_v52', graphs=[graph], cold_decisions=True,
        completed_cases=1, total_state_records=3, new_environment_samples=0, new_environment_calls=0,
        new_RL_updates=0, new_MCTS_calls=0, source_read_seconds=.1, graph_reconstruction_seconds=.1,
        whole_runner_seconds=1.5, runner_cpu_seconds=1.4, process_peak_rss_bytes=1000)
    report = analysis.summarize(manifest, [case], rows, old_manifest, old_analysis, [], [])
    assert not report['integrity']['passed'] and report['strata'] is report['per_graph'] is None
    assert report['root_values'] == [case]
    assert report['accounting']['new_cases']['wall_seconds'] == 1.
    assert report['accounting']['new_cases']['decision_work']['planner_calls'] == 3
    assert report['accounting']['retained_V52'] == old_analysis['accounting']
    assert report['accounting']['new_environment_samples'] == 0
