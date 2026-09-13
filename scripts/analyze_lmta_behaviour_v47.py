"""Describe all retained V46 evaluation behaviours without environment/model calls."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import itertools
import json
from pathlib import Path
import statistics
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
METHODS = ('FLAT_DQN', 'BUDGET_HRL', 'LMTA_RI')
CHECKPOINTS = (0, 32, 64, 128)


def group_summary(rows, method):
    durations = [row.get('daily_durations') for row in rows]
    if any(not isinstance(values, list) or len(values) != 10
           or any(not isinstance(value, int) or value < 0 for value in values)
           for values in durations):
        raise ValueError('Every evaluation must retain ten actual nonnegative integer durations')
    if any(sum(values) != row['counters']['primitive_selections'] for row, values in zip(rows, durations)):
        raise ValueError('Retained durations disagree with actual primitive selections')
    daily_totals = [sum(values[day] for values in durations) for day in range(10)]
    total = sum(daily_totals)
    summary = dict(episode_count=len(rows), mean_raw_return=statistics.mean(row['raw_return'] for row in rows),
        mean_daily_durations=[value / len(rows) for value in daily_totals],
        total_actual_selections=total,
        selection_weighted_mean_day=sum(day * value for day, value in enumerate(daily_totals)) / total if total else None,
        first_five_day_selection_share=sum(daily_totals[:5]) / total if total else None,
        last_day_selection_share=daily_totals[-1] / total if total else None,
        mean_zero_selection_days=sum(value == 0 for values in durations for value in values) / len(rows))
    if method != 'FLAT_DQN':
        budgets = [row.get('daily_budgets') for row in rows]
        if any(not isinstance(values, list) or len(values) != 10
               or any(not isinstance(value, int) or value < 0 for value in values)
               for values in budgets):
            raise ValueError('Both hierarchical methods must retain all ten requested budgets')
        gaps = [[budget - duration for budget, duration in zip(b, d)] for b, d in zip(budgets, durations)]
        summary['budget_minus_duration'] = dict(
            daily_mean=[statistics.mean(row[day] for row in gaps) for day in range(10)],
            signed_total=sum(sum(row) for row in gaps),
            absolute_total=sum(abs(value) for row in gaps for value in row),
            nonzero_day_count=sum(value != 0 for row in gaps for value in row),
            max_absolute_gap=max(abs(value) for row in gaps for value in row))
    if method == 'LMTA_RI':
        goals = [row.get('subgoals') for row in rows]
        if any(not isinstance(values, list) or len(values) != 10
               or any(not isinstance(z, int) or not 0 <= z < 32 for z in values) for values in goals):
            raise ValueError('LMTA must retain all ten subgoal choices in 0..31')
        counts = Counter(z for values in goals for z in values)
        summary['subgoals'] = dict(unique_count=len(counts), daily_decision_count=sum(counts.values()),
            counts=dict(sorted(counts.items())),
            proportions={z: count / sum(counts.values()) for z, count in sorted(counts.items())},
            scope='All daily decisions, including days with zero actual selections.')
    return summary


def summarize(events):
    evaluation = [row for row in events if row.get('phase') == 'evaluation']
    keys = [(row.get('method'), row.get('run_id'), row.get('checkpoint'), row.get('episode')) for row in evaluation]
    expected = itertools.product(METHODS, range(3), CHECKPOINTS, range(20))
    if Counter(keys) != Counter(expected):
        raise ValueError('All 720 distinct method/run/checkpoint/panel evaluations are required')
    grouped = defaultdict(list)
    for row in evaluation:
        grouped[(row['method'], row['run_id'], row['checkpoint'])].append(row)
    summaries = {key: group_summary(rows, key[0]) for key, rows in sorted(grouped.items())}
    comparisons = []
    scalar_names = ('mean_raw_return', 'selection_weighted_mean_day', 'first_five_day_selection_share',
                    'last_day_selection_share', 'mean_zero_selection_days')
    for method, run in itertools.product(METHODS, range(3)):
        before, after = summaries[method, run, 32], summaries[method, run, 128]
        delta = {name: after[name] - before[name]
                 if after[name] is not None and before[name] is not None else None for name in scalar_names}
        delta['mean_daily_durations'] = [a - b for a, b in zip(after['mean_daily_durations'], before['mean_daily_durations'])]
        before_rows = {row['episode']: row for row in grouped[method, run, 32]}
        after_rows = {row['episode']: row for row in grouped[method, run, 128]}
        fields = ['daily_durations']
        if method != 'FLAT_DQN':
            fields.append('daily_budgets')
        if method == 'LMTA_RI':
            fields.append('subgoals')
        matches = {field: sum(before_rows[episode][field] == after_rows[episode][field]
                             for episode in range(20)) for field in fields}
        comparisons.append(dict(method=method, run_id=run, from_checkpoint=32, to_checkpoint=128,
            delta=delta, paired_episode_count=20, identical_full_sequence_counts=matches))
    source_counters, source_work = Counter(), Counter()
    for row in events:
        source_counters.update(row.get('counters', {}))
        source_work.update(row.get('model_work', {}))
    return dict(schema='acfqp.lmta_behaviour.v47', evaluation_event_count=len(evaluation),
        summaries=[dict(method=method, run_id=run, checkpoint=checkpoint, **summary)
            for (method, run, checkpoint), summary in summaries.items()],
        checkpoint_32_to_128=comparisons,
        sequence_comparison_scope='Supplemental description added after reviewing group means; '
            'all nine comparisons retain all 20 episodes paired by the original panel episode ID. '
            'Sequence matches require all ten daily entries to be identical, not only their group means.',
        accounting=dict(new_environment_samples=0, new_environment_calls=0, new_network_calls=0,
            retained_source_event_count=len(events), retained_source_phase_counts=dict(Counter(row['phase'] for row in events)),
            retained_source_event_wall_seconds=sum(row['wall_seconds'] for row in events),
            retained_source_counters=dict(source_counters), retained_source_model_work=dict(source_work),
            original_full_cost_reference='reports/lmta_weighted_v46/analysis.json',
            scope='All supplied source events, including training, remain charged once. '
                  'Original graph/setup/retention and full runner costs remain in the V46 analysis; none are refunded.'),
        interpretation_scope='All 720 evaluations and all nine method/run comparisons from 32 to 128 are retained. '
            'Timing measures use actual primitive selections; day indices are 0..9 and the first five days are 0..4. '
            'Weighted day and shares use total actual selections across the group, not unweighted episode ratios. '
            'These summaries describe allocation timing, recorded returns, and subgoal use. They cannot establish '
            'causal mechanisms, independent statistical significance, subgoal semantic collapse, or value calibration; '
            'the events do not retain daily rewards for the latter.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path, default=ROOT / 'reports/lmta_weighted_v46/events.jsonl')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/lmta_mechanism_v47/behaviour.json')
    args = parser.parse_args()
    start = perf_counter()
    events = [json.loads(line) for line in args.events.read_text().splitlines()]
    report = summarize(events)
    report['accounting']['analysis_wall_seconds_before_serialization'] = perf_counter() - start
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(output=str(args.output), evaluations=report['evaluation_event_count'],
                         groups=len(report['summaries']), comparisons=len(report['checkpoint_32_to_128']))))


if __name__ == '__main__':
    main()
