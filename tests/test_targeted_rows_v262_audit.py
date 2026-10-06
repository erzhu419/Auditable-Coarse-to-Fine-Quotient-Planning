"""Focused independent checks for V262 direct native row acquisition."""
from collections import Counter
from fractions import Fraction as F
import pytest
from scripts import audit_targeted_rows_v262 as audit
from acfqp.science import targeted_rows_v262 as core


def test_direct_rows_are_native_ledger_only():
    state = core.prepare(0, audit.ARMS[0], Counter())
    core.observe_direct_row(state, 'A', 0, audit.D, {'DELIVERY': 1, 'LOST': 0, 'RECOVERY': 0})
    core.observe_direct_row(state, 'A', 0, audit.R, {'DELIVERY': 1, 'LOST': 0})
    assert len(state['direct_row_log']) == 2 and state['round_log'] == []
    assert state['trajectory']['A'][0]['rounds'] == []
    assert state['direct_row_counts']['A'][0][audit.D]['DELIVERY'] == 1
    with pytest.raises(ValueError):
        core.observe_direct_row(state, 'A', 0, audit.D, {'DELIVERY': 2, 'LOST': 0, 'RECOVERY': 0})


def test_targeted_rows_choose_execution_then_query_rows():
    assert core.targeted_rows_for_unresolved(dict(utility_lower=F(1), goal_impossible=False, query_ready=False)) == audit.OPERATORS
    assert core.targeted_rows_for_unresolved(dict(utility_lower=F(2), goal_impossible=False, query_ready=False)) == (audit.D, audit.R)
    assert core.targeted_rows_for_unresolved(dict(utility_lower=F(2), goal_impossible=False, query_ready=True)) == ()


def test_exact_return_retry_gap_factor():
    assert core.return_retry_risk_gap(F(3, 10), F(7, 10), '17/20') == F(3, 10) * (8*F(7,10)-4-F(17,20))


def test_unified_query_plan_has_single_joint_row_cs_and_no_unit_ids():
    state = core.prepare(0, audit.ARMS[0], Counter())
    case = dict(id='point', context='A', stage='A', operating='low', retry_cost='17/20')
    plan = core.make_plan(core.empty(), case, state, 0, 3, {}, Counter())
    assert plan['query_proof_method'] == 'unified_native_joint_row_cs_v262'
    assert plan['query_evidence']['method'] == 'unified_native_joint_row_cs_v262'
    comparisons = [c for q in plan['query_evidence']['queries'].values() for c in q.get('comparisons', [])]
    assert all(c['score_source'] == 'native_joint_row_cs' for c in comparisons)
    assert all('admitted_unit_ids' not in c and 'admitted_round_ids' not in c for c in comparisons)


def test_direct_rows_update_native_point_counts_but_not_trajectory():
    state = core.prepare(0, audit.ARMS[0], Counter())
    core.observe_direct_row(state, 'A', 0, audit.S, {'DELIVERY': 1, 'LOST': 0})
    core.observe_direct_row(state, 'A', 0, audit.D, {'DELIVERY': 1, 'LOST': 0, 'RECOVERY': 0})
    assert state['round_log'] == [] and state['trajectory']['A'][0]['rounds'] == []
    assert state['a']['pools'][0][audit.S]['DELIVERY'] == 1


@pytest.mark.parametrize('arm', audit.ARMS)
def test_all_three_arms_share_unified_row_cs_metadata(arm):
    state = core.prepare(0, arm, Counter())
    case = dict(id='point', context='A', stage='A', operating='low', retry_cost='17/20')
    plan = core.make_plan(core.empty(), case, state, 0, 3, {}, Counter())
    assert plan['row_confidence_kind'] == 'unified_native_joint_row_cs_v262'
    assert plan['query_evidence']['event_allocation']['shared_with_execution_cs']
