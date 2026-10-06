"""Frozen final two-task endpoint for persistent A -> B -> A learning."""
from math import floor
import random
from statistics import mean

ARMS = ('SOURCE', 'MC', 'LOCAL_RISK')
PAIRS = (('LOCAL_RISK', 'SOURCE'), ('MC', 'SOURCE'), ('LOCAL_RISK', 'MC'))
STAGE_TASKS = {'A1': ('A',), 'B': ('A', 'B'), 'A2': ('A', 'B')}
CELLS = tuple((stage+'_'+task, stage, task)
              for stage, tasks in STAGE_TASKS.items() for task in tasks)
CURRENT_TASK_CELLS = ('A1_A', 'B_B', 'A2_A')
FINAL_CELLS = ('A2_A', 'A2_B')
CHECKPOINTS = {'A_after_B': ('B_A', 'A1_A'),
               'B_after_A2': ('A2_B', 'B_B'),
               'A_restore_after_A2': ('A2_A', 'B_A'),
               'A_final_vs_A1': ('A2_A', 'A1_A')}
PRIMARY_CONTRAST = 'LOCAL_RISK_minus_SOURCE_FINAL_AB'
BOOTSTRAP_SEED = 30300001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def _game_summary(games, lifecycle, task):
    seeds = [303900000000+(0 if task=='A' else 100000)+lifecycle*1000000+episode
             for episode in range(32)]
    if len(games)!=32 or [game['seed'] for game in games]!=seeds:
        raise ValueError('V303 needs 32 fresh paired task seeds reused across checkpoints')
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


def _aggregate(values):
    return dict(mean_game_utility=mean(value['mean_game_utility'] for value in values),
                **{key:sum(value[key] for value in values)
                   for key in ('games', 'wins', 'losses', 'cutoffs', 'steps')})


def _heldout(rows, stage):
    provided = [row['stages'][stage]['arms'][arm].get('heldout') for row in rows for arm in ARMS]
    if not any(value is not None for value in provided):
        return None
    if any(value is None for value in provided):
        raise ValueError('Provided heldout diagnostics need all stage arms and lifecycles')
    per_arm = {arm:[] for arm in ARMS}
    for row in rows:
        identity = None
        for arm in ARMS:
            heldout = row['stages'][stage]['arms'][arm]['heldout']
            games = heldout['game_metrics']
            current = [tuple(game[key] for key in ('episode', 'start', 'end', 'count')) for game in games]
            if not games or any(game['count']<=0 for game in games):
                raise ValueError('Heldout diagnostics need complete games and nonwinning afterstates')
            if identity is not None and current!=identity:
                raise ValueError('Stage arms must score the same complete heldout inventory')
            identity = current
            value = dict(games=len(games), samples=sum(game['count'] for game in games),
                         **{metric:mean(game[metric] for game in games) for metric in ('bias', 'mse', 'mae')})
            components = heldout.get('component_game_metrics')
            if components is not None:
                if [tuple(game[key] for key in ('episode', 'start', 'end', 'count'))
                        for game in components]!=identity:
                    raise ValueError('Component diagnostics must score the same complete heldout inventory')
                if any(game['win_label'] not in (0., 1.) for game in components):
                    raise ValueError('Risk labels require factual complete-game terminal outcomes')
                value['components'] = {metric:mean(game[metric] for game in components) for metric in
                    ('reward_bias', 'reward_mse', 'reward_mae', 'risk_brier', 'risk_log_loss',
                     'risk_bias', 'mean_risk_probability', 'win_label')}
            per_arm[arm].append(value)
    result = {}
    for arm, values in per_arm.items():
        result[arm] = dict(games=sum(value['games'] for value in values),
            samples=sum(value['samples'] for value in values),
            **{metric:mean(value[metric] for value in values) for metric in ('bias', 'mse', 'mae')})
        if any('components' in value for value in values):
            if any('components' not in value for value in values):
                raise ValueError('Provided component diagnostics need every lifecycle of an arm')
            result[arm]['components'] = {metric:mean(value['components'][metric] for value in values)
                                         for metric in values[0]['components']}
    return result


def summarize(lifecycles, draws=20000):
    """Use final retained A/B utility as primary; adaptation and forgetting are separate."""
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=64 or [row['lifecycle'] for row in rows]!=list(range(64))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V303 needs all 64 fresh continual lifecycles under four fixed parents')
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
    supported = complete and final['LOCAL_RISK_minus_SOURCE']['ci95'][0]>0.
    final_tasks = {task:complete and cells['A2_'+task]['paired_contrasts']['LOCAL_RISK_minus_SOURCE']['ci95'][0]>0.
                   for task in ('A', 'B')}
    retention = {}
    for name in ('A_after_B', 'B_after_A2', 'A_final_vs_A1'):
        lower, upper = checkpoints[name]['LOCAL_RISK']['ci95']
        retention[name] = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else
            'SUPPORTED_NONDECREASE' if lower>=0. else 'SUPPORTED_LOSS' if upper<0. else 'UNRESOLVED')
    heldout = {stage:_heldout(rows, stage) for stage in STAGE_TASKS}
    return dict(arms=arms, cells=cells, final_ab_contrasts=final,
        current_task_sequence_contrasts=current, checkpoint_contrasts=checkpoints,
        heldout_by_stage={stage:value for stage, value in heldout.items() if value is not None},
        by_lifecycle=records, primary_contrast=PRIMARY_CONTRAST,
        primary_sequence_gain_supported=supported,
        primary_sequence_gain_status=('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        final_task_gain_supported=final_tasks, final_dual_task_gain_supported=all(final_tasks.values()),
        retention_status=retention,
        retained_gain_supported=all(value=='SUPPORTED_NONDECREASE' for value in retention.values()),
        a_restoration_supported=complete and checkpoints['A_restore_after_A2']['LOCAL_RISK']['ci95'][0]>0.,
        complete_game_endpoints=complete, bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        estimator='EQUAL_FINAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        checkpoint_sign='Literal after-minus-before whole-game utility; negative values indicate loss. '
            'Frozen SOURCE repeats exactly, so these equal source-adjusted gain changes.',
        retention_rule='Zero-margin checkpoint intervals: lower >= 0 supports nondecrease; upper < 0 supports loss; '
            'otherwise unresolved. Retention, restoration and final individual task gains are separate from the primary endpoint.',
        evidence_scope='New A -> B -> A factual histories with persistent learned parameters and frozen observed task beliefs. '
            'The primary endpoint is final equal-weight A/B whole-game LOCAL_RISK-minus-SOURCE utility, conditional on four '
            'reused frozen source parents. Current-task sequence utility and prediction errors are descriptive. '
            'Old development/confirmation results are not pooled; this does not establish unrestricted strategic transfer.',
        contribution_scope='SOURCE is frozen; MC retains one critic and LOCAL_RISK retains reward and risk heads across all stages. '
            'The learners receive the same acquired samples; equal data does not imply equal computation.')
