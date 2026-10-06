from copy import deepcopy

import pytest

from scripts import audit_convex_query_qualification_v241 as audit


def fixture(status='admitted_bad_kernel'):
    original = dict(life=2, index=44, arm='ORACLE_GAP', kind='positive',
        case=dict(operating='low', retry_cost='19/20'), identity={'A': 'a'},
        certificate_index=77, fees={'total_reference_paid_samples': 100})
    previous = dict(query='risk', chosen='DETOUR_RETURN', other='DETOUR_RETRY',
        family='D_REC_R', projected_counts={'D_REC': {'RECOVERY': 2, 'OTHER': 3},
        'R': {'DELIVERY': 3, 'LOST': 2}}, threshold=960, regret_threshold='1/20',
        status='unknown', certified=False, leaves=[{'old_bound': '1/2'}])
    diagnostic = dict(original, query='risk', chosen=previous['chosen'], other=previous['other'],
        family=previous['family'], projected_counts=deepcopy(previous['projected_counts']),
        result=dict(status=status, family=previous['family'], threshold=960, regret_threshold='1/20',
            projected_counts=deepcopy(previous['projected_counts']),
            global_tangent={'certified': status == 'global_bad_null_excluded', 'global_upper': '-2'},
            repaired_witness={'parameters': {'R': {'DELIVERY': '3/4', 'LOST': '1/4'}}, 'gap': '50001/1000000'}))
    ready = status == 'global_bad_null_excluded'
    routed = {field: deepcopy(previous[field]) for field in
        ('query', 'chosen', 'other', 'family', 'projected_counts', 'threshold', 'regret_threshold')}
    routed.update(classification_status=status, status='certified' if ready else 'unknown', certified=ready,
        proof_reference=dict(artifact='reports/convex_query_null_v240/records.json', record_index=4,
            field='result.global_tangent' if ready else 'result.repaired_witness'))
    if status == 'admitted_bad_kernel':
        routed['admitted_witness'] = deepcopy(diagnostic['result']['repaired_witness'])
    return original, previous, diagnostic, routed


@pytest.mark.parametrize('status', ('admitted_bad_kernel', 'global_bad_null_excluded'))
def test_replacement_preserves_exact_proof_reference_and_exclusion_decision(status):
    original, previous, diagnostic, routed = fixture(status)
    failed = []
    check = lambda name, ok: failed.append(name) if not ok else None
    ready = audit.audit_replacement(original, 'risk', previous, diagnostic, 4, routed, check)
    assert not failed and ready == (status == 'global_bad_null_excluded')
    wrong = deepcopy(routed)
    wrong['proof_reference']['record_index'] = 5
    wrong['certified'] = not ready
    audit.audit_replacement(original, 'risk', previous, diagnostic, 4, wrong, check)
    assert failed == ['replacement_uses_exact_validated_proof_and_exclusion_only_decision']


def test_same_counts_cannot_route_proof_from_different_known_retry_cost():
    original, previous, diagnostic, routed = fixture()
    diagnostic['case'] = dict(operating='low', retry_cost='17/20')
    failed = []
    audit.audit_replacement(original, 'risk', previous, diagnostic, 4, routed,
        lambda name, ok: failed.append(name) if not ok else None)
    assert failed == ['replacement_matches_original_identity_case_costs_and_counts']


def test_unreplaced_certificate_cannot_change_counts_or_decision():
    _, previous, _, _ = fixture()
    wrong = deepcopy(previous)
    wrong['projected_counts']['R']['DELIVERY'] = 4
    wrong['certified'] = True
    failed = []
    assert not audit.audit_reused_comparison(wrong, previous,
        lambda name, ok: failed.append(name) if not ok else None)
    assert failed == ['unreplaced_comparison_is_exact_validated_v239_certificate']


def test_alternative_and_and_three_query_and_reject_or_integration():
    failed = []
    check = lambda name, ok: failed.append(name) if not ok else None
    audit.audit_and({'certified': False}, [True, False, True], check)
    audit.audit_row_and({'query_ready': False}, dict(reward=True, goal=True, risk=False), check)
    assert not failed
    audit.audit_and({'certified': True}, [True, False, True], check)
    audit.audit_row_and({'query_ready': True}, dict(reward=True, goal=True, risk=False), check)
    assert failed == ['complete_alternative_and', 'complete_three_query_and']
