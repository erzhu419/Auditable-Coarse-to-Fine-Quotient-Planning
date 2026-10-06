from decimal import Decimal
from fractions import Fraction as F
from itertools import product

from acfqp.science import latent_mechanisms_v213 as mechanics
from acfqp.science import paired_query_score_v233 as direct


def case(operating='low', retry_cost='17/20'):
    return dict(operating=operating, retry_cost=retry_cost)


def test_exact_paired_score_mean_matches_every_shared_kernel_policy_gap():
    kernel = {
        direct.OPERATORS[0]: dict(DELIVERY=F(3, 5), LOST=F(2, 5)),
        direct.OPERATORS[1]: dict(DELIVERY=F(1, 2), LOST=F(1, 5), RECOVERY=F(3, 10)),
        direct.OPERATORS[2]: dict(DELIVERY=F(4, 5), LOST=F(1, 5))}
    for query, retry_cost, chosen, other in product(
            direct.QUERIES, ('17/20', '19/20'), direct.POLICIES, direct.POLICIES):
        spec = direct.score_spec(query, chosen, other, retry_cost)
        expectation = F(0)
        for values, units in spec.score_table:
            probability = F(1)
            for operator, outcome in zip(spec.required_rows, values):
                probability *= kernel[operator][outcome]
            expectation += probability * F(units, direct.SCORE_SCALE)
        vectors = mechanics.vectors(case(retry_cost=retry_cost), kernel)
        failure, delivery = direct.WEIGHTS[query]
        utility = lambda policy: vectors[policy][0] - failure * vectors[policy][1] + delivery * vectors[policy][2]
        assert expectation + direct.constant_gap(spec, case(retry_cost=retry_cost)) == utility(other) - utility(chosen)


def test_comparison_pairing_never_waits_for_an_irrelevant_retry_row():
    sequences = {direct.OPERATORS[0]: ('DELIVERY',) * 64,
                 direct.OPERATORS[1]: ('LOST',) * 64,
                 direct.OPERATORS[2]: ()}
    cache = {}
    initial = direct.stream_statistics(sequences, 'goal', 'SHORT', 'DETOUR_RETURN', '17/20', cache)
    assert initial.n == 64
    sequences[direct.OPERATORS[2]] = ('LOST',) * 200
    changed = direct.stream_statistics(sequences, 'goal', 'SHORT', 'DETOUR_RETURN', '19/20', cache)
    assert changed is initial
    assert len(cache) == 1


def test_betting_is_predictable_and_does_not_depend_on_current_or_future_score():
    spec = direct.score_spec('goal', 'SHORT', 'WAIT')
    first = (-80, -80, 0, -80, 0)
    changed = (-80, -80, 0, 0, -80)
    bets = direct.predictable_bets(spec, first)
    alternative = direct.predictable_bets(spec, changed)
    assert bets[:4] == alternative[:4]
    assert bets[4] != alternative[4]
    assert direct.predictable_bets(spec, first[:3]) == bets[:3]
    assert F(*bets[0]) == F(1, 20) / (F(1, 400) + 16)
    assert all(0 <= F(*bet) <= 1 / (spec.upper - spec.lower) for bet in bets)


def test_true_mean_eprocess_expectation_is_exactly_one_under_adaptive_bets():
    spec = direct.score_spec('goal', 'WAIT', 'SHORT')
    expected = F(0)
    # Here score is 4 with probability 1/4 and 0 with probability 3/4.
    # Enumerating all paths checks the adaptive, history-dependent product.
    for outcomes in product((0, 80), repeat=5):
        probability = F(1)
        e_value = F(1)
        for score, bet in zip(outcomes, direct.predictable_bets(spec, outcomes)):
            probability *= F(1, 4) if score else F(3, 4)
            e_value *= 1 + F(*bet) * (1 - F(score, direct.SCORE_SCALE))
        expected += probability * e_value
    assert expected == 1


def test_operating_costs_share_score_bets_and_change_only_tested_mean():
    sequences = {direct.OPERATORS[0]: ('DELIVERY',) * 160}
    statistics = direct.stream_statistics(sequences, 'goal', 'SHORT', 'WAIT')
    low, high = direct.evaluate(statistics, case()), direct.evaluate(statistics, case('high'))
    assert low['theta'] == -F(1, 20)
    assert high['theta'] == -F(7, 100)
    assert Decimal(low['log_e_lower']) > Decimal(high['log_e_lower'])
    # Decimal multiplication gives a genuine lower enclosure of the exact
    # product, rather than relying on floating point log evidence.
    exact = F(1)
    for units, bet in zip(statistics.score_units, statistics.bets):
        exact *= 1 + F(*bet) * (low['theta'] - F(units, direct.SCORE_SCALE))
    assert F(Decimal(low['e_lower'])) <= exact


def test_bad_chosen_policy_is_not_certified_and_mean_range_cases_are_analytic():
    sequences = {direct.OPERATORS[0]: ('DELIVERY',) * 160}
    bad = direct.stream_statistics(sequences, 'goal', 'WAIT', 'SHORT')
    assert not direct.evaluate(bad, case())['certified']
    equal = direct.stream_statistics({}, 'goal', 'WAIT', 'WAIT')
    assert direct.evaluate(equal, case())['kind'] == 'score_range'
    assert direct.evaluate(equal, case())['certified']


def test_queries_require_every_comparator_and_reward_wait_is_exact():
    sequences = {direct.OPERATORS[0]: ('DELIVERY',) * 256,
                 direct.OPERATORS[1]: ('LOST',) * 256,
                 direct.OPERATORS[2]: ('LOST',) * 256}
    queries = {query: dict(policy='SHORT') for query in direct.QUERIES}
    queries['reward'] = dict(policy='WAIT')
    certificate = direct.certificates(sequences, case(), queries)
    assert certificate['all_ready']
    assert len(certificate['comparison_records']) == 6
    assert certificate['queries']['reward']['kind'] == 'known_nonnegative_cost'
    queries['goal'] = dict(policy='WAIT')
    certificate = direct.certificates(sequences, case(), queries)
    assert not certificate['all_ready']
    assert not certificate['queries']['goal']['certified']


def test_retry_price_is_fixed_stream_evidence_not_an_additive_operating_cost():
    sequences = {direct.OPERATORS[1]: ('RECOVERY',) * 24,
                 direct.OPERATORS[2]: ('DELIVERY',) * 24}
    cheap = direct.stream_statistics(sequences, 'goal', 'DETOUR_RETURN', 'DETOUR_RETRY', '17/20')
    costly = direct.stream_statistics(sequences, 'goal', 'DETOUR_RETURN', 'DETOUR_RETRY', '19/20')
    assert cheap.spec != costly.spec
    assert cheap.score_units == (63,) * 24
    assert costly.score_units == (61,) * 24
    assert direct.constant_gap(cheap.spec, case()) == 0
