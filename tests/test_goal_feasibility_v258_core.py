"""Certified search, safe mixtures, strict thresholds and decision isolation."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

import pytest

from acfqp.science import goal_feasibility_v258 as core

CASE = dict(context='B', stage='B', operating='low', retry_cost='17/20')
S, D, R = core.OPERATORS


def paid_plan(short=None, detour=None, retry=None):
    counts = {
        S: short or dict(DELIVERY=0, LOST=500),
        D: detour or dict(DELIVERY=300, LOST=150, RECOVERY=50),
        R: retry or dict(DELIVERY=500, LOST=0),
    }
    constraints = {op: [core.coupled.joint.region(row, 720)] for op, row in counts.items()}
    envelopes = {D: dict(bounds={cat: [F(0), F(1)] for cat in counts[D]})}
    for op in (S, R):
        lower, upper = core.coupled.joint.interval(constraints[op], 'DELIVERY', Counter())
        envelopes[op] = dict(bounds=dict(DELIVERY=[lower, upper], LOST=[1-upper, 1-lower]))
    return dict(envelopes=envelopes, joint_constraints=constraints, utility_lower=F(0),
        goal_upper=core.coupled.boxes.goal_upper(CASE, envelopes, Counter()))


@pytest.mark.parametrize('lower,upper,reason',[
    (F(2), F(3), 'execution_certified'),
    (F(0), F(19,10), 'box_impossible'),
])
def test_original_resolved_decisions_skip_every_new_support(lower, upper, reason, monkeypatch):
    monkeypatch.setattr(core.coupled.boxes, 'box_vertices',
        lambda *args: pytest.fail('resolved decisions must not start a new search'))
    plan, work = dict(utility_lower=lower, goal_upper=upper), Counter()
    result = core.upper_bound(plan, CASE, work)
    assert result['skipped'] and result['skip_reason']==reason
    assert result['upper']==upper and result['new_impossible']==(upper<2)
    assert result['winner'] is None and result['old_dual'] is None
    assert result['search']['evaluations']==result['search']['reductions']==0
    assert not result['search']['trace']
    assert work['goal_feasibility_skips']==1 and work['joint_support_calls']==0


def test_new_multiplier_reveals_full_region_impossibility_with_auditable_winning_duals():
    plan, work = paid_plan(), Counter()
    before = deepcopy(plan)
    result = core.upper_bound(plan, CASE, work)
    assert plan==before
    assert result['old_dual']['lambda_value']==0 and result['box_goal_upper']>2
    assert result['winner']['lambda_value']>0
    assert 0<=result['upper']<2 and result['new_impossible']
    assert result['upper']<=result['box_goal_upper']
    search, winner = result['search'], result['winner']
    assert search['reductions']==20 and search['evaluations']<=25
    assert len({row['lambda_value'] for row in search['trace']})==search['evaluations']
    assert winner['lambda_value'] in {row['lambda_value'] for row in search['trace']}
    assert work['goal_feasibility_d_support_calls']==2*search['evaluations']
    assert work['goal_feasibility_interval_reductions']==20
    for row in winner['d_supports'].values():
        witness = row['support']['witness']
        assert witness['kind']=='likelihood_dual'
        assert row['support']['upper']==core.coupled.joint.dual_upper(
            plan['joint_constraints'][D], row['coefficients'], witness['lambdas'], witness['nu'])
    lam, q = winner['lambda_value'], winner['binary_upper'][R]
    assert winner['d_supports']['DETOUR_RETRY']['coefficients']==dict(
        DELIVERY=4, LOST=-lam, RECOVERY=(4+lam)*q-F(17,20)-lam)
    assert winner['candidate_upper']==lam/20+max(winner['branches'].values())


def test_bound_covers_an_interior_safe_policy_mixture():
    plan = paid_plan(short=dict(DELIVERY=9400, LOST=600),
        detour=dict(DELIVERY=0, LOST=500, RECOVERY=0))
    result = core.upper_bound(plan, CASE, Counter())
    # At p_SHORT_LOST=.06, mixing SHORT with WAIT at weight5/6 is safe
    # although pure SHORT is unsafe. Its exact goal is3.05, so neither an
    # unsafe-policy exclusion nor a risk/goal factor error may prove <2.
    weight, risk, goal = F(5,6), F(3,50), F(183,50)
    assert weight*risk==F(1,20) and weight*goal==F(61,20)
    assert result['upper']>=weight*goal and not result['new_impossible']


def test_support_primal_suggestions_never_override_safe_upper_and_original_event_refs(monkeypatch):
    plan, calls = paid_plan(), []
    def support(constraints, coefficients, work):
        calls.append(constraints)
        upper = max(coefficients.values())
        return dict(upper=upper, primal=-10**6, optimizer_success=True,
            witness=dict(kind='simplex', upper=upper))
    monkeypatch.setattr(core.coupled.joint, 'support', support)
    result = core.upper_bound(plan, CASE, Counter())
    assert all(constraints is plan['joint_constraints'][D] for constraints in calls)
    assert result['upper']==plan['goal_upper'] and not result['new_impossible']
    assert len(calls)==2*result['search']['evaluations']


def test_exact_two_is_not_certified_impossible_and_mismatched_old_bound_is_rejected(monkeypatch):
    bounds = {
        S: dict(DELIVERY=[F(0)]*2, LOST=[F(1)]*2),
        D: dict(DELIVERY=[F(41,80)]*2, LOST=[F(0)]*2, RECOVERY=[F(39,80)]*2),
        R: dict(DELIVERY=[F(0)]*2, LOST=[F(1)]*2),
    }
    envelopes = {op: dict(bounds=row) for op,row in bounds.items()}
    constraints = {op: [core.coupled.joint.region(dict.fromkeys(row,0),720)] for op,row in bounds.items()}
    plan = dict(envelopes=envelopes,joint_constraints=constraints,utility_lower=0,
        goal_upper=core.coupled.boxes.goal_upper(CASE,envelopes,Counter()))
    result = core.upper_bound(plan, CASE, Counter())
    assert result['upper']==2 and not result['new_impossible'] and not result['skipped']
    plan['goal_upper']+=F(1,100)
    monkeypatch.setattr(core.coupled.joint,'support',
        lambda *args: pytest.fail('a stale box bound must fail before any new support'))
    with pytest.raises(ValueError,match='exact original LP dual'):
        core.upper_bound(plan,CASE,Counter())


def test_make_plan_preserves_original_mix_queries_regions_and_source_plan(monkeypatch):
    original = dict(utility_lower=F(0),goal_upper=F(3),goal_impossible=False,
        mix=[('WAIT',F(1))],queries={'goal':{'policy':'SHORT'}},
        query_evidence={'threshold':4320},joint_constraints={'unchanged':'original events'})
    before, calls = deepcopy(original), []
    def base(*args):
        calls.append(args)
        return original
    proof = dict(box_goal_upper=F(3),upper=F(19,10),new_impossible=True)
    monkeypatch.setattr(core.original,'make_plan',base)
    monkeypatch.setattr(core,'upper_bound',lambda *args: proof)
    member,state,cache,work = {},{}, {},Counter()
    result = core.make_plan(member,CASE,state,1,30,cache,work)
    assert calls==[(member,CASE,state,1,30,cache,work)]
    assert original==before
    assert result['box_goal_upper']==3 and result['goal_upper']==F(19,10)
    assert result['goal_impossible'] and result['goal_feasibility'] is proof
    for key in ('mix','queries','query_evidence','joint_constraints','utility_lower'):
        assert result[key]==before[key]
