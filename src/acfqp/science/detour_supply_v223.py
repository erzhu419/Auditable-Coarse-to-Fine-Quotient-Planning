"""Paid detour observation versus fixed or cumulatively bounded source evidence."""
from copy import deepcopy
from math import log

from . import assignment_union_v222 as union
from . import fixed_source_acquisition_v219 as prior

ARMS = ('FIXED_SET', 'UNION_SET', 'FIXED_DETOUR', 'UNION_DETOUR')
RAW_BETA = log(2 * 17640 / .025)
POOL_BETA = log(2 * 27216 / .025)
OPERATORS, ALPHABETS = union.OPERATORS, union.ALPHABETS
empty, vectors, queries = union.empty, union.vectors, union.queries
clear_cache = union.clear_cache


def prepare(anchors, arm, work):
    work['detour_supply_preparations'] += 1
    return dict(members=[], bounds=union.raw_problem(
                    anchors, [], work, raw_beta=RAW_BETA)['source_boxes'],
                masks=[], no_feasible=False, iterations=0, max_dp_states=0)


def make_plan(member, anchors, case, arm, work, state, force_member=False):
    return union.plan(member, anchors, case, [] if force_member else state['bounds'],
                      work, raw_beta=RAW_BETA)


def choose(member, anchors, case, arm, plan, spent, work, state):
    if spent == 384:
        return None
    if spent == 0 and arm in ('FIXED_DETOUR', 'UNION_DETOUR'):
        return dict(operator='DETOUR_PASS', reason='paid_detour_pilot',
                    scope='TARGET', source_index=None)
    return prior.choose(member, anchors, case, 'SET', plan, spent, work)


def advance(state, member, anchors, arm, work):
    """Called after the terminal decision; retain every target, without selection."""
    if arm in ('FIXED_SET', 'FIXED_DETOUR'):
        return None
    state['members'].append(deepcopy(member))
    work['union_retained_targets'] += 1
    work['union_retained_samples'] += sum(sum(row.values()) for row in member.values())
    problem = union.raw_problem(anchors, state['members'], work, raw_beta=RAW_BETA)
    result = union.outer_union(problem, anchors, state['members'], work, pool_beta=POOL_BETA)
    state.update(result)
    return result
