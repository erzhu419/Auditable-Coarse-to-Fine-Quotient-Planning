"""Reconcile transition-budgeted TD adaptation, retained outcomes and reuse."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
from itertools import groupby
import json
import math
from pathlib import Path

import numpy as np

LIVES, QUERIES = tuple(range(4)), ('reward', 'risk_goal')
PHASES, METHODS = ('B', 'A_RETURN'), ('CONT', 'RESET')
LABELS, BUDGET, REPLICAS = (0, 131072, 524288), 524288, 8
BASE, MAX_STEPS, BLOCK_SIZE = 121 * 100_000_000, 2000, 64
P_FOUR = {'B': .5, 'A_RETURN': .1}
FIELDS = ('environment_counts', 'planning_counts', 'learning_counts', 'consequence_counts', 'setup_counts')
METRICS = ('score', 'utility', 'steps', 'seconds')


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values and all(x is not None for x in values) else None


def expected_utility(score, status, query):
    return score / 2048 + (4 * (status == 'WON') - 4 * (status == 'LOST') if query == 'risk_goal' else 0)


def expected_train_seed(life, query, phase, episode):
    return BASE + 1_000_000 + life * 10_000_000 + QUERIES.index(query) * 4_000_000 + PHASES.index(phase) * 1_000_000 + episode


def expected_eval_seed(life, phase, replica):
    return BASE + 90_000_000 + life * 100000 + PHASES.index(phase) * 10000 + replica


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            yield json.loads(line)


def new_cost():
    return dict(games=0, seconds=0., setup_seconds=0., statuses=Counter(),
                **{name: Counter() for name in FIELDS})


def add_cost(cost, row):
    result = row['result']
    cost['games'] += 1
    cost['seconds'] += result['seconds']
    cost['setup_seconds'] += result.get('setup_seconds', 0.)
    cost['statuses'][result['status']] += 1
    for field in FIELDS:
        cost[field].update(result.get(field, {}))


def merge_cost(target, source):
    for name in ('games', 'seconds', 'setup_seconds'):
        target[name] += source[name]
    target['statuses'].update(source['statuses'])
    for name in FIELDS:
        target[name].update(source[name])


def compact_valid(row):
    result = row['result']; n = result['steps']; work = result['environment_counts']
    arrays = ('actions', 'spawned_cells', 'spawned_ranks', 'scores')
    return (n > 0 and all(len(row[name]) == n for name in arrays)
        and sum(row['scores']) == result['score']
        and all(action in ('DOWN', 'LEFT', 'RIGHT', 'UP') for action in row['actions'])
        and all(0 <= cell < 16 for cell in row['spawned_cells'])
        and all(rank in (1, 2) for rank in row['spawned_ranks'])
        and len(row['initial_board']) == len(row['final_board']) == 16
        and len(row['initial_spawns']) == 2
        and (max(row['final_board']) >= 11) == (result['status'] == 'WON')
        and work.get('sampled_transitions') == n and work.get('initial_spawns') == 2
        and work.get('environment_random_draws') == 2*n+4
        and work.get('ground_explicit_swipe_calls') == n
        and math.isfinite(result['utility'])
        and result['utility'] == expected_utility(result['score'], result['status'], row['query']))


def empty_block(episode, transitions):
    return dict(start=episode, end=episode, transitions_before=transitions,
        transitions_after=transitions, games=0, statuses=Counter(),
        environment_counts=Counter(), learning_counts=Counter(), total_score=0, seconds=0.)


def inspect_training(rows, life, query, phase, method, initial_updates,
                     budget=BUDGET, middle=LABELS[1], block_size=BLOCK_SIZE):
    """Stream trace rows and reconstruct first-crossing checkpoints and costs."""
    checks = dict(training_roster=True, training_streams=True, training_trace=True,
        exact_training_budget=True, training_caps=True, td_update_timing=True,
        training_counter_deltas=True, no_model_spawns=True)
    transitions, updates, episodes = 0, initial_updates, 0
    prefixes = {0: dict(transitions=0, updates=initial_updates, episodes=0)}
    block, blocks, cost = empty_block(0, 0), [], new_cost()
    for index, row in enumerate(rows):
        result = row['result']; n = result['steps']; status = result['status']
        checks['training_roster'] &= (row['life'] == life and row['query'] == query
            and row['phase'] == phase and row['method'] == method and row['episode_index'] == index)
        checks['training_streams'] &= row['seed'] == expected_train_seed(life, query, phase, index)
        checks['training_trace'] &= compact_valid(row) and status in ('WON', 'LOST', 'CUTOFF')
        cap = min(MAX_STEPS, budget-transitions)
        checks['training_caps'] &= (row['max_steps'] == cap and 0 < n <= cap
            and (status != 'CUTOFF' or n == cap))
        checks['exact_training_budget'] &= (row['transitions_before'] == transitions
            and row['transitions_after'] == transitions+n and transitions+n <= budget)
        delta = n - int(status in ('WON', 'CUTOFF'))
        learn = result['learning_counts']
        checks['td_update_timing'] &= (result['updates_before'] == updates
            and result['updates_after'] == updates+delta
            and row['terminal_update'] == (status == 'LOST')
            and row['analytic_terminal'] == (status == 'WON')
            and row['censored_last_update'] == (status == 'CUTOFF'))
        checks['training_counter_deltas'] &= (learn.get('td_updates', 0) == delta
            and learn.get('choose_calls', 0) == n
            and learn.get('table_update_occurrences', 0) == 32*delta
            and all(value >= 0 for value in learn.values()))
        checks['no_model_spawns'] &= all(not result.get(field, {}).get('model_spawn_samples', 0) for field in FIELDS)
        transitions += n; updates = result['updates_after']; episodes += 1
        add_cost(cost, row)
        block['end'] = episodes; block['transitions_after'] = transitions; block['games'] += 1
        block['statuses'][status] += 1; block['total_score'] += result['score']
        block['seconds'] += result['seconds']
        for name in ('environment_counts', 'learning_counts'):
            block[name].update(result[name])
        checkpoint = middle if middle not in prefixes and transitions >= middle else None
        if transitions == budget:
            checkpoint = budget
        if checkpoint is not None:
            prefixes[checkpoint] = dict(transitions=transitions, updates=updates, episodes=episodes)
        if episodes % block_size == 0 or checkpoint is not None:
            blocks.append(block); block = empty_block(episodes, transitions)
    if block['games']:
        blocks.append(block)
    checks['exact_training_budget'] &= transitions == budget and middle in prefixes and budget in prefixes
    return dict(checks=checks, blocks=blocks, prefixes=prefixes, cost=cost, episodes=episodes)


def outer_key(row):
    return row['life'], row['query'], row['phase'], row['method'], row['checkpoint'], row['replica']


def outer_valid(row, updates):
    result = row['result']; learn = result['learning_counts']
    return (row['seed'] == expected_eval_seed(row['life'], row['phase'], row['replica'])
        and row['max_steps'] == MAX_STEPS and compact_valid(row)
        and result['status'] in ('WON', 'LOST', 'CUTOFF')
        and (result['status'] != 'CUTOFF' or result['steps'] == MAX_STEPS)
        and result['updates_before'] == result['updates_after'] == updates
        and not learn.get('td_updates', 0) and learn.get('choose_calls', 0) == result['steps']
        and all(not result.get(field, {}).get('model_spawn_samples', 0) for field in FIELDS))


def model_valid(directory, checkpoint):
    ref = checkpoint['model_ref']
    if ref == 'implicit_zero':
        return checkpoint['updates'] == 0 and checkpoint['model_origin'] == 'implicit_zero'
    path = directory / ref
    if not path.exists() or ('model_bytes' in checkpoint and path.stat().st_size != checkpoint['model_bytes']):
        return False
    with np.load(path, allow_pickle=False) as data:
        meta = json.loads(str(data['metadata'])); indices, values = data['indices'], data['values']
        return (meta['schema'] == 'controlled_predictive_ntuple_td_v120' and meta['radix'] == 11
            and meta['updates'] == checkpoint['updates'] and len(indices) == len(values)
            and bool(np.isfinite(values).all()) and bool((indices >= 0).all())
            and bool((indices < 4 * 11**6).all()) and bool((np.diff(indices) > 0).all()))


def comparisons(left, right):
    effects = []
    for a, b in zip(left['lifecycles'], right['lifecycles']):
        effects.append(dict(life=a['life'], deltas={field:
            a['means'][field]-b['means'][field] if a['complete'] and b['complete'] else None
            for field in METRICS}))
    utilities = [row['deltas']['utility'] for row in effects]
    return dict(lifecycles=effects,
        mean_deltas={field: mean(row['deltas'][field] for row in effects) for field in METRICS},
        positive=sum(value is not None and value > 0 for value in utilities),
        negative=sum(value is not None and value < 0 for value in utilities))


def summaries(indexed, valid, checkpoints):
    methods, contrasts = {}, {}
    for phase in PHASES:
        methods[phase], contrasts[phase] = {}, {}
        for method in ('FROZEN_A',) + METHODS:
            methods[phase][method] = {}
            for label in ((0,) if method == 'FROZEN_A' else LABELS):
                methods[phase][method][str(label)] = {}
                for query in QUERIES:
                    lives = []
                    for life in LIVES:
                        keys = [(life,query,phase,method,label,replica) for replica in range(REPLICAS)]
                        games = [indexed[key] for key in keys if key in indexed]
                        complete = len(games) == REPLICAS and all(valid.get(key,False) for key in keys)
                        cp = checkpoints.get((life,query,phase,method,label), {})
                        lives.append(dict(life=life, complete=complete, games=len(games),
                            training_transitions=cp.get('transitions'),
                            means={field: mean(row['result'][field] for row in games) if complete else None for field in METRICS},
                            wins=sum(row['result']['status'] == 'WON' for row in games),
                            statuses=dict(Counter(row['result']['status'] for row in games))))
                    methods[phase][method][str(label)][query] = dict(lifecycles=lives,
                        lifecycle_mean={field: mean(row['means'][field] for row in lives) for field in METRICS},
                        mean_training_transitions=mean(row['training_transitions'] for row in lives),
                        wins=sum(row['wins'] for row in lives), games=sum(row['games'] for row in lives),
                        complete=all(row['complete'] for row in lives))
        for name, right_method, right_label in (('CONT_final_minus_FROZEN_A','FROZEN_A',0),
                ('CONT_final_minus_RESET','RESET',BUDGET), ('CONT_final_minus_CONT_initial','CONT',0)):
            contrasts[phase][name] = {query: comparisons(methods[phase]['CONT'][str(BUDGET)][query],
                methods[phase][right_method][str(right_label)][query]) for query in QUERIES}
    retention = {query: comparisons(methods['A_RETURN']['CONT']['0'][query],
        methods['A_RETURN']['FROZEN_A']['0'][query]) for query in QUERIES}
    recovery = deepcopy(contrasts['A_RETURN']['CONT_final_minus_CONT_initial'])
    return dict(methods=methods, comparisons=contrasts,
        return_initial_minus_frozen=retention, return_recovery_change=recovery)


def analyze(directory):
    run = json.loads((directory/'run.json').read_text())
    source = json.loads((directory/'source_capsule.json').read_text())
    expected_settings = dict(lifecycles=list(LIVES),
        queries=dict(reward=dict(reward_weight=1., failure_penalty=0., goal_bonus=0.),
            risk_goal=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)),
        phases=P_FOUR, checkpoints=list(LABELS), train_transitions=BUDGET,
        replicas=REPLICAS, max_steps=MAX_STEPS, workers=4, alpha=.0025,
        block_episodes=BLOCK_SIZE, version_base=BASE)
    checks = dict(frozen_settings=run['settings'] == expected_settings,
        lifecycle_roster=len(run['lifecycles']) == len(LIVES)
            and {row['life'] for row in run['lifecycles']} == set(LIVES),
        source_roster=source['schema'] == 'acfqp.ntuple_regime.v121.source'
            and len(source['snapshots']) == len(LIVES)
            and {row['life'] for row in source['snapshots']} == set(LIVES),
        inherited_costs_match=run['inherited_costs'] == source['inherited_costs'],
        phase_method_roster=True, training_group_roster=True, training_blocks_recomputed=True,
        checkpoint_roster=True, checkpoint_prefix_updates=True, model_origins=True,
        sparse_models_complete=True, model_setup_accounting=True, outer_roster=True,
        outer_aliases=True, outer_summary_matches=True, outer_no_update_paired=True)
    training_cost, outer_cost = new_cost(), new_cost()
    training_groups = []
    by_phase_method = {phase: {method: new_cost() for method in METHODS} for phase in PHASES}
    outer_by_phase_method = {phase: {method: new_cost() for method in ('FROZEN_A',)+METHODS} for phase in PHASES}
    setup_counts, load_counts, save_counts = Counter(), Counter(), Counter()
    setup_seconds = load_seconds = save_seconds = 0.
    model_bytes, aliases, physical_games = 0, 0, 0
    indexed, valid, checkpoints, retained_model_checks = {}, {}, {}, {}
    source_index = {row['life']: row for row in source['snapshots']}
    for history in run['lifecycles']:
        life = history['life']; source_life = source_index[life]
        checks['lifecycle_roster'] &= set(history['queries']) == set(QUERIES)
        for query, data in history['queries'].items():
            source_model = source_life['models'][query]
            checks['phase_method_roster'] &= set(data['phases']) == set(PHASES)
            for phase in PHASES:
                phase_data = data['phases'][phase]
                checks['phase_method_roster'] &= (phase_data['p_four'] == P_FOUR[phase]
                    and set(phase_data['methods']) == set(('FROZEN_A',)+METHODS))
                for method, method_data in phase_data['methods'].items():
                    expected_labels = (0,) if method == 'FROZEN_A' else LABELS
                    checks['checkpoint_roster'] &= tuple(cp['label'] for cp in method_data['checkpoints']) == expected_labels
                    for cp in method_data['checkpoints']:
                        key = (life, query, phase, method, cp['label'])
                        checks['checkpoint_roster'] &= key not in checkpoints
                        checkpoints[key] = cp
                        model_key = (cp['model_ref'], cp['updates'], cp.get('model_bytes'))
                        if model_key not in retained_model_checks:
                            retained_model_checks[model_key] = model_valid(directory, cp)
                        checks['sparse_models_complete'] &= retained_model_checks[model_key]
                        if cp['label']:
                            model_bytes += cp['model_bytes']; save_seconds += cp['save_seconds']
                            save_counts.update(cp['save_counts'])
                            checks['model_origins'] &= cp['model_origin'] == 'v121' and not Path(cp['model_ref']).is_absolute()
                    initial = method_data['checkpoints'][0]
                    if method == 'RESET':
                        expected_origin, expected_updates, origin = 'implicit_zero', 0, 'implicit_zero'
                    elif method == 'CONT' and phase == 'A_RETURN':
                        previous = checkpoints[(life, query, 'B', 'CONT', BUDGET)]
                        expected_origin, expected_updates, origin = previous['model_ref'], previous['updates'], 'v121'
                    else:
                        expected_origin, expected_updates, origin = source_model['path'], source_model['updates'], 'source_v120'
                    checks['model_origins'] &= (initial['model_ref'] == expected_origin
                        and initial['updates'] == expected_updates and initial['model_origin'] == origin
                        and initial['transitions'] == 0)
            found_groups = {}
            for (phase, method), rows in groupby(read_rows(directory/data['training_trace']),
                    key=lambda row: (row['phase'], row['method'])):
                checks['training_group_roster'] &= (phase, method) not in found_groups
                initial_updates = checkpoints[(life, query, phase, method, 0)]['updates']
                found = inspect_training(rows, life, query, phase, method, initial_updates,
                    budget=BUDGET, middle=LABELS[1], block_size=BLOCK_SIZE)
                found_groups[(phase, method)] = found
                for name, value in found['checks'].items():
                    checks[name] = checks.get(name, True) and value
                saved = data['phases'][phase]['methods'][method]
                checks['training_blocks_recomputed'] &= saved['training_blocks'] == found['blocks']
                checks['exact_training_budget'] &= (saved['final_transitions'] == BUDGET
                    and saved['training_episodes'] == found['episodes']
                    and saved['final_updates'] == found['prefixes'].get(BUDGET, {}).get('updates'))
                for label in LABELS:
                    cp = checkpoints[(life, query, phase, method, label)]
                    prefix = found['prefixes'].get(label, {})
                    checks['checkpoint_prefix_updates'] &= (cp['transitions'] == prefix.get('transitions')
                        and cp['updates'] == prefix.get('updates'))
                merge_cost(training_cost, found['cost']); merge_cost(by_phase_method[phase][method], found['cost'])
                training_groups.append(dict(life=life, query=query, phase=phase, method=method,
                    **{name: value for name, value in found.items() if name != 'blocks'}))
            checks['training_group_roster'] &= set(found_groups) == {(phase, method) for phase in PHASES for method in METHODS}
            expected_setup = {('FROZEN_A','B'), ('CONT','B'), ('RESET','B'), ('RESET','A_RETURN')}
            setup_keys = [(row['method'], row['phase_origin']) for row in data['model_setup']]
            checks['model_setup_accounting'] &= len(setup_keys) == len(expected_setup) and set(setup_keys) == expected_setup
            for setup in data['model_setup']:
                is_reset = setup['method'] == 'RESET'
                checks['model_setup_accounting'] &= (setup['origin_ref'] == ('implicit_zero' if is_reset else source_model['path'])
                    and setup['updates_at_creation'] == (0 if is_reset else source_model['updates'])
                    and setup['load_counts'] == ({} if is_reset else dict(checkpoint_loads=1,
                        checkpoint_loaded_parameters=source_model['nonzero_weights'])))
                setup_counts.update(setup['setup_counts']); setup_seconds += setup['setup_seconds']
                load_counts.update(setup['load_counts']); load_seconds += setup['load_seconds']
            raw = list(read_rows(directory/data['control_trace']))
            physical = {row['eval_id']: row for row in raw}
            logical = [row for phase in PHASES for method in ('FROZEN_A',)+METHODS
                for cp in data['phases'][phase]['methods'][method]['checkpoints'] for row in cp['evaluations']]
            expected = {(life,query,phase,method,label,replica) for phase in PHASES
                for method in ('FROZEN_A',)+METHODS for label in ((0,) if method == 'FROZEN_A' else LABELS)
                for replica in range(REPLICAS)}
            logical_keys = [outer_key(row) for row in logical]
            expected_physical = expected - {(life,query,'B','CONT',0,replica) for replica in range(REPLICAS)}
            checks['outer_roster'] &= (len(logical_keys) == len(expected) and set(logical_keys) == expected
                and len(raw) == len(physical) == len(expected_physical)
                and {outer_key(row) for row in raw} == expected_physical)
            for row in raw:
                physical_games += 1; add_cost(outer_cost, row)
                add_cost(outer_by_phase_method[row['phase']][row['method']], row)
                checks['outer_aliases'] &= row['reused_from'] is None
            for row in logical:
                key = outer_key(row); cp = checkpoints[key[:-1]]
                reuse = row['reused_from']
                physical_row = physical.get(reuse or row['eval_id'])
                is_alias = row['phase'] == 'B' and row['method'] == 'CONT' and row['checkpoint'] == 0
                alias_valid = bool(reuse) == is_alias and row['eval_id'] == '/'.join(map(str,key))
                if is_alias:
                    aliases += 1
                    alias_valid &= reuse == f'{life}/{query}/B/FROZEN_A/0/{row["replica"]}'
                checks['outer_aliases'] &= alias_valid
                omitted = {'method','checkpoint','eval_id','reused_from'} if is_alias else set()
                matches = physical_row is not None and all(physical_row.get(name) == value
                    for name, value in row.items() if name not in omitted)
                checks['outer_summary_matches'] &= matches
                merged = {**(physical_row or {}), **row}
                ready = physical_row is not None and outer_valid(merged, cp['updates'])
                checks['outer_no_update_paired'] &= ready
                indexed[key], valid[key] = row, matches and alias_valid and ready and row['result']['status'] != 'CUTOFF'
    cohort = len(LIVES) * len(QUERIES) * REPLICAS
    expected_logical = len(PHASES) * (1 + len(METHODS) * len(LABELS)) * cohort
    checks['physical_logical_cost_roster'] = (physical_games == expected_logical-cohort
        and len(indexed) == expected_logical and aliases == cohort)
    checks['aggregate_training_budget'] = (training_cost['environment_counts']['sampled_transitions']
        == len(PHASES) * len(METHODS) * len(LIVES) * len(QUERIES) * BUDGET)
    inherited_training = Counter()
    for row in source['inherited_costs']['v120_training']:
        for data in row['queries'].values():
            for block in data['training_blocks']:
                inherited_training.update(block['environment_counts'])
    complete = run['status'] == 'complete' and all(checks.values())
    primary_complete = complete and all(valid.values())
    return dict(schema='acfqp.ntuple_regime.v121.analysis', complete=complete,
        primary_complete=primary_complete, checks={name:bool(value) for name,value in checks.items()},
        control=summaries(indexed, valid, checkpoints), training=training_groups,
        costs=dict(training=training_cost, training_by_phase_method=by_phase_method,
            outer=outer_cost, outer_by_phase_method=outer_by_phase_method,
            physical_outer_games=physical_games, logical_outer_rows=len(indexed), reused_outer_rows=aliases,
            learner_setup_counts=dict(setup_counts), learner_setup_seconds=setup_seconds,
            model_load_counts=dict(load_counts), model_load_seconds=load_seconds,
            model_save_counts=dict(save_counts), model_save_seconds=save_seconds,
            retained_new_model_bytes=model_bytes,
            training_environment_transitions=training_cost['environment_counts']['sampled_transitions'],
            actual_environment_transitions=training_cost['environment_counts']['sampled_transitions']
                + outer_cost['environment_counts']['sampled_transitions'],
            model_spawn_samples=sum(cost[field].get('model_spawn_samples',0)
                for cost in (training_cost, outer_cost) for field in FIELDS)),
        inherited_work=dict(v120_training_environment=dict(inherited_training),
            details=deepcopy(source['inherited_costs'])), seconds=run.get('seconds'),
        scope='Four histories, two separately trained objectives, fixed learner and shift; '
            'no unchanged-environment training branch, no structural learning or significance claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.run_dir)
    (args.run_dir/'analysis.json').write_text(json.dumps(report, allow_nan=False, indent=2)+'\n')
    print(json.dumps(dict(complete=report['complete'], primary_complete=report['primary_complete'],
        checks=report['checks'], costs=report['costs']), allow_nan=False))
