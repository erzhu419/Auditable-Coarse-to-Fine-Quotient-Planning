"""Compare local kernel predictions with actual V120/QueryTD table writes."""
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.ntuple_interference_v288 import feature_kernel, pair_metrics
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue, ALPHA
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1] / 'reports/ntuple_interference_v288/runtime/tests'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
BOARDS = np.asarray([[0] * 16, [1] * 16, [1] + [0] * 15,
                     [1, 2, 3, 0] * 4, [2, 1] + [0] * 14], dtype=np.int32)


def make_leaf(offset=False):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    source_query = dict(reward_weight=1., failure_penalty=0., goal_bonus=0.) if offset else QUERY
    return QueryTD(QueryParent(source, source_query, QUERY, .25 if offset else .5),
                   'PRIOR', BUILD)


def prediction(leaf, board):
    return leaf.model.value(board) + leaf.failure_shift + leaf.success_shift


def test_kernel_uses_true_flattened_addresses_and_repeated_occurrences():
    leaf = make_leaf()
    features = np.asarray([leaf.model.feature_indices(board) for board in BOARDS])
    counts = [Counter(row) for row in features]
    expected = [[sum(amount * right.get(address, 0) for address, amount in left.items())
                 for right in counts] for left in counts]
    actual = feature_kernel(features)
    np.testing.assert_array_equal(actual, expected)
    assert actual.dtype == np.int64
    assert actual[0, 0] == 4 * 8 * 8 == 256
    assert actual[0, 1] == 0
    assert actual[0, 2] > 0


@pytest.mark.parametrize('offset', [False, True])
def test_kernel_matches_real_isolated_query_td_update(offset):
    leaf = make_leaf(offset)
    features = np.asarray([leaf.model.feature_indices(board) for board in BOARDS])
    kernel = feature_kernel(features)
    before = np.asarray([prediction(leaf, board) for board in BOARDS])
    target = before[0] + 1.375
    receipt = leaf.update(BOARDS[0], target)
    after = np.asarray([prediction(leaf, board) for board in BOARDS])
    expected = ALPHA * (target - before[0]) * kernel[0]
    np.testing.assert_allclose(after - before, expected, rtol=0., atol=3e-14)
    assert receipt['raw_target'] == target - leaf.offset
    assert leaf.updates == 1 and leaf.model.counts['table_update_occurrences'] == 32
    assert after[1] == before[1]  # no shared address: unchanged exactly


def test_pair_metrics_match_native_single_and_mean_label_updates():
    leaf = make_leaf()
    i, j = BOARDS[0], BOARDS[2]
    features = np.asarray([leaf.model.feature_indices(board) for board in (i, j)])
    k = int(feature_kernel(features)[0, 1])
    vi, vj = prediction(leaf, i), prediction(leaf, j)
    discovery = np.tile(np.asarray([-4., 0., 2., 5.]), 8)
    validation = np.arange(32, dtype=np.float64) / 4. - 5.
    metrics = pair_metrics(vi, vj, discovery, validation, k)
    weights = leaf.weights.copy()
    baseline = np.mean((vj - validation) ** 2)
    observed = []
    for target in discovery:
        np.copyto(leaf.weights, weights)
        leaf.update(i, target)
        updated = prediction(leaf, j)
        observed.append(float(np.mean((updated - validation) ** 2) - baseline))
    np.copyto(leaf.weights, weights)
    leaf.update(i, float(discovery.mean()))
    mean_update = float(np.mean((prediction(leaf, j) - validation) ** 2) - baseline)
    assert metrics['baseline_validation_mse'] == baseline
    assert metrics['mean_label_delta_mse'] == pytest.approx(mean_update, abs=2e-14)
    assert metrics['single_label_mean_delta_mse'] == pytest.approx(np.mean(observed), abs=2e-14)
    assert metrics['single_label_mean_delta_mse'] - metrics['mean_label_delta_mse'] == pytest.approx(
        metrics['empirical_noise_penalty'], abs=2e-14)


def test_validation_variance_cancels_from_delta_and_zero_kernel_does_nothing():
    discovery = np.arange(32, dtype=np.float64) / 8.
    wide = np.tile([-3., 5.], 16)
    point = np.ones(32)
    left = pair_metrics(.25, -.5, discovery, wide, 128)
    right = pair_metrics(.25, -.5, discovery, point, 128)
    assert left['baseline_validation_mse'] - right['baseline_validation_mse'] == 16.
    for name in ('mean_label_delta_mse', 'single_label_mean_delta_mse', 'empirical_noise_penalty'):
        assert left[name] == right[name]
    zero = pair_metrics(.25, -.5, discovery, wide, 0)
    for name in ('mean_label_prediction_delta', 'mean_label_delta_mse',
                 'single_label_mean_delta_mse', 'empirical_noise_penalty'):
        assert zero[name] == 0.
    assert zero['mean_label_validation_mse'] == zero['baseline_validation_mse']
    assert left['batch1_popvar'] == discovery.var(ddof=0)
    assert left['batch2_popvar'] == wide.var(ddof=0)
