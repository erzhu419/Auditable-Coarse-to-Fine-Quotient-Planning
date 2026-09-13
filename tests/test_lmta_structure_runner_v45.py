"""Small numerical runner checks; no environment calls, rollouts, or training."""
import importlib.util
from pathlib import Path

import networkx as nx
import numpy as np
import torch
from torch.nn import functional as F

from acfqp.science.lmta_models_v43 import NodeQ, adjacency
from acfqp.science.lmta_structure_v45 import initial_features, mean_adjacency, weighted_adjacency


SPEC = importlib.util.spec_from_file_location('lmta_structure_runner_v45',
    Path(__file__).resolve().parents[1] / 'scripts/run_lmta_structure_v45.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def graph():
    result = nx.DiGraph()
    result.add_nodes_from(range(5))
    result.add_edges_from([(0, 1), (0, 2), (3, 2), (2, 3)])
    return result


def test_mean_float32_matches_published_adjacency_exactly():
    original = adjacency(graph(), 'cpu')
    rebuilt = mean_adjacency(graph(), dtype=torch.float32)
    assert original.dtype == rebuilt.dtype == torch.float32
    torch.testing.assert_close(rebuilt, original, rtol=0, atol=0)
    # The asymmetric orientation, degree-three denominator and isolated node
    # distinguish this from a transpose, symmetric normalization, or no self loop.
    assert rebuilt[0, 1] > 0 and rebuilt[1, 0] == 0
    assert rebuilt[0, 0] == torch.tensor(1. / 3, dtype=torch.float32)
    torch.testing.assert_close(rebuilt[4], torch.tensor([0., 0., 0., 0., 1.]), rtol=0, atol=0)


def test_conditional_batch_matches_each_full_goal_forward_in_float64():
    with torch.random.fork_rng(devices=[]), torch.inference_mode():
        torch.manual_seed(45)
        network = NodeQ(goal_size=128).double().eval()
        goals = F.normalize(torch.randn(4, 128, dtype=torch.float64), dim=-1)
        x = initial_features(5)
        x[1, :3] = torch.tensor([0., 1., 0.])
        x[2, :3] = torch.tensor([0., 0., 1.])
        a = weighted_adjacency(graph())
        batched, wait = runner.conditional_q(network, network.encoder.nodes(x, a), goals)
        separate = torch.stack([network(x, a, goal) for goal in goals])
        assert batched.dtype == torch.float64 and batched.shape == (4, 5)
        assert wait is None
        torch.testing.assert_close(batched, separate, rtol=1e-12, atol=1e-12)
        assert not torch.allclose(separate[0], separate[1])


def test_flat_wait_is_separate_and_ties_select_first_seed():
    with torch.random.fork_rng(devices=[]), torch.inference_mode():
        network = NodeQ(wait=True).double().eval()
        for parameter in network.head.parameters():
            parameter.zero_()
        for parameter in network.wait_head.parameters():
            parameter.zero_()
        network.head[-1].bias.fill_(2.)
        network.wait_head[-1].bias.fill_(9.)
        x, a = initial_features(5), mean_adjacency(graph())
        nodes = network.encoder.nodes(x, a)
        seeds, wait = runner.conditional_q(network, nodes)
        complete = network(x, a)
        torch.testing.assert_close(seeds[0], complete[:5], rtol=0, atol=0)
        assert wait == float(complete[5]) == 9.
        diagnostic = runner.describe_q(seeds[0], np.arange(5.), wait)
        assert diagnostic['q_range'] == diagnostic['scaled_row_range'] == 0.
        assert diagnostic['conditional_greedy_seed'] == 0
        assert diagnostic['flat_actual_choice_is_end_day'] is True
        assert int(complete.argmax()) == 5

        network.wait_head[-1].bias.fill_(2.)
        seeds, wait = runner.conditional_q(network, nodes)
        tied = runner.describe_q(seeds[0], np.arange(5.), wait)
        assert tied['q_range'] == 0.
        assert tied['flat_actual_choice_is_end_day'] is False
        assert tied['conditional_greedy_seed'] == int(network(x, a).argmax()) == 0
