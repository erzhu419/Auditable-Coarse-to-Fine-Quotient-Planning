"""Synthetic four-cell/anchor tests; source fixture generation samples no environment."""
from copy import deepcopy
import importlib.util
import itertools
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis = load_module('lmta_components_analysis_v48', ROOT / 'scripts/analyze_lmta_components_v48.py')
source_fixture = load_module('lmta_v46_synthetic_fixture', ROOT / 'tests/test_lmta_weighted_analysis_v46.py')


def fixture():
    weighted, weighted_manifest = source_fixture.fixture_side(True)
    heuristic, heuristic_manifest = source_fixture.fixture_side(False)
    weighted_manifest['runtime'] = dict(device='cuda', torch='synthetic-fixed', torch_threads=1)
    for row in weighted_manifest['completed_runs']:
        row['model_path'] = f"models/{row['method']}_run{row['run_id']}.pt"
    for row in weighted:
        if row['phase'] == 'evaluation' and row['method'] in analysis.METHODS:
            row['daily_budgets'] = [7] * 10
            row['daily_durations'] = [7] * 10
            if row['method'] == 'LMTA_RI':
                row['subgoals'] = [row['run_id']] * 10
                row['search_values'] = [1.25] * 10
    sources = {(row['method'], row['run_id'], row['episode']): row for row in weighted
               if row['phase'] == 'evaluation' and row['checkpoint'] == 128}
    events = []
    for method, run in itertools.product(analysis.METHODS, range(3)):
        anchor = deepcopy(sources[method, run, 0])
        anchor.update(phase='restore_anchor', cell='LL', wall_seconds=.5)
        events.append(anchor)
        for cell, episode in itertools.product(('LS', 'AL'), range(20)):
            row = deepcopy(sources[method, run, episode])
            row.update(cell=cell, wall_seconds=.5)
            row['raw_return'] += 5 + run if cell == 'LS' else -2 - run
            events.append(row)
    policies = [dict(run_id=row['run_id'], method=row['method'], model_path=row['model_path'],
                     model_bytes=row['model_bytes'], source_checkpoint=128, load_seconds=.2)
                for row in weighted_manifest['completed_runs'] if row['method'] in analysis.METHODS]
    manifest = dict(schema='acfqp.lmta_components.v48', status='complete',
        protocol=deepcopy(analysis.FROZEN_PROTOCOL), source_directory='reports/lmta_weighted_v46',
        runtime=deepcopy(weighted_manifest['runtime']),
        graphs=[deepcopy(row) for row in weighted_manifest['graphs'] if 440900 <= row['graph_id'] <= 440909],
        loaded_policies=policies, graph_generation_seconds=.4, wall_seconds=125.6)
    return events, manifest, weighted, weighted_manifest, heuristic, heuristic_manifest


def test_four_cells_effect_directions_df_two_and_single_retained_as_cost():
    report = analysis.summarize(*fixture())
    assert report['integrity']['passed'] and report['valid_component_estimates']
    assert all(row['passed'] for row in report['integrity']['candidate']['anchors'])
    assert report['integrity']['candidate']['phase_counts'] == {'restore_anchor': 6, 'evaluation': 240}
    for method in analysis.METHODS:
        cells = report['cell_means'][method]
        assert cells['LL']['run_values'] == [249.5, 251.5, 253.5]
        assert cells['AS']['panel_mean'] == 229.5
        assert cells['AS']['ci_95'] is None and cells['AS']['n_independent_training_runs'] == 0
        effects = report['component_effects'][method]
        expected = dict(node_substitution_LS_minus_LL=[5., 6., 7.],
            node_substitution_AS_minus_AL=[-18., -19., -20.],
            budget_substitution_AL_minus_LL=[-2., -3., -4.],
            budget_substitution_AS_minus_LS=[-25., -28., -31.],
            interaction_AS_minus_AL_minus_LS_plus_LL=[-23., -25., -27.],
            hybrid_LS_minus_AS=[25., 28., 31.], hybrid_AL_minus_AS=[18., 19., 20.])
        for name, values in expected.items():
            assert effects[name]['run_values'] == values
            assert effects[name]['n_independent_training_runs'] == 3
        radius = analysis.v44.T95_DF2 / 3 ** .5
        assert effects['node_substitution_LS_minus_LL']['ci_95'] == pytest.approx([6 - radius, 6 + radius])
    assert 'LMTA_continue_signal' not in report
    fees = report['accounting']['new_components']
    assert fees['all_actual_events']['event_count'] == 246
    assert fees['all_actual_events']['wall_seconds'] == 123.
    assert fees['all_actual_events']['counters']['primitive_selections'] == 246 * 70
    assert sum(row['event_count'] for row in fees['by_phase_cell_method_run'] if row['cell'] == 'LL') == 6
    assert fees['runner_costs']['policy_load_seconds'] == pytest.approx(1.2)
    assert fees['runner_costs']['unitemized_runner_seconds'] == pytest.approx(1.)
    assert report['accounting']['retained_weighted_V46']['all_actual_events']['event_count'] == 1872
    old = report['accounting']['retained_heuristic_source_V44']
    assert old['all_actual_events']['event_count'] == 1912
    assert sum(row['event_count'] for row in old['by_phase_method_run'] if row['method'] == 'AVERAGE_SCORE') == 20


@pytest.mark.parametrize('failure', ['anchor_return', 'anchor_counter', 'anchor_search', 'gradient',
                                   'wrong_panel', 'missing', 'duplicate', 'load_binding'])
def test_invalid_components_or_anchor_retain_every_raw_fee_without_valid_effects(failure):
    events, manifest, weighted, weighted_manifest, heuristic, heuristic_manifest = fixture()
    anchor = next(row for row in events if row['phase'] == 'restore_anchor' and row['method'] == 'LMTA_RI')
    hybrid = next(row for row in events if row['phase'] == 'evaluation')
    if failure == 'anchor_return':
        anchor['raw_return'] += 1.
    elif failure == 'anchor_counter':
        anchor['counters']['propagation_draws'] += 1
    elif failure == 'anchor_search':
        anchor['search_values'][0] += 1e-15
    elif failure == 'gradient':
        hybrid['model_work']['LL_gradient_steps'] = 1
    elif failure == 'wrong_panel':
        hybrid['environment_seed'] += 1
    elif failure == 'missing':
        events.remove(hybrid)
    elif failure == 'duplicate':
        events.append(deepcopy(hybrid))
    else:
        manifest['loaded_policies'][0]['model_bytes'] += 1
    report = analysis.summarize(events, manifest, weighted, weighted_manifest, heuristic, heuristic_manifest)
    assert not report['integrity']['passed'] and not report['valid_component_estimates']
    assert report['component_effects'] is None
    fees = report['accounting']['new_components']['all_actual_events']
    assert fees['event_count'] == len(events)
    assert fees['wall_seconds'] == .5 * len(events)
    assert fees['counters']['primitive_selections'] == 70 * len(events)
    assert report['accounting']['retained_heuristic_source_V44']['all_actual_events']['event_count'] == 1912


def test_anchor_requires_exact_original_model_work_but_excludes_component_counters():
    inputs = fixture()
    events = inputs[0]
    anchor = next(row for row in events if row['phase'] == 'restore_anchor' and row['method'] == 'LMTA_RI')
    anchor['model_work']['component_live_search_calls'] = 10
    report = analysis.summarize(*inputs)
    assert report['integrity']['passed']
    assert all(row['checks']['original_model_work'] for row in report['integrity']['candidate']['anchors'])
    # Unprefixed work is part of the original implementation and must match exactly.
    anchor['model_work']['latent_recurrent_calls'] = 1
    report = analysis.summarize(*inputs)
    assert not report['integrity']['passed'] and report['component_effects'] is None
    checks = next(row['checks'] for row in report['integrity']['candidate']['anchors']
                  if row['method'] == 'LMTA_RI' and row['run_id'] == anchor['run_id'])
    assert checks['original_model_work'] is False
    assert report['accounting']['new_components']['all_actual_events']['event_count'] == 246
    assert report['accounting']['new_components']['all_actual_events']['model_work']['component_live_search_calls'] == 10
