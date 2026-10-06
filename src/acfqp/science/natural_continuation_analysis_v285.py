"""Fixed state selection and independent continuation validation for V285.

Discovery chooses an action from total utility. Validation uses its independent
batch to compare that action and the two pre-existing recommendations against
the full ORACLE_P proxy. Each selection group remains a separate estimand.
"""
from collections import defaultdict
from math import sqrt
import random
from statistics import mean, stdev

PHASES = ('A', 'B', 'A_prime')
GROUPS = ('uniform', 'competition')
CONTRASTS = ('winner_minus_proxy', 'short_minus_proxy', 'retained_minus_proxy')
BOOTSTRAP_SEED = 28500001


def select_indices(n, competition_indices):
    """Four index-spaced states and four tail-override states, without outcomes."""
    uniform = tuple(k*n//4 for k in range(4))
    candidates = sorted(set(competition_indices) - set(uniform))
    if n < 4 or len(candidates) < 4:
        raise ValueError('V285 requires four distinct uniform and competition states')
    return dict(uniform=uniform,
        competition=tuple(candidates[k*len(candidates)//4] for k in range(4)))


def _paired_difference(values, left, right, replicas):
    differences = [values[left][i] - values[right][i] for i in range(replicas)]
    return dict(mean=mean(differences), paired_mc_se=stdev(differences)/sqrt(replicas))


def _state_result(state, records, replicas):
    actions = sorted(state['legal_actions'])
    values = {batch: {action: {} for action in actions}
              for batch in ('discovery', 'validation')}
    for row in records:
        bucket = values[row['batch']][row['action']]
        index = row['replica_index']
        if index in bucket:
            raise ValueError('duplicate continuation replica')
        bucket[index] = row['total_utility']
    expected = set(range(replicas))
    if any(set(bucket) != expected for batch in values.values() for bucket in batch.values()):
        raise ValueError('each action needs both complete independent replica batches')
    discovery = {action: mean(bucket.values()) for action, bucket in values['discovery'].items()}
    validation = {action: mean(bucket.values()) for action, bucket in values['validation'].items()}
    winner = min(actions, key=lambda action: (-discovery[action], action))
    alternatives = (winner, state['short_action'], state['retained_action'])
    contrasts = {name: _paired_difference(values['validation'], action,
        state['proxy_action'], replicas) for name, action in zip(CONTRASTS, alternatives)}
    return dict(state, winner=winner, discovery_means=discovery,
        validation_means=validation, contrasts=contrasts)


def _mean_contrasts(rows):
    return {name: mean(row['contrasts'][name] for row in rows) for name in CONTRASTS}


def _bootstrap(records, name, draws):
    deltas = [row['contrasts'][name] for row in records]
    groups = {parent: [row['contrasts'][name] for row in records if row['parent'] == parent]
              for parent in sorted({row['parent'] for row in records})}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(values, k=len(values)))
        for values in groups.values()) for _ in range(draws))
    def quantile(q):
        position = (len(samples)-1)*q
        lo = int(position)
        hi = min(lo+1, len(samples)-1)
        return samples[lo] + (samples[hi]-samples[lo])*(position-lo)
    return dict(mean=mean(deltas), ci95=[quantile(.025), quantile(.975)],
        lifecycle_deltas={str(row['lifecycle']): delta for row, delta in zip(records, deltas)},
        improved_equal_worse=[sum(x > 0. for x in deltas), sum(x == 0. for x in deltas),
                              sum(x < 0. for x in deltas)],
        adverse_lifecycles=[row['lifecycle'] for row, value in zip(records, deltas) if value < 0.],
        parent_mean_deltas={str(parent): mean(values) for parent, values in groups.items()},
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS')


def summarize(states, rollouts, parents, replicas=32, draws=20000):
    """Analyze complete paired total-utility receipts, without new samples.

    States contain state_id, lifecycle, phase, group, legal_actions,
    proxy_action, short_action and retained_action. Rollouts contain state_id,
    action, batch (discovery/validation), replica_index and total_utility.
    Parents maps the sixteen lifecycle IDs to their four frozen leaf parents.
    """
    parents = {int(life): parent for life, parent in parents.items()}
    if (len(parents) != 16 or len(set(parents.values())) != 4
            or any(list(parents.values()).count(p) != 4 for p in set(parents.values()))):
        raise ValueError('V285 requires sixteen lifecycles under four fixed parents')
    by_id = {state['state_id']: state for state in states}
    if len(by_id) != len(states):
        raise ValueError('selected state IDs must be distinct')
    buckets = defaultdict(list)
    for row in rollouts:
        if row['state_id'] not in by_id:
            raise ValueError('continuation row has no selected state')
        buckets[row['state_id']].append(row)
    results = [_state_result(state, buckets[state['state_id']], replicas) for state in states]
    groups = {}
    for group in GROUPS:
        lifecycles = []
        for life in sorted(parents):
            phases = {}
            for phase in PHASES:
                rows = [row for row in results if row['group'] == group
                        and row['lifecycle'] == life and row['phase'] == phase]
                if len(rows) != 4:
                    raise ValueError('each lifecycle/phase/selection group needs exactly four states')
                phases[phase] = dict(states=4, contrasts={name:
                    mean(row['contrasts'][name]['mean'] for row in rows) for name in CONTRASTS})
            lifecycles.append(dict(lifecycle=life, parent=parents[life], phases=phases,
                contrasts=_mean_contrasts(list(phases.values()))))
        contrasts = {name: dict(_bootstrap(lifecycles, name, draws), phases={phase:
            _bootstrap([dict(lifecycle=row['lifecycle'], parent=row['parent'],
                contrasts=row['phases'][phase]['contrasts']) for row in lifecycles], name, draws)
            for phase in PHASES}) for name in CONTRASTS}
        groups[group] = dict(states=16*3*4, contrasts=contrasts, by_lifecycle=lifecycles)
    if len(results) != 16*3*8:
        raise ValueError('V285 requires exactly the two frozen selection groups')
    return dict(states=len(results), rollouts=sum(len(rows) for rows in buckets.values()),
        replicas_per_action_per_batch=replicas, bootstrap_draws=draws,
        bootstrap_seed=BOOTSTRAP_SEED, state_results=results, groups=groups)
