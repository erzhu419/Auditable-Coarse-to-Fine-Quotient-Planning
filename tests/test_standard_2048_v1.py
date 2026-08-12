from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp.domains.g2048 import D4_ELEMENTS, D4Transform, transform_cell
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048InvariantViolation,
    boards_from_rows_v1,
    canonicalize_state_action_v1,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    swipe_board_v1,
    transform_action_v1,
    transform_board_v1,
    transform_state_v1,
)


def _board(*rows: tuple[int, int, int, int]) -> tuple[int, ...]:
    return boards_from_rows_v1(rows)


def test_standard_swipe_merges_each_tile_at_most_once() -> None:
    source = _board((1, 1, 1, 1), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    moved, score, changed = swipe_board_v1(source, Swipe2048Action.LEFT)
    assert moved[:4] == (2, 2, 0, 0)
    assert score == 8
    assert changed is True

    source = _board((1, 1, 2, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    moved, score, _ = swipe_board_v1(source, Swipe2048Action.LEFT)
    assert moved[:4] == (2, 2, 0, 0)
    assert score == 4


def test_whole_board_vertical_swipe_and_illegal_noop() -> None:
    source = _board((1, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0), (2, 0, 0, 0))
    moved, score, changed = swipe_board_v1(source, Swipe2048Action.UP)
    assert tuple(moved[index * 4] for index in range(4)) == (2, 3, 0, 0)
    assert score == 12
    assert changed is True
    assert Swipe2048Action.LEFT not in legal_actions_v1(moved)


def test_post_swipe_spawn_row_is_exact_and_normalized() -> None:
    source = state_from_board_v1(
        _board((1, 2, 3, 4), (2, 3, 4, 5), (3, 4, 5, 6), (1, 1, 2, 2))
    )
    outcomes = step_v1(source, Swipe2048Action.LEFT)
    moved = swipe_board_v1(source.board, Swipe2048Action.LEFT)[0]
    empty_count = sum(rank == 0 for rank in moved)
    assert len(outcomes) == empty_count * 2
    assert sum((row.probability for row in outcomes), Fraction()) == 1
    assert {row.spawned_rank for row in outcomes} == {1, 2}
    for cell in {row.spawned_cell for row in outcomes}:
        assert sum(
            (row.probability for row in outcomes if row.spawned_cell == cell),
            Fraction(),
        ) == Fraction(1, empty_count)


def test_d4_transport_commutes_with_swipe_and_spawn() -> None:
    source = state_from_board_v1(
        _board((1, 2, 3, 4), (2, 3, 4, 5), (3, 4, 5, 6), (1, 1, 2, 2))
    )
    for transform in D4_ELEMENTS:
        for action in legal_actions_v1(source.board):
            transformed_state = transform_state_v1(source, transform)
            transformed_action = transform_action_v1(action, transform)
            expected = {
                (
                    transform_state_v1(row.next_state, transform),
                    row.merge_score,
                    transform_cell(row.spawned_cell, 4, transform),
                    row.spawned_rank,
                    row.probability,
                )
                for row in step_v1(source, action)
            }
            actual = {
                (
                    row.next_state,
                    row.merge_score,
                    row.spawned_cell,
                    row.spawned_rank,
                    row.probability,
                )
                for row in step_v1(transformed_state, transformed_action)
            }
            assert actual == expected


def test_pair_canonicalization_is_stable_across_all_d4_images() -> None:
    source = state_from_board_v1(
        _board((1, 2, 3, 4), (2, 3, 4, 5), (3, 4, 5, 6), (1, 1, 2, 2))
    )
    canonical = canonicalize_state_action_v1(source, Swipe2048Action.LEFT)[:2]
    for transform in D4_ELEMENTS:
        image = transform_state_v1(source, transform)
        action = transform_action_v1(Swipe2048Action.LEFT, transform)
        assert canonicalize_state_action_v1(image, action)[:2] == canonical


def test_seeded_outcome_replay_is_stable_but_not_an_iid_claim() -> None:
    source = state_from_board_v1(
        _board((1, 2, 3, 4), (2, 3, 4, 5), (3, 4, 5, 6), (1, 1, 2, 2))
    )
    outcomes = step_v1(source, Swipe2048Action.LEFT)
    first = select_seeded_outcome_v1(outcomes, seed="heldout", decision_index=0)
    second = select_seeded_outcome_v1(outcomes, seed="heldout", decision_index=0)
    changed = select_seeded_outcome_v1(outcomes, seed="heldout", decision_index=1)
    assert first == second
    assert len(first[1]) == 64
    assert changed[1] != first[1]


def test_goal_and_input_boundaries_are_explicit() -> None:
    won = [0] * 16
    won[0] = GOAL_RANK
    assert state_from_board_v1(tuple(won)).status.value == "WON"
    with pytest.raises(Swipe2048InvariantViolation):
        boards_from_rows_v1(((1, 2, 3, 4),))
    with pytest.raises(Swipe2048InvariantViolation):
        swipe_board_v1(tuple([0] * 16), "LEFT")  # type: ignore[arg-type]
    assert tuple(action.value for action in ACTION_ORDER) == (
        "UP", "DOWN", "LEFT", "RIGHT"
    )
    assert transform_action_v1(Swipe2048Action.LEFT, D4Transform.ROTATE_90) is Swipe2048Action.UP
