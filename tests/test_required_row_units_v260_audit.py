"""Actual partial-unit admission, frozen masks, point histories and fees."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from io import StringIO
import json

import pytest

from scripts import audit_required_row_units_v260 as audit
from acfqp.science import required_row_units_v260 as core


def unit(identifier, declared, outcomes, context='A', identity=0):
    return dict(round_id=identifier, context=context, identity=identity,
        declared_rows=list(declared), outcomes=outcomes)


def certificate(units, query='goal', chosen='SHORT', other='DETOUR_RETURN'):
    case = dict(operating='low', retry_cost='17/20', context='A')
    stats = core.unit_statistics(units, query, chosen, other, case['retry_cost'], {}, Counter())
    proof = dict(core.trajectory.direct.statistics_record(stats),
        **core.trajectory.direct.evaluate(stats, case),
        score_source='actual_declared_required_row_units',
        admitted_unit_ids=[record['round_id'] for record in units],
        admitted_by_context={context: sum(record['context'] == context for record in units) for context in ('A', 'B')},
        cross_context=any(record['context'] != 'A' for record in units))
    return dict(profile_id=0, case=case, query_identity=0, certificate=proof)


def failures_for(profile, units):
    failures = []
    audit.audit_profile(profile, {record['round_id']: record for record in units}, audit.ARMS[0],
        lambda name, ok: failures.append(name) if not ok else None)
    return failures


def test_partial_SD_bets_and_outward_products_use_only_actual_unit_scores():
    units = [unit(1, (audit.S, audit.D), {audit.S: 'DELIVERY', audit.D: 'LOST'}),
        unit(2, (audit.S, audit.D), {audit.S: 'LOST', audit.D: 'RECOVERY'}),
        unit(3, (audit.S, audit.D), {audit.S: 'LOST', audit.D: 'DELIVERY'})]
    profile = certificate(units)
    assert not failures_for(profile, units)
    expected = [-4, 0, 4]
    assert audit.direct.direct_scores([row['outcomes'] for row in units],
        'goal', 'SHORT', 'DETOUR_RETURN', '17/20')[1] == expected
    wrong = deepcopy(profile)
    wrong['certificate']['score_sum_units'] += 1
    assert 'complete_conditional_round_score_statistics_without_row_minimum' in failures_for(wrong, units)


def test_declared_DR_nonrecovery_is_complete_but_D_only_cannot_enter_retry_stream():
    units = [unit(1, (audit.D, audit.R), {audit.D: 'DELIVERY', audit.R: None}),
        unit(2, (audit.D, audit.R), {audit.D: 'RECOVERY', audit.R: 'LOST'})]
    profile = certificate(units, chosen='WAIT', other='DETOUR_RETRY')
    assert not failures_for(profile, units)
    wrong_units = deepcopy(units)
    wrong_units[0]['declared_rows'] = [audit.D]
    del wrong_units[0]['outcomes'][audit.R]
    assert 'every_admitted_unit_predeclared_all_required_rows_and_only_actual_outcomes' in failures_for(profile, wrong_units)
    assert not audit.unit_outcomes((audit.D, audit.R), {audit.D: 'RECOVERY', audit.R: None})
    assert not audit.unit_outcomes((audit.D,), {audit.D: 'DELIVERY', audit.R: 'DELIVERY'})


def test_static_required_rows_still_exclude_changed_R_on_a_nonrecovery_branch():
    state = audit.state_for(0)
    state['interface'] = dict(changed_operator=audit.R, b_to_a=[2, 0, 1])
    state['rounds'] = [unit(1, (audit.D, audit.R), {audit.D: 'DELIVERY', audit.R: None}),
        unit(2, (audit.D, audit.R), {audit.D: 'DELIVERY', audit.R: None}, 'B', 1),
        unit(3, (audit.D,), {audit.D: 'DELIVERY'}, 'B', 1)]
    assert [row['round_id'] for row in audit.compatible_rounds(state, 'A', 0,
        (audit.D, audit.R), audit.ARMS[0])] == [1]
    assert [row['round_id'] for row in audit.compatible_rounds(state, 'A', 0,
        (audit.D,), audit.ARMS[0])] == [1, 2, 3]
    assert [row['round_id'] for row in audit.compatible_rounds(state, 'A', 0,
        (audit.D,), audit.ARMS[2])] == [1]


def test_partial_nonrecovery_unit_never_changes_complete_point_choice_or_histogram():
    state = core.prepare(0, audit.ARMS[0], Counter())
    units = [unit(1, audit.OPERATORS, {audit.S: 'LOST', audit.D: 'DELIVERY', audit.R: None}),
        unit(2, (audit.S, audit.D), {audit.S: 'DELIVERY', audit.D: 'LOST'})]
    for record in units:
        core.observe_unit(state, record)
    case = dict(id='point', context='A', stage='A', operating='low', retry_cost='17/20')
    saved = core.query_plan(state, case, 0, {}, Counter())
    vectors = audit.direct.empirical_vectors([units[0]['outcomes']], case)
    assert saved['query_pure_vectors'] == vectors
    assert saved['native_round_ids'] == [1] and saved['native_unit_ids'] == [1, 2]
    assert saved['native_complete_rounds'] == 1
    assert saved['native_joint_outcome_counts'] == audit.direct.joint_histogram([units[0]['outcomes']])
    independent = audit.state_for(0)
    independent['rounds'] = units
    assert audit.point_rounds(independent, 'A', 0) == [units[0]]
    baseline = core.original.prepare(0, 'CONTINUOUS_REUSE', Counter())
    core.original.observe_round(baseline, units[0])
    original = core.original.query_plan(baseline, case, 0, {}, Counter())
    assert saved['query_pure_vectors'] == original['query_pure_vectors']
    assert saved['queries'] == original['queries']


def test_frozen_mask_union_uses_previous_uncertified_comparisons_and_exec_fallback():
    plan = dict(case=dict(retry_cost='17/20'), utility_lower=F(0), goal_impossible=True,
        query_evidence=dict(queries=dict(reward=dict(policy='WAIT', certified=True),
            goal=dict(policy='SHORT', comparisons=[dict(other='DETOUR_RETURN', certified=False),
                dict(other='DETOUR_RETRY', certified=True), dict(other='WAIT', certified=True)]),
            risk=dict(policy='WAIT', comparisons=[dict(other='SHORT', certified=True),
                dict(other='DETOUR_RETURN', certified=True), dict(other='DETOUR_RETRY', certified=True)]))))
    plans = [deepcopy(plan) for _ in range(4)]
    assert audit.declared_rows_for_plans(plans) == list(core.declared_rows_for_plans(plans)) == [audit.S, audit.D]
    plans[3]['goal_impossible'] = False
    assert audit.declared_rows_for_plans(plans) == list(audit.OPERATORS)
    plans[3]['utility_lower'] = F(2)
    assert audit.declared_rows_for_plans(plans) == [audit.S, audit.D]
    plans[1]['query_evidence']['queries']['risk']['comparisons'][2]['certified'] = False
    assert audit.declared_rows_for_plans(plans) == list(audit.OPERATORS)


def actual_batch(arm, amount, mask, recovery=False):
    from scripts import run_required_row_units_v260 as runner
    cases, laws, identities, interface = audit.paid.world(0)
    if recovery:
        laws = deepcopy(laws)
        laws[0][audit.D] = dict(DELIVERY=F(0), LOST=F(0), RECOVERY=F(1))
    streams = {kind: StringIO() for kind in runner.FILE_KINDS}
    job = runner.Lifecycle(0, arm,
        dict(cases=cases, laws=laws, identities=identities, metadata=interface), streams)
    declarations = [list(mask), list(audit.OPERATORS), list(audit.OPERATORS)]
    job.conditional_batch('SHARED', 'A', 3, amount, [0], 0, declarations, [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]])
    data = {kind: [json.loads(line) for line in stream.getvalue().splitlines()] for kind, stream in streams.items()}
    state, failures = audit.state_for(0), []
    audit.replay_conditional_batch(0, arm, 'SHARED', 'A', 3, amount, [0], 0,
        state, data['tapes'], data['rounds'], data['batches'], laws,
        lambda name, ok: failures.append(name) if not ok else None,
        declarations, [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]])
    return job, state, data, failures


def test_before_unit_maximum_reservation_preserves_row_only_tails_and_required_R():
    job, state, data, failures = actual_batch(audit.ARMS[0], 1, (audit.D, audit.R), True)
    assert not failures
    assert data['rounds'] == [] and data['tapes'][0]['role'] == 'tail_S'
    assert state['shared_paid'] == 1 and state['query_counts']['A'][0][audit.S] == state['pools']['A'][0][audit.S]
    job, state, data, failures = actual_batch(audit.ARMS[0], 2, (audit.D, audit.R), True)
    assert not failures
    assert [row['operator'] for row in data['tapes']] == [audit.D, audit.R]
    assert data['rounds'][0]['maximum_calls_reserved'] == 2
    assert data['rounds'][0]['all_rows_declared'] is False
    assert state['shared_paid'] == 2 and state['query_counts']['A'][0] == audit.paid.empty()


@pytest.mark.parametrize('arm', audit.ARMS)
def test_each_paired_arm_physically_draws_and_charges_same_full_units(arm):
    _, state, data, failures = actual_batch(arm, 7, audit.OPERATORS)
    assert not failures
    assert state['step'] == state['shared_paid'] == len(data['tapes']) == 7
    assert all(row['all_rows_declared'] for row in data['rounds'])
    assert state['query_counts']['A'][0] == state['pools']['A'][0]
    _, laws, _, _ = audit.paid.world(0)
    other = audit.state_for(0)
    source = audit.replay_observation(0, 'SOURCE', 'A', 0, None, audit.S, other, laws[0])
    assert source['seed'] == 318000 and other['source_paid'] == 1
    assert other['pools']['A'][0] is not state['pools']['A'][0]
