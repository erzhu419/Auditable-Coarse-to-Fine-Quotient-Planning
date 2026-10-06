"""Synthetic SOURCE-only utility learning, frozen controls and paid acquisition."""
import json
import pytest
from scripts import run_controlled_predictive_utility_program_partition_v198 as runner


def fake_inputs(tmp_path, monkeypatch):
    prior, source_prior = tmp_path/'prior', tmp_path/'source_prior'
    monkeypatch.setattr(runner, 'ROOT', tmp_path); monkeypatch.setattr(runner, 'PREVIOUS', prior)
    monkeypatch.setattr(runner, 'SOURCE_PREVIOUS', source_prior)
    runner.save(tmp_path/'reports/v197_runtime_tmp/stage_checks.json', {'valid': True})
    runner.save(prior/'run.json', {'status': 'complete'})
    runner.save(prior/'summary.json', {'SOURCE': {'roots': 143, 'design_groups': 36}})
    source = [dict(root_id=f'source:{i}', source_id=f'group:{i%36}', program_contracts={'cached': True}) for i in range(143)]
    runner.save(source_prior/'roots.json', {'SOURCE': source, 'TARGET': [{'root_id': 'excluded:target'}]})
    runner.save(source_prior/'selection.json', {'PROGRAM': {'selected_utility': 1.269}})
    inherited = prior/'inputs/inherited'
    runner.save(inherited/'program_models.json', {mode: {'frozen_program': mode} for mode in runner.previous.NEW_MODES})
    runner.save(inherited/'program_libraries.json', {name: {'library_id': name} for name in ('FOLD_0', 'FOLD_1', 'FULL')})
    runner.save(inherited/'region_models.json', {'TREE32': {}, 'RAW32': {}})
    runner.save(inherited/'region_libraries.json', {'FULL': {'old_region': True}})
    runner.save(inherited/'conditional_models.json', {'CONDITIONAL': {}, 'PAIR98': {}})
    runner.save(inherited/'nonlinear_model.json', {'frozen_nonlinear': True})
    runner.save(inherited/'relation_model.json', {'frozen_relation': True})
    runner.save(inherited/'expanded_models.json', {'RIDGE': {}, 'LAYOUT': {}, 'SHARED': {'expanded': True}})
    runner.save(inherited/'baseline_models.json', {'SHARED': {'old': True}, 'ONE': {}})
    runner.save(inherited/'learned_rule.json', {})
    runner.save(inherited/'dense_models.json', {'LINEAR': {}, 'INTERACT': {}})
    monkeypatch.setattr(runner.LearnedDynamics, 'from_payload', lambda payload: object())
    events = []
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    def fit(rows, libraries):
        assert rows == source and set(libraries) == {'FOLD_0', 'FOLD_1', 'FULL'}
        events.append('fit_source_cached')
        return dict(models={'UTILITY': {'mode': 'UTILITY', 'library_id': 'FULL'}}, selection={'UTILITY': {}},
            costs={'new_predictors_fitted': 17, 'tree_predictors_fitted': 17, 'shared_library_preparations': 0,
                   'training_view_preparations': 3})
    monkeypatch.setattr(runner.core, 'fit_models', fit)
    def actual(rows, model, library):
        assert rows == source and model['mode'] == 'UTILITY' and library == {'library_id': 'FULL'}
        events.append('source_UTILITY')
        return dict(metrics={}, projection_residuals={}, root_records=[], work={'source_diagnostic_root_records': len(rows)})
    monkeypatch.setattr(runner, 'source_diagnostics', actual)
    monkeypatch.setattr(runner, 'cohort_cases', lambda: events.append('cases') or [{'name': 'fresh:0'}, {'name': 'fresh:1'}])
    def observe(cases):
        return [dict(root_id=row['name'], source_id=row['name'], life=0, canonical_board=[0]*16,
            legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': 0., 'LEFT': 0.}, fallback_action='DOWN',
            action_map={'DOWN': 'DOWN', 'LEFT': 'LEFT'}, layout_features={}, action_features={}, relation_features={},
            conditional_features={}, raw_afterstates={}, program_contracts={}) for row in cases], {}
    monkeypatch.setattr(runner.acquisition, 'observe_roots', observe)
    for module, name in ((runner.coverage, 'geometry'), (runner.relation, 'relation'),
                         (runner.conditional, 'conditional'), (runner.region, 'raw')):
        monkeypatch.setattr(module, 'cache_roots', lambda rows, name=name: events.append(name+'_cache') or {})
    def cache(rows, rule):
        assert all(row['root_id'].startswith('fresh:') for row in rows)
        events.append('program_cache_target'); return {'program_cache_roots_built': len(rows)}
    monkeypatch.setattr(runner.trace, 'cache_roots', cache)
    def old_choices(rows, models, libraries, region_libraries):
        assert set(models) == set(runner.previous.MODEL_NAMES)
        assert all(models[mode] == {'frozen_program': mode} for mode in runner.previous.NEW_MODES)
        assert libraries['FULL'] == {'library_id': 'FULL'} and region_libraries['FULL'] == {'old_region': True}
        assert models['SHARED'] == {'expanded': True} and models['OLD_SHARED'] == {'old': True}
        events.append('old_choices')
        return {mode: [dict(root_id=row['root_id'], canonical_action='DOWN', actual_action='DOWN', fallback=False,
            decision={'work': {}}) for row in rows] for mode in (*runner.previous.MODEL_NAMES, 'FALLBACK')}, {'frozen_model_choices': 16*len(rows)}
    monkeypatch.setattr(runner.previous, 'freeze_choices', old_choices)
    def choose(model, seen, library):
        assert 'action_components' not in seen and model['mode'] == 'UTILITY' and library == {'library_id': 'FULL'}
        events.append('choice_UTILITY_'+seen['root_id'])
        return dict(canonical_action='DOWN', actual_action='DOWN', fallback=False, work={'utility_inference': 1})
    monkeypatch.setattr(runner.core, 'choose_action', choose)
    def label(*args):
        assert events[-1].startswith('choice_UTILITY_') or events[-1] == 'label'
        events.append('label')
        return dict(native={}, teacher_policy=[], costs={kind: {'paid': 1} for kind in
            ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation')})
    monkeypatch.setattr(runner.acquisition, 'exact_labels', label)
    monkeypatch.setattr(runner, 'canonical_labels', lambda root, *args: dict(root))
    monkeypatch.setattr(runner, 'summarize', lambda *args: {'complete': True})
    return events


def test_cached_source_only_16_inputs_and_frozen_controls_before_all_labels(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch); record = runner.run(tmp_path/'out')
    assert events == ['capture', 'fit_source_cached', 'source_UTILITY', 'cases', 'geometry_cache', 'relation_cache',
        'conditional_cache', 'raw_cache', 'program_cache_target', 'old_choices', 'choice_UTILITY_fresh:0', 'choice_UTILITY_fresh:1', 'label', 'label']
    assert [row['phase'] for row in record['phase_history']] == ['protocol_frozen', 'source_selection', 'models_frozen',
        'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    assert [row['input_reads'] for row in record['phase_history']] == [0]+[16]*6
    inputs = json.loads((tmp_path/'out/input_manifest.json').read_text())
    assert all(row['phase'] == 'protocol_frozen' for row in inputs)
    assert [row['saved_ref'].split('/')[-1] for row in inputs] == ['v197_stage_checks.json', 'v197_run.json', 'v197_summary.json',
        'v196_roots.json', 'program_models.json', 'program_libraries.json', 'region_models.json', 'region_libraries.json',
        'conditional_models.json', 'nonlinear_model.json', 'relation_model.json', 'expanded_models.json', 'baseline_models.json',
        'learned_rule.json', 'dense_models.json', 'v196_selection.json']
    assert record['new_predictors_fitted'] == record['new_tree_fits'] == 17 and record['new_learning_attempts'] == 1
    assert record['new_source_selection_roots'] == record['new_source_evaluation_roots'] == 143
    assert all(record[key] == 0 for key in runner.ZERO_COUNTS)
    assert record['costs']['choices']['counts']['frozen_model_choices'] == 34
    assert record['costs']['choices']['counts']['utility_inference'] == 2
    assert set(json.loads((tmp_path/'out/models.json').read_text())) == set(runner.MODEL_NAMES)
    assert set(json.loads((tmp_path/'out/selection.json').read_text())) == {'UTILITY'}
    assert not (tmp_path/'out/libraries.json').exists()


def test_failed_utility_fit_retains_partial_paid_trees_and_closes_roster(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    def fail(*args):
        events.append('fit_source_cached'); error = RuntimeError('synthetic utility split failure')
        error.record = {'costs': {'new_predictors_fitted': 8, 'tree_predictors_fitted': 8,
                                  'tree_fit_attempts': 9, 'shared_library_preparations': 0}}
        raise error
    monkeypatch.setattr(runner.core, 'fit_models', fail)
    with pytest.raises(RuntimeError, match='utility split failure'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture', 'fit_source_cached']
    assert record['new_predictors_fitted'] == record['new_tree_fits'] == 8 and record['new_learning_attempts'] == 1
    assert record['costs']['failed_learning']['counts']['tree_fit_attempts'] == 9
    assert record['new_boards_generated'] == record['new_reference_kernel_attempts'] == record['new_source_evaluation_roots'] == 0
    assert all(record[key] == 0 for key in runner.ZERO_COUNTS)


def test_second_label_failure_preserves_frozen_fit_source_diagnostics_and_partial_labels(tmp_path, monkeypatch):
    fake_inputs(tmp_path, monkeypatch); first = runner.acquisition.exact_labels
    def label(case, rule):
        if case['name'] == 'fresh:0':
            return first(case, rule)
        error = ValueError('synthetic acquisition cap'); error.counts = {'concrete_states': 200000}
        error.elapsed_seconds = .25; raise error
    monkeypatch.setattr(runner.acquisition, 'exact_labels', label)
    with pytest.raises(ValueError, match='acquisition cap'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert record['new_predictors_fitted'] == record['new_tree_fits'] == 17
    assert record['new_reference_kernel_attempts'] == 2 and record['completed_roots'] == 1
    assert record['failure']['counts']['concrete_states'] == 200000 and record['failure']['label_seconds'] == .25
    assert len(json.loads((tmp_path/'out/labels.json').read_text())) == 1
    assert len(json.loads((tmp_path/'out/native_labels.json').read_text())) == 1
    assert len(json.loads((tmp_path/'out/label_costs.json').read_text())) == 1
    assert record['costs']['labels']['counts']['construction.paid'] == 1
    assert (tmp_path/'out/source_diagnostics.json').exists() and (tmp_path/'out/choices.json').exists()


def test_summary_marks_old_source_reuse_and_compares_source_utility_without_refit():
    roots = {'SOURCE': [{'source_id': 'g0'}, {'source_id': 'g1'}],
             'TARGET': [dict(root_id=f'r{i}', replica=i, stratum=0, legal_actions=['DOWN', 'LEFT']) for i in range(2)]}
    labels = [dict(root_id='r0', action_components={'DOWN': [1., 0., 0.], 'LEFT': [.6, 0., 0.]}),
              dict(root_id='r1', action_components={'DOWN': [.4, 0., 0.], 'LEFT': [.8, 0., 1.]})]
    choices = {}
    for mode in (*runner.MODEL_NAMES, 'FALLBACK'):
        choices[mode] = []
        for i in range(2):
            action = ('DOWN' if i == 0 else 'LEFT') if mode == 'UTILITY' else ('LEFT' if i == 0 else 'DOWN')
            decision = {'estimated_pairs': {'DOWN|LEFT': {'actions': ['DOWN', 'LEFT'], 'estimated_tail_delta': [0., 0., 0.],
                'projected_tail_delta': [0., 0., 0.], 'projection_residual': [0., 0., 0.]}}}
            choices[mode].append(dict(root_id=f'r{i}', canonical_action=action, fallback=False, decision=decision))
    retained = dict(SOURCE={'modes': {mode: {'frozen_source': mode} for mode in runner.previous.NEW_MODES}},
        projection_residuals={'SOURCE': {mode: {'retained_projection': mode} for mode in runner.previous.NEW_MODES}})
    selected = {'UTILITY': {'selected_depth': 4, 'selected_min_leaf_roots': 4, 'selected_utility': 1.3}}
    source = {'UTILITY': {'metrics': {'utility': 1.4}, 'projection_residuals': {'new_projection': True}}}
    models = {'UTILITY': {'constants': {'columns': 162}}}; old_selected = {'PROGRAM': {'selected_utility': 1.269}}
    summary = runner.summarize(roots, labels, choices, selected, models, source, retained, old_selected)
    assert all(summary['SOURCE']['modes'][mode] == retained['SOURCE']['modes'][mode] for mode in runner.previous.NEW_MODES)
    assert summary['SOURCE']['modes']['UTILITY']['actual'] == {'utility': 1.4}
    assert summary['SOURCE']['heldout_comparison'] == {'UTILITY_utility': 1.3, 'PROGRAM_utility': 1.269,
                                                    'UTILITY_MINUS_PROGRAM': pytest.approx(.031)}
    assert summary['SOURCE_reuse'] == {'retained_modes': list(runner.previous.NEW_MODES),
        'summary_ref': 'inputs/inherited/v197_summary.json', 'selection_ref': 'inputs/inherited/v196_selection.json',
        'fields': ['SOURCE.modes', 'projection_residuals.SOURCE']}
    assert set(summary['models']) == set(runner.MODELS) and len(summary['comparisons']) == 17
    assert set(summary['projection_residuals']['TARGET']) == set(runner.PAIR_MODES)
    assert summary['comparisons']['UTILITY_MINUS_PROGRAM']['utility'] == pytest.approx(.9)


def test_fixed_new_roster_with_synthetic_rng(monkeypatch):
    seeds = []
    class MockRng:
        def __init__(self, seed): seeds.append(seed)
        def randint(self, *args): return 7
        def sample(self, values, k): return values[:k]
    monkeypatch.setattr(runner.random, 'Random', MockRng)
    cases = runner.cohort_cases()
    assert seeds == list(range(1980200, 1980296)) and len(cases) == 96
    assert cases[0]['name'] == 'v198_target_r00_00' and cases[-1]['name'] == 'v198_target_r03_23'
    assert all(row['board'].count(0) == row['stratum']%3 and row['horizon'] == 3 for row in cases)
