"""Known-type acquisition from unresolved action-gap row uncertainty.

The score uses observed pooled counts and current confidence row projections.
It selects an operator without hypothetical outcomes or new planning calls.
"""
from fractions import Fraction as F
from math import sqrt

from . import latent_mechanisms_v213 as route
from .scoped_queries_v228 import POLICIES, WEIGHTS, THRESHOLD, row_vertices, utility

OPERATORS, ALPHABETS = route.OPERATORS, route.ALPHABETS
BATCH, TARGET_CAP = 16, 384


def _add(work, key, amount=1):
    work[key] = work.get(key, 0) + amount


def deficits(plan):
    """Track every unresolved query rather than just their current maximum."""
    result = {query: max(F(0), row['regret_upper']-THRESHOLD)
              for query, row in plan['query_certificates'].items()}
    result['execution'] = (F(0) if plan['goal_impossible']
                           else max(F(0), F(2)-plan['utility_lower']))
    return result


def _ready(plan):
    return (plan['utility_lower'] >= 2 or plan['goal_impossible']) and plan['query_ready']


def _influence(plan, work):
    """Measured row uncertainty in the currently blocking policy comparisons.

    Other rows stay at the observed pooled posterior.  This is an acquisition
    cue, not a confidence certificate or a law of future observations.
    """
    scores, execution = dict.fromkeys(OPERATORS, F(0)), {}
    values = {}
    for operator in OPERATORS:
        values[operator] = []
        for vertex in row_vertices(plan['envelopes'][operator]['bounds']):
            kernel = dict(plan['posterior'])
            kernel[operator] = vertex
            values[operator].append(route.vectors(plan['case'], kernel))
            _add(work, 'oracle_gap_influence_kernel_evaluations')

    for query, row in plan['query_certificates'].items():
        if row['certified']:
            continue
        selected, weights = row['policy'], WEIGHTS[query]
        blockers = [policy for policy in POLICIES if policy != selected
                    and plan['query_gap_bounds'][query][policy] > THRESHOLD]
        for operator in OPERATORS:
            for other in blockers:
                gaps = [utility(vectors[other], weights)-utility(vectors[selected], weights)
                        for vectors in values[operator]]
                scores[operator] += max(gaps)-min(gaps)
                _add(work, 'oracle_gap_blocking_comparison_spans')

    weight = (F(0) if plan['goal_impossible'] else
              min(F(1), max(F(0), F(2)-plan['utility_lower'])/2))
    for operator in OPERATORS:
        spans = []
        for policy in POLICIES:
            if policy == 'WAIT':
                continue
            goals = [utility(vectors[policy], WEIGHTS['goal']) for vectors in values[operator]]
            risks = [vectors[policy][1] for vectors in values[operator]]
            spans.append(max(goals)-min(goals)+4*(max(risks)-min(risks)))
        execution[operator] = weight*max(spans)
    return scores, execution


def choose(member, plan, spent, work):
    """Choose the next paid batch without evaluating hypothetical evidence.

    Required plan fields are the normal stop fields, ``posterior``, ``case``,
    ``envelopes``, ``effective_n``, and ``query_gap_bounds[query][other_policy]``.
    The latter identifies comparisons above the fixed query threshold.

    Each score is the sum of unresolved query comparison spans plus an
    execution contribution, times ``1-sqrt(n/(n+16))`` at the observed pooled
    row count.  This contraction is a deterministic acquisition heuristic;
    actual confidence certification still uses only observed outcomes.
    Ties prefer the least sampled member row, then the frozen operator order.
    """
    if spent >= TARGET_CAP or _ready(plan):
        return None
    query_influence, execution_influence = _influence(plan, work)
    contraction = {op: 1-sqrt(plan['effective_n'][op]/(plan['effective_n'][op]+BATCH))
                   for op in OPERATORS}
    scores = {op: float(query_influence[op]+execution_influence[op])*contraction[op]
              for op in OPERATORS}
    operator = min(OPERATORS, key=lambda op: (
        -scores[op], sum(member[op].values()), OPERATORS.index(op)))
    _add(work, 'oracle_gap_direct_choices')
    return dict(operator=operator, reason='known_type_action_gap',
                scores=scores, query_influence=query_influence,
                execution_influence=execution_influence, contraction=contraction,
                effective_n=dict(plan['effective_n']), initial_deficits=deficits(plan))
