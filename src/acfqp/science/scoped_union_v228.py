"""Assignment-safe confidence banks for one scoped operator revision."""
from copy import deepcopy
from fractions import Fraction as F

from . import assignment_union_v222 as union
from . import mixture_confidence_v225 as mixture

OPERATORS, ALPHABETS = mixture.OPERATORS, mixture.ALPHABETS
empty = mixture.empty
MEMBER_THRESHOLD = 20160
POOL_THRESHOLD = 1680


def boxes(counts, work, threshold=MEMBER_THRESHOLD):
    return mixture.boxes(counts, work, threshold)


def _state(priors, anchors, changed_op):
    return dict(priors=deepcopy(priors), anchor_counts=deepcopy(anchors),
                changed_op=changed_op, members=[], bounds=deepcopy(priors),
                masks=[], no_feasible=False, iterations=0, max_dp_states=0)


def initial_state(anchors, work):
    """A starts with source-pool CSs, with no finite-sample source event."""
    work['scoped_initializations'] += 1
    priors = [union._project_simplex(boxes(anchor, work, POOL_THRESHOLD))
              for anchor in anchors]
    return _state(priors, anchors, None)


def branch_state(a_bounds, changed_op, work):
    """Inherit only unchanged A intervals; every B pooled count starts at zero."""
    work['scoped_branch_initializations'] += 1
    priors = deepcopy(a_bounds)
    for prior in priors:
        for op in OPERATORS:
            prior[op]['n'] = 0
            prior[op]['counts'] = dict.fromkeys(ALPHABETS[op], 0)
            prior[op]['kind'] = ('scoped_unknown' if op == changed_op
                                 else 'scoped_inherited')
            if op == changed_op:
                prior[op]['bounds'] = {cat: [F(0), F(1)] for cat in ALPHABETS[op]}
        union._project_simplex(prior)
    return _state(priors, [empty() for _ in priors], changed_op)


def calibrated_branch(a_bounds, changed_op, permutation, b_anchors, work):
    """Intersect one A-to-B hypothesis with the common paid B source prefix."""
    work['scoped_calibrated_initializations'] += 1
    priors, infeasible = [], False
    for j, anchor in enumerate(b_anchors):
        box = boxes(anchor, work, POOL_THRESHOLD)
        inherited = a_bounds[permutation[j]]
        for op in OPERATORS:
            box[op]['kind'] = ('scoped_calibrated_changed' if op == changed_op
                               else 'scoped_calibrated_inherited')
            if op != changed_op:
                for cat in ALPHABETS[op]:
                    old, new = box[op]['bounds'][cat], inherited[op]['bounds'][cat]
                    box[op]['bounds'][cat] = [max(old[0], new[0]), min(old[1], new[1])]
        if union._feasible(box):
            union._project_simplex(box)
        else:
            infeasible = True
        priors.append(box)
    state = _state(priors, b_anchors, changed_op)
    state['permutation'] = tuple(permutation)
    if infeasible:
        state.update(bounds=[], no_feasible=True)
    return state


def candidates(state, member, work):
    """Compatibility is calculated without committing the current target."""
    raw = union._project_simplex(boxes(member, work))
    return {i: block for i, prior in enumerate(state['bounds'])
            if (block := union._intersection(prior, [raw])) is not None}


def _subset_endpoint(base_k, base_n, optional, work):
    states = union.subset_extrema(base_k, base_n, optional, work)
    lower, upper = F(1), F(0)
    for n, (low_k, high_k) in states.items():
        lower = min(lower, mixture.interval(low_k, n, work, POOL_THRESHOLD)[0])
        upper = max(upper, mixture.interval(high_k, n, work, POOL_THRESHOLD)[1])
    return [lower, upper], len(states)


def _outer(state, member_boxes, masks, work):
    """Retain an outer envelope of every compatible full target assignment."""
    work['scoped_outer_calls'] += 1
    members, priors = state['members'], state['priors']
    iterations, max_states = 0, 0
    while True:
        iterations += 1
        work['scoped_outer_iterations'] += 1
        if any(not mask for mask in masks):
            return union._no_feasible(members, iterations=iterations,
                                      max_dp_states=max_states)
        bounds = []
        for i, prior in enumerate(priors):
            fixed = [j for j, mask in enumerate(masks) if mask == [i]]
            optional = [j for j, mask in enumerate(masks) if i in mask and len(mask) > 1]
            pooled = deepcopy(state['anchor_counts'][i])
            for j in fixed:
                union._add(pooled, members[j])
            block = union._intersection(prior, [member_boxes[j] for j in fixed])
            if block is None:
                return union._no_feasible(members, iterations=iterations,
                                          max_dp_states=max_states)
            for op in OPERATORS:
                base_n = sum(pooled[op].values())
                for cat in ALPHABETS[op]:
                    choices = [(members[j][op][cat], sum(members[j][op].values()))
                               for j in optional]
                    envelope, size = _subset_endpoint(pooled[op][cat], base_n,
                                                       choices, work)
                    max_states = max(max_states, size)
                    old = block[op]['bounds'][cat]
                    block[op]['bounds'][cat] = [max(old[0], envelope[0]),
                                               min(old[1], envelope[1])]
            if not union._feasible(block):
                return union._no_feasible(members, iterations=iterations,
                                          max_dp_states=max_states)
            bounds.append(union._project_simplex(block))
        reduced = [[i for i in mask
                    if union._intersection(bounds[i], [member_boxes[j]]) is not None]
                   for j, mask in enumerate(masks)]
        if reduced == masks:
            return dict(bounds=bounds, masks=masks, no_feasible=False,
                        iterations=iterations, max_dp_states=max_states)
        masks = reduced


def advance(state, member, work):
    """Commit only a completed target and recompute from immutable scoped priors."""
    state['members'].append(deepcopy(member))
    work['scoped_retained_targets'] += 1
    work['scoped_retained_samples'] += sum(sum(row.values()) for row in member.values())
    member_boxes = [union._project_simplex(boxes(row, work)) for row in state['members']]
    masks = [[i for i, prior in enumerate(state['priors'])
              if union._intersection(prior, [row]) is not None]
             for row in member_boxes]
    result = _outer(state, member_boxes, masks, work)
    state.update(result)
    return result
