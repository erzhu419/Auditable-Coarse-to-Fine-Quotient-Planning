"""Only skip types whose current four-cost query decisions are jointly ready."""
ARMS = ('DIRECT_RR', 'DIRECT_JOINT_UNRESOLVED')


def ready_by_type(records):
    return [all(row['trajectory']['all_ready'] for row in records if row['identity'] == identity)
        for identity in range(3)]


def eligible_types(arm, readiness):
    return list(range(3)) if arm == 'DIRECT_RR' else [identity for identity in range(3) if not readiness[identity]]


def select_type(cursor, eligible):
    identity = next((cursor+offset) % 3 for offset in range(3) if (cursor+offset) % 3 in eligible)
    return identity, identity+1
