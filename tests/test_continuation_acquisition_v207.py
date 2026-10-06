from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from acfqp.science import continuation_acquisition_v207 as core
from scripts import analyze_continuation_acquisition_v207 as replay

def fixture(n=256,short_success=128):
    case=dict(id='synthetic',weather='normal',operating='low',retry_cost='17/20')
    model=core.empty()
    increments={'SHORT_PASS':dict(DELIVERY=short_success,LOST=256-short_success),
                'DETOUR_PASS':dict(DELIVERY=220,LOST=2,RECOVERY=34),
                'RECOVERY_RETRY':dict(DELIVERY=n//2,LOST=n//2)}
    for op in core.OPERATORS:
        model['tables'][op]=[dict(context=case,counts=increments[op])]
    model['observations_used']=512+n
    return core.fit(model,'REVISED',Counter()),case

def test_shared_leaf_cannot_exempt_new_member_probe():
    model,case=fixture();new=dict(case,id='target',operating='high')
    plan=core.make_plan(model,new,Counter())
    choice=core.choose(model,new,plan,Counter())
    assert choice['reason']=='member_probe' and choice['operator']=='SHORT_PASS'
    assert core.previous.policies.projection_counts(model,new)['SHORT_PASS']>0
    core.update(model,new,'SHORT_PASS',dict(DELIVERY=16,LOST=0),Counter())
    choice=core.choose(model,new,core.make_plan(model,new,Counter()),Counter())
    assert choice['operator']=='DETOUR_PASS'
    core.update(model,new,'DETOUR_PASS',dict(DELIVERY=14,LOST=0,RECOVERY=2),Counter())
    choice=core.choose(model,new,core.make_plan(model,new,Counter()),Counter())
    assert choice['operator']=='RECOVERY_RETRY' and choice['pilot']

def test_reached_continuation_uses_two_query_thresholds():
    model,case=fixture()
    plan=core.make_plan(model,case,Counter());choice=core.choose(model,case,plan,Counter())
    assert choice['operator']=='RECOVERY_RETRY' and choice['reason']=='continuation'
    assert choice['decision_evidence']['goal']['threshold']==F(17,80)
    assert choice['decision_evidence']['risk']['threshold']==F(97,160)
    assert choice['decision_evidence']['risk']['unresolved']
    assert 4*F(17,80)-F(17,20)==0
    assert 8*F(97,160)-4-F(17,20)==0

def test_true_counts_resolve_continuation_without_fake_evidence():
    model,case=fixture(n=4096)
    before=deepcopy(model);plan=core.make_plan(model,case,Counter())
    choice=core.choose(model,case,plan,Counter())
    assert choice['reason']=='ratio' and model==before
    assert all(not row['unresolved'] for row in choice['decision_evidence'].values())
    core.update(model,case,'RECOVERY_RETRY',dict(DELIVERY=8,LOST=8),Counter())
    assert model['observations_used']==before['observations_used']+16
    assert all(type(n) is int for rows in model['tables'].values() for row in rows for n in row['counts'].values())

def test_independent_choice_and_unreachable_recovery():
    for short_success in (128,256):
        model,case=fixture(short_success=short_success)
        plan=core.make_plan(model,case,Counter())
        actual=core.choose(model,case,plan,Counter())
        expected=replay.choose(model,case,plan,Counter())
        assert actual==expected
        if short_success==256:
            assert all(row['root']=='SHORT' for row in actual['decision_evidence'].values())
            assert actual['reason']=='ratio'
