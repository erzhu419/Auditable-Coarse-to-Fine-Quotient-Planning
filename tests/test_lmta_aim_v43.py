"""AIM day boundaries, passed-state simulations, masks, and physical counters."""
from copy import deepcopy
from itertools import product

import networkx as nx
import numpy as np
import pytest

from acfqp.science.lmta_aim_v43 import AIMEnvironment, generate_graph


class Draws:
    def __init__(self, values):
        self.values = iter(values)
        self.calls = 0

    def random(self):
        self.calls += 1
        return next(self.values)


def graph(n, edges):
    result = nx.DiGraph()
    result.add_nodes_from(range(n))
    result.add_edges_from(edges)
    return result


def test_seed_reward_and_one_daily_propagation_keep_both_old_and_seeded_active_sources():
    env = AIMEnvironment(graph(5, [(0, 1), (1, 2), (3, 4)]), budget=2, horizon=2)
    rng = Draws([.99, .99, .99])
    env.rng = rng
    obs, reward, done = env.select(0)
    assert reward == 1 and not done and rng.calls == 0
    assert obs["daily_selected"] == (0,)
    np.testing.assert_array_equal(env.day_start_status, [0, 0, 0, 0, 0])
    obs, reward, done, info = env.finish_day()
    assert reward == 1 and not done and info["day_reward"] == 2
    np.testing.assert_array_equal(obs["statuses"], [2, 1, 0, 0, 0])
    assert env.day == 1 and obs["remaining_days"] == 1
    env.select(3)
    obs, reward, done, info = env.finish_day()
    np.testing.assert_array_equal(obs["statuses"], [2, 2, 1, 2, 1])
    assert done and reward == 2 and info["day_reward"] == 3
    assert env.counters == {"train": {"primitive_selections": 2, "day_transitions": 2, "propagation_draws": 3}}
    assert obs["features"].shape == (5, 5) and obs["features"].dtype == np.float32
    np.testing.assert_array_equal(obs["features"][:, 3:], 0.)


def test_multiple_parents_draw_each_eligible_edge_and_count_target_only_once():
    env = AIMEnvironment(graph(4, [(0, 2), (1, 2), (2, 3)]), budget=2, horizon=2)
    assert env.graph[0][2]["weight"] == env.graph[1][2]["weight"] == .5
    activations = []
    counters = {}
    for values in product([.25, .75], repeat=2):
        rng = Draws(values)
        next_state, reward, info = env.transition(np.zeros(4, dtype=np.int8), [0, 1], rng, counters=counters)
        assert rng.calls == info["propagation_draws"] == 2
        assert next_state[0] == next_state[1] == 2
        assert next_state[3] == 0  # Newly activated target cannot spread this day.
        assert reward == 2 + int(next_state[2] == 1)
        activations.append(next_state[2] == 1)
    assert sum(activations) == 3  # Exact two-parent IC probability is 1-(1-.5)^2.
    assert counters == {"oracle_day_transitions": 4, "oracle_seed_exposures": 8, "oracle_propagation_draws": 8}
    assert env.counters == {}


def test_sorted_edge_order_ignores_graph_insertion_order():
    env = AIMEnvironment(graph(4, [(0, 2), (0, 1), (3, 2), (3, 1)]))
    rng = Draws([.25, .75])
    next_state, reward, info = env.transition(np.zeros(4, dtype=np.int8), [0], rng)
    np.testing.assert_array_equal(next_state, [2, 1, 0, 0])
    assert reward == 2 and info["propagation_draws"] == 2


def test_zero_allocation_still_advances_days_and_reset_preserves_phase_totals():
    env = AIMEnvironment(graph(2, [(0, 1)]), budget=0, horizon=2, seed=4)
    for day in range(2):
        obs, reward, done, info = env.finish_day()
        assert reward == 0 and info["propagation_draws"] == 0
        assert obs["remaining_days"] == 1 - day
        assert done == (day == 1)
    with pytest.raises(ValueError, match="already ended"):
        env.finish_day()
    env.reset(seed=5)
    env.finish_day(phase="eval")
    assert env.counters == {
        "train": {"primitive_selections": 0, "day_transitions": 2, "propagation_draws": 0},
        "eval": {"primitive_selections": 0, "day_transitions": 1, "propagation_draws": 0},
    }
    assert not env.legal_mask().any()
    assert np.isfinite(env.features()).all()


def test_counterfactual_uses_passed_state_without_changing_episode_or_environment_rng():
    env = AIMEnvironment(graph(3, [(0, 1), (1, 2)]), seed=12)
    passed = np.zeros(3, dtype=np.int8)
    env.statuses[:] = 2  # Deliberately unlike the state being simulated.
    env.day = 3
    env.remaining_budget = 2
    before_rng = deepcopy(env.rng.bit_generator.state)
    next_state, reward, info = env.transition(passed, [0], np.random.default_rng(10))
    np.testing.assert_array_equal(next_state, [2, 1, 0])
    np.testing.assert_array_equal(passed, [0, 0, 0])
    np.testing.assert_array_equal(env.statuses, [2, 2, 2])
    assert reward == 2 and info["propagation_draws"] == 1
    assert env.day == 3 and env.remaining_budget == 2 and env.counters == {}
    assert env.rng.bit_generator.state == before_rng


def test_masks_for_active_removed_selected_nodes_and_remaining_budget():
    env = AIMEnvironment(graph(3, [(0, 1)]), budget=2, horizon=3)
    env.select(0)
    assert env.legal_mask().tolist() == [False, True, True]
    with pytest.raises(ValueError, match="Illegal"):
        env.select(0)
    env.finish_day()
    assert env.legal_mask().tolist() == [False, False, True]
    for node in [0, 1]:
        with pytest.raises(ValueError, match="Illegal"):
            env.select(node)
    env.select(2)
    assert not env.legal_mask().any()
    assert env.counters["train"]["primitive_selections"] == 2
    with pytest.raises(ValueError, match="distinct"):
        env.transition(np.zeros(3, dtype=np.int8), [0, 0], Draws([]))
    with pytest.raises(ValueError, match="inactive"):
        env.transition(np.asarray([2, 0, 0]), [0], Draws([]))


def test_graph_generation_is_seeded_and_environment_owns_frozen_graph_copy():
    original = generate_graph(8, 43, p=.4)
    assert list(original.edges()) == list(generate_graph(8, 43, p=.4).edges())
    env = AIMEnvironment(original)
    assert nx.is_frozen(env.graph)
    assert "weight" not in next(iter(original.edges(data=True)))[2]
    assert all(data["weight"] == 1. / original.in_degree(target) for _, target, data in env.graph.edges(data=True))
