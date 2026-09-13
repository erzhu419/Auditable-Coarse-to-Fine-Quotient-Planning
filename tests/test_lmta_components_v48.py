"""Small evaluation-only component checks with all new environment calls paid."""
from collections import Counter
from contextlib import ExitStack
import json
from unittest.mock import patch

import networkx as nx
import numpy as np
import pytest
import torch

from acfqp.science.lmta_aim_v43 import AIMEnvironment
from acfqp.science.lmta_components_v48 import ComponentPolicy
from acfqp.science.lmta_heuristics_v44 import AverageScoreAgent
from acfqp.science.lmta_weighted_v46 import BudgetHRLAgent, LMTAAgent


@pytest.fixture(scope='module', autouse=True)
def development_accounting():
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    counts = Counter()
    with ExitStack() as stack:
        for name in ('select', 'finish_day', 'transition', 'reset'):
            original = getattr(AIMEnvironment, name)

            def measured(env, *args, original=original, name=name, **kwargs):
                counts[name + '_calls'] += 1
                result = original(env, *args, **kwargs)
                if name == 'transition':
                    counts['propagation_draws'] += result[2]['propagation_draws']
                return result

            stack.enter_context(patch.object(AIMEnvironment, name, measured))
        yield counts
    torch.set_num_threads(old_threads)
    print('\nV48_DEVELOPMENT_ACCOUNTING=' + json.dumps({'counters': dict(counts),
        'scope': 'Small test episodes only. finish_day is the physical day sample; '
            'its nested transition is not another sample. reset includes constructor and '
            'episode resets. All observers forward original calls without drawing RNG.'}, sort_keys=True))


def graph(n=7, edges=None):
    result = nx.DiGraph()
    result.add_nodes_from(range(n))
    result.add_edges_from(edges if edges is not None else
        [(0, 3), (0, 4), (0, 5), (1, 0), (1, 6), (2, 6), (2, 4)])
    result.graph['replay_id'] = 48000 + n
    return result


def agent_for(method, graph, budget=5, horizon=3):
    if method == 'LMTA_RI':
        return LMTAAgent(graph, budget, horizon, seed=48001, simulations=3)
    return BudgetHRLAgent(graph, budget, horizon, seed=48001)


def networks(agent):
    names = ('model', 'low', 'target') if isinstance(agent, LMTAAgent) else ('ll', 'll_target', 'hl', 'hl_target')
    return {name: getattr(agent, name) for name in names}


def snapshot(agent):
    return ({name: {key: value.clone() for key, value in module.state_dict().items()}
        for name, module in networks(agent).items()},
        {name: len(getattr(agent, name)) for name in ('games', 'low_replay', 'll_replay', 'hl_replay') if hasattr(agent, name)},
        agent.episodes if isinstance(agent, LMTAAgent) else agent.training_episodes)


def assert_untrained(agent, before):
    for name, state in before[0].items():
        for key, value in state.items():
            torch.testing.assert_close(value, networks(agent)[name].state_dict()[key], rtol=0, atol=0)
    assert all(len(getattr(agent, name)) == length for name, length in before[1].items())
    assert (agent.episodes if isinstance(agent, LMTAAgent) else agent.training_episodes) == before[2]
    assert all(value == 0 for key, value in agent.counts.items() if 'gradient_steps' in key)
    assert all(parameter.grad is None for module in networks(agent).values() for parameter in module.parameters())
    optimizers = (agent.optim, agent.low_optim) if isinstance(agent, LMTAAgent) else (agent.ll_optimizer, agent.hl_optimizer)
    assert all(not optimizer.state for optimizer in optimizers)


def collect(policy, env):
    actions = []
    original = env.select

    def select(node, **kwargs):
        actions.append((env.day, int(node)))
        return original(node, **kwargs)

    with patch.object(env, 'select', select):
        result = policy.run_episode(env, training=False)
    return result, actions, env.statuses.copy()


@pytest.mark.parametrize('method', ['BUDGET_HRL', 'LMTA_RI'])
def test_all_learned_matches_original_evaluation_actions_daily_rewards_and_search(method):
    g = graph()
    original, crossed = agent_for(method, g), agent_for(method, g)
    before = snapshot(crossed)
    reference = collect(original, AIMEnvironment(g, budget=5, horizon=3, seed=48010))
    policy = ComponentPolicy(crossed, method, 'LEARNED', 'LEARNED')
    actual = collect(policy, AIMEnvironment(g, budget=5, horizon=3, seed=48010))
    assert actual[1] == reference[1]
    np.testing.assert_array_equal(actual[2], reference[2])
    assert actual[0]['raw_return'] == reference[0]['raw_return']
    assert actual[0]['day_history'] == reference[0]['day_history']
    assert crossed.rng.bit_generator.state == original.rng.bit_generator.state
    if method == 'BUDGET_HRL':
        assert actual[0]['actions'] == reference[0]['actions']
    else:
        for name in ('root_searches', 'mcts_simulations', 'latent_recurrent_calls'):
            assert crossed.counts[name] == original.counts[name]
    assert actual[0]['losses'] == [] and actual[0]['train_updates'] == actual[0]['replay_draws'] == 0
    assert_untrained(crossed, before)


@pytest.mark.parametrize('method', ['BUDGET_HRL', 'LMTA_RI'])
def test_full_replacement_matches_average_score_without_any_network_or_search(method):
    g = graph()
    agent = agent_for(method, g)
    policy = ComponentPolicy(agent, method, 'AVERAGE', 'SCORE')
    before = snapshot(agent)
    reference = collect(AverageScoreAgent(g, 5, 3, seed=0), AIMEnvironment(g, budget=5, horizon=3, seed=48011))

    def forbidden(*args):
        raise AssertionError('Full replacement called a learned network/search')

    handles = [module.register_forward_pre_hook(forbidden) for network in networks(agent).values()
        for module in network.modules()]
    try:
        with patch.object(agent, 'search' if method == 'LMTA_RI' else '_act', forbidden):
            actual = collect(policy, AIMEnvironment(g, budget=5, horizon=3, seed=48011))
    finally:
        for handle in handles:
            handle.remove()
    assert actual[0]['actions'] == reference[0]['actions']
    assert actual[1] == reference[1] and actual[1][:2] == [(0, 0), (0, 2)]
    assert actual[0]['raw_return'] == reference[0]['raw_return']
    np.testing.assert_array_equal(actual[2], reference[2])
    assert policy.counts['component_score_calls'] == actual[0]['primitive_selections']
    assert policy.counts.get('component_search_requests', 0) == policy.counts.get('component_budget_head_calls', 0) == 0
    assert_untrained(agent, before)


@pytest.mark.parametrize('budget_rule,selection_rule', [('AVERAGE', 'LEARNED'), ('LEARNED', 'SCORE')])
def test_mixed_lmta_recomputes_goal_from_current_state_and_handles_empty_capacity(budget_rule, selection_rule):
    g = graph(3, [(0, 1), (1, 2)])
    agent = agent_for('LMTA_RI', g, budget=4)
    with torch.no_grad():
        for parameter in agent.low.head.parameters():
            parameter.zero_()
        for parameter in agent.model.budget.parameters():
            parameter.zero_()
        agent.model.budget[-1].bias[2] = 1.
    before = snapshot(agent)
    env = AIMEnvironment(g, budget=4, horizon=3, seed=48012)
    original_search = agent.search
    searched, low_goals, budget_goals = [], [], []

    def search(observation, training):
        assert training is False
        np.testing.assert_array_equal(observation['features'], env.features())
        probabilities, value = original_search(observation, training)
        searched.append((env.day, observation['features'].copy(), int(probabilities.argmax()), value))
        return probabilities, value

    handles = [agent.low.register_forward_pre_hook(lambda _, args: low_goals.append((env.day, args[2].clone()))),
        agent.model.budget.register_forward_pre_hook(lambda _, args: budget_goals.append((env.day, args[0][-128:].clone())))]
    try:
        with patch.object(agent, 'search', search):
            result, actions, _ = collect(ComponentPolicy(agent, 'LMTA_RI', budget_rule, selection_rule), env)
    finally:
        for handle in handles:
            handle.remove()
    assert [row[0] for row in searched] == [0, 1, 2]
    assert not np.array_equal(searched[0][1], searched[1][1])
    assert not np.array_equal(searched[1][1], searched[2][1])
    assert [row['budget'] for row in result['actions']] == [2, 0, 0]
    assert [row['capacity'] for row in result['day_history']] == [3, 0, 0]
    assert result['day_history'][-1]['forced'] is True
    assert actions == [(0, 0), (0, 1)] and result['raw_return'] == 3.
    assert [row['z'] for row in result['day_history']] == [row[2] for row in searched]
    assert len(low_goals) == (2 if selection_rule == 'LEARNED' else 0)
    assert len(budget_goals) == (3 if budget_rule == 'LEARNED' else 0)
    for day, goal in low_goals + budget_goals:
        expected = agent.model.goal(torch.tensor(searched[day][2]))
        torch.testing.assert_close(goal, expected, rtol=0, atol=0)
    assert agent.counts['mcts_simulations'] == 9
    assert_untrained(agent, before)


def test_training_request_is_rejected_before_environment_calls(development_accounting):
    g = graph()
    agent = agent_for('BUDGET_HRL', g)
    env = AIMEnvironment(g, budget=5, horizon=3)
    before = dict(development_accounting)
    with pytest.raises(ValueError, match='only evaluates'):
        ComponentPolicy(agent, 'BUDGET_HRL', 'LEARNED', 'LEARNED').run_episode(env, training=True)
    assert dict(development_accounting) == before
