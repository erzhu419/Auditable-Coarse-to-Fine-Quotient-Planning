"""Cumulative confidence against the original fixed-source acquisition rule."""
from copy import deepcopy
from math import log

from . import assignment_union_v222 as union
from . import fixed_source_acquisition_v219 as prior
from . import latent_mechanisms_v213 as evidence

ARMS = ('ORIGINAL', 'FIXED', 'UNION')
SOURCE_BETA = log(2 * 5544 / .05)
MEMBER_BETA = log(2 * 4032 / (1 / 88))
POOL_BETA = log(2 * 13608 / .025)
OPERATORS, ALPHABETS = union.OPERATORS, union.ALPHABETS
empty, vectors, queries = union.empty, union.vectors, union.queries
clear_cache = union.clear_cache


def raw_problem(anchors, members, work):
    """Keep original source endpoints; allocate new raw error only to members."""
    source_boxes = [evidence.boxes(anchor, work) for anchor in anchors]
    member_boxes = [union._project_simplex(union.boxes(member, work, MEMBER_BETA))
                    for member in members]
    masks = [[i for i, source in enumerate(source_boxes)
              if union._intersection(source, [member]) is not None]
             for member in member_boxes]
    return dict(source_boxes=source_boxes, member_boxes=member_boxes, masks=masks)


def prepare(anchors, arm, work):
    work['strong_reference_preparations'] += 1
    return dict(members=[], bounds=[evidence.boxes(anchor, work) for anchor in anchors],
                masks=[], no_feasible=False, iterations=0, max_dp_states=0)


def make_plan(member, anchors, case, arm, work, state, force_member=False):
    if arm == 'ORIGINAL':
        return prior.make_plan(member, anchors, case, 'SET', work,
                               force_member=force_member)
    return union.plan(member, anchors, case, [] if force_member else state['bounds'],
                      work, raw_beta=MEMBER_BETA)


def choose(member, anchors, case, arm, plan, spent, work, state):
    return prior.choose(member, anchors, case, 'SET', plan, spent, work)


def advance(state, member, anchors, arm, work):
    """Retain all terminal targets after decisions, without pooling point models."""
    if arm != 'UNION':
        return None
    state['members'].append(deepcopy(member))
    work['union_retained_targets'] += 1
    work['union_retained_samples'] += sum(sum(row.values()) for row in member.values())
    problem = raw_problem(anchors, state['members'], work)
    result = union.outer_union(problem, anchors, state['members'], work,
                               pool_beta=POOL_BETA)
    state.update(result)
    return result
