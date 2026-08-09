"""Process-local kernel-capability guardian for H1 native receipt evidence.

V6 deliberately records only durable callback evidence; an opaque receipt is
not a live kernel credential.  This additive E1 slice couples the exact V6
callback/result/receipt sequence to a non-serializable, broker-incarnation-
bound holder of three CLOEXEC aliases for the same Linux open-file description.

The guardian has no cleanup token and executes no cleanup action.  In
particular it does not close, reap, release, or finalize a live capability as
part of the failed-prefix cleanup protocol.  The private child-fork poison and
test-disposal paths merely prevent copied process-local handles from escaping
their broker incarnation; they confer no production cleanup authority.
"""

from __future__ import annotations

from contextvars import ContextVar
import ctypes
from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import fcntl
import hmac
import os
from pathlib import Path
import platform
import re
import secrets
import stat
import threading
from types import MappingProxyType
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_k7_h1_domain_registry_extension_v8 as domains_v8
from acfqp import construction_k7_h1_failed_prefix_cleanup_budget_admission_v1 as admission_v1
from acfqp import construction_k7_h1_native_resource_receipt_journal_v1 as receipts_v1
from acfqp import construction_k7_h1_owner_cleanup_continuation_sidecar_v1 as sidecar_v1
from acfqp import construction_k7_h1_phase_aware_normal_prefix_v1 as normal_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E1"
PROFILE_KEY = "construction_k7_h1_native_capability_guardian_v1"

NATIVE_CAPABILITY_GUARDIAN_PRESENT = True
LINUX_KCMP_FILE_IDENTITY_REQUIRED = True
CALLER_ORIGINAL_DESCRIPTOR_CLOSED_AFTER_ADOPTION = True
GUARDIAN_PROCESS_THREAD_INCARNATION_BOUND = True
DIRECT_V6_RECEIPT_CONFERS_LIVE_CAPABILITY = False
BROKER_RESTART_RECOVERY_PRESENT = False
CUTOFF_CLEANUP_TOKEN_AUTHORITY_PRESENT = False
CLEANUP_ACTION_JOURNAL_PRESENT = False
NATIVE_CLEANUP_EFFECT_AUTHORITY_PRESENT = False
PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False

SPEC_DOMAIN = (
    domains_v8.CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_SPEC_V1_DOMAIN
)
BINDING_DOMAIN = (
    domains_v8.CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_BINDING_V1_DOMAIN
)
MARKER_DOMAIN = (
    domains_v8.CONSTRUCTION_K7_H1_NATIVE_CAPABILITY_GUARDIAN_INIT_MARKER_V1_DOMAIN
)

_SPEC_ISSUER = object()
_GUARDIAN_ISSUER = object()
_ACQUISITION_ISSUER = object()
_PENDING_ISSUER = object()
_BOUND_ISSUER = object()
_KCMP_FILE = 0
_F_DUPFD_CLOEXEC = getattr(fcntl, "F_DUPFD_CLOEXEC", 1030)
_MARKER_ROOT_NAME = ".acfqp-k7-h1-native-capability-guardian-v1"
_MARKER_FILE = "guardian-init-marker.json"
_MARKER_SEAL_PREFIX = "guardian-init-marker-seal-"
_CONTENT_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_KCMP_SYSCALL_BY_MACHINE = MappingProxyType(
    {
        "x86_64": 312,
        "amd64": 312,
        "aarch64": 272,
        "arm64": 272,
    }
)


class ConstructionK7H1NativeCapabilityGuardianV1Error(ValueError):
    """The process-local capability guardian failed closed."""


class H1NativeCapabilityGuardianInjectedCrashV1(RuntimeError):
    """Test-only crash after irreversible marker publication."""


class H1NativeCapabilityGuardianStatusV1(str, Enum):
    PRESENT_LIVE = "PRESENT_LIVE"
    ABSENT = "ABSENT"
    UNRESOLVED = "UNRESOLVED"


class H1NativeCapabilityGuardianInitializationCrashPointV1(str, Enum):
    NONE = "NONE"
    AFTER_PRIMARY_FSYNC_BEFORE_SEAL = "AFTER_PRIMARY_FSYNC_BEFORE_SEAL"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1NativeCapabilityGuardianV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value or "\x00" in value:
        _fail(f"{label} must be one nonempty string")
    return value


def _parse(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            f"{label} is not canonical"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


def _content_id(domain: str, payload: Any) -> str:
    return domains_v8.extension_content_id_v8(domain, payload)


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _process_start_ticks(process_id: int | None = None) -> int:
    pid = os.getpid() if process_id is None else process_id
    try:
        with open(f"/proc/{pid}/stat", "rb", buffering=0) as stream:
            raw = stream.read()
        closing = raw.rfind(b")")
        fields = raw[closing + 2 :].split()
        value = int(fields[19])
    except (OSError, ValueError, IndexError) as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            "broker process incarnation cannot be read"
        ) from error
    if value < 1:
        _fail("broker process incarnation is invalid")
    return value


def _kcmp_file(left_fd: int, right_fd: int) -> bool:
    """Return exact same-OFD identity, or fail closed when kcmp is unavailable."""

    machine = platform.machine().lower()
    number = _KCMP_SYSCALL_BY_MACHINE.get(machine)
    if number is None:
        _fail("Linux kcmp(KCMP_FILE) is unavailable on this architecture")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = libc.syscall(
        ctypes.c_long(number),
        ctypes.c_int(os.getpid()),
        ctypes.c_int(os.getpid()),
        ctypes.c_int(_KCMP_FILE),
        ctypes.c_ulong(left_fd),
        ctypes.c_ulong(right_fd),
    )
    if result == -1:
        code = ctypes.get_errno()
        name = errno.errorcode.get(code, str(code))
        _fail(f"Linux kcmp(KCMP_FILE) failed closed: {name}")
    return result == 0


def _probe_kcmp_file() -> None:
    first_read = first_write = duplicate = second_read = second_write = -1
    try:
        first_read, first_write = os.pipe2(os.O_CLOEXEC)
        duplicate = fcntl.fcntl(first_read, _F_DUPFD_CLOEXEC, 0)
        second_read, second_write = os.pipe2(os.O_CLOEXEC)
        if not _kcmp_file(first_read, duplicate):
            _fail("Linux kcmp(KCMP_FILE) failed its same-OFD probe")
        if _kcmp_file(first_read, second_read):
            _fail("Linux kcmp(KCMP_FILE) failed its distinct-OFD probe")
    finally:
        for descriptor in (
            first_read,
            first_write,
            duplicate,
            second_read,
            second_write,
        ):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _fdinfo(descriptor: int, kind: receipts_v1.H1NativeCapabilityKindV1) -> tuple[tuple[str, str], ...]:
    try:
        with open(f"/proc/self/fdinfo/{descriptor}", "r", encoding="ascii") as stream:
            parsed: dict[str, str] = {}
            for raw in stream:
                key, separator, value = raw.partition(":")
                if separator:
                    parsed[key.strip()] = value.strip()
    except (OSError, UnicodeError) as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            "descriptor fdinfo provenance cannot be read"
        ) from error
    required = {"flags", "mnt_id", "ino"}
    if not required.issubset(parsed):
        _fail("descriptor fdinfo provenance is incomplete")
    if kind is receipts_v1.H1NativeCapabilityKindV1.PIDFD:
        if "Pid" not in parsed:
            _fail("PIDFD slot did not receive a Linux pidfd")
        keys = sorted(required | {key for key in ("Pid", "NSpid") if key in parsed})
    else:
        if "Pid" in parsed:
            _fail("OFD slot received a pidfd instead of its declared resource")
        keys = sorted(required)
    return tuple((key, parsed[key]) for key in keys)


def _stat_fingerprint(descriptor: int) -> tuple[int, int, int, int]:
    try:
        metadata = os.fstat(descriptor)
    except OSError as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            "descriptor fstat provenance cannot be read"
        ) from error
    return (metadata.st_mode, metadata.st_dev, metadata.st_ino, metadata.st_rdev)


def _require_cloexec(descriptor: int) -> None:
    try:
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFD)
    except OSError as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            "guardian descriptor is no longer open"
        ) from error
    if not flags & fcntl.FD_CLOEXEC:
        _fail("guardian descriptor lost CLOEXEC, including through dup2 replacement")


@dataclass(frozen=True, slots=True)
class H1NativeCapabilityGuardianSpecV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SPEC_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("native capability guardian spec is caller-minted")
        payload = _parse(self.payload_bytes, "native capability guardian spec")
        object.__setattr__(self, "_spec_id", _content_id(SPEC_DOMAIN, payload))

    @property
    def spec_id(self) -> str:
        return self._spec_id

    @property
    def payload(self) -> dict[str, Any]:
        return _parse(self.payload_bytes, "native capability guardian spec")

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(
            {**self.payload, "h1_native_capability_guardian_spec_id": self.spec_id}
        )


class _LiveCapabilityCell:
    __slots__ = (
        "_master_fd",
        "_witness_fd",
        "_stat_fingerprint",
        "_fdinfo_fingerprint",
        "_generation_secret",
        "kind",
        "slot_key",
    )

    def __init__(
        self,
        *,
        master_fd: int,
        witness_fd: int,
        stat_fingerprint: tuple[int, int, int, int],
        fdinfo_fingerprint: tuple[tuple[str, str], ...],
        generation_secret: bytes,
        kind: receipts_v1.H1NativeCapabilityKindV1,
        slot_key: str,
    ) -> None:
        self._master_fd = master_fd
        self._witness_fd = witness_fd
        self._stat_fingerprint = stat_fingerprint
        self._fdinfo_fingerprint = fdinfo_fingerprint
        self._generation_secret = generation_secret
        self.kind = kind
        self.slot_key = slot_key

    def __repr__(self) -> str:
        return "<_LiveCapabilityCell sealed>"

    def __reduce__(self) -> NoReturn:
        _fail("live capability cell is not serializable")

    def _close_master_witness(self) -> None:
        for name in ("_master_fd", "_witness_fd"):
            descriptor = getattr(self, name)
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                setattr(self, name, -1)
        self._generation_secret = b""


class _GuardianSlotState:
    __slots__ = (
        "binding_document",
        "cell",
        "pending_result_id",
        "resolution_id",
        "start_id",
        "status",
        "unresolved_reason",
    )

    def __init__(self) -> None:
        self.status = H1NativeCapabilityGuardianStatusV1.UNRESOLVED
        self.unresolved_reason = "NOT_GUARDIAN_BOUND"
        self.cell: _LiveCapabilityCell | None = None
        self.start_id: str | None = None
        self.pending_result_id: str | None = None
        self.resolution_id: str | None = None
        self.binding_document: dict[str, Any] | None = None

    def __repr__(self) -> str:
        return f"<_GuardianSlotState status={self.status.value}>"


class H1NativeCapabilityAcquisitionV1:
    __slots__ = (
        "_consumed",
        "_guardian_incarnation",
        "_process_id",
        "_cell",
        "_slot_key",
        "_thread",
        "absence_reason",
        "capability_kind",
        "resolution_kind",
    )

    def __init__(
        self,
        _issuer: object,
        *,
        resolution_kind: receipts_v1.H1NativeResolutionKindV1,
        capability_kind: receipts_v1.H1NativeCapabilityKindV1,
        cell: _LiveCapabilityCell | None,
        absence_reason: str | None,
        guardian_incarnation: object,
        slot_key: str,
    ) -> None:
        if _issuer is not _ACQUISITION_ISSUER:
            _fail("guardian acquisition is caller-minted")
        self.resolution_kind = resolution_kind
        self.capability_kind = capability_kind
        self.absence_reason = absence_reason
        self._cell = cell
        self._guardian_incarnation = guardian_incarnation
        self._slot_key = slot_key
        self._process_id = os.getpid()
        self._thread = threading.current_thread()
        self._consumed = False

    def __repr__(self) -> str:
        return (
            "<H1NativeCapabilityAcquisitionV1 "
            f"resolution={self.resolution_kind.value} sealed>"
        )

    def __reduce__(self) -> NoReturn:
        _fail("guardian acquisition is not serializable")


class H1GuardedPendingNativeBindingV1:
    __slots__ = (
        "_bound",
        "_guardian_incarnation",
        "_native_pending",
        "_process_id",
        "_slot_key",
        "_thread",
    )

    def __init__(
        self,
        _issuer: object,
        *,
        guardian_incarnation: object,
        slot_key: str,
        native_pending: receipts_v1.H1PendingNativeCallbackResultV1,
    ) -> None:
        if _issuer is not _PENDING_ISSUER:
            _fail("guarded pending binding is caller-minted")
        self._guardian_incarnation = guardian_incarnation
        self._slot_key = slot_key
        self._native_pending = native_pending
        self._process_id = os.getpid()
        self._thread = threading.current_thread()
        self._bound = False

    @property
    def result_id(self) -> str:
        return self._native_pending.result_id

    @property
    def slot_key(self) -> str:
        return self._slot_key

    def __repr__(self) -> str:
        return "<H1GuardedPendingNativeBindingV1 sealed>"

    def __reduce__(self) -> NoReturn:
        _fail("guarded pending binding is not serializable")


class H1GuardedNativeBindingV1:
    __slots__ = (
        "_binding_id",
        "_document_bytes",
        "_guardian",
        "_guardian_incarnation",
        "_slot_key",
        "_thread",
    )

    def __init__(
        self,
        _issuer: object,
        *,
        document_bytes: bytes,
        guardian: H1NativeCapabilityGuardianV1,
        slot_key: str,
    ) -> None:
        if _issuer is not _BOUND_ISSUER or type(document_bytes) is not bytes:
            _fail("guarded native binding is caller-minted")
        document = _parse(document_bytes, "guarded native binding")
        payload = dict(document)
        claimed = _cid(
            payload.pop("h1_native_capability_guardian_binding_id", None),
            "guarded native binding",
        )
        if claimed != _content_id(BINDING_DOMAIN, payload):
            _fail("guarded native binding identity changed")
        self._document_bytes = document_bytes
        self._guardian = guardian
        self._guardian_incarnation = guardian._incarnation
        self._slot_key = slot_key
        self._binding_id = claimed
        self._thread = threading.current_thread()

    def _require_live(self) -> None:
        _reject_public_reentry()
        _require_guardian(self._guardian)
        if (
            self._guardian_incarnation is not self._guardian._incarnation
            or self._thread is not threading.current_thread()
        ):
            _fail("guarded native binding token crossed its thread or incarnation")
        with _REGISTRY_LOCK:
            state = self._guardian._slot_states.get(self._slot_key)
            state_document = (
                dict(state.binding_document)
                if state is not None and state.binding_document is not None
                else None
            )
            state_claimed = (
                state_document.pop(
                    "h1_native_capability_guardian_binding_id", None
                )
                if state_document is not None
                else None
            )
            if (
                state is None
                or state.binding_document is None
                or state_claimed != self._binding_id
                or _content_id(BINDING_DOMAIN, state_document) != self._binding_id
            ):
                _fail("guarded native binding token lost its exact live state")
            expected_status = H1NativeCapabilityGuardianStatusV1(
                _parse(
                    self._document_bytes, "guarded native binding"
                )["guardian_status"]
            )
            if (
                state.status is H1NativeCapabilityGuardianStatusV1.UNRESOLVED
                or state.status is not expected_status
            ):
                _fail("guarded native binding token no longer matches live state")
            if expected_status is H1NativeCapabilityGuardianStatusV1.PRESENT_LIVE:
                if state.cell is None:
                    _fail("guarded native binding token lost its live cell")
                _verify_live_cell_locked(self._guardian, state.cell)
            elif state.cell is not None:
                _fail("guarded absence binding unexpectedly acquired a live cell")

    @property
    def document(self) -> dict[str, Any]:
        self._require_live()
        return _parse(self._document_bytes, "guarded native binding")

    @property
    def binding_id(self) -> str:
        self._require_live()
        return self._binding_id

    @property
    def status(self) -> H1NativeCapabilityGuardianStatusV1:
        self._require_live()
        return H1NativeCapabilityGuardianStatusV1(
            _parse(
                self._document_bytes, "guarded native binding"
            )["guardian_status"]
        )

    def __repr__(self) -> str:
        return "<H1GuardedNativeBindingV1 live-token sealed>"

    def __reduce__(self) -> NoReturn:
        _fail("guarded native binding is process-local and not serializable")


class H1NativeCapabilityGuardianV1:
    __slots__ = (
        "__weakref__",
        "_admission",
        "_broker_process_id",
        "_broker_process_start_ticks",
        "_broker_thread",
        "_broker_thread_diagnostic_id",
        "_incarnation",
        "_native_handle",
        "_marker_id",
        "_poison_reason",
        "_poisoned",
        "_registry_key",
        "_slot_states",
        "spec",
    )

    def __init__(
        self,
        _issuer: object,
        *,
        spec: H1NativeCapabilityGuardianSpecV1,
        native_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
        admission: admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1,
        incarnation: object,
        marker_id: str,
        broker_thread: threading.Thread,
        broker_thread_diagnostic_id: int,
        broker_process_start_ticks: int,
    ) -> None:
        if (
            _issuer is not _GUARDIAN_ISSUER
            or type(spec) is not H1NativeCapabilityGuardianSpecV1
            or type(native_handle) is not receipts_v1.H1NativeReceiptJournalHandleV1
            or type(admission)
            is not admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1
        ):
            _fail("native capability guardian is caller-minted")
        self.spec = spec
        self._native_handle = native_handle
        self._admission = admission
        self._incarnation = incarnation
        self._marker_id = _cid(marker_id, "guardian initialization marker")
        self._broker_process_id = os.getpid()
        if broker_thread is not threading.current_thread():
            _fail("guardian broker thread object changed during initialization")
        self._broker_thread = broker_thread
        self._broker_thread_diagnostic_id = broker_thread_diagnostic_id
        self._broker_process_start_ticks = broker_process_start_ticks
        self._registry_key = (
            native_handle.allocation_id,
            self._broker_process_id,
            self._broker_process_start_ticks,
        )
        self._slot_states = {
            row["slot_key"]: _GuardianSlotState()
            for row in receipts_v1._declared_slots_for_handle(native_handle)
        }
        self._poisoned = False
        self._poison_reason: str | None = None

    def __repr__(self) -> str:
        return (
            "<H1NativeCapabilityGuardianV1 "
            f"spec_id={self.spec.spec_id} sealed>"
        )

    def __reduce__(self) -> NoReturn:
        _fail("native capability guardian is not serializable")

    def _dispose_for_test_only(self) -> None:
        with _REGISTRY_LOCK:
            _poison_guardian_locked(self, "TEST_ONLY_PROCESS_LOCAL_DISPOSAL")
            _LIVE_GUARDIANS.pop(self._registry_key, None)


_REGISTRY_LOCK = threading.RLock()
_LIVE_GUARDIANS: dict[
    tuple[str, int, int], H1NativeCapabilityGuardianV1
] = {}
_GUARDED_ALLOCATIONS: set[tuple[str, int, int]] = set()
_ANCHOR_FDS: dict[tuple[tuple[str, int, int], str], int] = {}
_PENDING_FDS: set[int] = set()


def _close_fd_quietly(descriptor: int) -> None:
    if descriptor >= 0:
        try:
            os.close(descriptor)
        except OSError:
            pass


def _poison_guardian_locked(
    guardian: H1NativeCapabilityGuardianV1, reason: str
) -> None:
    if guardian._poisoned:
        return
    guardian._poisoned = True
    guardian._poison_reason = reason
    for slot_key, state in guardian._slot_states.items():
        if state.cell is not None:
            state.cell._close_master_witness()
        anchor = _ANCHOR_FDS.pop((guardian._registry_key, slot_key), -1)
        _close_fd_quietly(anchor)
        state.status = H1NativeCapabilityGuardianStatusV1.UNRESOLVED
        state.unresolved_reason = reason


def _guardian_atfork_before() -> None:
    _REGISTRY_LOCK.acquire()


def _guardian_atfork_after_parent() -> None:
    _REGISTRY_LOCK.release()


def _poison_guardians_after_fork_in_child() -> None:
    global _REGISTRY_LOCK
    descriptors = set(_PENDING_FDS)
    descriptors.update(_ANCHOR_FDS.values())
    for guardian in _LIVE_GUARDIANS.values():
        for state in guardian._slot_states.values():
            if state.cell is not None:
                descriptors.update(
                    (state.cell._master_fd, state.cell._witness_fd)
                )
                state.cell._master_fd = -1
                state.cell._witness_fd = -1
                state.cell._generation_secret = b""
            state.status = H1NativeCapabilityGuardianStatusV1.UNRESOLVED
            state.unresolved_reason = "FORKED_CHILD_HANDLE_IS_NONRECOVERABLE"
        guardian._poisoned = True
        guardian._poison_reason = "FORKED_CHILD_HANDLE_IS_NONRECOVERABLE"
    for descriptor in descriptors:
        _close_fd_quietly(descriptor)
    _PENDING_FDS.clear()
    _ANCHOR_FDS.clear()
    _LIVE_GUARDIANS.clear()
    _GUARDED_ALLOCATIONS.clear()
    _REGISTRY_LOCK = threading.RLock()


os.register_at_fork(
    before=_guardian_atfork_before,
    after_in_parent=_guardian_atfork_after_parent,
    after_in_child=_poison_guardians_after_fork_in_child,
)


class _ActiveAcquisitionCell:
    __slots__ = (
        "active",
        "guardian",
        "guardian_incarnation",
        "issued",
        "kind",
        "process_id",
        "slot_key",
        "thread",
        "window_incarnation",
    )

    def __init__(
        self,
        guardian: H1NativeCapabilityGuardianV1,
        slot_key: str,
        kind: receipts_v1.H1NativeCapabilityKindV1,
    ) -> None:
        self.guardian = guardian
        self.guardian_incarnation = guardian._incarnation
        self.slot_key = slot_key
        self.kind = kind
        self.issued: list[H1NativeCapabilityAcquisitionV1] = []
        self.process_id = os.getpid()
        self.thread = threading.current_thread()
        self.active = False
        self.window_incarnation: object | None = None


_ACTIVE_ACQUISITION: ContextVar[_ActiveAcquisitionCell | None] = ContextVar(
    "acfqp_k7_h1_native_capability_guardian_acquisition", default=None
)


def _require_guardian(handle: H1NativeCapabilityGuardianV1) -> None:
    if type(handle) is not H1NativeCapabilityGuardianV1:
        _fail("native capability guardian handle is not issuer-owned")
    if handle._poisoned:
        _fail("native capability guardian is poisoned and nonrecoverable")
    if (
        os.getpid() != handle._broker_process_id
        or threading.current_thread() is not handle._broker_thread
    ):
        _fail("native capability guardian crossed its broker process or thread")
    if _process_start_ticks() != handle._broker_process_start_ticks:
        with _REGISTRY_LOCK:
            _poison_guardian_locked(handle, "BROKER_INCARNATION_CHANGED")
        _fail("native capability guardian broker incarnation changed nonrecoverably")
    receipts_v1._require_broker(handle._native_handle)


def _reject_public_reentry() -> None:
    if _ACTIVE_ACQUISITION.get() is not None:
        _fail("guardian public API cannot reenter its active acquisition callback")


def _require_active_acquisition() -> _ActiveAcquisitionCell:
    active = _ACTIVE_ACQUISITION.get()
    if (
        active is None
        or not active.active
        or active.window_incarnation is None
        or active.process_id != os.getpid()
        or active.thread is not threading.current_thread()
        or active.guardian_incarnation is not active.guardian._incarnation
    ):
        _fail("guarded native observation is outside its live callback window")
    _require_guardian(active.guardian)
    return active


def _open_directory_at(directory_fd: int, name: str, label: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            f"{label} cannot be opened read-only"
        ) from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o700:
        os.close(descriptor)
        _fail(f"{label} is not one private directory")
    return descriptor


def _open_regular_at(directory_fd: int, name: str, label: str) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            f"{label} is absent or cannot be opened read-only"
        ) from error
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o400
    ):
        os.close(descriptor)
        _fail(f"{label} is not one immutable regular file")
    return descriptor


def _read_regular_fd(descriptor: int, expected_size: int, label: str) -> bytes:
    if expected_size < 1 or expected_size > 16 * 1024 * 1024:
        _fail(f"{label} size is outside its construction bound")
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = expected_size
    while remaining:
        chunk = os.read(descriptor, min(remaining, 1024 * 1024))
        if not chunk:
            _fail(f"{label} ended before its stat size")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        _fail(f"{label} grew during read-only replay")
    return b"".join(chunks)


class _DurableAdmissionPins:
    __slots__ = (
        "attempt_fd",
        "base",
        "base_fd",
        "primary_fd",
        "route_attempt_id",
        "root_fd",
        "seal_fd",
    )

    def __init__(self, base: Path, base_fd: int, root_fd: int, attempt_fd: int,
                 primary_fd: int, seal_fd: int, route_attempt_id: str) -> None:
        self.base = base
        self.base_fd = base_fd
        self.root_fd = root_fd
        self.attempt_fd = attempt_fd
        self.primary_fd = primary_fd
        self.seal_fd = seal_fd
        self.route_attempt_id = route_attempt_id

    def verify_namespace_mapping(self, expected_raw: bytes) -> None:
        """Recheck the complete durable C-D mapping while every object is pinned."""

        seal_name = f"{admission_v1._SEAL_PREFIX}{self.route_attempt_id}"
        try:
            mappings = (
                (
                    os.stat(self.base, follow_symlinks=False),
                    os.fstat(self.base_fd),
                    "phase base",
                ),
                (
                    os.stat(
                        admission_v1._ROOT_NAME,
                        dir_fd=self.base_fd,
                        follow_symlinks=False,
                    ),
                    os.fstat(self.root_fd),
                    "C-D root",
                ),
                (
                    os.stat(
                        self.route_attempt_id,
                        dir_fd=self.root_fd,
                        follow_symlinks=False,
                    ),
                    os.fstat(self.attempt_fd),
                    "C-D attempt",
                ),
                (
                    os.stat(
                        admission_v1._ADMISSION_FILE,
                        dir_fd=self.attempt_fd,
                        follow_symlinks=False,
                    ),
                    os.fstat(self.primary_fd),
                    "C-D primary",
                ),
                (
                    os.stat(
                        seal_name,
                        dir_fd=self.base_fd,
                        follow_symlinks=False,
                    ),
                    os.fstat(self.seal_fd),
                    "C-D base seal",
                ),
            )
        except OSError as error:
            raise ConstructionK7H1NativeCapabilityGuardianV1Error(
                "C-D durable namespace mapping disappeared while pinned"
            ) from error
        for current, pinned, label in mappings:
            if (current.st_dev, current.st_ino) != (pinned.st_dev, pinned.st_ino):
                _fail(f"{label} namespace mapping changed while pinned")
        primary_metadata = os.fstat(self.primary_fd)
        seal_metadata = os.fstat(self.seal_fd)
        if (
            stat.S_IMODE(primary_metadata.st_mode) != 0o400
            or stat.S_IMODE(seal_metadata.st_mode) != 0o400
            or primary_metadata.st_nlink != 2
            or seal_metadata.st_nlink != 2
            or set(os.listdir(self.attempt_fd)) != {admission_v1._ADMISSION_FILE}
            or any(
                not _CONTENT_ID_PATTERN.fullmatch(name)
                for name in os.listdir(self.root_fd)
            )
        ):
            _fail("C-D durable topology changed while pinned")
        primary_raw = _read_regular_fd(
            self.primary_fd, primary_metadata.st_size, "pinned C-D primary"
        )
        seal_raw = _read_regular_fd(
            self.seal_fd, seal_metadata.st_size, "pinned C-D base seal"
        )
        if (
            not hmac.compare_digest(primary_raw, expected_raw)
            or not hmac.compare_digest(seal_raw, expected_raw)
        ):
            _fail("C-D durable bytes changed while pinned")

    def close(self) -> None:
        for name in ("seal_fd", "primary_fd", "attempt_fd", "root_fd", "base_fd"):
            descriptor = getattr(self, name)
            if descriptor >= 0:
                _close_fd_quietly(descriptor)
                setattr(self, name, -1)


def _pin_and_replay_durable_cleanup_admission(
    admission: admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1,
) -> _DurableAdmissionPins:
    payload = admission.payload
    baseline = payload["prospective_owner_cleanup_sidecar_baseline"]
    base = Path(baseline["phase_base_realpath"])
    if not base.is_absolute() or str(base.resolve(strict=True)) != str(base):
        _fail("C-D phase-base realpath is not one fixed absolute mapping")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    base_fd = root_fd = attempt_fd = primary_fd = seal_fd = -1
    try:
        base_fd = os.open(base, flags)
        base_metadata = os.fstat(base_fd)
        if (
            not stat.S_ISDIR(base_metadata.st_mode)
            or (base_metadata.st_dev, base_metadata.st_ino)
            != (baseline["phase_base_device"], baseline["phase_base_inode"])
        ):
            _fail("C-D phase-base device/inode mapping changed")
        root_fd = _open_directory_at(
            base_fd, admission_v1._ROOT_NAME, "C-D admission root"
        )
        route_attempt_id = _cid(payload["route_attempt_id"], "route attempt")
        root_entries = os.listdir(root_fd)
        if any(not _CONTENT_ID_PATTERN.fullmatch(name) for name in root_entries):
            _fail("C-D admission root contains temp, repair, or foreign entries")
        if route_attempt_id not in root_entries:
            _fail("C-D admission root lost its exact attempt mapping")
        attempt_fd = _open_directory_at(
            root_fd, route_attempt_id, "C-D admission attempt"
        )
        if set(os.listdir(attempt_fd)) != {admission_v1._ADMISSION_FILE}:
            _fail("C-D admission attempt contains temp, repair, or foreign entries")
        primary_fd = _open_regular_at(
            attempt_fd, admission_v1._ADMISSION_FILE, "C-D admission primary"
        )
        seal_name = f"{admission_v1._SEAL_PREFIX}{route_attempt_id}"
        seal_fd = _open_regular_at(base_fd, seal_name, "C-D admission base seal")
        primary_metadata = os.fstat(primary_fd)
        seal_metadata = os.fstat(seal_fd)
        if (
            (primary_metadata.st_dev, primary_metadata.st_ino)
            != (seal_metadata.st_dev, seal_metadata.st_ino)
            or primary_metadata.st_nlink != 2
            or seal_metadata.st_nlink != 2
            or primary_metadata.st_size != seal_metadata.st_size
        ):
            _fail("C-D admission primary/base-seal topology changed")
        primary_raw = _read_regular_fd(
            primary_fd, primary_metadata.st_size, "C-D admission primary"
        )
        seal_raw = _read_regular_fd(
            seal_fd, seal_metadata.st_size, "C-D admission base seal"
        )
        if (
            not hmac.compare_digest(primary_raw, seal_raw)
            or not hmac.compare_digest(primary_raw, admission.canonical_bytes)
        ):
            _fail("C-D admission durable bytes differ from the issuer-owned object")
        replayed = admission_v1._admission_from_raw(primary_raw)
        if replayed.admission_id != admission.admission_id:
            _fail("C-D admission durable content ID changed")
        current_base = os.stat(base, follow_symlinks=False)
        current_root = os.stat(
            admission_v1._ROOT_NAME, dir_fd=base_fd, follow_symlinks=False
        )
        current_attempt = os.stat(
            route_attempt_id, dir_fd=root_fd, follow_symlinks=False
        )
        if (
            (current_base.st_dev, current_base.st_ino)
            != (base_metadata.st_dev, base_metadata.st_ino)
            or (current_root.st_dev, current_root.st_ino)
            != (os.fstat(root_fd).st_dev, os.fstat(root_fd).st_ino)
            or (current_attempt.st_dev, current_attempt.st_ino)
            != (os.fstat(attempt_fd).st_dev, os.fstat(attempt_fd).st_ino)
        ):
            _fail("C-D admission durable directory mapping changed")
        pins = _DurableAdmissionPins(
            base,
            base_fd,
            root_fd,
            attempt_fd,
            primary_fd,
            seal_fd,
            route_attempt_id,
        )
        base_fd = root_fd = attempt_fd = primary_fd = seal_fd = -1
        return pins
    except OSError as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            "C-D admission durable read-only replay failed"
        ) from error
    finally:
        for descriptor in (seal_fd, primary_fd, attempt_fd, root_fd, base_fd):
            _close_fd_quietly(descriptor)


def _write_all(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(descriptor, raw[offset:])
        if written < 1:
            _fail("guardian marker write made no progress")
        offset += written


def _publish_irreversible_guardian_marker(
    pins: _DurableAdmissionPins,
    *,
    marker_document: Mapping[str, Any],
    crash_point: H1NativeCapabilityGuardianInitializationCrashPointV1,
) -> str:
    route_attempt_id = _cid(marker_document["route_attempt_id"], "route attempt")
    root_fd = attempt_fd = primary_fd = seal_fd = -1
    try:
        try:
            os.mkdir(_MARKER_ROOT_NAME, 0o700, dir_fd=pins.base_fd)
            os.fsync(pins.base_fd)
        except FileExistsError:
            pass
        root_fd = _open_directory_at(
            pins.base_fd, _MARKER_ROOT_NAME, "guardian marker root"
        )
        if any(not _CONTENT_ID_PATTERN.fullmatch(name) for name in os.listdir(root_fd)):
            _fail("guardian marker root contains temp, repair, or foreign entries")
        try:
            os.mkdir(route_attempt_id, 0o700, dir_fd=root_fd)
            os.fsync(root_fd)
        except FileExistsError:
            pass
        attempt_fd = _open_directory_at(
            root_fd, route_attempt_id, "guardian marker attempt"
        )
        attempt_entries = set(os.listdir(attempt_fd))
        seal_name = f"{_MARKER_SEAL_PREFIX}{route_attempt_id}"
        try:
            os.stat(seal_name, dir_fd=pins.base_fd, follow_symlinks=False)
            seal_exists = True
        except FileNotFoundError:
            seal_exists = False
        if _MARKER_FILE in attempt_entries or seal_exists:
            _fail("durable guardian marker already burned this V6 allocation")
        if attempt_entries:
            _fail("guardian marker attempt contains temp, repair, or foreign entries")
        payload = dict(marker_document)
        claimed = _cid(
            payload.pop("h1_native_capability_guardian_init_marker_id", None),
            "guardian initialization marker",
        )
        if claimed != _content_id(MARKER_DOMAIN, payload):
            _fail("guardian initialization marker identity changed before publication")
        raw = canonical_json_bytes(marker_document)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        primary_fd = os.open(_MARKER_FILE, flags, 0o400, dir_fd=attempt_fd)
        os.fchmod(primary_fd, 0o400)
        _write_all(primary_fd, raw)
        os.fsync(primary_fd)
        os.close(primary_fd)
        primary_fd = -1
        os.fsync(attempt_fd)
        if (
            crash_point
            is H1NativeCapabilityGuardianInitializationCrashPointV1.AFTER_PRIMARY_FSYNC_BEFORE_SEAL
        ):
            raise H1NativeCapabilityGuardianInjectedCrashV1(
                "injected crash after irreversible guardian marker primary"
            )
        os.link(
            _MARKER_FILE,
            seal_name,
            src_dir_fd=attempt_fd,
            dst_dir_fd=pins.base_fd,
            follow_symlinks=False,
        )
        os.fsync(pins.base_fd)
        primary_fd = _open_regular_at(
            attempt_fd, _MARKER_FILE, "guardian marker primary"
        )
        seal_fd = _open_regular_at(
            pins.base_fd, seal_name, "guardian marker base seal"
        )
        primary_metadata = os.fstat(primary_fd)
        seal_metadata = os.fstat(seal_fd)
        if (
            (primary_metadata.st_dev, primary_metadata.st_ino)
            != (seal_metadata.st_dev, seal_metadata.st_ino)
            or primary_metadata.st_nlink != 2
            or seal_metadata.st_nlink != 2
            or _read_regular_fd(primary_fd, primary_metadata.st_size, "guardian marker primary")
            != raw
            or _read_regular_fd(seal_fd, seal_metadata.st_size, "guardian marker base seal")
            != raw
        ):
            _fail("guardian marker primary/base-seal topology changed")
        return claimed
    except H1NativeCapabilityGuardianInjectedCrashV1:
        raise
    except OSError as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            "guardian marker publication failed closed"
        ) from error
    finally:
        for descriptor in (seal_fd, primary_fd, attempt_fd, root_fd):
            _close_fd_quietly(descriptor)


def _verify_irreversible_guardian_marker(
    pins: _DurableAdmissionPins,
    marker_document: Mapping[str, Any],
) -> str:
    """Independently replay the marker; publisher return values are untrusted."""

    route_attempt_id = _cid(marker_document["route_attempt_id"], "route attempt")
    expected_raw = canonical_json_bytes(marker_document)
    expected_id = _cid(
        marker_document["h1_native_capability_guardian_init_marker_id"],
        "guardian initialization marker",
    )
    root_fd = attempt_fd = primary_fd = seal_fd = -1
    try:
        root_fd = _open_directory_at(
            pins.base_fd, _MARKER_ROOT_NAME, "guardian marker root replay"
        )
        if any(
            not _CONTENT_ID_PATTERN.fullmatch(name)
            for name in os.listdir(root_fd)
        ):
            _fail("guardian marker root replay found a foreign entry")
        attempt_fd = _open_directory_at(
            root_fd, route_attempt_id, "guardian marker attempt replay"
        )
        if set(os.listdir(attempt_fd)) != {_MARKER_FILE}:
            _fail("guardian marker attempt replay is not exact")
        seal_name = f"{_MARKER_SEAL_PREFIX}{route_attempt_id}"
        primary_fd = _open_regular_at(
            attempt_fd, _MARKER_FILE, "guardian marker primary replay"
        )
        seal_fd = _open_regular_at(
            pins.base_fd, seal_name, "guardian marker base seal replay"
        )
        primary_metadata = os.fstat(primary_fd)
        seal_metadata = os.fstat(seal_fd)
        if (
            (primary_metadata.st_dev, primary_metadata.st_ino)
            != (seal_metadata.st_dev, seal_metadata.st_ino)
            or primary_metadata.st_nlink != 2
            or seal_metadata.st_nlink != 2
            or primary_metadata.st_size != seal_metadata.st_size
        ):
            _fail("guardian marker replay topology changed")
        primary_raw = _read_regular_fd(
            primary_fd, primary_metadata.st_size, "guardian marker primary replay"
        )
        seal_raw = _read_regular_fd(
            seal_fd, seal_metadata.st_size, "guardian marker base seal replay"
        )
        if (
            not hmac.compare_digest(primary_raw, expected_raw)
            or not hmac.compare_digest(seal_raw, expected_raw)
        ):
            _fail("guardian marker replay bytes differ from the exact request")
        replayed = _parse(primary_raw, "guardian marker replay")
        replay_payload = dict(replayed)
        replay_claimed = _cid(
            replay_payload.pop(
                "h1_native_capability_guardian_init_marker_id", None
            ),
            "guardian initialization marker replay",
        )
        if (
            replay_claimed != expected_id
            or _content_id(MARKER_DOMAIN, replay_payload) != expected_id
        ):
            _fail("guardian marker replay content ID changed")
        mappings = (
            (
                os.stat(
                    _MARKER_ROOT_NAME,
                    dir_fd=pins.base_fd,
                    follow_symlinks=False,
                ),
                os.fstat(root_fd),
            ),
            (
                os.stat(
                    route_attempt_id,
                    dir_fd=root_fd,
                    follow_symlinks=False,
                ),
                os.fstat(attempt_fd),
            ),
            (
                os.stat(
                    _MARKER_FILE,
                    dir_fd=attempt_fd,
                    follow_symlinks=False,
                ),
                primary_metadata,
            ),
            (
                os.stat(
                    seal_name,
                    dir_fd=pins.base_fd,
                    follow_symlinks=False,
                ),
                seal_metadata,
            ),
        )
        if any(
            (current.st_dev, current.st_ino) != (pinned.st_dev, pinned.st_ino)
            for current, pinned in mappings
        ):
            _fail("guardian marker replay namespace mapping changed")
        return replay_claimed
    except OSError as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            "guardian marker independent read-only replay failed"
        ) from error
    finally:
        for descriptor in (seal_fd, primary_fd, attempt_fd, root_fd):
            _close_fd_quietly(descriptor)


def _validate_cleanup_admission_binding(
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    admission: admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1,
    native_spec: receipts_v1.H1NativeReceiptJournalSpecV1,
    native_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
) -> Mapping[str, Any]:
    """Isolated adapter for the evolving C-D live-admission API.

    E1 consumes only the final issuer-owned immutable admission.  It does not
    mint or repair C-D, nor does it rely on the call signature used to create
    that admission.
    """

    lease = normal_v1._require_live_lease(lease)
    if (
        type(admission)
        is not admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1
        or type(native_spec) is not receipts_v1.H1NativeReceiptJournalSpecV1
        or type(native_handle) is not receipts_v1.H1NativeReceiptJournalHandleV1
    ):
        _fail("guardian initialization requires exact issuer-owned C-D and V6 inputs")
    payload = admission.payload
    receipt_payload = native_spec.payload
    required_equalities = {
        "logical_occurrence_id": receipt_payload["logical_occurrence_id"],
        "route_attempt_id": receipt_payload["route_attempt_id"],
        "decision_point_id": receipt_payload["decision_point_id"],
        "transaction_id": receipt_payload["transaction_id"],
        "h1_normal_prefix_spec_id": receipt_payload["h1_normal_prefix_spec_id"],
        "h1_normal_prefix_allocation_id": receipt_payload[
            "h1_normal_prefix_allocation_id"
        ],
        "h1_native_receipt_journal_spec_id": native_spec.spec_id,
        "h1_native_receipt_allocation_id": native_handle.allocation_id,
        "h1_attempt_execution_phase_spec_id": lease.phase_handle.spec.spec_id,
        "h1_attempt_phase_allocation_id": lease.phase_handle.allocation_id,
        "h1_attempt_rejection_gate_id": lease.rejection_gate.spec.gate_id,
    }
    if any(payload.get(key) != expected for key, expected in required_equalities.items()):
        _fail("C-D admission crossed its exact V6 or attempt context")
    if (
        payload.get("actual_v6_spec_allocation_bound") is not True
        or payload.get("preadmitted_before_normal_ordinal_1") is not True
        or payload.get("normal_completed_event_count_at_admission") != 0
        or payload.get("normal_next_ordinal_at_admission") != 1
        or payload.get("native_receipt_record_count_at_admission") != 0
        or payload.get("native_receipt_slot_count") != 12
        or payload.get("budget_sufficient_on_every_category") is not True
        or payload.get("cleanup_action_execution_authority_present") is not False
        or payload.get("native_cleanup_effect_authority_present") is not False
        or payload.get("official_execution_allowed") is not False
    ):
        _fail("C-D admission is not the exact pre-ordinal guardian prerequisite")
    baseline = payload.get("prospective_owner_cleanup_sidecar_baseline")
    if (
        type(baseline) is not dict
        or baseline.get("h1_shared_cap_profile_core_v3_id")
        != lease.owner.profile.profile_id
        or baseline.get("h1_shared_cap_owner_v3_runtime_id")
        != lease.owner.runtime_id
        or baseline.get("h1_shared_cap_owner_v4_wal_binding_id")
        != lease.owner.binding_id
        or baseline.get("c_b_owner_cutoff_sequence")
        != payload.get("c_b_owner_cutoff_sequence")
        or baseline.get("c_b_owner_cutoff_head_id")
        != payload.get("c_b_owner_cutoff_head_id")
    ):
        _fail("C-D admission crossed its live lease Owner authority")
    return payload


def initialize_h1_native_capability_guardian_v1(
    lease: normal_v1.H1PhaseAwareNormalPrefixLeaseV1,
    *,
    native_receipt_spec: receipts_v1.H1NativeReceiptJournalSpecV1,
    native_receipt_handle: receipts_v1.H1NativeReceiptJournalHandleV1,
    cleanup_budget_admission: admission_v1.H1FailedPrefixCleanupBudgetAdmissionV1,
    crash_point: H1NativeCapabilityGuardianInitializationCrashPointV1 | str = (
        H1NativeCapabilityGuardianInitializationCrashPointV1.NONE
    ),
) -> H1NativeCapabilityGuardianV1:
    """Create one permanently marked guardian from any exact pristine lease."""

    _reject_public_reentry()
    lease = normal_v1._require_live_lease(lease)
    admission_payload = _validate_cleanup_admission_binding(
        lease,
        cleanup_budget_admission,
        native_receipt_spec,
        native_receipt_handle,
    )
    receipts_v1._require_broker(native_receipt_handle)
    if native_receipt_handle.spec.spec_id != native_receipt_spec.spec_id:
        _fail("guardian initialization crossed the V6 spec and allocation")
    try:
        crash = H1NativeCapabilityGuardianInitializationCrashPointV1(crash_point)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1NativeCapabilityGuardianV1Error(
            "guardian initialization crash point is invalid"
        ) from error
    _probe_kcmp_file()
    process_id = os.getpid()
    broker_thread = threading.current_thread()
    thread_diagnostic_id = threading.get_native_id()
    start_ticks = _process_start_ticks()
    allocation_key = (native_receipt_handle.allocation_id, process_id, start_ticks)

    normal_handle = native_receipt_handle.normal_handle
    if normal_handle is not lease.handle:
        _fail("guardian initialization crossed the live normal-prefix lease")
    owner_root_fd = owner_directory_fd = -1
    native_lock_fd = native_cursor_fd = -1
    admission_pins: _DurableAdmissionPins | None = None
    spec: H1NativeCapabilityGuardianSpecV1 | None = None
    marker_id: str | None = None
    try:
        normal_state = normal_v1._replay_journal_locked(
            normal_handle,
            lease._journal_root_fd,
            lease._journal_directory_fd,
            lease._journal_cursor_fd,
            repair=False,
        )
        normal_snapshot = normal_v1._snapshot_from_state(normal_handle, normal_state)
        normal_document = normal_snapshot.document
        if (
            normal_document["status"] != normal_v1.H1NormalPrefixStatusV1.READY.value
            or normal_document["completed_event_count"] != 0
            or normal_document["next_ordinal"] != 1
            or normal_document["dangling_intent_id"]
            != _typed_null("NO_DANGLING_INTENT")
        ):
            _fail("native capability guardian must initialize before normal ordinal 1")
        gate_state, gate_commit, gate_ack = rejection_v1._observe_gate_locked(
            lease.rejection_gate,
            lease._gate_directory_fd,
            advance_cursor=False,
        )
        if (
            gate_state is not rejection_v1.H1AttemptRejectionGateStateV1.OPEN
            or gate_commit is not None
            or gate_ack is not None
            or admission_payload.get("c_b_gate_state_at_preadmission")
            != rejection_v1.H1AttemptRejectionGateStateV1.OPEN.value
        ):
            _fail("guardian initialization requires the live pristine OPEN gate")
        gate_snapshot = rejection_v1.H1AttemptRejectionGateReplaySnapshotV1(
            rejection_v1._REPLAY_SNAPSHOT_ISSUER,
            lease.rejection_gate.spec.gate_id,
            gate_state,
            gate_commit,
            gate_ack,
        )
        (
            owner_root_fd,
            owner_directory_fd,
            owner_state,
            _owner_storage_before,
        ) = sidecar_v1._require_stable_owner_readonly_locked(lease.owner)
        gate_join = owner_v3._validate_owner_gate_join(
            lease.owner.owner, owner_state, gate_snapshot
        )
        if (
            owner_state.pending_cursor is not None
            or owner_v3._incomplete_pair_frontier(owner_state) is not None
            or gate_join.recovery_required
            or gate_join.status.value
            != admission_payload.get("c_b_gate_owner_join_status_at_preadmission")
            or owner_state.sequence
            != admission_payload.get("c_b_owner_cutoff_sequence")
            or owner_state.head_id
            != admission_payload.get("c_b_owner_cutoff_head_id")
        ):
            _fail("guardian initialization crossed the admitted live Owner/gate cutoff")
        normal_evidence = receipts_v1._normal_evidence_from_state(normal_state)
        native_lock_fd, native_cursor_fd, native_state = receipts_v1._with_locked(
            native_receipt_handle,
            normal_evidence=normal_evidence,
            repair=False,
        )
        declared_slots = receipts_v1._declared_slots_for_handle(native_receipt_handle)
        if (
            len(declared_slots) != 12
            or native_state.records
            or native_state.starts
            or native_state.results
            or native_state.resolutions
            or native_state.cutoff is not None
            or len(native_state.cursor_rows) != 1
        ):
            _fail("native capability guardian saw a non-pristine V6 allocation")
        genesis = native_state.cursor_rows[0]["h1_native_receipt_cursor_id"]
        if admission_payload.get("native_receipt_genesis_cursor_id") != genesis:
            _fail("C-D admission crossed the exact V6 genesis cursor")
        admission_pins = _pin_and_replay_durable_cleanup_admission(
            cleanup_budget_admission
        )
        spec_payload = {
            "schema": "acfqp.k7_h1_native_capability_guardian_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": admission_payload["logical_occurrence_id"],
            "route_attempt_id": admission_payload["route_attempt_id"],
            "decision_point_id": admission_payload["decision_point_id"],
            "transaction_id": admission_payload["transaction_id"],
            "h1_normal_prefix_spec_id": normal_handle.spec.spec_id,
            "h1_normal_prefix_allocation_id": normal_handle.allocation_id,
            "h1_attempt_execution_phase_spec_id": lease.phase_handle.spec.spec_id,
            "h1_attempt_phase_allocation_id": lease.phase_handle.allocation_id,
            "h1_attempt_rejection_gate_id": lease.rejection_gate.spec.gate_id,
            "h1_shared_cap_profile_core_v3_id": lease.owner.profile.profile_id,
            "h1_shared_cap_owner_v3_runtime_id": lease.owner.runtime_id,
            "h1_shared_cap_owner_v4_wal_binding_id": lease.owner.binding_id,
            "h1_native_receipt_journal_spec_id": native_receipt_spec.spec_id,
            "h1_native_receipt_allocation_id": native_receipt_handle.allocation_id,
            "h1_failed_prefix_cleanup_budget_admission_id": (
                cleanup_budget_admission.admission_id
            ),
            "native_receipt_genesis_cursor_id": genesis,
            "predeclared_native_resource_slot_ids": [
                row["h1_native_resource_slot_id"] for row in declared_slots
            ],
            "broker_process_id": process_id,
            "broker_thread_diagnostic_id": thread_diagnostic_id,
            "broker_process_start_ticks": start_ticks,
            "initialized_before_normal_ordinal_1": True,
            "exact_live_pristine_lease_revalidated": True,
            "durable_c_d_primary_base_seal_replayed_read_only": True,
            "same_c_d_creation_lease_required": False,
            "linux_kcmp_file_identity_required": True,
            "fstat_and_fdinfo_provenance_required": True,
            "master_witness_registry_anchor_cloexec_required": True,
            "irreversible_primary_base_seal_initialization_marker_required": True,
            "guarded_binding_is_live_process_local_token": True,
            "binding_document_is_durable_capability_authority": False,
            "raw_descriptor_fields_serialized": False,
            "generation_secret_serialized": False,
            "direct_v6_receipt_confers_live_capability": False,
            "broker_restart_recovery_present": False,
            "cutoff_cleanup_token_authority_present": False,
            "cleanup_action_journal_present": False,
            "native_cleanup_effect_authority_present": False,
            "production_output_leaf_authority_present": False,
            "production_execution_authority_present": False,
            "current_access_authority_present": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
        }
        spec = H1NativeCapabilityGuardianSpecV1(
            _SPEC_ISSUER, canonical_json_bytes(spec_payload)
        )
        marker_payload = {
            "schema": "acfqp.k7_h1_native_capability_guardian_init_marker.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": admission_payload["logical_occurrence_id"],
            "route_attempt_id": admission_payload["route_attempt_id"],
            "decision_point_id": admission_payload["decision_point_id"],
            "transaction_id": admission_payload["transaction_id"],
            "h1_native_capability_guardian_spec_id": spec.spec_id,
            "h1_native_receipt_journal_spec_id": native_receipt_spec.spec_id,
            "h1_native_receipt_allocation_id": native_receipt_handle.allocation_id,
            "h1_failed_prefix_cleanup_budget_admission_id": (
                cleanup_budget_admission.admission_id
            ),
            "native_receipt_genesis_cursor_id": genesis,
            "phase_base_realpath": str(admission_pins.base),
            "broker_process_id": process_id,
            "broker_thread_diagnostic_id": thread_diagnostic_id,
            "broker_process_start_ticks": start_ticks,
            "thread_object_identity_serialized": False,
            "marker_is_irreversible_one_shot_tombstone": True,
            "broker_restart_recovery_present": False,
            "native_cleanup_effect_authority_present": False,
            "current_access_authority_present": False,
            "formal_counter_records_issued": False,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
        }
        marker_document = {
            **marker_payload,
            "h1_native_capability_guardian_init_marker_id": _content_id(
                MARKER_DOMAIN, marker_payload
            ),
        }
        marker_id = _publish_irreversible_guardian_marker(
            admission_pins,
            marker_document=marker_document,
            crash_point=crash,
        )
        if marker_id != marker_document[
            "h1_native_capability_guardian_init_marker_id"
        ]:
            _fail("guardian marker publisher returned the wrong durable identity")
        if _verify_irreversible_guardian_marker(
            admission_pins, marker_document
        ) != marker_id:
            _fail("guardian marker independent replay returned the wrong identity")
        admission_pins.verify_namespace_mapping(
            cleanup_budget_admission.canonical_bytes
        )
    finally:
        try:
            if admission_pins is not None:
                admission_pins.close()
        finally:
            try:
                if native_lock_fd >= 0:
                    receipts_v1._unlock(native_lock_fd, native_cursor_fd)
            finally:
                try:
                    if owner_directory_fd >= 0:
                        os.close(owner_directory_fd)
                finally:
                    if owner_root_fd >= 0:
                        os.close(owner_root_fd)

    # The V6 and Owner storage locks above are fully released before the
    # process-wide capability mutex is entered.  No RLock -> storage-lock path
    # exists in this module.
    if spec is None or marker_id is None:  # pragma: no cover - control invariant
        _fail("guardian initialization produced no sealed spec and marker")
    with _REGISTRY_LOCK:
        if allocation_key in _GUARDED_ALLOCATIONS:
            _fail("process registry conflicts with the newly burned marker")
        guardian = H1NativeCapabilityGuardianV1(
            _GUARDIAN_ISSUER,
            spec=spec,
            native_handle=native_receipt_handle,
            admission=cleanup_budget_admission,
            incarnation=object(),
            marker_id=marker_id,
            broker_thread=broker_thread,
            broker_thread_diagnostic_id=thread_diagnostic_id,
            broker_process_start_ticks=start_ticks,
        )
        _GUARDED_ALLOCATIONS.add(allocation_key)
        _LIVE_GUARDIANS[allocation_key] = guardian
        return guardian


def observe_h1_guarded_native_present_v1(
    raw_descriptor: int,
) -> H1NativeCapabilityAcquisitionV1:
    active = _require_active_acquisition()
    if type(raw_descriptor) is not int or raw_descriptor < 0:
        _fail("guarded native descriptor must be one nonnegative integer")
    cell = _adopt_descriptor_immediately(
        active.guardian,
        slot_key=active.slot_key,
        kind=active.kind,
        raw_descriptor=raw_descriptor,
    )
    try:
        acquisition = H1NativeCapabilityAcquisitionV1(
            _ACQUISITION_ISSUER,
            resolution_kind=receipts_v1.H1NativeResolutionKindV1.KNOWN_PRESENT,
            capability_kind=active.kind,
            cell=cell,
            absence_reason=None,
            guardian_incarnation=active.guardian._incarnation,
            slot_key=active.slot_key,
        )
        active.issued.append(acquisition)
        return acquisition
    except BaseException:
        with _REGISTRY_LOCK:
            _revoke_cell_locked(
                active.guardian,
                cell,
                "PRESENT_OBSERVATION_REGISTRATION_FAILED",
            )
        raise


def observe_h1_guarded_native_absent_v1(
    *, reason: str
) -> H1NativeCapabilityAcquisitionV1:
    active = _require_active_acquisition()
    acquisition = H1NativeCapabilityAcquisitionV1(
        _ACQUISITION_ISSUER,
        resolution_kind=receipts_v1.H1NativeResolutionKindV1.KNOWN_ABSENT,
        capability_kind=active.kind,
        cell=None,
        absence_reason=_nonempty(reason, "guarded native absence reason"),
        guardian_incarnation=active.guardian._incarnation,
        slot_key=active.slot_key,
    )
    active.issued.append(acquisition)
    return acquisition


def _verify_live_cell_locked(
    guardian: H1NativeCapabilityGuardianV1, cell: _LiveCapabilityCell
) -> None:
    anchor = _ANCHOR_FDS.get((guardian._registry_key, cell.slot_key), -1)
    if (
        type(cell._generation_secret) is not bytes
        or len(cell._generation_secret) != 32
        or cell._master_fd < 0
        or cell._witness_fd < 0
        or anchor < 0
        or len({cell._master_fd, cell._witness_fd, anchor}) != 3
    ):
        _fail("guardian live-cell generation or descriptor triple changed")
    for descriptor in (cell._master_fd, cell._witness_fd, anchor):
        _require_cloexec(descriptor)
        if (
            _stat_fingerprint(descriptor) != cell._stat_fingerprint
            or _fdinfo(descriptor, cell.kind) != cell._fdinfo_fingerprint
        ):
            _fail("guardian descriptor crossed fstat or fdinfo provenance")
    if (
        not _kcmp_file(cell._master_fd, cell._witness_fd)
        or not _kcmp_file(cell._master_fd, anchor)
        or not _kcmp_file(cell._witness_fd, anchor)
    ):
        _fail("guardian descriptor was reused, replaced, or crossed its OFD provenance")


def _verify_live_cell(
    guardian: H1NativeCapabilityGuardianV1, cell: _LiveCapabilityCell
) -> None:
    with _REGISTRY_LOCK:
        _verify_live_cell_locked(guardian, cell)


def _adopt_descriptor_immediately(
    guardian: H1NativeCapabilityGuardianV1,
    *,
    slot_key: str,
    kind: receipts_v1.H1NativeCapabilityKindV1,
    raw_descriptor: int,
) -> _LiveCapabilityCell:
    master = witness = anchor = -1
    installed = False
    close_observed = True
    with _REGISTRY_LOCK:
        _PENDING_FDS.add(raw_descriptor)
        try:
            state = guardian._slot_states[slot_key]
            if state.cell is not None:
                _fail("guardian native slot already has one pinned observation")
            for registered in _LIVE_GUARDIANS.values():
                for existing in registered._slot_states.values():
                    if existing.cell is not None:
                        _verify_live_cell_locked(registered, existing.cell)
                        if raw_descriptor in {
                            existing.cell._master_fd,
                            existing.cell._witness_fd,
                            _ANCHOR_FDS.get(
                                (registered._registry_key, existing.cell.slot_key), -1
                            ),
                        }:
                            # This number is Guardian-owned, not a caller-owned
                            # original.  Reject it without closing a live alias.
                            close_observed = False
                            _fail(
                                "guardian internal descriptor alias cannot be resubmitted"
                            )
            _stat_fingerprint(raw_descriptor)
            master = fcntl.fcntl(raw_descriptor, _F_DUPFD_CLOEXEC, 0)
            _PENDING_FDS.add(master)
            witness = fcntl.fcntl(raw_descriptor, _F_DUPFD_CLOEXEC, 0)
            _PENDING_FDS.add(witness)
            anchor = fcntl.fcntl(raw_descriptor, _F_DUPFD_CLOEXEC, 0)
            _PENDING_FDS.add(anchor)
            if len({raw_descriptor, master, witness, anchor}) != 4:
                _fail("guardian adoption descriptor set is not distinct")
            for descriptor in (master, witness, anchor):
                _require_cloexec(descriptor)
                if not _kcmp_file(raw_descriptor, descriptor):
                    _fail("guardian descriptor triple is not the observed exact OFD")
            if (
                not _kcmp_file(master, witness)
                or not _kcmp_file(master, anchor)
                or not _kcmp_file(witness, anchor)
            ):
                _fail("guardian master/witness/anchor are not one exact OFD")
            fingerprint = _stat_fingerprint(master)
            fdinfo = _fdinfo(master, kind)
            for descriptor in (witness, anchor):
                if (
                    _stat_fingerprint(descriptor) != fingerprint
                    or _fdinfo(descriptor, kind) != fdinfo
                ):
                    _fail("guardian descriptor triple crossed fstat/fdinfo provenance")
            for registered in _LIVE_GUARDIANS.values():
                if registered._poisoned:
                    continue
                for existing in registered._slot_states.values():
                    if existing.cell is not None:
                        _verify_live_cell_locked(registered, existing.cell)
                        if _kcmp_file(master, existing.cell._master_fd):
                            _fail(
                                "one open-file description cannot cross native slots "
                                "or V6 allocations in one broker process"
                            )
            cell = _LiveCapabilityCell(
                master_fd=master,
                witness_fd=witness,
                stat_fingerprint=fingerprint,
                fdinfo_fingerprint=fdinfo,
                generation_secret=secrets.token_bytes(32),
                kind=kind,
                slot_key=slot_key,
            )
            state.cell = cell
            state.unresolved_reason = "PRESENT_OBSERVED_AND_PINNED_BEFORE_CALLBACK_RETURN"
            _ANCHOR_FDS[(guardian._registry_key, slot_key)] = anchor
            for descriptor in (master, witness, anchor):
                _PENDING_FDS.discard(descriptor)
            master = witness = anchor = -1
            installed = True
            return cell
        finally:
            _PENDING_FDS.discard(raw_descriptor)
            if close_observed:
                _close_fd_quietly(raw_descriptor)
            if not installed:
                for descriptor in (master, witness, anchor):
                    _PENDING_FDS.discard(descriptor)
                    _close_fd_quietly(descriptor)


def _revoke_acquisitions(
    guardian: H1NativeCapabilityGuardianV1,
    issued: list[H1NativeCapabilityAcquisitionV1],
    *,
    except_object: H1NativeCapabilityAcquisitionV1 | None = None,
) -> None:
    with _REGISTRY_LOCK:
        for item in issued:
            if item is except_object:
                continue
            item._consumed = True
            cell = item._cell
            item._cell = None
            if cell is not None:
                _revoke_cell_locked(
                    guardian,
                    cell,
                    "ACQUISITION_REVOKED_BEFORE_CALLBACK_RESULT",
                )


def _revoke_cell_locked(
    guardian: H1NativeCapabilityGuardianV1,
    cell: _LiveCapabilityCell,
    reason: str,
) -> None:
    state = guardian._slot_states.get(cell.slot_key)
    if state is not None and state.cell is cell:
        state.cell = None
        state.unresolved_reason = reason
    anchor = _ANCHOR_FDS.pop((guardian._registry_key, cell.slot_key), -1)
    _close_fd_quietly(anchor)
    cell._close_master_witness()


def execute_h1_guarded_native_acquisition_once_v1(
    guardian: H1NativeCapabilityGuardianV1,
    *,
    slot_key: str,
    h1_normal_site_intent_id: str,
    acquisition: Callable[[], H1NativeCapabilityAcquisitionV1],
) -> H1GuardedPendingNativeBindingV1:
    """Run the exact V6 START/callback/result path and retain any live OFD."""

    _reject_public_reentry()
    _require_guardian(guardian)
    slots = receipts_v1._declared_slots_by_key_for_handle(guardian._native_handle)
    slot = slots.get(slot_key)
    if slot is None or not callable(acquisition):
        _fail("guarded acquisition names an unknown slot or non-callable")
    intent_id = _cid(h1_normal_site_intent_id, "normal-site intent")
    with _REGISTRY_LOCK:
        state = guardian._slot_states[slot_key]
        if (
            state.start_id is not None
            or state.pending_result_id is not None
            or state.cell is not None
        ):
            _fail("guarded acquisition slot already started and cannot be replayed")
    kind = receipts_v1.H1NativeCapabilityKindV1(slot["capability_kind"])

    callback_cell = _ActiveAcquisitionCell(guardian, slot_key, kind)

    def sealed_callback() -> receipts_v1.H1NativeCallbackObservationV1:
        if callback_cell.active or callback_cell.window_incarnation is not None:
            _fail("guardian acquisition callback window was replayed")
        callback_cell.active = True
        callback_cell.window_incarnation = object()
        token = _ACTIVE_ACQUISITION.set(callback_cell)
        returned: H1NativeCapabilityAcquisitionV1 | None = None
        try:
            try:
                returned = acquisition()
            except BaseException:
                _revoke_acquisitions(guardian, callback_cell.issued)
                raise
        finally:
            callback_cell.active = False
            callback_cell.window_incarnation = None
            _ACTIVE_ACQUISITION.reset(token)
        if (
            type(returned) is not H1NativeCapabilityAcquisitionV1
            or len(callback_cell.issued) != 1
            or callback_cell.issued[0] is not returned
            or returned._consumed
            or returned._guardian_incarnation is not guardian._incarnation
            or returned._slot_key != slot_key
            or returned._process_id != os.getpid()
            or returned._thread is not threading.current_thread()
            or returned.capability_kind is not kind
        ):
            _revoke_acquisitions(guardian, callback_cell.issued)
            _fail("acquisition returned no unique sealed guardian observation")
        returned._consumed = True
        if returned.resolution_kind is receipts_v1.H1NativeResolutionKindV1.KNOWN_PRESENT:
            live = returned._cell
            with _REGISTRY_LOCK:
                if live is None or state.cell is not live:
                    _fail("present guardian observation lost its immediately pinned cell")
                _verify_live_cell_locked(guardian, live)
                state.unresolved_reason = "PRESENT_RESULT_NOT_YET_EVENT_BOUND"
            return receipts_v1.observe_h1_native_present_v1(
                live._master_fd, capability_kind=kind
            )
        if returned.resolution_kind is receipts_v1.H1NativeResolutionKindV1.KNOWN_ABSENT:
            with _REGISTRY_LOCK:
                if returned._cell is not None or state.cell is not None:
                    _fail("absent guardian observation conflicts with a pinned cell")
                state.unresolved_reason = "ABSENCE_RESULT_NOT_YET_EVENT_BOUND"
            return receipts_v1.observe_h1_native_absent_v1(
                capability_kind=kind,
                reason=_nonempty(returned.absence_reason, "guarded absence reason"),
            )
        _fail("guardian acquisition resolution kind is not closed")

    try:
        pending = receipts_v1.execute_h1_native_resource_callback_once_v1(
            guardian._native_handle,
            slot_key=slot_key,
            h1_normal_site_intent_id=intent_id,
            callback=sealed_callback,
        )
        document = pending.document
        if document.get("slot_key") != slot_key:
            _fail("V6 pending result crossed its guardian slot")
        start_id = _cid(
            document.get("h1_native_callback_start_id"), "native callback start"
        )
        result_id = pending.result_id
    except BaseException:
        # V6 START may be durable and non-replayable, but an unbound local
        # adoption is not durable authority.  Revoke every pinned alias on all
        # callback/result exceptions.
        _revoke_acquisitions(guardian, callback_cell.issued)
        with _REGISTRY_LOCK:
            state.unresolved_reason = (
                "V6_START_OR_RESULT_DID_NOT_YIELD_GUARDIAN_PENDING"
            )
        raise
    with _REGISTRY_LOCK:
        state.start_id = start_id
        state.pending_result_id = result_id
    return H1GuardedPendingNativeBindingV1(
        _PENDING_ISSUER,
        guardian_incarnation=guardian._incarnation,
        slot_key=slot_key,
        native_pending=pending,
    )


def bind_h1_guarded_native_result_to_normal_event_v1(
    guardian: H1NativeCapabilityGuardianV1,
    *,
    pending_binding: H1GuardedPendingNativeBindingV1,
    normal_site_event: normal_v1.H1NormalSiteEventCommitV1,
) -> H1GuardedNativeBindingV1:
    """Bind the exact pending V6 result and then seal the live guardian join."""

    _reject_public_reentry()
    _require_guardian(guardian)
    if (
        type(pending_binding) is not H1GuardedPendingNativeBindingV1
        or pending_binding._guardian_incarnation is not guardian._incarnation
        or pending_binding._process_id != os.getpid()
        or pending_binding._thread is not threading.current_thread()
        or pending_binding._bound
    ):
        _fail("pending native binding crossed guardian, process, thread, or use")
    slot_key = pending_binding._slot_key
    with _REGISTRY_LOCK:
        state = guardian._slot_states.get(slot_key)
        if (
            state is None
            or state.pending_result_id != pending_binding.result_id
            or state.binding_document is not None
        ):
            _fail("pending native binding crossed its exact guardian slot")

    resolution = receipts_v1.bind_h1_native_callback_result_to_normal_event_v1(
        guardian._native_handle,
        pending_result=pending_binding._native_pending,
        normal_site_event=normal_site_event,
    )
    pending_binding._bound = True
    if type(resolution) is receipts_v1.H1NativeResourceReceiptV1:
        with _REGISTRY_LOCK:
            if state.cell is None:
                state.unresolved_reason = "V6_PRESENT_RECEIPT_HAS_NO_LIVE_GUARDIAN_CELL"
                _fail("present V6 receipt has no live guardian capability")
            try:
                _verify_live_cell_locked(guardian, state.cell)
            except ConstructionK7H1NativeCapabilityGuardianV1Error:
                state.status = H1NativeCapabilityGuardianStatusV1.UNRESOLVED
                state.unresolved_reason = "LIVE_DESCRIPTOR_PROVENANCE_FAILED_AFTER_V6_RECEIPT"
                raise
        resolution_document = resolution.document
        resolution_id = resolution.receipt_id
        with _REGISTRY_LOCK:
            state.status = H1NativeCapabilityGuardianStatusV1.PRESENT_LIVE
            state.unresolved_reason = "NONE_PRESENT_LIVE"
        live_pair_verified = True
    elif type(resolution) is dict:
        with _REGISTRY_LOCK:
            if state.cell is not None:
                state.unresolved_reason = "V6_ABSENCE_RESOLUTION_CONFLICTS_WITH_LIVE_CELL"
                _fail("absent V6 resolution conflicts with a live guardian capability")
        resolution_document = dict(resolution)
        resolution_id = _cid(
            resolution_document.get("h1_native_absence_resolution_id"),
            "native absence resolution",
        )
        with _REGISTRY_LOCK:
            state.status = H1NativeCapabilityGuardianStatusV1.ABSENT
            state.unresolved_reason = "NONE_KNOWN_ABSENT"
        live_pair_verified = False
    else:  # pragma: no cover - V6 return-type invariant
        _fail("V6 returned no typed receipt or absence resolution")

    binding_payload = {
        "schema": "acfqp.k7_h1_native_capability_guardian_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_native_capability_guardian_spec_id": guardian.spec.spec_id,
        "h1_native_capability_guardian_init_marker_id": guardian._marker_id,
        "h1_failed_prefix_cleanup_budget_admission_id": guardian._admission.admission_id,
        "h1_native_receipt_journal_spec_id": guardian._native_handle.spec.spec_id,
        "h1_native_receipt_allocation_id": guardian._native_handle.allocation_id,
        "logical_occurrence_id": guardian.spec.payload["logical_occurrence_id"],
        "route_attempt_id": guardian.spec.payload["route_attempt_id"],
        "decision_point_id": guardian.spec.payload["decision_point_id"],
        "transaction_id": guardian.spec.payload["transaction_id"],
        "slot_key": slot_key,
        "h1_native_callback_start_id": state.start_id,
        "h1_native_callback_result_id": state.pending_result_id,
        "h1_native_resolution_id": resolution_id,
        "h1_normal_site_event_commit_id": resolution_document[
            "h1_normal_site_event_commit_id"
        ],
        "guardian_status": state.status.value,
        "live_master_witness_same_ofd_verified": live_pair_verified,
        "live_master_witness_registry_anchor_same_ofd_verified": (
            live_pair_verified
        ),
        "fstat_fdinfo_provenance_verified": live_pair_verified,
        "descriptor_cloexec_verified": live_pair_verified,
        "raw_descriptor_fields_serialized": False,
        "generation_secret_serialized": False,
        "binding_requires_live_process_local_guardian": True,
        "binding_document_is_durable_capability_authority": False,
        "direct_v6_receipt_confers_live_capability": False,
        "cutoff_cleanup_token_authority_present": False,
        "cleanup_action_journal_present": False,
        "native_cleanup_effect_authority_present": False,
        "production_output_leaf_authority_present": False,
        "production_execution_authority_present": False,
        "current_access_authority_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }
    binding_document = {
        **binding_payload,
        "h1_native_capability_guardian_binding_id": _content_id(
            BINDING_DOMAIN, binding_payload
        ),
    }
    with _REGISTRY_LOCK:
        state.resolution_id = resolution_id
        state.binding_document = binding_document
    return H1GuardedNativeBindingV1(
        _BOUND_ISSUER,
        document_bytes=canonical_json_bytes(binding_document),
        guardian=guardian,
        slot_key=slot_key,
    )


def snapshot_h1_native_capability_guardian_v1(
    guardian: H1NativeCapabilityGuardianV1,
) -> dict[str, Any]:
    """Verify V6 first, then verify each process-local live descriptor triple."""

    _reject_public_reentry()
    _require_guardian(guardian)
    # No Guardian mutex is held while V6 takes its journal locks.  E1 is
    # broker-thread-only, so the following in-memory read cannot race a legal
    # guardian operation.
    replay = receipts_v1.replay_h1_native_receipt_journal_v1(
        guardian._native_handle
    )
    rows: list[dict[str, Any]] = []
    with _REGISTRY_LOCK:
        for slot in receipts_v1._declared_slots_for_handle(guardian._native_handle):
            key = slot["slot_key"]
            state = guardian._slot_states[key]
            v6_resolution = replay["slot_resolutions"][key]
            status = state.status
            reason = state.unresolved_reason
            if state.cell is not None:
                try:
                    _verify_live_cell_locked(guardian, state.cell)
                except ConstructionK7H1NativeCapabilityGuardianV1Error:
                    state.status = H1NativeCapabilityGuardianStatusV1.UNRESOLVED
                    state.unresolved_reason = "LIVE_DESCRIPTOR_PROVENANCE_INVALIDATED"
                    raise
            if state.binding_document is None:
                status = H1NativeCapabilityGuardianStatusV1.UNRESOLVED
                if v6_resolution == receipts_v1.H1NativeResolutionKindV1.KNOWN_PRESENT.value:
                    reason = "DIRECT_V6_PRESENT_RECEIPT_WITHOUT_GUARDIAN_BINDING"
                elif v6_resolution == receipts_v1.H1NativeResolutionKindV1.KNOWN_ABSENT.value:
                    reason = "DIRECT_V6_ABSENCE_WITHOUT_GUARDIAN_BINDING"
                elif v6_resolution == receipts_v1.H1NativeResolutionKindV1.UNRESOLVED.value:
                    reason = "V6_CALLBACK_STARTED_BUT_GUARDIAN_BINDING_UNRESOLVED"
            elif status is H1NativeCapabilityGuardianStatusV1.PRESENT_LIVE:
                if v6_resolution != receipts_v1.H1NativeResolutionKindV1.KNOWN_PRESENT.value:
                    _fail("guardian present binding crossed the V6 resolution state")
                if state.cell is None:
                    _fail("guardian present binding lost its live cell")
            elif status is H1NativeCapabilityGuardianStatusV1.ABSENT:
                if v6_resolution != receipts_v1.H1NativeResolutionKindV1.KNOWN_ABSENT.value:
                    _fail("guardian absence binding crossed the V6 resolution state")
            rows.append(
                {
                    "slot_key": key,
                    "h1_native_resource_slot_id": slot["h1_native_resource_slot_id"],
                    "capability_kind": slot["capability_kind"],
                    "guardian_status": status.value,
                    "unresolved_reason": reason,
                    "v6_resolution": v6_resolution,
                    "h1_native_capability_guardian_binding_id": (
                        state.binding_document[
                            "h1_native_capability_guardian_binding_id"
                        ]
                        if state.binding_document is not None
                        else _typed_null("NO_GUARDIAN_BINDING")
                    ),
                    "raw_descriptor_fields_serialized": False,
                    "generation_secret_serialized": False,
                    "live_registry_anchor_required": (
                        status
                        is H1NativeCapabilityGuardianStatusV1.PRESENT_LIVE
                    ),
                }
            )
    return {
        "schema": "acfqp.k7_h1_native_capability_guardian_snapshot.v1",
        "h1_native_capability_guardian_spec_id": guardian.spec.spec_id,
        "h1_native_capability_guardian_init_marker_id": guardian._marker_id,
        "h1_failed_prefix_cleanup_budget_admission_id": guardian._admission.admission_id,
        "h1_native_receipt_journal_spec_id": guardian._native_handle.spec.spec_id,
        "h1_native_receipt_allocation_id": guardian._native_handle.allocation_id,
        "slot_states": rows,
        "raw_descriptor_fields_serialized": False,
        "generation_secret_serialized": False,
        "broker_restart_recovery_present": False,
        "cutoff_cleanup_token_authority_present": False,
        "cleanup_action_journal_present": False,
        "native_cleanup_effect_authority_present": False,
        "production_output_leaf_authority_present": False,
        "production_execution_authority_present": False,
        "current_access_authority_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "official_execution_allowed": False,
    }


__all__ = (
    "BROKER_RESTART_RECOVERY_PRESENT",
    "CALLER_ORIGINAL_DESCRIPTOR_CLOSED_AFTER_ADOPTION",
    "CLEANUP_ACTION_JOURNAL_PRESENT",
    "CURRENT_ACCESS_AUTHORITY_PRESENT",
    "CUTOFF_CLEANUP_TOKEN_AUTHORITY_PRESENT",
    "DIRECT_V6_RECEIPT_CONFERS_LIVE_CAPABILITY",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "GUARDIAN_PROCESS_THREAD_INCARNATION_BOUND",
    "ConstructionK7H1NativeCapabilityGuardianV1Error",
    "H1GuardedNativeBindingV1",
    "H1GuardedPendingNativeBindingV1",
    "H1NativeCapabilityAcquisitionV1",
    "H1NativeCapabilityGuardianInjectedCrashV1",
    "H1NativeCapabilityGuardianInitializationCrashPointV1",
    "H1NativeCapabilityGuardianSpecV1",
    "H1NativeCapabilityGuardianStatusV1",
    "H1NativeCapabilityGuardianV1",
    "LINUX_KCMP_FILE_IDENTITY_REQUIRED",
    "NATIVE_CAPABILITY_GUARDIAN_PRESENT",
    "NATIVE_CLEANUP_EFFECT_AUTHORITY_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PRODUCTION_EXECUTION_AUTHORITY_PRESENT",
    "PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT",
    "bind_h1_guarded_native_result_to_normal_event_v1",
    "execute_h1_guarded_native_acquisition_once_v1",
    "initialize_h1_native_capability_guardian_v1",
    "observe_h1_guarded_native_absent_v1",
    "observe_h1_guarded_native_present_v1",
    "snapshot_h1_native_capability_guardian_v1",
)
