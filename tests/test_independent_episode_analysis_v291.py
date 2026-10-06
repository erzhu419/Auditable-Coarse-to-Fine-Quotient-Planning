"""Finite cohort, pairing, weighting and fixed-parent bootstrap cases."""
from copy import deepcopy

import pytest

from acfqp.science.independent_episode_analysis_v291 import ARMS, PAIRS, summarize


def cohort(mean_shift=2.):
    rows = []
    for life in range(64):
        arms = {}
        for arm,shift,error in zip(ARMS,(0.,1.,mean_shift),(1.,.5,.25)):
            metrics = [dict(episode=0,start=0,end=1,count=1,bias=-1.,mse=error,mae=error)]
            if life==0:
                metrics.append(dict(episode=1,start=1,end=1001,count=1000,
                                    bias=0.,mse=9.*error,mae=3.*error))
            arms[arm] = dict(game_summaries=[dict(seed=291900000000+life*1000000+episode,
                utility=life+shift,status='LOST',steps=10+episode) for episode in range(32)],
                heldout=dict(game_metrics=metrics,metrics=dict(mse=-999999.)),
                old_v290_evidence=dict(mse=-15.727),anchor_metrics=dict(mse=-999999.),
                new_value_updates=10000000 if life==0 else 1)
        rows.append(dict(lifecycle=life,parent=life%4,arms=arms))
    return rows


def test_new_complete_game_and_lifecycle_weights_ignore_old_evidence_and_samples():
    result = summarize(cohort(),draws=20)
    frozen = result['arms']['FROZEN']['heldout']
    assert result['by_lifecycle'][0]['arms']['FROZEN']['heldout']['mse']==5.
    assert frozen['mse']==1.0625 and frozen['mae']==1.015625
    assert frozen['bias']==-.9921875
    assert frozen['games']==65 and frozen['samples']==1064
    assert result['heldout_contrasts']['EPISODE_MEAN_MC_minus_FROZEN']['mse']['mean']==-.796875
    assert result['arms']['FROZEN']['games']==64*32


def test_primary_confirmation_requires_positive_whole_game_utility_not_prediction():
    result = summarize(cohort(mean_shift=-1.),draws=20)
    name = result['primary_contrast']
    assert name==result['primary_prediction_contrast']=='EPISODE_MEAN_MC_minus_FROZEN'
    assert result['primary_prediction_metric']=='mse'
    primary = result['paired_contrasts'][name]
    assert primary['mean']==-1. and primary['ci95']==[-1.,-1.]
    assert primary['improved_equal_worse']==[0,0,64]
    assert primary['adverse_lifecycles']==list(range(64))
    assert result['independent_prediction_supported']
    assert not result['independent_learning_confirmed']
    assert result['independent_learning_status']=='NOT_SUPPORTED_CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert 'improved_equal_worse' not in result['heldout_contrasts'][name]['bias']


def test_positive_utility_complete_cohort_confirms_only_conditional_fixed_sources():
    result = summarize(cohort(),draws=20)
    assert result['complete_game_endpoints'] and result['independent_learning_confirmed']
    assert result['independent_learning_status']=='SUPPORTED_CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert result['paired_contrasts'][result['primary_contrast']]['ci95']==[2.,2.]
    assert set(result['paired_contrasts'])=={left+'_minus_'+right for left,right in PAIRS}
    assert result['paired_contrasts']['EPISODE_MEAN_MC_minus_NORMALIZED_SEQUENTIAL_MC']['mean']==1.
    assert result['paired_contrasts']['NORMALIZED_SEQUENTIAL_MC_minus_FROZEN']['mean']==1.


def test_stratified_bootstrap_keeps_all_four_parents_and_all_16_lives_each():
    rows = cohort()
    for row in rows:
        for game,frozen in zip(row['arms']['EPISODE_MEAN_MC']['game_summaries'],
                               row['arms']['FROZEN']['game_summaries']):
            game['utility']=frozen['utility']+row['parent']+1.
    result = summarize(rows,draws=40)
    primary = result['paired_contrasts'][result['primary_contrast']]
    assert primary['mean']==2.5 and primary['ci95']==[2.5,2.5]
    assert primary['parent_mean_deltas']=={str(parent):parent+1. for parent in range(4)}
    assert primary['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert result['bootstrap_seed']==29100001
    assert len(primary['lifecycle_deltas'])==64


@pytest.mark.parametrize('error',['seed','old_seed','games','heldout','parent','missing','duplicate'])
def test_wrong_cohort_pairing_or_heldout_inventory_is_rejected(error):
    rows = cohort()
    if error=='seed':
        rows[0]['arms']['EPISODE_MEAN_MC']['game_summaries'][0]['seed']+=1
    elif error=='old_seed':
        rows[0]['arms']['EPISODE_MEAN_MC']['game_summaries'][0]['seed']=290500000000
    elif error=='games':
        rows[0]['arms']['EPISODE_MEAN_MC']['game_summaries'].pop()
    elif error=='heldout':
        rows[0]['arms']['EPISODE_MEAN_MC']['heldout']['game_metrics'][0]['count']+=1
    elif error=='parent':
        rows[1]['parent']=0
    elif error=='missing':
        rows.pop()
    else:
        rows[-1]['lifecycle']=0
    with pytest.raises(ValueError):
        summarize(rows,draws=20)


def test_cutoff_cannot_confirm_learning_or_disappear_from_primary_or_indices():
    rows = cohort()
    rows[0]['arms']['EPISODE_MEAN_MC']['game_summaries'][0].update(status='CUTOFF',utility=-62.)
    result = summarize(rows,draws=20)
    assert not result['complete_game_endpoints'] and not result['independent_learning_confirmed']
    assert result['arms']['EPISODE_MEAN_MC']['cutoffs']==1
    life = result['by_lifecycle'][0]['arms']['EPISODE_MEAN_MC']
    assert life['cutoff_episodes']==[0] and life['mean_game_utility']==0.
    assert result['paired_contrasts'][result['primary_contrast']]['mean']==1.96875


def test_zero_lower_bound_and_any_secondary_cutoff_block_confirmation():
    result = summarize(cohort(mean_shift=0.),draws=20)
    assert result['paired_contrasts'][result['primary_contrast']]['ci95']==[0.,0.]
    assert not result['independent_learning_confirmed']
    rows = cohort()
    rows[0]['arms']['NORMALIZED_SEQUENTIAL_MC']['game_summaries'][5]['status']='CUTOFF'
    result = summarize(rows,draws=20)
    assert not result['independent_learning_confirmed']
    assert result['by_lifecycle'][0]['arms']['NORMALIZED_SEQUENTIAL_MC']['cutoff_episodes']==[5]


def test_analysis_is_readonly_reproducible_and_order_independent():
    rows = cohort(); before = deepcopy(rows)
    result = summarize(rows,draws=20)
    assert rows==before and result==summarize(list(reversed(rows)),draws=20)
