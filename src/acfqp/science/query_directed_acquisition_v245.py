"""Discriminate one retained bad kernel after execution is resolved.

Only a live uncertified goal SHORT-versus-RETRY comparison changes acquisition.
The V244 reconstruction supplies an acquisition cue, never a query certificate.
Every other acquisition and all stopping use the unchanged V231 rule.
"""
from fractions import Fraction as F
from math import log

from . import goal_joint_region_v244 as witness
from . import oracle_gap_acquisition_v231 as original

OPERATORS, ALPHABETS = original.OPERATORS, original.ALPHABETS
BATCH, TARGET_CAP = original.BATCH, original.TARGET_CAP


def _add(work, field):
    work[field] = work.get(field, 0)+1


def _fallback(member, plan, spent, work, candidate, reason):
    result = original.choose(member, plan, spent, work)
    _add(work, 'query_directed_fallback_choices')
    result.update(query_directed_candidate=candidate,
                  query_directed_scores=None, query_directed_reason=reason)
    return result


def choose(member, plan, spent, work):
    """Choose a batch using only the present paid counts and retained proof.

    Score = 16 * KL(empirical full row || fixed reconstructed bad-kernel row).
    Neither imagined outcomes nor row confidence membership are evaluated.
    Ties keep the original member-count and operator-order rule.
    """
    if spent >= TARGET_CAP or original._ready(plan):
        return None
    execution_resolved = plan['utility_lower'] >= 2 or plan['goal_impossible']
    goal = plan['query_evidence']['queries']['goal']
    if not execution_resolved or goal['policy'] != 'SHORT':
        return original.choose(member, plan, spent, work)
    comparison = next((row for row in goal['comparisons']
                       if row['other'] == 'DETOUR_RETRY' and not row['certified']), None)
    if comparison is None:
        return original.choose(member, plan, spent, work)

    candidate = witness.reconstruct(comparison, plan['case'])
    _add(work, 'query_directed_reconstructions')
    kernel = candidate['kernel']
    if kernel is None:
        return _fallback(member, plan, spent, work, candidate, 'candidate_unavailable')

    scores = {}
    for operator in OPERATORS:
        row = plan['evidence_counts'][operator]
        total = sum(row.values())
        terms = []
        for category in ALPHABETS[operator]:
            if row[category]:
                p = kernel[operator][category]
                if not p:
                    return _fallback(member, plan, spent, work, candidate,
                                     'positive_count_boundary_zero')
                q = F(row[category], total)
                terms.append(float(q)*log(float(q/p)))
        scores[operator] = BATCH*sum(terms)
        _add(work, 'query_directed_row_kl_evaluations')
    if not any(scores.values()):
        return _fallback(member, plan, spent, work, candidate, 'zero_discrimination')

    operator = min(OPERATORS, key=lambda op: (
        -scores[op], sum(member[op].values()), OPERATORS.index(op)))
    _add(work, 'query_directed_choices')
    return dict(operator=operator, reason='retained_goal_bad_kernel_discrimination',
                query_directed_reason='active', query_directed_candidate=candidate,
                query_directed_scores=scores,
                effective_n=dict(plan['effective_n']),
                initial_deficits=original.deficits(plan))
