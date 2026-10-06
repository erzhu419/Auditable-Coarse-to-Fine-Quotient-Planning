"""Synthetic cached games, predictions and fits; no learner or environment calls."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('consolidation_analysis_v117', ROOT / 'scripts/analyze_controlled_predictive_consolidation_v117.py')
OLD = load('context_fixture_v117', ROOT / 'tests/test_analyze_controlled_predictive_context_consequences_v116.py')


def counts(values):
    available = sum(value is not None for value in values)
    return dict(prediction_record_requests=len(values), predicted_record_rows=available,
        unavailable_record_rows=len(values) - available, policy_prediction_rows=available)


def fixture():
    run = OLD.fixture()
    run['settings'].update(modes=list(A.MODES), tracks=list(A.TRACKS), methods=list(A.METHODS),
        fit_games_per_phase=12, validation_games_per_phase=6, leaf_budget_per_policy=256)
    for history in run['lifecycles']:
        life = history['life']
        training, validation, archives = [], [], {}
        selected, origin = None, None
        for batch, phase in enumerate(history['phases']):
            cp = phase['checkpoint']
            module = 1 if batch == 1 else 0
            cp['router_module_id'] = module
            for game in phase['source_games']:
                local = game['episode'] % 18
                game['role'] = 'FIT' if local < 12 else 'VALIDATION'
                game['seed'] = 121000000 + life * 10000 + batch * 100 + local
                records = [dict(row, context_module_id=module, batch=batch, target=[1., 0., 0.])
                    for row in A._expected_records(game, 4, [30, 31])]
                (training if local < 12 else validation).extend(records)
            cp['models'], cp['fit_logs'] = {}, {}
            for mode in A.MODES:
                feature_names = [f'f{i}' for i in range(37)]
                recipe = dict(max_depth=8, min_samples_leaf=16, random_state=7701)
                allocations, totals, trees = {}, {}, {}
                for policy in A.POLICIES:
                    rows = [row for row in training if row['policy'] == policy]
                    groups = [None] if mode == 'SHARED' else sorted({row['context_module_id'] for row in rows})
                    allocations[policy] = [dict(module_id=group, training_rows=sum(mode == 'SHARED' or row['context_module_id'] == group for row in rows),
                        leaf_allowance=256 // len(groups), actual_leaves=1, actual_nodes=1, constant_leaf=False) for group in groups]
                    totals[policy] = dict(leaf_budget=256, node_budget=511, allocated_leaves=256,
                        actual_leaves=len(groups), actual_nodes=len(groups), groups=len(groups), training_rows=len(rows))
                    trees[policy] = {'shared' if group is None else str(group): {'left': [-1], 'value': batch + 1} for group in groups}
                cp['models'][mode] = dict(mode=mode, module_id=module, feature_names=feature_names,
                    tree_parameters=recipe, per_policy_leaf_budget=256, per_policy_node_budget=511, trees=trees)
                n, ngroups = len(training), sum(len(group) for group in allocations.values())
                cp['fit_logs'][mode] = dict(mode=mode, module_id=module, feature_names=feature_names, feature_dim=37,
                    tree_parameters=recipe, per_policy_leaf_budget=256, per_policy_node_budget=511,
                    training_records=n, training_roster=[{key: row[key] for key in A.ROSTER_KEYS + ('context_module_id',)} for row in training],
                    group_allocations=allocations, policy_totals=totals,
                    counts=dict(metadata_rows_read=n, training_rows_read=n, fit_rows=n, feature_rows=n,
                        tree_fits=ngroups, constant_leaf_models=0), seconds=.01)
            errors = {'NEW_SHARED': 1., 'NEW_SPLIT': .5} if batch < 2 else {'NEW_SHARED': 2., 'NEW_SPLIT': 2.}
            if batch:
                errors['KEEP'] = 1. if batch == 1 else .5
            predictions = {name: [[row['target'][0] + error, .1 * error, 0.] for row in validation] for name, error in errors.items()}
            result = A.recompute_selection(validation, predictions, batch == 0)
            cp['selection'] = dict(selected_candidate=result['selected_candidate'],
                acceptance={name: {'eligible': eligible} for name, eligible in result['eligible'].items()},
                scores={name: {'batches': value} for name, value in result['losses'].items()})
            cp['validation'] = dict(records=deepcopy(validation), predictions=predictions,
                prediction_counts={name: counts(value) for name, value in predictions.items()})
            chosen = result['selected_candidate']
            if chosen != 'KEEP':
                mode = chosen.removeprefix('NEW_')
                selected, origin = deepcopy(cp['models'][mode]), dict(batch=batch, mode=mode)
            selected['module_id'] = module
            cp['models']['SELECTED'], cp['selected_origin'] = deepcopy(selected), deepcopy(origin)
            for game in cp['predictive_tests']:
                game['seed'] = 119000000 + life * 100000 + batch * 10000 + A.POLICIES.index(game['policy']) * 100 + game['replica']
                for row in game['records']:
                    row['context_module_id'] = module
                    old = row['predictions']
                    row['predictions'] = {version: {'SHARED': group['MIXED'], 'SPLIT': group['CONTEXT']}
                        for version, group in old.items()}
                    for version, group in row['predictions'].items():
                        if version == 'A_END' or batch == 0:
                            group['SELECTED'] = deepcopy(group['SHARED'])
                        elif version == 'CURRENT' and batch == 2:
                            group['SELECTED'] = deepcopy(row['predictions']['B_END']['SPLIT'])
                        else:
                            group['SELECTED'] = deepcopy(group['SPLIT'])
            cp['prediction_counts'] = {version: {track: counts([r['predictions'][version][track]
                for game in cp['predictive_tests'] for r in game['records']]) for track in A.TRACKS}
                for version in cp['predictive_tests'][0]['records'][0]['predictions']}
            old_controls = cp['control_evaluations']
            cp['control_evaluations'] = []
            for method in A.METHODS:
                original = 'H2_ONLY' if method == 'H2_ONLY' else 'MIXED_PLAN' if method == 'SHARED_PLAN' else 'CONTEXT_PLAN'
                for old in old_controls:
                    if old['method'] != original:
                        continue
                    game = deepcopy(old)
                    game['method'] = method
                    game['seed'] = 120000000 + life * 100000 + batch * 10000 + game['replica']
                    game['result'].update(fallback_h2=False, routed_module_id=module)
                    cp['control_evaluations'].append(game)
            if batch < 2:
                archives[phase['name'] + '_END'] = deepcopy(cp['models'])
    return run


def test_complete_choices_prediction_means_and_split_nominal_budget():
    result = A.analyze_run(fixture())
    assert result['primary_complete'], result['checks']
    assert result['selection_counts'] == dict(NEW_SHARED=4, NEW_SPLIT=4, KEEP=4)
    assert result['predictive']['A']['comparisons']['CURRENT_SPLIT_minus_SHARED']['mean_mse_delta']['reward'] == -4.
    assert result['predictive']['A_RETURN']['comparisons']['SELECTED_CURRENT_minus_B_END']['mean_mse_delta']['reward'] == 0.
    assert result['control']['A']['comparisons']['SPLIT_PLAN_minus_SHARED_PLAN']['reward']['mean_deltas']['score'] == 20.


def test_selection_requires_every_batch_and_allows_new_coverage_without_retuning():
    records = [dict(batch=batch, policy='GREEDY', episode=batch, horizon=30, target=[0., 0., 0.]) for batch in (0, 1)]
    values = dict(KEEP=[[1., 1., 1.], [1., 1., 1.]], NEW_SHARED=[[0., 0., 0.], [2., 2., 2.]], NEW_SPLIT=[[1., 1., 1.], [1., 1., 1.]])
    assert A.recompute_selection(records, values)['selected_candidate'] == 'KEEP'
    values['KEEP'][1] = None
    values['NEW_SHARED'] = values['NEW_SPLIT'] = [[1., 1., 1.], [1., 1., 1.]]
    assert A.recompute_selection(records, values)['selected_candidate'] == 'NEW_SHARED'
    values['NEW_SHARED'][0] = None
    values['NEW_SPLIT'] = [[1., 1., 1.], [1., 1., 1.]]
    assert A.recompute_selection(records, values)['selected_candidate'] == 'NEW_SPLIT'


def test_fit_validation_and_outer_costs_remain_distinct():
    work = A.analyze_run(fixture())['actual_executed_work']
    assert {key: group['games'] for key, group in work['groups'].items()} == dict(source=216, predictive_evaluation=72, control_evaluation=192)
    assert {key: group['games'] for key, group in work['source_roles'].items()} == dict(FIT=144, VALIDATION=72)
    assert work['newly_sampled_environment_transitions'] == 14736
    assert work['fit_counts']['tree_fits'] == 96 and work['fit_counts']['fit_rows'] == 3456
    assert work['validation_prediction_counts']['prediction_record_requests'] == 2448
    assert work['outer_prediction_counts']['prediction_record_requests'] == 2520


def test_uncovered_split_is_a_result_not_zero_error_or_engineering_failure():
    run = fixture()
    cp = run['lifecycles'][0]['phases'][2]['checkpoint']
    cp['router_module_id'] = 2
    for game in cp['predictive_tests']:
        for row in game['records']:
            row['context_module_id'] = 2
            for version, groups in row['predictions'].items():
                groups['SPLIT'] = None
                if version != 'A_END':
                    groups['SELECTED'] = None
    for version, groups in cp['prediction_counts'].items():
        for track in groups:
            groups[track] = counts([row['predictions'][version][track] for game in cp['predictive_tests'] for row in game['records']])
    for game in cp['control_evaluations']:
        game['result']['routed_module_id'] = 2
        game['result']['fallback_h2'] = game['method'] in ('SPLIT_PLAN', 'SELECTED_PLAN')
    result = A.analyze_run(run)
    assert result['primary_complete'], result['checks']
    assert result['predictive']['A_RETURN']['summaries']['CURRENT']['SPLIT']['macro_mse']['reward'] is None
    assert any(row['available'] == 0 and row['requested'] > 0 for row in result['prediction_coverage'])
    assert result['control']['A_RETURN']['methods']['SPLIT_PLAN']['reward']['lifecycles'][0]['fallback_games'] == 2
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 14736


def test_validation_in_fit_or_unjustified_selection_is_rejected():
    run = fixture()
    run['lifecycles'][0]['phases'][0]['checkpoint']['fit_logs']['SHARED']['training_roster'][0]['episode'] = 12
    assert not A.analyze_run(run)['checks']['fitting_excludes_reserved_validation']
    run = fixture()
    run['lifecycles'][0]['phases'][1]['checkpoint']['selection']['selected_candidate'] = 'KEEP'
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['source_selection_recomputed']
