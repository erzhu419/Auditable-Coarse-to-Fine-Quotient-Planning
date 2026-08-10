"""Real gated SUPERVISOR -> PIDFD_PROBE bounded runtime.

This construction runtime composes the clone3/release/execveat native edge
with the source-closed supervisor role and its real nested-creator probe
protocol.  It observes the target SUPERVISOR -> PIDFD_PROBE creator chain in a
caller-provided CONTROL cgroup and can stop with the SUPERVISOR live; the
historical compatibility runner closes both parent/reap chains.  It emits only
issuer-local raw facts: without the E5A/B2-A/B2-B exclusive lease and a durable
artifact graph, exact/exclusive two-birth authority remains absent.
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
import weakref

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
OWNER_BOUND_LIVE_PREFIX_IMPLEMENTATION_PRESENT = True
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
_PREFIX_ISSUER = object()
_RUNTIME_LOCK = threading.RLock()
_PREFIX_REGISTRY_LOCK = threading.RLock()
_LIVE_PREFIXES: dict[int, "_LivePrefixOwnershipV1"] = {}
_TERMINAL_PREFIXES: weakref.WeakKeyDictionary[
    "BoundedNestedCreatorTwoBirthLivePrefixV1", "_TerminalPrefixTombstoneV1"
] = weakref.WeakKeyDictionary()
_BEGIN_FAILURE_QUARANTINE: "_BeginFailureQuarantineV1 | None" = None
_LAST_BEGIN_FAILURE_RECOVERY: Any = None
_BEGIN_FORK_GUARD: Mapping[str, Any] | None = None
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


class BoundedNestedCreatorTwoBirthLivePrefixV1:
    """Unserializable owner-bound cut after creator-reaping PIDFD_PROBE.

    This is a process-local capability, not a portable artifact.  It retains
    the exact live SUPERVISOR session and an owned CONTROL cgroup descriptor so
    lifecycle handoff can be audited without first closing the topology.  The
    V1 supervisor protocol accepts only SHUTDOWN after the probe reap, so this
    handle cannot itself launch BROKER and is not a composable five-birth
    prefix.
    """

    __slots__ = (
        "__weakref__",
        "_supervisor_pid",
        "_supervisor_start_ticks",
        "_probe_pid",
        "_probe_start_ticks",
        "_outer_pid_cell_value",
        "_outer_parent_edge",
        "_outer_nonce",
        "_outer_gate_facts",
        "_outer_pidfd_fact",
        "_outer_seal_set",
        "_outer_role_source_fact",
        "_outer_entry_empty_snapshots",
        "_outer_live_snapshots",
        "_probe_facts",
        "_probe_observed_facts_v2",
        "_nested_session",
        "_control_cgroup_fd",
        "_control_cgroup_device",
        "_control_cgroup_inode",
        "_owner_pid",
        "_owner_process_start_ticks",
        "_owner_thread",
        "_owner_thread_id",
        "_owner_native_thread_id",
        "_old_subreaper",
        "_subreaper_was_promoted",
        "_state",
        "_closed_result",
        "_abort_facts",
        "_issuer",
    )

    def __init__(
        self,
        *,
        supervisor_pid: int,
        supervisor_start_ticks: int,
        probe_pid: int,
        probe_start_ticks: int,
        outer_pid_cell_value: int,
        outer_parent_edge: Mapping[str, Any],
        outer_nonce: bytes,
        outer_gate_facts: tuple[Mapping[str, Any], ...],
        outer_pidfd_fact: Mapping[str, Any],
        outer_seal_set: int,
        outer_role_source_fact: Mapping[str, Any],
        outer_entry_empty_snapshots: tuple[Mapping[str, Any], ...],
        outer_live_snapshots: tuple[Mapping[str, Any], ...],
        probe_facts: probe_v1.NestedCreatorProbeRawFactsV1,
        probe_observed_facts_v2: probe_v1.NestedCreatorProbeObservedFactsV2,
        nested_session: probe_v1.NestedCreatorProbeLiveSessionV1,
        control_cgroup_fd: int,
        old_subreaper: bool,
        issuer: object,
    ) -> None:
        if issuer is not _PREFIX_ISSUER:
            _fail("two-birth live prefix is caller-minted")
        control_status = os.fstat(control_cgroup_fd)
        self._supervisor_pid = supervisor_pid
        self._supervisor_start_ticks = supervisor_start_ticks
        self._probe_pid = probe_pid
        self._probe_start_ticks = probe_start_ticks
        self._outer_pid_cell_value = outer_pid_cell_value
        self._outer_parent_edge = _freeze_json(dict(outer_parent_edge))
        self._outer_nonce = bytes(outer_nonce)
        self._outer_gate_facts = _freeze_json(outer_gate_facts)
        self._outer_pidfd_fact = _freeze_json(dict(outer_pidfd_fact))
        self._outer_seal_set = outer_seal_set
        self._outer_role_source_fact = _freeze_json(
            dict(outer_role_source_fact)
        )
        self._outer_entry_empty_snapshots = _freeze_json(
            outer_entry_empty_snapshots
        )
        self._outer_live_snapshots = _freeze_json(outer_live_snapshots)
        self._probe_facts = probe_facts
        self._probe_observed_facts_v2 = probe_observed_facts_v2
        self._nested_session = nested_session
        self._control_cgroup_fd = control_cgroup_fd
        self._control_cgroup_device = control_status.st_dev
        self._control_cgroup_inode = control_status.st_ino
        self._owner_pid = os.getpid()
        self._owner_process_start_ticks = _read_start_ticks(os.getpid())
        self._owner_thread = threading.current_thread()
        self._owner_thread_id = threading.get_ident()
        self._owner_native_thread_id = threading.get_native_id()
        self._old_subreaper = old_subreaper
        self._subreaper_was_promoted = not old_subreaper
        self._state = "PROBE_REAPED_SUPERVISOR_LIVE"
        self._closed_result: BoundedNestedCreatorTwoBirthRawResultV1 | None = None
        self._abort_facts: Any = None
        self._issuer = issuer

    @property
    def supervisor_pid(self) -> int:
        record = _LIVE_PREFIXES.get(id(self))
        if record is not None and record.handle is self:
            return record.supervisor_pid
        tombstone = _TERMINAL_PREFIXES.get(self)
        if tombstone is not None:
            return tombstone.supervisor_pid
        return self._supervisor_pid

    @property
    def supervisor_start_ticks(self) -> int:
        record = _LIVE_PREFIXES.get(id(self))
        if record is not None and record.handle is self:
            return record.supervisor_start_ticks
        tombstone = _TERMINAL_PREFIXES.get(self)
        if tombstone is not None:
            return tombstone.supervisor_start_ticks
        return self._supervisor_start_ticks

    @property
    def probe_pid(self) -> int:
        record = _LIVE_PREFIXES.get(id(self))
        if record is not None and record.handle is self:
            return record.probe_pid
        tombstone = _TERMINAL_PREFIXES.get(self)
        if tombstone is not None:
            return tombstone.probe_pid
        return self._probe_pid

    @property
    def probe_start_ticks(self) -> int:
        record = _LIVE_PREFIXES.get(id(self))
        if record is not None and record.handle is self:
            return record.probe_start_ticks
        tombstone = _TERMINAL_PREFIXES.get(self)
        if tombstone is not None:
            return tombstone.probe_start_ticks
        return self._probe_start_ticks

    @property
    def state(self) -> str:
        record = _LIVE_PREFIXES.get(id(self))
        if record is not None and record.handle is self:
            return record.state
        tombstone = _TERMINAL_PREFIXES.get(self)
        if tombstone is not None:
            return tombstone.state
        return self._state

    @property
    def probe_facts(self) -> probe_v1.NestedCreatorProbeRawFactsV1:
        record = _LIVE_PREFIXES.get(id(self))
        if record is not None and record.handle is self:
            return record.probe_facts
        tombstone = _TERMINAL_PREFIXES.get(self)
        if tombstone is not None:
            return tombstone.probe_facts
        return self._probe_facts

    @property
    def probe_observed_facts_v2(
        self,
    ) -> probe_v1.NestedCreatorProbeObservedFactsV2:
        record = _LIVE_PREFIXES.get(id(self))
        if record is not None and record.handle is self:
            return record.probe_observed_facts_v2
        tombstone = _TERMINAL_PREFIXES.get(self)
        if tombstone is not None:
            return tombstone.probe_observed_facts_v2
        return self._probe_observed_facts_v2

    def __copy__(self) -> NoReturn:
        _fail("two-birth live prefix cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("two-birth live prefix cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("two-birth live prefix cannot be copied or pickled")


@dataclass(slots=True)
class _LivePrefixOwnershipV1:
    """Trusted mutable ownership kept outside the caller-visible handle."""

    handle: BoundedNestedCreatorTwoBirthLivePrefixV1
    supervisor_pid: int
    supervisor_start_ticks: int
    probe_pid: int
    probe_start_ticks: int
    outer_pid_cell_value: int
    outer_parent_edge: Mapping[str, Any]
    outer_nonce: bytes
    outer_gate_facts: tuple[Mapping[str, Any], ...]
    outer_pidfd_fact: Mapping[str, Any]
    outer_seal_set: int
    outer_role_source_fact: Mapping[str, Any]
    outer_entry_empty_snapshots: tuple[Mapping[str, Any], ...]
    outer_live_snapshots: tuple[Mapping[str, Any], ...]
    probe_facts: probe_v1.NestedCreatorProbeRawFactsV1
    probe_observed_facts_v2: probe_v1.NestedCreatorProbeObservedFactsV2
    nested_session: probe_v1.NestedCreatorProbeLiveSessionV1
    control_cgroup_fd: int
    control_cgroup_device: int
    control_cgroup_inode: int
    owner_pid: int
    owner_process_start_ticks: int
    owner_thread: threading.Thread
    owner_thread_id: int
    owner_native_thread_id: int
    old_subreaper: bool
    subreaper_was_promoted: bool
    state: str = "PROBE_REAPED_SUPERVISOR_LIVE"
    hidden_begin_failure: bool = False
    terminal_prevalidated: bool = False
    closed_result: BoundedNestedCreatorTwoBirthRawResultV1 | None = None
    abort_facts: Any = None


@dataclass(frozen=True, slots=True)
class _TerminalPrefixTombstoneV1:
    state: str
    supervisor_pid: int
    supervisor_start_ticks: int
    probe_pid: int
    probe_start_ticks: int
    probe_facts: probe_v1.NestedCreatorProbeRawFactsV1
    probe_observed_facts_v2: probe_v1.NestedCreatorProbeObservedFactsV2
    owner_pid: int
    owner_process_start_ticks: int
    owner_thread: threading.Thread
    owner_thread_id: int
    owner_native_thread_id: int
    closed_result: BoundedNestedCreatorTwoBirthRawResultV1 | None
    abort_facts: Any


@dataclass(slots=True)
class _BeginFailureQuarantineV1:
    control_cgroup_fd: int
    control_cgroup_device: int
    control_cgroup_inode: int
    live_session: probe_v1.NestedCreatorProbeLiveSessionV1 | None
    owner_pid: int
    owner_process_start_ticks: int
    owner_thread: threading.Thread
    owner_thread_id: int
    owner_native_thread_id: int
    old_subreaper: bool
    allowed_direct_child_pids: tuple[int, ...]
    state: str = "BEGIN_CLEANUP_FAILED_QUARANTINED"
    cleanup_complete: bool = False
    cleanup_result: Any = None


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


def _open_fd_numbers() -> frozenset[int]:
    descriptors: set[int] = set()
    for name in os.listdir("/proc/self/fd"):
        if not name.isdigit():
            continue
        descriptor = int(name)
        try:
            os.fstat(descriptor)
        except OSError:
            continue
        descriptors.add(descriptor)
    return frozenset(descriptors)


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


def begin_bounded_nested_creator_two_birth_live_prefix_v1(
    *,
    control_cgroup_fd: int,
) -> BoundedNestedCreatorTwoBirthLivePrefixV1:
    """Stop after creator-reaping PIDFD_PROBE in caller-exclusive CONTROL.

    This raw API verifies two empty entry snapshots but does not mint the
    upstream exclusive lease; callers must own the supplied CONTROL cgroup.
    """

    global _BEGIN_FAILURE_QUARANTINE, _LAST_BEGIN_FAILURE_RECOVERY
    global _BEGIN_FORK_GUARD

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
    owned_control_cgroup_fd = -1
    recovery_control_cgroup_fd = -1
    live_session: probe_v1.NestedCreatorProbeLiveSessionV1 | None = None
    old_subreaper: bool | None = None
    original_mask: set[signal.Signals] | None = None
    birth_may_have_occurred = False
    begin_cleanup_complete = False
    live_prefix_committed = False
    registered_record: _LivePrefixOwnershipV1 | None = None
    try:
        all_signals = set(signal.valid_signals()) - {
            signal.SIGKILL,
            signal.SIGSTOP,
        }
        original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, all_signals)
        old_subreaper = _get_subreaper()
        with _RUNTIME_LOCK:
            with _PREFIX_REGISTRY_LOCK:
                if _LIVE_PREFIXES or _BEGIN_FAILURE_QUARANTINE is not None:
                    _fail("two-birth runtime already owns one live prefix")
                _LAST_BEGIN_FAILURE_RECOVERY = None
                baseline_fds = _open_fd_numbers()
                _BEGIN_FORK_GUARD = _freeze_json(
                    {
                        "owner_pid": os.getpid(),
                        "owner_thread_id": threading.get_ident(),
                        "allowed_child_fds": tuple(
                            sorted(baseline_fds - {control_cgroup_fd})
                        ),
                    }
                )
            outer_entry_empty_one = (
                probe_v1.observe_nested_creator_control_population_v1(
                    control_cgroup_fd, expected_pids=(), sequence=7000
                )
            )
            outer_entry_empty_two = (
                probe_v1.observe_nested_creator_control_population_v1(
                    control_cgroup_fd, expected_pids=(), sequence=7001
                )
            )
            recovery_control_cgroup_fd = fcntl.fcntl(
                control_cgroup_fd, fcntl.F_DUPFD_CLOEXEC, 5
            )
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
            native_return = -1
            try:
                native_return = int(
                    exec_v1.load_nested_creator_supervisor_exec_birth_entry_v1()(
                        ctypes.pointer(launch_args)
                    )
                )
            finally:
                # clone3 ownership must be captured before any other fallible
                # Python cleanup.
                if int(parent_edge.clone_result) > 0:
                    birth_may_have_occurred = True
                    supervisor_pid = int(parent_edge.clone_result)
                    if int(pidfd_cell.value) >= 0:
                        supervisor_pidfd = int(pidfd_cell.value)
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
            probe_observed_facts_v2 = (
                probe_v1.run_nested_creator_pidfd_probe_observed_v2(
                    live_session, control_cgroup_fd=control_cgroup_fd
                )
            )
            probe_facts = probe_observed_facts_v2.raw_facts_v1
            owned_control_cgroup_fd = fcntl.fcntl(
                control_cgroup_fd, fcntl.F_DUPFD_CLOEXEC, 5
            )
            handle = BoundedNestedCreatorTwoBirthLivePrefixV1(
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
                outer_entry_empty_snapshots=(
                    outer_entry_empty_one,
                    outer_entry_empty_two,
                ),
                outer_live_snapshots=(outer_live_one, outer_live_two),
                probe_facts=probe_facts,
                probe_observed_facts_v2=probe_observed_facts_v2,
                nested_session=live_session,
                control_cgroup_fd=owned_control_cgroup_fd,
                old_subreaper=old_subreaper,
                issuer=_PREFIX_ISSUER,
            )
            record = _LivePrefixOwnershipV1(
                handle=handle,
                supervisor_pid=handle._supervisor_pid,
                supervisor_start_ticks=handle._supervisor_start_ticks,
                probe_pid=handle._probe_pid,
                probe_start_ticks=handle._probe_start_ticks,
                outer_pid_cell_value=handle._outer_pid_cell_value,
                outer_parent_edge=handle._outer_parent_edge,
                outer_nonce=handle._outer_nonce,
                outer_gate_facts=handle._outer_gate_facts,
                outer_pidfd_fact=handle._outer_pidfd_fact,
                outer_seal_set=handle._outer_seal_set,
                outer_role_source_fact=handle._outer_role_source_fact,
                outer_entry_empty_snapshots=handle._outer_entry_empty_snapshots,
                outer_live_snapshots=handle._outer_live_snapshots,
                probe_facts=handle._probe_facts,
                probe_observed_facts_v2=handle._probe_observed_facts_v2,
                nested_session=handle._nested_session,
                control_cgroup_fd=handle._control_cgroup_fd,
                control_cgroup_device=handle._control_cgroup_device,
                control_cgroup_inode=handle._control_cgroup_inode,
                owner_pid=handle._owner_pid,
                owner_process_start_ticks=handle._owner_process_start_ticks,
                owner_thread=handle._owner_thread,
                owner_thread_id=handle._owner_thread_id,
                owner_native_thread_id=handle._owner_native_thread_id,
                old_subreaper=handle._old_subreaper,
                subreaper_was_promoted=handle._subreaper_was_promoted,
            )
            with _PREFIX_REGISTRY_LOCK:
                if _LIVE_PREFIXES:
                    _fail("two-birth live prefix registry changed")
                _LIVE_PREFIXES[id(handle)] = record
                registered_record = record
            _test_fault("AFTER_PREFIX_REGISTER")
            live_session = None
            owned_control_cgroup_fd = -1
            live_prefix_committed = True
            return handle
    except BaseException as original_error:
        try:
            if registered_record is not None:
                _abort_live_prefix_under_lock(registered_record.handle)
                registered_record = None
                live_session = None
                owned_control_cgroup_fd = -1
            elif live_session is not None:
                probe_v1.abort_nested_creator_supervisor_session_v1(
                    live_session, control_cgroup_fd=control_cgroup_fd
                )
                live_session = None
            elif birth_may_have_occurred:
                _abort_control_population(control_cgroup_fd)
        except BaseException as cleanup_error:
            if registered_record is not None:
                registered_record.hidden_begin_failure = True
                registered_record.state = "BEGIN_COMMIT_ABORT_FAILED_QUARANTINED"
                registered_record.handle._state = registered_record.state
                live_session = None
                owned_control_cgroup_fd = -1
                live_prefix_committed = True
            else:
                recovery_status = os.fstat(recovery_control_cgroup_fd)
                with _PREFIX_REGISTRY_LOCK:
                    if _BEGIN_FAILURE_QUARANTINE is not None:
                        _fail("two-birth begin quarantine identity changed")
                    _BEGIN_FAILURE_QUARANTINE = _BeginFailureQuarantineV1(
                        control_cgroup_fd=recovery_control_cgroup_fd,
                        control_cgroup_device=recovery_status.st_dev,
                        control_cgroup_inode=recovery_status.st_ino,
                        live_session=live_session,
                        owner_pid=os.getpid(),
                        owner_process_start_ticks=_read_start_ticks(os.getpid()),
                        owner_thread=threading.current_thread(),
                        owner_thread_id=threading.get_ident(),
                        owner_native_thread_id=threading.get_native_id(),
                        old_subreaper=bool(old_subreaper),
                        allowed_direct_child_pids=tuple(
                            sorted(
                                {
                                    pid
                                    for pid in (
                                        getattr(
                                            live_session,
                                            "supervisor_pid",
                                            supervisor_pid,
                                        ),
                                        getattr(
                                            live_session,
                                            "active_probe_pid",
                                            -1,
                                        ),
                                    )
                                    if type(pid) is int and pid > 0
                                }
                            )
                        ),
                    )
                recovery_control_cgroup_fd = -1
                live_session = None
                live_prefix_committed = True
            raise cleanup_error from original_error
        begin_cleanup_complete = True
        raise
    finally:
        try:
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
                owned_control_cgroup_fd,
                recovery_control_cgroup_fd,
            ):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
            if not live_prefix_committed and begin_cleanup_complete:
                if old_subreaper is False:
                    _set_subreaper(False)
        finally:
            _BEGIN_FORK_GUARD = None
            if original_mask is not None:
                try:
                    signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)
                except BaseException:
                    if registered_record is not None:
                        registered_record.hidden_begin_failure = True
                        registered_record.state = (
                            "BEGIN_RETURN_SIGNAL_FAILED_QUARANTINED"
                        )
                        registered_record.handle._state = registered_record.state
                    raise


def _direct_child_pids() -> tuple[int, ...]:
    raw = Path(
        f"/proc/self/task/{threading.get_native_id()}/children"
    ).read_text(encoding="ascii").strip()
    if not raw:
        return ()
    return tuple(sorted(int(value) for value in raw.split()))


def _require_single_cleanup_thread() -> None:
    task_ids = sorted(
        int(name) for name in os.listdir("/proc/self/task") if name.isdigit()
    )
    if task_ids != [threading.get_native_id()] or threading.active_count() != 1:
        _fail("two-birth cleanup requires one exact owner thread")


def _require_prefix_owner(
    handle: BoundedNestedCreatorTwoBirthLivePrefixV1,
) -> _LivePrefixOwnershipV1 | None:
    with _PREFIX_REGISTRY_LOCK:
        record = _LIVE_PREFIXES.get(id(handle))
        tombstone = _TERMINAL_PREFIXES.get(handle)
    if record is not None and record.handle is not handle:
        record = None
    if record is not None and record.handle is handle:
        owner_pid = record.owner_pid
        owner_process_start_ticks = record.owner_process_start_ticks
        owner_thread = record.owner_thread
        owner_thread_id = record.owner_thread_id
        owner_native_thread_id = record.owner_native_thread_id
    elif tombstone is not None:
        owner_pid = tombstone.owner_pid
        owner_process_start_ticks = tombstone.owner_process_start_ticks
        owner_thread = tombstone.owner_thread
        owner_thread_id = tombstone.owner_thread_id
        owner_native_thread_id = tombstone.owner_native_thread_id
    else:
        owner_pid = getattr(handle, "_owner_pid", -1)
        owner_process_start_ticks = getattr(
            handle, "_owner_process_start_ticks", -1
        )
        owner_thread = getattr(handle, "_owner_thread", None)
        owner_thread_id = getattr(handle, "_owner_thread_id", -1)
        owner_native_thread_id = getattr(
            handle, "_owner_native_thread_id", -1
        )
    if (
        type(handle) is not BoundedNestedCreatorTwoBirthLivePrefixV1
        or (
            record is None
            and tombstone is None
            and getattr(handle, "_issuer", None) is not _PREFIX_ISSUER
        )
        or owner_pid != os.getpid()
        or owner_process_start_ticks != _read_start_ticks(os.getpid())
        or owner_thread is not threading.current_thread()
        or owner_thread_id != threading.get_ident()
        or owner_native_thread_id != threading.get_native_id()
    ):
        _fail("two-birth live prefix owner identity changed")
    return record


def _require_live_prefix(
    handle: BoundedNestedCreatorTwoBirthLivePrefixV1,
    *,
    allowed_states: set[str],
) -> _LivePrefixOwnershipV1:
    record = _require_prefix_owner(handle)
    if (
        record is None
        or record.state not in allowed_states
        or record.control_cgroup_fd < 0
        or record.outer_pid_cell_value != record.supervisor_pid
        or record.outer_pidfd_fact["pid"] != record.supervisor_pid
        or record.probe_facts.supervisor_pid != record.supervisor_pid
        or record.probe_facts.probe_pid != record.probe_pid
        or record.probe_observed_facts_v2.raw_facts_v1
        is not record.probe_facts
    ):
        _fail("two-birth live prefix identity or state changed")
    control_status = os.fstat(record.control_cgroup_fd)
    if (
        control_status.st_dev != record.control_cgroup_device
        or control_status.st_ino != record.control_cgroup_inode
        or not stat.S_ISDIR(control_status.st_mode)
    ):
        _fail("two-birth live prefix CONTROL identity changed")
    session_facts = probe_v1.verify_nested_creator_live_session_v1(
        record.nested_session
    )
    if (
        session_facts["session_state"] != "PROBE_REAPED_SUPERVISOR_LIVE"
        or session_facts["supervisor_pid"] != record.supervisor_pid
        or session_facts["supervisor_start_ticks"]
        != record.supervisor_start_ticks
        or _direct_child_pids() != (record.supervisor_pid,)
    ):
        _fail("two-birth live prefix supervisor ownership changed")
    probe_v1.observe_nested_creator_control_population_v1(
        record.control_cgroup_fd,
        expected_pids=(record.supervisor_pid,),
        sequence=3,
    )
    return record


def _build_closed_result(
    record: _LivePrefixOwnershipV1,
    *,
    supervisor_reap: Mapping[str, Any],
    final_empty_snapshots: tuple[Mapping[str, Any], Mapping[str, Any]],
) -> BoundedNestedCreatorTwoBirthRawResultV1:
    result = BoundedNestedCreatorTwoBirthRawResultV1(
        supervisor_pid=record.supervisor_pid,
        supervisor_start_ticks=record.supervisor_start_ticks,
        probe_pid=record.probe_pid,
        probe_start_ticks=record.probe_start_ticks,
        outer_pid_cell_value=record.outer_pid_cell_value,
        outer_parent_edge=record.outer_parent_edge,
        outer_nonce=record.outer_nonce,
        outer_gate_facts=record.outer_gate_facts,
        outer_pidfd_fact=record.outer_pidfd_fact,
        outer_seal_set=record.outer_seal_set,
        outer_role_source_fact=record.outer_role_source_fact,
        outer_live_snapshots=record.outer_live_snapshots,
        probe_facts=record.probe_facts,
        supervisor_reap=supervisor_reap,
        final_empty_snapshots=final_empty_snapshots,
        _issuer=_RESULT_ISSUER,
    )
    if result.to_document()["maximum_observed_control_population"] != 2:
        _fail("two-birth result population join changed")
    return result


def _finish_prefix_terminal(
    record: _LivePrefixOwnershipV1,
    *,
    terminal_state: str,
    closed_result: BoundedNestedCreatorTwoBirthRawResultV1 | None = None,
    abort_facts: Any = None,
) -> None:
    if terminal_state not in {"CLOSED", "ABORTED_CLOSED"}:
        _fail("two-birth terminal state is invalid")
    with _PREFIX_REGISTRY_LOCK:
        if _LIVE_PREFIXES.get(id(record.handle)) is not record:
            _fail("two-birth live prefix registry changed before terminal commit")
    if terminal_state == "CLOSED":
        if closed_result is None or abort_facts is not None:
            _fail("two-birth normal terminal payload changed")
    elif abort_facts is None or closed_result is not None:
        _fail("two-birth abort terminal payload changed")
    if not record.terminal_prevalidated:
        if _direct_child_pids():
            _fail("two-birth terminal closure retained one direct child")
        control_status = os.fstat(record.control_cgroup_fd)
        if (
            control_status.st_dev != record.control_cgroup_device
            or control_status.st_ino != record.control_cgroup_inode
        ):
            _fail("two-birth terminal CONTROL identity changed")
        probe_v1.observe_nested_creator_control_population_v1(
            record.control_cgroup_fd, expected_pids=(), sequence=9998
        )
        record.terminal_prevalidated = True

    tombstone = _TerminalPrefixTombstoneV1(
        state=terminal_state,
        supervisor_pid=record.supervisor_pid,
        supervisor_start_ticks=record.supervisor_start_ticks,
        probe_pid=record.probe_pid,
        probe_start_ticks=record.probe_start_ticks,
        probe_facts=record.probe_facts,
        probe_observed_facts_v2=record.probe_observed_facts_v2,
        owner_pid=record.owner_pid,
        owner_process_start_ticks=record.owner_process_start_ticks,
        owner_thread=record.owner_thread,
        owner_thread_id=record.owner_thread_id,
        owner_native_thread_id=record.owner_native_thread_id,
        closed_result=closed_result,
        abort_facts=abort_facts,
    )
    all_signals = set(signal.valid_signals()) - {signal.SIGKILL, signal.SIGSTOP}
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, all_signals)
    try:
        _test_fault("BEFORE_SUBREAPER_RESTORE")
        current_subreaper = _get_subreaper()
        if current_subreaper not in {True, record.old_subreaper}:
            _fail("two-birth terminal subreaper state changed")
        if record.subreaper_was_promoted and current_subreaper:
            _set_subreaper(False)
        if _get_subreaper() is not record.old_subreaper:
            _fail("two-birth terminal subreaper restoration changed")
        if record.control_cgroup_fd >= 0:
            descriptor = record.control_cgroup_fd
            try:
                os.close(descriptor)
            except OSError:
                try:
                    os.fstat(descriptor)
                except OSError as status_error:
                    if status_error.errno != errno.EBADF:
                        raise
                else:
                    raise
            record.control_cgroup_fd = -1
            record.handle._control_cgroup_fd = -1
        _test_fault("AFTER_CONTROL_CLOSE")
        record.closed_result = closed_result
        record.abort_facts = abort_facts
        record.handle._closed_result = closed_result
        record.handle._abort_facts = abort_facts
        record.state = terminal_state
        record.handle._state = terminal_state
        with _PREFIX_REGISTRY_LOCK:
            _TERMINAL_PREFIXES[record.handle] = tombstone
            del _LIVE_PREFIXES[id(record.handle)]
        _test_fault("AFTER_REGISTRY_DELETE")
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def _abort_live_prefix_under_lock(
    handle: BoundedNestedCreatorTwoBirthLivePrefixV1,
) -> dict[str, Any]:
    record = _require_prefix_owner(handle)
    with _PREFIX_REGISTRY_LOCK:
        tombstone = _TERMINAL_PREFIXES.get(handle)
    if record is None and tombstone is not None and tombstone.state == "ABORTED_CLOSED":
        if tombstone.abort_facts is None:
            _fail("two-birth cached abort facts are absent")
        return _thaw_json(tombstone.abort_facts)
    if record is None and tombstone is not None and tombstone.state == "CLOSED":
        _fail("two-birth closed prefix cannot be aborted")
    if record is None:
        _fail("two-birth abort prefix was not registered")
    _require_single_cleanup_thread()
    expected_children = (
        ()
        if record.nested_session.state in {"CLOSED", "ABORTED_CLOSED"}
        else (record.supervisor_pid,)
    )
    if _direct_child_pids() != expected_children:
        _fail("two-birth abort found an unrelated direct child")
    record.state = "ABORT_PENDING"
    handle._state = record.state
    try:
        if record.nested_session.state == "CLOSED":
            inner_abort: dict[str, Any] = {
                "state": "ALREADY_CREATOR_REAPED",
                "supervisor_pid": record.supervisor_pid,
            }
        else:
            inner_abort = probe_v1.abort_nested_creator_supervisor_session_v1(
                record.nested_session,
                control_cgroup_fd=record.control_cgroup_fd,
            )
        if record.control_cgroup_fd >= 0:
            empty_one: Mapping[str, Any] = _wait_empty(
                record.control_cgroup_fd, 9996
            )
            empty_two: Mapping[str, Any] = (
                probe_v1.observe_nested_creator_control_population_v1(
                    record.control_cgroup_fd, expected_pids=(), sequence=9997
                )
            )
        elif record.terminal_prevalidated:
            empty_one = {"kind": "TERMINAL_EMPTY_PREVALIDATED"}
            empty_two = {"kind": "TERMINAL_EMPTY_PREVALIDATED"}
        else:
            _fail("two-birth abort lost CONTROL before empty verification")
        facts = {
            "state": "ABORTED_CLOSED",
            "supervisor_pid": record.supervisor_pid,
            "probe_pid": record.probe_pid,
            "inner_abort": inner_abort,
            "empty_snapshots": [dict(empty_one), dict(empty_two)],
        }
        record.abort_facts = _freeze_json(facts)
        _finish_prefix_terminal(
            record,
            terminal_state="ABORTED_CLOSED",
            abort_facts=record.abort_facts,
        )
        return _thaw_json(record.abort_facts)
    except BaseException:
        record.state = "ABORT_FAILED_QUARANTINED"
        handle._state = record.state
        raise


def abort_bounded_nested_creator_two_birth_live_prefix_v1(
    handle: BoundedNestedCreatorTwoBirthLivePrefixV1,
) -> dict[str, Any]:
    """Kill/reap a live prefix and close its exact process-local ownership."""

    with _RUNTIME_LOCK:
        return _abort_live_prefix_under_lock(handle)


def recover_bounded_nested_creator_two_birth_begin_failure_v1() -> dict[str, Any]:
    """Retry exact cleanup when begin failed before returning a capability."""

    global _BEGIN_FAILURE_QUARANTINE, _LAST_BEGIN_FAILURE_RECOVERY

    with _RUNTIME_LOCK:
        with _PREFIX_REGISTRY_LOCK:
            hidden_records = tuple(
                record
                for record in _LIVE_PREFIXES.values()
                if record.hidden_begin_failure
            )
            quarantine = _BEGIN_FAILURE_QUARANTINE
        if len(hidden_records) > 1 or (hidden_records and quarantine is not None):
            _fail("two-birth begin failure recovery identity changed")
        if hidden_records:
            return _abort_live_prefix_under_lock(hidden_records[0].handle)
        if quarantine is None:
            if _LAST_BEGIN_FAILURE_RECOVERY is not None:
                return _thaw_json(_LAST_BEGIN_FAILURE_RECOVERY)
            _fail("two-birth begin failure quarantine is absent")
        if (
            quarantine.owner_pid != os.getpid()
            or quarantine.owner_process_start_ticks != _read_start_ticks(os.getpid())
            or quarantine.owner_thread is not threading.current_thread()
            or quarantine.owner_thread_id != threading.get_ident()
            or quarantine.owner_native_thread_id != threading.get_native_id()
        ):
            _fail("two-birth begin failure recovery owner changed")
        quarantine.state = "BEGIN_CLEANUP_RETRY_PENDING"
        try:
            if not quarantine.cleanup_complete:
                _require_single_cleanup_thread()
                if not set(_direct_child_pids()).issubset(
                    quarantine.allowed_direct_child_pids
                ):
                    _fail(
                        "two-birth begin recovery found an unrelated direct child"
                    )
                status = os.fstat(quarantine.control_cgroup_fd)
                if (
                    status.st_dev != quarantine.control_cgroup_device
                    or status.st_ino != quarantine.control_cgroup_inode
                ):
                    _fail("two-birth begin failure recovery CONTROL changed")
                if quarantine.live_session is not None:
                    cleanup = probe_v1.abort_nested_creator_supervisor_session_v1(
                        quarantine.live_session,
                        control_cgroup_fd=quarantine.control_cgroup_fd,
                    )
                else:
                    cleanup = _abort_control_population(
                        quarantine.control_cgroup_fd
                    )
                quarantine.cleanup_result = _freeze_json(cleanup)
                quarantine.cleanup_complete = True
            facts = {
                "state": "BEGIN_FAILURE_RECOVERED_CLOSED",
                "cleanup": _thaw_json(quarantine.cleanup_result),
            }
            frozen_facts = _freeze_json(facts)
            with _PREFIX_REGISTRY_LOCK:
                if _BEGIN_FAILURE_QUARANTINE is not quarantine:
                    _fail("two-birth begin quarantine identity changed")
            all_signals = set(signal.valid_signals()) - {
                signal.SIGKILL,
                signal.SIGSTOP,
            }
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, all_signals)
            try:
                if quarantine.old_subreaper is False and _get_subreaper():
                    _set_subreaper(False)
                if _get_subreaper() is not quarantine.old_subreaper:
                    _fail("two-birth begin failure subreaper restoration changed")
                if quarantine.control_cgroup_fd >= 0:
                    descriptor = quarantine.control_cgroup_fd
                    try:
                        os.close(descriptor)
                    except OSError:
                        try:
                            os.fstat(descriptor)
                        except OSError as status_error:
                            if status_error.errno != errno.EBADF:
                                raise
                        else:
                            raise
                    quarantine.control_cgroup_fd = -1
                _test_fault("AFTER_BEGIN_RECOVERY_CONTROL_CLOSE")
                quarantine.state = facts["state"]
                _LAST_BEGIN_FAILURE_RECOVERY = frozen_facts
                with _PREFIX_REGISTRY_LOCK:
                    _BEGIN_FAILURE_QUARANTINE = None
                _test_fault("AFTER_BEGIN_RECOVERY_REGISTRY_CLEAR")
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            return _thaw_json(frozen_facts)
        except BaseException:
            if _BEGIN_FAILURE_QUARANTINE is quarantine:
                quarantine.state = "BEGIN_CLEANUP_FAILED_QUARANTINED"
            raise


def snapshot_bounded_nested_creator_two_birth_live_prefix_v1(
    handle: BoundedNestedCreatorTwoBirthLivePrefixV1,
) -> Mapping[str, Any]:
    """Freeze an issuance-time raw observation without exporting capability.

    The returned document contains no retained live descriptor number and
    cannot resume the process-local session.  Nested recvmsg receipts retain
    the historical integer payload of SCM_RIGHTS observations for audit; those
    integers are not live capabilities.  The document deliberately carries no
    E5A/B2 lease join and therefore cannot authorize an exact or exclusive
    topology claim.
    """

    with _RUNTIME_LOCK:
        record = _require_live_prefix(
            handle, allowed_states={"PROBE_REAPED_SUPERVISOR_LIVE"}
        )
        control_status = os.fstat(record.control_cgroup_fd)
        current_one = probe_v1.observe_nested_creator_control_population_v1(
            record.control_cgroup_fd,
            expected_pids=(record.supervisor_pid,),
            sequence=8000,
        )
        current_two = probe_v1.observe_nested_creator_control_population_v1(
            record.control_cgroup_fd,
            expected_pids=(record.supervisor_pid,),
            sequence=8001,
        )
        live_session = probe_v1.verify_nested_creator_live_session_v1(
            record.nested_session
        )
        expected_frames = (
            (
                "CELL_WITHDRAWN",
                b"ACFQP:EXEC_CELL_WITHDRAWN:v1:" + record.outer_nonce.hex().encode("ascii"),
            ),
            (
                "GATE_READY",
                b"ACFQP:EXEC_GATE_READY:v1:" + record.outer_nonce.hex().encode("ascii"),
            ),
            (
                "RELEASE_ECHO",
                b"ACFQP:EXEC_RELEASE:v1:" + record.outer_nonce.hex().encode("ascii"),
            ),
        )
        def require_snapshot(
            value: Mapping[str, Any],
            *,
            sequence: int,
            expected_pids: tuple[int, ...],
        ) -> None:
            expected = tuple(expected_pids)
            if (
                value.get("sequence") != sequence
                or value.get("directory_device") != record.control_cgroup_device
                or value.get("directory_inode") != record.control_cgroup_inode
                or tuple(value.get("first_cgroup_procs", ())) != expected
                or tuple(value.get("second_cgroup_procs", ())) != expected
                or value.get("pids_current") != len(expected)
                or value.get("events", {}).get("populated")
                != int(bool(expected))
                or value.get("events", {}).get("frozen") != 0
            ):
                _fail("two-birth stored CONTROL snapshot join changed")

        for value, sequence in zip(
            record.outer_entry_empty_snapshots,
            (7000, 7001),
            strict=True,
        ):
            require_snapshot(value, sequence=sequence, expected_pids=())
        for value, sequence in zip(
            record.outer_live_snapshots, (1, 2), strict=True
        ):
            require_snapshot(
                value,
                sequence=sequence,
                expected_pids=(record.supervisor_pid,),
            )
        require_snapshot(
            current_one,
            sequence=8000,
            expected_pids=(record.supervisor_pid,),
        )
        require_snapshot(
            current_two,
            sequence=8001,
            expected_pids=(record.supervisor_pid,),
        )
        if (
            record.outer_parent_edge.get("clone_result")
            != record.supervisor_pid
            or record.outer_parent_edge.get("status_bits")
            != exec_v1.PARENT_EDGE_REQUIRED_SUCCESS_BITS
            or record.outer_parent_edge.get("first_cleanup_error") != 0
            or record.outer_parent_edge.get("reserved_zero") != 0
            or record.outer_pid_cell_value != record.supervisor_pid
            or record.outer_pidfd_fact.get("pid") != record.supervisor_pid
            or record.outer_seal_set != REQUIRED_SEALS
            or record.outer_role_source_fact.get("elf_sha256")
            != role_v1.ELF_SHA256
            or record.outer_role_source_fact.get("elf_byte_count")
            != role_v1.ELF_BYTE_COUNT
            or record.outer_role_source_fact.get(
                "source_witness_same_identity"
            )
            is not True
        ):
            _fail("two-birth stored outer supervisor evidence changed")
        for fact, (kind, raw) in zip(
            record.outer_gate_facts, expected_frames, strict=True
        ):
            if (
                fact["kind"] != kind
                or fact["sha256"] != hashlib.sha256(raw).hexdigest()
                or fact["byte_count"] != len(raw)
                or fact["credential_pid"] != record.supervisor_pid
            ):
                _fail("two-birth outer gate snapshot join changed")
        document = {
            "schema": "acfqp.k7_h1_two_birth_live_observation.v1",
            "schema_version": "1.0.0",
            "profile_key": PROFILE_KEY,
            "readiness": READINESS,
            "live_prefix_state_at_issuance": record.state,
            "guardian_identity": {
                "pid": record.owner_pid,
                "process_start_ticks": record.owner_process_start_ticks,
                "thread_id": record.owner_thread_id,
                "native_thread_id": record.owner_native_thread_id,
            },
            "control_cgroup_identity": {
                "device": control_status.st_dev,
                "inode": control_status.st_ino,
                "mode": control_status.st_mode,
            },
            "birth_order": ["SUPERVISOR", "PIDFD_PROBE"],
            "creator_by_role": {
                "SUPERVISOR": "GUARDIAN",
                "PIDFD_PROBE": "SUPERVISOR",
            },
            "supervisor_pid": record.supervisor_pid,
            "supervisor_start_ticks": record.supervisor_start_ticks,
            "probe_pid": record.probe_pid,
            "probe_start_ticks": record.probe_start_ticks,
            "outer_pid_cell_value": record.outer_pid_cell_value,
            "outer_parent_edge": _thaw_json(record.outer_parent_edge),
            "outer_nonce_hex": record.outer_nonce.hex(),
            "outer_registered_expected_frames": [
                {
                    "kind": kind,
                    "payload_hex": raw.hex(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_count": len(raw),
                }
                for kind, raw in expected_frames
            ],
            "outer_receive_facts": _thaw_json(record.outer_gate_facts),
            "outer_pidfd_fact": _thaw_json(record.outer_pidfd_fact),
            "outer_seal_set": record.outer_seal_set,
            "outer_role_source_fact": _thaw_json(record.outer_role_source_fact),
            "entry_empty_control_snapshots": _thaw_json(
                record.outer_entry_empty_snapshots
            ),
            "outer_supervisor_live_snapshots": _thaw_json(
                record.outer_live_snapshots
            ),
            "checkpoint_current_control_snapshots": [
                dict(current_one),
                dict(current_two),
            ],
            "live_session_verification": _thaw_json(live_session),
            "nested_probe_observed_facts_v2": (
                record.probe_observed_facts_v2.to_document()
            ),
            "retained_descriptor_roles": [
                "CONTROL_CGROUP",
                "SUPERVISOR_CONTROL_SOCKET",
                "SUPERVISOR_PIDFD",
            ],
            "retained_live_descriptor_numbers_serialized": False,
            "historical_scm_rights_descriptor_number_observation_present": True,
            "historical_descriptor_numbers_are_not_resume_capability": True,
            "memory_peak_read_count": 0,
            "supervisor_v1_only_accepts_shutdown_after_probe": True,
            "broker_launch_supported_by_live_process": False,
            "target_two_birth_creator_chain_observed": True,
            "exact_creator_reap_ownership_observed": True,
            "portable_observation_checkpoint_present": False,
            "durable_two_birth_artifact_graph_present": False,
            "portable_checkpoint_authority_present": False,
            "live_continuation_capability_portable": False,
            "e5a_runtime_lease_join_present": False,
            "exact_two_birth_os_topology_observed": False,
            "two_birth_prefix_authority_present": False,
            "five_birth_process_authority_present": False,
            "actual_observed_e3_v2_completion_present": False,
            "e4_v2_completion_present": False,
            "production_shared_resource_receipts_present": False,
            "fq11_counter_completeness_present": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "formal_actual_projection_proof_issued": False,
            "current_access_authority_present": False,
            "formal_v7_authority_present": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        }
        return _freeze_json(document)


def close_bounded_nested_creator_two_birth_live_prefix_v1(
    handle: BoundedNestedCreatorTwoBirthLivePrefixV1,
) -> BoundedNestedCreatorTwoBirthRawResultV1:
    """Normally close the live SUPERVISOR and emit the historical V1 result."""

    _require_prefix_owner(handle)
    with _RUNTIME_LOCK:
        record = _require_prefix_owner(handle)
        with _PREFIX_REGISTRY_LOCK:
            tombstone = _TERMINAL_PREFIXES.get(handle)
        if record is None and tombstone is not None and tombstone.state == "CLOSED":
            if tombstone.closed_result is None:
                _fail("two-birth cached closed result is absent")
            return tombstone.closed_result
        if (
            record is None
            and tombstone is not None
            and tombstone.state == "ABORTED_CLOSED"
        ):
            _fail("two-birth aborted prefix cannot be normally closed")
        record = _require_live_prefix(
            handle, allowed_states={"PROBE_REAPED_SUPERVISOR_LIVE"}
        )
        _require_single_cleanup_thread()
        record.state = "NORMAL_CLOSE_PENDING"
        handle._state = record.state
        try:
            probe_v1.shutdown_nested_creator_supervisor_v1(
                record.nested_session
            )
            record.state = "SUPERVISOR_RELEASED_TO_EXIT"
            handle._state = record.state
            _test_fault("AFTER_SHUTDOWN_ECHO")
            supervisor_reap = probe_v1.finish_nested_creator_supervisor_reap_v1(
                record.nested_session
            )
            record.state = "SUPERVISOR_REAPED"
            handle._state = record.state
            _test_fault("AFTER_SUPERVISOR_REAP")
            final_one = _wait_empty(record.control_cgroup_fd, 5)
            final_two = probe_v1.observe_nested_creator_control_population_v1(
                record.control_cgroup_fd, expected_pids=(), sequence=6
            )
            result = _build_closed_result(
                record,
                supervisor_reap=supervisor_reap,
                final_empty_snapshots=(final_one, final_two),
            )
            record.closed_result = result
            _finish_prefix_terminal(
                record, terminal_state="CLOSED", closed_result=result
            )
            return result
        except BaseException:
            if record.state not in {"CLOSED", "ABORTED_CLOSED"}:
                _abort_live_prefix_under_lock(handle)
            raise


def run_bounded_nested_creator_two_birth_runtime_v1(
    *,
    control_cgroup_fd: int,
) -> BoundedNestedCreatorTwoBirthRawResultV1:
    """Compatibility adapter: begin the live cut, then close it normally."""

    handle = begin_bounded_nested_creator_two_birth_live_prefix_v1(
        control_cgroup_fd=control_cgroup_fd
    )
    return close_bounded_nested_creator_two_birth_live_prefix_v1(handle)


def _runtime_atfork_before() -> None:
    _RUNTIME_LOCK.acquire()
    _PREFIX_REGISTRY_LOCK.acquire()


def _runtime_atfork_after_parent() -> None:
    _PREFIX_REGISTRY_LOCK.release()
    _RUNTIME_LOCK.release()


def _runtime_atfork_after_child() -> None:
    global _RUNTIME_LOCK, _PREFIX_REGISTRY_LOCK, _BEGIN_FAILURE_QUARANTINE
    global _BEGIN_FORK_GUARD
    if _BEGIN_FORK_GUARD is not None:
        allowed = set(_BEGIN_FORK_GUARD["allowed_child_fds"])
        for name in os.listdir("/proc/self/fd"):
            if not name.isdigit():
                continue
            descriptor = int(name)
            if descriptor in allowed:
                continue
            try:
                os.close(descriptor)
            except OSError:
                pass
        os._exit(190)
    for record in tuple(_LIVE_PREFIXES.values()):
        if record.control_cgroup_fd >= 0:
            try:
                os.close(record.control_cgroup_fd)
            except OSError:
                pass
            record.control_cgroup_fd = -1
            record.handle._control_cgroup_fd = -1
        record.state = "FORK_CHILD_POISONED"
        record.handle._state = record.state
    _LIVE_PREFIXES.clear()
    _TERMINAL_PREFIXES.clear()
    if _BEGIN_FAILURE_QUARANTINE is not None:
        if _BEGIN_FAILURE_QUARANTINE.control_cgroup_fd >= 0:
            try:
                os.close(_BEGIN_FAILURE_QUARANTINE.control_cgroup_fd)
            except OSError:
                pass
        _BEGIN_FAILURE_QUARANTINE.state = "FORK_CHILD_POISONED"
        _BEGIN_FAILURE_QUARANTINE = None
    _PREFIX_REGISTRY_LOCK = threading.RLock()
    _RUNTIME_LOCK = threading.RLock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(
        before=_runtime_atfork_before,
        after_in_parent=_runtime_atfork_after_parent,
        after_in_child=_runtime_atfork_after_child,
    )


__all__ = (
    "BoundedNestedCreatorTwoBirthLivePrefixV1",
    "BoundedNestedCreatorTwoBirthRawResultV1",
    "ConstructionK7H1NestedCreatorTwoBirthRuntimeV1Error",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS",
    "SCHEMA_VERSION",
    "abort_bounded_nested_creator_two_birth_live_prefix_v1",
    "begin_bounded_nested_creator_two_birth_live_prefix_v1",
    "close_bounded_nested_creator_two_birth_live_prefix_v1",
    "recover_bounded_nested_creator_two_birth_begin_failure_v1",
    "run_bounded_nested_creator_two_birth_runtime_v1",
    "snapshot_bounded_nested_creator_two_birth_live_prefix_v1",
)
