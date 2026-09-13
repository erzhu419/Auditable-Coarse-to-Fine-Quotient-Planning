"""Four retained/frozen component cells, with exact restoration anchors and no Gate."""
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
_spec = importlib.util.spec_from_file_location('lmta_weighted_analysis_v46',
    Path(__file__).with_name('analyze_lmta_weighted_v46.py'))
v46 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v46)
v44 = v46.v44
METHODS = ['BUDGET_HRL', 'LMTA_RI']
FROZEN_PROTOCOL = dict(methods=METHODS, runs=3, panel_size=20, source_checkpoint=128,
    cells=['LS', 'AL'], anchor_episode=0, expected_hybrid_events=240, expected_anchor_events=6,
    nodes=500, p=.01, budget=70, horizon=10, goal_rule='live_search_on_hybrid_state')


def event_key(row):
    return row.get('phase'), row.get('cell'), row.get('method'), row.get('run_id'), row.get('episode')


def validate_candidate(events, manifest, weighted_manifest, weighted_index):
    expected = {('evaluation', cell, method, run, episode) for cell, method, run, episode in
        itertools.product(('LS', 'AL'), METHODS, range(3), range(20))}
    expected |= {('restore_anchor', 'LL', method, run, 0) for method, run in itertools.product(METHODS, range(3))}
    indexed, errors = defaultdict(list), []
    for field, expected_value in (('schema', 'acfqp.lmta_components.v48'), ('status', 'complete'),
            ('protocol', FROZEN_PROTOCOL), ('source_directory', 'reports/lmta_weighted_v46')):
        if manifest.get(field) != expected_value:
            errors.append(f'Manifest {field} differs from the frozen design')
    if manifest.get('runtime') != weighted_manifest.get('runtime'):
        errors.append('Restoration runtime differs from V46')
    graphs = manifest.get('graphs', [])
    panel_graphs = [row for row in weighted_manifest.get('graphs', []) if 440900 <= row['graph_id'] <= 440909]
    if len(graphs) != 10 or {row['graph_id']: row for row in graphs} != {row['graph_id']: row for row in panel_graphs}:
        errors.append('Ten held-out graph metadata records must exactly match V46')
    policies = manifest.get('loaded_policies', [])
    if Counter((row.get('method'), row.get('run_id')) for row in policies) != Counter(itertools.product(METHODS, range(3))):
        errors.append('Exactly six source policy loads are required')
    source_policies = {(row['method'], row['run_id']): row for row in weighted_manifest.get('completed_runs', [])}
    for row in policies:
        source = source_policies.get((row.get('method'), row.get('run_id')))
        if (source is None or row.get('source_checkpoint') != 128
                or any(row.get(field) != source.get(field) for field in ('model_path', 'model_bytes'))):
            errors.append('Loaded policy path/bytes/checkpoint differs from its source')
    for position, row in enumerate(events):
        key = event_key(row)
        indexed[key].append(row)
        episode = row.get('episode')
        if key not in expected:
            errors.append({'event_index': position, 'problem': 'Unexpected event identity'})
        if (row.get('checkpoint') != 128 or not isinstance(episode, int)
                or (row.get('graph_id'), row.get('environment_seed')) != (440900 + episode // 2, 446000 + episode)):
            errors.append({'event_index': position, 'problem': 'Source checkpoint or fixed panel binding differs'})
        reward, seconds = row.get('raw_return'), row.get('wall_seconds')
        if (not isinstance(reward, (int, float)) or not math.isfinite(reward)
                or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0):
            errors.append({'event_index': position, 'problem': 'Missing/nonfinite return or invalid wall time'})
        counters = row.get('counters', {})
        if (any(not isinstance(counters.get(name), int) or counters[name] < 0 for name in v44.COUNTERS)
                or counters.get('day_transitions') != 10):
            errors.append({'event_index': position, 'problem': 'Missing/incomplete actual physical counters'})
        if any('gradient_steps' in name and value != 0 for name, value in row.get('model_work', {}).items()):
            errors.append({'event_index': position, 'problem': 'Component evaluation performed a gradient update'})
    missing = expected - indexed.keys()
    duplicates = [key for key, rows in indexed.items() if len(rows) > 1]
    if missing or duplicates:
        errors.append(dict(missing_count=len(missing), duplicate_identity_count=len(duplicates)))
    anchors = []
    for method, run in itertools.product(METHODS, range(3)):
        rows = indexed.get(('restore_anchor', 'LL', method, run, 0), [])
        sources = weighted_index.get(('evaluation', run, method, 128, 0), [])
        fields = ['raw_return', 'counters', 'daily_budgets', 'daily_durations']
        if method == 'LMTA_RI':
            fields.extend(('subgoals', 'search_values'))
        checks = {field: len(rows) == len(sources) == 1 and field in rows[0] and field in sources[0]
                  and rows[0][field] == sources[0][field] for field in fields}
        checks['original_model_work'] = (len(rows) == len(sources) == 1
            and 'model_work' in rows[0] and 'model_work' in sources[0]
            and {key: value for key, value in rows[0]['model_work'].items()
                 if not key.startswith('component_')} == sources[0]['model_work'])
        anchors.append(dict(method=method, run_id=run, passed=all(checks.values()), checks=checks))
    if not all(row['passed'] for row in anchors):
        errors.append('At least one exact restoration anchor differs or is unavailable')
    return dict(passed=not errors, expected_events=246, actual_events=len(events), missing_count=len(missing),
        duplicate_identity_count=len(duplicates), phase_counts=dict(Counter(row.get('phase') for row in events)),
        anchors=anchors, errors=errors), indexed


def new_accounting(events, manifest):
    result = v44.accounting(events, manifest)
    loads = manifest.get('loaded_policies', [])
    load_seconds = sum(row['load_seconds'] for row in loads)
    graph_seconds, wall_seconds = manifest.get('graph_generation_seconds'), manifest.get('wall_seconds')
    result['runner_costs'] = dict(whole_runner_seconds=wall_seconds, graph_generation_seconds=graph_seconds,
        policy_load_seconds=load_seconds, loaded_policy_bytes=sum(row['model_bytes'] for row in loads),
        unitemized_runner_seconds=wall_seconds - result['all_actual_events']['wall_seconds'] - graph_seconds - load_seconds
            if wall_seconds is not None and graph_seconds is not None else None)
    by_cell = defaultdict(list)
    for row in events:
        by_cell[(row.get('phase'), row.get('cell'), row.get('method'), row.get('run_id'))].append(row)
    result['by_phase_cell_method_run'] = [dict(phase=phase, cell=cell, method=method, run_id=run,
        **v44.accounting(rows, {})['all_actual_events']) for (phase, cell, method, run), rows in by_cell.items()]
    result['scope'] = 'All 240 hybrid and six anchor episodes are newly charged once, including failed or duplicate records. Policy loads and graph construction are additional runner components; whole-run wall time contains them.'
    return result


def summarize(events, manifest, weighted_events, weighted_manifest, heuristic_events, heuristic_manifest):
    weighted_validation, weighted_index = v46.validate_side(weighted_events, weighted_manifest, candidate=True)
    heuristic_validation, heuristic_index = v46.validate_side(heuristic_events, heuristic_manifest, candidate=False)
    candidate_validation, candidate_index = validate_candidate(events, manifest, weighted_manifest, weighted_index)
    source_graphs_match = weighted_manifest.get('graphs') == heuristic_manifest.get('graphs')
    valid = candidate_validation['passed'] and weighted_validation['passed'] and heuristic_validation['passed'] and source_graphs_match

    def value(indexed, key):
        rows = indexed.get(key, [])
        reward = rows[0].get('raw_return') if len(rows) == 1 else None
        return reward if isinstance(reward, (int, float)) and math.isfinite(reward) else None

    def mean(values):
        return statistics.mean(values) if all(value is not None for value in values) else None

    score_values = [value(heuristic_index, ('heuristic', 'AVERAGE_SCORE', episode)) for episode in range(20)]
    score_mean = mean(score_values)
    cells, effects = {}, {}
    for method in METHODS:
        panels = {cell: [] for cell in ('LL', 'LS', 'AL', 'AS')}
        for run in range(3):
            panels['LL'].append([value(weighted_index, ('evaluation', run, method, 128, episode)) for episode in range(20)])
            for cell in ('LS', 'AL'):
                panels[cell].append([value(candidate_index, ('evaluation', cell, method, run, episode)) for episode in range(20)])
            panels['AS'].append(score_values)
        cells[method] = {cell: v44.run_statistics([mean(panel) for panel in panels[cell]]) for cell in ('LL', 'LS', 'AL')}
        cells[method]['AS'] = dict(panel_mean=score_mean, panel_size=20, ci_95=None,
            n_independent_training_runs=0, source='One retained V44 AVERAGE_SCORE panel, shared across all comparisons.')
        if valid:
            def contrast(coefficients):
                return v44.run_statistics([mean([sum(weight * panels[cell][run][episode] for cell, weight in coefficients.items())
                    for episode in range(20)]) for run in range(3)])

            effects[method] = dict(
                node_substitution_LS_minus_LL=contrast({'LS': 1, 'LL': -1}),
                node_substitution_AS_minus_AL=contrast({'AS': 1, 'AL': -1}),
                budget_substitution_AL_minus_LL=contrast({'AL': 1, 'LL': -1}),
                budget_substitution_AS_minus_LS=contrast({'AS': 1, 'LS': -1}),
                interaction_AS_minus_AL_minus_LS_plus_LL=contrast({'AS': 1, 'AL': -1, 'LS': -1, 'LL': 1}),
                hybrid_LS_minus_AS=contrast({'LS': 1, 'AS': -1}),
                hybrid_AL_minus_AS=contrast({'AL': 1, 'AS': -1}))
    return dict(schema='acfqp.lmta_components_analysis.v48', protocol=FROZEN_PROTOCOL,
        integrity=dict(passed=valid, candidate=candidate_validation, weighted_source=weighted_validation,
            heuristic_source=heuristic_validation, source_graphs_match=source_graphs_match),
        valid_component_estimates=valid, cell_means=cells, component_effects=effects if valid else None,
        accounting=dict(new_components=new_accounting(events, manifest),
            retained_weighted_V46=v44.accounting(weighted_events, weighted_manifest),
            retained_heuristic_source_V44=v44.accounting(heuristic_events, heuristic_manifest),
            scope='Each source event ledger is retained once. The shared AS panel is not resampled or multiplied by methods, cells, or training runs. No historical fee is refunded.'),
        inference_scope='LL uses the frozen V46 endpoint at 128. LS uses learned budgets and score nodes; AL uses average budgets and learned nodes. '
            'AS is one retained average-budget/score-node panel, with no independent training-run CI of its own. '
            'Effects first pair the same 20 fixed graph/flow episodes, then use three training-run means for descriptive t intervals (df=2). '
            'Intervals are conditional on these policies and this panel. LMTA searches live on each hybrid state. '
            'These are fixed-policy component substitutions, not explanations of the training trajectory or an adoption/continuation Gate.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_components_v48')
    parser.add_argument('--weighted-dir', type=Path, default=ROOT / 'reports/lmta_weighted_v46')
    parser.add_argument('--heuristic-dir', type=Path, default=ROOT / 'reports/lmta_learnability_v44')
    args = parser.parse_args()
    start = perf_counter()

    def load(directory):
        return ([json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()],
                json.loads((directory / 'manifest.json').read_text()))

    report = summarize(*load(args.output_dir), *load(args.weighted_dir), *load(args.heuristic_dir))
    report['accounting']['analysis_wall_seconds_before_serialization'] = perf_counter() - start
    (args.output_dir / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(integrity_passed=report['integrity']['passed'], component_effects=report['component_effects']), indent=2))


if __name__ == '__main__':
    main()
