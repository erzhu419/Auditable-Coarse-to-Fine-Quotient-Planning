"""Finite fixed-choice and actual continuation-cost faults, without new worlds."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_long_horizon_advantage_v296 as audit


def anchor_fixture():
    lost=[1,2,1,2,2,1,2,1,1,2,1,2,2,1,2,1]
    native_rows=[dict(action=a,replica_index=i,seed=audit.validation_seed(0,0,0,i),first_score=4 if a=='LEFT' else 0,
        total_score=4 if a=='LEFT' else 0,total_utility=(4 if a=='LEFT' else 0)/2048.-4,
        suffix_utility=-4.,status='LOST',steps=1,final_board=lost)
        for a in ('LEFT','RIGHT') for i in range(32)]
    actions={a:dict(score=4 if a=='LEFT' else 0,value=1.) for a in ('LEFT','RIGHT')}
    choices=dict(FROZEN=dict(action='LEFT',action_values=actions),BELLMAN_CONDITIONED=dict(action='LEFT',action_values=actions))
    old=dict(anchor_id='0:A:0',lifecycle=0,parent=0,phase='A',phase_index=0,anchor_index=0,
        episode=1,step=10,board_before_action=[0]*16,model_p_four=.17,choices=choices,
        reference=dict(rollouts=[dict(r,total_utility=2. if r['action']=='RIGHT' else 1.) for r in native_rows]))
    anchor=dict({k:v for k,v in old.items() if k!='reference'},discovery_reference=old['reference'],
        source_action='LEFT',bellman_action='LEFT',discovery_action='RIGHT',legal_actions=['LEFT','RIGHT'],
        discovery_action_means=dict(LEFT=1.,RIGHT=2.),
        validation_actions=['LEFT','RIGHT'],validation_reference=dict(rollouts=native_rows,model_p_four=.17,
            environment_p_four=.1,counts=dict(environment=dict(sampled_transitions=64,environment_random_draws=128,
                ground_explicit_swipe_calls=64,ground_swipe_calls=320,ground_state_status_calls=64,
                ground_status_internal_swipe_calls=256),planning={},rollout=dict(completed_rollouts=64,
                rng_streams_started=64,replica_streams=32,evaluate_calls=1,continuation_choose_calls=0))))
    return anchor,old


def test_discovery_argmax_is_old_total_utility_not_new_validation_winner():
    anchor,old=anchor_fixture();audit.check_selection(anchor,old)
    anchor['discovery_action']='LEFT'
    with pytest.raises(ValueError,match='fixed from old discovery'):audit.check_selection(anchor,old)


def test_union_acquisition_does_not_duplicate_shared_SOURCE_BELLMAN_action():
    anchor,old=anchor_fixture();audit.check_selection(anchor,old)
    result=audit.check_validation(anchor);assert result['rollouts']==64
    anchor['validation_actions'].append('LEFT')
    with pytest.raises(ValueError,match='frozen candidate union'):audit.check_selection(anchor,old)


def test_actual_costs_count_forced_first_spawn_and_two_random_draws():
    anchor,_=anchor_fixture();audit.check_validation(anchor)
    anchor['validation_reference']['counts']['environment']['environment_random_draws']=64
    with pytest.raises(ValueError,match='spawn/draw/status costs'):audit.check_validation(anchor)


def test_total_utility_keeps_first_action_reward_and_suffix_is_separate():
    anchor,_=anchor_fixture();anchor['validation_reference']['rollouts'][0]['total_utility']-=4/2048.
    with pytest.raises(ValueError,match='total first-action utility'):audit.check_validation(anchor)


def test_actual_law_is_not_substituted_for_observed_planner_probability():
    anchor,_=anchor_fixture();anchor['validation_reference']['model_p_four']=.1
    with pytest.raises(ValueError,match='planner observed p'):audit.check_validation(anchor)


def cohort():
    lives=[]
    for life in range(16):
        phases={}
        for pi,p in enumerate(audit.PHASES):
            anchors=[]
            for slot in range(3):
                anchor,_=anchor_fixture();anchor.update(anchor_id=f'L{life:02d}-{p}-Q{slot}',
                    lifecycle=life,parent=life%4,phase=p,phase_index=pi,anchor_index=slot)
                ref=anchor['validation_reference'];ref['environment_p_four']=audit.LAWS[pi]
                score=4*(life+slot+1)+8*pi
                anchor['choices']['FROZEN']['action_values']['LEFT']['score']=score
                for r in ref['rollouts']:
                    r['seed']=audit.validation_seed(life,pi,slot,r['replica_index'])
                    if r['action']=='LEFT':r.update(first_score=score,total_score=score,total_utility=score/2048.-4)
                if slot==0:
                    anchor['discovery_action']='LEFT';anchor['validation_actions']=['LEFT']
                    for r in anchor['discovery_reference']['rollouts']:r['total_utility']=2. if r['action']=='LEFT' else 1.
                    ref['rollouts']=[r for r in ref['rollouts'] if r['action']=='LEFT']
                    ref['counts']['environment']={k:v//2 for k,v in ref['counts']['environment'].items()}
                    ref['counts']['rollout'].update(completed_rollouts=32,rng_streams_started=32)
                anchors.append(anchor)
            phases[p]=dict(anchors=anchors)
        lives.append(dict(lifecycle=life,parent=life%4,phases=phases))
    return lives


def synthetic_summary(records,totals,inventory,same):
    def contrast(values,signed=False):
        m=sum(values)/16;c=dict(mean=m,ci95=[m,m],lifecycle_deltas={str(i):v for i,v in enumerate(values)},
            parent_mean_deltas={str(p):sum(values[p::4])/4 for p in range(4)},interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS')
        signs=[sum(v>0 for v in values),sum(v==0 for v in values),sum(v<0 for v in values)]
        if signed:c.update(positive_zero_negative=signs,negative_lifecycles=[i for i,v in enumerate(values) if v<0])
        else:c.update(improved_equal_worse=signs,adverse_lifecycles=[i for i,v in enumerate(values) if v<0])
        return c
    s=dict(by_lifecycle=records,method_values={},phase_method_values={},paired_contrasts={},discovery_contrasts={},
        discovery_validation_drop={},phase_contrasts={p:{} for p in audit.PHASES},
        phase_discovery_validation_drop={p:{} for p in audit.PHASES},validation_unique_action_inventory={str(n):inventory[n] for n in (1,2,3)},
        same_action_anchors=dict(same),complete_continuations=True,observed_anchor_signal_supported=False,
        primary_contrast='DISCOVERY_minus_SOURCE',bootstrap_seed=29600001,bootstrap_draws=20000,
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS',estimator='EQUAL_REPLICAS_THEN_ANCHORS_THEN_PHASES_THEN_LIFECYCLES')
    for key in ('anchors','discovery_physical_rollouts','validation_physical_rollouts','discovery_cutoffs',
        'validation_cutoffs','validation_logical_candidate_references','paired_replica_seed_streams'):s[key]=totals[key]
    for method in audit.CANDIDATES:
        s['method_values'][method]={label:sum(r[label+'_values'][method] for r in records)/16 for label in ('discovery','validation')}
    for p in audit.PHASES:s['phase_method_values'][p]={m:{label:sum(r['phases'][p][label+'_values'][m] for r in records)/16
        for label in ('discovery','validation')} for m in audit.CANDIDATES}
    for left,right in audit.PAIRS:
        name=left+'_minus_'+right
        for saved,field,signed in (('paired_contrasts','validation_contrasts',False),('discovery_contrasts','discovery_contrasts',False),
            ('discovery_validation_drop','discovery_validation_drop',True)):
            s[saved][name]=contrast([r[field][name] for r in records],signed)
        for p in audit.PHASES:
            s['phase_contrasts'][p][name]=contrast([r['phases'][p]['validation_contrasts'][name] for r in records])
            s['phase_discovery_validation_drop'][p][name]=contrast([r['phases'][p]['discovery_validation_drop'][name] for r in records],True)
    return s


def test_equal_anchor_weight_is_independent_of_shared_candidate_union_size():
    values=audit.recompute_records(cohort());records,totals,_,_=values
    # Q0 shares one physical action; Q1/Q2 have two. Its zero difference still gets one third weight.
    assert records[0]['phases']['A']['validation_contrasts']['DISCOVERY_minus_SOURCE']==-(8+12)/(3*2048.)
    assert totals['validation_physical_rollouts']==16*3*(32+64+64)
    assert totals['validation_logical_candidate_references']==144*3*32


def test_old_positive_discovery_cannot_override_negative_independent_validation():
    values=audit.recompute_records(cohort());s=synthetic_summary(*values);audit.check_summary(s,*values)
    assert s['discovery_contrasts']['DISCOVERY_minus_SOURCE']['mean']>0
    assert s['paired_contrasts']['DISCOVERY_minus_SOURCE']['mean']<0
    s['observed_anchor_signal_supported']=True
    with pytest.raises(ValueError,match='independent fixed-action signal'):audit.check_summary(s,*values)


def test_negative_validation_lives_and_signed_old_new_drop_remain_present():
    values=audit.recompute_records(cohort());s=synthetic_summary(*values)
    s['paired_contrasts']['DISCOVERY_minus_SOURCE']['adverse_lifecycles']=[]
    with pytest.raises(ValueError,match='adverse lives retained'):audit.check_summary(s,*values)
