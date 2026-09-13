"""Frozen V46 IC_SUM training; reuse the retained V44 mean/heuristic controls."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import gc
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
from acfqp.science.lmta_aim_v43 import generate_graph
from acfqp.science.lmta_weighted_v46 import LMTAAgent, FlatDQNAgent, BudgetHRLAgent
from run_lmta_learnability_v44 import (
    PROTOCOL as V44_PROTOCOL, execute_episode, isolated_evaluation, save_policy, synchronize,
)

METHODS = {'FLAT_DQN': FlatDQNAgent, 'BUDGET_HRL': BudgetHRLAgent, 'LMTA_RI': LMTAAgent}
PROTOCOL = {**deepcopy(V44_PROTOCOL), 'heuristics': []}
CONTROL = ROOT / 'reports/lmta_learnability_v44'
SOURCE_FILES = [
    'src/acfqp/science/lmta_aim_v43.py', 'src/acfqp/science/lmta_models_v43.py',
    'src/acfqp/science/lmta_agent_v44.py', 'src/acfqp/science/lmta_baselines_v44.py',
    'src/acfqp/science/lmta_heuristics_v44.py',
    'src/acfqp/science/lmta_structure_v45.py', 'src/acfqp/science/lmta_weighted_v46.py',
    'scripts/run_lmta_learnability_v44.py', 'scripts/analyze_lmta_learnability_v44.py',
    'scripts/run_lmta_weighted_v46.py', 'scripts/analyze_lmta_weighted_v46.py',
]


def run(output_dir, device):
    control = json.loads((CONTROL / 'manifest.json').read_text())
    if control['status'] != 'complete' or control['protocol'] != V44_PROTOCOL:
        raise ValueError('Retained V44 control does not match the frozen design')
    torch.set_num_threads(1)
    runtime = dict(python=platform.python_version(), numpy=np.__version__, networkx=nx.__version__,
                   torch=torch.__version__, device=device, torch_threads=torch.get_num_threads(),
                   gpu=torch.cuda.get_device_name() if str(device).startswith('cuda') else None)
    if runtime != control['runtime']:
        raise ValueError('Runtime differs from retained V44 comparison')
    # The historical control is valid only for the unchanged implementation.
    for retained in (CONTROL / 'source').rglob('*.py'):
        if retained.read_bytes() != (ROOT / retained.relative_to(CONTROL / 'source')).read_bytes():
            raise ValueError(f'V44 source changed: {retained.name}')
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / 'models').mkdir()
    started = perf_counter()
    for name in SOURCE_FILES:
        destination = output_dir / 'source' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    shutil.copyfile(ROOT / 'specs/LMTA_WEIGHTED_V46.md', output_dir / 'protocol.md')
    tick = perf_counter()
    graph_seeds = [440000 + r * 100 + i for r in range(3) for i in range(16)] + list(range(440900, 440910))
    graphs = {seed: generate_graph(500, seed) for seed in graph_seeds}
    for seed, graph in graphs.items():
        graph.graph['replay_id'] = seed
    graph_metadata = [dict(graph_id=k, nodes=len(g), edges=g.number_of_edges()) for k, g in graphs.items()]
    if graph_metadata != control['graphs']:
        raise ValueError('Graph metadata differs from retained V44 inputs')
    manifest = dict(schema='acfqp.lmta_weighted.v46', status='running', operator='IC_SUM',
        protocol=PROTOCOL, runtime=runtime, graphs=graph_metadata,
        graph_generation_seconds=perf_counter() - tick, completed_runs=[],
        control_directory=str(CONTROL.relative_to(ROOT)),
        control_reused_without_new_episodes=True,
        source_scope='V44 training algorithms with V45 IC_SUM graph operators in float32; fresh V46 training.')
    manifest_path = output_dir / 'manifest.json'

    def write_manifest():
        manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    write_manifest()
    with (output_dir / 'events.jsonl').open('x') as log:
        def emit(row):
            log.write(json.dumps(row, allow_nan=False) + '\n')
            log.flush()

        for run_id in range(3):
            order = list(METHODS)[run_id:] + list(METHODS)[:run_id]
            for name in order:
                tick = perf_counter()
                initialization_seed = 445001 + run_id
                agent = METHODS[name](graphs[440000 + 100 * run_id], budget=70, horizon=10,
                                      seed=initialization_seed, device=device)
                synchronize(device)
                initialization = perf_counter() - tick
                cumulative_train = Counter()
                if str(device).startswith('cuda'):
                    torch.cuda.reset_peak_memory_stats()

                def evaluate(checkpoint):
                    with isolated_evaluation(agent):
                        for j in range(20):
                            graph_id, env_seed = 440900 + j // 2, 446000 + j
                            row = execute_episode(agent, graphs[graph_id], env_seed, device=device, training=False)
                            emit(dict(phase='evaluation', run_id=run_id, method=name, checkpoint=checkpoint,
                                      episode=j, graph_id=graph_id, environment_seed=env_seed,
                                      cumulative_train_counters=dict(cumulative_train), **row))
                    print(json.dumps(dict(run_id=run_id, method=name, phase='evaluation', checkpoint=checkpoint, completed=20)), flush=True)

                evaluate(0)
                for episode in range(128):
                    graph_id = 440000 + 100 * run_id + episode // 8
                    env_seed = 441000 + 1000 * run_id + episode
                    row = execute_episode(agent, graphs[graph_id], env_seed, device=device, training=True)
                    cumulative_train.update(row['counters'])
                    emit(dict(phase='train', run_id=run_id, method=name, checkpoint=episode + 1,
                              episode=episode, graph_id=graph_id, environment_seed=env_seed,
                              cumulative_train_counters=dict(cumulative_train), **row))
                    if (episode + 1) % 8 == 0:
                        print(json.dumps(dict(run_id=run_id, method=name, phase='train', completed=episode + 1)), flush=True)
                    if episode + 1 in PROTOCOL['checkpoints']:
                        evaluate(episode + 1)
                tick = perf_counter()
                policy_path = output_dir / 'models' / f'{name}_run{run_id}.pt'
                weight_bytes = save_policy(agent, name, policy_path, run_id)
                manifest['completed_runs'].append(dict(run_id=run_id, method=name,
                    initialization_seed=initialization_seed, initialization_seconds=initialization,
                    cumulative_model_work=dict(agent.counts), cumulative_train_counters=dict(cumulative_train),
                    model_path=str(policy_path.relative_to(output_dir)), model_bytes=weight_bytes,
                    model_save_seconds=perf_counter() - tick,
                    peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated() if str(device).startswith('cuda') else None))
                write_manifest()
                del agent
                gc.collect()
        manifest.update(status='complete', wall_seconds=perf_counter() - started)
        write_manifest()
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_weighted_v46')
    parser.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
    args = parser.parse_args()
    run(args.output_dir, args.device)
