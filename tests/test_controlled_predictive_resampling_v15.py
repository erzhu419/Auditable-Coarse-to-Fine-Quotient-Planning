"""Cumulative batches, V14 cache updates, and separate heuristic selection."""

from collections import Counter
import math

import pytest

from acfqp.science import controlled_predictive_incremental_v13 as incremental
from acfqp.science import controlled_predictive_partial_v12 as partial
from acfqp.science import controlled_predictive_resampling_v15 as resampling
from acfqp.science.controlled_predictive_mass_bound_v14 import MassBoundPlannerState
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_resampling_v15 import ResamplingPlannerState


SINGLE = (0,) * 5 + (1,) + (0,) * 10
DOUBLE = (0,) * 5 + (2,) + (0,) * 10
QUERIES = {"q": Query(1, 5, 0), "goal": Query(1, 5, 3)}


def cache_values(cache):
    return cache.lower, cache.upper, cache.q_lower, cache.q_upper, cache.policy


def make_warm():
    key = (1, SINGLE)
    warm = MassBoundPlannerState(key, QUERIES)
    warm.observe_row(key, "RIGHT", ((1., (0, SINGLE), 0.),))
    warm.freeze()
    return warm


def test_warm_conversion_preserves_v14_state_and_deeply_isolates_counts():
    warm = make_warm()
    frozen_before, intervals_before = warm.freeze()
    counts_before = warm.work_counts.copy()
    state = ResamplingPlannerState.from_warm(warm)
    assert isinstance(state, ResamplingPlannerState)
    assert state.rows == warm.rows and state.row_order == warm.row_order
    assert state.profiles == warm.profiles and state.cursor == warm.cursor
    assert state.stop_reason == warm.stop_reason
    assert state.spent_batches == len(state.rows) == 1
    assert state.batch_counts == {(state.root, "RIGHT"): 1}
    assert state.outcome_counts[state.root, "RIGHT"] == Counter({((0, SINGLE), 0.): 256})
    for name in QUERIES:
        assert cache_values(state.caches[name]) == cache_values(warm.caches[name])
        assert state.caches[name].lower is not warm.caches[name].lower
    assert state.rows[state.root, "RIGHT"] is warm.rows[warm.root, "RIGHT"]
    assert state.profiles[state.root] is warm.profiles[warm.root]
    assert state.conversion_seconds > 0
    assert state.engine_seconds == warm.engine_seconds + state.conversion_seconds
    assert warm.work_counts == counts_before
    frozen_after, intervals_after = warm.freeze()
    assert frozen_before.policies == frozen_after.policies and intervals_before == intervals_after


def test_three_batches_keep_integer_counts_and_do_not_drop_old_draws():
    root = (2, SINGLE)
    a, b = (1, SINGLE), (1, DOUBLE)
    state = ResamplingPlannerState(root, QUERIES)
    state.observe_batch(root, "DOWN", ((.5, a, 0.), (.5, b, 0.)))
    state.observe_batch(root, "DOWN", ((1., a, 0.),))
    state.observe_batch(root, "DOWN", ((1 / 256, a, 0.), (255 / 256, b, 0.)))
    assert state.outcome_counts[root, "DOWN"] == Counter({(a, 0.): 385, (b, 0.): 383})
    assert state.rows[root, "DOWN"] == ((385 / 768, a, 0.), (383 / 768, b, 0.))
    assert state.batch_counts[root, "DOWN"] == state.spent_batches == 3
    assert state.row_order == [(root, "DOWN")] and len(state.rows) == 1
    assert state.work_counts["rows_acquired"] == 1
    assert state.work_counts["first_batch_observations_inserted"] == 1
    assert state.work_counts["repeat_batch_observations_inserted"] == 2
    assert state.work_counts["batch_draws_inserted"] == 768
    expected = MassBoundPlannerState(root, QUERIES)
    expected.observe_row(root, "DOWN", state.rows[root, "DOWN"])
    for name in QUERIES:
        assert cache_values(state.solve(name)) == cache_values(expected.solve(name))


def test_new_support_reopens_completion_and_invalidates_only_affected_ancestors():
    root, a, leaf, cutoff = ((h, SINGLE) for h in (3, 2, 1, 0))
    b, off_path = (2, DOUBLE), (1, (3,) + (0,) * 15)
    state = ResamplingPlannerState(root, QUERIES)
    for key, successor in ((root, a), (a, leaf)):
        for action in state.profiles[key].legal_actions:
            state.observe_batch(key, action, ((1., successor, 0.),))
    state.observe_batch(leaf, "DOWN", ((1., cutoff, 0.),))
    state.observe_state(off_path)
    assert state.select_row(root, "q") is None
    cache = state.solve("q")
    before_off_path = cache.lower[off_path], cache.upper[off_path]
    parent = state.clone()
    sibling = state.clone()
    state.observe_batch(root, "DOWN", ((1., b, 0.),))
    assert state.caches["q"].dirty == {root, b}
    assert root in state.reverse_dependencies[a] and root in state.reverse_dependencies[b]
    assert b not in parent.profiles and b not in sibling.profiles
    assert parent.batch_counts[root, "DOWN"] == sibling.batch_counts[root, "DOWN"] == 1
    assert state.batch_counts[root, "DOWN"] == 2
    visits = state.work_counts["interval_state_visits"]
    updated = state.solve("q")
    assert state.work_counts["interval_state_visits"] - visits == 2
    assert (updated.lower[off_path], updated.upper[off_path]) == before_off_path
    assert updated.upper[root] > updated.lower[root]
    assert state.select_row(root, "q") is not None
    assert state.caches["q"].lower is not parent.caches["q"].lower
    assert state.outcome_counts[root, "DOWN"] is not parent.outcome_counts[root, "DOWN"]
    assert state.rows[root, "LEFT"] is parent.rows[root, "LEFT"]
    assert parent.solve("q").lower[root] == parent.solve("q").upper[root] == 0


def test_unclipped_score_revisits_zero_variance_known_row_without_changing_execution(monkeypatch):
    monkeypatch.setattr(partial, "_step_v1", lambda *args: pytest.fail("planner accessed unknown support"))
    state = ResamplingPlannerState.from_warm(make_warm())
    key = state.root
    assert state.select_row(key, "q") is None
    frozen_before, intervals_before = state.freeze()
    scores = state._acquisition_scores("q")
    assert scores.radius[key, "RIGHT"] == 5 / math.sqrt(256)
    assert scores.q_upper[key, "RIGHT"] == 5 / 16
    assert scores.q_upper[key, "DOWN"] == 0
    assert scores.policy[key] == "RIGHT"
    assert state.select_resample(key, "q", "DIRECTED") == (key, "RIGHT")
    assert state.select_resample(key, "q", "BALANCED") == (key, "RIGHT")
    assert state._acquisition_scores("goal") == scores
    state.observe_batch(key, "RIGHT", ((1., (0, SINGLE), 0.),))
    assert state._acquisition_scores("q").radius[key, "RIGHT"] == 5 / math.sqrt(512)
    frozen_after, intervals_after = state.freeze()
    assert frozen_after.policies == frozen_before.policies
    assert intervals_after == intervals_before


def test_directed_uses_reach_times_radius_and_balanced_uses_batch_count_then_key():
    root, child, cutoff = ((h, SINGLE) for h in (2, 1, 0))
    state = ResamplingPlannerState(root, {"q": QUERIES["q"]})
    state.observe_batch(root, "DOWN", ((1., child, 0.),))
    state.observe_batch(child, "RIGHT", ((1., cutoff, 0.),))
    assert state.select_resample(root, "q", "DIRECTED") == (root, "DOWN")
    assert state.select_resample(root, "q", "BALANCED") == (child, "RIGHT")
    state.observe_batch(root, "DOWN", ((1., child, 0.),))
    assert state.select_resample(root, "q", "DIRECTED") == (child, "RIGHT")
    assert state.select_resample(root, "q", "BALANCED") == (child, "RIGHT")


def test_shared_successor_reach_is_summed_and_unreachable_rows_are_ineligible():
    root, a, b, leaf, cutoff = (3, SINGLE), (2, SINGLE), (2, DOUBLE), (1, SINGLE), (0, SINGLE)
    state = ResamplingPlannerState(root, {"q": QUERIES["q"]})
    for _ in range(2):
        state.observe_batch(root, "DOWN", ((.5, a, 0.), (.5, b, 0.)))
        state.observe_batch(a, "DOWN", ((1., leaf, 0.),))
        state.observe_batch(b, "DOWN", ((1., leaf, 0.),))
    state.observe_batch(leaf, "RIGHT", ((1., cutoff, 0.),))
    off_path = (1, (3,) + (0,) * 15)
    state.observe_batch(off_path, "DOWN", ((1., (0, off_path[1]), 0.),))
    visits = state.work_counts["resampling_frontier_state_visits"]
    assert state.select_resample(root, "q", "DIRECTED") == (leaf, "RIGHT")
    assert state.work_counts["resampling_frontier_state_visits"] - visits == 4


@pytest.mark.parametrize("key", [(0, SINGLE), (3, (11,) + (0,) * 15)])
def test_terminal_has_no_resampling_candidate_and_keeps_exact_terminal_score(key):
    state = ResamplingPlannerState(key, QUERIES)
    expected = 3 if key[0] else 0
    assert state._acquisition_scores("goal").upper[key] == expected
    assert state.select_resample(key, "goal", "DIRECTED") is None
    assert state.spent_batches == 0


def test_zero_return_range_is_not_a_resampling_candidate():
    key = (1, SINGLE)
    state = ResamplingPlannerState(key, {"q": Query(1, 0, 0)})
    state.observe_batch(key, "DOWN", ((1., (0, SINGLE), 0.),))
    assert state._acquisition_scores("q").radius[key, "DOWN"] == 0
    assert state.select_resample(key, "q", "BALANCED") is None
    assert state.select_resample(key, "q", "DIRECTED") is None


def test_conversion_and_clone_charge_outer_work_as_well_as_inherited_copy(monkeypatch):
    warm = make_warm()
    times = iter((10., 20., 30., 40., 50., 60., 70., 80.))
    tick = lambda: next(times)
    monkeypatch.setattr(incremental, "perf_counter", tick)
    monkeypatch.setattr(resampling, "perf_counter", tick)
    state = ResamplingPlannerState.from_warm(warm)
    assert state.conversion_seconds == 30
    assert state.engine_seconds == warm.engine_seconds + 30
    child = state.clone()
    assert child.clone_seconds == 30
    assert child.engine_seconds == state.engine_seconds + 30
    assert child.batch_counts is not state.batch_counts
    assert child.outcome_counts[state.root, "RIGHT"] is not state.outcome_counts[state.root, "RIGHT"]
    assert child.work_counts["clone_batch_count_entries_copied"] == 1
    assert child.work_counts["clone_outcome_count_entries_copied"] == 1


def test_new_row_interface_cannot_bypass_batch_bookkeeping():
    key = (1, SINGLE)
    state = ResamplingPlannerState(key, {"q": QUERIES["q"]})
    row = ((1., (0, SINGLE), 0.),)
    state.observe_row(key, "DOWN", row)
    assert state.spent_batches == state.batch_counts[key, "DOWN"] == 1
    with pytest.raises(ValueError, match="observe_batch"):
        state.observe_row(key, "DOWN", row)


def test_batch_counts_must_represent_256_actual_draws():
    state = ResamplingPlannerState((1, SINGLE), {"q": QUERIES["q"]})
    with pytest.raises(ValueError, match="256"):
        state.observe_batch(state.root, "DOWN", ((.1, (0, SINGLE), 0.), (.9, (0, DOUBLE), 0.)))
    assert state.spent_batches == 0 and state.rows == {}
