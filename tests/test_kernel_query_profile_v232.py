from copy import deepcopy
from fractions import Fraction as F
from math import log

from acfqp.science import kernel_query_profile_v232 as profile


CASE = {'operating': 'low', 'retry_cost': F(17, 20)}
S, D, R = profile.OPERATORS


def counts(short=(800, 200), detour=(900, 50, 50), retry=(500, 500)):
    return {S: dict(zip(profile.ALPHABETS[S], short)),
            D: dict(zip(('DELIVERY', 'RECOVERY', 'LOST'), detour)),
            R: dict(zip(profile.ALPHABETS[R], retry))}


def test_linear_bad_null_is_excluded_by_an_outward_dual():
    observed = counts()
    original = deepcopy(observed)
    result = profile.certificate(CASE, 'risk', 'DETOUR_RETURN', 'SHORT', observed)
    assert result['status'] == 'certified'
    assert result['partitions'] == 1
    assert result['log_e_lower'] > result['log_threshold_upper']
    assert observed == original
    leaf = result['leaves'][0]
    assert leaf['multiplier'] >= 0
    for operator, witness in leaf['row_witnesses'].items():
        assert witness['nu'] > max(leaf['multiplier']*coefficient
                                   for coefficient in leaf['gap_coefficients'][operator].values())


def test_retry_partition_covers_boundaries_and_relaxes_shared_kernel_gap():
    result = profile.certificate(CASE, 'goal', 'DETOUR_RETRY', 'DETOUR_RETURN',
                                 counts(short=(700, 300), detour=(800, 150, 50),
                                        retry=(900, 100)))
    assert result['status'] == 'certified'
    assert result['partitions'] == 32
    assert result['leaves'][0]['retry_interval'][0] == 0
    assert result['leaves'][-1]['retry_interval'][1] == 1
    for left, right in zip(result['leaves'], result['leaves'][1:]):
        assert left['retry_interval'][1] == right['retry_interval'][0]
    for leaf in result['leaves']:
        for retry in leaf['retry_interval']:
            kernel = profile._kernel(short=F(1, 3), delivery=F(1, 2),
                                     recovery=F(1, 3), retry=retry)
            relaxed = leaf['gap_constant']+sum(
                coefficient*kernel[op][cat]
                for op, row in leaf['gap_coefficients'].items()
                for cat, coefficient in row.items())
            assert relaxed >= profile.gap(CASE, 'goal', 'DETOUR_RETRY',
                                         'DETOUR_RETURN', kernel)


def test_bad_null_at_mle_returns_unknown_with_exact_negative_witness():
    result = profile.certificate(CASE, 'goal', 'SHORT', 'DETOUR_RETURN', counts())
    assert result['status'] == 'unknown'
    assert result['witness_kind'] == 'bad_null_mle'
    assert result['bad_null_gap'] >= F(1, 20)
    assert profile.gap(CASE, 'goal', 'SHORT', 'DETOUR_RETURN',
                       result['bad_null_kernel']) == result['bad_null_gap']


def test_non_mle_bad_kernel_inside_event_cannot_be_certified():
    observed = counts(short=(600, 400), detour=(600, 0, 400), retry=(0, 0))
    kernel = profile._kernel(short=F(31, 50), delivery=F(59, 100),
                             recovery=F(1, 2000), retry=F(1, 2))
    likelihood, mixture = F(1), F(1)
    for operator, row in observed.items():
        mixture *= profile.joint.mixture_normalizer(tuple(row.values()))
        for category, count in row.items():
            likelihood *= kernel[operator][category]**count
    assert mixture <= 480*likelihood
    assert profile.gap(CASE, 'goal', 'DETOUR_RETURN', 'SHORT', kernel) > F(1, 20)
    result = profile.certificate(CASE, 'goal', 'DETOUR_RETURN', 'SHORT', observed)
    assert result['witness_kind'] == 'global_likelihood_dual'
    assert result['status'] == 'unknown'


def test_row_dual_dominates_realizable_likelihood_including_zero_count_category():
    row = {'A': 3, 'B': 0, 'C': 2}
    coefficients = {'A': F(-2), 'B': F(3), 'C': F(1, 2)}
    multiplier, nu = F(2), F(7)
    upper = profile._row_dual_upper(row, coefficients, multiplier, nu)
    for probabilities in [(F(1, 5), F(3, 10), F(1, 2)),
                          (F(3, 5), F(0), F(2, 5))]:
        likelihood = sum(k*log(float(p)) for k, p in zip(row.values(), probabilities) if k)
        weighted = sum(a*p for a, p in zip(coefficients.values(), probabilities))
        assert float(upper) >= likelihood+float(multiplier*weighted)


def test_missing_likelihood_row_remains_free_not_fixed_to_observed_counts():
    observed = counts(short=(980, 20), detour=(20, 0, 980), retry=(0, 0))
    all_rows = profile.certificate(CASE, 'goal', 'SHORT', 'DETOUR_RETURN', observed)
    inherited = profile.certificate(CASE, 'goal', 'SHORT', 'DETOUR_RETURN', observed,
                                    operators=(S, R))
    assert all_rows['status'] == 'certified'
    assert inherited['status'] == 'unknown'
    assert not any(inherited['counts'][D].values())
    assert all(leaf['row_witnesses'][D]['kind'] == 'free_simplex'
               for leaf in inherited['leaves'])


def test_project_zero_sample_prefix_is_supported_and_not_spuriously_certified():
    observed = counts(short=(0, 0), detour=(0, 0, 0), retry=(0, 0))
    uncertain = profile.certificate(CASE, 'risk', 'WAIT', 'SHORT', observed)
    impossible = profile.certificate(CASE, 'reward', 'WAIT', 'SHORT', observed)
    assert uncertain['status'] == 'unknown'
    assert impossible['status'] == 'certified'
    assert impossible['witness_kind'] == 'empty_global_bad_null'
    assert all(leaf['maximum_relaxed_gap'] < F(1, 20) for leaf in impossible['leaves'])
