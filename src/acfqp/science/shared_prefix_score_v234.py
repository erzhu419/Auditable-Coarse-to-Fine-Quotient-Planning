"""Policy-gap certificates using a shared-prefix continuation factorization.

RETURN and RETRY have the same detour prefix and operating cost. Their gap
is the recovery probability times the retry continuation value, so each
Bernoulli confidence sequence uses its complete paid row rather than pairing
detour and retry observations. All other comparisons keep the frozen V233
score and bets. The joint 180-event family uses threshold 3600 throughout.
"""
from fractions import Fraction as F
from math import comb

from . import paired_query_score_v233 as direct

POLICIES = direct.POLICIES
QUERIES = direct.QUERIES
OPERATORS = direct.OPERATORS
REGRET = direct.REGRET
STREAM_THRESHOLD = 3600
BISECTIONS = 40
SHARED_POLICIES = frozenset(('DETOUR_RETURN', 'DETOUR_RETRY'))


def mixture_likelihood(n, k):
    """Jeffreys-prior Bernoulli sequence likelihood, exactly rational."""
    return F(comb(2 * k, k) * comb(2 * (n - k), n - k),
             4**n * comb(n, k))


def accepted_probability(probability, n, k, mixture, threshold=STREAM_THRESHOLD):
    """Compare L(p) >= integrated_L / threshold without rounded logs."""
    probability = F(probability)
    numerator, denominator = probability.numerator, probability.denominator
    return (numerator**k * (denominator - numerator)**(n - k)
            * mixture.denominator * threshold
            >= denominator**n * mixture.numerator)


def bernoulli_region(n, k, threshold=STREAM_THRESHOLD):
    """Outer confidence interval and both exact endpoint brackets.

    The count maximum k/n is accepted. Bisection keeps a rejected exterior
    endpoint and an accepted interior endpoint on each nonboundary side.
    Returning exterior endpoints encloses the full accepted likelihood set.
    """
    if not 0 <= k <= n:
        raise ValueError('Bernoulli counts must satisfy 0 <= k <= n')
    mixture = mixture_likelihood(n, k)
    center = F(k, n) if n else F(0)
    if not k:
        lower, lower_inside, lower_outside = F(0), F(0), None
    else:
        lower_outside, lower_inside = F(0), center
        for _ in range(BISECTIONS):
            midpoint = (lower_outside + lower_inside) / 2
            if accepted_probability(midpoint, n, k, mixture, threshold):
                lower_inside = midpoint
            else:
                lower_outside = midpoint
        lower = lower_outside
    if k == n:
        upper, upper_inside, upper_outside = F(1), F(1), None
    else:
        upper_inside, upper_outside = center, F(1)
        for _ in range(BISECTIONS):
            midpoint = (upper_inside + upper_outside) / 2
            if accepted_probability(midpoint, n, k, mixture, threshold):
                upper_inside = midpoint
            else:
                upper_outside = midpoint
        upper = upper_outside
    return dict(n=n, k=k, threshold=threshold, lower=lower, upper=upper,
                kind='exact_rational_bisection', bisections=BISECTIONS,
                lower_bracket=dict(outside=lower_outside, inside=lower_inside),
                upper_bracket=dict(inside=upper_inside, outside=upper_outside))


def _row_region(sequences, operator, success, cache):
    values = tuple(sequences[operator])
    key = ('bernoulli', operator, values, STREAM_THRESHOLD)
    if cache is not None and key in cache:
        return cache[key]
    region = dict(bernoulli_region(len(values), values.count(success)),
                  operator=operator, success=success)
    if cache is not None:
        cache[key] = region
    return region


def shared_comparison(sequences, case, query, chosen, other, cache=None):
    """Bound the exact gap p(recovery) * signed continuation value."""
    if query not in QUERIES or frozenset((chosen, other)) != SHARED_POLICIES:
        raise ValueError('shared-prefix comparison requires RETURN and RETRY')
    detour, retry = OPERATORS[1:]
    p = _row_region(sequences, detour, 'RECOVERY', cache)
    q = _row_region(sequences, retry, 'DELIVERY', cache)
    failure, delivery = direct.WEIGHTS[query]
    retry_cost = F(case['retry_cost'])
    direction = 1 if other == 'DETOUR_RETRY' else -1
    continuation = sorted(direction * ((failure + delivery) * value - failure - retry_cost)
                          for value in (q['lower'], q['upper']))
    corners = [probability * value for probability in (p['lower'], p['upper'])
               for value in continuation]
    lower, upper = min(corners), max(corners)
    return dict(query=query, chosen=chosen, other=other, retry_cost=retry_cost,
                method='shared_prefix_rectangle', kind='exact_rectangle',
                required_rows=[detour, retry],
                n_by_row={detour: p['n'], retry: q['n']},
                k_by_row={detour: p['k'], retry: q['k']},
                row_intervals={detour: p, retry: q}, direction=direction,
                continuation_bounds=continuation, gap_bounds=[lower, upper],
                constant_gap=F(0), threshold=STREAM_THRESHOLD,
                certified=upper <= REGRET)


def certificates(sequences, case, point_queries, cache=None):
    """AND the original chosen policies' comparisons, with no new sampling."""
    if point_queries['reward']['policy'] != 'WAIT':
        raise ValueError('declared reward query chooses the known cost-optimal WAIT')
    queries = {'reward': dict(policy='WAIT', certified=True,
                             kind='known_nonnegative_cost')}
    records, evidence = [], {}
    for query in QUERIES:
        chosen = point_queries[query]['policy']
        comparisons = []
        for other in POLICIES:
            if chosen == other:
                continue
            if frozenset((chosen, other)) == SHARED_POLICIES:
                comparison = shared_comparison(sequences, case, query, chosen, other, cache)
                evidence.update(comparison['row_intervals'])
            else:
                statistics = direct.stream_statistics(sequences, query, chosen, other,
                                                      case['retry_cost'], cache)
                comparison = dict(direct.statistics_record(statistics),
                                  **direct.evaluate(statistics, case, STREAM_THRESHOLD),
                                  method='paired_direct')
            comparisons.append(comparison)
            records.append(comparison)
        queries[query] = dict(policy=chosen,
                              certified=all(row['certified'] for row in comparisons),
                              comparisons=comparisons)
    return dict(queries=queries, all_ready=all(row['certified'] for row in queries.values()),
                comparison_records=records, threshold=STREAM_THRESHOLD,
                evidence_records=[evidence[op] for op in OPERATORS if op in evidence])
