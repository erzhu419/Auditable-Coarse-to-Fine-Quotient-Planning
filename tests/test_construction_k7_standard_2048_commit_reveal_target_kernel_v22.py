from __future__ import annotations

from fractions import Fraction

from acfqp import construction_k7_standard_2048_blind_expression_preregistration_v22 as pre
from acfqp import construction_k7_standard_2048_commit_reveal_target_kernel_v22 as kernel
from acfqp.domains.standard_2048 import Swipe2048Action, state_from_board_v1


def test_revealed_target_exactly_matches_prior_commitment() -> None:
    assert kernel.verify_target_kernel_commitment_v22() == pre.TARGET_KERNEL_COMMITMENT_ID
    assert kernel.TARGET_KERNEL_ID == pre.TARGET_KERNEL_COMMITMENT_ID
    document = kernel.kernel_semantics_document_v22()
    assert document["target_kernel_id"] == pre.TARGET_KERNEL_COMMITMENT_ID
    assert document["commit_reveal_protocol"] == (
        "TARGET_SEMANTICS_ABSENT_FROM_PREREGISTRATION_COMMIT_AND_REVEALED_ONLY_IN_SUCCESSOR_COMMIT"
    )


def test_query_interface_accepts_raw_post_swipe_board_not_named_feature() -> None:
    low_count = (0, 0, 1, 1, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7)
    high_count = (0, 1, 1, 1, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7)
    assert kernel.query_rank_two_probability_v22(low_count) == Fraction(3, 20)
    assert kernel.query_rank_two_probability_v22(high_count) == Fraction(1, 10)


def test_complete_target_row_is_normalized_and_uses_revealed_law() -> None:
    state = state_from_board_v1(
        (1, 1, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 0, 0)
    )
    outcomes = kernel.target_outcomes_v22(state, Swipe2048Action.LEFT)
    assert sum((row.probability for row in outcomes), Fraction()) == 1
    rank_two_mass = sum(row.probability for row in outcomes if row.spawned_rank == 2)
    post_board = list(outcomes[0].next_state.board)
    post_board[outcomes[0].spawned_cell] = 0
    assert rank_two_mass == kernel.query_rank_two_probability_v22(tuple(post_board))
