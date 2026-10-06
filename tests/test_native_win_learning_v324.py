"""WIN-only writes must reproduce the old WIN trajectory without reward access."""
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
from acfqp.science.native_query_supervision_v319 import fit_supervision, supervise
from acfqp.science.native_split_risk_v301 import SplitLeaf
from acfqp.science.native_win_learning_v324 import fit_win_supervision

BUILD = Path(__file__).resolve().parents[1] / 'reports/win_learning_v324/test_logs/native_runtime'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
BOARD = (1, 2, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0)
LOST_ROOT = (2, 3, 2, 3, 3, 2, 3, 2, 2, 3, 2, 3, 3, 2, 3, 0)


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


def private(template, first, *, win_only):
    leaf = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    leaf.reward_weights[:] = first.reward_weights; leaf.risk_weights[:] = first.risk_weights
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


def test_full_win_table_exactly_matches_dual_fit_through_both_rounds():
    template, first = fixture()
    win_only = private(template, first, win_only=True)
    dual = private(template, first, win_only=False)
    reward_before = win_only.reward_weights.tobytes()
    roots = np.asarray([(1,) + (0,) * 15, (1,) + (0,) * 15, BOARD], dtype=np.int32)
    rw = np.asarray([[1., 2., 3., 4.], [.2, .4, .6, .8], [-1., 0., 1., 2.]])
    ww = np.asarray([[0., .25, .75, 1.], [.1, .2, .3, .4], [.2, .2, .6, 1.]])
    for number in (1, 2):
        old = fit_supervision(dual, roots, rw * number, ww, BUILD)
        actual = fit_win_supervision(win_only, roots, ww, BUILD)
        np.testing.assert_array_equal(win_only.risk_weights, dual.risk_weights)
        assert win_only.reward_weights.tobytes() == reward_before
        assert not win_only.reward_weights.flags.writeable
        assert win_only.updates == dual.updates == 7 + 3 * number
        for sample in ('first_sample', 'last_sample'):
            assert actual[sample] == {key:old[sample][key] for key in actual[sample]}
        assert actual['replicate_noise']['win_replica_rms'] == old['replicate_noise']['win_replica_rms']
        assert actual['normalization_counts']['sort_comparisons'] == old['normalization_counts']['sort_comparisons']
    assert not np.array_equal(dual.reward_weights, first.reward_weights)
    assert first.updates == 7


def test_literal_duplicate_address_normalization_and_truthful_win_only_counts():
    template, first = fixture(); leaf = private(template, first, win_only=True)
    roots = np.asarray([(1,) + (0,) * 15, (1,) + (0,) * 15, BOARD], dtype=np.int32)
    targets = np.asarray([[0., .25, .75, 1.], [.1, .2, .3, .4], [.2, .2, .6, 1.]])
    expected = leaf.risk_weights.reshape(-1).copy(); uniques = 0; samples = []
    for index, root in enumerate(roots):
        occurrences = addresses(leaf, root); multiplicities = Counter(occurrences)
        assert len(multiplicities) < 32
        uniques += len(multiplicities)
        mean = sum(targets[index]) / 4.
        prediction = probability(sum(float(expected[address]) for address in occurrences))
        error = mean - prediction
        samples.append(dict(rootgroup=index, risk_target=mean, risk_probability=prediction, risk_error=error))
        for address, count in sorted(multiplicities.items()):
            expected[address] += .0025 * (count * error) / count
    result = fit_win_supervision(leaf, roots, targets, BUILD)
    np.testing.assert_array_equal(leaf.risk_weights.reshape(-1), expected)
    assert result['first_sample'] == samples[0] and result['last_sample'] == samples[-1]
    learning = result['learning_counts']
    for name in ('rootgroup_updates', 'current_predictions', 'win_predictions'):
        assert learning[name] == 3
    for name in ('table_lookups', 'win_table_lookups', 'table_update_occurrences'):
        assert learning[name] == 96
    assert learning['table_updates'] == learning['win_parameter_updates'] == uniques
    target = result['target_counts']
    assert target['rootgroups_targeted'] == target['target_mean_divisions'] == 3
    assert target['win_replica_reads'] == 24 and target['win_target_mean_additions'] == 12
    for name in ('replica_noise_residuals', 'replica_noise_squares', 'replica_noise_accumulations'):
        assert target[name] == 12
    assert target['replica_noise_divisions'] == target['replica_noise_square_roots'] == 1
    norm = result['normalization_counts']
    assert norm['denominator_occurrence_visits'] == norm['feature_occurrences'] == 96
    assert norm['feature_digit_reads'] == norm['feature_address_multiply_adds'] == 576
    for name in ('rootgroup_unique_addresses', 'win_gradient_products', 'normalization_divisions',
                 'parameter_update_multiplications', 'win_parameter_writes'):
        assert norm[name] == uniques
    assert norm['rootgroup_parameter_commits'] == norm['win_rootgroup_commits'] == 3
    assert norm['native_workspace_bytes'] == 512
    assert result['representation_counts'] == dict(risk_sigmoid_evaluations=3, local_risk_table_lookups=96)
    for counters in (learning, target, norm):
        assert not any('reward' in key for key in counters)
    assert result['reward_trained_afterstates'] == 0
    assert result['replicate_noise']['win_replica_rms'] == pytest.approx(
        np.sqrt(np.mean((targets-targets.mean(axis=1,keepdims=True))**2)))


def test_actual_four_draw_first_targets_include_win_loss_and_soft_bootstrap_without_reward_writes():
    template, first = fixture()
    roots = np.asarray([BOARD, (3, 3, 0, 0) + (0,) * 12, LOST_ROOT], dtype=np.int32)
    labels = supervise(first, roots, .375, 324200004, BUILD)
    assert labels['targetwin'][1].tolist() == [1.] * 4
    assert labels['targetwin'][2].tolist() == [0.] * 4
    assert np.all((labels['targetwin'][0] > 0.) & (labels['targetwin'][0] < 1.))
    learner = private(template, first, win_only=True); dual = private(template, first, win_only=False)
    fit_win_supervision(learner, roots, labels['targetwin'], BUILD)
    fit_supervision(dual, roots, labels['targetreward'], labels['targetwin'], BUILD)
    np.testing.assert_array_equal(learner.risk_weights, dual.risk_weights)
    np.testing.assert_array_equal(learner.reward_weights, first.reward_weights)
    assert not learner.reward_weights.flags.writeable and first.updates == 7


def test_fitting_requires_frozen_reward_private_win_and_four_replicas():
    template, first = fixture(); roots = np.asarray([BOARD], dtype=np.int32)
    with pytest.raises(ValueError, match='frozen FIRST reward'):
        fit_win_supervision(first, roots, np.zeros((1, 4)), BUILD)
    learner = private(template, first, win_only=False)
    with pytest.raises(ValueError, match='frozen FIRST reward'):
        fit_win_supervision(learner, roots, np.zeros((1, 4)), BUILD)
    learner.reward_weights.flags.writeable = False
    with pytest.raises(ValueError, match='four replicas'):
        fit_win_supervision(learner, roots, np.zeros((1, 1)), BUILD)
