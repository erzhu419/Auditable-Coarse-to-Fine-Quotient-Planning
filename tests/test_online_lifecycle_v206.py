from collections import Counter
from copy import deepcopy
from fractions import Fraction
import math
from acfqp.science import online_lifecycle_v206 as core
from acfqp.science import continual_route_kernels_v202 as original
from scripts import analyze_online_lifecycle_v206 as replay
from scripts import analyze_conditioned_mechanisms_v205 as independent

def fixture():
    model=core.empty()
    for weather,counts in [('normal',{'DELIVERY':14,'LOST':2}),('wet',{'DELIVERY':16,'LOST':0})]:
        case=dict(id=weather,weather=weather,operating='high',retry_cost='17/20')
        core.update(model,case,'SHORT_PASS',counts,Counter())
    return model

def test_sufficient_count_fit_matches_original_event_likelihood():
    model=fixture(); events=[]
    for op,rows in model['tables'].items():
        for row in rows:
            for cat,n in row['counts'].items():
                events += [dict(context=row['context'],operator=op,successor=cat)]*n
    expected=original.fit([events],'REVISED')
    untouched=deepcopy(model);actual=core.fit(model,'REVISED',Counter())
    assert actual['selected_fields']==expected['selected_fields'] and actual['scores']==expected['scores']
    assert model==untouched and actual['observations_used']==32

def test_empty_local_pilots_and_persistent_fields():
    model=core.fit(core.empty(),'LOCAL',Counter())
    case=dict(id='new',weather='wet',operating='low',retry_cost='17/20')
    assert core.choose(model,case,core.make_plan(model,case,Counter()))['operator']=='SHORT_PASS'
    core.update(model,case,'SHORT_PASS',{'DELIVERY':16,'LOST':0},Counter())
    model=core.fit(model,'LOCAL',Counter())
    choice=core.choose(model,case,core.make_plan(model,case,Counter()))
    assert choice['operator']=='DETOUR_PASS' and choice['pilot']
    assert all(fields==list(core.FIELDS) for fields in model['selected_fields'].values())

def test_larger_prefix_family_and_independent_bounds():
    assert core.BETA==math.log(2*2016/.05)
    assert core.interval(0,0,Counter())==(Fraction(0),Fraction(1))
    for k,n in [(0,16),(3,128),(16,16)]:
        assert core.interval(k,n,Counter())==independent.interval(k,n,Counter())

def test_independent_online_selection_and_joint_plan():
    model=fixture();case=dict(id='target',weather='wet',operating='low',retry_cost='17/20')
    for arm in ('REVISED','LOCAL','GLOBAL'):
        fitted=core.fit(model,arm,Counter()); rebuilt=replay.fitted(model,arm,Counter())
        assert fitted['selected_fields']==rebuilt['selected_fields'] and fitted['scores']==rebuilt['scores']
        plan=core.make_plan(fitted,case,Counter());expected=independent.make_plan(rebuilt,case,Counter())
        assert independent.exact_json(plan)==independent.exact_json(expected)
