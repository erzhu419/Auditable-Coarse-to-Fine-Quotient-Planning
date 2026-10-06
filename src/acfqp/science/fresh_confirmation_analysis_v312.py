"""Frozen four-arm confirmation under four freshly trained SOURCE value parents."""
from math import floor
import random
from statistics import mean

from .continual_analysis_v303 import _aggregate

ARMS = ('SOURCE', 'CONTEXT_MC', 'CONTEXT_LINEAR_WIN', 'CONTEXT_LOCAL')
PAIRS = (('CONTEXT_LOCAL', 'CONTEXT_LINEAR_WIN'), ('CONTEXT_LOCAL', 'CONTEXT_MC'),
         ('CONTEXT_LINEAR_WIN', 'CONTEXT_MC'), ('CONTEXT_LOCAL', 'SOURCE'),
         ('CONTEXT_LINEAR_WIN', 'SOURCE'), ('CONTEXT_MC', 'SOURCE'))
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
PRIMARY_CONTRAST = 'CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN_FINAL_AB'
BOOTSTRAP_SEED = 31200001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def _game_summary(games, lifecycle, task):
    seeds = [312900000000+(100000 if task=='B' else 0)+lifecycle*1000000+episode
             for episode in range(32)]
    if len(games)!=32 or [game['seed'] for game in games]!=seeds:
        raise ValueError('V312 requires all 32 fresh paired task seeds reused across checkpoints')
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
        raise ValueError('V312 needs all 64 fresh A/B/A/B/A lifecycles under four freshly trained frozen parents')
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
                raise ValueError('V312 requires the selected bank planning belief for every evaluation cell') from error
            for arm in ARMS:
                try:
                    evaluation = row['stages'][stage]['arms'][arm]['evaluations'][task]
                    games = evaluation['game_summaries']
                except KeyError as error:
                    raise ValueError('V312 requires all nine evaluation cells for every lifecycle and arm') from error
                try:
                    actual_p = evaluation['estimated_p_four']
                except KeyError as error:
                    raise ValueError('V312 requires the actual planning probability for every evaluation arm') from error
                if actual_p!=observed_p:
                    raise ValueError('All four V312 arms must use the selected bank planning belief in each cell')
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
    primary = complete and final['CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN']['ci95'][0]>0.
    local_mc = complete and final['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95'][0]>0.
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
        primary_local_over_linear_supported=primary,
        primary_local_over_linear_status=('SUPPORTED_' if primary else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        primary_local_over_mc_supported=local_mc,
        primary_local_over_mc_status=('SUPPORTED_' if local_mc else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        final_net_gain_supported=net,
        final_task_gain_supported=final_tasks, final_dual_task_gain_supported=all(final_tasks.values()),
        retention_status=retention, retention_supported=preserved,
        retained_gain_supported=primary and net and preserved,
        retained_gain_rule='Primary final LOCAL-over-LINEAR_WIN gain AND final LOCAL-over-SOURCE gain AND all seven '
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
            'first-FIT planning belief for SOURCE, MC, LINEAR_WIN and LOCAL; task labels do not select model probabilities. '
            'Utility evidence determines support flags.',
        evidence_scope='Four new SOURCE value-training histories from zero initialization and fresh seeds, '
            'with 64 new A/B/A/B/A acquisition and paired evaluation histories. Old SOURCE weights, target '
            'histories and evaluation outcomes are not reused or pooled. The previously learned deterministic '
            'dynamics program is shared. Intervals remain conditional on the four new frozen source parents; '
            'they do not include unconditional source-population uncertainty or establish full-pipeline '
            'independence. This confirms the frozen V311 matched two-table contrast on new source training '
            'and target histories, not a causal improvement over V311. LOCAL-over-MC support fields are '
            'descriptive; LOCAL-over-LINEAR_WIN is the sole primary.',
        contribution_scope='The three learners share supplied stage boundaries, observed-context routing, '
            'bank allocation, fresh frozen SOURCE initialization, immutable first-FIT bank belief and each '
            'new-context acquired dataset. CONTEXT_LOCAL and CONTEXT_LINEAR_WIN each retain two active '
            'ntuple tables with matched storage and per-address writes. LINEAR_WIN predicts an unclipped '
            'linear terminal value, initialized to 0.5 by table parameters 1/64, and combines R+8*WIN-4. '
            'With whole-game game-start residuals and identical address normalization, its combined '
            'predictor equals V290 MC in real arithmetic; floating point and action ties can differ. '
            'Its terminal prediction is not a Bernoulli probability. The contrast does not isolate a pure '
            'capacity or pure function-class effect, and matched storage and writes do not imply equal CPU. '
            'Existing contexts reuse frozen parameters. False new-context decisions can acquire another '
            'paid cohort. Other-task diagnostic probes use first task detectors. Unsegmented full online '
            'discovery, continued improvement within a known context, unrestricted strategic learning and '
            'false-error guarantees remain unestablished.')
