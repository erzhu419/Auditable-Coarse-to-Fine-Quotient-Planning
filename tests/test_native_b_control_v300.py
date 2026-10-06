"""Finite target-only interventions against V135 and literal V290 addresses."""
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.native_b_control_v300 import fit_control
from acfqp.science.native_episode_consolidation_v290 import fit_consolidated
from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue, ALPHA
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import (
    LearnedDynamics, RewriteProgram)

BUILD = Path(__file__).resolve().parents[1] / 'reports/b_control_v300/runtime/tests'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def make_leaf(offset=False):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    source_query = dict(reward_weight=1., failure_penalty=0., goal_bonus=0.) if offset else QUERY
    return QueryTD(QueryParent(source, source_query, QUERY, .25 if offset else .5), 'PRIOR', BUILD)


def dataset():
    boards = [[2]+[0]*15, [2, 1]+[0]*14,
        [1, 2, 1, 2]*3+[2, 1, 2, 0], [3, 3]+[0]*14,
        [4]+[0]*15, [2]+[0]*15, [2, 1]+[0]*14,
        [3, 3]+[0]*14, [4]+[0]*15]
    return dict(afterstates=np.asarray(boards, dtype=np.int32),
        rewards=np.asarray([4, 8, 0, 8, 16, 0, 4, 8, 16], dtype=np.float64)/2048.,
        ends=np.asarray([3, 5, 7, 9], dtype=np.int64),
        terminal_codes=np.asarray([-1, 1, -1, 1], dtype=np.int32),
        fit_game_count=3, fit_step_end=7)


def literal_target(leaf, after, probability):
    empties = np.flatnonzero(np.asarray(after) == 0)
    target = 0.
    for cell in empties:
        for rank in (1, 2):
            spawned = np.asarray(after).copy()
            spawned[cell] = rank
            value = leaf.choose(spawned)['value']
            target += ((1.-probability if rank == 1 else probability)/len(empties))*value
    return target


def literal_mean(leaf, data, probability, control=True):
    flat = leaf.weights.reshape(-1)
    start, examples, mass = 0, [], []
    for game in range(data['fit_game_count']):
        end = int(data['ends'][game])
        rows = {step: Counter(map(int, leaf.model.feature_indices(data['afterstates'][step])))
            for step in range(start, end) if max(data['afterstates'][step]) < leaf.radix}
        targets = {}
        if control:
            targets = {step: literal_target(leaf, data['afterstates'][step], probability)
                       for step in rows}
        else:
            suffix = 4. if data['terminal_codes'][game] == 1 else -4.
            for step in range(end-1, start-1, -1):
                targets[step] = suffix
                suffix += float(data['rewards'][step])
        denominators = Counter()
        for row in rows.values():
            denominators.update(row)
        errors = {}
        gradients = {address: 0. for address in denominators}
        for step in rows:
            before = leaf.model.value(data['afterstates'][step])
            raw_target = targets[step]-leaf.offset
            errors[step] = raw_target-before
            examples.append(dict(episode=game, step=step, target=targets[step],
                raw_target=raw_target, error=errors[step], raw_prediction_before_update=before))
        for step, row in rows.items():
            for address, count in sorted(row.items()):
                gradients[address] += count*errors[step]
        for address, gradient in gradients.items():
            flat[address] += ALPHA*gradient/denominators[address]
        mass.extend(sum(row.get(address, 0)/count for row in rows.values())
                    for address, count in denominators.items())
        start = end
    return examples, mass


@pytest.mark.parametrize('offset', [False, True])
def test_target_matches_h2_root_tail_and_omits_current_reward(offset):
    actual, reference = make_leaf(offset), make_leaf(offset)
    probability = .4375
    board = [1, 1]+[0]*14
    reference.freeze()
    planner = FrozenLeafPlanner(reference, 2, BUILD)
    planner.spawn_probabilities = (1.-probability, probability)
    root = planner.choose(board)
    row = next(row for row in root['action_values'].values()
               if row['afterstate'] == [2]+[0]*15)
    data = dict(afterstates=np.asarray([[2]+[0]*15], dtype=np.int32),
        rewards=np.asarray([123.], dtype=np.float64), ends=np.asarray([1], dtype=np.int64),
        terminal_codes=np.asarray([-1], dtype=np.int32), fit_game_count=1, fit_step_end=1)
    fitted = fit_control(actual, data, probability, BUILD)
    assert fitted['first_sample']['target'] == row['tail_value']
    assert fitted['first_sample']['raw_target'] == row['tail_value']-actual.offset
    assert fitted['first_sample']['target'] != row['value']
    planning = fitted['planning_counts']
    assert planning['generated_spawn_outcomes'] == planning['leaf_choose_calls'] == 30
    assert planning['spawn_rank1_outcomes'] == planning['spawn_rank2_outcomes'] == 15
    assert planning['learned_swipe_calls'] == planning['second_ply_swipe_calls'] == 120
    assert planning['line_table_lookups'] == 480
    assert planning['table_lookups'] == 32*planning['value_predictions']
    assert planning['spawn_board_cells_copied'] == 16*30
    assert fitted['target_counts'].get('suffix_reward_additions', 0) == 0


@pytest.mark.parametrize('offset', [False, True])
def test_game_snapshot_targets_and_original_multiplicity_normalization(offset):
    actual, reference = make_leaf(offset), make_leaf(offset)
    data = dataset()
    result = fit_control(actual, data, .43, BUILD)
    examples, mass = literal_mean(reference, data, .43)
    np.testing.assert_array_equal(actual.weights, reference.weights)
    assert result['first_sample'] == examples[0]
    assert result['last_sample'] == examples[-1]
    assert all(item == pytest.approx(1., abs=1e-15) for item in mass)
    assert result['trained_afterstates'] == actual.updates == 6
    assert result['learning_counts']['table_update_occurrences'] == 192
    assert result['consolidation_counts']['feature_occurrences'] == 192
    assert result['consolidation_counts']['game_parameter_commits'] == 3
    assert result['consolidation_counts'].get('sample_parameter_commits', 0) == 0
    assert result['target_counts']['skipped_winning_afterstates'] == 1
    assert actual.parent.source.updates == 0


@pytest.mark.parametrize('offset', [False, True])
def test_original_mc_mean_remains_bit_identical_to_literal_kernel(offset):
    actual, reference = make_leaf(offset), make_leaf(offset)
    result = fit_consolidated(actual, dataset(), 'EPISODE_MEAN_MC', BUILD)
    examples, _ = literal_mean(reference, dataset(), .43, control=False)
    np.testing.assert_array_equal(actual.weights, reference.weights)
    assert result['first_sample'] == examples[0]
    assert result['last_sample'] == examples[-1]


def test_future_rewards_heldout_and_terminal_labels_cannot_change_control_fit():
    actual, reference = make_leaf(), make_leaf()
    first, second = dataset(), dataset()
    second['afterstates'][7:] = 0
    second['rewards'][:] += 100.
    second['terminal_codes'][:] *= -1
    left = fit_control(actual, first, .43, BUILD)
    right = fit_control(reference, second, .43, BUILD)
    np.testing.assert_array_equal(actual.weights, reference.weights)
    for key in ('first_sample', 'last_sample', 'learning_counts', 'target_counts',
                'consolidation_counts', 'planning_counts'):
        assert left[key] == right[key]


def test_next_winning_action_reward_and_goal_are_analytic_once_with_offset():
    leaf = make_leaf(True)
    after = [3, 3]+[0]*14
    data = dict(afterstates=np.asarray([after, [4]+[0]*15], dtype=np.int32),
        rewards=np.asarray([99., 88.]), ends=np.asarray([2], dtype=np.int64),
        terminal_codes=np.asarray([1], dtype=np.int32), fit_game_count=1, fit_step_end=2)
    result = fit_control(leaf, data, .43, BUILD)
    assert result['first_sample'] == result['last_sample']
    assert result['first_sample']['target'] == pytest.approx(4.+16/2048., abs=2e-15)
    assert result['first_sample']['raw_target'] == result['first_sample']['target']-leaf.offset
    assert result['trained_afterstates'] == 1
    assert result['target_counts']['skipped_winning_afterstates'] == 1
    assert result['planning_counts']['terminal_goal_bypasses'] > 0


def test_postspawn_loss_uses_analytic_failure_and_zero_probability_branch_is_paid():
    leaf = make_leaf(True)
    after = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 0]
    data = dict(afterstates=np.asarray([after], dtype=np.int32),
        rewards=np.asarray([55.]), ends=np.asarray([1], dtype=np.int64),
        terminal_codes=np.asarray([-1], dtype=np.int32), fit_game_count=1, fit_step_end=1)
    result = fit_control(leaf, data, 0., BUILD)
    assert result['first_sample']['target'] == -4.
    assert result['first_sample']['raw_target'] == -4.-leaf.offset
    assert result['planning_counts']['leaf_terminal_loss_states'] == 1
    assert result['planning_counts']['generated_spawn_outcomes'] == 2
    assert result['planning_counts']['leaf_choose_calls'] == 2
    assert result['planning_counts']['learned_swipe_calls'] == 8
