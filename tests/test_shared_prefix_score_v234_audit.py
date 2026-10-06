"""Audit failures reachable with zero rows, rare recovery and directional gaps."""
from fractions import Fraction as F

from scripts import audit_shared_prefix_score_v234 as audit


def test_predictive_mixture_matches_exact_short_binary_probability():
    assert audit.mixture_weight(0, 0) == 1
    assert audit.mixture_weight(2, 1) == F(1, 8)
    assert audit.mixture_weight(3, 3) == F(5, 16)
    assert audit.mixture_value(2, 1, F(1, 2)) == F(1, 2)
    assert audit.mixture_value(2, 1, F(0)) is None


def test_roots_are_outward_with_exact_threshold_classification():
    for n, k in ((24, 0), (24, 3), (24, 24)):
        result = audit.region(n, k)
        assert 0 <= result['lower'] <= F(k, n) <= result['upper'] <= 1
        for side in ('lower', 'upper'):
            bracket = result[f'{side}_bracket']
            if bracket is None:
                assert result[side] == (0 if side == 'lower' else 1)
                continue
            left, right = bracket
            assert right-left <= F(1, 2**audit.BISECTIONS)
            outside, inside = (left, right) if side == 'lower' else (right, left)
            assert audit.mixture_value(n, k, outside) > audit.EVENT_THRESHOLD
            assert audit.mixture_value(n, k, inside) <= audit.EVENT_THRESHOLD
    assert audit.region(0, 0) == dict(lower=F(0), upper=F(1), lower_bracket=None, upper_bracket=None)


def test_negative_continuation_uses_lower_recovery_for_upper_gap():
    p = dict(lower=F(1, 20), upper=F(1, 5))
    q = dict(lower=F(1, 4), upper=F(1, 3))
    continuation, gap = audit.conditional_bounds(
        'risk', 'DETOUR_RETURN', 'DETOUR_RETRY', '19/20', p, q)
    assert continuation == [F(-59, 20), F(-137, 60)]
    assert gap == [F(-59, 100), F(-137, 1200)]
    reverse_continuation, reverse_gap = audit.conditional_bounds(
        'risk', 'DETOUR_RETRY', 'DETOUR_RETURN', '19/20', p, q)
    assert reverse_continuation == [-continuation[1], -continuation[0]]
    assert reverse_gap == [-gap[1], -gap[0]]


def test_region_audit_rejects_unused_row_counts_and_inward_endpoint():
    operator, success = audit.prior.R, 'DELIVERY'
    queues = {operator: ['DELIVERY']*3+['LOST']*21}
    expected = audit.region(24, 3)
    saved = dict(n=24, k=3, operator=operator, success=success,
                 threshold=3600, bisections=40, kind='exact_rational_bisection',
                 lower=expected['lower'], upper=expected['upper'],
                 lower_bracket=dict(outside=expected['lower_bracket'][0], inside=expected['lower_bracket'][1]),
                 upper_bracket=dict(inside=expected['upper_bracket'][0], outside=expected['upper_bracket'][1]))
    checks = []
    audit.audit_region(queues, operator, success, saved, lambda name, valid: checks.append((name, valid)))
    assert all(valid for _, valid in checks)
    checks = []
    audit.audit_region(queues, operator, success, dict(saved, n=8, upper=F(1, 8)),
                       lambda name, valid: checks.append((name, valid)))
    assert ('full_paid_bernoulli_row', False) in checks
    assert ('exact_outward_interval', False) in checks
