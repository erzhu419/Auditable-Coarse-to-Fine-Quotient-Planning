import json
from fractions import Fraction as F

from scripts import probe_source_predictive_evidence_v236 as probe


def test_prepared_witness_retains_costs_and_separate_training_validation(monkeypatch):
    witness = dict(query='risk', chosen='DETOUR_RETURN', other='SHORT', gap='3/20',
        parameters={'S': {'DELIVERY': '19/20', 'LOST': '1/20'},
                    'D_FULL': {'DELIVERY': '9/10', 'RECOVERY': '1/20', 'LOST': '1/20'}})
    training = {op: ['DELIVERY'] for op in probe.core.OPERATORS}
    validation = {op: ['LOST'] for op in probe.core.OPERATORS}
    split = dict(training=training, validation=validation,
        training_segments={op: [] for op in training}, validation_segments={op: [] for op in training})
    tape = dict(life=0, index=58, arm='ORACLE_BALANCED', kind='failure', phase='A_RETURN',
        case={'operating': 'low', 'retry_cost': '17/20'}, identity=1,
        fees={'source_paid_samples': 4608, 'history_paid_samples': 8000},
        changed_operator=probe.core.OPERATORS[0], operators={op: training[op]+validation[op] for op in training})
    monkeypatch.setattr(probe.core, 'split_tape', lambda actual: split)
    row = probe.prepare(witness, tape, 'V235_countermodel')
    assert row['fees'] == tape['fees'] and row['parameters']['S']['DELIVERY'] == F(19, 20)
    assert row['training_counts']['S'] == {'DELIVERY': 1, 'LOST': 0}
    assert row['validation_counts']['S'] == {'DELIVERY': 0, 'LOST': 1}
    assert row['row_lengths'][probe.core.OPERATORS[0]] == 2 and row['validation_lengths'][probe.core.OPERATORS[0]] == 1


def test_all_nine_inputs_and_protocol_are_saved_before_any_membership_check(tmp_path, monkeypatch):
    v235, v234, output = [tmp_path/name for name in ('v235', 'v234', 'output')]
    for directory in (v235, v234):
        directory.mkdir()
        (directory/'analysis.json').write_text(json.dumps({'valid': True}))
    (v235/'countermodel_analysis.json').write_text(json.dumps({'valid': True}))
    tapes = [dict(life=0, index=i, arm='ORACLE_BALANCED', kind='failure') for i in range(24)]
    (v235/'countermodels.json').write_text(json.dumps([dict(tape, found=True) for tape in tapes[:6]]))
    (v234/'diagnosis.json').write_text(json.dumps({'terminal_rectangle_witnesses': tapes[6:9]}))
    monkeypatch.setattr(probe, 'V235', v235)
    monkeypatch.setattr(probe, 'V234', v234)
    monkeypatch.setattr(probe, 'OUTPUT', output)
    monkeypatch.setattr(probe, 'read_rows', lambda path: tapes)
    monkeypatch.setattr(probe, 'prepare', lambda row, tape, origin: dict(row, origin=origin))
    captured = []
    monkeypatch.setattr(probe, 'capture', lambda: captured.append(True))

    def classify(row):
        inputs = json.loads((output/'records.json').read_text())
        protocol = json.loads((output/'protocol.json').read_text())
        assert len(inputs) == 9 and all('membership' not in value for value in inputs)
        assert captured and protocol['phases'] == ['protocol_frozen', 'evidence_frozen']
        return dict(row, membership={'exact_inside': True, 'excluded': False})

    monkeypatch.setattr(probe, 'classify', classify)
    summary = probe.run()
    assert not summary['full_qualification_eligible']
    assert summary['qualification_status'] == 'skipped_primary_bad_witness_still_admitted'
    assert not summary['query_certificates_obtained'] and not summary['scientific_gate_changed']
