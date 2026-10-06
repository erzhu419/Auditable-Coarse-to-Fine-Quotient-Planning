"""Real native two-head normalization, scalar MC identity and H2 execution."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_episode_consolidation_v290 import fit_consolidated
from acfqp.science.native_linear_win_v311 import (
    QUERY, LinearWinLeaf, evaluate_linear, fit_linear, predict_components, score_linear)
from acfqp.science.native_value_stream_v286 import NativeValueStream

BUILD = Path(__file__).resolve().parents[1]/'reports/linear_contribution_v311/runtime_tests/native'


def template():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    result = QueryTD(QueryParent(source, QUERY, QUERY, .5), 'PRIOR', BUILD)
    result.freeze()
    return result


def data():
    sparse = [2]+[0]*15
    boards = [sparse, sparse, [2, 1]+[0]*14, [3, 3]+[0]*14, [4]+[0]*15,
        [1, 2, 1, 2]*3+[2, 1, 2, 0], sparse, sparse, [3, 3]+[0]*14, [4]+[0]*15]
    return dict(afterstates=np.asarray(boards, dtype=np.int32),
        rewards=np.asarray([4, 8, 16, 8, 16, 0, 4, 8, 8, 16], dtype=np.float64)/2048.,
        ends=np.asarray([3, 5, 8, 10], dtype=np.int64),
        terminal_codes=np.asarray([-1, 1, -1, 1], dtype=np.int32), fit_game_count=3, fit_step_end=8)


def literal_prediction(leaf, board):
    addresses = list(map(int, leaf.model.feature_indices(board)))
    reward = sum(float(leaf.reward_weights.reshape(-1)[address]) for address in addresses)
    win = sum(float(leaf.win_weights.reshape(-1)[address]) for address in addresses)
    return reward, win, reward+8.*(win-.5)


def literal_fit(leaf, dataset):
    start, examples, writes, products = 0, [], 0, 0
    reward_flat, win_flat = leaf.reward_weights.reshape(-1), leaf.win_weights.reshape(-1)
    for game in range(dataset['fit_game_count']):
        end = int(dataset['ends'][game]); suffix = 0.; targets = {}
        for step in range(end-1, start-1, -1):
            targets[step]=suffix; suffix+=float(dataset['rewards'][step])
        steps = [step for step in range(start, end) if max(dataset['afterstates'][step])<leaf.radix]
        occurrences = {step:Counter(map(int, leaf.model.feature_indices(dataset['afterstates'][step]))) for step in steps}
        denominators = Counter()
        for row in occurrences.values():
            denominators.update(row)
        gradients = {address:[0., 0.] for address in denominators}
        residuals = {}; label = float(dataset['terminal_codes'][game]==1)
        for step in steps:
            reward, win, utility = literal_prediction(leaf, dataset['afterstates'][step])
            residuals[step]=(targets[step]-reward, label-win)
            examples.append(dict(episode=game, step=step, reward_target=targets[step], win_target=label,
                reward_prediction=reward, win_prediction=win, combined_prediction=utility,
                reward_error=targets[step]-reward, win_error=label-win))
        for step, row in occurrences.items():
            for address, count in sorted(row.items()):
                gradients[address][0]+=count*residuals[step][0]
                gradients[address][1]+=count*residuals[step][1]
                products+=1
        for address, (reward_gradient, win_gradient) in gradients.items():
            reward_flat[address]+=.0025*reward_gradient/denominators[address]
            win_flat[address]+=.0025*win_gradient/denominators[address]
        writes+=len(denominators); start=end
    return examples, writes, products


def test_initial_heads_copy_original_source_and_match_its_full_h2_values():
    original = template(); original.weights.flags.writeable=True; original.weights[:]=999.; original.freeze()
    leaf = LinearWinLeaf(original, BUILD)
    np.testing.assert_array_equal(leaf.reward_weights, original.parent.source.weights)
    assert leaf.weights is leaf.reward_weights
    assert not np.shares_memory(leaf.reward_weights, original.parent.source.weights)
    assert not np.shares_memory(leaf.reward_weights, leaf.win_weights)
    assert np.all(leaf.win_weights==1/64)
    assert leaf.setup_counts['allocated_weight_parameters']==2*leaf.reward_weights.size
    assert leaf.setup_counts['allocated_weight_bytes']==2*leaf.reward_weights.nbytes
    assert leaf.setup_counts['source_parameters_copied']==leaf.reward_weights.size
    assert leaf.setup_counts['initialized_half_win_parameters']==leaf.win_weights.size
    leaf.freeze()
    source = QueryTD(original.parent, 'PRIOR', BUILD); source.freeze()
    planner = FrozenLeafPlanner(source, 2, BUILD); planner.spawn_probabilities=(1.-.43, .43)
    for board in ([2]+[0]*15, [1, 1, 2, 0]+[0]*12):
        components = predict_components(leaf, board)
        assert components['win_prediction']==.5
        assert components['combined_prediction']==source.model.value(board)
        expected, actual = planner.choose(board), leaf.choose(board, .43)
        for key in ('action', 'afterstate', 'score', 'value', 'tail_value', 'action_values', 'status', 'counts'):
            assert actual[key]==expected[key]
    assert original.updates==original.parent.source.updates==leaf.updates==0


def test_native_game_start_updates_match_independent_occurrence_normalization_and_real_counts():
    source = template(); actual, reference = LinearWinLeaf(source, BUILD), LinearWinLeaf(source, BUILD)
    dataset = data()
    assert max(Counter(map(int, actual.model.feature_indices(dataset['afterstates'][0]))).values())>1
    before_reward, before_win = actual.reward_weights.copy(), actual.win_weights.copy()
    result = fit_linear(actual, dataset, BUILD); examples, writes, products = literal_fit(reference, dataset)
    np.testing.assert_array_equal(actual.reward_weights, reference.reward_weights)
    np.testing.assert_array_equal(actual.win_weights, reference.win_weights)
    assert np.any(actual.reward_weights!=before_reward) and np.any(actual.win_weights!=before_win)
    assert result['method']=='LINEAR_WIN2' and result['alpha']==.0025
    assert result['first_sample']==examples[0] and result['last_sample']==examples[-1]
    assert result['trained_afterstates']==actual.updates==7
    assert result['reward_trained_afterstates']==result['win_trained_afterstates']==7
    assert result['frozen_game_start_targets']
    learning, normalization, targets = result['learning_counts'], result['normalization_counts'], result['target_counts']
    assert learning['table_lookups']==64*7 and learning['table_update_occurrences']==32*7
    assert learning['reward_table_lookups']==learning['win_table_lookups']==32*7
    assert learning['reward_table_updates']==learning['win_parameter_updates']==writes
    assert learning['table_updates']==2*writes
    assert normalization['feature_extractions']==7 and normalization['feature_occurrences']==32*7
    assert normalization['reward_gradient_products']==normalization['win_gradient_products']==products
    assert normalization['normalization_divisions']==normalization['parameter_update_multiplications']==2*writes
    assert normalization['reward_game_commits']==normalization['win_game_commits']==3
    assert targets==dict(terminal_game_labels=3, win_label_assignments=7,
        reward_suffix_target_assignments=8, reward_suffix_additions=8, goal_checks=8, skipped_winning_afterstates=1)
    assert result['representation_counts']==dict(linear_win_table_lookups=32*7,
        combined_value_additions=2*7, combined_value_multiplications=7)


@pytest.mark.parametrize('games', [1, 2, 3])
def test_two_active_tables_recover_scalar_episode_mc_effective_weights_for_each_prefix(games):
    source = template(); linear = LinearWinLeaf(source, BUILD); scalar = QueryTD(source.parent, 'PRIOR', BUILD)
    dataset = data(); dataset['fit_game_count']=games; dataset['fit_step_end']=int(dataset['ends'][games-1])
    left = fit_linear(linear, dataset, BUILD)
    right = fit_consolidated(scalar, dataset, 'EPISODE_MEAN_MC', BUILD)
    effective = linear.reward_weights+8.*linear.win_weights-4./32.
    # Separate double-precision reductions need not be bitwise identical to one table.
    np.testing.assert_allclose(effective, scalar.weights, rtol=0., atol=1e-15)
    assert left['trained_afterstates']==right['trained_afterstates']
    assert left['learning_counts']['table_updates']==2*right['learning_counts']['table_updates']
    assert left['learning_counts']['reward_table_updates']==right['learning_counts']['table_updates']
    assert left['normalization_counts']['feature_extractions']==right['consolidation_counts']['feature_extractions']
    assert left['normalization_counts']['win_gradient_products']==right['consolidation_counts']['weighted_residual_multiplications']
    assert source.updates==source.parent.source.updates==0


def test_terminal_supervision_changes_only_win_head_and_that_head_is_unclipped_and_used_by_h2():
    source = template(); actual, reference = LinearWinLeaf(source, BUILD), LinearWinLeaf(source, BUILD)
    first, second = data(), data(); second['terminal_codes'][:3]*=-1
    left, right = fit_linear(actual, first, BUILD), fit_linear(reference, second, BUILD)
    np.testing.assert_array_equal(actual.reward_weights, reference.reward_weights)
    assert np.any(actual.win_weights!=reference.win_weights)
    assert left['first_sample']['win_target']==0. and right['first_sample']['win_target']==1.
    baseline, unbounded = LinearWinLeaf(source, BUILD), LinearWinLeaf(source, BUILD)
    unbounded.win_weights[:]=1/16
    board = [1, 1]+[0]*14
    base_components, components = predict_components(baseline, board), predict_components(unbounded, board)
    assert components['win_prediction']==2.
    assert components['combined_prediction']-base_components['combined_prediction']==pytest.approx(12.)
    original, changed = baseline.choose(board, .43), unbounded.choose(board, .43)
    for action, value in original['action_values'].items():
        assert changed['action_values'][action]['value']-value['value']==pytest.approx(12.)
    assert changed['representation_counts']['linear_win_table_lookups']==32*changed['counts']['value_predictions']


def test_current_rewards_and_heldout_rows_do_not_enter_fit_and_win_mse_stays_factual():
    source = template(); actual, reference = LinearWinLeaf(source, BUILD), LinearWinLeaf(source, BUILD)
    first, second = data(), deepcopy(data())
    second['rewards'][[0, 3, 5]]+=100.
    second['afterstates'][8:]=0; second['rewards'][8:]=100.; second['terminal_codes'][3]=-1
    left, right = fit_linear(actual, first, BUILD), fit_linear(reference, second, BUILD)
    np.testing.assert_array_equal(actual.reward_weights, reference.reward_weights)
    np.testing.assert_array_equal(actual.win_weights, reference.win_weights)
    assert left['first_sample']==right['first_sample'] and left['last_sample']==right['last_sample']
    actual.freeze(); reward, win, updates = actual.reward_weights.copy(), actual.win_weights.copy(), actual.updates
    scored = score_linear(actual, first, BUILD); component = scored['component_game_metrics'][0]
    r, w, u = literal_prediction(actual, first['afterstates'][8])
    assert component['win_mse']==pytest.approx((w-1.)**2)
    assert component['reward_mse']==pytest.approx((r-16/2048.)**2)
    assert scored['game_metrics'][0]['mse']==pytest.approx((u-4.-16/2048.)**2)
    assert set(component)=={'episode', 'start', 'end', 'count', 'reward_bias', 'reward_mse',
                           'reward_mae', 'win_mse', 'win_bias', 'mean_win_prediction', 'win_label'}
    assert scored['prediction_counts'].get('table_updates', 0)==0
    np.testing.assert_array_equal(actual.reward_weights, reward); np.testing.assert_array_equal(actual.win_weights, win)
    assert actual.updates==updates


def test_native_natural_evaluation_matches_initial_source_and_preserves_both_fitted_heads():
    source = template(); leaf = LinearWinLeaf(source, BUILD); leaf.freeze()
    engine = NativeValueStream(source, 3111234, BUILD)
    try:
        before = engine.state()
        expected = engine.evaluate_games(source, .43, .5, [311001, 311002], max_steps=128)
        actual = evaluate_linear(leaf, .43, .5, [311001, 311002], BUILD, max_steps=128)
        assert actual['game_summaries']==expected['game_summaries'] and actual['counts']==expected['counts']
        assert engine.state()==before and leaf.updates==0
    finally:
        engine.close()
    trained = LinearWinLeaf(source, BUILD); fit_linear(trained, data(), BUILD); trained.freeze()
    reward, win, updates = trained.reward_weights.copy(), trained.win_weights.copy(), trained.updates
    result = evaluate_linear(trained, .43, .5, [311003, 311004], BUILD)
    assert [game['seed'] for game in result['game_summaries']]==[311003, 311004]
    assert all(game['status'] in ('WON', 'LOST') for game in result['game_summaries'])
    assert result['representation_counts']['linear_win_table_lookups']==32*result['counts']['planning']['value_predictions']
    np.testing.assert_array_equal(trained.reward_weights, reward); np.testing.assert_array_equal(trained.win_weights, win)
    assert trained.updates==updates and result['cpu_seconds']>=0.
    with pytest.raises(ValueError, match='writable'):
        fit_linear(trained, data(), BUILD)
