from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_retained_critic_v287 as audit


def test_factual_suffix_excludes_current_action_reward_and_winning_afterstate():
    assert audit.future_targets([4,8,16],'WON') == [4.+24/2048.,4.+16/2048.]
    assert audit.future_targets([4,8,16],'LOST') == [-4.+24/2048.,-4.+16/2048.,-4.]


def fit(method):
    learning=dict(td_updates=4,value_predictions=6 if method == 'TD' else 4,
        table_lookups=192 if method == 'TD' else 128,table_update_occurrences=128,table_updates=100)
    targets=dict(goal_checks=8 if method == 'TD' else 5,skipped_winning_afterstates=1,raw_target_subtractions=4)
    if method == 'TD': targets.update(analytic_next_tails=1,terminal_target_assignments=1,td_next_reward_additions=3,prediction_shift_additions=4)
    else: targets.update(suffix_games=2,suffix_target_assignments=5,suffix_reward_additions=5,target_buffer_doubles_peak=3)
    return dict(method=method,fitted_games=2,fitted_steps=5,trained_afterstates=4,
        learning_counts=learning,target_counts=targets,
        first_update=dict(target=3.,raw_target=3.,error=.5,raw_prediction_before_update=2.5),
        last_update=dict(target=-4.,raw_target=-4.,error=-1.,raw_prediction_before_update=-3.))


@pytest.mark.parametrize('method',['TD','MC'])
def test_same_nonwinning_updates_and_actual_target_construction_counts(method):
    games=[dict(steps=3,status='WON'),dict(steps=2,status='LOST')]
    receipt=fit(method)
    assert audit.check_fit(receipt,games,method) == 4
    receipt['learning_counts']['td_updates']=5
    with pytest.raises(ValueError,match='afterstate inventory'): audit.check_fit(receipt,games,method)


def heldout():
    actual=audit.future_targets([4,8],'LOST')
    mu=sum(actual)/2
    saved=dict(episode=3,start=10,end=12,count=2,bias=1.,mse=1.,mae=1.,
        mean_prediction=mu+1.,mean_factual_future_utility=mu)
    return dict(game_metrics=[saved],metrics=dict(bias=1.,mse=1.,mae=1.),
        prediction_counts=dict(value_predictions=2,table_lookups=64),
        target_counts=dict(goal_checks=2,suffix_games=1,suffix_target_assignments=2,
            suffix_reward_additions=2,prediction_shift_additions=4,target_buffer_doubles_peak=2))


def test_holdout_actual_future_return_and_static_prediction_counts():
    games=[dict(episode=3,steps=2,status='LOST')]
    value=heldout()
    assert audit.check_holdout(value,games,[[4,8]],10) == dict(games=1,samples=2,bias=1.,mse=1.,mae=1.)
    value['prediction_counts']['td_updates']=1
    with pytest.raises(ValueError,match='no training'): audit.check_holdout(value,games,[[4,8]],10)


@pytest.mark.parametrize('field',['count','mean_factual_future_utility','bias','mse'])
def test_holdout_corrupt_inventory_current_reward_bias_or_moment_is_rejected(field):
    value=heldout();row=value['game_metrics'][0]
    if field == 'count': row[field]=1
    if field == 'mean_factual_future_utility': row[field]+=4/2048.
    if field == 'bias': row[field]=-1.
    if field == 'mse': row[field]=.5
    with pytest.raises(ValueError): audit.check_holdout(value,[dict(episode=3,steps=2,status='LOST')],[[4,8]],10)


def test_heldout_episode_mean_is_not_sample_weighted():
    value=heldout()
    second=deepcopy(value['game_metrics'][0]);second.update(episode=4,start=12,end=13,count=1,
        bias=3.,mse=9.,mae=3.,mean_prediction=-1.,mean_factual_future_utility=-4.)
    value['game_metrics'].append(second);value['metrics']=dict(bias=2.,mse=5.,mae=2.)
    value['prediction_counts']=dict(value_predictions=3,table_lookups=96)
    value['target_counts'].update(goal_checks=3,suffix_games=2,suffix_target_assignments=3,suffix_reward_additions=3,prediction_shift_additions=6)
    result=audit.check_holdout(value,[dict(episode=3,steps=2,status='LOST'),dict(episode=4,steps=1,status='LOST')],[[4,8],[4]],10)
    assert result['mse'] == 5.
    value['metrics']['mse']=11/3
    with pytest.raises(ValueError,match='episode weighting'): audit.check_holdout(value,[dict(episode=3,steps=2,status='LOST'),dict(episode=4,steps=1,status='LOST')],[[4,8],[4]],10)
