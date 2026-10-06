from collections import Counter
from copy import deepcopy

from scripts import audit_common_inheritance_return_v246 as audit
from tests.test_query_allocation_lifecycle_v245_audit import fixture


def test_directed_replay_reads_actual_current_profile_before_choice():
    member, plan = fixture()
    certificate = plan['query_evidence']['queries']['goal']['comparisons'][0]
    plan['query_evidence']['queries']['goal']['comparisons'] = [dict(profile_id=1)]
    before, work = deepcopy(plan), Counter()
    choice = audit.choose('RETURN_DIRECTED', member, plan,
                          [dict(certificate={'wrong': True}), dict(certificate=certificate)], work)
    assert choice['operator'] == 'RECOVERY_RETRY'
    assert work['query_directed_choices'] == 1
    assert plan == before


def prefix_rows(sources):
    pools = deepcopy(sources)
    rows, history = [], 0
    for index in audit.PREFIX_TARGETS:
        context = 'A' if index < 30 else 'B'
        identity = index % 3
        operator = 'SHORT_PASS'
        pool = pools[context.lower()][identity]
        before, member = deepcopy(pool), audit.paid.empty()
        increments = dict(DELIVERY=7, LOST=9)
        for category, count in increments.items():
            pool[operator][category] += count
            member[operator][category] += count
        rows.append(dict(life=0, index=index, arm='ONE_WAY',
            case=dict(context=context), identity=identity, pooled_before=before,
            pooled_after=deepcopy(pool), member=member, spent=16,
            history_paid_samples=history, batches=[dict(operator=operator, increments=increments)]))
        history += 16
    return rows, pools


def test_common_prefix_excludes_other_arms_and_historical_return():
    sources = dict(a=[audit.paid.empty() for _ in range(3)],
                   b=[audit.paid.empty() for _ in range(3)])
    rows, expected = prefix_rows(sources)
    rows.extend([dict(arm='QUERY_DIRECTED', index=3), dict(arm='REBUILD', index=4),
                 dict(arm='ONE_WAY', index=54)])
    checks = []
    state, history = audit.common_prefix(0, sources, rows,
        lambda name, condition: checks.append((name, condition)))
    assert all(condition for _, condition in checks)
    assert history == 48*16
    assert state['a'] == expected['a'] and state['b'] == expected['b']
    assert state['a_switch'] == expected['a']
    assert all(audit.paid.samples(pool) == 0 for bank in sources.values() for pool in bank)


def test_common_prefix_reports_native_pool_and_fee_corruption():
    sources = dict(a=[audit.paid.empty() for _ in range(3)],
                   b=[audit.paid.empty() for _ in range(3)])
    rows, _ = prefix_rows(sources)
    rows[1]['history_paid_samples'] += 16
    rows[2]['pooled_before']['SHORT_PASS']['DELIVERY'] += 1
    failures = []
    audit.common_prefix(0, sources, rows,
        lambda name, condition: failures.append(name) if not condition else None)
    assert failures == ['prefix_native_pool_after_and_paid_history',
                        'prefix_original_paid_native_pool_before']


def condition_fixture():
    method = dict(query_certified=54, joint_completed=54, total_samples=48000)
    method.update(dict.fromkeys(('false_query_certificates', 'false_execution_certificates',
        'false_impossible_certificates', 'false_goal_uppers', 'risk_violations',
        'executed_risk_violations'), 0))
    return dict(ONE_WAY=deepcopy(method), RETURN_DIRECTED=deepcopy(method))


def test_conditions_require_minimum_and_quality_but_allow_equal_charged_cost():
    methods = condition_fixture()
    assert all(audit.conditions(methods).values())
    methods['RETURN_DIRECTED']['query_certified'] = 53
    result = audit.conditions(methods)
    assert not result['a_return_quality'] and not result['matched_one_way_query_quality']
    methods['RETURN_DIRECTED']['query_certified'] = 54
    methods['RETURN_DIRECTED']['total_samples'] += 16
    assert not audit.conditions(methods)['actual_acquisition_nondegrading_vs_one_way']


def test_conditions_include_false_goal_upper_at_any_retained_point():
    methods = condition_fixture()
    methods['ONE_WAY']['false_goal_uppers'] = 1
    assert not audit.conditions(methods)['valid_certificates_and_execution']
