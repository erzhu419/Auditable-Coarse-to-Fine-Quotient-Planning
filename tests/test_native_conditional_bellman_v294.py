"""Finite literal references for the frozen V294 mathematics; no RNG games."""
from collections import Counter
from dataclasses import replace
from fractions import Fraction
import math
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import native_conditional_bellman_v294 as core
from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1] / 'reports/conditional_bellman_v294/runtime_tests'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def template(offset=False):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    source_query = dict(reward_weight=1., failure_penalty=0., goal_bonus=0.) if offset else QUERY
    leaf = QueryTD(QueryParent(source, source_query, QUERY, .25 if offset else .5), 'PRIOR', BUILD)
    leaf.freeze()
    return leaf


def game(winning=True, p=(.1, .5, .2, .8)):
    boards = [[2]+[0]*15, [2, 1]+[0]*14, [3, 3]+[0]*14, [4]+[0]*15]
    n = 4 if winning else 3
    return dict(afterstates=np.asarray(boards[:n], dtype=np.int32),
        rewards=np.asarray([4, 8, 8, 16][:n], dtype=np.float64)/2048.,
        model_p_four=np.asarray(p[:n], dtype=np.float64), terminal_code=1 if winning else -1)


def coefficients(p, conditioned):
    return np.asarray(((1.-p), p))/math.sqrt((1.-p)**2+p*p) if conditioned else np.asarray([1.])


def literal_prediction(head, board, p, residuals):
    if max(board) >= head.template.radix:
        return head.template.target_query['goal_bonus']
    indices = head.template.model.feature_indices(board)
    source, residual = head.template.weights.reshape(-1), residuals.reshape(head.banks, -1)
    basis = coefficients(p, head.conditioned)
    value = 0.
    for address in indices:
        weight = float(source[address])+float(basis[0])*float(residual[0, address])
        if head.banks == 2:
            weight += float(basis[1])*float(residual[1, address])
        value += weight
    return value+head.template.failure_shift+head.template.success_shift


def literal_update(head, data, targets):
    before = head.residuals.copy()
    rows, denominators = [], Counter()
    for step, board in enumerate(data['afterstates']):
        if max(board) >= head.template.radix:
            continue
        features = list(map(int, head.template.model.feature_indices(board)))
        denominators.update(features)
        p = float(data['model_p_four'][step])
        prediction = literal_prediction(head, board, p, before)
        error = float(targets[step])-prediction
        rows.append((step, features, coefficients(p, head.conditioned), error, prediction))
    gradients = [{a: 0. for a in denominators} for _ in range(head.banks)]
    for _, features, basis, error, _ in rows:
        for address in features:
            for bank in range(head.banks):
                gradients[bank][address] += float(basis[bank])*error
    flat = before.reshape(head.banks, -1)
    for bank in range(head.banks):
        for address in sorted(denominators):
            flat[bank, address] += .0025*gradients[bank][address]/denominators[address]
    return before, rows, denominators


def suffixes(data):
    suffix = 4. if data['terminal_code'] == 1 else -4.
    targets = np.zeros(len(data['rewards']))
    for step in reversed(range(len(targets))):
        targets[step] = suffix
        suffix += float(data['rewards'][step])
    return targets


def expected_control(head, board, p):
    leaf, _ = core.materialize(head, p, BUILD)
    empty = [i for i, rank in enumerate(board) if not rank]
    total = 0.
    for cell in empty:
        for rank in (1, 2):
            spawned = list(board); spawned[cell] = rank
            value = leaf.choose(spawned)['value']
            total += ((1.-p if rank == 1 else p)/len(empty))*value
    return total


@pytest.mark.parametrize('conditioned', [False, True])
@pytest.mark.parametrize('offset', [False, True])
def test_factual_game_frozen_errors_and_original_address_normalization(conditioned, offset):
    source = template(offset)
    original = source.weights.copy()
    head = core.ResidualHead(source, conditioned, BUILD)
    for data in (game(), game(False)):
        targets = suffixes(data)
        reference, rows, denominators = literal_update(head, data, targets)
        result = core.fit_episode(head, data, 'MC', BUILD)
        np.testing.assert_array_equal(head.residuals, reference)
        assert result['trained_afterstates'] == 3
        assert result['learning_counts']['table_update_occurrences'] == 96*head.banks
        assert result['learning_counts']['table_updates'] == len(denominators)*head.banks
        assert result['consolidation_counts']['normalization_divisions'] == len(denominators)*head.banks
        for key, row in (('first_sample', rows[0]), ('last_sample', rows[-1])):
            step, _, _, error, prediction = row
            assert result[key] == dict(step=step, target=float(targets[step]),
                prediction_before_update=prediction, error=error,
                model_p_four=float(data['model_p_four'][step]))
        assert result['target_counts'].get('skipped_winning_afterstates', 0) == int(data['terminal_code'] == 1)
        assert result['target_counts']['suffix_target_assignments'] == len(data['rewards'])
    assert head.updates == 6
    np.testing.assert_array_equal(source.weights, original)
    assert source.updates == source.parent.source.updates == 0
    assert not source.weights.flags.writeable


@pytest.mark.parametrize('conditioned', [False, True])
def test_expected_control_uses_whole_game_start_head_not_factual_future(conditioned):
    source = template()
    left, right = core.ResidualHead(source, conditioned, BUILD), core.ResidualHead(source, conditioned, BUILD)
    left.residuals[:] = np.arange(left.residuals.size).reshape(left.residuals.shape) % 7 * .002
    np.copyto(right.residuals, left.residuals)
    data = game(False)
    targets = [expected_control(left, b, float(p)) for b, p in zip(data['afterstates'], data['model_p_four'])]
    reference, rows, denominators = literal_update(left, data, targets)
    changed = dict(data, rewards=data['rewards']+100., terminal_code=1)
    a = core.fit_episode(left, data, 'EXPECTED_CONTROL', BUILD)
    b = core.fit_episode(right, changed, 'EXPECTED_CONTROL', BUILD)
    np.testing.assert_array_equal(left.residuals, right.residuals)
    np.testing.assert_allclose(left.residuals, reference, rtol=0., atol=2e-15)
    assert a['first_sample'] == b['first_sample'] and a['last_sample'] == b['last_sample']
    assert a['first_sample']['target'] == pytest.approx(targets[0], abs=2e-14)
    assert a['last_sample']['target'] == pytest.approx(targets[-1], abs=2e-14)
    assert a['last_sample']['prediction_before_update'] == rows[-1][-1]
    assert a['target_counts']['expected_control_targets'] == 3
    assert a['target_counts'].get('suffix_target_assignments', 0) == 0
    assert a['target_counts']['expected_spawn_outcomes'] == sum(2*list(board).count(0) for board in data['afterstates'])
    assert a['learning_counts']['table_updates'] == len(denominators)*left.banks


def test_condition_basis_preserves_same_p_gain_and_changes_cross_p_sharing():
    source = template()
    board = np.asarray([[2]+[0]*15], dtype=np.int32)
    data = dict(afterstates=np.repeat(board, 3, axis=0), rewards=np.zeros(3),
        model_p_four=np.full(3, .1), terminal_code=1)
    plain, conditioned = core.ResidualHead(source, False, BUILD), core.ResidualHead(source, True, BUILD)
    base = core.predict(plain, board, [.1], BUILD)['predictions'][0]
    core.fit_episode(plain, data, 'MC', BUILD)
    core.fit_episode(conditioned, data, 'MC', BUILD)
    plain_gain = core.predict(plain, board, [.1], BUILD)['predictions'][0]-base
    gain = core.predict(conditioned, np.repeat(board, 2, axis=0), [.1, .5], BUILD)['predictions']-base
    assert gain[0] == pytest.approx(plain_gain, abs=2e-15)
    assert gain[1] == pytest.approx(plain_gain*np.dot(coefficients(.1, True), coefficients(.5, True)), abs=2e-15)
    assert 0. < gain[1] < gain[0]


@pytest.mark.parametrize('conditioned', [False, True])
def test_composite_h2_exactly_matches_materialized_legacy_h2_and_terminal_values(conditioned):
    source = template()
    head = core.ResidualHead(source, conditioned, BUILD)
    boards = np.asarray([[2]+[0]*15, [3, 3]+[0]*14,
        [1, 2, 1, 2, 2, 1, 2, 1]*2, [4]+[0]*15], dtype=np.int32)
    probabilities = np.asarray([.1, .5, .2, .8])
    for nonzero in (False, True):
        if nonzero:
            head.residuals[:] = np.arange(head.residuals.size).reshape(head.residuals.shape) % 9 * .003
        actual = core.score_actions(head, boards, probabilities, BUILD)
        for board, p, choice in zip(boards, probabilities, actual['choices']):
            leaf, receipt = core.materialize(head, float(p), BUILD)
            leaf.rule = replace(leaf.rule, spawn_distribution=((1, Fraction(str(1.-p))), (2, Fraction(str(p)))))
            old = FrozenLeafPlanner(leaf, depth=2, build_dir=BUILD).choose(board)
            assert {k: v for k, v in old.items() if k != 'counts'} == choice
            assert receipt['blending_counts']['effective_table_parameters_scanned'] == source.weights.size*head.banks
            assert receipt['blending_counts']['allocated_blending_scratch_bytes'] == source.weights.nbytes
            assert receipt['setup_counts']['source_parameters_copied'] == source.weights.size
            assert leaf.updates == 0 and not leaf.weights.flags.writeable
        assert actual['choices'][2]['status'] == 'LOST' and actual['choices'][2]['value'] == -4.
        assert actual['choices'][3]['status'] == 'WON' and actual['choices'][3]['value'] == 4.


def test_saved_conditional_parameters_rematerialize_at_new_p_without_later_fit_changes():
    source = template()
    head, saved = core.ResidualHead(source, True, BUILD), core.ResidualHead(source, True, BUILD)
    core.fit_episode(head, game(), 'MC', BUILD)
    np.copyto(saved.residuals, head.residuals); saved.residuals.flags.writeable = False
    at_A, _ = core.materialize(saved, .1, BUILD)
    at_B, _ = core.materialize(saved, .5, BUILD)
    core.fit_episode(head, game(False), 'MC', BUILD)
    after, _ = core.materialize(saved, .5, BUILD)
    np.testing.assert_array_equal(after.weights, at_B.weights)
    assert not np.array_equal(at_A.weights, at_B.weights)
    assert saved.updates == 0 and head.updates == 6
    with pytest.raises(ValueError, match='writable'):
        core.fit_episode(saved, game(), 'MC', BUILD)
