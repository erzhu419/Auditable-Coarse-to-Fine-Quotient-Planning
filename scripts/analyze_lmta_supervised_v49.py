"""Bounded supervised ranking diagnosis on fixed teacher states; no RL Gate."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import itertools
import json
import math
from pathlib import Path
import statistics
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
FROZEN_PROTOCOL = dict(train_graph_ids=list(range(440000, 440016)), heldout_graph_ids=list(range(490900, 490908)),
    train_environment_seeds=list(range(491000, 491016)), heldout_environment_seeds=list(range(492000, 492008)),
    nodes=500, p=.01, budget=70, horizon=10, runs=3, initialization_seeds=[493001, 493002, 493003],
    batch_seeds=[494001, 494002, 494003], steps=2000, batch_size=4, checkpoints=[0, 2000],
    learning_rate=.001, weight_decay=.00001, gradient_clip=5., target_tie_tolerance=1e-9,
    max_mean_relative_regret=.01, min_optimal_rate=.95, loss='state_mean_legal_node_mse',
    state_policy='AVERAGE_SCORE', operator='IC_SUM', dtype='float32')
GRAPH_BINDINGS = [(split, graph, seed) for split in ('train', 'heldout')
    for graph, seed in zip(FROZEN_PROTOCOL[split + '_graph_ids'], FROZEN_PROTOCOL[split + '_environment_seeds'])]
STATE_BINDINGS = {70 * index + local: (split, graph) for index, (split, graph, _) in enumerate(GRAPH_BINDINGS)
                  for local in range(70)}
PHYSICAL_COUNTERS = ('primitive_selections', 'day_transitions', 'propagation_draws')
METRIC_NUMBERS = ('mse', 'best_score', 'chosen_score', 'score_regret', 'relative_regret', 'pairwise_correct')


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def validate(metrics, manifest, collections, training):
    errors = Counter()

    def check(name, passed):
        if not passed:
            errors[name] += 1

    check('manifest_schema_status_protocol', manifest.get('schema') == 'acfqp.lmta_supervised.v49'
          and manifest.get('status') == 'complete' and manifest.get('protocol') == FROZEN_PROTOCOL)
    expected_graphs = Counter((split, graph) for split, graph, _ in GRAPH_BINDINGS)
    check('graph_roster', Counter((row.get('split'), row.get('graph_id')) for row in manifest.get('graphs', [])) == expected_graphs)
    for row in manifest.get('graphs', []):
        check('graph_size', row.get('nodes') == 500 and isinstance(row.get('edges'), int) and row['edges'] >= 0)
    check('collection_roster', Counter((row.get('split'), row.get('graph_id'), row.get('environment_seed'))
          for row in collections) == Counter(GRAPH_BINDINGS))
    for row in collections:
        counts = row.get('counters', {})
        check('collection_counts', row.get('state_count') == row.get('label_calls') == 70
              and row.get('label_node_evaluations') == 35000
              and counts.get('primitive_selections') == 70 and counts.get('day_transitions') == 10
              and all(isinstance(counts.get(name), int) and counts[name] >= 0 for name in PHYSICAL_COUNTERS))
        check('collection_finite', finite(row.get('raw_return')) and finite(row.get('wall_seconds')) and row['wall_seconds'] >= 0)

    metric_keys, state_metadata = Counter(), {}
    for row in metrics:
        run, checkpoint, state = row.get('run_id'), row.get('checkpoint'), row.get('state_id')
        metric_keys[run, checkpoint, state] += 1
        check('metric_state_binding', STATE_BINDINGS.get(state) == (row.get('split'), row.get('graph_id')))
        numeric_valid = all(finite(row.get(name)) for name in METRIC_NUMBERS)
        check('metric_finite', numeric_valid and all(math.isfinite(value) for value in row.values() if isinstance(value, (int, float))))
        check('metric_state_fields', isinstance(row.get('day'), int) and 0 <= row['day'] < 10
              and isinstance(row.get('remaining_budget'), int) and 1 <= row['remaining_budget'] <= 70
              and isinstance(row.get('legal_nodes'), int) and 1 <= row['legal_nodes'] <= 500
              and all(isinstance(row.get(name), int) and 0 <= row[name] < 500 for name in ('predicted_node', 'teacher_node')))
        pairs = row.get('pairwise_pairs')
        check('pairwise_counts', isinstance(pairs, int) and pairs >= 0 and finite(row.get('pairwise_correct'))
              and 0 <= row['pairwise_correct'] <= pairs)
        if numeric_valid:
            gap = row['best_score'] - row['chosen_score']
            relative = gap / row['best_score'] if row['best_score'] else 0.
            check('ranking_consistency', row['mse'] >= 0 and row['best_score'] >= row['chosen_score'] >= 0
                  and math.isclose(row['score_regret'], gap, rel_tol=1e-12, abs_tol=1e-12)
                  and math.isclose(row['relative_regret'], relative, rel_tol=1e-12, abs_tol=1e-12)
                  and isinstance(row.get('optimal'), bool) and row['optimal'] == (gap <= 1e-9))
        metadata = tuple(row.get(name) for name in ('split', 'graph_id', 'day', 'remaining_budget', 'legal_nodes', 'teacher_node', 'best_score'))
        check('state_metadata_reuse', state_metadata.setdefault(state, metadata) == metadata)
    expected_metrics = set(itertools.product(range(3), (0, 2000), range(1680)))
    missing_metrics = expected_metrics - metric_keys.keys()
    duplicate_metrics = sum(count > 1 for count in metric_keys.values())
    check('metric_roster', metric_keys == Counter(expected_metrics))

    training_keys, rows_by_run, presentations_by_run = Counter(), Counter(), Counter()
    for row in training:
        run, step, batch = row.get('run_id'), row.get('step'), row.get('batch_state_ids')
        training_keys[run, step] += 1
        rows_by_run[run] += 1
        if isinstance(batch, list):
            presentations_by_run[run] += len(batch)
        check('training_batch', isinstance(batch, list) and len(batch) == 4
              and all(isinstance(state, int) and 0 <= state < 1120 for state in batch) and len(set(batch)) == 4)
        check('training_loss', finite(row.get('loss')) and row['loss'] >= 0)
    expected_steps = set(itertools.product(range(3), range(1, 2001)))
    check('training_step_roster', training_keys == Counter(expected_steps))
    runs = manifest.get('runs', [])
    check('manifest_run_roster', Counter(row.get('run_id') for row in runs) == Counter(range(3)))
    for row in runs:
        run = row.get('run_id')
        check('training_run_binding', isinstance(run, int) and 0 <= run < 3
              and row.get('initialization_seed') == 493001 + run and row.get('batch_seed') == 494001 + run
              and row.get('gradient_steps') == rows_by_run[run] == 2000
              and row.get('training_state_presentations') == presentations_by_run[run] == 8000)
        evaluations = row.get('evaluations', [])
        check('manifest_evaluations', Counter(e.get('checkpoint') for e in evaluations) == Counter((0, 2000))
              and all(e.get('states') == sum(count for (r, checkpoint, _), count in metric_keys.items()
                      if r == run and checkpoint == e.get('checkpoint')) == 1680 for e in evaluations))
        check('run_cost_fields', all(finite(row.get(name)) and row[name] >= 0 for name in
              ('initialization_seconds', 'training_seconds', 'model_serialization_seconds'))
              and all(finite(e.get('wall_seconds')) and e['wall_seconds'] >= 0 for e in evaluations)
              and isinstance(row.get('model_bytes'), int) and row['model_bytes'] > 0
              and row.get('model_path') == f'models/run{run}.pt')
    for name in ('graph_generation_seconds', 'dataset_serialization_seconds', 'tensor_preparation_seconds', 'wall_seconds'):
        check('runner_cost_fields', finite(manifest.get(name)) and manifest[name] >= 0)
    return dict(passed=not errors, errors=dict(errors), expected_metric_records=10080,
        actual_metric_records=len(metrics), missing_metric_records=len(missing_metrics), duplicate_metric_identities=duplicate_metrics,
        expected_training_records=6000, actual_training_records=len(training),
        missing_training_steps=len(expected_steps - training_keys.keys()),
        duplicate_training_step_identities=sum(count > 1 for count in training_keys.values()),
        expected_collection_records=24, actual_collection_records=len(collections))


def accounting(metrics, manifest, collections, training):
    def total(rows, name):
        return sum(row[name] for row in rows if finite(row.get(name)))

    runs = manifest.get('runs', [])
    evaluations = [evaluation for row in runs for evaluation in row.get('evaluations', [])]
    counters = Counter()
    for row in collections:
        counters.update({key: value for key, value in row.get('counters', {}).items() if finite(value)})
    stages = dict(collection=total(collections, 'wall_seconds'), initialization=total(runs, 'initialization_seconds'),
        supervised_training=total(runs, 'training_seconds'), evaluation=total(evaluations, 'wall_seconds'),
        model_serialization=total(runs, 'model_serialization_seconds'))
    stages.update({name.removesuffix('_seconds'): manifest.get(name) for name in
                  ('graph_generation_seconds', 'dataset_serialization_seconds', 'tensor_preparation_seconds')})
    whole = manifest.get('wall_seconds')
    return dict(collection_episodes_recorded=len(collections), new_physical_counters=dict(counters),
        teacher_states_recorded=total(collections, 'state_count'), analytical_label_calls=total(collections, 'label_calls'),
        analytical_label_node_evaluations=total(collections, 'label_node_evaluations'),
        gradient_update_records=len(training), training_state_presentations_recorded=sum(len(row['batch_state_ids'])
            for row in training if isinstance(row.get('batch_state_ids'), list)), evaluation_state_records=len(metrics),
        manifest_gradient_updates=total(runs, 'gradient_steps'),
        manifest_training_state_presentations=total(runs, 'training_state_presentations'),
        manifest_evaluation_states=total(evaluations, 'states'),
        new_RL_training_updates=0, new_MCTS_calls=0,
        wall_seconds_by_stage=stages, whole_runner_seconds=whole,
        unitemized_runner_seconds=whole - sum(stages.values()) if finite(whole) and all(finite(value) for value in stages.values()) else None,
        dataset_bytes=manifest.get('dataset_bytes'), model_bytes=total(runs, 'model_bytes'),
        retained_history_reference=manifest.get('retained_history'),
        scope='All collection records, updates, presentations and evaluations remain charged. Manifest counters and '
              'raw-record counts are two records of the same work, not additive fees; disagreements remain visible. '
              'Training presentations and repeated state evaluations reuse the fixed teacher data, not new environment samples. '
              'Whole-run time contains the listed stages. Earlier experimental costs are not refunded.')


def summarize(metrics, manifest, collections, training):
    integrity = validate(metrics, manifest, collections, training)
    groups = defaultdict(list)
    for row in metrics:
        groups[row.get('run_id'), row.get('checkpoint'), row.get('split')].append(row)
    summaries = []
    final = {}
    for run, checkpoint, split in itertools.product(range(3), (0, 2000), ('train', 'heldout')):
        rows = groups[run, checkpoint, split]
        valid_rows = bool(rows) and all(all(finite(row.get(name)) for name in METRIC_NUMBERS)
            and isinstance(row.get('optimal'), bool) and isinstance(row.get('pairwise_pairs'), int) for row in rows)
        result = dict(run_id=run, checkpoint=checkpoint, split=split, state_records=len(rows))
        if valid_rows:
            pairs = sum(row['pairwise_pairs'] for row in rows)
            result.update(mean_score_regret=statistics.mean(row['score_regret'] for row in rows),
                mean_relative_regret=statistics.mean(row['relative_regret'] for row in rows),
                optimal_rate=statistics.mean(row['optimal'] for row in rows),
                pairwise_accuracy=sum(row['pairwise_correct'] for row in rows) / pairs if pairs else None,
                pairwise_pairs=pairs, mse=statistics.mean(row['mse'] for row in rows))
        else:
            result.update({key: None for key in ('mean_score_regret', 'mean_relative_regret', 'optimal_rate', 'pairwise_accuracy', 'pairwise_pairs', 'mse')})
        summaries.append(result)
        if checkpoint == 2000:
            final[run, split] = result
    conditions, outcome = None, None
    if integrity['passed']:
        conditions = [dict(run_id=run, **{split: dict(
            mean_relative_regret_passed=final[run, split]['mean_relative_regret'] <= .01,
            optimal_rate_passed=final[run, split]['optimal_rate'] >= .95,
            passed=final[run, split]['mean_relative_regret'] <= .01 and final[run, split]['optimal_rate'] >= .95)
            for split in ('train', 'heldout')}) for run in range(3)]
        outcome = ('FIT_NOT_ESTABLISHED' if not all(row['train']['passed'] for row in conditions)
                   else 'GENERALIZATION_NOT_ESTABLISHED' if not all(row['heldout']['passed'] for row in conditions)
                   else 'SUPERVISED_RANKING_LEARNED')
    return dict(schema='acfqp.lmta_supervised_analysis.v49', protocol=FROZEN_PROTOCOL, integrity=integrity,
        valid_diagnostic=integrity['passed'], summaries=summaries, final_criteria_by_run=conditions,
        diagnostic_outcome=outcome, accounting=accounting(metrics, manifest, collections, training),
        inference_scope='State means weight each retained teacher state equally; pairwise accuracy sums correct pair credit '
            'over all counted non-tied teacher-score pairs. Each of three runs must independently meet both final thresholds '
            'on train and then heldout. Initial metrics are descriptive. This is a fixed-budget supervised ranking diagnosis '
            'on average-score teacher states, not evidence about RL targets, LMTA benefit, arbitrary visited states, or adoption. '
            'Invalid or incomplete evidence produces a null outcome while its recorded and declared costs remain retained.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_supervised_v49')
    args = parser.parse_args()
    start = perf_counter()

    def read_rows(name):
        return [json.loads(line) for line in (args.output_dir / name).read_text().splitlines()]

    manifest = json.loads((args.output_dir / 'manifest.json').read_text())
    report = summarize(read_rows('metrics.jsonl'), manifest, read_rows('collection.jsonl'), read_rows('training.jsonl'))
    report['accounting']['analysis_wall_seconds_before_serialization'] = perf_counter() - start
    (args.output_dir / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(integrity_passed=report['integrity']['passed'], diagnostic_outcome=report['diagnostic_outcome'],
                         final_criteria_by_run=report['final_criteria_by_run']), indent=2))


if __name__ == '__main__':
    main()
