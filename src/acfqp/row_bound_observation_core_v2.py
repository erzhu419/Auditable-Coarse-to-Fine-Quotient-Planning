"""Generic, immutable row-bound observation transcripts for V0-072.

The core in this module knows nothing about a transition law.  A backend must
produce exact source-observation documents and bind them to one immutable
row/lane/support-epoch stream.  The core then:

* copies every source document into a V2 domain;
* chains observations into content-addressed chunks;
* records an immutable prefix manifest at each preregistered checkpoint; and
* charges only newly appended draws when a prefix is extended.

Registered target acquisition is intentionally absent.  The development
adapter lives in ``v072_synthetic_row_observation_adapter_v1`` and has a
disjoint, nonconfirmatory content domain.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.partial_support_confidence_v2 import ConfidenceObservationLaneV2
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_row_bound_observation_core_v2"
CHUNK_DRAW_CAP = 256
DISCOVERY_DRAW_COUNT = 64
VALIDATION_CHECKPOINTS = (2_048, 4_096, 8_192, 16_384)
DEVELOPMENT_ROLE = (
    "DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE"
)


class RowBoundObservationV2InvariantViolation(ValueError):
    """A row, source observation, chunk, or prefix manifest is invalid."""


class RowObservationEvidenceClassV2(str, Enum):
    DEVELOPMENT_SYNTHETIC = "DEVELOPMENT_SYNTHETIC"
    REGISTERED_TARGET = "REGISTERED_TARGET"


DOMAIN_TAGS = {
    "seed": "acfqp:v072-row-observation-seed-identity:v2",
    "stream": "acfqp:v072-row-observation-stream-identity:v2",
    "sample": "acfqp:v072-row-observation-sample:v2",
    "observation": "acfqp:v072-row-bound-source-observation:v2",
    "chunk": "acfqp:v072-row-observation-transcript-chunk:v2",
    "transcript": "acfqp:v072-row-observation-transcript:v2",
    "work": "acfqp:v072-row-observation-work:v2",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("row-bound observation content domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise RowBoundObservationV2InvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise RowBoundObservationV2InvariantViolation(
            f"{field_name} must be a full content ID"
        ) from error


def _canonical_object_bytes(
    value: Mapping[str, Any],
    field_name: str,
) -> bytes:
    if not isinstance(value, Mapping):
        raise RowBoundObservationV2InvariantViolation(
            f"{field_name} must be a mapping"
        )
    try:
        encoded = canonical_json_bytes(dict(value))
        decoded = loads_canonical_json(encoded)
    except (TypeError, ValueError) as error:
        raise RowBoundObservationV2InvariantViolation(
            f"{field_name} is not canonical: {error}"
        ) from error
    if type(decoded) is not dict:
        raise RowBoundObservationV2InvariantViolation(
            f"{field_name} must decode to an object"
        )
    return encoded


def _decoded_object(value: bytes, field_name: str) -> dict[str, Any]:
    try:
        decoded = loads_canonical_json(value)
    except (TypeError, ValueError) as error:
        raise RowBoundObservationV2InvariantViolation(
            f"{field_name} bytes are not canonical JSON: {error}"
        ) from error
    if type(decoded) is not dict or canonical_json_bytes(decoded) != value:
        raise RowBoundObservationV2InvariantViolation(
            f"{field_name} bytes are not one canonical object"
        )
    return decoded


@dataclass(frozen=True, slots=True)
class RowObservationStreamIdentityV2:
    preregistration_id: str
    backend_domain_id: str
    context_id: str
    arm: str
    physical_row_id: str
    arm_free_row_id: str
    support_epoch_chain_id: str
    arm_free_support_semantics_id: str
    lane: ConfidenceObservationLaneV2
    confidence_epoch_index: int
    seed_material: tuple[tuple[str, str], ...]
    source_stream_id: str
    evidence_class: RowObservationEvidenceClassV2
    role: str
    registered_target_evidence: bool
    _seed_identity_id: str = field(init=False, repr=False)
    _stream_binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.preregistration_id, "stream preregistration"),
            (self.backend_domain_id, "stream backend domain"),
            (self.context_id, "stream context"),
            (self.physical_row_id, "stream physical row"),
            (self.arm_free_row_id, "stream arm-free row"),
            (self.support_epoch_chain_id, "stream support epoch chain"),
            (
                self.arm_free_support_semantics_id,
                "stream arm-free support semantics",
            ),
            (self.source_stream_id, "source stream"),
        ):
            _cid(value, label)
        if (
            self.preregistration_id
            != prereg.DRAFT_PREREGISTRATION_ID
            or type(self.arm) is not str
            or self.arm not in prereg.ARM_ORDER
            or type(self.lane) is not ConfidenceObservationLaneV2
            or type(self.confidence_epoch_index) is not int
            or self.confidence_epoch_index not in (0, 1, 2)
            or (
                self.confidence_epoch_index == 0
                and self.lane is not ConfidenceObservationLaneV2.DISCOVERY
            )
            or (
                self.confidence_epoch_index > 0
                and self.lane is not ConfidenceObservationLaneV2.VALIDATION
            )
            or type(self.seed_material) is not tuple
            or not self.seed_material
            or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or not item[0]
                or type(item[1]) is not str
                or not item[1]
                for item in self.seed_material
            )
            or tuple(sorted(set(self.seed_material))) != self.seed_material
            or type(self.evidence_class) is not RowObservationEvidenceClassV2
            or type(self.role) is not str
            or not self.role
            or type(self.registered_target_evidence) is not bool
        ):
            raise RowBoundObservationV2InvariantViolation(
                "row observation stream identity is malformed"
            )
        if (
            self.evidence_class
            is RowObservationEvidenceClassV2.DEVELOPMENT_SYNTHETIC
            and (
                self.role != DEVELOPMENT_ROLE
                or self.registered_target_evidence is not False
            )
        ):
            raise RowBoundObservationV2InvariantViolation(
                "development streams cannot become registered target evidence"
            )
        if (
            self.evidence_class
            is RowObservationEvidenceClassV2.REGISTERED_TARGET
        ):
            # No final execution-anchor/replay-attestation authority exists in
            # this revision.  A caller-supplied enum/boolean must never be
            # sufficient to mint registered target evidence.
            raise RowBoundObservationV2InvariantViolation(
                "registered target stream construction is unavailable until "
                "a future exact-type anchor and replay authority is ratified"
            )
        object.__setattr__(
            self,
            "_seed_identity_id",
            _content_id("seed", self._seed_payload()),
        )
        object.__setattr__(
            self,
            "_stream_binding_id",
            _content_id("stream", self._payload()),
        )

    def _seed_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_row_observation_seed_identity.v2",
            "schema_version": SCHEMA_VERSION,
            "backend_domain_id": self.backend_domain_id,
            "context_id": self.context_id,
            "arm_free_row_id": self.arm_free_row_id,
            "arm_free_support_semantics_id": (
                self.arm_free_support_semantics_id
            ),
            "lane": self.lane.value,
            "confidence_epoch_index": self.confidence_epoch_index,
            "seed_material": [
                {"key": key, "value": value}
                for key, value in self.seed_material
            ],
            "arm_serialized": False,
        }

    @property
    def seed_identity_id(self) -> str:
        return self._seed_identity_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_row_observation_stream_identity.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "backend_domain_id": self.backend_domain_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "physical_row_id": self.physical_row_id,
            "arm_free_row_id": self.arm_free_row_id,
            "support_epoch_chain_id": self.support_epoch_chain_id,
            "arm_free_support_semantics_id": (
                self.arm_free_support_semantics_id
            ),
            "lane": self.lane.value,
            "confidence_epoch_index": self.confidence_epoch_index,
            "seed_identity_id": self.seed_identity_id,
            "source_stream_id": self.source_stream_id,
            "evidence_class": self.evidence_class.value,
            "role": self.role,
            "registered_target_evidence": self.registered_target_evidence,
        }

    @property
    def stream_binding_id(self) -> str:
        return self._stream_binding_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "seed_material": [
                {"key": key, "value": value}
                for key, value in self.seed_material
            ],
            "stream_binding_id": self.stream_binding_id,
        }


@dataclass(frozen=True, slots=True)
class RowBoundRawObservationV2:
    stream_binding_id: str
    preregistration_id: str
    context_id: str
    arm: str
    physical_row_id: str
    support_epoch_chain_id: str
    stream_id: str
    lane: ConfidenceObservationLaneV2
    sequence_index: int
    source_observation_id: str
    source_commitment_id: str
    raw_digest: str
    outcome_descriptor_id: str
    source_document_bytes: bytes
    outcome_document_bytes: bytes
    _sample_id: str = field(init=False, repr=False)
    _observation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.stream_binding_id, "observation stream binding"),
            (self.preregistration_id, "observation preregistration"),
            (self.context_id, "observation context"),
            (self.physical_row_id, "observation physical row"),
            (self.support_epoch_chain_id, "observation support epoch chain"),
            (self.stream_id, "observation stream"),
            (self.source_observation_id, "source observation"),
            (self.source_commitment_id, "source commitment"),
            (self.raw_digest, "raw digest"),
            (self.outcome_descriptor_id, "outcome descriptor"),
        ):
            _cid(value, label)
        if (
            type(self.arm) is not str
            or self.arm not in prereg.ARM_ORDER
            or type(self.lane) is not ConfidenceObservationLaneV2
            or type(self.sequence_index) is not int
            or self.sequence_index <= 0
            or type(self.source_document_bytes) is not bytes
            or type(self.outcome_document_bytes) is not bytes
        ):
            raise RowBoundObservationV2InvariantViolation(
                "row-bound raw observation is malformed"
            )
        _decoded_object(self.source_document_bytes, "source observation")
        _decoded_object(self.outcome_document_bytes, "outcome descriptor")
        object.__setattr__(
            self,
            "_sample_id",
            _content_id("sample", self._sample_payload()),
        )
        object.__setattr__(
            self,
            "_observation_id",
            _content_id("observation", self._payload()),
        )

    def _sample_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_row_observation_sample.v2",
            "schema_version": SCHEMA_VERSION,
            "stream_binding_id": self.stream_binding_id,
            "source_observation_id": self.source_observation_id,
            "source_commitment_id": self.source_commitment_id,
            "sequence_index": self.sequence_index,
        }

    @property
    def sample_id(self) -> str:
        return self._sample_id

    @property
    def outcome_document(self) -> Mapping[str, Any]:
        return copy.deepcopy(
            _decoded_object(self.outcome_document_bytes, "outcome descriptor")
        )

    @property
    def source_document(self) -> Mapping[str, Any]:
        return copy.deepcopy(
            _decoded_object(self.source_document_bytes, "source observation")
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_row_bound_source_observation.v2",
            "schema_version": SCHEMA_VERSION,
            "stream_binding_id": self.stream_binding_id,
            "preregistration_id": self.preregistration_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "physical_row_id": self.physical_row_id,
            "support_epoch_chain_id": self.support_epoch_chain_id,
            "stream_id": self.stream_id,
            "lane": self.lane.value,
            "sequence_index": self.sequence_index,
            "sample_id": self.sample_id,
            "source_observation_id": self.source_observation_id,
            "source_commitment_id": self.source_commitment_id,
            "raw_digest": self.raw_digest,
            "outcome_descriptor_id": self.outcome_descriptor_id,
            "source_document": _decoded_object(
                self.source_document_bytes, "source observation"
            ),
            "outcome_document": _decoded_object(
                self.outcome_document_bytes, "outcome descriptor"
            ),
        }

    @property
    def observation_id(self) -> str:
        return self._observation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observation_id": self.observation_id}


@dataclass(frozen=True, slots=True)
class RowObservationTranscriptChunkV2:
    stream_binding_id: str
    start_sequence_index: int
    end_sequence_index: int
    previous_chunk_id: str | None
    observations: tuple[RowBoundRawObservationV2, ...]
    _chunk_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.stream_binding_id, "chunk stream binding")
        if self.previous_chunk_id is not None:
            _cid(self.previous_chunk_id, "previous chunk")
        if (
            type(self.start_sequence_index) is not int
            or type(self.end_sequence_index) is not int
            or self.start_sequence_index <= 0
            or self.end_sequence_index < self.start_sequence_index
            or type(self.observations) is not tuple
            or not self.observations
            or len(self.observations) > CHUNK_DRAW_CAP
            or len(self.observations)
            != self.end_sequence_index - self.start_sequence_index + 1
            or any(
                type(item) is not RowBoundRawObservationV2
                or item.stream_binding_id != self.stream_binding_id
                for item in self.observations
            )
            or tuple(item.sequence_index for item in self.observations)
            != tuple(
                range(self.start_sequence_index, self.end_sequence_index + 1)
            )
        ):
            raise RowBoundObservationV2InvariantViolation(
                "transcript chunk is gapped, oversized, or identity-transplanted"
            )
        object.__setattr__(
            self,
            "_chunk_id",
            _content_id("chunk", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_row_observation_transcript_chunk.v2",
            "schema_version": SCHEMA_VERSION,
            "stream_binding_id": self.stream_binding_id,
            "start_sequence_index": self.start_sequence_index,
            "end_sequence_index": self.end_sequence_index,
            "previous_chunk_id": self.previous_chunk_id,
            "observation_ids": [
                item.observation_id for item in self.observations
            ],
            "source_commitment_ids": [
                item.source_commitment_id for item in self.observations
            ],
            "exact_source_documents_embedded": True,
        }

    @property
    def chunk_id(self) -> str:
        return self._chunk_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "observations": [item.to_document() for item in self.observations],
            "chunk_id": self.chunk_id,
        }


@dataclass(frozen=True, slots=True)
class RowObservationWorkV2:
    stream_binding_id: str
    total_prefix_draws: int
    reused_prefix_draws: int
    newly_observed_draws: int
    source_commitments_verified_during_build: int
    chunks_written_during_build: int
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.stream_binding_id, "work stream binding")
        if (
            any(
                type(value) is not int or value < 0
                for value in (
                    self.total_prefix_draws,
                    self.reused_prefix_draws,
                    self.newly_observed_draws,
                    self.source_commitments_verified_during_build,
                    self.chunks_written_during_build,
                )
            )
            or self.total_prefix_draws
            != self.reused_prefix_draws + self.newly_observed_draws
            or self.source_commitments_verified_during_build
            != self.newly_observed_draws
            or (
                self.newly_observed_draws > 0
                and self.chunks_written_during_build <= 0
            )
        ):
            raise RowBoundObservationV2InvariantViolation(
                "row observation work does not reconcile"
            )
        object.__setattr__(
            self,
            "_work_id",
            _content_id("work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_row_observation_work.v2",
            "schema_version": SCHEMA_VERSION,
            "stream_binding_id": self.stream_binding_id,
            "total_prefix_draws": self.total_prefix_draws,
            "reused_prefix_draws": self.reused_prefix_draws,
            "newly_observed_draws": self.newly_observed_draws,
            "source_commitments_verified_during_build": (
                self.source_commitments_verified_during_build
            ),
            "chunks_written_during_build": self.chunks_written_during_build,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class RowObservationTranscriptV2:
    stream_identity: RowObservationStreamIdentityV2
    selected_checkpoint_draw_count: int
    chunks: tuple[RowObservationTranscriptChunkV2, ...]
    previous_transcript_id: str | None
    previous_draw_count: int
    work: RowObservationWorkV2
    immutable_prefix: bool = True
    _transcript_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.previous_transcript_id is not None:
            _cid(self.previous_transcript_id, "previous transcript")
        if (
            type(self.stream_identity) is not RowObservationStreamIdentityV2
            or type(self.selected_checkpoint_draw_count) is not int
            or self.selected_checkpoint_draw_count <= 0
            or type(self.chunks) is not tuple
            or not self.chunks
            or any(
                type(item) is not RowObservationTranscriptChunkV2
                for item in self.chunks
            )
            or self.previous_draw_count < 0
            or type(self.work) is not RowObservationWorkV2
            or self.work.stream_binding_id
            != self.stream_identity.stream_binding_id
            or self.work.total_prefix_draws
            != self.selected_checkpoint_draw_count
            or self.work.reused_prefix_draws != self.previous_draw_count
            or self.immutable_prefix is not True
        ):
            raise RowBoundObservationV2InvariantViolation(
                "row observation transcript is malformed"
            )
        if self.stream_identity.lane is ConfidenceObservationLaneV2.DISCOVERY:
            if (
                self.selected_checkpoint_draw_count != DISCOVERY_DRAW_COUNT
                or self.previous_transcript_id is not None
                or self.previous_draw_count != 0
            ):
                raise RowBoundObservationV2InvariantViolation(
                    "discovery transcript must be exactly one fresh 64-draw prefix"
                )
        elif self.selected_checkpoint_draw_count not in VALIDATION_CHECKPOINTS:
            raise RowBoundObservationV2InvariantViolation(
                "validation transcript checkpoint is not preregistered"
            )
        if (
            (self.previous_draw_count == 0)
            != (self.previous_transcript_id is None)
            or self.previous_draw_count >= self.selected_checkpoint_draw_count
        ):
            raise RowBoundObservationV2InvariantViolation(
                "transcript extension ancestry is invalid"
            )
        expected_start = 1
        previous_chunk_id: str | None = None
        for chunk in self.chunks:
            if (
                chunk.stream_binding_id
                != self.stream_identity.stream_binding_id
                or chunk.start_sequence_index != expected_start
                or chunk.previous_chunk_id != previous_chunk_id
            ):
                raise RowBoundObservationV2InvariantViolation(
                    "transcript chunk chain is incomplete or transplanted"
                )
            expected_start = chunk.end_sequence_index + 1
            previous_chunk_id = chunk.chunk_id
        if expected_start - 1 != self.selected_checkpoint_draw_count:
            raise RowBoundObservationV2InvariantViolation(
                "transcript chunks do not cover the selected prefix"
            )
        object.__setattr__(
            self,
            "_transcript_id",
            _content_id("transcript", self._payload()),
        )

    @property
    def observations(self) -> tuple[RowBoundRawObservationV2, ...]:
        return tuple(
            observation
            for chunk in self.chunks
            for observation in chunk.observations
        )

    @property
    def terminal_chunk_id(self) -> str:
        return self.chunks[-1].chunk_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_row_observation_transcript.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "stream_binding_id": self.stream_identity.stream_binding_id,
            "selected_checkpoint_draw_count": (
                self.selected_checkpoint_draw_count
            ),
            "chunk_ids": [item.chunk_id for item in self.chunks],
            "terminal_chunk_id": self.terminal_chunk_id,
            "previous_transcript_id": self.previous_transcript_id,
            "previous_draw_count": self.previous_draw_count,
            "work_id": self.work.work_id,
            "immutable_prefix": True,
        }

    @property
    def transcript_id(self) -> str:
        return self._transcript_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "stream_identity": self.stream_identity.to_document(),
            "chunks": [item.to_document() for item in self.chunks],
            "work": self.work.to_document(),
            "transcript_id": self.transcript_id,
        }


def freeze_source_observation_v2(
    *,
    stream_identity: RowObservationStreamIdentityV2,
    sequence_index: int,
    source_observation_id: str,
    source_commitment_id: str,
    raw_digest: str,
    outcome_descriptor_id: str,
    source_document: Mapping[str, Any],
    outcome_document: Mapping[str, Any],
) -> RowBoundRawObservationV2:
    """Copy a backend observation into the generic V2 transcript domain."""

    if type(stream_identity) is not RowObservationStreamIdentityV2:
        raise RowBoundObservationV2InvariantViolation(
            "source observation requires a concrete stream identity"
        )
    return RowBoundRawObservationV2(
        stream_binding_id=stream_identity.stream_binding_id,
        preregistration_id=stream_identity.preregistration_id,
        context_id=stream_identity.context_id,
        arm=stream_identity.arm,
        physical_row_id=stream_identity.physical_row_id,
        support_epoch_chain_id=stream_identity.support_epoch_chain_id,
        stream_id=stream_identity.source_stream_id,
        lane=stream_identity.lane,
        sequence_index=sequence_index,
        source_observation_id=source_observation_id,
        source_commitment_id=source_commitment_id,
        raw_digest=raw_digest,
        outcome_descriptor_id=outcome_descriptor_id,
        source_document_bytes=_canonical_object_bytes(
            source_document, "source observation"
        ),
        outcome_document_bytes=_canonical_object_bytes(
            outcome_document, "outcome descriptor"
        ),
    )


def recorded_transition_descriptor_document_v2(
    descriptor: Any,
) -> tuple[str, Mapping[str, Any]]:
    """Return the canonical target semantic descriptor without changing its ID.

    This is deliberately a lazy exact-type check.  It does not authorize a
    target stream; it only prevents a future adapter from inventing a second
    support-descriptor domain incompatible with the public novel-child
    cardinality authority.
    """

    from acfqp.public_novel_child_cardinality_authority_v2 import (
        RecordedTransitionDescriptorV2,
    )

    if type(descriptor) is not RecordedTransitionDescriptorV2:
        raise RowBoundObservationV2InvariantViolation(
            "target semantic outcomes require the exact recorded-transition "
            "descriptor authority"
        )
    document = descriptor.to_document()
    if (
        type(document) is not dict
        or document.get("descriptor_id") != descriptor.descriptor_id
    ):
        raise RowBoundObservationV2InvariantViolation(
            "recorded transition descriptor serialization is invalid"
        )
    return descriptor.descriptor_id, copy.deepcopy(document)


def build_or_extend_row_observation_transcript_v2(
    *,
    stream_identity: RowObservationStreamIdentityV2,
    selected_checkpoint_draw_count: int,
    new_observations: tuple[RowBoundRawObservationV2, ...],
    previous: RowObservationTranscriptV2 | None = None,
) -> RowObservationTranscriptV2:
    """Append a checkpoint suffix while preserving every old chunk byte-for-byte."""

    if (
        type(stream_identity) is not RowObservationStreamIdentityV2
        or type(new_observations) is not tuple
        or not new_observations
        or any(
            type(item) is not RowBoundRawObservationV2
            for item in new_observations
        )
    ):
        raise RowBoundObservationV2InvariantViolation(
            "transcript construction requires a nonempty exact suffix"
        )
    if previous is None:
        old_chunks: tuple[RowObservationTranscriptChunkV2, ...] = ()
        previous_count = 0
        previous_id = None
        previous_chunk_id = None
    else:
        if (
            type(previous) is not RowObservationTranscriptV2
            or previous.stream_identity != stream_identity
            or previous.selected_checkpoint_draw_count
            >= selected_checkpoint_draw_count
        ):
            raise RowBoundObservationV2InvariantViolation(
                "prefix extension changed stream identity or did not grow"
            )
        old_chunks = previous.chunks
        previous_count = previous.selected_checkpoint_draw_count
        previous_id = previous.transcript_id
        previous_chunk_id = previous.terminal_chunk_id
    if (
        tuple(item.sequence_index for item in new_observations)
        != tuple(range(previous_count + 1, selected_checkpoint_draw_count + 1))
        or len(new_observations)
        != selected_checkpoint_draw_count - previous_count
        or any(
            item.stream_binding_id != stream_identity.stream_binding_id
            for item in new_observations
        )
    ):
        raise RowBoundObservationV2InvariantViolation(
            "new observations are not the exact incremental suffix"
        )
    new_chunks: list[RowObservationTranscriptChunkV2] = []
    for offset in range(0, len(new_observations), CHUNK_DRAW_CAP):
        members = new_observations[offset : offset + CHUNK_DRAW_CAP]
        chunk = RowObservationTranscriptChunkV2(
            stream_identity.stream_binding_id,
            members[0].sequence_index,
            members[-1].sequence_index,
            previous_chunk_id,
            members,
        )
        new_chunks.append(chunk)
        previous_chunk_id = chunk.chunk_id
    work = RowObservationWorkV2(
        stream_identity.stream_binding_id,
        selected_checkpoint_draw_count,
        previous_count,
        len(new_observations),
        len(new_observations),
        len(new_chunks),
    )
    return RowObservationTranscriptV2(
        stream_identity,
        selected_checkpoint_draw_count,
        old_chunks + tuple(new_chunks),
        previous_id,
        previous_count,
        work,
    )


__all__ = [
    "CHUNK_DRAW_CAP",
    "DEVELOPMENT_ROLE",
    "DISCOVERY_DRAW_COUNT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RowBoundObservationV2InvariantViolation",
    "RowBoundRawObservationV2",
    "RowObservationEvidenceClassV2",
    "RowObservationStreamIdentityV2",
    "RowObservationTranscriptChunkV2",
    "RowObservationTranscriptV2",
    "RowObservationWorkV2",
    "SCHEMA_VERSION",
    "VALIDATION_CHECKPOINTS",
    "build_or_extend_row_observation_transcript_v2",
    "freeze_source_observation_v2",
    "recorded_transition_descriptor_document_v2",
]
