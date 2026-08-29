from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp.domains import standard_2048
from acfqp.domains.standard_2048 import (
    Swipe2048InvariantViolation,
    Swipe2048State,
    Swipe2048Status,
    state_from_board_v1,
)
from acfqp.science.latent_resource_2048_v1 import (
    KNOWN_MODEL_RESOURCE_FEATURE_NAMES_V1,
    KNOWN_MODEL_RESOURCE_VECTOR_DIMENSION_V1,
    RAW_FEATURE_NAMES_V1,
    RAW_VECTOR_DIMENSION_V1,
    RESOURCE_FEATURE_NAMES_V1,
    RESOURCE_VECTOR_DIMENSION_V1,
    STATE_ONLY_RESOURCE_FEATURE_NAMES_V1,
    STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1,
    Standard2048LatentResourceRepresentationV1,
    encode_standard_2048_board_v1,
    encode_standard_2048_known_model_board_v1,
    encode_standard_2048_state_only_board_v1,
    encode_standard_2048_state_only_state_v1,
    encode_standard_2048_state_v1,
    state_only_resource_standard_2048_vector_v1,
)


def _snake_board_v1() -> tuple[int, ...]:
    path = (0, 1, 2, 3, 7, 6, 5, 4, 8, 9, 10, 11, 15, 14, 13, 12)
    board = [0] * 16
    for cell, rank in zip(path, range(10, 0, -1), strict=False):
        board[cell] = rank
    return tuple(board)


def test_raw_and_resource_layouts_are_exact_and_deterministic() -> None:
    board = _snake_board_v1()
    first = encode_standard_2048_board_v1(board)
    second = encode_standard_2048_board_v1(board)

    assert first == second
    assert first.raw_vector == board
    assert RAW_VECTOR_DIMENSION_V1 == len(RAW_FEATURE_NAMES_V1) == 16
    assert RESOURCE_VECTOR_DIMENSION_V1 == len(RESOURCE_FEATURE_NAMES_V1) == 16
    assert len(first.resource_vector) == 16
    assert all(type(value) is Fraction for value in first.resource_vector)
    assert all(Fraction(0) <= value <= Fraction(1) for value in first.resource_vector[:8])
    assert all(Fraction(-1) <= value <= Fraction(1) for value in first.resource_vector[8:12])
    assert all(Fraction(0) <= value <= Fraction(1) for value in first.resource_vector[12:])


def test_corner_anchor_and_order_expose_the_hidden_resource() -> None:
    anchored = _snake_board_v1()
    displaced = list(anchored)
    displaced[0], displaced[5] = displaced[5], displaced[0]

    anchored_vector = encode_standard_2048_board_v1(anchored).resource_vector
    displaced_vector = encode_standard_2048_board_v1(tuple(displaced)).resource_vector

    assert anchored_vector[1] == Fraction(1)
    assert displaced_vector[1] == Fraction(0)
    assert anchored_vector[2] > displaced_vector[2]
    assert anchored_vector[7] < displaced_vector[7]


def test_empty_slack_merge_potential_and_continuation_are_explicit() -> None:
    board = (
        3, 2, 1, 0,
        3, 2, 1, 0,
        0, 0, 0, 0,
        0, 0, 0, 0,
    )
    vector = encode_standard_2048_board_v1(board).resource_vector

    assert vector[4] == Fraction(10, 16)
    assert vector[5] == Fraction(3, 8)
    assert vector[6] == Fraction(3, 4)


def test_each_action_has_delta_and_risk_and_illegal_action_is_unavailable() -> None:
    board = (
        3, 2, 1, 0,
        0, 0, 0, 0,
        0, 0, 0, 0,
        0, 0, 0, 0,
    )
    vector = encode_standard_2048_board_v1(board).resource_vector
    delta_up, delta_down, delta_left, delta_right = vector[8:12]
    risk_up, risk_down, risk_left, risk_right = vector[12:16]

    assert delta_up == delta_left == Fraction(0)
    assert risk_up == risk_left == Fraction(1)
    assert Fraction(-1) <= delta_down <= Fraction(1)
    assert Fraction(-1) <= delta_right <= Fraction(1)
    assert Fraction(0) <= risk_down < Fraction(1)
    assert Fraction(0) <= risk_right < Fraction(1)


def test_terminal_and_status_inconsistent_inputs_are_handled_exactly() -> None:
    empty = (0,) * 16
    encoded = encode_standard_2048_board_v1(empty)
    assert encoded.resource_vector[8:12] == (Fraction(0),) * 4
    assert encoded.resource_vector[12:16] == (Fraction(1),) * 4

    inconsistent = Swipe2048State(empty, Swipe2048Status.ACTIVE)
    with pytest.raises(Swipe2048InvariantViolation, match="status disagrees"):
        encode_standard_2048_state_v1(inconsistent)
    with pytest.raises(Swipe2048InvariantViolation):
        encode_standard_2048_board_v1([0] * 16)  # type: ignore[arg-type]


def test_representation_constructor_rejects_non_exact_or_out_of_range_values() -> None:
    valid = encode_standard_2048_state_v1(state_from_board_v1(_snake_board_v1()))
    with pytest.raises(Swipe2048InvariantViolation, match="exact fractions"):
        Standard2048LatentResourceRepresentationV1(
            valid.raw_vector, tuple(float(value) for value in valid.resource_vector)  # type: ignore[arg-type]
        )
    invalid = list(valid.resource_vector)
    invalid[12] = Fraction(2)
    with pytest.raises(Swipe2048InvariantViolation, match="escaped"):
        Standard2048LatentResourceRepresentationV1(valid.raw_vector, tuple(invalid))


def test_state_only_layout_is_exact_bounded_and_deterministic() -> None:
    board = _snake_board_v1()
    first = encode_standard_2048_state_only_board_v1(board)
    second = state_only_resource_standard_2048_vector_v1(board)

    assert first.raw_vector == board
    assert first.resource_vector == second
    assert (
        STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1
        == len(STATE_ONLY_RESOURCE_FEATURE_NAMES_V1)
        == len(second)
        == 16
    )
    assert all(type(value) is Fraction for value in second)
    assert all(Fraction(0) <= value <= Fraction(1) for value in second)


def test_state_only_features_are_current_board_geometry() -> None:
    board = (
        3, 2, 1, 0,
        3, 2, 1, 0,
        0, 0, 0, 0,
        0, 0, 0, 0,
    )
    vector = state_only_resource_standard_2048_vector_v1(board)

    assert vector[4] == Fraction(10, 16)
    assert vector[5] == Fraction(3, 24)
    assert vector[6] == Fraction(1, 2)
    assert vector[8:12] == (
        Fraction(3, 12),
        Fraction(3, 12),
        Fraction(0),
        Fraction(0),
    )
    assert vector[12:16] == (
        Fraction(0),
        Fraction(1),
        Fraction(0),
        Fraction(1),
    )


def test_state_only_encoder_never_calls_or_projects_dynamics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    board = (
        3, 2, 1, 0,
        3, 2, 1, 0,
        0, 0, 0, 0,
        0, 0, 0, 0,
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("state-only encoder consulted transition dynamics")

    for name in (
        "step_v1",
        "support_outcomes_v1",
        "swipe_board_v1",
        "legal_actions_v1",
        "state_from_board_v1",
    ):
        monkeypatch.setattr(standard_2048, name, forbidden)

    encoded_board = encode_standard_2048_state_only_board_v1(board)
    encoded_state = encode_standard_2048_state_only_state_v1(
        Swipe2048State(board, Swipe2048Status.ACTIVE)
    )
    assert encoded_board == encoded_state


def test_state_only_status_validation_is_direct_and_exact() -> None:
    lost_board = (
        1, 2, 3, 4,
        2, 3, 4, 1,
        3, 4, 1, 2,
        4, 1, 2, 3,
    )
    encoded = encode_standard_2048_state_only_state_v1(
        Swipe2048State(lost_board, Swipe2048Status.LOST)
    )
    assert encoded.raw_vector == lost_board
    with pytest.raises(Swipe2048InvariantViolation, match="directly inspected"):
        encode_standard_2048_state_only_state_v1(
            Swipe2048State(lost_board, Swipe2048Status.ACTIVE)
        )


def test_original_encoder_has_an_explicit_known_model_positive_control_name() -> None:
    board = _snake_board_v1()
    assert KNOWN_MODEL_RESOURCE_FEATURE_NAMES_V1 is RESOURCE_FEATURE_NAMES_V1
    assert KNOWN_MODEL_RESOURCE_VECTOR_DIMENSION_V1 == RESOURCE_VECTOR_DIMENSION_V1
    assert encode_standard_2048_known_model_board_v1(
        board
    ) == encode_standard_2048_board_v1(board)
