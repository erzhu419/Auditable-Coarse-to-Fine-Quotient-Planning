"""Partial point learning without outcome-selected admission or changed tests."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

import pytest

from acfqp.science import partial_path_point_v261 as core

S, D, R = core.OPERATORS
CASE = dict(context='A', stage='A', operating='low', retry_cost='17/20')


def unit(identifier, declared, short='DELIVERY', detour='LOST', retry='DELIVERY',
        context='A', identity=0, phase='SOURCE'):
    outcomes = {}
    if S in declared:
        outcomes[S] = short
    if D in declared:
        outcomes[D] = detour
    if R in declared and detour == 'RECOVERY':
        outcomes[R] = retry
    elif tuple(declared) == core.OPERATORS:
        outcomes[R] = None
    return dict(round_id=identifier, context=context, identity=identity,
        phase=phase, declared_rows=tuple(declared), outcomes=outcomes)


@pytest.mark.parametrize('arm,underlying', [
    ('PARTIAL_POINT_REUSE', 'REQUIRED_ROWS_REUSE'),
    ('REQUIRED_ROWS_REUSE', 'REQUIRED_ROWS_REUSE'),
    ('CONTINUOUS_REUSE', 'CONTINUOUS_REUSE'),
])
def test_external_arm_only_changes_its_point_interface(arm, underlying):
    expected = core.original.prepare(1, underlying, Counter())
    actual = core.prepare(1, arm, Counter())
    assert actual.pop('point_learning_arm') == arm
    if arm == core.ARMS[0]:
        points = actual.pop('policy_path_stats')
        assert points['B'] is None
        assert points['A'] == [core.new_type_statistics() for _ in range(3)]
        points['A'][0]['SHORT']['n'] = 1
        assert points['A'][1]['SHORT']['n'] == 0
    assert actual == expected


def test_partial_paths_update_actual_policy_values_and_change_stale_candidate():
    state = core.prepare(0, core.ARMS[0], Counter())
    for identifier, detour in enumerate(('DELIVERY', 'DELIVERY', 'RECOVERY'), 1):
        core.observe_unit(state, unit(identifier, core.OPERATORS,
            short='LOST', detour=detour, retry='LOST'))
    before = core.query_plan(state, CASE, 0, {}, Counter())
    assert before['queries']['goal']['policy'] == 'DETOUR_RETURN'
    old_joint = deepcopy(state['trajectory'])
    for identifier in range(4, 8):
        core.observe_unit(state, unit(identifier, (D, R), detour='RECOVERY',
            retry='DELIVERY', phase='SHARED'))
    after = core.query_plan(state, CASE, 0, {}, Counter())
    assert after['queries']['goal']['policy'] == 'DETOUR_RETRY'
    assert after['query_pure_vectors']['DETOUR_RETRY'] == [-F(23, 35), F(1, 7), F(6, 7)]
    assert after['query_pure_vectors']['SHORT'] == [-F(1, 10), F(1), F(0)]
    assert state['trajectory'] == old_joint
    assert after['native_complete_rounds'] == 3
    assert after['native_round_ids'] == [1, 2, 3]
    assert after['native_unit_ids'] == list(range(1, 8))
    assert after['query_point_statistics']['DETOUR_RETRY'] == dict(
        n=7, delivery=6, failure=1, recovery_calls=5, last_unit_id=7)
    assert after['query_point_method'] == 'native_predeclared_policy_path_means'
    after['query_point_statistics']['DETOUR_RETRY']['n'] = 0
    assert state['policy_path_stats']['A'][0]['DETOUR_RETRY']['n'] == 7
    control = deepcopy(state)
    control['point_learning_arm'] = 'REQUIRED_ROWS_REUSE'
    assert core.query_plan(control, CASE, 0, {}, Counter())['queries']['goal']['policy'] == 'DETOUR_RETURN'


@pytest.mark.parametrize('detour', ['DELIVERY', 'LOST', 'RECOVERY'])
def test_sd_declaration_never_promotes_retry_from_its_observed_branch(detour):
    state = core.prepare(0, core.ARMS[0], Counter())
    record = unit(1, (S, D), detour=detour)
    core.observe_unit(state, record)
    statistics = state['policy_path_stats']['A'][0]
    assert statistics['SHORT']['n'] == statistics['DETOUR_RETURN']['n'] == 1
    assert statistics['DETOUR_RETRY'] == core.new_type_statistics()['DETOUR_RETRY']
    assert core.admitted_units(state, 'A', 0,
        core.trajectory.direct.score_spec('goal', 'WAIT', 'DETOUR_RETRY', '17/20')) == []
    assert state['trajectory']['A'][0]['rounds'] == []


def test_dr_nonrecovery_units_supply_complete_retry_results_without_a_retry_draw():
    state = core.prepare(0, core.ARMS[0], Counter())
    delivery = unit(1, (D, R), detour='DELIVERY')
    failure = unit(2, (D, R), detour='LOST')
    assert R not in delivery['outcomes'] and R not in failure['outcomes']
    for record in (delivery, failure):
        core.observe_unit(state, record)
    statistics = state['policy_path_stats']['A'][0]
    assert statistics['DETOUR_RETRY'] == dict(n=2, delivery=1, failure=1,
        recovery_calls=0, last_unit_id=2)
    assert statistics['SHORT']['n'] == 0
    assert core.path_vectors(statistics, CASE)['DETOUR_RETRY'] == [-F(1, 20), F(1, 2), F(1, 2)]


def test_policy_counts_respect_s_and_d_only_predeclared_paths():
    state = core.prepare(0, core.ARMS[0], Counter())
    core.observe_unit(state, unit(1, (S,), short='LOST'))
    core.observe_unit(state, unit(2, (D,), detour='RECOVERY'))
    statistics = state['policy_path_stats']['A'][0]
    assert statistics['SHORT'] == dict(n=1, delivery=0, failure=1,
        recovery_calls=0, last_unit_id=1)
    assert statistics['DETOUR_RETURN'] == dict(n=1, delivery=0, failure=0,
        recovery_calls=0, last_unit_id=2)
    assert statistics['DETOUR_RETRY']['n'] == 0


@pytest.mark.parametrize('operating', ['low', 'high'])
@pytest.mark.parametrize('retry_cost', ['17/20', '19/20'])
@pytest.mark.parametrize('full_data', [False, True])
def test_full_only_point_vectors_queries_and_fixed_evidence_match_original_exactly(
        operating, retry_cost, full_data):
    state = core.prepare(0, core.ARMS[0], Counter())
    if full_data:
        for identifier, outcomes in enumerate(core.trajectory.OUTCOMES, 1):
            core.observe_unit(state, unit(identifier, core.OPERATORS,
                short=outcomes[0], detour=outcomes[1], retry=outcomes[2]))
    case = dict(CASE, operating=operating, retry_cost=retry_cost)
    control = deepcopy(state)
    control['point_learning_arm'] = 'REQUIRED_ROWS_REUSE'
    new = core.query_plan(state, case, 0, {}, Counter())
    old = core.query_plan(control, case, 0, {}, Counter())
    assert new['query_pure_vectors'] == core.trajectory.pure_vectors(state['trajectory']['A'][0], case)
    assert new.pop('query_point_method') == 'native_predeclared_policy_path_means'
    assert new.pop('query_point_statistics') == state['policy_path_stats']['A'][0]
    assert new == old
    if not full_data:
        assert all(vector == [F(0)]*3 for vector in new['query_pure_vectors'].values())


def test_point_means_stay_native_even_when_unchanged_comparison_rows_reuse_a_data():
    state = core.prepare(0, core.ARMS[0], Counter())
    core.observe_unit(state, unit(1, core.OPERATORS, short='LOST', detour='DELIVERY'))
    core.begin_b(state, R, (2, 0, 1), Counter())
    core.observe_unit(state, unit(2, (S, D), context='B', identity=1,
        short='DELIVERY', detour='LOST', phase='SHARED'))
    plan = core.query_plan(state, dict(CASE, context='B', stage='B'), 1, {}, Counter())
    assert plan['query_point_statistics']['SHORT'] == dict(n=1, delivery=1,
        failure=0, recovery_calls=0, last_unit_id=2)
    assert plan['query_point_statistics']['DETOUR_RETRY']['n'] == 0
    assert plan['native_complete_rounds'] == 0
    assert plan['query_pure_vectors']['SHORT'] == [-F(1, 10), F(0), F(1)]
    sd_spec = core.trajectory.direct.score_spec('goal', 'SHORT', 'DETOUR_RETURN', '17/20')
    assert [row['round_id'] for row in core.admitted_units(state, 'B', 1, sd_spec)] == [1, 2]
    a_plan = core.query_plan(state, CASE, 0, {}, Counter())
    assert a_plan['query_point_statistics']['SHORT']['last_unit_id'] == 1
    assert a_plan['query_point_statistics']['SHORT']['delivery'] == 0


def test_actual_tails_and_row_feedback_never_update_policy_point_means():
    state = core.prepare(0, core.ARMS[0], Counter())
    core.observe_unit(state, unit(1, core.OPERATORS))
    before = core.query_plan(state, CASE, 0, {}, Counter())
    core.observe_tail(state, 'A', 0, 'LOST')
    for operator in core.OPERATORS:
        counts = dict.fromkeys(core.ALPHABETS[operator], 0)
        counts[core.ALPHABETS[operator][0]] = 1
        core.observe_row(state, 'A', 0, operator, counts)
    assert core.query_plan(state, CASE, 0, {}, Counter()) == before
    assert state['trajectory']['A'][0]['tail_s_samples'] == 1


@pytest.mark.parametrize('phase', ['MEMBER', 'EXECUTION'])
def test_non_source_shared_units_do_not_enter_new_point_aggregates(phase):
    state = core.prepare(0, core.ARMS[0], Counter())
    core.observe_unit(state, unit(1, (D, R), detour='DELIVERY', phase=phase))
    assert state['policy_path_stats']['A'][0] == core.new_type_statistics()


def test_scores_bets_masks_and_row_confidence_are_original_functions():
    for name in ('admitted_units', 'unit_statistics', 'declared_rows_for_plans', 'regions', 'upper_bound'):
        assert getattr(core, name) is getattr(core.original, name)
    assert core.trajectory.direct.STREAM_THRESHOLD == 4320
    records = [unit(1, core.OPERATORS, short='LOST', detour='RECOVERY', retry='DELIVERY'),
        unit(2, (S, D), short='LOST', detour='DELIVERY')]
    statistics = core.unit_statistics(records, 'risk', 'SHORT', 'DETOUR_RETURN', '17/20', {}, Counter())
    original = core.original.unit_statistics(records, 'risk', 'SHORT', 'DETOUR_RETURN', '17/20', {}, Counter())
    assert statistics == original
    assert statistics.bets == ((20, 102401), (0, 1))


def test_partial_point_learning_leaves_every_execution_constraint_and_decision_unchanged():
    state = core.prepare(0, core.ARMS[0], Counter())
    for identifier, detour in enumerate(('DELIVERY', 'DELIVERY', 'RECOVERY'), 1):
        core.observe_unit(state, unit(identifier, core.OPERATORS,
            short='LOST', detour=detour, retry='LOST'))
    for identifier in range(4, 8):
        core.observe_unit(state, unit(identifier, (D, R), detour='RECOVERY',
            retry='DELIVERY', phase='SHARED'))
    control = deepcopy(state)
    control['point_learning_arm'] = 'REQUIRED_ROWS_REUSE'
    first = core.make_plan(core.empty(), CASE, state, 0, 3, {}, Counter())
    old = core.make_plan(core.empty(), CASE, control, 0, 3, {}, Counter())
    assert first['queries']['goal']['policy'] != old['queries']['goal']['policy']
    query_fields = set(core.query_plan(state, CASE, 0, {}, Counter())) - {'case'}
    assert {key: value for key, value in first.items() if key not in query_fields} == {
        key: value for key, value in old.items() if key not in query_fields}


@pytest.mark.parametrize('arm', ['REQUIRED_ROWS_REUSE', 'CONTINUOUS_REUSE'])
@pytest.mark.parametrize('function', ['query_plan', 'make_plan'])
def test_control_plans_delegate_exactly_and_never_create_a_point_bank(arm, function, monkeypatch):
    state = core.prepare(0, arm, Counter())
    core.begin_b(state, R, (2, 0, 1), Counter())
    assert 'policy_path_stats' not in state
    sentinel, calls = {'old': True}, []
    def old(*args):
        calls.append(args)
        return sentinel
    monkeypatch.setattr(core.original, function, old)
    cache, work = {}, Counter()
    args = (state, CASE, 0, cache, work) if function == 'query_plan' else (
        core.empty(), CASE, state, 0, 3, cache, work)
    assert getattr(core, function)(*args) is sentinel
    assert calls == [args]
