"""Real, fail-closed cgroup-v2 attempt-leaf leasing for the K7 successor.

The public acquisition function performs only parent-owned cgroup setup.  It
does not launch, attach, signal, or reap a child and it issues no accounting or
terminal authority.  All filesystem operations are relative to a caller-opened
directory descriptor; a pathname is never accepted as authority.
"""

from __future__ import annotations

import ctypes
from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import os
import secrets
import stat
import sys
import threading
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_os_supervisor_admission_v1 as admission
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_CGROUP_LEASE_AUTHORITY_V1_DOMAIN,
    V075_K7_CGROUP_LEASE_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN,
    V075_K7_CGROUP_LEASE_PROFILE_V1_DOMAIN,
    content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.96.0"
PROFILE_KEY = "v075_k7_cgroup_lease_v1"
CGROUP2_SUPER_MAGIC = 0x63677270
MAX_CONTROL_BYTES = 64 * 1024
REQUIRED_CONTROLLERS = ("memory", "pids")
REQUIRED_LEAF_FILES = admission.REQUIRED_LEAF_FILES
CONTROL_READBACKS = {
    "pids.max": "1",
    "cgroup.max.depth": "0",
    "cgroup.max.descendants": "0",
}
REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_CGROUP_LEASE_PROFILE_V1_DOMAIN",
    "V075_K7_CGROUP_LEASE_AUTHORITY_V1_DOMAIN",
    "V075_K7_CGROUP_LEASE_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN",
)
LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_CGROUP_LEASE_PROFILE_V1_DOMAIN,
        V075_K7_CGROUP_LEASE_AUTHORITY_V1_DOMAIN,
        V075_K7_CGROUP_LEASE_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("K7 cgroup-lease domains are unregistered")

CHILD_LAUNCH_ALLOWED = False
COUNTER_RECORD_AUTHORIZED = False
WORK_VECTOR_AUTHORIZED = False
COMPARISON_VECTOR_AUTHORIZED = False
ACTUAL_PROJECTION_PROOF_AUTHORIZED = False
ATTEMPT_TERMINAL_AUTHORIZED = False
OFFICIAL_EXECUTION_ALLOWED = False

_PROFILE_ISSUER = object()
_BLOCKED_ISSUER = object()
_LEASE_ISSUER = object()
_NONCE_TOKEN_ISSUER = object()


class V075K7CgroupLeaseV1Error(RuntimeError):
    """A lease input or runtime invariant was invalid."""


class V075K7CgroupLeaseCleanupV1Error(V075K7CgroupLeaseV1Error):
    """The implementation could not prove removal of its own attempt leaf."""


class K7CgroupLeaseBlockerV1(str, Enum):
    NOT_LINUX = "NOT_LINUX"
    ADMISSION_AUTHORITY_CROSSED = "ADMISSION_AUTHORITY_CROSSED"
    ADMISSION_DESCRIPTOR_NOT_BOUND = "ADMISSION_DESCRIPTOR_NOT_BOUND"
    DESCRIPTOR_IDENTITY_MISMATCH = "DESCRIPTOR_IDENTITY_MISMATCH"
    DESCRIPTOR_NOT_DIRECTORY = "DESCRIPTOR_NOT_DIRECTORY"
    DESCRIPTOR_DUPLICATION_FAILED = "DESCRIPTOR_DUPLICATION_FAILED"
    NOT_CGROUP2_FILESYSTEM = "NOT_CGROUP2_FILESYSTEM"
    PARENT_CONTROLLER_READ_FAILED = "PARENT_CONTROLLER_READ_FAILED"
    REQUIRED_CONTROLLER_NOT_DELEGATED = "REQUIRED_CONTROLLER_NOT_DELEGATED"
    UNIQUE_LEAF_CREATION_FAILED = "UNIQUE_LEAF_CREATION_FAILED"
    LEAF_OPEN_FAILED = "LEAF_OPEN_FAILED"
    LEAF_FILESYSTEM_MISMATCH = "LEAF_FILESYSTEM_MISMATCH"
    REQUIRED_LEAF_FILE_MISSING = "REQUIRED_LEAF_FILE_MISSING"
    LEAF_NOT_INITIALLY_EMPTY = "LEAF_NOT_INITIALLY_EMPTY"
    LEAF_TYPE_NOT_DOMAIN = "LEAF_TYPE_NOT_DOMAIN"
    MEMORY_PEAK_NOT_ZERO = "MEMORY_PEAK_NOT_ZERO"
    CONTROL_WRITE_FAILED = "CONTROL_WRITE_FAILED"
    CONTROL_READBACK_MISMATCH = "CONTROL_READBACK_MISMATCH"


class K7CgroupLeaseStageV1(str, Enum):
    AUTHORITY = "AUTHORITY"
    DESCRIPTOR = "DESCRIPTOR"
    FILESYSTEM = "FILESYSTEM"
    DELEGATION = "DELEGATION"
    CREATE = "CREATE"
    VALIDATE_EMPTY = "VALIDATE_EMPTY"
    CONFIGURE = "CONFIGURE"


def _fail(message: str) -> NoReturn:
    raise V075K7CgroupLeaseV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("K7 cgroup lease used an undeclared domain")
    return content_id(domain, dict(payload))


def _formal_locks() -> dict[str, bool]:
    return {
        "child_launch_allowed": CHILD_LAUNCH_ALLOWED,
        "counter_record_authorized": COUNTER_RECORD_AUTHORIZED,
        "work_vector_authorized": WORK_VECTOR_AUTHORIZED,
        "comparison_vector_authorized": COMPARISON_VECTOR_AUTHORIZED,
        "actual_projection_proof_authorized": (
            ACTUAL_PROJECTION_PROOF_AUTHORIZED
        ),
        "attempt_terminal_authorized": ATTEMPT_TERMINAL_AUTHORIZED,
        "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
    }


def _descriptor_payload(status: os.stat_result) -> dict[str, int]:
    return {
        "device": status.st_dev,
        "inode": status.st_ino,
        "mode": stat.S_IMODE(status.st_mode),
        "owner_uid": status.st_uid,
        "owner_gid": status.st_gid,
    }


def _parse_ascii(raw: bytes, label: str) -> str:
    if type(raw) is not bytes or len(raw) > MAX_CONTROL_BYTES:
        _fail(f"{label} exceeds its exact byte contract")
    try:
        value = raw.decode("ascii", errors="strict")
    except UnicodeDecodeError as error:
        raise V075K7CgroupLeaseV1Error(
            f"{label} is not strict ASCII"
        ) from error
    if "\x00" in value:
        _fail(f"{label} contains NUL")
    return value


def _parse_controller_tokens(raw: bytes, label: str) -> tuple[str, ...]:
    tokens = _parse_ascii(raw, label).split()
    if any(not token or not token.replace("_", "").isalnum() for token in tokens):
        _fail(f"{label} contains an invalid controller token")
    return tuple(sorted(set(tokens)))


def _parse_cgroup_events(raw: bytes) -> dict[str, int]:
    rows: dict[str, int] = {}
    for line in _parse_ascii(raw, "cgroup.events").splitlines():
        fields = line.split()
        if len(fields) != 2 or fields[0] in rows:
            _fail("cgroup.events is malformed or duplicated")
        if not fields[1].isdigit():
            _fail("cgroup.events value is not nonnegative")
        rows[fields[0]] = int(fields[1])
    if "populated" not in rows:
        _fail("cgroup.events lacks populated")
    return rows


def _parse_nonnegative(raw: bytes, label: str) -> int:
    value = _parse_ascii(raw, label).strip()
    if not value or not value.isdigit():
        _fail(f"{label} is not a nonnegative integer")
    return int(value)


def _readback_matches(raw: bytes, expected: str, label: str) -> bool:
    if type(expected) is not str or expected not in {"0", "1"}:
        _fail(f"{label} has an invalid frozen readback")
    return _parse_ascii(raw, label).strip() == expected


def _open_control(directory_fd: int, name: str, flags: int) -> int:
    if type(name) is not str or not name or "/" in name or name in {".", ".."}:
        _fail("cgroup control name is not one relative component")
    actual = flags | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        actual |= os.O_NOFOLLOW
    descriptor = os.open(name, actual, dir_fd=directory_fd)
    os.set_inheritable(descriptor, False)
    status = os.fstat(descriptor)
    if not stat.S_ISREG(status.st_mode):
        os.close(descriptor)
        _fail(f"{name} is not a regular cgroup control file")
    return descriptor


def _read_control(directory_fd: int, name: str) -> bytes:
    descriptor = _open_control(directory_fd, name, os.O_RDONLY)
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(8192, MAX_CONTROL_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_CONTROL_BYTES:
                _fail(f"{name} exceeds its byte cap")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _write_control(directory_fd: int, name: str, value: str) -> None:
    encoded = value.encode("ascii")
    descriptor = _open_control(directory_fd, name, os.O_WRONLY)
    try:
        if os.write(descriptor, encoded) != len(encoded):
            _fail(f"{name} accepted a partial write")
    finally:
        os.close(descriptor)


def _fstatfs_magic(descriptor: int) -> int:
    if not sys.platform.startswith("linux"):
        _fail("fstatfs is only admitted on Linux")
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.fstatfs
    function.argtypes = (ctypes.c_int, ctypes.c_void_p)
    function.restype = ctypes.c_int
    buffer = ctypes.create_string_buffer(256)
    if function(descriptor, ctypes.byref(buffer)) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return int(ctypes.c_long.from_buffer(buffer).value)


def _validate_empty_leaf(leaf_fd: int) -> None:
    if _parse_ascii(_read_control(leaf_fd, "cgroup.procs"), "cgroup.procs").split():
        _fail("attempt leaf contains a process")
    if _parse_ascii(
        _read_control(leaf_fd, "cgroup.threads"), "cgroup.threads"
    ).split():
        _fail("attempt leaf contains a thread")
    if _parse_nonnegative(_read_control(leaf_fd, "pids.current"), "pids.current") != 0:
        _fail("attempt leaf pids.current is nonzero")
    if _parse_cgroup_events(_read_control(leaf_fd, "cgroup.events"))["populated"] != 0:
        _fail("attempt leaf is populated")


def _validate_initial_leaf(
    leaf_fd: int,
) -> K7CgroupLeaseBlockerV1 | None:
    try:
        _validate_empty_leaf(leaf_fd)
    except (OSError, V075K7CgroupLeaseV1Error):
        return K7CgroupLeaseBlockerV1.LEAF_NOT_INITIALLY_EMPTY
    cgroup_type = _parse_ascii(
        _read_control(leaf_fd, "cgroup.type"), "cgroup.type"
    ).strip()
    if cgroup_type != "domain":
        return K7CgroupLeaseBlockerV1.LEAF_TYPE_NOT_DOMAIN
    memory_peak = _parse_nonnegative(
        _read_control(leaf_fd, "memory.peak"), "memory.peak"
    )
    if memory_peak != 0:
        return K7CgroupLeaseBlockerV1.MEMORY_PEAK_NOT_ZERO
    return None


@dataclass(frozen=True, slots=True)
class K7CgroupLeaseProfileV1:
    _issuer: InitVar[object]
    required_controllers: tuple[str, ...]
    required_leaf_files: tuple[str, ...]
    control_readbacks: tuple[tuple[str, str], ...]
    _profile_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PROFILE_ISSUER
            or self.required_controllers != REQUIRED_CONTROLLERS
            or self.required_leaf_files != REQUIRED_LEAF_FILES
            or self.control_readbacks != tuple(CONTROL_READBACKS.items())
        ):
            _fail("K7 cgroup lease profile changed")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(V075_K7_CGROUP_LEASE_PROFILE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_cgroup_lease_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "required_controllers": list(self.required_controllers),
            "required_leaf_files": list(self.required_leaf_files),
            "control_readbacks": [
                {"file": name, "value": value}
                for name, value in self.control_readbacks
            ],
            "authority_source": "CALLER_PREOPENED_DIRECTORY_DESCRIPTOR_ONLY",
            "path_authority_accepted": False,
            "parent_owned_nonce_consumed_before_cgroup_access": True,
            "nonce_binding": "EXACT_REQUEST_ADMISSION_DESCRIPTOR_IDENTITY",
            "durable_cross_process_replay_verified": False,
            "child_launch_implemented": False,
            **_formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        current = _hash(V075_K7_CGROUP_LEASE_PROFILE_V1_DOMAIN, self._payload())
        if current != self._profile_id:
            _fail("K7 cgroup lease profile changed after freeze")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cgroup_lease_profile_id": self.profile_id}


_OFFICIAL_PROFILE = K7CgroupLeaseProfileV1(
    _PROFILE_ISSUER,
    REQUIRED_CONTROLLERS,
    REQUIRED_LEAF_FILES,
    tuple(CONTROL_READBACKS.items()),
)


def official_v075_k7_cgroup_lease_profile_v1() -> K7CgroupLeaseProfileV1:
    return _OFFICIAL_PROFILE


class K7CgroupLeaseNonceTokenV1:
    """Process-local, single-use request/nonce binding issued by the parent."""

    __slots__ = (
        "_owner_pid",
        "_request",
        "_request_id",
        "_request_nonce",
        "_admission_result",
        "_admission_result_id",
        "_delegated_parent_fd",
        "_descriptor_identity",
        "_descriptor_target_sha256",
    )

    def __init__(
        self,
        issuer: object,
        request: successor.V075K7ParentOwnedSuccessorRequestV1,
        admission_result: admission.K7OSSupervisorAdmissionResultV1,
        delegated_parent_fd: int,
        descriptor_identity: tuple[int, int, int, int, int],
        descriptor_target_sha256: str,
    ) -> None:
        if issuer is not _NONCE_TOKEN_ISSUER:
            _fail("cgroup lease nonce token is service-issued")
        self._owner_pid = os.getpid()
        self._request = request
        self._request_id = request.request_id
        self._request_nonce = request.request_nonce
        self._admission_result = admission_result
        self._admission_result_id = admission_result.result_id
        self._delegated_parent_fd = delegated_parent_fd
        self._descriptor_identity = descriptor_identity
        self._descriptor_target_sha256 = descriptor_target_sha256

    def __reduce__(self):
        raise TypeError("K7 cgroup lease nonce token is unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("K7 cgroup lease nonce token is unpickleable")


class K7CgroupLeaseNonceServiceV1:
    """Parent-process replay guard; durable cross-process replay is not claimed."""

    __slots__ = ("_owner_pid", "_issued", "_consumed", "_lock")

    def __init__(self) -> None:
        self._owner_pid = os.getpid()
        self._issued: dict[int, K7CgroupLeaseNonceTokenV1] = {}
        self._consumed: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def _check_process(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("cgroup lease nonce service cannot cross a process boundary")

    def issue(
        self,
        *,
        request: successor.V075K7ParentOwnedSuccessorRequestV1,
        admission_result: admission.K7OSSupervisorAdmissionResultV1,
        delegated_parent_fd: int,
    ) -> K7CgroupLeaseNonceTokenV1:
        self._check_process()
        if type(request) is not successor.V075K7ParentOwnedSuccessorRequestV1:
            _fail("nonce service requires the exact successor request")
        if type(admission_result) is not admission.K7OSSupervisorAdmissionResultV1:
            _fail("nonce service requires the exact admission result")
        if type(delegated_parent_fd) is not int or delegated_parent_fd < 0:
            _fail("nonce service requires one exact delegated descriptor")
        request._assert_current()  # noqa: SLF001
        admission.verify_v075_k7_os_supervisor_admission_v1(admission_result)
        if admission_result.profile is not request.profile.admission_profile:
            _fail("nonce service request/admission authority is crossed")
        fact = admission_result.probe.delegated_parent_fact
        try:
            status = os.fstat(delegated_parent_fd)
            target = os.readlink(f"/proc/self/fd/{delegated_parent_fd}")
        except OSError as error:
            raise V075K7CgroupLeaseV1Error(
                "nonce service cannot observe the delegated descriptor"
            ) from error
        identity = (
            status.st_dev,
            status.st_ino,
            stat.S_IMODE(status.st_mode),
            status.st_uid,
            status.st_gid,
        )
        target_sha256 = hashlib.sha256(target.encode("utf-8")).hexdigest()
        if (
            not admission_result.probe.delegated_parent_fd_supplied
            or not fact.exists
            or identity
            != (fact.device, fact.inode, fact.mode, fact.owner_uid, fact.owner_gid)
            or target_sha256 != fact.path_sha256
        ):
            _fail("nonce service descriptor does not match admission evidence")
        token = K7CgroupLeaseNonceTokenV1(
            _NONCE_TOKEN_ISSUER,
            request,
            admission_result,
            delegated_parent_fd,
            identity,
            target_sha256,
        )
        identity_key = (request.request_id, request.request_nonce)
        with self._lock:
            if identity_key in self._consumed:
                _fail("cgroup lease request nonce was already consumed")
            self._issued[id(token)] = token
        return token

    def consume(
        self,
        token: K7CgroupLeaseNonceTokenV1,
        request: successor.V075K7ParentOwnedSuccessorRequestV1,
        admission_result: admission.K7OSSupervisorAdmissionResultV1,
        delegated_parent_fd: int,
    ) -> None:
        self._check_process()
        if (
            type(token) is not K7CgroupLeaseNonceTokenV1
            or token._owner_pid != self._owner_pid  # noqa: SLF001
            or token._request is not request  # noqa: SLF001
            or token._request_id != request.request_id  # noqa: SLF001
            or token._request_nonce != request.request_nonce  # noqa: SLF001
            or token._admission_result is not admission_result  # noqa: SLF001
            or token._admission_result_id != admission_result.result_id  # noqa: SLF001
            or token._delegated_parent_fd != delegated_parent_fd  # noqa: SLF001
        ):
            _fail("cgroup lease nonce token is crossed or stale")
        identity = (token._request_id, token._request_nonce)  # noqa: SLF001
        with self._lock:
            if identity in self._consumed:
                _fail("cgroup lease request nonce was already consumed")
            if self._issued.pop(id(token), None) is not token:
                _fail("cgroup lease nonce token was not issued by this service")
            self._consumed.add(identity)

    def __reduce__(self):
        raise TypeError("K7 cgroup lease nonce service is unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("K7 cgroup lease nonce service is unpickleable")


_NONCE_SERVICE = K7CgroupLeaseNonceServiceV1()


def official_v075_k7_cgroup_lease_nonce_service_v1(
) -> K7CgroupLeaseNonceServiceV1:
    return _NONCE_SERVICE


@dataclass(frozen=True, slots=True)
class K7CgroupLeasePrelaunchBlockedResultV1:
    _issuer: InitVar[object]
    request: successor.V075K7ParentOwnedSuccessorRequestV1 = field(
        repr=False, compare=False
    )
    admission_result: admission.K7OSSupervisorAdmissionResultV1 = field(
        repr=False, compare=False
    )
    blocker: K7CgroupLeaseBlockerV1
    stage: K7CgroupLeaseStageV1
    leaf_name_sha256: str
    leaf_was_created: bool
    leaf_was_removed: bool
    _validated_ids: tuple[str, str] = field(init=False, repr=False)
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BLOCKED_ISSUER
            or type(self.request)
            is not successor.V075K7ParentOwnedSuccessorRequestV1
            or type(self.admission_result)
            is not admission.K7OSSupervisorAdmissionResultV1
        ):
            _fail("cgroup prelaunch blocker is caller-minted or foreign")
        self.request._assert_current()  # noqa: SLF001
        admission.verify_v075_k7_os_supervisor_admission_v1(
            self.admission_result
        )
        try:
            blocker = K7CgroupLeaseBlockerV1(self.blocker)
            stage = K7CgroupLeaseStageV1(self.stage)
        except (TypeError, ValueError) as error:
            raise V075K7CgroupLeaseV1Error("unknown cgroup lease blocker") from error
        if (
            type(self.leaf_name_sha256) is not str
            or len(self.leaf_name_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.leaf_name_sha256)
            or type(self.leaf_was_created) is not bool
            or type(self.leaf_was_removed) is not bool
            or (self.leaf_was_removed and not self.leaf_was_created)
            or (self.leaf_was_created and not self.leaf_was_removed)
        ):
            _fail("cgroup prelaunch cleanup evidence is invalid")
        object.__setattr__(self, "blocker", blocker)
        object.__setattr__(self, "stage", stage)
        ids = (self.request.request_id, self.admission_result.result_id)
        object.__setattr__(self, "_validated_ids", ids)
        object.__setattr__(
            self,
            "_result_id",
            _hash(
                V075_K7_CGROUP_LEASE_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_cgroup_lease_prelaunch_blocked_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "cgroup_lease_profile_id": _OFFICIAL_PROFILE.profile_id,
            "successor_request_id": self.request.request_id,
            "os_supervisor_admission_result_id": self.admission_result.result_id,
            "route_identity_id": self.request.route_identity.route_identity_id,
            "route_attempt_id": (
                self.request.route_identity.route_attempt.route_attempt_id
            ),
            "decision_point_id": (
                self.request.route_identity.decision_point.decision_point_id
            ),
            "transaction_id": self.request.route_identity.transaction.transaction_id,
            "blocker": self.blocker.value,
            "blocked_stage": self.stage.value,
            "leaf_name_sha256": self.leaf_name_sha256,
            "leaf_was_created": self.leaf_was_created,
            "leaf_was_removed": self.leaf_was_removed,
            "cleanup_complete": (not self.leaf_was_created or self.leaf_was_removed),
            "attempt_terminal_issued": False,
            "noncertificate_closure_issued": False,
            "child_launch_attempted": False,
            "counter_record_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            **_formal_locks(),
        }

    @property
    def result_id(self) -> str:
        if (
            self.request.request_id,
            self.admission_result.result_id,
        ) != self._validated_ids:
            _fail("cgroup prelaunch blocker authority changed")
        current = _hash(
            V075_K7_CGROUP_LEASE_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN,
            self._payload(),
        )
        if current != self._result_id:
            _fail("cgroup prelaunch blocker changed after issuance")
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cgroup_lease_blocked_result_id": self.result_id}


class K7CgroupAttemptLeaseV1:
    """Process-local ownership of one configured, still-empty cgroup leaf."""

    __slots__ = (
        "_owner_pid",
        "_parent_fd",
        "_leaf_fd",
        "_leaf_name",
        "_leaf_status",
        "_parent_status",
        "_request",
        "_admission_result",
        "_lease_id",
        "_closed",
    )

    def __init__(
        self,
        issuer: object,
        *,
        parent_fd: int,
        leaf_fd: int,
        leaf_name: str,
        request: successor.V075K7ParentOwnedSuccessorRequestV1,
        admission_result: admission.K7OSSupervisorAdmissionResultV1,
    ) -> None:
        if issuer is not _LEASE_ISSUER:
            _fail("cgroup lease is runtime-issuer-owned")
        self._owner_pid = os.getpid()
        self._parent_fd = parent_fd
        self._leaf_fd = leaf_fd
        self._leaf_name = leaf_name
        self._parent_status = os.fstat(parent_fd)
        self._leaf_status = os.fstat(leaf_fd)
        self._request = request
        self._admission_result = admission_result
        self._closed = False
        self._lease_id = _hash(
            V075_K7_CGROUP_LEASE_AUTHORITY_V1_DOMAIN, self._payload()
        )

    def _check_process(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("cgroup lease cannot cross a process boundary")

    def _assert_live(self) -> None:
        self._check_process()
        if self._closed:
            _fail("cgroup lease is closed")
        self._request._assert_current()  # noqa: SLF001
        admission.verify_v075_k7_os_supervisor_admission_v1(
            self._admission_result
        )
        try:
            parent_status = os.fstat(self._parent_fd)
            leaf_status = os.fstat(self._leaf_fd)
            filesystems = (
                _fstatfs_magic(self._parent_fd),
                _fstatfs_magic(self._leaf_fd),
            )
        except OSError as error:
            raise V075K7CgroupLeaseV1Error(
                "cgroup lease descriptor is no longer live"
            ) from error
        if (
            _descriptor_payload(parent_status)
            != _descriptor_payload(self._parent_status)
            or _descriptor_payload(leaf_status)
            != _descriptor_payload(self._leaf_status)
            or filesystems != (CGROUP2_SUPER_MAGIC, CGROUP2_SUPER_MAGIC)
        ):
            _fail("cgroup lease descriptor identity changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_cgroup_lease_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "cgroup_lease_profile_id": _OFFICIAL_PROFILE.profile_id,
            "successor_request_id": self._request.request_id,
            "os_supervisor_admission_result_id": self._admission_result.result_id,
            "parent_descriptor_identity": _descriptor_payload(self._parent_status),
            "leaf_descriptor_identity": _descriptor_payload(self._leaf_status),
            "leaf_name_sha256": hashlib.sha256(
                self._leaf_name.encode("ascii")
            ).hexdigest(),
            "cgroup2_magic_verified": True,
            "required_controllers_delegated": list(REQUIRED_CONTROLLERS),
            "control_readbacks": dict(CONTROL_READBACKS),
            "leaf_initially_empty_verified": True,
            "process_local": True,
            "pickle_allowed": False,
            "child_launch_attempted": False,
            **_formal_locks(),
        }

    @property
    def lease_id(self) -> str:
        self._assert_live()
        return self._lease_id

    @property
    def leaf_fd(self) -> int:
        self._assert_live()
        return self._leaf_fd

    def to_document(self) -> dict[str, Any]:
        self._assert_live()
        return {**self._payload(), "cgroup_lease_id": self._lease_id}

    def close(self) -> None:
        self._check_process()
        if self._closed:
            return
        named_fd = -1
        try:
            self._assert_live()
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            named_fd = os.open(self._leaf_name, flags, dir_fd=self._parent_fd)
            named_status = os.fstat(named_fd)
            if (
                named_status.st_dev,
                named_status.st_ino,
            ) != (self._leaf_status.st_dev, self._leaf_status.st_ino):
                _fail("cgroup lease name no longer identifies its owned leaf")
            _validate_empty_leaf(self._leaf_fd)
            os.rmdir(self._leaf_name, dir_fd=self._parent_fd)
        except (OSError, V075K7CgroupLeaseV1Error) as error:
            if isinstance(error, V075K7CgroupLeaseCleanupV1Error):
                raise
            raise V075K7CgroupLeaseCleanupV1Error(
                "cgroup lease close could not prove removal of its owned leaf"
            ) from error
        finally:
            if named_fd >= 0:
                os.close(named_fd)
            os.close(self._leaf_fd)
            os.close(self._parent_fd)
            self._closed = True

    def __enter__(self) -> "K7CgroupAttemptLeaseV1":
        self._check_process()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def __reduce__(self):
        raise TypeError("K7 cgroup lease is process-local and unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("K7 cgroup lease is process-local and unpickleable")

    def __copy__(self):
        raise TypeError("K7 cgroup lease cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]):
        raise TypeError("K7 cgroup lease cannot be copied")


def _blocked(
    request: successor.V075K7ParentOwnedSuccessorRequestV1,
    admission_result: admission.K7OSSupervisorAdmissionResultV1,
    blocker: K7CgroupLeaseBlockerV1,
    stage: K7CgroupLeaseStageV1,
    leaf_name: str | None,
    created: bool,
    removed: bool,
) -> K7CgroupLeasePrelaunchBlockedResultV1:
    marker = "NOT_CREATED" if leaf_name is None else leaf_name
    return K7CgroupLeasePrelaunchBlockedResultV1(
        _BLOCKED_ISSUER,
        request,
        admission_result,
        blocker,
        stage,
        hashlib.sha256(marker.encode("ascii")).hexdigest(),
        created,
        removed,
    )


def _cleanup_failed_setup(
    *, parent_fd: int, leaf_fd: int, leaf_name: str
) -> None:
    if leaf_fd >= 0:
        os.close(leaf_fd)
    try:
        os.rmdir(leaf_name, dir_fd=parent_fd)
    except OSError as error:
        raise V075K7CgroupLeaseCleanupV1Error(
            "failed cgroup setup left an unremovable attempt leaf"
        ) from error


def acquire_v075_k7_cgroup_attempt_lease_v1(
    *,
    request: successor.V075K7ParentOwnedSuccessorRequestV1,
    admission_result: admission.K7OSSupervisorAdmissionResultV1,
    delegated_parent_fd: int,
    nonce_token: K7CgroupLeaseNonceTokenV1,
) -> K7CgroupAttemptLeaseV1 | K7CgroupLeasePrelaunchBlockedResultV1:
    """Acquire one empty configured leaf, or return a cleaned typed blocker."""

    if type(request) is not successor.V075K7ParentOwnedSuccessorRequestV1:
        _fail("cgroup lease requires the exact successor request")
    if type(admission_result) is not admission.K7OSSupervisorAdmissionResultV1:
        _fail("cgroup lease requires the exact V0-102 admission result")
    if type(delegated_parent_fd) is not int or delegated_parent_fd < 0:
        _fail("delegated parent descriptor must be a nonnegative exact integer")
    request._assert_current()  # noqa: SLF001
    # Parent-owned, single-use consumption precedes every cgroup mutation.
    _NONCE_SERVICE.consume(
        nonce_token, request, admission_result, delegated_parent_fd
    )
    admission.verify_v075_k7_os_supervisor_admission_v1(admission_result)

    if admission_result.profile is not request.profile.admission_profile:
        return _blocked(
            request,
            admission_result,
            K7CgroupLeaseBlockerV1.ADMISSION_AUTHORITY_CROSSED,
            K7CgroupLeaseStageV1.AUTHORITY,
            None,
            False,
            False,
        )
    fact = admission_result.probe.delegated_parent_fact
    if not admission_result.probe.delegated_parent_fd_supplied or not fact.exists:
        return _blocked(
            request,
            admission_result,
            K7CgroupLeaseBlockerV1.ADMISSION_DESCRIPTOR_NOT_BOUND,
            K7CgroupLeaseStageV1.AUTHORITY,
            None,
            False,
            False,
        )
    if not sys.platform.startswith("linux"):
        return _blocked(
            request,
            admission_result,
            K7CgroupLeaseBlockerV1.NOT_LINUX,
            K7CgroupLeaseStageV1.DESCRIPTOR,
            None,
            False,
            False,
        )

    try:
        caller_status = os.fstat(delegated_parent_fd)
    except OSError:
        return _blocked(
            request,
            admission_result,
            K7CgroupLeaseBlockerV1.DESCRIPTOR_IDENTITY_MISMATCH,
            K7CgroupLeaseStageV1.DESCRIPTOR,
            None,
            False,
            False,
        )
    expected = (fact.device, fact.inode, fact.mode, fact.owner_uid, fact.owner_gid)
    observed = (
        caller_status.st_dev,
        caller_status.st_ino,
        stat.S_IMODE(caller_status.st_mode),
        caller_status.st_uid,
        caller_status.st_gid,
    )
    try:
        target_sha256 = hashlib.sha256(
            os.readlink(f"/proc/self/fd/{delegated_parent_fd}").encode("utf-8")
        ).hexdigest()
    except OSError:
        target_sha256 = ""
    if (
        expected != observed
        or observed != nonce_token._descriptor_identity  # noqa: SLF001
        or target_sha256 != fact.path_sha256
        or target_sha256 != nonce_token._descriptor_target_sha256  # noqa: SLF001
    ):
        return _blocked(
            request,
            admission_result,
            K7CgroupLeaseBlockerV1.DESCRIPTOR_IDENTITY_MISMATCH,
            K7CgroupLeaseStageV1.DESCRIPTOR,
            None,
            False,
            False,
        )
    if not stat.S_ISDIR(caller_status.st_mode):
        return _blocked(
            request,
            admission_result,
            K7CgroupLeaseBlockerV1.DESCRIPTOR_NOT_DIRECTORY,
            K7CgroupLeaseStageV1.DESCRIPTOR,
            None,
            False,
            False,
        )

    parent_fd = -1
    leaf_fd = -1
    leaf_name: str | None = None
    created = False
    try:
        try:
            parent_fd = os.dup(delegated_parent_fd)
            os.set_inheritable(parent_fd, False)
        except OSError:
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.DESCRIPTOR_DUPLICATION_FAILED,
                K7CgroupLeaseStageV1.DESCRIPTOR,
                None,
                False,
                False,
            )
        if _descriptor_payload(os.fstat(parent_fd)) != _descriptor_payload(
            caller_status
        ):
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.DESCRIPTOR_IDENTITY_MISMATCH,
                K7CgroupLeaseStageV1.DESCRIPTOR,
                None,
                False,
                False,
            )
        try:
            magic = _fstatfs_magic(parent_fd)
        except (OSError, V075K7CgroupLeaseV1Error):
            magic = -1
        if magic != CGROUP2_SUPER_MAGIC:
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.NOT_CGROUP2_FILESYSTEM,
                K7CgroupLeaseStageV1.FILESYSTEM,
                None,
                False,
                False,
            )

        try:
            controllers = _parse_controller_tokens(
                _read_control(parent_fd, "cgroup.controllers"),
                "cgroup.controllers",
            )
            subtree = _parse_controller_tokens(
                _read_control(parent_fd, "cgroup.subtree_control"),
                "cgroup.subtree_control",
            )
        except (OSError, V075K7CgroupLeaseV1Error):
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.PARENT_CONTROLLER_READ_FAILED,
                K7CgroupLeaseStageV1.DELEGATION,
                None,
                False,
                False,
            )
        if not set(REQUIRED_CONTROLLERS) <= set(controllers) or not set(
            REQUIRED_CONTROLLERS
        ) <= set(subtree):
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.REQUIRED_CONTROLLER_NOT_DELEGATED,
                K7CgroupLeaseStageV1.DELEGATION,
                None,
                False,
                False,
            )

        leaf_name = f"acfqp-{request.request_id[:20]}-{secrets.token_hex(8)}"
        try:
            os.mkdir(leaf_name, mode=0o700, dir_fd=parent_fd)
            created = True
        except OSError:
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.UNIQUE_LEAF_CREATION_FAILED,
                K7CgroupLeaseStageV1.CREATE,
                leaf_name,
                False,
                False,
            )
        try:
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            leaf_fd = os.open(leaf_name, flags, dir_fd=parent_fd)
            os.set_inheritable(leaf_fd, False)
        except OSError:
            owned_leaf_fd = leaf_fd
            leaf_fd = -1
            _cleanup_failed_setup(
                parent_fd=parent_fd,
                leaf_fd=owned_leaf_fd,
                leaf_name=leaf_name,
            )
            created = False
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.LEAF_OPEN_FAILED,
                K7CgroupLeaseStageV1.CREATE,
                leaf_name,
                True,
                True,
            )
        try:
            leaf_magic = _fstatfs_magic(leaf_fd)
        except (OSError, V075K7CgroupLeaseV1Error):
            leaf_magic = -1
        if leaf_magic != CGROUP2_SUPER_MAGIC:
            owned_leaf_fd = leaf_fd
            leaf_fd = -1
            _cleanup_failed_setup(
                parent_fd=parent_fd,
                leaf_fd=owned_leaf_fd,
                leaf_name=leaf_name,
            )
            created = False
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.LEAF_FILESYSTEM_MISMATCH,
                K7CgroupLeaseStageV1.CREATE,
                leaf_name,
                True,
                True,
            )
        try:
            for name in REQUIRED_LEAF_FILES:
                _read_control(leaf_fd, name)
        except (OSError, V075K7CgroupLeaseV1Error):
            owned_leaf_fd = leaf_fd
            leaf_fd = -1
            _cleanup_failed_setup(
                parent_fd=parent_fd,
                leaf_fd=owned_leaf_fd,
                leaf_name=leaf_name,
            )
            created = False
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.REQUIRED_LEAF_FILE_MISSING,
                K7CgroupLeaseStageV1.VALIDATE_EMPTY,
                leaf_name,
                True,
                True,
            )
        try:
            initial_blocker = _validate_initial_leaf(leaf_fd)
        except (OSError, V075K7CgroupLeaseV1Error):
            initial_blocker = K7CgroupLeaseBlockerV1.LEAF_NOT_INITIALLY_EMPTY
        if initial_blocker is not None:
            owned_leaf_fd = leaf_fd
            leaf_fd = -1
            _cleanup_failed_setup(
                parent_fd=parent_fd,
                leaf_fd=owned_leaf_fd,
                leaf_name=leaf_name,
            )
            created = False
            return _blocked(
                request,
                admission_result,
                initial_blocker,
                K7CgroupLeaseStageV1.VALIDATE_EMPTY,
                leaf_name,
                True,
                True,
            )
        try:
            for name, value in CONTROL_READBACKS.items():
                _write_control(leaf_fd, name, value)
        except (OSError, V075K7CgroupLeaseV1Error):
            owned_leaf_fd = leaf_fd
            leaf_fd = -1
            _cleanup_failed_setup(
                parent_fd=parent_fd,
                leaf_fd=owned_leaf_fd,
                leaf_name=leaf_name,
            )
            created = False
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.CONTROL_WRITE_FAILED,
                K7CgroupLeaseStageV1.CONFIGURE,
                leaf_name,
                True,
                True,
            )
        try:
            readbacks_match = all(
                _readback_matches(_read_control(leaf_fd, name), value, name)
                for name, value in CONTROL_READBACKS.items()
            )
        except (OSError, V075K7CgroupLeaseV1Error):
            readbacks_match = False
        if not readbacks_match:
            owned_leaf_fd = leaf_fd
            leaf_fd = -1
            _cleanup_failed_setup(
                parent_fd=parent_fd,
                leaf_fd=owned_leaf_fd,
                leaf_name=leaf_name,
            )
            created = False
            return _blocked(
                request,
                admission_result,
                K7CgroupLeaseBlockerV1.CONTROL_READBACK_MISMATCH,
                K7CgroupLeaseStageV1.CONFIGURE,
                leaf_name,
                True,
                True,
            )

        lease = K7CgroupAttemptLeaseV1(
            _LEASE_ISSUER,
            parent_fd=parent_fd,
            leaf_fd=leaf_fd,
            leaf_name=leaf_name,
            request=request,
            admission_result=admission_result,
        )
        parent_fd = -1
        leaf_fd = -1
        created = False
        return lease
    finally:
        cleanup_error: V075K7CgroupLeaseCleanupV1Error | None = None
        if created and leaf_name is not None and parent_fd >= 0:
            owned_leaf_fd = leaf_fd
            leaf_fd = -1
            try:
                _cleanup_failed_setup(
                    parent_fd=parent_fd,
                    leaf_fd=owned_leaf_fd,
                    leaf_name=leaf_name,
                )
            except V075K7CgroupLeaseCleanupV1Error as error:
                cleanup_error = error
        if leaf_fd >= 0:
            os.close(leaf_fd)
        if parent_fd >= 0:
            os.close(parent_fd)
        if cleanup_error is not None:
            raise cleanup_error


__all__ = [
    "ACTUAL_PROJECTION_PROOF_AUTHORIZED",
    "ATTEMPT_TERMINAL_AUTHORIZED",
    "CGROUP2_SUPER_MAGIC",
    "CHILD_LAUNCH_ALLOWED",
    "COMPARISON_VECTOR_AUTHORIZED",
    "COUNTER_RECORD_AUTHORIZED",
    "K7CgroupAttemptLeaseV1",
    "K7CgroupLeaseBlockerV1",
    "K7CgroupLeasePrelaunchBlockedResultV1",
    "K7CgroupLeaseProfileV1",
    "K7CgroupLeaseStageV1",
    "K7CgroupLeaseNonceServiceV1",
    "K7CgroupLeaseNonceTokenV1",
    "LOCAL_DOMAIN_TAGS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "V075K7CgroupLeaseCleanupV1Error",
    "V075K7CgroupLeaseV1Error",
    "WORK_VECTOR_AUTHORIZED",
    "acquire_v075_k7_cgroup_attempt_lease_v1",
    "official_v075_k7_cgroup_lease_profile_v1",
    "official_v075_k7_cgroup_lease_nonce_service_v1",
]
