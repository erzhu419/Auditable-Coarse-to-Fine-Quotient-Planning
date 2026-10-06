"""Synthetic SOURCE-only fitting, fresh-choice freeze and retained paid work."""
import json
import pytest
from scripts import run_controlled_predictive_nonlinear_relations_v192 as runner


def fake_inputs(tmp_path, monkeypatch):
    prior, learned = tmp_path/'prior', tmp_path/'learned'
    monkeypatch.setattr(runner, 'ROOT', tmp_path); monkeypatch.setattr(runner, 'PREVIOUS', prior)
    monkeypatch.setattr(runner, 'LEARNED', learned)
    runner.save(tmp_path/'reports/v191_runtime_tmp/stage_checks.json', {'valid': True})
    runner.save(prior/'run.json', {'status': 'complete'})
    source = [dict(root_id=f'source:{i}', source_id=f'group:{i%36}', relation_features={'DOWN': [0.]*98}) for i in range(143)]
    runner.save(prior/'roots.json', {'SOURCE': source, 'TARGET': [{'root_id': 'excluded:target'}]})
    runner.save(learned/'model.json', {'old_relation': True})
    runner.save(learned/'inputs/inherited/expanded_models.json', {'RIDGE': {}, 'LAYOUT': {}, 'SHARED': {}})
    runner.save(learned/'inputs/inherited/baseline_models.json', {'SHARED': {}, 'ONE': {}})
    runner.save(learned/'inputs/inherited/learned_rule.json', {})
    runner.save(learned/'inputs/inherited/v188_models.json', {'LINEAR': {}, 'INTERACT': {}})
    monkeypatch.setattr(runner.LearnedDynamics, 'from_payload', lambda payload: object())
    events = []
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    def fit(rows):
        assert len(rows) == 143 and all(row['root_id'].startswith('source:') for row in rows)
        assert all('relation_features' in row for row in rows)
        events.append('fit')
        return dict(model={'rank': 4, 'root_mean_loss': .2, 'median_squared_distance': 2.},
            selection={'selected_gamma': 1., 'selected_lambda': .01, 'selected_utility': .6, 'candidates': []},
            costs={'new_predictors_fitted': 31, 'nonlinear_eigh_attempts': 7})
    monkeypatch.setattr(runner.core, 'fit_model', fit)
    def source(rows, model):
        assert len(rows) == 143 and model['rank'] == 4
        events.append('source_diagnostics'); return dict(metrics={}, root_records=[], work={'source_diagnostic_root_records': 143})
    monkeypatch.setattr(runner, 'source_diagnostics', source)
    monkeypatch.setattr(runner, 'cohort_cases', lambda: events.append('cases') or [{'name': 'fresh:target'}])
    monkeypatch.setattr(runner.acquisition, 'observe_roots', lambda cases: ([{'root_id': cases[0]['name']}], {}))
    monkeypatch.setattr(runner.coverage, 'cache_roots', lambda roots: events.append('geometry_cache') or {})
    monkeypatch.setattr(runner.relation, 'cache_roots', lambda roots: events.append('relation_cache') or {})
    def choose(roots, models):
        assert set(models) == set(runner.MODEL_NAMES) and models['RELATION'] == {'old_relation': True}
        assert roots[0]['root_id'] == 'fresh:target'
        events.append('choices'); return {}, {}
    monkeypatch.setattr(runner, 'freeze_choices', choose)
    def label(*args):
        events.append('label')
        return dict(native={}, teacher_policy=[], costs={kind: {} for kind in
            ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation')})
    monkeypatch.setattr(runner.acquisition, 'exact_labels', label)
    monkeypatch.setattr(runner, 'canonical_labels', lambda root, *args: dict(root))
    monkeypatch.setattr(runner, 'summarize', lambda *args: {'complete': True})
    return events


def test_source_fit_frozen_before_fresh_roster_and_all_choices_precede_labels(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch); record = runner.run(tmp_path/'out')
    assert events == ['capture', 'fit', 'source_diagnostics', 'cases', 'geometry_cache', 'relation_cache', 'choices', 'label']
    assert [row['phase'] for row in record['phase_history']] == ['protocol_frozen', 'source_selection',
        'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    assert [row['input_reads'] for row in record['phase_history']] == [0]+[8]*6
    inputs = json.loads((tmp_path/'out/input_manifest.json').read_text())
    assert all(row['phase'] == 'protocol_frozen' for row in inputs)
    assert [row['saved_ref'].split('/')[-1] for row in inputs] == ['v191_stage_checks.json', 'v191_run.json',
        'v191_roots.json', 'relation_model.json', 'expanded_models.json', 'baseline_models.json', 'learned_rule.json', 'dense_models.json']
    assert record['new_predictors_fitted'] == 31 and record['new_learning_attempts'] == 1
    assert record['new_boards_generated'] == record['new_reference_kernel_attempts'] == record['completed_roots'] == 1
    assert all(record[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates'))


def test_failed_fit_keeps_paid_predictors_and_eigh_attempts_without_opening_roster(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    def fail(*args):
        events.append('fit'); error = RuntimeError('synthetic seventh eigendecomposition failure')
        error.record = {'costs': {'new_predictors_fitted': 30, 'nonlinear_eigh_attempts': 7}}
        raise error
    monkeypatch.setattr(runner.core, 'fit_model', fail)
    with pytest.raises(RuntimeError, match='seventh'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture', 'fit'] and record['new_predictors_fitted'] == 30
    assert record['new_boards_generated'] == record['new_reference_kernel_attempts'] == 0
    assert record['costs']['failed_learning']['nonlinear_eigh_attempts'] == 7


def test_failed_acquisition_keeps_frozen_model_and_unfinished_attempt(tmp_path, monkeypatch):
    fake_inputs(tmp_path, monkeypatch)
    def fail(*args):
        error = ValueError('synthetic acquisition cap'); error.counts = {'concrete_states': 200000}
        error.elapsed_seconds = .25; raise error
    monkeypatch.setattr(runner.acquisition, 'exact_labels', fail)
    with pytest.raises(ValueError, match='acquisition cap'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert record['new_predictors_fitted'] == 31 and record['new_reference_kernel_attempts'] == 1
    assert record['completed_roots'] == 0 and record['failure']['label_seconds'] == .25
    assert record['failure']['counts']['concrete_states'] == 200000


def test_source_actual_full_rfs_chooser_receives_observable_features_without_labels(monkeypatch):
    root = dict(root_id='source', source_id='group', life=0, canonical_board=[0]*16,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': 0., 'LEFT': 0.}, fallback_action='DOWN',
        action_map={'DOWN': 'DOWN', 'LEFT': 'LEFT'}, layout_features={}, action_features={},
        relation_features={'DOWN': [0.]*98, 'LEFT': [1.]*98},
        action_components={'DOWN': [.7, .6, .1], 'LEFT': [.4, 0., .5]})
    def choose(model, seen, counts):
        assert 'action_components' not in seen and seen['relation_features'] == root['relation_features']
        counts.update(nonlinear_decisions=1)
        return dict(canonical_action='DOWN', fallback=False, predicted_components={'DOWN': [.7, .6, .1], 'LEFT': [.4, 0., .5]})
    monkeypatch.setattr(runner.core, 'choose_action', choose)
    result = runner.source_diagnostics([root], {'retained': True})
    assert result['root_records'][0]['oracle_action'] == 'LEFT' and result['root_records'][0]['regret'] == pytest.approx(.7)
    assert result['metrics']['positive_regret_roots'] == 1 and result['work']['nonlinear_decisions'] == 1


def test_frozen_96_root_seed_roster_with_synthetic_rng(monkeypatch):
    seeds = []
    class MockRng:
        def __init__(self, seed): seeds.append(seed)
        def randint(self, *args): return 7
        def sample(self, values, k): return values[:k]
    monkeypatch.setattr(runner.random, 'Random', MockRng)
    cases = runner.cohort_cases()
    assert seeds == list(range(1920200, 1920296)) and len(cases) == 96
    assert cases[0]['name'] == 'v192_target_r00_00' and cases[-1]['name'] == 'v192_target_r03_23'
    assert all(row['board'].count(0) == row['stratum']%3 and row['horizon'] == 3 for row in cases)
