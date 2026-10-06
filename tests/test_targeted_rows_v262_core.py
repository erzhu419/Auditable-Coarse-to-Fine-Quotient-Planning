"""Focused V262 core checks: native row provenance and one joint proof."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

import pytest

from acfqp.science import targeted_rows_v262 as core

S, D, R = core.OPERATORS
CASE = dict(context='A', stage='A', operating='low', retry_cost='17/20')


def one(category, operator):
    return {name: int(name == category) for name in core.ALPHABETS[operator]}


def test_direct_row_updates_native_pool_without_creating_unit_or_path_stats():
    state = core.prepare(0, 'DIRECT_ROW_REUSE', Counter())
    before_trajectory = deepcopy(state['trajectory'])
    before_rounds = deepcopy(state['round_log'])

    core.observe_direct_row(state, 'A', 0, R, one('DELIVERY', R))

    assert state['a']['pools'][0][R]['DELIVERY'] == 1
    assert state['direct_row_counts']['A'][0][R]['DELIVERY'] == 1
    assert len(state['direct_row_log']) == 1
    assert set(state['direct_row_log'][0]) == {
        'direct_row_index', 'context', 'identity', 'operator', 'increments'}
    assert state['round_log'] == before_rounds
    assert state['trajectory'] == before_trajectory
    assert 'policy_path_stats' not in state


def test_direct_rows_are_only_legal_on_direct_arm():
    state = core.prepare(0, 'FULL_UNIT_ROW_CS', Counter())
    with pytest.raises(ValueError, match='DIRECT_ROW_REUSE'):
        core.observe_direct_row(state, 'A', 0, D, one('DELIVERY', D))


def test_unresolved_row_target_is_frozen_by_query_and_execution_state():
    assert core.targeted_rows_for_unresolved(dict(
        utility_lower=F(0), goal_impossible=False, query_ready=False)) == core.OPERATORS
    assert core.targeted_rows_for_unresolved(dict(
        utility_lower=F(2), goal_impossible=False, query_ready=False)) == (D, R)
    assert core.targeted_rows_for_unresolved(dict(
        utility_lower=F(2), goal_impossible=False, query_ready=True)) == ()
    assert core.targeted_rows_for_unresolved(dict(
        utility_lower=F(0), goal_impossible=True, query_ready=False)) == (D, R)


def test_exact_return_retry_risk_factor():
    assert core.return_retry_risk_gap(F(1, 3), F(3, 4), F(17, 20)) == F(23, 60)
    assert core.return_retry_risk_gap(F(2, 5), F(1), F(19, 20)) == F(61, 50)


def test_joint_certificate_contains_exact_risk_recovery_coefficient():
    state = core.prepare(0, 'DIRECT_ROW_REUSE', Counter())
    constraints = core.regions(core.empty(), CASE, state, 0, 3)
    chosen = {
        'reward': {'policy': 'WAIT'},
        'goal': {'policy': 'DETOUR_RETURN'},
        'risk': {'policy': 'DETOUR_RETURN'},
    }
    certificate = core.query_confidence.certificates(CASE, constraints, chosen, Counter())
    rows = [row for row in certificate['support_records']
            if row['query'] == 'risk' and row['chosen'] == 'DETOUR_RETURN'
            and row['other'] == 'DETOUR_RETRY' and row['retry_delivery'] == F(1)]
    assert rows
    expected = 8 * F(1) - 4 - F(CASE['retry_cost'])
    assert all(row['weights']['RECOVERY'] == expected for row in rows)


@pytest.mark.parametrize('arm', core.ARMS)
def test_all_arms_use_native_points_and_unified_row_proof(arm):
    state = core.prepare(0, arm, Counter())
    plan = core.make_plan(core.empty(), CASE, state, 0, 3, {}, Counter())
    assert plan['query_proof_method'] == 'unified_native_joint_row_cs_v262'
    assert plan['row_confidence_kind'] == 'unified_native_joint_row_cs_v262'
    assert plan['query_evidence']['method'] == 'unified_native_joint_row_cs_v262'
    assert plan['query_point_method'] == 'native_row_posterior_means'
    comparisons = [comparison for decision in plan['query_evidence']['queries'].values()
                   for comparison in decision.get('comparisons', ())]
    assert comparisons
    assert all(row['score_source'] == 'native_joint_row_cs' for row in comparisons)
    assert all('admitted_unit_ids' not in row and 'admitted_round_ids' not in row
               for row in comparisons)


def test_direct_row_changes_native_point_counts_but_not_trajectory_history():
    state = core.prepare(0, 'DIRECT_ROW_REUSE', Counter())
    before = core.make_plan(core.empty(), CASE, state, 0, 3, {}, Counter())
    core.observe_direct_row(state, 'A', 0, D, one('DELIVERY', D))
    core.observe_direct_row(state, 'A', 0, R, one('DELIVERY', R))
    after = core.make_plan(core.empty(), CASE, state, 0, 3, {}, Counter())
    assert after['native_row_counts'][D]['DELIVERY'] == 1
    assert after['native_row_counts'][R]['DELIVERY'] == 1
    assert after['native_complete_rounds'] == before['native_complete_rounds'] == 0
    assert state['round_log'] == []
