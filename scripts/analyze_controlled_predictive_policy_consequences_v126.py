"""Independently reconcile fixed-policy Monte Carlo labels and query reuse."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from scripts import analyze_controlled_predictive_ntuple_regime_v121 as old

LIVES, POLICIES, AGES = tuple(range(4)), ('reward', 'risk_goal'), (256, 1024)
QUERIES = dict(reward=dict(reward_weight=1., failure_penalty=0., goal_bonus=0.),
    risk_goal=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.),
    risk1=dict(reward_weight=1., failure_penalty=1., goal_bonus=1.),
    risk8=dict(reward_weight=1., failure_penalty=8., goal_bonus=8.))
LEARNED = ('POLICY_reward', 'POLICY_risk_goal', 'GPI')
FROZEN = ('FROZEN_reward', 'FROZEN_risk_goal')
METHODS = FROZEN + LEARNED
REPLICAS, MAX_STEPS, BASE = 8, 2000, 126 * 100000000
FIELDS = ('environment_counts', 'policy_counts', 'learning_counts', 'setup_counts')
METRICS = ('score', 'utility', 'steps', 'seconds')
COMPONENTS = ('reward', 'failure', 'success')
mean = old.mean
read_rows = old.read_rows


def train_seed(life, policy, episode):
    return BASE + 1000000 + life * 100000 + POLICIES.index(policy) * 10000 + episode


def evaluation_seed(life, replica):
    return BASE + 90000000 + life * 100000 + replica


def utility(score, status, query):
    q = QUERIES[query]
    return q['reward_weight'] * score / 2048 - q['failure_penalty'] * (status == 'LOST') + q['goal_bonus'] * (status == 'WON')


def components(score, status):
    return [score / 2048, int(status == 'LOST'), int(status == 'WON')]


def suffix_targets(scores, status):
    """The action's immediate score is outside its afterstate continuation."""
    if status == 'CUTOFF':
        return np.empty((0, 3), dtype=float)
    scores = np.asarray(scores, dtype=float)
    future = (scores.sum() - np.cumsum(scores)) / 2048
    eligible = len(scores) - int(status == 'WON')
    return np.column_stack((future[:eligible], np.full(eligible, status == 'LOST'),
                            np.full(eligible, status == 'WON')))


def new_cost():
    return dict(games=0, seconds=0., statuses=Counter(), **{key: Counter() for key in FIELDS})


def add_cost(cost, row):
    r = row['result']
    cost['games'] += 1; cost['seconds'] += r['seconds']; cost['statuses'][r['status']] += 1
    for key in FIELDS:
        cost[key].update(r.get(key, {}))


def merge_cost(total, cost):
    total['games'] += cost['games']; total['seconds'] += cost['seconds']
    total['statuses'].update(cost['statuses'])
    for key in FIELDS:
        total[key].update(cost[key])


def compact_valid(row):
    r = row['result']; n = r['steps']; status = r['status']; w = r['environment_counts']
    return (0 < n <= MAX_STEPS and status in ('WON', 'LOST', 'CUTOFF')
        and (status != 'CUTOFF' or n == MAX_STEPS)
        and all(len(row[key]) == n for key in ('actions', 'spawned_cells', 'spawned_ranks', 'scores'))
        and sum(row['scores']) == r['score']
        and all(a in ('DOWN', 'LEFT', 'RIGHT', 'UP') for a in row['actions'])
        and all(0 <= cell < 16 for cell in row['spawned_cells'])
        and all(rank in (1, 2) for rank in row['spawned_ranks'])
        and len(row['initial_board']) == len(row['final_board']) == 16
        and len(row['initial_spawns']) == 2
        and (max(row['final_board']) >= 11) == (status == 'WON')
        and r['components'] == components(r['score'], status)
        and w.get('sampled_transitions') == n and w.get('initial_spawns') == 2
        and w.get('environment_random_draws') == 2*n+4 and w.get('ground_explicit_swipe_calls') == n
        and math.isfinite(r['seconds']) and r['seconds'] >= 0)


def fit_valid(row):
    r, fit = row['result'], row['fit']; n, status = r['steps'], r['status']
    target = suffix_targets(row['scores'], status)
    return (fit['status'] == status and fit['observed_afterstates'] == n
        and fit['updates'] == len(target) and fit['analytic_goals'] == int(status == 'WON')
        and fit['head_updates'] == [len(target)] * 3
        and fit['censored_afterstates'] == (n if status == 'CUTOFF' else 0)
        and np.allclose(fit['target_sums'], target.sum(axis=0), rtol=0., atol=1e-10))


def inspect_training(rows, life, policy, source_updates, episodes=1024, ages=AGES):
    checks = dict(training_roster=True, training_seeds=True, training_trace=True,
        monte_carlo_targets=True, vector_update_prefix=True, source_policy_immutable=True,
        learning_counters=True, no_model_samples=True)
    cost, blocks, prefixes = new_cost(), [], {}
    updates, target_sums, total = 0, np.zeros(3), 0
    def empty_block(start):
        return dict(start=start, end=start, total_score=0, updates=0,
            censored_afterstates=0, analytic_goals=0, target_sums=[0., 0., 0.], **new_cost())
    block = empty_block(0)
    diagnostics = Counter()
    for index, row in enumerate(rows):
        r = row['result']; fit = row['fit']; target = suffix_targets(row['scores'], r['status'])
        checks['training_roster'] &= (row['life'], row['policy'], row['method'], row['episode_index']) == (life, policy, 'TRAIN', index)
        checks['training_seeds'] &= row['seed'] == train_seed(life, policy, index)
        checks['training_trace'] &= compact_valid(row)
        checks['monte_carlo_targets'] &= fit_valid(row)
        checks['vector_update_prefix'] &= r['updates_before'] == updates and r['updates_after'] == updates + len(target)
        checks['source_policy_immutable'] &= (r['source_updates_before'] == r['source_updates_after'] == source_updates
            and r['policy_counts'].get('td_updates', 0) == 0 and r['policy_counts'].get('choose_calls', 0) == r['steps'])
        checks['no_model_samples'] &= all(not r.get(field, {}).get('model_spawn_samples', 0) for field in FIELDS)
        learn = r['learning_counts']; m = len(target)
        expected = dict(training_games=1, training_observed_afterstates=r['steps'],
            mc_updates=m, component_updates=3*m, component_predictions=3*m,
            table_lookups=96*m, table_update_occurrences=96*m,
            training_analytic_goals=int(r['status'] == 'WON'),
            censored_games=int(r['status'] == 'CUTOFF'),
            censored_afterstates=r['steps'] if r['status'] == 'CUTOFF' else 0)
        checks['learning_counters'] &= all(learn.get(k, 0) == v for k, v in expected.items())
        checks['learning_counters'] &= 3*m <= learn.get('table_updates', 0) <= 96*m
        updates += len(target); target_sums += target.sum(axis=0); total += 1
        diagnostics.update(observed_afterstates=r['steps'], fitted_afterstates=len(target),
            censored_afterstates=r['steps'] if r['status'] == 'CUTOFF' else 0,
            analytic_goals=int(r['status'] == 'WON'))
        add_cost(cost, row); add_cost(block, row)
        block['total_score'] += r['score']; block['end'] = total
        block['updates'] += m; block['analytic_goals'] += int(r['status'] == 'WON')
        block['censored_afterstates'] += r['steps'] if r['status'] == 'CUTOFF' else 0
        block['target_sums'] = (np.asarray(block['target_sums']) + target.sum(axis=0)).tolist()
        if total in ages:
            prefixes[total] = dict(updates=updates, target_sums=target_sums.tolist(),
                constant=(target_sums / updates).tolist() if updates else [0., 0., 0.],
                transitions=cost['environment_counts']['sampled_transitions'])
        if total % 256 == 0:
            blocks.append(block); block = empty_block(total)
    if block['games']:
        blocks.append(block)
    checks['training_roster'] &= total == episodes
    return dict(checks=checks, cost=cost, blocks=blocks, prefixes=prefixes, diagnostics=dict(diagnostics))


def outer_key(row):
    return row['life'], row['method'], row['checkpoint'], row['query'], row['replica']


def outer_valid(row, expected_updates):
    r = row['result']; method = row['method']; n = r['steps']; query = row['query']
    valid = (compact_valid(row) and row['seed'] == evaluation_seed(row['life'], row['replica'])
        and r['utility'] == utility(r['score'], r['status'], query)
        and all(not r.get(field, {}).get(key, 0) for field in FIELDS
                for key in ('td_updates', 'vector_updates', 'mc_updates', 'component_updates', 'model_spawn_samples')))
    if method in FROZEN:
        return (valid and row['policy'] == query == method[7:] and row['checkpoint'] is None
            and r['source_updates_before'] == r['source_updates_after'] == expected_updates
            and r['policy_counts'].get('choose_calls', 0) == n)
    valid &= r['updates_before'] == r['updates_after'] == expected_updates
    valid &= r['learning_counts'].get('choose_calls', 0) == n * (2 if method == 'GPI' else 1)
    arrays = ('chosen_vectors', 'chosen_values', 'policy_indices')
    if not all(len(row[key]) == n for key in arrays):
        return False
    q = QUERIES[query]
    for score, vector, value, index in zip(row['scores'], row['chosen_vectors'], row['chosen_values'], row['policy_indices']):
        valid &= (len(vector) == 3 and all(math.isfinite(x) for x in vector) and math.isfinite(value)
            and math.isclose(value, q['reward_weight']*(score/2048 + vector[0]) - q['failure_penalty']*vector[1] + q['goal_bonus']*vector[2], rel_tol=1e-12, abs_tol=1e-12)
            and index in ((0, 1) if method == 'GPI' else (POLICIES.index(method[7:]),)))
    return bool(valid)


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
                    values = {field: [] for field in METRICS}
                    for row in rows:
                        r = row['result']
                        for field in METRICS:
                            values[field].append(utility(r['score'], r['status'], query) if field == 'utility' else r[field])
                    lives.append(dict(life=life, complete=complete, games=len(rows),
                        means={field: mean(values[field]) if complete else None for field in METRICS},
                        wins=sum(row['result']['status'] == 'WON' for row in rows),
                        statuses=dict(Counter(row['result']['status'] for row in rows))))
                methods[method][str(age)][query] = dict(lifecycles=lives,
                    lifecycle_mean={field: mean(row['means'][field] for row in lives) for field in METRICS},
                    wins=sum(row['wins'] for row in lives), games=sum(row['games'] for row in lives),
                    complete=all(row['complete'] for row in lives))
    contrasts = {str(age): {'GPI_minus_' + right: {
        query: old.comparisons(methods['GPI'][str(age)][query], methods[right][str(age)][query])
        for query in QUERIES} for right in METHODS if right != 'GPI'} for age in AGES}
    growth = {method: {query: old.comparisons(methods[method]['1024'][query], methods[method]['256'][query])
        for query in QUERIES} for method in LEARNED}
    return dict(methods=methods, comparisons=contrasts, age1024_minus256=growth)


def diagnostic(row, source_game, prefix):
    r = source_game['result']; n = r['steps']; target = suffix_targets(source_game['scores'], r['status'])
    prediction = np.asarray(row['predictions'], dtype=float)
    checks = dict(diagnostic_source_path=(row['life'], row['policy'], row['replica'], row['eval_id']) ==
        (source_game['life'], source_game['policy'], source_game['replica'], source_game['eval_id']),
        diagnostic_training_prefix=row['prefix_updates'] == prefix['updates'] and np.allclose(row['constant'], prefix['constant'], rtol=0., atol=1e-12),
        diagnostic_readonly=(all(not row['learning_counts'].get(key, 0) for key in ('td_updates', 'vector_updates', 'mc_updates', 'component_updates', 'model_spawn_samples'))
            and row['learning_counts'].get('vector_predictions', 0) == n
            and row['learning_counts'].get('component_predictions', 0) == 3*(n-int(r['status'] == 'WON'))
            and row['learning_counts'].get('table_lookups', 0) == 96*(n-int(r['status'] == 'WON'))),
        diagnostic_predictions=prediction.shape == (n, 3) and bool(np.isfinite(prediction).all()))
    if not checks['diagnostic_predictions']:
        return dict(checks=checks, observations=n, samples=0, status=r['status'])
    if r['status'] == 'WON':
        checks['diagnostic_predictions'] &= np.array_equal(prediction[-1], [0., 0., 1.])
    pred = prediction[:len(target)]
    result = dict(checks=checks, observations=n, samples=len(target), status=r['status'],
        sum_squared_error=((pred - target)**2).sum(axis=0).tolist(),
        zero_sum_squared_error=(target**2).sum(axis=0).tolist(),
        constant_sum_squared_error=((np.asarray(prefix['constant']) - target)**2).sum(axis=0).tolist(),
        out_of_range=[int(((pred[:, 0] < 0)).sum()), int(((pred[:, 1] < 0) | (pred[:, 1] > 1)).sum()),
                      int(((pred[:, 2] < 0) | (pred[:, 2] > 1)).sum())],
        failure_success_sum_squared_error=float(((pred[:, 1]+pred[:, 2]-1)**2).sum()))
    return result


def diagnostic_summaries(rows):
    groups = []
    for life in LIVES:
        for policy in POLICIES:
            for age in AGES:
                group = [r for r in rows if (r['life'], r['policy'], r['checkpoint']) == (life, policy, age)]
                n = sum(r['samples'] for r in group)
                complete = len(group) == REPLICAS and all(all(r['checks'].values()) for r in group)
                sums = {name: sum((np.asarray(r.get(name, [0., 0., 0.])) for r in group), np.zeros(3)).tolist()
                    for name in ('sum_squared_error', 'zero_sum_squared_error', 'constant_sum_squared_error', 'out_of_range')}
                groups.append(dict(life=life, policy=policy, checkpoint=age, complete=complete,
                    games=len(group), samples=n, **sums,
                    mse={label: {c: sums[name][i]/n if complete and n else None for i, c in enumerate(COMPONENTS)}
                        for label, name in (('learned', 'sum_squared_error'), ('zero', 'zero_sum_squared_error'), ('constant', 'constant_sum_squared_error'))},
                    failure_success_mse=sum(r.get('failure_success_sum_squared_error', 0.) for r in group)/n if complete and n else None))
    aggregate = {policy: {str(age): {label: {component: mean(row['mse'][label][component] for row in groups
        if row['policy'] == policy and row['checkpoint'] == age) for component in COMPONENTS}
        for label in ('learned', 'zero', 'constant')} for age in AGES} for policy in POLICIES}
    return dict(lifecycles=groups, lifecycle_mean_mse=aggregate)


def model_valid(directory, cp):
    path = directory / cp['model_ref']
    if not path.exists() or path.stat().st_size != cp['model_bytes']:
        return False
    with np.load(path, allow_pickle=False) as data:
        meta = json.loads(str(data['metadata'])); indices, values = data['indices'], data['values']
        return (meta['schema'] == 'acfqp.policy_consequences.v126' and meta['radix'] == 11
            and meta['components'] == list(COMPONENTS) and meta['updates'] == cp['updates']
            and meta['head_updates'] == [cp['updates']] * 3 and len(indices) == len(values)
            and bool(np.isfinite(values).all()) and bool((indices >= 0).all())
            and bool((indices < 3*4*11**6).all()) and bool((np.diff(indices) > 0).all())
            and cp['save_counts'].get('checkpoint_saves') == 1
            and cp['save_counts'].get('checkpoint_scanned_parameters') == 3*4*11**6
            and cp['save_counts'].get('checkpoint_saved_parameters') == len(indices))


def analyze(directory):
    directory = Path(directory).resolve()
    run = json.loads((directory / 'run.json').read_text())
    source = json.loads((directory / 'source_capsule.json').read_text())
    expected_settings = dict(lifecycles=list(LIVES), policies={p: QUERIES[p] for p in POLICIES},
        queries=QUERIES, ages=list(AGES), train_episodes=1024, replicas=REPLICAS,
        max_steps=MAX_STEPS, workers=4, block_size=256, alpha=.0025, p_four=.1, version_base=BASE)
    checks = dict(frozen_settings=run['settings'] == expected_settings,
        source_roster=source['schema'] == 'acfqp.policy_consequences.v126.source'
            and len(source['snapshots']) == 4 and {s['life'] for s in source['snapshots']} == set(LIVES)
            and all(set(s) == {'life', 'rule', 'models'} and set(s['models']) == set(POLICIES) for s in source['snapshots']),
        lifecycle_roster=len(run['lifecycles']) == 4 and {s['life'] for s in run['lifecycles']} == set(LIVES),
        inherited_costs=run['inherited_costs'] == source['inherited_costs'],
        source_models=True, policy_roster=True, source_policy_immutable=True,
        training_blocks=True, checkpoint_roster=True, checkpoint_prefixes=True,
        saved_models=True, setup_counts=True, outer_roster=True, outer_readonly=True,
        outer_eval_ids=True, diagnostic_roster=True, all_outer_terminal=True)
    inherited_transitions = sum(b['environment_counts']['sampled_transitions']
        for life in source['inherited_costs']['v120_training']
        for policy in life['queries'].values() for b in policy['training_blocks'])
    checks['inherited_costs'] &= inherited_transitions == 22124667
    sources = {s['life']: s for s in source['snapshots']}
    training, diagnostic_rows, indexed, valid = [], [], {}, {}
    costs = dict(training=new_cost(), outer=new_cost(), outer_by_method={m: new_cost() for m in METHODS},
        diagnostics_counts=Counter(), diagnostics_seconds=0.,
        source_load_counts=Counter(), source_load_seconds=0., source_setup_counts=Counter(), source_setup_seconds=0.,
        learner_setup_counts=Counter(), learner_setup_seconds=0., model_save_counts=Counter(), model_save_seconds=0.,
        retained_model_bytes=0, retained_model_files=0, peak_weight_bytes_per_life=0)
    for life in run['lifecycles']:
        ident = life['life']; supplied = sources[ident]
        checks['policy_roster'] &= set(life['policies']) == set(POLICIES)
        checkpoints, prefixes = {}, {}
        for policy in POLICIES:
            data = life['policies'][policy]; src = supplied['models'][policy]
            checks['source_models'] &= (Path(src['path']) == ROOT / 'reports/controlled_predictive_ntuple_learning_v120' / f'life_{ident}' / policy / 'checkpoint_4096.npz'
                and old.model_valid(directory, dict(model_ref=src['path'], updates=src['updates'])))
            checks['source_policy_immutable'] &= data['source_updates_before'] == data['source_updates_after'] == src['updates']
            # Training files contain both policies. Scan in streaming order, selecting one policy at a time.
            rows = (r for r in read_rows(directory / life['training_trace']) if r['policy'] == policy)
            found = inspect_training(rows, ident, policy, src['updates'])
            for key, value in found['checks'].items():
                checks[key] = checks.get(key, True) and value
            merge_cost(costs['training'], found['cost'])
            training.append(dict(life=ident, policy=policy, **found))
            prefixes[policy] = found['prefixes']
            checks['training_blocks'] &= len(data['training_blocks']) == len(found['blocks'])
            for stored, actual in zip(data['training_blocks'], found['blocks']):
                checks['training_blocks'] &= all(actual[key] == value for key, value in stored.items())
            checks['checkpoint_roster'] &= [cp['age'] for cp in data['checkpoints']] == list(AGES)
            checkpoints[policy] = {cp['age']: cp for cp in data['checkpoints']}
            for cp in data['checkpoints']:
                prefix = prefixes[policy].get(cp['age'], {})
                checks['checkpoint_prefixes'] &= cp['updates'] == prefix.get('updates') and np.allclose(cp['constant'], prefix.get('constant', [math.inf]*3), rtol=0., atol=1e-12)
                checks['saved_models'] &= model_valid(directory, cp)
                costs['retained_model_bytes'] += cp['model_bytes']; costs['retained_model_files'] += 1
                costs['model_save_seconds'] += cp['save_seconds']; costs['model_save_counts'].update(cp['save_counts'])
            for key in ('source_load', 'source_setup', 'learner_setup'):
                costs[key + '_counts'].update(data[key + '_counts'])
                costs[key + '_seconds'] += data[key + '_seconds']
            checks['setup_counts'] &= (data['source_load_counts'].get('checkpoint_loads') == 1
                and data['source_load_counts'].get('checkpoint_loaded_parameters') == src['nonzero_weights']
                and data['source_setup_counts'].get('allocated_weight_bytes') == 4*11**6*8
                and data['learner_setup_counts'].get('allocated_weight_bytes') == 3*4*11**6*8)
        raw = list(read_rows(directory / life['control_trace']))
        expected = {(ident, m, None, m[7:], r) for m in FROZEN for r in range(REPLICAS)}
        expected |= {(ident, m, age, q, r) for m in LEARNED for age in AGES for q in QUERIES for r in range(REPLICAS)}
        keys = [outer_key(row) for row in raw]
        checks['outer_roster'] &= len(keys) == len(set(keys)) == len(expected) and set(keys) == expected
        ids = [r['eval_id'] for r in raw]
        checks['outer_eval_ids'] &= len(ids) == len(set(ids))
        for row in raw:
            key = outer_key(row)
            updates = (supplied['models'][row['policy']]['updates'] if row['method'] in FROZEN
                else [checkpoints[p][row['checkpoint']]['updates'] for p in POLICIES])
            ready = outer_valid(row, updates)
            checks['outer_readonly'] &= ready
            terminal = row['result']['status'] in ('WON', 'LOST')
            checks['all_outer_terminal'] &= terminal
            indexed[key], valid[key] = row, ready and terminal
            add_cost(costs['outer'], row); add_cost(costs['outer_by_method'][row['method']], row)
        raw_diag = list(read_rows(directory / life['diagnostic_trace']))
        keys = [(r['life'], r['policy'], r['checkpoint'], r['replica']) for r in raw_diag]
        expected_diag = {(ident, p, age, r) for p in POLICIES for age in AGES for r in range(REPLICAS)}
        checks['diagnostic_roster'] &= len(keys) == len(set(keys)) == len(expected_diag) and set(keys) == expected_diag
        for row in raw_diag:
            key = ident, 'FROZEN_' + row['policy'], None, row['policy'], row['replica']
            if key not in indexed:
                checks['diagnostic_roster'] = False
                continue
            found = diagnostic(row, indexed[key], prefixes[row['policy']][row['checkpoint']])
            for key, value in found['checks'].items():
                checks[key] = checks.get(key, True) and value
            diagnostic_rows.append(dict(life=ident, policy=row['policy'], checkpoint=row['checkpoint'],
                replica=row['replica'], **found))
            costs['diagnostics_counts'].update(row['learning_counts']); costs['diagnostics_seconds'] += row['seconds']
        checks['setup_counts'] &= life['peak_weight_bytes'] == 8*4*11**6*8
        costs['peak_weight_bytes_per_life'] = max(costs['peak_weight_bytes_per_life'], life['peak_weight_bytes'])
    costs['physical_outer_games'] = costs['outer']['games']
    costs['logical_outer_rows'] = sum(costs['outer_by_method'][m]['games'] * (len(QUERIES)*len(AGES) if m in FROZEN else 1) for m in METHODS)
    costs['actual_environment_transitions'] = costs['training']['environment_counts']['sampled_transitions'] + costs['outer']['environment_counts']['sampled_transitions']
    costs['model_spawn_samples'] = sum(c[field].get('model_spawn_samples', 0)
        for c in (costs['training'], costs['outer']) for field in FIELDS) + costs['diagnostics_counts'].get('model_spawn_samples', 0)
    checks['physical_and_logical_counts'] = costs['physical_outer_games'] == 832 and costs['logical_outer_rows'] == 1280
    checks['training_attempts'] = costs['training']['games'] == 8192
    complete = run['status'] == 'complete' and all(v for k, v in checks.items() if k != 'all_outer_terminal')
    return dict(schema='acfqp.policy_consequences.v126.analysis', complete=bool(complete),
        primary_complete=bool(complete and checks['all_outer_terminal']),
        checks={k: bool(v) for k, v in checks.items()}, control=summarize(indexed, valid),
        training=training, diagnostics=diagnostic_summaries(diagnostic_rows), costs=costs,
        inherited_work=dict(v120_training_transitions=inherited_transitions,
            deterministic_prior=source['inherited_costs']['deterministic_prior']), seconds=run['seconds'],
        scope='Fixed-policy joint consequences and frozen query readouts. Source-path errors do not establish GPI coverage; four source histories, no retuning or source-cost refund.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    report = analyze(parser.parse_args().run_dir)
    output = parser.parse_args().run_dir / 'analysis.json'
    output.write_text(json.dumps(report, allow_nan=False, indent=2) + '\n')
    print(json.dumps(dict(complete=report['complete'], primary_complete=report['primary_complete'],
        checks=report['checks'], output=str(output)), allow_nan=False))
