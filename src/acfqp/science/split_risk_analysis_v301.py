"""Retained-B split reward/risk representation and fresh whole-game evaluation."""
from math import floor
import random
from statistics import mean

ARMS = ('SOURCE', 'MC', 'LOCAL_RISK', 'GLOBAL_RISK')
PAIRS = (('GLOBAL_RISK', 'SOURCE'), ('LOCAL_RISK', 'SOURCE'), ('MC', 'SOURCE'),
         ('GLOBAL_RISK', 'LOCAL_RISK'), ('GLOBAL_RISK', 'MC'))
METRICS = ('bias', 'mse', 'mae')
COMPONENT_METRICS = ('reward_bias', 'reward_mse', 'reward_mae', 'risk_brier',
                     'risk_log_loss', 'risk_bias', 'mean_risk_probability', 'win_label')
PRIMARY_CONTRAST = 'GLOBAL_RISK_minus_SOURCE'
BOOTSTRAP_SEED = 30100001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_B_TRAINING'


def _game_summary(games, lifecycle):
    seeds = [301900000000+lifecycle*1000000+episode for episode in range(32)]
    if len(games) != 32 or [game['seed'] for game in games] != seeds:
        raise ValueError('V301 needs the same 32 fresh paired evaluation seeds per arm/lifecycle')
    if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
        raise ValueError('Evaluation games require explicit terminal or cutoff status')
    return dict(games=32, mean_game_utility=mean(game['utility'] for game in games),
        wins=sum(game['status']=='WON' for game in games),
        losses=sum(game['status']=='LOST' for game in games),
        cutoffs=sum(game['status']=='CUTOFF' for game in games),
        cutoff_episodes=[episode for episode,game in enumerate(games) if game['status']=='CUTOFF'],
        steps=sum(game['steps'] for game in games))


def _identity(games):
    return [(game['episode'],game['start'],game['end'],game['count']) for game in games]


def _heldout_summary(games):
    if not games or any(game['count'] <= 0 for game in games):
        raise ValueError('Full heldout needs complete games with scored nonwinning afterstates')
    return dict(games=len(games), samples=sum(game['count'] for game in games),
                **{metric:mean(game[metric] for game in games) for metric in METRICS})


def _component_summary(games, heldout):
    if _identity(games) != _identity(heldout):
        raise ValueError('Component errors must score the same complete heldout games and afterstates')
    if any(game['win_label'] not in (0., 1.) for game in games):
        raise ValueError('Heldout risk labels require complete-game factual WON or LOST outcomes')
    return dict(games=len(games), samples=sum(game['count'] for game in games),
                **{metric:mean(game[metric] for game in games) for metric in COMPONENT_METRICS})


def _bootstrap(records, values, draws):
    groups = {parent:[value for row,value in zip(records,values) if row['parent']==parent]
              for parent in range(4)}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group,k=16)) for group in groups.values())
                     for _ in range(draws))
    def quantile(q):
        position = (draws-1)*q
        lower,upper = floor(position),min(floor(position)+1,draws-1)
        return samples[lower]+(samples[upper]-samples[lower])*(position-lower)
    return dict(mean=mean(values),ci95=[quantile(.025),quantile(.975)],
        lifecycle_deltas={str(row['lifecycle']):value for row,value in zip(records,values)},
        positive_equal_negative=[sum(value>0. for value in values),sum(value==0. for value in values),
                                 sum(value<0. for value in values)],
        parent_mean_deltas={str(parent):mean(group) for parent,group in groups.items()},
        interval_scope=INTERVAL_SCOPE)


def summarize(lifecycles, draws=20000):
    """Compare all paired new games after fitting the same retained V298 B data.

    Component calibration and full heldout utility errors remain descriptive.
    Neither can select lifecycles or replace the primary whole-game endpoint.
    """
    rows = sorted(lifecycles,key=lambda row:row['lifecycle'])
    if (len(rows)!=64 or [row['lifecycle'] for row in rows]!=list(range(64))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V301 needs all 64 retained B lifecycles under their four fixed source parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    records = []
    for row in rows:
        arms,heldout_identity = {},None
        for arm in ARMS:
            value = row['arms'][arm]
            games = value['heldout']['game_metrics']
            identity = _identity(games)
            if heldout_identity is None:
                heldout_identity = identity
            elif identity!=heldout_identity:
                raise ValueError('All critics must score the same complete heldout games and afterstates')
            arms[arm] = dict(_game_summary(value['game_summaries'],row['lifecycle']),
                             heldout=_heldout_summary(games))
            components = value['heldout'].get('component_game_metrics')
            if components is not None:
                arms[arm]['heldout']['components'] = _component_summary(components,games)
        records.append(dict(lifecycle=row['lifecycle'],parent=row['parent'],arms=arms))
    arms = {}
    for arm in ARMS:
        values = [row['arms'][arm] for row in records]
        heldout = [value['heldout'] for value in values]
        arms[arm] = dict(mean_game_utility=mean(value['mean_game_utility'] for value in values),
            **{key:sum(value[key] for value in values) for key in ('games','wins','losses','cutoffs','steps')},
            heldout=dict(games=sum(value['games'] for value in heldout),
                samples=sum(value['samples'] for value in heldout),
                **{metric:mean(value[metric] for value in heldout) for metric in METRICS}))
        component_rows = [value.get('components') for value in heldout]
        if any(value is not None for value in component_rows):
            if any(value is None for value in component_rows):
                raise ValueError('Provided component diagnostics require all 64 lifecycles of an arm')
            arms[arm]['heldout']['components'] = dict(
                games=sum(value['games'] for value in component_rows),
                samples=sum(value['samples'] for value in component_rows),
                **{metric:mean(value[metric] for value in component_rows) for metric in COMPONENT_METRICS})
    paired,errors = {},{}
    for left,right in PAIRS:
        name = left+'_minus_'+right
        differences = [row['arms'][left]['mean_game_utility']-row['arms'][right]['mean_game_utility']
                       for row in records]
        contrast = _bootstrap(records,differences,draws)
        contrast['improved_equal_worse'] = contrast.pop('positive_equal_negative')
        contrast['adverse_lifecycles'] = [row['lifecycle'] for row,value in zip(records,differences) if value<0.]
        paired[name] = contrast
        errors[name] = {}
        for metric in METRICS:
            differences = [row['arms'][left]['heldout'][metric]-row['arms'][right]['heldout'][metric]
                           for row in records]
            contrast = _bootstrap(records,differences,draws)
            if metric in ('mse','mae'):
                contrast['improved_equal_worse'] = [sum(value<0. for value in differences),
                    sum(value==0. for value in differences),sum(value>0. for value in differences)]
                contrast['adverse_lifecycles'] = [row['lifecycle'] for row,value in zip(records,differences) if value>0.]
            errors[name][metric] = contrast
    complete = not any(value['cutoffs'] for value in arms.values())
    supported = complete and paired[PRIMARY_CONTRAST]['ci95'][0]>0.
    return dict(arms=arms,paired_contrasts=paired,heldout_contrasts=errors,
        primary_contrast=PRIMARY_CONTRAST,by_lifecycle=records,
        bootstrap_draws=draws,bootstrap_seed=BOOTSTRAP_SEED,complete_game_endpoints=complete,
        split_risk_gain_supported=supported,
        split_risk_gain_status=('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        estimator='EQUAL_EVALUATION_GAMES_THEN_LIFECYCLES',
        heldout_estimator='EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES',
        heldout_sign='Literal left-minus-right errors; negative MSE/MAE is better. Signed bias has no monotone quality ordering.',
        component_scope='Reward suffix errors and factual terminal-risk calibration are heldout diagnostics, '
            'equally weighted by complete game then lifecycle; they do not determine learning gain.',
        evidence_scope='Developmental representation intervention after fitting the same retained V298 B training data; '
            'fresh paired stable-B complete-game evaluation, conditional on four old source parents and old training lifecycles. '
            'Not an independent new learning cohort or fresh-source confirmation.',
        contribution_scope='GLOBAL_RISK versus LOCAL_RISK changes the risk feature basis and dimension within shared '
            'split reward/sigmoid-risk heads and the frozen per-game learning rule; it is not an equal-compute contrast. '
            'GLOBAL_RISK versus MC changes '
            'both representation and learning targets. Only GLOBAL_RISK versus SOURCE whole-game utility determines '
            'split-risk gain. Prediction or risk calibration and secondary utility cannot replace it; same samples '
            'do not imply equal compute budgets.')
