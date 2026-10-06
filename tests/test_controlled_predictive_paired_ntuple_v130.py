"""Synthetic checks of paired residual learning; no environment sampling."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_anchored_success_v127 import AnchoredSuccess, choose_gpi
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_paired_ntuple_v130 import PairResidual, QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/controlled_predictive_paired_ntuple_v130_build'
BOARD = [1, 1, 0, 0] + [0] * 12
OTHER = [2, 0, 1, 0] + [0] * 12
GOAL = [4] + [0] * 15
LOST = [1, 2, 1, 2, 2, 1, 2, 1] * 2
REWARD = dict(reward_weight=1., failure_penalty=0., goal_bonus=0.)
RISK = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
TARGET = dict(reward_weight=1., failure_penalty=1., goal_bonus=1.)
SOURCES, PARENTS, MODELS, REFERENCES = [], [], [], []
REFERENCE_WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_paired_ntuple_v130.core_checks.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    work = sum((model.counts - baseline for model, baseline in MODELS), Counter())
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before, core_work=dict(work),
        source_work=dict(sum((model.counts for model in SOURCES), Counter())),
        parent_work=dict(sum((model.counts for model in PARENTS), Counter())),
        reference_work=dict(sum((model.counts for model in REFERENCES), REFERENCE_WORK.copy())),
        setup_counts=dict(sum((model.setup_counts for model in SOURCES + REFERENCES +
                              [model for model, _ in MODELS]), Counter())),
        newly_sampled_environment_transitions=0,
        scope='Synthetic boards only. Source-prefixed counters overlap source_work; loaded histories excluded.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def parent(source_query=RISK, target_query=TARGET, constant=.4):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    source.weights.flags.writeable = False
    source.updates = 42
    SOURCES.append(source)
    result = QueryParent(source, source_query, target_query, constant)
    PARENTS.append(result)
    return result


def model(kind='PRIOR', **kwargs):
    result = PairResidual(parent(**kwargs), kind=kind, build_dir=BUILD)
    MODELS.append((result, Counter()))
    return result


def features(source, board):
    if max(board) >= source.radix:
        return Counter()
    REFERENCE_WORK['reference_feature_address_occurrences'] += 32
    return Counter(map(int, source.feature_indices(board)))


def difference(source, first, second):
    result = features(source, first)
    result.subtract(features(source, second))
    return {index: count for index, count in result.items() if count}


def assert_same_choices(actual, expected):
    assert actual['status'] == expected['status']
    assert actual['action'] == expected['action']
    assert actual['value'] == expected['value']
    assert set(actual['action_values']) == set(expected['action_values'])
    for action, row in expected['action_values'].items():
        candidate = actual['action_values'][action]
        for name in ('value', 'score', 'afterstate'):
            assert candidate[name] == row[name]


def test_query_parent_exactly_matches_v127_constant_single_policy():
    for source_query in (REWARD, RISK):
        for target_query in (source_query, TARGET):
            result = parent(source_query, target_query)
            reference = AnchoredSuccess(result.source, source_query, BUILD)
            reference.updates, reference.successes = 5, 2
            REFERENCES.append(reference)
            for board in (BOARD, OTHER, [3, 3] + [0] * 14, GOAL, LOST):
                expected = choose_gpi([reference], board, target_query, mode='CONSTANT')
                assert_same_choices(result.choose(board), expected)
            assert result.updates == result.source.updates == 42
            assert result.counts['source_choose_calls'] == 5


def test_zero_prior_preserves_all_parent_values_and_lexical_ties():
    result = model()
    for board in (BOARD, OTHER, [3, 3] + [0] * 14, GOAL, LOST):
        expected = result.parent.choose(board)
        actual = result.choose(board)
        assert_same_choices(actual, expected)
        for action, row in actual['action_values'].items():
            assert row['base_value'] == expected['action_values'][action]['value']
            assert row['residual'] == 0.


def test_pair_gradient_uses_merged_signed_multiplicities_and_normalization():
    result = model()
    result.weights[:] = np.arange(result.weights.size).reshape(result.weights.shape) % 7 * .003
    source = result.parent.source
    a, b = features(source, BOARD), features(source, OTHER)
    assert max(a.values()) > 1 and set(a) & set(b)
    delta = difference(source, BOARD, OTHER)
    old = result.weights.copy()
    residual_gap = sum(old.reshape(-1)[index] * count for index, count in delta.items())
    denominator = sum(count * count for count in delta.values())
    base_gap, target_gap, rate = .2, 1.7, .1
    error = target_gap - base_gap - residual_gap
    expected = old.copy().reshape(-1)
    for index, count in delta.items():
        expected[index] += rate * error * count / denominator
    fit = result.fit_pair(BOARD, OTHER, base_gap, target_gap, rate=rate)
    assert fit['applied'] and not fit['unidentifiable']
    assert fit['denominator'] == denominator
    assert fit['residual_gap'] == pytest.approx(residual_gap, abs=1e-14)
    assert fit['predicted_gap'] == pytest.approx(base_gap + residual_gap, abs=1e-14)
    assert fit['error'] == pytest.approx(error, abs=1e-14)
    np.testing.assert_allclose(result.weights.reshape(-1), expected, rtol=0, atol=1e-16)
    assert result.updates == 1


def test_identical_and_d4_equivalent_pairs_are_unidentifiable():
    result = model()
    rotated = np.rot90(np.asarray(OTHER).reshape(4, 4)).reshape(-1).tolist()
    assert rotated != OTHER
    assert features(result.parent.source, OTHER) == features(result.parent.source, rotated)
    for first, second in ((OTHER, OTHER), (OTHER, rotated)):
        fit = result.fit_pair(first, second, .2, 1.7)
        assert fit['denominator'] == 0
        assert fit['unidentifiable'] and not fit['applied']
        assert fit['residual_gap'] == 0.
    assert result.updates == 0
    assert not np.any(result.weights)


def test_goal_features_are_zero_and_terminal_values_remain_analytic():
    result = model()
    result.weights.fill(.01)
    assert result.residuals([GOAL]) == [0.]
    old = result.weights.copy()
    delta = difference(result.parent.source, GOAL, OTHER)
    residual_gap = sum(old.reshape(-1)[index] * count for index, count in delta.items())
    denominator = sum(count * count for count in delta.values())
    fit = result.fit_pair(GOAL, OTHER, .5, 1.5)
    expected = old.copy().reshape(-1)
    for index, count in delta.items():
        expected[index] += .1 * (1.5 - .5 - residual_gap) * count / denominator
    assert fit['denominator'] == denominator
    np.testing.assert_allclose(result.weights.reshape(-1), expected, rtol=0, atol=1e-16)
    assert result.residuals([GOAL]) == [0.]
    assert result.choose(GOAL)['value'] == TARGET['goal_bonus']
    assert result.choose(GOAL)['status'] == 'WON'
    assert result.choose(LOST)['value'] == -TARGET['failure_penalty']
    assert result.choose(LOST)['status'] == 'LOST'
    choice = result.choose([3, 3] + [0] * 14)
    goals = [row for row in choice['action_values'].values() if max(row['afterstate']) >= 4]
    assert goals
    for row in goals:
        assert row['residual'] == 0.
        assert row['value'] == row['score'] / 2048 + TARGET['goal_bonus']


def test_fit_never_updates_source_and_rejects_readonly_residual_weights():
    result = model()
    source = result.parent.source
    weights, updates, counts = source.weights.copy(), source.updates, source.counts.copy()
    result.fit_pair(BOARD, OTHER, .2, 1.7)
    assert source.counts == counts
    result.choose(BOARD)
    np.testing.assert_array_equal(source.weights, weights)
    assert source.updates == updates
    result.weights.flags.writeable = False
    before = result.weights.copy()
    with pytest.raises(RuntimeError, match='cannot be updated|read.only'):
        result.fit_pair(BOARD, OTHER, .2, 1.7)
    np.testing.assert_array_equal(result.weights, before)
    assert result.updates == 1


def test_scratch_uses_immediate_reward_and_no_source_predictions():
    result = model(kind='SCRATCH')
    source = result.parent.source
    counts = source.counts.copy()
    for board in (BOARD, OTHER, [3, 3] + [0] * 14, GOAL, LOST):
        choice = result.choose(board)
        for row in choice['action_values'].values():
            expected = row['score'] / 2048 + (TARGET['goal_bonus'] if max(row['afterstate']) >= 4 else 0.)
            assert row['base_value'] == row['value'] == expected
            assert row['residual'] == 0.
    result.fit_pair(BOARD, OTHER, .2, 1.7)
    result.choose(BOARD)
    assert source.counts == counts
    assert result.parent.counts == Counter()
    assert source.updates == 42


def test_sparse_save_load_preserves_parameters_and_pair_metadata(tmp_path):
    result = model()
    result.fit_pair(BOARD, OTHER, .2, 1.7)
    saved = result.save(tmp_path / 'paired.npz')
    with np.load(saved['path'], allow_pickle=False) as data:
        metadata = json.loads(str(data['metadata']))
        assert metadata['schema'] == 'acfqp.paired_ntuple.v130'
        assert metadata['kind'] == 'PRIOR'
        assert metadata['updates'] == 1
        assert metadata['source_updates'] == 42
        assert metadata['source_query'] == RISK
        assert metadata['target_query'] == TARGET
        assert metadata['constant'] == .4
        expected = np.zeros(result.weights.size)
        expected[data['indices']] = data['values']
        np.testing.assert_array_equal(expected.reshape(result.weights.shape), result.weights)
        assert len(data['indices']) == np.count_nonzero(result.weights)
    restored = PairResidual.load(saved['path'], result.parent, BUILD)
    MODELS.append((restored, Counter()))
    np.testing.assert_array_equal(restored.weights, result.weights)
    assert restored.updates == result.updates
    assert restored.kind == result.kind
    assert_same_choices(restored.choose(BOARD), result.choose(BOARD))
