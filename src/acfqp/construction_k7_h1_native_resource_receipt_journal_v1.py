"""Durable construction receipts for the twelve H1 native resources.

This successor predeclares ten mount OFD slots and the WORKER/BUSINESS PIDFD
slots before normal ordinal 1.  The broker writes a durable start cell before
calling native code and a durable callback result before the normal-site event.
A start without a result is permanently unresolved and the callback is never
replayed.  The final receipt is created only after the result is bound to the
exact issuer-owned durable normal-site event.

The journal deliberately does not serialize descriptor integers.  Its opaque
capability identities and receipts are construction evidence, not kernel
credentials or cleanup/current-access authority.
"""

from __future__ import annotations

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
import threading
from types import MappingProxyType
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_k7_h1_domain_registry_extension_v6 as domains_v6
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-NATIVE-A"
PROFILE_KEY = "construction_k7_h1_native_resource_receipt_journal_v1"

NATIVE_RESOURCE_SLOT_PREDECLARATION_PRESENT = True
NATIVE_RESOURCE_RECEIPT_JOURNAL_PRESENT = True
EXACT_NATIVE_CUTOFF_SNAPSHOT_PRESENT = True
NATIVE_CALLBACK_REPLAY_AFTER_START_FORBIDDEN = True
NATIVE_CALLBACK_RESULT_BEFORE_NORMAL_EVENT_PRESENT = True
NATIVE_RECEIPT_BEFORE_NORMAL_EVENT_PRESENT = False
SAME_BROKER_INITIALIZATION_CONVERGENCE_PRESENT = True
CROSS_PROCESS_INITIALIZATION_RECOVERY_PRESENT = False
NORMAL_FAILURE_EVENT_SEMANTIC_VERIFICATION_PRESENT = False
V2_TRANSITION_INTEGRATION_PRESENT = False
REAL_KERNEL_CREDENTIAL_AUTHORITY_PRESENT = False
NATIVE_CLEANUP_AUTHORITY_PRESENT = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False

SPEC_DOMAIN = domains_v6.CONSTRUCTION_K7_H1_NATIVE_RECEIPT_SPEC_V1_DOMAIN
SLOT_DOMAIN = domains_v6.CONSTRUCTION_K7_H1_NATIVE_SLOT_DECLARATION_V1_DOMAIN
ALLOCATION_DOMAIN = domains_v6.CONSTRUCTION_K7_H1_NATIVE_RECEIPT_ALLOCATION_V1_DOMAIN
START_DOMAIN = domains_v6.CONSTRUCTION_K7_H1_NATIVE_CALLBACK_START_V1_DOMAIN
RESULT_DOMAIN = domains_v6.CONSTRUCTION_K7_H1_NATIVE_CALLBACK_RESULT_V1_DOMAIN
RECEIPT_DOMAIN = domains_v6.CONSTRUCTION_K7_H1_NATIVE_RESOURCE_RECEIPT_V1_DOMAIN
ABSENCE_DOMAIN = domains_v6.CONSTRUCTION_K7_H1_NATIVE_ABSENCE_RESOLUTION_V1_DOMAIN
CURSOR_DOMAIN = domains_v6.CONSTRUCTION_K7_H1_NATIVE_RECEIPT_CURSOR_V1_DOMAIN
CUTOFF_DOMAIN = domains_v6.CONSTRUCTION_K7_H1_NATIVE_CUTOFF_SNAPSHOT_V1_DOMAIN

_ROOT_NAME = ".acfqp-k7-h1-native-resource-receipts-v1"
_ROOT_LOCK = ".allocation.lock"
_ATTEMPT_PREFIX = "attempt-"
_ANCHOR_FILE = "root-anchor.json"
_LOCK_FILE = "journal.lock"
_CURSOR_FILE = "journal.cursor"
_ALLOCATION_FILE = "allocation.json"
_SPEC_FILE = "spec.json"
_INITIALIZATION_COMPLETE_FILE = "initialization.complete.json"
_ROOT_SEAL_PREFIX = "root-seal-"
_ALLOCATION_SEAL_PREFIX = "allocation-seal-"
_CURSOR_SEAL_PREFIX = "cursor-seal-"
_RECORD_PATTERN = re.compile(
    r"^record-(?P<sequence>[0-9]{4})-(?P<kind>[A-Z_]+)-(?P<identity>[0-9a-f]{64})\.json$"
)
_WATER_PATTERN = re.compile(
    r"^cursor-high-water-(?P<sequence>[0-9]{4})-(?P<identity>[0-9a-f]{64})$"
)

_SPEC_ISSUER = object()
_HANDLE_ISSUER = object()
_OBSERVATION_ISSUER = object()
_PENDING_ISSUER = object()
_RECEIPT_ISSUER = object()
_CUTOFF_ISSUER = object()
_ACTIVE_NATIVE_CALLBACK: ContextVar[
    tuple[str, str, str, bytes, int, int] | None
] = ContextVar(
    "acfqp_k7_h1_native_receipt_callback", default=None
)


class ConstructionK7H1NativeReceiptJournalV1Error(ValueError):
    """The native receipt journal failed closed."""


class H1NativeReceiptInjectedCrashV1(RuntimeError):
    pass


class H1NativeForkedCallbackContinuationV1(RuntimeError):
    pass


class H1NativeCapabilityKindV1(str, Enum):
    OFD = "OFD"
    PIDFD = "PIDFD"


class H1NativeResolutionKindV1(str, Enum):
    KNOWN_PRESENT = "KNOWN_PRESENT"
    KNOWN_ABSENT = "KNOWN_ABSENT"
    UNRESOLVED = "UNRESOLVED"


class H1NativeCallbackCrashPointV1(str, Enum):
    NONE = "NONE"
    AFTER_START_FSYNC = "AFTER_START_FSYNC"
    AFTER_CALLBACK_BEFORE_RESULT_FSYNC = "AFTER_CALLBACK_BEFORE_RESULT_FSYNC"


class H1NativeInitializationCrashPointV1(str, Enum):
    NONE = "NONE"
    AFTER_ATTEMPT_DIRECTORY = "AFTER_ATTEMPT_DIRECTORY"
    AFTER_CURSOR_FSYNC = "AFTER_CURSOR_FSYNC"
    AFTER_ALLOCATION_PUBLISH = "AFTER_ALLOCATION_PUBLISH"
    AFTER_SEALS_FSYNC = "AFTER_SEALS_FSYNC"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1NativeReceiptJournalV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{label} must be one nonempty exact string")
    return value


def _exact_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail(f"{label} must be one exact integer >= {minimum}")
    return value


def _content_id(domain: str, payload: Any) -> str:
    return domains_v6.extension_content_id_v6(domain, payload)


def _write_all(fd: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(fd, view)
        if written <= 0:  # pragma: no cover - OS invariant
            _fail("durable journal write made no progress")
        view = view[written:]


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _parse(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


def _publish(path: Path, raw: bytes, *, mode: int = 0o400) -> None:
    temporary = path.with_name(
        f".{path.name}.publish-{os.getpid()}-{secrets.token_hex(16)}"
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(temporary, flags, mode)
    except OSError as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error(
            f"immutable publication failed: {path.name}"
        ) from error
    try:
        _write_all(fd, raw)
        os.fsync(fd)
        os.fchmod(fd, mode)
    finally:
        os.close(fd)
    try:
        if path.exists():
            _fail(f"immutable publication target already exists: {path.name}")
        os.rename(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _read_exact_regular(path: Path, *, mutable: bool = False) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error(
            f"required journal object is absent: {path.name}"
        ) from error
    try:
        metadata = os.fstat(fd)
        expected_mode = 0o600 if mutable else 0o400
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != expected_mode:
            _fail(f"journal object mode or type changed: {path.name}")
        chunks: list[bytes] = []
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            chunks.append(block)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _slot_payload(index: int, ordinal: int, site_key: str, role: str, kind: str) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.k7_h1_native_resource_slot_declaration.v1",
        "schema_version": SCHEMA_VERSION,
        "slot_index": index,
        "slot_key": f"native-slot:{index:02d}:{site_key}",
        "normal_ordinal": ordinal,
        "normal_site_key": site_key,
        "broker_role": "BROKER",
        "resource_role": role,
        "capability_kind": kind,
        "predeclared_before_normal_ordinal_1": True,
        "raw_descriptor_is_authority": False,
    }
    return {
        **payload,
        "h1_native_resource_slot_id": _content_id(SLOT_DOMAIN, payload),
    }


_MOUNT_ROWS = (
    (7, "mount-open:WORKER:sealed_runtime_archive", "WORKER"),
    (9, "mount-open:WORKER:ipc_binding_candidate", "WORKER"),
    (11, "mount-open:WORKER:execution_topology_profile", "WORKER"),
    (13, "mount-open:BUSINESS:sealed_runtime_archive", "BUSINESS"),
    (15, "mount-open:BUSINESS:business_request_candidate", "BUSINESS"),
    (17, "mount-open:BUSINESS:owned_engine_source", "BUSINESS"),
    (19, "mount-open:BUSINESS:owned_engine_authority_document", "BUSINESS"),
    (21, "mount-open:BUSINESS:kernel_replay_document", "BUSINESS"),
    (23, "mount-open:BUSINESS:query_replay_document", "BUSINESS"),
    (25, "mount-open:BUSINESS:fallback_cap_profile", "BUSINESS"),
)
_LAUNCH_ROWS = (
    (26, "launch:WORKER", "WORKER"),
    (30, "launch:BUSINESS", "BUSINESS"),
)
PREDECLARED_NATIVE_RESOURCE_SLOTS_V1 = tuple(
    MappingProxyType(
        _slot_payload(index, ordinal, site, role, H1NativeCapabilityKindV1.OFD.value)
    )
    for index, (ordinal, site, role) in enumerate(_MOUNT_ROWS, start=1)
) + tuple(
    MappingProxyType(
        _slot_payload(index, ordinal, site, role, H1NativeCapabilityKindV1.PIDFD.value)
    )
    for index, (ordinal, site, role) in enumerate(_LAUNCH_ROWS, start=11)
)
if (
    len(PREDECLARED_NATIVE_RESOURCE_SLOTS_V1) != 12
    or sum(row["capability_kind"] == "OFD" for row in PREDECLARED_NATIVE_RESOURCE_SLOTS_V1) != 10
    or sum(row["capability_kind"] == "PIDFD" for row in PREDECLARED_NATIVE_RESOURCE_SLOTS_V1) != 2
    or len({row["slot_key"] for row in PREDECLARED_NATIVE_RESOURCE_SLOTS_V1}) != 12
):  # pragma: no cover - import-time invariant
    raise RuntimeError("the H1 native resource slot registry is not exactly 10 OFD + 2 PIDFD")
_SLOTS_BY_KEY: Mapping[str, Mapping[str, Any]] = MappingProxyType(
    {row["slot_key"]: row for row in PREDECLARED_NATIVE_RESOURCE_SLOTS_V1}
)


@dataclass(frozen=True, slots=True)
class H1NativeReceiptJournalSpecV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SPEC_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("native receipt spec is caller-minted")
        payload = _parse(self.payload_bytes, "native receipt spec")
        object.__setattr__(self, "_spec_id", _content_id(SPEC_DOMAIN, payload))

    @property
    def spec_id(self) -> str:
        return self._spec_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse(self.payload_bytes, "native receipt spec")

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes({**self.payload, "h1_native_receipt_journal_spec_id": self.spec_id})


@dataclass(frozen=True, slots=True)
class H1NativeReceiptJournalHandleV1:
    _issuer: InitVar[object]
    spec: H1NativeReceiptJournalSpecV1
    normal_handle: normal_v1.H1NormalPrefixHandleV1
    allocation_id: str
    root: Path
    attempt_directory: Path
    broker_process_id: int
    broker_thread_id: int
    root_device: int
    root_inode: int
    attempt_device: int
    attempt_inode: int
    anchor_device: int
    anchor_inode: int
    lock_device: int
    lock_inode: int
    allocation_device: int
    allocation_inode: int
    cursor_device: int
    cursor_inode: int

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _HANDLE_ISSUER
            or type(self.spec) is not H1NativeReceiptJournalSpecV1
            or type(self.normal_handle) is not normal_v1.H1NormalPrefixHandleV1
            or self.spec.payload["h1_normal_prefix_spec_id"]
            != self.normal_handle.spec.spec_id
            or self.spec.payload["h1_normal_prefix_allocation_id"]
            != self.normal_handle.allocation_id
        ):
            _fail("native receipt handle is caller-minted")
        _cid(self.allocation_id, "native receipt allocation")

    def __reduce__(self) -> NoReturn:
        _fail("native receipt handle is not serializable")


def _declared_slots_for_handle(
    handle: H1NativeReceiptJournalHandleV1,
) -> tuple[Mapping[str, Any], ...]:
    """Return the slot registry sealed into this handle's content-addressed spec.

    Runtime issuance and replay deliberately do not consult the exported module
    registry.  The latter is only the immutable construction template used by
    ``freeze_h1_native_receipt_journal_spec_v1``; the spec bytes are the
    attempt-local authority after freezing.
    """

    rows = handle.spec.payload.get("predeclared_slots")
    if type(rows) is not list or len(rows) != 12:
        _fail("sealed native receipt spec lost its exact twelve slot declarations")
    slots: list[Mapping[str, Any]] = []
    keys: set[str] = set()
    ordinals: list[int] = []
    ofd_count = 0
    pidfd_count = 0
    for row in rows:
        if type(row) is not dict:
            _fail("sealed native receipt slot declaration changed type")
        payload = dict(row)
        claimed = _cid(
            payload.pop("h1_native_resource_slot_id", None),
            "native resource slot",
        )
        if claimed != _content_id(SLOT_DOMAIN, payload):
            _fail("sealed native receipt slot declaration identity changed")
        key = _nonempty(row.get("slot_key"), "native resource slot key")
        ordinal = _exact_int(
            row.get("normal_ordinal"), "native resource slot ordinal", minimum=1
        )
        if key in keys:
            _fail("sealed native receipt spec duplicated a slot key")
        keys.add(key)
        ordinals.append(ordinal)
        ofd_count += row.get("capability_kind") == H1NativeCapabilityKindV1.OFD.value
        pidfd_count += row.get("capability_kind") == H1NativeCapabilityKindV1.PIDFD.value
        slots.append(MappingProxyType(dict(row)))
    if (
        tuple(ordinals) != (7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 26, 30)
        or ofd_count != 10
        or pidfd_count != 2
    ):
        _fail("sealed native receipt spec changed the exact slot registry")
    return tuple(slots)


def _declared_slots_by_key_for_handle(
    handle: H1NativeReceiptJournalHandleV1,
) -> Mapping[str, Mapping[str, Any]]:
    return MappingProxyType(
        {row["slot_key"]: row for row in _declared_slots_for_handle(handle)}
    )


@dataclass(frozen=True, slots=True)
class H1NativeCallbackObservationV1:
    _issuer: InitVar[object]
    resolution_kind: H1NativeResolutionKindV1
    capability_kind: H1NativeCapabilityKindV1
    absence_reason: str | None
    _raw_descriptor: int | None = field(repr=False)
    _allocation_id: str = field(repr=False)
    _slot_key: str = field(repr=False)
    _start_id: str = field(repr=False)
    _callback_nonce: bytes = field(repr=False)
    _creating_process_id: int = field(repr=False)
    _creating_thread_id: int = field(repr=False)
    _consumed: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _OBSERVATION_ISSUER
            or type(self._callback_nonce) is not bytes
            or len(self._callback_nonce) != 32
        ):
            _fail("native callback observation is caller-minted")


@dataclass(frozen=True, slots=True)
class H1PendingNativeCallbackResultV1:
    _issuer: InitVar[object]
    document_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PENDING_ISSUER or type(self.document_bytes) is not bytes:
            _fail("pending native result is caller-minted")

    @property
    def document(self) -> dict[str, Any]:
        return _parse(self.document_bytes, "pending native callback result")

    @property
    def result_id(self) -> str:
        return _cid(self.document["h1_native_callback_result_id"], "native callback result")


@dataclass(frozen=True, slots=True)
class H1NativeResourceReceiptV1:
    _issuer: InitVar[object]
    document_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RECEIPT_ISSUER or type(self.document_bytes) is not bytes:
            _fail("native resource receipt is caller-minted")

    @property
    def document(self) -> dict[str, Any]:
        return _parse(self.document_bytes, "native resource receipt")

    @property
    def receipt_id(self) -> str:
        return _cid(self.document["h1_native_resource_receipt_id"], "native resource receipt")


@dataclass(frozen=True, slots=True)
class H1NativeCutoffSnapshotV1:
    _issuer: InitVar[object]
    document_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CUTOFF_ISSUER or type(self.document_bytes) is not bytes:
            _fail("native cutoff snapshot is caller-minted")

    @property
    def document(self) -> dict[str, Any]:
        return _parse(self.document_bytes, "native cutoff snapshot")

    @property
    def snapshot_id(self) -> str:
        return _cid(self.document["h1_native_cutoff_snapshot_id"], "native cutoff snapshot")


def _freeze_h1_native_receipt_journal_spec_under_normal_lock(
    receipt_base_directory: str | Path,
    *,
    normal_handle: normal_v1.H1NormalPrefixHandleV1,
    normal_state: Any,
) -> H1NativeReceiptJournalSpecV1:
    if type(normal_handle) is not normal_v1.H1NormalPrefixHandleV1:
        _fail("native receipt predeclaration requires one exact normal-prefix handle")
    base = Path(receipt_base_directory).resolve(strict=True)
    if not base.is_dir():
        _fail("native receipt base is not a directory")
    snapshot = normal_v1._snapshot_from_state(normal_handle, normal_state)
    current = snapshot.document
    if (
        current["completed_event_count"] != 0
        or current["next_ordinal"] != 1
        or current["status"] != normal_v1.H1NormalPrefixStatusV1.READY.value
        or current["dangling_intent_id"] != _typed_null("NO_DANGLING_INTENT")
    ):
        _fail("all twelve native slots must be predeclared before normal ordinal 1")
    normal_payload = normal_handle.spec.payload
    payload = {
        "schema": "acfqp.k7_h1_native_receipt_journal_spec.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_id": normal_payload["logical_occurrence_id"],
        "route_attempt_id": normal_payload["route_attempt_id"],
        "decision_point_id": normal_payload["decision_point_id"],
        "transaction_id": normal_payload["transaction_id"],
        "h1_normal_prefix_spec_id": normal_handle.spec.spec_id,
        "h1_normal_prefix_allocation_id": normal_handle.allocation_id,
        "h1_normal_prefix_genesis_snapshot_id": snapshot.snapshot_id,
        "h1_anchored_lifecycle_program_id": normal_payload["h1_anchored_lifecycle_program_id"],
        "h1_anchored_lifecycle_handler_registry_id": normal_payload["h1_anchored_lifecycle_handler_registry_id"],
        "receipt_base_realpath": str(base),
        "receipt_base_device": base.stat().st_dev,
        "receipt_base_inode": base.stat().st_ino,
        "broker_role": "BROKER",
        "slot_count": 12,
        "ofd_slot_count": 10,
        "pidfd_slot_count": 2,
        "predeclared_slots": [dict(row) for row in PREDECLARED_NATIVE_RESOURCE_SLOTS_V1],
        "predeclared_before_normal_ordinal_1": True,
        "native_callback_replay_after_start_forbidden": True,
        "native_callback_result_before_normal_event_present": True,
        "native_receipt_before_normal_event_present": False,
        "native_receipt_created_after_exact_event_binding": True,
        "same_broker_initialization_convergence_present": True,
        "cross_process_initialization_recovery_present": False,
        "raw_descriptor_fields_serialized": False,
        "opaque_identity_is_kernel_credential": False,
        "real_kernel_credential_authority_present": False,
        "native_cleanup_authority_present": False,
        "current_access_authority_present": False,
        "production_execution_authority_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    return H1NativeReceiptJournalSpecV1(_SPEC_ISSUER, canonical_json_bytes(payload))


def freeze_h1_native_receipt_journal_spec_v1(
    receipt_base_directory: str | Path,
    *,
    normal_handle: normal_v1.H1NormalPrefixHandleV1,
) -> H1NativeReceiptJournalSpecV1:
    if normal_v1._ACTIVE_EXECUTIONS.get():
        _fail("native receipt predeclaration cannot nest inside a normal lease")
    root_fd, journal_fd, lock_fd, cursor_fd, state = normal_v1._require_journal_locked(
        normal_handle
    )
    try:
        return _freeze_h1_native_receipt_journal_spec_under_normal_lock(
            receipt_base_directory,
            normal_handle=normal_handle,
            normal_state=state,
        )
    finally:
        normal_v1._release_journal_locked(
            root_fd, journal_fd, lock_fd, cursor_fd
        )


def _cursor_payload(sequence: int, previous_id: str | dict[str, str], record_kind: str, record_id: str | dict[str, str]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.k7_h1_native_receipt_cursor.v1",
        "schema_version": SCHEMA_VERSION,
        "sequence": sequence,
        "previous_h1_native_receipt_cursor_id": previous_id,
        "record_kind": record_kind,
        "record_id": record_id,
    }
    return {**payload, "h1_native_receipt_cursor_id": _content_id(CURSOR_DOMAIN, payload)}


def _cursor_genesis(spec_id: str) -> dict[str, Any]:
    return _cursor_payload(0, _typed_null("CURSOR_GENESIS"), "GENESIS", spec_id)


def _allocation_payload(spec: H1NativeReceiptJournalSpecV1, root: Path, attempt: Path, anchor: os.stat_result, lock: os.stat_result, cursor: os.stat_result, broker_pid: int, broker_tid: int) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.k7_h1_native_receipt_allocation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_native_receipt_journal_spec_id": spec.spec_id,
        "route_attempt_id": spec.payload["route_attempt_id"],
        "receipt_root_realpath": str(root.resolve(strict=True)),
        "receipt_root_device": root.stat().st_dev,
        "receipt_root_inode": root.stat().st_ino,
        "attempt_directory_realpath": str(attempt.resolve(strict=True)),
        "attempt_directory_device": attempt.stat().st_dev,
        "attempt_directory_inode": attempt.stat().st_ino,
        "root_anchor_device": anchor.st_dev,
        "root_anchor_inode": anchor.st_ino,
        "root_anchor_sha256": hashlib.sha256(
            _read_exact_regular(attempt / _ANCHOR_FILE)
        ).hexdigest(),
        "journal_lock_device": lock.st_dev,
        "journal_lock_inode": lock.st_ino,
        "journal_cursor_device": cursor.st_dev,
        "journal_cursor_inode": cursor.st_ino,
        "broker_process_id": broker_pid,
        "broker_thread_id": broker_tid,
        "slot_count": 12,
        "root_anchor_hardlink_seal_required": True,
        "allocation_hardlink_seal_required": True,
        "cursor_hardlink_seal_required": True,
        "single_broker_process_thread_issuer": True,
        "official_execution_allowed": False,
    }
    return {**payload, "h1_native_receipt_allocation_id": _content_id(ALLOCATION_DOMAIN, payload)}


def _initialization_complete_payload(
    spec: H1NativeReceiptJournalSpecV1, allocation_id: str
) -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_native_receipt_initialization_complete.v1",
        "schema_version": SCHEMA_VERSION,
        "h1_native_receipt_journal_spec_id": spec.spec_id,
        "h1_native_receipt_allocation_id": allocation_id,
        "route_attempt_id": spec.payload["route_attempt_id"],
        "initialization_atomically_converged": True,
        "convergence_scope": "SAME_BROKER_PROCESS_AND_THREAD_ONLY",
        "cross_process_initialization_recovery_present": False,
    }


def _attempt_name(route_attempt_id: str) -> str:
    return _ATTEMPT_PREFIX + _cid(route_attempt_id, "route attempt")


def _handle_from_existing(
    spec: H1NativeReceiptJournalSpecV1,
    normal_handle: normal_v1.H1NormalPrefixHandleV1,
    root: Path,
    attempt: Path,
) -> H1NativeReceiptJournalHandleV1:
    if _read_exact_regular(attempt / _SPEC_FILE) != spec.canonical_bytes:
        _fail("existing native receipt allocation crossed its spec")
    allocation_document = _parse(
        _read_exact_regular(attempt / _ALLOCATION_FILE),
        "native receipt allocation",
    )
    payload = dict(allocation_document)
    claimed = _cid(
        payload.pop("h1_native_receipt_allocation_id", None),
        "native receipt allocation",
    )
    broker_pid = payload.get("broker_process_id")
    broker_tid = payload.get("broker_thread_id")
    if type(broker_pid) is not int or broker_pid <= 0 or type(broker_tid) is not int or broker_tid <= 0:
        _fail("existing native receipt allocation issuer changed")
    if broker_pid != os.getpid() or broker_tid != threading.get_ident():
        raise H1NativeForkedCallbackContinuationV1(
            "native receipt allocation cannot be recovered by another process or thread"
        )
    expected_allocation = _allocation_payload(
        spec,
        root,
        attempt,
        (attempt / _ANCHOR_FILE).stat(),
        (attempt / _LOCK_FILE).stat(),
        (attempt / _CURSOR_FILE).stat(),
        broker_pid,
        broker_tid,
    )
    if allocation_document != expected_allocation or claimed != expected_allocation["h1_native_receipt_allocation_id"]:
        _fail("existing native receipt allocation identity changed")
    complete = _parse(
        _read_exact_regular(attempt / _INITIALIZATION_COMPLETE_FILE),
        "native receipt initialization completion",
    )
    if complete != _initialization_complete_payload(spec, claimed):
        _fail("native receipt initialization completion changed")
    handle = H1NativeReceiptJournalHandleV1(
        _HANDLE_ISSUER,
        spec,
        normal_handle,
        claimed,
        root,
        attempt,
        broker_pid,
        broker_tid,
        payload["receipt_root_device"],
        payload["receipt_root_inode"],
        payload["attempt_directory_device"],
        payload["attempt_directory_inode"],
        payload["root_anchor_device"],
        payload["root_anchor_inode"],
        payload["journal_lock_device"],
        payload["journal_lock_inode"],
        (attempt / _ALLOCATION_FILE).stat().st_dev,
        (attempt / _ALLOCATION_FILE).stat().st_ino,
        payload["journal_cursor_device"],
        payload["journal_cursor_inode"],
    )
    _require_physical_identity(handle)
    return handle


def _ensure_exact_file(path: Path, raw: bytes, *, mode: int) -> None:
    if path.exists():
        if _read_exact_regular(path, mutable=mode == 0o600) != raw:
            _fail(f"incomplete native receipt initialization crossed {path.name}")
        return
    _publish(path, raw, mode=mode)


def _ensure_initialization_link(primary: Path, seal: Path) -> None:
    primary_metadata = primary.stat(follow_symlinks=False)
    if seal.exists():
        seal_metadata = seal.stat(follow_symlinks=False)
        if (seal_metadata.st_dev, seal_metadata.st_ino) != (
            primary_metadata.st_dev,
            primary_metadata.st_ino,
        ):
            _fail("incomplete native receipt initialization crossed a seal")
        return
    os.link(primary, seal, follow_symlinks=False)


def _complete_attempt_initialization(
    spec: H1NativeReceiptJournalSpecV1,
    root: Path,
    attempt: Path,
    *,
    crash: H1NativeInitializationCrashPointV1,
) -> None:
    metadata = attempt.stat(follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o700:
        _fail("native receipt initialization attempt directory changed")
    allocation_path = attempt / _ALLOCATION_FILE
    if allocation_path.exists():
        existing_allocation = _parse(
            _read_exact_regular(allocation_path), "native receipt allocation"
        )
        broker_pid = existing_allocation.get("broker_process_id")
        broker_tid = existing_allocation.get("broker_thread_id")
        if broker_pid != os.getpid() or broker_tid != threading.get_ident():
            raise H1NativeForkedCallbackContinuationV1(
                "native receipt initialization cannot write recovery state for another process or thread"
            )
    _ensure_exact_file(attempt / _SPEC_FILE, spec.canonical_bytes, mode=0o400)
    anchor_path = attempt / _ANCHOR_FILE
    if not anchor_path.exists():
        anchor_payload = {
            "schema": "acfqp.k7_h1_native_receipt_root_anchor.v1",
            "h1_native_receipt_journal_spec_id": spec.spec_id,
            "route_attempt_id": spec.payload["route_attempt_id"],
            "nonce": secrets.token_hex(32),
            "construction_evidence_only": True,
        }
        _publish(anchor_path, canonical_json_bytes(anchor_payload))
    else:
        anchor = _parse(_read_exact_regular(anchor_path), "native receipt root anchor")
        if (
            set(anchor)
            != {
                "schema",
                "h1_native_receipt_journal_spec_id",
                "route_attempt_id",
                "nonce",
                "construction_evidence_only",
            }
            or anchor["schema"] != "acfqp.k7_h1_native_receipt_root_anchor.v1"
            or anchor["h1_native_receipt_journal_spec_id"] != spec.spec_id
            or anchor["route_attempt_id"] != spec.payload["route_attempt_id"]
            or type(anchor["nonce"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", anchor["nonce"]) is None
            or anchor["construction_evidence_only"] is not True
        ):
            _fail("incomplete native receipt initialization crossed its anchor")
    lock_path = attempt / _LOCK_FILE
    _ensure_exact_file(lock_path, b"", mode=0o600)
    genesis = _cursor_genesis(spec.spec_id)
    cursor_path = attempt / _CURSOR_FILE
    _ensure_exact_file(
        cursor_path, canonical_json_bytes(genesis) + b"\n", mode=0o600
    )
    high_water = attempt / (
        f"cursor-high-water-0000-{genesis['h1_native_receipt_cursor_id']}"
    )
    _ensure_exact_file(high_water, b"", mode=0o400)
    if crash is H1NativeInitializationCrashPointV1.AFTER_CURSOR_FSYNC:
        raise H1NativeReceiptInjectedCrashV1(
            "injected crash after native receipt cursor initialization"
        )
    if not allocation_path.exists():
        allocation = _allocation_payload(
            spec,
            root,
            attempt,
            anchor_path.stat(),
            lock_path.stat(),
            cursor_path.stat(),
            os.getpid(),
            threading.get_ident(),
        )
        _publish(allocation_path, canonical_json_bytes(allocation))
    else:
        allocation = _parse(
            _read_exact_regular(allocation_path), "native receipt allocation"
        )
        payload = dict(allocation)
        claimed = _cid(
            payload.pop("h1_native_receipt_allocation_id", None),
            "native receipt allocation",
        )
        broker_pid = payload.get("broker_process_id")
        broker_tid = payload.get("broker_thread_id")
        if (
            type(broker_pid) is not int
            or broker_pid <= 0
            or type(broker_tid) is not int
            or broker_tid <= 0
        ):
            _fail("incomplete native receipt allocation issuer changed")
        expected = _allocation_payload(
            spec,
            root,
            attempt,
            anchor_path.stat(),
            lock_path.stat(),
            cursor_path.stat(),
            broker_pid,
            broker_tid,
        )
        if allocation != expected or claimed != expected["h1_native_receipt_allocation_id"]:
            _fail("incomplete native receipt allocation changed")
    if crash is H1NativeInitializationCrashPointV1.AFTER_ALLOCATION_PUBLISH:
        raise H1NativeReceiptInjectedCrashV1(
            "injected crash after native receipt allocation publication"
        )
    route = spec.payload["route_attempt_id"]
    _ensure_initialization_link(anchor_path, root / f"{_ROOT_SEAL_PREFIX}{route}")
    _ensure_initialization_link(
        allocation_path, root / f"{_ALLOCATION_SEAL_PREFIX}{route}"
    )
    _ensure_initialization_link(cursor_path, root / f"{_CURSOR_SEAL_PREFIX}{route}")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(root_fd)
    finally:
        os.close(root_fd)
    if crash is H1NativeInitializationCrashPointV1.AFTER_SEALS_FSYNC:
        raise H1NativeReceiptInjectedCrashV1(
            "injected crash after native receipt seal publication"
        )
    allocation_id = allocation["h1_native_receipt_allocation_id"]
    _ensure_exact_file(
        attempt / _INITIALIZATION_COMPLETE_FILE,
        canonical_json_bytes(_initialization_complete_payload(spec, allocation_id)),
        mode=0o400,
    )


def _initialize_h1_native_receipt_journal_under_normal_lock(
    spec: H1NativeReceiptJournalSpecV1,
    *,
    normal_handle: normal_v1.H1NormalPrefixHandleV1,
    normal_state: Any,
    crash_point: H1NativeInitializationCrashPointV1 | str = H1NativeInitializationCrashPointV1.NONE,
) -> H1NativeReceiptJournalHandleV1:
    if type(spec) is not H1NativeReceiptJournalSpecV1 or type(normal_handle) is not normal_v1.H1NormalPrefixHandleV1:
        _fail("native receipt initialization crossed its spec or normal handle")
    if spec.payload["h1_normal_prefix_spec_id"] != normal_handle.spec.spec_id or spec.payload["h1_normal_prefix_allocation_id"] != normal_handle.allocation_id:
        _fail("native receipt initialization crossed the normal allocation")
    try:
        crash = H1NativeInitializationCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error(
            "native receipt initialization crash point is invalid"
        ) from error
    snapshot = normal_v1._snapshot_from_state(normal_handle, normal_state)
    if snapshot.snapshot_id != spec.payload["h1_normal_prefix_genesis_snapshot_id"] or snapshot.document["completed_event_count"] != 0:
        _fail("native receipt allocation was not created before ordinal 1")
    base = Path(spec.payload["receipt_base_realpath"])
    metadata = base.stat()
    if metadata.st_dev != spec.payload["receipt_base_device"] or metadata.st_ino != spec.payload["receipt_base_inode"]:
        _fail("native receipt base identity changed")
    root = base / _ROOT_NAME
    try:
        os.mkdir(root, mode=0o700)
    except FileExistsError:
        pass
    root_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        root_flags |= os.O_NOFOLLOW
    try:
        root_directory_fd = os.open(root, root_flags)
    except OSError as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error(
            "native receipt root is not one exact directory"
        ) from error
    try:
        root_metadata = os.fstat(root_directory_fd)
        if not stat.S_ISDIR(root_metadata.st_mode):
            _fail("native receipt root is not one exact directory")
        os.fchmod(root_directory_fd, 0o700)
    finally:
        os.close(root_directory_fd)
    root_lock = root / _ROOT_LOCK
    lock_flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        lock_flags |= os.O_NOFOLLOW
    root_lock_fd = os.open(root_lock, lock_flags, 0o600)
    try:
        os.fchmod(root_lock_fd, 0o600)
        fcntl.flock(root_lock_fd, fcntl.LOCK_EX)
        attempt = root / _attempt_name(spec.payload["route_attempt_id"])
        newly_created = not attempt.exists()
        if newly_created:
            attempt.mkdir(mode=0o700)
            if crash is H1NativeInitializationCrashPointV1.AFTER_ATTEMPT_DIRECTORY:
                raise H1NativeReceiptInjectedCrashV1(
                    "injected crash after native receipt attempt directory"
                )
        complete_path = attempt / _INITIALIZATION_COMPLETE_FILE
        if not complete_path.exists():
            _complete_attempt_initialization(spec, root, attempt, crash=crash)
        return _handle_from_existing(spec, normal_handle, root, attempt)
    finally:
        fcntl.flock(root_lock_fd, fcntl.LOCK_UN)
        os.close(root_lock_fd)


def initialize_h1_native_receipt_journal_v1(
    spec: H1NativeReceiptJournalSpecV1,
    *,
    normal_handle: normal_v1.H1NormalPrefixHandleV1,
    crash_point: H1NativeInitializationCrashPointV1 | str = H1NativeInitializationCrashPointV1.NONE,
) -> H1NativeReceiptJournalHandleV1:
    if normal_v1._ACTIVE_EXECUTIONS.get():
        _fail("native receipt initialization cannot nest inside a normal lease")
    root_fd, journal_fd, lock_fd, cursor_fd, state = normal_v1._require_journal_locked(
        normal_handle
    )
    try:
        return _initialize_h1_native_receipt_journal_under_normal_lock(
            spec,
            normal_handle=normal_handle,
            normal_state=state,
            crash_point=crash_point,
        )
    finally:
        normal_v1._release_journal_locked(
            root_fd, journal_fd, lock_fd, cursor_fd
        )


def open_h1_native_receipt_journal_v1(
    spec: H1NativeReceiptJournalSpecV1,
    *,
    normal_handle: normal_v1.H1NormalPrefixHandleV1,
) -> H1NativeReceiptJournalHandleV1:
    if (
        type(spec) is not H1NativeReceiptJournalSpecV1
        or type(normal_handle) is not normal_v1.H1NormalPrefixHandleV1
    ):
        _fail("native receipt open requires one exact spec")
    if (
        spec.payload["h1_normal_prefix_spec_id"] != normal_handle.spec.spec_id
        or spec.payload["h1_normal_prefix_allocation_id"]
        != normal_handle.allocation_id
    ):
        _fail("native receipt open crossed the normal allocation")
    base = Path(spec.payload["receipt_base_realpath"])
    root = base / _ROOT_NAME
    attempt = root / _attempt_name(spec.payload["route_attempt_id"])
    return _handle_from_existing(spec, normal_handle, root, attempt)


def _require_broker(handle: H1NativeReceiptJournalHandleV1) -> None:
    if type(handle) is not H1NativeReceiptJournalHandleV1:
        _fail("native receipt mutation requires one exact handle")
    if os.getpid() != handle.broker_process_id:
        raise H1NativeForkedCallbackContinuationV1("forked process cannot issue broker receipts")
    if threading.get_ident() != handle.broker_thread_id:
        _fail("foreign thread cannot issue broker receipts")


def _require_physical_identity(handle: H1NativeReceiptJournalHandleV1) -> None:
    try:
        root = handle.root.stat()
        attempt = handle.attempt_directory.stat()
    except OSError as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error(
            "native receipt root identity is unavailable"
        ) from error
    if (root.st_dev, root.st_ino) != (handle.root_device, handle.root_inode) or (attempt.st_dev, attempt.st_ino) != (handle.attempt_device, handle.attempt_inode):
        _fail("native receipt root identity changed")
    try:
        lock = (handle.attempt_directory / _LOCK_FILE).stat(follow_symlinks=False)
    except OSError as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error(
            "native receipt journal lock identity is unavailable"
        ) from error
    if (
        not stat.S_ISREG(lock.st_mode)
        or stat.S_IMODE(lock.st_mode) != 0o600
        or lock.st_nlink != 1
        or (lock.st_dev, lock.st_ino) != (handle.lock_device, handle.lock_inode)
    ):
        _fail("native receipt journal lock identity changed")
    pairs = (
        (
            handle.attempt_directory / _ANCHOR_FILE,
            handle.root / f"{_ROOT_SEAL_PREFIX}{handle.spec.payload['route_attempt_id']}",
            handle.anchor_device,
            handle.anchor_inode,
            False,
        ),
        (
            handle.attempt_directory / _ALLOCATION_FILE,
            handle.root / f"{_ALLOCATION_SEAL_PREFIX}{handle.spec.payload['route_attempt_id']}",
            handle.allocation_device,
            handle.allocation_inode,
            False,
        ),
        (
            handle.attempt_directory / _CURSOR_FILE,
            handle.root / f"{_CURSOR_SEAL_PREFIX}{handle.spec.payload['route_attempt_id']}",
            handle.cursor_device,
            handle.cursor_inode,
            True,
        ),
    )
    for primary, seal, device, inode, mutable in pairs:
        try:
            left = primary.stat(follow_symlinks=False)
            right = seal.stat(follow_symlinks=False)
        except OSError as error:
            raise ConstructionK7H1NativeReceiptJournalV1Error(
                "native receipt allocation/cursor/root seal changed"
            ) from error
        expected_mode = 0o600 if mutable else 0o400
        if (
            not stat.S_ISREG(left.st_mode)
            or not stat.S_ISREG(right.st_mode)
            or stat.S_IMODE(left.st_mode) != expected_mode
            or (left.st_dev, left.st_ino) != (device, inode)
            or (right.st_dev, right.st_ino) != (device, inode)
            or left.st_nlink != 2
            or right.st_nlink != 2
        ):
            _fail("native receipt allocation/cursor/root seal changed")
    anchor = _parse(
        _read_exact_regular(handle.attempt_directory / _ANCHOR_FILE),
        "native receipt root anchor",
    )
    if (
        set(anchor)
        != {
            "schema",
            "h1_native_receipt_journal_spec_id",
            "route_attempt_id",
            "nonce",
            "construction_evidence_only",
        }
        or anchor["schema"] != "acfqp.k7_h1_native_receipt_root_anchor.v1"
        or anchor["h1_native_receipt_journal_spec_id"] != handle.spec.spec_id
        or anchor["route_attempt_id"] != handle.spec.payload["route_attempt_id"]
        or type(anchor["nonce"]) is not str
        or re.fullmatch(r"[0-9a-f]{64}", anchor["nonce"]) is None
        or anchor["construction_evidence_only"] is not True
    ):
        _fail("native receipt root anchor content changed")
    allocation_document = _parse(_read_exact_regular(handle.attempt_directory / _ALLOCATION_FILE), "native receipt allocation")
    allocation = dict(allocation_document)
    claimed = _cid(allocation.pop("h1_native_receipt_allocation_id", None), "native receipt allocation")
    expected = _allocation_payload(
        handle.spec,
        handle.root,
        handle.attempt_directory,
        (handle.attempt_directory / _ANCHOR_FILE).stat(),
        lock,
        (handle.attempt_directory / _CURSOR_FILE).stat(),
        handle.broker_process_id,
        handle.broker_thread_id,
    )
    if claimed != handle.allocation_id or allocation_document != expected:
        _fail("native receipt allocation identity changed")
    if _read_exact_regular(handle.attempt_directory / _SPEC_FILE) != handle.spec.canonical_bytes:
        _fail("native receipt spec bytes changed")
    complete = _parse(
        _read_exact_regular(handle.attempt_directory / _INITIALIZATION_COMPLETE_FILE),
        "native receipt initialization completion",
    )
    if complete != _initialization_complete_payload(handle.spec, handle.allocation_id):
        _fail("native receipt initialization completion changed")


def _record_identity(document: Mapping[str, Any]) -> tuple[str, str, str]:
    schema = document.get("schema")
    table = {
        "acfqp.k7_h1_native_callback_start.v1": ("START", START_DOMAIN, "h1_native_callback_start_id"),
        "acfqp.k7_h1_native_callback_result.v1": ("CALLBACK_RESULT", RESULT_DOMAIN, "h1_native_callback_result_id"),
        "acfqp.k7_h1_native_resource_receipt.v1": ("KNOWN_PRESENT", RECEIPT_DOMAIN, "h1_native_resource_receipt_id"),
        "acfqp.k7_h1_native_absence_resolution.v1": ("KNOWN_ABSENT", ABSENCE_DOMAIN, "h1_native_absence_resolution_id"),
        "acfqp.k7_h1_native_cutoff_snapshot.v1": ("CUTOFF", CUTOFF_DOMAIN, "h1_native_cutoff_snapshot_id"),
    }
    if schema not in table:
        _fail("native receipt record schema is unregistered")
    kind, domain, key = table[schema]
    payload = dict(document)
    claimed = _cid(payload.pop(key, None), "native receipt record")
    if _content_id(domain, payload) != claimed:
        _fail("native receipt record content identity changed")
    return kind, key, claimed


@dataclass(slots=True)
class _State:
    records: list[dict[str, Any]]
    starts: dict[str, dict[str, Any]]
    results: dict[str, dict[str, Any]]
    resolutions: dict[str, dict[str, Any]]
    cutoff: dict[str, Any] | None
    cursor_rows: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class _NormalEvidence:
    intents_by_id: Mapping[str, Mapping[str, Any]]
    events_by_id: Mapping[str, Mapping[str, Any]]
    dangling_intent: Mapping[str, Any] | None
    completed_event_count: int
    failed: bool


def _load_normal_evidence(
    handle: H1NativeReceiptJournalHandleV1,
) -> _NormalEvidence:
    if normal_v1._ACTIVE_EXECUTIONS.get():
        _fail(
            "native receipt journal cannot nest inside a normal lease while V2 integration is false"
        )
    root_fd, journal_fd, lock_fd, cursor_fd, state = normal_v1._require_journal_locked(
        handle.normal_handle
    )
    try:
        return _normal_evidence_from_state(state)
    finally:
        normal_v1._release_journal_locked(
            root_fd, journal_fd, lock_fd, cursor_fd
        )


def _normal_evidence_from_state(state: Any) -> _NormalEvidence:
    intents = {
        row["h1_normal_site_intent_id"]: dict(row) for row in state.intents
    }
    events = {
        row["h1_normal_site_event_commit_id"]: dict(row) for row in state.events
    }
    dangling = dict(state.dangling_intent) if state.dangling_intent is not None else None
    return _NormalEvidence(
        intents,
        events,
        dangling,
        len(state.events),
        state.failed,
    )


def _require_exact_keys(
    document: Mapping[str, Any], expected: set[str], label: str
) -> None:
    if set(document) != expected:
        _fail(f"{label} fields changed")


def _require_record_context(
    handle: H1NativeReceiptJournalHandleV1,
    document: Mapping[str, Any],
    slot: Mapping[str, Any],
) -> None:
    expected = {
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_native_receipt_journal_spec_id": handle.spec.spec_id,
        "h1_native_receipt_allocation_id": handle.allocation_id,
        "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
        "route_attempt_id": handle.spec.payload["route_attempt_id"],
        "decision_point_id": handle.spec.payload["decision_point_id"],
        "transaction_id": handle.spec.payload["transaction_id"],
        "slot_key": slot["slot_key"],
        "h1_native_resource_slot_id": slot["h1_native_resource_slot_id"],
        "normal_ordinal": slot["normal_ordinal"],
        "normal_site_key": slot["normal_site_key"],
        "broker_role": "BROKER",
        "resource_role": slot["resource_role"],
        "capability_kind": slot["capability_kind"],
        "construction_evidence_only": True,
        "real_kernel_credential_authority_present": False,
        "native_cleanup_authority_present": False,
        "current_access_authority_present": False,
        "official_execution_allowed": False,
    }
    if any(document.get(key) != value for key, value in expected.items()):
        _fail("native receipt record crossed its frozen context or slot")


def _validate_start_document(
    handle: H1NativeReceiptJournalHandleV1,
    document: Mapping[str, Any],
    slot: Mapping[str, Any],
    normal_evidence: _NormalEvidence,
) -> None:
    _require_exact_keys(
        document,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "h1_native_receipt_journal_spec_id",
            "h1_native_receipt_allocation_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "transaction_id",
            "slot_key",
            "h1_native_resource_slot_id",
            "normal_ordinal",
            "normal_site_key",
            "broker_role",
            "resource_role",
            "capability_kind",
            "h1_normal_site_intent_id",
            "creating_process_id",
            "creating_thread_id",
            "callback_cell_nonce_commitment",
            "callback_replay_after_durable_start_forbidden",
            "raw_descriptor_fields_serialized",
            "result_status",
            "callback_result_before_normal_event_required",
            "native_receipt_before_normal_event_present",
            "construction_evidence_only",
            "real_kernel_credential_authority_present",
            "native_cleanup_authority_present",
            "current_access_authority_present",
            "official_execution_allowed",
            "h1_native_callback_start_id",
        },
        "native callback start",
    )
    _require_record_context(handle, document, slot)
    intent_id = _cid(document["h1_normal_site_intent_id"], "normal-site intent")
    normal_intent = normal_evidence.intents_by_id.get(intent_id)
    if normal_intent is None or any(
        normal_intent.get(key) != value
        for key, value in {
            "h1_normal_prefix_spec_id": handle.spec.payload["h1_normal_prefix_spec_id"],
            "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
            "route_attempt_id": handle.spec.payload["route_attempt_id"],
            "decision_point_id": handle.spec.payload["decision_point_id"],
            "transaction_id": handle.spec.payload["transaction_id"],
            "ordinal": slot["normal_ordinal"],
            "site_key": slot["normal_site_key"],
        }.items()
    ):
        _fail("native callback start is not bound to an exact normal intent")
    _cid(document["callback_cell_nonce_commitment"], "callback-cell nonce commitment")
    if (
        document["schema"] != "acfqp.k7_h1_native_callback_start.v1"
        or document["creating_process_id"] != handle.broker_process_id
        or document["creating_thread_id"] != handle.broker_thread_id
        or document["callback_replay_after_durable_start_forbidden"] is not True
        or document["raw_descriptor_fields_serialized"] is not False
        or document["result_status"] != "STARTED_WITHOUT_RESULT"
        or document["callback_result_before_normal_event_required"] is not True
        or document["native_receipt_before_normal_event_present"] is not False
    ):
        _fail("native callback start semantics changed")


def _validate_result_document(
    handle: H1NativeReceiptJournalHandleV1,
    document: Mapping[str, Any],
    slot: Mapping[str, Any],
    start: Mapping[str, Any],
) -> None:
    _require_exact_keys(
        document,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "h1_native_receipt_journal_spec_id",
            "h1_native_receipt_allocation_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "transaction_id",
            "slot_key",
            "h1_native_resource_slot_id",
            "normal_ordinal",
            "normal_site_key",
            "broker_role",
            "resource_role",
            "capability_kind",
            "h1_normal_site_intent_id",
            "h1_native_callback_start_id",
            "callback_cell_nonce_commitment",
            "resolution_kind",
            "opaque_capability_identity",
            "absence_reason",
            "creating_process_id",
            "creating_thread_id",
            "raw_descriptor_fields_serialized",
            "raw_descriptor_retained_by_receipt_journal",
            "normal_event_binding_status",
            "callback_invocation_count",
            "callback_replay_forbidden",
            "callback_result_durable_before_normal_event",
            "final_receipt_created_after_event_binding",
            "native_receipt_before_normal_event_present",
            "construction_evidence_only",
            "real_kernel_credential_authority_present",
            "native_cleanup_authority_present",
            "current_access_authority_present",
            "official_execution_allowed",
            "h1_native_callback_result_id",
        },
        "native callback result",
    )
    _require_record_context(handle, document, slot)
    inherited = {
        "h1_normal_site_intent_id",
        "h1_native_callback_start_id",
        "callback_cell_nonce_commitment",
        "creating_process_id",
        "creating_thread_id",
    }
    if any(
        document[key]
        != (
            start["h1_native_callback_start_id"]
            if key == "h1_native_callback_start_id"
            else start[key]
        )
        for key in inherited
    ):
        _fail("native callback result crossed its durable start")
    resolution = document["resolution_kind"]
    if resolution == H1NativeResolutionKindV1.KNOWN_PRESENT.value:
        _cid(document["opaque_capability_identity"], "opaque capability identity")
        if document["absence_reason"] != _typed_null("CAPABILITY_PRESENT"):
            _fail("present native callback result carries an absence reason")
    elif resolution == H1NativeResolutionKindV1.KNOWN_ABSENT.value:
        if (
            document["opaque_capability_identity"]
            != _typed_null("CAPABILITY_KNOWN_ABSENT")
            or type(document["absence_reason"]) is not str
            or not document["absence_reason"]
        ):
            _fail("absent native callback result semantics changed")
    else:
        _fail("native callback result resolution is invalid")
    if (
        document["schema"] != "acfqp.k7_h1_native_callback_result.v1"
        or document["raw_descriptor_fields_serialized"] is not False
        or document["raw_descriptor_retained_by_receipt_journal"] is not False
        or document["normal_event_binding_status"] != "PENDING"
        or document["callback_invocation_count"] != 1
        or document["callback_replay_forbidden"] is not True
        or document["callback_result_durable_before_normal_event"] is not True
        or document["final_receipt_created_after_event_binding"] is not True
        or document["native_receipt_before_normal_event_present"] is not False
    ):
        _fail("native callback result semantics changed")


def _validate_resolution_document(
    handle: H1NativeReceiptJournalHandleV1,
    document: Mapping[str, Any],
    slot: Mapping[str, Any],
    result: Mapping[str, Any],
    kind: str,
    normal_evidence: _NormalEvidence,
) -> None:
    common = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_native_receipt_journal_spec_id",
        "h1_native_receipt_allocation_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "transaction_id",
        "slot_key",
        "h1_native_resource_slot_id",
        "normal_ordinal",
        "normal_site_key",
        "broker_role",
        "resource_role",
        "capability_kind",
        "h1_normal_site_intent_id",
        "h1_normal_site_event_commit_id",
        "h1_native_callback_start_id",
        "h1_native_callback_result_id",
        "creating_process_id",
        "creating_thread_id",
        "raw_descriptor_fields_serialized",
        "opaque_identity_is_kernel_credential",
        "normal_intent_and_event_bound",
        "callback_result_was_durable_before_normal_event",
        "receipt_created_after_exact_normal_event_binding",
        "native_receipt_before_normal_event_present",
        "construction_evidence_only",
        "real_kernel_credential_authority_present",
        "native_cleanup_authority_present",
        "current_access_authority_present",
        "official_execution_allowed",
        "resolution_kind",
    }
    if kind == "KNOWN_PRESENT":
        expected_keys = common | {
            "opaque_capability_identity",
            "capability_identity_non_reusable",
            "h1_native_resource_receipt_id",
        }
        expected_schema = "acfqp.k7_h1_native_resource_receipt.v1"
        expected_resolution = H1NativeResolutionKindV1.KNOWN_PRESENT.value
    else:
        expected_keys = common | {
            "absence_reason",
            "h1_native_absence_resolution_id",
        }
        expected_schema = "acfqp.k7_h1_native_absence_resolution.v1"
        expected_resolution = H1NativeResolutionKindV1.KNOWN_ABSENT.value
    _require_exact_keys(document, expected_keys, "native event-bound resolution")
    _require_record_context(handle, document, slot)
    for key in (
        "h1_normal_site_intent_id",
        "h1_native_callback_start_id",
        "h1_native_callback_result_id",
        "creating_process_id",
        "creating_thread_id",
    ):
        expected_value = (
            result["h1_native_callback_result_id"]
            if key == "h1_native_callback_result_id"
            else result[key]
        )
        if document[key] != expected_value:
            _fail("native event-bound resolution crossed its callback result")
    event_id = _cid(document["h1_normal_site_event_commit_id"], "normal-site event")
    normal_event = normal_evidence.events_by_id.get(event_id)
    if normal_event is None or any(
        normal_event.get(key) != value
        for key, value in {
            "h1_normal_prefix_spec_id": handle.spec.payload["h1_normal_prefix_spec_id"],
            "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
            "route_attempt_id": handle.spec.payload["route_attempt_id"],
            "decision_point_id": handle.spec.payload["decision_point_id"],
            "transaction_id": handle.spec.payload["transaction_id"],
            "ordinal": slot["normal_ordinal"],
            "site_key": slot["normal_site_key"],
            "h1_normal_site_intent_id": result["h1_normal_site_intent_id"],
        }.items()
    ):
        _fail("native resolution is not bound to an exact normal event")
    if (
        document["schema"] != expected_schema
        or document["resolution_kind"] != expected_resolution
        or document["raw_descriptor_fields_serialized"] is not False
        or document["opaque_identity_is_kernel_credential"] is not False
        or document["normal_intent_and_event_bound"] is not True
        or document["callback_result_was_durable_before_normal_event"] is not True
        or document["receipt_created_after_exact_normal_event_binding"] is not True
        or document["native_receipt_before_normal_event_present"] is not False
    ):
        _fail("native event-bound resolution semantics changed")
    if kind == "KNOWN_PRESENT":
        if (
            result["resolution_kind"]
            != H1NativeResolutionKindV1.KNOWN_PRESENT.value
            or document["opaque_capability_identity"]
            != result["opaque_capability_identity"]
            or document["capability_identity_non_reusable"] is not True
        ):
            _fail("present receipt crossed its callback result")
    elif (
        result["resolution_kind"]
        != H1NativeResolutionKindV1.KNOWN_ABSENT.value
        or document["absence_reason"] != result["absence_reason"]
    ):
        _fail("absence resolution crossed its callback result")


def _validate_cutoff_document(
    handle: H1NativeReceiptJournalHandleV1,
    document: Mapping[str, Any],
    state: _State,
    normal_evidence: _NormalEvidence,
) -> None:
    _require_exact_keys(
        document,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "h1_native_receipt_journal_spec_id",
            "h1_native_receipt_allocation_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "transaction_id",
            "h1_normal_prefix_spec_id",
            "h1_normal_prefix_allocation_id",
            "primary_failure_ordinal",
            "primary_failure_event_id",
            "evidence_cursor_sequence",
            "evidence_cursor_head_id",
            "evidence_record_ids",
            "slot_count",
            "typed_resolutions",
            "known_present_count",
            "known_absent_count",
            "unresolved_count",
            "start_without_result_callback_replay_forbidden",
            "exact_cutoff_for_v2_transition",
            "cutoff_exactness_scope",
            "normal_failure_event_semantic_verification_present",
            "v2_transition_integration_present",
            "journal_sealed_against_further_native_starts",
            "callback_result_before_normal_event_present",
            "native_receipt_before_normal_event_present",
            "raw_descriptor_fields_serialized",
            "construction_evidence_only",
            "real_kernel_credential_authority_present",
            "native_cleanup_authority_present",
            "current_access_authority_present",
            "production_execution_authority_present",
            "formal_counter_records_issued",
            "formal_work_vector_issued",
            "formal_comparison_vector_issued",
            "formal_v7_route_authority_present",
            "official_execution_allowed",
            "h1_native_cutoff_snapshot_id",
        },
        "native cutoff snapshot",
    )
    ordinal = _exact_int(document["primary_failure_ordinal"], "primary failure ordinal", minimum=1)
    if ordinal > normal_v1.PREFIX_END_ORDINAL:
        _fail("native cutoff ordinal exceeds the normal prefix")
    failure_id = _cid(document["primary_failure_event_id"], "primary failure event")
    failure_event = normal_evidence.events_by_id.get(failure_id)
    if (
        failure_event is None
        or failure_event.get("ordinal") != ordinal
        or failure_event.get("outcome") == "SUCCESS"
        or failure_event.get("declared_first_failure") is not True
        or failure_event.get("h1_normal_prefix_spec_id")
        != handle.spec.payload["h1_normal_prefix_spec_id"]
        or failure_event.get("route_attempt_id")
        != handle.spec.payload["route_attempt_id"]
    ):
        _fail("native cutoff is not bound to an exact normal failure event")
    resolutions = [
        _typed_resolution(slot, state, ordinal)
        for slot in _declared_slots_for_handle(handle)
    ]
    expected = {
        "schema": "acfqp.k7_h1_native_cutoff_snapshot.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_native_receipt_journal_spec_id": handle.spec.spec_id,
        "h1_native_receipt_allocation_id": handle.allocation_id,
        "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
        "route_attempt_id": handle.spec.payload["route_attempt_id"],
        "decision_point_id": handle.spec.payload["decision_point_id"],
        "transaction_id": handle.spec.payload["transaction_id"],
        "h1_normal_prefix_spec_id": handle.spec.payload["h1_normal_prefix_spec_id"],
        "h1_normal_prefix_allocation_id": handle.spec.payload["h1_normal_prefix_allocation_id"],
        "primary_failure_ordinal": ordinal,
        "primary_failure_event_id": document["primary_failure_event_id"],
        "evidence_cursor_sequence": len(state.cursor_rows) - 1,
        "evidence_cursor_head_id": state.cursor_rows[-1]["h1_native_receipt_cursor_id"],
        "evidence_record_ids": [_record_identity(row)[2] for row in state.records],
        "slot_count": 12,
        "typed_resolutions": resolutions,
        "known_present_count": sum(row["resolution_kind"] == "KNOWN_PRESENT" for row in resolutions),
        "known_absent_count": sum(row["resolution_kind"] == "KNOWN_ABSENT" for row in resolutions),
        "unresolved_count": sum(row["resolution_kind"] == "UNRESOLVED" for row in resolutions),
        "start_without_result_callback_replay_forbidden": True,
        "exact_cutoff_for_v2_transition": True,
        "cutoff_exactness_scope": "NATIVE_RECEIPT_JOURNAL_PREFIX_ONLY",
        "normal_failure_event_semantic_verification_present": False,
        "v2_transition_integration_present": False,
        "journal_sealed_against_further_native_starts": True,
        "callback_result_before_normal_event_present": True,
        "native_receipt_before_normal_event_present": False,
        "raw_descriptor_fields_serialized": False,
        "construction_evidence_only": True,
        "real_kernel_credential_authority_present": False,
        "native_cleanup_authority_present": False,
        "current_access_authority_present": False,
        "production_execution_authority_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    identity = document["h1_native_cutoff_snapshot_id"]
    if dict(document) != {**expected, "h1_native_cutoff_snapshot_id": identity}:
        _fail("native cutoff snapshot semantics changed")


def _load_state_locked(
    handle: H1NativeReceiptJournalHandleV1,
    cursor_fd: int,
    normal_evidence: _NormalEvidence,
) -> _State:
    _require_physical_identity(handle)
    record_rows: list[tuple[int, str, str, dict[str, Any]]] = []
    for child in handle.attempt_directory.iterdir():
        match = _RECORD_PATTERN.fullmatch(child.name)
        if match is None:
            continue
        metadata = child.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_nlink != 1
        ):
            _fail("native receipt record type, mode, or link count changed")
        raw = _read_exact_regular(child)
        document = _parse(raw, "native receipt record")
        kind, _key, identity = _record_identity(document)
        if kind != match.group("kind") or identity != match.group("identity"):
            _fail("native receipt filename crossed its record")
        record_rows.append((int(match.group("sequence")), kind, identity, document))
    record_rows.sort()
    if [row[0] for row in record_rows] != list(range(1, len(record_rows) + 1)):
        _fail("native receipt record sequence has a gap or duplicate")
    expected = [_cursor_genesis(handle.spec.spec_id)]
    for sequence, kind, identity, _document in record_rows:
        expected.append(_cursor_payload(sequence, expected[-1]["h1_native_receipt_cursor_id"], kind, identity))
    os.lseek(cursor_fd, 0, os.SEEK_SET)
    raw = b""
    while True:
        block = os.read(cursor_fd, 65536)
        if not block:
            break
        raw += block
    expected_raw = b"".join(canonical_json_bytes(row) + b"\n" for row in expected)
    if not expected_raw.startswith(raw):
        _fail("native receipt cursor differs from immutable records")
    waters: list[tuple[int, str]] = []
    for child in handle.attempt_directory.iterdir():
        match = _WATER_PATTERN.fullmatch(child.name)
        if match is not None:
            metadata = child.stat(follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o400 or metadata.st_size != 0 or metadata.st_nlink != 1:
                _fail("native receipt high-water seal changed")
            waters.append((int(match.group("sequence")), match.group("identity")))
    waters.sort()
    if not waters or [row[0] for row in waters] != list(range(len(waters))):
        _fail("native receipt high-water sequence changed")
    for sequence, identity in waters:
        if sequence >= len(expected) or expected[sequence]["h1_native_receipt_cursor_id"] != identity:
            _fail("native receipt high-water identity changed")
    high = waters[-1][0]
    target = len(expected) - 1
    genesis_prefix = canonical_json_bytes(expected[0]) + b"\n"
    if (
        target - high not in {0, 1}
        or len(raw) < len(genesis_prefix)
        or raw[: len(genesis_prefix)] != genesis_prefix
    ):
        _fail("native receipt immutable high-water cannot reconcile the journal")
    if raw != expected_raw:
        os.lseek(cursor_fd, 0, os.SEEK_END)
        _write_all(cursor_fd, expected_raw[len(raw) :])
        os.fsync(cursor_fd)
    if high < target:
        _publish(handle.attempt_directory / f"cursor-high-water-{target:04d}-{expected[target]['h1_native_receipt_cursor_id']}", b"")
    rows = expected
    starts: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    resolutions: dict[str, dict[str, Any]] = {}
    cutoff: dict[str, Any] | None = None
    used_intents: set[str] = set()
    used_events: set[str] = set()
    opaque_identities: set[str] = set()
    records: list[dict[str, Any]] = []
    last_started_ordinal = 0
    slots_by_key = _declared_slots_by_key_for_handle(handle)
    for sequence, kind, _identity, document in record_rows:
        if cutoff is not None:
            _fail("native receipt journal continued after its terminal cutoff")
        slot_key = document.get("slot_key")
        if kind == "START":
            slot = slots_by_key.get(slot_key)
            if (
                slot is None
                or slot_key in starts
                or len(resolutions) != len(starts)
                or slot["normal_ordinal"] <= last_started_ordinal
            ):
                _fail("native callback start crossed or duplicated a slot")
            _validate_start_document(handle, document, slot, normal_evidence)
            intent = _cid(document.get("h1_normal_site_intent_id"), "normal-site intent")
            if intent in used_intents:
                _fail("normal-site intent was reused across native slots")
            used_intents.add(intent)
            starts[slot_key] = document
            last_started_ordinal = slot["normal_ordinal"]
        elif kind == "CALLBACK_RESULT":
            slot = slots_by_key.get(slot_key)
            if (
                slot is None
                or slot_key not in starts
                or slot_key in results
                or not records
                or records[-1] is not starts[slot_key]
            ):
                _fail("native callback result crossed or duplicated a start")
            _validate_result_document(handle, document, slot, starts[slot_key])
            if document["resolution_kind"] == H1NativeResolutionKindV1.KNOWN_PRESENT.value:
                opaque = _cid(document["opaque_capability_identity"], "opaque capability identity")
                if opaque in opaque_identities:
                    _fail("opaque capability identity was reused")
                opaque_identities.add(opaque)
            results[slot_key] = document
        elif kind in {"KNOWN_PRESENT", "KNOWN_ABSENT"}:
            slot = slots_by_key.get(slot_key)
            if (
                slot is None
                or slot_key not in results
                or slot_key in resolutions
                or not records
                or records[-1] is not results[slot_key]
            ):
                _fail("native resolution crossed or duplicated a callback result")
            _validate_resolution_document(
                handle,
                document,
                slot,
                results[slot_key],
                kind,
                normal_evidence,
            )
            event = _cid(document.get("h1_normal_site_event_commit_id"), "normal-site event")
            if event in used_events:
                _fail("normal-site event was reused across native slots")
            used_events.add(event)
            resolutions[slot_key] = document
        elif kind == "CUTOFF":
            prior = _State(
                list(records),
                starts,
                results,
                resolutions,
                None,
                expected[:sequence],
            )
            _validate_cutoff_document(handle, document, prior, normal_evidence)
            cutoff = document
        records.append(document)
    return _State(records, starts, results, resolutions, cutoff, rows)


def _with_locked(
    handle: H1NativeReceiptJournalHandleV1,
    *,
    normal_evidence: _NormalEvidence | None = None,
) -> tuple[int, int, _State]:
    if normal_evidence is None:
        normal_evidence = _load_normal_evidence(handle)
    _require_physical_identity(handle)
    flags = os.O_RDWR | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    lock_fd = os.open(handle.attempt_directory / _LOCK_FILE, flags)
    lock_metadata = os.fstat(lock_fd)
    if (
        not stat.S_ISREG(lock_metadata.st_mode)
        or stat.S_IMODE(lock_metadata.st_mode) != 0o600
        or lock_metadata.st_nlink != 1
        or (lock_metadata.st_dev, lock_metadata.st_ino)
        != (handle.lock_device, handle.lock_inode)
    ):
        os.close(lock_fd)
        _fail("opened native receipt journal lock identity changed")
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    cursor_fd = os.open(handle.attempt_directory / _CURSOR_FILE, flags)
    try:
        cursor_metadata = os.fstat(cursor_fd)
        if (
            not stat.S_ISREG(cursor_metadata.st_mode)
            or stat.S_IMODE(cursor_metadata.st_mode) != 0o600
            or cursor_metadata.st_nlink != 2
            or (cursor_metadata.st_dev, cursor_metadata.st_ino)
            != (handle.cursor_device, handle.cursor_inode)
        ):
            _fail("opened native receipt cursor identity changed")
        state = _load_state_locked(handle, cursor_fd, normal_evidence)
        return lock_fd, cursor_fd, state
    except BaseException:
        os.close(cursor_fd)
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        raise


def _unlock(lock_fd: int, cursor_fd: int) -> None:
    os.close(cursor_fd)
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    os.close(lock_fd)


def _append_record_locked(handle: H1NativeReceiptJournalHandleV1, cursor_fd: int, state: _State, document: dict[str, Any]) -> dict[str, Any]:
    kind, _key, identity = _record_identity(document)
    sequence = len(state.records) + 1
    path = handle.attempt_directory / f"record-{sequence:04d}-{kind}-{identity}.json"
    _publish(path, canonical_json_bytes(document))
    cursor = _cursor_payload(sequence, state.cursor_rows[-1]["h1_native_receipt_cursor_id"], kind, identity)
    os.lseek(cursor_fd, 0, os.SEEK_END)
    _write_all(cursor_fd, canonical_json_bytes(cursor) + b"\n")
    os.fsync(cursor_fd)
    _publish(handle.attempt_directory / f"cursor-high-water-{sequence:04d}-{cursor['h1_native_receipt_cursor_id']}", b"")
    state.records.append(document)
    state.cursor_rows.append(cursor)
    return document


def _require_current_normal_intent(
    handle: H1NativeReceiptJournalHandleV1,
    slot: Mapping[str, Any],
    intent_id: str,
    *,
    normal_evidence: _NormalEvidence | None = None,
) -> None:
    evidence = normal_evidence or _load_normal_evidence(handle)
    current = evidence.dangling_intent
    if (
        current is None
        or current.get("h1_normal_prefix_spec_id")
        != handle.spec.payload["h1_normal_prefix_spec_id"]
        or current.get("logical_occurrence_id")
        != handle.spec.payload["logical_occurrence_id"]
        or current.get("route_attempt_id") != handle.spec.payload["route_attempt_id"]
        or current.get("decision_point_id")
        != handle.spec.payload["decision_point_id"]
        or current.get("transaction_id") != handle.spec.payload["transaction_id"]
        or evidence.completed_event_count != slot["normal_ordinal"] - 1
        or current.get("ordinal") != slot["normal_ordinal"]
        or current.get("site_key") != slot["normal_site_key"]
        or current.get("h1_normal_site_intent_id") != intent_id
        or evidence.failed
    ):
        _fail("native callback is not bound to the exact current normal intent")


def _require_exact_normal_event(
    handle: H1NativeReceiptJournalHandleV1,
    slot: Mapping[str, Any],
    intent_id: str,
    event: normal_v1.H1NormalSiteEventCommitV1,
    *,
    normal_evidence: _NormalEvidence | None = None,
) -> Mapping[str, Any]:
    if type(event) is not normal_v1.H1NormalSiteEventCommitV1:
        _fail("native result binding requires one issuer-owned normal event")
    document = event.document
    expected = {
        "h1_normal_prefix_spec_id": handle.spec.payload["h1_normal_prefix_spec_id"],
        "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
        "route_attempt_id": handle.spec.payload["route_attempt_id"],
        "decision_point_id": handle.spec.payload["decision_point_id"],
        "transaction_id": handle.spec.payload["transaction_id"],
        "ordinal": slot["normal_ordinal"],
        "site_key": slot["normal_site_key"],
        "h1_normal_site_intent_id": intent_id,
    }
    if any(document.get(key) != value for key, value in expected.items()):
        _fail("normal event crossed the native slot or intent")
    event_id = _cid(
        document.get("h1_normal_site_event_commit_id"), "normal-site event"
    )
    evidence = normal_evidence or _load_normal_evidence(handle)
    durable = evidence.events_by_id.get(event_id)
    if (
        durable != document
        or evidence.completed_event_count != slot["normal_ordinal"]
        or not evidence.events_by_id
        or next(reversed(evidence.events_by_id)) != event_id
        or evidence.dangling_intent is not None
    ):
        _fail("native receipt was not bound immediately after its exact normal event")
    return document


def _require_exact_normal_failure_event(
    handle: H1NativeReceiptJournalHandleV1,
    event: normal_v1.H1NormalSiteEventCommitV1,
    *,
    normal_evidence: _NormalEvidence | None = None,
) -> Mapping[str, Any]:
    if type(event) is not normal_v1.H1NormalSiteEventCommitV1:
        _fail("native cutoff requires one issuer-owned normal failure event")
    document = event.document
    ordinal = _exact_int(document.get("ordinal"), "primary failure ordinal", minimum=1)
    if (
        ordinal > normal_v1.PREFIX_END_ORDINAL
        or document.get("h1_normal_prefix_spec_id")
        != handle.spec.payload["h1_normal_prefix_spec_id"]
        or document.get("logical_occurrence_id")
        != handle.spec.payload["logical_occurrence_id"]
        or document.get("route_attempt_id") != handle.spec.payload["route_attempt_id"]
        or document.get("decision_point_id")
        != handle.spec.payload["decision_point_id"]
        or document.get("transaction_id") != handle.spec.payload["transaction_id"]
        or document.get("outcome") == "SUCCESS"
        or document.get("declared_first_failure") is not True
    ):
        _fail("native cutoff event is not the bound normal failure")
    event_id = _cid(
        document.get("h1_normal_site_event_commit_id"), "primary failure event"
    )
    evidence = normal_evidence or _load_normal_evidence(handle)
    durable = evidence.events_by_id.get(event_id)
    if (
        durable != document
        or evidence.completed_event_count != ordinal
        or not evidence.events_by_id
        or next(reversed(evidence.events_by_id)) != event_id
        or evidence.failed is not True
    ):
        _fail("native cutoff is not at the exact current normal failure")
    return document


def observe_h1_native_present_v1(raw_descriptor: int, *, capability_kind: H1NativeCapabilityKindV1 | str) -> H1NativeCallbackObservationV1:
    active = _ACTIVE_NATIVE_CALLBACK.get()
    if active is None:
        _fail("native present observation is outside the broker callback cell")
    if os.getpid() != active[4]:
        raise H1NativeForkedCallbackContinuationV1("forked callback cannot mint a native observation")
    if threading.get_ident() != active[5]:
        _fail("foreign callback thread cannot mint a native observation")
    _exact_int(raw_descriptor, "raw descriptor")
    try:
        kind = H1NativeCapabilityKindV1(capability_kind)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error("native capability kind is invalid") from error
    return H1NativeCallbackObservationV1(
        _OBSERVATION_ISSUER,
        H1NativeResolutionKindV1.KNOWN_PRESENT,
        kind,
        None,
        raw_descriptor,
        active[0],
        active[1],
        active[2],
        active[3],
        active[4],
        active[5],
    )


def observe_h1_native_absent_v1(*, capability_kind: H1NativeCapabilityKindV1 | str, reason: str) -> H1NativeCallbackObservationV1:
    active = _ACTIVE_NATIVE_CALLBACK.get()
    if active is None:
        _fail("native absent observation is outside the broker callback cell")
    if os.getpid() != active[4]:
        raise H1NativeForkedCallbackContinuationV1(
            "forked callback cannot mint a native observation"
        )
    if threading.get_ident() != active[5]:
        _fail("foreign callback thread cannot mint a native observation")
    try:
        kind = H1NativeCapabilityKindV1(capability_kind)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error("native capability kind is invalid") from error
    return H1NativeCallbackObservationV1(
        _OBSERVATION_ISSUER,
        H1NativeResolutionKindV1.KNOWN_ABSENT,
        kind,
        _nonempty(reason, "native absence reason"),
        None,
        active[0],
        active[1],
        active[2],
        active[3],
        active[4],
        active[5],
    )


def execute_h1_native_resource_callback_once_v1(
    handle: H1NativeReceiptJournalHandleV1,
    *,
    slot_key: str,
    h1_normal_site_intent_id: str,
    callback: Callable[[], H1NativeCallbackObservationV1],
    crash_point: H1NativeCallbackCrashPointV1 | str = H1NativeCallbackCrashPointV1.NONE,
) -> H1PendingNativeCallbackResultV1:
    _require_broker(handle)
    if normal_v1._ACTIVE_EXECUTIONS.get():
        _fail("native callback cannot nest inside the unintegrated normal lease")
    root_fd, journal_fd, lock_fd, cursor_fd, normal_state = (
        normal_v1._require_journal_locked(handle.normal_handle)
    )
    try:
        evidence = _normal_evidence_from_state(normal_state)
        return _execute_h1_native_resource_callback_once_under_normal_lock(
            handle,
            slot_key=slot_key,
            h1_normal_site_intent_id=h1_normal_site_intent_id,
            callback=callback,
            crash_point=crash_point,
            normal_evidence=evidence,
        )
    finally:
        normal_v1._release_journal_locked(
            root_fd, journal_fd, lock_fd, cursor_fd
        )


def _execute_h1_native_resource_callback_once_under_normal_lock(
    handle: H1NativeReceiptJournalHandleV1,
    *,
    slot_key: str,
    h1_normal_site_intent_id: str,
    callback: Callable[[], H1NativeCallbackObservationV1],
    crash_point: H1NativeCallbackCrashPointV1 | str = H1NativeCallbackCrashPointV1.NONE,
    normal_evidence: _NormalEvidence,
) -> H1PendingNativeCallbackResultV1:
    _require_broker(handle)
    slots_by_key = _declared_slots_by_key_for_handle(handle)
    slot = slots_by_key.get(slot_key)
    if slot is None or not callable(callback):
        _fail("native callback names an unknown slot or non-callable")
    intent_id = _cid(h1_normal_site_intent_id, "normal-site intent")
    try:
        crash = H1NativeCallbackCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1NativeReceiptJournalV1Error("native callback crash point is invalid") from error
    _require_current_normal_intent(
        handle, slot, intent_id, normal_evidence=normal_evidence
    )
    lock_fd, cursor_fd, state = _with_locked(
        handle, normal_evidence=normal_evidence
    )
    try:
        if (
            state.cutoff is not None
            or slot_key in state.starts
            or len(state.resolutions) != len(state.starts)
            or any(
                row["h1_normal_site_intent_id"] == intent_id
                for row in state.starts.values()
            )
        ):
            _fail("native callback slot is sealed or already started; replay is forbidden")
        if state.starts and slot["normal_ordinal"] <= max(
            slots_by_key[key]["normal_ordinal"] for key in state.starts
        ):
            _fail("native callback slot order moved backwards")
        callback_nonce = secrets.token_bytes(32)
        nonce_commitment = hashlib.sha256(
            b"acfqp:h1-native-callback-cell-nonce:v1\x00" + callback_nonce
        ).hexdigest()
        start_payload = {
            "schema": "acfqp.k7_h1_native_callback_start.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_native_receipt_journal_spec_id": handle.spec.spec_id,
            "h1_native_receipt_allocation_id": handle.allocation_id,
            "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
            "route_attempt_id": handle.spec.payload["route_attempt_id"],
            "decision_point_id": handle.spec.payload["decision_point_id"],
            "transaction_id": handle.spec.payload["transaction_id"],
            "slot_key": slot_key,
            "h1_native_resource_slot_id": slot["h1_native_resource_slot_id"],
            "normal_ordinal": slot["normal_ordinal"],
            "normal_site_key": slot["normal_site_key"],
            "broker_role": "BROKER",
            "resource_role": slot["resource_role"],
            "capability_kind": slot["capability_kind"],
            "h1_normal_site_intent_id": intent_id,
            "creating_process_id": os.getpid(),
            "creating_thread_id": threading.get_ident(),
            "callback_cell_nonce_commitment": nonce_commitment,
            "callback_replay_after_durable_start_forbidden": True,
            "raw_descriptor_fields_serialized": False,
            "result_status": "STARTED_WITHOUT_RESULT",
            "callback_result_before_normal_event_required": True,
            "native_receipt_before_normal_event_present": False,
            "construction_evidence_only": True,
            "real_kernel_credential_authority_present": False,
            "native_cleanup_authority_present": False,
            "current_access_authority_present": False,
            "official_execution_allowed": False,
        }
        start = {**start_payload, "h1_native_callback_start_id": _content_id(START_DOMAIN, start_payload)}
        _append_record_locked(handle, cursor_fd, state, start)
    finally:
        _unlock(lock_fd, cursor_fd)
    if crash is H1NativeCallbackCrashPointV1.AFTER_START_FSYNC:
        raise H1NativeReceiptInjectedCrashV1("injected crash after durable native callback start")
    token = _ACTIVE_NATIVE_CALLBACK.set(
        (
            handle.allocation_id,
            slot_key,
            start["h1_native_callback_start_id"],
            callback_nonce,
            os.getpid(),
            threading.get_ident(),
        )
    )
    try:
        observation = callback()
    finally:
        _ACTIVE_NATIVE_CALLBACK.reset(token)
    _require_broker(handle)
    if (
        type(observation) is not H1NativeCallbackObservationV1
        or observation._allocation_id != handle.allocation_id
        or observation._slot_key != slot_key
        or observation._start_id != start["h1_native_callback_start_id"]
        or not hmac.compare_digest(observation._callback_nonce, callback_nonce)
        or observation._creating_process_id != os.getpid()
        or observation._creating_thread_id != threading.get_ident()
        or observation._consumed is not False
    ):
        _fail("native callback returned no issuer-owned typed observation")
    if observation.capability_kind.value != slot["capability_kind"]:
        _fail("native callback capability kind crossed its predeclared slot")
    object.__setattr__(observation, "_consumed", True)
    object.__setattr__(observation, "_raw_descriptor", None)
    if crash is H1NativeCallbackCrashPointV1.AFTER_CALLBACK_BEFORE_RESULT_FSYNC:
        raise H1NativeReceiptInjectedCrashV1("injected crash after native callback before result")
    lock_fd, cursor_fd, state = _with_locked(
        handle, normal_evidence=normal_evidence
    )
    try:
        durable_start = state.starts.get(slot_key)
        if durable_start is None or durable_start["h1_native_callback_start_id"] != start["h1_native_callback_start_id"] or slot_key in state.results or state.cutoff is not None:
            _fail("native callback result no longer matches one unresolved durable start")
        opaque = (
            hashlib.sha256(
                b"acfqp:h1-native-opaque-capability:v1\x00"
                + bytes.fromhex(start["h1_native_callback_start_id"])
                + secrets.token_bytes(32)
            ).hexdigest()
            if observation.resolution_kind is H1NativeResolutionKindV1.KNOWN_PRESENT
            else _typed_null("CAPABILITY_KNOWN_ABSENT")
        )
        if type(opaque) is str and any(
            row.get("opaque_capability_identity") == opaque
            for row in state.results.values()
        ):
            _fail("opaque capability identity is not globally fresh in this allocation")
        result_payload = {
            "schema": "acfqp.k7_h1_native_callback_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_native_receipt_journal_spec_id": handle.spec.spec_id,
            "h1_native_receipt_allocation_id": handle.allocation_id,
            "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
            "route_attempt_id": handle.spec.payload["route_attempt_id"],
            "decision_point_id": handle.spec.payload["decision_point_id"],
            "transaction_id": handle.spec.payload["transaction_id"],
            "slot_key": slot_key,
            "h1_native_resource_slot_id": slot["h1_native_resource_slot_id"],
            "normal_ordinal": slot["normal_ordinal"],
            "normal_site_key": slot["normal_site_key"],
            "broker_role": "BROKER",
            "resource_role": slot["resource_role"],
            "capability_kind": slot["capability_kind"],
            "h1_normal_site_intent_id": intent_id,
            "h1_native_callback_start_id": start["h1_native_callback_start_id"],
            "callback_cell_nonce_commitment": nonce_commitment,
            "resolution_kind": observation.resolution_kind.value,
            "opaque_capability_identity": opaque,
            "absence_reason": observation.absence_reason if observation.absence_reason is not None else _typed_null("CAPABILITY_PRESENT"),
            "creating_process_id": os.getpid(),
            "creating_thread_id": threading.get_ident(),
            "raw_descriptor_fields_serialized": False,
            "raw_descriptor_retained_by_receipt_journal": False,
            "normal_event_binding_status": "PENDING",
            "callback_invocation_count": 1,
            "callback_replay_forbidden": True,
            "callback_result_durable_before_normal_event": True,
            "final_receipt_created_after_event_binding": True,
            "native_receipt_before_normal_event_present": False,
            "construction_evidence_only": True,
            "real_kernel_credential_authority_present": False,
            "native_cleanup_authority_present": False,
            "current_access_authority_present": False,
            "official_execution_allowed": False,
        }
        result = {**result_payload, "h1_native_callback_result_id": _content_id(RESULT_DOMAIN, result_payload)}
        _append_record_locked(handle, cursor_fd, state, result)
        return H1PendingNativeCallbackResultV1(_PENDING_ISSUER, canonical_json_bytes(result))
    finally:
        _unlock(lock_fd, cursor_fd)


def bind_h1_native_callback_result_to_normal_event_v1(
    handle: H1NativeReceiptJournalHandleV1,
    *,
    pending_result: H1PendingNativeCallbackResultV1,
    normal_site_event: normal_v1.H1NormalSiteEventCommitV1,
) -> H1NativeResourceReceiptV1 | dict[str, Any]:
    _require_broker(handle)
    if normal_v1._ACTIVE_EXECUTIONS.get():
        _fail("native event binding cannot nest inside the unintegrated normal lease")
    root_fd, journal_fd, lock_fd, cursor_fd, normal_state = (
        normal_v1._require_journal_locked(handle.normal_handle)
    )
    try:
        evidence = _normal_evidence_from_state(normal_state)
        return _bind_h1_native_callback_result_under_normal_lock(
            handle,
            pending_result=pending_result,
            normal_site_event=normal_site_event,
            normal_evidence=evidence,
        )
    finally:
        normal_v1._release_journal_locked(
            root_fd, journal_fd, lock_fd, cursor_fd
        )


def _bind_h1_native_callback_result_under_normal_lock(
    handle: H1NativeReceiptJournalHandleV1,
    *,
    pending_result: H1PendingNativeCallbackResultV1,
    normal_site_event: normal_v1.H1NormalSiteEventCommitV1,
    normal_evidence: _NormalEvidence,
) -> H1NativeResourceReceiptV1 | dict[str, Any]:
    _require_broker(handle)
    if type(pending_result) is not H1PendingNativeCallbackResultV1:
        _fail("normal event binding requires one issuer-owned pending result")
    pending = pending_result.document
    slot_key = pending.get("slot_key")
    slot = _declared_slots_by_key_for_handle(handle).get(slot_key)
    if slot is None:
        _fail("pending native result crossed its predeclared slot")
    event_document = _require_exact_normal_event(
        handle,
        slot,
        pending.get("h1_normal_site_intent_id"),
        normal_site_event,
        normal_evidence=normal_evidence,
    )
    event_id = event_document["h1_normal_site_event_commit_id"]
    lock_fd, cursor_fd, state = _with_locked(
        handle, normal_evidence=normal_evidence
    )
    try:
        durable = state.results.get(slot_key)
        if (
            slot is None
            or durable != pending
            or slot_key in state.resolutions
            or state.cutoff is not None
            or any(
                row["h1_normal_site_event_commit_id"] == event_id
                for row in state.resolutions.values()
            )
        ):
            _fail("pending native result crossed its journal, slot, or cutoff")
        common = {
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_native_receipt_journal_spec_id": handle.spec.spec_id,
            "h1_native_receipt_allocation_id": handle.allocation_id,
            "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
            "route_attempt_id": handle.spec.payload["route_attempt_id"],
            "decision_point_id": handle.spec.payload["decision_point_id"],
            "transaction_id": handle.spec.payload["transaction_id"],
            "slot_key": slot_key,
            "h1_native_resource_slot_id": slot["h1_native_resource_slot_id"],
            "normal_ordinal": slot["normal_ordinal"],
            "normal_site_key": slot["normal_site_key"],
            "broker_role": "BROKER",
            "resource_role": slot["resource_role"],
            "capability_kind": slot["capability_kind"],
            "h1_normal_site_intent_id": pending["h1_normal_site_intent_id"],
            "h1_normal_site_event_commit_id": event_id,
            "h1_native_callback_start_id": pending["h1_native_callback_start_id"],
            "h1_native_callback_result_id": pending["h1_native_callback_result_id"],
            "creating_process_id": pending["creating_process_id"],
            "creating_thread_id": pending["creating_thread_id"],
            "raw_descriptor_fields_serialized": False,
            "opaque_identity_is_kernel_credential": False,
            "callback_result_was_durable_before_normal_event": True,
            "receipt_created_after_exact_normal_event_binding": True,
            "native_receipt_before_normal_event_present": False,
            "construction_evidence_only": True,
            "real_kernel_credential_authority_present": False,
            "native_cleanup_authority_present": False,
            "current_access_authority_present": False,
            "official_execution_allowed": False,
        }
        if pending["resolution_kind"] == H1NativeResolutionKindV1.KNOWN_PRESENT.value:
            payload = {
                **common,
                "schema": "acfqp.k7_h1_native_resource_receipt.v1",
                "resolution_kind": H1NativeResolutionKindV1.KNOWN_PRESENT.value,
                "opaque_capability_identity": pending["opaque_capability_identity"],
                "capability_identity_non_reusable": True,
                "normal_intent_and_event_bound": True,
            }
            document = {**payload, "h1_native_resource_receipt_id": _content_id(RECEIPT_DOMAIN, payload)}
            _append_record_locked(handle, cursor_fd, state, document)
            return H1NativeResourceReceiptV1(_RECEIPT_ISSUER, canonical_json_bytes(document))
        payload = {
            **common,
            "schema": "acfqp.k7_h1_native_absence_resolution.v1",
            "resolution_kind": H1NativeResolutionKindV1.KNOWN_ABSENT.value,
            "absence_reason": pending["absence_reason"],
            "normal_intent_and_event_bound": True,
        }
        document = {**payload, "h1_native_absence_resolution_id": _content_id(ABSENCE_DOMAIN, payload)}
        _append_record_locked(handle, cursor_fd, state, document)
        return dict(document)
    finally:
        _unlock(lock_fd, cursor_fd)


def _typed_resolution(slot: Mapping[str, Any], state: _State, cutoff_ordinal: int) -> dict[str, Any]:
    key = slot["slot_key"]
    if slot["normal_ordinal"] > cutoff_ordinal:
        if key in state.starts or key in state.results or key in state.resolutions:
            _fail("native evidence exists after the claimed exact cutoff")
        return {
            "slot_key": key,
            "h1_native_resource_slot_id": slot["h1_native_resource_slot_id"],
            "resolution_kind": H1NativeResolutionKindV1.KNOWN_ABSENT.value,
            "reason": "SITE_NOT_REACHED_BEFORE_EXACT_CUTOFF",
            "resolution_record_id": _typed_null("CONTROL_FLOW_ABSENCE"),
        }
    resolution = state.resolutions.get(key)
    if resolution is not None:
        if resolution["schema"] == "acfqp.k7_h1_native_resource_receipt.v1":
            return {
                "slot_key": key,
                "h1_native_resource_slot_id": slot["h1_native_resource_slot_id"],
                "resolution_kind": H1NativeResolutionKindV1.KNOWN_PRESENT.value,
                "receipt_id": resolution["h1_native_resource_receipt_id"],
                "opaque_capability_identity": resolution["opaque_capability_identity"],
            }
        return {
            "slot_key": key,
            "h1_native_resource_slot_id": slot["h1_native_resource_slot_id"],
            "resolution_kind": H1NativeResolutionKindV1.KNOWN_ABSENT.value,
            "reason": resolution["absence_reason"],
            "resolution_record_id": resolution["h1_native_absence_resolution_id"],
        }
    start = state.starts.get(key)
    result = state.results.get(key)
    return {
        "slot_key": key,
        "h1_native_resource_slot_id": slot["h1_native_resource_slot_id"],
        "resolution_kind": H1NativeResolutionKindV1.UNRESOLVED.value,
        "reason": "START_WITHOUT_EVENT_BOUND_RESULT" if start is not None else "REQUIRED_NATIVE_SITE_EVIDENCE_MISSING",
        "start_id": start["h1_native_callback_start_id"] if start is not None else _typed_null("NO_DURABLE_START"),
        "callback_result_id": result["h1_native_callback_result_id"] if result is not None else _typed_null("NO_DURABLE_CALLBACK_RESULT"),
        "native_callback_replay_forbidden": start is not None,
    }


def freeze_h1_native_cutoff_snapshot_for_v2_transition_v1(
    handle: H1NativeReceiptJournalHandleV1,
    *,
    primary_failure_event: normal_v1.H1NormalSiteEventCommitV1,
) -> H1NativeCutoffSnapshotV1:
    _require_broker(handle)
    if normal_v1._ACTIVE_EXECUTIONS.get():
        _fail("native cutoff cannot nest inside the unintegrated normal lease")
    root_fd, journal_fd, lock_fd, cursor_fd, normal_state = (
        normal_v1._require_journal_locked(handle.normal_handle)
    )
    try:
        evidence = _normal_evidence_from_state(normal_state)
        return _freeze_h1_native_cutoff_under_normal_lock(
            handle,
            primary_failure_event=primary_failure_event,
            normal_evidence=evidence,
        )
    finally:
        normal_v1._release_journal_locked(
            root_fd, journal_fd, lock_fd, cursor_fd
        )


def _freeze_h1_native_cutoff_under_normal_lock(
    handle: H1NativeReceiptJournalHandleV1,
    *,
    primary_failure_event: normal_v1.H1NormalSiteEventCommitV1,
    normal_evidence: _NormalEvidence,
) -> H1NativeCutoffSnapshotV1:
    _require_broker(handle)
    event = _require_exact_normal_failure_event(
        handle, primary_failure_event, normal_evidence=normal_evidence
    )
    ordinal = event["ordinal"]
    event_id = event["h1_normal_site_event_commit_id"]
    lock_fd, cursor_fd, state = _with_locked(
        handle, normal_evidence=normal_evidence
    )
    try:
        if state.cutoff is not None:
            _fail("native receipt cutoff is already frozen")
        resolutions = [
            _typed_resolution(slot, state, ordinal)
            for slot in _declared_slots_for_handle(handle)
        ]
        payload = {
            "schema": "acfqp.k7_h1_native_cutoff_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_native_receipt_journal_spec_id": handle.spec.spec_id,
            "h1_native_receipt_allocation_id": handle.allocation_id,
            "logical_occurrence_id": handle.spec.payload["logical_occurrence_id"],
            "route_attempt_id": handle.spec.payload["route_attempt_id"],
            "decision_point_id": handle.spec.payload["decision_point_id"],
            "transaction_id": handle.spec.payload["transaction_id"],
            "h1_normal_prefix_spec_id": handle.spec.payload["h1_normal_prefix_spec_id"],
            "h1_normal_prefix_allocation_id": handle.spec.payload["h1_normal_prefix_allocation_id"],
            "primary_failure_ordinal": ordinal,
            "primary_failure_event_id": event_id,
            "evidence_cursor_sequence": len(state.cursor_rows) - 1,
            "evidence_cursor_head_id": state.cursor_rows[-1]["h1_native_receipt_cursor_id"],
            "evidence_record_ids": [
                _record_identity(row)[2] for row in state.records
            ],
            "slot_count": 12,
            "typed_resolutions": resolutions,
            "known_present_count": sum(row["resolution_kind"] == "KNOWN_PRESENT" for row in resolutions),
            "known_absent_count": sum(row["resolution_kind"] == "KNOWN_ABSENT" for row in resolutions),
            "unresolved_count": sum(row["resolution_kind"] == "UNRESOLVED" for row in resolutions),
            "start_without_result_callback_replay_forbidden": True,
            "exact_cutoff_for_v2_transition": True,
            "cutoff_exactness_scope": "NATIVE_RECEIPT_JOURNAL_PREFIX_ONLY",
            "normal_failure_event_semantic_verification_present": False,
            "v2_transition_integration_present": False,
            "journal_sealed_against_further_native_starts": True,
            "callback_result_before_normal_event_present": True,
            "native_receipt_before_normal_event_present": False,
            "raw_descriptor_fields_serialized": False,
            "construction_evidence_only": True,
            "real_kernel_credential_authority_present": False,
            "native_cleanup_authority_present": False,
            "current_access_authority_present": False,
            "production_execution_authority_present": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
        }
        document = {**payload, "h1_native_cutoff_snapshot_id": _content_id(CUTOFF_DOMAIN, payload)}
        _append_record_locked(handle, cursor_fd, state, document)
        return H1NativeCutoffSnapshotV1(_CUTOFF_ISSUER, canonical_json_bytes(document))
    finally:
        _unlock(lock_fd, cursor_fd)


def replay_h1_native_receipt_journal_v1(handle: H1NativeReceiptJournalHandleV1) -> dict[str, Any]:
    lock_fd, cursor_fd, state = _with_locked(handle)
    try:
        resolutions = {
            slot["slot_key"]: (
                H1NativeResolutionKindV1.KNOWN_PRESENT.value
                if state.resolutions.get(slot["slot_key"], {}).get("schema") == "acfqp.k7_h1_native_resource_receipt.v1"
                else H1NativeResolutionKindV1.KNOWN_ABSENT.value
                if slot["slot_key"] in state.resolutions
                else H1NativeResolutionKindV1.UNRESOLVED.value
                if slot["slot_key"] in state.starts
                else "NOT_STARTED"
            )
            for slot in _declared_slots_for_handle(handle)
        }
        return {
            "schema": "acfqp.k7_h1_native_receipt_journal_replay.v1",
            "h1_native_receipt_journal_spec_id": handle.spec.spec_id,
            "h1_native_receipt_allocation_id": handle.allocation_id,
            "slot_count": 12,
            "record_count": len(state.records),
            "cursor_sequence": len(state.cursor_rows) - 1,
            "cursor_head_id": state.cursor_rows[-1]["h1_native_receipt_cursor_id"],
            "slot_resolutions": resolutions,
            "cutoff_snapshot_id": state.cutoff["h1_native_cutoff_snapshot_id"] if state.cutoff is not None else _typed_null("NO_CUTOFF"),
            "callback_replay_forbidden_slots": sorted(state.starts),
            "callback_result_before_normal_event_present": True,
            "native_receipt_before_normal_event_present": False,
            "native_receipt_created_after_exact_event_binding": True,
            "same_broker_initialization_convergence_present": True,
            "cross_process_initialization_recovery_present": False,
            "raw_descriptor_fields_serialized": False,
            "construction_evidence_only": True,
            "real_kernel_credential_authority_present": False,
            "native_cleanup_authority_present": False,
            "current_access_authority_present": False,
            "production_execution_authority_present": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
        }
    finally:
        _unlock(lock_fd, cursor_fd)


__all__ = (
    "CROSS_PROCESS_INITIALIZATION_RECOVERY_PRESENT",
    "CURRENT_ACCESS_AUTHORITY_PRESENT",
    "EXACT_NATIVE_CUTOFF_SNAPSHOT_PRESENT",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "H1NativeCallbackCrashPointV1",
    "H1NativeInitializationCrashPointV1",
    "H1NativeCapabilityKindV1",
    "H1NativeCutoffSnapshotV1",
    "H1NativeForkedCallbackContinuationV1",
    "H1NativeReceiptInjectedCrashV1",
    "H1NativeReceiptJournalHandleV1",
    "H1NativeReceiptJournalSpecV1",
    "H1NativeResolutionKindV1",
    "H1NativeResourceReceiptV1",
    "NATIVE_CLEANUP_AUTHORITY_PRESENT",
    "NATIVE_CALLBACK_RESULT_BEFORE_NORMAL_EVENT_PRESENT",
    "NATIVE_RECEIPT_BEFORE_NORMAL_EVENT_PRESENT",
    "NATIVE_RESOURCE_RECEIPT_JOURNAL_PRESENT",
    "NATIVE_RESOURCE_SLOT_PREDECLARATION_PRESENT",
    "NORMAL_FAILURE_EVENT_SEMANTIC_VERIFICATION_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PREDECLARED_NATIVE_RESOURCE_SLOTS_V1",
    "PRODUCTION_EXECUTION_AUTHORITY_PRESENT",
    "REAL_KERNEL_CREDENTIAL_AUTHORITY_PRESENT",
    "SAME_BROKER_INITIALIZATION_CONVERGENCE_PRESENT",
    "V2_TRANSITION_INTEGRATION_PRESENT",
    "bind_h1_native_callback_result_to_normal_event_v1",
    "execute_h1_native_resource_callback_once_v1",
    "freeze_h1_native_cutoff_snapshot_for_v2_transition_v1",
    "freeze_h1_native_receipt_journal_spec_v1",
    "initialize_h1_native_receipt_journal_v1",
    "observe_h1_native_absent_v1",
    "observe_h1_native_present_v1",
    "open_h1_native_receipt_journal_v1",
    "replay_h1_native_receipt_journal_v1",
)
