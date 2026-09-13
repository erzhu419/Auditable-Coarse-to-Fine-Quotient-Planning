"""Hand-derived small certificates; neither solver nor environment is imported."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location('lmta_exact_analysis_v52',
    Path(__file__).resolve().parents[1] / 'scripts/analyze_lmta_exact_v52.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def chain_certificate(method):
    # One seed at node 0 covers 0,1 on day one and node 2 on day two.
    common = dict(graph_id=1, horizon=2, method=method)
    rows = [dict(**common, statuses=[0, 0, 0], remaining_budget=1, remaining_days=2, value=3., selected=[0]),
            dict(**common, statuses=[2, 1, 0], remaining_budget=0, remaining_days=1, value=1., selected=[])]
    if method in ('AVERAGE_OPTIMAL', 'JOINT_OPTIMAL'):
        rows.extend([dict(**common, statuses=statuses, remaining_budget=0, remaining_days=1, value=0., selected=[])
                     for statuses in ([0, 2, 1], [0, 0, 2])])
    if method in ('SCORE_OPTIMAL_BUDGET', 'JOINT_OPTIMAL'):
        rows.append(dict(**common, statuses=[0, 0, 0], remaining_budget=1, remaining_days=1, value=2., selected=[0]))
    case = dict(**common, p=.25, budget=1, root_value=3., root_selected=[0],
                wall_seconds=.1, certificate_serialization_seconds=.02,
                certificate_records=len(rows), counters=dict(dp_states=len(rows), action_value_evaluations=12))
    return case, rows, [(0, 1), (1, 2)]


@pytest.mark.parametrize('method', analysis.METHODS)
def test_two_day_chain_certificate_including_zero_budget_and_myopic_selected_only(method):
    case, rows, edges = chain_certificate(method)
    report = analysis.verify_case(case, rows, edges, 3)
    assert report['passed'], report
    assert report['bellman_equations'] == len(rows)
    assert report['action_comparisons'] == len(rows)
    assert report['maximum_bellman_residual'] == 0.
    if method == 'AVERAGE_MYOPIC':
        # Nonchosen root seed 1 has no future certificate, and none is needed.
        assert not any(row['statuses'] == [0, 2, 1] for row in rows)


def test_checker_kernel_uses_full_target_indegree_and_waits_a_day_for_new_activity():
    _, outcomes = analysis.independent_model([(0, 2), (1, 2), (2, 3)], 4)
    single = outcomes((1, 0, 0, 0), ())
    assert single == ((.5, (2, 0, 0, 0), 0), (.5, (2, 0, 1, 0), 1))
    both = outcomes((1, 1, 0, 0), ())
    assert both == ((.25, (2, 2, 0, 0), 0), (.75, (2, 2, 1, 0), 1))
    seeded = outcomes((1, 0, 0, 0), (1,))
    assert seeded == ((.25, (2, 2, 0, 0), 1), (.75, (2, 2, 1, 0), 2))
    assert outcomes((2, 2, 1, 0), ()) == ((1., (2, 2, 2, 1), 1),)


@pytest.mark.parametrize('failure,error', [('value', 'bellman_equation'),
    ('missing', 'missing_successor'), ('suboptimal', 'action_optimality')])
def test_incorrect_certificate_cannot_pass(failure, error):
    case, rows, edges = chain_certificate('AVERAGE_OPTIMAL')
    if failure == 'value':
        rows[0]['value'] = case['root_value'] = 2.75
    elif failure == 'missing':
        rows.pop(1)
        case['certificate_records'] = case['counters']['dp_states'] = len(rows)
    else:
        rows[0].update(value=2., selected=[1])
        case.update(root_value=2., root_selected=[1])
    report = analysis.verify_case(case, rows, edges, 3)
    assert not report['passed'] and report['errors'][error] > 0


def test_incomplete_panel_suppresses_strata_and_retains_actual_case_costs():
    # Deliberately partial synthetic logs: no generation or evaluation of the real panel.
    case, rows, edges = chain_certificate('AVERAGE_SCORE')
    manifest = dict(schema='acfqp.lmta_exact.v52', status='complete', protocol=deepcopy(analysis.PROTOCOL),
        graphs=[dict(graph_id=1, p=.25, nodes=3, edges=edges)], cold_cache=True,
        new_environment_samples=0, new_environment_calls=0, new_RL_updates=0, new_MCTS_calls=0,
        graph_generation_seconds=.01, whole_runner_seconds=.2, runner_cpu_seconds=.19,
        process_peak_rss_bytes=1000, completed_cases=1, total_state_records=len(rows),
        data_bytes={'cases.jsonl': 100, 'states.jsonl': 200})
    report = analysis.summarize(manifest, [case], rows)
    assert not report['integrity']['passed'] and report['strata'] is None
    assert report['root_values'] == [case]
    assert report['accounting']['cold_case_solve_seconds'] == .1
    assert report['accounting']['certificate_serialization_seconds'] == .02
    assert report['accounting']['summed_case_counters']['dp_states'] == len(rows)
    assert report['accounting']['whole_runner_seconds'] == .2
    assert report['accounting']['new_environment_samples'] == 0
