"""Frozen synthetic source capsules and cached games; no model execution."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load('utility_analysis_v118', ROOT / 'scripts/analyze_controlled_predictive_utility_consolidation_v118.py')
OLD = load('consolidation_fixture_v118', ROOT / 'tests/test_analyze_controlled_predictive_consolidation_v117.py')
CAP = load('source_capsule_fixture_v118', ROOT / 'src/acfqp/science/controlled_predictive_utility_history_v118.py')


def fixture():
    source = OLD.fixture()
    source.update(schema='acfqp.consolidation.v117.run', supplied_dynamics={'synthetic': True})
    capsule = CAP.source_capsule(source)
    settings = dict(lifecycles=list(range(4)), phases=deepcopy(source['settings']['phases']), policies=list(A.POLICIES),
        tracks=list(A.TRACKS), methods=list(A.METHODS), queries=deepcopy(source['settings']['queries']),
        horizons=[30, 31], stride=4, source_validation_replicas=4, prediction_replicas=2, control_replicas=2)
    run = dict(status='complete', settings=settings, source_capsule_file='source_capsule.json',
        runner_checks={'no_new_fits': True}, lifecycles=[], actual_wall_seconds=1.)
    for source_life, saved_life in zip(source['lifecycles'], capsule['lifecycles']):
        life = source_life['life']
        history = dict(life=life, phases=[], checks={'source_unchanged': True})
        run['lifecycles'].append(history)
        for batch, (old_phase, inherited_phase) in enumerate(zip(source_life['phases'], saved_life['phases'])):
            old, inherited = old_phase['checkpoint'], inherited_phase['checkpoint']
            module = inherited['router_module_id']
            mode = 'SPLIT' if batch == 1 else 'SHARED'
            cp = dict(phase=old_phase['name'], router_p4=inherited['router_p4'], router_module_id=module,
                models=deepcopy(inherited['models']), mse_selected_origin=deepcopy(inherited['mse_selected_origin']),
                utility_selected_origin=dict(batch=batch, mode=mode), source_validation_games=[],
                checks={'new_games_never_update_router': True})
            history['phases'].append(dict(name=old_phase['name'], p4=old_phase['p4'], checkpoint=cp))
            cp['models']['UTILITY_SELECTED'] = deepcopy(cp['models'][mode])
            if batch:
                utilities = dict(KEEP=0., NEW_SHARED=1., NEW_SPLIT=2.) if batch == 1 else dict(KEEP=2., NEW_SHARED=3., NEW_SPLIT=1.)
                for candidate in A.CANDIDATES:
                    for query in settings['queries']:
                        for replica in range(4):
                            result = deepcopy(old['control_evaluations'][0]['result'])
                            utility = utilities[candidate] + replica / 1024
                            result.update(utility=utility, score=(utility + (4 if query == 'risk_goal' else 0)) * 2048)
                            cp['source_validation_games'].append(dict(candidate=candidate, method=candidate, query=query, replica=replica,
                                seed=A.BASE + 1_000_000 + life * 100000 + batch * 10000 + replica, result=result))
                cp['selection'] = A.recompute_utility(cp['source_validation_games'], list(settings['queries']), 4)
            else:
                cp['selection'] = dict(selected_candidate='NEW_SHARED', selection_complete=True, summaries={}, acceptance={})
            cp['predictive_tests'] = deepcopy(old['predictive_tests'])
            for game in cp['predictive_tests']:
                game['seed'] = A.BASE + 2_000_000 + life * 100000 + batch * 10000 + A.POLICIES.index(game['policy']) * 100 + game['replica']
                for row in game['records']:
                    for version, values in row['predictions'].items():
                        values['MSE_SELECTED'] = values.pop('SELECTED')
                        selected_track = 'SPLIT' if version == 'B_END' or (version == 'CURRENT' and batch == 1) else 'SHARED'
                        values['UTILITY_SELECTED'] = deepcopy(values[selected_track])
            cp['prediction_counts'] = {version: {track: OLD.counts([r['predictions'][version][track]
                for game in cp['predictive_tests'] for r in game['records']]) for track in A.TRACKS}
                for version in cp['predictive_tests'][0]['records'][0]['predictions']}
            cp['control_evaluations'] = []
            methods = A.METHODS + (('UTILITY_B_END_PLAN',) if batch == 2 else ())
            for method in methods:
                original = ('SELECTED_PLAN' if method == 'MSE_SELECTED_PLAN' else mode + '_PLAN'
                    if method == 'UTILITY_SELECTED_PLAN' else 'SPLIT_PLAN' if method == 'UTILITY_B_END_PLAN' else method)
                for game in old['control_evaluations']:
                    if game['method'] != original:
                        continue
                    row = deepcopy(game)
                    row.update(method=method, seed=A.BASE + 3_000_000 + life * 100000 + batch * 10000 + game['replica'])
                    cp['control_evaluations'].append(row)
    return run, capsule


def test_choices_complete_game_means_and_old_return_controller():
    run, capsule = fixture()
    result = A.analyze_run(run, capsule)
    assert result['primary_complete'], result['checks']
    assert result['selection_counts'] == dict(NEW_SHARED=8, NEW_SPLIT=4)
    paired = result['control']['A_RETURN']['comparisons']['UTILITY_SELECTED_PLAN_minus_UTILITY_B_END_PLAN']['reward']
    assert paired['mean_deltas']['score'] == -20.
    assert [row['deltas']['score'] for row in paired['lifecycles']] == [-8., -16., -24., -32.]
    assert result['predictive']['A_RETURN']['comparisons']['CURRENT_UTILITY_SELECTED_minus_SHARED']['mean_mse_delta']['reward'] == 0.


def test_query_protection_exact_tie_and_incomplete_means():
    run, _ = fixture()
    rows = run['lifecycles'][0]['phases'][1]['checkpoint']['source_validation_games']
    values = dict(KEEP=dict(reward=1., risk_goal=1.), NEW_SHARED=dict(reward=3., risk_goal=0.), NEW_SPLIT=dict(reward=2., risk_goal=1.))
    for row in rows:
        row['result']['utility'] = values[row['candidate']][row['query']]
    assert A.recompute_utility(rows, ['reward', 'risk_goal'], 4)['selected_candidate'] == 'NEW_SPLIT'
    for row in rows:
        if row['candidate'] == 'NEW_SHARED':
            row['result']['utility'] = values['NEW_SPLIT'][row['query']]
    assert A.recompute_utility(rows, ['reward', 'risk_goal'], 4)['selected_candidate'] == 'NEW_SHARED'
    rows[0]['result']['status'] = 'CUTOFF'
    result = A.recompute_utility(rows, ['reward', 'risk_goal'], 4)
    assert not result['selection_complete'] and result['selected_candidate'] == 'KEEP'
    assert all(row['mean_utility'] is None for row in result['summaries'].values())


def test_new_520_games_and_inherited_source_are_counted_separately():
    result = A.analyze_run(*fixture())
    new, old = result['actual_executed_work'], result['inherited_source_work']
    assert {key: group['games'] for key, group in new['groups'].items()} == dict(source_utility_validation=192, predictive_evaluation=72, control_evaluation=256)
    assert new['newly_sampled_environment_transitions'] == 29392
    assert new['new_tree_fits'] == new['new_router_observations'] == 0
    assert new['outer_prediction_counts']['prediction_record_requests'] == 3360
    assert old['physical_source_transitions'] == 1728 and old['fit_counts']['tree_fits'] == 96
    assert old['source_roles']['FIT']['games'] == 144 and old['source_roles']['VALIDATION']['games'] == 72
    assert old['attributed_source_transitions_per_track'] == {track: 1728 for track in A.TRACKS}


def test_missing_split_coverage_keeps_null_error_and_explicit_fallback():
    run, capsule = fixture()
    cp = run['lifecycles'][0]['phases'][2]['checkpoint']
    capsule['lifecycles'][0]['phases'][2]['checkpoint']['router_module_id'] = cp['router_module_id'] = 2
    for game in cp['predictive_tests']:
        for row in game['records']:
            row['context_module_id'] = 2
            for version, groups in row['predictions'].items():
                groups['SPLIT'] = None
                if version != 'A_END':
                    groups['MSE_SELECTED'] = None
                if version == 'B_END':
                    groups['UTILITY_SELECTED'] = None
    for version, groups in cp['prediction_counts'].items():
        for track in groups:
            groups[track] = OLD.counts([r['predictions'][version][track] for game in cp['predictive_tests'] for r in game['records']])
    for game in cp['source_validation_games']:
        game['result'].update(routed_module_id=2, fallback_h2=game['candidate'] in ('KEEP', 'NEW_SPLIT'))
    for game in cp['control_evaluations']:
        game['result'].update(routed_module_id=2, fallback_h2=game['method'] in ('SPLIT_PLAN', 'MSE_SELECTED_PLAN', 'UTILITY_B_END_PLAN'))
    result = A.analyze_run(run, capsule)
    assert result['primary_complete'], result['checks']
    assert result['predictive']['A_RETURN']['summaries']['B_END']['UTILITY_SELECTED']['macro_mse']['reward'] is None
    assert result['control']['A_RETURN']['methods']['UTILITY_B_END_PLAN']['reward']['lifecycles'][0]['fallback_games'] == 2


def test_changed_frozen_model_or_censored_validation_invalidates_without_refunding():
    run, capsule = fixture()
    run['lifecycles'][0]['phases'][0]['checkpoint']['models']['SHARED']['trees']['GREEDY']['shared']['value'] = 999
    assert not A.analyze_run(run, capsule)['checks']['frozen_models_and_router']
    run, capsule = fixture()
    run['lifecycles'][0]['phases'][1]['checkpoint']['source_validation_games'][0]['result']['status'] = 'CUTOFF'
    result = A.analyze_run(run, capsule)
    assert not result['primary_complete'] and not result['checks']['source_validation_complete']
    assert result['actual_executed_work']['groups']['source_utility_validation']['games'] == 192
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 29392
