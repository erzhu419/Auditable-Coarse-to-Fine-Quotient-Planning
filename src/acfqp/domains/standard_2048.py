"""Exact standard 4x4 2048 swipe/spawn semantics.

This module is intentionally separate from :mod:`acfqp.domains.g2048`.
The older ``G2048-Select`` fixture chooses one adjacent pair and one survivor;
the environment below performs one ordinary whole-board UP/DOWN/LEFT/RIGHT
swipe, merges each tile at most once, and then spawns a 2 or 4 uniformly in an
empty cell.  Tile values are represented by ranks: zero is empty and rank
``r`` denotes value ``2**r``.

The module supplies exact dynamics and D4 transport only.  It does not claim a
UI adapter, an IID implementation, a learned spawn law, or completion of an
unbounded game.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Iterable

from acfqp.domains.g2048 import D4Transform, D4_ELEMENTS, transform_cell


BOARD_SIZE = 4
CELL_COUNT = BOARD_SIZE * BOARD_SIZE
GOAL_RANK = 11  # 2**11 == 2048
SPAWN_DISTRIBUTION: tuple[tuple[int, Fraction], ...] = (
    (1, Fraction(9, 10)),
    (2, Fraction(1, 10)),
)


class Swipe2048InvariantViolation(ValueError):
    """A board, action, transition, or deterministic tape is invalid."""


class Swipe2048Action(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


ACTION_ORDER: tuple[Swipe2048Action, ...] = (
    Swipe2048Action.UP,
    Swipe2048Action.DOWN,
    Swipe2048Action.LEFT,
    Swipe2048Action.RIGHT,
)


class Swipe2048Status(str, Enum):
    ACTIVE = "ACTIVE"
    WON = "WON"
    LOST = "LOST"


@dataclass(frozen=True, order=True, slots=True)
class Swipe2048State:
    board: tuple[int, ...]
    status: Swipe2048Status = Swipe2048Status.ACTIVE

    def __post_init__(self) -> None:
        validate_board_v1(self.board)
        if type(self.status) is not Swipe2048Status:
            raise Swipe2048InvariantViolation("state status must be exact")


@dataclass(frozen=True, order=True, slots=True)
class Swipe2048Outcome:
    probability: Fraction
    next_state: Swipe2048State
    merge_score: int
    spawned_cell: int
    spawned_rank: int

    def __post_init__(self) -> None:
        if not isinstance(self.probability, Fraction) or not 0 < self.probability <= 1:
            raise Swipe2048InvariantViolation("outcome probability must be exact in (0,1]")
        if type(self.next_state) is not Swipe2048State:
            raise Swipe2048InvariantViolation("outcome state must be exact")
        if type(self.merge_score) is not int or self.merge_score < 0:
            raise Swipe2048InvariantViolation("merge score must be nonnegative")
        if type(self.spawned_cell) is not int or not 0 <= self.spawned_cell < CELL_COUNT:
            raise Swipe2048InvariantViolation("spawned cell is outside the board")
        if self.spawned_rank not in (1, 2):
            raise Swipe2048InvariantViolation("spawned rank must denote a 2 or 4")


def validate_board_v1(board: tuple[int, ...]) -> tuple[int, ...]:
    if type(board) is not tuple or len(board) != CELL_COUNT:
        raise Swipe2048InvariantViolation("a standard board has exactly sixteen cells")
    if any(type(rank) is not int or rank < 0 or rank > GOAL_RANK + 8 for rank in board):
        raise Swipe2048InvariantViolation("board ranks must be bounded nonnegative integers")
    return board


def _merge_line_v1(line: tuple[int, ...]) -> tuple[tuple[int, ...], int]:
    values = [value for value in line if value]
    merged: list[int] = []
    score = 0
    index = 0
    while index < len(values):
        value = values[index]
        if index + 1 < len(values) and values[index + 1] == value:
            value += 1
            score += 1 << value
            index += 2
        else:
            index += 1
        merged.append(value)
    merged.extend([0] * (BOARD_SIZE - len(merged)))
    return tuple(merged), score


def _line_cells_v1(action: Swipe2048Action, index: int) -> tuple[int, ...]:
    if type(action) is not Swipe2048Action or type(index) is not int or not 0 <= index < 4:
        raise Swipe2048InvariantViolation("line projection input changed")
    if action is Swipe2048Action.LEFT:
        return tuple(index * 4 + column for column in range(4))
    if action is Swipe2048Action.RIGHT:
        return tuple(index * 4 + column for column in range(3, -1, -1))
    if action is Swipe2048Action.UP:
        return tuple(row * 4 + index for row in range(4))
    return tuple(row * 4 + index for row in range(3, -1, -1))


def swipe_board_v1(
    board: tuple[int, ...], action: Swipe2048Action
) -> tuple[tuple[int, ...], int, bool]:
    """Apply one standard whole-board swipe before the random spawn."""

    validate_board_v1(board)
    if type(action) is not Swipe2048Action:
        raise Swipe2048InvariantViolation("swipe action must be exact")
    result = list(board)
    score = 0
    for index in range(4):
        cells = _line_cells_v1(action, index)
        merged, line_score = _merge_line_v1(tuple(board[cell] for cell in cells))
        score += line_score
        for cell, rank in zip(cells, merged, strict=True):
            result[cell] = rank
    output = tuple(result)
    return output, score, output != board


def legal_actions_v1(board: tuple[int, ...]) -> tuple[Swipe2048Action, ...]:
    validate_board_v1(board)
    return tuple(action for action in ACTION_ORDER if swipe_board_v1(board, action)[2])


def state_from_board_v1(board: tuple[int, ...]) -> Swipe2048State:
    validate_board_v1(board)
    if max(board) >= GOAL_RANK:
        status = Swipe2048Status.WON
    elif not legal_actions_v1(board):
        status = Swipe2048Status.LOST
    else:
        status = Swipe2048Status.ACTIVE
    return Swipe2048State(board, status)


def step_v1(
    state: Swipe2048State, action: Swipe2048Action
) -> tuple[Swipe2048Outcome, ...]:
    """Return the exact post-swipe, post-spawn outcome row."""

    if type(state) is not Swipe2048State or type(action) is not Swipe2048Action:
        raise Swipe2048InvariantViolation("step requires exact state and action values")
    expected_state = state_from_board_v1(state.board)
    if expected_state.status is not state.status:
        raise Swipe2048InvariantViolation("state status disagrees with its board")
    if state.status is not Swipe2048Status.ACTIVE or action not in legal_actions_v1(state.board):
        raise Swipe2048InvariantViolation("action is not legal in this active board")
    moved, score, changed = swipe_board_v1(state.board, action)
    if not changed:
        raise AssertionError("legal action did not change the board")
    empty = tuple(index for index, rank in enumerate(moved) if rank == 0)
    if not empty:
        raise AssertionError("a legal standard swipe left no spawn cell")
    outcomes: list[Swipe2048Outcome] = []
    for cell in empty:
        for rank, rank_probability in SPAWN_DISTRIBUTION:
            spawned = list(moved)
            spawned[cell] = rank
            outcomes.append(
                Swipe2048Outcome(
                    Fraction(1, len(empty)) * rank_probability,
                    state_from_board_v1(tuple(spawned)),
                    score,
                    cell,
                    rank,
                )
            )
    if sum((row.probability for row in outcomes), Fraction()) != 1:
        raise AssertionError("standard 2048 outcome mass is not one")
    return tuple(outcomes)


_ACTION_VECTOR = {
    Swipe2048Action.UP: (-1, 0),
    Swipe2048Action.DOWN: (1, 0),
    Swipe2048Action.LEFT: (0, -1),
    Swipe2048Action.RIGHT: (0, 1),
}
_VECTOR_ACTION = {value: key for key, value in _ACTION_VECTOR.items()}


def transform_action_v1(
    action: Swipe2048Action, transform: D4Transform
) -> Swipe2048Action:
    if type(action) is not Swipe2048Action or type(transform) is not D4Transform:
        raise Swipe2048InvariantViolation("D4 action transform input changed")
    row_delta, column_delta = _ACTION_VECTOR[action]
    reflected, rotations = {
        D4Transform.IDENTITY: (False, 0),
        D4Transform.ROTATE_90: (False, 1),
        D4Transform.ROTATE_180: (False, 2),
        D4Transform.ROTATE_270: (False, 3),
        D4Transform.REFLECT: (True, 0),
        D4Transform.REFLECT_ROTATE_90: (True, 1),
        D4Transform.REFLECT_ROTATE_180: (True, 2),
        D4Transform.REFLECT_ROTATE_270: (True, 3),
    }[transform]
    if reflected:
        column_delta = -column_delta
    for _ in range(rotations):
        row_delta, column_delta = column_delta, -row_delta
    return _VECTOR_ACTION[(row_delta, column_delta)]


def transform_board_v1(
    board: tuple[int, ...], transform: D4Transform
) -> tuple[int, ...]:
    validate_board_v1(board)
    if type(transform) is not D4Transform:
        raise Swipe2048InvariantViolation("D4 board transform must be exact")
    transformed = [0] * CELL_COUNT
    for source, rank in enumerate(board):
        transformed[transform_cell(source, BOARD_SIZE, transform)] = rank
    return tuple(transformed)


def transform_state_v1(
    state: Swipe2048State, transform: D4Transform
) -> Swipe2048State:
    return state_from_board_v1(transform_board_v1(state.board, transform))


def canonicalize_state_v1(
    state: Swipe2048State,
) -> tuple[Swipe2048State, D4Transform]:
    if type(state) is not Swipe2048State:
        raise Swipe2048InvariantViolation("canonicalization requires one exact state")
    candidates = tuple(
        (transform_state_v1(state, transform), ordinal, transform)
        for ordinal, transform in enumerate(D4_ELEMENTS)
    )
    representative, _, transform = min(
        candidates,
        key=lambda row: (row[0].board, row[0].status.value, row[1]),
    )
    return representative, transform


def canonicalize_state_action_v1(
    state: Swipe2048State, action: Swipe2048Action
) -> tuple[Swipe2048State, Swipe2048Action, D4Transform]:
    if type(state) is not Swipe2048State or type(action) is not Swipe2048Action:
        raise Swipe2048InvariantViolation("pair canonicalization input changed")
    candidates = tuple(
        (
            transform_state_v1(state, transform),
            transform_action_v1(action, transform),
            ordinal,
            transform,
        )
        for ordinal, transform in enumerate(D4_ELEMENTS)
    )
    representative, transformed_action, _, transform = min(
        candidates,
        key=lambda row: (row[0].board, row[0].status.value, row[1].value, row[2]),
    )
    return representative, transformed_action, transform


def select_seeded_outcome_v1(
    outcomes: tuple[Swipe2048Outcome, ...], *, seed: str, decision_index: int
) -> tuple[Swipe2048Outcome, str]:
    """Select one exact outcome with a stable preregistered SHA-256 tape.

    The tape is deterministic replay evidence, not an IID or entropy claim.
    """

    if (
        type(outcomes) is not tuple
        or not outcomes
        or any(type(row) is not Swipe2048Outcome for row in outcomes)
        or type(seed) is not str
        or not seed
        or type(decision_index) is not int
        or decision_index < 0
    ):
        raise Swipe2048InvariantViolation("seeded outcome selection input changed")
    digest = hashlib.sha256(
        b"acfqp:standard-2048-heldout-spawn-tape:v1\x00"
        + seed.encode("utf-8")
        + b"\x00"
        + str(decision_index).encode("ascii")
    ).digest()
    threshold = Fraction(int.from_bytes(digest, "big"), 1 << 256)
    cumulative = Fraction()
    for row in outcomes:
        cumulative += row.probability
        if threshold < cumulative:
            return row, digest.hex()
    raise AssertionError("seeded threshold escaped a normalized outcome row")


def boards_from_rows_v1(rows: Iterable[Iterable[int]]) -> tuple[int, ...]:
    materialized = tuple(tuple(row) for row in rows)
    if len(materialized) != 4 or any(len(row) != 4 for row in materialized):
        raise Swipe2048InvariantViolation("standard board rows must be 4 by 4")
    return validate_board_v1(tuple(rank for row in materialized for rank in row))


__all__ = (
    "ACTION_ORDER",
    "BOARD_SIZE",
    "CELL_COUNT",
    "GOAL_RANK",
    "SPAWN_DISTRIBUTION",
    "Swipe2048Action",
    "Swipe2048InvariantViolation",
    "Swipe2048Outcome",
    "Swipe2048State",
    "Swipe2048Status",
    "boards_from_rows_v1",
    "canonicalize_state_action_v1",
    "canonicalize_state_v1",
    "legal_actions_v1",
    "select_seeded_outcome_v1",
    "state_from_board_v1",
    "step_v1",
    "swipe_board_v1",
    "transform_action_v1",
    "transform_board_v1",
    "transform_state_v1",
    "validate_board_v1",
)
