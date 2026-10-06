"""The saved target branch and every newly paid spawn preserve actual world order."""
import ctypes
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue, ACTIONS
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_policy_stream_v313 import choose_direct
from acfqp.science.native_split_risk_v301 import SplitLeaf
from acfqp.science.native_teacher_calibration_v320 import continue_targets, TRACE_COLUMNS

BUILD = Path(__file__).resolve().parents[1] / 'reports/teacher_calibration_v320/runtime/tests/native'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
BOARD = (1, 2, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def fixture():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    template = QueryTD(QueryParent(NtupleValue(rule, BUILD), QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze(); first = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    index = np.arange(first.reward_weights.size).reshape(first.reward_weights.shape)
    first.reward_weights[:] = (index % 7) * .003
    first.risk_weights[:] = -(index % 5) * .01
    first.updates = 7; first.freeze()
    return first


def uniforms(first, seed, n):
    output = np.empty((n, 2)); function = first.library.native_common_draws_v285
    function.argtypes = [ctypes.c_uint64, ctypes.c_int,
        np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')]
    function.restype = None; function(seed, n, output)
    return output


def swipe(board, action):
    return ground.swipe_board_v1(tuple(map(int, board)), ground.Swipe2048Action(ACTIONS[action]))


def status(board, goal):
    return 1 if max(board) >= goal else 0 if any(swipe(board, action)[2] for action in range(4)) else -1


def run(first, roots, cells, ranks, actions, kinds, seeds, name, max_steps=8192):
    return continue_targets(first, np.asarray(roots, dtype=np.int32),
        np.asarray(cells, dtype=np.int32), np.asarray(ranks, dtype=np.int32),
        np.asarray(actions, dtype=np.int32), np.asarray(kinds, dtype=np.int32),
        np.asarray(seeds, dtype=np.uint64), BUILD, BUILD / f'{name}.npz',
        p_model=.375, p_true=.375, max_steps=max_steps)


def trace(receipt):
    with np.load(receipt['trace_artifact']['file']) as source:
        return source['moves'].copy()


def test_saved_goal_branch_spawns_after_win_with_fresh_first_rng_draw_and_no_origin_reward():
    first = fixture(); seed = 320500003
    root = (3, 3, 0, 0) + (0,) * 12
    result = run(first, [root], [[2]], [[1]], [[1]], [[2]], [[seed]], 'goal')
    after, gained, legal = swipe((*root[:2], 1, *root[3:]), 1)
    assert legal and gained == 16
    u, v = uniforms(first, seed, 1)[0]
    empties = [cell for cell, rank in enumerate(after) if not rank]
    cell, rank = empties[int(u * len(empties))], 1 if v < .625 else 2
    final = list(after); final[cell] = rank
    assert result['scores'].tolist() == [[16]]
    assert result['status'].tolist() == [[1]]
    assert result['actions'].tolist() == result['new_raw_tiles'].tolist() == [[1]]
    assert result['final_boards'].tolist() == [[final]]
    assert result['utility'][0, 0] == 16 / 2048. + 4.
    assert result['environment_counts']['raw_tile_productions'] == 1
    assert result['environment_counts']['environment_random_draws'] == 2
    assert result['counts']['reused_start_spawns'] == 1 and result['counts']['prescribed_direct_actions'] == 1
    assert result['planning_counts']['choose_calls'] == 0
    assert result['boundary_probes'] == [dict(root_local_index=0, member=0, first_h2_decision=None, last_h2_decision=None)]
    assert trace(result).tolist() == [[0, 0, 1, 1, 16, cell, rank, 1]]
    assert result['trace_artifact']['columns'] == list(TRACE_COLUMNS)
    assert result['trace_artifact']['uncompressed_bytes'] == 32


def test_saved_lost_start_is_natural_terminal_without_an_action_new_spawn_or_rng_draw():
    first = fixture()
    root = (2, 3, 2, 3, 3, 2, 3, 2, 2, 3, 2, 3, 3, 2, 3, 0)
    result = run(first, [root], [[15]], [[2]], [[-1]], [[3]], [[320500004]], 'lost')
    assert result['status'].tolist() == [[-1]]
    assert result['scores'].tolist() == result['actions'].tolist() == result['new_raw_tiles'].tolist() == [[0]]
    assert result['utility'].tolist() == [[-4.]]
    assert result['counts']['reused_start_spawns'] == result['counts']['terminal_losses'] == 1
    assert result['environment_counts'].get('raw_tile_productions', 0) == 0
    assert result['environment_counts'].get('environment_random_draws', 0) == 0
    assert trace(result).shape == (0, 8)


def test_cutoff_total_action_count_includes_direct_and_never_assigns_a_terminal_utility():
    first = fixture(); post = list(BOARD); post[15] = 2
    chosen = choose_direct(first, post, BUILD); action = ACTIONS.index(chosen['action'])
    result = run(first, [BOARD], [[15]], [[2]], [[action]], [[1]], [[320500005]], 'cutoff', max_steps=1)
    assert result['status'].tolist() == [[0]] and result['counts']['action_cutoffs'] == 1
    assert result['actions'].tolist() == result['new_raw_tiles'].tolist() == [[1]]
    assert all(np.isnan(result[key][0, 0]) for key in ('reward_return', 'win', 'utility'))
    assert trace(result)[-1, -1] == 0 and result['planning_counts']['choose_calls'] == 0


def test_full_continuation_literal_world_rng_frozen_h2_and_boundary_probes():
    first = fixture(); post = list(BOARD); post[15] = 2
    direct = choose_direct(first, post, BUILD); action = ACTIONS.index(direct['action'])
    saved = [first.reward_weights.copy(), first.risk_weights.copy()]
    seeds = np.asarray([[320500006, 320500007]], dtype=np.uint64)
    result = run(first, [BOARD], [[15, 15]], [[2, 2]], [[action, action]], [[1, 1]], seeds, 'natural')
    rows = trace(result); probes = result['boundary_probes']; total_new = 0
    for member, seed in enumerate(seeds[0]):
        member_rows = rows[rows[:, 1] == member]
        random = uniforms(first, int(seed), len(member_rows))
        board = post.copy(); total_score = 0; decisions = []
        for step, (row, (u, v)) in enumerate(zip(member_rows, random), 1):
            expected_action = action
            if step > 1:
                chosen = first.choose(board, .375); expected_action = ACTIONS.index(chosen['action'])
                decisions.append(dict(step=step, preboard=board.copy(), chosen=chosen))
            assert row[:4].tolist() == [0, member, step, expected_action]
            after, gained, legal = swipe(board, expected_action); assert legal
            empty = [cell for cell, rank in enumerate(after) if not rank]
            cell, rank = empty[int(u*len(empty))], 1 if v < .625 else 2
            board = list(after); board[cell] = rank; total_score += gained
            assert row[4:].tolist() == [gained, cell, rank, status(board, first.radix)]
        assert result['scores'][0, member] == total_score
        assert result['actions'][0, member] == result['new_raw_tiles'][0, member] == len(member_rows)
        assert result['status'][0, member] == status(board, first.radix) != 0
        assert result['final_boards'][0, member].tolist() == board
        assert len(decisions) > 1
        for key, expected in (('first_h2_decision', decisions[0]), ('last_h2_decision', decisions[-1])):
            probe = probes[member][key]; chosen = expected['chosen']
            assert probe['step'] == expected['step'] and probe['preboard'] == expected['preboard']
            assert probe['chosen_action'] == chosen['action'] and probe['chosen_afterstate'] == chosen['afterstate']
            assert probe['chosen_h2_value'] == chosen['value'] and probe['action_values'] == chosen['action_values']
        total_new += len(member_rows)
    assert result['counts']['h2_choose_calls'] == total_new-2
    assert result['environment_counts']['raw_tile_productions'] == total_new
    assert result['environment_counts']['environment_random_draws'] == 2*total_new
    assert result['environment_counts']['sampled_transitions'] == total_new
    for current, before in zip((first.reward_weights, first.risk_weights), saved):
        np.testing.assert_array_equal(current, before); assert not current.flags.writeable
    assert first.updates == 7


def test_paired_seeds_preserve_rng_prefixes_across_different_roots_and_probe_bounds():
    first = fixture(); roots = [(3, 3, 0, 0)+(0,)*12, (3, 3, 1, 0, 2)+(0,)*11]
    cells, ranks, actions, kinds = [[3]*4]*2, [[1]*4]*2, [[1]*4]*2, [[2]*4]*2
    seeds = np.arange(320510000, 320510004, dtype=np.uint64).reshape(1, 4)
    result = run(first, roots, cells, ranks, actions, kinds, np.repeat(seeds, 2, axis=0), 'paired')
    rows = trace(result)
    assert rows[:, 6].reshape(2, 4)[0].tolist() == rows[:, 6].reshape(2, 4)[1].tolist()
    assert len(result['boundary_probes']) == 8
    for group, root in enumerate(roots):
        for member, seed in enumerate(seeds[0]):
            board = list(root); board[3] = 1; after, _, _ = swipe(board, 1)
            u, _ = uniforms(first, int(seed), 1)[0]
            empty = [cell for cell, rank in enumerate(after) if not rank]
            assert rows[group*4+member, 5] == empty[int(u*len(empty))]


def test_prescribed_direct_action_is_not_reselected_and_probes_have_frozen_boundary_count():
    first = fixture(); post = list(BOARD); post[15] = 2
    chosen = ACTIONS.index(choose_direct(first, post, BUILD)['action'])
    prescribed = next(action for action in range(4) if action != chosen and swipe(post, action)[2])
    result = run(first, [BOARD], [[15]], [[2]], [[prescribed]], [[1]], [[320500010]], 'prescribed', max_steps=1)
    assert trace(result)[0, 3] == prescribed
    roots = [(3, 3, 0, 0)+(0,)*12] * 5
    boundary = run(first, roots, [[2]*4]*5, [[1]*4]*5, [[1]*4]*5, [[2]*4]*5,
        np.arange(320600000, 320600020, dtype=np.uint64).reshape(5, 4), 'boundaries')
    assert [(p['root_local_index']*4+p['member']) for p in boundary['boundary_probes']] == [*range(8), *range(12, 20)]


def test_sampling_requires_readonly_teacher_and_rejects_inconsistent_saved_target_kind():
    first = fixture(); first.risk_weights.flags.writeable = True
    with pytest.raises(ValueError, match='frozen FIRST'):
        run(first, [BOARD], [[15]], [[2]], [[1]], [[1]], [[320500008]], 'writable')
    first.freeze()
    with pytest.raises(ValueError, match='native code 8'):
        run(first, [(3, 3, 0, 0)+(0,)*12], [[2]], [[1]], [[1]], [[1]], [[320500009]], 'wrong_kind')
