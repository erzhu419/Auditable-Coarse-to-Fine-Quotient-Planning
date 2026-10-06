"""Old fixed choices are scored, never selected, by the new continuations."""
from copy import deepcopy

import pytest

from acfqp.science.long_horizon_advantage_analysis_v296 import (
    PHASES,PAIRS,PRIMARY,analyze,discovery_seed,validation_seed)


def reference(life,phase,anchor,values,seed_function):
    return dict(model_p_four=.2+phase*.1,environment_p_four=.5 if phase==1 else .1,
        rollouts=[dict(action=action,replica_index=i,seed=seed_function(life,phase,anchor,i),
            total_utility=value,suffix_utility=100.-value,status='LOST')
            for action,value in sorted(values.items()) for i in range(32)])


def cohort():
    rows=[]
    for life in range(16):
        phases={}
        for phase_index,phase in enumerate(PHASES):
            anchors=[]
            for i in range(3):
                legal=['DOWN','LEFT','UP']
                anchors.append(dict(anchor_id=f'L{life:02d}-{phase}-Q{i}',model_p_four=.2+phase_index*.1,
                    choices=dict(FROZEN=dict(action='DOWN',action_values={a:{} for a in legal}),
                                 BELLMAN_CONDITIONED=dict(action='LEFT')),
                    source_action='DOWN',bellman_action='LEFT',discovery_action='UP',
                    legal_actions=legal,validation_actions=legal,
                    discovery_reference=reference(life,phase_index,i,dict(DOWN=-5.,LEFT=-4.,UP=-1.),discovery_seed),
                    validation_reference=reference(life,phase_index,i,dict(DOWN=1.,LEFT=2.,UP=4.),validation_seed)))
            phases[phase]=dict(anchors=anchors)
        rows.append(dict(lifecycle=life,parent=life%4,phases=phases))
    return rows


def test_primary_secondary_and_observed_old_new_drop_are_distinct():
    result=analyze(cohort(),draws=20)
    assert result['primary_contrast']==PRIMARY
    assert set(result['paired_contrasts'])=={left+'_minus_'+right for left,right in PAIRS}
    assert result['paired_contrasts'][PRIMARY]['ci95']==[3.,3.]
    assert result['paired_contrasts']['DISCOVERY_minus_BELLMAN']['mean']==2.
    assert result['paired_contrasts']['BELLMAN_minus_SOURCE']['mean']==1.
    assert result['discovery_contrasts'][PRIMARY]['mean']==4.
    drop=result['discovery_validation_drop'][PRIMARY]
    assert drop['mean']==1. and drop['positive_zero_negative']==[16,0,0]
    assert 'improved_equal_worse' not in drop
    assert result['observed_anchor_signal_supported'] and 'net_gain_supported' not in result
    assert 'does not establish true selection bias' in result['discovery_validation_drop_interpretation']
    assert 'No full-policy net gain' in result['evidence_scope']


def test_total_returns_select_negative_discovery_winner_without_using_suffix():
    result=analyze(cohort(),draws=20)
    first=result['by_lifecycle'][0]['phases']['A']['anchors'][0]
    assert max(first['discovery_action_means'].values())<0.
    assert first['actions']['DISCOVERY']=='UP'
    assert first['discovery_values']['DISCOVERY']==-1.
    assert first['validation_values']['DISCOVERY']==4.
    assert result['method_values']['SOURCE']['validation']==1.


def test_new_validation_winner_cannot_replace_old_candidate_or_make_a_signal():
    rows=cohort()
    for row in rows:
        for phase in PHASES:
            for anchor in row['phases'][phase]['anchors']:
                for rollout in anchor['validation_reference']['rollouts']:
                    rollout['total_utility']={'DOWN':1.,'LEFT':100.,'UP':-10.}[rollout['action']]
    result=analyze(rows,draws=20)
    assert result['paired_contrasts'][PRIMARY]['ci95']==[-11.,-11.]
    assert result['paired_contrasts']['BELLMAN_minus_SOURCE']['mean']==99.
    assert not result['observed_anchor_signal_supported']
    assert all(a['actions']['DISCOVERY']=='UP' for r in result['by_lifecycle']
               for phase in r['phases'].values() for a in phase['anchors'])
    rows[0]['phases']['A']['anchors'][0]['discovery_action']='LEFT'
    with pytest.raises(ValueError,match='only from old discovery'):
        analyze(rows,draws=20)


def test_lexical_tie_and_zero_primary_are_retained_even_if_secondary_is_positive():
    rows=cohort()
    for row in rows:
        for phase in PHASES:
            for anchor in row['phases'][phase]['anchors']:
                for rollout in anchor['discovery_reference']['rollouts']:
                    rollout['total_utility']={'DOWN':-3.,'LEFT':-3.,'UP':-4.}[rollout['action']]
                anchor['discovery_action']='DOWN'; anchor['validation_actions']=['DOWN','LEFT']
                anchor['validation_reference']['rollouts']=[r for r in anchor['validation_reference']['rollouts'] if r['action']!='UP']
    result=analyze(rows,draws=20)
    assert result['same_action_anchors'][PRIMARY]==144
    assert result['paired_contrasts'][PRIMARY]['ci95']==[0.,0.]
    assert result['paired_contrasts']['BELLMAN_minus_SOURCE']['ci95']==[1.,1.]
    assert not result['observed_anchor_signal_supported']
    assert result['validation_physical_rollouts']==144*2*32
    assert result['validation_logical_candidate_references']==144*3*32


def test_shared_action_has_one_receipt_zero_paired_delta_and_is_not_dropped():
    rows=cohort(); anchor=rows[0]['phases']['A']['anchors'][0]
    anchor['source_action']=anchor['bellman_action']='UP'
    anchor['choices']['FROZEN']['action']=anchor['choices']['BELLMAN_CONDITIONED']['action']='UP'
    anchor['validation_actions']=['UP']
    anchor['validation_reference']['rollouts']=[r for r in anchor['validation_reference']['rollouts'] if r['action']=='UP']
    result=analyze(rows,draws=20)
    first=result['by_lifecycle'][0]['phases']['A']['anchors'][0]
    assert first['validation_contrasts']=={name:0. for name in result['paired_contrasts']}
    assert result['anchors']==144 and result['validation_physical_rollouts']==144*3*32-64
    assert result['validation_unique_action_inventory']=={'1':1,'2':0,'3':143}
    assert all(value==1 for value in result['same_action_anchors'].values())


def test_equal_replicas_then_anchors_then_phases_keep_every_natural_anchor():
    rows=cohort()
    for row in rows:
        for phase_index,phase in enumerate(PHASES):
            for anchor_index,anchor in enumerate(row['phases'][phase]['anchors']):
                gain=(1.,2.,9.)[anchor_index]+3.*phase_index
                for replica in anchor['validation_reference']['rollouts']:
                    # Common noise cancels within each forced-action replica.
                    replica['total_utility']=replica['replica_index']/32.+(gain if replica['action']=='UP' else 0.)
    result=analyze(rows,draws=20)
    assert result['paired_contrasts'][PRIMARY]['mean']==7.
    assert [result['phase_contrasts'][phase][PRIMARY]['mean'] for phase in PHASES]==[4.,7.,10.]
    assert result['estimator']=='EQUAL_REPLICAS_THEN_ANCHORS_THEN_PHASES_THEN_LIFECYCLES'


def test_whole_life_bootstrap_keeps_four_parent_composition_and_analysis_readonly():
    rows=cohort()
    for row in rows:
        for phase in PHASES:
            for anchor in row['phases'][phase]['anchors']:
                for rollout in anchor['validation_reference']['rollouts']:
                    if rollout['action']=='UP': rollout['total_utility']=1.+row['parent']+1.
    before=deepcopy(rows); result=analyze(rows,draws=40)
    assert rows==before and result==analyze(list(reversed(rows)),draws=40)
    primary=result['paired_contrasts'][PRIMARY]
    assert primary['ci95']==[2.5,2.5]
    assert primary['parent_mean_deltas']=={str(p):p+1. for p in range(4)}
    assert result['bootstrap_seed']==29600001
    assert result['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


@pytest.mark.parametrize('fault',['new_seed','new_unused_action','model_environment_swap','cutoff'])
def test_new_receipt_isolation_inventory_and_incomplete_return_are_not_silent(fault):
    rows=cohort(); anchor=rows[0]['phases']['A']['anchors'][0]
    reference=anchor['validation_reference']
    if fault=='new_seed': reference['rollouts'][0]['seed']=discovery_seed(0,0,0,0)
    elif fault=='new_unused_action': reference['rollouts'][0]['action']='RIGHT'
    elif fault=='model_environment_swap': reference['model_p_four']=reference['environment_p_four']
    else:
        reference['rollouts'][0]['status']='CUTOFF'
        result=analyze(rows,draws=20)
        assert result['validation_cutoffs']==1 and not result['complete_continuations']
        assert not result['observed_anchor_signal_supported']
        return
    with pytest.raises(ValueError): analyze(rows,draws=20)


def test_new_validation_seed_family_is_disjoint_from_discovery_and_fixtures():
    new={validation_seed(l,p,a,i) for l in range(16) for p in range(3) for a in range(3) for i in range(32)}
    old={discovery_seed(l,p,a,i) for l in range(16) for p in range(3) for a in range(3) for i in range(32)}
    assert len(new)==4608 and min(new)==296600010000 and new.isdisjoint(old)
    assert new.isdisjoint(range(29600003000,29600004000))
