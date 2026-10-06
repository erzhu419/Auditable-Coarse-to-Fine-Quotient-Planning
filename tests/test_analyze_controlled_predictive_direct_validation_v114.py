"""Actual-deployment source validation, fixed target caches and separate cost."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('direct_validation_analysis_v114', ROOT / 'scripts/analyze_controlled_predictive_direct_validation_v114.py')
B = load('fresh_targets_fixture_v114', ROOT / 'tests/test_analyze_controlled_predictive_fresh_targets_v113.py')


def fixture():
    run = B.fixture()
    # Synthetic prior result only; no previous production analysis is repeated.
    run['inherited_target_analysis'] = B.A.analyze_run(run)
    run['inherited_target_decisions'] = deepcopy(run['decisions'])
    run['inherited_target_scoring_log'] = deepcopy(run['scoring_log'])
    run['inherited_runner_checks'] = deepcopy(run['runner_checks'])
    run['settings'].update(methods=list(A.METHODS), contrasts=[list(pair) for pair in A.CONTRASTS])
    run['source_cohort'] = B.B.fixture()['cohort']
    roots, bundles, queries = run['source_cohort']['roots'], run['settings']['source_bundles'], run['settings']['queries']
    run.update(source_decisions=[], direct_selections=[], source_overlap_check=dict(training_roots=24,
        validation_roots=16, source_seed_overlap_count=0, board_overlap_count=0,
        checks={'seeds_disjoint': True, 'boards_disjoint': True}))
    for bundle in bundles:
        sources = [life for life in bundles if life != bundle]
        for root in roots:
            if root['life'] not in sources:
                continue
            for method in A.BASE_METHODS:
                run['source_decisions'].append(dict(bundle_id=bundle, root_id=root['root_id'], validation_life=root['life'],
                    method=method, event=B.B.B.event(A.OPTIONS[1] if method.endswith('_FULL') else 'H2')))
        for hidden in A.WIDTHS:
            for query in queries:
                sign = 1 if query == 'reward' else -1
                folds = []
                for life in sources:
                    group = sorted((root for root in roots if root['life'] == life and root['query'] == query),
                        key=lambda root: root['episode'])
                    folds.append(dict(validation_life=life, source_lives=sources,
                        root_ids=[root['root_id'] for root in group], mean_utility_delta=sign * (life - 10 + .5)))
                average = sum(fold['mean_utility_delta'] for fold in folds) / 3
                stage = 'FULL' if average > 0 else 'HALF'
                choice = dict(heldout_life=bundle, hidden=hidden, query=query, source_lives=sources,
                    validation_folds=folds, mean_utility_delta=average, chosen_stage=stage, chosen_method=f'POOLED_H{hidden}_{stage}')
                run['direct_selections'].append(choice)
                metadata = next(row['metadata'] for row in run['models'] if row['bundle_id'] == bundle and row['method'] == choice['chosen_method'])
                for root in run['cohort']['roots']:
                    if root['query'] != query:
                        continue
                    event = next(row['event'] for row in run['decisions'] if row['root_id'] == root['root_id']
                        and row['bundle_id'] == bundle and row['method'] == choice['chosen_method'])
                    run['decisions'].append(dict(bundle_id=bundle, root_id=root['root_id'], target_life=root['life'],
                        method=f'DIRECT_H{hidden}', chosen_method=choice['chosen_method'], chosen_model_path=metadata['path'], event=deepcopy(event)))
    bindings = [dict(bundle_id=row['bundle_id'], method=row['method'], source_lives=row['metadata']['source_lives'],
        retained_model_path=row['metadata']['path'], loaded_model_path=f"relocated/{row['metadata']['path']}") for row in run['models']]
    run['source_scoring_log'] = dict(validation_source_models='three_source_deployment', model_bindings=bindings,
        checks={'metadata_bound': True}, seconds=.01, counts=dict(model_payloads_loaded=16, model_root_scores=192,
            neural_candidate_predictions=960, neural_hidden_activations=9600, neural_model_fits=0, optimizer_steps=0,
            new_environment_transitions=0, new_synthetic_transitions=0, model_prefix_trajectories=0))
    run['direct_selection_log'] = dict(validation_source_models='three_source_deployment', checks={'source_only': True}, seconds=.01,
        counts=dict(selections=16, validation_folds=48, root_comparisons=96, cached_decision_lookups=192,
            neural_candidate_predictions=0, neural_model_fits=0, optimizer_steps=0,
            new_environment_transitions=0, new_synthetic_transitions=0))
    run['derived_log'] = dict(checks={'target_cache_bound': True}, seconds=.01,
        counts=dict(derived_decisions=128, cached_decision_lookups=128, new_neural_candidate_predictions=0))
    run['inherited_work']['V113'] = deepcopy(run['inherited_target_analysis']['actual_executed_work'])
    return run


def test_direct_validation_changes_only_the_model_pair_and_retains_full_target_matrix():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    matrix = result['comparisons']['DIRECT_H4_minus_SELECTED_H4']['reward']['pooled']['selected_utility_delta']
    assert matrix['cells'] == [[0.] * 4] * 3 + [[1.5, 2.5, 3.5, 4.5]]
    assert matrix['row_means'] == [0., 0., 0., 3.] and matrix['grand_mean'] == .75
    assert result['comparisons']['DIRECT_H4_minus_SELECTED_H4']['risk_goal']['pooled']['selected_utility_delta']['grand_mean'] == 2.25
    assert result['source_selection']['choice_counts']['4'] == {'reward': {'HALF': 0, 'FULL': 4}, 'risk_goal': {'HALF': 4, 'FULL': 0}}
    assert result['source_selection']['changed_selections'] == 8
    assert len(result['methods']) == 9 and len(result['comparisons']) == 8


def test_only_source_scoring_and_new_choices_are_new_work_not_target_sampling():
    result = A.analyze_run(fixture())
    work = result['actual_executed_work']
    assert work['newly_sampled_environment_transitions'] == work['new_model_prefix_transitions'] == 0
    assert work['new_neural_model_fits'] == work['new_optimizer_steps'] == work['new_target_neural_candidate_predictions'] == 0
    assert work['new_source_model_root_decisions'] == 192 and work['new_neural_candidate_predictions'] == 960
    assert work['new_selection_decisions'] == 16 and work['derived_target_decisions'] == 128
    assert result['inherited_target_evaluation_work']['newly_sampled_environment_transitions'] == 1760
    assert result['inherited_selection_acquisition_accounting']['learning_environment_transitions'] == 7270651


def test_missing_source_candidate_and_training_overlap_invalidate_direct_choice():
    run = fixture()
    run['source_decisions'].pop(0)
    run['source_overlap_check']['source_seed_overlap_count'] = 1
    result = A.analyze_run(run)
    assert not result['primary_complete']
    assert not result['checks']['complete_actual_model_validation_decisions']
    assert not result['checks']['direct_source_selection_recomputed']
    assert not result['checks']['source_validation_samples_disjoint_from_training']


def test_target_feedback_or_changed_old_selected_events_cannot_pass_cache_binding():
    run = fixture()
    choice = run['direct_selections'][0]
    choice['validation_folds'][0]['root_ids'][0] = run['cohort']['roots'][0]['root_id']
    derived = next(row for row in run['decisions'] if row['method'] == 'DIRECT_H4')
    derived['event'] = B.B.B.event('H2')
    old = next(row for row in run['decisions'] if row['method'] == 'SELECTED_H4')
    old['event'] = B.B.B.event('H2')
    result = A.analyze_run(run)
    assert not result['primary_complete']
    assert not result['checks']['direct_source_selection_recomputed']
    assert not result['checks']['selected_direct_target_events_exact']
    assert not result['checks']['inherited_target_decisions_exact']


def test_censored_target_reference_blocks_its_entire_matrix_column_without_new_cost():
    run = fixture()
    root = run['cohort']['roots'][0]
    root['reference_complete'] = False
    root['reference_log'].update(censored_root=True, pair_deltas={}, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete'], result['checks']
    matrix = result['methods']['DIRECT_H4']['reward']['pooled']['selected_reference_utility']
    assert all(row[0] is None for row in matrix['cells']) and matrix['grand_mean'] is None
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 0
    assert result['inherited_target_evaluation_work']['new_reference_transitions'] == 1600
