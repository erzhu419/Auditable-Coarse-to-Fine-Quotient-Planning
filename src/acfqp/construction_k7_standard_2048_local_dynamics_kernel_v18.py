"""Fresh dense-frontier 2048 dynamics used by the V18 recovery Gate.

This module is the target environment, not the planning model.  The planner
may query its rank law only after a failed applicability certificate, while
target execution and standalone evaluation use the complete outcome row.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from acfqp.domains.standard_2048 import (
    Swipe2048Action,
    Swipe2048Outcome,
    Swipe2048State,
    support_outcomes_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_KERNEL_V18_DOMAIN,
    content_id,
)


SCHEMA_VERSION = "18.0.0"
BASE_RANK_TWO_PROBABILITY = Fraction(1, 10)
DENSE_EMPTY_COUNT_THRESHOLD = 4
DENSE_RANK_TWO_PROBABILITY = Fraction(1, 5)
TARGET_KERNEL_ID = "84d799a915676cee6ded5fac11597386a26c10c213c09a64164eb9a13e811d8a"


def kernel_semantics_document_v18() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_local_repair_target_kernel.v18",
        "schema_version": SCHEMA_VERSION,
        "board_shape": [4, 4],
        "deterministic_swipe_semantics": "STANDARD_2048_WHOLE_BOARD_SWIPE_V1",
        "spawn_cell_law": "UNIFORM_OVER_POST_SWIPE_EMPTY_CELLS",
        "rank_two_law": {
            "base_probability": BASE_RANK_TWO_PROBABILITY,
            "override_predicate": "POST_SWIPE_EMPTY_COUNT_LE_THRESHOLD",
            "override_threshold": DENSE_EMPTY_COUNT_THRESHOLD,
            "override_probability": DENSE_RANK_TWO_PROBABILITY,
        },
        "outcome_order": "ASCENDING_CELL_THEN_ASCENDING_RANK",
        "exact_rational_arithmetic": True,
    }
    return {
        **payload,
        "target_kernel_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_KERNEL_V18_DOMAIN,
            payload,
        ),
    }


def verify_target_kernel_identity_v18() -> str:
    document = kernel_semantics_document_v18()
    if document["target_kernel_id"] != TARGET_KERNEL_ID:
        raise RuntimeError("V18 target kernel identity changed")
    return TARGET_KERNEL_ID


def query_rank_two_probability_v18(empty_count: int) -> Fraction:
    """Return one exact ground distinction for an authorized recovery query."""

    if type(empty_count) is not int or not 1 <= empty_count <= 16:
        raise ValueError("empty-count query is outside the registered board")
    return (
        DENSE_RANK_TWO_PROBABILITY
        if empty_count <= DENSE_EMPTY_COUNT_THRESHOLD
        else BASE_RANK_TWO_PROBABILITY
    )


def target_outcomes_v18(
    state: Swipe2048State, action: Swipe2048Action
) -> tuple[Swipe2048Outcome, ...]:
    """Return the complete exact target row for execution or evaluation."""

    support = support_outcomes_v1(state, action)
    empty_count = len(support) // 2
    probability_two = query_rank_two_probability_v18(empty_count)
    by_rank = {1: 1 - probability_two, 2: probability_two}
    outcomes = tuple(
        Swipe2048Outcome(
            by_rank[row.spawned_rank] / empty_count,
            row.next_state,
            row.merge_score,
            row.spawned_cell,
            row.spawned_rank,
        )
        for row in support
    )
    if sum((row.probability for row in outcomes), Fraction()) != 1:
        raise AssertionError("V18 target outcome mass changed")
    return outcomes


verify_target_kernel_identity_v18()


__all__ = (
    "BASE_RANK_TWO_PROBABILITY",
    "DENSE_EMPTY_COUNT_THRESHOLD",
    "DENSE_RANK_TWO_PROBABILITY",
    "TARGET_KERNEL_ID",
    "kernel_semantics_document_v18",
    "query_rank_two_probability_v18",
    "target_outcomes_v18",
    "verify_target_kernel_identity_v18",
)
