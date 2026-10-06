"""Synthetic frozen predictors, fresh roster and partial exact-label accounting."""
import json
import pytest
from scripts import run_controlled_predictive_frozen_program_replication_v197 as runner


def fake_inputs(tmp_path, monkeypatch):
    prior = tmp_path/'prior'
    monkeypatch.setattr(runner, 'ROOT', tmp_path); monkeypatch.setattr(runner, 'PREVIOUS', prior)
    runner.save(tmp_path/'reports/v196_runtime_tmp/stage_checks.json', {'valid': True})
    runner.save(prior/'run.json', {'status': 'complete', 'new_predictors_fitted': 41})
    runner.save(prior/'summary.json', {'SOURCE': {'roots': 143, 'design_groups': 36}})
    runner.save(prior/'models.json', {mode: {'mode': mode, 'frozen_program': True} for mode in runner.previous.NEW_MODES})
    runner.save(prior/'libraries.json', {'FULL': {'frozen_program_library': True}})
    inherited = prior/'inputs/inherited'
    runner.save(inherited/'region_models.json', {'TREE32': {}, 'RAW32': {}})
    runner.save(inherited/'region_libraries.json', {'FULL': {'frozen_region_library': True}})
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
    def forbidden(*args, **kwargs):
        raise AssertionError('SOURCE work or new fitting is forbidden')
    monkeypatch.setattr(runner.previous.core, 'fit_models', forbidden)
    monkeypatch.setattr(runner.previous, 'source_diagnostics', forbidden)
    monkeypatch.setattr(runner, 'cohort_cases', lambda: events.append('cases') or [{'name': 'fresh:0'}, {'name': 'fresh:1'}])
    monkeypatch.setattr(runner.acquisition, 'observe_roots', lambda cases: ([{'root_id': row['name']} for row in cases], {}))
    for module, name in ((runner.coverage, 'geometry'), (runner.relation, 'relation'),
                         (runner.conditional, 'conditional'), (runner.region, 'raw')):
        monkeypatch.setattr(module, 'cache_roots', lambda rows, name=name: events.append(name+'_cache') or {})
    def cache(rows, rule):
        assert all(row['root_id'].startswith('fresh:') for row in rows)
        events.append('program_cache_target'); return {'program_cache_roots_built': len(rows)}
    monkeypatch.setattr(runner.trace, 'cache_roots', cache)
    def choose(rows, models, libraries, region_libraries):
        assert set(models) == set(runner.MODEL_NAMES)
        assert all(models[mode]['frozen_program'] for mode in runner.previous.NEW_MODES)
        assert libraries['FULL'] == {'frozen_program_library': True}
        assert region_libraries['FULL'] == {'frozen_region_library': True}
        assert models['SHARED'] == {'expanded': True} and models['OLD_SHARED'] == {'old': True}
        events.append('choices'); return {}, {'frozen_model_choices': 32}
    monkeypatch.setattr(runner, 'freeze_choices', choose)
    def label(*args):
        assert events.index('choices') < len(events)
        events.append('label')
        return dict(native={}, teacher_policy=[], costs={kind: {'paid': 1} for kind in
            ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation')})
    monkeypatch.setattr(runner.acquisition, 'exact_labels', label)
    monkeypatch.setattr(runner, 'canonical_labels', lambda root, *args: dict(root))
    monkeypatch.setattr(runner, 'summarize', lambda *args: {'complete': True})
    return events


def test_frozen_14_inputs_and_all_models_choices_precede_target_labels(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch); record = runner.run(tmp_path/'out')
    assert events == ['capture', 'cases', 'geometry_cache', 'relation_cache', 'conditional_cache',
        'raw_cache', 'program_cache_target', 'choices', 'label', 'label']
    assert [row['phase'] for row in record['phase_history']] == ['protocol_frozen', 'models_frozen',
        'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    assert [row['input_reads'] for row in record['phase_history']] == [0]+[14]*5
    inputs = json.loads((tmp_path/'out/input_manifest.json').read_text())
    assert all(row['phase'] == 'protocol_frozen' for row in inputs)
    assert [row['saved_ref'].split('/')[-1] for row in inputs] == ['v196_stage_checks.json', 'v196_run.json',
        'v196_summary.json', 'program_models.json', 'program_libraries.json', 'region_models.json',
        'region_libraries.json', 'conditional_models.json', 'nonlinear_model.json', 'relation_model.json',
        'expanded_models.json', 'baseline_models.json', 'learned_rule.json', 'dense_models.json']
    assert all(record[key] == 0 for key in runner.ZERO_COUNTS)
    assert record['new_reference_kernel_attempts'] == record['completed_roots'] == 2
    assert set(json.loads((tmp_path/'out/roots.json').read_text())) == {'TARGET'}
    assert not (tmp_path/'out/libraries.json').exists() and not (tmp_path/'out/selection.json').exists()


def test_unsettled_predecessor_stops_before_fresh_roster(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    runner.save(tmp_path/'reports/v196_runtime_tmp/stage_checks.json', {'valid': False})
    with pytest.raises(ValueError, match='V196 stage is incomplete'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture'] and record['new_boards_generated'] == 0
    assert record['costs']['input_counts']['json_read_operations'] == 2
    assert all(record[key] == 0 for key in runner.ZERO_COUNTS)


def test_second_label_failure_retains_first_label_and_paid_attempts_without_fits(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    first = runner.acquisition.exact_labels
    def label(case, rule):
        if case['name'] == 'fresh:0':
            return first(case, rule)
        error = ValueError('synthetic acquisition cap'); error.counts = {'concrete_states': 200000}
        error.elapsed_seconds = .25; raise error
    monkeypatch.setattr(runner.acquisition, 'exact_labels', label)
    with pytest.raises(ValueError, match='acquisition cap'):
        runner.run(tmp_path/'out')
    record = json.loads((tmp_path/'out/run.json').read_text())
    assert record['new_reference_kernel_attempts'] == 2 and record['completed_roots'] == 1
    assert record['failure']['counts']['concrete_states'] == 200000 and record['failure']['label_seconds'] == .25
    assert all(record[key] == 0 for key in runner.ZERO_COUNTS)
    assert len(json.loads((tmp_path/'out/labels.json').read_text())) == 1
    assert len(json.loads((tmp_path/'out/native_labels.json').read_text())) == 1
    assert len(json.loads((tmp_path/'out/label_costs.json').read_text())) == 1
    assert record['costs']['labels']['counts']['construction.paid'] == 1
    assert (tmp_path/'out/choices.json').exists() and 'choices' in events


def test_summary_reuses_source_and_reports_separate_cohorts_only():
    roots = {'TARGET': [dict(root_id=f'r{i}', replica=i, stratum=0, legal_actions=['DOWN', 'LEFT']) for i in range(2)]}
    labels = [dict(root_id='r0', action_components={'DOWN': [1., 0., 0.], 'LEFT': [.6, 0., 0.]}),
              dict(root_id='r1', action_components={'DOWN': [.4, 0., 0.], 'LEFT': [.8, 0., 1.]})]
    choices = {}
    for mode in (*runner.MODEL_NAMES, 'FALLBACK'):
        choices[mode] = []
        for i in range(2):
            action = ('DOWN' if i == 0 else 'LEFT') if mode == 'PROGRAM' else ('LEFT' if i == 0 else 'DOWN')
            decision = {'estimated_pairs': {'DOWN|LEFT': {'actions': ['DOWN', 'LEFT'], 'estimated_tail_delta': [0., 0., 0.],
                'projected_tail_delta': [0., 0., 0.], 'projection_residual': [0., 0., 0.]}}}
            choices[mode].append(dict(root_id=f'r{i}', canonical_action=action, fallback=False, decision=decision))
    prior = dict(SOURCE={'roots': 143, 'design_groups': 36, 'modes': {'PROGRAM': {'selected_depth': 4}}},
        projection_residuals={'SOURCE': {'old_source_projection': True}},
        comparisons={'PROGRAM_MINUS_'+name: {'utility': .1} for name in runner.PRIMARY},
        replicas=[{'comparisons': {'PROGRAM_MINUS_'+name: {'utility': .2 if i%2 == 0 else -.1}
            for name in runner.PRIMARY}} for i in range(4)])
    summary = runner.summarize(roots, labels, choices, prior)
    assert summary['SOURCE'] == prior['SOURCE'] and summary['SOURCE'] is not prior['SOURCE']
    assert summary['projection_residuals']['SOURCE'] == prior['projection_residuals']['SOURCE']
    assert summary['SOURCE_reuse'] == {'retained': True, 'summary_ref': 'inputs/inherited/v196_summary.json',
                                     'fields': ['SOURCE', 'projection_residuals.SOURCE']}
    assert summary['roots'] == 2 and len(summary['root_records']) == 2
    assert set(summary['cross_cohort_comparisons']) == {'PROGRAM_MINUS_'+name for name in runner.PRIMARY}
    for contrast in summary['cross_cohort_comparisons'].values():
        assert contrast == {'V196_utility_delta': .1, 'V197_utility_delta': pytest.approx(.9),
                            'V196_positive_replicas': 2, 'V197_positive_replicas': 2}
    assert set(summary['projection_residuals']['TARGET']) == set(runner.PAIR_MODES)
    assert all(summary[key] == 0 for key in runner.ZERO_COUNTS)


def test_fixed_disjoint_roster_with_synthetic_rng(monkeypatch):
    seeds = []
    class MockRng:
        def __init__(self, seed): seeds.append(seed)
        def randint(self, *args): return 7
        def sample(self, values, k): return values[:k]
    monkeypatch.setattr(runner.random, 'Random', MockRng)
    cases = runner.cohort_cases()
    assert seeds == list(range(1970200, 1970296)) and len(cases) == 96
    assert cases[0]['name'] == 'v197_target_r00_00' and cases[-1]['name'] == 'v197_target_r03_23'
    assert all(row['board'].count(0) == row['stratum']%3 and row['horizon'] == 3 for row in cases)
