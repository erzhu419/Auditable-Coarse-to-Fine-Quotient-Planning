"""Independent science, own-head correction, pairing and paid-selection cases."""
from copy import deepcopy

import pytest

from acfqp.science.shadow_deployment_analysis_v293 import (
    ARMS, PHASES, PRIMARY_CONTRAST, MECHANISM_CONTRAST, _bootstrap, _direction,
    analyze, science_seed, validation_seed)


def games(life, phase, utility):
    return [dict(seed=science_seed(life, phase, episode), utility=utility,
                 status='LOST', steps=30+episode) for episode in range(32)]


def cohort():
    rows = []
    for life in range(16):
        arms = {}
        for arm in ARMS:
            phases, previous_id = {}, 0
            for phase_index, phase in enumerate(PHASES):
                frozen = arm=='FROZEN_H2'
                accepted = not frozen and (arm=='UNCONDITIONAL_H2' or phase!='B')
                proposal = 0 if frozen else phase_index+1
                deployed = proposal if accepted else previous_id
                shift = 0. if frozen else (1., -.5, 2.)[phase_index]
                if phase=='B':
                    shift = 0. if frozen else -3. if arm=='UNCONDITIONAL_H2' else .5
                current = games(life, phase_index, life+phase_index+shift)
                probe_shift = {0:0., 1:1., 2:-4., 3:2.}[deployed]
                probe = dict(game_summaries=current if phase=='A' else games(life, 0, life+probe_shift),
                    model_p_four=.12, environment_p_four=.1, depth=2, shared_with_current=phase=='A')
                delta = 0. if frozen else 1. if phase=='A' else -3.5 if phase=='B' else 6. if arm=='UNCONDITIONAL_H2' else 1.
                pairs = []
                for pair in range(8):
                    seed = validation_seed(life, phase_index, pair)
                    incumbent = dict(seed=seed, utility=100.+pair, status='LOST', steps=20+pair, raw_tiles=22+pair)
                    candidate = dict(incumbent, utility=incumbent['utility']+delta)
                    pairs.append(dict(pair_index=pair, seed=seed, incumbent_submission_id=previous_id,
                        candidate_submission_id=proposal, incumbent=incumbent, candidate=candidate))
                validation_games = [pair[side] for pair in pairs for side in ('incumbent', 'candidate')]
                validation_raw = sum(game['raw_tiles'] for game in validation_games)
                phases[phase] = dict(game_summaries=current, retention_probe=probe,
                    snapshot=dict(estimated_p_four=.48 if phase=='B' else .12, deployed_submission_id=deployed),
                    submission=dict(previous_submission_id=previous_id, candidate_submission_id=proposal,
                        deployed_submission_id=deployed, accepted=accepted,
                        gate=dict(accept=delta>0., lower95=delta)),
                    validation=dict(pairs=pairs, game_summaries=validation_games,
                                    raw_tiles=validation_raw, cutoff_games=0),
                    deployment=dict(raw_tiles=262144-65536-validation_raw, cutoff_games=0),
                    online_raw_tiles=262144, online_realized_utility=-99999.)
                if phase=='B':
                    ahead_shift = 0. if frozen else .5
                    phases[phase]['a_head_on_B'] = dict(game_summaries=games(life, 1, life+1+ahead_shift),
                        model_p_four=.48, environment_p_four=.5, depth=2)
                previous_id = deployed
            arms[arm] = dict(phases=phases)
        carrier = dict(phases={phase:dict(raw_tiles=65536, cutoff_games=0,
            snapshot=dict(estimated_p_four=.48 if phase=='B' else .12)) for phase in PHASES})
        rows.append(dict(lifecycle=life, parent=life%4, arms=arms, carrier=carrier))
    return rows


def test_post_fixture_environment_seed_bases_remain_separate_from_bootstrap():
    assert validation_seed(0, 0, 0)==293600010000
    assert validation_seed(15, 2, 7)==293615210007
    assert science_seed(0, 0, 0)==293900010000
    assert science_seed(15, 2, 31)==293915210031


def test_independent_cycle_and_mechanism_do_not_use_selection_or_execution_returns():
    rows = cohort()
    result = analyze(rows, draws=20)
    assert result['paired_contrasts'][PRIMARY_CONTRAST]['mean']==pytest.approx(7/6)
    assert result['paired_contrasts'][MECHANISM_CONTRAST]['mean']==pytest.approx(7/6)
    assert result['net_gain_supported'] and result['mechanism_supported']
    assert not result['correction_supported']
    assert result['physical_science_games']==9216 and result['physical_validation_games']==2304
    assert result['arms']['VALIDATED_H2']['accepted_submissions']==32
    for row in rows:
        for arm in ARMS:
            for phase in PHASES:
                value = row['arms'][arm]['phases'][phase]
                value['online_realized_utility']=1e12
                for pair in value['validation']['pairs']:
                    for side in ('incumbent', 'candidate'):
                        pair[side]['utility']+=1e6
    changed = analyze(rows, draws=20)
    assert changed['paired_contrasts']==result['paired_contrasts']


def test_rejection_and_holding_source_alone_cannot_confirm_learning():
    rows = cohort()
    for row in rows:
        life = row['lifecycle']
        for arm in ARMS:
            for phase_index, phase in enumerate(PHASES):
                value = row['arms'][arm]['phases'][phase]
                old = 0 if arm!='UNCONDITIONAL_H2' else phase_index
                deployed = 0 if arm!='UNCONDITIONAL_H2' else phase_index+1
                value['submission'].update(previous_submission_id=old, deployed_submission_id=deployed,
                    accepted=arm=='UNCONDITIONAL_H2', gate=dict(accept=False, lower95=0.))
                value['snapshot']['deployed_submission_id']=deployed
                for pair in value['validation']['pairs']:
                    pair['incumbent_submission_id']=old
                    pair['candidate']['utility']=pair['incumbent']['utility']
                current = games(life, phase_index, life+phase_index)
                value['game_summaries']=current
                value['retention_probe']['game_summaries']=current if phase=='A' else games(life, 0, life)
                if phase=='B':
                    value['a_head_on_B']['game_summaries']=games(life, 1, life+1)
    result = analyze(rows, draws=20)
    assert result['paired_contrasts'][PRIMARY_CONTRAST]['ci95']==[0., 0.]
    assert not result['net_gain_supported'] and not result['correction_supported']
    assert result['arms']['VALIDATED_H2']['accepted_submissions']==0
    assert 'Rejected candidates establish neither' in result['selection_interpretation']
    assert 'all_stages_complete' not in result


def test_each_correction_uses_own_A_head_on_B_and_retention_keeps_signed_failures():
    result = analyze(cohort(), draws=20)
    assert result['correction_contrasts']['VALIDATED_H2']['mean']==0.
    assert result['correction_contrasts']['UNCONDITIONAL_H2']['mean']==-3.5
    assert result['correction_contrasts']['FROZEN_H2']['mean']==0.
    bad = result['retention_contrasts']['UNCONDITIONAL_H2']['after_B']
    assert bad['mean']==-5. and bad['adverse_lifecycles']==list(range(16))
    assert bad['direction']=='NEGATIVE_CHANGE_SUPPORTED'
    assert result['retention_contrasts']['VALIDATED_H2']['after_B']['direction']=='ZERO_OBSERVED_CHANGE'
    assert result['retention_contrasts']['VALIDATED_H2']['restoration']['mean']==1.
    assert result['retention_contrasts']['FROZEN_H2']['final_vs_A']['ci95']==[0., 0.]
    assert _direction(dict(ci95=[-1., 1.], lifecycle_deltas={'0':-1., '1':1.}))=='CHANGE_UNCERTAIN'
    assert 'crossing zero does not establish preservation' in result['retention_interpretation']


def test_whole_life_bootstrap_keeps_four_fixed_parent_composition():
    records = [dict(lifecycle=life, parent=life%4) for life in range(16)]
    result = _bootstrap(records, [row['parent']+1. for row in records], 40)
    assert result['mean']==2.5 and result['ci95']==[2.5, 2.5]
    assert result['parent_mean_deltas']=={str(parent):parent+1. for parent in range(4)}
    assert result['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


@pytest.mark.parametrize('mistake', ['science_uses_validation', 'probe_uses_B_belief', 'ahead_uses_A_seeds', 'unpaid_validation'])
def test_science_independence_fixed_A_own_B_comparator_and_total_raw(mistake):
    rows = cohort()
    value = rows[0]['arms']['VALIDATED_H2']['phases']['B']
    if mistake=='science_uses_validation':
        value['game_summaries'][0]['seed']=validation_seed(0, 1, 0)
    elif mistake=='probe_uses_B_belief':
        value['retention_probe']['model_p_four']=.48
    elif mistake=='ahead_uses_A_seeds':
        value['a_head_on_B']['game_summaries'][0]['seed']=science_seed(0, 0, 0)
    else:
        value['deployment']['raw_tiles']+=value['validation']['raw_tiles']
    with pytest.raises(ValueError):
        analyze(rows, draws=20)


@pytest.mark.parametrize('where', ['carrier', 'validation', 'deployment', 'science'])
def test_actual_cutoffs_are_retained_and_prevent_confirmation(where):
    rows = cohort()
    value = rows[0]['arms']['FROZEN_H2']['phases']['B']
    if where=='carrier':
        rows[0]['carrier']['phases']['B']['cutoff_games']=1
    elif where=='validation':
        for side in ('incumbent', 'candidate'):
            value['validation']['pairs'][0][side]['status']='CUTOFF'
        value['validation']['cutoff_games']=2
    elif where=='deployment':
        value['deployment']['cutoff_games']=1
    else:
        value['game_summaries'][0]['status']='CUTOFF'
    result = analyze(rows, draws=20)
    assert not result['complete_game_endpoints'] and not result['net_gain_supported']
    assert not result['mechanism_supported'] and not result['correction_supported']
    assert result[where+'_cutoffs']>0


def test_readonly_roster_and_reproducible_signed_life_estimator():
    rows = cohort(); original = deepcopy(rows)
    result = analyze(rows, draws=20)
    assert rows==original and result==analyze(list(reversed(rows)), draws=20)
    assert result['bootstrap_seed']==29300001
    rows[0]['parent']=1
    with pytest.raises(ValueError):
        analyze(rows, draws=20)
