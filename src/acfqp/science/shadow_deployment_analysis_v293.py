"""Independent game evidence for shared-shadow deployment and retention."""
from math import floor
import random
from statistics import mean

from .natural_episode_analysis_v292 import _aggregate

ARMS = ('FROZEN_H2', 'UNCONDITIONAL_H2', 'VALIDATED_H2')
PHASES = ('A', 'B', 'A_prime')
PAIRS = (('VALIDATED_H2', 'FROZEN_H2'),
         ('VALIDATED_H2', 'UNCONDITIONAL_H2'),
         ('UNCONDITIONAL_H2', 'FROZEN_H2'))
PRIMARY_CONTRAST = 'VALIDATED_H2_minus_FROZEN_H2'
MECHANISM_CONTRAST = 'VALIDATED_H2_minus_UNCONDITIONAL_H2'
BOOTSTRAP_SEED = 29300001
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
ONLINE_RAW_TILES_PER_PHASE = 262144
CARRIER_RAW_TILES_PER_PHASE = 65536


def science_seed(life, phase_index, episode):
    return 293900010000+life*1000000+phase_index*100000+episode


def validation_seed(life, phase_index, pair):
    return 293600010000+life*1000000+phase_index*100000+pair


def _games(games, life, phase_index):
    seeds = [science_seed(life, phase_index, episode) for episode in range(32)]
    if len(games) != 32 or [game['seed'] for game in games] != seeds:
        raise ValueError('V293 science requires its 32 independent paired seeds')
    if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
        raise ValueError('Independent games require actual terminal or cutoff status')
    return dict(games=32, mean_game_utility=mean(game['utility'] for game in games),
        wins=sum(game['status']=='WON' for game in games),
        losses=sum(game['status']=='LOST' for game in games),
        cutoffs=sum(game['status']=='CUTOFF' for game in games),
        cutoff_episodes=[i for i,game in enumerate(games) if game['status']=='CUTOFF'],
        steps=sum(game['steps'] for game in games))


def _bootstrap(records, values, draws):
    groups = {parent:[value for row,value in zip(records, values) if row['parent']==parent]
              for parent in range(4)}
    rng = random.Random(BOOTSTRAP_SEED)
    samples = sorted(mean(mean(rng.choices(group, k=4)) for group in groups.values())
                     for _ in range(draws))
    def quantile(q):
        position = (draws-1)*q
        lower,upper = floor(position),min(floor(position)+1,draws-1)
        return samples[lower]+(samples[upper]-samples[lower])*(position-lower)
    return dict(mean=mean(values), ci95=[quantile(.025), quantile(.975)],
        lifecycle_deltas={str(row['lifecycle']):value for row,value in zip(records, values)},
        improved_equal_worse=[sum(value>0. for value in values), sum(value==0. for value in values),
                              sum(value<0. for value in values)],
        adverse_lifecycles=[row['lifecycle'] for row,value in zip(records, values) if value<0.],
        parent_mean_deltas={str(parent):mean(group) for parent,group in groups.items()},
        interval_scope=INTERVAL_SCOPE)


def _direction(contrast):
    if contrast['ci95'][0]>0.:
        return 'POSITIVE_CHANGE_SUPPORTED'
    if contrast['ci95'][1]<0.:
        return 'NEGATIVE_CHANGE_SUPPORTED'
    if all(value==0. for value in contrast['lifecycle_deltas'].values()):
        return 'ZERO_OBSERVED_CHANGE'
    return 'CHANGE_UNCERTAIN'


def _validation(value, life, phase_index, arm, previous_id):
    validation, submission = value['validation'], value['submission']
    pairs = validation['pairs']
    if (len(pairs)!=8 or [pair['pair_index'] for pair in pairs]!=list(range(8))
            or [pair['seed'] for pair in pairs]
            !=[validation_seed(life, phase_index, pair) for pair in range(8)]):
        raise ValueError('Submission requires its eight paired validation seeds')
    games = [pair[side] for pair in pairs for side in ('incumbent', 'candidate')]
    if (validation['game_summaries']!=games or any(
            pair[side]['seed']!=pair['seed'] or pair[side]['status'] not in ('WON', 'LOST', 'CUTOFF')
            for pair in pairs for side in ('incumbent', 'candidate'))):
        raise ValueError('Validation must retain both actual games in each pair')
    raw, cutoffs = sum(game['raw_tiles'] for game in games), sum(game['status']=='CUTOFF' for game in games)
    if (validation['raw_tiles']!=raw or validation['cutoff_games']!=cutoffs
            or any(game['raw_tiles']!=game['steps']+2 for game in games)):
        raise ValueError('Validation charges its initial tiles and every actual action spawn')
    candidate_id = 0 if arm=='FROZEN_H2' else phase_index+1
    accepted = arm=='UNCONDITIONAL_H2' or (arm=='VALIDATED_H2' and submission['gate']['accept'])
    deployed_id = candidate_id if accepted else previous_id
    if (submission['previous_submission_id']!=previous_id
            or submission['candidate_submission_id']!=candidate_id
            or submission['accepted']!=accepted
            or submission['deployed_submission_id']!=deployed_id
            or value['snapshot']['deployed_submission_id']!=deployed_id
            or any(pair['incumbent_submission_id']!=previous_id
                   or pair['candidate_submission_id']!=candidate_id for pair in pairs)):
        raise ValueError('Deployed heads must follow the frozen submission rule')
    if arm=='VALIDATED_H2' and accepted and (cutoffs or submission['gate']['lower95']<=0.):
        raise ValueError('Validated submission requires positive lower95 and no cutoff')
    return dict(games=16, raw_tiles=raw, cutoffs=cutoffs, accepted=accepted,
                deployed_submission_id=deployed_id)


def analyze(lifecycles, draws=20000):
    """Use independent science games, complete paired lives and paid selection.

    The common carrier owns belief and the persistent shadow. Validation scores
    determine submissions; fresh science games determine the reported effects.
    """
    rows = sorted(lifecycles, key=lambda row:row['lifecycle'])
    if (len(rows)!=16 or [row['lifecycle'] for row in rows]!=list(range(16))
            or any(row['parent']!=row['lifecycle']%4 for row in rows)):
        raise ValueError('V293 requires sixteen new lives under four fixed source parents')
    if draws<2:
        raise ValueError('Bootstrap requires at least two draws')
    records, carrier_cutoffs = [], 0
    for row in rows:
        life, arms = row['lifecycle'], {}
        carrier = row['carrier']['phases']
        for phase in PHASES:
            if carrier[phase]['raw_tiles']!=CARRIER_RAW_TILES_PER_PHASE:
                raise ValueError('Every phase must use the shared 65536-raw carrier')
            carrier_cutoffs += carrier[phase]['cutoff_games']
        for arm in ARMS:
            original = row['arms'][arm]['phases']
            p_a, previous_id, phases = original['A']['snapshot']['estimated_p_four'], 0, {}
            for phase_index, phase in enumerate(PHASES):
                value = original[phase]
                p = carrier[phase]['snapshot']['estimated_p_four']
                if value['snapshot']['estimated_p_four']!=p:
                    raise ValueError('All arms must use the shared carrier-only belief')
                validation = _validation(value, life, phase_index, arm, previous_id)
                previous_id = validation['deployed_submission_id']
                deployment = value['deployment']
                if (value['online_raw_tiles']!=ONLINE_RAW_TILES_PER_PHASE
                        or CARRIER_RAW_TILES_PER_PHASE+validation['raw_tiles']+deployment['raw_tiles']
                        !=ONLINE_RAW_TILES_PER_PHASE):
                    raise ValueError('Online budget includes all validation and remaining actual deployment')
                current = _games(value['game_summaries'], life, phase_index)
                probe = value['retention_probe']
                if (probe['model_p_four']!=p_a or probe['environment_p_four']!=.1
                        or probe['depth']!=2 or probe['shared_with_current']!=(phase_index==0)):
                    raise ValueError('A probes must freeze the original A belief and science seeds')
                if phase_index==0 and probe['game_summaries']!=value['game_summaries']:
                    raise ValueError('The A-end probe must share its exact current evaluation')
                phases[phase] = dict(current, validation=validation,
                    deployment_cutoffs=int(deployment['cutoff_games']),
                    deployment_raw_tiles=deployment['raw_tiles'],
                    online_raw_tiles=value['online_raw_tiles'],
                    online_realized_utility=value['online_realized_utility'],
                    retention_probe=_games(probe['game_summaries'], life, 0))
            ahead = original['B']['a_head_on_B']
            p_b = original['B']['snapshot']['estimated_p_four']
            if ahead['model_p_four']!=p_b or ahead['environment_p_four']!=.5 or ahead['depth']!=2:
                raise ValueError('Each saved A head on B must share its current B belief and law')
            phases['B']['a_head_on_B'] = _games(ahead['game_summaries'], life, 1)
            arms[arm] = dict(mean_game_utility=mean(phases[p]['mean_game_utility'] for p in PHASES),
                             phases=phases)
        records.append(dict(lifecycle=life, parent=row['parent'], arms=arms))
    arms = {}
    for arm in ARMS:
        phases = {}
        for phase in PHASES:
            values = [row['arms'][arm]['phases'][phase] for row in records]
            phases[phase] = dict(_aggregate(values),
                retention_probe=_aggregate([value['retention_probe'] for value in values]),
                accepted_submissions=sum(value['validation']['accepted'] for value in values),
                validation_games=sum(value['validation']['games'] for value in values),
                validation_raw_tiles=sum(value['validation']['raw_tiles'] for value in values),
                validation_cutoffs=sum(value['validation']['cutoffs'] for value in values),
                **{key:sum(value[key] for value in values) for key in
                   ('deployment_cutoffs', 'deployment_raw_tiles', 'online_raw_tiles', 'online_realized_utility')})
        phases['B']['a_head_on_B'] = _aggregate(
            [row['arms'][arm]['phases']['B']['a_head_on_B'] for row in records])
        arms[arm] = dict(mean_game_utility=mean(row['arms'][arm]['mean_game_utility'] for row in records),
            phases=phases, **{key:sum(value[key] for value in phases.values()) for key in
                ('games', 'wins', 'losses', 'cutoffs', 'accepted_submissions', 'validation_games',
                 'validation_raw_tiles', 'validation_cutoffs', 'deployment_cutoffs',
                 'deployment_raw_tiles', 'online_raw_tiles', 'online_realized_utility')})
    paired, phase_contrasts = {}, {phase:{} for phase in PHASES}
    for left,right in PAIRS:
        name = left+'_minus_'+right
        paired[name] = _bootstrap(records, [row['arms'][left]['mean_game_utility']
            -row['arms'][right]['mean_game_utility'] for row in records], draws)
        for phase in PHASES:
            phase_contrasts[phase][name] = _bootstrap(records,
                [row['arms'][left]['phases'][phase]['mean_game_utility']
                 -row['arms'][right]['phases'][phase]['mean_game_utility'] for row in records], draws)
    corrections, retention = {}, {}
    for arm in ARMS:
        corrections[arm] = dict(_bootstrap(records,
            [row['arms'][arm]['phases']['B']['mean_game_utility']
             -row['arms'][arm]['phases']['B']['a_head_on_B']['mean_game_utility'] for row in records], draws),
            name=arm+'_current_B_minus_A_head_on_B')
        probes = {phase:[row['arms'][arm]['phases'][phase]['retention_probe']['mean_game_utility']
                         for row in records] for phase in PHASES}
        retention[arm] = {}
        for name,p,q in (('after_B', 'B', 'A'), ('restoration', 'A_prime', 'B'), ('final_vs_A', 'A_prime', 'A')):
            contrast = _bootstrap(records, [left-right for left,right in zip(probes[p], probes[q])], draws)
            retention[arm][name] = dict(contrast, direction=_direction(contrast))
    current_cutoffs = sum(value['cutoffs'] for value in arms.values())
    additional_cutoffs = sum(arms[arm]['phases'][phase]['retention_probe']['cutoffs']
        for arm in ARMS for phase in ('B', 'A_prime'))
    additional_cutoffs += sum(arms[arm]['phases']['B']['a_head_on_B']['cutoffs'] for arm in ARMS)
    validation_cutoffs = sum(value['validation_cutoffs'] for value in arms.values())
    deployment_cutoffs = sum(value['deployment_cutoffs'] for value in arms.values())
    complete = carrier_cutoffs+validation_cutoffs+deployment_cutoffs+current_cutoffs+additional_cutoffs==0
    net_gain = complete and paired[PRIMARY_CONTRAST]['ci95'][0]>0.
    return dict(arms=arms, paired_contrasts=paired, phase_contrasts=phase_contrasts,
        primary_contrast=PRIMARY_CONTRAST, mechanism_contrast=MECHANISM_CONTRAST,
        correction_contrasts=corrections, correction_contrast=corrections['VALIDATED_H2'],
        retention_contrasts=retention, by_lifecycle=records,
        complete_game_endpoints=complete, net_gain_supported=net_gain,
        net_gain_status=('SUPPORTED_' if net_gain else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        mechanism_supported=complete and paired[MECHANISM_CONTRAST]['ci95'][0]>0.,
        correction_supported=complete and corrections['VALIDATED_H2']['ci95'][0]>0.,
        carrier_cutoffs=carrier_cutoffs, validation_cutoffs=validation_cutoffs,
        deployment_cutoffs=deployment_cutoffs,
        science_cutoffs=current_cutoffs+additional_cutoffs,
        current_science_cutoffs=current_cutoffs, additional_probe_cutoffs=additional_cutoffs,
        physical_science_games=sum(value['games'] for value in arms.values())+16*3*2*32+16*3*32,
        physical_validation_games=sum(value['validation_games'] for value in arms.values()),
        bootstrap_draws=draws, bootstrap_seed=BOOTSTRAP_SEED,
        estimator='EQUAL_GAMES_THEN_PHASES_THEN_LIFECYCLES',
        retention_interpretation='Signed fixed-A changes. A confidence interval crossing zero '
            'does not establish preservation; zero observed change alone is not a population equivalence claim.',
        correction_interpretation='Current B deployment minus its own saved A head with identical B belief, law and science seeds.',
        selection_interpretation='Rejected candidates establish neither net learning gain nor successful B correction. '
            'Submission t intervals are approximate decision rules; effects use independent science games.',
        evidence_scope='Common frozen-source carrier data and persistent shared shadow; three deployment rules, '
            'conditional on four old source parents. Carrier-only belief excludes validation/deployment feedback.')
