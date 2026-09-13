"""Evaluate only the frozen one-day policy whose V59 action changed."""
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
from acfqp.science.lmta_changed_policy_v60 import evaluate

PROTOCOL = dict(graph_id=580109, method='LOOKAHEAD_1_ANALYTIC', budget=2, horizon=3,
    changed_state=dict(statuses=[0, 0, 2, 0, 1, 0, 1, 1, 0], remaining_budget=1, remaining_days=2),
    limits=dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.))
SOURCE_DIRS = dict(policies='reports/lmta_analytic_scale_v58', replay='reports/lmta_analytic_short_v59')
FROZEN = {
    'src/acfqp/science/lmta_exact_v52.py': 'replay',
    'src/acfqp/science/lmta_analytic_short_v59.py': 'replay',
    'scripts/analyze_lmta_exact_v52.py': 'replay',
    'scripts/analyze_lmta_lookahead_v53.py': 'replay',
    'scripts/analyze_lmta_scale_v54.py': 'policies',
    'scripts/analyze_lmta_analytic_short_v59.py': 'replay'}
SOURCES = list(FROZEN) + ['src/acfqp/science/lmta_changed_policy_v60.py',
    'scripts/run_lmta_changed_policy_v60.py', 'scripts/analyze_lmta_changed_policy_v60.py',
    'specs/LMTA_CHANGED_POLICY_V60.md']


def read_source():
    documents = {key: {name: json.loads((ROOT / directory / (name+'.json')).read_text())
                      for name in ('manifest', 'analysis')} for key, directory in SOURCE_DIRS.items()}
    policy, replay = documents['policies'], documents['replay']
    if (any(doc['manifest']['status'] != 'complete' or not doc['analysis']['integrity']['passed']
            for doc in documents.values()) or not policy['analysis']['complete_quality_evidence']
            or not replay['analysis']['value_agreement_all']):
        raise AssertionError('V58 and V59 must have valid completed certificates')
    checks = replay['analysis']['integrity']['case_validations']
    missing = [(row['graph_id'], row['method']) for row in checks if not row['policy_value_preserved']]
    if len(checks) != 128 or missing != [(PROTOCOL['graph_id'], PROTOCOL['method'])]:
        raise AssertionError('The only unevaluated policy must be the frozen target')
    for relative, key in FROZEN.items():
        if (ROOT / relative).read_bytes() != (ROOT / SOURCE_DIRS[key] / 'source' / relative).read_bytes():
            raise AssertionError(f'Frozen dependency changed: {relative}')
    return next(row for row in policy['manifest']['graphs'] if row['graph_id'] == PROTOCOL['graph_id'])


def run(output_dir):
    started, cpu_started = perf_counter(), process_time()
    tick = perf_counter()
    graph_row = read_source()
    source_seconds = perf_counter() - tick
    if not gc.isenabled():
        raise AssertionError('Default automatic GC must remain enabled')
    output_dir.mkdir(parents=True, exist_ok=False)
    for relative in SOURCES:
        target = output_dir / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    tick = perf_counter()
    graph = nx.DiGraph()
    graph.add_nodes_from(range(graph_row['nodes']))
    graph.add_edges_from(graph_row['edges'])
    reconstruction_seconds = perf_counter() - tick
    manifest = dict(schema='acfqp.lmta_changed_policy.v60', status='running', protocol=PROTOCOL,
        source_directories=SOURCE_DIRS, graph=graph_row, cold_decisions=True,
        source_read_seconds=source_seconds, graph_reconstruction_seconds=reconstruction_seconds,
        data_output_seconds=0., completed_cases=0, successful_cases=0, resource_limited_cases=0,
        total_state_records=0, new_graphs=0, new_full_policy_evaluations=0,
        new_environment_samples=0, new_environment_calls=0, new_RL_updates=0, new_MCTS_calls=0,
        runtime=dict(python=platform.python_version(), networkx=nx.__version__, device='cpu',
                     arithmetic='float64', gc_enabled=gc.isenabled()))

    def save_manifest():
        manifest.update(whole_runner_seconds=perf_counter()-started,
            runner_cpu_seconds=process_time()-cpu_started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')

    save_manifest()
    try:
        tick = perf_counter()
        gc.collect()
        preparation = perf_counter()-tick
        manifest['new_full_policy_evaluations'] = 1
        case, rows = evaluate(graph, graph_row['graph_id'], graph_row['stratum'], graph_row['p'],
                              PROTOCOL['budget'], PROTOCOL['horizon'], PROTOCOL['limits'])
        tick = perf_counter()
        gc.collect()
        cleanup = perf_counter()-tick
        case.update(prepare_gc_seconds=preparation, cleanup_seconds=cleanup,
            decision_total_seconds=case['decision_seconds']+cleanup,
            block_seconds=case['wall_seconds']+cleanup)
        tick = perf_counter()
        with (output_dir / 'states.jsonl').open('x') as handle:
            for row in rows:
                handle.write(json.dumps(row, allow_nan=False)+'\n')
        case['serialization_seconds'] = perf_counter()-tick
        (output_dir / 'case.json').write_text(json.dumps(case, indent=2, allow_nan=False)+'\n')
        manifest.update(status='complete', data_output_seconds=perf_counter()-tick, completed_cases=1,
            successful_cases=int(case['status'] == 'complete'),
            resource_limited_cases=int(case['status'] == 'resource_limit'), total_state_records=len(rows))
    except Exception as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        manifest['data_bytes'] = {name: (output_dir / name).stat().st_size for name in ('case.json', 'states.jsonl')
                                  if (output_dir / name).exists()}
        save_manifest()
    print(json.dumps(dict(status=manifest['status'], successful_cases=manifest['successful_cases'],
        resource_limited_cases=manifest['resource_limited_cases'], total_state_records=manifest['total_state_records'])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_changed_policy_v60')
    run(parser.parse_args().output_dir)


if __name__ == '__main__':
    main()
