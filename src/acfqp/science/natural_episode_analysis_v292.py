"""Continuous-game learning, same-law correction, and fixed-A retention."""
from math import floor
import random
from statistics import mean

ARMS = ('FROZEN_H2', 'NSEQ_H2', 'MEAN_H2', 'FROZEN_DIRECT', 'MEAN_DIRECT')
PHASES = ('A', 'B', 'A_prime')
PAIRS = (('MEAN_H2', 'FROZEN_H2'), ('NSEQ_H2', 'FROZEN_H2'),
         ('MEAN_H2', 'NSEQ_H2'), ('FROZEN_H2', 'FROZEN_DIRECT'),
         ('MEAN_DIRECT', 'FROZEN_DIRECT'), ('MEAN_H2', 'MEAN_DIRECT'))
PRIMARY_CONTRAST = 'MEAN_H2_minus_FROZEN_H2'
CORRECTION_CONTRAST = 'MEAN_H2_current_B_minus_A_head_on_B'
BOOTSTRAP_SEED = 29200001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
RAW_TILES_PER_PHASE = 131072


def evaluation_seed(life, phase_index, episode):
    return 292900000000+life*1000000+phase_index*100000+episode


def _games(games, life, phase_index):
    seeds = [evaluation_seed(life,phase_index,episode) for episode in range(32)]
    if len(games)!=32 or [game['seed'] for game in games]!=seeds:
        raise ValueError('V292 requires all 32 frozen paired evaluation seeds')
    if any(game['status'] not in ('WON','LOST','CUTOFF') for game in games):
        raise ValueError('Evaluation requires explicit natural terminal or cutoff status')
    return dict(games=32,mean_game_utility=mean(game['utility'] for game in games),
        wins=sum(game['status']=='WON' for game in games),
        losses=sum(game['status']=='LOST' for game in games),
        cutoffs=sum(game['status']=='CUTOFF' for game in games),
        cutoff_episodes=[episode for episode,game in enumerate(games) if game['status']=='CUTOFF'],
        steps=sum(game['steps'] for game in games))


def _bootstrap(records, values, draws):
    groups = {parent:[value for row,value in zip(records,values) if row['parent']==parent]
              for parent in range(4)}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group,k=4)) for group in groups.values())
                     for _ in range(draws))
    def quantile(q):
        position = (draws-1)*q
        lower,upper = floor(position),min(floor(position)+1,draws-1)
        return samples[lower]+(samples[upper]-samples[lower])*(position-lower)
    return dict(mean=mean(values),ci95=[quantile(.025),quantile(.975)],
        lifecycle_deltas={str(row['lifecycle']):value for row,value in zip(records,values)},
        improved_equal_worse=[sum(value>0. for value in values),sum(value==0. for value in values),
                              sum(value<0. for value in values)],
        adverse_lifecycles=[row['lifecycle'] for row,value in zip(records,values) if value<0.],
        parent_mean_deltas={str(parent):mean(group) for parent,group in groups.items()},
        interval_scope=INTERVAL_SCOPE)


def _aggregate(games):
    return dict(mean_game_utility=mean(row['mean_game_utility'] for row in games),
        **{key:sum(row[key] for row in games) for key in ('games','wins','losses','cutoffs','steps')})


def summarize(lifecycles, draws=20000):
    """Read actual stream schema; no training return replaces a probe endpoint.

    Every retention probe uses the original A seeds and A-end belief. The saved
    A head on B instead uses the same B-end belief and B seeds as the current
    B head, so correction never subtracts outcomes under different laws.
    """
    rows = sorted(lifecycles,key=lambda row:row['lifecycle'])
    if (len(rows)!=16 or [row['lifecycle'] for row in rows]!=list(range(16))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V292 requires sixteen lifecycles under four fixed source parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    records = []
    for row in rows:
        life,arms = row['lifecycle'],{}
        for arm in ARMS:
            original = row['arms'][arm]['phases']
            p_a = original['A']['snapshot']['estimated_p_four']
            depth = 1 if arm.endswith('DIRECT') else 2
            phases = {}
            for phase_index,phase in enumerate(PHASES):
                value = original[phase]
                training = value['training']
                if training['raw_tiles']!=RAW_TILES_PER_PHASE:
                    raise ValueError('Every arm/phase must pay the same frozen raw-observation budget')
                current = _games(value['game_summaries'],life,phase_index)
                probe = value['retention_probe']
                if (probe['model_p_four']!=p_a or probe['environment_p_four']!=.1
                        or probe['depth']!=depth or probe['shared_with_current']!=(phase_index==0)):
                    raise ValueError('A probes must freeze the original A belief, law, depth and shared checkpoint')
                if phase_index==0 and probe['game_summaries']!=value['game_summaries']:
                    raise ValueError('The initial A probe must reuse its exact current evaluation')
                phases[phase] = dict(current,training_cutoffs=int(training['cutoff_games']),
                                    retention_probe=_games(probe['game_summaries'],life,0))
            arms[arm] = dict(mean_game_utility=mean(phases[phase]['mean_game_utility'] for phase in PHASES),
                             phases=phases)
        ahead = row['arms']['MEAN_H2']['phases']['B']['a_head_on_B']
        p_b = row['arms']['MEAN_H2']['phases']['B']['snapshot']['estimated_p_four']
        if ahead['model_p_four']!=p_b or ahead['environment_p_four']!=.5 or ahead['depth']!=2:
            raise ValueError('Saved A head on B must use the same current B belief and B law')
        arms['MEAN_H2']['phases']['B']['a_head_on_B'] = _games(ahead['game_summaries'],life,1)
        records.append(dict(lifecycle=life,parent=row['parent'],arms=arms))
    arms = {}
    for arm in ARMS:
        phases = {phase:_aggregate([row['arms'][arm]['phases'][phase] for row in records])
                  for phase in PHASES}
        for phase in PHASES:
            values = [row['arms'][arm]['phases'][phase] for row in records]
            phases[phase]['training_cutoffs'] = sum(value['training_cutoffs'] for value in values)
            phases[phase]['retention_probe'] = _aggregate([value['retention_probe'] for value in values])
        arms[arm] = dict(mean_game_utility=mean(row['arms'][arm]['mean_game_utility'] for row in records),
            phases=phases,**{key:sum(phases[p][key] for p in PHASES)
                           for key in ('games','wins','losses','cutoffs','steps','training_cutoffs')})
    paired,phase_contrasts = {},{phase:{} for phase in PHASES}
    for left,right in PAIRS:
        name = left+'_minus_'+right
        values = [row['arms'][left]['mean_game_utility']-row['arms'][right]['mean_game_utility']
                  for row in records]
        paired[name] = _bootstrap(records,values,draws)
        for phase in PHASES:
            values = [row['arms'][left]['phases'][phase]['mean_game_utility']
                      -row['arms'][right]['phases'][phase]['mean_game_utility'] for row in records]
            phase_contrasts[phase][name] = _bootstrap(records,values,draws)
    values = [row['arms']['MEAN_H2']['phases']['B']['mean_game_utility']
              -row['arms']['MEAN_H2']['phases']['B']['a_head_on_B']['mean_game_utility'] for row in records]
    correction = dict(_bootstrap(records,values,draws),name=CORRECTION_CONTRAST)
    retention = {}
    for arm in ARMS:
        probes = {phase:[row['arms'][arm]['phases'][phase]['retention_probe']['mean_game_utility']
                         for row in records] for phase in PHASES}
        retention[arm] = {name:_bootstrap(records,[left-right for left,right in zip(probes[p],probes[q])],draws)
            for name,p,q in (('after_B','B','A'),('restoration','A_prime','B'),('final_vs_A','A_prime','A'))}
    training_cutoffs = sum(value['training_cutoffs'] for value in arms.values())
    current_cutoffs = sum(value['cutoffs'] for value in arms.values())
    probe_cutoffs = sum(arms[arm]['phases'][phase]['retention_probe']['cutoffs']
                        for arm in ARMS for phase in ('B','A_prime'))
    ahead_summary = _aggregate([row['arms']['MEAN_H2']['phases']['B']['a_head_on_B'] for row in records])
    eval_cutoffs = current_cutoffs+probe_cutoffs+ahead_summary['cutoffs']
    complete = training_cutoffs==0 and eval_cutoffs==0
    confirmed = complete and paired[PRIMARY_CONTRAST]['ci95'][0]>0.
    return dict(arms=arms,paired_contrasts=paired,phase_contrasts=phase_contrasts,
        primary_contrast=PRIMARY_CONTRAST,correction_contrast=correction,
        a_head_on_B=ahead_summary,retention_contrasts=retention,by_lifecycle=records,
        bootstrap_draws=draws,bootstrap_seed=BOOTSTRAP_SEED,
        training_cutoffs=training_cutoffs,evaluation_cutoffs=eval_cutoffs,
        current_evaluation_cutoffs=current_cutoffs,additional_probe_cutoffs=probe_cutoffs+ahead_summary['cutoffs'],
        complete_game_endpoints=complete,online_learning_confirmed=confirmed,
        online_learning_status=('SUPPORTED_' if confirmed else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        correction_supported=complete and correction['ci95'][0]>0.,
        physical_evaluation_games=sum(value['games'] for value in arms.values())+16*5*2*32+16*32,
        estimator='EQUAL_GAMES_THEN_PHASES_THEN_LIFECYCLES',
        retention_interpretation='Fixed-A utility changes: after B, restoration during A_prime, and final versus original A. '
            'A confidence interval crossing zero does not establish preservation.',
        correction_interpretation='Current B head minus saved A head under identical current B belief, B law and B seeds.',
        contribution_scope='FROZEN_H2 versus FROZEN_DIRECT isolates planning with fixed source knowledge. '
            'MEAN_H2 versus MEAN_DIRECT compares complete closed-loop methods with different training trajectories and heads.',
        evidence_scope='Continuous natural-game value updates and static no-feedback complete-game checkpoint evaluation, '
            'conditional on four old source parents; no general strategic or structural-learning claim.')
