"""Cumulative kernel confidence with all feasible latent assignments retained."""
from copy import deepcopy
from fractions import Fraction as F
from itertools import product
from math import ceil, floor, log, prod

from . import latent_mechanisms_v213 as evidence
from . import query_sufficient_v214 as query_core

OPERATORS, ALPHABETS = evidence.OPERATORS, evidence.ALPHABETS
RAW_BETA = log(2 * 5544 / .025)
POOL_BETA = log(2 * 13608 / .025)
empty, vectors, queries = evidence.empty, evidence.vectors, evidence.queries
_INTERVAL_CACHE = {}


def clear_cache():
    _INTERVAL_CACHE.clear()


def interval(k, n, work, beta=RAW_BETA):
    """Outward-rounded raw or pooled Bernoulli KL interval, with reuse counted."""
    work['interval_calls'] += 1
    key = (k, n, beta)
    if key in _INTERVAL_CACHE:
        work['interval_cache_hits'] += 1
        return _INTERVAL_CACHE[key]
    work['interval_computations'] += 1
    if not n:
        result = F(0), F(1)
    else:
        x = k / n
        if k:
            lo, hi = 0., x
            for _ in range(64):
                mid = (lo + hi) / 2
                if n * evidence.robust.confidence._kl(x, mid, work) > beta:
                    lo = mid
                else:
                    hi = mid
            lower = lo
        else:
            lower = 0.
        if k < n:
            lo, hi = x, 1.
            for _ in range(64):
                mid = (lo + hi) / 2
                if n * evidence.robust.confidence._kl(x, mid, work) > beta:
                    hi = mid
                else:
                    lo = mid
            upper = hi
        else:
            upper = 1.
        grid = evidence.robust.GRID
        result = F(floor(lower * grid), grid), F(ceil(upper * grid), grid)
    _INTERVAL_CACHE[key] = result
    return result


def boxes(counts, work, beta=RAW_BETA):
    return {op: dict(n=sum(counts[op].values()), counts=deepcopy(counts[op]),
                     bounds={cat: list(interval(counts[op][cat],
                                 sum(counts[op].values()), work, beta))
                             for cat in ALPHABETS[op]})
            for op in OPERATORS}


def _feasible(box):
    for op in OPERATORS:
        pairs = [box[op]['bounds'][cat] for cat in ALPHABETS[op]]
        if any(lo > hi for lo, hi in pairs):
            return False
        if sum(lo for lo, _ in pairs) > 1 or sum(hi for _, hi in pairs) < 1:
            return False
    return True


def _intersection(first, others):
    result = deepcopy(first)
    for other in others:
        for op in OPERATORS:
            for cat in ALPHABETS[op]:
                pair, new = result[op]['bounds'][cat], other[op]['bounds'][cat]
                result[op]['bounds'][cat] = [max(pair[0], new[0]), min(pair[1], new[1])]
    return _project_simplex(result) if _feasible(result) else None


def _project_simplex(box):
    """Exact coordinate projection of each interval box intersected with simplex."""
    for op in OPERATORS:
        original = deepcopy(box[op]['bounds'])
        for cat in ALPHABETS[op]:
            others = [other for other in ALPHABETS[op] if other != cat]
            lo, hi = original[cat]
            box[op]['bounds'][cat] = [
                max(lo, 1 - sum(original[other][1] for other in others)),
                min(hi, 1 - sum(original[other][0] for other in others))]
    return box


def raw_problem(anchors, members, work, raw_beta=RAW_BETA):
    source_boxes = [_project_simplex(boxes(anchor, work, raw_beta)) for anchor in anchors]
    member_boxes = [_project_simplex(boxes(member, work, raw_beta)) for member in members]
    masks = [[i for i, source in enumerate(source_boxes)
              if _intersection(source, [member]) is not None]
             for member in member_boxes]
    return dict(source_boxes=source_boxes, member_boxes=member_boxes, masks=masks)


def _no_feasible(members, **extra):
    return dict(bounds=[], masks=[[] for _ in members], no_feasible=True, **extra)


def _add(counts, other):
    for op in OPERATORS:
        for cat in ALPHABETS[op]:
            counts[op][cat] += other[op][cat]


def _mark(bounds, kind):
    for box in bounds:
        for op in OPERATORS:
            box[op]['kind'] = kind
    return bounds


def exact_union(problem, anchors, members, work, pool_beta=POOL_BETA):
    """Coordinate envelope of every fully feasible Cartesian assignment branch."""
    total = prod(len(mask) for mask in problem['masks'])
    work['exact_union_calls'] += 1
    union, support, feasible = None, [set() for _ in members], 0
    for assignment in product(*problem['masks']):
        work['exact_assignment_checks'] += 1
        pooled = deepcopy(anchors)
        assigned = [[] for _ in anchors]
        for j, index in enumerate(assignment):
            _add(pooled[index], members[j])
            assigned[index].append(problem['member_boxes'][j])
        branch = []
        for i, source in enumerate(problem['source_boxes']):
            block = _intersection(source, assigned[i] + [boxes(pooled[i], work, pool_beta)])
            if block is None:
                break
            branch.append(block)
        if len(branch) != len(anchors):
            continue
        feasible += 1
        work['exact_feasible_assignments'] += 1
        for j, index in enumerate(assignment):
            support[j].add(index)
        if union is None:
            union = deepcopy(branch)
        else:
            for i, block in enumerate(branch):
                for op in OPERATORS:
                    for cat in ALPHABETS[op]:
                        old, new = union[i][op]['bounds'][cat], block[op]['bounds'][cat]
                        union[i][op]['bounds'][cat] = [min(old[0], new[0]), max(old[1], new[1])]
    if union is None:
        return _no_feasible(members, assignments=total, feasible_assignments=0)
    return dict(bounds=_mark(union, 'exact_assignment_union'),
                masks=[sorted(mask) for mask in support], no_feasible=False,
                assignments=total, feasible_assignments=feasible)


def subset_extrema(base_k, base_n, optional, work):
    """For each optional-subset n retain exact minimum and maximum category k."""
    states = {base_n: (base_k, base_k)}
    for k, n in optional:
        updated = dict(states)
        work['subset_dp_state_visits'] += len(states)
        for old_n, (low, high) in states.items():
            new_n, pair = old_n + n, (low + k, high + k)
            if new_n in updated:
                previous = updated[new_n]
                pair = min(previous[0], pair[0]), max(previous[1], pair[1])
            updated[new_n] = pair
        states = updated
    return states


def _subset_endpoint(base_k, base_n, optional, work, pool_beta=POOL_BETA):
    states = subset_extrema(base_k, base_n, optional, work)
    lower, upper = F(1), F(0)
    for n, (low_k, high_k) in states.items():
        # At fixed n the two KL endpoints are monotone in k.
        lower = min(lower, interval(low_k, n, work, pool_beta)[0])
        upper = max(upper, interval(high_k, n, work, pool_beta)[1])
    return [lower, upper], len(states)


def outer_union(problem, anchors, members, work, pool_beta=POOL_BETA):
    """Safe outer envelope with exact marginal subset DP and monotone pruning."""
    work['outer_union_calls'] += 1
    masks = deepcopy(problem['masks'])
    iterations, max_states = 0, 0
    while True:
        iterations += 1
        work['outer_union_iterations'] += 1
        if any(not mask for mask in masks):
            return _no_feasible(members, iterations=iterations, max_dp_states=max_states)
        bounds = []
        for i, source in enumerate(problem['source_boxes']):
            fixed = [j for j, mask in enumerate(masks) if mask == [i]]
            optional = [j for j, mask in enumerate(masks) if i in mask and len(mask) > 1]
            pooled = deepcopy(anchors[i])
            for j in fixed:
                _add(pooled, members[j])
            block = _intersection(source, [problem['member_boxes'][j] for j in fixed])
            if block is None:
                return _no_feasible(members, iterations=iterations, max_dp_states=max_states)
            for op in OPERATORS:
                base_n = sum(pooled[op].values())
                for cat in ALPHABETS[op]:
                    choices = [(members[j][op][cat], sum(members[j][op].values()))
                               for j in optional]
                    envelope, states = _subset_endpoint(pooled[op][cat], base_n, choices, work, pool_beta)
                    max_states = max(max_states, states)
                    old = block[op]['bounds'][cat]
                    block[op]['bounds'][cat] = [max(old[0], envelope[0]), min(old[1], envelope[1])]
            if not _feasible(block):
                return _no_feasible(members, iterations=iterations, max_dp_states=max_states)
            bounds.append(_project_simplex(block))
        reduced = [[i for i in mask
                    if _intersection(bounds[i], [problem['member_boxes'][j]]) is not None]
                   for j, mask in enumerate(masks)]
        if reduced == masks:
            return dict(bounds=_mark(bounds, 'outer_assignment_union'), masks=masks,
                        no_feasible=False, iterations=iterations, max_dp_states=max_states)
        masks = reduced


def plan(member, anchors, case, bounds, work, raw_beta=RAW_BETA):
    """Use cumulative safety bounds while keeping original-source point models."""
    raw = boxes(member, work, raw_beta)
    blocks = {i: block for i, source in enumerate(bounds)
              if (block := _intersection(raw, [source])) is not None}
    candidates = list(blocks)
    if candidates:
        risks, goals, means = {}, {}, []
        for i, block in blocks.items():
            r = evidence.robust.risk_bounds(block, work)
            g = evidence.robust.goals_lower(block, case, work)
            for policy in r:
                risks[policy] = max(risks.get(policy, F(0)), r[policy])
                goals[policy] = min(goals.get(policy, g[policy]), g[policy])
            combined = deepcopy(anchors[i])
            _add(combined, member)
            means.append(evidence.posterior(combined))
        p = {op: {cat: sum(mean[op][cat] for mean in means) / len(means)
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
        risks = evidence.robust.risk_bounds(raw, work)
        goals = evidence.robust.goals_lower(raw, case, work)
        p = evidence.posterior(member)
    pure = vectors(case, p)
    work['planning_calls'] += 1
    result = dict(**evidence.robust.solve(pure, risks, goals, work), envelopes=envelope,
                  risks=risks, goals_lower=goals, pure_vectors=pure,
                  candidates=candidates, candidate_envelopes=blocks, mode=mode)
    result['query_proxy'] = query_core.query_proxy(member, anchors, case, result, work)
    result['query_ready'] = (mode == 'library' and result['utility_lower'] >= 2
                             and result['query_proxy'] is not None
                             and result['query_proxy'] <= query_core.THRESHOLD)
    return result
