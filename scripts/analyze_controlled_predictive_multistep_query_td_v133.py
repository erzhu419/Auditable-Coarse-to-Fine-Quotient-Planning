"""Independently reconcile fixed multi-step and single-step TD training and frozen full-game curves."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_policy_consequences_v126 as old
from scripts import analyze_controlled_predictive_online_query_td_v131 as single

LIVES, KINDS, METHODS = tuple(range(4)), ('SINGLE', 'MULTI'), ('PARENT', 'SINGLE', 'MULTI')
QUERIES = {q: old.QUERIES[q] for q in ('risk1', 'risk8')}
PARENTS = dict(risk1='reward', risk8='risk_goal')
CHECKPOINTS, REPLICAS = (0, 32768, 131072, 524288), 16
BASE, MAX_STEPS, RATE = 133*100000000, 2000, .0025
read_rows = old.read_rows


def mean(values):
    values = list(values)
    return None if not values or any(v is None for v in values) else sum(values)/len(values)


def full_game_curve(indexed, valid):
    """Pair within histories and average all four histories equally at every age.

    Indexed rows include the explicitly declared parent/age-zero aliases. A
    cutoff is retained as observed work, but cannot stand in for terminal return.
    """
    curve = []
    for checkpoint in CHECKPOINTS:
        methods, comparisons = {}, {}
        for method in METHODS:
            methods[method] = {}
            for query in QUERIES:
                lives = []
                for life in LIVES:
                    keys = [(life, query, method, checkpoint, i) for i in range(REPLICAS)]
                    rows = [indexed[k] for k in keys if k in indexed]
                    complete = all(k in indexed and valid.get(k, False)
                        and indexed[k]['result']['status'] in ('WON', 'LOST') for k in keys)
                    lives.append(dict(life=life, complete=complete, games=len(rows),
                        statuses=dict(Counter(r['result']['status'] for r in rows)),
                        wins=sum(r['result']['status'] == 'WON' for r in rows),
                        means={name: mean(r['result'][name] for r in rows) if complete else None
                            for name in ('utility', 'score', 'steps')}))
                methods[method][query] = dict(lifecycles=lives,
                    complete=all(r['complete'] for r in lives),
                    means={name: mean(r['means'][name] for r in lives)
                        for name in ('utility', 'score', 'steps')})
        for other in ('SINGLE', 'PARENT'):
            name = 'MULTI_minus_'+other; comparisons[name] = {}
            for query in QUERIES:
                lives = []
                for life in LIVES:
                    complete = (methods['MULTI'][query]['lifecycles'][life]['complete']
                        and methods[other][query]['lifecycles'][life]['complete'])
                    item = dict(life=life, complete=complete)
                    if complete:
                        deltas = [indexed[(life, query, 'MULTI', checkpoint, i)]['result']['utility']-
                            indexed[(life, query, other, checkpoint, i)]['result']['utility']
                            for i in range(REPLICAS)]
                        item.update(mean=mean(deltas), replica_deltas=deltas)
                    lives.append(item)
                comparisons[name][query] = dict(lifecycles=lives,
                    complete=all(r['complete'] for r in lives),
                    mean=mean(r.get('mean') for r in lives),
                    positive=sum(r.get('mean', 0) > 0 for r in lives),
                    negative=sum(r.get('mean', 0) < 0 for r in lives),
                    zero=sum(r.get('mean') == 0 for r in lives))
        curve.append(dict(checkpoint=checkpoint, methods=methods, comparisons=comparisons))
    return dict(curve=curve, primary_checkpoint=CHECKPOINTS[-1], primary=curve[-1],
        complete=all(v['complete'] for row in curve for methods in row['methods'].values() for v in methods.values()))



HORIZON = 32

def expected_offset(source, query):
    return single.expected_offset(source, query, 'PRIOR')

def training_seed(life, query, episode):
    return BASE+10000000+life*1000000+list(QUERIES).index(query)*500000+episode

def outer_seed(life, replica):
    return BASE+90000000+life*100000+replica

def expected_target(scores, start, end, boundary, query, bootstrap=None):
    """Afterstate target excludes own reward and includes endpoint Q exactly once.

    Indices refer to actions in one episode. BOOTSTRAP at ``end`` uses chosen
    pre-update Q there; terminal end includes that terminal action. Integer
    score sums precede one /2048 division, matching the frozen objective.
    """
    q = QUERIES[query]
    if boundary == 'BOOTSTRAP':
        if bootstrap is None: raise ValueError('bootstrap value is required')
        return sum(scores[start+1:end])/2048. + bootstrap
    if boundary == 'WIN_BOUNDARY':
        return sum(scores[start+1:end+1])/2048. + q['goal_bonus']
    if boundary == 'LOSS':
        return sum(scores[start+1:end+1])/2048. - q['failure_penalty']
    raise ValueError(boundary)


def multi_segment_checks(row, previous, query, source, horizon=HORIZON):
    """Reconstruct queue timing and every target from retained score prefixes.

    Source-action identities, not board equality, establish one update each.
    Board values are checked against their recorded update and checkpoint
    entries; this audit does not repeat the environment or replay the weights.
    """
    n, status = len(row['actions']), row['status']; q = QUERIES[query]
    first = row['start_step'] == 0; offset = expected_offset(source, query)
    src = old.QUERIES[PARENTS[query]]
    failure = src['failure_penalty']-q['failure_penalty']
    success = ((q['failure_penalty']+q['goal_bonus'])-(src['failure_penalty']+src['goal_bonus']))*source['counts'][PARENTS[query]]['constant']
    arrays = ('scores', 'spawned_cells', 'spawned_ranks', 'chosen_values', 'chosen_raw_values')
    checks = dict(segment_shape=0 < n and row['horizon'] == horizon and all(len(row[k]) == n for k in arrays)
        and row['end_step']-row['start_step'] == n and row['end_step'] <= MAX_STEPS
        and all(a in ('DOWN', 'LEFT', 'RIGHT', 'UP') for a in row['actions'])
        and all(0 <= c < 16 for c in row['spawned_cells'])
        and all(r in (1, 2) for r in row['spawned_ranks']),
        segment_terminal=status in ('ACTIVE', 'WON', 'LOST', 'CUTOFF')
        and single.board_status(row['end_board']) == ('ACTIVE' if status == 'CUTOFF' else status)
        and (status != 'CUTOFF' or row['end_step'] == MAX_STEPS)
        and row['budget_status'] == ('BUDGET_END' if status == 'ACTIVE' else 'EPISODE_END'),
        segment_continuity=True, initial_spawns=True, td_targets=True,
        queue_semantics=True, training_counters=True)
    if not checks['segment_shape']: return {k: False for k in checks}
    if first:
        spawns = row.get('initial_spawns', []); board = [0]*16
        for spawn in spawns: board[spawn['cell']] = spawn['rank']
        checks['initial_spawns'] &= (len(spawns) == 2 and len({s['cell'] for s in spawns}) == 2
            and board == row['start_board'] and row['queue_before'] == [])
    else:
        checks['initial_spawns'] &= 'initial_spawns' not in row and len(row['queue_before']) > 0
    if previous is None:
        checks['segment_continuity'] &= row['episode'] == 0 and first and row['updates_before'] == 0
    else:
        same = previous['status'] == 'ACTIVE'
        checks['segment_continuity'] &= (row['updates_before'] == previous['updates_after']
            and row['cumulative_transitions'] == previous['cumulative_transitions']+n
            and row['episode'] == previous['episode']+int(not same)
            and (not same or (row['seed'] == previous['seed'] and row['start_step'] == previous['end_step']
                and row['start_board'] == previous['end_board'] and row['queue_before'] == previous['queue_after']))
            and (same or first))
    prefix = 0 if first else previous['return_score']
    checks['segment_continuity'] &= row['start_return_score'] == prefix and row['return_score'] == prefix+sum(row['scores'])
    queue = [dict(item) for item in row['queue_before']]
    records = row['update_records']; seen = set(); boards = {}
    for item in queue:
        boards[item['step']] = item['afterstate']
    for update in records:
        step = update['start_step']
        checks['queue_semantics'] &= step not in seen
        seen.add(step)
        if step in boards: checks['queue_semantics'] &= boards[step] == update['afterstate']
        boards[step] = update['afterstate']
    for item in row['queue_after']:
        step = item['step']
        checks['queue_semantics'] &= step not in seen
        if step in boards: checks['queue_semantics'] &= boards[step] == item['afterstate']
        boards[step] = item['afterstate']
    # CUTOFF afterstates discarded before fitting are retained in censored_queue.
    for item in row.get('censored_queue', []):
        step = item['step']
        checks['queue_semantics'] &= step not in seen
        if step in boards: checks['queue_semantics'] &= boards[step] == item['afterstate']
        boards[step] = item['afterstate']
    cursor = 0
    def consume(entry, endpoint, phase, category, reward_score, tail):
        nonlocal cursor
        if cursor >= len(records):
            checks['queue_semantics'] = False; return
        update = records[cursor]; cursor += 1
        checks['queue_semantics'] &= (update['start_step'] == entry['step']
            and update['end_step'] == endpoint and update['phase'] == phase
            and update['type'] == category and update['afterstate'] == entry['afterstate'])
        target = reward_score/2048.+tail
        checks['td_targets'] &= (update['reward_score'] == reward_score and update['tail'] == tail
            and update['target'] == target and update['raw_target'] == target-offset
            and all(math.isfinite(update[k]) for k in ('tail', 'target', 'raw_target', 'error'))
            and update['work'].get('td_updates') == 1)
    for i, (score, value, raw) in enumerate(zip(row['scores'], row['chosen_values'], row['chosen_raw_values'])):
        step = row['start_step']+i; winning = status == 'WON' and i == n-1
        expected_value = score/2048.+q['goal_bonus'] if winning else raw+failure+success
        checks['td_targets'] &= math.isfinite(raw) and value == expected_value
        if queue and step-queue[0]['step'] >= horizon:
            item = queue.pop(0)
            checks['queue_semantics'] &= step-item['step'] == horizon
            consume(item, step, 'PRE_ACTION', 'WIN_BOUNDARY' if winning else 'BOOTSTRAP',
                prefix-item['score_prefix'], value)
        prefix += score
        if not winning:
            after = boards.get(step)
            checks['queue_semantics'] &= (after is not None and len(after) == 16
                and all(0 <= rank < 11 for rank in after))
            queue.append(dict(step=step, afterstate=after, score_prefix=prefix))
        if i == n-1 and status in ('WON', 'LOST'):
            category = 'WIN_BOUNDARY' if status == 'WON' else 'LOSS'
            tail = q['goal_bonus'] if status == 'WON' else -q['failure_penalty']
            while queue:
                item = queue.pop(0)
                consume(item, step, 'POST_TERMINAL', category, prefix-item['score_prefix'], tail)
    censored = len(queue) if status == 'CUTOFF' else 0
    if status == 'CUTOFF':
        checks['queue_semantics'] &= row.get('censored_queue', []) == queue
        queue = []
    checks['queue_semantics'] &= (cursor == len(records) and row['queue_after'] == queue
        and len(queue) <= horizon and row['censored_updates'] == censored)
    after = list(row['end_board']); last_cell = row['spawned_cells'][-1]
    checks['queue_semantics'] &= after[last_cell] == row['spawned_ranks'][-1]
    after[last_cell] = 0
    if status != 'WON': checks['queue_semantics'] &= boards.get(row['end_step']-1) == after
    updates = len(records); work, model = row['environment_counts'], row['model_counts']
    target_counts = Counter(queue_appends=n-int(status == 'WON'), queue_removals=updates,
        target_constructions=updates, censored_updates=censored)
    target_counts.update(u['type'].lower()+'_updates' for u in records)
    checks['training_counters'] &= (Counter(row['target_counts']) == target_counts
        and row['updates_after'] == row['updates_before']+updates
        and row['cumulative_updates'] == row['updates_after']
        and work.get('sampled_transitions') == n and work.get('initial_spawns', 0) == 2*first
        and work.get('environment_random_draws') == 2*n+4*first
        and work.get('ground_explicit_swipe_calls') == n
        and work.get('ground_state_status_calls') == n+first
        and work.get('ground_status_internal_swipe_calls') == 4*(n+first-int(status == 'WON'))
        and model.get('choose_calls') == model.get('inner_choose_calls') == n
        and model.get('td_updates', 0) == model.get('inner_td_updates', 0) == updates
        and model.get('inner_table_update_occurrences', 0) == 32*updates
        and updates <= model.get('inner_table_updates', 0) <= 32*updates
        and not any(v for k, v in model.items() if k.endswith('model_spawn_samples')))
    return {k: bool(v) for k, v in checks.items()}

def inspect_training(rows, life, query, kind, source):
    checks = dict(training_roster=True, training_seeds=True, checkpoint_boundaries=True)
    cost = dict(segments=0, episodes_started=0, episodes_completed=0, statuses=Counter(), censored_updates=0, target_counts=Counter(),
        environment_counts=Counter(), model_counts=Counter(), seconds=0.)
    previous, checkpoints = None, {}
    for row in rows:
        n = len(row['actions']); age = row['checkpoint']; cost['segments'] += 1
        checks['training_roster'] &= (row['life'], row['query'], row['kind']) == (life, query, kind)
        checks['training_seeds'] &= row['seed'] == training_seed(life, query, row['episode'])
        checks['checkpoint_boundaries'] &= age in CHECKPOINTS[1:] and row['cumulative_transitions'] <= age
        segment_result = (single.segment_checks(row, previous, query, 'PRIOR', source)
            if kind == 'SINGLE' else multi_segment_checks(row, previous, query, source))
        for key, value in segment_result.items():
            checks[key] = checks.get(key, True) and value
        if previous and age != previous['checkpoint']:
            checks['checkpoint_boundaries'] &= previous['cumulative_transitions'] == previous['checkpoint']
        cost['episodes_started'] += row['start_step'] == 0
        cost['episodes_completed'] += row['status'] != 'ACTIVE'
        cost['statuses'][row['status']] += 1
        cost['censored_updates'] += int(row['censored_last_update']) if kind == 'SINGLE' else row['censored_updates']
        if kind == 'MULTI': cost['target_counts'].update(row['target_counts'])
        cost['environment_counts'].update(row['environment_counts'])
        cost['model_counts'].update(row['model_counts']); cost['seconds'] += row['seconds']
        checks['training_roster'] &= row['cumulative_transitions'] == cost['environment_counts']['sampled_transitions']
        if row['cumulative_transitions'] == age:
            checkpoints[age] = dict(transitions=age, updates=row['updates_after'],
                stream_state=dict(transitions=age, episodes_started=cost['episodes_started'],
                    episodes_completed=cost['episodes_completed'], episode=row['episode'], step=row['end_step'],
                    board=row['end_board'], pending=row.get('pending_after'),
                    environment_counts=dict(cost['environment_counts'])))
        if row['cumulative_transitions'] == age and kind == 'MULTI':
            checkpoints[age]['stream_state'].update(queue=row['queue_after'], target_counts=dict(cost['target_counts']))
        previous = row
    checks['checkpoint_boundaries'] &= set(checkpoints) == set(CHECKPOINTS[1:])
    expected_updates = cost['environment_counts']['sampled_transitions']-cost['statuses']['WON']-cost['censored_updates']-(int(previous['pending_after'] is not None) if kind == 'SINGLE' else len(previous['queue_after']))
    checks['exact_training_budget'] = (cost['environment_counts']['sampled_transitions'] == CHECKPOINTS[-1]
        and previous is not None and previous['updates_after'] == expected_updates)
    checkpoints[0] = dict(transitions=0, updates=0, stream_state=dict(transitions=0, episodes_started=0,
        episodes_completed=0, episode=-1, step=0, board=None, pending=None, environment_counts={}))
    if kind == 'MULTI': checkpoints[0]['stream_state'].update(queue=[], target_counts={})
    return dict(checks={k: bool(v) for k, v in checks.items()}, cost=cost, checkpoints=checkpoints)


def model_state(source, query, kind, updates):
    if kind == 'PARENT': return dict(updates=source['models'][PARENTS[query]]['updates'], readonly=True)
    return dict(updates=updates, readonly=True, kind='PRIOR', offset=expected_offset(source, query))


def control_valid(row, source, updates):
    result = row['result']; kind = row['method']; n = result['steps']
    expected = model_state(source, row['query'], kind, updates)
    checks = dict(control_trace=old.compact_valid(row)
        and row['seed'] == outer_seed(row['life'], row['replica'])
        and result['utility'] == old.utility(result['score'], result['status'], row['query'])
        and len(row['chosen_values']) == n and all(math.isfinite(v) for v in row['chosen_values'])
        and result['policy_counts'].get('choose_calls') == n,
        evaluation_frozen=result['model_state_before'] == result['model_state_after'] == expected
        and not any(v for k, v in result['policy_counts'].items() if k.endswith(('td_updates', 'model_spawn_samples'))),
        exact_zero_learners=True)
    if kind == 'PARENT':
        zeros = row['zero_equivalence']
        checks['exact_zero_learners'] = set(zeros) == set(KINDS) and all(
            item['exact'] is True and item['before'] == item['after'] == model_state(source, row['query'], kind, 0)
            and item['counts'].get('choose_calls') == n
            and not any(v for k, v in item['counts'].items() if k.endswith(('td_updates', 'model_spawn_samples')))
            for kind, item in zeros.items())
    return checks


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen = (read(name) for name in ('run.json', 'source_capsule.json', 'frozen_training.json'))
    sources = {s['life']: s for s in capsule['snapshots']}
    settings = dict(lifecycles=list(LIVES), policies={p: old.QUERIES[p] for p in old.POLICIES},
        queries=QUERIES, parents=PARENTS, kinds=list(KINDS), checkpoints=list(CHECKPOINTS),
        transitions_per_learner=CHECKPOINTS[-1], replicas=REPLICAS, max_steps=MAX_STEPS,
        workers=4, alpha=RATE, p_four=.1, version_base=BASE, horizon=HORIZON, physical_control_games=896,
        logical_control_rows=1536)
    checks = dict(frozen_settings=run['settings'] == settings,
        source_roster=len(capsule['snapshots']) == 4 and set(sources) == set(LIVES),
        stage_rosters=all(len(run[k]) == 4 and {r['life'] for r in run[k]} == set(LIVES)
            for k in ('lifecycles', 'eval_lifecycles')),
        inherited_costs=run['inherited_costs'] == capsule['inherited_costs'],
        all_training_frozen_before_evaluation=frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
            and all(frozen[k] == run[k] for k in ('settings', 'lifecycles', 'inherited_costs')),
        learner_rosters=True, checkpoint_snapshots=True, source_immutable=True,
        initialization_accounting=True, model_loads=True, control_roster=True)
    costs = dict(training=dict(environment_counts=Counter(), model_counts=Counter(), seconds=0.,
        episodes_started=0, episodes_completed=0, segments=0, statuses=Counter(), censored_updates=0, target_counts=Counter()),
        control=old.new_cost(), zero_equivalence_counts={kind: Counter() for kind in KINDS}, model_accounting=[])
    learners, updates = [], {}
    for life_data in run['lifecycles']:
        life = life_data['life']; source = sources[life]
        checks['learner_rosters'] &= set(life_data['queries']) == set(QUERIES)
        for query, qdata in life_data['queries'].items():
            checks['learner_rosters'] &= set(qdata['learners']) == set(KINDS)
            checks['source_immutable'] &= qdata['parent_before'] == qdata['parent_after'] == model_state(source, query, 'PARENT', 0)
            checks['model_loads'] &= qdata['loads']['load_counts'].get('checkpoint_loads') == 1
            for kind, data in qdata['learners'].items():
                inspected = inspect_training(read_rows(directory/data['training_trace']), life, query, kind, source)
                for key, value in inspected['checks'].items(): checks[key] = checks.get(key, True) and value
                init, state = data['initialization'], model_state(source, query, kind, 0)
                state['readonly'] = False
                checks['initialization_accounting'] &= (init['state'] == state and init['counts'] == {}
                    and init['setup_counts'].get('allocated_weight_parameters') == 4*11**6
                    and init['setup_counts'].get('source_parameters_copied', 0) == 4*11**6
                    and init['setup_counts'].get('source_weight_bytes_copied', 0) == 8*4*11**6)
                ages = [c['age'] for c in data['checkpoints']]
                checks['checkpoint_snapshots'] &= ages == list(CHECKPOINTS)
                saved_counts = Counter()
                for checkpoint in data['checkpoints']:
                    age = checkpoint['age']; meta = checkpoint['metadata']; expected = inspected['checkpoints'][age]
                    updates[(life, query, kind, age)] = expected['updates']
                    checks['checkpoint_snapshots'] &= (all(checkpoint[k] == expected[k] for k in ('transitions', 'updates', 'stream_state'))
                        and meta['updates'] == expected['updates'] and meta['parameter_count'] == 4*11**6
                        and checkpoint['save_counts'].get('checkpoint_saves') == 1
                        and checkpoint['save_counts'].get('inner_checkpoint_saves') == 1
                        and checkpoint['save_counts'].get('inner_checkpoint_scanned_parameters') == 4*11**6)
                    sidecar = read(checkpoint['model_ref']+'.query.json')
                    checks['checkpoint_snapshots'] &= (sidecar['kind'] == 'PRIOR' and sidecar['updates'] == expected['updates']
                        and sidecar['target_query'] == QUERIES[query] and sidecar['offset'] == expected_offset(source, query)
                        and sidecar['source_updates'] == source['models'][PARENTS[query]]['updates'])
                    saved_counts.update(checkpoint['save_counts'])
                final = inspected['checkpoints'][CHECKPOINTS[-1]]
                checks['checkpoint_snapshots'] &= (data['final_stream_state'] == final['stream_state']
                    and data['final_state'] == model_state(source, query, kind, final['updates'])
                    and Counter(data['final_counts']) == inspected['cost']['model_counts']+saved_counts)
                learners.append(dict(life=life, query=query, kind=kind, checks=inspected['checks'],
                    cost=inspected['cost'], final_stream_state=data['final_stream_state'],
                    updates=final['updates']))
                for name in ('environment_counts', 'model_counts', 'statuses', 'target_counts'):
                    costs['training'][name].update(inspected['cost'][name])
                for name in ('seconds', 'episodes_started', 'episodes_completed', 'segments', 'censored_updates'):
                    costs['training'][name] += inspected['cost'][name]
                costs['model_accounting'].append(dict(phase='training', life=life, query=query, kind=kind,
                    initialization=init, checkpoints=data['checkpoints'], final_counts=data['final_counts']))
            costs['model_accounting'].append(dict(phase='training_source_load', life=life, query=query, loads=qdata['loads']))
    indexed, valid = {}, {}
    for life_data in run['eval_lifecycles']:
        life = life_data['life']; source = sources[life]
        rows = list(read_rows(directory/life_data['control_trace']))
        keys = [(r['life'], r['query'], r['method'], r['checkpoint'], r['replica']) for r in rows]
        expected = {(life, q, kind, age, replica) for q in QUERIES for kind in KINDS for age in CHECKPOINTS
            for replica in range(REPLICAS) if age != 0}
        expected.update((life, q, 'PARENT', 0, replica) for q in QUERIES for replica in range(REPLICAS))
        checks['control_roster'] &= len(keys) == len(set(keys)) == 224 and set(keys) == expected
        for key, row in zip(keys, rows):
            _, query, kind, age, replica = key
            row_checks = control_valid(row, source, updates.get((life, query, kind, age), 0))
            for name, value in row_checks.items(): checks[name] = checks.get(name, True) and value
            indexed[key] = row; valid[key] = all(row_checks.values()); old.add_cost(costs['control'], row)
            if kind == 'PARENT':
                for method, item in row['zero_equivalence'].items():
                    costs['zero_equivalence_counts'][method].update(item['counts'])
                aliases = [(life, query, 'PARENT', c, replica) for c in CHECKPOINTS]
                aliases.extend((life, query, method, 0, replica) for method in KINDS)
                for alias in aliases: indexed[alias] = row; valid[alias] = valid[key]
        for query, qdata in life_data['queries'].items():
            checks['source_immutable'] &= qdata['parent_before'] == qdata['parent_after'] == model_state(source, query, 'PARENT', 0)
            loads = qdata['checkpoint_loads']
            checks['model_loads'] &= (len(loads) == 8 and {(r['kind'], r['age']) for r in loads} == {(k, a) for k in KINDS for a in CHECKPOINTS}
                and qdata['loads']['load_counts'].get('checkpoint_loads') == 1)
            for row in loads:
                kind, age = row['kind'], row['age']
                checks['model_loads'] &= row['load_counts'].get('checkpoint_loads') == 1 and row['state'] == model_state(source, query, kind, updates[(life, query, kind, age)])
            costs['model_accounting'].append(dict(phase='evaluation', life=life, query=query, **qdata))
    checks['physical_and_logical_rosters'] = costs['control']['games'] == 896 and len(indexed) == 1536
    checks['equal_real_training_budgets'] = costs['training']['environment_counts']['sampled_transitions'] == 8388608
    costs['new_environment_samples'] = costs['training']['environment_counts']['sampled_transitions']+costs['control']['environment_counts']['sampled_transitions']
    costs['new_model_samples'] = sum(v for data in costs['model_accounting'] for k, v in data.get('final_counts', {}).items() if k.endswith('model_spawn_samples'))
    checks['no_model_samples'] = costs['new_model_samples'] == 0
    control = full_game_curve(indexed, valid)
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.multistep_query_td.v133.analysis', complete=complete,
        primary_complete=complete and all(v['complete'] for group in control['primary']['methods'].values() for v in group.values()),
        checks={k: bool(v) for k, v in checks.items()}, learners=learners, control=control,
        costs=costs, inherited_work=run['inherited_costs'], required_inputs=capsule['required_inputs'],
        seconds=run['seconds'], analysis_seconds=perf_counter()-started,
        scope='Read retained numeric identities, contiguous episode segments, fixed budgets and frozen control traces; no trajectory resampling or weight replay. Every multi-step queue event and target is reconciled independently from retained integer score prefixes; numerical weight replay is not performed. Curves reuse parent and exact zero trajectories for both learners with physical work charged once; final checkpoint is primary.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_multistep_query_td_v133')
    args = parser.parse_args(); result = analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))
