"""Matched retained-B diagnosis of SOURCE versus A1-inherited initialization."""
from math import floor
import random
from statistics import mean

from .continual_analysis_v303 import _game_summary

ARMS = ('SOURCE', 'MC_FRESH_B', 'MC_AFTER_A1_B', 'LOCAL_FRESH_B', 'LOCAL_AFTER_A1_B')
PAIRS = (('LOCAL_FRESH_B', 'LOCAL_AFTER_A1_B'), ('MC_FRESH_B', 'MC_AFTER_A1_B'),
         ('LOCAL_FRESH_B', 'SOURCE'), ('LOCAL_AFTER_A1_B', 'SOURCE'),
         ('MC_FRESH_B', 'SOURCE'), ('MC_AFTER_A1_B', 'SOURCE'))
PRIMARY_CONTRAST = 'LOCAL_FRESH_B_minus_LOCAL_AFTER_A1_B'
BOOTSTRAP_SEED = 30400001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_V303_HISTORIES'
METRICS = ('bias', 'mse', 'mae')
COMPONENT_METRICS = ('reward_bias', 'reward_mse', 'reward_mae', 'risk_brier',
                     'risk_log_loss', 'risk_bias', 'mean_risk_probability', 'win_label')


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


def _heldout(rows):
    supplied = [row['arms'][arm].get('heldout') for row in rows for arm in ARMS]
    if not any(value is not None for value in supplied):
        return {}
    if any(value is None for value in supplied):
        raise ValueError('Provided B heldout diagnostics require all arms and lifecycles')
    per_arm = {arm:[] for arm in ARMS}
    for row in rows:
        identity = None
        for arm in ARMS:
            heldout = row['arms'][arm]['heldout']
            games = heldout['game_metrics']
            current = [tuple(game[key] for key in ('episode', 'start', 'end', 'count')) for game in games]
            if not games or any(game['count']<=0 for game in games):
                raise ValueError('B heldout requires complete games with nonwinning afterstates')
            if identity is not None and current!=identity:
                raise ValueError('All arms must score the same complete B heldout inventory')
            identity = current
            value = dict(games=len(games), samples=sum(game['count'] for game in games),
                         **{metric:mean(game[metric] for game in games) for metric in METRICS})
            components = heldout.get('component_game_metrics')
            if components is not None:
                if [tuple(game[key] for key in ('episode', 'start', 'end', 'count'))
                        for game in components]!=identity:
                    raise ValueError('Components must score the same complete B heldout inventory')
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
    """Pair B control utility on V303 seeds; fit history and heldout errors stay separate."""
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=64 or [row['lifecycle'] for row in rows]!=list(range(64))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V304 needs all 64 retained V303 lifecycles under four fixed parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    records = [dict(lifecycle=row['lifecycle'], parent=row['parent'],
        arms={arm:_game_summary(row['arms'][arm]['evaluation']['game_summaries'], row['lifecycle'], 'B')
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
    history_status, fresh_gain, negative_transfer = {}, {}, {}
    for family in ('LOCAL', 'MC'):
        lower, upper = paired[family+'_FRESH_B_minus_'+family+'_AFTER_A1_B']['ci95']
        history_status[family] = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else
            'SUPPORTED_PENALTY' if lower>0. else 'SUPPORTED_BENEFIT' if upper<0. else 'UNRESOLVED')
        fresh_gain[family] = complete and paired[family+'_FRESH_B_minus_SOURCE']['ci95'][0]>0.
        negative_transfer[family] = history_status[family]=='SUPPORTED_PENALTY' and \
            paired[family+'_AFTER_A1_B_minus_SOURCE']['ci95'][1]<0.
    supported = history_status['LOCAL']=='SUPPORTED_PENALTY'
    diagnosis = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else
        'FRESH_B_GAIN_WITH_HISTORY_NEGATIVE_TRANSFER_SUPPORTED' if fresh_gain['LOCAL'] and negative_transfer['LOCAL'] else
        'HISTORY_NEGATIVE_TRANSFER_SUPPORTED' if negative_transfer['LOCAL'] else
        'HISTORY_INITIALIZATION_PENALTY_SUPPORTED' if supported else
        'HISTORY_INITIALIZATION_BENEFIT_SUPPORTED' if history_status['LOCAL']=='SUPPORTED_BENEFIT' else
        'FRESH_B_GAIN_SUPPORTED_HISTORY_EFFECT_UNRESOLVED' if fresh_gain['LOCAL'] else
        'NO_SUPPORTED_HISTORY_PENALTY_OR_FRESH_B_GAIN')
    return dict(arms=arms, paired_contrasts=paired, heldout=_heldout(rows), by_lifecycle=records,
        primary_contrast=PRIMARY_CONTRAST, primary_history_penalty_supported=supported,
        history_effect_status=history_status, fresh_b_gain_supported=fresh_gain,
        history_negative_transfer_supported=negative_transfer, history_diagnosis=diagnosis,
        complete_game_endpoints=complete, bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        estimator='EQUAL_B_EVALUATION_GAMES_THEN_LIFECYCLES',
        heldout_estimator='EQUAL_COMPLETE_B_HELDOUT_GAMES_THEN_LIFECYCLES',
        contrast_sign='Fresh-minus-inherited utility: positive values indicate a penalty from A1 history. '
            'Fresh-minus-SOURCE gain and inherited-minus-SOURCE loss are separate endpoints.',
        evidence_scope='Controlled diagnosis on the same retained V303 B facts and B evaluation seeds, '
            'conditional on four frozen source parents and retained histories. This is not independent confirmation '
            'or a new training cohort; V302/V303 aggregate outcomes are not pooled.',
        contribution_scope='B fit data, targets, order, learning rates and evaluation conditions are matched. '
            'Inherited learners additionally fit A1 before B. Equal B exposure does not imply equal total '
            'training or computation; the comparison isolates initialization/history. It does not identify '
            'task-conditioned architecture as the unique remedy.')
