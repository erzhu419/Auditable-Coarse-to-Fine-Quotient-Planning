"""Global bad-query likelihood bounds for the fixed route policy grammar.

The likelihood optimizer proposes only nonnegative dual multipliers.  Each
proposal is evaluated independently with outward Decimal bounds.  RETRY's
only nonlinear term is a fixed signed coefficient times D_RECOVERY and
R_DELIVERY.  A complete, fixed partition of R_DELIVERY therefore reduces
each bad-null relaxation to a concave likelihood with a linear constraint.
No local primal optimum is used as a certificate.
"""
from decimal import Decimal, ROUND_CEILING, localcontext
from fractions import Fraction as F
from math import nextafter, inf

import numpy as np
from scipy.optimize import minimize_scalar

from . import joint_gap_v230 as joint
from . import latent_mechanisms_v213 as mechanics

OPERATORS, ALPHABETS = mechanics.OPERATORS, mechanics.ALPHABETS
POLICIES, WEIGHTS = joint.POLICIES, joint.WEIGHTS
REGRET_THRESHOLD = F(1, 20)
PARTITIONS = 32


def _add(work, key, amount=1):
    if work is not None:
        work[key] = work.get(key, 0) + amount


def _log_bounds(value):
    # ln(1) is exactly zero; avoid adjacent Decimal values around zero.
    return (F(0), F(0)) if F(value) == 1 else tuple(map(F, joint._log_bounds(value)))


def _sum_upper(values):
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 80, ROUND_CEILING
        result = Decimal(0)
        for value in values:
            result += joint._decimal_bounds(value)[1]
        return F(result.next_plus()) if result else F(0)


def _utility(case, query, policy, kernel):
    reward, risk, goal = WEIGHTS[query]
    vector = mechanics.vectors(case, kernel)[policy]
    return reward*vector[0] - risk*vector[1] + goal*vector[2]


def gap(case, query, chosen, alternative, kernel):
    """Exact shared-kernel utility difference, alternative minus chosen."""
    return (_utility(case, query, alternative, kernel)
            - _utility(case, query, chosen, kernel))


def _kernel(short=F(0), delivery=F(0), recovery=F(0), retry=F(0)):
    s, d, r = OPERATORS
    return {s: {'DELIVERY': short, 'LOST': 1-short},
            d: {'DELIVERY': delivery, 'RECOVERY': recovery,
                'LOST': 1-delivery-recovery},
            r: {'DELIVERY': retry, 'LOST': 1-retry}}


def gap_coefficients(case, query, chosen, alternative, retry):
    """Affine S/D representation at an exact R_DELIVERY endpoint."""
    s, d, _ = OPERATORS
    constant = gap(case, query, chosen, alternative, _kernel(retry=retry))
    coefficients = {
        s: {'DELIVERY': gap(case, query, chosen, alternative,
                           _kernel(short=F(1), retry=retry))-constant,
            'LOST': F(0)},
        d: {'DELIVERY': gap(case, query, chosen, alternative,
                           _kernel(delivery=F(1), retry=retry))-constant,
            'RECOVERY': gap(case, query, chosen, alternative,
                           _kernel(recovery=F(1), retry=retry))-constant,
            'LOST': F(0)}}
    return constant, coefficients


def _row_dual_upper(counts, coefficients, multiplier, nu):
    """Upper bound sup_simplex sum k ln(p) + multiplier * a.p."""
    multiplier, nu = F(multiplier), F(nu)
    if multiplier < 0 or nu <= max(multiplier*F(a) for a in coefficients.values()):
        raise ValueError('a row dual requires lambda >= 0 and nu > max(lambda*a)')
    terms = [nu-sum(counts.values())]
    for category, count in counts.items():
        if count:
            denominator = nu-multiplier*F(coefficients[category])
            terms.append(count*_log_bounds(F(count)/denominator)[1])
    return _sum_upper(terms)


def _float_row(counts, coefficients, multiplier):
    """Fast proposal for the scalar simplex dual; never used as proof."""
    ks = np.array(list(counts.values()), dtype=float)
    a = np.array([float(coefficients[c]) for c in counts], dtype=float)
    ws = multiplier*a
    maximum, n = float(max(ws)), float(sum(ks))
    if not n:
        return maximum, None
    if not multiplier:
        positive = ks > 0
        return float(np.sum(ks[positive]*np.log(ks[positive]/n))), n
    positive = ks > 0
    weights, active = ws[positive], ks[positive]
    low, high = nextafter(maximum, inf), maximum+n+1
    # Positive mass at a maximizing coefficient forces an interior root.
    # Recognizing it directly avoids dividing by nextafter(0, +inf).
    needs_root = bool(np.any(weights == maximum))
    if needs_root or float(np.sum(active/(low-weights))) > 1:
        for _ in range(60):
            mid = (low+high)/2
            if mid == low or mid == high:
                break
            if float(np.sum(active/(mid-weights))) > 1:
                low = mid
            else:
                high = mid
        nu = high
    else:
        nu = low
    return float(nu-n+np.sum(active*np.log(active/(nu-weights)))), nu


def _retry_likelihood(counts, interval):
    n = sum(counts.values())
    probability = (F(counts['DELIVERY'], n) if n else F(1, 2))
    probability = min(interval[1], max(interval[0], probability))
    row = {'DELIVERY': probability, 'LOST': 1-probability}
    upper = _sum_upper(count*_log_bounds(row[cat])[1]
                       for cat, count in counts.items() if count)
    return dict(probability=probability, log_likelihood_upper=upper)


def _evaluate_dual(counts, coefficients, multiplier):
    multiplier, witnesses = F(multiplier), {}
    for operator, coefs in coefficients.items():
        row = counts[operator]
        if not sum(row.values()):
            upper = max(multiplier*value for value in coefs.values())
            witnesses[operator] = dict(kind='free_simplex', upper=upper)
            continue
        _, suggestion = _float_row(row, coefs, float(multiplier))
        if not multiplier:
            nu = F(sum(row.values()))
        else:
            maximum = max(multiplier*value for value in coefs.values())
            nu = max(F(str(float(suggestion))), maximum+F(1, 10**12))
        witnesses[operator] = dict(kind='simplex_likelihood_dual', nu=nu,
                                  upper=_row_dual_upper(row, coefs, multiplier, nu))
    return witnesses


def _leaf(case, query, chosen, alternative, counts, interval, endpoint,
          regret_threshold, work):
    constant, coefficients = gap_coefficients(case, query, chosen, alternative, endpoint)
    maximum = constant+sum(max(row.values()) for row in coefficients.values())
    leaf = dict(retry_interval=list(interval), gap_endpoint=endpoint,
                gap_constant=constant, gap_coefficients=coefficients,
                maximum_relaxed_gap=maximum)
    if maximum < regret_threshold:
        return dict(leaf, kind='empty_bad_null', log_bad_likelihood_upper=None)
    retry = _retry_likelihood(counts[OPERATORS[2]], interval)
    constant_gap = constant-regret_threshold

    def objective(multiplier):
        return (sum(_float_row(counts[op], row, multiplier)[0]
                    for op, row in coefficients.items())
                + multiplier*float(constant_gap))

    scale = max(1, sum(sum(counts[op].values()) for op in coefficients))
    proposal = minimize_scalar(objective, bounds=(0.0, 1024.0*scale),
                               method='bounded', options=dict(maxiter=100, xatol=1e-8))
    _add(work, 'kernel_profile_optimizer_evaluations', proposal.nfev)
    multipliers = [F(0)]
    if np.isfinite(proposal.x) and proposal.x >= 0:
        multipliers.append(F(str(float(proposal.x))))
    candidates = []
    for multiplier in multipliers:
        rows = _evaluate_dual(counts, coefficients, multiplier)
        upper = _sum_upper([multiplier*constant_gap,
                            retry['log_likelihood_upper']]
                           + [row['upper'] for row in rows.values()])
        candidates.append((upper, multiplier, rows))
    upper, multiplier, rows = min(candidates, key=lambda value: value[0])
    return dict(leaf, kind='likelihood_dual', multiplier=multiplier,
                row_witnesses=rows, retry_likelihood=retry,
                log_bad_likelihood_upper=upper)


def certificate(case, query, chosen, alternative, counts, operators=None,
                threshold=480, regret_threshold=REGRET_THRESHOLD,
                partitions=PARTITIONS, work=None):
    """Exclude a complete bad null with an independently checkable witness.

    ``operators`` selects likelihood rows, including the two-row inherited A
    prefix.  Every other route row remains a free simplex.  Unknown includes
    insufficient precision or an explicitly feasible bad-null MLE; it does
    not establish that an intersection of several prefix regions fails.
    All RETRY partitions cover [0,1], including their shared boundaries.
    """
    if query not in WEIGHTS or chosen not in POLICIES or alternative not in POLICIES:
        raise ValueError('unsupported fixed route query/policy')
    threshold, regret_threshold = F(threshold), F(regret_threshold)
    if threshold <= 0 or partitions < 1:
        raise ValueError('positive event threshold and partition count required')
    selected = tuple(OPERATORS if operators is None else operators)
    effective = {op: {cat: int(counts[op][cat]) if op in selected else 0
                      for cat in ALPHABETS[op]} for op in OPERATORS}
    if any(value < 0 for row in effective.values() for value in row.values()):
        raise ValueError('counts must be nonnegative')
    _add(work, 'kernel_profile_calls')
    mixture_logs = [_log_bounds(joint.mixture_normalizer(tuple(row.values())))[0]
                    for row in effective.values()]
    log_mixture_lower = sum(mixture_logs, F(0))
    log_threshold_upper = _log_bounds(threshold)[1]
    result = dict(query=query, chosen=chosen, alternative=alternative,
                  operators=list(selected), counts=effective, threshold=threshold,
                  regret_threshold=regret_threshold,
                  log_mixture_lower=log_mixture_lower,
                  log_threshold_upper=log_threshold_upper)

    mle = {op: {cat: (F(count, sum(row.values())) if sum(row.values())
                      else F(1, len(row))) for cat, count in row.items()}
           for op, row in effective.items()}
    mle_gap = gap(case, query, chosen, alternative, mle)
    if threshold >= 1 and mle_gap >= regret_threshold:
        # Integrated likelihood <= its pointwise maximum, so this exact MLE
        # lies inside E<=1<=T.  This is a negative witness for this ONE prefix.
        _add(work, 'kernel_profile_bad_null_mle')
        return dict(result, status='unknown', witness_kind='bad_null_mle',
                    bad_null_kernel=mle, bad_null_gap=mle_gap, partitions=0,
                    leaves=[], log_bad_likelihood_upper=None, log_e_lower=None)

    slope = (gap(case, query, chosen, alternative, _kernel(recovery=F(1), retry=F(1)))
             - gap(case, query, chosen, alternative, _kernel(recovery=F(1))))
    count = partitions if slope else 1
    intervals = [(F(j, count), F(j+1, count)) for j in range(count)]
    leaves = [_leaf(case, query, chosen, alternative, effective, interval,
                    interval[1] if slope >= 0 else interval[0], regret_threshold, work)
              for interval in intervals]
    _add(work, 'kernel_profile_partition_leaves', len(leaves))
    finite = [leaf['log_bad_likelihood_upper'] for leaf in leaves
              if leaf['log_bad_likelihood_upper'] is not None]
    if not finite:
        return dict(result, status='certified', witness_kind='empty_global_bad_null',
                    partitions=count, retry_slope=slope, leaves=leaves,
                    log_bad_likelihood_upper=None, log_e_lower=None)
    upper = max(finite)
    log_e_lower = log_mixture_lower-upper
    return dict(result,
                status='certified' if log_e_lower > log_threshold_upper else 'unknown',
                witness_kind='global_likelihood_dual', partitions=count,
                retry_slope=slope, leaves=leaves,
                log_bad_likelihood_upper=upper, log_e_lower=log_e_lower)
