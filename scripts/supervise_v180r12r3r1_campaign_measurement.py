#!/usr/bin/env python3
"""Effectful V180r12r3r1 measured SUPERVISOR target.

The supervisor owns stable input reads, sealed memfd staging, the two/fourteen
STAGE semantic operations, worker launch/reap coordination, subject readback
and commit, visibility closure, and WINDOW_CLOSED.  It never receives an
EVENTS directory descriptor and never writes a campaign journal file.

The filesystem and memfd helpers below are real Linux implementations.  The
high-level bridge is injected so focused tests can prove ordering without
launching a process, mutating cgroup-v2, or consuming an authorization.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
import errno
import fcntl
import hashlib
import hmac
import os
import resource
import select
import signal
from pathlib import PurePosixPath
import socket
import stat
import sys
import types
from typing import Any, Mapping, NoReturn, Protocol, Sequence

from acfqp import construction_k7_campaign_measurement_worker_v180r12r3r1 as core
from acfqp import construction_k7_campaign_measurement_supervisor_v180r12r3r1 as supervisor_core
from acfqp import construction_k7_domain_registry_extension_v180r12r3r1 as identity_domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PROFILE_KEY = "supervise_v180r12r3r1_campaign_measurement"
IO_CHUNK_BYTES = 64 * 1024
SUBJECT_RESULT_RUNTIME_BYTE_CAP = 768 * 1024
MAX_SUBJECT_BYTES = SUBJECT_RESULT_RUNTIME_BYTE_CAP
RENAME_NOREPLACE = 1
F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 0x0004)
F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
REQUIRED_SEAL_MASK = F_SEAL_GROW | F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_WRITE
MFD_CLOEXEC = getattr(os, "MFD_CLOEXEC", 0x0001)
MFD_ALLOW_SEALING = getattr(os, "MFD_ALLOW_SEALING", 0x0002)
PRECOMPILED_SOURCE_BUNDLE_FD = 240
INTERNAL_IPC_FD = 241
INTERNAL_MAC_KEY_FD = 242
INTERNAL_CONTEXT_FD = 243
REPOSITORY_ROOT_FD = 244
WORKER_CGROUP_FD = 245
WORKER_TERMINAL_STAGE_FD = 246
WORKER_VERIFICATION_STAGE_FD = 247
WORKER_SUBJECT_RESULT_FD = 248
OUTPUT_ROOT_PARTS = (".tmp", "exact-freeze", "v180r12r3r1_campaign_measurement")
FRAME_BYTE_CAP = 1024 * 1024
SOCK_SEQPACKET_BUFFER_REQUEST_BYTES = FRAME_BYTE_CAP
SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES = 2 * FRAME_BYTE_CAP
SNAPSHOT_BYTES_TRANSPORT_SCHEMA = (
    "acfqp.v180r12r3r1_snapshot_bytes_transport.v1"
)
SNAPSHOT_BYTES_TRANSPORT_BYTE_CAP = 512 * 1024
SNAPSHOT_BYTES_TRANSPORT_FIELDS = (
    "schema", "snapshot_receipt_id", "role", "byte_count", "sha256",
    "canonical_bytes_hex",
)
RUNTIME_FRAME_SCHEMA = "acfqp.v180r12r3r1_runtime_ipc_frame.v1"
EVENT_PROPOSAL_SCHEMA = "acfqp.v180r12r3r1_event_proposal.v1"
EVENT_ACK_SCHEMA = "acfqp.v180r12r3r1_event_ack.v1"
EVENT_PROPOSAL_FIELDS = frozenset(
    {
        "schema", "protocol_id", "authorization_id",
        "authorization_evidence_id", "attempt_id",
        "campaign_event_sequence", "phase", "actor_role", "event_kind",
        "operation_id", "payload", "evidence_documents",
    }
)
EVENT_ACK_FIELDS = frozenset(
    {
        "schema", "protocol_id", "authorization_id",
        "authorization_evidence_id", "attempt_id",
        "campaign_event_sequence", "event_id", "event_file_sha256",
        "durable_file_and_directory_fsync_complete",
    }
)
RUNTIME_FRAME_FIELDS = frozenset(
    {
        "schema", "channel_id", "direction", "sender_actor_role",
        "recipient_actor_role", "frame_type", "sequence", "body", "mac",
    }
)
SUPERVISOR_WORKER_HANDOFF_SCHEMA = (
    "acfqp.v180r12r3r1_supervisor_worker_handoff.v1"
)
SUPERVISOR_WORKER_HANDOFF_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_attempt_record_id",
    "execution_slot_id",
    "execution_nonce",
    "logical_occurrence_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "measurement_launch_attempt_id",
    "operation_manifest_id",
    "native_zero_source_manifest_id",
    "native_zero_import_inventory_id",
    "terminal_snapshot_document",
    "verification_snapshot_document",
    "terminal_memfd_stage_document",
    "verification_memfd_stage_document",
    "terminal_open_visibility_document",
    "verification_open_visibility_document",
    "stage_semantic_receipt_documents",
    "terminal_stage_binding",
    "verification_stage_binding",
    "subject_output_binding",
    "worker_birth_operation_id",
    "worker_birth_receipt_id",
    "worker_birth_document",
    "worker_birth_event_id",
    "worker_birth_event_sequence",
    "next_campaign_event_sequence",
    "one_shot_handoff",
)
STAGE_FD_BINDING_FIELDS = (
    "fd", "device", "inode", "byte_count", "memfd_stage_receipt_id",
    "open_visibility_receipt_id",
)
SUBJECT_OUTPUT_BINDING_FIELDS = (
    "fd", "device", "inode", "mode", "nlink", "initial_byte_count",
)
OBSERVER_SUPERVISOR_START_SCHEMA = (
    "acfqp.v180r12r3r1_observer_supervisor_start.v1"
)
OBSERVER_SUPERVISOR_START_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_measurement_execution_slot_id",
    "logical_occurrence_id",
    "execution_nonce",
    "campaign_attempt_record_id",
    "campaign_operation_manifest_id",
    "native_zero_source_manifest_id",
    "native_zero_import_inventory_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "measurement_launch_attempt_id",
    "cgroup_topology_receipt_id",
    "cgroup_topology_document",
    "supervisor_birth_operation_id",
    "supervisor_birth_receipt_id",
    "supervisor_birth_document",
    "supervisor_birth_event_id",
    "supervisor_birth_event_sequence",
    "next_campaign_event_sequence",
    "one_shot_start",
)
_VERIFIED_CONTEXT_KEYS = frozenset(
    {
        "schema", "target", "actor_role", "parent_actor_role", "protocol_id",
        "authorization_id", "authorization_evidence_id", "attempt_id",
        "campaign_measurement_execution_slot_id", "logical_occurrence_id",
        "execution_nonce",
        "prelaunch_materialization_terminal_id", "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
        "launch_operation_id", "manifest_sha256",
        "precompiled_source_bundle_sha256", "inherited_fd_roles",
        "target_payload", "parent_to_child_mac_key", "parent_context_mac",
        "context_consumed_once",
    }
)
_EXPECTED_FD_ROLES = (
    (PRECOMPILED_SOURCE_BUNDLE_FD, "PRECOMPILED_SOURCE_BUNDLE_MEMFD"),
    (INTERNAL_IPC_FD, "OBSERVER_SUPERVISOR_SOCK_SEQPACKET"),
    (INTERNAL_MAC_KEY_FD, "PARENT_TO_CHILD_MAC_KEY_MEMFD"),
    (INTERNAL_CONTEXT_FD, "INTERNAL_LAUNCH_CONTEXT_MEMFD"),
    (REPOSITORY_ROOT_FD, "REPOSITORY_ROOT_O_PATH_DIRECTORY"),
    (WORKER_CGROUP_FD, "WORKER_CGROUP_DIRECTORY"),
)


class V180R12R3R1SupervisorRuntimeError(RuntimeError):
    """The measured supervisor escaped its frozen effect boundary."""


def _fail(message: str) -> NoReturn:
    raise V180R12R3R1SupervisorRuntimeError(message)


def configure_seqpacket_pair_v180r12r3r1(
    parent: socket.socket, child: socket.socket
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Provision both authenticated IPC endpoints before clone or send."""

    if (
        type(parent) is not socket.socket
        or type(child) is not socket.socket
        or parent.type & socket.SOCK_SEQPACKET != socket.SOCK_SEQPACKET
        or child.type & socket.SOCK_SEQPACKET != socket.SOCK_SEQPACKET
    ):
        _fail("SUPERVISOR IPC buffer provisioning requires one seqpacket pair")
    observations: list[tuple[int, int]] = []
    for endpoint in (parent, child):
        endpoint.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
        )
        endpoint.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
        )
        observed = (
            endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF),
            endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF),
        )
        if (
            any(type(value) is not int for value in observed)
            or min(observed) < SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        ):
            _fail("SUPERVISOR seqpacket buffers do not cover the frame cap")
        observations.append(observed)
    return observations[0], observations[1]


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) in {tuple, list}:
        return [_thaw(item) for item in value]
    return value


def _content_id(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256 identity")
    return value


def _validate_evidence_document(
    value: Mapping[str, Any], *, expected_schema: str
) -> tuple[dict[str, Any], str]:
    contracts = {
        schema: (domain, identity_field)
        for _kind, schema, domain, identity_field in (
            *core.EVIDENCE_DOCUMENT_CONTRACT_ROWS,
            *supervisor_core.EVIDENCE_DOCUMENT_CONTRACT_ROWS,
        )
    }
    keysets = {
        schema: keyset
        for _kind, schema, _identity_field, keyset in (
            *core.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
            *supervisor_core.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
            *supervisor_core.ledger.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
        )
    }
    document = _thaw(value)
    if (
        type(document) is not dict
        or document.get("schema") != expected_schema
        or expected_schema not in contracts
        or expected_schema not in keysets
        or set(document) != keysets[expected_schema]
    ):
        _fail("handoff evidence schema or exact keyset changed")
    domain, identity_field = contracts[expected_schema]
    payload = dict(document)
    identity = payload.pop(identity_field, None)
    expected = core.domains.extension_content_id_v180r12r3r1e(domain, payload)
    if identity != expected:
        _fail("handoff evidence content identity changed")
    return document, identity


def _parts(relative_path: str) -> tuple[str, ...]:
    if type(relative_path) is not str:
        _fail("supervisor input path must be one relative string")
    path = PurePosixPath(relative_path)
    if path.is_absolute() or not path.parts or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        _fail("supervisor input path escaped its repository descriptor")
    return path.parts


def _memfd_create(name: str) -> int:
    native = getattr(os, "memfd_create", None)
    if callable(native):
        return native(name, MFD_CLOEXEC | MFD_ALLOW_SEALING)
    if os.uname().machine != "x86_64":
        _fail("memfd_create fallback only freezes the x86_64 syscall ABI")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    result = libc.syscall(319, name.encode("ascii"), MFD_CLOEXEC | MFD_ALLOW_SEALING)
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return int(result)


@dataclass(frozen=True, slots=True)
class StableInputReadV180R12R3R1:
    fact: core.StableCampaignInputFactV180R12R3R1
    returned_bytes: bytes = field(repr=False, compare=False)
    returned_chunk_byte_counts: tuple[int, ...]
    device: int
    inode: int
    mode: int
    link_count: int

    def __post_init__(self) -> None:
        if (
            type(self.fact) is not core.StableCampaignInputFactV180R12R3R1
            or type(self.returned_bytes) is not bytes
            or len(self.returned_bytes) != self.fact.byte_count
            or type(self.returned_chunk_byte_counts) is not tuple
            or not self.returned_chunk_byte_counts
            or any(
                type(value) is not int or value <= 0
                for value in self.returned_chunk_byte_counts
            )
            or sum(self.returned_chunk_byte_counts) != self.fact.byte_count
            or self.device <= 0
            or self.inode <= 0
            or not stat.S_ISREG(self.mode)
            or self.link_count != 1
        ):
            _fail("stable input read observation is malformed")


def read_frozen_input_openat_v180r12r3r1(
    repository_root_fd: int,
    fact: core.StableCampaignInputFactV180R12R3R1,
    *,
    chunk_bytes: int = IO_CHUNK_BYTES,
) -> StableInputReadV180R12R3R1:
    """Open and read one frozen source using only no-follow openat traversal."""

    if (
        type(repository_root_fd) is not int
        or repository_root_fd < 3
        or fact not in core.FROZEN_INPUT_FACTS_V180R12R3R1
        or type(chunk_bytes) is not int
        or chunk_bytes <= 0
        or chunk_bytes > 1024 * 1024
    ):
        _fail("stable input open arguments are malformed")
    current = os.dup(repository_root_fd)
    descriptor = -1
    try:
        parts = _parts(fact.relative_path)
        for part in parts[:-1]:
            successor = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=current,
            )
            os.close(current)
            current = successor
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=current,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size != fact.byte_count
        ):
            _fail("frozen input is not its exact stable regular-file denominator")
        chunks: list[bytes] = []
        counts: list[int] = []
        remaining = fact.byte_count
        while remaining:
            raw = os.read(descriptor, min(chunk_bytes, remaining))
            if not raw:
                _fail("frozen input read made no progress")
            chunks.append(raw)
            counts.append(len(raw))
            remaining -= len(raw)
        if os.read(descriptor, 1):
            _fail("frozen input grew beyond its preregistered denominator")
        after = os.fstat(descriptor)
        identity_fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size")
        if any(
            getattr(before, name) != getattr(after, name)
            for name in identity_fields
        ):
            _fail("frozen input identity changed during its exact read")
        return StableInputReadV180R12R3R1(
            fact,
            b"".join(chunks),
            tuple(counts),
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_nlink,
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(current)


@dataclass(frozen=True, slots=True)
class SealedMemfdStageV180R12R3R1:
    role: core.CampaignInputRoleV180R12R3R1
    supervisor_descriptor: int
    worker_source_descriptor: int
    returned_chunk_byte_counts: tuple[int, ...]
    byte_count: int
    device: int
    inode: int
    mode: int
    link_count: int
    observed_seal_mask: int
    supervisor_cloexec: bool
    worker_source_read_only: bool
    worker_source_cloexec: bool
    write_probe_errno: int

    def __post_init__(self) -> None:
        if (
            type(self.role) is not core.CampaignInputRoleV180R12R3R1
            or self.supervisor_descriptor < 3
            or self.worker_source_descriptor < 3
            or self.supervisor_descriptor == self.worker_source_descriptor
            or not self.returned_chunk_byte_counts
            or sum(self.returned_chunk_byte_counts) != self.byte_count
            or any(
                type(value) is not int or value <= 0
                for value in self.returned_chunk_byte_counts
            )
            or self.byte_count <= 0
            or self.device <= 0
            or self.inode <= 0
            or not stat.S_ISREG(self.mode)
            or stat.S_IMODE(self.mode) != 0o400
            or self.link_count != 0
            or self.observed_seal_mask != REQUIRED_SEAL_MASK
            or self.supervisor_cloexec is not True
            or self.worker_source_read_only is not True
            or self.worker_source_cloexec is not True
            or self.write_probe_errno != errno.EBADF
        ):
            _fail("sealed memfd stage observation is malformed")


def stage_sealed_memfd_v180r12r3r1(
    role: core.CampaignInputRoleV180R12R3R1,
    raw: bytes,
    *,
    chunk_bytes: int = IO_CHUNK_BYTES,
) -> SealedMemfdStageV180R12R3R1:
    """Create, fill, seal, and reopen one anonymous payload read-only."""

    if (
        type(role) is not core.CampaignInputRoleV180R12R3R1
        or type(raw) is not bytes
        or not raw
        or type(chunk_bytes) is not int
        or chunk_bytes <= 0
        or chunk_bytes > 1024 * 1024
    ):
        _fail("memfd stage arguments are malformed")
    supervisor_fd = _memfd_create(f"v180r12r3r1-{role.value.lower()}")
    worker_fd = -1
    try:
        counts: list[int] = []
        offset = 0
        while offset < len(raw):
            written = os.write(supervisor_fd, raw[offset : offset + chunk_bytes])
            if written <= 0:
                _fail("memfd stage write made no progress")
            counts.append(written)
            offset += written
        os.fchmod(supervisor_fd, 0o400)
        fcntl.fcntl(supervisor_fd, F_ADD_SEALS, REQUIRED_SEAL_MASK)
        seals = fcntl.fcntl(supervisor_fd, F_GET_SEALS)
        worker_fd = os.open(
            f"/proc/self/fd/{supervisor_fd}", os.O_RDONLY | os.O_CLOEXEC
        )
        supervisor_stat = os.fstat(supervisor_fd)
        worker_stat = os.fstat(worker_fd)
        try:
            os.write(worker_fd, b"x")
        except OSError as error:
            write_errno = error.errno
        else:  # pragma: no cover - a read-only descriptor cannot write.
            _fail("read-only worker memfd unexpectedly accepted a write")
        if (
            seals != REQUIRED_SEAL_MASK
            or supervisor_stat.st_dev != worker_stat.st_dev
            or supervisor_stat.st_ino != worker_stat.st_ino
            or supervisor_stat.st_size != len(raw)
            or worker_stat.st_size != len(raw)
            or stat.S_IMODE(supervisor_stat.st_mode) != 0o400
            or stat.S_IMODE(worker_stat.st_mode) != 0o400
            or fcntl.fcntl(supervisor_fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
            or fcntl.fcntl(worker_fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
            or fcntl.fcntl(worker_fd, fcntl.F_GETFL) & os.O_ACCMODE
            != os.O_RDONLY
        ):
            _fail("sealed memfd descriptors disagree after read-only reopen")
        return SealedMemfdStageV180R12R3R1(
            role,
            supervisor_fd,
            worker_fd,
            tuple(counts),
            len(raw),
            supervisor_stat.st_dev,
            supervisor_stat.st_ino,
            supervisor_stat.st_mode,
            supervisor_stat.st_nlink,
            seals,
            True,
            True,
            True,
            write_errno,
        )
    except BaseException:
        if worker_fd >= 0:
            os.close(worker_fd)
        os.close(supervisor_fd)
        raise


def close_sealed_stage_v180r12r3r1(stage: SealedMemfdStageV180R12R3R1) -> None:
    if type(stage) is not SealedMemfdStageV180R12R3R1:
        _fail("sealed stage close is mistyped")
    primary: BaseException | None = None
    for descriptor in (
        stage.worker_source_descriptor,
        stage.supervisor_descriptor,
    ):
        try:
            os.close(descriptor)
        except BaseException as error:
            if primary is None:
                primary = error
    if primary is not None:
        raise primary


def _close_descriptor_if_same_inode_v180r12r3r1(
    descriptor: int,
    *,
    device: int,
    inode: int,
) -> None:
    """Close an owned raw FD only while it still names its registered inode."""

    try:
        metadata = os.fstat(descriptor)
    except OSError as error:
        if error.errno == errno.EBADF:
            return
        raise
    if metadata.st_dev == device and metadata.st_ino == inode:
        os.close(descriptor)


@dataclass(frozen=True, slots=True)
class SubjectOutputHandleV180R12R3R1:
    directory_fd: int
    descriptor: int
    worker_source_descriptor: int
    temporary_name: str
    final_name: str
    device: int
    inode: int

    def __post_init__(self) -> None:
        try:
            supervisor_metadata = os.fstat(self.descriptor)
            worker_metadata = os.fstat(self.worker_source_descriptor)
            supervisor_access = (
                fcntl.fcntl(self.descriptor, fcntl.F_GETFL) & os.O_ACCMODE
            )
            worker_access = (
                fcntl.fcntl(self.worker_source_descriptor, fcntl.F_GETFL)
                & os.O_ACCMODE
            )
        except OSError as error:
            raise V180R12R3R1SupervisorRuntimeError(
                "subject output handle contains an invalid descriptor"
            ) from error
        if (
            self.directory_fd < 3
            or self.descriptor < 3
            or self.worker_source_descriptor < 3
            or len({self.directory_fd, self.descriptor, self.worker_source_descriptor}) != 3
            or any(
                type(name) is not str
                or not name
                or "/" in name
                or name in {".", ".."}
                for name in (self.temporary_name, self.final_name)
            )
            or self.temporary_name == self.final_name
            or self.device <= 0
            or self.inode <= 0
            or supervisor_metadata.st_dev != self.device
            or supervisor_metadata.st_ino != self.inode
            or worker_metadata.st_dev != self.device
            or worker_metadata.st_ino != self.inode
            or supervisor_access != os.O_RDONLY
            or worker_access != os.O_WRONLY
        ):
            _fail("subject output handle is malformed")


def preopen_subject_output_v180r12r3r1(
    directory_fd: int,
    *,
    temporary_name: str = "SUBJECT_RESULT.json.partial",
    final_name: str = "SUBJECT_RESULT.json",
) -> SubjectOutputHandleV180R12R3R1:
    """O_EXCL-create the only subject path before worker birth."""

    for name in (temporary_name, final_name):
        if (
            type(name) is not str
            or not name
            or "/" in name
            or name in {".", ".."}
        ):
            _fail("subject output basename is malformed")
    try:
        os.stat(final_name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        _fail("final subject result already exists")
    creator_descriptor = -1
    descriptor = -1
    worker_descriptor = -1
    try:
        creator_descriptor = os.open(
            temporary_name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory_fd,
        )
        os.fchmod(creator_descriptor, 0o600)
        metadata = os.fstat(creator_descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or metadata.st_size
        ):
            _fail("preopened subject path is not one empty regular file")
        descriptor = os.open(
            f"/proc/self/fd/{creator_descriptor}", os.O_RDONLY | os.O_CLOEXEC
        )
        worker_descriptor = os.open(
            f"/proc/self/fd/{creator_descriptor}", os.O_WRONLY | os.O_CLOEXEC
        )
        supervisor_metadata = os.fstat(descriptor)
        worker_metadata = os.fstat(worker_descriptor)
        if (
            supervisor_metadata.st_dev != metadata.st_dev
            or supervisor_metadata.st_ino != metadata.st_ino
            or worker_metadata.st_dev != metadata.st_dev
            or worker_metadata.st_ino != metadata.st_ino
            or fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE
            != os.O_RDONLY
            or fcntl.fcntl(worker_descriptor, fcntl.F_GETFL) & os.O_ACCMODE
            != os.O_WRONLY
        ):
            _fail("worker subject descriptor did not preserve exact inode/access")
        os.close(creator_descriptor)
        creator_descriptor = -1
        os.fsync(directory_fd)
        return SubjectOutputHandleV180R12R3R1(
            directory_fd,
            descriptor,
            worker_descriptor,
            temporary_name,
            final_name,
            metadata.st_dev,
            metadata.st_ino,
        )
    except BaseException:
        if worker_descriptor >= 0:
            os.close(worker_descriptor)
        if descriptor >= 0:
            os.close(descriptor)
        if creator_descriptor >= 0:
            os.close(creator_descriptor)
        raise


def close_subject_writer_before_readback_v180r12r3r1(
    handle: SubjectOutputHandleV180R12R3R1,
    *,
    expected_byte_count: int,
) -> None:
    """Close the final write-capable OFD after worker reap and before readback."""

    if (
        type(handle) is not SubjectOutputHandleV180R12R3R1
        or type(expected_byte_count) is not int
        or expected_byte_count <= 0
        or expected_byte_count > MAX_SUBJECT_BYTES
    ):
        _fail("subject writer close arguments are malformed")
    metadata = os.fstat(handle.worker_source_descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_dev != handle.device
        or metadata.st_ino != handle.inode
        or metadata.st_nlink != 1
        or metadata.st_size != expected_byte_count
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or fcntl.fcntl(handle.worker_source_descriptor, fcntl.F_GETFL)
        & os.O_ACCMODE
        != os.O_WRONLY
    ):
        _fail("subject worker writer changed before its unique close point")
    os.close(handle.worker_source_descriptor)
    try:
        os.fstat(handle.worker_source_descriptor)
    except OSError as error:
        if error.errno != errno.EBADF:
            raise
    else:
        _fail("subject worker writer remained open after close")

    # Closing the designated writer is not sufficient: an accidentally
    # duplicated O_WRONLY/O_RDWR OFD would retain mutation authority across
    # the readback/commit window.  Bound the procfs walk before inspecting
    # every same-inode alias and require the sole surviving alias to be the
    # supervisor's registered O_RDONLY descriptor.
    matching_readers: list[int] = []
    matching_writers: list[int] = []
    with os.scandir("/proc/self/fd") as entries:
        for index, entry in enumerate(entries):
            if index >= 4096:
                _fail("subject writer alias scan exceeded fd cap")
            if not entry.name.isdigit():
                continue
            descriptor = int(entry.name)
            try:
                candidate = os.fstat(descriptor)
            except OSError:
                continue
            if (
                candidate.st_dev != handle.device
                or candidate.st_ino != handle.inode
            ):
                continue
            try:
                access_mode = fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE
            except OSError:
                continue
            if access_mode == os.O_RDONLY:
                matching_readers.append(descriptor)
            elif access_mode in (os.O_WRONLY, os.O_RDWR):
                matching_writers.append(descriptor)
            else:
                _fail("subject alias exposed an unknown access mode")
    if matching_writers or matching_readers != [handle.descriptor]:
        _fail("subject write-capable alias survived the unique close point")


@dataclass(frozen=True, slots=True)
class SubjectCommitObservationV180R12R3R1:
    returned_bytes: bytes = field(repr=False, compare=False)
    returned_chunk_byte_counts: tuple[int, ...]
    device: int
    inode: int
    mode: int
    link_count: int
    file_fsync_complete: bool
    rename_noreplace_complete: bool
    directory_fsync_complete: bool

    def __post_init__(self) -> None:
        if (
            type(self.returned_bytes) is not bytes
            or not self.returned_bytes
            or len(self.returned_bytes) > MAX_SUBJECT_BYTES
            or type(self.returned_chunk_byte_counts) is not tuple
            or not self.returned_chunk_byte_counts
            or any(type(value) is not int or value <= 0 for value in self.returned_chunk_byte_counts)
            or sum(self.returned_chunk_byte_counts) != len(self.returned_bytes)
            or self.device <= 0
            or self.inode <= 0
            or not stat.S_ISREG(self.mode)
            or stat.S_IMODE(self.mode) != 0o400
            or self.link_count != 1
            or self.file_fsync_complete is not True
            or self.rename_noreplace_complete is not True
            or self.directory_fsync_complete is not True
        ):
            _fail("subject commit observation is malformed")


@dataclass(frozen=True, slots=True)
class SubjectReadbackEffectV180R12R3R1:
    returned_bytes: bytes = field(repr=False, compare=False)
    returned_chunk_byte_counts: tuple[int, ...]
    device: int
    inode: int
    mode: int
    link_count: int

    def __post_init__(self) -> None:
        if (
            type(self.returned_bytes) is not bytes
            or not self.returned_bytes
            or len(self.returned_bytes) > MAX_SUBJECT_BYTES
            or type(self.returned_chunk_byte_counts) is not tuple
            or not self.returned_chunk_byte_counts
            or sum(self.returned_chunk_byte_counts) != len(self.returned_bytes)
            or any(
                type(value) is not int or value <= 0
                for value in self.returned_chunk_byte_counts
            )
            or self.device <= 0
            or self.inode <= 0
            or not stat.S_ISREG(self.mode)
            or stat.S_IMODE(self.mode) != 0o400
            or self.link_count != 1
        ):
            _fail("subject readback effect observation is malformed")


def _rename_noreplace(
    old_directory_fd: int,
    old_name: str,
    new_directory_fd: int,
    new_name: str,
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        _fail("libc does not expose required renameat2")
    renameat2.argtypes = (
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        old_directory_fd,
        old_name.encode("utf-8"),
        new_directory_fd,
        new_name.encode("utf-8"),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def commit_subject_output_v180r12r3r1(
    handle: SubjectOutputHandleV180R12R3R1,
    expected_bytes: bytes,
    *,
    chunk_bytes: int = IO_CHUNK_BYTES,
) -> SubjectCommitObservationV180R12R3R1:
    """Read back, chmod/fsync, and renameat2(NOREPLACE) the exact subject."""

    close_subject_writer_before_readback_v180r12r3r1(
        handle, expected_byte_count=len(expected_bytes)
    )
    readback = readback_subject_output_v180r12r3r1(
        handle, expected_bytes, chunk_bytes=chunk_bytes
    )
    return commit_subject_after_readback_v180r12r3r1(handle, readback)


def readback_subject_output_v180r12r3r1(
    handle: SubjectOutputHandleV180R12R3R1,
    expected_bytes: bytes,
    *,
    chunk_bytes: int = IO_CHUNK_BYTES,
) -> SubjectReadbackEffectV180R12R3R1:
    """Freeze mode then perform only the registered COMMIT readback effect."""

    if (
        type(handle) is not SubjectOutputHandleV180R12R3R1
        or type(expected_bytes) is not bytes
        or not expected_bytes
        or len(expected_bytes) > MAX_SUBJECT_BYTES
    ):
        _fail("subject commit arguments are malformed")
    os.fchmod(handle.descriptor, 0o400)
    before = os.fstat(handle.descriptor)
    if (
        before.st_dev != handle.device
        or before.st_ino != handle.inode
        or before.st_nlink != 1
        or before.st_size != len(expected_bytes)
        or stat.S_IMODE(before.st_mode) != 0o400
        or fcntl.fcntl(handle.descriptor, fcntl.F_GETFL) & os.O_ACCMODE
        != os.O_RDONLY
    ):
        _fail("subject output identity changed before readback")
    chunks: list[bytes] = []
    counts: list[int] = []
    offset = 0
    while offset < len(expected_bytes):
        raw = os.pread(
            handle.descriptor,
            min(chunk_bytes, len(expected_bytes) - offset),
            offset,
        )
        if not raw:
            _fail("subject readback made no progress")
        chunks.append(raw)
        counts.append(len(raw))
        offset += len(raw)
    returned = b"".join(chunks)
    if returned != expected_bytes or os.pread(handle.descriptor, 1, len(returned)):
        _fail("subject readback bytes differ from the worker result")
    return SubjectReadbackEffectV180R12R3R1(
        returned, tuple(counts), before.st_dev, before.st_ino,
        before.st_mode, before.st_nlink,
    )


def commit_subject_after_readback_v180r12r3r1(
    handle: SubjectOutputHandleV180R12R3R1,
    readback: SubjectReadbackEffectV180R12R3R1,
) -> SubjectCommitObservationV180R12R3R1:
    """Commit a previously stable-read subject without another payload read."""

    if (
        type(handle) is not SubjectOutputHandleV180R12R3R1
        or type(readback) is not SubjectReadbackEffectV180R12R3R1
    ):
        _fail("subject post-readback commit arguments are malformed")
    before = os.fstat(handle.descriptor)
    if (
        before.st_dev != readback.device
        or before.st_ino != readback.inode
        or before.st_size != len(readback.returned_bytes)
        or before.st_nlink != readback.link_count
        or before.st_mode != readback.mode
        or fcntl.fcntl(handle.descriptor, fcntl.F_GETFL) & os.O_ACCMODE
        != os.O_RDONLY
    ):
        _fail("subject identity changed after its stable readback")
    os.fsync(handle.descriptor)
    committed = os.fstat(handle.descriptor)
    if (
        committed.st_dev != handle.device
        or committed.st_ino != handle.inode
        or committed.st_nlink != 1
        or stat.S_IMODE(committed.st_mode) != 0o400
    ):
        _fail("subject output metadata changed before commit")
    _rename_noreplace(
        handle.directory_fd,
        handle.temporary_name,
        handle.directory_fd,
        handle.final_name,
    )
    os.fsync(handle.directory_fd)
    return SubjectCommitObservationV180R12R3R1(
        readback.returned_bytes,
        readback.returned_chunk_byte_counts,
        committed.st_dev,
        committed.st_ino,
        committed.st_mode,
        committed.st_nlink,
        True,
        True,
        True,
    )


class SupervisorLifecycleBridgeV180R12R3R1(Protocol):
    def before_source_read(self, fact: core.StableCampaignInputFactV180R12R3R1) -> None: ...
    def after_source_read(
        self, observation: StableInputReadV180R12R3R1
    ) -> core.StableInputSnapshotReceiptV180R12R3R1: ...
    def before_stage_write(
        self, snapshot: core.StableInputSnapshotReceiptV180R12R3R1
    ) -> None: ...
    def after_stage_write(
        self,
        stage: SealedMemfdStageV180R12R3R1,
        snapshot: core.StableInputSnapshotReceiptV180R12R3R1,
    ) -> core.MemfdStageReceiptV180R12R3R1: ...
    def open_visibility(
        self,
        stage: SealedMemfdStageV180R12R3R1,
        receipt: core.MemfdStageReceiptV180R12R3R1,
    ) -> None: ...
    def before_operation(
        self,
        kind: core.SemanticOperationKindV180R12R3R1,
        label: str,
        phase: str,
        actor_role: str,
    ) -> None: ...
    def after_operation(self, result: core.ReplayOperationResultV180R12R3R1) -> None: ...


@dataclass(slots=True)
class _StageOperationHooksV180R12R3R1:
    bridge: SupervisorLifecycleBridgeV180R12R3R1
    open_label: str | None = None

    def before_operation(self, kind, label, phase, actor_role) -> None:
        if self.open_label is not None or phase != "STAGE" or actor_role != "SUPERVISOR":
            _fail("STAGE semantic operation role/order changed")
        self.bridge.before_operation(kind, label, phase, actor_role)
        self.open_label = label

    def after_operation(self, result) -> None:
        if self.open_label != result.label:
            _fail("STAGE semantic outcome crossed its ACKed intent")
        self.bridge.after_operation(result)
        self.open_label = None


@dataclass(frozen=True, slots=True)
class SupervisorStageEffectsV180R12R3R1:
    terminal_read: StableInputReadV180R12R3R1
    verification_read: StableInputReadV180R12R3R1
    terminal_snapshot: core.StableInputSnapshotReceiptV180R12R3R1
    verification_snapshot: core.StableInputSnapshotReceiptV180R12R3R1
    terminal_stage: SealedMemfdStageV180R12R3R1
    verification_stage: SealedMemfdStageV180R12R3R1
    result: core.StageMeasurementResultV180R12R3R1


def run_supervisor_stage_effects_v180r12r3r1(
    *,
    repository_root_fd: int,
    bridge: SupervisorLifecycleBridgeV180R12R3R1,
) -> SupervisorStageEffectsV180R12R3R1:
    """Run exact read/read, stage/stage, mount/mount, then 2/6 semantics."""

    facts = core.frozen_campaign_input_facts_v180r12r3r1()
    reads: list[StableInputReadV180R12R3R1] = []
    snapshots: list[core.StableInputSnapshotReceiptV180R12R3R1] = []
    for fact in facts:
        bridge.before_source_read(fact)
        observation = read_frozen_input_openat_v180r12r3r1(repository_root_fd, fact)
        snapshot = bridge.after_source_read(observation)
        if type(snapshot) is not core.StableInputSnapshotReceiptV180R12R3R1:
            _fail("observer returned a mistyped stable-input snapshot receipt")
        reads.append(observation)
        snapshots.append(snapshot)
    stages: list[SealedMemfdStageV180R12R3R1] = []
    receipts: list[core.MemfdStageReceiptV180R12R3R1] = []
    try:
        for read, snapshot in zip(reads, snapshots):
            bridge.before_stage_write(snapshot)
            stage = stage_sealed_memfd_v180r12r3r1(read.fact.role, read.returned_bytes)
            receipt = bridge.after_stage_write(stage, snapshot)
            if type(receipt) is not core.MemfdStageReceiptV180R12R3R1:
                _fail("observer returned a mistyped memfd stage receipt")
            stages.append(stage)
            receipts.append(receipt)
        for stage, receipt in zip(stages, receipts):
            bridge.open_visibility(stage, receipt)
        hooks = _StageOperationHooksV180R12R3R1(bridge)
        result = core.measure_campaign_inputs_stage_v180r12r3r1(
            reads[0].returned_bytes,
            reads[1].returned_bytes,
            terminal_stage_receipt=receipts[0],
            verification_stage_receipt=receipts[1],
            operation_observer=hooks,
        )
        if hooks.open_label is not None:
            _fail("STAGE semantic operation remained unacknowledged")
        return SupervisorStageEffectsV180R12R3R1(
            reads[0], reads[1], snapshots[0], snapshots[1],
            stages[0], stages[1], result
        )
    except BaseException:
        for stage in reversed(stages):
            try:
                close_sealed_stage_v180r12r3r1(stage)
            except OSError:
                pass
        raise


def validate_observer_supervisor_start_v180r12r3r1(
    value: Mapping[str, Any],
    *,
    verified_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the authenticated full START documents before STAGE."""

    context = _validate_verified_context_v180r12r3r1(verified_context)
    document = _thaw(value)
    if (
        type(document) is not dict
        or set(document) != set(OBSERVER_SUPERVISOR_START_FIELDS)
        or document.get("schema") != OBSERVER_SUPERVISOR_START_SCHEMA
    ):
        _fail("observer START schema or exact keyset changed")
    # ATTEMPT itself was event 0 and is not duplicated in START.  Its durable
    # ID is joined through the exact field and every later semantic receipt.
    _content_id(document["campaign_attempt_record_id"], "START attempt record ID")
    topology, topology_id = _validate_evidence_document(
        document["cgroup_topology_document"],
        expected_schema="acfqp.campaign_cgroup_topology_receipt.v180r12r3r1",
    )
    birth, birth_id = _validate_evidence_document(
        document["supervisor_birth_document"],
        expected_schema="acfqp.campaign_pidfd_birth_receipt.v180r12r3r1",
    )
    for field_name in (
        "protocol_id", "authorization_id", "authorization_evidence_id",
        "attempt_id", "campaign_measurement_execution_slot_id",
        "logical_occurrence_id", "execution_nonce",
        "campaign_operation_manifest_id",
        "native_zero_source_manifest_id", "native_zero_import_inventory_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256", "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id", "cgroup_topology_receipt_id",
        "supervisor_birth_operation_id", "supervisor_birth_receipt_id",
        "supervisor_birth_event_id",
    ):
        _content_id(document[field_name], "START " + field_name)
    worker_leaf = topology.get("worker_leaf")
    worker_metadata = os.fstat(WORKER_CGROUP_FD)
    worker_path = os.readlink(f"/proc/self/fd/{WORKER_CGROUP_FD}")
    if not (
        document["protocol_id"] == context["protocol_id"]
        and document["authorization_id"] == context["authorization_id"]
        and document["authorization_evidence_id"]
        == context["authorization_evidence_id"]
        and document["attempt_id"] == context["attempt_id"]
        and document["campaign_measurement_execution_slot_id"]
        == context["campaign_measurement_execution_slot_id"]
        and document["logical_occurrence_id"] == context["logical_occurrence_id"]
        and document["execution_nonce"] == context["execution_nonce"]
        and document["prelaunch_materialization_terminal_id"]
        == context["prelaunch_materialization_terminal_id"]
        and document["prelaunch_launch_manifest_sha256"]
        == context["manifest_sha256"]
        and document["prelaunch_launch_rule_id"]
        == context["prelaunch_launch_rule_id"]
        and document["measurement_launch_attempt_id"]
        == context["measurement_launch_attempt_id"]
        and document["cgroup_topology_receipt_id"] == topology_id
        and document["supervisor_birth_receipt_id"] == birth_id
        and document["supervisor_birth_operation_id"]
        == context["launch_operation_id"]
        == birth.get("operation_id")
        and birth.get("attempt_id") == context["attempt_id"]
        and birth.get("process_role") == "SUPERVISOR"
        and birth.get("cgroup_topology_receipt_id") == topology_id
        and type(worker_leaf) is dict
        and worker_leaf.get("role") == "WORKER"
        and worker_leaf.get("path") == worker_path
        and worker_leaf.get("device") == worker_metadata.st_dev
        and worker_leaf.get("inode") == worker_metadata.st_ino
        and document["supervisor_birth_event_sequence"] == 2
        and document["next_campaign_event_sequence"] == 3
        and document["one_shot_start"] is True
    ):
        _fail("observer START context/topology/birth/FD join changed")
    return document


def build_supervisor_worker_handoff_v180r12r3r1(
    *,
    start_document: Mapping[str, Any],
    stage_effects: SupervisorStageEffectsV180R12R3R1,
    terminal_open_visibility_document: Mapping[str, Any],
    verification_open_visibility_document: Mapping[str, Any],
    stage_semantic_receipt_documents: Sequence[Mapping[str, Any]],
    subject_output: SubjectOutputHandleV180R12R3R1,
    worker_birth_document: Mapping[str, Any],
    worker_birth_event_id: str,
    worker_birth_event_sequence: int,
    next_campaign_event_sequence: int,
) -> dict[str, Any]:
    """Build the only full causal handoff accepted by the WORKER."""

    if (
        type(stage_effects) is not SupervisorStageEffectsV180R12R3R1
        or type(subject_output) is not SubjectOutputHandleV180R12R3R1
    ):
        _fail("worker handoff effect state is mistyped")
    start = _thaw(start_document)
    if (
        type(start) is not dict
        or set(start) != set(OBSERVER_SUPERVISOR_START_FIELDS)
        or start.get("schema") != OBSERVER_SUPERVISOR_START_SCHEMA
    ):
        _fail("worker handoff requires one validated START body")
    snapshots = (
        stage_effects.terminal_snapshot.to_document(),
        stage_effects.verification_snapshot.to_document(),
    )
    memfds = (
        stage_effects.result.terminal_stage_receipt.to_document(),
        stage_effects.result.verification_stage_receipt.to_document(),
    )
    visibility_values = (
        terminal_open_visibility_document,
        verification_open_visibility_document,
    )
    expected_roles = ("TERMINAL", "VERIFICATION")
    validated_snapshots: list[dict[str, Any]] = []
    validated_memfds: list[dict[str, Any]] = []
    validated_visibility: list[dict[str, Any]] = []
    for index, role in enumerate(expected_roles):
        snapshot, snapshot_id = _validate_evidence_document(
            snapshots[index],
            expected_schema="acfqp.campaign_stable_input_snapshot.v180r12r3r1",
        )
        memfd, memfd_id = _validate_evidence_document(
            memfds[index],
            expected_schema="acfqp.campaign_memfd_stage_receipt.v180r12r3r1",
        )
        visibility, visibility_id = _validate_evidence_document(
            visibility_values[index],
            expected_schema="acfqp.campaign_fd_visibility_receipt.v180r12r3r1",
        )
        expected_worker_fd = (
            WORKER_TERMINAL_STAGE_FD
            if index == 0
            else WORKER_VERIFICATION_STAGE_FD
        )
        stage = (
            stage_effects.terminal_stage
            if index == 0
            else stage_effects.verification_stage
        )
        metadata = os.fstat(stage.worker_source_descriptor)
        worker_flags = fcntl.fcntl(stage.worker_source_descriptor, fcntl.F_GETFL)
        worker_fd_flags = fcntl.fcntl(stage.worker_source_descriptor, fcntl.F_GETFD)
        if not (
            snapshot.get("role") == role
            and memfd.get("role") == role
            and memfd.get("input_snapshot_id") == snapshot_id
            and memfd.get("worker_fd") == expected_worker_fd
            and memfd.get("device") == metadata.st_dev
            and memfd.get("inode") == metadata.st_ino
            and memfd.get("byte_count") == metadata.st_size
            and worker_flags & os.O_ACCMODE == os.O_RDONLY
            and bool(worker_fd_flags & fcntl.FD_CLOEXEC)
            and fcntl.fcntl(stage.worker_source_descriptor, F_GET_SEALS)
            == REQUIRED_SEAL_MASK
            and os.lseek(stage.worker_source_descriptor, 0, os.SEEK_CUR) == 0
            and visibility.get("attempt_id") == start["attempt_id"]
            and visibility.get("stage_receipt_id") == memfd_id
            and visibility.get("holder_process_birth_receipt_id")
            == start["supervisor_birth_receipt_id"]
            and visibility.get("holder_role") == "SUPERVISOR"
            and visibility.get("role") == role
            and visibility.get("state") == "OPEN"
            and visibility.get("designated_worker_fd") == expected_worker_fd
            and visibility.get("expected_device") == metadata.st_dev
            and visibility.get("expected_inode") == metadata.st_ino
            and visibility.get("visible") is True
            and visibility.get("read_only") is True
        ):
            _fail("worker handoff snapshot/memfd/visibility causal join changed")
        validated_snapshots.append(snapshot)
        validated_memfds.append(memfd)
        validated_visibility.append(visibility)
        _content_id(visibility_id, "handoff visibility receipt ID")

    semantic_documents: list[dict[str, Any]] = []
    expected_labels = (
        *core.SEMANTIC_HASH_OPERATION_LABELS[:2],
        *core.INTEGRITY_CHECK_OPERATION_LABELS[:6],
    )
    if len(stage_semantic_receipt_documents) != len(expected_labels):
        _fail("worker handoff STAGE semantic receipt count changed")
    for supplied, label in zip(stage_semantic_receipt_documents, expected_labels):
        semantic, _semantic_id = _validate_evidence_document(
            supplied,
            expected_schema="acfqp.campaign_semantic_operation_receipt.v180r12r3r1",
        )
        if not (
            semantic.get("attempt_id") == start["attempt_id"]
            and semantic.get("label") == label
            and semantic.get("operation_manifest_id")
            == start["campaign_operation_manifest_id"]
            and semantic.get("native_zero_source_manifest_id")
            == start["native_zero_source_manifest_id"]
            and semantic.get("native_zero_import_inventory_id")
            == start["native_zero_import_inventory_id"]
            and semantic.get("evidence_subject_id")
            == start["campaign_attempt_record_id"]
        ):
            _fail("worker handoff STAGE semantic receipt join changed")
        semantic_documents.append(semantic)

    birth, birth_id = _validate_evidence_document(
        worker_birth_document,
        expected_schema="acfqp.campaign_pidfd_birth_receipt.v180r12r3r1",
    )
    schedule = supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r3r1(
        start["attempt_id"]
    )
    if (
        type(worker_birth_event_sequence) is not int
        or worker_birth_event_sequence < 1
        or worker_birth_event_sequence >= len(schedule)
        or schedule[worker_birth_event_sequence].event_kind
        != "PROCESS_BIRTH_OUTCOME"
        or schedule[worker_birth_event_sequence].actor_role != "SUPERVISOR"
        or schedule[worker_birth_event_sequence].phase != "WORKER"
        or schedule[worker_birth_event_sequence].operation_id
        != birth.get("operation_id")
        or birth.get("attempt_id") != start["attempt_id"]
        or birth.get("process_role") != "WORKER"
        or birth.get("cgroup_topology_receipt_id")
        != start["cgroup_topology_receipt_id"]
        or next_campaign_event_sequence != worker_birth_event_sequence + 1
    ):
        _fail("worker handoff birth event differs from exact schedule")
    _content_id(worker_birth_event_id, "worker birth event ID")
    subject_metadata = os.fstat(subject_output.descriptor)
    subject_worker_metadata = os.fstat(subject_output.worker_source_descriptor)
    if not (
        subject_metadata.st_dev == subject_output.device
        and subject_metadata.st_ino == subject_output.inode
        and subject_metadata.st_nlink == 1
        and subject_metadata.st_size == 0
        and stat.S_IMODE(subject_metadata.st_mode) == 0o600
        and fcntl.fcntl(subject_output.descriptor, fcntl.F_GETFL)
        & os.O_ACCMODE
        == os.O_RDONLY
        and subject_worker_metadata.st_dev == subject_output.device
        and subject_worker_metadata.st_ino == subject_output.inode
        and fcntl.fcntl(subject_output.worker_source_descriptor, fcntl.F_GETFL)
        & os.O_ACCMODE
        == os.O_WRONLY
    ):
        _fail("worker handoff subject output identity changed")
    stage_bindings = tuple(
        {
            "fd": expected_fd,
            "device": memfd["device"],
            "inode": memfd["inode"],
            "byte_count": memfd["byte_count"],
            "memfd_stage_receipt_id": memfd["memfd_stage_receipt_id"],
            "open_visibility_receipt_id": visibility["fd_visibility_receipt_id"],
        }
        for expected_fd, memfd, visibility in zip(
            (WORKER_TERMINAL_STAGE_FD, WORKER_VERIFICATION_STAGE_FD),
            validated_memfds,
            validated_visibility,
        )
    )
    subject_binding = {
        "fd": WORKER_SUBJECT_RESULT_FD,
        "device": subject_metadata.st_dev,
        "inode": subject_metadata.st_ino,
        "mode": subject_metadata.st_mode,
        "nlink": subject_metadata.st_nlink,
        "initial_byte_count": subject_metadata.st_size,
    }
    document = {
        "schema": SUPERVISOR_WORKER_HANDOFF_SCHEMA,
        "protocol_id": start["protocol_id"],
        "authorization_id": start["authorization_id"],
        "authorization_evidence_id": start["authorization_evidence_id"],
        "attempt_id": start["attempt_id"],
        "campaign_attempt_record_id": start["campaign_attempt_record_id"],
        "execution_slot_id": start["campaign_measurement_execution_slot_id"],
        "execution_nonce": start["execution_nonce"],
        "logical_occurrence_id": start["logical_occurrence_id"],
        "prelaunch_materialization_terminal_id": (
            start["prelaunch_materialization_terminal_id"]
        ),
        "prelaunch_launch_manifest_sha256": (
            start["prelaunch_launch_manifest_sha256"]
        ),
        "prelaunch_launch_rule_id": start["prelaunch_launch_rule_id"],
        "measurement_launch_attempt_id": start["measurement_launch_attempt_id"],
        "operation_manifest_id": start["campaign_operation_manifest_id"],
        "native_zero_source_manifest_id": start["native_zero_source_manifest_id"],
        "native_zero_import_inventory_id": (
            start["native_zero_import_inventory_id"]
        ),
        "terminal_snapshot_document": validated_snapshots[0],
        "verification_snapshot_document": validated_snapshots[1],
        "terminal_memfd_stage_document": validated_memfds[0],
        "verification_memfd_stage_document": validated_memfds[1],
        "terminal_open_visibility_document": validated_visibility[0],
        "verification_open_visibility_document": validated_visibility[1],
        "stage_semantic_receipt_documents": semantic_documents,
        "terminal_stage_binding": stage_bindings[0],
        "verification_stage_binding": stage_bindings[1],
        "subject_output_binding": subject_binding,
        "worker_birth_operation_id": birth["operation_id"],
        "worker_birth_receipt_id": birth_id,
        "worker_birth_document": birth,
        "worker_birth_event_id": worker_birth_event_id,
        "worker_birth_event_sequence": worker_birth_event_sequence,
        "next_campaign_event_sequence": next_campaign_event_sequence,
        "one_shot_handoff": True,
    }
    if tuple(document) != SUPERVISOR_WORKER_HANDOFF_FIELDS:
        raise AssertionError("worker handoff construction field order changed")
    return document


def _validate_verified_context_v180r12r3r1(
    value: Mapping[str, Any],
) -> types.MappingProxyType:
    if type(value) is not types.MappingProxyType or set(value) != _VERIFIED_CONTEXT_KEYS:
        _fail("supervisor requires the exact bootstrap-verified immutable context")
    ids = (
        value["protocol_id"], value["authorization_id"],
        value["authorization_evidence_id"], value["attempt_id"],
        value["campaign_measurement_execution_slot_id"],
        value["logical_occurrence_id"], value["execution_nonce"],
        value["prelaunch_materialization_terminal_id"],
        value["prelaunch_launch_rule_id"],
        value["measurement_launch_attempt_id"], value["launch_operation_id"],
        value["manifest_sha256"], value["precompiled_source_bundle_sha256"],
        value["parent_context_mac"],
    )
    target_payload = value["target_payload"]
    expected_attempt_id = identity_domains.derive_campaign_measurement_attempt_id_v180r12r3r1(
        protocol_id=value["protocol_id"],
        authorization_id=value["authorization_id"],
        authorization_evidence_id=value["authorization_evidence_id"],
        campaign_measurement_execution_slot_id=value[
            "campaign_measurement_execution_slot_id"
        ],
        logical_occurrence_id=value["logical_occurrence_id"],
        execution_nonce=value["execution_nonce"],
    )
    expected_launch_operation_id = (
        supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r3r1(
            expected_attempt_id
        )[1].operation_id
    )
    if not (
        value["schema"] == "acfqp.v180r12r3r1_verified_internal_launch_context.v1"
        and value["target"] == "supervisor"
        and value["actor_role"] == "SUPERVISOR"
        and value["parent_actor_role"] == "OBSERVER"
        and value["attempt_id"] == expected_attempt_id
        and value["launch_operation_id"] == expected_launch_operation_id
        and all(type(item) is str and len(item) == 64 and all(char in "0123456789abcdef" for char in item) for item in ids)
        and value["inherited_fd_roles"] == _EXPECTED_FD_ROLES
        and type(target_payload) is types.MappingProxyType
        and dict(target_payload)
        == {"repository_root_fd": REPOSITORY_ROOT_FD, "worker_cgroup_fd": WORKER_CGROUP_FD}
        and type(value["parent_to_child_mac_key"]) is bytes
        and len(value["parent_to_child_mac_key"]) == 32
        and value["context_consumed_once"] is True
    ):
        _fail("supervisor verified context role/identity/MAC binding changed")
    for closed in (INTERNAL_MAC_KEY_FD, INTERNAL_CONTEXT_FD):
        try:
            os.fstat(closed)
        except OSError as error:
            if error.errno != errno.EBADF:
                raise
        else:
            _fail("bootstrap key/context FD remained open at supervisor dispatch")
    for descriptor in (
        PRECOMPILED_SOURCE_BUNDLE_FD, INTERNAL_IPC_FD,
        REPOSITORY_ROOT_FD, WORKER_CGROUP_FD,
    ):
        if os.get_inheritable(descriptor):
            _fail("supervisor operational FD is not CLOEXEC at runner dispatch")
    duplicate = socket.fromfd(INTERNAL_IPC_FD, socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        if duplicate.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_SEQPACKET:
            _fail("supervisor IPC descriptor is not SOCK_SEQPACKET")
    finally:
        duplicate.close()
    bundle = os.fstat(PRECOMPILED_SOURCE_BUNDLE_FD)
    bundle_flags = fcntl.fcntl(PRECOMPILED_SOURCE_BUNDLE_FD, fcntl.F_GETFL)
    if not (
        stat.S_ISREG(bundle.st_mode)
        and bundle.st_nlink == 0
        and bundle.st_size > 0
        and stat.S_IMODE(bundle.st_mode) == 0o400
        and bundle_flags & os.O_ACCMODE == os.O_RDONLY
        and fcntl.fcntl(PRECOMPILED_SOURCE_BUNDLE_FD, F_GET_SEALS)
        == REQUIRED_SEAL_MASK
    ):
        _fail("supervisor precompiled bundle FD changed")
    repo_stat = os.fstat(REPOSITORY_ROOT_FD)
    worker_cgroup_stat = os.fstat(WORKER_CGROUP_FD)
    if (
        not stat.S_ISDIR(repo_stat.st_mode)
        or fcntl.fcntl(REPOSITORY_ROOT_FD, fcntl.F_GETFL) & os.O_PATH != os.O_PATH
        or not stat.S_ISDIR(worker_cgroup_stat.st_mode)
        or fcntl.fcntl(WORKER_CGROUP_FD, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY
    ):
        _fail("supervisor inherited directory FD roles changed")
    return value


class _AuthenticatedSupervisorChannelV180R12R3R1:
    """Exact SUPERVISOR endpoint for either frozen runtime channel."""

    def __init__(
        self,
        channel: socket.socket,
        secret: bytes,
        context: Mapping[str, Any],
        *,
        parent_actor_role: str,
        child_actor_role: str,
        channel_id: str,
    ) -> None:
        if (
            type(secret) is not bytes
            or len(secret) != 32
            or channel.type & socket.SOCK_SEQPACKET != socket.SOCK_SEQPACKET
            or (parent_actor_role, child_actor_role)
            not in {("OBSERVER", "SUPERVISOR"), ("SUPERVISOR", "WORKER")}
        ):
            _fail("SUPERVISOR authenticated channel arguments changed")
        _content_id(channel_id, "SUPERVISOR channel ID")
        schedule = supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r3r1(
            context["attempt_id"]
        )
        expected_channel_id = next(
            row.operation_id
            for row in schedule
            if row.event_kind == "PROCESS_BIRTH_INTENT"
            and row.actor_role == parent_actor_role
            and row.phase == (
                "STAGE" if child_actor_role == "SUPERVISOR" else "WORKER"
            )
        )
        if channel_id != expected_channel_id:
            _fail("SUPERVISOR channel ID differs from exact birth operation")
        self.channel = channel
        self.context = context
        self.parent_actor_role = parent_actor_role
        self.child_actor_role = child_actor_role
        self.local_actor_role = "SUPERVISOR"
        self.remote_actor_role = (
            child_actor_role
            if self.local_actor_role == parent_actor_role
            else parent_actor_role
        )
        self.is_parent = self.local_actor_role == parent_actor_role
        self.channel_id = channel_id
        self.send_direction = (
            "PARENT_TO_CHILD" if self.is_parent else "CHILD_TO_PARENT"
        )
        self.receive_direction = (
            "CHILD_TO_PARENT" if self.is_parent else "PARENT_TO_CHILD"
        )
        self.send_key = self._direction_key(secret, self.send_direction)
        self.receive_key = self._direction_key(secret, self.receive_direction)
        self.next_send_sequence = 0
        self.next_receive_sequence = 0

    def _direction_key(self, secret: bytes, direction: str) -> bytes:
        document = {
            "schema": "acfqp.v180r12r3r1_runtime_channel_key_context.v1",
            "channel_id": self.channel_id,
            "protocol_id": self.context["protocol_id"],
            "authorization_id": self.context["authorization_id"],
            "authorization_evidence_id": self.context[
                "authorization_evidence_id"
            ],
            "attempt_id": self.context["attempt_id"],
            "parent_actor_role": self.parent_actor_role,
            "child_actor_role": self.child_actor_role,
            "direction": direction,
        }
        return hashlib.blake2s(
            canonical_json_bytes(document), key=secret, digest_size=32
        ).digest()

    def _common_body(self, body: Mapping[str, Any]) -> bool:
        return (
            body.get("protocol_id") == self.context["protocol_id"]
            and body.get("authorization_id") == self.context["authorization_id"]
            and body.get("authorization_evidence_id")
            == self.context["authorization_evidence_id"]
            and body.get("attempt_id") == self.context["attempt_id"]
        )

    def _validate_body(
        self, frame_type: str, body: Mapping[str, Any], *, receiving: bool
    ) -> dict[str, Any]:
        document = _thaw(body)
        if type(document) is not dict or not self._common_body(document):
            _fail("SUPERVISOR authenticated body context changed")
        if frame_type == "SUPERVISOR_START":
            if not (
                receiving
                and not self.is_parent
                and self.next_receive_sequence == 0
                and set(document) == set(OBSERVER_SUPERVISOR_START_FIELDS)
                and document.get("schema") == OBSERVER_SUPERVISOR_START_SCHEMA
                and document.get("one_shot_start") is True
            ):
                _fail("SUPERVISOR START transition changed")
        elif frame_type == "WORKER_HANDOFF":
            if not (
                not receiving
                and self.is_parent
                and self.next_send_sequence == 0
                and set(document) == set(SUPERVISOR_WORKER_HANDOFF_FIELDS)
                and document.get("schema") == SUPERVISOR_WORKER_HANDOFF_SCHEMA
                and document.get("one_shot_handoff") is True
            ):
                _fail("SUPERVISOR HANDOFF transition changed")
        elif frame_type == "EVENT_PROPOSAL":
            if not (
                set(document) == EVENT_PROPOSAL_FIELDS
                and document.get("schema") == EVENT_PROPOSAL_SCHEMA
                and type(document.get("campaign_event_sequence")) is int
                and type(document.get("phase")) is str
                and type(document.get("actor_role")) is str
                and type(document.get("event_kind")) is str
                and type(document.get("operation_id")) is str
                and type(document.get("payload")) is dict
                and set(document["payload"])
                == {"evidence_id", "outcome_code", "measured_value", "auxiliary_values"}
                and document["payload"].get("auxiliary_values") == []
                and type(document.get("evidence_documents")) is list
                and all(type(row) is dict for row in document["evidence_documents"])
                and ((receiving and self.is_parent) or (not receiving and not self.is_parent))
            ):
                _fail("SUPERVISOR proposal body changed")
            _content_id(document["operation_id"], "SUPERVISOR proposal operation ID")
        elif frame_type == "EVENT_ACK":
            if not (
                set(document) == EVENT_ACK_FIELDS
                and document.get("schema") == EVENT_ACK_SCHEMA
                and type(document.get("campaign_event_sequence")) is int
                and document.get("durable_file_and_directory_fsync_complete")
                is True
                and ((receiving and not self.is_parent) or (not receiving and self.is_parent))
            ):
                _fail("SUPERVISOR event ACK body changed")
            _content_id(document.get("event_id"), "SUPERVISOR ACK event ID")
            _content_id(
                document.get("event_file_sha256"), "SUPERVISOR ACK event SHA"
            )
        else:
            _fail("SUPERVISOR authenticated frame type is unregistered")
        return document

    def send(self, frame_type: str, body: Mapping[str, Any]) -> None:
        sequence = self.next_send_sequence
        if self.send_direction == "PARENT_TO_CHILD":
            expected = "WORKER_HANDOFF" if sequence == 0 else "EVENT_ACK"
        else:
            expected = "EVENT_PROPOSAL"
        if frame_type != expected:
            _fail("SUPERVISOR send transition changed")
        document = self._validate_body(frame_type, body, receiving=False)
        unsigned = {
            "schema": RUNTIME_FRAME_SCHEMA,
            "channel_id": self.channel_id,
            "direction": self.send_direction,
            "sender_actor_role": self.local_actor_role,
            "recipient_actor_role": self.remote_actor_role,
            "frame_type": frame_type,
            "sequence": sequence,
            "body": document,
        }
        mac = hashlib.blake2s(
            canonical_json_bytes(unsigned), key=self.send_key, digest_size=32
        ).hexdigest()
        raw = canonical_json_bytes({**unsigned, "mac": mac})
        if len(raw) > FRAME_BYTE_CAP:
            _fail("SUPERVISOR authenticated frame exceeded its byte cap")
        if self.channel.send(raw) != len(raw):
            _fail("SUPERVISOR authenticated seqpacket write was partial")
        self.next_send_sequence += 1

    def receive(self, *, allow_eof: bool = False) -> tuple[str, dict[str, Any]] | None:
        raw, ancillary, flags, address = self.channel.recvmsg(FRAME_BYTE_CAP + 1)
        if not raw and not ancillary and flags == 0 and address in (None, "", b""):
            if allow_eof:
                return None
            _fail("SUPERVISOR authenticated channel ended early")
        if (
            flags != 0
            or ancillary
            or address not in (None, "", b"")
            or not raw
            or len(raw) > FRAME_BYTE_CAP
        ):
            _fail("SUPERVISOR frame carried flags, ancillary, address, or bad size")
        try:
            frame = loads_canonical_json(raw)
        except (TypeError, ValueError) as error:
            raise V180R12R3R1SupervisorRuntimeError(
                "SUPERVISOR IPC frame is not canonical JSON"
            ) from error
        if (
            type(frame) is not dict
            or canonical_json_bytes(frame) != raw
            or set(frame) != RUNTIME_FRAME_FIELDS
        ):
            _fail("SUPERVISOR IPC frame canonical keyset changed")
        unsigned_fields = (
            "schema", "channel_id", "direction", "sender_actor_role",
            "recipient_actor_role", "frame_type", "sequence", "body",
        )
        unsigned = {name: frame[name] for name in unsigned_fields}
        expected_mac = hashlib.blake2s(
            canonical_json_bytes(unsigned), key=self.receive_key, digest_size=32
        ).hexdigest()
        expected_first = "SUPERVISOR_START" if not self.is_parent else "EVENT_PROPOSAL"
        expected_later = "EVENT_ACK" if not self.is_parent else "EVENT_PROPOSAL"
        expected_type = expected_first if self.next_receive_sequence == 0 else expected_later
        if not (
            frame["schema"] == RUNTIME_FRAME_SCHEMA
            and frame["channel_id"] == self.channel_id
            and frame["direction"] == self.receive_direction
            and frame["sender_actor_role"] == self.remote_actor_role
            and frame["recipient_actor_role"] == self.local_actor_role
            and frame["frame_type"] == expected_type
            and frame["sequence"] == self.next_receive_sequence
            and type(frame["body"]) is dict
            and hmac.compare_digest(frame.get("mac", ""), expected_mac)
        ):
            _fail("SUPERVISOR IPC MAC, role, channel, or sequence changed")
        body = self._validate_body(frame["frame_type"], frame["body"], receiving=True)
        self.next_receive_sequence += 1
        return frame["frame_type"], body


@dataclass(slots=True)
class _AuthenticatedSupervisorBridgeV180R12R3R1:
    channel: _AuthenticatedSupervisorChannelV180R12R3R1
    start: Mapping[str, Any]
    campaign_event_sequence: int
    open_event: tuple[str, str] | None = None
    visibility_documents: list[dict[str, Any]] = field(default_factory=list)
    semantic_documents: list[dict[str, Any]] = field(default_factory=list)
    last_ack: dict[str, Any] | None = None
    visible_byte_count: int = 0

    def _planned(self):
        schedule = supervisor_core.ledger.build_campaign_success_event_schedule_v180r12r3r1(
            self.start["attempt_id"]
        )
        if self.campaign_event_sequence >= len(schedule):
            _fail("SUPERVISOR emitted beyond the exact success schedule")
        return schedule[self.campaign_event_sequence]

    def _propose_and_ack(
        self,
        *,
        event_kind: str,
        evidence_documents: Sequence[Mapping[str, Any]] = (),
        measured_value: int | None = None,
        expected_actor_role: str = "SUPERVISOR",
    ) -> dict[str, Any]:
        planned = self._planned()
        rows = [_thaw(row) for row in evidence_documents]
        direct_id = None
        if rows:
            schema = rows[0].get("schema")
            if type(schema) is not str:
                _fail("SUPERVISOR direct evidence schema is absent")
            _direct, direct_id = _validate_evidence_document(
                rows[0], expected_schema=schema
            )
        if not (
            planned.event_kind == event_kind
            and planned.actor_role == expected_actor_role
        ):
            _fail("SUPERVISOR callback differs from exact next event")
        payload = supervisor_core.campaign_event_payload_v180r12r3r1(
            event_kind=event_kind,
            evidence_id=direct_id,
            measured_value=measured_value,
            auxiliary_values=(),
        )
        body = {
            "schema": EVENT_PROPOSAL_SCHEMA,
            "protocol_id": self.start["protocol_id"],
            "authorization_id": self.start["authorization_id"],
            "authorization_evidence_id": self.start["authorization_evidence_id"],
            "attempt_id": self.start["attempt_id"],
            "campaign_event_sequence": self.campaign_event_sequence,
            "phase": planned.phase,
            "actor_role": planned.actor_role,
            "event_kind": planned.event_kind,
            "operation_id": planned.operation_id,
            "payload": payload,
            "evidence_documents": rows,
        }
        self.channel.send("EVENT_PROPOSAL", body)
        received = self.channel.receive()
        if received is None:
            _fail("SUPERVISOR observer channel ended before ACK")
        frame_type, ack = received
        if not (
            frame_type == "EVENT_ACK"
            and ack["campaign_event_sequence"] == self.campaign_event_sequence
        ):
            _fail("SUPERVISOR observer ACK crossed its event")
        self.campaign_event_sequence += 1
        self.last_ack = ack
        return ack

    def _intent(self, event_kind: str) -> None:
        if self.open_event is not None:
            _fail("SUPERVISOR overlapped two registered operations")
        planned = self._planned()
        self.open_event = (event_kind.removesuffix("_INTENT"), planned.operation_id)
        self._propose_and_ack(event_kind=event_kind)

    def _outcome(
        self,
        event_kind: str,
        direct_document: Mapping[str, Any],
        *,
        measured_value: int,
        supporting: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        planned = self._planned()
        if self.open_event != (
            event_kind.removesuffix("_OUTCOME"), planned.operation_id
        ):
            _fail("SUPERVISOR outcome crossed its ACKed intent")
        self._propose_and_ack(
            event_kind=event_kind,
            evidence_documents=(direct_document, *supporting),
            measured_value=measured_value,
        )
        self.open_event = None

    def before_source_read(self, fact: core.StableCampaignInputFactV180R12R3R1) -> None:
        planned = self._planned()
        expected_ordinal = (
            0 if fact.role is core.CampaignInputRoleV180R12R3R1.TERMINAL else 1
        )
        expected_operation = next(
            row.operation_id
            for row in supervisor_core.build_campaign_operation_schedule_v180r12r3r1(
                self.start["attempt_id"]
            )
            if row.slot == "INPUT_READ"
            and row.family == "FROZEN_SOURCE"
            and row.ordinal == expected_ordinal
        )
        if planned.operation_id != expected_operation:
            _fail("SUPERVISOR source read role/order changed")
        self._intent("INPUT_READ_INTENT")

    def after_source_read(
        self, observation: StableInputReadV180R12R3R1
    ) -> core.StableInputSnapshotReceiptV180R12R3R1:
        snapshot = core.StableInputSnapshotReceiptV180R12R3R1(
            observation.fact, observation.returned_bytes
        )
        planned = self._planned()
        transfer = supervisor_core.ledger.issue_campaign_io_transfer_receipt_v180r12r3r1(
            protocol_id=self.start["protocol_id"],
            authorization_id=self.start["authorization_id"],
            attempt_id=self.start["attempt_id"],
            operation_id=planned.operation_id,
            event_kind="INPUT_READ_OUTCOME",
            measured_value=len(observation.returned_bytes),
            returned_chunk_byte_counts=observation.returned_chunk_byte_counts,
            source_evidence_id=self.start["campaign_operation_manifest_id"],
            target_evidence_id=snapshot.snapshot_receipt_id,
        )
        snapshot_transport = {
            "schema": SNAPSHOT_BYTES_TRANSPORT_SCHEMA,
            "snapshot_receipt_id": snapshot.snapshot_receipt_id,
            "role": observation.fact.role.value,
            "byte_count": len(observation.returned_bytes),
            "sha256": hashlib.sha256(observation.returned_bytes).hexdigest(),
            "canonical_bytes_hex": observation.returned_bytes.hex(),
        }
        if (
            tuple(snapshot_transport) != SNAPSHOT_BYTES_TRANSPORT_FIELDS
            or len(canonical_json_bytes(snapshot_transport))
            > SNAPSHOT_BYTES_TRANSPORT_BYTE_CAP
        ):
            _fail("SUPERVISOR snapshot transport changed or exceeded its cap")
        self._outcome(
            "INPUT_READ_OUTCOME",
            transfer,
            measured_value=len(observation.returned_bytes),
            supporting=(snapshot.to_document(), snapshot_transport),
        )
        return snapshot

    def before_stage_write(
        self, snapshot: core.StableInputSnapshotReceiptV180R12R3R1
    ) -> None:
        if type(snapshot) is not core.StableInputSnapshotReceiptV180R12R3R1:
            _fail("SUPERVISOR stage write snapshot is mistyped")
        self._intent("STAGE_WRITE_INTENT")

    def after_stage_write(
        self,
        stage: SealedMemfdStageV180R12R3R1,
        snapshot: core.StableInputSnapshotReceiptV180R12R3R1,
    ) -> core.MemfdStageReceiptV180R12R3R1:
        worker_fd = (
            WORKER_TERMINAL_STAGE_FD
            if stage.role is core.CampaignInputRoleV180R12R3R1.TERMINAL
            else WORKER_VERIFICATION_STAGE_FD
        )
        receipt = core.MemfdStageReceiptV180R12R3R1(
            snapshot.snapshot_receipt_id,
            stage.role,
            stage.supervisor_descriptor,
            worker_fd,
            stage.device,
            stage.inode,
            stage.byte_count,
            snapshot.to_document()["observed_sha256"],
            core.REQUIRED_MEMFD_SEALS,
            stage.supervisor_cloexec,
            stage.worker_source_read_only,
            True,
            stage.link_count,
            stage.write_probe_errno,
        )
        planned = self._planned()
        transfer = supervisor_core.ledger.issue_campaign_io_transfer_receipt_v180r12r3r1(
            protocol_id=self.start["protocol_id"],
            authorization_id=self.start["authorization_id"],
            attempt_id=self.start["attempt_id"],
            operation_id=planned.operation_id,
            event_kind="STAGE_WRITE_OUTCOME",
            measured_value=stage.byte_count,
            returned_chunk_byte_counts=stage.returned_chunk_byte_counts,
            source_evidence_id=snapshot.snapshot_receipt_id,
            target_evidence_id=receipt.stage_receipt_id,
        )
        self._outcome(
            "STAGE_WRITE_OUTCOME",
            transfer,
            measured_value=stage.byte_count,
            supporting=(receipt.to_document(),),
        )
        return receipt

    def open_visibility(
        self,
        stage: SealedMemfdStageV180R12R3R1,
        receipt: core.MemfdStageReceiptV180R12R3R1,
    ) -> None:
        planned = self._planned()
        worker_fd = (
            WORKER_TERMINAL_STAGE_FD
            if stage.role is core.CampaignInputRoleV180R12R3R1.TERMINAL
            else WORKER_VERIFICATION_STAGE_FD
        )
        visibility = core.FDVisibilityReceiptV180R12R3R1(
            self.start["attempt_id"], planned.operation_id,
            receipt.stage_receipt_id,
            self.start["supervisor_birth_receipt_id"], "SUPERVISOR",
            stage.role, core.VisibilityStateV180R12R3R1.OPEN, worker_fd,
            stage.device, stage.inode, stage.device, stage.inode, True, True, (),
        )
        aggregate = self.visible_byte_count + stage.byte_count
        document = visibility.to_document()
        self._propose_and_ack(
            event_kind="MOUNT_VISIBILITY_OPEN",
            evidence_documents=(document,),
            measured_value=aggregate,
        )
        self.visibility_documents.append(document)
        self.visible_byte_count = aggregate

    def before_operation(self, kind, label, phase, actor_role) -> None:
        if phase not in {"STAGE", "COMMIT"} or actor_role != "SUPERVISOR":
            _fail("SUPERVISOR semantic callback crossed its process role")
        planned = self._planned()
        family, family_ordinal, _global, _phase, _actor = core._operation_coordinates(
            kind, label
        )
        expected_operation = core.domains.extension_content_id_v180r12r3r1e(
            core.domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_V180R12R3R1E_DOMAIN,
            {
                "schema": "acfqp.campaign_operation_identity.v180r12r3r1",
                "schema_version": core.SCHEMA_VERSION,
                "attempt_id": self.start["attempt_id"],
                "slot": kind.value,
                "family": family,
                "ordinal": family_ordinal,
            },
        )
        if planned.operation_id != expected_operation:
            _fail("SUPERVISOR semantic operation label/manifest changed")
        self._intent(kind.value + "_INTENT")

    def after_operation(self, result: core.ReplayOperationResultV180R12R3R1) -> None:
        receipt = core.semantic_operation_receipt_v180r12r3r1(
            attempt_id=self.start["attempt_id"],
            operation_manifest_id=self.start["campaign_operation_manifest_id"],
            native_zero_source_manifest_id=self.start[
                "native_zero_source_manifest_id"
            ],
            native_zero_import_inventory_id=self.start[
                "native_zero_import_inventory_id"
            ],
            evidence_subject_id=self.start["campaign_attempt_record_id"],
            result=result,
        )
        document = receipt.to_document()
        self._outcome(
            result.kind.value + "_OUTCOME",
            document,
            measured_value=result.measured_value,
        )
        self.semantic_documents.append(document)


def _open_output_root_from_repository_fd_v180r12r3r1(
    repository_root_fd: int,
) -> int:
    """Open the already-created campaign output root without path re-resolution."""

    descriptor = fcntl.fcntl(
        repository_root_fd, fcntl.F_DUPFD_CLOEXEC, 256
    )
    try:
        for component in OUTPUT_ROOT_PARTS:
            successor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = successor
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or metadata.st_nlink < 2
        ):
            _fail("SUPERVISOR output root metadata changed")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _semantic_receipt_and_result_from_document_v180r12r3r1(
    value: Mapping[str, Any],
    *,
    start: Mapping[str, Any],
) -> tuple[
    core.SemanticOperationReceiptV180R12R3R1,
    core.ReplayOperationResultV180R12R3R1,
]:
    document, _identity = _validate_evidence_document(
        value,
        expected_schema="acfqp.campaign_semantic_operation_receipt.v180r12r3r1",
    )
    kind = core.SemanticOperationKindV180R12R3R1(document["kind"])
    auxiliary = document["auxiliary_values"]
    expected_name = (
        "observed_sha256"
        if kind is core.SemanticOperationKindV180R12R3R1.SEMANTIC_HASH
        else "check_passed"
    )
    if (
        type(auxiliary) is not list
        or len(auxiliary) != 1
        or set(auxiliary[0]) != {"name", "value"}
        or auxiliary[0]["name"] != expected_name
        or (
            kind is core.SemanticOperationKindV180R12R3R1.SEMANTIC_HASH
            and (
                type(auxiliary[0]["value"]) is not str
                or len(auxiliary[0]["value"]) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in auxiliary[0]["value"]
                )
            )
        )
        or (
            kind is not core.SemanticOperationKindV180R12R3R1.SEMANTIC_HASH
            and auxiliary[0]["value"] is not True
        )
    ):
        _fail("SUPERVISOR semantic auxiliary evidence changed")
    family, family_ordinal, ordinal, phase, actor_role = (
        core._operation_coordinates(kind, document["label"])
    )
    if not (
        document["attempt_id"] == start["attempt_id"]
        and document["family"] == family
        and document["family_ordinal"] == family_ordinal
        and document["ordinal"] == ordinal
        and document["operation_manifest_id"]
        == start["campaign_operation_manifest_id"]
        and document["native_zero_source_manifest_id"]
        == start["native_zero_source_manifest_id"]
        and document["native_zero_import_inventory_id"]
        == start["native_zero_import_inventory_id"]
        and document["evidence_subject_id"]
        == start["campaign_attempt_record_id"]
    ):
        _fail("SUPERVISOR semantic receipt crossed its exact attempt closure")
    result = core.ReplayOperationResultV180R12R3R1(
        kind,
        document["label"],
        family,
        family_ordinal,
        ordinal,
        phase,
        actor_role,
        document["outcome_code"],
        document["measured_value"],
        auxiliary[0]["value"],
    )
    receipt = core.SemanticOperationReceiptV180R12R3R1(
        document["attempt_id"],
        document["operation_id"],
        kind,
        document["label"],
        family,
        family_ordinal,
        ordinal,
        document["operation_manifest_id"],
        document["native_zero_source_manifest_id"],
        document["native_zero_import_inventory_id"],
        document["evidence_subject_id"],
        document["outcome_code"],
        document["measured_value"],
        ((expected_name, auxiliary[0]["value"]),),
    )
    if receipt.to_document() != document:
        _fail("SUPERVISOR semantic receipt failed exact typed round trip")
    return receipt, result


def _worker_result_from_acked_documents_v180r12r3r1(
    *,
    start: Mapping[str, Any],
    stage_result: core.StageMeasurementResultV180R12R3R1,
    worker_semantic_documents: Sequence[Mapping[str, Any]],
    subject_document: Mapping[str, Any],
    worker_birth_receipt_id: str,
) -> core.WorkerReplayResultV180R12R3R1:
    expected_labels = (
        *core.SEMANTIC_HASH_OPERATION_LABELS[2:-1],
        *core.INTEGRITY_CHECK_OPERATION_LABELS[6:-2],
        *core.PROTOCOL_CHECK_OPERATION_LABELS,
    )
    if len(worker_semantic_documents) != len(expected_labels):
        _fail("SUPERVISOR worker semantic receipt denominator changed")
    parsed = tuple(
        _semantic_receipt_and_result_from_document_v180r12r3r1(
            supplied, start=start
        )
        for supplied in worker_semantic_documents
    )
    results = tuple(result for _receipt, result in parsed)
    if tuple(result.label for result in results) != expected_labels:
        _fail("SUPERVISOR worker semantic receipt order changed")
    subject, subject_id = _validate_evidence_document(
        subject_document,
        expected_schema="acfqp.campaign_measurement_subject_result.v180r12r3r1",
    )
    expected_context = {
        "protocol_id": start["protocol_id"],
        "authorization_id": start["authorization_id"],
        "authorization_evidence_id": start["authorization_evidence_id"],
        "attempt_id": start["attempt_id"],
        "campaign_attempt_record_id": start["campaign_attempt_record_id"],
        "execution_slot_id": start["campaign_measurement_execution_slot_id"],
        "execution_nonce": start["execution_nonce"],
        "logical_occurrence_id": start["logical_occurrence_id"],
        "prelaunch_materialization_terminal_id": start[
            "prelaunch_materialization_terminal_id"
        ],
        "prelaunch_launch_manifest_sha256": start[
            "prelaunch_launch_manifest_sha256"
        ],
        "prelaunch_launch_rule_id": start["prelaunch_launch_rule_id"],
        "measurement_launch_attempt_id": start["measurement_launch_attempt_id"],
        "operation_manifest_id": start["campaign_operation_manifest_id"],
        "worker_birth_receipt_id": worker_birth_receipt_id,
        "terminal_snapshot_id": stage_result.terminal_stage_receipt.input_snapshot_id,
        "verification_snapshot_id": (
            stage_result.verification_stage_receipt.input_snapshot_id
        ),
    }
    if any(subject.get(name) != value for name, value in expected_context.items()):
        _fail("SUPERVISOR subject result crossed its authenticated context")
    inner_rows = subject.get("inner_content_ids")
    if (
        type(inner_rows) is not list
        or any(
            type(row) is not dict or set(row) != {"label", "content_id"}
            for row in inner_rows
        )
    ):
        _fail("SUPERVISOR subject inner-content population changed")
    inner = tuple((row["label"], row["content_id"]) for row in inner_rows)
    subject_bytes = canonical_json_bytes(subject)
    hash_count = len(core.SEMANTIC_HASH_OPERATION_LABELS[2:-1])
    integrity_count = len(core.INTEGRITY_CHECK_OPERATION_LABELS[6:-2])
    worker = core.WorkerReplayResultV180R12R3R1(
        stage_result,
        subject_bytes,
        subject_id,
        inner,
        results[:hash_count],
        results[hash_count : hash_count + integrity_count],
        results[hash_count + integrity_count :],
    )
    return worker


def _validate_and_relay_worker_proposal_v180r12r3r1(
    *,
    body: Mapping[str, Any],
    bridge: _AuthenticatedSupervisorBridgeV180R12R3R1,
    observer_channel: _AuthenticatedSupervisorChannelV180R12R3R1,
    worker_channel: _AuthenticatedSupervisorChannelV180R12R3R1,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    document = _thaw(body)
    planned = bridge._planned()
    rows = document.get("evidence_documents")
    if type(rows) is not list:
        _fail("SUPERVISOR worker proposal evidence population changed")
    identities: list[str] = []
    validated_rows: list[dict[str, Any]] = []
    for supplied in rows:
        if type(supplied) is not dict or type(supplied.get("schema")) is not str:
            _fail("SUPERVISOR worker proposal evidence schema is absent")
        validated, identity = _validate_evidence_document(
            supplied, expected_schema=supplied["schema"]
        )
        validated_rows.append(validated)
        identities.append(identity)
    if len(identities) != len(set(identities)):
        _fail("SUPERVISOR worker proposal duplicated an evidence identity")
    direct_id = document.get("payload", {}).get("evidence_id")
    if (direct_id is None and rows) or (
        direct_id is not None and (not identities or identities[0] != direct_id)
    ):
        _fail("SUPERVISOR worker proposal direct-evidence order changed")
    expected_payload = supervisor_core.campaign_event_payload_v180r12r3r1(
        event_kind=planned.event_kind,
        evidence_id=direct_id,
        measured_value=document.get("payload", {}).get("measured_value"),
        auxiliary_values=(),
    )
    if not (
        document.get("campaign_event_sequence") == bridge.campaign_event_sequence
        and document.get("phase") == planned.phase == "WORKER"
        and document.get("actor_role") == planned.actor_role == "WORKER"
        and document.get("event_kind") == planned.event_kind
        and document.get("operation_id") == planned.operation_id
        and document.get("payload") == expected_payload
    ):
        _fail("SUPERVISOR worker proposal differs from exact next schedule row")
    # Forward the authenticated body without rebuilding or reordering any
    # evidence.  Only after the observer's durable ACK may it enter local
    # reconstruction state or be returned to the worker.
    observer_channel.send("EVENT_PROPOSAL", document)
    received = observer_channel.receive()
    if received is None:
        _fail("SUPERVISOR observer ended before relayed worker ACK")
    frame_type, ack = received
    if frame_type != "EVENT_ACK" or ack["campaign_event_sequence"] != (
        bridge.campaign_event_sequence
    ):
        _fail("SUPERVISOR relayed ACK crossed its worker proposal")
    worker_channel.send("EVENT_ACK", ack)
    bridge.campaign_event_sequence += 1
    bridge.last_ack = ack
    semantic = [
        row
        for row in validated_rows
        if row.get("schema")
        == "acfqp.campaign_semantic_operation_receipt.v180r12r3r1"
    ]
    subjects = [
        row
        for row in validated_rows
        if row.get("schema")
        == "acfqp.campaign_measurement_subject_result.v180r12r3r1"
    ]
    if len(semantic) > 1 or len(subjects) > 1:
        _fail("SUPERVISOR worker proposal carried repeated semantic/subject evidence")
    return semantic, (None if not subjects else subjects[0])


def _close_stage_and_build_visibility_receipt_v180r12r3r1(
    *,
    start: Mapping[str, Any],
    bridge: _AuthenticatedSupervisorBridgeV180R12R3R1,
    stage: SealedMemfdStageV180R12R3R1,
    stage_receipt: core.MemfdStageReceiptV180R12R3R1,
) -> core.FDVisibilityReceiptV180R12R3R1:
    close_sealed_stage_v180r12r3r1(stage)
    unexpected: list[int] = []
    with os.scandir("/proc/self/fd") as entries:
        for index, entry in enumerate(entries):
            if index >= 4096:
                _fail("SUPERVISOR fd-visibility scan exceeded cap")
            if not entry.name.isdigit():
                continue
            descriptor = int(entry.name)
            try:
                metadata = os.fstat(descriptor)
            except OSError:
                continue
            if metadata.st_dev == stage.device and metadata.st_ino == stage.inode:
                unexpected.append(descriptor)
    if unexpected:
        _fail("SUPERVISOR sealed stage remained visible after physical close")
    planned = bridge._planned()
    worker_fd = (
        WORKER_TERMINAL_STAGE_FD
        if stage.role is core.CampaignInputRoleV180R12R3R1.TERMINAL
        else WORKER_VERIFICATION_STAGE_FD
    )
    return core.FDVisibilityReceiptV180R12R3R1(
        start["attempt_id"],
        planned.operation_id,
        stage_receipt.stage_receipt_id,
        start["supervisor_birth_receipt_id"],
        "SUPERVISOR",
        stage.role,
        core.VisibilityStateV180R12R3R1.CLOSED,
        worker_fd,
        stage.device,
        stage.inode,
        None,
        None,
        False,
        False,
        (),
    )


def _topology_from_document_v180r12r3r1(
    value: Mapping[str, Any],
) -> supervisor_core.MeasurementCgroupTopologyReceiptV180R12R3R1:
    document, _identity = _validate_evidence_document(
        value, expected_schema="acfqp.campaign_cgroup_topology_receipt.v180r12r3r1"
    )

    def node(row: Mapping[str, Any]) -> supervisor_core.CgroupNodeIdentityV180R12R3R1:
        return supervisor_core.CgroupNodeIdentityV180R12R3R1(
            row["role"], row["path"], row["parent_path"],
            row["membership_path"], row["parent_membership_path"],
            row["directory_fd"], row["device"], row["inode"], row["mode"],
            row["link_count"], row["cloexec"], row["symlink_free_resolution"],
        )

    controls = tuple(
        supervisor_core.CgroupControlFileOFDV180R12R3R1(
            row["node_role"], row["name"], row["fd"], row["device"],
            row["inode"], row["mode"], row["link_count"], row["cloexec"],
            row["opened_before_supervisor_birth"],
            row["retained_through_os_observe"],
        )
        for row in document["control_files"]
    )
    topology = supervisor_core.MeasurementCgroupTopologyReceiptV180R12R3R1(
        document["cgroup_parent_fact"],
        node(document["delegated_parent"]),
        node(document["measurement_root"]),
        node(document["supervisor_leaf"]),
        node(document["worker_leaf"]),
        document["filesystem_type"], tuple(document["controllers"]),
        tuple(document["subtree_control"]), document["root_memory_max_bytes"],
        document["root_pids_max"], document["supervisor_leaf_pids_max"],
        document["worker_leaf_pids_max"],
        document["root_populated_before_birth"],
        document["root_process_count_before_birth"],
        tuple(document["leaf_process_counts_before_birth"]), controls,
    )
    if topology.to_document() != document:
        _fail("SUPERVISOR topology document did not round-trip exactly")
    return topology


@dataclass(frozen=True, slots=True)
class _WorkerProcessHandleV180R12R3R1:
    pid: int
    pidfd: int
    pidfd_device: int
    pidfd_inode: int
    proc_starttime_ticks: int
    fdinfo_pid: int
    fdinfo_nspid: tuple[int, ...]
    cgroup_membership_line: str
    channel: socket.socket = field(repr=False, compare=False)


class _CloneArgsV180R12R3R1(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint64), ("pidfd", ctypes.c_uint64),
        ("child_tid", ctypes.c_uint64), ("parent_tid", ctypes.c_uint64),
        ("exit_signal", ctypes.c_uint64), ("stack", ctypes.c_uint64),
        ("stack_size", ctypes.c_uint64), ("tls", ctypes.c_uint64),
        ("set_tid", ctypes.c_uint64), ("set_tid_size", ctypes.c_uint64),
        ("cgroup", ctypes.c_uint64),
    ]


def _bounded_proc_file_v180r12r3r1(path: str, byte_cap: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, byte_cap + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > byte_cap:
                _fail("SUPERVISOR proc observation exceeded its byte cap")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _proc_starttime_v180r12r3r1(pid: int) -> int:
    raw = _bounded_proc_file_v180r12r3r1(f"/proc/{pid}/stat", 16 * 1024)
    close = raw.rfind(b")")
    fields = raw[close + 2 :].split()
    if close <= 0 or len(fields) < 20:
        _fail("SUPERVISOR child /proc stat is malformed")
    return int(fields[19])


def _proc_cgroup_v180r12r3r1(pid: int) -> str:
    rows = [
        row
        for row in _bounded_proc_file_v180r12r3r1(
            f"/proc/{pid}/cgroup", 64 * 1024
        ).decode("ascii", "strict").splitlines()
        if row
    ]
    if len(rows) != 1 or not rows[0].startswith("0::/"):
        _fail("SUPERVISOR child cgroup membership is malformed")
    return rows[0]


def _pidfd_info_v180r12r3r1(pidfd: int) -> tuple[int, tuple[int, ...]]:
    values: dict[str, str] = {}
    for row in _bounded_proc_file_v180r12r3r1(
        f"/proc/self/fdinfo/{pidfd}", 64 * 1024
    ).decode("ascii", "strict").splitlines():
        name, separator, value = row.partition(":")
        if separator:
            values[name] = value.strip()
    if not values.get("Pid", "").isdigit():
        _fail("SUPERVISOR worker pidfd info lacks PID")
    nspid = tuple(int(value) for value in values.get("NSpid", "").split())
    if not nspid:
        _fail("SUPERVISOR worker pidfd info lacks NSpid")
    return int(values["Pid"]), nspid


def _sealed_read_only_memfd_v180r12r3r1(name: str, raw: bytes) -> int:
    writable = _memfd_create(name)
    read_only = -1
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(writable, raw[offset : offset + IO_CHUNK_BYTES])
            if written <= 0:
                _fail("SUPERVISOR sealed context write made no progress")
            offset += written
        os.fchmod(writable, 0o400)
        fcntl.fcntl(writable, F_ADD_SEALS, REQUIRED_SEAL_MASK)
        read_only = os.open(f"/proc/self/fd/{writable}", os.O_RDONLY | os.O_CLOEXEC)
        metadata = os.fstat(read_only)
        if (
            metadata.st_size != len(raw)
            or metadata.st_nlink != 0
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or fcntl.fcntl(read_only, F_GET_SEALS) != REQUIRED_SEAL_MASK
        ):
            _fail("SUPERVISOR sealed context memfd changed")
        return read_only
    except BaseException:
        if read_only >= 0:
            os.close(read_only)
        raise
    finally:
        os.close(writable)


def _internal_exec_argv_v180r12r3r1(target: str) -> tuple[str, ...]:
    raw = _bounded_proc_file_v180r12r3r1("/proc/self/cmdline", 64 * 1024)
    rows = tuple(item.decode("utf-8", "strict") for item in raw.rstrip(b"\0").split(b"\0"))
    if (
        len(rows) != 11
        or rows[:6]
        != (
            "/usr/bin/python3", "-I", "-S", "-B", "-X",
            "pycache_prefix=/dev/null/v180r12r3r1",
        )
        or rows[7] != "supervisor"
        or target != "worker"
    ):
        _fail("SUPERVISOR retained bootstrap argv changed")
    return (*rows[:7], target, *rows[8:])


class _LinuxWorkerProcessAdapterV180R12R3R1:
    clone3_number = 435
    pidfd_send_signal_number = 424
    clone_pidfd = 0x00001000
    clone_into_cgroup = 0x200000000

    def __init__(self) -> None:
        if os.uname().machine != "x86_64" or len(os.listdir("/proc/self/task")) != 1:
            _fail("SUPERVISOR worker clone3 requires x86_64 single-thread process")
        self.libc = ctypes.CDLL(None, use_errno=True)
        self.libc.syscall.restype = ctypes.c_long

    def launch_worker(
        self,
        *,
        context: Mapping[str, Any],
        start: Mapping[str, Any],
        topology: supervisor_core.MeasurementCgroupTopologyReceiptV180R12R3R1,
        stage_effects: SupervisorStageEffectsV180R12R3R1,
        subject_output: SubjectOutputHandleV180R12R3R1,
        operation_id: str,
    ) -> tuple[_WorkerProcessHandleV180R12R3R1, supervisor_core.PidfdBirthReceiptV180R12R3R1, bytes]:
        argv = _internal_exec_argv_v180r12r3r1("worker")
        env = {
            "ACFQP_V180R12R3R1_LAUNCH_MANIFEST_SHA256": context["manifest_sha256"],
            "LC_CTYPE": "C.UTF-8",
        }
        parent_channel, child_channel = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC
        )
        try:
            configure_seqpacket_pair_v180r12r3r1(parent_channel, child_channel)
        except BaseException:
            parent_channel.close()
            child_channel.close()
            raise
        secret = os.getrandom(32)
        if type(secret) is not bytes or len(secret) != 32:
            _fail("SUPERVISOR getrandom returned a short worker channel key")
        key_fd = context_fd = -1
        pidfd = -1
        try:
            inherited_roles = [
                {"fd": fd, "role": role}
                for fd, role in (
                    (PRECOMPILED_SOURCE_BUNDLE_FD, "PRECOMPILED_SOURCE_BUNDLE_MEMFD"),
                    (INTERNAL_IPC_FD, "SUPERVISOR_WORKER_SOCK_SEQPACKET"),
                    (INTERNAL_MAC_KEY_FD, "PARENT_TO_CHILD_MAC_KEY_MEMFD"),
                    (INTERNAL_CONTEXT_FD, "INTERNAL_LAUNCH_CONTEXT_MEMFD"),
                )
            ] + [
                {"fd": WORKER_TERMINAL_STAGE_FD, "role": "TERMINAL_STAGE_READ_ONLY_MEMFD"},
                {"fd": WORKER_VERIFICATION_STAGE_FD, "role": "VERIFICATION_STAGE_READ_ONLY_MEMFD"},
                {"fd": WORKER_SUBJECT_RESULT_FD, "role": "SUBJECT_RESULT_WRITE_ONLY_FD"},
            ]
            payload = {
                "schema": "acfqp.v180r12r3r1_internal_launch_context.v1",
                "target": "worker", "actor_role": "WORKER",
                "parent_actor_role": "SUPERVISOR",
                "protocol_id": context["protocol_id"],
                "authorization_id": context["authorization_id"],
                "authorization_evidence_id": context["authorization_evidence_id"],
                "attempt_id": context["attempt_id"],
                "campaign_measurement_execution_slot_id": context[
                    "campaign_measurement_execution_slot_id"
                ],
                "logical_occurrence_id": context["logical_occurrence_id"],
                "execution_nonce": context["execution_nonce"],
                "prelaunch_materialization_terminal_id": context[
                    "prelaunch_materialization_terminal_id"
                ],
                "prelaunch_launch_rule_id": context["prelaunch_launch_rule_id"],
                "measurement_launch_attempt_id": context[
                    "measurement_launch_attempt_id"
                ],
                "launch_operation_id": operation_id,
                "repository_root": argv[8], "c_pre_root": argv[9],
                "manifest_path": argv[10],
                "launch_manifest_sha256": context["manifest_sha256"],
                "c_pre_commit_id": os.environ.get(
                    "ACFQP_V180R12R3R1_PREREG_COMMIT", ""
                ),
                "precompiled_source_bundle_sha256": context[
                    "precompiled_source_bundle_sha256"
                ],
                "runner_relative_path": "scripts/work_v180r12r3r1_campaign_measurement.py",
                "inherited_fd_roles": inherited_roles,
                "target_payload": {
                    "terminal_stage_byte_count": stage_effects.terminal_stage.byte_count,
                    "verification_stage_byte_count": stage_effects.verification_stage.byte_count,
                    "subject_result_initial_byte_count": 0,
                },
                "one_shot": True,
                "context_mac_algorithm": "BLAKE2S_KEYED_256",
                "context_mac_direction": "PARENT_TO_CHILD_ONLY",
            }
            context_mac = hashlib.blake2s(
                canonical_json_bytes(payload), key=secret, digest_size=32
            ).hexdigest()
            context_raw = canonical_json_bytes({**payload, "context_mac": context_mac})
            key_fd = _sealed_read_only_memfd_v180r12r3r1(
                "v180r12r3r1-worker-key", secret
            )
            context_fd = _sealed_read_only_memfd_v180r12r3r1(
                "v180r12r3r1-worker-context", context_raw
            )
            sources = {
                PRECOMPILED_SOURCE_BUNDLE_FD: PRECOMPILED_SOURCE_BUNDLE_FD,
                INTERNAL_IPC_FD: child_channel.fileno(),
                INTERNAL_MAC_KEY_FD: key_fd,
                INTERNAL_CONTEXT_FD: context_fd,
                WORKER_TERMINAL_STAGE_FD: stage_effects.terminal_stage.worker_source_descriptor,
                WORKER_VERIFICATION_STAGE_FD: stage_effects.verification_stage.worker_source_descriptor,
                WORKER_SUBJECT_RESULT_FD: subject_output.worker_source_descriptor,
            }
            args = _CloneArgsV180R12R3R1()
            pidfd_cell = ctypes.c_int(-1)
            args.flags = self.clone_pidfd | self.clone_into_cgroup
            args.pidfd = ctypes.addressof(pidfd_cell)
            args.exit_signal = signal.SIGCHLD
            args.cgroup = WORKER_CGROUP_FD
            result = self.libc.syscall(
                self.clone3_number, ctypes.byref(args), ctypes.sizeof(args)
            )
            if result == 0:
                try:
                    resource.setrlimit(
                        resource.RLIMIT_AS,
                        (16 * 1024 * 1024 * 1024, 16 * 1024 * 1024 * 1024),
                    )
                    temporary: dict[int, int] = {}
                    floor = 256
                    for target, source in sources.items():
                        temporary[target] = fcntl.fcntl(
                            source, fcntl.F_DUPFD_CLOEXEC, floor
                        )
                        floor = max(floor, temporary[target] + 1)
                    for target, source in temporary.items():
                        os.dup2(source, target, inheritable=True)
                    for descriptor in temporary.values():
                        os.close(descriptor)
                    os.execve(argv[0], list(argv), env)
                except BaseException:
                    os._exit(127)
            if result < 0:
                error = ctypes.get_errno()
                raise OSError(error, os.strerror(error))
            pid = int(result)
            pidfd = pidfd_cell.value
            if pidfd < 0:
                # A positive clone3 return transfers ownership of a live direct
                # child even if the kernel/user-memory pidfd result is absent.
                # PID reuse cannot occur before this parent reaps its direct
                # child, so this is the only safe no-pidfd cleanup fallback.
                try:
                    os.kill(pid, signal.SIGKILL)
                finally:
                    os.waitpid(pid, 0)
                _fail("SUPERVISOR clone3 returned a PID without its pidfd")
            fcntl.fcntl(pidfd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
            pidfd_stat = os.fstat(pidfd)
            fdinfo_pid, fdinfo_nspid = _pidfd_info_v180r12r3r1(pidfd)
            starttime = _proc_starttime_v180r12r3r1(pid)
            membership = _proc_cgroup_v180r12r3r1(pid)
            if fdinfo_pid != pid or fdinfo_nspid[0] != pid:
                _fail("SUPERVISOR worker pidfd anti-reuse facts changed")
            handle = _WorkerProcessHandleV180R12R3R1(
                pid, pidfd, pidfd_stat.st_dev, pidfd_stat.st_ino, starttime,
                fdinfo_pid, fdinfo_nspid, membership, parent_channel,
            )
            target = topology.worker_leaf
            receipt = supervisor_core.PidfdBirthReceiptV180R12R3R1(
                topology, context["attempt_id"], operation_id,
                supervisor_core.ProcessRoleV180R12R3R1.WORKER,
                pid, pidfd, pidfd_stat.st_dev, pidfd_stat.st_ino,
                ("CLONE_INTO_CGROUP", "CLONE_PIDFD"), WORKER_CGROUP_FD,
                os.fstat(WORKER_CGROUP_FD).st_dev,
                os.fstat(WORKER_CGROUP_FD).st_ino, target.path, starttime,
                fdinfo_pid, fdinfo_nspid, membership, True, True,
            )
            child_channel.close()
            os.close(key_fd)
            key_fd = -1
            os.close(context_fd)
            context_fd = -1
            return handle, receipt, secret
        except BaseException:
            parent_channel.close()
            child_channel.close()
            if pidfd >= 0:
                try:
                    signal_result = self.libc.syscall(
                        self.pidfd_send_signal_number, pidfd, signal.SIGKILL, 0, 0
                    )
                    if signal_result == 0:
                        os.waitid(os.P_PIDFD, pidfd, os.WEXITED)
                    elif result > 0:
                        os.kill(int(result), signal.SIGKILL)
                        os.waitpid(int(result), 0)
                except BaseException:
                    pass
                try:
                    os.close(pidfd)
                except BaseException:
                    pass
            raise
        finally:
            if key_fd >= 0:
                os.close(key_fd)
            if context_fd >= 0:
                os.close(context_fd)

    def reap_worker(
        self,
        handle: _WorkerProcessHandleV180R12R3R1,
        birth: supervisor_core.PidfdBirthReceiptV180R12R3R1,
    ) -> supervisor_core.PidfdReapReceiptV180R12R3R1:
        if (
            os.fstat(handle.pidfd).st_dev != handle.pidfd_device
            or os.fstat(handle.pidfd).st_ino != handle.pidfd_inode
            or _proc_starttime_v180r12r3r1(handle.pid) != handle.proc_starttime_ticks
        ):
            _fail("SUPERVISOR worker pidfd identity changed before reap")
        result = os.waitid(os.P_PIDFD, handle.pidfd, os.WEXITED)
        if result is None or result.si_pid != handle.pid:
            _fail("SUPERVISOR waitid(P_PIDFD) did not reap worker")
        poller = select.poll()
        poller.register(handle.pidfd, select.POLLIN)
        events = LinuxCgroupReadV180R12R3R1.read_at(
            WORKER_CGROUP_FD, "cgroup.events"
        )
        processes = LinuxCgroupReadV180R12R3R1.read_at(
            WORKER_CGROUP_FD, "cgroup.procs"
        )
        populated = dict(
            row.split(" ", 1) for row in events.splitlines() if row
        ).get("populated")
        return supervisor_core.PidfdReapReceiptV180R12R3R1(
            birth, birth.operation_id, handle.pidfd_device, handle.pidfd_inode,
            handle.proc_starttime_ticks, "P_PIDFD", handle.pidfd,
            "CLD_EXITED" if result.si_code == os.CLD_EXITED else str(result.si_code),
            result.si_status, bool(poller.poll(0)), populated == "1",
            len([row for row in processes.splitlines() if row]),
        )

    def close_reaped_worker(self, handle: _WorkerProcessHandleV180R12R3R1) -> None:
        metadata = os.fstat(handle.pidfd)
        if metadata.st_dev != handle.pidfd_device or metadata.st_ino != handle.pidfd_inode:
            _fail("SUPERVISOR worker pidfd changed before close")
        os.close(handle.pidfd)
        handle.channel.close()

    def terminate_worker(self, handle: _WorkerProcessHandleV180R12R3R1) -> None:
        """Failure-only exact pidfd kill/reap/close for an owned worker."""

        primary: BaseException | None = None
        try:
            metadata = os.fstat(handle.pidfd)
            if (
                metadata.st_dev != handle.pidfd_device
                or metadata.st_ino != handle.pidfd_inode
            ):
                _fail("SUPERVISOR worker pidfd changed before failure cleanup")
            result = self.libc.syscall(
                self.pidfd_send_signal_number,
                handle.pidfd,
                signal.SIGKILL,
                0,
                0,
            )
            if result != 0 and ctypes.get_errno() != errno.ESRCH:
                error = ctypes.get_errno()
                raise OSError(error, os.strerror(error))
            os.waitid(os.P_PIDFD, handle.pidfd, os.WEXITED)
        except BaseException as error:
            primary = error
        try:
            os.close(handle.pidfd)
        except BaseException as error:
            if primary is None:
                primary = error
        try:
            handle.channel.close()
        except BaseException as error:
            if primary is None:
                primary = error
        if primary is not None:
            raise primary


class LinuxCgroupReadV180R12R3R1:
    @staticmethod
    def read_at(directory_fd: int, name: str, byte_cap: int = 64 * 1024) -> str:
        descriptor = os.open(
            name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory_fd,
        )
        try:
            raw = os.read(descriptor, byte_cap + 1)
            if len(raw) > byte_cap or os.read(descriptor, 1):
                _fail("SUPERVISOR cgroup read exceeded cap")
            return raw.decode("ascii", "strict")
        finally:
            os.close(descriptor)


def run_authenticated_supervisor_lifecycle_v180r12r3r1(
    *,
    context: types.MappingProxyType,
    start: Mapping[str, Any],
    observer_channel: _AuthenticatedSupervisorChannelV180R12R3R1,
    repository_root_fd: int,
    output_root_fd: int,
    worker_adapter: Any,
) -> None:
    """Execute the exact seq3..621 supervisor-owned lifecycle.

    The function is injectable for synthetic tests, but its default bootstrap
    caller supplies the real clone3/pidfd adapter.  It never writes a journal;
    every effect remains behind a synchronous authenticated observer ACK.
    """

    validated_start = validate_observer_supervisor_start_v180r12r3r1(
        start, verified_context=context
    )
    bridge = _AuthenticatedSupervisorBridgeV180R12R3R1(
        observer_channel,
        validated_start,
        validated_start["next_campaign_event_sequence"],
    )
    stage_effects: SupervisorStageEffectsV180R12R3R1 | None = None
    stages_open = [False, False]
    subject_output: SubjectOutputHandleV180R12R3R1 | None = None
    subject_reader_open = False
    subject_writer_open = False
    worker_handle: _WorkerProcessHandleV180R12R3R1 | None = None
    worker_owned = False
    worker_channel: _AuthenticatedSupervisorChannelV180R12R3R1 | None = None
    try:
        stage_effects = run_supervisor_stage_effects_v180r12r3r1(
            repository_root_fd=repository_root_fd,
            bridge=bridge,
        )
        stages_open[:] = [True, True]
        if bridge.campaign_event_sequence != 29 or bridge.open_event is not None:
            _fail("SUPERVISOR STAGE did not stop at exact worker-birth intent")

        # The worker-birth intent is the preregistered durable guard for both
        # the subject O_EXCL creation and clone3.  A subject partial can never
        # therefore precede the intent ACK, while it still exists before the
        # child is born.
        bridge._intent("PROCESS_BIRTH_INTENT")
        birth_plan = bridge._planned()
        subject_output = preopen_subject_output_v180r12r3r1(output_root_fd)
        subject_reader_open = True
        subject_writer_open = True
        topology = _topology_from_document_v180r12r3r1(
            validated_start["cgroup_topology_document"]
        )
        worker_handle, worker_birth, worker_secret = worker_adapter.launch_worker(
            context=context,
            start=validated_start,
            topology=topology,
            stage_effects=stage_effects,
            subject_output=subject_output,
            operation_id=birth_plan.operation_id,
        )
        worker_owned = True
        bridge._outcome(
            "PROCESS_BIRTH_OUTCOME",
            worker_birth.to_document(),
            measured_value=1,
        )
        if bridge.campaign_event_sequence != 31 or bridge.last_ack is None:
            _fail("SUPERVISOR worker birth outcome was not durably ACKed")

        worker_channel = _AuthenticatedSupervisorChannelV180R12R3R1(
            worker_handle.channel,
            worker_secret,
            context,
            parent_actor_role="SUPERVISOR",
            child_actor_role="WORKER",
            channel_id=worker_birth.operation_id,
        )
        handoff = build_supervisor_worker_handoff_v180r12r3r1(
            start_document=validated_start,
            stage_effects=stage_effects,
            terminal_open_visibility_document=bridge.visibility_documents[0],
            verification_open_visibility_document=bridge.visibility_documents[1],
            stage_semantic_receipt_documents=bridge.semantic_documents,
            subject_output=subject_output,
            worker_birth_document=worker_birth.to_document(),
            worker_birth_event_id=bridge.last_ack["event_id"],
            worker_birth_event_sequence=30,
            next_campaign_event_sequence=31,
        )
        worker_channel.send("WORKER_HANDOFF", handoff)

        worker_semantic_documents: list[dict[str, Any]] = []
        subject_document: dict[str, Any] | None = None
        worker_open_pair: tuple[str, str] | None = None
        while True:
            received = worker_channel.receive(allow_eof=True)
            if received is None:
                break
            frame_type, body = received
            if frame_type != "EVENT_PROPOSAL":
                _fail("SUPERVISOR worker sent a non-proposal after HANDOFF")
            planned = bridge._planned()
            kind = planned.event_kind
            if kind.endswith("_INTENT"):
                if worker_open_pair is not None:
                    _fail("SUPERVISOR observed overlapping worker operations")
                worker_open_pair = (
                    kind.removesuffix("_INTENT"), planned.operation_id
                )
            elif kind.endswith("_OUTCOME"):
                if worker_open_pair != (
                    kind.removesuffix("_OUTCOME"), planned.operation_id
                ):
                    _fail("SUPERVISOR worker outcome crossed its durable intent")
            semantics, subject = _validate_and_relay_worker_proposal_v180r12r3r1(
                body=body,
                bridge=bridge,
                observer_channel=observer_channel,
                worker_channel=worker_channel,
            )
            if kind.endswith("_OUTCOME"):
                worker_open_pair = None
            worker_semantic_documents.extend(semantics)
            if subject is not None:
                if subject_document is not None:
                    _fail("SUPERVISOR worker emitted more than one subject result")
                subject_document = subject
        if (
            bridge.campaign_event_sequence != 609
            or worker_open_pair is not None
            or subject_document is None
            or len(worker_semantic_documents) != 286
        ):
            _fail("SUPERVISOR accepted worker EOF outside exact seq608 closure")

        worker_result = _worker_result_from_acked_documents_v180r12r3r1(
            start=validated_start,
            stage_result=stage_effects.result,
            worker_semantic_documents=worker_semantic_documents,
            subject_document=subject_document,
            worker_birth_receipt_id=worker_birth.pidfd_birth_receipt_id,
        )
        expected_open_ids = tuple(
            document["fd_visibility_receipt_id"]
            for document in bridge.visibility_documents
        )
        if not (
            subject_document.get("memfd_stage_receipt_ids")
            == [
                stage_effects.result.terminal_stage_receipt.stage_receipt_id,
                stage_effects.result.verification_stage_receipt.stage_receipt_id,
            ]
            and subject_document.get("open_visibility_receipt_ids")
            == list(expected_open_ids)
        ):
            _fail("SUPERVISOR subject crossed its stage/visibility provenance")

        reap = worker_adapter.reap_worker(worker_handle, worker_birth)
        bridge._propose_and_ack(
            event_kind="PROCESS_REAP",
            evidence_documents=(reap.to_document(),),
            measured_value=None,
        )
        worker_adapter.close_reaped_worker(worker_handle)
        worker_owned = False
        worker_handle = None
        worker_channel = None

        # No write-capable subject OFD may survive into the readback window.
        close_subject_writer_before_readback_v180r12r3r1(
            subject_output,
            expected_byte_count=len(worker_result.subject_bytes),
        )
        subject_writer_open = False
        bridge._intent("INPUT_READ_INTENT")
        readback = readback_subject_output_v180r12r3r1(
            subject_output, worker_result.subject_bytes
        )
        read_plan = bridge._planned()
        readback_transfer = (
            supervisor_core.ledger.issue_campaign_io_transfer_receipt_v180r12r3r1(
                protocol_id=validated_start["protocol_id"],
                authorization_id=validated_start["authorization_id"],
                attempt_id=validated_start["attempt_id"],
                operation_id=read_plan.operation_id,
                event_kind="INPUT_READ_OUTCOME",
                measured_value=len(readback.returned_bytes),
                returned_chunk_byte_counts=readback.returned_chunk_byte_counts,
                source_evidence_id=worker_result.subject_id,
                target_evidence_id=validated_start[
                    "supervisor_birth_receipt_id"
                ],
            )
        )
        bridge._outcome(
            "INPUT_READ_OUTCOME",
            readback_transfer,
            measured_value=len(readback.returned_bytes),
        )
        commit_result = core.measure_subject_commit_v180r12r3r1(
            worker_result,
            subject_readback=lambda _expected: core.SubjectReadbackObservationV180R12R3R1(
                readback.returned_bytes,
                stat.S_IMODE(readback.mode),
                readback.link_count,
            ),
            operation_observer=bridge,
        )
        computation = core.join_campaign_replay_measurements_v180r12r3r1(
            stage_effects.result, worker_result, commit_result
        )
        execution_context = core.ReplayExecutionContextV180R12R3R1(
            validated_start["protocol_id"],
            validated_start["authorization_id"],
            validated_start["authorization_evidence_id"],
            validated_start["attempt_id"],
            validated_start["campaign_attempt_record_id"],
            validated_start["campaign_measurement_execution_slot_id"],
            validated_start["execution_nonce"],
            validated_start["logical_occurrence_id"],
            validated_start["prelaunch_materialization_terminal_id"],
            validated_start["prelaunch_launch_manifest_sha256"],
            validated_start["prelaunch_launch_rule_id"],
            validated_start["measurement_launch_attempt_id"],
            stage_effects.terminal_snapshot.snapshot_receipt_id,
            stage_effects.verification_snapshot.snapshot_receipt_id,
            expected_open_ids,
            worker_birth.pidfd_birth_receipt_id,
            validated_start["campaign_operation_manifest_id"],
            validated_start["native_zero_source_manifest_id"],
            validated_start["native_zero_import_inventory_id"],
        )
        semantic_receipts = core.materialize_semantic_operation_receipts_v180r12r3r1(
            computation,
            execution_context=execution_context,
            evidence_subject_id_by_label={
                label: validated_start["campaign_attempt_record_id"]
                for label in (
                    *core.SEMANTIC_HASH_OPERATION_LABELS,
                    *core.INTEGRITY_CHECK_OPERATION_LABELS,
                    *core.PROTOCOL_CHECK_OPERATION_LABELS,
                )
            },
        )
        collected_by_label = {
            document["label"]: document for document in bridge.semantic_documents
        }
        collected_by_label.update(
            {document["label"]: document for document in worker_semantic_documents}
        )
        if (
            len(collected_by_label) != 297
            or any(
                collected_by_label.get(receipt.label) != receipt.to_document()
                for receipt in semantic_receipts
            )
        ):
            _fail("SUPERVISOR semantic receipt reconstruction changed ACKed bytes")
        replay_receipt = core.ProducerFreeReplaySubjectReceiptV180R12R3R1(
            worker_result.subject_id,
            validated_start["campaign_attempt_record_id"],
            validated_start["campaign_operation_manifest_id"],
            validated_start["native_zero_source_manifest_id"],
            validated_start["native_zero_import_inventory_id"],
            stage_effects.terminal_snapshot.snapshot_receipt_id,
            stage_effects.verification_snapshot.snapshot_receipt_id,
            expected_open_ids,
            semantic_receipts,
            worker_result.subject_bytes,
            False,
            False,
            True,
            "PASS",
        )
        commit_observation = commit_subject_after_readback_v180r12r3r1(
            subject_output, readback
        )
        if commit_observation.returned_bytes != worker_result.subject_bytes:
            _fail("SUPERVISOR committed bytes changed after semantic readback")
        commit_plan = bridge._planned()
        commit_receipt = supervisor_core.ledger.issue_subject_commit_receipt_v180r12r3r1(
            protocol_id=validated_start["protocol_id"],
            authorization_id=validated_start["authorization_id"],
            attempt_id=validated_start["attempt_id"],
            operation_id=commit_plan.operation_id,
            subject_id=worker_result.subject_id,
            replay_subject_receipt_id=replay_receipt.replay_subject_receipt_id,
            readback_transfer_receipt_id=readback_transfer[
                "io_transfer_receipt_id"
            ],
            subject_byte_count=len(worker_result.subject_bytes),
        )
        bridge._propose_and_ack(
            event_kind="SUBJECT_COMMIT",
            evidence_documents=(commit_receipt, replay_receipt.to_document()),
            measured_value=None,
        )
        os.close(subject_output.descriptor)
        subject_reader_open = False

        close_receipts: list[core.FDVisibilityReceiptV180R12R3R1] = []
        stage_pairs = (
            (stage_effects.terminal_stage, stage_effects.result.terminal_stage_receipt),
            (
                stage_effects.verification_stage,
                stage_effects.result.verification_stage_receipt,
            ),
        )
        for index, (stage, stage_receipt) in enumerate(stage_pairs):
            receipt = _close_stage_and_build_visibility_receipt_v180r12r3r1(
                start=validated_start,
                bridge=bridge,
                stage=stage,
                stage_receipt=stage_receipt,
            )
            stages_open[index] = False
            bridge._propose_and_ack(
                event_kind="MOUNT_VISIBILITY_CLOSE",
                evidence_documents=(receipt.to_document(),),
                measured_value=None,
            )
            bridge.visible_byte_count -= stage.byte_count
            close_receipts.append(receipt)
        if bridge.visible_byte_count != 0:
            _fail("SUPERVISOR visibility aggregate remained nonzero at close")
        window_plan = bridge._planned()
        window_receipt = supervisor_core.ledger.issue_window_closure_receipt_v180r12r3r1(
            protocol_id=validated_start["protocol_id"],
            authorization_id=validated_start["authorization_id"],
            attempt_id=validated_start["attempt_id"],
            operation_id=window_plan.operation_id,
            subject_commit_receipt_id=commit_receipt[
                "subject_commit_receipt_id"
            ],
            close_visibility_receipt_ids=tuple(
                receipt.visibility_receipt_id for receipt in close_receipts
            ),
        )
        bridge._propose_and_ack(
            event_kind="WINDOW_CLOSED",
            evidence_documents=(window_receipt,),
            measured_value=None,
        )
        if bridge.campaign_event_sequence != 622 or bridge.open_event is not None:
            _fail("SUPERVISOR did not stop exactly after WINDOW_CLOSED")
        observer_channel.channel.shutdown(socket.SHUT_WR)
    finally:
        if worker_owned and worker_handle is not None:
            try:
                worker_adapter.terminate_worker(worker_handle)
            except BaseException:
                pass
        if subject_writer_open and subject_output is not None:
            try:
                _close_descriptor_if_same_inode_v180r12r3r1(
                    subject_output.worker_source_descriptor,
                    device=subject_output.device,
                    inode=subject_output.inode,
                )
            except OSError:
                pass
        if subject_reader_open and subject_output is not None:
            try:
                _close_descriptor_if_same_inode_v180r12r3r1(
                    subject_output.descriptor,
                    device=subject_output.device,
                    inode=subject_output.inode,
                )
            except OSError:
                pass
        if stage_effects is not None:
            for is_open, stage in zip(
                stages_open,
                (stage_effects.terminal_stage, stage_effects.verification_stage),
            ):
                if is_open:
                    try:
                        for descriptor in (
                            stage.worker_source_descriptor,
                            stage.supervisor_descriptor,
                        ):
                            _close_descriptor_if_same_inode_v180r12r3r1(
                                descriptor,
                                device=stage.device,
                                inode=stage.inode,
                            )
                    except OSError:
                        pass


def _run_bootstrap_verified_supervisor_v180r12r3r1(
    context: types.MappingProxyType,
) -> None:
    """Enter the real authenticated supervisor lifecycle from retained code."""

    duplicate = socket.fromfd(
        INTERNAL_IPC_FD, socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    output_root_fd = -1
    try:
        channel = _AuthenticatedSupervisorChannelV180R12R3R1(
            duplicate,
            context["parent_to_child_mac_key"],
            context,
            parent_actor_role="OBSERVER",
            child_actor_role="SUPERVISOR",
            channel_id=context["launch_operation_id"],
        )
        received = channel.receive()
        if received is None or received[0] != "SUPERVISOR_START":
            _fail("SUPERVISOR first authenticated frame is not START")
        start = validate_observer_supervisor_start_v180r12r3r1(
            received[1], verified_context=context
        )
        output_root_fd = _open_output_root_from_repository_fd_v180r12r3r1(
            REPOSITORY_ROOT_FD
        )
        run_authenticated_supervisor_lifecycle_v180r12r3r1(
            context=context,
            start=start,
            observer_channel=channel,
            repository_root_fd=REPOSITORY_ROOT_FD,
            output_root_fd=output_root_fd,
            worker_adapter=_LinuxWorkerProcessAdapterV180R12R3R1(),
        )
    finally:
        if output_root_fd >= 0:
            os.close(output_root_fd)
        duplicate.close()


def bootstrap_entrypoint_v180r12r3r1(verified_context: Mapping[str, Any]) -> None:
    context = _validate_verified_context_v180r12r3r1(verified_context)
    _run_bootstrap_verified_supervisor_v180r12r3r1(context)


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    raise V180R12R3R1SupervisorRuntimeError(
        "direct supervisor invocation is forbidden; the retained bootstrap must "
        "supply its authenticated internal launch context and bridge"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise
