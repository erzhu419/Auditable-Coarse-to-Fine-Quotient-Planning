"""Frozen-head update semantics, common-root contrasts and inherited work."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('frozen_head_analysis_v109', ROOT / 'scripts/analyze_controlled_predictive_frozen_head_v109.py')
B = load('query_update_fixture_v109', ROOT / 'tests/test_analyze_controlled_predictive_query_update_v108.py')


def fixture():
    run = B.fixture()
    run['settings'].update(methods=list(A.METHODS), contrasts=[list(pair) for pair in A.CONTRASTS])
    run.update(inherited_model_methods=list(A.OLD_METHODS[2:]), inherited_decisions=len(run['decisions']),
        inherited_v108_work={'new_neural_model_fits': 16, 'new_optimizer_steps': 16000},
        joint_source='fixture_v107')
    run['runner_checks']['frozen_hidden_parameters'] = True
    for stage in run['training']:
        old_fits = stage['fit_logs']
        stage['fit_logs'], stage['model_metadata'] = {}, {}
        for base in A.CURRENT:
            method = base + '_FROZEN_STATS_WARM_HEAD_ONLY'
            fit = deepcopy(old_fits[base + '_FROZEN_STATS_WARM_REWARD_ONLY'])
            hidden = fit['hidden']
            count = stage['data_log']['full']['training_roots']
            parameters = dict(parameter_count=123 * hidden, trainable_parameter_count=hidden,
                frozen_parameter_count=122 * hidden, updated_parameter_indices=[2])
            fit.update(mode='HEAD_ONLY', optimized_queries=['reward', 'risk_goal'],
                active_training_episodes=deepcopy(stage['data_log']['full']['training_episodes']),
                active_training_roots=count, full_loss_denominator_roots=count, data_loss_weight=1., **parameters)
            fit['checks']['frozen_hidden_parameters'] = True
            fit['models']['UNIFORM_SHRINK'].update(**parameters, final_gradient_norm=1e-8,
                final_full_gradient_norm=1., gradient_norm_semantics='updated_parameters_only')
            passes = dict(optimizer_root_passes=1000 * count, optimizer_pair_passes=10000 * count,
                optimizer_parameter_updates=1000 * hidden)
            fit['counts'].update(passes)
            fit['models']['UNIFORM_SHRINK']['counts'].update(passes)
            metadata = dict(hidden=hidden, mode='HEAD_ONLY', optimized_queries=['reward', 'risk_goal'],
                budget=512000, episode_cutoff=3, family='UNIFORM_SHRINK', **parameters)
            stage['fit_logs'][method], stage['model_metadata'][method] = fit, metadata
            run['models'].append(dict(training_life=stage['life'], method=method, metadata=metadata))
            for root in run['cohort']['roots']:
                run['decisions'].append(dict(root_id=root['root_id'], training_life=stage['life'], method=method,
                    event=B.B.B.event(A.OPTIONS[1])))
    run['scoring_log']['counts'].update(model_payloads_loaded=8, model_root_scores=128,
        neural_candidate_predictions=640, neural_hidden_activations=6400)
    return run


def test_six_contrasts_keep_common_roots_and_original_cached_models():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    head, half = A.CONTRASTS[4]
    comparison = result['comparisons'][head + '_minus_' + half]
    reward = comparison['reward']['pooled']['selected_utility_delta']
    risk = comparison['risk_goal']['pooled']['selected_utility_delta']
    assert reward['cells'] == [[1.5, 2.5, 3.5, 4.5]] * 4
    assert reward['grand_mean'] == 3. and risk['grand_mean'] == -3.
    assert reward['row_directions']['positive'] == risk['row_directions']['negative'] == 4
    assert len(result['comparisons']) == 6 and len(result['methods']) == 16
    assert result['cohort']['inherited_model_root_decisions'] == 768
    assert result['cohort']['new_model_root_decisions'] == 128


def test_only_head_updates_and_new_fits_are_charged_separately_from_retained_work():
    result = A.analyze_run(fixture())
    cost = result['actual_executed_work']
    assert cost['newly_sampled_environment_transitions'] == cost['new_model_prefix_transitions'] == 0
    assert cost['new_neural_model_fits'] == 8 and cost['new_optimizer_steps'] == 8000
    assert cost['new_optimizer_parameter_updates'] == 80000
    assert cost['new_optimizer_root_passes'] == 24000 and cost['new_optimizer_pair_passes'] == 240000
    assert cost['new_neural_candidate_predictions'] == 640 and cost['new_training_diagnostic_candidate_predictions'] == 160
    assert result['inherited_reference_work']['trajectories'] == 2560
    assert result['inherited_v108_total_work']['new_neural_model_fits'] == 16
    assert result['inherited_cohort_extraction_work']['counts']['new_synthetic_transitions'] == 123456


def test_frozen_parameter_gradient_is_diagnostic_and_is_not_a_convergence_gate():
    run = fixture()
    fit = run['training'][0]['fit_logs'][A.NEW_METHODS[0]]
    fit['models']['UNIFORM_SHRINK']['final_full_gradient_norm'] = 100.
    result = A.analyze_run(run)
    assert result['complete'] and result['primary_complete']
    retained = result['training']['fits'][0]['models']['UNIFORM_SHRINK']
    assert retained['final_gradient_norm'] == 1e-8 and retained['final_full_gradient_norm'] == 100.
    fit['models']['UNIFORM_SHRINK']['gradient_norm_semantics'] = 'all_parameters'
    assert not A.analyze_training(run)['checks']['hidden_parameters_frozen_and_head_only_updated']


def test_changed_hidden_parameters_or_wrong_updated_indices_invalidate_head_only_claim():
    run = fixture()
    fit = run['training'][0]['fit_logs'][A.NEW_METHODS[0]]
    fit['checks']['frozen_hidden_parameters'] = False
    fit['updated_parameter_indices'] = [0, 2]
    result = A.analyze_training(run)
    assert not result['checks']['hidden_parameters_frozen_and_head_only_updated']
    assert not result['checks']['deployed_update_metadata_bound']


def test_missing_head_decision_keeps_the_root_and_disables_the_full_matrix():
    run = fixture()
    index = next(i for i, row in enumerate(run['decisions']) if row['method'] == A.NEW_METHODS[0])
    run['decisions'].pop(index)
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['full_root_model_and_decision_rosters']
    matrix = result['methods'][A.NEW_METHODS[0]]['reward']['pooled']['selected_reference_utility']
    assert matrix['cells'][0][0] is None and matrix['grand_mean'] is None
    assert result['cohort']['unique_reference_roots'] == 16
    assert result['actual_executed_work']['new_neural_model_fits'] == 8


def test_censoring_preserves_reference_cost_and_new_head_update_cost():
    run = fixture()
    root = run['cohort']['roots'][0]
    root['reference_complete'] = False
    root['reference_log'].update(censored_root=True, pair_deltas={}, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete'], result['checks']
    assert result['inherited_reference_work']['trajectories'] == 2560
    assert result['actual_executed_work']['new_optimizer_parameter_updates'] == 80000
    matrix = result['methods'][A.NEW_METHODS[0]]['reward']['pooled']['selected_reference_utility']
    assert all(row[0] is None for row in matrix['cells']) and matrix['grand_mean'] is None
