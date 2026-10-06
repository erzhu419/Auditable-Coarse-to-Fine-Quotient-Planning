"""Synthetic chronological logs; no environment, learner or planner is executed."""
from collections import Counter
from copy import deepcopy
import importlib.util
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('regime_memory_analysis_v115',
    ROOT / 'scripts/analyze_controlled_predictive_regime_memory_v115.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def fixture():
    checkpoints = {'A': (6,), 'B': (1, 3, 6), 'A_RETURN': (1, 3, 6)}
    phases = [('A', .1), ('B', .3), ('A_RETURN', .1)]
    settings = dict(lifecycles=list(range(4)), methods=list(A.METHODS), eval_methods=list(A.EVAL_METHODS),
        queries=dict(reward={}, risk_goal={}), phases=[dict(name=name, p4=p) for name, p in phases],
        warmup_spawns=256, route_block=64, recent_window=256, source_games_per_phase=6,
        eval_checkpoints=[dict(phase=name, after_game=n) for name, _ in phases for n in checkpoints[name]], eval_replicas=2)
    run = dict(status='complete', settings=settings, lifecycles=[], runner_checks={'no_oracle_input': True}, actual_wall_seconds=1.)
    for life in settings['lifecycles']:
        values, modules, active = [], [dict(id=0, alpha=1, beta=1, visits=0)], 0
        events = []
        row = dict(life=life, phases=[], checks={'evaluation_never_updates_memory': True})
        run['lifecycles'].append(row)

        def payloads():
            n = len(values)
            payload = {}
            for method in A.METHODS:
                context = values[:256] if method == 'FROZEN' else (values[-256:] if method == 'RECENT' else values)
                summary = deepcopy(modules) if method == 'LIBRARY' else [dict(id=0,
                    alpha=1 + sum(context), beta=1 + len(context) - sum(context), visits=1)]
                counts = dict(observations_received=n, predict_calls=n,
                    beta_updates=min(n, 256) if method == 'FROZEN' else (256 + ((n - 256) // 64) * 64 if method == 'LIBRARY' and n >= 256 else n),
                    routing_blocks=max(0, (n - 256) // 64) if method == 'LIBRARY' else 0,
                    module_creations=sum(e['kind'] == 'created' for e in events) if method == 'LIBRARY' else 0,
                    module_reactivations=sum(e['kind'] == 'reactivated' for e in events) if method == 'LIBRARY' else 0,
                    candidate_predictive_scores=sum(len(e['existing_log_scores']) + 1 for e in events if e['kind'] != 'initialized') if method == 'LIBRARY' else 0)
                payload[method] = dict(method=method, observations_seen=n, active_module_id=active if method == 'LIBRARY' else 0,
                    modules=summary, counts=counts, stored_observation_counts=dict(statistics=sum(m['alpha'] + m['beta'] - 2 for m in summary), pending=0, raw=min(n, 256) if method == 'RECENT' else 0))
            return payload

        for pi, (name, truth) in enumerate(phases):
            phase = dict(name=name, p4=truth, source_games=[], predictions=[], module_events=[], checkpoints=[])
            row['phases'].append(phase)
            for episode in range(6):
                phase['source_games'].append(dict(episode=episode, source_seed=115000000 + life * 10000 + pi * 100 + episode,
                    outcome='LOST', ground_work=dict(sampled_transitions=64, initial_spawns=2, environment_random_draws=132),
                    planning_counts={'legal_swipes': 64}, steps=64, seconds=.001))
                for j in range(64):
                    n = len(values)
                    method_predictions = {}
                    for method in A.METHODS:
                        context = values[:256] if method == 'FROZEN' else (values[-256:] if method == 'RECENT' else values)
                        probability = ((modules[active]['alpha'] / (modules[active]['alpha'] + modules[active]['beta']))
                            if method == 'LIBRARY' else (1 + sum(context)) / (2 + len(context)))
                        method_predictions[method] = dict(p4=probability, module_id=active if method == 'LIBRARY' else 0)
                    y = int((episode * 64 + j) % 10 < (3 if name == 'B' else 1))
                    values.append(y)
                    phase['predictions'].append(dict(phase_observation_index=episode * 64 + j + 1,
                        observation_index=n + 1, is_four=y, methods=method_predictions))
                    if n < 256:
                        modules[0]['alpha'] += y
                        modules[0]['beta'] += 1 - y
                    if n + 1 == 256 or (n + 1 > 256 and (n + 1 - 256) % 64 == 0):
                        previous = active
                        scores = [dict(module_id=m['id'], log_score=-1.) for m in modules]
                        kind = 'initialized' if n + 1 == 256 else 'updated'
                        if n + 1 == 512:
                            active = 1
                            modules.append(dict(id=1, alpha=1, beta=1, visits=0))
                            kind = 'created'
                        elif n + 1 == 896:
                            active = 0
                            kind = 'reactivated'
                        if n + 1 > 256:
                            modules[active]['alpha'] += sum(values[-64:])
                            modules[active]['beta'] += 64 - sum(values[-64:])
                        event = dict(observation_index=n + 1, kind=kind, module_id=active,
                            previous_module_id=previous, existing_log_scores=scores)
                        events.append(event)
                        phase['module_events'].append(event)
                after = episode + 1
                if after in checkpoints[name]:
                    saved = payloads()
                    cp = dict(phase=name, after_game=after, models=saved, evaluations=[])
                    phase['checkpoints'].append(cp)
                    for mi, method in enumerate(A.EVAL_METHODS):
                        probability = truth if method == 'KNOWN_PARAMETER' else A._model_probability(saved[method])
                        for query in settings['queries']:
                            for replica in range(2):
                                score = 1000 + 20 * life + 10 * pi + after + replica + mi * 8 * (life + 1)
                                cp['evaluations'].append(dict(method=method, query=query, replica=replica,
                                    seed=115900000 + life * 100000 + pi * 10000 + after * 100 + replica,
                                    result=dict(score=score, utility=score / 2048 - (4 if query == 'risk_goal' else 0),
                                        status='LOST', steps=64, environment_counts=dict(sampled_transitions=64,
                                        initial_spawns=2, environment_random_draws=132),
                                        planning_counts=dict(model_spawn_samples=128, model_uniform_draws=256), seconds=.002, p4_used=probability)))
        row['final_models'] = payloads()
    return run


def test_metrics_use_pre_observation_probabilities_and_full_fixed_windows():
    result = A.adaptation_summary([.1] * 128 + [.3] * 128, [0, 1] * 128, .3)
    expected_loss = (-math.log(.1) - math.log(.9) - math.log(.3) - math.log(.7)) / 4
    assert math.isclose(result['first_256']['log_loss'], expected_loss)
    assert math.isclose(result['first_256']['brier'], .35)
    assert math.isclose(result['first_256']['absolute_parameter_error'], .1)
    assert result['first_tolerance_window_end'] == 176
    assert [row['observations'] for row in result['blocks']] == [64] * 4
    incomplete = A.adaptation_summary([.1] * 63, [0] * 63, .3)
    assert not incomplete['first_window_complete'] and incomplete['first_256']['log_loss'] is None
    assert incomplete['first_tolerance_window_end'] is None


def test_complete_lifecycle_pairing_and_library_reactivation():
    result = A.analyze_run(fixture())
    assert result['primary_complete'], result['checks']
    comparison = result['evaluation'][-1]['comparisons']['LIBRARY_minus_RECENT']['reward']
    assert comparison['mean_deltas']['score'] == 20
    assert comparison['mean_deltas']['utility'] == 20 / 2048
    assert [row['deltas']['score'] for row in comparison['lifecycles']] == [8, 16, 24, 32]
    assert comparison['utility_directions'] == dict(positive=4, negative=0, zero=0)
    assert sum(row['counts'].get('created', 0) for row in result['module_events']) == 4
    assert sum(row['counts'].get('reactivated', 0) for row in result['module_events']) == 4
    assert len(result['adaptation']['B']['LIBRARY']['lifecycles']) == 4


def test_shared_source_and_cumulative_work_are_charged_once():
    result = A.analyze_run(fixture())
    cost = result['actual_executed_work']
    assert cost['source_games'] == 72 and cost['evaluation_games'] == 560
    assert cost['source_sampled_transitions'] == 4608 and cost['evaluation_sampled_transitions'] == 35840
    assert cost['newly_sampled_environment_transitions'] == 40448
    assert cost['imagined_model_spawn_samples'] == 71680
    assert cost['attributed_source_transitions_per_learner'] == {method: 4608 for method in A.METHODS}
    assert cost['learning_counts']['POOLED']['observations_received'] == 4608
    assert cost['learning_counts']['FROZEN']['beta_updates'] == 1024
    assert cost['learning_counts']['LIBRARY']['module_creations'] == 4


def test_observation_leakage_and_false_reactivation_are_rejected():
    run = fixture()
    run['lifecycles'][0]['phases'][1]['predictions'][0]['methods']['POOLED']['p4'] = .3
    assert not A.analyze_run(run)['checks']['simple_control_predictions_match_observed_history']
    run = fixture()
    event = next(e for e in run['lifecycles'][0]['phases'][1]['module_events'] if e['kind'] == 'created')
    event['kind'] = 'reactivated'
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['library_event_semantics']


def test_missing_evaluation_or_cutoff_keeps_cost_and_missing_pair():
    run = fixture()
    run['lifecycles'][0]['phases'][-1]['checkpoints'][-1]['evaluations'].pop(0)
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['evaluation_roster_complete']
    assert result['evaluation'][-1]['comparisons']['LIBRARY_minus_FROZEN']['reward']['mean_deltas']['utility'] is None
    assert result['actual_executed_work']['evaluation_games'] == 559
    run = fixture()
    run['lifecycles'][0]['phases'][-1]['checkpoints'][-1]['evaluations'][0]['result']['status'] = 'CUTOFF'
    result = A.analyze_run(run)
    assert not result['primary_complete'] and not result['checks']['evaluation_games_terminal']
    assert result['actual_executed_work']['newly_sampled_environment_transitions'] == 40448
