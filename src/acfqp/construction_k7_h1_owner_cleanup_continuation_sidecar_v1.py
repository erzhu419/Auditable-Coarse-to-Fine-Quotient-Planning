"""Additive conservative Owner-cleanup continuation sidecar.

This module intentionally does not add a cleanup record kind to the frozen V3
Owner journal or the V4 pending-payload WAL.  One sidecar allocation binds one
exact V3/V4 cutoff and one still-outstanding deferred-origin reservation to the
already committed V2 cleanup transition, its pre-admitted envelope, selected
cleanup pass, and one exact cleanup action.

The only supported semantic operation is
``CONSERVATIVE_RELEASE_WITHOUT_NATIVE_START``.  It charges the reservation
upper, records a typed-null native value, and releases that exposure once in
the combined replay.  It cannot read memory, finalize output, perform a native
effect, issue formal accounting, or authorize production execution.
"""

from __future__ import annotations

from contextlib import contextmanager
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

from acfqp import construction_k7_h1_attempt_execution_phase_owner_v1 as phase_v1
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_domain_registry_extension_v5 as domains_v5
from acfqp import construction_k7_h1_lifecycle_complete_cleanup_v1 as cleanup_v1
from acfqp import construction_k7_h1_preadmitted_cleanup_transition_v2 as phase_v2
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_shared_cap_owner_v4_wal as owner_v4
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-C"
PROFILE_KEY = "construction_k7_h1_owner_cleanup_continuation_sidecar_v1"

OWNER_CLEANUP_CONTINUATION_SIDECAR_PRESENT = True
V3_V4_OWNER_BYTES_PRESERVED = True
CONSERVATIVE_RELEASE_WITHOUT_NATIVE_START_PRESENT = True
CLEANUP_ARBITRARY_EXECUTOR_PRESENT = False
CLEANUP_NATIVE_EFFECT_AUTHORITY_PRESENT = False
MEMORY_READ_AUTHORITY_PRESENT = False
OUTPUT_FINALIZE_AUTHORITY_PRESENT = False
OUTPUT_OWNER_CLOSE_AUTHORITY_PRESENT = False
PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
ATTEMPT_CLOSURE_ISSUED = False
TERMINAL_CLASSIFICATION_ISSUED = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False

SPEC_DOMAIN = domains_v5.CONSTRUCTION_K7_H1_OWNER_CLEANUP_SIDECAR_SPEC_V1_DOMAIN
ALLOCATION_DOMAIN = (
    domains_v5.CONSTRUCTION_K7_H1_OWNER_CLEANUP_SIDECAR_ALLOCATION_V1_DOMAIN
)
RELEASE_DOMAIN = domains_v5.CONSTRUCTION_K7_H1_OWNER_CLEANUP_RELEASE_V1_DOMAIN
CURSOR_DOMAIN = (
    domains_v5.CONSTRUCTION_K7_H1_OWNER_CLEANUP_CURSOR_RECORD_V1_DOMAIN
)
COMBINED_DOMAIN = (
    domains_v5.CONSTRUCTION_K7_H1_OWNER_CLEANUP_COMBINED_STATE_V1_DOMAIN
)

_ROOT_NAME = ".acfqp-k7-h1-owner-cleanup-sidecars-v1"
_ROOT_LOCK_FILE = "allocation.lock"
_SIDECAR_PREFIX = "sidecar-"
_ALLOCATION_FILE = "allocation.json"
_LOCK_FILE = "sidecar.lock"
_CURSOR_FILE = "cursor.jsonl"
_RELEASE_FILE = "release.json"
_ALLOCATION_SEAL_PREFIX = "allocation-seal-"
_RELEASE_SEAL_PREFIX = "release-seal-"
_TEMP_PREFIX = ".tmp-"

_SPEC_ISSUER = object()
_ALLOCATION_ISSUER = object()
_RELEASE_ISSUER = object()
_HANDLE_ISSUER = object()

_SUPPORTED_ACTIONS = {
    "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ": (
        "memory:bind-working-hierarchy",
        "memory.working_bytes_peak",
    ),
    "SETTLE_OUTPUT_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_FINALIZE": (
        "output:reserve-route-wide",
        "io.output_bytes",
    ),
}
_SEMANTIC_OPERATION = "CONSERVATIVE_RELEASE_WITHOUT_NATIVE_START"


class ConstructionK7H1OwnerCleanupContinuationSidecarV1Error(ValueError):
    """A cleanup sidecar binding, journal, or combined replay was crossed."""


class H1OwnerCleanupSidecarInjectedCrashV1(RuntimeError):
    """Deterministic crash boundary used by recovery tests."""


class H1OwnerCleanupSidecarCrashPointV1(str, Enum):
    NONE = "NONE"
    AFTER_RELEASE_FSYNC = "AFTER_RELEASE_FSYNC"
    AFTER_ROOT_SEAL_FSYNC = "AFTER_ROOT_SEAL_FSYNC"
    AFTER_CURSOR_FSYNC = "AFTER_CURSOR_FSYNC"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1OwnerCleanupContinuationSidecarV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1OwnerCleanupContinuationSidecarV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative integer")
    return value


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _content_id(domain: str, payload: Any) -> str:
    return domains_v5.extension_content_id_v5(domain, payload)


def _canonical_phase_base(
    cleanup_lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    base_directory: str | Path,
) -> Path:
    payload = cleanup_lease.handle.spec.payload
    try:
        supplied = Path(base_directory).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ConstructionK7H1OwnerCleanupContinuationSidecarV1Error(
            "cleanup sidecar base directory cannot be canonically resolved"
        ) from error
    metadata = supplied.stat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or str(supplied) != payload["phase_base_realpath"]
        or (metadata.st_dev, metadata.st_ino)
        != (payload["phase_base_device"], payload["phase_base_inode"])
    ):
        _fail("cleanup sidecar base differs from the unique phase-spec base")
    return supplied


def _parse_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1OwnerCleanupContinuationSidecarV1Error(
            f"{label} is not canonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _artifact_document(
    domain: str,
    payload: Mapping[str, Any],
    id_field: str,
) -> dict[str, Any]:
    body = dict(payload)
    return {**body, id_field: _content_id(domain, body)}


@dataclass(frozen=True, slots=True)
class H1OwnerCleanupSidecarSpecV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SPEC_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("cleanup sidecar spec is caller-minted")
        payload = _parse_document(self.payload_bytes, "cleanup sidecar spec")
        object.__setattr__(self, "_spec_id", _content_id(SPEC_DOMAIN, payload))

    @property
    def spec_id(self) -> str:
        return self._spec_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse_document(self.payload_bytes, "cleanup sidecar spec")

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self.payload, "h1_owner_cleanup_sidecar_spec_id": self.spec_id}


@dataclass(frozen=True, slots=True)
class H1OwnerCleanupSidecarAllocationV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _allocation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ALLOCATION_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("cleanup sidecar allocation is caller-minted")
        payload = _parse_document(self.payload_bytes, "cleanup sidecar allocation")
        object.__setattr__(
            self, "_allocation_id", _content_id(ALLOCATION_DOMAIN, payload)
        )

    @property
    def allocation_id(self) -> str:
        return self._allocation_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse_document(self.payload_bytes, "cleanup sidecar allocation")

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self.payload,
            "h1_owner_cleanup_sidecar_allocation_id": self.allocation_id,
        }


@dataclass(frozen=True, slots=True)
class H1OwnerCleanupReleaseV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _release_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RELEASE_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("cleanup release is caller-minted")
        payload = _parse_document(self.payload_bytes, "cleanup release")
        object.__setattr__(self, "_release_id", _content_id(RELEASE_DOMAIN, payload))

    @property
    def release_id(self) -> str:
        return self._release_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse_document(self.payload_bytes, "cleanup release")

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self.payload, "h1_owner_cleanup_release_id": self.release_id}


@dataclass(frozen=True, slots=True)
class H1OwnerCleanupSidecarHandleV1:
    _issuer: InitVar[object]
    spec: H1OwnerCleanupSidecarSpecV1
    allocation: H1OwnerCleanupSidecarAllocationV1
    root_directory: str
    root_device: int
    root_inode: int
    root_lock_device: int
    root_lock_inode: int
    sidecar_directory: str
    sidecar_device: int
    sidecar_inode: int
    lock_device: int
    lock_inode: int
    cursor_device: int
    cursor_inode: int

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _HANDLE_ISSUER
            or type(self.spec) is not H1OwnerCleanupSidecarSpecV1
            or type(self.allocation) is not H1OwnerCleanupSidecarAllocationV1
            or self.allocation.payload["h1_owner_cleanup_sidecar_spec_id"]
            != self.spec.spec_id
        ):
            _fail("cleanup sidecar handle is caller-minted or crossed")
        for value, label in (
            (self.root_device, "sidecar root device"),
            (self.root_inode, "sidecar root inode"),
            (self.root_lock_device, "sidecar root lock device"),
            (self.root_lock_inode, "sidecar root lock inode"),
            (self.sidecar_device, "sidecar directory device"),
            (self.sidecar_inode, "sidecar directory inode"),
            (self.lock_device, "sidecar lock device"),
            (self.lock_inode, "sidecar lock inode"),
            (self.cursor_device, "sidecar cursor device"),
            (self.cursor_inode, "sidecar cursor inode"),
        ):
            _nonnegative(value, label)

    @property
    def allocation_id(self) -> str:
        return self.allocation.allocation_id

    def __reduce__(self) -> NoReturn:
        _fail("cleanup sidecar handle is not serializable")


def _open_directory(path: Path) -> int:
    if not path.is_absolute():
        _fail("cleanup sidecar paths must be absolute")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ConstructionK7H1OwnerCleanupContinuationSidecarV1Error(
            f"cannot open cleanup sidecar directory: {path}"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_mode & 0o077:
        os.close(descriptor)
        _fail("cleanup sidecar directory is not private")
    return descriptor


def _open_regular_at(
    directory_fd: int,
    name: str,
    *,
    flags: int,
    mode: int = 0o600,
) -> int:
    effective = flags | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        effective |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, effective, mode, dir_fd=directory_fd)
    except OSError as error:
        raise ConstructionK7H1OwnerCleanupContinuationSidecarV1Error(
            f"cannot open cleanup sidecar file: {name}"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        os.close(descriptor)
        _fail(f"cleanup sidecar path is not regular: {name}")
    return descriptor


def _read_descriptor(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 1 << 16)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _read_file(directory_fd: int, name: str) -> tuple[bytes, os.stat_result] | None:
    try:
        descriptor = _open_regular_at(directory_fd, name, flags=os.O_RDONLY)
    except ConstructionK7H1OwnerCleanupContinuationSidecarV1Error as error:
        try:
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        raise error
    try:
        return _read_descriptor(descriptor), os.fstat(descriptor)
    finally:
        os.close(descriptor)


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:  # pragma: no cover - OS invariant
            _fail("cleanup sidecar write made no progress")
        view = view[written:]


def _publish_new(directory_fd: int, name: str, raw: bytes) -> bool:
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
        os.fchmod(descriptor, 0o400)
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
        except FileNotFoundError:  # pragma: no cover - defensive
            pass
    return published


def _link_cross_directory(
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


def _require_same_immutable_file(
    first: tuple[bytes, os.stat_result] | None,
    second: tuple[bytes, os.stat_result] | None,
    *,
    expected_raw: bytes,
    label: str,
) -> None:
    if first is None or second is None:
        _fail(f"{label} is incomplete")
    if (
        not hmac.compare_digest(first[0], expected_raw)
        or not hmac.compare_digest(second[0], expected_raw)
        or (first[1].st_dev, first[1].st_ino)
        != (second[1].st_dev, second[1].st_ino)
        or stat.S_IMODE(first[1].st_mode) != 0o400
        or stat.S_IMODE(second[1].st_mode) != 0o400
    ):
        _fail(f"{label} bytes, inode, or mode changed")


def _cleanup_temps(directory_fd: int) -> None:
    for name in os.listdir(directory_fd):
        if name.startswith(_TEMP_PREFIX):
            os.unlink(name, dir_fd=directory_fd)
    os.fsync(directory_fd)


def _allocation_seal_name(spec: H1OwnerCleanupSidecarSpecV1) -> str:
    payload = spec.payload
    return (
        f"{_ALLOCATION_SEAL_PREFIX}"
        f"{payload['h1_shared_cap_owner_v3_runtime_id']}-"
        f"{payload['h1_shared_cap_owner_v3_reservation_id']}.json"
    )


def _release_seal_name(spec: H1OwnerCleanupSidecarSpecV1) -> str:
    payload = spec.payload
    return (
        f"{_RELEASE_SEAL_PREFIX}"
        f"{payload['h1_shared_cap_owner_v3_runtime_id']}-"
        f"{payload['h1_shared_cap_owner_v3_reservation_id']}.json"
    )


def _cursor_payload(
    allocation_id: str,
    *,
    sequence: int,
    previous_cursor_id: Any,
    state: str,
    release_id: Any,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_owner_cleanup_cursor_record.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_owner_cleanup_sidecar_allocation_id": allocation_id,
        "sequence": sequence,
        "previous_cursor_record_id": previous_cursor_id,
        "state": state,
        "h1_owner_cleanup_release_id": release_id,
        "cleanup_arbitrary_executor_present": False,
        "output_owner_close_authority_present": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "production_execution_authority_present": False,
        "formal_counter_record_issued": False,
        "official_execution_allowed": False,
    }


def _cursor_document(payload: Mapping[str, Any]) -> dict[str, Any]:
    return _artifact_document(
        CURSOR_DOMAIN,
        payload,
        "h1_owner_cleanup_cursor_record_id",
    )


def _genesis_cursor(allocation_id: str) -> dict[str, Any]:
    return _cursor_document(
        _cursor_payload(
            allocation_id,
            sequence=0,
            previous_cursor_id=_typed_null("CURSOR_GENESIS"),
            state="OPEN",
            release_id=_typed_null("NO_RELEASE_COMMITTED"),
        )
    )


def _read_cursor_locked(
    cursor_fd: int,
    allocation_id: str,
    *,
    expected_release_id: str,
    repair_torn_suffix: bool,
) -> list[dict[str, Any]]:
    raw = _read_descriptor(cursor_fd)
    if not raw:
        _fail("cleanup sidecar cursor is empty")
    expected_genesis = _genesis_cursor(allocation_id)
    expected_commit = _cursor_document(
        _cursor_payload(
            allocation_id,
            sequence=1,
            previous_cursor_id=expected_genesis[
                "h1_owner_cleanup_cursor_record_id"
            ],
            state="RELEASE_COMMITTED",
            release_id=_cid(expected_release_id, "expected cleanup cursor release"),
        )
    )

    def decode_complete(complete_raw: bytes) -> list[dict[str, Any]]:
        if not complete_raw.endswith(b"\n"):
            _fail("cleanup sidecar retained cursor prefix is not complete")
        lines = complete_raw.splitlines()
        if len(lines) not in {1, 2}:
            _fail("cleanup sidecar cursor cardinality changed")
        documents = [
            _parse_document(line, "cleanup sidecar cursor record") for line in lines
        ]
        if documents[0] != expected_genesis:
            _fail("cleanup sidecar cursor genesis changed")
        if len(documents) == 2 and documents[1] != expected_commit:
            _fail("cleanup sidecar committed cursor changed")
        return documents

    if not raw.endswith(b"\n"):
        if not repair_torn_suffix or b"\n" not in raw:
            _fail("cleanup sidecar cursor has a torn record")
        cutoff = raw.rfind(b"\n") + 1
        retained = raw[:cutoff]
        suffix = raw[cutoff:]
        documents = decode_complete(retained)
        expected_suffix = canonical_json_bytes(expected_commit) + b"\n"
        if (
            len(documents) != 1
            or not suffix
            or len(suffix) >= len(expected_suffix)
            or not hmac.compare_digest(suffix, expected_suffix[: len(suffix)])
        ):
            _fail("cleanup sidecar torn suffix is not the unique expected commit")
        os.ftruncate(cursor_fd, cutoff)
        os.fsync(cursor_fd)
        return documents
    return decode_complete(raw)


def _append_cursor_commit(
    cursor_fd: int,
    allocation_id: str,
    records: list[dict[str, Any]],
    release_id: str,
) -> list[dict[str, Any]]:
    if len(records) != 1:
        _fail("cleanup sidecar release cursor was appended more than once")
    row = _cursor_document(
        _cursor_payload(
            allocation_id,
            sequence=1,
            previous_cursor_id=records[0]["h1_owner_cleanup_cursor_record_id"],
            state="RELEASE_COMMITTED",
            release_id=release_id,
        )
    )
    os.lseek(cursor_fd, 0, os.SEEK_END)
    _write_all(cursor_fd, canonical_json_bytes(row) + b"\n")
    os.fsync(cursor_fd)
    return [*records, row]


def _require_cleanup_lease_and_bindings(
    lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    *,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: phase_v2.H1AttemptCleanupTransitionV2,
    envelope: phase_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    action: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if (
        type(lease) is not phase_v2.H1AttemptCleanupOnlyLeaseV2
        or not lease._active
        or lease._owner_pid != os.getpid()
        or lease._owner_thread_id != threading.get_ident()
        or phase_v2._ACTIVE_V2_PHASE_LEASES.get() != (lease.handle.spec_id,)
        or phase_v1._ACTIVE_PHASE_LEASES.get() != (lease.handle.spec_id,)
    ):
        _fail("cleanup sidecar V2 lease is stale, crossed, forked, or inactive")
    lock_metadata = os.fstat(lease._lock_fd)
    cursor_metadata = os.fstat(lease._cursor_fd)
    if (
        (lock_metadata.st_dev, lock_metadata.st_ino)
        != (lease.handle.lock_device, lease.handle.lock_inode)
        or (cursor_metadata.st_dev, cursor_metadata.st_ino)
        != (lease.handle.cursor_device, lease.handle.cursor_inode)
        or rejection_v1._active_gate_modes(lease._gate_snapshot.gate_id)
        != (rejection_v1._CONTEXT_DEPENDENT_REPLAY_EXCLUSIVE,)
    ):
        _fail("cleanup sidecar V2 lease lost its retained phase/gate authority")
    if type(owner) is not owner_v4.H1SharedCapOwnerV4WalHandle:
        _fail("cleanup sidecar requires one exact V4 Owner handle")
    if type(transition) is not phase_v2.H1AttemptCleanupTransitionV2:
        _fail("cleanup sidecar requires one exact V2 transition")
    phase_v2._validate_transition_v2_for_handle(transition, lease.handle)
    if (
        lease.transition.transition_id != transition.transition_id
        or not hmac.compare_digest(
            lease.transition.canonical_bytes, transition.canonical_bytes
        )
    ):
        _fail("cleanup lease and V2 transition differ")
    if type(envelope) is not phase_v2.H1PreadmittedCleanupEnvelopeV1:
        _fail("cleanup sidecar requires one exact pre-admitted envelope")
    if type(cleanup_pass) is not cleanup_v1.H1LifecycleCleanupPassV1:
        _fail("cleanup sidecar requires one exact cleanup pass")
    transition_payload = transition.payload
    envelope_payload = envelope.payload
    pass_payload = cleanup_pass.payload
    if (
        transition_payload["h1_preadmitted_cleanup_envelope_id"]
        != envelope.envelope_id
        or transition_payload["h1_lifecycle_cleanup_pass_id"]
        != cleanup_pass.pass_id
        or transition_payload["branch_key"] != pass_payload["branch_key"]
        or transition_payload["h1_lifecycle_complete_branch_analysis_id"]
        != pass_payload["h1_lifecycle_complete_branch_analysis_id"]
        or envelope_payload["h1_shared_cap_owner_v3_runtime_id"]
        != owner.runtime_id
        or envelope_payload["h1_shared_cap_owner_v4_wal_binding_id"]
        != owner.binding_id
        or transition_payload["h1_shared_cap_owner_v3_runtime_id"]
        != owner.runtime_id
        or transition_payload["h1_shared_cap_owner_v4_wal_binding_id"]
        != owner.binding_id
    ):
        _fail("cleanup transition/envelope/pass/Owner identities crossed")
    if type(action) is not dict:
        _fail("cleanup sidecar action must be one exact cleanup-pass object")
    action_copy = dict(action)
    matches = [
        row
        for row in pass_payload["planned_cleanup_actions"]
        if row == action_copy
    ]
    kind = action_copy.get("action_kind")
    if (
        len(matches) != 1
        or kind not in _SUPPORTED_ACTIONS
        or action_copy.get("execution_authority_present") is not False
        or action_copy.get("new_business_work_allowed") is not False
        or action_copy.get("normal_route_reservation_allowed") is not False
        or action_copy.get("primary_failure_preserved") is not True
        or action_copy.get("secondary_failure_is_append_only") is not True
    ):
        _fail("cleanup sidecar action is absent, duplicate, or unsupported")
    expected_site, _expected_path = _SUPPORTED_ACTIONS[kind]
    if action_copy.get("target") != expected_site:
        _fail("cleanup sidecar action target changed")
    gate_snapshot = lease._gate_snapshot
    expected_commit: Any = (
        gate_snapshot.commit_id
        if gate_snapshot.commit_id is not None
        else _typed_null("NO_REJECTION_COMMIT")
    )
    expected_ack: Any = (
        gate_snapshot.acknowledgement_id
        if gate_snapshot.acknowledgement_id is not None
        else _typed_null("NO_REJECTION_ACK")
    )
    if (
        gate_snapshot.gate_id
        != transition_payload["h1_attempt_rejection_gate_id"]
        or gate_snapshot.state.value
        != transition_payload["gate_state_at_transition"]
        or transition_payload["gate_rejection_commit_id_at_transition"]
        != expected_commit
        or transition_payload["gate_rejection_ack_id_at_transition"]
        != expected_ack
    ):
        _fail("cleanup sidecar retained gate differs from the V2 transition")
    return transition_payload, pass_payload, action_copy


def _owner_head(state: owner_v3._ReplayState) -> Any:
    return state.head_id if state.head_id is not None else _typed_null("JOURNAL_GENESIS")


def _snapshot_directory_fd(
    directory_fd: int,
    *,
    names: list[str] | None = None,
) -> tuple[tuple[Any, ...], ...]:
    selected = sorted(os.listdir(directory_fd) if names is None else names)
    rows: list[tuple[Any, ...]] = []
    for name in selected:
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        mode = stat.S_IFMT(metadata.st_mode) | stat.S_IMODE(metadata.st_mode)
        digest: Any = _typed_null("DIRECTORY_ENTRY_HAS_NO_BYTES")
        if stat.S_ISREG(metadata.st_mode):
            flags = os.O_RDONLY | os.O_CLOEXEC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(name, flags, dir_fd=directory_fd)
            try:
                raw = _read_descriptor(descriptor)
            finally:
                os.close(descriptor)
            digest = hashlib.sha256(raw).hexdigest()
        elif not stat.S_ISDIR(metadata.st_mode):
            _fail("Owner preflight encountered a non-regular non-directory entry")
        rows.append(
            (
                name,
                mode,
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_nlink,
                metadata.st_size,
                digest,
            )
        )
    return tuple(rows)


def _owner_storage_snapshot_locked(
    root_fd: int,
    directory_fd: int,
    handle: owner_v3.H1SharedCapOwnerV3Handle,
) -> tuple[Any, ...]:
    root_names = [
        name
        for name in os.listdir(root_fd)
        if name
        in {
            handle.runtime_id,
            owner_v3._allocation_name(handle.runtime_id),
            owner_v3._cursor_token_name(handle.runtime_id),
            owner_v3._v4_wal_binding_name(handle.runtime_id),
            owner_v3._v4_wal_directory_name(handle.runtime_id),
        }
        or name.startswith(
            f"{owner_v3._CURSOR_STATE_PREFIX}{handle.runtime_id}-"
        )
        or name.startswith(owner_v3._v4_wal_binding_temp_prefix(handle.runtime_id))
    ]
    wal_fd = owner_v3._open_v4_wal_directory(handle)
    try:
        wal_snapshot = _snapshot_directory_fd(wal_fd)
    finally:
        os.close(wal_fd)
    return (
        _snapshot_directory_fd(root_fd, names=root_names),
        _snapshot_directory_fd(directory_fd),
        wal_snapshot,
    )


def _require_stable_owner_readonly_locked(
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
) -> tuple[int, int, owner_v3._ReplayState, tuple[Any, ...]]:
    """Acquire Owner EX and replay only a fully stable V4 namespace.

    This preflight deliberately does not call Owner's repair-capable replay.
    Any temp, pending cursor, adjacent committed cursor, or WAL payload is a
    negative result and remains byte-for-byte untouched for its owning recovery
    authority.
    """

    handle = owner.owner
    root_path = Path(handle.owner_root_realpath)
    root_fd = owner_v3._open_private_directory(root_path)
    directory_fd = cursor_token_fd = -1
    try:
        root_metadata = os.fstat(root_fd)
        if (root_metadata.st_dev, root_metadata.st_ino) != (
            handle.owner_root_device,
            handle.owner_root_inode,
        ):
            _fail("stable Owner preflight root inode changed")
        directory_fd = owner_v3._open_private_directory_at(root_fd, handle.runtime_id)
        directory_metadata = os.fstat(directory_fd)
        if (directory_metadata.st_dev, directory_metadata.st_ino) != (
            handle.owner_directory_device,
            handle.owner_directory_inode,
        ):
            _fail("stable Owner preflight directory inode changed")
        cursor_token_fd = owner_v3._open_cursor_token(root_fd, handle.runtime_id)
        cursor_metadata = os.fstat(cursor_token_fd)
        if (cursor_metadata.st_dev, cursor_metadata.st_ino) != (
            handle.cursor_token_device,
            handle.cursor_token_inode,
        ):
            _fail("stable Owner preflight cursor-token inode changed")
        allocation = owner_v3._freeze_or_verify_allocation(
            handle.runtime_id,
            root_path,
            root_fd,
            directory_fd,
            cursor_token_fd,
            allow_create=False,
        )
        os.close(cursor_token_fd)
        cursor_token_fd = -1
        fcntl.flock(directory_fd, fcntl.LOCK_EX)
        root_names = os.listdir(root_fd)
        if any(
            name.startswith(owner_v3._v4_wal_binding_temp_prefix(handle.runtime_id))
            for name in root_names
        ):
            _fail("stable Owner preflight refuses a repairable V4 binding temp")
        owner_names = os.listdir(directory_fd)
        if any(owner_v3._TEMP_PATTERN.fullmatch(name) for name in owner_names):
            _fail("stable Owner preflight refuses a repairable Owner temp")
        wal_binding = owner_v3._load_v4_wal_binding(
            root_fd, root_path, handle.runtime_id
        )
        if (
            wal_binding is None
            or wal_binding["h1_shared_cap_owner_v4_wal_binding_id"]
            != owner.binding_id
            or handle.pending_payload_wal_binding_id != owner.binding_id
        ):
            _fail("stable Owner preflight lost the exact V4 WAL binding")
        wal_fd = owner_v3._open_v4_wal_directory(handle)
        try:
            if os.listdir(wal_fd):
                _fail("stable Owner preflight refuses a repairable V4 WAL payload")
        finally:
            os.close(wal_fd)
        before = _owner_storage_snapshot_locked(root_fd, directory_fd, handle)
        profile_raw = owner_v3._read_file(directory_fd, owner_v3._PROFILE_FILE)
        source_raw = owner_v3._read_file(directory_fd, owner_v3._SOURCE_FILE)
        runtime_raw = owner_v3._read_file(directory_fd, owner_v3._RUNTIME_FILE)
        if profile_raw is None or source_raw is None or runtime_raw is None:
            _fail("stable Owner preflight lost static records")
        profile = owner_v3._profile_from_document(
            owner_v3._parse_document(profile_raw, "stable V3 profile")
        )
        source = owner_v3._source_from_document(
            owner_v3._parse_document(source_raw, "stable V3 source")
        )
        expected_runtime = owner_v3._runtime_document(
            profile,
            source,
            _cid(Path(handle.gate_directory).name, "attempt rejection gate"),
            owner_root_realpath=str(root_path),
            owner_root_device=allocation["owner_root_device"],
            owner_root_inode=allocation["owner_root_inode"],
        )
        runtime = owner_v3._parse_document(runtime_raw, "stable V3 runtime")
        if (
            profile.to_document() != handle.profile.to_document()
            or source.to_document() != handle.source_manifest.to_document()
            or runtime != expected_runtime
            or runtime["h1_shared_cap_owner_v3_runtime_id"] != handle.runtime_id
        ):
            _fail("stable Owner preflight static identity changed")
        state = owner_v3._replay_records_fd(directory_fd, handle)
        cursor_rows = owner_v3._cursor_states(
            root_fd,
            handle.runtime_id,
            expected_device=handle.cursor_token_device,
            expected_inode=handle.cursor_token_inode,
        )
        committed = [row for row in cursor_rows if row[0] == "C"]
        pending = [row for row in cursor_rows if row[0] == "P"]
        if (
            len(committed) != 1
            or pending
            or (state.sequence, state.head_id) != (committed[0][1], committed[0][2])
        ):
            _fail("stable Owner preflight refuses a repairable cursor frontier")
        binding_intent = owner_v3._v4_wal_binding_intent(state)
        if (
            binding_intent is None
            or binding_intent["operation_id"]
            != wal_binding["binding_control_operation_id"]
            or binding_intent["site_key"] != wal_binding["binding_control_site_key"]
        ):
            _fail("stable Owner preflight binding intent changed")
        after = _owner_storage_snapshot_locked(root_fd, directory_fd, handle)
        if after != before:
            _fail("stable Owner read-only preflight changed V3/V4 bytes or inodes")
        return root_fd, directory_fd, state, before
    except BaseException:
        if cursor_token_fd >= 0:
            os.close(cursor_token_fd)
        if directory_fd >= 0:
            os.close(directory_fd)
        os.close(root_fd)
        raise


def _validate_owner_cutoff_locked(
    lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition_payload: Mapping[str, Any],
) -> tuple[int, int, owner_v3._ReplayState, owner_v3._GateOwnerJoinV3]:
    root_fd, directory_fd, state, before = _require_stable_owner_readonly_locked(
        owner
    )
    try:
        join = owner_v3._validate_owner_gate_join(
            owner.owner, state, lease._gate_snapshot
        )
        pair_frontier = owner_v3._incomplete_pair_frontier(state)
        if (
            state.pending_cursor is not None
            or pair_frontier is not None
            or join.recovery_required
            or state.sequence
            != transition_payload["owner_tail_sequence_at_transition"]
            or _owner_head(state)
            != transition_payload["owner_tail_head_id_at_transition"]
            or join.status.value
            != transition_payload["gate_owner_join_status_at_transition"]
        ):
            _fail("cleanup sidecar requires the exact stable V3 transition cutoff")
        if _owner_storage_snapshot_locked(root_fd, directory_fd, owner.owner) != before:
            _fail("cleanup cutoff validation changed V3/V4 storage")
        return root_fd, directory_fd, state, join
    except BaseException:
        os.close(directory_fd)
        os.close(root_fd)
        raise


def _select_deferred_reservation(
    state: owner_v3._ReplayState,
    *,
    reservation_id: str,
    action: Mapping[str, Any],
) -> dict[str, Any]:
    reservation = state.reservations.get(_cid(reservation_id, "deferred reservation"))
    kind = action["action_kind"]
    expected_site, expected_path = _SUPPORTED_ACTIONS[kind]
    if (
        reservation is None
        or reservation["record_kind"] != "RESERVATION_DURABLE"
        or reservation["admission_outcome"] != "ADMITTED"
        or reservation["site_key"] != expected_site
        or reservation["path"] != expected_path
        or reservation["reservation_upper"] <= 0
        or reservation_id in state.cells
        or reservation_id in state.evidence
        or reservation_id in state.settlements
        or state.outstanding[expected_path] < reservation["reservation_upper"]
    ):
        _fail("cleanup action does not bind one outstanding deferred-origin reservation")
    return dict(reservation)


def _build_spec_locked(
    lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: phase_v2.H1AttemptCleanupTransitionV2,
    envelope: phase_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    action: Mapping[str, Any],
    state: owner_v3._ReplayState,
    reservation: Mapping[str, Any],
) -> H1OwnerCleanupSidecarSpecV1:
    transition_payload = transition.payload
    payload = {
        "schema": "acfqp.k7_h1_owner_cleanup_sidecar_spec.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_id": owner.profile.logical_occurrence_id,
        "route_attempt_id": owner.profile.route_attempt_id,
        "decision_point_id": owner.profile.decision_point_id,
        "transaction_id": owner.profile.transaction_id,
        "h1_attempt_execution_phase_spec_id": lease.handle.spec_id,
        "h1_attempt_phase_allocation_id": lease.handle.allocation_id,
        "phase_base_realpath": lease.handle.spec.payload["phase_base_realpath"],
        "phase_base_device": lease.handle.spec.payload["phase_base_device"],
        "phase_base_inode": lease.handle.spec.payload["phase_base_inode"],
        "h1_attempt_cleanup_transition_v2_id": transition.transition_id,
        "h1_attempt_rejection_gate_id": lease._gate_snapshot.gate_id,
        "h1_preadmitted_cleanup_envelope_id": envelope.envelope_id,
        "h1_lifecycle_cleanup_pass_id": cleanup_pass.pass_id,
        "h1_lifecycle_complete_branch_analysis_id": transition_payload[
            "h1_lifecycle_complete_branch_analysis_id"
        ],
        "branch_key": transition_payload["branch_key"],
        "h1_shared_cap_profile_core_v3_id": owner.profile.profile_id,
        "h1_shared_cap_owner_v3_runtime_id": owner.runtime_id,
        "h1_shared_cap_owner_v4_wal_binding_id": owner.binding_id,
        "owner_cutoff_sequence": state.sequence,
        "owner_cutoff_head_id": _owner_head(state),
        "gate_state_at_cutoff": lease._gate_snapshot.state.value,
        "gate_owner_join_status_at_cutoff": transition_payload[
            "gate_owner_join_status_at_transition"
        ],
        "h1_shared_cap_owner_v3_reservation_id": reservation[
            "h1_shared_cap_owner_v3_reservation_id"
        ],
        "operation_id": reservation["operation_id"],
        "deferred_origin_site_key": reservation["site_key"],
        "path": reservation["path"],
        "reducer": reservation["reducer"],
        "reservation_upper": reservation["reservation_upper"],
        "charged_at_cutoff": state.charged[reservation["path"]],
        "outstanding_at_cutoff": state.outstanding[reservation["path"]],
        "cleanup_action": dict(action),
        "cleanup_action_ordinal": action["cleanup_ordinal"],
        "cleanup_action_kind": action["action_kind"],
        "cleanup_action_target": action["target"],
        "sidecar_operation": _SEMANTIC_OPERATION,
        "native_observed_value": _typed_null("NATIVE_EFFECT_NOT_STARTED"),
        "native_effect_started": False,
        "memory_read_performed": False,
        "output_finalize_performed": False,
        "v3_v4_owner_bytes_preserved": True,
        "cleanup_arbitrary_executor_present": False,
        "cleanup_native_effect_authority_present": False,
        "output_owner_close_authority_present": False,
        "production_output_leaf_authority_present": False,
        "production_execution_authority_present": False,
        "current_access_authority_present": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    return H1OwnerCleanupSidecarSpecV1(
        _SPEC_ISSUER, canonical_json_bytes(payload)
    )


def _require_spec_matches_locked(
    spec: H1OwnerCleanupSidecarSpecV1,
    lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: phase_v2.H1AttemptCleanupTransitionV2,
    envelope: phase_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    action: Mapping[str, Any],
    state: owner_v3._ReplayState,
) -> dict[str, Any]:
    reservation_id = spec.payload["h1_shared_cap_owner_v3_reservation_id"]
    reservation = _select_deferred_reservation(
        state, reservation_id=reservation_id, action=action
    )
    expected = _build_spec_locked(
        lease,
        owner,
        transition,
        envelope,
        cleanup_pass,
        action,
        state,
        reservation,
    )
    if (
        expected.spec_id != spec.spec_id
        or not hmac.compare_digest(expected.canonical_bytes, spec.canonical_bytes)
    ):
        _fail("cleanup sidecar spec differs from the exact retained Owner cutoff")
    return reservation


def validate_h1_owner_cleanup_context_with_retained_lease_v1(
    lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    *,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: phase_v2.H1AttemptCleanupTransitionV2,
    envelope: phase_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    action: Mapping[str, Any],
    reservation_id: str,
) -> dict[str, Any]:
    """Validate the exact cleanup/gate/Owner join without mutating V3/V4."""

    transition_payload, _pass_payload, action_copy = (
        _require_cleanup_lease_and_bindings(
            lease,
            owner=owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
    )
    root_fd, directory_fd, state, join = _validate_owner_cutoff_locked(
        lease, owner, transition_payload
    )
    try:
        reservation = _select_deferred_reservation(
            state,
            reservation_id=_cid(reservation_id, "deferred reservation"),
            action=action_copy,
        )
        return {
            "schema": "acfqp.k7_h1_owner_cleanup_retained_context.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_attempt_cleanup_transition_v2_id": transition.transition_id,
            "h1_shared_cap_owner_v3_runtime_id": owner.runtime_id,
            "h1_shared_cap_owner_v4_wal_binding_id": owner.binding_id,
            "h1_shared_cap_owner_v3_reservation_id": reservation[
                "h1_shared_cap_owner_v3_reservation_id"
            ],
            "owner_cutoff_sequence": state.sequence,
            "owner_cutoff_head_id": _owner_head(state),
            "gate_owner_join_status": join.status.value,
            "path": reservation["path"],
            "reservation_upper": reservation["reservation_upper"],
            "retained_phase_gate_owner_validation_complete": True,
            "v3_v4_owner_bytes_preserved": True,
            "cleanup_arbitrary_executor_present": False,
            "output_owner_close_authority_present": False,
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
            "production_execution_authority_present": False,
            "formal_counter_record_issued": False,
            "official_execution_allowed": False,
        }
    finally:
        os.close(directory_fd)
        os.close(root_fd)


def _ensure_storage_root(base_directory: str | Path) -> Path:
    base = Path(base_directory).resolve()
    if not base.is_absolute() or not base.is_dir():
        _fail("cleanup sidecar base directory is invalid")
    root = base / _ROOT_NAME
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        pass
    metadata = os.lstat(root)
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o700:
        _fail("cleanup sidecar root is not one private directory")
    return root


def _ensure_regular_file(
    directory_fd: int,
    name: str,
    *,
    initial: bytes = b"",
) -> tuple[int, os.stat_result]:
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    created = False
    try:
        try:
            descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
            created = True
        except FileExistsError:
            descriptor = _open_regular_at(directory_fd, name, flags=os.O_RDWR)
        except OSError as error:
            raise ConstructionK7H1OwnerCleanupContinuationSidecarV1Error(
                f"cannot create cleanup sidecar mutable file: {name}"
            ) from error
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            _fail(f"cleanup sidecar mutable file mode changed: {name}")
        if created and initial:
            _write_all(descriptor, initial)
            os.fsync(descriptor)
        if created:
            os.fsync(directory_fd)
        return descriptor, metadata
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _allocation_payload(
    spec: H1OwnerCleanupSidecarSpecV1,
    *,
    root_path: Path,
    root_metadata: os.stat_result,
    root_lock_metadata: os.stat_result,
    sidecar_path: Path,
    sidecar_metadata: os.stat_result,
    lock_metadata: os.stat_result,
    cursor_metadata: os.stat_result,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_owner_cleanup_sidecar_allocation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_owner_cleanup_sidecar_spec_id": spec.spec_id,
        "h1_shared_cap_owner_v3_runtime_id": spec.payload[
            "h1_shared_cap_owner_v3_runtime_id"
        ],
        "h1_shared_cap_owner_v3_reservation_id": spec.payload[
            "h1_shared_cap_owner_v3_reservation_id"
        ],
        "sidecar_root_realpath": str(root_path),
        "sidecar_root_device": root_metadata.st_dev,
        "sidecar_root_inode": root_metadata.st_ino,
        "root_allocation_lock_device": root_lock_metadata.st_dev,
        "root_allocation_lock_inode": root_lock_metadata.st_ino,
        "sidecar_directory_realpath": str(sidecar_path),
        "sidecar_directory_device": sidecar_metadata.st_dev,
        "sidecar_directory_inode": sidecar_metadata.st_ino,
        "sidecar_lock_device": lock_metadata.st_dev,
        "sidecar_lock_inode": lock_metadata.st_ino,
        "sidecar_cursor_device": cursor_metadata.st_dev,
        "sidecar_cursor_inode": cursor_metadata.st_ino,
        "allocation_is_immutable": True,
        "root_allocation_seal_required": True,
        "v3_v4_owner_bytes_preserved": True,
        "cleanup_arbitrary_executor_present": False,
        "cleanup_native_effect_authority_present": False,
        "output_owner_close_authority_present": False,
        "production_execution_authority_present": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "formal_counter_record_issued": False,
        "official_execution_allowed": False,
    }


def _allocation_from_raw(raw: bytes) -> H1OwnerCleanupSidecarAllocationV1:
    document = _parse_document(raw, "cleanup sidecar allocation")
    payload = dict(document)
    claimed = _cid(
        payload.pop("h1_owner_cleanup_sidecar_allocation_id", None),
        "cleanup sidecar allocation",
    )
    allocation = H1OwnerCleanupSidecarAllocationV1(
        _ALLOCATION_ISSUER, canonical_json_bytes(payload)
    )
    if allocation.allocation_id != claimed:
        _fail("cleanup sidecar allocation content ID changed")
    return allocation


def _release_from_raw(raw: bytes) -> H1OwnerCleanupReleaseV1:
    document = _parse_document(raw, "cleanup release")
    payload = dict(document)
    claimed = _cid(
        payload.pop("h1_owner_cleanup_release_id", None), "cleanup release"
    )
    release = H1OwnerCleanupReleaseV1(
        _RELEASE_ISSUER, canonical_json_bytes(payload)
    )
    if release.release_id != claimed:
        _fail("cleanup release content ID changed")
    return release


def _handle_from_allocation(
    spec: H1OwnerCleanupSidecarSpecV1,
    allocation: H1OwnerCleanupSidecarAllocationV1,
) -> H1OwnerCleanupSidecarHandleV1:
    payload = allocation.payload
    return H1OwnerCleanupSidecarHandleV1(
        _HANDLE_ISSUER,
        spec,
        allocation,
        payload["sidecar_root_realpath"],
        payload["sidecar_root_device"],
        payload["sidecar_root_inode"],
        payload["root_allocation_lock_device"],
        payload["root_allocation_lock_inode"],
        payload["sidecar_directory_realpath"],
        payload["sidecar_directory_device"],
        payload["sidecar_directory_inode"],
        payload["sidecar_lock_device"],
        payload["sidecar_lock_inode"],
        payload["sidecar_cursor_device"],
        payload["sidecar_cursor_inode"],
    )


def _verify_allocation_storage(
    root_fd: int,
    sidecar_fd: int,
    spec: H1OwnerCleanupSidecarSpecV1,
    allocation: H1OwnerCleanupSidecarAllocationV1,
) -> None:
    _require_same_immutable_file(
        _read_file(sidecar_fd, _ALLOCATION_FILE),
        _read_file(root_fd, _allocation_seal_name(spec)),
        expected_raw=allocation.canonical_bytes,
        label="cleanup sidecar allocation/root seal",
    )


def _require_handle_storage_locked(
    handle: H1OwnerCleanupSidecarHandleV1,
) -> tuple[int, int, int, int]:
    if type(handle) is not H1OwnerCleanupSidecarHandleV1:
        _fail("cleanup sidecar operation requires one exact handle")
    root_fd = _open_directory(Path(handle.root_directory))
    root_lock_check_fd = sidecar_fd = lock_fd = cursor_fd = -1
    try:
        root_metadata = os.fstat(root_fd)
        if (root_metadata.st_dev, root_metadata.st_ino) != (
            handle.root_device,
            handle.root_inode,
        ):
            _fail("cleanup sidecar root inode changed")
        root_lock_check_fd = _open_regular_at(
            root_fd, _ROOT_LOCK_FILE, flags=os.O_RDONLY
        )
        root_lock_metadata = os.fstat(root_lock_check_fd)
        if (
            (root_lock_metadata.st_dev, root_lock_metadata.st_ino)
            != (handle.root_lock_device, handle.root_lock_inode)
            or stat.S_IMODE(root_lock_metadata.st_mode) != 0o600
        ):
            _fail("cleanup sidecar root allocation lock inode or mode changed")
        os.close(root_lock_check_fd)
        root_lock_check_fd = -1
        sidecar_fd = _open_directory(Path(handle.sidecar_directory))
        sidecar_metadata = os.fstat(sidecar_fd)
        if (sidecar_metadata.st_dev, sidecar_metadata.st_ino) != (
            handle.sidecar_device,
            handle.sidecar_inode,
        ):
            _fail("cleanup sidecar directory inode changed")
        lock_fd = _open_regular_at(sidecar_fd, _LOCK_FILE, flags=os.O_RDWR)
        lock_metadata = os.fstat(lock_fd)
        if (
            (lock_metadata.st_dev, lock_metadata.st_ino)
            != (handle.lock_device, handle.lock_inode)
            or stat.S_IMODE(lock_metadata.st_mode) != 0o600
        ):
            _fail("cleanup sidecar lock inode or mode changed")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        cursor_fd = _open_regular_at(sidecar_fd, _CURSOR_FILE, flags=os.O_RDWR)
        cursor_metadata = os.fstat(cursor_fd)
        if (
            (cursor_metadata.st_dev, cursor_metadata.st_ino)
            != (handle.cursor_device, handle.cursor_inode)
            or stat.S_IMODE(cursor_metadata.st_mode) != 0o600
        ):
            _fail("cleanup sidecar cursor inode or mode changed")
        _verify_allocation_storage(root_fd, sidecar_fd, handle.spec, handle.allocation)
        _cleanup_temps(sidecar_fd)
        return root_fd, sidecar_fd, lock_fd, cursor_fd
    except BaseException:
        if root_lock_check_fd >= 0:
            os.close(root_lock_check_fd)
        if cursor_fd >= 0:
            os.close(cursor_fd)
        if lock_fd >= 0:
            os.close(lock_fd)
        if sidecar_fd >= 0:
            os.close(sidecar_fd)
        os.close(root_fd)
        raise


def _release_storage(root_fd: int, sidecar_fd: int, lock_fd: int, cursor_fd: int) -> None:
    os.close(cursor_fd)
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    os.close(lock_fd)
    os.close(sidecar_fd)
    os.close(root_fd)


def _load_existing_allocation_under_root_lock(
    root_fd: int,
    spec: H1OwnerCleanupSidecarSpecV1,
) -> H1OwnerCleanupSidecarAllocationV1 | None:
    entry = _read_file(root_fd, _allocation_seal_name(spec))
    if entry is None:
        return None
    allocation = _allocation_from_raw(entry[0])
    if allocation.payload["h1_owner_cleanup_sidecar_spec_id"] != spec.spec_id:
        _fail("deferred reservation is already allocated to a crossed sidecar")
    return allocation


def _recover_allocation_under_root_lock(
    root_path: Path,
    root_fd: int,
    spec: H1OwnerCleanupSidecarSpecV1,
    *,
    expected_allocation_id: str,
) -> H1OwnerCleanupSidecarAllocationV1:
    sidecar_path = root_path / f"{_SIDECAR_PREFIX}{spec.spec_id}"
    sidecar_fd = _open_directory(sidecar_path)
    try:
        inside = _read_file(sidecar_fd, _ALLOCATION_FILE)
        sealed = _read_file(root_fd, _allocation_seal_name(spec))
        if inside is None and sealed is None:
            _fail("expected cleanup sidecar allocation is absent")
        source = inside if inside is not None else sealed
        assert source is not None
        allocation = _allocation_from_raw(source[0])
        if (
            allocation.allocation_id != expected_allocation_id
            or allocation.payload["h1_owner_cleanup_sidecar_spec_id"] != spec.spec_id
        ):
            _fail("expected cleanup sidecar allocation is crossed")
        if inside is None:
            if not _link_cross_directory(
                root_fd,
                _allocation_seal_name(spec),
                sidecar_fd,
                _ALLOCATION_FILE,
            ):
                _fail("cleanup sidecar allocation-link recovery conflicted")
        if sealed is None:
            if not _link_cross_directory(
                sidecar_fd,
                _ALLOCATION_FILE,
                root_fd,
                _allocation_seal_name(spec),
            ):
                _fail("cleanup sidecar allocation-seal recovery conflicted")
        _verify_allocation_storage(root_fd, sidecar_fd, spec, allocation)
        return allocation
    finally:
        os.close(sidecar_fd)


def _initialize_storage_under_owner_lock(
    base_directory: str | Path,
    spec: H1OwnerCleanupSidecarSpecV1,
) -> H1OwnerCleanupSidecarHandleV1:
    root_path = _ensure_storage_root(base_directory)
    root_fd = _open_directory(root_path)
    root_lock_fd = sidecar_fd = lock_fd = cursor_fd = -1
    try:
        root_lock_fd, root_lock_metadata = _ensure_regular_file(
            root_fd, _ROOT_LOCK_FILE
        )
        fcntl.flock(root_lock_fd, fcntl.LOCK_EX)
        existing = _load_existing_allocation_under_root_lock(root_fd, spec)
        if existing is not None:
            handle = _handle_from_allocation(spec, existing)
            check_root, check_sidecar, check_lock, check_cursor = (
                _require_handle_storage_locked(handle)
            )
            _release_storage(check_root, check_sidecar, check_lock, check_cursor)
            return handle
        sidecar_path = root_path / f"{_SIDECAR_PREFIX}{spec.spec_id}"
        try:
            sidecar_path.mkdir(mode=0o700)
        except FileExistsError:
            pass
        sidecar_fd = _open_directory(sidecar_path)
        sidecar_metadata = os.fstat(sidecar_fd)
        lock_fd, lock_metadata = _ensure_regular_file(sidecar_fd, _LOCK_FILE)
        genesis_placeholder = b""
        cursor_fd, cursor_metadata = _ensure_regular_file(
            sidecar_fd, _CURSOR_FILE, initial=genesis_placeholder
        )
        root_metadata = os.fstat(root_fd)
        allocation_payload = _allocation_payload(
            spec,
            root_path=root_path,
            root_metadata=root_metadata,
            root_lock_metadata=root_lock_metadata,
            sidecar_path=sidecar_path,
            sidecar_metadata=sidecar_metadata,
            lock_metadata=lock_metadata,
            cursor_metadata=cursor_metadata,
        )
        allocation = H1OwnerCleanupSidecarAllocationV1(
            _ALLOCATION_ISSUER, canonical_json_bytes(allocation_payload)
        )
        cursor_raw = _read_descriptor(cursor_fd)
        genesis_raw = canonical_json_bytes(_genesis_cursor(allocation.allocation_id)) + b"\n"
        if not cursor_raw:
            _write_all(cursor_fd, genesis_raw)
            os.fsync(cursor_fd)
        elif not hmac.compare_digest(cursor_raw, genesis_raw):
            _fail("pre-allocation cleanup cursor differs from exact genesis")
        if not _publish_new(sidecar_fd, _ALLOCATION_FILE, allocation.canonical_bytes):
            current = _read_file(sidecar_fd, _ALLOCATION_FILE)
            if current is None or not hmac.compare_digest(
                current[0], allocation.canonical_bytes
            ):
                _fail("cleanup sidecar allocation publication conflicted")
        if not _link_cross_directory(
            sidecar_fd,
            _ALLOCATION_FILE,
            root_fd,
            _allocation_seal_name(spec),
        ):
            _require_same_immutable_file(
                _read_file(sidecar_fd, _ALLOCATION_FILE),
                _read_file(root_fd, _allocation_seal_name(spec)),
                expected_raw=allocation.canonical_bytes,
                label="cleanup sidecar allocation/root seal",
            )
        _verify_allocation_storage(root_fd, sidecar_fd, spec, allocation)
        return _handle_from_allocation(spec, allocation)
    finally:
        if cursor_fd >= 0:
            os.close(cursor_fd)
        if lock_fd >= 0:
            os.close(lock_fd)
        if sidecar_fd >= 0:
            os.close(sidecar_fd)
        if root_lock_fd >= 0:
            fcntl.flock(root_lock_fd, fcntl.LOCK_UN)
            os.close(root_lock_fd)
        os.close(root_fd)


def initialize_h1_owner_cleanup_continuation_sidecar_v1(
    base_directory: str | Path,
    *,
    cleanup_lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: phase_v2.H1AttemptCleanupTransitionV2,
    envelope: phase_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    action: Mapping[str, Any],
    reservation_id: str,
) -> H1OwnerCleanupSidecarHandleV1:
    transition_payload, _pass_payload, action_copy = (
        _require_cleanup_lease_and_bindings(
            cleanup_lease,
            owner=owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
    )
    canonical_base = _canonical_phase_base(cleanup_lease, base_directory)
    owner_root_fd, owner_directory_fd, state, _join = _validate_owner_cutoff_locked(
        cleanup_lease, owner, transition_payload
    )
    try:
        reservation = _select_deferred_reservation(
            state,
            reservation_id=_cid(reservation_id, "deferred reservation"),
            action=action_copy,
        )
        spec = _build_spec_locked(
            cleanup_lease,
            owner,
            transition,
            envelope,
            cleanup_pass,
            action_copy,
            state,
            reservation,
        )
        return _initialize_storage_under_owner_lock(canonical_base, spec)
    finally:
        os.close(owner_directory_fd)
        os.close(owner_root_fd)


def open_h1_owner_cleanup_continuation_sidecar_v1(
    base_directory: str | Path,
    *,
    expected_allocation_id: str,
    cleanup_lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: phase_v2.H1AttemptCleanupTransitionV2,
    envelope: phase_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    action: Mapping[str, Any],
    reservation_id: str,
) -> H1OwnerCleanupSidecarHandleV1:
    """Reopen one exact allocation after a process/crash boundary."""

    expected = _cid(expected_allocation_id, "expected cleanup sidecar allocation")
    transition_payload, _pass_payload, action_copy = (
        _require_cleanup_lease_and_bindings(
            cleanup_lease,
            owner=owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
    )
    canonical_base = _canonical_phase_base(cleanup_lease, base_directory)
    owner_root_fd, owner_directory_fd, state, _join = _validate_owner_cutoff_locked(
        cleanup_lease, owner, transition_payload
    )
    root_fd = root_lock_fd = -1
    try:
        reservation = _select_deferred_reservation(
            state,
            reservation_id=_cid(reservation_id, "deferred reservation"),
            action=action_copy,
        )
        spec = _build_spec_locked(
            cleanup_lease,
            owner,
            transition,
            envelope,
            cleanup_pass,
            action_copy,
            state,
            reservation,
        )
        root_path = canonical_base / _ROOT_NAME
        root_fd = _open_directory(root_path)
        root_metadata = os.fstat(root_fd)
        root_lock_fd = _open_regular_at(root_fd, _ROOT_LOCK_FILE, flags=os.O_RDWR)
        root_lock_metadata = os.fstat(root_lock_fd)
        fcntl.flock(root_lock_fd, fcntl.LOCK_EX)
        allocation = _recover_allocation_under_root_lock(
            root_path,
            root_fd,
            spec,
            expected_allocation_id=expected,
        )
        allocation_payload = allocation.payload
        if (
            allocation_payload["sidecar_root_realpath"] != str(root_path)
            or (
                allocation_payload["sidecar_root_device"],
                allocation_payload["sidecar_root_inode"],
            )
            != (root_metadata.st_dev, root_metadata.st_ino)
            or (
                allocation_payload["root_allocation_lock_device"],
                allocation_payload["root_allocation_lock_inode"],
            )
            != (root_lock_metadata.st_dev, root_lock_metadata.st_ino)
        ):
            _fail("cleanup sidecar allocation crossed its storage root")
        handle = _handle_from_allocation(spec, allocation)
        check_root, check_sidecar, check_lock, check_cursor = (
            _require_handle_storage_locked(handle)
        )
        try:
            _reconcile_release_locked(
                handle, check_root, check_sidecar, check_cursor, repair=True
            )
        finally:
            _release_storage(check_root, check_sidecar, check_lock, check_cursor)
        return handle
    finally:
        if root_lock_fd >= 0:
            fcntl.flock(root_lock_fd, fcntl.LOCK_UN)
            os.close(root_lock_fd)
        if root_fd >= 0:
            os.close(root_fd)
        os.close(owner_directory_fd)
        os.close(owner_root_fd)


def _build_release(handle: H1OwnerCleanupSidecarHandleV1) -> H1OwnerCleanupReleaseV1:
    spec = handle.spec.payload
    upper = spec["reservation_upper"]
    before_charged = spec["charged_at_cutoff"]
    before_outstanding = spec["outstanding_at_cutoff"]
    after_charged = (
        before_charged + upper
        if spec["reducer"] == owner_v3.H1SharedReducerV3.SUM.value
        else max(before_charged, upper)
    )
    after_outstanding = before_outstanding - upper
    if after_outstanding < 0:
        _fail("cleanup release would make combined outstanding negative")
    payload = {
        "schema": "acfqp.k7_h1_owner_cleanup_release.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_owner_cleanup_sidecar_spec_id": handle.spec.spec_id,
        "h1_owner_cleanup_sidecar_allocation_id": handle.allocation_id,
        "h1_attempt_cleanup_transition_v2_id": spec[
            "h1_attempt_cleanup_transition_v2_id"
        ],
        "h1_preadmitted_cleanup_envelope_id": spec[
            "h1_preadmitted_cleanup_envelope_id"
        ],
        "h1_lifecycle_cleanup_pass_id": spec["h1_lifecycle_cleanup_pass_id"],
        "cleanup_action_ordinal": spec["cleanup_action_ordinal"],
        "cleanup_action_kind": spec["cleanup_action_kind"],
        "cleanup_action_target": spec["cleanup_action_target"],
        "h1_shared_cap_owner_v3_runtime_id": spec[
            "h1_shared_cap_owner_v3_runtime_id"
        ],
        "h1_shared_cap_owner_v4_wal_binding_id": spec[
            "h1_shared_cap_owner_v4_wal_binding_id"
        ],
        "owner_cutoff_sequence": spec["owner_cutoff_sequence"],
        "owner_cutoff_head_id": spec["owner_cutoff_head_id"],
        "h1_shared_cap_owner_v3_reservation_id": spec[
            "h1_shared_cap_owner_v3_reservation_id"
        ],
        "operation_id": spec["operation_id"],
        "deferred_origin_site_key": spec["deferred_origin_site_key"],
        "path": spec["path"],
        "reducer": spec["reducer"],
        "sidecar_operation": _SEMANTIC_OPERATION,
        "reservation_upper": upper,
        "native_observed_value": _typed_null("NATIVE_EFFECT_NOT_STARTED"),
        "charged_value": upper,
        "charged_before": before_charged,
        "charged_after": after_charged,
        "outstanding_before": before_outstanding,
        "outstanding_after": after_outstanding,
        "native_effect_started": False,
        "memory_read_performed": False,
        "output_finalize_performed": False,
        "outstanding_released": True,
        "single_spend": True,
        "conservative_charge": True,
        "v3_owner_record_appended": False,
        "v4_wal_payload_appended": False,
        "v3_v4_owner_bytes_preserved": True,
        "cleanup_arbitrary_executor_present": False,
        "cleanup_native_effect_authority_present": False,
        "output_owner_close_authority_present": False,
        "production_output_leaf_authority_present": False,
        "production_execution_authority_present": False,
        "current_access_authority_present": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    return H1OwnerCleanupReleaseV1(_RELEASE_ISSUER, canonical_json_bytes(payload))


def _reconcile_release_locked(
    handle: H1OwnerCleanupSidecarHandleV1,
    root_fd: int,
    sidecar_fd: int,
    cursor_fd: int,
    *,
    repair: bool,
) -> tuple[H1OwnerCleanupReleaseV1 | None, list[dict[str, Any]]]:
    expected = _build_release(handle)
    records = _read_cursor_locked(
        cursor_fd,
        handle.allocation_id,
        expected_release_id=expected.release_id,
        repair_torn_suffix=repair,
    )
    release_entry = _read_file(sidecar_fd, _RELEASE_FILE)
    seal_entry = _read_file(root_fd, _release_seal_name(handle.spec))
    if release_entry is None and seal_entry is None:
        if len(records) != 1:
            _fail("cleanup release cursor survived without release/root seal")
        return None, records
    if release_entry is None:
        if not repair:
            _fail("cleanup release file is absent while root seal exists")
        if not _link_cross_directory(
            root_fd,
            _release_seal_name(handle.spec),
            sidecar_fd,
            _RELEASE_FILE,
        ):
            _fail("cleanup release repair conflicted")
        release_entry = _read_file(sidecar_fd, _RELEASE_FILE)
    if seal_entry is None:
        if not repair:
            _fail("cleanup release root seal is absent")
        if not _link_cross_directory(
            sidecar_fd,
            _RELEASE_FILE,
            root_fd,
            _release_seal_name(handle.spec),
        ):
            _fail("cleanup release root-seal repair conflicted")
        seal_entry = _read_file(root_fd, _release_seal_name(handle.spec))
    _require_same_immutable_file(
        release_entry,
        seal_entry,
        expected_raw=expected.canonical_bytes,
        label="cleanup release/root seal",
    )
    release = _release_from_raw(release_entry[0])
    if release.release_id != expected.release_id:
        _fail("cleanup release differs from its exact allocation")
    if len(records) == 1:
        if not repair:
            _fail("cleanup release exists before cursor commit")
        records = _append_cursor_commit(
            cursor_fd, handle.allocation_id, records, release.release_id
        )
    if (
        len(records) != 2
        or records[-1]["h1_owner_cleanup_release_id"] != release.release_id
    ):
        _fail("cleanup release cursor and immutable event differ")
    return release, records


def _require_handle_spec_current_locked(
    handle: H1OwnerCleanupSidecarHandleV1,
    cleanup_lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: phase_v2.H1AttemptCleanupTransitionV2,
    envelope: phase_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    action: Mapping[str, Any],
    state: owner_v3._ReplayState,
) -> dict[str, Any]:
    return _require_spec_matches_locked(
        handle.spec,
        cleanup_lease,
        owner,
        transition,
        envelope,
        cleanup_pass,
        action,
        state,
    )


def conservatively_release_h1_owner_cleanup_reservation_v1(
    handle: H1OwnerCleanupSidecarHandleV1,
    *,
    cleanup_lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: phase_v2.H1AttemptCleanupTransitionV2,
    envelope: phase_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    action: Mapping[str, Any],
    crash_point: H1OwnerCleanupSidecarCrashPointV1 = (
        H1OwnerCleanupSidecarCrashPointV1.NONE
    ),
) -> H1OwnerCleanupReleaseV1:
    """Commit or recover the one conservative release without touching Owner."""

    if type(handle) is not H1OwnerCleanupSidecarHandleV1:
        _fail("cleanup release requires one exact sidecar handle")
    try:
        fault = H1OwnerCleanupSidecarCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1OwnerCleanupContinuationSidecarV1Error(
            "cleanup sidecar crash point is invalid"
        ) from error
    transition_payload, _pass_payload, action_copy = (
        _require_cleanup_lease_and_bindings(
            cleanup_lease,
            owner=owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
    )
    owner_root_fd, owner_directory_fd, state, _join = _validate_owner_cutoff_locked(
        cleanup_lease, owner, transition_payload
    )
    root_fd = sidecar_fd = lock_fd = cursor_fd = -1
    try:
        _require_handle_spec_current_locked(
            handle,
            cleanup_lease,
            owner,
            transition,
            envelope,
            cleanup_pass,
            action_copy,
            state,
        )
        root_fd, sidecar_fd, lock_fd, cursor_fd = _require_handle_storage_locked(
            handle
        )
        existing, _records = _reconcile_release_locked(
            handle, root_fd, sidecar_fd, cursor_fd, repair=True
        )
        if existing is not None:
            return existing
        release = _build_release(handle)
        if not _publish_new(sidecar_fd, _RELEASE_FILE, release.canonical_bytes):
            current = _read_file(sidecar_fd, _RELEASE_FILE)
            if current is None or not hmac.compare_digest(
                current[0], release.canonical_bytes
            ):
                _fail("cleanup release publication conflicted")
        if fault is H1OwnerCleanupSidecarCrashPointV1.AFTER_RELEASE_FSYNC:
            raise H1OwnerCleanupSidecarInjectedCrashV1(
                "cleanup sidecar crash after release fsync"
            )
        if not _link_cross_directory(
            sidecar_fd,
            _RELEASE_FILE,
            root_fd,
            _release_seal_name(handle.spec),
        ):
            _require_same_immutable_file(
                _read_file(sidecar_fd, _RELEASE_FILE),
                _read_file(root_fd, _release_seal_name(handle.spec)),
                expected_raw=release.canonical_bytes,
                label="cleanup release/root seal",
            )
        if fault is H1OwnerCleanupSidecarCrashPointV1.AFTER_ROOT_SEAL_FSYNC:
            raise H1OwnerCleanupSidecarInjectedCrashV1(
                "cleanup sidecar crash after root-seal fsync"
            )
        records = _read_cursor_locked(
            cursor_fd,
            handle.allocation_id,
            expected_release_id=release.release_id,
            repair_torn_suffix=True,
        )
        if len(records) == 1:
            _append_cursor_commit(
                cursor_fd, handle.allocation_id, records, release.release_id
            )
        if fault is H1OwnerCleanupSidecarCrashPointV1.AFTER_CURSOR_FSYNC:
            raise H1OwnerCleanupSidecarInjectedCrashV1(
                "cleanup sidecar crash after cursor fsync"
            )
        recovered, _records = _reconcile_release_locked(
            handle, root_fd, sidecar_fd, cursor_fd, repair=False
        )
        if recovered is None:  # pragma: no cover - construction invariant
            _fail("cleanup release disappeared after cursor commit")
        return recovered
    finally:
        if cursor_fd >= 0:
            _release_storage(root_fd, sidecar_fd, lock_fd, cursor_fd)
        os.close(owner_directory_fd)
        os.close(owner_root_fd)


def verify_h1_owner_cleanup_combined_state_v1(
    handle: H1OwnerCleanupSidecarHandleV1,
    *,
    cleanup_lease: phase_v2.H1AttemptCleanupOnlyLeaseV2,
    owner: owner_v4.H1SharedCapOwnerV4WalHandle,
    transition: phase_v2.H1AttemptCleanupTransitionV2,
    envelope: phase_v2.H1PreadmittedCleanupEnvelopeV1,
    cleanup_pass: cleanup_v1.H1LifecycleCleanupPassV1,
    action: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute V3 cutoff plus exactly one sidecar spend under retained locks."""

    if type(handle) is not H1OwnerCleanupSidecarHandleV1:
        _fail("combined cleanup replay requires one exact sidecar handle")
    transition_payload, _pass_payload, action_copy = (
        _require_cleanup_lease_and_bindings(
            cleanup_lease,
            owner=owner,
            transition=transition,
            envelope=envelope,
            cleanup_pass=cleanup_pass,
            action=action,
        )
    )
    owner_root_fd, owner_directory_fd, state, join = _validate_owner_cutoff_locked(
        cleanup_lease, owner, transition_payload
    )
    root_fd = sidecar_fd = lock_fd = cursor_fd = -1
    try:
        reservation = _require_handle_spec_current_locked(
            handle,
            cleanup_lease,
            owner,
            transition,
            envelope,
            cleanup_pass,
            action_copy,
            state,
        )
        root_fd, sidecar_fd, lock_fd, cursor_fd = _require_handle_storage_locked(
            handle
        )
        release, records = _reconcile_release_locked(
            handle, root_fd, sidecar_fd, cursor_fd, repair=True
        )
        if release is None or len(records) != 2:
            _fail("combined cleanup replay requires one committed sidecar release")
        released = release.payload
        path = reservation["path"]
        charged = dict(state.charged)
        outstanding = dict(state.outstanding)
        if (
            released["charged_before"] != charged[path]
            or released["outstanding_before"] != outstanding[path]
            or released["reservation_upper"] != reservation["reservation_upper"]
            or released["charged_value"] != reservation["reservation_upper"]
            or released["native_observed_value"]
            != _typed_null("NATIVE_EFFECT_NOT_STARTED")
            or released["native_effect_started"] is not False
            or released["memory_read_performed"] is not False
            or released["output_finalize_performed"] is not False
            or released["single_spend"] is not True
            or released["outstanding_released"] is not True
        ):
            _fail("combined cleanup release semantics changed")
        charged[path] = released["charged_after"]
        outstanding[path] = released["outstanding_after"]
        payload = {
            "schema": "acfqp.k7_h1_owner_cleanup_combined_state.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_owner_cleanup_sidecar_spec_id": handle.spec.spec_id,
            "h1_owner_cleanup_sidecar_allocation_id": handle.allocation_id,
            "h1_owner_cleanup_release_id": release.release_id,
            "h1_attempt_cleanup_transition_v2_id": transition.transition_id,
            "h1_shared_cap_owner_v3_runtime_id": owner.runtime_id,
            "h1_shared_cap_owner_v4_wal_binding_id": owner.binding_id,
            "owner_cutoff_sequence": state.sequence,
            "owner_cutoff_head_id": _owner_head(state),
            "gate_owner_join_status": join.status.value,
            "v3_charged_values": dict(state.charged),
            "v3_outstanding_values": dict(state.outstanding),
            "combined_charged_values": charged,
            "combined_outstanding_values": outstanding,
            "sidecar_release_count": 1,
            "sidecar_single_spend_verified": True,
            "released_reservation_id": reservation[
                "h1_shared_cap_owner_v3_reservation_id"
            ],
            "released_path": path,
            "released_value": reservation["reservation_upper"],
            "native_observed_value": _typed_null("NATIVE_EFFECT_NOT_STARTED"),
            "native_effect_started": False,
            "memory_read_performed": False,
            "output_finalize_performed": False,
            "v3_v4_owner_bytes_preserved": True,
            "cleanup_arbitrary_executor_present": False,
            "cleanup_native_effect_authority_present": False,
            "output_owner_close_authority_present": False,
            "production_output_leaf_authority_present": False,
            "production_execution_authority_present": False,
            "current_access_authority_present": False,
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
        }
        return _artifact_document(
            COMBINED_DOMAIN,
            payload,
            "h1_owner_cleanup_combined_state_id",
        )
    finally:
        if cursor_fd >= 0:
            _release_storage(root_fd, sidecar_fd, lock_fd, cursor_fd)
        os.close(owner_directory_fd)
        os.close(owner_root_fd)


__all__ = (
    "ATTEMPT_CLOSURE_ISSUED",
    "CLEANUP_ARBITRARY_EXECUTOR_PRESENT",
    "CLEANUP_NATIVE_EFFECT_AUTHORITY_PRESENT",
    "CONSERVATIVE_RELEASE_WITHOUT_NATIVE_START_PRESENT",
    "ConstructionK7H1OwnerCleanupContinuationSidecarV1Error",
    "CURRENT_ACCESS_AUTHORITY_PRESENT",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "H1OwnerCleanupReleaseV1",
    "H1OwnerCleanupSidecarAllocationV1",
    "H1OwnerCleanupSidecarCrashPointV1",
    "H1OwnerCleanupSidecarHandleV1",
    "H1OwnerCleanupSidecarInjectedCrashV1",
    "H1OwnerCleanupSidecarSpecV1",
    "MEMORY_READ_AUTHORITY_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OUTPUT_FINALIZE_AUTHORITY_PRESENT",
    "OUTPUT_OWNER_CLOSE_AUTHORITY_PRESENT",
    "OWNER_CLEANUP_CONTINUATION_SIDECAR_PRESENT",
    "PROFILE_KEY",
    "PRODUCTION_EXECUTION_AUTHORITY_PRESENT",
    "PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT",
    "PROPOSED_CONTRACT_VERSION",
    "TERMINAL_CLASSIFICATION_ISSUED",
    "V3_V4_OWNER_BYTES_PRESERVED",
    "conservatively_release_h1_owner_cleanup_reservation_v1",
    "initialize_h1_owner_cleanup_continuation_sidecar_v1",
    "open_h1_owner_cleanup_continuation_sidecar_v1",
    "validate_h1_owner_cleanup_context_with_retained_lease_v1",
    "verify_h1_owner_cleanup_combined_state_v1",
)
