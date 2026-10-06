"""Independent paired-action learning and frozen-policy evaluation analysis."""
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
from scripts import analyze_controlled_predictive_forced_actions_v128 as paired
from acfqp.domains import standard_2048 as ground

LIVES, QUERIES = old.LIVES, paired.QUERIES
METHODS = ('PARENT', 'PRIOR', 'SCRATCH')
PARENTS = {'risk1': 'reward', 'risk8': 'risk_goal'}
INDICES, DRAW_COUNT, OUTER_COUNT = (128, 256, 512, 768), 8, 16
BASE, MAX_STEPS = 130*100000000, 2000
read_rows, mean, paired_summary = old.read_rows, old.mean, paired.paired_summary


def sign(value):
    return int(value > 0)-int(value < 0)


def gap_statistics(predictions, labels):
    """Compare fixed predicted gaps with eight paired outcomes per action.

    Half-sample comparisons expose label noise; they are not a model test set.
    The parent action (identically zero gap) is excluded by the caller.
    """
    labels = np.asarray(labels, dtype=float)
    predictions = np.asarray(predictions, dtype=float)
    if not len(predictions):
        return dict(action_pairs=0, rmse=None, sign_agreement=None,
            half_label_rmse=None, half_label_sign_agreement=None)
    targets = labels.mean(axis=1)
    first, second = labels[:, :4].mean(axis=1), labels[:, 4:].mean(axis=1)
    return dict(action_pairs=len(predictions), rmse=float(np.sqrt(np.mean((predictions-targets)**2))),
        sign_agreement=sum(sign(float(a)) == sign(float(b)) for a, b in zip(predictions, targets)),
        half_label_rmse=float(np.sqrt(np.mean((first-second)**2))),
        half_label_sign_agreement=sum(sign(float(a)) == sign(float(b)) for a, b in zip(first, second)),
        mean_predicted_gap=float(predictions.mean()), mean_sample_gap=float(targets.mean()))


def heldout_differences(parent, first_only, full_update):
    p, f, u = (np.asarray(v, dtype=float) for v in (parent, first_only, full_update))
    values = dict(parent=p, first_only=f, full_update=u,
        first_only_minus_parent=f-p, full_update_minus_first_only=u-f,
        full_update_minus_parent=u-p)
    return dict(replica_values={k: v.tolist() for k, v in values.items()},
        paired={k: paired_summary(v) for k, v in values.items()})


def aggregate_heldout(cases):
    """Preserve missing slots and average roots within life, then lives equally."""
    lifecycles, overall = [], {}
    for query in QUERIES:
        for life in LIVES:
            slots = [r for r in cases if r['life'] == life and r['query'] == query]
            available = [r for r in slots if r['available']]
            ready = len(slots) == 16 and bool(available) and all(r['complete'] for r in available)
            item = dict(life=life, query=query, slots=len(slots), available=len(available),
                missing=len(slots)-len(available), complete=ready)
            if ready:
                values = {k: np.mean([r['replica_values'][k] for r in available], axis=0)
                    for k in available[0]['replica_values']}
                item.update(replica_values={k: v.tolist() for k, v in values.items()},
                    paired={k: paired_summary(v) for k, v in values.items()})
            lifecycles.append(item)
        members = [r for r in lifecycles if r['query'] == query]
        overall[query] = dict(complete=all(r['complete'] for r in members))
        if overall[query]['complete']:
            values = {k: np.mean([r['replica_values'][k] for r in members], axis=0)
                for k in members[0]['replica_values']}
            overall[query]['paired'] = {k: paired_summary(v) for k, v in values.items()}
    return dict(lifecycles=lifecycles, four_life_means=overall)


def full_game_summary(indexed, valid):
    methods, comparisons = {}, {}
    for method in METHODS:
        methods[method] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                keys = [(life, query, method, i) for i in range(OUTER_COUNT)]
                rows = [indexed[k] for k in keys if k in indexed]
                ready = all(k in indexed and valid.get(k, False)
                    and indexed[k]['result']['status'] in ('WON', 'LOST') for k in keys)
                result = dict(life=life, complete=ready, games=len(rows),
                    statuses=dict(Counter(r['result']['status'] for r in rows)),
                    wins=sum(r['result']['status'] == 'WON' for r in rows),
                    means={k: mean(r['result'][k] for r in rows) if ready else None
                        for k in ('utility', 'score', 'steps')})
                lives.append(result)
            methods[method][query] = dict(lifecycles=lives,
                complete=all(r['complete'] for r in lives),
                means={k: mean(r['means'][k] for r in lives) for k in ('utility', 'score', 'steps')})
    for other in ('PARENT', 'SCRATCH'):
        name = 'PRIOR_minus_'+other
        comparisons[name] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                ready = (methods['PRIOR'][query]['lifecycles'][life]['complete']
                    and methods[other][query]['lifecycles'][life]['complete'])
                item = dict(life=life, complete=ready)
                if ready:
                    deltas = [indexed[(life, query, 'PRIOR', i)]['result']['utility']-
                        indexed[(life, query, other, i)]['result']['utility'] for i in range(OUTER_COUNT)]
                    item.update(mean=float(np.mean(deltas)), replica_deltas=deltas)
                lives.append(item)
            ready = all(r['complete'] for r in lives)
            comparisons[name][query] = dict(lifecycles=lives, complete=ready,
                mean=mean(r.get('mean') for r in lives),
                positive=sum(r.get('mean', 0) > 0 for r in lives),
                negative=sum(r.get('mean', 0) < 0 for r in lives))
    return dict(methods=methods, comparisons=comparisons)


def prefix_boards(row):
    """Independently bind retained pre-action slots, without sampling outcomes."""
    result = {i: None for i in INDICES}; board = tuple(row['initial_board'])
    eligible = [i for i in INDICES if i < row['result']['steps']]
    swipes, okay = 0, True
    for step in range(max(eligible, default=-1)+1):
        if step in result:
            result[step] = list(board)
        if step == max(eligible):
            break
        after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(row['actions'][step]))
        cell, rank = row['spawned_cells'][step], row['spawned_ranks'][step]
        okay &= changed and score == row['scores'][step] and after[cell] == 0
        after = list(after); after[cell] = rank; board = tuple(after); swipes += 1
    return result, okay, swipes


def source_seed(life, episode):
    return BASE+10000000+life*100000+episode


def suffix_seed(root, replica):
    return BASE+50000000+root*1000+replica


def outer_seed(life, replica):
    return BASE+90000000+life*100000+replica


def model_state(source, query, method, updates=0):
    source_updates = source['models'][PARENTS[query]]['updates']
    return dict(updates=source_updates if method == 'PARENT' else updates,
        source_updates=source_updates, source_readonly=True,
        residual_readonly=None if method == 'PARENT' else True)


def scratch_value(row, query):
    return row['score']/2048.+(QUERIES[query]['goal_bonus'] if max(row['afterstate']) >= 11 else 0.)


def parent_prediction_valid(root, source):
    q = QUERIES[root['query']]; policy = PARENTS[root['query']]
    src = old.QUERIES[policy]; probability = source['counts'][policy]['constant']
    legal = {}
    for action in ('DOWN', 'LEFT', 'RIGHT', 'UP'):
        after, score, changed = ground.swipe_board_v1(tuple(root['board']), ground.Swipe2048Action(action))
        if changed: legal[action] = (list(after), score)
    rows = root['parent']['action_values']
    okay = set(rows) == set(legal) and root['actions'] == sorted(legal)
    for action, row in rows.items():
        goal = max(row['afterstate']) >= 11
        expected = scratch_value(row, root['query']) if goal else row['anchor_value']+(
            src['failure_penalty']-q['failure_penalty'])+(
            q['failure_penalty']+q['goal_bonus']-src['failure_penalty']-src['goal_bonus'])*probability
        okay &= (legal.get(action) == (row['afterstate'], row['score'])
            and row['success_probability'] == (1. if goal else probability)
            and math.isfinite(row['anchor_value']) and row['value'] == expected)
    return bool(okay and root['parent']['action'] == min(rows, key=lambda a: (-rows[a]['value'], a)))


def frozen_prediction_valid(root, frozen):
    okay = (frozen['root_id'] == root['root_id'] and frozen['query'] == root['query']
        and frozen['split'] == root['split'] and set(frozen['methods']) == set(METHODS)
        and frozen['methods']['PARENT'] == root['parent'])
    for method in ('PRIOR', 'SCRATCH'):
        pred = frozen['methods'][method]; values = pred['action_values']
        okay &= set(values) == set(root['actions'])
        for action, row in values.items():
            parent = root['parent']['action_values'][action]
            base = parent['value'] if method == 'PRIOR' else scratch_value(parent, root['query'])
            okay &= (row['afterstate'] == parent['afterstate'] and row['score'] == parent['score']
                and row['base_value'] == base and row['value'] == base+row['residual']
                and math.isfinite(row['residual']) and (max(row['afterstate']) < 11 or row['residual'] == 0.))
        okay &= pred['action'] == min(values, key=lambda a: (-values[a]['value'], a))
    return bool(okay)


def game_valid(row, expected_state, root=None):
    r = row['result']; n = r['steps']; work = r['environment_counts']; forced = root is not None
    okay = (r['model_state_before'] == r['model_state_after'] == expected_state
        and r['utility'] == old.utility(r['score'], r['status'], row['query'])
        and r['components'] == old.components(r['score'], r['status'])
        and r['policy_counts'].get('choose_calls', 0) == n-int(forced)
        and not any(v for k, v in r['policy_counts'].items()
            if k.endswith(('td_updates', 'pair_updates', 'model_spawn_samples'))))
    if forced:
        okay &= (0 < n <= MAX_STEPS and r['status'] in ('WON', 'LOST', 'CUTOFF')
            and (r['status'] != 'CUTOFF' or n == MAX_STEPS)
            and all(len(row[k]) == n for k in ('actions', 'scores', 'spawned_cells', 'spawned_ranks'))
            and sum(row['scores']) == r['score'] and row['initial_board'] == root['board']
            and row['initial_spawns'] == [] and row['actions'][0] == row['forced_action']
            and row['scores'][0] == root['parent']['action_values'][row['forced_action']]['score']
            and all(a in ('DOWN', 'LEFT', 'RIGHT', 'UP') for a in row['actions'])
            and all(0 <= c < 16 for c in row['spawned_cells'])
            and all(v in (1, 2) for v in row['spawned_ranks'])
            and (max(row['final_board']) >= 11) == (r['status'] == 'WON')
            and work.get('sampled_transitions') == n and work.get('initial_spawns', 0) == 0
            and work.get('environment_random_draws') == 2*n and work.get('ground_explicit_swipe_calls') == n
            and work.get('forced_actions') == 1 and row['split'] == root['split']
            and row['query'] == root['query'] and row['life'] == root['life']
            and row['seed'] == suffix_seed(root['root_id'], row['replica']))
    else:
        okay &= old.compact_valid(row)
        seed = source_seed(row['life'], row['replica']) if row['method'] == 'ACQUISITION' else outer_seed(row['life'], row['replica'])
        okay &= row['seed'] == seed and all(len(row[k]) == n for k in ('chosen_values', 'base_values', 'residual_values'))
        okay &= all(math.isfinite(v) and v == b+d for v, b, d in
            zip(row['chosen_values'], row['base_values'], row['residual_values']))
    return bool(okay)


def pair_labels(root, indexed, valid):
    labels = []
    ref = root['parent']['action']; values = root['parent']['action_values']
    for action in root['actions']:
        if action == ref: continue
        keys = [(root['root_id'], a, 'PARENT', i) for a in (action, ref) for i in range(DRAW_COUNT)]
        ready = all(k in indexed and valid.get(k, False) and indexed[k]['result']['status'] in ('WON', 'LOST') for k in keys)
        gaps = [indexed[(root['root_id'], action, 'PARENT', i)]['result']['utility']-
            indexed[(root['root_id'], ref, 'PARENT', i)]['result']['utility'] for i in range(DRAW_COUNT)] if all(k in indexed for k in keys) else []
        labels.append(dict(root_id=root['root_id'], life=root['life'], query=root['query'],
            reference_action=ref, action=action, afterstate=values[action]['afterstate'],
            reference_afterstate=values[ref]['afterstate'], eligible=ready, paired_gaps=gaps,
            target_gap=sum(gaps)/len(gaps) if ready else None,
            base_gaps=dict(PRIOR=values[action]['value']-values[ref]['value'],
                SCRATCH=scratch_value(values[action], root['query'])-scratch_value(values[ref], root['query']))))
    return labels


def gap_summary(labels, frozen, roots):
    rows = []
    for split in ('TRAIN', 'HOLDOUT'):
        for query in QUERIES:
            for life in LIVES:
                selected = [r for r in labels if r['life'] == life and r['query'] == query and roots[r['root_id']]['split'] == split]
                eligible = [r for r in selected if r['eligible']]
                samples = [r['paired_gaps'] for r in eligible]
                for method in ('PRIOR', 'SCRATCH'):
                    before = [r['base_gaps'][method] for r in eligible]
                    after = []
                    for row in eligible:
                        values = frozen[row['root_id']]['methods'][method]['action_values']
                        after.append(values[row['action']]['value']-values[row['reference_action']]['value'])
                    rows.append(dict(split=split, query=query, life=life, method=method,
                        ineligible_pairs=len(selected)-len(eligible), before=gap_statistics(before, samples),
                        after=gap_statistics(after, samples)))
    return rows


def feature_counts(afterstate):
    if max(afterstate) >= 11: return Counter()
    board = np.asarray(afterstate).reshape(4, 4)
    patterns = ((0, 1, 2, 4, 5, 6), (4, 5, 6, 8, 9, 10), (0, 1, 2, 3, 4, 5), (4, 5, 6, 7, 8, 9))
    result = Counter()
    for p, cells in enumerate(patterns):
        for reflected in (False, True):
            for turn in range(4):
                transformed = np.rot90(np.fliplr(board) if reflected else board, turn).reshape(-1)
                address = 0
                for cell in cells: address = address*11+int(transformed[cell])
                result[(p, address)] += 1
    return result


def expected_pair_counts(labels):
    total = Counter()
    for row in labels:
        if not row['eligible']: continue
        a, b = feature_counts(row['afterstate']), feature_counts(row['reference_afterstate'])
        addresses = set(a)|set(b); delta = [a[k]-b[k] for k in addresses]
        nonzero, occurrences = sum(v != 0 for v in delta), sum(abs(v) for v in delta)
        total.update(pair_fit_calls=1, pair_updates=int(nonzero > 0), unidentifiable_pairs=int(nonzero == 0),
            pair_feature_occurrences=sum(a.values())+sum(b.values()), pair_distinct_addresses=len(addresses),
            pair_nonzero_difference_addresses=nonzero, pair_signed_difference_occurrences=occurrences,
            pair_table_lookups=nonzero, pair_table_updates=nonzero, pair_update_occurrences=occurrences,
            pair_terminal_goal_bypasses=int(max(row['afterstate']) >= 11)+int(max(row['reference_afterstate']) >= 11))
    return total


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run, source, roster, frozen_run = (read(n) for n in ('run.json', 'source_capsule.json', 'roster.json', 'frozen_heads.json'))
    sources = {r['life']: r for r in source['snapshots']}
    roots = {r['root_id']: r for r in roster['cases']}
    settings = dict(lifecycles=list(LIVES), policies={p: old.QUERIES[p] for p in old.POLICIES},
        queries=QUERIES, parents=PARENTS, episodes=16, train_episodes=12, suffix_replicas=8,
        replicas=16, root_indices=list(INDICES), methods=list(METHODS), kinds=['PRIOR', 'SCRATCH'],
        epochs=20, rate=.1, max_steps=MAX_STEPS, workers=4, p_four=.1, version_base=BASE)
    checks = dict(frozen_settings=run['settings'] == settings, source_roster=len(source['snapshots']) == 4
        and set(sources) == set(LIVES), stage_rosters=all(len(run[k]) == 4 and {r['life'] for r in run[k]} == set(LIVES)
        for k in ('acquisition_lifecycles', 'fit_lifecycles', 'eval_lifecycles')),
        inherited_costs=run['inherited_costs'] == source['inherited_costs'],
        all_heads_frozen_before_evaluation=frozen_run['status'] == 'frozen' and frozen_run['eval_lifecycles'] == []
            and all(frozen_run[k] == run[k] for k in ('settings', 'inherited_costs', 'acquisition_lifecycles', 'fit_lifecycles')),
        slot_roster=len(roots) == len(roster['cases']) == 512 and set(roots) == set(range(512)),
        whole_episode_split=True, acquisition_roster=True, acquisition_traces=True, prefix_boards=True,
        root_predictions=True, frozen_predictions=True, branch_roster=True, branch_traces=True,
        paired_training_labels=True, fixed_fit_passes=True, learner_updates=True,
        control_roster=True, control_traces=True, source_immutability=True, model_loads=True, fixed_budgets=True)
    costs = {name: old.new_cost() for name in ('acquisition', 'training_branches', 'heldout_parent_branches',
        'heldout_full_branches', 'control')}
    costs.update(analysis_prefix_swipes=0, analysis_prediction_swipes=0, fit_counts=Counter(), fit_seconds=0.,
        model_accounting=[], source_load_seconds_includes_setup=True,
        model_count_note='Phase model counters retain nested parent calls; do not add parent_* fields to parent counters.')
    for root in roots.values():
        expected_id = root['life']*128+list(QUERIES).index(root['query'])*64+root['episode']*4+INDICES.index(root['index'])
        checks['whole_episode_split'] &= (root['root_id'] == expected_id and root['split'] == ('TRAIN' if root['episode'] < 12 else 'HOLDOUT'))
        if not root['available']:
            checks['slot_roster'] &= root['board'] is None and root['parent'] is None and root['actions'] == []
        else:
            checks['root_predictions'] &= parent_prediction_valid(root, sources[root['life']])
            costs['analysis_prediction_swipes'] += 4
    for data in run['acquisition_lifecycles']:
        life = data['life']; rows = list(read_rows(directory/data['trace']))
        keys = [(r['query'], r['replica']) for r in rows]
        checks['acquisition_roster'] &= len(keys) == len(set(keys)) == 32 and set(keys) == {(q, i) for q in QUERIES for i in range(16)}
        checks['slot_roster'] &= data['cases'] == [r for r in roster['cases'] if r['life'] == life]
        for row in rows:
            q = row['query']; okay = game_valid(row, model_state(sources[life], q, 'PARENT'))
            checks['acquisition_traces'] &= okay and row['life'] == life and row['method'] == 'ACQUISITION' and row['episode'] == row['replica']
            boards, okay, swipes = prefix_boards(row)
            checks['prefix_boards'] &= okay; costs['analysis_prefix_swipes'] += swipes
            for index in INDICES:
                root_id = life*128+list(QUERIES).index(q)*64+row['replica']*4+INDICES.index(index)
                root = roots[root_id]
                checks['prefix_boards'] &= root['board'] == boards[index] and root['available'] == (boards[index] is not None)
                if root['available']:
                    choice = root['parent']['action']
                    checks['root_predictions'] &= row['actions'][index] == choice and row['chosen_values'][index] == root['parent']['action_values'][choice]['value']
            old.add_cost(costs['acquisition'], row)
        for q, load in data['loads'].items():
            checks['model_loads'] &= load['source_policy'] == PARENTS[q] and load['source_updates'] == sources[life]['models'][PARENTS[q]]['updates'] and load['load_counts'].get('checkpoint_loads') == 1
        costs['model_accounting'].append(dict(phase='acquisition', life=life, loads=data['loads'], root_prediction_counts=data['root_prediction_counts']))
    frozen, labels, branches, valid, updates = {}, [], {}, {}, {}
    for data in run['fit_lifecycles']:
        life = data['life']; pred = read(data['predictions']); pred_ids = [r['root_id'] for r in pred]
        expected_ids = {r['root_id'] for r in roots.values() if r['life'] == life and r['available']}
        checks['frozen_predictions'] &= len(pred_ids) == len(set(pred_ids)) == len(expected_ids) and set(pred_ids) == expected_ids
        for row in pred:
            frozen[row['root_id']] = row
            checks['frozen_predictions'] &= frozen_prediction_valid(roots[row['root_id']], row)
        rows = list(read_rows(directory/data['trace'])); keys = [(r['root_id'], r['forced_action'], r['method'], r['replica']) for r in rows]
        expected = {(r['root_id'], a, 'PARENT', i) for r in roots.values() if r['life'] == life and r['available'] and r['split'] == 'TRAIN' for a in r['actions'] for i in range(DRAW_COUNT)}
        checks['branch_roster'] &= len(keys) == len(set(keys)) == len(expected) and set(keys) == expected
        for key, row in zip(keys, rows):
            branches[key] = row; valid[key] = game_valid(row, model_state(sources[life], row['query'], 'PARENT'), roots[row['root_id']])
            checks['branch_traces'] &= valid[key]; old.add_cost(costs['training_branches'], row)
        actual_labels = []
        for root in roots.values():
            if root['life'] == life and root['split'] == 'TRAIN' and root['available']:
                actual_labels.extend(pair_labels(root, branches, valid))
        checks['paired_training_labels'] &= read(data['labels']) == actual_labels
        labels.extend(actual_labels)
        epochs = list(read_rows(directory/data['epoch_trace'])); epoch_keys = [(r['query'], r['kind'], r['epoch']) for r in epochs]
        expected_epochs = {(q, k, e) for q in QUERIES for k in ('PRIOR', 'SCRATCH') for e in range(20)}
        checks['fixed_fit_passes'] &= len(epoch_keys) == len(set(epoch_keys)) == 80 and set(epoch_keys) == expected_epochs
        for q in QUERIES:
            query_data = data['queries'][q]; expected_counts = expected_pair_counts([r for r in actual_labels if r['query'] == q])
            checks['source_immutability'] &= query_data['model_state_before'] == query_data['model_state_after'] == model_state(sources[life], q, 'PARENT')
            for kind in ('PRIOR', 'SCRATCH'):
                head = query_data['learners'][kind]; checkpoint = query_data['checkpoints'][kind]
                nupdates = 20*expected_counts['pair_updates']; updates[(life, q, kind)] = nupdates
                checks['learner_updates'] &= (head['state'] == model_state(sources[life], q, kind, nupdates)
                    and checkpoint['updates'] == nupdates and checkpoint['parameter_count'] == 4*11**6
                    and all(head['counts'].get(k, 0) == 20*v for k, v in expected_counts.items()))
                for record in (r for r in epochs if r['query'] == q and r['kind'] == kind):
                    checks['fixed_fit_passes'] &= record['life'] == life and record['calls'] == expected_counts['pair_fit_calls'] and Counter(record['counts']) == expected_counts
                    checks['fixed_fit_passes'] &= math.isfinite(record['online_squared_error']) and record['online_squared_error'] >= 0
                    costs['fit_counts'].update(record['counts']); costs['fit_seconds'] += record['seconds']
        costs['model_accounting'].append(dict(phase='fit', life=life, queries=data['queries']))
    outer, outer_valid = {}, {}
    for data in run['eval_lifecycles']:
        life = data['life']; rows = list(read_rows(directory/data['trace']))
        keys = [(r['root_id'], r['forced_action'], r['method'], r['replica']) for r in rows]
        expected = set()
        for root in roots.values():
            if root['life'] != life or not root['available'] or root['split'] != 'HOLDOUT': continue
            expected.update((root['root_id'], a, 'PARENT', i) for a in root['actions'] for i in range(DRAW_COUNT))
            expected.update((root['root_id'], frozen[root['root_id']]['methods']['PRIOR']['action'], 'FULL_UPDATE', i) for i in range(DRAW_COUNT))
        checks['branch_roster'] &= len(keys) == len(set(keys)) == len(expected) and set(keys) == expected
        for key, row in zip(keys, rows):
            kind = 'PARENT' if row['method'] == 'PARENT' else 'PRIOR'
            expected_state = model_state(sources[life], row['query'], kind, updates.get((life, row['query'], kind), 0))
            branches[key] = row; valid[key] = game_valid(row, expected_state, roots[row['root_id']])
            checks['branch_traces'] &= valid[key]
            old.add_cost(costs['heldout_parent_branches' if kind == 'PARENT' else 'heldout_full_branches'], row)
        rows = list(read_rows(directory/data['control_trace'])); keys = [(r['life'], r['query'], r['method'], r['replica']) for r in rows]
        expected = {(life, q, m, i) for q in QUERIES for m in METHODS for i in range(OUTER_COUNT)}
        checks['control_roster'] &= len(keys) == len(set(keys)) == len(expected) and set(keys) == expected
        for key, row in zip(keys, rows):
            kind, q = row['method'], row['query']
            outer[key] = row; outer_valid[key] = game_valid(row, model_state(sources[life], q, kind, updates.get((life, q, kind), 0)))
            checks['control_traces'] &= outer_valid[key]; old.add_cost(costs['control'], row)
        for q, query_data in data['queries'].items():
            checks['source_immutability'] &= query_data['model_state_before'] == query_data['model_state_after'] == model_state(sources[life], q, 'PARENT')
            for kind, head in query_data['learners'].items():
                checks['learner_updates'] &= head['state'] == model_state(sources[life], q, kind, updates[(life, q, kind)])
                checks['model_loads'] &= head['load_counts'].get('checkpoint_loads') == 1
                checks['learner_updates'] &= not head['counts'].get('pair_updates', 0)
        costs['model_accounting'].append(dict(phase='evaluation', life=life, queries=data['queries']))
    heldout = []
    for root in roots.values():
        if root['split'] != 'HOLDOUT': continue
        item = {k: root[k] for k in ('root_id', 'life', 'query', 'episode', 'index', 'available')}
        item['complete'] = True
        if root['available']:
            labels.extend(pair_labels(root, branches, valid))
            choice = frozen[root['root_id']]['methods']['PRIOR']['action']
            selected = [('PARENT', root['parent']['action']), ('PARENT', choice), ('FULL_UPDATE', choice)]
            arrays = []
            for method, action in selected:
                keys = [(root['root_id'], action, method, i) for i in range(DRAW_COUNT)]
                ready = all(k in branches and valid.get(k, False) and branches[k]['result']['status'] in ('WON', 'LOST') for k in keys)
                item['complete'] &= ready
                if ready: arrays.append([branches[k]['result']['utility'] for k in keys])
            if item['complete']: item.update(heldout_differences(*arrays))
            item.update(parent_action=root['parent']['action'], prior_action=choice, action_changed=choice != root['parent']['action'])
        heldout.append(item)
    for name, maximum in (('training_branches', 12288), ('heldout_parent_branches', 4096), ('heldout_full_branches', 1024)):
        checks['fixed_budgets'] &= costs[name]['games'] == roster[name] <= maximum
    checks['fixed_budgets'] &= costs['control']['games'] == roster['control_games'] == 384 and costs['acquisition']['games'] == 128
    costs['new_environment_samples'] = sum(costs[k]['environment_counts'].get('sampled_transitions', 0)
        for k in ('acquisition', 'training_branches', 'heldout_parent_branches', 'heldout_full_branches', 'control'))
    costs['physical_games'] = sum(costs[k]['games'] for k in ('acquisition', 'training_branches', 'heldout_parent_branches', 'heldout_full_branches', 'control'))
    overlap = []
    for life in LIVES:
        for query in QUERIES:
            train = {tuple(r['board']) for r in roots.values() if r['life'] == life and r['query'] == query and r['split'] == 'TRAIN' and r['available']}
            test = [r for r in roots.values() if r['life'] == life and r['query'] == query and r['split'] == 'HOLDOUT' and r['available']]
            overlap.append(dict(life=life, query=query, heldout_roots=len(test), exact_board_overlap=sum(tuple(r['board']) in train for r in test)))
    control = full_game_summary(outer, outer_valid); heldout_summary = aggregate_heldout(heldout)
    complete = run['status'] == 'complete' and all(checks.values())
    primary = complete and all(v['complete'] for r in control['methods'].values() for v in r.values())
    return dict(schema='acfqp.paired_ntuple.v130.analysis', complete=complete, primary_complete=primary,
        checks={k: bool(v) for k, v in checks.items()}, coverage=dict(slots=len(roots), available=sum(r['available'] for r in roots.values()),
            train_available=sum(r['available'] and r['split'] == 'TRAIN' for r in roots.values()),
            heldout_available=sum(r['available'] and r['split'] == 'HOLDOUT' for r in roots.values()), board_overlap=overlap),
        paired_gap_errors=gap_summary(labels, frozen, roots), heldout=heldout, heldout_summary=heldout_summary,
        control=control, costs=costs, inherited_work=run['inherited_costs'], seconds=run.get('seconds'),
        analysis_seconds=perf_counter()-started,
        scope='One frozen improvement round; independent prefix replay and trace/accounting checks, not full continuation replay. Paired branch means are noisy labels. Full-game comparisons average four source histories equally; separate target heads do not establish zero-shot query transfer.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_paired_ntuple_v130')
    args = parser.parse_args(); result = analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'], checks=result['checks'])))
