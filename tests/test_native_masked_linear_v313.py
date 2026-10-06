"""Actual masked weights, complete factual targets and selected-state quotas."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_linear_win_v311 import QUERY, LinearWinLeaf, fit_linear
from acfqp.science.native_masked_linear_v313 import fit_masked_linear

BUILD = Path(__file__).resolve().parents[1]/'reports/closed_loop_v313/runtime_tests/masked_linear'


def leaf():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    template = QueryTD(QueryParent(source, QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    result = LinearWinLeaf(template, BUILD)
    result.win_weights[:] += np.arange(result.win_weights.size).reshape(result.win_weights.shape)%7*.002
    return result


def data():
    sparse = [2]+[0]*15
    return dict(afterstates=np.asarray([sparse, sparse, [2, 1]+[0]*14, [4]+[0]*15,
        sparse, sparse, [3, 3]+[0]*14, sparse, [4]+[0]*15], dtype=np.int32),
        rewards=np.asarray([4, 8, 16, 32, 4, 8, 16, 8, 16], dtype=np.float64)/2048.,
        ends=np.asarray([4, 7, 9], dtype=np.int64),
        terminal_codes=np.asarray([1, -1, 1], dtype=np.int32),
        fit_game_count=2, fit_step_end=7)


def reference_fit(model, dataset, mask):
    """Independent occurrence-count definition, with predictions frozen per game."""
    reward, win = model.reward_weights.reshape(-1), model.win_weights.reshape(-1)
    start = writes = 0
    samples = []
    for game in range(dataset['fit_game_count']):
        end = int(dataset['ends'][game]); suffix = 0.; targets = {}
        for step in range(end-1, start-1, -1):
            targets[step] = suffix; suffix += float(dataset['rewards'][step])
        steps = [step for step in range(start, end) if mask[step]]
        rows = {step:Counter(map(int, model.model.feature_indices(dataset['afterstates'][step])))
                for step in steps}
        denominators = Counter()
        for row in rows.values():
            denominators.update(row)
        errors = {}
        label = float(dataset['terminal_codes'][game]==1)
        for step in steps:
            addresses = list(map(int, model.model.feature_indices(dataset['afterstates'][step])))
            r = sum(float(reward[address]) for address in addresses)
            w = sum(float(win[address]) for address in addresses)
            errors[step] = targets[step]-r, label-w
            samples.append(dict(episode=game, step=step, reward_target=targets[step], win_target=label,
                reward_prediction=r, win_prediction=w, combined_prediction=r+8.*(w-.5),
                reward_error=targets[step]-r, win_error=label-w))
        for address in sorted(denominators):
            rg = wg = 0.
            for step in steps:
                if address in rows[step]:
                    rg += rows[step][address]*errors[step][0]
                    wg += rows[step][address]*errors[step][1]
            reward[address] += .0025*rg/denominators[address]
            win[address] += .0025*wg/denominators[address]
        writes += len(denominators); start = end
    return samples, writes


def test_masked_actual_weights_match_independent_game_start_residuals_and_occurrences():
    actual, reference = leaf(), leaf(); dataset = data()
    mask = np.asarray([1, 1, 0, 0, 1, 0, 1], dtype=np.int32)
    assert max(Counter(map(int, actual.model.feature_indices(dataset['afterstates'][0]))).values())>1
    result = fit_masked_linear(actual, dataset, mask, BUILD)
    samples, writes = reference_fit(reference, dataset, mask)
    np.testing.assert_array_equal(actual.reward_weights, reference.reward_weights)
    np.testing.assert_array_equal(actual.win_weights, reference.win_weights)
    assert result['first_sample']==samples[0] and result['last_sample']==samples[-1]
    # Unselected future rewards and the unselected winning afterstate remain factual targets.
    assert result['first_sample']['reward_target']==56/2048.
    assert result['first_sample']['win_target']==1. and result['last_sample']['win_target']==0.
    assert result['trained_afterstates']==actual.updates==4
    assert result['reward_trained_afterstates']==result['win_trained_afterstates']==4
    assert result['learning_counts']['table_updates']==2*writes
    assert result['learning_counts']['reward_table_updates']==result['learning_counts']['win_parameter_updates']==writes
    assert result['selection_counts']==dict(fit_afterstates_checked=7, winning_afterstates_skipped=1,
        nonwinning_selection_reads=6, unselected_nonwinning_afterstates=2,
        selected_nonwinning_afterstates=4, games_with_selected_samples=2)
    assert result['normalization_counts']['feature_occurrences']==128
    assert result['target_counts']['reward_suffix_target_assignments']==7
    assert result['target_counts']['win_label_assignments']==4


def test_full_eligible_mask_exactly_preserves_original_v311_weights_and_fit_endpoints():
    actual, original = leaf(), leaf(); dataset = data()
    mask = (np.max(dataset['afterstates'][:7], axis=1)<4).astype(np.int32)
    selected = fit_masked_linear(actual, dataset, mask, BUILD)
    full = fit_linear(original, dataset, BUILD)
    np.testing.assert_array_equal(actual.reward_weights, original.reward_weights)
    np.testing.assert_array_equal(actual.win_weights, original.win_weights)
    for key in ('learning_counts', 'target_counts', 'normalization_counts', 'representation_counts',
                'first_sample', 'last_sample', 'trained_afterstates'):
        assert selected[key]==full[key]


def test_empty_mask_and_games_without_selected_states_do_not_commit_parameters():
    actual = leaf(); dataset = data()
    reward, win = actual.reward_weights.copy(), actual.win_weights.copy()
    result = fit_masked_linear(actual, dataset, np.zeros(7, dtype=np.int32), BUILD)
    np.testing.assert_array_equal(actual.reward_weights, reward)
    np.testing.assert_array_equal(actual.win_weights, win)
    assert result['trained_afterstates']==actual.updates==0
    assert result['first_sample'] is result['last_sample'] is None
    assert result['selected_games']==0
    assert result['normalization_counts'].get('game_parameter_commits', 0)==0
    result = fit_masked_linear(actual, dataset, [0, 0, 0, 0, 1, 0, 0], BUILD)
    assert result['trained_afterstates']==actual.updates==1 and result['selected_games']==1
    assert result['first_sample']['episode']==1 and result['first_sample']['reward_target']==24/2048.


def test_heldout_rows_are_excluded_but_unselected_future_fit_rewards_still_change_supervision():
    actual, reference, altered = leaf(), leaf(), leaf(); dataset = data(); changed = deepcopy(dataset)
    changed['afterstates'][7:] = 0; changed['rewards'][7:] = 999.; changed['terminal_codes'][2] = -1
    mask = np.asarray([1, 0, 0, 0, 0, 0, 0], dtype=np.int32)
    first = fit_masked_linear(actual, dataset, mask, BUILD)
    second = fit_masked_linear(reference, changed, mask, BUILD)
    np.testing.assert_array_equal(actual.reward_weights, reference.reward_weights)
    np.testing.assert_array_equal(actual.win_weights, reference.win_weights)
    assert first['first_sample']==second['first_sample']
    changed['rewards'][2] += 1.
    third = fit_masked_linear(altered, changed, mask, BUILD)
    assert third['first_sample']['reward_target']==first['first_sample']['reward_target']+1.
    assert np.any(altered.reward_weights!=actual.reward_weights)
    np.testing.assert_array_equal(altered.win_weights, actual.win_weights)


@pytest.mark.parametrize('mask,message', [([1]*7, 'Winning'), ([1, 0], 'binary entry'),
                                         ([2, 0, 0, 0, 0, 0, 0], 'binary entry')])
def test_actual_selector_contract_rejects_winning_outside_prefix_and_nonbinary_masks(mask, message):
    with pytest.raises(ValueError, match=message):
        fit_masked_linear(leaf(), data(), mask, BUILD)


def test_frozen_collection_heads_cannot_be_fitted_without_an_explicit_writable_copy():
    model = leaf(); model.freeze()
    with pytest.raises(ValueError, match='writable'):
        fit_masked_linear(model, data(), [1, 0, 0, 0, 0, 0, 0], BUILD)


def test_cutoff_is_not_a_loss_label_for_masked_linear_supervision():
    dataset = data(); dataset['terminal_codes'][0] = 2
    with pytest.raises(ValueError, match='completed WON/LOST'):
        fit_masked_linear(leaf(), dataset, [1, 0, 0, 0, 0, 0, 0], BUILD)
