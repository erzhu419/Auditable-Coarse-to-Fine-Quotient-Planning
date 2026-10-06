"""Canonical row prefixes, native-bank accounting and full-region geometry."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

import pytest

from scripts import audit_continuous_row_cs_v259 as audit


def native_fixture(life, arm):
    from acfqp.science import continuous_row_cs_v259 as core
    state = core.prepare(life, arm, Counter())
    _, _, _, interface = audit.paid.world(life)
    for identity in range(3):
        for operator in audit.OPERATORS:
            state['a']['sources'][identity][operator]['DELIVERY'] = 10+identity
            state['a']['pools'][identity][operator]['DELIVERY'] = 14+identity
    core.begin_b(state, interface['changed_operator'], interface['b_to_a'], Counter())
    for identity in range(3):
        for operator in audit.OPERATORS:
            state['b']['sources'][identity][operator]['DELIVERY'] = 20+identity
            state['b']['pools'][identity][operator]['DELIVERY'] = 25+identity
    independent = audit.state_for(life)
    independent.update(sources={context: deepcopy(state[context.lower()]['sources']) for context in ('A', 'B')},
        pools={context: deepcopy(state[context.lower()]['pools']) for context in ('A', 'B')},
        a_switch=deepcopy(state['a_at_switch']['pools']), interface=interface)
    return core, state, independent, interface


@pytest.mark.parametrize('life', audit.LIVES)
def test_all_real_interfaces_keep_changed_rows_native_and_register_only_canonical_unchanged_events(life):
    core, actual, independent, interface = native_fixture(life, audit.ARMS[0])
    case = dict(context='B', stage='B')
    regions = core.regions(audit.paid.empty(), case, actual, 1, 30)
    expected = audit.execution_regions(life, 30, 'B', 1, independent, audit.paid.empty(), audit.ARMS[0])
    assert regions == expected
    a_identity = interface['b_to_a'][1]
    for operator in audit.OPERATORS:
        if operator == interface['changed_operator']:
            assert len(regions[operator]) == 3
            assert all('prefix_kind' not in region for region in regions[operator])
            assert regions[operator][0]['event'] == f'l{life}/B/pool1/{operator}'
        else:
            assert [region['prefix_kind'] for region in regions[operator]] == [
                'a_source', 'a_switch', 'a_switch_plus_b_source', 'continuous_current', 'member']
            assert all(region['event'] == f'l{life}/A/pool{a_identity}/{operator}'
                       and region['threshold'] == 720 for region in regions[operator][:-1])
            assert regions[operator][-1]['event'] == f'l{life}/member30/{operator}'
    wrong = deepcopy(regions)
    changed = interface['changed_operator']
    other = next(operator for operator in audit.OPERATORS if operator != changed)
    wrong[changed] = deepcopy(regions[other])
    assert wrong != expected
    wrong = deepcopy(regions)
    wrong[other][3]['event'] = f'l{life}/B/pool1/{other}'
    assert wrong != expected
    assert F(12, 720)+F(216, 8640) == F(1, 24) <= F(1, 20)


def test_return_prefix_counts_B_once_and_rejects_A_only_or_copied_inheritance():
    core, actual, independent, interface = native_fixture(0, audit.ARMS[0])
    identity, context = 2, 'A'
    mapped = interface['b_to_a'].index(identity)
    for operator in audit.OPERATORS:
        actual['a']['pools'][identity][operator]['LOST'] += 3
        independent['pools']['A'][identity][operator]['LOST'] += 3
    case = dict(context='A', stage='A_RETURN')
    regions = core.regions(audit.paid.empty(), case, actual, identity, 54)
    expected = audit.execution_regions(0, 54, context, identity, independent, audit.paid.empty(), audit.ARMS[0])
    assert regions == expected
    operator = next(op for op in audit.OPERATORS if op != interface['changed_operator'])
    current = regions[operator][3]
    assert current['counts']['DELIVERY'] == (14+identity)+(25+mapped)
    assert current['native_context_counts']['A']['counts']['LOST'] == 3
    assert current['native_context_counts']['B']['identity'] == mapped
    assert regions[operator][1]['counts']['LOST'] == 0
    assert actual['return_merge'] is not None
    wrong = deepcopy(regions)
    wrong[operator][3]['counts'] = deepcopy(independent['pools']['A'][identity][operator])
    assert wrong != expected
    copied = deepcopy(independent)
    copied['pools']['A'][identity][operator]['DELIVERY'] += independent['pools']['B'][mapped][operator]['DELIVERY']
    assert audit.execution_regions(0, 54, context, identity, copied, audit.paid.empty(), audit.ARMS[0]) != expected
    assert audit.execution_counts(independent, context, identity, audit.ARMS[0]) == audit.execution_counts(independent, context, identity, audit.ARMS[1])
    assert independent['pools']['A'][identity][operator]['DELIVERY'] == 14+identity


@pytest.fixture(scope='module')
def genuine_paid_geometry():
    from acfqp.science import continuous_row_cs_v259 as core
    directory = audit.ROOT/'reports/goal_feasibility_v258'
    retained = audit.load(directory/'worker_artifacts_life_00_TRAJECTORY_REUSE.json')['final_state']
    sources = audit.rows(directory/'sources_life_00_TRAJECTORY_REUSE.jsonl.gz')
    b_source = next(row for row in sources if row['context'] == 'B')
    state = core.prepare(0, audit.ARMS[0], Counter())
    state['a'] = deepcopy(retained['a_at_switch'])
    _, _, identities, interface = audit.paid.world(0)
    core.begin_b(state, interface['changed_operator'], interface['b_to_a'], Counter())
    state['b'] = dict(sources=deepcopy(b_source['source_counts']), pools=deepcopy(b_source['source_counts']))
    end_round = max(b_source['source_round_ids'])
    for record in retained['round_log']:
        if record['round_id'] <= end_round:
            core.observe_round(state, record)
    cases = audit.paid.world(0)[0]
    case, identity = cases[30], identities[30]
    plan = core.make_plan(core.empty(), case, state, identity, 30, {}, Counter())
    independent = audit.state_for(0)
    independent.update(sources={context: deepcopy(state[context.lower()]['sources']) for context in ('A', 'B')},
        pools={context: deepcopy(state[context.lower()]['pools']) for context in ('A', 'B')},
        a_switch=deepcopy(state['a_at_switch']['pools']), interface=interface)
    return case, identity, plan, independent


def test_genuine_paid_prefix_projects_and_certifies_through_independent_math(genuine_paid_geometry):
    case, identity, plan, state = genuine_paid_geometry
    counts = audit.execution_counts(state, 'B', identity, audit.ARMS[0])
    regions = audit.execution_regions(0, 30, 'B', identity, state, audit.paid.empty(), audit.ARMS[0])
    checks = []
    audit.audit_row_method(plan, audit.ARMS[0], lambda name, ok: checks.append((name, ok)))
    audit.audit_execution_plan(plan, case, counts, regions, {}, lambda name, ok: checks.append((name, ok)))
    assert all(ok for _, ok in checks)


def test_corrupted_original_event_or_B_count_is_detected_in_actual_plan(genuine_paid_geometry):
    case, identity, original, state = genuine_paid_geometry
    counts = audit.execution_counts(state, 'B', identity, audit.ARMS[0])
    expected = audit.execution_regions(0, 30, 'B', identity, state, audit.paid.empty(), audit.ARMS[0])
    operator = next(op for op in audit.OPERATORS if op != state['interface']['changed_operator'])
    plan = deepcopy(original)
    plan['joint_constraints'][operator][3]['event'] = 'unregistered/extra/pool'
    plan['joint_constraints'][operator][3]['counts']['DELIVERY'] += state['pools']['B'][identity][operator]['DELIVERY']
    failures = []
    audit.audit_execution_plan(plan, case, counts, expected, {},
                               lambda name, ok: failures.append(name) if not ok else None)
    assert 'native_rows_and_eligible_execution_rows_paid_once' in failures


def test_three_paired_arms_draw_and_charge_independent_native_samples():
    _, laws, _, _ = audit.paid.world(0)
    states = [audit.state_for(0) for _ in audit.ARMS]
    draws = [audit.replay_observation(0, 'SOURCE', 'A', 0, None, audit.S, state, laws[0]) for state in states]
    assert draws[0] == draws[1] == draws[2] and draws[0]['seed'] == 313000
    assert sum(state['source_paid'] for state in states) == 3
    assert all(audit.budget(0, 3, state)['fees']['source'] == 1 for state in states)
    category = draws[0]['outcome']
    states[0]['pools']['A'][0][audit.S][category] += 1
    assert states[1]['pools']['A'][0][audit.S][category] == states[2]['pools']['A'][0][audit.S][category] == 1

