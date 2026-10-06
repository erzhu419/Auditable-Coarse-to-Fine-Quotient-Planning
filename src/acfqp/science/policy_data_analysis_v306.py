"""Matched actor-data diagnosis after the same retained A1 local critic."""
from math import floor
import random
from statistics import mean

ARMS = ('SOURCE', 'A1_FROZEN', 'SOURCE_DATA', 'CURRENT_DATA')
DATASETS = ('SOURCE_DATA', 'CURRENT_DATA')
PAIRS = (('CURRENT_DATA', 'SOURCE_DATA'), ('CURRENT_DATA', 'A1_FROZEN'),
         ('SOURCE_DATA', 'A1_FROZEN'), ('CURRENT_DATA', 'SOURCE'),
         ('SOURCE_DATA', 'SOURCE'), ('A1_FROZEN', 'SOURCE'))
PRIMARY_CONTRAST = 'CURRENT_DATA_minus_SOURCE_DATA'
BOOTSTRAP_SEED = 30600001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_V303_A1_HISTORIES'
METRICS = ('bias', 'mse', 'mae')
COMPONENT_METRICS = ('reward_bias', 'reward_mse', 'reward_mae', 'risk_brier',
                     'risk_log_loss', 'risk_bias', 'mean_risk_probability', 'win_label')


def _game_summary(games, lifecycle):
    seeds = [306900000000+lifecycle*1000000+episode for episode in range(32)]
    if len(games)!=32 or [game['seed'] for game in games]!=seeds:
        raise ValueError('V306 requires all 32 new paired A evaluation seeds')
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


def _heldout(rows, dataset):
    supplied = [row['arms'][arm].get('heldout_by_dataset', {}).get(dataset)
                for row in rows for arm in ARMS]
    if not any(value is not None for value in supplied):
        return None
    if any(value is None for value in supplied):
        raise ValueError('Provided heldout diagnostics require all arms and lifecycles of a dataset')
    per_arm = {arm:[] for arm in ARMS}
    for row in rows:
        identity = None
        for arm in ARMS:
            heldout = row['arms'][arm]['heldout_by_dataset'][dataset]
            games = heldout['game_metrics']
            current = [tuple(game[key] for key in ('episode', 'start', 'end', 'count')) for game in games]
            if not games or any(game['count']<=0 for game in games):
                raise ValueError('Heldout requires complete games with nonwinning afterstates')
            if identity is not None and current!=identity:
                raise ValueError('All arms must score the same complete heldout inventory within a dataset')
            identity = current
            value = dict(games=len(games), samples=sum(game['count'] for game in games),
                         **{metric:mean(game[metric] for game in games) for metric in METRICS})
            components = heldout.get('component_game_metrics')
            if components is not None:
                if [tuple(game[key] for key in ('episode', 'start', 'end', 'count'))
                        for game in components]!=identity:
                    raise ValueError('Components must score the same complete heldout inventory')
                if any(game['win_label'] not in (0., 1.) for game in components):
                    raise ValueError('Risk labels require factual complete-game outcomes')
                value['components'] = {metric:mean(game[metric] for game in components)
                                        for metric in COMPONENT_METRICS}
            per_arm[arm].append(value)
    result = {}
    for arm, values in per_arm.items():
        result[arm] = dict(games=sum(value['games'] for value in values),
            samples=sum(value['samples'] for value in values),
            **{metric:mean(value[metric] for value in values) for metric in METRICS})
        if any('components' in value for value in values):
            if any('components' not in value for value in values):
                raise ValueError('Provided component diagnostics require every lifecycle of an arm')
            result[arm]['components'] = {metric:mean(value['components'][metric] for value in values)
                                        for metric in COMPONENT_METRICS}
    return result


def summarize(lifecycles, draws=20000):
    """Compare actor policies under matched raw budgets; report retention separately."""
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=64 or [row['lifecycle'] for row in rows]!=list(range(64))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V306 needs all 64 retained A1 lifecycles under four fixed parents')
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
    primary_supported = complete and paired[PRIMARY_CONTRAST]['ci95'][0]>0.
    lower, upper = paired['CURRENT_DATA_minus_A1_FROZEN']['ci95']
    retention_status = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else
        'SUPPORTED_NONDECREASE' if lower>=0. else 'SUPPORTED_LOSS' if upper<0. else 'UNRESOLVED')
    heldout = {dataset:_heldout(rows, dataset) for dataset in DATASETS}
    return dict(arms=arms, paired_contrasts=paired, by_lifecycle=records,
        heldout_by_dataset={dataset:value for dataset, value in heldout.items() if value is not None},
        primary_contrast=PRIMARY_CONTRAST, primary_policy_data_gain_supported=primary_supported,
        primary_policy_data_gain_status=('SUPPORTED_' if primary_supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        current_policy_retention_status=retention_status,
        current_policy_no_degradation_supported=retention_status=='SUPPORTED_NONDECREASE',
        source_reference_gain_supported={arm:complete and paired[arm+'_minus_SOURCE']['ci95'][0]>0.
                                         for arm in ('A1_FROZEN', 'SOURCE_DATA', 'CURRENT_DATA')},
        complete_game_endpoints=complete, bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        estimator='EQUAL_A_EVALUATION_GAMES_THEN_LIFECYCLES',
        heldout_estimator='EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES_SEPARATELY_BY_DATASET',
        contrast_sign='CURRENT_DATA-minus-SOURCE_DATA utility isolates the actor-data contrast. '
            'CURRENT_DATA-minus-A1_FROZEN is the separate post-update A retention endpoint.',
        retention_rule='Zero-margin A retention: lower >= 0 supports nondecrease; upper < 0 supports loss; '
            'otherwise unresolved. A gain over SOURCE alone does not establish retention of the A1 critic.',
        evidence_scope='New A training trajectories and new paired A evaluation seeds conditional on four frozen '
            'source parents and the same retained V303 A1 critic histories. The actor-data experiment has new '
            'target data; it is not fully independent method confirmation. Prior V303/V304/V305 aggregate '
            'outcomes are not pooled. B retention and dual-task continual learning are not evaluated here.',
        contribution_scope='Both learners start from the same A1 reward/risk parameters. SOURCE_DATA acquires '
            'new A facts using frozen SOURCE; CURRENT_DATA uses the frozen A1 full local actor. The collectors '
            'share raw-spawn RNG seeds and nominal raw budgets, while policy trajectories, completed games '
            'and fitted samples can differ. Raw-budget matching does not imply equal fitted samples or computation.')
