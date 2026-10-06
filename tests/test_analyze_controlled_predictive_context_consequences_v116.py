"""Synthetic retained logs only; no fitting, router updates or sampled games."""
from copy import deepcopy
import importlib.util
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('context_consequences_analysis_v116',
    ROOT / 'scripts/analyze_controlled_predictive_context_consequences_v116.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def game_cost(steps):
    return dict(sampled_transitions=steps, initial_spawns=2, environment_random_draws=2 * steps + 4)


def fixture():
    settings = dict(lifecycles=list(range(4)), phases=[dict(name=name, p4=p) for name, p in zip(A.PHASES, (.1, .3, .1))],
        source_games_per_phase=18, policies=list(A.POLICIES), modes=list(A.MODES), methods=list(A.METHODS),
        queries=dict(reward={}, risk_goal={}), horizons=[30, 31], stride=4, prediction_replicas=2, control_replicas=2)
    run = dict(status='complete', settings=settings, runner_checks={'independent_seed_streams': True}, lifecycles=[], actual_wall_seconds=1.)
    features = [f'feature_{i}' for i in range(37)] + ['context_p4']
    recipe = dict(max_depth=8, min_samples_leaf=16, random_state=7701)
    for life in settings['lifecycles']:
        history = dict(life=life, phases=[], checks={'causal_source_context': True})
        run['lifecycles'].append(history)
        roster = []
        for pi, phase_definition in enumerate(settings['phases']):
            phase = dict(**phase_definition, source_games=[])
            history['phases'].append(phase)
            for local in range(18):
                episode, policy = pi * 18 + local, A.POLICIES[local % 3]
                game = dict(episode=episode, policy=policy, seed=116000000 + life * 10000 + pi * 100 + local,
                    status='LOST', steps=8, environment_counts=game_cost(8), planning_counts={'legal_swipes': 24},
                    seconds=.001, label_log={'target_rows': 6})
                phase['source_games'].append(game)
                roster.extend(A._expected_records(game, 4, [30, 31]))
            p4 = (.11, .28, .11)[pi]
            cp = dict(phase=phase['name'], router_p4=p4, router_payload={'observations_seen': (pi + 1) * 144},
                models={}, fit_logs={}, predictive_tests=[], control_evaluations=[], prediction_counts={},
                checks={'immutable_old_models_and_no_evaluation_learning': True})
            phase['checkpoint'] = cp
            for mode in A.MODES:
                n = len(roster)
                counts = dict(tree_fits=3, metadata_rows_read=n, training_rows_read=n, feature_rows=n, fit_rows=n)
                counts['context_feature_rows' if mode == 'CONTEXT' else 'constant_context_feature_rows'] = n
                cp['models'][mode] = dict(mode=mode, context_p4=p4, feature_names=features, tree_parameters=recipe,
                    trees={policy: {} for policy in A.POLICIES})
                cp['fit_logs'][mode] = dict(mode=mode, context_p4=p4, feature_names=features, feature_dim=38,
                    tree_parameters=recipe, training_records=n, training_roster=deepcopy(roster),
                    policies={policy: dict(training_rows=n // 3, nodes=3 if mode == 'CONTEXT' else 1,
                        leaves=2 if mode == 'CONTEXT' else 1) for policy in A.POLICIES}, counts=counts, seconds=.01)
            versions = ('CURRENT', 'A_END', 'B_END') if pi == 2 else ('CURRENT',)
            for policy_index, policy in enumerate(A.POLICIES):
                for replica in range(2):
                    steps = 8 + 4 * replica
                    game = dict(policy=policy, replica=replica, seed=116800000 + life * 100000 + pi * 10000 + policy_index * 100 + replica,
                        status='LOST', steps=steps, environment_counts=game_cost(steps), planning_counts={'legal_swipes': steps * 3},
                        seconds=.002, records=[])
                    for window in A._expected_records(dict(episode=replica, policy=policy, steps=steps, status='LOST'), 4, [30, 31]):
                        failure = int(window['anchor_step'] == steps - 1)
                        row = dict(**window, target=[1., float(failure), 0.], predictions={})
                        for version in versions:
                            errors = {'MIXED': 2., 'CONTEXT': 1.}
                            if pi == 2 and version == 'B_END':
                                errors = {'MIXED': 3., 'CONTEXT': 2.}
                            elif pi == 2 and version == 'CURRENT':
                                errors = {'MIXED': 1., 'CONTEXT': .5}
                            row['predictions'][version] = {}
                            for mode, base in errors.items():
                                error = base + replica
                                row['predictions'][version][mode] = [1. + error,
                                    1. - error * .1 if failure else error * .1, error * .05]
                        game['records'].append(row)
                    cp['predictive_tests'].append(game)
            n_predictions = sum(len(game['records']) for game in cp['predictive_tests'])
            cp['prediction_counts'] = {version: {mode: dict(record_prediction_rows=n_predictions,
                policy_prediction_rows=n_predictions, feature_rows=n_predictions) for mode in A.MODES} for version in versions}
            for mi, method in enumerate(A.METHODS):
                for query in settings['queries']:
                    for replica in range(2):
                        score = 1000 + pi * 20 + life * 10 + replica + mi * 8 * (life + 1)
                        cp['control_evaluations'].append(dict(method=method, query=query, replica=replica,
                            seed=117900000 + life * 100000 + pi * 10000 + replica,
                            result=dict(score=score, utility=score / 2048 - (4 if query == 'risk_goal' else 0),
                                status='LOST', steps=64, environment_counts=game_cost(64),
                                planning_counts={'model_spawn_samples': 128}, prediction_counts={'policy_prediction_rows': 32 if mi else 0}, seconds=.003)))
        history['final_router'] = dict(observations_seen=432, counts=dict(observations_received=432, predict_calls=432))
    return run


def test_game_first_averaging_and_context_prediction_contrast():
    result = A.analyze_run(fixture())
    assert result['primary_complete'], result['checks']
    current = result['predictive']['A']['summaries']['CURRENT']
    # Replicas have different trajectory lengths. Equal game weight gives 2.5,
    # whereas pooling their three/four anchors would give 19/7.
    assert current['CONTEXT']['macro_mse']['reward'] == 2.5
    assert current['MIXED']['macro_mse']['reward'] == 6.5
    contrast = result['predictive']['A']['comparisons']['CURRENT_CONTEXT_minus_MIXED']
    assert contrast['mean_mse_delta']['reward'] == -4.
    assert math.isclose(contrast['mean_mse_delta']['failure'], -.04)
    assert len(contrast['lifecycles']) == 4
    assert len(current['CONTEXT']['by_policy_horizon']) == 3


def test_retention_and_relearning_use_same_return_trajectories():
    result = A.analyze_run(fixture())
    differences = result['predictive']['A_RETURN']['comparisons']
    assert differences['MIXED_B_END_minus_A_END']['mean_mse_delta']['reward'] == 6.
    assert differences['CONTEXT_B_END_minus_A_END']['mean_mse_delta']['reward'] == 4.
    assert differences['MIXED_CURRENT_minus_B_END']['mean_mse_delta']['reward'] == -10.
    assert differences['CONTEXT_CURRENT_minus_B_END']['mean_mse_delta']['reward'] == -5.25
    paired = result['control']['A_RETURN']['comparisons']['CONTEXT_PLAN_minus_MIXED_PLAN']['reward']
    assert paired['mean_deltas']['score'] == 20.
    assert [row['deltas']['score'] for row in paired['lifecycles']] == [8., 16., 24., 32.]


def test_physical_sampling_fits_and_old_model_predictions_have_separate_costs():
    result = A.analyze_run(fixture())
    work = result['actual_executed_work']
    assert {name: group['games'] for name, group in work['groups'].items()} == dict(source=216, predictive_evaluation=72, control_evaluation=144)
    assert work['newly_sampled_environment_transitions'] == 11664
    assert work['fit_counts']['tree_fits'] == 72 and work['fit_counts']['fit_rows'] == 5184
    assert work['predictive_inference_counts']['record_prediction_rows'] == 1680
    assert work['router_counts']['observations_received'] == 1728
    assert work['attributed_source_transitions_per_mode'] == dict(MIXED=1728, CONTEXT=1728)
    assert work['imagined_model_spawn_samples'] == 18432


def test_missing_old_version_is_incomplete_without_dropping_the_game():
    run = fixture()
    record = run['lifecycles'][0]['phases'][2]['checkpoint']['predictive_tests'][0]['records'][0]
    del record['predictions']['B_END']
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['predictive_versions_and_windows_complete']
    assert result['predictive']['A_RETURN']['comparisons']['CONTEXT_B_END_minus_A_END']['mean_mse_delta']['reward'] is None
    assert result['actual_executed_work']['groups']['predictive_evaluation']['games'] == 72


def test_future_training_record_or_control_cutoff_invalidates_primary_but_retains_cost():
    run = fixture()
    run['lifecycles'][0]['phases'][0]['checkpoint']['fit_logs']['CONTEXT']['training_roster'][0]['episode'] = 53
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['complete_cumulative_training_rosters']
    run = fixture()
    run['lifecycles'][0]['phases'][2]['checkpoint']['control_evaluations'][0]['result']['status'] = 'CUTOFF'
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['control_games_terminal']
    assert result['control']['A_RETURN']['comparisons']['CONTEXT_PLAN_minus_H2_ONLY']['reward']['mean_deltas']['utility'] is None
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 11664
