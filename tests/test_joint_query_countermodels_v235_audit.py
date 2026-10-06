from scripts import audit_joint_query_countermodels_v235 as audit


def test_accepts_strict_bad_gap_only_inside_the_original_projected_region():
    case = dict(operating='low', retry_cost='17/20')
    counts = {'S': {'DELIVERY': 8, 'LOST': 2},
              'D_FULL': {'DELIVERY': 2, 'LOST': 8, 'RECOVERY': 0}}
    parameters = {'S': {'DELIVERY': '4/5', 'LOST': '1/5'},
                  'D_FULL': {'DELIVERY': '1/5', 'LOST': '4/5', 'RECOVERY': '0'}}
    accepted, gap, ratio = audit.witness_values(case, 'risk', 'DETOUR_RETURN', 'SHORT', counts, parameters)
    assert accepted and gap > audit.evidence.REGRET and ratio <= 960
    reversed_accepted, _, _ = audit.witness_values(case, 'risk', 'SHORT', 'DETOUR_RETURN', counts, parameters)
    assert not reversed_accepted


def test_rejects_negative_probability_even_if_row_sum_is_one():
    case = dict(operating='low', retry_cost='17/20')
    counts = {'S': {'DELIVERY': 8, 'LOST': 2},
              'D_FULL': {'DELIVERY': 2, 'LOST': 8, 'RECOVERY': 0}}
    parameters = {'S': {'DELIVERY': '4/5', 'LOST': '1/5'},
                  'D_FULL': {'DELIVERY': '1/5', 'LOST': '9/10', 'RECOVERY': '-1/10'}}
    accepted, _, _ = audit.witness_values(case, 'risk', 'DETOUR_RETURN', 'SHORT', counts, parameters)
    assert not accepted
