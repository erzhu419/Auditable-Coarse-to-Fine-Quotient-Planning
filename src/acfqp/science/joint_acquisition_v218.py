"""Compare finite paid source revisits with current-member evidence acquisition."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from . import source_stopping_v216 as prior
from . import latent_mechanisms_v213 as evidence

OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
empty, vectors, queries = prior.empty, prior.vectors, prior.queries


def base_arm(arm):
    return 'EARLY' if arm in ('JOINT', 'MEMBER') else arm


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    return prior.make_plan(member, anchors, case, base_arm(arm), work, identity, force_member)


def deficit(plan):
    certificate = max(F(0), F(2)-plan['utility_lower'])
    proxy = plan['query_proxy']
    return certificate if proxy is None else certificate+max(F(0), proxy-F(1,20))


def member_mean(member, anchors, plan):
    if not plan['candidates']:
        return evidence.posterior(member)
    means = [evidence.posterior({op: {
        cat: member[op][cat]+anchors[i][op][cat] for cat in ALPHABETS[op]}
        for op in OPERATORS}) for i in plan['candidates']]
    return {op: {cat: sum(p[op][cat] for p in means)/len(means)
                 for cat in ALPHABETS[op]} for op in OPERATORS}


def forecasts(member, anchors, case, arm, plan, member_spent, work):
    actions = []
    if member_spent < 384:
        mean = member_mean(member, anchors, plan)
        actions += [('TARGET', None, member, mean, op) for op in OPERATORS]
    if arm == 'JOINT':
        for i, anchor in enumerate(anchors):
            if sum(sum(row.values()) for row in anchor.values()) < 1152:
                mean = evidence.posterior(anchor)
                actions += [('SOURCE', i, anchor, mean, op) for op in OPERATORS]
    result = []
    for scope, index, counts, mean, op in actions:
        temporary_member, temporary_sources = deepcopy(member), deepcopy(anchors)
        row = temporary_member[op] if scope == 'TARGET' else temporary_sources[index][op]
        for cat in ALPHABETS[op]:
            row[cat] += 16*mean[op][cat]
        predicted = make_plan(temporary_member, temporary_sources, case, arm, work)
        result.append(dict(scope=scope, source_index=index, operator=op,
            operator_n=sum(counts[op].values()), query_proxy=predicted['query_proxy'],
            utility_lower=predicted['utility_lower'], deficit=deficit(predicted)))
    return result


def choose(member, anchors, case, arm, plan, member_spent, work,
           source=False, source_index=None):
    if source or arm not in ('JOINT', 'MEMBER'):
        choice = prior.choose(member, anchors, case, base_arm(arm), plan,
                              member_spent, work, source)
        return None if choice is None else dict(choice,
            scope='SOURCE' if source else 'TARGET', source_index=source_index if source else None)
    if plan['query_ready']:
        return None
    counts = {op: sum(member[op].values()) for op in OPERATORS}
    if member_spent < 384:
        for op in OPERATORS:
            if not counts[op]:
                return dict(scope='TARGET', source_index=None, operator=op,
                            reason='target_pilot', counts=counts)
    forecast_work = Counter()
    scores = forecasts(member, anchors, case, arm, plan, member_spent, forecast_work)
    work.update({'forecast_'+key: value for key,value in forecast_work.items()})
    if not scores:
        return None
    best = min(scores, key=lambda s: (s['query_proxy'] is None, s['deficit'],
        s['operator_n'], s['scope'] != 'SOURCE',
        s['source_index'] if s['source_index'] is not None else -1,
        OPERATORS.index(s['operator'])))
    return dict(scope=best['scope'], source_index=best['source_index'],
                operator=best['operator'], reason='finite_joint_deficit', scores=scores)
