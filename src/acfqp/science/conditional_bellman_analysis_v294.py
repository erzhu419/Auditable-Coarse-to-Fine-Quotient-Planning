"""Independent control effects and separate factual/source-policy diagnostics."""
from math import floor
import random
from statistics import mean

from .natural_episode_analysis_v292 import _aggregate
from .shadow_deployment_analysis_v293 import _direction

ARMS = ('FROZEN', 'MC_BOARD', 'MC_CONDITIONED', 'BELLMAN_BOARD', 'BELLMAN_CONDITIONED')
PHASES = ('A', 'B', 'A_prime')
PAIRS = (('BELLMAN_CONDITIONED', 'FROZEN'), ('MC_CONDITIONED', 'MC_BOARD'),
         ('BELLMAN_CONDITIONED', 'BELLMAN_BOARD'), ('BELLMAN_BOARD', 'MC_BOARD'),
         ('BELLMAN_CONDITIONED', 'MC_CONDITIONED'))
PRIMARY_CONTRAST = 'BELLMAN_CONDITIONED_minus_FROZEN'
BOOTSTRAP_SEED = 29400001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def science_seed(life, phase, episode):
    return 294900010000+life*1000000+phase*100000+episode


def ranking_seed(life, phase, anchor, replica):
    return 294600010000+life*1000000+phase*100000+anchor*1000+replica


def _bootstrap(records, values, draws):
    groups = {parent:[value for row,value in zip(records, values) if row['parent']==parent]
              for parent in range(4)}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group, k=4)) for group in groups.values())
                     for _ in range(draws))
    def quantile(q):
        position=(draws-1)*q; lo=floor(position); hi=min(lo+1, draws-1)
        return samples[lo]+(samples[hi]-samples[lo])*(position-lo)
    return dict(mean=mean(values), ci95=[quantile(.025), quantile(.975)],
        lifecycle_deltas={str(row['lifecycle']):value for row,value in zip(records, values)},
        improved_equal_worse=[sum(value>0. for value in values), sum(value==0. for value in values),
                              sum(value<0. for value in values)],
        adverse_lifecycles=[row['lifecycle'] for row,value in zip(records, values) if value<0.],
        parent_mean_deltas={str(parent):mean(group) for parent,group in groups.items()},
        interval_scope=INTERVAL_SCOPE)


def _games(games, life, phase):
    if len(games)!=32 or [g['seed'] for g in games]!=[science_seed(life, phase, i) for i in range(32)]:
        raise ValueError('V294 science requires all 32 new paired seeds')
    if any(g['status'] not in ('WON', 'LOST', 'CUTOFF') for g in games):
        raise ValueError('Scientific games must retain actual terminal or cutoff status')
    return dict(games=32, mean_game_utility=mean(g['utility'] for g in games),
        wins=sum(g['status']=='WON' for g in games), losses=sum(g['status']=='LOST' for g in games),
        cutoffs=sum(g['status']=='CUTOFF' for g in games), steps=sum(g['steps'] for g in games))


def _signed(contrast):
    contrast['positive_zero_negative']=contrast.pop('improved_equal_worse')
    contrast['negative_lifecycles']=contrast.pop('adverse_lifecycles')
    return contrast


def _heldout(scored, expected):
    games = scored['game_metrics']
    if [game['metadata'] for game in games]!=expected:
        raise ValueError('All heads must score the same chronological factual heldout games')
    return dict(games=len(games), afterstates=sum(game['count'] for game in games),
                **{key:mean(game[key] for game in games) for key in ('mse', 'mae', 'bias')})


def _ranking(anchors, life, phase_index, expected):
    if len(anchors)!=3 or [a['anchor_id'] for a in anchors]!=[a['anchor_id'] for a in expected]:
        raise ValueError('Ranking requires three fixed first-heldout-game anchors')
    rows, cutoffs, rollouts = [], 0, 0
    for anchor_index, (anchor, source) in enumerate(zip(anchors, expected)):
        for key in ('episode', 'step', 'board_before_action', 'model_p_four'):
            if anchor[key]!=source[key]:
                raise ValueError('Ranking must retain the predetermined board and before-action p')
        reference = anchor['reference']
        env_p = .5 if phase_index==1 else .1
        if reference['model_p_four']!=anchor['model_p_four'] or reference['environment_p_four']!=env_p:
            raise ValueError('SOURCE continuation belief and actual generating law must remain separate')
        samples = reference['rollouts']; actions = sorted({sample['action'] for sample in samples})
        q = {}
        for action in actions:
            selected = [sample for sample in samples if sample['action']==action]
            if (len(selected)!=32 or [sample['seed'] for sample in selected]
                    !=[ranking_seed(life, phase_index, anchor_index, i) for i in range(32)]):
                raise ValueError('Every legal action uses its 32 fresh common replica seeds')
            q[action] = mean(sample['total_utility'] for sample in selected)
        cutoffs += sum(sample['status']=='CUTOFF' for sample in samples); rollouts += len(samples)
        source_action = anchor['choices']['FROZEN']['action']
        choices = {}
        for arm in ARMS:
            action = anchor['choices'][arm]['action']
            choices[arm] = dict(reference_utility=q[action], reference_regret=max(q.values())-q[action],
                change_from_source_action=q[action]-q[source_action], changed_action=action!=source_action)
        rows.append(dict(anchor_id=anchor['anchor_id'], action_means=q, choices=choices))
    return dict(arms={arm:dict(anchors=3, changed_actions=sum(row['choices'][arm]['changed_action'] for row in rows),
        **{key:mean(row['choices'][arm][key] for row in rows) for key in
           ('reference_utility', 'reference_regret', 'change_from_source_action')}) for arm in ARMS},
        anchors=rows, cutoffs=cutoffs, rollouts=rollouts)


def _interaction(record, field, phase=None):
    def value(arm):
        item=record['arms'][arm] if phase is None else record['arms'][arm]['phases'][phase]
        return item['mean_game_utility'] if field=='utility' else item['heldout'][field]
    return (value('BELLMAN_CONDITIONED')-value('BELLMAN_BOARD'))-(value('MC_CONDITIONED')-value('MC_BOARD'))


def analyze(lifecycles, draws=20000):
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=16 or [row['lifecycle'] for row in rows]!=list(range(16))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V294 requires sixteen paired lives under four fixed source parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    records, ranking_cutoffs, ranking_rollouts = [], 0, 0
    for row in rows:
        life, arms = row['lifecycle'], {}
        rank = {}
        for phase_index, phase in enumerate(PHASES):
            rank[phase] = _ranking(row['ranking'][phase]['anchors'], life, phase_index,
                                  row['dataset']['phases'][phase]['anchors'])
            ranking_cutoffs += rank[phase]['cutoffs']; ranking_rollouts += rank[phase]['rollouts']
        for arm in ARMS:
            original = row['arms'][arm]['phases']; phases = {}
            p_a = original['A']['snapshot']['estimated_p_four']
            for phase_index, phase in enumerate(PHASES):
                value = original[phase]; probe = value['retention_probe']
                p = row['dataset']['snapshots'][phase]['estimated_p_four']
                if value['snapshot']['estimated_p_four']!=p:
                    raise ValueError('All heads must use the original observed carrier checkpoint p')
                if (probe['model_p_four']!=p_a or probe['environment_p_four']!=.1 or probe['depth']!=2
                        or probe['shared_with_current']!=(phase_index==0)):
                    raise ValueError('Fixed-A probes require saved A p and original A science seeds')
                if phase_index==0 and probe['game_summaries']!=value['game_summaries']:
                    raise ValueError('A current science games must be shared with the initial A probe')
                phases[phase] = dict(_games(value['game_summaries'], life, phase_index),
                    heldout=_heldout(value['heldout'], row['dataset']['phases'][phase]['heldout_games']),
                    ranking=rank[phase]['arms'][arm], retention_probe=_games(probe['game_summaries'], life, 0))
            ahead = original['B']['a_head_on_B']; p_b = original['B']['snapshot']['estimated_p_four']
            if (ahead['model_p_four']!=p_b or ahead['environment_p_four']!=.5 or ahead['depth']!=2
                    or ahead['shared_with_current']!=(arm=='FROZEN')):
                raise ValueError('A parameter reference on B must be read at current B p')
            if arm=='FROZEN' and ahead['game_summaries']!=original['B']['game_summaries']:
                raise ValueError('FROZEN A-head-on-B reference shares its exact current B games')
            phases['B']['a_head_on_B'] = _games(ahead['game_summaries'], life, 1)
            arms[arm] = dict(mean_game_utility=mean(value['mean_game_utility'] for value in phases.values()),
                heldout={key:mean(value['heldout'][key] for value in phases.values()) for key in ('mse', 'mae', 'bias')},
                ranking={key:mean(value['ranking'][key] for value in phases.values()) for key in
                         ('reference_utility', 'reference_regret', 'change_from_source_action')}, phases=phases)
        records.append(dict(lifecycle=life, parent=row['parent'], arms=arms, ranking=rank))
    arms = {}
    for arm in ARMS:
        phases = {}
        for phase in PHASES:
            values = [row['arms'][arm]['phases'][phase] for row in records]
            phases[phase] = dict(_aggregate(values),
                heldout={key:mean(value['heldout'][key] for value in values) for key in ('mse', 'mae', 'bias')},
                ranking={key:mean(value['ranking'][key] for value in values) for key in
                         ('reference_utility', 'reference_regret', 'change_from_source_action')},
                retention_probe=_aggregate([value['retention_probe'] for value in values]))
        arms[arm] = dict(mean_game_utility=mean(row['arms'][arm]['mean_game_utility'] for row in records),
            heldout={key:mean(row['arms'][arm]['heldout'][key] for row in records) for key in ('mse', 'mae', 'bias')},
            phases=phases, **{key:sum(value[key] for value in phases.values()) for key in ('games', 'wins', 'losses', 'cutoffs', 'steps')})
    paired, heldout, ranking, phase_contrasts = {}, {}, {}, {phase:{} for phase in PHASES}
    for left,right in PAIRS:
        name=left+'_minus_'+right
        paired[name]=_bootstrap(records, [r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records], draws)
        heldout[name]={key:_bootstrap(records, [r['arms'][left]['heldout'][key]-r['arms'][right]['heldout'][key] for r in records], draws)
                       for key in ('mse', 'mae', 'bias')}
        for key,contrast in heldout[name].items():
            positive,zero,negative=_signed(contrast)['positive_zero_negative']
            if key in ('mse','mae'):
                contrast['better_equal_worse']=[negative,zero,positive]
                contrast['worse_lifecycles']=[int(life) for life,value in contrast['lifecycle_deltas'].items() if value>0.]
        ranking[name]=_bootstrap(records, [r['arms'][left]['ranking']['reference_utility']
                                         -r['arms'][right]['ranking']['reference_utility'] for r in records], draws)
        for phase in PHASES:
            phase_contrasts[phase][name]=_bootstrap(records, [r['arms'][left]['phases'][phase]['mean_game_utility']
                -r['arms'][right]['phases'][phase]['mean_game_utility'] for r in records], draws)
    interaction=dict(utility=_bootstrap(records, [_interaction(r, 'utility') for r in records], draws),
        heldout_mse=_signed(_bootstrap(records, [_interaction(r, 'mse') for r in records], draws)),
        phases={p:_bootstrap(records, [_interaction(r, 'utility', p) for r in records], draws) for p in PHASES})
    corrections, retention = {}, {}
    for arm in ARMS:
        corrections[arm]=_bootstrap(records, [r['arms'][arm]['phases']['B']['mean_game_utility']
            -r['arms'][arm]['phases']['B']['a_head_on_B']['mean_game_utility'] for r in records], draws)
        retention[arm]={}
        for name,p,q in (('after_B','B','A'), ('restoration','A_prime','B'), ('final_vs_A','A_prime','A')):
            c=_bootstrap(records, [r['arms'][arm]['phases'][p]['retention_probe']['mean_game_utility']
                -r['arms'][arm]['phases'][q]['retention_probe']['mean_game_utility'] for r in records], draws)
            retention[arm][name]=dict(c, direction=_direction(c))
    current_cutoffs=sum(value['cutoffs'] for value in arms.values())
    additional_cutoffs=sum(arms[a]['phases'][p]['retention_probe']['cutoffs'] for a in ARMS for p in ('B', 'A_prime'))
    additional_cutoffs+=sum(r['arms'][a]['phases']['B']['a_head_on_B']['cutoffs'] for r in records for a in ARMS[1:])
    complete=current_cutoffs+additional_cutoffs==0
    net=complete and paired[PRIMARY_CONTRAST]['ci95'][0]>0.
    return dict(arms=arms, paired_contrasts=paired, phase_contrasts=phase_contrasts,
        primary_contrast=PRIMARY_CONTRAST, heldout_contrasts=heldout, ranking_contrasts=ranking,
        factor_interaction=interaction, correction_contrasts=corrections, retention_contrasts=retention,
        net_gain_supported=net, complete_game_endpoints=complete,
        correction_supported=complete and corrections['BELLMAN_CONDITIONED']['ci95'][0]>0.,
        science_cutoffs=current_cutoffs+additional_cutoffs, ranking_cutoffs=ranking_cutoffs,
        physical_science_games=14848, logical_science_game_references=17920,
        ranking_anchors=144, ranking_rollouts=ranking_rollouts,
        bootstrap_seed=BOOTSTRAP_SEED, bootstrap_draws=draws, by_lifecycle=records,
        interval_scope=INTERVAL_SCOPE, estimator='EQUAL_GAMES_THEN_PHASES_THEN_LIFECYCLES',
        target_interpretation='MC estimates factual SOURCE-policy returns; expected Bellman uses a frozen-belief max-control objective. '
            'This changes the objective as well as the estimator.',
        heldout_interpretation='Factual SOURCE-policy prediction error, with whole-game label holdout; model-created Bellman labels are not validation truth.',
        ranking_interpretation='Finite SOURCE-H2 continuation values at fixed observed anchor p and actual phase law; not optimal-policy Q. '
            'Independent full-game utility decides the primary result.',
        retention_interpretation='Signed fixed-A changes. A confidence interval crossing zero does not establish preservation.',
        evidence_scope='Exploratory same-retained-carrier target/representation comparison with new independent science streams; '
            'conditional on four old source parents, without new training environment acquisition.')
