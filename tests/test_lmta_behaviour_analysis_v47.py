"""Synthetic log summaries only; no environment, network, or checkpoint loading."""
import importlib.util
import itertools
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location('lmta_behaviour_v47',
    Path(__file__).resolve().parents[1] / 'scripts/analyze_lmta_behaviour_v47.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def fixture():
    rows = []
    for method, run, checkpoint, episode in itertools.product(analysis.METHODS, range(3), analysis.CHECKPOINTS, range(20)):
        durations = [0] * 10
        # Different denominators make a mean of per-episode ratios demonstrably wrong.
        durations[0 if episode < 10 else 9] = 1 if episode < 10 else 3
        if checkpoint == 128:
            durations = list(reversed(durations))
        row = dict(phase='evaluation', method=method, run_id=run, checkpoint=checkpoint,
            episode=episode, raw_return=20. + (checkpoint == 128) * (run - 1), wall_seconds=.1,
            daily_durations=durations, counters=dict(primitive_selections=sum(durations), day_transitions=10, propagation_draws=5),
            model_work={})
        if method != 'FLAT_DQN':
            row['daily_budgets'] = durations.copy()
            row['daily_budgets'][4] += 1
        if method == 'LMTA_RI':
            row['subgoals'] = [2] * 9 + [7]
        rows.append(row)
    rows.append(dict(phase='train', wall_seconds=2., counters=dict(primitive_selections=70, day_transitions=10,
        propagation_draws=500), model_work=dict(HL_gradient_steps=1)))
    return rows


def test_all_groups_use_actual_selection_weights_and_preserve_zero_day_goals_and_costs():
    report = analysis.summarize(fixture())
    assert report['evaluation_event_count'] == 720
    assert len(report['summaries']) == 36
    row = next(row for row in report['summaries'] if row['method'] == 'LMTA_RI'
               and row['run_id'] == 0 and row['checkpoint'] == 32)
    assert row['mean_daily_durations'] == [.5, 0., 0., 0., 0., 0., 0., 0., 0., 1.5]
    assert row['selection_weighted_mean_day'] == 6.75
    assert row['first_five_day_selection_share'] == .25
    assert row['last_day_selection_share'] == .75
    assert row['mean_zero_selection_days'] == 9.
    assert row['subgoals']['counts'] == {2: 180, 7: 20}
    assert row['subgoals']['unique_count'] == 2
    assert row['subgoals']['daily_decision_count'] == 200
    assert row['budget_minus_duration']['absolute_total'] == 20
    assert row['budget_minus_duration']['nonzero_day_count'] == 20
    costs = report['accounting']
    assert costs['new_environment_samples'] == costs['new_environment_calls'] == costs['new_network_calls'] == 0
    assert costs['retained_source_event_count'] == 721
    assert costs['retained_source_counters']['primitive_selections'] == 1440 + 70
    assert costs['retained_source_event_wall_seconds'] == pytest.approx(74.)
    assert costs['retained_source_model_work'] == {'HL_gradient_steps': 1}


def test_fixed_comparisons_retain_improved_unchanged_and_degraded_runs():
    report = analysis.summarize(fixture())
    comparisons = report['checkpoint_32_to_128']
    assert len(comparisons) == 9
    for method in analysis.METHODS:
        subset = [row for row in comparisons if row['method'] == method]
        assert [row['delta']['mean_raw_return'] for row in subset] == [-1., 0., 1.]
        assert all(row['from_checkpoint'] == 32 and row['to_checkpoint'] == 128 for row in subset)
        assert all(row['delta']['selection_weighted_mean_day'] == -4.5 for row in subset)
    flat = next(row for row in report['summaries'] if row['method'] == 'FLAT_DQN')
    assert 'budget_minus_duration' not in flat and 'subgoals' not in flat


@pytest.mark.parametrize('failure', ['missing', 'duplicate', 'missing_duration'])
def test_incomplete_behaviour_cannot_be_silently_treated_as_a_full_panel(failure):
    rows = fixture()
    if failure == 'missing':
        rows.pop(0)
    elif failure == 'duplicate':
        rows.append(rows[0].copy())
    else:
        del rows[0]['daily_durations']
    with pytest.raises(ValueError):
        analysis.summarize(rows)


def test_equal_group_means_do_not_imply_identical_paired_episode_schedules():
    rows = fixture()
    before = {row['episode']: row for row in rows if row.get('method') == 'BUDGET_HRL'
              and row.get('run_id') == 2 and row.get('checkpoint') == 32}
    for row in rows:
        if row.get('method') == 'BUDGET_HRL' and row.get('run_id') == 2 and row.get('checkpoint') == 128:
            # Permute complete schedules across paired episodes, preserving all group means.
            source = before[(row['episode'] + 10) % 20]
            row['daily_durations'] = source['daily_durations'].copy()
            row['daily_budgets'] = source['daily_budgets'].copy()
            row['counters']['primitive_selections'] = sum(row['daily_durations'])
    report = analysis.summarize(rows)
    comparisons = report['checkpoint_32_to_128']
    assert len(comparisons) == 9 and all(row['paired_episode_count'] == 20 for row in comparisons)
    target = next(row for row in comparisons if row['method'] == 'BUDGET_HRL' and row['run_id'] == 2)
    assert target['delta']['mean_daily_durations'] == [0.] * 10
    assert target['identical_full_sequence_counts'] == {'daily_durations': 0, 'daily_budgets': 0}
    for row in comparisons:
        if row['method'] == 'LMTA_RI':
            assert row['identical_full_sequence_counts']['subgoals'] == 20
        if row['method'] == 'FLAT_DQN':
            assert set(row['identical_full_sequence_counts']) == {'daily_durations'}
