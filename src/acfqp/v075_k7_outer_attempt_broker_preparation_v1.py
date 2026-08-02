"""Prepare, but never launch, one live K7 outer-attempt broker session."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import os
import secrets
import socket
import stat
import threading
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_cgroup_lease_v1 as inner_v1
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_outer_attempt_cgroup_v1 as outer_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_OUTER_ATTEMPT_BROKER_EXECUTION_SPEC_V1_DOMAIN,
    V075_K7_OUTER_ATTEMPT_BROKER_PREPARATION_PROFILE_V1_DOMAIN,
    V075_K7_OUTER_ATTEMPT_PREPARED_BROKER_SESSION_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.5"
PROFILE_KEY = "v075_k7_outer_attempt_broker_preparation_v1"
BUSINESS_NAME = "business"
LEAF_CONTROL_READBACKS = outer_v1.WORKER_CONTROL_READBACKS
LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_OUTER_ATTEMPT_BROKER_PREPARATION_PROFILE_V1_DOMAIN,
        V075_K7_OUTER_ATTEMPT_BROKER_EXECUTION_SPEC_V1_DOMAIN,
        V075_K7_OUTER_ATTEMPT_PREPARED_BROKER_SESSION_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("broker-preparation domains are unregistered")

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_OUTER_ATTEMPT_BROKER_PREPARATION_PROFILE_V1_DOMAIN",
    "V075_K7_OUTER_ATTEMPT_BROKER_EXECUTION_SPEC_V1_DOMAIN",
    "V075_K7_OUTER_ATTEMPT_PREPARED_BROKER_SESSION_V1_DOMAIN",
)

_PROFILE_ISSUER = object()
_SPEC_ISSUER = object()
_GUARDIAN_ISSUER = object()
_SESSION_ISSUER = object()


class V075K7OuterAttemptBrokerPreparationV1Error(RuntimeError):
    """Live prelaunch preparation or verification failed closed."""

    def __init__(self, message: str, *, guardian: Any = None) -> None:
        super().__init__(message)
        self.guardian = guardian


class V075K7OuterAttemptBrokerPreparationProtocolV1Error(
    V075K7OuterAttemptBrokerPreparationV1Error
):
    """The empty owned tree was removed after a frozen-control mismatch."""

    def __init__(self, violations: tuple[str, ...]) -> None:
        if (
            type(violations) is not tuple
            or not violations
            or tuple(sorted(set(violations))) != violations
        ):
            _fail("broker-preparation protocol violations are noncanonical")
        super().__init__(
            "prepared empty hierarchy was removed after protocol mismatch: "
            + ",".join(violations)
        )
        self.cleanup_complete = True
        self.violations = violations


class K7PreparedBrokerCleanupStateV1(str, Enum):
    IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD = (
        "IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD"
    )
    PREPARED = "PREPARED"
    CLEANUP_PARTIAL = "CLEANUP_PARTIAL"
    CLOSED = "CLOSED"


def _fail(message: str) -> NoReturn:
    raise V075K7OuterAttemptBrokerPreparationV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("broker preparation used an undeclared domain")
    return content_id(domain, dict(payload))


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7OuterAttemptBrokerPreparationV1Error(
            f"{label} must be one exact content ID"
        ) from error


_DESCRIPTOR_FIELDS = frozenset(
    {"device", "inode", "mode", "owner_uid", "owner_gid"}
)


def _frozen_descriptor(value: Any, label: str) -> Mapping[str, int]:
    if (
        type(value) is not dict
        or frozenset(value) != _DESCRIPTOR_FIELDS
        or any(type(item) is not int or item < 0 for item in value.values())
    ):
        _fail(f"{label} descriptor identity is invalid")
    return MappingProxyType(dict(value))


def _formal_locks() -> dict[str, bool]:
    return {
        "process_launch_implemented": False,
        "worker_launched_from_birth_in_scope": False,
        "business_launched_from_birth_in_scope": False,
        "ipc_frame_sent": False,
        "shared_resource_value_issued": False,
        "complete_attempt_memory_window_verified": False,
        "counter_record_authorized": False,
        "work_vector_authorized": False,
        "comparison_vector_authorized": False,
        "attempt_terminal_authorized": False,
        "official_execution_allowed": False,
    }


def _descriptor(status: os.stat_result) -> dict[str, int]:
    return outer_v1._descriptor_document(status)  # noqa: SLF001


def _same_status(descriptor: int, expected: os.stat_result) -> bool:
    return outer_v1._descriptor_tuple(os.fstat(descriptor)) == (  # noqa: SLF001
        outer_v1._descriptor_tuple(expected)  # noqa: SLF001
    )


def _read_open_control(descriptor: int, label: str) -> int:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    total = 0
    while True:
        part = os.read(descriptor, min(8192, inner_v1.MAX_CONTROL_BYTES + 1 - total))
        if not part:
            break
        chunks.append(part)
        total += len(part)
        if total > inner_v1.MAX_CONTROL_BYTES:
            _fail(f"{label} exceeds its byte cap")
    return inner_v1._parse_nonnegative(b"".join(chunks), label)  # noqa: SLF001


@dataclass(frozen=True, slots=True)
class K7OuterAttemptBrokerPreparationProfileV1:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("broker-preparation profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(
                V075_K7_OUTER_ATTEMPT_BROKER_PREPARATION_PROFILE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_outer_attempt_broker_preparation_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "readiness_level": "PREPARED_LIVE_BROKER_SESSION",
            "business_name": BUSINESS_NAME,
            "business_control_readbacks": [
                {"file": name, "value": value}
                for name, value in LEAF_CONTROL_READBACKS
            ],
            "exact_measurement_window_reset_required": 0,
            "peak_reset_before_descendant_creation": True,
            "hierarchy_and_session_preparation_inside_memory_window": True,
            "prelaunch_peak_may_be_nonzero": True,
            "nonzero_baseline_subtraction_allowed": False,
            "same_memory_peak_open_file_description_required": True,
            "request_single_session_process_local": True,
            "business_preidentity_cleanup_requires_parent_guard": True,
            "crash_persistent_cleanup_verified": False,
            "live_peer_role_ownership_verified": False,
            "launch_authority": False,
            "no_launch": True,
            **_formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _hash(
            V075_K7_OUTER_ATTEMPT_BROKER_PREPARATION_PROFILE_V1_DOMAIN,
            self._payload(),
        ) != self._profile_id:
            _fail("broker-preparation profile changed after issuance")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "broker_preparation_profile_id": self.profile_id}


_OFFICIAL_PROFILE = K7OuterAttemptBrokerPreparationProfileV1(_PROFILE_ISSUER)


def official_v075_k7_outer_attempt_broker_preparation_profile_v1(
) -> K7OuterAttemptBrokerPreparationProfileV1:
    return _OFFICIAL_PROFILE


@dataclass(frozen=True, slots=True)
class K7OuterAttemptBrokerExecutionSpecV1:
    _issuer: InitVar[object]
    request_id: str
    route_identity_id: str
    outer_lease_id: str
    parent_identity: Mapping[str, int]
    outer_identity: Mapping[str, int]
    worker_identity: Mapping[str, int]
    business_identity: Mapping[str, int]
    cgroup_kill_identity: Mapping[str, int]
    memory_peak_identity: Mapping[str, int]
    worker_socket_identity: Mapping[str, int]
    business_socket_identity: Mapping[str, int]
    outer_name_sha256: str
    session_nonce: str
    prelaunch_memory_peak: int
    prelaunch_memory_current: int
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SPEC_ISSUER:
            _fail("broker execution spec is issuer-owned")
        object.__setattr__(self, "request_id", _cid(self.request_id, "request"))
        object.__setattr__(
            self,
            "route_identity_id",
            _cid(self.route_identity_id, "route identity"),
        )
        object.__setattr__(
            self,
            "outer_lease_id",
            _cid(self.outer_lease_id, "outer lease"),
        )
        object.__setattr__(
            self,
            "outer_name_sha256",
            _cid(self.outer_name_sha256, "outer name digest"),
        )
        for name in (
            "parent_identity",
            "outer_identity",
            "worker_identity",
            "business_identity",
            "cgroup_kill_identity",
            "memory_peak_identity",
            "worker_socket_identity",
            "business_socket_identity",
        ):
            object.__setattr__(
                self,
                name,
                _frozen_descriptor(getattr(self, name), name),
            )
        if (
            type(self.session_nonce) is not str
            or len(self.session_nonce) != 64
            or any(character not in "0123456789abcdef" for character in self.session_nonce)
        ):
            _fail("broker execution spec nonce is invalid")
        if (
            type(self.prelaunch_memory_peak) is not int
            or type(self.prelaunch_memory_current) is not int
            or self.prelaunch_memory_peak < self.prelaunch_memory_current
            or self.prelaunch_memory_current < 0
        ):
            _fail("broker execution spec prelaunch memory observation is invalid")
        object.__setattr__(
            self,
            "_spec_id",
            _hash(V075_K7_OUTER_ATTEMPT_BROKER_EXECUTION_SPEC_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_outer_attempt_broker_execution_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "broker_preparation_profile_id": _OFFICIAL_PROFILE.profile_id,
            "request_id": self.request_id,
            "route_identity_id": self.route_identity_id,
            "outer_attempt_cgroup_lease_id": self.outer_lease_id,
            "parent_descriptor_identity": dict(self.parent_identity),
            "outer_descriptor_identity": dict(self.outer_identity),
            "worker_descriptor_identity": dict(self.worker_identity),
            "business_descriptor_identity": dict(self.business_identity),
            "cgroup_kill_descriptor_identity": dict(self.cgroup_kill_identity),
            "memory_peak_control_file_identity": dict(self.memory_peak_identity),
            "same_memory_peak_open_file_description_authority": (
                "PROCESS_LOCAL_TRANSFERRED_CAPABILITY"
            ),
            "worker_socket_identity": dict(self.worker_socket_identity),
            "business_socket_identity": dict(self.business_socket_identity),
            "session_nonce_sha256": hashlib.sha256(
                self.session_nonce.encode("ascii")
            ).hexdigest(),
            "worker_name": "worker",
            "business_name": BUSINESS_NAME,
            "outer_attempt_broker_ipc_profile_id": (
                ipc_v1.official_v075_k7_outer_attempt_broker_ipc_profile_v1().profile_id
            ),
            "outer_name_sha256": self.outer_name_sha256,
            "outer_memory_peak_reset_value": 0,
            "measurement_window_reset_memory_peak_value": 0,
            "measurement_window_reset_memory_current_value": 0,
            "prelaunch_memory_peak_value": self.prelaunch_memory_peak,
            "prelaunch_memory_current_value": self.prelaunch_memory_current,
            "baseline_subtraction_allowed": False,
            **_formal_locks(),
        }

    @property
    def spec_id(self) -> str:
        if _hash(
            V075_K7_OUTER_ATTEMPT_BROKER_EXECUTION_SPEC_V1_DOMAIN,
            self._payload(),
        ) != self._spec_id:
            _fail("broker execution spec changed after issuance")
        return self._spec_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "broker_execution_spec_id": self.spec_id}


class K7OuterAttemptPrelaunchGuardianV1:
    """Sole process-local owner of every prelaunch descriptor."""

    def __init__(
        self,
        issuer: object,
        *,
        authority: dict[str, Any],
    ) -> None:
        if issuer is not _GUARDIAN_ISSUER:
            _fail("prelaunch guardian is issuer-owned")
        self._owner_pid = os.getpid()
        self._parent_fd = authority["parent_fd"]
        self._outer_fd = authority["outer_fd"]
        self._worker_fd = authority["worker_fd"]
        self._business_fd = -1
        self._kill_fd = -1
        self._peak_fd = authority["broker_peak_fd"]
        self._peak_status = authority["broker_peak_status"]
        self._peak_reset_peak = authority["broker_peak_reset_peak"]
        self._peak_reset_current = authority["broker_peak_reset_current"]
        self._transfer_token = authority["transfer_token"]
        if type(self._transfer_token) is not object:
            _fail("prelaunch guardian transfer token is invalid")
        self._worker_socket_fd = -1
        self._business_socket_fd = -1
        self._outer_name = authority["outer_name"]
        self._worker_name = authority["worker_name"]
        self._business_name = BUSINESS_NAME
        self._request_id = authority["request_id"]
        self._route_identity_id = authority["route_identity_id"]
        self._outer_lease_id = authority["lease_id"]
        self._parent_status = authority["parent_status"]
        self._outer_status = authority["outer_status"]
        self._worker_status = authority["worker_status"]
        self._business_status: os.stat_result | None = None
        self._business_created = False
        self._business_removed = False
        self._worker_removed = False
        self._outer_removed = False
        self._protocol_violations: list[str] = []
        self._state = K7PreparedBrokerCleanupStateV1.PREPARED
        self._lifecycle_lock = threading.Lock()

    def _check(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("prelaunch guardian crossed a process boundary")
        if self._state is K7PreparedBrokerCleanupStateV1.CLOSED:
            _fail("prelaunch guardian is closed")

    @property
    def cleanup_state(self) -> K7PreparedBrokerCleanupStateV1:
        if os.getpid() != self._owner_pid:
            _fail("prelaunch guardian crossed a process boundary")
        return self._state

    @property
    def closed(self) -> bool:
        return self.cleanup_state is K7PreparedBrokerCleanupStateV1.CLOSED

    def close_prelaunch(self) -> None:
        """Verify the still-empty topology and retryably delete all owned nodes."""

        with self._lifecycle_lock:
            self._close_prelaunch_locked()

    def _close_prelaunch_locked(self) -> None:
        """Locked implementation of :meth:`close_prelaunch`."""

        self._check()
        self._state = K7PreparedBrokerCleanupStateV1.CLEANUP_PARTIAL
        # Keep violations across partial-removal retries.  A mismatch observed
        # before a later cleanup syscall fails must still close as a protocol
        # failure once deletion eventually completes.
        protocol_violations = self._protocol_violations
        try:
            for attribute in (
                "_worker_socket_fd",
                "_business_socket_fd",
                "_peak_fd",
            ):
                descriptor = getattr(self, attribute)
                if descriptor >= 0:
                    os.close(descriptor)
                    setattr(self, attribute, -1)
            if self._business_created and not self._business_removed:
                if self._business_status is None:
                    self._state = (
                        K7PreparedBrokerCleanupStateV1
                        .IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD
                    )
                    _fail(
                        "business identity was not captured; cleanup requires "
                        "the preexisting parent guardian"
                    )
                if not _same_status(self._business_fd, self._business_status):
                    _fail("business descriptor identity changed")
                inner_v1._validate_empty_leaf(self._business_fd)  # noqa: SLF001
                try:
                    if not outer_v1._controls_match(  # noqa: SLF001
                        self._business_fd, LEAF_CONTROL_READBACKS
                    ):
                        protocol_violations.append("business_controls")
                except Exception:
                    protocol_violations.append("business_controls_unreadable")
                outer_v1._verify_named_descriptor(  # noqa: SLF001
                    self._outer_fd, self._business_name, self._business_status
                )
                os.rmdir(self._business_name, dir_fd=self._outer_fd)
                self._business_removed = True
                os.close(self._business_fd)
                self._business_fd = -1
            if not self._worker_removed:
                if not _same_status(self._worker_fd, self._worker_status):
                    _fail("worker descriptor identity changed")
                inner_v1._validate_empty_leaf(self._worker_fd)  # noqa: SLF001
                try:
                    if not outer_v1._controls_match(  # noqa: SLF001
                        self._worker_fd, LEAF_CONTROL_READBACKS
                    ):
                        protocol_violations.append("worker_controls")
                except Exception:
                    protocol_violations.append("worker_controls_unreadable")
                outer_v1._verify_named_descriptor(  # noqa: SLF001
                    self._outer_fd, self._worker_name, self._worker_status
                )
                os.rmdir(self._worker_name, dir_fd=self._outer_fd)
                self._worker_removed = True
                os.close(self._worker_fd)
                self._worker_fd = -1
            if not self._outer_removed:
                inner_v1._validate_empty_leaf(self._outer_fd)  # noqa: SLF001
                try:
                    if not outer_v1._controls_match(  # noqa: SLF001
                        self._outer_fd, outer_v1.OUTER_CONTROL_READBACKS
                    ):
                        protocol_violations.append("outer_controls")
                except Exception:
                    protocol_violations.append("outer_controls_unreadable")
                outer_v1._wait_descendant_counts(  # noqa: SLF001
                    self._outer_fd, expected_descendants=0
                )
                outer_v1._verify_named_descriptor(  # noqa: SLF001
                    self._parent_fd, self._outer_name, self._outer_status
                )
                os.rmdir(self._outer_name, dir_fd=self._parent_fd)
                self._outer_removed = True
                os.close(self._outer_fd)
                self._outer_fd = -1
            # Keep cgroup.kill retry authority until every descendant has
            # passed emptiness checks and the owned hierarchy is gone.  A
            # partial cleanup caused by an unexpected migrated process must
            # not irreversibly discard the only tree-wide containment OFD.
            if self._kill_fd >= 0:
                os.close(self._kill_fd)
                self._kill_fd = -1
            os.close(self._parent_fd)
            self._parent_fd = -1
            self._state = K7PreparedBrokerCleanupStateV1.CLOSED
            if protocol_violations:
                raise V075K7OuterAttemptBrokerPreparationProtocolV1Error(
                    tuple(sorted(set(protocol_violations)))
                )
        except BaseException as error:
            if isinstance(
                error,
                V075K7OuterAttemptBrokerPreparationProtocolV1Error,
            ):
                raise
            if isinstance(error, V075K7OuterAttemptBrokerPreparationV1Error):
                error.guardian = self
                raise
            raise V075K7OuterAttemptBrokerPreparationV1Error(
                "prelaunch cleanup is partial and retryable", guardian=self
            ) from error

    def __reduce__(self):
        raise TypeError("prelaunch guardian is unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("prelaunch guardian is unpickleable")


@dataclass(frozen=True, slots=True)
class K7OuterAttemptPreparedBrokerSessionV1:
    _issuer: InitVar[object]
    execution_spec: K7OuterAttemptBrokerExecutionSpecV1
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1
    measurement_window_reset_memory_peak: int
    measurement_window_reset_memory_current: int
    prelaunch_memory_peak: int
    prelaunch_memory_current: int
    guardian: K7OuterAttemptPrelaunchGuardianV1 = field(repr=False, compare=False)
    _session_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SESSION_ISSUER:
            _fail("prepared broker session is issuer-owned")
        if (
            type(self.execution_spec) is not K7OuterAttemptBrokerExecutionSpecV1
            or type(self.binding) is not ipc_v1.K7OuterAttemptBrokerIPCBindingV1
            or self.binding.broker_execution_spec_id != self.execution_spec.spec_id
            or self.binding.request_id != self.execution_spec.request_id
            or self.binding.route_identity_id
            != self.execution_spec.route_identity_id
            or self.binding.session_nonce != self.execution_spec.session_nonce
        ):
            _fail("prepared broker binding crossed its execution spec")
        if (
            type(self.measurement_window_reset_memory_peak) is not int
            or type(self.measurement_window_reset_memory_current) is not int
            or self.measurement_window_reset_memory_peak
            != self.measurement_window_reset_memory_current
        ):
            _fail("prepared broker measurement-window reset values differ")
        if self.measurement_window_reset_memory_peak != 0:
            _fail("exact prepared broker measurement-window reset is nonzero")
        if (
            type(self.prelaunch_memory_peak) is not int
            or type(self.prelaunch_memory_current) is not int
            or self.prelaunch_memory_peak < self.prelaunch_memory_current
            or self.prelaunch_memory_current < 0
            or self.prelaunch_memory_peak
            != self.execution_spec.prelaunch_memory_peak
            or self.prelaunch_memory_current
            != self.execution_spec.prelaunch_memory_current
        ):
            _fail("prepared broker prelaunch memory observation is invalid")
        object.__setattr__(
            self,
            "_session_id",
            _hash(V075_K7_OUTER_ATTEMPT_PREPARED_BROKER_SESSION_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_outer_attempt_prepared_broker_session.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "broker_preparation_profile_id": _OFFICIAL_PROFILE.profile_id,
            "broker_execution_spec_id": self.execution_spec.spec_id,
            "ipc_binding": self.binding.to_document(),
            "measurement_window_reset_memory_peak": (
                self.measurement_window_reset_memory_peak
            ),
            "measurement_window_reset_memory_current": (
                self.measurement_window_reset_memory_current
            ),
            "prelaunch_memory_peak": self.prelaunch_memory_peak,
            "prelaunch_memory_current": self.prelaunch_memory_current,
            "baseline_subtraction_allowed": False,
            "processes_launched": 0,
            "ipc_frames_sent": 0,
            "shared_resource_value": None,
            **_formal_locks(),
        }

    @property
    def session_id(self) -> str:
        if _hash(
            V075_K7_OUTER_ATTEMPT_PREPARED_BROKER_SESSION_V1_DOMAIN,
            self._payload(),
        ) != self._session_id:
            _fail("prepared broker session changed after issuance")
        return self._session_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prepared_broker_session_id": self.session_id}

    def close_prelaunch(self) -> None:
        self.guardian.close_prelaunch()


class K7OuterAttemptBrokerPreparationServiceV1:
    def __init__(self) -> None:
        self._owner_pid = os.getpid()
        self._consumed_requests: set[str] = set()
        self._lock = threading.Lock()

    def prepare(
        self, lease: outer_v1.K7OuterAttemptCgroupLeaseV1
    ) -> K7OuterAttemptPreparedBrokerSessionV1:
        if os.getpid() != self._owner_pid:
            _fail("broker-preparation service crossed a process boundary")
        if type(lease) is not outer_v1.K7OuterAttemptCgroupLeaseV1:
            _fail("broker preparation requires one exact outer lease")
        request_id = lease._request.request_id  # noqa: SLF001
        guardian_holder: list[Any] = []
        guardian: K7OuterAttemptPrelaunchGuardianV1 | None = None
        guardian_type = K7OuterAttemptPrelaunchGuardianV1

        def build_guardian(authority: dict[str, Any]) -> Any:
            candidate = guardian_type(_GUARDIAN_ISSUER, authority=authority)
            if type(candidate) is not guardian_type:
                _fail("broker-preparation factory returned the wrong guardian")
            return candidate

        try:
            with self._lock:
                if request_id in self._consumed_requests:
                    _fail("request already has a broker-preparation session")
                self._consumed_requests.add(request_id)
                guardian = lease._transfer_to_broker_preparation(  # noqa: SLF001
                    outer_v1._BROKER_PREPARATION_TRANSFER_ISSUER,  # noqa: SLF001
                    guardian_factory=build_guardian,
                    guardian_holder=guardian_holder,
                )
            if type(guardian) is not guardian_type:
                _fail("broker-preparation transfer returned the wrong guardian")
            if guardian._worker_name != "worker":  # noqa: SLF001
                _fail("worker name differs from its fixed identity")
            if not _same_status(guardian._parent_fd, guardian._parent_status):  # noqa: SLF001
                _fail("parent descriptor identity changed during transfer")
            if not _same_status(guardian._outer_fd, guardian._outer_status):  # noqa: SLF001
                _fail("outer descriptor identity changed during transfer")
            if not _same_status(guardian._worker_fd, guardian._worker_status):  # noqa: SLF001
                _fail("worker descriptor identity changed during transfer")
            outer_v1._verify_named_descriptor(  # noqa: SLF001
                guardian._parent_fd, guardian._outer_name, guardian._outer_status  # noqa: SLF001
            )
            outer_v1._verify_named_descriptor(  # noqa: SLF001
                guardian._outer_fd, guardian._worker_name, guardian._worker_status  # noqa: SLF001
            )
            if not outer_v1._controls_match(  # noqa: SLF001
                guardian._outer_fd, outer_v1.OUTER_CONTROL_READBACKS  # noqa: SLF001
            ):
                _fail("outer controls differ from the exact attempt profile")
            inner_v1._validate_empty_leaf(guardian._worker_fd)  # noqa: SLF001
            if not outer_v1._controls_match(  # noqa: SLF001
                guardian._worker_fd, LEAF_CONTROL_READBACKS  # noqa: SLF001
            ):
                _fail("worker controls differ from the exact leaf profile")
            if not outer_v1._controls_match(  # noqa: SLF001
                guardian._outer_fd, outer_v1.OUTER_CONTROL_READBACKS  # noqa: SLF001
            ):
                _fail("outer controls differ from the exact hierarchy profile")

            os.mkdir(BUSINESS_NAME, mode=0o700, dir_fd=guardian._outer_fd)  # noqa: SLF001
            guardian._business_created = True  # noqa: SLF001
            guardian._business_status = os.stat(  # noqa: SLF001
                BUSINESS_NAME,
                dir_fd=guardian._outer_fd,  # noqa: SLF001
                follow_symlinks=False,
            )
            guardian._business_fd = outer_v1._open_directory(  # noqa: SLF001
                guardian._outer_fd, BUSINESS_NAME  # noqa: SLF001
            )
            if not _same_status(
                guardian._business_fd, guardian._business_status  # noqa: SLF001
            ):
                _fail("business descriptor identity changed at creation")
            outer_v1._verify_named_descriptor(  # noqa: SLF001
                guardian._outer_fd, BUSINESS_NAME, guardian._business_status  # noqa: SLF001
            )
            for name in outer_v1.WORKER_REQUIRED_FILES:
                inner_v1._read_control(guardian._business_fd, name)  # noqa: SLF001
            outer_v1._validate_fresh_domain(guardian._business_fd)  # noqa: SLF001
            for name, value in LEAF_CONTROL_READBACKS:
                inner_v1._write_control(guardian._business_fd, name, value)  # noqa: SLF001
            if not outer_v1._controls_match(  # noqa: SLF001
                guardian._business_fd, LEAF_CONTROL_READBACKS  # noqa: SLF001
            ):
                _fail("business controls differ from the exact leaf profile")
            stats = outer_v1._cgroup_stat(guardian._outer_fd)  # noqa: SLF001
            if stats["nr_descendants"] != 2 or stats["nr_dying_descendants"] != 0:
                _fail("prepared outer topology does not contain two live siblings")
            outer_v1._verify_named_descriptor(  # noqa: SLF001
                guardian._outer_fd,
                guardian._worker_name,  # noqa: SLF001
                guardian._worker_status,  # noqa: SLF001
            )
            outer_v1._verify_named_descriptor(  # noqa: SLF001
                guardian._outer_fd,
                BUSINESS_NAME,
                guardian._business_status,  # noqa: SLF001
            )
            outer_v1._verify_named_descriptor(  # noqa: SLF001
                guardian._parent_fd,
                guardian._outer_name,  # noqa: SLF001
                guardian._outer_status,  # noqa: SLF001
            )

            guardian._kill_fd = inner_v1._open_control(  # noqa: SLF001
                guardian._outer_fd, "cgroup.kill", os.O_WRONLY  # noqa: SLF001
            )
            if (
                guardian._peak_fd < 0  # noqa: SLF001
                or guardian._peak_status is None  # noqa: SLF001
                or not _same_status(  # noqa: SLF001
                    guardian._peak_fd, guardian._peak_status
                )
                or guardian._peak_reset_peak != 0  # noqa: SLF001
                or guardian._peak_reset_current != 0  # noqa: SLF001
            ):
                _fail("broker preparation lacks the retained zero-reset peak OFD")

            worker_socket, business_socket = socket.socketpair(
                socket.AF_UNIX, socket.SOCK_STREAM
            )
            worker_socket.set_inheritable(False)
            business_socket.set_inheritable(False)
            guardian._worker_socket_fd = worker_socket.detach()  # noqa: SLF001
            guardian._business_socket_fd = business_socket.detach()  # noqa: SLF001
            prelaunch_peak = _read_open_control(  # noqa: SLF001
                guardian._peak_fd, "memory.peak"
            )
            prelaunch_current = inner_v1._parse_nonnegative(  # noqa: SLF001
                inner_v1._read_control(guardian._outer_fd, "memory.current"),  # noqa: SLF001
                "memory.current",
            )
            if prelaunch_peak < prelaunch_current:
                _fail(
                    "zero-reset retained memory.peak is below current memory "
                    "after preparation"
                )
            nonce = secrets.token_hex(32)
            spec = K7OuterAttemptBrokerExecutionSpecV1(
                _SPEC_ISSUER,
                guardian._request_id,  # noqa: SLF001
                guardian._route_identity_id,  # noqa: SLF001
                guardian._outer_lease_id,  # noqa: SLF001
                _descriptor(guardian._parent_status),  # noqa: SLF001
                _descriptor(guardian._outer_status),  # noqa: SLF001
                _descriptor(guardian._worker_status),  # noqa: SLF001
                _descriptor(guardian._business_status),  # noqa: SLF001
                _descriptor(os.fstat(guardian._kill_fd)),  # noqa: SLF001
                _descriptor(os.fstat(guardian._peak_fd)),  # noqa: SLF001
                _descriptor(os.fstat(guardian._worker_socket_fd)),  # noqa: SLF001
                _descriptor(os.fstat(guardian._business_socket_fd)),  # noqa: SLF001
                hashlib.sha256(
                    guardian._outer_name.encode("ascii")  # noqa: SLF001
                ).hexdigest(),
                nonce,
                prelaunch_peak,
                prelaunch_current,
            )
            binding = ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
                guardian._request_id,  # noqa: SLF001
                guardian._route_identity_id,  # noqa: SLF001
                spec.spec_id,
                nonce,
            )
            return K7OuterAttemptPreparedBrokerSessionV1(
                _SESSION_ISSUER,
                spec,
                binding,
                guardian._peak_reset_peak,  # noqa: SLF001
                guardian._peak_reset_current,  # noqa: SLF001
                prelaunch_peak,
                prelaunch_current,
                guardian,
            )
        except BaseException as error:
            if guardian is None and guardian_holder:
                candidate = guardian_holder[0]
                if type(candidate) is guardian_type:
                    guardian = candidate
            transfer_token = (
                guardian._transfer_token  # noqa: SLF001
                if guardian is not None
                else None
            )
            try:
                guardian_owns_cleanup = (
                    lease._resolve_failed_broker_preparation_transfer(  # noqa: SLF001
                        outer_v1._BROKER_PREPARATION_TRANSFER_ISSUER,  # noqa: SLF001
                        transfer_token,
                    )
                )
            except BaseException as cleanup_error:
                raise V075K7OuterAttemptBrokerPreparationV1Error(
                    "broker preparation failed and lease cleanup is retryable"
                ) from cleanup_error
            if not guardian_owns_cleanup:
                guardian = None
                if isinstance(error, V075K7OuterAttemptBrokerPreparationV1Error):
                    raise
                raise V075K7OuterAttemptBrokerPreparationV1Error(
                    "broker preparation failed before transfer"
                ) from error
            try:
                guardian.close_prelaunch()
            except BaseException as cleanup_error:
                if isinstance(
                    cleanup_error,
                    V075K7OuterAttemptBrokerPreparationProtocolV1Error,
                ):
                    raise cleanup_error
                if guardian.cleanup_state is (
                    K7PreparedBrokerCleanupStateV1
                    .IDENTITY_UNBOUND_REQUIRES_PARENT_GUARD
                ):
                    raise V075K7OuterAttemptBrokerPreparationV1Error(
                        "broker preparation failed before business identity "
                        "capture and requires the preexisting parent guardian",
                        guardian=guardian,
                    ) from cleanup_error
                raise V075K7OuterAttemptBrokerPreparationV1Error(
                    "broker preparation failed and cleanup is retryable",
                    guardian=guardian,
                ) from cleanup_error
            if isinstance(error, V075K7OuterAttemptBrokerPreparationV1Error):
                raise
            raise V075K7OuterAttemptBrokerPreparationV1Error(
                "broker preparation failed closed"
            ) from error

    def __reduce__(self):
        raise TypeError("broker-preparation service is unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("broker-preparation service is unpickleable")


_SERVICE = K7OuterAttemptBrokerPreparationServiceV1()


def official_v075_k7_outer_attempt_broker_preparation_service_v1(
) -> K7OuterAttemptBrokerPreparationServiceV1:
    return _SERVICE


def prepare_v075_k7_outer_attempt_broker_session_v1(
    lease: outer_v1.K7OuterAttemptCgroupLeaseV1,
) -> K7OuterAttemptPreparedBrokerSessionV1:
    return _SERVICE.prepare(lease)


__all__ = (
    "BUSINESS_NAME",
    "K7OuterAttemptBrokerExecutionSpecV1",
    "K7OuterAttemptBrokerPreparationProfileV1",
    "K7OuterAttemptBrokerPreparationServiceV1",
    "K7OuterAttemptPreparedBrokerSessionV1",
    "K7OuterAttemptPrelaunchGuardianV1",
    "K7PreparedBrokerCleanupStateV1",
    "LOCAL_DOMAIN_TAGS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "V075K7OuterAttemptBrokerPreparationV1Error",
    "V075K7OuterAttemptBrokerPreparationProtocolV1Error",
    "official_v075_k7_outer_attempt_broker_preparation_profile_v1",
    "official_v075_k7_outer_attempt_broker_preparation_service_v1",
    "prepare_v075_k7_outer_attempt_broker_session_v1",
)
