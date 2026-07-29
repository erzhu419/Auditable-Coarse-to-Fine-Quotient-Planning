"""Content-addressed operational reconciliation authority for V0-072.

This module reconciles native observation and planning artifacts; it never
accepts caller counts, discounts, or terminal outcomes.  Supported sources:

* immutable ``row_core`` transcript series;
* the strict matched-direct ground run; and
* compressed incremental-materializer streams and commitment ranges.

Every accepted draw remains independently addressable.  Resident row
transcripts use their arm-bound source commitment IDs.  Compressed streams
retain only a content-addressed range proof; individual commitment IDs are
derived lazily from ``(stream_id, accepted_draw_index, word)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Iterable, Iterator, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_confidence_v2 as confidence
from acfqp import row_bound_observation_core_v2 as row_core
from acfqp import target_preauthorization_selector_v2 as selector
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_development_complete_adaptive_run_v1 as complete
from acfqp import v072_incremental_materializer_v1 as materializer
from acfqp import v072_matched_direct_ground_baseline_v1 as matched


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_campaign_reconciliation_authority_v1"
REGISTERED_EXECUTION_STATUS = "LOCKED_NONAUTHORIZING_DRAFT"


class V072CampaignReconciliationInvariantViolation(ValueError):
    """A commitment, work, access, terminal, or denominator claim is invalid."""


class RegisteredCampaignReconciliationLockedV1(RuntimeError):
    """Registered reconciliation awaits the final execution manifest."""


class ReconciliationSourceKindV1(str, Enum):
    ROW_CORE_RESIDENT = "ROW_CORE_RESIDENT"
    MATCHED_DIRECT_RUN = "MATCHED_DIRECT_RUN"
    INCREMENTAL_COMPRESSED = "INCREMENTAL_COMPRESSED"
    COMPLETE_ADAPTIVE_PLANNING_COMPRESSED = (
        "COMPLETE_ADAPTIVE_PLANNING_COMPRESSED"
    )


class DrawStageV1(str, Enum):
    COLD_DISCOVERY = "COLD_DISCOVERY"
    COLD_VALIDATION = "COLD_VALIDATION"
    DIRECT_VALIDATION_EXTENSION = "DIRECT_VALIDATION_EXTENSION"
    ROW_CORE_VALIDATION_EXTENSION = "ROW_CORE_VALIDATION_EXTENSION"
    INCREMENTAL_PARENT_VALIDATION = "INCREMENTAL_PARENT_VALIDATION"
    INCREMENTAL_CHILD_DISCOVERY = "INCREMENTAL_CHILD_DISCOVERY"
    INCREMENTAL_CHILD_VALIDATION = "INCREMENTAL_CHILD_VALIDATION"


class CommitmentSchemeV1(str, Enum):
    RESIDENT_ARM_BOUND_SOURCE_COMMITMENT = (
        "RESIDENT_ARM_BOUND_SOURCE_COMMITMENT"
    )
    COMPRESSED_STREAM_INDEX_WORD = "COMPRESSED_STREAM_INDEX_WORD"


class ReconciliationTerminalClassV1(str, Enum):
    PLAN_CERTIFICATE = "PLAN_CERTIFICATE"
    ATTEMPT_CLOSURE_NONCERTIFICATE = "ATTEMPT_CLOSURE_NONCERTIFICATE"


class ReconciliationTerminalCodeV1(str, Enum):
    OBSERVATION_ONLY_NONCERTIFICATE = "OBSERVATION_ONLY_NONCERTIFICATE"
    MATCHED_DIRECT_GROUND_CERTIFIED = "MATCHED_DIRECT_GROUND_CERTIFIED"
    MATCHED_DIRECT_MAXIMUM_CHECKPOINT_EXHAUSTED = (
        "MATCHED_DIRECT_MAXIMUM_CHECKPOINT_EXHAUSTED"
    )
    MATCHED_DIRECT_SOLVER_RESOURCE_EXHAUSTED = (
        "MATCHED_DIRECT_SOLVER_RESOURCE_EXHAUSTED"
    )
    INCREMENTAL_PENDING_MODEL_REBUILD_NONCERTIFICATE = (
        "INCREMENTAL_PENDING_MODEL_REBUILD_NONCERTIFICATE"
    )
    ADAPTIVE_POSTBUILD_CERTIFIED = "ADAPTIVE_POSTBUILD_CERTIFIED"
    PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD = (
        "PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD"
    )
    PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD = (
        "PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD"
    )
    ADAPTIVE_MAXIMUM_ROUNDS_EXHAUSTED_NONCERTIFICATE = (
        "ADAPTIVE_MAXIMUM_ROUNDS_EXHAUSTED_NONCERTIFICATE"
    )
    ADAPTIVE_SOLVER_RESOURCE_EXHAUSTED_NONCERTIFICATE = (
        "ADAPTIVE_SOLVER_RESOURCE_EXHAUSTED_NONCERTIFICATE"
    )


class AccessOrderKindV1(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PREAUTHORIZED_INCREMENTAL = "PREAUTHORIZED_INCREMENTAL"


class CampaignOrderProfileV1(str, Enum):
    DEVELOPMENT_CONTENT_ID = "DEVELOPMENT_CONTENT_ID_V1"
    CONTEXT_MAJOR_FROZEN_ARM_ORDER = (
        "CONTEXT_MAJOR_THEN_FROZEN_ARM_ORDER_V1"
    )


DOMAIN_TAGS = {
    "row_series": "acfqp:v072-reconciliation-row-core-series:v1",
    "crn_group": "acfqp:v072-reconciliation-crn-pairing-group:v1",
    "range": "acfqp:v072-reconciliation-accepted-draw-range:v1",
    "work": "acfqp:v072-reconciliation-operational-work:v1",
    "access": "acfqp:v072-reconciliation-access-order:v1",
    "occurrence": "acfqp:v072-reconciliation-occurrence:v1",
    "campaign": "acfqp:v072-reconciliation-campaign-ledger:v1",
    "context_binding": (
        "acfqp:v072-reconciliation-development-context-binding:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("campaign reconciliation domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072CampaignReconciliationInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072CampaignReconciliationInvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _ordered_commitment_digest(values: Iterable[str]) -> tuple[str, str, str, int]:
    digest = hashlib.sha256()
    first = ""
    last = ""
    count = 0
    seen: set[str] = set()
    for value in values:
        _cid(value, "accepted draw commitment")
        if count == 0:
            first = value
        last = value
        digest.update(bytes.fromhex(value))
        seen.add(value)
        count += 1
    if count <= 0 or len(seen) != count:
        raise V072CampaignReconciliationInvariantViolation(
            "commitment range is empty or contains duplicate accepted draws"
        )
    return first, last, digest.hexdigest(), count


def _crn_pairing_group_id(
    *,
    arm_free_stream_identity_id: str,
    first_index: int,
    last_index: int,
) -> str:
    _cid(arm_free_stream_identity_id, "arm-free stream identity")
    return _content_id(
        "crn_group",
        {
            "schema": "acfqp.v072_reconciliation_crn_pairing_group.v1",
            "schema_version": SCHEMA_VERSION,
            "arm_free_stream_identity_id": arm_free_stream_identity_id,
            "accepted_draw_index_range": {
                "first": first_index,
                "last": last_index,
            },
            "arm_serialized": False,
            "cost_discount_allowed": False,
        },
    )


@dataclass(frozen=True, slots=True)
class RowCoreObservationSeriesV1:
    """One immutable row prefix family; terminal is always observation-only."""

    discovery_transcript: row_core.RowObservationTranscriptV2
    validation_history: tuple[row_core.RowObservationTranscriptV2, ...]
    _series_id: str = field(init=False, repr=False)
    _logical_occurrence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.discovery_transcript)
            is not row_core.RowObservationTranscriptV2
            or self.discovery_transcript.stream_identity.lane
            is not confidence.ConfidenceObservationLaneV2.DISCOVERY
            or self.discovery_transcript.selected_checkpoint_draw_count != 64
            or type(self.validation_history) is not tuple
            or not self.validation_history
            or any(
                type(item) is not row_core.RowObservationTranscriptV2
                for item in self.validation_history
            )
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "row-core series lacks one exact discovery/validation family"
            )
        discovery_stream = self.discovery_transcript.stream_identity
        prior: row_core.RowObservationTranscriptV2 | None = None
        for item in self.validation_history:
            if (
                item.stream_identity.lane
                is not confidence.ConfidenceObservationLaneV2.VALIDATION
                or item.stream_identity.context_id
                != discovery_stream.context_id
                or item.stream_identity.arm != discovery_stream.arm
                or item.stream_identity.physical_row_id
                != discovery_stream.physical_row_id
                or item.previous_transcript_id
                != (None if prior is None else prior.transcript_id)
                or item.previous_draw_count
                != (
                    0
                    if prior is None
                    else prior.selected_checkpoint_draw_count
                )
                or (
                    prior is not None
                    and item.chunks[: len(prior.chunks)] != prior.chunks
                )
            ):
                raise V072CampaignReconciliationInvariantViolation(
                    "row-core validation prefix was reset, dropped, or transplanted"
                )
            prior = item
        payload = {
            "schema": "acfqp.v072_reconciliation_row_core_series.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": discovery_stream.context_id,
            "arm": discovery_stream.arm,
            "physical_row_id": discovery_stream.physical_row_id,
            "discovery_transcript_id": (
                self.discovery_transcript.transcript_id
            ),
            "validation_transcript_ids": [
                item.transcript_id for item in self.validation_history
            ],
            "observation_only": True,
            "registered_target_evidence": False,
        }
        series_id = _content_id("row_series", payload)
        occurrence_id = _content_id(
            "occurrence",
            {
                "schema": (
                    "acfqp.v072_reconciliation_observation_only_occurrence.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "series_id": series_id,
                "context_id": discovery_stream.context_id,
                "arm": discovery_stream.arm,
                "physical_row_id": discovery_stream.physical_row_id,
            },
        )
        object.__setattr__(self, "_series_id", series_id)
        object.__setattr__(
            self, "_logical_occurrence_id", occurrence_id
        )

    @property
    def series_id(self) -> str:
        return self._series_id

    @property
    def logical_occurrence_id(self) -> str:
        return self._logical_occurrence_id

    @property
    def arm(self) -> str:
        return self.discovery_transcript.stream_identity.arm

    @property
    def context_id(self) -> str:
        return self.discovery_transcript.stream_identity.context_id

    @property
    def physical_row_id(self) -> str:
        return self.discovery_transcript.stream_identity.physical_row_id


@dataclass(frozen=True, slots=True)
class AcceptedDrawCommitmentRangeV1:
    logical_occurrence_id: str
    arm: str
    context_id: str
    round_index: int
    source_kind: ReconciliationSourceKindV1
    stage: DrawStageV1
    commitment_scheme: CommitmentSchemeV1
    physical_row_id: str
    stream_id: str
    source_artifact_id: str
    first_accepted_draw_index: int
    last_accepted_draw_index: int
    draw_count: int
    first_commitment_id: str
    last_commitment_id: str
    ordered_commitment_digest: str
    crn_pairing_group_id: str
    source_range_proof_id: str | None
    resident_commitment_objects: int
    compressed_commitment_objects: int
    accepted_exactly_once: bool = True
    _range_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.logical_occurrence_id, "range occurrence"),
            (self.context_id, "range context"),
            (self.physical_row_id, "range physical row"),
            (self.stream_id, "range stream"),
            (self.source_artifact_id, "range source artifact"),
            (self.first_commitment_id, "range first commitment"),
            (self.last_commitment_id, "range last commitment"),
            (self.ordered_commitment_digest, "range commitment digest"),
            (self.crn_pairing_group_id, "range CRN group"),
        ):
            _cid(value, label)
        if self.source_range_proof_id is not None:
            _cid(self.source_range_proof_id, "range source proof")
        if (
            type(self.arm) is not str
            or not self.arm
            or self.round_index not in (0, 1, 2)
            or type(self.source_kind) is not ReconciliationSourceKindV1
            or type(self.stage) is not DrawStageV1
            or type(self.commitment_scheme) is not CommitmentSchemeV1
            or type(self.first_accepted_draw_index) is not int
            or type(self.last_accepted_draw_index) is not int
            or self.first_accepted_draw_index < 0
            or self.last_accepted_draw_index
            < self.first_accepted_draw_index
            or self.draw_count
            != self.last_accepted_draw_index
            - self.first_accepted_draw_index
            + 1
            or self.draw_count <= 0
            or self.accepted_exactly_once is not True
            or (
                self.commitment_scheme
                is CommitmentSchemeV1.RESIDENT_ARM_BOUND_SOURCE_COMMITMENT
                and (
                    self.source_range_proof_id is not None
                    or self.resident_commitment_objects != self.draw_count
                    or self.compressed_commitment_objects != 0
                )
            )
            or (
                self.commitment_scheme
                is CommitmentSchemeV1.COMPRESSED_STREAM_INDEX_WORD
                and (
                    self.source_range_proof_id is None
                    or self.resident_commitment_objects != 0
                    or self.compressed_commitment_objects != self.draw_count
                )
            )
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "accepted-draw range schema or storage semantics are invalid"
            )
        object.__setattr__(
            self,
            "_range_id",
            _content_id("range", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_reconciliation_accepted_draw_range.v1",
            "schema_version": SCHEMA_VERSION,
            "logical_occurrence_id": self.logical_occurrence_id,
            "arm": self.arm,
            "context_id": self.context_id,
            "round_index": self.round_index,
            "source_kind": self.source_kind.value,
            "stage": self.stage.value,
            "commitment_scheme": self.commitment_scheme.value,
            "physical_row_id": self.physical_row_id,
            "stream_id": self.stream_id,
            "source_artifact_id": self.source_artifact_id,
            "accepted_draw_index_range": {
                "first": self.first_accepted_draw_index,
                "last": self.last_accepted_draw_index,
            },
            "draw_count": self.draw_count,
            "first_commitment_id": self.first_commitment_id,
            "last_commitment_id": self.last_commitment_id,
            "ordered_commitment_digest": self.ordered_commitment_digest,
            "crn_pairing_group_id": self.crn_pairing_group_id,
            "source_range_proof_id": self.source_range_proof_id,
            "resident_commitment_objects": self.resident_commitment_objects,
            "compressed_commitment_objects": (
                self.compressed_commitment_objects
            ),
            "accepted_exactly_once": True,
            "crn_cost_discount_draws": 0,
        }

    @property
    def range_id(self) -> str:
        return self._range_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "range_id": self.range_id}


@dataclass(frozen=True, slots=True)
class ReconciledOperationalWorkV1:
    accepted_draws: int
    random_word_calls: int
    resident_commitment_count: int
    compressed_commitment_count: int
    cold_discovery_draws: int
    cold_validation_draws: int
    row_core_validation_extension_draws: int
    direct_extension_draws: int
    incremental_parent_validation_draws: int
    incremental_child_discovery_draws: int
    incremental_child_validation_draws: int
    direct_checkpoint_attempts: int
    failed_direct_checkpoint_attempts: int
    failed_parent_certificate_attempts: int
    failed_incremental_postbuild_audits: int
    failed_certificate_attempts: int
    direct_model_builds: int
    direct_model_independent_verifications: int
    direct_solver_calls: int
    direct_proof_verifications: int
    incremental_materializer_calls: int
    incremental_observer_calls: int
    incremental_postbuild_model_builds: int
    incremental_postbuild_model_independent_verifications: int
    incremental_postbuild_solver_calls: int
    incremental_postbuild_proof_verifications: int
    incremental_postbuild_audits: int
    preauthorization_public_metadata_reads: int
    preauthorization_counterfactual_evaluations: int
    preauthorization_source_consensus_lookups: int
    native_zero_counter_count: int
    terminal_artifact_count: int = 1
    crn_cost_discount_draws: int = 0
    caller_supplied_counts: bool = False
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        integer_values = tuple(
            getattr(self, name)
            for name in self.__dataclass_fields__
            if name
            not in (
                "_work_id",
                "caller_supplied_counts",
            )
        )
        categorized_draws = (
            self.cold_discovery_draws
            + self.cold_validation_draws
            + self.row_core_validation_extension_draws
            + self.direct_extension_draws
            + self.incremental_parent_validation_draws
            + self.incremental_child_discovery_draws
            + self.incremental_child_validation_draws
        )
        if (
            any(type(value) is not int or value < 0 for value in integer_values)
            or self.accepted_draws != categorized_draws
            or self.random_word_calls != self.accepted_draws
            or self.resident_commitment_count
            + self.compressed_commitment_count
            != self.accepted_draws
            or self.failed_direct_checkpoint_attempts
            > self.direct_checkpoint_attempts
            or self.failed_certificate_attempts
            != (
                self.failed_direct_checkpoint_attempts
                + self.failed_parent_certificate_attempts
                + self.failed_incremental_postbuild_audits
            )
            or self.terminal_artifact_count != 1
            or self.crn_cost_discount_draws != 0
            or self.caller_supplied_counts is not False
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "operational work is incomplete, discounted, or caller supplied"
            )
        object.__setattr__(
            self,
            "_work_id",
            _content_id("work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_reconciliation_operational_work.v1",
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in (
                    "accepted_draws",
                    "random_word_calls",
                    "resident_commitment_count",
                    "compressed_commitment_count",
                    "cold_discovery_draws",
                    "cold_validation_draws",
                    "row_core_validation_extension_draws",
                    "direct_extension_draws",
                    "incremental_parent_validation_draws",
                    "incremental_child_discovery_draws",
                    "incremental_child_validation_draws",
                    "direct_checkpoint_attempts",
                    "failed_direct_checkpoint_attempts",
                    "failed_parent_certificate_attempts",
                    "failed_incremental_postbuild_audits",
                    "failed_certificate_attempts",
                    "direct_model_builds",
                    "direct_model_independent_verifications",
                    "direct_solver_calls",
                    "direct_proof_verifications",
                    "incremental_materializer_calls",
                    "incremental_observer_calls",
                    "incremental_postbuild_model_builds",
                    (
                        "incremental_postbuild_"
                        "model_independent_verifications"
                    ),
                    "incremental_postbuild_solver_calls",
                    "incremental_postbuild_proof_verifications",
                    "incremental_postbuild_audits",
                    "preauthorization_public_metadata_reads",
                    "preauthorization_counterfactual_evaluations",
                    "preauthorization_source_consensus_lookups",
                    "native_zero_counter_count",
                )
            },
            "terminal_artifact_count": 1,
            "crn_cost_discount_draws": 0,
            "caller_supplied_counts": False,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


def _zero_work(**changes: int) -> ReconciledOperationalWorkV1:
    values = {
        "accepted_draws": 0,
        "random_word_calls": 0,
        "resident_commitment_count": 0,
        "compressed_commitment_count": 0,
        "cold_discovery_draws": 0,
        "cold_validation_draws": 0,
        "row_core_validation_extension_draws": 0,
        "direct_extension_draws": 0,
        "incremental_parent_validation_draws": 0,
        "incremental_child_discovery_draws": 0,
        "incremental_child_validation_draws": 0,
        "direct_checkpoint_attempts": 0,
        "failed_direct_checkpoint_attempts": 0,
        "failed_parent_certificate_attempts": 0,
        "failed_incremental_postbuild_audits": 0,
        "failed_certificate_attempts": 0,
        "direct_model_builds": 0,
        "direct_model_independent_verifications": 0,
        "direct_solver_calls": 0,
        "direct_proof_verifications": 0,
        "incremental_materializer_calls": 0,
        "incremental_observer_calls": 0,
        "incremental_postbuild_model_builds": 0,
        "incremental_postbuild_model_independent_verifications": 0,
        "incremental_postbuild_solver_calls": 0,
        "incremental_postbuild_proof_verifications": 0,
        "incremental_postbuild_audits": 0,
        "preauthorization_public_metadata_reads": 0,
        "preauthorization_counterfactual_evaluations": 0,
        "preauthorization_source_consensus_lookups": 0,
        "native_zero_counter_count": 0,
    }
    unknown = set(changes) - set(values)
    if unknown:
        raise V072CampaignReconciliationInvariantViolation(
            f"unknown work leaves: {sorted(unknown)}"
        )
    values.update(changes)
    return ReconciledOperationalWorkV1(**values)


@dataclass(frozen=True, slots=True)
class ReconciledAccessOrderV1:
    kind: AccessOrderKindV1
    source_artifact_id: str
    access_log_id: str | None
    authorization_id: str | None
    authorization_freeze_id: str | None
    round_index: int | None
    authorization_sequence: int | None
    first_execution_sequence: int | None
    native_zero_counter_ids: tuple[str, ...]
    native_zero_paths: tuple[str, ...]
    native_zero_values: tuple[int, ...]
    authorization_frozen_before_execution: bool
    _access_order_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.source_artifact_id, "access source artifact")
        applicable = self.kind is AccessOrderKindV1.PREAUTHORIZED_INCREMENTAL
        if applicable:
            for value, label in (
                (self.access_log_id, "access log"),
                (self.authorization_id, "authorization"),
                (self.authorization_freeze_id, "authorization freeze"),
            ):
                _cid(value, label)
            if (
                self.round_index not in (1, 2)
                or self.authorization_sequence != 2 * self.round_index - 1
                or self.first_execution_sequence
                != self.authorization_sequence + 1
                or self.native_zero_paths
                != selector.REQUIRED_NATIVE_ZERO_PATHS
                or len(self.native_zero_counter_ids)
                != len(self.native_zero_paths)
                or any(
                    _cid(item, "native-zero counter") != item
                    for item in self.native_zero_counter_ids
                )
                or self.native_zero_values
                != tuple(0 for _ in self.native_zero_paths)
                or self.authorization_frozen_before_execution is not True
            ):
                raise V072CampaignReconciliationInvariantViolation(
                    "preauthorization order or native-zero record is invalid"
                )
        elif (
            self.kind is not AccessOrderKindV1.NOT_APPLICABLE
            or any(
                value is not None
                for value in (
                    self.access_log_id,
                    self.authorization_id,
                    self.authorization_freeze_id,
                    self.round_index,
                    self.authorization_sequence,
                    self.first_execution_sequence,
                )
            )
            or self.native_zero_counter_ids
            or self.native_zero_paths
            or self.native_zero_values
            or self.authorization_frozen_before_execution is not False
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "non-applicable access order contains execution claims"
            )
        object.__setattr__(
            self,
            "_access_order_id",
            _content_id("access", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_reconciliation_access_order.v1",
            "schema_version": SCHEMA_VERSION,
            "kind": self.kind.value,
            "source_artifact_id": self.source_artifact_id,
            "access_log_id": self.access_log_id,
            "authorization_id": self.authorization_id,
            "authorization_freeze_id": self.authorization_freeze_id,
            "round_index": self.round_index,
            "authorization_sequence": self.authorization_sequence,
            "first_execution_sequence": self.first_execution_sequence,
            "native_zero_counter_ids": list(self.native_zero_counter_ids),
            "native_zero_paths": list(self.native_zero_paths),
            "native_zero_values": list(self.native_zero_values),
            "authorization_frozen_before_execution": (
                self.authorization_frozen_before_execution
            ),
        }

    @property
    def access_order_id(self) -> str:
        return self._access_order_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "access_order_id": self.access_order_id}


def _not_applicable_access(source_artifact_id: str) -> ReconciledAccessOrderV1:
    return ReconciledAccessOrderV1(
        AccessOrderKindV1.NOT_APPLICABLE,
        source_artifact_id,
        None,
        None,
        None,
        None,
        None,
        None,
        (),
        (),
        (),
        False,
    )


@dataclass(frozen=True, slots=True)
class ReconciledOperationalOccurrenceV1:
    logical_occurrence_id: str
    arm: str
    context_id: str
    source_kind: ReconciliationSourceKindV1
    source_artifact_id: str
    draw_ranges: tuple[AcceptedDrawCommitmentRangeV1, ...]
    work: ReconciledOperationalWorkV1
    access_order: ReconciledAccessOrderV1
    terminal_class: ReconciliationTerminalClassV1
    terminal_code: ReconciliationTerminalCodeV1
    denominator_included: bool = True
    terminal_derived_from_source: bool = True
    caller_supplied_terminal_outcome: bool = False
    crn_cost_discount_draws: int = 0
    additional_access_orders: tuple[ReconciledAccessOrderV1, ...] = ()
    _occurrence_record_id: str = field(init=False, repr=False)
    _source_object: Any = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        for value, label in (
            (self.logical_occurrence_id, "occurrence identity"),
            (self.context_id, "occurrence context"),
            (self.source_artifact_id, "occurrence source"),
        ):
            _cid(value, label)
        if (
            type(self.arm) is not str
            or not self.arm
            or type(self.source_kind) is not ReconciliationSourceKindV1
            or type(self.draw_ranges) is not tuple
            or not self.draw_ranges
            or any(
                type(item) is not AcceptedDrawCommitmentRangeV1
                for item in self.draw_ranges
            )
            or tuple(item.range_id for item in self.draw_ranges)
            != tuple(sorted({item.range_id for item in self.draw_ranges}))
            or any(
                item.logical_occurrence_id != self.logical_occurrence_id
                or item.arm != self.arm
                or item.context_id != self.context_id
                or item.source_kind is not self.source_kind
                for item in self.draw_ranges
            )
            or type(self.work) is not ReconciledOperationalWorkV1
            or self.work.accepted_draws
            != sum(item.draw_count for item in self.draw_ranges)
            or self.work.resident_commitment_count
            != sum(
                item.resident_commitment_objects
                for item in self.draw_ranges
            )
            or self.work.compressed_commitment_count
            != sum(
                item.compressed_commitment_objects
                for item in self.draw_ranges
            )
            or type(self.access_order) is not ReconciledAccessOrderV1
            or self.access_order.source_artifact_id
            != self.source_artifact_id
            or type(self.additional_access_orders) is not tuple
            or any(
                type(item) is not ReconciledAccessOrderV1
                or item.source_artifact_id != self.source_artifact_id
                for item in self.additional_access_orders
            )
            or (
                self.additional_access_orders
                and (
                    self.access_order.round_index != 1
                    or tuple(
                        item.round_index
                        for item in self.additional_access_orders
                    )
                    != tuple(
                        range(2, 2 + len(self.additional_access_orders))
                    )
                )
            )
            or type(self.terminal_class) is not ReconciliationTerminalClassV1
            or type(self.terminal_code) is not ReconciliationTerminalCodeV1
            or self.denominator_included is not True
            or self.terminal_derived_from_source is not True
            or self.caller_supplied_terminal_outcome is not False
            or self.crn_cost_discount_draws != 0
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "occurrence work, terminal, or denominator is inconsistent"
            )
        _verify_occurrence_source_and_commitments_v1(self)
        object.__setattr__(
            self,
            "_occurrence_record_id",
            _content_id("occurrence", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_reconciliation_operational_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": self.logical_occurrence_id,
            "arm": self.arm,
            "context_id": self.context_id,
            "source_kind": self.source_kind.value,
            "source_artifact_id": self.source_artifact_id,
            "draw_range_ids": [item.range_id for item in self.draw_ranges],
            "work_id": self.work.work_id,
            "access_order_id": self.access_order.access_order_id,
            "access_order_ids": [
                self.access_order.access_order_id,
                *(
                    item.access_order_id
                    for item in self.additional_access_orders
                ),
            ],
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "denominator_included": True,
            "terminal_derived_from_source": True,
            "caller_supplied_terminal_outcome": False,
            "crn_cost_discount_draws": 0,
        }

    @property
    def occurrence_record_id(self) -> str:
        return self._occurrence_record_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "draw_ranges": [
                item.to_document() for item in self.draw_ranges
            ],
            "work": self.work.to_document(),
            "access_order": self.access_order.to_document(),
            "additional_access_orders": [
                item.to_document() for item in self.additional_access_orders
            ],
            "occurrence_record_id": self.occurrence_record_id,
        }


def _resident_range(
    *,
    logical_occurrence_id: str,
    source_kind: ReconciliationSourceKindV1,
    round_index: int,
    stage: DrawStageV1,
    transcript: row_core.RowObservationTranscriptV2,
    first_sequence_index: int,
    last_sequence_index: int,
) -> AcceptedDrawCommitmentRangeV1:
    if (
        type(transcript) is not row_core.RowObservationTranscriptV2
        or first_sequence_index <= 0
        or last_sequence_index > transcript.selected_checkpoint_draw_count
        or last_sequence_index < first_sequence_index
    ):
        raise V072CampaignReconciliationInvariantViolation(
            "resident commitment range is outside the immutable transcript"
        )
    observations = transcript.observations[
        first_sequence_index - 1 : last_sequence_index
    ]
    commitments = tuple(
        item.source_commitment_id for item in observations
    )
    first, last, digest, count = _ordered_commitment_digest(commitments)
    stream = transcript.stream_identity
    return AcceptedDrawCommitmentRangeV1(
        logical_occurrence_id,
        stream.arm,
        stream.context_id,
        round_index,
        source_kind,
        stage,
        CommitmentSchemeV1.RESIDENT_ARM_BOUND_SOURCE_COMMITMENT,
        stream.physical_row_id,
        stream.source_stream_id,
        transcript.transcript_id,
        first_sequence_index,
        last_sequence_index,
        count,
        first,
        last,
        digest,
        _crn_pairing_group_id(
            arm_free_stream_identity_id=stream.seed_identity_id,
            first_index=first_sequence_index,
            last_index=last_sequence_index,
        ),
        None,
        count,
        0,
    )


def _row_series_ranges(
    series: RowCoreObservationSeriesV1,
    *,
    logical_occurrence_id: str,
    source_kind: ReconciliationSourceKindV1,
    extension_stage: DrawStageV1,
) -> tuple[AcceptedDrawCommitmentRangeV1, ...]:
    ranges = [
        _resident_range(
            logical_occurrence_id=logical_occurrence_id,
            source_kind=source_kind,
            round_index=0,
            stage=DrawStageV1.COLD_DISCOVERY,
            transcript=series.discovery_transcript,
            first_sequence_index=1,
            last_sequence_index=64,
        )
    ]
    previous_count = 0
    for ordinal, transcript in enumerate(series.validation_history):
        ranges.append(
            _resident_range(
                logical_occurrence_id=logical_occurrence_id,
                source_kind=source_kind,
                round_index=0,
                stage=(
                    DrawStageV1.COLD_VALIDATION
                    if ordinal == 0
                    else extension_stage
                ),
                transcript=transcript,
                first_sequence_index=previous_count + 1,
                last_sequence_index=(
                    transcript.selected_checkpoint_draw_count
                ),
            )
        )
        previous_count = transcript.selected_checkpoint_draw_count
    return tuple(sorted(ranges, key=lambda item: item.range_id))


def reconcile_row_core_observation_series_v1(
    *,
    discovery_transcript: row_core.RowObservationTranscriptV2,
    validation_history: tuple[row_core.RowObservationTranscriptV2, ...],
) -> ReconciledOperationalOccurrenceV1:
    """Reconcile one observation-only row; no caller count/terminal fields."""

    series = RowCoreObservationSeriesV1(
        discovery_transcript, validation_history
    )
    ranges = _row_series_ranges(
        series,
        logical_occurrence_id=series.logical_occurrence_id,
        source_kind=ReconciliationSourceKindV1.ROW_CORE_RESIDENT,
        extension_stage=DrawStageV1.ROW_CORE_VALIDATION_EXTENSION,
    )
    first_validation = (
        series.validation_history[0].selected_checkpoint_draw_count
    )
    final_validation = (
        series.validation_history[-1].selected_checkpoint_draw_count
    )
    accepted = 64 + final_validation
    work = _zero_work(
        accepted_draws=accepted,
        random_word_calls=accepted,
        resident_commitment_count=accepted,
        cold_discovery_draws=64,
        cold_validation_draws=first_validation,
        row_core_validation_extension_draws=(
            final_validation - first_validation
        ),
    )
    return ReconciledOperationalOccurrenceV1(
        series.logical_occurrence_id,
        series.arm,
        series.context_id,
        ReconciliationSourceKindV1.ROW_CORE_RESIDENT,
        series.series_id,
        ranges,
        work,
        _not_applicable_access(series.series_id),
        ReconciliationTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE,
        ReconciliationTerminalCodeV1.OBSERVATION_ONLY_NONCERTIFICATE,
        _source_object=series,
    )


def _matched_terminal(
    run: matched.MatchedDirectGroundRunV1,
) -> tuple[ReconciliationTerminalClassV1, ReconciliationTerminalCodeV1]:
    if (
        run.terminal_class
        is matched.MatchedDirectTerminalClassV1.PLAN_CERTIFICATE
    ):
        return (
            ReconciliationTerminalClassV1.PLAN_CERTIFICATE,
            ReconciliationTerminalCodeV1
            .MATCHED_DIRECT_GROUND_CERTIFIED,
        )
    if (
        run.terminal_code
        is matched.MatchedDirectTerminalCodeV1
        .EXACT_LAZY_RESOURCE_EXHAUSTED
    ):
        return (
            ReconciliationTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE,
            ReconciliationTerminalCodeV1
            .MATCHED_DIRECT_SOLVER_RESOURCE_EXHAUSTED,
        )
    return (
        ReconciliationTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE,
        ReconciliationTerminalCodeV1
        .MATCHED_DIRECT_MAXIMUM_CHECKPOINT_EXHAUSTED,
    )


def reconcile_matched_direct_run_v1(
    run: matched.MatchedDirectGroundRunV1,
) -> ReconciledOperationalOccurrenceV1:
    """Derive all cold/extension/failed-direct work from one exact run."""

    if type(run) is not matched.MatchedDirectGroundRunV1:
        raise V072CampaignReconciliationInvariantViolation(
            "matched-direct adapter requires one exact run"
        )
    final_acquisitions = (
        run.checkpoint_records[-1].evidence.acquisitions
    )
    ranges: list[AcceptedDrawCommitmentRangeV1] = []
    for acquisition in final_acquisitions:
        series = RowCoreObservationSeriesV1(
            acquisition.discovery_transcript,
            acquisition.validation_history,
        )
        ranges.extend(
            _row_series_ranges(
                series,
                logical_occurrence_id=run.logical_occurrence_id,
                source_kind=ReconciliationSourceKindV1.MATCHED_DIRECT_RUN,
                extension_stage=(
                    DrawStageV1.DIRECT_VALIDATION_EXTENSION
                ),
            )
        )
    range_tuple = tuple(sorted(ranges, key=lambda item: item.range_id))
    row_count = len(final_acquisitions)
    first_checkpoint = matched.CHECKPOINTS[0]
    direct_attempts = len(run.checkpoint_records)
    failed_attempts = sum(
        item.status
        is matched.MatchedDirectCheckpointStatusV1.NOT_CERTIFIED
        for item in run.checkpoint_records
    )
    work = _zero_work(
        accepted_draws=run.total_accepted_draws,
        random_word_calls=run.total_random_word_calls,
        resident_commitment_count=run.total_accepted_draws,
        cold_discovery_draws=row_count * 64,
        cold_validation_draws=row_count * first_checkpoint,
        direct_extension_draws=(
            row_count * (run.stopped_checkpoint - first_checkpoint)
        ),
        direct_checkpoint_attempts=direct_attempts,
        failed_direct_checkpoint_attempts=failed_attempts,
        failed_certificate_attempts=failed_attempts,
        direct_model_builds=direct_attempts,
        direct_model_independent_verifications=direct_attempts,
        direct_solver_calls=direct_attempts,
        direct_proof_verifications=direct_attempts,
    )
    terminal_class, terminal_code = _matched_terminal(run)
    return ReconciledOperationalOccurrenceV1(
        run.logical_occurrence_id,
        matched.ARM,
        run.checkpoint_records[-1].evidence.closure_bundle.context_id,
        ReconciliationSourceKindV1.MATCHED_DIRECT_RUN,
        run.run_id,
        range_tuple,
        work,
        _not_applicable_access(run.run_id),
        terminal_class,
        terminal_code,
        _source_object=run,
    )


def _incremental_streams(
    run: materializer.DevelopmentAcquisitionControlRunV1,
) -> tuple[materializer.DevelopmentRawObservationStreamV1, ...]:
    return _incremental_streams_for_handoff(run.handoff)


def _incremental_streams_for_handoff(
    handoff: materializer.IncrementalModelRebuildHandoffV1,
) -> tuple[materializer.DevelopmentRawObservationStreamV1, ...]:
    return (
        handoff.parent_validation_stream,
        *(
            stream
            for row in handoff.child_rows
            for stream in (
                row.discovery_stream,
                row.validation_stream,
            )
        ),
    )


def _incremental_stage(
    stream: materializer.DevelopmentRawObservationStreamV1,
) -> DrawStageV1:
    return {
        materializer.AcquisitionLaneV1.PARENT_FRESH_VALIDATION: (
            DrawStageV1.INCREMENTAL_PARENT_VALIDATION
        ),
        materializer.AcquisitionLaneV1.CHILD_FRESH_DISCOVERY: (
            DrawStageV1.INCREMENTAL_CHILD_DISCOVERY
        ),
        materializer.AcquisitionLaneV1.CHILD_FRESH_VALIDATION: (
            DrawStageV1.INCREMENTAL_CHILD_VALIDATION
        ),
    }[stream.lane]


def _compressed_range(
    *,
    run: materializer.DevelopmentAcquisitionControlRunV1,
    stream: materializer.DevelopmentRawObservationStreamV1,
    proof: materializer.RawCommitmentRangeProofV1,
) -> AcceptedDrawCommitmentRangeV1:
    return _compressed_range_for_handoff(
        handoff=run.handoff,
        source_kind=ReconciliationSourceKindV1.INCREMENTAL_COMPRESSED,
        stream=stream,
        proof=proof,
    )


def _compressed_range_for_handoff(
    *,
    handoff: materializer.IncrementalModelRebuildHandoffV1,
    source_kind: ReconciliationSourceKindV1,
    stream: materializer.DevelopmentRawObservationStreamV1,
    proof: materializer.RawCommitmentRangeProofV1,
) -> AcceptedDrawCommitmentRangeV1:
    if (
        proof.stream_id != stream.stream_id
        or proof.draw_count != stream.draw_count
        or stream.arm != handoff.request.parent_epoch.arm
    ):
        raise V072CampaignReconciliationInvariantViolation(
            "incremental range proof was transplanted across streams"
        )
    return AcceptedDrawCommitmentRangeV1(
        handoff.request.parent_epoch.logical_occurrence_id,
        handoff.request.parent_epoch.arm,
        stream.context_id,
        stream.round_index,
        source_kind,
        _incremental_stage(stream),
        CommitmentSchemeV1.COMPRESSED_STREAM_INDEX_WORD,
        stream.physical_row_id,
        stream.stream_id,
        proof.range_proof_id,
        0,
        stream.draw_count - 1,
        stream.draw_count,
        proof.first_commitment_id,
        proof.last_commitment_id,
        proof.ordered_commitment_digest,
        _crn_pairing_group_id(
            arm_free_stream_identity_id=(
                stream.crn_pairing_group_seed_id
            ),
            first_index=0,
            last_index=stream.draw_count - 1,
        ),
        proof.range_proof_id,
        0,
        stream.draw_count,
    )


def _upstream_compressed_range(
    *,
    run: materializer.DevelopmentAcquisitionControlRunV1,
    transcript: materializer.DevelopmentUpstreamRowTranscriptV1,
    lane: materializer.UpstreamAcquisitionLaneV1,
    proof: materializer.RawCommitmentRangeProofV1,
) -> AcceptedDrawCommitmentRangeV1:
    return _upstream_compressed_range_for_handoff(
        handoff=run.handoff,
        source_kind=ReconciliationSourceKindV1.INCREMENTAL_COMPRESSED,
        transcript=transcript,
        lane=lane,
        proof=proof,
    )


def _upstream_compressed_range_for_handoff(
    *,
    handoff: materializer.IncrementalModelRebuildHandoffV1,
    source_kind: ReconciliationSourceKindV1,
    transcript: materializer.DevelopmentUpstreamRowTranscriptV1,
    lane: materializer.UpstreamAcquisitionLaneV1,
    proof: materializer.RawCommitmentRangeProofV1,
) -> AcceptedDrawCommitmentRangeV1:
    stream_id = materializer.upstream_stream_id_v1(transcript, lane)
    if proof.stream_id != stream_id:
        raise V072CampaignReconciliationInvariantViolation(
            "prior-cold commitment proof was transplanted across streams"
        )
    if transcript.arm != handoff.request.parent_epoch.arm:
        raise V072CampaignReconciliationInvariantViolation(
            "prior-cold stream was transplanted across arms"
        )
    seed_id = (
        transcript.discovery_seed_id
        if lane is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_seed_id
    )
    return AcceptedDrawCommitmentRangeV1(
        handoff.request.parent_epoch.logical_occurrence_id,
        handoff.request.parent_epoch.arm,
        handoff.request.parent_epoch.context_id,
        0,
        source_kind,
        (
            DrawStageV1.COLD_DISCOVERY
            if lane is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
            else DrawStageV1.COLD_VALIDATION
        ),
        CommitmentSchemeV1.COMPRESSED_STREAM_INDEX_WORD,
        transcript.physical_row.physical_row_id,
        stream_id,
        proof.range_proof_id,
        0,
        proof.draw_count - 1,
        proof.draw_count,
        proof.first_commitment_id,
        proof.last_commitment_id,
        proof.ordered_commitment_digest,
        _crn_pairing_group_id(
            arm_free_stream_identity_id=seed_id,
            first_index=0,
            last_index=proof.draw_count - 1,
        ),
        proof.range_proof_id,
        0,
        proof.draw_count,
    )


def reconcile_incremental_materializer_run_v1(
    run: materializer.DevelopmentAcquisitionControlRunV1,
) -> ReconciledOperationalOccurrenceV1:
    """Reconcile compressed incremental streams without resident draw objects."""

    if (
        type(run)
        is not materializer.DevelopmentAcquisitionControlRunV1
        or run.handoff.status != materializer.PENDING_STATUS
    ):
        raise V072CampaignReconciliationInvariantViolation(
            "incremental adapter requires one exact pending handoff run"
        )
    handoff = run.handoff
    streams = _incremental_streams(run)
    proof_by_stream = {
        item.stream_id: item for item in handoff.raw_commitment_ranges
    }
    if set(proof_by_stream) != {item.stream_id for item in streams}:
        raise V072CampaignReconciliationInvariantViolation(
            "incremental commitment range inventory is incomplete"
        )
    suffix_ranges = tuple(
        _compressed_range(
            run=run,
            stream=stream,
            proof=proof_by_stream[stream.stream_id],
        )
        for stream in streams
    )
    upstream_ranges = tuple(
        _upstream_compressed_range(
            run=run,
            transcript=transcript,
            lane=lane,
            proof=(
                transcript.discovery_raw_commitment_range
                if lane is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
                else transcript.validation_raw_commitment_range
            ),
        )
        for transcript in handoff.request.parent_evidence.upstream_root_rows
        for lane in (
            materializer.UpstreamAcquisitionLaneV1.DISCOVERY,
            materializer.UpstreamAcquisitionLaneV1.VALIDATION,
        )
    )
    ranges = tuple(
        sorted(
            (
                *upstream_ranges,
                *suffix_ranges,
            ),
            key=lambda item: item.range_id,
        )
    )
    counters = handoff.counters
    access = handoff.request.preauthorization_access
    authorization = handoff.request.authorization
    access_order = _access_order_from_handoff_v1(run.run_id, handoff)
    cold_discovery = sum(
        item.draw_count
        for item in upstream_ranges
        if item.stage is DrawStageV1.COLD_DISCOVERY
    )
    cold_validation = sum(
        item.draw_count
        for item in upstream_ranges
        if item.stage is DrawStageV1.COLD_VALIDATION
    )
    prior_cold_draws = cold_discovery + cold_validation
    work = _zero_work(
        accepted_draws=prior_cold_draws + counters.accepted_draws,
        random_word_calls=prior_cold_draws + counters.random_word_calls,
        compressed_commitment_count=(
            prior_cold_draws + counters.accepted_draws
        ),
        cold_discovery_draws=cold_discovery,
        cold_validation_draws=cold_validation,
        incremental_parent_validation_draws=(
            counters.parent_validation_draws
        ),
        incremental_child_discovery_draws=(
            counters.child_discovery_draws
        ),
        incremental_child_validation_draws=(
            counters.child_validation_draws
        ),
        failed_parent_certificate_attempts=1,
        failed_certificate_attempts=1,
        incremental_materializer_calls=counters.materializer_calls,
        incremental_observer_calls=counters.observer_calls,
        preauthorization_public_metadata_reads=(
            access.public_catalogue_metadata_reads
        ),
        preauthorization_counterfactual_evaluations=(
            access.exact_counterfactual_evaluations
        ),
        preauthorization_source_consensus_lookups=(
            access.source_consensus_lookups
        ),
        native_zero_counter_count=len(access.native_zero_counters),
    )
    return ReconciledOperationalOccurrenceV1(
        handoff.request.parent_epoch.logical_occurrence_id,
        handoff.request.parent_epoch.arm,
        handoff.request.parent_epoch.context_id,
        ReconciliationSourceKindV1.INCREMENTAL_COMPRESSED,
        run.run_id,
        ranges,
        work,
        access_order,
        ReconciliationTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE,
        (
            ReconciliationTerminalCodeV1
            .INCREMENTAL_PENDING_MODEL_REBUILD_NONCERTIFICATE
        ),
        _source_object=run,
    )


def _access_order_from_handoff_v1(
    source_artifact_id: str,
    handoff: materializer.IncrementalModelRebuildHandoffV1,
) -> ReconciledAccessOrderV1:
    access = handoff.request.preauthorization_access
    authorization = handoff.request.authorization
    return ReconciledAccessOrderV1(
        AccessOrderKindV1.PREAUTHORIZED_INCREMENTAL,
        source_artifact_id,
        access.access_log_id,
        authorization.authorization_id,
        handoff.request.authorization_freeze_id,
        handoff.request.parent_epoch.round_index,
        authorization.authorization_sequence,
        authorization.target_access_sequence_minimum,
        tuple(item.counter_id for item in access.native_zero_counters),
        tuple(item.path for item in access.native_zero_counters),
        tuple(item.value for item in access.native_zero_counters),
        authorization.frozen_before_target_access,
    )


def _complete_adaptive_components_v1(
    run: complete.DevelopmentCompleteAdaptivePlanningRunV1,
) -> tuple[
    tuple[AcceptedDrawCommitmentRangeV1, ...],
    ReconciledOperationalWorkV1,
    tuple[ReconciledAccessOrderV1, ...],
    ReconciliationTerminalClassV1,
    ReconciliationTerminalCodeV1,
]:
    if type(run) is not complete.DevelopmentCompleteAdaptivePlanningRunV1:
        raise V072CampaignReconciliationInvariantViolation(
            "complete adapter requires one exact adaptive planning run"
        )
    first = run.handoffs[0]
    source_kind = (
        ReconciliationSourceKindV1.COMPLETE_ADAPTIVE_PLANNING_COMPRESSED
    )
    upstream_ranges = tuple(
        _upstream_compressed_range_for_handoff(
            handoff=first,
            source_kind=source_kind,
            transcript=transcript,
            lane=lane,
            proof=(
                transcript.discovery_raw_commitment_range
                if lane
                is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
                else transcript.validation_raw_commitment_range
            ),
        )
        for transcript in first.request.parent_evidence.upstream_root_rows
        for lane in (
            materializer.UpstreamAcquisitionLaneV1.DISCOVERY,
            materializer.UpstreamAcquisitionLaneV1.VALIDATION,
        )
    )
    suffix_ranges: list[AcceptedDrawCommitmentRangeV1] = []
    for handoff in run.handoffs:
        streams = _incremental_streams_for_handoff(handoff)
        proof_by_stream = {
            item.stream_id: item
            for item in handoff.raw_commitment_ranges
        }
        if set(proof_by_stream) != {item.stream_id for item in streams}:
            raise V072CampaignReconciliationInvariantViolation(
                "complete adaptive suffix range inventory is incomplete"
            )
        suffix_ranges.extend(
            _compressed_range_for_handoff(
                handoff=handoff,
                source_kind=source_kind,
                stream=stream,
                proof=proof_by_stream[stream.stream_id],
            )
            for stream in streams
        )
    ranges = tuple(
        sorted(
            (*upstream_ranges, *suffix_ranges),
            key=lambda item: item.range_id,
        )
    )

    counters = tuple(handoff.counters for handoff in run.handoffs)
    accesses = tuple(
        handoff.request.preauthorization_access
        for handoff in run.handoffs
    )
    cold_discovery = sum(
        item.draw_count
        for item in upstream_ranges
        if item.stage is DrawStageV1.COLD_DISCOVERY
    )
    cold_validation = sum(
        item.draw_count
        for item in upstream_ranges
        if item.stage is DrawStageV1.COLD_VALIDATION
    )
    failed_postbuilds = sum(
        not result.certified for result in run.postbuild_results
    )
    postbuild_count = len(run.postbuild_results)
    work = _zero_work(
        accepted_draws=run.total_accepted_draws,
        random_word_calls=run.total_accepted_draws,
        compressed_commitment_count=run.total_accepted_draws,
        cold_discovery_draws=cold_discovery,
        cold_validation_draws=cold_validation,
        incremental_parent_validation_draws=sum(
            item.parent_validation_draws for item in counters
        ),
        incremental_child_discovery_draws=sum(
            item.child_discovery_draws for item in counters
        ),
        incremental_child_validation_draws=sum(
            item.child_validation_draws for item in counters
        ),
        failed_parent_certificate_attempts=1,
        failed_incremental_postbuild_audits=failed_postbuilds,
        failed_certificate_attempts=1 + failed_postbuilds,
        incremental_materializer_calls=sum(
            item.materializer_calls for item in counters
        ),
        incremental_observer_calls=sum(
            item.observer_calls for item in counters
        ),
        incremental_postbuild_model_builds=postbuild_count,
        incremental_postbuild_model_independent_verifications=(
            postbuild_count
        ),
        incremental_postbuild_solver_calls=postbuild_count,
        incremental_postbuild_proof_verifications=postbuild_count,
        incremental_postbuild_audits=postbuild_count,
        preauthorization_public_metadata_reads=sum(
            item.public_catalogue_metadata_reads for item in accesses
        ),
        preauthorization_counterfactual_evaluations=sum(
            item.exact_counterfactual_evaluations for item in accesses
        ),
        preauthorization_source_consensus_lookups=sum(
            item.source_consensus_lookups for item in accesses
        ),
        native_zero_counter_count=sum(
            len(item.native_zero_counters) for item in accesses
        ),
    )
    access_orders = tuple(
        _access_order_from_handoff_v1(run.run_id, handoff)
        for handoff in run.handoffs
    )
    terminal_code = {
        (
            complete.DevelopmentCompleteAdaptiveTerminalCodeV1
            .PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD
        ): (
            ReconciliationTerminalCodeV1
            .PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD
        ),
        (
            complete.DevelopmentCompleteAdaptiveTerminalCodeV1
            .PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD
        ): (
            ReconciliationTerminalCodeV1
            .PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD
        ),
    }.get(run.terminal_code)
    if (
        run.terminal_class
        is not (
            complete.DevelopmentCompleteAdaptiveTerminalClassV1
            .PLAN_CERTIFICATE
        )
        or terminal_code is None
        or sum(item.draw_count for item in ranges)
        != run.total_accepted_draws
        or cold_discovery + cold_validation != run.prior_cold_draws
        or sum(item.accepted_draws for item in counters)
        != run.incremental_suffix_draws
    ):
        raise V072CampaignReconciliationInvariantViolation(
            "complete adaptive terminal or native work does not reconcile"
        )
    return (
        ranges,
        work,
        access_orders,
        ReconciliationTerminalClassV1.PLAN_CERTIFICATE,
        terminal_code,
    )


def reconcile_complete_adaptive_run_v1(
    run: complete.DevelopmentCompleteAdaptivePlanningRunV1,
) -> ReconciledOperationalOccurrenceV1:
    """Reconcile a complete first/second rebuild adaptive occurrence."""

    ranges, work, accesses, terminal_class, terminal_code = (
        _complete_adaptive_components_v1(run)
    )
    return ReconciledOperationalOccurrenceV1(
        run.logical_occurrence_id,
        run.arm.value,
        run.context_id,
        ReconciliationSourceKindV1.COMPLETE_ADAPTIVE_PLANNING_COMPRESSED,
        run.run_id,
        ranges,
        work,
        accesses[0],
        terminal_class,
        terminal_code,
        additional_access_orders=accesses[1:],
        _source_object=run,
    )


def _resident_transcripts_for_occurrence(
    occurrence: ReconciledOperationalOccurrenceV1,
) -> dict[str, row_core.RowObservationTranscriptV2]:
    source = occurrence._source_object
    if occurrence.source_kind is ReconciliationSourceKindV1.ROW_CORE_RESIDENT:
        if type(source) is not RowCoreObservationSeriesV1:
            raise V072CampaignReconciliationInvariantViolation(
                "row-core occurrence lost its exact source series"
            )
        values = (
            source.discovery_transcript,
            *source.validation_history,
        )
    elif occurrence.source_kind is ReconciliationSourceKindV1.MATCHED_DIRECT_RUN:
        if type(source) is not matched.MatchedDirectGroundRunV1:
            raise V072CampaignReconciliationInvariantViolation(
                "matched occurrence lost its exact source run"
            )
        values = tuple(
            transcript
            for acquisition in (
                source.checkpoint_records[-1].evidence.acquisitions
            )
            for transcript in (
                acquisition.discovery_transcript,
                *acquisition.validation_history,
            )
        )
    else:
        return {}
    result = {item.transcript_id: item for item in values}
    if len(result) != len(values):
        # Shared validation prefixes occur as distinct transcript IDs; only an
        # exact duplicate artifact would disappear here.
        raise V072CampaignReconciliationInvariantViolation(
            "resident transcript inventory contains an exact duplicate"
        )
    return result


def _incremental_stream_map(
    occurrence: ReconciledOperationalOccurrenceV1,
) -> tuple[
    dict[str, materializer.DevelopmentRawObservationStreamV1],
    dict[
        str,
        tuple[
            materializer.DevelopmentUpstreamRowTranscriptV1,
            materializer.UpstreamAcquisitionLaneV1,
        ],
    ],
    dict[str, materializer.RawCommitmentRangeProofV1],
]:
    source = occurrence._source_object
    if type(source) is materializer.DevelopmentAcquisitionControlRunV1:
        handoffs = (source.handoff,)
    elif type(source) is complete.DevelopmentCompleteAdaptivePlanningRunV1:
        handoffs = source.handoffs
    else:
        raise V072CampaignReconciliationInvariantViolation(
            "compressed occurrence lost its exact materializer run"
        )
    streams = tuple(
        stream
        for handoff in handoffs
        for stream in _incremental_streams_for_handoff(handoff)
    )
    first = handoffs[0]
    upstream = {
        materializer.upstream_stream_id_v1(transcript, lane): (
            transcript,
            lane,
        )
        for transcript in (
            first.request.parent_evidence.upstream_root_rows
        )
        for lane in (
            materializer.UpstreamAcquisitionLaneV1.DISCOVERY,
            materializer.UpstreamAcquisitionLaneV1.VALIDATION,
        )
    }
    proofs = (
        *(
            proof
            for handoff in handoffs
            for proof in handoff.raw_commitment_ranges
        ),
        *first.prior_cold_raw_commitment_ranges,
    )
    return (
        {item.stream_id: item for item in streams},
        upstream,
        {
            item.range_proof_id: item
            for item in proofs
        },
    )


def _commitments_for_range_v1(
    occurrence: ReconciledOperationalOccurrenceV1,
    draw_range: AcceptedDrawCommitmentRangeV1,
) -> Iterator[str]:
    if (
        draw_range.logical_occurrence_id != occurrence.logical_occurrence_id
        or draw_range.arm != occurrence.arm
        or draw_range.context_id != occurrence.context_id
    ):
        raise V072CampaignReconciliationInvariantViolation(
            "draw range is transplanted across occurrences"
        )
    if (
        draw_range.commitment_scheme
        is CommitmentSchemeV1.RESIDENT_ARM_BOUND_SOURCE_COMMITMENT
    ):
        transcripts = _resident_transcripts_for_occurrence(occurrence)
        transcript = transcripts.get(draw_range.source_artifact_id)
        if (
            transcript is None
            or transcript.stream_identity.source_stream_id
            != draw_range.stream_id
            or transcript.stream_identity.arm != occurrence.arm
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "resident range source transcript/arm is invalid"
            )
        observations = transcript.observations[
            draw_range.first_accepted_draw_index
            - 1 : draw_range.last_accepted_draw_index
        ]
        if len(observations) != draw_range.draw_count:
            raise V072CampaignReconciliationInvariantViolation(
                "resident range does not cover its claimed accepted draws"
            )
        yield from (
            item.source_commitment_id for item in observations
        )
        return
    streams, upstream_streams, proofs = _incremental_stream_map(occurrence)
    stream = streams.get(draw_range.stream_id)
    upstream_stream = upstream_streams.get(draw_range.stream_id)
    proof = (
        None
        if draw_range.source_range_proof_id is None
        else proofs.get(draw_range.source_range_proof_id)
    )
    if proof is None:
        raise V072CampaignReconciliationInvariantViolation(
            "compressed range/stream/proof binding is invalid"
        )
    if stream is not None:
        if (
            upstream_stream is not None
            or proof.stream_id != stream.stream_id
            or proof.draw_count != stream.draw_count
            or stream.arm != occurrence.arm
            or draw_range.first_accepted_draw_index != 0
            or draw_range.last_accepted_draw_index
            != stream.draw_count - 1
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "incremental suffix range binding is invalid"
            )
        for index in range(stream.draw_count):
            yield materializer.raw_commitment_id_v1(stream, index)
        return
    if upstream_stream is None:
        raise V072CampaignReconciliationInvariantViolation(
            "compressed stream is absent from source evidence"
        )
    transcript, lane = upstream_stream
    draw_count = (
        transcript.discovery_draws
        if lane is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_draws
    )
    if (
        proof.stream_id != draw_range.stream_id
        or proof.draw_count != draw_count
        or transcript.arm != occurrence.arm
        or draw_range.first_accepted_draw_index != 0
        or draw_range.last_accepted_draw_index != draw_count - 1
    ):
        raise V072CampaignReconciliationInvariantViolation(
            "prior-cold range binding is invalid"
        )
    for index in range(draw_count):
        yield materializer.upstream_raw_commitment_id_v1(
            transcript,
            lane,
            index,
        )


def _verify_occurrence_source_and_commitments_v1(
    occurrence: ReconciledOperationalOccurrenceV1,
) -> None:
    source = occurrence._source_object
    expected_additional_accesses: tuple[ReconciledAccessOrderV1, ...] = ()
    if occurrence.source_kind is ReconciliationSourceKindV1.ROW_CORE_RESIDENT:
        if (
            type(source) is not RowCoreObservationSeriesV1
            or occurrence.source_artifact_id != source.series_id
            or occurrence.logical_occurrence_id
            != source.logical_occurrence_id
            or occurrence.arm != source.arm
            or occurrence.context_id != source.context_id
            or occurrence.terminal_class
            is not ReconciliationTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
            or occurrence.terminal_code
            is not ReconciliationTerminalCodeV1
            .OBSERVATION_ONLY_NONCERTIFICATE
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "row-core source or derived terminal is invalid"
            )
        expected_ranges = _row_series_ranges(
            source,
            logical_occurrence_id=source.logical_occurrence_id,
            source_kind=ReconciliationSourceKindV1.ROW_CORE_RESIDENT,
            extension_stage=DrawStageV1.ROW_CORE_VALIDATION_EXTENSION,
        )
        first_validation = (
            source.validation_history[0].selected_checkpoint_draw_count
        )
        final_validation = (
            source.validation_history[-1].selected_checkpoint_draw_count
        )
        accepted = 64 + final_validation
        expected_work = _zero_work(
            accepted_draws=accepted,
            random_word_calls=accepted,
            resident_commitment_count=accepted,
            cold_discovery_draws=64,
            cold_validation_draws=first_validation,
            row_core_validation_extension_draws=(
                final_validation - first_validation
            ),
        )
        expected_access = _not_applicable_access(source.series_id)
    elif occurrence.source_kind is ReconciliationSourceKindV1.MATCHED_DIRECT_RUN:
        if (
            type(source) is not matched.MatchedDirectGroundRunV1
            or occurrence.source_artifact_id != source.run_id
            or occurrence.logical_occurrence_id
            != source.logical_occurrence_id
            or (occurrence.terminal_class, occurrence.terminal_code)
            != _matched_terminal(source)
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "matched source or derived terminal is invalid"
            )
        acquisitions = (
            source.checkpoint_records[-1].evidence.acquisitions
        )
        expected_ranges = tuple(
            sorted(
                (
                    draw_range
                    for acquisition in acquisitions
                    for draw_range in _row_series_ranges(
                        RowCoreObservationSeriesV1(
                            acquisition.discovery_transcript,
                            acquisition.validation_history,
                        ),
                        logical_occurrence_id=source.logical_occurrence_id,
                        source_kind=(
                            ReconciliationSourceKindV1.MATCHED_DIRECT_RUN
                        ),
                        extension_stage=(
                            DrawStageV1.DIRECT_VALIDATION_EXTENSION
                        ),
                    )
                ),
                key=lambda item: item.range_id,
            )
        )
        attempts = len(source.checkpoint_records)
        failed = sum(
            item.status
            is matched.MatchedDirectCheckpointStatusV1.NOT_CERTIFIED
            for item in source.checkpoint_records
        )
        rows = len(acquisitions)
        expected_work = _zero_work(
            accepted_draws=source.total_accepted_draws,
            random_word_calls=source.total_random_word_calls,
            resident_commitment_count=source.total_accepted_draws,
            cold_discovery_draws=rows * 64,
            cold_validation_draws=rows * matched.CHECKPOINTS[0],
            direct_extension_draws=(
                rows
                * (
                    source.stopped_checkpoint
                    - matched.CHECKPOINTS[0]
                )
            ),
            direct_checkpoint_attempts=attempts,
            failed_direct_checkpoint_attempts=failed,
            failed_certificate_attempts=failed,
            direct_model_builds=attempts,
            direct_model_independent_verifications=attempts,
            direct_solver_calls=attempts,
            direct_proof_verifications=attempts,
        )
        expected_access = _not_applicable_access(source.run_id)
    elif (
        occurrence.source_kind
        is ReconciliationSourceKindV1.INCREMENTAL_COMPRESSED
    ):
        if (
            type(source)
            is not materializer.DevelopmentAcquisitionControlRunV1
            or occurrence.source_artifact_id != source.run_id
            or occurrence.logical_occurrence_id
            != source.handoff.request.parent_epoch.logical_occurrence_id
            or occurrence.terminal_class
            is not ReconciliationTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
            or occurrence.terminal_code
            is not (
                ReconciliationTerminalCodeV1
                .INCREMENTAL_PENDING_MODEL_REBUILD_NONCERTIFICATE
            )
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "incremental source or derived terminal is invalid"
            )
        handoff = source.handoff
        proof_by_stream = {
            item.stream_id: item for item in handoff.raw_commitment_ranges
        }
        expected_suffix_ranges = tuple(
            _compressed_range(
                run=source,
                stream=stream,
                proof=proof_by_stream[stream.stream_id],
            )
            for stream in _incremental_streams(source)
        )
        expected_upstream_ranges = tuple(
            _upstream_compressed_range(
                run=source,
                transcript=transcript,
                lane=lane,
                proof=(
                    transcript.discovery_raw_commitment_range
                    if (
                        lane
                        is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
                    )
                    else transcript.validation_raw_commitment_range
                ),
            )
            for transcript in (
                handoff.request.parent_evidence.upstream_root_rows
            )
            for lane in (
                materializer.UpstreamAcquisitionLaneV1.DISCOVERY,
                materializer.UpstreamAcquisitionLaneV1.VALIDATION,
            )
        )
        expected_ranges = tuple(
            sorted(
                (*expected_upstream_ranges, *expected_suffix_ranges),
                key=lambda item: item.range_id,
            )
        )
        cold_discovery = sum(
            item.draw_count
            for item in expected_upstream_ranges
            if item.stage is DrawStageV1.COLD_DISCOVERY
        )
        cold_validation = sum(
            item.draw_count
            for item in expected_upstream_ranges
            if item.stage is DrawStageV1.COLD_VALIDATION
        )
        counters = handoff.counters
        access = handoff.request.preauthorization_access
        authorization = handoff.request.authorization
        prior_cold = cold_discovery + cold_validation
        expected_work = _zero_work(
            accepted_draws=prior_cold + counters.accepted_draws,
            random_word_calls=prior_cold + counters.random_word_calls,
            compressed_commitment_count=(
                prior_cold + counters.accepted_draws
            ),
            cold_discovery_draws=cold_discovery,
            cold_validation_draws=cold_validation,
            incremental_parent_validation_draws=(
                counters.parent_validation_draws
            ),
            incremental_child_discovery_draws=(
                counters.child_discovery_draws
            ),
            incremental_child_validation_draws=(
                counters.child_validation_draws
            ),
            failed_parent_certificate_attempts=1,
            failed_certificate_attempts=1,
            incremental_materializer_calls=counters.materializer_calls,
            incremental_observer_calls=counters.observer_calls,
            preauthorization_public_metadata_reads=(
                access.public_catalogue_metadata_reads
            ),
            preauthorization_counterfactual_evaluations=(
                access.exact_counterfactual_evaluations
            ),
            preauthorization_source_consensus_lookups=(
                access.source_consensus_lookups
            ),
            native_zero_counter_count=len(access.native_zero_counters),
        )
        expected_access = ReconciledAccessOrderV1(
            AccessOrderKindV1.PREAUTHORIZED_INCREMENTAL,
            source.run_id,
            access.access_log_id,
            authorization.authorization_id,
            handoff.request.authorization_freeze_id,
            handoff.request.parent_epoch.round_index,
            authorization.authorization_sequence,
            authorization.target_access_sequence_minimum,
            tuple(
                item.counter_id for item in access.native_zero_counters
            ),
            tuple(item.path for item in access.native_zero_counters),
            tuple(item.value for item in access.native_zero_counters),
            authorization.frozen_before_target_access,
        )
    elif (
        occurrence.source_kind
        is (
            ReconciliationSourceKindV1
            .COMPLETE_ADAPTIVE_PLANNING_COMPRESSED
        )
    ):
        if (
            type(source)
            is not complete.DevelopmentCompleteAdaptivePlanningRunV1
            or occurrence.source_artifact_id != source.run_id
            or occurrence.logical_occurrence_id
            != source.logical_occurrence_id
            or occurrence.arm != source.arm.value
            or occurrence.context_id != source.context_id
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "complete adaptive source identity differs"
            )
        (
            expected_ranges,
            expected_work,
            expected_accesses,
            expected_terminal_class,
            expected_terminal_code,
        ) = _complete_adaptive_components_v1(source)
        expected_access = expected_accesses[0]
        expected_additional_accesses = expected_accesses[1:]
        if (
            occurrence.terminal_class is not expected_terminal_class
            or occurrence.terminal_code is not expected_terminal_code
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "complete adaptive terminal was not derived from source"
            )
    else:  # pragma: no cover
        raise V072CampaignReconciliationInvariantViolation(
            "unknown occurrence source kind"
        )
    if (
        occurrence.draw_ranges != expected_ranges
        or occurrence.work != expected_work
        or occurrence.access_order != expected_access
        or occurrence.additional_access_orders
        != expected_additional_accesses
    ):
        raise V072CampaignReconciliationInvariantViolation(
            "caller-derived range, work, or access claim differs from source"
        )
    seen: set[str] = set()
    for draw_range in occurrence.draw_ranges:
        commitments = tuple(
            _commitments_for_range_v1(occurrence, draw_range)
        )
        first, last, digest, count = _ordered_commitment_digest(
            commitments
        )
        if (
            first != draw_range.first_commitment_id
            or last != draw_range.last_commitment_id
            or digest != draw_range.ordered_commitment_digest
            or count != draw_range.draw_count
            or seen.intersection(commitments)
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "accepted draw commitment was forged, duplicated, or reused"
            )
        seen.update(commitments)


@dataclass(frozen=True, slots=True)
class DevelopmentSharedExperimentalContextBindingV1:
    """Mechanics-only grouping of nonmatched development backends."""

    mechanics_context_key: str
    arm_native_context_bindings: tuple[tuple[str, str], ...]
    scientific_matched_pair: bool = False
    matched_endpoint_authority: bool = False
    registered_target_evidence: bool = False
    _binding_id: str = field(init=False, repr=False)
    _mechanics_context_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.mechanics_context_key
            != "V072_DEVELOPMENT_P4_FIVE_ARM_MECHANICS_V1"
            or type(self.arm_native_context_bindings) is not tuple
            or tuple(
                arm for arm, _ in self.arm_native_context_bindings
            )
            != prereg.ARM_ORDER
            or any(
                type(item) is not tuple
                or len(item) != 2
                or _cid(item[1], "development native context") != item[1]
                for item in self.arm_native_context_bindings
            )
            or self.scientific_matched_pair is not False
            or self.matched_endpoint_authority is not False
            or self.registered_target_evidence is not False
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "development context binding is incomplete or overclaims matching"
            )
        base = {
            "schema": (
                "acfqp.v072_reconciliation_development_context_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "mechanics_context_key": self.mechanics_context_key,
            "arm_native_context_bindings": [
                {
                    "arm": arm,
                    "native_context_id": context_id,
                }
                for arm, context_id in self.arm_native_context_bindings
            ],
            "scientific_matched_pair": False,
            "matched_endpoint_authority": False,
            "registered_target_evidence": False,
        }
        object.__setattr__(
            self,
            "_mechanics_context_id",
            _content_id(
                "context_binding",
                {
                    **base,
                    "identity_role": "MECHANICS_CONTEXT",
                },
            ),
        )
        object.__setattr__(
            self,
            "_binding_id",
            _content_id(
                "context_binding",
                {
                    **base,
                    "mechanics_context_id": self.mechanics_context_id,
                    "identity_role": "NATIVE_CONTEXT_BINDING",
                },
            ),
        )

    @property
    def mechanics_context_id(self) -> str:
        return self._mechanics_context_id

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_reconciliation_development_context_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "mechanics_context_key": self.mechanics_context_key,
            "mechanics_context_id": self.mechanics_context_id,
            "arm_native_context_bindings": [
                {
                    "arm": arm,
                    "native_context_id": context_id,
                }
                for arm, context_id in self.arm_native_context_bindings
            ],
            "scientific_matched_pair": False,
            "matched_endpoint_authority": False,
            "registered_target_evidence": False,
            "binding_id": self.binding_id,
        }


@dataclass(frozen=True, slots=True, init=False)
class CampaignReconciliationLedgerV1:
    occurrences: tuple[ReconciledOperationalOccurrenceV1, ...]
    order_profile: CampaignOrderProfileV1
    development_context_binding: (
        DevelopmentSharedExperimentalContextBindingV1 | None
    )
    logical_occurrence_denominator: int
    plan_certificate_count: int
    noncertificate_count: int
    total_accepted_draws: int
    total_random_word_calls: int
    total_resident_commitments: int
    total_compressed_commitments: int
    total_terminal_artifacts: int
    crn_pairing_group_count: int
    crn_cost_discount_draws: int
    registered_target_evidence_count: int
    _ledger_id: str = field(init=False, repr=False)

    def __init__(
        self,
        occurrences: tuple[ReconciledOperationalOccurrenceV1, ...],
        order_profile: CampaignOrderProfileV1 = (
            CampaignOrderProfileV1.DEVELOPMENT_CONTENT_ID
        ),
        development_context_binding: (
            DevelopmentSharedExperimentalContextBindingV1 | None
        ) = None,
    ) -> None:
        if (
            type(occurrences) is not tuple
            or not occurrences
            or any(
                type(item) is not ReconciledOperationalOccurrenceV1
                for item in occurrences
            )
            or len(
                {
                    (item.logical_occurrence_id, item.arm)
                    for item in occurrences
                }
            )
            != len(occurrences)
            or type(order_profile) is not CampaignOrderProfileV1
            or (
                development_context_binding is not None
                and type(development_context_binding)
                is not DevelopmentSharedExperimentalContextBindingV1
            )
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "campaign occurrences are missing, duplicated, or noncanonical"
            )
        if (
            order_profile is CampaignOrderProfileV1.DEVELOPMENT_CONTENT_ID
            and tuple(item.occurrence_record_id for item in occurrences)
            != tuple(
                sorted(
                    {item.occurrence_record_id for item in occurrences}
                )
            )
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "development content-ID order profile is violated"
            )
        if (
            order_profile is CampaignOrderProfileV1.DEVELOPMENT_CONTENT_ID
            and development_context_binding is not None
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "development context binding requires the context-major profile"
            )
        if (
            order_profile
            is CampaignOrderProfileV1.CONTEXT_MAJOR_FROZEN_ARM_ORDER
        ):
            native_binding = (
                {}
                if development_context_binding is None
                else dict(
                    development_context_binding.arm_native_context_bindings
                )
            )
            if development_context_binding is not None and any(
                native_binding.get(item.arm) != item.context_id
                for item in occurrences
            ):
                raise V072CampaignReconciliationInvariantViolation(
                    "development mechanics binding differs from native contexts"
                )
            context_arm_pairs = tuple(
                (
                    (
                        item.context_id
                        if development_context_binding is None
                        else (
                            development_context_binding.mechanics_context_id
                        )
                    ),
                    item.arm,
                )
                for item in occurrences
            )
            context_ids = tuple(
                item.context_id
                for item in prereg.registered_heldout_public_contexts_v2()
            )
            registered_index = {
                context_id: index
                for index, context_id in enumerate(context_ids)
            }
            unknown_contexts = tuple(
                sorted(
                    {
                        context_id
                        for context_id, _ in context_arm_pairs
                        if context_id not in registered_index
                    }
                )
            )
            unknown_index = {
                context_id: len(registered_index) + index
                for index, context_id in enumerate(unknown_contexts)
            }
            context_index = {**registered_index, **unknown_index}
            arm_index = {
                arm: index for index, arm in enumerate(prereg.ARM_ORDER)
            }
            if (
                any(arm not in arm_index for _, arm in context_arm_pairs)
                or len(set(context_arm_pairs)) != len(context_arm_pairs)
                or context_arm_pairs
                != tuple(
                    sorted(
                        context_arm_pairs,
                        key=lambda item: (
                            context_index[item[0]],
                            arm_index[item[1]],
                        ),
                    )
                )
                or any(
                    {
                        arm
                        for context_id, arm in context_arm_pairs
                        if context_id == current_context
                    }
                    != set(prereg.ARM_ORDER)
                    for current_context in {
                        context_id for context_id, _ in context_arm_pairs
                    }
                )
            ):
                raise V072CampaignReconciliationInvariantViolation(
                    "context-major frozen five-arm campaign order is violated"
                )
            registered_pairs = tuple(
                pair
                for pair in context_arm_pairs
                if pair[0] in registered_index
            )
            if registered_pairs and (
                len(registered_pairs) != prereg.CONFIRMATORY_OCCURRENCE_COUNT
                or {
                    context_id for context_id, _ in registered_pairs
                }
                != set(context_ids)
            ):
                raise V072CampaignReconciliationInvariantViolation(
                    "registered campaign is not the exact 15-occurrence shape"
                )
        global_commitments: set[str] = set()
        crn_groups: dict[
            str, list[tuple[str, AcceptedDrawCommitmentRangeV1, set[str]]]
        ] = {}
        for occurrence in occurrences:
            _verify_occurrence_source_and_commitments_v1(occurrence)
            for draw_range in occurrence.draw_ranges:
                commitments = set(
                    _commitments_for_range_v1(
                        occurrence, draw_range
                    )
                )
                if global_commitments.intersection(commitments):
                    raise V072CampaignReconciliationInvariantViolation(
                        "accepted draw was reused across occurrence/arm/round"
                    )
                global_commitments.update(commitments)
                crn_groups.setdefault(
                    draw_range.crn_pairing_group_id, []
                ).append((occurrence.arm, draw_range, commitments))
        for members in crn_groups.values():
            arms = [item[0] for item in members]
            if len(arms) != len(set(arms)):
                raise V072CampaignReconciliationInvariantViolation(
                    "one arm appears twice in the same CRN pairing group"
                )
            counts = {item[1].draw_count for item in members}
            if len(counts) != 1:
                raise V072CampaignReconciliationInvariantViolation(
                    "CRN paired ranges have unequal accepted draw counts"
                )
            for index, (_, _, commitments) in enumerate(members):
                if any(
                    commitments.intersection(other[2])
                    for other in members[index + 1 :]
                ):
                    raise V072CampaignReconciliationInvariantViolation(
                        "CRN arms reused an arm-bound commitment identity"
                    )
        denominator = len(occurrences)
        plan_count = sum(
            item.terminal_class
            is ReconciliationTerminalClassV1.PLAN_CERTIFICATE
            for item in occurrences
        )
        noncertificate_count = denominator - plan_count
        accepted = sum(item.work.accepted_draws for item in occurrences)
        random_calls = sum(
            item.work.random_word_calls for item in occurrences
        )
        resident = sum(
            item.work.resident_commitment_count
            for item in occurrences
        )
        compressed = sum(
            item.work.compressed_commitment_count
            for item in occurrences
        )
        terminals = sum(
            item.work.terminal_artifact_count for item in occurrences
        )
        if (
            len(global_commitments) != accepted
            or random_calls != accepted
            or resident + compressed != accepted
            or terminals != denominator
        ):
            raise V072CampaignReconciliationInvariantViolation(
                "campaign work or denominator reconciliation is incomplete"
            )
        object.__setattr__(self, "occurrences", occurrences)
        object.__setattr__(self, "order_profile", order_profile)
        object.__setattr__(
            self,
            "development_context_binding",
            development_context_binding,
        )
        object.__setattr__(
            self, "logical_occurrence_denominator", denominator
        )
        object.__setattr__(self, "plan_certificate_count", plan_count)
        object.__setattr__(
            self, "noncertificate_count", noncertificate_count
        )
        object.__setattr__(self, "total_accepted_draws", accepted)
        object.__setattr__(self, "total_random_word_calls", random_calls)
        object.__setattr__(
            self, "total_resident_commitments", resident
        )
        object.__setattr__(
            self, "total_compressed_commitments", compressed
        )
        object.__setattr__(
            self, "total_terminal_artifacts", terminals
        )
        object.__setattr__(
            self, "crn_pairing_group_count", len(crn_groups)
        )
        object.__setattr__(self, "crn_cost_discount_draws", 0)
        object.__setattr__(
            self, "registered_target_evidence_count", 0
        )
        object.__setattr__(
            self,
            "_ledger_id",
            _content_id("campaign", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_campaign_reconciliation_ledger.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "order_profile": self.order_profile.value,
            "development_context_binding_id": (
                None
                if self.development_context_binding is None
                else self.development_context_binding.binding_id
            ),
            "occurrence_record_ids": [
                item.occurrence_record_id for item in self.occurrences
            ],
            "logical_occurrence_denominator": (
                self.logical_occurrence_denominator
            ),
            "plan_certificate_count": self.plan_certificate_count,
            "noncertificate_count": self.noncertificate_count,
            "total_accepted_draws": self.total_accepted_draws,
            "total_random_word_calls": self.total_random_word_calls,
            "total_resident_commitments": (
                self.total_resident_commitments
            ),
            "total_compressed_commitments": (
                self.total_compressed_commitments
            ),
            "total_terminal_artifacts": self.total_terminal_artifacts,
            "crn_pairing_group_count": self.crn_pairing_group_count,
            "crn_cost_discount_draws": 0,
            "registered_target_evidence_count": 0,
            "caller_supplied_counts": False,
            "caller_supplied_discounts": False,
            "caller_supplied_terminal_outcomes": False,
        }

    @property
    def ledger_id(self) -> str:
        return self._ledger_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrences": [
                item.to_document() for item in self.occurrences
            ],
            "development_context_binding": (
                None
                if self.development_context_binding is None
                else self.development_context_binding.to_document()
            ),
            "ledger_id": self.ledger_id,
        }


def reconcile_campaign_v1(
    *,
    occurrences: tuple[ReconciledOperationalOccurrenceV1, ...],
    order_profile: CampaignOrderProfileV1 = (
        CampaignOrderProfileV1.DEVELOPMENT_CONTENT_ID
    ),
    development_context_binding: (
        DevelopmentSharedExperimentalContextBindingV1 | None
    ) = None,
) -> CampaignReconciliationLedgerV1:
    """Build the ledger from typed occurrences; all totals are derived."""

    return CampaignReconciliationLedgerV1(
        occurrences,
        order_profile,
        development_context_binding,
    )


def reconcile_registered_v072_campaign_v1(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    raise RegisteredCampaignReconciliationLockedV1(
        "registered campaign reconciliation is locked: "
        f"status={REGISTERED_EXECUTION_STATUS}, "
        "confirmatory_execution_manifest_id=null, "
        "target_execution_allowed=false"
    )


__all__ = [
    "AcceptedDrawCommitmentRangeV1",
    "AccessOrderKindV1",
    "CampaignReconciliationLedgerV1",
    "CampaignOrderProfileV1",
    "CommitmentSchemeV1",
    "DOMAIN_TAGS",
    "DrawStageV1",
    "DevelopmentSharedExperimentalContextBindingV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_EXECUTION_STATUS",
    "ReconciledAccessOrderV1",
    "ReconciledOperationalOccurrenceV1",
    "ReconciledOperationalWorkV1",
    "ReconciliationSourceKindV1",
    "ReconciliationTerminalClassV1",
    "ReconciliationTerminalCodeV1",
    "RegisteredCampaignReconciliationLockedV1",
    "RowCoreObservationSeriesV1",
    "SCHEMA_VERSION",
    "V072CampaignReconciliationInvariantViolation",
    "reconcile_campaign_v1",
    "reconcile_complete_adaptive_run_v1",
    "reconcile_incremental_materializer_run_v1",
    "reconcile_matched_direct_run_v1",
    "reconcile_registered_v072_campaign_v1",
    "reconcile_row_core_observation_series_v1",
]
