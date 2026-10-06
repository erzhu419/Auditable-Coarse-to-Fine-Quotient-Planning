"""Winning weak duals, full-preview readiness and intermediate claims."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

import pytest

from scripts import audit_goal_feasibility_v258 as audit


@pytest.fixture(scope='module')
def retained_plans():
    return [row for life in audit.LIVES for arm in audit.ARMS for row in audit.rows(
        audit.ROOT/f'reports/trajectory_lifecycle_v256/records_life_{life:02d}_{arm}.jsonl.gz')]


@pytest.fixture(scope='module')
def searched_plan(retained_plans):
    from acfqp.science import goal_feasibility_v258 as core
    row = next(row for row in retained_plans if row['case']['stage'] == 'B'
               and row['query_certified'] and not row['execution_resolved'])
    plan = deepcopy(row['terminal_plan'])
    proof = core.upper_bound(plan, row['case'], Counter())
    plan.update(box_goal_upper=proof['box_goal_upper'], goal_feasibility=proof,
                goal_upper=proof['upper'], goal_impossible=proof['new_impossible'])
    return row, plan


def test_actual_paid_full_D_search_proof_binds_independent_exact_geometry(searched_plan):
    row, plan = searched_plan
    checks = []
    upper = audit.audit_goal_upper(plan, row['case'], lambda name, ok: checks.append((name, ok)))
    assert all(ok for _, ok in checks)
    assert upper <= plan['box_goal_upper']
    assert sum(name == 'winning_D_weak_dual_outward_100_digit_evidence' for name, _ in checks) == 2


def test_corrupted_winning_support_and_reused_goal_bound_are_rejected(searched_plan):
    row, original = searched_plan
    plan = deepcopy(original)
    plan['goal_feasibility']['winner']['d_supports']['DETOUR_RETRY']['support']['upper'] -= F(1, 100)
    failures = []
    audit.audit_goal_upper(plan, row['case'], lambda name, ok: failures.append(name) if not ok else None)
    assert 'winning_D_weak_dual_outward_100_digit_evidence' in failures
    plan = deepcopy(original)
    plan['box_goal_upper'] += F(1, 10)
    plan['goal_upper'] -= F(1, 10)
    failures = []
    audit.audit_goal_upper(plan, row['case'], lambda name, ok: failures.append(name) if not ok else None)
    assert 'original_exact_box_goal_upper_and_frozen_feasibility_skip_rule' in failures
    assert 'safe_minimum_original_box_and_winning_dual_strict_impossibility' in failures


def test_actual_certified_and_box_impossible_skips_keep_original_goal_decisions(retained_plans):
    from acfqp.science import goal_feasibility_v258 as core
    plans = [plan for row in retained_plans for plan in
             [row['initial_plan']]+[batch['plan'] for batch in row['batches']]]
    for predicate, reason in ((lambda plan: F(plan['utility_lower']) >= 2, 'execution_certified'),
                              (lambda plan: F(plan['goal_upper']) < 2, 'box_impossible')):
        original = next(plan for plan in plans if predicate(plan))
        plan = deepcopy(original)
        proof = core.upper_bound(plan, plan['case'], Counter())
        plan.update(box_goal_upper=proof['box_goal_upper'], goal_feasibility=proof,
                    goal_upper=proof['upper'], goal_impossible=proof['new_impossible'])
        checks = []
        audit.audit_goal_upper(plan, plan['case'], lambda name, ok: checks.append((name, ok)))
        assert all(ok for _, ok in checks)
        assert proof['skipped'] and proof['skip_reason'] == reason and proof['winner'] is None
        assert proof['search']['evaluations'] == 0 and proof['upper'] == F(original['goal_upper'])


def test_full12_check_rejects_query_only_readiness_and_reuses_upcoming_empty_member_events(monkeypatch):
    state = audit.state_for(0)
    state['source_paid'] = 3456
    state['sources']['A'] = audit.native_bank()
    previews = []
    for identity in range(3):
        for cost_index, (operating, retry) in enumerate(audit.COSTS):
            case = dict(id=f'v258_l0_A_t{identity}_c{cost_index}', context='A', stage='A', operating=operating, retry_cost=retry)
            previews.append(dict(life=0, arm=audit.ARMS[0], stage='A', context='A', index=3, check_id=0,
                identity=identity, cost_index=cost_index, preview_id=identity*4+cost_index,
                budget=audit.budget(0, 3, state), plan=dict(case=case, utility_lower=F(0),
                    goal_impossible=not (identity == 1 and cost_index == 3), query_ready=True)))
    visited = []

    def execution_plan(plan, case, counts, constraints, cache, check):
        visited.append(case['id'])
        assert plan['case'] == case and counts == audit.paid.empty()
        for operator in audit.OPERATORS:
            assert constraints[operator][2] == dict(counts=audit.paid.empty()[operator], threshold=8640,
                                                   event=f'l0/member3/{operator}')

    monkeypatch.setattr(audit, 'audit_execution_plan', execution_plan)
    monkeypatch.setattr(audit, 'audit_query', lambda *args: dict.fromkeys(audit.QUERIES, True))
    metadata = dict(life=0, arm=audit.ARMS[0], stage='A', context='A', index=3, check_id=0,
        preview_ids=list(range(12)), ready_by_type=[True]*3, all_ready=True, cursor=0, budget=audit.budget(0, 3, state))
    failures = []
    result = audit.audit_shared_check(0, audit.ARMS[0], 'A', 'A', 3, state,
        dict(previews=previews, checks=[metadata]), [], {}, set(), {}, {},
        lambda name, ok: failures.append(name) if not ok else None)
    assert len(visited) == 12 and result['ready_by_type'] == [True, False, True] and not result['all_ready']
    assert failures == ['all12_current_query_AND_execution_resolved_shared_check_no_latched_readiness']


def test_intermediate_uncertified_lower_and_risk_claims_are_scored_before_terminal_summary(searched_plan):
    original, plan = searched_plan
    first, last = deepcopy(plan), deepcopy(plan)
    first.update(mix=[['WAIT', F(1)]], utility_lower=F(1, 10), risk_upper=F(0))
    last.update(mix=[['SHORT', F(1)]], utility_lower=F(0), risk_upper=F(0))
    row = {field: original[field] for field in ('life', 'arm', 'index', 'identity')}
    row.update(initial_plan=first, batches=[dict(plan=last, spent=16)])
    _, laws, _, _ = audit.paid.world(original['life'])
    history = audit.score_execution_history(row, laws[original['index']])
    assert [point['prefix_position'] for point in history] == [0, 1]
    assert [point['is_terminal'] for point in history] == [False, True]
    assert history[0]['false_utility_lower'] and not history[0]['false_execution_certificate']
    assert history[1]['false_risk_upper'] and history[1]['actual_risk'] > 0
