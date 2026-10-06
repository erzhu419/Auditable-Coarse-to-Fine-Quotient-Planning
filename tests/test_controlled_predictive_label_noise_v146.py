"""Finite arithmetic checks; no learned model or environment is sampled."""
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_label_noise_v146 import (
    balanced_partitions, label_diagnostics,
)

ROOT = Path(__file__).resolve().parents[1]
TEMP = ROOT/'reports/v146_runtime_tmp'


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        scope='Synthetic scalar suffix values and fixed predictions only.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def test_balanced_partition_roster_has_all_35_unique_unordered_splits():
    partitions = balanced_partitions()
    assert len(partitions) == 35
    unordered = {frozenset((frozenset(first), frozenset(second)))
                 for first, second in partitions}
    assert len(unordered) == 35
    for first, second in partitions:
        assert len(first) == len(second) == 4
        assert 0 in first and 0 not in second
        assert set(first).isdisjoint(second)
        assert set(first) | set(second) == set(range(8))


def test_unbiased_variance_and_eight_suffix_mean_noise():
    result = label_diagnostics(range(8), {'PRIOR': 2.})
    assert result['n'] == 8
    assert result['mean'] == 3.5
    assert result['variance'] == 6.
    assert result['mean_noise_variance'] == .75
    assert result['methods']['PRIOR']['squared_error'] == 2.25
    assert result['methods']['PRIOR']['noise_adjusted_squared_error'] == 1.5


def test_negative_noise_adjusted_error_is_retained():
    result = label_diagnostics([-1., 1.]*4, {'UPDATED': 0.})
    method = result['methods']['UPDATED']
    assert method['squared_error'] == 0.
    assert method['noise_adjusted_squared_error'] == pytest.approx(-1./7.)
    assert method['cross_half_squared_error'] == 0.
    assert not method['select_h1']


def test_zero_ties_use_strict_positive_gate_and_explicit_sign_categories():
    result = label_diagnostics([0.]*8, {'ZERO': 0., 'POS': 1., 'NEG': -1.})
    fixed = result['fixed_halves']
    assert fixed['means'] == [0., 0.]
    assert fixed['signs'] == [0, 0]
    assert fixed['gates'] == [False, False]
    assert fixed['sign_agreement'] and fixed['gate_agreement'] and fixed['zero_both']
    assert not any(fixed[key] for key in ('positive_both', 'negative_both', 'mixed_sign', 'one_zero'))
    assert result['methods']['POS']['select_h1']
    assert not result['methods']['ZERO']['select_h1']
    assert not result['methods']['NEG']['select_h1']
    one_zero = label_diagnostics([0.]*4+[1.]*4, {})['fixed_halves']
    assert one_zero['one_zero'] and not one_zero['mixed_sign']
    assert not one_zero['sign_agreement'] and not one_zero['gate_agreement']


def test_fixed_half_cross_product_uses_fixed_prediction_twice():
    result = label_diagnostics(range(1, 9), {'REPLAY': 3.})
    fixed = result['fixed_halves']
    assert fixed['indices'] == [[0, 1, 2, 3], [4, 5, 6, 7]]
    assert fixed['means'] == [2.5, 6.5]
    assert result['methods']['REPLAY']['cross_half_squared_error'] == -1.75


def test_all_partition_rates_include_balanced_ties_without_pseudoreplication():
    result = label_diagnostics([1.]*4+[-1.]*4, {})['partitions']
    assert result['count'] == 35 and result['half_count'] == 70
    assert result['zero_both'] == result['sign_agreement'] == 18./35.
    assert result['gate_agreement'] == 18./35.
    assert result['mixed_sign'] == 17./35.
    assert result['positive_both'] == result['negative_both'] == result['one_zero'] == 0.


def test_utility_scaling_preserves_signs_and_scales_errors_quadratically():
    values, predictions = [-2., 1., 3., -1., 4., -3., 2., -4.], {'PRIOR': .25}
    result = label_diagnostics(values, predictions)
    scaled = label_diagnostics([3.*value for value in values], {'PRIOR': .75})
    assert scaled['mean'] == pytest.approx(3.*result['mean'])
    for key in ('variance', 'mean_noise_variance'):
        assert scaled[key] == pytest.approx(9.*result[key])
    for key in ('squared_error', 'noise_adjusted_squared_error', 'cross_half_squared_error'):
        assert scaled['methods']['PRIOR'][key] == pytest.approx(9.*result['methods']['PRIOR'][key])
    assert scaled['partitions'] == result['partitions']
    assert scaled['fixed_halves']['signs'] == result['fixed_halves']['signs']
