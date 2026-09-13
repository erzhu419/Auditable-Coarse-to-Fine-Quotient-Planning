"""Run the frozen exact-tie refinement comparison and separate known regression."""
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
from acfqp.science.lmta_scale_v54 import evaluate as evaluate_control
from acfqp.science.lmta_tie_refinement_v55 import evaluate as evaluate_candidate

CANDIDATE = 'LOOKAHEAD_2_TIE3'
METHODS = ['LOOKAHEAD_1', 'LOOKAHEAD_2', CANDIDATE, 'LOOKAHEAD_FULL']
PROTOCOL = dict(budget=2, horizon=3, methods=METHODS, panels=[
    dict(nodes=7, stratum='sparse', expected_degree=1.5, p=.25, seeds=list(range(550000, 550016))),
    dict(nodes=7, stratum='dense', expected_degree=4.5, p=.75, seeds=list(range(550100, 550116))),
    dict(nodes=9, stratum='sparse', expected_degree=1.5, p=.1875, seeds=list(range(550200, 550216))),
    dict(nodes=9, stratum='dense', expected_degree=4.5, p=.5625, seeds=list(range(550300, 550316)))],
    limits=dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.),
    regression=dict(graph_id=540009, source_directory='reports/lmta_scale_v54',
                    methods=[CANDIDATE], role='known_regression_only'))
SOURCE = ROOT / 'reports/lmta_scale_v54'
FROZEN = ['src/acfqp/science/lmta_aim_v43.py', 'src/acfqp/science/lmta_exact_v52.py',
          'src/acfqp/science/lmta_lookahead_v53.py', 'src/acfqp/science/lmta_scale_v54.py',
          'scripts/analyze_lmta_exact_v52.py', 'scripts/analyze_lmta_lookahead_v53.py',
          'scripts/analyze_lmta_scale_v54.py']
SOURCES = FROZEN + ['src/acfqp/science/lmta_tie_refinement_v55.py',
    'scripts/run_lmta_tie_refinement_v55.py', 'scripts/analyze_lmta_tie_refinement_v55.py',
    'specs/LMTA_TIE_REFINEMENT_V55.md']


def run(output_dir):
    started, cpu_started = perf_counter(), process_time()
    tick = perf_counter()
    previous = json.loads((SOURCE / 'manifest.json').read_text())
    checked = json.loads((SOURCE / 'analysis.json').read_text())
    if previous['status'] != 'complete' or not checked['complete_quality_evidence']:
        raise AssertionError('V54 controls must be complete and independently validated')
    for relative in FROZEN:
        if (ROOT / relative).read_bytes() != (SOURCE / 'source' / relative).read_bytes():
            raise AssertionError(f'Frozen V54 dependency changed: {relative}')
    regression_id = PROTOCOL['regression']['graph_id']
    regression = next(row for row in previous['graphs'] if row['graph_id'] == regression_id)
    controls = []
    with (SOURCE / 'cases.jsonl').open() as handle:
        for line in handle:
            row = json.loads(line)
            if row['graph_id'] == regression_id:
                controls.append(row)
    if sorted(row['method'] for row in controls) != sorted(m for m in METHODS if m != CANDIDATE):
        raise AssertionError('Known regression requires all three retained V54 controls')
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
            graph_rows.append(dict(graph_id=seed, panel='fresh',
                **{key: value for key, value in panel.items() if key != 'seeds'},
                edges=[list(edge) for edge in sorted(graph.edges())]))
    graph = nx.DiGraph()
    graph.add_nodes_from(range(regression['nodes']))
    graph.add_edges_from(regression['edges'])
    graphs[regression_id] = graph
    graph_rows.append(dict(regression, panel='regression'))
    manifest = dict(schema='acfqp.lmta_tie_refinement.v55', status='running', protocol=PROTOCOL,
        source_directory='reports/lmta_scale_v54', cold_decisions=True, graphs=graph_rows,
        regression_controls=controls, source_read_seconds=source_seconds,
        graph_generation_seconds=perf_counter() - tick,
        completed_cases=0, successful_cases=0, resource_limited_cases=0, total_state_records=0,
        new_environment_samples=0, new_environment_calls=0, new_RL_updates=0, new_MCTS_calls=0,
        runtime=dict(python=platform.python_version(), numpy=np.__version__, networkx=nx.__version__,
                     device='cpu', arithmetic='float64'))

    def save_manifest():
        manifest.update(whole_runner_seconds=perf_counter() - started,
            runner_cpu_seconds=process_time() - cpu_started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    save_manifest()
    try:
        with (output_dir / 'cases.jsonl').open('x') as case_file, (output_dir / 'states.jsonl').open('x') as state_file:
            for graph in graph_rows:
                methods = METHODS if graph['panel'] == 'fresh' else [CANDIDATE]
                for method in methods:
                    evaluate = evaluate_candidate if method == CANDIDATE else evaluate_control
                    case, rows = evaluate(graphs[graph['graph_id']], graph['graph_id'], graph['stratum'], graph['p'],
                        PROTOCOL['budget'], PROTOCOL['horizon'], method, PROTOCOL['limits'])
                    tick = perf_counter()
                    for row in rows:
                        state_file.write(json.dumps(row, allow_nan=False) + '\n')
                    state_file.flush()
                    case['serialization_seconds'] = perf_counter() - tick
                    case_file.write(json.dumps(case, allow_nan=False) + '\n')
                    case_file.flush()
                    manifest['completed_cases'] += 1
                    manifest['successful_cases' if case['status'] == 'complete' else 'resource_limited_cases'] += 1
                    manifest['total_state_records'] += len(rows)
                    del rows
                save_manifest()
                print(json.dumps(dict(graph_id=graph['graph_id'], panel=graph['panel'],
                    completed_cases=manifest['completed_cases'], resource_limited_cases=manifest['resource_limited_cases'])), flush=True)
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
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_tie_refinement_v55')
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == '__main__':
    main()
