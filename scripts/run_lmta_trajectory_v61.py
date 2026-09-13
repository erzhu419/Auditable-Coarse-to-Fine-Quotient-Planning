"""Calibrate frozen analytic policies using paired sampled trajectories."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.lmta_trajectory_v61 import run_block

METHODS = ['LOOKAHEAD_1_ANALYTIC', 'LOOKAHEAD_2_ANALYTIC']
PROTOCOL = dict(budget=2, horizon=3, replicates=128, methods=METHODS,
    graph_ids=[base+i for base in (580000, 580100, 580200, 580300) for i in range(16)],
    seed_base=61000000, seed_graph_stride=1000,
    limits=dict(max_planner_action_values=2000000, max_decisions=100000, max_wall_seconds=60.),
    calibration_family_size=12, calibration_alpha=.05)
SOURCE_DIRS = dict(policies='reports/lmta_analytic_scale_v58',
    replay='reports/lmta_analytic_short_v59', changed='reports/lmta_changed_policy_v60')
FROZEN = ['src/acfqp/science/lmta_exact_v52.py', 'src/acfqp/science/lmta_analytic_short_v59.py']
SOURCES = FROZEN + ['src/acfqp/science/lmta_trajectory_v61.py',
    'scripts/run_lmta_trajectory_v61.py', 'scripts/analyze_lmta_trajectory_v61.py',
    'specs/LMTA_TRAJECTORY_V61.md']


def read_source():
    docs = {key: {name: json.loads((ROOT / directory / (name+'.json')).read_text())
                  for name in ('manifest', 'analysis')} for key, directory in SOURCE_DIRS.items()}
    if any(doc['manifest']['status'] != 'complete' or not doc['analysis']['integrity']['passed']
           for doc in docs.values()):
        raise AssertionError('Completed V58/V59/V60 evidence is required')
    if not docs['changed']['analysis']['complete_unified_policy_evidence']:
        raise AssertionError('All analytic policies need full value certificates')
    graphs = sorted(docs['policies']['manifest']['graphs'], key=lambda row: row['graph_id'])
    if [row['graph_id'] for row in graphs] != PROTOCOL['graph_ids']:
        raise AssertionError('Frozen graph roster differs')
    for relative in FROZEN:
        if (ROOT / relative).read_bytes() != (ROOT / SOURCE_DIRS['changed'] / 'source' / relative).read_bytes():
            raise AssertionError(f'Frozen policy dependency changed: {relative}')
    return graphs


def run(output_dir):
    started, cpu_started = perf_counter(), process_time()
    tick = perf_counter()
    graphs = read_source()
    source_seconds = perf_counter()-tick
    if not gc.isenabled():
        raise AssertionError('Automatic GC must remain enabled')
    output_dir.mkdir(parents=True, exist_ok=False)
    for relative in SOURCES:
        target = output_dir / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    manifest = dict(schema='acfqp.lmta_trajectory.v61', status='running', protocol=PROTOCOL,
        source_directories=SOURCE_DIRS, graphs=graphs, cold_decisions=True,
        source_read_seconds=source_seconds, graph_reconstruction_seconds=0., data_output_seconds=0.,
        completed_blocks=0, successful_blocks=0, resource_limited_blocks=0,
        trajectory_records=0, completed_trajectories=0, decision_records=0,
        new_graphs=0, new_full_policy_evaluations=0, new_RL_updates=0, new_MCTS_calls=0,
        runtime=dict(python=platform.python_version(), networkx=nx.__version__, device='cpu',
                     arithmetic='float64', gc_enabled=gc.isenabled()))

    def save_manifest():
        manifest.update(whole_runner_seconds=perf_counter()-started,
            runner_cpu_seconds=process_time()-cpu_started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')

    save_manifest()
    try:
        with (output_dir / 'cases.jsonl').open('x') as case_handle, (output_dir / 'trajectories.jsonl').open('x') as trace_handle:
            for index, meta in enumerate(graphs):
                tick = perf_counter()
                graph = nx.DiGraph()
                graph.add_nodes_from(range(meta['nodes']))
                graph.add_edges_from(meta['edges'])
                manifest['graph_reconstruction_seconds'] += perf_counter()-tick
                for method in (METHODS if index % 2 == 0 else METHODS[::-1]):
                    tick = perf_counter()
                    gc.collect()
                    preparation = perf_counter()-tick
                    case, rows = run_block(graph, meta['graph_id'], method,
                        PROTOCOL['replicates'], PROTOCOL['budget'], PROTOCOL['horizon'], PROTOCOL['limits'])
                    tick = perf_counter()
                    gc.collect()
                    cleanup = perf_counter()-tick
                    case.update(prepare_gc_seconds=preparation, cleanup_seconds=cleanup,
                        decision_total_seconds=case['decision_seconds']+cleanup,
                        block_seconds=case['wall_seconds']+cleanup)
                    tick = perf_counter()
                    for row in rows:
                        trace_handle.write(json.dumps(row, allow_nan=False)+'\n')
                    trace_handle.flush()
                    case['serialization_seconds'] = perf_counter()-tick
                    case_handle.write(json.dumps(case, allow_nan=False)+'\n')
                    case_handle.flush()
                    manifest['data_output_seconds'] += perf_counter()-tick
                    manifest['completed_blocks'] += 1
                    manifest['successful_blocks'] += int(case['status'] == 'complete')
                    manifest['resource_limited_blocks'] += int(case['status'] == 'resource_limit')
                    manifest['trajectory_records'] += len(rows)
                    manifest['completed_trajectories'] += case['completed_replicates']
                    manifest['decision_records'] += case['decision_records']
                    del rows
                    save_manifest()
                print(json.dumps(dict(graph_id=meta['graph_id'], completed_blocks=manifest['completed_blocks'],
                    resource_limited_blocks=manifest['resource_limited_blocks'])), flush=True)
        manifest['status'] = 'complete'
    except Exception as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        manifest['data_bytes'] = {name: (output_dir / name).stat().st_size
            for name in ('cases.jsonl', 'trajectories.jsonl') if (output_dir / name).exists()}
        save_manifest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_trajectory_v61')
    run(parser.parse_args().output_dir)


if __name__ == '__main__':
    main()
