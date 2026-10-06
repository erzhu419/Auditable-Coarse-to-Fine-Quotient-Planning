"""Detect loss of complete outcomes, negative roots, weighting or freeze order."""
import json

import pytest
from scripts import run_controlled_predictive_fresh_h3_confirmation_v184 as runner


def fixture():
    roots, labels = [], []
    choices = {name: [] for name in ('RIDGE', 'LAYOUT', 'SHARED', 'ONE', 'FALLBACK')}
    for i, (replica, gain) in enumerate(((0, 4.), (0, -1.), (1, -1.))):
        root_id = f'synthetic:{i}'
        roots.append(dict(root_id=root_id, replica=replica, stratum=i,
            legal_actions=['DOWN', 'LEFT']))
        labels.append(dict(root_id=root_id, action_components={'DOWN': [2., .5, .25],
            'LEFT': [2.+gain, .5, .25]}))
        for name, rows in choices.items():
            rows.append(dict(root_id=root_id, canonical_action='LEFT' if name == 'RIDGE' else 'DOWN',
                fallback=False, decision=dict(coverage={'LEFT': dict(total_tokens=40, known_tokens=39, unknown_tokens=1)})))
    return roots, labels, choices


def test_complete_vectors_negative_roots_concentration_and_replica_weighting():
    summary = runner.summarize(*fixture())
    comparison = summary['comparisons']['RIDGE_MINUS_ONE']
    assert comparison['components'] == pytest.approx([2/3, 0, 0])
    assert comparison['utility'] == pytest.approx(2/3)
    assert (comparison['improved_roots'], comparison['worsened_roots']) == (1, 2)
    assert (comparison['positive_gain_sum'], comparison['negative_gain_sum']) == (4., -2.)
    assert comparison['largest_gain_share_of_positive'] == 1.
    assert summary['whole_cohort_positive_vs_one_and_shared']
    assert not summary['all_replicas_positive_vs_one_and_shared']
    assert summary['replicas'][0]['comparisons']['RIDGE_MINUS_ONE']['utility'] == 1.5
    assert summary['replicas'][1]['comparisons']['RIDGE_MINUS_ONE']['utility'] == -1.
    assert summary['feature_coverage']['unknown_tokens'] == 3


def test_risk_and_success_can_reverse_reward_only_ranking_and_zero_gain_is_retained():
    roots, labels, choices = fixture()
    for label in labels:
        label['action_components'] = {'DOWN': [1., 1., 0.], 'LEFT': [.5, 0., 1.]}
    result = runner.summarize(roots, labels, choices)
    assert result['models']['ORACLE']['utility'] == 1.5
    assert result['comparisons']['RIDGE_MINUS_ONE']['components'] == [-.5, -1., 1.]
    for rows in choices.values():
        for row in rows:
            row['canonical_action'] = 'LEFT'
    result = runner.summarize(roots, labels, choices)
    assert result['headroom_closed_fraction'] is None
    assert result['comparisons']['RIDGE_MINUS_ONE']['largest_gain_share_of_positive'] is None
    assert result['comparisons']['RIDGE_MINUS_ONE']['equal_value_roots'] == 3


def fake_inputs(tmp_path, monkeypatch):
    previous, baselines = tmp_path/'prior', tmp_path/'baseline'
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'PREVIOUS', previous)
    monkeypatch.setattr(runner, 'BASELINES', baselines)
    runner.save(tmp_path/'reports/v183_runtime_tmp/stage_checks.json', {'valid': True})
    runner.save(previous/'run.json', {'status': 'complete'})
    runner.save(previous/'models.json', {'RIDGE': {'constants': {'lambda_value': .1}}})
    runner.save(baselines/'models.json', {name: {'name': name} for name in ('LAYOUT', 'SHARED', 'ONE', 'RAW')})
    runner.save(tmp_path/'reports/controlled_predictive_composition_v69/learned_rule.json', {})
    monkeypatch.setattr(runner.LearnedDynamics, 'from_payload', lambda payload: object())
    events = []
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    monkeypatch.setattr(runner.core, 'fresh_cases', lambda: events.append('cases') or [{'name': 'synthetic'}])
    monkeypatch.setattr(runner.core, 'observe_roots', lambda cases: ([{'root_id': 'synthetic'}], {'synthetic': 1}))
    monkeypatch.setattr(runner.core, 'freeze_choices', lambda roots, models: events.append('choices') or ({}, {}))
    monkeypatch.setattr(runner, 'summarize', lambda *args: {'complete': True})
    monkeypatch.setattr(runner, 'canonical_labels', lambda root, native, provenance: {'root_id': root['root_id']})
    return events


def test_models_and_all_choices_are_frozen_before_any_exact_labels(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    def label(case, rule):
        events.append('label')
        return dict(native={}, teacher_policy=[], costs={
            'construction': {'concrete_states': 2, 'concrete_states_by_h': {'0': 1}},
            'planning': {}, 'label_evaluation': {}, 'teacher_export': {}, 'compilation': {}})
    monkeypatch.setattr(runner.core, 'exact_labels', label)
    output = tmp_path/'out'; result = runner.run(output)
    assert events == ['capture', 'cases', 'choices', 'label']
    assert [(p['phase'], p['input_reads']) for p in result['phase_history']] == [
        ('protocol_frozen', 0), ('models_frozen', 5), ('target_choices_frozen', 5), ('target_labels', 5), ('complete', 5)]
    assert result['new_reference_kernel_attempts'] == result['new_exact_label_roots'] == 1
    assert result['costs']['labels']['counts'] == {'construction.concrete_states': 2}
    baseline = json.loads((output/'inputs/inherited/baseline_models.json').read_text())
    assert set(baseline) == {'LAYOUT', 'SHARED', 'ONE'}


def test_resource_failure_retains_the_failed_attempt_and_paid_work(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    def fail(case, rule):
        error = ValueError('synthetic cap')
        error.counts = {'concrete_observations': 3}
        error.elapsed_seconds = .25
        raise error
    monkeypatch.setattr(runner.core, 'exact_labels', fail)
    output = tmp_path/'out'
    with pytest.raises(ValueError, match='synthetic cap'):
        runner.run(output)
    record = json.loads((output/'run.json').read_text())
    assert record['status'] == 'failed'
    assert record['new_reference_kernel_attempts'] == 1
    assert record['completed_roots'] == 0
    assert record['failure']['counts']['concrete_observations'] == 3
    assert record['failure']['label_seconds'] == .25
    assert events == ['capture', 'cases', 'choices']
