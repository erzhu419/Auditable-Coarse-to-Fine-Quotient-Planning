"""Durable construction-settlement core for the nine H1 shared resources.

This construction-only V3 core separates a caller-asserted native/source value
from the value charged to the accounting reducer.  It does not claim that the
assertion has been verified by a native authority.  Every reservation is
durably appended before the caller may attempt a side effect; lifecycle cells,
evidence, settlements, receipt/event pairs, and snapshots form one fsynced
previous-head journal.  Reopening the directory is the only supported recovery
mechanism, so Python object identity is never a spend authority.

The identity graph is deliberately acyclic::

    ProfileCore (lifecycle + occurrence + caps)
        -> attempt-wide rejection gate
        -> RuntimeBinding (ProfileCore + gate)

The gate's compatibility field ``shared_owner_profile_core_id`` therefore denotes
the ProfileCore ID.  This module does not activate production execution, bind
real syscalls, issue formal CounterRecords, or claim that conservative charges
are exact observations.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import InitVar, dataclass, field
from enum import Enum
import fcntl
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_NATIVE_CELL_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_NATIVE_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RECEIPT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RESERVATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RUNTIME_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SETTLEMENT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SNAPSHOT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SOURCE_MANIFEST_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-B"
PROFILE_KEY = "construction_k7_h1_shared_cap_owner_v3"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_EXECUTION_AUTHORIZED = False
FORMAL_ACTUAL_COMPLIANCE_ELIGIBLE = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False

PROFILE_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_PROFILE_V1_DOMAIN
SOURCE_DOMAIN = (
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SOURCE_MANIFEST_V1_DOMAIN
)
RUNTIME_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RUNTIME_V1_DOMAIN
RESERVATION_DOMAIN = (
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RESERVATION_V1_DOMAIN
)
NATIVE_CELL_DOMAIN = (
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_NATIVE_CELL_V1_DOMAIN
)
NATIVE_EVIDENCE_DOMAIN = (
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_NATIVE_EVIDENCE_V1_DOMAIN
)
SETTLEMENT_DOMAIN = (
    CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SETTLEMENT_V1_DOMAIN
)
RECEIPT_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RECEIPT_V1_DOMAIN
EVENT_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_EVENT_V1_DOMAIN
SNAPSHOT_DOMAIN = CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SNAPSHOT_V1_DOMAIN

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    PROFILE_DOMAIN,
    SOURCE_DOMAIN,
    RUNTIME_DOMAIN,
    RESERVATION_DOMAIN,
    NATIVE_CELL_DOMAIN,
    NATIVE_EVIDENCE_DOMAIN,
    SETTLEMENT_DOMAIN,
    RECEIPT_DOMAIN,
    EVENT_DOMAIN,
    SNAPSHOT_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS))
    != len(REQUESTED_PHASE3E_DOMAIN_TAGS)
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover - central registry invariant
    raise RuntimeError("H1 shared-cap owner V3 domains are not registered")


SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)
PATH_REDUCERS = {
    "common.hash_invocations": "SUM",
    "common.integrity_checks": "SUM",
    "common.protocol_checks": "SUM",
    "io.mounted_bytes_peak": "MAX",
    "io.output_bytes": "SUM",
    "io.read_bytes": "SUM",
    "io.staged_bytes": "SUM",
    "memory.working_bytes_peak": "MAX",
    "process.launches": "SUM",
}
_UNIT_EVENT_PATHS = frozenset(
    {
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "process.launches",
    }
)
_MAGNITUDE_PATHS = frozenset(SHARED_RESOURCE_PATHS) - _UNIT_EVENT_PATHS

_PROFILE_FILE = "profile-core.json"
_SOURCE_FILE = "source-manifest.json"
_RUNTIME_FILE = "runtime-binding.json"
_OWNER_ROOT_DIRECTORY = ".acfqp-h1-shared-cap-owner-v3"
_STATIC_FILES = frozenset({_PROFILE_FILE, _SOURCE_FILE, _RUNTIME_FILE})
_RECORD_PATTERN = re.compile(r"([0-9]{8})-([0-9a-f]{64})[.]json\Z")
_TEMP_PATTERN = re.compile(r"[.]tmp-[1-9][0-9]*-[0-9a-f]{32}\Z")
_MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
_CURSOR_TOKEN_PREFIX = ".acfqp-h1-owner-cursor-token-"
_CURSOR_STATE_PREFIX = ".acfqp-h1-owner-cursor-state-"
_GENESIS_HEAD = "GENESIS"
_ACTIVE_SIDE_EFFECT_GUARDS: ContextVar[frozenset[tuple[str, str]]] = ContextVar(
    "acfqp_h1_shared_cap_owner_v3_active_side_effect_guards",
    default=frozenset(),
)


class ConstructionK7H1SharedCapOwnerV3Error(ValueError):
    """The profile, journal, settlement, or reducer failed closed."""


class H1SharedCapOwnerV3Rejected(ConstructionK7H1SharedCapOwnerV3Error):
    """The attempt-wide cap gate has durably rejected the operation."""

    failure_kind = "SHARED_CAP_EXHAUSTED"
    certificate_issued = False
    infeasibility_certified = False

    def __init__(
        self,
        message: str,
        result: "H1SharedCapRejectionResultV3 | None" = None,
    ) -> None:
        super().__init__(message)
        self.result = result


class H1SharedCapOwnerV3ProtocolFailure(
    ConstructionK7H1SharedCapOwnerV3Error
):
    """A spend, chain, or evidence invariant failed."""

    failure_kind = "PROTOCOL_FAILURE"
    certificate_issued = False
    infeasibility_certified = False


class H1SharedCapOwnerV3InjectedCrash(RuntimeError):
    """Test-only interruption after one durable owner transition."""


class H1SharedCapOwnerV3ObservedOverrun(H1SharedCapOwnerV3ProtocolFailure):
    """The exact native observation was preserved above its reservation."""

    def __init__(self, message: str, result: "H1SharedSettlementResultV3") -> None:
        super().__init__(message)
        self.result = result


class H1SharedReducerV3(str, Enum):
    SUM = "SUM"
    MAX = "MAX"


class H1SharedValueBasisV3(str, Enum):
    EXACT_NATIVE = "CONSTRUCTION_ASSERTED_NATIVE_VALUE"
    EXACT_SOURCE_EVENT = "CONSTRUCTION_ASSERTED_SOURCE_EVENT"
    KNOWN_NOT_STARTED_ZERO = "KNOWN_NOT_STARTED_ZERO"
    CONSERVATIVE_RESERVATION_UPPER = "CONSERVATIVE_RESERVATION_UPPER"
    OBSERVED_OVERRUN = "OBSERVED_OVERRUN"


class H1SharedNativeStateV3(str, Enum):
    OBSERVED = "OBSERVED"
    KNOWN_NOT_STARTED = "KNOWN_NOT_STARTED"
    AMBIGUOUS_AT_CUTOFF = "AMBIGUOUS_AT_CUTOFF"
    SIDE_EFFECT_STARTED = "SIDE_EFFECT_STARTED"


class H1SharedGateOwnerJoinStatusV3(str, Enum):
    OPEN_NO_REJECTION = "OPEN_NO_REJECTION"
    LOCAL_COMMIT_AWAITING_ADMISSION = "LOCAL_COMMIT_AWAITING_ADMISSION"
    LOCAL_COMMIT_AWAITING_PAIR = "LOCAL_COMMIT_AWAITING_PAIR"
    LOCAL_PAIR_AWAITING_ACK = "LOCAL_PAIR_AWAITING_ACK"
    LOCAL_ACK_VERIFIED = "LOCAL_ACK_VERIFIED"
    EXTERNAL_ATTEMPT_REJECTION_UNACKNOWLEDGED = (
        "EXTERNAL_ATTEMPT_REJECTION_UNACKNOWLEDGED"
    )
    EXTERNAL_ATTEMPT_REJECTION_ACKNOWLEDGED = (
        "EXTERNAL_ATTEMPT_REJECTION_ACKNOWLEDGED"
    )


class H1SharedOwnerV3CrashPoint(str, Enum):
    NONE = "NONE"
    AFTER_RESERVATION = "AFTER_RESERVATION"
    AFTER_NATIVE_CELL = "AFTER_NATIVE_CELL"
    AFTER_EVIDENCE = "AFTER_EVIDENCE"
    AFTER_SETTLEMENT = "AFTER_SETTLEMENT"
    AFTER_RECEIPT = "AFTER_RECEIPT"
    AFTER_EVENT = "AFTER_EVENT"
    AFTER_SNAPSHOT = "AFTER_SNAPSHOT"
    AFTER_REJECTION_COMMIT = "AFTER_REJECTION_COMMIT"
    AFTER_REJECTION_OWNER_PAIR = "AFTER_REJECTION_OWNER_PAIR"
    AFTER_REJECTION_ACK = "AFTER_REJECTION_ACK"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1SharedCapOwnerV3Error(message)


def _protocol(message: str) -> NoReturn:
    raise H1SharedCapOwnerV3ProtocolFailure(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1SharedCapOwnerV3Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{label} must be one nonempty exact string")
    return value


def _require_value_basis_path(
    basis: H1SharedValueBasisV3,
    path: str,
) -> None:
    """Apply the same path/basis grammar to production and durable replay."""

    if basis is H1SharedValueBasisV3.EXACT_SOURCE_EVENT and path not in _UNIT_EVENT_PATHS:
        _fail("exact source-event basis is invalid for this shared path")
    if basis is H1SharedValueBasisV3.EXACT_NATIVE and path not in _MAGNITUDE_PATHS:
        _fail("exact native magnitude basis is invalid for this shared path")


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _id_payload(
    domain: str, payload: Mapping[str, Any], id_field: str
) -> dict[str, Any]:
    document = dict(payload)
    document[id_field] = content_id(domain, document)
    return document


@dataclass(frozen=True, slots=True)
class H1SharedCapLimitV3:
    path: str
    reducer: H1SharedReducerV3
    hard_cap: int

    def __post_init__(self) -> None:
        if self.path not in SHARED_RESOURCE_PATHS:
            _fail("V3 cap limit names an unknown shared path")
        try:
            object.__setattr__(self, "reducer", H1SharedReducerV3(self.reducer))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1SharedCapOwnerV3Error(
                "V3 cap reducer is invalid"
            ) from error
        if self.reducer.value != PATH_REDUCERS[self.path]:
            _fail("V3 cap reducer differs from the frozen path reducer")
        _nonnegative(self.hard_cap, "V3 shared hard cap")

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "reducer": self.reducer.value,
            "hard_cap": self.hard_cap,
        }


@dataclass(frozen=True, slots=True)
class H1SharedCapProfileCoreV3:
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    transaction_id: str
    caller_pinned_lifecycle_provenance_id: str
    lifecycle_program_snapshot_id: str
    lifecycle_program_id: str
    lifecycle_branch_analysis_id: str
    limits: tuple[H1SharedCapLimitV3, ...]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.decision_point_id, "decision point"),
            (self.transaction_id, "transaction"),
            (
                self.caller_pinned_lifecycle_provenance_id,
                "caller-pinned lifecycle provenance",
            ),
            (self.lifecycle_program_snapshot_id, "lifecycle snapshot"),
            (self.lifecycle_program_id, "lifecycle program"),
            (self.lifecycle_branch_analysis_id, "lifecycle branch analysis"),
        ):
            _cid(value, label)
        if (
            type(self.limits) is not tuple
            or tuple(row.path for row in self.limits) != SHARED_RESOURCE_PATHS
            or any(type(row) is not H1SharedCapLimitV3 for row in self.limits)
        ):
            _fail("V3 profile requires the ordered exact nine cap limits")
        object.__setattr__(
            self, "_profile_id", content_id(PROFILE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_shared_cap_profile_core.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
            "caller_pinned_lifecycle_provenance_id": (
                self.caller_pinned_lifecycle_provenance_id
            ),
            "lifecycle_program_snapshot_id": self.lifecycle_program_snapshot_id,
            "lifecycle_program_id": self.lifecycle_program_id,
            "lifecycle_branch_analysis_id": self.lifecycle_branch_analysis_id,
            "limits": [row.to_document() for row in self.limits],
            "path_order": list(SHARED_RESOURCE_PATHS),
            "gate_binding_deferred_to_runtime_binding": True,
            "identity_graph": "PROFILE_CORE_TO_GATE_TO_RUNTIME_BINDING",
            "profile_contains_gate_id": False,
            "production_activation_chain_verified": False,
            "formal_actual_compliance_eligible": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def profile_id(self) -> str:
        if content_id(PROFILE_DOMAIN, self._payload()) != self._profile_id:
            _fail("V3 profile core changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_shared_cap_profile_core_v3_id": self.profile_id,
        }


def freeze_h1_shared_cap_profile_core_v3(
    *,
    logical_occurrence_id: str,
    route_attempt_id: str,
    decision_point_id: str,
    transaction_id: str,
    caller_pinned_lifecycle_provenance_id: str,
    lifecycle_program_snapshot_id: str,
    lifecycle_program_id: str,
    lifecycle_branch_analysis_id: str,
    hard_caps: Mapping[str, int],
) -> H1SharedCapProfileCoreV3:
    if type(hard_caps) is not dict or set(hard_caps) != set(
        SHARED_RESOURCE_PATHS
    ):
        _fail("V3 hard caps must cover exactly the nine shared paths")
    return H1SharedCapProfileCoreV3(
        logical_occurrence_id,
        route_attempt_id,
        decision_point_id,
        transaction_id,
        caller_pinned_lifecycle_provenance_id,
        lifecycle_program_snapshot_id,
        lifecycle_program_id,
        lifecycle_branch_analysis_id,
        tuple(
            H1SharedCapLimitV3(
                path,
                H1SharedReducerV3(PATH_REDUCERS[path]),
                _nonnegative(hard_caps[path], f"{path} hard cap"),
            )
            for path in SHARED_RESOURCE_PATHS
        ),
    )


@dataclass(frozen=True, slots=True)
class H1SharedCapOwnerV3SourceManifest:
    caller_pinned_lifecycle_provenance_id: str
    lifecycle_program_snapshot_id: str
    lifecycle_program_id: str
    lifecycle_branch_analysis_id: str
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (
                self.caller_pinned_lifecycle_provenance_id,
                "caller-pinned lifecycle provenance",
            ),
            (self.lifecycle_program_snapshot_id, "lifecycle snapshot"),
            (self.lifecycle_program_id, "lifecycle program"),
            (self.lifecycle_branch_analysis_id, "lifecycle analysis"),
        ):
            _cid(value, label)
        object.__setattr__(
            self, "_manifest_id", content_id(SOURCE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_shared_cap_owner_v3_source_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "caller_pinned_lifecycle_provenance_id": (
                self.caller_pinned_lifecycle_provenance_id
            ),
            "lifecycle_program_snapshot_id": self.lifecycle_program_snapshot_id,
            "lifecycle_program_id": self.lifecycle_program_id,
            "lifecycle_branch_analysis_id": self.lifecycle_branch_analysis_id,
            "source_scope": "CALLER_PINNED_LOCAL_CONSTRUCTION_PROVENANCE",
            "real_syscall_adapter_bound": False,
            "production_source_authority_present": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def manifest_id(self) -> str:
        if content_id(SOURCE_DOMAIN, self._payload()) != self._manifest_id:
            _fail("V3 source manifest changed")
        return self._manifest_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_shared_cap_owner_v3_source_manifest_id": self.manifest_id,
        }


def freeze_h1_shared_cap_owner_v3_source_manifest(
    *,
    caller_pinned_lifecycle_provenance_id: str,
    lifecycle_program_snapshot_id: str,
    lifecycle_program_id: str,
    lifecycle_branch_analysis_id: str,
) -> H1SharedCapOwnerV3SourceManifest:
    return H1SharedCapOwnerV3SourceManifest(
        caller_pinned_lifecycle_provenance_id,
        lifecycle_program_snapshot_id,
        lifecycle_program_id,
        lifecycle_branch_analysis_id,
    )


@dataclass(frozen=True, slots=True)
class H1SharedCapOwnerV3Handle:
    owner_directory: str
    gate_directory: str
    runtime_id: str
    profile: H1SharedCapProfileCoreV3
    source_manifest: H1SharedCapOwnerV3SourceManifest
    owner_root_realpath: str
    owner_root_device: int
    owner_root_inode: int
    owner_directory_device: int
    owner_directory_inode: int
    cursor_token_device: int
    cursor_token_inode: int

    def __post_init__(self) -> None:
        if (
            not Path(self.owner_directory).is_absolute()
            or not Path(self.gate_directory).is_absolute()
        ):
            _fail("V3 owner and gate directories must be absolute")
        _cid(self.runtime_id, "V3 runtime")
        if (
            not Path(self.owner_root_realpath).is_absolute()
            or Path(self.owner_directory).parent != Path(self.owner_root_realpath)
        ):
            _fail("V3 owner handle root path is malformed")
        for value, label in (
            (self.owner_root_device, "V3 owner root device"),
            (self.owner_root_inode, "V3 owner root inode"),
            (self.owner_directory_device, "V3 owner directory device"),
            (self.owner_directory_inode, "V3 owner directory inode"),
            (self.cursor_token_device, "V3 cursor token device"),
            (self.cursor_token_inode, "V3 cursor token inode"),
        ):
            _nonnegative(value, label)


@dataclass(frozen=True, slots=True)
class H1SharedReservationV3:
    document: Mapping[str, Any]

    @property
    def reservation_id(self) -> str:
        return _cid(
            self.document["h1_shared_cap_owner_v3_reservation_id"],
            "V3 reservation",
        )

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(dict(self.document))


@dataclass(frozen=True, slots=True)
class H1SharedSideEffectStartV3:
    document: Mapping[str, Any]

    @property
    def native_cell_id(self) -> str:
        return _cid(
            self.document["h1_shared_cap_owner_v3_native_cell_id"],
            "V3 side-effect start",
        )


@dataclass(frozen=True, slots=True)
class _GateOwnerJoinV3:
    status: H1SharedGateOwnerJoinStatusV3
    recovery_required: bool
    local_pair_verified: bool
    external_attempt_rejection: bool


@dataclass(frozen=True, slots=True)
class H1SharedSettlementResultV3:
    reservation: H1SharedReservationV3
    native_cell_document: Mapping[str, Any]
    evidence_document: Mapping[str, Any]
    settlement_document: Mapping[str, Any]
    receipt_document: Mapping[str, Any]
    event_document: Mapping[str, Any]
    snapshot_document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class H1SharedCapRejectionResultV3:
    rejection_commit: rejection_v1.H1AttemptRejectionCommitV1
    receipt_document: Mapping[str, Any]
    event_document: Mapping[str, Any]
    snapshot_document: Mapping[str, Any]
    acknowledgement: rejection_v1.H1AttemptRejectionAckV1


@dataclass(slots=True)
class _ReplayState:
    sequence: int
    head_id: str | None
    charged: dict[str, int]
    outstanding: dict[str, int]
    reservations: dict[str, dict[str, Any]]
    reservation_by_operation: dict[str, str]
    cells: dict[str, dict[str, Any]]
    evidence: dict[str, dict[str, Any]]
    settlements: dict[str, dict[str, Any]]
    rejection_admissions: dict[str, dict[str, Any]]
    rejection_admission_by_operation: dict[str, str]
    receipts: dict[str, dict[str, Any]]
    events: dict[str, dict[str, Any]]
    snapshots: list[dict[str, Any]]
    rejection_commit_id: str | None
    conservative_settlement_count: int
    observed_overrun_count: int
    pending_cursor: tuple[int, str] | None = None


_RECORD_META = {
    "acfqp.k7_h1_shared_cap_reservation.v3": (
        RESERVATION_DOMAIN,
        "h1_shared_cap_owner_v3_reservation_id",
    ),
    "acfqp.k7_h1_shared_cap_native_cell.v3": (
        NATIVE_CELL_DOMAIN,
        "h1_shared_cap_owner_v3_native_cell_id",
    ),
    "acfqp.k7_h1_shared_cap_native_evidence.v3": (
        NATIVE_EVIDENCE_DOMAIN,
        "h1_shared_cap_owner_v3_native_evidence_id",
    ),
    "acfqp.k7_h1_shared_cap_settlement.v3": (
        SETTLEMENT_DOMAIN,
        "h1_shared_cap_owner_v3_settlement_id",
    ),
    "acfqp.k7_h1_shared_cap_receipt.v3": (
        RECEIPT_DOMAIN,
        "h1_shared_cap_owner_v3_receipt_id",
    ),
    "acfqp.k7_h1_shared_cap_event.v3": (
        EVENT_DOMAIN,
        "h1_shared_cap_owner_v3_event_id",
    ),
    "acfqp.k7_h1_shared_cap_snapshot.v3": (
        SNAPSHOT_DOMAIN,
        "h1_shared_cap_owner_v3_snapshot_id",
    ),
}


def _parse_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > _MAX_DOCUMENT_BYTES:
        _fail(f"{label} is absent, mistyped, or over its byte cap")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1SharedCapOwnerV3Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


def _open_private_directory(path: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ConstructionK7H1SharedCapOwnerV3Error(
            "V3 owner directory cannot be opened"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
        os.close(descriptor)
        _fail("V3 owner directory must be private")
    return descriptor


def _open_parent_directory(path: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ConstructionK7H1SharedCapOwnerV3Error(
            "V3 owner parent directory cannot be opened"
        ) from error
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        _fail("V3 owner parent is not a directory")
    return descriptor


def _open_private_directory_at(parent_fd: int, name: str) -> int:
    if type(name) is not str or not name or "/" in name or name in {".", ".."}:
        _fail("V3 relative owner directory name is malformed")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as error:
        raise ConstructionK7H1SharedCapOwnerV3Error(
            "V3 owner directory cannot be opened below its root"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
        os.close(descriptor)
        _fail("V3 owner directory must be private")
    return descriptor


def _resolve_owner_root(
    base_directory: str | Path,
    *,
    create: bool,
) -> tuple[Path, int]:
    outer = Path(base_directory).resolve(strict=True)
    outer_fd = _open_parent_directory(outer)
    try:
        if create:
            try:
                os.mkdir(_OWNER_ROOT_DIRECTORY, mode=0o700, dir_fd=outer_fd)
            except FileExistsError:
                pass
            os.fsync(outer_fd)
        root_fd = _open_private_directory_at(outer_fd, _OWNER_ROOT_DIRECTORY)
    finally:
        os.close(outer_fd)
    return outer / _OWNER_ROOT_DIRECTORY, root_fd


_ALLOCATION_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "h1_shared_cap_owner_v3_runtime_id",
        "owner_root_realpath",
        "owner_root_device",
        "owner_root_inode",
        "owner_directory_device",
        "owner_directory_inode",
        "cursor_token_device",
        "cursor_token_inode",
        "cursor_token_sha256",
        "allocation_state",
        "production_execution_authorized",
    }
)


def _allocation_name(runtime_id: str) -> str:
    return f".acfqp-h1-owner-allocation-{runtime_id}.json"


def _cursor_token_name(runtime_id: str) -> str:
    return f"{_CURSOR_TOKEN_PREFIX}{runtime_id}.bin"


def _cursor_token_bytes(runtime_id: str) -> bytes:
    return (
        b"ACFQP_H1_SHARED_CAP_OWNER_V3_CURSOR_TOKEN\x00"
        + runtime_id.encode("ascii")
        + b"\n"
    )


def _cursor_state_name(
    runtime_id: str,
    state_kind: str,
    sequence: int,
    head_id: str | None,
) -> str:
    if state_kind not in {"C", "P"}:
        _protocol("V3 cursor state kind is invalid")
    _nonnegative(sequence, "V3 cursor sequence")
    encoded_head = _GENESIS_HEAD if head_id is None else _cid(head_id, "V3 cursor head")
    if sequence == 0 and encoded_head != _GENESIS_HEAD:
        _protocol("V3 genesis cursor has a non-genesis head")
    if sequence != 0 and encoded_head == _GENESIS_HEAD:
        _protocol("V3 non-genesis cursor lacks a journal head")
    return (
        f"{_CURSOR_STATE_PREFIX}{runtime_id}-{state_kind}-"
        f"{sequence:08d}-{encoded_head}"
    )


def _allocation_document(
    runtime_id: str,
    root_path: Path,
    root_fd: int,
    owner_fd: int,
    cursor_token_fd: int,
) -> dict[str, Any]:
    root_metadata = os.fstat(root_fd)
    owner_metadata = os.fstat(owner_fd)
    cursor_metadata = os.fstat(cursor_token_fd)
    cursor_raw = os.pread(cursor_token_fd, 4096, 0)
    return {
        "schema": "acfqp.k7_h1_shared_cap_owner_v3_allocation.v1",
        "schema_version": SCHEMA_VERSION,
        "h1_shared_cap_owner_v3_runtime_id": runtime_id,
        "owner_root_realpath": str(root_path),
        "owner_root_device": root_metadata.st_dev,
        "owner_root_inode": root_metadata.st_ino,
        "owner_directory_device": owner_metadata.st_dev,
        "owner_directory_inode": owner_metadata.st_ino,
        "cursor_token_device": cursor_metadata.st_dev,
        "cursor_token_inode": cursor_metadata.st_ino,
        "cursor_token_sha256": hashlib.sha256(cursor_raw).hexdigest(),
        "allocation_state": "PINNED_LOCAL_FILESYSTEM_INODE",
        "production_execution_authorized": False,
    }


def _freeze_or_verify_allocation(
    runtime_id: str,
    root_path: Path,
    root_fd: int,
    owner_fd: int,
    cursor_token_fd: int,
    *,
    allow_create: bool,
) -> dict[str, Any]:
    expected = _allocation_document(
        runtime_id,
        root_path,
        root_fd,
        owner_fd,
        cursor_token_fd,
    )
    raw = canonical_json_bytes(expected)
    name = _allocation_name(runtime_id)
    published = _publish_new(root_fd, name, raw) if allow_create else False
    if not published:
        existing_raw = _read_file(root_fd, name)
        if existing_raw is None:
            _protocol("V3 owner allocation commit is absent")
        existing = _parse_document(existing_raw, "V3 owner allocation")
        if set(existing) != _ALLOCATION_FIELDS or existing != expected:
            _protocol("V3 owner physical allocation was already consumed")
    return expected


def _read_file(directory_fd: int, name: str) -> bytes | None:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ConstructionK7H1SharedCapOwnerV3Error(
            "V3 durable record cannot be opened"
        ) from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            _fail("V3 durable record must be one private regular file")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_DOCUMENT_BYTES:
                _fail("V3 durable record exceeds its byte cap")
            chunks.append(chunk)
        raw = b"".join(chunks)
        if not raw:
            _fail("V3 durable record is empty")
        return raw
    finally:
        os.close(descriptor)


def _write_all(descriptor: int, raw: bytes) -> None:
    remaining = memoryview(raw)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:  # pragma: no cover - OS invariant
            _fail("V3 durable write made no progress")
        remaining = remaining[written:]


def _publish_new(directory_fd: int, name: str, raw: bytes) -> bool:
    if not raw or len(raw) > _MAX_DOCUMENT_BYTES:
        _fail("V3 durable record exceeds its byte cap before publication")
    temporary = f".tmp-{os.getpid()}-{secrets.token_hex(16)}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
    try:
        _write_all(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    published = False
    try:
        try:
            os.link(
                temporary,
                name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
            os.fsync(directory_fd)
            published = True
        except FileExistsError:
            published = False
    finally:
        try:
            os.unlink(temporary, dir_fd=directory_fd)
            os.fsync(directory_fd)
        except FileNotFoundError:  # pragma: no cover
            pass
    return published


def _publish_exact(directory_fd: int, name: str, raw: bytes) -> None:
    if _publish_new(directory_fd, name, raw):
        return
    existing = _read_file(directory_fd, name)
    if existing is None or not hmac.compare_digest(existing, raw):
        _protocol(f"V3 durable record conflicts at {name}")


def _open_cursor_token(root_fd: int, runtime_id: str) -> int:
    name = _cursor_token_name(runtime_id)
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=root_fd)
    except OSError as error:
        raise H1SharedCapOwnerV3ProtocolFailure(
            "V3 owner high-water cursor token is absent"
        ) from error
    try:
        metadata = os.fstat(descriptor)
        raw = os.pread(descriptor, 4096, 0)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or not hmac.compare_digest(raw, _cursor_token_bytes(runtime_id))
        ):
            _protocol("V3 owner high-water cursor token changed")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _link_cursor_state(
    root_fd: int,
    runtime_id: str,
    state_kind: str,
    sequence: int,
    head_id: str | None,
) -> str:
    name = _cursor_state_name(runtime_id, state_kind, sequence, head_id)
    try:
        os.link(
            _cursor_token_name(runtime_id),
            name,
            src_dir_fd=root_fd,
            dst_dir_fd=root_fd,
            follow_symlinks=False,
        )
        os.fsync(root_fd)
    except FileExistsError:
        pass
    return name


def _unlink_cursor_state(root_fd: int, name: str) -> None:
    try:
        os.unlink(name, dir_fd=root_fd)
        os.fsync(root_fd)
    except FileNotFoundError:
        pass


def _parse_cursor_state_name(
    runtime_id: str, name: str
) -> tuple[str, int, str | None] | None:
    prefix = f"{_CURSOR_STATE_PREFIX}{runtime_id}-"
    if not name.startswith(prefix):
        return None
    match = re.fullmatch(
        rf"{re.escape(prefix)}([CP])-([0-9]{{8}})-(GENESIS|[0-9a-f]{{64}})",
        name,
    )
    if match is None:
        _protocol("V3 owner cursor state name is malformed")
    kind = match.group(1)
    sequence = int(match.group(2))
    encoded_head = match.group(3)
    head_id = None if encoded_head == _GENESIS_HEAD else _cid(
        encoded_head, "V3 owner cursor head"
    )
    if (sequence == 0) is not (head_id is None):
        _protocol("V3 owner cursor genesis semantics changed")
    return kind, sequence, head_id


def _cursor_states(
    root_fd: int,
    runtime_id: str,
    *,
    expected_device: int,
    expected_inode: int,
) -> list[tuple[str, int, str | None, str]]:
    token_name = _cursor_token_name(runtime_id)
    try:
        names = os.listdir(root_fd)
    except OSError as error:
        raise H1SharedCapOwnerV3ProtocolFailure(
            "V3 owner root cannot enumerate its cursor"
        ) from error
    result: list[tuple[str, int, str | None, str]] = []
    observed_links = 0
    state_prefix = f"{_CURSOR_STATE_PREFIX}{runtime_id}-"
    for name in names:
        if name != token_name and not name.startswith(state_prefix):
            continue
        try:
            metadata = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        except OSError as error:
            raise H1SharedCapOwnerV3ProtocolFailure(
                "V3 owner cursor namespace changed during replay"
            ) from error
        same_inode = (metadata.st_dev, metadata.st_ino) == (
            expected_device,
            expected_inode,
        )
        if same_inode:
            observed_links += 1
            parsed = _parse_cursor_state_name(runtime_id, name)
            if name != token_name and parsed is None:
                _protocol("V3 owner cursor token has an unregistered hard link")
        else:
            continue
        if name == token_name:
            continue
        assert parsed is not None
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            _protocol("V3 owner cursor state is not private and regular")
        result.append((*parsed, name))
    token_fd = _open_cursor_token(root_fd, runtime_id)
    try:
        token_metadata = os.fstat(token_fd)
        if (token_metadata.st_dev, token_metadata.st_ino) != (
            expected_device,
            expected_inode,
        ):
            _protocol("V3 owner cursor token inode changed")
        if token_metadata.st_nlink != observed_links:
            _protocol("V3 owner cursor token has an unregistered hard link")
    finally:
        os.close(token_fd)
    if not result:
        _protocol("V3 owner high-water cursor state is absent")
    return result


def _initialize_owner_cursor(
    root_fd: int,
    runtime_id: str,
    *,
    allow_create: bool,
) -> int:
    token_name = _cursor_token_name(runtime_id)
    token_raw = _cursor_token_bytes(runtime_id)
    if allow_create:
        if not _publish_new(root_fd, token_name, token_raw):
            _protocol("V3 new owner cursor token already exists")
        _link_cursor_state(root_fd, runtime_id, "C", 0, None)
    token_fd = _open_cursor_token(root_fd, runtime_id)
    if not allow_create:
        metadata = os.fstat(token_fd)
        _cursor_states(
            root_fd,
            runtime_id,
            expected_device=metadata.st_dev,
            expected_inode=metadata.st_ino,
        )
    return token_fd


def _recover_owner_cursor(
    root_fd: int,
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
) -> _ReplayState:
    rows = _cursor_states(
        root_fd,
        handle.runtime_id,
        expected_device=handle.cursor_token_device,
        expected_inode=handle.cursor_token_inode,
    )
    committed = sorted((row for row in rows if row[0] == "C"), key=lambda row: row[1])
    pending = sorted((row for row in rows if row[0] == "P"), key=lambda row: row[1])
    if len(committed) not in {1, 2} or len(pending) > 1:
        _protocol("V3 owner cursor has an invalid transition shape")
    if len(committed) == 2:
        old, new = committed
        if new[1] != old[1] + 1:
            _protocol("V3 owner cursor committed states are not adjacent")
        if pending and (pending[0][1], pending[0][2]) != (new[1], new[2]):
            _protocol("V3 owner cursor pending/committed states disagree")
        if (state.sequence, state.head_id) != (new[1], new[2]):
            _protocol("V3 owner journal differs from its newer cursor state")
        if pending:
            _unlink_cursor_state(root_fd, pending[0][3])
        _unlink_cursor_state(root_fd, old[3])
        state.pending_cursor = None
        return state

    current = committed[0]
    if not pending:
        if (state.sequence, state.head_id) != (current[1], current[2]):
            _protocol("V3 owner journal was truncated or exceeds its cursor")
        state.pending_cursor = None
        return state

    next_row = pending[0]
    if next_row[1] != current[1] + 1:
        _protocol("V3 owner pending cursor is not the next sequence")
    if (state.sequence, state.head_id) == (next_row[1], next_row[2]):
        next_committed = _link_cursor_state(
            root_fd,
            handle.runtime_id,
            "C",
            next_row[1],
            next_row[2],
        )
        _unlink_cursor_state(root_fd, next_row[3])
        _unlink_cursor_state(root_fd, current[3])
        if next_committed not in os.listdir(root_fd):  # pragma: no cover
            _protocol("V3 owner cursor recovery lost its committed state")
        state.pending_cursor = None
        return state
    if (state.sequence, state.head_id) == (current[1], current[2]):
        state.pending_cursor = (next_row[1], _cid(next_row[2], "V3 pending head"))
        return state
    _protocol("V3 owner pending cursor and journal cannot be reconciled")


def _profile_from_document(document: dict[str, Any]) -> H1SharedCapProfileCoreV3:
    limits_raw = document.get("limits")
    if type(limits_raw) is not list:
        _fail("V3 profile limits are malformed")
    limits = tuple(
        H1SharedCapLimitV3(row["path"], row["reducer"], row["hard_cap"])
        for row in limits_raw
        if type(row) is dict and set(row) == {"path", "reducer", "hard_cap"}
    )
    if len(limits) != len(limits_raw):
        _fail("V3 profile limit fields are not exact")
    value = H1SharedCapProfileCoreV3(
        document["logical_occurrence_id"],
        document["route_attempt_id"],
        document["decision_point_id"],
        document["transaction_id"],
        document["caller_pinned_lifecycle_provenance_id"],
        document["lifecycle_program_snapshot_id"],
        document["lifecycle_program_id"],
        document["lifecycle_branch_analysis_id"],
        limits,
    )
    if value.to_document() != document:
        _fail("V3 profile core did not replay exactly")
    return value


def _source_from_document(
    document: dict[str, Any],
) -> H1SharedCapOwnerV3SourceManifest:
    value = H1SharedCapOwnerV3SourceManifest(
        document["caller_pinned_lifecycle_provenance_id"],
        document["lifecycle_program_snapshot_id"],
        document["lifecycle_program_id"],
        document["lifecycle_branch_analysis_id"],
    )
    if value.to_document() != document:
        _fail("V3 source manifest did not replay exactly")
    return value


def _runtime_payload(
    profile: H1SharedCapProfileCoreV3,
    source: H1SharedCapOwnerV3SourceManifest,
    gate_id: str,
    *,
    owner_root_realpath: str,
    owner_root_device: int,
    owner_root_inode: int,
) -> dict[str, Any]:
    root_path = Path(_nonempty(owner_root_realpath, "owner root realpath"))
    if not root_path.is_absolute() or str(root_path) != owner_root_realpath:
        _fail("owner root realpath must be one normalized absolute path")
    return {
        "schema": "acfqp.k7_h1_shared_cap_runtime_binding.v3",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_shared_cap_profile_core_v3_id": profile.profile_id,
        "h1_shared_cap_owner_v3_source_manifest_id": source.manifest_id,
        "h1_attempt_rejection_gate_id": _cid(gate_id, "attempt rejection gate"),
        "logical_occurrence_id": profile.logical_occurrence_id,
        "route_attempt_id": profile.route_attempt_id,
        "decision_point_id": profile.decision_point_id,
        "transaction_id": profile.transaction_id,
        "owner_root_realpath": owner_root_realpath,
        "owner_root_device": _nonnegative(owner_root_device, "owner root device"),
        "owner_root_inode": _nonnegative(owner_root_inode, "owner root inode"),
        "identity_graph": "PROFILE_CORE_TO_GATE_TO_RUNTIME_BINDING",
        "gate_shared_owner_profile_id_semantics": "PROFILE_CORE_ID",
        "durable_journal_present": True,
        "real_syscall_adapter_bound": False,
        "production_activation_chain_verified": False,
        "formal_actual_compliance_eligible": False,
        "production_execution_authorized": False,
        "official_execution_allowed": False,
    }


def _runtime_document(
    profile: H1SharedCapProfileCoreV3,
    source: H1SharedCapOwnerV3SourceManifest,
    gate_id: str,
    *,
    owner_root_realpath: str,
    owner_root_device: int,
    owner_root_inode: int,
) -> dict[str, Any]:
    return _id_payload(
        RUNTIME_DOMAIN,
        _runtime_payload(
            profile,
            source,
            gate_id,
            owner_root_realpath=owner_root_realpath,
            owner_root_device=owner_root_device,
            owner_root_inode=owner_root_inode,
        ),
        "h1_shared_cap_owner_v3_runtime_id",
    )


def _validate_profile_source(
    profile: H1SharedCapProfileCoreV3,
    source: H1SharedCapOwnerV3SourceManifest,
) -> None:
    if (
        profile.caller_pinned_lifecycle_provenance_id,
        profile.lifecycle_program_snapshot_id,
        profile.lifecycle_program_id,
        profile.lifecycle_branch_analysis_id,
    ) != (
        source.caller_pinned_lifecycle_provenance_id,
        source.lifecycle_program_snapshot_id,
        source.lifecycle_program_id,
        source.lifecycle_branch_analysis_id,
    ):
        _fail("V3 profile and source manifest lifecycle identities differ")


def _validate_gate(
    profile: H1SharedCapProfileCoreV3,
    gate: rejection_v1.H1AttemptRejectionGateHandleV1,
) -> None:
    spec = gate.spec
    if (
        spec.logical_occurrence_id != profile.logical_occurrence_id
        or spec.route_attempt_id != profile.route_attempt_id
        or spec.caller_pinned_lifecycle_provenance_id
        != profile.caller_pinned_lifecycle_provenance_id
    ):
        _fail("V3 gate differs from its ProfileCore identity chain")


def initialize_h1_shared_cap_owner_v3(
    base_directory: str | Path,
    *,
    profile: H1SharedCapProfileCoreV3,
    source_manifest: H1SharedCapOwnerV3SourceManifest,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
) -> H1SharedCapOwnerV3Handle:
    if type(profile) is not H1SharedCapProfileCoreV3 or type(
        source_manifest
    ) is not H1SharedCapOwnerV3SourceManifest:
        _fail("V3 initialization requires exact profile/source objects")
    _validate_profile_source(profile, source_manifest)
    _validate_gate(profile, rejection_gate)
    verified_gate = rejection_v1.open_h1_attempt_rejection_gate_v1(
        rejection_gate.gate_directory,
        expected_gate_id=rejection_gate.spec.gate_id,
    )
    _validate_gate(profile, verified_gate)
    root_path, root_fd = _resolve_owner_root(base_directory, create=True)
    root_metadata = os.fstat(root_fd)
    runtime = _runtime_document(
        profile,
        source_manifest,
        verified_gate.spec.gate_id,
        owner_root_realpath=str(root_path),
        owner_root_device=root_metadata.st_dev,
        owner_root_inode=root_metadata.st_ino,
    )
    runtime_id = runtime["h1_shared_cap_owner_v3_runtime_id"]
    try:
        created = False
        try:
            os.mkdir(runtime_id, mode=0o700, dir_fd=root_fd)
            created = True
        except FileExistsError:
            pass
        os.fsync(root_fd)
        directory_fd = _open_private_directory_at(root_fd, runtime_id)
        cursor_token_fd = -1
        try:
            fcntl.flock(directory_fd, fcntl.LOCK_EX)
            cursor_token_fd = _initialize_owner_cursor(
                root_fd,
                runtime_id,
                allow_create=created,
            )
            allocation = _freeze_or_verify_allocation(
                runtime_id,
                root_path,
                root_fd,
                directory_fd,
                cursor_token_fd,
                allow_create=created,
            )
            static_records = {
                _PROFILE_FILE: canonical_json_bytes(profile.to_document()),
                _SOURCE_FILE: canonical_json_bytes(source_manifest.to_document()),
                _RUNTIME_FILE: canonical_json_bytes(runtime),
            }
            for name, raw in static_records.items():
                if created:
                    _publish_exact(directory_fd, name, raw)
                else:
                    existing = _read_file(directory_fd, name)
                    if existing is None or not hmac.compare_digest(existing, raw):
                        _protocol(
                            "V3 existing owner static record is absent or changed"
                        )
        finally:
            if cursor_token_fd >= 0:
                os.close(cursor_token_fd)
            os.close(directory_fd)
    finally:
        os.close(root_fd)
    owner_directory = root_path / runtime_id
    handle = H1SharedCapOwnerV3Handle(
        str(owner_directory),
        str(Path(verified_gate.gate_directory).resolve(strict=True)),
        runtime_id,
        profile,
        source_manifest,
        str(root_path),
        allocation["owner_root_device"],
        allocation["owner_root_inode"],
        allocation["owner_directory_device"],
        allocation["owner_directory_inode"],
        allocation["cursor_token_device"],
        allocation["cursor_token_inode"],
    )
    replay_h1_shared_cap_owner_v3(handle)
    return handle


def open_h1_shared_cap_owner_v3(
    owner_directory: str | Path,
    *,
    expected_runtime_id: str,
    gate_directory: str | Path,
) -> H1SharedCapOwnerV3Handle:
    expected = _cid(expected_runtime_id, "expected V3 runtime")
    requested_gate_id = _cid(
        Path(gate_directory).name,
        "expected attempt rejection gate",
    )
    gate = rejection_v1.open_h1_attempt_rejection_gate_v1(
        gate_directory,
        expected_gate_id=requested_gate_id,
    )
    supplied_path = Path(owner_directory)
    if not supplied_path.is_absolute() or supplied_path.name != expected:
        _fail("V3 owner directory name differs from expected runtime")
    root_path = supplied_path.parent.resolve(strict=True)
    root_fd = _open_private_directory(root_path)
    try:
        directory_fd = _open_private_directory_at(root_fd, expected)
        cursor_token_fd = -1
        try:
            fcntl.flock(directory_fd, fcntl.LOCK_EX)
            cursor_token_fd = _initialize_owner_cursor(
                root_fd,
                expected,
                allow_create=False,
            )
            allocation = _freeze_or_verify_allocation(
                expected,
                root_path,
                root_fd,
                directory_fd,
                cursor_token_fd,
                allow_create=False,
            )
            profile_raw = _read_file(directory_fd, _PROFILE_FILE)
            source_raw = _read_file(directory_fd, _SOURCE_FILE)
            runtime_raw = _read_file(directory_fd, _RUNTIME_FILE)
            if profile_raw is None or source_raw is None or runtime_raw is None:
                _fail("V3 owner static identity records are incomplete")
            profile = _profile_from_document(_parse_document(profile_raw, "V3 profile"))
            source = _source_from_document(_parse_document(source_raw, "V3 source"))
            runtime = _parse_document(runtime_raw, "V3 runtime")
            expected_runtime = _runtime_document(
                profile,
                source,
                runtime["h1_attempt_rejection_gate_id"],
                owner_root_realpath=str(root_path),
                owner_root_device=allocation["owner_root_device"],
                owner_root_inode=allocation["owner_root_inode"],
            )
            if runtime != expected_runtime or runtime[
                "h1_shared_cap_owner_v3_runtime_id"
            ] != expected:
                _fail("V3 runtime binding did not replay exactly")
            if runtime["h1_attempt_rejection_gate_id"] != requested_gate_id:
                _fail("V3 runtime binding names another rejection gate")
            _validate_profile_source(profile, source)
            _validate_gate(profile, gate)
        finally:
            if cursor_token_fd >= 0:
                os.close(cursor_token_fd)
            os.close(directory_fd)
    finally:
        os.close(root_fd)
    path = root_path / expected
    handle = H1SharedCapOwnerV3Handle(
        str(path), str(Path(gate_directory).resolve(strict=True)), expected,
        profile, source, str(root_path), allocation["owner_root_device"],
        allocation["owner_root_inode"], allocation["owner_directory_device"],
        allocation["owner_directory_inode"], allocation["cursor_token_device"],
        allocation["cursor_token_inode"],
    )
    replay_h1_shared_cap_owner_v3(handle)
    return handle


def _gate_for(handle: H1SharedCapOwnerV3Handle):
    return rejection_v1.open_h1_attempt_rejection_gate_v1(
        handle.gate_directory,
        expected_gate_id=_cid(
            Path(handle.gate_directory).name, "attempt rejection gate"
        ),
    )


def _side_effect_guard_key(
    handle: H1SharedCapOwnerV3Handle,
) -> tuple[str, str]:
    if type(handle) is not H1SharedCapOwnerV3Handle:
        _fail("V3 owner handle has a foreign type")
    return (
        _cid(Path(handle.gate_directory).name, "attempt rejection gate"),
        handle.runtime_id,
    )


def _active_guard_for_gate(
    handle: H1SharedCapOwnerV3Handle,
) -> tuple[tuple[str, str], bool, bool]:
    key = _side_effect_guard_key(handle)
    active = _ACTIVE_SIDE_EFFECT_GUARDS.get()
    same_runtime = key in active
    same_gate = any(row[0] == key[0] for row in active)
    return key, same_runtime, same_gate


_COMMON_RECORD_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_shared_cap_owner_v3_runtime_id",
        "h1_shared_cap_profile_core_v3_id",
        "h1_attempt_rejection_gate_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "transaction_id",
        "sequence",
        "previous_head_id",
        "record_kind",
        "formal_actual_compliance_eligible",
        "formal_counter_eligible",
        "production_execution_authorized",
        "official_execution_allowed",
    }
)
_EXTRA_FIELDS = {
    "acfqp.k7_h1_shared_cap_reservation.v3": frozenset(
        {
            "operation_id",
            "site_key",
            "path",
            "reducer",
            "reservation_upper",
            "admission_candidate",
            "charged_before",
            "outstanding_before",
            "durable_before_side_effect",
            "admission_outcome",
            "rejection_request_id",
        }
    ),
    "acfqp.k7_h1_shared_cap_native_cell.v3": frozenset(
        {
            "h1_shared_cap_owner_v3_reservation_id",
            "operation_id",
            "path",
            "lifecycle_state",
            "durable_before_native_effect",
        }
    ),
    "acfqp.k7_h1_shared_cap_native_evidence.v3": frozenset(
        {
            "h1_shared_cap_owner_v3_reservation_id",
            "h1_shared_cap_owner_v3_native_cell_id",
            "operation_id",
            "path",
            "value_basis",
            "native_observed_value",
            "charged_value",
            "construction_exact_value_assertion",
            "native_authority_verified",
            "evidence_source_authority_verified",
            "conservative_charge",
            "upper_bound_violation",
            "evidence_source_id",
        }
    ),
    "acfqp.k7_h1_shared_cap_settlement.v3": frozenset(
        {
            "h1_shared_cap_owner_v3_reservation_id",
            "h1_shared_cap_owner_v3_native_evidence_id",
            "operation_id",
            "path",
            "reducer",
            "value_basis",
            "native_observed_value",
            "charged_value",
            "reservation_upper",
            "charged_before",
            "charged_after",
            "outstanding_before",
            "outstanding_after",
            "single_spend",
        }
    ),
    "acfqp.k7_h1_shared_cap_receipt.v3": frozenset(
        {
            "subject_kind",
            "subject_id",
            "path",
            "reducer",
            "reservation_upper",
            "native_observed_value",
            "charged_value",
            "value_basis",
            "construction_exact_value_assertion",
            "native_authority_verified",
            "conservative_charge",
            "upper_bound_violation",
            "control_cap_rejections",
        }
    ),
    "acfqp.k7_h1_shared_cap_event.v3": frozenset(
        {
            "h1_shared_cap_owner_v3_receipt_id",
            "subject_kind",
            "subject_id",
            "path",
            "reducer",
            "reservation_upper",
            "native_observed_value",
            "charged_value",
            "value_basis",
            "construction_exact_value_assertion",
            "native_authority_verified",
            "conservative_charge",
            "upper_bound_violation",
            "control_cap_rejections",
        }
    ),
    "acfqp.k7_h1_shared_cap_snapshot.v3": frozenset(
        {
            "h1_shared_cap_owner_v3_receipt_id",
            "h1_shared_cap_owner_v3_event_id",
            "charged_values",
            "outstanding_values",
            "reservation_count",
            "settlement_count",
            "conservative_settlement_count",
            "observed_overrun_count",
            "control_cap_rejections",
            "all_settlements_nonconservative",
            "all_native_authorities_verified",
            "native_zero_eligible",
            "journal_replay_complete",
        }
    ),
}


def _common_record_payload(
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    *,
    schema: str,
    kind: str,
) -> dict[str, Any]:
    profile = handle.profile
    return {
        "schema": schema,
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_shared_cap_owner_v3_runtime_id": handle.runtime_id,
        "h1_shared_cap_profile_core_v3_id": profile.profile_id,
        "h1_attempt_rejection_gate_id": Path(handle.gate_directory).name,
        "logical_occurrence_id": profile.logical_occurrence_id,
        "route_attempt_id": profile.route_attempt_id,
        "decision_point_id": profile.decision_point_id,
        "transaction_id": profile.transaction_id,
        "sequence": state.sequence + 1,
        "previous_head_id": (
            state.head_id
            if state.head_id is not None
            else _typed_null("JOURNAL_GENESIS")
        ),
        "record_kind": kind,
        "formal_actual_compliance_eligible": False,
        "formal_counter_eligible": False,
        "production_execution_authorized": False,
        "official_execution_allowed": False,
    }


def _append_record(
    root_fd: int,
    directory_fd: int,
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    *,
    schema: str,
    kind: str,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    document = _next_record_document(
        handle,
        state,
        schema=schema,
        kind=kind,
        extra=extra,
    )
    _, id_field = _RECORD_META[schema]
    name = f"{document['sequence']:08d}-{document[id_field]}.json"
    next_cursor = (document["sequence"], document[id_field])
    raw = canonical_json_bytes(document)
    if not raw or len(raw) > _MAX_DOCUMENT_BYTES:
        _fail("V3 journal record exceeds its byte cap before cursor advance")
    _require_next_pair_record(state, document)
    if state.pending_cursor is None:
        _link_cursor_state(
            root_fd,
            handle.runtime_id,
            "P",
            next_cursor[0],
            next_cursor[1],
        )
    elif state.pending_cursor != next_cursor:
        _protocol("V3 pending cursor belongs to a different durable append")
    if not _publish_new(directory_fd, name, raw):
        existing = _read_file(directory_fd, name)
        if existing is None or not hmac.compare_digest(existing, raw):
            _protocol("V3 append-only journal sequence was already spent")
    next_committed = _link_cursor_state(
        root_fd,
        handle.runtime_id,
        "C",
        next_cursor[0],
        next_cursor[1],
    )
    current_committed = _cursor_state_name(
        handle.runtime_id,
        "C",
        state.sequence,
        state.head_id,
    )
    pending = _cursor_state_name(
        handle.runtime_id,
        "P",
        next_cursor[0],
        next_cursor[1],
    )
    _unlink_cursor_state(root_fd, pending)
    if current_committed != next_committed:
        _unlink_cursor_state(root_fd, current_committed)
    return document


def _next_record_document(
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    *,
    schema: str,
    kind: str,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    """Construct the exact next record without mutating its durable journal."""

    domain, id_field = _RECORD_META[schema]
    payload = {
        **_common_record_payload(handle, state, schema=schema, kind=kind),
        **dict(extra),
    }
    return _id_payload(domain, payload, id_field)


def _initial_state() -> _ReplayState:
    return _ReplayState(
        sequence=0,
        head_id=None,
        charged={path: 0 for path in SHARED_RESOURCE_PATHS},
        outstanding={path: 0 for path in SHARED_RESOURCE_PATHS},
        reservations={},
        reservation_by_operation={},
        cells={},
        evidence={},
        settlements={},
        rejection_admissions={},
        rejection_admission_by_operation={},
        receipts={},
        events={},
        snapshots=[],
        rejection_commit_id=None,
        conservative_settlement_count=0,
        observed_overrun_count=0,
    )


def _record_id(document: Mapping[str, Any]) -> str:
    schema = document["schema"]
    if schema not in _RECORD_META:
        _protocol("V3 journal record has an unknown schema")
    return _cid(document[_RECORD_META[schema][1]], "V3 journal record")


def _verify_record_identity(document: dict[str, Any]) -> str:
    schema = document.get("schema")
    if schema not in _RECORD_META:
        _protocol("V3 journal record has an unknown schema")
    domain, id_field = _RECORD_META[schema]
    expected_fields = _COMMON_RECORD_FIELDS | _EXTRA_FIELDS[schema] | {id_field}
    if set(document) != expected_fields:
        _protocol("V3 journal record fields are not exact")
    payload = dict(document)
    claimed = _cid(payload.pop(id_field), "V3 journal record")
    if content_id(domain, payload) != claimed:
        _protocol("V3 journal record content ID is invalid")
    return claimed


def _native_semantics(
    basis: H1SharedValueBasisV3,
    *,
    reservation_upper: int,
    native_observed_value: int | None,
) -> tuple[H1SharedNativeStateV3, Any, int, bool, bool, bool]:
    if basis is H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER:
        if native_observed_value is not None:
            _fail("conservative settlement cannot claim a native observation")
        return (
            H1SharedNativeStateV3.AMBIGUOUS_AT_CUTOFF,
            _typed_null("NATIVE_VALUE_UNRESOLVED_AT_CUTOFF"),
            reservation_upper,
            False,
            True,
            False,
        )
    if type(native_observed_value) is not int or native_observed_value < 0:
        _fail("exact/known native evidence requires one nonnegative value")
    if basis is H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO:
        if native_observed_value != 0:
            _fail("known-not-started evidence must observe and charge zero")
        return (
            H1SharedNativeStateV3.KNOWN_NOT_STARTED,
            0,
            0,
            True,
            False,
            False,
        )
    if basis is H1SharedValueBasisV3.OBSERVED_OVERRUN:
        if native_observed_value <= reservation_upper:
            _fail("observed-overrun evidence must exceed its reservation")
        return (
            H1SharedNativeStateV3.OBSERVED,
            native_observed_value,
            native_observed_value,
            True,
            False,
            True,
        )
    if (
        basis is H1SharedValueBasisV3.EXACT_SOURCE_EVENT
        and native_observed_value != 1
    ):
        _fail("exact source event must be one registered unit event")
    if native_observed_value > reservation_upper:
        _fail("exact evidence over its reservation requires OBSERVED_OVERRUN")
    return (
        H1SharedNativeStateV3.OBSERVED,
        native_observed_value,
        native_observed_value,
        True,
        False,
        False,
    )


def _limit(profile: H1SharedCapProfileCoreV3, path: str) -> H1SharedCapLimitV3:
    if path not in SHARED_RESOURCE_PATHS:
        _fail("V3 operation names an unknown shared path")
    return profile.limits[SHARED_RESOURCE_PATHS.index(path)]


def _require_record_context(
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    document: dict[str, Any],
) -> None:
    profile = handle.profile
    expected_previous: Any = (
        state.head_id if state.head_id is not None else _typed_null("JOURNAL_GENESIS")
    )
    if (
        document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["h1_shared_cap_owner_v3_runtime_id"] != handle.runtime_id
        or document["h1_shared_cap_profile_core_v3_id"] != profile.profile_id
        or document["h1_attempt_rejection_gate_id"]
        != Path(handle.gate_directory).name
        or document["logical_occurrence_id"] != profile.logical_occurrence_id
        or document["route_attempt_id"] != profile.route_attempt_id
        or document["decision_point_id"] != profile.decision_point_id
        or document["transaction_id"] != profile.transaction_id
        or document["sequence"] != state.sequence + 1
        or document["previous_head_id"] != expected_previous
        or document["formal_actual_compliance_eligible"] is not False
        or document["formal_counter_eligible"] is not False
        or document["production_execution_authorized"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _protocol("V3 journal context, sequence, or previous head changed")


def _apply_reservation(
    state: _ReplayState,
    document: dict[str, Any],
    handle: H1SharedCapOwnerV3Handle,
) -> None:
    if state.rejection_admissions:
        _protocol("V3 owner journal continued after its rejection admission")
    if document["record_kind"] not in {
        "RESERVATION_DURABLE",
        "REJECTION_ADMISSION_DURABLE",
    }:
        _protocol("V3 reservation/admission record kind changed")
    operation = _cid(document["operation_id"], "V3 operation")
    _nonempty(document["site_key"], "V3 site key")
    reservation_id = _record_id(document)
    if (
        operation in state.reservation_by_operation
        or operation in state.rejection_admission_by_operation
        or reservation_id in state.reservations
    ):
        _protocol("V3 reservation/admission operation was spent more than once")
    path = document["path"]
    limit = _limit(handle.profile, path)
    upper = _nonnegative(document["reservation_upper"], "reservation upper")
    if document["reducer"] != limit.reducer.value:
        _protocol("V3 reservation reducer differs from its profile")
    if (
        document["charged_before"] != state.charged[path]
        or document["outstanding_before"] != state.outstanding[path]
        or document["durable_before_side_effect"] is not True
    ):
        _protocol("V3 reservation accumulator prestate changed")
    candidate = (
        state.charged[path] + state.outstanding[path] + upper
        if limit.reducer is H1SharedReducerV3.SUM
        else max(state.charged[path], upper)
    )
    if limit.reducer is H1SharedReducerV3.MAX and state.outstanding[path] != 0:
        _protocol("V3 construction MAX core permits one unresolved exposure")
    if document["admission_candidate"] != candidate:
        _protocol("V3 reservation/admission candidate changed")
    outcome = document["admission_outcome"]
    if outcome == "ADMITTED":
        if (
            document["record_kind"] != "RESERVATION_DURABLE"
            or candidate > limit.hard_cap
            or document["rejection_request_id"]
            != _typed_null("CAP_NOT_EXCEEDED")
        ):
            _protocol("V3 reservation was admitted against a wrong candidate/cap")
        state.outstanding[path] += upper
        state.reservations[reservation_id] = document
        state.reservation_by_operation[operation] = reservation_id
        return
    if outcome != "REJECTED_BEFORE_SIDE_EFFECT":
        _protocol("V3 reservation/admission outcome is invalid")
    request_id = _cid(document["rejection_request_id"], "V3 rejection request")
    expected_request_id = _rejection_request_id(
        handle,
        operation_id=operation,
        site_key=document["site_key"],
        path=path,
        reducer=limit.reducer.value,
        reservation_upper=upper,
        candidate=candidate,
        hard_cap=limit.hard_cap,
    )
    if (
        document["record_kind"] != "REJECTION_ADMISSION_DURABLE"
        or candidate <= limit.hard_cap
        or request_id != expected_request_id
        or request_id in state.rejection_admissions
        or state.rejection_admissions
    ):
        _protocol("V3 rejection admission differs from its owner cap prestate")
    state.rejection_admissions[request_id] = document
    state.rejection_admission_by_operation[operation] = request_id


def _apply_cell(state: _ReplayState, document: dict[str, Any]) -> None:
    if document["record_kind"] != "NATIVE_CELL_DURABLE":
        _protocol("V3 native-cell record kind changed")
    reservation_id = _cid(
        document["h1_shared_cap_owner_v3_reservation_id"], "V3 reservation"
    )
    reservation = state.reservations.get(reservation_id)
    if reservation is None or reservation_id in state.cells:
        _protocol("V3 native cell is missing, duplicate, or reordered")
    try:
        lifecycle_state = H1SharedNativeStateV3(document["lifecycle_state"])
    except (TypeError, ValueError) as error:
        raise H1SharedCapOwnerV3ProtocolFailure(
            "V3 native-cell lifecycle state is invalid"
        ) from error
    if (
        document["operation_id"] != reservation["operation_id"]
        or document["path"] != reservation["path"]
        or lifecycle_state
        not in {
            H1SharedNativeStateV3.SIDE_EFFECT_STARTED,
            H1SharedNativeStateV3.KNOWN_NOT_STARTED,
        }
        or document["durable_before_native_effect"] is not True
    ):
        _protocol("V3 native cell crossed its reservation or state")
    state.cells[reservation_id] = document


def _apply_evidence(state: _ReplayState, document: dict[str, Any]) -> None:
    if document["record_kind"] != "NATIVE_EVIDENCE_DURABLE":
        _protocol("V3 native-evidence record kind changed")
    reservation_id = _cid(
        document["h1_shared_cap_owner_v3_reservation_id"], "V3 reservation"
    )
    reservation = state.reservations.get(reservation_id)
    cell = state.cells.get(reservation_id)
    if reservation is None or cell is None or reservation_id in state.evidence:
        _protocol("V3 native evidence is missing, duplicate, or reordered")
    basis = H1SharedValueBasisV3(document["value_basis"])
    _require_value_basis_path(basis, reservation["path"])
    _cid(document["evidence_source_id"], "V3 native evidence source")
    raw_native = document["native_observed_value"]
    native = None if type(raw_native) is dict else raw_native
    semantics = _native_semantics(
        basis,
        reservation_upper=reservation["reservation_upper"],
        native_observed_value=native,
    )
    _, expected_native, charged, exact, conservative, overrun = semantics
    required_lifecycle = (
        H1SharedNativeStateV3.KNOWN_NOT_STARTED
        if basis is H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO
        else H1SharedNativeStateV3.SIDE_EFFECT_STARTED
    )
    if (
        document["h1_shared_cap_owner_v3_native_cell_id"] != _record_id(cell)
        or document["operation_id"] != reservation["operation_id"]
        or document["path"] != reservation["path"]
        or cell["lifecycle_state"] != required_lifecycle.value
        or document["native_observed_value"] != expected_native
        or document["charged_value"] != charged
        or document["construction_exact_value_assertion"] is not exact
        or document["native_authority_verified"] is not False
        or document["evidence_source_authority_verified"] is not False
        or document["conservative_charge"] is not conservative
        or document["upper_bound_violation"] is not overrun
    ):
        _protocol("V3 native evidence value/basis semantics changed")
    state.evidence[reservation_id] = document
    if overrun:
        # The durable evidence is already sufficient to prove the upper-bound
        # violation.  A crash before settlement must not temporarily reopen
        # admission or native side effects.
        state.observed_overrun_count += 1


def _apply_settlement(state: _ReplayState, document: dict[str, Any], profile) -> None:
    if document["record_kind"] != "SETTLEMENT_DURABLE":
        _protocol("V3 settlement record kind changed")
    reservation_id = _cid(
        document["h1_shared_cap_owner_v3_reservation_id"], "V3 reservation"
    )
    reservation = state.reservations.get(reservation_id)
    evidence = state.evidence.get(reservation_id)
    if reservation is None or evidence is None or reservation_id in state.settlements:
        _protocol("V3 settlement is missing, duplicate, or reordered")
    path = reservation["path"]
    limit = _limit(profile, path)
    charged = evidence["charged_value"]
    before = state.charged[path]
    after = before + charged if limit.reducer is H1SharedReducerV3.SUM else max(before, charged)
    outstanding_before = state.outstanding[path]
    outstanding_after = outstanding_before - reservation["reservation_upper"]
    if (
        outstanding_after < 0
        or document["h1_shared_cap_owner_v3_native_evidence_id"]
        != _record_id(evidence)
        or document["operation_id"] != reservation["operation_id"]
        or document["path"] != path
        or document["reducer"] != limit.reducer.value
        or document["value_basis"] != evidence["value_basis"]
        or document["native_observed_value"] != evidence["native_observed_value"]
        or document["charged_value"] != charged
        or document["reservation_upper"] != reservation["reservation_upper"]
        or document["charged_before"] != before
        or document["charged_after"] != after
        or document["outstanding_before"] != outstanding_before
        or document["outstanding_after"] != outstanding_after
        or document["single_spend"] is not True
    ):
        _protocol("V3 settlement reducer transition changed")
    state.charged[path] = after
    state.outstanding[path] = outstanding_after
    state.settlements[reservation_id] = document
    if evidence["conservative_charge"]:
        state.conservative_settlement_count += 1


def _apply_receipt(state: _ReplayState, document: dict[str, Any]) -> None:
    if document["record_kind"] != "RECEIPT_DURABLE":
        _protocol("V3 receipt kind changed")
    receipt_id = _record_id(document)
    subject_kind = document["subject_kind"]
    subject_id = _cid(document["subject_id"], "V3 receipt subject")
    if any(row["subject_id"] == subject_id for row in state.receipts.values()):
        _protocol("V3 receipt subject was published more than once")
    if subject_kind == "SETTLEMENT":
        settlement = next(
            (row for row in state.settlements.values() if _record_id(row) == subject_id),
            None,
        )
        if settlement is None:
            _protocol("V3 receipt precedes or changes its settlement")
        evidence = state.evidence.get(
            settlement["h1_shared_cap_owner_v3_reservation_id"]
        )
        if evidence is None or _record_id(evidence) != settlement[
            "h1_shared_cap_owner_v3_native_evidence_id"
        ]:
            _protocol("V3 receipt settlement lost its native evidence")
        expected = {
            "path": settlement["path"],
            "reducer": settlement["reducer"],
            "reservation_upper": settlement["reservation_upper"],
            "native_observed_value": settlement["native_observed_value"],
            "charged_value": settlement["charged_value"],
            "value_basis": settlement["value_basis"],
            "construction_exact_value_assertion": evidence["construction_exact_value_assertion"],
            "native_authority_verified": evidence["native_authority_verified"],
            "conservative_charge": evidence["conservative_charge"],
            "upper_bound_violation": evidence["upper_bound_violation"],
            "control_cap_rejections": 0 if state.rejection_commit_id is None else 1,
        }
    elif subject_kind == "CAP_REJECTION":
        if state.rejection_commit_id is not None and state.rejection_commit_id != subject_id:
            _protocol("V3 receipt contains a second cap rejection")
        state.rejection_commit_id = subject_id
        expected = {
            "path": document["path"],
            "reducer": PATH_REDUCERS[document["path"]],
            "reservation_upper": document["reservation_upper"],
            "native_observed_value": 0,
            "charged_value": 0,
            "value_basis": H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO.value,
            "construction_exact_value_assertion": True,
            "native_authority_verified": False,
            "conservative_charge": False,
            "upper_bound_violation": False,
            "control_cap_rejections": 1,
        }
    else:
        _protocol("V3 receipt subject kind is unknown")
    if any(document[key] != value for key, value in expected.items()):
        _protocol("V3 receipt values differ from their subject")
    state.receipts[receipt_id] = document


def _apply_event(state: _ReplayState, document: dict[str, Any]) -> None:
    if document["record_kind"] != "EVENT_DURABLE":
        _protocol("V3 event kind changed")
    receipt_id = _cid(
        document["h1_shared_cap_owner_v3_receipt_id"], "V3 receipt"
    )
    receipt = state.receipts.get(receipt_id)
    if receipt is None or document["previous_head_id"] != receipt_id:
        _protocol("V3 event does not immediately follow its receipt")
    if any(
        row["h1_shared_cap_owner_v3_receipt_id"] == receipt_id
        for row in state.events.values()
    ):
        _protocol("V3 receipt has more than one semantic event")
    shared = _EXTRA_FIELDS["acfqp.k7_h1_shared_cap_receipt.v3"] - {"subject_kind", "subject_id"}
    if (
        document["subject_kind"] != receipt["subject_kind"]
        or document["subject_id"] != receipt["subject_id"]
        or any(document[key] != receipt[key] for key in shared)
    ):
        _protocol("V3 receipt/event atomic semantic pair changed")
    state.events[_record_id(document)] = document


def _apply_snapshot(state: _ReplayState, document: dict[str, Any]) -> None:
    if document["record_kind"] != "SNAPSHOT_DURABLE":
        _protocol("V3 snapshot kind changed")
    receipt_id = _cid(document["h1_shared_cap_owner_v3_receipt_id"], "V3 receipt")
    event_id = _cid(document["h1_shared_cap_owner_v3_event_id"], "V3 event")
    if (
        receipt_id not in state.receipts
        or event_id not in state.events
        or state.events[event_id]["h1_shared_cap_owner_v3_receipt_id"]
        != receipt_id
        or any(
            row["h1_shared_cap_owner_v3_event_id"] == event_id
            for row in state.snapshots
        )
        or document["previous_head_id"] != event_id
        or document["charged_values"] != state.charged
        or document["outstanding_values"] != state.outstanding
        or document["reservation_count"] != len(state.reservations)
        or document["settlement_count"] != len(state.settlements)
        or document["conservative_settlement_count"]
        != state.conservative_settlement_count
        or document["observed_overrun_count"] != state.observed_overrun_count
        or document["control_cap_rejections"]
        != (0 if state.rejection_commit_id is None else 1)
        or document["all_settlements_nonconservative"]
        is not (state.conservative_settlement_count == 0)
        or document["all_native_authorities_verified"] is not False
        or document["native_zero_eligible"] is not False
        or document["journal_replay_complete"] is not True
    ):
        _protocol("V3 durable snapshot differs from journal replay")
    state.snapshots.append(document)


def _cleanup_owner_temps(directory_fd: int) -> None:
    """Remove only strict private temp links while holding the owner lock."""

    try:
        names = os.listdir(directory_fd)
    except OSError as error:
        raise ConstructionK7H1SharedCapOwnerV3Error(
            "V3 owner directory cannot be enumerated"
        ) from error
    changed = False
    for name in names:
        if not _TEMP_PATTERN.fullmatch(name):
            continue
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            _protocol("V3 orphan temp is not one private regular file")
        os.unlink(name, dir_fd=directory_fd)
        changed = True
    if changed:
        os.fsync(directory_fd)


def _record_names(directory_fd: int) -> list[tuple[int, str, str]]:
    try:
        names = os.listdir(directory_fd)
    except OSError as error:
        raise ConstructionK7H1SharedCapOwnerV3Error(
            "V3 owner directory cannot be enumerated"
        ) from error
    result: list[tuple[int, str, str]] = []
    for name in names:
        if name in _STATIC_FILES:
            continue
        match = _RECORD_PATTERN.fullmatch(name)
        if match is None:
            _protocol("V3 owner directory contains an unknown record")
        result.append((int(match.group(1)), match.group(2), name))
    result.sort()
    return result


def _replay_records_fd(
    directory_fd: int,
    handle: H1SharedCapOwnerV3Handle,
    *,
    stop_after_sequence: int | None = None,
) -> _ReplayState:
    if stop_after_sequence is not None and (
        type(stop_after_sequence) is not int or stop_after_sequence < 0
    ):
        _protocol("V3 journal replay cutoff is invalid")
    state = _initial_state()
    records = _record_names(directory_fd)
    if stop_after_sequence is not None and stop_after_sequence > len(records):
        _protocol("V3 journal replay cutoff exceeds the durable tail")
    for expected_sequence, (sequence, filename_id, name) in enumerate(records, start=1):
        if sequence != expected_sequence:
            _protocol("V3 append-only journal has a gap or duplicate sequence")
        if stop_after_sequence is not None and sequence > stop_after_sequence:
            break
        raw = _read_file(directory_fd, name)
        if raw is None:  # pragma: no cover - locked directory invariant
            _protocol("V3 journal record disappeared during replay")
        document = _parse_document(raw, "V3 journal record")
        record_id = _verify_record_identity(document)
        if filename_id != record_id:
            _protocol("V3 journal filename and content identity differ")
        _require_record_context(handle, state, document)
        _require_next_pair_record(state, document)
        schema = document["schema"]
        try:
            if schema == "acfqp.k7_h1_shared_cap_reservation.v3":
                _apply_reservation(state, document, handle)
            elif schema == "acfqp.k7_h1_shared_cap_native_cell.v3":
                _apply_cell(state, document)
            elif schema == "acfqp.k7_h1_shared_cap_native_evidence.v3":
                _apply_evidence(state, document)
            elif schema == "acfqp.k7_h1_shared_cap_settlement.v3":
                _apply_settlement(state, document, handle.profile)
            elif schema == "acfqp.k7_h1_shared_cap_receipt.v3":
                _apply_receipt(state, document)
            elif schema == "acfqp.k7_h1_shared_cap_event.v3":
                _apply_event(state, document)
            elif schema == "acfqp.k7_h1_shared_cap_snapshot.v3":
                _apply_snapshot(state, document)
            else:  # pragma: no cover - identity verifier already checks
                _protocol("V3 record schema is unhandled")
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, ConstructionK7H1SharedCapOwnerV3Error):
                raise
            raise H1SharedCapOwnerV3ProtocolFailure(
                "V3 journal semantic replay failed"
            ) from error
        state.sequence = sequence
        state.head_id = record_id
    return state


def _require_handle_locked(
    handle: H1SharedCapOwnerV3Handle,
) -> tuple[int, int, _ReplayState]:
    if type(handle) is not H1SharedCapOwnerV3Handle:
        _fail("V3 owner handle has a foreign type")
    root_path = Path(handle.owner_root_realpath)
    root_fd = _open_private_directory(root_path)
    directory_fd = -1
    cursor_token_fd = -1
    try:
        root_metadata = os.fstat(root_fd)
        if (root_metadata.st_dev, root_metadata.st_ino) != (
            handle.owner_root_device,
            handle.owner_root_inode,
        ):
            _protocol("V3 owner root inode changed")
        directory_fd = _open_private_directory_at(root_fd, handle.runtime_id)
        cursor_token_fd = _open_cursor_token(root_fd, handle.runtime_id)
        allocation = _freeze_or_verify_allocation(
            handle.runtime_id,
            root_path,
            root_fd,
            directory_fd,
            cursor_token_fd,
            allow_create=False,
        )
        cursor_metadata = os.fstat(cursor_token_fd)
        if (cursor_metadata.st_dev, cursor_metadata.st_ino) != (
            handle.cursor_token_device,
            handle.cursor_token_inode,
        ):
            _protocol("V3 owner cursor token inode changed")
        os.close(cursor_token_fd)
        cursor_token_fd = -1
        directory_metadata = os.fstat(directory_fd)
        if (directory_metadata.st_dev, directory_metadata.st_ino) != (
            handle.owner_directory_device,
            handle.owner_directory_inode,
        ):
            _protocol("V3 owner directory inode changed")
        fcntl.flock(directory_fd, fcntl.LOCK_EX)
        _cleanup_owner_temps(directory_fd)
        profile_raw = _read_file(directory_fd, _PROFILE_FILE)
        source_raw = _read_file(directory_fd, _SOURCE_FILE)
        runtime_raw = _read_file(directory_fd, _RUNTIME_FILE)
        if profile_raw is None or source_raw is None or runtime_raw is None:
            _protocol("V3 owner static records disappeared")
        profile = _profile_from_document(_parse_document(profile_raw, "V3 profile"))
        source = _source_from_document(_parse_document(source_raw, "V3 source"))
        expected_runtime = _runtime_document(
            profile,
            source,
            _cid(Path(handle.gate_directory).name, "attempt rejection gate"),
            owner_root_realpath=str(root_path),
            owner_root_device=allocation["owner_root_device"],
            owner_root_inode=allocation["owner_root_inode"],
        )
        runtime = _parse_document(runtime_raw, "V3 runtime")
        if (
            profile.to_document() != handle.profile.to_document()
            or source.to_document() != handle.source_manifest.to_document()
            or runtime != expected_runtime
            or runtime["h1_shared_cap_owner_v3_runtime_id"] != handle.runtime_id
        ):
            _protocol("V3 owner handle or static identity was transplanted")
        state = _replay_records_fd(directory_fd, handle)
        state = _recover_owner_cursor(root_fd, handle, state)
        return root_fd, directory_fd, state
    except BaseException:
        if cursor_token_fd >= 0:
            os.close(cursor_token_fd)
        if directory_fd >= 0:
            os.close(directory_fd)
        os.close(root_fd)
        raise


def _validate_owner_gate_join(
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    gate_snapshot: rejection_v1.H1AttemptRejectionGateReplaySnapshotV1,
) -> _GateOwnerJoinV3:
    """Validate the exact gate/owner join while the caller retains gate EX.

    The gate is route-attempt-wide while this journal is transaction-bound.
    Consequently a rejection owned by another transaction is valid global
    state, but its receipt/event/snapshot can only be resolved by the later
    attempt aggregate rather than by this local owner.
    """

    if (
        type(gate_snapshot)
        is not rejection_v1.H1AttemptRejectionGateReplaySnapshotV1
        or gate_snapshot.gate_id != Path(handle.gate_directory).name
    ):
        _protocol("V3 owner replay received a foreign gate snapshot")
    owner_commit_id = state.rejection_commit_id
    gate_commit_id = gate_snapshot.commit_id
    gate_commit = gate_snapshot.commit
    acknowledgement = gate_snapshot.acknowledgement
    if gate_commit is None:
        if (
            gate_commit_id is not None
            or acknowledgement is not None
            or gate_snapshot.state
            is not rejection_v1.H1AttemptRejectionGateStateV1.OPEN
        ):
            _protocol("V3 gate replay exposed a rejection state without a commit")
        if owner_commit_id is not None:
            _protocol(
                "V3 OPEN gate conflicts with an owner pair lacking its "
                "committed gate rejection"
            )
        if state.rejection_admissions:
            _protocol("V3 owner rejection admission preceded its gate rejection")
        return _GateOwnerJoinV3(
            H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION,
            recovery_required=False,
            local_pair_verified=False,
            external_attempt_rejection=False,
        )

    local_gate_owner = (
        gate_commit.shared_owner_profile_core_id == handle.profile.profile_id
        and gate_commit.source_kind
        is rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER
    )
    if not local_gate_owner:
        if owner_commit_id is not None or state.rejection_admissions:
            _protocol(
                "V3 transaction owner rejection conflicts with another "
                "attempt-wide gate owner"
            )
        if acknowledgement is None:
            if gate_snapshot.state is not (
                rejection_v1.H1AttemptRejectionGateStateV1.COMMITTED_UNACKNOWLEDGED
            ):
                _protocol("V3 external attempt rejection has an invalid gate state")
            return _GateOwnerJoinV3(
                H1SharedGateOwnerJoinStatusV3.EXTERNAL_ATTEMPT_REJECTION_UNACKNOWLEDGED,
                recovery_required=True,
                local_pair_verified=False,
                external_attempt_rejection=True,
            )
        if gate_snapshot.state is not (
            rejection_v1.H1AttemptRejectionGateStateV1.ACKNOWLEDGED
        ):
            _protocol("V3 external attempt rejection ACK has an invalid gate state")
        return _GateOwnerJoinV3(
            H1SharedGateOwnerJoinStatusV3.EXTERNAL_ATTEMPT_REJECTION_ACKNOWLEDGED,
            recovery_required=False,
            local_pair_verified=False,
            external_attempt_rejection=True,
        )

    admission = state.rejection_admissions.get(gate_commit.rejection_request_id)
    _require_rejection_gate_shape(
        handle,
        state,
        gate_commit,
        require_current_prestate=admission is None,
    )
    if admission is None:
        if state.rejection_admissions:
            _protocol("V3 gate rejection differs from prior owner admission evidence")
        if owner_commit_id is not None or acknowledgement is not None:
            _protocol("V3 owner rejection pair precedes its admission evidence")
        return _GateOwnerJoinV3(
            H1SharedGateOwnerJoinStatusV3.LOCAL_COMMIT_AWAITING_ADMISSION,
            recovery_required=True,
            local_pair_verified=False,
            external_attempt_rejection=False,
        )
    _require_rejection_context(handle, state, gate_commit)
    if owner_commit_id is None:
        if acknowledgement is not None:
            _protocol("V3 acknowledged gate lacks its exact owner rejection pair")
        return _GateOwnerJoinV3(
            H1SharedGateOwnerJoinStatusV3.LOCAL_COMMIT_AWAITING_PAIR,
            recovery_required=True,
            local_pair_verified=False,
            external_attempt_rejection=False,
        )
    if (
        gate_commit_id != owner_commit_id
        or gate_snapshot.state
        is rejection_v1.H1AttemptRejectionGateStateV1.OPEN
        or gate_snapshot.state
        is rejection_v1.H1AttemptRejectionGateStateV1.INTENT_DURABLE
    ):
        _protocol("V3 owner rejection does not equal the committed gate rejection")
    pair = _find_pair_for_subject(state, owner_commit_id)
    if pair is None:
        if acknowledgement is not None:
            _protocol("V3 gate ACK precedes the complete owner rejection pair")
        return _GateOwnerJoinV3(
            H1SharedGateOwnerJoinStatusV3.LOCAL_COMMIT_AWAITING_PAIR,
            recovery_required=True,
            local_pair_verified=False,
            external_attempt_rejection=False,
        )
    receipt, event, snapshot = pair
    expected_pair = _rejection_pair_extra(gate_commit)
    for row in (receipt, event):
        if (
            row["subject_kind"] != "CAP_REJECTION"
            or row["subject_id"] != gate_commit.commit_id
            or any(row[key] != value for key, value in expected_pair.items())
        ):
            _protocol("V3 owner rejection pair differs from its exact gate commit")
    if acknowledgement is None:
        return _GateOwnerJoinV3(
            H1SharedGateOwnerJoinStatusV3.LOCAL_PAIR_AWAITING_ACK,
            recovery_required=True,
            local_pair_verified=False,
            external_attempt_rejection=False,
        )
    if (
        acknowledgement.receipt_id != _record_id(receipt)
        or acknowledgement.event_id != _record_id(event)
        or acknowledgement.snapshot_id != _record_id(snapshot)
        or gate_snapshot.state
        is not rejection_v1.H1AttemptRejectionGateStateV1.ACKNOWLEDGED
    ):
        _protocol("V3 gate ACK differs from the exact owner rejection pair")
    return _GateOwnerJoinV3(
        H1SharedGateOwnerJoinStatusV3.LOCAL_ACK_VERIFIED,
        recovery_required=False,
        local_pair_verified=True,
        external_attempt_rejection=False,
    )


def _acquire_joined_owner_locked(
    handle: H1SharedCapOwnerV3Handle,
) -> tuple[Any, int, int, _ReplayState, Any, _GateOwnerJoinV3]:
    """Acquire gate EX then owner EX and validate their exact semantic join."""

    gate_context = rejection_v1.hold_h1_attempt_rejection_gate_for_replay_v1(
        _gate_for(handle)
    )
    gate_snapshot = gate_context.__enter__()
    root_fd = -1
    directory_fd = -1
    try:
        root_fd, directory_fd, state = _require_handle_locked(handle)
        join = _validate_owner_gate_join(
            handle,
            state,
            gate_snapshot,
        )
    except BaseException:
        if directory_fd >= 0:
            os.close(directory_fd)
        if root_fd >= 0:
            os.close(root_fd)
        gate_context.__exit__(None, None, None)
        raise
    return (
        gate_context,
        root_fd,
        directory_fd,
        state,
        gate_snapshot,
        join,
    )


def _release_joined_owner_locked(
    gate_context: Any,
    root_fd: int,
    directory_fd: int,
) -> None:
    try:
        os.close(directory_fd)
        os.close(root_fd)
    finally:
        gate_context.__exit__(None, None, None)


def _require_owner_open_join(state: _ReplayState) -> None:
    if state.rejection_commit_id is not None or state.rejection_admissions:
        _protocol(
            "V3 OPEN gate conflicts with owner rejection admission/pair state"
        )


def replay_h1_shared_cap_owner_v3(
    handle: H1SharedCapOwnerV3Handle,
) -> dict[str, Any]:
    gate_context: Any | None
    _guard_key, same_runtime_guard, same_gate_guard = _active_guard_for_gate(handle)
    if same_gate_guard and not same_runtime_guard:
        _protocol(
            "V3 cannot replay another transaction while the attempt gate is guarded"
        )
    if same_runtime_guard:
        gate_context = None
        root_fd, directory_fd, state = _require_handle_locked(handle)
        _require_owner_open_join(state)
        gate_state = rejection_v1.H1AttemptRejectionGateStateV1.OPEN.value
        gate_join = _GateOwnerJoinV3(
            H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION,
            recovery_required=False,
            local_pair_verified=False,
            external_attempt_rejection=False,
        )
        gate_has_commit = False
    else:
        (
            gate_context,
            root_fd,
            directory_fd,
            state,
            gate_snapshot,
            gate_join,
        ) = _acquire_joined_owner_locked(handle)
        gate_state = gate_snapshot.state.value
        gate_has_commit = gate_snapshot.commit is not None
    try:
        pair_frontier = _incomplete_pair_frontier(state)
        recovery_required = (
            state.pending_cursor is not None
            or pair_frontier is not None
            or gate_join.recovery_required
        )
        return {
            "schema": "acfqp.k7_h1_shared_cap_owner_v3_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_shared_cap_owner_v3_runtime_id": handle.runtime_id,
            "h1_shared_cap_profile_core_v3_id": handle.profile.profile_id,
            "h1_attempt_rejection_gate_id": Path(handle.gate_directory).name,
            "journal_sequence": state.sequence,
            "journal_head_id": (
                state.head_id
                if state.head_id is not None
                else _typed_null("JOURNAL_GENESIS")
            ),
            "journal_replay_complete": not recovery_required,
            "recovery_required": recovery_required,
            "pending_cursor": (
                {
                    "sequence": state.pending_cursor[0],
                    "head_id": state.pending_cursor[1],
                }
                if state.pending_cursor is not None
                else _typed_null("NO_PENDING_CURSOR")
            ),
            "semantic_pair_frontier": (
                {
                    "subject_id": pair_frontier[0],
                    "stage": pair_frontier[1],
                    "frontier_id": pair_frontier[2],
                }
                if pair_frontier is not None
                else _typed_null("NO_INCOMPLETE_SEMANTIC_PAIR")
            ),
            "charged_values": dict(state.charged),
            "outstanding_values": dict(state.outstanding),
            "reservation_count": len(state.reservations),
            "rejection_admission_count": len(state.rejection_admissions),
            "settlement_count": len(state.settlements),
            "conservative_settlement_count": state.conservative_settlement_count,
            "observed_overrun_count": state.observed_overrun_count,
            "protocol_failed": state.observed_overrun_count > 0,
            "new_work_allowed": (
                state.observed_overrun_count == 0
                and state.pending_cursor is None
                and pair_frontier is None
                and gate_join.status
                is H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION
            ),
            "control_cap_rejections": 0 if state.rejection_commit_id is None else 1,
            "attempt_control_cap_rejections": (
                1 if gate_has_commit else 0
            ),
            "gate_owner_join_status": gate_join.status.value,
            "gate_owner_join_verified": (
                gate_join.status
                is H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION
                or gate_join.local_pair_verified
            ),
            "local_gate_owner_pair_verified": gate_join.local_pair_verified,
            "external_attempt_rejection": gate_join.external_attempt_rejection,
            "gate_state": gate_state,
            "all_settlements_nonconservative": (
                state.conservative_settlement_count == 0
            ),
            "all_native_authorities_verified": False,
            "native_authority_verified": False,
            "native_zero_eligible": False,
            "native_zero_blocker": "COMPLETE_ATTEMPT_LIFECYCLE_NOT_BOUND",
            "cross_process_single_spend_replayed": not recovery_required,
            "real_syscall_adapter_bound": False,
            "formal_actual_compliance_eligible": False,
            "formal_counter_eligible": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
        }
    finally:
        if gate_context is None:
            os.close(directory_fd)
            os.close(root_fd)
        else:
            _release_joined_owner_locked(gate_context, root_fd, directory_fd)


def inspect_h1_shared_cap_owner_v3_record_index(
    handle: H1SharedCapOwnerV3Handle,
) -> dict[str, Any]:
    """Return an atomic read-only index after the full durable replay.

    The index is a construction verifier aid, not a new accounting artifact or
    native-evidence authority.  All IDs come from records already validated by
    the same journal and gate-owner join used by ``replay_*``.
    """

    _guard_key, same_runtime_guard, same_gate_guard = _active_guard_for_gate(handle)
    if same_gate_guard:
        _protocol("V3 record index is unavailable while a side effect is guarded")
    (
        gate_context,
        root_fd,
        directory_fd,
        state,
        gate_snapshot,
        gate_join,
    ) = _acquire_joined_owner_locked(handle)
    try:
        pair_frontier = _incomplete_pair_frontier(state)
        if (
            state.pending_cursor is not None
            or pair_frontier is not None
            or gate_join.recovery_required
        ):
            _protocol("V3 record index requires one completely replayed frontier")
        return {
            "schema": "acfqp.k7_h1_shared_cap_owner_v3_record_index.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_shared_cap_owner_v3_runtime_id": handle.runtime_id,
            "journal_sequence": state.sequence,
            "journal_head_id": (
                state.head_id if state.head_id is not None else _typed_null("JOURNAL_GENESIS")
            ),
            "charged_values": dict(state.charged),
            "outstanding_values": dict(state.outstanding),
            "reservation_count": len(state.reservations),
            "settlement_count": len(state.settlements),
            "observed_overrun_count": state.observed_overrun_count,
            "new_work_allowed": (
                state.observed_overrun_count == 0
                and gate_join.status
                is H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION
            ),
            "record_ids_by_role": {
                "reservation": sorted(state.reservations),
                "rejection_admission": sorted(
                    _record_id(row) for row in state.rejection_admissions.values()
                ),
                "native_cell": sorted(_record_id(row) for row in state.cells.values()),
                "native_evidence": sorted(
                    _record_id(row) for row in state.evidence.values()
                ),
                "settlement": sorted(
                    _record_id(row) for row in state.settlements.values()
                ),
                "receipt": sorted(state.receipts),
                "event": sorted(state.events),
                "snapshot": sorted(_record_id(row) for row in state.snapshots),
            },
            "records_by_role": {
                "reservation": [
                    dict(state.reservations[record_id])
                    for record_id in sorted(state.reservations)
                ],
                "native_cell": [
                    dict(row)
                    for row in sorted(state.cells.values(), key=_record_id)
                ],
                "native_evidence": [
                    dict(row)
                    for row in sorted(state.evidence.values(), key=_record_id)
                ],
                "settlement": [
                    dict(row)
                    for row in sorted(state.settlements.values(), key=_record_id)
                ],
                "receipt": [
                    dict(state.receipts[record_id])
                    for record_id in sorted(state.receipts)
                ],
                "event": [
                    dict(state.events[record_id])
                    for record_id in sorted(state.events)
                ],
                "snapshot": [
                    dict(row) for row in sorted(state.snapshots, key=_record_id)
                ],
                "rejection_admission": [
                    dict(state.rejection_admissions[record_id])
                    for record_id in sorted(state.rejection_admissions)
                ],
            },
            "rejection_commit_id": (
                state.rejection_commit_id
                if state.rejection_commit_id is not None
                else _typed_null("NO_REJECTION_COMMIT")
            ),
            "rejection_ack_id": (
                gate_snapshot.acknowledgement_id
                if gate_snapshot.acknowledgement_id is not None
                else _typed_null("NO_REJECTION_ACK")
            ),
            "gate_owner_join_status": gate_join.status.value,
            "gate_owner_join_verified": (
                gate_join.status
                in {
                    H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION,
                    H1SharedGateOwnerJoinStatusV3.LOCAL_ACK_VERIFIED,
                }
            ),
            "construction_verifier_view_only": True,
            "native_evidence_authority_present": False,
            "formal_counter_eligible": False,
            "official_execution_allowed": False,
        }
    finally:
        _release_joined_owner_locked(gate_context, root_fd, directory_fd)


def inspect_h1_shared_cap_owner_v3_record_prefix(
    handle: H1SharedCapOwnerV3Handle,
    *,
    journal_sequence: int,
    journal_head_id: Any,
) -> dict[str, Any]:
    """Replay one immutable journal prefix while validating the complete tail.

    This construction-only view is intended for a trace captured before a
    later cleanup continuation appended more Owner records.  The current
    journal is first replayed in full.  The requested cutoff is then replayed
    independently and must end at the caller-supplied content head.  Therefore
    later records may only form the already-enforced append-only hash chain;
    an insertion, replacement, gap, or reordered record fails before a prefix
    view is returned.
    """

    if type(journal_sequence) is not int or journal_sequence < 0:
        _fail("V3 record-prefix sequence is invalid")
    expected_head = (
        _typed_null("JOURNAL_GENESIS")
        if journal_sequence == 0
        else _cid(journal_head_id, "V3 record-prefix head")
    )
    if journal_sequence == 0 and journal_head_id != expected_head:
        _protocol("V3 record-prefix genesis head changed")

    _guard_key, _same_runtime_guard, same_gate_guard = _active_guard_for_gate(handle)
    if same_gate_guard:
        _protocol("V3 record prefix is unavailable while a side effect is guarded")
    (
        gate_context,
        root_fd,
        directory_fd,
        full_state,
        gate_snapshot,
        gate_join,
    ) = _acquire_joined_owner_locked(handle)
    try:
        full_pair_frontier = _incomplete_pair_frontier(full_state)
        if (
            full_state.pending_cursor is not None
            or full_pair_frontier is not None
            or gate_join.recovery_required
        ):
            _protocol(
                "V3 record prefix requires one completely replayed durable tail"
            )
        prefix = _replay_records_fd(
            directory_fd,
            handle,
            stop_after_sequence=journal_sequence,
        )
        if _incomplete_pair_frontier(prefix) is not None:
            _protocol("V3 record-prefix cutoff splits one semantic journal unit")
        prefix_head = (
            prefix.head_id
            if prefix.head_id is not None
            else _typed_null("JOURNAL_GENESIS")
        )
        if prefix.sequence != journal_sequence or prefix_head != expected_head:
            _protocol("V3 record-prefix cutoff head differs from durable replay")

        if prefix.rejection_commit_id is None:
            if full_state.rejection_commit_id is None:
                if gate_join.status is not H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION:
                    _protocol("V3 record-prefix gate changed without a local journal tail")
            elif gate_join.status is not H1SharedGateOwnerJoinStatusV3.LOCAL_ACK_VERIFIED:
                _protocol("V3 record-prefix later rejection lacks a local joined tail")
            prefix_gate_status = H1SharedGateOwnerJoinStatusV3.OPEN_NO_REJECTION.value
            prefix_ack: Any = _typed_null("NO_REJECTION_ACK")
        else:
            if (
                full_state.rejection_commit_id != prefix.rejection_commit_id
                or gate_join.status is not H1SharedGateOwnerJoinStatusV3.LOCAL_ACK_VERIFIED
                or gate_snapshot.acknowledgement_id is None
            ):
                _protocol("V3 record-prefix rejection differs from the joined gate")
            prefix_gate_status = H1SharedGateOwnerJoinStatusV3.LOCAL_ACK_VERIFIED.value
            prefix_ack = gate_snapshot.acknowledgement_id

        record_ids_by_role = {
            "reservation": sorted(prefix.reservations),
            "rejection_admission": sorted(
                _record_id(row) for row in prefix.rejection_admissions.values()
            ),
            "native_cell": sorted(_record_id(row) for row in prefix.cells.values()),
            "native_evidence": sorted(
                _record_id(row) for row in prefix.evidence.values()
            ),
            "settlement": sorted(
                _record_id(row) for row in prefix.settlements.values()
            ),
            "receipt": sorted(prefix.receipts),
            "event": sorted(prefix.events),
            "snapshot": sorted(_record_id(row) for row in prefix.snapshots),
        }
        records_by_role = {
            "reservation": [
                dict(prefix.reservations[record_id])
                for record_id in sorted(prefix.reservations)
            ],
            "rejection_admission": [
                dict(prefix.rejection_admissions[record_id])
                for record_id in sorted(prefix.rejection_admissions)
            ],
            "native_cell": [
                dict(row) for row in sorted(prefix.cells.values(), key=_record_id)
            ],
            "native_evidence": [
                dict(row) for row in sorted(prefix.evidence.values(), key=_record_id)
            ],
            "settlement": [
                dict(row)
                for row in sorted(prefix.settlements.values(), key=_record_id)
            ],
            "receipt": [
                dict(prefix.receipts[record_id])
                for record_id in sorted(prefix.receipts)
            ],
            "event": [
                dict(prefix.events[record_id]) for record_id in sorted(prefix.events)
            ],
            "snapshot": [
                dict(row) for row in sorted(prefix.snapshots, key=_record_id)
            ],
        }
        return {
            "schema": "acfqp.k7_h1_shared_cap_owner_v3_record_prefix.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_shared_cap_owner_v3_runtime_id": handle.runtime_id,
            "journal_sequence": prefix.sequence,
            "journal_head_id": prefix_head,
            "charged_values": dict(prefix.charged),
            "outstanding_values": dict(prefix.outstanding),
            "reservation_count": len(prefix.reservations),
            "settlement_count": len(prefix.settlements),
            "observed_overrun_count": prefix.observed_overrun_count,
            "new_work_allowed": (
                prefix.observed_overrun_count == 0
                and prefix.rejection_commit_id is None
            ),
            "record_ids_by_role": record_ids_by_role,
            "records_by_role": records_by_role,
            "rejection_commit_id": (
                prefix.rejection_commit_id
                if prefix.rejection_commit_id is not None
                else _typed_null("NO_REJECTION_COMMIT")
            ),
            "rejection_ack_id": prefix_ack,
            "gate_owner_join_status": prefix_gate_status,
            "gate_owner_join_verified": True,
            "durable_tail_sequence": full_state.sequence,
            "durable_tail_head_id": (
                full_state.head_id
                if full_state.head_id is not None
                else _typed_null("JOURNAL_GENESIS")
            ),
            "append_only_tail_record_count": full_state.sequence - prefix.sequence,
            "construction_verifier_view_only": True,
            "native_evidence_authority_present": False,
            "formal_counter_eligible": False,
            "official_execution_allowed": False,
        }
    finally:
        _release_joined_owner_locked(gate_context, root_fd, directory_fd)


def _reservation_document_for_request(
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    *,
    operation_id: str,
    site_key: str,
    path: str,
    reservation_upper: int,
) -> tuple[dict[str, Any], int]:
    operation = _cid(operation_id, "V3 operation")
    site = _nonempty(site_key, "V3 site key")
    upper = _nonnegative(reservation_upper, "V3 reservation upper")
    limit = _limit(handle.profile, path)
    if limit.reducer is H1SharedReducerV3.MAX and state.outstanding[path] != 0:
        _protocol("V3 construction MAX core has an unresolved exposure")
    candidate = (
        state.charged[path] + state.outstanding[path] + upper
        if limit.reducer is H1SharedReducerV3.SUM
        else max(state.charged[path], upper)
    )
    rejected = candidate > limit.hard_cap
    rejection_request_id: Any = (
        _rejection_request_id(
            handle,
            operation_id=operation,
            site_key=site,
            path=path,
            reducer=limit.reducer.value,
            reservation_upper=upper,
            candidate=candidate,
            hard_cap=limit.hard_cap,
        )
        if rejected
        else _typed_null("CAP_NOT_EXCEEDED")
    )
    extra = {
        "operation_id": operation,
        "site_key": site,
        "path": path,
        "reducer": limit.reducer.value,
        "reservation_upper": upper,
        "admission_candidate": candidate,
        "charged_before": state.charged[path],
        "outstanding_before": state.outstanding[path],
        "durable_before_side_effect": True,
        "admission_outcome": (
            "REJECTED_BEFORE_SIDE_EFFECT" if rejected else "ADMITTED"
        ),
        "rejection_request_id": rejection_request_id,
    }
    payload = {
        **_common_record_payload(
            handle,
            state,
            schema="acfqp.k7_h1_shared_cap_reservation.v3",
            kind=(
                "REJECTION_ADMISSION_DURABLE"
                if rejected
                else "RESERVATION_DURABLE"
            ),
        ),
        **extra,
    }
    return _id_payload(
        RESERVATION_DOMAIN,
        payload,
        "h1_shared_cap_owner_v3_reservation_id",
    ), candidate


def _pair_extra(
    *,
    subject_kind: str,
    subject_id: str,
    path: str,
    reducer: str,
    reservation_upper: int,
    native_observed_value: Any,
    charged_value: int,
    value_basis: str,
    construction_exact_value_assertion: bool,
    conservative_charge: bool,
    upper_bound_violation: bool,
    control_cap_rejections: int,
) -> dict[str, Any]:
    return {
        "subject_kind": subject_kind,
        "subject_id": subject_id,
        "path": path,
        "reducer": reducer,
        "reservation_upper": reservation_upper,
        "native_observed_value": native_observed_value,
        "charged_value": charged_value,
        "value_basis": value_basis,
        "construction_exact_value_assertion": construction_exact_value_assertion,
        "native_authority_verified": False,
        "conservative_charge": conservative_charge,
        "upper_bound_violation": upper_bound_violation,
        "control_cap_rejections": control_cap_rejections,
    }


def _append_receipt_event_snapshot(
    root_fd: int,
    directory_fd: int,
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    *,
    pair_extra: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    requested_subject_id = _cid(pair_extra["subject_id"], "V3 pair subject")
    _require_pair_frontier(state, allowed_subject_id=requested_subject_id)
    receipt = next(
        (
            row
            for row in state.receipts.values()
            if row["subject_id"] == pair_extra["subject_id"]
        ),
        None,
    )
    if receipt is None:
        receipt = _append_record(
            root_fd,
            directory_fd,
            handle,
            state,
            schema="acfqp.k7_h1_shared_cap_receipt.v3",
            kind="RECEIPT_DURABLE",
            extra=pair_extra,
        )
    elif any(receipt[key] != value for key, value in pair_extra.items()):
        _protocol("V3 durable receipt conflicts with requested semantics")
    state = _replay_records_fd(directory_fd, handle)
    receipt_id = _record_id(receipt)
    event = next(
        (
            row
            for row in state.events.values()
            if row["h1_shared_cap_owner_v3_receipt_id"] == receipt_id
        ),
        None,
    )
    if event is None:
        event = _append_record(
            root_fd,
            directory_fd,
            handle,
            state,
            schema="acfqp.k7_h1_shared_cap_event.v3",
            kind="EVENT_DURABLE",
            extra={
                "h1_shared_cap_owner_v3_receipt_id": receipt_id,
                **dict(pair_extra),
            },
        )
    state = _replay_records_fd(directory_fd, handle)
    event_id = _record_id(event)
    snapshot = next(
        (
            row
            for row in state.snapshots
            if row["h1_shared_cap_owner_v3_event_id"] == event_id
        ),
        None,
    )
    if snapshot is None:
        snapshot = _append_record(
            root_fd,
            directory_fd,
            handle,
            state,
            schema="acfqp.k7_h1_shared_cap_snapshot.v3",
            kind="SNAPSHOT_DURABLE",
            extra={
                "h1_shared_cap_owner_v3_receipt_id": receipt_id,
                "h1_shared_cap_owner_v3_event_id": event_id,
                "charged_values": dict(state.charged),
                "outstanding_values": dict(state.outstanding),
                "reservation_count": len(state.reservations),
                "settlement_count": len(state.settlements),
                "conservative_settlement_count": state.conservative_settlement_count,
                "observed_overrun_count": state.observed_overrun_count,
                "control_cap_rejections": (
                    0 if state.rejection_commit_id is None else 1
                ),
                "all_settlements_nonconservative": (
                    state.conservative_settlement_count == 0
                ),
                "all_native_authorities_verified": False,
                "native_zero_eligible": False,
                "journal_replay_complete": True,
            },
        )
    _replay_records_fd(directory_fd, handle)
    return receipt, event, snapshot


def _find_pair_for_subject(
    state: _ReplayState, subject_id: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    receipt = next(
        (row for row in state.receipts.values() if row["subject_id"] == subject_id),
        None,
    )
    if receipt is None:
        return None
    receipt_id = _record_id(receipt)
    event = next(
        (
            row
            for row in state.events.values()
            if row["h1_shared_cap_owner_v3_receipt_id"] == receipt_id
        ),
        None,
    )
    if event is None:
        return None
    event_id = _record_id(event)
    snapshot = next(
        (
            row
            for row in state.snapshots
            if row["h1_shared_cap_owner_v3_event_id"] == event_id
        ),
        None,
    )
    if snapshot is None:
        return None
    return receipt, event, snapshot


def _incomplete_pair_frontier(
    state: _ReplayState,
) -> tuple[str, str, str] | None:
    """Return the sole recoverable lifecycle/pair frontier, if present."""

    events_by_receipt: dict[str, dict[str, Any]] = {}
    for event in state.events.values():
        receipt_id = _cid(
            event["h1_shared_cap_owner_v3_receipt_id"], "V3 receipt"
        )
        if receipt_id in events_by_receipt:
            _protocol("V3 receipt has more than one semantic event")
        events_by_receipt[receipt_id] = event

    snapshots_by_event: dict[str, dict[str, Any]] = {}
    for snapshot in state.snapshots:
        event_id = _cid(snapshot["h1_shared_cap_owner_v3_event_id"], "V3 event")
        if event_id in snapshots_by_event:
            _protocol("V3 event has more than one durable snapshot")
        snapshots_by_event[event_id] = snapshot

    incomplete: list[tuple[str, str, str]] = []
    for reservation_id, cell in state.cells.items():
        if reservation_id not in state.evidence:
            incomplete.append((reservation_id, "NATIVE_CELL", _record_id(cell)))
    for reservation_id, evidence in state.evidence.items():
        if reservation_id not in state.settlements:
            incomplete.append(
                (reservation_id, "NATIVE_EVIDENCE", _record_id(evidence))
            )
    receipt_subjects = {row["subject_id"] for row in state.receipts.values()}
    for settlement in state.settlements.values():
        settlement_id = _record_id(settlement)
        if settlement_id not in receipt_subjects:
            incomplete.append((settlement_id, "SETTLEMENT", settlement_id))
    for receipt_id, receipt in state.receipts.items():
        event = events_by_receipt.get(receipt_id)
        if event is None:
            incomplete.append((receipt["subject_id"], "RECEIPT", receipt_id))
            continue
        event_id = _record_id(event)
        if event_id not in snapshots_by_event:
            incomplete.append((receipt["subject_id"], "EVENT", event_id))

    if len(incomplete) > 1:
        _protocol("V3 journal contains multiple incomplete semantic pairs")
    if not incomplete:
        return None
    subject_id, stage, frontier_id = incomplete[0]
    if state.head_id != frontier_id:
        _protocol("V3 incomplete semantic pair is no longer the journal head")
    return _cid(subject_id, "V3 pair subject"), stage, frontier_id


def _require_pair_frontier(
    state: _ReplayState,
    *,
    allowed_subject_id: str | None,
) -> None:
    frontier = _incomplete_pair_frontier(state)
    if frontier is None:
        return
    subject_id, _stage, _frontier_id = frontier
    if allowed_subject_id is None or subject_id != allowed_subject_id:
        _protocol(
            "V3 incomplete lifecycle/receipt unit blocks unrelated appends"
        )


def _require_next_pair_record(
    state: _ReplayState,
    document: Mapping[str, Any],
) -> None:
    if state.rejection_admissions and state.rejection_commit_id is None:
        admission = next(iter(state.rejection_admissions.values()))
        if (
            state.head_id == _record_id(admission)
            and (
                document.get("schema")
                != "acfqp.k7_h1_shared_cap_receipt.v3"
                or document.get("subject_kind") != "CAP_REJECTION"
            )
        ):
            _protocol(
                "V3 rejection admission was not immediately followed by its receipt"
            )
    frontier = _incomplete_pair_frontier(state)
    if frontier is None:
        return
    _subject_id, stage, frontier_id = frontier
    if stage == "NATIVE_CELL":
        if (
            document.get("schema")
            != "acfqp.k7_h1_shared_cap_native_evidence.v3"
            or document.get("h1_shared_cap_owner_v3_native_cell_id")
            != frontier_id
        ):
            _protocol("V3 native cell was not immediately followed by its evidence")
        return
    if stage == "NATIVE_EVIDENCE":
        if (
            document.get("schema") != "acfqp.k7_h1_shared_cap_settlement.v3"
            or document.get("h1_shared_cap_owner_v3_native_evidence_id")
            != frontier_id
        ):
            _protocol("V3 native evidence was not immediately followed by settlement")
        return
    if stage == "SETTLEMENT":
        if (
            document.get("schema") != "acfqp.k7_h1_shared_cap_receipt.v3"
            or document.get("subject_kind") != "SETTLEMENT"
            or document.get("subject_id") != frontier_id
        ):
            _protocol("V3 settlement was not immediately followed by its receipt")
        return
    if stage == "RECEIPT":
        if (
            document.get("schema") != "acfqp.k7_h1_shared_cap_event.v3"
            or document.get("h1_shared_cap_owner_v3_receipt_id") != frontier_id
        ):
            _protocol("V3 receipt was not immediately followed by its event")
        return
    if (
        document.get("schema") != "acfqp.k7_h1_shared_cap_snapshot.v3"
        or document.get("h1_shared_cap_owner_v3_event_id") != frontier_id
    ):
        _protocol("V3 event was not immediately followed by its snapshot")


def _require_durable_reservation(
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    reservation: H1SharedReservationV3,
) -> tuple[str, dict[str, Any]]:
    if type(reservation) is not H1SharedReservationV3:
        _fail("V3 settlement requires one exact reservation wrapper")
    try:
        document = dict(reservation.document)
        reservation_id = reservation.reservation_id
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7H1SharedCapOwnerV3Error(
            "V3 reservation wrapper is malformed"
        ) from error
    durable = state.reservations.get(reservation_id)
    if durable is None or durable != document:
        _protocol("V3 reservation is foreign, stale, or mutated")
    if (
        durable["h1_shared_cap_owner_v3_runtime_id"] != handle.runtime_id
        or durable["h1_shared_cap_profile_core_v3_id"] != handle.profile.profile_id
    ):
        _protocol("V3 reservation crossed its runtime/profile")
    return reservation_id, durable


def _rejection_request_id(
    handle: H1SharedCapOwnerV3Handle,
    *,
    operation_id: str,
    site_key: str,
    path: str,
    reducer: str,
    reservation_upper: int,
    candidate: int,
    hard_cap: int,
) -> str:
    payload = canonical_json_bytes(
        {
            "schema": "acfqp.k7_h1_shared_cap_rejection_request.v3",
            "h1_shared_cap_owner_v3_runtime_id": handle.runtime_id,
            "operation_id": operation_id,
            "site_key": site_key,
            "path": path,
            "reducer": reducer,
            "reservation_upper": reservation_upper,
            "candidate": candidate,
            "hard_cap": hard_cap,
            "reason_code": "SHARED_CAP_EXHAUSTED",
        }
    )
    return hashlib.sha256(
        b"acfqp:h1-shared-cap-rejection-request:v3\x00" + payload
    ).hexdigest()


def _rejection_pair_extra(
    commit: rejection_v1.H1AttemptRejectionCommitV1,
) -> dict[str, Any]:
    return _pair_extra(
        subject_kind="CAP_REJECTION",
        subject_id=commit.commit_id,
        path=commit.path,
        reducer=PATH_REDUCERS[commit.path],
        reservation_upper=commit.reservation_upper,
        native_observed_value=0,
        charged_value=0,
        value_basis=H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO.value,
        construction_exact_value_assertion=True,
        conservative_charge=False,
        upper_bound_violation=False,
        control_cap_rejections=1,
    )


def _require_rejection_gate_shape(
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    commit: rejection_v1.H1AttemptRejectionCommitV1,
    *,
    require_current_prestate: bool,
) -> H1SharedCapLimitV3:
    profile = handle.profile
    if (
        commit.logical_occurrence_id != profile.logical_occurrence_id
        or commit.route_attempt_id != profile.route_attempt_id
        or commit.decision_point_id != profile.decision_point_id
        or commit.transaction_id != profile.transaction_id
        or commit.shared_owner_profile_core_id != profile.profile_id
    ):
        _protocol("V3 cap rejection crossed its owner decision context")
    if (
        commit.source_kind
        is not rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER
        or commit.limit_kind
        is not rejection_v1.H1RejectionLimitKindV1.SHARED_PATH
        or commit.reason_code != "SHARED_CAP_EXHAUSTED"
    ):
        _protocol("V3 owner cannot verify a non-shared-owner rejection")
    limit = _limit(profile, commit.path)
    if (
        commit.hard_cap != limit.hard_cap
        or commit.candidate is None
        or commit.candidate <= commit.hard_cap
    ):
        _protocol("V3 shared-owner rejection differs from its profile cap")
    if require_current_prestate:
        if state.observed_overrun_count:
            _protocol("V3 poisoned owner cannot originate a cap rejection")
        _require_pair_frontier(state, allowed_subject_id=None)
        if limit.reducer is H1SharedReducerV3.MAX and state.outstanding[commit.path]:
            _protocol("V3 MAX rejection has an unresolved prior exposure")
        expected_candidate = (
            state.charged[commit.path]
            + state.outstanding[commit.path]
            + commit.reservation_upper
            if limit.reducer is H1SharedReducerV3.SUM
            else max(state.charged[commit.path], commit.reservation_upper)
        )
        if commit.candidate != expected_candidate:
            _protocol("V3 rejection candidate differs from current owner prestate")
    return limit


def _require_rejection_context(
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    commit: rejection_v1.H1AttemptRejectionCommitV1,
) -> None:
    limit = _require_rejection_gate_shape(
        handle,
        state,
        commit,
        require_current_prestate=False,
    )
    admission = state.rejection_admissions.get(commit.rejection_request_id)
    if admission is None:
        _protocol("V3 shared-owner rejection lacks prior owner admission evidence")
    if (
        admission["site_key"] != commit.site_key
        or admission["path"] != commit.path
        or admission["reducer"] != limit.reducer.value
        or admission["reservation_upper"] != commit.reservation_upper
        or admission["admission_candidate"] != commit.candidate
        or admission["rejection_request_id"] != commit.rejection_request_id
    ):
        _protocol("V3 shared-owner rejection differs from its admission evidence")


def _append_rejection_pair_locked(
    root_fd: int,
    directory_fd: int,
    handle: H1SharedCapOwnerV3Handle,
    state: _ReplayState,
    commit: rejection_v1.H1AttemptRejectionCommitV1,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _require_rejection_context(handle, state, commit)
    if state.rejection_commit_id not in {None, commit.commit_id}:
        _protocol("V3 owner journal contains a different cap rejection")
    return _append_receipt_event_snapshot(
        root_fd,
        directory_fd,
        handle,
        state,
        pair_extra=_rejection_pair_extra(commit),
    )


def _ack_rejection_pair(
    handle: H1SharedCapOwnerV3Handle,
    commit: rejection_v1.H1AttemptRejectionCommitV1,
    pair: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> H1SharedCapRejectionResultV3:
    receipt, event, snapshot = pair
    gate = _gate_for(handle)
    ack = rejection_v1.acknowledge_h1_attempt_rejection_v1(
        gate,
        commit,
        writer_role=rejection_v1.H1AttemptRejectionWriterRoleV1.BROKER,
        shared_owner_receipt_id=_record_id(receipt),
        shared_owner_event_id=_record_id(event),
        shared_owner_snapshot_id=_record_id(snapshot),
    )
    return H1SharedCapRejectionResultV3(commit, receipt, event, snapshot, ack)


def synchronize_h1_shared_cap_rejection_v3(
    handle: H1SharedCapOwnerV3Handle,
) -> H1SharedCapRejectionResultV3 | None:
    _guard_key, _same_runtime_guard, same_gate_guard = _active_guard_for_gate(handle)
    if same_gate_guard:
        _protocol(
            "V3 cannot synchronize rejection while its side-effect guard is active"
        )
    (
        gate_context,
        root_fd,
        directory_fd,
        state,
        gate_snapshot,
        gate_join,
    ) = _acquire_joined_owner_locked(handle)
    try:
        commit = gate_snapshot.commit
        if commit is None:
            return None
        if (
            gate_join.external_attempt_rejection
            or gate_join.status
            is H1SharedGateOwnerJoinStatusV3.LOCAL_COMMIT_AWAITING_ADMISSION
        ):
            return None
        pair = _append_rejection_pair_locked(
            root_fd,
            directory_fd,
            handle,
            state,
            commit,
        )
    finally:
        _release_joined_owner_locked(gate_context, root_fd, directory_fd)
    return _ack_rejection_pair(handle, commit, pair)


def _recover_shared_owner_rejection_for_exact_request(
    handle: H1SharedCapOwnerV3Handle,
    *,
    operation_id: str,
    site_key: str,
    path: str,
    reservation_upper: int,
) -> H1SharedCapRejectionResultV3 | None:
    (
        gate_context,
        root_fd,
        directory_fd,
        state,
        gate_snapshot,
        gate_join,
    ) = _acquire_joined_owner_locked(handle)
    pair: tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None = None
    commit = gate_snapshot.commit
    try:
        if (
            commit is None
            or gate_join.external_attempt_rejection
            or gate_join.status
            is not H1SharedGateOwnerJoinStatusV3.LOCAL_COMMIT_AWAITING_ADMISSION
        ):
            return None
        _require_pair_frontier(state, allowed_subject_id=None)
        document, candidate = _reservation_document_for_request(
            handle,
            state,
            operation_id=operation_id,
            site_key=site_key,
            path=path,
            reservation_upper=reservation_upper,
        )
        limit = _limit(handle.profile, path)
        if (
            candidate <= limit.hard_cap
            or document["record_kind"] != "REJECTION_ADMISSION_DURABLE"
            or document["rejection_request_id"] != commit.rejection_request_id
            or commit.site_key != site_key
            or commit.path != path
            or commit.reservation_upper != reservation_upper
            or commit.candidate != candidate
            or commit.hard_cap != limit.hard_cap
        ):
            _protocol("V3 exact rejection recovery request differs from gate commit")
        _append_record(
            root_fd,
            directory_fd,
            handle,
            state,
            schema="acfqp.k7_h1_shared_cap_reservation.v3",
            kind="REJECTION_ADMISSION_DURABLE",
            extra={
                key: value
                for key, value in document.items()
                if key
                in _EXTRA_FIELDS[
                    "acfqp.k7_h1_shared_cap_reservation.v3"
                ]
            },
        )
        state = _replay_records_fd(directory_fd, handle)
        pair = _append_rejection_pair_locked(
            root_fd,
            directory_fd,
            handle,
            state,
            commit,
        )
    finally:
        _release_joined_owner_locked(gate_context, root_fd, directory_fd)
    if pair is None:  # pragma: no cover - guarded return above
        return None
    return _ack_rejection_pair(handle, commit, pair)


def _lookup_existing_reservation_after_rejection(
    handle: H1SharedCapOwnerV3Handle,
    *,
    operation_id: str,
    site_key: str,
    path: str,
    reservation_upper: int,
) -> H1SharedReservationV3 | None:
    (
        gate_context,
        root_fd,
        directory_fd,
        state,
        _gate_snapshot,
        _gate_join,
    ) = _acquire_joined_owner_locked(handle)
    try:
        reservation_id = state.reservation_by_operation.get(operation_id)
        if reservation_id is None:
            return None
        reservation = state.reservations[reservation_id]
        if (
            reservation["site_key"] != site_key
            or reservation["path"] != path
            or reservation["reservation_upper"] != reservation_upper
        ):
            _protocol("V3 closed-attempt reservation lookup changed semantics")
        return H1SharedReservationV3(reservation)
    finally:
        _release_joined_owner_locked(gate_context, root_fd, directory_fd)


def _recover_pending_admitted_reservation_after_rejection(
    handle: H1SharedCapOwnerV3Handle,
    *,
    operation_id: str,
    site_key: str,
    path: str,
    reservation_upper: int,
) -> H1SharedReservationV3 | None:
    """Finish only the exact pre-rejection reservation named by owner P.

    The pending cursor is durable evidence that this append was admitted while
    the attempt gate was OPEN.  A later transaction may close the attempt
    before the record publication resumes.  Only caller operands that recreate
    the exact pending content ID may complete that already-admitted append.
    """

    (
        gate_context,
        root_fd,
        directory_fd,
        state,
        _gate_snapshot,
        _gate_join,
    ) = _acquire_joined_owner_locked(handle)
    try:
        if state.pending_cursor is None:
            return None
        document, candidate = _reservation_document_for_request(
            handle,
            state,
            operation_id=operation_id,
            site_key=site_key,
            path=path,
            reservation_upper=reservation_upper,
        )
        limit = _limit(handle.profile, path)
        if candidate > limit.hard_cap or document["record_kind"] != "RESERVATION_DURABLE":
            return None
        reservation_id = document["h1_shared_cap_owner_v3_reservation_id"]
        expected_pending = (document["sequence"], reservation_id)
        if state.pending_cursor != expected_pending:
            _protocol(
                "V3 closed attempt has a different unresolved pending owner append"
            )
        appended = _append_record(
            root_fd,
            directory_fd,
            handle,
            state,
            schema="acfqp.k7_h1_shared_cap_reservation.v3",
            kind="RESERVATION_DURABLE",
            extra={
                key: value
                for key, value in document.items()
                if key
                in _EXTRA_FIELDS["acfqp.k7_h1_shared_cap_reservation.v3"]
            },
        )
        _replay_records_fd(directory_fd, handle)
        return H1SharedReservationV3(appended)
    finally:
        _release_joined_owner_locked(gate_context, root_fd, directory_fd)


def reserve_h1_shared_cap_owner_v3(
    handle: H1SharedCapOwnerV3Handle,
    *,
    operation_id: str,
    site_key: str,
    path: str,
    reservation_upper: int,
) -> H1SharedReservationV3:
    _guard_key, _same_runtime_guard, same_gate_guard = _active_guard_for_gate(handle)
    if same_gate_guard:
        _protocol(
            "V3 cannot reserve recursively while its side-effect guard is active"
        )
    operation = _cid(operation_id, "V3 operation")
    site = _nonempty(site_key, "V3 site key")
    upper = _nonnegative(reservation_upper, "V3 reservation upper")
    limit = _limit(handle.profile, path)
    gate = _gate_for(handle)
    rejection_commit: rejection_v1.H1AttemptRejectionCommitV1 | None = None
    rejection_pair: tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None = None
    try:
        with rejection_v1.hold_h1_attempt_gate_open_for_admission_v1(
            gate
        ) as admission:
            root_fd, directory_fd, state = _require_handle_locked(handle)
            try:
                _require_owner_open_join(state)
                existing_id = state.reservation_by_operation.get(operation)
                if existing_id is not None:
                    existing = state.reservations[existing_id]
                    if (
                        existing["site_key"] != site
                        or existing["path"] != path
                        or existing["reservation_upper"] != upper
                    ):
                        _protocol("V3 operation ID was reused with different semantics")
                    return H1SharedReservationV3(existing)
                if state.observed_overrun_count:
                    _protocol("V3 owner is durably poisoned by an observed overrun")
                _require_pair_frontier(state, allowed_subject_id=None)
                document, candidate = _reservation_document_for_request(
                    handle,
                    state,
                    operation_id=operation,
                    site_key=site,
                    path=path,
                    reservation_upper=upper,
                )
                if state.pending_cursor is not None:
                    if (
                        candidate > limit.hard_cap
                        or state.pending_cursor
                        != (
                            document["sequence"],
                            document["h1_shared_cap_owner_v3_reservation_id"],
                        )
                    ):
                        _protocol(
                            "V3 unresolved pending append forbids a different admission"
                        )
                    appended = _append_record(
                        root_fd,
                        directory_fd,
                        handle,
                        state,
                        schema="acfqp.k7_h1_shared_cap_reservation.v3",
                        kind="RESERVATION_DURABLE",
                        extra={
                            key: value
                            for key, value in document.items()
                            if key
                            in _EXTRA_FIELDS[
                                "acfqp.k7_h1_shared_cap_reservation.v3"
                            ]
                        },
                    )
                    _replay_records_fd(directory_fd, handle)
                    return H1SharedReservationV3(appended)
                if candidate > limit.hard_cap:
                    request_id = _cid(
                        document["rejection_request_id"],
                        "V3 rejection request",
                    )
                    rejection_commit = (
                        rejection_v1.commit_h1_attempt_rejection_with_admission_lease_v1(
                            admission,
                            writer_role=(
                                rejection_v1.H1AttemptRejectionWriterRoleV1.BROKER
                            ),
                            decision_point_id=handle.profile.decision_point_id,
                            transaction_id=handle.profile.transaction_id,
                            shared_owner_profile_core_id=handle.profile.profile_id,
                            rejection_request_id=request_id,
                            source_kind=(
                                rejection_v1.H1RejectionSourceKindV1.SHARED_OWNER
                            ),
                            site_key=site,
                            path=path,
                            limit_kind=(
                                rejection_v1.H1RejectionLimitKindV1.SHARED_PATH
                            ),
                            reservation_upper=upper,
                            candidate=candidate,
                            hard_cap=limit.hard_cap,
                            reason_code="SHARED_CAP_EXHAUSTED",
                        )
                    )
                    _append_record(
                        root_fd,
                        directory_fd,
                        handle,
                        state,
                        schema="acfqp.k7_h1_shared_cap_reservation.v3",
                        kind="REJECTION_ADMISSION_DURABLE",
                        extra={
                            key: value
                            for key, value in document.items()
                            if key
                            in _EXTRA_FIELDS[
                                "acfqp.k7_h1_shared_cap_reservation.v3"
                            ]
                        },
                    )
                    state = _replay_records_fd(directory_fd, handle)
                    rejection_pair = _append_rejection_pair_locked(
                        root_fd,
                        directory_fd,
                        handle,
                        state,
                        rejection_commit,
                    )
                else:
                    appended = _append_record(
                        root_fd,
                        directory_fd,
                        handle,
                        state,
                        schema="acfqp.k7_h1_shared_cap_reservation.v3",
                        kind=document["record_kind"],
                        extra={
                            key: value
                            for key, value in document.items()
                            if key in _EXTRA_FIELDS[
                                "acfqp.k7_h1_shared_cap_reservation.v3"
                            ]
                        },
                    )
                    _replay_records_fd(directory_fd, handle)
                    return H1SharedReservationV3(appended)
            finally:
                os.close(directory_fd)
                os.close(root_fd)
    except rejection_v1.H1AttemptRejectedV1 as error:
        result = synchronize_h1_shared_cap_rejection_v3(handle)
        if result is None:
            existing = _lookup_existing_reservation_after_rejection(
                handle,
                operation_id=operation,
                site_key=site,
                path=path,
                reservation_upper=upper,
            )
            if existing is not None:
                return existing
            recovered_pending = _recover_pending_admitted_reservation_after_rejection(
                handle,
                operation_id=operation,
                site_key=site,
                path=path,
                reservation_upper=upper,
            )
            if recovered_pending is not None:
                return recovered_pending
            result = _recover_shared_owner_rejection_for_exact_request(
                handle,
                operation_id=operation,
                site_key=site,
                path=path,
                reservation_upper=upper,
            )
        raise H1SharedCapOwnerV3Rejected(
            "attempt-wide cap rejection forbids a later reservation",
            result,
        ) from error
    if rejection_commit is None or rejection_pair is None:  # pragma: no cover
        _protocol("V3 cap rejection path lost its durable result")
    result = _ack_rejection_pair(handle, rejection_commit, rejection_pair)
    raise H1SharedCapOwnerV3Rejected(
        "V3 shared-cap admission exceeded its hard cap",
        result,
    )


@contextmanager
def hold_h1_shared_cap_owner_v3_side_effect(
    handle: H1SharedCapOwnerV3Handle,
    reservation: H1SharedReservationV3,
) -> Iterator[H1SharedSideEffectStartV3]:
    guard_key, _same_runtime_guard, same_gate_guard = _active_guard_for_gate(handle)
    if same_gate_guard:
        _protocol("V3 side-effect guard cannot be nested for one attempt gate")
    gate = _gate_for(handle)
    with rejection_v1.hold_h1_attempt_gate_open_for_side_effect_v1(gate):
        root_fd, directory_fd, state = _require_handle_locked(handle)
        try:
            _require_owner_open_join(state)
            if state.rejection_admissions:
                _protocol(
                    "V3 pending rejection admission forbids a later side effect"
                )
            reservation_id, durable = _require_durable_reservation(
                handle,
                state,
                reservation,
            )
            _require_pair_frontier(state, allowed_subject_id=reservation_id)
            if state.observed_overrun_count:
                _protocol("V3 owner is durably poisoned by an observed overrun")
            if reservation_id in state.settlements:
                _protocol("V3 settled reservation cannot start another side effect")
            if reservation_id in state.cells:
                _protocol("V3 side effect already started or was cancelled")
            cell = _append_record(
                root_fd,
                directory_fd,
                handle,
                state,
                schema="acfqp.k7_h1_shared_cap_native_cell.v3",
                kind="NATIVE_CELL_DURABLE",
                extra={
                    "h1_shared_cap_owner_v3_reservation_id": reservation_id,
                    "operation_id": durable["operation_id"],
                    "path": durable["path"],
                    "lifecycle_state": (
                        H1SharedNativeStateV3.SIDE_EFFECT_STARTED.value
                    ),
                    "durable_before_native_effect": True,
                },
            )
            _replay_records_fd(directory_fd, handle)
        finally:
            os.close(directory_fd)
            os.close(root_fd)
        active = _ACTIVE_SIDE_EFFECT_GUARDS.get()
        token = _ACTIVE_SIDE_EFFECT_GUARDS.set(active | {guard_key})
        try:
            yield H1SharedSideEffectStartV3(cell)
        finally:
            _ACTIVE_SIDE_EFFECT_GUARDS.reset(token)


def settle_h1_shared_cap_owner_v3(
    handle: H1SharedCapOwnerV3Handle,
    reservation: H1SharedReservationV3,
    *,
    value_basis: H1SharedValueBasisV3,
    native_observed_value: int | None,
    evidence_source_id: str,
) -> H1SharedSettlementResultV3:
    try:
        basis = H1SharedValueBasisV3(value_basis)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1SharedCapOwnerV3Error(
            "V3 settlement value basis is invalid"
        ) from error
    evidence_source = _cid(evidence_source_id, "V3 native evidence source")
    gate_context: Any | None
    _guard_key, same_runtime_guard, same_gate_guard = _active_guard_for_gate(handle)
    if same_gate_guard and not same_runtime_guard:
        _protocol(
            "V3 cannot settle another transaction while the attempt gate is guarded"
        )
    if same_runtime_guard:
        gate_context = None
        root_fd, directory_fd, state = _require_handle_locked(handle)
        _require_owner_open_join(state)
    else:
        (
            gate_context,
            root_fd,
            directory_fd,
            state,
            _gate_snapshot,
            gate_join,
        ) = _acquire_joined_owner_locked(handle)
    try:
        reservation_id, durable = _require_durable_reservation(
            handle,
            state,
            reservation,
        )
        _require_value_basis_path(basis, durable["path"])
        recovering_pending_start = False
        if state.pending_cursor is not None and reservation_id not in state.cells:
            pending_start = _next_record_document(
                handle,
                state,
                schema="acfqp.k7_h1_shared_cap_native_cell.v3",
                kind="NATIVE_CELL_DURABLE",
                extra={
                    "h1_shared_cap_owner_v3_reservation_id": reservation_id,
                    "operation_id": durable["operation_id"],
                    "path": durable["path"],
                    "lifecycle_state": (
                        H1SharedNativeStateV3.SIDE_EFFECT_STARTED.value
                    ),
                    "durable_before_native_effect": True,
                },
            )
            recovering_pending_start = state.pending_cursor == (
                pending_start["sequence"],
                pending_start["h1_shared_cap_owner_v3_native_cell_id"],
            )
            if (
                recovering_pending_start
                and basis
                is not H1SharedValueBasisV3.CONSERVATIVE_RESERVATION_UPPER
            ):
                _protocol(
                    "V3 ambiguous pending start requires conservative settlement"
                )
        existing_settlement = state.settlements.get(reservation_id)
        if (
            gate_context is not None
            and gate_join.status
            is H1SharedGateOwnerJoinStatusV3.LOCAL_COMMIT_AWAITING_ADMISSION
            and existing_settlement is None
        ):
            _protocol(
                "V3 rejection admission must recover before a new local settlement"
            )
        semantics = _native_semantics(
            basis,
            reservation_upper=durable["reservation_upper"],
            native_observed_value=native_observed_value,
        )
        native_state, encoded_native, charged, exact, conservative, overrun = semantics

        lifecycle_state = (
            H1SharedNativeStateV3.KNOWN_NOT_STARTED
            if basis is H1SharedValueBasisV3.KNOWN_NOT_STARTED_ZERO
            else H1SharedNativeStateV3.SIDE_EFFECT_STARTED
        )
        cell_extra = {
            "h1_shared_cap_owner_v3_reservation_id": reservation_id,
            "operation_id": durable["operation_id"],
            "path": durable["path"],
            "lifecycle_state": lifecycle_state.value,
            "durable_before_native_effect": True,
        }
        cell = state.cells.get(reservation_id)
        if cell is None:
            if (
                lifecycle_state is H1SharedNativeStateV3.SIDE_EFFECT_STARTED
                and not recovering_pending_start
            ):
                _protocol(
                    "V3 observed settlement lacks a durable side-effect start"
                )
            cell = _append_record(
                root_fd,
                directory_fd,
                handle,
                state,
                schema="acfqp.k7_h1_shared_cap_native_cell.v3",
                kind="NATIVE_CELL_DURABLE",
                extra=cell_extra,
            )
            state = _replay_records_fd(directory_fd, handle)
        elif any(cell[key] != value for key, value in cell_extra.items()):
            _protocol("V3 side-effect lifecycle cannot change at settlement")

        evidence_extra = {
            "h1_shared_cap_owner_v3_reservation_id": reservation_id,
            "h1_shared_cap_owner_v3_native_cell_id": _record_id(cell),
            "operation_id": durable["operation_id"],
            "path": durable["path"],
            "value_basis": basis.value,
            "native_observed_value": encoded_native,
            "charged_value": charged,
            "construction_exact_value_assertion": exact,
            "native_authority_verified": False,
            "evidence_source_authority_verified": False,
            "conservative_charge": conservative,
            "upper_bound_violation": overrun,
            "evidence_source_id": evidence_source,
        }
        evidence = state.evidence.get(reservation_id)
        if evidence is None:
            evidence = _append_record(
                root_fd,
                directory_fd,
                handle,
                state,
                schema="acfqp.k7_h1_shared_cap_native_evidence.v3",
                kind="NATIVE_EVIDENCE_DURABLE",
                extra=evidence_extra,
            )
            state = _replay_records_fd(directory_fd, handle)
        elif any(evidence[key] != value for key, value in evidence_extra.items()):
            _protocol("V3 native-evidence retry semantics changed")

        settlement = state.settlements.get(reservation_id)
        if settlement is None:
            limit = _limit(handle.profile, durable["path"])
            charged_before = state.charged[durable["path"]]
            charged_after = (
                charged_before + charged
                if limit.reducer is H1SharedReducerV3.SUM
                else max(charged_before, charged)
            )
            outstanding_before = state.outstanding[durable["path"]]
            settlement_extra = {
                "h1_shared_cap_owner_v3_reservation_id": reservation_id,
                "h1_shared_cap_owner_v3_native_evidence_id": _record_id(evidence),
                "operation_id": durable["operation_id"],
                "path": durable["path"],
                "reducer": limit.reducer.value,
                "value_basis": basis.value,
                "native_observed_value": encoded_native,
                "charged_value": charged,
                "reservation_upper": durable["reservation_upper"],
                "charged_before": charged_before,
                "charged_after": charged_after,
                "outstanding_before": outstanding_before,
                "outstanding_after": (
                    outstanding_before - durable["reservation_upper"]
                ),
                "single_spend": True,
            }
            settlement = _append_record(
                root_fd,
                directory_fd,
                handle,
                state,
                schema="acfqp.k7_h1_shared_cap_settlement.v3",
                kind="SETTLEMENT_DURABLE",
                extra=settlement_extra,
            )
            state = _replay_records_fd(directory_fd, handle)
        else:
            if (
                settlement["h1_shared_cap_owner_v3_native_evidence_id"]
                != _record_id(evidence)
                or settlement["value_basis"] != basis.value
                or settlement["native_observed_value"] != encoded_native
                or settlement["charged_value"] != charged
            ):
                _protocol("V3 settlement retry semantics changed")
        historic_pair = _find_pair_for_subject(state, _record_id(settlement))
        if historic_pair is not None:
            receipt, event, snapshot = historic_pair
        else:
            pair_extra = _pair_extra(
                subject_kind="SETTLEMENT",
                subject_id=_record_id(settlement),
                path=settlement["path"],
                reducer=settlement["reducer"],
                reservation_upper=settlement["reservation_upper"],
                native_observed_value=settlement["native_observed_value"],
                charged_value=settlement["charged_value"],
                value_basis=settlement["value_basis"],
                construction_exact_value_assertion=evidence["construction_exact_value_assertion"],
                conservative_charge=evidence["conservative_charge"],
                upper_bound_violation=evidence["upper_bound_violation"],
                control_cap_rejections=(
                    0 if state.rejection_commit_id is None else 1
                ),
            )
            receipt, event, snapshot = _append_receipt_event_snapshot(
                root_fd,
                directory_fd,
                handle,
                state,
                pair_extra=pair_extra,
            )
        result = H1SharedSettlementResultV3(
            H1SharedReservationV3(durable),
            cell,
            evidence,
            settlement,
            receipt,
            event,
            snapshot,
        )
    finally:
        if gate_context is None:
            os.close(directory_fd)
            os.close(root_fd)
        else:
            _release_joined_owner_locked(gate_context, root_fd, directory_fd)
    if overrun:
        raise H1SharedCapOwnerV3ObservedOverrun(
            "V3 observed overrun exceeded its reservation/cap without clipping",
            result,
        )
    return result


__all__ = (
    "ConstructionK7H1SharedCapOwnerV3Error",
    "FORMAL_ACTUAL_COMPLIANCE_ELIGIBLE",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_WORK_VECTOR_ISSUED",
    "H1SharedCapLimitV3",
    "H1SharedCapOwnerV3Handle",
    "H1SharedCapOwnerV3ObservedOverrun",
    "H1SharedCapOwnerV3ProtocolFailure",
    "H1SharedCapOwnerV3Rejected",
    "H1SharedCapOwnerV3SourceManifest",
    "H1SharedCapProfileCoreV3",
    "H1SharedCapRejectionResultV3",
    "H1SharedGateOwnerJoinStatusV3",
    "H1SharedNativeStateV3",
    "H1SharedReducerV3",
    "H1SharedReservationV3",
    "H1SharedSideEffectStartV3",
    "H1SharedSettlementResultV3",
    "H1SharedValueBasisV3",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PATH_REDUCERS",
    "PROFILE_KEY",
    "PRODUCTION_EXECUTION_AUTHORIZED",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SHARED_RESOURCE_PATHS",
    "freeze_h1_shared_cap_owner_v3_source_manifest",
    "freeze_h1_shared_cap_profile_core_v3",
    "hold_h1_shared_cap_owner_v3_side_effect",
    "initialize_h1_shared_cap_owner_v3",
    "inspect_h1_shared_cap_owner_v3_record_index",
    "inspect_h1_shared_cap_owner_v3_record_prefix",
    "open_h1_shared_cap_owner_v3",
    "replay_h1_shared_cap_owner_v3",
    "reserve_h1_shared_cap_owner_v3",
    "settle_h1_shared_cap_owner_v3",
    "synchronize_h1_shared_cap_rejection_v3",
)
