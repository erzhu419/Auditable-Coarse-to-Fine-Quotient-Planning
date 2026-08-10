"""Real gated SUPERVISOR -> PIDFD_PROBE bounded runtime.

This construction runtime composes the clone3/release/execveat native edge
with the source-closed supervisor role and its real nested-creator probe
protocol.  It observes the target SUPERVISOR -> PIDFD_PROBE creator chain in a
caller-provided CONTROL cgroup and closes both parent/reap chains.  It emits
only issuer-local raw facts: without the E5A/B2-A/B2-B exclusive lease and a
durable artifact graph, exact/exclusive two-birth authority remains absent.
"""

from __future__ import annotations

from array import array
import ctypes
from dataclasses import dataclass, field
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

from acfqp import construction_k7_h1_nested_creator_probe_native_v1 as probe_v1
from acfqp import construction_k7_h1_nested_creator_supervisor_exec_birth_native_v1 as exec_v1
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v1 as role_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-B2-D-RUNTIME"
PROFILE_KEY = "construction_k7_h1_nested_creator_two_birth_runtime_v1"
READINESS = "ACTUAL_TWO_BIRTH_RAW_RUNTIME_ONLY"

ACTUAL_GATED_SUPERVISOR_EXEC_BIRTH_IMPLEMENTATION_PRESENT = True
ACTUAL_NESTED_PIDFD_PROBE_BIRTH_IMPLEMENTATION_PRESENT = True
TARGET_TWO_BIRTH_CREATOR_CHAIN_IMPLEMENTATION_PRESENT = True
EXACT_TWO_BIRTH_OS_TOPOLOGY_OBSERVED = False
EXACT_CREATOR_REAP_OWNERSHIP_OBSERVED = True

E5A_RUNTIME_LEASE_JOIN_PRESENT = False
DURABLE_TWO_BIRTH_ARTIFACT_GRAPH_PRESENT = False
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
P_ALL = getattr(os, "P_ALL", 0)
PID_CELL_BYTES = role_v1.PID_CELL_BYTES
MAX_GATE_FRAME_BYTES = 64
PROTOCOL_TIMEOUT_SECONDS = 10.0
PR_SET_CHILD_SUBREAPER = 36
PR_GET_CHILD_SUBREAPER = 37

_RESULT_ISSUER = object()
_RUNTIME_LOCK = threading.RLock()
_LIBC = ctypes.CDLL(None, use_errno=True)
_TEST_FAULT_PHASE: str | None = None


class ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error(RuntimeError):
    """The exact raw two-birth topology or bounded cleanup failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error(message)


def _test_fault(phase: str) -> None:
    global _TEST_FAULT_PHASE
    if _TEST_FAULT_PHASE == phase:
        _TEST_FAULT_PHASE = None
        _fail(f"injected two-birth runtime fault after {phase}")


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
class BoundedNestedCreatorTwoBirthRawResultV1:
    supervisor_pid: int
    supervisor_start_ticks: int
    probe_pid: int
    probe_start_ticks: int
    outer_pid_cell_value: int
    outer_parent_edge: Mapping[str, int]
    outer_nonce: bytes = field(repr=False)
    outer_gate_facts: tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]
    outer_pidfd_fact: Mapping[str, int]
    outer_seal_set: int
    outer_role_source_fact: Mapping[str, Any]
    outer_live_snapshots: tuple[Mapping[str, Any], Mapping[str, Any]]
    probe_facts: probe_v1.NestedCreatorProbeRawFactsV1 = field(repr=False)
    supervisor_reap: Mapping[str, Any]
    final_empty_snapshots: tuple[Mapping[str, Any], Mapping[str, Any]]
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer is not _RESULT_ISSUER:
            _fail("two-birth raw result is caller-minted")
        if type(self.outer_nonce) is not bytes or len(self.outer_nonce) != 16:
            _fail("two-birth raw result outer nonce changed")
        for name in (
            "outer_parent_edge",
            "outer_gate_facts",
            "outer_pidfd_fact",
            "outer_role_source_fact",
            "outer_live_snapshots",
            "supervisor_reap",
            "final_empty_snapshots",
        ):
            object.__setattr__(self, name, _freeze_json(getattr(self, name)))

    def __copy__(self) -> NoReturn:
        _fail("two-birth raw result cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("two-birth raw result cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("two-birth raw result cannot be copied or pickled")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_nested_creator_two_birth_raw_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "supervisor_pid": self.supervisor_pid,
            "supervisor_start_ticks": self.supervisor_start_ticks,
            "probe_pid": self.probe_pid,
            "probe_start_ticks": self.probe_start_ticks,
            "outer_pid_cell_value": self.outer_pid_cell_value,
            "outer_parent_edge": _thaw_json(self.outer_parent_edge),
            "outer_nonce_hex": self.outer_nonce.hex(),
            "outer_gate_facts": _thaw_json(self.outer_gate_facts),
            "outer_pidfd_fact": _thaw_json(self.outer_pidfd_fact),
            "outer_seal_set": self.outer_seal_set,
            "outer_role_source_fact": _thaw_json(self.outer_role_source_fact),
            "outer_live_snapshots": _thaw_json(self.outer_live_snapshots),
            "probe_facts": self.probe_facts.to_document(),
            "supervisor_reap": _thaw_json(self.supervisor_reap),
            "final_empty_snapshots": _thaw_json(self.final_empty_snapshots),
            "birth_order": ["SUPERVISOR", "PIDFD_PROBE"],
            "creator_by_slot": {
                "SUPERVISOR": "EXTERNAL_GUARDIAN",
                "PIDFD_PROBE": "SUPERVISOR",
            },
            "maximum_observed_control_population": 2,
            "actual_gated_supervisor_exec_birth_present": True,
            "actual_nested_pidfd_probe_birth_present": True,
            "target_two_birth_creator_chain_observed": True,
            "exact_two_birth_os_topology_observed": False,
            "exclusive_two_birth_topology_authority_present": False,
            "exact_creator_reap_ownership_observed": True,
            "memory_peak_read_count": 0,
            "e5a_runtime_lease_join_present": False,
            "durable_two_birth_artifact_graph_present": False,
            "two_birth_prefix_authority_present": False,
            "five_birth_process_authority_present": False,
            "actual_observed_e3_v2_completion_present": False,
            "e4_v2_completion_present": False,
            "production_shared_resource_receipts_present": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "formal_actual_projection_proof_issued": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        }


def _fd_at_least(descriptor: int, minimum: int) -> int:
    if descriptor >= minimum:
        return descriptor
    replacement = fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, minimum)
    os.close(descriptor)
    return int(replacement)


def _read_start_ticks(pid: int) -> int:
    try:
        raw = Path(f"/proc/{pid}/stat").read_bytes()
    except OSError as error:
        raise ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error(
            "two-birth process stat is unavailable"
        ) from error
    close = raw.rfind(b")")
    fields = raw[close + 2 :].split() if close >= 0 else []
    if len(fields) < 20 or not fields[19].isdigit():
        _fail("two-birth process start ticks are malformed")
    return int(fields[19])


def _pidfd_fact(descriptor: int) -> dict[str, int]:
    try:
        raw = Path(f"/proc/self/fdinfo/{descriptor}").read_text(encoding="ascii")
    except OSError as error:
        raise ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error(
            "two-birth pidfd fdinfo is unavailable"
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
        _fail("two-birth pidfd does not identify one live PID")
    status = os.fstat(descriptor)
    return {
        "pid": values["pid"],
        "nspid": values.get("nspid", values["pid"]),
        "device": status.st_dev,
        "inode": status.st_ino,
    }


def _single_thread_guardian() -> None:
    task_ids = sorted(
        int(name) for name in os.listdir("/proc/self/task") if name.isdigit()
    )
    if task_ids != [threading.get_native_id()] or threading.active_count() != 1:
        _fail("two-birth raw runtime requires one exact guardian thread")
    if signal.getsignal(signal.SIGCHLD) is not signal.SIG_DFL:
        _fail("two-birth raw runtime requires default SIGCHLD")
    children = Path(
        f"/proc/self/task/{threading.get_native_id()}/children"
    ).read_text(encoding="ascii").strip()
    if children:
        _fail("two-birth raw runtime requires no pre-existing child")
    for descriptor in (0, 1, 2):
        try:
            os.fstat(descriptor)
        except OSError as error:
            raise ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error(
                "two-birth raw runtime requires standard descriptors"
            ) from error


def _new_seqpacket_pair() -> tuple[int, int]:
    first, second = socket.socketpair(
        socket.AF_UNIX,
        socket.SOCK_SEQPACKET | getattr(socket, "SOCK_CLOEXEC", 0),
    )
    try:
        first.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        second.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 0)
        first.set_inheritable(False)
        second.set_inheritable(False)
        return first.detach(), second.detach()
    except BaseException:
        first.close()
        second.close()
        raise


def _recv_exact_gate_frame(
    descriptor: int,
    *,
    expected: bytes,
    expected_pid: int,
) -> dict[str, Any]:
    poller = select.poll()
    poller.register(descriptor, select.POLLIN)
    events = poller.poll(int(PROTOCOL_TIMEOUT_SECONDS * 1000))
    if not events or events[0][0] != descriptor or events[0][1] & select.POLLIN == 0:
        _fail("two-birth gate frame did not become readable")
    wrapper = socket.socket(fileno=descriptor)
    rights: list[int] = []
    try:
        data, ancillary, flags, address = wrapper.recvmsg(
            len(expected) + 1,
            socket.CMSG_SPACE(struct.calcsize("=i"))
            + socket.CMSG_SPACE(struct.calcsize("=iii")),
            getattr(socket, "MSG_CMSG_CLOEXEC", 0),
        )
        credentials: list[tuple[int, int, int]] = []
        unknown = False
        for level, kind, raw in ancillary:
            if level != socket.SOL_SOCKET:
                unknown = True
            elif kind == socket.SCM_CREDENTIALS and len(raw) == struct.calcsize(
                "=iii"
            ):
                credentials.append(struct.unpack("=iii", raw))
            elif kind == socket.SCM_RIGHTS and raw:
                installed = array("i")
                installed.frombytes(raw)
                rights.extend(int(value) for value in installed)
            else:
                unknown = True
        allowed = getattr(socket, "MSG_EOR", 0) | getattr(
            socket, "MSG_CMSG_CLOEXEC", 0
        )
        if (
            data != expected
            or address is not None
            or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
            or flags & ~allowed
            or unknown
            or credentials != [(expected_pid, os.getuid(), os.getgid())]
            or rights
            or len(ancillary) != 1
        ):
            _fail("two-birth gate payload, credentials, or ancillary changed")
        return {
            "sha256": hashlib.sha256(data).hexdigest(),
            "byte_count": len(data),
            "credential_pid": credentials[0][0],
            "credential_uid": credentials[0][1],
            "credential_gid": credentials[0][2],
            "message_flags": flags,
        }
    finally:
        for right in rights:
            try:
                os.close(right)
            except OSError:
                pass
        wrapper.detach()


def _send_exact_gate_frame(descriptor: int, raw: bytes) -> None:
    wrapper = socket.socket(fileno=descriptor)
    try:
        sent = wrapper.sendmsg([raw], [], getattr(socket, "MSG_NOSIGNAL", 0))
        if sent != len(raw):
            _fail("two-birth gate release was short")
    finally:
        wrapper.detach()


def _map_pid_cell(descriptor: int, *, writable: bool) -> int:
    _LIBC.mmap.argtypes = (
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_long,
    )
    _LIBC.mmap.restype = ctypes.c_void_p
    protection = mmap.PROT_READ | (mmap.PROT_WRITE if writable else 0)
    mapped = _LIBC.mmap(
        None, PID_CELL_BYTES, protection, mmap.MAP_SHARED, descriptor, 0
    )
    address = int(mapped) if mapped is not None else 0
    if address in {0, ctypes.c_void_p(-1).value}:
        _fail("two-birth PID-cell mapping failed")
    return address


def _same_inode(first: int, second: int) -> bool:
    left = os.fstat(first)
    right = os.fstat(second)
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _set_subreaper(enabled: bool) -> None:
    if _LIBC.prctl(PR_SET_CHILD_SUBREAPER, int(enabled), 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error(
            f"two-birth subreaper transition failed with errno {error}"
        )


def _get_subreaper() -> bool:
    value = ctypes.c_int(-1)
    if _LIBC.prctl(PR_GET_CHILD_SUBREAPER, ctypes.byref(value), 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error(
            f"two-birth subreaper read failed with errno {error}"
        )
    if value.value not in {0, 1}:
        _fail("two-birth subreaper state changed")
    return bool(value.value)


def _wait_empty(control_cgroup_fd: int, sequence: int) -> dict[str, Any]:
    deadline = time.monotonic() + PROTOCOL_TIMEOUT_SECONDS
    while True:
        try:
            return probe_v1.observe_nested_creator_control_population_v1(
                control_cgroup_fd, expected_pids=(), sequence=sequence
            )
        except probe_v1.ConstructionK7H1NestedCreatorProbeNativeV1Error:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.005)


def _write_control(directory_fd: int, name: str, raw: bytes) -> None:
    descriptor = os.open(name, os.O_WRONLY | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                _fail(f"two-birth {name} write was short")
            offset += written
    finally:
        os.close(descriptor)


def _abort_control_population(control_cgroup_fd: int) -> dict[str, Any]:
    """Kill the isolated CONTROL population and consume all owned children."""

    _write_control(control_cgroup_fd, "cgroup.kill", b"1\n")
    deadline = time.monotonic() + PROTOCOL_TIMEOUT_SECONDS
    reaped: list[dict[str, int]] = []
    while True:
        try:
            result = os.waitid(P_ALL, 0, os.WEXITED | os.WNOHANG)
        except ChildProcessError:
            break
        except OSError as error:
            if error.errno == errno.ECHILD:
                break
            raise
        if result is None:
            if time.monotonic() >= deadline:
                _fail("two-birth aborted children did not become waitable")
            time.sleep(0.005)
            continue
        reaped.append(
            {
                name: int(getattr(result, name))
                for name in ("si_pid", "si_uid", "si_signo", "si_status", "si_code")
            }
        )
    children = Path(
        f"/proc/self/task/{threading.get_native_id()}/children"
    ).read_text(encoding="ascii").strip()
    if children:
        _fail("two-birth abort left an owned child")
    empty_one = _wait_empty(control_cgroup_fd, 9901)
    empty_two = probe_v1.observe_nested_creator_control_population_v1(
        control_cgroup_fd, expected_pids=(), sequence=9902
    )
    return {
        "reaped": reaped,
        "empty_snapshots": [dict(empty_one), dict(empty_two)],
    }


def run_bounded_nested_creator_two_birth_runtime_v1(
    *,
    control_cgroup_fd: int,
) -> BoundedNestedCreatorTwoBirthRawResultV1:
    """Observe SUPERVISOR then PIDFD_PROBE and close both target births."""

    exec_v1.verify_nested_creator_supervisor_exec_birth_native_image_v1()
    role_v1.verify_nested_creator_supervisor_native_image_v1()
    if type(control_cgroup_fd) is not int or control_cgroup_fd < 0:
        _fail("two-birth CONTROL cgroup descriptor is invalid")
    status = os.fstat(control_cgroup_fd)
    if not stat.S_ISDIR(status.st_mode):
        _fail("two-birth CONTROL cgroup descriptor is not a directory")
    _single_thread_guardian()

    parent_gate_fd = child_gate_fd = -1
    pid_cell_fd = pid_reader_fd = pid_creator_fd = -1
    creator_cgroup_fd = -1
    role_fd = role_witness_fd = child_role_fd = -1
    creator_mapping = guardian_mapping = 0
    supervisor_pidfd = -1
    supervisor_pid = -1
    live_session: probe_v1.NestedCreatorProbeLiveSessionV1 | None = None
    old_subreaper = _get_subreaper()
    original_mask: set[signal.Signals] | None = None
    try:
        with _RUNTIME_LOCK:
            if not old_subreaper:
                _set_subreaper(True)
            parent_gate_fd, child_gate_fd = _new_seqpacket_pair()
            child_gate_fd = _fd_at_least(
                child_gate_fd, exec_v1.CHILD_GATE_SOURCE_FD_MINIMUM
            )
            pid_cell_fd = os.memfd_create(
                "acfqp-h1-two-birth-supervisor-pid-cell",
                MFD_CLOEXEC | MFD_ALLOW_SEALING,
            )
            os.ftruncate(pid_cell_fd, PID_CELL_BYTES)
            pid_reader_fd = os.open(
                f"/proc/self/fd/{pid_cell_fd}", os.O_RDONLY | os.O_CLOEXEC
            )
            pid_creator_fd = fcntl.fcntl(
                pid_cell_fd, fcntl.F_DUPFD_CLOEXEC, 5
            )
            creator_cgroup_fd = fcntl.fcntl(
                control_cgroup_fd, fcntl.F_DUPFD_CLOEXEC, 5
            )
            role_fd = role_v1.create_sealed_nested_creator_supervisor_memfd_v1()
            role_witness_fd = fcntl.fcntl(role_fd, fcntl.F_DUPFD_CLOEXEC, 5)
            child_role_fd = fcntl.fcntl(role_fd, fcntl.F_DUPFD_CLOEXEC, 5)
            child_role_fd = _fd_at_least(
                child_role_fd, exec_v1.EXECUTABLE_SOURCE_FD_MINIMUM
            )
            sensitive = {
                parent_gate_fd,
                child_gate_fd,
                pid_cell_fd,
                pid_reader_fd,
                pid_creator_fd,
                creator_cgroup_fd,
                role_fd,
                role_witness_fd,
                child_role_fd,
            }
            if len(sensitive) != 9 or min(sensitive) < 3 or any(
                fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
                for descriptor in sensitive
            ):
                _fail("two-birth launch descriptors overlap or lost CLOEXEC")
            if (
                not _same_inode(pid_cell_fd, pid_reader_fd)
                or not _same_inode(role_fd, role_witness_fd)
                or not _same_inode(role_fd, child_role_fd)
                or os.pread(pid_reader_fd, PID_CELL_BYTES + 1, 0)
                != bytes(PID_CELL_BYTES)
            ):
                _fail("two-birth PID cell or role source identity changed")
            creator_mapping = _map_pid_cell(pid_creator_fd, writable=True)
            guardian_mapping = _map_pid_cell(pid_reader_fd, writable=False)
            pidfd_cell = ctypes.c_int(-1)
            clone_args = exec_v1.CloneArgsV1(
                flags=exec_v1.REQUIRED_CLONE_FLAGS,
                pidfd=ctypes.addressof(pidfd_cell),
                parent_tid=creator_mapping,
                exit_signal=int(signal.SIGCHLD),
                cgroup=creator_cgroup_fd,
            )
            parent_edge = exec_v1.NativeParentEdgeV1(0, 0, 0, 0)
            nonce = os.getrandom(16) if callable(getattr(os, "getrandom", None)) else os.urandom(16)
            nonce_ascii = nonce.hex().encode("ascii")
            withdrawn = b"ACFQP:EXEC_CELL_WITHDRAWN:v1:" + nonce_ascii
            ready = b"ACFQP:EXEC_GATE_READY:v1:" + nonce_ascii
            release = b"ACFQP:EXEC_RELEASE:v1:" + nonce_ascii
            if any(not 0 < len(frame) <= MAX_GATE_FRAME_BYTES for frame in (withdrawn, ready, release)):
                _fail("two-birth outer gate frame exceeds the native grammar")
            withdrawn_buffer = ctypes.create_string_buffer(withdrawn, len(withdrawn))
            ready_buffer = ctypes.create_string_buffer(ready, len(ready))
            release_buffer = ctypes.create_string_buffer(release, len(release))
            argv0 = ctypes.create_string_buffer(b"acfqp-h1-supervisor-v1\x00")
            argv = (ctypes.c_char_p * 2)(ctypes.cast(argv0, ctypes.c_char_p), None)
            envp = (ctypes.c_char_p * 1)(None)
            launch_args = exec_v1.NativeExecLaunchArgsV1(
                clone_args=ctypes.addressof(clone_args),
                creator_pid_cell_mapping=creator_mapping,
                pid_cell_mapping_bytes=PID_CELL_BYTES,
                creator_pid_cell_fd=pid_creator_fd,
                one_shot_cgroup_grant_fd=creator_cgroup_fd,
                child_gate_fd=child_gate_fd,
                parent_edge=ctypes.addressof(parent_edge),
                cell_withdrawn_frame=ctypes.addressof(withdrawn_buffer),
                cell_withdrawn_frame_bytes=len(withdrawn),
                gate_ready_frame=ctypes.addressof(ready_buffer),
                gate_ready_frame_bytes=len(ready),
                release_frame=ctypes.addressof(release_buffer),
                release_frame_bytes=len(release),
                supervisor_executable_fd=child_role_fd,
                supervisor_argv=ctypes.addressof(argv),
                supervisor_envp=ctypes.addressof(envp),
            )
            all_signals = set(signal.valid_signals()) - {signal.SIGKILL, signal.SIGSTOP}
            original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, all_signals)
            try:
                native_return = int(
                    exec_v1.load_nested_creator_supervisor_exec_birth_entry_v1()(
                        ctypes.pointer(launch_args)
                    )
                )
            finally:
                try:
                    os.close(child_gate_fd)
                except OSError:
                    pass
                child_gate_fd = -1
            # Take ownership from the native edge before validating it.  A
            # wrapper-cleanup error may return a synthetic negative value even
            # though clone3 already created the child.
            if int(parent_edge.clone_result) > 0:
                supervisor_pid = int(parent_edge.clone_result)
                if int(pidfd_cell.value) >= 0:
                    supervisor_pidfd = int(pidfd_cell.value)
            _test_fault("NATIVE_RETURN_TAKEOVER")
            if parent_edge.status_bits & exec_v1.PARENT_EDGE_CREATOR_MAPPING_WITHDRAWN:
                creator_mapping = 0
            if parent_edge.status_bits & exec_v1.PARENT_EDGE_CREATOR_FD_CLOSED:
                pid_creator_fd = -1
            if parent_edge.status_bits & exec_v1.PARENT_EDGE_CGROUP_GRANT_FD_CLOSED:
                creator_cgroup_fd = -1
            if parent_edge.status_bits & exec_v1.PARENT_EDGE_EXECUTABLE_FD_CLOSED:
                child_role_fd = -1
            if native_return <= 0 or parent_edge.clone_result <= 0:
                _fail(
                    "two-birth supervisor clone3 rejected: "
                    f"return={native_return}, edge={parent_edge.clone_result}"
                )
            if (
                native_return != parent_edge.clone_result
                or parent_edge.status_bits != exec_v1.PARENT_EDGE_REQUIRED_SUCCESS_BITS
                or parent_edge.first_cleanup_error != 0
                or parent_edge.reserved_zero != 0
                or pidfd_cell.value < 0
            ):
                _fail("two-birth supervisor native parent edge changed")
            supervisor_pid = int(native_return)
            supervisor_pidfd = int(pidfd_cell.value)
            withdrawn_fact = _recv_exact_gate_frame(
                parent_gate_fd, expected=withdrawn, expected_pid=supervisor_pid
            )
            ready_fact = _recv_exact_gate_frame(
                parent_gate_fd, expected=ready, expected_pid=supervisor_pid
            )
            fcntl.fcntl(pid_cell_fd, F_ADD_SEALS, REQUIRED_SEALS)
            raw_pid = os.pread(pid_reader_fd, PID_CELL_BYTES + 1, 0)
            outer_seal_set = fcntl.fcntl(pid_cell_fd, F_GET_SEALS)
            outer_pid_value = int.from_bytes(
                raw_pid[:4], "little", signed=True
            ) if len(raw_pid) >= 4 else -1
            outer_pidfd_fact = _pidfd_fact(supervisor_pidfd)
            if (
                outer_seal_set != REQUIRED_SEALS
                or len(raw_pid) != PID_CELL_BYTES
                or any(raw_pid[4:])
                or outer_pid_value != supervisor_pid
                or ctypes.string_at(guardian_mapping, PID_CELL_BYTES) != raw_pid
                or outer_pidfd_fact["pid"] != supervisor_pid
            ):
                _fail("two-birth supervisor PID-cell/pidfd join changed")
            supervisor_start = _read_start_ticks(supervisor_pid)
            outer_live_one = probe_v1.observe_nested_creator_control_population_v1(
                control_cgroup_fd,
                expected_pids=(supervisor_pid,),
                sequence=1,
            )
            outer_live_two = probe_v1.observe_nested_creator_control_population_v1(
                control_cgroup_fd,
                expected_pids=(supervisor_pid,),
                sequence=2,
            )
            _send_exact_gate_frame(parent_gate_fd, release)
            release_fact = _recv_exact_gate_frame(
                parent_gate_fd, expected=release, expected_pid=supervisor_pid
            )
            if (
                os.pread(role_fd, role_v1.ELF_BYTE_COUNT + 1, 0)
                != role_v1.ROLE_ELF_BYTES
                or os.pread(role_witness_fd, role_v1.ELF_BYTE_COUNT + 1, 0)
                != role_v1.ROLE_ELF_BYTES
            ):
                _fail("two-birth retained supervisor role image changed")
            role_source_status = os.fstat(role_fd)
            role_witness_status = os.fstat(role_witness_fd)
            outer_role_source_fact = {
                "elf_sha256": role_v1.ELF_SHA256,
                "elf_byte_count": role_v1.ELF_BYTE_COUNT,
                "source_device": role_source_status.st_dev,
                "source_inode": role_source_status.st_ino,
                "witness_device": role_witness_status.st_dev,
                "witness_inode": role_witness_status.st_ino,
                "source_witness_same_identity": (
                    role_source_status.st_dev,
                    role_source_status.st_ino,
                )
                == (
                    role_witness_status.st_dev,
                    role_witness_status.st_ino,
                ),
            }
            live_session = probe_v1.begin_nested_creator_supervisor_session_v1(
                supervisor_pid=supervisor_pid,
                supervisor_pidfd=supervisor_pidfd,
                control_fd=parent_gate_fd,
            )
            supervisor_pidfd = -1
            parent_gate_fd = -1
            if live_session.supervisor_start_ticks != supervisor_start:
                _fail("two-birth supervisor start identity changed across exec")
            probe_facts = probe_v1.run_nested_creator_pidfd_probe_v1(
                live_session, control_cgroup_fd=control_cgroup_fd
            )
            probe_v1.shutdown_nested_creator_supervisor_v1(live_session)
            supervisor_reap = probe_v1.finish_nested_creator_supervisor_reap_v1(
                live_session
            )
            live_session = None
            supervisor_pid = -1
            final_one = _wait_empty(control_cgroup_fd, 5)
            final_two = probe_v1.observe_nested_creator_control_population_v1(
                control_cgroup_fd, expected_pids=(), sequence=6
            )
            result = BoundedNestedCreatorTwoBirthRawResultV1(
                supervisor_pid=probe_facts.supervisor_pid,
                supervisor_start_ticks=probe_facts.supervisor_start_ticks,
                probe_pid=probe_facts.probe_pid,
                probe_start_ticks=probe_facts.probe_start_ticks,
                outer_pid_cell_value=outer_pid_value,
                outer_parent_edge={
                    "clone_result": int(parent_edge.clone_result),
                    "status_bits": int(parent_edge.status_bits),
                    "first_cleanup_error": int(parent_edge.first_cleanup_error),
                    "reserved_zero": int(parent_edge.reserved_zero),
                },
                outer_nonce=nonce,
                outer_gate_facts=(
                    {"kind": "CELL_WITHDRAWN", **withdrawn_fact},
                    {"kind": "GATE_READY", **ready_fact},
                    {"kind": "RELEASE_ECHO", **release_fact},
                ),
                outer_pidfd_fact=outer_pidfd_fact,
                outer_seal_set=outer_seal_set,
                outer_role_source_fact=outer_role_source_fact,
                outer_live_snapshots=(outer_live_one, outer_live_two),
                probe_facts=probe_facts,
                supervisor_reap=supervisor_reap,
                final_empty_snapshots=(final_one, final_two),
                _issuer=_RESULT_ISSUER,
            )
            if result.to_document()["maximum_observed_control_population"] != 2:
                _fail("two-birth result population join changed")
            return result
    except BaseException:
        if live_session is not None:
            probe_v1.abort_nested_creator_supervisor_session_v1(
                live_session, control_cgroup_fd=control_cgroup_fd
            )
            live_session = None
        else:
            _abort_control_population(control_cgroup_fd)
        raise
    finally:
        if original_mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)
        if creator_mapping:
            _LIBC.munmap(ctypes.c_void_p(creator_mapping), PID_CELL_BYTES)
        if guardian_mapping:
            _LIBC.munmap(ctypes.c_void_p(guardian_mapping), PID_CELL_BYTES)
        for descriptor in (
            supervisor_pidfd,
            parent_gate_fd,
            child_gate_fd,
            pid_creator_fd,
            pid_reader_fd,
            pid_cell_fd,
            creator_cgroup_fd,
            child_role_fd,
            role_witness_fd,
            role_fd,
        ):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if not old_subreaper:
            _set_subreaper(False)


__all__ = (
    "BoundedNestedCreatorTwoBirthRawResultV1",
    "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS",
    "SCHEMA_VERSION",
    "run_bounded_nested_creator_two_birth_runtime_v1",
)
