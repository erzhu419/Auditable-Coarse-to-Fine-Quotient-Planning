"""Independently reconcile persistent TD training and common-cohort evaluation."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import json
import math
from pathlib import Path
import numpy as np

LIVES, QUERIES, AGES = tuple(range(4)), ('reward', 'risk_goal'), (0, 256, 1024, 4096)
REPLICAS, BASE = 8, 120 * 100_000_000
FIELDS = ('environment_counts', 'planning_counts', 'learning_counts', 'consequence_counts', 'setup_counts')
TAGS = tuple('TD_' + str(age) for age in AGES) + ('H2_ONLY', 'MC4')


def mean(values):
    values = list(values)
    return sum(values)/len(values) if values and all(x is not None for x in values) else None


def expected_utility(score, status, query):
    return score/2048 + (4 * (status == 'WON') - 4 * (status == 'LOST') if query == 'risk_goal' else 0)


def new_cost():
    return dict(games=0, seconds=0., setup_seconds=0., statuses=Counter(),
        **{field: Counter() for field in FIELDS})


def add_cost(cost, row):
    r = row['result']
    cost['games'] += 1
    cost['seconds'] += r['seconds']
    cost['setup_seconds'] += r['setup_seconds']
    cost['statuses'][r['status']] += 1
    for field in FIELDS:
        cost[field].update(r.get(field, {}))


def compact_valid(row):
    r = row['result']; n = r['steps']; work = r['environment_counts']
    arrays = ('actions', 'spawned_cells', 'spawned_ranks', 'scores')
    return (n > 0 and all(len(row[name]) == n for name in arrays)
        and sum(row['scores']) == r['score']
        and all(a in ('DOWN', 'LEFT', 'RIGHT', 'UP') for a in row['actions'])
        and all(0 <= cell < 16 for cell in row['spawned_cells'])
        and all(rank in (1, 2) for rank in row['spawned_ranks'])
        and len(row['initial_board']) == len(row['final_board']) == 16
        and len(row['initial_spawns']) == 2
        and (max(row['final_board']) >= 11) == (r['status'] == 'WON')
        and work.get('sampled_transitions') == n and work.get('initial_spawns') == 2
        and work.get('environment_random_draws') == 2*n+4
        and work.get('ground_explicit_swipe_calls') == n
        and math.isfinite(r['utility'])
        and r['utility'] == expected_utility(r['score'], r['status'], row['query']))


def inspect_training(rows, life, query, ages=AGES, block_size=256):
    """Stream replay traces; avoid retaining millions of transitions in RAM."""
    checks = dict(training_roster=True, training_streams=True, training_trace=True,
        training_terminal=True, td_update_timing=True, no_training_model_spawns=True)
    blocks, prefixes, updates, total_games = [], {0: 0}, 0, 0
    start, cost, total_score = 0, new_cost(), 0
    for index, row in enumerate(rows):
        r = row['result']
        checks['training_roster'] &= (row['life'] == life and row['query'] == query
            and row['method'] == 'TRAIN' and row['episode_index'] == index)
        checks['training_streams'] &= row['seed'] == BASE + 1_000_000 + life*100000 + QUERIES.index(query)*10000 + index
        checks['training_trace'] &= compact_valid(row)
        checks['training_terminal'] &= r['status'] in ('WON', 'LOST')
        expected = r['steps'] - int(r['status'] in ('WON', 'CUTOFF'))
        checks['td_update_timing'] &= (r['updates_before'] == updates and
            r['updates_after'] - r['updates_before'] == expected
            and r['learning_counts'].get('td_updates', 0) == expected
            and row['terminal_update'] == (r['status'] == 'LOST')
            and row['analytic_terminal'] == (r['status'] == 'WON')
            and row['censored_last_update'] == (r['status'] == 'CUTOFF'))
        checks['no_training_model_spawns'] &= all(
            not r[field].get('model_spawn_samples', 0) for field in ('planning_counts', 'learning_counts'))
        updates = r['updates_after']; total_games += 1
        add_cost(cost, row); total_score += r['score']
        if total_games in ages[1:]:
            prefixes[total_games] = updates
        if total_games % block_size == 0:
            blocks.append(dict(start=start, end=total_games, total_score=total_score, **cost))
            start, cost, total_score = total_games, new_cost(), 0
    checks['training_roster'] &= total_games == ages[-1]
    if cost['games']:
        blocks.append(dict(start=start, end=total_games, total_score=total_score, **cost))
    return dict(checks=checks, blocks=blocks, prefix_updates=prefixes, games=total_games)


def outer_key(row):
    return row['life'], row['query'], row['method'], row['checkpoint'], row['replica']


def outer_valid(row, updates=None):
    r = row['result']; age = row['checkpoint']; method = row['method']
    expected_seed = BASE + 2_000_000 + row['life'] * 100000 + row['replica']
    return (row['seed'] == expected_seed and r['status'] in ('WON', 'LOST')
        and compact_valid(row) and r.get('updates_before',0) == r.get('updates_after',0)
        and (method != 'TD' or r['updates_before'] == updates)
        and (method == 'TD' or (row['planner_seed'] == expected_seed+50_000_000
            and row['rollout_seed'] == (expected_seed+60_000_000 if method=='MC4' else None)))
        and not r['learning_counts'].get('td_updates', 0))


def summaries(indexed, validity):
    methods, contrasts = {}, {}
    for tag in TAGS:
        method, age = ('TD', int(tag[3:])) if tag.startswith('TD_') else (tag, None)
        methods[tag] = {}
        for query in QUERIES:
            rows = []
            for life in LIVES:
                keys = [(life, query, method, age, replica) for replica in range(REPLICAS)]
                games = [indexed[key] for key in keys if key in indexed]
                complete = len(games) == REPLICAS and all(validity.get(key, False) for key in keys)
                rows.append(dict(life=life, complete=complete, games=len(games),
                    means={field: mean(g['result'][field] for g in games) if complete else None
                        for field in ('score', 'utility', 'steps', 'seconds')},
                    wins=sum(g['result']['status'] == 'WON' for g in games),
                    statuses=dict(Counter(g['result']['status'] for g in games))))
            methods[tag][query] = dict(lifecycles=rows,
                lifecycle_mean={field: mean(row['means'][field] for row in rows) for field in ('score','utility','steps','seconds')},
                wins=sum(row['wins'] for row in rows), games=sum(row['games'] for row in rows),
                complete=all(row['complete'] for row in rows))
    for right in ('TD_0', 'TD_256', 'TD_1024', 'H2_ONLY', 'MC4'):
        group = {}
        for query in QUERIES:
            effects = []
            for left, old in zip(methods['TD_4096'][query]['lifecycles'], methods[right][query]['lifecycles']):
                effects.append(dict(life=left['life'], deltas={field:
                    left['means'][field] - old['means'][field]
                    if left['complete'] and old['complete'] else None
                    for field in ('score','utility','steps','seconds')}))
            utilities = [row['deltas']['utility'] for row in effects]
            group[query] = dict(lifecycles=effects,
                mean_deltas={field: mean(row['deltas'][field] for row in effects) for field in effects[0]['deltas']},
                positive=sum(value is not None and value>0 for value in utilities),
                negative=sum(value is not None and value<0 for value in utilities))
        contrasts['TD_4096_minus_' + right] = group
    return dict(methods=methods, comparisons=contrasts)


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            yield json.loads(line)


def model_valid(path, checkpoint):
    if not path.exists() or path.stat().st_size != checkpoint['model_bytes']:
        return False
    with np.load(path, allow_pickle=False) as data:
        meta = json.loads(str(data['metadata']))
        indices, values = data['indices'], data['values']
        return (meta['schema'] == 'controlled_predictive_ntuple_td_v120' and meta['radix'] == 11
            and meta['updates'] == checkpoint['updates'] and len(indices) == len(values)
            and bool(np.isfinite(values).all())
            and bool((indices >= 0).all()) and bool((indices < 4 * 11**6).all())
            and bool((np.diff(indices) > 0).all()))


def analyze(directory):
    run = json.loads((directory/'run.json').read_text())
    source = json.loads((directory/'source_capsule.json').read_text())
    s = run['settings']
    checks = dict(lifecycle_roster=len(run['lifecycles']) == 4 and
        {x['life'] for x in run['lifecycles']} == set(LIVES),
        frozen_settings=(s['lifecycles']==list(LIVES) and s['train_episodes']==4096
            and s['checkpoints']==list(AGES) and s['replicas']==8 and s['max_steps']==2000
            and s['alpha']==.0025 and s['block_size']==256 and s['p_four']==.1
            and s['version_base']==BASE and s['planner_offset']==50_000_000 and s['rollout_offset']==60_000_000
            and s['queries']==dict(reward=dict(reward_weight=1.,failure_penalty=0.,goal_bonus=0.),
                risk_goal=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.))),
        source_only_rules=(source['schema']=='acfqp.ntuple_source.v120'
            and set(source)=={'schema','snapshots','inherited_costs'}
            and len(source['snapshots'])==4 and {x['life'] for x in source['snapshots']}==set(LIVES)
            and all(set(x) == {'life', 'rule'} for x in source['snapshots'])),
        inherited_costs_match=run['inherited_costs'] == source['inherited_costs'],
        checkpoint_roster=True, training_blocks_recomputed=True, checkpoint_prefix_updates=True,
        sparse_models_complete=True, outer_roster=True, outer_summary_matches=True,
        outer_no_update_terminal_paired=True)
    cost_training, cost_outer = new_cost(), {tag: new_cost() for tag in TAGS}
    setup, save_counts, save_seconds, model_bytes, query_training, indexed, valid = Counter(), Counter(), 0., 0, [], {}, {}
    setup_seconds = 0.
    for life in run['lifecycles']:
        ident = life['life']
        checks['lifecycle_roster'] &= set(life['queries']) == set(QUERIES)
        for query, data in life['queries'].items():
            found = inspect_training(read_rows(directory/data['training_trace']), ident, query)
            for name, value in found['checks'].items():
                checks[name] = checks.get(name, True) and value
            saved_blocks = data['training_blocks']
            checks['training_blocks_recomputed'] &= len(saved_blocks) == len(found['blocks'])
            for actual, saved in zip(found['blocks'], saved_blocks):
                for name in ('start','end','games','environment_counts','learning_counts','statuses','total_score','seconds'):
                    checks['training_blocks_recomputed'] &= actual[name] == saved[name]
                for field in FIELDS:
                    cost_training[field].update(actual[field])
                for name in ('games','seconds','setup_seconds'):
                    cost_training[name] += actual[name]
                cost_training['statuses'].update(actual['statuses'])
            query_training.append(dict(life=ident, query=query, **found))
            setup.update(data.get('setup_counts', {}))
            setup_seconds += data.get('setup_seconds', 0.)
            checkpoints = data['checkpoints']
            checks['checkpoint_roster'] &= [cp['episodes'] for cp in checkpoints] == list(AGES)
            summary_rows = list(data['references'])
            for cp in checkpoints:
                checks['checkpoint_prefix_updates'] &= cp['updates'] == found['prefix_updates'].get(cp['episodes'])
                checks['sparse_models_complete'] &= model_valid(directory/cp['model_file'], cp)
                model_bytes += cp['model_bytes']
                save_seconds += cp['save_seconds']
                save_counts.update(cp['save_counts'])
                summary_rows.extend(cp['evaluations'])
            saved = {outer_key(row): row for row in summary_rows}
            raw_rows = list(read_rows(directory/data['control_trace']))
            expected = {(ident,query,'TD',age,rep) for age in AGES for rep in range(REPLICAS)}
            expected |= {(ident,query,method,None,rep) for method in ('H2_ONLY','MC4') for rep in range(REPLICAS)}
            raw_keys = {outer_key(row) for row in raw_rows}
            checks['outer_roster'] &= len(summary_rows) == len(saved) == len(raw_rows) == len(raw_keys) == len(expected) and set(saved) == raw_keys == expected
            for row in raw_rows:
                key = outer_key(row)
                summary = saved.get(key)
                matches = summary is not None and all(row.get(name) == value for name,value in summary.items())
                checks['outer_summary_matches'] &= matches
                ready = outer_valid(row, found['prefix_updates'].get(row['checkpoint']))
                checks['outer_no_update_terminal_paired'] &= ready
                indexed[key], valid[key] = row, matches and ready
                tag = 'TD_' + str(row['checkpoint']) if row['method'] == 'TD' else row['method']
                if tag in cost_outer:
                    add_cost(cost_outer[tag], row)
    totals = Counter(cost_training['environment_counts'])
    for cost in cost_outer.values():
        totals.update(cost['environment_counts'])
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.ntuple_learning.v120.analysis', complete=complete, primary_complete=complete,
        checks={k: bool(v) for k,v in checks.items()}, control=summaries(indexed, valid),
        training=query_training, costs=dict(training=cost_training, outer=cost_outer,
            learner_setup_counts=dict(setup), learner_setup_seconds=setup_seconds,
            model_save_counts=dict(save_counts),
            model_save_seconds=save_seconds, retained_model_bytes=model_bytes,
            dense_parameters_per_query_model=4*11**6, dense_bytes_per_query_model=4*11**6*8,
            actual_environment_transitions=totals['sampled_transitions'],
            training_environment_transitions=cost_training['environment_counts']['sampled_transitions'],
            model_spawn_samples=sum(cost['planning_counts'].get('model_spawn_samples',0)
                +cost['learning_counts'].get('model_spawn_samples',0)
                +cost['consequence_counts'].get('model_spawn_samples',0) for cost in cost_outer.values())),
        inherited_source_work=deepcopy(source['inherited_costs']), seconds=run.get('seconds'),
        scope='Separate query-specific scalar TD actors, fixed dynamics/representation, common frozen outer cohort; no structure learning or sample-efficiency claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    args = parser.parse_args()
    report = analyze(args.run_dir)
    (args.run_dir/'analysis.json').write_text(json.dumps(report, allow_nan=False, indent=2)+'\n')
    print(json.dumps(dict(complete=report['complete'], checks=report['checks'],
        training_transitions=report['costs']['training_environment_transitions'],
        utility_contrasts={name: {q: v['mean_deltas']['utility'] for q,v in group.items()}
            for name,group in report['control']['comparisons'].items()})))
