"""Independent trajectory prediction and complete-game planning evidence for V116."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_controlled_predictive_regime_memory_v115 import mean, _game_summary, _paired_games, _lifecycle_contrast

MODES = ('MIXED', 'CONTEXT')
POLICIES = ('GREEDY', 'SPACE', 'SNAKE')
METHODS = ('H2_ONLY', 'MIXED_PLAN', 'CONTEXT_PLAN')
COMPONENTS = ('reward', 'failure', 'success')
PHASES = ('A', 'B', 'A_RETURN')


def mse(records, version, mode):
    """One trajectory/horizon is one averaging unit, irrespective of its length."""
    return {name: mean((record['predictions'][version][mode][index] - record['target'][index]) ** 2
                      for record in records) for index, name in enumerate(COMPONENTS)}


def _aggregate_prediction(rows, lives, policies, horizons, replicas):
    by_case, per_life = {}, []
    for policy in policies:
        by_case[policy] = {}
        for horizon in horizons:
            summaries = []
            for life in lives:
                selected = [row for row in rows if row['life'] == life and row['policy'] == policy and row['horizon'] == horizon]
                complete = len(selected) == replicas and {row['replica'] for row in selected} == set(range(replicas))
                summaries.append(dict(life=life, complete=complete, games=selected,
                    mse={field: mean(row['mse'][field] for row in selected) if complete else None for field in COMPONENTS}))
            by_case[policy][str(horizon)] = dict(lifecycles=summaries,
                mean_mse={field: mean(row['mse'][field] for row in summaries) for field in COMPONENTS})
    for life in lives:
        cases = [next(row for row in by_case[policy][str(horizon)]['lifecycles'] if row['life'] == life)
                 for policy in policies for horizon in horizons]
        per_life.append(dict(life=life, macro_mse={field: mean(row['mse'][field] for row in cases) for field in COMPONENTS}))
    return dict(by_policy_horizon=by_case, lifecycles=per_life,
        macro_mse={field: mean(row['macro_mse'][field] for row in per_life) for field in COMPONENTS})


def _prediction_delta(left, right):
    rows = []
    for first, second in zip(left['lifecycles'], right['lifecycles']):
        rows.append(dict(life=first['life'], mse_delta={field:
            first['macro_mse'][field] - second['macro_mse'][field]
            if first['macro_mse'][field] is not None and second['macro_mse'][field] is not None else None
            for field in COMPONENTS}))
    by_case = {}
    for policy, horizons in left['by_policy_horizon'].items():
        by_case[policy] = {}
        for horizon, group in horizons.items():
            first, second = group['mean_mse'], right['by_policy_horizon'][policy][horizon]['mean_mse']
            by_case[policy][horizon] = {field: first[field] - second[field]
                if first[field] is not None and second[field] is not None else None for field in COMPONENTS}
    return dict(lifecycles=rows, mean_mse_delta={field: mean(row['mse_delta'][field] for row in rows) for field in COMPONENTS},
        by_policy_horizon=by_case)


def _expected_records(game, stride, horizons):
    steps = game['steps']
    anchors = sorted(set(range(0, steps, stride)) | ({steps - 1} if steps else set()))
    return [dict(episode=game['episode'], policy=game['policy'], anchor_step=anchor, horizon=horizon)
            for anchor in anchors for horizon in horizons
            if game['status'] in ('WON', 'LOST') or anchor + horizon < steps]


def _cost_group():
    return dict(games=0, environment=Counter(), planning=Counter(), prediction=Counter(),
        outcomes=Counter(), seconds=0.)


def _add_game_cost(group, game):
    group['games'] += 1
    group['environment'].update(game['environment_counts'])
    group['planning'].update(game['planning_counts'])
    group['prediction'].update(game.get('prediction_counts', {}))
    group['outcomes'][game['status']] += 1
    group['seconds'] += game['seconds']


def analyze_run(run):
    s = run['settings']
    lives, phases = s['lifecycles'], s['phases']
    policies, modes, horizons = s['policies'], s['modes'], s['horizons']
    queries, methods = list(s['queries']), s['methods']
    p_replicas, c_replicas = s['prediction_replicas'], s['control_replicas']
    n_source = s['source_games_per_phase']
    indexed = {row['life']: row for row in run['lifecycles']}
    checks = dict(frozen_method_and_phase_rosters=tuple(modes) == MODES and tuple(policies) == POLICIES
        and tuple(methods) == METHODS and tuple(p['name'] for p in phases) == PHASES,
        lifecycle_roster_complete=len(indexed) == len(run['lifecycles']) == len(lives) and set(indexed) == set(lives),
        source_game_roster_complete=True, source_games_terminal=True,
        complete_cumulative_training_rosters=True, matched_nominal_tree_recipe=True,
        actual_fit_costs_match=True, predictive_game_roster_complete=True,
        predictive_games_terminal=True, predictive_versions_and_windows_complete=True,
        current_context_bound_to_prediction=True, predictive_inference_costs_match=True,
        control_game_roster_complete=True, control_games_terminal=True,
        fresh_seed_streams_and_pairing=True, environment_costs_match=True,
        router_receives_only_source_observations=True,
        execution_checks=bool(run['runner_checks']) and all(run['runner_checks'].values()))
    costs = {name: _cost_group() for name in ('source', 'predictive_evaluation', 'control_evaluation')}
    fit_counts, prediction_counts, label_counts, router_counts = Counter(), Counter(), Counter(), Counter()
    fit_seconds = 0.
    model_sizes, target_coverage = [], []
    case_rows = {phase['name']: {} for phase in phases}
    checkpoint_index = {}
    for life in lives:
        record = indexed.get(life)
        if record is None:
            continue
        checks['execution_checks'] &= bool(record['checks']) and all(record['checks'].values())
        checks['source_game_roster_complete'] &= [phase['name'] for phase in record['phases']] == [p['name'] for p in phases]
        training_roster, source_observations = [], 0
        for phase_index, (phase, expected_phase) in enumerate(zip(record['phases'], phases)):
            name = phase['name']
            checks['source_game_roster_complete'] &= phase['p4'] == expected_phase['p4']
            games = phase['source_games']
            expected_episodes = set(range(phase_index * n_source, (phase_index + 1) * n_source))
            checks['source_game_roster_complete'] &= len(games) == n_source and {g['episode'] for g in games} == expected_episodes
            for game in games:
                local = game['episode'] - phase_index * n_source
                checks['source_game_roster_complete'] &= game['policy'] == policies[local % len(policies)]
                checks['fresh_seed_streams_and_pairing'] &= game['seed'] == 116000000 + life * 10000 + phase_index * 100 + local
                checks['source_games_terminal'] &= game['status'] in ('WON', 'LOST')
                training_roster.extend(_expected_records(game, s['stride'], horizons))
                source_observations += game['steps']
                label_counts.update(game['label_log'])
                _add_game_cost(costs['source'], game)
            checkpoint = phase['checkpoint']
            checkpoint_index[life, name] = checkpoint
            checks['execution_checks'] &= checkpoint['phase'] == name and bool(checkpoint['checks']) and all(checkpoint['checks'].values())
            p4 = checkpoint['router_p4']
            checks['router_receives_only_source_observations'] &= checkpoint['router_payload']['observations_seen'] == source_observations
            checks['complete_cumulative_training_rosters'] &= set(checkpoint['fit_logs']) == set(checkpoint['models']) == set(modes)
            for mode in modes:
                fit, model = checkpoint['fit_logs'][mode], checkpoint['models'][mode]
                checks['complete_cumulative_training_rosters'] &= (fit['training_roster'] == training_roster
                    and fit['training_records'] == len(training_roster))
                checks['matched_nominal_tree_recipe'] &= (fit['mode'] == model['mode'] == mode
                    and fit['feature_dim'] == 38 and len(fit['feature_names']) == 38
                    and fit['feature_names'] == model['feature_names']
                    and fit['tree_parameters'] == model['tree_parameters'] == dict(max_depth=8, min_samples_leaf=16, random_state=7701)
                    and set(fit['policies']) == set(model['trees']) == set(policies))
                checks['current_context_bound_to_prediction'] &= fit['context_p4'] == model['context_p4'] == p4
                count = fit['counts']
                context_key = 'context_feature_rows' if mode == 'CONTEXT' else 'constant_context_feature_rows'
                checks['actual_fit_costs_match'] &= (count['tree_fits'] == len(policies)
                    and all(count[key] == len(training_roster) for key in ('training_rows_read', 'feature_rows', 'fit_rows', context_key)))
                fit_counts.update(count)
                fit_seconds += fit['seconds']
                model_sizes.append(dict(life=life, phase=name, mode=mode,
                    policies={policy: {key: fit['policies'][policy][key] for key in ('training_rows', 'nodes', 'leaves')}
                              for policy in policies}))
            versions = ('CURRENT', 'A_END', 'B_END') if name == 'A_RETURN' else ('CURRENT',)
            tests = checkpoint['predictive_tests']
            expected = {(policy, replica) for policy in policies for replica in range(p_replicas)}
            checks['predictive_game_roster_complete'] &= len(tests) == len(expected) and {(g['policy'], g['replica']) for g in tests} == expected
            total_prediction_rows = 0
            for game in tests:
                policy_index = policies.index(game['policy'])
                checks['fresh_seed_streams_and_pairing'] &= game['seed'] == 116800000 + life * 100000 + phase_index * 10000 + policy_index * 100 + game['replica']
                checks['predictive_games_terminal'] &= game['status'] in ('WON', 'LOST')
                _add_game_cost(costs['predictive_evaluation'], game)
                rows = game['records']
                total_prediction_rows += len(rows)
                expected_windows = _expected_records(dict(episode=0, policy=game['policy'], steps=game['steps'], status=game['status']), s['stride'], horizons)
                checks['predictive_versions_and_windows_complete'] &= len(rows) == len(expected_windows) and [
                    (row['anchor_step'], row['horizon']) for row in rows] == [(row['anchor_step'], row['horizon']) for row in expected_windows]
                for row in rows:
                    checks['predictive_versions_and_windows_complete'] &= (row['policy'] == game['policy']
                        and len(row['target']) == 3 and set(row['predictions']) == set(versions)
                        and all(set(row['predictions'][version]) == set(modes)
                            and all(len(row['predictions'][version][mode]) == 3 for mode in modes) for version in versions if version in row['predictions']))
                target_coverage.append(dict(life=life, phase=name, policy=game['policy'], replica=game['replica'],
                    records=len(rows), target_mean={field: mean(row['target'][i] for row in rows) for i, field in enumerate(COMPONENTS)},
                    terminal_failure_labels=sum(row['target'][1] for row in rows), terminal_success_labels=sum(row['target'][2] for row in rows)))
                for version in versions:
                    for mode in modes:
                        key = (version, mode)
                        entries = case_rows[name].setdefault(key, [])
                        for horizon in horizons:
                            group = [row for row in rows if row['horizon'] == horizon]
                            complete = (game['status'] in ('WON', 'LOST') and bool(group)
                                and all(version in row['predictions'] and mode in row['predictions'][version] for row in group))
                            entries.append(dict(life=life, policy=game['policy'], replica=game['replica'], horizon=horizon,
                                seed=game['seed'], records=len(group), mse=mse(group, version, mode) if complete else {field: None for field in COMPONENTS}))
            checks['predictive_inference_costs_match'] &= set(checkpoint['prediction_counts']) == set(versions)
            for version, mode_counts in checkpoint['prediction_counts'].items():
                checks['predictive_inference_costs_match'] &= set(mode_counts) == set(modes)
                for mode, count in mode_counts.items():
                    checks['predictive_inference_costs_match'] &= count['record_prediction_rows'] == count['policy_prediction_rows'] == total_prediction_rows
                    prediction_counts.update(count)
            controls = checkpoint['control_evaluations']
            expected = {(method, query, replica) for method in methods for query in queries for replica in range(c_replicas)}
            checks['control_game_roster_complete'] &= len(controls) == len(expected) and {
                (g['method'], g['query'], g['replica']) for g in controls} == expected
            for game in controls:
                checks['fresh_seed_streams_and_pairing'] &= game['seed'] == 117900000 + life * 100000 + phase_index * 10000 + game['replica']
                checks['control_games_terminal'] &= game['result']['status'] in ('WON', 'LOST')
                _add_game_cost(costs['control_evaluation'], game['result'])
        final = record['final_router']
        checks['router_receives_only_source_observations'] &= final['observations_seen'] == final['counts']['observations_received'] == source_observations
        router_counts.update(final['counts'])
    predictive = {}
    for phase in PHASES:
        versions = ('CURRENT', 'A_END', 'B_END') if phase == 'A_RETURN' else ('CURRENT',)
        summaries, comparisons = {}, {}
        for version in versions:
            summaries[version] = {mode: _aggregate_prediction(case_rows[phase].get((version, mode), []),
                lives, policies, horizons, p_replicas) for mode in modes}
            comparisons[f'{version}_CONTEXT_minus_MIXED'] = _prediction_delta(summaries[version]['CONTEXT'], summaries[version]['MIXED'])
        if phase == 'A_RETURN':
            for mode in modes:
                comparisons[f'{mode}_B_END_minus_A_END'] = _prediction_delta(summaries['B_END'][mode], summaries['A_END'][mode])
                comparisons[f'{mode}_CURRENT_minus_B_END'] = _prediction_delta(summaries['CURRENT'][mode], summaries['B_END'][mode])
        predictive[phase] = dict(summaries=summaries, comparisons=comparisons)
    control = {}
    for phase in PHASES:
        method_summaries, comparisons = {}, {}
        for method in methods:
            method_summaries[method] = {}
            for query in queries:
                rows = []
                for life in lives:
                    games = [g for g in checkpoint_index.get((life, phase), {}).get('control_evaluations', []) if g['method'] == method and g['query'] == query]
                    summary = _game_summary(games)
                    if len(games) != c_replicas:
                        summary['means'] = {field: None for field in summary['means']}
                        summary['win_fraction'] = summary['lost_fraction'] = None
                    rows.append(dict(life=life, **summary))
                method_summaries[method][query] = dict(lifecycles=rows,
                    lifecycle_mean={field: mean(row['means'][field] for row in rows) for field in ('score', 'utility', 'steps')},
                    win_fraction=mean(row['win_fraction'] for row in rows), lost_fraction=mean(row['lost_fraction'] for row in rows))
        for left, right in (('CONTEXT_PLAN', 'MIXED_PLAN'), ('CONTEXT_PLAN', 'H2_ONLY'), ('MIXED_PLAN', 'H2_ONLY')):
            comparisons[f'{left}_minus_{right}'] = {}
            for query in queries:
                rows = []
                for life in lives:
                    games = checkpoint_index.get((life, phase), {}).get('control_evaluations', [])
                    rows.append(dict(life=life, **_paired_games(
                        [g for g in games if g['method'] == left and g['query'] == query],
                        [g for g in games if g['method'] == right and g['query'] == query], c_replicas)))
                comparisons[f'{left}_minus_{right}'][query] = _lifecycle_contrast(rows)
        control[phase] = dict(methods=method_summaries, comparisons=comparisons)
    for group in costs.values():
        checks['environment_costs_match'] &= (group['environment']['initial_spawns'] == 2 * group['games']
            and group['environment']['environment_random_draws'] == 2 * group['environment']['sampled_transitions'] + 4 * group['games'])
    work = dict(groups=costs, fit_counts=dict(fit_counts), fit_seconds=fit_seconds,
        predictive_inference_counts=dict(prediction_counts), source_label_counts=dict(label_counts),
        router_counts=dict(router_counts), model_sizes=model_sizes,
        newly_sampled_environment_transitions=sum(group['environment']['sampled_transitions'] for group in costs.values()),
        imagined_model_spawn_samples=sum(group['planning']['model_spawn_samples'] for group in costs.values()),
        attributed_source_transitions_per_mode={mode: costs['source']['environment']['sampled_transitions'] for mode in modes},
        actual_wall_seconds=run['actual_wall_seconds'])
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.context_consequences_analysis.v116', complete=complete, primary_complete=complete,
        checks=checks, predictive=predictive, control=control, target_coverage=target_coverage,
        actual_executed_work=work,
        evidence_scope='Paired games are averaged within policy/horizon and lifecycle before equal lifecycle means. '
        'Negative MSE deltas favor the first model. Thirty/thirty-one-step labels are policy-conditioned consequences; '
        'whole-game utility tests their use by a replanning controller. Context is conditioning, not isolation of old modules. '
        'Tree constraints match nominal capacity, not effective capacity. No general strategic-learning or scientific Gate claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze_run(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))


if __name__ == '__main__':
    main()
