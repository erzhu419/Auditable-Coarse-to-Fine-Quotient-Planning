"""Independent source selection reconstruction, derived actions and inherited costs."""
from copy import deepcopy
from itertools import combinations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('nested_analysis_v112', ROOT / 'scripts/analyze_controlled_predictive_nested_selection_v112.py')
B = load('pooled_fixture_v112', ROOT / 'tests/test_analyze_controlled_predictive_pooled_history_v110.py')


def fixture():
    run = B.fixture()
    settings, roots = run['settings'], run['cohort']['roots']
    settings.update(methods=list(A.METHODS), contrasts=[list(pair) for pair in A.CONTRASTS])
    lives, queries = settings['lifecycles'], settings['queries']
    run.update(inherited_folds=deepcopy(run['folds']), inherited_model_count=len(run['models']),
        inherited_decisions=len(run['decisions']), pairs=[], inner_models=[], inner_decisions=[], selections=[])
    rosters = run['bank_log']['rosters']
    for sources_ in combinations(lives, 2):
        sources = list(sources_)
        pair_id, validation = '_'.join(map(str, sources)), [life for life in lives if life not in sources]
        data = dict(pair_id=pair_id, source_lives=sources, validation_lives=validation,
            checks={'source_pool_bound': True}, seconds=.01)
        for stage in ('half', 'full'):
            data[stage] = B.summary([row for life in sources for row in rosters[str(life)][stage]['training_roster']],
                [row for life in sources for row in rosters[str(life)][stage]['heldout_roster']])
        pair = dict(pair_id=pair_id, source_lives=sources, validation_lives=validation,
            data_log=data, fit_logs={}, model_metadata={})
        for hidden in A.WIDTHS:
            for stage, budget in zip(('HALF', 'FULL'), settings['budgets']):
                method = f'POOLED_H{hidden}_{stage}'
                fit = deepcopy(run['inherited_folds'][0]['fit_logs'][method])
                summary = data[stage.lower()]
                fit.update(source_lives=sources, training_roster=deepcopy(summary['training_roster']),
                    heldout_roster=deepcopy(summary['heldout_roster']), statistics_roster=deepcopy(data['half']['training_roster']),
                    training_roots=summary['training_roots'], heldout_roots=summary['heldout_roots'],
                    normalization_training_roots=4, conflict_mass_training_roots=4,
                    training_replica_rows=4 * summary['training_roots'], total_training_pairs=10 * summary['training_roots'])
                fit['counts'].update(optimizer_root_passes=1000 * summary['training_roots'],
                    optimizer_pair_passes=10000 * summary['training_roots'], diagnostic_candidate_predictions=5 * summary['records'])
                fit['models']['UNIFORM_SHRINK']['counts'] = deepcopy(fit['counts'])
                metadata = dict(hidden=hidden, family='UNIFORM_SHRINK', stage=stage, source_lives=sources,
                    validation_lives=validation, checkpoint=budget, budget=budget, parameter_count=123 * hidden)
                pair['fit_logs'][method], pair['model_metadata'][method] = fit, metadata
                run['inner_models'].append(dict(pair_id=pair_id, method=method, metadata=metadata))
                for root in roots:
                    if root['life'] in validation:
                        run['inner_decisions'].append(dict(pair_id=pair_id, root_id=root['root_id'], validation_life=root['life'],
                            method=method, event=B.B.event(A.OPTIONS[1] if stage == 'FULL' else 'H2')))
        run['pairs'].append(pair)
    for outer in lives:
        sources = [life for life in lives if life != outer]
        for hidden in A.WIDTHS:
            for query in queries:
                sign = 1 if query == 'reward' else -1
                folds = []
                for validation in sources:
                    training = [life for life in sources if life != validation]
                    group = sorted((root for root in roots if root['life'] == validation and root['query'] == query),
                        key=lambda root: root['episode'])
                    folds.append(dict(validation_life=validation, pair_id='_'.join(map(str, training)), source_lives=training,
                        root_ids=[root['root_id'] for root in group], mean_utility_delta=sign * (validation - 10 + .5)))
                average = sum(row['mean_utility_delta'] for row in folds) / 3
                stage = 'FULL' if average > 0 else 'HALF'
                choice = dict(heldout_life=outer, hidden=hidden, query=query, source_lives=sources,
                    validation_folds=folds, mean_utility_delta=average, chosen_stage=stage, chosen_method=f'POOLED_H{hidden}_{stage}')
                run['selections'].append(choice)
                for root in roots:
                    if root['life'] == outer and root['query'] == query:
                        cached = next(row['event'] for row in run['decisions'] if row['root_id'] == root['root_id']
                            and row['method'] == choice['chosen_method'])
                        run['decisions'].append(dict(root_id=root['root_id'], heldout_life=outer,
                            method=f'SELECTED_H{hidden}', event=deepcopy(cached)))
    run['scoring_log']['counts'].update(model_payloads_loaded=24, model_root_scores=192,
        neural_candidate_predictions=960, neural_hidden_activations=9600)
    run['selection_log'] = dict(checks={'source_only': True}, seconds=.01, counts=dict(selections=16,
        validation_folds=48, root_comparisons=96, cached_decision_lookups=192,
        neural_candidate_predictions=0, neural_model_fits=0, new_environment_transitions=0, new_synthetic_transitions=0))
    run['derived_log'] = dict(checks={'selected_event_exact': True}, seconds=.01,
        counts=dict(derived_outer_decisions=32, cached_outer_decision_lookups=32, new_neural_candidate_predictions=0))
    def work(n):
        return dict(roots=n, trajectories=160 * n, sampled_transitions=100 * n,
            ground_work={'sampled_transitions': 100 * n}, planning_counts={'model_uniform_draws': 400 * n}, outcomes={'LOST': 160 * n})
    run['selection_acquisition_accounting'] = dict(
        per_history=[dict(life=life, half_transitions=256000, full_transitions=512000, reference_work=work(4)) for life in lives],
        per_fold=[dict(heldout_life=life, source_lives=[other for other in lives if other != life],
            source_training_transitions=1536000, half_baseline_training_transitions=768000, full_baseline_training_transitions=1536000,
            selection_validation_work=work(12), outer_evaluation_work=work(4),
            learning_validation_environment_transitions=1537200, outer_evaluation_environment_transitions=400) for life in lives],
        unique_physical=dict(source_lives=lives, training_environment_transitions=2048000,
            reference_work=work(16), training_plus_reference_environment_transitions=2049600),
        newly_sampled_environment_transitions=0, checks={'source_validation_charged': True})
    run['inherited_work']['V111'] = {'new_optimizer_steps': 8000}
    return run


def test_nested_choice_and_outer_means_keep_the_prespecified_two_candidates():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    reward = result['comparisons']['SELECTED_H4_minus_POOLED_H4_HALF']['reward']['pooled']['selected_utility_delta']
    risk = result['comparisons']['SELECTED_H4_minus_POOLED_H4_FULL']['risk_goal']['pooled']['selected_utility_delta']
    assert reward['fold_means'] == [1.5, 2.5, 3.5, 4.5] and reward['grand_mean'] == risk['grand_mean'] == 3.
    assert result['selection']['choice_counts']['4'] == {'reward': {'HALF': 0, 'FULL': 4}, 'risk_goal': {'HALF': 4, 'FULL': 0}}
    assert result['selection_transfer']['16']['risk_goal']['pooled']['same_direction'] == 4
    assert len(result['methods']) == 7 and len(result['comparisons']) == 8


def test_new_inner_fit_costs_and_inherited_validation_learning_cost_are_separate():
    result = A.analyze_run(fixture())
    work = result['actual_executed_work']
    assert work['newly_sampled_environment_transitions'] == work['new_model_prefix_transitions'] == 0
    assert work['new_neural_model_fits'] == 24 and work['new_optimizer_steps'] == 24000
    assert work['new_optimizer_root_passes'] == 144000 and work['new_optimizer_pair_passes'] == 1440000
    assert work['new_optimizer_parameter_updates'] == 29520000
    assert work['new_training_diagnostic_candidate_predictions'] == 1200
    assert work['new_neural_candidate_predictions'] == 960 and work['new_inner_model_root_decisions'] == 192
    assert work['derived_outer_decisions'] == 32 and work['new_outer_neural_candidate_predictions'] == 0
    assert result['inherited_reference_work']['trajectories'] == 2560
    costs = result['selection_acquisition_accounting']
    assert costs['unique_physical']['reference_work']['sampled_transitions'] == 1600
    assert costs['per_fold'][0]['learning_validation_environment_transitions'] == 1537200
    assert result['inherited_total_work']['V111']['new_optimizer_steps'] == 8000
    run = fixture()
    run['selection_acquisition_accounting']['unique_physical']['training_plus_reference_environment_transitions'] *= 4
    assert not A.analyze_run(run)['checks']['source_reference_validation_charged_as_learning']


def test_missing_inner_candidate_disables_source_choice_without_hiding_cached_outer_results():
    run = fixture()
    run['inner_decisions'].pop(0)
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['complete_inner_model_decision_rosters']
    assert not result['checks']['source_only_selection_recomputed']
    assert result['comparisons']['POOLED_H4_FULL_minus_POOLED_H4_HALF']['reward']['pooled']['selected_utility_delta']['grand_mean'] == 3.
    assert result['actual_executed_work']['new_neural_model_fits'] == 24


def test_outer_reference_or_training_history_contamination_cannot_validate_a_choice():
    run = fixture()
    choice = run['selections'][0]
    choice['validation_folds'][0]['validation_life'] = choice['heldout_life']
    choice['validation_folds'][0]['root_ids'][0] = 'life_11_reward_0'
    run['pairs'][0]['fit_logs']['POOLED_H4_HALF']['training_roster'][0][0] = 13
    result = A.analyze_run(run)
    assert not result['primary_complete']
    assert not result['checks']['source_only_selection_recomputed']
    assert not result['checks']['inner_validation_histories_excluded']


def test_derived_selected_event_must_equal_the_source_chosen_cached_outer_event():
    run = fixture()
    row = next(row for row in run['decisions'] if row['method'] == 'SELECTED_H4')
    row['event'] = B.B.event('H2')
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['selected_events_match_chosen_outer_model']
    assert result['checks']['source_only_selection_recomputed']
    assert result['actual_executed_work']['new_outer_neural_candidate_predictions'] == 0
