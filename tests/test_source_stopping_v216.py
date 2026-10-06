from collections import Counter
from acfqp.science import source_stopping_v216 as core

CASE = dict(id='opaque', operating='high', retry_cost='19/20')


def test_source_certificate_does_not_skip_unobserved_operators():
    member = core.empty()
    member['SHORT_PASS']['DELIVERY'] = 384
    plan = core.make_plan(member, [], CASE, 'EARLY', Counter())
    assert plan['utility_lower'] >= 2
    choice = core.choose(member, [], CASE, 'EARLY', plan, 384, Counter(), source=True)
    assert choice['reason'] == 'calibration_pilot' and choice['operator'] == 'DETOUR_PASS'


def test_certified_source_stops_but_full_control_keeps_paying():
    member = core.empty()
    for op, n in zip(core.OPERATORS, (384, 32, 32)):
        member[op]['DELIVERY'] = n
    plan = core.make_plan(member, [], CASE, 'EARLY', Counter())
    assert plan['utility_lower'] >= 2
    assert core.choose(member, [], CASE, 'EARLY', plan, 448, Counter(), source=True) is None
    assert core.choose(member, [], CASE, 'ORACLE', plan, 448, Counter(), source=True) is None
    assert core.choose(member, [], CASE, 'FULL', plan, 448, Counter(), source=True)['reason'] == 'calibration_balance'


def test_weak_source_keeps_refining_until_cap():
    member = dict(SHORT_PASS=dict(DELIVERY=339, LOST=45),
                  DETOUR_PASS=dict(DELIVERY=327, LOST=8, RECOVERY=49),
                  RECOVERY_RETRY=dict(DELIVERY=80, LOST=240))
    plan = core.make_plan(member, [], CASE, 'EARLY', Counter())
    assert plan['utility_lower'] < 2
    assert core.choose(member, [], CASE, 'EARLY', plan, 1088, Counter(), source=True)['operator'] == 'DETOUR_PASS'
    assert core.choose(member, [], CASE, 'EARLY', plan, 1152, Counter(), source=True) is None


def test_target_stop_and_plan_math_are_unchanged():
    anchors = [core.empty()]
    for op in core.OPERATORS:
        anchors[0][op]['DELIVERY'] = 384
    member = core.empty()
    early = core.make_plan(member, anchors, CASE, 'EARLY', Counter())
    full = core.make_plan(member, anchors, CASE, 'FULL', Counter())
    assert early == full and early['query_ready']
    assert core.choose(member, anchors, CASE, 'EARLY', early, 0, Counter()) is None
    assert core.choose(member, anchors, CASE, 'FULL', full, 0, Counter()) is None
