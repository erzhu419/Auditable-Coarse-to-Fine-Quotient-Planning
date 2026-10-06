"""Fixed-panel readouts of the complete chronological V287 MC replay.

Panel metrics are supplied as anchor-within-game, then heldout-game means.
Every fitting-game prefix remains descriptive; only the final prefix defines
the primary endpoint. H2 reference utility belongs to the old continuation.
"""
from math import ceil
import random
from statistics import mean

import numpy as np

ANCHOR_METRICS = ('bias', 'mse', 'mae')
CHECKPOINT_FRACTIONS = (0., .25, .5, .75, 1.)
H2_ENDPOINTS = ('validation_utility_delta', 'action_disagreement')
BOOTSTRAP_SEED = 28900001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def select_anchor_indices(dataset, goal_rank=11):
    """Select up to four time-spaced nonwinning afterstates per heldout game.

    Required dataset fields are afterstates, exclusive cumulative ends and
    fit_game_count. Selection uses board ranks and chronology, never labels.
    """
    boards, ends = dataset['afterstates'], dataset['ends']
    selected = []
    for game in range(dataset['fit_game_count'], len(ends)):
        start, end = (int(ends[game-1]) if game else 0), int(ends[game])
        eligible = np.flatnonzero(np.max(boards[start:end], axis=1) < goal_rank) + start
        n, m = len(eligible), min(4, len(eligible))
        if not m:
            raise ValueError('Heldout game has no nonwinning afterstate')
        positions = [0] if m == 1 else [k*(n-1)//(m-1) for k in range(m)]
        selected.extend(int(eligible[position]) for position in positions)
    return np.asarray(selected, dtype=np.int64)


def _average(metrics):
    return {name: mean(row[name] for row in metrics) for name in metrics[0]}


def _bootstrap(records, values, draws, direction=None):
    groups = {parent: [value for row, value in zip(records, values) if row['parent'] == parent]
              for parent in sorted({row['parent'] for row in records})}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group, k=len(group))) for group in groups.values())
                     for _ in range(draws))

    def quantile(q):
        position = (len(samples)-1)*q
        lower, upper = int(position), min(int(position)+1, len(samples)-1)
        return samples[lower] + (samples[upper]-samples[lower])*(position-lower)

    result = dict(mean=mean(values), ci95=[quantile(.025), quantile(.975)],
        lifecycle_values={str(row['lifecycle']): value for row, value in zip(records, values)},
        negative_equal_positive=[sum(value < 0. for value in values),
            sum(value == 0. for value in values), sum(value > 0. for value in values)],
        parent_means={str(parent): mean(group) for parent, group in groups.items()},
        interval_scope=INTERVAL_SCOPE)
    if direction:
        # Convert quality direction only for endpoints with an actual ordering.
        losses = values if direction == 'negative_is_better' else [-value for value in values]
        result.update(improved_equal_worse=[sum(value < 0. for value in losses),
            sum(value == 0. for value in losses), sum(value > 0. for value in losses)],
            adverse_lifecycles=[row['lifecycle'] for row, loss in zip(records, losses) if loss > 0.],
            quality_direction=direction)
    return result


def _life_record(row):
    n = row['fit_game_count']
    snapshots = row['snapshots']
    if [snapshot['completed_fit_games'] for snapshot in snapshots] != list(range(n+1)):
        raise ValueError('Every chronological fitting-game prefix, including zero, is required')
    baseline = {name: float(snapshots[0]['metrics'][name]) for name in ANCHOR_METRICS}
    trajectory = []
    for snapshot in snapshots:
        metrics = {name: float(snapshot['metrics'][name]) for name in ANCHOR_METRICS}
        trajectory.append(dict(completed_fit_games=snapshot['completed_fit_games'],
            cumulative_updates=snapshot['cumulative_updates'],
            cumulative_fit_steps=snapshot['cumulative_fit_steps'], metrics=metrics,
            delta_from_frozen={name: metrics[name]-baseline[name] for name in ANCHOR_METRICS}))
    positive = [point['delta_from_frozen']['mse'] > 0. for point in trajectory]
    first_positive = next((i for i in range(1, n+1) if positive[i]), None)
    final_run = None
    if positive[-1]:
        final_run = n
        while final_run and positive[final_run-1]:
            final_run -= 1
    probes = [dict(completed_fit_games=probe['completed_fit_games'],
                   metrics={name: float(value) for name, value in probe['metrics'].items()})
              for probe in row['h2_probes']]
    if [probe['completed_fit_games'] for probe in probes] != sorted({ceil(f*n) for f in CHECKPOINT_FRACTIONS}):
        raise ValueError('H2 probes must use the five predetermined ceil game prefixes')
    return dict(lifecycle=row['lifecycle'], parent=row['parent'], fit_game_count=n,
        anchor_trajectory=trajectory, h2_probes=probes,
        first_above_baseline_game=first_positive,
        final_above_baseline_run_start_game=final_run)


def summarize(lifecycles, draws=20000):
    """Aggregate fixed-panel final endpoints and retain every signed prefix.

    Input lives have lifecycle, parent, fit_game_count, snapshots and h2_probes.
    Snapshot metrics bias/mse/mae must already average anchors within games,
    then complete heldout games equally. Probes contain same-board, same-p H2
    readouts; validation utility is evaluated with the old fixed continuation.
    """
    rows = sorted(lifecycles, key=lambda row: row['lifecycle'])
    parents = [row['parent'] for row in rows]
    if (len(rows) != 16 or len({row['lifecycle'] for row in rows}) != 16
            or len(set(parents)) != 4 or any(parents.count(parent) != 4 for parent in set(parents))):
        raise ValueError('V289 requires sixteen lifecycles under four fixed parents')
    records = [_life_record(row) for row in rows]
    final_anchor = {name: _bootstrap(records,
        [record['anchor_trajectory'][-1]['delta_from_frozen'][name] for record in records], draws,
        None if name == 'bias' else 'negative_is_better') for name in ANCHOR_METRICS}
    final_h2 = {name: _bootstrap(records,
        [record['h2_probes'][-1]['metrics'][name] for record in records], draws,
        'positive_is_better' if name == 'validation_utility_delta' else None) for name in H2_ENDPOINTS}
    anchor_checkpoints, h2_checkpoints = [], []
    for fraction in CHECKPOINT_FRACTIONS:
        prefixes = [ceil(fraction*record['fit_game_count']) for record in records]
        anchors = [record['anchor_trajectory'][prefix] for record, prefix in zip(records, prefixes)]
        probes = [next(probe for probe in record['h2_probes'] if probe['completed_fit_games'] == prefix)
                  for record, prefix in zip(records, prefixes)]
        counts = {str(record['lifecycle']): prefix for record, prefix in zip(records, prefixes)}
        anchor_checkpoints.append(dict(fraction=fraction, lifecycle_fit_games=counts,
            metrics=_average([point['metrics'] for point in anchors]),
            delta_from_frozen=_average([point['delta_from_frozen'] for point in anchors]),
            mean_cumulative_updates=mean(point['cumulative_updates'] for point in anchors),
            mean_cumulative_fit_steps=mean(point['cumulative_fit_steps'] for point in anchors)))
        h2_checkpoints.append(dict(fraction=fraction, lifecycle_fit_games=counts,
            metrics=_average([probe['metrics'] for probe in probes])))
    return dict(primary_endpoint='FINAL_ANCHOR_MC_MINUS_FROZEN_MSE',
        primary_final_anchor_mse_delta=final_anchor['mse'], final_anchor_contrasts=final_anchor,
        final_h2_diagnostics=final_h2, anchor_checkpoints=anchor_checkpoints,
        h2_checkpoints=h2_checkpoints, by_lifecycle=records,
        bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        estimator='ANCHOR_WITHIN_GAME_THEN_HELDOUT_GAME_THEN_LIFECYCLE',
        signs=dict(mse='Positive delta is harm', mae='Positive delta is harm',
            bias='Signed residual change has no quality ordering',
            validation_utility_delta='Positive is better under the old fixed continuation',
            action_disagreement='Recommendation drift has no quality ordering'),
        prefix_interpretation='Final positive run means every prefix exceeds baseline; not monotone worsening',
        h2_reference='OLD_ORACLE_H2_CONTINUATION_READOUT_NOT_NEW_POLICY_RETURN')
