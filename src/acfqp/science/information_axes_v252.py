"""Three fixed bad kernels separating empirical S/D and empirical R axes.

A point's rejection remains inconclusive about the complete bad-kernel set.
The two retained-recovery variants are exactly the original V248 results.
"""
from copy import deepcopy
from fractions import Fraction as F

from . import endpoint_region_v248 as original

joint = original.joint
S, D, R = original.S, original.D, original.R
VARIANTS = ('RETAINED', 'R_CENTERED', 'SD_CENTERED')
STRICT_GAP = original.original.STRICT_GAP


def sd_centered(counts, case):
    """Fix native empirical full S/D rows and solve R DELIVERY once, exactly."""
    empirical = {op: {category: F(count, sum(row.values())) for category, count in row.items()}
                 for op, row in counts.items()}
    candidate = dict(kind='sd_centered_analytic_r', fixed_rows={op: deepcopy(empirical[op]) for op in (S, D)},
        retry_delivery_unclipped=None, solve_applied=False, kernel=None, gap=None, reason=None)
    recovery = empirical[D]['RECOVERY']
    if recovery == 0:
        return dict(candidate, reason='zero_empirical_detour_recovery')
    sc, dc = joint.COST_PRIOR[case['operating']]
    retry = (STRICT_GAP-sc+dc+4*empirical[S]['DELIVERY']-4*empirical[D]['DELIVERY']
             +recovery*F(case['retry_cost']))/(4*recovery)
    candidate.update(retry_delivery_unclipped=retry, solve_applied=True)
    if not 0 <= retry <= 1:
        return dict(candidate, reason='retry_delivery_outside_simplex')
    kernel = {op: deepcopy(empirical[op]) for op in (S, D)}
    kernel[R] = {'DELIVERY': retry, 'LOST': 1-retry}
    gap = joint.gap(case, 'goal', 'SHORT', 'DETOUR_RETRY',
                    joint.project_parameters(kernel, original.original.CANONICAL))
    if not original.original._simplex(kernel) or gap != STRICT_GAP:
        return dict(candidate, gap=gap, reason='analytic_kernel_not_strict_bad')
    return dict(candidate, kernel=kernel, gap=gap)


def classify(counts, constraints, case, certificate):
    retained = original.classify(counts, constraints, case, certificate)
    centered = original._classify(counts, constraints, sd_centered(counts, case))
    variants = dict(retained['variants'], SD_CENTERED=centered)
    empirical = retained['empirical_rows']
    kernel = centered['candidate']['kernel']
    distances = dict(retained['distances'], SD_CENTERED={op:
        (sum((abs(kernel[op][category]-empirical[op][category]) for category in joint.ALPHABETS[op]), F(0))/2
         if kernel is not None else None) for op in joint.OPERATORS})
    return dict(variants=variants, empirical_rows=empirical, distances=distances)
