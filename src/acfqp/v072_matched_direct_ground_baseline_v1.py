"""Strict matched-direct H=2 observation/planning baseline for V0-072.

The registered arm remains locked.  The executable development control uses
real immutable row transcripts, confidence snapshots, interval projections,
the direct-only cold-model builder, the exact-lazy ground planner, and its
independent proof verifier.

The schedule is deliberately rigid:

* every physical row is observed at 64 discovery + 2,048 validation draws;
* all rows synchronously extend to 4,096, 8,192, then 16,384 validation draws;
* a complete direct model is built only after every row reaches a checkpoint;
* the first independently verified sound certificate stops acquisition; and
* failure at 16,384 is a typed noncertificate, never exact-law supplemented.

No quotient, source prior, selected-row acquisition, local promotion,
fallback, or hidden exact evaluator is available on this path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import exact_lazy_h2_independent_verifier_v1 as lazy_independent
from acfqp import exact_lazy_h2_robust_planner_v1 as lazy
from acfqp import partial_support_confidence_v2 as confidence
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import row_bound_observation_core_v2 as row_core
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_v1 as closure
from acfqp import v072_cold_h2_model_builders_v1 as model_builders
from acfqp import (
    v072_cold_h2_model_builders_independent_verifier_v1
    as model_independent,
)
from acfqp import v072_confidence_row_projection_v1 as projection
from acfqp import (
    v072_confidence_row_projection_independent_verifier_v1
    as projection_independent,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_matched_direct_ground_baseline_v1"
ARM = "MATCHED_DIRECT_GROUND"
CHECKPOINTS = (2_048, 4_096, 8_192, 16_384)
DISCOVERY_DRAWS_PER_ROW = 64
REGISTERED_TARGET_EXECUTION_STATUS = "LOCKED_NONAUTHORIZING_DRAFT"
ROLE = row_core.DEVELOPMENT_ROLE


class V072MatchedDirectGroundInvariantViolation(ValueError):
    """A schedule, row lineage, model, proof, or work claim is invalid."""


class RegisteredMatchedDirectGroundExecutionLockedV1(RuntimeError):
    """The registered target lacks a final execution anchor."""


class DevelopmentMatchedDirectLawV1(str, Enum):
    """Disjoint deterministic controls; neither is confirmatory evidence."""

    FAILURE_RESIDUE_1_OF_100 = "FAILURE_RESIDUE_1_OF_100"
    FAILURE_RESIDUE_3_OF_100 = "FAILURE_RESIDUE_3_OF_100"

    @property
    def failure_residues_per_hundred(self) -> int:
        return 1 if self is self.FAILURE_RESIDUE_1_OF_100 else 3


class MatchedDirectCheckpointStatusV1(str, Enum):
    CERTIFIED = "CERTIFIED"
    NOT_CERTIFIED = "NOT_CERTIFIED"
    SOLVER_RESOURCE_EXHAUSTED = "SOLVER_RESOURCE_EXHAUSTED"


class MatchedDirectTerminalClassV1(str, Enum):
    PLAN_CERTIFICATE = "PLAN_CERTIFICATE"
    ATTEMPT_CLOSURE_NONCERTIFICATE = "ATTEMPT_CLOSURE_NONCERTIFICATE"


class MatchedDirectTerminalCodeV1(str, Enum):
    MATCHED_DIRECT_GROUND_CERTIFIED = "MATCHED_DIRECT_GROUND_CERTIFIED"
    MAXIMUM_DIRECT_CHECKPOINT_EXHAUSTED = (
        "MAXIMUM_DIRECT_CHECKPOINT_EXHAUSTED"
    )
    EXACT_LAZY_RESOURCE_EXHAUSTED = "EXACT_LAZY_RESOURCE_EXHAUSTED"


DOMAIN_TAGS = {
    "backend": "acfqp:v072-matched-direct-development-backend:v1",
    "context": "acfqp:v072-matched-direct-development-context:v1",
    "state": "acfqp:v072-matched-direct-development-state:v1",
    "action": "acfqp:v072-matched-direct-development-action:v1",
    "row": "acfqp:v072-matched-direct-development-row:v1",
    "support_semantics": (
        "acfqp:v072-matched-direct-development-support-semantics:v1"
    ),
    "support_chain": (
        "acfqp:v072-matched-direct-development-support-chain:v1"
    ),
    "stream": "acfqp:v072-matched-direct-development-stream:v1",
    "descriptor": "acfqp:v072-matched-direct-development-descriptor:v1",
    "raw_digest": "acfqp:v072-matched-direct-development-raw-digest:v1",
    "commitment": "acfqp:v072-matched-direct-development-commitment:v1",
    "source_observation": (
        "acfqp:v072-matched-direct-development-source-observation:v1"
    ),
    "replay": "acfqp:v072-matched-direct-row-replay:v1",
    "acquisition": "acfqp:v072-matched-direct-row-acquisition:v1",
    "checkpoint": "acfqp:v072-matched-direct-checkpoint-evidence:v1",
    "work": "acfqp:v072-matched-direct-checkpoint-work:v1",
    "record": "acfqp:v072-matched-direct-checkpoint-record:v1",
    "run": "acfqp:v072-matched-direct-run:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("matched-direct content domains must be unique")


def _content_id(
    role: str,
    payload: Mapping[str, Any],
    *,
    raw_suffix: bytes = b"",
) -> str:
    try:
        data = (
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        )
    except (KeyError, TypeError, ValueError) as error:
        raise V072MatchedDirectGroundInvariantViolation(str(error)) from error
    if raw_suffix:
        data += b"\x00" + raw_suffix
    return hashlib.sha256(data).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072MatchedDirectGroundInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072MatchedDirectGroundInvariantViolation(
            "matched-direct arithmetic must use exact Fraction"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _backend_domain_id() -> str:
    return _content_id(
        "backend",
        {
            "schema": "acfqp.v072_matched_direct_development_backend.v1",
            "schema_version": SCHEMA_VERSION,
            "law": (
                "COUNTER_PREFIX_FAILURE_RESIDUES_MOD_100_"
                "DEVELOPMENT_NONCONFIRMATORY"
            ),
            "formal_exact_iid_claimed": False,
            "registered_target_evidence": False,
        },
    )


def development_matched_direct_context_id_v1() -> str:
    return _content_id(
        "context",
        {
            "schema": "acfqp.v072_matched_direct_development_context.v1",
            "schema_version": SCHEMA_VERSION,
            "root_ranks": [1, 1, 2, 0],
            "child_ranks": [2, 0, 1, 1],
            "horizon": 2,
            "rank_cap": 4,
            "physical_row_count": 2,
            "registered_target_evidence": False,
        },
    )


@dataclass(frozen=True, slots=True)
class DevelopmentMatchedDirectPhysicalRowV1:
    row_key: str
    remaining_horizon: int
    state_ranks: tuple[int, ...]
    action: tuple[int, int, int]
    success_next_ranks: tuple[int, ...]
    _state_semantic_id: str = field(init=False, repr=False)
    _action_semantic_id: str = field(init=False, repr=False)
    _arm_free_row_id: str = field(init=False, repr=False)
    _physical_row_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.row_key not in ("ROOT", "CHILD")
            or self.remaining_horizon not in (1, 2)
            or type(self.state_ranks) is not tuple
            or len(self.state_ranks) != 4
            or any(type(rank) is not int or not 0 <= rank <= 4 for rank in self.state_ranks)
            or type(self.action) is not tuple
            or len(self.action) != 3
            or any(type(item) is not int for item in self.action)
            or type(self.success_next_ranks) is not tuple
            or len(self.success_next_ranks) != 4
            or any(
                type(rank) is not int or not 0 <= rank <= 4
                for rank in self.success_next_ranks
            )
        ):
            raise V072MatchedDirectGroundInvariantViolation(
                "development physical row schema is invalid"
            )
        first, second, survivor = self.action
        if (
            min(first, second, survivor) < 0
            or max(first, second, survivor) >= len(self.state_ranks)
            or first == second
            or survivor not in (first, second)
            or self.state_ranks[first] <= 0
            or self.state_ranks[first] != self.state_ranks[second]
            or (self.row_key == "ROOT") != (self.remaining_horizon == 2)
        ):
            raise V072MatchedDirectGroundInvariantViolation(
                "development physical row is not one legal H2 row"
            )
        context_id = development_matched_direct_context_id_v1()
        state_id = _content_id(
            "state",
            {
                "schema": "acfqp.v072_matched_direct_development_state.v1",
                "schema_version": SCHEMA_VERSION,
                "context_id": context_id,
                "row_key": self.row_key,
                "remaining_horizon": self.remaining_horizon,
                "ranks": list(self.state_ranks),
            },
        )
        action_id = _content_id(
            "action",
            {
                "schema": "acfqp.v072_matched_direct_development_action.v1",
                "schema_version": SCHEMA_VERSION,
                "context_id": context_id,
                "state_semantic_id": state_id,
                "remaining_horizon": self.remaining_horizon,
                "action": list(self.action),
            },
        )
        arm_free = _content_id(
            "row",
            {
                "schema": "acfqp.v072_matched_direct_arm_free_row.v1",
                "schema_version": SCHEMA_VERSION,
                "context_id": context_id,
                "state_semantic_id": state_id,
                "action_semantic_id": action_id,
                "remaining_horizon": self.remaining_horizon,
            },
        )
        physical = _content_id(
            "row",
            {
                "schema": "acfqp.v072_matched_direct_physical_row.v1",
                "schema_version": SCHEMA_VERSION,
                "arm_free_row_id": arm_free,
                "ground_row_semantics": "STATE_ACTION_REMAINING_HORIZON",
            },
        )
        object.__setattr__(self, "_state_semantic_id", state_id)
        object.__setattr__(self, "_action_semantic_id", action_id)
        object.__setattr__(self, "_arm_free_row_id", arm_free)
        object.__setattr__(self, "_physical_row_id", physical)

    @property
    def context_id(self) -> str:
        return development_matched_direct_context_id_v1()

    @property
    def state_semantic_id(self) -> str:
        return self._state_semantic_id

    @property
    def action_semantic_id(self) -> str:
        return self._action_semantic_id

    @property
    def arm_free_row_id(self) -> str:
        return self._arm_free_row_id

    @property
    def physical_row_id(self) -> str:
        return self._physical_row_id

    @property
    def exact_row_reward(self) -> Fraction:
        rank = self.state_ranks[self.action[0]]
        return Fraction(2 ** (rank + 1), 2 ** 5) / 2

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_matched_direct_physical_row_record.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "row_key": self.row_key,
            "state_semantic_id": self.state_semantic_id,
            "action_semantic_id": self.action_semantic_id,
            "arm_free_row_id": self.arm_free_row_id,
            "physical_row_id": self.physical_row_id,
            "remaining_horizon": self.remaining_horizon,
            "state_ranks": list(self.state_ranks),
            "action": list(self.action),
            "success_next_ranks": list(self.success_next_ranks),
            "exact_row_reward": _fdoc(self.exact_row_reward),
            "registered_target_evidence": False,
        }

    @property
    def row_record_id(self) -> str:
        return _content_id("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_record_id": self.row_record_id}


def development_matched_direct_physical_rows_v1(
) -> tuple[DevelopmentMatchedDirectPhysicalRowV1, ...]:
    root = DevelopmentMatchedDirectPhysicalRowV1(
        "ROOT",
        2,
        (1, 1, 2, 0),
        (0, 1, 0),
        (2, 0, 1, 1),
    )
    child = DevelopmentMatchedDirectPhysicalRowV1(
        "CHILD",
        1,
        (2, 0, 1, 1),
        (2, 3, 2),
        (2, 0, 2, 0),
    )
    return tuple(sorted((root, child), key=lambda item: item.physical_row_id))


def _public_state(row: DevelopmentMatchedDirectPhysicalRowV1) -> closure.ColdPublicStateV1:
    return closure.ColdPublicStateV1(
        row.state_semantic_id,
        {
            "schema": "acfqp.v072_matched_direct_public_state.v1",
            "context_id": row.context_id,
            "row_key": row.row_key,
            "ranks": list(row.state_ranks),
            "remaining_horizon": row.remaining_horizon,
            "registered_target_evidence": False,
        },
    )


def _public_action(row: DevelopmentMatchedDirectPhysicalRowV1) -> closure.ColdPublicActionV1:
    return closure.ColdPublicActionV1(
        row.action_semantic_id,
        {
            "schema": "acfqp.v072_matched_direct_public_action.v1",
            "context_id": row.context_id,
            "row_key": row.row_key,
            "action": list(row.action),
            "remaining_horizon": row.remaining_horizon,
            "registered_target_evidence": False,
        },
    )


class _DevelopmentPublicGraphV1:
    context_id = development_matched_direct_context_id_v1()
    horizon = 2

    def root_state_v1(self) -> closure.ColdPublicStateV1:
        root = next(
            item
            for item in development_matched_direct_physical_rows_v1()
            if item.row_key == "ROOT"
        )
        return _public_state(root)

    def canonical_state_v1(
        self,
        state: closure.ColdPublicStateV1,
    ) -> closure.ColdPublicStateV1:
        matches = tuple(
            row
            for row in development_matched_direct_physical_rows_v1()
            if row.state_semantic_id == state.semantic_state_id
        )
        if len(matches) != 1 or state != _public_state(matches[0]):
            raise V072MatchedDirectGroundInvariantViolation(
                "public state is outside the fixed development graph"
            )
        return _public_state(matches[0])

    def legal_actions_v1(
        self,
        state: closure.ColdPublicStateV1,
        remaining_horizon: int,
    ) -> tuple[closure.ColdPublicActionV1, ...]:
        matches = tuple(
            row
            for row in development_matched_direct_physical_rows_v1()
            if row.state_semantic_id == state.semantic_state_id
            and row.remaining_horizon == remaining_horizon
        )
        if len(matches) != 1:
            raise V072MatchedDirectGroundInvariantViolation(
                "public legal-action query is outside the fixed graph"
            )
        return (_public_action(matches[0]),)


def _support_semantics_id(
    row: DevelopmentMatchedDirectPhysicalRowV1,
    *,
    lane: confidence.ConfidenceObservationLaneV2,
    support_descriptor_ids: tuple[str, ...],
) -> str:
    if support_descriptor_ids != tuple(sorted(set(support_descriptor_ids))):
        raise V072MatchedDirectGroundInvariantViolation(
            "support descriptor IDs must be sorted and distinct"
        )
    return _content_id(
        "support_semantics",
        {
            "schema": "acfqp.v072_matched_direct_support_semantics.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": row.context_id,
            "arm_free_row_id": row.arm_free_row_id,
            "lane": lane.value,
            "support_descriptor_ids": list(support_descriptor_ids),
            "arm_serialized": False,
        },
    )


def _support_chain_id(
    row: DevelopmentMatchedDirectPhysicalRowV1,
    *,
    lane: confidence.ConfidenceObservationLaneV2,
    support_semantics_id: str,
    parent_transcript_id: str | None,
) -> str:
    return _content_id(
        "support_chain",
        {
            "schema": "acfqp.v072_matched_direct_support_chain.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": row.context_id,
            "arm": ARM,
            "physical_row_id": row.physical_row_id,
            "lane": lane.value,
            "support_semantics_id": support_semantics_id,
            "parent_transcript_id": parent_transcript_id,
        },
    )


def _source_stream_id(
    row: DevelopmentMatchedDirectPhysicalRowV1,
    lane: confidence.ConfidenceObservationLaneV2,
    support_semantics_id: str,
) -> str:
    return _content_id(
        "stream",
        {
            "schema": "acfqp.v072_matched_direct_source_stream.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": row.context_id,
            "arm": ARM,
            "arm_free_row_id": row.arm_free_row_id,
            "lane": lane.value,
            "support_semantics_id": support_semantics_id,
        },
    )


def _stream_identity(
    row: DevelopmentMatchedDirectPhysicalRowV1,
    *,
    lane: confidence.ConfidenceObservationLaneV2,
    support_semantics_id: str,
    support_chain_id: str,
) -> row_core.RowObservationStreamIdentityV2:
    material = tuple(
        sorted(
            (
                ("arm_free_row_id", row.arm_free_row_id),
                ("lane", lane.value),
                ("support_semantics_id", support_semantics_id),
            )
        )
    )
    return row_core.RowObservationStreamIdentityV2(
        preregistration_id=prereg.DRAFT_PREREGISTRATION_ID,
        backend_domain_id=_backend_domain_id(),
        context_id=row.context_id,
        arm=ARM,
        physical_row_id=row.physical_row_id,
        arm_free_row_id=row.arm_free_row_id,
        support_epoch_chain_id=support_chain_id,
        arm_free_support_semantics_id=support_semantics_id,
        lane=lane,
        confidence_epoch_index=(
            0
            if lane is confidence.ConfidenceObservationLaneV2.DISCOVERY
            else 1
        ),
        seed_material=material,
        source_stream_id=_source_stream_id(
            row, lane, support_semantics_id
        ),
        evidence_class=(
            row_core.RowObservationEvidenceClassV2.DEVELOPMENT_SYNTHETIC
        ),
        role=ROLE,
        registered_target_evidence=False,
    )


def _descriptor_document(
    row: DevelopmentMatchedDirectPhysicalRowV1,
    *,
    failure: bool,
) -> tuple[str, dict[str, Any]]:
    terminal = failure or row.remaining_horizon == 1
    next_ranks = (
        row.state_ranks if failure else row.success_next_ranks
    )
    document = {
        "schema": "acfqp.v072_matched_direct_semantic_transition.v1",
        "schema_version": SCHEMA_VERSION,
        "context_id": row.context_id,
        "physical_row_id": row.physical_row_id,
        "next_state": {
            "ranks": list(next_ranks),
            "failure": failure,
        },
        "realized_row_reward": _fdoc(row.exact_row_reward),
        "failure": failure,
        "terminal": terminal,
        "registered_target_evidence": False,
    }
    descriptor_id = _content_id("descriptor", document)
    document["descriptor_id"] = descriptor_id
    return descriptor_id, document


def _is_failure_draw(
    sequence_index: int,
    law: DevelopmentMatchedDirectLawV1,
) -> bool:
    return (
        (sequence_index - 1) % 100
        < law.failure_residues_per_hundred
    )


def _raw_observation(
    row: DevelopmentMatchedDirectPhysicalRowV1,
    stream: row_core.RowObservationStreamIdentityV2,
    sequence_index: int,
    law: DevelopmentMatchedDirectLawV1,
) -> row_core.RowBoundRawObservationV2:
    if type(law) is not DevelopmentMatchedDirectLawV1 or sequence_index <= 0:
        raise V072MatchedDirectGroundInvariantViolation(
            "development raw observation request is invalid"
        )
    failure = _is_failure_draw(sequence_index, law)
    descriptor_id, descriptor_document = _descriptor_document(
        row, failure=failure
    )
    raw_payload = {
        "schema": "acfqp.v072_matched_direct_raw_digest.v1",
        "schema_version": SCHEMA_VERSION,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": sequence_index,
        "law": law.value,
        "failure": failure,
        "outcome_descriptor_id": descriptor_id,
    }
    raw_word = (
        law.failure_residues_per_hundred.to_bytes(1, "big")
        + sequence_index.to_bytes(8, "big")
    )
    raw_digest = _content_id(
        "raw_digest", raw_payload, raw_suffix=raw_word
    )
    commitment_payload = {
        "schema": "acfqp.v072_matched_direct_commitment.v1",
        "schema_version": SCHEMA_VERSION,
        "source_stream_id": stream.source_stream_id,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": sequence_index,
        "raw_digest": raw_digest,
    }
    commitment_id = _content_id("commitment", commitment_payload)
    source_payload = {
        "schema": "acfqp.v072_matched_direct_source_observation.v1",
        "schema_version": SCHEMA_VERSION,
        "source_stream_id": stream.source_stream_id,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": sequence_index,
        "law": law.value,
        "raw_digest": raw_digest,
        "commitment_id": commitment_id,
        "outcome_descriptor_id": descriptor_id,
        "outcome_descriptor": descriptor_document,
        "registered_target_evidence": False,
    }
    source_id = _content_id("source_observation", source_payload)
    return row_core.freeze_source_observation_v2(
        stream_identity=stream,
        sequence_index=sequence_index,
        source_observation_id=source_id,
        source_commitment_id=commitment_id,
        raw_digest=raw_digest,
        outcome_descriptor_id=descriptor_id,
        source_document={
            **source_payload,
            "source_observation_id": source_id,
        },
        outcome_document=descriptor_document,
    )


def _suffix(
    row: DevelopmentMatchedDirectPhysicalRowV1,
    stream: row_core.RowObservationStreamIdentityV2,
    start: int,
    stop: int,
    law: DevelopmentMatchedDirectLawV1,
) -> tuple[row_core.RowBoundRawObservationV2, ...]:
    if start <= 0 or stop < start:
        raise V072MatchedDirectGroundInvariantViolation(
            "development suffix bounds are invalid"
        )
    return tuple(
        _raw_observation(row, stream, index, law)
        for index in range(start, stop + 1)
    )


@dataclass(frozen=True, slots=True)
class MatchedDirectRowReplayVerificationV1:
    physical_row_id: str
    discovery_transcript_id: str
    validation_transcript_id: str
    validation_prefix_id: str
    selected_checkpoint_draw_count: int
    previous_validation_transcript_id: str | None
    newly_observed_validation_draws: int
    replayed_raw_observation_count: int
    immutable_prefix_verified: bool = True
    exact_development_law_replayed: bool = True
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.physical_row_id, "replay physical row"),
            (self.discovery_transcript_id, "replay discovery transcript"),
            (self.validation_transcript_id, "replay validation transcript"),
            (self.validation_prefix_id, "replay validation prefix"),
        ):
            _cid(value, label)
        if self.previous_validation_transcript_id is not None:
            _cid(
                self.previous_validation_transcript_id,
                "replay previous validation transcript",
            )
        if (
            self.selected_checkpoint_draw_count not in CHECKPOINTS
            or type(self.newly_observed_validation_draws) is not int
            or self.newly_observed_validation_draws <= 0
            or self.replayed_raw_observation_count
            != DISCOVERY_DRAWS_PER_ROW
            + self.selected_checkpoint_draw_count
            or self.immutable_prefix_verified is not True
            or self.exact_development_law_replayed is not True
        ):
            raise V072MatchedDirectGroundInvariantViolation(
                "row replay verification does not reconcile"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _content_id("replay", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_matched_direct_row_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "physical_row_id": self.physical_row_id,
            "discovery_transcript_id": self.discovery_transcript_id,
            "validation_transcript_id": self.validation_transcript_id,
            "validation_prefix_id": self.validation_prefix_id,
            "selected_checkpoint_draw_count": (
                self.selected_checkpoint_draw_count
            ),
            "previous_validation_transcript_id": (
                self.previous_validation_transcript_id
            ),
            "newly_observed_validation_draws": (
                self.newly_observed_validation_draws
            ),
            "replayed_raw_observation_count": (
                self.replayed_raw_observation_count
            ),
            "immutable_prefix_verified": True,
            "exact_development_law_replayed": True,
            "registered_target_evidence": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _assert_observation_matches_law(
    row: DevelopmentMatchedDirectPhysicalRowV1,
    observation: row_core.RowBoundRawObservationV2,
    stream: row_core.RowObservationStreamIdentityV2,
    law: DevelopmentMatchedDirectLawV1,
) -> None:
    expected = _raw_observation(
        row, stream, observation.sequence_index, law
    )
    if (
        observation != expected
        or canonical_json_bytes(observation.to_document())
        != canonical_json_bytes(expected.to_document())
    ):
        raise V072MatchedDirectGroundInvariantViolation(
            "raw observation differs from the frozen development law"
        )


def verify_development_matched_direct_row_transcripts_v1(
    *,
    row: DevelopmentMatchedDirectPhysicalRowV1,
    discovery_transcript: row_core.RowObservationTranscriptV2,
    validation_history: tuple[row_core.RowObservationTranscriptV2, ...],
    confidence_snapshot: confidence.PartialSupportConfidenceSnapshotV2,
    law: DevelopmentMatchedDirectLawV1,
) -> MatchedDirectRowReplayVerificationV1:
    """Replay exact raw bytes, checkpoint ancestry, and confidence prefix."""

    if (
        type(row) is not DevelopmentMatchedDirectPhysicalRowV1
        or type(discovery_transcript)
        is not row_core.RowObservationTranscriptV2
        or type(validation_history) is not tuple
        or not validation_history
        or any(
            type(item) is not row_core.RowObservationTranscriptV2
            for item in validation_history
        )
        or type(confidence_snapshot)
        is not confidence.PartialSupportConfidenceSnapshotV2
        or type(law) is not DevelopmentMatchedDirectLawV1
    ):
        raise V072MatchedDirectGroundInvariantViolation(
            "row replay requires exact transcript/confidence artifacts"
        )
    if (
        discovery_transcript.stream_identity.physical_row_id
        != row.physical_row_id
        or discovery_transcript.stream_identity.arm != ARM
        or discovery_transcript.stream_identity.lane
        is not confidence.ConfidenceObservationLaneV2.DISCOVERY
        or discovery_transcript.selected_checkpoint_draw_count
        != DISCOVERY_DRAWS_PER_ROW
        or discovery_transcript.previous_transcript_id is not None
        or discovery_transcript.work.newly_observed_draws
        != DISCOVERY_DRAWS_PER_ROW
    ):
        raise V072MatchedDirectGroundInvariantViolation(
            "discovery transcript is not one fresh complete 64-draw row"
        )
    for observation in discovery_transcript.observations:
        _assert_observation_matches_law(
            row,
            observation,
            discovery_transcript.stream_identity,
            law,
        )

    expected_checkpoints = CHECKPOINTS[: len(validation_history)]
    if tuple(
        item.selected_checkpoint_draw_count for item in validation_history
    ) != expected_checkpoints:
        raise V072MatchedDirectGroundInvariantViolation(
            "validation history is not one contiguous checkpoint prefix"
        )
    prior: row_core.RowObservationTranscriptV2 | None = None
    for transcript in validation_history:
        if (
            transcript.stream_identity.physical_row_id
            != row.physical_row_id
            or transcript.stream_identity.arm != ARM
            or transcript.stream_identity.lane
            is not confidence.ConfidenceObservationLaneV2.VALIDATION
            or transcript.previous_transcript_id
            != (None if prior is None else prior.transcript_id)
            or transcript.previous_draw_count
            != (
                0
                if prior is None
                else prior.selected_checkpoint_draw_count
            )
            or (
                prior is not None
                and transcript.chunks[: len(prior.chunks)] != prior.chunks
            )
            or transcript.work.newly_observed_draws
            != transcript.selected_checkpoint_draw_count
            - transcript.previous_draw_count
        ):
            raise V072MatchedDirectGroundInvariantViolation(
                "validation transcript reset, dropped, or changed its prefix"
            )
        start = transcript.previous_draw_count + 1
        for observation in transcript.observations[start - 1 :]:
            _assert_observation_matches_law(
                row, observation, transcript.stream_identity, law
            )
        prior = transcript
    assert prior is not None
    confidence_verification = (
        confidence.verify_partial_support_confidence_snapshot_v2(
            confidence_snapshot
        )
    )
    if (
        confidence_snapshot.selected_checkpoint_draw_count
        != prior.selected_checkpoint_draw_count
        or confidence_snapshot.validation_prefix.observations
        != tuple(
            confidence.freeze_confidence_observation_v2(item)
            for item in prior.observations
        )
        or confidence_verification.snapshot_id
        != confidence_snapshot.snapshot_id
    ):
        raise V072MatchedDirectGroundInvariantViolation(
            "confidence snapshot is not the final validation prefix"
        )
    return MatchedDirectRowReplayVerificationV1(
        row.physical_row_id,
        discovery_transcript.transcript_id,
        prior.transcript_id,
        confidence_snapshot.validation_prefix.prefix_id,
        prior.selected_checkpoint_draw_count,
        prior.previous_transcript_id,
        prior.work.newly_observed_draws,
        DISCOVERY_DRAWS_PER_ROW
        + prior.selected_checkpoint_draw_count,
    )


@dataclass(frozen=True, slots=True)
class DevelopmentMatchedDirectRowAcquisitionV1:
    row: DevelopmentMatchedDirectPhysicalRowV1
    law: DevelopmentMatchedDirectLawV1
    confidence_row_binding: confidence.ConfidencePhysicalRowBindingV2
    discovery_transcript: row_core.RowObservationTranscriptV2
    support_epoch: confidence.InitialSupportEpochV2
    validation_history: tuple[row_core.RowObservationTranscriptV2, ...]
    confidence_snapshot: confidence.PartialSupportConfidenceSnapshotV2
    confidence_verification: confidence.PartialSupportConfidenceVerificationV2
    source_projection: projection.ConfidenceIntervalSimplexRowProjectionV1
    projection_verification: (
        projection_independent.V072ConfidenceRowProjectionVerificationV1
    )
    row_replay: MatchedDirectRowReplayVerificationV1
    _acquisition_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.row) is not DevelopmentMatchedDirectPhysicalRowV1
            or type(self.law) is not DevelopmentMatchedDirectLawV1
            or type(self.confidence_row_binding)
            is not confidence.ConfidencePhysicalRowBindingV2
            or self.confidence_row_binding.context_id != self.row.context_id
            or self.confidence_row_binding.arm != ARM
            or self.confidence_row_binding.physical_row_id
            != self.row.physical_row_id
            or type(self.discovery_transcript)
            is not row_core.RowObservationTranscriptV2
            or type(self.support_epoch) is not confidence.InitialSupportEpochV2
            or self.support_epoch.row_binding != self.confidence_row_binding
            or type(self.validation_history) is not tuple
            or not self.validation_history
            or type(self.confidence_snapshot)
            is not confidence.PartialSupportConfidenceSnapshotV2
            or self.confidence_snapshot.support_epoch != self.support_epoch
            or type(self.confidence_verification)
            is not confidence.PartialSupportConfidenceVerificationV2
            or self.confidence_verification.snapshot_id
            != self.confidence_snapshot.snapshot_id
            or type(self.source_projection)
            is not projection.ConfidenceIntervalSimplexRowProjectionV1
            or self.source_projection.confidence_snapshot
            != self.confidence_snapshot
            or type(self.projection_verification)
            is not (
                projection_independent
                .V072ConfidenceRowProjectionVerificationV1
            )
            or self.projection_verification.projection_id
            != self.source_projection.projection_id
            or type(self.row_replay)
            is not MatchedDirectRowReplayVerificationV1
            or self.row_replay.physical_row_id != self.row.physical_row_id
            or self.row_replay.validation_transcript_id
            != self.validation_history[-1].transcript_id
            or self.row_replay.validation_prefix_id
            != self.confidence_snapshot.validation_prefix.prefix_id
        ):
            raise V072MatchedDirectGroundInvariantViolation(
                "development row acquisition identity chain is inconsistent"
            )
        object.__setattr__(
            self,
            "_acquisition_id",
            _content_id("acquisition", self._payload()),
        )

    @property
    def selected_checkpoint_draw_count(self) -> int:
        return self.validation_history[-1].selected_checkpoint_draw_count

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_matched_direct_row_acquisition.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "row_record_id": self.row.row_record_id,
            "law": self.law.value,
            "confidence_row_binding_id": (
                self.confidence_row_binding.row_binding_id
            ),
            "discovery_transcript_id": (
                self.discovery_transcript.transcript_id
            ),
            "support_epoch_id": self.support_epoch.support_epoch_id,
            "validation_transcript_ids": [
                item.transcript_id for item in self.validation_history
            ],
            "confidence_snapshot_id": self.confidence_snapshot.snapshot_id,
            "confidence_verification_id": (
                self.confidence_verification.verification_id
            ),
            "source_projection_id": self.source_projection.projection_id,
            "projection_verification_id": (
                self.projection_verification.verification_id
            ),
            "row_replay_verification_id": (
                self.row_replay.verification_id
            ),
            "selected_checkpoint_draw_count": (
                self.selected_checkpoint_draw_count
            ),
            "registered_target_evidence": False,
        }

    @property
    def acquisition_id(self) -> str:
        return self._acquisition_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "acquisition_id": self.acquisition_id}


def _public_projection_binding(
    row: DevelopmentMatchedDirectPhysicalRowV1,
    row_binding: confidence.ConfidencePhysicalRowBindingV2,
) -> projection.PublicStateActionRowBindingV1:
    return projection.PublicStateActionRowBindingV1(
        preregistration_id=prereg.DRAFT_PREREGISTRATION_ID,
        context_id=row.context_id,
        arm=ARM,
        physical_row_id=row.physical_row_id,
        confidence_row_binding_id=row_binding.row_binding_id,
        state_ranks=row.state_ranks,
        remaining_horizon=row.remaining_horizon,
        action=row.action,
    )


def _finish_acquisition(
    *,
    row: DevelopmentMatchedDirectPhysicalRowV1,
    law: DevelopmentMatchedDirectLawV1,
    row_binding: confidence.ConfidencePhysicalRowBindingV2,
    discovery: row_core.RowObservationTranscriptV2,
    support_epoch: confidence.InitialSupportEpochV2,
    validation_history: tuple[row_core.RowObservationTranscriptV2, ...],
) -> DevelopmentMatchedDirectRowAcquisitionV1:
    snapshot = confidence.build_partial_support_confidence_snapshot_v2(
        support_epoch,
        validation_history[-1].observations,
        confidence.v0072_partial_support_confidence_profile_v2(),
    )
    confidence_verification = (
        confidence.verify_partial_support_confidence_snapshot_v2(snapshot)
    )
    source_projection = (
        projection.project_confidence_snapshot_to_interval_row_v1(
            snapshot,
            _public_projection_binding(row, row_binding),
        )
    )
    projection_verification = (
        projection_independent.verify_v072_confidence_row_projection_v1(
            source_projection
        )
    )
    replay = verify_development_matched_direct_row_transcripts_v1(
        row=row,
        discovery_transcript=discovery,
        validation_history=validation_history,
        confidence_snapshot=snapshot,
        law=law,
    )
    return DevelopmentMatchedDirectRowAcquisitionV1(
        row,
        law,
        row_binding,
        discovery,
        support_epoch,
        validation_history,
        snapshot,
        confidence_verification,
        source_projection,
        projection_verification,
        replay,
    )


def acquire_development_matched_direct_row_v1(
    row: DevelopmentMatchedDirectPhysicalRowV1,
    *,
    law: DevelopmentMatchedDirectLawV1,
) -> DevelopmentMatchedDirectRowAcquisitionV1:
    if (
        type(row) is not DevelopmentMatchedDirectPhysicalRowV1
        or type(law) is not DevelopmentMatchedDirectLawV1
    ):
        raise V072MatchedDirectGroundInvariantViolation(
            "initial matched-direct acquisition requires exact inputs"
        )
    discovery_semantics = _support_semantics_id(
        row,
        lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
        support_descriptor_ids=(),
    )
    discovery_chain = _support_chain_id(
        row,
        lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
        support_semantics_id=discovery_semantics,
        parent_transcript_id=None,
    )
    discovery_stream = _stream_identity(
        row,
        lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
        support_semantics_id=discovery_semantics,
        support_chain_id=discovery_chain,
    )
    discovery = row_core.build_or_extend_row_observation_transcript_v2(
        stream_identity=discovery_stream,
        selected_checkpoint_draw_count=DISCOVERY_DRAWS_PER_ROW,
        new_observations=_suffix(
            row,
            discovery_stream,
            1,
            DISCOVERY_DRAWS_PER_ROW,
            law,
        ),
    )
    discovered = tuple(
        sorted(
            {
                item.outcome_descriptor_id
                for item in discovery.observations
            }
        )
    )
    if len(discovered) != 2:
        raise V072MatchedDirectGroundInvariantViolation(
            "development discovery must expose success and failure"
        )
    validation_semantics = _support_semantics_id(
        row,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
        support_descriptor_ids=discovered,
    )
    validation_chain = _support_chain_id(
        row,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
        support_semantics_id=validation_semantics,
        parent_transcript_id=discovery.transcript_id,
    )
    validation_stream = _stream_identity(
        row,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
        support_semantics_id=validation_semantics,
        support_chain_id=validation_chain,
    )
    row_binding = confidence.ConfidencePhysicalRowBindingV2(
        prereg.DRAFT_PREREGISTRATION_ID,
        row.context_id,
        ARM,
        row.physical_row_id,
    )
    profile = confidence.v0072_partial_support_confidence_profile_v2()
    support_epoch = confidence.freeze_initial_support_epoch_v2(
        row_binding=row_binding,
        purpose=confidence.ConfidenceEpochPurposeV2.INITIAL_SHARED_OR_DIRECT,
        discovery_support_epoch_chain_id=discovery_chain,
        discovery_stream_id=discovery_stream.source_stream_id,
        discovery_observations=discovery.observations,
        validation_support_epoch_chain_id=validation_chain,
        validation_stream_id=validation_stream.source_stream_id,
        profile=profile,
    )
    validation = row_core.build_or_extend_row_observation_transcript_v2(
        stream_identity=validation_stream,
        selected_checkpoint_draw_count=CHECKPOINTS[0],
        new_observations=_suffix(
            row, validation_stream, 1, CHECKPOINTS[0], law
        ),
    )
    return _finish_acquisition(
        row=row,
        law=law,
        row_binding=row_binding,
        discovery=discovery,
        support_epoch=support_epoch,
        validation_history=(validation,),
    )


def extend_development_matched_direct_row_v1(
    acquisition: DevelopmentMatchedDirectRowAcquisitionV1,
    *,
    validation_checkpoint: int,
) -> DevelopmentMatchedDirectRowAcquisitionV1:
    if (
        type(acquisition) is not DevelopmentMatchedDirectRowAcquisitionV1
        or validation_checkpoint not in CHECKPOINTS[1:]
        or validation_checkpoint
        != CHECKPOINTS[len(acquisition.validation_history)]
    ):
        raise V072MatchedDirectGroundInvariantViolation(
            "matched-direct row extension is stale or skips a checkpoint"
        )
    previous = acquisition.validation_history[-1]
    validation = row_core.build_or_extend_row_observation_transcript_v2(
        stream_identity=previous.stream_identity,
        selected_checkpoint_draw_count=validation_checkpoint,
        new_observations=_suffix(
            acquisition.row,
            previous.stream_identity,
            previous.selected_checkpoint_draw_count + 1,
            validation_checkpoint,
            acquisition.law,
        ),
        previous=previous,
    )
    return _finish_acquisition(
        row=acquisition.row,
        law=acquisition.law,
        row_binding=acquisition.confidence_row_binding,
        discovery=acquisition.discovery_transcript,
        support_epoch=acquisition.support_epoch,
        validation_history=acquisition.validation_history + (validation,),
    )


def _cold_descriptor(
    acquisition: DevelopmentMatchedDirectRowAcquisitionV1,
    descriptor: confidence.OpaqueOutcomeDescriptorV2,
) -> closure.ColdOutcomeDescriptorV1:
    document = descriptor.document
    failure = document.get("failure")
    terminal = document.get("terminal")
    next_state = document.get("next_state")
    if (
        type(failure) is not bool
        or type(terminal) is not bool
        or not isinstance(next_state, Mapping)
        or next_state.get("ranks")
        not in (
            acquisition.row.state_ranks,
            list(acquisition.row.state_ranks),
            acquisition.row.success_next_ranks,
            list(acquisition.row.success_next_ranks),
        )
    ):
        raise V072MatchedDirectGroundInvariantViolation(
            "confidence descriptor lacks exact public transition semantics"
        )
    successor: closure.ColdPublicStateV1 | None = None
    if not failure and not terminal:
        matches = tuple(
            row
            for row in development_matched_direct_physical_rows_v1()
            if row.state_ranks == acquisition.row.success_next_ranks
            and row.remaining_horizon
            == acquisition.row.remaining_horizon - 1
        )
        if len(matches) != 1:
            raise V072MatchedDirectGroundInvariantViolation(
                "active descriptor does not identify one frozen child"
            )
        successor = _public_state(matches[0])
    return closure.ColdOutcomeDescriptorV1(
        descriptor.descriptor_id,
        failure=failure,
        terminal=terminal,
        successor_state=successor,
        document=document,
    )


def _cold_row_evidence(
    acquisition: DevelopmentMatchedDirectRowAcquisitionV1,
) -> closure.ColdRowEvidenceV1:
    support = tuple(
        sorted(
            (
                _cold_descriptor(acquisition, item)
                for item in acquisition.support_epoch.support_descriptors
            ),
            key=lambda item: item.descriptor_record_id,
        )
    )
    novel = tuple(
        sorted(
            (
                _cold_descriptor(acquisition, item)
                for item in acquisition.confidence_snapshot.novel_descriptors
            ),
            key=lambda item: item.descriptor_record_id,
        )
    )
    if novel:
        raise V072MatchedDirectGroundInvariantViolation(
            "fixed development law unexpectedly produced validation novelty"
        )
    return closure.ColdRowEvidenceV1(
        acquisition.row.context_id,
        _public_state(acquisition.row),
        acquisition.row.remaining_horizon,
        _public_action(acquisition.row),
        support,
        novel,
        acquisition.support_epoch.support_epoch_id,
        acquisition.confidence_snapshot.snapshot_id,
        acquisition.row_replay.verification_id,
        acquisition.row.physical_row_id,
        closure.ColdRowNativeWorkV1(),
    )


def _freeze_checkpoint_closure(
    acquisitions: tuple[
        DevelopmentMatchedDirectRowAcquisitionV1, ...
    ],
    *,
    logical_occurrence_id: str,
) -> closure.V072ColdH2ClosureBundleV1:
    if (
        type(acquisitions) is not tuple
        or tuple(item.row for item in acquisitions)
        != development_matched_direct_physical_rows_v1()
        or len(
            {
                item.selected_checkpoint_draw_count
                for item in acquisitions
            }
        )
        != 1
    ):
        raise V072MatchedDirectGroundInvariantViolation(
            "checkpoint closure requires every fixed row synchronously"
        )
    cap = closure.development_synthetic_cold_h2_cap_evidence_v1(
        context_id=development_matched_direct_context_id_v1(),
        context_key="v072_matched_direct_development_h2_v1",
        total_physical_row_cap=len(acquisitions),
        development_scope_id=_content_id(
            "context",
            {
                "schema": (
                    "acfqp.v072_matched_direct_development_scope.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "context_id": (
                    development_matched_direct_context_id_v1()
                ),
                "registered_target_evidence": False,
            },
        ),
    )
    return closure.freeze_v072_cold_h2_closure_v1(
        public_graph=_DevelopmentPublicGraphV1(),
        row_evidence=tuple(
            _cold_row_evidence(item) for item in acquisitions
        ),
        logical_occurrence_id=logical_occurrence_id,
        arm=ARM,
        cap_evidence=cap,
    )


def _bound_projection(
    row: closure.ColdRowEvidenceV1,
    acquisition: DevelopmentMatchedDirectRowAcquisitionV1,
) -> model_builders.VerifiedColdH2ConfidenceRowProjectionV1:
    source = acquisition.source_projection
    if (
        row.context_id != acquisition.row.context_id
        or row.physical_evidence_id
        != acquisition.row.physical_row_id
        or row.support_epoch_id
        != acquisition.support_epoch.support_epoch_id
        or row.confidence_snapshot_id
        != acquisition.confidence_snapshot.snapshot_id
        or row.row_replay_verification_id
        != acquisition.row_replay.verification_id
        or source.row_binding.physical_row_id
        != acquisition.row.physical_row_id
        or source.row_binding.state_ranks != acquisition.row.state_ranks
        or source.row_binding.action != acquisition.row.action
        or source.exact_row_reward
        != acquisition.row.exact_row_reward
    ):
        raise V072MatchedDirectGroundInvariantViolation(
            "confidence projection was transplanted across closure rows"
        )
    events_by_descriptor = {
        item.event_key: item
        for item in acquisition.confidence_snapshot.event_intervals
        if item.event_kind
        is confidence.PartialSupportEventKindV2.SUPPORT
    }
    if set(events_by_descriptor) != {
        item.semantic_descriptor_id for item in row.discovery_support
    }:
        raise V072MatchedDirectGroundInvariantViolation(
            "confidence support differs from discovery-frozen closure support"
        )
    destinations = tuple(
        sorted(
            (
                *(
                    model_builders.destination_for_descriptor_v1(
                        row, descriptor
                    )
                    for descriptor in row.discovery_support
                ),
                model_builders.other_destination_for_row_v1(row),
            ),
            key=lambda item: item.destination_id,
        )
    )
    mass_values: list[robust.IntervalDestinationMassV1] = []
    for descriptor in row.discovery_support:
        event = events_by_descriptor[descriptor.semantic_descriptor_id]
        destination = model_builders.destination_for_descriptor_v1(
            row, descriptor
        )
        mass_values.append(
            robust.IntervalDestinationMassV1(
                destination.destination_id,
                event.lower_probability,
                event.upper_probability,
            )
        )
    other_event = acquisition.confidence_snapshot.event_intervals[-1]
    if (
        other_event.event_kind
        is not confidence.PartialSupportEventKindV2.OTHER
    ):
        raise V072MatchedDirectGroundInvariantViolation(
            "confidence snapshot lost its unique OTHER event"
        )
    other_id = model_builders.row_bound_other_destination_id_v1(row)
    mass_values.append(
        robust.IntervalDestinationMassV1(
            other_id,
            other_event.lower_probability,
            other_event.upper_probability,
        )
    )
    interval_row = robust.IntervalSimplexRowV1(
        model_builders.ground_state_id_v1(
            row.context_id, row.state, row.remaining_horizon
        ),
        row.remaining_horizon,
        model_builders.ground_action_id_v1(
            row.context_id,
            row.state,
            row.remaining_horizon,
            row.action,
        ),
        source.exact_row_reward,
        source.exact_row_reward,
        other_id,
        tuple(
            sorted(mass_values, key=lambda item: item.destination_id)
        ),
    )
    return model_builders.VerifiedColdH2ConfidenceRowProjectionV1(
        context_id=row.context_id,
        row_evidence_id=row.row_evidence_id,
        physical_evidence_id=row.physical_evidence_id,
        support_epoch_id=row.support_epoch_id,
        confidence_snapshot_id=row.confidence_snapshot_id,
        row_replay_verification_id=row.row_replay_verification_id,
        discovery_transcript_id=(
            acquisition.discovery_transcript.transcript_id
        ),
        validation_transcript_id=(
            acquisition.validation_history[-1].transcript_id
        ),
        validation_prefix_id=(
            acquisition.confidence_snapshot.validation_prefix.prefix_id
        ),
        selected_checkpoint_draw_count=(
            acquisition.selected_checkpoint_draw_count
        ),
        source_projection_id=source.projection_id,
        projection_verification_id=(
            acquisition.projection_verification.verification_id
        ),
        state_semantic_id=row.state.semantic_state_id,
        remaining_horizon=row.remaining_horizon,
        action_semantic_id=row.action.semantic_action_id,
        discovery_support_descriptor_ids=tuple(
            sorted(
                item.descriptor_record_id
                for item in row.discovery_support
            )
        ),
        validation_novel_descriptor_ids=tuple(
            sorted(
                item.descriptor_record_id
                for item in row.validation_novel
            )
        ),
        interval_row=interval_row,
        destinations=destinations,
        rank_cap=4,
        rank_profile=model_builders.DEVELOPMENT_RANK_PROFILE,
        evidence_class=(
            model_builders.RowProjectionEvidenceClassV1
            .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
        ),
        registered_target_evidence=False,
    )


@dataclass(frozen=True, slots=True)
class MatchedDirectCheckpointEvidenceV1:
    checkpoint: int
    closure_bundle: closure.V072ColdH2ClosureBundleV1
    acquisitions: tuple[
        DevelopmentMatchedDirectRowAcquisitionV1, ...
    ]
    bound_projections: tuple[
        model_builders.VerifiedColdH2ConfidenceRowProjectionV1, ...
    ]
    _checkpoint_evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.checkpoint not in CHECKPOINTS
            or type(self.closure_bundle)
            is not closure.V072ColdH2ClosureBundleV1
            or self.closure_bundle.arm != ARM
            or self.closure_bundle.consumer_profile.consumer_routes
            != closure.DIRECT_ONLY_CONSUMER_ROUTES
            or type(self.acquisitions) is not tuple
            or self.acquisitions
            != tuple(
                sorted(
                    self.acquisitions,
                    key=lambda item: item.row.physical_row_id,
                )
            )
            or tuple(item.row for item in self.acquisitions)
            != development_matched_direct_physical_rows_v1()
            or any(
                item.selected_checkpoint_draw_count != self.checkpoint
                for item in self.acquisitions
            )
            or type(self.bound_projections) is not tuple
            or self.bound_projections
            != tuple(
                sorted(
                    self.bound_projections,
                    key=lambda item: item.projection_binding_id,
                )
            )
            or len(self.bound_projections) != len(self.acquisitions)
            or {
                item.row_evidence_id
                for item in self.bound_projections
            }
            != {
                item.row_evidence_id
                for item in self.closure_bundle.all_rows
            }
            or {
                item.physical_evidence_id
                for item in self.bound_projections
            }
            != {
                item.row.physical_row_id
                for item in self.acquisitions
            }
        ):
            raise V072MatchedDirectGroundInvariantViolation(
                "matched-direct checkpoint is partial, asynchronous, or non-direct"
            )
        object.__setattr__(
            self,
            "_checkpoint_evidence_id",
            _content_id("checkpoint", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_matched_direct_checkpoint_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "arm": ARM,
            "checkpoint": self.checkpoint,
            "closure_id": self.closure_bundle.closure_id,
            "acquisition_ids": [
                item.acquisition_id for item in self.acquisitions
            ],
            "bound_projection_ids": [
                item.projection_binding_id
                for item in self.bound_projections
            ],
            "physical_row_ids": [
                item.row.physical_row_id for item in self.acquisitions
            ],
            "all_rows_checkpoint_complete": True,
            "consumer_routes": ["DIRECT"],
        }

    @property
    def checkpoint_evidence_id(self) -> str:
        return self._checkpoint_evidence_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "checkpoint_evidence_id": self.checkpoint_evidence_id,
        }


def _freeze_checkpoint_evidence(
    acquisitions: tuple[
        DevelopmentMatchedDirectRowAcquisitionV1, ...
    ],
    *,
    logical_occurrence_id: str,
) -> MatchedDirectCheckpointEvidenceV1:
    bundle = _freeze_checkpoint_closure(
        acquisitions,
        logical_occurrence_id=logical_occurrence_id,
    )
    acquisition_by_physical = {
        item.row.physical_row_id: item for item in acquisitions
    }
    bound = tuple(
        sorted(
            (
                _bound_projection(
                    row,
                    acquisition_by_physical[row.physical_evidence_id],
                )
                for row in bundle.all_rows
            ),
            key=lambda item: item.projection_binding_id,
        )
    )
    return MatchedDirectCheckpointEvidenceV1(
        acquisitions[0].selected_checkpoint_draw_count,
        bundle,
        acquisitions,
        bound,
    )


@dataclass(frozen=True, slots=True)
class MatchedDirectCheckpointWorkV1:
    checkpoint: int
    physical_row_count: int
    discovery_new_draws: int
    validation_new_draws: int
    accepted_new_draws: int
    cumulative_accepted_draws: int
    raw_observations_replayed: int
    confidence_verifications: int
    projection_verifications: int
    direct_model_builds: int = 1
    direct_model_independent_verifications: int = 1
    exact_lazy_ground_planner_calls: int = 1
    independent_lazy_proof_verifications: int = 1
    quotient_model_builds: int = 0
    quotient_planner_calls: int = 0
    source_prior_reads: int = 0
    selected_row_acquisition_calls: int = 0
    local_promotion_calls: int = 0
    fallback_calls: int = 0
    hidden_law_queries: int = 0
    exact_ground_evaluator_calls: int = 0
    crn_cost_discount_draws: int = 0
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        values = tuple(
            getattr(self, name)
            for name in self.__dataclass_fields__
            if name not in ("_work_id",)
        )
        if (
            self.checkpoint not in CHECKPOINTS
            or self.physical_row_count <= 0
            or any(type(value) is not int or value < 0 for value in values)
            or self.discovery_new_draws
            not in (0, self.physical_row_count * DISCOVERY_DRAWS_PER_ROW)
            or self.validation_new_draws
            <= 0
            or self.accepted_new_draws
            != self.discovery_new_draws + self.validation_new_draws
            or self.cumulative_accepted_draws
            != self.physical_row_count
            * (DISCOVERY_DRAWS_PER_ROW + self.checkpoint)
            or self.raw_observations_replayed
            != self.cumulative_accepted_draws
            or self.confidence_verifications != self.physical_row_count
            or self.projection_verifications != self.physical_row_count
            or any(
                value != 1
                for value in (
                    self.direct_model_builds,
                    self.direct_model_independent_verifications,
                    self.exact_lazy_ground_planner_calls,
                    self.independent_lazy_proof_verifications,
                )
            )
            or any(
                value != 0
                for value in (
                    self.quotient_model_builds,
                    self.quotient_planner_calls,
                    self.source_prior_reads,
                    self.selected_row_acquisition_calls,
                    self.local_promotion_calls,
                    self.fallback_calls,
                    self.hidden_law_queries,
                    self.exact_ground_evaluator_calls,
                    self.crn_cost_discount_draws,
                )
            )
        ):
            raise V072MatchedDirectGroundInvariantViolation(
                "checkpoint work is undercounted or uses a forbidden route"
            )
        object.__setattr__(
            self,
            "_work_id",
            _content_id("work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_matched_direct_checkpoint_work.v1",
            "schema_version": SCHEMA_VERSION,
            "checkpoint": self.checkpoint,
            "physical_row_count": self.physical_row_count,
            "discovery_new_draws": self.discovery_new_draws,
            "validation_new_draws": self.validation_new_draws,
            "accepted_new_draws": self.accepted_new_draws,
            "cumulative_accepted_draws": self.cumulative_accepted_draws,
            "raw_observations_replayed": self.raw_observations_replayed,
            "confidence_verifications": self.confidence_verifications,
            "projection_verifications": self.projection_verifications,
            "direct_model_builds": 1,
            "direct_model_independent_verifications": 1,
            "exact_lazy_ground_planner_calls": 1,
            "independent_lazy_proof_verifications": 1,
            "quotient_model_builds": 0,
            "quotient_planner_calls": 0,
            "source_prior_reads": 0,
            "selected_row_acquisition_calls": 0,
            "local_promotion_calls": 0,
            "fallback_calls": 0,
            "hidden_law_queries": 0,
            "exact_ground_evaluator_calls": 0,
            "crn_cost_discount_draws": 0,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class MatchedDirectCheckpointRecordV1:
    evidence: MatchedDirectCheckpointEvidenceV1
    direct_snapshot: model_builders.V072ColdH2GroundDirectSnapshotV1
    model_verification: (
        model_independent
        .V072ColdH2GroundDirectSnapshotIndependentVerificationV1
    )
    planner_result: lazy.ExactLazyH2SolveResultV1
    proof_verification: (
        lazy_independent.ExactLazyH2IndependentVerificationV1 | None
    )
    status: MatchedDirectCheckpointStatusV1
    work: MatchedDirectCheckpointWorkV1
    _record_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        solved = (
            self.planner_result.status
            is lazy.ExactLazyH2SolveStatus.SOLVED
        )
        audit = self.planner_result.audit
        expected_status = (
            MatchedDirectCheckpointStatusV1.SOLVER_RESOURCE_EXHAUSTED
            if not solved
            else (
                MatchedDirectCheckpointStatusV1.CERTIFIED
                if audit is not None
                and audit.status is robust.RobustAuditStatus.CERTIFIED
                else MatchedDirectCheckpointStatusV1.NOT_CERTIFIED
            )
        )
        if (
            type(self.evidence) is not MatchedDirectCheckpointEvidenceV1
            or type(self.direct_snapshot)
            is not model_builders.V072ColdH2GroundDirectSnapshotV1
            or self.direct_snapshot.closure_bundle
            != self.evidence.closure_bundle
            or self.direct_snapshot.row_projections
            != self.evidence.bound_projections
            or type(self.model_verification)
            is not (
                model_independent
                .V072ColdH2GroundDirectSnapshotIndependentVerificationV1
            )
            or self.model_verification.snapshot_id
            != self.direct_snapshot.snapshot_id
            or type(self.planner_result)
            is not lazy.ExactLazyH2SolveResultV1
            or self.planner_result.solver_kind
            is not robust.RobustSolverKind.GROUND_DIRECT
            or self.status is not expected_status
            or type(self.work) is not MatchedDirectCheckpointWorkV1
            or self.work.checkpoint != self.evidence.checkpoint
            or self.work.physical_row_count
            != len(self.evidence.acquisitions)
            or (
                solved
                and (
                    type(self.proof_verification)
                    is not lazy_independent.ExactLazyH2IndependentVerificationV1
                    or audit is None
                    or self.proof_verification.audit_id != audit.audit_id
                    or self.proof_verification.model_id
                    != self.direct_snapshot.planner_projection.planner_model.model_id
                    or self.proof_verification.threshold_profile_id
                    != self.direct_snapshot.threshold_profile.threshold_profile_id
                )
            )
            or (not solved and self.proof_verification is not None)
        ):
            raise V072MatchedDirectGroundInvariantViolation(
                "checkpoint planner/proof/model identity chain is invalid"
            )
        object.__setattr__(
            self,
            "_record_id",
            _content_id("record", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        audit_id = (
            None
            if self.planner_result.audit is None
            else self.planner_result.audit.audit_id
        )
        original_proof_id = (
            None
            if self.planner_result.trace is None
            else self.planner_result.trace.original_proof.proof_id
        )
        exhaustion = self.planner_result.exhaustion
        return {
            "schema": "acfqp.v072_matched_direct_checkpoint_record.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "checkpoint_evidence_id": (
                self.evidence.checkpoint_evidence_id
            ),
            "direct_snapshot_id": self.direct_snapshot.snapshot_id,
            "model_verification_id": (
                self.model_verification.verification_id
            ),
            "planner_status": self.planner_result.status.value,
            "audit_id": audit_id,
            "original_proof_id": original_proof_id,
            "proof_verification_id": (
                None
                if self.proof_verification is None
                else self.proof_verification.verification_id
            ),
            "resource_exhaustion": (
                None
                if exhaustion is None
                else {
                    "phase": exhaustion.phase.value,
                    "code": exhaustion.code.value,
                    "observed": exhaustion.observed,
                    "limit": exhaustion.limit,
                }
            ),
            "status": self.status.value,
            "work_id": self.work.work_id,
        }

    @property
    def record_id(self) -> str:
        return self._record_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "record_id": self.record_id}


@dataclass(frozen=True, slots=True)
class MatchedDirectGroundRunV1:
    logical_occurrence_id: str
    law: DevelopmentMatchedDirectLawV1
    checkpoint_records: tuple[MatchedDirectCheckpointRecordV1, ...]
    terminal_class: MatchedDirectTerminalClassV1
    terminal_code: MatchedDirectTerminalCodeV1
    stopped_checkpoint: int
    total_accepted_draws: int
    total_random_word_calls: int
    physical_row_count: int
    crn_cost_discount_draws: int = 0
    source_prior_reads: int = 0
    quotient_planner_calls: int = 0
    local_promotion_calls: int = 0
    fallback_calls: int = 0
    hidden_law_queries: int = 0
    exact_ground_evaluator_calls: int = 0
    registered_target_evidence_count: int = 0
    _run_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.logical_occurrence_id, "matched-direct occurrence")
        checkpoints = tuple(
            item.evidence.checkpoint for item in self.checkpoint_records
        )
        certified = tuple(
            item
            for item in self.checkpoint_records
            if item.status is MatchedDirectCheckpointStatusV1.CERTIFIED
        )
        exhausted = tuple(
            item
            for item in self.checkpoint_records
            if item.status
            is MatchedDirectCheckpointStatusV1.SOLVER_RESOURCE_EXHAUSTED
        )
        expected_terminal = (
            (
                MatchedDirectTerminalClassV1.PLAN_CERTIFICATE,
                MatchedDirectTerminalCodeV1.MATCHED_DIRECT_GROUND_CERTIFIED,
            )
            if certified
            else (
                MatchedDirectTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE,
                (
                    MatchedDirectTerminalCodeV1.EXACT_LAZY_RESOURCE_EXHAUSTED
                    if exhausted
                    else (
                        MatchedDirectTerminalCodeV1
                        .MAXIMUM_DIRECT_CHECKPOINT_EXHAUSTED
                    )
                ),
            )
        )
        if (
            type(self.law) is not DevelopmentMatchedDirectLawV1
            or type(self.checkpoint_records) is not tuple
            or not self.checkpoint_records
            or any(
                type(item) is not MatchedDirectCheckpointRecordV1
                for item in self.checkpoint_records
            )
            or checkpoints != CHECKPOINTS[: len(checkpoints)]
            or len(certified) > 1
            or (
                certified
                and certified[0] is not self.checkpoint_records[-1]
            )
            or (
                not certified
                and not exhausted
                and checkpoints[-1] != CHECKPOINTS[-1]
            )
            or (
                exhausted
                and exhausted[0] is not self.checkpoint_records[-1]
            )
            or (self.terminal_class, self.terminal_code)
            != expected_terminal
            or self.stopped_checkpoint != checkpoints[-1]
            or self.physical_row_count
            != len(self.checkpoint_records[0].evidence.acquisitions)
            or self.total_accepted_draws
            != self.physical_row_count
            * (DISCOVERY_DRAWS_PER_ROW + self.stopped_checkpoint)
            or self.total_random_word_calls != self.total_accepted_draws
            or any(
                value != 0
                for value in (
                    self.crn_cost_discount_draws,
                    self.source_prior_reads,
                    self.quotient_planner_calls,
                    self.local_promotion_calls,
                    self.fallback_calls,
                    self.hidden_law_queries,
                    self.exact_ground_evaluator_calls,
                    self.registered_target_evidence_count,
                )
            )
        ):
            raise V072MatchedDirectGroundInvariantViolation(
                "matched-direct run stopped early, undercounted, or used a forbidden route"
            )
        expected_physical = tuple(
            item.row.physical_row_id
            for item in self.checkpoint_records[0].evidence.acquisitions
        )
        prior_record: MatchedDirectCheckpointRecordV1 | None = None
        for record in self.checkpoint_records:
            if tuple(
                item.row.physical_row_id
                for item in record.evidence.acquisitions
            ) != expected_physical:
                raise V072MatchedDirectGroundInvariantViolation(
                    "checkpoint dropped or transplanted one physical row"
                )
            if prior_record is not None:
                previous_by_row = {
                    item.row.physical_row_id: item
                    for item in prior_record.evidence.acquisitions
                }
                for current in record.evidence.acquisitions:
                    prior = previous_by_row[current.row.physical_row_id]
                    if (
                        current.discovery_transcript
                        != prior.discovery_transcript
                        or current.support_epoch != prior.support_epoch
                        or current.validation_history[:-1]
                        != prior.validation_history
                        or current.validation_history[-1]
                        .previous_transcript_id
                        != prior.validation_history[-1].transcript_id
                    ):
                        raise V072MatchedDirectGroundInvariantViolation(
                            "row extension reset or dropped its prior prefix"
                        )
            prior_record = record
        object.__setattr__(
            self,
            "_run_id",
            _content_id("run", self._payload()),
        )

    @property
    def certified(self) -> bool:
        return (
            self.terminal_class
            is MatchedDirectTerminalClassV1.PLAN_CERTIFICATE
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_matched_direct_ground_run.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": self.logical_occurrence_id,
            "arm": ARM,
            "law": self.law.value,
            "checkpoint_record_ids": [
                item.record_id for item in self.checkpoint_records
            ],
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "stopped_checkpoint": self.stopped_checkpoint,
            "total_accepted_draws": self.total_accepted_draws,
            "total_random_word_calls": self.total_random_word_calls,
            "physical_row_count": self.physical_row_count,
            "crn_cost_discount_draws": 0,
            "source_prior_reads": 0,
            "quotient_planner_calls": 0,
            "local_promotion_calls": 0,
            "fallback_calls": 0,
            "hidden_law_queries": 0,
            "exact_ground_evaluator_calls": 0,
            "registered_target_evidence_count": 0,
        }

    @property
    def run_id(self) -> str:
        return self._run_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "run_id": self.run_id}


def run_development_matched_direct_ground_baseline_v1(
    *,
    law: DevelopmentMatchedDirectLawV1 = (
        DevelopmentMatchedDirectLawV1.FAILURE_RESIDUE_1_OF_100
    ),
    logical_occurrence_id: str | None = None,
) -> MatchedDirectGroundRunV1:
    """Execute the strict synchronous direct arm using only observed rows."""

    if type(law) is not DevelopmentMatchedDirectLawV1:
        raise V072MatchedDirectGroundInvariantViolation(
            "development run requires one frozen law enum"
        )
    occurrence = (
        _content_id(
            "run",
            {
                "schema": (
                    "acfqp.v072_matched_direct_development_occurrence.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "law": law.value,
                "context_id": development_matched_direct_context_id_v1(),
            },
        )
        if logical_occurrence_id is None
        else _cid(logical_occurrence_id, "development occurrence")
    )
    acquisitions = tuple(
        acquire_development_matched_direct_row_v1(row, law=law)
        for row in development_matched_direct_physical_rows_v1()
    )
    records: list[MatchedDirectCheckpointRecordV1] = []
    terminal_code: MatchedDirectTerminalCodeV1 | None = None
    for ordinal, checkpoint in enumerate(CHECKPOINTS):
        if ordinal:
            acquisitions = tuple(
                extend_development_matched_direct_row_v1(
                    item,
                    validation_checkpoint=checkpoint,
                )
                for item in acquisitions
            )
        evidence = _freeze_checkpoint_evidence(
            acquisitions,
            logical_occurrence_id=occurrence,
        )
        snapshot = (
            model_builders.build_v072_cold_h2_ground_direct_model_v1(
                closure_bundle=evidence.closure_bundle,
                verified_row_projections=evidence.bound_projections,
            )
        )
        model_verification = (
            model_independent
            .verify_v072_cold_h2_ground_direct_snapshot_independently_v1(
                snapshot
            )
        )
        planner_result = lazy.solve_exact_lazy_ground_direct_h2_v1(
            snapshot.planner_projection.planner_model,
            snapshot.threshold_profile,
        )
        proof_verification = None
        if planner_result.status is lazy.ExactLazyH2SolveStatus.SOLVED:
            proof_verification = (
                lazy_independent.verify_exact_lazy_h2_solve_result_v1(
                    snapshot.planner_projection.planner_model,
                    snapshot.threshold_profile,
                    planner_result,
                )
            )
        status = (
            MatchedDirectCheckpointStatusV1.SOLVER_RESOURCE_EXHAUSTED
            if planner_result.status
            is lazy.ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED
            else (
                MatchedDirectCheckpointStatusV1.CERTIFIED
                if planner_result.audit is not None
                and planner_result.audit.status
                is robust.RobustAuditStatus.CERTIFIED
                else MatchedDirectCheckpointStatusV1.NOT_CERTIFIED
            )
        )
        prior_checkpoint = 0 if ordinal == 0 else CHECKPOINTS[ordinal - 1]
        work = MatchedDirectCheckpointWorkV1(
            checkpoint=checkpoint,
            physical_row_count=len(acquisitions),
            discovery_new_draws=(
                len(acquisitions) * DISCOVERY_DRAWS_PER_ROW
                if ordinal == 0
                else 0
            ),
            validation_new_draws=(
                len(acquisitions) * (checkpoint - prior_checkpoint)
            ),
            accepted_new_draws=(
                len(acquisitions)
                * (
                    checkpoint
                    - prior_checkpoint
                    + (
                        DISCOVERY_DRAWS_PER_ROW
                        if ordinal == 0
                        else 0
                    )
                )
            ),
            cumulative_accepted_draws=(
                len(acquisitions)
                * (DISCOVERY_DRAWS_PER_ROW + checkpoint)
            ),
            raw_observations_replayed=(
                len(acquisitions)
                * (DISCOVERY_DRAWS_PER_ROW + checkpoint)
            ),
            confidence_verifications=len(acquisitions),
            projection_verifications=len(acquisitions),
        )
        record = MatchedDirectCheckpointRecordV1(
            evidence,
            snapshot,
            model_verification,
            planner_result,
            proof_verification,
            status,
            work,
        )
        records.append(record)
        if status is MatchedDirectCheckpointStatusV1.CERTIFIED:
            terminal_code = (
                MatchedDirectTerminalCodeV1
                .MATCHED_DIRECT_GROUND_CERTIFIED
            )
            break
        if (
            status
            is MatchedDirectCheckpointStatusV1.SOLVER_RESOURCE_EXHAUSTED
        ):
            terminal_code = (
                MatchedDirectTerminalCodeV1.EXACT_LAZY_RESOURCE_EXHAUSTED
            )
            break
    if terminal_code is None:
        terminal_code = (
            MatchedDirectTerminalCodeV1
            .MAXIMUM_DIRECT_CHECKPOINT_EXHAUSTED
        )
    terminal_class = (
        MatchedDirectTerminalClassV1.PLAN_CERTIFICATE
        if terminal_code
        is MatchedDirectTerminalCodeV1.MATCHED_DIRECT_GROUND_CERTIFIED
        else (
            MatchedDirectTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
        )
    )
    stop = records[-1].evidence.checkpoint
    row_count = len(acquisitions)
    draws = row_count * (DISCOVERY_DRAWS_PER_ROW + stop)
    return MatchedDirectGroundRunV1(
        occurrence,
        law,
        tuple(records),
        terminal_class,
        terminal_code,
        stop,
        draws,
        draws,
        row_count,
    )


def run_registered_matched_direct_ground_baseline_v1(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    raise RegisteredMatchedDirectGroundExecutionLockedV1(
        "registered matched-direct execution is locked: "
        f"status={REGISTERED_TARGET_EXECUTION_STATUS}, "
        f"preregistration_id={prereg.DRAFT_PREREGISTRATION_ID}, "
        "confirmatory_execution_manifest_id=null, "
        "target_execution_allowed=false"
    )


__all__ = [
    "ARM",
    "CHECKPOINTS",
    "DISCOVERY_DRAWS_PER_ROW",
    "DevelopmentMatchedDirectLawV1",
    "DevelopmentMatchedDirectPhysicalRowV1",
    "DevelopmentMatchedDirectRowAcquisitionV1",
    "MatchedDirectCheckpointEvidenceV1",
    "MatchedDirectCheckpointRecordV1",
    "MatchedDirectCheckpointStatusV1",
    "MatchedDirectCheckpointWorkV1",
    "MatchedDirectGroundRunV1",
    "MatchedDirectRowReplayVerificationV1",
    "MatchedDirectTerminalClassV1",
    "MatchedDirectTerminalCodeV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_TARGET_EXECUTION_STATUS",
    "RegisteredMatchedDirectGroundExecutionLockedV1",
    "SCHEMA_VERSION",
    "V072MatchedDirectGroundInvariantViolation",
    "acquire_development_matched_direct_row_v1",
    "development_matched_direct_context_id_v1",
    "development_matched_direct_physical_rows_v1",
    "extend_development_matched_direct_row_v1",
    "run_development_matched_direct_ground_baseline_v1",
    "run_registered_matched_direct_ground_baseline_v1",
    "verify_development_matched_direct_row_transcripts_v1",
]
