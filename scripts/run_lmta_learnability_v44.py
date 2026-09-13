"""Frozen V44 multi-graph learning run. No tuning or best-checkpoint selection."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import gc
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

import networkx as nx
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.lmta_aim_v43 import AIMEnvironment, generate_graph
from acfqp.science.lmta_agent_v44 import LMTAAgent
from acfqp.science.lmta_baselines_v44 import FlatDQNAgent, BudgetHRLAgent
from acfqp.science.lmta_heuristics_v44 import AverageRandomAgent, AverageScoreAgent

METHODS = {'FLAT_DQN': FlatDQNAgent, 'BUDGET_HRL': BudgetHRLAgent, 'LMTA_RI': LMTAAgent}
HEURISTICS = {'AVERAGE_RANDOM': AverageRandomAgent, 'AVERAGE_SCORE': AverageScoreAgent}
PROTOCOL = dict(runs=3, training_episodes=128, checkpoints=[0, 32, 64, 128],
    panel_size=20, methods=list(METHODS), heuristics=list(HEURISTICS), horizon=10,
    primary_checkpoint=128, nodes=500, budget=70, p=.01, graph_rotation_every=8)


def synchronize(device):
    if str(device).startswith('cuda'):
        torch.cuda.synchronize()


@contextmanager
def isolated_evaluation(agent):
    """Evaluation may consume RNG and populate graph caches, but not steer training."""
    action_state = deepcopy(agent.rng.bit_generator.state)
    torch_state = torch.get_rng_state()
    cuda_state = torch.cuda.get_rng_state_all() if str(agent.device).startswith('cuda') else None
    previous_graph = agent.graph_id, agent.a
    try:
        yield
    finally:
        agent.rng.bit_generator.state = action_state
        torch.set_rng_state(torch_state)
        if cuda_state is not None:
            torch.cuda.set_rng_state_all(cuda_state)
        agent.graph_id, agent.a = previous_graph


def behaviour(result):
    days = result.get('day_history', [])
    if days and 'z' in days[0]:
        return {'daily_budgets': [r['budget'] for r in days],
                'daily_durations': [r['duration'] for r in days],
                'subgoals': [r['z'] for r in days],
                'search_values': [r['search_value'] for r in days]}
    actions = result.get('actions', [])
    if actions and 'budget' in actions[0]:
        return {'daily_budgets': [r['budget'] for r in actions],
                'daily_durations': [r['realized_duration'] for r in actions]}
    counts = [0] * 10
    for row in actions:
        if row['action'] != 500:
            counts[row['day']] += 1
    return {'daily_durations': counts}


def execute_episode(agent, graph, environment_seed, *, device, training):
    synchronize(device)
    tick = perf_counter()
    env = AIMEnvironment(graph, budget=70, horizon=10, seed=environment_seed)
    before = Counter(agent.counts)
    result = agent.run_episode(env, training=training)
    synchronize(device)
    seconds = perf_counter() - tick
    work = dict(Counter(agent.counts) - before)
    if env.day != 10 or result['raw_return'] != int(np.count_nonzero(env.statuses)):
        raise AssertionError('AIM reward or calendar disagrees with terminal state')
    if not np.isfinite(np.asarray(result['losses'], dtype=float)).all():
        raise AssertionError('Nonfinite training loss')
    if not training and any(v for k, v in work.items() if 'gradient_steps' in k):
        raise AssertionError('Evaluation performed a gradient update')
    return dict(raw_return=result['raw_return'], counters=env.counters['train' if training else 'evaluation'],
                model_work=work, wall_seconds=seconds, losses=result['losses'], **behaviour(result))


def save_policy(agent, name, path, run_id):
    attributes = ('model', 'low') if name == 'LMTA_RI' else ('ll', 'hl')
    payload = {key: {k: v.detach().cpu() for k, v in getattr(agent, key).state_dict().items()}
               for key in attributes if hasattr(agent, key)}
    torch.save(dict(method=name, run_id=run_id, training_episodes=128,
                    purpose='Inference reuse only; no optimizer or replay state.', weights=payload), path)
    return path.stat().st_size


def run(output_dir, device):
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / 'models').mkdir()
    torch.set_num_threads(1)
    started = perf_counter()
    graph_seeds = [440000 + r * 100 + i for r in range(3) for i in range(16)] + list(range(440900, 440910))
    tick = perf_counter()
    graphs = {seed: generate_graph(500, seed) for seed in graph_seeds}
    for seed, graph in graphs.items():
        graph.graph['replay_id'] = seed
    manifest = dict(schema='acfqp.lmta_learnability.v44', status='running', protocol=PROTOCOL,
        runtime=dict(python=platform.python_version(), numpy=np.__version__, networkx=nx.__version__,
                     torch=torch.__version__, device=device, torch_threads=torch.get_num_threads(),
                     gpu=torch.cuda.get_device_name() if str(device).startswith('cuda') else None),
        graphs=[dict(graph_id=k, nodes=len(g), edges=g.number_of_edges()) for k, g in graphs.items()],
        graph_generation_seconds=perf_counter() - tick, completed_runs=[],
        source_scope='V44 agents/runner and unchanged V43 environment/models; independently specified LMTA variant.')
    manifest_path = output_dir / 'manifest.json'

    def write_manifest():
        manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    write_manifest()
    with (output_dir / 'events.jsonl').open('x') as log:
        def emit(row):
            log.write(json.dumps(row, allow_nan=False) + '\n')
            log.flush()

        for name, Agent in HEURISTICS.items():
            for j in range(20):
                graph_id, env_seed = 440900 + j // 2, 446000 + j
                agent = Agent(graphs[graph_id], budget=70, horizon=10, seed=449000 + j)
                row = execute_episode(agent, graphs[graph_id], env_seed, device=device, training=False)
                emit(dict(phase='heuristic', run_id=None, method=name, checkpoint=None, episode=j,
                          graph_id=graph_id, environment_seed=env_seed, action_seed=449000 + j, **row))
            print(json.dumps(dict(method=name, phase='heuristic', completed=20)), flush=True)

        for run_id in range(3):
            order = list(METHODS)[run_id:] + list(METHODS)[:run_id]
            for name in order:
                tick = perf_counter()
                agent = METHODS[name](graphs[440000 + 100 * run_id], budget=70, horizon=10,
                                      seed=445001 + run_id, device=device)
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
                    initialization_seconds=initialization, cumulative_model_work=dict(agent.counts),
                    cumulative_train_counters=dict(cumulative_train), model_path=str(policy_path.relative_to(output_dir)),
                    model_bytes=weight_bytes, model_save_seconds=perf_counter() - tick,
                    peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated() if str(device).startswith('cuda') else None))
                write_manifest()
                del agent
                gc.collect()
        manifest.update(status='complete', wall_seconds=perf_counter() - started)
        write_manifest()
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_learnability_v44')
    parser.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
    args = parser.parse_args()
    run(args.output_dir, args.device)
