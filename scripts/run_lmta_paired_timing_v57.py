"""Interleaved timing of frozen full planners using retained reference queries."""
from __future__ import annotations

import argparse
from collections import defaultdict
import gc
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import sys
from time import perf_counter, process_time

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.lmta_paired_timing_v57 import measure

METHODS = ['LOOKAHEAD_FULL', 'LOOKAHEAD_FULL_ANALYTIC']
PROTOCOL = dict(budget=2, horizon=3, methods=METHODS, repetitions=6, panels=[
    dict(nodes=7, stratum='sparse', expected_degree=1.5, p=.25, seeds=list(range(550000, 550016))),
    dict(nodes=7, stratum='dense', expected_degree=4.5, p=.75, seeds=list(range(550100, 550116))),
    dict(nodes=9, stratum='sparse', expected_degree=1.5, p=.1875, seeds=list(range(550200, 550216))),
    dict(nodes=9, stratum='dense', expected_degree=4.5, p=.5625, seeds=list(range(550300, 550316)))],
    warmup=dict(graph_id=550000, repetitions=5, query='root'),
    order=dict(graphs='ascending_on_even_repetition_descending_on_odd',
               first_method='control_if_repetition_plus_canonical_graph_index_even'),
    gc_policy='default_enabled_collect_before_and_after_each_block',
    limits=dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.))
SOURCE_DIRS = dict(control='reports/lmta_tie_refinement_v55', analytic='reports/lmta_analytic_terminal_v56')
FROZEN = ['src/acfqp/science/lmta_exact_v52.py', 'src/acfqp/science/lmta_lookahead_v53.py',
          'src/acfqp/science/lmta_analytic_terminal_v56.py']
SOURCES = FROZEN + ['src/acfqp/science/lmta_paired_timing_v57.py',
    'scripts/run_lmta_paired_timing_v57.py', 'scripts/analyze_lmta_paired_timing_v57.py',
    'specs/LMTA_PAIRED_TIMING_V57.md']


def schedule(graph_ids):
    result = []
    for repetition in range(PROTOCOL['warmup']['repetitions']):
        methods = METHODS if repetition % 2 == 0 else METHODS[::-1]
        result.extend(dict(phase='warmup', repetition=repetition,
            graph_id=PROTOCOL['warmup']['graph_id'], position=position, method=method)
            for position, method in enumerate(methods))
    canonical = sorted(graph_ids)
    for repetition in range(PROTOCOL['repetitions']):
        indices = range(len(canonical)) if repetition % 2 == 0 else reversed(range(len(canonical)))
        for index in indices:
            methods = METHODS if (repetition + index) % 2 == 0 else METHODS[::-1]
            result.extend(dict(phase='measured', repetition=repetition, graph_id=canonical[index],
                position=position, method=method) for position, method in enumerate(methods))
    return result


def read_references(directory, method, ids):
    queries = defaultdict(list)
    fields = ('statuses', 'remaining_budget', 'remaining_days', 'selected', 'planned_value', 'decision_work')
    with (directory / 'states.jsonl').open() as handle:
        for line in handle:
            row = json.loads(line)
            if row['graph_id'] in ids and row['method'] == method:
                query = {key: row[key] for key in fields}
                query['statuses'] = tuple(query['statuses'])
                if 'reach_probability' in row:
                    query['reach_probability'] = row['reach_probability']
                queries[row['graph_id']].append(query)
    return queries


def run(output_dir):
    started, cpu_started = perf_counter(), process_time()
    tick = perf_counter()
    control_dir, analytic_dir = (ROOT / SOURCE_DIRS[name] for name in ('control', 'analytic'))
    old_manifest = json.loads((control_dir / 'manifest.json').read_text())
    old_analysis = json.loads((control_dir / 'analysis.json').read_text())
    analytic_manifest = json.loads((analytic_dir / 'manifest.json').read_text())
    analytic_analysis = json.loads((analytic_dir / 'analysis.json').read_text())
    if (old_manifest['status'] != 'complete' or not old_analysis['integrity']['passed']
            or not old_analysis['fresh_complete_quality_evidence'] or analytic_manifest['status'] != 'complete'
            or not analytic_analysis['integrity']['passed'] or not analytic_analysis['policy_value_preserved_all']):
        raise AssertionError('Both reference packages and the V56 policy-preservation certificate must be valid')
    if not gc.isenabled():
        raise AssertionError('The frozen timing protocol requires default automatic GC enabled')
    for relative in FROZEN:
        if (ROOT / relative).read_bytes() != (analytic_dir / 'source' / relative).read_bytes():
            raise AssertionError(f'Frozen planner changed: {relative}')
    ids = {seed for panel in PROTOCOL['panels'] for seed in panel['seeds']}
    graph_rows = sorted((row for row in old_manifest['graphs'] if row['graph_id'] in ids), key=lambda row: row['graph_id'])
    if {row['graph_id'] for row in graph_rows} != ids:
        raise AssertionError('Retained fresh graph roster is incomplete')
    queries = {METHODS[0]: read_references(control_dir, METHODS[0], ids),
               METHODS[1]: read_references(analytic_dir, METHODS[1], ids)}
    for graph in ids:
        old, new = queries[METHODS[0]][graph], queries[METHODS[1]][graph]
        if not old or len(old) != len(new):
            raise AssertionError('Paired source query counts differ')
        for left, right in zip(old, new):
            if any(left[key] != right[key] for key in ('statuses', 'remaining_budget', 'remaining_days')):
                raise AssertionError('Paired source state order differs')
            right['reach_probability'] = left['reach_probability']
    source_seconds = perf_counter() - tick
    tick = perf_counter()
    graphs = {}
    for row in graph_rows:
        graph = nx.DiGraph()
        graph.add_nodes_from(range(row['nodes']))
        graph.add_edges_from(row['edges'])
        graphs[row['graph_id']] = graph
    reconstruction_seconds = perf_counter() - tick
    output_dir.mkdir(parents=True, exist_ok=False)
    for relative in SOURCES:
        target = output_dir / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    sequence = schedule(ids)
    manifest = dict(schema='acfqp.lmta_paired_timing.v57', status='running', protocol=PROTOCOL,
        source_directories=SOURCE_DIRS, cold_decisions=True, graphs=graph_rows,
        source_state_records=sum(map(len, queries[METHODS[0]].values())),
        source_read_seconds=source_seconds, graph_reconstruction_seconds=reconstruction_seconds,
        completed_blocks=0, completed_measured_blocks=0, completed_warmup_blocks=0,
        successful_blocks=0, resource_limited_blocks=0, total_query_count=0, data_output_seconds=0.,
        new_graphs=0, new_environment_samples=0, new_environment_calls=0, new_RL_updates=0,
        new_MCTS_calls=0, new_full_policy_evaluations=0, new_independent_DP_checks=0,
        runtime=dict(python=platform.python_version(), networkx=nx.__version__, device='cpu',
                     pid=os.getpid(), gc_enabled=gc.isenabled(), machine=platform.machine()))
    metadata = {row['graph_id']: row for row in graph_rows}

    def save_manifest():
        manifest.update(whole_runner_seconds=perf_counter() - started,
            runner_cpu_seconds=process_time() - cpu_started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    save_manifest()
    try:
        with (output_dir / 'cases.jsonl').open('x') as handle:
            for slot in sequence:
                identity = {key: metadata[slot['graph_id']][key] for key in ('graph_id', 'nodes', 'stratum', 'p')}
                identity.update(budget=2, horizon=3, **{key: slot[key] for key in ('phase', 'repetition', 'position')})
                rows = queries[slot['method']][slot['graph_id']]
                if slot['phase'] == 'warmup':
                    rows = [next(row for row in rows if row['remaining_days'] == 3 and not any(row['statuses']))]
                case = measure(graphs[slot['graph_id']], identity, rows, slot['method'], PROTOCOL['limits'])
                tick = perf_counter()
                handle.write(json.dumps(case, allow_nan=False) + '\n')
                handle.flush()
                manifest['data_output_seconds'] += perf_counter() - tick
                manifest['completed_blocks'] += 1
                manifest['completed_' + slot['phase'] + '_blocks'] += 1
                manifest['successful_blocks' if case['status'] == 'complete' else 'resource_limited_blocks'] += 1
                manifest['total_query_count'] += case['query_count']
                if slot['position'] == 1:
                    save_manifest()
            manifest['status'] = 'complete'
    except Exception as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        data = output_dir / 'cases.jsonl'
        manifest['data_bytes'] = {'cases.jsonl': data.stat().st_size} if data.exists() else {}
        save_manifest()
    print(json.dumps({key: manifest[key] for key in ('status', 'completed_blocks', 'total_query_count', 'whole_runner_seconds')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_paired_timing_v57')
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == '__main__':
    main()
