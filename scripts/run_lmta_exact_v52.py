"""Execute the fixed small AIM exact-policy panel in LMTA_EXACT_V52.md."""
from __future__ import annotations

import argparse
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
from acfqp.science.lmta_exact_v52 import ExactAIMSolver, METHODS

PROTOCOL = dict(nodes=7, budget=2, horizons=[1, 3], panels=[
    dict(p=.25, seeds=list(range(520000, 520016))),
    dict(p=.75, seeds=list(range(520100, 520116)))], methods=list(METHODS))
SOURCES = ['src/acfqp/science/lmta_aim_v43.py',
           'src/acfqp/science/lmta_heuristics_v44.py',
           'src/acfqp/science/lmta_exact_v52.py',
           'scripts/run_lmta_exact_v52.py',
           'scripts/analyze_lmta_exact_v52.py',
           'specs/LMTA_EXACT_V52.md']


def run(output_dir):
    started, cpu_started = perf_counter(), process_time()
    output_dir.mkdir(parents=True, exist_ok=False)
    for relative in SOURCES:
        target = output_dir / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    manifest = dict(schema='acfqp.lmta_exact.v52', status='running', protocol=PROTOCOL,
        runtime=dict(python=platform.python_version(), numpy=np.__version__,
                     networkx=nx.__version__, device='cpu', arithmetic='float64_full_enumeration'),
        graphs=[], completed_cases=0, total_state_records=0, cold_cache=True,
        new_environment_samples=0, new_environment_calls=0, new_RL_updates=0,
        new_MCTS_calls=0,
        retained_prior_runs=['reports/lmta_supervised_v49', 'reports/lmta_readout_v50',
                             'reports/lmta_best_action_v51'],
        prior_cost_scope='Prior artifacts retain all old work; no old work is charged anew.')
    path = output_dir / 'manifest.json'

    def save_manifest():
        manifest['whole_runner_seconds'] = perf_counter() - started
        manifest['runner_cpu_seconds'] = process_time() - cpu_started
        manifest['process_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    tick = perf_counter()
    graphs = {}
    for panel in PROTOCOL['panels']:
        for seed in panel['seeds']:
            graph = generate_graph(PROTOCOL['nodes'], seed, p=panel['p'])
            graphs[seed] = graph
            manifest['graphs'].append(dict(graph_id=seed, p=panel['p'], nodes=len(graph),
                                           edges=[list(edge) for edge in sorted(graph.edges())]))
    manifest['graph_generation_seconds'] = perf_counter() - tick
    save_manifest()
    try:
        with (output_dir / 'cases.jsonl').open('x') as cases, (output_dir / 'states.jsonl').open('x') as states:
            for graph_row in manifest['graphs']:
                graph = graphs[graph_row['graph_id']]
                for horizon in PROTOCOL['horizons']:
                    for method in METHODS:
                        tick = perf_counter()
                        solver = ExactAIMSolver(graph, method)
                        value = solver.value((0,) * len(graph), PROTOCOL['budget'], horizon)
                        records = solver.records()
                        root = next(row for row in records if row['statuses'] == [0] * len(graph)
                                    and row['remaining_budget'] == PROTOCOL['budget']
                                    and row['remaining_days'] == horizon)
                        solve_seconds = perf_counter() - tick
                        identity = dict(graph_id=graph_row['graph_id'], horizon=horizon, method=method)
                        tick = perf_counter()
                        for row in records:
                            states.write(json.dumps({**identity, **row}, allow_nan=False) + '\n')
                        states.flush()
                        serialization_seconds = perf_counter() - tick
                        result = dict(**identity, p=graph_row['p'], budget=PROTOCOL['budget'],
                            root_value=value, root_selected=root['selected'], wall_seconds=solve_seconds,
                            counters=dict(solver.counters), certificate_records=len(records),
                            certificate_serialization_seconds=serialization_seconds)
                        cases.write(json.dumps(result, allow_nan=False) + '\n')
                        cases.flush()
                        manifest['completed_cases'] += 1
                        manifest['total_state_records'] += len(records)
                        del solver, records
                save_manifest()
                print(json.dumps(dict(graph_id=graph_row['graph_id'], completed_cases=manifest['completed_cases'])), flush=True)
        manifest['status'] = 'complete'
    except Exception as error:
        manifest['status'] = 'failed'
        manifest['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        manifest['data_bytes'] = {name: (output_dir / name).stat().st_size
                                  for name in ('cases.jsonl', 'states.jsonl')
                                  if (output_dir / name).exists()}
        save_manifest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_exact_v52')
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == '__main__':
    main()
