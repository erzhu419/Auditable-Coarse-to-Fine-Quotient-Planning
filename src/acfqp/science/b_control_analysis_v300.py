"""Retained B training ablation: fresh complete-game control-target evaluation."""
from math import floor
import random
from statistics import mean

ARMS = ('SOURCE', 'MC', 'EXPECTED_CONTROL')
PAIRS = (('EXPECTED_CONTROL', 'SOURCE'), ('MC', 'SOURCE'),
         ('EXPECTED_CONTROL', 'MC'))
METRICS = ('bias', 'mse', 'mae')
PRIMARY_CONTRAST = 'EXPECTED_CONTROL_minus_SOURCE'
BOOTSTRAP_SEED = 30000001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_B_TRAINING'


def _game_summary(games, lifecycle):
    seeds = [300900000000+lifecycle*1000000+episode for episode in range(32)]
    if len(games) != 32 or [game['seed'] for game in games] != seeds:
        raise ValueError('V300 needs the same 32 fresh paired evaluation seeds per arm/lifecycle')
    if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
        raise ValueError('Evaluation games require explicit terminal or cutoff status')
    return dict(games=32, mean_game_utility=mean(game['utility'] for game in games),
        wins=sum(game['status']=='WON' for game in games),
        losses=sum(game['status']=='LOST' for game in games),
        cutoffs=sum(game['status']=='CUTOFF' for game in games),
        cutoff_episodes=[episode for episode,game in enumerate(games) if game['status']=='CUTOFF'],
        steps=sum(game['steps'] for game in games))


def _heldout_summary(games):
    if not games or any(game['count'] <= 0 for game in games):
        raise ValueError('Full heldout needs complete games with scored nonwinning afterstates')
    return dict(games=len(games), samples=sum(game['count'] for game in games),
                **{metric:mean(game[metric] for game in games) for metric in METRICS})


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
    """Pair fresh full-game evaluation after fitting identical retained B data.

    Prediction contrasts use the complete, shared old heldout game inventory.
    Training fitness, old-cohort outcomes and aggregate errors cannot choose,
    reweight or replace the primary whole-game control endpoint.
    """
    rows = sorted(lifecycles,key=lambda row:row['lifecycle'])
    if (len(rows)!=64 or [row['lifecycle'] for row in rows]!=list(range(64))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V300 needs all 64 retained B lifecycles under their four fixed source parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    records = []
    for row in rows:
        arms,heldout_identity = {},None
        for arm in ARMS:
            value = row['arms'][arm]
            games = value['heldout']['game_metrics']
            identity = [(game['episode'],game['start'],game['end'],game['count']) for game in games]
            if heldout_identity is None:
                heldout_identity = identity
            elif identity!=heldout_identity:
                raise ValueError('All critics must score the same complete heldout games and afterstates')
            arms[arm] = dict(_game_summary(value['game_summaries'],row['lifecycle']),
                             heldout=_heldout_summary(games))
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
        control_target_gain_supported=supported,
        control_target_gain_status=('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        estimator='EQUAL_EVALUATION_GAMES_THEN_LIFECYCLES',
        heldout_estimator='EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES',
        heldout_sign='Literal left-minus-right errors; negative MSE/MAE is better. Signed bias has no monotone quality ordering.',
        evidence_scope='Developmental control-target comparison after fitting the same retained V298 B training data; '
            'fresh paired stable-B complete-game evaluation, conditional on four old source parents and old training lifecycles. '
            'Not an independent new learning cohort or fresh-source confirmation.',
        contribution_scope='EXPECTED_CONTROL versus MC changes only the fitted target on shared old B samples. '
            'Only EXPECTED_CONTROL versus SOURCE whole-game utility determines control-target gain. '
            'Prediction error and secondary utility cannot replace it; same samples do not imply equal compute budgets.')

