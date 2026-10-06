from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import oracle_gap_pool_v231 as core


def counts():
    return {'SHORT_PASS': {'DELIVERY': 350, 'LOST': 34},
            'DETOUR_PASS': {'DELIVERY': 326, 'LOST': 4, 'RECOVERY': 54},
            'RECOVERY_RETRY': {'DELIVERY': 96, 'LOST': 288}}


def test_actual_batch_enters_pool_once_and_current_member_remains_separate():
    anchors, work = [counts() for _ in range(3)], Counter()
    state = core.prepare(anchors, 0, work)
    case = dict(context='A', operating='high', retry_cost='19/20')
    member = core.empty()
    increments = {'DELIVERY': 14, 'LOST': 2}
    core.observe(state, case, 1, 'SHORT_PASS', increments)
    member['SHORT_PASS'] = deepcopy(increments)
    before = deepcopy(state)
    plan = core.make_plan(member, case, state, 1, 3, work)
    constraints = plan['joint_constraints']['SHORT_PASS']
    assert [sum(row['counts'].values()) for row in constraints] == [384, 400, 16]
    assert plan['effective_n']['SHORT_PASS'] == 400
    assert all(sum(state['a']['pools'][i]['SHORT_PASS'].values()) == 384 for i in (0, 2))
    assert state == before and anchors == [counts() for _ in range(3)]
    assert all(row['policy'] == plan['queries'][q]['policy']
               for q, row in plan['query_certificates'].items())


def test_b_updates_cannot_overwrite_a_and_changed_row_does_not_inherit():
    state, work = core.prepare([counts() for _ in range(3)], 2, Counter()), Counter()
    a_before = deepcopy(state['a'])
    core.begin_b(state, [counts() for _ in range(3)], 'RECOVERY_RETRY', (2, 0, 1), work)
    case = dict(context='B', operating='low', retry_cost='17/20')
    core.observe(state, case, 0, 'RECOVERY_RETRY', {'DELIVERY': 16, 'LOST': 0})
    region = core.regions(core.empty(), case, state, 0, 30)
    assert len(region['RECOVERY_RETRY']) == 3
    assert len(region['SHORT_PASS']) == 5
    assert region['SHORT_PASS'][-1]['event'] == 'l2/A/pool2/SHORT_PASS'
    assert core.point_counts(case, state, 0)['SHORT_PASS']['DELIVERY'] == 700
    assert core.point_counts(case, state, 0)['RECOVERY_RETRY']['DELIVERY'] == 112
    assert state['a'] == a_before == state['a_at_switch']
    a_case = dict(case, context='A')
    assert core.bank(state, a_case) == a_before


def test_balanced_stop_has_separate_goal_and_query_conditions():
    member = core.empty()
    member['SHORT_PASS']['DELIVERY'] = 16
    plan = dict(utility_lower=F(3), goal_impossible=False, query_ready=False)
    assert core.balanced(member, plan, 16)['operator'] == 'DETOUR_PASS'
    assert core.balanced(member, dict(plan, query_ready=True), 16) is None
    assert core.balanced(member, plan, 384) is None
    assert core.ready(dict(plan, utility_lower=F(0), goal_impossible=True, query_ready=True))
