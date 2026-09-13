"""Replay analytic-terminal full decisions on V55's retained full-policy states."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import platform
import resource
import shutil
import sys
from time import perf_counter, process_time

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.lmta_analytic_terminal_v56 import plan

METHOD = 'LOOKAHEAD_FULL_ANALYTIC'
SOURCE_METHOD = 'LOOKAHEAD_FULL'
PROTOCOL = dict(budget=2, horizon=3, method=METHOD, source_method=SOURCE_METHOD, panels=[
    dict(nodes=7, stratum='sparse', expected_degree=1.5, p=.25, seeds=list(range(550000, 550016))),
    dict(nodes=7, stratum='dense', expected_degree=4.5, p=.75, seeds=list(range(550100, 550116))),
    dict(nodes=9, stratum='sparse', expected_degree=1.5, p=.1875, seeds=list(range(550200, 550216))),
    dict(nodes=9, stratum='dense', expected_degree=4.5, p=.5625, seeds=list(range(550300, 550316)))],
    limits=dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.))
SOURCE = ROOT / 'reports/lmta_tie_refinement_v55'
FROZEN = ['src/acfqp/science/lmta_exact_v52.py', 'src/acfqp/science/lmta_lookahead_v53.py',
          'scripts/analyze_lmta_exact_v52.py', 'scripts/analyze_lmta_lookahead_v53.py']
SOURCES = FROZEN + ['src/acfqp/science/lmta_analytic_terminal_v56.py',
    'scripts/run_lmta_analytic_terminal_v56.py', 'scripts/analyze_lmta_analytic_terminal_v56.py',
    'specs/LMTA_ANALYTIC_TERMINAL_V56.md']


def replay(graph, source_case, source_rows, limits):
    started = perf_counter()
    identity = {key: source_case[key] for key in ('graph_id', 'nodes', 'stratum', 'p', 'budget', 'horizon')}
    identity.update(method=METHOD, source_method=SOURCE_METHOD)
    rows, work, weighted = [], Counter(), Counter()
    weighted_seconds = []
    status, reason, checked_seconds = 'complete', None, 0.
    for old in source_rows:
        tick = perf_counter()
        decision = plan(graph, tuple(old['statuses']), old['remaining_budget'], old['remaining_days'])
        elapsed = perf_counter() - tick
        counts = dict(planner_calls=1, **decision['counters'])
        rows.append(dict(**identity, statuses=old['statuses'], remaining_budget=old['remaining_budget'],
            remaining_days=old['remaining_days'], selected=decision['selected'], planned_value=decision['planned_value'],
            root_action_values=decision['root_action_values'], decision_work=counts, decision_seconds=elapsed))
        work.update(counts)
        weighted.update({name: count * old['reach_probability'] for name, count in counts.items()})
        weighted_seconds.append(elapsed * old['reach_probability'])
        checked_seconds = perf_counter() - started
        observed = (work['action_value_evaluations'], len(rows), checked_seconds)
        for name, number in zip(('max_planner_action_values', 'max_policy_states', 'max_wall_seconds'), observed):
            if number >= limits[name]:
                status, reason = 'resource_limit', name
                break
        if reason:
            break
    elapsed = perf_counter() - started
    decision_seconds = math.fsum(row['decision_seconds'] for row in rows)
    return dict(**identity, status=status, stop_reason=reason, source_state_records=len(source_rows),
        state_records=len(rows), decision_work=dict(work),
        source_weighted_decision_work=dict(weighted) if status == 'complete' else None,
        decision_seconds=decision_seconds,
        source_weighted_decision_seconds=math.fsum(weighted_seconds) if status == 'complete' else None,
        replay_seconds=elapsed, replay_overhead_seconds=elapsed - decision_seconds,
        last_limit_check_seconds=checked_seconds), rows


def run(output_dir):
    started, cpu_started = perf_counter(), process_time()
    tick = perf_counter()
    previous = json.loads((SOURCE / 'manifest.json').read_text())
    checked = json.loads((SOURCE / 'analysis.json').read_text())
    if previous['status'] != 'complete' or not checked['fresh_complete_quality_evidence']:
        raise AssertionError('V55 fresh controls must be complete and independently validated')
    for relative in FROZEN:
        if (ROOT / relative).read_bytes() != (SOURCE / 'source' / relative).read_bytes():
            raise AssertionError(f'Frozen V55 dependency changed: {relative}')
    ids = {seed for panel in PROTOCOL['panels'] for seed in panel['seeds']}
    graphs = [row for row in previous['graphs'] if row['graph_id'] in ids]
    if {row['graph_id'] for row in graphs} != ids:
        raise AssertionError('V55 fresh graph roster is incomplete')
    source_cases = {}
    with (SOURCE / 'cases.jsonl').open() as handle:
        for line in handle:
            row = json.loads(line)
            if row['graph_id'] in ids and row['method'] == SOURCE_METHOD:
                source_cases[row['graph_id']] = row
    source_rows = {seed: [] for seed in ids}
    with (SOURCE / 'states.jsonl').open() as handle:
        for line in handle:
            row = json.loads(line)
            if row['graph_id'] in ids and row['method'] == SOURCE_METHOD:
                source_rows[row['graph_id']].append(row)
    for seed in ids:
        if source_cases[seed]['status'] != 'complete' or len(source_rows[seed]) != source_cases[seed]['state_records']:
            raise AssertionError('V55 full-policy state roster is incomplete')
    source_seconds = perf_counter() - tick
    output_dir.mkdir(parents=True, exist_ok=False)
    for relative in SOURCES:
        target = output_dir / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    manifest = dict(schema='acfqp.lmta_analytic_terminal.v56', status='running', protocol=PROTOCOL,
        source_directory='reports/lmta_tie_refinement_v55', cold_decisions=True, graphs=graphs,
        source_full_state_records=sum(map(len, source_rows.values())), source_read_seconds=source_seconds,
        completed_cases=0, successful_cases=0, resource_limited_cases=0, total_state_records=0,
        new_graphs=0, new_full_policy_evaluations=0, new_environment_samples=0, new_environment_calls=0,
        new_RL_updates=0, new_MCTS_calls=0,
        runtime=dict(python=platform.python_version(), networkx=nx.__version__, device='cpu', arithmetic='float64'))

    def save_manifest():
        manifest.update(whole_runner_seconds=perf_counter() - started,
            runner_cpu_seconds=process_time() - cpu_started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    save_manifest()
    try:
        with (output_dir / 'cases.jsonl').open('x') as case_file, (output_dir / 'states.jsonl').open('x') as state_file:
            for graph_row in graphs:
                graph = nx.DiGraph()
                graph.add_nodes_from(range(graph_row['nodes']))
                graph.add_edges_from(graph_row['edges'])
                seed = graph_row['graph_id']
                case, rows = replay(graph, source_cases[seed], source_rows[seed], PROTOCOL['limits'])
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
                print(json.dumps(dict(graph_id=seed, completed_cases=manifest['completed_cases'],
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
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_analytic_terminal_v56')
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == '__main__':
    main()
