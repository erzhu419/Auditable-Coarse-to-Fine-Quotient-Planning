from collections import Counter
from fractions import Fraction as F
import pytest

from acfqp.science import joint_gap_v230 as gap


def test_exact_mixture_martingale_step():
    # Detects a wrong Dirichlet normalizer, which would invalidate Ville.
    for counts in ((2, 3), (2, 3, 1), (0, 0, 0)):
        current = gap.mixture_normalizer(counts)
        n, k = sum(counts), len(counts)
        ratios = []
        for c in range(k):
            later = list(counts)
            later[c] += 1
            ratio = gap.mixture_normalizer(tuple(later))/current
            assert ratio == F(2*counts[c]+1, 2*n+k)
            ratios.append(ratio)
        assert sum(ratios) == 1
    assert gap.mixture_normalizer((1, 1)) == F(1, 8)


def test_dual_support_over_joint_intersection():
    # Detects an unsafe support calculation, including wrong Lagrange signs.
    regions = [gap.region({'a': 32, 'b': 4, 'c': 12}, 720),
               gap.region({'a': 66, 'b': 6, 'c': 24}, 720)]
    weights = {'a': F(3), 'b': F(-2), 'c': F(1)}
    answer = gap.support(regions, weights, Counter())
    witness = answer['witness']
    assert witness['kind'] == 'likelihood_dual'
    assert gap.dual_upper(regions, weights, witness['lambdas'], witness['nu']) == answer['upper']
    assert answer['upper'] < 3
    # Exact likelihood checks on a supported lattice; no optimization result
    # is treated as proof of an upper bound.
    found = 0
    for a in range(1, 40):
        for b in range(1, 40-a):
            p = {'a': F(a, 40), 'b': F(b, 40), 'c': F(40-a-b, 40)}
            if all(gap.mixture_normalizer(tuple(r['counts'].values()))
                   <= r['threshold']*product_probability(p, r['counts']) for r in regions):
                found += 1
                assert sum(weights[c]*p[c] for c in p) <= answer['upper']
    assert found


def product_probability(p, counts):
    value = F(1)
    for c, count in counts.items():
        value *= p[c]**count
    return value


def test_dual_rejects_invalid_witness_and_zero_samples():
    # Invalid witnesses must not silently become certificates.
    r = gap.region({'a': 0, 'b': 0}, 8640)
    assert gap.interval([r], 'a') == [0, 1]
    with pytest.raises(ValueError):
        gap.dual_upper([r], {'a': 1, 'b': 0}, [-1], 2)
    with pytest.raises(ValueError):
        gap.dual_upper([r], {'a': 1, 'b': 0}, [1], 1)
    # Zero observed LOST categories occur in the actual source interface.
    sparse = gap.region({'a': 350, 'b': 0, 'c': 34}, 720)
    answer = gap.support([sparse], {'a': 0, 'b': 1, 'c': 0})
    assert 0 < answer['upper'] < 1


def test_query_gaps_bound_supported_same_kernel():
    # Detects loss of detour/retry dependence or the wrong utility weights.
    case = dict(operating='high', retry_cost='17/20')
    counts = ({'DELIVERY': 36, 'LOST': 4},
              {'DELIVERY': 34, 'LOST': 1, 'RECOVERY': 5},
              {'DELIVERY': 12, 'LOST': 28})
    regions = {op: [gap.region(row, 720)] for op, row in zip(gap.OPERATORS, counts)}
    kernel = {op: {cat: F(value, sum(row.values())) for cat, value in row.items()}
              for op, row in zip(gap.OPERATORS, counts)}
    vectors = gap.route.vectors(case, kernel)
    chosen = {q: dict(policy=min(gap.POLICIES, key=lambda p:(-gap._utility(vectors[p], w),p)))
              for q,w in gap.WEIGHTS.items()}
    certificates = gap.certificates(case, regions, chosen)
    for q,w in gap.WEIGHTS.items():
        selected = chosen[q]['policy']
        actual = max(gap._utility(vectors[p], w)-gap._utility(vectors[selected], w)
                     for p in gap.POLICIES)
        assert actual <= certificates['queries'][q]['regret_upper']
    assert len(certificates['support_records']) == 36


def test_observed_distinct_source_member_is_explicitly_empty():
    # Real supported sources differ strongly in SHORT success; impossible
    # source/member intersections must not produce out-of-simplex corners.
    op_s, op_d, op_r = gap.OPERATORS
    constraints = {
        op_s: [gap.region({'DELIVERY': 380, 'LOST': 4}, 720),
               gap.region({'DELIVERY': 128, 'LOST': 128}, 8640)],
        op_d: [gap.region({'DELIVERY': 100, 'LOST': 1, 'RECOVERY': 27}, 720)],
        op_r: [gap.region({'DELIVERY': 35, 'LOST': 93}, 720)]}
    chosen = {q: dict(policy='WAIT') for q in gap.WEIGHTS}
    result = gap.certificates(dict(operating='high', retry_cost='17/20'), constraints, chosen)
    assert result['empty']
    assert result['empty_proof']['operators'] == [op_s]
    assert result['support_records'] == []
    assert not result['all_ready']
    assert all(not row['certified'] for row in result['queries'].values())
