from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from scripts import audit_query_allocation_lifecycle_v245 as audit


def fixture():
    counts = {'SHORT_PASS': dict(DELIVERY=5, LOST=5),
              'DETOUR_PASS': dict(DELIVERY=5, LOST=3, RECOVERY=2),
              'RECOVERY_RETRY': dict(DELIVERY=9, LOST=1)}
    kernel = {'SHORT_PASS': dict(DELIVERY=F(1, 2), LOST=F(1, 2)),
              'DETOUR_PASS': dict(DELIVERY=F(1, 2), LOST=F(3, 10), RECOVERY=F(1, 5)),
              'RECOVERY_RETRY': dict(DELIVERY=F(1, 10), LOST=F(9, 10))}
    certificate = dict(other='DETOUR_RETRY', certified=False,
        witness_kind='bad_null_mle', bad_null_kernel=kernel)
    plan = dict(case=dict(operating='low', retry_cost='17/20'),
        utility_lower=F(2), goal_impossible=False, query_ready=False,
        evidence_counts=counts, effective_n=dict.fromkeys(audit.OPERATORS, 10),
        posterior=audit.paid.posterior(counts),
        envelopes={op: dict(bounds={cat: [F(0), F(1)] for cat in categories})
                   for op, categories in audit.ALPHABETS.items()},
        query_certificates={query: dict(policy=policy, certified=query == 'reward',
                                       regret_upper=F(0) if query == 'reward' else F(20))
                            for query, policy in [('reward', 'WAIT'), ('goal', 'SHORT'), ('risk', 'SHORT')]},
        query_gap_bounds={query: {policy: F(policy != chosen)
                         for policy in audit.prior.joint.POLICIES}
                         for query, chosen in [('reward', 'WAIT'), ('goal', 'SHORT'), ('risk', 'SHORT')]},
        query_evidence=dict(queries=dict(goal=dict(policy='SHORT', comparisons=[certificate]))))
    return audit.paid.empty(), plan


def test_live_empirical_full_rows_select_retry_without_changing_plan():
    member, plan = fixture()
    before, work = deepcopy(plan), Counter()
    choice = audit.directed_choice(member, plan, work)
    assert choice['operator'] == 'RECOVERY_RETRY'
    assert choice['query_directed_candidate']['gap'] == F(50001, 1000000)
    assert choice['query_directed_scores']['DETOUR_PASS'] == 0
    assert work == Counter(query_directed_reconstructions=1,
                          query_directed_row_kl_evaluations=3, query_directed_choices=1)
    assert plan == before


def test_unresolved_execution_keeps_original_allocation_exactly():
    member, plan = fixture()
    plan['utility_lower'] = F(1)
    work = Counter()
    assert audit.directed_choice(member, plan, work) == audit.original_choice(member, plan)
    assert work == Counter(oracle_gap_direct_choices=1)


def test_positive_observed_count_at_boundary_zero_retains_original_choice():
    member, plan = fixture()
    kernel = plan['query_evidence']['queries']['goal']['comparisons'][0]['bad_null_kernel']
    kernel['RECOVERY_RETRY'] = dict(DELIVERY=F(1), LOST=F(0))
    work = Counter()
    choice = audit.directed_choice(member, plan, work)
    assert choice['query_directed_reason'] == 'positive_count_boundary_zero'
    assert choice['query_directed_scores'] is None
    assert choice['operator'] == audit.original_choice(member, plan)['operator']
    assert work['query_directed_choices'] == 0 and work['query_directed_fallback_choices'] == 1


def test_materialized_comparison_uses_referenced_current_profile_only():
    _, plan = fixture()
    comparison = plan['query_evidence']['queries']['goal']['comparisons'][0]
    plan['query_evidence']['queries']['goal']['comparisons'] = [dict(profile_id=1)]
    restored = audit.materialize_goal(plan, [dict(certificate={'wrong': True}), dict(certificate=comparison)])
    assert restored['query_evidence']['queries']['goal']['comparisons'] == [comparison]
    assert plan['query_evidence']['queries']['goal']['comparisons'] == [dict(profile_id=1)]
