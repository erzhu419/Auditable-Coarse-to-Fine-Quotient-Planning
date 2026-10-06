from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import endpoint_region_v248 as producer
from scripts import audit_endpoint_regions_v248 as audit


def fixture():
    counts = {audit.S: dict(DELIVERY=6, LOST=14),
              audit.D: dict(DELIVERY=6, LOST=8, RECOVERY=6),
              audit.R: dict(DELIVERY=4, LOST=16)}
    case = dict(operating='low', retry_cost='17/20')
    leaf = dict(log_bad_likelihood_upper=F(-10), multiplier=0, gap_endpoint=F(17, 32),
        gap_coefficients=audit.witness.restored_coefficients(case, F(17, 32)),
        retry_interval=[F(1, 2), F(17, 32)], retry_likelihood=dict(probability=F(1, 2)),
        row_witnesses={operator: dict(kind='simplex_likelihood_dual', nu=20)
                       for operator in (audit.S, audit.D)})
    certificate = dict(witness_kind='global_likelihood_dual', embedded_counts=counts,
                       leaves=[leaf, deepcopy(leaf)])
    sources = dict(a=[deepcopy(counts) for _ in range(3)])
    constraints = audit.witness.original_constraints(0, 60, 0, sources, counts, counts)
    return counts, constraints, case, certificate


def test_two_candidates_preserve_original_D_and_center_R_with_own_exact_repair():
    counts, constraints, case, certificate = fixture()
    before = deepcopy((counts, certificate))
    original = audit.witness.reconstruct_candidate(certificate, case)
    centered = audit.centered_candidate(original, counts, case)
    produced = producer.classify(counts, constraints, case, certificate)
    assert original['leaf_index'] == centered['leaf_index'] == 0
    assert original['kernel'][audit.R]['DELIVERY'] == F(1, 2)
    assert centered['kernel'][audit.R]['DELIVERY'] == F(1, 5)
    assert original['recovered_kernel'][audit.D] == centered['recovered_kernel'][audit.D]
    assert centered['recovered_kernel'][audit.S] == original['recovered_kernel'][audit.S]
    assert centered['kernel'][audit.S] != original['kernel'][audit.S]
    assert centered['gap'] == original['gap'] == audit.witness.STRICT_GAP
    assert centered == produced['variants']['R_CENTERED']['candidate']
    assert (counts, certificate) == before


def test_both_variants_verify_all_eight_query_and_nine_original_execution_regions():
    counts, constraints, case, certificate = fixture()
    produced = producer.classify(counts, constraints, case, certificate)
    retained = audit.witness.reconstruct_candidate(certificate, case)
    candidates = dict(RETAINED=retained, R_CENTERED=audit.centered_candidate(retained, counts, case))
    checks = []
    for variant, candidate in candidates.items():
        saved = dict(produced['variants'][variant], empirical_rows=produced['empirical_rows'],
                     distances=produced['distances'][variant])
        rebuilt = audit.audit_variant(saved, candidate, counts, constraints, case,
            lambda name, condition: checks.append((name, condition)))
        assert len(rebuilt['query_regions']) == 8 and len(rebuilt['execution_regions']) == 9
        assert all(event['threshold'] == (8640 if event['position'] == 2 else 720)
                   for event in rebuilt['execution_regions'])
    assert all(condition for _, condition in checks)


def test_literal_execution_label_and_member_threshold_are_verified_separately_from_admission():
    counts, constraints, case, certificate = fixture()
    produced = producer.classify(counts, constraints, case, certificate)
    saved = dict(produced['variants']['R_CENTERED'], empirical_rows=produced['empirical_rows'],
                 distances=produced['distances']['R_CENTERED'])
    saved['execution_regions'][2]['event'] = 'l0/B/pool0/SHORT_PASS'
    saved['execution_regions'][2]['threshold'] = 720
    failures = []
    audit.audit_variant(saved, audit.centered_candidate(audit.witness.reconstruct_candidate(certificate, case),
        counts, case), counts, constraints, case,
        lambda name, condition: failures.append(name) if not condition else None)
    assert failures == ['literal_original_execution_event_labels_counts_positions_thresholds']


def test_certificate_ceiling_uses_union_of_distinct_bad_endpoints_across_variants():
    records = []
    for index in (60, 61):
        for arm in audit.ARMS:
            for variant in audit.VARIANTS:
                records.append(dict(life=0, index=index, arm=arm, variant=variant,
                    status='full_region_bad_witness', canonical_inside=True, all_query_inside=True,
                    all_execution_inside=True, query_regions={}, execution_regions=[]))
    summary = audit.summarize(records, [])
    assert all(row['distinct_full_bad_endpoints'] == 2 for row in summary['arm_full_bad_endpoint_unions'])
    assert all(row['same_evidence_query_certificate_ceiling'] == 70
               for row in summary['arm_full_bad_endpoint_unions'])
