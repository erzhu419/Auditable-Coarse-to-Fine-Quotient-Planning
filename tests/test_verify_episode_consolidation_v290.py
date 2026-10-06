from pathlib import Path
from copy import deepcopy
from statistics import mean
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_episode_consolidation_v290 as audit


def test_address_exposure_uses_real_occurrence_multiplicity():
    result=audit.episode_math({0:1.,1:0.},[[0,0],[0,1]],[0.,0.],
        'EPISODE_MEAN_MC',alpha=.25)
    assert result['exposure']=={0:3,1:1}
    assert result['weights']==pytest.approx({0:1.-5./12.,1:-.25})
    assert result['sample_addresses']==3 and result['episode_addresses']==2


def test_sequential_residual_uses_current_weights_mean_uses_game_start():
    features=[[0,0],[0,1]];weights={0:1.,1:0.}
    seq=audit.episode_math(weights,features,[0.,0.],'NORMALIZED_SEQUENTIAL_MC',alpha=.25)
    avg=audit.episode_math(weights,features,[0.,0.],'EPISODE_MEAN_MC',alpha=.25)
    assert seq['examples'][1]['prediction']==pytest.approx(2./3.)
    assert avg['examples'][1]['prediction']==1.
    assert seq['weights'] != avg['weights']
    assert weights=={0:1.,1:0.}


def test_query_offset_subtracted_once_in_converted_residual():
    result=audit.episode_math({0:1.},[[0,0]],[5.],'EPISODE_MEAN_MC',offset=3.,alpha=.25)
    assert result['examples'][0]==dict(prediction=5.,error=0.)
    assert result['weights']=={0:1.}


def test_one_address_exposure_is_per_episode_not_per_dataset():
    first=audit.episode_math({0:0.},[[0],[0]],[1.,1.],'EPISODE_MEAN_MC',alpha=.25)
    second=audit.episode_math(first['weights'],[[0]],[1.],'EPISODE_MEAN_MC',alpha=.25)
    assert first['weights'][0]==.25 and second['weights'][0]==.4375


def test_same_address_mean_is_order_independent_in_exact_fixture():
    a=audit.episode_math({0:1.,1:0.},[[0,0],[0,1]],[0.,0.],'EPISODE_MEAN_MC',alpha=.25)
    b=audit.episode_math({0:1.,1:0.},[[0,1],[0,0]],[0.,0.],'EPISODE_MEAN_MC',alpha=.25)
    assert a['weights']==b['weights']


def test_registered_paired_seeds_are_fresh_and_distinct_across_lives():
    seeds={audit.evaluation_seed(life,episode) for life in range(16) for episode in range(16)}
    assert len(seeds)==256 and min(seeds)==290500000000 and max(seeds)==290515000015
    assert not seeds & {287500000000+life*1000000+episode for life in range(16) for episode in range(16)}


def normalized_receipt(method):
    games=[dict(episode=0,steps=2,status='LOST',score=12),dict(episode=1,steps=2,status='WON',score=24)]
    scores={0:[4,8],1:[8,16]};sample_unique,game_unique=12,8
    writes=game_unique if method=='EPISODE_MEAN_MC' else sample_unique
    work=dict(games_processed=2,feature_extractions=3,feature_occurrences=96,feature_digit_reads=576,
        feature_address_multiply_adds=576,game_sort_calls=2,game_sort_items=96,address_occurrence_count_visits=96,
        address_occurrence_count_comparisons=94,sample_sort_calls=3,sample_sort_items=96,
        sample_unique_addresses=sample_unique,game_unique_addresses=game_unique,address_denominator_searches=12,
        parameter_write_events=writes,normalization_divisions=writes,
        feature_index_buffer_int64_peak=64,sorted_feature_buffer_int64_peak=64,
        sample_step_buffer_int64_peak=2,sample_end_buffer_int64_peak=2,
        game_address_buffer_int64_peak=4,game_denominator_buffer_int64_peak=4,
        sample_address_buffer_int64_peak=8,sample_multiplicity_buffer_int64_peak=8)
    if method=='EPISODE_MEAN_MC':
        work.update(game_parameter_commits=2,weighted_residual_multiplications=12,
            weighted_residual_accumulations=12,parameter_update_multiplications=writes,
            error_buffer_doubles_peak=2,raw_prediction_buffer_doubles_peak=2,address_gradient_buffer_doubles_peak=4)
    else:work.update(sample_parameter_commits=3,parameter_update_multiplications=2*writes)
    work['native_buffer_bytes_peak']=8*(sum(v for k,v in work.items() if k.endswith('_peak'))+2)
    first=audit.factual_targets(scores[0],'LOST')[0];last=audit.factual_targets(scores[1],'WON')[0]
    def sample(episode,step,target):return dict(episode=episode,step=step,target=target,raw_target=target,
        error=target-1.,raw_prediction_before_update=1.)
    fit=dict(method=method,alpha=.0025,fitted_games=2,fitted_steps=4,trained_afterstates=3,
        learning_counts=dict(td_updates=3,value_predictions=3,table_lookups=96,table_update_occurrences=96,table_updates=writes),
        target_counts=dict(goal_checks=4,suffix_games=2,suffix_target_assignments=4,suffix_reward_additions=4,
            raw_target_subtractions=3,skipped_winning_afterstates=1,target_buffer_doubles_peak=2),
        consolidation_counts=work,first_sample=sample(0,0,first),last_sample=sample(1,2,last),
        count_semantics=dict(td_updates='Nonwinning training samples processed',table_update_occurrences='not parameter writes'))
    return fit,games,dict(fit_step_end=4),scores


@pytest.mark.parametrize('method',['NORMALIZED_SEQUENTIAL_MC','EPISODE_MEAN_MC'])
def test_physical_sample_and_parameter_writes_remain_distinct(method):
    fit,games,data,scores=normalized_receipt(method)
    assert audit.check_normalized_fit(fit,games,data,scores,method)==(8 if method=='EPISODE_MEAN_MC' else 12)
    fit['learning_counts']['table_updates']+=1
    with pytest.raises(ValueError,match='parameter writes'):audit.check_normalized_fit(fit,games,data,scores,method)


def test_mse_and_utility_quality_directions_preserve_actual_adverse_lives():
    values=[-1.,1.]*8
    result=dict(mean=0.,ci95=[0.,0.],lifecycle_deltas={str(i):v for i,v in enumerate(values)},
        parent_mean_deltas={str(p):mean(values[p::4]) for p in range(4)},interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS',
        improved_equal_worse=[8,0,8],adverse_lifecycles=list(range(0,16,2)))
    audit.check_contrast(result,values,'higher_is_better')
    result.update(positive_equal_negative=[8,0,8],adverse_lifecycles=list(range(1,16,2)))
    audit.check_contrast(result,values,'lower_is_better')
    result['adverse_lifecycles']=[]
    with pytest.raises(ValueError,match='adverse'):audit.check_contrast(result,values,'lower_is_better')


def test_last_normalized_target_does_not_include_current_reward():
    fit,games,data,scores=normalized_receipt('EPISODE_MEAN_MC')
    fit['last_sample']['target']+=8/2048.
    with pytest.raises(ValueError,match='after-current-action'):audit.check_normalized_fit(fit,games,data,scores,'EPISODE_MEAN_MC')
