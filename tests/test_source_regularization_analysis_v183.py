"""Pure normalized-ridge and SOURCE-heldout policy tests; no environment draws."""
from collections import Counter
from copy import deepcopy
import math
import numpy as np

from acfqp.science import controlled_predictive_source_regularization_v183 as core
from scripts import analyze_controlled_predictive_source_regularization_v183 as audit


def record(rank):
    board = [rank]+[0]*15
    return dict(aggregate=[0, 16-int(rank > 0), 0, 0, 0, 0],
        tokens=[['cell', i, value] for i, value in enumerate(board)]+
               [['horizontal', i, board[i], board[i+1]] for i in range(16) if i % 4 < 3]+
               [['vertical', i, board[i], board[i+4]] for i in range(12)])


def examples():
    return [dict(root_id=f'r{i:02}', source_id=f'DESIGN_SOURCE:{i:02}', life=0, canonical_board=[0]*16,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': 0., 'LEFT': .25},
        action_components={'DOWN': [0., 0., 0.], 'LEFT': [.75, .25, .5]},
        layout_features={'DOWN': record(0), 'LEFT': record(1+i % 10)}, fallback_action='LEFT',
        action_map={'DOWN': 'DOWN', 'LEFT': 'LEFT'}, teacher_action_native='UP',
        action_component_fractions={'unused': [[99, 1]]}) for i in range(12)]


def test_row_gram_ridge_uses_root_mean_normalization_and_full_vector():
    matrix = np.array([[1., 0., 1.], [0., 1., 0.], [1., 1., 1.]])
    targets = np.array([[1., .2, .3], [2., .7, .1], [.5, .4, .8]])
    work = Counter(); zero, rank, _ = audit.ridge_coefficients(matrix, targets, 7, 0., work)
    assert rank == 2 and np.allclose(zero[0], zero[2], atol=1e-12)
    actual, _, _ = audit.ridge_coefficients(matrix, targets, 7, .1, work)
    augmented = np.vstack([matrix, math.sqrt(.7)*np.eye(3)])
    expected = np.linalg.lstsq(augmented, np.vstack([targets, np.zeros((3, 3))]), rcond=None)[0]
    assert np.allclose(actual, expected, atol=1e-12)
    incorrectly_unscaled = np.linalg.solve(matrix.T@matrix+.1*np.eye(3), matrix.T@targets)
    assert not np.allclose(actual, incorrectly_unscaled)
    assert work['zero_minimum_norm_lstsq_solves'] == work['positive_row_gram_solves'] == 1


def test_fold_vocabulary_support_selection_and_counts_are_independent(monkeypatch):
    rows = examples(); original_choose = audit.previous.choose_action; observations = []
    def observable_only(model, root, counts=None):
        observations.append(set(root))
        assert 'action_components' not in root and 'action_component_fractions' not in root and 'teacher_action_native' not in root
        return original_choose(model, root, counts)
    monkeypatch.setattr(audit.previous, 'choose_action', observable_only)
    expected = core.select_regularization(rows); actual, work = audit.select_regularization(rows)
    assert audit.exact._equal(expected, actual) and audit.exact._equal(actual, expected)
    assert actual['costs'] == expected['costs'] and actual['selected_lambda'] == 0.
    assert len(observations) == 72 and work['zero_minimum_norm_lstsq_solves'] == 3 and work['positive_row_gram_solves'] == 10
    assert all(set(fold['train_sources']).isdisjoint(fold['heldout_sources']) for fold in actual['folds'])
    fold = actual['folds'][0]
    assert ['cell', 0, 1] not in fold['design']['vocabulary'] and ['cell', 0, 2] in fold['design']['vocabulary']
    assert any(choice['decision']['coverage']['LEFT']['unknown_tokens'] > 0 for choice in actual['candidates'][0]['fold_results'][0]['choices'])
    assert actual['costs']['ridge_svd_decompositions'] == 3 and actual['costs']['ridge_predictors_fitted'] == 13


def test_heldout_score_reads_actual_full_vectors_and_equal_source_groups(monkeypatch):
    rows = [deepcopy(examples()[0]) for _ in range(3)]
    for i, row in enumerate(rows):
        row.update(root_id=f'root{i}', source_id='A' if i < 2 else 'B')
        row['action_components']['DOWN'] = [2., .25, .5] if i < 2 else [.1, 1., 0.]
    def frozen_choice(model, observable, counts):
        assert set(observable) <= {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards', 'fallback_action', 'layout_features', 'action_map'}
        return dict(canonical_action='DOWN', predicted_components={'DOWN': [999., 0., 0.]})
    monkeypatch.setattr(audit.previous, 'choose_action', frozen_choice)
    groups, choices, counts = audit.score_heldout({}, rows)
    group_mean = sum(row['utility'] for row in groups)/len(groups)
    root_mean = sum(row['utility'] for row in choices)/len(choices)
    assert math.isclose(group_mean, .675) and math.isclose(root_mean, 1.2)
    assert all(row['utility'] != 999. for row in choices)
    assert counts['heldout_action_vector_reads'] == 3 and counts['heldout_group_component_means'] == 6
