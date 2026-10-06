"""Query-gradient masks, inherited decisions and paired matrix directions."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('query_update_analysis_v108', ROOT / 'scripts/analyze_controlled_predictive_query_update_v108.py')
B = load('incremental_fixture_v108', ROOT / 'tests/test_analyze_controlled_predictive_incremental_ranking_v107.py')


def fixture():
    run = B.fixture()
    run['settings'].update(methods=list(A.METHODS), contrasts=[list(pair) for pair in A.CONTRASTS],
        queries=['reward', 'risk_goal'])
    # Both query cohorts are retained; only their reference utility signs differ in this fixture.
    for original in list(run['cohort']['roots']):
        root = deepcopy(original)
        root['root_id'] = root['root_id'].replace('reward', 'risk_goal')
        root['query'] = 'risk_goal'
        for vectors in root['reference_log']['pair_deltas'].values():
            for vector in vectors:
                vector[0] = -abs(vector[0])
        run['cohort']['roots'].append(root)
    for original in list(run['decisions']):
        row = deepcopy(original)
        row['root_id'] = row['root_id'].replace('reward', 'risk_goal')
        run['decisions'].append(row)
    run.update(inherited_model_methods=list(A.OLD_METHODS[2:]), inherited_decisions=len(run['decisions']),
        inherited_v107_work={'new_neural_model_fits': 16, 'new_optimizer_steps': 16000})
    for stage in run['training']:
        old_fits = stage['fit_logs']
        stage['fit_logs'], stage['model_metadata'] = {}, {}
        for base in A.CURRENT:
            for mode in A.MODES:
                method = base + '_FROZEN_STATS_WARM_' + mode
                query = A.MODE_QUERY[mode]
                fit = deepcopy(old_fits[base + '_FROZEN_STATS_WARM'])
                active = len(stage['data_log']['full']['training_episodes'][query])
                fit.update(mode=mode, optimized_queries=[query], active_training_episodes={query:
                    stage['data_log']['full']['training_episodes'][query]}, active_training_roots=active,
                    full_loss_denominator_roots=3, data_loss_weight=active / 3.)
                passes = dict(optimizer_root_passes=1000 * active, optimizer_pair_passes=10000 * active)
                fit['counts'].update(passes)
                fit['models']['UNIFORM_SHRINK']['counts'].update(passes)
                metadata = dict(hidden=fit['hidden'], mode=mode, optimized_queries=[query], budget=512000,
                    episode_cutoff=3, family='UNIFORM_SHRINK')
                stage['fit_logs'][method], stage['model_metadata'][method] = fit, metadata
                run['models'].append(dict(training_life=stage['life'], method=method, metadata=metadata))
                for root in run['cohort']['roots']:
                    run['decisions'].append(dict(root_id=root['root_id'], training_life=stage['life'], method=method,
                        event=B.B.event(A.OPTIONS[1] if mode == 'REWARD_ONLY' else 'H2')))
    run['scoring_log']['counts'].update(model_root_scores=256, neural_candidate_predictions=1280,
        neural_hidden_activations=12800)
    return run


def test_all_fourteen_contrasts_keep_both_query_directions_on_identical_roots():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    left, right = A.CONTRASTS[6]
    comparison = result['comparisons'][left + '_minus_' + right]
    reward = comparison['reward']['pooled']['selected_utility_delta']
    risk = comparison['risk_goal']['pooled']['selected_utility_delta']
    assert reward['cells'] == [[1.5, 2.5, 3.5, 4.5]] * 4
    assert reward['grand_mean'] == 3. and risk['grand_mean'] == -3.
    assert reward['row_directions']['positive'] == risk['row_directions']['negative'] == 4
    assert reward['grand_mean'] == comparison['reward']['A']['selected_utility_delta']['grand_mean']
    assert len(result['comparisons']) == len(result['methods']) == 14
    assert result['cohort']['inherited_model_root_decisions'] == 512
    assert result['cohort']['new_model_root_decisions'] == 256


def test_active_gradient_passes_and_new_fits_are_charged_once_separately_from_old_work():
    result = A.analyze_run(fixture())
    cost = result['actual_executed_work']
    assert cost['newly_sampled_environment_transitions'] == cost['new_model_prefix_transitions'] == 0
    assert cost['new_neural_model_fits'] == 16 and cost['new_optimizer_steps'] == 16000
    assert cost['new_optimizer_root_passes'] == 24000 and cost['new_optimizer_pair_passes'] == 240000
    assert cost['new_neural_candidate_predictions'] == 1280 and cost['new_training_diagnostic_candidate_predictions'] == 320
    assert result['inherited_reference_work']['trajectories'] == 2560
    assert result['inherited_v107_total_work']['new_neural_model_fits'] == 16
    assert result['inherited_cohort_extraction_work']['counts']['new_synthetic_transitions'] == 123456


def test_active_subset_renormalization_or_wrong_query_roster_invalidates_the_comparison():
    run = fixture()
    fit = run['training'][0]['fit_logs'][A.NEW_METHODS[0]]
    assert fit['active_training_roots'] == 2 and fit['full_loss_denominator_roots'] == 3
    fit['full_loss_denominator_roots'] = 2
    fit['data_loss_weight'] = 1.
    assert not A.analyze_run(run)['checks']['active_query_and_full_denominator_bound']
    run = fixture()
    fit = run['training'][0]['fit_logs'][A.NEW_METHODS[1]]
    fit['active_training_episodes'] = {'reward': [0, 1]}
    assert not A.analyze_training(run)['checks']['active_query_and_full_denominator_bound']


def test_missing_query_arm_decision_retains_roster_and_disables_full_matrix():
    run = fixture()
    index = next(i for i, row in enumerate(run['decisions']) if row['method'] == A.NEW_METHODS[0])
    run['decisions'].pop(index)
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['full_root_model_and_decision_rosters']
    matrix = result['methods'][A.NEW_METHODS[0]]['reward']['pooled']['selected_reference_utility']
    assert matrix['cells'][0][0] is None and matrix['grand_mean'] is None
    assert result['cohort']['unique_reference_roots'] == 16
    assert result['actual_executed_work']['new_neural_model_fits'] == 16


def test_censored_reference_keeps_old_cost_and_new_update_work_without_dropping_the_root():
    run = fixture()
    root = run['cohort']['roots'][0]
    root['reference_complete'] = False
    root['reference_log'].update(censored_root=True, pair_deltas={}, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete'], result['checks']
    assert result['inherited_reference_work']['trajectories'] == 2560
    assert result['actual_executed_work']['new_optimizer_root_passes'] == 24000
    matrix = result['methods'][A.NEW_METHODS[0]]['reward']['pooled']['selected_reference_utility']
    assert all(row[0] is None for row in matrix['cells']) and matrix['grand_mean'] is None
