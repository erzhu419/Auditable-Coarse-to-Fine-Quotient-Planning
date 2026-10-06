"""Finite mutations of V299 arithmetic; no fitting, world or bootstrap."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_b_mechanism_v299 as audit


def test_winning_afterstate_is_not_a_trainable_sample():
    game = dict(status='WON', steps=8)
    audit.check_episode_identity(0, 'WON', 7, game)
    with pytest.raises(ValueError, match='nonwinning training samples'):
        audit.check_episode_identity(0, 'WON', 8, game)


def test_retained_loss_donor_cannot_be_relabelled_as_win():
    with pytest.raises(ValueError, match='natural donor outcome'):
        audit.check_episode_identity(0, 'WON', 7, dict(status='LOST', steps=8))


@pytest.mark.parametrize('status,terminal', [('WON', 4.), ('LOST', -4.)])
def test_mc_suffix_excludes_immediate_action_reward(status, terminal):
    scores = [2048, 4096, 1024]
    audit.check_mc_target(scores, status, 0, terminal+2.5)
    audit.check_mc_target(scores, status, 2, terminal)
    with pytest.raises(ValueError, match='factual MC suffix'):
        audit.check_mc_target(scores, status, 0, terminal+3.5)


def test_local_loss_increase_cannot_be_hidden_by_final_panel_improvement():
    audit.check_loss_descent(4., 3.)
    with pytest.raises(ValueError, match='increased its own'):
        audit.check_loss_descent(4., 4.1)


def test_game_prediction_delta_uses_previous_snapshot():
    audit.check_panel_delta([10., 12.], [9., 13.], [-1., 1.])
    with pytest.raises(ValueError, match='delta arithmetic'):
        audit.check_panel_delta([10., 12.], [9., 13.], [1., 1.])


def test_signed_win_and_loss_donors_both_close():
    source, final = [10., 12.], [8., 13.]
    donors = [('WON', [1., -2.]), ('LOST', [-3., 3.])]
    assert audit.check_telescoping(source, final, donors) == {
        'WON': [1., -2.], 'LOST': [-3., 3.]}
    with pytest.raises(ValueError, match='signed WON/LOST'):
        audit.check_telescoping(source, final, donors[:1])


def test_prediction_inventory_cannot_be_shortened_by_zip():
    with pytest.raises(ValueError, match='inventory'):
        audit.check_panel_delta([1., 2.], [1.], [0.])


def test_root_margin_and_tie_order_are_independent_arithmetic():
    audit.check_margin(dict(LEFT=3., RIGHT=3., UP=2.), 'LEFT', 0.)
    with pytest.raises(ValueError, match='lexical tie order'):
        audit.check_margin(dict(LEFT=3., RIGHT=3., UP=2.), 'RIGHT', 0.)
    with pytest.raises(ValueError, match='runner-up margin'):
        audit.check_margin(dict(LEFT=3., UP=2.), 'LEFT', 2.)


def test_one_action_root_does_not_invent_a_margin():
    audit.check_margin(dict(LEFT=3.), 'LEFT', None)
    with pytest.raises(ValueError, match='no runner-up margin'):
        audit.check_margin(dict(LEFT=3.), 'LEFT', 0.)


def test_factual_loss_closure_cannot_drop_the_quadratic_term():
    targets, source, final = [10.], [8.], [9.]
    donors = [('WON', [2.]), ('LOST', [-1.])]
    audit.check_loss_delta_closure(targets, source, final, donors, -3.)
    with pytest.raises(ValueError, match='loss change arithmetic'):
        audit.check_loss_delta_closure(targets, source, final, donors, -4.)


def test_offline_diagnostic_cannot_pay_old_raw_as_new():
    audit.check_zero_new_world(0, 0, 131072, 131072)
    with pytest.raises(ValueError, match='new world'):
        audit.check_zero_new_world(131072, 0, 131072, 131072)
    with pytest.raises(ValueError, match='omitted or repaid'):
        audit.check_zero_new_world(0, 0, 0, 131072)


def test_temporal_panel_is_frozen_without_selecting_outcomes_or_values():
    games = [dict(status='WON', steps=5) for _ in range(12)]
    assert audit.expected_panel_indices(games, 8) == [
        0,1,2,3,10,11,12,13,20,21,22,23,35,36,37,38,
        40,41,42,43,45,46,47,48,50,51,52,53,55,56,57,58]


def test_h2_remax_cannot_fall_below_its_available_frozen_choice():
    source, fixed, current = dict(LEFT=3.), dict(LEFT=2.), dict(LEFT=2.5)
    assert audit.check_h2_decomposition(source, current, fixed)['LEFT'] == dict(
        leaf=-1., remax=.5, total=-.5)
    with pytest.raises(ValueError, match='below the frozen'):
        audit.check_h2_decomposition(source, dict(LEFT=1.5), fixed)


def test_full_score_suffix_mean_keeps_last_winning_reward_for_prior_samples():
    games = [dict(episode=1, steps=3, score=14336, status='WON', split='FIT'),
             dict(episode=2, steps=3, score=14336, status='LOST', split='HELDOUT')]
    scores = {1:[2048,4096,8192], 2:[2048,4096,8192]}
    rows = []
    for ordinal, game in enumerate(games):
        target = 9. if ordinal == 0 else -2./3.
        rows.append(dict(episode=ordinal,start=3*ordinal,end=3*(ordinal+1),
            count=2 if ordinal==0 else 3,status=game['status'],split=game['split'],
            mean_prediction=target,mean_factual_future_utility=target,bias=0.,mse=0.,mae=0.))
    result = dict(game_metrics=rows,metrics=dict(bias=0.,mse=0.,mae=0.))
    original = [{key:value for key,value in rows[1].items() if key not in ('split','status')}]
    audit.check_full_score(result,games,scores,original)
    rows[0]['mean_factual_future_utility'] -= 4.
    with pytest.raises(ValueError, match='future suffix mean'):
        audit.check_full_score(result,games,scores,original)
