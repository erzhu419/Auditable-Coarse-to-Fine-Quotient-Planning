"""Incremental fitting cost and crossed-reference contrasts on tiny retained fixtures."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('incremental_analysis_v107', ROOT / 'scripts/analyze_controlled_predictive_incremental_ranking_v107.py')
B = load('crossed_fixture_v107', ROOT / 'tests/test_analyze_controlled_predictive_crossed_ranking_v106.py')


def fixture():
    run = B.fixture()
    run['settings'].update(methods=list(A.METHODS), contrasts=[list(pair) for pair in A.CONTRASTS],
        budgets=[256000, 512000], optimizer_steps=1000, l2_coefficient=.001 / 1968, l2_reference_parameters=1968)
    run.update(inherited_model_methods=list(A.OLD_METHODS[2:]), inherited_decisions=len(run['decisions']),
        runner_checks={'cached_baselines_exact': True, 'deployed_half_statistics_exact': True},
        inherited_v106_work={'scoring_counts': deepcopy(run['scoring_log']['counts'])}, training=[])
    # This is inherited extraction work; it must never enter the new training/prefix total.
    run['cohort']['log']['counts']['new_synthetic_transitions'] = 123456
    for life in run['settings']['training_lifecycles']:
        half = dict(records=1, training_roots=1, heldout_roots=0,
            training_episodes={'reward': [0], 'risk_goal': []})
        full = dict(records=4, training_roots=3, heldout_roots=1,
            training_episodes={'reward': [0, 1], 'risk_goal': [1]})
        data = dict(half_cutoff=2, full_cutoff=3, half=half, full=full, counts={key: 0 for key in A.ZERO_DATA},
            checks={'half_statistics_exact': True, 'full_roster_bound': True}, seconds=.01)
        stage = dict(life=life, data_log=data, fit_logs={}, model_metadata={})
        for method in A.NEW_METHODS:
            hidden = 4 if '_H4_' in method else 16
            mode = next(mode for mode in A.MODES if method.endswith(mode))
            warm = mode == A.MODES[1]
            fit = dict(mode=mode, family='UNIFORM_SHRINK', hidden=hidden, parameter_count=123 * hidden,
                initialization='half_parameters' if warm else 'original_initialization',
                optimizer_state='reset_zero_moments', new_optimizer_steps=1000,
                inherited_parameter_steps=1000 if warm else 0, parameter_lineage_steps=2000 if warm else 1000,
                statistics_source_checkpoint=2, statistics_training_episodes=deepcopy(half['training_episodes']),
                checkpoint=3, training_episodes=deepcopy(full['training_episodes']), training_roots=3, heldout_roots=1,
                normalization_training_roots=1, conflict_mass_training_roots=1, uniform_gamma=.25,
                training_replica_rows=12, total_training_pairs=30, l2_coefficient=.001 / 1968,
                l2_reference_parameters=1968, counts={'neural_model_fits': 1, 'optimizer_steps': 1000},
                checks={'frozen_half_statistics': True, 'initial_parameters_from_half_or_original': True}, seconds=.01,
                models={'UNIFORM_SHRINK': dict(parameter_count=123 * hidden,
                    counts={'neural_model_fits': 1, 'optimizer_steps': 1000, 'diagnostic_candidate_predictions': 20})})
            metadata = dict(hidden=hidden, mode=mode, budget=512000, episode_cutoff=3, family='UNIFORM_SHRINK')
            stage['fit_logs'][method] = fit
            stage['model_metadata'][method] = metadata
            run['models'].append(dict(training_life=life, method=method, metadata=metadata))
            for root in run['cohort']['roots']:
                run['decisions'].append(dict(root_id=root['root_id'], training_life=life, method=method,
                    event=B.event(A.OPTIONS[1] if warm else 'H2')))
        run['training'].append(stage)
    return run


def test_warm_scratch_contrasts_share_roots_and_keep_original_baselines_cached():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    warm, scratch = A.CONTRASTS[1]
    matrix = result['comparisons'][warm + '_minus_' + scratch]['reward']['pooled']['selected_utility_delta']
    assert matrix['cells'] == [[1.5, 2.5, 3.5, 4.5]] * 4
    assert matrix['grand_mean'] == 3. and matrix['row_means'] == [3.] * 4
    assert matrix['decomposition']['shares']['cohort'] == 1.
    assert len(result['comparisons']) == 10 and len(result['methods']) == 10
    assert result['cohort']['inherited_model_root_decisions'] == result['cohort']['new_model_root_decisions'] == 128


def test_new_fit_and_scoring_work_is_separate_from_inherited_cohort_and_parameter_lineage():
    result = A.analyze_run(fixture())
    cost = result['actual_executed_work']
    assert cost['newly_sampled_environment_transitions'] == cost['new_model_prefix_transitions'] == 0
    assert cost['new_neural_model_fits'] == 16 and cost['new_optimizer_steps'] == 16000
    assert cost['new_neural_candidate_predictions'] == 640 and cost['new_training_diagnostic_candidate_predictions'] == 320
    assert result['inherited_cohort_extraction_work']['counts']['new_synthetic_transitions'] == 123456
    assert result['inherited_reference_work']['trajectories'] == 1280
    assert result['inherited_v105_total_work']['newly_sampled_environment_transitions'] == 7492903


def test_half_statistics_use_actual_first_batch_roster_and_initialization_is_parameter_only():
    run = fixture()
    assert A.analyze_training(run)['checks']['full_data_and_half_statistics_bound']
    stage = run['training'][0]
    warm = A.NEW_METHODS[1]
    # Newly added episode1 is below half cutoff2 but was not a member of the first batch.
    stage['fit_logs'][warm]['statistics_training_episodes']['reward'].append(1)
    stage['fit_logs'][warm]['optimizer_state'] = 'continued_moments'
    result = A.analyze_training(run)
    assert not result['checks']['full_data_and_half_statistics_bound']
    assert not result['checks']['paired_initializations_and_reset_adam']
    run = fixture()
    run['training'][0]['fit_logs'][warm]['checks']['frozen_half_statistics'] = False
    assert not A.analyze_training(run)['checks']['full_data_and_half_statistics_bound']


def test_missing_new_decision_blocks_matrix_without_rescoring_or_dropping_the_root():
    run = fixture()
    index = next(i for i, row in enumerate(run['decisions']) if row['method'] == A.NEW_METHODS[1])
    run['decisions'].pop(index)
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['full_root_model_and_decision_rosters']
    matrix = result['methods'][A.NEW_METHODS[1]]['reward']['pooled']['selected_reference_utility']
    assert matrix['cells'][0][0] is None and matrix['grand_mean'] is None
    assert result['cohort']['unique_reference_roots'] == 8
    assert result['actual_executed_work']['new_neural_model_fits'] == 16


def test_censoring_preserves_inherited_reference_cost_and_both_fitting_arms():
    run = fixture()
    root = run['cohort']['roots'][0]
    root['reference_complete'] = False
    root['reference_log'].update(censored_root=True, pair_deltas={}, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete'], result['checks']
    assert result['inherited_reference_work']['trajectories'] == 1280
    assert result['actual_executed_work']['new_neural_model_fits'] == 16
    matrix = result['methods'][A.NEW_METHODS[1]]['reward']['pooled']['selected_reference_utility']
    assert all(row[0] is None for row in matrix['cells']) and matrix['grand_mean'] is None
