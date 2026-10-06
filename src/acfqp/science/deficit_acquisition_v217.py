"""Observe current query or certificate deficits while retaining identity ambiguity."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from . import source_stopping_v216 as prior
from . import latent_mechanisms_v213 as evidence

OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
empty, vectors, queries = prior.empty, prior.vectors, prior.queries


def base_arm(arm):
    return 'EARLY' if arm in ('DEFICIT', 'IDENTITY') else arm


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    return prior.make_plan(member, anchors, case, base_arm(arm), work, identity, force_member)


def candidate_means(member, anchors, plan):
    if not plan['candidates']:
        return {None: evidence.posterior(member)}
    return {i: evidence.posterior({op: {
        cat: member[op][cat]+anchors[i][op][cat] for cat in ALPHABETS[op]}
        for op in OPERATORS}) for i in plan['candidates']}


def query_scores(member, anchors, case, means, work):
    probabilities = {op: {cat: sum(p[op][cat] for p in means.values())/len(means)
                          for cat in ALPHABETS[op]} for op in OPERATORS}
    result = {}
    for op in OPERATORS:
        counts = deepcopy(member)
        for cat in ALPHABETS[op]:
            counts[op][cat] += 16*probabilities[op][cat]
        forecast = make_plan(counts, anchors, case, 'DEFICIT', work)
        result[op] = dict(query_proxy=forecast['query_proxy'], utility_lower=forecast['utility_lower'])
    return result


def certificate_scores(case, plan, means, work):
    blocks = plan['candidate_envelopes'] if plan['candidates'] else {None: plan['envelopes']}
    result = {}
    for op in OPERATORS:
        risks, goals = {}, {}
        for i, block in blocks.items():
            forecast = deepcopy(block)
            forecast[op]['bounds'] = {cat: [p,p] for cat,p in means[i][op].items()}
            upper = evidence.robust.risk_bounds(forecast, work)
            lower = evidence.robust.goals_lower(forecast, case, work)
            for policy in upper:
                risks[policy] = max(risks.get(policy,F(0)), upper[policy])
                goals[policy] = min(goals.get(policy,lower[policy]), lower[policy])
        result[op] = evidence.robust.solve(plan['pure_vectors'], risks, goals, work)['utility_lower']
    return result


def choose(member, anchors, case, arm, plan, spent, work, source=False):
    if source or arm != 'DEFICIT':
        return prior.choose(member, anchors, case, base_arm(arm), plan, spent, work, source)
    if spent == 384 or plan['query_ready']:
        return None
    counts = {op: sum(member[op].values()) for op in OPERATORS}
    for op in OPERATORS:
        if counts[op] == 0:
            return dict(operator=op, reason='target_pilot', counts=counts)
    means = candidate_means(member, anchors, plan)
    forecast_work = Counter()
    if plan['query_proxy'] is not None and plan['query_proxy'] > F(1,20):
        scores = query_scores(member, anchors, case, means, forecast_work)
        key = lambda op: (scores[op]['query_proxy'] is None,
                          scores[op]['query_proxy'] if scores[op]['query_proxy'] is not None else F(0),
                          counts[op], OPERATORS.index(op))
        reason = 'query_deficit'
    else:
        scores = certificate_scores(case, plan, means, forecast_work)
        key = lambda op: (-scores[op], counts[op], OPERATORS.index(op))
        reason = 'certificate_deficit'
    work.update({'forecast_'+key: value for key,value in forecast_work.items()})
    return dict(operator=min(OPERATORS,key=key), reason=reason, scores=scores, counts=counts)
