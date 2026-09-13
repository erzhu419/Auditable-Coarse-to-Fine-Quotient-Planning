"""Action-gap stopping, dual-path acquisition, and empirical-model isolation."""

from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_gap_v16 as gap_module
from acfqp.science import controlled_predictive_partial_v12 as partial
from acfqp.science.controlled_predictive_gap_v16 import GapPlannerState
from acfqp.science.controlled_predictive_mass_bound_v14 import MassBoundPlannerState
from acfqp.science.controlled_predictive_partial_v12 import BoardProfile
from acfqp.science.controlled_predictive_quotient_v1 import Query


SINGLE = (0,) * 5 + (1,) + (0,) * 10
DOUBLE = (0,) * 5 + (2,) + (0,) * 10
TRIPLE = (0,) * 5 + (3,) + (0,) * 10
GOAL = (11,) + (0,) * 15
QUERY = {"q": Query(1, 5, 0)}


def restrict(state, key, actions):
    state.observe_state(key)
    profile = state.profiles[key]
    state.profiles[key] = BoardProfile(profile.status, tuple(actions),
                                       tuple((action, profile.reward(action)) for action in actions),
                                       profile.mass)


def assess(state):
    return state.assess_gap(state.root, "q")


def test_unknown_challenger_remains_a_paid_candidate_after_empirical_closure(monkeypatch):
    monkeypatch.setattr(partial, "_step_v1", lambda *args: pytest.fail("planner enumerated support"))
    root = (1, SINGLE)
    state = GapPlannerState(root, QUERY)
    state.observe_batch(root, "RIGHT", ((1., (0, SINGLE), 0.),))
    assert state.select_row(root, "q") is None
    result = assess(state)
    assert result.incumbent == "RIGHT" and result.challenger == "DOWN"
    assert result.incumbent_lower == -5 / 16 and result.challenger_upper == 0
    assert result.gap == -5 / 16 and not result.separated
    assert result.pair == (root, "DOWN") and result.candidate_count == 2
    assert state.spent_batches == 1
    assert state.work_counts["gap_unknown_frontiers"] == 1


def test_shared_downstream_row_receives_both_witness_reach_contributions(monkeypatch):
    root, child, finished = (2, SINGLE), (1, DOUBLE), (1, GOAL)
    state = GapPlannerState(root, QUERY)
    restrict(state, root, ("DOWN", "RIGHT"))
    for action in ("DOWN", "RIGHT"):
        state.observe_batch(root, action, ((.5, child, 0.), (.5, finished, 0.)))
    restrict(state, child, ("DOWN",))
    state.observe_batch(child, "DOWN", ((1., (0, SINGLE), 0.),))
    off_path = (1, TRIPLE)
    state.observe_batch(off_path, "DOWN", ((1., (0, TRIPLE), 0.),))
    # Each root contribution is .5. Each witness contributes .375 to the child,
    # so only their sum makes that child the largest eligible contribution.
    monkeypatch.setattr(gap_module, "mass_bound_unknown_action_bounds",
                        lambda key, *_: (0., 12. if key == child else 8.))
    result = assess(state)
    assert result.incumbent == "DOWN" and result.challenger == "RIGHT"
    assert result.pair == (child, "DOWN")
    assert result.candidate_count == 3
    assert state.work_counts["gap_frontier_state_visits"] == 4
    assert state.work_counts["gap_candidate_contributions"] == 4
    assert state.work_counts["gap_candidates_considered"] == 3


def test_single_legal_action_separates_even_when_its_value_is_unresolved():
    root, child = (2, SINGLE), (1, DOUBLE)
    state = GapPlannerState(root, QUERY)
    restrict(state, root, ("DOWN",))
    state.observe_batch(root, "DOWN", ((1., child, 0.),))
    cache = state.solve("q")
    assert cache.upper[root] > cache.lower[root]
    result = state.assess_gap(root, "q")
    assert result.incumbent == "DOWN" and result.challenger is None
    assert result.separated and result.gap is None and result.challenger_upper is None
    # NO_STOP can still acquire through the unique action's downstream path.
    assert result.pair == (child, "DOWN") and result.candidate_count == 2


def test_empirical_ties_with_identical_observations_do_not_imply_separation():
    root = (1, SINGLE)
    state = GapPlannerState(root, QUERY)
    restrict(state, root, ("DOWN", "RIGHT"))
    for action in ("DOWN", "RIGHT"):
        state.observe_batch(root, action, ((1., (0, SINGLE), 0.),))
    result = assess(state)
    assert result.incumbent == "DOWN" and result.challenger == "RIGHT"
    assert not result.separated and result.gap == -10 / 16
    assert result.pair == (root, "DOWN")
    assert result.candidate_count == 2
    state.observe_batch(root, "DOWN", ((1., (0, SINGLE), 0.),))
    next_result = assess(state)
    assert not next_result.separated and next_result.pair == (root, "RIGHT")


def test_positive_action_gap_stops_but_keeps_identical_no_stop_allocation():
    root = (1, SINGLE)
    state = GapPlannerState(root, QUERY)
    restrict(state, root, ("DOWN", "RIGHT"))
    state.observe_batch(root, "DOWN", ((1., (0, SINGLE), 1.),))
    state.observe_batch(root, "RIGHT", ((1., (0, SINGLE), 0.),))
    result = assess(state)
    assert result.incumbent == "DOWN" and result.challenger == "RIGHT"
    assert result.separated and result.gap == 1 - 10 / 16
    assert result.pair == (root, "DOWN") and result.candidate_count == 2


def test_assessment_and_inherited_conversion_clone_preserve_empirical_state():
    root = (1, SINGLE)
    warm = MassBoundPlannerState(root, QUERY)
    warm.observe_row(root, "RIGHT", ((1., (0, SINGLE), 0.),))
    warm.solve("q")
    state = GapPlannerState.from_warm(warm)
    assert isinstance(state, GapPlannerState)
    before_cache = deepcopy(state.caches)
    before_rows = dict(state.rows)
    before_counts = deepcopy(state.outcome_counts)
    before_engine = state.engine_seconds
    result = state.assess_gap(root, "q")
    assert state.engine_seconds > before_engine
    assert state.caches == before_cache and state.rows == before_rows
    assert state.outcome_counts == before_counts and state.spent_batches == 1
    assert state.caches == warm.caches
    sibling = state.clone()
    assert isinstance(sibling, GapPlannerState)
    sibling.observe_batch(root, "RIGHT", ((1., (0, DOUBLE), 0.),))
    assert state.outcome_counts == before_counts and state.spent_batches == 1
    assert sibling.spent_batches == 2
    assert state.assess_gap(root, "q") == result
    assert sibling.work_counts is not state.work_counts


def test_terminal_and_exact_zero_range_have_no_paid_candidate():
    terminal = GapPlannerState((0, SINGLE), QUERY)
    terminal_result = assess(terminal)
    assert terminal_result.separated and terminal_result.pair is None
    assert terminal_result.incumbent is terminal_result.challenger is None
    state = GapPlannerState((1, SINGLE), {"q": Query(1, 0, 0)})
    result = assess(state)
    assert result.separated and result.gap == 0
    assert result.pair is None and result.candidate_count == 0


def test_assessment_charges_the_entire_score_and_selection_pass(monkeypatch):
    state = GapPlannerState((1, SINGLE), QUERY)
    state.solve("q")
    before = state.engine_seconds
    ticks = iter((10., 15.))
    monkeypatch.setattr(gap_module, "perf_counter", lambda: next(ticks))
    state.assess_gap(state.root, "q")
    assert state.engine_seconds == before + 5
    assert state.work_counts["gap_score_queries"] == 1
    assert state.work_counts["gap_score_state_visits"] == 1
    assert state.work_counts["gap_assessments"] == 1
