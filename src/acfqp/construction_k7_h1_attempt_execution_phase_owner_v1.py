"""Attempt-wide durable NORMAL -> CLEANUP_ONLY phase authority.

This additive successor is orthogonal to the attempt rejection gate: cap
rejection can happen in either phase, while cleanup may be triggered by a
non-cap lifecycle failure.  The phase owner serializes one attempt through an
inode-bound exclusive lease and records exactly one immutable primary
transition.  It does not execute cleanup, recover a missing normal-site event,
or authorize production/native work.
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
import stat
import threading
from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_domain_registry_extension_v2 as domains_v2
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4
from acfqp import construction_k7_h1_tail_bound_prefix_attestation_v1 as tail_v1
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-B"
PROFILE_KEY = "construction_k7_h1_attempt_execution_phase_owner_v1"

PHASE_AUTHORITY_PRESENT = True
NORMAL_PHASE_LEASE_PRESENT = True
NORMAL_EXECUTION_LEASE_PRESENT = False
CLEANUP_ONLY_LEASE_PRESENT = True
LEASE_AWARE_NORMAL_DISPATCH_PRESENT = False
HISTORICAL_CAP_REJECTION_TRANSITION_REACHABLE = False
HISTORICAL_POST_REJECTION_PREFIX_ATTESTATION_REACHABLE = False
NO_EVENT_RECOVERY_COMPLETE = False
CLEANUP_ENVELOPE_PREADMITTED = False
CLEANUP_EXECUTION_AUTHORITY_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORD_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

SPEC_DOMAIN = domains_v2.CONSTRUCTION_K7_H1_ATTEMPT_EXECUTION_PHASE_SPEC_V1_DOMAIN
TRANSITION_DOMAIN = domains_v2.CONSTRUCTION_K7_H1_ATTEMPT_CLEANUP_TRANSITION_V1_DOMAIN
ALLOCATION_DOMAIN = domains_v2.CONSTRUCTION_K7_H1_ATTEMPT_PHASE_ALLOCATION_V1_DOMAIN

_ROOT_NAME = ".acfqp-k7-h1-attempt-execution-phase-v1"
_ROOT_LOCK = ".allocation.lock"
_SPEC_FILE = "phase-spec.json"
_LOCK_FILE = "phase.lock"
_CURSOR_FILE = "phase.cursor"
_INTENT_FILE = "cleanup-intent.json"
_COMMIT_FILE = "cleanup-commit.json"
_ALLOCATION_PREFIX = "allocation-"
_ROOT_TRANSITION_SEAL_PREFIX = "cleanup-transition-seal-"
_TEMP_PREFIX = ".tmp-"

_SPEC_ISSUER = object()
_HANDLE_ISSUER = object()
_TRANSITION_ISSUER = object()
_LEASE_ISSUER = object()
_ACTIVE_PHASE_LEASES: ContextVar[tuple[str, ...]] = ContextVar(
    "acfqp_k7_h1_active_phase_leases", default=()
)

_CURSOR_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "h1_attempt_execution_phase_spec_id",
        "sequence",
        "previous_phase_cursor_record_id",
        "state",
        "h1_attempt_cleanup_transition_id",
        "h1_attempt_phase_cursor_record_id",
    }
)
_ALLOCATION_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_attempt_execution_phase_spec_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "h1_attempt_rejection_gate_id",
        "phase_root_realpath",
        "phase_root_device",
        "phase_root_inode",
        "root_allocation_lock_device",
        "root_allocation_lock_inode",
        "phase_directory_realpath",
        "phase_directory_device",
        "phase_directory_inode",
        "phase_lock_device",
        "phase_lock_inode",
        "phase_cursor_device",
        "phase_cursor_inode",
        "attempt_split_brain_forbidden",
        "official_execution_allowed",
        "h1_attempt_phase_allocation_id",
    }
)
_TRANSITION_PAYLOAD_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_attempt_execution_phase_spec_id",
        "h1_attempt_phase_allocation_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "h1_attempt_rejection_gate_id",
        "h1_shared_cap_owner_v3_runtime_id",
        "h1_shared_cap_owner_v4_wal_binding_id",
        "decision_point_id",
        "transaction_id",
        "h1_lifecycle_dispatch_trace_id",
        "h1_lifecycle_dispatch_profile_id",
        "h1_prefix_verifier_semantic_closure_id",
        "h1_tail_bound_prefix_attestation_id",
        "h1_lifecycle_cleanup_pass_id",
        "h1_lifecycle_complete_branch_analysis_id",
        "branch_key",
        "primary_failure_event_id",
        "primary_failure_site_key",
        "primary_failure_outcome",
        "primary_failure_trigger_kind",
        "owner_tail_sequence_at_transition",
        "owner_tail_head_id_at_transition",
        "gate_state_at_transition",
        "gate_owner_join_status_at_transition",
        "from_phase",
        "to_phase",
        "normal_phase_never_reopens",
        "primary_failure_immutable",
        "secondary_failures_append_only",
        "phase_gate_owner_snapshot_held_during_intent_publish",
        "historical_normal_lane_coverage_present",
        "no_event_recovery_complete",
        "cleanup_envelope_preadmitted",
        "cleanup_execution_authority_present",
        "production_execution_authority_present",
        "formal_counter_record_issued",
        "formal_work_vector_issued",
        "formal_comparison_vector_issued",
        "formal_v7_route_authority_present",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "official_execution_allowed",
    }
)


class ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(ValueError):
    """The attempt phase identity, layout, transition, or lease failed."""


class H1AttemptPhaseInjectedCrashV1(RuntimeError):
    """Test-only interruption after one durable phase transition boundary."""


class H1AttemptExecutionPhaseV1(str, Enum):
    NORMAL = "NORMAL"
    CLEANUP_INTENT_DURABLE = "CLEANUP_INTENT_DURABLE"
    CLEANUP_ONLY = "CLEANUP_ONLY"


class H1AttemptPhaseLeaseKindV1(str, Enum):
    NORMAL_PHASE = "NORMAL_PHASE"
    TRANSITION_ONLY = "TRANSITION_ONLY"
    CLEANUP_PHASE = "CLEANUP_PHASE"


class H1AttemptPhaseCrashPointV1(str, Enum):
    NONE = "NONE"
    AFTER_INTENT_FSYNC = "AFTER_INTENT_FSYNC"
    AFTER_INTENT_CURSOR_FSYNC = "AFTER_INTENT_CURSOR_FSYNC"
    AFTER_COMMIT_LINK_FSYNC = "AFTER_COMMIT_LINK_FSYNC"
    AFTER_CLEANUP_CURSOR_FSYNC = "AFTER_CLEANUP_CURSOR_FSYNC"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{label} must be one nonempty exact string")
    return value


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _phase_content_id(domain: str, payload: Any) -> str:
    return domains_v2.extension_content_id_v2(domain, payload)


def _open_directory(path: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
            f"phase directory cannot be opened safely: {path}"
        ) from error
    os.set_inheritable(descriptor, False)
    return descriptor


def _open_directory_at(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as error:
        raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
            f"phase child directory cannot be opened safely: {name}"
        ) from error
    os.set_inheritable(descriptor, False)
    return descriptor


def _open_regular_at(
    directory_fd: int,
    name: str,
    *,
    flags: int,
    mode: int | None = None,
) -> int:
    options = flags | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        options |= os.O_NOFOLLOW
    try:
        if mode is None:
            descriptor = os.open(name, options, dir_fd=directory_fd)
        else:
            descriptor = os.open(name, options, mode, dir_fd=directory_fd)
    except OSError as error:
        raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
            f"phase regular file cannot be opened safely: {name}"
        ) from error
    os.set_inheritable(descriptor, False)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        os.close(descriptor)
        _fail(f"phase path is not one regular file: {name}")
    return descriptor


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:  # pragma: no cover - OS invariant
            _fail("phase file write made no progress")
        view = view[written:]


def _read_descriptor(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 1 << 16)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _read_file(directory_fd: int, name: str) -> bytes | None:
    try:
        descriptor = _open_regular_at(directory_fd, name, flags=os.O_RDONLY)
    except ConstructionK7H1AttemptExecutionPhaseOwnerV1Error as error:
        try:
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        raise error
    try:
        return _read_descriptor(descriptor)
    finally:
        os.close(descriptor)


def _read_file_with_metadata(
    directory_fd: int,
    name: str,
) -> tuple[bytes, os.stat_result] | None:
    try:
        descriptor = _open_regular_at(directory_fd, name, flags=os.O_RDONLY)
    except ConstructionK7H1AttemptExecutionPhaseOwnerV1Error as error:
        try:
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        raise error
    try:
        return _read_descriptor(descriptor), os.fstat(descriptor)
    finally:
        os.close(descriptor)


def _publish_new(directory_fd: int, name: str, raw: bytes, *, mode: int = 0o400) -> bool:
    token = hashlib.sha256(raw).hexdigest()[:16]
    temporary = f"{_TEMP_PREFIX}{os.getpid()}-{threading.get_ident()}-{token}"
    descriptor = _open_regular_at(
        directory_fd,
        temporary,
        flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        mode=0o600,
    )
    try:
        _write_all(descriptor, raw)
        os.fsync(descriptor)
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
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
        except FileNotFoundError:  # pragma: no cover - exact temp lifecycle
            pass
    return published


def _cleanup_temps(directory_fd: int) -> None:
    for name in os.listdir(directory_fd):
        if name.startswith(_TEMP_PREFIX):
            os.unlink(name, dir_fd=directory_fd)
    os.fsync(directory_fd)


def _require_mode(metadata: os.stat_result, expected: int, label: str) -> None:
    if stat.S_IMODE(metadata.st_mode) != expected:
        _fail(f"{label} mode changed")


@dataclass(frozen=True, slots=True)
class H1AttemptExecutionPhaseSpecV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SPEC_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("phase spec is caller-minted")
        payload = loads_canonical_json(self.payload_bytes)
        if type(payload) is not dict or canonical_json_bytes(payload) != self.payload_bytes:
            _fail("phase spec payload is not canonical")
        object.__setattr__(self, "_spec_id", _phase_content_id(SPEC_DOMAIN, payload))

    @property
    def spec_id(self) -> str:
        return self._spec_id

    @property
    def payload(self) -> dict[str, Any]:
        value = loads_canonical_json(self.payload_bytes)
        if type(value) is not dict:  # pragma: no cover - issuer invariant
            _fail("phase spec changed type")
        return value

    def to_document(self) -> dict[str, Any]:
        return {**self.payload, "h1_attempt_execution_phase_spec_id": self.spec_id}


def freeze_h1_attempt_execution_phase_spec_v1(
    base_directory: str | Path,
    *,
    logical_occurrence_id: str,
    route_attempt_id: str,
    caller_pinned_lifecycle_provenance_id: str,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
    anchored_program_id: str,
    handler_registry_id: str,
    cleanup_analysis: cleanup_v1.H1LifecycleCompleteBranchAnalysisV1,
) -> H1AttemptExecutionPhaseSpecV1:
    if (
        type(rejection_gate) is not rejection_v1.H1AttemptRejectionGateHandleV1
        or type(cleanup_analysis) is not cleanup_v1.H1LifecycleCompleteBranchAnalysisV1
    ):
        _fail("phase spec requires exact gate and cleanup-analysis objects")
    occurrence = _cid(logical_occurrence_id, "phase logical occurrence")
    attempt = _cid(route_attempt_id, "phase route attempt")
    provenance = _cid(
        caller_pinned_lifecycle_provenance_id,
        "phase lifecycle provenance",
    )
    gate_spec = rejection_gate.spec
    if (
        gate_spec.logical_occurrence_id != occurrence
        or gate_spec.route_attempt_id != attempt
        or gate_spec.caller_pinned_lifecycle_provenance_id != provenance
    ):
        _fail("phase spec crossed its attempt rejection gate")
    base = Path(base_directory).resolve(strict=True)
    base_metadata = base.stat()
    if not stat.S_ISDIR(base_metadata.st_mode):
        _fail("phase base is not a directory")
    analysis = cleanup_analysis.payload
    program = _cid(anchored_program_id, "phase anchored program")
    registry = _cid(handler_registry_id, "phase handler registry")
    if (
        analysis["h1_anchored_lifecycle_program_id"] != program
        or analysis["h1_anchored_lifecycle_handler_registry_id"] != registry
    ):
        _fail("phase spec crossed its cleanup analysis")
    payload = {
        "schema": "acfqp.k7_h1_attempt_execution_phase_spec.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_id": occurrence,
        "route_attempt_id": attempt,
        "caller_pinned_lifecycle_provenance_id": provenance,
        "h1_attempt_rejection_gate_id": rejection_gate.spec.gate_id,
        "h1_anchored_lifecycle_program_id": program,
        "h1_anchored_lifecycle_handler_registry_id": registry,
        "h1_lifecycle_complete_branch_analysis_id": cleanup_analysis.analysis_id,
        "phase_base_realpath": str(base),
        "phase_base_device": base_metadata.st_dev,
        "phase_base_inode": base_metadata.st_ino,
        "attempt_wide_not_transaction_scoped": True,
        "single_primary_cleanup_transition": True,
        "lock_order": "PHASE_EX_THEN_GATE_THEN_OWNER_THEN_NATIVE",
        "normal_and_cleanup_leases_exclusive": True,
        "normal_phase_lease_is_execution_integration": False,
        "lease_aware_normal_dispatch_present": False,
        "cleanup_execution_authority_present": False,
        "production_execution_authority_present": False,
        "official_execution_allowed": False,
    }
    return H1AttemptExecutionPhaseSpecV1(
        _SPEC_ISSUER,
        canonical_json_bytes(payload),
    )


@dataclass(frozen=True, slots=True)
class H1AttemptExecutionPhaseOwnerV1Handle:
    _issuer: InitVar[object]
    spec: H1AttemptExecutionPhaseSpecV1
    allocation_id: str
    root_directory: str
    root_device: int
    root_inode: int
    root_allocation_lock_device: int
    root_allocation_lock_inode: int
    phase_directory: str
    phase_device: int
    phase_inode: int
    lock_device: int
    lock_inode: int
    cursor_device: int
    cursor_inode: int
    gate_directory: str

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _HANDLE_ISSUER
            or type(self.spec) is not H1AttemptExecutionPhaseSpecV1
        ):
            _fail("phase handle is caller-minted")
        _cid(self.allocation_id, "phase allocation")

    @property
    def spec_id(self) -> str:
        return self.spec.spec_id

    @property
    def route_attempt_id(self) -> str:
        return self.spec.payload["route_attempt_id"]

    def __reduce__(self) -> NoReturn:
        _fail("phase handle is not serializable")


@dataclass(frozen=True, slots=True)
class H1AttemptCleanupTransitionV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _transition_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TRANSITION_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("cleanup transition is caller-minted")
        payload = loads_canonical_json(self.payload_bytes)
        if type(payload) is not dict or canonical_json_bytes(payload) != self.payload_bytes:
            _fail("cleanup transition is not canonical")
        object.__setattr__(
            self,
            "_transition_id",
            _phase_content_id(TRANSITION_DOMAIN, payload),
        )

    @property
    def transition_id(self) -> str:
        return self._transition_id

    @property
    def payload(self) -> dict[str, Any]:
        value = loads_canonical_json(self.payload_bytes)
        if type(value) is not dict:  # pragma: no cover
            _fail("cleanup transition changed type")
        return value

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self.payload,
            "h1_attempt_cleanup_transition_id": self.transition_id,
        }


@dataclass(slots=True)
class H1AttemptExecutionPhaseLeaseV1:
    _issuer: InitVar[object]
    handle: H1AttemptExecutionPhaseOwnerV1Handle
    phase: H1AttemptExecutionPhaseV1
    lease_kind: H1AttemptPhaseLeaseKindV1
    transition_id: str | None
    _root_fd: int = field(repr=False)
    _phase_fd: int = field(repr=False)
    _lock_fd: int = field(repr=False)
    _cursor_fd: int = field(repr=False)
    _gate_context: Any = field(repr=False)
    _gate_snapshot: rejection_v1.H1AttemptRejectionGateReplaySnapshotV1 = field(
        repr=False
    )
    _owner_pid: int = field(repr=False)
    _owner_thread_id: int = field(repr=False)
    _active: bool = field(default=True, repr=False)
    _transitioned: bool = field(default=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _LEASE_ISSUER:
            _fail("phase lease is caller-minted")
        if (
            type(self._gate_snapshot)
            is not rejection_v1.H1AttemptRejectionGateReplaySnapshotV1
        ):
            _fail("phase lease lacks one exact retained rejection-gate snapshot")
        for descriptor in (
            self._root_fd,
            self._phase_fd,
            self._lock_fd,
            self._cursor_fd,
        ):
            if os.get_inheritable(descriptor):
                _fail("phase lease descriptor is inheritable")

    def __reduce__(self) -> NoReturn:
        _fail("phase lease is not serializable")


def _spec_raw(spec: H1AttemptExecutionPhaseSpecV1) -> bytes:
    return canonical_json_bytes(spec.to_document())


def _allocation_name(route_attempt_id: str) -> str:
    return f"{_ALLOCATION_PREFIX}{route_attempt_id}.json"


def _root_transition_seal_name(route_attempt_id: str) -> str:
    return f"{_ROOT_TRANSITION_SEAL_PREFIX}{route_attempt_id}.json"


def _allocation_document(
    spec: H1AttemptExecutionPhaseSpecV1,
    *,
    root_path: Path,
    root_metadata: os.stat_result,
    root_allocation_lock_metadata: os.stat_result,
    phase_path: Path,
    phase_metadata: os.stat_result,
    lock_metadata: os.stat_result,
    cursor_metadata: os.stat_result,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.k7_h1_attempt_phase_allocation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_attempt_execution_phase_spec_id": spec.spec_id,
        "logical_occurrence_id": spec.payload["logical_occurrence_id"],
        "route_attempt_id": spec.payload["route_attempt_id"],
        "h1_attempt_rejection_gate_id": spec.payload[
            "h1_attempt_rejection_gate_id"
        ],
        "phase_root_realpath": str(root_path),
        "phase_root_device": root_metadata.st_dev,
        "phase_root_inode": root_metadata.st_ino,
        "root_allocation_lock_device": root_allocation_lock_metadata.st_dev,
        "root_allocation_lock_inode": root_allocation_lock_metadata.st_ino,
        "phase_directory_realpath": str(phase_path),
        "phase_directory_device": phase_metadata.st_dev,
        "phase_directory_inode": phase_metadata.st_ino,
        "phase_lock_device": lock_metadata.st_dev,
        "phase_lock_inode": lock_metadata.st_ino,
        "phase_cursor_device": cursor_metadata.st_dev,
        "phase_cursor_inode": cursor_metadata.st_ino,
        "attempt_split_brain_forbidden": True,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "h1_attempt_phase_allocation_id": _phase_content_id(
            ALLOCATION_DOMAIN, payload
        ),
    }


def _parse_allocation(raw: bytes) -> tuple[dict[str, Any], str]:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
            "phase allocation is not canonical"
        ) from error
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != raw
        or frozenset(document) != _ALLOCATION_FIELDS
        or document.get("schema") != "acfqp.k7_h1_attempt_phase_allocation.v1"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("proposed_contract_version") != PROPOSED_CONTRACT_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("attempt_split_brain_forbidden") is not True
        or document.get("official_execution_allowed") is not False
    ):
        _fail("phase allocation is not one canonical object")
    numeric_fields = (
        "phase_root_device",
        "phase_root_inode",
        "root_allocation_lock_device",
        "root_allocation_lock_inode",
        "phase_directory_device",
        "phase_directory_inode",
        "phase_lock_device",
        "phase_lock_inode",
        "phase_cursor_device",
        "phase_cursor_inode",
    )
    if any(
        type(document[key]) is not int or document[key] < 0
        for key in numeric_fields
    ):
        _fail("phase allocation contains a mistyped filesystem identity")
    for key in ("phase_root_realpath", "phase_directory_realpath"):
        if type(document[key]) is not str or not Path(document[key]).is_absolute():
            _fail("phase allocation path is not one absolute exact string")
    claimed = _cid(
        document.get("h1_attempt_phase_allocation_id"),
        "phase allocation",
    )
    payload = dict(document)
    payload.pop("h1_attempt_phase_allocation_id", None)
    if _phase_content_id(ALLOCATION_DOMAIN, payload) != claimed:
        _fail("phase allocation content identity changed")
    return document, claimed


def _cursor_record(
    *,
    spec_id: str,
    sequence: int,
    previous_id: Any,
    state: H1AttemptExecutionPhaseV1,
    transition_id: Any,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.k7_h1_attempt_phase_cursor.v1",
        "schema_version": SCHEMA_VERSION,
        "h1_attempt_execution_phase_spec_id": spec_id,
        "sequence": sequence,
        "previous_phase_cursor_record_id": previous_id,
        "state": state.value,
        "h1_attempt_cleanup_transition_id": transition_id,
    }
    return {
        **payload,
        "h1_attempt_phase_cursor_record_id": hashlib.sha256(
            b"acfqp:k7-h1-attempt-phase-cursor:v1\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _cursor_genesis(spec_id: str) -> dict[str, Any]:
    return _cursor_record(
        spec_id=spec_id,
        sequence=0,
        previous_id=_typed_null("PHASE_CURSOR_GENESIS"),
        state=H1AttemptExecutionPhaseV1.NORMAL,
        transition_id=_typed_null("NO_CLEANUP_TRANSITION"),
    )


def _parse_cursor(raw: bytes, spec_id: str) -> list[dict[str, Any]]:
    if not raw or not raw.endswith(b"\n"):
        _fail("phase cursor is empty or has a torn final frame")
    records: list[dict[str, Any]] = []
    previous: str | None = None
    for sequence, line in enumerate(raw.splitlines()):
        try:
            document = loads_canonical_json(line)
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
                "phase cursor frame is not canonical"
            ) from error
        if (
            type(document) is not dict
            or frozenset(document) != _CURSOR_FIELDS
            or document.get("schema") != "acfqp.k7_h1_attempt_phase_cursor.v1"
            or document.get("schema_version") != SCHEMA_VERSION
            or type(document.get("sequence")) is not int
        ):
            _fail("phase cursor frame is not one object")
        claimed = _cid(
            document.get("h1_attempt_phase_cursor_record_id"),
            "phase cursor record",
        )
        payload = dict(document)
        payload.pop("h1_attempt_phase_cursor_record_id", None)
        expected = hashlib.sha256(
            b"acfqp:k7-h1-attempt-phase-cursor:v1\x00"
            + canonical_json_bytes(payload)
        ).hexdigest()
        if (
            claimed != expected
            or document.get("sequence") != sequence
            or document.get("h1_attempt_execution_phase_spec_id") != spec_id
            or document.get("previous_phase_cursor_record_id")
            != (
                previous
                if previous is not None
                else _typed_null("PHASE_CURSOR_GENESIS")
            )
        ):
            _fail("phase cursor chain changed")
        try:
            state = H1AttemptExecutionPhaseV1(document.get("state"))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
                "phase cursor state is invalid"
            ) from error
        if sequence == 0:
            if document != _cursor_genesis(spec_id):
                _fail("phase cursor genesis changed")
        else:
            prior_state = H1AttemptExecutionPhaseV1(records[-1]["state"])
            transition = _cid(
                document.get("h1_attempt_cleanup_transition_id"),
                "phase cursor transition",
            )
            prior_transition = records[-1]["h1_attempt_cleanup_transition_id"]
            if (
                (prior_state is H1AttemptExecutionPhaseV1.NORMAL and state
                 is not H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE)
                or (
                    prior_state
                    is H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE
                    and state is not H1AttemptExecutionPhaseV1.CLEANUP_ONLY
                )
                or prior_state is H1AttemptExecutionPhaseV1.CLEANUP_ONLY
                or (
                    sequence > 1
                    and prior_transition != transition
                )
            ):
                _fail("phase cursor is not one monotonic transition")
        records.append(document)
        previous = claimed
    if len(records) > 3:
        _fail("phase cursor contains more than one cleanup transition")
    return records


def _read_repairable_cursor_locked(
    cursor_fd: int,
    spec_id: str,
    *,
    transition_id: str | None,
) -> list[dict[str, Any]]:
    """Read the append-only cursor, repairing only a crash-torn final frame.

    A transition payload is fsynced before either non-genesis cursor record.
    Consequently a nonempty canonical prefix plus a non-newline suffix may be
    truncated only when that immutable payload is present.  Complete corrupt
    frames and a torn genesis remain integrity failures.
    """

    raw = _read_descriptor(cursor_fd)
    if raw.endswith(b"\n"):
        return _parse_cursor(raw, spec_id)
    if transition_id is None:
        _fail("phase cursor is empty or has a torn genesis frame")
    boundary = raw.rfind(b"\n")
    if boundary < 0:
        _fail("phase cursor lost its complete genesis frame")
    prefix = raw[: boundary + 1]
    records = _parse_cursor(prefix, spec_id)
    state = H1AttemptExecutionPhaseV1(records[-1]["state"])
    if state is H1AttemptExecutionPhaseV1.NORMAL:
        next_state = H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE
    elif state is H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE:
        next_state = H1AttemptExecutionPhaseV1.CLEANUP_ONLY
    else:
        _fail("phase cursor has bytes after its terminal CLEANUP_ONLY frame")
    expected = canonical_json_bytes(
        _cursor_record(
            spec_id=spec_id,
            sequence=len(records),
            previous_id=records[-1]["h1_attempt_phase_cursor_record_id"],
            state=next_state,
            transition_id=transition_id,
        )
    ) + b"\n"
    suffix = raw[boundary + 1 :]
    if not expected.startswith(suffix) or len(suffix) >= len(expected):
        _fail("phase cursor suffix is not the expected crash-torn next frame")
    os.ftruncate(cursor_fd, len(prefix))
    os.fsync(cursor_fd)
    return records


def _append_cursor(
    cursor_fd: int,
    records: list[dict[str, Any]],
    *,
    spec_id: str,
    state: H1AttemptExecutionPhaseV1,
    transition_id: str,
) -> list[dict[str, Any]]:
    record = _cursor_record(
        spec_id=spec_id,
        sequence=len(records),
        previous_id=records[-1]["h1_attempt_phase_cursor_record_id"],
        state=state,
        transition_id=transition_id,
    )
    os.lseek(cursor_fd, 0, os.SEEK_END)
    _write_all(cursor_fd, canonical_json_bytes(record) + b"\n")
    os.fsync(cursor_fd)
    return [*records, record]


def _transition_from_raw(raw: bytes) -> H1AttemptCleanupTransitionV1:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
            "cleanup transition file is not canonical"
        ) from error
    if type(document) is not dict:
        _fail("cleanup transition file is not one object")
    claimed = _cid(
        document.pop("h1_attempt_cleanup_transition_id", None),
        "cleanup transition",
    )
    if (
        frozenset(document) != _TRANSITION_PAYLOAD_FIELDS
        or document.get("schema") != "acfqp.k7_h1_attempt_cleanup_transition.v1"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("proposed_contract_version") != PROPOSED_CONTRACT_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("from_phase") != H1AttemptExecutionPhaseV1.NORMAL.value
        or document.get("to_phase") != H1AttemptExecutionPhaseV1.CLEANUP_ONLY.value
        or document.get("normal_phase_never_reopens") is not True
        or document.get("primary_failure_immutable") is not True
        or document.get("phase_gate_owner_snapshot_held_during_intent_publish")
        is not True
        or document.get("official_execution_allowed") is not False
    ):
        _fail("cleanup transition schema or frozen claims changed")
    transition = H1AttemptCleanupTransitionV1(
        _TRANSITION_ISSUER,
        canonical_json_bytes(document),
    )
    if transition.transition_id != claimed or transition.canonical_bytes != raw:
        _fail("cleanup transition content identity changed")
    return transition


def _validate_transition_for_handle(
    transition: H1AttemptCleanupTransitionV1,
    handle: H1AttemptExecutionPhaseOwnerV1Handle,
) -> None:
    payload = transition.payload
    spec = handle.spec.payload
    if (
        payload["h1_attempt_execution_phase_spec_id"] != handle.spec_id
        or payload["h1_attempt_phase_allocation_id"] != handle.allocation_id
        or payload["logical_occurrence_id"] != spec["logical_occurrence_id"]
        or payload["route_attempt_id"] != spec["route_attempt_id"]
        or payload["h1_attempt_rejection_gate_id"]
        != spec["h1_attempt_rejection_gate_id"]
        or payload["h1_lifecycle_complete_branch_analysis_id"]
        != spec["h1_lifecycle_complete_branch_analysis_id"]
        or payload["from_phase"] != H1AttemptExecutionPhaseV1.NORMAL.value
        or payload["to_phase"] != H1AttemptExecutionPhaseV1.CLEANUP_ONLY.value
    ):
        _fail("cleanup transition crossed its immutable phase identity")
    for key in (
        "h1_shared_cap_owner_v3_runtime_id",
        "h1_shared_cap_owner_v4_wal_binding_id",
        "decision_point_id",
        "transaction_id",
        "h1_lifecycle_dispatch_trace_id",
        "h1_lifecycle_dispatch_profile_id",
        "h1_prefix_verifier_semantic_closure_id",
        "h1_tail_bound_prefix_attestation_id",
        "h1_lifecycle_cleanup_pass_id",
        "h1_lifecycle_complete_branch_analysis_id",
        "primary_failure_event_id",
    ):
        _cid(payload[key], f"cleanup transition {key}")
    if type(payload["owner_tail_sequence_at_transition"]) is not int or payload[
        "owner_tail_sequence_at_transition"
    ] < 0:
        _fail("cleanup transition Owner sequence is not one nonnegative integer")
    head = payload["owner_tail_head_id_at_transition"]
    if payload["owner_tail_sequence_at_transition"] == 0:
        if head != _typed_null("JOURNAL_GENESIS"):
            _fail("cleanup transition genesis head is invalid")
    else:
        _cid(head, "cleanup transition Owner head")
    try:
        rejection_v1.H1AttemptRejectionGateStateV1(
            payload["gate_state_at_transition"]
        )
        owner_v3.H1SharedGateOwnerJoinStatusV3(
            payload["gate_owner_join_status_at_transition"]
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
            "cleanup transition gate/Owner state is invalid"
        ) from error
    outcome = _nonempty(
        payload["primary_failure_outcome"],
        "cleanup transition primary failure outcome",
    )
    expected_trigger = (
        "CAP_REJECTION"
        if outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT"
        else "LIFECYCLE_FAILURE"
    )
    site = _nonempty(
        payload["primary_failure_site_key"],
        "cleanup transition primary failure site",
    )
    expected_branch = (
        f"SUPPLEMENTAL:{site}:{outcome}"
        if outcome == cleanup_v1._SUPPLEMENTAL_OUTCOME
        else f"FAIL:{site}:{outcome}"
    )
    if (
        payload["primary_failure_trigger_kind"] != expected_trigger
        or payload["branch_key"] != expected_branch
        or (
            expected_trigger == "CAP_REJECTION"
            and payload["gate_state_at_transition"]
            == rejection_v1.H1AttemptRejectionGateStateV1.OPEN.value
        )
    ):
        _fail("cleanup transition primary failure classification changed")
    exact_true = (
        "normal_phase_never_reopens",
        "primary_failure_immutable",
        "secondary_failures_append_only",
        "phase_gate_owner_snapshot_held_during_intent_publish",
    )
    exact_false = (
        "historical_normal_lane_coverage_present",
        "no_event_recovery_complete",
        "cleanup_envelope_preadmitted",
        "cleanup_execution_authority_present",
        "production_execution_authority_present",
        "formal_counter_record_issued",
        "formal_work_vector_issued",
        "formal_comparison_vector_issued",
        "formal_v7_route_authority_present",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "official_execution_allowed",
    )
    if any(payload[key] is not True for key in exact_true) or any(
        payload[key] is not False for key in exact_false
    ):
        _fail("cleanup transition frozen claim values changed")


def _link_intent_to_commit(phase_fd: int) -> bool:
    try:
        os.link(
            _INTENT_FILE,
            _COMMIT_FILE,
            src_dir_fd=phase_fd,
            dst_dir_fd=phase_fd,
            follow_symlinks=False,
        )
        os.fsync(phase_fd)
        return True
    except FileExistsError:
        return False


def _link_between_directories(
    source_fd: int,
    source_name: str,
    target_fd: int,
    target_name: str,
) -> bool:
    try:
        os.link(
            source_name,
            target_name,
            src_dir_fd=source_fd,
            dst_dir_fd=target_fd,
            follow_symlinks=False,
        )
        os.fsync(target_fd)
        return True
    except FileExistsError:
        return False


def _reconcile_root_transition_seal_locked(
    root_fd: int,
    phase_fd: int,
    handle: H1AttemptExecutionPhaseOwnerV1Handle,
) -> tuple[bytes, os.stat_result] | None:
    seal_name = _root_transition_seal_name(handle.route_attempt_id)
    intent_entry = _read_file_with_metadata(phase_fd, _INTENT_FILE)
    seal_entry = _read_file_with_metadata(root_fd, seal_name)
    if intent_entry is None and seal_entry is not None:
        _require_mode(seal_entry[1], 0o400, "root cleanup transition seal")
        if not _link_between_directories(
            root_fd,
            seal_name,
            phase_fd,
            _INTENT_FILE,
        ):
            _fail("root cleanup transition seal recovery conflicted")
        intent_entry = _read_file_with_metadata(phase_fd, _INTENT_FILE)
    elif intent_entry is not None and seal_entry is None:
        _require_mode(intent_entry[1], 0o400, "phase cleanup intent")
        if not _link_between_directories(
            phase_fd,
            _INTENT_FILE,
            root_fd,
            seal_name,
        ):
            _fail("root cleanup transition seal publication conflicted")
        seal_entry = _read_file_with_metadata(root_fd, seal_name)
    if intent_entry is None:
        return None
    if seal_entry is None:  # pragma: no cover - exact hard-link convergence
        _fail("root cleanup transition seal did not converge")
    _require_mode(intent_entry[1], 0o400, "phase cleanup intent")
    _require_mode(seal_entry[1], 0o400, "root cleanup transition seal")
    if (
        not hmac.compare_digest(intent_entry[0], seal_entry[0])
        or (intent_entry[1].st_dev, intent_entry[1].st_ino)
        != (seal_entry[1].st_dev, seal_entry[1].st_ino)
    ):
        _fail("root cleanup transition seal differs from the phase intent")
    return intent_entry


def _open_cursor_locked(
    phase_fd: int,
    handle: H1AttemptExecutionPhaseOwnerV1Handle,
) -> int:
    cursor_fd = _open_regular_at(phase_fd, _CURSOR_FILE, flags=os.O_RDWR)
    metadata = os.fstat(cursor_fd)
    _require_mode(metadata, 0o600, "phase cursor")
    if (metadata.st_dev, metadata.st_ino) != (
        handle.cursor_device,
        handle.cursor_inode,
    ):
        os.close(cursor_fd)
        _fail("phase cursor inode changed")
    return cursor_fd


def _recover_locked(
    root_fd: int,
    phase_fd: int,
    cursor_fd: int,
    handle: H1AttemptExecutionPhaseOwnerV1Handle,
) -> tuple[H1AttemptExecutionPhaseV1, H1AttemptCleanupTransitionV1 | None]:
    _cleanup_temps(phase_fd)
    intent_entry = _reconcile_root_transition_seal_locked(
        root_fd,
        phase_fd,
        handle,
    )
    commit_entry = _read_file_with_metadata(phase_fd, _COMMIT_FILE)
    intent_raw = intent_entry[0] if intent_entry is not None else None
    commit_raw = commit_entry[0] if commit_entry is not None else None
    if intent_entry is not None:
        _require_mode(intent_entry[1], 0o400, "phase cleanup intent")
    if commit_entry is not None:
        _require_mode(commit_entry[1], 0o400, "phase cleanup commit")
    if commit_raw is not None and intent_raw is None:
        _fail("phase cleanup commit exists without its intent")
    transition = _transition_from_raw(intent_raw) if intent_raw is not None else None
    if transition is not None:
        _validate_transition_for_handle(transition, handle)
    if commit_raw is not None:
        if not hmac.compare_digest(commit_raw, intent_raw):
            _fail("phase cleanup commit differs from its intent")
        if (
            intent_entry is None
            or (commit_entry[1].st_dev, commit_entry[1].st_ino)
            != (intent_entry[1].st_dev, intent_entry[1].st_ino)
        ):
            _fail("phase cleanup commit is not the immutable intent hard link")
    records = _read_repairable_cursor_locked(
        cursor_fd,
        handle.spec_id,
        transition_id=(transition.transition_id if transition is not None else None),
    )
    state = H1AttemptExecutionPhaseV1(records[-1]["state"])
    if transition is None:
        if state is not H1AttemptExecutionPhaseV1.NORMAL:
            _fail("phase cursor retained cleanup after transition files disappeared")
        return state, None
    transition_id = transition.transition_id
    cursor_transition = records[-1]["h1_attempt_cleanup_transition_id"]
    if state is H1AttemptExecutionPhaseV1.NORMAL:
        records = _append_cursor(
            cursor_fd,
            records,
            spec_id=handle.spec_id,
            state=H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE,
            transition_id=transition_id,
        )
        state = H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE
        cursor_transition = transition_id
    if cursor_transition != transition_id:
        _fail("phase cursor and cleanup intent name different transitions")
    if state is H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE:
        if commit_raw is None:
            if not _link_intent_to_commit(phase_fd):
                _fail("phase cleanup commit link conflicted")
            commit_raw = _read_file(phase_fd, _COMMIT_FILE)
        if commit_raw is None or not hmac.compare_digest(commit_raw, intent_raw):
            _fail("phase cleanup commit did not converge")
        records = _append_cursor(
            cursor_fd,
            records,
            spec_id=handle.spec_id,
            state=H1AttemptExecutionPhaseV1.CLEANUP_ONLY,
            transition_id=transition_id,
        )
        state = H1AttemptExecutionPhaseV1.CLEANUP_ONLY
    if state is not H1AttemptExecutionPhaseV1.CLEANUP_ONLY or commit_raw is None:
        _fail("phase transition did not converge to CLEANUP_ONLY")
    return state, transition


def _validate_live_gate(
    spec: H1AttemptExecutionPhaseSpecV1,
    gate: rejection_v1.H1AttemptRejectionGateHandleV1,
) -> None:
    if type(gate) is not rejection_v1.H1AttemptRejectionGateHandleV1:
        _fail("phase owner requires one exact rejection gate")
    payload = spec.payload
    if (
        gate.spec.gate_id != payload["h1_attempt_rejection_gate_id"]
        or gate.spec.logical_occurrence_id != payload["logical_occurrence_id"]
        or gate.spec.route_attempt_id != payload["route_attempt_id"]
        or gate.spec.caller_pinned_lifecycle_provenance_id
        != payload["caller_pinned_lifecycle_provenance_id"]
    ):
        _fail("phase owner crossed its live rejection gate")


def initialize_h1_attempt_execution_phase_owner_v1(
    spec: H1AttemptExecutionPhaseSpecV1,
    *,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
) -> H1AttemptExecutionPhaseOwnerV1Handle:
    if type(spec) is not H1AttemptExecutionPhaseSpecV1:
        _fail("phase initialization requires one exact spec")
    _validate_live_gate(spec, rejection_gate)
    payload = spec.payload
    base = Path(payload["phase_base_realpath"])
    base_fd = _open_directory(base)
    root_fd = -1
    allocation_lock_fd = -1
    phase_fd = -1
    lock_fd = -1
    phase_lock_held = False
    cursor_fd = -1
    try:
        base_metadata = os.fstat(base_fd)
        if (base_metadata.st_dev, base_metadata.st_ino) != (
            payload["phase_base_device"],
            payload["phase_base_inode"],
        ):
            _fail("phase base inode changed")
        try:
            os.mkdir(_ROOT_NAME, 0o700, dir_fd=base_fd)
            os.fsync(base_fd)
        except FileExistsError:
            pass
        root_fd = _open_directory_at(base_fd, _ROOT_NAME)
        root_metadata = os.fstat(root_fd)
        _require_mode(root_metadata, 0o700, "phase root")
        try:
            allocation_lock_fd = _open_regular_at(
                root_fd,
                _ROOT_LOCK,
                flags=os.O_RDWR | os.O_CREAT | os.O_EXCL,
                mode=0o600,
            )
            os.fsync(root_fd)
        except ConstructionK7H1AttemptExecutionPhaseOwnerV1Error:
            allocation_lock_fd = _open_regular_at(
                root_fd, _ROOT_LOCK, flags=os.O_RDWR
            )
        _require_mode(os.fstat(allocation_lock_fd), 0o600, "phase allocation lock")
        fcntl.flock(allocation_lock_fd, fcntl.LOCK_EX)
        _cleanup_temps(root_fd)
        phase_name = payload["route_attempt_id"]
        try:
            os.mkdir(phase_name, 0o700, dir_fd=root_fd)
            os.fsync(root_fd)
        except FileExistsError:
            pass
        phase_fd = _open_directory_at(root_fd, phase_name)
        phase_metadata = os.fstat(phase_fd)
        _require_mode(phase_metadata, 0o700, "phase attempt directory")
        try:
            lock_fd = _open_regular_at(
                phase_fd,
                _LOCK_FILE,
                flags=os.O_RDWR | os.O_CREAT | os.O_EXCL,
                mode=0o600,
            )
            os.fsync(phase_fd)
        except ConstructionK7H1AttemptExecutionPhaseOwnerV1Error:
            lock_fd = _open_regular_at(phase_fd, _LOCK_FILE, flags=os.O_RDWR)
        lock_metadata = os.fstat(lock_fd)
        _require_mode(lock_metadata, 0o600, "phase lock")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        phase_lock_held = True
        _cleanup_temps(phase_fd)
        spec_raw = _spec_raw(spec)
        existing_spec = _read_file(phase_fd, _SPEC_FILE)
        if existing_spec is None:
            if not _publish_new(phase_fd, _SPEC_FILE, spec_raw):
                _fail("phase spec publication conflicted")
        elif not hmac.compare_digest(existing_spec, spec_raw):
            _fail("route attempt already has a different phase spec")
        cursor_raw = _read_file(phase_fd, _CURSOR_FILE)
        if cursor_raw is None:
            genesis_raw = canonical_json_bytes(_cursor_genesis(spec.spec_id)) + b"\n"
            if not _publish_new(
                phase_fd,
                _CURSOR_FILE,
                genesis_raw,
                mode=0o600,
            ):
                _fail("phase cursor genesis publication conflicted")
            cursor_fd = _open_regular_at(phase_fd, _CURSOR_FILE, flags=os.O_RDWR)
        else:
            cursor_fd = _open_regular_at(phase_fd, _CURSOR_FILE, flags=os.O_RDWR)
            _parse_cursor(cursor_raw, spec.spec_id)
        cursor_metadata = os.fstat(cursor_fd)
        _require_mode(cursor_metadata, 0o600, "phase cursor")
        root_path = (base / _ROOT_NAME).resolve(strict=True)
        phase_path = (root_path / phase_name).resolve(strict=True)
        allocation = _allocation_document(
            spec,
            root_path=root_path,
            root_metadata=root_metadata,
            root_allocation_lock_metadata=os.fstat(allocation_lock_fd),
            phase_path=phase_path,
            phase_metadata=phase_metadata,
            lock_metadata=lock_metadata,
            cursor_metadata=cursor_metadata,
        )
        allocation_raw = canonical_json_bytes(allocation)
        allocation_name = _allocation_name(phase_name)
        existing_allocation = _read_file(root_fd, allocation_name)
        if existing_allocation is None:
            if not _publish_new(root_fd, allocation_name, allocation_raw):
                _fail("phase attempt allocation publication conflicted")
        elif not hmac.compare_digest(existing_allocation, allocation_raw):
            _fail("route attempt phase allocation split-brain detected")
        handle = H1AttemptExecutionPhaseOwnerV1Handle(
            _HANDLE_ISSUER,
            spec,
            allocation["h1_attempt_phase_allocation_id"],
            str(root_path),
            root_metadata.st_dev,
            root_metadata.st_ino,
            os.fstat(allocation_lock_fd).st_dev,
            os.fstat(allocation_lock_fd).st_ino,
            str(phase_path),
            phase_metadata.st_dev,
            phase_metadata.st_ino,
            lock_metadata.st_dev,
            lock_metadata.st_ino,
            cursor_metadata.st_dev,
            cursor_metadata.st_ino,
            rejection_gate.gate_directory,
        )
    finally:
        if cursor_fd >= 0:
            os.close(cursor_fd)
        if lock_fd >= 0:
            if phase_lock_held:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
        if phase_fd >= 0:
            os.close(phase_fd)
        if allocation_lock_fd >= 0:
            fcntl.flock(allocation_lock_fd, fcntl.LOCK_UN)
            os.close(allocation_lock_fd)
        if root_fd >= 0:
            os.close(root_fd)
        os.close(base_fd)
    replay_h1_attempt_execution_phase_owner_v1(
        handle,
        rejection_gate=rejection_gate,
    )
    return handle


def _require_handle_locked(
    handle: H1AttemptExecutionPhaseOwnerV1Handle,
) -> tuple[int, int, int, int]:
    if type(handle) is not H1AttemptExecutionPhaseOwnerV1Handle:
        _fail("phase operation requires one exact issuer-owned handle")
    root_path = Path(handle.root_directory)
    phase_path = Path(handle.phase_directory)
    root_fd = _open_directory(root_path)
    phase_fd = -1
    lock_fd = -1
    cursor_fd = -1
    try:
        root_metadata = os.fstat(root_fd)
        _require_mode(root_metadata, 0o700, "phase root")
        if (root_metadata.st_dev, root_metadata.st_ino) != (
            handle.root_device,
            handle.root_inode,
        ):
            _fail("phase root inode changed")
        allocation_entry = _read_file_with_metadata(
            root_fd,
            _allocation_name(handle.route_attempt_id),
        )
        if allocation_entry is None:
            _fail("phase allocation record disappeared")
        allocation_raw = allocation_entry[0]
        _require_mode(allocation_entry[1], 0o400, "phase allocation record")
        allocation, claimed_allocation = _parse_allocation(allocation_raw)
        expected_root = (
            Path(handle.spec.payload["phase_base_realpath"]) / _ROOT_NAME
        ).resolve(strict=True)
        expected_phase = (expected_root / handle.route_attempt_id).resolve(strict=True)
        root_allocation_lock_fd = _open_regular_at(
            root_fd,
            _ROOT_LOCK,
            flags=os.O_RDONLY,
        )
        try:
            root_allocation_lock_metadata = os.fstat(root_allocation_lock_fd)
            _require_mode(
                root_allocation_lock_metadata,
                0o600,
                "phase allocation lock",
            )
        finally:
            os.close(root_allocation_lock_fd)
        if (
            claimed_allocation != handle.allocation_id
            or str(root_path) != str(expected_root)
            or str(phase_path) != str(expected_phase)
            or allocation.get("h1_attempt_execution_phase_spec_id")
            != handle.spec_id
            or allocation.get("logical_occurrence_id")
            != handle.spec.payload["logical_occurrence_id"]
            or allocation.get("route_attempt_id") != handle.route_attempt_id
            or allocation.get("h1_attempt_rejection_gate_id")
            != handle.spec.payload["h1_attempt_rejection_gate_id"]
            or allocation.get("phase_root_realpath") != str(expected_root)
            or allocation.get("phase_root_device") != handle.root_device
            or allocation.get("phase_root_inode") != handle.root_inode
            or allocation.get("root_allocation_lock_device")
            != handle.root_allocation_lock_device
            or allocation.get("root_allocation_lock_inode")
            != handle.root_allocation_lock_inode
            or (
                root_allocation_lock_metadata.st_dev,
                root_allocation_lock_metadata.st_ino,
            )
            != (
                handle.root_allocation_lock_device,
                handle.root_allocation_lock_inode,
            )
            or allocation.get("phase_directory_realpath") != str(expected_phase)
            or allocation.get("phase_directory_device") != handle.phase_device
            or allocation.get("phase_directory_inode") != handle.phase_inode
            or allocation.get("phase_lock_device") != handle.lock_device
            or allocation.get("phase_lock_inode") != handle.lock_inode
            or allocation.get("phase_cursor_device") != handle.cursor_device
            or allocation.get("phase_cursor_inode") != handle.cursor_inode
        ):
            _fail("phase allocation record changed")
        phase_fd = _open_directory(phase_path)
        phase_metadata = os.fstat(phase_fd)
        _require_mode(phase_metadata, 0o700, "phase attempt directory")
        if (phase_metadata.st_dev, phase_metadata.st_ino) != (
            handle.phase_device,
            handle.phase_inode,
        ):
            _fail("phase attempt directory inode changed")
        allowed = {
            _SPEC_FILE,
            _LOCK_FILE,
            _CURSOR_FILE,
            _INTENT_FILE,
            _COMMIT_FILE,
        }
        unknown = {
            name
            for name in os.listdir(phase_fd)
            if name not in allowed and not name.startswith(_TEMP_PREFIX)
        }
        if unknown:
            _fail("phase directory contains an unknown entry")
        spec_entry = _read_file_with_metadata(phase_fd, _SPEC_FILE)
        if spec_entry is None or spec_entry[0] != _spec_raw(handle.spec):
            _fail("phase spec bytes changed")
        _require_mode(spec_entry[1], 0o400, "phase spec")
        lock_fd = _open_regular_at(phase_fd, _LOCK_FILE, flags=os.O_RDWR)
        lock_metadata = os.fstat(lock_fd)
        if (lock_metadata.st_dev, lock_metadata.st_ino) != (
            handle.lock_device,
            handle.lock_inode,
        ):
            _fail("phase lock inode changed")
        _require_mode(lock_metadata, 0o600, "phase lock")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        cursor_fd = _open_cursor_locked(phase_fd, handle)
        return root_fd, phase_fd, lock_fd, cursor_fd
    except BaseException:
        if cursor_fd >= 0:
            os.close(cursor_fd)
        if lock_fd >= 0:
            os.close(lock_fd)
        if phase_fd >= 0:
            os.close(phase_fd)
        os.close(root_fd)
        raise


def _release_locked(root_fd: int, phase_fd: int, lock_fd: int, cursor_fd: int) -> None:
    os.close(cursor_fd)
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    os.close(lock_fd)
    os.close(phase_fd)
    os.close(root_fd)


def _close_fork_inherited_locked(
    root_fd: int,
    phase_fd: int,
    lock_fd: int,
    cursor_fd: int,
) -> None:
    """Close only a fork child's descriptor copies, never its parent's lock."""

    os.close(cursor_fd)
    os.close(lock_fd)
    os.close(phase_fd)
    os.close(root_fd)


def _finish_phase_lease_context(
    *,
    lease: H1AttemptExecutionPhaseLeaseV1 | None,
    gate_context: Any | None,
    root_fd: int,
    phase_fd: int,
    lock_fd: int,
    cursor_fd: int,
    phase_context_token: Any,
    owner_pid: int,
    owner_thread_id: int,
) -> None:
    """Finish one phase lease while preserving parent locks across ``fork``."""

    current_pid = os.getpid()
    current_thread_id = threading.get_ident()
    if current_pid == owner_pid and current_thread_id == owner_thread_id:
        if lease is not None:
            lease._active = False
        if gate_context is not None:
            gate_context.__exit__(None, None, None)
        if root_fd >= 0:
            _release_locked(root_fd, phase_fd, lock_fd, cursor_fd)
        _ACTIVE_PHASE_LEASES.reset(phase_context_token)
        return
    if current_pid != owner_pid:
        if lease is not None:
            lease._active = False
        # The rejection-gate context has the same fork-aware close-only rule.
        if gate_context is not None:
            gate_context.__exit__(None, None, None)
        if root_fd >= 0:
            _close_fork_inherited_locked(root_fd, phase_fd, lock_fd, cursor_fd)
        _ACTIVE_PHASE_LEASES.set(())
        return
    # A foreign thread shares this process's descriptor table.  Closing there
    # would revoke the owner's live lease, so retain every FD and fail closed.
    _fail("phase lease context crossed its owning thread during finalization")


def open_h1_attempt_execution_phase_owner_v1(
    spec: H1AttemptExecutionPhaseSpecV1,
    *,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
) -> H1AttemptExecutionPhaseOwnerV1Handle:
    _validate_live_gate(spec, rejection_gate)
    payload = spec.payload
    root_path = Path(payload["phase_base_realpath"]) / _ROOT_NAME
    root_fd = _open_directory(root_path)
    try:
        root_metadata = os.fstat(root_fd)
        _require_mode(root_metadata, 0o700, "phase root")
        root_allocation_lock_fd = _open_regular_at(
            root_fd,
            _ROOT_LOCK,
            flags=os.O_RDONLY,
        )
        try:
            root_allocation_lock_metadata = os.fstat(root_allocation_lock_fd)
            _require_mode(
                root_allocation_lock_metadata,
                0o600,
                "phase allocation lock",
            )
        finally:
            os.close(root_allocation_lock_fd)
        allocation_entry = _read_file_with_metadata(
            root_fd,
            _allocation_name(payload["route_attempt_id"]),
        )
        if allocation_entry is None:
            _fail("phase allocation is absent")
        allocation_raw = allocation_entry[0]
        _require_mode(allocation_entry[1], 0o400, "phase allocation record")
        allocation, claimed = _parse_allocation(allocation_raw)
        expected_root = root_path.resolve(strict=True)
        expected_phase = (expected_root / payload["route_attempt_id"]).resolve(
            strict=True
        )
        if (
            allocation.get("h1_attempt_execution_phase_spec_id") != spec.spec_id
            or allocation.get("logical_occurrence_id")
            != payload["logical_occurrence_id"]
            or allocation.get("route_attempt_id") != payload["route_attempt_id"]
            or allocation.get("h1_attempt_rejection_gate_id")
            != payload["h1_attempt_rejection_gate_id"]
            or allocation.get("phase_root_realpath") != str(expected_root)
            or allocation.get("phase_root_device") != root_metadata.st_dev
            or allocation.get("phase_root_inode") != root_metadata.st_ino
            or allocation.get("root_allocation_lock_device")
            != root_allocation_lock_metadata.st_dev
            or allocation.get("root_allocation_lock_inode")
            != root_allocation_lock_metadata.st_ino
            or allocation.get("phase_directory_realpath") != str(expected_phase)
        ):
            _fail("phase allocation differs from the expected attempt spec")
        handle = H1AttemptExecutionPhaseOwnerV1Handle(
            _HANDLE_ISSUER,
            spec,
            claimed,
            allocation["phase_root_realpath"],
            allocation["phase_root_device"],
            allocation["phase_root_inode"],
            allocation["root_allocation_lock_device"],
            allocation["root_allocation_lock_inode"],
            allocation["phase_directory_realpath"],
            allocation["phase_directory_device"],
            allocation["phase_directory_inode"],
            allocation["phase_lock_device"],
            allocation["phase_lock_inode"],
            allocation["phase_cursor_device"],
            allocation["phase_cursor_inode"],
            rejection_gate.gate_directory,
        )
    finally:
        os.close(root_fd)
    replay_h1_attempt_execution_phase_owner_v1(
        handle,
        rejection_gate=rejection_gate,
    )
    return handle


def replay_h1_attempt_execution_phase_owner_v1(
    handle: H1AttemptExecutionPhaseOwnerV1Handle,
    *,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
) -> dict[str, Any]:
    _validate_live_gate(handle.spec, rejection_gate)
    root_fd, phase_fd, lock_fd, cursor_fd = _require_handle_locked(handle)
    gate_context: Any | None = None
    try:
        state, transition = _recover_locked(root_fd, phase_fd, cursor_fd, handle)
        gate_context = rejection_v1.hold_h1_attempt_rejection_gate_for_replay_v1(
            rejection_gate
        )
        retained_gate = gate_context.__enter__()
        gate_state = retained_gate.state.value
        gate_commit_id = (
            retained_gate.commit_id
            if retained_gate.commit_id is not None
            else _typed_null("NO_REJECTION_COMMIT")
        )
        gate_ack_id = (
            retained_gate.acknowledgement_id
            if retained_gate.acknowledgement_id is not None
            else _typed_null("NO_REJECTION_ACK")
        )
    finally:
        if gate_context is not None:
            gate_context.__exit__(None, None, None)
        _release_locked(root_fd, phase_fd, lock_fd, cursor_fd)
    return {
        "schema": "acfqp.k7_h1_attempt_execution_phase_replay.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_attempt_execution_phase_spec_id": handle.spec_id,
        "h1_attempt_phase_allocation_id": handle.allocation_id,
        "state": state.value,
        "h1_attempt_cleanup_transition_id": (
            transition.transition_id
            if transition is not None
            else _typed_null("NO_CLEANUP_TRANSITION")
        ),
        "h1_attempt_rejection_gate_id": handle.spec.payload[
            "h1_attempt_rejection_gate_id"
        ],
        "rejection_gate_state": gate_state,
        "rejection_gate_commit_id": gate_commit_id,
        "rejection_gate_acknowledgement_id": gate_ack_id,
        "phase_and_gate_observed_under_ordered_exclusive_locks": True,
        "rejection_durable_while_phase_normal": (
            state is H1AttemptExecutionPhaseV1.NORMAL
            and gate_state != rejection_v1.H1AttemptRejectionGateStateV1.OPEN.value
        ),
        "normal_execution_allowed_by_phase": (
            state is H1AttemptExecutionPhaseV1.NORMAL
        ),
        "normal_phase_lease_is_execution_integration": False,
        "lease_aware_normal_dispatch_present": False,
        "cleanup_only_allowed_by_phase": (
            state is H1AttemptExecutionPhaseV1.CLEANUP_ONLY
        ),
        "no_event_recovery_complete": False,
        "cleanup_envelope_preadmitted": False,
        "cleanup_execution_authority_present": False,
        "production_execution_authority_present": False,
        "official_execution_allowed": False,
    }


def _activate_lease_context(handle: H1AttemptExecutionPhaseOwnerV1Handle) -> Any:
    active = _ACTIVE_PHASE_LEASES.get()
    if active:
        _fail("phase leases cannot nest or reverse the global lock order")
    return _ACTIVE_PHASE_LEASES.set((handle.spec_id,))


def _require_live_lease(
    lease: H1AttemptExecutionPhaseLeaseV1,
    expected_phase: H1AttemptExecutionPhaseV1,
    allowed_kinds: tuple[H1AttemptPhaseLeaseKindV1, ...],
) -> H1AttemptExecutionPhaseOwnerV1Handle:
    if (
        type(lease) is not H1AttemptExecutionPhaseLeaseV1
        or not lease._active
        or lease._transitioned
        or lease.phase is not expected_phase
        or lease.lease_kind not in allowed_kinds
        or lease._owner_pid != os.getpid()
        or lease._owner_thread_id != threading.get_ident()
        or _ACTIVE_PHASE_LEASES.get() != (lease.handle.spec_id,)
    ):
        _fail("phase lease is stale, crossed, forked, or wrong-phase")
    metadata = os.fstat(lease._lock_fd)
    if (metadata.st_dev, metadata.st_ino) != (
        lease.handle.lock_device,
        lease.handle.lock_inode,
    ):
        _fail("phase lease lock inode changed")
    cursor_metadata = os.fstat(lease._cursor_fd)
    if (cursor_metadata.st_dev, cursor_metadata.st_ino) != (
        lease.handle.cursor_device,
        lease.handle.cursor_inode,
    ):
        _fail("phase lease cursor inode changed")
    if rejection_v1._active_gate_modes(
        lease._gate_snapshot.gate_id
    ) != (rejection_v1._CONTEXT_DEPENDENT_REPLAY_EXCLUSIVE,):
        _fail("phase lease lost its retained rejection-gate lock context")
    return lease.handle


@contextmanager
def hold_h1_attempt_normal_execution_lease_v1(
    handle: H1AttemptExecutionPhaseOwnerV1Handle,
    *,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
) -> Iterator[H1AttemptExecutionPhaseLeaseV1]:
    _validate_live_gate(handle.spec, rejection_gate)
    owner_pid = os.getpid()
    owner_thread_id = threading.get_ident()
    token = _activate_lease_context(handle)
    root_fd = phase_fd = lock_fd = cursor_fd = -1
    lease: H1AttemptExecutionPhaseLeaseV1 | None = None
    gate_context: Any | None = None
    try:
        root_fd, phase_fd, lock_fd, cursor_fd = _require_handle_locked(handle)
        state, transition = _recover_locked(root_fd, phase_fd, cursor_fd, handle)
        if state is not H1AttemptExecutionPhaseV1.NORMAL or transition is not None:
            _fail("normal execution lease is forbidden after cleanup transition")
        gate_context = rejection_v1.hold_h1_attempt_rejection_gate_for_replay_v1(
            rejection_gate
        )
        gate_snapshot = gate_context.__enter__()
        if gate_snapshot.state is not rejection_v1.H1AttemptRejectionGateStateV1.OPEN:
            _fail("normal execution lease is forbidden after attempt rejection")
        lease = H1AttemptExecutionPhaseLeaseV1(
            _LEASE_ISSUER,
            handle,
            H1AttemptExecutionPhaseV1.NORMAL,
            H1AttemptPhaseLeaseKindV1.NORMAL_PHASE,
            None,
            root_fd,
            phase_fd,
            lock_fd,
            cursor_fd,
            gate_context,
            gate_snapshot,
            owner_pid,
            owner_thread_id,
        )
        yield lease
    finally:
        _finish_phase_lease_context(
            lease=lease,
            gate_context=gate_context,
            root_fd=root_fd,
            phase_fd=phase_fd,
            lock_fd=lock_fd,
            cursor_fd=cursor_fd,
            phase_context_token=token,
            owner_pid=owner_pid,
            owner_thread_id=owner_thread_id,
        )


@contextmanager
def hold_h1_attempt_cleanup_transition_lease_v1(
    handle: H1AttemptExecutionPhaseOwnerV1Handle,
    *,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
) -> Iterator[H1AttemptExecutionPhaseLeaseV1]:
    """Hold PHASE->GATE exclusively for transition only.

    This authority is intentionally usable after the attempt gate is already
    rejected.  It cannot authorize a normal lifecycle site; it exists so a
    previously durable cap-rejection event can monotonically close NORMAL.
    """

    _validate_live_gate(handle.spec, rejection_gate)
    owner_pid = os.getpid()
    owner_thread_id = threading.get_ident()
    token = _activate_lease_context(handle)
    root_fd = phase_fd = lock_fd = cursor_fd = -1
    lease: H1AttemptExecutionPhaseLeaseV1 | None = None
    gate_context: Any | None = None
    try:
        root_fd, phase_fd, lock_fd, cursor_fd = _require_handle_locked(handle)
        state, transition = _recover_locked(
            root_fd,
            phase_fd,
            cursor_fd,
            handle,
        )
        if state is not H1AttemptExecutionPhaseV1.NORMAL or transition is not None:
            _fail("transition-only lease requires the untransitioned NORMAL phase")
        gate_context = rejection_v1.hold_h1_attempt_rejection_gate_for_replay_v1(
            rejection_gate
        )
        gate_snapshot = gate_context.__enter__()
        lease = H1AttemptExecutionPhaseLeaseV1(
            _LEASE_ISSUER,
            handle,
            H1AttemptExecutionPhaseV1.NORMAL,
            H1AttemptPhaseLeaseKindV1.TRANSITION_ONLY,
            None,
            root_fd,
            phase_fd,
            lock_fd,
            cursor_fd,
            gate_context,
            gate_snapshot,
            owner_pid,
            owner_thread_id,
        )
        yield lease
    finally:
        _finish_phase_lease_context(
            lease=lease,
            gate_context=gate_context,
            root_fd=root_fd,
            phase_fd=phase_fd,
            lock_fd=lock_fd,
            cursor_fd=cursor_fd,
            phase_context_token=token,
            owner_pid=owner_pid,
            owner_thread_id=owner_thread_id,
        )


def _expected_branch_key(trace: Mapping[str, Any]) -> tuple[str, Mapping[str, Any]]:
    events = trace.get("consumed_events")
    if type(events) is not list or not events:
        _fail("cleanup transition requires a nonempty failed dispatch trace")
    failure = events[-1]
    if type(failure) is not dict or failure.get("outcome") == "SUCCESS":
        _fail("cleanup transition requires the final event to be a failure")
    if any(event.get("outcome") != "SUCCESS" for event in events[:-1]):
        _fail("cleanup transition trace continued after an earlier failure")
    outcome = _nonempty(failure.get("outcome"), "cleanup failure outcome")
    site = _nonempty(failure.get("site_key"), "cleanup failure site")
    if outcome == cleanup_v1._SUPPLEMENTAL_OUTCOME:
        return f"SUPPLEMENTAL:{site}:{outcome}", failure
    return f"FAIL:{site}:{outcome}", failure


def _build_transition(
    lease: H1AttemptExecutionPhaseLeaseV1,
    *,
    trace_bytes: bytes,
    tail_attestation: tail_v1.H1TailBoundPrefixAttestationV1,
    semantic_closure: tail_v1.H1PrefixVerifierSemanticClosureV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    gate_snapshot: rejection_v1.H1AttemptRejectionGateReplaySnapshotV1,
    owner_state: Any,
    gate_join: Any,
) -> H1AttemptCleanupTransitionV1:
    handle = _require_live_lease(
        lease,
        H1AttemptExecutionPhaseV1.NORMAL,
        (
            H1AttemptPhaseLeaseKindV1.NORMAL_PHASE,
            H1AttemptPhaseLeaseKindV1.TRANSITION_ONLY,
        ),
    )
    if (
        type(trace_bytes) is not bytes
        or type(tail_attestation) is not tail_v1.H1TailBoundPrefixAttestationV1
        or type(semantic_closure) is not tail_v1.H1PrefixVerifierSemanticClosureV1
        or type(cleanup_pass) is not cleanup_v1.H1LifecycleCleanupPassV1
        or type(owner) is not owner_v4.H1SharedCapOwnerV4WalHandle
    ):
        _fail("cleanup transition evidence has a foreign type")
    tail_v1._require_live_semantic_closure(semantic_closure)
    try:
        trace = loads_canonical_json(trace_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
            "cleanup transition trace is not canonical"
        ) from error
    if type(trace) is not dict or canonical_json_bytes(trace) != trace_bytes:
        _fail("cleanup transition trace is not one canonical object")
    attestation = tail_attestation.payload
    cleanup = cleanup_pass.payload
    branch_key, failure = _expected_branch_key(trace)
    trace_id = _cid(
        trace.get("h1_lifecycle_dispatch_trace_id"),
        "cleanup dispatch trace",
    )
    if (
        attestation["h1_lifecycle_dispatch_trace_id"] != trace_id
        or attestation["h1_prefix_verifier_semantic_closure_id"]
        != semantic_closure.closure_id
        or attestation["dispatch_trace_sha256"]
        != hashlib.sha256(trace_bytes).hexdigest()
        or attestation["prefix_last_event_id"]
        != failure["h1_lifecycle_dispatch_event_id"]
        or cleanup["branch_key"] != branch_key
        or cleanup["h1_lifecycle_complete_branch_analysis_id"]
        != handle.spec.payload["h1_lifecycle_complete_branch_analysis_id"]
        or attestation["h1_anchored_lifecycle_program_id"]
        != handle.spec.payload["h1_anchored_lifecycle_program_id"]
        or attestation["h1_anchored_lifecycle_handler_registry_id"]
        != handle.spec.payload["h1_anchored_lifecycle_handler_registry_id"]
        or attestation["logical_occurrence_id"]
        != handle.spec.payload["logical_occurrence_id"]
        or attestation["route_attempt_id"]
        != handle.spec.payload["route_attempt_id"]
        or attestation["h1_shared_cap_owner_v3_runtime_id"] != owner.runtime_id
        or attestation["h1_shared_cap_owner_v4_wal_binding_id"] != owner.binding_id
    ):
        _fail("cleanup transition evidence crossed its attempt, trace, or plan")
    current_head = (
        owner_state.head_id
        if owner_state.head_id is not None
        else _typed_null("JOURNAL_GENESIS")
    )
    current_commit = (
        owner_state.rejection_commit_id
        if owner_state.rejection_commit_id is not None
        else _typed_null("NO_REJECTION_COMMIT")
    )
    current_ack = (
        gate_snapshot.acknowledgement_id
        if gate_snapshot.acknowledgement_id is not None
        else _typed_null("NO_REJECTION_ACK")
    )
    if (
        owner_state.pending_cursor is not None
        or owner_v3._incomplete_pair_frontier(owner_state) is not None
        or gate_join.recovery_required
        or attestation["current_tail_sequence"] != owner_state.sequence
        or attestation["current_tail_head_id"] != current_head
        or attestation["current_gate_state"] != gate_snapshot.state.value
        or attestation["current_gate_join_status"] != gate_join.status.value
        or attestation["current_gate_rejection_commit_id"] != current_commit
        or attestation["current_gate_rejection_ack_id"] != current_ack
    ):
        _fail("cleanup transition requires the attested exact current gate/Owner tail")
    failure_outcome = _nonempty(failure["outcome"], "primary failure outcome")
    payload = {
        "schema": "acfqp.k7_h1_attempt_cleanup_transition.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_attempt_execution_phase_spec_id": handle.spec_id,
        "h1_attempt_phase_allocation_id": handle.allocation_id,
        "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
        "route_attempt_id": handle.route_attempt_id,
        "h1_attempt_rejection_gate_id": handle.spec.payload[
            "h1_attempt_rejection_gate_id"
        ],
        "h1_shared_cap_owner_v3_runtime_id": owner.runtime_id,
        "h1_shared_cap_owner_v4_wal_binding_id": owner.binding_id,
        "decision_point_id": owner.owner.profile.decision_point_id,
        "transaction_id": owner.owner.profile.transaction_id,
        "h1_lifecycle_dispatch_trace_id": trace_id,
        "h1_lifecycle_dispatch_profile_id": attestation[
            "h1_lifecycle_dispatch_profile_id"
        ],
        "h1_prefix_verifier_semantic_closure_id": semantic_closure.closure_id,
        "h1_tail_bound_prefix_attestation_id": tail_attestation.attestation_id,
        "h1_lifecycle_cleanup_pass_id": cleanup_pass.pass_id,
        "h1_lifecycle_complete_branch_analysis_id": cleanup[
            "h1_lifecycle_complete_branch_analysis_id"
        ],
        "branch_key": branch_key,
        "primary_failure_event_id": _cid(
            failure["h1_lifecycle_dispatch_event_id"],
            "primary failure event",
        ),
        "primary_failure_site_key": failure["site_key"],
        "primary_failure_outcome": failure_outcome,
        "primary_failure_trigger_kind": (
            "CAP_REJECTION"
            if failure_outcome == "CAP_REJECTED_BEFORE_SIDE_EFFECT"
            else "LIFECYCLE_FAILURE"
        ),
        "owner_tail_sequence_at_transition": owner_state.sequence,
        "owner_tail_head_id_at_transition": current_head,
        "gate_state_at_transition": gate_snapshot.state.value,
        "gate_owner_join_status_at_transition": gate_join.status.value,
        "from_phase": H1AttemptExecutionPhaseV1.NORMAL.value,
        "to_phase": H1AttemptExecutionPhaseV1.CLEANUP_ONLY.value,
        "normal_phase_never_reopens": True,
        "primary_failure_immutable": True,
        "secondary_failures_append_only": True,
        "phase_gate_owner_snapshot_held_during_intent_publish": True,
        "historical_normal_lane_coverage_present": False,
        "no_event_recovery_complete": False,
        "cleanup_envelope_preadmitted": False,
        "cleanup_execution_authority_present": False,
        "production_execution_authority_present": False,
        "formal_counter_record_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "official_execution_allowed": False,
    }
    return H1AttemptCleanupTransitionV1(
        _TRANSITION_ISSUER,
        canonical_json_bytes(payload),
    )


def transition_h1_attempt_to_cleanup_only_with_phase_lease_v1(
    lease: H1AttemptExecutionPhaseLeaseV1,
    *,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
    trace_bytes: bytes,
    tail_attestation: tail_v1.H1TailBoundPrefixAttestationV1,
    semantic_closure: tail_v1.H1PrefixVerifierSemanticClosureV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    crash_point: H1AttemptPhaseCrashPointV1 = H1AttemptPhaseCrashPointV1.NONE,
) -> H1AttemptCleanupTransitionV1:
    handle = _require_live_lease(
        lease,
        H1AttemptExecutionPhaseV1.NORMAL,
        (
            H1AttemptPhaseLeaseKindV1.NORMAL_PHASE,
            H1AttemptPhaseLeaseKindV1.TRANSITION_ONLY,
        ),
    )
    _validate_live_gate(handle.spec, rejection_gate)
    try:
        fault = H1AttemptPhaseCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1AttemptExecutionPhaseOwnerV1Error(
            "phase transition crash point is invalid"
        ) from error
    if owner.gate_directory != rejection_gate.gate_directory:
        _fail("cleanup transition Owner crossed its rejection gate")
    gate_snapshot = lease._gate_snapshot
    if gate_snapshot.gate_id != rejection_gate.spec.gate_id:
        _fail("cleanup transition lease crossed its retained rejection gate")
    owner_root_fd = owner_directory_fd = -1
    try:
        owner_root_fd, owner_directory_fd, owner_state = owner_v3._require_handle_locked(
            owner.owner
        )
        gate_join = owner_v3._validate_owner_gate_join(
            owner.owner,
            owner_state,
            gate_snapshot,
        )
        transition = _build_transition(
            lease,
            trace_bytes=trace_bytes,
            tail_attestation=tail_attestation,
            semantic_closure=semantic_closure,
            cleanup_pass=cleanup_pass,
            owner=owner,
            gate_snapshot=gate_snapshot,
            owner_state=owner_state,
            gate_join=gate_join,
        )
        existing = _read_file(lease._phase_fd, _INTENT_FILE)
        # Once all evidence is validated and immutable publication begins,
        # consume this process-local NORMAL authority conservatively.  This is
        # stronger than waiting for the link/fsync return and removes even the
        # asynchronous-exception window after a durable link becomes visible.
        lease._transitioned = True
        if existing is None:
            if not _publish_new(
                lease._phase_fd,
                _INTENT_FILE,
                transition.canonical_bytes,
            ):
                _fail("cleanup transition intent publication conflicted")
        else:
            if not hmac.compare_digest(existing, transition.canonical_bytes):
                _fail("attempt already has a different primary cleanup transition")
        # The first durable intent irrevocably revokes this NORMAL authority,
        # including when a caller catches an injected/process-boundary error.
        if fault is H1AttemptPhaseCrashPointV1.AFTER_INTENT_FSYNC:
            raise H1AttemptPhaseInjectedCrashV1("phase crash after intent fsync")
        sealed = _reconcile_root_transition_seal_locked(
            lease._root_fd,
            lease._phase_fd,
            handle,
        )
        if sealed is None or not hmac.compare_digest(
            sealed[0], transition.canonical_bytes
        ):
            _fail("root cleanup transition seal did not bind the exact intent")
        records = _read_repairable_cursor_locked(
            lease._cursor_fd,
            handle.spec_id,
            transition_id=transition.transition_id,
        )
        if H1AttemptExecutionPhaseV1(records[-1]["state"]) is H1AttemptExecutionPhaseV1.NORMAL:
            records = _append_cursor(
                lease._cursor_fd,
                records,
                spec_id=handle.spec_id,
                state=H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE,
                transition_id=transition.transition_id,
            )
        if fault is H1AttemptPhaseCrashPointV1.AFTER_INTENT_CURSOR_FSYNC:
            raise H1AttemptPhaseInjectedCrashV1(
                "phase crash after intent cursor fsync"
            )
        if not _link_intent_to_commit(lease._phase_fd):
            commit = _read_file(lease._phase_fd, _COMMIT_FILE)
            if commit is None or not hmac.compare_digest(
                commit, transition.canonical_bytes
            ):
                _fail("cleanup transition commit conflicted")
        if fault is H1AttemptPhaseCrashPointV1.AFTER_COMMIT_LINK_FSYNC:
            raise H1AttemptPhaseInjectedCrashV1(
                "phase crash after commit link fsync"
            )
        records = _read_repairable_cursor_locked(
            lease._cursor_fd,
            handle.spec_id,
            transition_id=transition.transition_id,
        )
        if (
            H1AttemptExecutionPhaseV1(records[-1]["state"])
            is H1AttemptExecutionPhaseV1.CLEANUP_INTENT_DURABLE
        ):
            _append_cursor(
                lease._cursor_fd,
                records,
                spec_id=handle.spec_id,
                state=H1AttemptExecutionPhaseV1.CLEANUP_ONLY,
                transition_id=transition.transition_id,
            )
        if fault is H1AttemptPhaseCrashPointV1.AFTER_CLEANUP_CURSOR_FSYNC:
            raise H1AttemptPhaseInjectedCrashV1(
                "phase crash after cleanup cursor fsync"
            )
        lease.transition_id = transition.transition_id
        return transition
    finally:
        if owner_directory_fd >= 0:
            os.close(owner_directory_fd)
        if owner_root_fd >= 0:
            os.close(owner_root_fd)


@contextmanager
def hold_h1_attempt_cleanup_only_lease_v1(
    handle: H1AttemptExecutionPhaseOwnerV1Handle,
    *,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
    expected_transition_id: str,
) -> Iterator[H1AttemptExecutionPhaseLeaseV1]:
    _validate_live_gate(handle.spec, rejection_gate)
    expected = _cid(expected_transition_id, "expected cleanup transition")
    owner_pid = os.getpid()
    owner_thread_id = threading.get_ident()
    token = _activate_lease_context(handle)
    root_fd = phase_fd = lock_fd = cursor_fd = -1
    lease: H1AttemptExecutionPhaseLeaseV1 | None = None
    gate_context: Any | None = None
    try:
        root_fd, phase_fd, lock_fd, cursor_fd = _require_handle_locked(handle)
        state, transition = _recover_locked(root_fd, phase_fd, cursor_fd, handle)
        if (
            state is not H1AttemptExecutionPhaseV1.CLEANUP_ONLY
            or transition is None
            or transition.transition_id != expected
        ):
            _fail("cleanup-only lease requires the exact committed transition")
        gate_context = rejection_v1.hold_h1_attempt_rejection_gate_for_replay_v1(
            rejection_gate
        )
        gate_snapshot = gate_context.__enter__()
        lease = H1AttemptExecutionPhaseLeaseV1(
            _LEASE_ISSUER,
            handle,
            H1AttemptExecutionPhaseV1.CLEANUP_ONLY,
            H1AttemptPhaseLeaseKindV1.CLEANUP_PHASE,
            expected,
            root_fd,
            phase_fd,
            lock_fd,
            cursor_fd,
            gate_context,
            gate_snapshot,
            owner_pid,
            owner_thread_id,
        )
        yield lease
    finally:
        _finish_phase_lease_context(
            lease=lease,
            gate_context=gate_context,
            root_fd=root_fd,
            phase_fd=phase_fd,
            lock_fd=lock_fd,
            cursor_fd=cursor_fd,
            phase_context_token=token,
            owner_pid=owner_pid,
            owner_thread_id=owner_thread_id,
        )


__all__ = (
    "ConstructionK7H1AttemptExecutionPhaseOwnerV1Error",
    "H1AttemptCleanupTransitionV1",
    "H1AttemptExecutionPhaseLeaseV1",
    "H1AttemptExecutionPhaseOwnerV1Handle",
    "H1AttemptExecutionPhaseSpecV1",
    "H1AttemptExecutionPhaseV1",
    "H1AttemptPhaseLeaseKindV1",
    "H1AttemptPhaseCrashPointV1",
    "H1AttemptPhaseInjectedCrashV1",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "freeze_h1_attempt_execution_phase_spec_v1",
    "hold_h1_attempt_cleanup_only_lease_v1",
    "hold_h1_attempt_cleanup_transition_lease_v1",
    "hold_h1_attempt_normal_execution_lease_v1",
    "initialize_h1_attempt_execution_phase_owner_v1",
    "open_h1_attempt_execution_phase_owner_v1",
    "replay_h1_attempt_execution_phase_owner_v1",
    "transition_h1_attempt_to_cleanup_only_with_phase_lease_v1",
)
