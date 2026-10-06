"""True two-member targets and one-pass native prediction for the V327 intervention."""
from collections import Counter
from fractions import Fraction
import math
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science import joint_terminal_prediction_v327 as prediction
from acfqp.science.native_query_supervision_v319 import fit_supervision
from acfqp.science.native_split_risk_v301 import SplitLeaf, predict_components
from acfqp.science.native_win_learning_v324 import fit_win_supervision

BUILD = Path(__file__).resolve().parents[1] / 'reports/joint_terminal_v327/test_logs/native_runtime'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
BOARD = (1, 2, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0)
ROOTS = np.asarray([(1,) + (0,) * 15, (1,) + (0,) * 15, BOARD], dtype=np.int32)


def fixture():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    template = QueryTD(QueryParent(NtupleValue(rule, BUILD), QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    first = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    index = np.arange(first.reward_weights.size).reshape(first.reward_weights.shape)
    first.reward_weights[:] = index % 7 * .003
    first.risk_weights[:] = -(index % 5) * .01
    first.updates = 7
    first.freeze()
    return template, first


def private(template, first, *, win_only):
    leaf = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    leaf.reward_weights[:] = first.reward_weights
    leaf.risk_weights[:] = first.risk_weights
    leaf.updates = first.updates
    if win_only:
        leaf.reward_weights.flags.writeable = False
    return leaf


def addresses(leaf, board):
    result = []
    for index, pattern in enumerate(leaf.model.patterns.reshape(-1, 6)):
        address = 0
        for cell in pattern:
            address = address * leaf.radix + int(board[cell])
        result.append((index // 8) * leaf.radix ** 6 + address)
    return result


def probability(logit):
    if logit >= 0.:
        return 1. / (1. + math.exp(-logit))
    value = math.exp(logit)
    return value / (1. + value)


@pytest.mark.parametrize('members', (2, 4))
def test_two_round_win_trajectory_is_bit_exact_between_joint_and_win_only(members):
    template, first = fixture()
    win_only = private(template, first, win_only=True)
    joint = private(template, first, win_only=False)
    rw = np.asarray([[1., 2., 3., 4.], [.2, .4, .6, .8], [-1., 0., 1., 2.]])[:, :members]
    ww = np.asarray([[0., 1., 0., 1.], [0., 0., 0., 1.], [1., 1., 0., 1.]])[:, :members]
    reward_before = win_only.reward_weights.tobytes()
    for round_number in (1, 2):
        joint_receipt = fit_supervision(joint, ROOTS, rw * round_number, ww, BUILD)
        win_receipt = fit_win_supervision(win_only, ROOTS, ww, BUILD)
        np.testing.assert_array_equal(win_only.risk_weights, joint.risk_weights)
        assert win_only.reward_weights.tobytes() == reward_before
        assert win_only.updates == joint.updates == 7 + 3 * round_number
        assert joint_receipt['replicates'] == win_receipt['replicates'] == members
        assert win_receipt['sampling_unit'] == joint_receipt['sampling_unit'] == 'ROOTGROUP_MEAN_OF_PROVIDED_REPLICAS'
        for sample in ('first_sample', 'last_sample'):
            assert win_receipt[sample] == {key: joint_receipt[sample][key] for key in win_receipt[sample]}
        assert win_receipt['replicate_noise']['win_replica_rms'] == joint_receipt['replicate_noise']['win_replica_rms']
    assert not np.array_equal(joint.reward_weights, first.reward_weights)
    assert not win_only.reward_weights.flags.writeable and first.updates == 7


def test_literal_two_member_updates_and_member_work_never_duplicate_four_targets():
    template, first = fixture()
    leaf = private(template, first, win_only=False)
    rw = np.asarray([[1., 2.], [.2, .4], [-1., 0.]])
    ww = np.asarray([[0., 1.], [0., 0.], [1., 1.]])
    expected_r, expected_p = leaf.reward_weights.reshape(-1).copy(), leaf.risk_weights.reshape(-1).copy()
    uniques = 0
    for root_index, root in enumerate(ROOTS):
        row = addresses(leaf, root)
        multiplicities = Counter(row)
        assert len(row) == 32 and len(multiplicities) < 32
        uniques += len(multiplicities)
        reward_mean = sum(rw[root_index]) / 2.
        win_mean = sum(ww[root_index]) / 2.
        rp = sum(float(expected_r[address]) for address in row)
        pp = probability(sum(float(expected_p[address]) for address in row))
        for address, count in sorted(multiplicities.items()):
            expected_r[address] += .0025 * (count * (reward_mean - rp)) / count
            expected_p[address] += .0025 * (count * (win_mean - pp)) / count
    joint = fit_supervision(leaf, ROOTS, rw, ww, BUILD)
    np.testing.assert_array_equal(leaf.reward_weights.reshape(-1), expected_r)
    np.testing.assert_array_equal(leaf.risk_weights.reshape(-1), expected_p)
    assert joint['replicates'] == 2
    assert joint['target_counts']['reward_replica_reads'] == 12
    assert joint['target_counts']['win_replica_reads'] == 12
    assert joint['target_counts']['reward_target_mean_additions'] == 6
    assert joint['target_counts']['win_target_mean_additions'] == 6
    assert joint['target_counts']['replica_noise_residuals'] == 12
    assert joint['learning_counts']['table_lookups'] == 192
    assert joint['learning_counts']['table_updates'] == 2 * uniques
    assert joint['normalization_counts']['feature_occurrences'] == 96
    assert joint['normalization_counts']['feature_digit_reads'] == 576
    win_only = private(template, first, win_only=True)
    win = fit_win_supervision(win_only, ROOTS, ww, BUILD)
    np.testing.assert_array_equal(win_only.risk_weights, expected_p.reshape(first.risk_weights.shape))
    assert win['replicates'] == 2
    assert win['target_counts']['win_replica_reads'] == 12
    assert win['target_counts']['win_target_mean_additions'] == 6
    assert win['target_counts']['replica_noise_residuals'] == 6
    assert win['learning_counts']['table_lookups'] == 96
    assert win['learning_counts']['table_updates'] == uniques
    for counters in (win['learning_counts'], win['target_counts'], win['normalization_counts']):
        assert not any('reward' in name for name in counters)


def test_batch_prediction_reads_both_targets_in_one_native_call_per_root(monkeypatch):
    _, first = fixture()
    calls = []
    native_predict = prediction.predict_components

    def counted(leaf, board):
        calls.append(tuple(map(int, board)))
        return native_predict(leaf, board)

    monkeypatch.setattr(prediction, 'predict_components', counted)
    actual = prediction.predict_components_batch(first, ROOTS)
    assert calls == [tuple(map(int, root)) for root in ROOTS]
    expected = [predict_components(first, root) for root in ROOTS]
    for output, key in (('rewards', 'reward_prediction'), ('probabilities', 'risk_probability'),
                        ('logits', 'risk_logit'), ('utilities', 'combined_prediction')):
        np.testing.assert_array_equal(actual[output], [row[key] for row in expected])
    assert actual['counts']['reward_table_lookups'] == actual['counts']['win_table_lookups'] == 96
    assert actual['counts']['feature_occurrences'] == 96
    assert actual['counts']['parameter_writes'] == actual['counts']['fit_updates'] == 0
    assert actual['updates_before'] == actual['updates_after'] == first.updates == 7
    assert actual['readonly']
