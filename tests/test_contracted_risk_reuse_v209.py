from collections import Counter
from copy import deepcopy
from acfqp.science import contracted_risk_reuse_v209 as core
from scripts import analyze_contracted_risk_reuse_v209 as replay

def test_contract_pooling_and_weather_boundary():
    source=dict(id='source',weather='wet',operating='high',retry_cost='17/20')
    target=dict(source,id='target',operating='low',retry_cost='19/20')
    model=core.empty()
    for op in core.OPERATORS:
        model['tables'][op]=[dict(context=source,counts={cat:16 if i==0 else 0 for i,cat in enumerate(core.ALPHABETS[op])})]
    before=deepcopy(model)
    for arm in ('REVISED','LOCAL','GLOBAL'):
        fitted=core.fit(model,arm,Counter());plan=core.make_plan(fitted,target,Counter())
        assert replay.independent.exact_json(plan)==replay.independent.exact_json(replay.make_plan(fitted,target,Counter()))
        assert plan['envelopes']['SHORT_PASS']['n']==(16 if arm=='REVISED' else 0)
        assert core.make_plan(fitted,dict(target,weather='blocked'),Counter())['envelopes']['SHORT_PASS']['n']==0
    assert model==before

def test_same_learner_different_evidence_contract():
    a,b=(core.fit(core.empty(),arm,Counter()) for arm in ('REVISED','LOCAL'))
    for key in ('selected_fields','scores','tables','observations_used'): assert a[key]==b[key]
    assert a['certificate_fields']!=b['certificate_fields']
