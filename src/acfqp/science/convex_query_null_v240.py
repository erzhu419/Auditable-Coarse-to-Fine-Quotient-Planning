"""One convex bad-null likelihood proposal for each fixed V240 comparison.

Exact accepted bad kernels and global concavity tangents determine the result.
The sole numerical optimizer supplies an interior evaluation point; its success
flag never supplies a certificate or a claim of likelihood optimality.
"""
from fractions import Fraction as F

import numpy as np
from scipy.optimize import minimize

from .joint_query_evidence_v235 import COST_PRIOR, REGRET, THRESHOLD, gap, log_bounds, membership, mixture_normalizer

EPS = 1e-9
OPTIONS = dict(maxiter=500, ftol=1e-12)
DENOMINATOR_LIMIT = 10**9
STRICT_GAP = REGRET+F(1, 10**6)
STARTS = {'S_D_FULL': (F(9, 10), F(1, 10), F(1, 20), F(1, 10), F(17, 20)),
          'D_REC_R': (F(1, 2), F(9, 10))}
COORDINATES = (('S', 'DELIVERY'), ('S', 'LOST'), ('D_FULL', 'DELIVERY'),
               ('D_FULL', 'RECOVERY'), ('D_FULL', 'LOST'))


def _log(value):
    return tuple(map(F, log_bounds(value)))


def _h(case, family, point):
    if family == 'S_D_FULL':
        return gap(case, 'risk', 'DETOUR_RETURN', 'SHORT', point)-REGRET
    d, r = point['D_REC']['RECOVERY'], point['R']['DELIVERY']
    return r-(4+F(case['retry_cost']))/8-REGRET/(8*d)


def _point(values, family):
    values = [F(str(float(value))).limit_denominator(DENOMINATOR_LIMIT) for value in values]
    if family == 'S_D_FULL':
        rows = {'S': dict(zip(('DELIVERY', 'LOST'), values[:2])),
                'D_FULL': dict(zip(('DELIVERY', 'RECOVERY', 'LOST'), values[2:]))}
        return {name: {category: value/sum(row.values()) for category, value in row.items()}
                for name, row in rows.items()}
    d, r = values
    return {'D_REC': {'RECOVERY': d, 'OTHER': 1-d}, 'R': {'DELIVERY': r, 'LOST': 1-r}}


def _interior(point):
    return all(sum(row.values()) == 1 and min(row.values()) > 0 for row in point.values())


def _proposal(counts, case, family):
    size = sum(sum(row.values()) for row in counts.values())
    if family == 'S_D_FULL':
        observed = np.array([counts[name][category] for name, category in COORDINATES], dtype=float)
        sc, dc = COST_PRIOR[case['operating']]
        gradient_h = np.array([8., 0., -4., 0., 4.])

        def objective(x):
            return -float(np.sum(observed*np.log(x)))/size, -observed/(x*size)

        constraints = [
            dict(type='eq', fun=lambda x: x[0]+x[1]-1,
                 jac=lambda x: np.array([1., 1., 0., 0., 0.])),
            dict(type='eq', fun=lambda x: sum(x[2:])-1,
                 jac=lambda x: np.array([0., 0., 1., 1., 1.])),
            dict(type='ineq', fun=lambda x: float(dc-sc-4-REGRET)+float(gradient_h@x),
                 jac=lambda x: gradient_h),
        ]
    else:
        successes = np.array([counts['D_REC']['RECOVERY'], counts['R']['DELIVERY']], dtype=float)
        failures = np.array([counts['D_REC']['OTHER'], counts['R']['LOST']], dtype=float)
        a, b = float((4+F(case['retry_cost']))/8), float(REGRET/8)

        def objective(x):
            return (-float(np.sum(successes*np.log(x)+failures*np.log(1-x)))/size,
                    (-successes/x+failures/(1-x))/size)

        constraints = [dict(type='ineq', fun=lambda x: x[1]-a-b/x[0],
                            jac=lambda x: np.array([b/x[0]**2, 1.]))]
    result = minimize(objective, np.array(list(map(float, STARTS[family]))), method='SLSQP', jac=True,
        constraints=constraints, bounds=[(EPS, 1-EPS)]*len(STARTS[family]), options=OPTIONS)
    record = dict(method='SLSQP', start=list(STARTS[family]), success=bool(result.success),
        iterations=int(result.nit), message=str(result.message), options=dict(OPTIONS),
        objective_scaling='negative_log_likelihood_divided_by_projected_count_total', bounds=[EPS, 1-EPS])
    return (_point(result.x, family) if np.isfinite(result.x).all() else None), record


def _repair(point, counts, case, family):
    candidate = {name: dict(row) for name, row in point.items()}
    if family == 'S_D_FULL':
        sc, dc = COST_PRIOR[case['operating']]
        row = candidate['D_FULL']
        s = (STRICT_GAP-(dc-sc-4)+4*row['DELIVERY']-4*row['LOST'])/8
        candidate['S'] = {'DELIVERY': s, 'LOST': 1-s}
        other = 'SHORT'
    else:
        d = candidate['D_REC']['RECOVERY']
        r = (4+F(case['retry_cost'])+STRICT_GAP/d)/8
        candidate['R'] = {'DELIVERY': r, 'LOST': 1-r}
        other = 'DETOUR_RETRY'
    feasible = all(sum(row.values()) == 1 and min(row.values()) >= 0 for row in candidate.values())
    measured = gap(case, 'risk', 'DETOUR_RETURN', other, candidate) if feasible else None
    member = membership(counts, candidate) if feasible and measured > REGRET else None
    return dict(parameters=candidate, feasible=feasible, gap=measured, membership=member)


def _tangent(point, counts, case, family):
    likelihood_upper = sum((count*_log(point[name][category])[1]
        for name, row in counts.items() for category, count in row.items() if count), F(0))
    h = _h(case, family, point)
    if family == 'S_D_FULL':
        grad_f = {name: {category: F(count)/point[name][category] for category, count in row.items()}
                  for name, row in counts.items()}
        grad_h = {'S': {'DELIVERY': F(8), 'LOST': F(0)},
                  'D_FULL': {'DELIVERY': F(-4), 'RECOVERY': F(0), 'LOST': F(4)}}
        multiplier = max(F(0), (grad_f['S']['LOST']-grad_f['S']['DELIVERY'])/8)
        residual = {name: {category: grad_f[name][category]+multiplier*grad_h[name][category]
                          for category in row} for name, row in counts.items()}
        support = sum((max(row.values())-sum(coefficient*point[name][category]
            for category, coefficient in row.items()) for name, row in residual.items()), F(0))
    else:
        d, r = point['D_REC']['RECOVERY'], point['R']['DELIVERY']
        grad_f = {'D_REC': F(counts['D_REC']['RECOVERY'])/d-F(counts['D_REC']['OTHER'])/(1-d),
                  'R': F(counts['R']['DELIVERY'])/r-F(counts['R']['LOST'])/(1-r)}
        grad_h = {'D_REC': REGRET/(8*d*d), 'R': F(1)}
        multiplier = max(F(0), -grad_f['R'])
        residual = {name: grad_f[name]+multiplier*grad_h[name] for name in grad_f}
        support = sum((max(F(0), value)-value*point[name]['RECOVERY' if name == 'D_REC' else 'DELIVERY']
                       for name, value in residual.items()), F(0))
    upper = likelihood_upper+multiplier*h+support
    mixture_lower = sum((_log(mixture_normalizer(tuple(row.values())))[0] for row in counts.values()), F(0))
    threshold_upper = _log(F(THRESHOLD))[1]
    e_lower = mixture_lower-upper
    return dict(point=point, h_point=h, log_likelihood_upper=likelihood_upper,
        gradient_likelihood=grad_f, gradient_h=grad_h, multiplier=multiplier,
        residual_gradient=residual, residual_support=support, global_upper=upper,
        log_mixture_lower=mixture_lower, log_e_lower=e_lower,
        log_threshold_upper=threshold_upper, certified=e_lower > threshold_upper)


def classify(counts, case, family):
    """Return one exact bad witness or one global tangent exclusion, else unknown."""
    if family not in STARTS:
        raise ValueError('V240 supports the two frozen risk comparisons only')
    point, optimizer = _proposal(counts, case, family)
    base = dict(family=family, projected_counts=counts, threshold=THRESHOLD,
                regret_threshold=REGRET, optimizer=optimizer, proposed_point=point)
    if point is None or not _interior(point):
        return dict(base, status='unknown', repaired_witness=None, global_tangent=None)
    witness = _repair(point, counts, case, family)
    tangent = _tangent(point, counts, case, family)
    admitted = witness['membership'] is not None and witness['membership']['exact_inside']
    status = ('admitted_bad_kernel' if admitted else
              'global_bad_null_excluded' if tangent['certified'] else 'unknown')
    return dict(base, status=status, repaired_witness=witness, global_tangent=tangent)
