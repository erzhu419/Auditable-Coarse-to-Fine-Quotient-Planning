"""Independently reconcile one-step TD with global and local context conditioning."""
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

LIVES, KINDS, METHODS = tuple(range(4)), ('SINGLE', 'GLOBAL', 'CAPACITY'), ('PARENT', 'SINGLE', 'GLOBAL', 'CAPACITY')
QUERIES = {q: old.QUERIES[q] for q in ('risk1', 'risk8')}
PARENTS = dict(risk1='reward', risk8='risk_goal')
CHECKPOINTS, REPLICAS = (0, 32768, 131072, 524288), 16
BASE, MAX_STEPS, RATE = 134*100000000, 2000, .0025
CONTEXT_SPEC = dict(global_empty_threshold=4, capacity_extra_cells=[3, 7, 6, 10])
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
        for other in ('CAPACITY', 'SINGLE', 'PARENT'):
            name = 'GLOBAL_minus_'+other; comparisons[name] = {}
            for query in QUERIES:
                lives = []
                for life in LIVES:
                    complete = (methods['GLOBAL'][query]['lifecycles'][life]['complete']
                        and methods[other][query]['lifecycles'][life]['complete'])
                    item = dict(life=life, complete=complete)
                    if complete:
                        deltas = [indexed[(life, query, 'GLOBAL', checkpoint, i)]['result']['utility']-
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


def parameter_count(kind):
    return 4*11**6*(2 if kind in ('GLOBAL', 'CAPACITY') else 1)


def context_counts_valid(counts, kind):
    """Both contexts retain 32 occurrences, with their actual work charged."""
    if kind not in ('GLOBAL', 'CAPACITY'): return True
    value = lambda name: counts.get('inner_'+name, 0)
    predictions, updates = value('value_predictions'), value('td_updates')
    reads, selections = (16, 1) if kind == 'GLOBAL' else (32, 32)
    return (value('bank_0_prediction_occurrences')+value('bank_1_prediction_occurrences') == 32*(predictions-updates)
        and value('bank_0_update_occurrences')+value('bank_1_update_occurrences') == 32*updates
        and value('bank_0_unique_updates')+value('bank_1_unique_updates') == value('table_updates')
        and value('context_cell_reads') == reads*predictions
        and value('context_bank_selections') == selections*predictions
        and value('context_bank_offset_additions') == 32*predictions
        and 32*updates <= value('update_feature_squared_norm') <= 256*updates)


def context_diagnostic(counts):
    updates = counts.get('inner_td_updates', 0)
    return dict(updates=updates,
        mean_feature_squared_norm=None if not updates else counts.get('inner_update_feature_squared_norm', 0)/updates,
        mean_unique_updated_parameters=None if not updates else counts.get('inner_table_updates', 0)/updates,
        bank_prediction_occurrences=[counts.get(f'inner_bank_{bank}_prediction_occurrences', 0) for bank in (0, 1)],
        bank_update_occurrences=[counts.get(f'inner_bank_{bank}_update_occurrences', 0) for bank in (0, 1)],
        context_cell_reads=counts.get('inner_context_cell_reads', 0),
        context_bank_selections=counts.get('inner_context_bank_selections', 0))


def expected_offset(source, query, kind):
    q, p = QUERIES[query], old.QUERIES[PARENTS[query]]
    constant = source['counts'][PARENTS[query]]['constant']
    return (p['failure_penalty']-q['failure_penalty'])+(
        q['failure_penalty']+q['goal_bonus']-p['failure_penalty']-p['goal_bonus'])*constant


def training_seed(life, query, episode):
    return BASE+10000000+life*1000000+list(QUERIES).index(query)*500000+episode


def outer_seed(life, replica):
    return BASE+90000000+life*100000+replica


def board_status(board):
    if max(board) >= 11: return 'WON'
    if 0 in board or any(board[i] == board[j] for i in range(16)
            for j in (i+1, i+4) if j < 16 and (j == i+4 or i//4 == j//4)):
        return 'ACTIVE'
    return 'LOST'


def segment_checks(row, previous, query, kind, source):
    """Read retained numeric identities, never resample or refit the trajectory."""
    n, status = len(row['actions']), row['status']; q = QUERIES[query]
    first = row['start_step'] == 0
    offset = expected_offset(source, query, kind)
    src = old.QUERIES[PARENTS[query]]
    failure = src['failure_penalty']-q['failure_penalty']
    success = ((q['failure_penalty']+q['goal_bonus'])-(src['failure_penalty']+src['goal_bonus']))*source['counts'][PARENTS[query]]['constant']
    targets, raw_targets, errors = row['td_targets'], row['raw_td_targets'], row['td_errors']
    arrays = ('scores', 'spawned_cells', 'spawned_ranks', 'chosen_values',
        'chosen_raw_values', 'td_targets', 'raw_td_targets', 'td_errors')
    checks = dict(segment_shape=0 < n and all(len(row[k]) == n for k in arrays)
        and row['end_step']-row['start_step'] == n and row['end_step'] <= MAX_STEPS
        and all(a in ('DOWN', 'LEFT', 'RIGHT', 'UP') for a in row['actions'])
        and all(0 <= c < 16 for c in row['spawned_cells'])
        and all(r in (1, 2) for r in row['spawned_ranks']),
        segment_terminal=status in ('ACTIVE', 'WON', 'LOST', 'CUTOFF')
        and board_status(row['end_board']) == ('ACTIVE' if status == 'CUTOFF' else status)
        and (status != 'CUTOFF' or row['end_step'] == MAX_STEPS)
        and row['budget_status'] == ('BUDGET_END' if status == 'ACTIVE' else 'EPISODE_END')
        and row['censored_last_update'] == (status == 'CUTOFF'),
        segment_continuity=True, initial_spawns=True, td_targets=True,
        pending_semantics=True, training_counters=True)
    if not checks['segment_shape']: return {k: False for k in checks}
    if first:
        spawns = row.get('initial_spawns', []); board = [0]*16
        for spawn in spawns:
            board[spawn['cell']] = spawn['rank']
        checks['initial_spawns'] &= (len(spawns) == 2 and len({s['cell'] for s in spawns}) == 2
            and board == row['start_board'] and row['pending_before'] is None)
    else:
        checks['initial_spawns'] &= 'initial_spawns' not in row and row['pending_before'] is not None
    if previous is None:
        checks['segment_continuity'] &= row['episode'] == 0 and first and row['updates_before'] == 0
    else:
        same = previous['status'] == 'ACTIVE'
        checks['segment_continuity'] &= (row['updates_before'] == previous['updates_after']
            and row['cumulative_transitions'] == previous['cumulative_transitions']+n
            and row['episode'] == previous['episode']+int(not same)
            and (not same or (row['seed'] == previous['seed'] and row['start_step'] == previous['end_step']
                and row['start_board'] == previous['end_board'] and row['pending_before'] == previous['pending_after']))
            and (same or first))
    start_return = 0 if first else previous['return_score']
    checks['segment_continuity'] &= row['return_score'] == start_return+sum(row['scores'])
    checks['td_targets'] &= all((t is None and r is None and e is None) if i == 0 and first else
        (t is not None and r is not None and e is not None and t == row['chosen_values'][i]
            and r == t-offset and all(math.isfinite(v) for v in (t, r, e)))
        for i, (t, r, e) in enumerate(zip(targets, raw_targets, errors)))
    for i, (value, raw) in enumerate(zip(row['chosen_values'], row['chosen_raw_values'])):
        winning = status == 'WON' and i == n-1
        expected = row['scores'][i]/2048.+q['goal_bonus'] if winning else raw+failure+success
        checks['td_targets'] &= math.isfinite(value) and math.isfinite(raw) and value == expected
    terminal = row['terminal_update']
    checks['td_targets'] &= (terminal is None) if status != 'LOST' else (terminal is not None
        and terminal['target'] == -q['failure_penalty'] and terminal['raw_target'] == -q['failure_penalty']-offset
        and math.isfinite(terminal['error']) and terminal['work'].get('td_updates') == 1)
    after = list(row['end_board']); last_cell = row['spawned_cells'][-1]
    checks['pending_semantics'] &= after[last_cell] == row['spawned_ranks'][-1]
    after[last_cell] = 0
    checks['pending_semantics'] &= row['pending_after'] == (after if status == 'ACTIVE' else None)
    if terminal is not None:
        checks['pending_semantics'] &= terminal['afterstate'] == after
    updates = sum(t is not None for t in targets)+int(terminal is not None)
    work, model = row['environment_counts'], row['model_counts']
    checks['training_counters'] &= (row['updates_after'] == row['updates_before']+updates
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
    checks['conditioning_counts'] = context_counts_valid(model, kind)
    return {k: bool(v) for k, v in checks.items()}


def inspect_training(rows, life, query, kind, source):
    checks = dict(training_roster=True, training_seeds=True, checkpoint_boundaries=True)
    cost = dict(segments=0, episodes_started=0, episodes_completed=0, statuses=Counter(),
        environment_counts=Counter(), model_counts=Counter(), seconds=0.)
    previous, checkpoints = None, {}
    for row in rows:
        n = len(row['actions']); age = row['checkpoint']; cost['segments'] += 1
        checks['training_roster'] &= (row['life'], row['query'], row['kind']) == (life, query, kind)
        checks['training_seeds'] &= row['seed'] == training_seed(life, query, row['episode'])
        checks['checkpoint_boundaries'] &= age in CHECKPOINTS[1:] and row['cumulative_transitions'] <= age
        for key, value in segment_checks(row, previous, query, kind, source).items():
            checks[key] = checks.get(key, True) and value
        if previous and age != previous['checkpoint']:
            checks['checkpoint_boundaries'] &= previous['cumulative_transitions'] == previous['checkpoint']
        cost['episodes_started'] += row['start_step'] == 0
        cost['episodes_completed'] += row['status'] != 'ACTIVE'
        cost['statuses'][row['status']] += 1
        cost['environment_counts'].update(row['environment_counts'])
        cost['model_counts'].update(row['model_counts']); cost['seconds'] += row['seconds']
        checks['training_roster'] &= row['cumulative_transitions'] == cost['environment_counts']['sampled_transitions']
        if row['cumulative_transitions'] == age:
            checkpoints[age] = dict(transitions=age, updates=row['updates_after'],
                stream_state=dict(transitions=age, episodes_started=cost['episodes_started'],
                    episodes_completed=cost['episodes_completed'], episode=row['episode'], step=row['end_step'],
                    board=row['end_board'], pending=row['pending_after'],
                    environment_counts=dict(cost['environment_counts'])))
        previous = row
    checks['checkpoint_boundaries'] &= set(checkpoints) == set(CHECKPOINTS[1:])
    expected_updates = cost['environment_counts']['sampled_transitions']-cost['statuses']['WON']-cost['statuses']['CUTOFF']-int(previous is not None and previous['pending_after'] is not None)
    checks['exact_training_budget'] = (cost['environment_counts']['sampled_transitions'] == CHECKPOINTS[-1]
        and previous is not None and previous['updates_after'] == expected_updates)
    checkpoints[0] = dict(transitions=0, updates=0, stream_state=dict(transitions=0, episodes_started=0,
        episodes_completed=0, episode=-1, step=0, board=None, pending=None, environment_counts={}))
    return dict(checks={k: bool(v) for k, v in checks.items()}, cost=cost, checkpoints=checkpoints)


def model_state(source, query, kind, updates):
    if kind == 'PARENT': return dict(updates=source['models'][PARENTS[query]]['updates'], readonly=True)
    result = dict(updates=updates, readonly=True, kind='PRIOR', offset=expected_offset(source, query, kind))
    if kind != 'SINGLE': result['representation'] = kind
    return result


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
        exact_zero_learners=True, conditioning_counts=context_counts_valid(result['policy_counts'], kind))
    if kind == 'PARENT':
        zeros = row['zero_equivalence']
        checks['exact_zero_learners'] = set(zeros) == set(KINDS) and all(
            item['exact'] is True and item['before'] == item['after'] == model_state(source, row['query'], method, 0)
            and item['counts'].get('choose_calls') == n
            and context_counts_valid(item['counts'], method)
            and not any(v for k, v in item['counts'].items() if k.endswith(('td_updates', 'model_spawn_samples')))
            for method, item in zeros.items())
    return checks


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen = (read(name) for name in ('run.json', 'source_capsule.json', 'frozen_training.json'))
    sources = {s['life']: s for s in capsule['snapshots']}
    settings = dict(lifecycles=list(LIVES), policies={p: old.QUERIES[p] for p in old.POLICIES},
        queries=QUERIES, parents=PARENTS, kinds=list(KINDS), checkpoints=list(CHECKPOINTS),
        transitions_per_learner=CHECKPOINTS[-1], replicas=REPLICAS, max_steps=MAX_STEPS,
        workers=4, alpha=RATE, p_four=.1, version_base=BASE, empty_threshold=4, extra_cells=[3, 7, 6, 10], physical_control_games=1280,
        logical_control_rows=2048)
    checks = dict(frozen_settings=run['settings'] == settings,
        source_roster=len(capsule['snapshots']) == 4 and set(sources) == set(LIVES),
        stage_rosters=all(len(run[k]) == 4 and {r['life'] for r in run[k]} == set(LIVES)
            for k in ('lifecycles', 'eval_lifecycles')),
        inherited_costs=run['inherited_costs'] == capsule['inherited_costs'],
        all_training_frozen_before_evaluation=frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
            and all(frozen[k] == run[k] for k in ('settings', 'lifecycles', 'inherited_costs')),
        learner_rosters=True, checkpoint_snapshots=True, source_immutable=True,
        initialization_accounting=True, model_loads=True, control_roster=True, conditional_metadata=True)
    costs = dict(training=dict(environment_counts=Counter(), model_counts=Counter(), seconds=0.,
        episodes_started=0, episodes_completed=0, segments=0, statuses=Counter()),
        control=old.new_cost(), zero_equivalence_counts={method: Counter() for method in KINDS}, model_accounting=[])
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
                    and init['setup_counts'].get('allocated_weight_parameters') == parameter_count(kind)
                    and init['setup_counts'].get('source_parameters_copied', 0) == parameter_count(kind)
                    and init['setup_counts'].get('source_weight_bytes_copied', 0) == 8*parameter_count(kind))
                ages = [c['age'] for c in data['checkpoints']]
                checks['checkpoint_snapshots'] &= ages == list(CHECKPOINTS)
                saved_counts = Counter()
                for checkpoint in data['checkpoints']:
                    age = checkpoint['age']; meta = checkpoint['metadata']; expected = inspected['checkpoints'][age]
                    updates[(life, query, kind, age)] = expected['updates']
                    checks['checkpoint_snapshots'] &= (all(checkpoint[k] == expected[k] for k in ('transitions', 'updates', 'stream_state'))
                        and meta['updates'] == expected['updates'] and meta['parameter_count'] == parameter_count(kind)
                        and checkpoint['save_counts'].get('checkpoint_saves') == 1
                        and checkpoint['save_counts'].get('inner_checkpoint_saves') == 1
                        and checkpoint['save_counts'].get('inner_checkpoint_scanned_parameters') == parameter_count(kind))
                    sidecar = read(checkpoint['model_ref']+'.query.json')
                    checks['checkpoint_snapshots'] &= (sidecar['kind'] == 'PRIOR' and sidecar['updates'] == expected['updates']
                        and sidecar['target_query'] == QUERIES[query] and sidecar['offset'] == expected_offset(source, query, kind)
                        and sidecar['source_updates'] == source['models'][PARENTS[query]]['updates'])
                    if kind != 'SINGLE':
                        checks['conditional_metadata'] &= (sidecar['schema'] == 'acfqp.contextual_query_td.v134'
                            and sidecar['representation'] == kind and sidecar['context_spec'] == CONTEXT_SPEC)
                    saved_counts.update(checkpoint['save_counts'])
                final = inspected['checkpoints'][CHECKPOINTS[-1]]
                checks['checkpoint_snapshots'] &= (data['final_stream_state'] == final['stream_state']
                    and data['final_state'] == model_state(source, query, kind, final['updates'])
                    and Counter(data['final_counts']) == inspected['cost']['model_counts']+saved_counts)
                learners.append(dict(life=life, query=query, kind=kind, checks=inspected['checks'],
                    cost=inspected['cost'], final_stream_state=data['final_stream_state'],
                    updates=final['updates']))
                for name in ('environment_counts', 'model_counts', 'statuses'):
                    costs['training'][name].update(inspected['cost'][name])
                for name in ('seconds', 'episodes_started', 'episodes_completed', 'segments'):
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
        checks['control_roster'] &= len(keys) == len(set(keys)) == 320 and set(keys) == expected
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
            checks['model_loads'] &= (len(loads) == 12 and {(r['kind'], r['age']) for r in loads} == {(k, a) for k in KINDS for a in CHECKPOINTS}
                and qdata['loads']['load_counts'].get('checkpoint_loads') == 1)
            for row in loads:
                kind, age = row['kind'], row['age']
                checks['model_loads'] &= row['load_counts'].get('checkpoint_loads') == 1 and row['state'] == model_state(source, query, kind, updates[(life, query, kind, age)])
            costs['model_accounting'].append(dict(phase='evaluation', life=life, query=query, **qdata))
    checks['physical_and_logical_rosters'] = costs['control']['games'] == 1280 and len(indexed) == 2048
    checks['equal_real_training_budgets'] = costs['training']['environment_counts']['sampled_transitions'] == 12582912
    costs['new_environment_samples'] = costs['training']['environment_counts']['sampled_transitions']+costs['control']['environment_counts']['sampled_transitions']
    costs['new_model_samples'] = sum(v for data in costs['model_accounting'] for k, v in data.get('final_counts', {}).items() if k.endswith('model_spawn_samples'))
    checks['no_model_samples'] = costs['new_model_samples'] == 0
    control = full_game_curve(indexed, valid)
    conditioning = {kind: dict(parameter_count=parameter_count(kind),
        training=context_diagnostic(sum((Counter(r['cost']['model_counts']) for r in learners if r['kind'] == kind), Counter())),
        histories=[dict(life=r['life'], query=r['query'], **context_diagnostic(r['cost']['model_counts']))
            for r in learners if r['kind'] == kind]) for kind in ('GLOBAL', 'CAPACITY')}
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.contextual_ntuple.v134.analysis', complete=complete,
        primary_complete=complete and all(v['complete'] for group in control['primary']['methods'].values() for v in group.values()),
        checks={k: bool(v) for k, v in checks.items()}, learners=learners, control=control,
        costs=costs, conditioning=conditioning, inherited_work=run['inherited_costs'], required_inputs=capsule['required_inputs'],
        seconds=run['seconds'], analysis_seconds=perf_counter()-started,
        scope='Read retained numeric identities, contiguous episode segments, fixed budgets and frozen control traces; no trajectory resampling or weight replay. Global and local context conditioning match nominal parameter counts and active occurrences, while duplicate-address multiplicities and effective update size can differ; observed feature norms are reported. Curves reuse parent and three exact zero trajectories with physical work charged once; final checkpoint is primary.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_contextual_ntuple_v134')
    args = parser.parse_args(); result = analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))
