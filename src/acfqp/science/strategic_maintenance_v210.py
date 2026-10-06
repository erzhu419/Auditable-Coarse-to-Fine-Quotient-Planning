"""Contract-consistent condition induction and paid post-certificate maintenance."""
from copy import deepcopy
from fractions import Fraction
from math import ceil, floor, log
from . import contracted_risk_reuse_v209 as prior
OPERATORS, ALPHABETS, FIELDS = prior.OPERATORS, prior.ALPHABETS, prior.FIELDS
empty, update = prior.empty, prior.update
THRESHOLD = log(20)

def fit(model, arm, work):
    result = deepcopy(model); learner = prior.previous.learner
    work['online_fit_calls'] += 1
    for op in OPERATORS:
        scores = [dict(fields=list(fields), score=learner._score(model['tables'][op], op, fields, work))
                  for fields in ((), ('weather',))]
        best = scores[1] if scores[1]['score'] > scores[0]['score']+learner.SCORE_EPS else scores[0]
        result['selected_fields'][op] = best['fields']; result['scores'][op] = scores
        work['condition_operator_fits'] += 1
    result['certificate_fields'] = list(FIELDS) if arm == 'LOCAL' else ['weather']
    return result

def maintenance(model, arm):
    if arm == 'BASE': return None
    op = 'DETOUR_PASS'
    weathers = {row['context']['weather'] for row in model['tables'][op] if sum(row['counts'].values())}
    if len(weathers) < 2: return None
    scores = model['scores'][op]
    gap = scores[1]['score']-scores[0]['score']
    if gap >= THRESHOLD: return None
    return dict(operator=op, pilot=False, reason='strategic_condition_evidence',
                policy=None, evidence_gap=gap, threshold=THRESHOLD)

def next_choice(model, case, plan, arm, spent, work):
    if spent == 384: return None
    if plan['utility_lower'] < 2: return prior.choose(model, case, plan, work)
    return maintenance(model, arm)

robust = prior.robust
BETA = log(2*6048/.05)

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
