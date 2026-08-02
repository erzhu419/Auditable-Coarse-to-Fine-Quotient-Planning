"""Process-local resource preparation for the K7 two-role broker v2.

This module joins one executable production role manifest and its two launch
contexts to the concrete descriptor topology needed by a future live broker:
two broker-mediated ``AF_UNIX/SOCK_SEQPACKET`` channels, one shared result
memfd with distinct read-write/read-only open descriptions, and one fresh
output directory exposed to the worker role only.  It launches no process,
sends no protocol packet, and issues no accounting receipt.

All serialized identities use centrally registered domain-separated content
IDs.  The session nevertheless remains process-local and construction-only.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import fcntl
import hashlib
import os
import socket
import stat
import threading
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_production_role_bootstrap_v2 as bootstrap_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_BROKER_RESOURCE_SESSION_PROFILE_V2_DOMAIN,
    V075_K7_BROKER_RESOURCE_SESSION_V2_DOMAIN,
    V075_K7_BROKER_ROLE_CAPABILITY_BUNDLE_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.15"
PROFILE_KEY = "v075_k7_broker_resource_session_v2"

BROKER_RESOURCE_SESSION_PROFILE_V2_DOMAIN = (
    V075_K7_BROKER_RESOURCE_SESSION_PROFILE_V2_DOMAIN
)
BROKER_ROLE_CAPABILITY_BUNDLE_V2_DOMAIN = (
    V075_K7_BROKER_ROLE_CAPABILITY_BUNDLE_V2_DOMAIN
)
BROKER_RESOURCE_SESSION_V2_DOMAIN = V075_K7_BROKER_RESOURCE_SESSION_V2_DOMAIN
REQUESTED_PHASE3E_DOMAIN_TAGS = (
    BROKER_RESOURCE_SESSION_PROFILE_V2_DOMAIN,
    BROKER_ROLE_CAPABILITY_BUNDLE_V2_DOMAIN,
    BROKER_RESOURCE_SESSION_V2_DOMAIN,
)
if not frozenset(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("broker resource-session domains are unregistered")

OUTPUT_DIRECTORY_PREFIX = ".acfqp-k7-broker-v2-"
MAX_OUTPUT_DIRECTORY_NAME_BYTES = 96
BROKER_DESCRIPTOR_ROLES = (
    "WORKER_CHANNEL",
    "BUSINESS_CHANNEL",
    "BUSINESS_RESULT_READONLY",
    "OUTPUT_DIRECTORY",
)
WORKER_RUNTIME_DESCRIPTOR_ROLES = bootstrap_v2.WORKER_CAPABILITY_ROLES
BUSINESS_RUNTIME_DESCRIPTOR_ROLES = bootstrap_v2.BUSINESS_CAPABILITY_ROLES

_BROKER_RUNTIME_DESCRIPTOR_MAP = MappingProxyType(
    {
        "WORKER_CHANNEL": "worker_broker_channel",
        "BUSINESS_CHANNEL": "business_broker_channel",
        "BUSINESS_RESULT_READONLY": "broker_result_readonly",
        "OUTPUT_DIRECTORY": "broker_output_directory",
    }
)
_WORKER_RUNTIME_DESCRIPTOR_MAP = MappingProxyType(
    {
        "BROKER_CHANNEL": "worker_child_channel",
        "BUSINESS_RESULT_READONLY": "worker_result_readonly",
        "OUTPUT_DIRECTORY": "worker_output_directory",
    }
)
_BUSINESS_RUNTIME_DESCRIPTOR_MAP = MappingProxyType(
    {
        "BROKER_CHANNEL": "business_child_channel",
        "BUSINESS_RESULT_WRITABLE": "business_result_readwrite",
    }
)

_PROFILE_ISSUER = object()
_BUNDLE_ISSUER = object()
_SESSION_ISSUER = object()
_GUARDIAN_ISSUER = object()
_RUNTIME_TRANSFER_ISSUER = object()
_PREPARATION_LOCK = threading.Lock()
_CONSUMED_CONTEXTS: set[tuple[int, str, str, str]] = set()


class V075K7BrokerResourceSessionV2Error(RuntimeError):
    """The resource topology is stale, crossed, contaminated, or mistyped."""


class V075K7BrokerResourceSessionCleanupV2Error(
    V075K7BrokerResourceSessionV2Error
):
    """Prepared resources could not be closed without losing cleanup state."""

    def __init__(self, message: str, *, guardian: Any) -> None:
        super().__init__(message)
        self.guardian = guardian


class K7BrokerResourceSessionStateV2(str, Enum):
    PREPARED = "PREPARED"
    RUNTIME_TRANSFERRED = "RUNTIME_TRANSFERRED"
    CLEANUP_PARTIAL = "CLEANUP_PARTIAL"
    CLOSED = "CLOSED"


def _fail(message: str) -> NoReturn:
    raise V075K7BrokerResourceSessionV2Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("broker resource session used an undeclared domain")
    return content_id(domain, dict(payload))


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7BrokerResourceSessionV2Error(
            f"{label} must be one exact content ID"
        ) from error


def _formal_locks() -> dict[str, bool]:
    return {
        "outer_cgroup_guardian_joined": False,
        "native_role_launcher_implemented": False,
        "role_specific_seccomp_implemented": False,
        "role_specific_landlock_implemented": False,
        "live_sender_credentials_verified": False,
        "complete_five_frame_protocol_verified": False,
        "post_reap_supervisor_envelope_issued": False,
        "shared_resource_receipts_issued": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "official_execution_allowed": False,
    }


def _descriptor_identity(descriptor: int) -> tuple[int, int, int, int, int, int]:
    try:
        status = os.fstat(descriptor)
    except OSError as error:
        raise V075K7BrokerResourceSessionV2Error(
            "broker resource descriptor is no longer live"
        ) from error
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
        status.st_rdev,
    )


def _identity_document(
    identity: tuple[int, int, int, int, int, int],
) -> dict[str, int]:
    return {
        "device": identity[0],
        "inode": identity[1],
        "mode": identity[2],
        "owner_uid": identity[3],
        "owner_gid": identity[4],
        "rdev": identity[5],
    }


def _fd_flags(descriptor: int) -> int:
    try:
        return fcntl.fcntl(descriptor, fcntl.F_GETFL)
    except OSError as error:
        raise V075K7BrokerResourceSessionV2Error(
            "broker resource descriptor flags are unavailable"
        ) from error


def _duplicate_cloexec(descriptor: int) -> int:
    try:
        duplicate = fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, 3)
        os.set_inheritable(duplicate, False)
        return duplicate
    except OSError as error:
        raise V075K7BrokerResourceSessionV2Error(
            "broker resource descriptor could not be duplicated"
        ) from error


def _socket_state(descriptor: int) -> tuple[int, int, int, bool, bool]:
    duplicate = -1
    endpoint: socket.socket | None = None
    try:
        duplicate = _duplicate_cloexec(descriptor)
        endpoint = socket.socket(fileno=duplicate)
        duplicate = -1
        endpoint.getpeername()
        domain = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_DOMAIN)
        socket_type = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
        passcred = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED)
        flags = _fd_flags(endpoint.fileno())
        inheritable = os.get_inheritable(endpoint.fileno())
        try:
            queued = endpoint.recv(
                1,
                socket.MSG_PEEK | socket.MSG_DONTWAIT,
            )
        except BlockingIOError:
            queued = None
        if queued is not None:
            _fail("prepared broker channel is not empty")
        return domain, socket_type, passcred, bool(flags & os.O_NONBLOCK), inheritable
    except OSError as error:
        raise V075K7BrokerResourceSessionV2Error(
            "prepared broker channel cannot be replayed"
        ) from error
    finally:
        if endpoint is not None:
            endpoint.close()
        elif duplicate >= 0:
            os.close(duplicate)


def _assert_socket(
    descriptor: int,
    *,
    expected_identity: tuple[int, int, int, int, int, int],
    broker_endpoint: bool,
) -> None:
    identity = _descriptor_identity(descriptor)
    domain, socket_type, passcred, nonblocking, inheritable = _socket_state(
        descriptor
    )
    if (
        identity != expected_identity
        or not stat.S_ISSOCK(identity[2])
        or domain != socket.AF_UNIX
        or socket_type != socket.SOCK_SEQPACKET
        or passcred != (1 if broker_endpoint else 0)
        or nonblocking
        or inheritable
    ):
        _fail("prepared broker channel identity or kernel state changed")


def _memfd_state(descriptor: int) -> tuple[
    tuple[int, int, int, int, int, int], int, int, bool
]:
    try:
        identity = _descriptor_identity(descriptor)
        flags = _fd_flags(descriptor)
        seals = fcntl.fcntl(descriptor, runtime_v1.F_GET_SEALS)
        inheritable = os.get_inheritable(descriptor)
        size = os.fstat(descriptor).st_size
    except OSError as error:
        raise V075K7BrokerResourceSessionV2Error(
            "prepared result memfd cannot be replayed"
        ) from error
    if not stat.S_ISREG(identity[2]) or size != 0 or seals != 0 or inheritable:
        _fail("prepared result memfd is not empty, unsealed, regular, and CLOEXEC")
    return identity, flags & os.O_ACCMODE, seals, inheritable


def _assert_output_directory(
    descriptor: int,
    *,
    expected_identity: tuple[int, int, int, int, int, int],
) -> None:
    try:
        identity = _descriptor_identity(descriptor)
        flags = _fd_flags(descriptor)
        entries = os.listdir(descriptor)
        inheritable = os.get_inheritable(descriptor)
    except OSError as error:
        raise V075K7BrokerResourceSessionV2Error(
            "prepared output directory cannot be replayed"
        ) from error
    if (
        identity != expected_identity
        or not stat.S_ISDIR(identity[2])
        or flags & getattr(os, "O_PATH", 0)
        or entries
        or inheritable
    ):
        _fail("prepared output directory identity, emptiness, or flags changed")


@dataclass(frozen=True, slots=True)
class K7BrokerResourceSessionProfileV2:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("broker resource-session profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(BROKER_RESOURCE_SESSION_PROFILE_V2_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_broker_resource_session_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "role_order": list(bootstrap_v2.ROLE_ORDER),
            "channel_topology": [
                "BROKER_TO_WORKER_SEQPACKET",
                "BROKER_TO_BUSINESS_SEQPACKET",
            ],
            "broker_receive_end_so_passcred_required": True,
            "child_end_so_passcred_required": False,
            "result_memfd_open_descriptions": [
                "BUSINESS_READWRITE",
                "WORKER_READONLY",
                "BROKER_READONLY",
            ],
            "worker_only_child_role_output_directory": True,
            "exclusive_global_output_writer_verified": False,
            "capability_fd_numbers_cross_role_disjoint": True,
            "sealed_input_lane_join_deferred_to_native_launcher": True,
            "one_shot_runtime_transfer": True,
            "runtime_transfer_replays_prepared_state_under_guardian_lock": True,
            "runtime_parent_descriptor_retirement_is_monotone": True,
            "runtime_transfer_claims_launch_or_output": False,
            "runtime_transfer_claims_accounting": False,
            "process_local": True,
            "central_domain_registration_pending_merge": False,
            "construction_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _hash(
            BROKER_RESOURCE_SESSION_PROFILE_V2_DOMAIN, self._payload()
        ) != self._profile_id:
            _fail("broker resource-session profile changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "broker_resource_session_profile_id": self.profile_id}


_OFFICIAL_PROFILE = K7BrokerResourceSessionProfileV2(_PROFILE_ISSUER)


def official_v075_k7_broker_resource_session_profile_v2(
) -> K7BrokerResourceSessionProfileV2:
    return _OFFICIAL_PROFILE


@dataclass(frozen=True, slots=True)
class K7BrokerRoleCapabilityBundleV2:
    _issuer: InitVar[object]
    role: manifest_v2.K7ProductionBrokerRoleV2
    manifest_id: str
    launch_context_id: str
    request_id: str
    route_identity_id: str
    broker_execution_spec_id: str
    session_nonce: str
    _guardian: Any = field(repr=False, compare=False)
    _descriptors: Mapping[str, int] = field(repr=False, compare=False)
    _identities: Mapping[str, tuple[int, int, int, int, int, int]] = field(
        repr=False, compare=False
    )
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BUNDLE_ISSUER:
            _fail("broker role capability bundle is issuer-owned")
        exact_role = manifest_v2.K7ProductionBrokerRoleV2(self.role)
        object.__setattr__(self, "role", exact_role)
        for value, label in (
            (self.manifest_id, "manifest"),
            (self.launch_context_id, "launch context"),
            (self.request_id, "request"),
            (self.route_identity_id, "route identity"),
            (self.broker_execution_spec_id, "broker execution spec"),
        ):
            _cid(value, label)
        _cid(self.session_nonce, "session nonce")
        expected_roles = (
            bootstrap_v2.WORKER_CAPABILITY_ROLES
            if exact_role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
            else bootstrap_v2.BUSINESS_CAPABILITY_ROLES
        )
        if (
            type(self._descriptors) not in {dict, MappingProxyType}
            or tuple(self._descriptors) != expected_roles
            or type(self._identities) not in {dict, MappingProxyType}
            or tuple(self._identities) != expected_roles
            or any(type(fd) is not int or fd < 3 for fd in self._descriptors.values())
            or len(set(self._descriptors.values())) != len(expected_roles)
            or type(self._guardian) is not K7BrokerResourceGuardianV2
        ):
            _fail("broker role capability descriptor lanes are malformed")
        for name in expected_roles:
            if _descriptor_identity(self._descriptors[name]) != self._identities[name]:
                _fail("broker role capability identity changed before issuance")
        object.__setattr__(
            self, "_descriptors", MappingProxyType(dict(self._descriptors))
        )
        object.__setattr__(
            self, "_identities", MappingProxyType(dict(self._identities))
        )
        object.__setattr__(
            self,
            "_bundle_id",
            _hash(BROKER_ROLE_CAPABILITY_BUNDLE_V2_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_broker_role_capability_bundle.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "broker_resource_session_profile_id": _OFFICIAL_PROFILE.profile_id,
            "role": self.role.value,
            "production_role_manifest_id": self.manifest_id,
            "production_role_launch_context_id": self.launch_context_id,
            "request_id": self.request_id,
            "route_identity_id": self.route_identity_id,
            "broker_execution_spec_id": self.broker_execution_spec_id,
            "session_nonce": self.session_nonce,
            "capability_fd_roles": list(self._descriptors),
            "descriptor_identities": [
                {
                    "role": name,
                    **_identity_document(self._identities[name]),
                }
                for name in self._descriptors
            ],
            "raw_descriptor_numbers_serialized": False,
            "sealed_input_fd_lane_included": False,
            "caller_selected_fd_roles": False,
            "construction_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def bundle_id(self) -> str:
        if _hash(
            BROKER_ROLE_CAPABILITY_BUNDLE_V2_DOMAIN, self._payload()
        ) != self._bundle_id:
            _fail("broker role capability bundle changed")
        return self._bundle_id

    @property
    def descriptor_roles(self) -> tuple[str, ...]:
        return tuple(self._descriptors)

    def descriptor(self, role: str) -> int:
        if type(role) is not str or role not in self._descriptors:
            _fail("broker role capability requested an unknown descriptor role")
        self._guardian._assert_session_capability_access()  # noqa: SLF001
        descriptor = self._descriptors[role]
        if _descriptor_identity(descriptor) != self._identities[role]:
            _fail("broker role capability descriptor changed")
        return descriptor

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "broker_role_capability_bundle_id": self.bundle_id}

    def __reduce__(self):
        raise TypeError("broker role capability bundle is process-local")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("broker role capability bundle is process-local")


class K7BrokerResourceGuardianV2:
    """Sole process-local cleanup owner for one unlaunched resource session."""

    def __init__(
        self,
        issuer: object,
        *,
        descriptors: Mapping[str, int],
        identities: Mapping[str, tuple[int, int, int, int, int, int]],
        output_parent_fd: int,
        output_parent_identity: tuple[int, int, int, int, int, int],
        output_name: str,
        output_status: os.stat_result,
    ) -> None:
        if issuer is not _GUARDIAN_ISSUER:
            _fail("broker resource guardian is issuer-owned")
        self._owner_pid = os.getpid()
        self._descriptors = dict(descriptors)
        self._identities = dict(identities)
        self._output_parent_fd = output_parent_fd
        self._output_parent_identity = output_parent_identity
        self._output_name = output_name
        self._output_status = output_status
        self._output_removed = False
        self._output_unlinked = False
        self._output_parent_synced = False
        self._runtime_transferred = False
        self._retired_runtime_roles: set[str] = set()
        self._state = K7BrokerResourceSessionStateV2.PREPARED
        self._lock = threading.Lock()

    @property
    def state(self) -> K7BrokerResourceSessionStateV2:
        if os.getpid() != self._owner_pid:
            _fail("broker resource guardian crossed a process boundary")
        return self._state

    @property
    def closed(self) -> bool:
        return self.state is K7BrokerResourceSessionStateV2.CLOSED

    def _check_owner(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("broker resource guardian crossed a process boundary")
        if self._state is K7BrokerResourceSessionStateV2.CLOSED:
            _fail("broker resource guardian is closed")

    def _assert_session_capability_access(self) -> None:
        with self._lock:
            self._check_owner()
            if self._state is not K7BrokerResourceSessionStateV2.PREPARED:
                _fail("broker resource session authority is no longer PREPARED")

    def _assert_current_locked(self) -> None:
        self._check_owner()
        if self._state is not K7BrokerResourceSessionStateV2.PREPARED:
            _fail("broker resource guardian is not PREPARED")
        for name in (
            "worker_broker_channel",
            "worker_child_channel",
            "business_broker_channel",
            "business_child_channel",
        ):
            _assert_socket(
                self._descriptors[name],
                expected_identity=self._identities[name],
                broker_endpoint=name.endswith("broker_channel"),
            )
        memfd_rows = (
            ("business_result_readwrite", os.O_RDWR),
            ("worker_result_readonly", os.O_RDONLY),
            ("broker_result_readonly", os.O_RDONLY),
        )
        observed_memfds = []
        for name, expected_access in memfd_rows:
            identity, access, seals, inheritable = _memfd_state(
                self._descriptors[name]
            )
            if (
                identity != self._identities[name]
                or access != expected_access
                or seals != 0
                or inheritable
            ):
                _fail("prepared result memfd role changed")
            observed_memfds.append(identity[:2])
        if len(set(observed_memfds)) != 1:
            _fail("prepared result memfd open descriptions crossed inodes")
        for name in ("worker_output_directory", "broker_output_directory"):
            _assert_output_directory(
                self._descriptors[name],
                expected_identity=self._identities[name],
            )
        if self._identities["worker_output_directory"][:2] != self._identities[
            "broker_output_directory"
        ][:2]:
            _fail("worker and broker output-directory views crossed inodes")
        if _descriptor_identity(self._output_parent_fd) != self._output_parent_identity:
            _fail("broker output parent descriptor changed")
        try:
            named = os.stat(
                self._output_name,
                dir_fd=self._output_parent_fd,
                follow_symlinks=False,
            )
        except OSError as error:
            raise V075K7BrokerResourceSessionV2Error(
                "prepared output directory name cannot be replayed"
            ) from error
        if (
            named.st_dev,
            named.st_ino,
            named.st_mode,
            named.st_uid,
            named.st_gid,
            named.st_rdev,
        ) != self._identities["broker_output_directory"]:
            _fail("prepared output directory name crossed its inode")

    def _assert_runtime_identity_locked(self) -> None:
        self._check_owner()
        if (
            not self._runtime_transferred
            or self._state
            not in {
                K7BrokerResourceSessionStateV2.RUNTIME_TRANSFERRED,
                K7BrokerResourceSessionStateV2.CLEANUP_PARTIAL,
            }
        ):
            _fail("broker resources are not owned by a live runtime transfer")
        for name, descriptor in self._descriptors.items():
            if descriptor < 0:
                continue
            if _descriptor_identity(descriptor) != self._identities[name]:
                _fail("runtime transfer descriptor identity changed")
        if self._output_parent_fd >= 0:
            if (
                _descriptor_identity(self._output_parent_fd)
                != self._output_parent_identity
            ):
                _fail("runtime transfer output-parent FD identity changed")
            if not self._output_unlinked:
                try:
                    named = os.stat(
                        self._output_name,
                        dir_fd=self._output_parent_fd,
                        follow_symlinks=False,
                    )
                except OSError as error:
                    raise V075K7BrokerResourceSessionV2Error(
                        "runtime output directory name cannot be replayed"
                    ) from error
                if (
                    named.st_dev,
                    named.st_ino,
                    named.st_mode,
                    named.st_uid,
                    named.st_gid,
                    named.st_rdev,
                ) != self._identities["broker_output_directory"]:
                    _fail("runtime output directory name crossed its inode")

    def _assert_bundle_maps_locked(
        self, session: "K7BrokerResourceSessionV2"
    ) -> None:
        rows = (
            (session.worker_capabilities, _WORKER_RUNTIME_DESCRIPTOR_MAP),
            (session.business_capabilities, _BUSINESS_RUNTIME_DESCRIPTOR_MAP),
        )
        for bundle, mapping in rows:
            if bundle._guardian is not self:  # noqa: SLF001
                _fail("broker capability bundle crossed its cleanup guardian")
            if tuple(bundle._descriptors) != tuple(mapping):  # noqa: SLF001
                _fail("broker capability runtime role map changed")
            for role, name in mapping.items():
                if (
                    bundle._descriptors[role] != self._descriptors[name]  # noqa: SLF001
                    or bundle._identities[role] != self._identities[name]  # noqa: SLF001
                ):
                    _fail("broker capability runtime descriptor crossed")

    def _consume_for_runtime_locked(
        self, session: "K7BrokerResourceSessionV2"
    ) -> "K7BrokerRuntimeTransferAuthorityV2":
        self._assert_current_locked()
        session._assert_static_binding()  # noqa: SLF001
        self._assert_bundle_maps_locked(session)
        if (
            _hash(BROKER_RESOURCE_SESSION_V2_DOMAIN, session._payload())  # noqa: SLF001
            != session._session_id  # noqa: SLF001
        ):
            _fail("broker resource session changed before runtime transfer")
        authority = K7BrokerRuntimeTransferAuthorityV2(
            _RUNTIME_TRANSFER_ISSUER,
            guardian=self,
            resource_session_id=session._session_id,  # noqa: SLF001
        )
        self._runtime_transferred = True
        self._state = K7BrokerResourceSessionStateV2.RUNTIME_TRANSFERRED
        return authority

    def consume_for_runtime(
        self, session: "K7BrokerResourceSessionV2"
    ) -> "K7BrokerRuntimeTransferAuthorityV2":
        with self._lock:
            return self._consume_for_runtime_locked(session)

    def _runtime_descriptor(
        self,
        *,
        mapping: Mapping[str, str],
        role: str,
    ) -> int:
        if type(role) is not str or role not in mapping:
            _fail("runtime transfer requested an unknown descriptor role")
        with self._lock:
            self._assert_runtime_identity_locked()
            name = mapping[role]
            descriptor = self._descriptors[name]
            if descriptor < 0:
                _fail("runtime transfer descriptor was permanently retired")
            if _descriptor_identity(descriptor) != self._identities[name]:
                _fail("runtime transfer descriptor identity changed")
            return descriptor

    def _retire_parent_role_descriptors(
        self, role: manifest_v2.K7ProductionBrokerRoleV2
    ) -> None:
        exact_role = manifest_v2.K7ProductionBrokerRoleV2(role)
        role_name = exact_role.value
        mapping = (
            _WORKER_RUNTIME_DESCRIPTOR_MAP
            if exact_role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
            else _BUSINESS_RUNTIME_DESCRIPTOR_MAP
        )
        with self._lock:
            self._assert_runtime_identity_locked()
            if self._state is not K7BrokerResourceSessionStateV2.RUNTIME_TRANSFERRED:
                _fail("runtime descriptor retirement is unavailable during cleanup")
            if role_name in self._retired_runtime_roles:
                _fail("runtime role parent descriptors were already retired")
            first_error: BaseException | None = None
            for name in mapping.values():
                descriptor = self._descriptors[name]
                if descriptor < 0:
                    continue
                try:
                    os.close(descriptor)
                    self._descriptors[name] = -1
                except BaseException as error:
                    if first_error is None:
                        first_error = error
            if first_error is not None:
                raise V075K7BrokerResourceSessionCleanupV2Error(
                    "runtime parent-side descriptor retirement is partial",
                    guardian=self,
                ) from first_error
            self._retired_runtime_roles.add(role_name)

    def assert_current(self) -> None:
        with self._lock:
            self._assert_current_locked()

    def broker_descriptor(self, role: str) -> int:
        if type(role) is not str or role not in _BROKER_RUNTIME_DESCRIPTOR_MAP:
            _fail("broker resource guardian requested an unknown broker FD role")
        with self._lock:
            self._assert_current_locked()
            return self._descriptors[_BROKER_RUNTIME_DESCRIPTOR_MAP[role]]

    def _close_locked(self, *, runtime_owner: bool) -> None:
        self._check_owner()
        if runtime_owner != self._runtime_transferred:
            _fail("broker resource cleanup authority was transferred")
        allowed_states = (
            {
                K7BrokerResourceSessionStateV2.RUNTIME_TRANSFERRED,
                K7BrokerResourceSessionStateV2.CLEANUP_PARTIAL,
            }
            if runtime_owner
            else {
                K7BrokerResourceSessionStateV2.PREPARED,
                K7BrokerResourceSessionStateV2.CLEANUP_PARTIAL,
            }
        )
        if self._state not in allowed_states:
            _fail("broker resource cleanup state is invalid")
        self._state = K7BrokerResourceSessionStateV2.CLEANUP_PARTIAL
        first_error: BaseException | None = None
        for name in (
            "worker_broker_channel",
            "worker_child_channel",
            "business_broker_channel",
            "business_child_channel",
            "business_result_readwrite",
            "worker_result_readonly",
            "broker_result_readonly",
        ):
            descriptor = self._descriptors.get(name, -1)
            if descriptor < 0:
                continue
            try:
                os.close(descriptor)
                self._descriptors[name] = -1
            except BaseException as error:
                if first_error is None:
                    first_error = error
        if not self._output_unlinked:
            try:
                live_output_names = tuple(
                    name
                    for name in (
                        "worker_output_directory",
                        "broker_output_directory",
                    )
                    if self._descriptors[name] >= 0
                )
                if "broker_output_directory" not in live_output_names:
                    _fail("broker output cleanup descriptor was retired")
                for name in live_output_names:
                    _assert_output_directory(
                        self._descriptors[name],
                        expected_identity=self._identities[name],
                    )
                if (
                    _descriptor_identity(self._output_parent_fd)
                    != self._output_parent_identity
                ):
                    _fail("output parent changed before cleanup")
                named = os.stat(
                    self._output_name,
                    dir_fd=self._output_parent_fd,
                    follow_symlinks=False,
                )
                if (named.st_dev, named.st_ino) != (
                    self._output_status.st_dev,
                    self._output_status.st_ino,
                ):
                    _fail("output directory name changed before cleanup")
                # rmdir is intentionally attempted while both verified
                # directory handles remain open.  ENOTEMPTY preserves every
                # handle and byte for explicit caller recovery.
                os.rmdir(self._output_name, dir_fd=self._output_parent_fd)
                self._output_unlinked = True
            except BaseException as error:
                if first_error is None:
                    first_error = error
        if self._output_unlinked:
            for name in (
                "worker_output_directory",
                "broker_output_directory",
            ):
                descriptor = self._descriptors[name]
                if descriptor < 0:
                    continue
                try:
                    os.close(descriptor)
                    self._descriptors[name] = -1
                except BaseException as error:
                    if first_error is None:
                        first_error = error
        if self._output_unlinked and not self._output_parent_synced:
            try:
                os.fsync(self._output_parent_fd)
                self._output_parent_synced = True
            except BaseException as error:
                if first_error is None:
                    first_error = error
        if self._output_parent_synced and self._output_parent_fd >= 0:
            try:
                os.close(self._output_parent_fd)
                self._output_parent_fd = -1
                self._output_removed = True
            except BaseException as error:
                if first_error is None:
                    first_error = error
        if first_error is not None:
            raise V075K7BrokerResourceSessionCleanupV2Error(
                "broker resource-session cleanup is partial",
                guardian=self,
            ) from first_error
        self._state = K7BrokerResourceSessionStateV2.CLOSED

    def close(self) -> None:
        with self._lock:
            self._close_locked(runtime_owner=False)

    def _close_runtime(self) -> None:
        with self._lock:
            self._close_locked(runtime_owner=True)

    def __reduce__(self):
        raise TypeError("broker resource guardian is process-local")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("broker resource guardian is process-local")


class K7BrokerRuntimeTransferAuthorityV2:
    """One-shot runtime view over fixed role descriptors and guardian cleanup.

    It records neither a clone nor a protocol/output/accounting event.  The
    caller may retire its parent copies only after independently establishing
    the corresponding clone edge.
    """

    __slots__ = ("_guardian", "_owner_pid", "_resource_session_id")

    def __init__(
        self,
        issuer: object,
        *,
        guardian: K7BrokerResourceGuardianV2,
        resource_session_id: str,
    ) -> None:
        if (
            issuer is not _RUNTIME_TRANSFER_ISSUER
            or type(guardian) is not K7BrokerResourceGuardianV2
        ):
            _fail("broker runtime transfer authority is caller-minted")
        self._resource_session_id = _cid(
            resource_session_id,
            "runtime transfer resource session",
        )
        self._guardian = guardian
        self._owner_pid = os.getpid()

    def _check_owner(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("broker runtime transfer authority crossed a process boundary")

    @property
    def resource_session_id(self) -> str:
        self._check_owner()
        return self._resource_session_id

    @property
    def broker_descriptor_roles(self) -> tuple[str, ...]:
        return BROKER_DESCRIPTOR_ROLES

    @property
    def worker_descriptor_roles(self) -> tuple[str, ...]:
        return WORKER_RUNTIME_DESCRIPTOR_ROLES

    @property
    def business_descriptor_roles(self) -> tuple[str, ...]:
        return BUSINESS_RUNTIME_DESCRIPTOR_ROLES

    @property
    def closed(self) -> bool:
        self._check_owner()
        return self._guardian.state is K7BrokerResourceSessionStateV2.CLOSED

    def assert_current(self) -> None:
        self._check_owner()
        with self._guardian._lock:  # noqa: SLF001 - issuer-owned authority
            self._guardian._assert_runtime_identity_locked()  # noqa: SLF001

    def broker_descriptor(self, role: str) -> int:
        self._check_owner()
        return self._guardian._runtime_descriptor(  # noqa: SLF001
            mapping=_BROKER_RUNTIME_DESCRIPTOR_MAP,
            role=role,
        )

    def worker_descriptor(self, role: str) -> int:
        self._check_owner()
        return self._guardian._runtime_descriptor(  # noqa: SLF001
            mapping=_WORKER_RUNTIME_DESCRIPTOR_MAP,
            role=role,
        )

    def business_descriptor(self, role: str) -> int:
        self._check_owner()
        return self._guardian._runtime_descriptor(  # noqa: SLF001
            mapping=_BUSINESS_RUNTIME_DESCRIPTOR_MAP,
            role=role,
        )

    def retire_parent_side_descriptors_after_clone_v2(
        self,
        role: manifest_v2.K7ProductionBrokerRoleV2 | str,
    ) -> None:
        self._check_owner()
        self._guardian._retire_parent_role_descriptors(  # noqa: SLF001
            manifest_v2.K7ProductionBrokerRoleV2(role)
        )

    def close(self) -> None:
        self._check_owner()
        self._guardian._close_runtime()  # noqa: SLF001

    def __enter__(self) -> "K7BrokerRuntimeTransferAuthorityV2":
        self.assert_current()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def __reduce__(self):
        raise TypeError("broker runtime transfer authority is process-local")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("broker runtime transfer authority is process-local")


@dataclass(frozen=True, slots=True)
class K7BrokerResourceSessionV2:
    _issuer: InitVar[object]
    manifest: manifest_v2.K7ProductionRoleManifestV2 = field(
        repr=False, compare=False
    )
    worker_context: manifest_v2.K7ProductionRoleLaunchContextV2 = field(
        repr=False, compare=False
    )
    business_context: manifest_v2.K7ProductionRoleLaunchContextV2 = field(
        repr=False, compare=False
    )
    worker_capabilities: K7BrokerRoleCapabilityBundleV2
    business_capabilities: K7BrokerRoleCapabilityBundleV2
    guardian: K7BrokerResourceGuardianV2 = field(repr=False, compare=False)
    output_directory_name_sha256: str
    _session_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _SESSION_ISSUER
            or type(self.manifest) is not manifest_v2.K7ProductionRoleManifestV2
            or type(self.worker_context)
            is not manifest_v2.K7ProductionRoleLaunchContextV2
            or type(self.business_context)
            is not manifest_v2.K7ProductionRoleLaunchContextV2
            or type(self.worker_capabilities) is not K7BrokerRoleCapabilityBundleV2
            or type(self.business_capabilities) is not K7BrokerRoleCapabilityBundleV2
            or type(self.guardian) is not K7BrokerResourceGuardianV2
        ):
            _fail("broker resource session is caller-minted or mistyped")
        _cid(self.output_directory_name_sha256, "output directory name digest")
        worker_fds = self.worker_capabilities._descriptors.values()  # noqa: SLF001
        business_fds = self.business_capabilities._descriptors.values()  # noqa: SLF001
        all_role_fds = tuple(worker_fds) + tuple(business_fds)
        if len(all_role_fds) != len(set(all_role_fds)):
            _fail("worker/business capability FD lanes overlap")
        self._assert_static_binding()
        object.__setattr__(
            self,
            "_session_id",
            _hash(BROKER_RESOURCE_SESSION_V2_DOMAIN, self._payload()),
        )

    def _assert_static_binding(self) -> None:
        self.manifest.assert_current()
        worker = self.worker_context
        business = self.business_context
        if (
            worker.manifest is not self.manifest
            or business.manifest is not self.manifest
            or worker.role is not manifest_v2.K7ProductionBrokerRoleV2.WORKER
            or business.role is not manifest_v2.K7ProductionBrokerRoleV2.BUSINESS
            or worker.binding is not business.binding
            or self.worker_capabilities.role
            is not manifest_v2.K7ProductionBrokerRoleV2.WORKER
            or self.business_capabilities.role
            is not manifest_v2.K7ProductionBrokerRoleV2.BUSINESS
            or self.worker_capabilities.manifest_id != self.manifest.manifest_id
            or self.business_capabilities.manifest_id != self.manifest.manifest_id
            or self.worker_capabilities.launch_context_id != worker.context_id
            or self.business_capabilities.launch_context_id != business.context_id
        ):
            _fail("broker resource session crossed manifest/context roles")
        binding = worker.binding
        for bundle in (self.worker_capabilities, self.business_capabilities):
            if (
                bundle.request_id != binding.request_id
                or bundle.route_identity_id != binding.route_identity_id
                or bundle.broker_execution_spec_id
                != binding.broker_execution_spec_id
                or bundle.session_nonce != binding.session_nonce
            ):
                _fail("broker capability bundle crossed its launch binding")

    def _payload(self) -> dict[str, Any]:
        binding = self.worker_context.binding
        return {
            "schema": "acfqp.v075_k7_broker_resource_session.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "broker_resource_session_profile_id": _OFFICIAL_PROFILE.profile_id,
            "production_role_manifest_id": self.manifest.manifest_id,
            "worker_launch_context_id": self.worker_context.context_id,
            "business_launch_context_id": self.business_context.context_id,
            **binding.to_document(),
            "worker_capability_bundle_id": self.worker_capabilities.bundle_id,
            "business_capability_bundle_id": self.business_capabilities.bundle_id,
            "output_directory_name_sha256": self.output_directory_name_sha256,
            "role_capability_fd_numbers_cross_role_disjoint": True,
            "worker_only_child_role_has_output_directory": True,
            "broker_so_passcred_receive_end_count": 2,
            "protocol_frames_sent": 0,
            "processes_launched": 0,
            "post_reap_envelope": None,
            "shared_resource_receipts": None,
            "construction_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def session_id(self) -> str:
        self.guardian._assert_session_capability_access()  # noqa: SLF001
        if _hash(BROKER_RESOURCE_SESSION_V2_DOMAIN, self._payload()) != self._session_id:
            _fail("broker resource session changed")
        return self._session_id

    def assert_current(self) -> None:
        self.guardian.assert_current()
        self._assert_static_binding()
        for bundle in (self.worker_capabilities, self.business_capabilities):
            for role in bundle.descriptor_roles:
                bundle.descriptor(role)
        _ = self.session_id

    def role_capabilities(
        self, role: manifest_v2.K7ProductionBrokerRoleV2
    ) -> K7BrokerRoleCapabilityBundleV2:
        exact = manifest_v2.K7ProductionBrokerRoleV2(role)
        self.assert_current()
        return (
            self.worker_capabilities
            if exact is manifest_v2.K7ProductionBrokerRoleV2.WORKER
            else self.business_capabilities
        )

    def broker_descriptor(self, role: str) -> int:
        if role not in BROKER_DESCRIPTOR_ROLES:
            _fail("broker resource session requested an unknown broker FD role")
        return self.guardian.broker_descriptor(role)

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "broker_resource_session_id": self.session_id}

    def close(self) -> None:
        self.guardian.close()

    def consume_for_runtime_v2(self) -> K7BrokerRuntimeTransferAuthorityV2:
        """Atomically replay and permanently transfer this prepared session."""

        return self.guardian.consume_for_runtime(self)

    def __enter__(self) -> "K7BrokerResourceSessionV2":
        self.assert_current()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def __reduce__(self):
        raise TypeError("broker resource session is process-local")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("broker resource session is process-local")


def _output_directory_name(
    manifest: manifest_v2.K7ProductionRoleManifestV2,
    worker_context: manifest_v2.K7ProductionRoleLaunchContextV2,
    business_context: manifest_v2.K7ProductionRoleLaunchContextV2,
) -> str:
    digest = hashlib.sha256(
        canonical_json_bytes(
            {
                "manifest_id": manifest.manifest_id,
                "worker_context_id": worker_context.context_id,
                "business_context_id": business_context.context_id,
                "session_nonce": worker_context.binding.session_nonce,
            }
        )
    ).hexdigest()
    name = OUTPUT_DIRECTORY_PREFIX + digest[:40]
    if len(os.fsencode(name)) > MAX_OUTPUT_DIRECTORY_NAME_BYTES:
        _fail("derived broker output directory name exceeds its cap")
    return name


def _new_socket_pair() -> tuple[int, int]:
    flags = socket.SOCK_SEQPACKET | getattr(socket, "SOCK_CLOEXEC", 0)
    broker: socket.socket | None = None
    child: socket.socket | None = None
    try:
        broker, child = socket.socketpair(socket.AF_UNIX, flags)
        broker.setblocking(True)
        child.setblocking(True)
        broker.set_inheritable(False)
        child.set_inheritable(False)
        broker.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        if child.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED) != 0:
            _fail("new child channel unexpectedly enabled SO_PASSCRED")
        return broker.detach(), child.detach()
    except BaseException:
        if broker is not None:
            try:
                broker.close()
            except BaseException:
                pass
        if child is not None:
            try:
                child.close()
            except BaseException:
                pass
        raise


def _open_readonly_memfd_view(readwrite_fd: int) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC
    try:
        descriptor = os.open(f"/proc/self/fd/{readwrite_fd}", flags)
        os.set_inheritable(descriptor, False)
        return descriptor
    except OSError as error:
        raise V075K7BrokerResourceSessionV2Error(
            "read-only result memfd view could not be opened"
        ) from error


def _open_output_directory(parent_fd: int, name: str) -> tuple[int, int, os.stat_result]:
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    os.mkdir(name, mode=0o700, dir_fd=parent_fd)
    status = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    broker_fd = os.open(name, flags, dir_fd=parent_fd)
    try:
        worker_fd = os.open(name, flags, dir_fd=parent_fd)
    except BaseException:
        os.close(broker_fd)
        raise
    return broker_fd, worker_fd, status


def prepare_v075_k7_broker_resource_session_v2(
    *,
    manifest: manifest_v2.K7ProductionRoleManifestV2,
    worker_context: manifest_v2.K7ProductionRoleLaunchContextV2,
    business_context: manifest_v2.K7ProductionRoleLaunchContextV2,
    output_parent_fd: int,
) -> K7BrokerResourceSessionV2:
    """Prepare one unlaunched, role-bound broker resource session."""

    if (
        type(manifest) is not manifest_v2.K7ProductionRoleManifestV2
        or type(worker_context)
        is not manifest_v2.K7ProductionRoleLaunchContextV2
        or type(business_context)
        is not manifest_v2.K7ProductionRoleLaunchContextV2
        or type(output_parent_fd) is not int
        or output_parent_fd < 0
    ):
        _fail("broker resource preparation received mistyped authorities")
    manifest.assert_current()
    if (
        worker_context.manifest is not manifest
        or business_context.manifest is not manifest
        or worker_context.role is not manifest_v2.K7ProductionBrokerRoleV2.WORKER
        or business_context.role
        is not manifest_v2.K7ProductionBrokerRoleV2.BUSINESS
        or worker_context.binding is not business_context.binding
        or worker_context.binding.request_id != manifest.request_id
        or worker_context.binding.route_identity_id != manifest.route_identity_id
    ):
        _fail("broker resource preparation crossed manifest/context binding")
    parent_flags = _fd_flags(output_parent_fd)
    parent_status = os.fstat(output_parent_fd)
    if (
        not stat.S_ISDIR(parent_status.st_mode)
        or parent_flags & getattr(os, "O_PATH", 0)
        or os.get_inheritable(output_parent_fd)
    ):
        _fail("broker output parent must be a usable CLOEXEC directory")

    key = (
        os.getpid(),
        manifest.manifest_id,
        worker_context.context_id,
        business_context.context_id,
    )
    descriptors: dict[str, int] = {}
    output_name = _output_directory_name(manifest, worker_context, business_context)
    output_created = False
    parent_owned = -1
    guardian: K7BrokerResourceGuardianV2 | None = None
    with _PREPARATION_LOCK:
        if key in _CONSUMED_CONTEXTS:
            _fail("broker role contexts already own one resource session")
        try:
            parent_owned = _duplicate_cloexec(output_parent_fd)
            descriptors["worker_broker_channel"], descriptors[
                "worker_child_channel"
            ] = _new_socket_pair()
            descriptors["business_broker_channel"], descriptors[
                "business_child_channel"
            ] = _new_socket_pair()
            descriptors["business_result_readwrite"] = (
                runtime_v1._new_sealable_memfd(  # noqa: SLF001
                    "acfqp-k7-broker-v2-result"
                )
            )
            os.fchmod(descriptors["business_result_readwrite"], 0o600)
            descriptors["worker_result_readonly"] = _open_readonly_memfd_view(
                descriptors["business_result_readwrite"]
            )
            descriptors["broker_result_readonly"] = _open_readonly_memfd_view(
                descriptors["business_result_readwrite"]
            )
            (
                descriptors["broker_output_directory"],
                descriptors["worker_output_directory"],
                output_status,
            ) = _open_output_directory(parent_owned, output_name)
            output_created = True
            if len(descriptors) != len(set(descriptors.values())):
                _fail("prepared broker resource descriptor numbers overlap")
            identities = {
                name: _descriptor_identity(fd) for name, fd in descriptors.items()
            }
            guardian = K7BrokerResourceGuardianV2(
                _GUARDIAN_ISSUER,
                descriptors=descriptors,
                identities=identities,
                output_parent_fd=parent_owned,
                output_parent_identity=_descriptor_identity(parent_owned),
                output_name=output_name,
                output_status=output_status,
            )
            binding = worker_context.binding
            worker_bundle = K7BrokerRoleCapabilityBundleV2(
                _BUNDLE_ISSUER,
                manifest_v2.K7ProductionBrokerRoleV2.WORKER,
                manifest.manifest_id,
                worker_context.context_id,
                binding.request_id,
                binding.route_identity_id,
                binding.broker_execution_spec_id,
                binding.session_nonce,
                guardian,
                {
                    "BROKER_CHANNEL": descriptors["worker_child_channel"],
                    "BUSINESS_RESULT_READONLY": descriptors[
                        "worker_result_readonly"
                    ],
                    "OUTPUT_DIRECTORY": descriptors["worker_output_directory"],
                },
                {
                    "BROKER_CHANNEL": identities["worker_child_channel"],
                    "BUSINESS_RESULT_READONLY": identities[
                        "worker_result_readonly"
                    ],
                    "OUTPUT_DIRECTORY": identities["worker_output_directory"],
                },
            )
            business_bundle = K7BrokerRoleCapabilityBundleV2(
                _BUNDLE_ISSUER,
                manifest_v2.K7ProductionBrokerRoleV2.BUSINESS,
                manifest.manifest_id,
                business_context.context_id,
                binding.request_id,
                binding.route_identity_id,
                binding.broker_execution_spec_id,
                binding.session_nonce,
                guardian,
                {
                    "BROKER_CHANNEL": descriptors["business_child_channel"],
                    "BUSINESS_RESULT_WRITABLE": descriptors[
                        "business_result_readwrite"
                    ],
                },
                {
                    "BROKER_CHANNEL": identities["business_child_channel"],
                    "BUSINESS_RESULT_WRITABLE": identities[
                        "business_result_readwrite"
                    ],
                },
            )
            session = K7BrokerResourceSessionV2(
                _SESSION_ISSUER,
                manifest,
                worker_context,
                business_context,
                worker_bundle,
                business_bundle,
                guardian,
                hashlib.sha256(output_name.encode("ascii")).hexdigest(),
            )
            session.assert_current()
            _CONSUMED_CONTEXTS.add(key)
            return session
        except BaseException as error:
            if guardian is not None:
                try:
                    guardian.close()
                except BaseException as cleanup_error:
                    raise V075K7BrokerResourceSessionCleanupV2Error(
                        "broker resource preparation failed with partial cleanup",
                        guardian=guardian,
                    ) from cleanup_error
            else:
                for descriptor in set(descriptors.values()):
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
                if output_created and parent_owned >= 0:
                    try:
                        os.rmdir(output_name, dir_fd=parent_owned)
                    except OSError as cleanup_error:
                        if cleanup_error.errno not in {errno.ENOENT}:
                            raise V075K7BrokerResourceSessionCleanupV2Error(
                                "broker resource preparation left its output directory",
                                guardian=None,
                            ) from cleanup_error
                if parent_owned >= 0:
                    try:
                        os.close(parent_owned)
                    except OSError:
                        pass
            raise error


__all__ = (
    "BROKER_DESCRIPTOR_ROLES",
    "BROKER_RESOURCE_SESSION_PROFILE_V2_DOMAIN",
    "BROKER_RESOURCE_SESSION_V2_DOMAIN",
    "BROKER_ROLE_CAPABILITY_BUNDLE_V2_DOMAIN",
    "BUSINESS_RUNTIME_DESCRIPTOR_ROLES",
    "K7BrokerResourceGuardianV2",
    "K7BrokerRuntimeTransferAuthorityV2",
    "K7BrokerResourceSessionProfileV2",
    "K7BrokerResourceSessionStateV2",
    "K7BrokerResourceSessionV2",
    "K7BrokerRoleCapabilityBundleV2",
    "OUTPUT_DIRECTORY_PREFIX",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "WORKER_RUNTIME_DESCRIPTOR_ROLES",
    "V075K7BrokerResourceSessionCleanupV2Error",
    "V075K7BrokerResourceSessionV2Error",
    "official_v075_k7_broker_resource_session_profile_v2",
    "prepare_v075_k7_broker_resource_session_v2",
)
