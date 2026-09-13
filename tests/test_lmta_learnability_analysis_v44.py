import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location('analyze_lmta_v44',
    Path(__file__).resolve().parents[1] / 'scripts/analyze_lmta_learnability_v44.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def fixture():
    protocol = {'runs': 3, 'training_episodes': 128, 'checkpoints': [0, 32, 64, 128],
        'panel_size': 20, 'methods': ['FLAT_DQN', 'BUDGET_HRL', 'LMTA_RI'],
        'heuristics': ['AVERAGE_RANDOM', 'AVERAGE_SCORE'], 'horizon': 10,
        'primary_checkpoint': 128}
    events = []
    for key in sorted(analysis.expected_keys(protocol), key=str):
        phase = key[0]
        if phase == 'train':
            _, run, method, episode = key
            checkpoint = episode + 1
            graph, seed = 440000 + run * 100 + episode // 8, 441000 + run * 1000 + episode
            reward = 150.
        elif phase == 'evaluation':
            _, run, method, checkpoint, episode = key
            graph, seed = 440900 + episode // 2, 446000 + episode
            reward = 160. + run + episode + (40. + run if checkpoint else 0.)
        else:
            _, method, episode = key
            run = checkpoint = None
            graph, seed = 440900 + episode // 2, 446000 + episode
            reward = (180. if method == 'AVERAGE_SCORE' else 150.) + episode
        events.append({'phase': phase, 'run_id': run, 'method': method,
            'checkpoint': checkpoint, 'episode': episode, 'graph_id': graph,
            'environment_seed': seed, 'raw_return': reward, 'wall_seconds': .25,
            'counters': {'primitive_selections': 70, 'day_transitions': 10, 'propagation_draws': 100},
            'model_work': {'LL_gradient_steps': 1 if phase == 'train' else 0}})
    return events, {'status': 'complete', 'protocol': protocol}


def test_complete_design_uses_three_run_means_and_charges_heuristics_once():
    events, manifest = fixture()
    manifest.update(graph_generation_seconds=2., wall_seconds=485., completed_runs=[{
        'initialization_seconds': .1, 'model_save_seconds': .2, 'model_bytes': 100} for _ in range(9)])
    # Using less than K remains legitimate when no legal seeds are left.
    events[0]['counters']['primitive_selections'] = 69
    report = analysis.summarize(events, manifest)
    assert report['integrity']['passed']
    assert report['integrity']['expected_events'] == 1912
    assert report['integrity']['phase_event_counts'] == {'train': 1152, 'evaluation': 720, 'heuristic': 40}
    assert report['LMTA_continue_signal'] is True
    own = report['endpoint_comparisons']['LMTA_RI']['own_initial']
    assert own['run_values'] == [40., 41., 42.]
    assert own['n_independent_training_runs'] == 3
    assert own['mean'] == 41.
    assert report['endpoint_comparisons']['LMTA_RI']['AVERAGE_SCORE']['run_values'] == [20., 22., 24.]
    fees = report['accounting']['all_actual_events']
    assert fees['event_count'] == 1912
    assert fees['wall_seconds'] == 478.
    assert fees['counters']['primitive_selections'] == 1912 * 70 - 1
    assert fees['counters']['day_transitions'] == 19120
    assert fees['model_work']['LL_gradient_steps'] == 1152
    heuristic_costs = [row for row in report['accounting']['by_phase_method_run'] if row['phase'] == 'heuristic']
    assert len(heuristic_costs) == 2
    assert sum(row['event_count'] for row in heuristic_costs) == 40
    assert all(row['run_id'] is None for row in heuristic_costs)
    overhead = report['accounting']['runner_costs']
    assert overhead['saved_policy_bytes'] == 900
    assert overhead['unitemized_runner_seconds'] == pytest.approx(2.3)


def test_endpoint_is_fixed_even_when_middle_checkpoints_look_better():
    events, manifest = fixture()
    for row in events:
        if row['phase'] == 'evaluation' and row['method'] == 'LMTA_RI' and row['checkpoint'] == 128:
            row['raw_return'] = 159. + row['run_id'] + row['episode']
    report = analysis.summarize(events, manifest)
    assert report['integrity']['passed']
    assert report['LMTA_continue_signal'] is False
    assert report['endpoint_comparisons']['LMTA_RI']['own_initial']['run_values'] == [-1., -1., -1.]
    middle = next(row for row in report['learning_curve'] if row['checkpoint'] == 64)
    assert middle['descriptive_only']
    assert middle['methods']['LMTA_RI']['paired_differences']['own_initial']['mean'] == 41.


@pytest.mark.parametrize('failure', ['missing', 'duplicate', 'panel_binding', 'seed_overlap'])
def test_invalid_evidence_suppresses_signal_and_preserves_all_raw_costs(failure):
    events, manifest = fixture()
    target = next(i for i, row in enumerate(events) if row['phase'] == 'evaluation'
        and row['method'] == 'LMTA_RI' and row['checkpoint'] == 128)
    if failure == 'missing':
        events.pop(target)
    elif failure == 'duplicate':
        events.append(events[target].copy())
    elif failure == 'panel_binding':
        events[target]['environment_seed'] += 100
    else:
        for row in events:
            if row['phase'] != 'train' and row['episode'] == 0:
                row['environment_seed'] = 441000
    report = analysis.summarize(events, manifest)
    assert not report['integrity']['passed']
    assert report['LMTA_continue_signal'] is None
    assert report['accounting']['all_actual_events']['event_count'] == len(events)
    assert report['accounting']['all_actual_events']['wall_seconds'] == len(events) * .25
    if failure in ('missing', 'duplicate'):
        assert not report['endpoint_comparisons']['LMTA_RI']['own_initial']['complete']


def test_t_interval_has_df_two_not_panel_episode_count():
    result = analysis.run_statistics([1., 2., 3.])
    half_width = analysis.T95_DF2 / 3 ** .5
    assert result['ci_95'] == pytest.approx([2 - half_width, 2 + half_width])
    assert result['all_runs_positive'] is True
    assert result['all_positive_and_ci_lower_positive'] is False
    assert analysis.run_statistics([1., None, 3.])['ci_95'] is None
