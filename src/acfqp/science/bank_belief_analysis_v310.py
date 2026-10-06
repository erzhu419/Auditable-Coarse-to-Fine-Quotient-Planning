"""Selected-bank planning beliefs and strict retention across A/B/A/B/A."""
from math import floor
import random
from statistics import mean

from .continual_analysis_v303 import _aggregate

ARMS = ('SOURCE', 'CONTEXT_MC', 'CONTEXT_LOCAL')
PAIRS = (('CONTEXT_LOCAL', 'CONTEXT_MC'), ('CONTEXT_LOCAL', 'SOURCE'),
         ('CONTEXT_MC', 'SOURCE'))
STAGES = ('A1', 'B1', 'A2', 'B2', 'A3')
STAGE_TASKS = {'A1': ('A',), 'B1': ('A', 'B'), 'A2': ('A', 'B'),
               'B2': ('A', 'B'), 'A3': ('A', 'B')}
CELLS = tuple((stage+'_'+task, stage, task)
              for stage, tasks in STAGE_TASKS.items() for task in tasks)
CURRENT_TASK_CELLS = ('A1_A', 'B1_B', 'A2_A', 'B2_B', 'A3_A')
FINAL_CELLS = ('A3_A', 'A3_B')
CHECKPOINTS = {'A_after_B1': ('B1_A', 'A1_A'),
               'A_return_A2': ('A2_A', 'A1_A'),
               'A_after_B2': ('B2_A', 'A1_A'),
               'A_final_vs_A1': ('A3_A', 'A1_A'),
               'B_after_A2': ('A2_B', 'B1_B'),
               'B_return_B2': ('B2_B', 'B1_B'),
               'B_final_vs_B1': ('A3_B', 'B1_B')}
PRIMARY_CONTRAST = 'CONTEXT_LOCAL_minus_CONTEXT_MC_FINAL_AB'
BOOTSTRAP_SEED = 31000001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def _game_summary(games, lifecycle, task):
    seeds = [310900000000+(100000 if task=='B' else 0)+lifecycle*1000000+episode
             for episode in range(32)]
    if len(games)!=32 or [game['seed'] for game in games]!=seeds:
        raise ValueError('V310 requires all 32 fresh paired task seeds reused across checkpoints')
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
    """Use actual bank beliefs and all seven literal first-reference retention endpoints."""
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=64 or [row['lifecycle'] for row in rows]!=list(range(64))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V310 needs all 64 fresh A/B/A/B/A lifecycles under four fixed parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    records = []
    for row in rows:
        cells, source_games = {}, {}
        for cell, stage, task in CELLS:
            arms = {}
            try:
                observed_p = row['stages'][stage]['planning_beliefs'][task]['estimated_p_four']
            except KeyError as error:
                raise ValueError('V310 requires the selected bank planning belief for every evaluation cell') from error
            for arm in ARMS:
                try:
                    evaluation = row['stages'][stage]['arms'][arm]['evaluations'][task]
                    games = evaluation['game_summaries']
                except KeyError as error:
                    raise ValueError('V310 requires all nine evaluation cells for every lifecycle and arm') from error
                try:
                    actual_p = evaluation['estimated_p_four']
                except KeyError as error:
                    raise ValueError('V310 requires the actual planning probability for every evaluation arm') from error
                if actual_p!=observed_p:
                    raise ValueError('All three V310 arms must use the selected bank planning belief in each cell')
                arms[arm] = _game_summary(games, row['lifecycle'], task)
                if arm=='SOURCE':
                    source_key = (task, observed_p)
                    if source_key in source_games and games!=source_games[source_key]:
                        raise ValueError('Frozen SOURCE must repeat exactly for the same task and actual planning probability')
                    source_games[source_key] = games
            cells[cell] = dict(estimated_p_four=observed_p, arms=arms)
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
    primary = complete and final['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95'][0]>0.
    net = complete and final['CONTEXT_LOCAL_minus_SOURCE']['ci95'][0]>0.
    final_tasks = {task:complete and cells['A3_'+task]['paired_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95'][0]>0.
                   for task in ('A', 'B')}
    retention = {}
    for name in CHECKPOINTS:
        lower, upper = checkpoints[name]['CONTEXT_LOCAL']['ci95']
        retention[name] = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else
            'SUPPORTED_NONDECREASE' if lower>=0. else 'SUPPORTED_LOSS' if upper<0. else 'UNRESOLVED')
    preserved = all(value=='SUPPORTED_NONDECREASE' for value in retention.values())
    return dict(arms=arms, cells=cells, final_ab_contrasts=final,
        current_task_sequence_contrasts=current, checkpoint_contrasts=checkpoints,
        by_lifecycle=records, primary_contrast=PRIMARY_CONTRAST,
        primary_local_over_mc_supported=primary,
        primary_local_over_mc_status=('SUPPORTED_' if primary else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        final_net_gain_supported=net,
        final_task_gain_supported=final_tasks, final_dual_task_gain_supported=all(final_tasks.values()),
        retention_status=retention, retention_supported=preserved,
        retained_gain_supported=primary and net and preserved,
        retained_gain_rule='Primary final LOCAL-over-MC gain AND final LOCAL-over-SOURCE gain AND all seven '
            'zero-margin LOCAL retention comparisons relative to the first task endpoint supported. '
            'Individual final A/B gains remain separate.',
        complete_game_endpoints=complete, bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        estimator='EQUAL_FINAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        checkpoint_sign='Literal after-minus-first-task-endpoint whole-game utility; negative values indicate loss. '
            'SOURCE may change when the selected bank planning belief changes, so these are not necessarily source-adjusted gain changes. Deployment model risk remains in the literal retention endpoint.',
        retention_rule='All seven zero-margin first-reference checkpoint intervals: lower >= 0 supports '
            'nondecrease; upper < 0 supports loss; otherwise unresolved. Positive final mean gain alone '
            'does not establish task preservation.',
        routing_endpoint_scope='A1_A, B1_B, A2_A, B2_B and A3_A use their actual observed stage routes. '
            'Other task cells are readonly probes routed using the first observed task detectors. '
            'Actual return routing, including misclassification or creation of another bank, enters '
            'the current-task endpoints and final A3_A endpoint. Each cell uses its selected bank immutable '
            'first-FIT planning belief for SOURCE, MC and LOCAL; task labels do not select model probabilities. '
            'Utility evidence determines support flags.',
        evidence_scope='Fresh A/B/A/B/A acquisition and paired evaluation histories under four reused '
            'frozen SOURCE parents. V309 target cases and outcomes are not reused or pooled. '
            'Intervals remain conditional on the four source parents. These fresh target histories test '
            'bank-owned-belief first adaptation and reuse; they do not identify a causal improvement over '
            'V309 or provide independent source-training confirmation.',
        contribution_scope='Both learners share supplied stage boundaries, observed-context routing, bank '
            'allocation, original SOURCE initialization, immutable first-FIT bank belief and each new-context '
            'acquired dataset. CONTEXT_MC '
            'fits a single utility critic; CONTEXT_LOCAL fits reward and risk, with unequal capacity and '
            'computation despite matched data and routing. Existing contexts reuse frozen parameters. '
            'False new-context decisions can acquire another paid cohort. This tests repeated first adaptation '
            'and parameter reuse at supplied boundaries, with other-task diagnostic probes using first task '
            'detectors. Unsegmented full online discovery, continued improvement within a known context, '
            'unrestricted strategic learning and false-error guarantees remain unestablished.')
