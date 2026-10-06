"""Predeclared admission, honest point data and unchanged all-row evidence."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

import pytest

from acfqp.science import required_row_units_v260 as core

S, D, R = core.OPERATORS
CASE = dict(context='A', stage='A', operating='low', retry_cost='17/20')


def unit(identifier, declared, short='DELIVERY', detour='LOST', retry='DELIVERY',
        context='A', identity=0):
    outcomes = {}
    if S in declared:
        outcomes[S] = short
    if D in declared:
        outcomes[D] = detour
    if R in declared and detour == 'RECOVERY':
        outcomes[R] = retry
    elif tuple(declared) == core.OPERATORS:
        outcomes[R] = None  # The unchanged full-round structural absence.
    return dict(round_id=identifier, context=context, identity=identity,
        declared_rows=tuple(declared), outcomes=outcomes)


def spec(chosen, other, query='goal'):
    return core.trajectory.direct.score_spec(query, chosen, other, '17/20')


@pytest.mark.parametrize('arm,underlying', [
    ('REQUIRED_ROWS_REUSE', 'CONTINUOUS_REUSE'),
    ('CONTINUOUS_REUSE', 'CONTINUOUS_REUSE'),
    ('TRAJECTORY_REBUILD', 'TRAJECTORY_REBUILD'),
])
def test_external_acquisition_arm_preserves_the_fixed_confidence_and_trajectory_interfaces(arm, underlying):
    expected = core.original.prepare(1, underlying, Counter())
    actual = core.prepare(1, arm, Counter())
    assert actual.pop('acquisition_arm') == arm
    assert actual == expected


@pytest.mark.parametrize('detour', ['DELIVERY', 'RECOVERY'])
def test_sd_units_never_enter_retry_comparisons_based_on_the_observed_detour_branch(detour):
    state = core.prepare(0, 'REQUIRED_ROWS_REUSE', Counter())
    record = unit(1, (S, D), detour=detour)
    before = deepcopy(state['trajectory'])
    core.observe_unit(state, record)
    assert state['trajectory'] == before
    assert core.admitted_units(state, 'A', 0, spec('SHORT', 'DETOUR_RETURN')) == [record]
    assert core.admitted_units(state, 'A', 0, spec('SHORT', 'DETOUR_RETRY')) == []
    assert core.admitted_units(state, 'A', 0, spec('DETOUR_RETURN', 'DETOUR_RETRY')) == []
    assert R not in state['round_log'][0]['outcomes']


def test_declared_dr_nonrecovery_supplies_a_complete_retry_score_without_a_fake_retry_draw():
    state = core.prepare(0, 'REQUIRED_ROWS_REUSE', Counter())
    record = unit(1, (D, R), detour='DELIVERY')
    core.observe_unit(state, record)
    admitted = core.admitted_units(state, 'A', 0, spec('WAIT', 'DETOUR_RETRY'))
    assert admitted == [record] and R not in record['outcomes'] and S not in record['outcomes']
    statistics = core.unit_statistics(admitted, 'goal', 'WAIT', 'DETOUR_RETRY', '17/20', {}, Counter())
    assert statistics.score_units == (80,) and statistics.n == 1
    assert core.trajectory.direct.evaluate(statistics, CASE)['threshold'] == 4320
    assert state['trajectory']['A'][0]['rounds'] == []
    with pytest.raises(ValueError, match='requires its detour'):
        core.observe_unit(state, unit(2, (R,)))


def test_partial_units_add_only_covered_evidence_while_full_joint_point_choice_stays_fixed():
    state = core.prepare(0, 'REQUIRED_ROWS_REUSE', Counter())
    core.observe_unit(state, unit(1, core.OPERATORS))
    before_state = deepcopy(state['trajectory'])
    before = core.query_plan(state, CASE, 0, {}, Counter())
    record = unit(2, (S, D), detour='RECOVERY')
    core.observe_unit(state, record)
    after = core.query_plan(state, CASE, 0, {}, Counter())
    assert state['trajectory'] == before_state
    for key in ('queries', 'query_pure_vectors', 'native_joint_outcome_counts', 'native_complete_rounds'):
        assert after[key] == before[key]
    assert after['native_round_ids'] == [1] and after['native_unit_ids'] == [1, 2]
    goal = {row['other']: row for row in after['query_evidence']['queries']['goal']['comparisons']}
    assert after['queries']['goal']['policy'] == 'SHORT'
    assert goal['DETOUR_RETURN']['admitted_unit_ids'] == [1, 2]
    assert goal['DETOUR_RETURN']['n'] == 2
    assert goal['DETOUR_RETRY']['admitted_unit_ids'] == [1]
    assert goal['DETOUR_RETRY']['n'] == 1
    assert all(row['score_source'] == 'actual_declared_required_row_units' for row in goal.values())
    record['outcomes'][S] = 'LOST'
    assert state['round_log'][1]['outcomes'][S] == 'DELIVERY'


def test_full_declared_units_match_original_point_choices_and_every_certificate_value():
    state = core.prepare(0, 'REQUIRED_ROWS_REUSE', Counter())
    for identifier, values in enumerate(core.trajectory.OUTCOMES, 1):
        core.observe_unit(state, unit(identifier, core.OPERATORS,
            short=values[0], detour=values[1], retry=values[2]))
    old = deepcopy(state)
    old['acquisition_arm'] = 'CONTINUOUS_REUSE'
    required = core.query_plan(state, CASE, 0, {}, Counter())
    control = core.query_plan(old, CASE, 0, {}, Counter())
    assert required['queries'] == control['queries']
    assert required['query_pure_vectors'] == control['query_pure_vectors']
    assert required['native_round_ids'] == required['native_unit_ids'] == control['native_round_ids']
    assert required['native_complete_rounds'] == control['native_complete_rounds'] == 8
    for query in ('goal', 'risk'):
        left = required['query_evidence']['queries'][query]
        right = control['query_evidence']['queries'][query]
        assert left['policy'] == right['policy'] and left['certified'] == right['certified']
        for new, original in zip(left['comparisons'], right['comparisons']):
            new, original = deepcopy(new), deepcopy(original)
            assert new.pop('admitted_unit_ids') == original.pop('admitted_round_ids')
            assert new.pop('score_source') == 'actual_declared_required_row_units'
            assert original.pop('score_source') == 'actual_complete_conditional_rounds'
            assert new == original


def test_partial_and_full_scores_retain_original_bets_and_cost_specific_thresholds():
    records = [unit(1, core.OPERATORS, short='LOST', detour='RECOVERY', retry='DELIVERY'),
        unit(2, core.OPERATORS, detour='DELIVERY'),
        unit(3, (S, D), short='LOST', detour='RECOVERY')]
    state = core.prepare(0, 'REQUIRED_ROWS_REUSE', Counter())
    for record in records:
        core.observe_unit(state, record)
    admitted = core.admitted_units(state, 'A', 0, spec('SHORT', 'DETOUR_RETURN', 'risk'))
    new = core.unit_statistics(admitted, 'risk', 'SHORT', 'DETOUR_RETURN', '17/20', {}, Counter())
    old = core.trajectory.actual_statistics([record['outcomes'] for record in records[:2]],
        'risk', 'SHORT', 'DETOUR_RETURN', '17/20', {}, Counter())
    first_two = core.unit_statistics(admitted[:2], 'risk', 'SHORT', 'DETOUR_RETURN',
        '17/20', {}, Counter())
    assert first_two == old
    # Each LOST-short/RECOVERY-detour contributes +4; equal deliveries give0.
    assert new.score_units == (80, 0, 80)
    assert new.bets == ((20, 102401), (0, 1), (0, 1))
    expected = core.trajectory.direct.StreamStatistics(new.spec, (80, 0, 80),
        ((20, 102401), (0, 1), (0, 1)), 160, 12800)
    for operating in ('low', 'high'):
        case = dict(CASE, operating=operating)
        assert core.trajectory.direct.evaluate(new, case) == core.trajectory.direct.evaluate(expected, case)
        assert core.trajectory.direct.evaluate(new, case)['threshold'] == 4320
    full_retry = core.admitted_units(state, 'A', 0, spec('SHORT', 'DETOUR_RETRY'))
    assert [record['round_id'] for record in full_retry] == [1, 2]


def test_cross_context_units_require_all_fixed_score_rows_unchanged_even_on_nonrecovery():
    state = core.prepare(2, 'REQUIRED_ROWS_REUSE', Counter())
    core.observe_unit(state, unit(1, (S, D), detour='DELIVERY'))
    core.observe_unit(state, unit(2, core.OPERATORS, detour='DELIVERY'))
    core.begin_b(state, R, (2, 0, 1), Counter())
    core.observe_unit(state, unit(3, (S, D), context='B', identity=1))
    core.observe_unit(state, unit(4, (D, R), detour='DELIVERY', context='B', identity=1))
    sd = core.admitted_units(state, 'B', 1, spec('SHORT', 'DETOUR_RETURN'))
    dr = core.admitted_units(state, 'B', 1, spec('WAIT', 'DETOUR_RETRY'))
    assert [record['round_id'] for record in sd] == [1, 2, 3]
    assert [record['round_id'] for record in dr] == [4]
    assert [record['round_id'] for record in core.admitted_units(
        state, 'A', 0, spec('SHORT', 'DETOUR_RETURN'))] == [1, 2, 3]


def test_old_s_tails_change_neither_point_data_nor_query_unit_prefixes():
    state = core.prepare(0, 'REQUIRED_ROWS_REUSE', Counter())
    core.observe_unit(state, unit(1, core.OPERATORS))
    before = core.query_plan(state, CASE, 0, {}, Counter())
    core.observe_tail(state, 'A', 0, 'LOST')
    after = core.query_plan(state, CASE, 0, {}, Counter())
    assert after == before
    assert state['trajectory']['A'][0]['tail_s_samples'] == 1
    assert len(state['round_log']) == 1


def preview(operating='low', lower=F(2), impossible=False, chosen='SHORT', other='DETOUR_RETURN', certified=False):
    return dict(case=dict(CASE, operating=operating), utility_lower=lower, goal_impossible=impossible,
        query_evidence=dict(queries={'goal': dict(policy=chosen,
            comparisons=[dict(other=other, certified=certified)]),
            'reward': dict(policy='WAIT', certified=True)}))


def test_masks_union_all_costs_but_any_execution_uncertainty_forces_all_rows():
    plans = [preview(operating=operating) for operating in ('low', 'high')]
    before = deepcopy(plans)
    assert core.declared_rows_for_plans(plans) == (S, D)
    assert plans == before
    assert core.declared_rows_for_plans(plans+[preview(other='DETOUR_RETRY')]) == core.OPERATORS
    assert core.declared_rows_for_plans(plans+[preview(lower=F(199,100), certified=True)]) == core.OPERATORS
    assert core.declared_rows_for_plans([preview(lower=F(1), impossible=True)]) == (S, D)
    assert core.declared_rows_for_plans([preview(certified=True)]) == ()


@pytest.mark.parametrize('arm', ['CONTINUOUS_REUSE', 'TRAJECTORY_REBUILD'])
def test_control_execution_plans_are_exact_original_delegations(arm, monkeypatch):
    state = core.prepare(0, arm, Counter())
    sentinel, calls = dict(original=True), []
    member, cache, work = core.empty(), {}, Counter()
    def base(*args):
        calls.append(args)
        return sentinel
    monkeypatch.setattr(core.original, 'make_plan', base)
    assert core.make_plan(member, CASE, state, 0, 3, cache, work) is sentinel
    assert calls == [(member, CASE, state, 0, 3, cache, work)]
