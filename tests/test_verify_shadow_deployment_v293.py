from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_shadow_deployment_v293 as audit


def test_student_t_selector_keeps_unbiased_sample_standard_error():
    result=audit.paired_decision([1.,2.,3.,4.,5.,6.,7.,8.],0,'VALIDATED_H2')
    assert result['mean']==4.5 and result['standard_error']==pytest.approx((.75)**.5)
    assert result['ci95']==pytest.approx([4.5-audit.T_CRITICAL*(.75)**.5,4.5+audit.T_CRITICAL*(.75)**.5])
    assert result['accepted']


def test_zero_difference_rejects_and_positive_zero_standard_error_accepts():
    assert not audit.paired_decision([0.]*8,0,'VALIDATED_H2')['accepted']
    assert audit.paired_decision([1.]*8,0,'VALIDATED_H2')['accepted']
    assert not audit.paired_decision([1.]*8,1,'VALIDATED_H2')['accepted']


def test_selector_uses_full_signed_differences_instead_of_counting_positive_pairs():
    result=audit.paired_decision([2.]*7+[-12.],0,'VALIDATED_H2')
    assert result['mean']==.25 and not result['accepted']
    assert audit.paired_decision([-1.]*8,0,'UNCONDITIONAL_H2')['accepted']
    assert not audit.paired_decision([10.]*8,0,'FROZEN_H2')['accepted']


def test_validation_does_not_stop_early_after_a_favorable_prefix():
    with pytest.raises(ValueError,match='eight fixed'):audit.paired_decision([10.]*7,0,'VALIDATED_H2')


def test_seed_families_are_disjoint_and_only_declared_pair_reuse_occurs():
    warm={audit.warmup_seed(life,e) for life in range(16) for e in range(256)}
    carrier={audit.carrier_seed(life) for life in range(16)}
    deploy={audit.deployment_seed(life,arm) for life in range(16) for arm in audit.ARMS}
    validation={audit.validation_seed(life,p,i) for life in range(16) for p in range(3) for i in range(8)}
    science={audit.evaluation_seed(life,p,i) for life in range(16) for p in range(3) for i in range(32)}
    families=[warm,carrier,deploy,validation,science]
    assert all(not families[i]&families[j] for i in range(5) for j in range(i))
    assert len(deploy)==48 and len(validation)==384 and len(science)==1536
    assert audit.warmup_seed(0,0)==293100010000 and audit.carrier_seed(0)==293200010000
    assert audit.deployment_seed(0,'FROZEN_H2')==293400010000
    assert audit.validation_seed(0,0,0)==293600010000 and audit.evaluation_seed(0,0,0)==293900010000


def submission_fixture(arm='VALIDATED_H2',delta=1.):
    pairs=[dict(incumbent=dict(utility=0.,status='LOST'),candidate=dict(utility=delta,status='LOST')) for _ in range(8)]
    accepted=arm=='UNCONDITIONAL_H2' or (arm=='VALIDATED_H2' and delta>0)
    candidate=0 if arm=='FROZEN_H2' else 1
    row=dict(arm=arm,previous_submission_id=0,candidate_submission_id=candidate,deployed_submission_id=candidate if accepted else 0,
        accepted=accepted,rule='ALWAYS' if arm=='UNCONDITIONAL_H2' else 'FROZEN_SOURCE' if arm=='FROZEN_H2' else 'PAIRED_T_LOWER95_POSITIVE_NO_CUTOFF',
        shadow_value_updates=32,gate=dict(pairs=8,pair_deltas=[delta]*8,mean_delta=delta,sample_std=0.,standard_error=0.,lower95=delta,
            t_critical=audit.T_CRITICAL,no_cutoffs=True,cutoff_pairs=[],accept=delta>0))
    return row,pairs


def test_declared_submission_matches_current_candidate_and_recomputes_actual_gate():
    row,pairs=submission_fixture()
    assert audit.check_submission(row,pairs,0,1,32)==1
    row['gate']['lower95']=-1.
    with pytest.raises(ValueError,match='selector recomputation'):audit.check_submission(row,pairs,0,1,32)
    row['gate']['lower95']=1.;row['candidate_submission_id']=2
    with pytest.raises(ValueError,match='version/rule'):audit.check_submission(row,pairs,0,1,32)


def test_rejected_candidate_does_not_reset_future_shadow_training_prefix():
    row,pairs=submission_fixture(delta=-1.)
    assert audit.check_submission(row,pairs,0,1,32)==0
    row['shadow_value_updates']=0
    with pytest.raises(ValueError,match='version/rule'):audit.check_submission(row,pairs,0,1,32)
    row,pairs=submission_fixture('UNCONDITIONAL_H2',delta=-1.)
    assert audit.check_submission(row,pairs,0,1,32)==1


def test_passive_stream_has_no_memory_block_or_learning_feedback():
    from test_verify_natural_episode_v292 import terminal_chunk
    row,_=terminal_chunk('FROZEN_H2');p=row['model_p_four']
    assert audit.check_passive_chunk(row,64,p)==row['completed_games']
    row['model_p_four']=.5
    with pytest.raises(ValueError,match='observed prefix'):audit.check_passive_chunk(row,64,p)


def test_unfinished_carrier_tail_is_paid_but_has_no_future_label():
    stream=dict(status='ACTIVE',episode=7,raw_tiles=196608,game_start_raw=196508,step=98,return_score=128)
    assert audit.unfinished(stream,True)==dict(status='ACTIVE',episode=7,raw_tiles=100,steps=98,score=128,retained_afterstates=98)
    assert audit.unfinished(stream)==dict(status='ACTIVE',episode=7,raw_tiles=100,steps=98,score=128)
    stream['status']='LOST'
    assert audit.unfinished(stream,True)['raw_tiles']==0


def test_actual_passive_deployment_tail_has_no_afterstate_buffer():
    stream=dict(status='ACTIVE',episode=663,raw_tiles=546268,game_start_raw=545202,step=1064,return_score=18524)
    assert audit.unfinished(stream)==dict(status='ACTIVE',episode=663,raw_tiles=1066,steps=1064,score=18524)
    assert audit.unfinished(stream,True)==dict(status='ACTIVE',episode=663,raw_tiles=1066,steps=1064,score=18524,retained_afterstates=1064)
