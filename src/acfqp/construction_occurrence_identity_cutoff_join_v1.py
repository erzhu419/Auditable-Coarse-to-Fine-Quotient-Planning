"""Identity and operational-cutoff joins for K7 accounting completion.

This module is a fail-closed prerequisite, not an accounting finalizer.  It
joins the exact owned-partial K7 result to the evidence-closure and shared
resource schemas, and it defines an ordered operational cutoff.  The join can
prove structural identity equality only.  The current K7 path has no
independently replayable route-context or cutoff authority, and the shared
resource receipt module is schema-only; consequently every verification here
keeps ``CounterRecord``, ``WorkVector`` and ``ComparisonVector`` issuance
disabled.

In particular, a content ID is not semantic proof.  Receipt values and cutoff
events become usable only after a future independent verifier replays their
source bytes and execution supervisor.  Missing authorities are represented
by typed blockers rather than caller-selected IDs or inferred zeros.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import (
    CONSTRUCTION_IDENTITY_JOIN_READINESS_V1_DOMAIN,
    CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_V1_DOMAIN,
    CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_OPERATIONAL_CUTOFF_ATTESTATION_V1_DOMAIN,
    CONSTRUCTION_OPERATIONAL_CUTOFF_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_OPERATIONAL_SEQUENCE_MARKER_V1_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp import construction_accounting_evidence_closure_v1 as closure_v1
from acfqp import construction_accounting_partial_native_v1 as partial_v1
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp import v075_k7_root_cap_owned_partial_runner_v1 as owned_v1


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_occurrence_identity_cutoff_join_v1"

REQUESTED_PHASE3E_DOMAIN_TAGS = frozenset(
    {
        CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_V1_DOMAIN,
        CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_VERIFICATION_V1_DOMAIN,
        CONSTRUCTION_OPERATIONAL_SEQUENCE_MARKER_V1_DOMAIN,
        CONSTRUCTION_OPERATIONAL_CUTOFF_ATTESTATION_V1_DOMAIN,
        CONSTRUCTION_OPERATIONAL_CUTOFF_VERIFICATION_V1_DOMAIN,
        CONSTRUCTION_IDENTITY_JOIN_READINESS_V1_DOMAIN,
    }
)

_ROLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_JOIN_ISSUER = object()
_CUTOFF_ISSUER = object()
_VERIFICATION_ISSUER = object()
_READINESS_ISSUER = object()


class ConstructionOccurrenceIdentityCutoffJoinV1Error(ValueError):
    """A join, cutoff, or replay request is stale, crossed, or incomplete."""


class ConstructionExecutionStatusV1(str, Enum):
    OWNED_PARTIAL_COMPLETED = "OWNED_PARTIAL_COMPLETED"


class IndependentSemanticReplayStatusV1(str, Enum):
    NOT_RUN = "NOT_RUN"


class IdentityJoinReadinessStatusV1(str, Enum):
    NOT_READY_SCHEMA_ONLY = "NOT_READY_SCHEMA_ONLY"


class IdentityJoinBlockerCodeV1(str, Enum):
    CUTOFF_AUTHORITY_NOT_INDEPENDENTLY_REPLAYED = (
        "CUTOFF_AUTHORITY_NOT_INDEPENDENTLY_REPLAYED"
    )
    EVIDENCE_CLOSURE_INCOMPLETE = "EVIDENCE_CLOSURE_INCOMPLETE"
    OWNED_RESULT_PARTIAL_NATIVE_ONLY = "OWNED_RESULT_PARTIAL_NATIVE_ONLY"
    ROUTE_CONTEXT_AUTHORITY_NOT_AVAILABLE = (
        "ROUTE_CONTEXT_AUTHORITY_NOT_AVAILABLE"
    )
    SHARED_RECEIPTS_INCOMPLETE_TYPED = "SHARED_RECEIPTS_INCOMPLETE_TYPED"
    SHARED_RECEIPT_SEMANTICS_NOT_INDEPENDENTLY_REPLAYED = (
        "SHARED_RECEIPT_SEMANTICS_NOT_INDEPENDENTLY_REPLAYED"
    )


class OperationalSequenceKindV1(str, Enum):
    WINDOW_START = "WINDOW_START"
    BUSINESS_WORK = "BUSINESS_WORK"
    TRANSCRIPT_TERMINAL = "TRANSCRIPT_TERMINAL"
    OPERATIONAL_CUTOFF = "OPERATIONAL_CUTOFF"
    ACCOUNTING_TAIL = "ACCOUNTING_TAIL"
    PROVENANCE_TAIL = "PROVENANCE_TAIL"


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "identity/cutoff schema used an unregistered local domain"
        )
    return content_id(domain, dict(payload))


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            f"{field_name} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            f"{field_name} must be a nonnegative exact integer"
        )
    return value


def _role(value: Any, field_name: str) -> str:
    if type(value) is not str or _ROLE.fullmatch(value) is None:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            f"{field_name} must be a canonical role"
        )
    return value


def _enum(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            f"{field_name} is invalid"
        ) from error


def _terminal_id(
    transcript: partial_v1.PartialNativeOccurrenceTranscriptV1,
) -> str:
    return transcript.nodes[-1].chain_id


@dataclass(frozen=True, slots=True)
class MissingIndependentAuthorityV1:
    """Typed blocker; never interchangeable with a missing field or an ID."""

    authority_role: str
    reason_code: str
    kind: str = "NOT_AVAILABLE"

    def __post_init__(self) -> None:
        _role(self.authority_role, "authority role")
        _role(self.reason_code, "authority reason")
        if self.kind != "NOT_AVAILABLE":
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "missing authority must remain typed NOT_AVAILABLE"
            )

    def to_document(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "authority_role": self.authority_role,
            "reason": self.reason_code,
        }


def _missing_route_context_authority() -> MissingIndependentAuthorityV1:
    return MissingIndependentAuthorityV1(
        "route_context_semantic_authority",
        "NO_K7_ROUTE_CONTEXT_REPLAY_AUTHORITY",
    )


def _missing_cutoff_authority() -> MissingIndependentAuthorityV1:
    return MissingIndependentAuthorityV1(
        "operational_cutoff_semantic_authority",
        "NO_K7_OUTER_SUPERVISOR_CUTOFF_REPLAY_AUTHORITY",
    )


def _missing_receipt_set_authority() -> MissingIndependentAuthorityV1:
    return MissingIndependentAuthorityV1(
        "shared_resource_receipt_set_authority",
        "NO_K7_LIVE_CLOSED_SHARED_RESOURCE_RECEIPT_SET",
    )


@dataclass(frozen=True, slots=True)
class ConstructionOccurrenceIdentityJoinV1:
    """One exact structural join; it is not semantic accounting evidence."""

    _issuer: InitVar[object]
    owned_partial_result_id: str
    original_result_id: str
    evidence_closure_context_id: str
    evidence_closure_id: str
    shared_resource_identity_binding_id: str
    shared_resource_receipt_set_id: str
    shared_resource_measurement_window_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    execution_profile_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    partial_native_transcript_id: str
    transcript_terminal_id: str
    transcript_terminal_kind: str
    execution_terminal_status: str
    execution_status: ConstructionExecutionStatusV1
    route_context_authority: MissingIndependentAuthorityV1 = field(repr=False)
    cutoff_authority: MissingIndependentAuthorityV1 = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _JOIN_ISSUER:
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "occurrence identity join is caller-minted"
            )
        for name in (
            "owned_partial_result_id",
            "original_result_id",
            "evidence_closure_context_id",
            "evidence_closure_id",
            "shared_resource_identity_binding_id",
            "shared_resource_receipt_set_id",
            "shared_resource_measurement_window_id",
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
            "execution_profile_id",
            "occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "partial_native_transcript_id",
            "transcript_terminal_id",
        ):
            _cid(getattr(self, name), name)
        _role(self.transcript_terminal_kind, "transcript terminal kind")
        _role(self.execution_terminal_status, "execution terminal status")
        object.__setattr__(
            self,
            "execution_status",
            _enum(
                ConstructionExecutionStatusV1,
                self.execution_status,
                "execution status",
            ),
        )
        if (
            type(self.route_context_authority)
            is not MissingIndependentAuthorityV1
            or self.route_context_authority
            != _missing_route_context_authority()
            or type(self.cutoff_authority) is not MissingIndependentAuthorityV1
            or self.cutoff_authority != _missing_cutoff_authority()
            or self.execution_status
            is not ConstructionExecutionStatusV1.OWNED_PARTIAL_COMPLETED
        ):
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "V1 join must retain both missing independent authorities"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_occurrence_identity_join.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_partial_result_id": self.owned_partial_result_id,
            "original_result_id": self.original_result_id,
            "evidence_closure_context_id": self.evidence_closure_context_id,
            "evidence_closure_id": self.evidence_closure_id,
            "shared_resource_identity_binding_id": (
                self.shared_resource_identity_binding_id
            ),
            "shared_resource_receipt_set_id": (
                self.shared_resource_receipt_set_id
            ),
            "shared_resource_measurement_window_id": (
                self.shared_resource_measurement_window_id
            ),
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "execution_profile_id": self.execution_profile_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "partial_native_transcript_id": self.partial_native_transcript_id,
            "transcript_terminal_id": self.transcript_terminal_id,
            "transcript_terminal_kind": self.transcript_terminal_kind,
            "execution_terminal_status": self.execution_terminal_status,
            "execution_status": self.execution_status.value,
            "route_context_authority": self.route_context_authority.to_document(),
            "cutoff_authority": self.cutoff_authority.to_document(),
            "structural_identity_join_only": True,
            "route_context_semantics_independently_replayed": False,
            "shared_receipt_semantics_independently_replayed": False,
            "cutoff_semantics_independently_replayed": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def identity_join_id(self) -> str:
        return _content_id(
            CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_identity_join_id": self.identity_join_id}


def freeze_construction_occurrence_identity_join_v1(
    *,
    owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
    evidence_closure: closure_v1.EvidenceClosureV1,
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
) -> ConstructionOccurrenceIdentityJoinV1:
    """Join exact typed roots without asserting their source semantics."""

    if (
        type(owned_result) is not owned_v1.V075K7RootCapOwnedPartialResultV1
        or type(evidence_closure) is not closure_v1.EvidenceClosureV1
        or type(receipt_set) is not receipts_v1.SharedResourceReceiptSetV1
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "identity join requires exact typed owned/closure/receipt roots"
        )
    transcript = owned_result.transcript
    try:
        owned_result.__post_init__(owned_v1._WRAPPER_RESULT_ISSUER)  # noqa: SLF001
        partial_v1.verify_partial_native_occurrence_transcript_v1(transcript)
        closure_v1.verify_evidence_closure_coverage_v1(evidence_closure)
        receipts_v1.replay_shared_resource_receipt_set_structure_v1(
            receipt_set, require_all_structurally_recorded=False
        )
    except Exception as error:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "one identity-join root failed structural replay"
        ) from error

    terminal_id = _terminal_id(transcript)
    context = evidence_closure.context
    identity = receipt_set.identity
    if (
        context.counter_registry_id != owned_result.counter_registry_id
        or context.stage_profile_id != owned_result.stage_profile_id
        or context.boundary_profile_id != owned_result.boundary_profile_id
        or context.execution_profile_id != owned_result.execution_profile_id
        or context.transcript_id != transcript.transcript_id
        or context.terminal_id != terminal_id
        or identity.counter_registry_id != owned_result.counter_registry_id
        or identity.stage_profile_id != owned_result.stage_profile_id
        or identity.boundary_profile_id != owned_result.boundary_profile_id
        or identity.execution_profile_id != owned_result.execution_profile_id
        or identity.occurrence_id != transcript.start.occurrence_id
        or receipt_set.window.identity_binding_id
        != identity.identity_binding_id
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "owned result, closure, and receipt identities do not join exactly"
        )

    return ConstructionOccurrenceIdentityJoinV1(
        _JOIN_ISSUER,
        owned_result.wrapper_id,
        owned_result.result.result_id,
        context.context_id,
        evidence_closure.closure_id,
        identity.identity_binding_id,
        receipt_set.receipt_set_id,
        receipt_set.window.window_id,
        owned_result.counter_registry_id,
        owned_result.stage_profile_id,
        owned_result.boundary_profile_id,
        owned_result.execution_profile_id,
        transcript.start.occurrence_id,
        identity.route_attempt_id,
        identity.decision_point_id,
        transcript.transcript_id,
        terminal_id,
        transcript.terminal_kind.value,
        owned_result.result.status.value,
        ConstructionExecutionStatusV1.OWNED_PARTIAL_COMPLETED,
        _missing_route_context_authority(),
        _missing_cutoff_authority(),
    )


@dataclass(frozen=True, slots=True)
class OperationalSequenceMarkerV1:
    sequence: int
    kind: OperationalSequenceKindV1
    role: str
    subject_id: str

    def __post_init__(self) -> None:
        _nonnegative(self.sequence, "marker sequence")
        object.__setattr__(
            self,
            "kind",
            _enum(OperationalSequenceKindV1, self.kind, "marker kind"),
        )
        _role(self.role, "marker role")
        _cid(self.subject_id, "marker subject")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_operational_sequence_marker.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence": self.sequence,
            "kind": self.kind.value,
            "role": self.role,
            "subject_id": self.subject_id,
        }

    @property
    def marker_id(self) -> str:
        return _content_id(
            CONSTRUCTION_OPERATIONAL_SEQUENCE_MARKER_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operational_sequence_marker_id": self.marker_id}


def _validate_cutoff_markers(
    *,
    identity_join: ConstructionOccurrenceIdentityJoinV1,
    window: receipts_v1.SharedResourceMeasurementWindowV1,
    markers: tuple[OperationalSequenceMarkerV1, ...],
) -> None:
    if (
        not markers
        or any(type(row) is not OperationalSequenceMarkerV1 for row in markers)
        or tuple(row.sequence for row in markers)
        != tuple(sorted(row.sequence for row in markers))
        or len({row.sequence for row in markers}) != len(markers)
        or len({row.marker_id for row in markers}) != len(markers)
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "cutoff markers must be nonempty, strictly ordered, and unique"
        )
    by_kind = {
        kind: tuple(row for row in markers if row.kind is kind)
        for kind in OperationalSequenceKindV1
    }
    for singleton in (
        OperationalSequenceKindV1.WINDOW_START,
        OperationalSequenceKindV1.TRANSCRIPT_TERMINAL,
        OperationalSequenceKindV1.OPERATIONAL_CUTOFF,
    ):
        if len(by_kind[singleton]) != 1:
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                f"cutoff requires exactly one {singleton.value} marker"
            )
    if (
        not by_kind[OperationalSequenceKindV1.ACCOUNTING_TAIL]
        or not by_kind[OperationalSequenceKindV1.PROVENANCE_TAIL]
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "post-cutoff accounting and provenance tails must both be explicit"
        )
    start = by_kind[OperationalSequenceKindV1.WINDOW_START][0]
    terminal = by_kind[OperationalSequenceKindV1.TRANSCRIPT_TERMINAL][0]
    cutoff = by_kind[OperationalSequenceKindV1.OPERATIONAL_CUTOFF][0]
    if (
        start.sequence != window.start_sequence
        or start.subject_id != window.start_marker_id
        or cutoff.sequence != window.cutoff_sequence
        or cutoff.subject_id != window.cutoff_marker_id
        or terminal.subject_id != identity_join.transcript_terminal_id
        or not start.sequence < terminal.sequence <= cutoff.sequence
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "start, transcript terminal, or cutoff marker is identity-stale"
        )
    business = by_kind[OperationalSequenceKindV1.BUSINESS_WORK]
    if any(
        not start.sequence < row.sequence < cutoff.sequence for row in business
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "business work is forbidden after the operational cutoff"
        )
    cutoff_index = markers.index(cutoff)
    if any(
        row.kind
        not in {
            OperationalSequenceKindV1.ACCOUNTING_TAIL,
            OperationalSequenceKindV1.PROVENANCE_TAIL,
        }
        for row in markers[cutoff_index + 1 :]
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "only accounting/provenance tail events may follow cutoff"
        )
    if any(
        row.sequence <= cutoff.sequence
        for kind in (
            OperationalSequenceKindV1.ACCOUNTING_TAIL,
            OperationalSequenceKindV1.PROVENANCE_TAIL,
        )
        for row in by_kind[kind]
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "accounting/provenance tails must be strictly post-cutoff"
        )


@dataclass(frozen=True, slots=True)
class OperationalCutoffAttestationV1:
    """Ordered cutoff shape, still awaiting independent supervisor replay."""

    _issuer: InitVar[object]
    occurrence_identity_join_id: str
    shared_resource_identity_binding_id: str
    shared_resource_receipt_set_id: str
    measurement_window_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    transcript_id: str
    transcript_terminal_id: str
    execution_terminal_status: str
    markers: tuple[OperationalSequenceMarkerV1, ...] = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CUTOFF_ISSUER:
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "operational cutoff attestation is caller-minted"
            )
        for name in (
            "occurrence_identity_join_id",
            "shared_resource_identity_binding_id",
            "shared_resource_receipt_set_id",
            "measurement_window_id",
            "occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "transcript_id",
            "transcript_terminal_id",
        ):
            _cid(getattr(self, name), name)
        _role(self.execution_terminal_status, "execution terminal status")
        if type(self.markers) is not tuple:
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "cutoff markers must be one immutable tuple"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_operational_cutoff_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_identity_join_id": self.occurrence_identity_join_id,
            "shared_resource_identity_binding_id": (
                self.shared_resource_identity_binding_id
            ),
            "shared_resource_receipt_set_id": self.shared_resource_receipt_set_id,
            "measurement_window_id": self.measurement_window_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "transcript_id": self.transcript_id,
            "transcript_terminal_id": self.transcript_terminal_id,
            "execution_terminal_status": self.execution_terminal_status,
            "ordered_marker_ids": [row.marker_id for row in self.markers],
            "marker_policy_declares_business_work_forbidden_after_cutoff": True,
            "marker_structure_has_explicit_accounting_tail": True,
            "marker_structure_has_explicit_provenance_tail": True,
            "post_cutoff_business_work_absence_verified": {
                "kind": "UNKNOWN",
                "reason": "SOURCE_EVENT_BYTES_NOT_INDEPENDENTLY_REPLAYED",
            },
            "post_cutoff_tail_output_byte_exclusion_verified": {
                "kind": "UNKNOWN",
                "reason": "OUTPUT_BYTE_RECEIPT_NOT_SEMANTICALLY_REPLAYED",
            },
            "cutoff_semantics_independently_replayed": False,
            "formal_vector_authorized": False,
        }

    @property
    def cutoff_attestation_id(self) -> str:
        return _content_id(
            CONSTRUCTION_OPERATIONAL_CUTOFF_ATTESTATION_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "operational_cutoff_attestation_id": self.cutoff_attestation_id,
        }


def freeze_operational_cutoff_attestation_v1(
    *,
    identity_join: ConstructionOccurrenceIdentityJoinV1,
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
    markers: Iterable[OperationalSequenceMarkerV1],
) -> OperationalCutoffAttestationV1:
    if (
        type(identity_join) is not ConstructionOccurrenceIdentityJoinV1
        or type(receipt_set) is not receipts_v1.SharedResourceReceiptSetV1
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "cutoff requires exact join and receipt-set roots"
        )
    rows = tuple(markers)
    if (
        identity_join.shared_resource_identity_binding_id
        != receipt_set.identity.identity_binding_id
        or identity_join.shared_resource_receipt_set_id != receipt_set.receipt_set_id
        or identity_join.shared_resource_measurement_window_id
        != receipt_set.window.window_id
        or identity_join.occurrence_id != receipt_set.identity.occurrence_id
        or identity_join.route_attempt_id != receipt_set.identity.route_attempt_id
        or identity_join.decision_point_id != receipt_set.identity.decision_point_id
        or receipt_set.window.state
        is not receipts_v1.MeasurementWindowStateV1.CLOSED
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "cutoff receipt identity differs from its occurrence join"
        )
    _validate_cutoff_markers(
        identity_join=identity_join,
        window=receipt_set.window,
        markers=rows,
    )
    return OperationalCutoffAttestationV1(
        _CUTOFF_ISSUER,
        identity_join.identity_join_id,
        receipt_set.identity.identity_binding_id,
        receipt_set.receipt_set_id,
        receipt_set.window.window_id,
        identity_join.occurrence_id,
        identity_join.route_attempt_id,
        identity_join.decision_point_id,
        identity_join.partial_native_transcript_id,
        identity_join.transcript_terminal_id,
        identity_join.execution_terminal_status,
        rows,
    )


@dataclass(frozen=True, slots=True)
class OperationalCutoffVerificationV1:
    _issuer: InitVar[object]
    cutoff_attestation_id: str
    occurrence_identity_join_id: str
    measurement_window_id: str
    marker_count: int
    last_business_sequence: int | None
    cutoff_sequence: int
    accounting_tail_count: int
    provenance_tail_count: int

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _VERIFICATION_ISSUER:
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "cutoff verification is caller-minted"
            )
        for name in (
            "cutoff_attestation_id",
            "occurrence_identity_join_id",
            "measurement_window_id",
        ):
            _cid(getattr(self, name), name)
        for name in (
            "marker_count",
            "cutoff_sequence",
            "accounting_tail_count",
            "provenance_tail_count",
        ):
            _nonnegative(getattr(self, name), name)
        if self.last_business_sequence is not None:
            _nonnegative(self.last_business_sequence, "last business sequence")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_operational_cutoff_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "operational_cutoff_attestation_id": self.cutoff_attestation_id,
            "occurrence_identity_join_id": self.occurrence_identity_join_id,
            "measurement_window_id": self.measurement_window_id,
            "marker_count": self.marker_count,
            "last_business_sequence": self.last_business_sequence,
            "cutoff_sequence": self.cutoff_sequence,
            "accounting_tail_count": self.accounting_tail_count,
            "provenance_tail_count": self.provenance_tail_count,
            "ordered_marker_structure_replayed": True,
            "marker_structure_contains_business_work_after_cutoff": False,
            "source_event_business_work_after_cutoff": {
                "kind": "UNKNOWN",
                "reason": "SOURCE_EVENT_BYTES_NOT_INDEPENDENTLY_REPLAYED",
            },
            "post_cutoff_tail_output_byte_exclusion_verified": {
                "kind": "UNKNOWN",
                "reason": "OUTPUT_BYTE_RECEIPT_NOT_SEMANTICALLY_REPLAYED",
            },
            "source_event_bytes_independently_replayed": False,
            "outer_supervisor_semantics_verified": False,
            "formal_vector_authorized": False,
        }

    @property
    def cutoff_verification_id(self) -> str:
        return _content_id(
            CONSTRUCTION_OPERATIONAL_CUTOFF_VERIFICATION_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "operational_cutoff_verification_id": self.cutoff_verification_id,
        }


def verify_operational_cutoff_attestation_v1(
    attestation: OperationalCutoffAttestationV1,
    *,
    identity_join: ConstructionOccurrenceIdentityJoinV1,
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
) -> OperationalCutoffVerificationV1:
    if type(attestation) is not OperationalCutoffAttestationV1:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "cutoff verifier requires an exact attestation"
        )
    expected = freeze_operational_cutoff_attestation_v1(
        identity_join=identity_join,
        receipt_set=receipt_set,
        markers=attestation.markers,
    )
    if expected != attestation or expected.cutoff_attestation_id != attestation.cutoff_attestation_id:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "operational cutoff differs from deterministic structural replay"
        )
    business = tuple(
        row.sequence
        for row in attestation.markers
        if row.kind is OperationalSequenceKindV1.BUSINESS_WORK
    )
    cutoff = next(
        row.sequence
        for row in attestation.markers
        if row.kind is OperationalSequenceKindV1.OPERATIONAL_CUTOFF
    )
    return OperationalCutoffVerificationV1(
        _VERIFICATION_ISSUER,
        attestation.cutoff_attestation_id,
        identity_join.identity_join_id,
        receipt_set.window.window_id,
        len(attestation.markers),
        max(business) if business else None,
        cutoff,
        sum(
            row.kind is OperationalSequenceKindV1.ACCOUNTING_TAIL
            for row in attestation.markers
        ),
        sum(
            row.kind is OperationalSequenceKindV1.PROVENANCE_TAIL
            for row in attestation.markers
        ),
    )


@dataclass(frozen=True, slots=True)
class ConstructionOccurrenceIdentityJoinVerificationV1:
    _issuer: InitVar[object]
    identity_join_id: str
    evidence_closure_verification_id: str
    receipt_set_id: str
    cutoff_verification_id: str | MissingIndependentAuthorityV1
    blocker_codes: tuple[IdentityJoinBlockerCodeV1, ...]

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _VERIFICATION_ISSUER:
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "identity-join verification is caller-minted"
            )
        for name in (
            "identity_join_id",
            "evidence_closure_verification_id",
            "receipt_set_id",
        ):
            _cid(getattr(self, name), name)
        if type(self.cutoff_verification_id) is str:
            _cid(self.cutoff_verification_id, "cutoff verification")
        elif (
            type(self.cutoff_verification_id) is not MissingIndependentAuthorityV1
            or self.cutoff_verification_id != _missing_cutoff_authority()
        ):
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "missing cutoff verification must remain a typed blocker"
            )
        normalized = tuple(
            _enum(IdentityJoinBlockerCodeV1, row, "join blocker")
            for row in self.blocker_codes
        )
        if (
            normalized != tuple(sorted(normalized, key=lambda row: row.value))
            or len(set(normalized)) != len(normalized)
            or not normalized
        ):
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "join blockers must be nonempty, sorted, and unique"
            )
        object.__setattr__(self, "blocker_codes", normalized)

    def _payload(self) -> dict[str, Any]:
        cutoff_ref: Any = self.cutoff_verification_id
        if type(cutoff_ref) is MissingIndependentAuthorityV1:
            cutoff_ref = cutoff_ref.to_document()
        return {
            "schema": "acfqp.construction_occurrence_identity_join_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_identity_join_id": self.identity_join_id,
            "evidence_closure_verification_id": (
                self.evidence_closure_verification_id
            ),
            "shared_resource_receipt_set_id": self.receipt_set_id,
            "operational_cutoff_verification_id": cutoff_ref,
            "blocker_codes": [row.value for row in self.blocker_codes],
            "structural_identity_replayed": True,
            "independent_semantic_replay_status": (
                IndependentSemanticReplayStatusV1.NOT_RUN.value
            ),
            "semantic_accounting_authority": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vector_authorized": False,
        }

    @property
    def verification_id(self) -> str:
        return _content_id(
            CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_VERIFICATION_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "identity_join_verification_id": self.verification_id}


def verify_construction_occurrence_identity_join_v1(
    join: ConstructionOccurrenceIdentityJoinV1,
    *,
    owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
    evidence_closure: closure_v1.EvidenceClosureV1,
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
    cutoff_attestation: OperationalCutoffAttestationV1 | None = None,
) -> ConstructionOccurrenceIdentityJoinVerificationV1:
    if type(join) is not ConstructionOccurrenceIdentityJoinV1:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "identity verifier requires an exact join"
        )
    expected = freeze_construction_occurrence_identity_join_v1(
        owned_result=owned_result,
        evidence_closure=evidence_closure,
        receipt_set=receipt_set,
    )
    if expected != join or expected.identity_join_id != join.identity_join_id:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "identity join differs from deterministic structural replay"
        )
    closure_replay = closure_v1.verify_evidence_closure_coverage_v1(
        evidence_closure
    )
    blockers = {
        IdentityJoinBlockerCodeV1.OWNED_RESULT_PARTIAL_NATIVE_ONLY,
        IdentityJoinBlockerCodeV1.ROUTE_CONTEXT_AUTHORITY_NOT_AVAILABLE,
        (
            IdentityJoinBlockerCodeV1
            .SHARED_RECEIPT_SEMANTICS_NOT_INDEPENDENTLY_REPLAYED
        ),
        IdentityJoinBlockerCodeV1.CUTOFF_AUTHORITY_NOT_INDEPENDENTLY_REPLAYED,
    }
    if closure_replay.completeness is closure_v1.EvidenceClosureCompletenessV1.INCOMPLETE:
        blockers.add(IdentityJoinBlockerCodeV1.EVIDENCE_CLOSURE_INCOMPLETE)
    if not receipt_set.all_receipts_structurally_recorded:
        blockers.add(IdentityJoinBlockerCodeV1.SHARED_RECEIPTS_INCOMPLETE_TYPED)

    cutoff_ref: str | MissingIndependentAuthorityV1
    if cutoff_attestation is None:
        cutoff_ref = _missing_cutoff_authority()
    else:
        cutoff_ref = verify_operational_cutoff_attestation_v1(
            cutoff_attestation,
            identity_join=join,
            receipt_set=receipt_set,
        ).cutoff_verification_id
    return ConstructionOccurrenceIdentityJoinVerificationV1(
        _VERIFICATION_ISSUER,
        join.identity_join_id,
        closure_replay.verification_id,
        receipt_set.receipt_set_id,
        cutoff_ref,
        tuple(sorted(blockers, key=lambda row: row.value)),
    )


@dataclass(frozen=True, slots=True)
class ConstructionIdentityJoinReadinessV1:
    """Current-path readiness when route context/receipts/cutoff do not exist."""

    _issuer: InitVar[object]
    owned_partial_result_id: str
    evidence_closure_context_id: str
    evidence_closure_id: str
    occurrence_id: str
    transcript_id: str
    transcript_terminal_id: str
    route_attempt_id: MissingIndependentAuthorityV1
    decision_point_id: MissingIndependentAuthorityV1
    receipt_set_id: MissingIndependentAuthorityV1
    cutoff_attestation_id: MissingIndependentAuthorityV1
    blocker_codes: tuple[IdentityJoinBlockerCodeV1, ...]

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _READINESS_ISSUER:
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "identity readiness is caller-minted"
            )
        for name in (
            "owned_partial_result_id",
            "evidence_closure_context_id",
            "evidence_closure_id",
            "occurrence_id",
            "transcript_id",
            "transcript_terminal_id",
        ):
            _cid(getattr(self, name), name)
        for name in ("route_attempt_id", "decision_point_id"):
            value = getattr(self, name)
            if (
                type(value) is not MissingIndependentAuthorityV1
                or value != _missing_route_context_authority()
            ):
                raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                    "missing route/receipt identity must remain typed"
                )
        if (
            type(self.receipt_set_id) is not MissingIndependentAuthorityV1
            or self.receipt_set_id != _missing_receipt_set_authority()
        ):
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "missing receipt-set identity must remain typed"
            )
        if (
            type(self.cutoff_attestation_id) is not MissingIndependentAuthorityV1
            or self.cutoff_attestation_id != _missing_cutoff_authority()
        ):
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "missing cutoff identity must remain typed"
            )
        normalized = tuple(
            _enum(IdentityJoinBlockerCodeV1, row, "readiness blocker")
            for row in self.blocker_codes
        )
        if normalized != tuple(sorted(set(normalized), key=lambda row: row.value)):
            raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
                "readiness blockers must be sorted and unique"
            )
        object.__setattr__(self, "blocker_codes", normalized)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_identity_join_readiness.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_partial_result_id": self.owned_partial_result_id,
            "evidence_closure_context_id": self.evidence_closure_context_id,
            "evidence_closure_id": self.evidence_closure_id,
            "occurrence_id": self.occurrence_id,
            "transcript_id": self.transcript_id,
            "transcript_terminal_id": self.transcript_terminal_id,
            "route_attempt_id": self.route_attempt_id.to_document(),
            "decision_point_id": self.decision_point_id.to_document(),
            "shared_resource_receipt_set_id": self.receipt_set_id.to_document(),
            "operational_cutoff_attestation_id": (
                self.cutoff_attestation_id.to_document()
            ),
            "status": IdentityJoinReadinessStatusV1.NOT_READY_SCHEMA_ONLY.value,
            "blocker_codes": [row.value for row in self.blocker_codes],
            "identity_join_issued": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
        }

    @property
    def readiness_id(self) -> str:
        return _content_id(
            CONSTRUCTION_IDENTITY_JOIN_READINESS_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "identity_join_readiness_id": self.readiness_id}


def assess_current_identity_join_readiness_v1(
    *,
    owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
    evidence_closure: closure_v1.EvidenceClosureV1,
) -> ConstructionIdentityJoinReadinessV1:
    """Describe the honest current state without inventing route IDs/receipts."""

    if (
        type(owned_result) is not owned_v1.V075K7RootCapOwnedPartialResultV1
        or type(evidence_closure) is not closure_v1.EvidenceClosureV1
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "readiness requires exact owned and closure roots"
        )
    transcript = owned_result.transcript
    terminal_id = _terminal_id(transcript)
    context = evidence_closure.context
    try:
        owned_result.__post_init__(owned_v1._WRAPPER_RESULT_ISSUER)  # noqa: SLF001
        partial_v1.verify_partial_native_occurrence_transcript_v1(transcript)
        closure_replay = closure_v1.verify_evidence_closure_coverage_v1(
            evidence_closure
        )
    except Exception as error:
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "readiness root failed structural replay"
        ) from error
    if (
        context.counter_registry_id != owned_result.counter_registry_id
        or context.stage_profile_id != owned_result.stage_profile_id
        or context.boundary_profile_id != owned_result.boundary_profile_id
        or context.execution_profile_id != owned_result.execution_profile_id
        or context.transcript_id != transcript.transcript_id
        or context.terminal_id != terminal_id
    ):
        raise ConstructionOccurrenceIdentityCutoffJoinV1Error(
            "readiness closure context differs from owned transcript"
        )
    blockers = {
        IdentityJoinBlockerCodeV1.OWNED_RESULT_PARTIAL_NATIVE_ONLY,
        IdentityJoinBlockerCodeV1.ROUTE_CONTEXT_AUTHORITY_NOT_AVAILABLE,
        (
            IdentityJoinBlockerCodeV1
            .SHARED_RECEIPT_SEMANTICS_NOT_INDEPENDENTLY_REPLAYED
        ),
        IdentityJoinBlockerCodeV1.SHARED_RECEIPTS_INCOMPLETE_TYPED,
        IdentityJoinBlockerCodeV1.CUTOFF_AUTHORITY_NOT_INDEPENDENTLY_REPLAYED,
    }
    if closure_replay.completeness is closure_v1.EvidenceClosureCompletenessV1.INCOMPLETE:
        blockers.add(IdentityJoinBlockerCodeV1.EVIDENCE_CLOSURE_INCOMPLETE)
    route_missing = _missing_route_context_authority()
    receipt_missing = _missing_receipt_set_authority()
    cutoff_missing = _missing_cutoff_authority()
    return ConstructionIdentityJoinReadinessV1(
        _READINESS_ISSUER,
        owned_result.wrapper_id,
        context.context_id,
        evidence_closure.closure_id,
        transcript.start.occurrence_id,
        transcript.transcript_id,
        terminal_id,
        route_missing,
        route_missing,
        receipt_missing,
        cutoff_missing,
        tuple(sorted(blockers, key=lambda row: row.value)),
    )


__all__ = [
    "CONSTRUCTION_IDENTITY_JOIN_READINESS_V1_DOMAIN",
    "CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_V1_DOMAIN",
    "CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_VERIFICATION_V1_DOMAIN",
    "CONSTRUCTION_OPERATIONAL_CUTOFF_ATTESTATION_V1_DOMAIN",
    "CONSTRUCTION_OPERATIONAL_CUTOFF_VERIFICATION_V1_DOMAIN",
    "CONSTRUCTION_OPERATIONAL_SEQUENCE_MARKER_V1_DOMAIN",
    "ConstructionExecutionStatusV1",
    "ConstructionIdentityJoinReadinessV1",
    "ConstructionOccurrenceIdentityCutoffJoinV1Error",
    "ConstructionOccurrenceIdentityJoinV1",
    "ConstructionOccurrenceIdentityJoinVerificationV1",
    "IdentityJoinBlockerCodeV1",
    "IdentityJoinReadinessStatusV1",
    "IndependentSemanticReplayStatusV1",
    "MissingIndependentAuthorityV1",
    "OperationalCutoffAttestationV1",
    "OperationalCutoffVerificationV1",
    "OperationalSequenceKindV1",
    "OperationalSequenceMarkerV1",
    "PROFILE_KEY",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "assess_current_identity_join_readiness_v1",
    "freeze_construction_occurrence_identity_join_v1",
    "freeze_operational_cutoff_attestation_v1",
    "verify_construction_occurrence_identity_join_v1",
    "verify_operational_cutoff_attestation_v1",
]
