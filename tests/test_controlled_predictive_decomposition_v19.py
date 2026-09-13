"""Analytic error terms, terminal rewards, frozen-state isolation and exact truth."""

from copy import deepcopy
import math

import pytest

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import (
    ExactOracle, UnsupportedSnapshot, evaluate_snapshot,
)
from acfqp.science.controlled_predictive_gap_v16 import GapPlannerState
from acfqp.science.controlled_predictive_quotient_v1 import Query, compile_full_state, plan


def board(rank):
    return (0,) * 5 + (rank,) + (0,) * 10


ROOT, A, B, END = (2, board(1)), (1, board(2)), (1, board(3)), (0, board(1))


def analytic_fixture(omit_a_observations=False):
    state = GapPlannerState(ROOT, {"q": Query(1, 0, 0)})
    ground_rows = {}
    for key, exact, empirical in (
        (A, {"LEFT": 1., "RIGHT": 2., "DOWN": 0., "UP": 0.},
         {"LEFT": 5., "RIGHT": 2., "DOWN": 0., "UP": 0.}),
        (B, {"LEFT": 1., "RIGHT": 4., "DOWN": 0., "UP": 0.},
         {"LEFT": 1., "RIGHT": 3., "DOWN": 0., "UP": 0.}),
    ):
        for action, reward in exact.items():
            ground_rows[key, action] = ((1., END, reward),)
            if not (key == A and omit_a_observations):
                state.observe_batch(key, action, ((1., END, empirical[action]),))
    state.observe_batch(ROOT, "LEFT", ((.75, A, 0.), (.25, B, 0.)))
    state.observe_batch(ROOT, "RIGHT", ((.25, A, 0.), (.75, B, 0.)))
    ground_rows[ROOT, "LEFT"] = ((.5, A, 0.), (.5, B, 0.))
    ground_rows[ROOT, "RIGHT"] = ((.25, A, 0.), (.75, B, 0.))
    ground_rows[ROOT, "DOWN"] = ground_rows[ROOT, "UP"] = ((1., A, 0.),)
    oracle = ExactOracle({ROOT: "ACTIVE", A: "ACTIVE", B: "ACTIVE", END: "CUTOFF"}, ground_rows)
    return state, oracle


def test_analytic_transition_estimation_policy_loss_and_margin_accounting():
    state, oracle = analytic_fixture()
    report = evaluate_snapshot(state, "q", ROOT, oracle)
    left, right = report["actions"]["LEFT"], report["actions"]["RIGHT"]
    assert report["empirical"]["selected_action"] == "LEFT"
    assert report["local_true_optimal_actions"] == ["RIGHT"]
    assert [left[k] for k in ("q_hat", "q_star", "q_hat_exact_continuation")] == [4.5, 3., 2.5]
    assert [left[k] for k in ("A_transition_error", "B_continuation_estimation_error", "C_continuation_policy_loss")] == [-.5, 2.75, -.75]
    assert [right[k] for k in ("q_hat", "q_star", "A_transition_error", "B_continuation_estimation_error", "C_continuation_policy_loss")] == [3.5, 3.5, 0., .25, -.25]
    margin = report["left_minus_right"]
    assert [margin[k] for k in ("q_hat", "q_star", "A_transition_error", "B_continuation_estimation_error", "C_continuation_policy_loss")] == [1., -.5, -.5, 2.5, -.5]
    assert report["identities_pass"] and report["maximum_absolute_identity_residual"] == 0
    assert all(c["C_policy_loss"] <= 0 for action in (left, right) for c in action["children"])
    assert left["children"][0]["selected_action"] == "LEFT"
    assert left["children"][0]["selected_action_observed"]
    assert left["children"][0]["empirical_interval_closed"]


def test_terminal_bonuses_penalties_and_immediate_reward_belong_in_transition_term():
    lost_board = tuple(1 + (i + i // 4) % 2 for i in range(16))
    lost, won = (1, lost_board), (1, (11,) + (0,) * 15)
    state = GapPlannerState(ROOT, {"q": Query(2, 3, 5)})
    left = ((.75, lost, 1.), (.25, won, 2.))
    right = ((.25, lost, 0.), (.75, won, 0.))
    state.observe_batch(ROOT, "LEFT", left)
    state.observe_batch(ROOT, "RIGHT", right)
    oracle = ExactOracle({ROOT: "ACTIVE", lost: "LOST", won: "WON"}, {
        (ROOT, "LEFT"): ((.5, lost, 1.), (.5, won, 2.)), (ROOT, "RIGHT"): right})
    result = evaluate_snapshot(state, "q", ROOT, oracle)
    row = result["actions"]["LEFT"]
    assert row["q_hat"] == 1.5 and row["q_star"] == 4.
    assert row["A_transition_error"] == -2.5
    assert row["B_continuation_estimation_error"] == row["C_continuation_policy_loss"] == 0
    assert all(child["selected_action"] is None for child in row["children"])
    assert result["identities_pass"]


def test_unknown_h1_chosen_row_is_reported_as_structural_bound_without_oracle_substitution():
    state, oracle = analytic_fixture(omit_a_observations=True)
    state.queries["q"] = Query(1, 1, 0)
    result = evaluate_snapshot(state, "q", ROOT, oracle)
    child = result["actions"]["LEFT"]["children"][0]
    assert child["key"] == [A[0], list(A[1])]
    assert child["selected_action"] == "DOWN" and not child["selected_action_observed"]
    assert child["selected_action_batch_count"] == 0
    assert not child["empirical_interval_closed"]
    assert child["v_hat"] == -1 and child["v_pi"] == 0
    assert child["B_value_estimation_error"] == -1
    assert child["v_star"] == 2 and child["C_policy_loss"] == -2
    assert result["identities_pass"]


def test_snapshot_is_unchanged_and_repeated_truth_query_uses_only_oracle_cache(monkeypatch):
    state, oracle = analytic_fixture()
    before = deepcopy(state.__dict__)
    rows_before, statuses_before = dict(oracle.rows), dict(oracle.statuses)
    def no_observation(*args, **kwargs):
        pytest.fail("diagnosis acquired or inserted an observation")
    monkeypatch.setattr(GapPlannerState, "observe_batch", no_observation)
    monkeypatch.setattr(GapPlannerState, "observe_row", no_observation)
    first = evaluate_snapshot(state, "q", ROOT, oracle)
    dp_work = oracle.work_counts["exact_dp_state_visits"]
    second = evaluate_snapshot(state, "q", ROOT, oracle)
    assert state.__dict__ == before
    assert oracle.rows == rows_before and oracle.statuses == statuses_before
    assert first["actions"] == second["actions"]
    assert first["left_minus_right"] == second["left_minus_right"]
    assert oracle.work_counts["exact_dp_state_visits"] == dp_work
    assert second["accounting"]["oracle_work"]["exact_query_cache_hits"] == 1
    assert "exact_dp_row_reads" not in second["accounting"]["oracle_work"]
    assert first["accounting"]["snapshot_clone_and_solve_seconds"] > 0
    assert oracle.accounting()["total_seconds"] > 0


def test_closure_key_conversion_matches_established_exact_plan():
    dense = (1, 1, 3, 3, 5, 6, 7, 8, 9, 3, 4, 5, 6, 7, 8, 9)
    closure = build_development_closure(horizon=2, boards={"fixture": dense})
    query = Query(1, 2, 3)
    oracle = ExactOracle.from_closure(closure)
    solution = oracle.solution(query)
    compiled = compile_full_state(closure.model)
    reference = plan(compiled, query)
    for state, board_value in closure.boards.items():
        key = closure.model.layers[state], board_value
        assert math.isclose(solution.values[key], reference.values[compiled.state_to_cell[state]], abs_tol=1e-10, rel_tol=0)
    assert oracle.work_counts["ground_rows_indexed"] == len(closure.model.rows)
    assert oracle.work_counts["ground_support_entries_indexed"] == closure.counts["exact_outcomes_enumerated"]


def test_h3_root_cannot_be_substituted_for_the_declared_h2_snapshot():
    state, oracle = analytic_fixture()
    with pytest.raises(UnsupportedSnapshot, match="retained H2"):
        evaluate_snapshot(state, "q", (3, ROOT[1]), oracle)
