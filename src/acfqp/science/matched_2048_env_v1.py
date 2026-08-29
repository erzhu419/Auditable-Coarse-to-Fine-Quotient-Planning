"""Deterministic-tape environment wrapper for matched 2048 experiments."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048State,
    Swipe2048Status,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
)


class Matched2048EnvironmentV1Error(ValueError):
    """A tape, episode, action, or transition request is invalid."""


def _digest(seed: str, episode_index: int, purpose: str) -> bytes:
    if (
        type(seed) is not str
        or not seed
        or type(episode_index) is not int
        or episode_index < 0
        or type(purpose) is not str
        or not purpose
    ):
        raise Matched2048EnvironmentV1Error("stable tape input changed")
    return hashlib.sha256(
        b"acfqp:matched-2048-environment:v1\x00"
        + purpose.encode("ascii")
        + b"\x00"
        + seed.encode("utf-8")
        + b"\x00"
        + str(episode_index).encode("ascii")
    ).digest()


def initial_state_v1(*, seed: str, episode_index: int) -> Swipe2048State:
    """Place two distinct initial tiles using a stable preregistered tape."""

    raw = _digest(seed, episode_index, "INITIAL_BOARD")
    first = int.from_bytes(raw[0:8], "big") % 16
    compressed_second = int.from_bytes(raw[8:16], "big") % 15
    second = compressed_second + (compressed_second >= first)
    first_rank = 1 if int.from_bytes(raw[16:24], "big") % 10 else 2
    second_rank = 1 if int.from_bytes(raw[24:32], "big") % 10 else 2
    board = [0] * 16
    board[first] = first_rank
    board[second] = second_rank
    return state_from_board_v1(tuple(board))


@dataclass(frozen=True, slots=True)
class Matched2048StepV1:
    state: Swipe2048State
    action_index: int
    next_state: Swipe2048State
    merge_score: int
    tape_digest: str

    @property
    def done(self) -> bool:
        return self.next_state.status is not Swipe2048Status.ACTIVE


def transition_v1(
    state: Swipe2048State,
    action_index: int,
    *,
    seed: str,
    episode_index: int,
    decision_index: int,
) -> Matched2048StepV1:
    if (
        type(state) is not Swipe2048State
        or type(action_index) is not int
        or not 0 <= action_index < len(ACTION_ORDER)
        or type(decision_index) is not int
        or decision_index < 0
    ):
        raise Matched2048EnvironmentV1Error("transition input changed")
    action = ACTION_ORDER[action_index]
    if action not in legal_actions_v1(state.board):
        raise Matched2048EnvironmentV1Error("action is illegal")
    outcome, tape_digest = select_seeded_outcome_v1(
        step_v1(state, action),
        seed=f"{seed}:episode:{episode_index}",
        decision_index=decision_index,
    )
    return Matched2048StepV1(
        state=state,
        action_index=action_index,
        next_state=outcome.next_state,
        merge_score=outcome.merge_score,
        tape_digest=tape_digest,
    )


def legal_action_mask_v1(state: Swipe2048State) -> tuple[bool, bool, bool, bool]:
    if type(state) is not Swipe2048State:
        raise Matched2048EnvironmentV1Error("legal mask requires an exact state")
    legal = set(legal_actions_v1(state.board))
    return tuple(action in legal for action in ACTION_ORDER)  # type: ignore[return-value]


__all__ = (
    "Matched2048EnvironmentV1Error",
    "Matched2048StepV1",
    "initial_state_v1",
    "legal_action_mask_v1",
    "transition_v1",
)
