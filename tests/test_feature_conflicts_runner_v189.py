"""Synthetic retained-data phases and failed-capacity paid work."""
import json
import pytest
from scripts import run_controlled_predictive_feature_conflicts_v189 as runner


def fake_inputs(tmp_path, monkeypatch):
    prior = tmp_path/'prior'
    monkeypatch.setattr(runner, 'ROOT', tmp_path); monkeypatch.setattr(runner, 'PREVIOUS', prior)
    runner.save(tmp_path/'reports/v188_runtime_tmp/stage_checks.json', {'valid': True})
    runner.save(prior/'run.json', {'status': 'complete'})
    roots = {'SOURCE': [{'root_id': f's:{i}'} for i in range(143)],
             'TARGET': [{'root_id': f't:{i}'} for i in range(96)]}
    runner.save(prior/'roots.json', roots)
    runner.save(prior/'labels.json', [{'root_id': f't:{i}'} for i in range(96)])
    runner.save(prior/'summary.json', {'roots': 96})
    events = []
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    def diagnostics(roots, labels, summary):
        assert len(roots['TARGET']) == len(labels) == summary['roots'] == 96
        events.append('diagnostics')
        return dict(problem={'roots': roots['TARGET']}, alias={}, coverage={}, costs={'tuple_reads': 12})
    monkeypatch.setattr(runner.core, 'build_diagnostics', diagnostics)
    def solve(problem):
        events.append('capacity')
        return dict(status='weak_infeasible', costs={'lp_solves': 1, 'symbolic_balance_solves': 1})
    monkeypatch.setattr(runner.capacity_backend, 'solve_capacity', solve)
    monkeypatch.setattr(runner.core, 'summarize', lambda *args: events.append('summary') or {'complete': True, 'work': {}})
    return events


def test_freeze_before_retained_inputs_and_only_one_target_scope(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    result = runner.run(tmp_path/'out')
    assert events == ['capture', 'diagnostics', 'capacity', 'summary']
    assert [row['phase'] for row in result['phase_history']] == [
        'protocol_frozen', 'retained_inputs', 'diagnostics_frozen', 'target_capacity', 'complete']
    assert [row['input_reads'] for row in result['phase_history']] == [0, 5, 5, 5, 5]
    inputs = json.loads((tmp_path/'out/input_manifest.json').read_text())
    assert [row['phase'] for row in inputs] == ['protocol_frozen']*5
    assert result['new_capacity_attempts'] == result['new_capacity_scopes'] == result['new_lp_solves'] == 1
    assert all(result[name] == 0 for name in ('new_environment_samples', 'new_source_games',
        'new_native_weight_updates', 'new_predictors_fitted', 'new_reference_kernels', 'new_exact_label_roots'))


def test_failed_capacity_keeps_attempt_and_paid_solver_work(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    def fail(problem):
        events.append('capacity')
        error = RuntimeError('synthetic exact dual balance failure')
        error.record = dict(status='execution_error', costs={'lp_solves': 2, 'symbolic_balance_solves': 2})
        raise error
    monkeypatch.setattr(runner.capacity_backend, 'solve_capacity', fail)
    with pytest.raises(RuntimeError, match='dual balance'):
        runner.run(tmp_path/'out')
    result = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture', 'diagnostics', 'capacity']
    assert result['status'] == 'failed' and result['new_capacity_attempts'] == 1
    assert result['new_capacity_scopes'] == 0 and result['new_lp_solves'] == 2
    assert result['costs']['failed_capacity']['symbolic_balance_solves'] == 2
    assert json.loads((tmp_path/'out/failed_capacity.json').read_text())['status'] == 'execution_error'


def test_incomplete_prior_stops_before_diagnostics_or_capacity(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    runner.save(tmp_path/'reports/v188_runtime_tmp/stage_checks.json', {'valid': False})
    with pytest.raises(ValueError, match='incomplete'):
        runner.run(tmp_path/'out')
    result = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture'] and result['new_capacity_attempts'] == 0
    assert result['costs']['input_counts']['json_read_operations'] == 2
