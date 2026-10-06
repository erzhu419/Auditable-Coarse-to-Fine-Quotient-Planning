"""Jeffreys mixture confidence sequences with uncertain target attribution."""
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction as F
from math import ceil, comb, floor

from . import assignment_union_v222 as union
from . import fixed_source_acquisition_v219 as prior
from . import latent_mechanisms_v213 as evidence

ARMS = ('ORIGINAL', 'FIXED_CS', 'UNION_CS')
SOURCE_BETA = evidence.BETA
MEMBER_THRESHOLD = 14784
POOL_THRESHOLD = 840
OPERATORS, ALPHABETS = union.OPERATORS, union.ALPHABETS
empty, vectors, queries = union.empty, union.vectors, union.queries
_INTERVAL_CACHE = {}


def clear_cache():
    _INTERVAL_CACHE.clear()


def _mixture_normalizer(k, n):
    """Exact Jeffreys Beta(1/2,1/2) sequence likelihood."""
    return F(comb(2*k, k)*comb(2*(n-k), n-k), 4**n*comb(n, k))


def _log_bounds(value):
    value = F(value)
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 80, ROUND_FLOOR
        low = Decimal(value.numerator)/Decimal(value.denominator)
        ctx.rounding = ROUND_CEILING
        high = Decimal(value.numerator)/Decimal(value.denominator)
        # ln is correctly rounded; adjacent values enclose both endpoint logs.
        return low.ln().next_minus(), high.ln().next_plus()


def _log_e_bounds(k, n, p, normalizer, boundary, work):
    """Outward bounds for log(M/L)-log(threshold) at exact p."""
    work['mixture_log_e_evaluations'] += 1
    logs = [(count, _log_bounds(probability))
            for count, probability in ((k, p), (n-k, 1-p)) if count]
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 80, ROUND_FLOOR
        lower = normalizer[0]-boundary[1]
        for count, (_, high) in logs:
            with localcontext() as product_ctx:
                product_ctx.rounding = ROUND_CEILING
                term = count*high
            lower -= term
        ctx.rounding = ROUND_CEILING
        upper = normalizer[1]-boundary[0]
        for count, (low, _) in logs:
            with localcontext() as product_ctx:
                product_ctx.rounding = ROUND_FLOOR
                term = count*low
            upper -= term
    return lower, upper


def interval(k, n, work, threshold=MEMBER_THRESHOLD):
    """Invert the beta(.5,.5) mixture e-value, rounding endpoints outward."""
    work['mixture_interval_calls'] += 1
    key = (k, n, threshold)
    if key in _INTERVAL_CACHE:
        work['mixture_interval_cache_hits'] += 1
        return _INTERVAL_CACHE[key]
    work['mixture_interval_computations'] += 1
    if not n:
        result = F(0), F(1)
    else:
        normalizer = _log_bounds(_mixture_normalizer(k, n))
        boundary, x = _log_bounds(threshold), F(k, n)
        # M <= max L and every supported threshold exceeds one, so the
        # exact mode is inside. Positive observed counts make 0/1 outside.
        if k:
            lo, hi = F(0), x
            for _ in range(64):
                mid = (lo+hi)/2
                below, above = _log_e_bounds(k, n, mid, normalizer, boundary, work)
                if below > 0:
                    lo = mid
                elif above <= 0:
                    hi = mid
                else:
                    break
            lower = lo
        else:
            lower = F(0)
        if k < n:
            lo, hi = x, F(1)
            for _ in range(64):
                mid = (lo+hi)/2
                below, above = _log_e_bounds(k, n, mid, normalizer, boundary, work)
                if below > 0:
                    hi = mid
                elif above <= 0:
                    lo = mid
                else:
                    break
            upper = hi
        else:
            upper = F(1)
        grid = evidence.robust.GRID
        result = F(floor(lower*grid), grid), F(ceil(upper*grid), grid)
    _INTERVAL_CACHE[key] = result
    return result


def boxes(counts, work, threshold=MEMBER_THRESHOLD):
    return {op: dict(n=sum(counts[op].values()), counts=deepcopy(counts[op]),
                     bounds={cat: list(interval(counts[op][cat],
                                 sum(counts[op].values()), work, threshold))
                             for cat in ALPHABETS[op]})
            for op in OPERATORS}


def _mark(bounds, kind):
    for box in bounds:
        for op in OPERATORS:
            box[op]['kind'] = kind
    return bounds


def initial_bounds(anchors, work):
    """The two CS arms share this source-only region, including its pool event."""
    bounds = [union._intersection(evidence.boxes(anchor, work),
                                  [boxes(anchor, work, POOL_THRESHOLD)])
              for anchor in anchors]
    return _mark(bounds, 'initial_source_mixture')


def raw_problem(anchors, members, work):
    source_boxes = initial_bounds(anchors, work)
    member_boxes = [union._project_simplex(boxes(member, work)) for member in members]
    masks = [[i for i, source in enumerate(source_boxes)
              if union._intersection(source, [member]) is not None]
             for member in member_boxes]
    return dict(source_boxes=source_boxes, member_boxes=member_boxes, masks=masks)


def _subset_endpoint(base_k, base_n, optional, work):
    states = union.subset_extrema(base_k, base_n, optional, work)
    lower, upper = F(1), F(0)
    for n, (low_k, high_k) in states.items():
        lower = min(lower, interval(low_k, n, work, POOL_THRESHOLD)[0])
        upper = max(upper, interval(high_k, n, work, POOL_THRESHOLD)[1])
    return [lower, upper], len(states)


def outer_union(problem, anchors, members, work):
    """Safe outer envelope of all assignments, using monotone CS endpoints."""
    work['outer_union_calls'] += 1
    masks = deepcopy(problem['masks'])
    iterations, max_states = 0, 0
    while True:
        iterations += 1
        work['outer_union_iterations'] += 1
        if any(not mask for mask in masks):
            return union._no_feasible(members, iterations=iterations, max_dp_states=max_states)
        bounds = []
        for i, source in enumerate(problem['source_boxes']):
            fixed = [j for j, mask in enumerate(masks) if mask == [i]]
            optional = [j for j, mask in enumerate(masks) if i in mask and len(mask)>1]
            pooled = deepcopy(anchors[i])
            for j in fixed:
                union._add(pooled, members[j])
            block = union._intersection(source, [problem['member_boxes'][j] for j in fixed])
            if block is None:
                return union._no_feasible(members, iterations=iterations, max_dp_states=max_states)
            for op in OPERATORS:
                base_n = sum(pooled[op].values())
                for cat in ALPHABETS[op]:
                    choices = [(members[j][op][cat], sum(members[j][op].values()))
                               for j in optional]
                    envelope, states = _subset_endpoint(pooled[op][cat], base_n, choices, work)
                    max_states = max(max_states, states)
                    old = block[op]['bounds'][cat]
                    block[op]['bounds'][cat] = [max(old[0], envelope[0]), min(old[1], envelope[1])]
            if not union._feasible(block):
                return union._no_feasible(members, iterations=iterations, max_dp_states=max_states)
            bounds.append(union._project_simplex(block))
        reduced = [[i for i in mask
                    if union._intersection(bounds[i], [problem['member_boxes'][j]]) is not None]
                   for j, mask in enumerate(masks)]
        if reduced == masks:
            return dict(bounds=_mark(bounds, 'outer_assignment_mixture'), masks=masks,
                        no_feasible=False, iterations=iterations, max_dp_states=max_states)
        masks = reduced


def prepare(anchors, arm, work):
    work['mixture_preparations'] += 1
    bounds = ([evidence.boxes(anchor, work) for anchor in anchors]
              if arm == 'ORIGINAL' else initial_bounds(anchors, work))
    return dict(members=[], bounds=bounds, masks=[], no_feasible=False,
                iterations=0, max_dp_states=0)


def make_plan(member, anchors, case, arm, work, state, force_member=False):
    if arm == 'ORIGINAL':
        return prior.make_plan(member, anchors, case, 'SET', work, force_member=force_member)
    raw = boxes(member, work)
    bounds = [] if force_member else state['bounds']
    blocks = {i: block for i, source in enumerate(bounds)
              if (block := union._intersection(raw, [source])) is not None}
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
            union._add(combined, member)
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
        risks = evidence.robust.risk_bounds(raw, work)
        goals = evidence.robust.goals_lower(raw, case, work)
        p = evidence.posterior(member)
    pure = vectors(case, p)
    work['planning_calls'] += 1
    result = dict(**evidence.robust.solve(pure, risks, goals, work), envelopes=envelope,
                  risks=risks, goals_lower=goals, pure_vectors=pure,
                  candidates=candidates, candidate_envelopes=blocks, mode=mode)
    result['query_proxy'] = union.query_core.query_proxy(member, anchors, case, result, work)
    result['query_ready'] = (mode == 'library' and result['utility_lower']>=2
                             and result['query_proxy'] is not None
                             and result['query_proxy']<=union.query_core.THRESHOLD)
    return result


def choose(member, anchors, case, arm, plan, spent, work, state):
    return prior.choose(member, anchors, case, 'SET', plan, spent, work)


def advance(state, member, anchors, arm, work):
    """Retain every completed target only after its terminal decision is frozen."""
    if arm != 'UNION_CS':
        return None
    state['members'].append(deepcopy(member))
    work['union_retained_targets'] += 1
    work['union_retained_samples'] += sum(sum(row.values()) for row in member.values())
    problem = raw_problem(anchors, state['members'], work)
    result = outer_union(problem, anchors, state['members'], work)
    state.update(result)
    return result
