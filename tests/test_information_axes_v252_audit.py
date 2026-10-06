from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json

from scripts import audit_information_axes_v252 as audit


def fixture():
    counts = {audit.S: dict(DELIVERY=6, LOST=4),
              audit.D: dict(DELIVERY=5, LOST=3, RECOVERY=2),
              audit.R: dict(DELIVERY=2, LOST=8)}
    case = dict(operating='low', retry_cost='17/20')
    certificate = dict(witness_kind='global_likelihood_dual', leaves=[])
    sources = dict(a=[deepcopy(counts) for _ in range(3)])
    constraints = audit.witness.original_constraints(0, 60, 0, sources, counts, counts)
    return counts, constraints, case, certificate


def test_independent_SD_rows_and_one_exact_R_solve_do_not_require_profile_recovery():
    from acfqp.science import information_axes_v252 as producer
    counts, constraints, case, certificate = fixture()
    original = deepcopy((counts, constraints, case, certificate))
    retained = audit.witness.reconstruct_candidate(certificate, case)
    centered = audit.centered_candidate(retained, counts, case)
    candidate = audit.sd_centered_candidate(counts, case)
    result = producer.classify(counts, constraints, case, certificate)
    assert retained['kernel'] is centered['kernel'] is None
    assert candidate == result['variants']['SD_CENTERED']['candidate']
    assert candidate['kernel'][audit.S] == dict(DELIVERY=F(3, 5), LOST=F(2, 5))
    assert candidate['kernel'][audit.D] == dict(DELIVERY=F(1, 2), LOST=F(3, 10), RECOVERY=F(1, 5))
    assert candidate['kernel'][audit.R]['DELIVERY'] == F(570001, 800000)
    assert candidate['gap'] == audit.witness.STRICT_GAP
    assert candidate['fixed_rows'] == {op: candidate['kernel'][op] for op in (audit.S, audit.D)}
    assert (counts, constraints, case, certificate) == original


def test_all_three_fixed_candidates_use_eight_exact_query_and_nine_full_events():
    from acfqp.science import information_axes_v252 as producer
    counts, constraints, case, _ = fixture()
    certificate = dict(witness_kind='bad_null_mle', bad_null_kernel={
        audit.S: dict(DELIVERY=F(9, 10), LOST=F(1, 10)),
        audit.D: dict(DELIVERY=F(1, 2), LOST=F(1, 4), RECOVERY=F(1, 4)),
        audit.R: dict(DELIVERY=F(3, 4), LOST=F(1, 4))})
    result = producer.classify(counts, constraints, case, certificate)
    retained = audit.witness.reconstruct_candidate(certificate, case)
    candidates = dict(RETAINED=retained, R_CENTERED=audit.centered_candidate(retained, counts, case),
                      SD_CENTERED=audit.sd_centered_candidate(counts, case))
    checks = []
    for variant in audit.VARIANTS:
        saved = dict(result['variants'][variant], empirical_rows=result['empirical_rows'],
                     distances=result['distances'][variant])
        rebuilt = audit.audit_variant(saved, candidates[variant], counts, constraints, case,
            lambda name, ok: checks.append((name, ok)))
        assert len(rebuilt['query_regions']) == 8 and len(rebuilt['execution_regions']) == 9
        assert [event['threshold'] for event in rebuilt['execution_regions']] == [720, 720, 8640]*3
    assert all(ok for _, ok in checks)
    saved = dict(result['variants']['SD_CENTERED'], empirical_rows=result['empirical_rows'],
                 distances=result['distances']['SD_CENTERED'])
    saved['execution_regions'][2]['event'] = 'l0/B/pool0/SHORT_PASS'
    failed = []
    audit.audit_variant(saved, candidates['SD_CENTERED'], counts, constraints, case,
        lambda name, ok: failed.append(name) if not ok else None)
    assert failed == ['literal_original_execution_event_labels_counts_positions_thresholds']


def test_infeasible_R_solution_remains_unknown_and_is_not_clipped_or_recovered():
    from acfqp.science import information_axes_v252 as producer
    counts, constraints, case, certificate = fixture()
    counts[audit.S] = dict(DELIVERY=10, LOST=0)
    counts[audit.D] = dict(DELIVERY=0, LOST=9, RECOVERY=1)
    constraints = audit.witness.original_constraints(0, 60, 0,
        dict(a=[deepcopy(counts) for _ in range(3)]), counts, counts)
    result = producer.classify(counts, constraints, case, certificate)
    candidate = audit.sd_centered_candidate(counts, case)
    assert candidate == result['variants']['SD_CENTERED']['candidate']
    assert candidate['retry_delivery_unclipped'] > 1 and candidate['solve_applied']
    assert candidate['kernel'] is None and candidate['reason'] == 'retry_delivery_outside_simplex'
    saved = dict(result['variants']['SD_CENTERED'], empirical_rows=result['empirical_rows'],
                 distances=result['distances']['SD_CENTERED'])
    checks = []
    rebuilt = audit.audit_variant(saved, candidate, counts, constraints, case,
        lambda name, ok: checks.append((name, ok)))
    assert all(ok for _, ok in checks) and rebuilt['status'] == 'unknown'
    assert rebuilt['query_regions'] == {} and rebuilt['execution_regions'] == []


def test_actual_V251_native_timeline_endpoint_counts_all_fees_and_roster_match(monkeypatch):
    from scripts import run_information_axes_v252 as producer
    monkeypatch.setattr(producer.core, 'classify', lambda *args: (_ for _ in ()).throw(
        AssertionError('candidate calculation before frozen endpoint selection')))
    checks = []
    check = lambda name, ok: checks.append((name, ok))
    sources = audit.witness.source_banks(audit.load(audit.SOURCE/'source_records.json'), check)
    cases = {row['life']: row['cases'] for row in audit.load(audit.SOURCE/'cases.json')}
    interfaces = {row['life']: row for row in audit.load(audit.SOURCE/'interfaces.json')}
    selected, fees = [], []
    for life in audit.LIVES:
        for arm in audit.ARMS:
            snapshots, fee = audit.terminal_snapshots(life, arm, sources[life], cases[life], interfaces[life], check)
            selected.extend(snapshots)
            fees.append(fee)
    selected.sort(key=lambda snapshot: (snapshot['record']['life'], snapshot['record']['index'],
                                       audit.ARMS.index(snapshot['record']['arm'])))
    endpoints = [audit.endpoint(snapshot) for snapshot in selected]
    actual_endpoints, actual_fees = producer.endpoints()
    assert endpoints == actual_endpoints and fees == actual_fees and all(ok for _, ok in checks)
    assert len(endpoints) == 48 and Counter((row['life'], row['arm']) for row in endpoints) == Counter(
        {(life, arm): 8 for life in audit.LIVES for arm in audit.ARMS})
    assert [fee['total_samples'] for fee in fees] == [14144, 14144, 17072, 17072, 17168, 16896]
    assert all(len(row['joint_constraints'][op]) == 3 for row in endpoints for op in audit.OPERATORS)


def test_three_pair_status_summaries_and_distinct_endpoint_union_match_saved_schema():
    from scripts import run_information_axes_v252 as producer
    records = []
    for index in (60, 61):
        for arm in audit.ARMS:
            for variant in audit.VARIANTS:
                bad = index == 60 or variant == 'SD_CENTERED'
                records.append(dict(life=0, index=index, arm=arm, variant=variant,
                    status='full_region_bad_witness' if bad else 'unknown', canonical_inside=bad,
                    all_query_inside=bad, all_execution_inside=bad, query_regions={}, execution_regions=[]))
    actual = json.loads(json.dumps(producer.summarize(records, [])))
    expected = audit.summarize(records, [])
    assert actual == expected and expected['records'] == 12 and expected['endpoints'] == 4
    assert len(expected['paired_arm_statuses']) == 3 and len(expected['within_arm_variant_statuses']) == 6
    assert all(row['distinct_full_bad_endpoints'] == 2 for row in expected['arm_full_bad_endpoint_unions'])
    assert all(row['same_evidence_query_certificate_ceiling'] == 70 for row in expected['arm_full_bad_endpoint_unions'])
