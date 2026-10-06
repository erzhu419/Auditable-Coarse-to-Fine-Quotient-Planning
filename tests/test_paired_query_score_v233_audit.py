"""Concrete score, predictable-bet and false-proof failures caught by V233."""
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import paired_query_score_v233 as core
from scripts import audit_paired_query_score_v233 as audit


def test_retry_score_uses_matching_recovery_row_and_required_prefix_only():
    queues = {audit.S: ['DELIVERY', 'LOST'],
              audit.DETOUR: ['RECOVERY', 'DELIVERY'],
              audit.R: ['DELIVERY', 'LOST']}
    needed, scores, _, _ = audit.scores_from_queues(
        queues, 'goal', 'DETOUR_RETURN', 'DETOUR_RETRY', '17/20')
    assert needed == (audit.DETOUR, audit.R)
    assert scores == [F(63, 20), F(0)]
    changed = deepcopy(queues)
    changed[audit.R] = ['LOST', 'DELIVERY']
    assert audit.scores_from_queues(changed, 'goal', 'DETOUR_RETURN', 'DETOUR_RETRY', '17/20')[1] == [F(-17, 20), F(0)]
    assert audit.scores_from_queues(queues, 'risk', 'SHORT', 'DETOUR_RETURN', '17/20') == audit.scores_from_queues(
        changed, 'risk', 'SHORT', 'DETOUR_RETURN', '19/20')


def test_bets_depend_only_on_preceding_scores_and_match_independent_formula():
    spec = core.score_spec('risk', 'SHORT', 'DETOUR_RETURN')
    scores = [F(-8), F(0), F(8), F(-4), F(0)]
    expected = audit.predictable_bets(scores, spec.lower, spec.upper)
    actual = [F(*pair) for pair in core.predictable_bets(spec, [int(score*20) for score in scores])]
    assert actual == expected
    future_changed = scores[:2]+[F(-8), F(8), F(4)]
    changed = audit.predictable_bets(future_changed, spec.lower, spec.upper)
    assert changed[:3] == expected[:3]
    assert all(F(0) <= bet <= F(1, 16) for bet in expected)


def test_independent_proof_audit_accepts_real_bounds_and_rejects_inflation():
    queues = {audit.S: ['DELIVERY']*32,
              audit.DETOUR: ['DELIVERY']*24+['LOST']*8,
              audit.R: ['DELIVERY']*32}
    case = dict(operating='low', retry_cost='17/20')
    stats = core.stream_statistics(queues, 'risk', 'SHORT', 'DETOUR_RETURN', case['retry_cost'])
    saved, statistics = core.evaluate(stats, case), core.statistics_record(stats)
    kernel = {audit.S: {'DELIVERY': F(9, 10), 'LOST': F(1, 10)},
              audit.DETOUR: {'DELIVERY': F(4, 5), 'LOST': F(1, 10), 'RECOVERY': F(1, 10)},
              audit.R: {'DELIVERY': F(1, 2), 'LOST': F(1, 2)}}
    checks = []
    audit.audit_comparison(queues, case, 'risk', 'SHORT', 'DETOUR_RETURN', saved, statistics,
                           kernel, lambda key, valid: checks.append((key, valid)))
    assert all(valid for _, valid in checks)
    inflated = dict(saved, log_e_lower='1000')
    checks = []
    audit.audit_comparison(queues, case, 'risk', 'SHORT', 'DETOUR_RETURN', inflated, statistics,
                           kernel, lambda key, valid: checks.append((key, valid)))
    assert ('outward_lower_e_log', False) in checks


def test_operating_costs_shift_supported_null_without_requiring_extra_rows():
    queues = {operator: [] for operator in audit.OPERATORS}
    stats = core.stream_statistics(queues, 'goal', 'DETOUR_RETURN', 'WAIT')
    saved = core.evaluate(stats, dict(operating='high', retry_cost='19/20'))
    assert stats.spec.upper == 0 and saved['theta'] == F(-1, 50)
    assert saved['kind'] == 'bounded_mean_bet' and not saved['certified']
    assert len(audit.required('SHORT', 'WAIT')) == 1
    reverse = core.stream_statistics(queues, 'risk', 'WAIT', 'DETOUR_RETURN')
    assert core.evaluate(reverse, dict(operating='low', retry_cost='17/20'))['theta'] == F(1, 10)
