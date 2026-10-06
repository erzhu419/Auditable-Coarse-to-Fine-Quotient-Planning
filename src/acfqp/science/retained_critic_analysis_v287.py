"""Fixed-history critic fit diagnostics and independent static H2 game outcomes.

Prediction errors average episodes first, then equally weighted lifecycles.
Only new-game utility defines the primary contribution. Conditional intervals
resample whole lifecycles within each of four existing source parents.
"""
from math import floor
import random
from statistics import mean

ARMS = ('FROZEN', 'SHADOW_TD', 'EPISODIC_MC')
PAIRS = (('EPISODIC_MC', 'FROZEN'), ('SHADOW_TD', 'FROZEN'), ('EPISODIC_MC', 'SHADOW_TD'))
METRICS = ('bias', 'mse', 'mae')
BOOTSTRAP_SEED = 28700001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def _game_summary(games, lifecycle):
    seeds = [287500000000+lifecycle*1000000+i for i in range(16)]
    if len(games) != 16 or [g['seed'] for g in games] != seeds:
        raise ValueError('V287 needs the same sixteen fresh evaluation seeds per arm/lifecycle')
    if any(g['status'] not in ('WON', 'LOST', 'CUTOFF') for g in games):
        raise ValueError('evaluation games must have explicit terminal or cutoff status')
    return dict(games=16, mean_game_utility=mean(g['utility'] for g in games),
        wins=sum(g['status'] == 'WON' for g in games),
        losses=sum(g['status'] == 'LOST' for g in games),
        cutoffs=sum(g['status'] == 'CUTOFF' for g in games),
        steps=sum(g['steps'] for g in games))


def _heldout_summary(games):
    if not games or any(g['count'] <= 0 for g in games):
        raise ValueError('heldout needs complete episodes with scored afterstates')
    return dict(games=len(games), samples=sum(g['count'] for g in games),
        **{key: mean(g[key] for g in games) for key in METRICS})


def _pooled_game_summary(rows):
    return dict(mean_game_utility=mean(r['mean_game_utility'] for r in rows),
        **{k: sum(r[k] for r in rows) for k in ('games', 'wins', 'losses', 'cutoffs', 'steps')})


def _bootstrap(records, values, draws):
    groups = {p: [v for r, v in zip(records, values) if r['parent'] == p] for p in range(4)}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group, k=4)) for group in groups.values()) for _ in range(draws))
    def quantile(q):
        position = (draws-1)*q
        lo, hi = floor(position), min(floor(position)+1, draws-1)
        return samples[lo]+(samples[hi]-samples[lo])*(position-lo)
    return dict(mean=mean(values), ci95=[quantile(.025), quantile(.975)],
        lifecycle_deltas={str(r['lifecycle']): v for r, v in zip(records, values)},
        positive_equal_negative=[sum(v > 0 for v in values), sum(v == 0 for v in values), sum(v < 0 for v in values)],
        parent_mean_deltas={str(p): mean(group) for p, group in groups.items()},
        interval_scope=INTERVAL_SCOPE)


def summarize(lifecycles, draws=20000):
    """Read arms[*].game_summaries and arms[*].heldout.game_metrics.

    Each heldout row has episode/start/end/count/bias/mse/mae. Training cost,
    critic targets, and aggregate sample-weighted metrics are not outcomes.
    """
    rows = sorted(lifecycles, key=lambda r: r['lifecycle'])
    if (len(rows) != 16 or [r['lifecycle'] for r in rows] != list(range(16))
            or any(r['parent'] != r['lifecycle'] % 4 for r in rows)):
        raise ValueError('V287 needs sixteen lifecycles under their four fixed source parents')
    if draws < 2:
        raise ValueError('bootstrap requires at least two draws')
    records = []
    for row in rows:
        arms, heldout_identity = {}, None
        for arm in ARMS:
            value = row['arms'][arm]
            games = value['heldout']['game_metrics']
            identity = [(g['episode'], g['start'], g['end'], g['count']) for g in games]
            if heldout_identity is None:
                heldout_identity = identity
            elif identity != heldout_identity:
                raise ValueError('critics must score the same heldout episodes and afterstates')
            arms[arm] = dict(_game_summary(value['game_summaries'], row['lifecycle']),
                heldout=_heldout_summary(games))
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], arms=arms))
    arms = {}
    for arm in ARMS:
        values = [r['arms'][arm] for r in records]
        heldout = [r['heldout'] for r in values]
        arms[arm] = dict(_pooled_game_summary(values),
            heldout=dict(games=sum(r['games'] for r in heldout), samples=sum(r['samples'] for r in heldout),
                **{key: mean(r[key] for r in heldout) for key in METRICS}))
    paired, errors = {}, {}
    for left, right in PAIRS:
        name = left+'_minus_'+right
        differences = [r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records]
        contrast = _bootstrap(records, differences, draws)
        contrast['improved_equal_worse'] = contrast.pop('positive_equal_negative')
        contrast['adverse_lifecycles'] = [r['lifecycle'] for r, v in zip(records, differences) if v < 0]
        paired[name] = contrast
        errors[name] = {}
        for key in METRICS:
            differences = [r['arms'][left]['heldout'][key]-r['arms'][right]['heldout'][key] for r in records]
            contrast = _bootstrap(records, differences, draws)
            if key in ('mse', 'mae'):
                contrast['improved_equal_worse'] = [sum(v < 0 for v in differences), sum(v == 0 for v in differences), sum(v > 0 for v in differences)]
                contrast['adverse_lifecycles'] = [r['lifecycle'] for r, v in zip(records, differences) if v > 0]
            errors[name][key] = contrast
    return dict(arms=arms, paired_contrasts=paired, heldout_contrasts=errors,
        primary_contrast='EPISODIC_MC_minus_FROZEN', by_lifecycle=records,
        bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        complete_game_endpoints=not any(r['cutoffs'] for r in arms.values()),
        estimator='EQUAL_EVALUATION_GAMES_THEN_LIFECYCLES',
        heldout_estimator='EQUAL_EPISODES_THEN_LIFECYCLES',
        heldout_sign='Literal left-minus-right errors; negative MSE/MAE is better. Signed bias has no monotone improvement direction.',
        contribution_scope='Same retained behavior and fit history; new static H2 game outcomes. Differences from V286 also change the dataset, and do not isolate actor feedback alone.')
