from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from acfqp.science import constrained_acquisition_v208 as core
from scripts import analyze_constrained_acquisition_v208 as replay

def fixture(retry_needed=False):
    case=dict(id='synthetic',weather='normal',operating='low',retry_cost='17/20')
    model=core.empty()
    counts={'SHORT_PASS':{'DELIVERY':128,'LOST':128},
            'DETOUR_PASS':dict(DELIVERY=100,LOST=3,RECOVERY=153) if retry_needed else dict(DELIVERY=220,LOST=3,RECOVERY=33),
            'RECOVERY_RETRY':dict(DELIVERY=244,LOST=12) if retry_needed else dict(DELIVERY=128,LOST=128)}
    for op in core.OPERATORS:model['tables'][op]=[dict(context=case,counts=counts[op])]
    model['observations_used']=768
    model=core.fit(model,'REVISED',Counter())
    return model,case,core.make_plan(model,case,Counter())

def test_point_objective_is_whole_policy_wait_mixture():
    plan=dict(pure_vectors={'WAIT':(F(0),F(0),F(0)),
                           'SHORT':(-F(1,10),F(1,2),F(1,2)),
                           'DETOUR_RETURN':(-F(1,20),F(1,100),F(4,5))})
    scores=core.point_scores(plan)
    assert scores['SHORT']==F(19,100) and scores['DETOUR_RETURN']==F(63,20)

def test_sufficient_return_is_preferred_to_optional_retry():
    model,case,plan=fixture()
    # A more rewarding retry is not necessary once one-operator RETURN suffices.
    plan['pure_vectors']['DETOUR_RETRY']=(-F(1,20),F(1,100),F(9,10))
    choice=core.choose(model,case,plan,Counter())
    assert choice['policy']=='DETOUR_RETURN' and choice['operator']=='DETOUR_PASS'
    assert choice['policy_scores']['DETOUR_RETRY']>choice['policy_scores']['DETOUR_RETURN']
    assert choice['sensitivity_scores'] is None

def test_required_retry_forecast_never_injects_evidence():
    model,case,plan=fixture(retry_needed=True)
    before_model,before_plan=deepcopy(model),deepcopy(plan)
    work=Counter();choice=core.choose(model,case,plan,work)
    assert choice['policy']=='DETOUR_RETRY' and work['sensitivity_candidates']==2
    assert set(choice['sensitivity_scores'])=={'DETOUR_PASS','RECOVERY_RETRY'}
    assert model==before_model and plan==before_plan
    assert all(type(n) is int for rows in model['tables'].values() for r in rows for n in r['counts'].values())

def test_independent_targeting_and_member_pilot():
    for needed in (False,True):
        model,case,plan=fixture(needed)
        assert core.choose(model,case,plan,Counter())==replay.choose(model,case,plan,Counter())
        target=dict(case,operating='high',id='new')
        plan=core.make_plan(model,target,Counter())
        actual=core.choose(model,target,plan,Counter())
        assert actual==replay.choose(model,target,plan,Counter())
        assert actual['pilot'] and actual['operator']=='SHORT_PASS'
