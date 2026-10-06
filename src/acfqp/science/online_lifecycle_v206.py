"""Online sufficient-count field revision and whole-lifecycle member bounds."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from math import ceil, floor, log
from . import continual_route_kernels_v202 as learner
from . import target_risk_acquisition_v204 as robust
from . import conditioned_mechanisms_v205 as policies

BETA = log(2*2016/.05)
OPERATORS = learner.OPERATORS
ALPHABETS = learner.ALPHABETS
FIELDS = learner.FEATURE_FIELDS
BATCH, BUDGET = 16, 384
choose = policies.choose
update = policies.update

def empty():
    return dict(tables={op: [] for op in OPERATORS}, selected_fields={op: [] for op in OPERATORS},
                observations_used=0, scores={})

def fit(model, arm, work):
    result = deepcopy(model)
    work['online_fit_calls'] += 1
    for op in OPERATORS:
        subsets = (learner.SUBSETS if arm == 'REVISED' else
                   (FIELDS,) if arm == 'LOCAL' else ((),))
        best = None; scores = []
        for fields in subsets:
            score = learner._score(model['tables'][op], op, fields, work)
            scores.append(dict(fields=list(fields), score=score))
            key = (len(fields), fields)
            if best is None or score > best[0]+learner.SCORE_EPS or (
                    abs(score-best[0]) <= learner.SCORE_EPS and key < best[1]):
                best = score, key, fields
        result['selected_fields'][op] = list(best[2])
        result['scores'][op] = scores
        work['condition_operator_fits'] += 1
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
    envelope = {}
    wanted = tuple(case[field] for field in FIELDS)
    for op in OPERATORS:
        counts = dict.fromkeys(ALPHABETS[op], 0)
        for row in model['tables'][op]:
            work['member_context_scans'] += 1
            if tuple(row['context'][field] for field in FIELDS) == wanted:
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
