from copy import deepcopy
import random

from scripts import audit_shared_probe_timing_v249 as audit


def test_frozen_before_all_types_and_deferred_after_first_actual_return():
    identities = [0]*54+[2, 2, 1, 0]+[0]*20
    assert audit.probe_schedule('BEFORE_SHARED', identities) == [(54, 0), (54, 1), (54, 2)]
    assert audit.probe_schedule('DEFERRED_SHARED', identities) == [(54, 2), (56, 1), (57, 0)]
    assert audit.probe_schedule('REBUILD', identities) == []


def test_full_probe_and_future_source_reservation_is_not_actual_paid_fee():
    early = audit.budget_values(0, 'BEFORE_SHARED', 3, 0, 0)
    assert early['future_source'] == 1152 and early['pending_probe'] == 768
    before = audit.budget_values(0, 'BEFORE_SHARED', 54, 6768, 768, 16)
    deferred = audit.budget_values(0, 'DEFERRED_SHARED', 55, 6768, 256, 16)
    assert before['available'] == deferred['available'] == 2000
    assert before['future_source'] == deferred['future_source'] == 0
    assert before['pending_probe'] == 0 and deferred['pending_probe'] == 512
    assert before['reference_paid']-deferred['reference_paid'] == 512
    assert before['adaptive_after'] == deferred['adaptive_after'] == 1984
    assert audit.budget_values(0, 'REBUILD', 54, 6768, 0)['available'] == 2768


def test_each_paired_probe_row_uses_one_continuing_actual_random_prefix():
    _, laws, _, _ = audit.paid.world(0)
    batches = audit.expected_probe_batches(0, 1, laws[1])
    assert len(batches) == 16 and sum(sum(row['increments'].values()) for row in batches) == 256
    assert batches == audit.expected_probe_batches(0, 1, laws[1])
    for j, operator in enumerate(audit.PROBE_OPERATORS):
        generator = random.Random(290000+2+j)
        selected = [row for row in batches if row['operator'] == operator]
        assert [row['draw_start'] for row in selected] == list(range(0, 128, 16))
        assert [row['increments'] for row in selected] == [audit.paid.draw(generator, laws[1], operator) for _ in range(8)]
    assert all(row['operator'] != 'RECOVERY_RETRY' for row in batches)


def test_original_evidence_events_continue_native_pool_without_member_double_read():
    sources = dict(a=[audit.paid.empty() for _ in range(3)], b=[audit.paid.empty() for _ in range(3)])
    state = dict(a=deepcopy(sources['a']), b=deepcopy(sources['b']), a_switch=deepcopy(sources['a']))
    before, member = deepcopy(state), audit.paid.empty()
    state['a'][1]['SHORT_PASS'] = dict(DELIVERY=11, LOST=5)
    case, metadata = dict(context='A', stage='A_RETURN'), dict(changed_operator='SHORT_PASS', b_to_a=[2, 0, 1])
    counts = audit.prior.evidence_counts(state, case, 1, 'ONE_WAY', metadata)
    constraints = audit.prior.execution_constraints(0, 54, case, 1, sources, state, member, 'ONE_WAY', metadata)
    assert counts['SHORT_PASS'] == dict(DELIVERY=11, LOST=5)
    assert constraints['SHORT_PASS'] == [
        dict(counts=dict(DELIVERY=0, LOST=0), threshold=720, event='l0/A/pool1/SHORT_PASS'),
        dict(counts=dict(DELIVERY=11, LOST=5), threshold=720, event='l0/A/pool1/SHORT_PASS'),
        dict(counts=dict(DELIVERY=0, LOST=0), threshold=8640, event='l0/member54/SHORT_PASS')]
    assert state['b'] == before['b'] and state['a_switch'] == before['a_switch']
    assert all(audit.paid.samples(row) == 0 for bank in sources.values() for row in bank)


def methods_fixture():
    method = dict(joint_completed=180, total_samples=48000,
        late_b=dict(query_certified=27), a_return=dict(query_certified=54))
    method.update(dict.fromkeys(('false_query_certificates', 'false_execution_certificates',
        'false_impossible_certificates', 'false_goal_uppers', 'risk_violations', 'executed_risk_violations'), 0))
    methods = {arm: deepcopy(method) for arm in audit.ARMS}
    methods['REBUILD']['total_samples'] += 16
    return methods


def test_exact_eleven_conditions_include_full_charged_probes_and_all_plan_errors():
    methods = methods_fixture()
    assert len(audit.conditions(methods)) == 11 and all(audit.conditions(methods).values())
    methods['BEFORE_SHARED']['total_samples'] += 16
    result = audit.conditions(methods)
    assert not result['actual_acquisition_nondegrading_vs_deferred_shared']
    assert not result['actual_acquisition_saving_vs_rebuild']
    methods = methods_fixture()
    methods['DEFERRED_SHARED']['false_goal_uppers'] = 1
    assert not audit.conditions(methods)['valid_certificates_and_execution']
