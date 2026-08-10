"""Guardian-side raw protocol for one source-closed nested PIDFD_PROBE.

This module owns the first new runtime fact not established by the bounded
B2-C fixture: a live non-guardian SUPERVISOR creates, releases, WNOWAIT
observes, consume-reaps, and proves ECHILD for one PIDFD_PROBE.  The external
guardian independently joins SCM credentials, the shared PID cell, pidfd,
two live cgroup snapshots, child gate frames, death readiness, and the
creator's reap report.

The API consumes an already-executing exact native supervisor role.  It does
not establish the supervisor's own gated birth and therefore deliberately
issues no two-birth prefix, five-birth, E3 V2, accounting, or official claim.
"""

from __future__ import annotations

from array import array
from dataclasses import dataclass, field
import copy
import errno
import fcntl
import hashlib
import mmap
import os
from pathlib import Path
import select
import signal
import socket
import stat
import struct
import threading
import time
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_nested_creator_supervisor_native_v1 as role_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-B2-D-PROBE-NATIVE"
PROFILE_KEY = "construction_k7_h1_nested_creator_probe_native_v1"
READINESS = "RAW_NESTED_CREATOR_RUNTIME_PRIMITIVE"

ACTUAL_SOURCE_CLOSED_SUPERVISOR_READY_OBSERVATION_PRESENT = True
ACTUAL_NESTED_PIDFD_PROBE_BIRTH_PRESENT = True
ACTUAL_NON_GUARDIAN_CREATOR_REAP_PRESENT = True
GUARDIAN_INDEPENDENT_PID_CELL_PIDFD_CGROUP_JOIN_PRESENT = True

GATED_SUPERVISOR_BIRTH_AUTHORITY_PRESENT = False
TWO_BIRTH_PREFIX_AUTHORITY_PRESENT = False
FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT = False
ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT = False
E4_V2_COMPLETION_PRESENT = False
PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT = False
FQ11_COUNTER_COMPLETENESS_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_V7_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE = "NOT_RUN"

MFD_CLOEXEC = getattr(os, "MFD_CLOEXEC", 0x0001)
MFD_ALLOW_SEALING = getattr(os, "MFD_ALLOW_SEALING", 0x0002)
F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 0x0004)
F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
REQUIRED_SEALS = F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE
P_PIDFD = getattr(os, "P_PIDFD", 3)
FRAME = struct.Struct("<QIIQ16sqiIQ")
UCRED = struct.Struct("=iII")
FRAME_BYTES = FRAME.size
MAX_FRAME_BYTES = FRAME_BYTES + 1
PROTOCOL_TIMEOUT_SECONDS = 10.0
EMPTY_NONCE = bytes(16)
ALLOWED_RECV_FLAGS = getattr(socket, "MSG_EOR", 0) | getattr(
    socket, "MSG_CMSG_CLOEXEC", 0
)
REJECTED_RECV_FLAGS = socket.MSG_TRUNC | socket.MSG_CTRUNC
_ABSTRACT_AUTOBIND_HEX = frozenset(b"0123456789abcdef")

_SESSION_ISSUER = object()
_FACTS_ISSUER = object()
_SESSION_LOCK = threading.RLock()
_TEST_FAULT_PHASE: str | None = None


class ConstructionK7H1NestedCreatorProbeNativeV1Error(RuntimeError):
    """The exact nested-creator protocol or cleanup failed closed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1NestedCreatorProbeNativeV1Error(message)


def _test_fault(phase: str) -> None:
    global _TEST_FAULT_PHASE
    if _TEST_FAULT_PHASE == phase:
        _TEST_FAULT_PHASE = None
        _fail(f"injected nested-creator fault after {phase}")


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if type(value) in {list, tuple}:
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class NativeProtocolFrameV1:
    opcode: int
    sequence: int
    nonce: bytes
    pid: int
    status: int = 0
    flags: int = 0
    fact_a: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.opcode) is not int
            or self.opcode not in role_v1.OPCODES.values()
            or type(self.sequence) is not int
            or not 0 <= self.sequence < 1 << 64
            or type(self.nonce) is not bytes
            or len(self.nonce) != 16
            or type(self.pid) is not int
            or not -(1 << 63) <= self.pid < 1 << 63
            or type(self.status) is not int
            or not -(1 << 31) <= self.status < 1 << 31
            or type(self.flags) is not int
            or not 0 <= self.flags < 1 << 32
            or type(self.fact_a) is not int
            or not 0 <= self.fact_a < 1 << 64
        ):
            _fail("nested-creator protocol frame fields are not exact")

    def to_bytes(self) -> bytes:
        return FRAME.pack(
            role_v1.FRAME_MAGIC,
            role_v1.FRAME_VERSION,
            self.opcode,
            self.sequence,
            self.nonce,
            self.pid,
            self.status,
            self.flags,
            self.fact_a,
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> "NativeProtocolFrameV1":
        if type(raw) is not bytes or len(raw) != FRAME_BYTES:
            _fail("nested-creator protocol frame byte count changed")
        magic, version, opcode, sequence, nonce, pid, status, flags, fact_a = (
            FRAME.unpack(raw)
        )
        if magic != role_v1.FRAME_MAGIC or version != role_v1.FRAME_VERSION:
            _fail("nested-creator protocol frame identity changed")
        return cls(opcode, sequence, nonce, pid, status, flags, fact_a)


@dataclass(frozen=True, slots=True)
class NestedCreatorProbeRawFactsV1:
    """Issuer-only raw facts; intentionally not a certificate artifact."""

    supervisor_pid: int
    supervisor_start_ticks: int
    probe_pid: int
    probe_start_ticks: int
    nonce: bytes = field(repr=False)
    parent_return_frame: NativeProtocolFrameV1
    child_withdrawn_frame: NativeProtocolFrameV1
    child_ready_frame: NativeProtocolFrameV1
    child_release_echo_frame: NativeProtocolFrameV1
    creator_reap_frame: NativeProtocolFrameV1
    pid_cell_value: int
    pidfd_fact: Mapping[str, int]
    live_cgroup_snapshots: tuple[Mapping[str, Any], Mapping[str, Any]]
    post_reap_cgroup_snapshots: tuple[Mapping[str, Any], Mapping[str, Any]]
    guardian_waitid_errno: int
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer is not _FACTS_ISSUER:
            _fail("nested-creator raw facts are caller-minted")
        object.__setattr__(self, "pidfd_fact", _freeze_json(self.pidfd_fact))
        object.__setattr__(
            self,
            "live_cgroup_snapshots",
            _freeze_json(self.live_cgroup_snapshots),
        )
        object.__setattr__(
            self,
            "post_reap_cgroup_snapshots",
            _freeze_json(self.post_reap_cgroup_snapshots),
        )

    def __copy__(self) -> NoReturn:
        _fail("nested-creator raw facts cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("nested-creator raw facts cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("nested-creator raw facts cannot be copied or pickled")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_nested_creator_probe_raw_facts.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "supervisor_pid": self.supervisor_pid,
            "supervisor_start_ticks": self.supervisor_start_ticks,
            "probe_pid": self.probe_pid,
            "probe_start_ticks": self.probe_start_ticks,
            "nonce_hex": self.nonce.hex(),
            "parent_return_frame": _frame_document(self.parent_return_frame),
            "child_withdrawn_frame": _frame_document(self.child_withdrawn_frame),
            "child_ready_frame": _frame_document(self.child_ready_frame),
            "child_release_echo_frame": _frame_document(
                self.child_release_echo_frame
            ),
            "creator_reap_frame": _frame_document(self.creator_reap_frame),
            "pid_cell_value": self.pid_cell_value,
            "pidfd_fact": _thaw_json(self.pidfd_fact),
            "live_cgroup_snapshots": _thaw_json(self.live_cgroup_snapshots),
            "post_reap_cgroup_snapshots": _thaw_json(
                self.post_reap_cgroup_snapshots
            ),
            "guardian_waitid_errno": self.guardian_waitid_errno,
            "actual_nested_pidfd_probe_birth_present": True,
            "actual_non_guardian_creator_reap_present": True,
            "guardian_independent_pid_cell_pidfd_cgroup_join_present": True,
            "gated_supervisor_birth_authority_present": False,
            "two_birth_prefix_authority_present": False,
            "five_birth_process_authority_present": False,
            "production_shared_resource_receipts_present": False,
            "official_execution_allowed": False,
        }


@dataclass(frozen=True, slots=True)
class NestedCreatorProbeObservedFactsV2:
    """V1 semantics plus replayable SCM/rights receive observations."""

    raw_facts_v1: NestedCreatorProbeRawFactsV1 = field(repr=False)
    supervisor_ready_observation: Mapping[str, Any]
    protocol_receive_observations: tuple[Mapping[str, Any], ...]
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _FACTS_ISSUER
            or type(self.raw_facts_v1) is not NestedCreatorProbeRawFactsV1
            or self.raw_facts_v1._issuer is not _FACTS_ISSUER
        ):
            _fail("nested-creator observed V2 facts are caller-minted")
        object.__setattr__(
            self,
            "supervisor_ready_observation",
            _freeze_json(self.supervisor_ready_observation),
        )
        object.__setattr__(
            self,
            "protocol_receive_observations",
            _freeze_json(self.protocol_receive_observations),
        )

    def __copy__(self) -> NoReturn:
        _fail("nested-creator observed V2 facts cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("nested-creator observed V2 facts cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("nested-creator observed V2 facts cannot be copied or pickled")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_nested_creator_probe_observed_facts.v2",
            "schema_version": "2.0.0",
            "profile_key": (
                "construction_k7_h1_nested_creator_probe_observed_v2"
            ),
            "raw_facts_v1": self.raw_facts_v1.to_document(),
            "supervisor_ready_observation": _thaw_json(
                self.supervisor_ready_observation
            ),
            "protocol_receive_observations": _thaw_json(
                self.protocol_receive_observations
            ),
            "nested_receive_credential_observations_present": True,
            "nested_receive_rights_observations_present": True,
            "portable_checkpoint_authority_present": False,
            "two_birth_prefix_authority_present": False,
            "official_execution_allowed": False,
        }


@dataclass(slots=True)
class NestedCreatorProbeLiveSessionV1:
    """Owner-bound exact native SUPERVISOR session after its READY frame."""

    supervisor_pid: int
    supervisor_start_ticks: int
    supervisor_pidfd: int = field(repr=False)
    control_fd: int = field(repr=False)
    guardian_pid: int
    guardian_uid: int
    guardian_gid: int
    owner_pid: int
    owner_thread_id: int
    state: str
    supervisor_ready_observation: Mapping[str, Any] = field(
        default_factory=dict, repr=False
    )
    active_probe_pid: int = -1
    raw_facts: NestedCreatorProbeRawFactsV1 | None = field(default=None, repr=False)
    observed_facts_v2: NestedCreatorProbeObservedFactsV2 | None = field(
        default=None, repr=False
    )
    abort_facts: Mapping[str, Any] | None = field(default=None, repr=False)
    shutdown_frame: NativeProtocolFrameV1 | None = field(default=None, repr=False)
    finish_facts: Mapping[str, Any] | None = field(default=None, repr=False)
    _issuer: object = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _SESSION_ISSUER:
            _fail("nested-creator live session is caller-minted")
        self.supervisor_ready_observation = _freeze_json(
            self.supervisor_ready_observation
        )
    def __copy__(self) -> NoReturn:
        _fail("nested-creator live session cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("nested-creator live session cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("nested-creator live session cannot be copied or pickled")


@dataclass(slots=True)
class _LiveSessionOwnershipV1:
    """Single trusted authority for one caller-visible mutable session."""

    session: NestedCreatorProbeLiveSessionV1
    supervisor_pid: int
    supervisor_start_ticks: int
    supervisor_pidfd: int
    supervisor_pidfd_device: int
    supervisor_pidfd_inode: int
    control_fd: int
    control_socket_device: int
    control_socket_inode: int
    control_peer_credentials: tuple[int, int, int]
    guardian_pid: int
    guardian_uid: int
    guardian_gid: int
    owner_pid: int
    owner_thread_id: int
    state: str
    control_open: bool = True
    pidfd_open: bool = True
    active_probe_pid: int = -1
    active_probe_start_ticks: int = -1
    probe_command_issued: bool = False
    control_cgroup_device: int | None = None
    control_cgroup_inode: int | None = None
    shutdown_frame: NativeProtocolFrameV1 | None = None
    finish_facts: Mapping[str, Any] | None = None
    abort_facts: Mapping[str, Any] | None = None


class _LiveSessionRegistryV1:
    """One-record registry with a narrow legacy observation surface."""

    __slots__ = ("_records",)

    def __init__(self) -> None:
        self._records: dict[int, _LiveSessionOwnershipV1] = {}

    def __len__(self) -> int:
        return len(self._records)

    def __bool__(self) -> bool:
        return bool(self._records)

    def get(
        self, key: int, default: Any = None
    ) -> NestedCreatorProbeLiveSessionV1 | Any:
        record = self._records.get(key)
        return record.session if record is not None else default

    def values(self) -> tuple[NestedCreatorProbeLiveSessionV1, ...]:
        return tuple(record.session for record in self._records.values())

    def record(
        self, session: NestedCreatorProbeLiveSessionV1
    ) -> _LiveSessionOwnershipV1 | None:
        record = self._records.get(id(session))
        return record if record is not None and record.session is session else None

    def register(self, record: _LiveSessionOwnershipV1) -> None:
        key = id(record.session)
        if key in self._records:
            _fail("nested-creator live session identity was reused")
        self._records[key] = record

    def remove(self, session: NestedCreatorProbeLiveSessionV1) -> None:
        key = id(session)
        record = self._records.get(key)
        if record is None or record.session is not session:
            _fail("nested-creator live session registry removal changed")
        del self._records[key]

    def records(self) -> tuple[_LiveSessionOwnershipV1, ...]:
        return tuple(self._records.values())

    def clear(self) -> None:
        self._records.clear()


_LIVE_SESSIONS = _LiveSessionRegistryV1()


def _socket_peer_credentials(descriptor: int) -> tuple[int, int, int]:
    try:
        wrapper = socket.socket(fileno=descriptor)
        try:
            raw = wrapper.getsockopt(
                socket.SOL_SOCKET, socket.SO_PEERCRED, UCRED.size
            )
        finally:
            wrapper.detach()
    except OSError as error:
        raise ConstructionK7H1NestedCreatorProbeNativeV1Error(
            "nested-creator control SO_PEERCRED is unavailable"
        ) from error
    if type(raw) is not bytes or len(raw) != UCRED.size:
        _fail("nested-creator control SO_PEERCRED byte count changed")
    return UCRED.unpack(raw)


def _frame_document(frame: NativeProtocolFrameV1) -> dict[str, Any]:
    return {
        "opcode": frame.opcode,
        "sequence": frame.sequence,
        "nonce_hex": frame.nonce.hex(),
        "pid": frame.pid,
        "status": frame.status,
        "flags": frame.flags,
        "fact_a": frame.fact_a,
    }


def _read_start_ticks(pid: int) -> int:
    try:
        raw = Path(f"/proc/{pid}/stat").read_bytes()
    except OSError as error:
        raise ConstructionK7H1NestedCreatorProbeNativeV1Error(
            "nested-creator process stat is unavailable"
        ) from error
    close = raw.rfind(b")")
    fields = raw[close + 2 :].split() if close >= 0 else []
    if len(fields) < 20 or not fields[19].isdigit():
        _fail("nested-creator process start ticks are malformed")
    return int(fields[19])


def _read_parent_pid(pid: int) -> int:
    try:
        raw = Path(f"/proc/{pid}/stat").read_bytes()
    except OSError as error:
        raise ConstructionK7H1NestedCreatorProbeNativeV1Error(
            "nested-creator process parent stat is unavailable"
        ) from error
    close = raw.rfind(b")")
    fields = raw[close + 2 :].split() if close >= 0 else []
    if len(fields) < 2 or not fields[1].isdigit():
        _fail("nested-creator process parent PID is malformed")
    return int(fields[1])


def _direct_child_pids() -> tuple[int, ...]:
    try:
        raw = Path(
            f"/proc/self/task/{threading.get_native_id()}/children"
        ).read_text(encoding="ascii").strip()
    except OSError as error:
        raise ConstructionK7H1NestedCreatorProbeNativeV1Error(
            "nested-creator direct-child inventory is unavailable"
        ) from error
    if not raw:
        return ()
    fields = raw.split()
    if any(not field.isdigit() or int(field) <= 0 for field in fields):
        _fail("nested-creator direct-child inventory is malformed")
    values = tuple(sorted(int(field) for field in fields))
    if len(values) != len(set(values)):
        _fail("nested-creator direct-child inventory contains a duplicate")
    return values


def _pidfd_fact(descriptor: int) -> dict[str, int]:
    try:
        raw = Path(f"/proc/self/fdinfo/{descriptor}").read_text(encoding="ascii")
    except OSError as error:
        raise ConstructionK7H1NestedCreatorProbeNativeV1Error(
            "nested-creator pidfd fdinfo is unavailable"
        ) from error
    values: dict[str, int] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        value = value.strip()
        if name in {"Pid", "NSpid"} and value.lstrip("-").isdigit():
            values[name.lower()] = int(value)
    if values.get("pid", -1) <= 0:
        _fail("nested-creator pidfd does not identify a live namespace PID")
    status = os.fstat(descriptor)
    return {
        "pid": values["pid"],
        "nspid": values.get("nspid", values["pid"]),
        "device": status.st_dev,
        "inode": status.st_ino,
    }


def _set_passcred(descriptor: int, enabled: bool) -> None:
    wrapper = socket.socket(fileno=descriptor)
    try:
        wrapper.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, int(enabled))
        if wrapper.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED) != int(enabled):
            _fail("nested-creator SO_PASSCRED state changed")
    finally:
        wrapper.detach()


def _recv_frame(
    descriptor: int,
    *,
    expected_credentials: tuple[int, int, int],
    expected_rights: int,
    observation_sink: list[dict[str, Any]] | None = None,
) -> tuple[NativeProtocolFrameV1, list[int]]:
    wrapper = socket.socket(fileno=descriptor)
    rights: list[int] = []
    credentials: list[tuple[int, int, int]] = []
    installed: list[int] = []
    try:
        peer_address = wrapper.getpeername()
        raw, ancillary, flags, address = wrapper.recvmsg(
            MAX_FRAME_BYTES,
            socket.CMSG_SPACE(4 * array("i").itemsize)
            + socket.CMSG_SPACE(UCRED.size),
            getattr(socket, "MSG_CMSG_CLOEXEC", 0),
        )
        address_is_connected_peer = address in {None, "", b""} or address == peer_address
        address_is_linux_autobind = (
            type(address) is bytes
            and len(address) == 6
            and address[:1] == b"\x00"
            and all(value in _ABSTRACT_AUTOBIND_HEX for value in address[1:])
        )
        if (
            type(address) not in {str, bytes, type(None)}
            or not (address_is_connected_peer or address_is_linux_autobind)
            or len(raw) != FRAME_BYTES
            or flags & REJECTED_RECV_FLAGS
            or flags & ~ALLOWED_RECV_FLAGS
        ):
            _fail(
                "nested-creator seqpacket payload or return flags changed: "
                f"bytes={len(raw)}, flags={flags:#x}, address={address!r}, "
                f"ancillary={[(level, kind, len(data)) for level, kind, data in ancillary]}"
            )
        for level, kind, data in ancillary:
            if level != socket.SOL_SOCKET:
                _fail("nested-creator seqpacket installed an unknown cmsg level")
            if kind == socket.SCM_CREDENTIALS:
                if len(data) != UCRED.size or credentials:
                    _fail("nested-creator SCM_CREDENTIALS grammar changed")
                credentials.append(UCRED.unpack(data))
            elif kind == socket.SCM_RIGHTS:
                if not data or len(data) % array("i").itemsize or rights:
                    _fail("nested-creator SCM_RIGHTS grammar changed")
                received = array("i")
                received.frombytes(data)
                installed.extend(int(value) for value in received)
                rights.extend(installed)
            else:
                _fail("nested-creator seqpacket installed an unknown ancillary")
        if credentials != [expected_credentials] or len(rights) != expected_rights:
            _fail("nested-creator credentials or rights count changed")
        if any(
            descriptor_value < 0
            or fcntl.fcntl(descriptor_value, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
            for descriptor_value in rights
        ):
            _fail("nested-creator installed right lost CLOEXEC")
        frame = NativeProtocolFrameV1.from_bytes(raw)
        if observation_sink is not None:
            if type(observation_sink) is not list:
                _fail("nested-creator observation sink changed type")
            if address is None:
                address_document: dict[str, Any] = {"kind": "NONE"}
            elif type(address) is str:
                address_document = {"kind": "TEXT", "value": address}
            else:
                address_document = {
                    "kind": "BYTES_HEX",
                    "value": address.hex(),
                }
            if peer_address is None:
                peer_document: dict[str, Any] = {"kind": "NONE"}
            elif type(peer_address) is str:
                peer_document = {"kind": "TEXT", "value": peer_address}
            else:
                peer_document = {
                    "kind": "BYTES_HEX",
                    "value": peer_address.hex(),
                }
            observation_sink.append(
                {
                    "event_index": len(observation_sink),
                    "opcode": frame.opcode,
                    "sequence": frame.sequence,
                    "frame_pid": frame.pid,
                    "payload_sha256": hashlib.sha256(raw).hexdigest(),
                    "payload_byte_count": len(raw),
                    "raw_payload_hex": raw.hex(),
                    "decoded_frame": {
                        "opcode": frame.opcode,
                        "sequence": frame.sequence,
                        "nonce_hex": frame.nonce.hex(),
                        "pid": frame.pid,
                        "status": frame.status,
                        "flags": frame.flags,
                        "fact_a": frame.fact_a,
                    },
                    "credentials": {
                        "pid": credentials[0][0],
                        "uid": credentials[0][1],
                        "gid": credentials[0][2],
                    },
                    "rights_count": len(rights),
                    "installed_pidfd_facts": [
                        {
                            **_pidfd_fact(installed_fd),
                            "descriptor_flags": fcntl.fcntl(
                                installed_fd, fcntl.F_GETFD
                            ),
                            "cloexec": bool(
                                fcntl.fcntl(installed_fd, fcntl.F_GETFD)
                                & fcntl.FD_CLOEXEC
                            ),
                        }
                        for installed_fd in rights
                    ],
                    "recv_flags": flags,
                    "address": address_document,
                    "connected_peer_address": peer_document,
                    "ancillary": [
                        {
                            "level": level,
                            "kind": kind,
                            "byte_count": len(data),
                            "data_hex": data.hex(),
                        }
                        for level, kind, data in ancillary
                    ],
                }
            )
        return frame, rights
    except BaseException:
        for installed_fd in installed:
            try:
                os.close(installed_fd)
            except OSError:
                pass
        raise
    finally:
        wrapper.detach()


def _send_frame(
    descriptor: int,
    frame: NativeProtocolFrameV1,
    rights: tuple[int, ...] = (),
) -> None:
    wrapper = socket.socket(fileno=descriptor)
    try:
        ancillary = []
        if rights:
            right_array = array("i", rights)
            ancillary.append(
                (socket.SOL_SOCKET, socket.SCM_RIGHTS, right_array.tobytes())
            )
        sent = wrapper.sendmsg(
            [frame.to_bytes()], ancillary, getattr(socket, "MSG_NOSIGNAL", 0)
        )
        if sent != FRAME_BYTES:
            _fail("nested-creator seqpacket send was short")
    finally:
        wrapper.detach()


def _read_control(
    directory_fd: int,
    name: str,
    cap: int = 65536,
    *,
    allow_empty: bool = False,
) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        raw = os.read(descriptor, cap + 1)
    finally:
        os.close(descriptor)
    if (not raw and not allow_empty) or len(raw) > cap:
        _fail(f"nested-creator {name} exceeded its exact bound")
    return raw


def _write_control(directory_fd: int, name: str, raw: bytes) -> None:
    descriptor = os.open(name, os.O_WRONLY | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                _fail(f"nested-creator {name} write was short")
            offset += written
    finally:
        os.close(descriptor)


def _parse_pid_lines(raw: bytes) -> list[int]:
    rows = raw.splitlines()
    if any(not row.isdigit() for row in rows):
        _fail("nested-creator cgroup.procs contains a malformed PID")
    values = sorted(int(row) for row in rows)
    if len(values) != len(set(values)):
        _fail("nested-creator cgroup.procs contains a duplicate PID")
    return values


def _parse_single(raw: bytes, label: str) -> int:
    stripped = raw.strip()
    if not stripped.isdigit():
        _fail(f"nested-creator {label} is not one nonnegative integer")
    return int(stripped)


def _parse_events(raw: bytes) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) != 2 or not fields[1].isdigit():
            _fail("nested-creator cgroup.events grammar changed")
        key = fields[0].decode("ascii")
        if key in result:
            _fail("nested-creator cgroup.events contains a duplicate key")
        result[key] = int(fields[1])
    if "populated" not in result:
        _fail("nested-creator cgroup.events lacks populated")
    return result


def _cgroup_snapshot(
    directory_fd: int,
    *,
    expected_pids: tuple[int, ...],
    sequence: int,
) -> dict[str, Any]:
    first = _parse_pid_lines(
        _read_control(directory_fd, "cgroup.procs", allow_empty=True)
    )
    events = _parse_events(_read_control(directory_fd, "cgroup.events"))
    current = _parse_single(_read_control(directory_fd, "pids.current"), "pids.current")
    second = _parse_pid_lines(
        _read_control(directory_fd, "cgroup.procs", allow_empty=True)
    )
    expected = sorted(expected_pids)
    if (
        first != expected
        or second != expected
        or events["populated"] != int(bool(expected))
        or current != len(expected)
    ):
        _fail("nested-creator cgroup membership snapshot changed")
    status = os.fstat(directory_fd)
    return {
        "sequence": sequence,
        "directory_device": status.st_dev,
        "directory_inode": status.st_ino,
        "first_cgroup_procs": first,
        "events": dict(sorted(events.items())),
        "pids_current": current,
        "second_cgroup_procs": second,
    }


def _wait_for_snapshot(
    directory_fd: int,
    *,
    expected_pids: tuple[int, ...],
    sequence: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + PROTOCOL_TIMEOUT_SECONDS
    while True:
        try:
            return _cgroup_snapshot(
                directory_fd, expected_pids=expected_pids, sequence=sequence
            )
        except ConstructionK7H1NestedCreatorProbeNativeV1Error:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.005)


def _require_live_pidfd(descriptor: int) -> None:
    poller = select.poll()
    poller.register(descriptor, select.POLLIN)
    if poller.poll(0):
        _fail("nested-creator pidfd was not live")


def _require_dead_pidfd(descriptor: int) -> None:
    poller = select.poll()
    poller.register(descriptor, select.POLLIN)
    events = poller.poll(int(PROTOCOL_TIMEOUT_SECONDS * 1000))
    if (
        len(events) != 1
        or events[0][0] != descriptor
        or events[0][1] & select.POLLIN == 0
        or events[0][1] & (select.POLLERR | select.POLLNVAL)
    ):
        _fail("nested-creator pidfd did not reach exact death readiness")


def _drain_exact_owned_children_after_kill(
    expected_pids: tuple[int, ...],
) -> tuple[dict[str, int], ...]:
    """Reap only registered children; never let P_ALL consume unrelated work."""

    deadline = time.monotonic() + PROTOCOL_TIMEOUT_SECONDS
    facts: list[dict[str, int]] = []
    remaining = set(expected_pids)
    while remaining:
        progressed = False
        for child_pid in tuple(sorted(remaining)):
            try:
                result = os.waitid(os.P_PID, child_pid, os.WEXITED | os.WNOHANG)
            except ChildProcessError:
                result = None
                if not Path(f"/proc/{child_pid}").exists():
                    remaining.remove(child_pid)
                    progressed = True
            except OSError as error:
                if error.errno != errno.ECHILD:
                    raise
                result = None
                if not Path(f"/proc/{child_pid}").exists():
                    remaining.remove(child_pid)
                    progressed = True
            if result is not None:
                facts.append(
                    {
                        name: int(getattr(result, name))
                        for name in (
                            "si_pid",
                            "si_uid",
                            "si_signo",
                            "si_status",
                            "si_code",
                        )
                    }
                )
                remaining.remove(child_pid)
                progressed = True
        if remaining and not progressed:
            if time.monotonic() >= deadline:
                _fail("nested-creator abort children did not become waitable")
            time.sleep(0.005)
    if _direct_child_pids():
        _fail("nested-creator abort left a direct child")
    return tuple(facts)


def _block_terminal_signals() -> set[signal.Signals]:
    blockable = signal.valid_signals() - {signal.SIGKILL, signal.SIGSTOP}
    return signal.pthread_sigmask(signal.SIG_BLOCK, blockable)


def _restore_terminal_signals(previous: set[signal.Signals]) -> None:
    signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def _close_finish_forward(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError as error:
        if error.errno != errno.EBADF:
            raise


def _stable_control_cgroup_members(directory_fd: int) -> tuple[int, ...]:
    first = tuple(
        _parse_pid_lines(
            _read_control(directory_fd, "cgroup.procs", allow_empty=True)
        )
    )
    second = tuple(
        _parse_pid_lines(
            _read_control(directory_fd, "cgroup.procs", allow_empty=True)
        )
    )
    if first != second or len(first) > 2:
        _fail("nested-creator cleanup cgroup membership was not exclusive")
    return first


def observe_nested_creator_control_population_v1(
    directory_fd: int,
    *,
    expected_pids: tuple[int, ...],
    sequence: int,
) -> dict[str, Any]:
    """Public raw cgroup observation; it mints no artifact or authority."""

    if (
        type(directory_fd) is not int
        or directory_fd < 0
        or type(expected_pids) is not tuple
        or any(type(pid) is not int or pid <= 0 for pid in expected_pids)
        or len(expected_pids) != len(set(expected_pids))
        or type(sequence) is not int
        or sequence < 0
    ):
        _fail("nested-creator raw cgroup observation inputs changed")
    return _cgroup_snapshot(
        directory_fd, expected_pids=expected_pids, sequence=sequence
    )


def begin_nested_creator_supervisor_session_v1(
    *,
    supervisor_pid: int,
    supervisor_pidfd: int,
    control_fd: int,
) -> NestedCreatorProbeLiveSessionV1:
    """Accept exactly one READY from the registered source-closed role."""

    role_v1.verify_nested_creator_supervisor_native_image_v1()
    if (
        type(supervisor_pid) is not int
        or supervisor_pid <= 0
        or type(supervisor_pidfd) is not int
        or supervisor_pidfd < 0
        or type(control_fd) is not int
        or control_fd < 0
        or os.getpid() == supervisor_pid
    ):
        _fail("nested-creator supervisor session inputs are invalid")
    try:
        initial_control_status = os.fstat(control_fd)
        initial_control_flags = fcntl.fcntl(control_fd, fcntl.F_GETFD)
        initial_pidfd_flags = fcntl.fcntl(supervisor_pidfd, fcntl.F_GETFD)
    except OSError as error:
        raise ConstructionK7H1NestedCreatorProbeNativeV1Error(
            "nested-creator supervisor session descriptors are unavailable"
        ) from error
    if (
        not stat.S_ISSOCK(initial_control_status.st_mode)
        or initial_control_flags & fcntl.FD_CLOEXEC == 0
        or initial_pidfd_flags & fcntl.FD_CLOEXEC == 0
    ):
        _fail("nested-creator supervisor session descriptor contract changed")
    _set_passcred(control_fd, True)
    expected_credentials = (supervisor_pid, os.getuid(), os.getgid())
    ready_observations: list[dict[str, Any]] = []
    frame, rights = _recv_frame(
        control_fd,
        expected_credentials=expected_credentials,
        expected_rights=0,
        observation_sink=ready_observations,
    )
    if rights or frame != NativeProtocolFrameV1(
        role_v1.OPCODES["SUPERVISOR_READY"],
        0,
        EMPTY_NONCE,
        supervisor_pid,
        fact_a=os.getpid(),
    ):
        _fail("nested-creator SUPERVISOR_READY frame changed")
    pidfd = _pidfd_fact(supervisor_pidfd)
    start_ticks = _read_start_ticks(supervisor_pid)
    if pidfd["pid"] != supervisor_pid:
        _fail("nested-creator supervisor pidfd identity changed")
    _require_live_pidfd(supervisor_pidfd)
    if _direct_child_pids() != (supervisor_pid,):
        _fail("nested-creator supervisor was not the sole direct child")
    control_status = os.fstat(control_fd)
    pidfd_status = os.fstat(supervisor_pidfd)
    control_peer_credentials = _socket_peer_credentials(control_fd)
    session = NestedCreatorProbeLiveSessionV1(
        supervisor_pid=supervisor_pid,
        supervisor_start_ticks=start_ticks,
        supervisor_pidfd=supervisor_pidfd,
        control_fd=control_fd,
        guardian_pid=os.getpid(),
        guardian_uid=os.getuid(),
        guardian_gid=os.getgid(),
        owner_pid=os.getpid(),
        owner_thread_id=threading.get_ident(),
        state="SUPERVISOR_READY",
        supervisor_ready_observation=_freeze_json(ready_observations[0]),
        _issuer=_SESSION_ISSUER,
    )
    record = _LiveSessionOwnershipV1(
        session=session,
        supervisor_pid=supervisor_pid,
        supervisor_start_ticks=start_ticks,
        supervisor_pidfd=supervisor_pidfd,
        supervisor_pidfd_device=pidfd_status.st_dev,
        supervisor_pidfd_inode=pidfd_status.st_ino,
        control_fd=control_fd,
        control_socket_device=control_status.st_dev,
        control_socket_inode=control_status.st_ino,
        control_peer_credentials=control_peer_credentials,
        guardian_pid=os.getpid(),
        guardian_uid=os.getuid(),
        guardian_gid=os.getgid(),
        owner_pid=os.getpid(),
        owner_thread_id=threading.get_ident(),
        state="SUPERVISOR_READY",
    )
    with _SESSION_LOCK:
        _LIVE_SESSIONS.register(record)
        try:
            _test_fault("AFTER_SESSION_RECORD_REGISTER")
        except BaseException:
            _LIVE_SESSIONS.remove(session)
            raise
    return session


def _require_session(
    session: NestedCreatorProbeLiveSessionV1, *, allowed_states: set[str]
) -> _LiveSessionOwnershipV1:
    with _SESSION_LOCK:
        record = _LIVE_SESSIONS.record(session)
    if (
        type(session) is not NestedCreatorProbeLiveSessionV1
        or session._issuer is not _SESSION_ISSUER
        or record is None
        or record.owner_pid != os.getpid()
        or record.owner_thread_id != threading.get_ident()
        or session.owner_pid != record.owner_pid
        or session.owner_thread_id != record.owner_thread_id
        or session.guardian_pid != record.guardian_pid
        or session.guardian_uid != record.guardian_uid
        or session.guardian_gid != record.guardian_gid
        or session.supervisor_pid != record.supervisor_pid
        or session.supervisor_start_ticks != record.supervisor_start_ticks
        or session.supervisor_pidfd
        != (record.supervisor_pidfd if record.pidfd_open else -1)
        or session.control_fd != (record.control_fd if record.control_open else -1)
        or session.state != record.state
        or record.state not in allowed_states
        or session.active_probe_pid != record.active_probe_pid
        or _pidfd_fact(record.supervisor_pidfd)["pid"] != record.supervisor_pid
        or _read_start_ticks(record.supervisor_pid)
        != record.supervisor_start_ticks
    ):
        _fail("nested-creator live session identity or state changed")
    try:
        control_status = os.fstat(record.control_fd)
        pidfd_status = os.fstat(record.supervisor_pidfd)
    except OSError as error:
        raise ConstructionK7H1NestedCreatorProbeNativeV1Error(
            "nested-creator live session descriptor identity is unavailable"
        ) from error
    if (
        control_status.st_dev != record.control_socket_device
        or control_status.st_ino != record.control_socket_inode
        or pidfd_status.st_dev != record.supervisor_pidfd_device
        or pidfd_status.st_ino != record.supervisor_pidfd_inode
        or _socket_peer_credentials(record.control_fd)
        != record.control_peer_credentials
    ):
        _fail("nested-creator live session descriptor identity changed")
    _require_live_pidfd(record.supervisor_pidfd)
    return record


def _require_terminal_session_identity(
    session: NestedCreatorProbeLiveSessionV1,
    *,
    allowed_states: set[str],
    require_control: bool,
) -> _LiveSessionOwnershipV1:
    """Validate frozen authority before any destructive close or wait."""

    with _SESSION_LOCK:
        record = _LIVE_SESSIONS.record(session)
    if (
        type(session) is not NestedCreatorProbeLiveSessionV1
        or session._issuer is not _SESSION_ISSUER
        or record is None
        or record.owner_pid != os.getpid()
        or record.owner_thread_id != threading.get_ident()
        or session.owner_pid != record.owner_pid
        or session.owner_thread_id != record.owner_thread_id
        or session.guardian_pid != record.guardian_pid
        or session.guardian_uid != record.guardian_uid
        or session.guardian_gid != record.guardian_gid
        or session.supervisor_pid != record.supervisor_pid
        or session.supervisor_start_ticks != record.supervisor_start_ticks
        or record.state not in allowed_states
        or not record.pidfd_open
        or require_control != record.control_open
    ):
        _fail("nested-creator terminal session authority changed")
    try:
        pidfd_status = os.fstat(record.supervisor_pidfd)
        pidfd_flags = fcntl.fcntl(record.supervisor_pidfd, fcntl.F_GETFD)
    except OSError as error:
        raise ConstructionK7H1NestedCreatorProbeNativeV1Error(
            "nested-creator terminal pidfd identity is unavailable"
        ) from error
    if (
        pidfd_status.st_dev != record.supervisor_pidfd_device
        or pidfd_status.st_ino != record.supervisor_pidfd_inode
        or pidfd_flags & fcntl.FD_CLOEXEC == 0
        or _pidfd_fact(record.supervisor_pidfd)["pid"] != record.supervisor_pid
    ):
        _fail("nested-creator terminal pidfd identity changed")
    if require_control:
        try:
            control_status = os.fstat(record.control_fd)
            control_flags = fcntl.fcntl(record.control_fd, fcntl.F_GETFD)
        except OSError as error:
            raise ConstructionK7H1NestedCreatorProbeNativeV1Error(
                "nested-creator terminal control identity is unavailable"
            ) from error
        if (
            control_status.st_dev != record.control_socket_device
            or control_status.st_ino != record.control_socket_inode
            or control_flags & fcntl.FD_CLOEXEC == 0
            or _socket_peer_credentials(record.control_fd)
            != record.control_peer_credentials
        ):
            _fail("nested-creator terminal control identity changed")
    return record


def verify_nested_creator_live_session_v1(
    session: NestedCreatorProbeLiveSessionV1,
) -> Mapping[str, Any]:
    """Recheck one owner-bound live session without changing its state."""

    record = _require_session(
        session,
        allowed_states={"SUPERVISOR_READY", "PROBE_REAPED_SUPERVISOR_LIVE"},
    )
    if (
        record.guardian_pid != os.getpid()
        or record.guardian_uid != os.getuid()
        or record.guardian_gid != os.getgid()
        or record.control_fd < 0
    ):
        _fail("nested-creator live session guardian identity changed")
    try:
        control_status = os.fstat(record.control_fd)
        control_flags = fcntl.fcntl(record.control_fd, fcntl.F_GETFD)
        wrapper = socket.socket(fileno=record.control_fd)
        try:
            socket_type = wrapper.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
            passcred = wrapper.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED)
            peer_address = wrapper.getpeername()
        finally:
            wrapper.detach()
    except OSError as error:
        raise ConstructionK7H1NestedCreatorProbeNativeV1Error(
            "nested-creator live session control channel is unavailable"
        ) from error
    peer_credentials = _socket_peer_credentials(record.control_fd)
    if (
        not stat.S_ISSOCK(control_status.st_mode)
        or socket_type != socket.SOCK_SEQPACKET
        or passcred != 1
        or control_flags & fcntl.FD_CLOEXEC == 0
        or control_status.st_dev != record.control_socket_device
        or control_status.st_ino != record.control_socket_inode
        or peer_credentials != record.control_peer_credentials
    ):
        _fail("nested-creator live session control channel identity changed")
    if peer_address is None:
        peer_document: dict[str, Any] = {"kind": "NONE"}
    elif type(peer_address) is str:
        peer_document = {"kind": "TEXT", "value": peer_address}
    elif type(peer_address) is bytes:
        peer_document = {"kind": "BYTES_HEX", "value": peer_address.hex()}
    else:
        _fail("nested-creator live session peer address type changed")
    pidfd_flags = fcntl.fcntl(record.supervisor_pidfd, fcntl.F_GETFD)
    pidfd_status = os.fstat(record.supervisor_pidfd)
    if (
        pidfd_flags & fcntl.FD_CLOEXEC == 0
        or pidfd_status.st_dev != record.supervisor_pidfd_device
        or pidfd_status.st_ino != record.supervisor_pidfd_inode
    ):
        _fail("nested-creator live session pidfd identity changed")
    facts = {
        "profile_key": PROFILE_KEY,
        "session_state": record.state,
        "supervisor_pid": record.supervisor_pid,
        "supervisor_start_ticks": record.supervisor_start_ticks,
        "supervisor_pidfd_fact": _pidfd_fact(record.supervisor_pidfd),
        "supervisor_pidfd_cloexec": bool(pidfd_flags & fcntl.FD_CLOEXEC),
        "control_socket_fact": {
            "device": control_status.st_dev,
            "inode": control_status.st_ino,
            "socket_type": socket_type,
            "passcred": passcred,
            "descriptor_flags": control_flags,
            "cloexec": bool(control_flags & fcntl.FD_CLOEXEC),
            "connected_peer_address": peer_document,
            "peer_credentials": {
                "pid": peer_credentials[0],
                "uid": peer_credentials[1],
                "gid": peer_credentials[2],
            },
        },
        "owner_pid": record.owner_pid,
        "owner_thread_id": record.owner_thread_id,
        "active_probe_pid": record.active_probe_pid,
        "live_session_verified": True,
        "verification_mutated_session": False,
    }
    return _freeze_json(facts)


def _run_nested_creator_pidfd_probe_impl_v1(
    session: NestedCreatorProbeLiveSessionV1,
    *,
    control_cgroup_fd: int,
    observation_sink: list[dict[str, Any]] | None,
) -> NestedCreatorProbeRawFactsV1:
    """Run one real nested probe and leave the exact supervisor live."""

    record = _require_session(session, allowed_states={"SUPERVISOR_READY"})
    if type(control_cgroup_fd) is not int or control_cgroup_fd < 0:
        _fail("nested-creator CONTROL cgroup descriptor is invalid")
    cgroup_status = os.fstat(control_cgroup_fd)
    before = _cgroup_snapshot(
        control_cgroup_fd,
        expected_pids=(session.supervisor_pid,),
        sequence=0,
    )
    del before
    with _SESSION_LOCK:
        if record.control_cgroup_device is not None:
            _fail("nested-creator control cgroup lease was already registered")
        record.control_cgroup_device = cgroup_status.st_dev
        record.control_cgroup_inode = cgroup_status.st_ino
    parent_gate: socket.socket | None = None
    child_gate: socket.socket | None = None
    release_duplicate = -1
    pid_cell = -1
    pid_reader = -1
    pid_creator = -1
    cgroup_grant = -1
    probe_pidfd = -1
    nonce = os.getrandom(16) if callable(getattr(os, "getrandom", None)) else os.urandom(16)
    try:
        parent_gate, child_gate = socket.socketpair(
            socket.AF_UNIX,
            socket.SOCK_SEQPACKET | getattr(socket, "SOCK_CLOEXEC", 0),
        )
        parent_gate.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        child_gate.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 0)
        parent_gate.set_inheritable(False)
        child_gate.set_inheritable(False)
        release_duplicate = fcntl.fcntl(
            parent_gate.fileno(), fcntl.F_DUPFD_CLOEXEC, 5
        )
        pid_cell = os.memfd_create(
            "acfqp-h1-nested-probe-pid-cell", MFD_CLOEXEC | MFD_ALLOW_SEALING
        )
        os.ftruncate(pid_cell, role_v1.PID_CELL_BYTES)
        pid_reader = os.open(
            f"/proc/self/fd/{pid_cell}", os.O_RDONLY | os.O_CLOEXEC
        )
        pid_creator = fcntl.fcntl(pid_cell, fcntl.F_DUPFD_CLOEXEC, 5)
        cgroup_grant = fcntl.fcntl(control_cgroup_fd, fcntl.F_DUPFD_CLOEXEC, 5)
        if os.pread(pid_reader, role_v1.PID_CELL_BYTES + 1, 0) != bytes(
            role_v1.PID_CELL_BYTES
        ):
            _fail("nested-creator PID cell was not pristine zero")
        rights = (
            cgroup_grant,
            pid_creator,
            child_gate.fileno(),
            release_duplicate,
        )
        if len(set(rights)) != 4 or any(
            fcntl.fcntl(value, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
            for value in rights
        ):
            _fail("nested-creator command rights overlap or lost CLOEXEC")
        command = NativeProtocolFrameV1(
            role_v1.OPCODES["PROBE_COMMAND"],
            1,
            nonce,
            session.supervisor_pid,
        )
        _send_frame(session.control_fd, command, rights)
        with _SESSION_LOCK:
            record.probe_command_issued = True
        for descriptor in (cgroup_grant, pid_creator, release_duplicate):
            os.close(descriptor)
        cgroup_grant = pid_creator = release_duplicate = -1
        child_gate.close()
        child_gate = None
        if _TEST_FAULT_PHASE == "BEFORE_PARENT_RETURN":
            fault_deadline = time.monotonic() + PROTOCOL_TIMEOUT_SECONDS
            while len(_stable_control_cgroup_members(control_cgroup_fd)) < 2:
                if time.monotonic() >= fault_deadline:
                    _fail("nested-creator pre-return fault probe did not appear")
                time.sleep(0.005)
            _test_fault("BEFORE_PARENT_RETURN")

        parent_return, installed = _recv_frame(
            session.control_fd,
            expected_credentials=(
                session.supervisor_pid,
                session.guardian_uid,
                session.guardian_gid,
            ),
            expected_rights=1,
            observation_sink=observation_sink,
        )
        probe_pidfd = installed[0]
        if (
            parent_return.opcode != role_v1.OPCODES["PROBE_PARENT_RETURN"]
            or parent_return.sequence != 1
            or parent_return.nonce != nonce
            or parent_return.pid <= 0
            or parent_return.status != 0
            or parent_return.flags != 0x1F
            or parent_return.fact_a != session.supervisor_pid
        ):
            _fail("nested-creator parent-return frame changed")
        probe_pid = parent_return.pid
        trusted_probe_start_ticks = _read_start_ticks(probe_pid)
        with _SESSION_LOCK:
            record.active_probe_pid = probe_pid
            record.active_probe_start_ticks = trusted_probe_start_ticks
        session.active_probe_pid = probe_pid
        _test_fault("PROBE_PARENT_RETURN")
        child_withdrawn, rights = _recv_frame(
            parent_gate.fileno(),
            expected_credentials=(probe_pid, session.guardian_uid, session.guardian_gid),
            expected_rights=0,
            observation_sink=observation_sink,
        )
        child_ready, rights_two = _recv_frame(
            parent_gate.fileno(),
            expected_credentials=(probe_pid, session.guardian_uid, session.guardian_gid),
            expected_rights=0,
            observation_sink=observation_sink,
        )
        if (
            rights
            or rights_two
            or child_withdrawn
            != NativeProtocolFrameV1(
                role_v1.OPCODES["CHILD_CELL_WITHDRAWN"], 1, nonce, probe_pid
            )
            or child_ready
            != NativeProtocolFrameV1(
                role_v1.OPCODES["CHILD_GATE_READY"], 1, nonce, probe_pid
            )
        ):
            _fail("nested-creator child pre-release frames changed")
        fcntl.fcntl(pid_cell, F_ADD_SEALS, REQUIRED_SEALS)
        if fcntl.fcntl(pid_cell, F_GET_SEALS) != REQUIRED_SEALS:
            _fail("nested-creator PID cell final seal set changed")
        raw_pid = os.pread(pid_reader, role_v1.PID_CELL_BYTES + 1, 0)
        if (
            len(raw_pid) != role_v1.PID_CELL_BYTES
            or any(raw_pid[4:])
            or int.from_bytes(raw_pid[:4], "little", signed=True) != probe_pid
        ):
            _fail("nested-creator sealed PID cell value changed")
        pidfd_fact = _pidfd_fact(probe_pidfd)
        probe_start_ticks = _read_start_ticks(probe_pid)
        if probe_start_ticks != trusted_probe_start_ticks:
            _fail("nested-creator probe start identity changed")
        if pidfd_fact["pid"] != probe_pid:
            _fail("nested-creator probe pidfd identity changed")
        _require_live_pidfd(probe_pidfd)
        live_one = _cgroup_snapshot(
            control_cgroup_fd,
            expected_pids=(session.supervisor_pid, probe_pid),
            sequence=1,
        )
        live_two = _cgroup_snapshot(
            control_cgroup_fd,
            expected_pids=(session.supervisor_pid, probe_pid),
            sequence=2,
        )
        ack = NativeProtocolFrameV1(
            role_v1.OPCODES["PROBE_ACK"], 1, nonce, probe_pid
        )
        _send_frame(session.control_fd, ack)
        release_echo, echo_rights = _recv_frame(
            parent_gate.fileno(),
            expected_credentials=(probe_pid, session.guardian_uid, session.guardian_gid),
            expected_rights=0,
            observation_sink=observation_sink,
        )
        if echo_rights or release_echo != NativeProtocolFrameV1(
            role_v1.OPCODES["CHILD_RELEASE_ECHO"], 1, nonce, probe_pid
        ):
            _fail("nested-creator child release echo changed")
        _require_dead_pidfd(probe_pidfd)
        creator_reap, reap_rights = _recv_frame(
            session.control_fd,
            expected_credentials=(
                session.supervisor_pid,
                session.guardian_uid,
                session.guardian_gid,
            ),
            expected_rights=0,
            observation_sink=observation_sink,
        )
        if (
            reap_rights
            or creator_reap
            != NativeProtocolFrameV1(
                role_v1.OPCODES["PROBE_REAP"],
                1,
                nonce,
                probe_pid,
                status=0,
                flags=1,
                fact_a=errno.ECHILD,
            )
        ):
            _fail("nested-creator WNOWAIT/consume/ECHILD report changed")
        try:
            os.waitid(P_PIDFD, probe_pidfd, os.WEXITED | os.WNOHANG)
        except ChildProcessError:
            guardian_wait_errno = errno.ECHILD
        except OSError as error:
            if error.errno != errno.ECHILD:
                raise
            guardian_wait_errno = error.errno
        else:
            _fail("guardian unexpectedly became the nested probe reaper")
        post_one = _wait_for_snapshot(
            control_cgroup_fd,
            expected_pids=(session.supervisor_pid,),
            sequence=3,
        )
        post_two = _cgroup_snapshot(
            control_cgroup_fd,
            expected_pids=(session.supervisor_pid,),
            sequence=4,
        )
        if _read_start_ticks(session.supervisor_pid) != session.supervisor_start_ticks:
            _fail("nested-creator supervisor identity changed after probe reap")
        _require_live_pidfd(session.supervisor_pidfd)
        facts = NestedCreatorProbeRawFactsV1(
            supervisor_pid=session.supervisor_pid,
            supervisor_start_ticks=session.supervisor_start_ticks,
            probe_pid=probe_pid,
            probe_start_ticks=probe_start_ticks,
            nonce=nonce,
            parent_return_frame=parent_return,
            child_withdrawn_frame=child_withdrawn,
            child_ready_frame=child_ready,
            child_release_echo_frame=release_echo,
            creator_reap_frame=creator_reap,
            pid_cell_value=probe_pid,
            pidfd_fact=pidfd_fact,
            live_cgroup_snapshots=(live_one, live_two),
            post_reap_cgroup_snapshots=(post_one, post_two),
            guardian_waitid_errno=guardian_wait_errno,
            _issuer=_FACTS_ISSUER,
        )
        session.raw_facts = facts
        with _SESSION_LOCK:
            record.active_probe_pid = -1
            record.active_probe_start_ticks = -1
            record.state = "PROBE_REAPED_SUPERVISOR_LIVE"
        session.active_probe_pid = -1
        session.state = "PROBE_REAPED_SUPERVISOR_LIVE"
        return facts
    except BaseException:
        if record.active_probe_pid <= 0 and pid_reader >= 0:
            try:
                pending_raw = os.pread(pid_reader, role_v1.PID_CELL_BYTES, 0)
                pending_pid = int.from_bytes(
                    pending_raw[:4], "little", signed=True
                )
                if (
                    len(pending_raw) != role_v1.PID_CELL_BYTES
                    or any(pending_raw[4:])
                ):
                    pending_pid = -1
                pending_members = set(
                    _stable_control_cgroup_members(control_cgroup_fd)
                )
                pending_parent = (
                    _read_parent_pid(pending_pid) if pending_pid > 0 else -1
                )
            except (OSError, ConstructionK7H1NestedCreatorProbeNativeV1Error):
                pending_pid = -1
                pending_parent = -1
                pending_members = set()
            if (
                pending_pid > 0
                and pending_pid in pending_members
                and pending_parent == record.supervisor_pid
            ):
                with _SESSION_LOCK:
                    record.active_probe_pid = pending_pid
                    record.active_probe_start_ticks = _read_start_ticks(
                        pending_pid
                    )
                session.active_probe_pid = pending_pid
        with _SESSION_LOCK:
            record.state = "PROTOCOL_FAILURE_CLEANUP_REQUIRED"
        session.state = "PROTOCOL_FAILURE_CLEANUP_REQUIRED"
        raise
    finally:
        for descriptor in (
            probe_pidfd,
            cgroup_grant,
            pid_creator,
            pid_reader,
            pid_cell,
            release_duplicate,
        ):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if child_gate is not None:
            child_gate.close()
        if parent_gate is not None:
            parent_gate.close()


def run_nested_creator_pidfd_probe_v1(
    session: NestedCreatorProbeLiveSessionV1,
    *,
    control_cgroup_fd: int,
) -> NestedCreatorProbeRawFactsV1:
    """Run the registered V1 probe summary without issuing V2 observations."""

    return _run_nested_creator_pidfd_probe_impl_v1(
        session,
        control_cgroup_fd=control_cgroup_fd,
        observation_sink=None,
    )


def run_nested_creator_pidfd_probe_observed_v2(
    session: NestedCreatorProbeLiveSessionV1,
    *,
    control_cgroup_fd: int,
) -> NestedCreatorProbeObservedFactsV2:
    """Run the probe and retain every nested receive credential/right fact."""

    observations: list[dict[str, Any]] = []
    raw_facts = _run_nested_creator_pidfd_probe_impl_v1(
        session,
        control_cgroup_fd=control_cgroup_fd,
        observation_sink=observations,
    )
    if len(observations) != 5 or [
        observation["event_index"] for observation in observations
    ] != list(range(5)):
        _fail("nested-creator V2 receive observation inventory changed")
    facts = NestedCreatorProbeObservedFactsV2(
        raw_facts_v1=raw_facts,
        supervisor_ready_observation=session.supervisor_ready_observation,
        protocol_receive_observations=tuple(observations),
        _issuer=_FACTS_ISSUER,
    )
    session.observed_facts_v2 = facts
    return facts


def abort_nested_creator_supervisor_session_v1(
    session: NestedCreatorProbeLiveSessionV1,
    *,
    control_cgroup_fd: int,
) -> dict[str, Any]:
    """Idempotently kill/reap this raw session and close its live registry."""

    if (
        type(session) is not NestedCreatorProbeLiveSessionV1
        or session._issuer is not _SESSION_ISSUER
        or session.owner_pid != os.getpid()
        or session.owner_thread_id != threading.get_ident()
        or type(control_cgroup_fd) is not int
        or control_cgroup_fd < 0
    ):
        _fail("nested-creator abort session identity changed")
    with _SESSION_LOCK:
        registered = _LIVE_SESSIONS.record(session)
    if registered is None and session.state == "ABORTED_CLOSED":
        if session.abort_facts is None:
            _fail("nested-creator closed abort state changed")
        return _thaw_json(session.abort_facts)
    if registered is None:
        _fail("nested-creator abort session was not live")
    record = _require_terminal_session_identity(
        session,
        allowed_states={
            "SUPERVISOR_READY",
            "PROBE_REAPED_SUPERVISOR_LIVE",
            "PROTOCOL_FAILURE_CLEANUP_REQUIRED",
            "SUPERVISOR_RELEASED_TO_EXIT",
            "ABORT_CONTROL_CLOSED_CLEANUP_REQUIRED",
        },
        require_control=registered.control_open,
    )

    cgroup_status = os.fstat(control_cgroup_fd)
    if record.control_cgroup_device is not None and (
        cgroup_status.st_dev != record.control_cgroup_device
        or cgroup_status.st_ino != record.control_cgroup_inode
    ):
        _fail("nested-creator abort control cgroup lease changed")
    cgroup_members = _stable_control_cgroup_members(control_cgroup_fd)
    member_set = set(cgroup_members)
    if (
        record.control_cgroup_device is None
        and record.supervisor_pid not in member_set
    ):
        _fail("nested-creator abort control cgroup lacked the supervisor")
    if record.control_cgroup_device is None:
        record.control_cgroup_device = cgroup_status.st_dev
        record.control_cgroup_inode = cgroup_status.st_ino
    unknown_members = member_set - {record.supervisor_pid}
    if record.active_probe_pid > 0:
        active_exists = Path(f"/proc/{record.active_probe_pid}").exists()
        if unknown_members - {record.active_probe_pid} or (
            active_exists
            and (
                record.active_probe_pid not in member_set
                or _read_start_ticks(record.active_probe_pid)
                != record.active_probe_start_ticks
            )
        ):
            _fail("nested-creator abort cgroup contains an unregistered process")
    elif unknown_members:
        _fail("nested-creator abort cgroup contains an unknown process")

    children_before = _direct_child_pids()
    trusted_children = {record.supervisor_pid}
    if record.active_probe_pid > 0:
        trusted_children.add(record.active_probe_pid)
    if any(child not in trusted_children for child in children_before):
        _fail("nested-creator abort found an unrelated direct child")
    if record.supervisor_pid not in children_before and record.state not in {
        "SUPERVISOR_RELEASED_TO_EXIT",
        "PROTOCOL_FAILURE_CLEANUP_REQUIRED",
        "ABORT_CONTROL_CLOSED_CLEANUP_REQUIRED",
    }:
        _fail("nested-creator abort lost the direct supervisor")
    if record.control_open:
        pending: BaseException | None = None
        previous_signals = _block_terminal_signals()
        try:
            record.state = "ABORT_CONTROL_CLOSED_CLEANUP_REQUIRED"
            session.state = record.state
            _close_finish_forward(record.control_fd)
            record.control_open = False
            session.control_fd = -1
            try:
                _test_fault("AFTER_INNER_CONTROL_CLOSE")
            except BaseException as error:
                pending = error
        finally:
            _restore_terminal_signals(previous_signals)
        if pending is not None:
            raise pending
    _write_control(control_cgroup_fd, "cgroup.kill", b"1\n")
    reaped = _drain_exact_owned_children_after_kill(
        tuple(sorted(trusted_children))
    )
    empty_one = _wait_for_snapshot(
        control_cgroup_fd, expected_pids=(), sequence=9001
    )
    empty_two = _cgroup_snapshot(
        control_cgroup_fd, expected_pids=(), sequence=9002
    )
    facts: dict[str, Any] = {
        "state": "ABORTED_CLOSED",
        "supervisor_pid": record.supervisor_pid,
        "active_probe_pid": record.active_probe_pid,
        "children_before": list(children_before),
        "reaped": [dict(fact) for fact in reaped],
        "empty_snapshots": [dict(empty_one), dict(empty_two)],
    }
    pending = None
    previous_signals = _block_terminal_signals()
    try:
        record.abort_facts = _freeze_json(facts)
        session.abort_facts = record.abort_facts
        record.active_probe_pid = -1
        record.active_probe_start_ticks = -1
        session.active_probe_pid = -1
        record.state = "ABORTED_CLOSED"
        session.state = "ABORTED_CLOSED"
        if record.pidfd_open:
            _close_finish_forward(record.supervisor_pidfd)
            record.pidfd_open = False
            session.supervisor_pidfd = -1
        try:
            _test_fault("AFTER_INNER_PIDFD_CLOSE")
        except BaseException as error:
            pending = error
        with _SESSION_LOCK:
            _LIVE_SESSIONS.remove(session)
    finally:
        _restore_terminal_signals(previous_signals)
    if pending is not None:
        raise pending
    return _thaw_json(session.abort_facts)


def shutdown_nested_creator_supervisor_v1(
    session: NestedCreatorProbeLiveSessionV1,
) -> NativeProtocolFrameV1:
    """Release the raw role to exit; the real parent must consume-reap it."""

    with _SESSION_LOCK:
        registered = _LIVE_SESSIONS.record(session)
    if registered is None:
        _fail("nested-creator shutdown ownership record is unavailable")
    if (
        registered.state == "SUPERVISOR_RELEASED_TO_EXIT"
        and registered.shutdown_frame is not None
    ):
        _require_terminal_session_identity(
            session,
            allowed_states={"SUPERVISOR_RELEASED_TO_EXIT"},
            require_control=False,
        )
        session.state = registered.state
        session.control_fd = -1
        session.shutdown_frame = registered.shutdown_frame
        return registered.shutdown_frame
    record = _require_terminal_session_identity(
        session,
        allowed_states={"PROBE_REAPED_SUPERVISOR_LIVE"},
        require_control=True,
    )
    nonce = os.getrandom(16) if callable(getattr(os, "getrandom", None)) else os.urandom(16)
    shutdown = NativeProtocolFrameV1(
        role_v1.OPCODES["SUPERVISOR_SHUTDOWN"],
        2,
        nonce,
        record.supervisor_pid,
    )
    _send_frame(record.control_fd, shutdown)
    bye, rights = _recv_frame(
        record.control_fd,
        expected_credentials=(
            record.supervisor_pid,
            record.guardian_uid,
            record.guardian_gid,
        ),
        expected_rights=0,
    )
    expected = NativeProtocolFrameV1(
        role_v1.OPCODES["SUPERVISOR_BYE"], 2, nonce, record.supervisor_pid
    )
    if rights or bye != expected:
        _fail("nested-creator supervisor shutdown echo changed")
    pending: BaseException | None = None
    previous_signals = _block_terminal_signals()
    try:
        record.shutdown_frame = bye
        session.shutdown_frame = record.shutdown_frame
        record.state = "SUPERVISOR_RELEASED_TO_EXIT"
        session.state = record.state
        _close_finish_forward(record.control_fd)
        record.control_open = False
        session.control_fd = -1
        try:
            _test_fault("AFTER_INNER_CONTROL_CLOSE")
        except BaseException as error:
            pending = error
    finally:
        _restore_terminal_signals(previous_signals)
    if pending is not None:
        raise pending
    return bye


def finish_nested_creator_supervisor_reap_v1(
    session: NestedCreatorProbeLiveSessionV1,
) -> dict[str, Any]:
    """Direct guardian WNOWAIT/consume-reap for the bounded raw fixture."""

    if (
        type(session) is NestedCreatorProbeLiveSessionV1
        and session._issuer is _SESSION_ISSUER
        and session.state == "CLOSED"
        and session.finish_facts is not None
        and _LIVE_SESSIONS.get(id(session)) is not session
    ):
        return _thaw_json(session.finish_facts)
    record = _require_terminal_session_identity(
        session,
        allowed_states={"SUPERVISOR_RELEASED_TO_EXIT"},
        require_control=False,
    )
    _require_dead_pidfd(record.supervisor_pidfd)
    pending: BaseException | None = None
    previous_signals = _block_terminal_signals()
    try:
        observed = os.waitid(
            P_PIDFD, record.supervisor_pidfd, os.WEXITED | os.WNOWAIT
        )
        consumed = os.waitid(P_PIDFD, record.supervisor_pidfd, os.WEXITED)
        try:
            _test_fault("AFTER_INNER_PIDFD_CONSUME")
        except BaseException as error:
            pending = error
        fields = ("si_pid", "si_uid", "si_signo", "si_status", "si_code")
        observed_fact = {name: int(getattr(observed, name)) for name in fields}
        consumed_fact = {name: int(getattr(consumed, name)) for name in fields}
        if (
            observed_fact != consumed_fact
            or observed_fact["si_pid"] != record.supervisor_pid
            or observed_fact["si_status"] != 0
        ):
            _fail("nested-creator supervisor direct reap status changed")
        try:
            os.waitid(P_PIDFD, record.supervisor_pidfd, os.WEXITED | os.WNOHANG)
        except ChildProcessError:
            third_errno = errno.ECHILD
        except OSError as error:
            if error.errno != errno.ECHILD:
                raise
            third_errno = error.errno
        else:
            _fail("nested-creator supervisor remained waitable after consume")
        facts = {
            "observed_wnowait": observed_fact,
            "consumed": consumed_fact,
            "third_wait_errno": third_errno,
            "supervisor_reaped_exactly_once": True,
        }
        record.finish_facts = _freeze_json(facts)
        session.finish_facts = record.finish_facts
        record.state = "CLOSED"
        session.state = record.state
        _close_finish_forward(record.supervisor_pidfd)
        record.pidfd_open = False
        session.supervisor_pidfd = -1
        try:
            _test_fault("AFTER_INNER_PIDFD_CLOSE")
        except BaseException as error:
            pending = error
        with _SESSION_LOCK:
            _LIVE_SESSIONS.remove(session)
    finally:
        _restore_terminal_signals(previous_signals)
    if pending is not None:
        raise pending
    return _thaw_json(session.finish_facts)


def _live_sessions_atfork_before_v1() -> None:
    _SESSION_LOCK.acquire()


def _live_sessions_atfork_after_parent_v1() -> None:
    _SESSION_LOCK.release()


def _poison_live_sessions_after_fork_child_v1() -> None:
    """Drop inherited capabilities; ownership and cleanup remain in the parent."""

    try:
        records = _LIVE_SESSIONS.records()
        descriptors = {
            descriptor
            for record in records
            for descriptor in (
                record.control_fd if record.control_open else -1,
                record.supervisor_pidfd if record.pidfd_open else -1,
            )
            if type(descriptor) is int and descriptor >= 0
        }
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass
        for record in records:
            record.session.control_fd = -1
            record.session.supervisor_pidfd = -1
            record.session.state = "FORK_CHILD_POISONED"
        _LIVE_SESSIONS.clear()
    finally:
        _SESSION_LOCK.release()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(
        before=_live_sessions_atfork_before_v1,
        after_in_parent=_live_sessions_atfork_after_parent_v1,
        after_in_child=_poison_live_sessions_after_fork_child_v1,
    )


__all__ = (
    "ConstructionK7H1NestedCreatorProbeNativeV1Error",
    "NestedCreatorProbeLiveSessionV1",
    "NestedCreatorProbeObservedFactsV2",
    "NestedCreatorProbeRawFactsV1",
    "NativeProtocolFrameV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS",
    "SCHEMA_VERSION",
    "abort_nested_creator_supervisor_session_v1",
    "begin_nested_creator_supervisor_session_v1",
    "finish_nested_creator_supervisor_reap_v1",
    "observe_nested_creator_control_population_v1",
    "run_nested_creator_pidfd_probe_v1",
    "run_nested_creator_pidfd_probe_observed_v2",
    "shutdown_nested_creator_supervisor_v1",
    "verify_nested_creator_live_session_v1",
)
