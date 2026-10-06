"""Joint categorical confidence regions and certified action-gap supports.

For a row of K categories, M(k) = prod rising(1/2,k_c) /
rising(K/2,n). E_n(p)=M(k)/prod p_c**k_c is a nonnegative
martingale: its next-step factor is (k_c+1/2)/((n+K/2)*p_c),
whose conditional expectation is one. Predictable row acquisition preserves
this identity. Ville and the frozen stream allocation give member threshold
8640 (216 streams, delta .025), and A/B pool threshold 720 each
(9 streams each, delta .0125). These are NEW V230 events.

The optimizer proposes nonnegative likelihood multipliers. Every reported
support is evaluated from their weak-dual formula with outward Decimal
enclosures; optimizer success or a feasible primal point is not a certificate.
"""
from collections import Counter
from decimal import Decimal, localcontext, ROUND_CEILING, ROUND_FLOOR
from fractions import Fraction as F
from functools import lru_cache
from itertools import product
from math import factorial, lgamma, log

import numpy as np
from scipy.optimize import minimize

from . import latent_mechanisms_v213 as route
from . import mixture_confidence_v225 as scalar_cs

MEMBER_THRESHOLD, POOL_THRESHOLD = 8640, 720
OPERATORS, ALPHABETS = route.OPERATORS, route.ALPHABETS
POLICIES = ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')
WEIGHTS = {'reward': (1, 0, 0), 'goal': (1, 0, 4), 'risk': (1, 4, 4)}
THRESHOLD = F(1, 20)


def _add(work, key, amount=1):
    if work is not None:
        work[key] = work.get(key, 0) + amount


def region(counts, threshold):
    return dict(counts=dict(counts), threshold=int(threshold))


@lru_cache(maxsize=4096)
def mixture_normalizer(counts):
    """Exact rational Dirichlet(1/2,...,1/2) integrated likelihood."""
    n, categories = sum(counts), len(counts)
    numerator, denominator = 1, 1
    for k in counts:
        numerator *= factorial(2*k)
        denominator *= factorial(k)
    if categories == 2:
        denominator *= 4**n * factorial(n)
    elif categories == 3:
        numerator *= factorial(n)
        denominator *= factorial(2*n+1)
    else:
        raise ValueError('supported route rows have two or three categories')
    return F(numerator, denominator)


def _decimal_bounds(value):
    value = F(value)
    with localcontext() as ctx:
        ctx.prec = 80
        ctx.rounding = ROUND_FLOOR
        low = Decimal(value.numerator)/Decimal(value.denominator)
        ctx.rounding = ROUND_CEILING
        high = Decimal(value.numerator)/Decimal(value.denominator)
    return low, high


def _log_bounds(value):
    """Decimal.ln is correctly rounded; adjacent values enclose its result."""
    low, high = _decimal_bounds(value)
    with localcontext() as ctx:
        ctx.prec = 80
        return low.ln().next_minus(), high.ln().next_plus()


def dual_upper(constraints, weights, lambdas, nu):
    """Evaluate a feasible weak-dual witness, independently of any optimizer."""
    cats = tuple(weights)
    weights, lambdas, nu = {c: F(weights[c]) for c in cats}, list(map(F, lambdas)), F(nu)
    if len(lambdas) != len(constraints) or any(value < 0 for value in lambdas):
        raise ValueError('one nonnegative multiplier is required per region')
    if nu <= max(weights.values()):
        raise ValueError('dual nu must strictly exceed every categorical weight')
    total = {c: sum(lam*item['counts'][c]
                    for lam, item in zip(lambdas, constraints)) for c in cats}
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 80, ROUND_CEILING
        upper = _decimal_bounds(nu - sum(total.values()))[1]
        for c, count in total.items():
            if count:
                log_upper = _log_bounds(count/(nu-weights[c]))[1]
                # The logarithm can have either sign; multiply with an interval
                # endpoint selected to preserve an upper enclosure.
                count_pair = _decimal_bounds(count)
                upper += count_pair[1 if log_upper >= 0 else 0]*log_upper
        for lam, item in zip(lambdas, constraints):
            if not lam:
                continue
            normalizer = mixture_normalizer(tuple(item['counts'][c] for c in cats))
            # a_low subtraction itself must round downward.
            with localcontext() as lower_ctx:
                lower_ctx.prec, lower_ctx.rounding = 80, ROUND_FLOOR
                a_low = _log_bounds(normalizer)[0] - _log_bounds(item['threshold'])[1]
            lam_pair = _decimal_bounds(lam)
            upper += -lam_pair[0 if a_low >= 0 else 1]*a_low
        return F(upper.next_plus())


def support(constraints, weights, work=None):
    """Upper bound max w.p over the intersection of all supplied regions."""
    constraints = list(constraints)
    cats = tuple(weights)
    weights = {c: F(weights[c]) for c in cats}
    simple = max(weights.values())
    fallback = dict(upper=simple, witness=dict(kind='simplex', upper=simple))
    _add(work, 'joint_support_calls')
    active = [j for j, item in enumerate(constraints) if sum(item['counts'].values())]
    if not active or min(weights.values()) == simple:
        return fallback
    counts = np.array([[constraints[j]['counts'][c] for c in cats] for j in active], dtype=float)
    sizes = counts.sum(axis=1)
    normalized = counts/sizes[:, None]
    a = np.array([
        lgamma(len(cats)/2)-lgamma(n+len(cats)/2)
        +sum(lgamma(k+.5)-lgamma(.5) for k in row)
        -log(constraints[j]['threshold'])
        for j, row, n in zip(active, counts, sizes)])
    w = np.array([float(weights[c]) for c in cats])
    maximum = float(simple)

    def objective(values):
        ts, gap = values[:-1], values[-1]
        nu = maximum+gap
        combined = ts @ normalized
        differences = nu-w
        logs = np.zeros_like(combined)
        positive = combined > 0
        logs[positive] = np.log(combined[positive]/differences[positive])
        value = nu + np.sum(combined*(logs-1)) - np.dot(ts, a/sizes)
        gradient = np.r_[normalized @ logs - a/sizes,
                         1-np.sum(combined/differences)]
        return float(value), gradient

    # A single deterministic proposal; infeasible or inaccurate proposals only
    # lose tightness because the simplex bound remains available.
    result = minimize(objective, np.r_[np.ones(len(active)), 1.0], jac=True,
                      method='L-BFGS-B', bounds=[(1e-10, None)]*len(active)+[(1e-9, None)],
                      options=dict(maxiter=200, ftol=1e-13, gtol=1e-9))
    _add(work, 'joint_dual_optimizer_iterations', result.nit)
    if not np.isfinite(result.x).all():
        return fallback
    lambdas = [F(0)]*len(constraints)
    for j, t, size in zip(active, result.x[:-1], sizes):
        lambdas[j] = F(str(float(t/size)))
    nu = F(str(float(maximum+result.x[-1])))
    if nu <= simple:
        return fallback
    upper = dual_upper(constraints, weights, lambdas, nu)
    if upper >= simple:
        return fallback
    return dict(upper=upper, witness=dict(kind='likelihood_dual', lambdas=lambdas,
                                         nu=nu, upper=upper))


def interval(constraints, category, work=None):
    """A valid marginal projection of the NEW joint region intersection."""
    cats = tuple(constraints[0]['counts'])
    if len(cats) == 2:
        # K=2 Dirichlet(1/2,1/2) is exactly the existing scalar beta
        # inversion. Every call supplies the NEW row's own threshold.
        # Intersecting these closed intervals detects empty false sources
        # before a dual optimization would diverge along infeasibility.
        scalar_work = Counter()
        pairs = [scalar_cs.interval(item['counts'][category],
                                    sum(item['counts'].values()), scalar_work,
                                    item['threshold']) for item in constraints]
        for key, value in scalar_work.items():
            _add(work, key, value)
        return [max(pair[0] for pair in pairs), min(pair[1] for pair in pairs)]
    positive = {cat: F(cat == category) for cat in cats}
    negative = {cat: -value for cat, value in positive.items()}
    low, high = -support(constraints, negative, work)['upper'], support(constraints, positive, work)['upper']
    return [max(F(0), low), min(F(1), high)]


def _utility(vector, weights):
    reward, risk, goal = weights
    return reward*vector[0]-risk*vector[1]+goal*vector[2]


def certificates(case, constraints_by_op, chosen, work=None):
    """Support shared-kernel policy gaps without boxing the detour row.

    S/R rows are binary. At fixed detour probabilities, every policy gap
    is affine in each of their delivery probabilities. Their projected
    endpoints therefore suffice; the detour coefficient is then linear.
    Every corner support is an outward upper bound, so taking the maximum
    preserves simultaneous regret validity for adaptively chosen policies.
    """
    s_op, d_op, r_op = OPERATORS
    s_pair = interval(constraints_by_op[s_op], 'DELIVERY', work)
    r_pair = interval(constraints_by_op[r_op], 'DELIVERY', work)
    binary_intervals = {s_op: s_pair, r_op: r_pair}
    empty_ops = [op for op, (low, high) in binary_intervals.items() if low > high]
    if empty_ops:
        return dict(empty=True, empty_proof=dict(operators=empty_ops,
                                                binary_intervals=binary_intervals),
                    queries={q: dict(policy=chosen[q]['policy'], regret_upper=F(0),
                                     certified=False) for q in WEIGHTS},
                    all_ready=False, support_records=[], binary_intervals=binary_intervals)
    records, queries = [], {}
    for query, weights in WEIGHTS.items():
        selected = chosen[query]['policy']
        upper = F(0)
        for other in POLICIES:
            if other == selected:
                continue
            for short, retry in product(sorted(set(s_pair)), sorted(set(r_pair))):
                coefficient = {}
                for category in ALPHABETS[d_op]:
                    kernel = {s_op: {'DELIVERY': short, 'LOST': 1-short},
                              r_op: {'DELIVERY': retry, 'LOST': 1-retry},
                              d_op: {cat: F(cat == category) for cat in ALPHABETS[d_op]}}
                    vectors = route.vectors(case, kernel)
                    coefficient[category] = _utility(vectors[other], weights)-_utility(vectors[selected], weights)
                bound = support(constraints_by_op[d_op], coefficient, work)
                records.append(dict(query=query, other=other, chosen=selected,
                                    short_delivery=short, retry_delivery=retry,
                                    weights=coefficient, support=bound))
                upper = max(upper, bound['upper'])
        queries[query] = dict(policy=selected, regret_upper=upper, certified=upper <= THRESHOLD)
    _add(work, 'joint_query_support_records', len(records))
    return dict(empty=False, queries=queries,
                all_ready=all(value['certified'] for value in queries.values()),
                support_records=records, binary_intervals=binary_intervals)
