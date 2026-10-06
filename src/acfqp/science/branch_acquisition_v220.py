"""Integrate every integer next-batch outcome without changing real certificates."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import product
from math import factorial, fsum, prod

from . import fixed_source_acquisition_v219 as prior
from . import latent_mechanisms_v213 as evidence
from . import query_sufficient_v214 as query_core

OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
empty, vectors, queries = prior.empty, prior.vectors, prior.queries
BATCH = 16


def _outcomes(size):
    if size == 2:
        rows = [(a, BATCH-a) for a in range(BATCH+1)]
    else:
        rows = [(a, b, BATCH-a-b) for a in range(BATCH+1)
                for b in range(BATCH-a+1)]
    return tuple((row, factorial(BATCH)//prod(factorial(k) for k in row))
                 for row in rows)


OUTCOMES = {op: _outcomes(len(ALPHABETS[op])) for op in OPERATORS}


def _record(work, counted):
    if work is not None:
        for key, value in counted.items():
            work['forecast_'+key] += value


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    return prior.make_plan(member, anchors, case, 'MEAN' if arm == 'BRANCH' else arm,
                           work, identity, force_member)


def _boxes(counts, cache, counted):
    result = {}
    for op in OPERATORS:
        row, bounds = counts[op], {}
        n = sum(row.values())
        for cat in ALPHABETS[op]:
            key = (row[cat], n)
            if key in cache['intervals']:
                counted['interval_cache_hits'] += 1
            else:
                cache['intervals'][key] = evidence.interval(row[cat], n, counted)
            bounds[cat] = list(cache['intervals'][key])
        result[op] = dict(n=n, counts=dict(row), bounds=bounds)
    return result


def prepare(anchors, work):
    cache = dict(source_boxes=[], intervals={})
    counted = Counter()
    cache['source_boxes'] = [_boxes(anchor, cache, counted) for anchor in anchors]
    counted['source_box_records'] += len(anchors)
    _record(work, counted)
    return cache


def forecast_plan(member, anchors, case, work, cache):
    """Full MEAN planning semantics, with only source boxes and intervals cached."""
    counted = Counter()
    raw = _boxes(member, cache, counted)
    blocks, candidates = {}, []
    for i, source in enumerate(cache['source_boxes']):
        block, ok = deepcopy(raw), True
        for op in OPERATORS:
            for cat in ALPHABETS[op]:
                a, b = raw[op]['bounds'][cat], source[op]['bounds'][cat]
                pair = [max(a[0], b[0]), min(a[1], b[1])]
                if pair[0] > pair[1]:
                    ok = False
                block[op]['bounds'][cat] = pair
        if ok:
            candidates.append(i)
            blocks[i] = block
    if candidates:
        risks, goals, means = {}, {}, []
        for i, block in blocks.items():
            r = evidence.robust.risk_bounds(block, counted)
            g = evidence.robust.goals_lower(block, case, counted)
            for policy in r:
                risks[policy] = max(risks.get(policy, F(0)), r[policy])
                goals[policy] = min(goals.get(policy, g[policy]), g[policy])
            combined = {op: {cat: member[op][cat]+anchors[i][op][cat]
                             for cat in ALPHABETS[op]} for op in OPERATORS}
            means.append(evidence.posterior(combined))
        p = {op: {cat: sum(mean[op][cat] for mean in means)/len(means)
                  for cat in ALPHABETS[op]} for op in OPERATORS}
        envelope = deepcopy(raw)
        for op in OPERATORS:
            for cat in ALPHABETS[op]:
                envelope[op]['bounds'][cat] = [
                    min(block[op]['bounds'][cat][0] for block in blocks.values()),
                    max(block[op]['bounds'][cat][1] for block in blocks.values())]
        mode = 'library'
    else:
        envelope, mode = raw, 'member'
        risks = evidence.robust.risk_bounds(raw, counted)
        goals = evidence.robust.goals_lower(raw, case, counted)
        p = evidence.posterior(member)
    pure = vectors(case, p)
    counted['planning_calls'] += 1
    result = dict(**evidence.robust.solve(pure, risks, goals, counted),
                  envelopes=envelope, risks=risks, goals_lower=goals,
                  pure_vectors=pure, candidates=candidates,
                  candidate_envelopes=blocks, mode=mode)
    result['query_proxy'] = query_core.query_proxy(member, anchors, case, result, counted)
    result['query_ready'] = (mode == 'library' and result['utility_lower'] >= 2
                             and result['query_proxy'] is not None
                             and result['query_proxy'] <= query_core.THRESHOLD)
    _record(work, counted)
    return result


def dm_distribution(row, op, work=None):
    """Exact Dirichlet-multinomial law, alpha=count+1/2, for all 16-draw rows."""
    alpha2 = [2*row[cat]+1 for cat in ALPHABETS[op]]
    rising = []
    for value in alpha2:
        sequence = [1]
        for j in range(BATCH):
            sequence.append(sequence[-1]*(value+2*j))
        rising.append(sequence)
    denominator = prod(sum(alpha2)+2*j for j in range(BATCH))
    result = [(counts, F(coefficient*prod(rising[j][k] for j, k in enumerate(counts)),
                         denominator)) for counts, coefficient in OUTCOMES[op]]
    _record(work, dict(dm_components=1, dm_probability_constructions=len(result)))
    return result


def predictive_distribution(member, anchors, plan, op, work=None):
    if plan['candidates']:
        rows = [{cat: member[op][cat]+anchors[i][op][cat] for cat in ALPHABETS[op]}
                for i in plan['candidates']]
    else:
        rows = [member[op]]
    laws = [dm_distribution(row, op, work) for row in rows]
    return [(dict(zip(ALPHABETS[op], counts)),
             sum(law[index][1] for law in laws)/len(laws))
            for index, (counts, _) in enumerate(OUTCOMES[op])]


def regret_bound(case, work=None):
    """Full-kernel mean-query range over the 2x3x2 simplex vertices."""
    maximum = F(0)
    for categories in product(*(ALPHABETS[op] for op in OPERATORS)):
        p = {op: {cat: F(cat == category) for cat in ALPHABETS[op]}
             for op, category in zip(OPERATORS, categories)}
        pure, ranges = vectors(case, p), []
        for weights in query_core.WEIGHTS.values():
            values = [v[0]*weights[0]-v[1]*weights[1]+v[2]*weights[2]
                      for v in pure.values()]
            ranges.append(max(values)-min(values))
        maximum = max(maximum, sum(ranges)/len(ranges))
    _record(work, dict(query_bound_vertices=12, query_bound_policy_values=144))
    return maximum


def forecast_loss(plan, unavailable_bound):
    proxy = unavailable_bound if plan['query_proxy'] is None else plan['query_proxy']
    return max(F(0), F(2)-plan['utility_lower'])+max(F(0), proxy-F(1, 20))


def choose(member, anchors, case, arm, plan, spent, work, cache):
    if arm != 'BRANCH':
        return prior.choose(member, anchors, case, arm, plan, spent, work)
    if spent == 384 or plan['query_ready']:
        return None
    counts = {op: sum(member[op].values()) for op in OPERATORS}
    for op in OPERATORS:
        if not counts[op]:
            return dict(scope='TARGET', source_index=None, operator=op,
                        reason='target_pilot', counts=counts)
    bound, scores = regret_bound(case, work), {}
    for op in OPERATORS:
        loss_terms, ready_terms, unavailable_terms, mass = [], [], [], F(0)
        branches = predictive_distribution(member, anchors, plan, op, work)
        for increments, probability in branches:
            temporary = {key: dict(row) for key, row in member.items()}
            for cat, amount in increments.items():
                temporary[op][cat] += amount
            predicted = forecast_plan(temporary, anchors, case, work, cache)
            mass += probability
            weight = float(probability)
            loss_terms.append(weight*float(forecast_loss(predicted, bound)))
            ready_terms.append(weight*predicted['query_ready'])
            unavailable_terms.append(weight*(predicted['query_proxy'] is None))
        if mass != 1:
            raise ArithmeticError('The complete predictive batch law must have probability one.')
        scores[op] = dict(expected_loss=fsum(loss_terms),
                          ready_probability=fsum(ready_terms),
                          unavailable_probability=fsum(unavailable_terms),
                          probability_mass=mass, branches=len(branches))
    selected = min(OPERATORS, key=lambda op: (scores[op]['expected_loss'], counts[op],
                                            OPERATORS.index(op)))
    return dict(scope='TARGET', source_index=None, operator=selected,
                reason='branch_integral', scores=scores)
