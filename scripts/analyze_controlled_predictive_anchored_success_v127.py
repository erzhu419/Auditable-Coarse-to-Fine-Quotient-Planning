"""Reconcile retained-policy event learning and anchored query readouts."""
import argparse
from collections import Counter
from itertools import zip_longest
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from scripts import analyze_controlled_predictive_policy_consequences_v126 as old

LIVES, POLICIES, AGES, QUERIES = old.LIVES, old.POLICIES, old.AGES, old.QUERIES
FROZEN = old.FROZEN
LEARNED = ('LEARNED_reward', 'LEARNED_risk_goal', 'LEARNED_GPI')
CONSTANT = ('CONSTANT_reward', 'CONSTANT_risk_goal', 'CONSTANT_GPI')
ADAPTIVE, METHODS = LEARNED + CONSTANT, FROZEN + LEARNED + CONSTANT
BASE, REPLICAS, MAX_STEPS = 127 * 100000000, 8, 2000
METRICS, FIELDS = old.METRICS, old.FIELDS
read_rows, mean = old.read_rows, old.mean
new_cost, add_cost, merge_cost = old.new_cost, old.add_cost, old.merge_cost


def evaluation_seed(life, replica):
    return BASE + 90000000 + life * 100000 + replica


def expected_labels(row):
    r = row['result']; n, status = r['steps'], r['status']
    updates = 0 if status == 'CUTOFF' else n - int(status == 'WON')
    return updates, updates * int(status == 'WON')


def inspect_replay(rows, originals, life, policy, episodes=1024, ages=AGES):
    checks = dict(replay_roster=True, retained_seed_labels=True, retained_trace=True,
        replay_prefix=True, replay_no_acquisition=True, replay_counters=True)
    cost, blocks, prefixes = new_cost(), [], {}
    updates = successes = total = retained_transitions = unique_total = winning_unique = 0
    def empty(start):
        return dict(start=start, end=start, total_score=0, updates=0, successes=0,
            success_afterstates=0, unique_feature_updates=0,
            censored_afterstates=0, analytic_goals=0, retained_transitions=0, **new_cost())
    block = empty(0)
    for index, pair in enumerate(zip_longest(rows, originals)):
        row, source = pair
        if row is None or source is None:
            checks['replay_roster'] = False
            continue
        r, fit, sr = row['result'], row['fit'], source['result']
        n, wins = expected_labels(source)
        checks['replay_roster'] &= (row['life'], row['policy'], row['episode_index']) == (life, policy, index)
        checks['retained_seed_labels'] &= (source['life'], source['policy'], source['episode_index']) == (life, policy, index)
        checks['retained_seed_labels'] &= row['source_seed'] == source['seed'] == old.train_seed(life, policy, index)
        checks['retained_seed_labels'] &= all(r[k] == sr[k] for k in ('steps', 'status', 'score'))
        checks['retained_trace'] &= old.compact_valid(source)
        checks['replay_prefix'] &= (r['updates_before'], r['updates_after'], r['successes_before'], r['successes_after']) == (updates, updates+n, successes, successes+wins)
        checks['replay_no_acquisition'] &= not r['environment_counts'] and r['retained_transitions'] == sr['steps']
        checks['replay_no_acquisition'] &= not r['learning_counts'].get('model_spawn_samples', 0)
        unique = fit['unique_feature_updates']; status, steps = sr['status'], sr['steps']
        expected_fit = dict(status=status, observed_afterstates=steps, updates=n,
            successes=wins, success_afterstates=wins, analytic_goals=int(status == 'WON'),
            censored_afterstates=steps if status == 'CUTOFF' else 0)
        checks['retained_seed_labels'] &= all(fit[k] == v for k, v in expected_fit.items())
        checks['replay_counters'] &= 4*n <= unique <= 32*n
        expected = dict(replay_games=1, replay_swipe_calls=steps, replay_line_table_lookups=4*steps,
            replay_recorded_spawns=steps, training_games=1, training_observed_afterstates=steps,
            success_observation_updates=n, unique_feature_updates=unique, count_array_writes=2*unique,
            feature_address_occurrences=32*n, training_analytic_goals=int(status == 'WON'),
            censored_games=int(status == 'CUTOFF'), censored_afterstates=steps if status == 'CUTOFF' else 0)
        checks['replay_counters'] &= all(r['learning_counts'].get(k, 0) == v for k, v in expected.items())
        unique_total += unique; winning_unique += unique if status == 'WON' else 0
        updates += n; successes += wins; total += 1; retained_transitions += sr['steps']
        add_cost(cost, row); add_cost(block, row)
        block['end'] = total; block['total_score'] += sr['score']
        block['updates'] += n; block['successes'] += wins; block['retained_transitions'] += sr['steps']
        block['success_afterstates'] += wins; block['unique_feature_updates'] += unique
        block['censored_afterstates'] += sr['steps'] if sr['status'] == 'CUTOFF' else 0
        block['analytic_goals'] += int(sr['status'] == 'WON')
        if total in ages:
            prefixes[total] = dict(updates=updates, successes=successes,
                constant=successes/updates if updates else .5, retained_transitions=retained_transitions,
                unique_feature_updates=unique_total, winning_unique_feature_updates=winning_unique)
        if total % 256 == 0:
            blocks.append(block); block = empty(total)
    if block['games']:
        blocks.append(block)
    checks['replay_roster'] &= total == episodes
    return dict(checks=checks, cost=cost, blocks=blocks, prefixes=prefixes,
        retained_transitions=retained_transitions)


def outer_key(row):
    return row['life'], row['method'], row['checkpoint'], row['query'], row['replica']


def outer_valid(row, expected_updates, expected_successes=None, constants=None):
    r, method, query = row['result'], row['method'], row['query']
    valid = (old.compact_valid(row) and row['seed'] == evaluation_seed(row['life'], row['replica'])
        and r['utility'] == old.utility(r['score'], r['status'], query)
        and all(not r.get(field, {}).get(k, 0) for field in FIELDS
            for k in ('td_updates', 'source_td_updates', 'mc_updates', 'success_observation_updates', 'count_array_writes', 'model_spawn_samples')))
    if method in FROZEN:
        return (valid and row['policy'] == query == method[7:] and row['checkpoint'] is None
            and r['source_updates_before'] == r['source_updates_after'] == expected_updates
            and r['policy_counts'].get('choose_calls', 0) == r['steps'])
    valid &= r['updates_before'] == r['updates_after'] == expected_updates
    valid &= r['successes_before'] == r['successes_after'] == expected_successes
    n = r['steps']; mode, actor = method.split('_', 1)
    learn = r['learning_counts']; source_calls = n * (2 if actor == 'GPI' else 1)
    valid &= learn.get('choose_calls', 0) == learn.get('source_choose_calls', 0) == source_calls
    valid &= learn.get('exact_anchor_bypasses', 0) == (n if query in POLICIES and actor in ('GPI', query) else 0)
    pred = learn.get('success_predictions', 0); goals = learn.get('terminal_goal_bypasses', 0)
    valid &= learn.get('count_array_reads', 0) == 64*(pred-goals)
    if mode == 'CONSTANT':
        valid &= pred == 0
    arrays = ('chosen_anchor_values', 'chosen_success_probabilities', 'chosen_values', 'policy_indices')
    if not all(len(row[k]) == n for k in arrays):
        return False
    for step, (anchor, success, value, index) in enumerate(zip(*(row[k] for k in arrays))):
        if index not in (0, 1):
            return False
        policy = POLICIES[index]; src, q = QUERIES[policy], QUERIES[query]
        valid &= actor == 'GPI' or actor == policy
        if query == policy:
            valid &= success is None and value == anchor
        else:
            valid &= success is not None and 0 <= success <= 1
            winning_tail = step == n-1 and r['status'] == 'WON'
            if winning_tail:
                valid &= success == 1.
            elif mode == 'CONSTANT':
                valid &= success == constants[index]
            if success is not None:
                expected = anchor + src['failure_penalty'] - q['failure_penalty'] + (
                    q['failure_penalty'] + q['goal_bonus'] - src['failure_penalty'] - src['goal_bonus']) * success
                valid &= math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12)
        valid &= math.isfinite(anchor) and math.isfinite(value)
    return bool(valid)


def same_history(left, right):
    return (all(left[k] == right[k] for k in ('seed', 'initial_board', 'final_board',
        'initial_spawns', 'actions', 'spawned_cells', 'spawned_ranks', 'scores'))
        and all(left['result'][k] == right['result'][k] for k in ('score', 'status', 'steps', 'utility', 'components')))


def summarize(indexed, valid):
    methods = {}
    for method in METHODS:
        methods[method] = {}
        for age in AGES:
            methods[method][str(age)] = {}
            for query in QUERIES:
                lives = []
                for life in LIVES:
                    keys = [(life, method, None if method in FROZEN else age,
                        method[7:] if method in FROZEN else query, rep) for rep in range(REPLICAS)]
                    rows = [indexed[k] for k in keys if k in indexed]
                    complete = len(rows) == REPLICAS and all(valid.get(k, False) for k in keys)
                    values = {k: [old.utility(r['result']['score'], r['result']['status'], query)
                        if k == 'utility' else r['result'][k] for r in rows] for k in METRICS}
                    lives.append(dict(life=life, complete=complete, games=len(rows),
                        means={k: mean(values[k]) if complete else None for k in METRICS},
                        wins=sum(r['result']['status'] == 'WON' for r in rows),
                        statuses=dict(Counter(r['result']['status'] for r in rows))))
                methods[method][str(age)][query] = dict(lifecycles=lives,
                    lifecycle_mean={k: mean(r['means'][k] for r in lives) for k in METRICS},
                    games=sum(r['games'] for r in lives), wins=sum(r['wins'] for r in lives),
                    complete=all(r['complete'] for r in lives))
    pairs = [(m, m.replace('LEARNED_', 'CONSTANT_')) for m in LEARNED]
    pairs += [('LEARNED_GPI', r) for r in FROZEN + LEARNED[:2]]
    contrasts = {str(age): {left+'_minus_'+right: {q: old.old.comparisons(
        methods[left][str(age)][q], methods[right][str(age)][q]) for q in QUERIES}
        for left, right in pairs} for age in AGES}
    growth = {m: {q: old.old.comparisons(methods[m]['1024'][q], methods[m]['256'][q])
        for q in QUERIES} for m in ADAPTIVE}
    return dict(methods=methods, comparisons=contrasts, age1024_minus256=growth)


def diagnostic(row, source, prefix):
    r = source['result']; predictions = np.asarray(row['probabilities'], dtype=float)
    n = r['steps']; eligible, successes = expected_labels(source)
    checks = dict(diagnostic_source_path=(row['life'], row['policy'], row['replica'], row['eval_id']) ==
        (source['life'], source['policy'], source['replica'], source['eval_id']),
        diagnostic_prefix=row['prefix_updates'] == prefix['updates'] and row['prefix_successes'] == prefix['successes'] and row['constant'] == prefix['constant'],
        diagnostic_readonly=(all(not row['learning_counts'].get(k, 0) for k in ('success_observation_updates', 'count_array_writes', 'td_updates', 'model_spawn_samples'))
            and row['learning_counts'].get('success_predictions') == n
            and row['learning_counts'].get('terminal_goal_bypasses', 0) == int(r['status'] == 'WON')
            and row['learning_counts'].get('count_array_reads', 0) == 64*(n-int(r['status'] == 'WON'))),
        bounded_probabilities=predictions.shape == (n,) and bool(np.isfinite(predictions).all())
            and bool(((predictions >= 0) & (predictions <= 1)).all()))
    if not checks['bounded_probabilities']:
        return dict(checks=checks, samples=0, learned_sse=0., constant_sse=0.)
    if r['status'] == 'WON':
        checks['bounded_probabilities'] &= predictions[-1] == 1.
    target = int(r['status'] == 'WON'); pred = predictions[:eligible]
    return dict(checks=checks, samples=eligible, successes=successes,
        learned_sse=float(((pred-target)**2).sum()),
        constant_sse=float(eligible*(prefix['constant']-target)**2))


def diagnostic_summaries(rows):
    lives = []
    for life in LIVES:
        for policy in POLICIES:
            for age in AGES:
                group = [r for r in rows if (r['life'], r['policy'], r['checkpoint']) == (life, policy, age)]
                n = sum(r['samples'] for r in group)
                complete = len(group) == REPLICAS and all(all(r['checks'].values()) for r in group)
                lives.append(dict(life=life, policy=policy, checkpoint=age, games=len(group),
                    samples=n, complete=complete, **{label: sum(r[label+'_sse'] for r in group)/n if complete and n else None
                    for label in ('learned', 'constant')}))
    means = {p: {str(a): {label: mean(r[label] for r in lives if r['policy'] == p and r['checkpoint'] == a)
        for label in ('learned', 'constant')} for a in AGES} for p in POLICIES}
    return dict(lifecycles=lives, lifecycle_mean_brier=means)


def model_valid(directory, cp, prefix, policy, source_updates):
    path = directory / cp['model_ref']
    if not path.exists() or path.stat().st_size != cp['model_bytes']:
        return False
    with np.load(path, allow_pickle=False) as data:
        meta = json.loads(str(data['metadata'])); indices, visits, wins = data['indices'], data['visits'], data['wins']
        return (meta['schema'] == 'acfqp.anchored_success.v127' and meta['radix'] == 11
            and meta['source_query'] == QUERIES[policy] and meta['source_updates'] == source_updates
            and all(meta[k] == cp[k] == prefix[k] for k in ('updates', 'successes'))
            and meta['global_success_rate'] == cp['constant'] == prefix['constant']
            and len(indices) == len(visits) == len(wins) and indices.dtype == np.dtype('int64')
            and visits.dtype == wins.dtype == np.dtype('uint64')
            and bool((indices >= 0).all()) and bool((indices < 4*11**6).all())
            and bool((np.diff(indices) > 0).all()) and bool((visits > 0).all())
            and bool((wins <= visits).all()) and bool((visits <= cp['updates']).all())
            and int(visits.sum()) == prefix['unique_feature_updates']
            and int(wins.sum()) == prefix['winning_unique_feature_updates']
            and cp['save_counts'].get('checkpoint_saves') == 1
            and cp['save_counts'].get('checkpoint_scanned_entries') == 4*11**6
            and cp['save_counts'].get('checkpoint_saved_addresses') == len(indices)
            and cp['save_counts'].get('checkpoint_saved_count_entries') == 2*len(indices))


def analyze(directory):
    directory = Path(directory).resolve()
    run = json.loads((directory/'run.json').read_text())
    source = json.loads((directory/'source_capsule.json').read_text())
    expected_settings = dict(lifecycles=list(LIVES), policies={p: QUERIES[p] for p in POLICIES},
        queries=QUERIES, ages=list(AGES), train_episodes=1024, replicas=REPLICAS,
        max_steps=MAX_STEPS, workers=4, block_size=256, p_four=.1, version_base=BASE, prior_strength=1.)
    inherited = source['inherited_costs']
    inherited_v120 = sum(b['environment_counts']['sampled_transitions'] for life in inherited['v120_training']
        for policy in life['queries'].values() for b in policy['training_blocks'])
    checks = dict(frozen_settings=run['settings'] == expected_settings,
        source_roster=source['schema'] == 'acfqp.anchored_success.v127.source'
            and len(source['snapshots']) == 4 and {s['life'] for s in source['snapshots']} == set(LIVES)
            and all(set(s) == {'life', 'rule', 'models', 'training_trace'} and set(s['models']) == set(POLICIES) for s in source['snapshots']),
        lifecycle_roster=len(run['lifecycles']) == 4 and {s['life'] for s in run['lifecycles']} == set(LIVES),
        inherited_costs=run['inherited_costs'] == inherited and inherited_v120 == 22124667
            and inherited['v126_training']['games'] == 8192
            and inherited['v126_training']['environment_counts']['sampled_transitions'] == 6635452,
        source_models=True, retained_source=True, policy_roster=True, source_policy_immutable=True,
        replay_blocks=True, checkpoint_roster=True, checkpoint_prefixes=True, count_models=True,
        setup_counts=True, outer_roster=True, outer_readonly=True, outer_eval_ids=True,
        own_query_history=True, diagnostic_roster=True, all_outer_terminal=True)
    sources = {s['life']: s for s in source['snapshots']}
    training, diagnostic_rows, indexed, valid = [], [], {}, {}
    costs = dict(replay=new_cost(), outer=new_cost(), outer_by_method={m: new_cost() for m in METHODS},
        diagnostic_counts=Counter(), diagnostic_seconds=0.,
        source_load_counts=Counter(), source_load_seconds=0., source_setup_counts=Counter(), source_setup_seconds=0.,
        learner_setup_counts=Counter(), learner_setup_seconds=0., model_save_counts=Counter(), model_save_seconds=0.,
        retained_model_bytes=0, retained_model_files=0, peak_weight_bytes_per_life=0, retained_replayed_transitions=0)
    for life in run['lifecycles']:
        ident = life['life']; supplied = sources[ident]
        checks['policy_roster'] &= set(life['policies']) == set(POLICIES)
        checks['retained_source'] &= Path(supplied['training_trace']) == ROOT/'reports/controlled_predictive_policy_consequences_v126'/f'life_{ident}'/'training.jsonl.gz'
        checkpoints, prefixes = {}, {}
        for policy in POLICIES:
            data = life['policies'][policy]; src = supplied['models'][policy]
            checks['source_models'] &= (Path(src['path']) == ROOT/'reports/controlled_predictive_ntuple_learning_v120'/f'life_{ident}'/policy/'checkpoint_4096.npz'
                and old.old.model_valid(directory, dict(model_ref=src['path'], updates=src['updates'])))
            checks['source_policy_immutable'] &= data['source_updates_before'] == data['source_updates_after'] == src['updates']
            rows = (r for r in read_rows(directory/life['training_trace']) if r['policy'] == policy)
            originals = (r for r in read_rows(Path(supplied['training_trace'])) if r['policy'] == policy)
            found = inspect_replay(rows, originals, ident, policy)
            for key, value in found['checks'].items():
                checks[key] = checks.get(key, True) and value
            merge_cost(costs['replay'], found['cost']); costs['retained_replayed_transitions'] += found['retained_transitions']
            training.append(dict(life=ident, policy=policy, **found)); prefixes[policy] = found['prefixes']
            checks['replay_blocks'] &= len(data['training_blocks']) == len(found['blocks'])
            for saved, actual in zip(data['training_blocks'], found['blocks']):
                checks['replay_blocks'] &= all(actual[k] == v for k, v in saved.items())
            checks['checkpoint_roster'] &= [cp['age'] for cp in data['checkpoints']] == list(AGES)
            checkpoints[policy] = {cp['age']: cp for cp in data['checkpoints']}
            for cp in data['checkpoints']:
                prefix = prefixes[policy].get(cp['age'], {})
                checks['checkpoint_prefixes'] &= all(cp[k] == prefix.get(k) for k in ('updates', 'successes', 'constant'))
                checks['count_models'] &= model_valid(directory, cp, prefix, policy, src['updates'])
                costs['retained_model_bytes'] += cp['model_bytes']; costs['retained_model_files'] += 1
                costs['model_save_seconds'] += cp['save_seconds']; costs['model_save_counts'].update(cp['save_counts'])
            for key in ('source_load', 'source_setup', 'learner_setup'):
                costs[key+'_counts'].update(data[key+'_counts']); costs[key+'_seconds'] += data[key+'_seconds']
            checks['setup_counts'] &= (data['source_load_counts'].get('checkpoint_loads') == 1
                and data['source_load_counts'].get('checkpoint_loaded_parameters') == src['nonzero_weights']
                and data['source_setup_counts'].get('allocated_weight_bytes') == 4*11**6*8
                and data['learner_setup_counts'].get('allocated_count_bytes') == 2*4*11**6*8)
        raw = list(read_rows(directory/life['control_trace']))
        expected = {(ident, m, None, m[7:], r) for m in FROZEN for r in range(REPLICAS)}
        expected |= {(ident, m, age, q, r) for m in ADAPTIVE for age in AGES for q in QUERIES for r in range(REPLICAS)}
        keys = [outer_key(r) for r in raw]
        checks['outer_roster'] &= len(keys) == len(set(keys)) == len(expected) and set(keys) == expected
        ids = [r['eval_id'] for r in raw]; checks['outer_eval_ids'] &= len(ids) == len(set(ids))
        for row in raw:
            key = outer_key(row); frozen = row['method'] in FROZEN
            updates = supplied['models'][row['policy']]['updates'] if frozen else [checkpoints[p][row['checkpoint']]['updates'] for p in POLICIES]
            successes = None if frozen else [checkpoints[p][row['checkpoint']]['successes'] for p in POLICIES]
            constants = None if frozen else [checkpoints[p][row['checkpoint']]['constant'] for p in POLICIES]
            ready = outer_valid(row, updates, successes, constants)
            checks['outer_readonly'] &= ready
            terminal = row['result']['status'] in ('WON', 'LOST'); checks['all_outer_terminal'] &= terminal
            indexed[key], valid[key] = row, ready and terminal
            add_cost(costs['outer'], row); add_cost(costs['outer_by_method'][row['method']], row)
        for p in POLICIES:
            for mode in ('LEARNED', 'CONSTANT'):
                for age in AGES:
                    for rep in range(REPLICAS):
                        key, ref = (ident, mode+'_'+p, age, p, rep), (ident, 'FROZEN_'+p, None, p, rep)
                        checks['own_query_history'] &= key in indexed and ref in indexed and same_history(indexed[key], indexed[ref])
        raw_diag = list(read_rows(directory/life['diagnostic_trace']))
        keys = [(r['life'], r['policy'], r['checkpoint'], r['replica']) for r in raw_diag]
        expected_diag = {(ident, p, a, r) for p in POLICIES for a in AGES for r in range(REPLICAS)}
        checks['diagnostic_roster'] &= len(keys) == len(set(keys)) == len(expected_diag) and set(keys) == expected_diag
        for row in raw_diag:
            key = ident, 'FROZEN_'+row['policy'], None, row['policy'], row['replica']
            if key not in indexed:
                checks['diagnostic_roster'] = False
                continue
            found = diagnostic(row, indexed[key], prefixes[row['policy']][row['checkpoint']])
            for key, value in found['checks'].items():
                checks[key] = checks.get(key, True) and value
            diagnostic_rows.append(dict(life=ident, policy=row['policy'], checkpoint=row['checkpoint'], replica=row['replica'], **found))
            costs['diagnostic_counts'].update(row['learning_counts']); costs['diagnostic_seconds'] += row['seconds']
        checks['setup_counts'] &= life['peak_weight_bytes'] == 6*4*11**6*8
        costs['peak_weight_bytes_per_life'] = max(costs['peak_weight_bytes_per_life'], life['peak_weight_bytes'])
    costs['physical_outer_games'] = costs['outer']['games']
    costs['logical_outer_rows'] = sum(costs['outer_by_method'][m]['games'] * (8 if m in FROZEN else 1) for m in METHODS)
    costs['fresh_training_environment_transitions'] = costs['replay']['environment_counts'].get('sampled_transitions', 0)
    costs['actual_new_environment_transitions'] = costs['outer']['environment_counts'].get('sampled_transitions', 0) + costs['fresh_training_environment_transitions']
    costs['model_spawn_samples'] = sum(c[field].get('model_spawn_samples', 0) for c in (costs['replay'], costs['outer']) for field in FIELDS)
    checks['physical_and_logical_counts'] = costs['physical_outer_games'] == 1600 and costs['logical_outer_rows'] == 2048
    checks['full_retained_replay'] = costs['replay']['games'] == 8192 and costs['retained_replayed_transitions'] == 6635452
    complete = run['status'] == 'complete' and all(v for k, v in checks.items() if k != 'all_outer_terminal')
    return dict(schema='acfqp.anchored_success.v127.analysis', complete=bool(complete),
        primary_complete=bool(complete and checks['all_outer_terminal']), checks={k: bool(v) for k, v in checks.items()},
        control=summarize(indexed, valid), training=training, diagnostics=diagnostic_summaries(diagnostic_rows), costs=costs,
        inherited_work=dict(v120_training_transitions=inherited_v120, v126_training=inherited['v126_training'],
            deterministic_prior=inherited['deterministic_prior']), seconds=run['seconds'],
        scope='Own-query history recovery is an engineering identity. Transfer needs learned-versus-constant and frozen-source gains; bounded event counts alone do not prove calibration.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    args = parser.parse_args(); report = analyze(args.run_dir)
    output = args.run_dir/'analysis.json'
    output.write_text(json.dumps(report, allow_nan=False, indent=2)+'\n')
    print(json.dumps(dict(complete=report['complete'], primary_complete=report['primary_complete'],
        checks=report['checks'], output=str(output)), allow_nan=False))
