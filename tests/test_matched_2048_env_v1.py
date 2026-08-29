from __future__ import annotations

import pytest

from acfqp.domains.standard_2048 import Swipe2048Status, state_from_board_v1
from acfqp.science.matched_2048_env_v1 import (
    Matched2048EnvironmentV1Error,
    initial_state_v1,
    legal_action_mask_v1,
    transition_v1,
)


def test_initial_board_and_transition_tapes_are_stable() -> None:
    state = initial_state_v1(seed="paired-seed", episode_index=3)
    assert state == initial_state_v1(seed="paired-seed", episode_index=3)
    assert state.status is Swipe2048Status.ACTIVE
    assert sum(rank != 0 for rank in state.board) == 2
    mask = legal_action_mask_v1(state)
    action_index = mask.index(True)

    first = transition_v1(
        state,
        action_index,
        seed="paired-seed",
        episode_index=3,
        decision_index=0,
    )
    second = transition_v1(
        state,
        action_index,
        seed="paired-seed",
        episode_index=3,
        decision_index=0,
    )
    assert first == second
    assert len(first.tape_digest) == 64


def test_illegal_action_is_rejected() -> None:
    state = state_from_board_v1((1, 0, 0, 0) + (0,) * 12)
    mask = legal_action_mask_v1(state)
    assert not all(mask)
    with pytest.raises(Matched2048EnvironmentV1Error, match="illegal"):
        transition_v1(
            state,
            mask.index(False),
            seed="paired-seed",
            episode_index=9,
            decision_index=0,
        )
