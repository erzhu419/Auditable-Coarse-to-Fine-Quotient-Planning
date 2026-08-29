"""Auditable raw and latent-resource representations for standard 2048.

The raw vector retains the sixteen board ranks without preprocessing.  Two
scientifically distinct resource vectors are exposed.  The state-only vector
is computed directly from the current board and never applies the transition
model or enumerates a successor.  The known-model vector is the original
positive control: its final eight coordinates use exact one-step outcomes
under the public spawn law from ``standard_2048``.

All derived values are :class:`fractions.Fraction` objects.  Consequently the
representation is deterministic and contains no platform-dependent floating
point reductions.  State-only coordinates all lie in ``[0, 1]``.  Known-model
global resources and action risks lie in ``[0, 1]``; its action deltas lie in
``[-1, 1]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from acfqp.domains import standard_2048


RAW_VECTOR_DIMENSION_V1 = standard_2048.CELL_COUNT
RESOURCE_VECTOR_DIMENSION_V1 = 16
KNOWN_MODEL_RESOURCE_VECTOR_DIMENSION_V1 = RESOURCE_VECTOR_DIMENSION_V1
STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1 = 16

RAW_FEATURE_NAMES_V1: tuple[str, ...] = tuple(
    f"cell_{row}_{column}_rank"
    for row in range(standard_2048.BOARD_SIZE)
    for column in range(standard_2048.BOARD_SIZE)
)

_ACTION_SUFFIXES = tuple(action.value.lower() for action in standard_2048.ACTION_ORDER)
RESOURCE_FEATURE_NAMES_V1: tuple[str, ...] = (
    "max_rank_goal_progress",
    "max_tile_corner_anchor",
    "snake_order",
    "monotonic_order",
    "empty_slack",
    "merge_potential",
    "legal_continuation_reserve",
    "irreversibility_anchor_displacement_risk",
    *(f"expected_resource_quality_delta_{suffix}" for suffix in _ACTION_SUFFIXES),
    *(f"expected_resource_loss_risk_{suffix}" for suffix in _ACTION_SUFFIXES),
)
KNOWN_MODEL_RESOURCE_FEATURE_NAMES_V1 = RESOURCE_FEATURE_NAMES_V1
STATE_ONLY_RESOURCE_FEATURE_NAMES_V1: tuple[str, ...] = (
    "max_rank_goal_progress",
    "max_tile_corner_anchor",
    "snake_order",
    "monotonic_order",
    "empty_slack",
    "visible_adjacent_merge_density",
    "directional_flow_liquidity",
    "current_irreversibility_risk",
    *(f"visible_merge_opportunity_{suffix}" for suffix in _ACTION_SUFFIXES),
    *(f"flow_liquidity_{suffix}" for suffix in _ACTION_SUFFIXES),
)

_ZERO = Fraction(0)
_ONE = Fraction(1)
_CORNER_CELLS = (0, 3, 12, 15)
_MAX_NEAREST_CORNER_DISTANCE = max(
    min(
        abs(index // standard_2048.BOARD_SIZE - corner // standard_2048.BOARD_SIZE)
        + abs(index % standard_2048.BOARD_SIZE - corner % standard_2048.BOARD_SIZE)
        for corner in _CORNER_CELLS
    )
    for index in range(standard_2048.CELL_COUNT)
)


def _row_snake_from_top_left_v1() -> tuple[int, ...]:
    return tuple(
        row * standard_2048.BOARD_SIZE + column
        for row in range(standard_2048.BOARD_SIZE)
        for column in (
            range(standard_2048.BOARD_SIZE)
            if row % 2 == 0
            else range(standard_2048.BOARD_SIZE - 1, -1, -1)
        )
    )


def _transpose_path_v1(path: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        (cell % standard_2048.BOARD_SIZE) * standard_2048.BOARD_SIZE
        + cell // standard_2048.BOARD_SIZE
        for cell in path
    )


_BASE_SNAKE = _row_snake_from_top_left_v1()
_MIRRORED_SNAKE = tuple(
    cell // standard_2048.BOARD_SIZE * standard_2048.BOARD_SIZE
    + (standard_2048.BOARD_SIZE - 1 - cell % standard_2048.BOARD_SIZE)
    for cell in _BASE_SNAKE
)
_SNAKE_PATHS = tuple(
    dict.fromkeys(
        (
            _BASE_SNAKE,
            tuple(reversed(_BASE_SNAKE)),
            _MIRRORED_SNAKE,
            tuple(reversed(_MIRRORED_SNAKE)),
            _transpose_path_v1(_BASE_SNAKE),
            tuple(reversed(_transpose_path_v1(_BASE_SNAKE))),
            _transpose_path_v1(_MIRRORED_SNAKE),
            tuple(reversed(_transpose_path_v1(_MIRRORED_SNAKE))),
        )
    )
)

if len(RAW_FEATURE_NAMES_V1) != RAW_VECTOR_DIMENSION_V1:
    raise AssertionError("raw 2048 feature layout changed")
if len(RESOURCE_FEATURE_NAMES_V1) != RESOURCE_VECTOR_DIMENSION_V1:
    raise AssertionError("resource 2048 feature layout changed")
if (
    len(STATE_ONLY_RESOURCE_FEATURE_NAMES_V1)
    != STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1
):
    raise AssertionError("state-only resource 2048 feature layout changed")
if len(_SNAKE_PATHS) != 8:
    raise AssertionError("the eight corner-oriented snake paths changed")


@dataclass(frozen=True, slots=True)
class Standard2048LatentResourceRepresentationV1:
    """Original known-model positive-control representation.

    The final eight coordinates query exact one-step public dynamics.  This
    class remains under its original name for runtime compatibility; new
    experiments should identify it as the known-model positive control.
    """

    raw_vector: tuple[int, ...]
    resource_vector: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        standard_2048.validate_board_v1(self.raw_vector)
        if len(self.raw_vector) != RAW_VECTOR_DIMENSION_V1:
            raise standard_2048.Swipe2048InvariantViolation(
                "raw 2048 vector dimension changed"
            )
        if (
            type(self.resource_vector) is not tuple
            or len(self.resource_vector) != RESOURCE_VECTOR_DIMENSION_V1
            or any(type(value) is not Fraction for value in self.resource_vector)
        ):
            raise standard_2048.Swipe2048InvariantViolation(
                "resource 2048 vector must contain sixteen exact fractions"
            )
        bounded_zero_one = self.resource_vector[:8] + self.resource_vector[12:]
        if any(not _ZERO <= value <= _ONE for value in bounded_zero_one):
            raise standard_2048.Swipe2048InvariantViolation(
                "resource or risk feature escaped [0,1]"
            )
        if any(not -_ONE <= value <= _ONE for value in self.resource_vector[8:12]):
            raise standard_2048.Swipe2048InvariantViolation(
                "action resource delta escaped [-1,1]"
            )


@dataclass(frozen=True, slots=True)
class Standard2048StateOnlyLatentResourceRepresentationV1:
    """One raw/state-only resource pair computed from the current board."""

    raw_vector: tuple[int, ...]
    resource_vector: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        standard_2048.validate_board_v1(self.raw_vector)
        if len(self.raw_vector) != RAW_VECTOR_DIMENSION_V1:
            raise standard_2048.Swipe2048InvariantViolation(
                "raw 2048 vector dimension changed"
            )
        if (
            type(self.resource_vector) is not tuple
            or len(self.resource_vector) != STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1
            or any(type(value) is not Fraction for value in self.resource_vector)
        ):
            raise standard_2048.Swipe2048InvariantViolation(
                "state-only resource vector must contain sixteen exact fractions"
            )
        if any(not _ZERO <= value <= _ONE for value in self.resource_vector):
            raise standard_2048.Swipe2048InvariantViolation(
                "state-only resource feature escaped [0,1]"
            )


Standard2048KnownModelLatentResourceRepresentationV1 = (
    Standard2048LatentResourceRepresentationV1
)


@dataclass(frozen=True, slots=True)
class _CoreResourcesV1:
    max_rank_goal_progress: Fraction
    max_tile_corner_anchor: Fraction
    snake_order: Fraction
    monotonic_order: Fraction
    empty_slack: Fraction
    merge_potential: Fraction
    legal_continuation_reserve: Fraction
    irreversibility_anchor_displacement_risk: Fraction

    def as_vector(self) -> tuple[Fraction, ...]:
        return (
            self.max_rank_goal_progress,
            self.max_tile_corner_anchor,
            self.snake_order,
            self.monotonic_order,
            self.empty_slack,
            self.merge_potential,
            self.legal_continuation_reserve,
            self.irreversibility_anchor_displacement_risk,
        )

    def quality(self) -> Fraction:
        positive = self.as_vector()[:7] + (
            _ONE - self.irreversibility_anchor_displacement_risk,
        )
        return sum(positive, _ZERO) / len(positive)


def _validate_state_v1(
    state: standard_2048.Swipe2048State,
) -> standard_2048.Swipe2048State:
    if type(state) is not standard_2048.Swipe2048State:
        raise standard_2048.Swipe2048InvariantViolation(
            "latent-resource encoding requires one exact standard 2048 state"
        )
    expected = standard_2048.state_from_board_v1(state.board)
    if state != expected:
        raise standard_2048.Swipe2048InvariantViolation(
            "state status disagrees with the standard 2048 board"
        )
    return state


def _tile_values_v1(board: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(0 if rank == 0 else 1 << rank for rank in board)


def _max_tile_corner_anchor_v1(board: tuple[int, ...]) -> Fraction:
    maximum = max(board)
    if maximum == 0:
        return _ZERO
    maximum_cells = tuple(index for index, rank in enumerate(board) if rank == maximum)
    corner_count = sum(index in _CORNER_CELLS for index in maximum_cells)
    return Fraction(corner_count, len(maximum_cells))


def _anchor_displacement_v1(board: tuple[int, ...]) -> Fraction:
    maximum = max(board)
    if maximum == 0:
        return _ZERO
    maximum_cells = tuple(index for index, rank in enumerate(board) if rank == maximum)
    distance = sum(
        min(
            abs(index // standard_2048.BOARD_SIZE - corner // standard_2048.BOARD_SIZE)
            + abs(index % standard_2048.BOARD_SIZE - corner % standard_2048.BOARD_SIZE)
            for corner in _CORNER_CELLS
        )
        for index in maximum_cells
    )
    return Fraction(distance, len(maximum_cells) * _MAX_NEAREST_CORNER_DISTANCE)


def _snake_order_v1(board: tuple[int, ...]) -> Fraction:
    values = _tile_values_v1(board)
    if not any(values):
        return _ZERO
    position_weights = tuple(range(standard_2048.CELL_COUNT, 0, -1))
    ideal = sum(
        value * weight
        for value, weight in zip(
            sorted(values, reverse=True), position_weights, strict=True
        )
    )
    observed = max(
        sum(values[cell] * weight for cell, weight in zip(path, position_weights, strict=True))
        for path in _SNAKE_PATHS
    )
    score = Fraction(observed, ideal)
    if not _ZERO <= score <= _ONE:
        raise AssertionError("snake order escaped its exact bound")
    return score


def _monotonic_order_v1(board: tuple[int, ...]) -> Fraction:
    values = _tile_values_v1(board)
    if not any(values):
        return _ZERO
    variation = sum(
        abs(values[row * 4 + column] - values[row * 4 + column + 1])
        for row in range(4)
        for column in range(3)
    ) + sum(
        abs(values[row * 4 + column] - values[(row + 1) * 4 + column])
        for row in range(3)
        for column in range(4)
    )
    if variation == 0:
        return _ONE

    scores: list[Fraction] = []
    for corner_row in (0, 3):
        rows = range(4) if corner_row == 0 else range(3, -1, -1)
        for corner_column in (0, 3):
            columns = range(4) if corner_column == 0 else range(3, -1, -1)
            violation = sum(
                max(0, values[row * 4 + far] - values[row * 4 + near])
                for row in range(4)
                for near, far in zip(columns, tuple(columns)[1:])
            ) + sum(
                max(0, values[far * 4 + column] - values[near * 4 + column])
                for column in range(4)
                for near, far in zip(rows, tuple(rows)[1:])
            )
            scores.append(_ONE - Fraction(violation, variation))
    score = max(scores)
    if not _ZERO <= score <= _ONE:
        raise AssertionError("monotonic order escaped its exact bound")
    return score


_HORIZONTAL_EDGES_V1 = tuple(
    (
        row * standard_2048.BOARD_SIZE + column,
        row * standard_2048.BOARD_SIZE + column + 1,
    )
    for row in range(standard_2048.BOARD_SIZE)
    for column in range(standard_2048.BOARD_SIZE - 1)
)
_VERTICAL_EDGES_V1 = tuple(
    (
        row * standard_2048.BOARD_SIZE + column,
        (row + 1) * standard_2048.BOARD_SIZE + column,
    )
    for row in range(standard_2048.BOARD_SIZE - 1)
    for column in range(standard_2048.BOARD_SIZE)
)
_GRID_EDGES_V1 = _HORIZONTAL_EDGES_V1 + _VERTICAL_EDGES_V1


def _matching_edge_count_v1(
    board: tuple[int, ...], edges: tuple[tuple[int, int], ...]
) -> int:
    """Count currently adjacent, equal, occupied pairs without projecting a move."""

    return sum(
        board[left] != 0 and board[left] == board[right]
        for left, right in edges
    )


def _visible_merge_opportunities_v1(board: tuple[int, ...]) -> tuple[Fraction, ...]:
    vertical = Fraction(_matching_edge_count_v1(board, _VERTICAL_EDGES_V1), 12)
    horizontal = Fraction(_matching_edge_count_v1(board, _HORIZONTAL_EDGES_V1), 12)
    vertical_actions = (
        standard_2048.Swipe2048Action.UP,
        standard_2048.Swipe2048Action.DOWN,
    )
    return tuple(
        vertical if action in vertical_actions else horizontal
        for action in standard_2048.ACTION_ORDER
    )


def _cells_toward_edge_v1(
    cell: int, action: standard_2048.Swipe2048Action
) -> tuple[int, ...]:
    row, column = divmod(cell, standard_2048.BOARD_SIZE)
    if action is standard_2048.Swipe2048Action.UP:
        return tuple(other * 4 + column for other in range(row))
    if action is standard_2048.Swipe2048Action.DOWN:
        return tuple(other * 4 + column for other in range(row + 1, 4))
    if action is standard_2048.Swipe2048Action.LEFT:
        return tuple(row * 4 + other for other in range(column))
    return tuple(row * 4 + other for other in range(column + 1, 4))


def _flow_liquidity_v1(board: tuple[int, ...]) -> tuple[Fraction, ...]:
    """Fraction of occupied tiles with a currently empty cell toward each edge."""

    occupied = tuple(cell for cell, rank in enumerate(board) if rank != 0)
    if not occupied:
        return (_ZERO,) * len(standard_2048.ACTION_ORDER)
    return tuple(
        Fraction(
            sum(
                any(
                    board[target] == 0
                    for target in _cells_toward_edge_v1(cell, action)
                )
                for cell in occupied
            ),
            len(occupied),
        )
        for action in standard_2048.ACTION_ORDER
    )


def _state_only_status_from_board_v1(
    board: tuple[int, ...],
) -> standard_2048.Swipe2048Status:
    """Derive status by direct board inspection, without legal-action enumeration."""

    standard_2048.validate_board_v1(board)
    if max(board) >= standard_2048.GOAL_RANK:
        return standard_2048.Swipe2048Status.WON
    if any(board) and (
        0 in board or _matching_edge_count_v1(board, _GRID_EDGES_V1) > 0
    ):
        return standard_2048.Swipe2048Status.ACTIVE
    return standard_2048.Swipe2048Status.LOST


def _state_only_resource_vector_from_board_v1(
    board: tuple[int, ...],
) -> tuple[Fraction, ...]:
    standard_2048.validate_board_v1(board)
    maximum = max(board)
    snake = _snake_order_v1(board)
    monotonic = _monotonic_order_v1(board)
    empty_slack = Fraction(board.count(0), standard_2048.CELL_COUNT)
    visible_merge_density = Fraction(
        _matching_edge_count_v1(board, _GRID_EDGES_V1), len(_GRID_EDGES_V1)
    )
    merge_opportunities = _visible_merge_opportunities_v1(board)
    flow_liquidity = _flow_liquidity_v1(board)
    mean_liquidity = sum(flow_liquidity, _ZERO) / len(flow_liquidity)
    ordering_loss = _ONE - (snake + monotonic) / 2
    irreversibility = (
        _anchor_displacement_v1(board) + ordering_loss + (_ONE - mean_liquidity)
    ) / 3
    vector = (
        Fraction(min(maximum, standard_2048.GOAL_RANK), standard_2048.GOAL_RANK),
        _max_tile_corner_anchor_v1(board),
        snake,
        monotonic,
        empty_slack,
        visible_merge_density,
        mean_liquidity,
        irreversibility,
        *merge_opportunities,
        *flow_liquidity,
    )
    if len(vector) != STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1:
        raise AssertionError("state-only resource vector dimension changed")
    return vector


def _merge_potential_v1(board: tuple[int, ...]) -> Fraction:
    occupied = sum(rank != 0 for rank in board)
    maximum_merges = max(
        occupied
        - sum(rank != 0 for rank in standard_2048.swipe_board_v1(board, action)[0])
        for action in standard_2048.ACTION_ORDER
    )
    return Fraction(maximum_merges, standard_2048.CELL_COUNT // 2)


def _core_resources_v1(board: tuple[int, ...]) -> _CoreResourcesV1:
    standard_2048.validate_board_v1(board)
    maximum = max(board)
    anchor = _max_tile_corner_anchor_v1(board)
    snake = _snake_order_v1(board)
    monotonic = _monotonic_order_v1(board)
    displacement = _anchor_displacement_v1(board)
    ordering_loss = _ONE - (snake + monotonic) / 2
    irreversibility = (displacement + ordering_loss) / 2
    return _CoreResourcesV1(
        max_rank_goal_progress=Fraction(
            min(maximum, standard_2048.GOAL_RANK), standard_2048.GOAL_RANK
        ),
        max_tile_corner_anchor=anchor,
        snake_order=snake,
        monotonic_order=monotonic,
        empty_slack=Fraction(board.count(0), standard_2048.CELL_COUNT),
        merge_potential=_merge_potential_v1(board),
        legal_continuation_reserve=Fraction(
            len(standard_2048.legal_actions_v1(board)),
            len(standard_2048.ACTION_ORDER),
        ),
        irreversibility_anchor_displacement_risk=irreversibility,
    )


def _positive_drop_v1(before: Fraction, after: Fraction) -> Fraction:
    return max(_ZERO, before - after)


def _outcome_loss_risk_v1(
    before: _CoreResourcesV1,
    outcome: standard_2048.Swipe2048Outcome,
    after: _CoreResourcesV1,
) -> Fraction:
    terminal_loss = Fraction(
        outcome.next_state.status is standard_2048.Swipe2048Status.LOST
    )
    losses = (
        after.irreversibility_anchor_displacement_risk,
        _positive_drop_v1(before.max_tile_corner_anchor, after.max_tile_corner_anchor),
        _positive_drop_v1(before.snake_order, after.snake_order),
        _positive_drop_v1(before.monotonic_order, after.monotonic_order),
        _positive_drop_v1(before.empty_slack, after.empty_slack),
        _positive_drop_v1(
            before.legal_continuation_reserve, after.legal_continuation_reserve
        ),
        terminal_loss,
    )
    return sum(losses, _ZERO) / len(losses)


def _action_features_v1(
    state: standard_2048.Swipe2048State,
    core: _CoreResourcesV1,
) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]]:
    legal = (
        frozenset(standard_2048.legal_actions_v1(state.board))
        if state.status is standard_2048.Swipe2048Status.ACTIVE
        else frozenset()
    )
    deltas: list[Fraction] = []
    risks: list[Fraction] = []
    for action in standard_2048.ACTION_ORDER:
        if action not in legal:
            deltas.append(_ZERO)
            risks.append(_ONE)
            continue
        outcomes = standard_2048.step_v1(state, action)
        after_rows = tuple(
            (outcome, _core_resources_v1(outcome.next_state.board))
            for outcome in outcomes
        )
        expected_quality = sum(
            outcome.probability * after.quality() for outcome, after in after_rows
        )
        expected_risk = sum(
            outcome.probability * _outcome_loss_risk_v1(core, outcome, after)
            for outcome, after in after_rows
        )
        deltas.append(expected_quality - core.quality())
        risks.append(expected_risk)
    return tuple(deltas), tuple(risks)


def raw_standard_2048_vector_v1(
    state: standard_2048.Swipe2048State,
) -> tuple[int, ...]:
    """Return the lossless row-major rank observation."""

    return _validate_state_v1(state).board


def resource_standard_2048_vector_v1(
    state: standard_2048.Swipe2048State,
) -> tuple[Fraction, ...]:
    """Return the original known-model positive-control resource vector."""

    state = _validate_state_v1(state)
    core = _core_resources_v1(state.board)
    deltas, risks = _action_features_v1(state, core)
    vector = core.as_vector() + deltas + risks
    if len(vector) != RESOURCE_VECTOR_DIMENSION_V1:
        raise AssertionError("resource vector dimension changed")
    return vector


def encode_standard_2048_state_v1(
    state: standard_2048.Swipe2048State,
) -> Standard2048LatentResourceRepresentationV1:
    """Encode a state with the original known-model positive control."""

    state = _validate_state_v1(state)
    return Standard2048LatentResourceRepresentationV1(
        raw_standard_2048_vector_v1(state),
        resource_standard_2048_vector_v1(state),
    )


def encode_standard_2048_board_v1(
    board: tuple[int, ...],
) -> Standard2048LatentResourceRepresentationV1:
    """Validate a board and apply the original known-model positive control."""

    standard_2048.validate_board_v1(board)
    return encode_standard_2048_state_v1(standard_2048.state_from_board_v1(board))


def known_model_resource_standard_2048_vector_v1(
    state: standard_2048.Swipe2048State,
) -> tuple[Fraction, ...]:
    """Explicitly named access to the known-model positive-control vector."""

    return resource_standard_2048_vector_v1(state)


def encode_standard_2048_known_model_state_v1(
    state: standard_2048.Swipe2048State,
) -> Standard2048KnownModelLatentResourceRepresentationV1:
    """Explicitly encode a state with the known-model positive control."""

    return encode_standard_2048_state_v1(state)


def encode_standard_2048_known_model_board_v1(
    board: tuple[int, ...],
) -> Standard2048KnownModelLatentResourceRepresentationV1:
    """Explicitly encode a board with the known-model positive control."""

    return encode_standard_2048_board_v1(board)


def state_only_resource_standard_2048_vector_v1(
    board: tuple[int, ...],
) -> tuple[Fraction, ...]:
    """Return sixteen features computed only by inspecting ``board``.

    This function does not call the transition model, project a swipe, enumerate
    legal actions, or enumerate successor states.  Its action-labelled values
    are current directional geometry, not predicted action outcomes.
    """

    return _state_only_resource_vector_from_board_v1(board)


def encode_standard_2048_state_only_board_v1(
    board: tuple[int, ...],
) -> Standard2048StateOnlyLatentResourceRepresentationV1:
    """Encode a board without consulting standard-2048 transition dynamics."""

    standard_2048.validate_board_v1(board)
    return Standard2048StateOnlyLatentResourceRepresentationV1(
        raw_vector=board,
        resource_vector=_state_only_resource_vector_from_board_v1(board),
    )


def encode_standard_2048_state_only_state_v1(
    state: standard_2048.Swipe2048State,
) -> Standard2048StateOnlyLatentResourceRepresentationV1:
    """Encode a status-consistent state using direct board inspection only."""

    if type(state) is not standard_2048.Swipe2048State:
        raise standard_2048.Swipe2048InvariantViolation(
            "state-only encoding requires one exact standard 2048 state"
        )
    expected_status = _state_only_status_from_board_v1(state.board)
    if state.status is not expected_status:
        raise standard_2048.Swipe2048InvariantViolation(
            "state status disagrees with the directly inspected 2048 board"
        )
    return encode_standard_2048_state_only_board_v1(state.board)


__all__ = (
    "KNOWN_MODEL_RESOURCE_FEATURE_NAMES_V1",
    "KNOWN_MODEL_RESOURCE_VECTOR_DIMENSION_V1",
    "RAW_FEATURE_NAMES_V1",
    "RAW_VECTOR_DIMENSION_V1",
    "RESOURCE_FEATURE_NAMES_V1",
    "RESOURCE_VECTOR_DIMENSION_V1",
    "STATE_ONLY_RESOURCE_FEATURE_NAMES_V1",
    "STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1",
    "Standard2048KnownModelLatentResourceRepresentationV1",
    "Standard2048LatentResourceRepresentationV1",
    "Standard2048StateOnlyLatentResourceRepresentationV1",
    "encode_standard_2048_board_v1",
    "encode_standard_2048_known_model_board_v1",
    "encode_standard_2048_known_model_state_v1",
    "encode_standard_2048_state_only_board_v1",
    "encode_standard_2048_state_only_state_v1",
    "encode_standard_2048_state_v1",
    "known_model_resource_standard_2048_vector_v1",
    "raw_standard_2048_vector_v1",
    "resource_standard_2048_vector_v1",
    "state_only_resource_standard_2048_vector_v1",
)
