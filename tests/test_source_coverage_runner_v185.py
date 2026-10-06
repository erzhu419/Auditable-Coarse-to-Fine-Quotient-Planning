"""Detect paired outcome loss and SOURCE/TARGET phase or resource accounting errors."""
import json

import pytest
from scripts import run_controlled_predictive_source_coverage_v185 as runner


def test_paired_effect_counts_risk_success_losses_and_error_changes():
    new, old = [], []
    for i, (a, b) in enumerate((([1., 0., 1.], [1., .5, 0.]), ([0., 1., 0.], [1., 0., 0.]))):
        for rows, vector, regret, action in ((new, a, float(i), 'LEFT'), (old, b, float(1-i), 'DOWN')):
            rows.append(dict(root_id=str(i), models={'SHARED': dict(components=vector,
                utility=runner.statistics.utility(vector), regret=regret, action=action)}))
    effect = runner.paired_effect(new, old, 'SHARED')
    assert effect['components'] == [-.5, .25, .5]
    assert effect['utility'] == -.25
    assert (effect['positive_gain_sum'], effect['negative_gain_sum']) == (1.5, -2.)
    assert effect['improved_roots'] == effect['worsened_roots'] == 1
    assert effect['new_error_roots'] == effect['resolved_error_roots'] == 1
    assert effect['largest_gain_share_of_positive'] == 1.


def test_paired_effect_matches_root_ids_without_using_list_position():
    values = [dict(root_id=str(i), models={'RIDGE': dict(components=[float(i), 0., 0.],
        utility=float(i), regret=0., action='DOWN')}) for i in range(2)]
    effect = runner.paired_effect(values, list(reversed(values)), 'RIDGE')
    assert effect['equal_value_roots'] == 2 and effect['utility'] == 0.
    assert effect['largest_gain_root'] is None and effect['largest_gain_share_of_positive'] is None


def fake_run_inputs(tmp_path, monkeypatch):
    prior = tmp_path/'prior'
    monkeypatch.setattr(runner, 'ROOT', tmp_path); monkeypatch.setattr(runner, 'PREVIOUS', prior)
    runner.save(tmp_path/'reports/v184_runtime_tmp/stage_checks.json', {'valid': True})
    runner.save(prior/'run.json', {'status': 'complete'})
    source = [dict(root_id=f'old:{i}', source_id=f'group:{i%12}') for i in range(47)]
    runner.save(prior/'inputs/inherited/ridge_models.json', {'RIDGE': {'training_outcomes': source}})
    runner.save(prior/'inputs/inherited/baseline_models.json', {name: {} for name in ('LAYOUT', 'SHARED', 'ONE')})
    runner.save(prior/'inputs/inherited/learned_rule.json', {})
    monkeypatch.setattr(runner.LearnedDynamics, 'from_payload', lambda payload: object())
    events = []
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    def cases(split):
        events.append('cases:'+split)
        return [dict(name='synthetic:'+split, split=split)]
    monkeypatch.setattr(runner.core, 'cohort_cases', cases)
    monkeypatch.setattr(runner.core, 'observe_roots', lambda cases: ([{'root_id': cases[0]['name']}], {}))
    monkeypatch.setattr(runner.core, 'cache_roots', lambda roots: {})
    def labels(case, rule):
        events.append('label:'+case['split'])
        return dict(native={}, teacher_policy=[], costs={name: {} for name in (
            'construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation')})
    monkeypatch.setattr(runner.acquisition, 'exact_labels', labels)
    monkeypatch.setattr(runner, 'canonical_labels', lambda root, native, provenance: dict(root))
    def fit(source):
        events.append('fit')
        assert len(source) == 48
        assert all('TARGET' not in row['root_id'] for row in source)
        return dict(selection={'model': {}}, models={}, costs={'new_predictors': 15})
    monkeypatch.setattr(runner.core, 'fit_expanded', fit)
    monkeypatch.setattr(runner.core, 'freeze_choices', lambda *args: events.append('choices') or ({}, {}))
    monkeypatch.setattr(runner, 'summarize', lambda *args: {'complete': True})
    return events


def test_source_labels_fit_models_then_target_boards_choices_and_labels(tmp_path, monkeypatch):
    events = fake_run_inputs(tmp_path, monkeypatch)
    result = runner.run(tmp_path/'out')
    assert events == ['capture', 'cases:SOURCE', 'label:SOURCE', 'fit', 'cases:TARGET', 'choices', 'label:TARGET']
    assert [row['phase'] for row in result['phase_history']] == ['protocol_frozen', 'source_roots',
        'source_labels', 'source_selection', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    assert [row['input_reads'] for row in result['phase_history']] == [0]+[5]*8
    assert result['new_exact_label_roots'] == result['new_reference_kernel_attempts'] == 2
    assert result['new_predictors_fitted'] == 15


def test_failed_source_acquisition_retains_cost_without_fitting_or_opening_target(tmp_path, monkeypatch):
    events = fake_run_inputs(tmp_path, monkeypatch)
    def fail(*args):
        error = ValueError('synthetic cap'); error.counts = {'concrete_states': 200000}; error.elapsed_seconds = .125
        raise error
    monkeypatch.setattr(runner.acquisition, 'exact_labels', fail)
    with pytest.raises(ValueError, match='synthetic cap'):
        runner.run(tmp_path/'out')
    result = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture', 'cases:SOURCE']
    assert result['new_predictors_fitted'] == result['completed_roots'] == 0
    assert result['new_reference_kernel_attempts'] == 1
    assert result['failure']['counts'] == {'concrete_states': 200000}
    assert result['failure']['label_seconds'] == .125
