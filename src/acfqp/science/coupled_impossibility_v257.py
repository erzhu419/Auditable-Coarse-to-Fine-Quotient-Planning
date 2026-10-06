"""Same-event risk-constrained upper bounds on retained paid row regions."""
from fractions import Fraction as F
from itertools import combinations

from . import joint_gap_v230 as joint
from . import scoped_queries_v228 as boxes

RISK_LIMIT, GOAL_THRESHOLD = F(1, 20), F(2)
POLICIES, OPERATORS = boxes.POLICIES, boxes.OPERATORS
S, D, R = OPERATORS


def old_dual(rectangles):
    """Exact minimum of the original four-line, piecewise-linear LP dual."""
    lambdas = {F(0)}
    for left, right in combinations(POLICIES, 2):
        a, b = rectangles[left], rectangles[right]
        difference = a['risk_min']-b['risk_min']
        if difference:
            value = (a['goal_max']-b['goal_max'])/difference
            if value >= 0:
                lambdas.add(value)
    candidates = [dict(lambda_value=value, objective=value*RISK_LIMIT+max(
        point['goal_max']-value*point['risk_min'] for point in rectangles.values()))
        for value in sorted(lambdas)]
    best = min(candidates, key=lambda row: (row['objective'], row['lambda_value']))
    value = best['lambda_value']
    maximum = max(point['goal_max']-value*point['risk_min'] for point in rectangles.values())
    return dict(lambda_value=value, value=best['objective'], candidates=candidates,
        maximizing_policies=[policy for policy in POLICIES
            if rectangles[policy]['goal_max']-value*rectangles[policy]['risk_min']==maximum])


def upper_bound(plan, case, work=None):
    """Do not acquire evidence or choose lambda again after region supports."""
    vertices = boxes.box_vertices(plan['envelopes'])
    points = []
    for index, kernel in enumerate(vertices):
        vectors = boxes.mechanics.vectors(case, kernel)
        for policy in POLICIES:
            vector = vectors[policy]
            points.append(dict(vertex_index=index, policy=policy, risk=vector[1],
                goal=vector[0]+4*vector[2]))
    rectangles = {policy:dict(risk_min=min(point['risk'] for point in points if point['policy']==policy),
        goal_max=max(point['goal'] for point in points if point['policy']==policy)) for policy in POLICIES}
    dual = old_dual(rectangles)
    old, lam = F(plan['goal_upper']), dual['lambda_value']
    if dual['value'] != old:
        raise ValueError('the exact original LP dual must equal the retained goal upper')
    paired_max = max(point['goal']-lam*point['risk'] for point in points)
    paired = dict(upper=lam*RISK_LIMIT+paired_max, vertices=vertices, points=points,
        maximizing_points=[dict(vertex_index=point['vertex_index'],policy=point['policy'])
            for point in points if point['goal']-lam*point['risk']==paired_max])
    s, q = (F(plan['envelopes'][op]['bounds']['DELIVERY'][1]) for op in (S, R))
    short_cost, detour_cost = boxes.mechanics.robust.learning.COST_PRIOR[case['operating']]
    retry_cost = F(case['retry_cost'])
    coefficients = {
        'DETOUR_RETURN':dict(DELIVERY=F(4), LOST=-lam, RECOVERY=F(0)),
        'DETOUR_RETRY':dict(DELIVERY=F(4), LOST=-lam, RECOVERY=(4+lam)*q-retry_cost-lam)}
    supports = {policy:dict(coefficients=weights,
        support=joint.support(plan['joint_constraints'][D], weights, work))
        for policy, weights in coefficients.items()}
    branches = dict(WAIT=F(0), SHORT=-short_cost-lam+(4+lam)*s,
        DETOUR_RETURN=-detour_cost+supports['DETOUR_RETURN']['support']['upper'],
        DETOUR_RETRY=-detour_cost+supports['DETOUR_RETRY']['support']['upper'])
    candidate = lam*RISK_LIMIT+max(branches.values())
    result = min(old, paired['upper'], candidate)
    if work is not None:
        work['coupled_impossibility_bounds'] += 1
        work['coupled_box_vertices'] += len(vertices)
        work['coupled_vertex_policy_pairs'] += len(points)
        work['coupled_old_dual_candidates'] += len(dual['candidates'])
    return dict(risk_limit=RISK_LIMIT, goal_threshold=GOAL_THRESHOLD,
        old_goal_upper=old, rectangles=rectangles, old_dual=dual, paired_box=paired,
        binary_upper={S:s, R:q}, d_supports=supports, branches=branches,
        joint_candidate=candidate, upper=result, reduction=old-result,
        old_impossible=old<GOAL_THRESHOLD, new_impossible=result<GOAL_THRESHOLD)
