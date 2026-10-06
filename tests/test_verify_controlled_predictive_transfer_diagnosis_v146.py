"""Independent V146 formulas against analytically known finite cases."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_controlled_predictive_transfer_diagnosis_v146 import (
    SVDGeometry, independent_labels, matches)


def test_negative_noise_adjusted_error_and_fixed_split():
    result, partitions = independent_labels([0.]*4+[2.]*4, {'FIXED': 1.})
    assert result['variance'] == pytest.approx(8/7)
    assert result['methods']['FIXED']['noise_adjusted_squared_error'] == pytest.approx(-1/7)
    assert result['methods']['FIXED']['cross_half_squared_error'] == -1
    assert partitions['FIXED'] == pytest.approx(-1/7)
    altered = dict(result, variance=0.)
    assert not matches(altered, result)


def test_strict_gate_and_structural_zero_labels():
    result, partitions = independent_labels([0.]*8, {'TIE': 0., 'POSITIVE': 2.})
    assert result['partitions']['zero_both'] == 1
    assert result['partitions']['gate_agreement'] == 1
    assert not result['methods']['TIE']['select_h1']
    assert result['methods']['POSITIVE']['noise_adjusted_squared_error'] == 4
    assert partitions == {'TIE': 0., 'POSITIVE': 4.}


def test_svd_distinguishes_address_coverage_from_row_span():
    geometry = SVDGeometry([[(1, 1), (2, 1)], [(1, 2), (2, 2)], []])
    result = geometry.measure([(1, 1), (3, 1)])
    assert result['train_rank'] == 1
    assert result['nonzero_train_roots'] == 2
    assert result['covered_norm_fraction'] == .5
    assert result['projection_fraction'] == pytest.approx(.25)
    assert result['max_abs_cosine'] == pytest.approx(.5)
    assert not matches(dict(result, projection_fraction=.5), result)


def test_supported_orthogonal_and_zero_queries():
    geometry = SVDGeometry([[(1, 1), (2, 1)]])
    orthogonal = geometry.measure([(1, 1), (2, -1)])
    assert orthogonal['covered_norm_fraction'] == 1
    assert orthogonal['orthogonal_to_training']
    assert orthogonal['projection_fraction'] == pytest.approx(0, abs=1e-25)
    zero = geometry.measure([])
    assert zero['zero_feature']
    assert zero['covered_norm_fraction'] is None
    assert zero['projection_fraction'] is None
