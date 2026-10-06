from pathlib import Path
from statistics import mean
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_ntuple_interference_v288 as audit


def test_real_multiplicity_kernel_scale_has_no_division_by_32():
    left=[0]*8+[1]*8+[2]*8+[3]*8
    right=[0]*4+[9]*28
    assert audit.kernel(left,left)==256
    assert audit.kernel(left,right)==32
    result=audit.expected_metrics(2.,1.,[3.]*32,[0.]*32,32)
    assert result['beta']==.08
    assert result['mean_label_prediction_delta']==.08
    assert result['mean_label_delta_mse']==pytest.approx(.1664)


def test_nonzero_query_offset_is_not_subtracted_twice():
    weights={0:.25,1:.5};offset=3.
    fi=[0]*16+[1]*16;fj=[0]*32
    vi=sum(weights[a] for a in fi)+offset
    vj=sum(weights[a] for a in fj)+offset
    target=vi+2.
    k=audit.kernel(fi,fj)
    result=audit.expected_metrics(vi,vj,[target]*32,[vj-1.]*32,k)
    delta_error=target-offset-sum(weights[a] for a in fi)
    counts={a:fi.count(a) for a in set(fi)}
    updated={a:w+.0025*delta_error*counts.get(a,0) for a,w in weights.items()}
    after=sum(updated[a] for a in fj)+offset
    assert after-vj==pytest.approx(result['mean_label_prediction_delta'])


def test_empirical_population_variance_matches_average_32_isolated_updates():
    discovery=list(range(32));validation=[1.,5.]*16
    r=audit.expected_metrics(4.,2.,discovery,validation,64)
    single=mean(mean((2.+.0025*64*(y-4.)-v)**2-(2.-v)**2 for v in validation) for y in discovery)
    assert r['single_label_mean_delta_mse']==pytest.approx(single)
    assert r['empirical_noise_penalty']==pytest.approx(.0025**2*64**2*85.25)
    assert r['single_label_mean_delta_mse']==pytest.approx(r['mean_label_delta_mse']+r['empirical_noise_penalty'])


def test_zero_kernel_is_protected_and_validation_variance_cancels():
    r=audit.expected_metrics(10.,1.,list(range(32)),[0.,2.]*16,0)
    assert r['mean_label_delta_mse']==r['single_label_mean_delta_mse']==r['empirical_noise_penalty']==0.
    a=audit.expected_metrics(10.,1.,list(range(32)),[0.,2.]*16,32)
    b=audit.expected_metrics(10.,1.,list(range(32)),[1.]*32,32)
    assert a['mean_label_delta_mse']==b['mean_label_delta_mse']
    assert a['baseline_validation_mse'] != b['baseline_validation_mse']


def test_literal_feature_addresses_keep_eight_occurrences_per_pattern_table():
    features=audit.feature_addresses([0]*16)
    assert features==[0]*8+[11**6]*8+[2*11**6]*8+[3*11**6]*8
    assert len(features)==32 and audit.kernel(features,features)==256


def test_category_hierarchy_keeps_zero_kernel_and_equal_boards():
    pairs=[]
    for donor,actions in [('A',['a']),('B',['a','b','c'])]:
        target='B' if donor=='A' else 'A'
        for action in actions:
            for target_action in (['a','b','c'] if target=='B' else ['a']):
                delta=4. if donor=='A' else 0.
                pairs.append(dict(donor_state_id=donor,donor_action=action,target_state_id=target,
                    target_action=target_action,kernel=32 if delta else 0,baseline_validation_mse=2.,
                    mean_label_delta_mse=delta,single_label_mean_delta_mse=delta,empirical_noise_penalty=0.))
    result=audit.aggregate(pairs,'OTHER_BOARD')
    assert result['metrics']['mean_label_delta_mse']==2.
    assert result['metrics']['zero_kernel_fraction']==.5 and result['zero_kernel_pairs']==3


def test_signed_harms_and_parent_scope_are_preserved():
    values=[-1.,1.]*8
    saved=dict(mean=0.,ci95=[0.,0.],lifecycle_deltas={str(i):v for i,v in enumerate(values)},
        improved_equal_worse=[8,0,8],adverse_lifecycles=list(range(1,16,2)),
        parent_mean_deltas={str(p):mean(values[p::4]) for p in range(4)},
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS')
    audit.check_diagnostic(saved,values)
    saved['adverse_lifecycles']=[]
    with pytest.raises(ValueError,match='harms'):audit.check_diagnostic(saved,values)


def test_deterministic_swipe_consumes_each_pair_once_and_aligns_reward():
    board=[1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0]
    left,score=audit.swipe(board,'LEFT')
    right,right_score=audit.swipe(board,'RIGHT')
    assert left[:4]==[2,2,0,0] and right[:4]==[0,0,2,2]
    assert score==right_score==8
    assert board[:4]==[1,1,1,1]
    vertical=[1,0,0,0,1,0,0,0,2,0,0,0,2,0,0,0]
    down,score=audit.swipe(vertical,'DOWN')
    assert down[::4]==[0,0,2,3] and score==12


def test_changed_pair_statistics_are_rejected():
    expected=audit.expected_metrics(2.,1.,[3.]*32,[0.]*32,32)
    saved=dict(expected);saved['empirical_noise_penalty']=.5
    with pytest.raises(ValueError,match='empirical_noise_penalty'):
        audit.compare_nested(saved,expected,'isolated update arithmetic')
