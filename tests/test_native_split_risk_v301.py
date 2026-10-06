"""Literal reward/risk updates, spatial features, H2 values and natural execution."""
from collections import Counter
from fractions import Fraction
import math
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_retained_critic_v287 import score_retained
from acfqp.science.native_split_risk_v301 import (
    QUERY, SplitLeaf, evaluate_split, fit_split, global_features, predict_components, score_split)
from acfqp.science.native_value_stream_v286 import NativeValueStream

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/split_risk_v301/runtime/tests/native'


def make_template():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9,10)), (2, Fraction(1,10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    result = QueryTD(QueryParent(source, QUERY, QUERY, .5), 'PRIOR', BUILD)
    result.freeze()
    return result


def data():
    boards = [[2]+[0]*15, [2,1]+[0]*14, [3,3]+[0]*14, [4]+[0]*15,
        [1,2,1,2]*3+[2,1,2,0], [2]+[0]*15, [3,3]+[0]*14, [4]+[0]*15]
    return dict(afterstates=np.asarray(boards, dtype=np.int32),
        rewards=np.asarray([4,8,8,16,0,4,8,16], dtype=np.float64)/2048.,
        ends=np.asarray([2,4,6,8], dtype=np.int64),
        terminal_codes=np.asarray([-1,1,-1,1], dtype=np.int32), fit_game_count=3, fit_step_end=6)


def literal_features(board, radix):
    b = list(map(int, board))
    neighbors = [[j for j in range(16) if abs(i//4-j//4)+abs(i%4-j%4)==1] for i in range(16)]
    unseen = {i for i in range(16) if b[i]==0}
    component_sizes = []
    while unseen:
        frontier = [unseen.pop()]; size=0
        while frontier:
            current = frontier.pop(); size+=1
            found = unseen.intersection(neighbors[current]); unseen.difference_update(found); frontier.extend(found)
        component_sizes.append(size)
    ranks = sorted(b, reverse=True); maximum=ranks[0]
    largest = [i for i in range(16) if maximum and b[i]==maximum]
    edge = {i for i in range(16) if i//4 in (0,3) or i%4 in (0,3)}
    pairs = [(i,j) for i in range(16) for j in neighbors[i] if i<j]
    lines = [b[4*r:4*r+4] for r in range(4)] + [b[c::4] for c in range(4)]
    packed = [[v for v in line if v] for line in lines]
    monotone = sum(all(a<=z for a,z in zip(line,line[1:])) or
        all(a>=z for a,z in zip(line,line[1:])) for line in packed)
    masses = sorted([2.**rank if rank else 0. for rank in b], reverse=True)
    return np.asarray([1., b.count(0)/16., len(component_sizes)/8., max(component_sizes, default=0)/16.,
        maximum/radix, ranks[1]/radix, sum(b)/(16.*radix),
        float(bool(set(largest).intersection({0,3,12,15}))), float(bool(set(largest).intersection(edge))),
        len(largest)/16., max((sum(b[j]==0 for j in neighbors[i]) for i in largest), default=0)/4.,
        max((sum(b[j]==maximum for j in neighbors[i]) for i in largest), default=0)/4.,
        sum(b[i]>0 and b[i]==b[j] for i,j in pairs)/24., sum(abs(b[i]-b[j]) for i,j in pairs)/(24.*radix),
        sum(a==z for line in packed for a,z in zip(line,line[1:]))/24., monotone/8.,
        b.count(1)/16., b.count(2)/16., sum(masses[:2])/sum(masses) if sum(masses) else 0.,
        sum(b[i]!=0 for i in edge)/12.])


def literal_prediction(leaf, board):
    addresses = list(map(int, leaf.model.feature_indices(board)))
    reward = sum(float(leaf.reward_weights.reshape(-1)[i]) for i in addresses)
    if leaf.kind == 'LOCAL_RISK':
        logit = sum(float(leaf.risk_weights.reshape(-1)[i]) for i in addresses)
    else:
        x = literal_features(board, leaf.radix)
        logit = sum(float(leaf.risk_weights[j])*float(x[j]) for j in range(20))
    exponential = math.exp(-logit) if logit>=0. else math.exp(logit)
    probability = 1./(1.+exponential) if logit>=0. else exponential/(1.+exponential)
    return reward, probability, reward+8.*(probability-.5)


def literal_fit(leaf, dataset):
    start=0; examples=[]
    reward_flat, risk_flat = leaf.reward_weights.reshape(-1), leaf.risk_weights.reshape(-1)
    for game in range(dataset['fit_game_count']):
        end = int(dataset['ends'][game]); suffix=0.; targets={}
        for step in range(end-1,start-1,-1):
            targets[step]=suffix; suffix+=float(dataset['rewards'][step])
        steps=[i for i in range(start,end) if max(dataset['afterstates'][i])<leaf.radix]
        occurrences={step: Counter(map(int, leaf.model.feature_indices(dataset['afterstates'][step]))) for step in steps}
        denominators=Counter()
        for row in occurrences.values(): denominators.update(row)
        reward_grad={address: 0. for address in denominators}
        risk_grad={address: 0. for address in denominators} if leaf.kind=='LOCAL_RISK' else np.zeros(20)
        risk_den=np.zeros(20)
        residuals={}; label=float(dataset['terminal_codes'][game]==1)
        for step in steps:
            reward,probability,combined=literal_prediction(leaf,dataset['afterstates'][step])
            residuals[step]=(targets[step]-reward,label-probability)
            examples.append(dict(episode=game,step=step,reward_target=targets[step],risk_target=label,
                reward_prediction=reward,risk_probability=probability,combined_prediction=combined,
                reward_error=targets[step]-reward,risk_error=label-probability))
        for step,row in occurrences.items():
            reward_error,risk_error=residuals[step]
            for address,count in sorted(row.items()):
                reward_grad[address]+=count*reward_error
                if leaf.kind=='LOCAL_RISK': risk_grad[address]+=count*risk_error
            if leaf.kind=='GLOBAL_RISK':
                x=literal_features(dataset['afterstates'][step],leaf.radix)
                for j in range(20):
                    risk_grad[j]+=float(x[j])*risk_error; risk_den[j]+=float(x[j])
        for address,gradient in reward_grad.items(): reward_flat[address]+=.0025*gradient/denominators[address]
        if leaf.kind=='LOCAL_RISK':
            for address,gradient in risk_grad.items(): risk_flat[address]+=.0025*gradient/denominators[address]
        else:
            for j in range(20):
                if risk_den[j]: risk_flat[j]+=.0025*float(risk_grad[j])/float(risk_den[j])
        start=end
    return examples


@pytest.mark.parametrize('board', [
    [0]*16, [1]*16, [0,1,0,1,1,0,1,0,0,1,0,1,1,0,1,0],
    [3,2,0,0,0,3,1,0,2,0,1,0,0,0,2,1]])
def test_all_twenty_features_match_literal_and_dihedral_symmetry(board):
    expected=literal_features(board,4)
    actual=global_features(board,4,BUILD)
    np.testing.assert_array_equal(actual,expected)
    assert np.all((actual>=0.) & (actual<=1.))
    square=np.asarray(board).reshape(4,4)
    for reflected in (False,True):
        for rotations in range(4):
            transformed=np.rot90(np.fliplr(square) if reflected else square,rotations).reshape(-1)
            np.testing.assert_array_equal(global_features(transformed,4,BUILD),expected)


@pytest.mark.parametrize('kind', ['LOCAL_RISK','GLOBAL_RISK'])
def test_game_start_two_head_updates_match_literal_occurrence_normalization(kind):
    template=make_template(); actual,reference=SplitLeaf(template,kind,BUILD),SplitLeaf(template,kind,BUILD)
    result=fit_split(actual,data(),BUILD); examples=literal_fit(reference,data())
    np.testing.assert_array_equal(actual.reward_weights,reference.reward_weights)
    np.testing.assert_array_equal(actual.risk_weights,reference.risk_weights)
    assert result['first_sample']==examples[0] and result['last_sample']==examples[-1]
    assert result['frozen_game_start_targets'] and result['trained_afterstates']==actual.updates==5
    assert result['reward_trained_afterstates']==result['risk_trained_afterstates']==5
    assert result['target_counts']['skipped_winning_afterstates']==1
    assert result['learning_counts']['table_update_occurrences']==160
    assert result['learning_counts']['reward_predictions']==result['learning_counts']['risk_predictions']==5
    assert result['normalization_counts']['game_parameter_commits']==3
    assert result['normalization_counts']['normalization_divisions']==result['learning_counts']['table_updates']
    assert template.updates==template.parent.source.updates==0
    if kind=='LOCAL_RISK':
        assert result['learning_counts']['reward_table_updates']==result['learning_counts']['risk_parameter_updates']
        assert result['representation_counts']['local_risk_table_lookups']==160
    else:
        assert result['representation_counts']['global_feature_extractions']==5
        assert result['representation_counts']['global_dot_products']==5
        assert result['normalization_counts']['risk_parameter_writes']+result['normalization_counts'].get('global_zero_denominators',0)==60


@pytest.mark.parametrize('kind', ['LOCAL_RISK','GLOBAL_RISK'])
def test_initial_source_value_h2_and_natural_rng_are_identical(kind):
    template=make_template(); leaf=SplitLeaf(template,kind,BUILD); leaf.freeze()
    assert not leaf.risk_weights.flags.writeable and not leaf.reward_weights.flags.writeable
    planner=FrozenLeafPlanner(template,2,BUILD); planner.spawn_probabilities=(1.-.43,.43)
    board=[1,1,2,0]+[0]*12
    source=planner.choose(board); split=leaf.choose(board,.43)
    for key in ('action','afterstate','score','value','tail_value','action_values','status','counts'):
        assert split[key]==source[key]
    components=predict_components(leaf,[2]+[0]*15)
    assert components['risk_probability']==.5 and components['combined_prediction']==template.model.value([2]+[0]*15)
    engine=NativeValueStream(template,1234,BUILD)
    try:
        before=engine.state()
        original=engine.evaluate_games(template,.43,.5,[301001,301002,301003],max_steps=128)
        fitted=evaluate_split(leaf,.43,.5,[301001,301002,301003],BUILD,max_steps=128)
        assert fitted['game_summaries']==original['game_summaries'] and fitted['counts']==original['counts']
        assert engine.state()==before and leaf.updates==0
    finally: engine.close()
    assert fitted['representation_counts']['risk_sigmoid_evaluations']==fitted['counts']['planning']['value_predictions']
    with pytest.raises(ValueError,match='writable'): fit_split(leaf,data(),BUILD)


@pytest.mark.parametrize('kind', ['LOCAL_RISK','GLOBAL_RISK'])
def test_current_reward_and_heldout_cannot_change_fitted_heads(kind):
    template=make_template(); actual,reference=SplitLeaf(template,kind,BUILD),SplitLeaf(template,kind,BUILD)
    first,second=data(),data()
    # First reward in each game never appears in that game's afterstate suffix.
    second['rewards'][[0,2,4]]+=100.
    second['afterstates'][6:]=0; second['rewards'][6:]=100.; second['terminal_codes'][3]=-1
    left,right=fit_split(actual,first,BUILD),fit_split(reference,second,BUILD)
    np.testing.assert_array_equal(actual.reward_weights,reference.reward_weights)
    np.testing.assert_array_equal(actual.risk_weights,reference.risk_weights)
    for key in ('first_sample','last_sample','learning_counts','target_counts','normalization_counts','representation_counts'):
        assert left[key]==right[key]


@pytest.mark.parametrize('kind', ['LOCAL_RISK','GLOBAL_RISK'])
def test_terminal_label_changes_only_risk_head_and_never_reward_head(kind):
    template=make_template(); actual,reference=SplitLeaf(template,kind,BUILD),SplitLeaf(template,kind,BUILD)
    first,second=data(),data(); second['terminal_codes'][:3]*=-1
    left,right=fit_split(actual,first,BUILD),fit_split(reference,second,BUILD)
    np.testing.assert_array_equal(actual.reward_weights,reference.reward_weights)
    assert np.any(actual.risk_weights!=reference.risk_weights)
    assert left['first_sample']['risk_target']==0. and right['first_sample']['risk_target']==1.
    assert left['first_sample']['reward_target']==right['first_sample']['reward_target']


@pytest.mark.parametrize('kind', ['LOCAL_RISK','GLOBAL_RISK'])
def test_heldout_component_scores_are_literal_and_readonly(kind):
    template=make_template(); leaf=SplitLeaf(template,kind,BUILD); fit_split(leaf,data(),BUILD); leaf.freeze()
    reward,risk=leaf.reward_weights.copy(),leaf.risk_weights.copy(); updates=leaf.updates
    result=score_split(leaf,data(),BUILD); old=score_retained(template,data(),BUILD)
    row,components=result['game_metrics'][0],result['component_game_metrics'][0]
    r,p,v=literal_prediction(leaf,data()['afterstates'][6]); reward_target=16/2048.; utility_target=4.+reward_target
    assert row['count']==components['count']==1 and row['start']==components['start']==6
    assert row['mean_factual_future_utility']==old['game_metrics'][0]['mean_factual_future_utility']==utility_target
    assert row['mse']==pytest.approx((v-utility_target)**2)
    assert components['reward_mse']==pytest.approx((r-reward_target)**2)
    assert components['risk_brier']==pytest.approx((p-1.)**2)
    assert components['risk_log_loss']==pytest.approx(-math.log(p))
    assert row['bias']==pytest.approx(components['reward_bias']+8.*components['risk_bias'])
    assert result['prediction_counts'].get('td_updates',0)==result['prediction_counts'].get('table_updates',0)==0
    np.testing.assert_array_equal(reward,leaf.reward_weights); np.testing.assert_array_equal(risk,leaf.risk_weights)
    assert leaf.updates==updates


@pytest.mark.parametrize('kind', ['LOCAL_RISK','GLOBAL_RISK'])
def test_h2_winning_reward_terminal_goal_and_loss_are_analytic_once(kind):
    template=make_template(); leaf=SplitLeaf(template,kind,BUILD)
    leaf.reward_weights[:]=123.; leaf.risk_weights[:]=9.; leaf.freeze()
    won=leaf.choose([4]+[0]*15,.43)
    assert won['status']=='WON' and won['value']==4. and not won['representation_counts']
    board=[3,3]+[0]*14; choice=leaf.choose(board,.43)
    winning=[row for row in choice['action_values'].values() if max(row['afterstate'])==4]
    assert winning and all(row['tail_value']==4. and row['value']==4.+16/2048. for row in winning)
    lost=leaf.choose([1,2,1,2,2,1,2,1,1,2,1,2,2,1,2,1],.43)
    assert lost['status']=='LOST' and lost['value']==-4. and not lost['representation_counts']


def test_global_local_are_distinct_after_learning_and_original_source_is_used():
    template=make_template(); template.weights.flags.writeable=True; template.weights[:]=999.
    local,global_leaf=SplitLeaf(template,'LOCAL_RISK',BUILD),SplitLeaf(template,'GLOBAL_RISK',BUILD)
    np.testing.assert_array_equal(local.reward_weights,template.parent.source.weights)
    np.testing.assert_array_equal(global_leaf.reward_weights,template.parent.source.weights)
    assert local.setup_counts['allocated_weight_bytes']==local.reward_weights.nbytes+local.risk_weights.nbytes
    assert global_leaf.setup_counts['allocated_weight_bytes']==global_leaf.reward_weights.nbytes+global_leaf.risk_weights.nbytes
    fit_split(local,data(),BUILD); fit_split(global_leaf,data(),BUILD)
    np.testing.assert_array_equal(local.reward_weights,global_leaf.reward_weights)
    assert predict_components(local,[2]+[0]*15)['risk_probability']!=predict_components(global_leaf,[2]+[0]*15)['risk_probability']


@pytest.mark.parametrize('kind', ['LOCAL_RISK','GLOBAL_RISK'])
def test_trained_risk_head_is_used_at_each_second_ply_literal_h2_leaf(kind):
    template=make_template(); leaf=SplitLeaf(template,kind,BUILD); fit_split(leaf,data(),BUILD); leaf.freeze()
    probability=.43; board=[1,1,2,0]+[0]*12
    actual=leaf.choose(board,probability)
    expected={}
    for action in ('DOWN','LEFT','RIGHT','UP'):
        after,score,legal=leaf.rule.swipe(board,action)
        if not legal: continue
        if max(after)>=leaf.radix:
            tail=4.
        else:
            empty=[i for i,rank in enumerate(after) if not rank]; tail=0.
            for position in empty:
                for rank in (1,2):
                    spawned=list(after); spawned[position]=rank
                    if max(spawned)>=leaf.radix:
                        next_value=4.
                    else:
                        next_values=[]
                        for next_action in ('DOWN','LEFT','RIGHT','UP'):
                            second,reward,allowed=leaf.rule.swipe(spawned,next_action)
                            if allowed:
                                second_tail=4. if max(second)>=leaf.radix else literal_prediction(leaf,second)[2]
                                next_values.append(reward/2048.+second_tail)
                        next_value=max(next_values,default=-4.)
                    tail+=((1.-probability if rank==1 else probability)/len(empty))*next_value
        expected[action]=dict(afterstate=list(after),score=score,tail_value=tail,value=score/2048.+tail)
    assert actual['action_values']==expected
    assert actual['action']==min(expected,key=lambda a:(-expected[a]['value'],a))


@pytest.mark.parametrize('kind', ['LOCAL_RISK','GLOBAL_RISK'])
def test_large_finite_logit_probability_and_unclipped_log_loss(kind):
    template=make_template(); leaf=SplitLeaf(template,kind,BUILD)
    leaf.risk_weights[:]=-100.; leaf.freeze()
    predicted=predict_components(leaf,[3,3]+[0]*14)
    assert 0.<=predicted['risk_probability']<=1. and predicted['combined_prediction']==pytest.approx(predicted['reward_prediction']-4.)
    scores=score_split(leaf,data(),BUILD)
    assert math.isfinite(scores['component_game_metrics'][0]['risk_log_loss'])
    assert scores['component_game_metrics'][0]['risk_log_loss']>100.
