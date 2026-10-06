"""Finite native executions against independent Python ground and V135."""
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import native_continuation_v285 as core
from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1]/'reports/natural_continuation_v285/runtime/tests'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
SPARSE = [1, 0, 0, 0, 0, 1]+[0]*10
GOAL = [3, 3]+[0]*14
LOSS_BRANCH = [2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1, 2, 1, 1, 1]


@pytest.fixture(scope='module')
def leaf():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11*.001
    model = QueryTD(QueryParent(source, QUERY, QUERY, .5), 'PRIOR', BUILD)
    model.freeze()
    return model


def python_reference(leaf, board, first_action, p_four, draws):
    """Ground merge/status are independent of the leaf's learned lookup table."""
    planner = FrozenLeafPlanner(leaf, depth=2, build_dir=BUILD)
    planner.spawn_probabilities = 1.-p_four, p_four
    board, total_score, first_score, status = tuple(board), 0, 0, 'ACTIVE'
    counts = Counter()
    for step, (cell_draw, rank_draw) in enumerate(draws):
        selected = first_action if step == 0 else planner.choose(board)['action']
        after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(selected))
        assert changed
        empty = [cell for cell, rank in enumerate(after) if not rank]
        child = list(after)
        child[empty[int(cell_draw*len(empty))]] = 1 if rank_draw < 1.-p_four else 2
        board = tuple(child)
        total_score += score
        if step == 0:
            first_score = score
        counts.update(sampled_transitions=1, environment_random_draws=2,
            ground_explicit_swipe_calls=1, ground_swipe_calls=1, ground_state_status_calls=1)
        # The finite fixture uses a lower goal to exercise true termination cheaply.
        if max(board) >= leaf.radix:
            status = 'WON'
        else:
            counts.update(ground_status_internal_swipe_calls=4, ground_swipe_calls=4)
            if not ground.legal_actions_v1(board):
                status = 'LOST'
        if status != 'ACTIVE':
            break
    if status == 'ACTIVE':
        status = 'CUTOFF'
    bonus = 4. if status == 'WON' else -4. if status == 'LOST' else 0.
    result = dict(first_score=first_score, total_score=total_score, steps=step+1,
        suffix_utility=(total_score-first_score)/2048.+bonus,
        total_utility=total_score/2048.+bonus, status=status, final_board=list(board))
    planning = {key: value for key, value in planner.counts.items() if key != 'choose_calls' and value}
    return result, counts, planning


@pytest.mark.parametrize('p_four', [0., .1, .37, .5, 1.])
def test_one_native_call_matches_ground_and_original_h2_for_all_paired_branches(leaf, p_four):
    engine = core.NativeContinuation(leaf, BUILD)
    actions, seeds, horizon = ['DOWN', 'LEFT', 'RIGHT', 'UP'], [17, 23, 29], 6
    before, updates = leaf.weights.copy(), leaf.updates
    actual = engine.evaluate(SPARSE, actions, p_four, seeds, horizon)
    expected_environment, expected_planning = Counter(), Counter()
    for index, result in enumerate(actual['rollouts']):
        action, replica = divmod(index, len(seeds))
        expected, environment, planning = python_reference(leaf, SPARSE, actions[action],
            p_four, engine.common_draws(seeds[replica], horizon))
        assert result == dict(expected, action=actions[action], replica_index=replica, seed=seeds[replica])
        expected_environment.update(environment)
        expected_planning.update(planning)
    assert actual['counts']['environment'] == dict(expected_environment)
    assert actual['counts']['planning'] == dict(expected_planning)
    assert actual['counts']['rollout']['completed_rollouts'] == 12
    assert actual['counts']['rollout']['replica_streams'] == 3
    assert actual['counts']['rollout']['continuation_choose_calls'] == sum(r['steps']-1 for r in actual['rollouts'])
    np.testing.assert_array_equal(leaf.weights, before)
    assert not leaf.weights.flags.writeable and leaf.updates == updates == 0


def test_goal_still_spawns_and_suffix_excludes_first_score(leaf):
    engine = core.NativeContinuation(leaf, BUILD)
    result = engine.evaluate(GOAL, ['LEFT'], .5, [3])
    row, counts = result['rollouts'][0], result['counts']
    assert row['status'] == 'WON' and row['steps'] == 1
    assert row['first_score'] == row['total_score'] == 16
    assert row['suffix_utility'] == 4. and row['total_utility'] == 4.+16/2048.
    assert sum(rank != 0 for rank in row['final_board']) == 2
    assert counts['environment']['sampled_transitions'] == 1
    assert counts['environment']['environment_random_draws'] == 2
    assert counts['environment']['ground_swipe_calls'] == 1
    assert counts['planning'] == {} and 'continuation_choose_calls' not in counts['rollout']


def test_terminal_loss_uses_true_ground_and_counts_penalty_once(leaf):
    engine = core.NativeContinuation(leaf, BUILD)
    selected = None
    for action in ground.legal_actions_v1(tuple(LOSS_BRANCH)):
        after, _, _ = ground.swipe_board_v1(tuple(LOSS_BRANCH), action)
        empty = [cell for cell, rank in enumerate(after) if not rank]
        for index, cell in enumerate(empty):
            for rank in (1, 2):
                child = list(after)
                child[cell] = rank
                if max(child) < leaf.radix and not ground.legal_actions_v1(tuple(child)):
                    selected = action.value, len(empty), index, float(rank == 2)
                    break
            if selected:
                break
        if selected:
            break
    assert selected is not None
    action, n, position, p_four = selected
    seed = next(seed for seed in range(100) if int(engine.common_draws(seed, 1)[0, 0]*n) == position)
    result = engine.evaluate(LOSS_BRANCH, [action], p_four, [seed])
    row = result['rollouts'][0]
    assert row['status'] == 'LOST' and row['steps'] == 1
    assert row['suffix_utility'] == -4.
    assert row['total_utility'] == row['first_score']/2048.-4.
    assert result['counts']['environment']['ground_state_status_calls'] == 1
    assert result['counts']['planning'] == {}


def test_cutoff_counts_forced_first_action_and_stream_readout_is_not_feedback(leaf):
    engine = core.NativeContinuation(leaf, BUILD)
    before = {key: value.copy() for key, value in engine.counts.items()}
    first = engine.common_draws(28500001, 8)
    assert engine.counts == before
    np.testing.assert_array_equal(first, engine.common_draws(28500001, 8))
    assert np.all((first >= 0.) & (first < 1.))
    assert not np.array_equal(first, engine.common_draws(28500002, 8))
    result = engine.evaluate(SPARSE, ['LEFT', 'RIGHT'], .1, [28500001], 1)
    assert all(row['status'] == 'CUTOFF' and row['steps'] == 1 for row in result['rollouts'])
    assert all(row['suffix_utility'] == 0. for row in result['rollouts'])
    assert result['counts']['environment']['sampled_transitions'] == 2
    assert result['counts']['environment']['environment_random_draws'] == 4
    assert result['counts']['rollout']['rng_streams_started'] == 2
    assert result['counts']['rollout']['replica_streams'] == 1
    assert result['counts']['planning'] == {}
