from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from math import log

import pytest

from acfqp.science import goal_joint_region_v244 as witness
from acfqp.science import query_directed_acquisition_v245 as core

S, D, R = core.OPERATORS
KERNEL = {S: dict(DELIVERY=F(9, 10), LOST=F(1, 10)),
          D: dict(DELIVERY=F(1, 2), LOST=F(1, 4), RECOVERY=F(1, 4)),
          R: dict(DELIVERY=F(1, 5), LOST=F(4, 5))}


def empty():
    return {op: dict.fromkeys(core.ALPHABETS[op], 0) for op in core.OPERATORS}


def plan(kernel=KERNEL):
    observed = {S: dict(DELIVERY=497, LOST=503),
                D: dict(DELIVERY=500, LOST=250, RECOVERY=250),
                R: dict(DELIVERY=900, LOST=100)}
    comparison = dict(query='goal', chosen='SHORT', other='DETOUR_RETRY', certified=False,
                      witness_kind='bad_null_mle', bad_null_kernel=deepcopy(kernel))
    certificates = {
        'goal': dict(policy='SHORT', regret_upper=F(20), certified=False),
        'risk': dict(policy='DETOUR_RETURN', regret_upper=F(1, 20), certified=True),
        'reward': dict(policy='WAIT', regret_upper=F(0), certified=True)}
    return dict(utility_lower=F(2), goal_impossible=False, query_ready=False,
        case=dict(operating='low', retry_cost='17/20'), evidence_counts=observed,
        effective_n={op: sum(row.values()) for op, row in observed.items()},
        posterior={op: {cat: F(value, sum(row.values())) for cat, value in row.items()}
                   for op, row in observed.items()},
        envelopes={op: dict(bounds={cat: [F(0), F(1)] for cat in core.ALPHABETS[op]})
                   for op in core.OPERATORS},
        query_certificates=certificates,
        query_gap_bounds={query: {policy: F(query == 'goal' and policy != 'SHORT')
            for policy in core.original.POLICIES} for query in certificates},
        query_evidence=dict(queries={'goal': dict(policy='SHORT', comparisons=[comparison])}))


def test_retained_bad_kernel_targets_retry_with_observed_counts_and_no_new_proof(monkeypatch):
    member, active, work = empty(), plan(), Counter()
    before = deepcopy((member, active))
    monkeypatch.setattr(witness.joint, 'membership', lambda *args: pytest.fail('new membership'))
    result = core.choose(member, active, 0, work)
    assert result['operator'] == R and result['query_directed_reason'] == 'active'
    candidate = result['query_directed_candidate']
    assert candidate['gap'] == F(50001, 10**6)
    assert candidate['kernel'][D] == KERNEL[D] and candidate['kernel'][R] == KERNEL[R]
    expected = 16*(.9*log(.9/.2)+.1*log(.1/.8))
    assert result['query_directed_scores'][R] == pytest.approx(expected)
    assert result['query_directed_scores'][D] == 0
    assert (member, active) == before
    assert work == dict(query_directed_reconstructions=1,
                        query_directed_row_kl_evaluations=3, query_directed_choices=1)


def test_empirical_counts_drive_scores_even_when_posterior_disagrees():
    active = plan()
    active['posterior'][R] = deepcopy(KERNEL[R])
    result = core.choose(empty(), active, 0, Counter())
    assert result['operator'] == R and result['query_directed_scores'][R] > 0


@pytest.mark.parametrize('outside', ('execution_unresolved', 'different_goal', 'retry_certified'))
def test_outside_narrow_route_is_exact_original_choice(outside):
    active = plan()
    if outside == 'execution_unresolved':
        active['utility_lower'] = F(1)
    elif outside == 'different_goal':
        active['query_evidence']['queries']['goal']['policy'] = 'DETOUR_RETURN'
    else:
        active['query_evidence']['queries']['goal']['comparisons'][0]['certified'] = True
    actual_work, old_work = Counter(), Counter()
    assert core.choose(empty(), active, 0, actual_work) == core.original.choose(empty(), active, 0, old_work)
    assert actual_work == old_work


def test_stopping_performs_no_reconstruction_or_acquisition(monkeypatch):
    active, work = plan(), Counter()
    monkeypatch.setattr(witness, 'reconstruct', lambda *args: pytest.fail('reconstruction after stop'))
    assert core.choose(empty(), active, 384, work) is None
    active['query_ready'] = True
    assert core.choose(empty(), active, 0, work) is None
    assert not work


def test_unavailable_repair_preserves_original_fallback_choice():
    kernel = deepcopy(KERNEL)
    kernel[D] = dict(DELIVERY=F(0), LOST=F(1), RECOVERY=F(0))
    active = plan(kernel)
    expected = core.original.choose(empty(), active, 0, Counter())
    result = core.choose(empty(), active, 0, Counter())
    assert result['query_directed_reason'] == 'candidate_unavailable'
    assert result['query_directed_candidate']['reason'] == 'short_delivery_outside_simplex'
    assert result['query_directed_scores'] is None
    assert {key: result[key] for key in expected} == expected


def test_positive_empirical_count_at_candidate_boundary_falls_back_without_smoothing():
    kernel = deepcopy(KERNEL)
    kernel[R] = dict(DELIVERY=F(0), LOST=F(1))
    active = plan(kernel)
    expected = core.original.choose(empty(), active, 0, Counter())
    result = core.choose(empty(), active, 0, Counter())
    assert result['query_directed_reason'] == 'positive_count_boundary_zero'
    assert result['query_directed_candidate']['kernel'][R]['DELIVERY'] == 0
    assert result['query_directed_scores'] is None
    assert {key: result[key] for key in expected} == expected


def test_exact_equal_scores_keep_member_count_then_original_operator_order():
    kernel = deepcopy(KERNEL)
    kernel[D] = dict(DELIVERY=F(2462501, 4000000),
                     LOST=F(537499, 4000000), RECOVERY=F(1, 4))
    kernel[R] = dict(DELIVERY=F(3, 4), LOST=F(1, 4))
    active, member = plan(kernel), empty()
    active['evidence_counts'] = {S: dict(DELIVERY=500, LOST=500),
        D: dict(DELIVERY=616, LOST=134, RECOVERY=250), R: dict(DELIVERY=500, LOST=500)}
    result = core.choose(member, active, 0, Counter())
    assert result['query_directed_candidate']['kernel'][S]['DELIVERY'] == F(3, 4)
    assert result['query_directed_scores'][S] == result['query_directed_scores'][R]
    assert result['operator'] == S
    member[S]['DELIVERY'] = 16
    assert core.choose(member, active, 16, Counter())['operator'] == R


def test_zero_discrimination_keeps_original_allocation():
    kernel = {S: dict(DELIVERY=F(1, 2), LOST=F(1, 2)),
              D: dict(DELIVERY=F(999, 2000), LOST=F(999, 2000), RECOVERY=F(1, 1000)),
              R: dict(DELIVERY=F(2851, 4000), LOST=F(1149, 4000))}
    active = plan(kernel)
    active['evidence_counts'] = {S: dict(DELIVERY=500, LOST=500),
        D: dict(DELIVERY=999, LOST=999, RECOVERY=2), R: dict(DELIVERY=2851, LOST=1149)}
    expected = core.original.choose(empty(), active, 0, Counter())
    result = core.choose(empty(), active, 0, Counter())
    assert result['query_directed_candidate']['kernel'] == kernel
    assert result['query_directed_reason'] == 'zero_discrimination'
    assert {key: result[key] for key in expected} == expected
