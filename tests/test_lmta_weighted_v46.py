"""Tiny development episodes with explicit physical-call accounting."""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import networkx as nx
import numpy as np
import pytest
import torch

from acfqp.science.lmta_agent_v44 import LMTAAgent as OldLMTA
from acfqp.science.lmta_baselines_v44 import FlatDQNAgent as OldFlat, BudgetHRLAgent as OldBudget
from acfqp.science.lmta_aim_v43 import AIMEnvironment
from acfqp.science.lmta_structure_v45 import weighted_adjacency
from acfqp.science.lmta_weighted_v46 import LMTAAgent, FlatDQNAgent, BudgetHRLAgent

SPEC = importlib.util.spec_from_file_location('v44_weighted_test_runner',
    Path(__file__).resolve().parents[1] / 'scripts/run_lmta_learnability_v44.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
PAIRS = [(OldLMTA, LMTAAgent), (OldFlat, FlatDQNAgent), (OldBudget, BudgetHRLAgent)]


@pytest.fixture(scope='module', autouse=True)
def charge_development_calls():
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    counts = Counter()
    with ExitStack() as stack:
        for name in ('select', 'finish_day', 'transition', 'reset'):
            original = getattr(AIMEnvironment, name)

            def measured(self, *args, original=original, name=name, **kwargs):
                counts[name + '_calls'] += 1
                result = original(self, *args, **kwargs)
                if name == 'transition':
                    counts['propagation_draws'] += result[2]['propagation_draws']
                return result

            stack.enter_context(patch.object(AIMEnvironment, name, measured))
        yield counts
    torch.set_num_threads(previous_threads)
    print('\nV46_DEVELOPMENT_ACCOUNTING=' + json.dumps({'counters': dict(counts),
        'scope': 'Tiny test graphs only, excluded from the main experiment. select is a primitive '
            'selection; finish_day is a physical daily transition. transition is nested inside '
            'finish_day and must not be added as another physical sample. reset includes constructor '
            'and episode resets. Observers forward original calls and draw no RNG.'}, sort_keys=True))


def graphs():
    result = []
    for identifier, edges in [(460001, [(0, 5), (0, 6), (1, 6), (2, 7)]),
                               (460002, [(3, 5), (4, 5), (6, 7)])]:
        graph = nx.DiGraph()
        graph.add_nodes_from(range(8))
        graph.add_edges_from(edges)
        graph.graph['replay_id'] = identifier
        result.append(graph)
    return result


def make_agent(cls, graph, budget=1, horizon=1):
    kwargs = {'simulations': 3} if issubclass(cls, OldLMTA) else {}
    return cls(graph, budget, horizon, seed=46, **kwargs)


def modules(agent):
    names = ('model', 'low', 'target') if isinstance(agent, OldLMTA) else ('ll', 'll_target', 'hl', 'hl_target')
    return {name: getattr(agent, name) for name in names if hasattr(agent, name)}


def copy_rng(agent):
    copied = np.random.default_rng(0)
    copied.bit_generator.state = deepcopy(agent.rng.bit_generator.state)
    return copied


@pytest.mark.parametrize('old_cls,new_cls', PAIRS)
def test_initial_networks_identical_and_both_graph_caches_are_weighted_float32(old_cls, new_cls):
    first, second = graphs()
    old, new = make_agent(old_cls, first), make_agent(new_cls, first)
    assert not torch.equal(old.a, new.a)
    for name, network in modules(old).items():
        assert network.state_dict().keys() == modules(new)[name].state_dict().keys()
        for key, tensor in network.state_dict().items():
            torch.testing.assert_close(tensor, modules(new)[name].state_dict()[key], rtol=0, atol=0)
    assert old.rng.bit_generator.state == new.rng.bit_generator.state
    cached = new.a
    new.set_graph(second)
    cache = new.adjacency_cache if isinstance(new, OldLMTA) else new.graph_adjacencies
    assert set(cache) == {460001, 460002}
    for graph in (first, second):
        actual = cache[graph.graph['replay_id']]
        assert actual.dtype == torch.float32
        torch.testing.assert_close(actual, weighted_adjacency(graph, dtype=torch.float32), rtol=0, atol=0)
    assert cache[460001][0, 6] == .5 and cache[460001][0, 0] == 1.
    new.set_graph(first)
    assert new.a is cached


@pytest.mark.parametrize('cls', [LMTAAgent, FlatDQNAgent, BudgetHRLAgent])
def test_mixed_graph_replay_updates_use_each_collected_weighted_operator(cls):
    first, second = graphs()
    agent = make_agent(cls, first)
    for index in range(8):
        graph = (first, second)[index % 2]
        result = agent.run_episode(AIMEnvironment(graph, budget=1, horizon=1, seed=460100 + index))
        assert np.isfinite(result['losses']).all()
    lmta = isinstance(agent, OldLMTA)
    replay = agent.low_replay if lmta else agent.ll_replay
    assert len(replay) == 8 and {row[-1] for row in replay} == {460001, 460002}
    cache = agent.adjacency_cache if lmta else agent.graph_adjacencies

    def check_update(replay, networks, update):
        rng = copy_rng(agent)
        batch = [replay[int(index)] for index in rng.choice(len(replay), 8, replace=False)]
        expected = torch.stack([cache[row[-1]] for row in batch])
        captured = []
        handles = [network.register_forward_pre_hook(lambda _, args: captured.append(args[1].detach().clone()))
            for network in networks]
        try:
            assert np.isfinite(update())
        finally:
            for handle in handles:
                handle.remove()
        assert len(captured) == len(networks)
        for actual in captured:
            torch.testing.assert_close(actual, expected, rtol=0, atol=0)
        assert sum(torch.equal(row, cache[460001]) for row in expected) == 4

    if not lmta:
        check_update(agent.ll_replay, (agent.ll, agent.ll_target), agent._learn_ll)
        if isinstance(agent, OldBudget):
            check_update(agent.hl_replay, (agent.hl, agent.hl_target), lambda: agent._update(
                agent.hl_replay, agent.hl, agent.hl_target, agent.hl_optimizer, 'hl'))
        return

    check_update(agent.low_replay, (agent.low, agent.target), agent.update_low)
    assert len(agent.games) == 8 and agent.counts['HL_gradient_steps'] == 1
    rng = copy_rng(agent)
    games = [agent.games[int(index)] for index in rng.choice(len(agent.games), 8, replace=False)]
    expected = []
    for game in games:
        start = int(rng.integers(len(game)))
        expected.extend([cache[game[start]['graph_id']]] * (1 + len(game[start:start + 5])))
    micro = [agent.low_replay[int(index)] for index in rng.choice(len(agent.low_replay), 8, replace=False)]
    micro_a = torch.stack([cache[row[-1]] for row in micro])
    expected.extend([micro_a, micro_a])
    captured = []
    handle = agent.model.encoder.register_forward_pre_hook(lambda _, args: captured.append(args[1].detach().clone()))
    try:
        assert np.isfinite(agent.update_high())
    finally:
        handle.remove()
    assert len(captured) == len(expected)
    for actual, wanted in zip(captured, expected):
        torch.testing.assert_close(actual, wanted, rtol=0, atol=0)


@pytest.mark.parametrize('cls', [LMTAAgent, FlatDQNAgent, BudgetHRLAgent])
def test_isolated_evaluation_preserves_next_training_update(cls):
    first, second = graphs()
    agent, reference = [make_agent(cls, first, budget=4, horizon=2) for _ in range(2)]
    for learner in (agent, reference):
        learner.run_episode(AIMEnvironment(first, budget=4, horizon=2, seed=460201))
    action_state = deepcopy(agent.rng.bit_generator.state)
    torch_state = torch.get_rng_state()
    before_updates = agent.counts['LL_gradient_steps']
    before_episodes = agent.episodes if isinstance(agent, OldLMTA) else agent.training_episodes
    with runner.isolated_evaluation(agent):
        agent.run_episode(AIMEnvironment(second, budget=4, horizon=2, seed=460202), training=False)
        torch.rand(3)
    assert agent.rng.bit_generator.state == action_state
    assert torch.equal(torch.get_rng_state(), torch_state)
    assert agent.graph_id == 460001
    assert (agent.episodes if isinstance(agent, OldLMTA) else agent.training_episodes) == before_episodes
    results = [learner.run_episode(AIMEnvironment(first, budget=4, horizon=2, seed=460203))
        for learner in (agent, reference)]
    assert agent.counts['LL_gradient_steps'] > before_updates
    assert results[0]['raw_return'] == results[1]['raw_return']
    np.testing.assert_array_equal(results[0]['losses'], results[1]['losses'])
    if isinstance(agent, OldLMTA):
        assert results[0]['day_history'] == results[1]['day_history']
        assert [row[2] for row in agent.low_replay] == [row[2] for row in reference.low_replay]
    else:
        assert results[0]['actions'] == results[1]['actions']
    assert agent.rng.bit_generator.state == reference.rng.bit_generator.state
    for name, network in modules(agent).items():
        for key, tensor in network.state_dict().items():
            torch.testing.assert_close(tensor, modules(reference)[name].state_dict()[key], rtol=0, atol=0)
