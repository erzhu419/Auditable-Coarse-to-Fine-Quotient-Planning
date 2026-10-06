from collections import Counter
from fractions import Fraction as F
from acfqp.science import query_sufficient_v214 as core

def anchor(short,detour):
    row=core.empty()
    row['SHORT_PASS']=dict(DELIVERY=short,LOST=384-short)
    row['DETOUR_PASS']=dict(DELIVERY=detour,LOST=384-detour,RECOVERY=0)
    row['RECOVERY_RETRY']=dict(DELIVERY=384,LOST=0)
    return row

def case():return dict(id='opaque',operating='low',retry_cost='17/20')

def test_proxy_takes_worst_whole_candidate_not_mean_oracle():
    anchors=[anchor(384,0),anchor(0,384)]
    plan=dict(candidates=[0,1],pure_vectors={'WAIT':[F(0)]*3,'SHORT':[-F(1,10),F(1,4),F(3,4)],
          'DETOUR_RETURN':[-F(1,20),F(3,4),F(1,4)],'DETOUR_RETRY':[-F(1,20),F(3,4),F(1,4)]})
    assert core.query_proxy(core.empty(),anchors,case(),plan,Counter())>4

def test_single_candidate_query_regret_zero():
    anchors=[anchor(384,0)]
    plan=core.make_plan(core.empty(),anchors,case(),'ORACLE',Counter(),identity=0)
    assert plan['query_proxy']==0 and plan['query_ready']

def test_soft_stop_preserves_paid_source_and_handles_budget_end():
    anchors=[anchor(384,0),anchor(0,384)]
    plan=dict(query_ready=True)
    assert core.choose(core.empty(),anchors,case(),'SET',plan,0,Counter()) is None
    assert core.choose(core.empty(),anchors,case(),'SET',plan,384,Counter()) is None
    assert core.choose(core.empty(),anchors,case(),'SET',plan,0,Counter(),source=True)['reason']=='paid_anchor'
