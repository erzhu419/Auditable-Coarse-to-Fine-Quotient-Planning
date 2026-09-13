"""Small hand certificates and synthetic metadata; no fresh ER panel is generated."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('analytic_scale_analysis_v58', ROOT / 'scripts/analyze_lmta_analytic_scale_v58.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


@pytest.fixture(scope='session', autouse=True)
def development_work():
    """Charge the independent hand-query enumeration executed by these tests."""
    patch, work = pytest.MonkeyPatch(), Counter()
    original_plan, original_model = A.v53.independent_plan, A.v52.independent_model

    def plan(*args):
        work['independent_query_checks'] += 1
        return original_plan(*args)

    def model(*args):
        work['independent_model_constructions'] += 1
        score, kernel = original_model(*args)

        def outcomes(*inputs):
            before = kernel.cache_info()
            result = kernel(*inputs)
            after = kernel.cache_info()
            work['independent_kernel_calls'] += 1
            work['independent_kernel_cache_hits'] += after.hits-before.hits
            work['independent_kernel_builds'] += after.misses-before.misses
            if after.misses > before.misses:
                work['independent_transition_outcomes_created'] += len(result)
            return result

        return score, outcomes

    patch.setattr(A.v53, 'independent_plan', plan)
    patch.setattr(A.v52, 'independent_model', model)
    yield work
    patch.undo()
    path = ROOT / 'reports/lmta_analytic_scale_v58.analysis_checks.json'
    report = json.loads(path.read_text()) if path.exists() else {'schema': 'acfqp.lmta_analytic_scale_analysis_checks.v58', 'analysis_test_attempts': []}
    report['development_work'] = dict(work, new_graphs=0, new_environment_samples=0,
        new_environment_calls=0, new_planner_implementation_calls=0, new_RL_updates=0,
        new_MCTS_calls=0, scope='independent checker enumeration of hand certificates; synthetic roster uses stubbed certificate math')
    path.write_text(json.dumps(report, indent=2)+'\n')


def certificate(method=A.ANALYTIC):
    meta = dict(graph_id=1, horizon=2, method=method, nodes=3, stratum='sparse', p=.25, budget=1)
    root_work = dict(planner_calls=1, forced_choice=0, action_value_evaluations=6, kernel_builds=3,
                     kernel_cache_hits=0, target_probability_evaluations=6, dp_states=4, transition_outcomes=4)
    if method == A.ANALYTIC:
        root_work.update(analytic_expectation_calls=3, analytic_probability_terms=3)
    else:
        root_work['kernel_builds'] = 6
    rows = [dict(**meta, statuses=[0, 0, 0], remaining_budget=1, remaining_days=2, selected=[0],
        value=1.5, reach_probability=1., planned_value=1.5,
        root_action_values=[dict(selected=[node], value=value) for node, value in enumerate((1.5, 1.5, 1.))],
        decision_seconds=.1, decision_work=root_work)]
    for statuses, seconds in (([2, 0, 0], .2), ([2, 0, 1], .3)):
        work = {name: 0 for name in root_work}
        work.update(planner_calls=1, forced_choice=1)
        rows.append(dict(**meta, statuses=statuses, remaining_budget=0, remaining_days=1, selected=[],
            value=0., reach_probability=.5, planned_value=None, root_action_values=[],
            decision_seconds=seconds, decision_work=work))
    counts = Counter()
    for row in rows:
        counts.update(row['decision_work'])
    case = dict(**meta, status='complete', stop_reason=None, root_value=1.5, root_selected=[0],
        value_source='V58_full_policy_evaluation', control_method=None, state_records=3, decision_work=dict(counts),
        expected_decision_work={key: sum(row['reach_probability']*row['decision_work'][key] for row in rows) for key in counts},
        expected_decision_seconds=.35, decision_seconds=.6, evaluation_seconds=.4, wall_seconds=1.,
        serialization_seconds=.02, last_limit_check_seconds=.7, prepare_gc_seconds=.03, cleanup_seconds=.04,
        decision_total_seconds=.64, block_seconds=1.04,
        evaluation_work=dict(new_full_policy_backups=3, retained_value_reads=0, occupancy_probability_terms=2))
    return case, rows, [(0, 2), (1, 2)], 3


def test_three_methods_hand_policy_certificates_and_nonmutating_views():
    for method in A.METHODS:
        inputs = certificate(method)
        before = deepcopy(inputs)
        result = A.verify_case(*inputs)
        assert result['passed'] and result['quality_verified'], result
        assert result['full_policy_equations'] == 3
        assert inputs == before
        fees = A.case_accounting([inputs[0]])
        assert fees['decision_total_seconds'] == .64 and fees['block_seconds'] == 1.04
        assert fees['expected_decision_seconds'] == .35
    inputs = certificate()
    inputs[0]['value_source'] = 'V54_full_policy_evaluation'
    assert A.verify_case(*inputs)['errors']['actual_V58_method_and_value_source'] == 1


def test_own_exact_reported_argmax_not_historical_action_identity():
    inputs = certificate()
    root = inputs[1][0]
    root['root_action_values'][1]['value'] += 5e-12
    checked = A.verify_case(*inputs)
    assert not checked['passed'] and checked['errors']['reported_strict_argmax_and_lex_tie'] == 1
    assert 'truncated_action_values' not in checked['errors']
    # Swapping the symmetric parent action changes policy states but leaves true value 1.5.
    root.update(selected=[1], planned_value=root['root_action_values'][1]['value'])
    inputs[0]['root_selected'] = [1]
    for row in inputs[1][1:]:
        row['statuses'][0], row['statuses'][1] = row['statuses'][1], row['statuses'][0]
    checked = A.verify_case(*inputs)
    assert checked['passed'] and checked['quality_verified'], checked


def test_analytic_calls_and_cleanup_cannot_be_deleted_from_charged_views():
    inputs = certificate()
    row = inputs[1][0]
    row['decision_work']['analytic_expectation_calls'] = 0
    inputs[0]['decision_work']['analytic_expectation_calls'] = 0
    inputs[0]['expected_decision_work']['analytic_expectation_calls'] = 0
    inputs[0]['decision_total_seconds'] = inputs[0]['decision_seconds']
    checked = A.verify_case(*inputs)
    assert checked['errors']['analytic_work_partition'] == 1
    assert checked['errors']['decision_total_includes_cleanup'] == 1
    assert A.case_accounting([inputs[0]])['cleanup_seconds'] == .04


def test_resource_limit_preserves_paid_decision_check_and_has_no_quality():
    case, rows, edges, nodes = certificate()
    rows = rows[:1]
    rows[0].update(value=None, reach_probability=None)
    case.update(status='resource_limit', stop_reason='max_policy_states', root_value=None, root_selected=None,
        state_records=1, decision_work=deepcopy(rows[0]['decision_work']), decision_seconds=.1,
        expected_decision_work=None, expected_decision_seconds=None, wall_seconds=.2, evaluation_seconds=.1,
        last_limit_check_seconds=.15, decision_total_seconds=.14, block_seconds=.24,
        evaluation_work=dict(new_full_policy_backups=0, retained_value_reads=0, occupancy_probability_terms=0))
    limits = dict(A.LIMITS, max_policy_states=1)
    checked = A.verify_case(case, rows, edges, nodes, limits)
    assert checked['passed'] and not checked['quality_verified'], checked
    rows[0]['root_action_values'][0]['value'] += .2
    checked = A.verify_case(case, rows, edges, nodes, limits)
    assert not checked['passed'] and checked['errors']['truncated_action_values'] == 1
    fees = A.case_accounting([case])
    assert fees['decision_work']['analytic_expectation_calls'] == 3
    assert fees['expected_decision_work'] is None and fees['decision_total_seconds'] == .14


def test_synthetic_full_roster_gc_and_incomplete_group_scale_summary(monkeypatch):
    # Metadata/statistics only: hand tests above perform the independent math checks.
    monkeypatch.setattr(A, 'verify_case', lambda case, rows, edges, nodes: dict(
        passed=True, errors={}, quality_verified=case['status']=='complete', planned_roots=0,
        forced_roots=0, full_policy_equations=0, state_records=len(rows)))
    graphs, cases = [], []
    for panel in A.PANELS:
        for graph in panel['seeds']:
            graphs.append(dict(graph_id=graph, edges=[], **{key: value for key, value in panel.items() if key != 'seeds'}))
            for method, value in zip(A.METHODS, (3., 2.5, 4.)):
                case = certificate(method)[0]
                case.update(graph_id=graph, nodes=panel['nodes'], stratum=panel['stratum'], p=panel['p'],
                            budget=2, horizon=3, root_value=value, state_records=0)
                case['expected_decision_work']['action_value_evaluations'] = 10 if panel['nodes'] == 9 else 20
                cases.append(case)
    manifest = dict(schema='acfqp.lmta_analytic_scale.v58', status='complete', protocol=deepcopy(A.PROTOCOL),
        source_directory='reports/lmta_paired_timing_v57', cold_decisions=True, runtime={'gc_enabled': True}, graphs=graphs,
        completed_cases=192, successful_cases=192, resource_limited_cases=0, total_state_records=0, new_graphs=64,
        new_environment_samples=0, new_environment_calls=0, new_RL_updates=0, new_MCTS_calls=0,
        source_read_seconds=.1, graph_generation_seconds=.2, data_output_seconds=.3, whole_runner_seconds=250.,
        runner_cpu_seconds=240., process_peak_rss_bytes=1000)
    source = dict(integrity={'passed': True}, complete_performance_evidence=True, accounting={'historical_seconds': 100.})
    report = A.summarize(manifest, cases, [], source)
    assert report['integrity']['passed'] and report['complete_quality_evidence'], report['integrity']
    assert report['accounting']['data_output_seconds'] == .3
    assert report['accounting']['retained_V57'] == source['accounting']
    assert all(row['contrasts']['two_minus_myopic']['negative_count'] == 16 for row in report['strata'])
    assert all(row['sum_gain_over_sum_headroom'] == -.5 for row in report['strata'])
    for row in report['descriptive_scale_comparisons']:
        for method in A.METHODS:
            assert row['ratios_of_per_graph_mean_work'][method]['expected_decision_work']['action_value_evaluations'] == 2.
    cases[0].update(status='resource_limit', root_value=None, expected_decision_work=None, expected_decision_seconds=None)
    manifest.update(successful_cases=191, resource_limited_cases=1)
    partial = A.summarize(manifest, cases, [], source)
    assert partial['integrity']['passed'] and not partial['complete_quality_evidence']
    assert partial['strata'][0]['values'] is partial['strata'][0]['ratios_of_total_work_and_cost'] is None
    assert partial['descriptive_scale_comparisons'][0]['ratios_of_per_graph_mean_work'] is None
    assert partial['descriptive_scale_comparisons'][1]['ratios_of_per_graph_mean_work'] is not None
    assert partial['accounting']['new_cases']['case_records'] == 192
    manifest['runtime']['gc_enabled'] = False
    invalid = A.summarize(manifest, cases, [], source)
    assert not invalid['integrity']['passed'] and invalid['integrity']['errors']['manifest_protocol'] == 1
    assert invalid['accounting']['new_cases']['cleanup_seconds'] == report['accounting']['new_cases']['cleanup_seconds']
