"""Small development calls only; these are excluded from the ER500 pilot."""
import importlib.util
import io
import json
from pathlib import Path
import random

import networkx as nx
import numpy as np
import torch


SPEC = importlib.util.spec_from_file_location('lmta_sample_v42',
    Path(__file__).resolve().parents[1] / 'scripts/run_lmta_sample_v42.py')
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)
Agent, Env = pilot.load_reference()


def assert_identical(left, right):
    if isinstance(left, np.ndarray):
        np.testing.assert_array_equal(left, right)
    elif isinstance(left, (list, tuple)):
        assert len(left) == len(right)
        for a, b in zip(left, right):
            assert_identical(a, b)
    else:
        assert left == right


def rng_state():
    return (random.getstate(), np.random.get_state(), torch.get_rng_state(),
        torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [])


def make_agent():
    pilot.seed_all(7)
    graph = nx.DiGraph([(0, 1), (1, 2), (2, 3), (3, 0)])
    return Agent(Env(graph, budget=2, T=3))


def exercise(agent):
    episode = agent.run_episode(budget_policy='average', seeding_policy='agent',
        epsilon=.3, beam_search=False)
    estimate = agent.run_simulation(episode[0][0], [0], iter_num=3)
    # No gradients or updates: forwarding is verified without a training epoch.
    agent.optimizer.step()
    agent.optimizer_sub.step()
    return episode, estimate, agent.env.state.copy(), rng_state()


def test_observer_preserves_original_results_actions_and_all_rng_states():
    baseline = exercise(make_agent())
    agent = make_agent()
    original_uniform = random.uniform
    writer = io.StringIO()
    with pilot.Observer(agent, writer) as observer:
        measured = exercise(agent)
    assert_identical(baseline[:3], measured[:3])
    assert_identical(baseline[3][:2], measured[3][:2])
    assert torch.equal(baseline[3][2], measured[3][2])
    assert len(baseline[3][3]) == len(measured[3][3])
    for a, b in zip(baseline[3][3], measured[3][3]):
        assert torch.equal(a, b)
    assert random.uniform is original_uniform
    assert 'step' not in agent.env.__dict__
    assert 'run_episode' not in agent.__dict__
    assert 'run_simulation' not in agent.__dict__

    report = observer.report()
    trajectory = report['phases']['training_trajectory']
    simulation = report['phases']['reward_estimation']
    assert trajectory['env_step_calls'] == 3
    assert trajectory['empty_action_calls'] == 1
    assert trajectory['requested_seed_exposures'] == 2
    assert simulation['env_step_calls'] == 3
    assert simulation['requested_seed_exposures'] == 3
    assert simulation['run_simulation_calls'] == 1
    assert simulation['requested_simulation_iterations'] == 3
    assert simulation['original_discounted_score'] is None
    assert trajectory['original_discounted_score'] == baseline[0][-1]
    assert report['optimizer']['HL_step_calls'] == 1
    assert report['optimizer']['LL_step_calls'] == 1
    events = [json.loads(line) for line in writer.getvalue().splitlines()]
    assert len(events) == report['total_env_step_calls'] == 6
    assert report['total_requested_seed_exposures'] == 5
    for phase, counts in report['phases'].items():
        selected = [event for event in events if event['phase'] == phase]
        assert counts['random_uniform_calls'] == sum(event['random_uniform_calls'] for event in selected)
        assert counts['random_uniform_calls'] == sum(counts.get('random_uniform_' + kind + '_calls', 0)
            for kind in ('seed_activation', 'propagation', 'other'))
        assert counts['invalid_seed_requests'] == sum(len(event['invalid_seed_requests']) for event in selected)
        assert counts['raw_undiscounted_reward_sum'] == sum(event['reward'] for event in selected)


def test_internal_state_witness_preserves_bug_and_restores_python_rng():
    before = random.getstate()
    witness = pilot.state_argument_witness(Env)
    assert random.getstate() == before
    assert witness['outcome_depends_on_internal_state']
    assert witness['development_env_step_calls'] == 2
    assert witness['development_random_uniform_calls'] == 3
    normal, removed = witness['outcomes']
    assert normal['passed_state'] == removed['passed_state']
    assert normal['reward'] == 2 and removed['reward'] == 1
    assert normal['next_state'][1] == [0, 1, 0]
    assert removed['next_state'][1] == [1, 0, 0]


def test_passed_state_invalid_requests_are_counted_without_filtering():
    agent = make_agent()
    passed = agent.env.state.copy()
    agent.env.set_state_index(passed, [0], 2)
    writer = io.StringIO()
    with pilot.Observer(agent, writer) as observer:
        agent.run_simulation(passed, [0, 0], iter_num=2)
    counts = observer.report()['phases']['reward_estimation']
    assert counts['env_step_calls'] == 2
    assert counts['requested_seed_exposures'] == 4
    assert counts['invalid_seed_requests'] == 4
    assert counts['duplicate_seed_requests'] == 2
    assert counts['passed_state_differs_from_internal_calls'] == 2
    assert counts['random_uniform_seed_activation_calls'] == 4
    assert all(json.loads(line)['action'] == [0, 0] for line in writer.getvalue().splitlines())
