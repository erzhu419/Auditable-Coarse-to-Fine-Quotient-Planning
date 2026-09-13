import networkx as nx
import numpy as np
import torch

from acfqp.science.lmta_aim_v43 import AIMEnvironment
from acfqp.science.lmta_baselines_v43 import BudgetHRLAgent, FlatDQNAgent


def graph(n, edges=()):
    g = nx.DiGraph()
    g.add_nodes_from(range(n))
    g.add_edges_from(edges)
    return g


def first_legal(network, observation, legal, training):
    return int(np.flatnonzero(legal)[0])


def test_flat_last_seed_retains_all_residual_propagation():
    g = graph(4, [(0, 1), (1, 2), (2, 3)])
    env = AIMEnvironment(g, budget=1, horizon=3)
    agent = FlatDQNAgent(g, 1, 3, 0)
    agent._act = first_legal
    result = agent.run_episode(env)
    assert result["raw_return"] == 4
    assert result["primitive_selections"] == 1
    assert result["epsilon"] == .9
    assert result["day_transitions"] == result["propagation_draws"] == 3
    assert len(agent.ll_replay) == 1
    assert agent.ll_replay[-1][2] == 4
    assert agent.ll_replay[-1][-1] and not agent.ll_replay[-1][-2].any()


def test_flat_end_day_is_available_then_masked_on_final_day():
    g = graph(4)
    env = AIMEnvironment(g, budget=2, horizon=2)
    agent = FlatDQNAgent(g, 2, 2, 1)
    agent._act = lambda net, obs, legal, training: int(np.flatnonzero(legal)[-1])
    result = agent.run_episode(env)
    assert [a["action"] for a in result["actions"]] == [4, 3, 2]
    assert result["primitive_selections"] == result["raw_return"] == 2
    assert result["day_transitions"] == 2


def test_budget_zero_allocation_days_keep_environment_reward():
    g = graph(4, [(0, 1), (1, 2), (2, 3)])
    env = AIMEnvironment(g, budget=1, horizon=3)
    agent = BudgetHRLAgent(g, 1, 3, 2)
    agent._act = first_legal
    result = agent.run_episode(env)
    assert [a["budget"] for a in result["actions"]] == [1, 0, 0]
    assert [row[2] for row in agent.hl_replay] == [2, 1, 1]
    assert len(agent.ll_replay) == 1 and agent.ll_replay[0][2] == 2
    assert agent.ll_replay[0][-1] and not agent.ll_replay[0][-2].any()
    assert result["raw_return"] == 4 and result["day_transitions"] == 3


def test_both_learners_update_copy_targets_and_evaluation_does_not_train():
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        g = graph(10)
        env = AIMEnvironment(g, budget=8, horizon=2)
        for cls in (FlatDQNAgent, BudgetHRLAgent):
            agent = cls(g, 8, 2, 3)
            agent._act = first_legal
            initial = {k: p.clone() for k, p in agent.ll.state_dict().items()}
            for _ in range(4):
                result = agent.run_episode(env)
                assert result["raw_return"] == result["primitive_selections"] == 8
                assert result["day_transitions"] == 2
            assert agent.counts["LL_gradient_steps"] > 0
            assert any(not torch.equal(initial[k], p) for k, p in agent.ll.state_dict().items())
            if cls is BudgetHRLAgent:
                assert agent.counts["HL_gradient_steps"] > 0
            assert agent.total_replay_draws == 8 * agent.total_train_updates
            agent.counts["LL_gradient_steps"] = 99
            agent._learn_ll()
            assert all(torch.equal(p, agent.ll_target.state_dict()[k])
                       for k, p in agent.ll.state_dict().items())
            updates, replay, episodes = agent.total_train_updates, len(agent.ll_replay), agent.training_episodes
            evaluation = agent.run_episode(env, training=False)
            assert evaluation["train_updates"] == evaluation["replay_draws"] == 0
            assert (agent.total_train_updates, len(agent.ll_replay), agent.training_episodes) == (updates, replay, episodes)
    finally:
        torch.set_num_threads(old_threads)


def test_episode_uses_heldout_graph_and_budget_caps_legal_choices():
    training_graph = graph(3)
    heldout_graph = graph(3, [(0, 1)])
    for cls in (FlatDQNAgent, BudgetHRLAgent):
        agent = cls(training_graph, 5, 2, 4)
        old_adjacency = agent.a.clone()
        agent._act = first_legal
        env = AIMEnvironment(heldout_graph, budget=5, horizon=2)
        result = agent.run_episode(env)
        assert not torch.equal(old_adjacency, agent.a)
        assert agent.a[0, 1] == .5
        assert np.asarray(result["losses"], dtype=float).ndim == 1
        if cls is BudgetHRLAgent:
            assert [a["budget"] for a in result["actions"]] == [3, 0]
            observed = env.reset()
            assert np.array_equal(np.flatnonzero(agent._mask(observed)), [0, 1, 2, 3])
            observed["remaining_days"] = 1
            assert np.array_equal(np.flatnonzero(agent._mask(observed)), [3])
            observed["legal_mask"][:] = False
            assert np.array_equal(np.flatnonzero(agent._mask(observed)), [0])
