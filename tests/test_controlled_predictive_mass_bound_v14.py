"""Only an impossible goal term changes V13's incremental completion bounds."""

from collections import Counter
import math

import pytest

from acfqp.science import controlled_predictive_partial_v12 as partial
from acfqp.science.controlled_predictive_incremental_v13 import PlannerState
from acfqp.science.controlled_predictive_mass_bound_v14 import (
    MassBoundPlannerState, mass_bound_unknown_action_bounds,
)
from acfqp.science.controlled_predictive_quotient_v1 import Query


SINGLE = (0,) * 5 + (1,) + (0,) * 10
WON = (11,) + (0,) * 15
LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)


def board_with_mass(mass):
    ranks = tuple(rank for rank in range(1, 11) if mass & (1 << rank))
    return ranks + (0,) * (16 - len(ranks))


def values(cache):
    return cache.lower, cache.upper, cache.q_lower, cache.q_upper, cache.policy


@pytest.mark.parametrize("horizon", [1, 2, 3])
@pytest.mark.parametrize("offset", [-2, 0, 2])
def test_mass_boundary_is_strict_and_preserves_all_other_bound_terms(horizon, offset):
    mass = 2048 - 4 * horizon + offset
    key = (horizon, board_with_mass(mass))
    observed = partial.profile(key, Counter())
    assert observed.status == "ACTIVE" and observed.mass == mass
    query = Query(1.25, 2.5, 3.75)
    for action in observed.legal_actions:
        old = partial.unknown_action_bounds(key, observed, action, query)
        new = mass_bound_unknown_action_bounds(key, observed, action, query)
        expected_query = Query(query.reward_weight, query.failure_penalty, 0) if offset < 0 else query
        assert new == partial.unknown_action_bounds(key, observed, action, expected_query)
        assert new[0] == old[0]
    state = MassBoundPlannerState(key, {"q": query})
    cache = state.solve("q")
    assert all(cache.q_upper[key, action] == mass_bound_unknown_action_bounds(key, observed, action, query)[1]
               for action in observed.legal_actions)
    assert state.work_counts["mass_bound_unknown_action_checks"] == len(observed.legal_actions)
    assert state.work_counts["mass_bound_nonzero_goal_terms_removed"] == (
        len(observed.legal_actions) if offset < 0 else 0
    )


@pytest.mark.parametrize("key,expected", [((0, WON), 3), ((3, WON), 3),
                                         ((0, LOST), -5), ((3, LOST), -5), ((0, SINGLE), 0)])
def test_terminal_precedence_bypasses_the_active_mass_bound(key, expected):
    state = MassBoundPlannerState(key, {"q": Query(1, 5, 3)})
    cache = state.solve("q")
    assert cache.lower[key] == cache.upper[key] == expected
    assert cache.policy == cache.q_lower == cache.q_upper == {}
    assert state.next_row() is None
    assert state.work_counts["mass_bound_unknown_action_checks"] == 0


class LocalRows:
    """Deterministic fixture rows; the planner cannot inspect a full closure."""
    def __init__(self):
        self.requests = []

    @property
    def closure(self):
        raise AssertionError("unknown closure access")

    def sample(self, key, action):
        self.requests.append((key, action))
        return ((1.0, (key[0] - 1, key[1]), 0.0),)


@pytest.mark.parametrize("mode", ["bfs", "query_interval"])
def test_zero_goal_preserves_exact_caches_rows_round_robin_and_frozen_policies(mode, monkeypatch):
    monkeypatch.setattr(partial, "_step_v1", lambda *args: pytest.fail("unknown stochastic support accessed"))
    queries = {"z_first": Query(1, 1, 0), "a_second": Query(2, .1, 0)}
    old = PlannerState((3, SINGLE), queries, mode=mode)
    new = MassBoundPlannerState((3, SINGLE), queries, mode=mode)
    providers = [LocalRows(), LocalRows()]
    for budget in (0, 1, 4, 8):
        for state, provider in zip((old, new), providers):
            while len(state.rows) < budget and state.sample_next(provider):
                pass
        assert old.rows == new.rows
        assert old.row_order == new.row_order
        assert old.cursor == new.cursor
        assert old.stop_reason == new.stop_reason
        for name in queries:
            assert values(old.solve(name)) == values(new.solve(name))
        old_frozen, old_intervals = old.freeze()
        new_frozen, new_intervals = new.freeze()
        assert old_frozen.policies == new_frozen.policies
        assert old_intervals == new_intervals
    assert providers[0].requests == providers[1].requests
    assert new.work_counts["mass_bound_nonzero_goal_terms_removed"] == 0


def test_new_rows_propagate_candidate_bounds_and_clones_keep_independent_candidate_caches(monkeypatch):
    monkeypatch.setattr(partial, "_step_v1", lambda *args: pytest.fail("unknown stochastic support accessed"))
    root, child, leaf, cutoff = ((h, SINGLE) for h in (3, 2, 1, 0))
    off_path = (1, board_with_mass(4))
    queries = {"q": Query(1, 1, 3), "later": Query(2, .5, 2)}
    state = MassBoundPlannerState(root, queries)
    state.observe_state(off_path)
    for key, successor in ((root, child), (child, leaf)):
        for action in state.profiles[key].legal_actions:
            state.observe_row(key, action, ((1., successor, 0.),))
    cache = state.solve("q")
    assert cache.lower[root] == -1 and cache.upper[root] == 0
    assert all(cache.q_upper[leaf, action] == 0 for action in state.profiles[leaf].legal_actions)
    branch = state.clone()
    sibling = state.clone()
    assert isinstance(branch, MassBoundPlannerState)
    assert branch.profiles[root] is state.profiles[root]
    assert branch.rows[root, "DOWN"] is state.rows[root, "DOWN"]
    branch.observe_row(leaf, "DOWN", ((1., cutoff, 0.),))
    assert branch.caches["q"].dirty == {root, child, leaf, cutoff}
    visits = branch.work_counts["interval_state_visits"]
    updated = branch.solve("q")
    assert branch.work_counts["interval_state_visits"] - visits == 4
    assert updated.lower[root] == updated.upper[root] == 0
    assert cutoff not in state.profiles and cutoff not in sibling.profiles
    assert state.caches["q"].lower[root] == sibling.caches["q"].lower[root] == -1
    assert not state.caches["q"].dirty and not sibling.caches["q"].dirty
    assert branch.caches["q"].lower is not state.caches["q"].lower
    fresh = MassBoundPlannerState(root, queries)
    fresh.observe_state(off_path)
    for pair in branch.row_order:
        fresh.observe_row(*pair, branch.rows[pair])
    for name in queries:
        assert values(branch.solve(name)) == values(fresh.solve(name))
    assert branch.work_counts["mass_bound_nonzero_goal_terms_removed"] > 0


def test_sampled_row_fsum_remains_exact_and_bounds_only_unobserved_actions():
    root = (2, SINGLE)
    successors = [(1, board_with_mass(mass)) for mass in (2, 4, 8)]
    row = tuple(zip((13 / 256, 37 / 256, 206 / 256), successors, (.123456789, 1e-17, .00390625)))
    state = MassBoundPlannerState(root, {"q": Query(1.25, .5, 2)})
    state.solve("q")
    state.observe_row(root, "DOWN", row)
    cache = state.solve("q")
    assert cache.q_lower[root, "DOWN"] == math.fsum(
        weight * (1.25 * reward + cache.lower[successor]) for weight, successor, reward in row
    )
    assert cache.q_upper[root, "DOWN"] == math.fsum(
        weight * (1.25 * reward + cache.upper[successor]) for weight, successor, reward in row
    )
    assert all(cache.upper[successor] == 0 for successor in successors)


def test_reachable_goal_keeps_its_bonus_and_observed_won_successor_value():
    root = (1, (10, 10) + (0,) * 14)
    query = Query(1, 5, 3)
    state = MassBoundPlannerState(root, {"q": query})
    cache = state.solve("q")
    assert cache.q_upper[root, "LEFT"] == 4
    support = partial._step_v1(
        partial.Swipe2048State(root[1], partial.Swipe2048Status.ACTIVE), partial.Swipe2048Action.LEFT,
    )
    assert all(outcome.next_state.status == partial.Swipe2048Status.WON for outcome in support)
    row = tuple((float(outcome.probability), (0, outcome.next_state.board), outcome.merge_score / 2048)
                for outcome in support)
    true_value = math.fsum(weight * (reward + query.goal_bonus) for weight, _, reward in row)
    assert true_value == 4 and true_value <= cache.q_upper[root, "LEFT"]
    state.observe_row(root, "LEFT", row)
    cache = state.solve("q")
    assert cache.q_lower[root, "LEFT"] == cache.q_upper[root, "LEFT"] == true_value
    assert cache.lower[root] == cache.upper[root] == true_value
    assert state.work_counts["mass_bound_nonzero_goal_terms_removed"] == 0


def test_candidate_explicitly_rejects_unimplemented_full_recompute_mode():
    with pytest.raises(ValueError, match="only incremental"):
        MassBoundPlannerState((1, SINGLE), {"q": Query(1, 1, 1)}, update_mode="full_recompute")
