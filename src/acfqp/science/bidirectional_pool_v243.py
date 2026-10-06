"""Native row evidence reused in both directions under a known equality map.

ONE_WAY and TWO_WAY have identical A/B histories. On A_RETURN, TWO_WAY reads
each eligible native B pool once alongside its native A pool. The view never
rewrites either bank: B's inherited A evidence is absent from native B counts,
and new return observations enter only A. Query events continue with every
eligible B observation; execution retains the original A/B event labels.
"""
from copy import deepcopy

from . import reuse_rebuild_pool_v242 as original
from . import oracle_gap_pool_v231 as native

ARMS = ('ONE_WAY', 'TWO_WAY', 'REBUILD')
OPERATORS, ALPHABETS = original.OPERATORS, original.ALPHABETS
BATCH, CAP = original.BATCH, original.CAP
empty, bank = original.empty, original.bank
begin_b, observe, ready = original.begin_b, original.observe, original.ready


def prepare(anchors, life, arm, work):
    if arm not in ARMS:
        raise ValueError('the fixed comparison has ONE_WAY, TWO_WAY and REBUILD arms')
    state = native.prepare(anchors, life, work)
    state.update(arm=arm, return_merge=None)
    return state


def _returns_b_evidence(case, state):
    return state['arm'] == 'TWO_WAY' and case.get('stage') == 'A_RETURN'


def _b_identity(state, identity):
    return state['b_to_a'].index(identity)


def _eligible_operators(state):
    return tuple(operator for operator in OPERATORS if operator != state['changed_operator'])


def _record_return_merge(state, index):
    if state['return_merge'] is not None:
        return
    rows = []
    for identity in range(len(state['a']['pools'])):
        b_identity = _b_identity(state, identity)
        for operator in _eligible_operators(state):
            source = deepcopy(state['b']['sources'][b_identity][operator])
            pool = deepcopy(state['b']['pools'][b_identity][operator])
            target = {category: pool[category]-source[category] for category in ALPHABETS[operator]}
            rows.append(dict(a_identity=identity, b_identity=b_identity, operator=operator,
                event=f'l{state["life"]}/B/pool{b_identity}/{operator}', source_counts=source,
                pool_counts=pool, target_counts=target, source_samples=sum(source.values()),
                target_samples=sum(target.values()), total_samples=sum(pool.values())))
    state['return_merge'] = dict(stage='A_RETURN', first_target_index=index, rows=rows,
        total_source_samples=sum(row['source_samples'] for row in rows),
        total_target_samples=sum(row['target_samples'] for row in rows),
        total_samples=sum(row['total_samples'] for row in rows))


def point_counts(case, state, identity):
    counts = original.point_counts(case, state, identity)
    if _returns_b_evidence(case, state):
        native_b = state['b']['pools'][_b_identity(state, identity)]
        for operator in _eligible_operators(state):
            for category in ALPHABETS[operator]:
                counts[operator][category] += native_b[operator][category]
    return counts


def regions(member, case, state, identity, index):
    constraints = original.regions(member, case, state, identity, index)
    if _returns_b_evidence(case, state):
        _record_return_merge(state, index)
        b_identity = _b_identity(state, identity)
        for operator in _eligible_operators(state):
            event = f'l{state["life"]}/B/pool{b_identity}/{operator}'
            constraints[operator].extend(
                dict(native.joint.region(counts[b_identity][operator], 720), event=event)
                for counts in (state['b']['sources'], state['b']['pools']))
    return constraints


def make_plan(member, case, state, identity, index, query_cache, work):
    constraints = regions(member, case, state, identity, index)
    observed = point_counts(case, state, identity)
    plan = original.plan_from_evidence(constraints, observed, case, query_cache, work)
    transfer = None
    if _returns_b_evidence(case, state):
        b_identity = _b_identity(state, identity)
        operators = _eligible_operators(state)
        counts = {operator: deepcopy(state['b']['pools'][b_identity][operator]) for operator in operators}
        transfer = dict(a_identity=identity, mapped_b_identity=b_identity, operators=operators,
            transferred_counts=counts, total_samples=sum(sum(row.values()) for row in counts.values()))
    plan['return_transfer'] = transfer
    return plan
