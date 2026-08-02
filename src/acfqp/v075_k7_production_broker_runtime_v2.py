"""Joined construction-only runtime for the V0-075 K7 production broker.

This module is the first boundary which consumes the prepared outer cgroup,
the V2 descriptor topology, the two immutable launch records, and the two
pre-exec sandbox authorities in one irreversible lifecycle.  It deliberately
does *not* issue accounting receipts or a CounterRecord.  Its success value is
therefore a typed, nonformal execution envelope only.

The worker currently commits ``operational-output.json``.  That object is a
pre-reap wrapper around the public business result; it is not the registered
eight-role ``BUSINESS_RESULT`` payload.  The distinction is explicit in the
envelope and this runtime never feeds the wrapper to the durable-output fixed
point under a false role.
"""

from __future__ import annotations

import ctypes
from dataclasses import InitVar, dataclass, field
import errno
import fcntl
import hashlib
import os
import platform
import select
import signal
import socket
import stat
import threading
import time
from types import MappingProxyType
from typing import Any, Callable, Mapping, NoReturn

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as atomic_v1
from acfqp import v075_k7_authenticated_broker_channel_v2 as channel_v2
from acfqp import v075_k7_broker_resource_session_v2 as resource_v2
from acfqp import v075_k7_broker_worker_entry_v1 as worker_v1
from acfqp import v075_k7_child_business_bundle_v1 as business_bundle_v1
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_outer_attempt_broker_preparation_v1 as preparation_v1
from acfqp import v075_k7_production_role_launch_authority_v2 as launch_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp import v075_k7_production_role_sandbox_v2 as sandbox_v2
from acfqp import v075_k7_successor_portable_replay_v1 as replay_v1
from acfqp import v075_k7_two_role_broker_probe_v1 as probe_v1
from acfqp.phase3e_ids import (
    V075_K7_PRODUCTION_BROKER_RUNTIME_ENVELOPE_V2_DOMAIN,
    V075_K7_PRODUCTION_BROKER_RUNTIME_PROFILE_V2_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.19"
PROFILE_KEY = "v075_k7_production_broker_runtime_v2"
ROLE_ORDER = ("WORKER", "BUSINESS")
FRAME_ROLE_ORDER = tuple(role.value for role in ipc_v1.FRAME_ROLES)
RUNTIME_PROFILE_DOMAIN = V075_K7_PRODUCTION_BROKER_RUNTIME_PROFILE_V2_DOMAIN
RUNTIME_ENVELOPE_DOMAIN = V075_K7_PRODUCTION_BROKER_RUNTIME_ENVELOPE_V2_DOMAIN
MAX_OUTPUT_BYTES = worker_v1.MAX_OUTPUT_BYTES
PROMOTED_OUTPUT_PREFIX = ".acfqp-k7-runtime-v2-"

_PROFILE_ISSUER = object()
_ENVELOPE_ISSUER = object()
_CONSUMED_LOCK = threading.Lock()
_CONSUMED_SESSIONS: set[tuple[int, str, str]] = set()


class V075K7ProductionBrokerRuntimeV2Error(RuntimeError):
    """The joined runtime failed before a formal accounting boundary."""

    def __init__(
        self,
        message: str,
        *,
        cleanup_complete: bool = False,
        cleanup_authority: Any = None,
        unresolved_roles: tuple[str, ...] = (),
        output_preserved: bool = False,
        promoted_output_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.cleanup_complete = cleanup_complete
        self.cleanup_authority = cleanup_authority
        self.unresolved_roles = unresolved_roles
        self.output_preserved = output_preserved
        self.promoted_output_name = promoted_output_name


class V075K7ProductionBrokerRuntimeCleanupV2Error(
    V075K7ProductionBrokerRuntimeV2Error
):
    """Cleanup remains retryable through retained pidfd/tree/resource OFDs."""


def _fail(message: str) -> NoReturn:
    raise V075K7ProductionBrokerRuntimeV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7ProductionBrokerRuntimeV2Error(
            f"{label} must be one exact content ID"
        ) from error


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in {RUNTIME_PROFILE_DOMAIN, RUNTIME_ENVELOPE_DOMAIN}:
        _fail("production broker runtime used an undeclared local domain")
    return content_id(domain, dict(payload))


def _descriptor_identity(descriptor: int) -> tuple[int, ...]:
    try:
        status = os.fstat(descriptor)
        descriptor_flags = fcntl.fcntl(descriptor, fcntl.F_GETFD)
        open_flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
    except OSError as error:
        raise V075K7ProductionBrokerRuntimeV2Error(
            "production runtime descriptor is unavailable"
        ) from error
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
        status.st_rdev,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
        descriptor_flags,
        open_flags,
    )


def _identity_document(identity: tuple[int, ...]) -> dict[str, int]:
    keys = (
        "device",
        "inode",
        "mode",
        "owner_uid",
        "owner_gid",
        "rdev",
        "byte_count",
        "mtime_ns",
        "ctime_ns",
        "descriptor_flags",
        "open_flags",
    )
    if type(identity) is not tuple or len(identity) != len(keys):
        _fail("production runtime descriptor identity is malformed")
    return dict(zip(keys, identity))


def _formal_locks() -> dict[str, bool]:
    return {
        "shared_resource_receipts_issued": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "actual_projection_proof_issued": False,
        "attempt_terminal_authorized": False,
        "official_execution_allowed": False,
    }


@dataclass(frozen=True, slots=True)
class K7ProductionBrokerRuntimeProfileV2:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("production runtime profile is issuer-owned")
        object.__setattr__(self, "_profile_id", _hash(RUNTIME_PROFILE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_broker_runtime_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "role_order": list(ROLE_ORDER),
            "frame_role_order": list(FRAME_ROLE_ORDER),
            "outer_guardian_lifecycle_lock_required": True,
            "probe_stream_endpoints_irreversibly_superseded": True,
            "native_clone3_into_fixed_sibling_cgroups": True,
            "native_write_ahead_edges_required": True,
            "authenticated_scm_credentials_required": True,
            "direct_pidfd_zero_exit_reap_required": True,
            "same_memory_peak_open_file_description_required": True,
            "success_output_promoted_without_replace": True,
            "success_output_post_reap_sealed_readonly": True,
            "failure_never_deletes_nonempty_output": True,
            "output_role": "PRE_REAP_OPERATIONAL_RESULT",
            "registered_eight_role_business_result_claimed": False,
            "construction_only": True,
            "central_domain_registration_pending": False,
            "formal_locks": _formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _hash(RUNTIME_PROFILE_DOMAIN, self._payload()) != self._profile_id:
            _fail("production runtime profile changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "production_broker_runtime_profile_id": self.profile_id}


_OFFICIAL_PROFILE = K7ProductionBrokerRuntimeProfileV2(_PROFILE_ISSUER)


def official_v075_k7_production_broker_runtime_profile_v2(
) -> K7ProductionBrokerRuntimeProfileV2:
    return _OFFICIAL_PROFILE


@dataclass(frozen=True, slots=True)
class _LaunchOutcomeV2:
    role: str
    pid: int
    pidfd: int
    pidfd_identity: tuple[int, ...]
    native_edge: int
    setup_raw_sha256: str
    setup_raw_byte_count: int


@dataclass(frozen=True, slots=True)
class _BusinessReplayV2:
    bundle_id: str
    raw_sha256: str
    raw_byte_count: int


@dataclass(frozen=True, slots=True)
class _PinnedOutputV2:
    descriptor: int
    identity: tuple[int, ...]
    operational_output_id: str
    raw: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class K7ProductionBrokerRuntimeEnvelopeV2:
    _issuer: InitVar[object]
    prepared_session_id: str
    resource_session_id: str
    manifest_id: str
    worker_launch_authority_id: str
    business_launch_authority_id: str
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1 = field(repr=False)
    role_rows: tuple[Mapping[str, Any], ...]
    frame_observations: tuple[channel_v2.K7AuthenticatedBrokerFrameV2, ...] = field(
        repr=False, compare=False
    )
    transcript: ipc_v1.V075K7OuterAttemptBrokerIPCTranscriptV1 = field(
        repr=False, compare=False
    )
    business_result_id: str
    business_result_sha256: str
    business_result_byte_count: int
    operational_output_id: str
    output_sha256: str
    output_byte_count: int
    output_inode_identity: Mapping[str, int]
    promoted_output_name: str
    final_memory_peak: int
    peak_ofd_identity: Mapping[str, int]
    cgroup_cleanup_complete: bool
    resource_cleanup_complete: bool
    _envelope_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ENVELOPE_ISSUER
            or type(self.binding) is not ipc_v1.K7OuterAttemptBrokerIPCBindingV1
            or type(self.frame_observations) is not tuple
            or len(self.frame_observations) != 5
            or any(
                type(item) is not channel_v2.K7AuthenticatedBrokerFrameV2
                for item in self.frame_observations
            )
            or type(self.transcript) is not ipc_v1.V075K7OuterAttemptBrokerIPCTranscriptV1
        ):
            _fail("production runtime envelope is caller-minted or incomplete")
        for value, label in (
            (self.prepared_session_id, "prepared session"),
            (self.resource_session_id, "resource session"),
            (self.manifest_id, "manifest"),
            (self.worker_launch_authority_id, "worker launch authority"),
            (self.business_launch_authority_id, "business launch authority"),
            (self.business_result_id, "business result"),
            (self.operational_output_id, "operational output"),
        ):
            _cid(value, label)
        roles = tuple(row.get("role") for row in self.role_rows)
        frame_roles = tuple(item.frame.role.value for item in self.frame_observations)
        if (
            type(self.role_rows) is not tuple
            or roles != ROLE_ORDER
            or any(
                row.get("native_write_ahead_edge") != 1
                or row.get("direct_pidfd_reaped") is not True
                or row.get("exit_code") != 0
                for row in self.role_rows
            )
            or frame_roles != FRAME_ROLE_ORDER
            or tuple(item.frame.frame_id for item in self.frame_observations)
            != tuple(frame.frame_id for frame in self.transcript.frames)
            or self.transcript.binding != self.binding
            or type(self.output_byte_count) is not int
            or not 0 < self.output_byte_count <= MAX_OUTPUT_BYTES
            or self.output_sha256
            != self.frame_observations[3].frame.payload["output_sha256"]
            or self.output_byte_count
            != self.frame_observations[3].frame.payload["output_byte_count"]
            or type(self.business_result_byte_count) is not int
            or self.business_result_byte_count <= 0
            or type(self.final_memory_peak) is not int
            or self.final_memory_peak < 0
            or type(self.promoted_output_name) is not str
            or not self.promoted_output_name.startswith(PROMOTED_OUTPUT_PREFIX)
            or not isinstance(self.output_inode_identity, Mapping)
            or type(self.output_inode_identity.get("mode")) is not int
            or stat.S_IMODE(self.output_inode_identity["mode"]) != 0o400
            or self.cgroup_cleanup_complete is not True
            or self.resource_cleanup_complete is not True
        ):
            _fail("production runtime success envelope facts are inconsistent")
        object.__setattr__(
            self,
            "role_rows",
            tuple(MappingProxyType(dict(row)) for row in self.role_rows),
        )
        object.__setattr__(
            self,
            "output_inode_identity",
            MappingProxyType(dict(self.output_inode_identity)),
        )
        object.__setattr__(
            self,
            "peak_ofd_identity",
            MappingProxyType(dict(self.peak_ofd_identity)),
        )
        object.__setattr__(
            self,
            "_envelope_id",
            _hash(RUNTIME_ENVELOPE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_broker_runtime_envelope.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_broker_runtime_profile_id": _OFFICIAL_PROFILE.profile_id,
            "prepared_broker_session_id": self.prepared_session_id,
            "broker_resource_session_id": self.resource_session_id,
            "production_role_manifest_id": self.manifest_id,
            "worker_launch_authority_id": self.worker_launch_authority_id,
            "business_launch_authority_id": self.business_launch_authority_id,
            **self.binding.to_document(),
            "roles": [dict(row) for row in self.role_rows],
            "authenticated_frame_observation_ids": [
                item.observation_id for item in self.frame_observations
            ],
            "outer_attempt_broker_ipc_transcript_id": self.transcript.transcript_id,
            "frame_roles": list(FRAME_ROLE_ORDER),
            "business_result_id": self.business_result_id,
            "business_result_sha256": self.business_result_sha256,
            "business_result_byte_count": self.business_result_byte_count,
            "sealed_business_result_replay_completed": True,
            "operational_output_id": self.operational_output_id,
            "output_sha256": self.output_sha256,
            "output_byte_count": self.output_byte_count,
            "output_inode_identity": dict(self.output_inode_identity),
            "promoted_output_name": self.promoted_output_name,
            "promoted_output_no_replace": True,
            "promoted_output_parent_fsync_completed": True,
            "output_post_reap_write_bits_removed": True,
            "output_role": "PRE_REAP_OPERATIONAL_RESULT",
            "registered_eight_role_business_result_claimed": False,
            "durable_output_fixed_point_joined": False,
            "final_memory_peak_same_retained_ofd": self.final_memory_peak,
            "peak_ofd_identity": dict(self.peak_ofd_identity),
            "cgroup_cleanup_complete": self.cgroup_cleanup_complete,
            "resource_cleanup_complete": self.resource_cleanup_complete,
            "direct_child_count": 2,
            "authenticated_frame_count": 5,
            "process_launches_raw": 2,
            "receipts": None,
            "counter_records": None,
            "construction_only": True,
            "nonformal": True,
            "central_domain_registration_pending": False,
            "formal_locks": _formal_locks(),
        }

    @property
    def envelope_id(self) -> str:
        if _hash(RUNTIME_ENVELOPE_DOMAIN, self._payload()) != self._envelope_id:
            _fail("production runtime envelope changed")
        return self._envelope_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "production_broker_runtime_envelope_id": self.envelope_id}


class _RoleNativeCellsV2:
    __slots__ = ("clone_result", "pidfd", "edge", "setup_read")

    def __init__(self) -> None:
        self.clone_result = ctypes.c_long(0)
        self.pidfd = ctypes.c_int(-1)
        self.edge = ctypes.c_uint64(0)
        self.setup_read = ctypes.c_int(-1)


def _remaining_milliseconds(deadline_ns: int) -> int:
    remaining = (deadline_ns - time.monotonic_ns() + 999_999) // 1_000_000
    if remaining <= 0:
        _fail("production broker deadline expired")
    return int(remaining)


def _wait_readable(descriptor: int, deadline_ns: int, label: str) -> None:
    poller = select.poll()
    poller.register(descriptor, select.POLLIN | select.POLLHUP | select.POLLERR)
    while True:
        remaining = _remaining_milliseconds(deadline_ns)
        events = poller.poll(min(remaining, 100))
        if events:
            return
        if time.monotonic_ns() >= deadline_ns:
            _fail(f"production broker timed out waiting for {label}")


def _wait_writable(descriptor: int, deadline_ns: int, label: str) -> None:
    poller = select.poll()
    poller.register(descriptor, select.POLLOUT | select.POLLHUP | select.POLLERR)
    while True:
        remaining = _remaining_milliseconds(deadline_ns)
        events = poller.poll(min(remaining, 100))
        if events:
            return
        if time.monotonic_ns() >= deadline_ns:
            _fail(f"production broker timed out waiting for {label}")


def _read_setup_status_until_v2(status_fd: int, deadline_ns: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        _wait_readable(status_fd, deadline_ns, "native setup status EOF")
        while True:
            try:
                chunk = os.read(status_fd, 33 - total)
            except BlockingIOError:
                break
            except InterruptedError:
                continue
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
            total += len(chunk)
            if total > 32:
                _fail("native setup status exceeded two fixed records")


def _reconstruct_request_replay_v2(
    worker_authority: launch_v2.K7ProductionRoleLaunchAuthorityV2,
    business_authority: launch_v2.K7ProductionRoleLaunchAuthorityV2,
) -> replay_v1.V075K7SuccessorPortableRequestReplayV1:
    worker_rows = dict(worker_authority._public_expected)  # noqa: SLF001
    business_rows = dict(business_authority._public_expected)  # noqa: SLF001
    common = (
        "SOURCE_ARCHIVE",
        "TRANSPORT_PROFILE",
        "LIFECYCLE_PROFILE",
        "SUCCESSOR_PROFILE",
        "SUCCESSOR_REQUEST",
        "ROLE_MANIFEST_V2",
    )
    if any(worker_rows.get(name) != business_rows.get(name) for name in common):
        _fail("worker/business launch authorities crossed public replay inputs")
    closure = replay_v1.reconstruct_v075_k7_successor_portable_profile_closure_v1(
        source_archive_raw=worker_rows["SOURCE_ARCHIVE"],
        transport_profile_raw=worker_rows["TRANSPORT_PROFILE"],
        lifecycle_profile_raw=worker_rows["LIFECYCLE_PROFILE"],
        successor_profile_raw=worker_rows["SUCCESSOR_PROFILE"],
    )
    return replay_v1.replay_v075_k7_successor_request_bytes_portable_v1(
        raw=worker_rows["SUCCESSOR_REQUEST"],
        profile_closure=closure,
    )


def _launch_production_role_v2(
    *,
    role: str,
    leaf_fd: int,
    launch_record: launch_v2.K7ProductionRoleNativeLaunchRecordV2,
    sandbox_material: sandbox_v2.K7ProductionRolePreexecSandboxMaterialV2,
    native_cells: _RoleNativeCellsV2,
    deadline_ns: int,
) -> _LaunchOutcomeV2:
    if role not in ROLE_ORDER:
        _fail("production native launcher received an unknown role")
    executable_fd, sealed_fds, capability_fds, argv, environment_rows = launch_record
    inherited = (executable_fd, *sealed_fds, *capability_fds)
    setup_read = setup_write = null_fd = -1
    try:
        sandbox_material.assert_current()
        if sandbox_material.executable_fd != executable_fd:
            _fail("sandbox and launch record crossed executable FDs")
        setup_read, setup_write = os.pipe2(os.O_CLOEXEC)
        native_cells.setup_read.value = setup_read
        os.set_blocking(setup_read, False)
        null_fd = os.open("/dev/null", os.O_RDWR | os.O_CLOEXEC)
        landlock_fd = sandbox_material.preexec_landlock_ruleset_fd
        descriptors = (
            *inherited,
            setup_read,
            setup_write,
            null_fd,
            landlock_fd,
            leaf_fd,
        )
        if min(descriptors) < 3 or len(set(descriptors)) != len(descriptors):
            _fail(f"{role} production launch descriptor roles overlap")
        for descriptor in inherited:
            os.set_inheritable(descriptor, True)
        identities = tuple(atomic_v1._descriptor_identity(fd) for fd in descriptors)  # noqa: SLF001
        encoded_argv = tuple(value.encode("utf-8") for value in argv)
        encoded_env = tuple(
            f"{key}={value}".encode("utf-8") for key, value in environment_rows
        )
        argv_array = (ctypes.c_char_p * (len(encoded_argv) + 1))(
            *encoded_argv, None
        )
        env_array = (ctypes.c_char_p * (len(encoded_env) + 1))(
            *encoded_env, None
        )
        clone_args = atomic_v1.CloneArgsV1(
            flags=atomic_v1.REQUIRED_CLONE_FLAGS,
            pidfd=ctypes.addressof(native_cells.pidfd),
            exit_signal=signal.SIGCHLD,
            cgroup=leaf_fd,
        )
        launch_args = probe_v1._NativeTwoRoleLaunchArgsV1(  # noqa: SLF001
            ctypes.addressof(clone_args),
            executable_fd,
            null_fd,
            ctypes.cast(argv_array, ctypes.c_void_p).value,
            ctypes.cast(env_array, ctypes.c_void_p).value,
            os.getpid(),
            landlock_fd,
            sandbox_material.preexec_seccomp_program_address,
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
            _fail(f"{role} production launch critical section is not single-threaded")
        returned = int(probe_v1._native_two_role_trampoline_v1()(ctypes.byref(launch_args)))  # noqa: SLF001
        clone_result = int(native_cells.clone_result.value)
        pidfd = int(native_cells.pidfd.value)
        edge = int(native_cells.edge.value)
        if returned != clone_result:
            _fail(f"{role} native return crossed its write-ahead result cell")
        if clone_result <= 0 or edge != 1:
            _fail(f"{role} clone3 did not publish one positive write-ahead edge")
        if not probe_v1._pidfd_matches_child_v1(pidfd, clone_result):  # noqa: SLF001
            _fail(f"{role} positive native edge lacks its matching pidfd")
        # The parent copy must close before waiting for EOF.  The child copy
        # is CLOEXEC, so EOF now proves either successful exec or child exit.
        os.close(setup_write)
        setup_write = -1
        setup_raw = _read_setup_status_until_v2(setup_read, deadline_ns)
        os.close(setup_read)
        setup_read = -1
        native_cells.setup_read.value = -1
        setup_ok, _stage, _error = atomic_v1._parse_setup_status(setup_raw)  # noqa: SLF001
        if not setup_ok:
            _fail(f"{role} native pre-exec setup or execveat failed")
        return _LaunchOutcomeV2(
            role,
            clone_result,
            pidfd,
            _descriptor_identity(pidfd),
            edge,
            hashlib.sha256(setup_raw).hexdigest(),
            len(setup_raw),
        )
    finally:
        if setup_read >= 0:
            try:
                os.close(setup_read)
            except OSError:
                pass
            native_cells.setup_read.value = -1
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


def _receive_authenticated_v2(
    *,
    endpoint: socket.socket,
    launch: _LaunchOutcomeV2,
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    role: ipc_v1.K7OuterAttemptBrokerFrameRoleV1,
    deadline_ns: int,
) -> channel_v2.K7AuthenticatedBrokerFrameV2:
    _wait_readable(endpoint.fileno(), deadline_ns, role.value)
    return channel_v2.receive_v075_k7_authenticated_broker_frame_v2(
        endpoint=endpoint,
        expected_pid=launch.pid,
        expected_pidfd=launch.pidfd,
        expected_binding=binding,
        expected_role=role,
    )


def _send_exact_packet_and_half_close_v2(
    endpoint: socket.socket,
    raw: bytes,
    deadline_ns: int,
) -> None:
    try:
        flags = getattr(socket, "MSG_NOSIGNAL", 0) | getattr(
            socket, "MSG_DONTWAIT", 0
        )
        while True:
            try:
                sent = endpoint.send(raw, flags)
            except (BlockingIOError, InterruptedError):
                _wait_writable(
                    endpoint.fileno(), deadline_ns, "business result relay"
                )
                continue
            if sent != len(raw):
                _fail("business result relay was not one exact packet")
            break
        endpoint.shutdown(socket.SHUT_WR)
    except OSError as error:
        raise V075K7ProductionBrokerRuntimeV2Error(
            "business result relay or SHUT_WR failed"
        ) from error


def _read_business_result_v2(
    *,
    descriptor: int,
    frame: channel_v2.K7AuthenticatedBrokerFrameV2,
    request_replay: replay_v1.V075K7SuccessorPortableRequestReplayV1,
) -> _BusinessReplayV2:
    raw = worker_v1._read_sealed_business_result(descriptor)  # noqa: SLF001
    try:
        bundle = business_bundle_v1.verify_v075_k7_child_business_bundle_public_bytes_v1(
            raw=raw,
            expected_request_replay=request_replay,
        )
    except Exception as error:
        raise V075K7ProductionBrokerRuntimeV2Error(
            "broker sealed business result failed public replay"
        ) from error
    if frame.frame.payload["business_result_id"] != bundle.bundle_id:
        _fail("authenticated BUSINESS_RESULT crossed its sealed public bundle")
    return _BusinessReplayV2(
        bundle.bundle_id,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )


def _wait_zero_exit_v2(launch: _LaunchOutcomeV2, deadline_ns: int) -> None:
    waited = atomic_v1._wait_pidfd(  # noqa: SLF001
        launch.pidfd,
        grace_milliseconds=min(
            _remaining_milliseconds(deadline_ns),
            atomic_v1.MAX_REAP_GRACE_MILLISECONDS,
        ),
    )
    if (
        waited.si_pid != launch.pid
        or waited.si_code != os.CLD_EXITED
        or int(waited.si_status) != 0
    ):
        _fail(f"{launch.role} direct child did not exit cleanly with status zero")


def _read_exact_file(descriptor: int, size: int) -> bytes:
    chunks: list[bytes] = []
    offset = 0
    while offset < size:
        chunk = os.pread(descriptor, min(1024 * 1024, size - offset), offset)
        if not chunk:
            _fail("pinned operational output ended before its frozen extent")
        chunks.append(chunk)
        offset += len(chunk)
    return b"".join(chunks)


def _reread_operational_output_v2(
    *,
    output_directory_fd: int,
    request_replay: replay_v1.V075K7SuccessorPortableRequestReplayV1,
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    parent_output: channel_v2.K7AuthenticatedBrokerFrameV2,
) -> _PinnedOutputV2:
    try:
        entries = tuple(sorted(os.listdir(output_directory_fd)))
    except OSError as error:
        raise V075K7ProductionBrokerRuntimeV2Error(
            "broker output directory cannot be enumerated after reap"
        ) from error
    if entries != (worker_v1.OUTPUT_NAME,):
        _fail("post-reap output directory lacks one exact operational output")
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(worker_v1.OUTPUT_NAME, flags, dir_fd=output_directory_fd)
    try:
        before = _descriptor_identity(descriptor)
        if (
            not stat.S_ISREG(before[2])
            or before[6] <= 0
            or before[6] > MAX_OUTPUT_BYTES
            or stat.S_IMODE(before[2]) != 0o600
        ):
            _fail("pinned operational output inode is invalid")
        raw = _read_exact_file(descriptor, before[6])
        if _descriptor_identity(descriptor) != before:
            _fail("pinned operational output changed during readback")
        named = os.stat(
            worker_v1.OUTPUT_NAME,
            dir_fd=output_directory_fd,
            follow_symlinks=False,
        )
        if (named.st_dev, named.st_ino) != before[:2]:
            _fail("operational output name crossed its pinned inode")
        replayed = worker_v1.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=raw,
            expected_request_replay=request_replay,
            expected_binding=binding,
        )
        digest = hashlib.sha256(raw).hexdigest()
        payload = parent_output.frame.payload
        if (
            payload["output_byte_count"] != len(raw)
            or payload["output_sha256"] != digest
        ):
            _fail("authenticated PARENT_OUTPUT crossed durable output bytes")
        # Both direct children have already been reaped.  Remove the worker's
        # write bits before the envelope can expose these bytes as immutable.
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
        os.fsync(output_directory_fd)
        sealed = _descriptor_identity(descriptor)
        sealed_named = os.stat(
            worker_v1.OUTPUT_NAME,
            dir_fd=output_directory_fd,
            follow_symlinks=False,
        )
        stable_indices = (0, 1, 3, 4, 5, 6, 7, 9, 10)
        if (
            tuple(sealed[index] for index in stable_indices)
            != tuple(before[index] for index in stable_indices)
            or stat.S_IMODE(sealed[2]) != 0o400
            or (sealed_named.st_dev, sealed_named.st_ino) != sealed[:2]
            or stat.S_IMODE(sealed_named.st_mode) != 0o400
            or _read_exact_file(descriptor, sealed[6]) != raw
        ):
            _fail("post-reap operational output sealing changed its bytes or inode")
        return _PinnedOutputV2(descriptor, sealed, replayed.output_id, raw)
    except BaseException:
        os.close(descriptor)
        raise


def _rename_noreplace(
    *, source_directory_fd: int, source_name: str, target_directory_fd: int,
    target_name: str,
) -> None:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (OSError, AttributeError) as error:
        raise V075K7ProductionBrokerRuntimeV2Error(
            "renameat2(RENAME_NOREPLACE) is unavailable"
        ) from error
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    if renameat2(
        source_directory_fd,
        source_name.encode("ascii"),
        target_directory_fd,
        target_name.encode("ascii"),
        worker_v1.RENAME_NOREPLACE,
    ) != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), target_name)


def _promote_output_v2(
    *,
    transfer: resource_v2.K7BrokerRuntimeTransferAuthorityV2,
    pinned: _PinnedOutputV2,
    resource_session_id: str,
    on_renamed: Callable[[str], None] | None = None,
) -> str:
    guardian = transfer._guardian  # noqa: SLF001 - runtime owns transfer
    output_directory_fd = transfer.broker_descriptor("OUTPUT_DIRECTORY")
    parent_fd = guardian._output_parent_fd  # noqa: SLF001
    target_name = f"{PROMOTED_OUTPUT_PREFIX}{resource_session_id}.json"
    _rename_noreplace(
        source_directory_fd=output_directory_fd,
        source_name=worker_v1.OUTPUT_NAME,
        target_directory_fd=parent_fd,
        target_name=target_name,
    )
    if on_renamed is not None:
        on_renamed(target_name)
    named = os.stat(target_name, dir_fd=parent_fd, follow_symlinks=False)
    if (named.st_dev, named.st_ino) != pinned.identity[:2]:
        _fail("promoted operational output crossed its pinned inode")
    after = _descriptor_identity(pinned.descriptor)
    # rename(2) legitimately advances ctime.  Every other inode/extent and
    # open-description field, plus a second byte replay, must remain exact.
    stable_indices = (0, 1, 2, 3, 4, 5, 6, 7, 9, 10)
    if (
        tuple(after[index] for index in stable_indices)
        != tuple(pinned.identity[index] for index in stable_indices)
        or _read_exact_file(pinned.descriptor, pinned.identity[6]) != pinned.raw
    ):
        _fail("promoted operational output changed after no-replace rename")
    os.fsync(output_directory_fd)
    os.fsync(parent_fd)
    return target_name


def _output_entries(resource_owner: Any) -> tuple[str, ...]:
    try:
        descriptor = (
            resource_owner.broker_descriptor("OUTPUT_DIRECTORY")
            if type(resource_owner) is resource_v2.K7BrokerRuntimeTransferAuthorityV2
            else resource_owner.broker_descriptor("OUTPUT_DIRECTORY")
        )
        return tuple(sorted(os.listdir(descriptor)))
    except BaseException:
        return ("<UNREADABLE>",)


class K7ProductionBrokerRuntimeCleanupAuthorityV2:
    """Retry authority retaining every unresolved direct-child/resource OFD."""

    def __init__(self, *, guardian: Any, resource_session: Any) -> None:
        self._owner_pid = os.getpid()
        self._guardian = guardian
        self._resource_session = resource_session
        self._transfer: resource_v2.K7BrokerRuntimeTransferAuthorityV2 | None = None
        self._native_cells = {role: _RoleNativeCellsV2() for role in ROLE_ORDER}
        self._launches: dict[str, _LaunchOutcomeV2] = {}
        self._reaped = {role: False for role in ROLE_ORDER}
        self._launch_owned_fds: set[int] = set()
        self._sandbox_authorities: list[Any] = []
        self._sandbox_materials: list[Any] = []
        self._broker_endpoints: list[socket.socket] = []
        self._pinned_output_fd = -1
        self._promoted_output_name: str | None = None
        self._cgroup_closed = False
        self._resource_closed = False
        self._closed = False

    @property
    def unresolved_roles(self) -> tuple[str, ...]:
        self._refresh_native()
        return tuple(
            role for role in ROLE_ORDER
            if self._launch_pid(role) > 0 and not self._reaped[role]
        )

    @property
    def output_preserved(self) -> bool:
        owner = self._transfer if self._transfer is not None else self._resource_session
        if bool(_output_entries(owner)):
            return True
        if self._promoted_output_name is None:
            return False
        if self._resource_closed:
            return True
        try:
            parent_fd = owner._guardian._output_parent_fd  # noqa: SLF001
            os.stat(
                self._promoted_output_name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
            return True
        except (AttributeError, OSError):
            return False

    @property
    def promoted_output_name(self) -> str | None:
        return self._promoted_output_name

    def _record_promoted_output(self, target_name: str) -> None:
        if self._promoted_output_name is not None:
            _fail("production output promotion was recorded twice")
        self._promoted_output_name = target_name

    def _take_pinned_output(self, pinned: _PinnedOutputV2) -> None:
        if (
            type(pinned) is not _PinnedOutputV2
            or pinned.descriptor < 3
            or self._pinned_output_fd >= 0
            or _descriptor_identity(pinned.descriptor) != pinned.identity
        ):
            _fail("production pinned output ownership transfer is invalid")
        self._pinned_output_fd = pinned.descriptor

    def _launch_pid(self, role: str) -> int:
        launch = self._launches.get(role)
        if launch is not None:
            return launch.pid
        return int(self._native_cells[role].clone_result.value)

    def _launch_pidfd(self, role: str) -> int:
        launch = self._launches.get(role)
        if launch is not None:
            return launch.pidfd
        return int(self._native_cells[role].pidfd.value)

    def _refresh_native(self) -> None:
        for role in ROLE_ORDER:
            if self._reaped[role] or role in self._launches:
                continue
            pid = int(self._native_cells[role].clone_result.value)
            pidfd = int(self._native_cells[role].pidfd.value)
            edge = int(self._native_cells[role].edge.value)
            if pid > 0 and edge == 1 and probe_v1._pidfd_matches_child_v1(pidfd, pid):  # noqa: SLF001
                self._launches[role] = _LaunchOutcomeV2(
                    role, pid, pidfd, _descriptor_identity(pidfd), edge, "0" * 64, 0
                )

    def _retire_launch_resources(self) -> None:
        for endpoint in self._broker_endpoints:
            try:
                endpoint.close()
            except OSError:
                pass
        self._broker_endpoints.clear()
        for material in self._sandbox_materials:
            try:
                material.close()
            except BaseException:
                pass
        self._sandbox_materials.clear()
        for authority in self._sandbox_authorities:
            try:
                authority.close()
            except BaseException:
                pass
        self._sandbox_authorities.clear()
        for descriptor in tuple(self._launch_owned_fds):
            try:
                os.close(descriptor)
            except OSError:
                pass
        self._launch_owned_fds.clear()
        if self._pinned_output_fd >= 0:
            try:
                os.close(self._pinned_output_fd)
            except OSError:
                pass
            self._pinned_output_fd = -1

    def _cleanup_locked(self) -> None:
        self._refresh_native()
        numbers = atomic_v1._SYSCALLS.get(platform.machine().lower())  # noqa: SLF001
        for role in self.unresolved_roles:
            pidfd = self._launch_pidfd(role)
            try:
                if numbers is not None and probe_v1._pidfd_matches_child_v1(  # noqa: SLF001
                    pidfd, self._launch_pid(role)
                ):
                    atomic_v1._send_pidfd_signal(numbers, pidfd, signal.SIGKILL)  # noqa: SLF001
            except BaseException:
                pass
        try:
            probe_v1._ancestor_kill(self._guardian)  # noqa: SLF001
        except BaseException:
            pass
        for role in self.unresolved_roles:
            pid = self._launch_pid(role)
            pidfd = self._launch_pidfd(role)
            try:
                if probe_v1._pidfd_matches_child_v1(pidfd, pid):  # noqa: SLF001
                    atomic_v1._wait_pidfd(pidfd)  # noqa: SLF001
                else:
                    atomic_v1._kill_and_reap_direct_child(pid)  # noqa: SLF001
                self._reaped[role] = True
            except BaseException:
                pass
        self._retire_launch_resources()
        unresolved = self.unresolved_roles
        if unresolved:
            raise V075K7ProductionBrokerRuntimeCleanupV2Error(
                "production broker cleanup retains unreaped direct children",
                cleanup_complete=False,
                cleanup_authority=self,
                unresolved_roles=unresolved,
                output_preserved=self.output_preserved,
                promoted_output_name=self._promoted_output_name,
            )
        for role, launch in tuple(self._launches.items()):
            try:
                os.close(launch.pidfd)
            except OSError:
                pass
            self._native_cells[role].pidfd.value = -1
        if not self._cgroup_closed:
            self._guardian._close_prelaunch_locked()  # noqa: SLF001
            self._cgroup_closed = True
        owner = self._transfer if self._transfer is not None else self._resource_session
        entries = _output_entries(owner)
        if entries:
            raise V075K7ProductionBrokerRuntimeCleanupV2Error(
                "production broker failure preserved a nonempty output directory",
                cleanup_complete=False,
                cleanup_authority=self,
                unresolved_roles=(),
                output_preserved=True,
                promoted_output_name=self._promoted_output_name,
            )
        if not self._resource_closed:
            owner.close()
            self._resource_closed = True
        self._closed = True
        if getattr(self._guardian, "_production_broker_runtime_cleanup_authority", None) is self:
            self._guardian._production_broker_runtime_cleanup_authority = None

    def retry_cleanup(self) -> None:
        if os.getpid() != self._owner_pid or self._closed:
            _fail("production broker cleanup authority is stale or closed")
        with self._guardian._lifecycle_lock:  # noqa: SLF001
            self._cleanup_locked()

    def preserved_output_directory_fd(self) -> int:
        if os.getpid() != self._owner_pid or self._closed or not self.output_preserved:
            _fail("no preserved production output is available")
        owner = self._transfer if self._transfer is not None else self._resource_session
        return owner.broker_descriptor("OUTPUT_DIRECTORY")

    def __reduce__(self):
        raise TypeError("production broker cleanup authority is process-local")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("production broker cleanup authority is process-local")


def _assert_joined_inputs_v2(
    *,
    prepared_session: preparation_v1.K7OuterAttemptPreparedBrokerSessionV1,
    resource_session: resource_v2.K7BrokerResourceSessionV2,
    worker_launch_authority: launch_v2.K7ProductionRoleLaunchAuthorityV2,
    business_launch_authority: launch_v2.K7ProductionRoleLaunchAuthorityV2,
    worker_sandbox_authority: sandbox_v2.K7ProductionRoleSandboxAuthorityV2,
    business_sandbox_authority: sandbox_v2.K7ProductionRoleSandboxAuthorityV2,
) -> None:
    if (
        type(prepared_session) is not preparation_v1.K7OuterAttemptPreparedBrokerSessionV1
        or type(resource_session) is not resource_v2.K7BrokerResourceSessionV2
        or type(worker_launch_authority) is not launch_v2.K7ProductionRoleLaunchAuthorityV2
        or type(business_launch_authority) is not launch_v2.K7ProductionRoleLaunchAuthorityV2
        or type(worker_sandbox_authority) is not sandbox_v2.K7ProductionRoleSandboxAuthorityV2
        or type(business_sandbox_authority) is not sandbox_v2.K7ProductionRoleSandboxAuthorityV2
    ):
        _fail("production broker runtime requires six exact issuer-owned inputs")
    binding = prepared_session.binding
    if (
        resource_session.worker_context.binding is not binding
        or resource_session.business_context.binding is not binding
        or binding.broker_execution_spec_id != prepared_session.execution_spec.spec_id
        or resource_session.worker_context is not worker_launch_authority._launch_context  # noqa: SLF001
        or resource_session.business_context is not business_launch_authority._launch_context  # noqa: SLF001
        or worker_launch_authority.role is not manifest_v2.K7ProductionBrokerRoleV2.WORKER
        or business_launch_authority.role is not manifest_v2.K7ProductionBrokerRoleV2.BUSINESS
        or worker_sandbox_authority.role is not sandbox_v2.K7ProductionSandboxRoleV2.WORKER
        or business_sandbox_authority.role is not sandbox_v2.K7ProductionSandboxRoleV2.BUSINESS
        or worker_sandbox_authority.executable_fd != worker_launch_authority._executable_fd  # noqa: SLF001
        or business_sandbox_authority.executable_fd != business_launch_authority._executable_fd  # noqa: SLF001
        or worker_sandbox_authority.output_directory_fd
        != resource_session.worker_capabilities.descriptor("OUTPUT_DIRECTORY")
        or business_sandbox_authority.output_directory_fd is not None
    ):
        _fail("production broker runtime authorities crossed role/session identities")


def run_v075_k7_production_broker_runtime_v2(
    *,
    prepared_session: preparation_v1.K7OuterAttemptPreparedBrokerSessionV1,
    resource_session: resource_v2.K7BrokerResourceSessionV2,
    worker_launch_authority: launch_v2.K7ProductionRoleLaunchAuthorityV2,
    business_launch_authority: launch_v2.K7ProductionRoleLaunchAuthorityV2,
    worker_sandbox_authority: sandbox_v2.K7ProductionRoleSandboxAuthorityV2,
    business_sandbox_authority: sandbox_v2.K7ProductionRoleSandboxAuthorityV2,
    deadline_milliseconds: int,
) -> K7ProductionBrokerRuntimeEnvelopeV2:
    """Consume and execute one exact two-role production broker attempt."""

    _assert_joined_inputs_v2(
        prepared_session=prepared_session,
        resource_session=resource_session,
        worker_launch_authority=worker_launch_authority,
        business_launch_authority=business_launch_authority,
        worker_sandbox_authority=worker_sandbox_authority,
        business_sandbox_authority=business_sandbox_authority,
    )
    if (
        type(deadline_milliseconds) is not int
        or not 1 <= deadline_milliseconds <= atomic_v1.MAX_DEADLINE_MILLISECONDS
    ):
        _fail("production broker deadline is outside its frozen positive bound")
    capability = atomic_v1.probe_v075_k7_atomic_pidfd_capability_v1()
    if not capability.admitted:
        _fail("production broker native clone3/pidfd capability is not admitted")

    guardian = prepared_session.guardian
    cleanup = K7ProductionBrokerRuntimeCleanupAuthorityV2(
        guardian=guardian,
        resource_session=resource_session,
    )
    cleanup._sandbox_authorities.extend(  # noqa: SLF001
        (worker_sandbox_authority, business_sandbox_authority)
    )
    original_error: BaseException | None = None
    deadline_ns = time.monotonic_ns() + deadline_milliseconds * 1_000_000
    previous_mask: set[signal.Signals] | None = None
    promoted_name: str | None = None
    pinned: _PinnedOutputV2 | None = None
    transfer: resource_v2.K7BrokerRuntimeTransferAuthorityV2 | None = None
    launches: dict[str, _LaunchOutcomeV2] = {}
    observations: list[channel_v2.K7AuthenticatedBrokerFrameV2] = []
    transcript: ipc_v1.V075K7OuterAttemptBrokerIPCTranscriptV1 | None = None
    business_replay: _BusinessReplayV2 | None = None
    final_peak: int | None = None
    peak_identity: tuple[int, ...] | None = None
    worker_authority_id = business_authority_id = ""
    request_replay: replay_v1.V075K7SuccessorPortableRequestReplayV1 | None = None
    launch_records: dict[str, launch_v2.K7ProductionRoleNativeLaunchRecordV2] = {}
    materials: dict[str, sandbox_v2.K7ProductionRolePreexecSandboxMaterialV2] = {}
    prepared_session_id = ""
    resource_session_id = ""
    manifest_id = ""

    with guardian._lifecycle_lock:  # noqa: SLF001 - sole outer lifecycle lock
        try:
            guardian._check()  # noqa: SLF001
            if getattr(guardian, "_production_broker_runtime_cleanup_authority", None) is not None:
                _fail("prepared broker already has one production runtime owner")
            probe_v1._revalidate_prepared_session_v1(  # noqa: SLF001
                prepared_session,
                target_role="WORKER",
            )
            resource_session.assert_current()
            worker_launch_authority.assert_current()
            business_launch_authority.assert_current()
            worker_sandbox_authority.assert_current()
            business_sandbox_authority.assert_current()
            _assert_joined_inputs_v2(
                prepared_session=prepared_session,
                resource_session=resource_session,
                worker_launch_authority=worker_launch_authority,
                business_launch_authority=business_launch_authority,
                worker_sandbox_authority=worker_sandbox_authority,
                business_sandbox_authority=business_sandbox_authority,
            )
            request_replay = _reconstruct_request_replay_v2(
                worker_launch_authority,
                business_launch_authority,
            )
            prepared_session_id = prepared_session.session_id
            resource_session_id = resource_session.session_id
            manifest_id = resource_session.manifest.manifest_id
            worker_authority_id = worker_launch_authority.authority_id
            business_authority_id = business_launch_authority.authority_id
            session_key = (
                os.getpid(), prepared_session_id, resource_session_id
            )
            with _CONSUMED_LOCK:
                if session_key in _CONSUMED_SESSIONS:
                    _fail("production broker session pair was already consumed")
                _CONSUMED_SESSIONS.add(session_key)

            # The V1 endpoints were only probe capabilities.  Closing both
            # under the guardian lock makes the V2 SEQPACKET topology the sole
            # live protocol authority and permanently disables the old probe.
            for attribute in ("_worker_socket_fd", "_business_socket_fd"):
                descriptor = getattr(guardian, attribute)
                if descriptor < 3:
                    _fail("prepared probe socket was already superseded")
                os.close(descriptor)
                setattr(guardian, attribute, -1)
            guardian._production_broker_runtime_cleanup_authority = cleanup

            launch_records["WORKER"] = worker_launch_authority.consume()
            launch_records["BUSINESS"] = business_launch_authority.consume()
            materials["WORKER"] = (
                sandbox_v2.consume_v075_k7_production_role_preexec_sandbox_v2(
                    worker_sandbox_authority
                )
            )
            materials["BUSINESS"] = (
                sandbox_v2.consume_v075_k7_production_role_preexec_sandbox_v2(
                    business_sandbox_authority
                )
            )
            cleanup._sandbox_materials.extend(materials.values())  # noqa: SLF001
            for record in launch_records.values():
                cleanup._launch_owned_fds.update((record[0], *record[1]))  # noqa: SLF001
            transfer = resource_session.consume_for_runtime_v2()
            cleanup._transfer = transfer  # noqa: SLF001
            worker_endpoint = socket.socket(
                fileno=fcntl.fcntl(
                    transfer.broker_descriptor("WORKER_CHANNEL"),
                    fcntl.F_DUPFD_CLOEXEC,
                    3,
                )
            )
            business_endpoint = socket.socket(
                fileno=fcntl.fcntl(
                    transfer.broker_descriptor("BUSINESS_CHANNEL"),
                    fcntl.F_DUPFD_CLOEXEC,
                    3,
                )
            )
            cleanup._broker_endpoints.extend((worker_endpoint, business_endpoint))  # noqa: SLF001

            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
            blocked = set(signal.valid_signals()) - {signal.SIGKILL, signal.SIGSTOP}
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)

            launches["WORKER"] = _launch_production_role_v2(
                role="WORKER",
                leaf_fd=guardian._worker_fd,  # noqa: SLF001
                launch_record=launch_records["WORKER"],
                sandbox_material=materials["WORKER"],
                native_cells=cleanup._native_cells["WORKER"],  # noqa: SLF001
                deadline_ns=deadline_ns,
            )
            cleanup._launches["WORKER"] = launches["WORKER"]  # noqa: SLF001
            transfer.retire_parent_side_descriptors_after_clone_v2("WORKER")
            observations.append(
                _receive_authenticated_v2(
                    endpoint=worker_endpoint,
                    launch=launches["WORKER"],
                    binding=prepared_session.binding,
                    role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
                    deadline_ns=deadline_ns,
                )
            )
            observations.append(
                _receive_authenticated_v2(
                    endpoint=worker_endpoint,
                    launch=launches["WORKER"],
                    binding=prepared_session.binding,
                    role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_REQUEST,
                    deadline_ns=deadline_ns,
                )
            )

            launches["BUSINESS"] = _launch_production_role_v2(
                role="BUSINESS",
                leaf_fd=guardian._business_fd,  # noqa: SLF001
                launch_record=launch_records["BUSINESS"],
                sandbox_material=materials["BUSINESS"],
                native_cells=cleanup._native_cells["BUSINESS"],  # noqa: SLF001
                deadline_ns=deadline_ns,
            )
            cleanup._launches["BUSINESS"] = launches["BUSINESS"]  # noqa: SLF001
            transfer.retire_parent_side_descriptors_after_clone_v2("BUSINESS")
            observations.append(
                _receive_authenticated_v2(
                    endpoint=business_endpoint,
                    launch=launches["BUSINESS"],
                    binding=prepared_session.binding,
                    role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT,
                    deadline_ns=deadline_ns,
                )
            )
            business_replay = _read_business_result_v2(
                descriptor=transfer.broker_descriptor("BUSINESS_RESULT_READONLY"),
                frame=observations[2],
                request_replay=request_replay,
            )
            _send_exact_packet_and_half_close_v2(
                worker_endpoint,
                observations[2].frame.framed_bytes,
                deadline_ns,
            )
            observations.append(
                _receive_authenticated_v2(
                    endpoint=worker_endpoint,
                    launch=launches["WORKER"],
                    binding=prepared_session.binding,
                    role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.PARENT_OUTPUT,
                    deadline_ns=deadline_ns,
                )
            )
            observations.append(
                _receive_authenticated_v2(
                    endpoint=worker_endpoint,
                    launch=launches["WORKER"],
                    binding=prepared_session.binding,
                    role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_EOF,
                    deadline_ns=deadline_ns,
                )
            )
            transcript = ipc_v1.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
                raw=b"".join(item.frame.framed_bytes for item in observations),
                expected_binding=prepared_session.binding,
            )

            for role in ROLE_ORDER:
                _wait_zero_exit_v2(launches[role], deadline_ns)
                cleanup._reaped[role] = True  # noqa: SLF001

            # Only after both direct P_PIDFD reaps may the broker become the
            # sole output reader/writer and inspect the worker's durable file.
            pinned = _reread_operational_output_v2(
                output_directory_fd=transfer.broker_descriptor("OUTPUT_DIRECTORY"),
                request_replay=request_replay,
                binding=prepared_session.binding,
                parent_output=observations[3],
            )
            cleanup._take_pinned_output(pinned)  # noqa: SLF001
            peak_identity = _descriptor_identity(guardian._peak_fd)  # noqa: SLF001
            final_peak = preparation_v1._read_open_control(  # noqa: SLF001
                guardian._peak_fd, "memory.peak"  # noqa: SLF001
            )
            if (
                preparation_v1._descriptor(os.fstat(guardian._peak_fd))  # noqa: SLF001
                != dict(prepared_session.execution_spec.memory_peak_identity)
                or final_peak < prepared_session.prelaunch_memory_peak
            ):
                _fail("final memory peak crossed the retained prepared OFD")

            # Known direct children have already been reaped.  Empty cgroups
            # are now a tree-cleanup fact, never a substitute for those reaps.
            guardian._close_prelaunch_locked()  # noqa: SLF001
            cleanup._cgroup_closed = True  # noqa: SLF001
            promoted_name = _promote_output_v2(
                transfer=transfer,
                pinned=pinned,
                resource_session_id=resource_session_id,
                on_renamed=cleanup._record_promoted_output,  # noqa: SLF001
            )
            transfer.close()
            cleanup._resource_closed = True  # noqa: SLF001
            for launch in launches.values():
                os.close(launch.pidfd)
                cleanup._native_cells[launch.role].pidfd.value = -1  # noqa: SLF001
            cleanup._retire_launch_resources()  # noqa: SLF001
            pinned = _PinnedOutputV2(
                -1,
                pinned.identity,
                pinned.operational_output_id,
                pinned.raw,
            )
            cleanup._closed = True  # noqa: SLF001
            guardian._production_broker_runtime_cleanup_authority = None
        except BaseException as error:
            original_error = error
            try:
                cleanup._cleanup_locked()  # noqa: SLF001
            except V075K7ProductionBrokerRuntimeCleanupV2Error as cleanup_error:
                raise cleanup_error from error
            except BaseException as cleanup_error:
                raise V075K7ProductionBrokerRuntimeCleanupV2Error(
                    "production broker failed and cleanup remains retryable",
                    cleanup_complete=False,
                    cleanup_authority=cleanup,
                    unresolved_roles=cleanup.unresolved_roles,
                    output_preserved=cleanup.output_preserved,
                    promoted_output_name=cleanup.promoted_output_name,
                ) from cleanup_error
            raise V075K7ProductionBrokerRuntimeV2Error(
                "production broker runtime failed closed",
                cleanup_complete=True,
                cleanup_authority=None,
                unresolved_roles=(),
                output_preserved=promoted_name is not None,
                promoted_output_name=cleanup.promoted_output_name,
            ) from error
        finally:
            if previous_mask is not None:
                try:
                    signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
                except BaseException as error:
                    if original_error is None:
                        raise V075K7ProductionBrokerRuntimeV2Error(
                            "production broker could not restore its signal mask",
                            cleanup_complete=cleanup._closed,  # noqa: SLF001
                            cleanup_authority=None if cleanup._closed else cleanup,  # noqa: SLF001
                            output_preserved=promoted_name is not None,
                            promoted_output_name=cleanup.promoted_output_name,
                        ) from error

    assert (
        request_replay is not None
        and transfer is not None
        and transcript is not None
        and business_replay is not None
        and pinned is not None
        and promoted_name is not None
        and final_peak is not None
        and peak_identity is not None
        and len(observations) == 5
    )
    role_rows = tuple(
        {
            "role": role,
            "pid": launches[role].pid,
            "pidfd_identity": _identity_document(launches[role].pidfd_identity),
            "native_write_ahead_edge": launches[role].native_edge,
            "setup_raw_sha256": launches[role].setup_raw_sha256,
            "setup_raw_byte_count": launches[role].setup_raw_byte_count,
            "authenticated_frame_ids": [
                item.observation_id
                for item in observations
                if item.sender_pid == launches[role].pid
            ],
            "direct_pidfd_reaped": True,
            "exit_code": 0,
        }
        for role in ROLE_ORDER
    )
    return K7ProductionBrokerRuntimeEnvelopeV2(
        _ENVELOPE_ISSUER,
        prepared_session_id,
        resource_session_id,
        manifest_id,
        worker_authority_id,
        business_authority_id,
        prepared_session.binding,
        role_rows,
        tuple(observations),
        transcript,
        business_replay.bundle_id,
        business_replay.raw_sha256,
        business_replay.raw_byte_count,
        pinned.operational_output_id,
        hashlib.sha256(pinned.raw).hexdigest(),
        len(pinned.raw),
        _identity_document(pinned.identity),
        promoted_name,
        final_peak,
        _identity_document(peak_identity),
        True,
        True,
    )


__all__ = (
    "FRAME_ROLE_ORDER",
    "K7ProductionBrokerRuntimeCleanupAuthorityV2",
    "K7ProductionBrokerRuntimeEnvelopeV2",
    "K7ProductionBrokerRuntimeProfileV2",
    "PROFILE_KEY",
    "PROMOTED_OUTPUT_PREFIX",
    "PROPOSED_CONTRACT_VERSION",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "V075K7ProductionBrokerRuntimeCleanupV2Error",
    "V075K7ProductionBrokerRuntimeV2Error",
    "official_v075_k7_production_broker_runtime_profile_v2",
    "run_v075_k7_production_broker_runtime_v2",
)
