from __future__ import annotations

from fractions import Fraction

from acfqp import construction_k7_standard_2048_commit_reveal_target_kernel_v22 as target
from acfqp import construction_k7_standard_2048_expression_planner_v1 as planner
from acfqp.domains.standard_2048 import (
    Swipe2048Action,
    select_seeded_outcome_v1,
    state_from_board_v1,
)


EXPRESSION = {
    "operator": "COUNT_EQ",
    "vector_source": "POST_SWIPE_BOARD_RANKS",
    "constant": 1,
}
CONFIG = {
    "expression_ast": EXPRESSION,
    "threshold": 2,
    "base_probability": Fraction(1, 10),
    "override_probability": Fraction(3, 20),
    "horizon": 3,
}


def test_persistent_session_preserves_exact_values_and_reuses_subproofs() -> None:
    state = state_from_board_v1((1, 1) + (0,) * 14)
    session = planner.create_expression_planning_session_v1(**CONFIG)
    first = session.plan_root(state)
    outcome, _ = select_seeded_outcome_v1(
        target.target_outcomes_v22(state, Swipe2048Action(first["selected_action"])),
        seed="expression-planner-session-v1-test",
        decision_index=0,
    )
    reused = session.plan_root(outcome.next_state)
    stateless = planner.plan_expression_world_model_root_v1(outcome.next_state, **CONFIG)
    assert reused["root_action_exact_values"] == stateless["root_action_exact_values"]
    assert reused["selected_action"] == stateless["selected_action"]
    assert reused["selected_expected_merge_score"] == stateless["selected_expected_merge_score"]
    assert reused["selected_loss_probability_within_horizon"] == stateless[
        "selected_loss_probability_within_horizon"
    ]
    assert reused["factored_action_row_evaluation_count"] < stateless[
        "factored_action_row_evaluation_count"
    ]
    assert reused["subproof_cache_miss_count"] < stateless["subproof_cache_miss_count"]
    assert reused["cross_decision_subproof_cache_hit_count"] > 0
    assert reused["cumulative_subproof_cache_hit_count"] > reused["subproof_cache_hit_count"]
    assert reused["persistent_subproof_cache_entry_count"] > 0
    assert reused["target_transition_accessed"] is False
