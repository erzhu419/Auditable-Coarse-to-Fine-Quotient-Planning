"""Execute the frozen new-graph size panel, retaining bounded incomplete work and explicit case cleanup."""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import platform
import resource
import shutil
import sys
from time import perf_counter, process_time

import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.lmta_aim_v43 import generate_graph
from acfqp.science.lmta_analytic_scale_v58 import evaluate

METHODS = ['LOOKAHEAD_1', 'LOOKAHEAD_2', 'LOOKAHEAD_FULL_ANALYTIC']
PROTOCOL = dict(budget=2, horizon=3, methods=METHODS, panels=[
    dict(nodes=9, stratum='sparse', expected_degree=1.5, p=1.5/8, seeds=list(range(580000, 580016))),
    dict(nodes=9, stratum='dense', expected_degree=4.5, p=4.5/8, seeds=list(range(580100, 580116))),
    dict(nodes=11, stratum='sparse', expected_degree=1.5, p=1.5/10, seeds=list(range(580200, 580216))),
    dict(nodes=11, stratum='dense', expected_degree=4.5, p=4.5/10, seeds=list(range(580300, 580316)))],
    limits=dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.))
SOURCE = ROOT / 'reports/lmta_paired_timing_v57'
FROZEN = {
    'src/acfqp/science/lmta_exact_v52.py': 'reports/lmta_paired_timing_v57',
    'src/acfqp/science/lmta_lookahead_v53.py': 'reports/lmta_paired_timing_v57',
    'src/acfqp/science/lmta_analytic_terminal_v56.py': 'reports/lmta_paired_timing_v57',
    'src/acfqp/science/lmta_aim_v43.py': 'reports/lmta_exact_v52',
    'scripts/analyze_lmta_exact_v52.py': 'reports/lmta_tie_refinement_v55',
    'scripts/analyze_lmta_lookahead_v53.py': 'reports/lmta_tie_refinement_v55',
    'scripts/analyze_lmta_scale_v54.py': 'reports/lmta_tie_refinement_v55'}
SOURCES = list(FROZEN) + ['src/acfqp/science/lmta_analytic_scale_v58.py',
    'scripts/run_lmta_analytic_scale_v58.py', 'scripts/analyze_lmta_analytic_scale_v58.py',
    'specs/LMTA_ANALYTIC_SCALE_V58.md']


def run(output_dir):
    started, cpu_started = perf_counter(), process_time()
    tick = perf_counter()
    previous = json.loads((SOURCE / 'manifest.json').read_text())
    previous_analysis = json.loads((SOURCE / 'analysis.json').read_text())
    if (previous['status'] != 'complete' or not previous_analysis['integrity']['passed']
            or not previous_analysis['complete_performance_evidence']):
        raise AssertionError('V57 source must be complete and independently validated')
    for relative, directory in FROZEN.items():
        if (ROOT / relative).read_bytes() != (ROOT / directory / 'source' / relative).read_bytes():
            raise AssertionError(f'Frozen dependency changed: {relative}')
    if not gc.isenabled():
        raise AssertionError('Default automatic GC must remain enabled')
    source_seconds = perf_counter() - tick
    output_dir.mkdir(parents=True, exist_ok=False)
    for relative in SOURCES:
        target = output_dir / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    tick = perf_counter()
    graphs, graph_rows = {}, []
    for panel in PROTOCOL['panels']:
        for seed in panel['seeds']:
            graph = generate_graph(panel['nodes'], seed, p=panel['p'])
            graphs[seed] = graph
            graph_rows.append(dict(graph_id=seed, **{key: value for key, value in panel.items() if key != 'seeds'},
                                   edges=[list(edge) for edge in sorted(graph.edges())]))
    manifest = dict(schema='acfqp.lmta_analytic_scale.v58', status='running', protocol=PROTOCOL,
        source_directory='reports/lmta_paired_timing_v57', cold_decisions=True, graphs=graph_rows,
        source_read_seconds=source_seconds, graph_generation_seconds=perf_counter() - tick,
        completed_cases=0, successful_cases=0, resource_limited_cases=0, total_state_records=0,
        new_graphs=len(graph_rows), data_output_seconds=0., new_environment_samples=0, new_environment_calls=0, new_RL_updates=0, new_MCTS_calls=0,
        runtime=dict(python=platform.python_version(), numpy=np.__version__, networkx=nx.__version__,
                     device='cpu', arithmetic='float64', gc_enabled=gc.isenabled()))

    def save_manifest():
        manifest.update(whole_runner_seconds=perf_counter() - started,
            runner_cpu_seconds=process_time() - cpu_started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    save_manifest()
    try:
        with (output_dir / 'cases.jsonl').open('x') as case_file, (output_dir / 'states.jsonl').open('x') as state_file:
            for graph in graph_rows:
                for method in METHODS:
                    tick = perf_counter()
                    gc.collect()
                    prepare_gc_seconds = perf_counter() - tick
                    case, rows = evaluate(graphs[graph['graph_id']], graph['graph_id'], graph['stratum'], graph['p'],
                        PROTOCOL['budget'], PROTOCOL['horizon'], method, PROTOCOL['limits'])
                    tick = perf_counter()
                    gc.collect()
                    cleanup_seconds = perf_counter() - tick
                    case.update(prepare_gc_seconds=prepare_gc_seconds, cleanup_seconds=cleanup_seconds,
                        decision_total_seconds=case['decision_seconds'] + cleanup_seconds,
                        block_seconds=case['wall_seconds'] + cleanup_seconds)
                    tick = perf_counter()
                    for row in rows:
                        state_file.write(json.dumps(row, allow_nan=False) + '\n')
                    state_file.flush()
                    case['serialization_seconds'] = perf_counter() - tick
                    case_file.write(json.dumps(case, allow_nan=False) + '\n')
                    case_file.flush()
                    manifest['data_output_seconds'] += perf_counter() - tick
                    manifest['completed_cases'] += 1
                    manifest['successful_cases' if case['status'] == 'complete' else 'resource_limited_cases'] += 1
                    manifest['total_state_records'] += len(rows)
                    del rows
                save_manifest()
                print(json.dumps(dict(graph_id=graph['graph_id'], completed_cases=manifest['completed_cases'],
                                      resource_limited_cases=manifest['resource_limited_cases'])), flush=True)
        manifest['status'] = 'complete'
    except Exception as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        manifest['data_bytes'] = {name: (output_dir / name).stat().st_size for name in ('cases.jsonl', 'states.jsonl')
                                  if (output_dir / name).exists()}
        save_manifest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_analytic_scale_v58')
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == '__main__':
    main()
