"""Full factual targets and literal masked game-normalized updates."""
from collections import Counter
from fractions import Fraction
import math
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_replay_fit_v307 import fit_masked_split
from acfqp.science.native_split_risk_v301 import QUERY, SplitLeaf, fit_split

BUILD = Path(__file__).resolve().parents[1]/'reports/experience_replay_v307/runtime/tests/native'


def leaf():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9,10)), (2, Fraction(1,10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    template = QueryTD(QueryParent(source, QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    result = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    result.risk_weights[:] = np.arange(result.risk_weights.size).reshape(result.risk_weights.shape)%7*.002
    return result


def data():
    return dict(afterstates=np.asarray([[2]+[0]*15, [2,1]+[0]*14, [3,3]+[0]*14,
        [4]+[0]*15, [2]+[0]*15, [2,1]+[0]*14, [3,3]+[0]*14,
        [2]+[0]*15, [3,3]+[0]*14, [4]+[0]*15], dtype=np.int32),
        rewards=np.asarray([4,8,16,16,4,8,16,4,8,16], dtype=np.float64)/2048.,
        ends=np.asarray([4,7,10], dtype=np.int64),
        terminal_codes=np.asarray([1,-1,1], dtype=np.int32), fit_game_count=2, fit_step_end=7)


def eligible(dataset):
    return (np.max(dataset['afterstates'][:dataset['fit_step_end']], axis=1)<4).astype(np.int32)


def literal_fit(model, dataset, mask):
    reward_weights, risk_weights = model.reward_weights.reshape(-1), model.risk_weights.reshape(-1)
    start=0; examples=[]
    for game in range(dataset['fit_game_count']):
        end=int(dataset['ends'][game]); suffix=0.; targets={}
        for step in range(end-1,start-1,-1):
            targets[step]=suffix; suffix+=float(dataset['rewards'][step])
        steps=[step for step in range(start,end) if mask[step]]
        occurrences={step:Counter(map(int, model.model.feature_indices(dataset['afterstates'][step]))) for step in steps}
        denominators=Counter()
        for row in occurrences.values(): denominators.update(row)
        reward_grad={address:0. for address in denominators}
        risk_grad={address:0. for address in denominators}
        label=float(dataset['terminal_codes'][game]==1)
        for step in steps:
            addresses=list(map(int,model.model.feature_indices(dataset['afterstates'][step])))
            reward=sum(float(reward_weights[address]) for address in addresses)
            logit=sum(float(risk_weights[address]) for address in addresses)
            probability=1./(1.+math.exp(-logit)) if logit>=0. else math.exp(logit)/(1.+math.exp(logit))
            combined=reward+8.*(probability-.5)
            reward_error, risk_error=targets[step]-reward,label-probability
            examples.append(dict(episode=game,step=step,reward_target=targets[step],risk_target=label,
                reward_prediction=reward,risk_probability=probability,combined_prediction=combined,
                reward_error=reward_error,risk_error=risk_error))
            for address,count in sorted(occurrences[step].items()):
                reward_grad[address]+=count*reward_error
                risk_grad[address]+=count*risk_error
        for address,gradient in reward_grad.items(): reward_weights[address]+=.0025*gradient/denominators[address]
        for address,gradient in risk_grad.items(): risk_weights[address]+=.0025*gradient/denominators[address]
        start=end
    return examples


def test_all_eligible_mask_exactly_reproduces_v301_fit_parameters_and_scientific_receipt():
    original, masked = leaf(), leaf(); dataset=data()
    expected=fit_split(original,dataset,BUILD)
    actual=fit_masked_split(masked,dataset,eligible(dataset),BUILD)
    np.testing.assert_array_equal(original.reward_weights,masked.reward_weights)
    np.testing.assert_array_equal(original.risk_weights,masked.risk_weights)
    ignored={'seconds','cpu_seconds','setup_counts'}
    assert {k:v for k,v in expected.items() if k not in ignored} == {
        k:v for k,v in actual.items() if k not in ignored|{'candidate_fitted_games','selected_games','selection_counts'}}
    assert original.updates==masked.updates==6
    assert actual['selection_counts']['selected_nonwinning_afterstates']==6
    assert actual['selection_counts']['winning_afterstates_skipped']==1
    assert actual['candidate_fitted_games']==actual['selected_games']==2


def test_discontiguous_mask_keeps_full_future_rewards_and_original_win_label():
    actual, reference=leaf(),leaf(); dataset=data()
    mask=np.asarray([1,0,1,0,0,0,0], dtype=np.int32)
    examples=literal_fit(reference,dataset,mask)
    result=fit_masked_split(actual,dataset,mask,BUILD)
    np.testing.assert_array_equal(actual.reward_weights,reference.reward_weights)
    np.testing.assert_array_equal(actual.risk_weights,reference.risk_weights)
    assert result['first_sample']==examples[0] and result['last_sample']==examples[-1]
    assert result['first_sample']['reward_target']==40/2048.
    assert result['last_sample']['reward_target']==16/2048.
    assert result['first_sample']['risk_target']==result['last_sample']['risk_target']==1.
    assert actual.updates==result['trained_afterstates']==2
    assert result['target_counts']['reward_suffix_target_assignments']==7
    assert result['target_counts']['terminal_game_labels']==2
    assert result['selected_games']==1 and result['candidate_fitted_games']==2
    assert result['normalization_counts']['game_parameter_commits']==1


def test_exact_update_budget_and_game_start_normalization_match_literal_masked_fit():
    actual, reference=leaf(),leaf(); dataset=data()
    mask=np.asarray([0,1,0,0,1,0,1], dtype=np.int32)
    examples=literal_fit(reference,dataset,mask)
    result=fit_masked_split(actual,dataset,mask,BUILD)
    np.testing.assert_array_equal(actual.reward_weights,reference.reward_weights)
    np.testing.assert_array_equal(actual.risk_weights,reference.risk_weights)
    assert result['first_sample']==examples[0] and result['last_sample']==examples[-1]
    assert actual.updates==sum(mask)==result['trained_afterstates']==3
    assert result['reward_trained_afterstates']==result['risk_trained_afterstates']==3
    assert result['learning_counts']['table_update_occurrences']==96
    assert result['selection_counts']['unselected_nonwinning_afterstates']==3
    assert result['selection_counts']['games_with_selected_samples']==2


def test_empty_selection_preserves_parameters_and_charges_only_full_target_processing():
    model=leaf(); dataset=data(); reward,risk=model.reward_weights.copy(),model.risk_weights.copy()
    result=fit_masked_split(model,dataset,np.zeros(7,dtype=np.int32),BUILD)
    np.testing.assert_array_equal(model.reward_weights,reward)
    np.testing.assert_array_equal(model.risk_weights,risk)
    assert model.updates==result['trained_afterstates']==result['selected_games']==0
    assert result['first_sample'] is None and result['last_sample'] is None
    assert result['learning_counts']=={} and result['target_counts']['reward_suffix_additions']==7
    assert result['candidate_fitted_games']==2
    assert result['selection_counts']['unselected_nonwinning_afterstates']==6


@pytest.mark.parametrize('mask', [np.ones(6,dtype=np.int32), np.asarray([1,1,1,1,1,1,1]),
    np.asarray([1,1,1,0,1,1,2])])
def test_selection_cannot_redefine_fit_boundary_or_include_winning_rows(mask):
    with pytest.raises(ValueError):
        fit_masked_split(leaf(),data(),mask,BUILD)
