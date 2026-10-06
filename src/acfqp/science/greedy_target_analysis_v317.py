"""Sampled coupled greedy versus factual SARSA targets on shared fixed-policy facts."""
from math import floor
import random
from statistics import mean

TASKS = ('A', 'B')
ROUNDS = ('1', '2')
INITIAL_ARMS = ('SOURCE', 'FIRST_LOCAL')
UPDATING_ARMS = ('SARSA_LOCAL', 'GREEDY_LOCAL')
ARMS = INITIAL_ARMS+UPDATING_ARMS
PAIRS = (('GREEDY_LOCAL', 'FIRST_LOCAL'), ('GREEDY_LOCAL', 'SARSA_LOCAL'),
    ('GREEDY_LOCAL', 'SOURCE'), ('SARSA_LOCAL', 'FIRST_LOCAL'),
    ('SARSA_LOCAL', 'SOURCE'), ('FIRST_LOCAL', 'SOURCE'))
BOOTSTRAP_SEED = 31700001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
PRIMARY_CONTRAST = 'GREEDY_LOCAL_minus_FIRST_LOCAL_FINAL_AB'


def _game_summary(evaluation, life, task, p):
    try:
        actual_p, games = evaluation['estimated_p_four'], evaluation['game_summaries']
    except KeyError as error:
        raise ValueError('V317 requires actual bank planning probability and evaluation games') from error
    if actual_p!=p:
        raise ValueError('Every V317 cell uses its immutable first-FIT bank planning belief')
    seeds = [317900000000+(100000 if task=='B' else 0)+life*1000000+episode for episode in range(32)]
    if len(games)!=32 or [game['seed'] for game in games]!=seeds:
        raise ValueError('V317 requires 32 fresh paired task seeds at every H2 checkpoint')
    if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
        raise ValueError('Evaluation games require explicit terminal or cutoff status')
    return dict(games=32, mean_game_utility=mean(game['utility'] for game in games),
        wins=sum(game['status']=='WON' for game in games),
        losses=sum(game['status']=='LOST' for game in games),
        cutoffs=sum(game['status']=='CUTOFF' for game in games),
        cutoff_episodes=[episode for episode, game in enumerate(games) if game['status']=='CUTOFF'],
        steps=sum(game['steps'] for game in games))


def _aggregate(rows):
    return dict(games=sum(row['games'] for row in rows), wins=sum(row['wins'] for row in rows),
        losses=sum(row['losses'] for row in rows), cutoffs=sum(row['cutoffs'] for row in rows),
        steps=sum(row['steps'] for row in rows), mean_game_utility=mean(row['mean_game_utility'] for row in rows))


def _bootstrap(records, values, draws):
    groups = {parent:[value for row, value in zip(records, values) if row['parent']==parent]
              for parent in range(4)}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group, k=4)) for group in groups.values())
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


def _gain_status(contrast, hold_reason):
    if hold_reason:
        return hold_reason
    lower, upper = contrast['ci95']
    return 'SUPPORTED_GAIN' if lower>0. else 'SUPPORTED_LOSS' if upper<0. else 'UNRESOLVED'


def _retention_status(contrast, hold_reason):
    if hold_reason:
        return hold_reason
    lower, upper = contrast['ci95']
    return 'SUPPORTED_NONDECREASE' if lower>=0. else 'SUPPORTED_LOSS' if upper<0. else 'UNRESOLVED'


def summarize(lifecycles, draws=20000):
    """Retain the complete operator-control cohort and separate growth from comparator gain."""
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=16 or [row['lifecycle'] for row in rows]!=list(range(16))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V317 needs all 16 new lifecycles under the four frozen V312 parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    try:
        failed_preconditions = [row['lifecycle'] for row in rows if not row['initial_context_precondition_met']]
    except KeyError as error:
        raise ValueError('V317 requires the observed initial distinct-bank precondition for every lifecycle') from error
    records, training_cutoffs = [], []
    physical = {arm:[] for arm in ARMS}
    for row in rows:
        cells = {}
        for task in TASKS:
            try:
                initial = row['initial'][task]
                p = initial['planning_belief']['estimated_p_four']
                training_cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, round='FIRST',
                    collector='SOURCE', episode=game['episode']) for game in initial['dataset']['games']
                    if game['status']=='CUTOFF')
                first_version = initial['head_versions']['FIRST_LOCAL']
                if initial['evaluations']['FIRST_LOCAL']['H2']['head_version']!=first_version:
                    raise ValueError('V317 FIRST_LOCAL evaluation must use its actual frozen v0 head')
                first = {arm:_game_summary(initial['evaluations'][arm]['H2'], row['lifecycle'], task, p)
                         for arm in INITIAL_ARMS}
            except KeyError as error:
                raise ValueError('V317 requires initial bank planning belief, head versions and both initial H2 cells') from error
            versions = {arm:first_version for arm in UPDATING_ARMS}
            cells['FIRST_'+task] = dict(task=task, checkpoint='FIRST', estimated_p_four=p, arms=first)
            for arm in INITIAL_ARMS:
                physical[arm].append(first[arm])
            for round_id in ROUNDS:
                try:
                    batch = row['rounds'][round_id][task]
                    quota, collectors = batch['quota'], batch['collectors']
                    if (set(collectors)!={'FIXED_FIRST'} or
                            collectors['FIXED_FIRST']['actor_version']!=first_version):
                        raise ValueError('V317 every collection batch must use the immutable FIRST_LOCAL v0 actor')
                    receipt = collectors['FIXED_FIRST']
                    selection = receipt['selection']
                    if (quota<=0 or selection['eligible_samples']!=quota or selection['selected_samples']!=quota
                            or selection['selection_rule']!='ALL_NONWINNING_COMPLETE_FIT_STATES'):
                        raise ValueError('V317 fits all eligible nonwinning complete-FIT states of its shared batch')
                    training_cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, round=round_id,
                        collector='FIXED_FIRST', episode=game['episode']) for game in receipt['dataset']['games']
                        if game['status']=='CUTOFF')
                    updated, writes = {}, []
                    for arm in UPDATING_ARMS:
                        item = batch['arms'][arm]
                        fit = item['fit']
                        if (fit['trained_afterstates']!=quota or item['updates_after']-item['updates_before']!=quota
                                or fit['alpha']!=.0025 or not fit['frozen_game_start_predictions']):
                            raise ValueError('V317 SARSA and GREEDY require the same state quota, alpha and game-start residual rule')
                        if item['updates_before']!=versions[arm]['updates']:
                            raise ValueError('V317 every batch continues its own actual learner updates')
                        if (item['head_version']==versions[arm] or
                                item['evaluations']['H2']['head_version']!=item['head_version']):
                            raise ValueError('V317 evaluation must use the advanced actual private learner head')
                        if (fit['bootstrap_version']!=versions[arm]
                                or not fit['frozen_batch_start_bootstrap']
                                or fit['bootstrap_mode']!='BATCH_START_FROZEN_OWN_HEAD' or not fit['target_artifact']):
                            raise ValueError('V317 both arms require their own batch-start bootstrap head and actual target artifact')
                        if arm=='GREEDY_LOCAL':
                            metadata = fit['target_artifact']['metadata']
                            if (metadata['schema']!='acfqp.local_sampled_greedy_targets.v317' or metadata['target_rule']!=
                                    'OBSERVED_POSTSPAWN_SINGLE_COMBINED_DIRECT_GREEDY_BRANCH'):
                                raise ValueError('V317 GREEDY requires the actual single combined-branch native target artifact')
                        counts = fit['normalization_counts']
                        writes.append((counts['reward_parameter_writes'], counts['risk_parameter_writes']))
                        updated[arm] = _game_summary(item['evaluations']['H2'], row['lifecycle'], task, p)
                        versions[arm] = item['head_version']
                        physical[arm].append(updated[arm])
                    if writes[0]!=writes[1]:
                        raise ValueError('V317 SARSA and GREEDY must have equal actual writes to both tables on the same batch')
                except KeyError as error:
                    raise ValueError('V317 requires both shared factual batches, private fits and batch-start target metadata') from error
                cells['ROUND'+round_id+'_'+task] = dict(task=task, checkpoint='ROUND'+round_id,
                    estimated_p_four=p, quota=quota, arms={**first, **updated})
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], cells=cells))

    def utility(row, key, arm):
        return row['cells'][key]['arms'][arm]['mean_game_utility']
    cells, rounds, checkpoints = {}, {}, {}
    for task in TASKS:
        key = 'FIRST_'+task
        cells[key] = dict(task=task, checkpoint='FIRST', paired_contrasts=dict(FIRST_LOCAL_minus_SOURCE=
            _bootstrap(records, [utility(row, key, 'FIRST_LOCAL')-utility(row, key, 'SOURCE') for row in records], draws)),
            arms={arm:_aggregate([row['cells'][key]['arms'][arm] for row in records]) for arm in INITIAL_ARMS})
    for round_id in ROUNDS:
        rounds[round_id] = {left+'_minus_'+right:_bootstrap(records,
            [mean(utility(row, 'ROUND'+round_id+'_'+task, left)-utility(row, 'ROUND'+round_id+'_'+task, right)
                  for task in TASKS) for row in records], draws) for left, right in PAIRS}
        for task in TASKS:
            key = 'ROUND'+round_id+'_'+task
            contrasts = {left+'_minus_'+right:_bootstrap(records,
                [utility(row, key, left)-utility(row, key, right) for row in records], draws) for left, right in PAIRS}
            cells[key] = dict(task=task, checkpoint='ROUND'+round_id, paired_contrasts=contrasts,
                arms={arm:_aggregate([row['cells'][key]['arms'][arm] for row in records]) for arm in ARMS})
            checkpoints[key] = {arm:_bootstrap(records,
                [utility(row, key, arm)-utility(row, key, 'FIRST_LOCAL') for row in records], draws)
                for arm in UPDATING_ARMS}
    final = rounds['2']
    arms = {arm:_aggregate(physical[arm]) for arm in ARMS}
    complete = not training_cutoffs and not any(value['cutoffs'] for value in arms.values())
    hold_reason = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else
                   'INITIAL_BANK_PRECONDITION_NOT_MET' if failed_preconditions else None)
    primary_status = _gain_status(final['GREEDY_LOCAL_minus_FIRST_LOCAL'], hold_reason)
    target_status = _gain_status(final['GREEDY_LOCAL_minus_SARSA_LOCAL'], hold_reason)
    net_status = _gain_status(final['GREEDY_LOCAL_minus_SOURCE'], hold_reason)
    sarsa_status = _gain_status(final['SARSA_LOCAL_minus_FIRST_LOCAL'], hold_reason)
    task_gain = {task:_gain_status(checkpoints['ROUND2_'+task]['GREEDY_LOCAL'], hold_reason) for task in TASKS}
    retention = {task:_retention_status(checkpoints['ROUND2_'+task]['GREEDY_LOCAL'], hold_reason) for task in TASKS}
    preserved = all(value=='SUPPORTED_NONDECREASE' for value in retention.values())
    primary, target = primary_status=='SUPPORTED_GAIN', target_status=='SUPPORTED_GAIN'
    return dict(arms=arms, cells=cells, round_ab_contrasts=rounds, final_ab_contrasts=final,
        checkpoint_contrasts=checkpoints, by_lifecycle=records, primary_contrast=PRIMARY_CONTRAST,
        primary_self_improvement_supported=primary, primary_self_improvement_status=primary_status,
        operator_intervention_supported=target, operator_intervention_status=target_status,
        final_net_gain_supported=net_status=='SUPPORTED_GAIN', final_net_gain_status=net_status,
        sarsa_self_improvement_supported=sarsa_status=='SUPPORTED_GAIN', sarsa_self_improvement_status=sarsa_status,
        final_task_improvement_supported={task:value=='SUPPORTED_GAIN' for task,value in task_gain.items()},
        final_task_improvement_status=task_gain, task_retention_status=retention,
        task_retention_supported=preserved, retained_improvement_supported=primary and preserved,
        operator_mechanism_supported=primary and preserved and target,
        checkpoint_status={key:{arm:_retention_status(value, hold_reason) for arm,value in contrasts.items()}
                           for key,contrasts in checkpoints.items()},
        complete_game_endpoints=complete, training_cutoffs=training_cutoffs,
        initial_context_precondition_met=not failed_preconditions,
        initial_precondition_failed_lifecycles=failed_preconditions,
        bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED, interval_scope=INTERVAL_SCOPE,
        estimator='EQUAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        primary_rule='Final GREEDY_LOCAL H2 minus its own frozen FIRST_LOCAL H2; strict positive lower CI. '
            'GREEDY minus SARSA identifies the operator intervention separately; net SOURCE cannot replace own-first improvement.',
        retention_rule='Literal final-minus-own-FIRST utility for A and B, each lower CI >= 0, is mandatory '
            'for retained improvement. Intermediate and SARSA own-FIRST checkpoints remain reported.',
        mechanism_rule='Retained own-FIRST improvement AND a positive GREEDY-minus-SARSA lower CI.',
        evidence_scope='Sixteen new operator-control lifecycles condition on four frozen fresh V312 SOURCE parents. '
            'Initial source-carried target '
            'facts, FIRST adaptation, subsequent fixed-policy target facts and evaluation seeds are new; '
            'no old target facts or evaluation outcomes are pooled. SOURCE weights '
            'and previously learned deterministic dynamics are reused; intervals do not include unconditional '
            'source-population uncertainty or establish full-pipeline independence. Initial A/B banks must '
            'be observed and confirmed; supplied task/round boundaries and immutable first-FIT beliefs '
            'do not establish unsegmented online discovery.',
        contribution_scope='SARSA and GREEDY start from private copies of the same FIRST_LOCAL head and share each '
            'new natural factual batch from its frozen H2 collector. Both update every nonwinning complete-FIT '
            'state with the same two tables, alpha, game-start residuals, address normalization and actual '
            'table-write counts. Both freeze their own batch-start bootstrap head. SARSA uses the actual '
            'recorded next action; GREEDY chooses one DIRECT action by immediate reward plus combined '
            'reward/WIN continuation on the actual observed postspawn board and uses that same branch '
            'for both component targets. Actual tapes and natural terminal labels stay intact. '
            'Extra action search, bootstrap reads, target saves, snapshot work and CPU are paid separately. '
            'This is an operator intervention under fixed FIRST state coverage, with sampled observed '
            'spawns, reused dynamics and immutable bank beliefs. It does not implement a full expected '
            'model or Bayesian operator, establish exact H2 operator equality, test actor feedback '
            'or establish structure learning.')
