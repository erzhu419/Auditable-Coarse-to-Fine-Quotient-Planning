"""Evaluation checkpoints must not change the next training update."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import networkx as nx
import numpy as np
import torch

from acfqp.science.lmta_aim_v43 import AIMEnvironment
from acfqp.science.lmta_agent_v44 import LMTAAgent

spec = importlib.util.spec_from_file_location('v44_runner', Path(__file__).resolve().parents[1] / 'scripts/run_lmta_learnability_v44.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_evaluation_does_not_steer_next_training_episode():
    torch.set_num_threads(1)
    a = nx.DiGraph([(0, 1), (1, 2), (2, 3)])
    b = nx.DiGraph([(0, 3), (3, 2), (2, 1)])
    a.graph['replay_id'], b.graph['replay_id'] = 44, 45
    agent = LMTAAgent(a, 2, 2, 77, simulations=3)
    reference = LMTAAgent(a, 2, 2, 77, simulations=3)
    for learner in (agent, reference):
        learner.run_episode(AIMEnvironment(a, budget=2, horizon=2, seed=1), training=True)
    random_state = deepcopy(agent.rng.bit_generator.state)
    torch_state = torch.get_rng_state()
    model_state = {k: v.detach().clone() for k, v in agent.model.state_dict().items()}
    replay_lengths = len(agent.games), len(agent.low_replay)
    with runner.isolated_evaluation(agent):
        agent.run_episode(AIMEnvironment(b, budget=2, horizon=2, seed=2), training=False)
        torch.rand(3)
    assert agent.rng.bit_generator.state == random_state
    assert torch.equal(torch.get_rng_state(), torch_state)
    assert agent.graph_id == 44
    assert agent.episodes == 1
    assert (len(agent.games), len(agent.low_replay)) == replay_lengths
    for key, value in agent.model.state_dict().items():
        assert torch.equal(value, model_state[key])
    got = agent.run_episode(AIMEnvironment(a, budget=2, horizon=2, seed=3), training=True)
    expected = reference.run_episode(AIMEnvironment(a, budget=2, horizon=2, seed=3), training=True)
    assert got['raw_return'] == expected['raw_return']
    np.testing.assert_allclose(got['losses'], expected['losses'], atol=1e-7, rtol=0)
    assert agent.rng.bit_generator.state == reference.rng.bit_generator.state
    for key, value in agent.model.state_dict().items():
        torch.testing.assert_close(value, reference.model.state_dict()[key], atol=1e-7, rtol=0)
