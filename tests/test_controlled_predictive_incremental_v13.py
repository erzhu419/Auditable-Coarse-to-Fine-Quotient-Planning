"""Incremental intervals retain V12 numerical semantics and branch isolation."""

from collections import Counter

import pytest

from acfqp.science.controlled_predictive_incremental_v13 import PlannerState
from acfqp.science.controlled_predictive_partial_v12 import RowSampleProvider, _solve, run_partial
from acfqp.science.controlled_predictive_quotient_v1 import Query


def board(rank):
    return (0,) * 5 + (rank,) + (0,) * 10


ROOT = (3, board(1))
A, B = (2, board(1)), (2, board(2))
LEAF_A, LEAF_B = (1, board(1)), (1, board(2))
CUTOFF = (0, board(1))
QUERIES = {"z_first": Query(1, 1, 0), "a_second": Query(1, .1, 2)}


def cache_values(cache):
    return cache.lower, cache.upper, cache.q_lower, cache.q_upper, cache.policy


def make_branching(update_mode="incremental"):
    state = PlannerState(ROOT, QUERIES, update_mode=update_mode)
    state.observe_row(ROOT, "DOWN", ((.5, A, 0.), (.5, B, 0.)))
    state.observe_row(A, "LEFT", ((1., LEAF_A, 0.),))
    state.observe_row(B, "RIGHT", ((1., LEAF_B, 0.),))
    return state


def test_new_row_and_child_update_only_the_observed_ancestor_branch():
    state = make_branching()
    cache = state.solve("z_first")
    untouched = {key: (cache.lower[key], cache.upper[key], cache.policy[key]) for key in (B, LEAF_B)}
    visits_before = state.work_counts["interval_state_visits"]
    state.observe_row(LEAF_A, "UP", ((1., CUTOFF, 0.),))
    assert cache.dirty == {CUTOFF, LEAF_A, A, ROOT}
    updated = state.solve("z_first")
    assert state.work_counts["interval_state_visits"] - visits_before == 4
    assert updated.lower[LEAF_A] == updated.lower[A] == 0
    assert updated.lower[ROOT] == -.5
    assert {key: (updated.lower[key], updated.upper[key], updated.policy[key]) for key in (B, LEAF_B)} == untouched
    assert not updated.dirty
    assert cache_values(updated) == _solve(state.profiles, state.rows, QUERIES["z_first"], Counter())
    before = state.work_counts["interval_state_visits"]
    assert state.solve("z_first") is updated
    assert state.work_counts["interval_state_visits"] == before


def test_each_query_initializes_from_all_current_rows_then_invalidates_independently():
    state = make_branching()
    first = state.solve("z_first")
    assert "a_second" not in state.caches
    state.observe_row(LEAF_A, "UP", ((1., CUTOFF, 0.),))
    visits = state.work_counts["interval_state_visits"]
    second = state.solve("a_second")
    assert state.work_counts["interval_state_visits"] - visits == len(state.profiles)
    assert state.work_counts["query_cache_initializations"] == 2
    assert not second.dirty
    assert first.dirty == {CUTOFF, LEAF_A, A, ROOT}
    assert cache_values(second) == _solve(state.profiles, state.rows, QUERIES["a_second"], Counter())


def test_revealed_off_path_state_is_profiled_without_changing_existing_bounds():
    state = make_branching()
    cache = state.solve("z_first")
    before = dict(cache.lower), dict(cache.upper)
    independent = (1, board(3))
    state.observe_state(independent)
    assert cache.dirty == {independent}
    visits = state.work_counts["interval_state_visits"]
    state.solve("z_first")
    assert state.work_counts["interval_state_visits"] - visits == 1
    assert all(cache.lower[key] == value for key, value in before[0].items())
    assert all(cache.upper[key] == value for key, value in before[1].items())
    assert not state.rows.get((independent, "DOWN"))


def test_fsum_and_all_action_values_match_complete_recompute_exactly_after_every_insertion():
    incremental = PlannerState(ROOT, QUERIES)
    complete = PlannerState(ROOT, QUERIES, update_mode="full_recompute")
    third = (2, board(3))
    transitions = [
        (ROOT, "DOWN", ((13 / 256, A, .123456789), (37 / 256, B, 1e-17), (206 / 256, third, .00390625))),
        (A, "LEFT", ((1., LEAF_A, 0.),)),
        (B, "RIGHT", ((1., LEAF_B, 0.),)),
        (LEAF_A, "UP", ((1., CUTOFF, 0.),)),
    ]
    for state in (incremental, complete):
        for name in QUERIES:
            state.solve(name)
    for key, action, row in transitions:
        for state in (incremental, complete):
            state.observe_row(key, action, row)
        for name in QUERIES:
            inc = incremental.solve(name)
            full = complete.solve(name)
            assert cache_values(inc) == cache_values(full)
            assert cache_values(inc) == _solve(incremental.profiles, incremental.rows, QUERIES[name], Counter())
    assert complete.reverse_dependencies == {}
    assert complete.work_counts["reverse_dependency_states_visited"] == 0
    assert incremental.work_counts["interval_state_visits"] < complete.work_counts["interval_state_visits"]


@pytest.mark.parametrize("mode", ["bfs", "query_interval"])
def test_selected_rows_intervals_and_all_policies_equal_v12_at_the_same_checkpoints(mode):
    root = (2, board(1))
    budgets = (1, 4, 8)
    reference = run_partial(root, RowSampleProvider(31), QUERIES, budgets=budgets, mode=mode)
    engines = [PlannerState(root, QUERIES, mode=mode, update_mode=update)
               for update in ("full_recompute", "incremental")]
    providers = [RowSampleProvider(31), RowSampleProvider(31)]
    stopped = [False, False]
    for checkpoint, budget in zip(reference, budgets):
        for index, (state, provider) in enumerate(zip(engines, providers)):
            while len(state.rows) < budget and not stopped[index]:
                stopped[index] = not state.sample_next(provider)
            frozen, intervals = state.freeze()
            assert state.rows == checkpoint.known_rows
            assert state.profiles == checkpoint.profiles
            assert frozen.policies == checkpoint.frozen_policy.policies
            assert intervals == checkpoint.root_intervals
        assert engines[0].row_order == engines[1].row_order
    assert providers[0].work_counts == providers[1].work_counts


def test_branch_clone_is_independent_in_rows_dependencies_dirty_sets_caches_and_cursor():
    parent = make_branching()
    parent.freeze()
    frozen_before, intervals_before = parent.freeze()
    left, right = parent.clone(), parent.clone()
    assert left.profiles is not parent.profiles
    assert left.profiles[ROOT] is parent.profiles[ROOT]
    assert left.rows[ROOT, "DOWN"] is parent.rows[ROOT, "DOWN"]
    assert left.reverse_dependencies[LEAF_A] is not parent.reverse_dependencies[LEAF_A]
    assert left.caches["z_first"].lower is not parent.caches["z_first"].lower
    left.observe_row(LEAF_A, "UP", ((1., CUTOFF, 0.),))
    left.solve("z_first")
    left.next_row()
    assert (LEAF_A, "UP") not in parent.rows and (LEAF_A, "UP") not in right.rows
    assert CUTOFF not in parent.profiles and CUTOFF not in right.profiles
    assert left.caches["z_first"].lower[ROOT] == -.5
    assert parent.caches["z_first"].lower[ROOT] == right.caches["z_first"].lower[ROOT] == -1
    assert parent.cursor == right.cursor == 0 and left.cursor > 0
    frozen_after, intervals_after = parent.freeze()
    assert intervals_before == intervals_after
    assert frozen_before.policies == frozen_after.policies
    assert parent.work_counts["branch_clones"] == 0
    assert left.work_counts["branch_clones"] == 1
    assert left.clone_seconds > 0


def test_current_board_selection_does_not_advance_multi_query_cursor_or_observe_siblings():
    state = PlannerState(ROOT, QUERIES)
    current = (1, board(2))
    assert state.select_row(current, "z_first") == (current, "DOWN")
    assert state.cursor == 0
    assert set(state.profiles) == {ROOT, current}
    assert state.rows == {}
    state.observe_row(current, "DOWN", ((1., (0, board(2)), 0.),))
    assert state.select_row(current, "z_first") is None
    assert state.cursor == 0
    assert state.solve("z_first").lower[current] == state.solve("z_first").upper[current] == 0
