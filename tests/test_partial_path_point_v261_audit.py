"""Independent path-count, conditional-cost and unchanged-certificate replay."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

import pytest

from scripts import audit_partial_path_point_v261 as audit
from acfqp.science import partial_path_point_v261 as core


def unit(identifier, declared, outcomes, context='A', identity=0, phase='SHARED'):
    return dict(round_id=identifier, phase=phase, context=context, identity=identity,
        declared_rows=list(declared), outcomes=outcomes)


def point_fixture(arm, units):
    state = core.prepare(0, arm, Counter())
    for record in units:
        core.observe_unit(state, record)
    case = dict(id='point', context='A', stage='A', operating='low', retry_cost='17/20')
    saved = core.query_plan(state, case, 0, {}, Counter())
    replay = audit.state_for(0)
    replay['rounds'] = deepcopy(units)
    return saved, case, replay


def point_failures(saved, case, replay, arm):
    failures = []
    audit.audit_query_point(saved, case, 0, replay, arm, {},
        lambda name, ok: failures.append(name) if not ok else None)
    return failures


def test_policy_counts_admit_declared_paths_and_exclude_other_contexts_and_phases():
    units = [unit(1, (audit.S,), {audit.S: 'DELIVERY'}),
        unit(2, (audit.S, audit.D), {audit.S: 'LOST', audit.D: 'DELIVERY'}),
        unit(3, (audit.D,), {audit.D: 'LOST'}),
        unit(4, (audit.D, audit.R), {audit.D: 'DELIVERY', audit.R: None}),
        unit(5, (audit.D, audit.R), {audit.D: 'RECOVERY', audit.R: 'LOST'}),
        unit(6, (audit.S,), {audit.S: 'LOST'}, 'B'),
        unit(7, (audit.S,), {audit.S: 'LOST'}, identity=1),
        unit(8, (audit.S,), {audit.S: 'LOST'}, phase='MEMBER'),
        unit(9, (audit.S,), {audit.S: 'LOST'}, phase='EXECUTION')]
    stats = audit.policy_path_statistics(units, 'A', 0)
    assert stats == dict(
        SHORT=dict(n=2, delivery=1, failure=1, recovery_calls=0, last_unit_id=2),
        DETOUR_RETURN=dict(n=4, delivery=2, failure=1, recovery_calls=0, last_unit_id=5),
        DETOUR_RETRY=dict(n=2, delivery=1, failure=1, recovery_calls=1, last_unit_id=5))
    assert 'WAIT' not in stats
    assert audit.policy_path_statistics(units, 'B', 0)['SHORT']['n'] == 1


def test_nonrecovery_D_without_declared_R_never_enters_retry_mean():
    units = [unit(1, (audit.S, audit.D), {audit.S: 'DELIVERY', audit.D: 'DELIVERY'}),
        unit(2, (audit.D,), {audit.D: 'LOST'}),
        unit(3, (audit.D, audit.R), {audit.D: 'DELIVERY', audit.R: None})]
    stats = audit.policy_path_statistics(units, 'A', 0)
    assert stats['DETOUR_RETURN']['n'] == 3
    assert stats['DETOUR_RETRY'] == dict(n=1, delivery=1, failure=0,
        recovery_calls=0, last_unit_id=3)
    assert audit.unit_outcomes((audit.D, audit.R), units[2]['outcomes'])
    assert not audit.unit_outcomes((audit.D, audit.R), {audit.D: 'RECOVERY', audit.R: None})


@pytest.mark.parametrize('retry_cost', ('17/20', '19/20'))
def test_actual_recovery_calls_pay_retry_cost_and_nonrecovery_needs_no_R(retry_cost):
    units = [unit(1, (audit.D, audit.R), {audit.D: 'DELIVERY', audit.R: None}),
        unit(2, (audit.D, audit.R), {audit.D: 'RECOVERY', audit.R: 'DELIVERY'}),
        unit(3, (audit.D, audit.R), {audit.D: 'RECOVERY', audit.R: 'LOST'})]
    case = dict(operating='high', retry_cost=retry_cost)
    stats = audit.policy_path_statistics(units, 'A', 0)
    pure = audit.policy_path_vectors(stats, case)
    _, detour_cost = audit.direct.trajectory.COSTS['high']
    assert pure['DETOUR_RETRY'] == [-detour_cost-F(retry_cost)*F(2, 3), F(1, 3), F(2, 3)]
    assert pure['DETOUR_RETURN'] == [-detour_cost, F(0), F(1, 3)]
    assert pure['SHORT'] == pure['WAIT'] == [F(0)]*3


@pytest.mark.parametrize('operating,retry_cost', audit.COSTS)
def test_ALL_path_means_exactly_equal_previous_joint_point_vectors(operating, retry_cost):
    units = [unit(1, audit.OPERATORS, {audit.S: 'DELIVERY', audit.D: 'RECOVERY', audit.R: 'LOST'}),
        unit(2, audit.OPERATORS, {audit.S: 'LOST', audit.D: 'DELIVERY', audit.R: None}),
        unit(3, audit.OPERATORS, {audit.S: 'DELIVERY', audit.D: 'RECOVERY', audit.R: 'DELIVERY'})]
    case = dict(operating=operating, retry_cost=retry_cost)
    assert audit.policy_path_vectors(audit.policy_path_statistics(units, 'A', 0), case) == (
        audit.direct.empirical_vectors([record['outcomes'] for record in units], case))


def test_partial_unit_updates_candidate_and_independent_statistics_corruption_is_caught():
    units = [unit(1, audit.OPERATORS, {audit.S: 'LOST', audit.D: 'LOST', audit.R: None})]
    units.extend(unit(i, (audit.S, audit.D), {audit.S: 'DELIVERY', audit.D: 'LOST'}) for i in range(2, 7))
    treatment, case, replay = point_fixture(audit.ARMS[0], units)
    control, _, _ = point_fixture(audit.ARMS[1], units)
    assert not point_failures(treatment, case, replay, audit.ARMS[0])
    assert not point_failures(control, case, replay, audit.ARMS[1])
    # SHORT's goal rises to 4*(5/6)-1/10 = 97/30; the ALL-only
    # control keeps all three paid policies below WAIT's zero utility.
    assert treatment['query_pure_vectors']['SHORT'] == [-F(1, 10), F(1, 6), F(5, 6)]
    assert treatment['queries']['goal']['policy'] == 'SHORT'
    assert control['queries']['goal']['policy'] == 'WAIT'
    assert treatment['native_joint_outcome_counts'] == control['native_joint_outcome_counts']
    assert treatment['native_round_ids'] == control['native_round_ids'] == [1]
    broken = deepcopy(treatment)
    broken['query_point_statistics']['SHORT']['n'] += 1
    assert 'native_predeclared_policy_path_point_counts_and_conditional_retry_cost' in (
        point_failures(broken, case, replay, audit.ARMS[0]))
    broken = deepcopy(treatment)
    broken['queries']['goal']['policy'] = control['queries']['goal']['policy']
    assert 'query_choices_from_original_utilities_and_lexical_ties' in (
        point_failures(broken, case, replay, audit.ARMS[0]))


def test_candidate_flip_keeps_original_fixed_stream_statistics_and_bets():
    units = [unit(1, audit.OPERATORS, {audit.S: 'LOST', audit.D: 'LOST', audit.R: None})]
    units.extend(unit(i, (audit.S, audit.D), {audit.S: 'DELIVERY', audit.D: 'LOST'}) for i in range(2, 7))
    states = [core.prepare(0, arm, Counter()) for arm in audit.ARMS[:2]]
    for state in states:
        for record in units:
            core.observe_unit(state, record)
    spec = core.trajectory.direct.score_spec('goal', 'SHORT', 'DETOUR_RETURN', '17/20')
    eligible = [core.admitted_units(state, 'A', 0, spec) for state in states]
    statistics = [core.unit_statistics(records, 'goal', 'SHORT', 'DETOUR_RETURN', '17/20', {}, Counter())
        for records in eligible]
    assert statistics[0] == statistics[1]
    case = dict(operating='low', retry_cost='17/20', context='A')
    for arm, admitted, stats in zip(audit.ARMS[:2], eligible, statistics):
        proof = dict(core.trajectory.direct.statistics_record(stats),
            **core.trajectory.direct.evaluate(stats, case),
            score_source='actual_declared_required_row_units',
            admitted_unit_ids=[record['round_id'] for record in admitted],
            admitted_by_context={'A': len(admitted), 'B': 0}, cross_context=False)
        failures = []
        audit.audit_profile(dict(certificate=proof, case=case),
            {record['round_id']: record for record in units}, arm,
            lambda name, ok: failures.append(name) if not ok else None)
        assert not failures


@pytest.mark.parametrize('arm', audit.ARMS)
def test_all_three_arms_share_continuous_execution_counts_and_regions(arm):
    state = audit.state_for(0)
    state['sources']['A'] = audit.native_bank()
    state['sources']['B'] = audit.native_bank()
    state['a_switch'] = audit.native_bank()
    state['interface'] = dict(changed_operator=audit.R, b_to_a=[2, 0, 1])
    state['pools']['A'][0][audit.S]['DELIVERY'] = 3
    state['pools']['B'][1][audit.S]['LOST'] = 2
    state['pools']['A'][0][audit.R]['DELIVERY'] = 4
    state['pools']['B'][1][audit.R]['LOST'] = 7
    observed = audit.execution_counts(state, 'A', 0, arm)
    assert observed[audit.S] == {'DELIVERY': 3, 'LOST': 2}
    assert observed[audit.R] == {'DELIVERY': 4, 'LOST': 0}
    constraints = audit.execution_regions(0, 54, 'A', 0, state, audit.paid.empty(), arm)
    assert constraints[audit.S][3]['counts'] == observed[audit.S]
    assert constraints[audit.S][3]['prefix_kind'] == 'continuous_current'
    assert 'prefix_kind' not in constraints[audit.R][0]
