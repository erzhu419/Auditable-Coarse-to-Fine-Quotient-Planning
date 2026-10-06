"""Small observable/linear-algebra fixtures; no stochastic environment calls."""
from collections import Counter
from copy import deepcopy
import math
import numpy as np
import pytest

from acfqp.science import controlled_predictive_rank_layout_consequences_v182 as core
from scripts import analyze_controlled_predictive_rank_layout_consequences_v182 as audit


def record(rank):
    board = [rank]+[0]*15
    return dict(aggregate=[0, 16-int(rank > 0), 0, 0, 0, 0],
                tokens=[['cell', i, value] for i, value in enumerate(board)]+
                       [['horizontal', i, board[i], board[i+1]] for i in range(16) if i % 4 < 3]+
                       [['vertical', i, board[i], board[i+4]] for i in range(12)])


@pytest.fixture(scope='module')
def fitted():
    examples = [dict(root_id=f'r{i:02}', source_id=f'DESIGN_SOURCE:{i:02}', life=0, canonical_board=[0]*16,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': 0., 'LEFT': .25},
        action_components={'DOWN': [0., 0., 0.], 'LEFT': [.75, .25, .5]},
        layout_features={'DOWN': record(0), 'LEFT': record(1)}, fallback_action='LEFT',
        action_map={'DOWN': 'DOWN', 'LEFT': 'LEFT'}, provenance={}) for i in range(12)]
    return examples, audit.fit_model(examples), core.fit_model(examples)


def test_observable_tokens_keep_zero_ranks_rotation_and_cache(monkeypatch):
    board = tuple(range(16)); rotated = audit.rotate_down(board, 'RIGHT')
    assert rotated == (12, 8, 4, 0, 13, 9, 5, 1, 14, 10, 6, 2, 15, 11, 7, 3)
    root = dict(canonical_board=[0, 1, 0, 2, 3, 0, 4, 0, 0, 5, 0, 6, 7, 0, 8, 0])
    work = Counter(); features = audit.action_features_from_root(root, work)
    expected_work = Counter(); expected = core.action_features_from_root(root, expected_work)
    assert features == expected and work == expected_work and work['layout_ground_swipe_calls'] == 4
    for row in features.values():
        assert len(row['tokens']) == 40 and any(token[-1] == 0 for token in row['tokens'])
        assert row['tokens'][16][0:2] == ['horizontal', 0] and row['tokens'][28][0:2] == ['vertical', 0]
        for kind in ('cell', 'horizontal', 'vertical'):
            assert math.isclose(sum(audit.token_weight(token)**2 for token in row['tokens'] if token[0] == kind), 1.)
    cached = dict(root, layout_features=deepcopy(features))
    monkeypatch.setattr(audit, 'swipe', lambda *args: pytest.fail('cache must avoid deterministic swipes'))
    returned = audit.action_features_from_root(cached); returned['DOWN']['tokens'][0][-1] = 99
    assert cached['layout_features'] == features


def test_sparse_weighted_complete_vector_fit_matches_independent_svd(fitted):
    _, model, production = fitted
    assert audit.exact._equal(model, production) and audit.exact._equal(production, model)
    assert model['rank'] == 1 and len(model['vocabulary']) == 43 and model['design_format'] == 'sparse_columns'
    assert np.allclose(model['coefficients'][1], [-12/35, -6/35, -12/35], atol=1e-12)
    assert model['fit_residuals'][0]['components'] == [-.5, -.25, -.5]
    assert all(row['weight'] == 1. and row['weighted_loss'] < 1e-20 for row in model['fit_residuals'])
    assert all(model[key] == production[key] for key in ('fit_counts', 'feature_counts', 'encoder_counts'))
    assert model['fit_counts']['layout_lstsq_solves'] == 1 and model['feature_counts']['layout_feature_cache_hits'] == 12


def test_unseen_target_tokens_are_zero_contributions_without_fallback(fitted):
    examples, model, production = fitted
    target = deepcopy(examples[0]); target['layout_features']['LEFT'] = record(2)
    original = deepcopy(model['vocabulary']); decision = audit.choose_action(model, target); actual = core.choose_action(production, target)
    assert audit.exact._equal(decision, actual) and audit.exact._equal(actual, decision)
    assert decision['coverage']['LEFT'] == dict(known_tokens=37, unknown_tokens=3, total_tokens=40)
    assert not decision['fallback'] and decision['canonical_action'] == 'LEFT'
    assert model['vocabulary'] == original and ['cell', 0, 2] not in original
    encoded, _ = audit.encode_action(target['layout_features']['LEFT'], audit.vocabulary_index(original, Counter()), Counter())
    predicted = [sum(value*model['coefficients'][column][k] for column, value in encoded.items()) for k in range(3)]
    predicted[0] += target['immediate_rewards']['LEFT']
    assert np.allclose(predicted, decision['predicted_components']['LEFT'], atol=1e-12)
