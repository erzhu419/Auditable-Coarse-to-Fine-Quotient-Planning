"""Own-first improvement and collector feedback on fresh natural-game cohorts."""
from math import floor
import random
from statistics import mean

TASKS = ('A', 'B')
ROUNDS = ('1', '2')
INITIAL_ARMS = ('SOURCE', 'FIRST_LOCAL', 'FIRST_LINEAR')
UPDATING_ARMS = ('FIXED_LOCAL', 'CLOSED_LOCAL', 'CLOSED_LINEAR')
ARMS = INITIAL_ARMS+UPDATING_ARMS
DIRECT_ARMS = ('FIRST_LOCAL', 'FIRST_LINEAR', 'CLOSED_LOCAL', 'CLOSED_LINEAR')
PAIRS = (('CLOSED_LOCAL', 'FIRST_LOCAL'), ('CLOSED_LOCAL', 'FIXED_LOCAL'),
    ('CLOSED_LOCAL', 'CLOSED_LINEAR'), ('CLOSED_LOCAL', 'SOURCE'),
    ('CLOSED_LINEAR', 'FIRST_LINEAR'), ('CLOSED_LINEAR', 'SOURCE'))
BOOTSTRAP_SEED = 31300001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
PRIMARY_CONTRAST = 'CLOSED_LOCAL_minus_FIRST_LOCAL_FINAL_AB'


def _game_summary(evaluation, life, task, p):
    try:
        actual_p, games = evaluation['estimated_p_four'], evaluation['game_summaries']
    except KeyError as error:
        raise ValueError('V313 requires actual planning probability and complete evaluation games') from error
    if actual_p!=p:
        raise ValueError('Every V313 H2/DIRECT cell uses its immutable first-FIT bank planning belief')
    seeds = [313900000000+(100000 if task=='B' else 0)+life*1000000+episode for episode in range(32)]
    if len(games)!=32 or [game['seed'] for game in games]!=seeds:
        raise ValueError('V313 requires 32 fresh paired task seeds at every checkpoint and planner')
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
    """Keep all sixteen development lives; feedback and SOURCE are separate endpoints."""
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=16 or [row['lifecycle'] for row in rows]!=list(range(16))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V313 needs all 16 new lifecycles under the four frozen V312 parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    try:
        failed_preconditions = [row['lifecycle'] for row in rows if not row['initial_context_precondition_met']]
    except KeyError as error:
        raise ValueError('V313 requires the observed initial distinct-bank precondition for every lifecycle') from error
    records, training_cutoffs, unchanged_actors = [], [], []
    physical = {arm:[] for arm in ARMS}
    for row in rows:
        cells, direct, versions = {}, {}, {}
        for task in TASKS:
            try:
                initial = row['initial'][task]
                p = initial['planning_belief']['estimated_p_four']
                training_cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, round='FIRST',
                    collector='SOURCE', episode=game['episode']) for game in initial['dataset']['games']
                    if game['status']=='CUTOFF')
                first_versions = initial['head_versions']
                versions[task] = {arm:first_versions['FIRST_LINEAR' if arm=='CLOSED_LINEAR' else 'FIRST_LOCAL']
                                  for arm in UPDATING_ARMS}
                first = {arm:_game_summary(initial['evaluations'][arm]['H2'], row['lifecycle'], task, p)
                         for arm in INITIAL_ARMS}
            except KeyError as error:
                raise ValueError('V313 requires initial bank planning belief, head versions and all initial H2 cells') from error
            cells['FIRST_'+task] = dict(task=task, checkpoint='FIRST', estimated_p_four=p, arms=first)
            for arm in INITIAL_ARMS:
                physical[arm].append(first[arm])
            for round_id in ROUNDS:
                try:
                    batch = row['rounds'][round_id][task]
                    quota, collectors = batch['quota'], batch['collectors']
                    if round_id=='1':
                        expected = {'SHARED_LOCAL':first_versions['FIRST_LOCAL'],
                                    'CLOSED_LINEAR':first_versions['FIRST_LINEAR']}
                    else:
                        expected = {'CLOSED_LOCAL':versions[task]['CLOSED_LOCAL'],
                                    'FIXED_LOCAL':first_versions['FIRST_LOCAL'],
                                    'CLOSED_LINEAR':versions[task]['CLOSED_LINEAR']}
                    if set(collectors)!=set(expected) or any(
                            collectors[arm]['actor_version']!=version for arm, version in expected.items()):
                        raise ValueError('V313 collectors must use the previous actual head version; FIXED_LOCAL keeps v0')
                    fitted = batch['arms']
                    for collector, receipt in collectors.items():
                        training_cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, round=round_id,
                            collector=collector, episode=game['episode']) for game in receipt['dataset']['games']
                            if game['status']=='CUTOFF')
                    updated = {}
                    for arm in UPDATING_ARMS:
                        item = fitted[arm]
                        if (quota<=0 or item['fit']['trained_afterstates']!=quota
                                or item['updates_after']-item['updates_before']!=quota):
                            raise ValueError('All three V313 branches must fit the same positive selected-state quota')
                        if round_id=='2' and item['updates_before']!=row['rounds']['1'][task]['arms'][arm]['updates_after']:
                            raise ValueError('V313 round two continues its own round-one learner updates')
                        if item['head_version']==versions[task][arm]:
                            raise ValueError('V313 consolidation must advance the actual head-version receipt')
                        if round_id=='1' and arm in ('CLOSED_LOCAL', 'CLOSED_LINEAR'):
                            if item['head_version']['changed_parameters']==0:
                                unchanged_actors.append(dict(lifecycle=row['lifecycle'], task=task, arm=arm,
                                    version=1, changed_parameters=0))
                        updated[arm] = _game_summary(item['evaluations']['H2'], row['lifecycle'], task, p)
                        versions[task][arm] = item['head_version']
                        physical[arm].append(updated[arm])
                except KeyError as error:
                    raise ValueError('V313 requires both factual collection/consolidation rounds and actor-version metadata') from error
                cells['ROUND'+round_id+'_'+task] = dict(task=task, checkpoint='ROUND'+round_id,
                    estimated_p_four=p, quota=quota, arms={**first, **updated})
            try:
                direct[task] = {arm:_game_summary(row['final_direct'][task][arm], row['lifecycle'], task, p)
                                for arm in DIRECT_ARMS}
            except KeyError as error:
                raise ValueError('V313 requires same-head DIRECT endpoints for first and final LOCAL/LINEAR') from error
            for arm in DIRECT_ARMS:
                physical[arm].append(direct[task][arm])
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], cells=cells, direct=direct))

    def utility(row, round_id, task, arm):
        return row['cells']['ROUND'+round_id+'_'+task]['arms'][arm]['mean_game_utility']
    cells, rounds, checkpoints = {}, {}, {}
    for round_id in ROUNDS:
        rounds[round_id] = {left+'_minus_'+right:_bootstrap(records,
            [mean(utility(row, round_id, task, left)-utility(row, round_id, task, right) for task in TASKS)
             for row in records], draws) for left, right in PAIRS}
        for task in TASKS:
            key = 'ROUND'+round_id+'_'+task
            contrasts = {left+'_minus_'+right:_bootstrap(records,
                [utility(row, round_id, task, left)-utility(row, round_id, task, right) for row in records], draws)
                for left, right in PAIRS}
            cells[key] = dict(task=task, checkpoint='ROUND'+round_id, paired_contrasts=contrasts,
                arms={arm:_aggregate([row['cells'][key]['arms'][arm] for row in records]) for arm in ARMS})
            checkpoints[key] = {arm:_bootstrap(records,
                [utility(row, round_id, task, arm)-utility(row, round_id, task,
                    'FIRST_LINEAR' if arm=='CLOSED_LINEAR' else 'FIRST_LOCAL') for row in records], draws)
                for arm in UPDATING_ARMS}
    final = rounds['2']
    planning = {}
    for arm in DIRECT_ARMS:
        round_id = '2'
        def delta(row, task):
            return utility(row, round_id, task, arm)-row['direct'][task][arm]['mean_game_utility']
        planning[arm] = dict(final_ab=_bootstrap(records,
            [mean(delta(row, task) for task in TASKS) for row in records], draws),
            by_task={task:_bootstrap(records, [delta(row, task) for row in records], draws) for task in TASKS})
    arms = {arm:_aggregate(physical[arm]) for arm in ARMS}
    complete = not training_cutoffs and not any(value['cutoffs'] for value in arms.values())
    hold_reason = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else
                   'INITIAL_BANK_PRECONDITION_NOT_MET' if failed_preconditions else None)
    primary_status = _gain_status(final['CLOSED_LOCAL_minus_FIRST_LOCAL'], hold_reason)
    feedback_status = _gain_status(final['CLOSED_LOCAL_minus_FIXED_LOCAL'], hold_reason)
    net_status = _gain_status(final['CLOSED_LOCAL_minus_SOURCE'], hold_reason)
    task_gain = {task:_gain_status(cells['ROUND2_'+task]['paired_contrasts']['CLOSED_LOCAL_minus_FIRST_LOCAL'], hold_reason)
                 for task in TASKS}
    retention = {task:_retention_status(checkpoints['ROUND2_'+task]['CLOSED_LOCAL'], hold_reason) for task in TASKS}
    preserved = all(value=='SUPPORTED_NONDECREASE' for value in retention.values())
    primary = primary_status=='SUPPORTED_GAIN'
    feedback = feedback_status=='SUPPORTED_GAIN'
    return dict(arms=arms, cells=cells, round_ab_contrasts=rounds, final_ab_contrasts=final,
        checkpoint_contrasts=checkpoints, planning_contributions=planning, by_lifecycle=records,
        primary_contrast=PRIMARY_CONTRAST, primary_self_improvement_supported=primary,
        primary_self_improvement_status=primary_status, feedback_supported=feedback,
        feedback_status=feedback_status, final_net_gain_supported=net_status=='SUPPORTED_GAIN',
        final_net_gain_status=net_status, final_task_improvement_supported={task:value=='SUPPORTED_GAIN' for task,value in task_gain.items()},
        final_task_improvement_status=task_gain, task_retention_status=retention,
        task_retention_supported=preserved, retained_improvement_supported=primary and preserved,
        actor_change_premise_met=not unchanged_actors,
        actor_change_premise_status='MET' if not unchanged_actors else 'HOLD_NO_ACTOR_CHANGE',
        unchanged_round_two_actors=unchanged_actors,
        closed_loop_mechanism_supported=primary and preserved and feedback and not unchanged_actors,
        mechanism_rule='Retained own-first improvement AND feedback gain AND actual parameter changes in '
            'every CLOSED v1 head used for round-two collection. An unchanged actor is a valid physical '
            'result retained as premise HOLD; utility contrasts remain reported.',
        checkpoint_status={key:{arm:_retention_status(value, hold_reason) for arm,value in contrasts.items()}
                           for key,contrasts in checkpoints.items()},
        complete_game_endpoints=complete, training_cutoffs=training_cutoffs,
        initial_context_precondition_met=not failed_preconditions,
        initial_precondition_failed_lifecycles=failed_preconditions,
        bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        interval_scope=INTERVAL_SCOPE, estimator='EQUAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        primary_rule='Final CLOSED_LOCAL H2 minus its own frozen first-adapted LOCAL H2; strict positive lower CI. '
            'Feedback over FIXED_LOCAL is a separate mechanistic endpoint; net SOURCE gain cannot replace own-first improvement.',
        retention_rule='Literal final-minus-own-first per-task utility: lower >= 0 supports nondecrease; '
            'upper < 0 supports loss; otherwise unresolved. Intermediate checkpoints are retained descriptively.',
        evidence_scope='Sixteen new development lifecycles condition on the four frozen fresh V312 SOURCE parents. '
            'Initial and subsequent target facts and evaluation seeds are new; no old target outcomes are pooled. '
            'SOURCE value weights and previously learned deterministic dynamics are reused. Intervals do not '
            'include unconditional source-population uncertainty or establish full-pipeline independence. '
            'The A/B banks must be observed and confirmed initially; supplied task/round boundaries and fixed '
            'first-FIT bank beliefs do not establish unsegmented online discovery.',
        contribution_scope='All three updating branches have two active tables, two scheduled update rounds, '
            'the same selected-state quota, alpha and game-start normalization rule. Actual address writes '
            'and CPU may differ. Round-one LOCAL facts are physically shared, with private learner arrays '
            'and fits; round two closes the updated-collector feedback loop. CLOSED_LINEAR collects with '
            'its own updated head, so LOCAL-versus-LINEAR includes factual coverage and collector outcomes. '
            'Every label remains the factual return and natural terminal outcome of its batch collector, '
            'with no stale-policy label mixing. H2-minus-DIRECT compares each supplied same head on paired '
            'game seeds; it does not change the collection or fitting policy. LINEAR terminal predictions '
            'are unclipped values, not Bernoulli probabilities. SOURCE identity is conditional on task and '
            'actual bank planning probability; raw own-first losses are not SOURCE-adjusted away.')
