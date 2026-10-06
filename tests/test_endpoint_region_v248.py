"""Check same-D centering, one repair, fixed recovery and full event retention."""
from copy import deepcopy
from fractions import Fraction as F

import pytest

from acfqp.science import endpoint_region_v248 as core

S, D, R = core.S, core.D, core.R
CASE = {'operating': 'low', 'retry_cost': '17/20'}
COUNTS = {S: {'DELIVERY': 6, 'LOST': 4}, D: {'DELIVERY': 5, 'RECOVERY': 2, 'LOST': 3},
          R: {'DELIVERY': 2, 'LOST': 8}}
KERNEL = {S: {'DELIVERY': F(9, 10), 'LOST': F(1, 10)},
          D: {'DELIVERY': F(1, 2), 'RECOVERY': F(1, 4), 'LOST': F(1, 4)},
          R: {'DELIVERY': F(3, 4), 'LOST': F(1, 4)}}


def certificate(kernel=KERNEL):
    return {'witness_kind': 'bad_null_mle', 'bad_null_kernel': deepcopy(kernel)}


def events(counts=COUNTS):
    return {op: [dict(counts=deepcopy(counts[op]), threshold=threshold, event=f'A/{role}/{op}')
                 for role, threshold in (('source', 720), ('pool', 720), ('member', 8640))]
            for op in core.joint.OPERATORS}


def dual():
    counts = {op: dict.fromkeys(core.joint.ALPHABETS[op], 1) for op in core.joint.OPERATORS}
    leaf = dict(log_bad_likelihood_upper='3', multiplier='0', gap_endpoint='1',
        gap_coefficients={op: dict.fromkeys(core.joint.ALPHABETS[op], 0) for op in (S, D)},
        row_witnesses={op: dict(kind='simplex_likelihood_dual', nu='4') for op in (S, D)},
        retry_likelihood=dict(probability='3/4'))
    leaves = [deepcopy(leaf) for _ in range(3)]
    leaves[0]['log_bad_likelihood_upper'] = '2'
    leaves[2]['retry_likelihood']['probability'] = '1/2'
    return dict(witness_kind='global_likelihood_dual', embedded_counts=counts, leaves=leaves)


def test_retained_is_exact_old_classification_and_centering_changes_only_r_then_s():
    proof, constraints = certificate(), events()
    before = deepcopy((COUNTS, constraints, proof))
    result = core.classify(COUNTS, constraints, CASE, proof)
    retained, centered = (result['variants'][variant] for variant in core.VARIANTS)
    assert retained == core.original.classify(COUNTS, constraints, CASE, proof)
    c = centered['candidate']
    assert c['kind'] == 'r_centered_fixed_d' and c['parent_kind'] == 'bad_null_mle'
    assert c['original_retry_probability'] == F(3, 4)
    assert c['kernel'][D] == c['recovered_kernel'][D] == KERNEL[D]
    assert c['kernel'][R] == {'DELIVERY': F(1, 5), 'LOST': F(4, 5)}
    assert c['gap'] == retained['candidate']['gap'] == F(50001, 10**6)
    assert c['kernel'][S]['DELIVERY'] == F(1987499, 4000000)
    assert result['distances']['R_CENTERED'][R] == 0
    assert result['distances']['R_CENTERED'][D] == result['distances']['RETAINED'][D] == F(1, 20)
    assert (COUNTS, constraints, proof) == before


def test_centered_uses_original_first_maximum_leaf_and_no_other_leaf_recovery():
    result = core.classify(COUNTS, events(), CASE, dual())
    for variant in core.VARIANTS:
        assert result['variants'][variant]['candidate']['leaf_index'] == 1
    centered = result['variants']['R_CENTERED']['candidate']
    assert set(centered['kernel'][D].values()) == {F(1, 3)}
    assert centered['original_retry_probability'] == F(3, 4)
    assert centered['kernel'][R]['DELIVERY'] == F(1, 5)


def test_recovery_failure_leaves_both_unknown_without_membership_or_alternate_leaf(monkeypatch):
    proof = dual()
    proof['leaves'][1]['row_witnesses'][D] = {'kind': 'free_simplex'}
    monkeypatch.setattr(core.joint, 'membership', lambda *args: pytest.fail('membership without recovery'))
    result = core.classify(COUNTS, events(), CASE, proof)
    for record in result['variants'].values():
        assert record['status'] == 'unknown' and record['candidate']['kernel'] is None
        assert record['candidate']['reason'] == f'free_simplex:{D}'
        assert record['query_regions'] == {} and record['execution_regions'] == []


def test_centered_can_make_its_prespecified_repair_when_retained_repair_is_infeasible():
    kernel, counts = deepcopy(KERNEL), deepcopy(COUNTS)
    kernel[D] = {'DELIVERY': F(0), 'RECOVERY': F(1, 2), 'LOST': F(1, 2)}
    kernel[R] = {'DELIVERY': F(0), 'LOST': F(1)}
    counts[R] = {'DELIVERY': 3, 'LOST': 1}
    result = core.classify(counts, events(counts), CASE, certificate(kernel))
    retained, centered = (result['variants'][variant]['candidate'] for variant in core.VARIANTS)
    assert retained['reason'] == 'short_delivery_outside_simplex' and retained['kernel'] is None
    assert centered['repair_applied'] and centered['kernel'] is not None
    assert centered['kernel'][D] == kernel[D] and centered['kernel'][R]['DELIVERY'] == F(3, 4)


def test_infeasible_center_is_not_clipped_or_retried():
    kernel, counts = deepcopy(KERNEL), deepcopy(COUNTS)
    kernel[D] = {'DELIVERY': F(0), 'RECOVERY': F(1, 2), 'LOST': F(1, 2)}
    counts[R] = {'DELIVERY': 1, 'LOST': 9}
    result = core.classify(counts, events(counts), CASE, certificate(kernel))
    record = result['variants']['R_CENTERED']
    assert record['candidate']['short_delivery_unclipped'] < 0
    assert record['candidate']['reason'] == 'short_delivery_outside_simplex'
    assert record['status'] == 'unknown' and record['candidate']['kernel'] is None
    assert all(value is None for value in result['distances']['R_CENTERED'].values())


def test_all_eight_query_families_and_nine_original_event_labels_are_retained():
    result = core.classify(COUNTS, events(), CASE, certificate())
    for record in result['variants'].values():
        assert set(record['query_regions']) == set(core.joint.FAMILIES)
        assert len(record['execution_regions']) == 9
        assert [row['threshold'] for row in record['execution_regions']] == [720, 720, 8640]*3
        assert {row['event'] for row in record['execution_regions']} == {
            f'A/{role}/{op}' for role in ('source', 'pool', 'member') for op in core.joint.OPERATORS}
        assert all(row['membership']['exact_inside'] for row in record['execution_regions'])
        assert record['status'] == 'full_region_bad_witness'
        assert 'certified' not in record and 'query_ready' not in record


def test_exact_full_d_event_rejection_is_preserved_in_both_variants():
    constraints = events()
    constraints[D][0] = dict(counts={'DELIVERY': 160, 'RECOVERY': 112, 'LOST': 48},
                             threshold=720, event='full_D/source')
    result = core.classify(COUNTS, constraints, CASE, certificate())
    for record in result['variants'].values():
        rejected = [row for row in record['execution_regions'] if row['event'] == 'full_D/source'][0]
        assert not rejected['membership']['exact_inside']
        assert record['canonical_inside'] and record['status'] == 'paid_constraints_reject_candidate'


def test_canonical_product_does_not_override_a_rejecting_paid_query_family():
    counts = {S: {'DELIVERY': 63, 'LOST': 37},
              D: {'DELIVERY': 20, 'RECOVERY': 0, 'LOST': 0}, R: {'DELIVERY': 75, 'LOST': 25}}
    result = core.classify(counts, {op: [] for op in core.joint.OPERATORS}, CASE, certificate())
    for record in result['variants'].values():
        assert record['canonical_inside'] and not record['query_regions']['D_DEL']['exact_inside']
        assert record['status'] == 'paid_constraints_reject_candidate'


def test_both_variants_share_one_original_recovery_and_create_no_query_certificate(monkeypatch):
    reconstruct, calls = core.original.reconstruct, []

    def recover(proof, case):
        calls.append(proof)
        return reconstruct(proof, case)

    monkeypatch.setattr(core.original, 'reconstruct', recover)
    monkeypatch.setattr(core.joint, 'certificate', lambda *args: pytest.fail('diagnosis created a certificate'))
    core.classify(COUNTS, events(), CASE, dual())
    assert len(calls) == 1
