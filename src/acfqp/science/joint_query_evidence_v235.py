"""Fixed V235 necessary-row mixture regions and global gap certificates.

Each projected row uses a Jeffreys prior. Its mixture likelihood ratio is
updated on the arm's own actual acquisition path, with other rows skipped.
Exact membership supplies the first fixed-witness diagnostic. The separately
admitted qualification bounds the entire bad null using unchanged V232 dual
arithmetic and the new projected mixture numerator. Neither phase samples.
"""
from collections import Counter
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction as F
from functools import lru_cache
from math import factorial

from .continual_route_kernels_v202 import ALPHABETS, COST_PRIOR, OPERATORS

POLICIES = ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')
THRESHOLD = 960
REGRET = F(1, 20)
S, D, R = OPERATORS
ROWS = {
    'S': (S, ('DELIVERY', 'LOST')),
    'D_DEL': (D, ('DELIVERY', 'OTHER')),
    'D_FULL': (D, ('DELIVERY', 'RECOVERY', 'LOST')),
    'R': (R, ('DELIVERY', 'LOST')),
    'D_REC': (D, ('RECOVERY', 'OTHER')),
}
FAMILIES = {
    'S': ('S',), 'D_DEL': ('D_DEL',), 'D_FULL': ('D_FULL',),
    'D_FULL_R': ('D_FULL', 'R'), 'S_D_DEL': ('S', 'D_DEL'),
    'S_D_FULL': ('S', 'D_FULL'), 'S_D_FULL_R': ('S', 'D_FULL', 'R'),
    'D_REC_R': ('D_REC', 'R'),
}


def canonical_family(query, chosen, other):
    """The direction and known costs share the same true-region event."""
    if query not in ('goal', 'risk') or chosen not in POLICIES or other not in POLICIES:
        raise ValueError('fixed goal/risk policy comparisons required')
    pair = frozenset((chosen, other))
    families = {
        frozenset(('WAIT', 'SHORT')): 'S',
        frozenset(('WAIT', 'DETOUR_RETURN')): 'D_DEL' if query == 'goal' else 'D_FULL',
        frozenset(('WAIT', 'DETOUR_RETRY')): 'D_FULL_R',
        frozenset(('SHORT', 'DETOUR_RETURN')): 'S_D_DEL' if query == 'goal' else 'S_D_FULL',
        frozenset(('SHORT', 'DETOUR_RETRY')): 'S_D_FULL_R',
        frozenset(('DETOUR_RETURN', 'DETOUR_RETRY')): 'D_REC_R',
    }
    if pair not in families:
        raise ValueError('two different fixed policies required')
    return families[pair]


def project_counts(operators, family):
    """Preserve every paid entry of the required row, coarsening only labels."""
    projected = {}
    for name in FAMILIES[family]:
        op, categories = ROWS[name]
        raw = operators[op]
        counts = Counter(raw) if not isinstance(raw, dict) else raw
        total = sum(counts.values())
        if name in ('D_DEL', 'D_REC'):
            success = categories[0]
            projected[name] = {success: counts.get(success, 0),
                               'OTHER': total-counts.get(success, 0)}
        else:
            projected[name] = {cat: counts.get(cat, 0) for cat in categories}
    return projected


def project_parameters(kernel, family):
    result = {}
    for name in FAMILIES[family]:
        op, categories = ROWS[name]
        if name in ('D_DEL', 'D_REC'):
            p = F(kernel[op][categories[0]])
            result[name] = {categories[0]: p, 'OTHER': 1-p}
        else:
            result[name] = {cat: F(kernel[op][cat]) for cat in categories}
    return result


@lru_cache(maxsize=256)
def mixture_normalizer(counts):
    """Dirichlet(1/2,...,1/2) sequence likelihood, exactly rational."""
    n, k = sum(counts), len(counts)
    if k not in (2, 3) or any(v < 0 for v in counts):
        raise ValueError('nonnegative two- or three-category row counts required')
    numerator, denominator = 1, 1
    for count in counts:
        numerator *= factorial(2*count)
        denominator *= factorial(count)
    if k == 2:
        denominator *= 4**n * factorial(n)
    else:
        numerator *= factorial(n)
        denominator *= factorial(2*n+1)
    return F(numerator, denominator)


def log_bounds(value):
    """Compact directed Decimal bounds; the exact decision does not use logs."""
    value = F(value)
    if value == 1:
        return '0', '0'
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 80, ROUND_FLOOR
        lower = Decimal(value.numerator)/Decimal(value.denominator)
        ctx.rounding = ROUND_CEILING
        upper = Decimal(value.numerator)/Decimal(value.denominator)
        # Decimal.ln is correctly rounded independently of the current mode.
        return str(lower.ln().next_minus()), str(upper.ln().next_plus())


def membership(counts, parameters, threshold=THRESHOLD):
    """Exact M <= T L membership, with equality retained in the region."""
    threshold, mixture, likelihood = F(threshold), F(1), F(1)
    for name, row in counts.items():
        probabilities = {cat: F(parameters[name][cat]) for cat in row}
        if sum(probabilities.values()) != 1 or any(p < 0 for p in probabilities.values()):
            raise ValueError('each projected parameter row must be a simplex')
        mixture *= mixture_normalizer(tuple(row.values()))
        for cat, count in row.items():
            likelihood *= probabilities[cat]**count
    inside = mixture <= threshold*likelihood
    lo, hi = log_bounds(mixture/likelihood) if likelihood else ('Infinity', 'Infinity')
    tlo, thi = log_bounds(threshold)
    return dict(exact_inside=inside, excluded=not inside, threshold=int(threshold),
                log_lr_lower=lo, log_lr_upper=hi,
                log_threshold_lower=tlo, log_threshold_upper=thi)


def gap(case, query, chosen, other, parameters):
    """Exact gap from sufficient projected parameters, including known costs."""
    family = canonical_family(query, chosen, other)
    if set(parameters) != set(FAMILIES[family]):
        raise ValueError('gap requires exactly its canonical parameter projection')
    sc, dc = COST_PRIOR[case['operating']]
    rc = F(case['retry_cost'])
    if family == 'D_REC_R':
        recovery = F(parameters['D_REC']['RECOVERY'])
        retry = F(parameters['R']['DELIVERY'])
        continuation = 4*retry-rc if query == 'goal' else 8*retry-4-rc
        return recovery*continuation*(1 if other == 'DETOUR_RETRY' else -1)
    failure = 0 if query == 'goal' else 4

    def value(policy):
        if policy == 'WAIT':
            return F(0)
        if policy == 'SHORT':
            row = parameters['S']
            return -sc+4*F(row['DELIVERY'])-failure*F(row['LOST'])
        name = 'D_DEL' if 'D_DEL' in parameters else 'D_FULL'
        row = parameters[name]
        result = -dc+4*F(row['DELIVERY'])-failure*F(row.get('LOST', 0))
        if policy == 'DETOUR_RETRY':
            q = F(parameters['R']['DELIVERY'])
            result += F(row['RECOVERY'])*(4*q-failure*(1-q)-rc)
        return result

    return value(other)-value(chosen)


def compare_prefix_data(counts, family, prefixes):
    """Report literal mask/count identity; thresholds remain separate."""
    names = FAMILIES[family]
    full_mask = all(name not in ('D_DEL', 'D_REC') for name in names)
    required = tuple(ROWS[name][0] for name in names)
    result = []
    for prefix in prefixes:
        raw = prefix['counts']
        selected = {op: raw.get(op, dict.fromkeys(ALPHABETS[op], 0)) for op in required}
        relevant = project_counts(selected, family)
        same_mask = full_mask and set(prefix['operators']) == set(required)
        same_counts = relevant == counts
        result.append(dict(prefix=prefix['name'], threshold=prefix['threshold'],
            operators=prefix['operators'], relevant_projected_counts=relevant,
            same_projection_mask=same_mask, same_projected_counts=same_counts,
            equivalent_evidence=same_mask and same_counts,
            same_region=same_mask and same_counts and prefix['threshold'] == THRESHOLD))
    return result


def embedded_counts(projected, family):
    """Embed sufficient categories into the unchanged V232 gap coordinates.

    In a canonical D_DEL gap, RECOVERY and LOST have identical utility.
    In a canonical D_REC gap, DELIVERY and LOST have identical utility.
    Putting the merged category in LOST preserves the likelihood supremum;
    its zero-count companion adds no observation or prior to the numerator.
    """
    result = {op: dict.fromkeys(ALPHABETS[op], 0) for op in OPERATORS}
    for name in FAMILIES[family]:
        op, _ = ROWS[name]
        row = projected[name]
        if name in ('D_DEL', 'D_REC'):
            success = ROWS[name][1][0]
            result[op][success] = row[success]
            result[op]['LOST'] = row['OTHER']
        else:
            result[op].update(row)
    return result


def certificate(sequences, case, query, chosen, other, cache=None, work=None):
    """Bound the entire bad-gap null using the frozen projected numerator.

    The unchanged V232 leaf routine proposes a nonnegative dual multiplier,
    then evaluates it with outward 80-digit bounds. Nonlinear retry gaps use
    all 32 fixed cells. A local feasible optimum never supplies a certificate.
    """
    from . import kernel_query_profile_v232 as profile

    family = canonical_family(query, chosen, other)
    projected = project_counts(sequences, family)
    cache_key = (case['operating'], F(case['retry_cost']), query, chosen, other,
                 family, tuple((name, tuple(projected[name].items()))
                               for name in FAMILIES[family]), profile.PARTITIONS)
    profile._add(work, 'projected_certificate_calls')
    if cache is not None and cache_key in cache:
        profile._add(work, 'projected_certificate_cache_hits')
        return cache[cache_key]
    counts = embedded_counts(projected, family)
    log_mixture_lower = sum((profile._log_bounds(mixture_normalizer(tuple(row.values())))[0]
                             for row in projected.values()), F(0))
    log_threshold_upper = profile._log_bounds(THRESHOLD)[1]
    base = dict(query=query, chosen=chosen, other=other, family=family,
                projected_counts=projected, embedded_counts=counts, threshold=THRESHOLD,
                regret_threshold=REGRET, log_mixture_lower=log_mixture_lower,
                log_threshold_upper=log_threshold_upper)
    mle = {op: {cat: F(count, sum(row.values())) if sum(row.values()) else F(1, len(row))
                for cat, count in row.items()} for op, row in counts.items()}
    mle_gap = profile.gap(case, query, chosen, other, mle)
    if mle_gap >= REGRET:
        # An embedded maximum-likelihood point attains the projected maximum
        # as well. M <= max L, so it belongs to this one region when T >= 1.
        result = dict(base, status='unknown', certified=False, witness_kind='bad_null_mle',
                      bad_null_kernel=mle, bad_null_gap=mle_gap, partitions=0,
                      leaves=[], log_bad_likelihood_upper=None, log_e_lower=None)
        profile._add(work, 'projected_bad_null_mle')
    else:
        slope = (profile.gap(case, query, chosen, other, profile._kernel(recovery=F(1), retry=F(1)))
                 - profile.gap(case, query, chosen, other, profile._kernel(recovery=F(1))))
        partitions = profile.PARTITIONS if slope else 1
        intervals = [(F(index, partitions), F(index+1, partitions))
                     for index in range(partitions)]
        leaves = [profile._leaf(case, query, chosen, other, counts, interval,
                               interval[1] if slope >= 0 else interval[0], REGRET, work)
                  for interval in intervals]
        profile._add(work, 'projected_partition_leaves', len(leaves))
        finite = [leaf['log_bad_likelihood_upper'] for leaf in leaves
                  if leaf['log_bad_likelihood_upper'] is not None]
        if not finite:
            result = dict(base, status='certified', certified=True,
                witness_kind='empty_global_bad_null', partitions=partitions,
                retry_slope=slope, leaves=leaves,
                log_bad_likelihood_upper=None, log_e_lower=None)
        else:
            upper = max(finite)
            lower = log_mixture_lower-upper
            certified = lower > log_threshold_upper
            result = dict(base, status='certified' if certified else 'unknown', certified=certified,
                witness_kind='global_likelihood_dual', partitions=partitions,
                retry_slope=slope, leaves=leaves,
                log_bad_likelihood_upper=upper, log_e_lower=lower)
    profile._add(work, 'projected_unique_certificates')
    if cache is not None:
        cache[cache_key] = result
    return result


def certificates(sequences, case, point_queries, cache=None, work=None):
    """AND all original goal/risk comparisons; reward WAIT is analytic."""
    if point_queries['reward']['policy'] != 'WAIT':
        raise ValueError('the frozen reward query uses cost-optimal WAIT')
    decisions = {'reward': dict(policy='WAIT', certified=True, kind='known_nonnegative_cost')}
    records = []
    for query in ('goal', 'risk'):
        chosen = point_queries[query]['policy']
        comparisons = [certificate(sequences, case, query, chosen, other, cache, work)
                       for other in POLICIES if other != chosen]
        decisions[query] = dict(policy=chosen, certified=all(row['certified'] for row in comparisons),
                                comparisons=comparisons)
        records.extend(comparisons)
    return dict(queries=decisions, all_ready=all(row['certified'] for row in decisions.values()),
                comparison_records=records, threshold=THRESHOLD)
