"""Fresh paired evaluation of frozen V314 reward/WIN component combinations."""
from math import floor
import random
from statistics import mean

TASKS = ('A', 'B')
ARMS = ('MC_MC', 'TD_MC', 'MC_TD', 'TD_TD', 'FIRST_LOCAL')
COMBINATIONS = ARMS[:4]
MECHANISMS = {
    'reward_given_MC_WIN': (('TD_MC', 1.), ('MC_MC', -1.)),
    'reward_given_TD_WIN': (('TD_TD', 1.), ('MC_TD', -1.)),
    'WIN_given_MC_reward': (('MC_TD', 1.), ('MC_MC', -1.)),
    'WIN_given_TD_reward': (('TD_TD', 1.), ('TD_MC', -1.)),
    'interaction': (('TD_TD', 1.), ('TD_MC', -1.), ('MC_TD', -1.), ('MC_MC', 1.)),
}
SECONDARY_PAIRS = (('TD_TD', 'MC_MC'),)+tuple((arm, 'FIRST_LOCAL') for arm in COMBINATIONS)
BOOTSTRAP_SEED = 31500001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_REALIZED_V314_HEADS'


def _game_summary(evaluation, life, task, p):
    try:
        actual_p, games = evaluation['estimated_p_four'], evaluation['game_summaries']
    except KeyError as error:
        raise ValueError('V315 requires actual immutable bank planning probability and evaluation games') from error
    if actual_p!=p:
        raise ValueError('Every V315 combination uses the same immutable V314 bank planning belief')
    seeds = [315900000000+life*1000000+(100000 if task=='B' else 0)+episode for episode in range(32)]
    if len(games)!=32 or [game['seed'] for game in games]!=seeds:
        raise ValueError('V315 requires 32 fresh paired seeds for every frozen combination and FIRST')
    if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
        raise ValueError('Evaluation games require explicit natural terminal or cutoff status')
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


def _bootstrap(records, values, draws, levels=(.95,)):
    groups = {parent:[value for row, value in zip(records, values) if row['parent']==parent]
              for parent in range(4)}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group, k=4)) for group in groups.values())
                     for _ in range(draws))
    def quantile(q):
        position = (draws-1)*q
        lower, upper = floor(position), min(floor(position)+1, draws-1)
        return samples[lower]+(samples[upper]-samples[lower])*(position-lower)
    result = dict(mean=mean(values), lifecycle_deltas={str(row['lifecycle']):value for row,value in zip(records, values)},
        improved_equal_worse=[sum(value>0. for value in values), sum(value==0. for value in values),
                              sum(value<0. for value in values)],
        adverse_lifecycles=[row['lifecycle'] for row,value in zip(records, values) if value<0.],
        parent_mean_deltas={str(parent):mean(group) for parent,group in groups.items()},
        interval_scope=INTERVAL_SCOPE)
    for level in levels:
        tail = .025 if level==.95 else .005
        result['ci'+str(round(level*100))] = [quantile(tail), quantile(1.-tail)]
    return result


def _effect_status(interval, hold_reason):
    if hold_reason:
        return hold_reason
    lower, upper = interval
    return 'SUPPORTED_POSITIVE' if lower>0. else 'SUPPORTED_NEGATIVE' if upper<0. else 'UNRESOLVED'


def _retention_status(interval, hold_reason):
    if hold_reason:
        return hold_reason
    lower, upper = interval
    return 'SUPPORTED_NONDECREASE' if lower>=0. else 'SUPPORTED_LOSS' if upper<0. else 'UNRESOLVED'


def summarize(lifecycles, draws=20000):
    """Five prespecified mechanism effects; FIRST comparisons remain secondary."""
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=16 or [row['lifecycle'] for row in rows]!=list(range(16))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V315 requires all 16 realized V314 lives and their four fixed parent groups')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    records = []
    for row in rows:
        cells = {}
        for task in TASKS:
            try:
                item = row['tasks'][task]
                context_id, p, components = item['context_id'], item['estimated_p_four'], item['head_components']
                mc, td, first = (components[arm] for arm in ('MC_MC', 'TD_TD', 'FIRST_LOCAL'))
                if (mc['reward_version']!=mc['win_version'] or td['reward_version']!=td['win_version']
                        or first['reward_version']!=first['win_version']
                        or components['TD_MC']!=dict(reward_version=td['reward_version'], win_version=mc['win_version'])
                        or components['MC_TD']!=dict(reward_version=mc['reward_version'], win_version=td['win_version'])):
                    raise ValueError('V315 frozen hybrid heads must use the specified reward and WIN version components')
                arms = {arm:_game_summary(item['evaluations'][arm], row['lifecycle'], task, p) for arm in ARMS}
            except KeyError as error:
                raise ValueError('V315 requires selected-bank metadata and all five actual frozen component evaluations') from error
            cells[task] = dict(task=task, context_id=context_id, estimated_p_four=p,
                              head_components=components, arms=arms)
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], cells=cells))

    def effect(row, task, terms):
        return sum(coefficient*row['cells'][task]['arms'][arm]['mean_game_utility'] for arm,coefficient in terms)
    arms = {arm:_aggregate([row['cells'][task]['arms'][arm] for row in records for task in TASKS]) for arm in ARMS}
    complete = not any(value['cutoffs'] for value in arms.values())
    hold_reason = None if complete else 'INCOMPLETE_GAME_ENDPOINTS'
    mechanisms = {key:_bootstrap(records,
        [mean(effect(row, task, terms) for task in TASKS) for row in records], draws, levels=(.95,.99))
        for key,terms in MECHANISMS.items()}
    for contrast in mechanisms.values():
        contrast['family_status'] = _effect_status(contrast['ci99'], hold_reason)
    secondary = {left+'_minus_'+right:_bootstrap(records,
        [mean(effect(row, task, ((left,1.),(right,-1.))) for task in TASKS) for row in records], draws)
        for left,right in SECONDARY_PAIRS}
    cells = {task:dict(task=task,
        arms={arm:_aggregate([row['cells'][task]['arms'][arm] for row in records]) for arm in ARMS},
        mechanism_contrasts={key:_bootstrap(records, [effect(row, task, terms) for row in records], draws)
                             for key,terms in MECHANISMS.items()},
        secondary_contrasts={left+'_minus_'+right:_bootstrap(records,
            [effect(row, task, ((left,1.),(right,-1.))) for row in records], draws)
            for left,right in SECONDARY_PAIRS}) for task in TASKS}
    retention = {arm:{task:_retention_status(cells[task]['secondary_contrasts'][arm+'_minus_FIRST_LOCAL']['ci95'],
                                           hold_reason) for task in TASKS} for arm in COMBINATIONS}
    return dict(arms=arms, cells=cells, by_lifecycle=records, mechanism_contrasts=mechanisms,
        mechanism_family_status={key:value['family_status'] for key,value in mechanisms.items()},
        secondary_contrasts=secondary, task_retention_status=retention,
        task_retention_supported={arm:all(value=='SUPPORTED_NONDECREASE' for value in tasks.values())
                                 for arm,tasks in retention.items()},
        complete_game_endpoints=complete, bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        interval_scope=INTERVAL_SCOPE, estimator='EQUAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        primary_family=list(MECHANISMS), mechanism_family_size=5, family_error_rate=.05,
        family_interval_level=.99, family_adjustment='BONFERRONI_FIVE_TWO_SIDED_EFFECTS',
        mechanism_rule='Exactly five equal-A/B prespecified effects use two-sided Bonferroni 99% bootstrap '
            'intervals for family-status decisions; pointwise 95% intervals are also retained. '
            'Positive/negative interaction describes departure from additive component effects on utility. '
            'Task mechanism intervals are pointwise 95% descriptive intervals outside this five-effect family.',
        secondary_rule='Fresh TD_TD-minus-MC_MC and all four frozen combinations minus FIRST use pointwise '
            '95% intervals. Per-task nondecrease requires lower >= 0; loss requires upper < 0. '
            'These secondary results do not select a winner or confirm new growth.',
        evidence_scope='Fresh evaluation only of the same sixteen realized V314 lifecycles and frozen learned '
            'heads, conditional on their four frozen V312 SOURCE parents. V314 target facts, fixed FIRST '
            'collector, fitted parameters, bank ownership and deterministic dynamics are reused. '
            'No new training cohort or source training occurs, and old evaluation outcomes are not pooled. '
            'Intervals exclude source-population and new-training-cohort uncertainty; this is development '
            'mechanism decomposition, not independent learning confirmation or full-pipeline independence.',
        contribution_scope='The first arm token selects reward and the second WIN. Fixed FIRST collection '
            'and component-separate MC/TD targets and gradients permit the two hybrid heads to reuse '
            'actual learned tables without another fit. All five arms use H2, the same actual bank belief '
            'and paired new evaluation seeds. The five effects measure decision-utility contributions '
            'and interaction of these realized component estimators; they do not identify a microscopic '
            'learning cause or equate factual policy targets with an optimal counterfactual H2 operator.')
