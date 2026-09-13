from __future__ import annotations

import pytest

from acfqp.domains.standard_2048 import legal_actions_v1, state_from_board_v1, step_v1
from acfqp.science.controlled_predictive_2048_v1 import (
    PUBLIC_DEVELOPMENT_BOARDS,
    build_development_closure,
    run_development,
)
from acfqp.science.controlled_predictive_quotient_v1 import Query, audit_policy, compile_full_state, plan


def test_complete_closure_preserves_engine_rows_rewards_and_terminal_risk() -> None:
    """A missing spawn/action or cutoff-as-loss would corrupt quotient risk."""
    closure = build_development_closure(horizon=2)
    model = closure.model
    index = {(model.layers[state], board): state for state, board in closure.boards.items()}
    for state, board in closure.boards.items():
        if model.terminal[state] != "ACTIVE":
            assert not any(source == state for source, _ in model.rows)
            continue
        assert {action for source, action in model.rows if source == state} == {
            action.value for action in legal_actions_v1(board)
        }
        for action in legal_actions_v1(board):
            expected = step_v1(state_from_board_v1(board), action)
            actual = model.rows[state, action.value]
            assert len(actual) == len(expected)
            assert sum(row.probability for row in actual) == pytest.approx(1)
            for observed, reference in zip(actual, expected, strict=True):
                assert observed.next_state == index[model.layers[state] - 1, reference.next_state.board]
                assert observed.reward == reference.merge_score / 2048
                assert observed.probability == float(reference.probability)
    assert {"WON", "LOST", "CUTOFF"} <= set(model.terminal.values())
    assert all(len(legal_actions_v1(board)) > 1 for board in PUBLIC_DEVELOPMENT_BOARDS.values())


def test_closure_bound_fails_instead_of_changing_model_support() -> None:
    with pytest.raises(ValueError, match="no truncated model produced"):
        build_development_closure(max_nodes=3)


def test_exact_one_step_risk_and_goal_use_terminal_outcomes() -> None:
    closure = build_development_closure(horizon=1)
    model = compile_full_state(closure.model)
    query = Query(reward_weight=0, failure_penalty=1, goal_bonus=1)
    solution = plan(model, query=query)
    audit = audit_policy(closure.model, model, solution, query=query)
    risk_root, _, goal_root = closure.model.roots
    assert audit.root_metrics[risk_root]["failure"] == pytest.approx(0.9)
    assert audit.root_metrics[goal_root]["success"] == pytest.approx(1)
    assert solution.policy[model.state_to_cell[risk_root]] == "LEFT"


def test_development_report_reuses_sampling_and_separates_audit_work() -> None:
    """The runnable slice must expose matched inputs and real planning/audit costs."""
    report = run_development(horizon=1, samples_per_row=32)
    assert report["scientific_gate"] == "NOT_A_FORMAL_GATE"
    assert report["coverage"]["complete_all_legal_actions_and_outcomes"]
    assert report["construction"]["shared_empirical_draws"] == (
        32 * report["construction"]["shared_empirical_rows"]
    )
    assert len(report["queries"]) == 3
    for query in report["queries"].values():
        assert len(query["models"]) == 5
        for name, model in query["models"].items():
            assert model["ground_audit_counts"]
            assert model["planning_counts"]
            assert model["compiled_policy_evaluation_counts"]
            assert model["recovery_calls"] == 0
            assert model["exact_objective_gap_to_ground"] >= -1e-12
            for root, metrics in model["predicted_root_metrics"].items():
                assert metrics["value"] == pytest.approx(model["predicted_root_objective"][root])
                for component in ("reward", "failure", "success", "value"):
                    assert model["root_prediction_absolute_errors"][root][component] == pytest.approx(
                        abs(metrics[component] - model["exact_lifted_root_metrics"][root][component])
                    )
            if name in {"exact_ground", "oracle_exact_quotient"}:
                assert model["exact_objective_gap_to_ground"] == pytest.approx(0)
