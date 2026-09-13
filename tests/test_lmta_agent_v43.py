"""Small engineering checks; three search simulations are not a training setting."""
from copy import deepcopy

import networkx as nx
import numpy as np
import pytest
import torch

from acfqp.science.lmta_agent_v43 import LMTAAgent, WorldModel, mts_terms
from acfqp.science.lmta_aim_v43 import AIMEnvironment
from acfqp.science.lmta_models_v43 import NodeQ, adjacency, masked_max


@pytest.fixture(autouse=True)
def one_torch_thread():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def tiny_graph():
    graph = nx.DiGraph()
    graph.add_nodes_from(range(8))
    graph.add_edges_from([(0, 6), (1, 7)])
    return graph


def test_search_has_exact_simulation_count_and_no_environment_or_budget_calls(monkeypatch):
    env = AIMEnvironment(tiny_graph(), budget=4, horizon=3, seed=5)
    agent = LMTAAgent(env.graph, 4, 3, 7, simulations=3)
    observation = env.observation()
    rng_before, status_before = deepcopy(env.rng.bit_generator.state), env.statuses.copy()

    def forbidden(*args, **kwargs):
        raise AssertionError("Latent search accessed execution or the budget head")

    for name in ('select', 'finish_day', 'transition'):
        monkeypatch.setattr(env, name, forbidden)
    monkeypatch.setattr(agent.model.budget, 'forward', forbidden)
    # Deliberately omit remaining_budget and action masks: search needs neither.
    search_input = {key: observation[key] for key in ('features', 'remaining_days')}
    for training in (False, True):
        probabilities, value = agent.search(search_input, training)
        assert probabilities.shape == (32,)
        assert probabilities.sum() == pytest.approx(1.)
        assert np.all(probabilities >= 0.)
        np.testing.assert_allclose(probabilities * 3, np.rint(probabilities * 3))
        assert np.isfinite(value)
    assert agent.counts['mcts_simulations'] == 6
    assert agent.counts['root_searches'] == 2
    assert 1 <= agent.counts['latent_recurrent_calls'] <= 6
    assert not env.counters
    np.testing.assert_array_equal(env.statuses, status_before)
    assert env.rng.bit_generator.state == rng_before
    assert LMTAAgent.__init__.__defaults__[-1] == 150


def test_mts_tied_durations_contribute_one_and_formulas_have_gradients():
    micro_before = torch.zeros((2, 2), requires_grad=True)
    micro_after = torch.tensor([[.2, 0.], [.2, 0.]], requires_grad=True)
    macro_before = torch.zeros((2, 2), requires_grad=True)
    predicted = torch.tensor([[.4, 0.], [.4, 0.]], requires_grad=True)
    margins = torch.full((2,), .7, requires_grad=True)
    terms = mts_terms(micro_before, micro_after, macro_before, predicted,
                      margins, torch.tensor([2, 2]))
    np.testing.assert_allclose([float(t.detach()) for t in terms], [.01, .3, 1.], atol=1e-7)
    # Ties remain in the mean and contribute a constant, with zero order gradient.
    order_grad = torch.autograd.grad(terms[2], (predicted, margins), retain_graph=True)
    assert all(torch.count_nonzero(gradient) == 0 for gradient in order_grad)
    sum(terms).backward()
    for tensor in (micro_before, micro_after, macro_before, predicted, margins):
        assert tensor.grad is not None and torch.isfinite(tensor.grad).all()
        assert torch.count_nonzero(tensor.grad) > 0


def test_recurrent_reward_batch_shape_and_legal_low_level_values():
    torch.manual_seed(2)
    model = WorldModel(4)
    h = torch.nn.functional.normalize(torch.randn(3, 128), dim=-1)
    z = torch.tensor([0, 1, 2])
    predicted, reward = model.recurrent(h, z)
    assert predicted.shape == (3, 128) and reward.shape == (3,)
    torch.testing.assert_close(predicted.norm(dim=-1), torch.ones(3))
    assert model.recurrent(h[0], z[0])[1].ndim == 0
    reward.square().mean().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all()
               for p in model.reward.parameters())
    env = AIMEnvironment(tiny_graph(), budget=4, horizon=3)
    states = torch.tensor(np.stack([env.features()] * 3))
    q = NodeQ(goal_size=128)(states, adjacency(env.graph, 'cpu'), model.goal(z))
    assert q.shape == (3, 8)
    values = masked_max(torch.tensor([[100., 2.], [3., 4.]]),
                        np.array([[False, True], [False, False]]))
    torch.testing.assert_close(values, torch.tensor([2., 0.]))


def test_eight_tiny_episodes_update_high_low_and_budget_with_charged_counts():
    env = AIMEnvironment(tiny_graph(), budget=4, horizon=3, seed=13)
    agent = LMTAAgent(env.graph, 4, 3, 11, simulations=3)
    assert agent.low.encoder is agent.model.encoder
    modules = {'high': agent.model.encoder, 'low': agent.low,
               'budget': agent.model.budget, 'reward': agent.model.reward}
    before = {name: [p.detach().clone() for p in module.parameters()]
              for name, module in modules.items()}
    results = [agent.run_episode(env, training=True) for _ in range(8)]
    assert len(agent.games) == agent.episodes == 8
    assert all(result['primitive_selections'] == 4 for result in results)
    assert all(4 <= result['raw_return'] <= 6 for result in results)
    assert env.counters['train']['primitive_selections'] == 32
    assert env.counters['train']['day_transitions'] == 24
    assert len(agent.low_replay) == 32
    assert agent.counts['root_searches'] == 24
    assert agent.counts['mcts_simulations'] == 72
    assert agent.counts['LL_gradient_steps'] > 0
    assert agent.counts['LL_replay_samples'] == 8 * agent.counts['LL_gradient_steps']
    assert agent.counts['HL_gradient_steps'] == agent.counts['budget_gradient_steps'] == 1
    assert agent.counts['HL_replay_games'] == agent.counts['MTS_micro_replay_samples'] == 8
    assert 8 <= agent.counts['HL_replay_transitions'] <= 24
    losses = [loss for result in results for loss in result['losses']]
    assert losses and np.isfinite(losses).all()
    for name, module in modules.items():
        assert any(not torch.equal(old, new) for old, new in zip(before[name], module.parameters()))
        assert all(torch.isfinite(p).all() for p in module.parameters())
    assert any(p.grad is not None and torch.count_nonzero(p.grad) > 0
               for p in agent.model.budget.parameters())
    # Every macro-ending seed has zero LL bootstrap, including a nonterminal day.
    assert any(row[6] and np.any(row[5]) for row in agent.low_replay)
