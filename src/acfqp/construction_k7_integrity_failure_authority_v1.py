"""Non-retroactive K7 integrity-failure accounting authority.

This successor closes the ``WORK_VECTOR=INVALID`` hole in the generic K7
terminal matrix without ever minting an invalid ``WorkVector``.  The terminal
is derived from an externally anchored expected-artifact identity and the
bytes actually read.  Every V6 required counter leaf is materialized as an
observed ``CounterRecordV1`` (including explicit native zeroes), so an empty
pre-failure event prefix remains a complete typed accounting prefix.

The authority distinguishes integrity failure from protocol failure:
non-contiguous access sequences, post-cutoff events, invalid counter metadata,
or route-family violations are rejected as protocol errors and cannot be
relabelled as ``INTEGRITY_FAILURE``.  A valid result is always exactly

``ROUTE_ATTEMPT / ATTEMPT_CLOSURE_NONCERTIFICATE / INTEGRITY_FAILURE``.

The independent byte verifier reconstructs the identity violation, access
cutoff, all 202 records, the WorkVector, the eight-axis comparison, and the
terminal.  It does not invoke the producer.  This construction does not issue
a certificate, classify infeasibility, close a logical occurrence, or unlock
an official Gate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import re
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import (
    SHARED_AXES,
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_EXPECTED_ARTIFACT_IDENTITY_V1_DOMAIN,
    CONSTRUCTION_K7_INTEGRITY_ACCESS_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_INTEGRITY_ACCESS_SEQUENCE_V1_DOMAIN,
    CONSTRUCTION_K7_INTEGRITY_ATTEMPT_CONTEXT_V1_DOMAIN,
    CONSTRUCTION_K7_INTEGRITY_FAILURE_BUNDLE_V1_DOMAIN,
    CONSTRUCTION_K7_INTEGRITY_FAILURE_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_INTEGRITY_PREFIX_COMPLETENESS_V1_DOMAIN,
    CONSTRUCTION_K7_INTEGRITY_PREFIX_RECORDER_V1_DOMAIN,
    CONSTRUCTION_K7_INTEGRITY_READ_RECEIPT_V1_DOMAIN,
    CONSTRUCTION_K7_INTEGRITY_TERMINAL_AUTHORITY_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.35"
PROFILE_KEY = "construction_k7_integrity_failure_authority_v1"

EXPECTED_COUNTER_RECORD_COUNT = registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
EXPECTED_COMPARISON_AXIS_COUNT = len(SHARED_AXES)

TERMINAL_SCOPE = "ROUTE_ATTEMPT"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = "INTEGRITY_FAILURE"
SPECIFIC_CAUSE = "ARTIFACT_IDENTITY_MISMATCH"

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

EXPECTED_ARTIFACT_IDENTITY_V1_DOMAIN = (
    CONSTRUCTION_K7_EXPECTED_ARTIFACT_IDENTITY_V1_DOMAIN
)
INTEGRITY_ATTEMPT_CONTEXT_V1_DOMAIN = (
    CONSTRUCTION_K7_INTEGRITY_ATTEMPT_CONTEXT_V1_DOMAIN
)
INTEGRITY_ACCESS_EVENT_V1_DOMAIN = (
    CONSTRUCTION_K7_INTEGRITY_ACCESS_EVENT_V1_DOMAIN
)
INTEGRITY_READ_RECEIPT_V1_DOMAIN = (
    CONSTRUCTION_K7_INTEGRITY_READ_RECEIPT_V1_DOMAIN
)
INTEGRITY_ACCESS_SEQUENCE_V1_DOMAIN = (
    CONSTRUCTION_K7_INTEGRITY_ACCESS_SEQUENCE_V1_DOMAIN
)
INTEGRITY_PREFIX_RECORDER_V1_DOMAIN = (
    CONSTRUCTION_K7_INTEGRITY_PREFIX_RECORDER_V1_DOMAIN
)
INTEGRITY_PREFIX_COMPLETENESS_V1_DOMAIN = (
    CONSTRUCTION_K7_INTEGRITY_PREFIX_COMPLETENESS_V1_DOMAIN
)
INTEGRITY_TERMINAL_AUTHORITY_V1_DOMAIN = (
    CONSTRUCTION_K7_INTEGRITY_TERMINAL_AUTHORITY_V1_DOMAIN
)
INTEGRITY_FAILURE_BUNDLE_V1_DOMAIN = (
    CONSTRUCTION_K7_INTEGRITY_FAILURE_BUNDLE_V1_DOMAIN
)
INTEGRITY_FAILURE_VERIFICATION_V1_DOMAIN = (
    CONSTRUCTION_K7_INTEGRITY_FAILURE_VERIFICATION_V1_DOMAIN
)

LOCAL_DOMAINS = frozenset(
    {
        EXPECTED_ARTIFACT_IDENTITY_V1_DOMAIN,
        INTEGRITY_ATTEMPT_CONTEXT_V1_DOMAIN,
        INTEGRITY_ACCESS_EVENT_V1_DOMAIN,
        INTEGRITY_READ_RECEIPT_V1_DOMAIN,
        INTEGRITY_ACCESS_SEQUENCE_V1_DOMAIN,
        INTEGRITY_PREFIX_RECORDER_V1_DOMAIN,
        INTEGRITY_PREFIX_COMPLETENESS_V1_DOMAIN,
        INTEGRITY_TERMINAL_AUTHORITY_V1_DOMAIN,
        INTEGRITY_FAILURE_BUNDLE_V1_DOMAIN,
        INTEGRITY_FAILURE_VERIFICATION_V1_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 10 or not LOCAL_DOMAINS.issubset(  # pragma: no cover
    PHASE3E_DOMAIN_TAGS
):
    raise RuntimeError(
        "K7 integrity-failure domains must be unique and centrally registered"
    )

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_EXPECTED_IDENTITY_ISSUER = object()
_READ_RECEIPT_ISSUER = object()
_ACCESS_SEQUENCE_ISSUER = object()
_COMPLETENESS_ISSUER = object()
_TERMINAL_ISSUER = object()
_BUNDLE_ISSUER = object()
_VERIFICATION_ISSUER = object()


class ConstructionK7IntegrityFailureAuthorityV1Error(ValueError):
    """An identity, prefix, accounting vector, or terminal failed replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7IntegrityFailureAuthorityV1Error(message)


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("K7 integrity-failure authority used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _raw_domain_id(domain: str, raw: bytes) -> str:
    _identifier(domain, "artifact content domain")
    if type(raw) is not bytes:
        _fail("artifact bytes must be exact bytes")
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + raw).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7IntegrityFailureAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        _fail(f"{label} must be one canonical identifier")
    return value


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        _fail(f"{label} must be one lowercase SHA-256")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _positive(value: Any, label: str) -> int:
    if _nonnegative(value, label) == 0:
        _fail(f"{label} must be positive")
    return value


def _canonical_object(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7IntegrityFailureAuthorityV1Error(
            f"{label} bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} bytes are noncanonical")
    return document


def _fields(document: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != expected:
        _fail(f"{label} field set changed")
    return document


class IntegrityFailureCutoffV1(str, Enum):
    EARLY_INPUT_READ = "EARLY_INPUT_READ"
    PRELAUNCH_FREEZE = "PRELAUNCH_FREEZE"
    MIDROUTE_EXECUTION = "MIDROUTE_EXECUTION"
    LATE_TERMINALIZATION = "LATE_TERMINALIZATION"


_CUTOFF_ORDER = {
    IntegrityFailureCutoffV1.EARLY_INPUT_READ: 0,
    IntegrityFailureCutoffV1.PRELAUNCH_FREEZE: 1,
    IntegrityFailureCutoffV1.MIDROUTE_EXECUTION: 2,
    IntegrityFailureCutoffV1.LATE_TERMINALIZATION: 3,
}


class IntegrityViolationReasonV1(str, Enum):
    NONCANONICAL_BYTES = "NONCANONICAL_BYTES"
    CONTENT_ID_MISMATCH = "CONTENT_ID_MISMATCH"
    SHA256_MISMATCH = "SHA256_MISMATCH"
    BYTE_COUNT_MISMATCH = "BYTE_COUNT_MISMATCH"


@dataclass(frozen=True, slots=True)
class K7IntegrityAttemptContextV1:
    structural_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    build_epoch_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    transaction_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.structural_id, "structural identity"),
            (self.query_id, "query identity"),
            (self.selected_plan_id, "selected-plan identity"),
            (self.threshold_profile_id, "threshold identity"),
            (self.build_epoch_id, "build-epoch identity"),
            (self.logical_occurrence_id, "logical-occurrence identity"),
            (self.route_attempt_id, "route-attempt identity"),
            (self.decision_point_id, "decision-point identity"),
            (self.transaction_id, "transaction identity"),
        ):
            _cid(value, label)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_integrity_attempt_context.v1",
            "schema_version": SCHEMA_VERSION,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "build_epoch_id": self.build_epoch_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
        }

    @property
    def context_id(self) -> str:
        return _local_id(INTEGRITY_ATTEMPT_CONTEXT_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "integrity_attempt_context_id": self.context_id}

    @classmethod
    def from_document(cls, document: Any) -> "K7IntegrityAttemptContextV1":
        row = _fields(
            document,
            {
                "schema", "schema_version", "structural_id", "query_id",
                "selected_plan_id", "threshold_profile_id", "build_epoch_id",
                "logical_occurrence_id", "route_attempt_id", "decision_point_id",
                "transaction_id", "integrity_attempt_context_id",
            },
            "integrity attempt context",
        )
        if (
            row["schema"] != "acfqp.construction_k7_integrity_attempt_context.v1"
            or row["schema_version"] != SCHEMA_VERSION
        ):
            _fail("integrity attempt context schema changed")
        result = cls(
            row["structural_id"], row["query_id"], row["selected_plan_id"],
            row["threshold_profile_id"], row["build_epoch_id"],
            row["logical_occurrence_id"], row["route_attempt_id"],
            row["decision_point_id"], row["transaction_id"],
        )
        if row["integrity_attempt_context_id"] != result.context_id:
            _fail("integrity attempt context identity changed")
        return result


@dataclass(frozen=True, slots=True)
class K7ExpectedArtifactIdentityV1:
    _issuer: InitVar[object]
    artifact_role: str
    artifact_schema: str
    content_domain: str
    source_locator_id: str
    expected_artifact_id: str
    expected_sha256: str
    expected_byte_count: int
    _identity_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _EXPECTED_IDENTITY_ISSUER:
            _fail("expected artifact identity is caller-minted")
        _identifier(self.artifact_role, "artifact role")
        _identifier(self.artifact_schema, "artifact schema")
        _identifier(self.content_domain, "artifact content domain")
        _cid(self.source_locator_id, "source locator")
        _cid(self.expected_artifact_id, "expected artifact")
        _sha256(self.expected_sha256, "expected byte digest")
        _nonnegative(self.expected_byte_count, "expected byte count")
        object.__setattr__(
            self, "_identity_id",
            _local_id(EXPECTED_ARTIFACT_IDENTITY_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_expected_artifact_identity.v1",
            "schema_version": SCHEMA_VERSION,
            "artifact_role": self.artifact_role,
            "artifact_schema": self.artifact_schema,
            "content_domain": self.content_domain,
            "source_locator_id": self.source_locator_id,
            "expected_artifact_id": self.expected_artifact_id,
            "expected_sha256": self.expected_sha256,
            "expected_byte_count": self.expected_byte_count,
        }

    @property
    def identity_id(self) -> str:
        if _local_id(EXPECTED_ARTIFACT_IDENTITY_V1_DOMAIN, self._payload()) != self._identity_id:
            _fail("expected artifact identity changed after freezing")
        return self._identity_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "expected_artifact_identity_id": self.identity_id}

    @classmethod
    def _from_document(cls, document: Any) -> "K7ExpectedArtifactIdentityV1":
        row = _fields(
            document,
            {
                "schema", "schema_version", "artifact_role", "artifact_schema",
                "content_domain", "source_locator_id", "expected_artifact_id",
                "expected_sha256", "expected_byte_count",
                "expected_artifact_identity_id",
            },
            "expected artifact identity",
        )
        if (
            row["schema"] != "acfqp.construction_k7_expected_artifact_identity.v1"
            or row["schema_version"] != SCHEMA_VERSION
        ):
            _fail("expected artifact identity schema changed")
        result = cls(
            _EXPECTED_IDENTITY_ISSUER,
            row["artifact_role"], row["artifact_schema"], row["content_domain"],
            row["source_locator_id"], row["expected_artifact_id"],
            row["expected_sha256"], row["expected_byte_count"],
        )
        if row["expected_artifact_identity_id"] != result.identity_id:
            _fail("expected artifact identity content ID changed")
        return result


def freeze_k7_expected_artifact_identity_v1(
    *,
    artifact_role: str,
    artifact_schema: str,
    content_domain: str,
    source_locator_id: str,
    expected_bytes: bytes,
) -> K7ExpectedArtifactIdentityV1:
    """Freeze an externally retained expected-byte identity anchor."""

    if type(expected_bytes) is not bytes or not expected_bytes:
        _fail("expected artifact bytes are missing")
    try:
        parsed = loads_canonical_json(expected_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7IntegrityFailureAuthorityV1Error(
            "expected artifact bytes must be canonical JSON"
        ) from error
    if canonical_json_bytes(parsed) != expected_bytes:
        _fail("expected artifact bytes must be canonical JSON")
    return K7ExpectedArtifactIdentityV1(
        _EXPECTED_IDENTITY_ISSUER,
        artifact_role,
        artifact_schema,
        content_domain,
        source_locator_id,
        _raw_domain_id(content_domain, expected_bytes),
        hashlib.sha256(expected_bytes).hexdigest(),
        len(expected_bytes),
    )


@dataclass(frozen=True, slots=True, order=True)
class K7IntegrityCounterDeltaV1:
    path: str
    value: int

    def __post_init__(self) -> None:
        _identifier(self.path, "counter path")
        _positive(self.value, "counter delta")

    def to_document(self) -> dict[str, Any]:
        return {"path": self.path, "value": self.value}

    @classmethod
    def from_document(cls, document: Any) -> "K7IntegrityCounterDeltaV1":
        row = _fields(document, {"path", "value"}, "counter delta")
        return cls(row["path"], row["value"])


@dataclass(frozen=True, slots=True)
class K7IntegrityAccessEventV1:
    context_id: str
    sequence_number: int
    phase: IntegrityFailureCutoffV1
    event_kind: str
    evidence_ref_id: str
    counter_deltas: tuple[K7IntegrityCounterDeltaV1, ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "event context")
        _positive(self.sequence_number, "event sequence number")
        try:
            object.__setattr__(self, "phase", IntegrityFailureCutoffV1(self.phase))
        except (TypeError, ValueError) as error:
            raise ConstructionK7IntegrityFailureAuthorityV1Error(
                "access event phase is invalid"
            ) from error
        _identifier(self.event_kind, "event kind")
        _cid(self.evidence_ref_id, "event evidence")
        if (
            type(self.counter_deltas) is not tuple
            or not self.counter_deltas
            or tuple(sorted(self.counter_deltas, key=lambda row: row.path))
            != self.counter_deltas
            or len({row.path for row in self.counter_deltas})
            != len(self.counter_deltas)
        ):
            _fail("event counter deltas must be nonempty, unique, and path-sorted")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_integrity_access_event.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "sequence_number": self.sequence_number,
            "phase": self.phase.value,
            "event_kind": self.event_kind,
            "evidence_ref_id": self.evidence_ref_id,
            "counter_deltas": [row.to_document() for row in self.counter_deltas],
        }

    @property
    def event_id(self) -> str:
        return _local_id(INTEGRITY_ACCESS_EVENT_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "integrity_access_event_id": self.event_id}

    @classmethod
    def from_document(cls, document: Any) -> "K7IntegrityAccessEventV1":
        row = _fields(
            document,
            {
                "schema", "schema_version", "context_id", "sequence_number",
                "phase", "event_kind", "evidence_ref_id", "counter_deltas",
                "integrity_access_event_id",
            },
            "integrity access event",
        )
        if (
            row["schema"] != "acfqp.construction_k7_integrity_access_event.v1"
            or row["schema_version"] != SCHEMA_VERSION
            or type(row["counter_deltas"]) is not list
        ):
            _fail("integrity access event schema changed")
        result = cls(
            row["context_id"], row["sequence_number"], row["phase"],
            row["event_kind"], row["evidence_ref_id"],
            tuple(K7IntegrityCounterDeltaV1.from_document(item) for item in row["counter_deltas"]),
        )
        if row["integrity_access_event_id"] != result.event_id:
            _fail("integrity access event identity changed")
        return result


def _canonicality_of(raw: bytes) -> bool:
    try:
        parsed = loads_canonical_json(raw)
    except (TypeError, ValueError):
        return False
    return canonical_json_bytes(parsed) == raw


def _derive_violation(
    expected: K7ExpectedArtifactIdentityV1,
    offending_bytes: bytes,
) -> tuple[str, str, int, tuple[IntegrityViolationReasonV1, ...]]:
    if type(offending_bytes) is not bytes:
        _fail("offending artifact must be exact bytes")
    observed_sha = hashlib.sha256(offending_bytes).hexdigest()
    observed_id = _raw_domain_id(expected.content_domain, offending_bytes)
    reasons: list[IntegrityViolationReasonV1] = []
    if not _canonicality_of(offending_bytes):
        reasons.append(IntegrityViolationReasonV1.NONCANONICAL_BYTES)
    if observed_id != expected.expected_artifact_id:
        reasons.append(IntegrityViolationReasonV1.CONTENT_ID_MISMATCH)
    if observed_sha != expected.expected_sha256:
        reasons.append(IntegrityViolationReasonV1.SHA256_MISMATCH)
    if len(offending_bytes) != expected.expected_byte_count:
        reasons.append(IntegrityViolationReasonV1.BYTE_COUNT_MISMATCH)
    if not reasons:
        _fail("artifact bytes match the expected identity; no integrity failure exists")
    return observed_id, observed_sha, len(offending_bytes), tuple(reasons)


@dataclass(frozen=True, slots=True)
class K7IntegrityReadReceiptV1:
    _issuer: InitVar[object]
    context_id: str
    cutoff: IntegrityFailureCutoffV1
    access_sequence_number: int
    expected_identity_id: str
    source_locator_id: str
    expected_artifact_id: str
    observed_artifact_id: str
    expected_sha256: str
    observed_sha256: str
    expected_byte_count: int
    observed_byte_count: int
    violation_reasons: tuple[IntegrityViolationReasonV1, ...]
    _receipt_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _READ_RECEIPT_ISSUER:
            _fail("integrity read receipt is caller-minted")
        _cid(self.context_id, "read-receipt context")
        try:
            object.__setattr__(self, "cutoff", IntegrityFailureCutoffV1(self.cutoff))
        except (TypeError, ValueError) as error:
            raise ConstructionK7IntegrityFailureAuthorityV1Error(
                "read-receipt cutoff is invalid"
            ) from error
        _positive(self.access_sequence_number, "read sequence number")
        for value, label in (
            (self.expected_identity_id, "expected identity"),
            (self.source_locator_id, "source locator"),
            (self.expected_artifact_id, "expected artifact"),
            (self.observed_artifact_id, "observed artifact"),
        ):
            _cid(value, label)
        _sha256(self.expected_sha256, "expected digest")
        _sha256(self.observed_sha256, "observed digest")
        _nonnegative(self.expected_byte_count, "expected byte count")
        _nonnegative(self.observed_byte_count, "observed byte count")
        try:
            reasons = tuple(IntegrityViolationReasonV1(item) for item in self.violation_reasons)
        except (TypeError, ValueError) as error:
            raise ConstructionK7IntegrityFailureAuthorityV1Error(
                "integrity violation reason is invalid"
            ) from error
        object.__setattr__(self, "violation_reasons", reasons)
        if not reasons or len(set(reasons)) != len(reasons):
            _fail("integrity read receipt needs unique nonempty violation reasons")
        object.__setattr__(
            self, "_receipt_id",
            _local_id(INTEGRITY_READ_RECEIPT_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_integrity_read_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "cutoff": self.cutoff.value,
            "access_sequence_number": self.access_sequence_number,
            "expected_identity_id": self.expected_identity_id,
            "source_locator_id": self.source_locator_id,
            "expected_artifact_id": self.expected_artifact_id,
            "observed_artifact_id": self.observed_artifact_id,
            "expected_sha256": self.expected_sha256,
            "observed_sha256": self.observed_sha256,
            "expected_byte_count": self.expected_byte_count,
            "observed_byte_count": self.observed_byte_count,
            "violation_reasons": [row.value for row in self.violation_reasons],
            "read_counter_path": "io.read_bytes",
            "read_counter_value": self.observed_byte_count,
            "hash_counter_path": "integrity.bytes_hashed",
            "hash_counter_value": self.observed_byte_count,
        }

    @property
    def receipt_id(self) -> str:
        if _local_id(INTEGRITY_READ_RECEIPT_V1_DOMAIN, self._payload()) != self._receipt_id:
            _fail("integrity read receipt changed after issuance")
        return self._receipt_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "integrity_read_receipt_id": self.receipt_id}

    @classmethod
    def _from_document(cls, document: Any) -> "K7IntegrityReadReceiptV1":
        row = _fields(
            document,
            {
                "schema", "schema_version", "context_id", "cutoff",
                "access_sequence_number", "expected_identity_id",
                "source_locator_id", "expected_artifact_id", "observed_artifact_id",
                "expected_sha256", "observed_sha256", "expected_byte_count",
                "observed_byte_count", "violation_reasons", "read_counter_path",
                "read_counter_value", "hash_counter_path", "hash_counter_value",
                "integrity_read_receipt_id",
            },
            "integrity read receipt",
        )
        if (
            row["schema"] != "acfqp.construction_k7_integrity_read_receipt.v1"
            or row["schema_version"] != SCHEMA_VERSION
            or row["read_counter_path"] != "io.read_bytes"
            or row["hash_counter_path"] != "integrity.bytes_hashed"
            or row["read_counter_value"] != row["observed_byte_count"]
            or row["hash_counter_value"] != row["observed_byte_count"]
            or type(row["violation_reasons"]) is not list
        ):
            _fail("integrity read receipt schema or accounting locks changed")
        result = cls(
            _READ_RECEIPT_ISSUER,
            row["context_id"], row["cutoff"], row["access_sequence_number"],
            row["expected_identity_id"], row["source_locator_id"],
            row["expected_artifact_id"], row["observed_artifact_id"],
            row["expected_sha256"], row["observed_sha256"],
            row["expected_byte_count"], row["observed_byte_count"],
            tuple(row["violation_reasons"]),
        )
        if row["integrity_read_receipt_id"] != result.receipt_id:
            _fail("integrity read receipt identity changed")
        return result


def _make_read_receipt(
    *,
    context: K7IntegrityAttemptContextV1,
    cutoff: IntegrityFailureCutoffV1,
    sequence_number: int,
    expected: K7ExpectedArtifactIdentityV1,
    offending_bytes: bytes,
) -> K7IntegrityReadReceiptV1:
    observed_id, observed_sha, observed_count, reasons = _derive_violation(
        expected, offending_bytes
    )
    return K7IntegrityReadReceiptV1(
        _READ_RECEIPT_ISSUER,
        context.context_id,
        cutoff,
        sequence_number,
        expected.identity_id,
        expected.source_locator_id,
        expected.expected_artifact_id,
        observed_id,
        expected.expected_sha256,
        observed_sha,
        expected.expected_byte_count,
        observed_count,
        reasons,
    )


@dataclass(frozen=True, slots=True)
class K7IntegrityAccessSequenceV1:
    _issuer: InitVar[object]
    context_id: str
    cutoff: IntegrityFailureCutoffV1
    prefix_events: tuple[K7IntegrityAccessEventV1, ...]
    read_receipt: K7IntegrityReadReceiptV1
    detection_sequence_number: int
    _sequence_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ACCESS_SEQUENCE_ISSUER:
            _fail("integrity access sequence is caller-minted")
        _cid(self.context_id, "access-sequence context")
        try:
            cutoff = IntegrityFailureCutoffV1(self.cutoff)
        except (TypeError, ValueError) as error:
            raise ConstructionK7IntegrityFailureAuthorityV1Error(
                "access-sequence cutoff is invalid"
            ) from error
        object.__setattr__(self, "cutoff", cutoff)
        if type(self.prefix_events) is not tuple:
            _fail("prefix events must be one exact tuple")
        expected_numbers = tuple(range(1, len(self.prefix_events) + 1))
        if tuple(row.sequence_number for row in self.prefix_events) != expected_numbers:
            _fail("protocol sequence is not contiguous from one")
        if any(
            row.context_id != self.context_id
            or _CUTOFF_ORDER[row.phase] > _CUTOFF_ORDER[cutoff]
            for row in self.prefix_events
        ):
            _fail("protocol sequence contains a transplanted or post-cutoff event")
        if any(
            _CUTOFF_ORDER[left.phase] > _CUTOFF_ORDER[right.phase]
            for left, right in zip(self.prefix_events, self.prefix_events[1:])
        ):
            _fail("protocol sequence phase order regressed")
        if (
            type(self.read_receipt) is not K7IntegrityReadReceiptV1
            or self.read_receipt.context_id != self.context_id
            or self.read_receipt.cutoff is not cutoff
            or self.read_receipt.access_sequence_number != len(self.prefix_events) + 1
            or self.detection_sequence_number != len(self.prefix_events) + 2
        ):
            _fail("read and detection cutoff sequence changed")
        object.__setattr__(
            self, "_sequence_id",
            _local_id(INTEGRITY_ACCESS_SEQUENCE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_integrity_access_sequence.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "cutoff": self.cutoff.value,
            "prefix_event_ids": [row.event_id for row in self.prefix_events],
            "read_receipt_id": self.read_receipt.receipt_id,
            "read_sequence_number": self.read_receipt.access_sequence_number,
            "detection_sequence_number": self.detection_sequence_number,
            "event_sequence_contiguous": True,
            "post_cutoff_event_count": 0,
        }

    @property
    def sequence_id(self) -> str:
        if _local_id(INTEGRITY_ACCESS_SEQUENCE_V1_DOMAIN, self._payload()) != self._sequence_id:
            _fail("integrity access sequence changed after issuance")
        return self._sequence_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "prefix_events": [row.to_document() for row in self.prefix_events],
            "integrity_access_sequence_id": self.sequence_id,
        }

    @classmethod
    def _from_document(
        cls,
        document: Any,
        receipt: K7IntegrityReadReceiptV1,
    ) -> "K7IntegrityAccessSequenceV1":
        row = _fields(
            document,
            {
                "schema", "schema_version", "context_id", "cutoff",
                "prefix_event_ids", "read_receipt_id", "read_sequence_number",
                "detection_sequence_number", "event_sequence_contiguous",
                "post_cutoff_event_count", "prefix_events",
                "integrity_access_sequence_id",
            },
            "integrity access sequence",
        )
        if (
            row["schema"] != "acfqp.construction_k7_integrity_access_sequence.v1"
            or row["schema_version"] != SCHEMA_VERSION
            or row["event_sequence_contiguous"] is not True
            or row["post_cutoff_event_count"] != 0
            or type(row["prefix_event_ids"]) is not list
            or type(row["prefix_events"]) is not list
        ):
            _fail("integrity access sequence locks changed")
        events = tuple(K7IntegrityAccessEventV1.from_document(item) for item in row["prefix_events"])
        if row["prefix_event_ids"] != [item.event_id for item in events]:
            _fail("integrity access event identity list changed")
        result = cls(
            _ACCESS_SEQUENCE_ISSUER,
            row["context_id"], row["cutoff"], events, receipt,
            row["detection_sequence_number"],
        )
        if (
            row["read_receipt_id"] != receipt.receipt_id
            or row["read_sequence_number"] != receipt.access_sequence_number
            or row["integrity_access_sequence_id"] != result.sequence_id
        ):
            _fail("integrity access sequence identity changed")
        return result


def _validate_route_exclusivity(
    route_kind: RouteKindEnum,
    values: Mapping[str, int],
) -> None:
    if route_kind is RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE:
        _fail("an integrity failure cannot use an abstract-certificate route kind")
    if route_kind is RouteKindEnum.LOCAL_ATTEMPT:
        families = ("fallback.", "rebuild.")
    elif route_kind is RouteKindEnum.DIRECT_FALLBACK:
        families = ("local.", "rebuild.")
    elif route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX:
        families = ("local.", "fallback.", "rebuild.")
    elif route_kind is RouteKindEnum.REBUILD:
        families = ("common.", "local.", "fallback.", "control.")
    else:  # pragma: no cover
        _fail("unknown integrity-failure route kind")
    invalid = sorted(
        path
        for path, value in values.items()
        if value
        and any(path.startswith(prefix) for prefix in families)
        and not (
            route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
            and path == "local.causal_candidate_evaluations"
        )
    )
    if invalid:
        _fail(f"route-family exclusivity failed for integrity prefix: {invalid!r}")


def _derive_prefix_values(
    *,
    route_kind: RouteKindEnum,
    access: K7IntegrityAccessSequenceV1,
) -> tuple[registry_v6.CounterRegistryV6, dict[str, int]]:
    registry = registry_v6.official_counter_registry_v6()
    registry.validate_official_catalogue()
    required = set(registry.required_paths)
    values = {path: 0 for path in registry.required_paths}
    reserved = {"route.attempts", "route.successes", "route.failures"}
    for event in access.prefix_events:
        for delta in event.counter_deltas:
            if delta.path not in required:
                _fail(f"protocol event names an unknown or optional counter path {delta.path!r}")
            if delta.path in reserved:
                _fail("protocol event cannot self-report route reconciliation")
            leaf = registry.by_path[delta.path]
            if leaf.reducer is ReducerEnum.SUM:
                values[delta.path] += delta.value
            else:
                values[delta.path] = max(values[delta.path], delta.value)

    receipt = access.read_receipt
    values["common.integrity_checks"] += 1
    values["common.protocol_checks"] += 1
    values["common.hash_invocations"] += 1
    values["io.read_bytes"] += receipt.observed_byte_count
    # ``integrity.bytes_hashed`` is one of the seven optional diagnostic V6
    # leaves.  The bytes themselves are charged exactly once through
    # ``io.read_bytes`` and the hash operation through
    # ``common.hash_invocations``; inserting the diagnostic volume into the
    # required 202-record WorkVector would both violate the registry and
    # double count it.  The read receipt retains the diagnostic byte volume.
    values["route.attempts"] = 1
    values["route.successes"] = 0
    values["route.failures"] = 1

    launches = values["process.launches"]
    successes = values["process.exit_successes"]
    failures = values["process.exit_failures"]
    if successes + failures > launches:
        _fail("protocol prefix reports more process exits than launches")
    values["process.exit_failures"] += launches - successes - failures

    solver_attempts = values["solver.attempts"]
    solver_successes = values["solver.successes"]
    solver_failures = values["solver.failures"]
    if solver_successes + solver_failures > solver_attempts:
        _fail("protocol prefix reports more solver outcomes than attempts")
    values["solver.failures"] += solver_attempts - solver_successes - solver_failures

    if values["route.attempts"] != values["route.successes"] + values["route.failures"]:
        _fail("route reconciliation failed")
    if values["solver.attempts"] != values["solver.successes"] + values["solver.failures"]:
        _fail("solver reconciliation failed")
    if values["process.launches"] != values["process.exit_successes"] + values["process.exit_failures"]:
        _fail("process reconciliation failed")
    for path in (
        "epoch.serialized_bytes", "model.serialized_bytes",
        "capability.serialized_bytes",
    ):
        if values.get(path, 0) > values["io.output_bytes"]:
            _fail(f"{path} exceeds accounted output bytes")
    if values.get("branch.evaluations", 0) != 0:
        _fail("generic branch evaluations cannot enter integrity accounting")
    _validate_route_exclusivity(route_kind, values)
    return registry, values


def _record_id_for(
    *,
    context_id: str,
    access_sequence_id: str,
    path: str,
    value: int,
) -> str:
    return _local_id(
        INTEGRITY_PREFIX_RECORDER_V1_DOMAIN,
        {
            "schema": "acfqp.construction_k7_integrity_prefix_recorder.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "access_sequence_id": access_sequence_id,
            "path": path,
            "value": value,
            "observed": True,
            "evidence_kind": (
                "PROFILE_NATIVE_ZERO" if value == 0 else "PREFIX_OR_TERMINAL_EVENT"
            ),
        },
    )


def _materialize_prefix(
    *,
    context: K7IntegrityAttemptContextV1,
    route_kind: RouteKindEnum,
    access: K7IntegrityAccessSequenceV1,
) -> tuple[tuple[CounterRecordV1, ...], WorkVectorV1, ComparisonVectorV1]:
    registry, values = _derive_prefix_values(route_kind=route_kind, access=access)
    records = tuple(
        CounterRecordV1(
            registry.registry_id,
            path,
            values[path],
            True,
            _record_id_for(
                context_id=context.context_id,
                access_sequence_id=access.sequence_id,
                path=path,
                value=values[path],
            ),
            registry.by_path[path].semantics_id,
            registry.by_path[path].owner,
            registry.by_path[path].unit,
            registry.by_path[path].lane,
            registry.by_path[path].scope,
            registry.by_path[path].reducer,
        )
        for path in registry.required_paths
    )
    if (
        len(records) != EXPECTED_COUNTER_RECORD_COUNT
        or tuple(sorted(records, key=lambda row: row.path)) != records
        or any(row.observed is not True for row in records)
    ):
        _fail("integrity prefix did not materialize all observed V6 records")
    work = WorkVectorV1(
        registry.registry_id,
        context.route_attempt_id,
        route_kind,
        records,
    )
    if (
        work.counter_registry_id != registry.registry_id
        or work.subject_id != context.route_attempt_id
        or tuple(row.path for row in work.records) != registry.required_paths
        or len({row.record_id for row in work.records}) != len(work.records)
        or any(
            row.counter_registry_id != registry.registry_id
            or row.observed is not True
            or (
                row.semantics_id,
                row.owner,
                row.unit,
                row.lane,
                row.scope,
                row.reducer,
            )
            != (
                registry.by_path[row.path].semantics_id,
                registry.by_path[row.path].owner,
                registry.by_path[row.path].unit,
                registry.by_path[row.path].lane,
                registry.by_path[row.path].scope,
                registry.by_path[row.path].reducer,
            )
            for row in work.records
        )
    ):
        _fail("last-valid-prefix WorkVector failed exact V6 validation")
    comparison_profile = registry_v6.official_comparison_profile_v6(registry)
    actual_profile = registry_v6.official_actual_projection_profile_v6(
        registry,
        comparison_profile,
    )
    comparison_profile.validate(registry)
    actual_profile.validate(registry, comparison_profile)
    if (
        tuple(row.source_leaf for row in actual_profile.terms)
        != tuple(row.path for row in registry.operational_leaves)
        or len({row.source_leaf for row in actual_profile.terms})
        != len(registry.operational_leaves)
    ):
        _fail("V6 operational projection coverage changed")
    axes = {axis: 0 for axis in SHARED_AXES}
    for term in actual_profile.terms:
        contribution = values[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axes[term.target_axis] += contribution
        else:
            axes[term.target_axis] = max(axes[term.target_axis], contribution)
    comparison = ComparisonVectorV1(
        comparison_profile.comparison_profile_id,
        work.work_vector_id,
        context.route_attempt_id,
        route_kind,
        tuple(sorted(axes.items())),
    )
    return records, work, comparison


@dataclass(frozen=True, slots=True)
class K7IntegrityPrefixCompletenessV1:
    _issuer: InitVar[object]
    context_id: str
    access_sequence_id: str
    counter_registry_id: str
    work_vector_id: str
    comparison_vector_id: str
    counter_record_ids: tuple[str, ...]
    native_zero_paths: tuple[str, ...]
    native_zero_recorder_ids: tuple[str, ...]
    nonzero_paths: tuple[str, ...]
    prior_prefix_event_count: int
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _COMPLETENESS_ISSUER:
            _fail("integrity prefix completeness is caller-minted")
        for value, label in (
            (self.context_id, "completeness context"),
            (self.access_sequence_id, "access sequence"),
            (self.counter_registry_id, "counter registry"),
            (self.work_vector_id, "work vector"),
            (self.comparison_vector_id, "comparison vector"),
            *((value, "counter record") for value in self.counter_record_ids),
            *((value, "native-zero recorder") for value in self.native_zero_recorder_ids),
        ):
            _cid(value, label)
        _nonnegative(self.prior_prefix_event_count, "prior prefix event count")
        if (
            type(self.counter_record_ids) is not tuple
            or len(self.counter_record_ids) != EXPECTED_COUNTER_RECORD_COUNT
            or len(set(self.counter_record_ids)) != len(self.counter_record_ids)
            or tuple(sorted(self.native_zero_paths)) != self.native_zero_paths
            or tuple(sorted(self.nonzero_paths)) != self.nonzero_paths
            or set(self.native_zero_paths) & set(self.nonzero_paths)
            or len(self.native_zero_paths) + len(self.nonzero_paths)
            != EXPECTED_COUNTER_RECORD_COUNT
            or len(self.native_zero_paths) != len(self.native_zero_recorder_ids)
        ):
            _fail("integrity prefix completeness partition changed")
        object.__setattr__(
            self, "_attestation_id",
            _local_id(INTEGRITY_PREFIX_COMPLETENESS_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_integrity_prefix_completeness.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "access_sequence_id": self.access_sequence_id,
            "counter_registry_id": self.counter_registry_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "counter_record_ids": list(self.counter_record_ids),
            "native_zero_paths": list(self.native_zero_paths),
            "native_zero_recorder_ids": list(self.native_zero_recorder_ids),
            "nonzero_paths": list(self.nonzero_paths),
            "prior_prefix_event_count": self.prior_prefix_event_count,
            "required_record_count": EXPECTED_COUNTER_RECORD_COUNT,
            "all_required_records_observed": True,
            "missing_inferred_as_zero": False,
        }

    @property
    def attestation_id(self) -> str:
        if _local_id(INTEGRITY_PREFIX_COMPLETENESS_V1_DOMAIN, self._payload()) != self._attestation_id:
            _fail("integrity prefix completeness changed after issuance")
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "integrity_prefix_completeness_id": self.attestation_id}

    @classmethod
    def _from_document(cls, document: Any) -> "K7IntegrityPrefixCompletenessV1":
        row = _fields(
            document,
            {
                "schema", "schema_version", "context_id", "access_sequence_id",
                "counter_registry_id", "work_vector_id", "comparison_vector_id",
                "counter_record_ids", "native_zero_paths",
                "native_zero_recorder_ids", "nonzero_paths",
                "prior_prefix_event_count", "required_record_count",
                "all_required_records_observed", "missing_inferred_as_zero",
                "integrity_prefix_completeness_id",
            },
            "integrity prefix completeness",
        )
        if (
            row["schema"] != "acfqp.construction_k7_integrity_prefix_completeness.v1"
            or row["schema_version"] != SCHEMA_VERSION
            or row["required_record_count"] != EXPECTED_COUNTER_RECORD_COUNT
            or row["all_required_records_observed"] is not True
            or row["missing_inferred_as_zero"] is not False
            or any(
                type(row[name]) is not list
                for name in (
                    "counter_record_ids", "native_zero_paths",
                    "native_zero_recorder_ids", "nonzero_paths",
                )
            )
        ):
            _fail("integrity prefix completeness locks changed")
        result = cls(
            _COMPLETENESS_ISSUER,
            row["context_id"], row["access_sequence_id"],
            row["counter_registry_id"], row["work_vector_id"],
            row["comparison_vector_id"], tuple(row["counter_record_ids"]),
            tuple(row["native_zero_paths"]),
            tuple(row["native_zero_recorder_ids"]),
            tuple(row["nonzero_paths"]), row["prior_prefix_event_count"],
        )
        if row["integrity_prefix_completeness_id"] != result.attestation_id:
            _fail("integrity prefix completeness identity changed")
        return result


def _make_completeness(
    *,
    context: K7IntegrityAttemptContextV1,
    access: K7IntegrityAccessSequenceV1,
    records: tuple[CounterRecordV1, ...],
    work: WorkVectorV1,
    comparison: ComparisonVectorV1,
) -> K7IntegrityPrefixCompletenessV1:
    zero = tuple(row for row in records if row.value == 0)
    nonzero = tuple(row for row in records if row.value != 0)
    return K7IntegrityPrefixCompletenessV1(
        _COMPLETENESS_ISSUER,
        context.context_id,
        access.sequence_id,
        work.counter_registry_id,
        work.work_vector_id,
        comparison.comparison_vector_id,
        tuple(row.record_id for row in records),
        tuple(row.path for row in zero),
        tuple(row.recorder_id for row in zero),
        tuple(row.path for row in nonzero),
        len(access.prefix_events),
    )


@dataclass(frozen=True, slots=True)
class K7IntegrityFailureTerminalAuthorityV1:
    _issuer: InitVar[object]
    context: K7IntegrityAttemptContextV1
    route_kind: RouteKindEnum
    cutoff: IntegrityFailureCutoffV1
    expected_identity_id: str
    read_receipt_id: str
    access_sequence_id: str
    prefix_completeness_id: str
    work_vector_id: str
    comparison_vector_id: str
    counter_record_ids: tuple[str, ...]
    violation_reasons: tuple[IntegrityViolationReasonV1, ...]
    _terminal_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TERMINAL_ISSUER or type(self.context) is not K7IntegrityAttemptContextV1:
            _fail("integrity-failure terminal authority is caller-minted")
        try:
            object.__setattr__(self, "route_kind", RouteKindEnum(self.route_kind))
            object.__setattr__(self, "cutoff", IntegrityFailureCutoffV1(self.cutoff))
            reasons = tuple(IntegrityViolationReasonV1(item) for item in self.violation_reasons)
        except (TypeError, ValueError) as error:
            raise ConstructionK7IntegrityFailureAuthorityV1Error(
                "integrity terminal enum changed"
            ) from error
        object.__setattr__(self, "violation_reasons", reasons)
        for value, label in (
            (self.expected_identity_id, "expected identity"),
            (self.read_receipt_id, "read receipt"),
            (self.access_sequence_id, "access sequence"),
            (self.prefix_completeness_id, "prefix completeness"),
            (self.work_vector_id, "work vector"),
            (self.comparison_vector_id, "comparison vector"),
            *((value, "counter record") for value in self.counter_record_ids),
        ):
            _cid(value, label)
        if (
            len(self.counter_record_ids) != EXPECTED_COUNTER_RECORD_COUNT
            or len(set(self.counter_record_ids)) != len(self.counter_record_ids)
            or not reasons
            or len(set(reasons)) != len(reasons)
        ):
            _fail("integrity terminal evidence cardinality changed")
        object.__setattr__(
            self, "_terminal_id",
            _local_id(INTEGRITY_TERMINAL_AUTHORITY_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_integrity_failure_terminal_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context.context_id,
            "structural_id": self.context.structural_id,
            "query_id": self.context.query_id,
            "selected_plan_id": self.context.selected_plan_id,
            "threshold_profile_id": self.context.threshold_profile_id,
            "build_epoch_id": self.context.build_epoch_id,
            "logical_occurrence_id": self.context.logical_occurrence_id,
            "route_attempt_id": self.context.route_attempt_id,
            "decision_point_id": self.context.decision_point_id,
            "transaction_id": self.context.transaction_id,
            "route_kind": self.route_kind.value,
            "cutoff": self.cutoff.value,
            "expected_identity_id": self.expected_identity_id,
            "read_receipt_id": self.read_receipt_id,
            "access_sequence_id": self.access_sequence_id,
            "prefix_completeness_id": self.prefix_completeness_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "counter_record_ids": list(self.counter_record_ids),
            "violation_reasons": [row.value for row in self.violation_reasons],
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "specific_cause": SPECIFIC_CAUSE,
            "protocol_failure": False,
            "terminal_is_infeasibility_certificate": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "logical_occurrence_closed": False,
            "official_execution_allowed": False,
        }

    @property
    def terminal_id(self) -> str:
        if _local_id(INTEGRITY_TERMINAL_AUTHORITY_V1_DOMAIN, self._payload()) != self._terminal_id:
            _fail("integrity terminal changed after issuance")
        return self._terminal_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "integrity_failure_terminal_authority_id": self.terminal_id}

    @classmethod
    def _from_document(
        cls,
        document: Any,
        context: K7IntegrityAttemptContextV1,
    ) -> "K7IntegrityFailureTerminalAuthorityV1":
        expected_fields = set(cls(
            _TERMINAL_ISSUER,
            context,
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            IntegrityFailureCutoffV1.EARLY_INPUT_READ,
            "0" * 64, "1" * 64, "2" * 64, "3" * 64, "4" * 64,
            "5" * 64,
            tuple(hashlib.sha256(f"r-{index}".encode()).hexdigest() for index in range(EXPECTED_COUNTER_RECORD_COUNT)),
            (IntegrityViolationReasonV1.SHA256_MISMATCH,),
        ).to_document())
        row = _fields(document, expected_fields, "integrity terminal authority")
        locks = {
            "schema": "acfqp.construction_k7_integrity_failure_terminal_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": context.context_id,
            "structural_id": context.structural_id,
            "query_id": context.query_id,
            "selected_plan_id": context.selected_plan_id,
            "threshold_profile_id": context.threshold_profile_id,
            "build_epoch_id": context.build_epoch_id,
            "logical_occurrence_id": context.logical_occurrence_id,
            "route_attempt_id": context.route_attempt_id,
            "decision_point_id": context.decision_point_id,
            "transaction_id": context.transaction_id,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "specific_cause": SPECIFIC_CAUSE,
            "protocol_failure": False,
            "terminal_is_infeasibility_certificate": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "logical_occurrence_closed": False,
            "official_execution_allowed": False,
        }
        if any(row.get(key) != value for key, value in locks.items()):
            _fail("integrity terminal class, identity, or lock changed")
        if type(row["counter_record_ids"]) is not list or type(row["violation_reasons"]) is not list:
            _fail("integrity terminal list fields changed")
        result = cls(
            _TERMINAL_ISSUER,
            context, row["route_kind"], row["cutoff"],
            row["expected_identity_id"], row["read_receipt_id"],
            row["access_sequence_id"], row["prefix_completeness_id"],
            row["work_vector_id"], row["comparison_vector_id"],
            tuple(row["counter_record_ids"]), tuple(row["violation_reasons"]),
        )
        if row["integrity_failure_terminal_authority_id"] != result.terminal_id:
            _fail("integrity terminal identity changed")
        return result


@dataclass(frozen=True, slots=True)
class K7IntegrityFailureBundleV1:
    _issuer: InitVar[object]
    context: K7IntegrityAttemptContextV1
    expected_identity: K7ExpectedArtifactIdentityV1
    offending_bytes: bytes
    read_receipt: K7IntegrityReadReceiptV1
    access_sequence: K7IntegrityAccessSequenceV1
    records: tuple[CounterRecordV1, ...]
    work_vector: WorkVectorV1
    comparison_vector: ComparisonVectorV1
    prefix_completeness: K7IntegrityPrefixCompletenessV1
    terminal_authority: K7IntegrityFailureTerminalAuthorityV1
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BUNDLE_ISSUER
            or type(self.context) is not K7IntegrityAttemptContextV1
            or type(self.expected_identity) is not K7ExpectedArtifactIdentityV1
            or type(self.offending_bytes) is not bytes
            or type(self.read_receipt) is not K7IntegrityReadReceiptV1
            or type(self.access_sequence) is not K7IntegrityAccessSequenceV1
            or type(self.work_vector) is not WorkVectorV1
            or type(self.comparison_vector) is not ComparisonVectorV1
            or type(self.prefix_completeness) is not K7IntegrityPrefixCompletenessV1
            or type(self.terminal_authority) is not K7IntegrityFailureTerminalAuthorityV1
        ):
            _fail("integrity-failure bundle is caller-minted")
        if (
            len(self.records) != EXPECTED_COUNTER_RECORD_COUNT
            or tuple(row.record_id for row in self.records)
            != tuple(row.record_id for row in self.work_vector.records)
            or self.context.context_id != self.access_sequence.context_id
            or self.expected_identity.identity_id != self.read_receipt.expected_identity_id
            or self.read_receipt.receipt_id != self.access_sequence.read_receipt.receipt_id
            or self.work_vector.work_vector_id != self.prefix_completeness.work_vector_id
            or self.comparison_vector.comparison_vector_id
            != self.prefix_completeness.comparison_vector_id
            or self.terminal_authority.work_vector_id != self.work_vector.work_vector_id
            or self.terminal_authority.comparison_vector_id
            != self.comparison_vector.comparison_vector_id
            or self.terminal_authority.prefix_completeness_id
            != self.prefix_completeness.attestation_id
        ):
            _fail("integrity-failure bundle identity graph changed")
        object.__setattr__(
            self, "_bundle_id",
            _local_id(INTEGRITY_FAILURE_BUNDLE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_integrity_failure_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "integrity_attempt_context": self.context.to_document(),
            "expected_artifact_identity": self.expected_identity.to_document(),
            "offending_bytes_hex": self.offending_bytes.hex(),
            "integrity_read_receipt": self.read_receipt.to_document(),
            "integrity_access_sequence": self.access_sequence.to_document(),
            "counter_record_ids": [row.record_id for row in self.records],
            "counter_records": [row.to_dict() for row in self.records],
            "last_valid_prefix_work_vector": self.work_vector.to_dict(),
            "last_valid_prefix_comparison_vector": self.comparison_vector.to_dict(),
            "integrity_prefix_completeness": self.prefix_completeness.to_document(),
            "integrity_failure_terminal_authority": self.terminal_authority.to_document(),
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "specific_cause": SPECIFIC_CAUSE,
            "protocol_failure": False,
            "terminal_is_infeasibility_certificate": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "logical_occurrence_closed": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def bundle_id(self) -> str:
        if _local_id(INTEGRITY_FAILURE_BUNDLE_V1_DOMAIN, self._payload()) != self._bundle_id:
            _fail("integrity-failure bundle changed after issuance")
        return self._bundle_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "integrity_failure_bundle_id": self.bundle_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def issue_k7_integrity_failure_bundle_v1(
    *,
    context: K7IntegrityAttemptContextV1,
    route_kind: RouteKindEnum,
    cutoff: IntegrityFailureCutoffV1,
    prefix_events: tuple[K7IntegrityAccessEventV1, ...],
    expected_identity: K7ExpectedArtifactIdentityV1,
    offending_bytes: bytes,
) -> K7IntegrityFailureBundleV1:
    """Issue one fully accounted integrity terminal from exact read bytes."""

    if type(context) is not K7IntegrityAttemptContextV1:
        _fail("integrity failure requires one exact attempt context")
    if type(expected_identity) is not K7ExpectedArtifactIdentityV1:
        _fail("integrity failure requires one frozen expected identity")
    try:
        route = RouteKindEnum(route_kind)
        selected_cutoff = IntegrityFailureCutoffV1(cutoff)
    except (TypeError, ValueError) as error:
        raise ConstructionK7IntegrityFailureAuthorityV1Error(
            "integrity-failure route or cutoff is invalid"
        ) from error
    if type(prefix_events) is not tuple:
        _fail("prefix events must be one exact tuple")
    receipt = _make_read_receipt(
        context=context,
        cutoff=selected_cutoff,
        sequence_number=len(prefix_events) + 1,
        expected=expected_identity,
        offending_bytes=offending_bytes,
    )
    access = K7IntegrityAccessSequenceV1(
        _ACCESS_SEQUENCE_ISSUER,
        context.context_id,
        selected_cutoff,
        prefix_events,
        receipt,
        len(prefix_events) + 2,
    )
    records, work, comparison = _materialize_prefix(
        context=context,
        route_kind=route,
        access=access,
    )
    completeness = _make_completeness(
        context=context,
        access=access,
        records=records,
        work=work,
        comparison=comparison,
    )
    terminal = K7IntegrityFailureTerminalAuthorityV1(
        _TERMINAL_ISSUER,
        context,
        route,
        selected_cutoff,
        expected_identity.identity_id,
        receipt.receipt_id,
        access.sequence_id,
        completeness.attestation_id,
        work.work_vector_id,
        comparison.comparison_vector_id,
        tuple(row.record_id for row in records),
        receipt.violation_reasons,
    )
    return K7IntegrityFailureBundleV1(
        _BUNDLE_ISSUER,
        context,
        expected_identity,
        offending_bytes,
        receipt,
        access,
        records,
        work,
        comparison,
        completeness,
        terminal,
    )


@dataclass(frozen=True, slots=True)
class K7IntegrityFailureVerificationV1:
    _issuer: InitVar[object]
    bundle_id: str
    bundle_sha256: str
    bundle_byte_count: int
    expected_identity_id: str
    context_id: str
    read_receipt_id: str
    access_sequence_id: str
    prefix_completeness_id: str
    work_vector_id: str
    comparison_vector_id: str
    terminal_authority_id: str
    cutoff: IntegrityFailureCutoffV1
    violation_reasons: tuple[IntegrityViolationReasonV1, ...]
    verified_work_vector: WorkVectorV1
    verified_comparison_vector: ComparisonVectorV1
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.verified_work_vector) is not WorkVectorV1
            or type(self.verified_comparison_vector) is not ComparisonVectorV1
        ):
            _fail("integrity-failure verification is caller-minted")
        for value, label in (
            (self.bundle_id, "integrity bundle"),
            (self.expected_identity_id, "expected identity"),
            (self.context_id, "attempt context"),
            (self.read_receipt_id, "read receipt"),
            (self.access_sequence_id, "access sequence"),
            (self.prefix_completeness_id, "prefix completeness"),
            (self.work_vector_id, "work vector"),
            (self.comparison_vector_id, "comparison vector"),
            (self.terminal_authority_id, "terminal authority"),
        ):
            _cid(value, label)
        _sha256(self.bundle_sha256, "bundle digest")
        _positive(self.bundle_byte_count, "bundle byte count")
        try:
            object.__setattr__(self, "cutoff", IntegrityFailureCutoffV1(self.cutoff))
            reasons = tuple(IntegrityViolationReasonV1(item) for item in self.violation_reasons)
        except (TypeError, ValueError) as error:
            raise ConstructionK7IntegrityFailureAuthorityV1Error(
                "verification enum changed"
            ) from error
        object.__setattr__(self, "violation_reasons", reasons)
        if (
            not reasons
            or self.verified_work_vector.work_vector_id != self.work_vector_id
            or self.verified_comparison_vector.comparison_vector_id
            != self.comparison_vector_id
        ):
            _fail("verification work or reason binding changed")
        object.__setattr__(
            self, "_verification_id",
            _local_id(INTEGRITY_FAILURE_VERIFICATION_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_integrity_failure_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "bundle_id": self.bundle_id,
            "bundle_sha256": self.bundle_sha256,
            "bundle_byte_count": self.bundle_byte_count,
            "expected_identity_id": self.expected_identity_id,
            "context_id": self.context_id,
            "read_receipt_id": self.read_receipt_id,
            "access_sequence_id": self.access_sequence_id,
            "prefix_completeness_id": self.prefix_completeness_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "terminal_authority_id": self.terminal_authority_id,
            "cutoff": self.cutoff.value,
            "violation_reasons": [row.value for row in self.violation_reasons],
            "counter_record_count": EXPECTED_COUNTER_RECORD_COUNT,
            "comparison_axis_count": EXPECTED_COMPARISON_AXIS_COUNT,
            "offending_bytes_rehashed": True,
            "identity_violation_independently_recomputed": True,
            "access_sequence_independently_recomputed": True,
            "complete_prefix_work_independently_recomputed": True,
            "producer_invoked": False,
            "verification_lane": "evaluation",
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        if _local_id(INTEGRITY_FAILURE_VERIFICATION_V1_DOMAIN, self._payload()) != self._verification_id:
            _fail("integrity-failure verification changed after issuance")
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "integrity_failure_verification_id": self.verification_id}


_BUNDLE_FIELDS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "integrity_attempt_context", "expected_artifact_identity",
    "offending_bytes_hex", "integrity_read_receipt",
    "integrity_access_sequence", "counter_record_ids", "counter_records",
    "last_valid_prefix_work_vector", "last_valid_prefix_comparison_vector",
    "integrity_prefix_completeness", "integrity_failure_terminal_authority",
    "terminal_scope", "terminal_class", "terminal_code", "specific_cause",
    "protocol_failure", "terminal_is_infeasibility_certificate",
    "plan_certificate", "infeasibility_certificate", "logical_occurrence_closed",
    "official_execution_allowed", "counter_completeness_gate_status",
    "workload_economics_gate_status", "official_scalar_cost",
    "official_N_break_even", "integrity_failure_bundle_id",
}


def verify_k7_integrity_failure_bundle_bytes_v1(
    *,
    raw: bytes,
    expected_identity_id: str,
    expected_context_id: str,
) -> K7IntegrityFailureVerificationV1:
    """Independently replay one integrity terminal from portable bytes."""

    anchored_identity_id = _cid(expected_identity_id, "anchored expected identity")
    anchored_context_id = _cid(expected_context_id, "anchored attempt context")
    document = _fields(_canonical_object(raw, "integrity-failure bundle"), _BUNDLE_FIELDS, "integrity-failure bundle")
    locks = {
        "schema": "acfqp.construction_k7_integrity_failure_bundle.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": TERMINAL_CODE,
        "specific_cause": SPECIFIC_CAUSE,
        "protocol_failure": False,
        "terminal_is_infeasibility_certificate": False,
        "plan_certificate": False,
        "infeasibility_certificate": False,
        "logical_occurrence_closed": False,
        "official_execution_allowed": False,
        "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
        "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        "official_scalar_cost": None,
        "official_N_break_even": None,
    }
    if any(document.get(key) != value for key, value in locks.items()):
        _fail("integrity-failure terminal relabel or Gate unlock detected")
    payload = dict(document)
    claimed_bundle_id = payload.pop("integrity_failure_bundle_id")
    replayed_bundle_id = _local_id(INTEGRITY_FAILURE_BUNDLE_V1_DOMAIN, payload)
    if claimed_bundle_id != replayed_bundle_id:
        _fail("integrity-failure bundle content ID changed")

    context = K7IntegrityAttemptContextV1.from_document(document["integrity_attempt_context"])
    expected = K7ExpectedArtifactIdentityV1._from_document(document["expected_artifact_identity"])
    if context.context_id != anchored_context_id or expected.identity_id != anchored_identity_id:
        _fail("integrity-failure bundle was transplanted away from an external anchor")
    offending_hex = document["offending_bytes_hex"]
    if type(offending_hex) is not str or len(offending_hex) % 2:
        _fail("offending artifact hex is invalid")
    try:
        offending_bytes = bytes.fromhex(offending_hex)
    except ValueError as error:
        raise ConstructionK7IntegrityFailureAuthorityV1Error(
            "offending artifact hex is invalid"
        ) from error
    if offending_bytes.hex() != offending_hex:
        _fail("offending artifact hex is noncanonical")

    receipt_document = document["integrity_read_receipt"]
    receipt_claim = K7IntegrityReadReceiptV1._from_document(receipt_document)
    recomputed_receipt = _make_read_receipt(
        context=context,
        cutoff=receipt_claim.cutoff,
        sequence_number=receipt_claim.access_sequence_number,
        expected=expected,
        offending_bytes=offending_bytes,
    )
    if recomputed_receipt.to_document() != receipt_claim.to_document():
        _fail("offending bytes do not match the independently recomputed read receipt")
    access = K7IntegrityAccessSequenceV1._from_document(
        document["integrity_access_sequence"],
        recomputed_receipt,
    )
    records, work, comparison = _materialize_prefix(
        context=context,
        route_kind=RouteKindEnum(document["last_valid_prefix_work_vector"]["route_kind"]),
        access=access,
    )
    claimed_record_documents = document["counter_records"]
    claimed_record_ids = document["counter_record_ids"]
    if (
        type(claimed_record_documents) is not list
        or type(claimed_record_ids) is not list
        or claimed_record_documents != [row.to_dict() for row in records]
        or claimed_record_ids != [row.record_id for row in records]
    ):
        _fail("last-valid-prefix CounterRecords are incomplete or changed")
    if document["last_valid_prefix_work_vector"] != work.to_dict():
        _fail("last-valid-prefix WorkVector differs from independent replay")
    if document["last_valid_prefix_comparison_vector"] != comparison.to_dict():
        _fail("last-valid-prefix ComparisonVector differs from independent replay")
    completeness = _make_completeness(
        context=context,
        access=access,
        records=records,
        work=work,
        comparison=comparison,
    )
    claimed_completeness = K7IntegrityPrefixCompletenessV1._from_document(
        document["integrity_prefix_completeness"]
    )
    if claimed_completeness.to_document() != completeness.to_document():
        _fail("prefix completeness or native-zero partition differs from replay")
    terminal = K7IntegrityFailureTerminalAuthorityV1._from_document(
        document["integrity_failure_terminal_authority"],
        context,
    )
    expected_terminal = K7IntegrityFailureTerminalAuthorityV1(
        _TERMINAL_ISSUER,
        context,
        work.route_kind,
        access.cutoff,
        expected.identity_id,
        recomputed_receipt.receipt_id,
        access.sequence_id,
        completeness.attestation_id,
        work.work_vector_id,
        comparison.comparison_vector_id,
        tuple(row.record_id for row in records),
        recomputed_receipt.violation_reasons,
    )
    if terminal.to_document() != expected_terminal.to_document():
        _fail("integrity terminal differs from independent semantic replay")
    return K7IntegrityFailureVerificationV1(
        _VERIFICATION_ISSUER,
        replayed_bundle_id,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
        expected.identity_id,
        context.context_id,
        recomputed_receipt.receipt_id,
        access.sequence_id,
        completeness.attestation_id,
        work.work_vector_id,
        comparison.comparison_vector_id,
        terminal.terminal_id,
        access.cutoff,
        recomputed_receipt.violation_reasons,
        work,
        comparison,
    )


__all__ = [
    "ConstructionK7IntegrityFailureAuthorityV1Error",
    "IntegrityFailureCutoffV1",
    "IntegrityViolationReasonV1",
    "K7ExpectedArtifactIdentityV1",
    "K7IntegrityAccessEventV1",
    "K7IntegrityAttemptContextV1",
    "K7IntegrityCounterDeltaV1",
    "K7IntegrityFailureBundleV1",
    "K7IntegrityFailureTerminalAuthorityV1",
    "K7IntegrityFailureVerificationV1",
    "PROPOSED_CONTRACT_VERSION",
    "freeze_k7_expected_artifact_identity_v1",
    "issue_k7_integrity_failure_bundle_v1",
    "verify_k7_integrity_failure_bundle_bytes_v1",
]
