"""Paired complete-game checkpoint evidence for persistent value learning.

Training returns never enter these estimates. Games are averaged within each
phase, the three phases within each lifecycle, and the sixteen lifecycles.
Uncertainty resamples whole lifecycles within their four fixed source parents.
"""
from math import floor
import random
from statistics import mean

ARMS = ('FROZEN', 'ORDINARY_TD', 'PERSISTENT_TD')
PHASES = ('A', 'B', 'A_prime')
BOOTSTRAP_SEED = 28600001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def _game_summary(games):
    if len(games) != 16:
        raise ValueError('each V286 checkpoint needs sixteen evaluation games')
    return dict(games=len(games), mean_game_utility=mean(game['utility'] for game in games),
        wins=sum(game['status'] == 'WON' for game in games),
        losses=sum(game['status'] == 'LOST' for game in games),
        cutoffs=sum(game['status'] == 'CUTOFF' for game in games),
        steps=sum(game['steps'] for game in games))


def _pooled_summary(rows):
    return dict(mean_game_utility=mean(row['mean_game_utility'] for row in rows),
        **{name: sum(row[name] for row in rows)
           for name in ('games', 'wins', 'losses', 'cutoffs', 'steps')})


def _bootstrap(records, values, draws):
    groups = {parent: [value for row, value in zip(records, values) if row['parent'] == parent]
              for parent in sorted({row['parent'] for row in records})}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group, k=len(group)))
        for group in groups.values()) for _ in range(draws))
    def quantile(q):
        position = (len(samples)-1)*q
        lo, hi = floor(position), min(floor(position)+1, len(samples)-1)
        return samples[lo] + (samples[hi]-samples[lo])*(position-lo)
    return dict(mean=mean(values), ci95=[quantile(.025), quantile(.975)],
        lifecycle_deltas={str(row['lifecycle']): value for row, value in zip(records, values)},
        improved_equal_worse=[sum(value > 0. for value in values),
            sum(value == 0. for value in values), sum(value < 0. for value in values)],
        adverse_lifecycles=[row['lifecycle'] for row, value in zip(records, values) if value < 0.],
        parent_mean_deltas={str(parent): mean(group) for parent, group in groups.items()},
        interval_scope=INTERVAL_SCOPE)


def _contrast(records, left, right, draws, phase=None):
    if phase is None:
        values = [row['arms'][left]['mean_lifecycle_utility']
                  - row['arms'][right]['mean_lifecycle_utility'] for row in records]
    else:
        values = [row['arms'][left]['phases'][phase]['mean_game_utility']
                  - row['arms'][right]['phases'][phase]['mean_game_utility'] for row in records]
    return _bootstrap(records, values, draws)


def summarize(lifecycles, draws=20000):
    """Read phase checkpoint game_summaries and matched final DIRECT games.

    Input rows contain lifecycle, parent, arms[arm].phases[phase].game_summaries
    and direct_final.game_summaries. Each game has seed, utility, status, steps;
    extra training, cost or receipt fields are ignored, never used as outcomes.
    """
    rows = sorted(lifecycles, key=lambda row: row['lifecycle'])
    parents = [row['parent'] for row in rows]
    if (len(rows) != 16 or len({row['lifecycle'] for row in rows}) != 16
            or len(set(parents)) != 4 or any(parents.count(parent) != 4 for parent in set(parents))):
        raise ValueError('V286 requires sixteen lifecycles under four fixed parents')
    records = []
    for row in rows:
        arms = {}
        for arm in ARMS:
            phases = {phase: _game_summary(row['arms'][arm]['phases'][phase]['game_summaries'])
                      for phase in PHASES}
            arms[arm] = dict(_pooled_summary(list(phases.values())), phases=phases,
                mean_lifecycle_utility=mean(phase['mean_game_utility'] for phase in phases.values()))
        for phase in PHASES:
            seeds = [game['seed'] for game in row['arms']['FROZEN']['phases'][phase]['game_summaries']]
            if len(set(seeds)) != 16 or any([game['seed'] for game in
                row['arms'][arm]['phases'][phase]['game_summaries']] != seeds for arm in ARMS[1:]):
                raise ValueError('phase evaluation games must use the same sixteen distinct seeds')
        direct = _game_summary(row['direct_final']['game_summaries'])
        if [game['seed'] for game in row['direct_final']['game_summaries']] != [game['seed'] for game in
                row['arms']['PERSISTENT_TD']['phases']['A_prime']['game_summaries']]:
            raise ValueError('final DIRECT must pair with the learned PERSISTENT_TD H2 snapshot')
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'],
            arms=arms, direct_final=direct))
    arms = {arm: dict(_pooled_summary([row['arms'][arm] for row in records]),
        mean_lifecycle_utility=mean(row['arms'][arm]['mean_lifecycle_utility'] for row in records),
        phases={phase: _pooled_summary([row['arms'][arm]['phases'][phase] for row in records])
                for phase in PHASES}) for arm in ARMS}
    contrasts = {f'{left}_minus_{right}': dict(_contrast(records, left, right, draws),
        phases={phase: _contrast(records, left, right, draws, phase) for phase in PHASES})
        for left, right in (('PERSISTENT_TD', 'ORDINARY_TD'), ('PERSISTENT_TD', 'FROZEN'),
                            ('ORDINARY_TD', 'FROZEN'))}
    planner = _bootstrap(records, [row['arms']['PERSISTENT_TD']['phases']['A_prime']['mean_game_utility']
        - row['direct_final']['mean_game_utility'] for row in records], draws)
    direct = _pooled_summary([row['direct_final'] for row in records])
    return dict(arms=arms, direct_final=direct, paired_contrasts=contrasts,
        primary_contrast='PERSISTENT_TD_minus_ORDINARY_TD', retention_endpoint='A_prime',
        planner_contribution=dict(planner, contrast='PERSISTENT_TD_H2_minus_DIRECT', phase='A_prime'),
        by_lifecycle=records, bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        complete_game_endpoints=not any(arm['cutoffs'] for arm in arms.values()) and not direct['cutoffs'],
        estimator='EQUAL_PHASE_CHECKPOINT_GAME_UTILITY')
