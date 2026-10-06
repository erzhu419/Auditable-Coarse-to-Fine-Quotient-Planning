"""Fresh target matrices, frozen derived actions and real/synthetic cost boundaries."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('fresh_targets_analysis_v113', ROOT / 'scripts/analyze_controlled_predictive_fresh_targets_v113.py')
B = load('pooled_fixture_v113', ROOT / 'tests/test_analyze_controlled_predictive_pooled_history_v110.py')


def fixture():
    old = B.fixture()
    settings = dict(old['settings'], source_bundles=[11, 12, 13, 14], lifecycles=[15, 16, 17, 18],
        methods=list(A.METHODS), contrasts=[list(pair) for pair in A.CONTRASTS],
        prefix_replicas=32, horizon=4, feature_dim=121, source_life_base=113000,
        prefix_seed_base=253000000000, reference_life_base=113000,
        new_neural_model_fits=0, new_optimizer_steps=0)
    source_models = deepcopy(old['models'])
    for row in source_models:
        row['metadata']['path'] = f"frozen/{row['heldout_life']}/{row['method']}.json"
    models = [dict(bundle_id=row['heldout_life'], method=row['method'], metadata=deepcopy(row['metadata'])) for row in source_models]
    roots = []
    for original in old['cohort']['roots']:
        root = deepcopy(original)
        root['life'] += 4
        root['root_id'] = f"{root['life']}_{root['query']}_{root['episode']}"
        root['source_seed'] = 8300000 + (113000 + root['life']) * 10000 + root['episode']
        root['prefix_seed'] = (253000000000 + root['life'] * 10000000
            + settings['queries'].index(root['query']) * 1000000 + root['episode'] * 1000)
        root['features'] = [[0.] * 121 for _ in A.OPTIONS]
        root['reference_log']['ground_work']['environment_random_draws'] = 200
        root['reference_log']['pair_deltas'][A.OPTIONS[2]] = [
            [2 * value for value in row] for row in root['reference_log']['pair_deltas'][A.OPTIONS[1]]]
        roots.append(root)
    histories = []
    for life in settings['lifecycles']:
        group = [root for root in roots if root['life'] == life]
        histories.append(dict(life=life, roots=deepcopy(group), missing_roots=[], checks={'source_semantics': True},
            source_log=dict(games=4, roots=4, ground_work={'sampled_transitions': 40, 'environment_random_draws': 96},
                planning_counts={}, outcomes={'LOST': 4}, seconds=.01),
            prefix_log=dict(trajectories=640, model_work={'synthetic_transitions': 2000, 'spawn_uniform_draws': 4000},
                planning_counts={'model_uniform_draws': 8000}, feature_counts={'candidate_feature_vectors': 20},
                outcomes={'ACTIVE': 640}, wiring={'paired': True}, seconds=.01), seconds=.02))
    choices, bindings, decisions = [], [], []
    for bundle in settings['source_bundles']:
        for hidden in A.WIDTHS:
            for query in settings['queries']:
                stage = 'FULL' if bundle in (11, 12) else 'HALF'
                method = f'POOLED_H{hidden}_{stage}'
                metadata = next(row['metadata'] for row in models if row['bundle_id'] == bundle and row['method'] == method)
                choices.append(dict(heldout_life=bundle, hidden=hidden, query=query, source_lives=metadata['source_lives'],
                    chosen_stage=stage, chosen_method=method))
                bindings.append(dict(bundle_id=bundle, hidden=hidden, query=query, source_lives=metadata['source_lives'],
                    chosen_stage=stage, chosen_method=method, chosen_model_path=metadata['path']))
        for root in roots:
            for method in A.BASE_METHODS:
                option = 'H2'
                if method.endswith('_FULL'):
                    option = A.OPTIONS[2] if bundle == 12 else A.OPTIONS[1] if bundle in (11, 14) else 'H2'
                decisions.append(dict(bundle_id=bundle, root_id=root['root_id'], target_life=root['life'],
                    method=method, event=B.B.event(option)))
            for hidden in A.WIDTHS:
                choice = next(row for row in bindings if row['bundle_id'] == bundle and row['hidden'] == hidden and row['query'] == root['query'])
                cached = next(row['event'] for row in decisions if row['bundle_id'] == bundle and row['root_id'] == root['root_id']
                    and row['method'] == choice['chosen_method'])
                decisions.append(dict(bundle_id=bundle, root_id=root['root_id'], target_life=root['life'], method=f'SELECTED_H{hidden}',
                    event=deepcopy(cached), chosen_method=choice['chosen_method'], chosen_model_path=choice['chosen_model_path']))
    counts = dict(model_payloads_loaded=16, model_root_scores=256, neural_candidate_predictions=1280,
        neural_hidden_activations=12800, derived_decisions=128, cached_decision_lookups=128,
        new_environment_transitions=0, new_synthetic_transitions=0, neural_model_fits=0, optimizer_steps=0, model_prefix_trajectories=0)
    return dict(status='complete', settings=settings, histories=histories, cohort=dict(roots=roots,
        missing_roots=[], expected_roots=16, completed_references=16), source_models=source_models,
        source_folds=old['folds'], frozen_selections=choices, models=models, decisions=decisions,
        scoring_log=dict(counts=counts, choices_binding=bindings, checks={'frozen_recipe': True}, seconds=.01),
        runner_checks={'predictions_before_references': True}, inherited_work={'V112': {'new_optimizer_steps': 24000}},
        inherited_selection_acquisition_accounting={'learning_environment_transitions': 7270651},
        inherited_cohort_extraction_work=old['cohort']['log'], actual_wall_seconds=.1)


def test_full_source_target_matrix_has_equal_axes_without_diagonal_replacement():
    result = A.analyze_run(fixture())
    assert result['complete'] and result['primary_complete'], result['checks']
    matrix = result['comparisons']['SELECTED_H4_minus_POOLED_H4_HALF']['reward']['pooled']['selected_utility_delta']
    assert matrix['cells'] == [[1.5, 2.5, 3.5, 4.5], [3., 5., 7., 9.], [0.] * 4, [0.] * 4]
    assert matrix['row_means'] == [3., 6., 0., 0.]
    assert matrix['column_means'] == [1.125, 1.875, 2.625, 3.375]
    assert matrix['grand_mean'] == 2.25 and matrix['diagonal']['mean'] is None
    assert len(result['methods']) == 7 and len(result['comparisons']) == 8


def test_source_reference_and_prefix_work_are_new_while_learning_is_inherited():
    result = A.analyze_run(fixture())
    work = result['actual_executed_work']
    assert work['new_h2_source_transitions'] == 160 and work['new_reference_transitions'] == 1600
    assert work['newly_sampled_environment_transitions'] == 1760
    assert work['new_model_prefix_transitions'] == 8000 and work['new_model_prefix_trajectories'] == 2560
    assert work['new_neural_model_fits'] == work['new_optimizer_steps'] == work['new_selection_decisions'] == 0
    assert work['new_neural_candidate_predictions'] == 1280 and work['derived_decisions'] == 128
    assert result['inherited_total_work']['V112']['new_optimizer_steps'] == 24000
    run = fixture()
    run['histories'][0]['prefix_log']['model_work']['spawn_uniform_draws'] += 1
    assert not A.analyze_run(run)['checks']['source_and_prefix_work_accounted']


def test_source_cutoff_after_trigger_is_valid_but_reference_cutoff_blocks_every_affected_row():
    run = fixture()
    run['histories'][0]['source_log']['outcomes'] = {'LOST': 3, 'CUTOFF': 1}
    result = A.analyze_run(run)
    assert result['primary_complete'] and result['actual_executed_work']['source_games_with_cutoff'] == 1
    root = run['cohort']['roots'][0]
    root['reference_complete'] = False
    root['reference_log'].update(censored_root=True, pair_deltas={}, outcomes={'LOST': 159, 'CUTOFF': 1})
    result = A.analyze_run(run)
    assert result['complete'] and not result['primary_complete'], result['checks']
    matrix = result['methods']['SELECTED_H4']['reward']['pooled']['selected_reference_utility']
    assert all(row[0] is None for row in matrix['cells']) and matrix['grand_mean'] is None
    assert result['actual_executed_work']['new_reference_transitions'] == 1600


def test_missing_crossed_decision_does_not_shrink_the_target_or_fill_from_selected_event():
    run = fixture()
    run['decisions'].pop(0)
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['complete_crossed_model_and_decision_rosters']
    matrix = result['methods'][A.BASE_METHODS[0]]['reward']['pooled']['selected_reference_utility']
    assert matrix['cells'][0][0] is None and matrix['grand_mean'] is None
    assert result['cohort']['unique_reference_roots'] == 16


def test_changed_fresh_stream_or_derived_choice_cannot_pass_frozen_transfer():
    run = fixture()
    run['cohort']['roots'][0]['source_seed'] = 8300000 + 11 * 10000
    selected = next(row for row in run['decisions'] if row['method'] == 'SELECTED_H4')
    selected['event'] = B.B.event('H2')
    result = A.analyze_run(run)
    assert not result['primary_complete']
    assert not result['checks']['fresh_root_streams_and_features_bound']
    assert not result['checks']['frozen_choice_binding_and_derived_events']
