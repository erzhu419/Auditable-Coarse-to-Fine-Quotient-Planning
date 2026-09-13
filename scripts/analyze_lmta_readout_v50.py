"""Paired first-message readout diagnosis on unchanged V49 data and batches."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import importlib.util
import itertools
import json
import math
from pathlib import Path
import statistics
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v49 = load_helper('lmta_supervised_analysis_v49', 'analyze_lmta_supervised_v49.py')
v44 = load_helper('lmta_run_statistics_v44', 'analyze_lmta_learnability_v44.py')
FROZEN_PROTOCOL = dict(v49.FROZEN_PROTOCOL, architecture='NodeQ_plus_learned_first_message_linear',
    added_parameters=6, readout_initialization='zero', batch_source='V49_recorded_batches',
    float64_readout_tolerance=1e-12, float32_readout_tolerance=2e-6)
STATE_FIELDS = ('split', 'graph_id', 'day', 'remaining_budget', 'legal_nodes', 'teacher_node', 'best_score', 'pairwise_pairs')
PAIRED_METRICS = ('mean_relative_regret', 'optimal_rate', 'pairwise_accuracy', 'mse')


def key(row):
    return row.get('run_id'), row.get('checkpoint'), row.get('state_id')


def validate(metrics, manifest, training, information, old_metrics, old_manifest, old_training):
    errors = Counter()

    def check(name, passed):
        if not passed:
            errors[name] += 1

    for field, value in (('schema', 'acfqp.lmta_readout.v50'), ('status', 'complete'), ('protocol', FROZEN_PROTOCOL),
            ('source_directory', 'reports/lmta_supervised_v49'), ('dataset_path', 'reports/lmta_supervised_v49/dataset.npz'),
            ('dataset_bytes', old_manifest.get('dataset_bytes')), ('runtime', old_manifest.get('runtime')),
            ('graphs', old_manifest.get('graphs')), ('initial_anchors_complete', True), ('information_passed', True),
            ('new_environment_calls', 0), ('new_RL_training_updates', 0), ('new_MCTS_calls', 0)):
        check('manifest_' + field, manifest.get(field) == value)
    original = {key(row): row for row in old_metrics}
    expected = Counter(itertools.product(range(3), (0, 2000), range(1680)))
    counts = Counter(key(row) for row in metrics)
    check('metric_roster', counts == expected)
    initial_matches = 0
    for row in metrics:
        source = original.get(key(row))
        check('metric_schema_and_state_binding', source is not None and set(row) == set(source)
              and all(row.get(field) == source.get(field) for field in STATE_FIELDS))
        numeric = all(v49.finite(row.get(field)) for field in v49.METRIC_NUMBERS)
        check('metric_finite', numeric and all(math.isfinite(value) for value in row.values() if isinstance(value, (int, float))))
        if row.get('checkpoint') == 0:
            same = source is not None and row == source
            check('initial_metric_exact', same)
            initial_matches += same
        pairs = row.get('pairwise_pairs')
        check('pairwise_counts', isinstance(pairs, int) and pairs >= 0 and v49.finite(row.get('pairwise_correct'))
              and 0 <= row['pairwise_correct'] <= pairs)
        check('predicted_node', isinstance(row.get('predicted_node'), int) and 0 <= row['predicted_node'] < 500)
        if numeric:
            gap = row['best_score'] - row['chosen_score']
            relative = gap / row['best_score'] if row['best_score'] else 0.
            check('ranking_consistency', row['mse'] >= 0 and row['best_score'] >= row['chosen_score'] >= 0
                  and math.isclose(row['score_regret'], gap, rel_tol=1e-12, abs_tol=1e-12)
                  and math.isclose(row['relative_regret'], relative, rel_tol=1e-12, abs_tol=1e-12)
                  and isinstance(row.get('optimal'), bool) and row['optimal'] == (gap <= 1e-9))
    original_batches = {(row['run_id'], row['step']): row['batch_state_ids'] for row in old_training}
    steps, rows_by_run, presentations = Counter(), Counter(), Counter()
    batch_matches = 0
    for row in training:
        batch, identity = row.get('batch_state_ids'), (row.get('run_id'), row.get('step'))
        steps[identity] += 1
        rows_by_run[identity[0]] += 1
        if isinstance(batch, list):
            presentations[identity[0]] += len(batch)
        check('training_batch', isinstance(batch, list) and len(batch) == 4
              and all(isinstance(state, int) and 0 <= state < 1120 for state in batch) and len(set(batch)) == 4)
        same = batch == original_batches.get(identity)
        check('recorded_batch_exact', same)
        batch_matches += same
        check('training_loss', v49.finite(row.get('loss')) and row['loss'] >= 0)
    expected_steps = Counter(itertools.product(range(3), range(1, 2001)))
    check('training_step_roster', steps == expected_steps)
    runs = manifest.get('runs', [])
    check('run_roster', Counter(row.get('run_id') for row in runs) == Counter(range(3)))
    for row in runs:
        run = row.get('run_id')
        check('run_binding', isinstance(run, int) and 0 <= run < 3
              and row.get('initialization_seed') == 493001 + run and row.get('batch_seed') == 494001 + run
              and row.get('gradient_steps') == rows_by_run[run] == 2000
              and row.get('training_state_presentations') == presentations[run] == 8000
              and row.get('base_parameters') == 50433 and row.get('candidate_parameters') == 50439)
        evaluations = row.get('evaluations', [])
        check('run_evaluations', Counter(e.get('checkpoint') for e in evaluations) == Counter((0, 2000))
              and all(e.get('states') == sum(count for (r, checkpoint, _), count in counts.items()
                      if r == run and checkpoint == e.get('checkpoint')) == 1680
                      and e.get('initial_mismatch_count') == 0 for e in evaluations))
        weights = row.get('learned_message_weight')
        check('learned_readout_parameters', isinstance(weights, list) and len(weights) == 5
              and all(v49.finite(value) for value in weights) and v49.finite(row.get('learned_message_bias')))
        check('run_costs', all(v49.finite(row.get(field)) and row[field] >= 0 for field in
              ('initialization_seconds', 'training_seconds', 'model_serialization_seconds'))
              and all(v49.finite(e.get('wall_seconds')) and e['wall_seconds'] >= 0 for e in evaluations)
              and row.get('model_path') == f'models/run{run}.pt' and isinstance(row.get('model_bytes'), int) and row['model_bytes'] > 0)
    for field in ('source_read_seconds', 'graph_generation_seconds', 'tensor_preparation_seconds', 'information_check_seconds', 'wall_seconds'):
        check('runner_costs', v49.finite(manifest.get(field)) and manifest[field] >= 0)
    legal_by_graph = Counter()
    for row in old_metrics:
        if row['run_id'] == row['checkpoint'] == 0:
            legal_by_graph[row['graph_id']] += row['legal_nodes']
    info_rows = information.get('by_graph', [])
    check('information_summary', information.get('passed') is True and information.get('states') == 1680
          and information.get('legal_nodes') == sum(legal_by_graph.values())
          and v49.finite(information.get('wall_seconds')) and information['wall_seconds'] >= 0)
    check('information_graph_roster', Counter(row.get('graph_id') for row in info_rows) == Counter(legal_by_graph.keys()))
    for row in info_rows:
        check('information_graph_counts', row.get('states') == 70 and row.get('legal_nodes') == legal_by_graph.get(row.get('graph_id')))
    for precision, tolerance in (('float64', 1e-12), ('float32', 2e-6)):
        field = 'max_abs_error_' + precision
        check('information_' + precision, all(v49.finite(row.get(field)) and 0 <= row[field] <= tolerance
              for row in [information, *info_rows]))
    return dict(passed=not errors, errors=dict(errors), metric_records=len(metrics), expected_metric_records=10080,
        missing_metric_records=len(expected.keys() - counts.keys()), duplicate_metric_identities=sum(count > 1 for count in counts.values()),
        initial_metric_records_exact=initial_matches, expected_initial_metric_records=5040,
        training_records=len(training), expected_training_records=6000, recorded_batches_exact=batch_matches,
        missing_training_steps=len(expected_steps.keys() - steps.keys()))


def state_summaries(metrics):
    groups = defaultdict(list)
    for row in metrics:
        groups[row.get('run_id'), row.get('checkpoint'), row.get('split')].append(row)
    result = []
    for run, checkpoint, split in itertools.product(range(3), (0, 2000), ('train', 'heldout')):
        rows = groups[run, checkpoint, split]
        entry = dict(run_id=run, checkpoint=checkpoint, split=split, state_records=len(rows))
        usable = rows and all(all(v49.finite(row.get(field)) for field in v49.METRIC_NUMBERS)
            and isinstance(row.get('optimal'), bool) and isinstance(row.get('pairwise_pairs'), int) for row in rows)
        if usable:
            pairs = sum(row['pairwise_pairs'] for row in rows)
            entry.update(mean_score_regret=statistics.mean(row['score_regret'] for row in rows),
                mean_relative_regret=statistics.mean(row['relative_regret'] for row in rows),
                optimal_rate=statistics.mean(row['optimal'] for row in rows),
                pairwise_accuracy=sum(row['pairwise_correct'] for row in rows) / pairs if pairs else None,
                pairwise_pairs=pairs, mse=statistics.mean(row['mse'] for row in rows))
        else:
            entry.update({field: None for field in ('mean_score_regret', 'mean_relative_regret', 'optimal_rate', 'pairwise_accuracy', 'pairwise_pairs', 'mse')})
        result.append(entry)
    return result


def new_accounting(metrics, manifest, training, information):
    def total(rows, name):
        return sum(row[name] for row in rows if v49.finite(row.get(name)))

    runs = manifest.get('runs', [])
    evaluations = [e for row in runs for e in row.get('evaluations', [])]
    stages = {field.removesuffix('_seconds'): manifest.get(field) for field in
              ('source_read_seconds', 'graph_generation_seconds', 'tensor_preparation_seconds', 'information_check_seconds')}
    stages.update(initialization=total(runs, 'initialization_seconds'), supervised_training=total(runs, 'training_seconds'),
                  evaluation=total(evaluations, 'wall_seconds'), model_serialization=total(runs, 'model_serialization_seconds'))
    whole = manifest.get('wall_seconds')
    return dict(new_environment_samples=0, new_environment_calls=manifest.get('new_environment_calls'),
        new_RL_training_updates=manifest.get('new_RL_training_updates'), new_MCTS_calls=manifest.get('new_MCTS_calls'),
        gradient_update_records=len(training), training_state_presentations_recorded=sum(len(row['batch_state_ids'])
            for row in training if isinstance(row.get('batch_state_ids'), list)), evaluation_state_records=len(metrics),
        initial_anchor_state_evaluations=sum(row.get('checkpoint') == 0 for row in metrics),
        manifest_gradient_updates=total(runs, 'gradient_steps'),
        manifest_training_state_presentations=total(runs, 'training_state_presentations'),
        manifest_evaluation_states=total(evaluations, 'states'), wall_seconds_by_stage=stages, whole_runner_seconds=whole,
        unitemized_runner_seconds=whole - sum(stages.values()) if v49.finite(whole) and all(v49.finite(value) for value in stages.values()) else None,
        information_reported_wall_seconds=information.get('wall_seconds'), source_dataset_bytes=manifest.get('dataset_bytes'),
        new_model_bytes=total(runs, 'model_bytes'), added_parameters_per_model=6,
        scope='All new supervised updates and state evaluations, including the initial anchors, are charged. '
              'Recorded and manifest counts describe the same work and are not additive. Information report timing is '
              'included in its runner stage, not an additional charge. No old collection or dataset serialization is charged anew.')


def summarize(metrics, manifest, training, information, old_metrics, old_manifest, old_collections, old_training):
    source = v49.summarize(old_metrics, old_manifest, old_collections, old_training)
    candidate = validate(metrics, manifest, training, information, old_metrics, old_manifest, old_training)
    valid = source['integrity']['passed'] and candidate['passed']
    summaries = state_summaries(metrics)
    final = {(row['run_id'], row['split']): row for row in summaries if row['checkpoint'] == 2000}
    previous = {(row['run_id'], row['split']): row for row in source['summaries'] if row['checkpoint'] == 2000}
    conditions, outcome, paired = None, None, None
    if valid:
        conditions = [dict(run_id=run, **{split: dict(
            mean_relative_regret_passed=final[run, split]['mean_relative_regret'] <= .01,
            optimal_rate_passed=final[run, split]['optimal_rate'] >= .95,
            passed=final[run, split]['mean_relative_regret'] <= .01 and final[run, split]['optimal_rate'] >= .95)
            for split in ('train', 'heldout')}) for run in range(3)]
        outcome = ('FIT_NOT_ESTABLISHED' if not all(row['train']['passed'] for row in conditions)
                   else 'GENERALIZATION_NOT_ESTABLISHED' if not all(row['heldout']['passed'] for row in conditions)
                   else 'SUPERVISED_RANKING_LEARNED')
        paired = {split: {field: v44.run_statistics([final[run, split][field] - previous[run, split][field]
            if final[run, split][field] is not None and previous[run, split][field] is not None else None for run in range(3)])
            for field in PAIRED_METRICS} for split in ('train', 'heldout')}
    return dict(schema='acfqp.lmta_readout_analysis.v50', protocol=FROZEN_PROTOCOL,
        integrity=dict(passed=valid, candidate=candidate, source_V49=source['integrity']), valid_diagnostic=valid,
        summaries=summaries, final_criteria_by_run=conditions, diagnostic_outcome=outcome,
        paired_final_candidate_minus_V49=paired,
        retained_V49=dict(diagnostic_outcome=source['diagnostic_outcome'], summaries=source['summaries'],
                          final_criteria_by_run=source['final_criteria_by_run']),
        information=information,
        accounting=dict(new_readout=new_accounting(metrics, manifest, training, information), retained_V49=source['accounting']),
        inference_scope='Thresholds and state-weighted metrics are unchanged from V49. Every final candidate-minus-V49 '
            'difference uses the same data and recorded batches; descriptive t intervals use three run means (df=2). '
            'Lower relative regret/MSE and higher optimal rate/pairwise accuracy are better. These already-exposed heldout '
            'graphs provide a paired development comparison, not new generalization confirmation. Information recovery '
            'and finite-budget supervised learnability are distinct. No RL, online-return, adoption or continuation Gate is created; '
            'invalid evidence yields null outcome and paired contrasts while retaining all recorded and declared costs.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_readout_v50')
    parser.add_argument('--control-dir', type=Path, default=ROOT / 'reports/lmta_supervised_v49')
    args = parser.parse_args()
    start = perf_counter()

    def rows(directory, name):
        return [json.loads(line) for line in (directory / name).read_text().splitlines()]

    def document(directory, name):
        return json.loads((directory / name).read_text())

    report = summarize(rows(args.output_dir, 'metrics.jsonl'), document(args.output_dir, 'manifest.json'),
        rows(args.output_dir, 'training.jsonl'), document(args.output_dir, 'information.json'),
        rows(args.control_dir, 'metrics.jsonl'), document(args.control_dir, 'manifest.json'),
        rows(args.control_dir, 'collection.jsonl'), rows(args.control_dir, 'training.jsonl'))
    report['accounting']['analysis_wall_seconds_before_serialization'] = perf_counter() - start
    (args.output_dir / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(integrity_passed=report['integrity']['passed'], diagnostic_outcome=report['diagnostic_outcome'],
                         paired_final_candidate_minus_V49=report['paired_final_candidate_minus_V49']), indent=2))


if __name__ == '__main__':
    main()
