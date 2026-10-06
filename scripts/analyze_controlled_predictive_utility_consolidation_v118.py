"""Frozen-source utility selection with fresh validation and outer evaluation."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_controlled_predictive_consolidation_v117 import _covered, _counts_match
from scripts.analyze_controlled_predictive_context_consequences_v116 import (
    COMPONENTS, PHASES, POLICIES, _aggregate_prediction, _prediction_delta, _expected_records, _cost_group, _add_game_cost)
from scripts.analyze_controlled_predictive_regime_memory_v115 import mean, _game_summary, _paired_games, _lifecycle_contrast

TRACKS = ('SHARED', 'SPLIT', 'MSE_SELECTED', 'UTILITY_SELECTED')
METHODS = ('H2_ONLY',) + tuple(track + '_PLAN' for track in TRACKS)
CANDIDATES = ('KEEP', 'NEW_SHARED', 'NEW_SPLIT')
BASE = 118 * 100_000_000


def recompute_utility(rows, queries, replicas):
    expected = {(name, query, replica) for name in CANDIDATES for query in queries for replica in range(replicas)}
    indexed = {(row['candidate'], row['query'], row['replica']): row for row in rows}
    complete = len(rows) == len(indexed) == len(expected) and set(indexed) == expected
    complete &= all(row['result']['status'] in ('WON', 'LOST') and math.isfinite(row['result']['utility']) for row in rows)
    complete &= all(len({row['seed'] for row in rows if row['replica'] == replica}) == 1 for replica in range(replicas))
    summaries = {}
    for name in CANDIDATES:
        by_query = {}
        for query in queries:
            games = [indexed.get((name, query, replica)) for replica in range(replicas)]
            values = [game['result']['utility'] if game is not None and game['result']['status'] in ('WON', 'LOST')
                      and math.isfinite(game['result']['utility']) else None for game in games]
            by_query[query] = dict(per_replica=values, mean_utility=sum(values) / replicas if complete else None)
        summaries[name] = dict(queries=by_query, mean_utility=sum(row['mean_utility'] for row in by_query.values()) / len(queries) if complete else None)
    acceptance = {}
    for candidate in CANDIDATES[1:]:
        deltas = {query: summaries[candidate]['queries'][query]['mean_utility'] - summaries['KEEP']['queries'][query]['mean_utility']
                  for query in queries} if complete else {}
        improved = [query for query, delta in deltas.items() if delta > 0]
        harmed = [query for query, delta in deltas.items() if delta < 0]
        acceptance[candidate] = dict(eligible=complete and not harmed and bool(improved), improved_queries=improved,
            harmed_queries=harmed, equal_queries=[query for query, delta in deltas.items() if delta == 0])
    eligible = [candidate for candidate in CANDIDATES[1:] if acceptance[candidate]['eligible']]
    selected = max(eligible, key=lambda candidate: summaries[candidate]['mean_utility']) if eligible else 'KEEP'
    return dict(selected_candidate=selected, selection_complete=complete, summaries=summaries, acceptance=acceptance)


def inherited_source_work(capsule):
    source, roles = _cost_group(), {role: _cost_group() for role in ('FIT', 'VALIDATION')}
    fitting, validation, router, labels = Counter(), Counter(), Counter(), Counter()
    for life in capsule['lifecycles']:
        for phase in life['phases']:
            for game in phase['source_games']:
                _add_game_cost(source, game)
                _add_game_cost(roles[game['role']], game)
                labels.update(game['label_log'])
            cp = phase['checkpoint']
            for log in cp['fit_logs'].values():
                fitting.update(log['counts'])
            for count in cp['source_validation_prediction_counts'].values():
                validation.update(count)
        router.update(life['final_router']['counts'])
    return dict(source=source, source_roles=roles, fit_counts=dict(fitting), source_validation_prediction_counts=dict(validation),
        router_counts=dict(router), source_label_counts=dict(labels),
        physical_source_transitions=source['environment']['sampled_transitions'],
        attributed_source_transitions_per_track={track: source['environment']['sampled_transitions'] for track in TRACKS})


def _control_summary(indexed, phase, lives, queries, replicas):
    methods = METHODS + (('UTILITY_B_END_PLAN',) if phase == 'A_RETURN' else ())
    summaries, comparisons = {}, {}
    for method in methods:
        summaries[method] = {}
        for query in queries:
            rows = []
            for life in lives:
                games = [game for game in indexed.get((life, phase), {}).get('control_evaluations', [])
                         if game['method'] == method and game['query'] == query]
                result = _game_summary(games)
                if len(games) != replicas:
                    result['means'] = {key: None for key in result['means']}
                    result['win_fraction'] = result['lost_fraction'] = None
                rows.append(dict(life=life, fallback_games=sum(game['result']['fallback_h2'] for game in games), **result))
            summaries[method][query] = dict(lifecycles=rows,
                lifecycle_mean={key: mean(row['means'][key] for row in rows) for key in ('score', 'utility', 'steps')},
                win_fraction=mean(row['win_fraction'] for row in rows), lost_fraction=mean(row['lost_fraction'] for row in rows))
    for right in ('MSE_SELECTED_PLAN', 'SHARED_PLAN', 'SPLIT_PLAN', 'H2_ONLY') + (('UTILITY_B_END_PLAN',) if phase == 'A_RETURN' else ()):
        comparisons[f'UTILITY_SELECTED_PLAN_minus_{right}'] = {}
        for query in queries:
            rows = []
            for life in lives:
                games = indexed.get((life, phase), {}).get('control_evaluations', [])
                rows.append(dict(life=life, **_paired_games(
                    [g for g in games if g['method'] == 'UTILITY_SELECTED_PLAN' and g['query'] == query],
                    [g for g in games if g['method'] == right and g['query'] == query], replicas)))
            comparisons[f'UTILITY_SELECTED_PLAN_minus_{right}'][query] = _lifecycle_contrast(rows)
    return dict(methods=summaries, comparisons=comparisons)


def analyze_run(run, capsule):
    s = run['settings']
    lives, policies, queries, horizons = s['lifecycles'], s['policies'], list(s['queries']), s['horizons']
    v_replicas, p_replicas, c_replicas = s['source_validation_replicas'], s['prediction_replicas'], s['control_replicas']
    inherited = {(life['life'], phase['name']): phase['checkpoint'] for life in capsule['lifecycles'] for phase in life['phases']}
    indexed = {row['life']: row for row in run['lifecycles']}
    checks = dict(frozen_rosters=tuple(s['tracks']) == TRACKS and tuple(s['methods']) == METHODS and tuple(policies) == POLICIES
        and tuple(p['name'] for p in s['phases']) == PHASES,
        lifecycle_roster_complete=len(indexed) == len(run['lifecycles']) == len(lives) and set(indexed) == set(lives),
        source_capsule_only=capsule['schema'] == 'acfqp.utility_source.v118' and capsule['source_status'] == 'complete',
        frozen_models_and_router=True, source_validation_complete=True, source_validation_selection_recomputed=True,
        utility_model_origin_bound=True, predictive_roster_and_versions=True, predictive_terminal=True,
        coverage_bound_to_models=True, prediction_counts_match=True, control_roster=True, control_terminal=True,
        explicit_h2_fallback=True, fresh_paired_streams=True, physical_environment_counts=True,
        execution_checks=bool(run['runner_checks']) and all(run['runner_checks'].values()))
    allowed_cp = {'phase', 'router_p4', 'router_module_id', 'router_payload', 'models', 'fit_logs',
                  'mse_selected_origin', 'mse_selection', 'source_validation_prediction_counts'}
    checks['source_capsule_only'] &= all(set(cp) == allowed_cp for cp in inherited.values())
    checks['source_capsule_only'] &= all(set(phase) == {'name', 'p4', 'source_games', 'checkpoint'}
                                       for life in capsule['lifecycles'] for phase in life['phases'])
    costs = {name: _cost_group() for name in ('source_utility_validation', 'predictive_evaluation', 'control_evaluation')}
    outer_counts = Counter()
    choices, coverage, target_coverage = [], [], []
    case_rows = {phase: {} for phase in PHASES}
    checkpoints = {}
    for life in lives:
        history = indexed.get(life)
        if history is None:
            continue
        checks['execution_checks'] &= bool(history['checks']) and all(history['checks'].values())
        checks['lifecycle_roster_complete'] &= [p['name'] for p in history['phases']] == list(PHASES)
        previous, origin, archives = None, None, {}
        for batch, phase in enumerate(history['phases']):
            name, cp = phase['name'], phase['checkpoint']
            checkpoints[life, name] = cp
            source, module_id = inherited[life, name], cp['router_module_id']
            checks['execution_checks'] &= bool(cp['checks']) and all(cp['checks'].values())
            checks['frozen_models_and_router'] &= (cp['phase'] == source['phase'] == name and cp['router_p4'] == source['router_p4']
                and module_id == source['router_module_id'] and cp['mse_selected_origin'] == source['mse_selected_origin']
                and all(cp['models'][track] == source['models'][track] for track in TRACKS[:-1]))
            rows = cp['source_validation_games']
            if batch == 0:
                actual = dict(selected_candidate='NEW_SHARED', selection_complete=True, summaries={}, acceptance={})
                checks['source_validation_complete'] &= not rows
            else:
                actual = recompute_utility(rows, queries, v_replicas)
                checks['source_validation_complete'] &= actual['selection_complete']
            saved = cp['selection']
            checks['source_validation_selection_recomputed'] &= all(saved[key] == actual[key] for key in actual)
            candidate_models = dict(NEW_SHARED=cp['models']['SHARED'], NEW_SPLIT=cp['models']['SPLIT'], KEEP=previous)
            for row in rows:
                checks['fresh_paired_streams'] &= (row['seed'] == BASE + 1_000_000 + life * 100000 + batch * 10000 + row['replica']
                    and row['method'] == row['candidate'])
                expected_fallback = not all(_covered(candidate_models[row['candidate']], policy, module_id) for policy in policies)
                checks['explicit_h2_fallback'] &= row['result']['fallback_h2'] == expected_fallback and row['result']['routed_module_id'] == module_id
                _add_game_cost(costs['source_utility_validation'], row['result'])
            chosen = actual['selected_candidate']
            if chosen != 'KEEP':
                mode = chosen.removeprefix('NEW_')
                previous, origin = cp['models'][mode], dict(batch=batch, mode=mode)
            current = cp['models']['UTILITY_SELECTED']
            fields = ('mode', 'trees', 'feature_names', 'tree_parameters', 'per_policy_leaf_budget', 'per_policy_node_budget')
            checks['utility_model_origin_bound'] &= cp['utility_selected_origin'] == origin and all(current[key] == previous[key] for key in fields)
            choices.append(dict(life=life, phase=name, selected_candidate=chosen, origin=origin, recomputed=actual))
            versions = dict(CURRENT=cp['models'])
            if name == 'A_RETURN':
                versions.update(archives)
            games = cp['predictive_tests']
            expected = {(policy, replica) for policy in policies for replica in range(p_replicas)}
            checks['predictive_roster_and_versions'] &= len(games) == len(expected) and {(g['policy'], g['replica']) for g in games} == expected
            predictions = {(version, track): [] for version in versions for track in TRACKS}
            for game in games:
                checks['fresh_paired_streams'] &= game['seed'] == BASE + 2_000_000 + life * 100000 + batch * 10000 + policies.index(game['policy']) * 100 + game['replica']
                checks['predictive_terminal'] &= game['status'] in ('WON', 'LOST')
                _add_game_cost(costs['predictive_evaluation'], game)
                records = game['records']
                expected_rows = _expected_records(dict(episode=0, policy=game['policy'], steps=game['steps'], status=game['status']), s['stride'], horizons)
                checks['predictive_roster_and_versions'] &= [(r['anchor_step'], r['horizon']) for r in records] == [(r['anchor_step'], r['horizon']) for r in expected_rows]
                for row in records:
                    checks['predictive_roster_and_versions'] &= (row['context_module_id'] == module_id and row['policy'] == game['policy']
                        and set(row['predictions']) == set(versions) and all(set(group) == set(TRACKS) for group in row['predictions'].values()))
                target_coverage.append(dict(life=life, phase=name, policy=game['policy'], replica=game['replica'], records=len(records),
                    failure_labels=sum(r['target'][1] for r in records), success_labels=sum(r['target'][2] for r in records)))
                for version, models in versions.items():
                    for track in TRACKS:
                        values = [row['predictions'].get(version, {}).get(track) for row in records]
                        predictions[version, track].extend(values)
                        supported = _covered(models[track], game['policy'], module_id)
                        checks['coverage_bound_to_models'] &= all((value is not None) == supported for value in values)
                        for horizon in horizons:
                            positions = [i for i, row in enumerate(records) if row['horizon'] == horizon]
                            available = sum(values[i] is not None for i in positions)
                            complete = bool(positions) and len(positions) == available and game['status'] in ('WON', 'LOST')
                            errors = {field: mean((values[i][c] - records[i]['target'][c]) ** 2 for i in positions)
                                      if complete else None for c, field in enumerate(COMPONENTS)}
                            case_rows[name].setdefault((version, track), []).append(dict(life=life, policy=game['policy'], replica=game['replica'],
                                horizon=horizon, seed=game['seed'], records=len(positions), mse=errors))
                            coverage.append(dict(life=life, phase=name, version=version, track=track, policy=game['policy'], replica=game['replica'],
                                horizon=horizon, requested=len(positions), available=available, complete=complete))
            checks['prediction_counts_match'] &= set(cp['prediction_counts']) == set(versions)
            for version, tracks in cp['prediction_counts'].items():
                checks['prediction_counts_match'] &= set(tracks) == set(TRACKS)
                for track, count in tracks.items():
                    checks['prediction_counts_match'] &= _counts_match(count, predictions[version, track])
                    outer_counts.update(count)
            methods = METHODS + (('UTILITY_B_END_PLAN',) if name == 'A_RETURN' else ())
            controls = cp['control_evaluations']
            expected = {(method, query, replica) for method in methods for query in queries for replica in range(c_replicas)}
            checks['control_roster'] &= len(controls) == len(expected) and {(g['method'], g['query'], g['replica']) for g in controls} == expected
            for game in controls:
                checks['fresh_paired_streams'] &= game['seed'] == BASE + 3_000_000 + life * 100000 + batch * 10000 + game['replica']
                result, method = game['result'], game['method']
                checks['control_terminal'] &= result['status'] in ('WON', 'LOST')
                model = None if method == 'H2_ONLY' else archives['B_END']['UTILITY_SELECTED'] if method == 'UTILITY_B_END_PLAN' else cp['models'][method.removesuffix('_PLAN')]
                fallback = model is not None and not all(_covered(model, policy, module_id) for policy in policies)
                checks['explicit_h2_fallback'] &= result['fallback_h2'] == fallback and result['routed_module_id'] == module_id
                _add_game_cost(costs['control_evaluation'], result)
            if name in ('A', 'B'):
                archives[name + '_END'] = cp['models']
    predictive = {}
    for phase in PHASES:
        versions = ('CURRENT', 'A_END', 'B_END') if phase == 'A_RETURN' else ('CURRENT',)
        summaries, comparisons = {}, {}
        for version in versions:
            summaries[version] = {track: _aggregate_prediction(case_rows[phase].get((version, track), []), lives, policies, horizons, p_replicas) for track in TRACKS}
            for right in TRACKS[:-1]:
                comparisons[f'{version}_UTILITY_SELECTED_minus_{right}'] = _prediction_delta(summaries[version]['UTILITY_SELECTED'], summaries[version][right])
        if phase == 'A_RETURN':
            for track in TRACKS:
                for left, right in (('B_END', 'A_END'), ('CURRENT', 'B_END')):
                    comparisons[f'{track}_{left}_minus_{right}'] = _prediction_delta(summaries[left][track], summaries[right][track])
        predictive[phase] = dict(summaries=summaries, comparisons=comparisons)
    for group in costs.values():
        checks['physical_environment_counts'] &= group['environment']['initial_spawns'] == 2 * group['games'] and group['environment']['environment_random_draws'] == 2 * group['environment']['sampled_transitions'] + 4 * group['games']
    work = dict(groups=costs, outer_prediction_counts=dict(outer_counts), new_tree_fits=0, new_router_observations=0,
        newly_sampled_environment_transitions=sum(g['environment']['sampled_transitions'] for g in costs.values()),
        imagined_model_spawn_samples=sum(g['planning']['model_spawn_samples'] for g in costs.values()),
        new_utility_selection_games=costs['source_utility_validation']['games'],
        new_validation_transitions_attributed_to='UTILITY_SELECTED', actual_wall_seconds=run['actual_wall_seconds'])
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.utility_consolidation_analysis.v118', complete=complete, primary_complete=complete,
        checks=checks, selections=choices, selection_counts=dict(Counter(row['selected_candidate'] for row in choices)),
        predictive=predictive, prediction_coverage=coverage, target_coverage=target_coverage,
        control={phase: _control_summary(checkpoints, phase, lives, queries, c_replicas) for phase in PHASES},
        actual_executed_work=work, inherited_source_work=inherited_source_work(capsule),
        evidence_scope='Frozen V117 source histories and models; fresh utility validation is extra learning experience. '
        'This is not a matched-sampling or criterion-only comparison and does not protect all earlier source batches. '
        'B-end consequence banks use the current A-return router, so return comparisons are not zero-information recovery. '
        'Missing split coverage remains missing; H2 fallback is explicit. No general-learning Gate claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run = json.loads(args.input.read_text())
    capsule = json.loads((args.input.parent / run['source_capsule_file']).read_text())
    result = analyze_run(run, capsule)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))
