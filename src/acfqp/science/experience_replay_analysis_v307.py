"""Budget-matched old/new replay with retained A1 and current-policy facts."""
from math import floor
import random
from statistics import mean

ARMS = ('SOURCE', 'A1_FROZEN', 'NEW_ONLY', 'MIXED_REPLAY')
PAIRS = (('MIXED_REPLAY', 'NEW_ONLY'), ('MIXED_REPLAY', 'A1_FROZEN'),
         ('NEW_ONLY', 'A1_FROZEN'), ('MIXED_REPLAY', 'SOURCE'),
         ('NEW_ONLY', 'SOURCE'), ('A1_FROZEN', 'SOURCE'))
PRIMARY_CONTRAST = 'MIXED_REPLAY_minus_NEW_ONLY'
BOOTSTRAP_SEED = 30700001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_A1_AND_V306_CURRENT_DATA_HISTORIES'


def _game_summary(games, lifecycle):
    seeds = [307900000000+lifecycle*1000000+episode for episode in range(32)]
    if len(games)!=32 or [game['seed'] for game in games]!=seeds:
        raise ValueError('V307 requires all 32 new paired A evaluation seeds')
    if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
        raise ValueError('Evaluation games require explicit terminal or cutoff status')
    return dict(games=32, mean_game_utility=mean(game['utility'] for game in games),
        wins=sum(game['status']=='WON' for game in games),
        losses=sum(game['status']=='LOST' for game in games),
        cutoffs=sum(game['status']=='CUTOFF' for game in games),
        cutoff_episodes=[episode for episode, game in enumerate(games) if game['status']=='CUTOFF'],
        steps=sum(game['steps'] for game in games))


def _bootstrap(records, values, draws):
    groups = {parent:[value for row, value in zip(records, values) if row['parent']==parent]
              for parent in range(4)}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group, k=16)) for group in groups.values())
                     for _ in range(draws))
    def quantile(q):
        position = (draws-1)*q
        lower, upper = floor(position), min(floor(position)+1, draws-1)
        return samples[lower]+(samples[upper]-samples[lower])*(position-lower)
    return dict(mean=mean(values), ci95=[quantile(.025), quantile(.975)],
        lifecycle_deltas={str(row['lifecycle']):value for row, value in zip(records, values)},
        improved_equal_worse=[sum(value>0. for value in values), sum(value==0. for value in values),
                              sum(value<0. for value in values)],
        adverse_lifecycles=[row['lifecycle'] for row, value in zip(records, values) if value<0.],
        parent_mean_deltas={str(parent):mean(group) for parent, group in groups.items()},
        interval_scope=INTERVAL_SCOPE)


def summarize(lifecycles, draws=20000):
    """Replay advantage and retention of the starting A1 critic are separate."""
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=64 or [row['lifecycle'] for row in rows]!=list(range(64))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V307 needs all 64 retained A1/current-data lifecycles under four fixed parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    records = [dict(lifecycle=row['lifecycle'], parent=row['parent'],
        arms={arm:_game_summary(row['arms'][arm]['evaluation']['game_summaries'], row['lifecycle'])
              for arm in ARMS}) for row in rows]
    arms = {}
    for arm in ARMS:
        values = [row['arms'][arm] for row in records]
        arms[arm] = dict(mean_game_utility=mean(value['mean_game_utility'] for value in values),
            **{key:sum(value[key] for value in values) for key in ('games', 'wins', 'losses', 'cutoffs', 'steps')})
    paired = {left+'_minus_'+right:_bootstrap(records,
        [row['arms'][left]['mean_game_utility']-row['arms'][right]['mean_game_utility'] for row in records], draws)
        for left, right in PAIRS}
    complete = not any(value['cutoffs'] for value in arms.values())
    supported = complete and paired[PRIMARY_CONTRAST]['ci95'][0]>0.
    lower, upper = paired['MIXED_REPLAY_minus_A1_FROZEN']['ci95']
    retention_status = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else
        'SUPPORTED_NONDECREASE' if lower>=0. else 'SUPPORTED_LOSS' if upper<0. else 'UNRESOLVED')
    return dict(arms=arms, paired_contrasts=paired, by_lifecycle=records,
        primary_contrast=PRIMARY_CONTRAST, primary_replay_gain_supported=supported,
        primary_replay_gain_status=('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        replay_retention_status=retention_status,
        replay_no_degradation_supported=retention_status=='SUPPORTED_NONDECREASE',
        source_reference_gain_supported={arm:complete and paired[arm+'_minus_SOURCE']['ci95'][0]>0.
                                         for arm in ('A1_FROZEN', 'NEW_ONLY', 'MIXED_REPLAY')},
        complete_game_endpoints=complete, bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        estimator='EQUAL_A_EVALUATION_GAMES_THEN_LIFECYCLES',
        contrast_sign='MIXED_REPLAY-minus-NEW_ONLY measures the budget-matched replay intervention. '
            'MIXED_REPLAY-minus-A1_FROZEN separately measures post-update retention of the initial critic.',
        retention_rule='Zero-margin A retention: lower >= 0 supports nondecrease; upper < 0 supports loss; '
            'otherwise unresolved. Gain over SOURCE does not establish retention of the A1 critic.',
        evidence_scope='Controlled replay diagnosis using the same retained V303 A1 and V306 CURRENT_DATA '
            'facts with new paired A evaluation seeds, conditional on four frozen source parents and both '
            'retained histories. No new training cohort is acquired. Prior aggregate outcomes are not '
            'pooled. This is not independent full-sequence confirmation, and B retention is not evaluated.',
        contribution_scope='Updating arms start from identical A1 reward/risk parameters. NEW_ONLY consumes '
            'new facts; MIXED_REPLAY replaces half its update budget with old A1 facts under a frozen '
            'selection rule. Matched eligible-row updates do not imply equal game coverage or total '
            'reconstruction computation. Replay jointly changes state coverage, factual return-label '
            'distribution and update ordering; it does not identify one as the unique causal mechanism.')
