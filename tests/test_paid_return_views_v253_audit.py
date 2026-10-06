from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
import json

import pytest

from scripts import audit_paid_return_views_v253 as audit


def test_actual_V251_all_return_snapshots_native_time_fees_and_original_plans_match(monkeypatch):
    from scripts import run_paid_return_views_v253 as producer
    monkeypatch.setattr(producer.core, 'make_two_way', lambda *args: (_ for _ in ()).throw(
        AssertionError('no new planning during snapshot replay')))
    checks = []
    check = lambda name, ok: checks.append((name, ok))
    sources = audit.timeline.witness.source_banks(audit.load(audit.SOURCE/'source_records.json'), check)
    cases = {row['life']: row['cases'] for row in audit.load(audit.SOURCE/'cases.json')}
    interfaces = {row['life']: row for row in audit.load(audit.SOURCE/'interfaces.json')}
    snapshots, fees = [], []
    for life in audit.LIVES:
        for arm in audit.ARMS:
            selected, fee = audit.terminal_snapshots(life, arm, sources[life], cases[life], interfaces[life], check)
            snapshots.extend(selected)
            fees.append(fee)
    actual, actual_fees = producer.collect_snapshots()
    assert snapshots == actual and fees == actual_fees and all(ok for _, ok in checks)
    assert len(snapshots) == 144 and Counter((row['life'], row['arm']) for row in snapshots) == Counter(
        {(life, arm): 24 for life in audit.LIVES for arm in audit.ARMS})
    assert [fee['total_samples'] for fee in fees] == [14144, 14144, 17072, 17072, 17168, 16896]
    for life in audit.LIVES:
        for arm in audit.ARMS:
            selected = [row for row in snapshots if row['life'] == life and row['arm'] == arm]
            assert [row['index'] for row in selected] == list(range(54, 78))
            for identity in range(3):
                own = [row for row in selected if row['identity'] == identity]
                assert all(row['b_pool'] == own[0]['b_pool'] for row in own)
                assert all(row['one_way_plan']['evidence_counts'] == row['a_pool'] for row in own)
                assert all(row['one_way_plan']['return_transfer'] is None for row in own)


def counts(amount):
    return {operator: {category: amount+position for position, category in enumerate(audit.ALPHABETS[operator])}
            for operator in audit.OPERATORS}


def snapshot(changed):
    return dict(life=1, arm='QUERY_SHARED', index=58, identity=0,
        case=dict(context='A', stage='A_RETURN', operating='low', retry_cost='17/20'),
        a_source=counts(10), a_pool=counts(20), b_source=counts(2), b_pool=counts(5), member=counts(3),
        mapped_b_identity=1, interface=dict(changed_operator=changed, b_to_a=[2, 0, 1]),
        baseline_provenance=dict(directory='query_shared_acquisition_v251',
            record_file='records_life_01_QUERY_SHARED.jsonl.gz', profile_file='profiles_life_01_QUERY_SHARED.jsonl.gz'),
        retained_fees=dict(total_reference_paid_samples=1000), spent=16,
        retained_executed_mix=[['WAIT', '1']], one_way_plan=dict(
            query_evidence=dict(queries=dict(goal=dict(comparisons=[dict(profile_id=777)])))))


@pytest.mark.parametrize('changed', audit.OPERATORS)
def test_independent_TWOWAY_constructor_matches_V243_and_excludes_changed_native_row(changed):
    from acfqp.science import paid_return_views_v253 as producer
    saved = snapshot(changed)
    original = deepcopy(saved)
    counts_, constraints, transfer = audit.two_way_evidence(saved)
    actual = json.loads(json.dumps(producer.two_way_evidence(saved)))
    assert actual == [counts_, constraints, transfer]
    sources = dict(a=[counts(100) for _ in range(3)], b=[counts(200) for _ in range(3)])
    state = dict(a=[counts(300) for _ in range(3)], b=[counts(400) for _ in range(3)])
    sources['a'][0], state['a'][0] = saved['a_source'], saved['a_pool']
    sources['b'][1], state['b'][1] = saved['b_source'], saved['b_pool']
    assert counts_ == audit.prior.evidence_counts(state, saved['case'], 0, 'TWO_WAY', saved['interface'])
    assert constraints == audit.prior.execution_constraints(1, 58, saved['case'], 0, sources, state,
                                                            saved['member'], 'TWO_WAY', saved['interface'])
    assert transfer == audit.prior.transfer_view(saved['case'], 0, state, 'TWO_WAY', saved['interface'])
    assert len([region for regions in constraints.values() for region in regions]) == 13
    assert len(constraints[changed]) == 3 and counts_[changed] == saved['a_pool'][changed]
    for operator in transfer['operators']:
        assert counts_[operator] == {category: saved['a_pool'][operator][category]+saved['b_pool'][operator][category]
                                    for category in audit.ALPHABETS[operator]}
        assert constraints[operator][-2]['counts'] == saved['b_source'][operator]
        assert constraints[operator][-1]['counts'] == saved['b_pool'][operator]
        assert all(region['event'] == f'l1/B/pool1/{operator}' for region in constraints[operator][-2:])
    assert saved == original


def test_original_private_profile_references_actual_execution_and_fees_are_literal():
    original = snapshot(audit.OPERATORS[0])
    record = {field: deepcopy(original[field]) for field in audit.RECORD_FIELDS}
    record.update(model_seconds=0.01, output_seconds=0.01)
    failures = []
    audit.original_record(record, original, lambda name, ok: failures.append(name) if not ok else None)
    assert not failures
    for field, changed in (
        ('one_way_plan', dict(query_evidence=dict(queries=dict(goal=dict(comparisons=[dict(profile_id=0)]))))),
        ('retained_executed_mix', [['SHORT', '1']]),
        ('retained_fees', dict(total_reference_paid_samples=0))):
        invalid = deepcopy(record)
        invalid[field] = changed
        failures = []
        audit.original_record(invalid, original, lambda name, ok: failures.append(name) if not ok else None)
        assert failures == ['original_ONE_plan_profile_namespace_actual_execution_and_fees_unchanged']


def minimal_plan(query_ready, certified, impossible, policy='SHORT'):
    selected = dict(reward='WAIT', goal=policy, risk='DETOUR_RETURN')
    return dict(utility_lower='2' if certified else '1', goal_impossible=impossible, query_ready=query_ready,
        queries={query: dict(policy=chosen) for query, chosen in selected.items()},
        query_evidence=dict(queries={query: dict(policy=chosen, certified=query_ready or query == 'reward')
                                    for query, chosen in selected.items()}),
        query_blockers={query: [] if query_ready or query == 'reward' else ['DETOUR_RETRY'] for query in selected})


def test_fixed_view_gain_loss_choices_and_impossibility_summary_matches_producer():
    from scripts import run_paid_return_views_v253 as producer
    records = []
    variants = [(minimal_plan(False, True, False), minimal_plan(True, True, False)),
                (minimal_plan(True, False, True), minimal_plan(False, False, False, 'DETOUR_RETRY')),
                (minimal_plan(True, False, False), minimal_plan(True, False, True)),
                (minimal_plan(False, False, True), minimal_plan(False, True, False))]
    for life in audit.LIVES:
        for arm in audit.ARMS:
            for offset, (one, two) in enumerate(variants):
                records.append(dict(life=life, arm=arm, index=54+offset, identity=offset%3,
                                    one_way_plan=one, two_way_plan=two))
    expected = audit.summarize(records, [])
    assert expected == json.loads(json.dumps(producer.summarize(records, [])))
    state = audit.plan_state(variants[1][0])
    assert state['execution_resolved'] and state['joint_ready'] and not state['execution_certified']
    group = expected['life_summaries'][0]
    assert group['paired']['query_ready']['gains'] == group['paired']['query_ready']['losses'] == 1
    assert group['paired']['certified_by_query']['goal']['gains'] == 1
    assert group['paired']['certified_by_query']['goal']['losses'] == 1
    assert group['paired']['query_choices']['goal']['changed'] == 1
    assert group['views']['ONE_WAY']['execution_certified'] == 1
    assert group['views']['ONE_WAY']['execution_resolved'] == 3
    assert expected['new_observations'] == expected['one_way_replans'] == expected['new_truth_scoring_calls'] == 0
    assert expected['view_delta_scope'] == audit.DELTA_SCOPE


def test_audit_job_reads_only_new_private_TWOWAY_profiles_and_preserves_ONE_namespace(monkeypatch, tmp_path):
    monkeypatch.setattr(audit, 'OUTPUT', tmp_path)
    snapshots, records = [], []
    profile = dict(profile_id=0, certificate=dict(certified=False, leaves=[]))
    for index in audit.RETURN_TARGETS:
        saved = snapshot(audit.OPERATORS[0])
        saved['life'], saved['index'], saved['arm'] = 0, index, 'QUERY_SHARED'
        counts_, constraints, transfer = audit.two_way_evidence(saved)
        comparisons = [dict(profile_id=0, other=policy, certified=False)
                       for policy in ('WAIT', 'SHORT', 'DETOUR_RETRY')]
        new = dict(case=saved['case'], evidence_counts=counts_, joint_constraints=constraints,
            return_transfer=transfer, query_evidence=dict(queries={query: dict(comparisons=comparisons)
                                                                 for query in ('goal', 'risk')}))
        records.append(dict(**{field: deepcopy(saved[field]) for field in audit.RECORD_FIELDS},
                            two_way_plan=new, model_seconds=0.01, output_seconds=0.01))
        snapshots.append(saved)
    for kind, data in (('records', records), ('profiles', [profile])):
        with gzip.open(tmp_path/f'{kind}_life_00_QUERY_SHARED.jsonl.gz', 'wt') as stream:
            stream.writelines(json.dumps(row)+'\n' for row in data)
    artifact = dict(life=0, arm='QUERY_SHARED', profiles=1, model_seconds=sum(row['model_seconds'] for row in records),
        output_seconds=1., worker_wall_seconds=1.,
        work=dict(reuse_rebuild_joint_plans=24, online_query_comparison_calls=144),
        normalizer_cache_statistics={name: dict(maxsize=size, currsize=0, hits=0, misses=0)
                                     for name, size in (('execution', 4096), ('query', 256))})
    (tmp_path/'worker_artifacts_life_00_QUERY_SHARED.json').write_text(json.dumps(artifact))
    proof_calls, plan_calls = [], []
    def audit_profile(actual, check):
        proof_calls.append(actual['profile_id'])
        assert actual == profile
        return False
    def audit_plan(plan, case, counts_, constraints, profiles, decisions, projections, used, check):
        plan_calls.append(case)
        assert case['retry_cost'] == '17/20'
        assert plan['evidence_counts'] == counts_ and plan['joint_constraints'] == constraints
        assert profiles == [profile] and decisions == {0: False}
        assert all(reference['profile_id'] == 0 for query in ('goal', 'risk')
                   for reference in plan['query_evidence']['queries'][query]['comparisons'])
        used.add(0)
    monkeypatch.setattr(audit.prior, 'audit_profile', audit_profile)
    monkeypatch.setattr(audit.prior, 'audit_plan', audit_plan)
    result = audit.audit_life_arm((0, 'QUERY_SHARED', snapshots))
    assert not result['failures'] and proof_calls == [0] and len(plan_calls) == 24
    assert result['profiles'] == 1 and result['records'] == records
    assert all(row['one_way_plan']['query_evidence']['queries']['goal']['comparisons'][0]['profile_id'] == 777
               for row in result['records'])
