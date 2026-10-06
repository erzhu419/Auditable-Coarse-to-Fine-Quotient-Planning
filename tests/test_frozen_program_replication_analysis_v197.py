"""Focused frozen-model, SOURCE reuse and independent-cohort flow checks."""
from copy import deepcopy

import pytest

from scripts import analyze_controlled_predictive_frozen_program_replication_v197 as audit


def inputs():
    models = {name: dict(mode=name, parameter=.25, library_id='FULL') for name in audit.MODEL_NAMES}
    return {'program_models.json': {name: models[name] for name in audit.previous.MODES},
        'region_models.json': {name: models[name] for name in ('TREE32', 'RAW32')},
        'conditional_models.json': {name: models[name] for name in ('CONDITIONAL', 'PAIR98')},
        'nonlinear_model.json': models['NONLINEAR'], 'relation_model.json': models['RELATION'],
        'expanded_models.json': {name: models[name] for name in ('RIDGE', 'LAYOUT', 'SHARED')},
        'dense_models.json': {name: models[name] for name in ('LINEAR', 'INTERACT')},
        'baseline_models.json': {'SHARED': models['OLD_SHARED'], 'ONE': models['ONE']}}


def retained_summary():
    effects = {'PROGRAM_MINUS_'+name: {'utility': -.25} for name in audit.PRIMARY}
    replicas = [{'replica': i, 'comparisons': {'PROGRAM_MINUS_'+name: {'utility': value} for name in audit.PRIMARY}}
        for i, value in enumerate((-.5, .1, 0., audit.EPS))]
    return dict(SOURCE=dict(roots=143, design_groups=36, modes={'PROGRAM': {'selected_depth': 4, 'actual': {'utility': 1.2}}}),
        projection_residuals={'SOURCE': {'PROGRAM': {'roots': 143, 'pairs': 9, 'mean_abs_components': [.1, .2, .3]}}},
        comparisons=effects, replicas=replicas)


def summary_fixture():
    target = [dict(root_id=f'v197:fixture:{i}', legal_actions=['DOWN', 'LEFT'], replica=i, stratum=0) for i in range(2)]
    labels = [dict(root_id=target[0]['root_id'], action_components={'DOWN': [.2, 0., 0.], 'LEFT': [0., 0., 1.]}),
        dict(root_id=target[1]['root_id'], action_components={'DOWN': [1.3, .1, 0.], 'LEFT': [0., 0., 1.]})]
    choices = {}
    for name in (*audit.MODEL_NAMES, 'FALLBACK'):
        action = 'LEFT' if name == 'PROGRAM' else 'DOWN'
        choices[name] = [dict(root_id=root['root_id'], canonical_action=action, fallback=False,
            decision={'estimated_pairs': {'DOWN|LEFT': dict(actions=['DOWN', 'LEFT'], estimated_tail_delta=[0., 0., 0.],
                projected_tail_delta=[0., 0., 0.], projection_residual=[0., 0., 0.])}}) for root in target]
    return target, labels, choices


def test_exact_sixteen_model_payloads_and_both_explicit_frozen_libraries():
    retained = inputs(); before = deepcopy(retained); models = audit.merge_models(retained)
    libraries = {'FULL': {'library_id': 'FULL', 'prototypes': 'retained read-only source support'}}
    assert set(models) == set(audit.MODEL_NAMES) and len(models) == 16
    assert models['OLD_SHARED'] == retained['baseline_models.json']['SHARED']
    assert audit.models_binding(deepcopy(models), models, libraries, libraries)
    altered = deepcopy(models); altered['PROGRAM']['parameter'] += 1e-12
    assert audit.close(altered, models) and not audit.models_binding(altered, models, libraries, libraries)
    altered = deepcopy(models); altered['TREE32']['library_id'] = 'FOLD_0'
    assert not audit.models_binding(altered, models, libraries, libraries)
    altered = deepcopy(models); del altered['NONLINEAR']
    assert not audit.models_binding(altered, models, libraries, libraries)
    assert retained == before


def test_zero_source_and_training_work_rejects_refit_or_fresh_source_accounting():
    run = dict(costs={'observations': {'counts': {'observed_roots': 96}}, 'choices': {'counts': {'frozen_model_choices': 1536}}},
        **{name: 0 for name in audit.ZERO_WORK})
    assert audit.zero_source_work(run)
    for name in ('new_tree_fits', 'new_learning_attempts', 'new_source_cache_roots', 'new_source_evaluation_roots', 'new_source_selection_roots'):
        changed = deepcopy(run); changed[name] = 1
        assert not audit.zero_source_work(changed)
    for name in ('learning', 'source_features', 'source_evaluation_PROGRAM'):
        changed = deepcopy(run); changed['costs'][name] = {'counts': {}}
        assert not audit.zero_source_work(changed)
    assert len(audit.ZERO_WORK) == 12


def test_reused_source_and_target_metrics_do_not_call_source_operations(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('a settled SOURCE operation must never run')
    for name in ('fit_models', 'prepare_library', 'model_from_library', 'source_diagnostics'):
        monkeypatch.setattr(audit.previous, name, forbidden)
    target, labels, choices = summary_fixture(); retained = retained_summary(); before = deepcopy(retained)
    result = audit.summarize(target, labels, choices, retained)
    assert result['schema'] == 'acfqp.frozen_program_replication.v197.summary'
    assert result['roots'] == 2 and len(result['models']) == 18 and len(result['comparisons']) == 16
    assert audit.source_reuse_binding(result, retained) and retained == before
    assert result['SOURCE']['roots'] == 143 and result['SOURCE']['design_groups'] == 36
    assert result['SOURCE_reuse'] == dict(retained=True, summary_ref='inputs/inherited/v196_summary.json', fields=['SOURCE', 'projection_residuals.SOURCE'])
    assert set(result['projection_residuals']['TARGET']) == set(audit.PAIR_MODES)
    assert all(result[name] == 0 for name in audit.ZERO_WORK)
    assert result['success_diagnostics']['PROGRAM']['eligible_roots'] == 1
    assert result['success_diagnostics']['PROGRAM']['missed_root_ids'] == ['v197:fixture:1']
    result['SOURCE']['modes']['PROGRAM']['actual']['utility'] += .01
    assert retained == before and not audit.source_reuse_binding(result, retained)


def test_cross_cohort_effects_remain_separate_with_original_primary_names():
    target, labels, choices = summary_fixture(); result = audit.summarize(target, labels, choices, retained_summary())
    assert set(result['cross_cohort_comparisons']) == {'PROGRAM_MINUS_'+name for name in audit.PRIMARY}
    assert len(result['root_records']) == 2 and [row['root_id'] for row in result['root_records']] == [row['root_id'] for row in target]
    for row in result['cross_cohort_comparisons'].values():
        assert set(row) == {'V196_utility_delta', 'V197_utility_delta', 'V196_positive_replicas', 'V197_positive_replicas'}
        assert row['V196_utility_delta'] == -.25 and row['V197_utility_delta'] == pytest.approx(.3)
        assert row['V196_positive_replicas'] == row['V197_positive_replicas'] == 1
    assert result['comparisons']['PROGRAM_MINUS_LINEAR']['utility'] == pytest.approx(.3)
    assert result['replicas'][0]['comparisons']['PROGRAM_MINUS_LINEAR']['utility'] == pytest.approx(.8)
    assert result['replicas'][1]['comparisons']['PROGRAM_MINUS_LINEAR']['utility'] == pytest.approx(-.2)
    changed = deepcopy(result); changed['projection_residuals']['SOURCE']['PROGRAM']['mean_abs_components'][0] += 1e-12
    assert audit.close(changed, result) and not audit.source_reuse_binding(changed, retained_summary())
    changed = deepcopy(result); changed['SOURCE_reuse']['retained'] = False
    assert not audit.source_reuse_binding(changed, retained_summary())


def test_fourteen_input_roster_fresh_starts_and_labels_after_frozen_choices():
    assert audit.INPUT_NAMES == ('v196_stage_checks.json', 'v196_run.json', 'v196_summary.json', 'program_models.json', 'program_libraries.json',
        'region_models.json', 'region_libraries.json', 'conditional_models.json', 'nonlinear_model.json', 'relation_model.json',
        'expanded_models.json', 'baseline_models.json', 'learned_rule.json', 'dense_models.json')
    run = dict(phase_history=[dict(phase=phase, input_reads=0 if i == 0 else 14) for i, phase in enumerate(audit.PHASES)])
    assert audit.phase_binding(run)
    changed = deepcopy(run); changed['phase_history'][3], changed['phase_history'][4] = changed['phase_history'][4], changed['phase_history'][3]
    assert not audit.phase_binding(changed)
    changed = deepcopy(run); changed['phase_history'][1]['input_reads'] = 13
    assert not audit.phase_binding(changed)
    cases = audit.cohort_cases()
    assert len(cases) == 96 and cases[0]['name'] == 'v197_target_r00_00' and cases[-1]['name'] == 'v197_target_r03_23'
    assert [row['seed'] for row in cases] == list(range(1970200, 1970296))
    assert all(row['split'] == 'TARGET' and row['horizon'] == 3 for row in cases)
