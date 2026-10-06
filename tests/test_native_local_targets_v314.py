"""Recorded successor targets, frozen bootstrap, duplicate addresses and real writes."""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

import numpy as np

from acfqp.science.closed_loop_versions_v313 import snapshot_weights
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_local_targets_v314 import fit_local_targets
from acfqp.science.native_split_risk_v301 import SplitLeaf, fit_split

BUILD = Path(__file__).resolve().parents[1] / 'reports/local_targets_v314/runtime/tests/native_local_targets'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
VERSION = dict(file='FIRST_LOCAL_v0.npz', version=0, updates=7, head_kind='LOCAL_RISK')


def fixture():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    template = QueryTD(QueryParent(NtupleValue(rule, BUILD), QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    leaf = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    leaf.reward_weights[:] = .01
    leaf.risk_weights[:] = -.01
    a, b, win = [1, 0, 0, 0] + [0] * 12, [2, 0, 0, 0] + [0] * 12, [4] + [0] * 15
    data = dict(lifecycle=0, parent=0, afterstates=np.asarray([a, b, a, b, a, win, a, b], dtype=np.int32),
        rewards=np.asarray([.11, .22, .33, .44, .55, .66, .77, .88]),
        ends=np.asarray([2, 4, 6, 8], dtype=np.int64),
        terminal_codes=np.asarray([-1, -1, 1, -1], dtype=np.int32), fit_game_count=3, fit_step_end=6)
    return leaf, data


def fit(leaf, data, name):
    snapshot = snapshot_weights(leaf)
    receipt = fit_local_targets(leaf, data, snapshot, BUILD, BUILD / name,
                               bootstrap_version=VERSION)
    with np.load(receipt['target_artifact']['file'], allow_pickle=False) as saved:
        targets = {key:saved[key].copy() for key in ('targetreward', 'targetwin', 'targetkind')}
        metadata = json.loads(str(saved['metadata_json']))
    return receipt, snapshot, targets, metadata


def test_targets_use_recorded_successor_batch_snapshot_and_correct_terminal_costs():
    leaf, data = fixture()
    receipt, snapshot, targets, metadata = fit(leaf, data, 'terminal_targets.npz')
    r0, p0 = sum([.01] * 32), 1. / (1. + math.exp(-sum([-.01] * 32)))
    np.testing.assert_allclose(targets['targetreward'], [.22 + r0, 0., .44 + r0, 0., .66, 0.], rtol=0., atol=1e-15)
    np.testing.assert_allclose(targets['targetwin'], [p0, 0., p0, 0., 1., 0.], rtol=0., atol=1e-15)
    assert targets['targetkind'].tolist() == [1, 3, 1, 3, 2, 0]
    assert receipt['first_sample']['reward_target'] == targets['targetreward'][0]
    assert receipt['first_sample']['risk_target'] == targets['targetwin'][0]
    assert receipt['last_sample']['step'] == 4
    assert receipt['last_sample']['reward_target'] == .66 and receipt['last_sample']['risk_target'] == 1.
    assert targets['targetwin'][0] == targets['targetwin'][2]
    assert receipt['last_sample']['risk_probability'] != p0
    assert leaf.updates == receipt['trained_afterstates'] == 5
    assert receipt['bootstrap_mode'] == 'BATCH_START_FROZEN_OWN_HEAD'
    assert receipt['bootstrap_version'] == metadata['bootstrap_version'] == VERSION
    assert receipt['frozen_batch_start_bootstrap'] and receipt['frozen_game_start_predictions']
    assert metadata == receipt['target_artifact']['metadata']
    assert metadata['target_array_bytes'] == 6 * 20
    assert receipt['target_artifact']['saved_bytes'] == Path(receipt['target_artifact']['file']).stat().st_size
    assert 0. <= receipt['target_artifact']['save_cpu_seconds'] <= receipt['cpu_seconds']
    assert 0. <= receipt['target_generation_cpu_seconds'] <= receipt['cpu_seconds']
    assert all(not snapshot[key].flags.writeable for key in ('reward', 'terminal'))
    assert np.all(snapshot['reward'] == .01) and np.all(snapshot['terminal'] == -.01)
    json.dumps(receipt, allow_nan=False)


def test_native_commits_match_literal_game_start_soft_label_residuals_and_collision_denominators():
    leaf, data = fixture()
    expected_reward, expected_risk = leaf.reward_weights.reshape(-1).copy(), leaf.risk_weights.reshape(-1).copy()
    receipt, _, targets, _ = fit(leaf, data, 'literal_commits.npz')
    start = 0
    for end in data['ends'][:data['fit_game_count']]:
        rows = [i for i in range(start, int(end)) if max(data['afterstates'][i]) < 4]
        features = {i:leaf.model.feature_indices(data['afterstates'][i]).tolist() for i in rows}
        assert any(len(set(indices)) < 32 for indices in features.values())
        denominators = Counter(address for indices in features.values() for address in indices)
        reward_gradient, risk_gradient = defaultdict(float), defaultdict(float)
        for i in rows:
            indices = features[i]
            reward = sum(float(expected_reward[a]) for a in indices)
            probability = 1. / (1. + math.exp(-sum(float(expected_risk[a]) for a in indices)))
            reward_error = targets['targetreward'][i] - reward
            risk_error = targets['targetwin'][i] - probability
            for address, multiplicity in sorted(Counter(indices).items()):
                reward_gradient[address] += multiplicity * reward_error
                risk_gradient[address] += multiplicity * risk_error
        for address in sorted(denominators):
            expected_reward[address] += .0025 * reward_gradient[address] / denominators[address]
            expected_risk[address] += .0025 * risk_gradient[address] / denominators[address]
        start = int(end)
    np.testing.assert_allclose(leaf.reward_weights.reshape(-1), expected_reward, rtol=0., atol=1e-15)
    np.testing.assert_allclose(leaf.risk_weights.reshape(-1), expected_risk, rtol=0., atol=1e-15)
    assert receipt['bootstrap_counts'] == dict(afterstate_predictions=2,
        reward_table_lookups=64, risk_table_lookups=64, feature_extractions=2,
        feature_occurrences=64, feature_digit_reads=384, feature_address_multiply_adds=384,
        risk_sigmoid_evaluations=2, local_risk_table_lookups=64)
    assert receipt['target_counts'] == dict(terminal_game_labels=3, goal_checks=6,
        skipped_winning_afterstates=1, sampled_next_reward_reads=3,
        reward_target_assignments=5, win_target_assignments=5, bootstrap_successor_targets=2,
        analytic_next_win_targets=1, terminal_lost_targets=2, next_afterstate_goal_checks=3,
        target_kind_reads=6)
    leaf.freeze()
    chosen = leaf.choose(data['afterstates'][0], .375)
    assert chosen['action'] in ('DOWN', 'LEFT', 'RIGHT', 'UP') and leaf.updates == 5


def test_mc_control_matches_current_rows_address_normalization_and_two_head_writes():
    td, data = fixture()
    mc, _ = fixture()
    td_receipt, _, _, _ = fit(td, data, 'matched_control.npz')
    mc_receipt = fit_split(mc, data, BUILD)
    assert td_receipt['learning_counts'] == mc_receipt['learning_counts']
    assert td_receipt['representation_counts'] == mc_receipt['representation_counts']
    for key in set(td_receipt['normalization_counts']) | set(mc_receipt['normalization_counts']):
        if key != 'native_buffer_bytes_peak':
            assert td_receipt['normalization_counts'].get(key, 0) == mc_receipt['normalization_counts'].get(key, 0)
    assert td_receipt['reward_trained_afterstates'] == td_receipt['risk_trained_afterstates'] == mc_receipt['trained_afterstates'] == 5
    assert not np.array_equal(td.reward_weights, mc.reward_weights)
    assert not np.array_equal(td.risk_weights, mc.risk_weights)


def test_current_reward_other_game_and_heldout_changes_cannot_enter_targets():
    first, data = fixture()
    other, _ = fixture()
    changed = deepcopy(data)
    changed['rewards'][[0, 2, 6, 7]] += 1000.
    changed['afterstates'][6:] = 0
    a, _, targets_a, _ = fit(first, data, 'isolation_a.npz')
    b, _, targets_b, _ = fit(other, changed, 'isolation_b.npz')
    for key in targets_a:
        np.testing.assert_array_equal(targets_a[key], targets_b[key])
    np.testing.assert_array_equal(first.reward_weights, other.reward_weights)
    np.testing.assert_array_equal(first.risk_weights, other.risk_weights)
    assert a['first_sample'] == b['first_sample'] and a['last_sample'] == b['last_sample']
