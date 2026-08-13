"""Committed V35 target rank law, revealed after preregistration commit."""

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
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_TARGET_V35_DOMAIN,
    content_id,
)


SCHEMA_VERSION = "35.0.0"
BASE_RANK_TWO_PROBABILITY = Fraction(1, 10)
OVERRIDE_EXPRESSION_AST = {
    "operator": "COUNT_EQ",
    "vector_source": "POST_SWIPE_BOARD_RANKS",
    "constant": 2,
}
OVERRIDE_THRESHOLD = 1
OVERRIDE_RANK_TWO_PROBABILITY = Fraction(1, 4)
TARGET_KERNEL_ID = "e542f25f3929b78c3dd622beaf632df1fee75a775de99bead1232a8a8a936236"


def target_semantics_payload_v35() -> dict[str, Any]:
    return {
        "schema": "acfqp.standard_2048_adaptive_expression_target.v35",
        "schema_version": SCHEMA_VERSION,
        "spawn_rank_support": [1, 2],
        "base_rank_two_probability": BASE_RANK_TWO_PROBABILITY,
        "override_expression_ast": OVERRIDE_EXPRESSION_AST,
        "override_relation": "LESS_THAN_OR_EQUAL",
        "override_threshold": OVERRIDE_THRESHOLD,
        "override_rank_two_probability": OVERRIDE_RANK_TWO_PROBABILITY,
        "rank_one_probability_is_exact_complement": True,
    }


def target_semantics_document_v35() -> dict[str, Any]:
    payload = target_semantics_payload_v35()
    return {
        **payload,
        "target_kernel_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_TARGET_V35_DOMAIN,
            payload,
        ),
    }


def verify_target_commitment_v35() -> str:
    observed = target_semantics_document_v35()["target_kernel_id"]
    if observed != TARGET_KERNEL_ID:
        raise RuntimeError("revealed V35 target differs from its preregistered commitment")
    return observed


def query_rank_two_probability_v35(
    post_swipe_board: tuple[int, ...],
) -> Fraction:
    if (
        type(post_swipe_board) is not tuple
        or len(post_swipe_board) != 16
        or any(type(rank) is not int or rank < 0 for rank in post_swipe_board)
        or 0 not in post_swipe_board
    ):
        raise ValueError("V35 probability query requires one valid post-swipe board")
    expression_value = post_swipe_board.count(2)
    return (
        OVERRIDE_RANK_TWO_PROBABILITY
        if expression_value <= OVERRIDE_THRESHOLD
        else BASE_RANK_TWO_PROBABILITY
    )


def target_outcomes_v35(
    state: Swipe2048State, action: Swipe2048Action
) -> tuple[Swipe2048Outcome, ...]:
    post_board, merge_score, moved = swipe_board_v1(state.board, action)
    if not moved:
        raise ValueError("V35 target row requires a legal swipe")
    support = support_outcomes_v1(state, action)
    empty_count = post_board.count(0)
    if len(support) != 2 * empty_count:
        raise AssertionError("V35 target support cardinality changed")
    p2 = query_rank_two_probability_v35(post_board)
    masses = {1: 1 - p2, 2: p2}
    outcomes = tuple(
        Swipe2048Outcome(
            masses[row.spawned_rank] / empty_count,
            row.next_state,
            merge_score,
            row.spawned_cell,
            row.spawned_rank,
        )
        for row in support
    )
    if sum((row.probability for row in outcomes), Fraction()) != 1:
        raise AssertionError("V35 target outcome mass changed")
    return outcomes


verify_target_commitment_v35()


__all__ = (
    "BASE_RANK_TWO_PROBABILITY",
    "OVERRIDE_EXPRESSION_AST",
    "OVERRIDE_RANK_TWO_PROBABILITY",
    "OVERRIDE_THRESHOLD",
    "TARGET_KERNEL_ID",
    "query_rank_two_probability_v35",
    "target_outcomes_v35",
    "target_semantics_document_v35",
    "target_semantics_payload_v35",
    "verify_target_commitment_v35",
)
