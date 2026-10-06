"""Supported A/B/A compatibility, actual execution and reserve regressions."""
from copy import deepcopy
from fractions import Fraction as F

from scripts import audit_trajectory_lifecycle_v256 as audit


def test_real_three_changed_operator_interfaces_admit_only_whole_compatible_rounds_in_chronology():
    for life in audit.LIVES:
        _, _, _, interface = audit.paid.world(life)
        state = audit.state_for(life)
        state['interface'] = interface
        records = []
        for context, identities in (('A', range(3)), ('B', range(3)), ('A', reversed(range(3)))):
            for identity in identities:
                records.append(dict(round_id=len(records)+1, context=context, identity=identity,
                    outcomes={audit.S: 'DELIVERY', audit.D: 'RECOVERY', audit.R: 'LOST'}))
        state['rounds'] = records
        for context in ('A', 'B'):
            for identity in range(3):
                for chosen in audit.POLICIES:
                    for other in audit.POLICIES:
                        if chosen == other:
                            continue
                        required = audit.direct.trajectory.specification('goal', chosen, other, '17/20')[0]
                        rebuild = audit.compatible_rounds(state, context, identity, required, audit.ARMS[1])
                        assert rebuild == [row for row in records if row['context'] == context and row['identity'] == identity]
                        reused = audit.compatible_rounds(state, context, identity, required, audit.ARMS[0])
                        mapped = interface['b_to_a'].index(identity) if context == 'A' else interface['b_to_a'][identity]
                        expected = [row for row in records if row in rebuild or row['context'] != context
                            and row['identity'] == mapped and interface['changed_operator'] not in required]
                        assert reused == expected
                        assert len({row['round_id'] for row in reused}) == len(reused)
                        if {chosen, other} == {'SHORT', 'DETOUR_RETRY'}:
                            assert set(required) == set(audit.OPERATORS) and reused == rebuild
        state['interface'] = None
        assert audit.compatible_rounds(state, 'A', 0, (audit.D,), audit.ARMS[0]) == [row for row in records if row['context'] == 'A' and row['identity'] == 0]


def test_native_source_pool_and_realized_execution_updates_are_counted_once_and_keep_event_labels():
    state = audit.state_for(2)
    _, _, _, interface = audit.paid.world(2)
    state['interface'] = interface
    for context in ('A', 'B'):
        for identity in range(3):
            for operator in audit.OPERATORS:
                state['pools'][context][identity][operator]['DELIVERY'] = 2+identity
        state['sources'][context] = deepcopy(state['pools'][context])
    identity, mapped = 1, interface['b_to_a'].index(1)
    before = deepcopy(state)
    native = audit.execution_counts(state, 'A', identity, audit.ARMS[1])
    reused = audit.execution_counts(state, 'A', identity, audit.ARMS[0])
    for operator in audit.OPERATORS:
        expected = native[operator]['DELIVERY']+(0 if operator == interface['changed_operator'] else 2+mapped)
        assert reused[operator]['DELIVERY'] == expected
    regions = audit.execution_regions(2, 54, 'A', identity, state, audit.paid.empty(), audit.ARMS[0])
    for operator in audit.OPERATORS:
        assert regions[operator][:3] == [
            dict(counts=state['sources']['A'][identity][operator], threshold=720, event=f'l2/A/pool1/{operator}'),
            dict(counts=state['pools']['A'][identity][operator], threshold=720, event=f'l2/A/pool1/{operator}'),
            dict(counts=audit.paid.empty()[operator], threshold=8640, event=f'l2/member54/{operator}')]
        if operator != interface['changed_operator']:
            assert len(regions[operator]) == 5 and regions[operator][4]['event'] == f'l2/B/pool{mapped}/{operator}'
        else:
            assert len(regions[operator]) == 3
    state['pools']['A'][1][audit.S]['LOST'] += 1
    assert native[audit.S]['LOST'] == reused[audit.S]['LOST'] == 0
    assert regions[audit.S][1]['counts']['LOST'] == 0
    assert audit.execution_counts(state, 'A', 1, audit.ARMS[1])[audit.S]['LOST'] == 1
    assert state['sources'] == before['sources'] and state['rounds'] == before['rounds']


def test_every_remaining_target_has_two_reserved_units_and_WAIT_releases_actual_unused_cost():
    state = audit.state_for(0)
    state['source_paid'] = 3456
    initial = audit.budget(0, 3, state)
    assert initial == dict(cap=14144, fees=dict(source=3456, shared=0, member=0, execution=0),
        paid=3456, future_B_source_reserved=1152, remaining_targets=72, execution_reserved=144, available=9392)
    state['shared_paid'] = initial['available']
    assert audit.budget(0, 3, state)['available'] == 0
    # WAIT consumes no physical observation and releases the current reservation.
    assert audit.budget(0, 4, state)['available'] == 2
    state['source_paid'] += 1152
    state['sources']['B'] = audit.native_bank()
    at_b = audit.budget(0, 30, state)
    assert at_b['future_B_source_reserved'] == 0 and at_b['execution_reserved'] == 96
    assert at_b['available'] == 48
    state['execution_paid'] = 47
    assert audit.budget(0, 30, state)['available'] == 1
    assert F(216, 4320) == F(18, 720)+F(216, 8640) == F(1, 20)


def test_actual_RETURN_RECOVERY_aborts_while_RETRY_pays_and_realizes_second_operator():
    case = dict(operating='low', retry_cost='17/20')
    observed = {audit.S: 'LOST', audit.D: 'RECOVERY', audit.R: 'DELIVERY'}
    assert audit.realized_vector(case, 'WAIT', {}) == [0, 0, 0]
    assert audit.realized_vector(case, 'SHORT', observed) == [-F(1, 10), 1, 0]
    assert audit.realized_vector(case, 'DETOUR_RETURN', observed) == [-F(1, 20), 0, 0]
    assert audit.realized_vector(case, 'DETOUR_RETRY', observed) == [-F(9, 10), 0, 1]
    observed[audit.R] = 'LOST'
    assert audit.realized_vector(case, 'DETOUR_RETRY', observed) == [-F(9, 10), 1, 0]
    observed[audit.D] = 'DELIVERY'
    assert audit.realized_vector(case, 'DETOUR_RETRY', observed) == [-F(1, 20), 0, 1]
    mixture = [['WAIT', '1/4'], ['SHORT', '3/4']]
    assert audit.sample_mixture(mixture, .1) == 'WAIT' and audit.sample_mixture(mixture, .5) == 'SHORT'


def test_exec_resolved_without_joint_query_never_becomes_joint_completion():
    plan = dict(utility_lower='2', goal_impossible=False, query_ready=False)
    assert audit.execution_resolved(plan) and not audit.jointly_ready(plan)
    plan['query_ready'] = True
    assert audit.jointly_ready(plan)
    plan.update(utility_lower='0', goal_impossible=True, query_ready=False)
    assert audit.execution_resolved(plan) and not audit.jointly_ready(plan)


def test_actual_direct_profiles_and_plan_refs_bind_native_choices_and_whole_compatible_history():
    from acfqp.science import trajectory_lifecycle_v256 as producer
    from collections import Counter
    life, arm = 0, audit.ARMS[0]
    _, _, _, interface = audit.paid.world(life)
    actual = producer.prepare(life, arm, Counter())
    observations = [
        {audit.S: 'DELIVERY', audit.D: 'DELIVERY', audit.R: None},
        {audit.S: 'LOST', audit.D: 'DELIVERY', audit.R: None},
        {audit.S: 'DELIVERY', audit.D: 'RECOVERY', audit.R: 'DELIVERY'},
        {audit.S: 'DELIVERY', audit.D: 'LOST', audit.R: None},
        {audit.S: 'LOST', audit.D: 'RECOVERY', audit.R: 'LOST'},
        {audit.S: 'DELIVERY', audit.D: 'DELIVERY', audit.R: None}]
    records = []
    for context in ('A', 'B'):
        if context == 'B':
            producer.begin_b(actual, interface['changed_operator'], interface['b_to_a'], Counter())
        for identity in range(3):
            for observation in observations:
                record = dict(context=context, identity=identity, round_id=len(records)+1, outcomes=observation)
                records.append(record)
                producer.observe_round(actual, record)
    case = dict(id='fixed_return', context='A', stage='A_RETURN', operating='low', retry_cost='17/20')
    plan = producer.query_plan(actual, case, 0, {}, Counter())
    profiles = []
    for query in ('goal', 'risk'):
        references = []
        for comparison in plan['query_evidence']['queries'][query]['comparisons']:
            identifier = len(profiles)
            profiles.append(dict(profile_id=identifier, query_identity=0,
                case={field: case[field] for field in ('operating', 'retry_cost', 'context')}, certificate=comparison))
            references.append(dict(profile_id=identifier, other=comparison['other'], certified=comparison['certified']))
        plan['query_evidence']['queries'][query]['comparisons'] = references
    checked = []
    check = lambda name, ok: checked.append((name, ok))
    round_map = {record['round_id']: record for record in records}
    decisions = {profile['profile_id']: audit.audit_profile(profile, round_map, check) for profile in profiles}
    independent = audit.state_for(life)
    independent.update(rounds=records, interface=interface)
    used = set()
    ready = audit.audit_query(plan, case, 0, independent, arm, profiles, decisions, used, {}, check)
    assert all(ok for _, ok in checked) and used == set(range(6)) and all(ready.values()) == plan['query_ready']
    assert any(profile['certificate']['cross_context'] for profile in profiles)
    broken = deepcopy(profiles)
    changed_comparison = next(profile for profile in broken if interface['changed_operator'] in profile['certificate']['required_rows'])
    mapped = interface['b_to_a'].index(0)
    cross = next(record for record in records if record['context'] == 'B' and record['identity'] == mapped)
    changed_comparison['certificate']['admitted_round_ids'].append(cross['round_id'])
    failures = []
    audit.audit_query(plan, case, 0, independent, arm, broken, decisions, set(), {},
        lambda name, ok: failures.append(name) if not ok else None)
    assert failures == ['comparison_uses_whole_compatible_native_rounds_current_prefix_without_future_or_duplicate']


def test_independent_primitive_streams_continue_shared_A_on_return_and_separate_member_execution_fees():
    _, laws, identities, _ = audit.paid.world(1)
    index = next(index for index in range(54, 78) if identities[index] == 2)
    state = audit.state_for(1)
    source = audit.replay_observation(1, 'SOURCE', 'A', 2, 3, audit.S, state, laws[2])
    first = audit.replay_observation(1, 'SHARED', 'A', 2, 3, audit.S, state, laws[2])
    member = audit.replay_observation(1, 'MEMBER', 'A', 2, index, audit.S, state, laws[index])
    terminal = deepcopy(state['pools']['A'][2])
    executed = audit.replay_observation(1, 'EXECUTION', 'A', 2, index, audit.S, state, laws[index])
    returned = audit.replay_observation(1, 'SHARED', 'A', 2, 54, audit.S, state, laws[2])
    assert source['seed'] == 303000+(1*6+2)*3
    assert first['seed'] == returned['seed'] == 304000+(1*6+2)*3
    assert first['draw_start'] == 0 and returned['draw_start'] == 1
    assert member['seed'] == 305000+(1*78+index)*3 and executed['seed'] == 306000+(1*78+index)*3
    assert member['draw_start'] == executed['draw_start'] == 0
    assert audit.full_paid(state) == state['step'] == 5
    assert (state['source_paid'], state['shared_paid'], state['member_paid'], state['execution_paid']) == (1, 2, 1, 1)
    assert sum(terminal[audit.S].values()) == 3 and sum(state['pools']['A'][2][audit.S].values()) == 5
    assert state['rounds'] == [] and state['complete']['A'] == [[], [], []]


def test_actual_runner_conditional_batches_and_frozen_mix_execution_replay_all_fields(monkeypatch):
    from scripts import run_trajectory_lifecycle_v256 as producer
    import io
    import json
    for module, source, shared in ((audit, 'SOURCE_BASE', 'SHARED_BASE'), (producer, 'SOURCE_BASE', 'SHARED_BASE')):
        monkeypatch.setattr(module, source, 123000)
        monkeypatch.setattr(module, shared, 124000)
    cases, laws, identities, interface = audit.paid.world(0)
    streams = {kind: io.StringIO() for kind in producer.FILE_KINDS}
    job = producer.Lifecycle(0, audit.ARMS[0], dict(cases=cases, laws=laws, identities=identities, metadata=interface), streams)
    schedule = [('SOURCE', 17, [0, 1, 2], None), ('SHARED', 14, [0, 2], 0), ('SHARED', 12, [1], 1)]
    for phase, amount, eligible, prior in schedule:
        job.conditional_batch(phase, 'A', 3, amount, eligible, prior)
    state, checked = audit.state_for(0), []
    data = {kind: [json.loads(line) for line in streams[kind].getvalue().splitlines()] for kind in ('tapes', 'rounds', 'batches')}
    check = lambda name, ok: checked.append((name, ok))
    for phase, amount, eligible, prior in schedule:
        audit.replay_conditional_batch(0, audit.ARMS[0], phase, 'A', 3, amount, eligible, prior,
            state, data['tapes'], data['rounds'], data['batches'], laws, check)
    assert all(ok for _, ok in checked) and job.step == state['step'] == 43
    assert state['pools']['A'] == job.state['a']['pools']
    assert state['query_counts']['A'] == [item['native_counts'] for item in job.state['trajectory']['A']]
    assert state['cursors'] == job.cursors and sum(state['tails'].values()) > 0
    old_rounds, old_query_counts = deepcopy(state['rounds']), deepcopy(state['query_counts'])
    for index, policy in zip(range(3, 7), ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')):
        saved = job.execute(index, cases[index], identities[index], [(policy, F(1))])
        data['tapes'] = [json.loads(line) for line in streams['tapes'].getvalue().splitlines()]
        independent = audit.replay_execution(0, audit.ARMS[0], index, cases[index], identities[index], [(policy, F(1))],
            state, data, laws, check)
        assert saved == independent
        assert saved['actual_samples'] <= 2 and saved['released_execution_reserve'] == 2-saved['actual_samples']
    assert all(ok for _, ok in checked) and state['pools']['A'] == job.state['a']['pools']
    assert state['rounds'] == old_rounds and state['query_counts'] == old_query_counts
    assert state['execution_paid'] == job.fees['execution']


def test_actual_execution_math_and_postfreeze_truth_bind_separate_query_and_execution_vectors():
    from acfqp.science import trajectory_lifecycle_v256 as core
    from scripts import run_trajectory_lifecycle_v256 as producer
    from collections import Counter
    cases, laws, identities, _ = audit.paid.world(0)
    index, identity, case = 3, identities[3], cases[3]
    state, actual = audit.state_for(0), core.prepare(0, audit.ARMS[0], Counter())
    for type_id in range(3):
        for outcome in (
            {audit.S: 'DELIVERY', audit.D: 'DELIVERY', audit.R: None},
            {audit.S: 'LOST', audit.D: 'RECOVERY', audit.R: 'DELIVERY'},
            {audit.S: 'DELIVERY', audit.D: 'LOST', audit.R: None}):
            record = dict(context='A', identity=type_id, round_id=len(state['rounds'])+1, outcomes=outcome)
            state['rounds'].append(record)
            core.observe_round(actual, record)
            for operator, observed in outcome.items():
                if observed is not None:
                    increment = dict.fromkeys(audit.ALPHABETS[operator], 0)
                    increment[observed] = 1
                    core.observe_row(actual, 'A', type_id, operator, increment)
                    state['pools']['A'][type_id][operator][observed] += 1
    core.freeze_sources(actual, 'A')
    state['sources']['A'] = deepcopy(state['pools']['A'])
    plan = core.make_plan(audit.paid.empty(), case, actual, identity, index, {}, Counter())
    counts = audit.execution_counts(state, 'A', identity, audit.ARMS[0])
    constraints = audit.execution_regions(0, index, 'A', identity, state, audit.paid.empty(), audit.ARMS[0])
    checked = []
    audit.audit_execution_plan(plan, case, counts, constraints, {}, lambda name, ok: checked.append((name, ok)))
    assert all(ok for _, ok in checked)
    broken = deepcopy(plan)
    broken['risk_upper'] += F(1, 1000)
    failures = []
    audit.audit_execution_plan(broken, case, counts, constraints, {}, lambda name, ok: failures.append(name) if not ok else None)
    assert failures == ['actual_execution_mix_and_original_risk_bound']
    ready = audit.jointly_ready(plan)
    row = dict(life=0, arm=audit.ARMS[0], index=index, identity=identity, case=case, initial_plan=plan,
        terminal_plan=plan, batches=[], spent=0, execution_certified=plan['utility_lower'] >= 2,
        goal_impossible=plan['goal_impossible'], query_certified=plan['query_ready'], joint_completed=ready,
        fallback=not ready, budget_exhausted=False, model_seconds=0.,
        executed_mix=plan['mix'] if ready else [('WAIT', F(1))], actual_execution={'actual_samples': 0})
    expected = dict(producer.evaluate(row, laws[index]), actual_execution=row['actual_execution'])
    assert audit.exact(audit.score_target(row, laws[index])) == audit.exact(expected)
