"""Audit fixed consolidation choices, coverage, retention and whole-game use."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_controlled_predictive_context_consequences_v116 import (
    COMPONENTS, PHASES, POLICIES, _aggregate_prediction, _prediction_delta,
    _expected_records, _cost_group, _add_game_cost)
from scripts.analyze_controlled_predictive_regime_memory_v115 import (
    mean, _game_summary, _paired_games, _lifecycle_contrast)

MODES = ('SHARED', 'SPLIT')
TRACKS = MODES + ('SELECTED',)
METHODS = ('H2_ONLY', 'SHARED_PLAN', 'SPLIT_PLAN', 'SELECTED_PLAN')
ROSTER_KEYS = ('episode', 'policy', 'anchor_step', 'horizon')


def validation_losses(records, predictions):
    """Independent record -> horizon -> game -> policy -> batch calculation."""
    def average(values):
        values = list(values)
        return sum(values) / len(values)
    groups = {}
    for index, row in enumerate(records):
        groups.setdefault(row['batch'], {}).setdefault(row['policy'], {}).setdefault(
            row['episode'], {}).setdefault(row['horizon'], []).append(index)
    result = {}
    for batch, policies in sorted(groups.items()):
        policy_errors = []
        for policy, games in sorted(policies.items()):
            game_errors = []
            for episode, horizons in sorted(games.items()):
                horizon_errors = []
                for horizon, indices in sorted(horizons.items()):
                    values = [predictions[i] for i in indices]
                    horizon_errors.append([average((predictions[i][c] - records[i]['target'][c]) ** 2 for i in indices)
                        for c in range(3)] if all(value is not None for value in values) else None)
                game_errors.append([average(error[c] for error in horizon_errors) for c in range(3)]
                    if all(error is not None for error in horizon_errors) else None)
            policy_errors.append([average(error[c] for error in game_errors) for c in range(3)]
                if all(error is not None for error in game_errors) else None)
        covered = all(error is not None for error in policy_errors)
        components = [average(error[c] for error in policy_errors) for c in range(3)] if covered else None
        result[str(batch)] = dict(covered=covered, components=dict(zip(COMPONENTS, components)) if covered else {
            key: None for key in COMPONENTS}, joint_loss=average(components) if covered else None)
    return result


def recompute_selection(records, predictions, bootstrap=False):
    losses = {name: validation_losses(records, values) for name, values in predictions.items()}
    if bootstrap:
        return dict(selected_candidate='NEW_SHARED', losses=losses, eligible={})
    eligible = {}
    for name in ('NEW_SHARED', 'NEW_SPLIT'):
        candidate, incumbent = losses[name], losses['KEEP']
        covered = all(row['covered'] for row in candidate.values())
        harmed = any(incumbent[batch]['covered'] and row['covered'] and row['joint_loss'] > incumbent[batch]['joint_loss']
                     for batch, row in candidate.items())
        improved = any(row['covered'] and (not incumbent[batch]['covered'] or row['joint_loss'] < incumbent[batch]['joint_loss'])
                       for batch, row in candidate.items())
        eligible[name] = covered and not harmed and improved
    choices = [name for name in ('NEW_SHARED', 'NEW_SPLIT') if eligible[name]]
    chosen = min(choices, key=lambda name: sum(row['joint_loss'] for row in losses[name].values()) / len(losses[name])) if choices else 'KEEP'
    return dict(selected_candidate=chosen, losses=losses, eligible=eligible)


def _project(rows):
    return [{key: row[key] for key in ROSTER_KEYS} for row in rows]


def _covered(model, policy, module_id):
    return ('shared' if model['mode'] == 'SHARED' else str(module_id)) in model['trees'][policy]


def _counts_match(counts, predictions):
    available = sum(row is not None for row in predictions)
    return (counts.get('prediction_record_requests', 0) == len(predictions)
        and counts.get('predicted_record_rows', 0) == available
        and counts.get('unavailable_record_rows', 0) == len(predictions) - available)


def _control_summary(checkpoints, lives, methods, queries, replicas, phase):
    summaries, comparisons = {}, {}
    for method in methods:
        summaries[method] = {}
        for query in queries:
            rows = []
            for life in lives:
                games = [g for g in checkpoints.get((life, phase), {}).get('control_evaluations', [])
                         if g['method'] == method and g['query'] == query]
                result = _game_summary(games)
                if len(games) != replicas:
                    result['means'] = {key: None for key in result['means']}
                    result['win_fraction'] = result['lost_fraction'] = None
                rows.append(dict(life=life, fallback_games=sum(g['result']['fallback_h2'] for g in games), **result))
            summaries[method][query] = dict(lifecycles=rows,
                lifecycle_mean={key: mean(row['means'][key] for row in rows) for key in ('score', 'utility', 'steps')},
                win_fraction=mean(row['win_fraction'] for row in rows), lost_fraction=mean(row['lost_fraction'] for row in rows))
    pairs = (('SPLIT_PLAN', 'SHARED_PLAN'), ('SELECTED_PLAN', 'SHARED_PLAN'), ('SELECTED_PLAN', 'SPLIT_PLAN'),
             ('SELECTED_PLAN', 'H2_ONLY'), ('SHARED_PLAN', 'H2_ONLY'), ('SPLIT_PLAN', 'H2_ONLY'))
    for left, right in pairs:
        comparisons[f'{left}_minus_{right}'] = {}
        for query in queries:
            rows = []
            for life in lives:
                games = checkpoints.get((life, phase), {}).get('control_evaluations', [])
                rows.append(dict(life=life, **_paired_games(
                    [g for g in games if g['method'] == left and g['query'] == query],
                    [g for g in games if g['method'] == right and g['query'] == query], replicas)))
            comparisons[f'{left}_minus_{right}'][query] = _lifecycle_contrast(rows)
    return dict(methods=summaries, comparisons=comparisons)


def analyze_run(run):
    s = run['settings']
    lives, phases, policies = s['lifecycles'], s['phases'], s['policies']
    modes, tracks, methods, horizons = s['modes'], s['tracks'], s['methods'], s['horizons']
    n_source, n_fit = s['source_games_per_phase'], s['fit_games_per_phase']
    p_replicas, c_replicas = s['prediction_replicas'], s['control_replicas']
    indexed = {row['life']: row for row in run['lifecycles']}
    checks = dict(frozen_rosters=tuple(modes) == MODES and tuple(tracks) == TRACKS and tuple(methods) == METHODS
        and tuple(policies) == POLICIES and tuple(p['name'] for p in phases) == PHASES,
        lifecycle_roster_complete=len(indexed) == len(run['lifecycles']) == len(lives) and set(indexed) == set(lives),
        source_and_role_rosters=True, source_terminal=True, fitting_excludes_reserved_validation=True,
        nominal_capacity_budget=True, executed_fit_counts_match=True, cumulative_validation_roster=True,
        source_selection_recomputed=True, selected_model_origin_bound=True, source_validation_counts_match=True,
        prediction_roster_and_versions=True, prediction_terminal=True, predictive_coverage_bound_to_models=True,
        predictive_counts_match=True, control_roster=True, control_terminal=True, explicit_h2_fallback=True,
        fresh_paired_streams=True, physical_environment_counts=True, router_source_only=True,
        execution_checks=bool(run['runner_checks']) and all(run['runner_checks'].values()))
    costs = {name: _cost_group() for name in ('source', 'predictive_evaluation', 'control_evaluation')}
    role_costs = {name: _cost_group() for name in ('FIT', 'VALIDATION')}
    fit_counts, validation_counts, outer_counts, router_counts = Counter(), Counter(), Counter(), Counter()
    choices, sizes, coverage, target_coverage = [], [], [], []
    case_rows = {phase['name']: {} for phase in phases}
    checkpoints = {}
    fit_seconds = 0.
    for life in lives:
        history = indexed.get(life)
        if history is None:
            continue
        checks['execution_checks'] &= bool(history['checks']) and all(history['checks'].values())
        checks['source_and_role_rosters'] &= [p['name'] for p in history['phases']] == [p['name'] for p in phases]
        fit_roster, validation_roster, archives = [], [], {}
        selected, origin, observed = None, None, 0
        for batch, (phase, expected_phase) in enumerate(zip(history['phases'], phases)):
            name, games = phase['name'], phase['source_games']
            checks['source_and_role_rosters'] &= phase['p4'] == expected_phase['p4'] and len(games) == n_source
            checks['source_and_role_rosters'] &= {g['episode'] for g in games} == set(range(batch * n_source, (batch + 1) * n_source))
            for game in games:
                local = game['episode'] - batch * n_source
                role = 'FIT' if local < n_fit else 'VALIDATION'
                checks['source_and_role_rosters'] &= game['role'] == role and game['policy'] == policies[local % len(policies)]
                checks['fresh_paired_streams'] &= game['seed'] == 121000000 + life * 10000 + batch * 100 + local
                checks['source_terminal'] &= game['status'] in ('WON', 'LOST')
                target = fit_roster if role == 'FIT' else validation_roster
                target.extend(_expected_records(game, s['stride'], horizons))
                observed += game['steps']
                _add_game_cost(costs['source'], game)
                _add_game_cost(role_costs[role], game)
            cp = phase['checkpoint']
            checkpoints[life, name] = cp
            module_id = cp['router_module_id']
            checks['execution_checks'] &= cp['phase'] == name and bool(cp['checks']) and all(cp['checks'].values())
            checks['router_source_only'] &= cp['router_payload']['observations_seen'] == observed
            checks['fitting_excludes_reserved_validation'] &= set(cp['fit_logs']) == set(modes) and set(cp['models']) == set(tracks)
            previous_roster = None
            for mode in modes:
                log, model = cp['fit_logs'][mode], cp['models'][mode]
                checks['fitting_excludes_reserved_validation'] &= (_project(log['training_roster']) == fit_roster
                    and log['training_records'] == len(fit_roster) and (previous_roster is None or log['training_roster'] == previous_roster))
                previous_roster = log['training_roster']
                checks['nominal_capacity_budget'] &= (log['mode'] == model['mode'] == mode and log['feature_dim'] == 37
                    and len(log['feature_names']) == 37 and log['feature_names'] == model['feature_names']
                    and log['tree_parameters'] == model['tree_parameters'] == dict(max_depth=8, min_samples_leaf=16, random_state=7701)
                    and log['per_policy_leaf_budget'] == model['per_policy_leaf_budget'] == s['leaf_budget_per_policy'] == 256
                    and log['per_policy_node_budget'] == model['per_policy_node_budget'] == 511)
                groups = [g for policy in policies for g in log['group_allocations'][policy]]
                for policy in policies:
                    allocation, total = log['group_allocations'][policy], log['policy_totals'][policy]
                    checks['nominal_capacity_budget'] &= (sum(g['leaf_allowance'] for g in allocation) == total['allocated_leaves'] == 256
                        and sum(g['actual_leaves'] for g in allocation) == total['actual_leaves'] <= 256
                        and sum(g['actual_nodes'] for g in allocation) == total['actual_nodes'] <= 511
                        and all(g['actual_leaves'] <= g['leaf_allowance'] for g in allocation))
                count = log['counts']
                checks['executed_fit_counts_match'] &= (count['fit_rows'] == count['training_rows_read'] == len(fit_roster)
                    and count['tree_fits'] == sum(not g['constant_leaf'] for g in groups)
                    and count['constant_leaf_models'] == sum(g['constant_leaf'] for g in groups))
                fit_counts.update(count)
                fit_seconds += log['seconds']
                sizes.append(dict(life=life, phase=name, mode=mode, groups=log['group_allocations'], policies=log['policy_totals']))
            validation = cp['validation']
            records, predictions = validation['records'], validation['predictions']
            names = ('NEW_SHARED', 'NEW_SPLIT') if batch == 0 else ('NEW_SHARED', 'NEW_SPLIT', 'KEEP')
            checks['cumulative_validation_roster'] &= (_project(records) == validation_roster
                and all(row['batch'] == row['episode'] // n_source for row in records)
                and set(predictions) == set(names) and all(len(values) == len(records) for values in predictions.values()))
            recomputed = recompute_selection(records, predictions, batch == 0)
            chosen = recomputed['selected_candidate']
            checks['source_selection_recomputed'] &= cp['selection']['selected_candidate'] == chosen
            if batch:
                for candidate, eligible in recomputed['eligible'].items():
                    checks['source_selection_recomputed'] &= cp['selection']['acceptance'][candidate]['eligible'] == eligible
                for candidate, batches in recomputed['losses'].items():
                    for label, values in batches.items():
                        saved = cp['selection']['scores'][candidate]['batches'][label]
                        checks['source_selection_recomputed'] &= all(saved[key] == values[key] for key in ('covered', 'joint_loss', 'components'))
            if chosen != 'KEEP':
                mode = chosen.removeprefix('NEW_')
                selected, origin = cp['models'][mode], dict(batch=batch, mode=mode)
            current = cp['models']['SELECTED']
            checks['selected_model_origin_bound'] &= (cp['selected_origin'] == origin and current['mode'] == selected['mode']
                and current['trees'] == selected['trees'] and current['feature_names'] == selected['feature_names'])
            choices.append(dict(life=life, phase=name, selected_candidate=chosen, selected_origin=origin,
                recomputed=recomputed))
            checks['source_validation_counts_match'] &= set(validation['prediction_counts']) == set(names)
            for candidate, count in validation['prediction_counts'].items():
                checks['source_validation_counts_match'] &= _counts_match(count, predictions[candidate])
                validation_counts.update(count)
            versions = dict(CURRENT=cp['models'])
            if name == 'A_RETURN':
                versions.update(archives)
            tests = cp['predictive_tests']
            expected_tests = {(policy, replica) for policy in policies for replica in range(p_replicas)}
            checks['prediction_roster_and_versions'] &= len(tests) == len(expected_tests) and {(g['policy'], g['replica']) for g in tests} == expected_tests
            all_predictions = {(version, track): [] for version in versions for track in tracks}
            for game in tests:
                checks['fresh_paired_streams'] &= game['seed'] == 119000000 + life * 100000 + batch * 10000 + policies.index(game['policy']) * 100 + game['replica']
                checks['prediction_terminal'] &= game['status'] in ('WON', 'LOST')
                _add_game_cost(costs['predictive_evaluation'], game)
                rows = game['records']
                expected_rows = _expected_records(dict(episode=0, policy=game['policy'], steps=game['steps'], status=game['status']), s['stride'], horizons)
                checks['prediction_roster_and_versions'] &= [(r['anchor_step'], r['horizon']) for r in rows] == [(r['anchor_step'], r['horizon']) for r in expected_rows]
                for row in rows:
                    checks['prediction_roster_and_versions'] &= (row['policy'] == game['policy'] and row['context_module_id'] == module_id
                        and set(row['predictions']) == set(versions) and all(set(group) == set(tracks) for group in row['predictions'].values()))
                target_coverage.append(dict(life=life, phase=name, policy=game['policy'], replica=game['replica'], records=len(rows),
                    failure_labels=sum(r['target'][1] for r in rows), success_labels=sum(r['target'][2] for r in rows)))
                for version, models in versions.items():
                    for track in tracks:
                        values = [row['predictions'].get(version, {}).get(track) for row in rows]
                        all_predictions[version, track].extend(values)
                        supported = _covered(models[track], game['policy'], module_id)
                        checks['predictive_coverage_bound_to_models'] &= all((value is not None) == supported for value in values)
                        for horizon in horizons:
                            positions = [i for i, row in enumerate(rows) if row['horizon'] == horizon]
                            available = sum(values[i] is not None for i in positions)
                            complete = bool(positions) and available == len(positions) and game['status'] in ('WON', 'LOST')
                            errors = {field: mean((values[i][c] - rows[i]['target'][c]) ** 2 for i in positions)
                                if complete else None for c, field in enumerate(COMPONENTS)}
                            case = dict(life=life, policy=game['policy'], replica=game['replica'], horizon=horizon,
                                seed=game['seed'], records=len(positions), mse=errors)
                            case_rows[name].setdefault((version, track), []).append(case)
                            coverage.append(dict(life=life, phase=name, version=version, track=track,
                                policy=game['policy'], replica=game['replica'], horizon=horizon,
                                requested=len(positions), available=available, complete=complete))
            checks['predictive_counts_match'] &= set(cp['prediction_counts']) == set(versions)
            for version, groups in cp['prediction_counts'].items():
                checks['predictive_counts_match'] &= set(groups) == set(tracks)
                for track, count in groups.items():
                    checks['predictive_counts_match'] &= _counts_match(count, all_predictions[version, track])
                    outer_counts.update(count)
            controls = cp['control_evaluations']
            expected_controls = {(method, query, replica) for method in methods for query in s['queries'] for replica in range(c_replicas)}
            checks['control_roster'] &= len(controls) == len(expected_controls) and {(g['method'], g['query'], g['replica']) for g in controls} == expected_controls
            for game in controls:
                checks['fresh_paired_streams'] &= game['seed'] == 120000000 + life * 100000 + batch * 10000 + game['replica']
                value = game['result']
                checks['control_terminal'] &= value['status'] in ('WON', 'LOST')
                method = game['method']
                fallback = method != 'H2_ONLY' and not all(_covered(cp['models'][method.removesuffix('_PLAN')], policy, module_id) for policy in policies)
                checks['explicit_h2_fallback'] &= value['fallback_h2'] == fallback and value['routed_module_id'] == module_id
                _add_game_cost(costs['control_evaluation'], value)
            if name in ('A', 'B'):
                archives[name + '_END'] = cp['models']
        checks['router_source_only'] &= history['final_router']['observations_seen'] == observed
        router_counts.update(history['final_router']['counts'])
    predictive = {}
    for phase in PHASES:
        versions = ('CURRENT', 'A_END', 'B_END') if phase == 'A_RETURN' else ('CURRENT',)
        summaries, comparisons = {}, {}
        for version in versions:
            summaries[version] = {track: _aggregate_prediction(case_rows[phase].get((version, track), []), lives, policies, horizons, p_replicas) for track in tracks}
            for left, right in (('SPLIT', 'SHARED'), ('SELECTED', 'SHARED'), ('SELECTED', 'SPLIT')):
                comparisons[f'{version}_{left}_minus_{right}'] = _prediction_delta(summaries[version][left], summaries[version][right])
        if phase == 'A_RETURN':
            for track in tracks:
                for left, right in (('B_END', 'A_END'), ('CURRENT', 'B_END')):
                    comparisons[f'{track}_{left}_minus_{right}'] = _prediction_delta(summaries[left][track], summaries[right][track])
        predictive[phase] = dict(summaries=summaries, comparisons=comparisons)
    for group in costs.values():
        checks['physical_environment_counts'] &= group['environment']['initial_spawns'] == 2 * group['games'] and group['environment']['environment_random_draws'] == 2 * group['environment']['sampled_transitions'] + 4 * group['games']
    work = dict(groups=costs, source_roles=role_costs, fit_counts=dict(fit_counts), fit_seconds=fit_seconds,
        validation_prediction_counts=dict(validation_counts), outer_prediction_counts=dict(outer_counts), router_counts=dict(router_counts),
        model_sizes=sizes, newly_sampled_environment_transitions=sum(g['environment']['sampled_transitions'] for g in costs.values()),
        imagined_model_spawn_samples=sum(g['planning']['model_spawn_samples'] for g in costs.values()),
        attributed_source_transitions_per_track={track: costs['source']['environment']['sampled_transitions'] for track in tracks},
        actual_wall_seconds=run['actual_wall_seconds'])
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.consolidation_analysis.v117', complete=complete, primary_complete=complete, checks=checks,
        predictive=predictive, prediction_coverage=coverage, target_coverage=target_coverage, selections=choices,
        selection_counts=dict(Counter(row['selected_candidate'] for row in choices)),
        control={phase: _control_summary(checkpoints, lives, methods, list(s['queries']), c_replicas, phase) for phase in PHASES},
        actual_executed_work=work,
        evidence_scope='Finite consolidation candidates use reserved source labels; source validation is learning cost. '
        'An unavailable split prediction is retained as missing coverage, never zero error; control explicitly falls back to H2. '
        'Equal leaf caps are nominal capacity bounds, not matched effective capacity or computation. '
        'Prediction means weight games, policies/horizons and independent lifecycles equally. No general-learning Gate claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze_run(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))
