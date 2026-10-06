from copy import deepcopy
from fractions import Fraction as F

import pytest

from scripts import audit_reuse_rebuild_lifecycle_v242 as audit


def counts(amount):
    result = audit.empty()
    for row in result.values():
        row['DELIVERY'] = amount
    return result


def test_only_reuse_b_unchanged_rows_inherit_switch_pool_and_return_restores_a():
    state = dict(a=[counts(3)], b=[counts(5)], a_switch=[counts(2)])
    metadata = dict(b_to_a=[0], changed_operator='DETOUR_PASS')
    case = dict(context='B')
    reused = audit.evidence_counts(state, case, 0, 'REUSE', metadata)
    rebuilt = audit.evidence_counts(state, case, 0, 'REBUILD', metadata)
    assert rebuilt == counts(5)
    assert reused['DETOUR_PASS'] == counts(5)['DETOUR_PASS']
    assert reused['SHORT_PASS']['DELIVERY'] == reused['RECOVERY_RETRY']['DELIVERY'] == 7
    assert audit.evidence_counts(state, dict(context='A'), 0, 'REUSE', metadata) == counts(3)
    assert state == dict(a=[counts(3)], b=[counts(5)], a_switch=[counts(2)])


def test_rebuild_execution_constraints_exclude_inherited_a_and_count_member_once():
    state = dict(a=[counts(3)], b=[counts(5)], a_switch=[counts(2)])
    sources = dict(a=[counts(1)], b=[counts(4)])
    member, metadata = counts(1), dict(b_to_a=[0], changed_operator='DETOUR_PASS')
    rebuilt = audit.execution_constraints(0, 30, dict(context='B'), 0, sources, state, member, 'REBUILD', metadata)
    reused = audit.execution_constraints(0, 30, dict(context='B'), 0, sources, state, member, 'REUSE', metadata)
    assert all(len(rows) == 3 for rows in rebuilt.values())
    assert len(reused['DETOUR_PASS']) == 3 and len(reused['SHORT_PASS']) == 5
    assert rebuilt['SHORT_PASS'][1]['counts'] == counts(5)['SHORT_PASS']
    assert rebuilt['SHORT_PASS'][2]['counts'] == counts(1)['SHORT_PASS']
    assert audit.evidence_counts(state, dict(context='B'), 0, 'REBUILD', metadata) == counts(5)


@pytest.mark.parametrize('mutation', ('retry_cost', 'paid_counts'))
def test_profile_reference_rejects_wrong_cost_or_extra_member_counts(mutation):
    raw, case = counts(5), dict(operating='low', retry_cost='19/20')
    uniform = {op: dict.fromkeys(cats, F(1, len(cats))) for op, cats in audit.ALPHABETS.items()}
    projected, _ = audit.evidence.named_projection('D_REC_R', raw, uniform)
    cert = dict(query='risk', chosen='DETOUR_RETURN', other='DETOUR_RETRY', family='D_REC_R',
        projected_counts=projected, engine='convex_tangent', relevant_cost='19/20', certified=False)
    profile = dict(profile_id=0, case=case, certificate=cert)
    reference, failed = dict(profile_id=0, other='DETOUR_RETRY', certified=False), []
    check = lambda name, ok: failed.append(name) if not ok else None
    audit.audit_reference(profile, reference, raw, case, 'risk', 'DETOUR_RETURN', 'DETOUR_RETRY', False, check)
    assert not failed
    bad = deepcopy(profile)
    if mutation == 'retry_cost':
        bad['certificate']['relevant_cost'] = '17/20'
    else:
        bad['certificate']['projected_counts']['D_REC']['OTHER'] += 1
    audit.audit_reference(bad, reference, raw, case, 'risk', 'DETOUR_RETURN', 'DETOUR_RETRY', False, check)
    assert failed == ['profile_reference_actual_paid_projection_direction_and_cost']


def test_global_budget_can_stop_unknown_but_cannot_skip_available_batch():
    unknown = dict(utility_lower='2', goal_impossible=False, query_ready=False)
    assert not audit.terminal_stop(16, 32, unknown)
    assert audit.terminal_stop(16, 16, unknown)
    assert audit.terminal_stop(0, 0, unknown)
    assert audit.terminal_stop(384, 512, unknown)
    assert audit.terminal_stop(0, 32, dict(utility_lower='2', goal_impossible=False, query_ready=True))


def test_fallback_bound_describes_wait_and_keeps_original_planned_bounds():
    case = dict(operating='low', retry_cost='17/20', stage='B')
    law = {op: dict.fromkeys(cats, F(1, len(cats))) for op, cats in audit.ALPHABETS.items()}
    plan = dict(mix=[['SHORT', '1']], risk_upper='1/20', utility_lower='1/2', goal_upper='4', goal_impossible=False,
        envelopes={op: dict(bounds={cat: ['0', '1'] for cat in cats}) for op, cats in audit.ALPHABETS.items()},
        queries={query: dict(policy='WAIT') for query in ('reward', 'goal', 'risk')},
        query_certificates={query: dict(certified=query == 'reward') for query in ('reward', 'goal', 'risk')})
    row = dict(life=0, index=30, arm='REUSE', case=case, spent=0, execution_certified=False,
        goal_impossible=False, query_certified=False, joint_completed=False, fallback=True,
        budget_exhausted=False, model_seconds=0., initial_plan=plan, terminal_plan=plan,
        batches=[], executed_mix=[['WAIT', '1']])
    score = audit.score_history(row, law)
    assert score['executed']['actual'] == [F(0), F(0), F(0)]
    assert score['executed']['risk_upper'] == score['executed']['utility_lower'] == 0
    assert score['history'][0]['risk_upper'] == F(1, 20)
    assert score['history'][0]['utility_lower'] == F(1, 2)
