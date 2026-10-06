"""Keep each proposal on its fixed source-inclusive comparison and known cost."""
from scripts import probe_convex_query_null_v240 as runner


def test_runner_forwards_paid_counts_and_distinguishes_known_retry_cost(monkeypatch):
    counts = {'D_REC': {'RECOVERY': 117, 'OTHER': 539}, 'R': {'DELIVERY': 1389, 'LOST': 979}}
    costs = []

    def fake(observed, case, family):
        assert observed is counts and family == 'D_REC_R'
        costs.append(case['retry_cost'])
        return dict(status='unknown')

    monkeypatch.setattr(runner.core, 'classify', fake)
    descriptor = dict(life=2, index=44, arm='ORACLE_GAP', kind='positive',
        case={'retry_cost': '19/20'}, family='D_REC_R', projected_counts=counts,
        certificate_index=77, fees={'total_reference_paid_samples': 16352}, old_comparison={})
    first = runner.classify(descriptor)
    second = runner.classify(dict(descriptor, index=47, kind='failure', case={'retry_cost': '17/20'}))
    assert costs == ['19/20', '17/20']
    assert first['fees'] == second['fees'] == descriptor['fees']
    assert first['certificate_index'] == 77 and 'old_comparison' not in first
    assert first['new_observations'] == first['new_paid_samples'] == 0
