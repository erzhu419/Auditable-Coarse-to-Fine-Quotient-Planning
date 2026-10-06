"""The new runner must pass all paid source rows and preserve the fixed comparison."""
from collections import Counter
from scripts import run_life_end_joint_evidence_v239 as runner


def test_joint_runner_passes_paid_sources_even_without_validation(monkeypatch):
    point = {q: {'policy': p} for q, p in
        (('reward', 'WAIT'), ('goal', 'SHORT'), ('risk', 'SHORT'))}
    paid = {op: ['DELIVERY']*384 for op in runner.core.OPERATORS}
    tape = dict(life=1, index=54, arm='ORACLE_GAP', kind='positive', phase='A_RETURN',
        case={}, identity=0, fees={'total_reference_paid_samples': 17024},
        early_fees={'total_reference_paid_samples': 14000}, endpoint_index=77,
        certificate_index=77, evidence_end_index=2, operators=paid)

    def fake(operators, case, queries, cache, work):
        assert operators is paid and queries is point
        return dict(queries={q: dict(v, certified=True) for q, v in point.items()},
                    all_ready=True, comparison_records=[])

    monkeypatch.setattr(runner.core, 'certificates', fake)
    row = runner.qualify(tape, {'terminal_plan': {'queries': point, 'query_ready': True}},
        {'query_ready': True}, {'query_ready': False}, {}, Counter())
    assert row['query_ready'] and row['v235_query_ready'] and not row['v238_query_ready']
    assert row['row_lengths'] == dict.fromkeys(paid, 384)
    assert row['fees'] == tape['fees'] and row['early_fees'] == tape['early_fees']
    assert row['index'] == 54 and row['certificate_index'] == 77
    assert row['new_observations'] == row['new_paid_samples'] == 0


def test_runner_rejects_changing_policy_for_saved_truth(monkeypatch):
    import pytest
    point = {q: {'policy': 'WAIT'} for q in ('reward', 'goal', 'risk')}
    changed = {q: {'policy': 'SHORT' if q == 'goal' else 'WAIT'} for q in point}
    monkeypatch.setattr(runner.core, 'certificates', lambda *args: dict(queries=changed))
    with pytest.raises(ValueError, match='retain original policies'):
        runner.qualify({'operators': {}, 'case': {}}, {'terminal_plan': {'queries': point}},
                       {}, {}, {}, Counter())
