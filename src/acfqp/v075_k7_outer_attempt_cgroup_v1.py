"""Prepared outer cgroup-v2 hierarchy for one future complete K7 attempt.

The authority creates an empty ancestor plus one empty worker leaf.  It does
not launch the worker and therefore cannot issue a memory measurement or a
formal shared-resource resolution.  A later runtime must consume the lease,
place the worker in the worker leaf from birth, supervise the complete attempt,
and finalize the hierarchical peak after reap and empty-tree closure.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import os
import secrets
import stat
import sys
import threading
import time
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_cgroup_lease_v1 as inner_v1
from acfqp import v075_k7_os_supervisor_admission_v1 as admission_v1
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_OUTER_ATTEMPT_CGROUP_BLOCKED_RESULT_V1_DOMAIN,
    V075_K7_OUTER_ATTEMPT_CGROUP_LEASE_V1_DOMAIN,
    V075_K7_OUTER_ATTEMPT_CGROUP_PROFILE_V1_DOMAIN,
    V075_K7_OUTER_ATTEMPT_MEMORY_EVIDENCE_V1_DOMAIN,
    content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.3"
PROFILE_KEY = "v075_k7_outer_attempt_cgroup_v1"
FIXED_OUTER_MEMORY_MAX_BYTES = 4 * 1024 * 1024 * 1024
REQUIRED_CONTROLLERS = ("memory", "pids")
OUTER_CONTROL_READBACKS = (
    ("memory.max", str(FIXED_OUTER_MEMORY_MAX_BYTES)),
    ("memory.swap.max", "0"),
    ("pids.max", "2"),
    ("cgroup.max.depth", "1"),
    ("cgroup.max.descendants", "2"),
)
WORKER_CONTROL_READBACKS = (
    ("pids.max", "1"),
    ("cgroup.max.depth", "0"),
    ("cgroup.max.descendants", "0"),
)
OUTER_REQUIRED_FILES = tuple(
    sorted(
        {
            *admission_v1.REQUIRED_LEAF_FILES,
            "cgroup.controllers",
            "cgroup.kill",
            "cgroup.stat",
            "cgroup.subtree_control",
            "memory.max",
            "memory.swap.max",
        }
    )
)
WORKER_REQUIRED_FILES = admission_v1.REQUIRED_LEAF_FILES
MAX_DYING_DESCENDANT_WAIT_MILLISECONDS = 10_000
REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_OUTER_ATTEMPT_CGROUP_PROFILE_V1_DOMAIN",
    "V075_K7_OUTER_ATTEMPT_CGROUP_LEASE_V1_DOMAIN",
    "V075_K7_OUTER_ATTEMPT_CGROUP_BLOCKED_RESULT_V1_DOMAIN",
    "V075_K7_OUTER_ATTEMPT_MEMORY_EVIDENCE_V1_DOMAIN",
)
LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_OUTER_ATTEMPT_CGROUP_PROFILE_V1_DOMAIN,
        V075_K7_OUTER_ATTEMPT_CGROUP_LEASE_V1_DOMAIN,
        V075_K7_OUTER_ATTEMPT_CGROUP_BLOCKED_RESULT_V1_DOMAIN,
        V075_K7_OUTER_ATTEMPT_MEMORY_EVIDENCE_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("outer-attempt cgroup domains are unregistered")

_PROFILE_ISSUER = object()
_TOKEN_ISSUER = object()
_LEASE_ISSUER = object()
_CLEANUP_GUARD_ISSUER = object()
_BLOCKED_ISSUER = object()


class V075K7OuterAttemptCgroupV1Error(RuntimeError):
    """An outer hierarchy input, identity, or lifecycle invariant failed."""


class V075K7OuterAttemptCgroupCleanupV1Error(
    V075K7OuterAttemptCgroupV1Error
):
    """The owned hierarchy could not be proved empty and removed."""

    def __init__(
        self,
        message: str,
        *,
        cleanup_guard: K7OuterAttemptCgroupCleanupGuardV1 | None = None,
    ) -> None:
        super().__init__(message)
        self.cleanup_guard = cleanup_guard


class V075K7OuterAttemptCgroupProtocolV1Error(
    V075K7OuterAttemptCgroupV1Error
):
    """Cleanup completed, but a frozen control protocol was violated."""

    def __init__(self, violations: tuple[str, ...]) -> None:
        if (
            type(violations) is not tuple
            or not violations
            or any(type(value) is not str or not value for value in violations)
            or tuple(sorted(set(violations))) != violations
        ):
            _fail("cleanup protocol violations are not canonical")
        super().__init__(
            "unused hierarchy was removed after protocol mismatch: "
            + ",".join(violations)
        )
        self.cleanup_complete = True
        self.violations = violations


class K7OuterAttemptCgroupLeaseStateV1(str, Enum):
    ACTIVE = "ACTIVE"
    CLEANUP_PARTIAL = "CLEANUP_PARTIAL"
    CLOSED = "CLOSED"


class K7OuterAttemptCgroupCleanupStateV1(str, Enum):
    IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD = (
        "IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD"
    )
    CLEANUP_PENDING = "CLEANUP_PENDING"
    CLEANUP_PARTIAL = "CLEANUP_PARTIAL"
    CLOSED = "CLOSED"


class K7OuterAttemptCgroupBlockerV1(str, Enum):
    NOT_LINUX = "NOT_LINUX"
    ADMISSION_AUTHORITY_CROSSED = "ADMISSION_AUTHORITY_CROSSED"
    DESCRIPTOR_IDENTITY_MISMATCH = "DESCRIPTOR_IDENTITY_MISMATCH"
    NOT_CGROUP2_FILESYSTEM = "NOT_CGROUP2_FILESYSTEM"
    REQUIRED_CONTROLLER_NOT_DELEGATED = "REQUIRED_CONTROLLER_NOT_DELEGATED"
    OUTER_CREATE_FAILED = "OUTER_CREATE_FAILED"
    OUTER_VALIDATION_FAILED = "OUTER_VALIDATION_FAILED"
    OUTER_CONFIGURATION_FAILED = "OUTER_CONFIGURATION_FAILED"
    SUBTREE_ENABLE_FAILED = "SUBTREE_ENABLE_FAILED"
    WORKER_CREATE_FAILED = "WORKER_CREATE_FAILED"
    WORKER_VALIDATION_FAILED = "WORKER_VALIDATION_FAILED"
    WORKER_CONFIGURATION_FAILED = "WORKER_CONFIGURATION_FAILED"
    FINAL_SNAPSHOT_VALIDATION_FAILED = "FINAL_SNAPSHOT_VALIDATION_FAILED"


class K7OuterAttemptCgroupStageV1(str, Enum):
    AUTHORITY = "AUTHORITY"
    DESCRIPTOR = "DESCRIPTOR"
    FILESYSTEM = "FILESYSTEM"
    DELEGATION = "DELEGATION"
    OUTER_CREATE = "OUTER_CREATE"
    OUTER_CONFIGURE = "OUTER_CONFIGURE"
    WORKER_CREATE = "WORKER_CREATE"
    WORKER_CONFIGURE = "WORKER_CONFIGURE"
    FINAL_SNAPSHOT = "FINAL_SNAPSHOT"


def _fail(message: str) -> NoReturn:
    raise V075K7OuterAttemptCgroupV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("outer-attempt cgroup used an undeclared domain")
    return content_id(domain, dict(payload))


def _locks() -> dict[str, bool]:
    return {
        "worker_launch_implemented": False,
        "worker_launched_from_birth_in_scope": False,
        "complete_attempt_memory_window_verified": False,
        "memory_evidence_issued": False,
        "eligible_as_shared_resource_resolution": False,
        "process_broker_implemented": False,
        "exclusive_parent_writer_verified": False,
        "atomic_name_to_inode_delete_verified": False,
        "guardian_cleanup_authority_bound": False,
        "launch_baseline_memory_peak_reset_verified": False,
        "safe_for_exact_runtime_consumption": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "formal_vector_authorized": False,
        "attempt_terminal_issued": False,
        "official_execution_allowed": False,
    }


def _descriptor_tuple(status: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        status.st_dev,
        status.st_ino,
        stat.S_IMODE(status.st_mode),
        status.st_uid,
        status.st_gid,
    )


def _descriptor_document(status: os.stat_result) -> dict[str, int]:
    device, inode, mode, owner_uid, owner_gid = _descriptor_tuple(status)
    return {
        "device": device,
        "inode": inode,
        "mode": mode,
        "owner_uid": owner_uid,
        "owner_gid": owner_gid,
    }


def _descriptor_target_sha256(descriptor: int) -> str:
    return hashlib.sha256(
        os.readlink(f"/proc/self/fd/{descriptor}").encode("utf-8")
    ).hexdigest()


def _open_directory(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=parent_fd)
    os.set_inheritable(descriptor, False)
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):  # pragma: no cover
        os.close(descriptor)
        _fail("opened cgroup component is not a directory")
    return descriptor


def _control_text(directory_fd: int, name: str) -> str:
    return inner_v1._parse_ascii(  # noqa: SLF001
        inner_v1._read_control(directory_fd, name),  # noqa: SLF001
        name,
    ).strip()


def _controls_match(
    directory_fd: int, rows: tuple[tuple[str, str], ...]
) -> bool:
    return all(_control_text(directory_fd, name) == value for name, value in rows)


def _cgroup_stat(directory_fd: int) -> dict[str, int]:
    result: dict[str, int] = {}
    raw = inner_v1._parse_ascii(  # noqa: SLF001
        inner_v1._read_control(directory_fd, "cgroup.stat"),  # noqa: SLF001
        "cgroup.stat",
    )
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) != 2 or fields[0] in result or not fields[1].isdigit():
            _fail("cgroup.stat is malformed or duplicated")
        result[fields[0]] = int(fields[1])
    if not {"nr_descendants", "nr_dying_descendants"} <= set(result):
        _fail("cgroup.stat lacks descendant closure fields")
    return result


def _wait_descendant_counts(
    directory_fd: int, *, expected_descendants: int
) -> None:
    deadline = (
        time.monotonic_ns()
        + MAX_DYING_DESCENDANT_WAIT_MILLISECONDS * 1_000_000
    )
    while True:
        rows = _cgroup_stat(directory_fd)
        if (
            rows["nr_descendants"] == expected_descendants
            and rows["nr_dying_descendants"] == 0
        ):
            return
        if time.monotonic_ns() >= deadline:
            raise V075K7OuterAttemptCgroupCleanupV1Error(
                "cgroup descendants did not leave the dying state"
            )
        time.sleep(0.01)


def _validate_fresh_domain(directory_fd: int) -> None:
    inner_v1._validate_empty_leaf(directory_fd)  # noqa: SLF001
    if _control_text(directory_fd, "cgroup.type") != "domain":
        _fail("outer hierarchy node is not a domain cgroup")
    if inner_v1._parse_nonnegative(  # noqa: SLF001
        inner_v1._read_control(directory_fd, "memory.peak"),  # noqa: SLF001
        "memory.peak",
    ) != 0:
        _fail("fresh outer hierarchy node has nonzero memory.peak")


def _verify_named_descriptor(
    parent_fd: int,
    name: str,
    expected: os.stat_result,
) -> None:
    descriptor = _open_directory(parent_fd, name)
    try:
        if _descriptor_tuple(os.fstat(descriptor)) != _descriptor_tuple(expected):
            _fail("owned cgroup name was replaced")
    finally:
        os.close(descriptor)


class K7OuterAttemptCgroupCleanupGuardV1:
    """Process-local descriptor authority retained after failed setup cleanup."""

    __slots__ = (
        "_owner_pid",
        "_parent_fd",
        "_outer_fd",
        "_worker_fd",
        "_outer_name",
        "_worker_name",
        "_parent_status",
        "_outer_status",
        "_worker_status",
        "_worker_removed",
        "_outer_removed",
        "_state",
    )

    def __init__(
        self,
        issuer: object,
        *,
        parent_fd: int,
        outer_fd: int,
        worker_fd: int,
        outer_name: str | None,
        worker_name: str | None,
        parent_status: os.stat_result,
        outer_status: os.stat_result | None,
        worker_status: os.stat_result | None,
    ) -> None:
        if issuer is not _CLEANUP_GUARD_ISSUER:
            _fail("outer-attempt cleanup guard is issuer-owned")
        self._owner_pid = os.getpid()
        self._parent_fd = parent_fd
        self._outer_fd = outer_fd
        self._worker_fd = worker_fd
        self._outer_name = outer_name
        self._worker_name = worker_name
        self._parent_status = parent_status
        self._outer_status = outer_status
        self._worker_status = worker_status
        self._worker_removed = worker_name is None
        self._outer_removed = outer_name is None
        identity_unbound = (
            outer_name is not None and outer_status is None
        ) or (worker_name is not None and worker_status is None)
        self._state = (
            K7OuterAttemptCgroupCleanupStateV1.IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD
            if identity_unbound
            else K7OuterAttemptCgroupCleanupStateV1.CLEANUP_PENDING
        )

    def _check_process(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("outer-attempt cleanup guard crossed a process boundary")

    def _open_missing_descriptors(self) -> None:
        if (
            self._parent_fd < 0
            or _descriptor_tuple(os.fstat(self._parent_fd))
            != _descriptor_tuple(self._parent_status)
        ):
            _fail("cleanup parent descriptor identity changed")
        if not self._outer_removed and self._outer_fd < 0:
            if self._outer_name is None or self._outer_status is None:
                _fail("cleanup lacks a bound outer descriptor identity")
            descriptor = _open_directory(self._parent_fd, self._outer_name)
            if _descriptor_tuple(os.fstat(descriptor)) != _descriptor_tuple(
                self._outer_status
            ):
                os.close(descriptor)
                _fail("owned outer cgroup name was replaced")
            self._outer_fd = descriptor
        if not self._worker_removed and self._worker_fd < 0:
            if self._worker_name is None or self._worker_status is None:
                _fail("cleanup lacks a bound worker descriptor identity")
            descriptor = _open_directory(self._outer_fd, self._worker_name)
            if _descriptor_tuple(os.fstat(descriptor)) != _descriptor_tuple(
                self._worker_status
            ):
                os.close(descriptor)
                _fail("owned worker cgroup name was replaced")
            self._worker_fd = descriptor

    def retry_cleanup(self) -> None:
        """Resume identity-matched empty-tree deletion without other authority."""

        self._check_process()
        if self._state is K7OuterAttemptCgroupCleanupStateV1.CLOSED:
            _fail("outer-attempt cleanup guard is closed")
        if self._state is (
            K7OuterAttemptCgroupCleanupStateV1.IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD
        ):
            raise V075K7OuterAttemptCgroupCleanupV1Error(
                "pre-identity setup cleanup requires an external parent guardian",
                cleanup_guard=self,
            )
        try:
            self._open_missing_descriptors()
            self._state = K7OuterAttemptCgroupCleanupStateV1.CLEANUP_PARTIAL
            if not self._worker_removed:
                if (
                    self._outer_name is None
                    or self._worker_name is None
                    or self._outer_status is None
                    or self._worker_status is None
                ):
                    _fail("cleanup worker identity is incomplete")
                _verify_named_descriptor(
                    self._parent_fd, self._outer_name, self._outer_status
                )
                _verify_named_descriptor(
                    self._outer_fd, self._worker_name, self._worker_status
                )
                os.rmdir(self._worker_name, dir_fd=self._outer_fd)
                self._worker_removed = True
                descriptor = self._worker_fd
                self._worker_fd = -1
                os.close(descriptor)
            if not self._outer_removed:
                if self._outer_name is None or self._outer_status is None:
                    _fail("cleanup outer identity is incomplete")
                if (
                    inner_v1._fstatfs_magic(self._outer_fd)  # noqa: SLF001
                    == inner_v1.CGROUP2_SUPER_MAGIC
                ):
                    _wait_descendant_counts(
                        self._outer_fd, expected_descendants=0
                    )
                _verify_named_descriptor(
                    self._parent_fd, self._outer_name, self._outer_status
                )
                os.rmdir(self._outer_name, dir_fd=self._parent_fd)
                self._outer_removed = True
                descriptor = self._outer_fd
                self._outer_fd = -1
                os.close(descriptor)
            descriptor = self._parent_fd
            self._parent_fd = -1
            os.close(descriptor)
            self._state = K7OuterAttemptCgroupCleanupStateV1.CLOSED
        except BaseException as error:
            if (
                isinstance(error, V075K7OuterAttemptCgroupCleanupV1Error)
                and error.cleanup_guard is self
            ):
                raise
            raise V075K7OuterAttemptCgroupCleanupV1Error(
                "failed setup retained a retryable cleanup guard",
                cleanup_guard=self,
            ) from error

    @property
    def cleanup_state(self) -> K7OuterAttemptCgroupCleanupStateV1:
        self._check_process()
        return self._state

    @property
    def closed(self) -> bool:
        return self.cleanup_state is K7OuterAttemptCgroupCleanupStateV1.CLOSED

    def __reduce__(self):
        raise TypeError("outer-attempt cleanup guard is unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("outer-attempt cleanup guard is unpickleable")


@dataclass(frozen=True, slots=True)
class K7OuterAttemptCgroupProfileV1:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("outer-attempt cgroup profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(V075_K7_OUTER_ATTEMPT_CGROUP_PROFILE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_outer_attempt_cgroup_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "readiness_level": "PREP_ONLY",
            "required_controllers": list(REQUIRED_CONTROLLERS),
            "outer_control_readbacks": [
                {"file": name, "value": value}
                for name, value in OUTER_CONTROL_READBACKS
            ],
            "worker_control_readbacks": [
                {"file": name, "value": value}
                for name, value in WORKER_CONTROL_READBACKS
            ],
            "outer_required_files": list(OUTER_REQUIRED_FILES),
            "worker_required_files": list(WORKER_REQUIRED_FILES),
            "topology": "EMPTY_ANCESTOR_WITH_WORKER_AND_FUTURE_BUSINESS_SIBLING",
            "external_supervisor_inside_charged_attempt": False,
            "ancestor_memory_peak_is_hierarchical": True,
            "leaf_peak_max_or_sum_accepted": False,
            "pids_max_is_cumulative_launch_count": False,
            "normal_future_process_launch_count": 2,
            "process_connection_status": "EXTERNAL_BROKER_NOT_IMPLEMENTED",
            "memory_connection_status": "OUTER_HIERARCHY_PREP_ONLY",
            "lease_cleanup_states": [
                state.value for state in K7OuterAttemptCgroupLeaseStateV1
            ],
            "partial_cleanup_consumer_access_forbidden": True,
            "post_identity_setup_cleanup_retryable": True,
            "pre_identity_create_cleanup_requires_parent_guard": True,
            **_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _hash(
            V075_K7_OUTER_ATTEMPT_CGROUP_PROFILE_V1_DOMAIN, self._payload()
        ) != self._profile_id:
            _fail("outer-attempt cgroup profile changed after freeze")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outer_attempt_cgroup_profile_id": self.profile_id}


_OFFICIAL_PROFILE = K7OuterAttemptCgroupProfileV1(_PROFILE_ISSUER)


def official_v075_k7_outer_attempt_cgroup_profile_v1(
) -> K7OuterAttemptCgroupProfileV1:
    return _OFFICIAL_PROFILE


class K7OuterAttemptCgroupNonceTokenV1:
    __slots__ = (
        "_owner_pid",
        "_request",
        "_request_id",
        "_request_nonce",
        "_admission",
        "_admission_id",
        "_descriptor",
        "_descriptor_identity",
        "_descriptor_target_sha256",
    )

    def __init__(
        self,
        issuer: object,
        request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
        admission: admission_v1.K7OSSupervisorAdmissionResultV1,
        descriptor: int,
        descriptor_identity: tuple[int, int, int, int, int],
        descriptor_target_sha256: str,
    ) -> None:
        if issuer is not _TOKEN_ISSUER:
            _fail("outer-attempt nonce token is service-issued")
        self._owner_pid = os.getpid()
        self._request = request
        self._request_id = request.request_id
        self._request_nonce = request.request_nonce
        self._admission = admission
        self._admission_id = admission.result_id
        self._descriptor = descriptor
        self._descriptor_identity = descriptor_identity
        self._descriptor_target_sha256 = descriptor_target_sha256

    def __reduce__(self):
        raise TypeError("outer-attempt cgroup nonce is unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("outer-attempt cgroup nonce is unpickleable")


class K7OuterAttemptCgroupNonceServiceV1:
    __slots__ = ("_owner_pid", "_issued", "_consumed", "_lock")

    def __init__(self) -> None:
        self._owner_pid = os.getpid()
        self._issued: dict[int, K7OuterAttemptCgroupNonceTokenV1] = {}
        self._consumed: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def _check_process(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("outer-attempt nonce service crossed a process boundary")

    def issue(
        self,
        *,
        request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
        admission_result: admission_v1.K7OSSupervisorAdmissionResultV1,
        delegated_parent_fd: int,
    ) -> K7OuterAttemptCgroupNonceTokenV1:
        self._check_process()
        if (
            type(request) is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
            or type(admission_result)
            is not admission_v1.K7OSSupervisorAdmissionResultV1
            or type(delegated_parent_fd) is not int
            or delegated_parent_fd < 0
        ):
            _fail("outer-attempt nonce inputs are mistyped")
        request._assert_current()  # noqa: SLF001
        admission_v1.verify_v075_k7_os_supervisor_admission_v1(admission_result)
        if admission_result.profile is not request.profile.admission_profile:
            _fail("outer-attempt request/admission authority is crossed")
        status = os.fstat(delegated_parent_fd)
        identity = _descriptor_tuple(status)
        target_sha256 = _descriptor_target_sha256(delegated_parent_fd)
        fact = admission_result.probe.delegated_parent_fact
        if (
            not admission_result.probe.delegated_parent_fd_supplied
            or not fact.exists
            or identity
            != (fact.device, fact.inode, fact.mode, fact.owner_uid, fact.owner_gid)
            or target_sha256 != fact.path_sha256
        ):
            _fail("outer-attempt descriptor differs from admission evidence")
        token = K7OuterAttemptCgroupNonceTokenV1(
            _TOKEN_ISSUER,
            request,
            admission_result,
            delegated_parent_fd,
            identity,
            target_sha256,
        )
        key = (request.request_id, request.request_nonce)
        with self._lock:
            if key in self._consumed:
                _fail("outer-attempt request nonce was already consumed")
            self._issued[id(token)] = token
        return token

    def consume(
        self,
        token: K7OuterAttemptCgroupNonceTokenV1,
        request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
        admission_result: admission_v1.K7OSSupervisorAdmissionResultV1,
        delegated_parent_fd: int,
    ) -> None:
        self._check_process()
        if (
            type(token) is not K7OuterAttemptCgroupNonceTokenV1
            or token._owner_pid != self._owner_pid  # noqa: SLF001
            or token._request is not request  # noqa: SLF001
            or token._request_id != request.request_id  # noqa: SLF001
            or token._request_nonce != request.request_nonce  # noqa: SLF001
            or token._admission is not admission_result  # noqa: SLF001
            or token._admission_id != admission_result.result_id  # noqa: SLF001
            or token._descriptor != delegated_parent_fd  # noqa: SLF001
        ):
            _fail("outer-attempt nonce token is crossed or stale")
        key = (token._request_id, token._request_nonce)  # noqa: SLF001
        with self._lock:
            if key in self._consumed:
                _fail("outer-attempt request nonce was already consumed")
            if self._issued.pop(id(token), None) is not token:
                _fail("outer-attempt nonce token was not issued by this service")
            self._consumed.add(key)

    def __reduce__(self):
        raise TypeError("outer-attempt cgroup nonce service is unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("outer-attempt cgroup nonce service is unpickleable")


_NONCE_SERVICE = K7OuterAttemptCgroupNonceServiceV1()


def official_v075_k7_outer_attempt_cgroup_nonce_service_v1(
) -> K7OuterAttemptCgroupNonceServiceV1:
    return _NONCE_SERVICE


@dataclass(frozen=True, slots=True)
class K7OuterAttemptCgroupBlockedResultV1:
    _issuer: InitVar[object]
    request_id: str
    route_identity_id: str
    admission_result_id: str
    blocker: K7OuterAttemptCgroupBlockerV1
    stage: K7OuterAttemptCgroupStageV1
    outer_created: bool
    worker_created: bool
    cleanup_complete: bool
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BLOCKED_ISSUER:
            _fail("outer-attempt blocker is issuer-owned")
        for value in (self.request_id, self.route_identity_id, self.admission_result_id):
            if (
                type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                _fail("outer-attempt blocker identity is invalid")
        try:
            blocker = K7OuterAttemptCgroupBlockerV1(self.blocker)
            stage = K7OuterAttemptCgroupStageV1(self.stage)
        except (TypeError, ValueError) as error:
            raise V075K7OuterAttemptCgroupV1Error(
                "outer-attempt blocker enum is invalid"
            ) from error
        if (
            type(self.outer_created) is not bool
            or type(self.worker_created) is not bool
            or type(self.cleanup_complete) is not bool
            or self.worker_created and not self.outer_created
            or (self.outer_created or self.worker_created) and not self.cleanup_complete
        ):
            _fail("outer-attempt blocker cleanup facts are inconsistent")
        object.__setattr__(self, "blocker", blocker)
        object.__setattr__(self, "stage", stage)
        object.__setattr__(
            self,
            "_result_id",
            _hash(
                V075_K7_OUTER_ATTEMPT_CGROUP_BLOCKED_RESULT_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_outer_attempt_cgroup_blocked_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outer_attempt_cgroup_profile_id": _OFFICIAL_PROFILE.profile_id,
            "request_id": self.request_id,
            "route_identity_id": self.route_identity_id,
            "os_supervisor_admission_result_id": self.admission_result_id,
            "blocker": self.blocker.value,
            "blocked_stage": self.stage.value,
            "outer_created": self.outer_created,
            "worker_created": self.worker_created,
            "cleanup_complete": self.cleanup_complete,
            "worker_launch_attempted": False,
            "memory_value_present": False,
            **_locks(),
        }

    @property
    def result_id(self) -> str:
        if _hash(
            V075_K7_OUTER_ATTEMPT_CGROUP_BLOCKED_RESULT_V1_DOMAIN,
            self._payload(),
        ) != self._result_id:
            _fail("outer-attempt blocker changed after issuance")
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outer_attempt_cgroup_blocked_result_id": self.result_id}


class K7OuterAttemptCgroupLeaseV1:
    """Process-local ownership of an empty ancestor and empty worker leaf."""

    __slots__ = (
        "_owner_pid",
        "_parent_fd",
        "_outer_fd",
        "_worker_fd",
        "_outer_name",
        "_worker_name",
        "_parent_status",
        "_outer_status",
        "_worker_status",
        "_request",
        "_admission",
        "_lease_id",
        "_worker_removed",
        "_outer_removed",
        "_protocol_violations",
        "_state",
    )

    def __init__(
        self,
        issuer: object,
        *,
        parent_fd: int,
        outer_fd: int,
        worker_fd: int,
        outer_name: str,
        worker_name: str,
        request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
        admission_result: admission_v1.K7OSSupervisorAdmissionResultV1,
    ) -> None:
        if issuer is not _LEASE_ISSUER:
            _fail("outer-attempt cgroup lease is issuer-owned")
        self._owner_pid = os.getpid()
        self._parent_fd = parent_fd
        self._outer_fd = outer_fd
        self._worker_fd = worker_fd
        self._outer_name = outer_name
        self._worker_name = worker_name
        self._parent_status = os.fstat(parent_fd)
        self._outer_status = os.fstat(outer_fd)
        self._worker_status = os.fstat(worker_fd)
        self._request = request
        self._admission = admission_result
        self._worker_removed = False
        self._outer_removed = False
        self._protocol_violations: list[str] = []
        self._state = K7OuterAttemptCgroupLeaseStateV1.ACTIVE
        self._lease_id = _hash(
            V075_K7_OUTER_ATTEMPT_CGROUP_LEASE_V1_DOMAIN, self._payload()
        )

    def _check_process(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("outer-attempt cgroup lease crossed a process boundary")

    def _assert_cleanup_authority(self) -> None:
        self._check_process()
        if self._state is K7OuterAttemptCgroupLeaseStateV1.CLOSED:
            _fail("outer-attempt cgroup lease is closed")
        parent_valid = (
            self._parent_fd >= 0
            and _descriptor_tuple(os.fstat(self._parent_fd))
            == _descriptor_tuple(self._parent_status)
            and inner_v1._fstatfs_magic(self._parent_fd)  # noqa: SLF001
            == inner_v1.CGROUP2_SUPER_MAGIC
        )
        outer_valid = self._outer_removed or (
            self._outer_fd >= 0
            and _descriptor_tuple(os.fstat(self._outer_fd))
            == _descriptor_tuple(self._outer_status)
            and inner_v1._fstatfs_magic(self._outer_fd)  # noqa: SLF001
            == inner_v1.CGROUP2_SUPER_MAGIC
        )
        worker_valid = self._worker_removed or (
            self._worker_fd >= 0
            and _descriptor_tuple(os.fstat(self._worker_fd))
            == _descriptor_tuple(self._worker_status)
            and inner_v1._fstatfs_magic(self._worker_fd)  # noqa: SLF001
            == inner_v1.CGROUP2_SUPER_MAGIC
        )
        if not parent_valid or not outer_valid or not worker_valid:
            _fail("outer-attempt cgroup descriptor identity changed")

    def _assert_consumable(self) -> None:
        self._check_process()
        if self._state is not K7OuterAttemptCgroupLeaseStateV1.ACTIVE:
            _fail("outer-attempt cgroup lease is not consumable")
        self._assert_cleanup_authority()
        self._request._assert_current()  # noqa: SLF001
        admission_v1.verify_v075_k7_os_supervisor_admission_v1(self._admission)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_outer_attempt_cgroup_lease.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outer_attempt_cgroup_profile_id": _OFFICIAL_PROFILE.profile_id,
            "request_id": self._request.request_id,
            "route_identity_id": self._request.route_identity.route_identity_id,
            "os_supervisor_admission_result_id": self._admission.result_id,
            "parent_descriptor_identity": _descriptor_document(self._parent_status),
            "outer_descriptor_identity": _descriptor_document(self._outer_status),
            "worker_descriptor_identity": _descriptor_document(self._worker_status),
            "outer_name_sha256": hashlib.sha256(
                self._outer_name.encode("ascii")
            ).hexdigest(),
            "worker_name_sha256": hashlib.sha256(
                self._worker_name.encode("ascii")
            ).hexdigest(),
            "initial_outer_empty_verified": True,
            "initial_worker_empty_verified": True,
            "pre_descendant_creation_memory_peak_zero_verified": True,
            "launch_baseline_memory_peak_value": None,
            "launch_baseline_reset_required": True,
            "launch_baseline_memory_peak_reset_verified": False,
            "cgroup_kill_openability_verified": True,
            "complete_hierarchy_final_snapshot_verified": True,
            "controllers_enabled_before_worker_launch": True,
            "issued_cleanup_state": K7OuterAttemptCgroupLeaseStateV1.ACTIVE.value,
            "partial_cleanup_consumer_access_forbidden": True,
            "cleanup_authority_independent_of_request_currentness": True,
            "process_local": True,
            "pickle_allowed": False,
            "consumed_by_outer_runtime": False,
            **_locks(),
        }

    @property
    def lease_id(self) -> str:
        self._assert_consumable()
        if _hash(
            V075_K7_OUTER_ATTEMPT_CGROUP_LEASE_V1_DOMAIN, self._payload()
        ) != self._lease_id:
            _fail("outer-attempt cgroup lease changed after issuance")
        return self._lease_id

    @property
    def outer_fd(self) -> int:
        self._assert_consumable()
        return self._outer_fd

    @property
    def worker_fd(self) -> int:
        self._assert_consumable()
        return self._worker_fd

    @property
    def closed(self) -> bool:
        self._check_process()
        return self._state is K7OuterAttemptCgroupLeaseStateV1.CLOSED

    @property
    def cleanup_state(self) -> K7OuterAttemptCgroupLeaseStateV1:
        self._check_process()
        return self._state

    def to_document(self) -> dict[str, Any]:
        self._assert_consumable()
        return {**self._payload(), "outer_attempt_cgroup_lease_id": self.lease_id}

    def close_unused(self) -> None:
        """Remove a never-consumed hierarchy; executed work requires a runtime."""

        self._assert_cleanup_authority()
        self._state = K7OuterAttemptCgroupLeaseStateV1.CLEANUP_PARTIAL
        # Creating a descendant cgroup may itself charge kernel memory to its
        # ancestor.  This unused close discards that observation; it does not
        # reinterpret a later nonzero peak as proof that a worker ran.
        try:
            protocol_violations = self._protocol_violations
            if not self._worker_removed:
                inner_v1._validate_empty_leaf(self._worker_fd)  # noqa: SLF001
                inner_v1._validate_empty_leaf(self._outer_fd)  # noqa: SLF001
                try:
                    if not _controls_match(
                        self._outer_fd, OUTER_CONTROL_READBACKS
                    ):
                        protocol_violations.append("outer_controls")
                except Exception:
                    protocol_violations.append("outer_controls_unreadable")
                try:
                    if not _controls_match(
                        self._worker_fd, WORKER_CONTROL_READBACKS
                    ):
                        protocol_violations.append("worker_controls")
                except Exception:
                    protocol_violations.append("worker_controls_unreadable")
                try:
                    enabled = set(
                        inner_v1._parse_controller_tokens(  # noqa: SLF001
                            inner_v1._read_control(  # noqa: SLF001
                                self._outer_fd, "cgroup.subtree_control"
                            ),
                            "cgroup.subtree_control",
                        )
                    )
                    if not set(REQUIRED_CONTROLLERS) <= enabled:
                        protocol_violations.append("subtree_controllers")
                except Exception:
                    protocol_violations.append("subtree_controllers_unreadable")
                stats = _cgroup_stat(self._outer_fd)
                if (
                    stats["nr_descendants"] != 1
                    or stats["nr_dying_descendants"] != 0
                ):
                    _fail("unused outer hierarchy has an unexpected descendant set")
                _verify_named_descriptor(
                    self._outer_fd, self._worker_name, self._worker_status
                )
                _verify_named_descriptor(
                    self._parent_fd, self._outer_name, self._outer_status
                )
                os.rmdir(self._worker_name, dir_fd=self._outer_fd)
                self._worker_removed = True
                descriptor = self._worker_fd
                self._worker_fd = -1
                os.close(descriptor)

            if not self._outer_removed:
                inner_v1._validate_empty_leaf(self._outer_fd)  # noqa: SLF001
                try:
                    if not _controls_match(
                        self._outer_fd, OUTER_CONTROL_READBACKS
                    ):
                        protocol_violations.append("outer_controls")
                except Exception:
                    protocol_violations.append("outer_controls_unreadable")
                _wait_descendant_counts(self._outer_fd, expected_descendants=0)
                _verify_named_descriptor(
                    self._parent_fd, self._outer_name, self._outer_status
                )
                os.rmdir(self._outer_name, dir_fd=self._parent_fd)
                self._outer_removed = True
                descriptor = self._outer_fd
                self._outer_fd = -1
                os.close(descriptor)

            descriptor = self._parent_fd
            self._parent_fd = -1
            os.close(descriptor)
            self._state = K7OuterAttemptCgroupLeaseStateV1.CLOSED
            if protocol_violations:
                raise V075K7OuterAttemptCgroupProtocolV1Error(
                    tuple(sorted(set(protocol_violations)))
                )
        except BaseException as error:
            if isinstance(
                error,
                (
                    V075K7OuterAttemptCgroupCleanupV1Error,
                    V075K7OuterAttemptCgroupProtocolV1Error,
                ),
            ):
                raise
            raise V075K7OuterAttemptCgroupCleanupV1Error(
                "unused outer hierarchy could not be removed"
            ) from error

    def __enter__(self) -> "K7OuterAttemptCgroupLeaseV1":
        self._assert_consumable()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close_unused()

    def __reduce__(self):
        raise TypeError("outer-attempt cgroup lease is unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("outer-attempt cgroup lease is unpickleable")


def _blocked(
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    admission_result: admission_v1.K7OSSupervisorAdmissionResultV1,
    blocker: K7OuterAttemptCgroupBlockerV1,
    stage: K7OuterAttemptCgroupStageV1,
    *,
    outer_created: bool,
    worker_created: bool,
) -> K7OuterAttemptCgroupBlockedResultV1:
    return K7OuterAttemptCgroupBlockedResultV1(
        _BLOCKED_ISSUER,
        request.request_id,
        request.route_identity.route_identity_id,
        admission_result.result_id,
        blocker,
        stage,
        outer_created,
        worker_created,
        True,
    )


def acquire_v075_k7_outer_attempt_cgroup_v1(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    admission_result: admission_v1.K7OSSupervisorAdmissionResultV1,
    delegated_parent_fd: int,
    nonce_token: K7OuterAttemptCgroupNonceTokenV1,
) -> K7OuterAttemptCgroupLeaseV1 | K7OuterAttemptCgroupBlockedResultV1:
    """Create one fresh empty ancestor and worker leaf, or fail closed."""

    if (
        type(request) is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
        or type(admission_result)
        is not admission_v1.K7OSSupervisorAdmissionResultV1
        or type(delegated_parent_fd) is not int
        or delegated_parent_fd < 0
    ):
        _fail("outer-attempt cgroup acquisition inputs are mistyped")
    request._assert_current()  # noqa: SLF001
    _NONCE_SERVICE.consume(
        nonce_token, request, admission_result, delegated_parent_fd
    )
    admission_v1.verify_v075_k7_os_supervisor_admission_v1(admission_result)
    if admission_result.profile is not request.profile.admission_profile:
        return _blocked(
            request,
            admission_result,
            K7OuterAttemptCgroupBlockerV1.ADMISSION_AUTHORITY_CROSSED,
            K7OuterAttemptCgroupStageV1.AUTHORITY,
            outer_created=False,
            worker_created=False,
        )
    if not sys.platform.startswith("linux"):
        return _blocked(
            request,
            admission_result,
            K7OuterAttemptCgroupBlockerV1.NOT_LINUX,
            K7OuterAttemptCgroupStageV1.FILESYSTEM,
            outer_created=False,
            worker_created=False,
        )
    fact = admission_result.probe.delegated_parent_fact
    try:
        caller_status = os.fstat(delegated_parent_fd)
        caller_identity = _descriptor_tuple(caller_status)
        caller_target = _descriptor_target_sha256(delegated_parent_fd)
    except OSError:
        caller_identity = (-1, -1, -1, -1, -1)
        caller_target = ""
    expected_identity = (
        fact.device,
        fact.inode,
        fact.mode,
        fact.owner_uid,
        fact.owner_gid,
    )
    if (
        not admission_result.probe.delegated_parent_fd_supplied
        or not fact.exists
        or caller_identity != expected_identity
        or caller_identity != nonce_token._descriptor_identity  # noqa: SLF001
        or caller_target != fact.path_sha256
        or caller_target != nonce_token._descriptor_target_sha256  # noqa: SLF001
    ):
        return _blocked(
            request,
            admission_result,
            K7OuterAttemptCgroupBlockerV1.DESCRIPTOR_IDENTITY_MISMATCH,
            K7OuterAttemptCgroupStageV1.DESCRIPTOR,
            outer_created=False,
            worker_created=False,
        )

    parent_fd = outer_fd = worker_fd = -1
    outer_name: str | None = None
    worker_name: str | None = None
    outer_status: os.stat_result | None = None
    worker_status: os.stat_result | None = None
    outer_created = worker_created = False
    blocker: tuple[K7OuterAttemptCgroupBlockerV1, K7OuterAttemptCgroupStageV1] | None = None
    try:
        try:
            parent_fd = os.dup(delegated_parent_fd)
            os.set_inheritable(parent_fd, False)
            if (
                _descriptor_tuple(os.fstat(parent_fd)) != caller_identity
                or inner_v1._fstatfs_magic(parent_fd)  # noqa: SLF001
                != inner_v1.CGROUP2_SUPER_MAGIC
            ):
                blocker = (
                    K7OuterAttemptCgroupBlockerV1.NOT_CGROUP2_FILESYSTEM,
                    K7OuterAttemptCgroupStageV1.FILESYSTEM,
                )
            else:
                controllers = set(
                    inner_v1._parse_controller_tokens(  # noqa: SLF001
                        inner_v1._read_control(  # noqa: SLF001
                            parent_fd, "cgroup.controllers"
                        ),
                        "cgroup.controllers",
                    )
                )
                delegated = set(
                    inner_v1._parse_controller_tokens(  # noqa: SLF001
                        inner_v1._read_control(  # noqa: SLF001
                            parent_fd, "cgroup.subtree_control"
                        ),
                        "cgroup.subtree_control",
                    )
                )
                if not set(REQUIRED_CONTROLLERS) <= controllers & delegated:
                    blocker = (
                        K7OuterAttemptCgroupBlockerV1.REQUIRED_CONTROLLER_NOT_DELEGATED,
                        K7OuterAttemptCgroupStageV1.DELEGATION,
                    )
        except (OSError, inner_v1.V075K7CgroupLeaseV1Error):
            blocker = (
                K7OuterAttemptCgroupBlockerV1.NOT_CGROUP2_FILESYSTEM,
                K7OuterAttemptCgroupStageV1.FILESYSTEM,
            )
        if blocker is None:
            outer_name = f"acfqp-outer-{request.request_id[:16]}-{secrets.token_hex(8)}"
            try:
                os.mkdir(outer_name, mode=0o700, dir_fd=parent_fd)
                outer_created = True
                outer_status = os.stat(
                    outer_name, dir_fd=parent_fd, follow_symlinks=False
                )
                outer_fd = _open_directory(parent_fd, outer_name)
                if _descriptor_tuple(os.fstat(outer_fd)) != _descriptor_tuple(
                    outer_status
                ):
                    _fail("new outer cgroup descriptor identity crossed")
            except (OSError, V075K7OuterAttemptCgroupV1Error):
                blocker = (
                    K7OuterAttemptCgroupBlockerV1.OUTER_CREATE_FAILED,
                    K7OuterAttemptCgroupStageV1.OUTER_CREATE,
                )
        if blocker is None:
            try:
                if inner_v1._fstatfs_magic(outer_fd) != inner_v1.CGROUP2_SUPER_MAGIC:  # noqa: SLF001
                    raise V075K7OuterAttemptCgroupV1Error("outer is not cgroup2")
                for name in OUTER_REQUIRED_FILES:
                    if name == "cgroup.kill":
                        descriptor = inner_v1._open_control(  # noqa: SLF001
                            outer_fd, name, os.O_WRONLY
                        )
                        os.close(descriptor)
                    else:
                        inner_v1._read_control(outer_fd, name)  # noqa: SLF001
                _validate_fresh_domain(outer_fd)
            except (OSError, inner_v1.V075K7CgroupLeaseV1Error, V075K7OuterAttemptCgroupV1Error):
                blocker = (
                    K7OuterAttemptCgroupBlockerV1.OUTER_VALIDATION_FAILED,
                    K7OuterAttemptCgroupStageV1.OUTER_CREATE,
                )
        if blocker is None:
            try:
                for name, value in OUTER_CONTROL_READBACKS:
                    inner_v1._write_control(outer_fd, name, value)  # noqa: SLF001
                if not _controls_match(outer_fd, OUTER_CONTROL_READBACKS):
                    raise V075K7OuterAttemptCgroupV1Error("outer readback mismatch")
            except (OSError, inner_v1.V075K7CgroupLeaseV1Error, V075K7OuterAttemptCgroupV1Error):
                blocker = (
                    K7OuterAttemptCgroupBlockerV1.OUTER_CONFIGURATION_FAILED,
                    K7OuterAttemptCgroupStageV1.OUTER_CONFIGURE,
                )
        if blocker is None:
            try:
                inner_v1._write_control(  # noqa: SLF001
                    outer_fd, "cgroup.subtree_control", "+memory +pids"
                )
                enabled = set(
                    inner_v1._parse_controller_tokens(  # noqa: SLF001
                        inner_v1._read_control(  # noqa: SLF001
                            outer_fd, "cgroup.subtree_control"
                        ),
                        "cgroup.subtree_control",
                    )
                )
                if not set(REQUIRED_CONTROLLERS) <= enabled:
                    raise V075K7OuterAttemptCgroupV1Error("subtree readback mismatch")
            except (OSError, inner_v1.V075K7CgroupLeaseV1Error, V075K7OuterAttemptCgroupV1Error):
                blocker = (
                    K7OuterAttemptCgroupBlockerV1.SUBTREE_ENABLE_FAILED,
                    K7OuterAttemptCgroupStageV1.OUTER_CONFIGURE,
                )
        if blocker is None:
            worker_name = "worker"
            try:
                os.mkdir(worker_name, mode=0o700, dir_fd=outer_fd)
                worker_created = True
                worker_status = os.stat(
                    worker_name, dir_fd=outer_fd, follow_symlinks=False
                )
                worker_fd = _open_directory(outer_fd, worker_name)
                if _descriptor_tuple(os.fstat(worker_fd)) != _descriptor_tuple(
                    worker_status
                ):
                    _fail("new worker cgroup descriptor identity crossed")
            except (OSError, V075K7OuterAttemptCgroupV1Error):
                blocker = (
                    K7OuterAttemptCgroupBlockerV1.WORKER_CREATE_FAILED,
                    K7OuterAttemptCgroupStageV1.WORKER_CREATE,
                )
        if blocker is None:
            try:
                if inner_v1._fstatfs_magic(worker_fd) != inner_v1.CGROUP2_SUPER_MAGIC:  # noqa: SLF001
                    raise V075K7OuterAttemptCgroupV1Error("worker is not cgroup2")
                for name in WORKER_REQUIRED_FILES:
                    inner_v1._read_control(worker_fd, name)  # noqa: SLF001
                _validate_fresh_domain(worker_fd)
            except (OSError, inner_v1.V075K7CgroupLeaseV1Error, V075K7OuterAttemptCgroupV1Error):
                blocker = (
                    K7OuterAttemptCgroupBlockerV1.WORKER_VALIDATION_FAILED,
                    K7OuterAttemptCgroupStageV1.WORKER_CREATE,
                )
        if blocker is None:
            try:
                for name, value in WORKER_CONTROL_READBACKS:
                    inner_v1._write_control(worker_fd, name, value)  # noqa: SLF001
                if not _controls_match(worker_fd, WORKER_CONTROL_READBACKS):
                    raise V075K7OuterAttemptCgroupV1Error("worker readback mismatch")
            except (OSError, inner_v1.V075K7CgroupLeaseV1Error, V075K7OuterAttemptCgroupV1Error):
                blocker = (
                    K7OuterAttemptCgroupBlockerV1.WORKER_CONFIGURATION_FAILED,
                    K7OuterAttemptCgroupStageV1.WORKER_CONFIGURE,
                )
        if blocker is None:
            try:
                inner_v1._validate_empty_leaf(outer_fd)  # noqa: SLF001
                inner_v1._validate_empty_leaf(worker_fd)  # noqa: SLF001
                if not _controls_match(outer_fd, OUTER_CONTROL_READBACKS):
                    raise V075K7OuterAttemptCgroupV1Error(
                        "outer final control readback mismatch"
                    )
                if not _controls_match(worker_fd, WORKER_CONTROL_READBACKS):
                    raise V075K7OuterAttemptCgroupV1Error(
                        "worker final control readback mismatch"
                    )
                enabled = set(
                    inner_v1._parse_controller_tokens(  # noqa: SLF001
                        inner_v1._read_control(  # noqa: SLF001
                            outer_fd, "cgroup.subtree_control"
                        ),
                        "cgroup.subtree_control",
                    )
                )
                stats = _cgroup_stat(outer_fd)
                worker_peak = inner_v1._parse_nonnegative(  # noqa: SLF001
                    inner_v1._read_control(worker_fd, "memory.peak"),  # noqa: SLF001
                    "memory.peak",
                )
                if (
                    not set(REQUIRED_CONTROLLERS) <= enabled
                    or stats["nr_descendants"] != 1
                    or stats["nr_dying_descendants"] != 0
                    or worker_peak != 0
                ):
                    raise V075K7OuterAttemptCgroupV1Error(
                        "complete hierarchy final snapshot mismatch"
                    )
                _verify_named_descriptor(outer_fd, worker_name, os.fstat(worker_fd))
                _verify_named_descriptor(parent_fd, outer_name, os.fstat(outer_fd))
            except (
                OSError,
                inner_v1.V075K7CgroupLeaseV1Error,
                V075K7OuterAttemptCgroupV1Error,
            ):
                blocker = (
                    K7OuterAttemptCgroupBlockerV1.FINAL_SNAPSHOT_VALIDATION_FAILED,
                    K7OuterAttemptCgroupStageV1.FINAL_SNAPSHOT,
                )

        if blocker is not None:
            observed_outer = outer_created
            observed_worker = worker_created
            return _blocked(
                request,
                admission_result,
                blocker[0],
                blocker[1],
                outer_created=observed_outer,
                worker_created=observed_worker,
            )
        lease = K7OuterAttemptCgroupLeaseV1(
            _LEASE_ISSUER,
            parent_fd=parent_fd,
            outer_fd=outer_fd,
            worker_fd=worker_fd,
            outer_name=outer_name,
            worker_name=worker_name,
            request=request,
            admission_result=admission_result,
        )
        parent_fd = outer_fd = worker_fd = -1
        outer_created = worker_created = False
        return lease
    finally:
        cleanup_error: BaseException | None = None
        if outer_created or worker_created:
            cleanup_guard = K7OuterAttemptCgroupCleanupGuardV1(
                _CLEANUP_GUARD_ISSUER,
                parent_fd=parent_fd,
                outer_fd=outer_fd,
                worker_fd=worker_fd,
                outer_name=outer_name if outer_created else None,
                worker_name=worker_name if worker_created else None,
                parent_status=caller_status,
                outer_status=outer_status,
                worker_status=worker_status,
            )
            parent_fd = outer_fd = worker_fd = -1
            outer_created = worker_created = False
            try:
                cleanup_guard.retry_cleanup()
            except BaseException as error:
                cleanup_error = error
        for descriptor in (worker_fd, outer_fd, parent_fd):
            if descriptor >= 0:
                os.close(descriptor)
        if cleanup_error is not None:
            raise cleanup_error


__all__ = (
    "FIXED_OUTER_MEMORY_MAX_BYTES",
    "K7OuterAttemptCgroupBlockedResultV1",
    "K7OuterAttemptCgroupBlockerV1",
    "K7OuterAttemptCgroupCleanupGuardV1",
    "K7OuterAttemptCgroupCleanupStateV1",
    "K7OuterAttemptCgroupLeaseV1",
    "K7OuterAttemptCgroupLeaseStateV1",
    "K7OuterAttemptCgroupNonceServiceV1",
    "K7OuterAttemptCgroupNonceTokenV1",
    "K7OuterAttemptCgroupProfileV1",
    "K7OuterAttemptCgroupStageV1",
    "LOCAL_DOMAIN_TAGS",
    "OUTER_CONTROL_READBACKS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "V075K7OuterAttemptCgroupCleanupV1Error",
    "V075K7OuterAttemptCgroupProtocolV1Error",
    "V075K7OuterAttemptCgroupV1Error",
    "WORKER_CONTROL_READBACKS",
    "acquire_v075_k7_outer_attempt_cgroup_v1",
    "official_v075_k7_outer_attempt_cgroup_nonce_service_v1",
    "official_v075_k7_outer_attempt_cgroup_profile_v1",
)
