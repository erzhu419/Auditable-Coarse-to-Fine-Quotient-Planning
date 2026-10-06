"""Finite search over certified goal-feasibility weak-dual upper bounds."""
from fractions import Fraction as F

from . import trajectory_lifecycle_v256 as original
from . import coupled_impossibility_v257 as coupled
from .trajectory_lifecycle_v256 import (
    ARMS, OPERATORS, ALPHABETS, empty, ready, prepare, begin_b, observe_row,
    freeze_sources, observe_round, observe_tail, admitted_rounds, query_plan,
    native, trajectory, row_views,
)

RISK_LIMIT, GOAL_THRESHOLD = F(1, 20), F(2)
GOLDEN_RATIO, INTERVAL_REDUCTIONS = 0.6180339887498949, 20
S, D, R = OPERATORS


def _add(work, name, amount=1):
    if work is not None:
        work[name] = work.get(name, 0) + amount


def _candidate(plan, case, lam, work):
    s, q = (F(plan['envelopes'][op]['bounds']['DELIVERY'][1]) for op in (S, R))
    short_cost, detour_cost = coupled.boxes.mechanics.robust.learning.COST_PRIOR[case['operating']]
    coefficients = {
        'DETOUR_RETURN': dict(DELIVERY=F(4), LOST=-lam, RECOVERY=F(0)),
        'DETOUR_RETRY': dict(DELIVERY=F(4), LOST=-lam,
            RECOVERY=(4+lam)*q-F(case['retry_cost'])-lam),
    }
    supports = {policy: dict(coefficients=weights,
        support=coupled.joint.support(plan['joint_constraints'][D], weights, work))
        for policy, weights in coefficients.items()}
    branches = dict(WAIT=F(0), SHORT=-short_cost-lam+(4+lam)*s,
        DETOUR_RETURN=-detour_cost+supports['DETOUR_RETURN']['support']['upper'],
        DETOUR_RETRY=-detour_cost+supports['DETOUR_RETRY']['support']['upper'])
    _add(work, 'goal_feasibility_candidate_evaluations')
    _add(work, 'goal_feasibility_d_support_calls', 2)
    return dict(lambda_value=lam, binary_upper={S:s, R:q}, d_supports=supports,
        branches=branches, candidate_upper=lam*RISK_LIMIT+max(branches.values()))


def upper_bound(plan, case, work=None):
    """Retain one complete proof; discarded proposal values are diagnostics."""
    old = F(plan['goal_upper'])
    _add(work, 'goal_feasibility_bounds')
    result = dict(kind='coupled_goal_feasibility_v258', skipped=False, skip_reason=None,
        box_goal_upper=old, upper=old, old_impossible=old<GOAL_THRESHOLD,
        new_impossible=old<GOAL_THRESHOLD, risk_limit=RISK_LIMIT, goal_threshold=GOAL_THRESHOLD,
        old_dual=None, winner=None, search=dict(interval=[F(0), old/RISK_LIMIT],
            configured_reductions=INTERVAL_REDUCTIONS, reductions=0, evaluations=0, trace=[]))
    reason = ('execution_certified' if F(plan['utility_lower'])>=GOAL_THRESHOLD
        else 'box_impossible' if old<GOAL_THRESHOLD else None)
    if reason:
        _add(work, 'goal_feasibility_skips')
        return dict(result, skipped=True, skip_reason=reason)

    vertices = coupled.boxes.box_vertices(plan['envelopes'])
    vectors = [coupled.boxes.mechanics.vectors(case, kernel) for kernel in vertices]
    rectangles = {policy: dict(risk_min=min(values[policy][1] for values in vectors),
        goal_max=max(values[policy][0]+4*values[policy][2] for values in vectors))
        for policy in coupled.POLICIES}
    dual = coupled.old_dual(rectangles)
    if dual['value'] != old:
        raise ValueError('the exact original LP dual must equal the box goal upper')
    _add(work, 'goal_feasibility_box_vertices', len(vertices))
    _add(work, 'goal_feasibility_old_dual_candidates', len(dual['candidates']))
    evaluated, trace = {}, result['search']['trace']

    def evaluate(lam):
        lam = F(lam)
        if lam not in evaluated:
            evaluated[lam] = _candidate(plan, case, lam, work)
            trace.append(dict(lambda_value=lam,
                upper_float=float(evaluated[lam]['candidate_upper'])))
        return evaluated[lam]

    high = old/RISK_LIMIT
    for lam in (F(0), high, dual['lambda_value']):
        evaluate(lam)
    left, right = 0., float(high)
    c, d = right-GOLDEN_RATIO*(right-left), left+GOLDEN_RATIO*(right-left)
    fc, fd = evaluate(F(str(c))), evaluate(F(str(d)))
    for _ in range(INTERVAL_REDUCTIONS):
        if (fc['candidate_upper'], fc['lambda_value']) <= (fd['candidate_upper'], fd['lambda_value']):
            right, d, fd = d, c, fc
            c = right-GOLDEN_RATIO*(right-left)
            fc = evaluate(F(str(c)))
        else:
            left, c, fc = c, d, fd
            d = left+GOLDEN_RATIO*(right-left)
            fd = evaluate(F(str(d)))
        _add(work, 'goal_feasibility_interval_reductions')
    winner = min(evaluated.values(), key=lambda row: (row['candidate_upper'], row['lambda_value']))
    value = min(old, winner['candidate_upper'])
    result.update(upper=value, new_impossible=value<GOAL_THRESHOLD,
        old_dual=dict(lambda_value=dual['lambda_value'], value=dual['value']), winner=winner)
    result['search'].update(reductions=INTERVAL_REDUCTIONS, evaluations=len(evaluated))
    return result


def make_plan(member, case, state, identity, index, cache, work):
    plan = dict(original.make_plan(member, case, state, identity, index, cache, work))
    proof = upper_bound(plan, case, work)
    plan.update(box_goal_upper=proof['box_goal_upper'], goal_feasibility=proof,
        goal_upper=proof['upper'], goal_impossible=proof['new_impossible'])
    return plan
