"""Observed-context repair on retained V303 A -> B -> A histories."""
from math import floor
import random
from statistics import mean

from .continual_analysis_v303 import (
    CELLS, CHECKPOINTS, CURRENT_TASK_CELLS, FINAL_CELLS, STAGE_TASKS,
    _aggregate, _game_summary,
)

ARMS = ('SOURCE', 'SHARED_LOCAL', 'CONTEXT_LOCAL')
PAIRS = (('CONTEXT_LOCAL', 'SHARED_LOCAL'), ('CONTEXT_LOCAL', 'SOURCE'),
         ('SHARED_LOCAL', 'SOURCE'))
PRIMARY_CONTRAST = 'CONTEXT_LOCAL_minus_SHARED_LOCAL_FINAL_AB'
BOOTSTRAP_SEED = 30500001
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


def _heldout(rows, stage):
    supplied = [row['stages'][stage]['arms'][arm].get('heldout') for row in rows for arm in ARMS]
    if not any(value is not None for value in supplied):
        return None
    if any(value is None for value in supplied):
        raise ValueError('Provided heldout diagnostics require all stage arms and lifecycles')
    per_arm = {arm:[] for arm in ARMS}
    for row in rows:
        identity = None
        for arm in ARMS:
            heldout = row['stages'][stage]['arms'][arm]['heldout']
            games = heldout['game_metrics']
            current = [tuple(game[key] for key in ('episode', 'start', 'end', 'count')) for game in games]
            if not games or any(game['count']<=0 for game in games):
                raise ValueError('Heldout diagnostics require complete games with nonwinning afterstates')
            if identity is not None and current!=identity:
                raise ValueError('All arms must score the same complete heldout inventory')
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
    """Keep structural repair, final task gains, and signed retention separate."""
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=64 or [row['lifecycle'] for row in rows]!=list(range(64))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V305 needs all 64 retained V303 lifecycles under four fixed parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    records = []
    for row in rows:
        cells, source_games = {}, {}
        for cell, stage, task in CELLS:
            arms = {}
            for arm in ARMS:
                games = row['stages'][stage]['arms'][arm]['evaluations'][task]['game_summaries']
                arms[arm] = _game_summary(games, row['lifecycle'], task)
                if arm=='SOURCE':
                    if task in source_games and games!=source_games[task]:
                        raise ValueError('Frozen SOURCE must repeat exactly on each task across checkpoints')
                    source_games[task] = games
            cells[cell] = dict(arms=arms)
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], cells=cells))
    cells, final, current, checkpoints, arms = {}, {}, {}, {}, {}
    def utility(row, cell, arm):
        return row['cells'][cell]['arms'][arm]['mean_game_utility']
    for cell, stage, task in CELLS:
        comparisons = {left+'_minus_'+right:_bootstrap(records,
            [utility(row, cell, left)-utility(row, cell, right) for row in records], draws)
            for left, right in PAIRS}
        cells[cell] = dict(stage=stage, task=task, paired_contrasts=comparisons,
            arms={arm:_aggregate([row['cells'][cell]['arms'][arm] for row in records]) for arm in ARMS})
    for left, right in PAIRS:
        pair = left+'_minus_'+right
        final[pair] = _bootstrap(records,
            [mean(utility(row, cell, left)-utility(row, cell, right) for cell in FINAL_CELLS)
             for row in records], draws)
        current[pair] = _bootstrap(records,
            [mean(utility(row, cell, left)-utility(row, cell, right) for cell in CURRENT_TASK_CELLS)
             for row in records], draws)
    for name, (after, before) in CHECKPOINTS.items():
        checkpoints[name] = {arm:_bootstrap(records,
            [utility(row, after, arm)-utility(row, before, arm) for row in records], draws)
            for arm in ARMS}
    for arm in ARMS:
        arms[arm] = _aggregate([row['cells'][cell]['arms'][arm] for row in records for cell, _, _ in CELLS])
        arms[arm].pop('mean_game_utility')
        arms[arm]['mean_final_ab_game_utility'] = mean(
            mean(utility(row, cell, arm) for cell in FINAL_CELLS) for row in records)
        arms[arm]['mean_current_task_sequence_game_utility'] = mean(
            mean(utility(row, cell, arm) for cell in CURRENT_TASK_CELLS) for row in records)
    complete = not any(value['cutoffs'] for value in arms.values())
    supported = complete and final['CONTEXT_LOCAL_minus_SHARED_LOCAL']['ci95'][0]>0.
    final_tasks = {task:complete and cells['A2_'+task]['paired_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95'][0]>0.
                   for task in ('A', 'B')}
    retention = {}
    for name in ('A_after_B', 'B_after_A2', 'A_final_vs_A1'):
        lower, upper = checkpoints[name]['CONTEXT_LOCAL']['ci95']
        retention[name] = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else
            'SUPPORTED_NONDECREASE' if lower>=0. else 'SUPPORTED_LOSS' if upper<0. else 'UNRESOLVED')
    heldout = {stage:_heldout(rows, stage) for stage in STAGE_TASKS}
    return dict(arms=arms, cells=cells, final_ab_contrasts=final,
        current_task_sequence_contrasts=current, checkpoint_contrasts=checkpoints,
        heldout_by_stage={stage:value for stage, value in heldout.items() if value is not None},
        by_lifecycle=records, primary_contrast=PRIMARY_CONTRAST,
        primary_repair_supported=supported,
        primary_repair_status=('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        final_task_gain_supported=final_tasks, final_dual_task_gain_supported=all(final_tasks.values()),
        retention_status=retention,
        retained_gain_supported=all(value=='SUPPORTED_NONDECREASE' for value in retention.values()),
        a_restoration_supported=complete and checkpoints['A_restore_after_A2']['CONTEXT_LOCAL']['ci95'][0]>0.,
        complete_game_endpoints=complete, bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        estimator='EQUAL_FINAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        checkpoint_sign='Literal after-minus-before whole-game utility; negative values indicate loss. '
            'Frozen SOURCE repeats exactly, so these equal source-adjusted gain changes.',
        retention_rule='Zero-margin checkpoint intervals: lower >= 0 supports nondecrease; upper < 0 supports loss; '
            'otherwise unresolved. Retention and final individual task gains are separate from the primary repair endpoint.',
        evidence_scope='Controlled structural repair diagnosis on the same retained V303 A -> B -> A facts and '
            'evaluation seeds, conditional on four frozen source parents and retained histories. This is not '
            'independent confirmation or a new training cohort; V304 aggregate outcomes are not pooled.',
        contribution_scope='SOURCE and SHARED_LOCAL are exact retained V303 controls. CONTEXT_LOCAL uses '
            'observed spawn statistics to select persistent reward/risk parameters. New heads receive the same '
            'stage fit facts and frozen task evaluation beliefs; parameter bank allocation and computation '
            'must be accounted separately from acquired data.')
