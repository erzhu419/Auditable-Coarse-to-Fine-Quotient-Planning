"""Run the frozen eight-episode V43 engineering probe, not a performance trial."""
from __future__ import annotations

import argparse
from collections import Counter
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
from acfqp.science.lmta_agent_v43 import LMTAAgent
from acfqp.science.lmta_baselines_v43 import FlatDQNAgent, BudgetHRLAgent


def synchronize(device):
    if str(device).startswith('cuda'):
        torch.cuda.synchronize()


def run(output_dir, device):
    output_dir.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    start = perf_counter()
    graphs = {seed: generate_graph(500, seed) for seed in (43000, 43010, 43011)}
    graph_seconds = perf_counter() - start
    summary = dict(schema='acfqp.lmta_independent.v43', status='running',
        purpose='Independent implementation engineering probe; no sample-efficiency or convergence verdict.',
        parameters=dict(n=500, p=.01, T=10, K=70, training_episodes=8, evaluation_episodes=2,
            graph_seed=43000, agent_seed=43001, train_environment_seed=43002,
            evaluation_graph_seeds=[43010, 43011], evaluation_environment_seeds=[43020, 43021],
            LMTA_mcts_simulations_per_decision=150),
        runtime=dict(python=platform.python_version(), numpy=np.__version__, networkx=nx.__version__,
            torch=torch.__version__, device=device,
            gpu=torch.cuda.get_device_name() if str(device).startswith('cuda') else None),
        graph_generation_seconds=graph_seconds, graphs={str(k):dict(nodes=len(g), edges=g.number_of_edges()) for k, g in graphs.items()},
        arms={}, checkpoint_files_written=0)
    with (output_dir / 'episodes.jsonl').open('x') as log:
        for name, Agent in [('FLAT_DQN', FlatDQNAgent), ('BUDGET_HRL', BudgetHRLAgent), ('LMTA_RI', LMTAAgent)]:
            tick = perf_counter()
            agent = Agent(graphs[43000], budget=70, horizon=10, seed=43001, device=device)
            synchronize(device)
            initialization = perf_counter() - tick
            train_env = AIMEnvironment(graphs[43000], budget=70, horizon=10, seed=43002)
            arm = dict(initialization_seconds=initialization, training=[], evaluation=[])
            for phase, count in [('train', 8), ('evaluation', 2)]:
                phase_work_before = Counter(agent.counts)
                phase_start = perf_counter()
                totals = Counter()
                for episode in range(count):
                    env = train_env if phase == 'train' else AIMEnvironment(graphs[43010 + episode], budget=70, horizon=10, seed=43020 + episode)
                    before = Counter(env.counters.get(phase, {}))
                    synchronize(device)
                    tick = perf_counter()
                    result = agent.run_episode(env, training=phase == 'train')
                    synchronize(device)
                    seconds = perf_counter() - tick
                    counters = Counter(env.counters.get(phase, {})) - before
                    total_influenced = int(np.count_nonzero(env.statuses != 0))
                    if result['raw_return'] != total_influenced or env.day != 10:
                        raise AssertionError('Return/state or calendar disagreement')
                    if not np.isfinite(np.asarray(result['losses'], dtype=float)).all():
                        raise AssertionError('Nonfinite training loss')
                    row = dict(arm=name, phase=phase, episode=episode, wall_seconds=seconds,
                        raw_return=result['raw_return'], counters=dict(counters),
                        losses=result['losses'], final_remaining_budget=env.remaining_budget)
                    log.write(json.dumps(row, allow_nan=False) + '\n')
                    log.flush()
                    totals.update(counters)
                    arm['training' if phase == 'train' else 'evaluation'].append(row)
                    print(json.dumps({k: row[k] for k in ('arm', 'phase', 'episode', 'raw_return', 'wall_seconds')}), flush=True)
                arm[phase + '_counters'] = dict(totals)
                arm[phase + '_model_work'] = dict(Counter(agent.counts) - phase_work_before)
                arm[phase + '_wall_seconds'] = perf_counter() - phase_start
            if not arm['train_model_work'].get('LL_gradient_steps', 0):
                raise AssertionError('Low-level learning did not execute')
            if name != 'FLAT_DQN' and not arm['train_model_work'].get('HL_gradient_steps', 0):
                raise AssertionError('High-level learning did not execute')
            if name == 'LMTA_RI' and not arm['train_model_work'].get('budget_gradient_steps', 0):
                raise AssertionError('Learned budget update did not execute')
            if any('gradient_steps' in key and value for key, value in arm['evaluation_model_work'].items()):
                raise AssertionError('Evaluation updated the model')
            summary['arms'][name] = arm
            (output_dir / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
            del agent
    summary.update(status='complete', engineering_checks_passed=True, scientifically_validated=False,
        wall_seconds=perf_counter() - start)
    (output_dir / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_independent_v43')
    parser.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
    args = parser.parse_args()
    run(args.output_dir, args.device)
