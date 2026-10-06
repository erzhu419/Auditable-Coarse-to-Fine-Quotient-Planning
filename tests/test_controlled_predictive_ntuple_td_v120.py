"""Synthetic differential checks for tuple lookup, TD, and identified dynamics."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_ntuple_td_v120 import (
    ACTIONS, ALPHA, NtupleValue, PATTERNS)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import (
    LearnedDynamics, RewriteProgram)

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/controlled_predictive_ntuple_td_v120_build'
MODELS, REFERENCE_WORK = [], Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_ntuple_td_v120.checks.json'
    payload = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    work, setup = Counter(), Counter()
    for model in MODELS:
        work.update(model.counts)
        setup.update(model.setup_counts)
    payload['attempts'].append(dict(tests=5, failures=request.session.testsfailed-before,
        development_work=dict(work), setup_work=dict(setup),
        reference_model_work=dict(REFERENCE_WORK),
        setup_seconds=sum(model.setup_seconds for model in MODELS),
        serialization_seconds=sum(getattr(model, 'last_save_seconds', 0.0)
            + getattr(model, 'last_load_seconds', 0.0) for model in MODELS),
        newly_sampled_environment_transitions=0, tree_fits=0,
        optimizer_steps=sum(model.updates for model in MODELS
                            if not hasattr(model, 'loaded_setup_counts')),
        scope='Synthetic tuple values, scalar TD updates, and identified rule swipes; no environment sampling.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def rule(goal=4, reward='output_value'):
    return LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', reward),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', goal)


def model(dynamics=None):
    result = NtupleValue(dynamics or rule(), BUILD)
    MODELS.append(result)
    return result


def python_indices(board, radix):
    grid = np.asarray(board).reshape(4, 4)
    indices = []
    for base, pattern in enumerate(PATTERNS):
        for reflect in (False, True):
            for rotations in range(4):
                transformed = np.rot90(np.fliplr(grid) if reflect else grid, rotations)
                address = 0
                for cell in pattern:
                    address = address*radix + int(transformed.reshape(-1)[cell])
                indices.append(base*radix**6 + address)
    return indices


def reference_value(board, fitted):
    indices = python_indices(board, fitted.radix)
    return sum(float(fitted.weights.reshape(-1)[index]) for index in indices)


def test_lookup_matches_python_and_all_symmetries():
    fitted = model()
    fitted.weights[:] = (np.arange(fitted.weights.size).reshape(fitted.weights.shape) % 97)*.03125
    rng = np.random.default_rng(120)
    for _ in range(8):
        board = rng.integers(0, fitted.radix, 16)
        expected = reference_value(board, fitted)
        assert sorted(fitted.feature_indices(board)) == sorted(python_indices(board, fitted.radix))
        assert fitted.value(board) == expected
        for reflect in (False, True):
            for rotations in range(4):
                grid = board.reshape(4, 4)
                transformed = np.rot90(np.fliplr(grid) if reflect else grid, rotations)
                assert fitted.value(transformed.reshape(-1)) == expected
    assert fitted.updates == 0


def test_update_uses_one_error_and_duplicate_multiplicity():
    fitted = model()
    board = (1,)*16
    error = fitted.update(board, 1.0)
    indices, multiplicities = np.unique(fitted.feature_indices(board), return_counts=True)
    assert multiplicities.tolist() == [8]*4
    assert error == 1.0
    np.testing.assert_array_equal(fitted.weights.reshape(-1)[indices], [.02]*4)
    assert fitted.value(board) == pytest.approx(.64)
    assert fitted.counts['table_updates'] == 4
    assert fitted.counts['table_update_occurrences'] == 32
    # A nonuniform board also has repeated addresses; updates use its one old value.
    board = (1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    before = fitted.weights.copy().reshape(-1)
    old_value = fitted.value(board)
    indices, multiplicities = np.unique(fitted.feature_indices(board), return_counts=True)
    expected = before.copy()
    expected[indices] += ALPHA*(2.0-old_value)*multiplicities
    assert fitted.update(board, 2.0) == 2.0-old_value
    np.testing.assert_array_equal(fitted.weights.reshape(-1), expected)
    assert fitted.updates == 2


def test_choose_matches_supplied_program_and_query_coefficients():
    boards = [(1, 0, 0, 0)+(0,)*12,
              (1, 1, 2, 0, 2, 3, 1, 0, 0, 2, 2, 0, 3, 0, 1, 0),
              (3, 3, 0, 0)+(0,)*12]
    query = dict(reward_weight=2.5, goal_bonus=7.0, failure_penalty=3.0)
    for reward in ('count', 'output_value'):
        fitted = model(rule(reward=reward))
        fitted.weights[:] = (np.arange(fitted.weights.size).reshape(fitted.weights.shape) % 31)*.03125
        for board in boards:
            expected = {}
            for action in ACTIONS:
                afterstate, score, changed = fitted.rule.swipe(board, action, REFERENCE_WORK)
                if changed:
                    tail = (query['goal_bonus'] if max(afterstate) >= fitted.radix
                            else reference_value(afterstate, fitted))
                    expected[action] = dict(afterstate=list(afterstate), score=score,
                        tail_value=tail, value=query['reward_weight']*score/2048 + tail)
            actual = fitted.choose(board, query)
            assert actual['action_values'] == expected
            assert actual['action'] == max(expected, key=lambda a: expected[a]['value'])
            assert actual['score'] == expected[actual['action']]['score']
            assert actual['value'] == expected[actual['action']]['value']
        assert fitted.updates == 0
    zero = model()
    assert zero.choose(boards[0], query)['action'] == 'DOWN'


def test_goal_ranks_bypass_tables_and_terminal_loss_is_analytic():
    fitted = model(rule(goal=11))
    assert fitted.weights.size == 7_086_244
    assert fitted.weights.nbytes == 56_689_952
    query = dict(reward_weight=1., goal_bonus=4., failure_penalty=2.)
    goal_board = (11,)+(1,)*15
    result = fitted.choose(goal_board, query)
    assert result['status'] == 'WON' and result['value'] == 4.
    assert result['action'] is None and not result['action_values']
    assert fitted.counts['table_lookups'] == 0
    with pytest.raises(ValueError, match='terminal goals'):
        fitted.value(goal_board)
    with pytest.raises(ValueError, match='terminal goals'):
        fitted.update(goal_board, 4.)
    result = fitted.choose((10, 10, 0, 0)+(0,)*12, query)
    for action in ('LEFT', 'RIGHT'):
        assert result['action_values'][action]['tail_value'] == 4.
        assert result['action_values'][action]['value'] == 5.
    dead = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
    result = fitted.choose(dead, query)
    assert result['status'] == 'LOST' and result['value'] == -2.
    assert result['action'] is None


def test_sparse_roundtrip_and_evaluation_leave_weights_unchanged():
    fitted = model()
    board = (1, 1, 0, 0)+(0,)*12
    fitted.update(board, 2.)
    path = BUILD / 'test_ntuple_checkpoint_v120.npz'
    saved = fitted.save(path)
    assert saved['parameter_count'] == fitted.weights.size
    assert saved['nonzero_weights'] == len(np.unique(fitted.feature_indices(board)))
    with np.load(path, allow_pickle=False) as data:
        assert set(data.files) == {'indices', 'values', 'metadata'}
        assert len(data['values']) == saved['nonzero_weights']
        metadata = json.loads(str(data['metadata']))
        assert metadata['updates'] == fitted.updates
    restored = NtupleValue.load(path, fitted.rule, BUILD)
    # Avoid counting inherited operations as new development work in the ledger.
    restored.counts = Counter(checkpoint_loads=1,
                              checkpoint_loaded_parameters=saved['nonzero_weights'])
    MODELS.append(restored)
    np.testing.assert_array_equal(restored.weights, fitted.weights)
    before, updates = restored.weights.copy(), restored.updates
    query = dict(reward_weight=1., failure_penalty=1., goal_bonus=2.)
    assert restored.choose(board, query)['action_values'] == fitted.choose(board, query)['action_values']
    assert restored.value(board) == fitted.value(board)
    np.testing.assert_array_equal(restored.weights, before)
    assert restored.updates == updates == fitted.updates
