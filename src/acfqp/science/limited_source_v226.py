"""Limited source evidence: fixed, classified point updates, or confidence union."""
from copy import deepcopy

from . import mixture_confidence_v225 as prior

ARMS = ('FULL_FIXED', 'LOW_FIXED', 'LOW_PARAM', 'LOW_UNION')
SOURCE_BETA = prior.SOURCE_BETA
MEMBER_THRESHOLD, POOL_THRESHOLD = prior.MEMBER_THRESHOLD, prior.POOL_THRESHOLD
OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
empty, vectors, queries = prior.empty, prior.vectors, prior.queries
clear_cache = prior.clear_cache


def prepare(anchors, arm, work):
    work['limited_source_preparations'] += 1
    state = prior.prepare(anchors, 'UNION_CS' if arm == 'LOW_UNION' else 'FIXED_CS', work)
    if arm == 'LOW_PARAM':
        state.update(counts=deepcopy(anchors), commits=[0]*len(anchors))
    return state


def make_plan(member, anchors, case, arm, work, state, force_member=False):
    points = state['counts'] if arm == 'LOW_PARAM' else anchors
    return prior.make_plan(member, points, case, 'FIXED_CS', work, state, force_member)


def choose(member, anchors, case, arm, plan, spent, work, state):
    points = state['counts'] if arm == 'LOW_PARAM' else anchors
    return prior.choose(member, points, case, 'FIXED_CS', plan, spent, work, state)


def advance(state, member, anchors, arm, work, terminal_plan=None):
    """Update only after decisions; classified counts remain predictive, not safety."""
    if arm == 'LOW_UNION':
        return prior.advance(state, member, anchors, 'UNION_CS', work)
    if arm != 'LOW_PARAM' or terminal_plan is None:
        return None
    if terminal_plan['mode'] != 'library' or len(terminal_plan['candidates']) != 1:
        return None
    index = terminal_plan['candidates'][0]
    for op in OPERATORS:
        for cat in ALPHABETS[op]:
            state['counts'][index][op][cat] += member[op][cat]
    state['commits'][index] += 1
    samples = sum(sum(row.values()) for row in member.values())
    work['parameter_committed_targets'] += 1
    work['parameter_committed_samples'] += samples
    return dict(source_index=index, samples=samples)
