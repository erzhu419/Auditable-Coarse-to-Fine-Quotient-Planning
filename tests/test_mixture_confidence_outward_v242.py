"""Regression checks for V242's actually reached scalar projection defect."""
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction as F

import pytest

from acfqp.science import mixture_confidence_v225 as core
from scripts.audit_joint_gap_v230 import binary_interval


def assert_independent_outer(k, n, threshold):
    region = dict(counts=dict(DELIVERY=k, LOST=n-k), threshold=threshold)
    reference_low, reference_high = binary_interval([region])
    low, high = core.interval(k, n, Counter(), threshold)
    with localcontext() as ctx:
        ctx.prec = 100
        assert Decimal(low.numerator)/Decimal(low.denominator) <= reference_low
        assert Decimal(high.numerator)/Decimal(high.denominator) >= reference_high
    assert low <= F(k, n) <= high
    assert (low*core.evidence.robust.GRID).denominator == 1
    assert (high*core.evidence.robust.GRID).denominator == 1


def test_jeffreys_normalizer_keeps_the_frozen_prior():
    assert core._mixture_normalizer(1, 2) == F(1, 8)
    assert core._mixture_normalizer(0, 0) == F(1)


@pytest.mark.parametrize('k,n,threshold', [(202, 704, 720), (452, 608, 720),
                                        (526, 576, 720), (773, 848, 720),
                                        (1587, 1744, 720)])
def test_actual_v242_under_enclosed_inputs_enclose_independent_roots(k, n, threshold):
    assert_independent_outer(k, n, threshold)


@pytest.mark.parametrize('k,n,threshold', [(0, 16, 8640), (16, 16, 8640),
                                        (0, 128, 720), (128, 128, 720)])
def test_zero_count_category_endpoints_enclose_independent_roots(k, n, threshold):
    assert_independent_outer(k, n, threshold)
    low, high = core.interval(k, n, Counter(), threshold)
    if k == 0:
        assert low == 0
    else:
        assert high == 1


def test_empty_observed_row_keeps_the_whole_simplex():
    assert core.interval(0, 0, Counter(), 8640) == (F(0), F(1))
