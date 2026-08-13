"""Target dynamics revealed only after the V22 commitment commit."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from acfqp.domains.standard_2048 import (
    Swipe2048Action,
    Swipe2048Outcome,
    Swipe2048State,
    support_outcomes_v1,
    swipe_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_COMMIT_REVEAL_TARGET_KERNEL_V22_DOMAIN,
    content_id,
)


SCHEMA_VERSION = "22.0.0"
BASE_RANK_TWO_PROBABILITY = Fraction(1, 10)
OVERRIDE_THRESHOLD = 2
OVERRIDE_RANK_TWO_PROBABILITY = Fraction(3, 20)
TARGET_KERNEL_ID = "9c40dc9f4a33d2f8bdb008aad5af3fc43be228c7fb964cf137c53af03e962eb5"


def kernel_semantics_document_v22() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_commit_reveal_target_kernel.v22",
        "schema_version": SCHEMA_VERSION,
        "board_shape": [4, 4],
        "deterministic_swipe_semantics": "STANDARD_2048_WHOLE_BOARD_SWIPE_V1",
        "spawn_cell_law": "UNIFORM_OVER_POST_SWIPE_EMPTY_CELLS",
        "rank_two_law": {
            "base_probability": BASE_RANK_TWO_PROBABILITY,
            "override_expression_ast": {
                "operator": "COUNT_EQ",
                "vector_source": "POST_SWIPE_BOARD_RANKS",
                "constant": 1,
            },
            "override_predicate": "EXPRESSION_VALUE_LE_THRESHOLD",
            "override_threshold": OVERRIDE_THRESHOLD,
            "override_probability": OVERRIDE_RANK_TWO_PROBABILITY,
        },
        "outcome_order": "ASCENDING_CELL_THEN_ASCENDING_RANK",
        "exact_rational_arithmetic": True,
        "commit_reveal_protocol": (
            "TARGET_SEMANTICS_ABSENT_FROM_PREREGISTRATION_COMMIT_AND_REVEALED_ONLY_IN_SUCCESSOR_COMMIT"
        ),
    }
    return {
        **payload,
        "target_kernel_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_COMMIT_REVEAL_TARGET_KERNEL_V22_DOMAIN,
            payload,
        ),
    }


def verify_target_kernel_commitment_v22() -> str:
    if kernel_semantics_document_v22()["target_kernel_id"] != TARGET_KERNEL_ID:
        raise RuntimeError("revealed V22 target does not match the frozen commitment")
    return TARGET_KERNEL_ID


def query_rank_two_probability_v22(post_swipe_board: tuple[int, ...]) -> Fraction:
    """Return one label for an already-frozen raw post-swipe context."""

    if (
        type(post_swipe_board) is not tuple
        or len(post_swipe_board) != 16
        or any(type(rank) is not int or rank < 0 for rank in post_swipe_board)
        or 0 not in post_swipe_board
    ):
        raise ValueError("V22 query requires one valid post-swipe board with empty support")
    expression_value = post_swipe_board.count(1)
    return (
        OVERRIDE_RANK_TWO_PROBABILITY
        if expression_value <= OVERRIDE_THRESHOLD
        else BASE_RANK_TWO_PROBABILITY
    )


def target_outcomes_v22(
    state: Swipe2048State, action: Swipe2048Action
) -> tuple[Swipe2048Outcome, ...]:
    """Return the complete revealed target row for execution or evaluation."""

    post_board, merge_score, moved = swipe_board_v1(state.board, action)
    if not moved:
        raise ValueError("V22 target row requires a legal swipe")
    support = support_outcomes_v1(state, action)
    empty_count = post_board.count(0)
    if len(support) != 2 * empty_count:
        raise AssertionError("V22 target support cardinality changed")
    p2 = query_rank_two_probability_v22(post_board)
    by_rank = {1: 1 - p2, 2: p2}
    outcomes = tuple(
        Swipe2048Outcome(
            by_rank[row.spawned_rank] / empty_count,
            row.next_state,
            merge_score,
            row.spawned_cell,
            row.spawned_rank,
        )
        for row in support
    )
    if sum((row.probability for row in outcomes), Fraction()) != 1:
        raise AssertionError("V22 target outcome mass changed")
    return outcomes


verify_target_kernel_commitment_v22()


__all__ = (
    "BASE_RANK_TWO_PROBABILITY",
    "OVERRIDE_RANK_TWO_PROBABILITY",
    "OVERRIDE_THRESHOLD",
    "TARGET_KERNEL_ID",
    "kernel_semantics_document_v22",
    "query_rank_two_probability_v22",
    "target_outcomes_v22",
    "verify_target_kernel_commitment_v22",
)
