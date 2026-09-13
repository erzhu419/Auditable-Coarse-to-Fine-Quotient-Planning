"""Run the fixed new-graph trajectory scale panel without changing policies."""
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
from acfqp.science.lmta_aim_v43 import generate_graph
from acfqp.science.lmta_trajectory_v61 import run_block

METHODS = ['LOOKAHEAD_1_ANALYTIC', 'LOOKAHEAD_2_ANALYTIC']
PROTOCOL = dict(budget=2, horizon=3, replicates=128, methods=METHODS, panels=[
    dict(nodes=13, stratum='sparse', expected_degree=1.5, p=1.5/12, seeds=list(range(620000,620016))),
    dict(nodes=13, stratum='dense', expected_degree=4.5, p=4.5/12, seeds=list(range(620100,620116))),
    dict(nodes=15, stratum='sparse', expected_degree=1.5, p=1.5/14, seeds=list(range(620200,620216))),
    dict(nodes=15, stratum='dense', expected_degree=4.5, p=4.5/14, seeds=list(range(620300,620316)))],
    seed_base=61000000, seed_graph_stride=1000,
    limits=dict(max_planner_action_values=2000000, max_decisions=100000, max_wall_seconds=60.),
    primary_family_size=4, primary_alpha=.05)
PREVIOUS = 'reports/lmta_trajectory_v61'
FROZEN = {path: PREVIOUS+'/source/'+path for path in (
    'src/acfqp/science/lmta_exact_v52.py', 'src/acfqp/science/lmta_analytic_short_v59.py',
    'src/acfqp/science/lmta_trajectory_v61.py')}
FROZEN.update({
    'src/acfqp/science/lmta_aim_v43.py': 'reports/lmta_analytic_scale_v58/source/src/acfqp/science/lmta_aim_v43.py',
    'scripts/analyze_lmta_trajectory_v61.py': PREVIOUS+'/analysis_repair_source.py'})
SOURCES = list(FROZEN) + ['scripts/run_lmta_trajectory_scale_v62.py',
    'scripts/analyze_lmta_trajectory_scale_v62.py', 'scripts/lmta_trajectory_certificate_v62.py',
    'specs/LMTA_TRAJECTORY_SCALE_V62.md']


def require_previous():
    previous = json.loads((ROOT/PREVIOUS/'manifest.json').read_text())
    analysis = json.loads((ROOT/PREVIOUS/'analysis.json').read_text())
    if (previous['status'] != 'complete' or not analysis['integrity']['passed']
            or not analysis['complete_trajectory_evidence'] or not analysis['calibration_consistent']):
        raise AssertionError('Completed V61 trajectory calibration is required')
    for relative, frozen in FROZEN.items():
        if (ROOT/relative).read_bytes() != (ROOT/frozen).read_bytes():
            raise AssertionError(f'Frozen dependency changed: {relative}')


def run(output_dir):
    started, cpu_started = perf_counter(), process_time()
    tick = perf_counter()
    require_previous()
    source_seconds = perf_counter()-tick
    if not gc.isenabled():
        raise AssertionError('Automatic GC must remain enabled')
    output_dir.mkdir(parents=True, exist_ok=False)
    for relative in SOURCES:
        target = output_dir/'source'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, target)
    tick = perf_counter()
    graphs, metadata = {}, []
    for panel in PROTOCOL['panels']:
        for graph_id in panel['seeds']:
            graph = generate_graph(panel['nodes'], graph_id, p=panel['p'])
            graphs[graph_id] = graph
            metadata.append(dict(graph_id=graph_id,
                **{key:value for key,value in panel.items() if key != 'seeds'},
                edges=[list(edge) for edge in sorted(graph.edges())]))
    manifest = dict(schema='acfqp.lmta_trajectory_scale.v62', status='running', protocol=PROTOCOL,
        previous_source=PREVIOUS, graphs=metadata, cold_decisions=True,
        source_read_seconds=source_seconds, graph_generation_seconds=perf_counter()-tick,
        data_output_seconds=0., completed_blocks=0, successful_blocks=0, resource_limited_blocks=0,
        trajectory_records=0, completed_trajectories=0, decision_records=0,
        new_graphs=len(graphs), new_full_policy_evaluations=0, new_RL_updates=0, new_MCTS_calls=0,
        runtime=dict(python=platform.python_version(), networkx=nx.__version__, device='cpu',
                     arithmetic='float64', gc_enabled=gc.isenabled()))

    def save_manifest():
        manifest.update(whole_runner_seconds=perf_counter()-started,
            runner_cpu_seconds=process_time()-cpu_started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        (output_dir/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')

    save_manifest()
    try:
        with (output_dir/'cases.jsonl').open('x') as ch, (output_dir/'trajectories.jsonl').open('x') as th:
            for index, meta in enumerate(metadata):
                for method in (METHODS if index%2 == 0 else METHODS[::-1]):
                    tick = perf_counter()
                    gc.collect()
                    preparation = perf_counter()-tick
                    case, rows = run_block(graphs[meta['graph_id']], meta['graph_id'], method,
                        PROTOCOL['replicates'], PROTOCOL['budget'], PROTOCOL['horizon'], PROTOCOL['limits'])
                    tick = perf_counter()
                    gc.collect()
                    cleanup = perf_counter()-tick
                    case.update(prepare_gc_seconds=preparation, cleanup_seconds=cleanup,
                        decision_total_seconds=case['decision_seconds']+cleanup,
                        block_seconds=case['wall_seconds']+cleanup)
                    tick = perf_counter()
                    for row in rows:
                        th.write(json.dumps(row, allow_nan=False)+'\n')
                    th.flush()
                    case['serialization_seconds'] = perf_counter()-tick
                    ch.write(json.dumps(case, allow_nan=False)+'\n')
                    ch.flush()
                    manifest['data_output_seconds'] += perf_counter()-tick
                    manifest['completed_blocks'] += 1
                    manifest['successful_blocks'] += int(case['status']=='complete')
                    manifest['resource_limited_blocks'] += int(case['status']=='resource_limit')
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
        manifest['data_bytes'] = {name:(output_dir/name).stat().st_size for name in
            ('cases.jsonl','trajectories.jsonl') if (output_dir/name).exists()}
        save_manifest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'reports/lmta_trajectory_scale_v62')
    run(parser.parse_args().output_dir)
