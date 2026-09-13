"""Synthetic retained-event tests; no environment or neural network is loaded."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location('lmta_weighted_analysis_v46',
    Path(__file__).resolve().parents[1] / 'scripts/analyze_lmta_weighted_v46.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def fixture_side(candidate):
    protocol = deepcopy(analysis.FROZEN_PROTOCOL)
    protocol['heuristics'] = [] if candidate else analysis.HEURISTICS.copy()
    events = []
    for key in sorted(analysis.v44.expected_keys(protocol), key=str):
        phase = key[0]
        if phase == 'train':
            _, run, method, episode = key
            checkpoint = episode + 1
            graph, seed = 440000 + run * 100 + episode // 8, 441000 + run * 1000 + episode
            reward = 150.
        elif phase == 'evaluation':
            _, run, method, checkpoint, episode = key
            graph, seed = 440900 + episode // 2, 446000 + episode
            base, gain = (200., 40.) if candidate else (195., 10.)
            reward = base + run + episode + (gain + run if checkpoint else 0.)
        else:
            _, method, episode = key
            run = checkpoint = None
            graph, seed = 440900 + episode // 2, 446000 + episode
            reward = (220. if method == 'AVERAGE_SCORE' else 190.) + episode
        row = dict(phase=phase, run_id=run, method=method, checkpoint=checkpoint,
            episode=episode, graph_id=graph, environment_seed=seed,
            raw_return=reward, wall_seconds=.25,
            counters=dict(primitive_selections=70, day_transitions=10, propagation_draws=100),
            model_work={'LL_gradient_steps': 1 if phase == 'train' else 0})
        if phase == 'heuristic':
            row['action_seed'] = 449000 + episode
        events.append(row)
    manifest = dict(schema='acfqp.lmta_weighted.v46' if candidate else 'acfqp.lmta_learnability.v44',
        status='complete', protocol=protocol, graphs=[dict(graph_id=g, nodes=500, edges=2400 + g % 100)
            for g in sorted(analysis.GRAPH_IDS)], graph_generation_seconds=1., wall_seconds=1000.,
        completed_runs=[dict(run_id=run, method=method, initialization_seed=445001 + run,
            initialization_seconds=.1, model_save_seconds=.2, model_bytes=100)
            for run in range(3) for method in analysis.METHODS])
    if candidate:
        manifest.update(operator='IC_SUM', control_directory='reports/lmta_learnability_v44')
    else:
        for row in manifest['completed_runs']:
            del row['initialization_seed']  # The original V44 manifest did not record it.
    return events, manifest


def fixture():
    return (*fixture_side(True), *fixture_side(False))


def test_complete_three_run_design_has_separate_new_and_retained_costs():
    report = analysis.summarize(*fixture())
    assert report['integrity']['passed']
    assert report['LMTA_continue_signal'] is True
    assert report['integrity']['candidate']['expected_events'] == 1872
    assert report['integrity']['control']['expected_events'] == 1912
    endpoint = report['endpoint_comparisons']['LMTA_RI']
    assert endpoint['own_initial']['run_values'] == [40., 41., 42.]
    assert endpoint['MEAN_V44']['run_values'] == [35., 35., 35.]
    assert endpoint['AVERAGE_SCORE']['run_values'] == [20., 22., 24.]
    assert endpoint['AVERAGE_RANDOM']['run_values'] == [50., 52., 54.]
    assert endpoint['own_initial']['n_independent_training_runs'] == 3
    assert [row['checkpoint'] for row in report['learning_curve']] == [0, 32, 64, 128]
    assert report['learning_curve'][0]['methods']['LMTA_RI']['paired_differences']['MEAN_V44']['run_values'] == [-5., -6., -7.]
    assert len(report['endpoint_method_differences_descriptive']) == 3
    new, old = (report['accounting'][name] for name in ('new_candidate', 'retained_V44_control'))
    assert new['all_actual_events']['event_count'] == 1872
    assert old['all_actual_events']['event_count'] == 1912
    assert new['all_actual_events']['wall_seconds'] == 468.
    assert old['all_actual_events']['wall_seconds'] == 478.
    assert new['all_actual_events']['counters']['primitive_selections'] == 1872 * 70
    assert not [row for row in new['by_phase_method_run'] if row['phase'] == 'heuristic']
    assert sum(row['event_count'] for row in old['by_phase_method_run'] if row['phase'] == 'heuristic') == 40


@pytest.mark.parametrize('side', ['candidate', 'control'])
@pytest.mark.parametrize('failure', ['missing', 'duplicate'])
def test_incomplete_either_side_suppresses_signal_but_keeps_all_actual_costs(side, failure):
    candidate, candidate_manifest, control, control_manifest = fixture()
    events = candidate if side == 'candidate' else control
    position = next(i for i, row in enumerate(events) if row['phase'] == 'evaluation'
        and row['method'] == 'LMTA_RI' and row['checkpoint'] == 128)
    if failure == 'missing':
        events.pop(position)
    else:
        events.append(deepcopy(events[position]))
    report = analysis.summarize(candidate, candidate_manifest, control, control_manifest)
    assert not report['integrity']['passed'] and report['LMTA_continue_signal'] is None
    for rows, key in ((candidate, 'new_candidate'), (control, 'retained_V44_control')):
        fees = report['accounting'][key]['all_actual_events']
        assert fees['event_count'] == len(rows)
        assert fees['wall_seconds'] == .25 * len(rows)


@pytest.mark.parametrize('failure', ['shared_wrong_graph', 'shared_wrong_seed', 'protocol',
                                   'graph_metadata', 'initialization_seed', 'operator'])
def test_parameter_or_consistently_wrong_binding_cannot_produce_scientific_signal(failure):
    candidate, candidate_manifest, control, control_manifest = fixture()
    if failure.startswith('shared_wrong'):
        # Both sides remain internally paired, so the frozen formula must catch this.
        field = 'graph_id' if failure == 'shared_wrong_graph' else 'environment_seed'
        for row in candidate + control:
            if row['phase'] in ('evaluation', 'heuristic') and row['episode'] == 0:
                row[field] += 1
    elif failure == 'protocol':
        candidate_manifest['protocol']['budget'] = 71
    elif failure == 'graph_metadata':
        candidate_manifest['graphs'][0]['edges'] += 1
    elif failure == 'initialization_seed':
        candidate_manifest['completed_runs'][0]['initialization_seed'] += 1
    else:
        candidate_manifest['operator'] = 'MEAN'
    report = analysis.summarize(candidate, candidate_manifest, control, control_manifest)
    assert not report['integrity']['passed'] and report['LMTA_continue_signal'] is None
    assert report['accounting']['new_candidate']['all_actual_events']['event_count'] == 1872
    assert report['accounting']['retained_V44_control']['all_actual_events']['event_count'] == 1912


def test_better_intermediate_checkpoint_cannot_rescue_the_fixed_endpoint():
    candidate, candidate_manifest, control, control_manifest = fixture()
    for row in candidate:
        if row['phase'] == 'evaluation' and row['method'] == 'LMTA_RI':
            if row['checkpoint'] == 64:
                row['raw_return'] = 350. + row['episode']
            if row['checkpoint'] == 128:
                row['raw_return'] = 199. + row['run_id'] + row['episode']
    report = analysis.summarize(candidate, candidate_manifest, control, control_manifest)
    assert report['integrity']['passed'] and report['LMTA_continue_signal'] is False
    assert report['endpoint_comparisons']['LMTA_RI']['own_initial']['run_values'] == [-1., -1., -1.]
    assert report['learning_curve'][2]['descriptive_only']
    assert report['learning_curve'][2]['methods']['LMTA_RI']['paired_differences']['own_initial']['mean'] == 149.


def test_ci_uses_three_runs_not_sixty_panel_episodes():
    candidate, candidate_manifest, control, control_manifest = fixture()
    for row in candidate:
        if row['phase'] == 'evaluation' and row['method'] == 'LMTA_RI' and row['checkpoint'] == 128:
            row['raw_return'] = 201. + 2 * row['run_id'] + row['episode']
    report = analysis.summarize(candidate, candidate_manifest, control, control_manifest)
    difference = report['endpoint_comparisons']['LMTA_RI']['own_initial']
    assert difference['run_values'] == [1., 2., 3.]
    radius = analysis.v44.T95_DF2 / 3 ** .5
    assert difference['ci_95'] == pytest.approx([2 - radius, 2 + radius])
    assert difference['n_independent_training_runs'] == 3
    assert difference['all_runs_positive'] is True
    assert difference['all_positive_and_ci_lower_positive'] is False
