"""The sole treatment is skipping currently jointly ready types."""
from copy import deepcopy

from acfqp.science import joint_unresolved_trajectory_v255 as core


def records():
    return [dict(identity=identity,cost_index=cost,trajectory=dict(all_ready=True))
        for identity in range(3) for cost in range(4)]


def test_all_eligible_is_exact_same_cursor_and_type_sequence():
    rr, adaptive = 2, 2
    for _ in range(20):
        before = core.select_type(rr,core.eligible_types('DIRECT_RR',[False]*3))
        after = core.select_type(adaptive,core.eligible_types('DIRECT_JOINT_UNRESOLVED',[False]*3))
        assert before == after
        identity, rr = before
        _, adaptive = after
        assert rr == identity+1


def test_skip_uses_cyclic_cursor_not_type_paid_scores_or_restarts():
    eligible = core.eligible_types('DIRECT_JOINT_UNRESOLVED',[False,True,False])
    cursor, sequence = 1, []
    for _ in range(6):
        identity,cursor = core.select_type(cursor,eligible)
        sequence.append(identity)
    assert sequence == [2,0,2,0,2,0]
    assert core.eligible_types('DIRECT_RR',[True,False,True]) == [0,1,2]


def test_all_four_costs_and_current_readiness_are_required_without_latching():
    cases = records()
    original = deepcopy(cases)
    cases[6]['trajectory']['all_ready'] = False
    assert core.ready_by_type(cases) == [True,False,True]
    assert core.eligible_types('DIRECT_JOINT_UNRESOLVED',core.ready_by_type(cases)) == [1]
    cases[6]['trajectory']['all_ready'] = True
    assert core.ready_by_type(cases) == [True]*3
    cases[10]['trajectory']['all_ready'] = False
    assert core.ready_by_type(cases) == [True,True,False]
    assert core.eligible_types('DIRECT_JOINT_UNRESOLVED',core.ready_by_type(cases)) == [2]
    assert all(row['trajectory']['all_ready'] for row in original)
