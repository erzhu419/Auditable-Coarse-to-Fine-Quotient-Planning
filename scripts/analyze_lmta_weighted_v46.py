"""Analyze fixed IC_SUM retraining against retained V44 controls; no new evaluation."""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import itertools
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('lmta_analysis_v44',
    Path(__file__).with_name('analyze_lmta_learnability_v44.py'))
v44 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v44)
METHODS = ['FLAT_DQN', 'BUDGET_HRL', 'LMTA_RI']
HEURISTICS = ['AVERAGE_RANDOM', 'AVERAGE_SCORE']
FROZEN_PROTOCOL = dict(runs=3, training_episodes=128, checkpoints=[0, 32, 64, 128],
    panel_size=20, methods=METHODS, heuristics=[], horizon=10,
    primary_checkpoint=128, nodes=500, budget=70, p=.01, graph_rotation_every=8)
GRAPH_IDS = {440000 + 100 * run + index for run in range(3) for index in range(16)} | set(range(440900, 440910))


def validate_side(events, manifest, *, candidate):
    protocol = {**FROZEN_PROTOCOL, 'heuristics': [] if candidate else HEURISTICS}
    integrity, indexed = v44.validate(events, {**manifest, 'protocol': protocol})
    errors = []
    if manifest.get('protocol') != protocol:
        errors.append('Protocol differs from the frozen V46/V44 design')
    if candidate and manifest.get('operator') != 'IC_SUM':
        errors.append('Candidate operator must be IC_SUM')
    if candidate and manifest.get('control_directory') != 'reports/lmta_learnability_v44':
        errors.append('Candidate must identify the retained V44 control directory')
    if not candidate and manifest.get('schema') != 'acfqp.lmta_learnability.v44':
        errors.append('Control must be the V44 retained mean-aggregation run')
    graphs = manifest.get('graphs', [])
    if (len(graphs) != 58 or {row.get('graph_id') for row in graphs} != GRAPH_IDS
            or any(row.get('nodes') != 500 for row in graphs)):
        errors.append('The exact 58 retained graph IDs with 500 nodes are required')
    completed = manifest.get('completed_runs', [])
    identities = [(row.get('run_id'), row.get('method')) for row in completed]
    if Counter(identities) != Counter(itertools.product(range(3), METHODS)):
        errors.append('Exactly nine completed method/run records are required')
    if candidate and any(row.get('initialization_seed') != 445001 + row['run_id']
                         for row in completed if isinstance(row.get('run_id'), int)):
        errors.append('Candidate initialization seed differs from 445001 + run_id')
    for index, row in enumerate(events):
        phase, run, episode = row.get('phase'), row.get('run_id'), row.get('episode')
        if not isinstance(episode, int):
            continue  # Invalid identities are already retained by V44 validation.
        if phase == 'train' and isinstance(run, int):
            expected = 440000 + 100 * run + episode // 8, 441000 + 1000 * run + episode
        elif phase in ('evaluation', 'heuristic'):
            expected = 440900 + episode // 2, 446000 + episode
        else:
            continue
        if (row.get('graph_id'), row.get('environment_seed')) != expected:
            errors.append({'event_index': index, 'problem': 'Graph/environment seed violates the frozen formula'})
        if phase == 'heuristic' and row.get('action_seed') != 449000 + episode:
            errors.append({'event_index': index, 'problem': 'Retained heuristic action seed differs'})
    return {**integrity, 'passed': integrity['passed'] and not errors,
            'frozen_binding_errors': errors}, indexed


def summarize(candidate_events, candidate_manifest, control_events, control_manifest):
    candidate_validation, candidate_index = validate_side(candidate_events, candidate_manifest, candidate=True)
    control_validation, control_index = validate_side(control_events, control_manifest, candidate=False)
    candidate_graphs = {row.get('graph_id'): row for row in candidate_manifest.get('graphs', [])}
    control_graphs = {row.get('graph_id'): row for row in control_manifest.get('graphs', [])}
    graph_metadata_match = candidate_graphs == control_graphs
    valid = candidate_validation['passed'] and control_validation['passed'] and graph_metadata_match

    def value(indexed, key):
        rows = indexed.get(key, [])
        result = rows[0].get('raw_return') if len(rows) == 1 else None
        return result if isinstance(result, (int, float)) and math.isfinite(result) else None

    def panel_values(indexed, run, method, checkpoint):
        return [value(indexed, ('evaluation', run, method, checkpoint, episode)) for episode in range(20)]

    def paired_mean(left, right=None):
        right = [0.] * len(left) if right is None else right
        return statistics.mean(a - b for a, b in zip(left, right)) if all(
            a is not None and b is not None for a, b in zip(left, right)) else None

    heuristic_values = {method: [value(control_index, ('heuristic', method, episode))
        for episode in range(20)] for method in HEURISTICS}
    heuristics = {method: {'panel_mean': paired_mean(values), 'panel_size': 20,
        'actual_unique_evaluations': sum(value is not None for value in values), 'source': 'retained V44'}
        for method, values in heuristic_values.items()}
    curve, endpoint = [], {}
    for checkpoint in FROZEN_PROTOCOL['checkpoints']:
        row = dict(checkpoint=checkpoint, descriptive_only=checkpoint != 128, methods={})
        for method in METHODS:
            panels = [panel_values(candidate_index, run, method, checkpoint) for run in range(3)]
            comparisons = {
                'own_initial': v44.run_statistics([paired_mean(panels[run],
                    panel_values(candidate_index, run, method, 0)) for run in range(3)]),
                'MEAN_V44': v44.run_statistics([paired_mean(panels[run],
                    panel_values(control_index, run, method, 128)) for run in range(3)])}
            comparisons.update({name: v44.run_statistics([paired_mean(panel, reference) for panel in panels])
                for name, reference in heuristic_values.items()})
            row['methods'][method] = dict(raw_return=v44.run_statistics([paired_mean(panel) for panel in panels]),
                paired_differences=comparisons)
            if checkpoint == 128:
                endpoint[method] = comparisons
        curve.append(row)
    pairs = [('LMTA_RI', 'FLAT_DQN'), ('LMTA_RI', 'BUDGET_HRL'), ('BUDGET_HRL', 'FLAT_DQN')]
    method_differences = {left + '_minus_' + right: v44.run_statistics([paired_mean(
        panel_values(candidate_index, run, left, 128), panel_values(candidate_index, run, right, 128))
        for run in range(3)]) for left, right in pairs}
    conditions = {name: endpoint['LMTA_RI'][name]['all_positive_and_ci_lower_positive']
        for name in ('own_initial', 'MEAN_V44', 'AVERAGE_SCORE')}
    signal = all(conditions.values()) if valid and all(value is not None for value in conditions.values()) else None
    return dict(schema='acfqp.lmta_weighted_analysis.v46', operator='IC_SUM',
        protocol=FROZEN_PROTOCOL, primary_checkpoint=128, mean_control_checkpoint=128,
        integrity=dict(passed=valid, candidate=candidate_validation, control=control_validation,
            graph_metadata_match=graph_metadata_match),
        accounting=dict(new_candidate=v44.accounting(candidate_events, candidate_manifest),
            retained_V44_control=v44.accounting(control_events, control_manifest),
            scope='Every candidate event is charged once, including incomplete or duplicate evidence. '
                  'Retained V44 costs are historical, not new costs. Its 40 heuristic evaluations are '
                  'retained once despite reuse across methods, checkpoints, and runs.'),
        heuristic_panel_means=heuristics, learning_curve=curve, endpoint_comparisons=endpoint,
        endpoint_method_differences_descriptive=method_differences,
        LMTA_continue_conditions=conditions, LMTA_continue_signal=signal,
        inference_scope='The three independently trained run means, each using the same fixed 20-episode '
            'held-out panel, are the units of paired t intervals (df=2). These intervals are conditional '
            'on the retained graphs and flows, not population-graph uncertainty. Every curve point compares '
            'to its own initial policy and the fixed corresponding V44 method/run endpoint at 128. '
            'Only endpoint 128 can satisfy the continuation conditions; intermediate points are descriptive. '
            'Null signal means invalid or incomplete evidence; false means the valid scientific condition failed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_weighted_v46')
    parser.add_argument('--control-dir', type=Path, default=ROOT / 'reports/lmta_learnability_v44')
    args = parser.parse_args()

    def load(directory):
        return ([json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()],
                json.loads((directory / 'manifest.json').read_text()))

    report = summarize(*load(args.output_dir), *load(args.control_dir))
    (args.output_dir / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(integrity_passed=report['integrity']['passed'],
        LMTA_continue_signal=report['LMTA_continue_signal'],
        LMTA_endpoint=report['endpoint_comparisons']['LMTA_RI']), indent=2))


if __name__ == '__main__':
    main()
