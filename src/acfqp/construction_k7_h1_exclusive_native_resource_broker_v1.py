"""Fresh-exec exclusive native-resource broker for K7 H1 cleanup E3.

This additive V10 vertical slice creates ten new target memfds *inside* a
fresh-exec broker.  Caller/source descriptors are only provisioning inputs;
they are never adopted as target OFDs.  The broker launches two fresh-exec
roles through ``clone3(CLONE_PIDFD | CLONE_INTO_CGROUP)``, binds their kernel
credentials and cgroup membership, consumes their exits with
``waitid(P_PIDFD)``, drains their credential channels (including unexpected
SCM_RIGHTS), and only then closes the ten target OFDs in ordinals 43..52.

The success authority is therefore a new ``BROKER_EXCLUSIVE_PRESENT`` result.
V8 ``PRESENT_LIVE`` bindings are neither accepted nor imported.  Missing
kernel/cgroup prerequisites return a typed unavailable result, and every
post-launch failure returns a noncertificate crash closure; neither path can
mint the cleanup barrier.
"""

from __future__ import annotations

import array
import ctypes
from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import fcntl
import hashlib
import json
import mmap
import os
from pathlib import Path
import platform
import re
import select
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
from types import MappingProxyType
from typing import Any, Mapping, NoReturn, Sequence


# These strings intentionally occur in the sealed fresh-exec source itself.
# The imported V10 registry below independently checks the same values.
_D_PROFILE = "acfqp:construction-k7-h1-exclusive-broker-profile:v1"
_D_SOURCE = "acfqp:construction-k7-h1-exclusive-broker-source-manifest:v1"
_D_GENESIS = "acfqp:construction-k7-h1-exclusive-broker-session-genesis:v1"
_D_PAYLOAD = "acfqp:construction-k7-h1-exclusive-payload-creation:v1"
_D_LAUNCH = "acfqp:construction-k7-h1-exclusive-role-launch-edge:v1"
_D_CREDENTIAL = "acfqp:construction-k7-h1-exclusive-child-credential:v1"
_D_REAP = "acfqp:construction-k7-h1-exclusive-role-reap:v1"
_D_CLOSE = "acfqp:construction-k7-h1-last-legal-reference-closure:v1"
_D_BARRIER = "acfqp:construction-k7-h1-native-cleanup-barrier:v1"
_D_COMPLETE = "acfqp:construction-k7-h1-exclusive-broker-completion:v1"
_D_CRASH = "acfqp:construction-k7-h1-exclusive-broker-crash-closure:v1"
_D_UNAVAILABLE = "acfqp:construction-k7-h1-exclusive-broker-unavailable:v1"

SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E3"
PROFILE_KEY = "construction_k7_h1_exclusive_native_resource_broker_v1"

BROKER_EXCLUSIVE_PRESENT_AUTHORITY_PRESENT = True
V8_PRESENT_LIVE_UPGRADABLE = False
FRESH_EXEC_EXCLUSIVE_BROKER_PRESENT = True
TARGET_OFD_CREATED_FROM_SOURCE_COPY = True
ATOMIC_TWO_ROLE_CLONE3_PIDFD_PRESENT = True
ROLE_CREDENTIAL_CGROUP_BINDING_PRESENT = True
WAITID_PIDFD_REAP_PRESENT = True
QUEUED_SCM_RIGHTS_DRAIN_PRESENT = True
LAST_LEGAL_REFERENCE_CLOSE_AUTHORITY_PRESENT = True
NORMAL_ORDINAL_41_TO_52_BARRIER_AUTHORITY_PRESENT = True
BROKER_CRASH_NONCERTIFICATE_PRESENT = True
OUTPUT_ORDINAL_53_TO_62_AUTHORITY_PRESENT = False
PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
OFFICIAL_EXECUTION_ALLOWED = False

MAX_SOURCE_BYTES_PER_SLOT = 4 * 1024 * 1024
MAX_INTERPRETER_BYTES = 256 * 1024 * 1024
MAX_PACKET_BYTES = 1024 * 1024
MAX_DEADLINE_MILLISECONDS = 60_000
CLEANUP_TIMEOUT_MILLISECONDS = 5_000
_F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
_F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
_F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
_F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
_F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 0x0004)
_F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
REQUIRED_MEMFD_SEALS = (
    _F_SEAL_SEAL | _F_SEAL_SHRINK | _F_SEAL_GROW | _F_SEAL_WRITE
)
_MFD_CLOEXEC = getattr(os, "MFD_CLOEXEC", 0x0001)
_MFD_ALLOW_SEALING = getattr(os, "MFD_ALLOW_SEALING", 0x0002)
_P_PIDFD = getattr(os, "P_PIDFD", 3)
CGROUP2_SUPER_MAGIC = 0x63677270
CLONE_PIDFD = 0x00001000
CLONE_PARENT_SETTID = 0x00100000
CLONE_CLEAR_SIGHAND = 0x100000000
CLONE_INTO_CGROUP = 0x200000000
AT_EMPTY_PATH = 0x1000
KCMP_FILE = 0
PR_SET_DUMPABLE = 4
PR_GET_DUMPABLE = 3
PR_SET_CHILD_SUBREAPER = 36
PR_GET_CHILD_SUBREAPER = 37
PR_SET_NO_NEW_PRIVS = 38
PR_GET_NO_NEW_PRIVS = 39
_CHILD_MODE = "--acfqp-k7-h1-exclusive-broker-child-v1"
_CRASH_POINTS = (
    "NONE",
    "AFTER_TARGET_CREATION",
    "AFTER_WORKER_ESCROW",
    "AFTER_ROLE_REAPS",
    "DURING_CLOSE_47",
)
_F_DUPFD_CLOEXEC = getattr(fcntl, "F_DUPFD_CLOEXEC", 1030)
_MSG_CMSG_CLOEXEC = getattr(socket, "MSG_CMSG_CLOEXEC", 0x40000000)
_OUTPUT_CONTINUATION_NOT_PREBOUND_REASON = "OUTPUT_CONTINUATION_NOT_PREBOUND"

# cleanup ordinal, original V6 normal ordinal, site key, role
PAYLOAD_SLOTS: tuple[tuple[int, int, str, str], ...] = (
    (52, 7, "mount-open:WORKER:sealed_runtime_archive", "WORKER"),
    (51, 9, "mount-open:WORKER:ipc_binding_candidate", "WORKER"),
    (50, 11, "mount-open:WORKER:execution_topology_profile", "WORKER"),
    (49, 13, "mount-open:BUSINESS:sealed_runtime_archive", "BUSINESS"),
    (48, 15, "mount-open:BUSINESS:business_request_candidate", "BUSINESS"),
    (47, 17, "mount-open:BUSINESS:owned_engine_source", "BUSINESS"),
    (46, 19, "mount-open:BUSINESS:owned_engine_authority_document", "BUSINESS"),
    (45, 21, "mount-open:BUSINESS:kernel_replay_document", "BUSINESS"),
    (44, 23, "mount-open:BUSINESS:query_replay_document", "BUSINESS"),
    (43, 25, "mount-open:BUSINESS:fallback_cap_profile", "BUSINESS"),
)
SOURCE_SITE_ORDER = tuple(row[2] for row in sorted(PAYLOAD_SLOTS, key=lambda row: row[1]))
ROLE_ORDER = ("WORKER", "BUSINESS")
ROLE_PAYLOAD_SITES = MappingProxyType(
    {
        role: tuple(row[2] for row in PAYLOAD_SLOTS if row[3] == role)
        for role in ROLE_ORDER
    }
)

_SYSCALLS = MappingProxyType(
    {
        "x86_64": {
            "clone3": 435,
            "execveat": 322,
            "kcmp": 312,
            "memfd_create": 319,
            "pidfd_open": 434,
            "pidfd_send_signal": 424,
        },
        "amd64": {
            "clone3": 435,
            "execveat": 322,
            "kcmp": 312,
            "memfd_create": 319,
            "pidfd_open": 434,
            "pidfd_send_signal": 424,
        },
        "aarch64": {
            "clone3": 435,
            "execveat": 281,
            "kcmp": 272,
            "memfd_create": 279,
            "pidfd_open": 434,
            "pidfd_send_signal": 424,
        },
        "arm64": {
            "clone3": 435,
            "execveat": 281,
            "kcmp": 272,
            "memfd_create": 279,
            "pidfd_open": 434,
            "pidfd_send_signal": 424,
        },
    }
)


class _CloneArgsV10(ctypes.Structure):
    _fields_ = (
        ("flags", ctypes.c_uint64),
        ("pidfd", ctypes.c_uint64),
        ("child_tid", ctypes.c_uint64),
        ("parent_tid", ctypes.c_uint64),
        ("exit_signal", ctypes.c_uint64),
        ("stack", ctypes.c_uint64),
        ("stack_size", ctypes.c_uint64),
        ("tls", ctypes.c_uint64),
        ("set_tid", ctypes.c_uint64),
        ("set_tid_size", ctypes.c_uint64),
        ("cgroup", ctypes.c_uint64),
    )


class _StatFSV10(ctypes.Structure):
    _fields_ = (
        ("f_type", ctypes.c_long),
        ("f_bsize", ctypes.c_long),
        ("f_blocks", ctypes.c_ulong),
        ("f_bfree", ctypes.c_ulong),
        ("f_bavail", ctypes.c_ulong),
        ("f_files", ctypes.c_ulong),
        ("f_ffree", ctypes.c_ulong),
        ("f_fsid", ctypes.c_int * 2),
        ("f_namelen", ctypes.c_long),
        ("f_frsize", ctypes.c_long),
        ("f_flags", ctypes.c_long),
        ("f_spare", ctypes.c_long * 4),
    )


_ROLE_SOURCE = r'''from __future__ import annotations
import array, ctypes, fcntl, hashlib, json, os, socket, struct, sys

def enc(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def open_fds():
    rows=[]
    for name in os.listdir("/proc/self/fd"):
        try:
            fd=int(name); fcntl.fcntl(fd, fcntl.F_GETFD)
        except (OSError, ValueError):
            continue
        rows.append(fd)
    return sorted(set(rows))

def recv_go(endpoint, broker_pid):
    raw, ancillary, flags, _ = endpoint.recvmsg(4096, socket.CMSG_SPACE(struct.calcsize("3i")) + socket.CMSG_SPACE(64), getattr(socket,"MSG_CMSG_CLOEXEC",0x40000000))
    rights=[]; creds=[]
    for level, kind, data in ancillary:
        if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
            values=array.array("i"); values.frombytes(data[:len(data)-(len(data)%values.itemsize)]); rights.extend(values)
        elif level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS and len(data) >= struct.calcsize("3i"):
            creds.append(struct.unpack("3i",data[:struct.calcsize("3i")]))
    for fd in rights:
        try: os.close(fd)
        except OSError: pass
    if flags & (socket.MSG_TRUNC|socket.MSG_CTRUNC) or rights or len(creds)!=1 or creds[0][0]!=broker_pid or raw!=b'{"kind":"GO"}':
        raise RuntimeError("role GO credential or ancillary mismatch")

role=sys.argv[1]
channel_fd=int(sys.argv[2])
source_fd=int(sys.argv[3])
source_sha=sys.argv[4]
payload_fds=tuple(int(value) for value in sys.argv[5].split(",") if value)
session_nonce=sys.argv[6]
broker_pid=int(sys.argv[7])
libc=ctypes.CDLL(None,use_errno=True); libc.prctl.restype=ctypes.c_int
if libc.prctl(4,0,0,0,0)==-1 or libc.prctl(38,1,0,0,0)==-1:
    os._exit(80)
dumpable=libc.prctl(3,0,0,0,0); no_new_privs=libc.prctl(39,0,0,0,0)
if dumpable!=0 or no_new_privs!=1:
    os._exit(80)
source=os.pread(source_fd, 1_000_000, 0)
if hashlib.sha256(source).hexdigest()!=source_sha:
    os._exit(81)
os.close(source_fd)
endpoint=socket.socket(fileno=channel_fd)
endpoint.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
for fd in (channel_fd,*payload_fds):
    os.set_inheritable(fd,False)
expected=sorted((0,1,2,channel_fd,*payload_fds))
observed=open_fds()
cgroup_raw=open("/proc/self/cgroup","rb",buffering=0).read()
ready={"kind":"ROLE_READY","role":role,"pid":os.getpid(),"session_nonce":session_nonce,"channel_fd":channel_fd,"payload_fds":list(payload_fds),"fd_numbers":observed,"expected_fd_numbers":expected,"all_nonstandard_fds_cloexec":all(not os.get_inheritable(fd) for fd in (channel_fd,*payload_fds)),"dumpable_zero":dumpable==0,"no_new_privs":no_new_privs==1,"cgroup_sha256":hashlib.sha256(cgroup_raw).hexdigest()}
endpoint.send(enc(ready))
if observed != expected:
    os._exit(82)
recv_go(endpoint, broker_pid)
for fd in payload_fds:
    os.close(fd)
endpoint.send(enc({"kind":"ROLE_CLOSED","role":role,"pid":os.getpid(),"session_nonce":session_nonce,"closed_payload_fds":list(payload_fds)}))
endpoint.shutdown(socket.SHUT_WR)
endpoint.close()
os._exit(0)
'''


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _not_prebound_output_continuation_context() -> dict[str, str]:
    return {
        "kind": "NOT_APPLICABLE",
        "reason": _OUTPUT_CONTINUATION_NOT_PREBOUND_REASON,
    }


def _valid_prebound_output_continuation_value(value: Any) -> bool:
    return (
        type(value) is str
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    ) or value == _not_prebound_output_continuation_context()


def _raw_content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + _json_bytes(payload)).hexdigest()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_all_fd(descriptor: int, cap: int) -> bytes:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or not 0 < metadata.st_size <= cap:
        raise RuntimeError("descriptor is not one bounded nonempty regular file")
    chunks: list[bytes] = []
    offset = 0
    while offset < metadata.st_size:
        chunk = os.pread(descriptor, min(1024 * 1024, metadata.st_size - offset), offset)
        if not chunk:
            raise RuntimeError("descriptor ended during exact read")
        chunks.append(chunk)
        offset += len(chunk)
    final_metadata = os.fstat(descriptor)
    initial_identity = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )
    final_identity = (
        final_metadata.st_dev,
        final_metadata.st_ino,
        final_metadata.st_mode,
        final_metadata.st_nlink,
        final_metadata.st_uid,
        final_metadata.st_gid,
        final_metadata.st_size,
        final_metadata.st_mtime_ns,
        final_metadata.st_ctime_ns,
    )
    if final_identity != initial_identity:
        raise RuntimeError("descriptor changed during exact read")
    return b"".join(chunks)


def _open_verified_current_executable(
    expected_sha256: str,
) -> tuple[int, dict[str, Any]]:
    """Pin and verify the image backing this process using one exact FD."""

    descriptor = os.open("/proc/self/exe", os.O_RDONLY | os.O_CLOEXEC)
    try:
        raw = _read_all_fd(descriptor, MAX_INTERPRETER_BYTES)
        metadata = os.fstat(descriptor)
        observed_sha256 = _sha(raw)
        if observed_sha256 != expected_sha256:
            raise RuntimeError("running interpreter image changed")
        return descriptor, {
            "proc_path": "/proc/self/exe",
            "fd": descriptor,
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "byte_count": metadata.st_size,
            "sha256": observed_sha256,
            "hash_and_execveat_use_same_fd": True,
        }
    except BaseException:
        os.close(descriptor)
        raise


def _create_sealed_memfd(raw: bytes, name: str) -> int:
    descriptor = _memfd_create(name, _MFD_CLOEXEC | _MFD_ALLOW_SEALING)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise RuntimeError("memfd write made no progress")
            offset += written
        fcntl.fcntl(descriptor, _F_ADD_SEALS, REQUIRED_MEMFD_SEALS)
        if fcntl.fcntl(descriptor, _F_GET_SEALS) & REQUIRED_MEMFD_SEALS != REQUIRED_MEMFD_SEALS:
            raise RuntimeError("memfd complete seal set is absent")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_fd_numbers() -> tuple[int, ...]:
    values: list[int] = []
    for name in os.listdir("/proc/self/fd"):
        try:
            descriptor = int(name)
            fcntl.fcntl(descriptor, fcntl.F_GETFD)
        except (OSError, ValueError):
            continue
        values.append(descriptor)
    return tuple(sorted(set(values)))


def _memfd_create(name: str, flags: int) -> int:
    function = getattr(os, "memfd_create", None)
    if callable(function):
        return int(function(name, flags))
    numbers = _SYSCALLS.get(platform.machine().lower())
    if numbers is None:
        raise OSError(errno.ENOSYS, "memfd_create is unavailable")
    encoded = name.encode("utf-8")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = int(
        libc.syscall(
            ctypes.c_long(numbers["memfd_create"]),
            ctypes.c_char_p(encoded),
            ctypes.c_uint(flags),
        )
    )
    if result < 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return result


def _pidfd_open(pid: int) -> int:
    function = getattr(os, "pidfd_open", None)
    if callable(function):
        return int(function(pid, 0))
    numbers = _SYSCALLS.get(platform.machine().lower())
    if numbers is None:
        raise OSError(errno.ENOSYS, "pidfd_open is unavailable")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = int(
        libc.syscall(
            ctypes.c_long(numbers["pidfd_open"]),
            ctypes.c_int(pid),
            ctypes.c_uint(0),
        )
    )
    if result < 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return result


def _pidfd_send_signal(pidfd: int, signal_number: int) -> None:
    function = getattr(signal, "pidfd_send_signal", None)
    if callable(function):
        function(pidfd, signal_number)
        return
    numbers = _SYSCALLS.get(platform.machine().lower())
    if numbers is None:
        raise OSError(errno.ENOSYS, "pidfd_send_signal is unavailable")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = int(
        libc.syscall(
            ctypes.c_long(numbers["pidfd_send_signal"]),
            ctypes.c_int(pidfd),
            ctypes.c_int(signal_number),
            ctypes.c_void_p(0),
            ctypes.c_uint(0),
        )
    )
    if result < 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def _process_start_ticks(pid: int) -> int:
    raw = Path(f"/proc/{pid}/stat").read_bytes()
    closing = raw.rfind(b")")
    return int(raw[closing + 2 :].split()[19])


def _prctl(option: int, argument: int = 0) -> int:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = libc.prctl(
        ctypes.c_int(option),
        ctypes.c_ulong(argument),
        ctypes.c_ulong(0),
        ctypes.c_ulong(0),
        ctypes.c_ulong(0),
    )
    if result == -1:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return int(result)


def _fdinfo_pid(pidfd: int) -> int:
    rows: dict[str, str] = {}
    with open(f"/proc/self/fdinfo/{pidfd}", "r", encoding="ascii") as stream:
        for line in stream:
            key, separator, value = line.partition(":")
            if separator:
                rows[key.strip()] = value.strip()
    value = int(rows.get("Pid", "-1"))
    if value <= 0:
        raise RuntimeError("pidfd fdinfo lacks one positive PID")
    return value


def _send_packet(endpoint: socket.socket, payload: Mapping[str, Any], rights: Sequence[int] = ()) -> None:
    raw = _json_bytes(dict(payload))
    ancillary: list[tuple[int, int, bytes]] = []
    if rights:
        descriptors = array.array("i", rights)
        ancillary.append((socket.SOL_SOCKET, socket.SCM_RIGHTS, descriptors.tobytes()))
    sent = endpoint.sendmsg([raw], ancillary, getattr(socket, "MSG_NOSIGNAL", 0))
    if sent != len(raw):
        raise RuntimeError("SEQPACKET send was not exact")


def _recv_packet(
    endpoint: socket.socket,
    *,
    deadline: float,
    expected_pid: int,
    expected_rights: int | tuple[int, ...],
    allow_eof: bool = False,
) -> tuple[dict[str, Any] | None, tuple[int, ...], tuple[int, int, int] | None]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("authenticated packet deadline expired")
    readable, _, _ = select.select([endpoint], [], [], remaining)
    if not readable:
        raise TimeoutError("authenticated packet deadline expired")
    raw, ancillary, flags, _address = endpoint.recvmsg(
        MAX_PACKET_BYTES + 1,
        socket.CMSG_SPACE(struct.calcsize("3i")) + socket.CMSG_SPACE(64 * struct.calcsize("i")),
        _MSG_CMSG_CLOEXEC,
    )
    rights: list[int] = []
    credentials: list[tuple[int, int, int]] = []
    try:
        for level, kind, data in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                values = array.array("i")
                values.frombytes(data[: len(data) - (len(data) % values.itemsize)])
                rights.extend(int(value) for value in values)
            elif (
                level == socket.SOL_SOCKET
                and kind == socket.SCM_CREDENTIALS
                and len(data) >= struct.calcsize("3i")
            ):
                credentials.append(struct.unpack("3i", data[: struct.calcsize("3i")]))
            else:
                raise RuntimeError("unexpected ancillary record")
        if not raw:
            if allow_eof and not rights and not credentials:
                return None, (), None
            raise RuntimeError("authenticated channel closed unexpectedly")
        allowed_right_counts = (
            (expected_rights,)
            if type(expected_rights) is int
            else expected_rights
        )
        if (
            len(raw) > MAX_PACKET_BYTES
            or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
            or len(credentials) != 1
            or credentials[0][0] != expected_pid
            or len(rights) not in allowed_right_counts
        ):
            raise RuntimeError("authenticated packet credentials, rights or extent changed")
        payload = json.loads(raw.decode("utf-8"))
        if type(payload) is not dict or _json_bytes(payload) != raw:
            raise RuntimeError("authenticated packet is not canonical JSON")
        return payload, tuple(rights), credentials[0]
    except BaseException:
        for descriptor in rights:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise


def _drain_exact_eof(endpoint: socket.socket, *, deadline: float, expected_pid: int) -> None:
    payload, rights, credential = _recv_packet(
        endpoint,
        deadline=deadline,
        expected_pid=expected_pid,
        expected_rights=0,
        allow_eof=True,
    )
    if payload is not None or rights or credential is not None:
        raise RuntimeError("role channel retained bytes or rights before EOF")


def _fstatfs_magic(descriptor: int) -> int:
    libc = ctypes.CDLL(None, use_errno=True)
    result = _StatFSV10()
    libc.fstatfs.restype = ctypes.c_int
    ctypes.set_errno(0)
    if libc.fstatfs(ctypes.c_int(descriptor), ctypes.byref(result)) == -1:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return int(result.f_type)


def _read_control(directory_fd: int, name: str, cap: int = 65536) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        raw = os.read(descriptor, cap + 1)
        if len(raw) > cap:
            raise RuntimeError("cgroup control exceeded cap")
        return raw
    finally:
        os.close(descriptor)


def _parse_cgroup_procs(raw: bytes) -> tuple[int, ...]:
    try:
        rows = tuple(int(value) for value in raw.decode("ascii").split())
    except (UnicodeError, ValueError) as error:
        raise RuntimeError("cgroup.procs is malformed") from error
    if any(value <= 0 for value in rows) or len(rows) != len(set(rows)):
        raise RuntimeError("cgroup.procs is noncanonical")
    return tuple(sorted(rows))


def _cgroup_populated(directory_fd: int) -> int:
    rows: dict[str, int] = {}
    try:
        text = _read_control(directory_fd, "cgroup.events").decode("ascii")
        for line in text.splitlines():
            key, value = line.split()
            rows[key] = int(value)
    except (UnicodeError, ValueError) as error:
        raise RuntimeError("cgroup.events is malformed") from error
    if rows.get("populated") not in {0, 1}:
        raise RuntimeError("cgroup.events lacks populated")
    return rows["populated"]


def _require_empty_role_cgroup(directory_fd: int) -> None:
    metadata = os.fstat(directory_fd)
    if not stat.S_ISDIR(metadata.st_mode) or _fstatfs_magic(directory_fd) != CGROUP2_SUPER_MAGIC:
        raise RuntimeError("role cgroup FD is not a cgroup-v2 directory")
    if _parse_cgroup_procs(_read_control(directory_fd, "cgroup.procs")):
        raise RuntimeError("role cgroup is not empty")
    if _cgroup_populated(directory_fd) != 0:
        raise RuntimeError("role cgroup remains populated")
    if int(_read_control(directory_fd, "pids.current").decode("ascii").strip()) != 0:
        raise RuntimeError("role cgroup retains a charged task")
    required = {
        "pids.max": "1",
        "cgroup.max.depth": "0",
        "cgroup.max.descendants": "0",
    }
    for name, expected in required.items():
        if _read_control(directory_fd, name).decode("ascii").strip() != expected:
            raise RuntimeError(f"role cgroup {name} is not frozen to {expected}")


def _wait_cgroup_empty(directory_fd: int, deadline: float) -> None:
    stable_once = False
    while time.monotonic() < deadline:
        empty = (
            not _parse_cgroup_procs(_read_control(directory_fd, "cgroup.procs"))
            and _cgroup_populated(directory_fd) == 0
            and int(
                _read_control(directory_fd, "pids.current").decode("ascii").strip()
            )
            == 0
        )
        if empty and stable_once:
            return
        stable_once = empty
        time.sleep(0.005)
    raise TimeoutError("role cgroup did not become empty")


def _cgroup_identity(directory_fd: int) -> dict[str, Any]:
    metadata = os.fstat(directory_fd)
    return {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "path": os.readlink(f"/proc/self/fd/{directory_fd}"),
    }


def _kcmp_file(left_fd: int, right_fd: int) -> bool:
    numbers = _SYSCALLS.get(platform.machine().lower())
    if numbers is None:
        raise RuntimeError("kcmp architecture is unsupported")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = libc.syscall(
        ctypes.c_long(numbers["kcmp"]),
        ctypes.c_int(os.getpid()),
        ctypes.c_int(os.getpid()),
        ctypes.c_int(KCMP_FILE),
        ctypes.c_ulong(left_fd),
        ctypes.c_ulong(right_fd),
    )
    if result == -1:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return result == 0


def _same_ofd_inventory(reference_fd: int) -> tuple[int, ...]:
    matches: list[int] = []
    for descriptor in _open_fd_numbers():
        try:
            if _kcmp_file(reference_fd, descriptor):
                matches.append(descriptor)
        except OSError as error:
            if error.errno == errno.EBADF:
                continue
            raise
    return tuple(sorted(matches))


def _create_exclusive_target_from_source_fd(
    source_fd: int,
    *,
    expected_sha256: str,
    expected_size: int,
    name: str,
) -> dict[str, Any]:
    source_raw = _read_all_fd(source_fd, MAX_SOURCE_BYTES_PER_SLOT)
    source_stat = os.fstat(source_fd)
    source_seals = fcntl.fcntl(source_fd, _F_GET_SEALS)
    if (
        len(source_raw) != expected_size
        or _sha(source_raw) != expected_sha256
        or source_seals & REQUIRED_MEMFD_SEALS != REQUIRED_MEMFD_SEALS
    ):
        raise RuntimeError("source descriptor identity, bytes or seals changed")
    creator_fd = _create_sealed_memfd(source_raw, name)
    master_fd = anchor_fd = -1
    try:
        target_stat = os.fstat(creator_fd)
        if (target_stat.st_dev, target_stat.st_ino) == (source_stat.st_dev, source_stat.st_ino):
            raise RuntimeError("source and target unexpectedly share one inode")
        master_fd = os.open(
            f"/proc/self/fd/{creator_fd}",
            os.O_RDONLY | os.O_CLOEXEC,
        )
        os.close(creator_fd)
        creator_fd = -1
        anchor_fd = fcntl.fcntl(master_fd, _F_DUPFD_CLOEXEC, 3)
        os.set_inheritable(anchor_fd, False)
        if not _kcmp_file(master_fd, anchor_fd):
            raise RuntimeError("target master and anchor are not the same OFD")
        target_stat = os.fstat(master_fd)
        return {
            "master_fd": master_fd,
            "anchor_fd": anchor_fd,
            "source_device": source_stat.st_dev,
            "source_inode": source_stat.st_ino,
            "target_device": target_stat.st_dev,
            "target_inode": target_stat.st_ino,
            "byte_count": len(source_raw),
            "sha256": expected_sha256,
            "seals": fcntl.fcntl(master_fd, _F_GET_SEALS),
            "creator_rw_ofd_closed": True,
        }
    except BaseException:
        for descriptor in (master_fd, anchor_fd):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        raise
    finally:
        if creator_fd >= 0:
            os.close(creator_fd)


def _status_zero_capabilities() -> bool:
    wanted = {"CapInh", "CapPrm", "CapEff", "CapAmb"}
    values: dict[str, int] = {}
    with open("/proc/self/status", "r", encoding="ascii") as stream:
        for line in stream:
            key, separator, value = line.partition(":")
            if separator and key in wanted:
                values[key] = int(value.strip(), 16)
    return set(values) == wanted and not any(values.values())


def _wait_pidfd_reap(pidfd: int, pid: int, deadline: float) -> dict[str, int]:
    poller = select.poll()
    poller.register(pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)
    remaining = deadline - time.monotonic()
    if remaining <= 0 or not poller.poll(max(1, int(remaining * 1000))):
        raise TimeoutError("pidfd did not become terminal")
    observed = os.waitid(_P_PIDFD, pidfd, os.WEXITED | os.WNOWAIT)
    if observed.si_pid != pid:
        raise RuntimeError("pidfd preobservation PID changed")
    consumed = os.waitid(_P_PIDFD, pidfd, os.WEXITED)
    if consumed.si_pid != pid:
        raise RuntimeError("pidfd reap PID changed")
    return {
        "si_pid": int(consumed.si_pid),
        "si_code": int(consumed.si_code),
        "si_status": int(consumed.si_status),
    }


def _exec_role_source(
    *,
    executable_fd: int,
    role_source_fd: int,
    role_source_sha256: str,
    role: str,
    channel_fd: int,
    payload_fds: Sequence[int],
    session_nonce: str,
    broker_pid: int,
) -> NoReturn:
    numbers = _SYSCALLS[platform.machine().lower()]
    argv = (
        sys.executable,
        "-I",
        "-S",
        "-B",
        f"/proc/self/fd/{role_source_fd}",
        role,
        str(channel_fd),
        str(role_source_fd),
        role_source_sha256,
        ",".join(str(value) for value in payload_fds),
        session_nonce,
        str(broker_pid),
    )
    environment = ("LANG=C", "LC_ALL=C", "TZ=UTC")
    encoded_argv = tuple(value.encode("utf-8") for value in argv)
    encoded_env = tuple(value.encode("utf-8") for value in environment)
    argv_array = (ctypes.c_char_p * (len(encoded_argv) + 1))(*encoded_argv, None)
    env_array = (ctypes.c_char_p * (len(encoded_env) + 1))(*encoded_env, None)
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    libc.syscall(
        ctypes.c_long(numbers["execveat"]),
        ctypes.c_int(executable_fd),
        ctypes.c_char_p(b""),
        ctypes.cast(argv_array, ctypes.c_void_p),
        ctypes.cast(env_array, ctypes.c_void_p),
        ctypes.c_int(AT_EMPTY_PATH),
    )
    os._exit(126)


def _clone_role(
    *,
    endpoint_to_supervisor: socket.socket,
    role: str,
    cgroup_fd: int,
    target_by_site: Mapping[str, Mapping[str, Any]],
    executable_fd: int,
    role_source_fd: int,
    role_source_sha256: str,
    session_nonce: str,
    launch_map: mmap.mmap,
    launch_offset: int,
    deadline: float,
    crash_point: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    broker_endpoint, child_endpoint = socket.socketpair(
        socket.AF_UNIX,
        socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC,
    )
    broker_endpoint.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    child_endpoint.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    launch_fds: list[int] = []
    child_payload_fds: tuple[int, ...] = ()
    pidfd_cell = ctypes.c_int(-1)
    shared_pid_cell = ctypes.c_int.from_buffer(launch_map, launch_offset)
    shared_pid_cell.value = 0
    pid = -1
    pidfd = -1
    try:
        for site in ROLE_PAYLOAD_SITES[role]:
            duplicate = fcntl.fcntl(target_by_site[site]["master_fd"], _F_DUPFD_CLOEXEC, 3)
            os.set_inheritable(duplicate, True)
            launch_fds.append(duplicate)
        child_payload_fds = tuple(launch_fds)
        os.set_inheritable(child_endpoint.fileno(), True)
        os.set_inheritable(role_source_fd, True)
        inherited = {0, 1, 2, child_endpoint.fileno(), role_source_fd, *launch_fds}
        if {
            descriptor
            for descriptor in _open_fd_numbers()
            if os.get_inheritable(descriptor)
        } != inherited:
            raise RuntimeError("role pre-clone inheritable FD inventory changed")
        clone_args = _CloneArgsV10(
            flags=(
                CLONE_PIDFD
                | CLONE_PARENT_SETTID
                | CLONE_CLEAR_SIGHAND
                | CLONE_INTO_CGROUP
            ),
            pidfd=ctypes.addressof(pidfd_cell),
            parent_tid=ctypes.addressof(shared_pid_cell),
            exit_signal=signal.SIGCHLD,
            cgroup=cgroup_fd,
        )
        libc = ctypes.CDLL(None, use_errno=True)
        libc.syscall.restype = ctypes.c_long
        numbers = _SYSCALLS[platform.machine().lower()]
        ctypes.set_errno(0)
        result = int(
            libc.syscall(
                ctypes.c_long(numbers["clone3"]),
                ctypes.byref(clone_args),
                ctypes.c_size_t(ctypes.sizeof(clone_args)),
            )
        )
        if result == 0:
            broker_endpoint.close()
            _prctl(PR_SET_DUMPABLE, 0)
            _prctl(PR_SET_NO_NEW_PRIVS, 1)
            _exec_role_source(
                executable_fd=executable_fd,
                role_source_fd=role_source_fd,
                role_source_sha256=role_source_sha256,
                role=role,
                channel_fd=child_endpoint.fileno(),
                payload_fds=launch_fds,
                session_nonce=session_nonce,
                broker_pid=os.getppid(),
            )
        if result < 0:
            code = ctypes.get_errno()
            raise OSError(code, f"clone3 for {role} failed: {os.strerror(code)}")
        pid = result
        pidfd = int(pidfd_cell.value)
        if shared_pid_cell.value != pid or pidfd < 3 or _fdinfo_pid(pidfd) != pid:
            raise RuntimeError("clone3 PID, shared launch cell and pidfd crossed")
        child_endpoint.close()
        os.set_inheritable(role_source_fd, False)
        for descriptor in launch_fds:
            os.set_inheritable(descriptor, False)
            os.close(descriptor)
        launch_fds.clear()
        cgroup_identity = _cgroup_identity(cgroup_fd)
        launch_payload = {
            "schema": "acfqp.k7_h1_exclusive_role_launch_edge.v1",
            "schema_version": SCHEMA_VERSION,
            "session_nonce": session_nonce,
            "role": role,
            "pid": pid,
            "pidfd_fdinfo_pid": _fdinfo_pid(pidfd),
            "clone3_pidfd_atomic": True,
            "clone_parent_settid_shared_journal": True,
            "clone_into_cgroup": True,
            "cgroup_identity": cgroup_identity,
            "payload_sites": list(ROLE_PAYLOAD_SITES[role]),
        }
        launch = {
            **launch_payload,
            "h1_exclusive_role_launch_edge_id": _raw_content_id(_D_LAUNCH, launch_payload),
        }
        _send_packet(
            endpoint_to_supervisor,
            {"kind": "ROLE_LAUNCH", "launch": launch},
            (pidfd,),
        )
        if role == "WORKER" and crash_point == "AFTER_WORKER_ESCROW":
            os._exit(97)
        ready, rights, credential = _recv_packet(
            broker_endpoint,
            deadline=deadline,
            expected_pid=pid,
            expected_rights=0,
        )
        if rights or ready is None or credential is None:
            raise RuntimeError("role READY was absent")
        cgroup_raw = Path(f"/proc/{pid}/cgroup").read_bytes()
        if (
            ready.get("kind") != "ROLE_READY"
            or ready.get("role") != role
            or ready.get("pid") != pid
            or ready.get("session_nonce") != session_nonce
            or type(ready.get("channel_fd")) is not int
            or ready.get("payload_fds") != list(child_payload_fds)
            or ready.get("all_nonstandard_fds_cloexec") is not True
            or ready.get("dumpable_zero") is not True
            or ready.get("no_new_privs") is not True
            or ready.get("fd_numbers") != ready.get("expected_fd_numbers")
            or ready.get("fd_numbers")
            != sorted((0, 1, 2, ready["channel_fd"], *child_payload_fds))
            or ready.get("cgroup_sha256") != _sha(cgroup_raw)
            or _parse_cgroup_procs(_read_control(cgroup_fd, "cgroup.procs")) != (pid,)
        ):
            raise RuntimeError("role credential, FD or cgroup binding changed")
        credential_payload = {
            "schema": "acfqp.k7_h1_exclusive_child_credential.v1",
            "schema_version": SCHEMA_VERSION,
            "session_nonce": session_nonce,
            "role": role,
            "pid": pid,
            "uid": credential[1],
            "gid": credential[2],
            "pidfd_fdinfo_pid": _fdinfo_pid(pidfd),
            "cgroup_identity": cgroup_identity,
            "cgroup_membership_sha256": _sha(cgroup_raw),
            "postexec_fd_numbers": ready["fd_numbers"],
            "postexec_dumpable_zero": ready["dumpable_zero"],
            "postexec_no_new_privs": ready["no_new_privs"],
        }
        credential_attestation = {
            **credential_payload,
            "h1_exclusive_child_credential_id": _raw_content_id(
                _D_CREDENTIAL, credential_payload
            ),
        }
        _send_packet(broker_endpoint, {"kind": "GO"})
        closed, rights, closed_credential = _recv_packet(
            broker_endpoint,
            deadline=deadline,
            expected_pid=pid,
            expected_rights=0,
        )
        if (
            rights
            or closed is None
            or closed_credential is None
            or closed.get("kind") != "ROLE_CLOSED"
            or closed.get("role") != role
            or closed.get("pid") != pid
            or closed.get("session_nonce") != session_nonce
            or closed.get("closed_payload_fds") != list(child_payload_fds)
        ):
            raise RuntimeError("role close acknowledgement changed")
        _drain_exact_eof(broker_endpoint, deadline=deadline, expected_pid=pid)
        waited = _wait_pidfd_reap(pidfd, pid, deadline)
        if waited["si_code"] != os.CLD_EXITED or waited["si_status"] != 0:
            raise RuntimeError("role fresh-exec child did not exit zero")
        _wait_cgroup_empty(cgroup_fd, deadline)
        reap_payload = {
            "schema": "acfqp.k7_h1_exclusive_role_reap.v1",
            "schema_version": SCHEMA_VERSION,
            "session_nonce": session_nonce,
            "role": role,
            "pid": pid,
            "pidfd_waitid_preobserved": True,
            "pidfd_waitid_consumed": True,
            "waitid": waited,
            "channel_eof_observed": True,
            "queued_scm_rights_drained": True,
            "cgroup_empty_verified": True,
        }
        reap = {
            **reap_payload,
            "h1_exclusive_role_reap_id": _raw_content_id(_D_REAP, reap_payload),
        }
        _send_packet(endpoint_to_supervisor, {"kind": "ROLE_REAP", "reap": reap})
        return launch, credential_attestation, reap
    finally:
        del shared_pid_cell
        try:
            os.set_inheritable(role_source_fd, False)
        except OSError:
            pass
        for descriptor in launch_fds:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            child_endpoint.close()
        except OSError:
            pass
        try:
            broker_endpoint.close()
        except OSError:
            pass
        if pidfd >= 0:
            try:
                os.close(pidfd)
            except OSError:
                pass


def _broker_child_main(argv: Sequence[str]) -> int:
    if len(argv) != 14 or argv[1] != _CHILD_MODE:
        return 64
    control_fd = int(argv[2])
    worker_cgroup_fd = int(argv[3])
    business_cgroup_fd = int(argv[4])
    source_code_fd = int(argv[5])
    launch_journal_fd = int(argv[6])
    expected_source_sha256 = argv[7]
    expected_interpreter_sha256 = argv[8]
    session_nonce = argv[9]
    expected_profile_id = argv[10]
    expected_source_manifest_id = argv[11]
    try:
        prebinding_launch_input = json.loads(argv[12])
    except (TypeError, ValueError):
        return 65
    prebound_output_continuation_context_id = (
        prebinding_launch_input.get("prebound_output_continuation_context_id")
        if type(prebinding_launch_input) is dict
        else None
    )
    crash_point = argv[13]
    if (
        crash_point not in _CRASH_POINTS
        or re.fullmatch(r"[0-9a-f]{64}", expected_profile_id) is None
        or re.fullmatch(r"[0-9a-f]{64}", expected_source_manifest_id) is None
        or type(prebinding_launch_input) is not dict
        or set(prebinding_launch_input) != {
            "prebound_output_continuation_context_id"
        }
        or _json_bytes(prebinding_launch_input).decode("utf-8") != argv[12]
        or not _valid_prebound_output_continuation_value(
            prebound_output_continuation_context_id
        )
    ):
        return 65
    parent_pid = os.getppid()
    endpoint = socket.socket(fileno=control_fd)
    endpoint.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    deadline = time.monotonic() + MAX_DEADLINE_MILLISECONDS / 1000
    targets: dict[str, dict[str, Any]] = {}
    source_fds: list[int] = []
    executable_fd = role_source_fd = -1
    launch_map: mmap.mmap | None = None
    try:
        source_raw = _read_all_fd(source_code_fd, 8 * 1024 * 1024)
        if (
            _sha(source_raw) != expected_source_sha256
            or fcntl.fcntl(source_code_fd, _F_GET_SEALS) & REQUIRED_MEMFD_SEALS
            != REQUIRED_MEMFD_SEALS
        ):
            raise RuntimeError("sealed broker source changed")
        launch_journal_stat = os.fstat(launch_journal_fd)
        launch_map = mmap.mmap(launch_journal_fd, 64, access=mmap.ACCESS_WRITE)
        os.close(source_code_fd)
        source_code_fd = -1
        os.close(launch_journal_fd)
        launch_journal_fd = -1
        for descriptor in (control_fd, worker_cgroup_fd, business_cgroup_fd):
            os.set_inheritable(descriptor, False)
        _prctl(PR_SET_DUMPABLE, 0)
        _prctl(PR_SET_NO_NEW_PRIVS, 1)
        if _prctl(PR_GET_DUMPABLE) != 0 or _prctl(PR_GET_NO_NEW_PRIVS) != 1:
            raise RuntimeError("broker privilege boundary did not remain active")
        if not _status_zero_capabilities():
            raise RuntimeError("broker retains effective capability authority")
        _require_empty_role_cgroup(worker_cgroup_fd)
        _require_empty_role_cgroup(business_cgroup_fd)
        worker_identity = _cgroup_identity(worker_cgroup_fd)
        business_identity = _cgroup_identity(business_cgroup_fd)
        if (worker_identity["device"], worker_identity["inode"]) == (
            business_identity["device"],
            business_identity["inode"],
        ):
            raise RuntimeError("worker and business cgroup identities overlap")
        executable_fd, interpreter_execution_identity = _open_verified_current_executable(
            expected_interpreter_sha256
        )
        base_inventory = {
            0,
            1,
            2,
            control_fd,
            worker_cgroup_fd,
            business_cgroup_fd,
            executable_fd,
        }
        runtime_retired: list[dict[str, Any]] = []
        for descriptor in tuple(set(_open_fd_numbers()) - base_inventory):
            target = os.readlink(f"/proc/self/fd/{descriptor}")
            metadata = os.fstat(descriptor)
            if target == "/dev/urandom":
                runtime_retired.append(
                    {"fd": descriptor, "target": target, "cloexec": bool(
                        fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
                    )}
                )
                os.close(descriptor)
        observed_inventory = _open_fd_numbers()
        journal_backing_fds = tuple(
            descriptor
            for descriptor in observed_inventory
            if descriptor not in base_inventory
            and (
                os.fstat(descriptor).st_dev,
                os.fstat(descriptor).st_ino,
            )
            == (launch_journal_stat.st_dev, launch_journal_stat.st_ino)
        )
        if len(journal_backing_fds) > 1:
            raise RuntimeError("mmap retained more than one launch-journal FD")
        expected_inventory = tuple(sorted((*base_inventory, *journal_backing_fds)))
        if observed_inventory != expected_inventory:
            observed_targets = {
                descriptor: os.readlink(f"/proc/self/fd/{descriptor}")
                for descriptor in observed_inventory
            }
            raise RuntimeError(
                "fresh-exec broker inherited FD inventory changed: "
                f"expected={expected_inventory}, observed={observed_inventory}, "
                f"targets={observed_targets}"
            )
        genesis_payload = {
            "schema": "acfqp.k7_h1_exclusive_broker_session_genesis.v1",
            "schema_version": SCHEMA_VERSION,
            "session_nonce": session_nonce,
            "broker_pid": os.getpid(),
            "broker_parent_pid": parent_pid,
            "broker_start_ticks": _process_start_ticks(os.getpid()),
            "broker_source_sha256": expected_source_sha256,
            "interpreter_sha256": expected_interpreter_sha256,
            "interpreter_execution_identity": interpreter_execution_identity,
            "h1_exclusive_broker_profile_id": expected_profile_id,
            "h1_exclusive_broker_source_manifest_id": expected_source_manifest_id,
            "prebound_output_continuation_context_id": (
                prebound_output_continuation_context_id
            ),
            "test_crash_point": crash_point,
            "fresh_exec_observed": True,
            "dumpable_zero": True,
            "no_new_privs": True,
            "zero_effective_capabilities": True,
            "fd_numbers": list(expected_inventory),
            "runtime_opened_fds_retired_before_ready": runtime_retired,
            "launch_journal_mapping_fds": list(journal_backing_fds),
            "launch_journal_identity": {
                "device": launch_journal_stat.st_dev,
                "inode": launch_journal_stat.st_ino,
                "size": launch_journal_stat.st_size,
            },
            "worker_cgroup_identity": worker_identity,
            "business_cgroup_identity": business_identity,
        }
        genesis = {
            **genesis_payload,
            "h1_exclusive_broker_session_genesis_id": _raw_content_id(
                _D_GENESIS, genesis_payload
            ),
        }
        _send_packet(endpoint, {"kind": "BROKER_READY", "genesis": genesis})
        provision, received, credential = _recv_packet(
            endpoint,
            deadline=deadline,
            expected_pid=parent_pid,
            expected_rights=len(SOURCE_SITE_ORDER),
        )
        if provision is None or credential is None or provision.get("kind") != "PROVISION":
            raise RuntimeError("source provisioning packet is absent")
        rows = provision.get("sources")
        if type(rows) is not list or [row.get("site_key") for row in rows] != list(SOURCE_SITE_ORDER):
            raise RuntimeError("source provisioning order changed")
        source_fds.extend(received)
        creations: list[dict[str, Any]] = []
        for index, (site, source_fd, row) in enumerate(zip(SOURCE_SITE_ORDER, source_fds, rows)):
            target = _create_exclusive_target_from_source_fd(
                source_fd,
                expected_sha256=row["sha256"],
                expected_size=row["byte_count"],
                name=f"acfqp-e3-target-{index}",
            )
            targets[site] = target
            creation_payload = {
                "schema": "acfqp.k7_h1_exclusive_payload_creation.v1",
                "schema_version": SCHEMA_VERSION,
                "session_nonce": session_nonce,
                "site_key": site,
                "role": next(item[3] for item in PAYLOAD_SLOTS if item[2] == site),
                "source_sha256": target["sha256"],
                "byte_count": target["byte_count"],
                "source_device": target["source_device"],
                "source_inode": target["source_inode"],
                "target_device": target["target_device"],
                "target_inode": target["target_inode"],
                "required_seals": REQUIRED_MEMFD_SEALS,
                "observed_seals": target["seals"],
                "new_target_inode": True,
                "creator_rw_ofd_closed": True,
                "target_readonly_ofd_created": True,
                "source_ofd_not_adopted": True,
            }
            creations.append(
                {
                    **creation_payload,
                    "h1_exclusive_payload_creation_id": _raw_content_id(
                        _D_PAYLOAD, creation_payload
                    ),
                }
            )
        for descriptor in source_fds:
            os.close(descriptor)
        source_fds.clear()
        if crash_point == "AFTER_TARGET_CREATION":
            os._exit(97)
        role_source_raw = _ROLE_SOURCE.encode("utf-8")
        role_source_sha256 = _sha(role_source_raw)
        role_source_fd = _create_sealed_memfd(role_source_raw, "acfqp-e3-role-source")
        launches: list[dict[str, Any]] = []
        credentials: list[dict[str, Any]] = []
        reaps: list[dict[str, Any]] = []
        for index, (role, cgroup_fd) in enumerate(
            (("WORKER", worker_cgroup_fd), ("BUSINESS", business_cgroup_fd))
        ):
            launch, child_credential, reap = _clone_role(
                endpoint_to_supervisor=endpoint,
                role=role,
                cgroup_fd=cgroup_fd,
                target_by_site=targets,
                executable_fd=executable_fd,
                role_source_fd=role_source_fd,
                role_source_sha256=role_source_sha256,
                session_nonce=session_nonce,
                launch_map=launch_map,
                launch_offset=index * 16,
                deadline=deadline,
                crash_point=crash_point,
            )
            launches.append(launch)
            credentials.append(child_credential)
            reaps.append(reap)
        if crash_point == "AFTER_ROLE_REAPS":
            os._exit(97)
        os.close(role_source_fd)
        role_source_fd = -1
        os.close(executable_fd)
        executable_fd = -1
        memory_peaks = {
            "WORKER": int(_read_control(worker_cgroup_fd, "memory.peak").decode("ascii").strip()),
            "BUSINESS": int(_read_control(business_cgroup_fd, "memory.peak").decode("ascii").strip()),
        }
        ordinal_41 = {
            "normal_ordinal": 41,
            "effect": "EXACT_ROLE_REAPS_COMPLETE",
            "role_reap_ids": [row["h1_exclusive_role_reap_id"] for row in reaps],
            "success": True,
        }
        ordinal_42 = {
            "normal_ordinal": 42,
            "effect": "RETAINED_ROLE_CGROUP_PEAK_READ",
            "memory_peak_bytes_by_role": memory_peaks,
            "peak_working_bytes": max(memory_peaks.values()),
            "success": True,
        }
        close_rows: list[dict[str, Any]] = []
        for cleanup_ordinal, normal_ordinal, site, role in sorted(PAYLOAD_SLOTS):
            if cleanup_ordinal == 47 and crash_point == "DURING_CLOSE_47":
                os._exit(97)
            target = targets[site]
            master = target["master_fd"]
            anchor = target["anchor_fd"]
            before = _same_ofd_inventory(master)
            if before != tuple(sorted((master, anchor))):
                raise RuntimeError("target OFD retained an unledgered broker alias")
            os.close(master)
            target["master_fd"] = -1
            after_master = _same_ofd_inventory(anchor)
            if after_master != (anchor,):
                raise RuntimeError("target OFD retained an alias after master close")
            os.close(anchor)
            target["anchor_fd"] = -1
            close_payload = {
                "schema": "acfqp.k7_h1_last_legal_reference_closure.v1",
                "schema_version": SCHEMA_VERSION,
                "session_nonce": session_nonce,
                "normal_ordinal": cleanup_ordinal,
                "source_normal_ordinal": normal_ordinal,
                "site_key": site,
                "role": role,
                "authority_disposition": "BROKER_EXCLUSIVE_PRESENT",
                "preclose_same_ofd_fds": list(before),
                "after_master_same_ofd_fds": list(after_master),
                "both_roles_reaped": True,
                "both_role_channels_eof_and_rights_drained": True,
                "both_role_cgroups_empty": True,
                "master_closed": True,
                "anchor_closed": True,
                "last_legal_reference_closed": True,
                "global_kernel_reference_count_observed": False,
                "mount_resource_release_proven": False,
            }
            close_rows.append(
                {
                    **close_payload,
                    "h1_last_legal_reference_closure_id": _raw_content_id(
                        _D_CLOSE, close_payload
                    ),
                }
            )
        barrier_payload = {
            "schema": "acfqp.k7_h1_native_cleanup_barrier.v1",
            "schema_version": SCHEMA_VERSION,
            "session_nonce": session_nonce,
            "authority_disposition": "BROKER_EXCLUSIVE_PRESENT",
            "prebound_output_continuation_context_id": (
                prebound_output_continuation_context_id
            ),
            "completed_normal_ordinals": list(range(41, 53)),
            "ordinal_41_event": ordinal_41,
            "ordinal_42_event": ordinal_42,
            "last_legal_reference_closure_ids": [
                row["h1_last_legal_reference_closure_id"] for row in close_rows
            ],
            "normal_ordinal_41_to_52_success_events_issued": True,
            "native_cleanup_complete": True,
            "output_ordinal_53_prerequisite_satisfied": True,
            "output_ordinals_53_to_62_authorized": False,
        }
        barrier = {
            **barrier_payload,
            "h1_native_cleanup_barrier_id": _raw_content_id(_D_BARRIER, barrier_payload),
        }
        completion_payload = {
            "schema": "acfqp.k7_h1_exclusive_broker_completion.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "session_nonce": session_nonce,
            "authority_disposition": "BROKER_EXCLUSIVE_PRESENT",
            "h1_exclusive_broker_profile_id": expected_profile_id,
            "h1_exclusive_broker_source_manifest_id": expected_source_manifest_id,
            "prebound_output_continuation_context_id": (
                prebound_output_continuation_context_id
            ),
            "broker_session_genesis": genesis,
            "payload_creations": creations,
            "role_launches": launches,
            "child_credentials": credentials,
            "role_reaps": reaps,
            "last_legal_reference_closures": close_rows,
            "native_cleanup_barrier": barrier,
            "broker_exclusive_present": True,
            "v8_present_live_used": False,
            "source_ofd_adopted": False,
            "normal_ordinal_41_to_52_success_events_issued": True,
            "output_ordinals_53_to_62_authorized": False,
            "production_output_leaf_authority_present": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "official_execution_allowed": False,
        }
        completion = {
            **completion_payload,
            "h1_exclusive_broker_completion_id": _raw_content_id(
                _D_COMPLETE, completion_payload
            ),
        }
        _send_packet(endpoint, {"kind": "COMPLETE", "completion": completion})
        endpoint.shutdown(socket.SHUT_WR)
        return 0
    except BaseException as error:
        try:
            _send_packet(
                endpoint,
                {
                    "kind": "BROKER_FAILURE",
                    "failure_type": type(error).__name__,
                    "failure_message": str(error)[:512],
                    "normal_ordinal_41_to_52_success_events_issued": False,
                    "native_cleanup_barrier_issued": False,
                },
            )
        except BaseException:
            pass
        return 91
    finally:
        for target in targets.values():
            for key in ("master_fd", "anchor_fd"):
                descriptor = int(target.get(key, -1))
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
        for descriptor in (*source_fds, executable_fd, role_source_fd, source_code_fd, launch_journal_fd):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if launch_map is not None:
            try:
                launch_map.close()
            except (BufferError, OSError):
                pass
        try:
            endpoint.close()
        except OSError:
            pass


if __name__ == "__main__":  # fresh-exec broker never imports the project package
    os._exit(_broker_child_main(sys.argv))


from acfqp import construction_k7_h1_domain_registry_extension_v10 as domains_v10
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


_RESULT_ISSUER = object()
_PROFILE_ISSUER = object()
_SOURCE_ISSUER = object()
_CONTENT_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ConstructionK7H1ExclusiveNativeResourceBrokerV1Error(ValueError):
    """The E3 source, kernel authority or exact cleanup protocol crossed."""


class H1ExclusiveBrokerUnavailableReasonV1(str, Enum):
    NOT_LINUX = "NOT_LINUX"
    UNSUPPORTED_ARCHITECTURE = "UNSUPPORTED_ARCHITECTURE"
    MULTITHREADED_SUPERVISOR = "MULTITHREADED_SUPERVISOR"
    SIGCHLD_DISPOSITION_UNSAFE = "SIGCHLD_DISPOSITION_UNSAFE"
    MEMFD_SEAL_UNAVAILABLE = "MEMFD_SEAL_UNAVAILABLE"
    KCMP_UNAVAILABLE = "KCMP_UNAVAILABLE"
    CLONE3_UNAVAILABLE = "CLONE3_UNAVAILABLE"
    PIDFD_WAIT_UNAVAILABLE = "PIDFD_WAIT_UNAVAILABLE"
    SUBREAPER_UNAVAILABLE = "SUBREAPER_UNAVAILABLE"
    CGROUP_AUTHORITY_REQUIRED = "CGROUP_AUTHORITY_REQUIRED"
    CGROUP_AUTHORITY_INVALID = "CGROUP_AUTHORITY_INVALID"


class H1ExclusiveBrokerCrashPointV1(str, Enum):
    NONE = "NONE"
    AFTER_TARGET_CREATION = "AFTER_TARGET_CREATION"
    AFTER_WORKER_ESCROW = "AFTER_WORKER_ESCROW"
    AFTER_ROLE_REAPS = "AFTER_ROLE_REAPS"
    DURING_CLOSE_47 = "DURING_CLOSE_47"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1ExclusiveNativeResourceBrokerV1Error(message)


def _normalize_prebound_output_continuation_context_id(
    value: str | None,
) -> str | dict[str, str]:
    if value is None:
        return _not_prebound_output_continuation_context()
    if type(value) is str and _CONTENT_ID_PATTERN.fullmatch(value) is not None:
        return value
    _fail("prebound output-continuation context ID is not lowercase 64-hex or None")


def _verify_prebound_output_continuation_echo(
    observed: Any,
    expected: str | Mapping[str, str],
) -> None:
    if not _valid_prebound_output_continuation_value(observed) or observed != expected:
        raise RuntimeError("prebound output-continuation context echo crossed launch input")


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1ExclusiveNativeResourceBrokerV1Error(
            f"{label} is not one content ID"
        ) from error


def _domain_id(domain: str, payload: Any) -> str:
    return domains_v10.extension_content_id_v10(domain, payload)


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1ExclusiveNativeResourceBrokerV1Error(
            f"{label} is not canonical"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


@dataclass(frozen=True, slots=True)
class H1ExclusiveBrokerProfileV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    profile_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("exclusive broker profile is caller-minted")
        payload = _canonical_document(self.payload_bytes, "exclusive broker profile")
        object.__setattr__(
            self,
            "profile_id",
            _domain_id(domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_PROFILE_V1_DOMAIN, payload),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_canonical_document(self.payload_bytes, "exclusive broker profile"),
            "h1_exclusive_broker_profile_id": self.profile_id,
        }


@dataclass(frozen=True, slots=True)
class H1ExclusiveBrokerSourceManifestV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    manifest_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_ISSUER:
            _fail("exclusive broker source manifest is caller-minted")
        payload = _canonical_document(self.payload_bytes, "exclusive broker source manifest")
        object.__setattr__(
            self,
            "manifest_id",
            _domain_id(
                domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_SOURCE_MANIFEST_V1_DOMAIN,
                payload,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_canonical_document(self.payload_bytes, "exclusive broker source manifest"),
            "h1_exclusive_broker_source_manifest_id": self.manifest_id,
        }


@dataclass(frozen=True, slots=True)
class H1ExclusiveBrokerUnavailableV1:
    _issuer: InitVar[object]
    reason: H1ExclusiveBrokerUnavailableReasonV1
    prerequisites: Mapping[str, bool]
    document: Mapping[str, Any] = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER or type(self.reason) is not H1ExclusiveBrokerUnavailableReasonV1:
            _fail("exclusive broker unavailable result is caller-minted")
        payload = {
            "schema": "acfqp.k7_h1_exclusive_broker_unavailable.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "reason": self.reason.value,
            "prerequisites": dict(self.prerequisites),
            "broker_launched": False,
            "broker_exclusive_present": False,
            "normal_ordinal_41_to_52_success_events_issued": False,
            "native_cleanup_barrier_issued": False,
            "output_ordinals_53_to_62_authorized": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "official_execution_allowed": False,
        }
        object.__setattr__(
            self,
            "document",
            MappingProxyType(
                {
                    **payload,
                    "h1_exclusive_broker_unavailable_id": _domain_id(
                        domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_UNAVAILABLE_V1_DOMAIN,
                        payload,
                    ),
                }
            ),
        )

    def to_document(self) -> dict[str, Any]:
        return dict(self.document)


@dataclass(frozen=True, slots=True)
class H1ExclusiveBrokerCrashClosureV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    crash_closure_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("exclusive broker crash closure is caller-minted")
        payload = _canonical_document(self.payload_bytes, "exclusive broker crash closure")
        object.__setattr__(
            self,
            "crash_closure_id",
            _domain_id(
                domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_CRASH_CLOSURE_V1_DOMAIN,
                payload,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_canonical_document(self.payload_bytes, "exclusive broker crash closure"),
            "h1_exclusive_broker_crash_closure_id": self.crash_closure_id,
        }


@dataclass(frozen=True, slots=True)
class H1ExclusiveBrokerCompletionV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    completion_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("exclusive broker completion is caller-minted")
        document = _canonical_document(self.payload_bytes, "exclusive broker completion")
        payload = dict(document)
        supplied = _cid(
            payload.pop("h1_exclusive_broker_completion_id", None),
            "exclusive broker completion",
        )
        expected = _domain_id(
            domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_COMPLETION_V1_DOMAIN,
            payload,
        )
        if supplied != expected:
            _fail("exclusive broker completion content ID changed")
        _verify_completion_document(document)
        object.__setattr__(self, "completion_id", supplied)

    def to_document(self) -> dict[str, Any]:
        return _canonical_document(self.payload_bytes, "exclusive broker completion")


def _profile_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_exclusive_broker_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "authority_disposition": "BROKER_EXCLUSIVE_PRESENT",
        "accepted_upstream_dispositions": [],
        "v8_present_live_upgradable": False,
        "payload_slot_count": 10,
        "role_order": list(ROLE_ORDER),
        "normal_cleanup_ordinals": list(range(41, 53)),
        "target_created_by_source_copy": True,
        "clone3_pidfd_into_distinct_cgroups_required": True,
        "exact_postexec_fd_inventory_required": True,
        "scm_credentials_required": True,
        "unexpected_scm_rights_closed_before_rejection": True,
        "waitid_pidfd_reap_required": True,
        "pidfd_capability_probe_child_launches_per_reached_admission": 1,
        "subreaper_opposite_value_restore_probe_required": True,
        "cgroup_classification_precedes_runtime_admission": True,
        "execution_cleanup_window_milliseconds": CLEANUP_TIMEOUT_MILLISECONDS,
        "prelaunch_failure_typed_crash_closure_forbidden": True,
        "optional_output_continuation_prebinding_present": True,
        "output_continuation_prebinding_authorizes_output": False,
        "kcmp_broker_inventory_required": True,
        "output_ordinals_53_to_62_authorized": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "official_execution_allowed": False,
    }


_PROFILE = H1ExclusiveBrokerProfileV1(
    _PROFILE_ISSUER,
    canonical_json_bytes(_profile_payload()),
)


def official_h1_exclusive_broker_profile_v1() -> H1ExclusiveBrokerProfileV1:
    return _PROFILE


def official_h1_exclusive_broker_source_manifest_v1() -> H1ExclusiveBrokerSourceManifestV1:
    path = Path(__file__).resolve()
    raw = path.read_bytes()
    executable_fd = os.open("/proc/self/exe", os.O_RDONLY | os.O_CLOEXEC)
    try:
        interpreter = _read_all_fd(executable_fd, MAX_INTERPRETER_BYTES)
        interpreter_stat = os.fstat(executable_fd)
    finally:
        os.close(executable_fd)
    payload = {
        "schema": "acfqp.k7_h1_exclusive_broker_source_manifest.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "source_path_display": path.name,
        "source_sha256": _sha(raw),
        "source_byte_count": len(raw),
        "source_staged_as_sealed_memfd": True,
        "interpreter_path_display": "/proc/self/exe",
        "interpreter_sha256": _sha(interpreter),
        "interpreter_byte_count": len(interpreter),
        "interpreter_device": interpreter_stat.st_dev,
        "interpreter_inode": interpreter_stat.st_ino,
        "interpreter_manifest_read_from_one_fd": True,
        "fresh_exec_flags": ["-I", "-S", "-B"],
    }
    return H1ExclusiveBrokerSourceManifestV1(
        _SOURCE_ISSUER,
        canonical_json_bytes(payload),
    )


def _thread_count() -> int | None:
    try:
        return len(tuple(Path("/proc/self/task").iterdir()))
    except OSError:
        return None


def _probe_clone3() -> bool:
    numbers = _SYSCALLS.get(platform.machine().lower())
    if numbers is None:
        return False
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = libc.syscall(ctypes.c_long(numbers["clone3"]), ctypes.c_void_p(0), ctypes.c_size_t(0))
    return result == -1 and ctypes.get_errno() != errno.ENOSYS


def _probe_memfd_sealing() -> bool:
    descriptor = -1
    try:
        descriptor = _create_sealed_memfd(b"e3-probe", "acfqp-e3-seal-probe")
        return (
            fcntl.fcntl(descriptor, _F_GET_SEALS) & REQUIRED_MEMFD_SEALS
            == REQUIRED_MEMFD_SEALS
        )
    except (KeyError, OSError, RuntimeError):
        return False
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _probe_kcmp() -> bool:
    first_read = first_write = duplicate = second_read = second_write = -1
    try:
        first_read, first_write = os.pipe2(os.O_CLOEXEC)
        duplicate = fcntl.fcntl(first_read, _F_DUPFD_CLOEXEC, 3)
        second_read, second_write = os.pipe2(os.O_CLOEXEC)
        return _kcmp_file(first_read, duplicate) and not _kcmp_file(first_read, second_read)
    except (OSError, RuntimeError):
        return False
    finally:
        for descriptor in (first_read, first_write, duplicate, second_read, second_write):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _probe_pidfd_wait() -> bool:
    """Exercise pidfd open/signal/waitid and consume every probe child."""

    if not hasattr(os, "fork") or not hasattr(os, "waitid"):
        return False
    ready_read = ready_write = pidfd = -1
    pid = -1
    reaped = False
    try:
        ready_read, ready_write = os.pipe2(os.O_CLOEXEC)
        pid = os.fork()
        if pid == 0:  # pragma: no cover - exercised by the real kernel probe
            try:
                os.close(ready_read)
                os.write(ready_write, b"1")
                os.close(ready_write)
                while True:
                    signal.pause()
            except BaseException:
                os._exit(125)
        os.close(ready_write)
        ready_write = -1
        readable, _, _ = select.select([ready_read], [], [], 1.0)
        if not readable or os.read(ready_read, 1) != b"1":
            return False
        pidfd = _pidfd_open(pid)
        if _fdinfo_pid(pidfd) != pid:
            return False
        _pidfd_send_signal(pidfd, signal.SIGKILL)
        waited = _wait_pidfd_reap(pidfd, pid, time.monotonic() + 2.0)
        reaped = True
        return (
            waited["si_pid"] == pid
            and waited["si_code"] == os.CLD_KILLED
            and waited["si_status"] == signal.SIGKILL
        )
    except (AttributeError, ChildProcessError, KeyError, OSError, RuntimeError, TimeoutError):
        return False
    finally:
        for descriptor in (ready_read, ready_write, pidfd):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if pid > 0 and not reaped:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass


def _probe_subreaper() -> bool:
    """Toggle the bit, then restore it; restoration failure is fatal."""

    try:
        original = _get_subreaper()
    except OSError:
        return False
    try:
        opposite = 0 if original else 1
        previous = _set_subreaper(opposite)
        return previous == original and _get_subreaper() == opposite
    except (OSError, RuntimeError):
        return False
    finally:
        try:
            _set_subreaper(original)
            if _get_subreaper() != original:
                raise RuntimeError("subreaper probe restoration was not exact")
        except (OSError, RuntimeError) as error:
            raise RuntimeError(
                "subreaper capability probe could not restore prior state"
            ) from error


def _probe_prerequisites(
    worker_cgroup_fd: int | None,
    business_cgroup_fd: int | None,
) -> tuple[dict[str, bool], H1ExclusiveBrokerUnavailableReasonV1 | None]:
    facts = {
        "linux": False,
        "supported_architecture": False,
        "single_threaded_supervisor": False,
        "sigchld_default": False,
        "memfd_sealing": False,
        "kcmp_file": False,
        "clone3": False,
        "pidfd_wait": False,
        "subreaper_prctl": False,
        "worker_cgroup_fd_supplied": type(worker_cgroup_fd) is int and worker_cgroup_fd >= 3,
        "business_cgroup_fd_supplied": type(business_cgroup_fd) is int and business_cgroup_fd >= 3,
        "role_cgroups_valid": False,
    }
    if not facts["worker_cgroup_fd_supplied"] or not facts["business_cgroup_fd_supplied"]:
        return facts, H1ExclusiveBrokerUnavailableReasonV1.CGROUP_AUTHORITY_REQUIRED
    try:
        assert worker_cgroup_fd is not None and business_cgroup_fd is not None
        _require_empty_role_cgroup(worker_cgroup_fd)
        _require_empty_role_cgroup(business_cgroup_fd)
        left = os.fstat(worker_cgroup_fd)
        right = os.fstat(business_cgroup_fd)
        facts["role_cgroups_valid"] = (left.st_dev, left.st_ino) != (right.st_dev, right.st_ino)
    except (OSError, RuntimeError, UnicodeError, ValueError):
        facts["role_cgroups_valid"] = False
    if not facts["role_cgroups_valid"]:
        return facts, H1ExclusiveBrokerUnavailableReasonV1.CGROUP_AUTHORITY_INVALID
    ordered_probes = (
        (
            "linux",
            lambda: sys.platform.startswith("linux"),
            H1ExclusiveBrokerUnavailableReasonV1.NOT_LINUX,
        ),
        (
            "supported_architecture",
            lambda: platform.machine().lower() in _SYSCALLS,
            H1ExclusiveBrokerUnavailableReasonV1.UNSUPPORTED_ARCHITECTURE,
        ),
        (
            "single_threaded_supervisor",
            lambda: _thread_count() == 1,
            H1ExclusiveBrokerUnavailableReasonV1.MULTITHREADED_SUPERVISOR,
        ),
        (
            "sigchld_default",
            lambda: signal.getsignal(signal.SIGCHLD) is signal.SIG_DFL,
            H1ExclusiveBrokerUnavailableReasonV1.SIGCHLD_DISPOSITION_UNSAFE,
        ),
        (
            "memfd_sealing",
            _probe_memfd_sealing,
            H1ExclusiveBrokerUnavailableReasonV1.MEMFD_SEAL_UNAVAILABLE,
        ),
        (
            "kcmp_file",
            _probe_kcmp,
            H1ExclusiveBrokerUnavailableReasonV1.KCMP_UNAVAILABLE,
        ),
        (
            "clone3",
            _probe_clone3,
            H1ExclusiveBrokerUnavailableReasonV1.CLONE3_UNAVAILABLE,
        ),
        (
            "pidfd_wait",
            _probe_pidfd_wait,
            H1ExclusiveBrokerUnavailableReasonV1.PIDFD_WAIT_UNAVAILABLE,
        ),
        (
            "subreaper_prctl",
            _probe_subreaper,
            H1ExclusiveBrokerUnavailableReasonV1.SUBREAPER_UNAVAILABLE,
        ),
    )
    for name, probe, reason in ordered_probes:
        facts[name] = bool(probe())
        if not facts[name]:
            return facts, reason
    return facts, None


def probe_h1_exclusive_native_resource_broker_v1(
    *,
    worker_cgroup_fd: int | None = None,
    business_cgroup_fd: int | None = None,
) -> Mapping[str, Any]:
    facts, blocker = _probe_prerequisites(worker_cgroup_fd, business_cgroup_fd)
    return MappingProxyType(
        {
            "schema": "acfqp.k7_h1_exclusive_broker_capability_probe.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "prerequisites": facts,
            "admitted": blocker is None,
            "blocker": None if blocker is None else blocker.value,
            "success_authority_issued": False,
            "official_execution_allowed": False,
        }
    )


def _validate_sources(source_payloads: Mapping[str, bytes]) -> tuple[tuple[str, bytes], ...]:
    if type(source_payloads) is not dict or tuple(source_payloads) != SOURCE_SITE_ORDER:
        _fail("source payload mapping must use the exact V6 site order")
    rows: list[tuple[str, bytes]] = []
    for site in SOURCE_SITE_ORDER:
        raw = source_payloads[site]
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_SOURCE_BYTES_PER_SLOT:
            _fail("source payload is not one bounded nonempty byte string")
        rows.append((site, raw))
    return tuple(rows)


def _verify_content_object(row: Mapping[str, Any], *, id_name: str, domain: str) -> None:
    payload = dict(row)
    supplied = _cid(payload.pop(id_name, None), id_name)
    if _domain_id(domain, payload) != supplied:
        _fail(f"{id_name} changed content")


def _verify_completion_document(document: Mapping[str, Any]) -> None:
    profile_id = _cid(
        document.get("h1_exclusive_broker_profile_id"),
        "exclusive broker profile reference",
    )
    source_manifest_id = _cid(
        document.get("h1_exclusive_broker_source_manifest_id"),
        "exclusive broker source-manifest reference",
    )
    prebound_output_continuation_context_id = document.get(
        "prebound_output_continuation_context_id"
    )
    if (
        document.get("schema") != "acfqp.k7_h1_exclusive_broker_completion.v1"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or profile_id != official_h1_exclusive_broker_profile_v1().profile_id
        or source_manifest_id
        != official_h1_exclusive_broker_source_manifest_v1().manifest_id
        or not _valid_prebound_output_continuation_value(
            prebound_output_continuation_context_id
        )
        or document.get("authority_disposition") != "BROKER_EXCLUSIVE_PRESENT"
        or document.get("broker_exclusive_present") is not True
        or document.get("v8_present_live_used") is not False
        or document.get("source_ofd_adopted") is not False
        or document.get("normal_ordinal_41_to_52_success_events_issued") is not True
        or document.get("output_ordinals_53_to_62_authorized") is not False
        or document.get("production_output_leaf_authority_present") is not False
        or document.get("formal_counter_records_issued") is not False
        or document.get("formal_work_vector_issued") is not False
        or document.get("formal_comparison_vector_issued") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("exclusive broker completion authority flags changed")
    creations = document.get("payload_creations")
    launches = document.get("role_launches")
    credentials = document.get("child_credentials")
    reaps = document.get("role_reaps")
    closures = document.get("last_legal_reference_closures")
    barrier = document.get("native_cleanup_barrier")
    genesis = document.get("broker_session_genesis")
    session_nonce = document.get("session_nonce")
    expected_closures = list(sorted(PAYLOAD_SLOTS))
    if (
        type(session_nonce) is not str
        or re.fullmatch(r"[0-9a-f]{64}", session_nonce) is None
        or type(creations) is not list
        or [row.get("site_key") for row in creations] != list(SOURCE_SITE_ORDER)
        or type(launches) is not list
        or [row.get("role") for row in launches] != list(ROLE_ORDER)
        or type(credentials) is not list
        or [row.get("role") for row in credentials] != list(ROLE_ORDER)
        or type(reaps) is not list
        or [row.get("role") for row in reaps] != list(ROLE_ORDER)
        or type(closures) is not list
        or [
            (
                row.get("normal_ordinal"),
                row.get("source_normal_ordinal"),
                row.get("site_key"),
                row.get("role"),
            )
            for row in closures
        ]
        != expected_closures
        or type(barrier) is not dict
        or type(genesis) is not dict
        or barrier.get("completed_normal_ordinals") != list(range(41, 53))
        or barrier.get("session_nonce") != session_nonce
        or barrier.get("authority_disposition") != "BROKER_EXCLUSIVE_PRESENT"
        or barrier.get("prebound_output_continuation_context_id")
        != prebound_output_continuation_context_id
        or barrier.get("normal_ordinal_41_to_52_success_events_issued") is not True
        or barrier.get("native_cleanup_complete") is not True
        or barrier.get("output_ordinal_53_prerequisite_satisfied") is not True
        or barrier.get("output_ordinals_53_to_62_authorized") is not False
    ):
        _fail("exclusive broker completion topology changed")
    _verify_content_object(
        genesis,
        id_name="h1_exclusive_broker_session_genesis_id",
        domain=domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_SESSION_GENESIS_V1_DOMAIN,
    )
    if (
        genesis.get("session_nonce") != session_nonce
        or genesis.get("h1_exclusive_broker_profile_id") != profile_id
        or genesis.get("h1_exclusive_broker_source_manifest_id") != source_manifest_id
        or genesis.get("prebound_output_continuation_context_id")
        != prebound_output_continuation_context_id
        or genesis.get("test_crash_point") != "NONE"
        or genesis.get("fresh_exec_observed") is not True
        or genesis.get("dumpable_zero") is not True
        or genesis.get("no_new_privs") is not True
        or genesis.get("zero_effective_capabilities") is not True
        or type(genesis.get("interpreter_execution_identity")) is not dict
        or genesis["interpreter_execution_identity"].get(
            "hash_and_execveat_use_same_fd"
        )
        is not True
    ):
        _fail("exclusive broker genesis identity chain changed")
    role_by_site = {site: role for _cleanup, _normal, site, role in PAYLOAD_SLOTS}
    for row in creations:
        _verify_content_object(
            row,
            id_name="h1_exclusive_payload_creation_id",
            domain=domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_PAYLOAD_CREATION_V1_DOMAIN,
        )
        if (
            (row["source_device"], row["source_inode"])
            == (row["target_device"], row["target_inode"])
            or row.get("session_nonce") != session_nonce
            or row.get("role") != role_by_site[row["site_key"]]
            or row.get("required_seals") != REQUIRED_MEMFD_SEALS
            or row.get("observed_seals") & REQUIRED_MEMFD_SEALS
            != REQUIRED_MEMFD_SEALS
            or row.get("new_target_inode") is not True
            or row.get("source_ofd_not_adopted") is not True
            or row.get("creator_rw_ofd_closed") is not True
            or row.get("target_readonly_ofd_created") is not True
        ):
            _fail("exclusive target creation did not separate source and target")
    for role, launch, credential, reap in zip(
        ROLE_ORDER, launches, credentials, reaps
    ):
        _verify_content_object(
            launch,
            id_name="h1_exclusive_role_launch_edge_id",
            domain=domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_ROLE_LAUNCH_EDGE_V1_DOMAIN,
        )
        _verify_content_object(
            credential,
            id_name="h1_exclusive_child_credential_id",
            domain=domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_CHILD_CREDENTIAL_V1_DOMAIN,
        )
        _verify_content_object(
            reap,
            id_name="h1_exclusive_role_reap_id",
            domain=domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_ROLE_REAP_V1_DOMAIN,
        )
        pid = launch.get("pid")
        if (
            launch.get("session_nonce") != session_nonce
            or credential.get("session_nonce") != session_nonce
            or reap.get("session_nonce") != session_nonce
            or launch.get("role") != role
            or credential.get("role") != role
            or reap.get("role") != role
            or type(pid) is not int
            or pid <= 0
            or credential.get("pid") != pid
            or reap.get("pid") != pid
            or launch.get("pidfd_fdinfo_pid") != pid
            or credential.get("pidfd_fdinfo_pid") != pid
            or credential.get("postexec_dumpable_zero") is not True
            or credential.get("postexec_no_new_privs") is not True
            or reap.get("pidfd_waitid_preobserved") is not True
            or reap.get("pidfd_waitid_consumed") is not True
            or reap.get("channel_eof_observed") is not True
            or reap.get("queued_scm_rights_drained") is not True
            or reap.get("cgroup_empty_verified") is not True
        ):
            _fail("exclusive role launch, credential or reap chain changed")
    for row in closures:
        _verify_content_object(
            row,
            id_name="h1_last_legal_reference_closure_id",
            domain=domains_v10.CONSTRUCTION_K7_H1_LAST_LEGAL_REFERENCE_CLOSURE_V1_DOMAIN,
        )
        if (
            row.get("authority_disposition") != "BROKER_EXCLUSIVE_PRESENT"
            or row.get("session_nonce") != session_nonce
            or row.get("both_roles_reaped") is not True
            or row.get("both_role_channels_eof_and_rights_drained") is not True
            or row.get("both_role_cgroups_empty") is not True
            or row.get("master_closed") is not True
            or row.get("anchor_closed") is not True
            or row.get("last_legal_reference_closed") is not True
            or row.get("global_kernel_reference_count_observed") is not False
            or row.get("mount_resource_release_proven") is not False
        ):
            _fail("last-legal-reference claim widened")
    _verify_content_object(
        barrier,
        id_name="h1_native_cleanup_barrier_id",
        domain=domains_v10.CONSTRUCTION_K7_H1_NATIVE_CLEANUP_BARRIER_V1_DOMAIN,
    )
    if (
        barrier.get("last_legal_reference_closure_ids")
        != [row["h1_last_legal_reference_closure_id"] for row in closures]
        or barrier.get("ordinal_41_event")
        != {
            "normal_ordinal": 41,
            "effect": "EXACT_ROLE_REAPS_COMPLETE",
            "role_reap_ids": [row["h1_exclusive_role_reap_id"] for row in reaps],
            "success": True,
        }
        or type(barrier.get("ordinal_42_event")) is not dict
        or barrier["ordinal_42_event"].get("normal_ordinal") != 42
        or barrier["ordinal_42_event"].get("effect")
        != "RETAINED_ROLE_CGROUP_PEAK_READ"
        or barrier["ordinal_42_event"].get("success") is not True
        or type(barrier["ordinal_42_event"].get("peak_working_bytes")) is not int
        or barrier["ordinal_42_event"]["peak_working_bytes"] < 0
    ):
        _fail("exclusive cleanup barrier did not bind exact evidence")


def _get_subreaper() -> int:
    current = ctypes.c_int(-1)
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(PR_GET_CHILD_SUBREAPER, ctypes.byref(current), 0, 0, 0) == -1:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return int(current.value)


def _set_subreaper(enabled: int) -> int:
    current = _get_subreaper()
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(PR_SET_CHILD_SUBREAPER, enabled, 0, 0, 0) == -1:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    if _get_subreaper() != enabled:
        raise RuntimeError("child-subreaper state did not change exactly")
    return current


def _restore_signal_mask(expected: set[signal.Signals]) -> None:
    signal.pthread_sigmask(signal.SIG_SETMASK, expected)
    observed = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    if observed != expected:
        raise RuntimeError("supervisor signal mask restoration was not exact")


def _restore_subreaper(expected: int) -> None:
    _set_subreaper(expected)
    if _get_subreaper() != expected:
        raise RuntimeError("supervisor child-subreaper restoration was not exact")


def _crash_cleanup_is_complete(
    *,
    broker_launched: bool,
    broker_pidfd_reap_confirmed: bool,
    role_cleanup: Mapping[str, bool],
    cgroup_empty: Mapping[str, bool],
) -> bool:
    return (
        (not broker_launched or broker_pidfd_reap_confirmed)
        and set(role_cleanup) == set(ROLE_ORDER)
        and set(cgroup_empty) == set(ROLE_ORDER)
        and all(role_cleanup.values())
        and all(cgroup_empty.values())
    )


def _wait_direct_process(process: subprocess.Popen[bytes], pidfd: int, deadline: float) -> int:
    poller = select.poll()
    poller.register(pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)
    remaining = deadline - time.monotonic()
    if remaining <= 0 or not poller.poll(max(1, int(remaining * 1000))):
        raise TimeoutError("fresh-exec broker did not terminate")
    observed = os.waitid(_P_PIDFD, pidfd, os.WEXITED | os.WNOWAIT)
    consumed = os.waitid(_P_PIDFD, pidfd, os.WEXITED)
    if observed.si_pid != process.pid or consumed.si_pid != process.pid:
        raise RuntimeError("fresh-exec broker pidfd reap changed PID")
    if consumed.si_code == os.CLD_EXITED:
        process.returncode = int(consumed.si_status)
    else:
        process.returncode = -int(consumed.si_status)
    return process.returncode


def _kill_pidfd(pidfd: int) -> None:
    try:
        _pidfd_send_signal(pidfd, signal.SIGKILL)
    except (AttributeError, OSError, ProcessLookupError):
        pass


def _cleanup_reparented_role(pid: int, escrow_pidfd: int | None, deadline: float) -> bool:
    if pid <= 0:
        return True
    descriptor = escrow_pidfd
    owned = False
    if descriptor is None:
        try:
            descriptor = _pidfd_open(pid)
            owned = True
        except OSError:
            descriptor = None
    if descriptor is not None:
        _kill_pidfd(descriptor)
    try:
        while time.monotonic() < deadline:
            try:
                waited_pid, _status = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                return True
            if waited_pid == pid:
                return True
            time.sleep(0.005)
    finally:
        if owned and descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
    return False


def run_h1_exclusive_native_resource_broker_v1(
    *,
    source_payloads: Mapping[str, bytes],
    worker_cgroup_fd: int | None = None,
    business_cgroup_fd: int | None = None,
    prebound_output_continuation_context_id: str | None = None,
    deadline_milliseconds: int = 30_000,
    crash_point: H1ExclusiveBrokerCrashPointV1 = H1ExclusiveBrokerCrashPointV1.NONE,
) -> H1ExclusiveBrokerUnavailableV1 | H1ExclusiveBrokerCrashClosureV1 | H1ExclusiveBrokerCompletionV1:
    """Run one exclusive E3 broker attempt or fail without a success alias.

    The caller must supply two distinct, empty, preconfigured cgroup-v2 leaf
    directory FDs with ``pids.max=1`` and zero descendant limits.  This
    function never creates a synthetic cgroup and never treats an ordinary
    directory as a positive fixture.
    """

    prebound_output_continuation_context = (
        _normalize_prebound_output_continuation_context_id(
            prebound_output_continuation_context_id
        )
    )
    sources = _validate_sources(source_payloads)
    if (
        type(deadline_milliseconds) is not int
        or not 1 <= deadline_milliseconds <= MAX_DEADLINE_MILLISECONDS
        or type(crash_point) is not H1ExclusiveBrokerCrashPointV1
    ):
        _fail("exclusive broker deadline or crash point is invalid")
    facts, blocker = _probe_prerequisites(worker_cgroup_fd, business_cgroup_fd)
    if blocker is not None:
        return H1ExclusiveBrokerUnavailableV1(_RESULT_ISSUER, blocker, facts)
    assert worker_cgroup_fd is not None and business_cgroup_fd is not None
    profile = official_h1_exclusive_broker_profile_v1()
    source_manifest = official_h1_exclusive_broker_source_manifest_v1()
    source_manifest_document = source_manifest.to_document()
    session_nonce = os.urandom(32).hex()
    deadline = time.monotonic() + deadline_milliseconds / 1000
    parent_endpoint: socket.socket | None = None
    child_endpoint: socket.socket | None = None
    process: subprocess.Popen[bytes] | None = None
    broker_pidfd = -1
    code_fd = launch_journal_fd = -1
    launch_map: mmap.mmap | None = None
    cgroup_duplicates: list[int] = []
    source_fds: list[int] = []
    escrow: dict[str, int] = {}
    role_pids: dict[str, int] = {}
    old_subreaper = 0
    subreaper_changed = False
    previous_mask: set[signal.Signals] | None = None
    broker_launched = False
    broker_exit_status: int | None = None
    broker_pidfd_reap_confirmed = False
    failure_stage = "PRELAUNCH"

    def restore_supervisor_controls() -> None:
        nonlocal previous_mask, subreaper_changed
        errors: list[BaseException] = []
        if previous_mask is not None:
            try:
                _restore_signal_mask(previous_mask)
                previous_mask = None
            except BaseException as error:
                errors.append(error)
        if subreaper_changed:
            try:
                _restore_subreaper(old_subreaper)
                subreaper_changed = False
            except BaseException as error:
                errors.append(error)
        if errors:
            raise RuntimeError(
                "supervisor signal-mask or subreaper restoration failed"
            ) from errors[0]

    with tempfile.TemporaryDirectory(prefix="acfqp-h1-e3-exclusive-") as sandbox:
        try:
            source_path = Path(__file__).resolve()
            source_code = source_path.read_bytes()
            if (
                _sha(source_code) != source_manifest_document["source_sha256"]
                or len(source_code) != source_manifest_document["source_byte_count"]
            ):
                _fail("exclusive broker source changed after manifest freeze")
            supervisor_executable_fd, supervisor_execution_identity = (
                _open_verified_current_executable(
                    source_manifest_document["interpreter_sha256"]
                )
            )
            try:
                if (
                    supervisor_execution_identity["byte_count"]
                    != source_manifest_document["interpreter_byte_count"]
                    or supervisor_execution_identity["device"]
                    != source_manifest_document["interpreter_device"]
                    or supervisor_execution_identity["inode"]
                    != source_manifest_document["interpreter_inode"]
                ):
                    _fail("exclusive broker interpreter identity changed after manifest freeze")
            finally:
                os.close(supervisor_executable_fd)
            code_fd = _create_sealed_memfd(source_code, "acfqp-e3-broker-source")
            launch_journal_fd = _memfd_create("acfqp-e3-launch-journal", _MFD_CLOEXEC)
            os.ftruncate(launch_journal_fd, 64)
            launch_map = mmap.mmap(launch_journal_fd, 64, access=mmap.ACCESS_WRITE)
            for index, (_site, raw) in enumerate(sources):
                source_fds.append(_create_sealed_memfd(raw, f"acfqp-e3-source-{index}"))
            cgroup_duplicates = [
                fcntl.fcntl(worker_cgroup_fd, _F_DUPFD_CLOEXEC, 3),
                fcntl.fcntl(business_cgroup_fd, _F_DUPFD_CLOEXEC, 3),
            ]
            parent_endpoint, child_endpoint = socket.socketpair(
                socket.AF_UNIX,
                socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC,
            )
            parent_endpoint.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            child_endpoint.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            old_subreaper = _set_subreaper(1)
            subreaper_changed = True
            blocked = set(signal.valid_signals()) - {signal.SIGKILL, signal.SIGSTOP}
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
            argv = (
                sys.executable,
                "-I",
                "-S",
                "-B",
                f"/proc/self/fd/{code_fd}",
                _CHILD_MODE,
                str(child_endpoint.fileno()),
                str(cgroup_duplicates[0]),
                str(cgroup_duplicates[1]),
                str(code_fd),
                str(launch_journal_fd),
                source_manifest_document["source_sha256"],
                source_manifest_document["interpreter_sha256"],
                session_nonce,
                profile.profile_id,
                source_manifest.manifest_id,
                _json_bytes(
                    {
                        "prebound_output_continuation_context_id": (
                            prebound_output_continuation_context
                        )
                    }
                ).decode("utf-8"),
                crash_point.value,
            )
            environment = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=sandbox,
                env=environment,
                close_fds=True,
                pass_fds=(
                    child_endpoint.fileno(),
                    *cgroup_duplicates,
                    code_fd,
                    launch_journal_fd,
                ),
                start_new_session=True,
            )
            broker_launched = True
            failure_stage = "BROKER_READY"
            child_endpoint.close()
            child_endpoint = None
            broker_pidfd = _pidfd_open(process.pid)
            ready, rights, credential = _recv_packet(
                parent_endpoint,
                deadline=deadline,
                expected_pid=process.pid,
                expected_rights=0,
            )
            if ready is not None and ready.get("kind") == "BROKER_FAILURE":
                raise RuntimeError(
                    "fresh-exec broker pre-READY failure: "
                    + str(ready.get("failure_message", "UNKNOWN"))
                )
            if (
                rights
                or ready is None
                or credential is None
                or ready.get("kind") != "BROKER_READY"
                or type(ready.get("genesis")) is not dict
            ):
                raise RuntimeError("fresh-exec broker READY is invalid")
            genesis = ready["genesis"]
            _verify_content_object(
                genesis,
                id_name="h1_exclusive_broker_session_genesis_id",
                domain=domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_SESSION_GENESIS_V1_DOMAIN,
            )
            _verify_prebound_output_continuation_echo(
                genesis.get("prebound_output_continuation_context_id"),
                prebound_output_continuation_context,
            )
            execution_identity = genesis.get("interpreter_execution_identity")
            base_broker_fds = {
                0,
                1,
                2,
                int(argv[6]),
                *cgroup_duplicates,
                execution_identity.get("fd", -1)
                if type(execution_identity) is dict
                else -1,
            }
            mapping_fds = genesis.get("launch_journal_mapping_fds")
            observed_broker_fds = genesis.get("fd_numbers")
            launch_journal_stat = os.fstat(launch_journal_fd)
            if (
                genesis.get("session_nonce") != session_nonce
                or genesis.get("broker_pid") != process.pid
                or genesis.get("broker_parent_pid") != os.getpid()
                or genesis.get("broker_source_sha256") != source_manifest_document["source_sha256"]
                or genesis.get("interpreter_sha256") != source_manifest_document["interpreter_sha256"]
                or genesis.get("h1_exclusive_broker_profile_id") != profile.profile_id
                or genesis.get("h1_exclusive_broker_source_manifest_id")
                != source_manifest.manifest_id
                or genesis.get("test_crash_point") != crash_point.value
                or genesis.get("fresh_exec_observed") is not True
                or type(execution_identity) is not dict
                or execution_identity.get("proc_path") != "/proc/self/exe"
                or execution_identity.get("sha256")
                != source_manifest_document["interpreter_sha256"]
                or execution_identity.get("byte_count")
                != source_manifest_document["interpreter_byte_count"]
                or execution_identity.get("device")
                != source_manifest_document["interpreter_device"]
                or execution_identity.get("inode")
                != source_manifest_document["interpreter_inode"]
                or execution_identity.get("hash_and_execveat_use_same_fd") is not True
                or type(execution_identity.get("fd")) is not int
                or execution_identity["fd"] < 3
                or type(mapping_fds) is not list
                or len(mapping_fds) > 1
                or any(type(value) is not int or value in base_broker_fds for value in mapping_fds)
                or type(observed_broker_fds) is not list
                or observed_broker_fds != sorted((*base_broker_fds, *mapping_fds))
                or genesis.get("launch_journal_identity")
                != {
                    "device": launch_journal_stat.st_dev,
                    "inode": launch_journal_stat.st_ino,
                    "size": launch_journal_stat.st_size,
                }
                or type(genesis.get("runtime_opened_fds_retired_before_ready")) is not list
                or any(
                    row.get("target") != "/dev/urandom"
                    or row.get("cloexec") is not True
                    for row in genesis.get("runtime_opened_fds_retired_before_ready", [])
                )
                or _fdinfo_pid(broker_pidfd) != process.pid
            ):
                raise RuntimeError("fresh-exec broker identity or FD inventory changed")
            failure_stage = "PROVISION"
            source_rows = [
                {
                    "site_key": site,
                    "sha256": _sha(raw),
                    "byte_count": len(raw),
                    "source_device": os.fstat(descriptor).st_dev,
                    "source_inode": os.fstat(descriptor).st_ino,
                }
                for (site, raw), descriptor in zip(sources, source_fds)
            ]
            _send_packet(
                parent_endpoint,
                {"kind": "PROVISION", "sources": source_rows},
                source_fds,
            )
            launch_rows: list[dict[str, Any]] = []
            reap_rows: list[dict[str, Any]] = []
            completion: dict[str, Any] | None = None
            while completion is None:
                message, received_rights, _broker_credential = _recv_packet(
                    parent_endpoint,
                    deadline=deadline,
                    expected_pid=process.pid,
                    expected_rights=(0, 1)
                    if len(launch_rows) == len(reap_rows) and len(launch_rows) < 2
                    else 0,
                )
                if message is None:
                    raise RuntimeError("broker closed before completion")
                kind = message.get("kind")
                if kind == "ROLE_LAUNCH":
                    if len(received_rights) != 1 or len(launch_rows) != len(reap_rows):
                        raise RuntimeError("role launch sequence changed")
                    launch = message.get("launch")
                    if type(launch) is not dict or launch.get("role") != ROLE_ORDER[len(launch_rows)]:
                        raise RuntimeError("role launch identity changed")
                    _verify_content_object(
                        launch,
                        id_name="h1_exclusive_role_launch_edge_id",
                        domain=domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_ROLE_LAUNCH_EDGE_V1_DOMAIN,
                    )
                    pidfd = received_rights[0]
                    if _fdinfo_pid(pidfd) != launch["pid"]:
                        os.close(pidfd)
                        raise RuntimeError("escrow pidfd crossed role launch PID")
                    role = launch["role"]
                    escrow[role] = pidfd
                    role_pids[role] = launch["pid"]
                    launch_rows.append(launch)
                    failure_stage = f"{role}_RUNNING"
                elif kind == "ROLE_REAP":
                    if received_rights or len(reap_rows) >= len(launch_rows):
                        raise RuntimeError("role reap sequence changed")
                    reap = message.get("reap")
                    if type(reap) is not dict or reap.get("role") != ROLE_ORDER[len(reap_rows)]:
                        raise RuntimeError("role reap identity changed")
                    _verify_content_object(
                        reap,
                        id_name="h1_exclusive_role_reap_id",
                        domain=domains_v10.CONSTRUCTION_K7_H1_EXCLUSIVE_ROLE_REAP_V1_DOMAIN,
                    )
                    reap_rows.append(reap)
                    failure_stage = f"{reap['role']}_REAPED"
                elif kind == "COMPLETE":
                    if received_rights or len(launch_rows) != 2 or len(reap_rows) != 2:
                        raise RuntimeError("completion arrived before both exact reaps")
                    candidate = message.get("completion")
                    if type(candidate) is not dict:
                        raise RuntimeError("completion payload is absent")
                    completion = candidate
                elif kind == "BROKER_FAILURE":
                    for descriptor in received_rights:
                        os.close(descriptor)
                    raise RuntimeError(
                        "fresh-exec broker reported failure: "
                        + str(message.get("failure_message", "UNKNOWN"))
                    )
                else:
                    for descriptor in received_rights:
                        os.close(descriptor)
                    raise RuntimeError("fresh-exec broker emitted an unknown message")
            failure_stage = "BROKER_REAP"
            eof, eof_rights, eof_credential = _recv_packet(
                parent_endpoint,
                deadline=deadline,
                expected_pid=process.pid,
                expected_rights=0,
                allow_eof=True,
            )
            if eof is not None or eof_rights or eof_credential is not None:
                raise RuntimeError("fresh-exec broker emitted bytes after completion")
            broker_exit_status = _wait_direct_process(process, broker_pidfd, deadline)
            broker_pidfd_reap_confirmed = True
            if broker_exit_status != 0:
                raise RuntimeError("fresh-exec broker exited nonzero after completion")
            assert completion is not None
            raw_completion = canonical_json_bytes(completion)
            result = H1ExclusiveBrokerCompletionV1(_RESULT_ISSUER, raw_completion)
            if (
                result.to_document()["session_nonce"] != session_nonce
                or result.to_document()["prebound_output_continuation_context_id"]
                != prebound_output_continuation_context
                or result.to_document()["h1_exclusive_broker_profile_id"]
                != profile.profile_id
                or result.to_document()["h1_exclusive_broker_source_manifest_id"]
                != source_manifest.manifest_id
                or result.to_document()["broker_session_genesis"] != genesis
                or result.to_document()["role_launches"] != launch_rows
                or result.to_document()["role_reaps"] != reap_rows
                or [
                    (row["site_key"], row["source_device"], row["source_inode"], row["source_sha256"], row["byte_count"])
                    for row in result.to_document()["payload_creations"]
                ]
                != [
                    (row["site_key"], row["source_device"], row["source_inode"], row["sha256"], row["byte_count"])
                    for row in source_rows
                ]
            ):
                raise RuntimeError("completion crossed supervisor-held source or launch evidence")
            restore_supervisor_controls()
            return result
        except BaseException as error:
            if not broker_launched:
                restore_supervisor_controls()
                raise ConstructionK7H1ExclusiveNativeResourceBrokerV1Error(
                    "exclusive broker failed before process launch"
                ) from error
            cleanup_deadline = (
                time.monotonic() + CLEANUP_TIMEOUT_MILLISECONDS / 1000
            )
            if broker_pidfd >= 0:
                _kill_pidfd(broker_pidfd)
            if process is not None and process.returncode is None and broker_pidfd >= 0:
                try:
                    broker_exit_status = _wait_direct_process(process, broker_pidfd, cleanup_deadline)
                    broker_pidfd_reap_confirmed = True
                except BaseException:
                    broker_exit_status = None
                    broker_pidfd_reap_confirmed = False
            elif process is not None and process.returncode is not None:
                broker_exit_status = process.returncode
                broker_pidfd_reap_confirmed = True
            shared_pids = {role: 0 for role in ROLE_ORDER}
            if launch_map is not None:
                for index, role in enumerate(ROLE_ORDER):
                    shared_pids[role] = struct.unpack_from("i", launch_map, index * 16)[0]
                    if shared_pids[role] > 0:
                        role_pids.setdefault(role, shared_pids[role])
            role_cleanup = {
                role: _cleanup_reparented_role(
                    role_pids.get(role, 0),
                    escrow.get(role),
                    cleanup_deadline,
                )
                for role in ROLE_ORDER
            }
            cgroup_empty = {}
            for role, descriptor in zip(ROLE_ORDER, (worker_cgroup_fd, business_cgroup_fd)):
                try:
                    _wait_cgroup_empty(descriptor, cleanup_deadline)
                    cgroup_empty[role] = True
                except BaseException:
                    cgroup_empty[role] = False
            restore_supervisor_controls()
            crash_cleanup_complete = _crash_cleanup_is_complete(
                broker_launched=broker_launched,
                broker_pidfd_reap_confirmed=broker_pidfd_reap_confirmed,
                role_cleanup=role_cleanup,
                cgroup_empty=cgroup_empty,
            )
            payload = {
                "schema": "acfqp.k7_h1_exclusive_broker_crash_closure.v1",
                "schema_version": SCHEMA_VERSION,
                "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                "profile_key": PROFILE_KEY,
                "h1_exclusive_broker_profile_id": profile.profile_id,
                "h1_exclusive_broker_source_manifest_id": source_manifest.manifest_id,
                "session_nonce": session_nonce,
                "prebound_output_continuation_context_id": (
                    prebound_output_continuation_context
                ),
                "failure_stage": failure_stage,
                "failure_type": type(error).__name__,
                "failure_message": str(error)[:512],
                "execution_deadline_expired": isinstance(error, TimeoutError),
                "cleanup_window_milliseconds": CLEANUP_TIMEOUT_MILLISECONDS,
                "cleanup_window_independent_of_execution_deadline": True,
                "broker_launched": broker_launched,
                "broker_exit_status": broker_exit_status,
                "broker_pidfd_reap_confirmed": broker_pidfd_reap_confirmed,
                "shared_clone_parent_settid_pids": shared_pids,
                "escrow_roles": sorted(escrow),
                "role_cleanup_complete": role_cleanup,
                "role_cgroups_empty": cgroup_empty,
                "crash_cleanup_complete": crash_cleanup_complete,
                "supervisor_signal_mask_restored": previous_mask is None,
                "supervisor_subreaper_restored": not subreaper_changed,
                "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
                "terminal_code": "PROTOCOL_FAILURE",
                "broker_exclusive_present": False,
                "normal_ordinal_41_to_52_success_events_issued": False,
                "native_cleanup_barrier_issued": False,
                "output_ordinals_53_to_62_authorized": False,
                "formal_counter_records_issued": False,
                "formal_work_vector_issued": False,
                "formal_comparison_vector_issued": False,
                "official_execution_allowed": False,
            }
            return H1ExclusiveBrokerCrashClosureV1(
                _RESULT_ISSUER,
                canonical_json_bytes(payload),
            )
        finally:
            restoration_error: BaseException | None = None
            try:
                restore_supervisor_controls()
            except BaseException as error:
                restoration_error = error
            for descriptor in escrow.values():
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            for descriptor in (*source_fds, *cgroup_duplicates, code_fd, launch_journal_fd, broker_pidfd):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
            if launch_map is not None:
                try:
                    launch_map.close()
                except (BufferError, OSError):
                    pass
            for endpoint in (parent_endpoint, child_endpoint):
                if endpoint is not None:
                    try:
                        endpoint.close()
                    except OSError:
                        pass
            if restoration_error is not None:
                raise RuntimeError(
                    "exclusive broker could not restore supervisor controls"
                ) from restoration_error


if set(
    (
        _D_PROFILE,
        _D_SOURCE,
        _D_GENESIS,
        _D_PAYLOAD,
        _D_LAUNCH,
        _D_CREDENTIAL,
        _D_REAP,
        _D_CLOSE,
        _D_BARRIER,
        _D_COMPLETE,
        _D_CRASH,
        _D_UNAVAILABLE,
    )
) != set(domains_v10.K7_H1_DOMAIN_TAG_EXTENSION_V10):  # pragma: no cover
    raise RuntimeError("sealed broker source domains crossed V10 registry")


__all__ = (
    "ATOMIC_TWO_ROLE_CLONE3_PIDFD_PRESENT",
    "BROKER_CRASH_NONCERTIFICATE_PRESENT",
    "BROKER_EXCLUSIVE_PRESENT_AUTHORITY_PRESENT",
    "ConstructionK7H1ExclusiveNativeResourceBrokerV1Error",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORDS_ISSUED",
    "FORMAL_WORK_VECTOR_ISSUED",
    "FRESH_EXEC_EXCLUSIVE_BROKER_PRESENT",
    "H1ExclusiveBrokerCompletionV1",
    "H1ExclusiveBrokerCrashClosureV1",
    "H1ExclusiveBrokerCrashPointV1",
    "H1ExclusiveBrokerProfileV1",
    "H1ExclusiveBrokerSourceManifestV1",
    "H1ExclusiveBrokerUnavailableReasonV1",
    "H1ExclusiveBrokerUnavailableV1",
    "LAST_LEGAL_REFERENCE_CLOSE_AUTHORITY_PRESENT",
    "NORMAL_ORDINAL_41_TO_52_BARRIER_AUTHORITY_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OUTPUT_ORDINAL_53_TO_62_AUTHORITY_PRESENT",
    "PAYLOAD_SLOTS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "QUEUED_SCM_RIGHTS_DRAIN_PRESENT",
    "ROLE_CREDENTIAL_CGROUP_BINDING_PRESENT",
    "ROLE_ORDER",
    "ROLE_PAYLOAD_SITES",
    "SCHEMA_VERSION",
    "SOURCE_SITE_ORDER",
    "TARGET_OFD_CREATED_FROM_SOURCE_COPY",
    "V8_PRESENT_LIVE_UPGRADABLE",
    "WAITID_PIDFD_REAP_PRESENT",
    "official_h1_exclusive_broker_profile_v1",
    "official_h1_exclusive_broker_source_manifest_v1",
    "probe_h1_exclusive_native_resource_broker_v1",
    "run_h1_exclusive_native_resource_broker_v1",
)
