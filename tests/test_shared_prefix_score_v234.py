from fractions import Fraction as F
from itertools import product
from math import factorial

from acfqp.science import paired_query_score_v233 as direct
from acfqp.science import shared_prefix_score_v234 as shared


def case(operating='low', retry_cost='17/20'):
    return dict(operating=operating, retry_cost=retry_cost)


def rows(detour, retry):
    return {shared.OPERATORS[0]: ('DELIVERY',) * 128,
            shared.OPERATORS[1]: tuple(detour), shared.OPERATORS[2]: tuple(retry)}


def test_jeffreys_sequence_likelihood_matches_exact_beta_identity():
    for n in range(13):
        for k in range(n + 1):
            rising_half = lambda count: F(factorial(2 * count), 4**count * factorial(count))
            beta_ratio = rising_half(k) * rising_half(n - k) / factorial(n)
            assert shared.mixture_likelihood(n, k) == beta_ratio


def test_boundary_rows_and_empty_rows_have_exact_outer_enclosures():
    empty = shared.bernoulli_region(0, 0)
    assert (empty['lower'], empty['upper']) == (0, 1)
    assert empty['lower_bracket']['outside'] is None
    assert empty['upper_bracket']['outside'] is None
    failures = shared.bernoulli_region(128, 0)
    successes = shared.bernoulli_region(128, 128)
    assert failures['lower'] == 0
    assert successes['upper'] == 1
    assert 0 < failures['upper'] < F(1, 10)
    assert successes['lower'] == 1 - failures['upper']


def test_bisection_records_accepted_and_rejected_endpoints_exactly():
    for n, k in ((64, 0), (64, 64), (79, 23)):
        interval = shared.bernoulli_region(n, k)
        mixture = shared.mixture_likelihood(n, k)
        assert interval['lower'] <= F(k, n) <= interval['upper']
        for bracket in (interval['lower_bracket'], interval['upper_bracket']):
            assert shared.accepted_probability(bracket['inside'], n, k, mixture)
            if bracket['outside'] is not None:
                assert not shared.accepted_probability(bracket['outside'], n, k, mixture)
                assert abs(bracket['inside'] - bracket['outside']) <= F(1, 2**40)


def test_factorization_matches_exact_expected_scores_for_both_signs_and_costs():
    kernels = {direct.OPERATORS[1]: {'DELIVERY': F(1, 2), 'LOST': F(1, 5), 'RECOVERY': F(3, 10)},
               direct.OPERATORS[2]: {'DELIVERY': F(4, 5), 'LOST': F(1, 5)}}
    for query, retry_cost, chosen in product(shared.QUERIES, ('17/20', '19/20'), shared.SHARED_POLICIES):
        other = next(policy for policy in shared.SHARED_POLICIES if policy != chosen)
        score = direct.score_spec(query, chosen, other, retry_cost)
        expected = sum(F(units, 20) * kernels[direct.OPERATORS[1]][values[0]]
                       * kernels[direct.OPERATORS[2]][values[1]] for values, units in score.score_table)
        failure, delivery = direct.WEIGHTS[query]
        direction = 1 if other == 'DETOUR_RETRY' else -1
        continuation = direction * ((failure + delivery) * F(4, 5) - failure - F(retry_cost))
        assert expected == F(3, 10) * continuation
        assert direct.constant_gap(score, case('low', retry_cost)) == 0
        assert direct.constant_gap(score, case('high', retry_cost)) == 0


def test_shared_comparison_uses_all_retry_observations_with_unequal_row_lengths():
    # The first 128 retry entries all fail, but the remaining paid entries
    # alter the continuation direction. Discarding them would falsely pass.
    sequences = rows(('RECOVERY',) * 128, ('LOST',) * 128 + ('DELIVERY',) * 384)
    result = shared.shared_comparison(sequences, case(), 'goal', 'DETOUR_RETURN', 'DETOUR_RETRY')
    assert result['n_by_row'] == {shared.OPERATORS[1]: 128, shared.OPERATORS[2]: 512}
    assert result['k_by_row'][shared.OPERATORS[2]] == 384
    assert not result['certified']
    sequences[shared.OPERATORS[2]] = sequences[shared.OPERATORS[2]][:128]
    prefix = shared.shared_comparison(sequences, case(), 'goal', 'DETOUR_RETURN', 'DETOUR_RETRY')
    assert prefix['certified']


def test_rectangle_handles_negative_continuation_and_reverse_policy_gap():
    sequences = rows(('RECOVERY',) * 64 + ('DELIVERY',) * 64, ('LOST',) * 512)
    forward = shared.shared_comparison(sequences, case(), 'risk', 'DETOUR_RETURN', 'DETOUR_RETRY')
    reverse = shared.shared_comparison(sequences, case('high'), 'risk', 'DETOUR_RETRY', 'DETOUR_RETURN')
    assert forward['continuation_bounds'][1] < 0
    assert forward['certified']
    assert reverse['gap_bounds'] == [-forward['gap_bounds'][1], -forward['gap_bounds'][0]]
    assert not reverse['certified']
    assert shared.shared_comparison(sequences, case('high'), 'risk', 'DETOUR_RETURN', 'DETOUR_RETRY') == forward


def test_certificate_reuses_frozen_direct_scores_with_revised_joint_threshold():
    sequences = rows(('LOST',) * 128, ('LOST',) * 384)
    point_queries = {'reward': dict(policy='WAIT'), 'goal': dict(policy='DETOUR_RETURN'),
                     'risk': dict(policy='DETOUR_RETURN')}
    result = shared.certificates(sequences, case(), point_queries)
    assert len(result['comparison_records']) == 6
    assert len(result['evidence_records']) == 2
    assert result['threshold'] == 3600
    assert result['queries']['reward']['certified']
    for comparison in result['comparison_records']:
        assert comparison['threshold'] == 3600
        if comparison['method'] == 'paired_direct':
            statistics = direct.stream_statistics(sequences, comparison['query'], comparison['chosen'],
                                                  comparison['other'], case()['retry_cost'])
            expected = direct.evaluate(statistics, case(), 3600)
            assert all(comparison[key] == value for key, value in expected.items())
    assert result['all_ready'] == all(query['certified'] for query in result['queries'].values())


def test_cache_uses_complete_rows_and_shares_row_events_between_queries():
    sequences = rows(('RECOVERY',) * 40, ('LOST',) * 160)
    cache = {}
    first = shared.shared_comparison(sequences, case(), 'goal', 'DETOUR_RETURN', 'DETOUR_RETRY', cache)
    shared.shared_comparison(sequences, case(), 'risk', 'DETOUR_RETURN', 'DETOUR_RETRY', cache)
    assert len(cache) == 2
    sequences[shared.OPERATORS[2]] += ('DELIVERY',) * 16
    changed = shared.shared_comparison(sequences, case(), 'goal', 'DETOUR_RETURN', 'DETOUR_RETRY', cache)
    assert len(cache) == 3
    assert first['row_intervals'][shared.OPERATORS[1]] is changed['row_intervals'][shared.OPERATORS[1]]
    assert changed['n_by_row'][shared.OPERATORS[2]] == 176
    assert changed['k_by_row'][shared.OPERATORS[2]] == 16
