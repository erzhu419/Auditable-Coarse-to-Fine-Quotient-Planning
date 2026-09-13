"""Observe one original WS-option training update and same-graph evaluation."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import json
from pathlib import Path
import random
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'acfqp-ws-option-reference-v42-source'
SOURCE_COMMIT = 'd6790c4db0bcc475e74aec267c152d0253959fc6'


def load_reference(source=SOURCE):
    sys.path.insert(0, str(source / 'IM'))
    from Agent import Agent
    from Env import Env
    return Agent, Env


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def node_counts(state):
    return {name: int(state[:, index].sum()) for index, name in enumerate(('inactive', 'active', 'removed'))}


class Observer:
    """Scoped forwarding wrappers: they neither alter arguments nor draw RNG."""
    def __init__(self, agent, writer=None):
        self.agent, self.env, self.writer = agent, agent.env, writer
        self.phase, self.rng_kind, self.inside_step = 'training_trajectory', None, False
        self.counts, self.episodes, self.optimizer_counts = defaultdict(Counter), {}, Counter()
        self.step_original = self.env.step
        self.uniform_original = random.uniform
        self.episode_original = agent.run_episode
        self.simulation_original = agent.run_simulation
        self.step_index = 0
        self.observer_seconds = 0.

    def __enter__(self):
        self.stack = ExitStack()
        for obj, name, wrapper in ((self.env, 'step', self.step), (random, 'uniform', self.uniform),
                (self.agent, 'run_episode', self.episode), (self.agent, 'run_simulation', self.simulation)):
            self.stack.enter_context(patch.object(obj, name, wrapper))
        for method, kind in (('activate_seeds', 'seed_activation'), ('activate_nodes', 'propagation')):
            original = getattr(self.env, method)
            def activate(*args, original=original, kind=kind, **kwargs):
                previous = self.rng_kind
                self.rng_kind = kind
                try:
                    return original(*args, **kwargs)
                finally:
                    self.rng_kind = previous
            self.stack.enter_context(patch.object(self.env, method, activate))
        for label, optimizer in (('HL', self.agent.optimizer), ('LL', self.agent.optimizer_sub)):
            original = optimizer.step
            def step(*args, original=original, label=label, **kwargs):
                self.optimizer_counts[label + '_step_calls'] += 1
                tick = perf_counter()
                try:
                    return original(*args, **kwargs)
                finally:
                    self.optimizer_counts[label + '_step_seconds'] += perf_counter() - tick
            self.stack.enter_context(patch.object(optimizer, 'step', step))
        return self

    def __exit__(self, *exception):
        return self.stack.__exit__(*exception)

    def uniform(self, *args, **kwargs):
        if self.inside_step:
            counts = self.counts[self.phase]
            counts['random_uniform_calls'] += 1
            counts['random_uniform_' + (self.rng_kind or 'other') + '_calls'] += 1
        return self.uniform_original(*args, **kwargs)

    def step(self, state, action):
        tick = perf_counter()
        phase, counts = self.phase, self.counts[self.phase]
        requested = [int(node) for node in action]
        invalid = [node for node in requested if not 0 <= node < self.env.n or state[node, 0] != 1]
        counts.update(env_step_calls=1, requested_seed_exposures=len(requested), empty_action_calls=int(not requested),
            invalid_seed_requests=len(invalid), duplicate_seed_requests=len(requested) - len(set(requested)),
            passed_state_differs_from_internal_calls=int(not np.array_equal(state, self.env.state)))
        rng_before = counts['random_uniform_calls']
        self.observer_seconds += perf_counter() - tick
        started = perf_counter()
        self.inside_step = True
        try:
            result = self.step_original(state, action)
        finally:
            self.inside_step = False
            counts['instrumented_env_step_seconds'] += perf_counter() - started
        tick = perf_counter()
        next_state, reward, done, is_null = result
        counts['raw_undiscounted_reward_sum'] += float(reward)
        counts['done_returns'] += int(done)
        counts['null_returns'] += int(is_null)
        event = {'step_index': self.step_index, 'phase': phase, 'action': requested,
            'invalid_seed_requests': invalid, 'reward': float(reward), 'done': bool(done),
            'is_null': bool(is_null), 'random_uniform_calls': counts['random_uniform_calls'] - rng_before,
            'next_state_counts': node_counts(next_state)}
        self.step_index += 1
        if self.writer is not None:
            self.writer.write(json.dumps(event, separators=(',', ':')) + '\n')
        self.observer_seconds += perf_counter() - tick
        return result

    def simulation(self, state, action, iter_num=10):
        previous = self.phase
        self.phase = 'reward_estimation'
        counts = self.counts[self.phase]
        counts.update(run_simulation_calls=1, requested_simulation_iterations=iter_num)
        started = perf_counter()
        try:
            result = self.simulation_original(state, action, iter_num=iter_num)
            counts['simulation_mean_reward_sum'] += float(result)
            return result
        finally:
            counts['instrumented_run_simulation_seconds'] += perf_counter() - started
            self.phase = previous

    def episode(self, *args, **kwargs):
        phase = self.phase
        started = perf_counter()
        result = self.episode_original(*args, **kwargs)
        _, options, actions, rewards, done, score = result
        self.episodes[phase] = {'actions': [[int(node) for node in action] for action in actions],
            'options': [[int(value) for value in option] for option in options], 'rewards': [float(value) for value in rewards],
            'done': [bool(value) for value in done], 'raw_undiscounted_reward': float(sum(rewards)),
            'original_discounted_score': float(score), 'instrumented_episode_seconds': perf_counter() - started,
            'final_state_counts': node_counts(self.env.state)}
        return result

    def report(self):
        phases = {phase: {**dict(counts), 'original_discounted_score': self.episodes.get(phase, {}).get('original_discounted_score')}
            for phase, counts in self.counts.items()}
        return {'phases': phases, 'episodes': self.episodes, 'optimizer': dict(self.optimizer_counts),
            'total_env_step_calls': sum(row['env_step_calls'] for row in self.counts.values()),
            'total_requested_seed_exposures': sum(row['requested_seed_exposures'] for row in self.counts.values()),
            'observer_outside_step_seconds': self.observer_seconds,
            'scope': 'Step calls and requested seed exposures are distinct units. Prefix re-simulations are fully counted. Invalid means not inactive in the passed state, including out-of-range indices; duplicates are also listed separately. Reward-estimation calls have one-step rewards and no original discounted episode score. Timings include instrumentation; optimizer/episode/simulation/step spans are nested and must not be added.'}


def state_argument_witness(Env):
    """Keep the original internal-state filtering behavior and isolate its RNG."""
    previous = random.getstate()
    env = Env(nx.DiGraph([(0, 1)]), budget=1, T=1)
    passed = env.state.copy()
    outcomes, draws = [], Counter()
    original = random.uniform
    def uniform(*args, **kwargs):
        draws['calls'] += 1
        return original(*args, **kwargs)
    try:
        with patch.object(random, 'uniform', uniform):
            for removed in (False, True):
                env.state = passed.copy()
                if removed:
                    env.set_state_index(env.state, [1], 2)
                internal = env.state.copy()
                random.seed(42003)
                before = draws['calls']
                result = env.step(passed, [0])
                outcomes.append({'internal_node1_removed': removed, 'passed_state': passed.tolist(),
                    'internal_state': internal.tolist(), 'next_state': result[0].tolist(), 'reward': float(result[1]),
                    'done': bool(result[2]), 'is_null': bool(result[3]), 'random_uniform_calls': draws['calls'] - before})
    finally:
        random.setstate(previous)
    return {'outcomes': outcomes, 'passed_state_action_and_initial_rng_identical': True,
        'outcome_depends_on_internal_state': outcomes[0]['next_state'] != outcomes[1]['next_state'],
        'development_env_step_calls': 2, 'development_random_uniform_calls': draws['calls'],
        'scope': 'Separate two-node semantic witness, excluded from the ER500 pilot counts. Original Env.step calls get_inactive_neighbors without its state argument; no behavior is repaired.'}


def run_pilot(output_dir):
    if output_dir.exists():
        raise FileExistsError('Retain existing pilot outputs; do not overwrite')
    head = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    if head != SOURCE_COMMIT or subprocess.check_output(['git', '-C', str(SOURCE), 'diff', 'HEAD', '--'], text=True):
        raise ValueError('Reference source revision or tracked contents differ')
    Agent, Env = load_reference()
    output_dir.mkdir(parents=True)
    started = perf_counter()
    graph_rng = random.Random(42000)
    graph_random = graph_rng.random
    graph_counts = Counter()
    def draw():
        graph_counts['random_calls'] += 1
        return graph_random()
    graph_rng.random = draw
    tick = perf_counter()
    graph = nx.erdos_renyi_graph(500, .01, seed=graph_rng, directed=True)
    graph_seconds = perf_counter() - tick
    seed_all(42001)
    tick = perf_counter()
    env = Env(graph, budget=70, T=10)
    agent = Agent(env)
    initialization_seconds = perf_counter() - tick
    with (output_dir / 'steps.jsonl').open('x', encoding='utf-8') as writer, Observer(agent, writer) as observer:
        tick = perf_counter()
        losses = agent.update_q_function(budget_policy='average', seeding_policy='agent')
        training_seconds = perf_counter() - tick
        seed_all(42002)
        agent.eval()
        observer.phase = 'evaluation'
        tick = perf_counter()
        agent.run_episode(budget_policy='average', seeding_policy='agent', epsilon=0, beam_search=False)
        evaluation_seconds = perf_counter() - tick
    report = {'schema': 'acfqp.lmta_sample_accounting.v42', 'source_commit': head,
        'parameters': {'nodes': 500, 'edge_probability': .01, 'T': 10, 'K': 70, 'graph_seed': 42000, 'agent_train_seed': 42001, 'evaluation_seed': 42002,
            'budget_policy': 'average', 'seeding_policy': 'agent', 'training_updates': 1, 'evaluation_episodes': 1},
        'runtime': {'python': sys.version, 'networkx': nx.__version__, 'torch': torch.__version__, 'device': str(agent.A.device)},
        'graph': {'nodes': graph.number_of_nodes(), 'edges': graph.number_of_edges(), **graph_counts, 'generation_seconds': graph_seconds},
        'initialization_seconds': initialization_seconds, 'training_update_seconds': training_seconds, 'evaluation_seconds': evaluation_seconds,
        'training_return': {'HL_loss': float(losses[0]), 'LL_loss': float(losses[1]), 'original_discounted_score': float(losses[2])},
        **observer.report(), 'state_argument_witness': state_argument_witness(Env),
        'pilot_wall_seconds': perf_counter() - started, 'checkpoint_files_written': 0,
        'interpretation': 'One original WS-option counting pilot at the explicitly chosen AIM scale. Same-graph evaluation is an execution check, not generalization or an LMTA reproduction. Separate witness and test draws are development work. Original source, policy methods, reward simulations and state semantics are unchanged.'}
    (output_dir / 'summary.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_sample_v42')
    args = parser.parse_args()
    report = run_pilot(args.output_dir)
    print(json.dumps({key: report[key] for key in ('total_env_step_calls', 'total_requested_seed_exposures', 'training_update_seconds', 'evaluation_seconds', 'optimizer')}, indent=2))


if __name__ == '__main__':
    main()
