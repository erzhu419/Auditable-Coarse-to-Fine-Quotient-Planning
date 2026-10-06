"""Coupled greedy branches, actual terminal costs and unchanged LOCAL commits."""
from collections import Counter, defaultdict
from copy import copy, deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

import numpy as np

from acfqp.science.closed_loop_versions_v313 import snapshot_weights
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue, ACTIONS
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_greedy_targets_v317 import fit_greedy_targets
from acfqp.science.native_local_targets_v314 import fit_local_targets
from acfqp.science.native_policy_stream_v313 import choose_direct
from acfqp.science.native_split_risk_v301 import SplitLeaf

BUILD = Path(__file__).resolve().parents[1] / 'reports/greedy_targets_v317/runtime/tests/native'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
VERSION = dict(file='FIRST_LOCAL_v0.npz', version=0, updates=7, head_kind='LOCAL_RISK')


def leaf_fixture():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    template = QueryTD(QueryParent(NtupleValue(rule, BUILD), QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    return SplitLeaf(template, 'LOCAL_RISK', BUILD)


def indices(leaf, board):
    result = []
    for tuple_index, pattern in enumerate(leaf.model.patterns.reshape(-1, 6)):
        address = 0
        for cell in pattern:
            address = address * leaf.radix + int(board[cell])
        result.append((tuple_index // 8) * leaf.radix ** 6 + address)
    return result


def sigmoid(logit):
    if logit >= 0.:
        return 1. / (1. + math.exp(-logit))
    value = math.exp(logit)
    return value / (1. + value)


def swipe(leaf, board, action):
    after, score = list(board), 0
    for cells in leaf.model.cells[action].reshape(4, 4):
        packed = [int(board[cell]) for cell in cells if board[cell]]
        merged, position = [], 0
        while position < len(packed):
            if position + 1 < len(packed) and packed[position] == packed[position + 1]:
                rank = packed[position] + 1
                merged.append(rank); score += 2 ** rank; position += 2
            else:
                merged.append(packed[position]); position += 1
        for cell, rank in zip(cells, merged + [0] * (4 - len(merged))):
            after[cell] = rank
    return after, score


def branches(leaf, board, snapshot):
    rows = []
    reward_weights, risk_weights = snapshot['reward'].reshape(-1), snapshot['terminal'].reshape(-1)
    for action in range(4):
        after, score = swipe(leaf, board, action)
        if after == list(board):
            continue
        if max(after) >= leaf.radix:
            reward, win, kind = 0., 1., 2
        else:
            addresses = indices(leaf, after)
            reward = sum(float(reward_weights[address]) for address in addresses)
            win = sigmoid(sum(float(risk_weights[address]) for address in addresses))
            kind = 1
        rt = score / 2048. + reward
        rows.append(dict(action=action, reward=rt, win=win, kind=kind,
                         value=rt + 8. * (win - .5), after=after))
    return rows


def coupled_fixture():
    leaf = leaf_fixture()
    board = [1, 1, 2, 0, 2, 1, 3, 0, 0, 2, 1, 0, 1, 0, 0, 0]
    legal = [swipe(leaf, board, action)[0] for action in range(4)]
    features = [Counter(indices(leaf, after)) for after in legal]
    different = next(row for row in features[1:] if row != features[0])
    contrast = np.zeros(leaf.reward_weights.size)
    for address, multiplicity in features[0].items():
        contrast[address] += multiplicity
    for address, multiplicity in different.items():
        contrast[address] -= multiplicity
    projections = [sum(float(contrast[address]) for address in indices(leaf, after)) for after in legal]
    span = max(projections) - min(projections)
    assert span > 0.
    leaf.reward_weights.reshape(-1)[:] = .5 * contrast / span
    leaf.risk_weights.reshape(-1)[:] = -6. * contrast / span + 6. * (max(projections) + min(projections)) / (2. * span * 32.)
    current = board.copy(); current[12] = 0
    lost = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1]
    last = lost.copy(); last[-1] = 0
    data = dict(afterstates=np.asarray([current, last] * 4, dtype=np.int32),
        postspawn_boards=np.asarray([board, lost] * 4, dtype=np.int32),
        rewards=np.asarray([.11, .22, .33, .44, .55, .66, .77, .88]),
        ends=np.asarray([2, 4, 6, 8], dtype=np.int64),
        terminal_codes=np.asarray([-1] * 4, dtype=np.int32), fit_game_count=3, fit_step_end=6)
    return leaf, data


def fit(leaf, data, name):
    snapshot = snapshot_weights(leaf)
    receipt = fit_greedy_targets(leaf, data, snapshot, BUILD, BUILD / name, bootstrap_version=VERSION)
    with np.load(receipt['target_artifact']['file'], allow_pickle=False) as saved:
        targets = {key:saved[key] for key in ('targetreward', 'targetwin', 'targetkind', 'selected_action')}
        metadata = json.loads(str(saved['metadata_json']))
    return receipt, snapshot, targets, metadata


def test_one_combined_direct_branch_feeds_both_targets_and_frozen_batch_snapshot():
    leaf, data = coupled_fixture()
    before_reward, before_risk = leaf.reward_weights.copy(), leaf.risk_weights.copy()
    receipt, snapshot, targets, metadata = fit(leaf, data, 'coupled_targets.npz')
    options = branches(leaf, data['postspawn_boards'][0], snapshot)
    reward_best = max(options, key=lambda row:row['reward'])
    win_best = max(options, key=lambda row:row['win'])
    expected = max(options, key=lambda row:row['value'])
    assert reward_best['action'] != win_best['action']
    assert expected['action'] != reward_best['action']
    frozen = copy(leaf); frozen.reward_weights = snapshot['reward']; frozen.risk_weights = snapshot['terminal']
    actual = choose_direct(frozen, data['postspawn_boards'][0], BUILD)
    assert actual['action'] == ACTIONS[expected['action']]
    for step in (0, 2, 4):
        assert targets['selected_action'][step] == expected['action']
        assert targets['targetreward'][step] == expected['reward']
        assert targets['targetwin'][step] == expected['win']
    assert targets['targetreward'][0] != reward_best['reward']
    assert targets['targetkind'].tolist() == [1, 3, 1, 3, 1, 3]
    np.testing.assert_array_equal(snapshot['reward'], before_reward)
    np.testing.assert_array_equal(snapshot['terminal'], before_risk)
    assert not snapshot['reward'].flags.writeable and not snapshot['terminal'].flags.writeable
    assert receipt['last_sample']['reward_prediction'] != receipt['first_sample']['reward_prediction']
    assert receipt['frozen_game_start_predictions'] and receipt['frozen_batch_start_bootstrap']
    assert receipt['bootstrap_version'] == metadata['bootstrap_version'] == VERSION
    assert metadata['target_rule'] == 'OBSERVED_POSTSPAWN_SINGLE_COMBINED_DIRECT_GREEDY_BRANCH'
    assert metadata['target_array_bytes'] == 6 * 24
    assert metadata == receipt['target_artifact']['metadata']
    assert 0. <= receipt['target_artifact']['save_cpu_seconds'] <= receipt['cpu_seconds']
    assert receipt['bootstrap_counts']['action_candidates'] == 24
    assert receipt['bootstrap_planning_counts']['learned_swipe_calls'] == 24
    assert receipt['bootstrap_counts']['feature_occurrences'] == 32 * receipt['bootstrap_counts']['candidate_afterstate_predictions']
    json.dumps(receipt, allow_nan=False)


def test_analytic_win_postspawn_loss_unused_current_win_and_direct_first_max_ties():
    leaf = leaf_fixture()
    current = [3, 3, 0, 0] + [0] * 12
    next_win = [3, 3, 1, 0] + [0] * 12
    win = [4] + [0] * 15
    tie = [1, 2, 0, 0] + [0] * 12
    lost = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1]
    last = lost.copy(); last[-1] = 0
    data = dict(afterstates=np.asarray([current, win, [1] + [0] * 15, last, current, last], dtype=np.int32),
        postspawn_boards=np.asarray([next_win, [4, 1] + [0] * 14, tie, lost, next_win, lost], dtype=np.int32),
        rewards=np.asarray([91., 92., 93., 94., 95., 96.]),
        ends=np.asarray([2, 4, 6], dtype=np.int64), terminal_codes=np.asarray([1, -1, -1], dtype=np.int32),
        fit_game_count=2, fit_step_end=4)
    receipt, _, targets, _ = fit(leaf, data, 'terminal_targets.npz')
    assert targets['selected_action'].tolist() == [ACTIONS.index('LEFT'), -1, ACTIONS.index('DOWN'), -1]
    np.testing.assert_array_equal(targets['targetreward'], [16. / 2048., 0., 0., 0.])
    np.testing.assert_array_equal(targets['targetwin'], [1., 0., .5, 0.])
    assert targets['targetkind'].tolist() == [2, 0, 1, 3]
    assert receipt['trained_afterstates'] == 3
    assert receipt['target_counts'] == dict(terminal_game_labels=2, goal_checks=4, skipped_winning_afterstates=1,
        postspawn_board_reads=3, reward_target_assignments=3, win_target_assignments=3,
        bootstrap_greedy_targets=1, analytic_selected_win_targets=1, postspawn_lost_targets=1, target_kind_reads=4)
    assert receipt['bootstrap_counts']['analytic_win_candidates'] == 2
    assert receipt['bootstrap_planning_counts']['leaf_terminal_loss_states'] == 1


def test_literal_game_start_commits_collision_denominators_and_sarsa_write_budget_match():
    leaf, data = coupled_fixture()
    sarsa, _ = coupled_fixture()
    expected_reward, expected_risk = leaf.reward_weights.reshape(-1).copy(), leaf.risk_weights.reshape(-1).copy()
    receipt, _, targets, _ = fit(leaf, data, 'literal_commits.npz')
    start = 0
    for end in data['ends'][:data['fit_game_count']]:
        rows = list(range(start, int(end)))
        features = {step:indices(leaf, data['afterstates'][step]) for step in rows}
        assert any(len(set(row)) < 32 for row in features.values())
        denominators = Counter(address for row in features.values() for address in row)
        reward_gradient, risk_gradient = defaultdict(float), defaultdict(float)
        for step in rows:
            row = features[step]
            rp = sum(float(expected_reward[address]) for address in row)
            pp = sigmoid(sum(float(expected_risk[address]) for address in row))
            for address, multiplicity in sorted(Counter(row).items()):
                reward_gradient[address] += multiplicity * (targets['targetreward'][step] - rp)
                risk_gradient[address] += multiplicity * (targets['targetwin'][step] - pp)
        for address in sorted(denominators):
            expected_reward[address] += .0025 * reward_gradient[address] / denominators[address]
            expected_risk[address] += .0025 * risk_gradient[address] / denominators[address]
        start = int(end)
    np.testing.assert_allclose(leaf.reward_weights.reshape(-1), expected_reward, rtol=0., atol=1e-15)
    np.testing.assert_allclose(leaf.risk_weights.reshape(-1), expected_risk, rtol=0., atol=1e-15)
    control = fit_local_targets(sarsa, data, snapshot_weights(sarsa), BUILD, BUILD / 'sarsa_control.npz', bootstrap_version=VERSION)
    assert receipt['learning_counts'] == control['learning_counts']
    assert receipt['representation_counts'] == control['representation_counts']
    assert receipt['normalization_counts'] == control['normalization_counts']
    assert leaf.updates == sarsa.updates == 6


def test_recorded_rewards_successor_afterstates_and_heldout_boards_do_not_enter_greedy_targets():
    first, data = coupled_fixture()
    second, _ = coupled_fixture()
    changed = deepcopy(data)
    changed['rewards'] += 1000.
    changed['afterstates'][6:] = 0
    changed['postspawn_boards'][6:] = 0
    a, _, targets_a, _ = fit(first, data, 'isolation_a.npz')
    b, _, targets_b, _ = fit(second, changed, 'isolation_b.npz')
    for key in targets_a:
        np.testing.assert_array_equal(targets_a[key], targets_b[key])
    np.testing.assert_array_equal(first.reward_weights, second.reward_weights)
    np.testing.assert_array_equal(first.risk_weights, second.risk_weights)
    assert a['first_sample'] == b['first_sample'] and a['last_sample'] == b['last_sample']
