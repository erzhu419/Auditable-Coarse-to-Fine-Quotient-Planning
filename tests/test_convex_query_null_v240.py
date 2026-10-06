from decimal import Decimal, localcontext
from fractions import Fraction as F
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import convex_query_null_v240 as core
from acfqp.science import joint_query_evidence_v235 as prior


def case(operating='low', retry_cost='17/20'):
    return dict(operating=operating, retry_cost=retry_cost)


LOW_COUNTS = {
    'S_D_FULL': {'S': {'DELIVERY': 1, 'LOST': 1},
                 'D_FULL': {'DELIVERY': 1, 'RECOVERY': 1, 'LOST': 1}},
    'D_REC_R': {'D_REC': {'RECOVERY': 1, 'OTHER': 1}, 'R': {'DELIVERY': 1, 'LOST': 1}},
}
STRONG_COUNTS = {
    'S_D_FULL': {'S': {'DELIVERY': 1, 'LOST': 999},
                 'D_FULL': {'DELIVERY': 998, 'RECOVERY': 1, 'LOST': 1}},
    'D_REC_R': {'D_REC': {'RECOVERY': 500, 'OTHER': 500}, 'R': {'DELIVERY': 1, 'LOST': 999}},
}


@pytest.mark.parametrize('family', ('S_D_FULL', 'D_REC_R'))
def test_exact_repaired_bad_kernel_is_inside_its_full_projected_region(family):
    result = core.classify(LOW_COUNTS[family], case(), family)
    witness = result['repaired_witness']
    assert result['status'] == 'admitted_bad_kernel'
    assert witness['feasible'] and witness['gap'] == core.STRICT_GAP
    assert all(sum(row.values()) == 1 and min(row.values()) >= 0
               for row in witness['parameters'].values())
    other = 'SHORT' if family == 'S_D_FULL' else 'DETOUR_RETRY'
    assert prior.gap(case(), 'risk', 'DETOUR_RETURN', other, witness['parameters']) > F(1, 20)
    assert prior.membership(LOW_COUNTS[family], witness['parameters'])['exact_inside']
    assert not result['global_tangent']['certified']
    # An independently evaluated likelihood of an actual bad point must be
    # below the proposed global tangent upper bound, irrespective of optimizer status.
    with localcontext() as context:
        context.prec = 160
        log_likelihood = sum(Decimal(count)*(Decimal(witness['parameters'][name][category].numerator)
            /Decimal(witness['parameters'][name][category].denominator)).ln()
            for name, row in LOW_COUNTS[family].items() for category, count in row.items())
        upper = result['global_tangent']['global_upper']
        assert log_likelihood <= Decimal(upper.numerator)/Decimal(upper.denominator)


@pytest.mark.parametrize('family', ('S_D_FULL', 'D_REC_R'))
def test_global_tangent_excludes_strong_bad_nulls_with_full_parameter_domain(family):
    result = core.classify(STRONG_COUNTS[family], case('high', '19/20'), family)
    tangent = result['global_tangent']
    assert result['status'] == 'global_bad_null_excluded'
    assert tangent['multiplier'] >= 0 and tangent['certified']
    assert tangent['global_upper'] == (tangent['log_likelihood_upper']
        +tangent['multiplier']*tangent['h_point']+tangent['residual_support'])
    assert tangent['log_e_lower'] > tangent['log_threshold_upper']
    assert not result['repaired_witness']['membership']['exact_inside']
    if family == 'D_REC_R':
        assert tangent['residual_gradient']['R'] == 0
    else:
        assert tangent['residual_gradient']['S']['DELIVERY'] == tangent['residual_gradient']['S']['LOST']
    assert result['projected_counts'] == STRONG_COUNTS[family]


def test_optimizer_success_flag_never_decides_bad_kernel_acceptance(monkeypatch):
    calls = []

    def failed_proposal(*args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(x=np.array(list(map(float, core.STARTS['S_D_FULL']))),
                               success=False, nit=1, message='iteration limit')

    monkeypatch.setattr(core, 'minimize', failed_proposal)
    result = core.classify(LOW_COUNTS['S_D_FULL'], case(), 'S_D_FULL')
    assert len(calls) == 1 and not result['optimizer']['success']
    assert result['status'] == 'admitted_bad_kernel'
    assert result['repaired_witness']['membership']['exact_inside']
