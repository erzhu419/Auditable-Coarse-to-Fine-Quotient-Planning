"""Issuer-owned K7 worker protocol core and durable output commit.

This module implements the worker half of the future live external-broker
runtime.  It emits the two worker prefix frames, accepts one broker-forwarded
business-result frame, replays the sealed public business bundle, commits one
canonical operational output with ``RENAME_NOREPLACE`` durability, and emits
the two worker suffix frames.  Process launch, kernel peer authentication,
post-reap accounting and formal shared-resource receipts remain outside this
core.
"""

from __future__ import annotations

import ctypes
from dataclasses import InitVar, dataclass, field
import errno
import fcntl
import hashlib
import os
import select
import socket
import stat
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as atomic_runtime
from acfqp import v075_k7_child_business_bundle_v1 as business_bundle
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as broker_ipc
from acfqp import v075_k7_successor_portable_replay_v1 as portable_replay
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_BROKER_OPERATIONAL_OUTPUT_V1_DOMAIN,
    V075_K7_BROKER_OUTPUT_COMMIT_RECEIPT_V1_DOMAIN,
    V075_K7_BROKER_WORKER_COMPLETION_V1_DOMAIN,
    V075_K7_BROKER_WORKER_ENTRY_CORE_PROFILE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.7"
PROFILE_KEY = "v075_k7_broker_worker_entry_core_v1"
OUTPUT_NAME = "operational-output.json"
RENAME_NOREPLACE = 1
MAX_OUTPUT_BYTES = 128 * 1024 * 1024
MAX_BUSINESS_RESULT_PACKET_BYTES = 64 * 1024
BROKER_RESULT_EOF_WAIT_MILLISECONDS = 30_000

LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_BROKER_WORKER_ENTRY_CORE_PROFILE_V1_DOMAIN,
        V075_K7_BROKER_OPERATIONAL_OUTPUT_V1_DOMAIN,
        V075_K7_BROKER_OUTPUT_COMMIT_RECEIPT_V1_DOMAIN,
        V075_K7_BROKER_WORKER_COMPLETION_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("broker-worker domains are unregistered")

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_BROKER_WORKER_ENTRY_CORE_PROFILE_V1_DOMAIN",
    "V075_K7_BROKER_OPERATIONAL_OUTPUT_V1_DOMAIN",
    "V075_K7_BROKER_OUTPUT_COMMIT_RECEIPT_V1_DOMAIN",
    "V075_K7_BROKER_WORKER_COMPLETION_V1_DOMAIN",
)

_PROFILE_ISSUER = object()
_OUTPUT_ISSUER = object()
_COMMIT_ISSUER = object()
_COMPLETION_ISSUER = object()
_BOUNDARY_ISSUER = object()
_BOUNDARY_FACTS_ISSUER = object()


class V075K7BrokerWorkerEntryV1Error(RuntimeError):
    """The worker protocol, bundle replay, or durable commit failed closed."""


@dataclass(frozen=True, slots=True)
class _CommitBoundaryFactsV1:
    _issuer: InitVar[object]
    operational_output_id: str
    commit_stage: str
    commit_receipt_id: str | None
    output_directory_contaminated: bool
    directory_device: int
    directory_inode: int
    committed_file_device: int | None
    committed_file_inode: int | None
    file_fsync_completed: bool
    rename_noreplace_completed: bool
    directory_fsync_completed: bool
    cleanup_error_present: bool
    _digest: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BOUNDARY_FACTS_ISSUER:
            _fail("broker worker commit-boundary facts are issuer-owned")
        _cid(self.operational_output_id, "boundary operational output")
        if self.commit_receipt_id is not None:
            _cid(self.commit_receipt_id, "boundary commit receipt")
        if (
            type(self.commit_stage) is not str
            or not self.commit_stage
            or type(self.output_directory_contaminated) is not bool
            or type(self.directory_device) is not int
            or self.directory_device < 0
            or type(self.directory_inode) is not int
            or self.directory_inode < 0
            or (self.committed_file_device is None)
            != (self.committed_file_inode is None)
            or (
                self.committed_file_device is not None
                and (
                    type(self.committed_file_device) is not int
                    or self.committed_file_device < 0
                    or type(self.committed_file_inode) is not int
                    or self.committed_file_inode < 0
                )
            )
            or type(self.file_fsync_completed) is not bool
            or type(self.rename_noreplace_completed) is not bool
            or type(self.directory_fsync_completed) is not bool
            or type(self.cleanup_error_present) is not bool
            or (
                self.rename_noreplace_completed
                and not self.file_fsync_completed
            )
        ):
            _fail("broker worker commit-boundary facts are invalid")
        object.__setattr__(
            self,
            "_digest",
            hashlib.sha256(canonical_json_bytes(self._payload())).hexdigest(),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_broker_worker_commit_boundary_facts.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "operational_output_id": self.operational_output_id,
            "commit_stage": self.commit_stage,
            "commit_receipt_id": self.commit_receipt_id,
            "output_directory_contaminated": self.output_directory_contaminated,
            "directory_device": self.directory_device,
            "directory_inode": self.directory_inode,
            "committed_file_device": self.committed_file_device,
            "committed_file_inode": self.committed_file_inode,
            "file_fsync_completed": self.file_fsync_completed,
            "rename_noreplace_completed": self.rename_noreplace_completed,
            "directory_fsync_completed": self.directory_fsync_completed,
            "cleanup_error_present": self.cleanup_error_present,
        }

    def assert_current(self) -> None:
        if hashlib.sha256(canonical_json_bytes(self._payload())).hexdigest() != self._digest:
            _fail("broker worker commit-boundary facts changed after issuance")


class V075K7BrokerWorkerCommitBoundaryV1Error(
    V075K7BrokerWorkerEntryV1Error
):
    """An irreversible output boundary was crossed before clean completion."""

    def __init__(
        self,
        issuer: object,
        message: str,
        *,
        operational_output: "V075K7BrokerOperationalOutputV1",
        commit_stage: str,
        commit_receipt: "V075K7BrokerOutputCommitReceiptV1 | None" = None,
        output_directory_contaminated: bool,
        directory_device: int,
        directory_inode: int,
        committed_file_device: int | None,
        committed_file_inode: int | None,
        file_fsync_completed: bool,
        rename_noreplace_completed: bool,
        directory_fsync_completed: bool,
        cleanup_error: BaseException | None = None,
    ) -> None:
        if issuer is not _BOUNDARY_ISSUER:
            _fail("broker worker commit-boundary error is issuer-owned")
        super().__init__(message)
        if type(operational_output) is not V075K7BrokerOperationalOutputV1:
            _fail("broker worker commit boundary retained a mistyped output")
        operational_output._assert_current()  # noqa: SLF001
        if (
            commit_receipt is not None
            and type(commit_receipt) is not V075K7BrokerOutputCommitReceiptV1
        ):
            _fail("broker worker commit boundary retained a mistyped receipt")
        facts = _CommitBoundaryFactsV1(
            _BOUNDARY_FACTS_ISSUER,
            operational_output.output_id,
            commit_stage,
            None if commit_receipt is None else commit_receipt.receipt_id,
            output_directory_contaminated,
            directory_device,
            directory_inode,
            committed_file_device,
            committed_file_inode,
            file_fsync_completed,
            rename_noreplace_completed,
            directory_fsync_completed,
            cleanup_error is not None,
        )
        self._operational_output = operational_output
        self._commit_receipt = commit_receipt
        self._facts = facts
        self._cleanup_error = cleanup_error

    def _assert_current(self) -> None:
        self._facts.assert_current()
        self._operational_output._assert_current()  # noqa: SLF001
        if self._facts.operational_output_id != self._operational_output.output_id:
            _fail("broker worker boundary crossed its operational output")
        current_receipt_id = (
            None
            if self._commit_receipt is None
            else self._commit_receipt.receipt_id
        )
        if current_receipt_id != self._facts.commit_receipt_id:
            _fail("broker worker boundary crossed its commit receipt")

    @property
    def operational_output(self) -> "V075K7BrokerOperationalOutputV1":
        self._assert_current()
        return self._operational_output

    @property
    def commit_receipt(self) -> "V075K7BrokerOutputCommitReceiptV1 | None":
        self._assert_current()
        return self._commit_receipt

    @property
    def cleanup_error(self) -> BaseException | None:
        return self._cleanup_error

    def _fact(self, name: str) -> Any:
        self._facts.assert_current()
        return getattr(self._facts, name)

    @property
    def commit_stage(self) -> str:
        return self._fact("commit_stage")

    @property
    def output_directory_contaminated(self) -> bool:
        return self._fact("output_directory_contaminated")

    @property
    def directory_device(self) -> int:
        return self._fact("directory_device")

    @property
    def directory_inode(self) -> int:
        return self._fact("directory_inode")

    @property
    def committed_file_device(self) -> int | None:
        return self._fact("committed_file_device")

    @property
    def committed_file_inode(self) -> int | None:
        return self._fact("committed_file_inode")

    @property
    def file_fsync_completed(self) -> bool:
        return self._fact("file_fsync_completed")

    @property
    def rename_noreplace_completed(self) -> bool:
        return self._fact("rename_noreplace_completed")

    @property
    def directory_fsync_completed(self) -> bool:
        return self._fact("directory_fsync_completed")


def _fail(message: str) -> NoReturn:
    raise V075K7BrokerWorkerEntryV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7BrokerWorkerEntryV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("broker worker used an undeclared content domain")
    return content_id(domain, dict(payload))


def _formal_locks() -> dict[str, bool]:
    return {
        "production_role_manifest_verified": False,
        "kernel_peer_role_provenance_verified": False,
        "live_five_frame_transcript_verified": False,
        "post_reap_supervisor_envelope_verified": False,
        "complete_attempt_memory_window_verified": False,
        "shared_resource_value_issued": False,
        "counter_record_authorized": False,
        "work_vector_authorized": False,
        "comparison_vector_authorized": False,
        "actual_projection_proof_authorized": False,
        "attempt_terminal_authorized": False,
        "official_execution_allowed": False,
    }


@dataclass(frozen=True, slots=True)
class V075K7BrokerWorkerEntryCoreProfileV1:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("broker-worker profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(V075_K7_BROKER_WORKER_ENTRY_CORE_PROFILE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        role = broker_ipc.K7OuterAttemptBrokerFrameRoleV1
        return {
            "schema": "acfqp.v075_k7_broker_worker_entry_core_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outer_attempt_broker_ipc_profile_id": (
                broker_ipc.official_v075_k7_outer_attempt_broker_ipc_profile_v1().profile_id
            ),
            "worker_emitted_frame_roles": [
                role.WORKER_READY.value,
                role.BUSINESS_REQUEST.value,
                role.PARENT_OUTPUT.value,
                role.WORKER_EOF.value,
            ],
            "broker_forwarded_frame_role": role.BUSINESS_RESULT.value,
            "control_transport": "AF_UNIX_SOCK_SEQPACKET",
            "business_payload_transport": "SEALED_READ_ONLY_MEMFD",
            "broker_result_half_close_required": True,
            "broker_result_eof_wait_milliseconds": (
                BROKER_RESULT_EOF_WAIT_MILLISECONDS
            ),
            "max_business_result_packet_bytes": MAX_BUSINESS_RESULT_PACKET_BYTES,
            "output_name": OUTPUT_NAME,
            "output_name_caller_selectable": False,
            "output_commit_sequence": [
                "OPENAT_O_EXCL_O_NOFOLLOW",
                "WRITE_ALL",
                "FSYNC_FILE",
                "RENAMEAT2_RENAME_NOREPLACE",
                "FSYNC_DIRECTORY",
                "DESCRIPTOR_PINNED_READBACK",
            ],
            "durable_pre_reap_operational_output_implemented": True,
            "exclusive_output_directory_writer_verified": False,
            "post_return_output_name_stability_verified": False,
            "durable_eight_role_fixed_point_implemented": False,
            "process_launch_implemented": False,
            **_formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _hash(
            V075_K7_BROKER_WORKER_ENTRY_CORE_PROFILE_V1_DOMAIN,
            self._payload(),
        ) != self._profile_id:
            _fail("broker-worker profile changed after issuance")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "broker_worker_entry_core_profile_id": self.profile_id}


_OFFICIAL_PROFILE = V075K7BrokerWorkerEntryCoreProfileV1(_PROFILE_ISSUER)


def official_v075_k7_broker_worker_entry_core_profile_v1(
) -> V075K7BrokerWorkerEntryCoreProfileV1:
    return _OFFICIAL_PROFILE


def _assert_request_and_binding(
    request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    binding: broker_ipc.K7OuterAttemptBrokerIPCBindingV1,
) -> None:
    if (
        type(request_replay)
        is not portable_replay.V075K7SuccessorPortableRequestReplayV1
        or type(binding) is not broker_ipc.K7OuterAttemptBrokerIPCBindingV1
    ):
        _fail("broker worker requires exact request replay and IPC binding")
    request_replay.profile_closure._assert_current()  # noqa: SLF001
    request = request_replay.request
    request._assert_current()  # noqa: SLF001
    if (
        binding.request_id != request.request_id
        or binding.route_identity_id != request.route_identity.route_identity_id
    ):
        _fail("broker worker request replay crossed its IPC binding")


def _assert_seqpacket(endpoint: socket.socket) -> None:
    if type(endpoint) is not socket.socket or endpoint.fileno() < 0:
        _fail("broker worker requires one live socket endpoint")
    try:
        socket_type = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
        if not hasattr(socket, "SO_DOMAIN"):
            _fail("Linux SO_DOMAIN is unavailable for worker endpoint verification")
        kernel_domain = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_DOMAIN)
        descriptor = endpoint.fileno()
        status = os.fstat(descriptor)
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        inheritable = os.get_inheritable(descriptor)
        endpoint.getpeername()
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker worker endpoint cannot be inspected"
        ) from error
    if (
        endpoint.family != socket.AF_UNIX
        or kernel_domain != socket.AF_UNIX
        or socket_type != socket.SOCK_SEQPACKET
        or not stat.S_ISSOCK(status.st_mode)
        or endpoint.gettimeout() is not None
        or flags & os.O_NONBLOCK
        or inheritable
    ):
        _fail(
            "broker worker endpoint must be connected blocking CLOEXEC "
            "AF_UNIX SOCK_SEQPACKET"
        )


def _send_packet(endpoint: socket.socket, raw: bytes) -> None:
    try:
        sent = endpoint.send(raw)
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker worker could not send one protocol packet"
        ) from error
    if sent != len(raw):
        _fail("broker worker protocol packet was partially sent")


def _receive_packet_and_require_peer_eof(endpoint: socket.socket) -> bytes:
    cap = MAX_BUSINESS_RESULT_PACKET_BYTES
    try:
        raw, ancillary, flags, address = endpoint.recvmsg(cap, 0)
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker worker could not receive the business-result packet"
        ) from error
    if (
        not raw
        or ancillary
        or flags & (getattr(socket, "MSG_TRUNC", 0) | getattr(socket, "MSG_CTRUNC", 0))
        or address not in {None, "", b""}
    ):
        _fail("broker worker received a truncated, attributed, or injected packet")
    poller = select.poll()
    poller.register(
        endpoint.fileno(),
        select.POLLIN | select.POLLHUP | select.POLLERR | select.POLLNVAL,
    )
    try:
        events = poller.poll(BROKER_RESULT_EOF_WAIT_MILLISECONDS)
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker result-channel closure wait failed"
        ) from error
    if not events:
        _fail("broker did not half-close within the frozen EOF wait")
    try:
        trailing, trailing_ancillary, trailing_flags, trailing_address = endpoint.recvmsg(
            1,
            0,
            getattr(socket, "MSG_PEEK", 0),
        )
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker result-channel closure cannot be verified"
        ) from error
    if (
        trailing
        or trailing_ancillary
        or trailing_flags
        or trailing_address not in {None, "", b""}
    ):
        _fail("broker sent an extra packet after the sole business result")
    return raw


def _assert_read_only_memfd(fd: int, *, allow_empty: bool) -> None:
    if type(fd) is not int or fd < 0:
        _fail("business-result descriptor is invalid")
    try:
        status = os.fstat(fd)
        descriptor_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        access = descriptor_flags & os.O_ACCMODE
        seals = fcntl.fcntl(fd, atomic_runtime.F_GET_SEALS)
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "business-result descriptor cannot be inspected"
        ) from error
    if (
        not stat.S_ISREG(status.st_mode)
        or access != os.O_RDONLY
        or descriptor_flags & getattr(os, "O_PATH", 0)
        or (not allow_empty and status.st_size <= 0)
        or status.st_size > business_bundle.MAX_BUNDLE_BYTES
        or (
            status.st_size == 0
            and seals != 0
        )
        or (
            status.st_size > 0
            and seals & atomic_runtime.REQUIRED_MEMFD_SEALS
            != atomic_runtime.REQUIRED_MEMFD_SEALS
        )
    ):
        _fail("business-result descriptor is not one bounded read-only memfd")
    try:
        os.pread(fd, 1, 0)
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "business-result descriptor is not readable"
        ) from error


def _assert_output_directory_preflight(directory_fd: int) -> os.stat_result:
    if type(directory_fd) is not int or directory_fd < 0:
        _fail("broker worker output directory descriptor is invalid")
    try:
        status = os.fstat(directory_fd)
        descriptor_flags = fcntl.fcntl(directory_fd, fcntl.F_GETFL)
        entries = os.listdir(directory_fd)
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker worker output directory cannot be inspected"
        ) from error
    if (
        not stat.S_ISDIR(status.st_mode)
        or status.st_nlink <= 0
        or descriptor_flags & getattr(os, "O_PATH", 0)
        or entries
    ):
        _fail("broker worker requires one empty usable output directory")
    return status


def _read_sealed_business_result(fd: int) -> bytes:
    _assert_read_only_memfd(fd, allow_empty=False)
    before = os.fstat(fd)
    try:
        seals = fcntl.fcntl(fd, atomic_runtime.F_GET_SEALS)
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "business-result descriptor is not a sealable memfd"
        ) from error
    if seals & atomic_runtime.REQUIRED_MEMFD_SEALS != atomic_runtime.REQUIRED_MEMFD_SEALS:
        _fail("business-result memfd lacks the complete immutable seal set")
    chunks: list[bytes] = []
    offset = 0
    while offset < before.st_size:
        chunk = os.pread(fd, min(1024 * 1024, before.st_size - offset), offset)
        if not chunk:
            _fail("sealed business-result memfd was truncated")
        chunks.append(chunk)
        offset += len(chunk)
    after = os.fstat(fd)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        _fail("sealed business-result memfd identity changed while read")
    return b"".join(chunks)


_OUTPUT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "broker_worker_entry_core_profile_id",
        "outer_attempt_broker_ipc_profile_id",
        "request_id",
        "route_identity_id",
        "broker_execution_spec_id",
        "session_nonce",
        "portable_request_replay_id",
        "business_result_id",
        "business_result_sha256",
        "business_result_byte_count",
        "business_result",
        "output_scope",
        "durable_eight_role_fixed_point_implemented",
        "post_reap_supervisor_envelope_required",
        "formal_locks",
        "broker_operational_output_id",
    }
)


@dataclass(frozen=True, slots=True)
class V075K7BrokerOperationalOutputV1:
    _issuer: InitVar[object]
    _raw: bytes = field(repr=False)
    _request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1 = field(
        repr=False, compare=False
    )
    _binding: broker_ipc.K7OuterAttemptBrokerIPCBindingV1 = field(
        repr=False, compare=False
    )
    _raw_sha256: str = field(init=False, repr=False, compare=False)
    _validated_output_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _OUTPUT_ISSUER or type(self._raw) is not bytes:
            _fail("broker operational output is caller-minted")
        _validate_output_document(
            self._raw,
            expected_request_replay=self._request_replay,
            expected_binding=self._binding,
        )
        document = loads_canonical_json(self._raw)
        assert type(document) is dict
        object.__setattr__(self, "_raw_sha256", hashlib.sha256(self._raw).hexdigest())
        object.__setattr__(
            self,
            "_validated_output_id",
            document["broker_operational_output_id"],
        )

    def _assert_current(self) -> None:
        _validate_output_document(
            self._raw,
            expected_request_replay=self._request_replay,
            expected_binding=self._binding,
        )
        document = loads_canonical_json(self._raw)
        if (
            type(document) is not dict
            or hashlib.sha256(self._raw).hexdigest() != self._raw_sha256
            or document.get("broker_operational_output_id")
            != self._validated_output_id
        ):
            _fail("broker operational output changed after issuance")

    @property
    def output_id(self) -> str:
        self._assert_current()
        return self._validated_output_id

    @property
    def canonical_bytes(self) -> bytes:
        self._assert_current()
        return self._raw

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        value = loads_canonical_json(self._raw)
        if type(value) is not dict:  # pragma: no cover - constructor proves this
            _fail("broker operational output is not an object")
        return value


def _validate_output_document(
    raw: bytes,
    *,
    expected_request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    expected_binding: broker_ipc.K7OuterAttemptBrokerIPCBindingV1,
) -> business_bundle.V075K7ChildBusinessBundleV1:
    _assert_request_and_binding(expected_request_replay, expected_binding)
    if type(raw) is not bytes or not raw or len(raw) > MAX_OUTPUT_BYTES:
        _fail("broker operational output bytes are empty, mistyped, or over cap")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker operational output is not canonical JSON"
        ) from error
    if (
        type(document) is not dict
        or frozenset(document) != _OUTPUT_FIELDS
        or canonical_json_bytes(document) != raw
    ):
        _fail("broker operational output fields or canonical bytes changed")
    payload = dict(document)
    claimed = _cid(payload.pop("broker_operational_output_id"), "operational output")
    request = expected_request_replay.request
    if (
        document["schema"] != "acfqp.v075_k7_broker_operational_output.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["broker_worker_entry_core_profile_id"] != _OFFICIAL_PROFILE.profile_id
        or document["outer_attempt_broker_ipc_profile_id"]
        != broker_ipc.official_v075_k7_outer_attempt_broker_ipc_profile_v1().profile_id
        or document["request_id"] != expected_binding.request_id
        or document["route_identity_id"] != expected_binding.route_identity_id
        or document["broker_execution_spec_id"]
        != expected_binding.broker_execution_spec_id
        or document["session_nonce"] != expected_binding.session_nonce
        or document["portable_request_replay_id"] != expected_request_replay.replay_id
        or document["output_scope"] != "PRE_REAP_OPERATIONAL_RESULT"
        or document["durable_eight_role_fixed_point_implemented"] is not False
        or document["post_reap_supervisor_envelope_required"] is not True
        or document["formal_locks"] != _formal_locks()
        or _hash(V075_K7_BROKER_OPERATIONAL_OUTPUT_V1_DOMAIN, payload) != claimed
        or request.request_id != expected_binding.request_id
    ):
        _fail("broker operational output identity or authority changed")
    business_raw = canonical_json_bytes(document["business_result"])
    if (
        type(document["business_result_byte_count"]) is not int
        or document["business_result_byte_count"] != len(business_raw)
        or document["business_result_sha256"]
        != hashlib.sha256(business_raw).hexdigest()
    ):
        _fail("broker operational output business-result commitment changed")
    try:
        verified = business_bundle.verify_v075_k7_child_business_bundle_public_bytes_v1(
            raw=business_raw,
            expected_request_replay=expected_request_replay,
        )
    except Exception as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker operational output nested business replay failed"
        ) from error
    if verified.bundle_id != _cid(document["business_result_id"], "business result"):
        _fail("broker operational output crossed its business-result identity")
    return verified


def verify_v075_k7_broker_operational_output_bytes_v1(
    *,
    raw: bytes,
    expected_request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    expected_binding: broker_ipc.K7OuterAttemptBrokerIPCBindingV1,
) -> V075K7BrokerOperationalOutputV1:
    _validate_output_document(
        raw,
        expected_request_replay=expected_request_replay,
        expected_binding=expected_binding,
    )
    return V075K7BrokerOperationalOutputV1(
        _OUTPUT_ISSUER,
        raw,
        expected_request_replay,
        expected_binding,
    )


def _freeze_output(
    *,
    request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    binding: broker_ipc.K7OuterAttemptBrokerIPCBindingV1,
    bundle: business_bundle.V075K7ChildBusinessBundleV1,
) -> V075K7BrokerOperationalOutputV1:
    business_raw = bundle.canonical_bytes
    payload = {
        "schema": "acfqp.v075_k7_broker_operational_output.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "broker_worker_entry_core_profile_id": _OFFICIAL_PROFILE.profile_id,
        "outer_attempt_broker_ipc_profile_id": (
            broker_ipc.official_v075_k7_outer_attempt_broker_ipc_profile_v1().profile_id
        ),
        **binding.to_document(),
        "portable_request_replay_id": request_replay.replay_id,
        "business_result_id": bundle.bundle_id,
        "business_result_sha256": hashlib.sha256(business_raw).hexdigest(),
        "business_result_byte_count": len(business_raw),
        "business_result": bundle.to_document(),
        "output_scope": "PRE_REAP_OPERATIONAL_RESULT",
        "durable_eight_role_fixed_point_implemented": False,
        "post_reap_supervisor_envelope_required": True,
        "formal_locks": _formal_locks(),
    }
    raw = canonical_json_bytes(
        {
            **payload,
            "broker_operational_output_id": _hash(
                V075_K7_BROKER_OPERATIONAL_OUTPUT_V1_DOMAIN, payload
            ),
        }
    )
    return V075K7BrokerOperationalOutputV1(
        _OUTPUT_ISSUER, raw, request_replay, binding
    )


def _rename_noreplace(directory_fd: int, old_name: str, new_name: str) -> None:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (OSError, AttributeError) as error:
        raise V075K7BrokerWorkerEntryV1Error(
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
    result = renameat2(
        directory_fd,
        old_name.encode("ascii"),
        directory_fd,
        new_name.encode("ascii"),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number), new_name)


def _write_all(fd: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(fd, raw[offset:])
        if written <= 0:
            _fail("broker operational output write made no progress")
        offset += written


def _read_committed(fd: int, expected_size: int) -> tuple[bytes, os.stat_result]:
    before = os.fstat(fd)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size != expected_size
    ):
        _fail("committed operational output inode is invalid")
    chunks: list[bytes] = []
    offset = 0
    while offset < expected_size:
        chunk = os.pread(fd, min(1024 * 1024, expected_size - offset), offset)
        if not chunk:
            _fail("committed operational output was truncated")
        chunks.append(chunk)
        offset += len(chunk)
    after = os.fstat(fd)
    if (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_uid,
        before.st_gid,
        before.st_nlink,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_uid,
        after.st_gid,
        after.st_nlink,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        _fail("committed operational output inode changed during readback")
    return b"".join(chunks), before


@dataclass(frozen=True, slots=True)
class V075K7BrokerOutputCommitReceiptV1:
    _issuer: InitVar[object]
    operational_output_id: str
    output_byte_count: int
    output_sha256: str
    directory_device: int
    directory_inode: int
    file_device: int
    file_inode: int
    file_mode: int
    file_uid: int
    file_gid: int
    recovered_after_boundary_failure: bool
    _receipt_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _COMMIT_ISSUER:
            _fail("broker output commit receipt is issuer-owned")
        object.__setattr__(
            self,
            "operational_output_id",
            _cid(self.operational_output_id, "operational output"),
        )
        if (
            type(self.output_byte_count) is not int
            or not 0 < self.output_byte_count <= MAX_OUTPUT_BYTES
            or type(self.output_sha256) is not str
            or len(self.output_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.output_sha256)
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.directory_device,
                    self.directory_inode,
                    self.file_device,
                    self.file_inode,
                    self.file_mode,
                    self.file_uid,
                    self.file_gid,
                )
            )
            or not stat.S_ISREG(self.file_mode)
            or type(self.recovered_after_boundary_failure) is not bool
        ):
            _fail("broker output commit receipt fields are invalid")
        object.__setattr__(
            self,
            "_receipt_id",
            _hash(V075_K7_BROKER_OUTPUT_COMMIT_RECEIPT_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_broker_output_commit_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "broker_worker_entry_core_profile_id": _OFFICIAL_PROFILE.profile_id,
            "broker_operational_output_id": self.operational_output_id,
            "output_name": OUTPUT_NAME,
            "output_byte_count": self.output_byte_count,
            "output_sha256": self.output_sha256,
            "directory_device": self.directory_device,
            "directory_inode": self.directory_inode,
            "file_device": self.file_device,
            "file_inode": self.file_inode,
            "file_mode": self.file_mode,
            "file_uid": self.file_uid,
            "file_gid": self.file_gid,
            "file_link_count": 1,
            "file_fsync_completed": True,
            "rename_noreplace_completed": True,
            "directory_fsync_completed": True,
            "descriptor_pinned_readback_completed": True,
            "name_to_inode_recheck_completed": True,
            "recovered_after_boundary_failure": self.recovered_after_boundary_failure,
            "atomic_local_commit_sequence_verified": True,
            "exclusive_output_directory_writer_verified": False,
            "post_return_output_name_stability_verified": False,
            "formal_durable_output_authority": False,
            "shared_resource_receipt_issued": False,
            "formal_locks": _formal_locks(),
        }

    @property
    def receipt_id(self) -> str:
        if _hash(
            V075_K7_BROKER_OUTPUT_COMMIT_RECEIPT_V1_DOMAIN,
            self._payload(),
        ) != self._receipt_id:
            _fail("broker output commit receipt changed after issuance")
        return self._receipt_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "broker_output_commit_receipt_id": self.receipt_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _commit_output(
    *, output: V075K7BrokerOperationalOutputV1, directory_fd: int
) -> V075K7BrokerOutputCommitReceiptV1:
    if type(output) is not V075K7BrokerOperationalOutputV1:
        _fail("broker worker commit requires one exact issued operational output")
    output._assert_current()  # noqa: SLF001
    directory_before = _assert_output_directory_preflight(directory_fd)
    raw = output.canonical_bytes
    temporary_name = f".{output.output_id}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    output_fd = -1
    renamed = False
    temporary_created = False
    temporary_status: os.stat_result | None = None
    file_fsync_completed = False
    directory_fsync_completed = False
    commit_stage = "PRE_TEMPORARY_OPEN"
    receipt: V075K7BrokerOutputCommitReceiptV1 | None = None
    primary_error: BaseException | None = None
    cleanup_error: BaseException | None = None
    try:
        output_fd = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        temporary_created = True
        commit_stage = "TEMPORARY_OPENED"
        temporary_status = os.fstat(output_fd)
        os.fchmod(output_fd, 0o600)
        if not stat.S_ISREG(temporary_status.st_mode) or temporary_status.st_nlink != 1:
            _fail("broker worker temporary output is not one private regular file")
        _write_all(output_fd, raw)
        os.fsync(output_fd)
        file_fsync_completed = True
        commit_stage = "FILE_SYNCED"
        owned_fd = output_fd
        output_fd = -1
        os.close(owned_fd)
        _rename_noreplace(directory_fd, temporary_name, OUTPUT_NAME)
        renamed = True
        commit_stage = "RENAMED_NOREPLACE"
        os.fsync(directory_fd)
        directory_fsync_completed = True
        commit_stage = "DIRECTORY_SYNCED"
        read_flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            read_flags |= os.O_NOFOLLOW
        output_fd = os.open(OUTPUT_NAME, read_flags, dir_fd=directory_fd)
        replayed, file_status = _read_committed(output_fd, len(raw))
        directory_after = os.fstat(directory_fd)
        named_status = os.stat(
            OUTPUT_NAME,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        if (
            replayed != raw
            or hashlib.sha256(replayed).hexdigest() != hashlib.sha256(raw).hexdigest()
            or (directory_before.st_dev, directory_before.st_ino)
            != (directory_after.st_dev, directory_after.st_ino)
            or (temporary_status.st_dev, temporary_status.st_ino)
            != (file_status.st_dev, file_status.st_ino)
            or (named_status.st_dev, named_status.st_ino)
            != (file_status.st_dev, file_status.st_ino)
        ):
            _fail("broker operational output durable readback changed")
        receipt = V075K7BrokerOutputCommitReceiptV1(
            _COMMIT_ISSUER,
            output.output_id,
            len(raw),
            hashlib.sha256(raw).hexdigest(),
            directory_after.st_dev,
            directory_after.st_ino,
            file_status.st_dev,
            file_status.st_ino,
            file_status.st_mode,
            file_status.st_uid,
            file_status.st_gid,
            False,
        )
        commit_stage = "READBACK_AND_NAME_RECHECK_VERIFIED"
    except BaseException as error:
        primary_error = error
    finally:
        if output_fd >= 0:
            owned_fd = output_fd
            output_fd = -1
            try:
                os.close(owned_fd)
            except BaseException as error:
                cleanup_error = error
        if not renamed and temporary_created:
            try:
                named_temporary = os.stat(
                    temporary_name,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
                if (
                    temporary_status is None
                    or (named_temporary.st_dev, named_temporary.st_ino)
                    != (temporary_status.st_dev, temporary_status.st_ino)
                ):
                    raise V075K7BrokerWorkerEntryV1Error(
                        "broker worker temporary name no longer names its owned inode"
                    )
                os.unlink(temporary_name, dir_fd=directory_fd)
            except FileNotFoundError as error:
                if cleanup_error is None:
                    cleanup_error = V075K7BrokerWorkerEntryV1Error(
                        "broker worker owned temporary name disappeared before cleanup"
                    )
                    cleanup_error.__cause__ = error
            except BaseException as error:
                if cleanup_error is None:
                    cleanup_error = error

    if primary_error is not None or cleanup_error is not None:
        causal_error = primary_error if primary_error is not None else cleanup_error
        assert causal_error is not None
        if renamed or cleanup_error is not None:
            raise V075K7BrokerWorkerCommitBoundaryV1Error(
                _BOUNDARY_ISSUER,
                "broker operational output crossed a commit boundary before clean completion",
                operational_output=output,
                commit_stage=commit_stage,
                commit_receipt=receipt,
                output_directory_contaminated=(renamed or cleanup_error is not None),
                directory_device=directory_before.st_dev,
                directory_inode=directory_before.st_ino,
                committed_file_device=(
                    None if temporary_status is None else temporary_status.st_dev
                ),
                committed_file_inode=(
                    None if temporary_status is None else temporary_status.st_ino
                ),
                file_fsync_completed=file_fsync_completed,
                rename_noreplace_completed=renamed,
                directory_fsync_completed=directory_fsync_completed,
                cleanup_error=cleanup_error,
            ) from causal_error
        if isinstance(primary_error, OSError):
            if primary_error.errno == errno.EEXIST:
                raise V075K7BrokerWorkerEntryV1Error(
                    "broker operational output commit refused an existing name"
                ) from primary_error
            raise V075K7BrokerWorkerEntryV1Error(
                "broker operational output durable commit failed"
            ) from primary_error
        assert primary_error is not None
        raise primary_error
    if receipt is None:  # pragma: no cover - total state audit
        _fail("broker operational output commit produced no receipt")
    return receipt


def recover_v075_k7_broker_committed_output_v1(
    *,
    boundary_error: V075K7BrokerWorkerCommitBoundaryV1Error,
    output_directory_fd: int,
    expected_request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    expected_binding: broker_ipc.K7OuterAttemptBrokerIPCBindingV1,
) -> tuple[V075K7BrokerOperationalOutputV1, V075K7BrokerOutputCommitReceiptV1]:
    """Recover and re-attest a visible output after an irreversible boundary."""

    if (
        type(boundary_error) is not V075K7BrokerWorkerCommitBoundaryV1Error
        or not boundary_error.output_directory_contaminated
        or boundary_error.commit_receipt is not None
        or not boundary_error.file_fsync_completed
        or not boundary_error.rename_noreplace_completed
        or boundary_error.committed_file_device is None
        or boundary_error.committed_file_inode is None
    ):
        _fail(
            "broker output recovery requires one issuer-owned post-rename boundary"
        )
    expected = boundary_error.operational_output
    if type(expected) is not V075K7BrokerOperationalOutputV1:
        _fail("broker output boundary retained the wrong operational output type")
    expected._assert_current()  # noqa: SLF001
    if type(output_directory_fd) is not int or output_directory_fd < 0:
        _fail("broker output recovery directory descriptor is invalid")
    try:
        directory_status = os.fstat(output_directory_fd)
        directory_flags = fcntl.fcntl(output_directory_fd, fcntl.F_GETFL)
        if (
            not stat.S_ISDIR(directory_status.st_mode)
            or directory_flags & getattr(os, "O_PATH", 0)
            or (directory_status.st_dev, directory_status.st_ino)
            != (boundary_error.directory_device, boundary_error.directory_inode)
        ):
            _fail(
                "broker output recovery descriptor crossed its retained directory"
            )
        read_flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            read_flags |= os.O_NOFOLLOW
        descriptor = os.open(
            OUTPUT_NAME,
            read_flags,
            dir_fd=output_directory_fd,
        )
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker output recovery could not open the committed name"
        ) from error
    read_error: BaseException | None = None
    replayed: bytes | None = None
    file_status: os.stat_result | None = None
    try:
        replayed, file_status = _read_committed(
            descriptor,
            len(expected.canonical_bytes),
        )
    except BaseException as error:
        read_error = error
    owned_fd = descriptor
    descriptor = -1
    try:
        os.close(owned_fd)
    except BaseException as close_error:
        if read_error is not None:
            failure = V075K7BrokerWorkerEntryV1Error(
                "broker output recovery read and descriptor close both failed"
            )
            failure.cleanup_error = close_error  # type: ignore[attr-defined]
            raise failure from read_error
        raise V075K7BrokerWorkerEntryV1Error(
            "broker output recovery descriptor close failed"
        ) from close_error
    if read_error is not None:
        raise read_error
    assert replayed is not None and file_status is not None
    if replayed != expected.canonical_bytes:
        _fail("broker output recovery bytes differ from the retained output")
    if (file_status.st_dev, file_status.st_ino) != (
        boundary_error.committed_file_device,
        boundary_error.committed_file_inode,
    ):
        _fail("broker output recovery inode crossed the committed boundary")
    recovered = verify_v075_k7_broker_operational_output_bytes_v1(
        raw=replayed,
        expected_request_replay=expected_request_replay,
        expected_binding=expected_binding,
    )
    try:
        named_status = os.stat(
            OUTPUT_NAME,
            dir_fd=output_directory_fd,
            follow_symlinks=False,
        )
        os.fsync(output_directory_fd)
        directory_after = os.fstat(output_directory_fd)
    except OSError as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker output recovery could not re-establish directory durability"
        ) from error
    if (
        (named_status.st_dev, named_status.st_ino)
        != (file_status.st_dev, file_status.st_ino)
        or (directory_status.st_dev, directory_status.st_ino)
        != (directory_after.st_dev, directory_after.st_ino)
    ):
        _fail("broker output recovery name or directory identity changed")
    receipt = V075K7BrokerOutputCommitReceiptV1(
        _COMMIT_ISSUER,
        recovered.output_id,
        len(replayed),
        hashlib.sha256(replayed).hexdigest(),
        directory_after.st_dev,
        directory_after.st_ino,
        file_status.st_dev,
        file_status.st_ino,
        file_status.st_mode,
        file_status.st_uid,
        file_status.st_gid,
        True,
    )
    return recovered, receipt


@dataclass(frozen=True, slots=True)
class V075K7BrokerWorkerCompletionV1:
    _issuer: InitVar[object]
    binding: broker_ipc.K7OuterAttemptBrokerIPCBindingV1 = field(repr=False)
    business_result_id: str
    operational_output: V075K7BrokerOperationalOutputV1 = field(
        repr=False, compare=False
    )
    output_commit_receipt: V075K7BrokerOutputCommitReceiptV1 = field(
        repr=False, compare=False
    )
    frame_ids: tuple[str, ...]
    _completion_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _COMPLETION_ISSUER
            or type(self.binding) is not broker_ipc.K7OuterAttemptBrokerIPCBindingV1
            or type(self.operational_output)
            is not V075K7BrokerOperationalOutputV1
            or type(self.output_commit_receipt)
            is not V075K7BrokerOutputCommitReceiptV1
            or type(self.frame_ids) is not tuple
            or len(self.frame_ids) != 5
        ):
            _fail("broker worker completion is caller-minted or incomplete")
        object.__setattr__(
            self,
            "business_result_id",
            _cid(self.business_result_id, "business result"),
        )
        self.operational_output._assert_current()  # noqa: SLF001
        if (
            self.output_commit_receipt.operational_output_id
            != self.operational_output.output_id
        ):
            _fail("broker worker completion crossed output and commit receipt")
        object.__setattr__(
            self,
            "frame_ids",
            tuple(_cid(value, "worker protocol frame") for value in self.frame_ids),
        )
        object.__setattr__(
            self,
            "_completion_id",
            _hash(V075_K7_BROKER_WORKER_COMPLETION_V1_DOMAIN, self._payload()),
        )

    @property
    def operational_output_id(self) -> str:
        self.operational_output._assert_current()  # noqa: SLF001
        return self.operational_output.output_id

    @property
    def output_commit_receipt_id(self) -> str:
        return self.output_commit_receipt.receipt_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_broker_worker_completion.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "broker_worker_entry_core_profile_id": _OFFICIAL_PROFILE.profile_id,
            **self.binding.to_document(),
            "business_result_id": self.business_result_id,
            "broker_operational_output_id": self.operational_output_id,
            "broker_output_commit_receipt_id": self.output_commit_receipt_id,
            "operational_output_retained_process_locally": True,
            "output_commit_receipt_retained_process_locally": True,
            "frame_roles": [role.value for role in broker_ipc.FRAME_ROLES],
            "frame_ids": list(self.frame_ids),
            "worker_emitted_frame_count": 4,
            "broker_forwarded_frame_count": 1,
            "business_result_public_replay_completed": True,
            "operational_output_atomic_local_commit_completed": True,
            "exclusive_output_directory_writer_verified": False,
            "post_return_output_name_stability_verified": False,
            "full_five_frame_transcript_requires_broker_replay": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def completion_id(self) -> str:
        self.operational_output._assert_current()  # noqa: SLF001
        if (
            self.output_commit_receipt.operational_output_id
            != self.operational_output.output_id
        ):
            _fail("broker worker completion retained artifact join changed")
        if _hash(
            V075_K7_BROKER_WORKER_COMPLETION_V1_DOMAIN,
            self._payload(),
        ) != self._completion_id:
            _fail("broker worker completion changed after issuance")
        return self._completion_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "broker_worker_completion_id": self.completion_id}


def execute_v075_k7_broker_worker_core_v1(
    *,
    expected_request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    binding: broker_ipc.K7OuterAttemptBrokerIPCBindingV1,
    endpoint: socket.socket,
    sealed_business_result_fd: int,
    output_directory_fd: int,
) -> V075K7BrokerWorkerCompletionV1:
    """Execute exactly one fixed worker-side protocol transaction."""

    _assert_request_and_binding(expected_request_replay, binding)
    _assert_seqpacket(endpoint)
    _assert_read_only_memfd(sealed_business_result_fd, allow_empty=True)
    _assert_output_directory_preflight(output_directory_fd)

    role = broker_ipc.K7OuterAttemptBrokerFrameRoleV1
    ready_raw = broker_ipc.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
        binding=binding,
        role=role.WORKER_READY,
        payload={"worker_replay_id": expected_request_replay.replay_id},
    )
    request_raw = broker_ipc.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
        binding=binding,
        role=role.BUSINESS_REQUEST,
        payload={"request_ordinal": 0},
    )
    _send_packet(endpoint, ready_raw)
    _send_packet(endpoint, request_raw)

    result_raw = _receive_packet_and_require_peer_eof(endpoint)
    result_frame = broker_ipc.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
        raw=result_raw,
        expected_binding=binding,
        expected_role=role.BUSINESS_RESULT,
    )
    business_raw = _read_sealed_business_result(sealed_business_result_fd)
    try:
        bundle = business_bundle.verify_v075_k7_child_business_bundle_public_bytes_v1(
            raw=business_raw,
            expected_request_replay=expected_request_replay,
        )
    except Exception as error:
        raise V075K7BrokerWorkerEntryV1Error(
            "broker worker public business-result replay failed"
        ) from error
    if result_frame.payload["business_result_id"] != bundle.bundle_id:
        _fail("broker-forwarded result frame crossed its sealed business bundle")

    output = _freeze_output(
        request_replay=expected_request_replay,
        binding=binding,
        bundle=bundle,
    )
    receipt = _commit_output(output=output, directory_fd=output_directory_fd)
    output_raw = output.canonical_bytes
    parent_raw = broker_ipc.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
        binding=binding,
        role=role.PARENT_OUTPUT,
        payload={
            "output_byte_count": len(output_raw),
            "output_sha256": hashlib.sha256(output_raw).hexdigest(),
        },
    )
    eof_raw = broker_ipc.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
        binding=binding,
        role=role.WORKER_EOF,
        payload={"clean_close": True},
    )
    try:
        _send_packet(endpoint, parent_raw)
        _send_packet(endpoint, eof_raw)
    except BaseException as error:
        raise V075K7BrokerWorkerCommitBoundaryV1Error(
            _BOUNDARY_ISSUER,
            "broker output was committed before worker suffix completion",
            operational_output=output,
            commit_stage="OUTPUT_COMMITTED_SUFFIX_INCOMPLETE",
            commit_receipt=receipt,
            output_directory_contaminated=True,
            directory_device=receipt.directory_device,
            directory_inode=receipt.directory_inode,
            committed_file_device=receipt.file_device,
            committed_file_inode=receipt.file_inode,
            file_fsync_completed=True,
            rename_noreplace_completed=True,
            directory_fsync_completed=True,
        ) from error

    frames = (
        broker_ipc.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
            raw=ready_raw, expected_binding=binding, expected_role=role.WORKER_READY
        ),
        broker_ipc.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
            raw=request_raw,
            expected_binding=binding,
            expected_role=role.BUSINESS_REQUEST,
        ),
        result_frame,
        broker_ipc.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
            raw=parent_raw, expected_binding=binding, expected_role=role.PARENT_OUTPUT
        ),
        broker_ipc.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
            raw=eof_raw, expected_binding=binding, expected_role=role.WORKER_EOF
        ),
    )
    return V075K7BrokerWorkerCompletionV1(
        _COMPLETION_ISSUER,
        binding,
        bundle.bundle_id,
        output,
        receipt,
        tuple(frame.frame_id for frame in frames),
    )


__all__ = (
    "LOCAL_DOMAIN_TAGS",
    "MAX_OUTPUT_BYTES",
    "MAX_BUSINESS_RESULT_PACKET_BYTES",
    "OUTPUT_NAME",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "V075K7BrokerOperationalOutputV1",
    "V075K7BrokerOutputCommitReceiptV1",
    "V075K7BrokerWorkerCompletionV1",
    "V075K7BrokerWorkerCommitBoundaryV1Error",
    "V075K7BrokerWorkerEntryCoreProfileV1",
    "V075K7BrokerWorkerEntryV1Error",
    "execute_v075_k7_broker_worker_core_v1",
    "official_v075_k7_broker_worker_entry_core_profile_v1",
    "recover_v075_k7_broker_committed_output_v1",
    "verify_v075_k7_broker_operational_output_bytes_v1",
)
