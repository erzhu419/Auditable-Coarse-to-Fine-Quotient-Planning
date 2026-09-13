"""Evaluate two endpoint-policy interventions after six retained-control anchors."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

import networkx as nx
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from acfqp.science.lmta_aim_v43 import AIMEnvironment, generate_graph
from acfqp.science.lmta_weighted_v46 import BudgetHRLAgent, LMTAAgent
from acfqp.science.lmta_components_v48 import ComponentPolicy
from run_lmta_learnability_v44 import behaviour, isolated_evaluation, synchronize

WEIGHTED = ROOT / 'reports/lmta_weighted_v46'
METHODS = {'BUDGET_HRL': BudgetHRLAgent, 'LMTA_RI': LMTAAgent}
RULES = {'LL': ('LEARNED', 'LEARNED'), 'LS': ('LEARNED', 'SCORE'), 'AL': ('AVERAGE', 'LEARNED')}
PROTOCOL = dict(methods=list(METHODS), runs=3, panel_size=20, source_checkpoint=128,
    cells=['LS', 'AL'], anchor_episode=0, expected_hybrid_events=240, expected_anchor_events=6,
    nodes=500, p=.01, budget=70, horizon=10, goal_rule='live_search_on_hybrid_state')
SOURCES = ['src/acfqp/science/' + name for name in (
    'lmta_aim_v43.py', 'lmta_models_v43.py', 'lmta_agent_v44.py', 'lmta_baselines_v44.py',
    'lmta_heuristics_v44.py', 'lmta_structure_v45.py', 'lmta_weighted_v46.py', 'lmta_components_v48.py')]
SOURCES += ['scripts/' + name for name in ('run_lmta_learnability_v44.py',
    'analyze_lmta_learnability_v44.py', 'analyze_lmta_weighted_v46.py',
    'run_lmta_components_v48.py', 'analyze_lmta_components_v48.py')]


def execute(policy, graph, seed):
    synchronize(policy.device)
    tick = perf_counter()
    env = AIMEnvironment(graph, budget=70, horizon=10, seed=seed)
    before = Counter(policy.counts)
    result = policy.run_episode(env, training=False)
    synchronize(policy.device)
    elapsed = perf_counter() - tick
    work = dict(Counter(policy.counts) - before)
    if env.day != 10 or result['raw_return'] != int(np.count_nonzero(env.statuses)):
        raise AssertionError('Episode reward/calendar mismatch')
    if result['losses'] or any(value for name, value in work.items() if 'gradient_steps' in name):
        raise AssertionError('Evaluation performed learning')
    return dict(raw_return=result['raw_return'], counters=dict(env.counters['evaluation']),
        model_work=work, wall_seconds=elapsed, losses=result['losses'], **behaviour(result),
        daily_rewards=[row['reward'] for row in result['actions']],
        selected_nodes=[row['selected'] for row in result['actions']])


def anchor_matches(row, reference):
    fields = ['raw_return', 'counters', 'daily_budgets', 'daily_durations']
    if row['method'] == 'LMTA_RI':
        fields += ['subgoals', 'search_values']
    differences = [name for name in fields if row[name] != reference[name]]
    original_work = {key: value for key, value in row['model_work'].items() if not key.startswith('component_')}
    if original_work != reference['model_work']:
        differences.append('original_model_work')
    return differences


def run(output_dir, device):
    control = json.loads((WEIGHTED / 'manifest.json').read_text())
    torch.set_num_threads(1)
    runtime = dict(python=platform.python_version(), numpy=np.__version__, networkx=nx.__version__,
        torch=torch.__version__, device=device, torch_threads=torch.get_num_threads(),
        gpu=torch.cuda.get_device_name() if str(device).startswith('cuda') else None)
    if control['status'] != 'complete' or runtime != control['runtime']:
        raise ValueError('Retained endpoint or runtime does not match V46')
    for path in (WEIGHTED / 'source').rglob('*.py'):
        if path.read_bytes() != (ROOT / path.relative_to(WEIGHTED / 'source')).read_bytes():
            raise ValueError(f'Retained source differs: {path.name}')
    output_dir.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    for name in SOURCES:
        target = output_dir / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    shutil.copyfile(ROOT / 'specs/LMTA_COMPONENTS_V48.md', output_dir / 'protocol.md')
    tick = perf_counter()
    graphs = {seed: generate_graph(500, seed, .01) for seed in range(440900, 440910)}
    for seed, graph in graphs.items():
        graph.graph['replay_id'] = seed
    metadata = [dict(graph_id=key, nodes=len(g), edges=g.number_of_edges()) for key, g in graphs.items()]
    if metadata != [row for row in control['graphs'] if row['graph_id'] in graphs]:
        raise ValueError('Regenerated evaluation graphs differ')
    manifest = dict(schema='acfqp.lmta_components.v48', status='running', protocol=PROTOCOL,
        runtime=runtime, source_directory='reports/lmta_weighted_v46', graphs=metadata,
        graph_generation_seconds=perf_counter() - tick, loaded_policies=[], completed_cells=[],
        anchors_complete=False, old_heuristic_directory='reports/lmta_learnability_v44')

    def save_manifest():
        (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    save_manifest()
    agents = {}
    for record in control['completed_runs']:
        method, run_id = record['method'], record['run_id']
        if method not in METHODS:
            continue
        tick = perf_counter()
        payload = torch.load(WEIGHTED / record['model_path'], map_location='cpu', weights_only=True)
        if (payload['method'], payload['run_id'], payload['training_episodes']) != (method, run_id, 128):
            raise ValueError('Policy identity/checkpoint mismatch')
        agent = METHODS[method](graphs[440900], budget=70, horizon=10, seed=445001 + run_id, device=device)
        for name in (('model', 'low') if method == 'LMTA_RI' else ('ll', 'hl')):
            getattr(agent, name).load_state_dict(payload['weights'][name], strict=True)
            getattr(agent, name).eval()
        synchronize(device)
        agents[method, run_id] = agent
        manifest['loaded_policies'].append(dict(method=method, run_id=run_id,
            source_checkpoint=128, model_path=record['model_path'], model_bytes=record['model_bytes'],
            load_seconds=perf_counter() - tick))
    save_manifest()
    old_events = [json.loads(line) for line in (WEIGHTED / 'events.jsonl').read_text().splitlines()]
    references = {(r['method'], r['run_id']): r for r in old_events
        if r['phase'] == 'evaluation' and r['checkpoint'] == 128 and r['episode'] == 0}
    with (output_dir / 'events.jsonl').open('x') as log:
        def evaluate(method, run_id, cell, episode, phase):
            agent = agents[method, run_id]
            policy = ComponentPolicy(agent, method, *RULES[cell])
            graph_id, seed = 440900 + episode // 2, 446000 + episode
            result = execute(policy, graphs[graph_id], seed)
            row = dict(phase=phase, method=method, run_id=run_id, cell=cell, checkpoint=128,
                episode=episode, graph_id=graph_id, environment_seed=seed, **result)
            log.write(json.dumps(row, allow_nan=False) + '\n')
            log.flush()
            return row

        for (method, run_id), agent in agents.items():
            with isolated_evaluation(agent):
                row = evaluate(method, run_id, 'LL', 0, 'restore_anchor')
            mismatches = anchor_matches(row, references[method, run_id])
            if mismatches:
                manifest.update(status='anchor_mismatch', anchor_mismatch=dict(method=method, run_id=run_id, fields=mismatches),
                    wall_seconds=perf_counter() - started)
                save_manifest()
                raise AssertionError(f'Restored policy differs: {method}/{run_id}: {mismatches}')
        manifest['anchors_complete'] = True
        save_manifest()
        print(json.dumps(dict(restore_anchors=6, exact=True)), flush=True)
        for run_id in range(3):
            methods = list(METHODS) if run_id % 2 == 0 else list(reversed(METHODS))
            cells = ['LS', 'AL'] if run_id % 2 == 0 else ['AL', 'LS']
            for method in methods:
                for cell in cells:
                    with isolated_evaluation(agents[method, run_id]):
                        for episode in range(20):
                            evaluate(method, run_id, cell, episode, 'evaluation')
                    manifest['completed_cells'].append(dict(method=method, run_id=run_id, cell=cell, episodes=20))
                    save_manifest()
                    print(json.dumps(dict(method=method, run_id=run_id, cell=cell, completed=20)), flush=True)
    manifest.update(status='complete', wall_seconds=perf_counter() - started)
    save_manifest()
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_components_v48')
    parser.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
    args = parser.parse_args()
    run(args.output_dir, args.device)
