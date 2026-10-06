"""Exact replay budgets without changing complete factual target inventories."""
from copy import deepcopy
import numpy as np
import pytest

from acfqp.science.experience_selection_v307 import build_replay, game_priority


def data(scale=1.):
    boards = np.tile([1, 0]+[0]*14, (17, 1)).astype(np.int32)
    boards[7, 0] = 11
    return dict(afterstates=boards, rewards=np.arange(1, 18)*scale/2048.,
        ends=np.asarray([5, 8, 12, 17], dtype=np.int64), terminal_codes=np.asarray([-1, 1, -1, -1], dtype=np.int32),
        fit_game_count=3, fit_step_end=12,
        games=[dict(episode=i, steps=length, status='WON' if i==1 else 'LOST', split='FIT' if i<3 else 'HELDOUT')
            for i,length in enumerate((5, 3, 4, 5))])


def test_game_priority_is_fixed_midpoint_breadth_first_without_repetition():
    assert list(game_priority(7))==[3, 1, 5, 0, 2, 4, 6]
    assert list(game_priority(0))==[]


def test_new_only_keeps_original_dataset_and_complete_fit_mask_not_heldout():
    old, current = data(), data(2.)
    result = build_replay(old, current)
    assert result['datasets']['NEW_ONLY'] is current
    assert result['masks']['NEW_ONLY'].shape==(12,)
    assert result['budget']==11 and result['masks']['NEW_ONLY'].sum()==11
    assert result['masks']['NEW_ONLY'][7]==0
    assert all(row['source_game']<3 and row['source_end']<=12 for row in result['plans']['NEW_ONLY']['games'])


def test_whole_game_suffix_data_and_original_codes_survive_exact_partial_quota():
    old, current = data(), data(2.)
    result = build_replay(old, current)
    plan, mixed = result['plans']['MIXED_REPLAY'], result['datasets']['MIXED_REPLAY']
    assert plan['quotas']==dict(OLD_A1=5, CURRENT_DATA=6)
    assert result['masks']['MIXED_REPLAY'].sum()==result['masks']['NEW_ONLY'].sum()==11
    assert [(row['source'], row['source_game']) for row in plan['games']]==[
        ('OLD_A1', 0), ('CURRENT_DATA', 0), ('OLD_A1', 1), ('CURRENT_DATA', 1)]
    assert plan['games'][0]['selected_local_steps']==[0, 2, 4]
    assert plan['games'][1]['selected_local_steps']==[0, 1, 3, 4]
    for index, row in enumerate(plan['games']):
        source = old if row['source']=='OLD_A1' else current
        np.testing.assert_array_equal(mixed['afterstates'][row['fit_start']:row['fit_end']], source['afterstates'][row['source_start']:row['source_end']])
        np.testing.assert_array_equal(mixed['rewards'][row['fit_start']:row['fit_end']], source['rewards'][row['source_start']:row['source_end']])
        assert mixed['terminal_codes'][index]==source['terminal_codes'][row['source_game']]
        assert result['masks']['MIXED_REPLAY'][row['fit_start']:row['fit_end']].sum()==row['selected_count']
    assert not np.any(result['masks']['MIXED_REPLAY'] & (np.max(mixed['afterstates'], axis=1)>=11))


def test_selection_does_not_choose_games_using_reward_or_fitted_predictions():
    old, current = data(), data(2.)
    baseline = build_replay(old, current)['plans']
    changed = deepcopy(current); changed['rewards'] *= 100.
    assert build_replay(old, changed)['plans']==baseline


def test_missing_old_fit_facts_stop_instead_of_replacing_or_changing_mix():
    old, current = data(), data(2.)
    old['fit_game_count']=1; old['fit_step_end']=5
    current['afterstates'][7, 0]=1
    with pytest.raises(ValueError, match='quotas'):
        build_replay(old, current)
