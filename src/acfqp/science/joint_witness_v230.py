"""Explicit ORACLE diagnostic witnesses inside retained V230 joint regions.

SLSQP only proposes a kernel. Acceptance checks the complete categorical
likelihood inequalities by exact rational arithmetic and evaluates the shared
kernel policy gap exactly. Finding a witness proves a particular pure query
policy cannot have a uniformly valid <=.05 certificate over this region.
Failure to find one proves nothing. True kernels are diagnostic proposals,
never learner inputs or an acquisition rule.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction as F
from itertools import product
from math import lgamma, log

import numpy as np
from scipy.optimize import minimize

from . import joint_gap_v230 as joint


def _fraction(value):
    return value if isinstance(value, F) else F(str(value))


def _add(work, key, amount=1):
    if work is not None:
        work[key] = work.get(key, 0) + amount


def verify_kernel(constraints_by_op, kernel, work=None):
    """Exact likelihood membership; Decimal slack is retained only for reading."""
    checks = []
    for op, constraints in constraints_by_op.items():
        p = {cat: _fraction(value) for cat, value in kernel[op].items()}
        if sum(p.values()) != 1 or any(value < 0 or value > 1 for value in p.values()):
            return dict(valid=False, checks=checks, reason='outside_simplex')
        for index, item in enumerate(constraints):
            counts = tuple(item['counts'][cat] for cat in p)
            normalizer = joint.mixture_normalizer(counts)
            likelihood = F(1)
            for cat, count in item['counts'].items():
                likelihood *= p[cat]**count
            inside = normalizer <= item['threshold']*likelihood
            _add(work, 'joint_primal_exact_likelihood_checks')
            if not inside:
                return dict(valid=False, checks=checks,
                            reason='outside_joint_region', operator=op, constraint_index=index)
            with localcontext() as ctx:
                ctx.prec = 60
                ratio = item['threshold']*likelihood/normalizer
                slack = (Decimal(ratio.numerator)/Decimal(ratio.denominator)).ln()
            checks.append(dict(operator=op, constraint_index=index,
                               exact_inside=True, log_likelihood_slack=str(slack)))
    return dict(valid=True, checks=checks)


def _utility(vector, weights):
    return weights[0]*vector[0]-weights[1]*vector[1]+weights[2]*vector[2]


def witness(case, constraints_by_op, query, chosen_policy, known_feasible_kernel, work=None):
    """Propose and EXACTLY verify a full kernel with alternative gap > .05.

    The known kernel may only be supplied by a labeled oracle diagnosis.
    Binary row corners and a convex detour-row solve seek an alternative;
    every accepted result contains a full feasible categorical kernel.
    """
    known = {op: {cat: _fraction(value) for cat, value in row.items()}
             for op, row in deepcopy(known_feasible_kernel).items()}
    known_check = verify_kernel(constraints_by_op, known, work)
    if not known_check['valid']:
        return dict(found=False, valid=False, reason='known_kernel_not_in_joint_region',
                    query=query, chosen_policy=chosen_policy, feasibility=known_check)
    weights = joint.WEIGHTS[query]

    def accepted(kernel, other, feasibility=None):
        vectors = joint.route.vectors(case, kernel)
        gap = _utility(vectors[other], weights)-_utility(vectors[chosen_policy], weights)
        if gap <= joint.THRESHOLD:
            return None
        feasibility = feasibility or verify_kernel(constraints_by_op, kernel, work)
        if not feasibility['valid']:
            return None
        return dict(found=True, valid=True, kind='ORACLE_JOINT_REGION_REGRET_WITNESS',
                    query=query, chosen_policy=chosen_policy, alternative_policy=other,
                    kernel=kernel, regret=gap, threshold=joint.THRESHOLD,
                    feasibility=feasibility)

    for other in joint.POLICIES:
        if other != chosen_policy:
            answer = accepted(known, other, known_check)
            if answer:
                return answer

    s_op, d_op, r_op = joint.OPERATORS
    s_pair = joint.interval(constraints_by_op[s_op], 'DELIVERY', work)
    r_pair = joint.interval(constraints_by_op[r_op], 'DELIVERY', work)
    categories = tuple(joint.ALPHABETS[d_op])
    start = np.array([float(known[d_op][cat]) for cat in categories])
    counts = np.array([[item['counts'][cat] for cat in categories]
                       for item in constraints_by_op[d_op]], dtype=float)
    n = counts.sum(axis=1)
    cutoffs = np.array([
        lgamma(len(categories)/2)-lgamma(size+len(categories)/2)
        +sum(lgamma(value+.5)-lgamma(.5) for value in row)-log(item['threshold'])
        for item, row, size in zip(constraints_by_op[d_op], counts, n)])
    constraints = [dict(type='eq', fun=lambda p: p.sum()-1,
                        jac=lambda p: np.ones(len(categories))),
                   dict(type='ineq', fun=lambda p: counts @ np.log(p)-cutoffs,
                        jac=lambda p: counts/p[None, :])]
    for other in joint.POLICIES:
        if other == chosen_policy:
            continue
        for short, retry in product(sorted(set(s_pair)), sorted(set(r_pair))):
            coefficient = []
            for category in categories:
                kernel = {s_op: {'DELIVERY': short, 'LOST': 1-short},
                          r_op: {'DELIVERY': retry, 'LOST': 1-retry},
                          d_op: {cat: F(cat == category) for cat in categories}}
                vectors = joint.route.vectors(case, kernel)
                coefficient.append(_utility(vectors[other], weights)
                                   -_utility(vectors[chosen_policy], weights))
            if max(coefficient) <= joint.THRESHOLD:
                continue
            c = np.array(list(map(float, coefficient)))
            result = minimize(lambda p: -c @ p, start, jac=lambda p: -c,
                              bounds=[(1e-12, 1)]*len(categories), constraints=constraints,
                              method='SLSQP', options=dict(maxiter=200, ftol=1e-12))
            _add(work, 'joint_primal_optimizer_iterations', result.nit)
            if not np.isfinite(result.x).all():
                continue
            row = {cat: _fraction(float(value)) for cat, value in zip(categories[:-1], result.x[:-1])}
            row[categories[-1]] = 1-sum(row.values())
            proposed = {s_op: {'DELIVERY': short, 'LOST': 1-short},
                        r_op: {'DELIVERY': retry, 'LOST': 1-retry}, d_op: row}
            # Solvers may land just outside a curved constraint. A small
            # inward convex move is only a proposal; exact checks decide.
            for blend in (F(0), F(1, 10**7), F(1, 10**5), F(1, 10**3)):
                kernel = {op: {cat: (1-blend)*value+blend*known[op][cat]
                               for cat, value in proposed[op].items()}
                          for op in joint.OPERATORS}
                answer = accepted(kernel, other)
                if answer:
                    return answer
    return dict(found=False, valid=False, reason='no_verified_regret_witness',
                query=query, chosen_policy=chosen_policy)


def find_regret_witness(case, constraints_by_op, chosen, known_feasible_kernel, work=None):
    """Find one counterexample to the selected three-query certificate."""
    for query in joint.WEIGHTS:
        answer = witness(case, constraints_by_op, query, chosen[query]['policy'],
                         known_feasible_kernel, work)
        if answer['found']:
            return answer
    return dict(found=False, valid=False, reason='no_verified_regret_witness')
