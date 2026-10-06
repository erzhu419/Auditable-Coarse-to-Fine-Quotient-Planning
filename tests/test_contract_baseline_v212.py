from collections import Counter
from copy import deepcopy
from fractions import Fraction
from acfqp.science import contract_baseline_v212 as core
from scripts import analyze_contract_baseline_v212 as replay

def test_direct_uses_only_weather_real_counts_and_no_condition_search():
    model=core.empty();case=dict(id='x',weather='wet',operating='high',retry_cost='17/20')
    for weather in ('normal','wet'):
        context=dict(case,weather=weather)
        for op in core.OPERATORS:
            counts={cat:16 if i==(0 if weather=='wet' else 1) else 0 for i,cat in enumerate(core.ALPHABETS[op])}
            core.update(model,context,op,counts,Counter())
    before=deepcopy(model);work=Counter();fitted=core.fit(model,'DIRECT',work)
    expected=replay.fitted(model,'DIRECT',Counter())
    for key in ('tables','selected_fields','scores','observations_used','certificate_fields'):
        assert replay.independent.equal_numbers(fitted[key],expected[key])
    assert work['score_candidates']==0 and model==before
    a=core.make_plan(fitted,case,Counter());b=core.make_plan(fitted,dict(case,operating='low'),Counter())
    assert a['envelopes']==b['envelopes']
    assert all(e['n']==16 for e in a['envelopes'].values())
    assert replay.independent.exact_json(a)==replay.independent.exact_json(replay.make_plan(fitted,case,Counter()))

def test_direct_stops_without_strategic_maintenance():
    model=core.fit(core.empty(),'DIRECT',Counter());case=dict(weather='wet',operating='low',retry_cost='17/20')
    plan=dict(utility_lower=Fraction(2))
    assert core.next_choice(model,case,plan,'DIRECT',0,Counter()) is None
    assert replay.next_choice(model,case,plan,'DIRECT',0,Counter()) is None
