"""Analyze the fixed V44 endpoint using independent training runs as units."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import itertools
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
T95_DF2 = 4.302652729749
COUNTERS = ('primitive_selections', 'day_transitions', 'propagation_draws')


def run_statistics(values):
    """A t interval conditional on the fixed panel, never on its episode count."""
    complete = len(values) == 3 and all(value is not None and math.isfinite(value) for value in values)
    result = {'run_values': values, 'complete': complete, 'n_independent_training_runs':
        sum(value is not None and math.isfinite(value) for value in values)}
    if not complete:
        return {**result, 'mean': None, 'sample_std': None, 'ci_95': None,
            'all_runs_positive': None, 'all_positive_and_ci_lower_positive': None}
    mean = statistics.mean(values)
    deviation = statistics.stdev(values)
    radius = T95_DF2 * deviation / math.sqrt(3)
    return {**result, 'mean': mean, 'sample_std': deviation,
        'ci_95': [mean - radius, mean + radius], 'all_runs_positive': all(value > 0 for value in values),
        'all_positive_and_ci_lower_positive': all(value > 0 for value in values) and mean - radius > 0}


def event_key(row):
    phase = row.get('phase')
    if phase == 'train':
        return phase, row.get('run_id'), row.get('method'), row.get('episode')
    if phase == 'evaluation':
        return phase, row.get('run_id'), row.get('method'), row.get('checkpoint'), row.get('episode')
    return phase, row.get('method'), row.get('episode')


def expected_keys(protocol):
    runs = range(protocol['runs'])
    methods, panel = protocol['methods'], range(protocol['panel_size'])
    return ({('train', run, method, episode) for run, method, episode in
        itertools.product(runs, methods, range(protocol['training_episodes']))}
        | {('evaluation', run, method, checkpoint, episode) for run, method, checkpoint, episode in
            itertools.product(runs, methods, protocol['checkpoints'], panel)}
        | {('heuristic', method, episode) for method, episode in itertools.product(protocol['heuristics'], panel)})


def accounting(events, manifest):
    groups = defaultdict(lambda: {'event_count': 0, 'wall_seconds': 0.,
        'counters': Counter(), 'model_work': Counter()})
    total = {'event_count': len(events), 'wall_seconds': 0., 'counters': Counter(), 'model_work': Counter()}
    for row in events:
        group = groups[(row.get('phase'), row.get('method'), row.get('run_id'))]
        group['event_count'] += 1
        for target in (group, total):
            seconds = row.get('wall_seconds')
            if isinstance(seconds, (int, float)) and math.isfinite(seconds):
                target['wall_seconds'] += seconds
            for field in ('counters', 'model_work'):
                target[field].update({key: value for key, value in row.get(field, {}).items()
                    if isinstance(value, (int, float)) and math.isfinite(value)})
    records = [{'phase': phase, 'method': method, 'run_id': run, **cost}
        for (phase, method, run), cost in groups.items()]
    completed = manifest.get('completed_runs')
    initialization = sum(row['initialization_seconds'] for row in completed) if completed is not None else None
    retention = sum(row['model_save_seconds'] for row in completed) if completed is not None else None
    graph_seconds, full_seconds = manifest.get('graph_generation_seconds'), manifest.get('wall_seconds')
    components = [total['wall_seconds'], graph_seconds, initialization, retention]
    overhead = {'whole_runner_seconds': full_seconds, 'graph_generation_seconds': graph_seconds,
        'all_model_initialization_seconds': initialization, 'all_model_save_seconds': retention,
        'saved_policy_bytes': sum(row['model_bytes'] for row in completed) if completed is not None else None,
        'unitemized_runner_seconds': full_seconds - sum(components)
            if full_seconds is not None and all(value is not None for value in components) else None}
    return {'all_actual_events': total, 'by_phase_method_run': records, 'runner_costs': overhead,
        'scope': 'Every raw event is charged once, including duplicate or incomplete runs. '
            'Heuristic evaluations are sampled once and reused without multiplying their costs. '
            'Event wall spans exclude graph generation, initialization and other runner overhead, '
            'which are retained separately under runner_costs. Whole-run time contains these components; '
            'model-work counters are not additional environment samples.'}


def validate(events, manifest):
    protocol, errors = manifest['protocol'], []
    if manifest.get('status') != 'complete':
        errors.append('Manifest status is not complete')
    if protocol['runs'] != 3 or protocol['primary_checkpoint'] != 128:
        errors.append('Three training runs and primary checkpoint 128 are required')
    expected = expected_keys(protocol)
    indexed = defaultdict(list)
    panel_binding, training_binding = {}, {}
    training_graphs, evaluation_graphs = set(), set()
    training_seeds, evaluation_seeds = set(), set()
    for index, row in enumerate(events):
        key, phase = event_key(row), row.get('phase')
        indexed[key].append(row)
        problem = []
        if key not in expected:
            problem.append('unexpected identity')
        if phase == 'train' and row.get('checkpoint') != row.get('episode', -2) + 1:
            problem.append('training completed-episode checkpoint')
        if phase == 'heuristic' and (row.get('checkpoint') is not None or row.get('run_id') is not None):
            problem.append('heuristic must be sampled once with null checkpoint/run')
        reward, seconds = row.get('raw_return'), row.get('wall_seconds')
        if not isinstance(reward, (int, float)) or not math.isfinite(reward):
            problem.append('nonfinite/missing return')
        if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            problem.append('invalid event wall time')
        counts = row.get('counters', {})
        if any(not isinstance(counts.get(name), int) or counts[name] < 0 for name in COUNTERS):
            problem.append('invalid/missing physical counters')
        if counts.get('day_transitions') != protocol['horizon']:
            problem.append('incomplete episode calendar')
        if phase != 'train' and any('gradient_steps' in name and value != 0
                for name, value in row.get('model_work', {}).items()):
            problem.append('evaluation performed gradient updates')
        binding = row.get('graph_id'), row.get('environment_seed')
        if None in binding:
            problem.append('missing graph/environment identity')
        elif phase in ('evaluation', 'heuristic'):
            old = panel_binding.setdefault(row['episode'], binding)
            if old != binding:
                problem.append('shared panel graph/flow disagreement')
            evaluation_graphs.add(binding[0])
            evaluation_seeds.add(binding[1])
        elif phase == 'train':
            old = training_binding.setdefault((row['run_id'], row['episode']), binding)
            if old != binding:
                problem.append('paired training graph/flow disagreement')
            training_graphs.add(binding[0])
            training_seeds.add(binding[1])
        if problem:
            errors.append({'event_index': index, 'problems': problem})
    missing = expected - indexed.keys()
    duplicates = [key for key, rows in indexed.items() if len(rows) > 1]
    unexpected = indexed.keys() - expected
    if missing:
        errors.append({'missing_identities': sorted(missing, key=str)})
    if duplicates:
        errors.append({'duplicate_identities': duplicates})
    if unexpected:
        errors.append({'unexpected_identities': sorted(unexpected, key=str)})
    if training_graphs & evaluation_graphs:
        errors.append('Training and held-out graph IDs overlap')
    if training_seeds & evaluation_seeds:
        errors.append('Training and held-out environment seeds overlap')
    return {'passed': not errors, 'manifest_complete': manifest.get('status') == 'complete',
        'expected_events': len(expected), 'actual_events': len(events),
        'phase_event_counts': dict(Counter(row.get('phase') for row in events)),
        'missing_count': len(missing), 'duplicate_identity_count': len(duplicates),
        'unexpected_identity_count': len(unexpected), 'errors': errors}, indexed


def summarize(events, manifest):
    protocol = manifest['protocol']
    validation, indexed = validate(events, manifest)
    panel = range(protocol['panel_size'])
    runs, methods = range(protocol['runs']), protocol['methods']

    def value(key):
        rows = indexed.get(key, [])
        reward = rows[0].get('raw_return') if len(rows) == 1 else None
        return reward if isinstance(reward, (int, float)) and math.isfinite(reward) else None

    def paired_mean(left, right=None):
        a = [value(key) for key in left]
        b = [value(key) for key in right] if right is not None else [0.] * len(a)
        return statistics.mean(x - y for x, y in zip(a, b)) if all(
            x is not None and y is not None for x, y in zip(a, b)) else None

    def evaluation_keys(run, method, checkpoint):
        return [('evaluation', run, method, checkpoint, episode) for episode in panel]

    heuristic_keys = {name: [('heuristic', name, episode) for episode in panel]
        for name in protocol['heuristics']}
    heuristics = {name: {'panel_mean': paired_mean(keys), 'panel_size': protocol['panel_size'],
        'actual_unique_evaluations': sum(len(indexed.get(key, [])) == 1 for key in keys)}
        for name, keys in heuristic_keys.items()}
    curve, comparisons = [], {}
    for checkpoint in protocol['checkpoints']:
        row = {'checkpoint': checkpoint, 'descriptive_only': checkpoint != protocol['primary_checkpoint'], 'methods': {}}
        for method in methods:
            keys = {run: evaluation_keys(run, method, checkpoint) for run in runs}
            means = run_statistics([paired_mean(keys[run]) for run in runs])
            contrasts = {'own_initial': run_statistics([paired_mean(keys[run], evaluation_keys(run, method, 0)) for run in runs])}
            contrasts.update({name: run_statistics([paired_mean(keys[run], reference) for run in runs])
                for name, reference in heuristic_keys.items()})
            row['methods'][method] = {'raw_return': means, 'paired_differences': contrasts}
            if checkpoint == protocol['primary_checkpoint']:
                comparisons[method] = contrasts
        curve.append(row)
    primary = protocol['primary_checkpoint']
    method_differences = {left + '_minus_' + right: run_statistics([paired_mean(
        evaluation_keys(run, left, primary), evaluation_keys(run, right, primary)) for run in runs])
        for left, right in itertools.combinations(methods, 2)}
    required = {name: comparisons['LMTA_RI'][name]['all_positive_and_ci_lower_positive']
        for name in ('own_initial', 'AVERAGE_SCORE')}
    signal = all(required.values()) if validation['passed'] and all(value is not None for value in required.values()) else None
    return {'schema': 'acfqp.lmta_learnability_analysis.v44', 'protocol': protocol,
        'integrity': validation, 'accounting': accounting(events, manifest),
        'heuristic_panel_means': heuristics, 'learning_curve': curve,
        'primary_checkpoint': primary, 'endpoint_comparisons': comparisons,
        'endpoint_method_differences_descriptive': method_differences,
        'LMTA_continue_conditions': required, 'LMTA_continue_signal': signal,
        'inference_scope': 'Each value is a paired mean over the fixed held-out panel for one independently trained run. '
            'The three run means, not panel episodes or checkpoints, define the t interval (df=2). '
            'Intervals are conditional on this panel and assume normally distributed run differences; '
            'they do not measure population-graph uncertainty. Only checkpoint 128 enters the prespecified '
            'continuation signal. A false signal is a scientific result, not an execution failure. '
            'A null signal means execution evidence is incomplete or invalid.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_learnability_v44')
    args = parser.parse_args()
    manifest = json.loads((args.output_dir / 'manifest.json').read_text())
    events = [json.loads(line) for line in (args.output_dir / 'events.jsonl').read_text().splitlines()]
    report = summarize(events, manifest)
    (args.output_dir / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'integrity_passed': report['integrity']['passed'],
        'LMTA_continue_signal': report['LMTA_continue_signal'],
        'LMTA_endpoint': report['endpoint_comparisons']['LMTA_RI']}, indent=2))


if __name__ == '__main__':
    main()
