"""Exact query regret bounds over categorical boxes and their simplexes.

Utility differences share the same kernel.  Enumerating row vertices preserves
that dependence, including the bilinear detour/retry term, instead of
subtracting independently optimized utility endpoints.
"""
from fractions import Fraction as F
from itertools import combinations, product

from . import latent_mechanisms_v213 as mechanics

OPERATORS, ALPHABETS = mechanics.OPERATORS, mechanics.ALPHABETS
POLICIES = ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')
WEIGHTS = {'reward': (1, 0, 0), 'goal': (1, 0, 4), 'risk': (1, 4, 4)}
THRESHOLD = F(1, 20)


def _add(work, key, amount=1):
    if work is not None:
        work[key] = work.get(key, 0) + amount


def row_vertices(bounds):
    """Enumerate a 2/3-category box/simplex intersection's exact vertices."""
    categories = tuple(bounds)
    pairs = {cat: tuple(F(value) for value in bounds[cat]) for cat in categories}
    vertices = set()
    for fixed in combinations(categories, len(categories)-1):
        free = next(cat for cat in categories if cat not in fixed)
        for endpoints in product(*(pairs[cat] for cat in fixed)):
            row = dict(zip(fixed, endpoints))
            row[free] = 1 - sum(endpoints)
            if all(pairs[cat][0] <= row[cat] <= pairs[cat][1] for cat in categories):
                vertices.add(tuple(row[cat] for cat in categories))
    if not vertices:
        raise ValueError('empty categorical box/simplex intersection')
    return [dict(zip(categories, values)) for values in sorted(vertices)]


def box_vertices(envelope):
    rows = [row_vertices(envelope[op]['bounds']) for op in OPERATORS]
    return [dict(zip(OPERATORS, values)) for values in product(*rows)]


def utility(vector, weights):
    reward, failure, goal = weights
    return reward*vector[0] - failure*vector[1] + goal*vector[2]


def goal_upper(case, envelope, work=None):
    """Optimistic upper bound on risk-constrained R+4S, not pure-query regret.

    Any truly feasible complete-policy mixture is feasible after each policy's
    failure is replaced by its minimum over the box.  Replacing its goal
    utility by the maximum can only increase its objective.  These independent
    policy extrema relax the shared-kernel constraints, so their LP optimum is
    an upper bound even when no single kernel attains all extrema together.
    """
    values = [mechanics.vectors(case, kernel) for kernel in box_vertices(envelope)]
    risk_lower = {policy: min(vectors[policy][1] for vectors in values) for policy in POLICIES}
    optimistic = {policy: [max(utility(vectors[policy], WEIGHTS['goal']) for vectors in values), F(0), F(0)]
                  for policy in POLICIES}
    _add(work, 'goal_upper_kernel_vertices', len(values))
    _add(work, 'goal_upper_policy_extrema', 2*len(POLICIES)*len(values))
    return mechanics.robust.confidence.optimize(optimistic, risk_lower, work=work)['predicted_utility']


def certificates(case, envelope, point_queries, work=None, threshold=THRESHOLD):
    """Certify each fixed point-selected policy's worst shared-kernel regret.

    A route utility is affine in each categorical row separately.  Its extrema
    over independent row polytopes therefore occur at their vertex products.
    These query certificates have no execution-utility or safety prerequisite.
    """
    vertices = box_vertices(envelope)
    values = {query: {policy: [] for policy in POLICIES} for query in WEIGHTS}
    for kernel in vertices:
        vectors = mechanics.vectors(case, kernel)
        _add(work, 'query_certificate_kernel_vertices')
        for query, weights in WEIGHTS.items():
            for policy in POLICIES:
                values[query][policy].append(utility(vectors[policy], weights))
                _add(work, 'query_certificate_policy_utilities')
    result = {}
    for query in WEIGHTS:
        chosen = point_queries[query]['policy']
        by_policy = values[query]
        upper = max(F(0), max(value-selected
                    for policy in POLICIES
                    for value, selected in zip(by_policy[policy], by_policy[chosen])))
        result[query] = dict(policy=chosen,
                            utility_bounds={policy: [min(values), max(values)]
                                            for policy, values in by_policy.items()},
                            regret_upper=upper, certified=upper <= threshold)
        _add(work, 'query_certificate_regret_comparisons', len(vertices)*len(POLICIES))
    return dict(queries=result, all_ready=all(row['certified'] for row in result.values()),
                vertex_count=len(vertices))
