"""Synthetic shared-library freeze, compact SOURCE retention and success errors."""
import json
import pytest
from scripts import run_controlled_predictive_pair_regions_v195 as runner


def fake_inputs(tmp_path, monkeypatch):
    prior = tmp_path/'prior'
    monkeypatch.setattr(runner, 'ROOT', tmp_path); monkeypatch.setattr(runner, 'PREVIOUS', prior)
    runner.save(tmp_path/'reports/v194_runtime_tmp/stage_checks.json', {'valid': True})
    runner.save(prior/'run.json', {'status': 'complete'})
    source = [dict(root_id=f'source:{i}', source_id=f'group:{i%36}', conditional_features={}) for i in range(143)]
    runner.save(prior/'roots.json', {'SOURCE': source, 'TARGET': [{'root_id': 'excluded:target'}]})
    runner.save(prior/'models.json', {'CONDITIONAL': {}, 'PAIR98': {}})
    inherited = prior/'inputs/inherited'
    runner.save(inherited/'nonlinear_model.json', {'old_nonlinear': True})
    runner.save(inherited/'relation_model.json', {'old_relation': True})
    runner.save(inherited/'expanded_models.json', {'RIDGE': {}, 'LAYOUT': {}, 'SHARED': {}})
    runner.save(inherited/'baseline_models.json', {'SHARED': {}, 'ONE': {}})
    runner.save(inherited/'learned_rule.json', {})
    runner.save(inherited/'dense_models.json', {'LINEAR': {}, 'INTERACT': {}})
    monkeypatch.setattr(runner.LearnedDynamics, 'from_payload', lambda payload: object())
    events = []
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    def cache(rows):
        cohort = 'source' if rows[0]['root_id'].startswith('source:') else 'target'
        events.append('raw_cache_'+cohort)
        for row in rows:
            row['raw_afterstates'] = {}
        return {'raw_roots_cached': len(rows)}
    monkeypatch.setattr(runner.core, 'cache_roots', cache)
    def fit(rows):
        assert len(rows) == 143 and all(row['root_id'].startswith('source:') for row in rows)
        assert all('raw_afterstates' in row and 'conditional_features' in row for row in rows)
        events.append('fit_shared')
        return dict(models={mode: {'mode': mode, 'library_id': 'FULL'} for mode in runner.NEW_MODES},
            selection={mode: {} for mode in runner.NEW_MODES},
            libraries={name: {'library_id': name} for name in ('FOLD_0', 'FOLD_1', 'FULL')},
            costs={'new_predictors_fitted': 24, 'tree_predictors_fitted': 17,
                   'raw_predictor_configurations': 7, 'shared_library_preparations': 3})
    monkeypatch.setattr(runner.core, 'fit_models', fit)
    def actual(rows, model, library):
        assert library == {'library_id': 'FULL'} and 'prototypes' not in model
        events.append('source_'+model['mode'])
        return dict(metrics={}, root_records=[], projection_residuals={}, work={'source_diagnostic_root_records': len(rows)})
    monkeypatch.setattr(runner, 'source_diagnostics', actual)
    monkeypatch.setattr(runner, 'cohort_cases', lambda: events.append('cases') or [{'name': 'fresh:target'}])
    monkeypatch.setattr(runner.acquisition, 'observe_roots', lambda cases: ([{'root_id': cases[0]['name']}], {}))
    monkeypatch.setattr(runner.coverage, 'cache_roots', lambda rows: events.append('geometry_cache') or {})
    monkeypatch.setattr(runner.relation, 'cache_roots', lambda rows: events.append('relation_cache') or {})
    monkeypatch.setattr(runner.conditional, 'cache_roots', lambda rows: events.append('conditional_cache') or {})
    def choose(rows, models, libraries):
        assert set(models) == set(runner.MODEL_NAMES) and set(libraries) == {'FOLD_0', 'FOLD_1', 'FULL'}
        assert models['NONLINEAR'] == {'old_nonlinear': True}
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


def test_shared_three_libraries_source_only_and_all_choices_precede_labels(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch); record = runner.run(tmp_path/'out')
    assert events == ['capture', 'raw_cache_source', 'fit_shared', 'source_TREE32', 'source_RAW32', 'cases',
        'geometry_cache', 'relation_cache', 'conditional_cache', 'raw_cache_target', 'choices', 'label']
    assert [row['phase'] for row in record['phase_history']] == ['protocol_frozen', 'source_selection',
        'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    assert [row['input_reads'] for row in record['phase_history']] == [0]+[10]*6
    inputs = json.loads((tmp_path/'out/input_manifest.json').read_text())
    assert all(row['phase'] == 'protocol_frozen' for row in inputs)
    assert [row['saved_ref'].split('/')[-1] for row in inputs] == ['v194_stage_checks.json', 'v194_run.json',
        'v194_roots.json', 'conditional_models.json', 'nonlinear_model.json', 'relation_model.json',
        'expanded_models.json', 'baseline_models.json', 'learned_rule.json', 'dense_models.json']
    assert record['new_predictors_fitted'] == 24 and record['new_tree_fits'] == 17 and record['new_raw_configurations'] == 7
    assert record['new_learning_attempts'] == 1 and record['shared_library_preparations'] == 3
    assert record['new_parameter_solves'] == 0 and record['new_reference_kernel_attempts'] == record['completed_roots'] == 1
    assert set(json.loads((tmp_path/'out/libraries.json').read_text())) == {'FOLD_0', 'FOLD_1', 'FULL'}


def test_failed_joint_fit_keeps_tree_and_raw_partial_paid_work_roster_closed(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    def fail(*args):
        events.append('fit_shared'); error = RuntimeError('synthetic final RAW configuration failure')
        error.record = {'costs': {'new_predictors_fitted': 20, 'tree_predictors_fitted': 17,
                                  'raw_predictor_configurations': 3, 'shared_library_preparations': 3}}
        raise error
    monkeypatch.setattr(runner.core, 'fit_models', fail)
    with pytest.raises(RuntimeError, match='RAW configuration'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture', 'raw_cache_source', 'fit_shared']
    assert record['new_predictors_fitted'] == 20 and record['new_tree_fits'] == 17 and record['new_raw_configurations'] == 3
    assert record['shared_library_preparations'] == 3 and record['new_learning_attempts'] == 1
    assert record['new_boards_generated'] == record['new_reference_kernel_attempts'] == 0
    assert record['costs']['failed_learning']['counts']['raw_predictor_configurations'] == 3


def test_failed_acquisition_keeps_frozen_24_predictors_and_paid_attempt(tmp_path, monkeypatch):
    fake_inputs(tmp_path, monkeypatch)
    def fail(*args):
        error = ValueError('synthetic acquisition cap'); error.counts = {'concrete_states': 200000}
        error.elapsed_seconds = .25; raise error
    monkeypatch.setattr(runner.acquisition, 'exact_labels', fail)
    with pytest.raises(ValueError, match='acquisition cap'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert record['new_predictors_fitted'] == 24 and record['new_reference_kernel_attempts'] == 1
    assert record['completed_roots'] == 0 and record['failure']['label_seconds'] == .25


def test_source_library_explicit_label_free_and_only_nested_raw_neighbors_removed(monkeypatch):
    root = dict(root_id='source', source_id='group', life=0, canonical_board=[0]*16,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': 0., 'LEFT': 0.}, fallback_action='DOWN',
        action_map={'DOWN': 'DOWN', 'LEFT': 'LEFT'}, layout_features={}, action_features={},
        relation_features={}, conditional_features={}, raw_afterstates={'DOWN': [0]*16, 'LEFT': [1]*16},
        action_components={'DOWN': [.7, .6, .1], 'LEFT': [.4, 0., .5]})
    def choose(model, seen, library, counts):
        assert 'action_components' not in seen and library == {'library_id': 'FULL'}
        counts.update(region_decisions=1)
        direction = {'components': [0., 0., 0.], 'neighbors': [{'weight': 1., 'prototype_index': 0}]}
        return dict(canonical_action='DOWN', fallback=False, projection_residual_sse=0., projection_residual_max=0.,
            predicted_components={'DOWN': [0., 0., 0.], 'LEFT': [0., 0., 0.]},
            estimated_pairs={'DOWN|LEFT': {'actions': ['DOWN', 'LEFT'], 'forward': dict(direction), 'reverse': dict(direction),
                'estimated_tail_delta': [0., 0., 0.], 'projected_tail_delta': [0., 0., 0.], 'projection_residual': [0., 0., 0.]}})
    monkeypatch.setattr(runner.core, 'choose_action', choose)
    result = runner.source_diagnostics([root], {'mode': 'RAW32'}, {'library_id': 'FULL'})
    pair = result['root_records'][0]['decision']['estimated_pairs']['DOWN|LEFT']
    assert 'neighbors' not in pair['forward'] and 'neighbors' not in pair['reverse']
    assert pair['forward']['components'] == [0., 0., 0.] and pair['estimated_tail_delta'] == [0., 0., 0.]
    assert result['projection_residuals']['pairs'] == 1
    assert result['root_records'][0]['regret'] == pytest.approx(.7)


def test_success_misses_and_wrong_direction_use_selected_orientation_and_positive_regret():
    records, chosen = [], {mode: {} for mode in runner.PAIR_MODES}
    for index, (selected, oracle) in enumerate((('DOWN', 'LEFT'), ('LEFT', 'DOWN'))):
        root_id = f'r{index}'; models = {'ORACLE': {'action': oracle, 'components': [0., 0., 1.], 'regret': 0.}}
        for mode in runner.PAIR_MODES:
            action = oracle if mode == 'PAIR98' else selected
            models[mode] = {'action': action, 'components': [0., 0., float(mode == 'PAIR98')],
                            'regret': 0. if mode == 'PAIR98' else 1.}
            stored_success = 0. if mode == 'TREE32' else .4 if index == 0 else -.4
            chosen[mode][root_id] = {'decision': {'estimated_pairs': {'DOWN|LEFT': {
                'actions': ['DOWN', 'LEFT'], 'estimated_tail_delta': [0., 0., stored_success]}}}}
        records.append({'root_id': root_id, 'models': models})
    result = runner.success_diagnostics(records, chosen)
    assert result['TREE32']['missed_root_ids'] == ['r0', 'r1'] and result['TREE32']['wrong_direction'] == 0
    assert result['RAW32']['wrong_direction_root_ids'] == ['r0', 'r1'] and result['RAW32']['missed'] == 0
    assert result['PAIR98']['eligible_roots'] == 0 and result['PAIR98']['wrong_direction'] == 0


def test_fixed_new_96_root_roster_with_synthetic_rng(monkeypatch):
    seeds = []
    class MockRng:
        def __init__(self, seed): seeds.append(seed)
        def randint(self, *args): return 7
        def sample(self, values, k): return values[:k]
    monkeypatch.setattr(runner.random, 'Random', MockRng)
    cases = runner.cohort_cases()
    assert seeds == list(range(1950200, 1950296)) and len(cases) == 96
    assert cases[0]['name'] == 'v195_target_r00_00' and cases[-1]['name'] == 'v195_target_r03_23'
    assert all(row['board'].count(0) == row['stratum']%3 and row['horizon'] == 3 for row in cases)
