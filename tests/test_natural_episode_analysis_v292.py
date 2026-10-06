"""Finite same-law correction, retention, budget and pairing cases."""
from copy import deepcopy

import pytest

from acfqp.science.natural_episode_analysis_v292 import ARMS,PHASES,PAIRS,evaluation_seed,summarize


def games(life,phase,value):
    return [dict(seed=evaluation_seed(life,phase,episode),utility=value,status='LOST',steps=10+episode)
            for episode in range(32)]


def cohort():
    rows = []
    for life in range(16):
        arms = {}
        for arm,shift in zip(ARMS,(0.,1.,2.,-2.,-.5)):
            phases = {}
            for phase_index,phase in enumerate(PHASES):
                current = games(life,phase_index,life+phase_index+shift)
                probe_value = life+shift+(0. if phase_index==0 or arm.startswith('FROZEN')
                                         else -1. if phase_index==1 else .5)
                probe = dict(game_summaries=current if phase_index==0 else games(life,0,probe_value),
                    model_p_four=.12,environment_p_four=.1,depth=1 if arm.endswith('DIRECT') else 2,
                    shared_with_current=phase_index==0)
                phases[phase] = dict(game_summaries=current,retention_probe=probe,
                    snapshot=dict(estimated_p_four=.12 if phase_index!=1 else .48),
                    training=dict(raw_tiles=131072,cutoff_games=0),
                    misleading_training_return=999999.)
            if arm=='MEAN_H2':
                phases['B']['a_head_on_B'] = dict(game_summaries=games(life,1,life+1.),
                    model_p_four=.48,environment_p_four=.5,depth=2)
            arms[arm] = dict(phases=phases)
        rows.append(dict(lifecycle=life,parent=life%4,arms=arms))
    return rows


def test_cycle_gain_phase_weight_and_five_predefined_controls():
    result = summarize(cohort(),draws=20)
    primary = result['paired_contrasts'][result['primary_contrast']]
    assert primary['mean']==2. and primary['ci95']==[2.,2.]
    assert primary['improved_equal_worse']==[16,0,0] and primary['adverse_lifecycles']==[]
    assert result['online_learning_confirmed'] and result['physical_evaluation_games']==13312
    assert result['arms']['MEAN_H2']['games']==16*3*32
    assert set(result['paired_contrasts'])=={left+'_minus_'+right for left,right in PAIRS}
    assert result['paired_contrasts']['FROZEN_H2_minus_FROZEN_DIRECT']['mean']==2.
    assert result['paired_contrasts']['MEAN_DIRECT_minus_FROZEN_DIRECT']['mean']==1.5
    rows = cohort()
    for row in rows:
        for phase,shift in zip(PHASES,(3.,-3.,6.)):
            for game in row['arms']['MEAN_H2']['phases'][phase]['game_summaries']:
                game['utility']=row['lifecycle']+PHASES.index(phase)+shift
    changed = summarize(rows,draws=20)
    assert changed['paired_contrasts'][changed['primary_contrast']]['mean']==2.
    assert [changed['phase_contrasts'][p][changed['primary_contrast']]['mean'] for p in PHASES]==[3.,-3.,6.]


def test_correction_uses_saved_A_head_on_same_B_law_not_A_current_returns():
    result = summarize(cohort(),draws=20)
    correction = result['correction_contrast']
    assert correction['name']=='MEAN_H2_current_B_minus_A_head_on_B'
    assert correction['mean']==2. and correction['ci95']==[2.,2.]
    assert result['correction_supported']
    assert result['a_head_on_B']['games']==16*32


def test_retention_and_restoration_have_fixed_A_belief_seeds_and_signed_losses():
    result = summarize(cohort(),draws=20)
    retained = result['retention_contrasts']['MEAN_H2']
    assert retained['after_B']['mean']==-1. and retained['after_B']['ci95']==[-1.,-1.]
    assert retained['after_B']['adverse_lifecycles']==list(range(16))
    assert retained['restoration']['mean']==1.5 and retained['final_vs_A']['mean']==.5
    for arm in ('FROZEN_H2','FROZEN_DIRECT'):
        assert all(value['mean']==0. and value['ci95']==[0.,0.]
                   for value in result['retention_contrasts'][arm].values())
    assert 'crossing zero does not establish preservation' in result['retention_interpretation']


def test_whole_lifecycle_bootstrap_keeps_fixed_parent_composition():
    rows = cohort()
    for row in rows:
        for phase in PHASES:
            for game,frozen in zip(row['arms']['MEAN_H2']['phases'][phase]['game_summaries'],
                                    row['arms']['FROZEN_H2']['phases'][phase]['game_summaries']):
                game['utility']=frozen['utility']+row['parent']+1.
    result = summarize(rows,draws=40)
    primary = result['paired_contrasts'][result['primary_contrast']]
    assert primary['mean']==2.5 and primary['ci95']==[2.5,2.5]
    assert primary['parent_mean_deltas']=={str(parent):parent+1. for parent in range(4)}
    assert primary['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert result['bootstrap_seed']==29200001


@pytest.mark.parametrize('error',['seed','probe_seed','probe_belief','probe_law','correction_belief',
                                 'correction_seed','budget','parent','missing'])
def test_actual_pairing_law_belief_roster_and_raw_budget_mismatches_are_rejected(error):
    rows = cohort(); phases = rows[0]['arms']['MEAN_H2']['phases']
    if error=='seed':
        phases['B']['game_summaries'][0]['seed']+=1
    elif error=='probe_seed':
        phases['B']['retention_probe']['game_summaries'][0]['seed']+=1
    elif error=='probe_belief':
        phases['B']['retention_probe']['model_p_four']=.48
    elif error=='probe_law':
        phases['B']['retention_probe']['environment_p_four']=.5
    elif error=='correction_belief':
        phases['B']['a_head_on_B']['model_p_four']=.12
    elif error=='correction_seed':
        phases['B']['a_head_on_B']['game_summaries'][0]['seed']=evaluation_seed(0,0,0)
    elif error=='budget':
        phases['B']['training']['raw_tiles']-=1
    elif error=='parent':
        rows[0]['parent']=1
    else:
        rows.pop()
    with pytest.raises(ValueError):
        summarize(rows,draws=20)


@pytest.mark.parametrize('kind',['training','current','probe','ahead'])
def test_any_actual_training_or_evaluation_cutoff_is_retained_and_blocks_confirmation(kind):
    rows = cohort(); phases = rows[0]['arms']['MEAN_H2']['phases']
    if kind=='training':
        phases['B']['training']['cutoff_games']=1
    elif kind=='current':
        phases['B']['game_summaries'][0]['status']='CUTOFF'
    elif kind=='probe':
        phases['B']['retention_probe']['game_summaries'][3]['status']='CUTOFF'
    else:
        phases['B']['a_head_on_B']['game_summaries'][5]['status']='CUTOFF'
    result = summarize(rows,draws=20)
    assert not result['complete_game_endpoints'] and not result['online_learning_confirmed']
    assert not result['correction_supported']
    assert result['training_cutoffs']+result['evaluation_cutoffs']==1


def test_negative_lives_zero_primary_and_readonly_reproducibility():
    rows = cohort(); before = deepcopy(rows)
    result = summarize(rows,draws=20)
    assert rows==before and result==summarize(list(reversed(rows)),draws=20)
    for row in rows:
        for phase in PHASES:
            for game,frozen in zip(row['arms']['MEAN_H2']['phases'][phase]['game_summaries'],
                                    row['arms']['FROZEN_H2']['phases'][phase]['game_summaries']):
                game['utility']=frozen['utility']
    zero = summarize(rows,draws=20)
    assert zero['paired_contrasts'][zero['primary_contrast']]['ci95']==[0.,0.]
    assert not zero['online_learning_confirmed']
