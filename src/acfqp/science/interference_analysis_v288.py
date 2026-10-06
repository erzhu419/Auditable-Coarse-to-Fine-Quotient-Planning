"""Equal-board, equal-action aggregation of isolated scalar-critic updates.

Each donor update starts from the original source critic. Recipient actions
are averaged within boards before donor actions and boards are averaged.
Protected zero-kernel pairs remain part of every corresponding estimand.
"""
from collections import defaultdict
import random
from statistics import mean

GROUPS = ('uniform', 'competition')
CATEGORIES = ('SELF', 'SAME_BOARD_OTHER_ACTION', 'OTHER_BOARD')
ENDPOINTS = ('mean_label_delta_mse', 'single_label_mean_delta_mse', 'empirical_noise_penalty')
BOOTSTRAP_SEED = 28800001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def pair_category(pair):
    if pair['donor_state_id'] != pair['target_state_id']:
        return 'OTHER_BOARD'
    return ('SELF' if pair['donor_action'] == pair['target_action']
            else 'SAME_BOARD_OTHER_ACTION')


def _metrics(pair):
    baseline = pair['baseline_validation_mse']
    return dict(baseline_validation_mse=baseline,
        **{name: pair[name] for name in ENDPOINTS},
        mean_label_validation_mse=baseline+pair['mean_label_delta_mse'],
        single_label_mean_validation_mse=baseline+pair['single_label_mean_delta_mse'],
        zero_kernel_fraction=float(pair['kernel'] == 0),
        positive_mean_label_delta_fraction=float(pair['mean_label_delta_mse'] > 0.))


def _average(rows):
    return {name: mean(row[name] for row in rows) for name in rows[0]}


def aggregate_category(pairs, category):
    """Recipient actions -> boards -> donor actions -> boards, all equal."""
    rows = [pair for pair in pairs if pair_category(pair) == category]
    donors = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for pair in rows:
        donors[pair['donor_state_id']][pair['donor_action']][pair['target_state_id']].append(_metrics(pair))
    board_means = []
    for actions in donors.values():
        action_means = []
        for target_boards in actions.values():
            action_means.append(_average([_average(target_actions)
                                         for target_actions in target_boards.values()]))
        board_means.append(_average(action_means))
    return dict(metrics=_average(board_means), pairs=len(rows), donor_boards=len(donors),
        recipient_boards=len({row['target_state_id'] for row in rows}),
        zero_kernel_pairs=sum(row['kernel'] == 0 for row in rows),
        positive_mean_label_pairs=sum(row['mean_label_delta_mse'] > 0. for row in rows),
        negative_mean_label_pairs=sum(row['mean_label_delta_mse'] < 0. for row in rows))


def _bootstrap(records, values, draws):
    parents = {parent: [value for row, value in zip(records, values) if row['parent'] == parent]
               for parent in sorted({row['parent'] for row in records})}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group, k=len(group)))
        for group in parents.values()) for _ in range(draws))
    def quantile(q):
        position = (len(samples)-1)*q
        lo, hi = int(position), min(int(position)+1, len(samples)-1)
        return samples[lo] + (samples[hi]-samples[lo])*(position-lo)
    return dict(mean=mean(values), ci95=[quantile(.025), quantile(.975)],
        lifecycle_deltas={str(row['lifecycle']): value for row, value in zip(records, values)},
        improved_equal_worse=[sum(value < 0. for value in values),
            sum(value == 0. for value in values), sum(value > 0. for value in values)],
        adverse_lifecycles=[row['lifecycle'] for row, value in zip(records, values) if value > 0.],
        parent_mean_deltas={str(parent): mean(group) for parent, group in parents.items()},
        interval_scope=INTERVAL_SCOPE)


def summarize(lifecycles, draws=20000):
    """Summarize life,parent,groups[group].pairs without fitting or new samples.

    Pair rows contain donor_state_id/action, target_state_id/action, kernel,
    baseline_validation_mse and the three ENDPOINTS. Positive MSE differences
    mean harm; single-minus-mean is a separate empirical noise diagnostic.
    """
    rows = sorted(lifecycles, key=lambda row: row['lifecycle'])
    parents = [row['parent'] for row in rows]
    if (len(rows) != 16 or len({row['lifecycle'] for row in rows}) != 16
            or len(set(parents)) != 4 or any(parents.count(parent) != 4 for parent in set(parents))):
        raise ValueError('V288 requires sixteen lifecycles under four fixed parents')
    records = [dict(lifecycle=row['lifecycle'], parent=row['parent'], groups={group:
        dict(categories={category: aggregate_category(row['groups'][group]['pairs'], category)
                         for category in CATEGORIES}) for group in GROUPS}) for row in rows]
    groups = {}
    for group in GROUPS:
        categories = {}
        for category in CATEGORIES:
            results = [row['groups'][group]['categories'][category] for row in records]
            diagnostics = {name: _bootstrap(records,
                [result['metrics'][name] for result in results], draws) for name in ENDPOINTS}
            categories[category] = dict(metrics=_average([result['metrics'] for result in results]),
                paired_diagnostics=diagnostics, **{name: sum(result[name] for result in results)
                for name in ('pairs', 'zero_kernel_pairs', 'positive_mean_label_pairs',
                             'negative_mean_label_pairs')})
        groups[group] = dict(categories=categories)
    return dict(groups=groups, by_lifecycle=records,
        primary_endpoint=dict(group='uniform', category='OTHER_BOARD', metric='mean_label_delta_mse'),
        bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        estimator='RECIPIENT_ACTION_BOARD_THEN_DONOR_ACTION_BOARD_THEN_LIFECYCLE',
        sign='Positive MSE difference is harm; all zero-kernel protected pairs are included.')
