from copy import deepcopy
from fractions import Fraction as F

import pytest

from acfqp.science import goal_joint_region_v244 as core
from acfqp.science import joint_query_evidence_v235 as joint

CASE = dict(operating='low', retry_cost='17/20')
KERNEL = {core.S: {'DELIVERY': F(9, 10), 'LOST': F(1, 10)},
          core.D: {'DELIVERY': F(1, 2), 'RECOVERY': F(1, 4), 'LOST': F(1, 4)},
          core.R: {'DELIVERY': F(3, 4), 'LOST': F(1, 4)}}


def mle(kernel=KERNEL):
    return dict(witness_kind='bad_null_mle', bad_null_kernel=deepcopy(kernel))


def empty_counts():
    return {op: dict.fromkeys(joint.ALPHABETS[op], 0) for op in joint.OPERATORS}


def dual():
    counts = {op: dict.fromkeys(joint.ALPHABETS[op], 1) for op in joint.OPERATORS}
    leaf = dict(log_bad_likelihood_upper='3', multiplier='0', gap_endpoint='1',
        gap_coefficients={op: dict.fromkeys(joint.ALPHABETS[op], 0) for op in (core.S, core.D)},
        row_witnesses={op: dict(kind='simplex_likelihood_dual', nu='4') for op in (core.S, core.D)},
        retry_likelihood=dict(probability='3/4'))
    leaves = [deepcopy(leaf) for _ in range(3)]
    leaves[0]['log_bad_likelihood_upper'] = '2'
    leaves[2]['retry_likelihood']['probability'] = '1/2'
    return dict(witness_kind='global_likelihood_dual', embedded_counts=counts, leaves=leaves)


def test_mle_is_repaired_once_to_strict_goal_gap_without_mutating_input():
    certificate = mle()
    before = deepcopy(certificate)
    result = core.reconstruct(certificate, CASE)
    kernel = result['kernel']
    assert result['repair_applied'] and result['reason'] is None
    assert result['recovered_kernel'] == KERNEL and kernel[core.D] == KERNEL[core.D]
    assert kernel[core.R] == KERNEL[core.R] and kernel[core.S] != KERNEL[core.S]
    assert result['gap'] == core.STRICT_GAP > F(1, 20)
    assert (F(1, 20)+4*F(1, 2)+F(1, 4)*(3-F(17, 20))
            -4*kernel[core.S]['DELIVERY']) == core.STRICT_GAP
    assert certificate == before


def test_maximum_leaf_uses_first_exact_tie_and_actual_retry_probability():
    result = core.reconstruct(dual(), CASE)
    assert result['leaf_index'] == 1 and result['reason'] is None
    assert result['recovered_kernel'][core.S]['DELIVERY'] == F(1, 2)
    assert set(result['recovered_kernel'][core.D].values()) == {F(1, 3)}
    assert result['kernel'][core.R]['DELIVERY'] == F(3, 4)
    assert result['gap'] == core.STRICT_GAP


@pytest.mark.parametrize('failure', ('free_simplex', 'zero_row', 'denominator', 'no_leaf'))
def test_failed_recovery_stops_without_trying_another_leaf(failure):
    certificate = dual()
    leaf = certificate['leaves'][1]
    if failure == 'free_simplex':
        leaf['row_witnesses'][core.D] = dict(kind='free_simplex')
    elif failure == 'zero_row':
        certificate['embedded_counts'][core.D] = dict.fromkeys(joint.ALPHABETS[core.D], 0)
    elif failure == 'denominator':
        leaf['row_witnesses'][core.D]['nu'] = 0
    else:
        for item in certificate['leaves']:
            item['log_bad_likelihood_upper'] = None
    result = core.classify(empty_counts(), {op: [] for op in joint.OPERATORS}, CASE, certificate)
    assert result['status'] == 'unknown' and result['candidate']['reason']
    assert not result['candidate']['repair_applied'] and result['candidate']['kernel'] is None
    assert result['query_regions'] == {} and result['canonical_inside'] is None


def test_outside_short_repair_is_retained_unclipped_and_unavailable():
    kernel = deepcopy(KERNEL)
    kernel[core.D] = dict(DELIVERY=F(0), RECOVERY=F(0), LOST=F(1))
    result = core.reconstruct(mle(kernel), CASE)
    assert result['repair_applied'] and result['short_delivery_unclipped'] == -F(1, 4*10**6)
    assert result['kernel'] is None and result['reason'] == 'short_delivery_outside_simplex'


def test_full_region_bad_witness_checks_all_eight_original_events():
    result = core.classify(empty_counts(), {op: [] for op in joint.OPERATORS}, CASE, mle())
    assert result['status'] == 'full_region_bad_witness'
    assert result['canonical_inside'] and result['all_query_inside'] and result['all_execution_inside']
    assert set(result['query_regions']) == set(joint.FAMILIES)
    assert all(row['threshold'] == 960 for row in result['query_regions'].values())


def test_canonical_product_can_pass_while_another_paid_query_event_rejects():
    counts = {core.S: dict(DELIVERY=63, LOST=37),
              core.D: dict(DELIVERY=20, RECOVERY=0, LOST=0),
              core.R: dict(DELIVERY=75, LOST=25)}
    result = core.classify(counts, {op: [] for op in joint.OPERATORS}, CASE, mle())
    assert result['canonical_inside'] and not result['all_query_inside']
    assert not result['query_regions']['D_DEL']['exact_inside']
    assert result['status'] == 'paid_constraints_reject_candidate'


def test_full_multivariate_execution_event_cannot_be_replaced_by_coordinate_projections():
    counts = dict(DELIVERY=160, RECOVERY=112, LOST=48)
    row = KERNEL[core.D]
    # Each candidate coordinate is attained by a point in the full @720 event.
    for cat in counts:
        rest = sum(value for name, value in counts.items() if name != cat)
        projected = {name: row[cat] if name == cat else (1-row[cat])*F(value, rest)
                     for name, value in counts.items()}
        assert joint.membership({'D': counts}, {'D': projected}, 720)['exact_inside']
    constraints = {op: [] for op in joint.OPERATORS}
    constraints[core.D] = [dict(counts=counts, threshold=720, event='A/source_pool'),
                          dict(counts=counts, threshold=8640, event='member/1')]
    result = core.classify(empty_counts(), constraints, CASE, mle())
    assert result['all_query_inside'] and not result['all_execution_inside']
    assert result['status'] == 'paid_constraints_reject_candidate'
    records = result['execution_regions']
    assert [record['threshold'] for record in records] == [720, 8640]
    assert [record['position'] for record in records] == [0, 1]
    assert not records[0]['membership']['exact_inside'] and records[1]['membership']['exact_inside']
    assert records[0]['event'] == 'A/source_pool' and records[0]['counts'] == counts


def test_canonical_exclusion_remains_unknown_without_claiming_null_emptiness():
    counts = {core.S: dict(DELIVERY=0, LOST=100),
              core.D: dict(DELIVERY=100, RECOVERY=0, LOST=0),
              core.R: dict(DELIVERY=100, LOST=0)}
    result = core.classify(counts, {op: [] for op in joint.OPERATORS}, CASE, mle())
    assert not result['canonical_inside'] and result['status'] == 'unknown'
    assert 'certified' not in result and 'query_ready' not in result
