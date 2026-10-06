"""Prequential adaptation and paired complete-game outcomes for V115."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


METHODS = ('FROZEN', 'POOLED', 'RECENT', 'LIBRARY')
EVAL_METHODS = METHODS + ('KNOWN_PARAMETER',)
PHASES = ('A', 'B', 'A_RETURN')
FIELDS = ('log_loss', 'brier', 'absolute_parameter_error')
GAME_FIELDS = ('score', 'utility', 'steps')


def mean(values):
    values = list(values)
    return math.fsum(values) / len(values) if values and all(v is not None for v in values) else None


def prediction_metrics(probabilities, outcomes, true_p4):
    """Each p is recorded before its corresponding real spawn is observed."""
    probabilities, outcomes = list(probabilities), list(outcomes)
    if not probabilities or len(probabilities) != len(outcomes):
        return {field: None for field in FIELDS}
    return dict(log_loss=mean(-math.log(p) if y else -math.log1p(-p)
                             for p, y in zip(probabilities, outcomes)),
                brier=mean((p - y) ** 2 for p, y in zip(probabilities, outcomes)),
                absolute_parameter_error=mean(abs(p - true_p4) for p in probabilities))


def adaptation_summary(probabilities, outcomes, true_p4, window=64, first=256, tolerance=.05):
    probabilities, outcomes = list(probabilities), list(outcomes)
    enough = len(probabilities) >= first
    initial = prediction_metrics(probabilities[:first], outcomes[:first], true_p4) if enough else {
        field: None for field in FIELDS}
    blocks = [dict(first_observation=start + 1, last_observation=min(start + window, len(probabilities)),
                   observations=len(probabilities[start:start + window]),
                   complete=len(probabilities[start:start + window]) == window,
                   **prediction_metrics(probabilities[start:start + window], outcomes[start:start + window], true_p4))
              for start in range(0, len(probabilities), window)]
    reached = next((end for end in range(window, len(probabilities) + 1)
                    if mean(abs(p - true_p4) for p in probabilities[end - window:end]) <= tolerance), None)
    return dict(observations=len(probabilities), first_window_complete=enough,
                first_256=initial, blocks=blocks,
                first_tolerance_window_end=reached,
                tolerance_status='reached' if reached is not None else (
                    'insufficient_observations' if len(probabilities) < window else 'not_reached'))


def _model_probability(payload):
    active = next(module for module in payload['modules'] if module['id'] == payload['active_module_id'])
    return active['alpha'] / (active['alpha'] + active['beta'])


def _game_summary(games):
    games = list(games)
    outcomes = Counter(game['result']['status'] for game in games)
    terminal = bool(games) and set(outcomes) <= {'WON', 'LOST'}
    return dict(games=len(games), terminal=terminal, outcomes=dict(outcomes),
                means={field: mean(game['result'][field] for game in games) if terminal else None
                       for field in GAME_FIELDS},
                win_fraction=outcomes['WON'] / len(games) if terminal else None,
                lost_fraction=outcomes['LOST'] / len(games) if terminal else None)


def _paired_games(left, right, replicas):
    left = {row['replica']: row for row in left}
    right = {row['replica']: row for row in right}
    complete = set(left) == set(right) == set(range(replicas)) and all(
        left[r]['seed'] == right[r]['seed']
        and left[r]['result']['status'] in ('WON', 'LOST')
        and right[r]['result']['status'] in ('WON', 'LOST') for r in range(replicas))
    fields = {field: mean(left[r]['result'][field] - right[r]['result'][field]
                         for r in range(replicas)) if complete else None for field in GAME_FIELDS}
    fields['win_fraction'] = mean(int(left[r]['result']['status'] == 'WON')
                                 - int(right[r]['result']['status'] == 'WON')
                                 for r in range(replicas)) if complete else None
    return dict(complete=complete, pairs=replicas if complete else 0, deltas=fields)


def _lifecycle_contrast(rows):
    fields = GAME_FIELDS + ('win_fraction',)
    complete = bool(rows) and all(row['complete'] for row in rows)
    return dict(complete=complete, lifecycles=rows,
                mean_deltas={field: mean(row['deltas'][field] for row in rows) if complete else None
                             for field in fields},
                utility_directions={label: sum(row['deltas']['utility'] is not None and predicate(row['deltas']['utility'])
                                               for row in rows)
                                    for label, predicate in (('positive', lambda x: x > 0),
                                                             ('negative', lambda x: x < 0), ('zero', lambda x: x == 0))})


def analyze_run(run):
    settings = run['settings']
    expected_lives = settings['lifecycles']
    methods, eval_methods = settings['methods'], settings['eval_methods']
    queries = list(settings['queries'])
    replicas = settings['eval_replicas']
    source_games_per_phase = settings['source_games_per_phase']
    phases = settings['phases']
    checkpoints = [(row['phase'], row['after_game']) for row in settings['eval_checkpoints']]
    warmup, window = settings['warmup_spawns'], settings['route_block']
    lives = {row['life']: row for row in run['lifecycles']}
    checks = dict(frozen_method_roster=tuple(methods) == METHODS and tuple(eval_methods) == EVAL_METHODS,
                  lifecycle_roster_complete=len(lives) == len(run['lifecycles']) == len(expected_lives)
                  and set(lives) == set(expected_lives),
                  phase_roster_complete=True, source_game_roster_complete=True,
                  source_games_terminal=True, chronological_prequential_observations=True,
                  simple_control_predictions_match_observed_history=True,
                  initial_warmup_complete=True, adaptation_windows_complete=True,
                  checkpoint_roster_complete=True, evaluation_roster_complete=True,
                  evaluation_games_terminal=True, evaluation_seed_pairing=True,
                  frozen_evaluation_probabilities=True, library_event_semantics=True,
                  source_spawn_costs_match=True, environment_draw_costs_match=True,
                  final_learning_work_matches_observations=True, fresh_source_and_evaluation_streams=True,
                  execution_checks=bool(run['runner_checks']) and all(run['runner_checks'].values()))
    source_work, source_planning = Counter(), Counter()
    eval_work = {method: Counter() for method in eval_methods}
    eval_planning = {method: Counter() for method in eval_methods}
    source_outcomes, eval_outcomes = Counter(), Counter()
    learning_counts = {method: Counter() for method in methods}
    learning_rows, event_rows, memory_rows = [], [], []
    checkpoints_by_life = {}
    source_seconds = eval_seconds = 0.
    for life_id in expected_lives:
        life = lives.get(life_id)
        if life is None:
            continue
        checks['execution_checks'] &= bool(life['checks']) and all(life['checks'].values())
        checks['phase_roster_complete'] &= [row['name'] for row in life['phases']] == [row['name'] for row in phases]
        all_observations, seen_modules, active_module = [], {0}, 0
        cumulative_fours, library_events = 0, []
        life_checkpoints = {}
        for phase_index, (phase, expected_phase) in enumerate(zip(life['phases'], phases)):
            name, truth = phase['name'], expected_phase['p4']
            checks['phase_roster_complete'] &= phase['p4'] == truth
            games, predictions = phase['source_games'], phase['predictions']
            checks['source_game_roster_complete'] &= len(games) == source_games_per_phase and {
                game['episode'] for game in games} == set(range(source_games_per_phase))
            checks['source_games_terminal'] &= bool(games) and all(game['outcome'] in ('WON', 'LOST') for game in games)
            phase_source_work = Counter()
            for game in games:
                checks['fresh_source_and_evaluation_streams'] &= game['source_seed'] == (
                    115000000 + life_id * 10000 + phase_index * 100 + game['episode'])
                source_work.update(game['ground_work'])
                phase_source_work.update(game['ground_work'])
                source_planning.update(game['planning_counts'])
                source_outcomes[game['outcome']] += 1
                source_seconds += game['seconds']
            checks['source_spawn_costs_match'] &= len(predictions) == phase_source_work['sampled_transitions']
            checks['environment_draw_costs_match'] &= (phase_source_work['initial_spawns'] == 2 * len(games)
                and phase_source_work['environment_random_draws'] == 2 * len(predictions) + 4 * len(games))
            for index, row in enumerate(predictions, 1):
                checks['chronological_prequential_observations'] &= (
                    row['phase_observation_index'] == index
                    and row['observation_index'] == len(all_observations) + 1
                    and row['is_four'] in (0, 1) and set(row['methods']) == set(methods)
                    and all(0 < row['methods'][method]['p4'] < 1 for method in methods))
                before = all_observations
                contexts = dict(FROZEN=before[:warmup], RECENT=before[-settings['recent_window']:])
                expected_probabilities = {method: (1 + sum(context)) / (2 + len(context)) for method, context in contexts.items()}
                expected_probabilities['POOLED'] = (1 + cumulative_fours) / (2 + len(before))
                for method, expected_p in expected_probabilities.items():
                    checks['simple_control_predictions_match_observed_history'] &= math.isclose(
                        row['methods'][method]['p4'], expected_p, rel_tol=0., abs_tol=1e-12)
                all_observations.append(row['is_four'])
                cumulative_fours += row['is_four']
            if name == 'A':
                checks['initial_warmup_complete'] &= len(predictions) >= warmup
            learning = {}
            for method in methods:
                probabilities = [row['methods'][method]['p4'] for row in predictions]
                learning[method] = adaptation_summary(probabilities, [row['is_four'] for row in predictions], truth, window)
                if name != 'A':
                    checks['adaptation_windows_complete'] &= learning[method]['first_window_complete']
            learning_rows.append(dict(life=life_id, phase=name, true_p4=truth, methods=learning))
            events = phase['module_events']
            library_events.extend(events)
            for event in events:
                kind, module_id = event['kind'], event['module_id']
                index = event['observation_index']
                valid = event['previous_module_id'] == active_module
                if kind == 'initialized':
                    valid &= index == warmup and module_id == active_module
                elif kind == 'created':
                    valid &= module_id not in seen_modules and index > warmup and (index - warmup) % window == 0
                elif kind == 'reactivated':
                    valid &= module_id in seen_modules and module_id != active_module and index > warmup and (index - warmup) % window == 0
                else:
                    valid &= kind == 'updated' and module_id == active_module and index > warmup and (index - warmup) % window == 0
                checks['library_event_semantics'] &= valid
                seen_modules.add(module_id)
                active_module = module_id
            event_rows.append(dict(life=life_id, phase=name, counts=dict(Counter(row['kind'] for row in events)), events=events))
            for checkpoint in phase['checkpoints']:
                key = (checkpoint['phase'], checkpoint['after_game'])
                checks['checkpoint_roster_complete'] &= key not in life_checkpoints and checkpoint['phase'] == name
                life_checkpoints[key] = checkpoint
                checks['frozen_evaluation_probabilities'] &= set(checkpoint['models']) == set(methods)
                evaluations = checkpoint['evaluations']
                expected = {(method, query, replica) for method in eval_methods for query in queries for replica in range(replicas)}
                keys = [(row['method'], row['query'], row['replica']) for row in evaluations]
                checks['evaluation_roster_complete'] &= len(keys) == len(expected) and set(keys) == expected
                seed_groups = {}
                for row in evaluations:
                    method, result = row['method'], row['result']
                    checks['fresh_source_and_evaluation_streams'] &= row['seed'] == (
                        115900000 + life_id * 100000 + phase_index * 10000 + checkpoint['after_game'] * 100 + row['replica'])
                    seed_groups.setdefault((row['query'], row['replica']), set()).add(row['seed'])
                    expected_p = truth if method == 'KNOWN_PARAMETER' else _model_probability(checkpoint['models'][method])
                    checks['frozen_evaluation_probabilities'] &= math.isclose(result['p4_used'], expected_p, rel_tol=0., abs_tol=1e-12)
                    checks['evaluation_games_terminal'] &= result['status'] in ('WON', 'LOST')
                    eval_work[method].update(result['environment_counts'])
                    environment = result['environment_counts']
                    checks['environment_draw_costs_match'] &= (environment['initial_spawns'] == 2
                        and environment['sampled_transitions'] == result['steps']
                        and environment['environment_random_draws'] == 2 * result['steps'] + 4)
                    eval_planning[method].update(result['planning_counts'])
                    eval_outcomes[result['status']] += 1
                    eval_seconds += result['seconds']
                checks['evaluation_seed_pairing'] &= all(len(seeds) == 1 for seeds in seed_groups.values())
        checks['checkpoint_roster_complete'] &= set(life_checkpoints) == set(checkpoints)
        checkpoints_by_life[life_id] = life_checkpoints
        n = len(all_observations)
        expected_indices = ([warmup] + list(range(warmup + window, n + 1, window))) if n >= warmup else []
        checks['library_event_semantics'] &= [event['observation_index'] for event in library_events] == expected_indices
        for method in methods:
            payload = life['final_models'][method]
            counts = payload['counts']
            expected_updates = min(n, warmup) if method == 'FROZEN' else (
                min(n, warmup) + max(0, (n - warmup) // window) * window if method == 'LIBRARY' else n)
            checks['final_learning_work_matches_observations'] &= (payload['observations_seen'] == n
                and counts['observations_received'] == counts['predict_calls'] == n
                and counts['beta_updates'] == expected_updates)
            if method == 'LIBRARY':
                checks['final_learning_work_matches_observations'] &= (
                    counts['routing_blocks'] == max(0, (n - warmup) // window)
                    and counts['module_creations'] == sum(event['kind'] == 'created' for event in library_events)
                    and counts['module_reactivations'] == sum(event['kind'] == 'reactivated' for event in library_events)
                    and counts['candidate_predictive_scores'] == sum(len(event['existing_log_scores']) + 1
                        for event in library_events if event['kind'] != 'initialized'))
            learning_counts[method].update(counts)
            memory_rows.append(dict(life=life_id, method=method, modules=len(payload['modules']),
                active_module_id=payload['active_module_id'], stored_observation_counts=payload['stored_observation_counts']))
    adaptation = {}
    for phase in [row['name'] for row in phases]:
        adaptation[phase] = {}
        for method in methods:
            rows = [dict(life=life, **next(row['methods'][method] for row in learning_rows
                if row['life'] == life and row['phase'] == phase)) for life in expected_lives
                if any(row['life'] == life and row['phase'] == phase for row in learning_rows)]
            complete = len(rows) == len(expected_lives) and all(row['first_window_complete'] for row in rows)
            adaptation[phase][method] = dict(lifecycles=rows, first_256_complete=complete,
                first_256_mean={field: mean(row['first_256'][field] for row in rows) if complete else None for field in FIELDS},
                tolerance_reached_lifecycles=sum(row['first_tolerance_window_end'] is not None for row in rows),
                first_tolerance_window_ends=[row['first_tolerance_window_end'] for row in rows])
    adaptation_comparisons = {}
    for phase in PHASES[1:]:
        adaptation_comparisons[phase] = {}
        for right in METHODS[:-1]:
            left = {row['life']: row for row in adaptation[phase]['LIBRARY']['lifecycles']}
            control = {row['life']: row for row in adaptation[phase][right]['lifecycles']}
            rows = [dict(life=life, deltas={field: (left[life]['first_256'][field] - control[life]['first_256'][field])
                if life in left and life in control and left[life]['first_window_complete'] and control[life]['first_window_complete']
                else None for field in FIELDS}) for life in expected_lives]
            adaptation_comparisons[phase][f'LIBRARY_minus_{right}'] = dict(lifecycles=rows,
                mean_deltas={field: mean(row['deltas'][field] for row in rows) for field in FIELDS})
    evaluation = []
    for phase, after_game in checkpoints:
        result = dict(phase=phase, after_game=after_game, methods={}, comparisons={})
        for query in queries:
            for method in eval_methods:
                rows = []
                for life in expected_lives:
                    checkpoint = checkpoints_by_life.get(life, {}).get((phase, after_game), {})
                    games = [row for row in checkpoint.get('evaluations', []) if row['method'] == method and row['query'] == query]
                    rows.append(dict(life=life, **_game_summary(games)))
                result['methods'].setdefault(method, {})[query] = dict(lifecycles=rows,
                    lifecycle_mean={field: mean(row['means'][field] for row in rows) for field in GAME_FIELDS},
                    win_fraction=mean(row['win_fraction'] for row in rows), lost_fraction=mean(row['lost_fraction'] for row in rows))
            for right in (method for method in eval_methods if method != 'LIBRARY'):
                rows = []
                for life in expected_lives:
                    checkpoint = checkpoints_by_life.get(life, {}).get((phase, after_game), {})
                    games = checkpoint.get('evaluations', [])
                    left_games = [row for row in games if row['method'] == 'LIBRARY' and row['query'] == query]
                    right_games = [row for row in games if row['method'] == right and row['query'] == query]
                    rows.append(dict(life=life, **_paired_games(left_games, right_games, replicas)))
                result['comparisons'].setdefault(f'LIBRARY_minus_{right}', {})[query] = _lifecycle_contrast(rows)
        evaluation.append(result)
    new_real = source_work['sampled_transitions'] + sum(counts['sampled_transitions'] for counts in eval_work.values())
    work = dict(source_games=sum(source_outcomes.values()), evaluation_games=sum(eval_outcomes.values()),
        source_environment_counts=dict(source_work), source_planning_counts=dict(source_planning),
        evaluation_environment_counts={method: dict(counts) for method, counts in eval_work.items()},
        evaluation_planning_counts={method: dict(counts) for method, counts in eval_planning.items()},
        learning_counts={method: dict(counts) for method, counts in learning_counts.items()},
        source_outcomes=dict(source_outcomes), evaluation_outcomes=dict(eval_outcomes),
        newly_sampled_environment_transitions=new_real,
        source_sampled_transitions=source_work['sampled_transitions'],
        evaluation_sampled_transitions=sum(counts['sampled_transitions'] for counts in eval_work.values()),
        imagined_model_spawn_samples=source_planning['model_spawn_samples'] + sum(counts['model_spawn_samples'] for counts in eval_planning.values()),
        attributed_source_transitions_per_learner={method: source_work['sampled_transitions'] for method in methods},
        final_memory=memory_rows,
        source_seconds=source_seconds, summed_evaluation_seconds=eval_seconds,
        actual_wall_seconds=run['actual_wall_seconds'])
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.regime_memory_analysis.v115', complete=complete, primary_complete=complete,
        checks=checks, adaptation=adaptation, adaptation_comparisons=adaptation_comparisons,
        evaluation=evaluation, module_events=event_rows,
        actual_executed_work=work,
        evidence_scope='Four independent A/B/A-return lifecycles; descriptive lifecycle means. '
        'Known-parameter H2 is a calibration reference, not an optimal-policy bound. '
        'Parameter-module adaptation does not establish structural discovery or general strategic learning.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run = json.loads(args.input.read_text())
    result = analyze_run(run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))


if __name__ == '__main__':
    main()
