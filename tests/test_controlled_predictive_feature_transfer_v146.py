"""Finite signed-support, rank-deficiency, and projection checks; no sampling."""
from collections import Counter
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_feature_transfer_v146 import TrainingGeometry


ROOT = Path(__file__).resolve().parents[1]
GEOMETRIES = []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_feature_transfer_v146.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        geometry_work=dict(sum((item.counts for item in GEOMETRIES), Counter())),
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        scope='Synthetic signed sparse vectors; no environment, planner or model training.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def geometry(rows):
    result = TrainingGeometry(rows)
    GEOMETRIES.append(result)
    return result


def test_disjoint_query_has_no_support_or_projection():
    model = geometry([{1: 2, 2: -1}, {3: 1}])
    row = model.measure({4: 3})
    assert row['train_rank'] == 2 and row['train_addresses'] == 3
    assert row['covered_addresses'] == row['covered_norm2'] == 0
    assert row['covered_norm_fraction'] == row['projection_fraction'] == 0.
    assert row['max_abs_cosine'] == 0. and row['orthogonal_to_training']


def test_shared_support_can_still_be_orthogonal():
    model = geometry([{1: 1, 2: 1}])
    row = model.measure({1: 1, 2: -1})
    assert row['covered_norm_fraction'] == 1.
    assert row['projection_fraction'] == 0.
    assert row['orthogonal_to_training'] and row['max_abs_cosine'] == 0.


def test_duplicates_and_zero_rows_do_not_inflate_rank():
    model = geometry([{1: 1, 2: -2}, {1: 2, 2: -4}, {}, {9: 0}])
    row = model.measure({1: -3, 2: 6})
    assert row['train_roots'] == 4 and row['nonzero_train_roots'] == 2
    assert row['train_rank'] == 1 and row['train_addresses'] == 2
    assert row['projection_norm2'] == pytest.approx(45.)
    assert row['projection_fraction'] == pytest.approx(1.)
    assert row['max_abs_cosine'] == pytest.approx(1.)
    assert not row['orthogonal_to_training']
    assert model.counts == dict(gram_dot_products=10, eigendecompositions=1,
                                query_measures=1, query_dot_products=4)


def test_zero_query_fraction_is_undefined():
    row = geometry([{1: 1}]).measure({2: 0})
    assert row['zero_feature'] and row['orthogonal_to_training']
    assert row['query_addresses'] == row['query_norm2'] == row['projection_norm2'] == 0
    assert row['projection_fraction'] is None and row['covered_norm_fraction'] is None
    assert row['max_abs_cosine'] == 0.


def test_zero_gram_has_rank_zero_without_eigendecomposition():
    model = geometry([{}, {1: 0}])
    row = model.measure({1: 2})
    assert row['train_rank'] == 0 and row['projection_norm2'] == 0.
    assert row['orthogonal_to_training'] and not row['zero_feature']
    assert model.counts['eigendecompositions'] == 0


def test_full_span_and_known_partial_projection():
    full = geometry([{1: 1, 2: 1}, {1: 1, 2: -1}]).measure({1: 3, 2: -4})
    assert full['train_rank'] == 2 and full['projection_norm2'] == pytest.approx(25.)
    partial = geometry([{1: 1, 2: 1}]).measure({1: 2, 3: 2})
    assert partial['covered_norm_fraction'] == .5
    assert partial['projection_norm2'] == pytest.approx(2.)
    assert partial['projection_fraction'] == pytest.approx(.25)
    assert partial['max_abs_cosine'] == pytest.approx(.5)


def test_zero_initialized_lms_cannot_use_orthogonal_query_component():
    rows = np.array([[1., 1., 0.], [0., 0., 1.]])
    targets = [2., -3.]
    weights = np.zeros(3)
    for _ in range(5):
        for row, target in zip(rows, targets):
            weights += .1*row*(target-row@weights)/(row@row)
    query = np.array([3., -1., 4.])
    projected = np.array([1., 1., 4.])
    assert query@weights == pytest.approx(projected@weights)
    assert (query-projected)@weights == pytest.approx(0.)
    model = geometry([{1: 1, 2: 1}, {3: 1}])
    row = model.measure({1: 3, 2: -1, 3: 4})
    assert row['projection_norm2'] == pytest.approx(projected@projected)
    assert row['projection_fraction'] == pytest.approx(18./26.)


def test_large_projection_error_is_not_hidden_by_clamping():
    model = geometry([{1: 1}])
    model.eigenvalues[0] = .5
    with pytest.raises(ValueError, match='squared-norm bounds'):
        model.measure({1: 1})
