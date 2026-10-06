"""Outcome-blind panel selection, local contraction and factual attribution."""
from copy import deepcopy

import numpy as np
import pytest

from acfqp.science.b_mechanism_analysis_v299 import select_indices, summarize


def dataset():
    boards = np.zeros((60,16),dtype=np.int32)
    boards[4::5,0] = 11
    return dict(afterstates=boards, ends=np.arange(5,61,5), fit_game_count=8,
                terminal_codes=np.ones(12), rewards=np.arange(60))


def metric(episode,split,status,value,count=1):
    return dict(episode=episode,split=split,status=status,count=count,
        bias=value,mse=value,mae=value,mean_prediction=value,mean_factual_future_utility=0.)


def life(lifecycle=0,scale=1.):
    source = [metric(0,'FIT','LOST',2.),metric(1,'FIT','WON',6.,1000),
              metric(2,'HELDOUT','LOST',3.),metric(3,'HELDOUT','WON',7.,1000)]
    learned = [dict(row,**{k:row[k]+scale for k in ('bias','mse','mae','mean_prediction')}) for row in source]
    return dict(lifecycle=lifecycle,parent=lifecycle%4,
        final_full=dict(SOURCE=dict(game_metrics=source),MEAN=dict(game_metrics=learned)),
        panel=[dict(split='FIT',episode=0,target=-1.,status='LOST'),
               dict(split='HELDOUT',episode=3,target=9.,status='WON')],
        snapshots=[dict(completed_fit_games=0,predictions=[2.,3.]),
                   dict(completed_fit_games=1,predictions=[2.5,4.]),
                   dict(completed_fit_games=2,predictions=[2.25,3.5])],
        updates=[dict(game=0,status='WON',local_mse_before=10.,local_mse_after=9.,
                      local_samples=1000,delta_predictions=[.5,1.]),
                 dict(game=1,status='LOST',local_mse_before=2.,local_mse_after=1.5,
                      local_samples=1,delta_predictions=[-.25,-.5])],h2=[])


def test_panel_selects_four_time_games_and_nonwinning_steps_without_labels():
    data = dataset()
    assert select_indices(data,'FIT') == [0,1,2,3,10,11,12,13,20,21,22,23,35,36,37,38]
    assert select_indices(data,'HELDOUT') == [40,41,42,43,45,46,47,48,50,51,52,53,55,56,57,58]
    data['rewards'] *= -999
    data['terminal_codes'] *= -1
    assert select_indices(data,'FIT') == [0,1,2,3,10,11,12,13,20,21,22,23,35,36,37,38]


def test_small_panel_has_no_duplicate_games_or_steps_and_keeps_global_indices():
    data = dataset()
    data.update(ends=np.asarray([2,5]),fit_game_count=1)
    assert select_indices(data,'FIT') == [0,1]
    assert select_indices(data,'HELDOUT') == [2,3]


def test_full_metrics_use_games_then_lives_and_keep_terminal_groups():
    result = summarize([life(0,1.),life(1,-3.)])
    assert result['final_full']['FIT']['arms']['SOURCE']['metrics']['mse'] == 4.
    assert result['final_full']['HELDOUT']['MEAN_minus_SOURCE']['mse'] == -1.
    assert result['final_full']['HELDOUT']['mse_increased_lifecycles'] == [0]
    won = result['final_full']['HELDOUT']['terminal']['WON']
    assert won['arms']['SOURCE']['metrics']['mse'] == 7.
    assert won['arms']['SOURCE']['samples'] == 2000
    assert won['MEAN_minus_SOURCE']['bias'] == -1.


def test_donor_terminal_deltas_close_and_preserve_each_recipient():
    result = summarize([life()])
    assert result['panel_prediction_delta_closed']
    assert result['panel_prediction_deltas']['FIT']['donor_prediction_deltas'] == dict(WON=.5,LOST=-.25)
    assert result['panel_prediction_deltas']['HELDOUT']['observed_prediction_delta'] == .5
    panel = result['by_lifecycle'][0]['panel_prediction_deltas']['panel']
    assert panel[1]['target'] == 9. and panel[1]['status'] == 'WON'
    assert panel[1]['closure_residual'] == 0.


def test_missing_shared_update_contribution_reports_failed_closure():
    row = life()
    row['updates'][1]['delta_predictions'][1] = 0.
    result = summarize([row])
    assert not result['panel_prediction_delta_closed']
    assert result['by_lifecycle'][0]['panel_prediction_deltas']['panel'][1]['closure_residual'] == -.5


def test_chronological_donor_loss_contributions_include_the_cross_term():
    result = summarize([life()])
    assert result['panel_factual_loss_delta_closed']
    fit = result['panel_prediction_deltas']['FIT']
    assert fit['donor_factual_mse_deltas'] == dict(WON=3.25,LOST=-1.6875)
    assert fit['observed_factual_mse_delta'] == 1.5625
    heldout = result['panel_prediction_deltas']['HELDOUT']
    assert heldout['donor_factual_mse_deltas'] == dict(WON=-11.,LOST=5.25)
    assert heldout['observed_factual_mse_delta'] == -5.75


def test_local_game_mse_increase_is_retained_with_identity():
    row = life()
    row['updates'][1]['local_mse_after'] = 2.125
    result = summarize([row])
    assert not result['local_update']['all_game_mse_nonincreasing']
    assert result['local_update']['increasing_games'] == [dict(lifecycle=0,game=1)]
    assert result['local_update']['mean_game_mse_delta'] == -.4375


def test_analysis_keeps_input_readonly_and_life_order_deterministic():
    rows = [life(1,-3.),life(0,1.)]
    original = deepcopy(rows)
    result = summarize(rows)
    assert rows == original
    assert result == summarize(list(reversed(rows)))
    assert result['local_update']['all_game_mse_nonincreasing']
    assert result['local_update']['mean_game_mse_delta'] == -.75
    assert 'No new bootstrap' in result['evidence_scope']
