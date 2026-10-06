"""Reachable failures in the independent certificate arithmetic."""
from fractions import Fraction as F
from copy import deepcopy

import pytest

from scripts import audit_kernel_query_profile_v232 as audit
from acfqp.science import kernel_query_profile_v232 as producer


def test_row_dual_zero_multiplier_encloses_binary_empirical_likelihood():
    counts = {'DELIVERY': 8, 'LOST': 2}
    coefficients = {'DELIVERY': F(7), 'LOST': F(-2)}
    upper = audit.row_dual_upper(counts, coefficients, F(0), F(10))
    likelihood = 8*audit.logarithm(F(4, 5))[1]+2*audit.logarithm(F(1, 5))[1]
    assert upper == likelihood
    assert audit.row_dual_upper(counts, coefficients, F(0), F(11)) > upper


def test_illegal_lagrange_sign_and_dual_boundary_are_rejected():
    counts = {'DELIVERY': 8, 'LOST': 2}
    coefficients = {'DELIVERY': F(7), 'LOST': F(-2)}
    with pytest.raises(ValueError):
        audit.row_dual_upper(counts, coefficients, F(-1), F(10))
    with pytest.raises(ValueError):
        audit.row_dual_upper(counts, coefficients, F(1), F(7))


def test_retry_interval_bounds_use_clamped_empirical_mean_and_zero_rows():
    counts = {'DELIVERY': 8, 'LOST': 2}
    constrained = audit.retry_likelihood_upper(counts, (F(0), F(1, 2)))
    assert constrained == 10*audit.logarithm(F(1, 2))[1]
    unconstrained = audit.retry_likelihood_upper(counts, (F(1, 2), F(1)))
    assert constrained < unconstrained
    assert audit.retry_likelihood_upper(dict(DELIVERY=0, LOST=0), (F(0), F(1))) == 0


def test_bilinear_classifier_uses_complete_mechanics():
    case = dict(operating='low', retry_cost='17/20')
    assert not audit.bilinear(case, 'reward', 'WAIT', 'DETOUR_RETRY')
    assert not audit.bilinear(case, 'goal', 'SHORT', 'DETOUR_RETURN')
    assert audit.bilinear(case, 'goal', 'SHORT', 'DETOUR_RETRY')
    assert audit.bilinear(case, 'risk', 'DETOUR_RETRY', 'SHORT')


def test_complete_bilinear_certificate_is_audited_and_missing_cell_detected():
    case = dict(operating='high', retry_cost='19/20')
    counts = dict(SHORT_PASS=dict(DELIVERY=350, LOST=34),
                  DETOUR_PASS=dict(DELIVERY=326, LOST=4, RECOVERY=54),
                  RECOVERY_RETRY=dict(DELIVERY=96, LOST=288))
    prefix = dict(operators=list(audit.OPERATORS), counts=counts, threshold=480)
    certificate = producer.certificate(case, 'goal', 'SHORT', 'DETOUR_RETRY', counts)
    assert certificate['partitions'] == 32
    checks = []
    audit.audit_certificate(case, 'goal', 'SHORT', 'DETOUR_RETRY', prefix, certificate,
                            lambda name, valid: checks.append((name, valid)))
    assert all(valid for _, valid in checks)
    tampered = deepcopy(certificate)
    tampered['leaves'].pop()
    failures = []
    audit.audit_certificate(case, 'goal', 'SHORT', 'DETOUR_RETRY', prefix, tampered,
                            lambda name, valid: failures.append((name, valid)))
    assert ('fixed_partition_covers_full_retry_simplex', False) in failures


def test_empty_reward_null_is_proved_without_data():
    case = dict(operating='high', retry_cost='19/20')
    counts = {op: dict.fromkeys(cats, 0) for op, cats in audit.ALPHABETS.items()}
    prefix = dict(operators=list(audit.OPERATORS), counts=counts, threshold=480)
    certificate = producer.certificate(case, 'reward', 'WAIT', 'SHORT', counts)
    checks = []
    certified = audit.audit_certificate(case, 'reward', 'WAIT', 'SHORT', prefix, certificate,
                                        lambda name, valid: checks.append((name, valid)))
    assert certified and certificate['witness_kind'] == 'empty_global_bad_null'
    assert all(valid for _, valid in checks)

