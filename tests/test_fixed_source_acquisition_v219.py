from collections import Counter
from copy import deepcopy

from acfqp.science import fixed_source_acquisition_v219 as core


CASE = dict(id='opaque', operating='low', retry_cost='19/20')


def source_bound_fixture():
    # Retained V217 life1/task10 evidence exposes a tempting source revisit.
    member = dict(SHORT_PASS=dict(DELIVERY=31, LOST=17),
                  DETOUR_PASS=dict(DELIVERY=154, LOST=4, RECOVERY=34),
                  RECOVERY_RETRY=dict(DELIVERY=9, LOST=7))
    anchors = [
        dict(SHORT_PASS=dict(DELIVERY=29, LOST=3),
             DETOUR_PASS=dict(DELIVERY=277, LOST=4, RECOVERY=39),
             RECOVERY_RETRY=dict(DELIVERY=9, LOST=23)),
        dict(SHORT_PASS=dict(DELIVERY=18, LOST=14),
             DETOUR_PASS=dict(DELIVERY=252, LOST=3, RECOVERY=49),
             RECOVERY_RETRY=dict(DELIVERY=10, LOST=22)),
        dict(SHORT_PASS=dict(DELIVERY=175, LOST=1),
             DETOUR_PASS=dict(DELIVERY=26, LOST=2, RECOVERY=4),
             RECOVERY_RETRY=dict(DELIVERY=27, LOST=5)),
    ]
    return member, anchors


def full_source_fixture():
    # V218 life0 FULL source rows reused as V219's fixed paid evidence.
    return [
        dict(SHORT_PASS=dict(DELIVERY=243, LOST=141),
             DETOUR_PASS=dict(DELIVERY=307, LOST=5, RECOVERY=88),
             RECOVERY_RETRY=dict(DELIVERY=157, LOST=211)),
        dict(SHORT_PASS=dict(DELIVERY=378, LOST=6),
             DETOUR_PASS=dict(DELIVERY=250, LOST=58, RECOVERY=76),
             RECOVERY_RETRY=dict(DELIVERY=334, LOST=50)),
        dict(SHORT_PASS=dict(DELIVERY=341, LOST=43),
             DETOUR_PASS=dict(DELIVERY=320, LOST=6, RECOVERY=58),
             RECOVERY_RETRY=dict(DELIVERY=95, LOST=289)),
    ]


def test_mean_cannot_dispatch_source_or_change_fixed_evidence():
    member, anchors = source_bound_fixture()
    plan = core.make_plan(member, anchors, CASE, 'MEAN', Counter())
    before = deepcopy((member, anchors, plan))
    choice = core.choose(member, anchors, CASE, 'MEAN', plan, 256, Counter())
    assert choice['scope'] == 'TARGET' and choice['source_index'] is None
    assert all(score['scope'] == 'TARGET' and score['source_index'] is None
               for score in choice['scores'])
    assert (member, anchors, plan) == before


def test_same_evidence_produces_same_plan_and_stopping_conditions():
    anchors = full_source_fixture()
    member = dict(SHORT_PASS=dict(DELIVERY=31, LOST=17),
                  DETOUR_PASS=dict(DELIVERY=154, LOST=4, RECOVERY=34),
                  RECOVERY_RETRY=dict(DELIVERY=9, LOST=7))
    plans = {arm: core.make_plan(member, anchors, CASE, arm, Counter())
             for arm in ('MEAN', 'SET')}
    assert plans['MEAN'] == plans['SET']
    capped_member, weak_anchors = source_bound_fixture()
    cap_plans = {arm: core.make_plan(capped_member, weak_anchors, CASE, arm, Counter())
                 for arm in ('MEAN', 'SET')}
    assert cap_plans['MEAN'] == cap_plans['SET']
    assert not cap_plans['MEAN']['query_ready']
    for arm, plan in cap_plans.items():
        assert core.choose(capped_member, weak_anchors, CASE, arm, plan, 384, Counter()) is None

    # This supported dry-task history separates the family and certifies SHORT.
    ready_member = dict(SHORT_PASS=dict(DELIVERY=320, LOST=0),
                        DETOUR_PASS=dict(DELIVERY=12, LOST=2, RECOVERY=2),
                        RECOVERY_RETRY=dict(DELIVERY=14, LOST=2))
    ready_plans = {arm: core.make_plan(ready_member, anchors, CASE, arm, Counter())
                   for arm in ('MEAN', 'SET')}
    assert ready_plans['MEAN'] == ready_plans['SET']
    assert ready_plans['MEAN']['candidates'] == [1]
    assert ready_plans['MEAN']['query_ready']
    for arm, plan in ready_plans.items():
        assert core.choose(ready_member, anchors, CASE, arm, plan, 352, Counter()) is None
