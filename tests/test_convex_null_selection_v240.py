from copy import deepcopy

import pytest

from scripts.convex_null_selection_v240 import select


def comparison(family, other, certified=False):
    counts = ({'S': {'DELIVERY': 310, 'LOST': 74},
               'D_FULL': {'DELIVERY': 270, 'RECOVERY': 80, 'LOST': 34}}
              if family == 'S_D_FULL' else
              {'D_REC': {'RECOVERY': 80, 'OTHER': 304}, 'R': {'DELIVERY': 296, 'LOST': 88}})
    return dict(query='risk', chosen='DETOUR_RETURN', other=other, family=family,
                certified=certified, projected_counts=counts, leaves=[dict(proof='retained')])


def rows():
    result = []
    for index in range(24):
        selected = index % 2 == 0 and index < 18
        sd = comparison('S_D_FULL', 'SHORT', certified=not selected or index >= 12)
        retry = comparison('D_REC_R', 'DETOUR_RETRY', certified=not selected)
        risk = dict(policy='DETOUR_RETURN', certified=not selected,
                    comparisons=[retry, sd])
        goal = dict(policy='DETOUR_RETURN', certified=not selected,
                    comparisons=[dict(retry, query='goal')])
        result.append(dict(life=index//8, index=index, arm='ORACLE_GAP',
            kind='failure' if index < 16 else 'positive', case={'operating': 'low', 'retry_cost': '17/20'},
            identity=index % 3, certificate_index=77,
            fees={'total_reference_paid_samples': 4608+1152}, query_ready=not selected,
            queries={'risk': risk, 'goal': goal, 'reward': {'policy': 'WAIT', 'certified': True}}))
    return result


def test_frozen_selection_preserves_order_prefers_sd_and_uses_only_uncertified_risk():
    originals = rows()
    expected = deepcopy(originals)
    selected = select(originals)
    assert [row['index'] for row in selected] == list(range(0, 18, 2))
    assert [row['family'] for row in selected] == ['S_D_FULL']*6+['D_REC_R']*3
    assert all(row['query'] == 'risk' and row['chosen'] == 'DETOUR_RETURN' for row in selected)
    for descriptor in selected:
        original = originals[descriptor['index']]
        assert descriptor['case'] == original['case'] and descriptor['fees'] == original['fees']
        assert descriptor['certificate_index'] == 77
        assert descriptor['old_comparison']['projected_counts'] == descriptor['projected_counts']
        assert not descriptor['old_comparison']['certified']
    selected[0]['projected_counts']['S']['DELIVERY'] = 0
    selected[0]['old_comparison']['leaves'].clear()
    assert originals == expected


def test_certified_risk_or_other_actions_cannot_be_replaced_by_goal_comparisons():
    originals = rows()
    original = originals[0]
    original['queries']['risk']['comparisons'] = [
        comparison('S_D_FULL', 'SHORT', certified=True),
        comparison('D_REC_R', 'DETOUR_RETRY', certified=True),
        dict(query='risk', chosen='DETOUR_RETURN', other='WAIT', family='D_FULL', certified=False)]
    assert not original['queries']['goal']['comparisons'][0]['certified']
    with pytest.raises(ValueError, match='declared uncertified risk comparison'):
        select(originals)
