"""Nonconfirmatory transition-stream control for V0-072 development.

This module is deliberately domain-separated from every registered held-out
context, environment manifest, stream, commitment, and observation.  It is
the only place where pre-anchor positive sampler tests may execute.

Nothing emitted here is admissible target evidence.  Every artifact carries
the role ``DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import combinations
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.relational_graph_core_v1 import GraphTopologyV1


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_development_synthetic_transition_control_v0"
ROLE = "DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE"
RANK_CAP = 4
HORIZON = 2

_UINT64_MODULUS = 1 << 64
_UINT64_MASK = _UINT64_MODULUS - 1
_SPLITMIX_GAMMA = 0x9E3779B97F4A7C15

DOMAIN_TAGS = {
    "anchor": "acfqp:v072-development-synthetic-anchor:v1",
    "context": "acfqp:v072-development-synthetic-context:v1",
    "state": "acfqp:v072-development-synthetic-state:v1",
    "catalogue": "acfqp:v072-development-synthetic-catalogue:v1",
    "stream": "acfqp:v072-development-synthetic-stream:v1",
    "pairing_group": (
        "acfqp:v072-development-synthetic-pairing-group:v1"
    ),
    "digest": "acfqp:v072-development-synthetic-raw-digest:v1",
    "commitment": (
        "acfqp:v072-development-synthetic-raw-commitment:v1"
    ),
    "observation": "acfqp:v072-development-synthetic-observation:v1",
    "replay": "acfqp:v072-development-synthetic-replay:v1",
    "atom": "acfqp:v072-development-synthetic-exact-atom:v1",
}


class SyntheticTransitionControlInvariantViolation(ValueError):
    """A development-only synthetic control object is invalid."""


def _content_id(
    role: str,
    payload: Mapping[str, Any],
    raw: bytes = b"",
) -> str:
    try:
        body = (
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SyntheticTransitionControlInvariantViolation(
            str(error)
        ) from error
    if raw:
        body += b"\x00" + raw
    return hashlib.sha256(body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise SyntheticTransitionControlInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise SyntheticTransitionControlInvariantViolation(
            "synthetic control arithmetic must use exact Fraction"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


SYNTHETIC_TOPOLOGY = GraphTopologyV1(
    4,
    tuple(combinations(range(4), 2)),
)
_SYNTHETIC_LAW = (
    (1, Fraction(3, 4)),
    (2, Fraction(1, 4)),
)


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticAnchorV1:
    nonce: str = "v072-development-synthetic-control-anchor-v1"
    role: str = ROLE

    def __post_init__(self) -> None:
        if (
            self.nonce
            != "v072-development-synthetic-control-anchor-v1"
            or self.role != ROLE
        ):
            raise SyntheticTransitionControlInvariantViolation(
                "synthetic development anchor changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_synthetic_anchor.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "nonce": self.nonce,
            "role": ROLE,
            "registered_target_execution_authorized": False,
        }

    @property
    def anchor_id(self) -> str:
        return _content_id("anchor", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "anchor_id": self.anchor_id}


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticContextV1:
    context_key: str = "v072_development_synthetic_k4_v0"
    topology: GraphTopologyV1 = SYNTHETIC_TOPOLOGY
    root_ranks: tuple[int, ...] = (1, 1, 2, 0)
    role: str = ROLE

    def __post_init__(self) -> None:
        if (
            self.context_key != "v072_development_synthetic_k4_v0"
            or self.topology != SYNTHETIC_TOPOLOGY
            or self.root_ranks != (1, 1, 2, 0)
            or self.role != ROLE
        ):
            raise SyntheticTransitionControlInvariantViolation(
                "synthetic context changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_synthetic_context.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context_key": self.context_key,
            "topology": self.topology.to_document(),
            "root_ranks": list(self.root_ranks),
            "horizon": HORIZON,
            "rank_cap": RANK_CAP,
            "role": ROLE,
            "hidden_law_serialized": False,
            "registered_target_context": False,
        }

    @property
    def context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticStateV1:
    ranks: tuple[int, ...]
    failure: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.ranks) is not tuple
            or len(self.ranks) != 4
            or any(
                type(rank) is not int or not 0 <= rank <= RANK_CAP
                for rank in self.ranks
            )
            or type(self.failure) is not bool
        ):
            raise SyntheticTransitionControlInvariantViolation(
                "synthetic state is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_synthetic_state.v1",
            "schema_version": SCHEMA_VERSION,
            "ranks": list(self.ranks),
            "failure": self.failure,
            "role": ROLE,
        }

    @property
    def state_id(self) -> str:
        return _content_id("state", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "state_id": self.state_id}


def _legal_actions(
    context: DevelopmentSyntheticContextV1,
    state: DevelopmentSyntheticStateV1,
) -> tuple[tuple[int, int, int], ...]:
    if state.failure:
        return ()
    return tuple(
        sorted(
            (first, second, survivor)
            for first, second in context.topology.edges
            if state.ranks[first] > 0
            and state.ranks[first] == state.ranks[second]
            for survivor in (first, second)
        )
    )


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticCatalogueV1:
    context_id: str
    state: DevelopmentSyntheticStateV1
    remaining_horizon: int
    actions: tuple[tuple[int, int, int], ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "synthetic catalogue context")
        if (
            type(self.state) is not DevelopmentSyntheticStateV1
            or self.remaining_horizon not in (1, HORIZON)
            or type(self.actions) is not tuple
            or self.actions != tuple(sorted(set(self.actions)))
        ):
            raise SyntheticTransitionControlInvariantViolation(
                "synthetic catalogue is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_synthetic_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state": self.state.to_document(),
            "remaining_horizon": self.remaining_horizon,
            "actions": [list(action) for action in self.actions],
            "role": ROLE,
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_id": self.catalogue_id}


def development_synthetic_root_catalogue_v1(
) -> tuple[
    DevelopmentSyntheticContextV1,
    DevelopmentSyntheticStateV1,
    DevelopmentSyntheticCatalogueV1,
]:
    context = DevelopmentSyntheticContextV1()
    state = DevelopmentSyntheticStateV1(context.root_ranks)
    catalogue = DevelopmentSyntheticCatalogueV1(
        context.context_id,
        state,
        HORIZON,
        _legal_actions(context, state),
    )
    return context, state, catalogue


class DevelopmentSyntheticLaneV1(str, Enum):
    DISCOVERY = "DISCOVERY"
    VALIDATION = "VALIDATION"


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticStreamSpecV1:
    anchor_id: str
    context_id: str
    catalogue_id: str
    action: tuple[int, int, int]
    arm: str
    lane: DevelopmentSyntheticLaneV1
    observer_epoch_index: int
    arm_free_support_lineage_id: str

    def __post_init__(self) -> None:
        _cid(self.anchor_id, "synthetic stream anchor")
        _cid(self.context_id, "synthetic stream context")
        _cid(self.catalogue_id, "synthetic stream catalogue")
        _cid(
            self.arm_free_support_lineage_id,
            "synthetic stream support lineage",
        )
        if (
            type(self.action) is not tuple
            or len(self.action) != 3
            or any(type(item) is not int for item in self.action)
            or self.arm not in (
                "SOURCE_CONSENSUS_PRIOR",
                "MATCHED_DIRECT_GROUND",
            )
            or type(self.lane) is not DevelopmentSyntheticLaneV1
            or self.observer_epoch_index not in (0, 1, 2)
            or (
                self.observer_epoch_index == 0
                and self.lane is not DevelopmentSyntheticLaneV1.DISCOVERY
            )
            or (
                self.observer_epoch_index > 0
                and self.lane is not DevelopmentSyntheticLaneV1.VALIDATION
            )
        ):
            raise SyntheticTransitionControlInvariantViolation(
                "synthetic stream spec is invalid"
            )

    @property
    def raw_word_pairing_group_id(self) -> str:
        return _content_id(
            "pairing_group",
            {
                "schema": (
                    "acfqp.v072_development_synthetic_pairing_group.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "anchor_id": self.anchor_id,
                "context_id": self.context_id,
                "catalogue_id": self.catalogue_id,
                "action": list(self.action),
                "lane": self.lane.value,
                "observer_epoch_index": self.observer_epoch_index,
                "arm_free_support_lineage_id": (
                    self.arm_free_support_lineage_id
                ),
                "arm_serialized": False,
                "role": ROLE,
            },
        )

    @property
    def stream_id(self) -> str:
        return _content_id(
            "stream",
            {
                "schema": (
                    "acfqp.v072_development_synthetic_stream.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "raw_word_pairing_group_id": (
                    self.raw_word_pairing_group_id
                ),
                "arm": self.arm,
                "role": ROLE,
            },
        )


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticRawCommitmentV1:
    stream_id: str
    raw_word_pairing_group_id: str
    accepted_draw_index: int
    raw_word_index: int
    raw_digest: str
    role: str = ROLE

    def __post_init__(self) -> None:
        _cid(self.stream_id, "synthetic raw stream")
        _cid(
            self.raw_word_pairing_group_id,
            "synthetic raw pairing group",
        )
        _cid(self.raw_digest, "synthetic raw digest")
        if (
            self.accepted_draw_index <= 0
            or self.raw_word_index <= 0
            or self.role != ROLE
        ):
            raise SyntheticTransitionControlInvariantViolation(
                "synthetic raw commitment is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_development_synthetic_raw_commitment.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "stream_id": self.stream_id,
            "raw_word_pairing_group_id": (
                self.raw_word_pairing_group_id
            ),
            "accepted_draw_index": self.accepted_draw_index,
            "raw_word_index": self.raw_word_index,
            "raw_digest": self.raw_digest,
            "role": ROLE,
        }

    @property
    def commitment_id(self) -> str:
        return _content_id("commitment", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "commitment_id": self.commitment_id}


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticObservationV1:
    stream_id: str
    raw_word_pairing_group_id: str
    arm: str
    lane: DevelopmentSyntheticLaneV1
    accepted_draw_index: int
    next_state: DevelopmentSyntheticStateV1
    reward: Fraction
    failure: bool
    terminal: bool
    raw_commitment: DevelopmentSyntheticRawCommitmentV1
    role: str = ROLE

    def __post_init__(self) -> None:
        _cid(self.stream_id, "synthetic observation stream")
        _cid(
            self.raw_word_pairing_group_id,
            "synthetic observation pairing group",
        )
        if (
            self.arm
            not in ("SOURCE_CONSENSUS_PRIOR", "MATCHED_DIRECT_GROUND")
            or type(self.lane) is not DevelopmentSyntheticLaneV1
            or self.accepted_draw_index <= 0
            or type(self.next_state) is not DevelopmentSyntheticStateV1
            or type(self.reward) is not Fraction
            or self.failure != self.next_state.failure
            or type(self.terminal) is not bool
            or type(self.raw_commitment)
            is not DevelopmentSyntheticRawCommitmentV1
            or self.raw_commitment.stream_id != self.stream_id
            or self.raw_commitment.raw_word_pairing_group_id
            != self.raw_word_pairing_group_id
            or self.raw_commitment.accepted_draw_index
            != self.accepted_draw_index
            or self.role != ROLE
        ):
            raise SyntheticTransitionControlInvariantViolation(
                "synthetic observation is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_development_synthetic_observation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "stream_id": self.stream_id,
            "raw_word_pairing_group_id": (
                self.raw_word_pairing_group_id
            ),
            "arm": self.arm,
            "lane": self.lane.value,
            "accepted_draw_index": self.accepted_draw_index,
            "next_state": self.next_state.to_document(),
            "reward": _fdoc(self.reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "raw_commitment": self.raw_commitment.to_document(),
            "role": ROLE,
            "registered_target_evidence": False,
        }

    @property
    def observation_id(self) -> str:
        return _content_id("observation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observation_id": self.observation_id}


def _splitmix64(value: int) -> int:
    word = value & _UINT64_MASK
    word = (word ^ (word >> 30)) * 0xBF58476D1CE4E5B9
    word &= _UINT64_MASK
    word = (word ^ (word >> 27)) * 0x94D049BB133111EB
    word &= _UINT64_MASK
    return (word ^ (word >> 31)) & _UINT64_MASK


def _merged_row(
    context: DevelopmentSyntheticContextV1,
    catalogue: DevelopmentSyntheticCatalogueV1,
    action: tuple[int, int, int],
) -> tuple[tuple[int, ...], tuple[int, ...], Fraction]:
    if action not in catalogue.actions:
        raise SyntheticTransitionControlInvariantViolation(
            "synthetic action is not legal"
        )
    first, second, survivor = action
    rank = catalogue.state.ranks[first]
    board = list(catalogue.state.ranks)
    board[first] = 0
    board[second] = 0
    board[survivor] = min(rank + 1, RANK_CAP)
    empty = tuple(index for index, value in enumerate(board) if value == 0)
    reward = Fraction(2 ** (rank + 1), 2 ** (RANK_CAP + 1)) / HORIZON
    return tuple(board), empty, reward


class DevelopmentSyntheticTransitionStreamV1:
    __slots__ = (
        "_context",
        "_catalogue",
        "_spec",
        "_board",
        "_empty",
        "_reward",
        "_seed",
        "_draws",
    )

    def __init__(
        self,
        anchor: DevelopmentSyntheticAnchorV1,
        context: DevelopmentSyntheticContextV1,
        catalogue: DevelopmentSyntheticCatalogueV1,
        action: tuple[int, int, int],
        arm: str,
        lane: DevelopmentSyntheticLaneV1,
        observer_epoch_index: int,
        arm_free_support_lineage_id: str,
    ) -> None:
        if (
            type(anchor) is not DevelopmentSyntheticAnchorV1
            or type(context) is not DevelopmentSyntheticContextV1
            or type(catalogue) is not DevelopmentSyntheticCatalogueV1
            or catalogue.context_id != context.context_id
        ):
            raise SyntheticTransitionControlInvariantViolation(
                "synthetic stream binding is invalid"
            )
        self._context = context
        self._catalogue = catalogue
        self._spec = DevelopmentSyntheticStreamSpecV1(
            anchor.anchor_id,
            context.context_id,
            catalogue.catalogue_id,
            action,
            arm,
            lane,
            observer_epoch_index,
            arm_free_support_lineage_id,
        )
        self._board, self._empty, self._reward = _merged_row(
            context,
            catalogue,
            action,
        )
        self._seed = int.from_bytes(
            hashlib.sha256(
                b"acfqp:v072-development-synthetic-seed:v1\x00"
                + self._spec.raw_word_pairing_group_id.encode("ascii")
            ).digest()[:8],
            "big",
        )
        self._draws = 0

    @property
    def stream_id(self) -> str:
        return self._spec.stream_id

    @property
    def raw_word_pairing_group_id(self) -> str:
        return self._spec.raw_word_pairing_group_id

    def draw(self) -> DevelopmentSyntheticObservationV1:
        self._draws += 1
        word = _splitmix64(
            self._seed + _SPLITMIX_GAMMA * self._draws
        )
        denominator = len(self._empty) * 4
        token = word % denominator
        empty_index = token // 4
        rank_token = token % 4
        spawn_rank = 1 if rank_token < 3 else 2
        successor = list(self._board)
        successor[self._empty[empty_index]] = spawn_rank
        provisional = DevelopmentSyntheticStateV1(tuple(successor))
        failure = not _legal_actions(self._context, provisional)
        next_state = DevelopmentSyntheticStateV1(
            tuple(successor),
            failure,
        )
        terminal = (
            failure or self._catalogue.remaining_horizon == 1
        )
        raw_digest = _content_id(
            "digest",
            {
                "schema": (
                    "acfqp.v072_development_synthetic_raw_digest.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "stream_id": self._spec.stream_id,
                "raw_word_pairing_group_id": (
                    self._spec.raw_word_pairing_group_id
                ),
                "accepted_draw_index": self._draws,
                "next_state": next_state.to_document(),
                "reward": _fdoc(self._reward),
                "failure": failure,
                "terminal": terminal,
                "role": ROLE,
            },
            word.to_bytes(8, "big"),
        )
        commitment = DevelopmentSyntheticRawCommitmentV1(
            self._spec.stream_id,
            self._spec.raw_word_pairing_group_id,
            self._draws,
            self._draws,
            raw_digest,
        )
        return DevelopmentSyntheticObservationV1(
            self._spec.stream_id,
            self._spec.raw_word_pairing_group_id,
            self._spec.arm,
            self._spec.lane,
            self._draws,
            next_state,
            self._reward,
            failure,
            terminal,
            commitment,
        )


def open_development_synthetic_stream_v1(
    anchor: DevelopmentSyntheticAnchorV1,
    context: DevelopmentSyntheticContextV1,
    catalogue: DevelopmentSyntheticCatalogueV1,
    action: tuple[int, int, int],
    arm: str,
    lane: DevelopmentSyntheticLaneV1,
    observer_epoch_index: int,
    arm_free_support_lineage_id: str,
) -> DevelopmentSyntheticTransitionStreamV1:
    return DevelopmentSyntheticTransitionStreamV1(
        anchor,
        context,
        catalogue,
        action,
        arm,
        lane,
        observer_epoch_index,
        arm_free_support_lineage_id,
    )


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticReplayV1:
    observation_id: str
    replayed_draws: int
    role: str = ROLE

    def __post_init__(self) -> None:
        _cid(self.observation_id, "synthetic replay observation")
        if self.replayed_draws <= 0 or self.role != ROLE:
            raise SyntheticTransitionControlInvariantViolation(
                "synthetic replay is invalid"
            )

    @property
    def replay_id(self) -> str:
        return _content_id(
            "replay",
            {
                "schema": "acfqp.v072_development_synthetic_replay.v1",
                "schema_version": SCHEMA_VERSION,
                "observation_id": self.observation_id,
                "replayed_draws": self.replayed_draws,
                "role": ROLE,
            },
        )


def verify_development_synthetic_observation_v1(
    anchor: DevelopmentSyntheticAnchorV1,
    context: DevelopmentSyntheticContextV1,
    catalogue: DevelopmentSyntheticCatalogueV1,
    action: tuple[int, int, int],
    arm: str,
    lane: DevelopmentSyntheticLaneV1,
    observer_epoch_index: int,
    arm_free_support_lineage_id: str,
    observation: DevelopmentSyntheticObservationV1,
) -> DevelopmentSyntheticReplayV1:
    if type(observation) is not DevelopmentSyntheticObservationV1:
        raise SyntheticTransitionControlInvariantViolation(
            "synthetic replay requires a canonical observation"
        )
    stream = open_development_synthetic_stream_v1(
        anchor,
        context,
        catalogue,
        action,
        arm,
        lane,
        observer_epoch_index,
        arm_free_support_lineage_id,
    )
    replayed: DevelopmentSyntheticObservationV1 | None = None
    for _ in range(observation.accepted_draw_index):
        replayed = stream.draw()
    if (
        replayed is None
        or replayed.to_document() != observation.to_document()
    ):
        raise SyntheticTransitionControlInvariantViolation(
            "synthetic observation differs from raw replay"
        )
    return DevelopmentSyntheticReplayV1(
        observation.observation_id,
        observation.accepted_draw_index,
    )


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticExactAtomV1:
    next_state: DevelopmentSyntheticStateV1
    probability: Fraction
    reward: Fraction
    failure: bool
    terminal: bool
    execution_lane: str = "DEVELOPMENT_EVALUATION_ONLY"
    role: str = ROLE

    def __post_init__(self) -> None:
        if (
            type(self.next_state) is not DevelopmentSyntheticStateV1
            or type(self.probability) is not Fraction
            or not 0 < self.probability <= 1
            or type(self.reward) is not Fraction
            or self.failure != self.next_state.failure
            or self.execution_lane != "DEVELOPMENT_EVALUATION_ONLY"
            or self.role != ROLE
        ):
            raise SyntheticTransitionControlInvariantViolation(
                "synthetic exact atom is invalid"
            )

    @property
    def atom_id(self) -> str:
        return _content_id(
            "atom",
            {
                "schema": (
                    "acfqp.v072_development_synthetic_exact_atom.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "next_state": self.next_state.to_document(),
                "probability": _fdoc(self.probability),
                "reward": _fdoc(self.reward),
                "failure": self.failure,
                "terminal": self.terminal,
                "execution_lane": self.execution_lane,
                "role": ROLE,
            },
        )


def development_evaluation_only_exact_atoms_v1(
    anchor: DevelopmentSyntheticAnchorV1,
    context: DevelopmentSyntheticContextV1,
    catalogue: DevelopmentSyntheticCatalogueV1,
    action: tuple[int, int, int],
) -> tuple[DevelopmentSyntheticExactAtomV1, ...]:
    if type(anchor) is not DevelopmentSyntheticAnchorV1:
        raise SyntheticTransitionControlInvariantViolation(
            "synthetic exact atoms require the synthetic anchor"
        )
    board, empty, reward = _merged_row(context, catalogue, action)
    atoms: list[DevelopmentSyntheticExactAtomV1] = []
    for cell in empty:
        for rank, probability in _SYNTHETIC_LAW:
            successor = list(board)
            successor[cell] = rank
            provisional = DevelopmentSyntheticStateV1(tuple(successor))
            failure = not _legal_actions(context, provisional)
            next_state = DevelopmentSyntheticStateV1(
                tuple(successor),
                failure,
            )
            atoms.append(
                DevelopmentSyntheticExactAtomV1(
                    next_state,
                    Fraction(1, len(empty)) * probability,
                    reward,
                    failure,
                    failure or catalogue.remaining_horizon == 1,
                )
            )
    if sum((atom.probability for atom in atoms), Fraction(0)) != 1:
        raise RuntimeError("synthetic exact atom row is not normalized")
    return tuple(atoms)


__all__ = [
    "DevelopmentSyntheticAnchorV1",
    "DevelopmentSyntheticCatalogueV1",
    "DevelopmentSyntheticContextV1",
    "DevelopmentSyntheticExactAtomV1",
    "DevelopmentSyntheticLaneV1",
    "DevelopmentSyntheticObservationV1",
    "DevelopmentSyntheticRawCommitmentV1",
    "DevelopmentSyntheticReplayV1",
    "DevelopmentSyntheticStateV1",
    "DevelopmentSyntheticStreamSpecV1",
    "DevelopmentSyntheticTransitionStreamV1",
    "PROFILE_KEY",
    "ROLE",
    "SyntheticTransitionControlInvariantViolation",
    "development_evaluation_only_exact_atoms_v1",
    "development_synthetic_root_catalogue_v1",
    "open_development_synthetic_stream_v1",
    "verify_development_synthetic_observation_v1",
]
