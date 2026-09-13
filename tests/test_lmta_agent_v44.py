"""Graph-bound replay checks using tiny engineering episodes, never the main run."""
from copy import deepcopy

import networkx as nx
import numpy as np
import pytest
import torch

from acfqp.science.lmta_agent_v43 import LMTAAgent as V43Agent
from acfqp.science.lmta_agent_v44 import LMTAAgent
from acfqp.science.lmta_aim_v43 import AIMEnvironment


@pytest.fixture(autouse=True)
def one_torch_thread():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def graph(seed):
    result = nx.DiGraph()
    result.add_nodes_from(range(8))
    result.add_edges_from({101: [(0, 6), (1, 7)],
                           102: [(2, 6), (3, 7)],
                           103: [(4, 6), (5, 7)]}[seed])
    result.graph['replay_id'] = seed
    return result


def copy_rng(agent):
    rng = np.random.default_rng()
    rng.bit_generator.state = deepcopy(agent.rng.bit_generator.state)
    return rng


def test_mixed_replay_uses_collected_graph_for_ll_hl_and_mts_after_graph_switch():
    environments = [AIMEnvironment(graph(seed), budget=4, horizon=3, seed=seed)
                    for seed in (101, 102)]
    agent = LMTAAgent(environments[0].graph, 4, 3, 11, simulations=3)
    results = [agent.run_episode(environments[i % 2]) for i in range(8)]
    assert {row[7] for row in agent.low_replay} == {101, 102}
    assert {row['graph_id'] for game in agent.games for row in game} == {101, 102}
    assert all(len({row['graph_id'] for row in game}) == 1 for game in agent.games)
    assert np.isfinite([loss for result in results for loss in result['losses']]).all()
    assert agent.counts['HL_gradient_steps'] == 1
    cached = agent.adjacency_cache[101]
    agent.set_graph(graph(101))
    assert agent.a is cached
    agent.set_graph(graph(103))  # This graph has no collected replay samples.

    rng = copy_rng(agent)
    batch = [agent.low_replay[int(i)] for i in rng.choice(len(agent.low_replay), 8, replace=False)]
    expected = torch.stack([agent.adjacency_cache[row[7]] for row in batch])
    ll_calls, target_calls = [], []
    handles = [agent.low.register_forward_pre_hook(lambda _, args: ll_calls.append(args[1].clone())),
               agent.target.register_forward_pre_hook(lambda _, args: target_calls.append(args[1].clone()))]
    try:
        assert np.isfinite(agent.update_low())
    finally:
        for handle in handles:
            handle.remove()
    assert len(ll_calls) == len(target_calls) == 1
    torch.testing.assert_close(ll_calls[0], expected, rtol=0, atol=0)
    torch.testing.assert_close(target_calls[0], expected, rtol=0, atol=0)

    # Reconstruct only the sampled indices; the actual encoders are observed by hooks.
    rng = copy_rng(agent)
    games = [agent.games[int(i)] for i in rng.choice(len(agent.games), 8, replace=False)]
    expected_calls = []
    for game in games:
        start = int(rng.integers(len(game)))
        a = agent.adjacency_cache[game[start]['graph_id']]
        expected_calls.extend([a] * (1 + len(game[start:start + 5])))
    micro = [agent.low_replay[int(i)] for i in rng.choice(len(agent.low_replay), 8, replace=False)]
    micro_a = torch.stack([agent.adjacency_cache[row[7]] for row in micro])
    expected_calls.extend([micro_a, micro_a])
    encoder_calls = []
    handle = agent.model.encoder.register_forward_pre_hook(
        lambda _, args: encoder_calls.append(args[1].clone()))
    try:
        assert np.isfinite(agent.update_high())
    finally:
        handle.remove()
    assert len(encoder_calls) == len(expected_calls)
    for actual, expected in zip(encoder_calls, expected_calls):
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    assert agent.graph_id == 103
    assert all(torch.isfinite(p).all() for p in agent.model.parameters())
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in agent.model.parameters())


def test_single_graph_training_matches_v43_actions_rewards_and_updates():
    old = V43Agent(graph(101), 4, 3, 11, simulations=3)
    new = LMTAAgent(graph(101), 4, 3, 11, simulations=3)
    old_env = AIMEnvironment(graph(101), budget=4, horizon=3, seed=13)
    new_env = AIMEnvironment(graph(101), budget=4, horizon=3, seed=13)
    for _ in range(8):
        old_result = old.run_episode(old_env)
        new_result = new.run_episode(new_env)
        assert old_result['primitive_selections'] == new_result['primitive_selections']
        assert old_result['raw_return'] == new_result['raw_return']
        np.testing.assert_allclose(old_result['losses'], new_result['losses'], rtol=0, atol=1e-7)
    assert old.counts == new.counts
    assert old_env.counters == new_env.counters
    assert old.rng.bit_generator.state == new.rng.bit_generator.state
    assert [row[2] for row in old.low_replay] == [row[2] for row in new.low_replay]
    assert [row[3] for row in old.low_replay] == [row[3] for row in new.low_replay]
    assert new.low.encoder is new.model.encoder
    for old_module, new_module in ((old.model, new.model), (old.low, new.low), (old.target, new.target)):
        for key, tensor in old_module.state_dict().items():
            torch.testing.assert_close(tensor, new_module.state_dict()[key], rtol=0, atol=1e-7)


def test_initial_evaluation_uses_deployed_budget_policy_without_training_warmup(monkeypatch):
    env = AIMEnvironment(graph(101), budget=4, horizon=3, seed=13)
    agent = LMTAAgent(env.graph, 4, 3, 11, simulations=3)
    # Equal logits deploy budget zero until the separately specified last-day rule.
    with torch.no_grad():
        for parameter in agent.model.budget.parameters():
            parameter.zero_()
    before = {key: tensor.clone() for key, tensor in agent.model.state_dict().items()}
    budgets = []
    finish_day = env.finish_day

    def record_day(**kwargs):
        budgets.append(len(env.daily_selected))
        return finish_day(**kwargs)

    monkeypatch.setattr(env, 'finish_day', record_day)
    result = agent.run_episode(env, training=False)
    assert budgets == [0, 0, 4]
    assert [row['day'] for row in result['day_history']] == [0, 1, 2]
    assert [row['duration'] for row in result['day_history']] == budgets
    assert sum(row['duration'] for row in result['day_history']) == result['primitive_selections'] == 4
    assert sum(row['reward'] for row in result['day_history']) == result['raw_return']
    assert all(set(row) == {'day', 'z', 'budget', 'duration', 'reward',
                            'search_value', 'capacity', 'forced'} for row in result['day_history'])
    assert agent.episodes == 0 and not agent.games and not agent.low_replay
    assert result['losses'] == []
    assert env.counters['evaluation']['primitive_selections'] == 4
    for key, tensor in before.items():
        torch.testing.assert_close(tensor, agent.model.state_dict()[key], rtol=0, atol=0)
