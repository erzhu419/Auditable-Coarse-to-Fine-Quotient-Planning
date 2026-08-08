"""Durable attempt-wide one-shot cap-rejection journal (construction V1).

The gate gives the shared owner, business engine and fallback engine one common
route-attempt rejection slot.  Freezing the attempt-scope spec first consumes a
base-level allocation intent keyed only by ``route_attempt_id``; decision-point,
transaction and owner-profile-core identities belong to the eventual rejection
request, not to a second gate.  The allocation commit pins the gate and
coordination-lock inodes plus an append-only high-water cursor inode and
genesis token, so deletion or path replacement cannot silently reopen the slot.

It publishes a full canonical commit first as ``intent.json`` and then creates
``commit.json`` as an atomic hard link to the same inode.  A crash after intent
publication can therefore complete only that exact intent; a different second
rejection cannot replace it.  A separately durable acknowledgement binds the
owner receipt/event pair.  Cooperating native side effects hold a shared
``flock`` from the OPEN check through the effect, while rejection/recovery holds
the exclusive side, removing the former cross-process check/use window.

This module proves local filesystem mechanics only.  The broker writer's OS
credentials, unique production root, external activation chain, durable native
side-effect-start evidence, operational I/O counters and formal CounterRecord
projection are intentionally not yet bound.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import fcntl
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import stat
import threading
from typing import Any, Iterator, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_ACK_V1_DOMAIN,
    CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_COMMIT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_GATE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-B"
PROFILE_KEY = "construction_k7_h1_attempt_rejection_gate_v1"

GATE_DOMAIN = CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_GATE_V1_DOMAIN
COMMIT_DOMAIN = CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_COMMIT_V1_DOMAIN
ACK_DOMAIN = CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_ACK_V1_DOMAIN
if {GATE_DOMAIN, COMMIT_DOMAIN, ACK_DOMAIN} - PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("H1 attempt-rejection domains are not registered")

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
_GATE_FILE = "gate.json"
_INTENT_FILE = "intent.json"
_COMMIT_FILE = "commit.json"
_ACK_FILE = "ack.json"
_CURSOR_FILE = "high-water.cursor"
_LOCK_FILE = "gate.lock"
_LOCK_BYTES = b"ACFQP_H1_ATTEMPT_REJECTION_GATE_LOCK_V1\n"
_ROOT_DIRECTORY = ".acfqp-h1-attempt-rejection-v1"
_KNOWN_FILES = frozenset(
    {_GATE_FILE, _INTENT_FILE, _COMMIT_FILE, _ACK_FILE, _CURSOR_FILE, _LOCK_FILE}
)
_TEMP_PATTERN = re.compile(r"[.]tmp-[1-9][0-9]*-[0-9a-f]{32}\Z")
_MAX_DOCUMENT_BYTES = 1024 * 1024
_CURSOR_DOMAIN = "acfqp:k7-h1-attempt-rejection-high-water-cursor-record:v1"
_CONTEXT_ADMISSION_EXCLUSIVE = "ADMISSION_EXCLUSIVE"
_CONTEXT_DEPENDENT_REPLAY_EXCLUSIVE = "DEPENDENT_REPLAY_EXCLUSIVE"
_CONTEXT_SIDE_EFFECT_SHARED = "SIDE_EFFECT_SHARED"
_ACTIVE_GATE_CONTEXTS: ContextVar[tuple[tuple[str, str], ...]] = ContextVar(
    "acfqp_k7_h1_active_attempt_rejection_gate_contexts_v1",
    default=(),
)
_ALLOCATION_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "h1_attempt_rejection_gate_id",
        "gate_base_realpath",
        "gate_base_device",
        "gate_base_inode",
        "gate_directory_device",
        "gate_directory_inode",
        "gate_lock_device",
        "gate_lock_inode",
        "high_water_cursor_device",
        "high_water_cursor_inode",
        "high_water_cursor_token",
        "high_water_cursor_genesis_record_id",
        "allocation_state",
        "kernel_writer_credential_verified",
        "production_execution_authorized",
    }
)
_CURSOR_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "h1_attempt_rejection_gate_id",
        "cursor_token",
        "sequence",
        "state",
        "h1_attempt_rejection_commit_id",
        "h1_attempt_rejection_ack_id",
        "previous_cursor_record_id",
        "cursor_record_id",
    }
)


class ConstructionK7H1AttemptRejectionGateV1Error(ValueError):
    """The durable gate or one of its exact records is invalid."""


class H1AttemptSecondRejectionV1(ConstructionK7H1AttemptRejectionGateV1Error):
    """A different second rejection attempted to use the one-shot slot."""

    failure_kind = "PROTOCOL_FAILURE"
    certificate_issued = False
    infeasibility_certified = False


class H1AttemptRejectedV1(ConstructionK7H1AttemptRejectionGateV1Error):
    """The gate is durably rejected and no later side effect may start."""

    failure_kind = "SHARED_CAP_EXHAUSTED"
    certificate_issued = False
    infeasibility_certified = False


class H1AttemptRejectionInjectedCrashV1(RuntimeError):
    """Test-only crash point after a durable journal transition."""


class H1RejectionSourceKindV1(str, Enum):
    SHARED_OWNER = "SHARED_OWNER"
    BUSINESS_ENGINE = "BUSINESS_ENGINE"
    FALLBACK_ENGINE = "FALLBACK_ENGINE"


class H1RejectionLimitKindV1(str, Enum):
    SHARED_PATH = "SHARED_PATH"
    CONTROL_CAP_CHECKS = "CONTROL_CAP_CHECKS"


class H1AttemptRejectionGateStateV1(str, Enum):
    OPEN = "OPEN"
    INTENT_DURABLE = "INTENT_DURABLE"
    COMMITTED_UNACKNOWLEDGED = "COMMITTED_UNACKNOWLEDGED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


class H1AttemptRejectionCrashPointV1(str, Enum):
    NONE = "NONE"
    AFTER_INTENT_FSYNC = "AFTER_INTENT_FSYNC"
    AFTER_COMMIT_FSYNC = "AFTER_COMMIT_FSYNC"
    AFTER_ACK_FSYNC = "AFTER_ACK_FSYNC"


class H1AttemptRejectionWriterRoleV1(str, Enum):
    BROKER = "BROKER"
    WORKER = "WORKER"
    BUSINESS = "BUSINESS"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1AttemptRejectionGateV1Error(message)


def _active_gate_modes(gate_id: str) -> tuple[str, ...]:
    return tuple(
        mode
        for active_gate_id, mode in _ACTIVE_GATE_CONTEXTS.get()
        if active_gate_id == gate_id
    )


def _reject_same_gate_context_reentry(gate_id: str, api_name: str) -> None:
    modes = _active_gate_modes(gate_id)
    if modes:
        _fail(
            f"{api_name} cannot re-enter active same-gate context "
            f"{','.join(modes)}; only the active admission lease commit is allowed"
        )


def _activate_gate_context(gate_id: str, mode: str) -> Any:
    _reject_same_gate_context_reentry(gate_id, mode)
    active = _ACTIVE_GATE_CONTEXTS.get()
    return _ACTIVE_GATE_CONTEXTS.set((*active, (gate_id, mode)))


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{label} must be one nonempty exact string")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _parse_exact(raw: bytes, fields: frozenset[str], label: str) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or frozenset(document) != fields:
        _fail(f"{label} fields are not exact")
    return document


_GATE_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "logical_occurrence_id",
        "route_attempt_id",
        "gate_base_realpath",
        "gate_base_device",
        "gate_base_inode",
        "caller_pinned_lifecycle_provenance_id",
        "writer_role",
        "attempt_wide",
        "max_cap_rejections",
        "durable_commit_before_ack_required",
        "production_activation_chain_verified",
        "kernel_writer_credential_verified",
        "filesystem_durability_model_verified",
        "power_loss_recovery_empirically_verified",
        "operational_io_accounting_connected",
        "formal_counter_eligible",
        "production_execution_authorized",
        "official_execution_allowed",
        "h1_attempt_rejection_gate_id",
    }
)
_COMMIT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_attempt_rejection_gate_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "transaction_id",
        "shared_owner_profile_core_id",
        "rejection_request_id",
        "rejection_source_kind",
        "site_key",
        "path",
        "limit_kind",
        "reservation_upper",
        "candidate",
        "hard_cap",
        "reason_code",
        "side_effect_started",
        "native_existence",
        "rejection_ordinal",
        "control_cap_rejections",
        "commit_state",
        "commit_bytes_role",
        "durable_commit_requires_atomic_same_inode_pair",
        "formal_counter_eligible",
        "production_execution_authorized",
        "official_execution_allowed",
        "h1_attempt_rejection_commit_id",
    }
)
_ACK_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_attempt_rejection_gate_id",
        "h1_attempt_rejection_commit_id",
        "shared_owner_receipt_id",
        "shared_owner_event_id",
        "shared_owner_snapshot_id",
        "control_cap_rejections",
        "ack_state",
        "ack_bytes_role",
        "durable_ack_requires_gate_journal_replay",
        "formal_counter_eligible",
        "production_execution_authorized",
        "official_execution_allowed",
        "h1_attempt_rejection_ack_id",
    }
)


_SPEC_ISSUER = object()
_COMMIT_ISSUER = object()
_ACK_ISSUER = object()
_HANDLE_ISSUER = object()
_LEASE_ISSUER = object()
_REPLAY_SNAPSHOT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1AttemptRejectionGateSpecV1:
    _issuer: InitVar[object]
    logical_occurrence_id: str
    route_attempt_id: str
    gate_base_realpath: str
    gate_base_device: int
    gate_base_inode: int
    caller_pinned_lifecycle_provenance_id: str
    _gate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SPEC_ISSUER:
            _fail("attempt-rejection gate spec is issuer-created only")
        for value, label in (
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (
                self.caller_pinned_lifecycle_provenance_id,
                "caller-pinned lifecycle provenance",
            ),
        ):
            _cid(value, label)
        path = Path(_nonempty(self.gate_base_realpath, "gate base realpath"))
        if not path.is_absolute() or str(path) != self.gate_base_realpath:
            _fail("gate base realpath must be one normalized absolute path")
        _nonnegative(self.gate_base_device, "gate base device")
        _nonnegative(self.gate_base_inode, "gate base inode")
        object.__setattr__(self, "_gate_id", content_id(GATE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_attempt_rejection_gate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "gate_base_realpath": self.gate_base_realpath,
            "gate_base_device": self.gate_base_device,
            "gate_base_inode": self.gate_base_inode,
            "caller_pinned_lifecycle_provenance_id": (
                self.caller_pinned_lifecycle_provenance_id
            ),
            "writer_role": "BROKER",
            "attempt_wide": True,
            "max_cap_rejections": 1,
            "durable_commit_before_ack_required": True,
            "production_activation_chain_verified": False,
            "kernel_writer_credential_verified": False,
            "filesystem_durability_model_verified": False,
            "power_loss_recovery_empirically_verified": False,
            "operational_io_accounting_connected": False,
            "formal_counter_eligible": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def gate_id(self) -> str:
        if content_id(GATE_DOMAIN, self._payload()) != self._gate_id:
            _fail("attempt-rejection gate spec changed after issuance")
        return self._gate_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_attempt_rejection_gate_id": self.gate_id}


def freeze_h1_attempt_rejection_gate_spec_v1(
    *,
    base_directory: str | Path,
    logical_occurrence_id: str,
    route_attempt_id: str,
    caller_pinned_lifecycle_provenance_id: str,
) -> H1AttemptRejectionGateSpecV1:
    base, base_fd = _resolve_gate_base(base_directory, create=True)
    try:
        base_stat = os.fstat(base_fd)
        spec = H1AttemptRejectionGateSpecV1(
            _SPEC_ISSUER,
            logical_occurrence_id,
            route_attempt_id,
            str(base),
            base_stat.st_dev,
            base_stat.st_ino,
            caller_pinned_lifecycle_provenance_id,
        )
        _freeze_or_verify_allocation_intent(base_fd, spec)
        return spec
    finally:
        os.close(base_fd)


def _spec_from_document(document: dict[str, Any]) -> H1AttemptRejectionGateSpecV1:
    value = H1AttemptRejectionGateSpecV1(
        _SPEC_ISSUER,
        document["logical_occurrence_id"],
        document["route_attempt_id"],
        document["gate_base_realpath"],
        document["gate_base_device"],
        document["gate_base_inode"],
        document["caller_pinned_lifecycle_provenance_id"],
    )
    if value.to_document() != document:
        _fail("durable gate spec did not replay")
    return value


@dataclass(frozen=True, slots=True)
class H1AttemptRejectionCommitV1:
    _issuer: InitVar[object]
    gate_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    transaction_id: str
    shared_owner_profile_core_id: str
    rejection_request_id: str
    source_kind: H1RejectionSourceKindV1
    site_key: str
    path: str
    limit_kind: H1RejectionLimitKindV1
    reservation_upper: int
    candidate: int | None
    hard_cap: int
    reason_code: str
    _commit_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _COMMIT_ISSUER:
            _fail("attempt-rejection commit is issuer-created only")
        for value, label in (
            (self.gate_id, "rejection gate"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.decision_point_id, "decision point"),
            (self.transaction_id, "transaction"),
            (self.shared_owner_profile_core_id, "shared-owner profile core"),
            (self.rejection_request_id, "rejection request"),
        ):
            _cid(value, label)
        try:
            object.__setattr__(self, "source_kind", H1RejectionSourceKindV1(self.source_kind))
            object.__setattr__(self, "limit_kind", H1RejectionLimitKindV1(self.limit_kind))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1AttemptRejectionGateV1Error(
                "rejection source/limit kind is invalid"
            ) from error
        _nonempty(self.site_key, "rejection site")
        if self.path not in SHARED_RESOURCE_PATHS:
            _fail("rejection path is not one of the nine shared resources")
        _nonnegative(self.reservation_upper, "rejection reservation")
        _nonnegative(self.hard_cap, "rejection hard cap")
        _nonempty(self.reason_code, "rejection reason code")
        if self.limit_kind is H1RejectionLimitKindV1.SHARED_PATH:
            if type(self.candidate) is not int or self.candidate <= self.hard_cap:
                _fail("shared-path rejection candidate must exceed the hard cap")
        elif self.candidate is not None:
            _fail("control-check rejection candidate must be typed not applicable")
        object.__setattr__(self, "_commit_id", content_id(COMMIT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_attempt_rejection_commit.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_attempt_rejection_gate_id": self.gate_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
            "shared_owner_profile_core_id": self.shared_owner_profile_core_id,
            "rejection_request_id": self.rejection_request_id,
            "rejection_source_kind": self.source_kind.value,
            "site_key": self.site_key,
            "path": self.path,
            "limit_kind": self.limit_kind.value,
            "reservation_upper": self.reservation_upper,
            "candidate": (
                self.candidate
                if self.candidate is not None
                else {"kind": "NOT_APPLICABLE", "reason": "CONTROL_CHECK_LIMIT"}
            ),
            "hard_cap": self.hard_cap,
            "reason_code": self.reason_code,
            "side_effect_started": False,
            "native_existence": "KNOWN_NOT_STARTED",
            "rejection_ordinal": 1,
            "control_cap_rejections": 1,
            "commit_state": "COMMIT_BYTES_FROZEN_NOT_SELF_PROVING",
            "commit_bytes_role": "INTENT_AND_COMMIT_IDENTICAL_BYTES",
            "durable_commit_requires_atomic_same_inode_pair": True,
            "formal_counter_eligible": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def commit_id(self) -> str:
        if content_id(COMMIT_DOMAIN, self._payload()) != self._commit_id:
            _fail("attempt-rejection commit changed after issuance")
        return self._commit_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_attempt_rejection_commit_id": self.commit_id}


def _commit_from_document(document: dict[str, Any]) -> H1AttemptRejectionCommitV1:
    candidate_value = document["candidate"]
    candidate: int | None
    if candidate_value == {"kind": "NOT_APPLICABLE", "reason": "CONTROL_CHECK_LIMIT"}:
        candidate = None
    else:
        candidate = candidate_value
    value = H1AttemptRejectionCommitV1(
        _COMMIT_ISSUER,
        document["h1_attempt_rejection_gate_id"],
        document["logical_occurrence_id"],
        document["route_attempt_id"],
        document["decision_point_id"],
        document["transaction_id"],
        document["shared_owner_profile_core_id"],
        document["rejection_request_id"],
        document["rejection_source_kind"],
        document["site_key"],
        document["path"],
        document["limit_kind"],
        document["reservation_upper"],
        candidate,
        document["hard_cap"],
        document["reason_code"],
    )
    if value.to_document() != document:
        _fail("durable rejection commit did not replay")
    return value


@dataclass(frozen=True, slots=True)
class H1AttemptRejectionAckV1:
    _issuer: InitVar[object]
    gate_id: str
    commit_id: str
    receipt_id: str
    event_id: str
    snapshot_id: str
    _ack_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ACK_ISSUER:
            _fail("attempt-rejection acknowledgement is issuer-created only")
        for value, label in (
            (self.gate_id, "rejection gate"),
            (self.commit_id, "rejection commit"),
            (self.receipt_id, "shared-owner receipt"),
            (self.event_id, "shared-owner event"),
            (self.snapshot_id, "shared-owner snapshot"),
        ):
            _cid(value, label)
        object.__setattr__(self, "_ack_id", content_id(ACK_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_attempt_rejection_ack.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_attempt_rejection_gate_id": self.gate_id,
            "h1_attempt_rejection_commit_id": self.commit_id,
            "shared_owner_receipt_id": self.receipt_id,
            "shared_owner_event_id": self.event_id,
            "shared_owner_snapshot_id": self.snapshot_id,
            "control_cap_rejections": 1,
            "ack_state": "ACK_BYTES_FROZEN_NOT_SELF_PROVING",
            "ack_bytes_role": "OWNER_PAIR_ACK_CANDIDATE",
            "durable_ack_requires_gate_journal_replay": True,
            "formal_counter_eligible": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def ack_id(self) -> str:
        if content_id(ACK_DOMAIN, self._payload()) != self._ack_id:
            _fail("attempt-rejection acknowledgement changed after issuance")
        return self._ack_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_attempt_rejection_ack_id": self.ack_id}


def _ack_from_document(document: dict[str, Any]) -> H1AttemptRejectionAckV1:
    value = H1AttemptRejectionAckV1(
        _ACK_ISSUER,
        document["h1_attempt_rejection_gate_id"],
        document["h1_attempt_rejection_commit_id"],
        document["shared_owner_receipt_id"],
        document["shared_owner_event_id"],
        document["shared_owner_snapshot_id"],
    )
    if value.to_document() != document:
        _fail("durable rejection acknowledgement did not replay")
    return value


@dataclass(frozen=True, slots=True)
class H1AttemptRejectionGateHandleV1:
    _issuer: InitVar[object]
    gate_directory: str
    spec: H1AttemptRejectionGateSpecV1
    gate_directory_device: int
    gate_directory_inode: int
    gate_lock_device: int
    gate_lock_inode: int
    high_water_cursor_device: int
    high_water_cursor_inode: int
    high_water_cursor_token: str
    high_water_cursor_genesis_record_id: str

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _HANDLE_ISSUER or type(self.spec) is not H1AttemptRejectionGateSpecV1:
            _fail("attempt-rejection gate handle is verifier-opened only")
        path = Path(self.gate_directory)
        if not path.is_absolute() or path.name != self.spec.gate_id:
            _fail("attempt-rejection gate handle path is malformed")
        _nonnegative(self.gate_directory_device, "gate directory device")
        _nonnegative(self.gate_directory_inode, "gate directory inode")
        _nonnegative(self.gate_lock_device, "gate lock device")
        _nonnegative(self.gate_lock_inode, "gate lock inode")
        _nonnegative(self.high_water_cursor_device, "high-water cursor device")
        _nonnegative(self.high_water_cursor_inode, "high-water cursor inode")
        _cid(self.high_water_cursor_token, "high-water cursor token")
        _cid(
            self.high_water_cursor_genesis_record_id,
            "high-water cursor genesis record",
        )


@dataclass(slots=True)
class H1AttemptRejectionAdmissionLeaseV1:
    _issuer: InitVar[object]
    gate: H1AttemptRejectionGateHandleV1
    _directory_fd: int = field(repr=False)
    _lock_fd: int = field(repr=False)
    _owner_thread_id: int = field(repr=False)
    _commit_mutex: Any = field(default_factory=threading.Lock, repr=False)
    _active: bool = field(default=True, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _LEASE_ISSUER:
            _fail("attempt-rejection admission lease is context-created only")

    def __reduce__(self) -> NoReturn:
        _fail("attempt-rejection admission lease is not serializable")


@dataclass(frozen=True, slots=True)
class H1AttemptRejectionGateReplaySnapshotV1:
    """Exact gate replay retained under the caller's gate lock."""

    _issuer: InitVar[object]
    gate_id: str
    state: H1AttemptRejectionGateStateV1
    commit: H1AttemptRejectionCommitV1 | None
    acknowledgement: H1AttemptRejectionAckV1 | None

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPLAY_SNAPSHOT_ISSUER:
            _fail("attempt-rejection replay snapshot is issuer-created only")
        _cid(self.gate_id, "replay snapshot rejection gate")
        try:
            object.__setattr__(
                self,
                "state",
                H1AttemptRejectionGateStateV1(self.state),
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1AttemptRejectionGateV1Error(
                "attempt-rejection replay snapshot state is invalid"
            ) from error
        if self.commit is not None:
            if (
                type(self.commit) is not H1AttemptRejectionCommitV1
                or self.commit.gate_id != self.gate_id
            ):
                _fail("attempt-rejection replay snapshot commit is invalid")
        if self.acknowledgement is not None:
            if (
                type(self.acknowledgement) is not H1AttemptRejectionAckV1
                or self.commit is None
                or self.acknowledgement.gate_id != self.gate_id
                or self.acknowledgement.commit_id != self.commit.commit_id
            ):
                _fail("attempt-rejection replay snapshot acknowledgement is invalid")

    @property
    def commit_id(self) -> str | None:
        return self.commit.commit_id if self.commit is not None else None

    @property
    def commit_document(self) -> dict[str, Any] | None:
        return self.commit.to_document() if self.commit is not None else None

    @property
    def acknowledgement_id(self) -> str | None:
        return (
            self.acknowledgement.ack_id
            if self.acknowledgement is not None
            else None
        )

    @property
    def acknowledgement_document(self) -> dict[str, Any] | None:
        return (
            self.acknowledgement.to_document()
            if self.acknowledgement is not None
            else None
        )

    def __reduce__(self) -> NoReturn:
        _fail("attempt-rejection replay snapshot is not serializable")


def _open_directory_fd(path: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "attempt-rejection gate directory cannot be opened"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
        os.close(descriptor)
        _fail("attempt-rejection gate directory is not private")
    return descriptor


def _open_parent_directory_fd(path: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "attempt-rejection parent directory cannot be opened"
        ) from error
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        _fail("attempt-rejection parent is not a directory")
    return descriptor


def _resolve_gate_base(
    base_directory: str | Path,
    *,
    create: bool,
) -> tuple[Path, int]:
    outer = Path(base_directory).resolve(strict=True)
    outer_fd = _open_parent_directory_fd(outer)
    try:
        if create:
            try:
                os.mkdir(_ROOT_DIRECTORY, mode=0o700, dir_fd=outer_fd)
            except FileExistsError:
                pass
            os.fsync(outer_fd)
        gate_base_fd = _open_directory_fd_at(outer_fd, _ROOT_DIRECTORY)
    finally:
        os.close(outer_fd)
    return outer / _ROOT_DIRECTORY, gate_base_fd


def _open_directory_fd_at(parent_fd: int, name: str) -> int:
    if type(name) is not str or not name or "/" in name or name in {".", ".."}:
        _fail("relative gate directory name is malformed")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "attempt-rejection gate directory cannot be opened below its pinned base"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
        os.close(descriptor)
        _fail("attempt-rejection gate directory is not private")
    return descriptor


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _verify_base_identity(
    base: Path,
    base_fd: int,
    spec: H1AttemptRejectionGateSpecV1,
) -> None:
    metadata = os.fstat(base_fd)
    if (
        str(base) != spec.gate_base_realpath
        or metadata.st_dev != spec.gate_base_device
        or metadata.st_ino != spec.gate_base_inode
    ):
        _fail("attempt-rejection gate base differs from its frozen physical identity")


def _read_file(directory_fd: int, name: str) -> bytes | None:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "durable gate record cannot be opened"
        ) from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            _fail("durable gate record is not one private regular file")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_DOCUMENT_BYTES:
                _fail("durable gate record exceeds its byte cap")
            chunks.append(chunk)
        raw = b"".join(chunks)
        if not raw:
            _fail("durable gate record is empty")
        return raw
    finally:
        os.close(descriptor)


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:  # pragma: no cover - OS invariant
            _fail("durable gate record write made no progress")
        view = view[written:]


def _cursor_not_applicable(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _cursor_record_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        _CURSOR_DOMAIN.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _cursor_document(
    *,
    gate_id: str,
    cursor_token: str,
    sequence: int,
    state: H1AttemptRejectionGateStateV1,
    commit_id: str | None,
    ack_id: str | None,
    previous_record_id: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.k7_h1_attempt_rejection_high_water_cursor_record.v1",
        "schema_version": SCHEMA_VERSION,
        "h1_attempt_rejection_gate_id": _cid(gate_id, "cursor rejection gate"),
        "cursor_token": _cid(cursor_token, "high-water cursor token"),
        "sequence": _nonnegative(sequence, "high-water cursor sequence"),
        "state": H1AttemptRejectionGateStateV1(state).value,
        "h1_attempt_rejection_commit_id": (
            _cid(commit_id, "cursor rejection commit")
            if commit_id is not None
            else _cursor_not_applicable("NO_REJECTION_COMMITTED")
        ),
        "h1_attempt_rejection_ack_id": (
            _cid(ack_id, "cursor rejection acknowledgement")
            if ack_id is not None
            else _cursor_not_applicable("NO_REJECTION_ACKNOWLEDGED")
        ),
        "previous_cursor_record_id": (
            _cid(previous_record_id, "previous high-water cursor record")
            if previous_record_id is not None
            else _cursor_not_applicable("GENESIS_HAS_NO_PREDECESSOR")
        ),
    }
    return {**payload, "cursor_record_id": _cursor_record_id(payload)}


_CURSOR_STATES = (
    H1AttemptRejectionGateStateV1.OPEN,
    H1AttemptRejectionGateStateV1.INTENT_DURABLE,
    H1AttemptRejectionGateStateV1.COMMITTED_UNACKNOWLEDGED,
    H1AttemptRejectionGateStateV1.ACKNOWLEDGED,
)


def _read_descriptor(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, 65536)
        if not chunk:
            break
        total += len(chunk)
        if total > _MAX_DOCUMENT_BYTES:
            _fail("high-water cursor exceeds its byte cap")
        chunks.append(chunk)
    raw = b"".join(chunks)
    if not raw:
        _fail("high-water cursor is empty")
    return raw


def _open_cursor_fd(directory_fd: int, *, writable: bool = False) -> int:
    flags = (os.O_WRONLY | os.O_APPEND) if writable else os.O_RDONLY
    flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(_CURSOR_FILE, flags, dir_fd=directory_fd)
    except OSError as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "attempt-rejection high-water cursor is absent or cannot be opened"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
        os.close(descriptor)
        _fail("attempt-rejection high-water cursor is not private and regular")
    return descriptor


def _parse_cursor_log(
    raw: bytes,
    *,
    expected_gate_id: str,
) -> list[dict[str, Any]]:
    if not raw.endswith(b"\n"):
        _fail("high-water cursor has a torn or truncated tail")
    lines = raw[:-1].split(b"\n")
    if not lines or len(lines) > len(_CURSOR_STATES) or any(not line for line in lines):
        _fail("high-water cursor record count is invalid")
    records: list[dict[str, Any]] = []
    token: str | None = None
    previous_id: str | None = None
    commit_id: str | None = None
    for sequence, line in enumerate(lines):
        document = _parse_exact(line, _CURSOR_FIELDS, "high-water cursor record")
        payload = {key: value for key, value in document.items() if key != "cursor_record_id"}
        if document["cursor_record_id"] != _cursor_record_id(payload):
            _fail("high-water cursor record identity changed")
        if document["schema"] != "acfqp.k7_h1_attempt_rejection_high_water_cursor_record.v1":
            _fail("high-water cursor schema changed")
        if document["schema_version"] != SCHEMA_VERSION:
            _fail("high-water cursor schema version changed")
        if document["h1_attempt_rejection_gate_id"] != expected_gate_id:
            _fail("high-water cursor belongs to another gate")
        current_token = _cid(document["cursor_token"], "high-water cursor token")
        if token is None:
            token = current_token
        elif current_token != token:
            _fail("high-water cursor token changed")
        if document["sequence"] != sequence:
            _fail("high-water cursor sequence is not contiguous")
        expected_state = _CURSOR_STATES[sequence]
        if document["state"] != expected_state.value:
            _fail("high-water cursor state is not monotone")
        expected_previous = (
            _cursor_not_applicable("GENESIS_HAS_NO_PREDECESSOR")
            if previous_id is None
            else previous_id
        )
        if document["previous_cursor_record_id"] != expected_previous:
            _fail("high-water cursor predecessor chain changed")
        if sequence == 0:
            if document["h1_attempt_rejection_commit_id"] != _cursor_not_applicable(
                "NO_REJECTION_COMMITTED"
            ):
                _fail("high-water cursor genesis unexpectedly binds a commit")
        else:
            current_commit_id = _cid(
                document["h1_attempt_rejection_commit_id"],
                "cursor rejection commit",
            )
            if commit_id is None:
                commit_id = current_commit_id
            elif current_commit_id != commit_id:
                _fail("high-water cursor commit identity changed")
        if sequence < 3:
            if document["h1_attempt_rejection_ack_id"] != _cursor_not_applicable(
                "NO_REJECTION_ACKNOWLEDGED"
            ):
                _fail("high-water cursor binds an acknowledgement too early")
        else:
            _cid(
                document["h1_attempt_rejection_ack_id"],
                "cursor rejection acknowledgement",
            )
        previous_id = _cid(document["cursor_record_id"], "high-water cursor record")
        records.append(document)
    return records


def _read_cursor_log(
    directory_fd: int,
    *,
    expected_gate_id: str,
) -> tuple[list[dict[str, Any]], os.stat_result]:
    descriptor = _open_cursor_fd(directory_fd)
    try:
        metadata = os.fstat(descriptor)
        raw = _read_descriptor(descriptor)
    finally:
        os.close(descriptor)
    return _parse_cursor_log(raw, expected_gate_id=expected_gate_id), metadata


def _freeze_cursor_genesis(
    directory_fd: int,
    spec: H1AttemptRejectionGateSpecV1,
    *,
    allow_create: bool,
) -> tuple[list[dict[str, Any]], os.stat_result]:
    if allow_create:
        token = secrets.token_hex(32)
        genesis = _cursor_document(
            gate_id=spec.gate_id,
            cursor_token=token,
            sequence=0,
            state=H1AttemptRejectionGateStateV1.OPEN,
            commit_id=None,
            ack_id=None,
            previous_record_id=None,
        )
        _publish_new(
            directory_fd,
            _CURSOR_FILE,
            canonical_json_bytes(genesis) + b"\n",
        )
    records, metadata = _read_cursor_log(
        directory_fd,
        expected_gate_id=spec.gate_id,
    )
    return records, metadata


def _verify_cursor_handle(
    gate: H1AttemptRejectionGateHandleV1,
    records: list[dict[str, Any]],
    metadata: os.stat_result,
) -> None:
    genesis = records[0]
    if (
        metadata.st_dev != gate.high_water_cursor_device
        or metadata.st_ino != gate.high_water_cursor_inode
        or genesis["cursor_token"] != gate.high_water_cursor_token
        or genesis["cursor_record_id"] != gate.high_water_cursor_genesis_record_id
    ):
        _fail("attempt-rejection high-water cursor inode or genesis changed")


def _append_cursor_state_locked(
    gate: H1AttemptRejectionGateHandleV1,
    directory_fd: int,
    *,
    state: H1AttemptRejectionGateStateV1,
    commit_id: str | None,
    ack_id: str | None,
) -> None:
    target_sequence = _CURSOR_STATES.index(state)
    records, metadata = _read_cursor_log(
        directory_fd,
        expected_gate_id=gate.spec.gate_id,
    )
    _verify_cursor_handle(gate, records, metadata)
    if len(records) - 1 >= target_sequence:
        existing = records[target_sequence]
        expected_commit = (
            commit_id
            if commit_id is not None
            else _cursor_not_applicable("NO_REJECTION_COMMITTED")
        )
        expected_ack = (
            ack_id
            if ack_id is not None
            else _cursor_not_applicable("NO_REJECTION_ACKNOWLEDGED")
        )
        if (
            existing["state"] != state.value
            or existing["h1_attempt_rejection_commit_id"] != expected_commit
            or existing["h1_attempt_rejection_ack_id"] != expected_ack
        ):
            _fail("high-water cursor conflicts with the durable transition")
        return
    if len(records) != target_sequence:
        _fail("high-water cursor transition skipped a durable state")
    document = _cursor_document(
        gate_id=gate.spec.gate_id,
        cursor_token=gate.high_water_cursor_token,
        sequence=target_sequence,
        state=state,
        commit_id=commit_id,
        ack_id=ack_id,
        previous_record_id=records[-1]["cursor_record_id"],
    )
    descriptor = _open_cursor_fd(directory_fd, writable=True)
    try:
        cursor_metadata = os.fstat(descriptor)
        if (cursor_metadata.st_dev, cursor_metadata.st_ino) != (
            gate.high_water_cursor_device,
            gate.high_water_cursor_inode,
        ):
            _fail("attempt-rejection high-water cursor inode changed before append")
        _write_all(descriptor, canonical_json_bytes(document) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    replayed, replayed_metadata = _read_cursor_log(
        directory_fd,
        expected_gate_id=gate.spec.gate_id,
    )
    _verify_cursor_handle(gate, replayed, replayed_metadata)
    if replayed[-1] != document:
        _fail("high-water cursor transition did not replay")


def _publish_new(directory_fd: int, name: str, raw: bytes) -> bool:
    if len(raw) > _MAX_DOCUMENT_BYTES:
        _fail("durable gate record exceeds its byte cap before publication")
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
            published = True
            os.fsync(directory_fd)
        except FileExistsError:
            published = False
    finally:
        try:
            os.unlink(temporary, dir_fd=directory_fd)
            os.fsync(directory_fd)
        except FileNotFoundError:  # pragma: no cover - defensive
            pass
    return published


def _link_intent_to_commit(directory_fd: int) -> bool:
    try:
        os.link(
            _INTENT_FILE,
            _COMMIT_FILE,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
        os.fsync(directory_fd)
        return True
    except FileExistsError:
        return False


def _verify_layout(directory_fd: int) -> None:
    try:
        names = set(os.listdir(directory_fd))
    except OSError as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "durable gate directory cannot be enumerated"
        ) from error
    unexpected: set[str] = set()
    for name in names:
        if name in _KNOWN_FILES:
            continue
        if not _TEMP_PATTERN.fullmatch(name):
            unexpected.add(name)
            continue
        try:
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            _fail("durable gate orphan temp is not private and regular")
    if unexpected:
        _fail("durable gate directory contains an unknown record")
    lock_raw = _read_file(directory_fd, _LOCK_FILE)
    if lock_raw is None or not hmac.compare_digest(lock_raw, _LOCK_BYTES):
        _fail("durable gate directory lacks its exact coordination lock")


def _cleanup_gate_temps(directory_fd: int) -> None:
    """Remove only writer-shaped orphan temps while retaining gate EX."""

    changed = False
    for name in os.listdir(directory_fd):
        if not _TEMP_PATTERN.fullmatch(name):
            continue
        try:
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            _fail("durable gate orphan temp is not private and regular")
        os.unlink(name, dir_fd=directory_fd)
        changed = True
    if changed:
        os.fsync(directory_fd)


def _open_lock_fd(directory_fd: int) -> int:
    flags = os.O_RDWR | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(_LOCK_FILE, flags, dir_fd=directory_fd)
    except OSError as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "attempt-rejection coordination lock cannot be opened"
        ) from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            _fail("attempt-rejection coordination lock is not private and regular")
        raw = os.pread(descriptor, len(_LOCK_BYTES) + 1, 0)
        if not hmac.compare_digest(raw, _LOCK_BYTES):
            _fail("attempt-rejection coordination lock bytes changed")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _acquire_lock(descriptor: int, operation: int) -> None:
    try:
        fcntl.flock(descriptor, operation)
    except OSError as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "attempt-rejection coordination lock failed"
        ) from error


def _make_handle_locked(
    path: Path,
    spec: H1AttemptRejectionGateSpecV1,
    directory_fd: int,
    lock_fd: int,
) -> H1AttemptRejectionGateHandleV1:
    """Build one handle while the supplied coordination lock is retained."""

    directory_metadata = os.fstat(directory_fd)
    lock_metadata = os.fstat(lock_fd)
    cursor_records, cursor_metadata = _read_cursor_log(
        directory_fd,
        expected_gate_id=spec.gate_id,
    )
    cursor_genesis = cursor_records[0]
    return H1AttemptRejectionGateHandleV1(
        _HANDLE_ISSUER,
        str(path),
        spec,
        directory_metadata.st_dev,
        directory_metadata.st_ino,
        lock_metadata.st_dev,
        lock_metadata.st_ino,
        cursor_metadata.st_dev,
        cursor_metadata.st_ino,
        cursor_genesis["cursor_token"],
        cursor_genesis["cursor_record_id"],
    )


def _allocation_intent_name(route_attempt_id: str) -> str:
    return f".acfqp-h1-attempt-slot-intent-{route_attempt_id}.json"


def _allocation_commit_name(route_attempt_id: str) -> str:
    return f".acfqp-h1-attempt-slot-commit-{route_attempt_id}.json"


def _freeze_or_verify_allocation_intent(
    base_fd: int,
    spec: H1AttemptRejectionGateSpecV1,
) -> None:
    expected_raw = canonical_json_bytes(spec.to_document())
    name = _allocation_intent_name(spec.route_attempt_id)
    if not _publish_new(base_fd, name, expected_raw):
        existing_raw = _read_file(base_fd, name)
        if existing_raw is None or not hmac.compare_digest(existing_raw, expected_raw):
            _fail("attempt-rejection gate allocation intent conflicts")


def _verify_allocation_intent(
    base_fd: int,
    spec: H1AttemptRejectionGateSpecV1,
) -> None:
    expected_raw = canonical_json_bytes(spec.to_document())
    existing_raw = _read_file(
        base_fd,
        _allocation_intent_name(spec.route_attempt_id),
    )
    if existing_raw is None or not hmac.compare_digest(existing_raw, expected_raw):
        _fail("attempt-rejection gate lacks its frozen base allocation intent")


def _allocation_document(
    spec: H1AttemptRejectionGateSpecV1,
    directory_fd: int,
    lock_fd: int,
) -> dict[str, Any]:
    """Recompute allocation identity while ``lock_fd`` is already locked."""

    metadata = os.fstat(directory_fd)
    lock_metadata = os.fstat(lock_fd)
    cursor_records, cursor_metadata = _read_cursor_log(
        directory_fd,
        expected_gate_id=spec.gate_id,
    )
    cursor_genesis = cursor_records[0]
    return {
        "schema": "acfqp.k7_h1_attempt_rejection_gate_allocation.v1",
        "schema_version": SCHEMA_VERSION,
        "h1_attempt_rejection_gate_id": spec.gate_id,
        "gate_base_realpath": spec.gate_base_realpath,
        "gate_base_device": spec.gate_base_device,
        "gate_base_inode": spec.gate_base_inode,
        "gate_directory_device": metadata.st_dev,
        "gate_directory_inode": metadata.st_ino,
        "gate_lock_device": lock_metadata.st_dev,
        "gate_lock_inode": lock_metadata.st_ino,
        "high_water_cursor_device": cursor_metadata.st_dev,
        "high_water_cursor_inode": cursor_metadata.st_ino,
        "high_water_cursor_token": cursor_genesis["cursor_token"],
        "high_water_cursor_genesis_record_id": cursor_genesis["cursor_record_id"],
        "allocation_state": "PINNED_LOCAL_FILESYSTEM_INODE",
        "kernel_writer_credential_verified": False,
        "production_execution_authorized": False,
    }


def _freeze_or_verify_allocation_commit(
    base_fd: int,
    spec: H1AttemptRejectionGateSpecV1,
    directory_fd: int,
    lock_fd: int,
    *,
    allow_create: bool,
) -> None:
    expected_document = _allocation_document(spec, directory_fd, lock_fd)
    expected_raw = canonical_json_bytes(expected_document)
    name = _allocation_commit_name(spec.route_attempt_id)
    published = _publish_new(base_fd, name, expected_raw) if allow_create else False
    if not published:
        existing_raw = _read_file(base_fd, name)
        if existing_raw is None:
            _fail("attempt-rejection base allocation commit is absent")
        existing_document = _parse_exact(
            existing_raw,
            _ALLOCATION_FIELDS,
            "attempt-rejection base allocation",
        )
        if existing_document != expected_document or not hmac.compare_digest(
            existing_raw, expected_raw
        ):
            _fail("attempt-rejection gate physical allocation was already consumed")


def initialize_h1_attempt_rejection_gate_v1(
    base_directory: str | Path,
    spec: H1AttemptRejectionGateSpecV1,
) -> H1AttemptRejectionGateHandleV1:
    if type(spec) is not H1AttemptRejectionGateSpecV1:
        _fail("attempt-rejection gate requires one exact spec")
    _reject_same_gate_context_reentry(
        spec.gate_id,
        "initialize_h1_attempt_rejection_gate_v1",
    )
    requested_base = Path(base_directory).resolve(strict=True) / _ROOT_DIRECTORY
    if str(requested_base) != spec.gate_base_realpath:
        _fail("attempt-rejection gate base differs from its frozen physical identity")
    base, base_fd = _resolve_gate_base(base_directory, create=False)
    try:
        _verify_base_identity(base, base_fd, spec)
        created_directory = False
        try:
            os.mkdir(spec.gate_id, mode=0o700, dir_fd=base_fd)
            created_directory = True
        except FileExistsError:
            pass
        os.fsync(base_fd)
        directory_fd = _open_directory_fd_at(base_fd, spec.gate_id)
        lock_fd = -1
        lock_held = False
        try:
            if created_directory:
                _publish_new(directory_fd, _LOCK_FILE, _LOCK_BYTES)
            else:
                existing_lock = _read_file(directory_fd, _LOCK_FILE)
                if existing_lock is None or not hmac.compare_digest(
                    existing_lock, _LOCK_BYTES
                ):
                    _fail(
                        "existing rejection gate physical allocation was already "
                        "consumed or has a different coordination lock"
                    )
            lock_fd = _open_lock_fd(directory_fd)
            _acquire_lock(lock_fd, fcntl.LOCK_EX)
            lock_held = True
            _verify_allocation_intent(base_fd, spec)
            try:
                _freeze_cursor_genesis(
                    directory_fd,
                    spec,
                    allow_create=created_directory,
                )
            except ConstructionK7H1AttemptRejectionGateV1Error:
                if not created_directory:
                    _fail(
                        "attempt-rejection gate physical allocation was already consumed"
                    )
                raise
            _freeze_or_verify_allocation_commit(
                base_fd,
                spec,
                directory_fd,
                lock_fd,
                allow_create=created_directory,
            )
            raw = canonical_json_bytes(spec.to_document())
            if not _publish_new(directory_fd, _GATE_FILE, raw):
                existing = _read_file(directory_fd, _GATE_FILE)
                if existing is None or not hmac.compare_digest(existing, raw):
                    _fail("existing rejection gate differs from the requested spec")
            _cleanup_gate_temps(directory_fd)
            _verify_layout(directory_fd)
            gate_directory = base / spec.gate_id
            handle = _make_handle_locked(
                gate_directory,
                spec,
                directory_fd,
                lock_fd,
            )
        finally:
            if lock_held:
                _acquire_lock(lock_fd, fcntl.LOCK_UN)
            if lock_fd >= 0:
                os.close(lock_fd)
            os.close(directory_fd)
    finally:
        os.close(base_fd)
    return handle


def open_h1_attempt_rejection_gate_v1(
    gate_directory: str | Path,
    *,
    expected_gate_id: str,
) -> H1AttemptRejectionGateHandleV1:
    expected = _cid(expected_gate_id, "expected rejection gate")
    _reject_same_gate_context_reentry(
        expected,
        "open_h1_attempt_rejection_gate_v1",
    )
    supplied_path = Path(gate_directory)
    if not supplied_path.is_absolute():
        _fail("gate directory path must be absolute")
    if supplied_path.name != expected:
        _fail("gate directory name differs from the expected gate ID")
    base = supplied_path.parent.resolve(strict=True)
    path = base / supplied_path.name
    base_fd = _open_directory_fd(base)
    try:
        directory_fd = _open_directory_fd_at(base_fd, expected)
        lock_fd = -1
        lock_held = False
        try:
            try:
                lock_fd = _open_lock_fd(directory_fd)
            except ConstructionK7H1AttemptRejectionGateV1Error as error:
                raise ConstructionK7H1AttemptRejectionGateV1Error(
                    "attempt-rejection gate physical allocation was already "
                    "consumed or lacks its coordination lock"
                ) from error
            _acquire_lock(lock_fd, fcntl.LOCK_SH)
            lock_held = True
            raw = _read_file(directory_fd, _GATE_FILE)
            if raw is None:
                _fail("durable rejection gate lacks its spec")
            spec = _spec_from_document(_parse_exact(raw, _GATE_FIELDS, "gate spec"))
            if not hmac.compare_digest(spec.gate_id, expected):
                _fail("durable rejection gate ID differs from the expected ID")
            _verify_base_identity(base, base_fd, spec)
            _verify_allocation_intent(base_fd, spec)
            _freeze_or_verify_allocation_commit(
                base_fd,
                spec,
                directory_fd,
                lock_fd,
                allow_create=False,
            )
            _verify_layout(directory_fd)
            handle = _make_handle_locked(path, spec, directory_fd, lock_fd)
        finally:
            if lock_held:
                _acquire_lock(lock_fd, fcntl.LOCK_UN)
            if lock_fd >= 0:
                os.close(lock_fd)
            os.close(directory_fd)
    finally:
        os.close(base_fd)
    return handle


def _require_handle(
    value: Any,
    lock_operation: int,
) -> tuple[H1AttemptRejectionGateHandleV1, int, int]:
    if type(value) is not H1AttemptRejectionGateHandleV1:
        _fail("attempt-rejection gate handle has a foreign type")
    _reject_same_gate_context_reentry(
        value.spec.gate_id,
        "locked attempt-rejection gate API",
    )
    if lock_operation not in {fcntl.LOCK_SH, fcntl.LOCK_EX}:
        _fail("attempt-rejection handle requires one shared or exclusive lock")
    base = Path(value.spec.gate_base_realpath)
    base_fd = _open_directory_fd(base)
    directory_fd = -1
    lock_fd = -1
    lock_held = False
    try:
        _verify_base_identity(base, base_fd, value.spec)
        directory_fd = _open_directory_fd_at(base_fd, value.spec.gate_id)
        directory_metadata = os.fstat(directory_fd)
        if (directory_metadata.st_dev, directory_metadata.st_ino) != (
            value.gate_directory_device,
            value.gate_directory_inode,
        ):
            _fail(
                "attempt-rejection gate physical allocation was already consumed: "
                "handle directory inode changed"
            )
        lock_fd = _open_lock_fd(directory_fd)
        lock_metadata = os.fstat(lock_fd)
        if (lock_metadata.st_dev, lock_metadata.st_ino) != (
            value.gate_lock_device,
            value.gate_lock_inode,
        ):
            _fail(
                "attempt-rejection gate physical allocation was already consumed: "
                "coordination lock inode changed"
            )
        _acquire_lock(lock_fd, lock_operation)
        lock_held = True

        # From this point through the caller's release, no cooperating writer
        # can expose a partial cursor append or a mismatched dynamic record set.
        _verify_allocation_intent(base_fd, value.spec)
        _freeze_or_verify_allocation_commit(
            base_fd,
            value.spec,
            directory_fd,
            lock_fd,
            allow_create=False,
        )
        raw = _read_file(directory_fd, _GATE_FILE)
        if raw is None:
            _fail("attempt-rejection gate spec disappeared")
        spec = _spec_from_document(_parse_exact(raw, _GATE_FIELDS, "gate spec"))
        if spec.to_document() != value.spec.to_document():
            _fail("attempt-rejection gate handle is stale or transplanted")
        if lock_operation == fcntl.LOCK_EX:
            _cleanup_gate_temps(directory_fd)
        _verify_layout(directory_fd)
        cursor_records, cursor_metadata = _read_cursor_log(
            directory_fd,
            expected_gate_id=value.spec.gate_id,
        )
        _verify_cursor_handle(value, cursor_records, cursor_metadata)
    except BaseException:
        if lock_held:
            _acquire_lock(lock_fd, fcntl.LOCK_UN)
        if lock_fd >= 0:
            os.close(lock_fd)
        if directory_fd >= 0:
            os.close(directory_fd)
        raise
    finally:
        os.close(base_fd)
    return value, directory_fd, lock_fd


def _build_commit(
    spec: H1AttemptRejectionGateSpecV1,
    *,
    decision_point_id: str,
    transaction_id: str,
    shared_owner_profile_core_id: str,
    rejection_request_id: str,
    source_kind: H1RejectionSourceKindV1,
    site_key: str,
    path: str,
    limit_kind: H1RejectionLimitKindV1,
    reservation_upper: int,
    candidate: int | None,
    hard_cap: int,
    reason_code: str,
) -> H1AttemptRejectionCommitV1:
    return H1AttemptRejectionCommitV1(
        _COMMIT_ISSUER,
        spec.gate_id,
        spec.logical_occurrence_id,
        spec.route_attempt_id,
        decision_point_id,
        transaction_id,
        shared_owner_profile_core_id,
        rejection_request_id,
        source_kind,
        site_key,
        path,
        limit_kind,
        reservation_upper,
        candidate,
        hard_cap,
        reason_code,
    )


def _read_commit_record(directory_fd: int, name: str) -> H1AttemptRejectionCommitV1 | None:
    raw = _read_file(directory_fd, name)
    if raw is None:
        return None
    return _commit_from_document(_parse_exact(raw, _COMMIT_FIELDS, "rejection commit"))


def _read_committed_pair_locked(
    gate: H1AttemptRejectionGateHandleV1,
    directory_fd: int,
) -> H1AttemptRejectionCommitV1 | None:
    state, commit, _ = _observe_gate_locked(
        gate,
        directory_fd,
        advance_cursor=False,
    )
    if state in {
        H1AttemptRejectionGateStateV1.COMMITTED_UNACKNOWLEDGED,
        H1AttemptRejectionGateStateV1.ACKNOWLEDGED,
    }:
        return commit
    return None


def _observe_gate_locked(
    gate: H1AttemptRejectionGateHandleV1,
    directory_fd: int,
    *,
    advance_cursor: bool,
) -> tuple[
    H1AttemptRejectionGateStateV1,
    H1AttemptRejectionCommitV1 | None,
    H1AttemptRejectionAckV1 | None,
]:
    cursor_records, cursor_metadata = _read_cursor_log(
        directory_fd,
        expected_gate_id=gate.spec.gate_id,
    )
    _verify_cursor_handle(gate, cursor_records, cursor_metadata)
    intent_raw = _read_file(directory_fd, _INTENT_FILE)
    commit_raw = _read_file(directory_fd, _COMMIT_FILE)
    ack_raw = _read_file(directory_fd, _ACK_FILE)
    if intent_raw is None:
        if commit_raw is not None or ack_raw is not None:
            _fail("rejection commit/ack exists without its durable intent")
        observed_sequence = 0
        intent = None
        commit = None
        ack = None
    else:
        intent = _commit_from_document(
            _parse_exact(intent_raw, _COMMIT_FIELDS, "rejection intent")
        )
        if intent.gate_id != gate.spec.gate_id:
            _fail("rejection intent belongs to another gate")
        observed_sequence = 1
        commit = None
        ack = None
        if commit_raw is not None:
            if not hmac.compare_digest(commit_raw, intent_raw):
                _fail("rejection commit differs from its intent")
            intent_stat = os.stat(
                _INTENT_FILE,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
            commit_stat = os.stat(
                _COMMIT_FILE,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
            if (intent_stat.st_dev, intent_stat.st_ino) != (
                commit_stat.st_dev,
                commit_stat.st_ino,
            ):
                _fail("rejection commit is not the atomic intent hard link")
            commit = _commit_from_document(
                _parse_exact(commit_raw, _COMMIT_FIELDS, "rejection commit")
            )
            if commit.commit_id != intent.commit_id:
                _fail("rejection commit identity changed")
            observed_sequence = 2
        if ack_raw is not None:
            if commit is None:
                _fail("rejection acknowledgement exists before durable commit")
            ack = _ack_from_document(
                _parse_exact(ack_raw, _ACK_FIELDS, "rejection ack")
            )
            if ack.gate_id != gate.spec.gate_id or ack.commit_id != commit.commit_id:
                _fail("rejection acknowledgement is stale or transplanted")
            observed_sequence = 3

    cursor_sequence = len(cursor_records) - 1
    if cursor_sequence > observed_sequence:
        _fail("durable rejection records fell below the cursor high-water mark")
    if cursor_sequence >= 1:
        if intent is None or cursor_records[1][
            "h1_attempt_rejection_commit_id"
        ] != intent.commit_id:
            _fail("cursor high-water intent binding changed")
    if cursor_sequence >= 2:
        if commit is None or cursor_records[2][
            "h1_attempt_rejection_commit_id"
        ] != commit.commit_id:
            _fail("cursor high-water commit binding changed")
    if cursor_sequence >= 3:
        if ack is None or cursor_records[3][
            "h1_attempt_rejection_ack_id"
        ] != ack.ack_id:
            _fail("cursor high-water acknowledgement binding changed")

    if advance_cursor and cursor_sequence < observed_sequence:
        durable_commit_id = intent.commit_id if intent is not None else None
        if cursor_sequence < 1 <= observed_sequence:
            _append_cursor_state_locked(
                gate,
                directory_fd,
                state=H1AttemptRejectionGateStateV1.INTENT_DURABLE,
                commit_id=durable_commit_id,
                ack_id=None,
            )
        if cursor_sequence < 2 <= observed_sequence:
            _append_cursor_state_locked(
                gate,
                directory_fd,
                state=H1AttemptRejectionGateStateV1.COMMITTED_UNACKNOWLEDGED,
                commit_id=durable_commit_id,
                ack_id=None,
            )
        if cursor_sequence < 3 <= observed_sequence:
            if ack is None:  # pragma: no cover - implied by observed_sequence
                _fail("cursor recovery lacks its durable acknowledgement")
            _append_cursor_state_locked(
                gate,
                directory_fd,
                state=H1AttemptRejectionGateStateV1.ACKNOWLEDGED,
                commit_id=durable_commit_id,
                ack_id=ack.ack_id,
            )

    return _CURSOR_STATES[observed_sequence], commit, ack


def _commit_rejection_locked(
    gate: H1AttemptRejectionGateHandleV1,
    directory_fd: int,
    *,
    decision_point_id: str,
    transaction_id: str,
    shared_owner_profile_core_id: str,
    rejection_request_id: str,
    source_kind: H1RejectionSourceKindV1,
    site_key: str,
    path: str,
    limit_kind: H1RejectionLimitKindV1,
    reservation_upper: int,
    candidate: int | None,
    hard_cap: int,
    reason_code: str,
    fault: H1AttemptRejectionCrashPointV1,
) -> H1AttemptRejectionCommitV1:
    desired = _build_commit(
        gate.spec,
        decision_point_id=decision_point_id,
        transaction_id=transaction_id,
        shared_owner_profile_core_id=shared_owner_profile_core_id,
        rejection_request_id=rejection_request_id,
        source_kind=source_kind,
        site_key=site_key,
        path=path,
        limit_kind=limit_kind,
        reservation_upper=reservation_upper,
        candidate=candidate,
        hard_cap=hard_cap,
        reason_code=reason_code,
    )
    raw = desired.canonical_bytes
    if len(raw) > _MAX_DOCUMENT_BYTES:
        _fail("rejection commit exceeds its byte cap before publication")
    _observe_gate_locked(gate, directory_fd, advance_cursor=True)
    existing_intent_raw = _read_file(directory_fd, _INTENT_FILE)
    if existing_intent_raw is None:
        _publish_new(directory_fd, _INTENT_FILE, raw)
        existing_intent_raw = _read_file(directory_fd, _INTENT_FILE)
    if existing_intent_raw is None:
        _fail("rejection intent was not durably published")
    existing_intent = _commit_from_document(
        _parse_exact(existing_intent_raw, _COMMIT_FIELDS, "rejection intent")
    )
    if existing_intent.commit_id != desired.commit_id:
        raise H1AttemptSecondRejectionV1(
            "a different rejection already owns the attempt-wide slot"
        )
    _append_cursor_state_locked(
        gate,
        directory_fd,
        state=H1AttemptRejectionGateStateV1.INTENT_DURABLE,
        commit_id=existing_intent.commit_id,
        ack_id=None,
    )
    if fault is H1AttemptRejectionCrashPointV1.AFTER_INTENT_FSYNC:
        raise H1AttemptRejectionInjectedCrashV1("crash after durable intent")
    existing_commit_raw = _read_file(directory_fd, _COMMIT_FILE)
    if existing_commit_raw is None:
        _link_intent_to_commit(directory_fd)
        existing_commit_raw = _read_file(directory_fd, _COMMIT_FILE)
    if existing_commit_raw is None or not hmac.compare_digest(
        existing_commit_raw, existing_intent_raw
    ):
        _fail("rejection commit is absent or differs from its intent")
    intent_stat = os.stat(_INTENT_FILE, dir_fd=directory_fd, follow_symlinks=False)
    commit_stat = os.stat(_COMMIT_FILE, dir_fd=directory_fd, follow_symlinks=False)
    if (intent_stat.st_dev, intent_stat.st_ino) != (
        commit_stat.st_dev,
        commit_stat.st_ino,
    ):
        _fail("rejection commit is not the atomic intent hard link")
    committed = _commit_from_document(
        _parse_exact(existing_commit_raw, _COMMIT_FIELDS, "rejection commit")
    )
    _append_cursor_state_locked(
        gate,
        directory_fd,
        state=H1AttemptRejectionGateStateV1.COMMITTED_UNACKNOWLEDGED,
        commit_id=committed.commit_id,
        ack_id=None,
    )
    if fault is H1AttemptRejectionCrashPointV1.AFTER_COMMIT_FSYNC:
        raise H1AttemptRejectionInjectedCrashV1("crash after durable commit")
    return committed


def commit_h1_attempt_rejection_v1(
    gate: H1AttemptRejectionGateHandleV1,
    *,
    writer_role: H1AttemptRejectionWriterRoleV1,
    decision_point_id: str,
    transaction_id: str,
    shared_owner_profile_core_id: str,
    rejection_request_id: str,
    source_kind: H1RejectionSourceKindV1,
    site_key: str,
    path: str,
    limit_kind: H1RejectionLimitKindV1,
    reservation_upper: int,
    candidate: int | None,
    hard_cap: int,
    reason_code: str,
    crash_point: H1AttemptRejectionCrashPointV1 = H1AttemptRejectionCrashPointV1.NONE,
) -> H1AttemptRejectionCommitV1:
    try:
        role = H1AttemptRejectionWriterRoleV1(writer_role)
        fault = H1AttemptRejectionCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "rejection writer role or crash point is invalid"
        ) from error
    if role is not H1AttemptRejectionWriterRoleV1.BROKER:
        _fail("only the broker API role may publish a rejection")
    gate, directory_fd, lock_fd = _require_handle(gate, fcntl.LOCK_EX)
    try:
        return _commit_rejection_locked(
            gate,
            directory_fd,
            decision_point_id=decision_point_id,
            transaction_id=transaction_id,
            shared_owner_profile_core_id=shared_owner_profile_core_id,
            rejection_request_id=rejection_request_id,
            source_kind=source_kind,
            site_key=site_key,
            path=path,
            limit_kind=limit_kind,
            reservation_upper=reservation_upper,
            candidate=candidate,
            hard_cap=hard_cap,
            reason_code=reason_code,
            fault=fault,
        )
    finally:
        _acquire_lock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        os.close(directory_fd)


@contextmanager
def hold_h1_attempt_gate_open_for_admission_v1(
    gate: H1AttemptRejectionGateHandleV1,
) -> Iterator[H1AttemptRejectionAdmissionLeaseV1]:
    """Serialize one admission decision against rejection under ``LOCK_EX``."""

    gate, directory_fd, lock_fd = _require_handle(gate, fcntl.LOCK_EX)
    lease = H1AttemptRejectionAdmissionLeaseV1(
        _LEASE_ISSUER,
        gate,
        directory_fd,
        lock_fd,
        threading.get_ident(),
    )
    context_token: Any | None = None
    try:
        state, _ = _replay_gate_locked(gate, directory_fd)
        if state is not H1AttemptRejectionGateStateV1.OPEN:
            raise H1AttemptRejectedV1(
                "attempt-wide cap rejection is durable; admission is forbidden"
            )
        context_token = _activate_gate_context(
            gate.spec.gate_id,
            _CONTEXT_ADMISSION_EXCLUSIVE,
        )
        yield lease
    finally:
        if context_token is not None:
            _ACTIVE_GATE_CONTEXTS.reset(context_token)
        lease._active = False
        _acquire_lock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        os.close(directory_fd)


def commit_h1_attempt_rejection_with_admission_lease_v1(
    lease: H1AttemptRejectionAdmissionLeaseV1,
    *,
    writer_role: H1AttemptRejectionWriterRoleV1,
    decision_point_id: str,
    transaction_id: str,
    shared_owner_profile_core_id: str,
    rejection_request_id: str,
    source_kind: H1RejectionSourceKindV1,
    site_key: str,
    path: str,
    limit_kind: H1RejectionLimitKindV1,
    reservation_upper: int,
    candidate: int | None,
    hard_cap: int,
    reason_code: str,
    crash_point: H1AttemptRejectionCrashPointV1 = H1AttemptRejectionCrashPointV1.NONE,
) -> H1AttemptRejectionCommitV1:
    if type(lease) is not H1AttemptRejectionAdmissionLeaseV1 or not lease._active:
        _fail("attempt-rejection admission lease is absent or stale")
    if threading.get_ident() != lease._owner_thread_id:
        _fail("attempt-rejection admission lease crossed its owning thread")
    if _active_gate_modes(lease.gate.spec.gate_id) != (
        _CONTEXT_ADMISSION_EXCLUSIVE,
    ):
        _fail("attempt-rejection admission lease left its active context")
    try:
        role = H1AttemptRejectionWriterRoleV1(writer_role)
        fault = H1AttemptRejectionCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "rejection writer role or crash point is invalid"
        ) from error
    if role is not H1AttemptRejectionWriterRoleV1.BROKER:
        _fail("only the broker API role may publish a rejection")
    with lease._commit_mutex:
        if not lease._active:
            _fail("attempt-rejection admission lease became stale")
        metadata = os.fstat(lease._directory_fd)
        if (metadata.st_dev, metadata.st_ino) != (
            lease.gate.gate_directory_device,
            lease.gate.gate_directory_inode,
        ):
            _fail("attempt-rejection admission lease directory changed")
        return _commit_rejection_locked(
            lease.gate,
            lease._directory_fd,
            decision_point_id=decision_point_id,
            transaction_id=transaction_id,
            shared_owner_profile_core_id=shared_owner_profile_core_id,
            rejection_request_id=rejection_request_id,
            source_kind=source_kind,
            site_key=site_key,
            path=path,
            limit_kind=limit_kind,
            reservation_upper=reservation_upper,
            candidate=candidate,
            hard_cap=hard_cap,
            reason_code=reason_code,
            fault=fault,
        )


def _replay_gate_locked(
    gate: H1AttemptRejectionGateHandleV1,
    directory_fd: int,
) -> tuple[H1AttemptRejectionGateStateV1, H1AttemptRejectionCommitV1 | None]:
    _cleanup_gate_temps(directory_fd)
    state, commit, _ = _observe_gate_locked(
        gate,
        directory_fd,
        advance_cursor=True,
    )
    if state is H1AttemptRejectionGateStateV1.INTENT_DURABLE:
        if not _link_intent_to_commit(directory_fd):
            _fail("rejection recovery could not publish the missing commit link")
        state, commit, _ = _observe_gate_locked(
            gate,
            directory_fd,
            advance_cursor=True,
        )
    return state, commit


def recover_h1_attempt_rejection_gate_v1(
    gate: H1AttemptRejectionGateHandleV1,
) -> H1AttemptRejectionGateStateV1:
    gate, directory_fd, lock_fd = _require_handle(gate, fcntl.LOCK_EX)
    try:
        state, _ = _replay_gate_locked(gate, directory_fd)
        return state
    finally:
        _acquire_lock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        os.close(directory_fd)


@contextmanager
def hold_h1_attempt_rejection_gate_for_replay_v1(
    gate: H1AttemptRejectionGateHandleV1,
) -> Iterator[H1AttemptRejectionGateReplaySnapshotV1]:
    """Replay exactly once and retain ``LOCK_EX`` across dependent replay.

    A dependent owner may acquire its own lock only after entering this
    context.  The gate state and exact commit/ack objects therefore cannot
    change before that dependent replay finishes.
    """

    gate, directory_fd, lock_fd = _require_handle(gate, fcntl.LOCK_EX)
    context_token: Any | None = None
    try:
        _replay_gate_locked(gate, directory_fd)
        state, commit, acknowledgement = _observe_gate_locked(
            gate,
            directory_fd,
            advance_cursor=False,
        )
        snapshot = H1AttemptRejectionGateReplaySnapshotV1(
            _REPLAY_SNAPSHOT_ISSUER,
            gate.spec.gate_id,
            state,
            commit,
            acknowledgement,
        )
        context_token = _activate_gate_context(
            gate.spec.gate_id,
            _CONTEXT_DEPENDENT_REPLAY_EXCLUSIVE,
        )
        yield snapshot
    finally:
        if context_token is not None:
            _ACTIVE_GATE_CONTEXTS.reset(context_token)
        _acquire_lock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        os.close(directory_fd)


def read_h1_attempt_rejection_commit_v1(
    gate: H1AttemptRejectionGateHandleV1,
) -> H1AttemptRejectionCommitV1 | None:
    gate, directory_fd, lock_fd = _require_handle(gate, fcntl.LOCK_SH)
    try:
        return _read_committed_pair_locked(gate, directory_fd)
    finally:
        _acquire_lock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        os.close(directory_fd)


def acknowledge_h1_attempt_rejection_v1(
    gate: H1AttemptRejectionGateHandleV1,
    commit: H1AttemptRejectionCommitV1,
    *,
    writer_role: H1AttemptRejectionWriterRoleV1,
    shared_owner_receipt_id: str,
    shared_owner_event_id: str,
    shared_owner_snapshot_id: str,
    crash_point: H1AttemptRejectionCrashPointV1 = H1AttemptRejectionCrashPointV1.NONE,
) -> H1AttemptRejectionAckV1:
    try:
        role = H1AttemptRejectionWriterRoleV1(writer_role)
        fault = H1AttemptRejectionCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptRejectionGateV1Error(
            "rejection ack writer role or crash point is invalid"
        ) from error
    if role is not H1AttemptRejectionWriterRoleV1.BROKER:
        _fail("only the broker API role may acknowledge a rejection")
    if type(gate) is not H1AttemptRejectionGateHandleV1:
        _fail("attempt-rejection gate handle has a foreign type")
    if type(commit) is not H1AttemptRejectionCommitV1:
        _fail("rejection acknowledgement requires one exact commit")
    commit_document = commit.to_document()
    if commit.gate_id != gate.spec.gate_id:
        _fail("rejection acknowledgement commit is stale or transplanted")
    # Validate every caller-supplied ACK operand before exclusive replay.  An
    # invalid acknowledgement must not turn an INTENT_DURABLE prefix into a
    # committed rejection as a side effect of argument validation.
    desired = H1AttemptRejectionAckV1(
        _ACK_ISSUER,
        gate.spec.gate_id,
        commit.commit_id,
        shared_owner_receipt_id,
        shared_owner_event_id,
        shared_owner_snapshot_id,
    )
    gate, directory_fd, lock_fd = _require_handle(gate, fcntl.LOCK_EX)
    try:
        _, durable = _replay_gate_locked(gate, directory_fd)
        if durable is None:
            _fail("rejection acknowledgement cannot precede durable commit")
        if durable.to_document() != commit_document:
            _fail("rejection acknowledgement commit is stale or transplanted")
        raw = desired.canonical_bytes
        if not _publish_new(directory_fd, _ACK_FILE, raw):
            existing = _read_file(directory_fd, _ACK_FILE)
            if existing is None or not hmac.compare_digest(existing, raw):
                _fail("a different acknowledgement already exists")
        _append_cursor_state_locked(
            gate,
            directory_fd,
            state=H1AttemptRejectionGateStateV1.ACKNOWLEDGED,
            commit_id=commit.commit_id,
            ack_id=desired.ack_id,
        )
        if fault is H1AttemptRejectionCrashPointV1.AFTER_ACK_FSYNC:
            raise H1AttemptRejectionInjectedCrashV1("crash after durable ack")
        return _ack_from_document(
            _parse_exact(raw, _ACK_FIELDS, "rejection acknowledgement")
        )
    finally:
        _acquire_lock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        os.close(directory_fd)


def require_h1_attempt_gate_open_before_side_effect_v1(
    gate: H1AttemptRejectionGateHandleV1,
) -> None:
    if type(gate) is not H1AttemptRejectionGateHandleV1:
        _fail("attempt-rejection gate handle has a foreign type")
    _reject_same_gate_context_reentry(
        gate.spec.gate_id,
        "require_h1_attempt_gate_open_before_side_effect_v1",
    )
    _fail(
        "point-in-time gate checks are TOCTOU-unsafe; hold the side-effect guard"
    )


@contextmanager
def hold_h1_attempt_gate_open_for_side_effect_v1(
    gate: H1AttemptRejectionGateHandleV1,
) -> Iterator[None]:
    """Hold the cross-process read lock from OPEN check through side effect.

    Every cooperating side-effect source must execute the entire native action
    inside this context.  A rejection commit takes the exclusive side of the
    same inode-pinned lock, giving the two operations one kernel-serialized
    order.  This does not assert that untrusted processes lack filesystem or
    syscall authority; those production credential claims remain false.
    """

    gate, directory_fd, lock_fd = _require_handle(gate, fcntl.LOCK_SH)
    context_token: Any | None = None
    try:
        state, _, _ = _observe_gate_locked(
            gate,
            directory_fd,
            advance_cursor=False,
        )
        if state is not H1AttemptRejectionGateStateV1.OPEN:
            raise H1AttemptRejectedV1(
                "attempt-wide cap rejection is durable; later side effects are forbidden"
            )
        context_token = _activate_gate_context(
            gate.spec.gate_id,
            _CONTEXT_SIDE_EFFECT_SHARED,
        )
        yield
    finally:
        if context_token is not None:
            _ACTIVE_GATE_CONTEXTS.reset(context_token)
        _acquire_lock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        os.close(directory_fd)


def h1_attempt_rejection_gate_snapshot_v1(
    gate: H1AttemptRejectionGateHandleV1,
) -> dict[str, Any]:
    gate, directory_fd, lock_fd = _require_handle(gate, fcntl.LOCK_EX)
    try:
        state, commit = _replay_gate_locked(gate, directory_fd)
        return {
            "schema": "acfqp.k7_h1_attempt_rejection_gate_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_attempt_rejection_gate_id": gate.spec.gate_id,
            "state": state.value,
            "h1_attempt_rejection_commit_id": (
                commit.commit_id
                if commit is not None
                else {"kind": "NOT_APPLICABLE", "reason": "NO_REJECTION_COMMITTED"}
            ),
            "control_cap_rejections": 1 if commit is not None else 0,
            "native_zero_eligible": False,
            "native_zero_blocker": "COMPLETE_ATTEMPT_JOURNAL_NOT_BOUND",
            "production_activation_chain_verified": False,
            "kernel_writer_credential_verified": False,
            "operational_io_accounting_connected": False,
            "formal_counter_eligible": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
        }
    finally:
        _acquire_lock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        os.close(directory_fd)


__all__ = (
    "ConstructionK7H1AttemptRejectionGateV1Error",
    "H1AttemptRejectedV1",
    "H1AttemptRejectionAckV1",
    "H1AttemptRejectionAdmissionLeaseV1",
    "H1AttemptRejectionCommitV1",
    "H1AttemptRejectionCrashPointV1",
    "H1AttemptRejectionGateHandleV1",
    "H1AttemptRejectionGateReplaySnapshotV1",
    "H1AttemptRejectionGateSpecV1",
    "H1AttemptRejectionGateStateV1",
    "H1AttemptRejectionInjectedCrashV1",
    "H1AttemptRejectionWriterRoleV1",
    "H1AttemptSecondRejectionV1",
    "H1RejectionLimitKindV1",
    "H1RejectionSourceKindV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SHARED_RESOURCE_PATHS",
    "acknowledge_h1_attempt_rejection_v1",
    "commit_h1_attempt_rejection_v1",
    "commit_h1_attempt_rejection_with_admission_lease_v1",
    "freeze_h1_attempt_rejection_gate_spec_v1",
    "h1_attempt_rejection_gate_snapshot_v1",
    "hold_h1_attempt_gate_open_for_side_effect_v1",
    "hold_h1_attempt_gate_open_for_admission_v1",
    "hold_h1_attempt_rejection_gate_for_replay_v1",
    "initialize_h1_attempt_rejection_gate_v1",
    "open_h1_attempt_rejection_gate_v1",
    "read_h1_attempt_rejection_commit_v1",
    "recover_h1_attempt_rejection_gate_v1",
    "require_h1_attempt_gate_open_before_side_effect_v1",
)
