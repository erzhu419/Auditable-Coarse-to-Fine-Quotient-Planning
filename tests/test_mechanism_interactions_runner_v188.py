"""Check source/choice isolation and retained failed optimizer/acquisition costs."""
import json
import pytest
from scripts import run_controlled_predictive_mechanism_interactions_v188 as runner


def fake_inputs(tmp_path, monkeypatch):
    prior = tmp_path/'prior'
    monkeypatch.setattr(runner, 'ROOT', tmp_path); monkeypatch.setattr(runner, 'PREVIOUS', prior)
    runner.save(tmp_path/'reports/v187_runtime_tmp/stage_checks.json', {'valid': True})
    runner.save(prior/'run.json', {'status': 'complete'})
    source = [dict(root_id=f'source:{i}', source_id=f'group:{i%36}') for i in range(143)]
    runner.save(prior/'source_labels.json', source)
    runner.save(prior/'inputs/inherited/expanded_models.json', {'RIDGE': {'constants': {'lambda_value': .1}}, 'LAYOUT': {}, 'SHARED': {}})
    runner.save(prior/'inputs/inherited/baseline_models.json', {'SHARED': {}, 'ONE': {}})
    runner.save(prior/'inputs/inherited/learned_rule.json', {})
    monkeypatch.setattr(runner.LearnedDynamics, 'from_payload', lambda payload: object())
    events = []
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    def fit(source):
        assert len(source) == 143 and all(row['root_id'].startswith('source:') for row in source)
        events.append('fit')
        return dict(models={name: {'constants': {'columns': columns}, 'rank': 2, 'root_mean_loss': .1}
            for name, columns in (('LINEAR', 6), ('INTERACT', 26))},
            selections={name: dict(selected_lambda=.1, selected_utility=.5, candidates=[{'lambda_value': .1, 'utility': .5}])
            for name in ('LINEAR', 'INTERACT')}, costs={'ridge_predictors_fitted': 26})
    monkeypatch.setattr(runner.core, 'fit_models', fit)
    monkeypatch.setattr(runner.core, 'cohort_cases', lambda: events.append('cases') or [{'name': 'synthetic:target'}])
    monkeypatch.setattr(runner.core, 'observe_roots', lambda cases: ([{'root_id': cases[0]['name']}], {}))
    monkeypatch.setattr(runner.core, 'cache_roots', lambda roots: {})
    def choose(roots, models):
        assert set(models) == {'INTERACT', 'LINEAR', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE'}
        events.append('choices'); return {}, {}
    monkeypatch.setattr(runner.core, 'freeze_choices', choose)
    def labels(case, rule):
        events.append('label')
        return dict(native={}, teacher_policy=[], costs={name: {} for name in (
            'construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation')})
    monkeypatch.setattr(runner.acquisition, 'exact_labels', labels)
    monkeypatch.setattr(runner, 'canonical_labels', lambda root, *args: dict(root))
    monkeypatch.setattr(runner, 'summarize', lambda *args: {'complete': True})
    return events


def test_fit_then_new_boards_then_all_choices_then_labels(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    result = runner.run(tmp_path/'out')
    assert events == ['capture', 'fit', 'cases', 'choices', 'label']
    assert [row['phase'] for row in result['phase_history']] == ['protocol_frozen', 'source_selection',
        'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    assert [row['input_reads'] for row in result['phase_history']] == [0]+[6]*6
    assert result['new_predictors_fitted'] == 26 and result['new_learning_attempts'] == 1
    assert result['new_boards_generated'] == result['new_reference_kernel_attempts'] == result['completed_roots'] == 1


def test_failed_selection_retains_paid_work_and_never_opens_target(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    def fail(*args):
        events.append('fit')
        error = RuntimeError('synthetic second SVD failure')
        error.record = dict(costs={'ridge_predictors_fitted': 4, 'ridge_svd_attempts': 2})
        raise error
    monkeypatch.setattr(runner.core, 'fit_models', fail)
    with pytest.raises(RuntimeError, match='second SVD'):
        runner.run(tmp_path/'out')
    result = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture', 'fit']
    assert result['new_learning_attempts'] == 1
    assert result['new_predictors_fitted'] == 4
    assert result['new_boards_generated'] == result['new_reference_kernel_attempts'] == 0
    assert result['costs']['failed_learning']['ridge_svd_attempts'] == 2
    assert json.loads((tmp_path/'out/failed_learning.json').read_text())['costs']['ridge_predictors_fitted'] == 4


def test_failed_target_kernel_preserves_attempt_and_fit(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    def fail(*args):
        error = ValueError('synthetic acquisition cap'); error.counts = {'concrete_states': 200000}
        error.elapsed_seconds = .25; raise error
    monkeypatch.setattr(runner.acquisition, 'exact_labels', fail)
    with pytest.raises(ValueError, match='acquisition cap'):
        runner.run(tmp_path/'out')
    result = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture', 'fit', 'cases', 'choices']
    assert result['new_predictors_fitted'] == 26 and result['new_reference_kernel_attempts'] == 1
    assert result['completed_roots'] == 0 and result['failure']['label_seconds'] == .25
    assert result['failure']['counts'] == {'concrete_states': 200000}


def test_summary_uses_actual_full_vectors_for_interactions_and_all_controls():
    roots = {'SOURCE': [{'source_id': 's'}], 'TARGET': [dict(root_id='target', replica=0, stratum=0,
        legal_actions=['DOWN', 'LEFT'])]}
    labels = [dict(root_id='target', action_components={'DOWN': [1., .2, .3], 'LEFT': [1.1, .5, .4]})]
    choices = {name: [dict(root_id='target', canonical_action='DOWN' if name == 'INTERACT' else 'LEFT',
        fallback=False, decision={})]
        for name in (*runner.core.MODEL_NAMES, 'FALLBACK')}
    selection = {name: dict(selected_lambda=.1, selected_utility=.5, candidates=[{'lambda_value': .1, 'utility': .5}])
        for name in ('LINEAR', 'INTERACT')}
    models = {name: dict(constants={'columns': columns}, rank=2, root_mean_loss=.1)
        for name, columns in (('LINEAR', 6), ('INTERACT', 26))}
    result = runner.summarize(roots, labels, choices, selection, models)
    assert result['models']['INTERACT']['components'] == [1., .2, .3]
    assert result['models']['RIDGE']['components'] == [1.1, .5, .4]
    assert result['comparisons']['INTERACT_MINUS_RIDGE']['utility'] == pytest.approx(.1)
    assert result['comparisons']['INTERACT_MINUS_RIDGE']['resolved_error_roots'] == 1
    assert set(result['models']) == set(runner.MODELS)
    assert result['SOURCE']['learners']['INTERACT']['columns'] == 26
    assert result['SOURCE']['learners']['LINEAR']['columns'] == 6
    assert 'feature_coverage' not in result
