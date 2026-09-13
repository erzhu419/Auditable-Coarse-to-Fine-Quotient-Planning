"""Matched local draws, unchanged selectors, arbitrary-horizon error terms and fixed panels."""

from copy import deepcopy
from itertools import combinations

import pytest

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_execution_v13 import ExactEnvironment
from acfqp.science.controlled_predictive_execution_v17 import evaluate_balanced_gap_execution
from acfqp.science.controlled_predictive_local_v21 import (
    ARMS, evaluate_local_snapshot, evaluate_panel, run_local_allocation,
)
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState


def board(rank):
    return (0,) * 5 + (rank,) + (0,) * 10


ROOT = (1, board(1))
END = (0, board(1))
GOAL_BOARD = (11,) + (0,) * 15


def repeated_snapshot(query=Query(1, 1, 0)):
    state = CachedGapPlannerState(ROOT, {"q": query})
    for action in state.profiles[ROOT].legal_actions:
        state.observe_batch(ROOT, action, ((1., END, float(action == "LEFT")),))
    for _ in range(2):
        state.observe_batch(ROOT, "LEFT", ((1., END, 1.),))
    return state


@pytest.mark.parametrize("arm", ("CACHED", "VARIANCE"))
def test_local_draws_preserve_repeat_indices_ignore_gap_and_match_original_selectors(arm, monkeypatch):
    state = repeated_snapshot()
    original = deepcopy(state.__dict__)
    assert state.spent_batches == 6 and len(state.rows) == 4
    environment = ExactEnvironment.from_closure(build_development_closure(horizon=1, boards={"fixture": ROOT[1]}))
    reference_state = state.clone()
    reference_state.__class__ = ARMS[arm]
    reference = evaluate_balanced_gap_execution(reference_state, BatchRowSampleProvider(71), "q", environment,
                                              mode="CONTINUE", total_batch_cap=9)
    def no_truth(*args, **kwargs):
        pytest.fail("the local allocation loop consulted the truth oracle")
    monkeypatch.setattr(ExactOracle, "solution", no_truth)
    endpoint, report = run_local_allocation(state, arm, BatchRowSampleProvider(71), "q", ROOT, 3)
    assert type(endpoint) is ARMS[arm]
    assert state.__dict__ == original
    assert report["first_original_stop_index"] == 0
    assert report["completed_fixed_budget"] and report["completed_batches"] == 3
    assert report["initial_batches"] == 6 and report["final_batches"] == 9
    assert report["actual_draws"] == report["provider_counts"]["physical_draws"] == 768
    assert report["requested_batches"][0]["batch_index"] == 3
    for name in ("requested_batches", "observed_batches", "gap_assessments"):
        assert report[name] == reference["trace"][name]
    assert report["final_action"] == reference["root_action"]
    assert report["accounting"]["work_counts"]["branch_clones"] == 1
    assert report["accounting"]["seconds_by_stage"]["acquisition"] > 0


def test_original_empty_selector_is_retained_as_an_incomplete_matched_budget():
    state = repeated_snapshot(query=Query(0, 0, 0))
    endpoint, report = run_local_allocation(state, "VARIANCE", BatchRowSampleProvider(71), "q", ROOT, 3)
    assert report["first_original_stop_index"] == 0
    assert not report["completed_fixed_budget"] and report["completed_batches"] == 0
    assert report["stop_reason"] == "NO_ELIGIBLE_CANDIDATE"
    assert report["requested_batches"] == report["observed_batches"] == []
    assert len(report["gap_assessments"]) == 1
    assert report["provider_counts"] == {} and report["actual_draws"] == 0
    assert endpoint.spent_batches == state.spent_batches


def test_passed_original_remaining_quota_cannot_overrun_total_cap():
    state = repeated_snapshot()
    provider = BatchRowSampleProvider(71)
    with pytest.raises(ValueError, match="128-batch cap"):
        run_local_allocation(state, "CACHED", provider, "q", ROOT, 123)
    assert state.spent_batches == 6 and not provider.work_counts


def analytic_snapshot(horizon):
    root, a, b = (horizon, board(1)), (horizon - 1, board(2)), (horizon - 1, board(3))
    end = (horizon - 2, GOAL_BOARD)
    state = CachedGapPlannerState(root, {"q": Query(1, 0, 0)})
    rows = {}
    for key, exact, empirical in (
        (a, {"LEFT": 1., "RIGHT": 2., "DOWN": 0., "UP": 0.},
         {"LEFT": 5., "RIGHT": 2., "DOWN": 0., "UP": 0.}),
        (b, {"LEFT": 1., "RIGHT": 4., "DOWN": 0., "UP": 0.},
         {"LEFT": 1., "RIGHT": 3., "DOWN": 0., "UP": 0.}),
    ):
        for action in exact:
            rows[key, action] = ((1., end, exact[action]),)
            state.observe_batch(key, action, ((1., end, empirical[action]),))
    state.observe_batch(root, "LEFT", ((.75, a, 0.), (.25, b, 0.)))
    state.observe_batch(root, "RIGHT", ((.25, a, 0.), (.75, b, 0.)))
    rows[root, "LEFT"] = ((.5, a, 0.), (.5, b, 0.))
    rows[root, "RIGHT"] = ((.25, a, 0.), (.75, b, 0.))
    rows[root, "DOWN"] = rows[root, "UP"] = ((1., a, 0.),)
    oracle = ExactOracle({root: "ACTIVE", a: "ACTIVE", b: "ACTIVE", end: "WON"}, rows)
    return state, oracle, root, a, b, end


@pytest.mark.parametrize("horizon", [2, 3])
def test_any_horizon_ad_identity_sorted_margins_and_unknown_bounds(horizon):
    state, oracle, root, a, b, end = analytic_snapshot(horizon)
    original = deepcopy(state.__dict__)
    result = evaluate_local_snapshot(state, "q", root, oracle)
    assert state.__dict__ == original
    left = result["actions"]["LEFT"]
    assert left["q_hat"] == 4.5 and left["q_star"] == 3
    assert left["A_transition_error"] == -.5 and left["D_continuation_error"] == 2
    assert left["total_error"] == 1.5
    assert result["selected_action"] == "LEFT" and result["local_regret"] == .5
    assert result["local_true_optimal_actions"] == ["RIGHT"]
    assert result["identities_pass"] and result["maximum_absolute_identity_residual"] == 0
    assert [row["actions"] for row in result["pair_margins"]] == [list(pair) for pair in combinations(sorted(state.profiles[root].legal_actions), 2)]
    margin = next(row for row in result["pair_margins"] if row["actions"] == ["LEFT", "RIGHT"])
    assert margin["q_hat_difference"] == 1 and margin["q_star_difference"] == -.5
    assert margin["A_transition_error_difference"] == -.5 and margin["D_continuation_error_difference"] == 2
    unknown = result["actions"]["DOWN"]
    assert not unknown["observed"] and unknown["q_hat"] is None
    assert unknown["A_transition_error"] is unknown["D_continuation_error"] is None
    assert unknown["children"] == [] and unknown["batch_count"] == 0
    assert unknown["lower"] <= unknown["upper"] and unknown["q_star"] == 2


def test_h1_decomposition_keeps_terminal_values_and_reward_weights():
    lost_board = tuple(1 + (i + i // 4) % 2 for i in range(16))
    lost, won = (0, lost_board), (0, GOAL_BOARD)
    state = CachedGapPlannerState(ROOT, {"q": Query(2, 3, 5)})
    left = ((.75, lost, 1.), (.25, won, 2.))
    right = ((.25, lost, 0.), (.75, won, 0.))
    state.observe_batch(ROOT, "LEFT", left)
    state.observe_batch(ROOT, "RIGHT", right)
    rows = {(ROOT, "LEFT"): ((.5, lost, 1.), (.5, won, 2.)), (ROOT, "RIGHT"): right,
            (ROOT, "DOWN"): ((1., lost, 0.),), (ROOT, "UP"): ((1., lost, 0.),)}
    oracle = ExactOracle({ROOT: "ACTIVE", lost: "LOST", won: "WON"}, rows)
    result = evaluate_local_snapshot(state, "q", ROOT, oracle)
    action = result["actions"]["LEFT"]
    assert action["q_hat"] == 1.5 and action["q_star"] == 4
    assert action["A_transition_error"] == -2.5 and action["D_continuation_error"] == 0
    assert result["identities_pass"]


def test_fixed_panel_detects_downstream_choice_change_without_expanding_or_recloning_per_state():
    state, initial_oracle, root, a, b, end = analytic_snapshot(2)
    panel = tuple(sorted((root, a)))
    new = (1, board(4))
    extra_rows = {(new, action): ((1., end, float(action == "DOWN")),)
                  for action in state.profiles[a].legal_actions}
    oracle = ExactOracle({**initial_oracle.statuses, new: "ACTIVE"}, {**initial_oracle.rows, **extra_rows})
    before = evaluate_panel(state, "q", panel, oracle)
    endpoint = state.clone()
    endpoint.observe_batch(a, "RIGHT", ((1., end, 20.),))
    endpoint.observe_batch(new, "DOWN", ((1., end, 1.),))
    original = deepcopy(endpoint.__dict__)
    after = evaluate_panel(endpoint, "q", panel, oracle)
    assert endpoint.__dict__ == original
    assert after["state_count"] == before["state_count"] == 2
    assert [row["key"] for row in after["states"]] == [[key[0], list(key[1])] for key in panel]
    assert [new[0], list(new[1])] not in [row["key"] for row in after["states"]]
    assert before["selected_optimal_count"] == 0 and after["selected_optimal_count"] == 1
    assert before["sum_local_regret"] == 1.5 and after["sum_local_regret"] == .5
    assert after["accounting"]["snapshot_clone_and_solve_work"]["branch_clones"] == 1
    assert after["accounting"]["oracle_work"]["exact_query_cache_hits"] == 1
    assert "exact_dp_state_visits" not in after["accounting"]["oracle_work"]
