"""Independent full-game analysis of frozen-tree and simulated consequences."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import json
import math
from pathlib import Path

LIVES, METHODS, REPLICAS = (0, 1, 2, 3), ('H2_ONLY', 'TREE', 'MC4', 'MC16'), 2
QUERIES = dict(reward=dict(reward_weight=1., failure_penalty=0., goal_bonus=0.),
               risk_goal=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.))
BASE, PLANNER_OFFSET, ROLLOUT_OFFSET = 119 * 100_000_000, 50_000_000, 60_000_000
COMPARISONS = (('MC4', 'TREE'), ('MC16', 'TREE'), ('MC4', 'H2_ONLY'),
               ('MC16', 'H2_ONLY'), ('MC16', 'MC4'), ('TREE', 'H2_ONLY'))


def key(row):
    return row['life'], row['method'], row['query'], row['replica']


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values and all(v is not None for v in values) else None


def utility(result, query):
    q = QUERIES[query]
    return (q['reward_weight'] * result['score'] / 2048
            - q['failure_penalty'] * (result['status'] == 'LOST')
            + q['goal_bonus'] * (result['status'] == 'WON'))


def correct_stream(row):
    seed = BASE + 3_000_000 + row['life'] * 100000 + row['replica']
    return (row['seed'] == seed and row['planner_seed'] == seed + PLANNER_OFFSET
            and row['rollout_seed'] == (seed + ROLLOUT_OFFSET if row['method'].startswith('MC') else None))


def correct_utility(row):
    value = row['result']['utility']
    return row['query'] in QUERIES and math.isfinite(value) and value == utility(row['result'], row['query'])


def physical_counts(result):
    work, steps = result['environment_counts'], result['steps']
    return (work.get('sampled_transitions') == steps and work.get('initial_spawns') == 2
            and work.get('environment_random_draws') == 2 * steps + 4
            and work.get('ground_explicit_swipe_calls') == steps
            and work.get('ground_state_status_calls') == steps + 1)


def raw_checks(row, summary):
    """Check retained execution history without importing actor or dynamics code."""
    ep, result, decisions = row['episode'], row['result'], row['decisions']
    steps = ep['steps']
    matches = summary is not None and {k: v for k, v in row.items() if k not in ('episode', 'decisions')} == summary
    matches &= (ep['seed'] == row['seed'] and ep['return_score'] == result['score']
        and ep['status'] == result['status'] and ep['steps_count'] == result['steps']
        and ep['work'] == result['environment_counts'] and ep['seconds'] == result['seconds'])
    history = (len(steps) == len(decisions) == result['steps'] and bool(steps)
        and sum(step['score'] for step in steps) == result['score'])
    board = ep['initial_board']
    for i, step in enumerate(steps):
        history &= (step['board'] == board and len(board) == 16
            and step['status'] == (result['status'] if i == len(steps) - 1 and result['status'] != 'CUTOFF' else 'ACTIVE'))
        after, next_board = step['afterstate'], step['next_board']
        cell, rank = step['spawned_cell'], step['spawned_rank']
        history &= (len(after) == len(next_board) == 16 and 0 <= cell < 16 and rank in (1, 2))
        if 0 <= cell < 16 and len(after) == len(next_board) == 16:
            expected = list(after)
            expected[cell] = rank
            history &= after[cell] == 0 and next_board == expected
        if i < len(decisions):
            decision = decisions[i]
            history &= decision['action'] == step['action'] and decision['action'] in decision['action_values']
            if decision['action'] in decision['action_values']:
                selected = decision['action_values'][decision['action']]
                history &= decision['value'] == selected['value'] == max(x['value'] for x in decision['action_values'].values())
        board = next_board
    history &= board == ep['final_board']
    return bool(matches), bool(history)


def cost_group(rows):
    groups = {field: Counter() for field in ('environment', 'planning', 'consequence', 'setup')}
    for row in rows:
        for field in groups:
            groups[field].update(row['result'][field + '_counts'])
    return dict(games=len(rows), **{field: dict(counts) for field, counts in groups.items()},
        episode_seconds=sum(row['result']['seconds'] for row in rows),
        setup_seconds=sum(row['result']['setup_seconds'] for row in rows),
        total_model_spawn_samples=groups['planning']['model_spawn_samples'] + groups['consequence']['model_spawn_samples'])


def analyze_run(run, capsule, raw_rows):
    expected = {(life, method, query, replica) for life in LIVES for method in METHODS
                for query in QUERIES for replica in range(REPLICAS)}
    rows = [row for life in run['lifecycles'] for row in life['games']]
    summaries, raw = {key(row): row for row in rows}, {key(row): row for row in raw_rows}
    settings = run['settings']
    snapshots = capsule['snapshots']
    checks = dict(
        frozen_settings=(settings['lifecycles'] == list(LIVES) and settings['methods'] == list(METHODS)
            and settings['queries'] == QUERIES and settings['replicas'] == REPLICAS
            and settings['phase'] == 'A_RETURN' and settings['max_steps'] == 2000
            and settings['version_base'] == BASE and settings['planner_offset'] == PLANNER_OFFSET
            and settings['rollout_offset'] == ROLLOUT_OFFSET),
        lifecycle_roster=(len(run['lifecycles']) == len(LIVES)
            and {x['life'] for x in run['lifecycles']} == set(LIVES)
            and all(row['life'] == life['life'] for life in run['lifecycles'] for row in life['games'])),
        summary_roster=len(rows) == len(summaries) == len(expected) and set(summaries) == expected,
        retained_roster=len(raw_rows) == len(raw) == len(expected) and set(raw) == expected,
        source_capsule_only=(capsule['schema'] == 'acfqp.rollout_source.v119'
            and set(capsule) == {'schema', 'snapshots', 'inherited_costs'}
            and len(snapshots) == len(LIVES) and {x['life'] for x in snapshots} == set(LIVES)
            and all(set(x) == {'life', 'phase', 'module_id', 'rule', 'model', 'selected_origin', 'source_choices'}
                and x['phase'] == 'A_RETURN' for x in snapshots)),
        inherited_costs_match=run['inherited_costs'] == capsule['inherited_costs'],
        source_read_only=True, fresh_paired_streams=True, terminal_games=True,
        utility_recomputed=True, physical_environment_counts=True,
        retained_summary_matches=True, retained_action_histories=True,
        no_new_training=True)
    all_rows = rows + raw_rows
    for row in all_rows:
        result = row['result']
        checks['source_read_only'] &= result['source_unchanged'] is True
        checks['fresh_paired_streams'] &= correct_stream(row)
        checks['terminal_games'] &= result['status'] in ('WON', 'LOST')
        checks['utility_recomputed'] &= correct_utility(row)
        checks['physical_environment_counts'] &= physical_counts(result)
        checks['no_new_training'] &= all(not count.get(name, 0)
            for count in (result['environment_counts'], result['planning_counts'], result['consequence_counts'], result['setup_counts'])
            for name in ('tree_fits', 'fit_calls', 'router_observations', 'new_tree_fits'))
    valid_raw = {}
    for row in raw_rows:
        matches, history = raw_checks(row, summaries.get(key(row)))
        checks['retained_summary_matches'] &= matches
        checks['retained_action_histories'] &= history
        valid_raw[key(row)] = matches and history
    # Retain incurred costs even when a summary or trajectory is missing.
    cost_rows = raw_rows + [row for row in rows if key(row) not in raw]
    methods, contrasts = {}, {}
    for method in METHODS:
        methods[method] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                games = [summaries.get((life, method, query, r)) for r in range(REPLICAS)]
                present = [g for g in games if g is not None]
                complete = all(g is not None and valid_raw.get(key(g), False) and correct_stream(g)
                    and correct_utility(g) and g['result']['status'] in ('WON', 'LOST') for g in games)
                values = {field: mean(g['result'][field] for g in present) if complete else None
                          for field in ('score', 'utility', 'steps', 'seconds', 'setup_seconds')}
                lives.append(dict(life=life, complete=complete, games=len(present), means=values,
                    statuses=dict(Counter(g['result']['status'] for g in present)),
                    win_fraction=sum(g['result']['status'] == 'WON' for g in present) / REPLICAS if complete else None,
                    lost_fraction=sum(g['result']['status'] == 'LOST' for g in present) / REPLICAS if complete else None))
            methods[method][query] = dict(lifecycles=lives, complete=all(x['complete'] for x in lives),
                lifecycle_mean={f: mean(x['means'][f] for x in lives) for f in lives[0]['means']},
                win_fraction=mean(x['win_fraction'] for x in lives), lost_fraction=mean(x['lost_fraction'] for x in lives),
                statuses=dict(sum((Counter(x['statuses']) for x in lives), Counter())))
    for left, right in COMPARISONS:
        by_query = {}
        for query in QUERIES:
            effects = []
            for lrow, rrow in zip(methods[left][query]['lifecycles'], methods[right][query]['lifecycles']):
                complete = lrow['complete'] and rrow['complete']
                effects.append(dict(life=lrow['life'], complete=complete,
                    deltas={field: lrow['means'][field] - rrow['means'][field] if complete else None for field in lrow['means']}))
            utilities = [x['deltas']['utility'] for x in effects]
            by_query[query] = dict(lifecycles=effects, complete=all(x['complete'] for x in effects),
                mean_deltas={field: mean(x['deltas'][field] for x in effects) for field in effects[0]['deltas']},
                utility_signs=dict(positive=sum(x is not None and x > 0 for x in utilities),
                    negative=sum(x is not None and x < 0 for x in utilities), equal=sum(x == 0 for x in utilities),
                    missing=sum(x is None for x in utilities)))
        contrasts[left + '_minus_' + right] = by_query
    totals = cost_group(cost_rows)
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.rollout_consequences_analysis.v119', complete=complete, primary_complete=complete,
        checks={name: bool(value) for name, value in checks.items()}, control=dict(methods=methods, comparisons=contrasts),
        actual_executed_work=dict(total=totals,
            methods={method: cost_group([row for row in cost_rows if row['method'] == method]) for method in METHODS},
            newly_sampled_environment_transitions=totals['environment'].get('sampled_transitions', 0),
            imagined_model_spawn_samples=totals['total_model_spawn_samples'],
            new_tree_fits=sum(row['result'][group].get('tree_fits', 0) for row in cost_rows
                for group in ('environment_counts', 'planning_counts', 'consequence_counts', 'setup_counts')),
            new_router_observations=sum(row['result'][group].get('router_observations', 0) for row in cost_rows
                for group in ('environment_counts', 'planning_counts', 'consequence_counts', 'setup_counts')),
            retained_cost_rows=len(raw_rows), summary_only_cost_rows=len(cost_rows) - len(raw_rows),
            wall_seconds=run.get('seconds')),
        inherited_source_work=deepcopy(capsule['inherited_costs']),
        evidence_scope='Four frozen A_RETURN source histories, two paired outer replicas per query. '
            'MC4 and MC16 are finite simulated consequences, not an oracle or learned compression. '
            'All costs and cutoffs retained; no general-learning or sampling-efficiency Gate claim.')


def analyze_directory(directory):
    run = json.loads((directory / 'run.json').read_text())
    capsule = json.loads((directory / 'source_capsule.json').read_text())
    raw = []
    for life in LIVES:
        path = directory / f'life_{life}' / 'control_games.jsonl.gz'
        if path.exists():
            with gzip.open(path, 'rt') as stream:
                raw.extend(json.loads(line) for line in stream if line.strip())
    return analyze_run(run, capsule, raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = analyze_directory(args.run_dir)
    (args.output or args.run_dir / 'analysis.json').write_text(json.dumps(result, allow_nan=False, indent=2) + '\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'],
        checks_passed=sum(result['checks'].values()), checks_total=len(result['checks']),
        costs=result['actual_executed_work'],
        utility_contrasts={name: {q: x['mean_deltas']['utility'] for q, x in rows.items()}
            for name, rows in result['control']['comparisons'].items()})))
