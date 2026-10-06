from copy import deepcopy

import pytest

from acfqp.science.retained_critic_analysis_v287 import summarize, ARMS


def cohort():
    rows=[]
    for life in range(16):
        arms={}
        for arm,shift in zip(ARMS,(0.,1.,-2.)):
            metrics=[dict(episode=0,start=0,end=1,count=1,bias=1. if arm == 'FROZEN' else 0.,
                mse=1. if arm != 'EPISODIC_MC' else 4.,mae=1. if arm != 'EPISODIC_MC' else 2.)]
            if life == 0:
                metrics.append(dict(episode=1,start=1,end=1001,count=1000,bias=0.,
                    mse=9. if arm == 'FROZEN' else 1. if arm == 'SHADOW_TD' else 4.,
                    mae=3. if arm == 'FROZEN' else 1. if arm == 'SHADOW_TD' else 2.))
            arms[arm]=dict(game_summaries=[dict(seed=287500000000+life*1000000+i,
                utility=life+shift,status='LOST',steps=10+i) for i in range(16)],
                heldout=dict(game_metrics=metrics,metrics=dict(mse=99999.),prediction_counts={},target_counts={}))
        rows.append(dict(lifecycle=life,parent=life%4,arms=arms))
    return rows


def test_holdout_weights_episodes_then_lives_instead_of_afterstate_count():
    result=summarize(cohort(),draws=40)
    assert result['by_lifecycle'][0]['arms']['FROZEN']['heldout']['mse'] == 5.
    assert result['arms']['FROZEN']['heldout']['mse'] == 1.25
    assert result['arms']['FROZEN']['heldout']['games'] == 17
    assert result['arms']['FROZEN']['heldout']['samples'] == 1016
    assert result['arms']['FROZEN']['heldout']['bias'] == .96875


def test_signed_primary_retains_all_adverse_lives_and_conditional_parent_means():
    result=summarize(cohort(),draws=40)
    primary=result['paired_contrasts']['EPISODIC_MC_minus_FROZEN']
    assert result['primary_contrast'] == 'EPISODIC_MC_minus_FROZEN'
    assert primary['mean'] == -2. and primary['ci95'] == [-2.,-2.]
    assert primary['improved_equal_worse'] == [0,0,16]
    assert primary['adverse_lifecycles'] == list(range(16))
    assert primary['parent_mean_deltas'] == {str(p):-2. for p in range(4)}
    assert primary['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert result['paired_contrasts']['SHADOW_TD_minus_FROZEN']['mean'] == 1.
    assert result['paired_contrasts']['EPISODIC_MC_minus_SHADOW_TD']['mean'] == -3.


def test_prediction_improvement_does_not_replace_new_game_primary():
    result=summarize(cohort(),draws=40)
    td=result['heldout_contrasts']['SHADOW_TD_minus_FROZEN']['mse']
    assert td['mean'] == -.25 and td['improved_equal_worse'] == [1,15,0]
    assert result['paired_contrasts']['EPISODIC_MC_minus_FROZEN']['mean'] < 0.
    assert 'improved_equal_worse' not in result['heldout_contrasts']['SHADOW_TD_minus_FROZEN']['bias']


@pytest.mark.parametrize('error',['seed','heldout','parent','missing'])
def test_actual_pairing_inventory_errors_are_rejected(error):
    rows=cohort()
    if error == 'seed': rows[0]['arms']['SHADOW_TD']['game_summaries'][0]['seed'] += 1
    if error == 'heldout': rows[0]['arms']['SHADOW_TD']['heldout']['game_metrics'][0]['count'] += 1
    if error == 'parent': rows[1]['parent']=0
    if error == 'missing': rows.pop()
    with pytest.raises(ValueError): summarize(rows,draws=40)


def test_cutoff_and_negative_utility_are_not_filtered():
    rows=cohort()
    game=rows[0]['arms']['EPISODIC_MC']['game_summaries'][0]
    game.update(status='CUTOFF',utility=-50.)
    result=summarize(rows,draws=40)
    assert not result['complete_game_endpoints']
    assert result['arms']['EPISODIC_MC']['cutoffs'] == 1
    assert result['by_lifecycle'][0]['arms']['EPISODIC_MC']['mean_game_utility'] == -5.
    assert result['paired_contrasts']['EPISODIC_MC_minus_FROZEN']['mean'] == -2.1875


def test_analysis_is_read_only_and_bootstrap_is_reproducible():
    rows=cohort();before=deepcopy(rows)
    first=summarize(rows,draws=40)
    assert first == summarize(rows,draws=40) and rows == before
