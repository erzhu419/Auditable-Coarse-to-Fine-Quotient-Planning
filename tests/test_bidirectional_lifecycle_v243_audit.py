from copy import deepcopy
from decimal import localcontext
from fractions import Fraction as F

from scripts import audit_bidirectional_lifecycle_v243 as audit


def counts(amount):
    result = audit.empty()
    for row in result.values():
        row['DELIVERY'] = amount
    return result


def fixture():
    return (dict(a=[counts(10), counts(20), counts(30)],
                 b=[counts(4), counts(5), counts(6)],
                 a_switch=[counts(2), counts(3), counts(4)]),
            dict(a=[counts(1), counts(1), counts(1)], b=[counts(1), counts(1), counts(1)]),
            dict(b_to_a=[2, 0, 1], changed_operator='DETOUR_PASS'))


def test_return_adds_native_b_once_skips_changed_row_and_never_mutates_banks():
    state, _, metadata = fixture()
    before = deepcopy(state)
    case = dict(context='A', stage='A_RETURN')
    merged = audit.evidence_counts(state, case, 0, 'TWO_WAY', metadata)
    assert merged['SHORT_PASS']['DELIVERY'] == merged['RECOVERY_RETRY']['DELIVERY'] == 15
    assert merged['DETOUR_PASS']['DELIVERY'] == 10
    assert audit.evidence_counts(state, case, 0, 'ONE_WAY', metadata) == counts(10)
    assert audit.evidence_counts(state, case, 0, 'REBUILD', metadata) == counts(10)
    assert state == before
    # A later native A batch changes only A; the B prefix is not merged twice.
    state['a'][0]['SHORT_PASS']['DELIVERY'] += 16
    assert audit.evidence_counts(state, case, 0, 'TWO_WAY', metadata)['SHORT_PASS']['DELIVERY'] == 31


def test_pre_return_one_two_share_same_b_inheritance_and_rebuild_stays_native():
    state, _, metadata = fixture()
    case = dict(context='B', stage='B')
    one = audit.evidence_counts(state, case, 1, 'ONE_WAY', metadata)
    assert one == audit.evidence_counts(state, case, 1, 'TWO_WAY', metadata)
    assert one['SHORT_PASS']['DELIVERY'] == 7
    assert one['DETOUR_PASS']['DELIVERY'] == 5
    assert audit.evidence_counts(state, case, 1, 'REBUILD', metadata) == counts(5)
    assert audit.transfer_view(case, 1, state, 'TWO_WAY', metadata) is None


def test_return_execution_appends_original_b_events_not_mixed_a_count_event():
    state, sources, metadata = fixture()
    case = dict(context='A', stage='A_RETURN')
    constraints = audit.execution_constraints(2, 54, case, 0, sources, state, counts(2), 'TWO_WAY', metadata)
    assert len(constraints['DETOUR_PASS']) == 3
    assert len(constraints['SHORT_PASS']) == 5
    row = constraints['SHORT_PASS']
    assert row[1]['counts']['DELIVERY'] == 10
    assert row[3] == dict(counts=counts(1)['SHORT_PASS'], threshold=720, event='l2/B/pool1/SHORT_PASS')
    assert row[4] == dict(counts=counts(5)['SHORT_PASS'], threshold=720, event='l2/B/pool1/SHORT_PASS')
    controls = audit.execution_constraints(2, 54, case, 0, sources, state, counts(2), 'ONE_WAY', metadata)
    assert all(len(rows) == 3 for rows in controls.values())


def test_transfer_ledger_credits_every_native_b_prefix_once_with_inverse_mapping():
    state, sources, metadata = fixture()
    ledger = audit.transfer_ledger(2, 54, sources, state, metadata)
    assert len(ledger['rows']) == 6
    assert ledger['total_source_samples'] == 6
    assert ledger['total_target_samples'] == 24
    assert ledger['total_samples'] == 30
    view = audit.transfer_view(dict(context='A', stage='A_RETURN'), 0, state, 'TWO_WAY', metadata)
    assert view['mapped_b_identity'] == 1 and view['total_samples'] == 10
    assert view['transferred_counts'] == {op: counts(5)[op] for op in ('SHORT_PASS', 'RECOVERY_RETRY')}


def test_binary_projection_rejects_real_scale_inward_shrink_without_tolerance():
    region = dict(counts={'DELIVERY': 360, 'LOST': 24}, threshold=720)
    lower, upper = audit.joint.binary_interval([region])
    with localcontext() as ctx:
        ctx.prec = 100
        outside = dict(DELIVERY=[F(lower)-F(1, 10**50), F(upper)+F(1, 10**50)],
                       LOST=[1-F(upper)-F(1, 10**50), 1-F(lower)+F(1, 10**50)])
        inside = dict(DELIVERY=[F(lower)+F(1, 10**15), F(upper)],
                      LOST=[1-F(upper), 1-F(lower)-F(1, 10**15)])
    assert audit.binary_encloses([region], outside)
    assert not audit.binary_encloses([region], inside)
