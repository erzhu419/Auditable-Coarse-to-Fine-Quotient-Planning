"""Synthetic two-arm SOURCE-only selection, compact retention and paid failures."""
import json
import pytest
from scripts import run_controlled_predictive_conditional_pairs_v194 as runner


def fake_inputs(tmp_path, monkeypatch):
    prior, learned = tmp_path/'prior', tmp_path/'learned'
    monkeypatch.setattr(runner, 'ROOT', tmp_path); monkeypatch.setattr(runner, 'PREVIOUS', prior)
    monkeypatch.setattr(runner, 'LEARNED', learned)
    runner.save(tmp_path/'reports/v193_runtime_tmp/stage_checks.json', {'valid': True})
    runner.save(prior/'run.json', {'status': 'complete'})
    source = [dict(root_id=f'source:{i}', source_id=f'group:{i%36}', relation_features={'DOWN': [0.]*98}) for i in range(143)]
    runner.save(prior/'inputs/inherited/roots.json', {'SOURCE': source, 'TARGET': [{'root_id': 'excluded:target'}]})
    runner.save(learned/'model.json', {'old_nonlinear': True})
    runner.save(learned/'inputs/inherited/relation_model.json', {'old_relation': True})
    runner.save(learned/'inputs/inherited/expanded_models.json', {'RIDGE': {}, 'LAYOUT': {}, 'SHARED': {}})
    runner.save(learned/'inputs/inherited/baseline_models.json', {'SHARED': {}, 'ONE': {}})
    runner.save(learned/'inputs/inherited/learned_rule.json', {})
    runner.save(learned/'inputs/inherited/dense_models.json', {'LINEAR': {}, 'INTERACT': {}})
    monkeypatch.setattr(runner.LearnedDynamics, 'from_payload', lambda payload: object())
    events = []
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    def cache(rows):
        cohort = 'source' if rows[0]['root_id'].startswith('source:') else 'target'
        events.append('conditional_cache_'+cohort)
        for row in rows:
            row['conditional_features'] = {}
        return {'conditional_roots_cached': len(rows)}
    monkeypatch.setattr(runner.core, 'cache_roots', cache)
    def fit(rows, mode):
        assert len(rows) == 143 and all(row['root_id'].startswith('source:') for row in rows)
        assert all('conditional_features' in row for row in rows)
        events.append('fit_'+mode)
        return dict(model={'mode': mode, 'constants': {'columns': 224 if mode == 'CONDITIONAL' else 98},
                          'median_squared_distance': 2.},
            selection={'selected_k': 1, 'selected_temperature': .01, 'selected_utility': .6, 'candidates': []},
            costs={'new_predictors_fitted': 19, 'pair_predictor_configurations': 19, 'pair_design_preparations': 3})
    monkeypatch.setattr(runner.core, 'fit_model', fit)
    def actual(rows, model):
        events.append('source_'+model['mode'])
        return dict(metrics={}, root_records=[], projection_residuals={}, work={'source_diagnostic_root_records': len(rows)})
    monkeypatch.setattr(runner, 'source_diagnostics', actual)
    monkeypatch.setattr(runner, 'cohort_cases', lambda: events.append('cases') or [{'name': 'fresh:target'}])
    monkeypatch.setattr(runner.acquisition, 'observe_roots', lambda cases: ([{'root_id': cases[0]['name']}], {}))
    monkeypatch.setattr(runner.coverage, 'cache_roots', lambda roots: events.append('geometry_cache') or {})
    monkeypatch.setattr(runner.relation, 'cache_roots', lambda roots: events.append('relation_cache') or {})
    def choose(roots, models):
        assert set(models) == set(runner.MODEL_NAMES)
        assert models['NONLINEAR'] == {'old_nonlinear': True} and models['RELATION'] == {'old_relation': True}
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


def test_two_source_arms_and_all_frozen_choices_precede_new_labels(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch); record = runner.run(tmp_path/'out')
    assert events == ['capture', 'conditional_cache_source', 'fit_CONDITIONAL', 'source_CONDITIONAL',
        'fit_PAIR98', 'source_PAIR98', 'cases', 'geometry_cache', 'relation_cache', 'conditional_cache_target', 'choices', 'label']
    assert [row['phase'] for row in record['phase_history']] == ['protocol_frozen', 'source_selection',
        'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    assert [row['input_reads'] for row in record['phase_history']] == [0]+[9]*6
    inputs = json.loads((tmp_path/'out/input_manifest.json').read_text())
    assert all(row['phase'] == 'protocol_frozen' for row in inputs)
    assert [row['saved_ref'].split('/')[-1] for row in inputs] == ['v193_stage_checks.json', 'v193_run.json',
        'v193_roots.json', 'nonlinear_model.json', 'relation_model.json', 'expanded_models.json',
        'baseline_models.json', 'learned_rule.json', 'dense_models.json']
    assert record['new_predictors_fitted'] == record['new_prototype_configurations'] == 38
    assert record['new_learning_attempts'] == 2 and record['new_parameter_solves'] == 0
    assert record['new_boards_generated'] == record['new_reference_kernel_attempts'] == record['completed_roots'] == 1
    assert set(json.loads((tmp_path/'out/models.json').read_text())) == set(runner.NEW_MODES)
    assert set(json.loads((tmp_path/'out/selection.json').read_text())) == set(runner.NEW_MODES)


def test_failed_second_fit_keeps_first_arm_and_partial_paid_configuration_cost(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    original = runner.core.fit_model
    def fit(rows, mode):
        if mode == 'CONDITIONAL':
            return original(rows, mode)
        events.append('fit_PAIR98'); error = RuntimeError('synthetic final PAIR98 library failure')
        error.record = {'costs': {'new_predictors_fitted': 18, 'pair_predictor_configurations': 18,
                                  'pair_design_preparations': 3}}
        raise error
    monkeypatch.setattr(runner.core, 'fit_model', fit)
    with pytest.raises(RuntimeError, match='PAIR98 library'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture', 'conditional_cache_source', 'fit_CONDITIONAL', 'source_CONDITIONAL', 'fit_PAIR98']
    assert record['new_predictors_fitted'] == record['new_prototype_configurations'] == 37
    assert record['new_learning_attempts'] == 2 and record['new_boards_generated'] == 0
    assert record['failure']['learning_mode'] == 'PAIR98'
    assert record['costs']['failed_learning']['counts']['pair_design_preparations'] == 3
    assert set(json.loads((tmp_path/'out/models.json').read_text())) == {'CONDITIONAL'}


def test_failed_acquisition_keeps_both_frozen_arms_and_unfinished_attempt(tmp_path, monkeypatch):
    fake_inputs(tmp_path, monkeypatch)
    def fail(*args):
        error = ValueError('synthetic acquisition cap'); error.counts = {'concrete_states': 200000}
        error.elapsed_seconds = .25; raise error
    monkeypatch.setattr(runner.acquisition, 'exact_labels', fail)
    with pytest.raises(ValueError, match='acquisition cap'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert record['new_predictors_fitted'] == 38 and record['new_reference_kernel_attempts'] == 1
    assert record['completed_roots'] == 0 and record['failure']['label_seconds'] == .25


def test_source_label_free_choice_retains_residuals_but_omits_neighbors(monkeypatch):
    root = dict(root_id='source', source_id='group', life=0, canonical_board=[0]*16,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': 0., 'LEFT': 0.}, fallback_action='DOWN',
        action_map={'DOWN': 'DOWN', 'LEFT': 'LEFT'}, layout_features={}, action_features={},
        relation_features={'DOWN': [0.]*98, 'LEFT': [1.]*98}, conditional_features={},
        action_components={'DOWN': [.7, .6, .1], 'LEFT': [.4, 0., .5]})
    def choose(model, seen, counts):
        assert 'action_components' not in seen
        counts.update(pair_decisions=1)
        return dict(canonical_action='DOWN', fallback=False, projection_residual_sse=14., projection_residual_max=3.,
            predicted_components={'DOWN': [.7, .6, .1], 'LEFT': [.4, 0., .5]},
            estimated_pairs={'DOWN|LEFT': {'neighbors': [{'weight': 1.}], 'estimated_tail_delta': [.1, .2, .3],
                                         'projected_tail_delta': [-.9, -1.8, -2.7], 'projection_residual': [-1., -2., -3.]}})
    monkeypatch.setattr(runner.core, 'choose_action', choose)
    result = runner.source_diagnostics([root], {'mode': 'CONDITIONAL'})
    pair = result['root_records'][0]['decision']['estimated_pairs']['DOWN|LEFT']
    assert 'neighbors' not in pair and pair['projection_residual'] == [-1., -2., -3.]
    assert result['root_records'][0]['oracle_action'] == 'LEFT' and result['root_records'][0]['regret'] == pytest.approx(.7)
    assert result['projection_residuals']['mean_abs_components'] == [1., 2., 3.]
    assert result['projection_residuals']['max_abs_components'] == [1., 2., 3.]
    assert result['projection_residuals']['utility_sign_flips'] == 1
    assert result['metrics']['positive_regret_roots'] == 1 and result['work']['pair_decisions'] == 1


def test_frozen_96_root_seed_roster_with_synthetic_rng(monkeypatch):
    seeds = []
    class MockRng:
        def __init__(self, seed): seeds.append(seed)
        def randint(self, *args): return 7
        def sample(self, values, k): return values[:k]
    monkeypatch.setattr(runner.random, 'Random', MockRng)
    cases = runner.cohort_cases()
    assert seeds == list(range(1940200, 1940296)) and len(cases) == 96
    assert cases[0]['name'] == 'v194_target_r00_00' and cases[-1]['name'] == 'v194_target_r03_23'
    assert all(row['board'].count(0) == row['stratum']%3 and row['horizon'] == 3 for row in cases)
