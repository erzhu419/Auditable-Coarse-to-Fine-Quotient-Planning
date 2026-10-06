from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from acfqp.science import latent_mechanisms_v213 as core
from acfqp.science import latent_route_task_v213 as task

def case():return dict(id='opaque',operating='low',retry_cost='17/20')

def test_joint_candidate_bounds_and_cost_is_reward_only():
    anchors=[]
    for delivery in (320,96):
        counts=core.empty()
        counts['SHORT_PASS']={'DELIVERY':delivery,'LOST':384-delivery}
        counts['DETOUR_PASS']={'DELIVERY':300,'LOST':4,'RECOVERY':80}
        counts['RECOVERY_RETRY']={'DELIVERY':384-delivery,'LOST':delivery}
        anchors.append(counts)
    member=core.empty();before=deepcopy(anchors)
    a=core.make_plan(member,anchors,case(),'LATENT',Counter())
    b=core.make_plan(member,anchors,dict(case(),operating='high'),'LATENT',Counter())
    assert a['candidates']==[0,1] and a['envelopes']==b['envelopes'] and anchors==before
    for name in a['risks']:
        assert a['risks'][name]==max(core.robust.risk_bounds(block,Counter())[name] for block in a['candidate_envelopes'].values())
        assert a['goals_lower'][name]==min(core.robust.goals_lower(block,case(),Counter())[name] for block in a['candidate_envelopes'].values())

def test_identity_and_calibration_stopping_are_not_free():
    plan=dict(utility_lower=F(2),candidates=[0,1])
    anchors=[core.empty(),core.empty()]
    assert core.choose(core.empty(),anchors,case(),'LATENT',plan,0,Counter()) is not None
    assert core.choose(core.empty(),anchors,case(),'LATENT',plan,1152,Counter(),source=True) is None
    assert core.choose(core.empty(),anchors,case(),'LATENT',plan,1136,Counter(),source=True)['reason']=='paid_anchor'
    plan['candidates']=[0]
    assert core.choose(core.empty(),anchors,case(),'LATENT',plan,0,Counter()) is None

def test_public_roster_does_not_supply_identity_or_weather():
    for life in (0,1):
        cases,laws,identities=task.world(life)
        assert len(cases)==27 and identities[:3]==[0,1,2]
        assert all(set(c)=={'id','operating','retry_cost'} for c in cases)
        assert all(identities[3:].count(i)==8 for i in range(3))
