"""Live two-role clone3 probe consuming one prepared outer-broker session.

This is deliberately a probe, not the production K7 protocol.  It proves two
role-ordered, from-birth launches and preserves an unrollbackable 0/1/2 native
prefix.  It emits no CounterRecord, formal vector, terminal, or certificate.
"""

from __future__ import annotations

import ctypes
from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import hashlib
import mmap
import os
import platform
import signal
import threading
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as atomic_v1
from acfqp import v075_k7_outer_attempt_broker_preparation_v1 as preparation_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_TWO_ROLE_BROKER_FAILURE_PREFIX_V1_DOMAIN,
    V075_K7_TWO_ROLE_BROKER_PROBE_PROFILE_V1_DOMAIN,
    V075_K7_TWO_ROLE_BROKER_PROBE_RESULT_V1_DOMAIN,
    content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.6"
PROFILE_KEY = "v075_k7_two_role_broker_probe_v1"
ROLE_ORDER = ("WORKER", "BUSINESS")
TRAMPOLINE_SHA256 = "9126ba532125afd249da58578e7e39085a8c6ec6b79209c0fca479b32fe96957"
_TRAMPOLINE_BYTES = bytes.fromhex(
    "41544989fc498b3c2448c7c65800000048c7c0b30100000f054885c0781b7426498b54244848c70201000000498b542450488902e952020000498b542450488902e94502000048c7c09d00000048c7c70100000048c7c6090000004831d24d31d24d31c00f054885c00f887c01000048c7c06e0000000f05493b4424280f857101000048c7c09d00000048c7c72600000048c7c6010000004831d24d31d24d31c00f054885c00f885901000048c7c0be010000498b7c24304831f60f054885c00f884801000048c7c09d00000048c7c71600000048c7c602000000498b5424384d31d24d31c00f054885c00f88260100004883ec0848c704240000000048c7c00e00000048c7c7020000004889e64831d249c7c2080000000f054883c4084885c00f88f900000048c7c021000000498b7c24104831f60f054885c00f88e800000048c7c021000000498b7c241048c7c6010000000f054885c00f88d300000048c7c021000000498b7c241048c7c6020000000f054885c00f88be0000004d31c04d31c9e8c70000004883f8100f85e70000004883ec0848c704240000000048c7c042010000498b7c24084889e6498b5424184d8b54242049c7c0001000004d31c90f054883c4084989c149f7d949c7c00a000000e87600000048c7c77f00000048c7c0e70000000f050f0b49c7c001000000eb4e49c7c0020000004d31c9e84c000000eb7449c7c003000000eb3449c7c004000000eb2b49c7c005000000eb2249c7c006000000eb1949c7c007000000eb1049c7c008000000eb0749c7c0090000004989c149f7d9e802000000eb2a4883ec104c8904244c894c240848c7c001000000498b7c24404889e648c7c2100000000f054883c410c348c7c77e00000048c7c0e70000000f050f0b415cc3"
)
LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_TWO_ROLE_BROKER_PROBE_PROFILE_V1_DOMAIN,
        V075_K7_TWO_ROLE_BROKER_PROBE_RESULT_V1_DOMAIN,
        V075_K7_TWO_ROLE_BROKER_FAILURE_PREFIX_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("two-role broker probe domains are unregistered")

_PROFILE_ISSUER = object()
_PREFIX_ISSUER = object()
_RESULT_ISSUER = object()
_CONSUMED_LOCK = threading.Lock()
_CONSUMED_SESSIONS: set[tuple[int, str]] = set()
_TRAMPOLINE_MEMORY: mmap.mmap | None = None
_TRAMPOLINE_FUNCTION: Any = None


class V075K7TwoRoleBrokerProbeV1Error(RuntimeError):
    pass


class V075K7TwoRoleBrokerProbeCleanupV1Error(V075K7TwoRoleBrokerProbeV1Error):
    def __init__(
        self,
        message: str,
        *,
        prefix: Any,
        cleanup_complete: bool = False,
        unresolved_roles: tuple[str, ...] = (),
        cleanup_authority: Any = None,
    ) -> None:
        super().__init__(message)
        self.prefix = prefix
        self.cleanup_complete = cleanup_complete
        self.unresolved_roles = unresolved_roles
        self.cleanup_authority = cleanup_authority


class K7TwoRoleBrokerProbeOutcomeV1(str, Enum):
    SUCCESS = "SUCCESS"
    CAPABILITY_BLOCKED = "CAPABILITY_BLOCKED"
    WORKER_CLONE_REJECTED = "WORKER_CLONE_REJECTED"
    WORKER_SETUP_FAILED = "WORKER_SETUP_FAILED"
    BUSINESS_CLONE_REJECTED = "BUSINESS_CLONE_REJECTED"
    BUSINESS_SETUP_FAILED = "BUSINESS_SETUP_FAILED"
    PROBE_FAILURE = "PROBE_FAILURE"


def _fail(message: str) -> NoReturn:
    raise V075K7TwoRoleBrokerProbeV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("two-role broker used an undeclared domain")
    return content_id(domain, dict(payload))


def _locks() -> dict[str, bool]:
    return {
        "exact_process_launches_signed": False,
        "complete_attempt_memory_window_verified": False,
        "live_five_frame_protocol_verified": False,
        "counter_record_authorized": False,
        "work_vector_authorized": False,
        "comparison_vector_authorized": False,
        "attempt_terminal_authorized": False,
        "official_execution_allowed": False,
    }


@dataclass(frozen=True, slots=True)
class K7TwoRoleBrokerProbeProfileV1:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("two-role probe profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(V075_K7_TWO_ROLE_BROKER_PROBE_PROFILE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_two_role_broker_probe_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "readiness_level": "PREPARED_SESSION_CONSUMED_LIVE_PROBE",
            "role_order": list(ROLE_ORDER),
            "from_birth_clone_flags": atomic_v1.REQUIRED_CLONE_FLAGS,
            "native_role_edge_before_python_return": True,
            "allowed_role_prefixes": [[0, 0], [1, 0], [1, 1]],
            "two_distinct_pidfds_required_on_success": True,
            "trampoline_sha256": TRAMPOLINE_SHA256,
            "no_spawn_seccomp_profile_reused": True,
            "bootstrap_authority": "CALLER_SUPPLIED_SEALED_PROBE_INPUT",
            "role_manifest_bound": False,
            **_locks(),
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "two_role_broker_probe_profile_id": self.profile_id}


_OFFICIAL_PROFILE = K7TwoRoleBrokerProbeProfileV1(_PROFILE_ISSUER)


def official_v075_k7_two_role_broker_probe_profile_v1() -> K7TwoRoleBrokerProbeProfileV1:
    return _OFFICIAL_PROFILE


@dataclass(frozen=True, slots=True)
class K7TwoRoleBrokerFailurePrefixV1:
    _issuer: InitVar[object]
    session_id: str
    worker_edge: int
    business_edge: int
    failure_stage: str
    failure_code: str
    _prefix_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PREFIX_ISSUER:
            _fail("two-role failure prefix is issuer-owned")
        if (self.worker_edge, self.business_edge) not in {(0, 0), (1, 0), (1, 1)}:
            _fail("two-role native edge prefix is impossible")
        if (
            type(self.failure_stage) is not str
            or not self.failure_stage
            or type(self.failure_code) is not str
            or not self.failure_code
            or len(self.failure_code) > 256
        ):
            _fail("two-role failure stage/code is invalid")
        object.__setattr__(
            self,
            "_prefix_id",
            _hash(V075_K7_TWO_ROLE_BROKER_FAILURE_PREFIX_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_two_role_broker_failure_prefix.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_id": _OFFICIAL_PROFILE.profile_id,
            "prepared_session_id": self.session_id,
            "worker_native_edge": self.worker_edge,
            "business_native_edge": self.business_edge,
            "native_edge_total": self.worker_edge + self.business_edge,
            "failure_stage": self.failure_stage,
            "failure_code": self.failure_code,
            "volatile_process_local_prefix": True,
            "crash_persistence_proved": False,
            **_locks(),
        }

    @property
    def prefix_id(self) -> str:
        return self._prefix_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "failure_prefix_id": self.prefix_id}


class K7TwoRoleBrokerCleanupAuthorityV1:
    """Process-local retry authority for unresolved reap/tree obligations."""

    def __init__(
        self,
        issuer: object,
        *,
        guardian: Any,
        pids: dict[str, int],
        pidfds: dict[str, int],
        pidfd_valid: dict[str, bool],
        reaped: dict[str, bool],
        native_cells: Mapping[str, Any],
        prefix: K7TwoRoleBrokerFailurePrefixV1 | None,
        final_memory_peak: int | None,
    ) -> None:
        if issuer is not _RESULT_ISSUER:
            _fail("two-role cleanup authority is issuer-owned")
        self._owner_pid = os.getpid()
        self._guardian = guardian
        self._pids = pids
        self._pidfds = pidfds
        self._pidfd_valid = pidfd_valid
        self._reaped = reaped
        self._native_cells = native_cells
        self.prefix = prefix
        self.closed = False
        self.final_memory_peak = final_memory_peak

    @property
    def unresolved_roles(self) -> tuple[str, ...]:
        self._refresh_native_facts()
        return tuple(
            role
            for role in ROLE_ORDER
            if self._pids[role] > 0 and not self._reaped[role]
        )

    def _refresh_native_facts(self) -> None:
        for role in ROLE_ORDER:
            # Reap/retirement is monotone.  Never resurrect a closed pidfd
            # number from a native cell after that number may have been reused
            # by an unrelated open(2).
            if self._reaped[role]:
                continue
            cells = self._native_cells[role]
            child_pid = int(cells.clone_result.value)
            if child_pid <= 0:
                continue
            pidfd = int(cells.pidfd.value)
            self._pids[role] = child_pid
            self._pidfds[role] = pidfd
            try:
                valid = _pidfd_matches_child_v1(pidfd, child_pid)
            except BaseException:
                valid = False
            self._pidfd_valid[role] = valid

    def _retire_pidfd(self, role: str) -> None:
        descriptor = self._pidfds[role]
        try:
            if descriptor >= 0:
                os.close(descriptor)
        except OSError:
            pass
        finally:
            self._pidfds[role] = -1
            self._pidfd_valid[role] = False
            self._native_cells[role].pidfd.value = -1

    def bind_prefix(self, prefix: K7TwoRoleBrokerFailurePrefixV1) -> None:
        if self.prefix is not None or type(prefix) is not K7TwoRoleBrokerFailurePrefixV1:
            _fail("two-role cleanup prefix was already bound or is invalid")
        self.prefix = prefix

    def _close_binding(self) -> None:
        if getattr(self._guardian, "_two_role_cleanup_authority", None) is self:
            self._guardian._two_role_cleanup_authority = None
        self.closed = True

    def retry_cleanup(self) -> int:
        if os.getpid() != self._owner_pid or self.closed:
            _fail("two-role cleanup authority is stale or closed")
        guardian = self._guardian
        with guardian._lifecycle_lock:  # noqa: SLF001
            for role in self.unresolved_roles:
                if self._pidfd_valid[role]:
                    try:
                        atomic_v1._send_pidfd_signal(  # noqa: SLF001
                            atomic_v1._SYSCALLS[platform.machine().lower()],  # noqa: SLF001
                            self._pidfds[role],
                            signal.SIGKILL,
                        )
                    except BaseException:
                        pass
            # Kill the complete retained tree even if no known direct child is
            # unresolved: an unexpected migrated process is a tree obligation,
            # not a PID-ledger obligation.
            try:
                _ancestor_kill(guardian)
            except BaseException:
                pass
            for role in self.unresolved_roles:
                try:
                    if self._pidfd_valid[role]:
                        try:
                            atomic_v1._wait_pidfd(self._pidfds[role])  # noqa: SLF001
                        except BaseException:
                            atomic_v1._kill_and_reap_direct_child(  # noqa: SLF001
                                self._pids[role]
                            )
                    else:
                        atomic_v1._kill_and_reap_direct_child(  # noqa: SLF001
                            self._pids[role]
                        )
                    self._reaped[role] = True
                except BaseException as error:
                    raise V075K7TwoRoleBrokerProbeCleanupV1Error(
                        "two-role cleanup retry still has unreaped children",
                        prefix=self.prefix,
                        unresolved_roles=self.unresolved_roles,
                        cleanup_authority=self,
                    ) from error
            for role in ROLE_ORDER:
                self._retire_pidfd(role)
            if self.final_memory_peak is None and guardian._peak_fd >= 0:  # noqa: SLF001
                try:
                    self.final_memory_peak = preparation_v1._read_open_control(  # noqa: SLF001
                        guardian._peak_fd, "memory.peak"  # noqa: SLF001
                    )
                except BaseException:
                    # Peak loss makes the probe nonformal, but must not prevent
                    # containment and identity-bound tree removal.
                    self.final_memory_peak = None
            try:
                guardian._close_prelaunch_locked()  # noqa: SLF001
            except BaseException as error:
                cleanup_complete = guardian.closed
                if cleanup_complete:
                    self._close_binding()
                raise V075K7TwoRoleBrokerProbeCleanupV1Error(
                    "two-role tree cleanup retry is incomplete",
                    prefix=self.prefix,
                    unresolved_roles=(),
                    cleanup_complete=cleanup_complete,
                    cleanup_authority=None if cleanup_complete else self,
                ) from error
            self._close_binding()
            return -1 if self.final_memory_peak is None else self.final_memory_peak

    def __reduce__(self):
        raise TypeError("two-role cleanup authority is unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("two-role cleanup authority is unpickleable")


@dataclass(frozen=True, slots=True)
class K7TwoRoleBrokerProbeResultV1:
    _issuer: InitVar[object]
    session_id: str
    outcome: K7TwoRoleBrokerProbeOutcomeV1
    worker_edge: int
    business_edge: int
    worker_pid: int | None
    business_pid: int | None
    worker_reaped: bool
    business_reaped: bool
    final_memory_peak: int
    cleanup_complete: bool
    failure_prefix: K7TwoRoleBrokerFailurePrefixV1 | None
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("two-role probe result is issuer-owned")
        object.__setattr__(self, "outcome", K7TwoRoleBrokerProbeOutcomeV1(self.outcome))
        if (self.worker_edge, self.business_edge) not in {(0, 0), (1, 0), (1, 1)}:
            _fail("two-role result prefix is impossible")
        if self.outcome is K7TwoRoleBrokerProbeOutcomeV1.SUCCESS and not (
            (self.worker_edge, self.business_edge) == (1, 1)
            and self.worker_reaped
            and self.business_reaped
            and self.cleanup_complete
        ):
            _fail("successful two-role result lacks complete lifecycle")
        object.__setattr__(
            self,
            "_result_id",
            _hash(V075_K7_TWO_ROLE_BROKER_PROBE_RESULT_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_two_role_broker_probe_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_id": _OFFICIAL_PROFILE.profile_id,
            "prepared_session_id": self.session_id,
            "outcome": self.outcome.value,
            "worker_native_edge": self.worker_edge,
            "business_native_edge": self.business_edge,
            "native_edge_total": self.worker_edge + self.business_edge,
            "worker_pid": self.worker_pid,
            "business_pid": self.business_pid,
            "worker_direct_child_reaped": self.worker_reaped,
            "business_direct_child_reaped": self.business_reaped,
            "final_memory_peak_same_retained_ofd": self.final_memory_peak,
            "cleanup_complete": self.cleanup_complete,
            "failure_prefix_id": (
                None if self.failure_prefix is None else self.failure_prefix.prefix_id
            ),
            "process_launches_counter_record": None,
            "attempt_terminal": None,
            **_locks(),
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "two_role_broker_probe_result_id": self.result_id}


class _NativeTwoRoleLaunchArgsV1(ctypes.Structure):
    _fields_ = [
        *atomic_v1._NativeLaunchArgsV1._fields_,  # noqa: SLF001
        ("role_edge_cell", ctypes.c_void_p),
        ("clone_result_cell", ctypes.c_void_p),
    ]


class _RoleNativeCellsV1:
    """Caller-owned native facts that outlive every launch helper frame."""

    __slots__ = ("clone_result", "pidfd", "edge", "setup_read")

    def __init__(self) -> None:
        self.clone_result = ctypes.c_long(0)
        self.pidfd = ctypes.c_int(-1)
        self.edge = ctypes.c_uint64(0)
        self.setup_read = ctypes.c_int(-1)


def _native_two_role_trampoline_v1() -> Any:
    global _TRAMPOLINE_MEMORY, _TRAMPOLINE_FUNCTION
    if platform.machine().lower() not in {"x86_64", "amd64"}:
        _fail("two-role native trampoline is x86-64 only")
    if hashlib.sha256(_TRAMPOLINE_BYTES).hexdigest() != TRAMPOLINE_SHA256:
        _fail("two-role trampoline digest changed")
    if _TRAMPOLINE_FUNCTION is not None:
        return _TRAMPOLINE_FUNCTION
    memory = mmap.mmap(
        -1,
        len(_TRAMPOLINE_BYTES),
        flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
        prot=mmap.PROT_READ | mmap.PROT_WRITE,
    )
    memory.write(_TRAMPOLINE_BYTES)
    address = ctypes.addressof(ctypes.c_char.from_buffer(memory))
    atomic_v1._LIBC.mprotect.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int)  # noqa: SLF001
    atomic_v1._LIBC.mprotect.restype = ctypes.c_int  # noqa: SLF001
    if atomic_v1._LIBC.mprotect(  # noqa: SLF001
        ctypes.c_void_p(address),
        ctypes.c_size_t(len(_TRAMPOLINE_BYTES)),
        mmap.PROT_READ | mmap.PROT_EXEC,
    ) != 0:
        _fail("two-role trampoline W^X transition failed")
    function = ctypes.PYFUNCTYPE(ctypes.c_long, ctypes.POINTER(_NativeTwoRoleLaunchArgsV1))(address)
    _TRAMPOLINE_MEMORY = memory
    _TRAMPOLINE_FUNCTION = function
    return function


def _descriptor_matches(descriptor: int, expected: Mapping[str, int]) -> bool:
    if descriptor < 0:
        return False
    try:
        return preparation_v1._descriptor(os.fstat(descriptor)) == dict(expected)  # noqa: SLF001
    except OSError:
        return False


def _revalidate_prepared_session_v1(
    prepared_session: preparation_v1.K7OuterAttemptPreparedBrokerSessionV1,
    *,
    target_role: str,
) -> None:
    """Replay frozen topology/capabilities immediately before consumption/clone."""

    if target_role not in ROLE_ORDER:
        _fail("two-role preflight target is invalid")
    guardian = prepared_session.guardian
    if guardian._state is not preparation_v1.K7PreparedBrokerCleanupStateV1.PREPARED:  # noqa: SLF001
        _fail("prepared broker guardian is not in its exact PREPARED state")
    guardian._check()  # noqa: SLF001
    spec = prepared_session.execution_spec
    descriptor_rows = (
        (guardian._parent_fd, spec.parent_identity, "parent"),  # noqa: SLF001
        (guardian._outer_fd, spec.outer_identity, "outer"),  # noqa: SLF001
        (guardian._worker_fd, spec.worker_identity, "worker"),  # noqa: SLF001
        (guardian._business_fd, spec.business_identity, "business"),  # noqa: SLF001
        (guardian._kill_fd, spec.cgroup_kill_identity, "cgroup.kill"),  # noqa: SLF001
        (guardian._peak_fd, spec.memory_peak_identity, "memory.peak"),  # noqa: SLF001
    )
    if any(
        not _descriptor_matches(descriptor, identity)
        for descriptor, identity, _label in descriptor_rows
    ):
        _fail("prepared broker descriptor identity changed before launch")
    if (
        guardian._business_status is None  # noqa: SLF001
        or not preparation_v1._same_status(  # noqa: SLF001
            guardian._parent_fd, guardian._parent_status  # noqa: SLF001
        )
        or not preparation_v1._same_status(  # noqa: SLF001
            guardian._outer_fd, guardian._outer_status  # noqa: SLF001
        )
        or not preparation_v1._same_status(  # noqa: SLF001
            guardian._worker_fd, guardian._worker_status  # noqa: SLF001
        )
        or not preparation_v1._same_status(  # noqa: SLF001
            guardian._business_fd, guardian._business_status  # noqa: SLF001
        )
    ):
        _fail("prepared broker hierarchy identity changed before launch")
    preparation_v1.outer_v1._verify_named_descriptor(  # noqa: SLF001
        guardian._parent_fd, guardian._outer_name, guardian._outer_status  # noqa: SLF001
    )
    preparation_v1.outer_v1._verify_named_descriptor(  # noqa: SLF001
        guardian._outer_fd, guardian._worker_name, guardian._worker_status  # noqa: SLF001
    )
    preparation_v1.outer_v1._verify_named_descriptor(  # noqa: SLF001
        guardian._outer_fd, guardian._business_name, guardian._business_status  # noqa: SLF001
    )
    for descriptor in (
        guardian._parent_fd,  # noqa: SLF001
        guardian._outer_fd,  # noqa: SLF001
        guardian._worker_fd,  # noqa: SLF001
        guardian._business_fd,  # noqa: SLF001
    ):
        if (
            preparation_v1.inner_v1._fstatfs_magic(descriptor)  # noqa: SLF001
            != preparation_v1.inner_v1.CGROUP2_SUPER_MAGIC
        ):
            _fail("prepared broker hierarchy is no longer cgroup v2")
    if not preparation_v1.outer_v1._controls_match(  # noqa: SLF001
        guardian._outer_fd, preparation_v1.outer_v1.OUTER_CONTROL_READBACKS  # noqa: SLF001
    ):
        _fail("prepared outer controls changed before launch")
    for leaf_fd in (guardian._worker_fd, guardian._business_fd):  # noqa: SLF001
        if not preparation_v1.outer_v1._controls_match(  # noqa: SLF001
            leaf_fd, preparation_v1.LEAF_CONTROL_READBACKS
        ):
            _fail("prepared role controls changed before launch")
    enabled = set(
        preparation_v1.inner_v1._parse_controller_tokens(  # noqa: SLF001
            preparation_v1.inner_v1._read_control(  # noqa: SLF001
                guardian._outer_fd, "cgroup.subtree_control"  # noqa: SLF001
            ),
            "cgroup.subtree_control",
        )
    )
    if not set(preparation_v1.outer_v1.REQUIRED_CONTROLLERS) <= enabled:
        _fail("prepared subtree controllers changed before launch")
    stats = preparation_v1.outer_v1._cgroup_stat(guardian._outer_fd)  # noqa: SLF001
    if stats.get("nr_descendants") != 2 or stats.get("nr_dying_descendants") != 0:
        _fail("prepared two-sibling topology changed before launch")
    target_fd = (
        guardian._worker_fd  # noqa: SLF001
        if target_role == "WORKER"
        else guardian._business_fd  # noqa: SLF001
    )
    preparation_v1.inner_v1._validate_empty_leaf(target_fd)  # noqa: SLF001
    if target_role == "WORKER":
        preparation_v1.inner_v1._validate_empty_leaf(  # noqa: SLF001
            guardian._business_fd  # noqa: SLF001
        )
    endpoint_fd = (
        guardian._worker_socket_fd  # noqa: SLF001
        if target_role == "WORKER"
        else guardian._business_socket_fd  # noqa: SLF001
    )
    endpoint_identity = (
        spec.worker_socket_identity
        if target_role == "WORKER"
        else spec.business_socket_identity
    )
    if not _descriptor_matches(endpoint_fd, endpoint_identity):
        _fail("prepared role endpoint changed before launch")
    if target_role == "BUSINESS" and guardian._worker_socket_fd != -1:  # noqa: SLF001
        _fail("worker endpoint remained in broker after worker launch")


def _pidfd_matches_child_v1(pidfd: int, child_pid: int) -> bool:
    if type(pidfd) is not int or type(child_pid) is not int or pidfd < 3 or child_pid <= 0:
        return False
    try:
        os.fstat(pidfd)
        flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        info_fd = os.open(f"/proc/self/fdinfo/{pidfd}", flags)
        try:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(info_fd, min(4096, 8193 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > 8192:
                    return False
        finally:
            os.close(info_fd)
        rows = b"".join(chunks).decode("ascii", errors="strict").splitlines()
    except (OSError, UnicodeError):
        return False
    pid_rows = [row.split(":", 1)[1].strip() for row in rows if row.startswith("Pid:")]
    return len(pid_rows) == 1 and pid_rows[0].isdigit() and int(pid_rows[0]) == child_pid


def _launch_one_role(
    *,
    role: str,
    leaf_fd: int,
    endpoint_fd: int,
    bootstrap_record: tuple[
        int, tuple[int, ...], tuple[str, ...], tuple[tuple[str, str], ...]
    ],
    landlock_fd: int,
    seccomp_program: Any,
    trampoline: Any,
    native_cells: _RoleNativeCellsV1,
) -> tuple[int, int, int, int]:
    executable_fd, input_fds, argv, base_environment = bootstrap_record
    inherited = (executable_fd, *input_fds, endpoint_fd)
    setup_read = -1
    setup_write = -1
    null_fd = -1
    try:
        setup_read, setup_write = os.pipe2(os.O_CLOEXEC)
        native_cells.setup_read.value = setup_read
        os.set_blocking(setup_read, False)
        null_fd = os.open("/dev/null", os.O_RDWR | os.O_CLOEXEC)
        descriptors = (
            executable_fd,
            *input_fds,
            endpoint_fd,
            setup_read,
            setup_write,
            null_fd,
            landlock_fd,
            leaf_fd,
        )
        if min(descriptors) < 3 or len(set(descriptors)) != len(descriptors):
            _fail(f"{role} descriptor roles overlap")
        for descriptor in inherited:
            os.set_inheritable(descriptor, True)
        identities = tuple(atomic_v1._descriptor_identity(fd) for fd in descriptors)  # noqa: SLF001
        environment = dict(base_environment)
        environment[atomic_v1.CHANNEL_ENV_KEY] = str(endpoint_fd)
        environment[atomic_v1.INPUT_FDS_ENV_KEY] = ",".join(str(fd) for fd in input_fds)
        encoded_argv = tuple(value.encode("utf-8") for value in argv)
        encoded_env = tuple(
            f"{key}={value}".encode("utf-8") for key, value in sorted(environment.items())
        )
        argv_array = (ctypes.c_char_p * (len(encoded_argv) + 1))(*encoded_argv, None)
        env_array = (ctypes.c_char_p * (len(encoded_env) + 1))(*encoded_env, None)
        clone_args = atomic_v1.CloneArgsV1(
            flags=atomic_v1.REQUIRED_CLONE_FLAGS,
            pidfd=ctypes.addressof(native_cells.pidfd),
            exit_signal=signal.SIGCHLD,
            cgroup=leaf_fd,
        )
        launch_args = _NativeTwoRoleLaunchArgsV1(
            ctypes.addressof(clone_args),
            executable_fd,
            null_fd,
            ctypes.cast(argv_array, ctypes.c_void_p).value,
            ctypes.cast(env_array, ctypes.c_void_p).value,
            os.getpid(),
            landlock_fd,
            ctypes.addressof(seccomp_program),
            setup_write,
            ctypes.addressof(native_cells.edge),
            ctypes.addressof(native_cells.clone_result),
        )
        atomic_v1._assert_exact_inheritable_fds({0, 1, 2, *inherited})  # noqa: SLF001
        atomic_v1._assert_descriptor_roles_current(  # noqa: SLF001
            descriptors=descriptors,
            identities=identities,
            required_inheritable=inherited,
        )
        if atomic_v1._thread_count() != 1:  # noqa: SLF001
            _fail(f"{role} launch critical section is not single-threaded")
        returned_result = int(trampoline(ctypes.byref(launch_args)))
        clone_result = int(native_cells.clone_result.value)
        pidfd = int(native_cells.pidfd.value)
        edge = int(native_cells.edge.value)
        if returned_result != clone_result:
            _fail(f"{role} native return differs from its persistent result cell")
        if clone_result > 0 and edge != 1:
            _fail(f"{role} positive clone lacks its native write-ahead edge")
        if clone_result <= 0 and edge != 0:
            _fail(f"{role} rejected clone forged a native edge")
        return clone_result, pidfd, edge, setup_read
    except BaseException:
        if setup_read >= 0:
            try:
                os.close(setup_read)
            except OSError:
                pass
            setup_read = -1
        native_cells.setup_read.value = -1
        raise
    finally:
        for descriptor in (setup_write, null_fd):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        for descriptor in inherited:
            try:
                os.set_inheritable(descriptor, False)
            except OSError:
                pass


def _ancestor_kill(guardian: Any) -> None:
    if guardian._kill_fd < 0:  # noqa: SLF001
        _fail("two-role cleanup lost ancestor cgroup.kill")
    try:
        if os.write(guardian._kill_fd, b"1") != 1:  # noqa: SLF001
            _fail("ancestor cgroup.kill accepted a partial command")
    except OSError as error:
        if error.errno != errno.ESRCH:
            raise


def run_v075_k7_two_role_broker_probe_v1(
    *,
    prepared_session: preparation_v1.K7OuterAttemptPreparedBrokerSessionV1,
    worker_bootstrap: atomic_v1.K7SealedBootstrapExecV1,
    business_bootstrap: atomic_v1.K7SealedBootstrapExecV1,
    deadline_milliseconds: int,
) -> K7TwoRoleBrokerProbeResultV1:
    if type(prepared_session) is not preparation_v1.K7OuterAttemptPreparedBrokerSessionV1:
        _fail("two-role probe requires one exact prepared session")
    if type(worker_bootstrap) is not atomic_v1.K7SealedBootstrapExecV1 or type(
        business_bootstrap
    ) is not atomic_v1.K7SealedBootstrapExecV1:
        _fail("two-role probe requires two exact sealed bootstraps")
    if worker_bootstrap is business_bootstrap:
        _fail("worker and business bootstraps must be distinct")
    if type(deadline_milliseconds) is not int or not 1 <= deadline_milliseconds <= atomic_v1.MAX_DEADLINE_MILLISECONDS:
        _fail("two-role deadline is outside its frozen positive bound")

    guardian = prepared_session.guardian
    session_id = prepared_session.session_id
    capability = atomic_v1.probe_v075_k7_atomic_pidfd_capability_v1()
    if not capability.admitted:
        return K7TwoRoleBrokerProbeResultV1(
            _RESULT_ISSUER,
            session_id,
            K7TwoRoleBrokerProbeOutcomeV1.CAPABILITY_BLOCKED,
            0,
            0,
            None,
            None,
            False,
            False,
            -1,
            False,
            None,
        )
    key = (os.getpid(), session_id)
    worker_edge = business_edge = 0
    pids = {"WORKER": -1, "BUSINESS": -1}
    pidfds = {"WORKER": -1, "BUSINESS": -1}
    pidfd_valid = {"WORKER": False, "BUSINESS": False}
    reaped = {"WORKER": False, "BUSINESS": False}
    setup_reads = {"WORKER": -1, "BUSINESS": -1}
    native_cells = {
        "WORKER": _RoleNativeCellsV1(),
        "BUSINESS": _RoleNativeCellsV1(),
    }
    outcome = K7TwoRoleBrokerProbeOutcomeV1.PROBE_FAILURE
    failure_stage = "PRELAUNCH"
    final_peak = -1
    cleanup_complete = False
    original_error: BaseException | None = None
    prefix: K7TwoRoleBrokerFailurePrefixV1 | None = None
    landlock_fd = -1
    previous_mask: set[signal.Signals] | None = None
    filters: Any = None
    cleanup_authority = K7TwoRoleBrokerCleanupAuthorityV1(
        _RESULT_ISSUER,
        guardian=guardian,
        pids=pids,
        pidfds=pidfds,
        pidfd_valid=pidfd_valid,
        reaped=reaped,
        native_cells=native_cells,
        prefix=None,
        final_memory_peak=None,
    )

    with guardian._lifecycle_lock:  # noqa: SLF001 - sole runtime transfer lock
        guardian._check()  # noqa: SLF001
        if getattr(guardian, "_two_role_cleanup_authority", None) is not None:
            _fail("prepared broker already has a runtime cleanup authority")
        guardian._two_role_cleanup_authority = cleanup_authority
        try:
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
            blocked = set(signal.valid_signals()) - {signal.SIGKILL, signal.SIGSTOP}
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
            _revalidate_prepared_session_v1(
                prepared_session,
                target_role="WORKER",
            )
            with _CONSUMED_LOCK:
                if key in _CONSUMED_SESSIONS:
                    _fail("prepared broker session was already consumed")
                _CONSUMED_SESSIONS.add(key)
            if capability.landlock_abi_version is None:
                _fail("admitted broker capability lacks Landlock")
            # After capability admission, both bootstraps enter one
            # irreversible consumed prefix under the guardian lock before the
            # first clone attempt.
            worker_record = worker_bootstrap._consume()  # noqa: SLF001
            business_record = business_bootstrap._consume()  # noqa: SLF001
            landlock_fd = atomic_v1._create_write_denial_landlock_ruleset_v1(  # noqa: SLF001
                capability.landlock_abi_version
            )
            filters, seccomp_program = atomic_v1._seccomp_no_spawn_program_v1()  # noqa: SLF001
            trampoline = _native_two_role_trampoline_v1()

            for role, bootstrap_record, leaf_fd, endpoint_attribute in (
                (
                    "WORKER",
                    worker_record,
                    guardian._worker_fd,  # noqa: SLF001
                    "_worker_socket_fd",
                ),
                (
                    "BUSINESS",
                    business_record,
                    guardian._business_fd,  # noqa: SLF001
                    "_business_socket_fd",
                ),
            ):
                failure_stage = f"{role}_CLONE"
                _revalidate_prepared_session_v1(
                    prepared_session,
                    target_role=role,
                )
                endpoint_fd = getattr(guardian, endpoint_attribute)
                clone_result, pidfd, edge, setup_read = _launch_one_role(
                    role=role,
                    leaf_fd=leaf_fd,
                    endpoint_fd=endpoint_fd,
                    bootstrap_record=bootstrap_record,
                    landlock_fd=landlock_fd,
                    seccomp_program=seccomp_program,
                    trampoline=trampoline,
                    native_cells=native_cells[role],
                )
                setup_reads[role] = setup_read
                if role == "WORKER":
                    worker_edge = edge
                else:
                    business_edge = edge
                if clone_result <= 0:
                    outcome = (
                        K7TwoRoleBrokerProbeOutcomeV1.WORKER_CLONE_REJECTED
                        if role == "WORKER"
                        else K7TwoRoleBrokerProbeOutcomeV1.BUSINESS_CLONE_REJECTED
                    )
                    raise V075K7TwoRoleBrokerProbeV1Error(
                        f"{role} clone3 rejected with errno {-clone_result}"
                    )
                pids[role] = clone_result
                pidfds[role] = pidfd
                pidfd_valid[role] = _pidfd_matches_child_v1(pidfd, clone_result)
                if not pidfd_valid[role]:
                    _fail(f"{role} positive clone lacks its matching pidfd")
                os.close(endpoint_fd)
                setattr(guardian, endpoint_attribute, -1)
                failure_stage = f"{role}_SETUP"
                setup_raw = atomic_v1._read_setup_status(setup_read)  # noqa: SLF001
                os.close(setup_read)
                setup_reads[role] = -1
                native_cells[role].setup_read.value = -1
                setup_ok, _stage, _error = atomic_v1._parse_setup_status(setup_raw)  # noqa: SLF001
                if not setup_ok:
                    outcome = (
                        K7TwoRoleBrokerProbeOutcomeV1.WORKER_SETUP_FAILED
                        if role == "WORKER"
                        else K7TwoRoleBrokerProbeOutcomeV1.BUSINESS_SETUP_FAILED
                    )
                    raise V075K7TwoRoleBrokerProbeV1Error(f"{role} native setup failed")

            failure_stage = "PIDFD_REAP"
            for role in ROLE_ORDER:
                atomic_v1._wait_pidfd(  # noqa: SLF001
                    pidfds[role], grace_milliseconds=deadline_milliseconds
                )
                reaped[role] = True
            if (
                pids["WORKER"] == pids["BUSINESS"]
                or pidfds["WORKER"] == pidfds["BUSINESS"]
            ):
                _fail("two-role positive launches reused a PID or pidfd")
            final_peak = preparation_v1._read_open_control(  # noqa: SLF001
                guardian._peak_fd, "memory.peak"  # noqa: SLF001
            )
            if final_peak < prepared_session.prelaunch_memory_peak:
                _fail("retained final peak is below the frozen prelaunch peak")
            outcome = K7TwoRoleBrokerProbeOutcomeV1.SUCCESS
        except BaseException as error:
            original_error = error
            # Recover facts written natively before any Python return.  These
            # caller-owned cells outlive the helper frame and do not depend on
            # a post-return dict/object publication.  Signals remain blocked
            # until these facts have reached the preinstalled cleanup guard.
            cleanup_authority._refresh_native_facts()
            for role in ROLE_ORDER:
                cells = native_cells[role]
                native_result = int(cells.clone_result.value)
                native_pidfd = int(cells.pidfd.value)
                native_edge = int(cells.edge.value)
                if native_result > 0:
                    pids[role] = native_result
                    pidfds[role] = native_pidfd
                native_setup_read = int(cells.setup_read.value)
                if native_setup_read >= 0:
                    setup_reads[role] = native_setup_read
                if role == "WORKER":
                    worker_edge = native_edge
                else:
                    business_edge = native_edge
            for role in ROLE_ORDER:
                if pids[role] > 0 and not reaped[role] and pidfd_valid[role]:
                    try:
                        atomic_v1._send_pidfd_signal(  # noqa: SLF001
                            atomic_v1._SYSCALLS[platform.machine().lower()],  # noqa: SLF001
                            pidfds[role],
                            signal.SIGKILL,
                        )
                    except BaseException:
                        pass
            if any(pids[role] > 0 for role in ROLE_ORDER):
                try:
                    _ancestor_kill(guardian)
                except BaseException:
                    pass
            for role in ROLE_ORDER:
                if pids[role] <= 0 or reaped[role]:
                    continue
                try:
                    if pidfd_valid[role]:
                        try:
                            atomic_v1._wait_pidfd(pidfds[role])  # noqa: SLF001
                        except BaseException:
                            atomic_v1._kill_and_reap_direct_child(pids[role])  # noqa: SLF001
                    else:
                        atomic_v1._kill_and_reap_direct_child(pids[role])  # noqa: SLF001
                    reaped[role] = True
                except BaseException:
                    pass
            try:
                final_peak = preparation_v1._read_open_control(  # noqa: SLF001
                    guardian._peak_fd, "memory.peak"  # noqa: SLF001
                )
            except BaseException:
                final_peak = -1
        finally:
            # Freeze every native fact into the cleanup authority before a
            # pending signal can run Python or any fallible failure artifact
            # is materialized.  The authority was attached to the guardian
            # before the first clone attempt.
            cleanup_authority._refresh_native_facts()
            for role in ROLE_ORDER:
                native_edge = int(native_cells[role].edge.value)
                if role == "WORKER":
                    worker_edge = native_edge
                else:
                    business_edge = native_edge
            unresolved = cleanup_authority.unresolved_roles

            signal_restore_error: BaseException | None = None
            if previous_mask is not None:
                try:
                    signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
                except BaseException as error:
                    signal_restore_error = error
                finally:
                    previous_mask = None
            if signal_restore_error is not None and original_error is None:
                original_error = signal_restore_error
                failure_stage = "SIGNAL_RESTORE"
                outcome = K7TwoRoleBrokerProbeOutcomeV1.PROBE_FAILURE

            del filters
            for descriptor in (*setup_reads.values(), landlock_fd):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
            for bootstrap in (worker_bootstrap, business_bootstrap):
                try:
                    bootstrap.close()
                except BaseException:
                    pass

            # Failure-prefix construction is deliberately downstream of the
            # preinstalled containment guard and native-fact recovery.  Even
            # hashing/allocation failure cannot erase cleanup authority.
            prefix_error: BaseException | None = None
            if original_error is not None:
                try:
                    prefix = K7TwoRoleBrokerFailurePrefixV1(
                        _PREFIX_ISSUER,
                        session_id,
                        worker_edge,
                        business_edge,
                        failure_stage,
                        (
                            type(original_error).__name__
                            + ":"
                            + str(original_error)
                        )[:256],
                    )
                    cleanup_authority.bind_prefix(prefix)
                except BaseException as error:
                    prefix = None
                    prefix_error = error

            if unresolved:
                # Preserve every unresolved pidfd together with the guardian.
                # Closing it merely because the cgroup is empty would lose the
                # only direct-child reap authority for a zombie.
                for role in ROLE_ORDER:
                    if role in unresolved:
                        continue
                    cleanup_authority._retire_pidfd(role)
                # A read taken while an unresolved child may still run is not
                # final.  Retry rereads the retained OFD after every direct
                # child has been reaped.
                cleanup_authority.final_memory_peak = None
                raise V075K7TwoRoleBrokerProbeCleanupV1Error(
                    "two-role direct children were not all proven reaped",
                    prefix=prefix,
                    unresolved_roles=unresolved,
                    cleanup_authority=cleanup_authority,
                ) from prefix_error

            for role in ROLE_ORDER:
                cleanup_authority._retire_pidfd(role)
            cleanup_authority.final_memory_peak = (
                None if final_peak < 0 else final_peak
            )
            # A populated tree can contain a process absent from the two
            # direct-child ledgers.  Kill the retained ancestor unconditionally
            # before emptiness verification; cleanup retains the kill OFD until
            # the hierarchy has actually been removed.
            try:
                _ancestor_kill(guardian)
            except BaseException:
                pass
            try:
                guardian._close_prelaunch_locked()  # noqa: SLF001
                cleanup_complete = True
            except BaseException as cleanup_error:
                cleanup_complete = guardian.closed
                if prefix is None and prefix_error is None:
                    try:
                        prefix = K7TwoRoleBrokerFailurePrefixV1(
                            _PREFIX_ISSUER,
                            session_id,
                            worker_edge,
                            business_edge,
                            "CLEANUP",
                            (
                                type(cleanup_error).__name__
                                + ":"
                                + str(cleanup_error)
                            )[:256],
                        )
                        cleanup_authority.bind_prefix(prefix)
                    except BaseException as error:
                        prefix = None
                        prefix_error = error
                if cleanup_complete:
                    cleanup_authority._close_binding()
                raise V075K7TwoRoleBrokerProbeCleanupV1Error(
                    "two-role probe cleanup is incomplete",
                    prefix=prefix,
                    cleanup_complete=cleanup_complete,
                    unresolved_roles=(),
                    cleanup_authority=(
                        None if cleanup_complete else cleanup_authority
                    ),
                ) from (prefix_error or cleanup_error)
            cleanup_authority._close_binding()
            if prefix_error is not None:
                raise V075K7TwoRoleBrokerProbeCleanupV1Error(
                    "two-role failure prefix could not be materialized",
                    prefix=None,
                    cleanup_complete=True,
                    unresolved_roles=(),
                    cleanup_authority=None,
                ) from prefix_error

    if original_error is not None and outcome is K7TwoRoleBrokerProbeOutcomeV1.PROBE_FAILURE:
        outcome = K7TwoRoleBrokerProbeOutcomeV1.PROBE_FAILURE
    return K7TwoRoleBrokerProbeResultV1(
        _RESULT_ISSUER,
        session_id,
        outcome,
        worker_edge,
        business_edge,
        None if pids["WORKER"] < 0 else pids["WORKER"],
        None if pids["BUSINESS"] < 0 else pids["BUSINESS"],
        reaped["WORKER"],
        reaped["BUSINESS"],
        final_peak,
        cleanup_complete,
        prefix if original_error is not None else None,
    )


__all__ = (
    "K7TwoRoleBrokerCleanupAuthorityV1",
    "K7TwoRoleBrokerFailurePrefixV1",
    "K7TwoRoleBrokerProbeOutcomeV1",
    "K7TwoRoleBrokerProbeProfileV1",
    "K7TwoRoleBrokerProbeResultV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "TRAMPOLINE_SHA256",
    "V075K7TwoRoleBrokerProbeCleanupV1Error",
    "V075K7TwoRoleBrokerProbeV1Error",
    "official_v075_k7_two_role_broker_probe_profile_v1",
    "run_v075_k7_two_role_broker_probe_v1",
)
