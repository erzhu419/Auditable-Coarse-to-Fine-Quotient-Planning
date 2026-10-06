"""Actual H2 call pools, independent ground draws and one normalized rootgroup commit."""
from collections import Counter
import ctypes
from fractions import Fraction
import math
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue, ACTIONS
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_policy_stream_v313 import choose_direct
from acfqp.science.native_query_supervision_v319 import query_roots, supervise, fit_supervision
from acfqp.science.native_split_risk_v301 import SplitLeaf, predict_components

BUILD = Path(__file__).resolve().parents[1] / 'reports/query_supervision_v319/runtime/tests/native'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
BOARD = (1, 2, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0)
LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)


def fixture():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    template = QueryTD(QueryParent(NtupleValue(rule, BUILD), QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    first = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    index = np.arange(first.reward_weights.size).reshape(first.reward_weights.shape)
    first.reward_weights[:] = index % 7 * .003
    first.risk_weights[:] = -(index % 5) * .01
    first.updates = 7; first.freeze()
    return template, first


def draws(first, seed, n):
    output = np.empty((n, 2))
    function = first.library.native_common_draws_v285
    function.argtypes = [ctypes.c_uint64, ctypes.c_int,
        np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')]
    function.restype = None
    function(seed, n, output)
    return output


def literal_pool(first, anchor):
    pool = []
    if max(anchor) >= first.radix:
        return pool
    for root_action, name in enumerate(ACTIONS):
        after, _, legal = ground.swipe_board_v1(anchor, ground.Swipe2048Action(name))
        if not legal or max(after) >= first.radix:
            continue
        for cell in range(16):
            if after[cell]:
                continue
            for rank in (1, 2):
                spawned = list(after); spawned[cell] = rank
                if max(spawned) >= first.radix:
                    continue
                for inner_action, inner in enumerate(ACTIONS):
                    result, _, legal = ground.swipe_board_v1(tuple(spawned), ground.Swipe2048Action(inner))
                    if legal and max(result) < first.radix:
                        pool.append((tuple(result), (root_action, cell, rank, inner_action)))
    return pool


def addresses(first, board):
    result = []
    for tuple_index, pattern in enumerate(first.model.patterns.reshape(-1, 6)):
        address = 0
        for cell in pattern:
            address = address * first.radix + int(board[cell])
        result.append((tuple_index // 8) * first.radix ** 6 + address)
    return result


def probability(logit):
    if logit >= 0.:
        return 1. / (1. + math.exp(-logit))
    value = math.exp(logit)
    return value / (1. + value)


def test_query_roots_follow_actual_h2_call_multiplicity_paths_and_one_draw_per_anchor():
    _, first = fixture()
    anchors = np.asarray([BOARD, (4,) + (0,) * 15, LOST, BOARD], dtype=np.int32)
    receipt = query_roots(first, anchors, 319100003, BUILD, p_model=.375)
    uniforms = draws(first, 319100003, 2).reshape(-1)
    planning, representation, total = Counter(), Counter(), 0
    for index, anchor_array in enumerate(anchors):
        anchor = tuple(map(int, anchor_array)); pool = literal_pool(first, anchor); total += len(pool)
        chosen = first.choose(anchor, .375)
        planning.update(chosen['counts']); representation.update(chosen['representation_counts'])
        assert receipt['chosen_actions'][index] == (-2 if chosen['status'] == 'WON' else -1 if chosen['status'] == 'LOST' else ACTIONS.index(chosen['action']))
        assert receipt['chosen_afterstates'][index].tolist() == chosen['afterstate']
        assert bool(receipt['validmask'][index]) == bool(pool)
        if pool:
            ordinal = int(uniforms[index] * len(pool))
            board, path = pool[ordinal]
            assert receipt['root_afterstates'][index].tolist() == list(board)
            assert receipt['provenance'][index].tolist() == [*path, ordinal, len(pool)]
            assert len(set(board for board,_ in pool)) < len(pool)
        else:
            assert receipt['provenance'][index].tolist() == [-1, -1, -1, -1, -1, 0]
    assert receipt['counts']['actual_nonwin_leaf_queries'] == total == planning['value_predictions']
    assert receipt['counts']['pool_board_cells_written'] == 16 * total
    assert receipt['counts']['pool_path_fields_written'] == 4 * total
    assert receipt['counts']['selector_random_draws'] == 4
    assert receipt['planning_counts'] == dict(planning) and receipt['representation_counts'] == dict(representation)
    for probe in receipt['first_probes'] + receipt['last_probes']:
        actual = first.choose(probe['preboard'], .375)
        assert probe['chosen_action'] == actual['action'] and probe['chosen_h2_value'] == actual['value']
        assert probe['action_values'] == actual['action_values']
    assert first.updates == 7


def test_four_ground_spawns_per_root_targets_use_one_coupled_direct_branch_and_terminal_costs():
    _, first = fixture()
    last = [rank + 1 for rank in LOST]; last[-1] = 0
    roots = np.asarray([BOARD, (3, 3, 0, 0) + (0,) * 12, last], dtype=np.int32)
    saved = [first.reward_weights.copy(), first.risk_weights.copy()]
    receipt = supervise(first, roots, .375, 319200004, BUILD)
    random = draws(first, 319200004, 12)
    outcomes, active = [], 0
    for root_index, root in enumerate(roots):
        for replica in range(4):
            u, v = random[4*root_index + replica]
            empty = [cell for cell,rank in enumerate(root) if not rank]
            cell = empty[int(u * len(empty))]; rank = 1 if v < .625 else 2
            board = root.tolist(); board[cell] = rank
            chosen = choose_direct(first, board, BUILD)
            assert receipt['spawn_cells'][root_index, replica] == cell
            assert receipt['spawn_ranks'][root_index, replica] == rank
            if chosen['status'] == 'LOST':
                expected = (0., 0., -1, 3)
            else:
                active += 1
                after, score, legal = ground.swipe_board_v1(tuple(board), ground.Swipe2048Action(chosen['action']))
                assert legal
                if max(after) >= first.radix:
                    expected = (score / 2048., 1., ACTIONS.index(chosen['action']), 2)
                else:
                    prediction = predict_components(first, after)
                    expected = (score / 2048. + prediction['reward_prediction'], prediction['risk_probability'], ACTIONS.index(chosen['action']), 1)
            outcomes.append(expected)
            assert tuple(receipt[key][root_index, replica] for key in ('targetreward', 'targetwin', 'selected_action', 'targetkind')) == expected
    assert receipt['targetkind'][1].tolist() == [2] * 4
    assert set(receipt['spawn_ranks'].reshape(-1)) == {1, 2}
    assert receipt['targetkind'][2].tolist() == [3] * 4
    assert receipt['targetreward'][2].tolist() == receipt['targetwin'][2].tolist() == [0.] * 4
    assert receipt['environment_counts']['raw_tile_productions'] == 12
    assert receipt['environment_counts']['environment_random_draws'] == 24
    assert receipt['environment_counts']['ground_explicit_swipe_calls'] == active
    assert receipt['environment_counts']['sampled_transitions'] == active
    assert receipt['counts']['supervision_start_spawns'] == 12
    assert receipt['counts']['ground_teacher_branch_checks'] == active
    assert receipt['counts']['terminal_lost_targets'] == 4
    for current, before in zip((first.reward_weights, first.risk_weights), saved):
        np.testing.assert_array_equal(current, before)
        assert not current.flags.writeable
    assert first.updates == 7


def test_rootgroup_mean_soft_labels_literal_duplicate_address_normalization_and_replica_noise():
    template, first = fixture()
    learner = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    learner.reward_weights[:] = first.reward_weights; learner.risk_weights[:] = first.risk_weights
    learner.updates = first.updates
    roots = np.asarray([(1,) + (0,) * 15, (1,) + (0,) * 15, BOARD], dtype=np.int32)
    rt = np.asarray([[1., 2., 3., 4.], [.2, .4, .6, .8], [-1., 0., 1., 2.]])
    pt = np.asarray([[0., .25, .75, 1.], [.1, .2, .3, .4], [.2, .2, .6, 1.]])
    expected_r, expected_p = learner.reward_weights.reshape(-1).copy(), learner.risk_weights.reshape(-1).copy()
    uniques = 0
    for root_index, root in enumerate(roots):
        row = addresses(learner, root); counts = Counter(row); uniques += len(counts)
        assert len(counts) < 32
        reward_mean, win_mean = sum(rt[root_index]) / 4., sum(pt[root_index]) / 4.
        rp = sum(float(expected_r[address]) for address in row)
        pp = probability(sum(float(expected_p[address]) for address in row))
        for address, multiplicity in sorted(counts.items()):
            expected_r[address] += .0025 * (multiplicity * (reward_mean-rp)) / multiplicity
            expected_p[address] += .0025 * (multiplicity * (win_mean-pp)) / multiplicity
    receipt = fit_supervision(learner, roots, rt, pt, BUILD)
    np.testing.assert_allclose(learner.reward_weights.reshape(-1), expected_r, rtol=0., atol=1e-15)
    np.testing.assert_allclose(learner.risk_weights.reshape(-1), expected_p, rtol=0., atol=1e-15)
    assert learner.updates == 10 and first.updates == 7
    assert receipt['fitted_rootgroups'] == receipt['trained_afterstates'] == 3
    assert receipt['learning_counts']['rootgroup_updates'] == receipt['learning_counts']['current_predictions'] == 3
    assert receipt['learning_counts']['table_lookups'] == 192
    assert receipt['learning_counts']['table_updates'] == 2 * uniques
    assert receipt['normalization_counts']['denominator_occurrence_visits'] == 96
    assert receipt['normalization_counts']['normalization_divisions'] == 2 * uniques
    assert receipt['first_sample']['rootgroup'] == 0 and receipt['last_sample']['rootgroup'] == 2
    assert receipt['first_sample']['risk_target'] == .5
    assert 'fitted_games' not in receipt and not any('game' in key for key in receipt['normalization_counts'])
    assert receipt['replicate_noise']['reward_replica_rms'] == pytest.approx(np.sqrt(np.mean((rt-rt.mean(axis=1, keepdims=True))**2)))
    assert receipt['replicate_noise']['win_replica_rms'] == pytest.approx(np.sqrt(np.mean((pt-pt.mean(axis=1, keepdims=True))**2)))


def test_sampling_keeps_teacher_readonly_and_fitter_requires_private_writable_arrays():
    _, first = fixture()
    roots = np.asarray([BOARD], dtype=np.int32)
    with pytest.raises(ValueError, match='private LOCAL learner'):
        fit_supervision(first, roots, np.zeros((1, 4)), np.zeros((1, 4)), BUILD)
    first.risk_weights.flags.writeable = True
    with pytest.raises(ValueError, match='frozen FIRST'):
        query_roots(first, roots, 319300001, BUILD, p_model=.375)
    with pytest.raises(ValueError, match='frozen FIRST'):
        supervise(first, roots, .1, 319300002, BUILD)
