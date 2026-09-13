"""Small hand-derived certificates, with separately recorded checker work."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from time import perf_counter

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tie_refinement_analysis_v55', ROOT / 'scripts/analyze_lmta_tie_refinement_v55.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)
EDGES = [(3, 0), (0, 1), (1, 2)]


@pytest.fixture(scope='session', autouse=True)
def record_checker_work(request):
    started, counts = perf_counter(), Counter()
    originals = [(analysis.v53, 'independent_plan', 'independent_prefix_plan_calls'),
                 (analysis, 'refinement_values', 'independent_refinement_calls'),
                 (analysis.v52, 'independent_model', 'independent_kernel_instances')]
    saved = []
    for module, name, counter in originals:
        original = getattr(module, name)
        def wrapped(*args, _function=original, _counter=counter, **kwargs):
            counts[_counter] += 1
            return _function(*args, **kwargs)
        saved.append((module, name, original))
        setattr(module, name, wrapped)
    yield
    for module, name, original in saved:
        setattr(module, name, original)
    path = ROOT / 'reports/lmta_tie_refinement_v55.analysis_checks.json'
    data = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    data['attempts'].append(dict(test_module='tests/test_lmta_tie_refinement_analysis_v55.py',
        passed=len(request.session.items) - request.session.testsfailed, failed=request.session.testsfailed,
        wall_seconds=perf_counter() - started, independent_checker_calls=dict(counts),
        environment_calls=0, neural_model_evaluations=0, gradient_steps=0,
        scope='Hand-derived small graph records only. Prefix/refinement calls are included within kernel-instance work, not additive costs.'))
    path.write_text(json.dumps(data, indent=2) + '\n')


def combine(row):
    work = Counter(row['prefix_work'])
    work.update(row['refinement_work'])
    work.update(planner_calls=1, refinement_calls=int(bool(row['refinement_action_values'])),
                refined_root_actions=len(row['refinement_action_values']))
    row['decision_work'] = dict(work)


def recost(case, rows):
    case['state_records'] = len(rows)
    for field in ('decision_work', 'prefix_work', 'refinement_work'):
        total = Counter()
        for row in rows:
            total.update(row[field])
        case[field] = dict(total)
        case['expected_' + field] = ({name: sum(row['reach_probability'] * row[field].get(name, 0)
                                               for row in rows) for name in total}
                                    if case['status'] == 'complete' else None)
    case['decision_seconds'] = sum(row['decision_seconds'] for row in rows)
    case['evaluation_seconds'] = case['wall_seconds'] - case['decision_seconds']
    case['expected_decision_seconds'] = case['decision_seconds'] if case['status'] == 'complete' else None


def certificate():
    common = dict(graph_id=1, horizon=3, method=analysis.CANDIDATE, nodes=4, stratum='sparse', p=.25, budget=1)
    counter_names = ('dp_states', 'action_value_evaluations', 'kernel_builds', 'transition_outcomes', 'bellman_expectation_terms')
    prefix = {name: 7 for name in counter_names}
    prefix['forced_choice'] = 0
    refinement = {name: 6 for name in counter_names}
    rows = [dict(**common, statuses=[0, 0, 0, 0], remaining_budget=1, remaining_days=3,
        value=4., selected=[3], prefix_selected=[0], reach_probability=1., planned_value=3.,
        root_action_values=[dict(selected=[node], value=value) for node, value in enumerate((3., 2., 1., 3.))],
        refinement_action_values=[dict(selected=[0], value=3.), dict(selected=[3], value=4.)],
        prefix_work=prefix, refinement_work=refinement, decision_seconds=.3)]
    for statuses, days, value in (([1, 0, 0, 2], 2, 2.), ([2, 1, 0, 2], 1, 1.)):
        rows.append(dict(**common, statuses=statuses, remaining_budget=0, remaining_days=days,
            value=value, selected=[], prefix_selected=[], reach_probability=1., planned_value=None,
            root_action_values=[], refinement_action_values=[], prefix_work=dict.fromkeys(counter_names, 0) | {'forced_choice': 1},
            refinement_work=dict.fromkeys(counter_names, 0), decision_seconds=.05))
    for row in rows:
        combine(row)
    case = dict(**common, status='complete', stop_reason=None, root_value=4., root_selected=[3],
        value_source='V55_full_policy_evaluation', control_method=None, wall_seconds=.6, serialization_seconds=.02,
        last_limit_check_seconds=.45, evaluation_work=dict(new_full_policy_backups=3, retained_value_reads=0, occupancy_probability_terms=2))
    recost(case, rows)
    return case, rows


def test_complete_refinement_changes_root_and_retains_both_stage_costs():
    case, rows = certificate()
    result = analysis.verify_candidate_case(case, rows, EDGES, 4)
    assert result['passed'] and result['quality_verified'], result
    assert result['full_policy_equations'] == 3
    costs = analysis.candidate_costs([case])
    assert costs['prefix_work']['action_value_evaluations'] == 7
    assert costs['refinement_work']['action_value_evaluations'] == 6
    assert costs['decision_work']['action_value_evaluations'] == 13
    assert costs['expected_decision_work']['action_value_evaluations'] == 13
    assert costs['root_trigger_rate'] == costs['expected_refinement_calls_per_trajectory'] == 1.
    assert costs['reach_weighted_trigger_fraction_of_decisions'] == pytest.approx(1 / 3)


def test_close_but_not_equal_reported_prefix_values_do_not_trigger():
    row = certificate()[1][0]
    row['root_action_values'][3]['value'] -= 5e-11
    row['refinement_action_values'] = []
    row['refinement_work'] = dict.fromkeys(row['refinement_work'], 0)
    row['selected'] = row['prefix_selected']
    combine(row)
    checked = analysis.verify_candidate_decision(row, EDGES, 4)
    assert checked['passed'] and not checked['triggered'], checked


@pytest.mark.parametrize('failure,error', [('trigger', 'no_untriggered_refinement'),
    ('refinement_q', 'refinement_values'), ('prefix_choice', 'prefix_strict_choice'),
    ('synchronized_free_refinement', 'triggered_refinement_work')])
def test_trigger_choice_values_and_synchronized_fee_deletion_are_rejected(failure, error):
    row = certificate()[1][0]
    if failure == 'trigger':
        row['root_action_values'][3]['value'] -= 5e-11
    elif failure == 'refinement_q':
        row['refinement_action_values'][0]['value'] += .1
    elif failure == 'prefix_choice':
        row['prefix_selected'] = [3]
    else:
        row['refinement_work'] = dict.fromkeys(row['refinement_work'], 0)
        combine(row)  # Combined ledger is forged consistently with the deleted stage.
    report = analysis.verify_candidate_decision(row, EDGES, 4)
    assert not report['passed'] and report['errors'][error] > 0


def test_partial_case_checks_paid_refinement_and_keeps_no_full_quality():
    case, rows = certificate()
    rows = rows[:1]
    rows[0].update(value=None, reach_probability=None)
    case.update(status='resource_limit', stop_reason='max_policy_states', root_value=None, root_selected=None,
        evaluation_work=dict(new_full_policy_backups=0, retained_value_reads=0, occupancy_probability_terms=0))
    recost(case, rows)
    limits = dict(analysis.LIMITS, max_policy_states=1)
    good = analysis.verify_candidate_case(case, rows, EDGES, 4, limits)
    assert good['passed'] and not good['quality_verified'], good
    rows[0]['refinement_action_values'][0]['value'] += .1
    bad = analysis.verify_candidate_case(case, rows, EDGES, 4, limits)
    assert not bad['passed'] and bad['errors']['refinement_values'] > 0
    assert analysis.candidate_costs([case])['decision_work']['action_value_evaluations'] == 13


def test_stratum_retains_negative_myopic_gap_action_changes_and_ratio_of_sums():
    panel = dict(nodes=7, stratum='sparse', expected_degree=1.5, p=.25, seeds=[101, 102])
    cases = []
    for graph, values in ((101, (4., 3., 3.5, 5.)), (102, (2., 2., 2., 2.))):
        for method, value in zip(analysis.METHODS, values):
            case = certificate()[0]
            case.update(graph_id=graph, method=method, root_value=value, root_selected=[3] if method == analysis.CANDIDATE else [0])
            if graph == 102 and method != analysis.CANDIDATE:
                case['expected_decision_work']['action_value_evaluations'] = 26
            cases.append(case)
    result = analysis.stratum_summary(panel, cases, True)
    assert result['quality_complete']
    assert result['contrasts']['candidate_minus_myopic']['mean'] == -.25
    assert result['contrasts']['candidate_minus_myopic']['negative_count'] == 1
    assert result['contrasts']['headroom_fraction']['null_count'] == 1
    assert result['new_degradations'] == 0 and result['root_actions_changed_vs_two'] == 2
    assert result['candidate_over_control_cost_ratios']['LOOKAHEAD_2']['expected_action_values']['mean'] == .75
    assert result['ratio_of_summed_expected_action_values']['LOOKAHEAD_2'] == pytest.approx(2 / 3)


def test_regression_is_excluded_from_fresh_fees_and_new_case_counts():
    fresh, regression = certificate()[0], certificate()[0]
    fresh.update(graph_id=550000, nodes=7)
    regression.update(graph_id=540009, nodes=7)
    controls = [dict(certificate()[0], graph_id=540009, method=method) for method in analysis.METHODS if method != analysis.CANDIDATE]
    manifest = dict(schema='acfqp.lmta_tie_refinement.v55', status='complete', protocol=deepcopy(analysis.PROTOCOL),
        source_directory='reports/lmta_scale_v54', cold_decisions=True, graphs=[], regression_controls=controls,
        completed_cases=2, successful_cases=2, resource_limited_cases=0, total_state_records=0,
        source_read_seconds=.1, graph_generation_seconds=.1, whole_runner_seconds=1.4, runner_cpu_seconds=1.3,
        process_peak_rss_bytes=1000, new_environment_samples=0, new_environment_calls=0, new_RL_updates=0, new_MCTS_calls=0)
    old = dict(integrity={'passed': True}, complete_quality_evidence=True, accounting={'old_fee': 10.})
    report = analysis.summarize(manifest, [fresh, regression], [], old, controls)
    assert not report['integrity']['passed'] and not report['fresh_complete_quality_evidence']
    assert report['accounting']['new_cases']['case_records'] == 2
    assert report['accounting']['fresh_cases']['case_records'] == 1
    assert report['accounting']['regression_new_candidate']['case_records'] == 1
    assert report['accounting']['new_cases']['wall_seconds'] == 1.2
    assert report['regression']['retained_control_cases'] == controls
    assert report['accounting']['retained_V54'] == old['accounting']
    assert all(row['values'] is None for row in report['strata'])
