"""The short target follows the paid DIRECT prefix and bootstraps before the final spawn."""
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
from acfqp.science.native_query_supervision_v319 import supervise
from acfqp.science.native_reward_targets_v321 import acquire_rewards, TRACE_COLUMNS
from acfqp.science.native_split_risk_v301 import SplitLeaf, predict_components

BUILD = Path(__file__).resolve().parents[1] / 'reports/reward_targets_v321/runtime/tests/native'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
BOARD = (1, 2, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0)
LOST_ROOT = (2, 3, 2, 3, 3, 2, 3, 2, 2, 3, 2, 3, 3, 2, 3, 0)


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


def run(first, roots, cells, ranks, actions, kinds, seeds, name, horizon=4, p_true=.375):
    return acquire_rewards(first, np.asarray(roots, dtype=np.int32),
        np.asarray(cells, dtype=np.int32), np.asarray(ranks, dtype=np.int32),
        np.asarray(actions, dtype=np.int32), np.asarray(kinds, dtype=np.int32),
        np.asarray(seeds, dtype=np.uint64), BUILD, BUILD / f'{name}.npz',
        p_model=.375, p_true=p_true, horizon=horizon)


def trace(receipt):
    with np.load(receipt['trace_artifact']['file']) as source:
        return source['moves'].copy()


def test_horizon_one_exactly_reproduces_saved_v319_reward_labels_including_win_and_loss():
    first = fixture()
    roots = np.asarray([BOARD, (3, 3, 0, 0)+(0,)*12, LOST_ROOT], dtype=np.int32)
    old = supervise(first, roots, .375, 319200004, BUILD)
    result = run(first, roots, old['spawn_cells'], old['spawn_ranks'],
        old['selected_action'], old['targetkind'], np.arange(321100000, 321100012).reshape(3, 4),
        'h1', horizon=1)
    np.testing.assert_array_equal(result['target_reward'], old['targetreward'])
    np.testing.assert_array_equal(result['status'], np.where(old['targetkind']==2, 1,
        np.where(old['targetkind']==3, -1, 0)))
    assert result['new_raw_tiles'].sum() == 0
    assert result['environment_counts'].get('environment_random_draws', 0) == 0
    assert result['planning_counts']['choose_calls'] == 0
    assert result['counts']['reused_start_spawns'] == 12
    assert result['counts']['reward_bootstrap_predictions'] == 4
    assert 'targetwin' not in result and 'win' not in result
    rows = trace(result)
    assert rows.shape == (8, 9) and np.all(rows[:, 5:7] == -1)
    assert result['trace_artifact']['columns'] == list(TRACE_COLUMNS)


def test_direct_win_has_zero_new_rng_and_no_terminal_spawn_or_bootstrap_reward():
    first = fixture(); root = (3, 3, 0, 0)+(0,)*12
    action = ACTIONS.index('LEFT')
    result = run(first, [root], [[2]], [[1]], [[action]], [[2]], [[321200001]], 'goal')
    after, gained, legal = swipe((3, 3, 1)+(0,)*13, action)
    assert legal and gained == 16
    assert result['scores'].tolist() == [[16]] and result['target_reward'].tolist() == [[16/2048.]]
    assert result['status'].tolist() == [[1]] and result['actions'].tolist() == [[1]]
    assert result['new_raw_tiles'].tolist() == result['tail_reward'].tolist() == [[0]]
    assert result['final_boards'].tolist() == result['last_afterstates'].tolist() == [[list(after)]]
    assert np.all(result['bootstrap_afterstates'] == 0)
    assert trace(result).tolist() == [[0, 0, 1, action, 16, -1, -1, 1, 1]]
    assert result['environment_counts'].get('raw_tile_productions', 0) == 0
    assert result['environment_counts'].get('environment_random_draws', 0) == 0


def test_initial_lost_has_no_actions_and_keeps_the_paid_postspawn_board():
    first = fixture(); result = run(first, [LOST_ROOT], [[15]], [[2]], [[-1]], [[3]], [[321200002]], 'lost')
    post = list(LOST_ROOT); post[15] = 2
    assert result['status'].tolist() == [[-1]]
    assert all(result[key].tolist() == [[0]] for key in ('scores', 'actions', 'new_raw_tiles', 'tail_reward', 'target_reward'))
    assert all(result[key].tolist() == [[post]] for key in ('final_boards', 'last_preboards', 'last_afterstates'))
    assert np.all(result['bootstrap_afterstates'] == 0) and trace(result).shape == (0, 9)
    assert result['counts']['terminal_losses'] == 1 and result['counts']['reused_start_spawns'] == 1


def test_natural_lost_after_intermediate_spawn_has_reward_prefix_and_no_bootstrap():
    first = fixture()
    root = (1, 1, 3, 2, 3, 2, 3, 2, 2, 3, 2, 3, 3, 2, 3, 0)
    action = ACTIONS.index('LEFT')
    result = run(first, [root], [[15]], [[2]], [[action]], [[1]], [[321200003]], 'early_lost', p_true=0.)
    post = list(root); post[15] = 2; after, gained, legal = swipe(post, action)
    assert legal and gained == 4
    final = list(after); final[3] = 1; assert status(final, first.radix) == -1
    assert result['status'].tolist() == [[-1]] and result['actions'].tolist() == [[1]]
    assert result['target_reward'].tolist() == [[4/2048.]] and result['tail_reward'].tolist() == [[0.]]
    assert result['final_boards'].tolist() == [[final]]
    assert result['last_preboards'].tolist() == [[post]] and result['last_afterstates'].tolist() == [[list(after)]]
    assert np.all(result['bootstrap_afterstates'] == 0)
    assert trace(result).tolist() == [[0, 0, 1, action, 4, 3, 1, -1, -1]]
    assert result['environment_counts']['raw_tile_productions'] == 1
    assert result['environment_counts']['environment_random_draws'] == 2


def test_h4_literal_world_rng_h2_last_afterstate_tail_and_boundary_probes():
    first = fixture(); post = list(BOARD); post[15] = 2
    action = ACTIONS.index(choose_direct(first, post, BUILD)['action'])
    seeds = np.arange(321300000, 321300008, dtype=np.uint64).reshape(2, 4)
    roots = [BOARD, BOARD]
    before = [first.reward_weights.copy(), first.risk_weights.copy()]
    result = run(first, roots, [[15]*4]*2, [[2]*4]*2, [[action]*4]*2, [[1]*4]*2, seeds, 'h4')
    rows = trace(result); probes = result['boundary_probes']; raw_total = 0
    for group in range(2):
        for member in range(4):
            board = post.copy(); total_score = 0; raw = 0; decisions = []
            random = uniforms(first, int(seeds[group, member]), 3)
            expected_rows = []; tail = 0.; bootstrap = [0]*16
            for step in range(1, 5):
                chosen_action = action
                if step > 1:
                    chosen = first.choose(board, .375); chosen_action = ACTIONS.index(chosen['action'])
                    decisions.append(dict(step=step, preboard=board.copy(), chosen=chosen))
                pre = board.copy(); after, gained, legal = swipe(board, chosen_action); assert legal
                last_after = list(after); board = list(after); total_score += gained
                current = status(board, first.radix); cell = rank = -1
                if not current and step == 4:
                    tail = predict_components(first, board)['reward_prediction']; bootstrap = board.copy()
                elif not current:
                    u, v = random[raw]; empty = [i for i, value in enumerate(board) if not value]
                    cell, rank = empty[int(u*len(empty))], 1 if v < .625 else 2
                    board[cell] = rank; raw += 1; current = status(board, first.radix)
                endpoint = current if current else 2 if step == 4 else 0
                expected_rows.append([group, member, step, chosen_action, gained, cell, rank, current, endpoint])
                if current or step == 4:
                    break
            actual_rows = rows[(rows[:, 0]==group) & (rows[:, 1]==member)]
            assert actual_rows.tolist() == expected_rows
            assert result['scores'][group, member] == total_score
            assert result['actions'][group, member] == step
            assert result['new_raw_tiles'][group, member] == raw
            assert result['status'][group, member] == current
            assert result['tail_reward'][group, member] == tail
            assert result['target_reward'][group, member] == total_score/2048.+tail
            assert result['last_preboards'][group, member].tolist() == pre
            assert result['last_afterstates'][group, member].tolist() == last_after
            assert result['bootstrap_afterstates'][group, member].tolist() == bootstrap
            assert result['final_boards'][group, member].tolist() == board
            for key, expected in (('first_h2_decision', decisions[0]), ('last_h2_decision', decisions[-1])):
                probe = probes[group*4+member][key]; chosen = expected['chosen']
                assert probe['step'] == expected['step'] and probe['preboard'] == expected['preboard']
                assert probe['chosen_action'] == chosen['action'] and probe['chosen_afterstate'] == chosen['afterstate']
                assert probe['chosen_h2_value'] == chosen['value'] and probe['action_values'] == chosen['action_values']
            raw_total += raw
    assert result['counts']['h2_choose_calls'] == int(result['actions'].sum())-8
    assert result['environment_counts']['raw_tile_productions'] == raw_total
    assert result['environment_counts']['environment_random_draws'] == 2*raw_total
    assert result['environment_counts']['sampled_transitions'] == int(result['actions'].sum())
    assert result['counts']['reward_bootstrap_table_lookups'] == 32*int(np.count_nonzero(result['status']==0))
    assert result['trace_artifact']['uncompressed_bytes'] == len(rows)*36
    for current_weights, saved in zip((first.reward_weights, first.risk_weights), before):
        np.testing.assert_array_equal(current_weights, saved); assert not current_weights.flags.writeable
    assert first.updates == 7


def test_saved_direct_is_not_reselected_and_horizon_one_does_not_charge_start_spawn():
    first = fixture(); post = list(BOARD); post[15] = 2
    chosen = ACTIONS.index(choose_direct(first, post, BUILD)['action'])
    prescribed = next(a for a in range(4) if a != chosen and swipe(post, a)[2])
    result = run(first, [BOARD], [[15]], [[2]], [[prescribed]], [[1]], [[321300020]], 'prescribed', horizon=1)
    after, score, legal = swipe(post, prescribed); assert legal
    assert trace(result)[0, 3] == prescribed
    assert result['target_reward'][0, 0] == score/2048.+predict_components(first, after)['reward_prediction']
    assert result['new_raw_tiles'][0, 0] == 0 and result['planning_counts']['choose_calls'] == 0
    assert result['status'][0, 0] == 0 and result['status_codes']['BOOTSTRAPPED'] == 0


def test_boundary_probe_selection_is_first_eight_and_last_eight_rollouts():
    first = fixture(); root = (3, 3, 0, 0)+(0,)*12
    result = run(first, [root]*5, [[2]*4]*5, [[1]*4]*5, [[ACTIONS.index('LEFT')]*4]*5,
        [[2]*4]*5, np.arange(321400000, 321400020).reshape(5, 4), 'boundary_indices')
    assert [p['root_local_index']*4+p['member'] for p in result['boundary_probes']] == [*range(8), *range(12, 20)]
    assert all(p['first_h2_decision'] is None and p['last_h2_decision'] is None for p in result['boundary_probes'])


def test_readonly_teacher_and_saved_targetkind_are_required():
    first = fixture(); first.reward_weights.flags.writeable = True
    with pytest.raises(ValueError, match='frozen FIRST'):
        run(first, [BOARD], [[15]], [[2]], [[1]], [[1]], [[321300021]], 'writable')
    first.freeze()
    with pytest.raises(ValueError, match='native code 8'):
        run(first, [(3, 3, 0, 0)+(0,)*12], [[2]], [[1]], [[ACTIONS.index('LEFT')]], [[1]], [[321300022]], 'wrong_kind')
