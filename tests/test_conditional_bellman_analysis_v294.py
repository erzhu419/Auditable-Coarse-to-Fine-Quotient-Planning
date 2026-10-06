"""Finite factorial effects, policy-value diagnostics and paired probes."""
from copy import deepcopy

import pytest

from acfqp.science.conditional_bellman_analysis_v294 import (
    ARMS, PHASES, PAIRS, PRIMARY_CONTRAST, analyze, ranking_seed, science_seed)


def games(life, phase, utility):
    return [dict(seed=science_seed(life, phase, i), status='LOST', steps=10+i,
                 utility=utility) for i in range(32)]


def cohort():
    rows=[]
    for life in range(16):
        dataset=dict(snapshots={}, phases={})
        ranking={}
        for i,phase in enumerate(PHASES):
            p=(.12,.48,.15)[i]
            metadata=[dict(episode=10*i+2, steps=5), dict(episode=10*i+3, steps=100)]
            anchors=[dict(anchor_id=f'L{life:02d}-{phase}-Q{slot}', episode=10*i+2,
                step=slot+1, board_before_action=[1,1]+[0]*14,
                model_p_four=.17+i*.1) for slot in range(3)]
            dataset['snapshots'][phase]=dict(estimated_p_four=p)
            dataset['phases'][phase]=dict(heldout_games=metadata, anchors=anchors)
            ranked=[]
            for slot,anchor in enumerate(anchors):
                samples=[dict(action=action, seed=ranking_seed(life,i,slot,replica),
                    total_utility=value, suffix_utility=1000.-value, status='LOST')
                    for action,value in (('LEFT',1.),('RIGHT',4.)) for replica in range(32)]
                choices={a:dict(action='LEFT' if a=='FROZEN' else 'RIGHT') for a in ARMS}
                ranked.append(dict(anchor, reference=dict(rollouts=samples,
                    model_p_four=anchor['model_p_four'], environment_p_four=.5 if i==1 else .1),
                    choices=choices))
            ranking[phase]=dict(anchors=ranked)
        arms={}
        for arm,shift,error_shift in zip(ARMS,(0.,1.,2.,3.,6.),(0.,-1.,-2.,-3.,-5.)):
            phases={}
            for i,phase in enumerate(PHASES):
                current=games(life,i,life+i+shift)
                probe=games(life,0,life+shift+(-1. if i==1 and arm!='FROZEN' else 0.))
                scored=[dict(metadata=m, count=n, mse=e+error_shift,
                    mae=e/2+error_shift/2, bias=e/4+error_shift/4)
                    for m,n,e in zip(dataset['phases'][phase]['heldout_games'],(4,99),(10.,20.))]
                phases[phase]=dict(game_summaries=current, heldout=dict(game_metrics=scored),
                    snapshot=dict(estimated_p_four=dataset['snapshots'][phase]['estimated_p_four']),
                    retention_probe=dict(game_summaries=current if i==0 else probe,
                        model_p_four=.12, environment_p_four=.1, depth=2, shared_with_current=i==0))
            phases['B']['a_head_on_B']=dict(
                game_summaries=phases['B']['game_summaries'] if arm=='FROZEN' else games(life,1,life+1.+shift-2.),
                model_p_four=.48, environment_p_four=.5, depth=2, shared_with_current=arm=='FROZEN')
            arms[arm]=dict(phases=phases)
        rows.append(dict(lifecycle=life,parent=life%4,dataset=dataset,ranking=ranking,arms=arms))
    return rows


def test_independent_primary_and_predefined_factorial_effects():
    result=analyze(cohort(),draws=20)
    primary=result['paired_contrasts'][PRIMARY_CONTRAST]
    assert primary['mean']==6. and primary['ci95']==[6.,6.]
    assert primary['improved_equal_worse']==[16,0,0] and result['net_gain_supported']
    assert set(result['paired_contrasts'])=={left+'_minus_'+right for left,right in PAIRS}
    assert result['paired_contrasts']['MC_CONDITIONED_minus_MC_BOARD']['mean']==1.
    assert result['paired_contrasts']['BELLMAN_CONDITIONED_minus_BELLMAN_BOARD']['mean']==3.
    assert result['factor_interaction']['utility']['mean']==2.
    assert result['physical_science_games']==14848
    assert result['logical_science_game_references']==17920
    assert result['ranking_anchors']==144 and result['ranking_rollouts']==144*2*32
    assert result['arms']['FROZEN']['games']==16*3*32
    assert 'all_stages_complete' not in result


def test_factual_prediction_error_weights_games_not_afterstates_and_preserves_loss_sign():
    result=analyze(cohort(),draws=20)
    assert result['arms']['FROZEN']['heldout']['mse']==15.
    contrast=result['heldout_contrasts'][PRIMARY_CONTRAST]['mse']
    assert contrast['mean']==-5. and contrast['ci95']==[-5.,-5.]
    assert contrast['better_equal_worse']==[16,0,0]
    assert contrast['positive_zero_negative']==[0,0,16]
    assert contrast['negative_lifecycles']==list(range(16))
    assert contrast['worse_lifecycles']==[] and 'improved_equal_worse' not in contrast
    assert 'better_equal_worse' not in result['heldout_contrasts'][PRIMARY_CONTRAST]['bias']
    assert result['factor_interaction']['heldout_mse']['mean']==-1.
    assert 'improved_equal_worse' not in result['factor_interaction']['heldout_mse']


def test_source_continuation_diagnostic_uses_total_utility_and_cannot_select_primary():
    rows=cohort(); result=analyze(rows,draws=20)
    assert result['ranking_contrasts'][PRIMARY_CONTRAST]['mean']==3.
    assert result['arms']['FROZEN']['phases']['B']['ranking']['reference_regret']==3.
    assert result['arms']['BELLMAN_CONDITIONED']['phases']['B']['ranking']['reference_regret']==0.
    for row in rows:
        for phase in PHASES:
            current=row['arms']['BELLMAN_CONDITIONED']['phases'][phase]
            frozen=row['arms']['FROZEN']['phases'][phase]
            for game,control in zip(current['game_summaries'],frozen['game_summaries']):
                game['utility']=control['utility']-1.
    worse=analyze(rows,draws=20)
    assert worse['heldout_contrasts'][PRIMARY_CONTRAST]['mse']['mean']==-5.
    assert worse['ranking_contrasts'][PRIMARY_CONTRAST]['mean']==3.
    assert not worse['net_gain_supported']
    assert 'not optimal-policy Q' in worse['ranking_interpretation']


def test_saved_parameters_on_B_and_fixed_A_retention_are_different_contrasts():
    result=analyze(cohort(),draws=20)
    assert result['correction_contrasts']['BELLMAN_CONDITIONED']['mean']==2.
    assert result['correction_contrasts']['FROZEN']['mean']==0.
    assert result['correction_supported']
    retained=result['retention_contrasts']['BELLMAN_CONDITIONED']
    assert retained['after_B']['mean']==-1. and retained['after_B']['direction']=='NEGATIVE_CHANGE_SUPPORTED'
    assert retained['restoration']['mean']==1. and retained['final_vs_A']['mean']==0.
    assert retained['final_vs_A']['direction']=='ZERO_OBSERVED_CHANGE'
    assert 'crossing zero does not establish preservation' in result['retention_interpretation']


def test_bootstrap_resamples_complete_lives_within_fixed_parents_and_is_readonly():
    rows=cohort()
    for row in rows:
        for phase in PHASES:
            for game,control in zip(row['arms']['BELLMAN_CONDITIONED']['phases'][phase]['game_summaries'],
                                    row['arms']['FROZEN']['phases'][phase]['game_summaries']):
                game['utility']=control['utility']+row['parent']+1.
    before=deepcopy(rows)
    result=analyze(rows,draws=40)
    assert result==analyze(list(reversed(rows)),draws=40) and rows==before
    primary=result['paired_contrasts'][PRIMARY_CONTRAST]
    assert primary['ci95']==[2.5,2.5] and primary['mean']==2.5
    assert primary['parent_mean_deltas']=={str(p):p+1. for p in range(4)}
    assert result['bootstrap_seed']==29400001
    assert result['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


@pytest.mark.parametrize('fault',['science_seed','rank_seed','rank_model_env','ahead_p','heldout_games'])
def test_supported_seed_belief_and_same_data_mismatches_reject(fault):
    rows=cohort(); phase=rows[0]['arms']['BELLMAN_CONDITIONED']['phases']['B']
    anchor=rows[0]['ranking']['B']['anchors'][0]
    if fault=='science_seed':
        phase['game_summaries'][0]['seed']+=1000000
    elif fault=='rank_seed':
        anchor['reference']['rollouts'][0]['seed']+=1
    elif fault=='rank_model_env':
        anchor['reference']['model_p_four']=.5
    elif fault=='ahead_p':
        phase['a_head_on_B']['model_p_four']=.12
    else:
        phase['heldout']['game_metrics'].reverse()
    with pytest.raises(ValueError):
        analyze(rows,draws=20)


def test_all_physical_science_cutoffs_block_confirmation_but_proxy_cutoff_is_separate():
    rows=cohort()
    rows[0]['ranking']['A']['anchors'][0]['reference']['rollouts'][0]['status']='CUTOFF'
    proxy=analyze(rows,draws=20)
    assert proxy['ranking_cutoffs']==1 and proxy['science_cutoffs']==0
    assert proxy['net_gain_supported']
    rows[0]['arms']['MC_BOARD']['phases']['B']['a_head_on_B']['game_summaries'][0]['status']='CUTOFF'
    cutoff=analyze(rows,draws=20)
    assert cutoff['ranking_cutoffs']==1 and cutoff['science_cutoffs']==1
    assert not cutoff['complete_game_endpoints'] and not cutoff['net_gain_supported']
    assert not cutoff['correction_supported']


def test_scientific_and_ranking_seed_sets_are_new_disjoint_families():
    science={science_seed(l,p,e) for l in range(16) for p in range(3) for e in range(32)}
    rank={ranking_seed(l,p,a,r) for l in range(16) for p in range(3) for a in range(3) for r in range(32)}
    assert len(science)==1536 and len(rank)==4608 and science.isdisjoint(rank)
    assert min(science)==294900010000 and min(rank)==294600010000
