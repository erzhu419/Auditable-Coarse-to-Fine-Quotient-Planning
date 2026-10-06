from copy import deepcopy
from fractions import Fraction as F
from itertools import product

import pytest

from scripts import audit_convex_query_null_v240 as audit


CASE = dict(operating='low', retry_cost='17/20')
COUNTS = {
    'S_D_FULL': {'S': {'DELIVERY': 2, 'LOST': 3},
                 'D_FULL': {'DELIVERY': 2, 'RECOVERY': 1, 'LOST': 3}},
    'D_REC_R': {'D_REC': {'RECOVERY': 2, 'OTHER': 3},
                'R': {'DELIVERY': 3, 'LOST': 2}},
}
POINTS = {
    'S_D_FULL': {'S': {'DELIVERY': F(2, 5), 'LOST': F(3, 5)},
                 'D_FULL': {'DELIVERY': F(1, 3), 'RECOVERY': F(1, 3), 'LOST': F(1, 3)}},
    'D_REC_R': {'D_REC': {'RECOVERY': F(2, 5), 'OTHER': F(3, 5)},
                'R': {'DELIVERY': F(2, 5), 'LOST': F(3, 5)}},
}


@pytest.mark.parametrize('family', ('S_D_FULL', 'D_REC_R'))
def test_complete_domain_support_and_outward_tangent_cover_bad_kernel(family):
    counts, point = COUNTS[family], POINTS[family]
    tangent = audit.tangent_components(CASE, family, counts, point, F(7, 3))
    assert tangent['h_point'] < 0  # The tangent point need not itself be bad.
    if family == 'S_D_FULL':
        residual = tangent['residual_gradient']
        vertices = product(*[list(row) for row in residual.values()])
        direct_support = max(sum(residual[name][category]
            -sum(value*point[name][cat] for cat, value in residual[name].items())
            for name, category in zip(residual, vertex)) for vertex in vertices)
        bad = deepcopy(point)
        bad['S'] = dict(DELIVERY=F(9, 10), LOST=F(1, 10))
        other = 'SHORT'
    else:
        residual = tangent['residual_gradient']
        d, r = point['D_REC']['RECOVERY'], point['R']['DELIVERY']
        direct_support = max(residual['D_REC']*(u-d)+residual['R']*(v-r)
                             for u, v in product((F(0), F(1)), repeat=2))
        bad = {'D_REC': dict(RECOVERY=F(1, 2), OTHER=F(1, 2)),
               'R': dict(DELIVERY=F(9, 10), LOST=F(1, 10))}
        other = 'DETOUR_RETRY'
    assert direct_support == tangent['residual_support']
    assert audit.gap(CASE, other, bad) > audit.REGRET
    log_bad_upper = sum(count*audit.arithmetic.logarithm(bad[name][category])[1]
        for name, row in counts.items() for category, count in row.items())
    assert log_bad_upper < tangent['global_upper']
    # Reversing the support direction is not a valid outward upper bound.
    reversed_support_upper = (tangent['log_likelihood_upper']
        +F(7, 3)*tangent['h_point']-direct_support)
    assert reversed_support_upper < log_bad_upper


def test_feasible_member_is_not_automatically_a_strict_bad_witness():
    counts = {'S': {'DELIVERY': 1, 'LOST': 1},
              'D_FULL': {'DELIVERY': 1, 'RECOVERY': 1, 'LOST': 1}}
    good = POINTS['S_D_FULL']
    assert audit.strict_simplex(good, counts)
    assert audit.fixed_membership(counts, good)[0]
    assert audit.gap(CASE, 'SHORT', good) <= audit.REGRET
    illegal = deepcopy(good)
    illegal['S'] = dict(DELIVERY=F(11, 10), LOST=F(-1, 10))
    assert not audit.strict_simplex(illegal, counts)
    assert audit.fixed_membership(counts, illegal) == (False, None)


def test_negative_multiplier_cannot_support_global_bad_null_bound():
    with pytest.raises(ValueError, match='nonnegative multiplier'):
        audit.tangent_components(CASE, 'D_REC_R', COUNTS['D_REC_R'], POINTS['D_REC_R'], F(-1))
