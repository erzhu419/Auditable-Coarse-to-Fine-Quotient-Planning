"""Independent frozen-method cohort: complete games, then whole lifecycles."""
from math import floor
import random
from statistics import mean

ARMS = ('FROZEN', 'NORMALIZED_SEQUENTIAL_MC', 'EPISODE_MEAN_MC')
PAIRS = (('EPISODE_MEAN_MC', 'FROZEN'), ('NORMALIZED_SEQUENTIAL_MC', 'FROZEN'),
         ('EPISODE_MEAN_MC', 'NORMALIZED_SEQUENTIAL_MC'))
METRICS = ('bias', 'mse', 'mae')
PRIMARY_CONTRAST = 'EPISODE_MEAN_MC_minus_FROZEN'
BOOTSTRAP_SEED = 29100001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def _game_summary(games, lifecycle):
    seeds = [291900000000+lifecycle*1000000+episode for episode in range(32)]
    if len(games) != 32 or [game['seed'] for game in games] != seeds:
        raise ValueError('V291 needs the same 32 fresh paired evaluation seeds per arm/lifecycle')
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
    """Use only this cohort's full game outcomes and heldout game metrics.

    Optional aggregate errors, old-cohort evidence, anchors and training returns
    cannot select or reweight an endpoint. Every critic scores the same factual
    heldout inventory, and the bootstrap preserves all four fixed parents.
    """
    rows = sorted(lifecycles,key=lambda row:row['lifecycle'])
    if (len(rows)!=64 or [row['lifecycle'] for row in rows]!=list(range(64))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V291 needs 64 new lifecycles under their four fixed source parents')
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
    confirmed = complete and paired[PRIMARY_CONTRAST]['ci95'][0]>0.
    return dict(arms=arms,paired_contrasts=paired,heldout_contrasts=errors,
        primary_contrast=PRIMARY_CONTRAST,primary_prediction_contrast=PRIMARY_CONTRAST,
        primary_prediction_metric='mse',by_lifecycle=records,
        bootstrap_draws=draws,bootstrap_seed=BOOTSTRAP_SEED,complete_game_endpoints=complete,
        independent_learning_confirmed=confirmed,
        independent_learning_status=('SUPPORTED_' if confirmed else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        independent_prediction_supported=errors[PRIMARY_CONTRAST]['mse']['ci95'][1]<0.,
        estimator='EQUAL_EVALUATION_GAMES_THEN_LIFECYCLES',
        heldout_estimator='EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES',
        heldout_sign='Literal left-minus-right errors; negative MSE/MAE is better. Signed bias has no monotone quality ordering.',
        evidence_scope='New independent training and evaluation lifecycles under frozen V290 methods, '
            'conditional on four old source parents; no fresh-source pretraining claim.',
        contribution_scope='MEAN versus normalized sequential compares frozen game-start residual aggregation '
            'with current-residual sequential updates at equal nominal per-address total step size. '
            'Same training samples do not imply equal parameter-write or compute budgets.')
