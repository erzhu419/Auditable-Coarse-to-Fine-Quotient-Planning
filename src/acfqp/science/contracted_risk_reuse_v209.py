"""Explicit cost-invariant kernel contract; learned fields never authorize pooling."""
from fractions import Fraction
from math import ceil, floor, log
from . import online_lifecycle_v206 as previous
from . import constrained_acquisition_v208 as acquisition
robust = previous.robust
OPERATORS, ALPHABETS, FIELDS = previous.OPERATORS, previous.ALPHABETS, previous.FIELDS
BETA = log(2*4032/.05)
empty, update, choose = previous.empty, previous.update, acquisition.choose

def fit(model, arm, work):
    result = previous.fit(model, 'REVISED' if arm == 'LOCAL' else arm, work)
    result['certificate_fields'] = ['weather'] if arm == 'REVISED' else list(FIELDS)
    return result

def interval(k, n, work):
    work['interval_calls'] += 1
    if n == 0:
        return Fraction(0), Fraction(1)
    x = k/n
    if k == 0:
        lower = 0.
    else:
        lo, hi = 0., x
        for _ in range(64):
            mid = (lo+hi)/2
            if n*robust.confidence._kl(x, mid, work) > BETA:
                lo = mid
            else:
                hi = mid
        lower = lo
    if k == n:
        upper = 1.
    else:
        lo, hi = x, 1.
        for _ in range(64):
            mid = (lo+hi)/2
            if n*robust.confidence._kl(x, mid, work) > BETA:
                hi = mid
            else:
                lo = mid
        upper = hi
    return Fraction(floor(lower*robust.GRID), robust.GRID), Fraction(ceil(upper*robust.GRID), robust.GRID)

def make_plan(model, case, work):
    fields = model["certificate_fields"]
    envelope = {}
    wanted = tuple(case[field] for field in fields)
    for op in OPERATORS:
        counts = dict.fromkeys(ALPHABETS[op], 0)
        for row in model['tables'][op]:
            work['member_context_scans'] += 1
            if tuple(row['context'][field] for field in fields) == wanted:
                for cat in counts:
                    counts[cat] += row['counts'][cat]
        n = sum(counts.values())
        envelope[op] = dict(n=n, counts=counts,
                           bounds={cat: list(interval(counts[cat], n, work)) for cat in counts})
    risks = robust.risk_bounds(envelope, work)
    goals = robust.goals_lower(envelope, case, work)
    pure = robust.point_vectors(model, case, work)
    work['planning_calls'] += 1
    return dict(**robust.solve(pure, risks, goals, work), envelopes=envelope,
                risks=risks, goals_lower=goals, pure_vectors=pure)
