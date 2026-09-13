"""An H2 root readout using complementary halves of retained H1 integer counts."""

from collections import Counter
import math
import random
from time import perf_counter

from .controlled_predictive_partial_v12 import _terminal, row_seed

TOLERANCE = 1e-10


def _key(key):
    return [key[0], list(key[1])]


def _input(state, query_name):
    root = state.root
    if root[0] != 2 or state.profiles[root].status != 'ACTIVE':
        raise ValueError('V38 requires a retained ACTIVE H2 root')
    cache = state.caches[query_name]
    if cache.dirty:
        raise ValueError('V38 requires the already restored and solved pooled cache')
    return root, cache, state.queries[query_name]


def pooled_root_readout(state, query_name):
    started = perf_counter()
    root, cache, _ = _input(state, query_name)
    values = {action: cache.q_lower[root, action] for action in sorted(state.profiles[root].legal_actions)}
    return {'root_action': cache.policy[root], 'root_values': values,
        'validation': {'passed': True, 'checks': {'exact_pooled_argmax': cache.policy[root] == min(values, key=lambda action: (-values[action], action))}},
        'accounting': {'whole_readout_seconds': perf_counter() - started,
            'root_action_values_read': len(values), 'new_provider_calls': 0, 'new_sampling_calls': 0, 'new_physical_draws': 0}}


def split_counts(counts, partition_seed, suffix_seed, key, action):
    """Uniform N/2 labels without replacement; B is the exact count complement."""
    ordered = sorted(counts.items())
    total = sum(count for _, count in ordered)
    if not ordered or total % 256 or any(type(count) is not int or count <= 0 for _, count in ordered):
        raise ValueError('V38 requires positive pooled integer counts from complete 256-draw batches')
    half = total // 2
    seed = row_seed(partition_seed * 1_000_000 + suffix_seed, key, action)
    if len(ordered) == 1:
        selected = Counter({0: half})
    else:
        selected = Counter(random.Random(seed).sample(range(len(ordered)), counts=[count for _, count in ordered], k=half))
    a = {outcome: selected[index] for index, (outcome, _) in enumerate(ordered)}
    b = {outcome: count - a[outcome] for outcome, count in ordered}
    return a, b, {'row_key': [_key(key), action], 'row_seed': seed,
        'pooled_count': total, 'fold_count': half,
        'outcomes': [{'successor': _key(outcome[0]), 'reward': outcome[1], 'pooled_count': count, 'fold_A_count': a[outcome]}
            for outcome, count in ordered],
        'random_partition': len(ordered) > 1}


def crossfit_root_readout(state, query_name, partition_seed, suffix_seed):
    """Change only root scores; H1 deployment remains the pooled policy."""
    started = perf_counter()
    root, cache, query = _input(state, query_name)
    work, seconds = Counter(), Counter()
    split_rows, folded = [], {}
    for (key, action), counts in sorted(state.outcome_counts.items()):
        if key[0] != 1:
            continue
        tick = perf_counter()
        a, b, retained = split_counts(counts, partition_seed, suffix_seed, key, action)
        seconds['integer_partition'] += perf_counter() - tick
        split_rows.append(retained)
        work.update(partitioned_h1_rows=1, pooled_integer_entries_read=len(counts),
            retained_draws_partitioned=retained['pooled_count'],
            random_partition_rows=int(retained['random_partition']),
            randomized_fold_A_labels=retained['fold_count'] if retained['random_partition'] else 0)
        tick = perf_counter()
        def value(fold):
            return math.fsum(count / retained['fold_count'] * (query.reward_weight * reward + _terminal(state.profiles[successor].status, query))
                for (successor, reward), count in fold.items() if count)
        folded[key, action] = value(a), value(b)
        seconds['fold_action_values'] += perf_counter() - tick
    tick = perf_counter()
    continuations, values, residuals = [], {}, []
    for key in sorted(state.profiles):
        if key[0] != 1:
            continue
        profile = state.profiles[key]
        row = {'key': _key(key), 'status': profile.status, 'pooled_value': cache.lower[key]}
        if profile.status != 'ACTIVE':
            cross = _terminal(profile.status, query)
        else:
            q_a, q_b = {}, {}
            for action in sorted(profile.legal_actions):
                pair = key, action
                q_a[action], q_b[action] = folded[pair] if pair in folded else (cache.q_lower[pair], cache.q_lower[pair])
                residuals.append(abs(.5 * math.fsum((q_a[action], q_b[action])) - cache.q_lower[pair]))
            chosen_a = min(q_a, key=lambda action: (-q_a[action], action))
            chosen_b = min(q_b, key=lambda action: (-q_b[action], action))
            cross = .5 * math.fsum((q_b[chosen_a], q_a[chosen_b]))
            row.update(pooled_action=cache.policy[key], fold_actions=[chosen_a, chosen_b],
                fold_q_values={action: {'A': q_a[action], 'B': q_b[action], 'observed': (key, action) in state.rows} for action in q_a})
            work['active_h1_values'] += 1
        row.update(cross_value=cross, cross_minus_pooled=cross - cache.lower[key])
        continuations.append(row)
        values[key] = cross
    seconds['cross_continuation_values'] += perf_counter() - tick
    tick = perf_counter()
    root_values = {}
    for action in sorted(state.profiles[root].legal_actions):
        pair = root, action
        if pair not in state.rows:
            root_values[action] = cache.q_lower[pair]
            continue
        root_values[action] = math.fsum(probability * (query.reward_weight * reward + values[successor])
            for probability, successor, reward in state.rows[pair])
        work['root_empirical_support_entries_read'] += len(state.rows[pair])
    chosen = min(root_values, key=lambda action: (-root_values[action], action))
    seconds['root_readout'] += perf_counter() - tick
    checks = {'complementary_equal_integer_halves': all(
        sum(item['fold_A_count'] for item in row['outcomes']) == row['fold_count'] and
        all(0 <= item['fold_A_count'] <= item['pooled_count'] for item in row['outcomes']) and row['fold_count'] * 2 == row['pooled_count']
        for row in split_rows),
        'pooled_fold_average': max(residuals, default=0.) <= TOLERANCE,
        'cross_continuation_not_above_pooled': all(row['cross_minus_pooled'] <= TOLERANCE for row in continuations),
        'cross_root_not_above_pooled': all(value <= cache.q_lower[root, action] + TOLERANCE for action, value in root_values.items())}
    return {'root_action': chosen, 'root_values': root_values, 'partition_seed': partition_seed, 'suffix_seed': suffix_seed,
        'split_rows': split_rows, 'continuations': continuations,
        'validation': {'passed': all(checks.values()), 'checks': checks, 'maximum_fold_average_residual': max(residuals, default=0.)},
        'accounting': {'whole_readout_seconds': perf_counter() - started, 'seconds_by_stage': dict(seconds), **dict(work),
            'new_provider_calls': 0, 'new_sampling_calls': 0, 'new_physical_draws': 0}}
