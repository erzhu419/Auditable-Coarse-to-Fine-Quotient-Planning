from collections import Counter
from fractions import Fraction as F
from acfqp.science import query_calibration_v215 as core

CASE = dict(id='opaque', operating='high', retry_cost='19/20')


def test_source_pilot_observes_every_operator_before_targeting():
    member = core.empty()
    for step in range(6):
        choice = core.choose(member, [], CASE, 'CALIBRATE', {}, step*16, Counter(), source=True)
        assert choice['reason'] == 'calibration_pilot'
        assert choice['operator'] == core.OPERATORS[step % 3]
        member[choice['operator']]['DELIVERY'] += 16


def test_retained_weak_detour_is_refined_instead_of_balancing_retry():
    member = dict(SHORT_PASS=dict(DELIVERY=339, LOST=45),
                  DETOUR_PASS=dict(DELIVERY=327, LOST=8, RECOVERY=49),
                  RECOVERY_RETRY=dict(DELIVERY=80, LOST=240))
    plan = core.make_plan(member, [], CASE, 'CALIBRATE', Counter())
    assert plan['utility_lower'] < 2
    choice = core.choose(member, [], CASE, 'CALIBRATE', plan, 1088, Counter(), source=True)
    assert choice['reason'] == 'calibration_certificate'
    assert choice['operator'] == 'DETOUR_PASS'


def test_paid_source_continues_after_certificate_and_rechecks_each_batch():
    member = core.empty()
    for op in core.OPERATORS:
        member[op]['DELIVERY'] = 320
    plan = core.make_plan(member, [], CASE, 'CALIBRATE', Counter())
    assert plan['utility_lower'] >= 2
    choice = core.choose(member, [], CASE, 'CALIBRATE', plan, 960, Counter(), source=True)
    assert choice['reason'] == 'calibration_balance'
    assert core.choose(member, [], CASE, 'CALIBRATE', plan, 1152, Counter(), source=True) is None
    weak = dict(SHORT_PASS=dict(DELIVERY=339, LOST=45),
                DETOUR_PASS=dict(DELIVERY=327, LOST=8, RECOVERY=49),
                RECOVERY_RETRY=dict(DELIVERY=80, LOST=240))
    plan = core.make_plan(weak, [], CASE, 'CALIBRATE', Counter())
    assert core.choose(weak, [], CASE, 'CALIBRATE', plan, 1088, Counter(), source=True)['reason'] == 'calibration_certificate'


def test_target_preserves_query_set_stop_at_budget_end():
    plan = dict(query_ready=True)
    assert core.choose(core.empty(), [], CASE, 'CALIBRATE', plan, 384, Counter()) is None
