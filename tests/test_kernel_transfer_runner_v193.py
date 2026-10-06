"""Synthetic retained-input freeze, complete cohort and paid diagnostic failures."""
import json
import pytest
from scripts import run_controlled_predictive_kernel_transfer_v193 as runner


def fake_inputs(tmp_path, monkeypatch):
    prior = tmp_path/'prior'
    monkeypatch.setattr(runner, 'ROOT', tmp_path); monkeypatch.setattr(runner, 'PREVIOUS', prior)
    runner.save(tmp_path/'reports/v192_runtime_tmp/corrected_stage_checks.json', {'valid': True})
    runner.save(prior/'run.json', {'status': 'complete'})
    runner.save(prior/'model.json', {'retained_model': True})
    roots = {'SOURCE': [{'root_id': f's:{i}', 'source_id': f'g:{i%36}'} for i in range(143)],
             'TARGET': [{'root_id': f't:{i}', 'source_id': f'tg:{i}'} for i in range(96)]}
    runner.save(prior/'roots.json', roots)
    runner.save(prior/'choices.json', {'NONLINEAR': [{'root_id': f't:{i}'} for i in range(96)]})
    runner.save(prior/'labels.json', [{'root_id': f't:{i}'} for i in range(96)])
    runner.save(prior/'summary.json', {'retained_summary': True})
    runner.save(prior/'source_diagnostics.json', {'retained_source_diagnostics': True})
    events = []
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    def diagnose(model, roots, choices, labels, summary, source):
        events.append('diagnose')
        assert model == {'retained_model': True} and len(roots['SOURCE']) == 143
        assert [row['root_id'] for row in roots['TARGET']] == [row['root_id'] for row in labels] == [
            row['root_id'] for row in choices['NONLINEAR']]
        assert len(labels) == 96 and summary == {'retained_summary': True}
        assert source == {'retained_source_diagnostics': True}
        return dict(schema='acfqp.kernel_transfer.v193', complete=True, parameters={'gamma': 1.},
            reference={'pairs': 12}, root_records=[{'root_id': row['root_id']} for row in roots['TARGET']],
            summary={'roots': 96}, costs={'target_kernel_exponentials': 120})
    monkeypatch.setattr(runner.core, 'diagnose', diagnose)
    return events


def test_source_frozen_before_eight_inputs_and_one_complete_cohort_call(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch); record = runner.run(tmp_path/'out')
    assert events == ['capture', 'diagnose']
    assert [row['phase'] for row in record['phase_history']] == ['protocol_frozen', 'inputs_retained',
        'source_reference', 'target_diagnostics', 'complete']
    assert [row['input_reads'] for row in record['phase_history']] == [0, 8, 8, 8, 8]
    inputs = json.loads((tmp_path/'out/input_manifest.json').read_text())
    assert [row['saved_ref'].split('/')[-1] for row in inputs] == ['v192_stage_checks.json', 'run.json',
        'model.json', 'roots.json', 'choices.json', 'labels.json', 'summary.json', 'source_diagnostics.json']
    assert all(row['phase'] == 'protocol_frozen' for row in inputs)
    assert record['diagnostic_attempts'] == 1 and record['diagnostic_complete']
    assert record['costs']['diagnostics']['counts'] == {'target_kernel_exponentials': 120}
    assert all(record[key] == 0 for key in ('new_predictors_fitted', 'new_solve_attempts',
        'new_eigen_decompositions', 'new_svd_decompositions', 'new_feature_derivations', 'new_source_games',
        'new_boards_generated', 'new_reference_kernels', 'new_exact_label_roots', 'new_environment_samples', 'new_native_weight_updates'))
    diagnostics = json.loads((tmp_path/'out/diagnostics.json').read_text())
    assert len(diagnostics['root_records']) == 96
    assert json.loads((tmp_path/'out/reference.json').read_text()) == diagnostics['reference']
    assert json.loads((tmp_path/'out/summary.json').read_text()) == diagnostics['summary']


def test_failed_diagnostic_keeps_attempt_elapsed_and_paid_counts(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    def fail(*args):
        events.append('diagnose'); error = RuntimeError('synthetic retained prediction mismatch')
        error.counts = {'target_kernel_exponentials': 24}; raise error
    monkeypatch.setattr(runner.core, 'diagnose', fail)
    with pytest.raises(RuntimeError, match='prediction mismatch'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture', 'diagnose'] and record['status'] == 'failed'
    assert record['diagnostic_attempts'] == 1 and not record['diagnostic_complete']
    assert record['costs']['failed_diagnostics']['counts'] == {'target_kernel_exponentials': 24}
    assert record['costs']['failed_diagnostics']['seconds'] >= 0
    assert record['costs']['input_counts']['json_read_operations'] == 8
    assert not (tmp_path/'out/summary.json').exists()


def test_incomplete_corrected_stage_stops_before_model_or_diagnostic(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    runner.save(tmp_path/'reports/v192_runtime_tmp/corrected_stage_checks.json', {'valid': False})
    with pytest.raises(ValueError, match='incomplete'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture'] and record['diagnostic_attempts'] == 0
    assert record['costs']['input_counts']['json_read_operations'] == 2


def test_roster_mismatch_stops_before_reference_or_model_replay(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    runner.save(tmp_path/'prior/labels.json', [{'root_id': 't:0'}])
    with pytest.raises(ValueError, match='SOURCE143'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture'] and record['diagnostic_attempts'] == 0
    assert record['costs']['input_counts']['json_read_operations'] == 8
