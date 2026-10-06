from collections import Counter
from copy import deepcopy
from fractions import Fraction
from math import log
from acfqp.science import strategic_maintenance_v210 as core
from scripts import analyze_strategic_maintenance_v210 as replay

def fixture():
    model=core.empty();case=dict(weather='normal',operating='low',retry_cost='17/20',id='a')
    for weather in ('normal','wet'):
        context=dict(case,weather=weather)
        for op in core.OPERATORS:
            counts={cat:16 if i==0 else 0 for i,cat in enumerate(core.ALPHABETS[op])}
            model['tables'][op].append(dict(context=context,counts=counts))
    model["observations_used"]=96
    return core.fit(model,'REVISED',Counter()),case

def test_contract_excludes_reward_fields_and_independent_fit():
    model,case=fixture()
    expected=replay.fitted(dict(tables=model['tables']),'REVISED',Counter())
    for key in ('tables','selected_fields','scores','certificate_fields','observations_used'):
        assert replay.independent.equal_numbers(model[key],expected[key])
    assert all(set(r['fields'])<= {'weather'} for scores in model['scores'].values() for r in scores)

def test_certificate_and_maintenance_have_distinct_stops():
    model,case=fixture();plan=dict(utility_lower=Fraction(2))
    before=deepcopy(model)
    for arm in ('REVISED','LOCAL','BASE'):
        choice=core.next_choice(model,case,plan,arm,0,Counter())
        assert choice==replay.next_choice(model,case,plan,arm,0,Counter())
        assert (choice is None)==(arm=='BASE')
        assert core.next_choice(model,case,plan,arm,384,Counter()) is None
    assert model==before
    model['scores']['DETOUR_PASS'][1]['score']=model['scores']['DETOUR_PASS'][0]['score']+log(20)+1
    assert core.next_choice(model,case,plan,'REVISED',0,Counter()) is None
