"""Matched-step data contrasts, cached controls and newly executed update work."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('half_continuation_analysis_v111', ROOT / 'scripts/analyze_controlled_predictive_half_continuation_v111.py')
B = load('pooled_fixture_v111', ROOT / 'tests/test_analyze_controlled_predictive_pooled_history_v110.py')


def fixture():
    run = B.fixture()
    run['settings'].update(methods=list(A.METHODS), contrasts=[list(pair) for pair in A.CONTRASTS])
    for fold in run['folds']:
        for name, metadata in fold['model_metadata'].items():
            metadata['path'] = f"retained/life_{fold['heldout_life']}/{name}.json"
    run.update(inherited_folds=deepcopy(run['folds']), inherited_model_count=len(run['models']),
        inherited_decisions=len(run['decisions']), input_counts={'pooled_half_payload_files_read': 8})
    run['inherited_work']['V110'] = {'new_neural_model_fits': 16, 'new_optimizer_steps': 16000}
    # The new control selects a candidate worth half the full-model candidate's value.
    for root in run['cohort']['roots']:
        root['reference_log']['pair_deltas'][A.OPTIONS[2]] = [
            [value / 2 for value in row] for row in root['reference_log']['pair_deltas'][A.OPTIONS[1]]]
    run['folds'] = []
    for original in run['inherited_folds']:
        life = original['heldout_life']
        fold = dict(heldout_life=life, source_lives=original['source_lives'],
            data_log=deepcopy(original['data_log']), fit_logs={}, model_metadata={})
        for hidden in A.WIDTHS:
            method = f'POOLED_H{hidden}_HALF_CONTINUED'
            fit = deepcopy(original['fit_logs'][f'POOLED_H{hidden}_HALF'])
            fit.update(stage='HALF_CONTINUED', initialization='half_parameters',
                inherited_parameter_steps=1000, parameter_lineage_steps=2000)
            fit['checks'].update(frozen_half_statistics=True, unchanged_half_training_roster=True)
            half_metadata = original['model_metadata'][f'POOLED_H{hidden}_HALF']
            metadata = dict(half_metadata, stage='HALF_CONTINUED', path=f'new/{life}/{method}.json',
                half_source_path=half_metadata['path'])
            metadata.pop('episode_cutoff')
            fold['fit_logs'][method], fold['model_metadata'][method] = fit, metadata
            run['models'].append(dict(heldout_life=life, method=method, metadata=metadata))
            for root in run['cohort']['roots']:
                if root['life'] == life:
                    run['decisions'].append(dict(root_id=root['root_id'], heldout_life=life, method=method,
                        event=B.B.event(A.OPTIONS[2])))
        run['folds'].append(fold)
    run['scoring_log']['counts'].update(model_payloads_loaded=8, model_root_scores=32,
        neural_candidate_predictions=160, neural_hidden_activations=1600)
    return run


def test_eight_contrasts_decompose_additional_data_and_optimization_on_the_same_roots():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    full, continued, half = 'POOLED_H4_FULL', 'POOLED_H4_HALF_CONTINUED', 'POOLED_H4_HALF'
    def summary(left, right, query='reward'):
        return result['comparisons'][left + '_minus_' + right][query]['pooled']['selected_utility_delta']
    assert summary(full, continued)['fold_means'] == [.75, 1.25, 1.75, 2.25]
    assert summary(continued, half)['grand_mean'] == 1.5
    assert summary(full, half)['grand_mean'] == 3.
    assert summary(full, continued, 'risk_goal')['grand_mean'] == -1.5
    assert result['effect_decomposition_residuals']['4']['reward']['pooled']['fold_means'] == [0.] * 4
    assert len(result['methods']) == 7 and len(result['comparisons']) == 8


def test_only_new_half_continuation_fits_and_scores_are_charged():
    result = A.analyze_run(fixture())
    work = result['actual_executed_work']
    assert work['newly_sampled_environment_transitions'] == work['new_model_prefix_transitions'] == 0
    assert work['new_neural_model_fits'] == 8 and work['new_optimizer_steps'] == 8000
    assert work['new_optimizer_root_passes'] == 48000 and work['new_optimizer_pair_passes'] == 480000
    assert work['new_optimizer_parameter_updates'] == 9840000
    assert work['new_training_diagnostic_candidate_predictions'] == 480
    assert work['new_neural_candidate_predictions'] == 160 and work['new_model_root_decisions'] == 32
    assert work['bank_counts']['record_files_read'] == 8 and work['input_counts']['pooled_half_payload_files_read'] == 8
    assert result['cohort']['inherited_model_root_decisions'] == 64
    assert result['inherited_reference_work']['trajectories'] == 2560
    assert result['inherited_total_work']['V110']['new_optimizer_steps'] == 16000


def test_excluded_history_leakage_and_second_batch_contamination_invalidate_control():
    run = fixture()
    fit = run['folds'][0]['fit_logs'][A.NEW_METHODS[0]]
    fit['training_roster'][0][0] = run['folds'][0]['heldout_life']
    fit['statistics_roster'][-1][2] = 1
    result = A.analyze_run(run)
    assert not result['primary_complete']
    assert not result['checks']['source_history_training_and_statistics_exclusion']
    assert not result['checks']['actual_half_membership_and_statistics_bound']
    assert not result['checks']['half_data_learning_rule_bound']


def test_missing_new_decision_preserves_cached_full_half_results_and_inherited_costs():
    run = fixture()
    run['decisions'].pop(run['inherited_decisions'])
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['full_root_model_and_decision_rosters']
    new = result['comparisons']['POOLED_H4_FULL_minus_POOLED_H4_HALF_CONTINUED']['reward']['pooled']['selected_utility_delta']
    old = result['comparisons']['POOLED_H4_FULL_minus_POOLED_H4_HALF']['reward']['pooled']['selected_utility_delta']
    assert new['fold_means'][0] is None and new['grand_mean'] is None
    assert old['grand_mean'] == 3.
    assert result['actual_executed_work']['new_neural_model_fits'] == 8
    assert result['inherited_reference_work']['trajectories'] == 2560


def test_wrong_update_budget_or_inherited_scoring_charged_as_new_cannot_pass():
    run = fixture()
    fit = run['folds'][0]['fit_logs'][A.NEW_METHODS[0]]
    fit['new_optimizer_steps'] = 2000
    fit['counts']['optimizer_root_passes'] += 1
    run['scoring_log']['counts']['model_root_scores'] += run['inherited_decisions']
    result = A.analyze_run(run)
    assert not result['primary_complete']
    assert not result['checks']['matched_start_and_new_steps_with_full']
    assert not result['checks']['new_fit_budget_and_diagnostics_accounted']
    assert not result['checks']['new_scoring_roster_and_work_accounted']
