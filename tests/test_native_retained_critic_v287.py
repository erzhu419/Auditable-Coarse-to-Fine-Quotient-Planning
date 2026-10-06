"""Finite factual critics against Python QueryTD; no environment acquisitions."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import native_retained_critic_v287 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD=Path(__file__).resolve().parents[1]/'reports/natural_retained_critic_v287/runtime/tests'
QUERY=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)


def make_leaf(offset=False):
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
    source=NtupleValue(rule,BUILD)
    source.weights[:]=np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    source_query=dict(reward_weight=1.,failure_penalty=0.,goal_bonus=0.) if offset else QUERY
    return QueryTD(QueryParent(source,source_query,QUERY,.25 if offset else .5),'PRIOR',BUILD)


def dataset():
    boards=[[2]+[0]*15,[2,1]+[0]*14,[1,2,1,2]*3+[2,1,2,0],
        [3,3]+[0]*14,[4]+[0]*15,[1,1]+[0]*14,[2,1]+[0]*14,
        [3,3]+[0]*14,[4]+[0]*15]
    return dict(afterstates=np.asarray(boards,dtype=np.int32),
        rewards=np.asarray([4,8,0,8,16,0,4,8,16],dtype=np.float64)/2048.,
        ends=np.asarray([3,5,7,9],dtype=np.int64),terminal_codes=np.asarray([-1,1,-1,1],dtype=np.int32),
        fit_game_count=2,fit_step_end=5)


def factual_targets(data,game):
    start=int(data['ends'][game-1]) if game else 0
    end=int(data['ends'][game]); value=4. if data['terminal_codes'][game]==1 else -4.
    targets={}
    for index in reversed(range(start,end)):
        targets[index]=value
        value+=float(data['rewards'][index])
    return targets


def python_fit(leaf,data,method):
    examples=[]
    start=0
    for game in range(data['fit_game_count']):
        end=int(data['ends'][game]); futures=factual_targets(data,game)
        for index in range(start,end):
            after=data['afterstates'][index]
            if max(after)>=leaf.radix:
                continue
            if method=='MC':
                target=futures[index]
            elif index+1==end:
                target=4. if data['terminal_codes'][game]==1 else -4.
            else:
                next_after=data['afterstates'][index+1]
                tail=4. if max(next_after)>=leaf.radix else leaf.model.value(next_after)+leaf.failure_shift+leaf.success_shift
                target=float(data['rewards'][index+1])+tail
            result=leaf.update(after,target)
            examples.append(dict(episode=game,step=index,target=result['target'],
                raw_target=result['raw_target'],error=result['error']))
        start=end
    return examples


@pytest.mark.parametrize('method',['TD','MC'])
@pytest.mark.parametrize('offset',[False,True])
def test_one_pass_exactly_matches_factual_python_updates_and_offset(method,offset):
    actual,reference=make_leaf(offset),make_leaf(offset)
    data=dataset()
    result=core.fit_retained(actual,data,method,BUILD)
    examples=python_fit(reference,data,method)
    np.testing.assert_array_equal(actual.weights,reference.weights)
    assert actual.updates==reference.updates==4
    assert result['fitted_games']==2 and result['fitted_steps']==5
    assert result['trained_afterstates']==4
    for field,expected in (('first_update',examples[0]),('last_update',examples[-1])):
        assert {key:result[field][key] for key in expected}==expected
    work=result['learning_counts']
    assert work['td_updates']==4
    assert work['table_update_occurrences']==128
    assert work['table_updates']<work['table_update_occurrences']
    assert work['value_predictions']==(6 if method=='TD' else 4)
    assert work['table_lookups']==32*work['value_predictions']
    assert actual.model.counts['td_updates']==actual.counts['td_updates']==actual.counts['inner_td_updates']==4
    assert actual.parent.source.updates==0 and actual.parent.source.counts.get('td_updates',0)==0
    assert result['target_counts']['skipped_winning_afterstates']==1
    if method=='MC':
        assert result['first_update']['target']==8/2048.-4.
        assert result['last_update']['target']==16/2048.+4.
        assert result['target_counts']['suffix_target_assignments']==5
        assert result['target_counts']['suffix_reward_additions']==5
    else:
        assert result['target_counts']['analytic_next_tails']==1


@pytest.mark.parametrize('method',['TD','MC'])
def test_heldout_future_rewards_never_change_fit_prefix(method):
    left,right=make_leaf(),make_leaf()
    first,second=dataset(),dataset()
    second['rewards'][5:]+=.25
    second['afterstates'][5:]=np.roll(second['afterstates'][5:],1,axis=1)
    a=core.fit_retained(left,first,method,BUILD)
    b=core.fit_retained(right,second,method,BUILD)
    np.testing.assert_array_equal(left.weights,right.weights)
    assert a['first_update']==b['first_update'] and a['last_update']==b['last_update']
    assert a['learning_counts']==b['learning_counts'] and left.updates==right.updates


@pytest.mark.parametrize('offset',[False,True])
def test_fixed_score_matches_factual_suffix_and_weights_games_equally(offset):
    leaf=make_leaf(offset); data=dataset()
    core.fit_retained(leaf,data,'MC',BUILD)
    before,updates=leaf.weights.copy(),leaf.updates
    score=core.score_retained(leaf,data,BUILD)
    np.testing.assert_array_equal(leaf.weights,before)
    assert leaf.updates==updates and leaf.weights.flags.writeable
    expected=[]
    for game in range(2,4):
        futures=factual_targets(data,game)
        errors=[]
        for index,target in futures.items():
            after=data['afterstates'][index]
            if max(after)<leaf.radix:
                value=leaf.model.value(after)+leaf.failure_shift+leaf.success_shift
                errors.append(value-target)
        expected.append(dict(count=len(errors),bias=sum(errors)/len(errors),
            mse=sum(x*x for x in errors)/len(errors),mae=sum(abs(x) for x in errors)/len(errors)))
    assert [r['count'] for r in score['game_metrics']]==[2,1]
    for actual,reference in zip(score['game_metrics'],expected):
        for key,value in reference.items():
            assert actual[key]==pytest.approx(value,abs=1e-14)
    for metric in ('bias','mse','mae'):
        assert score['metrics'][metric]==pytest.approx(sum(r[metric] for r in expected)/2.,abs=1e-14)
    assert score['metrics']['bias']!=pytest.approx(sum(r['bias']*r['count'] for r in expected)/3.)
    assert score['prediction_counts']==dict(value_predictions=3,table_lookups=96)
    assert score['target_counts']['skipped_winning_afterstates']==1
    assert score['target_counts']['suffix_target_assignments']==4
