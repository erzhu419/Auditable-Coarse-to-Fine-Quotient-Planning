"""The endpoint runner must preserve policies and distinguish earlier evidence."""
from collections import Counter
from scripts import run_life_end_query_evidence_v238 as runner


def test_qualify_passes_training_and_validation_separately(monkeypatch):
    training = {op: ['DELIVERY'] for op in runner.split.OPERATORS}
    validation = {op: ['LOST', 'LOST'] for op in runner.split.OPERATORS}
    point = {q: {'policy': p} for q, p in
        (('reward', 'WAIT'), ('goal', 'SHORT'), ('risk', 'DETOUR_RETURN'))}
    tape = dict(life=0, index=54, arm='ORACLE_GAP', kind='failure', phase='A_RETURN',
        case={}, identity=0, fees={'total_reference_paid_samples': 100},
        early_fees={'total_reference_paid_samples': 80}, endpoint_index=77,
        certificate_index=77, evidence_end_index=76,
        operators={op: training[op]+validation[op] for op in training})
    monkeypatch.setattr(runner.split, 'split_tape', lambda t: dict(training=training, validation=validation))

    def fake(train, validate, case, queries, cache, work):
        assert train == training and validate == validation and queries == point
        return dict(queries={q: dict(v, certified=True) for q, v in point.items()},
                    all_ready=True, comparison_records=[])

    monkeypatch.setattr(runner.core, 'certificates', fake)
    result = runner.qualify(tape, {'terminal_plan': {'queries': point, 'query_ready': False}},
        {'query_ready': False}, {}, Counter())
    assert result['query_ready'] and not result['v235_query_ready']
    assert result['index'] == 54 and result['certificate_index'] == 77
    assert result['fees'] != result['early_fees']
    assert result['training_row_lengths'] == dict.fromkeys(training, 1)
    assert result['validation_row_lengths'] == dict.fromkeys(training, 2)


def test_grouping_keeps_whole_query_and_arm_statuses():
    queries = {q: dict(policy='WAIT', certified=(q != 'risk'),
        comparisons=[] if q != 'risk' else [{'family': 'S_D_FULL', 'certified': False}])
        for q in ('reward', 'goal', 'risk')}
    row = dict(kind='failure', arm='ORACLE_GAP', old_query_ready=False,
        v235_query_ready=False, query_ready=False, queries=queries)
    result = runner.grouped([row])
    assert result['failure']['queries'] == {'reward': 1, 'goal': 1, 'risk': 0}
    assert result['failure']['query_ready'] == 0
    assert result['failure']['blockers_by_family'] == {'S_D_FULL': 1}
    assert result['failure']['arms']['ORACLE_GAP']['targets'] == 1
