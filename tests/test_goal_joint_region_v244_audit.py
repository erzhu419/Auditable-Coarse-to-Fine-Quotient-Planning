from copy import deepcopy
from fractions import Fraction as F

from scripts import audit_goal_joint_region_v244 as audit


def kernel(short=F(1, 2), delivery=F(1, 3), recovery=F(1, 3), retry=F(1, 2)):
    return {audit.S: dict(DELIVERY=short, LOST=1 - short),
            audit.D: dict(DELIVERY=delivery, LOST=1 - delivery - recovery, RECOVERY=recovery),
            audit.R: dict(DELIVERY=retry, LOST=1 - retry)}


def test_three_category_jeffreys_normalizer_uses_full_dimension():
    # Substituting the binary prior would change full-row membership.
    assert audit.normalizer((1, 1, 0)) == F(1, 15)
    assert audit.normalizer((1, 1, 1)) == F(1, 105)
    assert audit.normalizer((1, 1)) == F(1, 8)
    decision, ratio = audit.membership({'D': dict(DELIVERY=1, LOST=1, RECOVERY=0)},
                                      {'D': dict(DELIVERY=F(1, 2), LOST=F(1, 2), RECOVERY=0)}, 1)
    assert ratio == F(4, 15) and decision['exact_inside']


def test_original_member_threshold_is_8640_and_every_row_is_tested():
    # This paid member lies between the 720 and 8640 thresholds.
    member, pool, sources = audit.empty(), audit.empty(), {'a': [audit.empty() for _ in range(3)]}
    member[audit.S]['DELIVERY'] = 15
    constraints = audit.original_constraints(0, 54, 0, sources, pool, member)
    tested = audit.execution_memberships(constraints, kernel())
    assert len(tested) == 9
    event, ratio = tested[2]
    assert 720 < ratio < 8640
    assert event['threshold'] == 8640 and event['membership']['exact_inside']
    changed = deepcopy(constraints)
    changed[audit.S][2]['threshold'] = 720
    assert not audit.execution_memberships(changed, kernel())[2][0]['membership']['exact_inside']


def test_recovery_repairs_gap_at_retained_retry_mle_not_relaxed_endpoint():
    counts = {audit.S: dict(DELIVERY=4, LOST=6),
              audit.D: dict(DELIVERY=3, LOST=4, RECOVERY=3),
              audit.R: dict(DELIVERY=1, LOST=3)}
    case = dict(operating='low', retry_cost='1/10')
    leaf = dict(log_bad_likelihood_upper='-10', multiplier=0, gap_endpoint='1/2',
        gap_coefficients=audit.restored_coefficients(case, F(1, 2)), retry_interval=['0', '1/2'],
        row_witnesses={operator: dict(kind='simplex_likelihood_dual', nu=10)
                       for operator in (audit.S, audit.D)},
        retry_likelihood=dict(probability='1/4'))
    certificate = dict(witness_kind='global_likelihood_dual', embedded_counts=counts,
                       leaves=[leaf, deepcopy(leaf)])
    result = audit.reconstruct_candidate(certificate, case)
    assert result['leaf_index'] == 0  # exact maximum ties retain the first leaf
    assert result['kernel'][audit.R]['DELIVERY'] == F(1, 4)
    assert result['gap'] == audit.STRICT_GAP == audit.goal_gap(case, result['kernel'])
    relaxed = deepcopy(result['kernel'])
    relaxed[audit.R] = dict(DELIVERY=F(1, 2), LOST=F(1, 2))
    assert audit.goal_gap(case, relaxed) != result['gap']


def test_excluded_candidate_is_unknown_or_rejected_without_a_certificate():
    candidate = dict(kernel=kernel(), gap=audit.STRICT_GAP)
    assert audit.status(candidate, False, False, True) == 'unknown'
    assert audit.status(candidate, True, False, True) == 'paid_constraints_reject_candidate'
    assert audit.status(candidate, True, True, True) == 'full_region_bad_witness'


def test_native_snapshot_excludes_later_and_other_arm_observations():
    sources = {context: [audit.empty() for _ in range(3)] for context in ('a', 'b')}
    sources['a'][0][audit.S]['DELIVERY'] = 10
    sources['b'][0][audit.S]['DELIVERY'] = 100

    def record(index, before):
        member = audit.empty()
        member[audit.S]['DELIVERY'] = 16
        after = deepcopy(before)
        after[audit.S]['DELIVERY'] += 16
        return dict(life=0, index=index, identity=0, arm='ONE_WAY',
                    case=dict(context='A', stage='A_RETURN'), pooled_before=deepcopy(before),
                    pooled_after=after, member=member, spent=16,
                    batches=[dict(operator=audit.S, increments=member[audit.S],
                                  draw_start=0, draw_end=16, spent=16)])

    first = record(54, sources['a'][0])
    second = record(55, first['pooled_after'])
    passed = []
    snapshots = list(audit.replay_native_pools(0, sources, dict(identities=[0] * 78),
        [first, dict(arm='TWO_WAY', batches=[dict(operator=audit.S,
             increments=dict(DELIVERY=10000, LOST=0))]), second],
        lambda name, condition: passed.append(condition)))
    assert all(passed)
    assert snapshots[0]['evidence_counts'][audit.S]['DELIVERY'] == 26
    assert snapshots[1]['evidence_counts'][audit.S]['DELIVERY'] == 42
    assert snapshots[0]['joint_constraints'][audit.S][1]['counts']['DELIVERY'] == 26
    assert sources['a'][0][audit.S]['DELIVERY'] == 10
