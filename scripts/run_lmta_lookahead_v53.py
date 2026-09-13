"""Frozen receding two-day lookahead with separate decision/evaluation costs."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
from acfqp.science.lmta_exact_v52 import ExactAIMSolver
from acfqp.science.lmta_lookahead_v53 import plan

METHODS = ['LOOKAHEAD_1', 'LOOKAHEAD_2', 'LOOKAHEAD_FULL']
CONTROLS = {'LOOKAHEAD_1': 'AVERAGE_MYOPIC', 'LOOKAHEAD_FULL': 'AVERAGE_OPTIMAL'}
PROTOCOL = dict(nodes=7, budget=2, horizons=[1, 3], panels=[
    dict(p=.25, seeds=list(range(520000, 520016))),
    dict(p=.75, seeds=list(range(520100, 520116)))], methods=METHODS)
SOURCE = ROOT / 'reports/lmta_exact_v52'
SOURCES = ['src/acfqp/science/lmta_exact_v52.py',
           'src/acfqp/science/lmta_lookahead_v53.py',
           'scripts/run_lmta_lookahead_v53.py',
           'scripts/analyze_lmta_exact_v52.py',
           'scripts/analyze_lmta_lookahead_v53.py',
           'specs/LMTA_LOOKAHEAD_V53.md']


def key(row):
    return tuple(row['statuses']), row['remaining_budget'], row['remaining_days']


def evaluate(graph, graph_id, p, horizon, method, retained):
    """Only the outer evaluator can read a retained control value."""
    started = perf_counter()
    identity = dict(graph_id=graph_id, horizon=horizon, method=method)
    kernel = ExactAIMSolver(graph, 'AVERAGE_OPTIMAL')
    records, branches = {}, {}

    def visit(statuses, budget, days):
        if days == 0:
            return 0.
        state = statuses, budget, days
        if state in records:
            return records[state]['value']
        depth = days if method == 'LOOKAHEAD_FULL' else min(int(method[-1]), days)
        tick = perf_counter()
        decision = plan(graph, statuses, budget, days, depth)
        decision_seconds = perf_counter() - tick
        action = tuple(decision['selected'])
        outcomes = kernel.kernel(statuses, action)
        branches[state] = outcomes
        if method in CONTROLS:
            old = retained[state]
            if decision['selected'] != old['selected']:
                raise AssertionError(f'Retained control action mismatch: {identity}, {state}')
            value = old['value']
            # Walk the actual policy without recomputing retained Bellman values.
            for _, after, _ in outcomes:
                visit(after, budget - len(action), days - 1)
        else:
            value = math.fsum(probability * (reward + visit(after, budget - len(action), days - 1))
                              for probability, after, reward in outcomes)
        records[state] = dict(**identity, statuses=list(statuses), remaining_budget=budget,
            remaining_days=days, selected=list(action), value=value,
            planned_value=decision['planned_value'], root_action_values=decision['root_action_values'],
            decision_seconds=decision_seconds, decision_work={'planner_calls': 1, **decision['counters']})
        return value

    initial = (0,) * len(graph), PROTOCOL['budget'], horizon
    root_value = visit(*initial)
    reach = defaultdict(float, {initial: 1.})
    occupancy_terms = 0
    for days in range(horizon, 0, -1):
        contributions = defaultdict(list)
        for state, row in records.items():
            if state[2] != days:
                continue
            row['reach_probability'] = reach[state]
            if days > 1:
                for probability, after, _ in branches[state]:
                    contributions[after, state[1] - len(row['selected']), days - 1].append(reach[state] * probability)
                    occupancy_terms += 1
        for successor, terms in contributions.items():
            reach[successor] = math.fsum(terms)
    rows = [records[state] for state in sorted(records)]
    work = Counter()
    for row in rows:
        work.update(row['decision_work'])
    expected_work = {name: math.fsum(row['reach_probability'] * row['decision_work'].get(name, 0)
                                    for row in rows) for name in work}
    decision_seconds = math.fsum(row['decision_seconds'] for row in rows)
    evaluation_work = dict(kernel.counters)
    evaluation_work.update(new_full_policy_backups=len(rows) if method == 'LOOKAHEAD_2' else 0,
        retained_value_reads=len(rows) if method in CONTROLS else 0, occupancy_probability_terms=occupancy_terms)
    total = perf_counter() - started
    case = dict(**identity, p=p, budget=PROTOCOL['budget'], root_value=root_value,
        root_selected=records[initial]['selected'], control_method=CONTROLS.get(method),
        value_source='V52_retained' if method in CONTROLS else 'V53_full_policy_evaluation',
        wall_seconds=total, decision_seconds=decision_seconds, evaluation_seconds=total - decision_seconds,
        state_records=len(rows), decision_work=dict(work), expected_decision_work=expected_work,
        expected_decision_seconds=math.fsum(row['reach_probability'] * row['decision_seconds'] for row in rows),
        evaluation_work=evaluation_work)
    return case, rows


def run(output_dir):
    started, cpu_started = perf_counter(), process_time()
    tick = perf_counter()
    source_manifest = json.loads((SOURCE / 'manifest.json').read_text())
    source_analysis = json.loads((SOURCE / 'analysis.json').read_text())
    expected_protocol = {**PROTOCOL, 'methods': ['AVERAGE_SCORE', 'AVERAGE_MYOPIC', 'AVERAGE_OPTIMAL',
                                               'SCORE_OPTIMAL_BUDGET', 'JOINT_OPTIMAL']}
    if source_manifest['status'] != 'complete' or not source_analysis['integrity']['passed'] or source_manifest['protocol'] != expected_protocol:
        raise AssertionError('V52 source must be complete and independently validated')
    for relative in ['src/acfqp/science/lmta_exact_v52.py', 'scripts/analyze_lmta_exact_v52.py']:
        if (ROOT / relative).read_bytes() != (SOURCE / 'source' / relative).read_bytes():
            raise AssertionError(f'Frozen dependency changed: {relative}')
    retained = defaultdict(dict)
    with (SOURCE / 'states.jsonl').open() as handle:
        for line in handle:
            row = json.loads(line)
            if row['method'] in CONTROLS.values():
                retained[row['graph_id'], row['horizon'], row['method']][key(row)] = row
    read_seconds = perf_counter() - tick
    output_dir.mkdir(parents=True, exist_ok=False)
    for relative in SOURCES:
        target = output_dir / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    tick = perf_counter()
    graphs = {}
    for row in source_manifest['graphs']:
        graph = nx.DiGraph()
        graph.add_nodes_from(range(row['nodes']))
        graph.add_edges_from(row['edges'])
        graphs[row['graph_id']] = graph
    graph_seconds = perf_counter() - tick
    manifest = dict(schema='acfqp.lmta_lookahead.v53', status='running', protocol=PROTOCOL,
        source_directory='reports/lmta_exact_v52', cold_decisions=True,
        graphs=source_manifest['graphs'], source_read_seconds=read_seconds,
        graph_reconstruction_seconds=graph_seconds, completed_cases=0, total_state_records=0,
        new_environment_samples=0, new_environment_calls=0, new_RL_updates=0, new_MCTS_calls=0,
        runtime=dict(python=platform.python_version(), networkx=nx.__version__, device='cpu', arithmetic='float64'))

    def save_manifest():
        manifest.update(whole_runner_seconds=perf_counter() - started,
            runner_cpu_seconds=process_time() - cpu_started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    save_manifest()
    try:
        with (output_dir / 'cases.jsonl').open('x') as case_file, (output_dir / 'states.jsonl').open('x') as state_file:
            for graph in manifest['graphs']:
                for horizon in PROTOCOL['horizons']:
                    for method in METHODS:
                        old = retained.get((graph['graph_id'], horizon, CONTROLS.get(method)), {})
                        case, states = evaluate(graphs[graph['graph_id']], graph['graph_id'], graph['p'], horizon, method, old)
                        tick = perf_counter()
                        for state in states:
                            state_file.write(json.dumps(state, allow_nan=False) + '\n')
                        state_file.flush()
                        case['serialization_seconds'] = perf_counter() - tick
                        case_file.write(json.dumps(case, allow_nan=False) + '\n')
                        case_file.flush()
                        manifest['completed_cases'] += 1
                        manifest['total_state_records'] += len(states)
                save_manifest()
                print(json.dumps(dict(graph_id=graph['graph_id'], completed_cases=manifest['completed_cases'])), flush=True)
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
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_lookahead_v53')
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == '__main__':
    main()
