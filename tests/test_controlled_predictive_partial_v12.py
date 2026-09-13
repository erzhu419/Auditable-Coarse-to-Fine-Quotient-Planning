"""Partial planning never requires the complete target closure."""

from collections import Counter
from fractions import Fraction

import pytest

from acfqp.science import controlled_predictive_partial_v12 as partial
from acfqp.science.controlled_predictive_quotient_v1 import Query


SINGLE = (0,) * 5 + (1,) + (0,) * 10
LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
WON = (11,) + (0,) * 15


class LocalRows:
    """Minimal cooperating provider; unchanged boards make a small layered DAG."""
    def __init__(self):
        self.work_counts = Counter()
        self.provider_seconds = 0.0
        self.requests = []

    @property
    def closure(self):
        raise AssertionError("planner must never inspect a closure")

    def sample(self, key, action):
        assert (key, action) not in self.requests
        self.requests.append((key, action))
        self.work_counts.update(row_requests=1, physical_draws=256)
        return ((1.0, (key[0] - 1, key[1]), 0.0),)


def test_row_stream_is_order_independent_and_exact_support_stays_inside_requested_provider(monkeypatch):
    actual_step = partial._step_v1
    requested = []

    def tracked(state, action):
        requested.append((state.board, action.value))
        return actual_step(state, action)

    monkeypatch.setattr(partial, "_step_v1", tracked)
    key = (2, SINGLE)
    first = partial.RowSampleProvider(832101)
    down, left = first.sample(key, "DOWN"), first.sample(key, "LEFT")
    second = partial.RowSampleProvider(832101)
    assert second.sample(key, "LEFT") == left
    assert second.sample(key, "DOWN") == down
    assert requested == [(SINGLE, "DOWN"), (SINGLE, "LEFT"), (SINGLE, "LEFT"), (SINGLE, "DOWN")]
    assert first.work_counts["row_requests"] == first.work_counts["exact_transition_row_calls"] == 2
    assert first.work_counts["physical_draws"] == 512
    assert first.provider_seconds > 0
    assert not hasattr(first, "support")
    for row in (down, left):
        assert sum(Fraction(weight) for weight, _, _ in row) == 1
        assert all(weight > 0 and (weight * 256).is_integer() and successor[0] == 1
                   for weight, successor, _ in row)
    radix = 12 ** 16
    expected = 832101 * radix * 16 + (2 * 4 + partial.ACTIONS.index("LEFT")) * radix + 12 ** 5
    assert partial.row_seed(832101, key, "LEFT") == expected


@pytest.mark.parametrize("board,horizon,status,swipes", [
    (WON, 0, "WON", 0), (WON, 3, "WON", 0),
    (LOST, 0, "LOST", 4), (LOST, 3, "LOST", 4), (SINGLE, 0, "CUTOFF", 1),
])
def test_terminal_profile_precedence_and_costs(board, horizon, status, swipes):
    work = Counter()
    observed = partial.profile((horizon, board), work)
    assert observed.status == status
    assert observed.legal_actions == observed.immediate_rewards == ()
    assert work["deterministic_swipe_calls"] == swipes
    assert work["states_profiled"] == 1
    query = Query(1, 5, 3)
    result = partial.run_partial((horizon, board), LocalRows(), {"q": query}, budgets=(0,))
    if status != "CUTOFF" or horizon == 0:
        expected = {"WON": 3, "LOST": -5, "CUTOFF": 0}[status]
        assert result[0].root_intervals["q"] == partial.RootInterval(expected, expected, None)


def test_unknown_action_bounds_include_immediate_reward_and_safe_remaining_mass():
    board = (1,) * 16
    key = (3, board)
    observed = partial.profile(key, Counter())
    assert observed.mass == 32
    assert observed.reward("LEFT") == 32 / 2048
    query = Query(2, 5, 3)
    lower, upper = partial.unknown_action_bounds(key, observed, "LEFT", query)
    assert lower == 2 * (32 / 2048) - 5
    assert upper == 2 * ((32 + 2 * 36 + 4) / 2048) + 3
    horizon_one = partial.profile((1, board), Counter())
    assert partial.unknown_action_bounds((1, board), horizon_one, "LEFT", query)[1] == 2 * 32 / 2048 + 3


def test_budget_prefixes_are_frozen_and_bfs_samples_only_discovered_rows(monkeypatch):
    monkeypatch.setattr(partial, "_step_v1", lambda *args: pytest.fail("planner cannot enumerate stochastic support"))
    provider = LocalRows()
    queries = {f"q{index}": Query(1, index / 10, 0) for index in range(10)}
    checkpoints = partial.run_partial((3, SINGLE), provider, queries, budgets=(0, 1, 3, 8, 32), mode="bfs")
    assert [len(c.known_rows) for c in checkpoints] == [0, 1, 3, 8, 12]
    assert [c.provider_counts.get("physical_draws", 0) for c in checkpoints] == [0, 256, 768, 2048, 3072]
    assert provider.requests[:4] == [((3, SINGLE), action) for action in partial.ACTIONS]
    assert checkpoints[-1].stop_reason == "NO_UNOBSERVED_ROWS"
    assert len(checkpoints[0].profiles) == 1
    assert len(checkpoints[1].profiles) == 2
    assert all(len(c.known_rows) <= c.budget for c in checkpoints)
    assert all(len(c.frozen_policy.policies) == 10 for c in checkpoints)
    assert all(c.provider_seconds <= c.elapsed_seconds and 0 <= c.checkpoint_copy_seconds <= c.elapsed_seconds
               for c in checkpoints)
    assert checkpoints[0].known_rows is not checkpoints[-1].known_rows
    assert checkpoints[0].frozen_policy.policies is not checkpoints[-1].frozen_policy.policies
    assert checkpoints[-1].work_counts["rows_acquired"] == 12
    assert checkpoints[-1].work_counts["checkpoints_created"] == 5


def test_query_interval_stops_when_root_bounds_close_without_exhausting_rows():
    provider = LocalRows()
    checkpoints = partial.run_partial((1, SINGLE), provider, {"risk": Query(1, 1, 0)}, budgets=(8, 32, 128))
    assert [len(c.known_rows) for c in checkpoints] == [1, 1, 1]
    assert provider.requests == [((1, SINGLE), "DOWN")]
    assert all(c.stop_reason == "ALL_QUERIES_CONVERGED" for c in checkpoints)
    assert checkpoints[0].root_intervals["risk"] == partial.RootInterval(0, 0, "DOWN")
    assert checkpoints[0].frozen_policy.action((1, SINGLE), "risk") == "DOWN"
    assert checkpoints[0].frozen_policy.work_counts["fallback_calls"] == 0
    assert checkpoints[-1].frozen_policy.work_counts["policy_action_calls"] == 0


class OrderedPrior:
    def __init__(self):
        self.seen = []

    def __call__(self, key, query):
        self.seen.append((key, query.failure_penalty))
        return {"RIGHT" if query.failure_penalty == 1 else "LEFT": 1000}

    def diagnostics(self):
        return {"calls": len(self.seen)}


def test_prior_only_breaks_search_ties_and_queries_keep_declared_insertion_order():
    prior = OrderedPrior()
    provider = LocalRows()
    queries = {"z_first": Query(1, 1, 0), "a_second": Query(1, 2, 0)}
    checkpoints = partial.run_partial((2, SINGLE), provider, queries, budgets=(0, 1, 2),
                                      mode="source_priority", prior=prior)
    assert provider.requests[:2] == [((2, SINGLE), "RIGHT"), ((2, SINGLE), "LEFT")]
    assert [penalty for _, penalty in prior.seen] == [1, 2]
    assert [c.prior_diagnostics["calls"] for c in checkpoints] == [0, 1, 2]
    # Search-priority values never replace execution values or unknown-row bounds.
    for checkpoint in checkpoints:
        assert checkpoint.root_intervals["z_first"].lower == -1
        assert checkpoint.root_intervals["z_first"].action == "DOWN"
        assert checkpoint.frozen_policy.action((2, SINGLE), "z_first") == "DOWN"
        assert ((2, SINGLE), "DOWN") not in checkpoint.known_rows
    assert checkpoints[-1].prior_seconds > 0


def test_unseen_state_fallback_is_greedy_independent_and_costed_without_observation_changes():
    checkpoint = partial.run_partial((1, SINGLE), LocalRows(), {"q": Query(1, 1, 0)}, budgets=(0,))[0]
    unknown = (2, (1, 1) + (0,) * 14)
    known_count = len(checkpoint.profiles)
    policy = checkpoint.frozen_policy
    assert policy.action(unknown, "q") == "LEFT"
    assert policy.action(unknown, "q") == "LEFT"
    assert len(checkpoint.profiles) == known_count
    assert unknown not in policy.policies["q"]
    assert policy.work_counts["fallback_calls"] == 2
    assert policy.work_counts["deterministic_swipe_calls"] == 8
    assert policy.fallback_seconds > 0
    assert not checkpoint.known_rows
    with pytest.raises(KeyError):
        policy.action(unknown, "undeclared_query")


def test_sampled_goal_row_propagates_exact_terminal_value_inside_unknown_bounds():
    board = (10, 10) + (0,) * 14
    root = (1, board)
    provider = partial.RowSampleProvider(7)
    queries = {"q": Query(1, 5, 3)}
    checkpoints = partial.run_partial(root, provider, queries, budgets=(0, 8), mode="bfs")
    before, after = checkpoints[0].root_intervals["q"], checkpoints[-1].root_intervals["q"]
    assert before.lower <= after.lower == after.upper <= before.upper
    assert after.lower == 4
    assert after.action == "LEFT"
    assert all(successor in checkpoints[-1].profiles for row in checkpoints[-1].known_rows.values()
               for _, successor, _ in row)
