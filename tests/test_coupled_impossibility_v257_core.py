"""Exact dual selection, coupled support and strict impossibility semantics."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import pytest

from acfqp.science import coupled_impossibility_v257 as core

CASE = dict(context='B',stage='B',operating='low',retry_cost='17/20')
S,D,R = core.OPERATORS


def plan_for(bounds,counts=None):
    envelopes = {op:dict(bounds=deepcopy(row)) for op,row in bounds.items()}
    constraints = {op:[dict(counts=dict.fromkeys(core.joint.ALPHABETS[op],0),threshold=720)] for op in core.OPERATORS}
    if counts:
        constraints[D][0]['counts'] = counts
    return dict(envelopes=envelopes,joint_constraints=constraints,
        goal_upper=core.boxes.goal_upper(CASE,envelopes,Counter()))


def broad_plan():
    bounds = {S:dict(DELIVERY=[F(7,10),F(9,10)],LOST=[F(1,10),F(3,10)]),
        D:dict(DELIVERY=[F(7,20),F(13,20)],LOST=[F(3,100),F(9,50)],RECOVERY=[F(1,5),F(3,5)]),
        R:dict(DELIVERY=[F(7,10),F(9,10)],LOST=[F(1,10),F(3,10)])}
    return plan_for(bounds,dict(DELIVERY=300,LOST=60,RECOVERY=240))


def test_exact_four_line_dual_matches_existing_primal_and_smallest_lambda_tie():
    rectangles = dict(WAIT=dict(risk_min=F(0),goal_max=F(0)),
        SHORT=dict(risk_min=F(1,10),goal_max=F(3)),
        DETOUR_RETURN=dict(risk_min=F(1,100),goal_max=F(1)),
        DETOUR_RETRY=dict(risk_min=F(1,5),goal_max=F(4)))
    dual = core.old_dual(rectangles)
    primal = core.boxes.mechanics.robust.confidence.optimize(
        {p:[row['goal_max'],F(0),F(0)] for p,row in rectangles.items()},
        {p:row['risk_min'] for p,row in rectangles.items()})
    assert dual['value']==primal['predicted_utility']==F(17,9)
    assert dual['lambda_value']==F(200,9)
    tied = {p:dict(risk_min=F(0),goal_max=F(1)) for p in core.POLICIES}
    assert core.old_dual(tied)['lambda_value']==0


def test_original_full_D_region_can_strictly_improve_same_lambda_paired_box():
    plan, work = broad_plan(), Counter()
    result = core.upper_bound(plan,CASE,work)
    assert result['old_dual']['value']==plan['goal_upper']
    assert result['paired_box']['upper']==plan['goal_upper']  # actual route monotonicity
    assert result['joint_candidate']<result['paired_box']['upper']
    assert result['upper']==result['joint_candidate'] and result['reduction']>0
    assert work['joint_support_calls']==2 and work['coupled_impossibility_bounds']==1
    for row in result['d_supports'].values():
        witness = row['support']['witness']
        assert witness['kind']=='likelihood_dual'
        assert row['support']['upper']==core.joint.dual_upper(plan['joint_constraints'][D],
            row['coefficients'],witness['lambdas'],witness['nu'])


def test_two_D_coefficients_use_original_regions_and_fixed_old_lambda(monkeypatch):
    plan, calls = broad_plan(), []
    def support(constraints,weights,work):
        calls.append((constraints,deepcopy(weights)))
        return dict(upper=max(weights.values()),witness=dict(kind='simplex',upper=max(weights.values())))
    monkeypatch.setattr(core.joint,'support',support)
    result = core.upper_bound(plan,CASE,Counter())
    lam,q,s = result['old_dual']['lambda_value'],result['binary_upper'][R],result['binary_upper'][S]
    assert len(calls)==2 and all(row[0] is plan['joint_constraints'][D] for row in calls)
    assert calls[0][1]==dict(DELIVERY=4,LOST=-lam,RECOVERY=0)
    assert calls[1][1]==dict(DELIVERY=4,LOST=-lam,RECOVERY=(4+lam)*q-F(17,20)-lam)
    assert result['branches']['SHORT']==-F(1,10)-lam+(4+lam)*s
    assert result['upper']==min(plan['goal_upper'],result['paired_box']['upper'],result['joint_candidate'])


def test_strict_threshold_keeps_exact_two_unresolved():
    exact = {S:dict(DELIVERY=[F(0)]*2,LOST=[F(1)]*2),
        D:dict(DELIVERY=[F(41,80)]*2,LOST=[F(0)]*2,RECOVERY=[F(39,80)]*2),
        R:dict(DELIVERY=[F(0)]*2,LOST=[F(1)]*2)}
    plan = plan_for(exact)
    result = core.upper_bound(plan,CASE,Counter())
    assert result['upper']==2 and not result['new_impossible']
    exact[D]['DELIVERY'] = [F(1,2)]*2
    exact[D]['RECOVERY'] = [F(1,2)]*2
    below = core.upper_bound(plan_for(exact),CASE,Counter())
    assert below['upper']==F(39,20) and below['new_impossible']


def test_mismatched_retained_old_upper_fails_before_any_new_support(monkeypatch):
    plan = broad_plan()
    plan['goal_upper'] += F(1,100)
    monkeypatch.setattr(core.joint,'support',lambda *args:pytest.fail('support must wait for exact old dual equality'))
    with pytest.raises(ValueError,match='exact original LP dual'):
        core.upper_bound(plan,CASE,Counter())
