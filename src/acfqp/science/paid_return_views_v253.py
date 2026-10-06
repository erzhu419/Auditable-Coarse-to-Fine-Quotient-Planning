"""A fixed TWO_WAY planning view of an already paid return-time snapshot.

Only compatible native B rows enter the query counts and confidence events.
B's inherited A view never enters the snapshot's native bank.
"""
from copy import deepcopy

from . import reuse_rebuild_pool_v242 as planning

OPERATORS, ALPHABETS = planning.OPERATORS, planning.ALPHABETS


def two_way_evidence(snapshot):
    life, index, identity = snapshot['life'], snapshot['index'], snapshot['identity']
    interface = snapshot['interface']
    b_identity = interface['b_to_a'].index(identity)
    eligible = tuple(op for op in OPERATORS if op != interface['changed_operator'])
    counts = deepcopy(snapshot['a_pool'])
    constraints = {}
    for op in OPERATORS:
        a_event = f'l{life}/A/pool{identity}/{op}'
        constraints[op] = [
            dict(counts=deepcopy(snapshot['a_source'][op]), threshold=720, event=a_event),
            dict(counts=deepcopy(snapshot['a_pool'][op]), threshold=720, event=a_event),
            dict(counts=deepcopy(snapshot['member'][op]), threshold=8640,
                 event=f'l{life}/member{index}/{op}')]
        if op in eligible:
            for category, value in snapshot['b_pool'][op].items():
                counts[op][category] += value
            b_event = f'l{life}/B/pool{b_identity}/{op}'
            constraints[op].extend(dict(counts=deepcopy(snapshot[key][op]), threshold=720, event=b_event)
                for key in ('b_source', 'b_pool'))
    transferred = {op: deepcopy(snapshot['b_pool'][op]) for op in eligible}
    transfer = dict(a_identity=identity, mapped_b_identity=b_identity, operators=eligible,
        transferred_counts=transferred, total_samples=sum(sum(row.values()) for row in transferred.values()))
    return counts, constraints, transfer


def make_two_way(snapshot, query_cache, work):
    counts, constraints, transfer = two_way_evidence(snapshot)
    plan = planning.plan_from_evidence(constraints, counts, snapshot['case'], query_cache, work)
    plan['return_transfer'] = transfer
    return plan
