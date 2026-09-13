import networkx as nx
import numpy as np
import pytest
import torch

from acfqp.science.lmta_aim_v43 import AIMEnvironment
from acfqp.science.lmta_baselines_v44 import BudgetHRLAgent, FlatDQNAgent
from acfqp.science.lmta_heuristics_v44 import AverageRandomAgent, AverageScoreAgent


def graph(identifier, n=6, edges=()):
    result = nx.DiGraph()
    result.add_nodes_from(range(n))
    result.add_edges_from(edges)
    result.graph["replay_id"] = identifier
    return result


@pytest.fixture
def single_thread():
    before = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(before)


@pytest.mark.parametrize("cls", [FlatDQNAgent, BudgetHRLAgent])
def test_replay_uses_collection_graph_after_evaluation_switch(cls, single_thread):
    train_graph, evaluation_graph = graph(11), graph(12, edges=[(0, 1)])
    agent = cls(train_graph, 1, 1, 0)
    env = AIMEnvironment(train_graph, budget=1, horizon=1)
    for _ in range(8):
        agent.run_episode(env)
    agent.run_episode(AIMEnvironment(evaluation_graph, budget=1, horizon=1), training=False)
    assert agent.graph_id == 12 and all(row[-1] == 11 for row in agent.ll_replay)
    captured = []
    hooks = [network.register_forward_pre_hook(lambda _, args: captured.append(args[1].clone()))
             for network in (agent.ll, agent.ll_target)]
    try:
        assert np.isfinite(agent._learn_ll())
    finally:
        for hook in hooks:
            hook.remove()
    assert len(captured) == 2
    for batch_a in captured:
        assert batch_a.shape == (8, 6, 6)
        assert torch.equal(batch_a, agent.graph_adjacencies[11].expand(8, -1, -1))
        assert not torch.equal(batch_a[0], agent.a)
    if cls is BudgetHRLAgent:
        assert all(row[-1] == 11 for row in agent.hl_replay)


@pytest.mark.parametrize("cls", [FlatDQNAgent, BudgetHRLAgent])
def test_mixed_graph_batch_has_finite_gradients_in_both_learners(cls, single_thread):
    graphs = [graph(21), graph(22, edges=[(0, 1), (2, 3)])]
    agent = cls(graphs[0], 1, 1, 1)
    for g in graphs:
        for _ in range(4):
            agent.run_episode(AIMEnvironment(g, budget=1, horizon=1))
    assert {row[-1] for row in agent.ll_replay} == {21, 22}
    learners = [(agent.ll_replay, agent.ll, agent.ll_target, agent.ll_optimizer, "ll")]
    if cls is BudgetHRLAgent:
        learners.append((agent.hl_replay, agent.hl, agent.hl_target, agent.hl_optimizer, "hl"))
    for replay, net, target, optimizer, level in learners:
        captured = []
        hook = net.register_forward_pre_hook(lambda _, args: captured.append(args[1].clone()))
        try:
            assert np.isfinite(agent._update(replay, net, target, optimizer, level))
        finally:
            hook.remove()
        batch_a = captured[0]
        for identifier in (21, 22):
            assert sum(torch.equal(row, agent.graph_adjacencies[identifier]) for row in batch_a) == 4
        gradients = [p.grad for p in net.parameters() if p.grad is not None]
        assert gradients and all(torch.isfinite(g).all() for g in gradients)
    assert agent.total_replay_draws == 8 * agent.total_train_updates


def test_score_recomputes_after_each_selection_and_uses_lowest_tie():
    g = graph(31, 7, [(0, 3), (0, 4), (0, 5), (1, 0), (1, 6), (2, 6), (2, 4)])
    agent = AverageScoreAgent(g, 2, 1, 0)
    result = agent.run_episode(AIMEnvironment(g, budget=2, horizon=1))
    assert result["actions"][0]["selected"] == [0, 2]
    tied = graph(32)
    result = agent.run_episode(AIMEnvironment(tied, budget=2, horizon=1))
    assert result["actions"][0]["selected"] == [0, 1]


@pytest.mark.parametrize("cls", [AverageRandomAgent, AverageScoreAgent])
def test_heuristics_charge_real_selections_and_all_ten_days(cls):
    g = graph(41, 20)
    env = AIMEnvironment(g, budget=7, horizon=10)
    agent = cls(g, 7, 10, 2)
    result = agent.run_episode(env)
    assert result["primitive_selections"] == result["raw_return"] == 7
    assert result["day_transitions"] == 10 and result["propagation_draws"] == 0
    assert [a["budget"] for a in result["actions"]] == [1] * 7 + [0] * 3
    selected = [v for day in result["actions"] for v in day["selected"]]
    assert len(set(selected)) == 7
    assert set(env.counters) == {"evaluation"}
    assert result["train_updates"] == result["replay_draws"] == 0


def test_score_keeps_old_active_propagation_on_zero_budget_days():
    g = graph(51, 4, [(0, 1), (1, 2), (2, 3)])
    agent = AverageScoreAgent(g, 1, 3, 0)
    result = agent.run_episode(AIMEnvironment(g, budget=1, horizon=3))
    assert result["raw_return"] == 4 and result["primitive_selections"] == 1
    assert result["propagation_draws"] == result["day_transitions"] == 3
    assert [a["reward"] for a in result["actions"]] == [2, 1, 1]
