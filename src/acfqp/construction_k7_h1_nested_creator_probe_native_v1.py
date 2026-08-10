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
import mmap
import os
from pathlib import Path
import select
import socket
import struct
import threading
import time
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
_LIVE_SESSIONS: dict[int, "NestedCreatorProbeLiveSessionV1"] = {}
_SESSION_LOCK = threading.RLock()


class ConstructionK7H1NestedCreatorProbeNativeV1Error(RuntimeError):
    """The exact nested-creator protocol or cleanup failed closed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1NestedCreatorProbeNativeV1Error(message)


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
            "pidfd_fact": dict(self.pidfd_fact),
            "live_cgroup_snapshots": [
                dict(snapshot) for snapshot in self.live_cgroup_snapshots
            ],
            "post_reap_cgroup_snapshots": [
                dict(snapshot) for snapshot in self.post_reap_cgroup_snapshots
            ],
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
    raw_facts: NestedCreatorProbeRawFactsV1 | None = field(default=None, repr=False)
    _issuer: object = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _SESSION_ISSUER:
            _fail("nested-creator live session is caller-minted")

    def __copy__(self) -> NoReturn:
        _fail("nested-creator live session cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("nested-creator live session cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("nested-creator live session cannot be copied or pickled")


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
        return NativeProtocolFrameV1.from_bytes(raw), rights
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


def _read_control(directory_fd: int, name: str, cap: int = 65536) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        raw = os.read(descriptor, cap + 1)
    finally:
        os.close(descriptor)
    if not raw or len(raw) > cap:
        _fail(f"nested-creator {name} exceeded its exact bound")
    return raw


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
    first = _parse_pid_lines(_read_control(directory_fd, "cgroup.procs"))
    events = _parse_events(_read_control(directory_fd, "cgroup.events"))
    current = _parse_single(_read_control(directory_fd, "pids.current"), "pids.current")
    second = _parse_pid_lines(_read_control(directory_fd, "cgroup.procs"))
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
    _set_passcred(control_fd, True)
    expected_credentials = (supervisor_pid, os.getuid(), os.getgid())
    frame, rights = _recv_frame(
        control_fd,
        expected_credentials=expected_credentials,
        expected_rights=0,
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
        _issuer=_SESSION_ISSUER,
    )
    with _SESSION_LOCK:
        if id(session) in _LIVE_SESSIONS:
            _fail("nested-creator live session identity was reused")
        _LIVE_SESSIONS[id(session)] = session
    return session


def _require_session(
    session: NestedCreatorProbeLiveSessionV1, *, allowed_states: set[str]
) -> None:
    if (
        type(session) is not NestedCreatorProbeLiveSessionV1
        or session._issuer is not _SESSION_ISSUER
        or session.owner_pid != os.getpid()
        or session.owner_thread_id != threading.get_ident()
        or session.state not in allowed_states
        or _LIVE_SESSIONS.get(id(session)) is not session
        or _pidfd_fact(session.supervisor_pidfd)["pid"] != session.supervisor_pid
        or _read_start_ticks(session.supervisor_pid) != session.supervisor_start_ticks
    ):
        _fail("nested-creator live session identity or state changed")
    _require_live_pidfd(session.supervisor_pidfd)


def run_nested_creator_pidfd_probe_v1(
    session: NestedCreatorProbeLiveSessionV1,
    *,
    control_cgroup_fd: int,
) -> NestedCreatorProbeRawFactsV1:
    """Run one real nested probe and leave the exact supervisor live."""

    _require_session(session, allowed_states={"SUPERVISOR_READY"})
    if type(control_cgroup_fd) is not int or control_cgroup_fd < 0:
        _fail("nested-creator CONTROL cgroup descriptor is invalid")
    before = _cgroup_snapshot(
        control_cgroup_fd,
        expected_pids=(session.supervisor_pid,),
        sequence=0,
    )
    del before
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
        for descriptor in (cgroup_grant, pid_creator, release_duplicate):
            os.close(descriptor)
        cgroup_grant = pid_creator = release_duplicate = -1
        child_gate.close()
        child_gate = None

        parent_return, installed = _recv_frame(
            session.control_fd,
            expected_credentials=(
                session.supervisor_pid,
                session.guardian_uid,
                session.guardian_gid,
            ),
            expected_rights=1,
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
        child_withdrawn, rights = _recv_frame(
            parent_gate.fileno(),
            expected_credentials=(probe_pid, session.guardian_uid, session.guardian_gid),
            expected_rights=0,
        )
        child_ready, rights_two = _recv_frame(
            parent_gate.fileno(),
            expected_credentials=(probe_pid, session.guardian_uid, session.guardian_gid),
            expected_rights=0,
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
        session.state = "PROBE_REAPED_SUPERVISOR_LIVE"
        return facts
    except BaseException:
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


def shutdown_nested_creator_supervisor_v1(
    session: NestedCreatorProbeLiveSessionV1,
) -> NativeProtocolFrameV1:
    """Release the raw role to exit; the real parent must consume-reap it."""

    _require_session(
        session, allowed_states={"PROBE_REAPED_SUPERVISOR_LIVE"}
    )
    nonce = os.getrandom(16) if callable(getattr(os, "getrandom", None)) else os.urandom(16)
    shutdown = NativeProtocolFrameV1(
        role_v1.OPCODES["SUPERVISOR_SHUTDOWN"],
        2,
        nonce,
        session.supervisor_pid,
    )
    _send_frame(session.control_fd, shutdown)
    bye, rights = _recv_frame(
        session.control_fd,
        expected_credentials=(
            session.supervisor_pid,
            session.guardian_uid,
            session.guardian_gid,
        ),
        expected_rights=0,
    )
    expected = NativeProtocolFrameV1(
        role_v1.OPCODES["SUPERVISOR_BYE"], 2, nonce, session.supervisor_pid
    )
    if rights or bye != expected:
        _fail("nested-creator supervisor shutdown echo changed")
    os.close(session.control_fd)
    session.control_fd = -1
    session.state = "SUPERVISOR_RELEASED_TO_EXIT"
    return bye


def finish_nested_creator_supervisor_reap_v1(
    session: NestedCreatorProbeLiveSessionV1,
) -> dict[str, Any]:
    """Direct guardian WNOWAIT/consume-reap for the bounded raw fixture."""

    if (
        type(session) is not NestedCreatorProbeLiveSessionV1
        or session._issuer is not _SESSION_ISSUER
        or session.owner_pid != os.getpid()
        or session.owner_thread_id != threading.get_ident()
        or session.state != "SUPERVISOR_RELEASED_TO_EXIT"
        or _LIVE_SESSIONS.get(id(session)) is not session
    ):
        _fail("nested-creator supervisor reap session changed")
    _require_dead_pidfd(session.supervisor_pidfd)
    observed = os.waitid(P_PIDFD, session.supervisor_pidfd, os.WEXITED | os.WNOWAIT)
    consumed = os.waitid(P_PIDFD, session.supervisor_pidfd, os.WEXITED)
    fields = ("si_pid", "si_uid", "si_signo", "si_status", "si_code")
    observed_fact = {name: int(getattr(observed, name)) for name in fields}
    consumed_fact = {name: int(getattr(consumed, name)) for name in fields}
    if (
        observed_fact != consumed_fact
        or observed_fact["si_pid"] != session.supervisor_pid
        or observed_fact["si_status"] != 0
    ):
        _fail("nested-creator supervisor direct reap status changed")
    try:
        os.waitid(P_PIDFD, session.supervisor_pidfd, os.WEXITED | os.WNOHANG)
    except ChildProcessError:
        third_errno = errno.ECHILD
    except OSError as error:
        if error.errno != errno.ECHILD:
            raise
        third_errno = error.errno
    else:
        _fail("nested-creator supervisor remained waitable after consume")
    os.close(session.supervisor_pidfd)
    session.supervisor_pidfd = -1
    session.state = "CLOSED"
    _LIVE_SESSIONS.pop(id(session), None)
    return {
        "observed_wnowait": observed_fact,
        "consumed": consumed_fact,
        "third_wait_errno": third_errno,
        "supervisor_reaped_exactly_once": True,
    }


__all__ = (
    "ConstructionK7H1NestedCreatorProbeNativeV1Error",
    "NestedCreatorProbeLiveSessionV1",
    "NestedCreatorProbeRawFactsV1",
    "NativeProtocolFrameV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS",
    "SCHEMA_VERSION",
    "begin_nested_creator_supervisor_session_v1",
    "finish_nested_creator_supervisor_reap_v1",
    "run_nested_creator_pidfd_probe_v1",
    "shutdown_nested_creator_supervisor_v1",
)
