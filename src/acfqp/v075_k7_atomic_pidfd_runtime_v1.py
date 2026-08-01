"""Linux clone3/pidfd execution primitive for one V0-075 K7 cgroup lease.

This module is deliberately below the accounting/certificate layer.  It can
consume one real :class:`K7CgroupAttemptLeaseV1`, execute one identity-bound
sealed memfd program, and return parent-observed raw facts.  It never emits a
CounterRecord, WorkVector, ComparisonVector, projection proof, or terminal.

The lease is process-local, so transplanting it to a helper would destroy its
authority.  Consequently the direct ``clone3`` path is admitted only when
``/proc/self/task`` proves that the parent has exactly one thread.  There is no
``fork``/``Popen`` fallback and no test backend capable of minting a lease.
"""

from __future__ import annotations

import ctypes
from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import fcntl
import hashlib
import mmap
import os
import platform
import select
import signal
import socket
import stat
import struct
import sys
import threading
import time
from typing import Any, Mapping, NoReturn
import weakref

from acfqp import v075_k7_cgroup_lease_v1 as cgroup_lease
from acfqp import v075_k7_attempt_process_sink_v1 as attempt_process_sink
from acfqp.phase3e_ids import (
    V075_K7_ATOMIC_SUPERVISOR_RESOURCE_EVIDENCE_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v075_k7_atomic_pidfd_runtime_v1"

CLONE_PIDFD = 0x00001000
CLONE_INTO_CGROUP = 0x200000000
CLONE_CLEAR_SIGHAND = 0x100000000
REQUIRED_CLONE_FLAGS = CLONE_PIDFD | CLONE_CLEAR_SIGHAND | CLONE_INTO_CGROUP
AT_EMPTY_PATH = 0x1000
REQUIRED_MEMFD_SEALS = 0x0001 | 0x0002 | 0x0004 | 0x0008
MFD_CLOEXEC = 0x0001
MFD_ALLOW_SEALING = 0x0002
F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
F_SEAL_SEAL = 0x0001
F_SEAL_SHRINK = 0x0002
F_SEAL_GROW = 0x0004
F_SEAL_WRITE = 0x0008
F_SEAL_EXEC = 0x0020
P_PIDFD = getattr(os, "P_PIDFD", 3)
MAX_EXECUTABLE_BYTES = 128 * 1024 * 1024
MAX_SEALED_INPUT_BYTES = 128 * 1024 * 1024
MAX_SEALED_INPUT_COUNT = 16
MAX_CHILD_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_DEADLINE_MILLISECONDS = 12 * 60 * 60 * 1000
MIN_MEMORY_MAX_BYTES = 64 * 1024 * 1024
MAX_MEMORY_MAX_BYTES = 1 << 50
MAX_REAP_GRACE_MILLISECONDS = 10_000
MAX_ARGV_COUNT = 64
MAX_ARGV_ENV_BYTES = 1024 * 1024
SUCCESS_PATH_CGROUP_CONTROL_READS = 17
ALLOWED_BASE_ENV_KEYS = frozenset({"LANG", "LC_ALL", "TZ", "PYTHONHASHSEED"})
CHANNEL_ENV_KEY = "ACFQP_K7_PARENT_CHANNEL_FD"
INPUT_FDS_ENV_KEY = "ACFQP_K7_SEALED_INPUT_FDS"

COUNTER_RECORD_AUTHORIZED = False
WORK_VECTOR_AUTHORIZED = False
COMPARISON_VECTOR_AUTHORIZED = False
ACTUAL_PROJECTION_PROOF_AUTHORIZED = False
ATTEMPT_TERMINAL_AUTHORIZED = False
OFFICIAL_EXECUTION_ALLOWED = False

_SPEC_ISSUER = object()
_CAPABILITY_ISSUER = object()
_BLOCKED_ISSUER = object()
_RESULT_ISSUER = object()
_SUPERVISOR_EVIDENCE_ISSUER = object()
_CONSUMED_LOCK = threading.Lock()
_CONSUMED_LEASES: set[tuple[int, int, str]] = set()
_BOOTSTRAP_LOCK = threading.Lock()

LANDLOCK_CREATE_RULESET = 444
LANDLOCK_RESTRICT_SELF = 446
LANDLOCK_CREATE_RULESET_VERSION = 1
LANDLOCK_ACCESS_FS_WRITE_FILE = 1 << 1
LANDLOCK_ACCESS_FS_REMOVE_DIR = 1 << 4
LANDLOCK_ACCESS_FS_REMOVE_FILE = 1 << 5
LANDLOCK_ACCESS_FS_MAKE_CHAR = 1 << 6
LANDLOCK_ACCESS_FS_MAKE_DIR = 1 << 7
LANDLOCK_ACCESS_FS_MAKE_REG = 1 << 8
LANDLOCK_ACCESS_FS_MAKE_SOCK = 1 << 9
LANDLOCK_ACCESS_FS_MAKE_FIFO = 1 << 10
LANDLOCK_ACCESS_FS_MAKE_BLOCK = 1 << 11
LANDLOCK_ACCESS_FS_MAKE_SYM = 1 << 12
LANDLOCK_ACCESS_FS_REFER = 1 << 13
LANDLOCK_ACCESS_FS_TRUNCATE = 1 << 14
_LANDLOCK_ABI1_WRITE_MASK = (
    LANDLOCK_ACCESS_FS_WRITE_FILE
    | LANDLOCK_ACCESS_FS_REMOVE_DIR
    | LANDLOCK_ACCESS_FS_REMOVE_FILE
    | LANDLOCK_ACCESS_FS_MAKE_CHAR
    | LANDLOCK_ACCESS_FS_MAKE_DIR
    | LANDLOCK_ACCESS_FS_MAKE_REG
    | LANDLOCK_ACCESS_FS_MAKE_SOCK
    | LANDLOCK_ACCESS_FS_MAKE_FIFO
    | LANDLOCK_ACCESS_FS_MAKE_BLOCK
    | LANDLOCK_ACCESS_FS_MAKE_SYM
)

# Generated exactly from v075_k7_atomic_trampoline_x86_64.S.  The child side
# never returns into Python; the parent invokes it through PYFUNCTYPE so the
# GIL remains held across the final thread check and clone3 syscall.
_X86_64_TRAMPOLINE_BYTES = bytes.fromhex(
    "41544989fc498b3c2448c7c65800000048c7c0b30100000f054885c00f884b02"
    "00000f854502000048c7c09d00000048c7c70100000048c7c6090000004831d2"
    "4d31d24d31c00f054885c00f887c01000048c7c06e0000000f05493b4424280f"
    "857101000048c7c09d00000048c7c72600000048c7c6010000004831d24d31d2"
    "4d31c00f054885c00f885901000048c7c0be010000498b7c24304831f60f0548"
    "85c00f884801000048c7c09d00000048c7c71600000048c7c602000000498b54"
    "24384d31d24d31c00f054885c00f88260100004883ec0848c704240000000048"
    "c7c00e00000048c7c7020000004889e64831d249c7c2080000000f054883c408"
    "4885c00f88f900000048c7c021000000498b7c24104831f60f054885c00f88e8"
    "00000048c7c021000000498b7c241048c7c6010000000f054885c00f88d30000"
    "0048c7c021000000498b7c241048c7c6020000000f054885c00f88be0000004d"
    "31c04d31c9e8c70000004883f8100f85e70000004883ec0848c7042400000000"
    "48c7c042010000498b7c24084889e6498b5424184d8b54242049c7c000100000"
    "4d31c90f054883c4084989c149f7d949c7c00a000000e87600000048c7c77f00"
    "000048c7c0e70000000f050f0b49c7c001000000eb4e49c7c0020000004d31c9"
    "e84c000000eb7449c7c003000000eb3449c7c004000000eb2b49c7c005000000"
    "eb2249c7c006000000eb1949c7c007000000eb1049c7c008000000eb0749c7c0"
    "090000004989c149f7d9e802000000eb2a4883ec104c8904244c894c240848c7"
    "c001000000498b7c24404889e648c7c2100000000f054883c410c348c7c77e00"
    "000048c7c0e70000000f050f0b415cc3"
)
X86_64_TRAMPOLINE_SHA256 = (
    "b51d9aa3e58bfdf04d8e02babf5e17b3e320ba7a126f01fdfd07ed6642ec8489"
)
_TRAMPOLINE_MEMORY: mmap.mmap | None = None
_TRAMPOLINE_FUNCTION: Any = None

_AUDIT_ARCH_X86_64 = 0xC000003E
_SECCOMP_RET_KILL_PROCESS = 0x80000000
_SECCOMP_RET_ERRNO = 0x00050000
_SECCOMP_RET_ALLOW = 0x7FFF0000
_BPF_LD_W_ABS = 0x20
_BPF_JMP_JEQ_K = 0x15
_BPF_JMP_JSET_K = 0x45
_BPF_RET_K = 0x06
_SECCOMP_FCNTL_SYSCALL_X86_64 = 72
_SECCOMP_DENIED_FCNTL_COMMANDS = (
    8,     # F_SETOWN
    10,    # F_SETSIG
    15,    # F_SETOWN_EX
    1024,  # F_SETLEASE
    1026,  # F_NOTIFY
)
_SECCOMP_DENIED_X86_64_SYSCALLS = (
    16,   # ioctl
    29,   # shmget
    30,   # shmat
    31,   # shmctl
    41,   # socket
    42,   # connect
    43,   # accept
    44,   # sendto
    45,   # recvfrom
    46,   # sendmsg
    47,   # recvmsg
    49,   # bind
    50,   # listen
    53,   # socketpair
    56,   # clone
    57,   # fork
    58,   # vfork
    62,   # kill
    64,   # semget
    65,   # semop
    66,   # semctl
    67,   # shmdt
    68,   # msgget
    69,   # msgsnd
    70,   # msgrcv
    71,   # msgctl
    76,   # truncate
    77,   # ftruncate
    90,   # chmod
    91,   # fchmod
    92,   # chown
    93,   # fchown
    94,   # lchown
    101,  # ptrace
    129,  # rt_sigqueueinfo
    132,  # utime
    141,  # setpriority
    142,  # sched_setparam
    144,  # sched_setscheduler
    155,  # pivot_root
    157,  # prctl (prevents clearing PDEATHSIG)
    165,  # mount
    166,  # umount2
    188,  # setxattr
    189,  # lsetxattr
    190,  # fsetxattr
    197,  # removexattr
    198,  # lremovexattr
    199,  # fremovexattr
    200,  # tkill
    203,  # sched_setaffinity
    234,  # tgkill
    235,  # utimes
    248,  # add_key
    249,  # request_key
    250,  # keyctl
    251,  # ioprio_set
    256,  # migrate_pages
    260,  # fchownat
    261,  # futimesat
    268,  # fchmodat
    272,  # unshare
    279,  # move_pages
    280,  # utimensat
    288,  # accept4
    298,  # perf_event_open
    299,  # recvmmsg
    302,  # prlimit64
    307,  # sendmmsg
    297,  # rt_tgsigqueueinfo
    308,  # setns
    310,  # process_vm_readv
    311,  # process_vm_writev
    312,  # kcmp
    314,  # sched_setattr
    321,  # bpf
    323,  # userfaultfd
    424,  # pidfd_send_signal
    425,  # io_uring_setup
    426,  # io_uring_enter
    427,  # io_uring_register
    428,  # open_tree
    429,  # move_mount
    430,  # fsopen
    432,  # fsmount
    433,  # fspick
    434,  # pidfd_open
    435,  # clone3
    438,  # pidfd_getfd
    440,  # process_madvise
    452,  # fchmodat2
)


class V075K7AtomicPidfdRuntimeV1Error(RuntimeError):
    """The low-level runtime contract or an observed invariant failed."""


class V075K7AtomicPidfdCleanupV1Error(V075K7AtomicPidfdRuntimeV1Error):
    """A launched child could not be killed/reaped or its cgroup proven empty."""


class K7AtomicPidfdBlockerV1(str, Enum):
    NOT_LINUX = "NOT_LINUX"
    UNSUPPORTED_ARCHITECTURE = "UNSUPPORTED_ARCHITECTURE"
    MULTITHREADED_PARENT = "MULTITHREADED_PARENT"
    PROC_TASK_UNAVAILABLE = "PROC_TASK_UNAVAILABLE"
    CLONE3_UNAVAILABLE = "CLONE3_UNAVAILABLE"
    PIDFD_SEND_SIGNAL_UNAVAILABLE = "PIDFD_SEND_SIGNAL_UNAVAILABLE"
    EXECVEAT_UNAVAILABLE = "EXECVEAT_UNAVAILABLE"
    PIDFD_WAIT_UNAVAILABLE = "PIDFD_WAIT_UNAVAILABLE"
    LANDLOCK_UNAVAILABLE = "LANDLOCK_UNAVAILABLE"
    NATIVE_TRAMPOLINE_UNAVAILABLE = "NATIVE_TRAMPOLINE_UNAVAILABLE"
    SIGCHLD_DISPOSITION_UNSAFE = "SIGCHLD_DISPOSITION_UNSAFE"
    SIGNAL_MASK_UNAVAILABLE = "SIGNAL_MASK_UNAVAILABLE"
    STANDARD_FDS_UNAVAILABLE = "STANDARD_FDS_UNAVAILABLE"
    PRIVILEGED_PARENT = "PRIVILEGED_PARENT"
    CLONE3_REJECTED = "CLONE3_REJECTED"


class K7AtomicPidfdOutcomeV1(str, Enum):
    EXITED = "EXITED"
    SIGNALED = "SIGNALED"
    DEADLINE_KILLED = "DEADLINE_KILLED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    OUTPUT_CAP_KILLED = "OUTPUT_CAP_KILLED"
    OUTPUT_CAP_EXCEEDED = "OUTPUT_CAP_EXCEEDED"
    SETUP_FAILED = "SETUP_FAILED"


class K7AtomicPidfdSetupStageV1(int, Enum):
    READY_FOR_EXEC = 0
    PARENT_DEATH_SIGNAL = 1
    PARENT_IDENTITY_RACE = 2
    NO_NEW_PRIVILEGES = 3
    LANDLOCK_RESTRICTION = 4
    SECCOMP_RESTRICTION = 5
    SIGNAL_MASK_CLEAR = 6
    DUP_STDIN = 7
    DUP_STDOUT = 8
    DUP_STDERR = 9
    EXECVEAT = 10


def _fail(message: str) -> NoReturn:
    raise V075K7AtomicPidfdRuntimeV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7AtomicPidfdRuntimeV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _locks() -> dict[str, bool]:
    return {
        "counter_record_authorized": COUNTER_RECORD_AUTHORIZED,
        "work_vector_authorized": WORK_VECTOR_AUTHORIZED,
        "comparison_vector_authorized": COMPARISON_VECTOR_AUTHORIZED,
        "actual_projection_proof_authorized": ACTUAL_PROJECTION_PROOF_AUTHORIZED,
        "attempt_terminal_authorized": ATTEMPT_TERMINAL_AUTHORIZED,
        "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
    }


@dataclass(frozen=True, slots=True)
class _SyscallNumbers:
    clone3: int
    pidfd_send_signal: int
    execveat: int
    exit_group: int
    memfd_create: int


_SYSCALLS = {
    "x86_64": _SyscallNumbers(435, 424, 322, 231, 319),
    "amd64": _SyscallNumbers(435, 424, 322, 231, 319),
    "aarch64": _SyscallNumbers(435, 424, 281, 94, 279),
    "arm64": _SyscallNumbers(435, 424, 281, 94, 279),
}


class CloneArgsV1(ctypes.Structure):
    """The stable Linux ``struct clone_args`` through ``cgroup``."""

    _fields_ = [
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
    ]


class _NativeLaunchArgsV1(ctypes.Structure):
    _fields_ = [
        ("clone_args", ctypes.c_void_p),
        ("executable_fd", ctypes.c_long),
        ("null_fd", ctypes.c_long),
        ("argv", ctypes.c_void_p),
        ("envp", ctypes.c_void_p),
        ("expected_parent_pid", ctypes.c_long),
        ("landlock_ruleset_fd", ctypes.c_long),
        ("seccomp_program", ctypes.c_void_p),
        ("setup_status_fd", ctypes.c_long),
    ]


class _LandlockRulesetAttrV1(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _SockFilterV1(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_ushort),
        ("jt", ctypes.c_ubyte),
        ("jf", ctypes.c_ubyte),
        ("k", ctypes.c_uint32),
    ]


class _SockFprogV1(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ushort),
        ("filters", ctypes.POINTER(_SockFilterV1)),
    ]


_LIBC = ctypes.CDLL(None, use_errno=True)
_LIBC.syscall.restype = ctypes.c_long
_LIBC.dup2.argtypes = (ctypes.c_int, ctypes.c_int)
_LIBC.dup2.restype = ctypes.c_int


def _raw_syscall(number: int, *arguments: object) -> tuple[int, int]:
    ctypes.set_errno(0)
    result = int(_LIBC.syscall(ctypes.c_long(number), *arguments))
    return result, (ctypes.get_errno() if result == -1 else 0)


def _probe_syscall(number: int, arguments: tuple[object, ...]) -> tuple[bool, int]:
    result, error = _raw_syscall(number, *arguments)
    if result != -1:
        # Every probe uses deliberately invalid arguments and must not succeed.
        _fail("a non-mutating syscall probe unexpectedly succeeded")
    return error not in {errno.ENOSYS, errno.EPERM}, error


def _landlock_abi_version() -> int | None:
    result, error = _raw_syscall(
        LANDLOCK_CREATE_RULESET,
        0,
        0,
        LANDLOCK_CREATE_RULESET_VERSION,
    )
    if result >= 1:
        return result
    if error in {errno.ENOSYS, errno.EOPNOTSUPP, errno.EPERM, errno.EINVAL}:
        return None
    _fail(f"Landlock ABI probe failed with unexpected errno {error}")


def _native_trampoline_v1() -> Any:
    global _TRAMPOLINE_MEMORY, _TRAMPOLINE_FUNCTION
    if platform.machine().lower() not in {"x86_64", "amd64"}:
        _fail("the audited native trampoline is unavailable on this architecture")
    if hashlib.sha256(_X86_64_TRAMPOLINE_BYTES).hexdigest() != X86_64_TRAMPOLINE_SHA256:
        _fail("the embedded native trampoline digest changed")
    if _TRAMPOLINE_FUNCTION is not None:
        if (
            _TRAMPOLINE_MEMORY is None
            or _TRAMPOLINE_MEMORY[:] != _X86_64_TRAMPOLINE_BYTES
        ):
            _fail("mapped native trampoline bytes changed")
        return _TRAMPOLINE_FUNCTION
    memory = mmap.mmap(
        -1,
        len(_X86_64_TRAMPOLINE_BYTES),
        flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
        prot=mmap.PROT_READ | mmap.PROT_WRITE,
    )
    memory.write(_X86_64_TRAMPOLINE_BYTES)
    address = ctypes.addressof(ctypes.c_char.from_buffer(memory))
    _LIBC.mprotect.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int)
    _LIBC.mprotect.restype = ctypes.c_int
    if _LIBC.mprotect(
        ctypes.c_void_p(address),
        ctypes.c_size_t(len(_X86_64_TRAMPOLINE_BYTES)),
        mmap.PROT_READ | mmap.PROT_EXEC,
    ) != 0:
        error = ctypes.get_errno()
        memory.close()
        raise V075K7AtomicPidfdRuntimeV1Error(
            f"native trampoline W^X transition failed with errno {error}"
        )
    function_type = ctypes.PYFUNCTYPE(
        ctypes.c_long,
        ctypes.POINTER(_NativeLaunchArgsV1),
    )
    _TRAMPOLINE_MEMORY = memory
    _TRAMPOLINE_FUNCTION = function_type(address)
    return _TRAMPOLINE_FUNCTION


def _create_write_denial_landlock_ruleset_v1(abi_version: int) -> int:
    if type(abi_version) is not int or abi_version < 1:
        _fail("Landlock ruleset requires a supported ABI")
    mask = _LANDLOCK_ABI1_WRITE_MASK
    if abi_version >= 2:
        mask |= LANDLOCK_ACCESS_FS_REFER
    if abi_version >= 3:
        mask |= LANDLOCK_ACCESS_FS_TRUNCATE
    attribute = _LandlockRulesetAttrV1(mask)
    descriptor, error = _raw_syscall(
        LANDLOCK_CREATE_RULESET,
        ctypes.byref(attribute),
        ctypes.sizeof(attribute),
        0,
    )
    if descriptor < 0:
        raise V075K7AtomicPidfdRuntimeV1Error(
            f"Landlock write-denial ruleset creation failed with errno {error}"
        )
    os.set_inheritable(descriptor, False)
    return descriptor


def _seccomp_no_spawn_program_v1() -> tuple[Any, _SockFprogV1]:
    rows = [
        _SockFilterV1(_BPF_LD_W_ABS, 0, 0, 4),
        _SockFilterV1(_BPF_JMP_JEQ_K, 1, 0, _AUDIT_ARCH_X86_64),
        _SockFilterV1(_BPF_RET_K, 0, 0, _SECCOMP_RET_KILL_PROCESS),
        _SockFilterV1(_BPF_LD_W_ABS, 0, 0, 0),
        # AUDIT_ARCH_X86_64 also covers the x32 ABI. Reject its syscall bit
        # before matching native syscall numbers, otherwise nr|0x40000000
        # bypasses every exact deny row.
        _SockFilterV1(_BPF_JMP_JSET_K, 0, 1, 0x40000000),
        _SockFilterV1(_BPF_RET_K, 0, 0, _SECCOMP_RET_KILL_PROCESS),
    ]
    fcntl_argument_rows = [
        _SockFilterV1(_BPF_LD_W_ABS, 0, 0, 24),  # seccomp_data.args[1]
    ]
    for command in _SECCOMP_DENIED_FCNTL_COMMANDS:
        fcntl_argument_rows.extend(
            (
                _SockFilterV1(_BPF_JMP_JEQ_K, 0, 1, command),
                _SockFilterV1(
                    _BPF_RET_K,
                    0,
                    0,
                    _SECCOMP_RET_ERRNO | errno.EPERM,
                ),
            )
        )
    fcntl_argument_rows.append(_SockFilterV1(_BPF_LD_W_ABS, 0, 0, 0))
    rows.append(
        _SockFilterV1(
            _BPF_JMP_JEQ_K,
            0,
            len(fcntl_argument_rows),
            _SECCOMP_FCNTL_SYSCALL_X86_64,
        )
    )
    rows.extend(fcntl_argument_rows)
    for number in _SECCOMP_DENIED_X86_64_SYSCALLS:
        rows.extend(
            (
                _SockFilterV1(_BPF_JMP_JEQ_K, 0, 1, number),
                _SockFilterV1(
                    _BPF_RET_K,
                    0,
                    0,
                    _SECCOMP_RET_ERRNO | errno.EPERM,
                ),
            )
        )
    rows.append(_SockFilterV1(_BPF_RET_K, 0, 0, _SECCOMP_RET_ALLOW))
    array_type = _SockFilterV1 * len(rows)
    filters = array_type(*rows)
    program = _SockFprogV1(len(rows), filters)
    return filters, program


def _thread_count() -> int | None:
    try:
        names = os.listdir("/proc/self/task")
    except OSError:
        return None
    numeric = tuple(name for name in names if name.isdigit())
    return len(numeric) if numeric else None


def _pidfd_wait_available() -> bool:
    function = getattr(os, "waitid", None)
    if not callable(function):
        return False
    descriptor = -1
    try:
        descriptor = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        function(P_PIDFD, descriptor, os.WEXITED | os.WNOHANG)
    except OSError as error:
        # A recognized P_PIDFD rejects a live non-pidfd descriptor with EBADF.
        # An old kernel that does not recognize the idtype returns EINVAL.
        return error.errno == errno.EBADF
    except (TypeError, ValueError):
        return False
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return False


def _standard_fds_available() -> bool:
    try:
        for descriptor in (0, 1, 2):
            os.fstat(descriptor)
    except OSError:
        return False
    return True


def _signal_mask_available() -> bool:
    return callable(getattr(signal, "pthread_sigmask", None)) and callable(
        getattr(signal, "valid_signals", None)
    )


def _parent_privilege_status() -> tuple[
    tuple[int, int, int, int],
    tuple[int, int, int, int],
    tuple[int, ...],
    tuple[tuple[str, int], ...],
] | None:
    try:
        with open("/proc/self/status", "rb", buffering=0) as stream:
            raw = stream.read(256 * 1024 + 1)
    except OSError:
        return None
    if len(raw) > 256 * 1024:
        return None
    try:
        rows = raw.decode("ascii", errors="strict").splitlines()
    except UnicodeDecodeError:
        return None
    values: dict[str, str] = {}
    wanted = {"Uid", "Gid", "Groups", "CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"}
    for row in rows:
        if ":" not in row:
            continue
        key, value = row.split(":", 1)
        if key in wanted:
            if key in values:
                return None
            values[key] = value.strip()
    if set(values) != wanted:
        return None
    try:
        uid_values = tuple(int(value) for value in values["Uid"].split())
        gid_values = tuple(int(value) for value in values["Gid"].split())
        groups = tuple(int(value) for value in values["Groups"].split())
        capabilities = tuple(
            (name, int(values[name], 16))
            for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")
        )
    except ValueError:
        return None
    if len(uid_values) != 4 or len(gid_values) != 4 or not groups:
        return None
    uids = (uid_values[0], uid_values[1], uid_values[2], uid_values[3])
    gids = (gid_values[0], gid_values[1], gid_values[2], gid_values[3])
    return uids, gids, groups, capabilities


def _unprivileged_parent_verified(
    status: tuple[
        tuple[int, int, int, int],
        tuple[int, int, int, int],
        tuple[int, ...],
        tuple[tuple[str, int], ...],
    ] | None,
) -> bool:
    if status is None:
        return False
    uids, gids, groups, capabilities = status
    capability_map = dict(capabilities)
    return (
        all(value != 0 for value in (*uids, *gids, *groups))
        and all(
            capability_map[name] == 0
            for name in ("CapInh", "CapPrm", "CapEff", "CapAmb")
        )
    )


@dataclass(frozen=True, slots=True)
class K7AtomicPidfdCapabilityV1:
    _issuer: InitVar[object]
    architecture: str
    thread_count: int | None
    clone3_probe_errno: int | None
    pidfd_send_signal_probe_errno: int | None
    execveat_probe_errno: int | None
    landlock_abi_version: int | None
    parent_privilege_status: tuple[
        tuple[int, int, int, int],
        tuple[int, int, int, int],
        tuple[int, ...],
        tuple[tuple[str, int], ...],
    ] | None
    blockers: tuple[K7AtomicPidfdBlockerV1, ...]

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CAPABILITY_ISSUER:
            _fail("atomic pidfd capability is runtime-issued")

    @property
    def admitted(self) -> bool:
        return not self.blockers

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_atomic_pidfd_capability.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "architecture": self.architecture,
            "thread_count": self.thread_count,
            "clone3_probe_errno": self.clone3_probe_errno,
            "pidfd_send_signal_probe_errno": self.pidfd_send_signal_probe_errno,
            "execveat_probe_errno": self.execveat_probe_errno,
            "landlock_abi_version": self.landlock_abi_version,
            "parent_privilege_status": (
                None
                if self.parent_privilege_status is None
                else {
                    "uids": list(self.parent_privilege_status[0]),
                    "gids": list(self.parent_privilege_status[1]),
                    "supplementary_groups": list(self.parent_privilege_status[2]),
                    "capability_sets": {
                        name: f"{value:016x}"
                        for name, value in self.parent_privilege_status[3]
                    },
                }
            ),
            "unprivileged_parent_verified": _unprivileged_parent_verified(
                self.parent_privilege_status
            ),
            "pidfd_wait_present": _pidfd_wait_available(),
            "single_thread_required": True,
            "admitted": self.admitted,
            "blockers": [value.value for value in self.blockers],
            **_locks(),
        }


def probe_v075_k7_atomic_pidfd_capability_v1() -> K7AtomicPidfdCapabilityV1:
    architecture = platform.machine().lower()
    threads = _thread_count()
    blockers: list[K7AtomicPidfdBlockerV1] = []
    clone_error: int | None = None
    signal_error: int | None = None
    exec_error: int | None = None
    landlock_version: int | None = None
    privilege_status = _parent_privilege_status()
    if not sys.platform.startswith("linux"):
        blockers.append(K7AtomicPidfdBlockerV1.NOT_LINUX)
    numbers = _SYSCALLS.get(architecture)
    if numbers is None:
        blockers.append(K7AtomicPidfdBlockerV1.UNSUPPORTED_ARCHITECTURE)
    if threads is None:
        blockers.append(K7AtomicPidfdBlockerV1.PROC_TASK_UNAVAILABLE)
    elif threads != 1:
        blockers.append(K7AtomicPidfdBlockerV1.MULTITHREADED_PARENT)
    if not _pidfd_wait_available():
        blockers.append(K7AtomicPidfdBlockerV1.PIDFD_WAIT_UNAVAILABLE)
    if not _signal_mask_available():
        blockers.append(K7AtomicPidfdBlockerV1.SIGNAL_MASK_UNAVAILABLE)
    if not _standard_fds_available():
        blockers.append(K7AtomicPidfdBlockerV1.STANDARD_FDS_UNAVAILABLE)
    if not _unprivileged_parent_verified(privilege_status):
        blockers.append(K7AtomicPidfdBlockerV1.PRIVILEGED_PARENT)
    if architecture not in {"x86_64", "amd64"}:
        blockers.append(K7AtomicPidfdBlockerV1.NATIVE_TRAMPOLINE_UNAVAILABLE)
    if signal.getsignal(signal.SIGCHLD) is not signal.SIG_DFL:
        blockers.append(K7AtomicPidfdBlockerV1.SIGCHLD_DISPOSITION_UNSAFE)
    if sys.platform.startswith("linux") and numbers is not None:
        clone_ok, clone_error = _probe_syscall(numbers.clone3, (0, 0))
        signal_ok, signal_error = _probe_syscall(
            numbers.pidfd_send_signal, (-1, 0, 0, 0)
        )
        exec_ok, exec_error = _probe_syscall(
            numbers.execveat, (-1, ctypes.c_char_p(b""), 0, 0, AT_EMPTY_PATH)
        )
        if not clone_ok:
            blockers.append(K7AtomicPidfdBlockerV1.CLONE3_UNAVAILABLE)
        if not signal_ok:
            blockers.append(K7AtomicPidfdBlockerV1.PIDFD_SEND_SIGNAL_UNAVAILABLE)
        if not exec_ok:
            blockers.append(K7AtomicPidfdBlockerV1.EXECVEAT_UNAVAILABLE)
        landlock_version = _landlock_abi_version()
        if landlock_version is None:
            blockers.append(K7AtomicPidfdBlockerV1.LANDLOCK_UNAVAILABLE)
    return K7AtomicPidfdCapabilityV1(
        _CAPABILITY_ISSUER,
        architecture,
        threads,
        clone_error,
        signal_error,
        exec_error,
        landlock_version,
        privilege_status,
        tuple(dict.fromkeys(blockers)),
    )


def _read_fd(fd: int, cap: int, label: str) -> tuple[bytes, os.stat_result]:
    try:
        before = os.fstat(fd)
    except OSError as error:
        raise V075K7AtomicPidfdRuntimeV1Error(f"{label} cannot be inspected") from error
    if not stat.S_ISREG(before.st_mode) or before.st_size <= 0 or before.st_size > cap:
        _fail(f"{label} is not one bounded nonempty regular file")
    chunks: list[bytes] = []
    offset = 0
    while offset < before.st_size:
        chunk = os.pread(fd, min(1024 * 1024, before.st_size - offset), offset)
        if not chunk:
            _fail(f"{label} was truncated")
        chunks.append(chunk)
        offset += len(chunk)
    after = os.fstat(fd)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
    ):
        _fail(f"{label} changed while read")
    try:
        seals = fcntl.fcntl(fd, F_GET_SEALS)
    except OSError as error:
        raise V075K7AtomicPidfdRuntimeV1Error(f"{label} is not a sealed memfd") from error
    if seals & REQUIRED_MEMFD_SEALS != REQUIRED_MEMFD_SEALS:
        _fail(f"{label} lacks the complete immutable seal set")
    return b"".join(chunks), before


def _duplicate_cloexec(fd: int) -> int:
    duplicate = fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, 3)
    os.set_inheritable(duplicate, False)
    return duplicate


def _normalize_cloexec_fd(fd: int) -> int:
    if fd >= 3:
        os.set_inheritable(fd, False)
        return fd
    duplicate = _duplicate_cloexec(fd)
    os.close(fd)
    return duplicate


def _new_sealable_memfd(name: str) -> int:
    flags = MFD_CLOEXEC | MFD_ALLOW_SEALING
    if callable(getattr(os, "memfd_create", None)):
        return _normalize_cloexec_fd(os.memfd_create(name, flags))
    numbers = _SYSCALLS.get(platform.machine().lower())
    if numbers is None or not sys.platform.startswith("linux"):
        _fail("memfd_create is unavailable on this runtime")
    fd, error = _raw_syscall(
        numbers.memfd_create,
        ctypes.c_char_p(name.encode("ascii")),
        flags,
    )
    if fd == -1:
        raise V075K7AtomicPidfdRuntimeV1Error(
            f"memfd_create failed with errno {error}"
        )
    return _normalize_cloexec_fd(fd)


def _runtime_private_sealed_memfd(
    *,
    raw: bytes,
    name: str,
    mode: int,
) -> int:
    fd = _new_sealable_memfd(name)
    try:
        os.fchmod(fd, mode)
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                _fail("runtime-private memfd write made no progress")
            offset += written
        base_seals = F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE
        try:
            fcntl.fcntl(fd, F_ADD_SEALS, base_seals | F_SEAL_EXEC)
        except OSError as error:
            if error.errno != errno.EINVAL:
                raise
            fcntl.fcntl(fd, F_ADD_SEALS, base_seals)
        fcntl.fcntl(fd, F_ADD_SEALS, F_SEAL_SEAL)
        replayed, status = _read_fd(fd, len(raw), "runtime-private sealed memfd")
        if replayed != raw or stat.S_IMODE(status.st_mode) != mode:
            _fail("runtime-private sealed memfd identity changed")
        return fd
    except BaseException:
        os.close(fd)
        raise


def create_v075_k7_sealed_memfd_from_bytes_v1(
    *,
    raw: bytes,
    name: str,
    byte_cap: int = MAX_SEALED_INPUT_BYTES,
) -> int:
    """Create one caller-owned immutable memfd, including Python builds
    that do not expose :func:`os.memfd_create`.
    """

    if (
        type(raw) is not bytes
        or not raw
        or type(byte_cap) is not int
        or not 1 <= len(raw) <= byte_cap <= MAX_EXECUTABLE_BYTES
        or type(name) is not str
        or not 1 <= len(name) <= 249
        or "\x00" in name
        or "/" in name
        or any(ord(character) < 0x20 or ord(character) > 0x7E for character in name)
    ):
        _fail("sealed memfd source, name, or cap is invalid")
    fd = _new_sealable_memfd(name)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                _fail("sealed memfd write made no progress")
            offset += written
        fcntl.fcntl(fd, F_ADD_SEALS, REQUIRED_MEMFD_SEALS)
        replayed, _status = _read_fd(fd, byte_cap, "new sealed memfd")
        if replayed != raw:
            _fail("new sealed memfd changed during freeze")
        return fd
    except BaseException:
        os.close(fd)
        raise


@dataclass(frozen=True, slots=True)
class _K7SealedBootstrapRecordV1:
    owner_pid: int
    executable_fd: int
    input_fds: tuple[int, ...]
    argv: tuple[str, ...]
    environment: tuple[tuple[str, str], ...]
    executable_sha256: str
    input_sha256: tuple[str, ...]
    consumed: bool
    closed: bool


_BOOTSTRAP_RECORDS: weakref.WeakKeyDictionary[
    object, _K7SealedBootstrapRecordV1
] = weakref.WeakKeyDictionary()


class K7SealedBootstrapExecV1:
    """Process-local opaque ownership of one sealed executable and inputs."""

    __slots__ = ("__weakref__",)

    def __init__(
        self,
        issuer: object,
        executable_fd: int,
        input_fds: tuple[int, ...],
        argv: tuple[str, ...],
        environment: tuple[tuple[str, str], ...],
        executable_sha256: str,
        input_sha256: tuple[str, ...],
    ) -> None:
        if issuer is not _SPEC_ISSUER:
            _fail("sealed bootstrap exec is runtime-issued")
        record = _K7SealedBootstrapRecordV1(
            os.getpid(), executable_fd, input_fds, argv, environment,
            executable_sha256, input_sha256, False, False,
        )
        with _BOOTSTRAP_LOCK:
            if self in _BOOTSTRAP_RECORDS:  # pragma: no cover
                _fail("sealed bootstrap exec identity was already issued")
            _BOOTSTRAP_RECORDS[self] = record

    @staticmethod
    def _record(authority: "K7SealedBootstrapExecV1") -> _K7SealedBootstrapRecordV1:
        record = _BOOTSTRAP_RECORDS.get(authority)
        if record is None or os.getpid() != record.owner_pid:
            _fail("sealed bootstrap exec is unknown or crossed between processes")
        return record

    @property
    def consumed(self) -> bool:
        with _BOOTSTRAP_LOCK:
            return self._record(self).consumed

    @property
    def closed(self) -> bool:
        with _BOOTSTRAP_LOCK:
            return self._record(self).closed

    def _check(self) -> None:
        with _BOOTSTRAP_LOCK:
            if self._record(self).closed:
                _fail("sealed bootstrap exec is closed or crossed between processes")

    def _consume(self) -> tuple[int, tuple[int, ...], tuple[str, ...], tuple[tuple[str, str], ...]]:
        with _BOOTSTRAP_LOCK:
            record = self._record(self)
            if record.closed:
                _fail("sealed bootstrap exec is closed or crossed between processes")
            if record.consumed:
                _fail("sealed bootstrap exec was already consumed")
            executable, executable_status = _read_fd(
                record.executable_fd, MAX_EXECUTABLE_BYTES, "executable"
            )
            if (
                hashlib.sha256(executable).hexdigest() != record.executable_sha256
                or stat.S_IMODE(executable_status.st_mode) != 0o500
            ):
                _fail("sealed executable digest changed")
            for fd, digest in zip(record.input_fds, record.input_sha256):
                raw, input_status = _read_fd(
                    fd, MAX_SEALED_INPUT_BYTES, "sealed input"
                )
                if (
                    hashlib.sha256(raw).hexdigest() != digest
                    or stat.S_IMODE(input_status.st_mode) != 0o400
                ):
                    _fail("sealed input digest changed")
            _BOOTSTRAP_RECORDS[self] = _K7SealedBootstrapRecordV1(
                record.owner_pid,
                record.executable_fd,
                record.input_fds,
                record.argv,
                record.environment,
                record.executable_sha256,
                record.input_sha256,
                True,
                False,
            )
            return (
                record.executable_fd,
                record.input_fds,
                record.argv,
                record.environment,
            )

    def close(self) -> None:
        with _BOOTSTRAP_LOCK:
            record = self._record(self)
            if record.closed:
                return
            close_error: OSError | None = None
            for fd in (record.executable_fd, *record.input_fds):
                try:
                    os.close(fd)
                except OSError as error:
                    if close_error is None:
                        close_error = error
            _BOOTSTRAP_RECORDS[self] = _K7SealedBootstrapRecordV1(
                record.owner_pid,
                -1,
                (),
                (),
                (),
                "",
                (),
                record.consumed,
                True,
            )
            if close_error is not None:
                raise V075K7AtomicPidfdCleanupV1Error(
                    "sealed bootstrap exec descriptor cleanup failed"
                ) from close_error

    def __enter__(self) -> "K7SealedBootstrapExecV1":
        self._check()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def __reduce__(self):
        raise TypeError("sealed bootstrap exec is process-local and unpickleable")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("sealed bootstrap exec is process-local and unpickleable")


def freeze_v075_k7_sealed_bootstrap_exec_v1(
    *,
    executable_fd: int,
    executable_sha256: str,
    argv: tuple[str, ...],
    environment: Mapping[str, str],
    sealed_input_fds: tuple[int, ...] = (),
) -> K7SealedBootstrapExecV1:
    if type(executable_fd) is not int or executable_fd < 0:
        _fail("executable descriptor is invalid")
    if (
        type(executable_sha256) is not str
        or len(executable_sha256) != 64
        or any(c not in "0123456789abcdef" for c in executable_sha256)
    ):
        _fail("executable digest is not lowercase SHA-256")
    if type(argv) is not tuple or not argv or len(argv) > MAX_ARGV_COUNT or any(
        type(value) is not str or not value or "\x00" in value for value in argv
    ):
        _fail("bootstrap argv is not one exact nonempty string tuple")
    if type(environment) is not dict or any(
        type(key) is not str or not key or "=" in key or "\x00" in key
        or type(value) is not str or "\x00" in value
        for key, value in environment.items()
    ):
        _fail("bootstrap environment is not one exact string mapping")
    if CHANNEL_ENV_KEY in environment or INPUT_FDS_ENV_KEY in environment:
        _fail("bootstrap environment attempts to replace runtime-owned FD bindings")
    if not set(environment) <= ALLOWED_BASE_ENV_KEYS:
        _fail("bootstrap environment contains an unregistered key")
    encoded_size = sum(len(value.encode("utf-8")) + 1 for value in argv) + sum(
        len(key.encode("utf-8")) + len(value.encode("utf-8")) + 2
        for key, value in environment.items()
    )
    if encoded_size > MAX_ARGV_ENV_BYTES:
        _fail("bootstrap argv and environment exceed their byte cap")
    if (
        type(sealed_input_fds) is not tuple
        or len(sealed_input_fds) > MAX_SEALED_INPUT_COUNT
        or any(type(fd) is not int or fd < 0 for fd in sealed_input_fds)
    ):
        _fail("sealed input descriptors are invalid")
    if len(set(sealed_input_fds)) != len(sealed_input_fds) or executable_fd in sealed_input_fds:
        _fail("sealed descriptor roles overlap")

    owned: list[int] = []
    try:
        executable_raw, _ = _read_fd(executable_fd, MAX_EXECUTABLE_BYTES, "executable")
        if hashlib.sha256(executable_raw).hexdigest() != executable_sha256:
            _fail("sealed executable does not match its expected digest")
        # Never retain the caller's inode. Immutable contents do not prevent
        # the caller from changing mode metadata on another descriptor for the
        # same memfd after freeze.
        owned_executable = _runtime_private_sealed_memfd(
            raw=executable_raw,
            name="acfqp-k7-private-executable",
            mode=0o500,
        )
        owned.append(owned_executable)
        input_digests: list[str] = []
        owned_inputs: list[int] = []
        for fd in sealed_input_fds:
            raw, _ = _read_fd(fd, MAX_SEALED_INPUT_BYTES, "sealed input")
            duplicate = _runtime_private_sealed_memfd(
                raw=raw,
                name=f"acfqp-k7-private-input-{len(owned_inputs)}",
                mode=0o400,
            )
            owned.append(duplicate)
            owned_inputs.append(duplicate)
            input_digests.append(hashlib.sha256(raw).hexdigest())
        result = K7SealedBootstrapExecV1(
            _SPEC_ISSUER,
            owned_executable,
            tuple(owned_inputs),
            argv,
            tuple(sorted(environment.items())),
            executable_sha256,
            tuple(input_digests),
        )
        owned.clear()
        return result
    finally:
        for fd in owned:
            os.close(fd)


@dataclass(frozen=True, slots=True)
class K7AtomicPidfdCountersV1:
    process_launches: int
    pidfd_waits: int
    pidfd_signals: int
    socket_read_calls: int
    child_output_bytes: int
    captured_output_bytes: int
    cgroup_control_reads: int

    def __post_init__(self) -> None:
        if any(type(value) is not int or value < 0 for value in (
            self.process_launches, self.pidfd_waits, self.pidfd_signals,
            self.socket_read_calls, self.child_output_bytes,
            self.captured_output_bytes, self.cgroup_control_reads,
        )):
            _fail("raw runtime counter is invalid")
        if self.captured_output_bytes > self.child_output_bytes:
            _fail("captured child output exceeds total observed output")


@dataclass(frozen=True, slots=True)
class K7AtomicPidfdBlockedResultV1:
    _issuer: InitVar[object]
    blocker: K7AtomicPidfdBlockerV1
    syscall_errno: int | None
    lease_consumed: bool
    lease_closed: bool
    bootstrap_consumed: bool
    bootstrap_closed: bool
    child_launch_attempted: bool

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BLOCKED_ISSUER:
            _fail("atomic pidfd blocker is runtime-issued")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_atomic_pidfd_blocked_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "blocker": self.blocker.value,
            "syscall_errno": self.syscall_errno,
            "lease_consumed": self.lease_consumed,
            "lease_closed": self.lease_closed,
            "bootstrap_consumed": self.bootstrap_consumed,
            "bootstrap_closed": self.bootstrap_closed,
            "child_launch_attempted": self.child_launch_attempted,
            "attempt_terminal_issued": False,
            **_locks(),
        }


@dataclass(frozen=True, slots=True)
class K7AtomicSupervisorResourceEvidenceV1:
    """Runtime-issued lifecycle evidence for launch and final cgroup peak.

    Sequence numbers are allocated at the native supervisor call sites.  The
    object is not a CounterRecord: a route-bound semantic authority must still
    join it to the exact request, parent execution spec, V6 registry, and
    production measurement profile.
    """

    _issuer: InitVar[object]
    lease_id: str
    child_pid: int
    process_launch_sequence: int
    output_eof_sequence: int
    process_reap_sequence: int
    cgroup_empty_sequence: int
    descendant_scan_sequence: int
    final_memory_peak_sequence: int
    memory_controls_verified_sequence: int
    process_launches: int
    memory_peak_bytes: int
    memory_max_bytes: int
    output_eof_before_reap: bool
    cgroup_empty_verified: bool
    no_descendants_verified: bool
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SUPERVISOR_EVIDENCE_ISSUER:
            _fail("atomic supervisor resource evidence is runtime-issued")
        _cid(self.lease_id, "supervisor evidence lease")
        if (
            type(self.child_pid) is not int
            or self.child_pid <= 0
            or self.process_launches != 1
            or type(self.memory_peak_bytes) is not int
            or self.memory_peak_bytes < 0
            or type(self.memory_max_bytes) is not int
            or not MIN_MEMORY_MAX_BYTES
            <= self.memory_max_bytes
            <= MAX_MEMORY_MAX_BYTES
            or self.memory_peak_bytes > self.memory_max_bytes
            or type(self.output_eof_before_reap) is not bool
            or self.cgroup_empty_verified is not True
            or self.no_descendants_verified is not True
        ):
            _fail("atomic supervisor resource evidence facts are invalid")
        sequence_by_role = {
            "PROCESS_LAUNCH": self.process_launch_sequence,
            "OUTPUT_EOF": self.output_eof_sequence,
            "PROCESS_REAP": self.process_reap_sequence,
            "CGROUP_EMPTY": self.cgroup_empty_sequence,
            "DESCENDANT_SCAN": self.descendant_scan_sequence,
            "FINAL_MEMORY_PEAK": self.final_memory_peak_sequence,
            "MEMORY_CONTROLS_VERIFIED": self.memory_controls_verified_sequence,
        }
        if any(type(value) is not int for value in sequence_by_role.values()):
            _fail("atomic supervisor lifecycle sequence is mistyped")
        expected_order = (
            (
                "PROCESS_LAUNCH",
                "OUTPUT_EOF",
                "PROCESS_REAP",
                "CGROUP_EMPTY",
                "DESCENDANT_SCAN",
                "FINAL_MEMORY_PEAK",
                "MEMORY_CONTROLS_VERIFIED",
            )
            if self.output_eof_before_reap
            else (
                "PROCESS_LAUNCH",
                "PROCESS_REAP",
                "OUTPUT_EOF",
                "CGROUP_EMPTY",
                "DESCENDANT_SCAN",
                "FINAL_MEMORY_PEAK",
                "MEMORY_CONTROLS_VERIFIED",
            )
        )
        if tuple(sequence_by_role[role] for role in expected_order) != tuple(
            range(1, len(expected_order) + 1)
        ):
            _fail("atomic supervisor lifecycle order is incomplete or crossed")
        object.__setattr__(
            self,
            "_evidence_id",
            content_id(
                V075_K7_ATOMIC_SUPERVISOR_RESOURCE_EVIDENCE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_atomic_supervisor_resource_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "lease_id": self.lease_id,
            "child_pid": self.child_pid,
            "lifecycle_sequence": [
                {"role": role, "sequence": sequence}
                for role, sequence in sorted(
                    {
                        "PROCESS_LAUNCH": self.process_launch_sequence,
                        "OUTPUT_EOF": self.output_eof_sequence,
                        "PROCESS_REAP": self.process_reap_sequence,
                        "CGROUP_EMPTY": self.cgroup_empty_sequence,
                        "DESCENDANT_SCAN": self.descendant_scan_sequence,
                        "FINAL_MEMORY_PEAK": self.final_memory_peak_sequence,
                        "MEMORY_CONTROLS_VERIFIED": (
                            self.memory_controls_verified_sequence
                        ),
                    }.items(),
                    key=lambda row: row[1],
                )
            ],
            "process_launches": self.process_launches,
            "memory_peak_bytes": self.memory_peak_bytes,
            "memory_max_bytes": self.memory_max_bytes,
            "output_eof_before_reap": self.output_eof_before_reap,
            "cgroup_empty_verified": self.cgroup_empty_verified,
            "no_descendants_verified": self.no_descendants_verified,
            "runtime_issuer_owned": True,
            "counter_record_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def evidence_id(self) -> str:
        if content_id(
            V075_K7_ATOMIC_SUPERVISOR_RESOURCE_EVIDENCE_V1_DOMAIN,
            self._payload(),
        ) != self._evidence_id:
            _fail("atomic supervisor resource evidence changed after issuance")
        return self._evidence_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "atomic_supervisor_resource_evidence_id": self.evidence_id,
        }


@dataclass(frozen=True, slots=True)
class K7AtomicPidfdRunResultV1:
    _issuer: InitVar[object]
    lease_id: str
    child_pid: int
    outcome: K7AtomicPidfdOutcomeV1
    exit_code: int | None
    terminating_signal: int | None
    setup_succeeded: bool
    setup_failure_stage: K7AtomicPidfdSetupStageV1 | None
    setup_errno: int | None
    output: bytes = field(repr=False)
    output_truncated: bool
    output_eof_before_reap: bool
    deadline_milliseconds: int
    output_cap_bytes: int
    memory_max_bytes: int
    memory_peak_bytes: int
    cgroup_empty_verified: bool
    no_descendants_verified: bool
    supervisor_resource_evidence: K7AtomicSupervisorResourceEvidenceV1 = field(
        repr=False
    )
    elapsed_nanoseconds: int
    counters: K7AtomicPidfdCountersV1

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("atomic pidfd result is runtime-issued")
        if not self.cgroup_empty_verified or not self.no_descendants_verified:
            _fail("atomic pidfd result lacks final cgroup proof")
        if (
            type(self.setup_succeeded) is not bool
            or (self.setup_succeeded and (
                self.setup_failure_stage is not None or self.setup_errno is not None
            ))
            or (
                self.setup_failure_stage is not None
                and type(self.setup_failure_stage) is not K7AtomicPidfdSetupStageV1
            )
            or (self.setup_errno is not None and (
                type(self.setup_errno) is not int or self.setup_errno < 0
            ))
            or (
                self.outcome is K7AtomicPidfdOutcomeV1.SETUP_FAILED
                and (
                    self.setup_succeeded
                    or self.setup_failure_stage is None
                    or self.exit_code not in {126, 127}
                )
            )
            or (
                (self.setup_failure_stage is None)
                != (self.setup_errno is None)
            )
        ):
            _fail("atomic pidfd setup evidence is inconsistent")
        if (
            type(self.memory_max_bytes) is not int
            or not MIN_MEMORY_MAX_BYTES <= self.memory_max_bytes <= MAX_MEMORY_MAX_BYTES
            or type(self.deadline_milliseconds) is not int
            or not 1 <= self.deadline_milliseconds <= MAX_DEADLINE_MILLISECONDS
            or type(self.output_cap_bytes) is not int
            or not 1 <= self.output_cap_bytes <= MAX_CHILD_OUTPUT_BYTES
            or type(self.memory_peak_bytes) is not int
            or self.memory_peak_bytes < 0
        ):
            _fail("atomic pidfd memory evidence is invalid")
        if (
            type(self.output_eof_before_reap) is not bool
            or self.counters.captured_output_bytes != len(self.output)
            or self.output_truncated
            != (self.counters.child_output_bytes > len(self.output))
            or self.counters.process_launches != 1
            or self.counters.pidfd_waits != 1
            or self.counters.cgroup_control_reads
            != SUCCESS_PATH_CGROUP_CONTROL_READS
        ):
            _fail("atomic pidfd output counters disagree with captured bytes")
        evidence = self.supervisor_resource_evidence
        if (
            type(evidence) is not K7AtomicSupervisorResourceEvidenceV1
            or evidence.lease_id != self.lease_id
            or evidence.child_pid != self.child_pid
            or evidence.process_launches != self.counters.process_launches
            or evidence.memory_peak_bytes != self.memory_peak_bytes
            or evidence.memory_max_bytes != self.memory_max_bytes
            or evidence.output_eof_before_reap != self.output_eof_before_reap
            or evidence.cgroup_empty_verified != self.cgroup_empty_verified
            or evidence.no_descendants_verified != self.no_descendants_verified
        ):
            _fail("atomic supervisor evidence differs from the run result")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_atomic_pidfd_run_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "lease_id": self.lease_id,
            "child_pid": self.child_pid,
            "outcome": self.outcome.value,
            "exit_code": self.exit_code,
            "terminating_signal": self.terminating_signal,
            "setup_succeeded": self.setup_succeeded,
            "setup_failure_stage": (
                None if self.setup_failure_stage is None
                else self.setup_failure_stage.name
            ),
            "setup_errno": self.setup_errno,
            "output_byte_count": len(self.output),
            "output_sha256": hashlib.sha256(self.output).hexdigest(),
            "output_truncated": self.output_truncated,
            "output_eof_before_reap": self.output_eof_before_reap,
            "total_observed_output_byte_count": self.counters.child_output_bytes,
            "deadline_milliseconds": self.deadline_milliseconds,
            "output_cap_bytes": self.output_cap_bytes,
            "memory_max_bytes": self.memory_max_bytes,
            "memory_swap_max_bytes": 0,
            "memory_peak_bytes": self.memory_peak_bytes,
            "cgroup_empty_verified": self.cgroup_empty_verified,
            "no_descendants_verified": self.no_descendants_verified,
            "supervisor_resource_evidence": (
                self.supervisor_resource_evidence.to_document()
            ),
            "elapsed_nanoseconds": self.elapsed_nanoseconds,
            "raw_counters": {
                name: getattr(self.counters, name)
                for name in self.counters.__dataclass_fields__
            },
            "counter_record_issued": False,
            "attempt_terminal_issued": False,
            **_locks(),
        }


def _parse_cgroup_stat(raw: bytes) -> dict[str, int]:
    try:
        text = raw.decode("ascii", errors="strict")
    except UnicodeDecodeError as error:
        raise V075K7AtomicPidfdRuntimeV1Error("cgroup.stat is not ASCII") from error
    result: dict[str, int] = {}
    for row in text.splitlines():
        fields = row.split()
        if len(fields) != 2 or fields[0] in result or not fields[1].isdigit():
            _fail("cgroup.stat is malformed or duplicated")
        result[fields[0]] = int(fields[1])
    if not {"nr_descendants", "nr_dying_descendants"} <= result.keys():
        _fail("cgroup.stat lacks descendant counts")
    return result


def _assert_exact_inheritable_fds(allowed: set[int]) -> None:
    try:
        observed = {
            int(name)
            for name in os.listdir("/proc/self/fd")
            if name.isdigit() and os.path.exists(f"/proc/self/fd/{name}")
        }
    except OSError as error:
        raise V075K7AtomicPidfdRuntimeV1Error("cannot enumerate inherited descriptors") from error
    unexpected: list[int] = []
    for fd in observed:
        try:
            inheritable = os.get_inheritable(fd)
        except OSError:
            continue
        if inheritable and fd not in allowed:
            unexpected.append(fd)
    if unexpected:
        _fail(f"unexpected inheritable descriptors: {sorted(unexpected)}")


def _descriptor_identity(fd: int) -> tuple[int, int, int, int, int, int]:
    try:
        status = os.fstat(fd)
    except OSError as error:
        raise V075K7AtomicPidfdRuntimeV1Error(
            "atomic runtime descriptor role is no longer live"
        ) from error
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
        status.st_rdev,
    )


def _assert_descriptor_roles_current(
    *,
    descriptors: tuple[int, ...],
    identities: tuple[tuple[int, int, int, int, int, int], ...],
    required_inheritable: tuple[int, ...],
) -> None:
    if (
        len(descriptors) != len(identities)
        or tuple(_descriptor_identity(fd) for fd in descriptors) != identities
        or any(not os.get_inheritable(fd) for fd in required_inheritable)
    ):
        _fail("atomic runtime descriptor identity or inheritance changed")


def _send_pidfd_signal(numbers: _SyscallNumbers, pidfd: int, sig: int) -> None:
    result, error = _raw_syscall(numbers.pidfd_send_signal, pidfd, sig, 0, 0)
    if result == -1 and error != errno.ESRCH:
        raise OSError(error, os.strerror(error))


def _wait_pidfd(
    pidfd: int,
    *,
    grace_milliseconds: int = MAX_REAP_GRACE_MILLISECONDS,
) -> os.waitid_result:
    deadline_ns = time.monotonic_ns() + grace_milliseconds * 1_000_000
    poller = select.poll()
    poller.register(pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)
    while time.monotonic_ns() < deadline_ns:
        remaining_ms = max(
            1,
            min(100, (deadline_ns - time.monotonic_ns() + 999_999) // 1_000_000),
        )
        if not poller.poll(remaining_ms):
            continue
        try:
            waited = os.waitid(P_PIDFD, pidfd, os.WEXITED | os.WNOHANG)
        except OSError as error:
            raise V075K7AtomicPidfdCleanupV1Error("pidfd waitid failed") from error
        if waited is not None:
            return waited
    raise V075K7AtomicPidfdCleanupV1Error(
        "pidfd child did not become reapable within the cleanup grace"
    )


def _status(
    waited: os.waitid_result,
    forced_reason: str | None,
) -> tuple[K7AtomicPidfdOutcomeV1, int | None, int | None]:
    if forced_reason is not None:
        killed = (
            waited.si_code in {os.CLD_KILLED, os.CLD_DUMPED}
            and int(waited.si_status) == signal.SIGKILL
        )
        if forced_reason == "DEADLINE":
            outcome = (
                K7AtomicPidfdOutcomeV1.DEADLINE_KILLED
                if killed
                else K7AtomicPidfdOutcomeV1.DEADLINE_EXCEEDED
            )
        elif forced_reason == "OUTPUT_CAP":
            outcome = (
                K7AtomicPidfdOutcomeV1.OUTPUT_CAP_KILLED
                if killed
                else K7AtomicPidfdOutcomeV1.OUTPUT_CAP_EXCEEDED
            )
        else:  # pragma: no cover - internal closed enum
            _fail("unknown forced runtime reason")
        if waited.si_code == os.CLD_EXITED:
            return outcome, int(waited.si_status), None
        if waited.si_code in {os.CLD_KILLED, os.CLD_DUMPED}:
            return outcome, None, int(waited.si_status)
        _fail("forced pidfd wait returned an impossible child status")
    if waited.si_code == os.CLD_EXITED:
        return K7AtomicPidfdOutcomeV1.EXITED, int(waited.si_status), None
    if waited.si_code in {os.CLD_KILLED, os.CLD_DUMPED}:
        return K7AtomicPidfdOutcomeV1.SIGNALED, None, int(waited.si_status)
    _fail("pidfd wait returned an impossible child status")


def _read_setup_status(status_fd: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    deadline_ns = time.monotonic_ns() + 1_000_000_000
    poller = select.poll()
    poller.register(status_fd, select.POLLIN | select.POLLHUP | select.POLLERR)
    while time.monotonic_ns() < deadline_ns:
        remaining_ms = max(
            1,
            min(100, (deadline_ns - time.monotonic_ns() + 999_999) // 1_000_000),
        )
        if not poller.poll(remaining_ms):
            continue
        while True:
            try:
                chunk = os.read(status_fd, 33 - total)
            except BlockingIOError:
                break
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
            total += len(chunk)
            if total > 32:
                _fail("native setup status exceeded two fixed records")
    _fail("native setup status did not reach CLOEXEC/exit EOF")


def _parse_setup_status(
    raw: bytes,
) -> tuple[bool, K7AtomicPidfdSetupStageV1 | None, int | None]:
    if len(raw) not in {0, 16, 32}:
        _fail("native setup status has a partial record")
    if not raw:
        return False, None, None
    records = tuple(
        struct.unpack("<QQ", raw[offset: offset + 16])
        for offset in range(0, len(raw), 16)
    )
    try:
        stages = tuple(K7AtomicPidfdSetupStageV1(stage) for stage, _ in records)
    except ValueError as error:
        raise V075K7AtomicPidfdRuntimeV1Error(
            "native setup status contains an unknown stage"
        ) from error
    if records[0] == (K7AtomicPidfdSetupStageV1.READY_FOR_EXEC.value, 0):
        if len(records) == 1:
            return True, None, None
        if (
            len(records) == 2
            and stages[1] is K7AtomicPidfdSetupStageV1.EXECVEAT
            and records[1][1] > 0
        ):
            return False, stages[1], int(records[1][1])
        _fail("native setup status has an invalid post-ready record")
    if len(records) != 1 or stages[0] in {
        K7AtomicPidfdSetupStageV1.READY_FOR_EXEC,
        K7AtomicPidfdSetupStageV1.EXECVEAT,
    }:
        _fail("native setup status has an invalid pre-exec record sequence")
    return False, stages[0], int(records[0][1])


def _configure_leaf_runtime_controls(
    *,
    leaf_fd: int,
    memory_max_bytes: int,
) -> int:
    # memory.max bounds resident working memory; swap is disabled so it cannot
    # become an unrecorded second capacity channel.
    cgroup_lease._write_control(  # noqa: SLF001
        leaf_fd, "memory.max", str(memory_max_bytes)
    )
    cgroup_lease._write_control(leaf_fd, "memory.swap.max", "0")  # noqa: SLF001
    _verify_leaf_memory_controls(
        leaf_fd=leaf_fd,
        memory_max_bytes=memory_max_bytes,
    )
    kill_fd = -1
    try:
        flags = os.O_WRONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        kill_fd = os.open("cgroup.kill", flags, dir_fd=leaf_fd)
        if not stat.S_ISREG(os.fstat(kill_fd).st_mode):
            _fail("cgroup.kill is not one cgroup control file")
    except OSError as error:
        raise V075K7AtomicPidfdRuntimeV1Error(
            "attempt leaf lacks a writable cgroup.kill cleanup authority"
        ) from error
    finally:
        if kill_fd >= 0:
            os.close(kill_fd)
    return 2


def _verify_leaf_memory_controls(*, leaf_fd: int, memory_max_bytes: int) -> int:
    readbacks = {
        "memory.max": cgroup_lease._parse_ascii(  # noqa: SLF001
            cgroup_lease._read_control(leaf_fd, "memory.max"),  # noqa: SLF001
            "memory.max",
        ).strip(),
        "memory.swap.max": cgroup_lease._parse_ascii(  # noqa: SLF001
            cgroup_lease._read_control(leaf_fd, "memory.swap.max"),  # noqa: SLF001
            "memory.swap.max",
        ).strip(),
    }
    if readbacks != {
        "memory.max": str(memory_max_bytes),
        "memory.swap.max": "0",
    }:
        _fail("attempt leaf memory hard-cap readback changed")
    return 2


def _leaf_is_empty_and_descendant_free(leaf_fd: int) -> bool:
    try:
        cgroup_lease._validate_empty_leaf(leaf_fd)  # noqa: SLF001
        values = _parse_cgroup_stat(
            cgroup_lease._read_control(leaf_fd, "cgroup.stat")  # noqa: SLF001
        )
    except (OSError, V075K7AtomicPidfdRuntimeV1Error, cgroup_lease.V075K7CgroupLeaseV1Error):
        return False
    return values["nr_descendants"] == 0 and values["nr_dying_descendants"] == 0


def _kill_leaf_and_wait_empty(leaf_fd: int) -> None:
    if _leaf_is_empty_and_descendant_free(leaf_fd):
        return
    try:
        cgroup_lease._write_control(leaf_fd, "cgroup.kill", "1")  # noqa: SLF001
    except (OSError, cgroup_lease.V075K7CgroupLeaseV1Error) as error:
        raise V075K7AtomicPidfdCleanupV1Error(
            "atomic runtime could not invoke cgroup.kill"
        ) from error
    deadline_ns = time.monotonic_ns() + MAX_REAP_GRACE_MILLISECONDS * 1_000_000
    while time.monotonic_ns() < deadline_ns:
        if _leaf_is_empty_and_descendant_free(leaf_fd):
            return
        time.sleep(0.01)
    raise V075K7AtomicPidfdCleanupV1Error(
        "atomic runtime could not prove an empty descendant-free leaf after cgroup.kill"
    )


def _kill_and_reap_direct_child(child_pid: int) -> None:
    try:
        os.kill(child_pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    deadline_ns = time.monotonic_ns() + MAX_REAP_GRACE_MILLISECONDS * 1_000_000
    while time.monotonic_ns() < deadline_ns:
        try:
            waited_pid, _status_word = os.waitpid(child_pid, os.WNOHANG)
        except ChildProcessError:
            return
        if waited_pid == child_pid:
            return
        time.sleep(0.01)
    raise V075K7AtomicPidfdCleanupV1Error(
        "direct child could not be reaped without its required pidfd"
    )


def _claim_lease(
    lease: cgroup_lease.K7CgroupAttemptLeaseV1,
) -> tuple[str, tuple[int, int, str]]:
    if type(lease) is not cgroup_lease.K7CgroupAttemptLeaseV1:
        _fail("atomic runtime requires one exact cgroup lease authority")
    lease_id = lease.lease_id
    key = (os.getpid(), id(lease), lease_id)
    with _CONSUMED_LOCK:
        if key in _CONSUMED_LEASES:
            _fail("cgroup lease was already consumed by the atomic runtime")
        _CONSUMED_LEASES.add(key)
    return lease_id, key


def run_v075_k7_atomic_pidfd_runtime_v1(
    *,
    lease: cgroup_lease.K7CgroupAttemptLeaseV1,
    bootstrap: K7SealedBootstrapExecV1,
    deadline_milliseconds: int,
    memory_max_bytes: int,
    output_cap_bytes: int = MAX_CHILD_OUTPUT_BYTES,
) -> K7AtomicPidfdRunResultV1 | K7AtomicPidfdBlockedResultV1:
    """Run one child, or leave both inputs live on a preflight blocker.

    Once capability preflight succeeds, both authorities are consumed and
    closed on every return or exception path.
    """

    if type(lease) is not cgroup_lease.K7CgroupAttemptLeaseV1:
        _fail("atomic runtime requires one exact cgroup lease authority")
    if type(bootstrap) is not K7SealedBootstrapExecV1:
        _fail("atomic runtime requires one exact sealed bootstrap authority")
    if type(deadline_milliseconds) is not int or not 1 <= deadline_milliseconds <= MAX_DEADLINE_MILLISECONDS:
        _fail("deadline is outside the frozen positive bound")
    if type(output_cap_bytes) is not int or not 1 <= output_cap_bytes <= MAX_CHILD_OUTPUT_BYTES:
        _fail("output cap is outside the frozen positive bound")
    if (
        type(memory_max_bytes) is not int
        or not MIN_MEMORY_MAX_BYTES <= memory_max_bytes <= MAX_MEMORY_MAX_BYTES
    ):
        _fail("memory hard cap is outside the frozen positive bound")

    capability = probe_v075_k7_atomic_pidfd_capability_v1()
    if not capability.admitted:
        return K7AtomicPidfdBlockedResultV1(
            _BLOCKED_ISSUER,
            capability.blockers[0],
            None,
            False,
            False,
            False,
            False,
            False,
        )
    numbers = _SYSCALLS[capability.architecture]
    lease_id = ""
    claimed_lease_key: tuple[int, int, str] | None = None
    leaf_fd = -1
    executable_fd = -1
    input_fds: tuple[int, ...] = ()
    argv: tuple[str, ...] = ()
    base_environment: tuple[tuple[str, str], ...] = ()
    parent_socket: socket.socket | None = None
    child_socket: socket.socket | None = None
    setup_status_read_fd = -1
    setup_status_write_fd = -1
    null_fd = -1
    landlock_ruleset_fd = -1
    pidfd = -1
    child_pid = -1
    waited: os.waitid_result | None = None
    forced_reason: str | None = None
    signal_count = 0
    socket_reads = 0
    total_output_bytes = 0
    output = bytearray()
    start_ns = time.monotonic_ns()
    lease_closed = False
    reads = 0
    lifecycle_roles: list[str] = []

    def record_lifecycle(role: str) -> None:
        if role in lifecycle_roles:
            _fail("atomic supervisor lifecycle role was recorded twice")
        lifecycle_roles.append(role)

    def wait_and_record_reap() -> os.waitid_result:
        observed_wait = _wait_pidfd(pidfd)
        record_lifecycle("PROCESS_REAP")
        return observed_wait

    previous_signal_mask: set[signal.Signals] | None = None
    signals_blocked = False
    try:
        # Freeze the parent signal surface before any consumed authority or
        # launch argument can be changed by a pre-existing Python/C handler.
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        blocked_signals = set(signal.valid_signals()) - {
            signal.SIGKILL,
            signal.SIGSTOP,
        }
        previous_signal_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK,
            blocked_signals,
        )
        signals_blocked = True
        lease_id, claimed_lease_key = _claim_lease(lease)
        leaf_fd = lease.leaf_fd
        executable_fd, input_fds, argv, base_environment = (  # noqa: SLF001
            bootstrap._consume()
        )
        reads += _configure_leaf_runtime_controls(
            leaf_fd=leaf_fd,
            memory_max_bytes=memory_max_bytes,
        )
        if capability.landlock_abi_version is None:  # pragma: no cover
            _fail("admitted capability lost its Landlock ABI")
        landlock_ruleset_fd = _create_write_denial_landlock_ruleset_v1(
            capability.landlock_abi_version
        )
        parent_socket, child_socket = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM | socket.SOCK_CLOEXEC)
        parent_socket.setblocking(False)
        child_socket.setblocking(True)
        setup_status_read_fd, setup_status_write_fd = os.pipe2(os.O_CLOEXEC)
        os.set_blocking(setup_status_read_fd, False)
        null_fd = os.open("/dev/null", os.O_RDWR | os.O_CLOEXEC)
        child_fd = child_socket.fileno()
        descriptor_roles = (
            executable_fd,
            *input_fds,
            parent_socket.fileno(),
            child_fd,
            setup_status_read_fd,
            setup_status_write_fd,
            null_fd,
            landlock_ruleset_fd,
            leaf_fd,
        )
        if min(descriptor_roles) < 3 or len(set(descriptor_roles)) != len(descriptor_roles):
            _fail("atomic runtime descriptor roles overlap or use standard streams")
        inherited = (executable_fd, *input_fds, child_fd)
        for fd in inherited:
            os.set_inheritable(fd, True)
        descriptor_identities = tuple(
            _descriptor_identity(fd) for fd in descriptor_roles
        )

        environment = dict(base_environment)
        environment[CHANNEL_ENV_KEY] = str(child_fd)
        environment[INPUT_FDS_ENV_KEY] = ",".join(str(fd) for fd in input_fds)
        encoded_argv = tuple(value.encode("utf-8", errors="strict") for value in argv)
        encoded_env = tuple(
            f"{key}={value}".encode("utf-8", errors="strict")
            for key, value in sorted(environment.items())
        )
        argv_array = (ctypes.c_char_p * (len(encoded_argv) + 1))(*encoded_argv, None)
        env_array = (ctypes.c_char_p * (len(encoded_env) + 1))(*encoded_env, None)
        seccomp_filters, seccomp_program = _seccomp_no_spawn_program_v1()
        pidfd_cell = ctypes.c_int(-1)
        clone_args = CloneArgsV1(
            flags=REQUIRED_CLONE_FLAGS,
            pidfd=ctypes.addressof(pidfd_cell),
            exit_signal=signal.SIGCHLD,
            cgroup=leaf_fd,
        )
        launch_args = _NativeLaunchArgsV1(
            clone_args=ctypes.addressof(clone_args),
            executable_fd=executable_fd,
            null_fd=null_fd,
            argv=ctypes.cast(argv_array, ctypes.c_void_p).value,
            envp=ctypes.cast(env_array, ctypes.c_void_p).value,
            expected_parent_pid=os.getpid(),
            landlock_ruleset_fd=landlock_ruleset_fd,
            seccomp_program=ctypes.addressof(seccomp_program),
            setup_status_fd=setup_status_write_fd,
        )
        trampoline = _native_trampoline_v1()
        launch_args_pointer = ctypes.byref(launch_args)
        # The already-prepared PYFUNCTYPE retains the GIL from the final
        # descriptor/thread audit through native clone3.
        clone_result: int | None = None
        try:
            if _native_trampoline_v1() is not trampoline:
                _fail("native trampoline function identity changed")
            _assert_exact_inheritable_fds({0, 1, 2, *inherited})
            _assert_descriptor_roles_current(
                descriptors=descriptor_roles,
                identities=descriptor_identities,
                required_inheritable=inherited,
            )
            if _thread_count() == 1:
                clone_result = int(trampoline(launch_args_pointer))
                if clone_result > 0:
                    # Publish every cleanup authority while signals remain
                    # blocked. A pending Python handler cannot interrupt the
                    # parent before child_pid/pidfd are recoverable.
                    child_pid = clone_result
                    pidfd = pidfd_cell.value
                    # The kernel has created the process.  Write the
                    # attempt-scope edge before descriptor cleanup, signal
                    # unmasking, or any other fallible post-clone work.
                    attempt_process_sink.record_v075_k7_attempt_process_launch_v1()
                    record_lifecycle("PROCESS_LAUNCH")
                    os.close(setup_status_write_fd)
                    setup_status_write_fd = -1
                    os.close(landlock_ruleset_fd)
                    landlock_ruleset_fd = -1
                    child_socket.close()
                    child_socket = None
                    for fd in inherited[:-1]:
                        os.set_inheritable(fd, False)
        finally:
            assert previous_signal_mask is not None
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_signal_mask)
            signals_blocked = False
        if clone_result is None:
            lease.close()
            lease_closed = True
            bootstrap.close()
            return K7AtomicPidfdBlockedResultV1(
                _BLOCKED_ISSUER,
                K7AtomicPidfdBlockerV1.MULTITHREADED_PARENT,
                None,
                True,
                True,
                True,
                True,
                False,
            )
        # Keep the BPF array live until the syscall returns in the parent.
        del seccomp_filters
        clone_error = -clone_result if clone_result < 0 else 0
        if clone_result < 0:
            lease.close()
            lease_closed = True
            bootstrap.close()
            return K7AtomicPidfdBlockedResultV1(
                _BLOCKED_ISSUER,
                K7AtomicPidfdBlockerV1.CLONE3_REJECTED,
                clone_error,
                True,
                True,
                True,
                True,
                True,
            )
        if pidfd < 0:
            raise V075K7AtomicPidfdCleanupV1Error("clone3 did not return its required pidfd")

        poller = select.poll()
        poller.register(pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)
        poller.register(parent_socket.fileno(), select.POLLIN | select.POLLHUP | select.POLLERR)
        deadline_ns = start_ns + deadline_milliseconds * 1_000_000
        socket_eof = False
        socket_eof_before_reap = False
        pidfd_ready = False
        while waited is None:
            remaining_ns = deadline_ns - time.monotonic_ns()
            if remaining_ns <= 0:
                forced_reason = "DEADLINE"
                _send_pidfd_signal(numbers, pidfd, signal.SIGKILL)
                signal_count += 1
                waited = wait_and_record_reap()
                break
            events = poller.poll(max(1, min(100, (remaining_ns + 999_999) // 1_000_000)))
            for descriptor, event in events:
                if descriptor == parent_socket.fileno() and event & (select.POLLIN | select.POLLHUP | select.POLLERR):
                    while True:
                        try:
                            chunk = os.read(descriptor, min(65536, output_cap_bytes + 1 - len(output)))
                        except BlockingIOError:
                            break
                        socket_reads += 1
                        if not chunk:
                            socket_eof = True
                            socket_eof_before_reap = waited is None
                            record_lifecycle("OUTPUT_EOF")
                            try:
                                poller.unregister(descriptor)
                            except KeyError:  # pragma: no cover - local idempotence
                                pass
                            break
                        total_output_bytes += len(chunk)
                        output.extend(chunk[: output_cap_bytes + 1 - len(output)])
                        if len(output) > output_cap_bytes:
                            forced_reason = "OUTPUT_CAP"
                            _send_pidfd_signal(numbers, pidfd, signal.SIGKILL)
                            signal_count += 1
                            waited = wait_and_record_reap()
                            break
                if waited is None and descriptor == pidfd and event & (select.POLLIN | select.POLLHUP | select.POLLERR):
                    # On normal termination retain the child as a zombie until
                    # exact EOF has frozen its sole output stream.  This gives
                    # the parent a non-racy cutoff-before-reap observation.
                    pidfd_ready = True
                    try:
                        poller.unregister(pidfd)
                    except KeyError:  # pragma: no cover - local idempotence
                        pass
            if (
                waited is None
                and forced_reason is None
                and pidfd_ready
                and socket_eof
            ):
                waited = wait_and_record_reap()
            if forced_reason is not None:
                break

        # Drain bytes already committed to the parent socket after reap.
        if not socket_eof:
            parent_socket.setblocking(True)
            parent_socket.settimeout(0.1)
            drain_deadline_ns = time.monotonic_ns() + 1_000_000_000
            while not socket_eof:
                try:
                    chunk = parent_socket.recv(65536)
                except (TimeoutError, socket.timeout):
                    if time.monotonic_ns() >= drain_deadline_ns:
                        _fail("parent could not prove EOF on the child channel")
                    continue
                socket_reads += 1
                if not chunk:
                    socket_eof = True
                    record_lifecycle("OUTPUT_EOF")
                    break
                total_output_bytes += len(chunk)
                if len(output) <= output_cap_bytes:
                    output.extend(chunk[: output_cap_bytes + 1 - len(output)])
        if len(output) > output_cap_bytes and forced_reason is None:
            forced_reason = "OUTPUT_CAP"
        if len(output) > output_cap_bytes:
            del output[output_cap_bytes:]
        if not socket_eof:
            _fail("parent did not observe exact EOF on the child channel")

        setup_status_raw = _read_setup_status(setup_status_read_fd)
        setup_succeeded, setup_failure_stage, setup_errno = _parse_setup_status(
            setup_status_raw
        )

        cgroup_lease._validate_empty_leaf(leaf_fd)  # noqa: SLF001
        record_lifecycle("CGROUP_EMPTY")
        # _validate_empty_leaf reads procs, threads, pids.current, and events.
        reads += 4
        controls = {
            name: cgroup_lease._parse_ascii(  # noqa: SLF001
                cgroup_lease._read_control(leaf_fd, name), name  # noqa: SLF001
            ).strip()
            for name in ("pids.max", "cgroup.max.depth", "cgroup.max.descendants")
        }
        reads += 3
        if controls != {"pids.max": "1", "cgroup.max.depth": "0", "cgroup.max.descendants": "0"}:
            _fail("attempt leaf descendant/process caps changed")
        cgroup_stat = _parse_cgroup_stat(
            cgroup_lease._read_control(leaf_fd, "cgroup.stat")  # noqa: SLF001
        )
        reads += 1
        no_descendants = (
            cgroup_stat["nr_descendants"] == 0
            and cgroup_stat["nr_dying_descendants"] == 0
        )
        if not no_descendants:
            _fail("attempt leaf retained a live or dying descendant cgroup")
        record_lifecycle("DESCENDANT_SCAN")
        # Final peak is intentionally observed after the descendant scan so
        # the parent lifecycle order is: reap -> descendant proof -> peak.
        memory_peak = cgroup_lease._parse_nonnegative(  # noqa: SLF001
            cgroup_lease._read_control(leaf_fd, "memory.peak"),  # noqa: SLF001
            "memory.peak",
        )
        reads += 1
        if memory_peak > memory_max_bytes:
            _fail("attempt leaf memory peak exceeded its hard cap")
        record_lifecycle("FINAL_MEMORY_PEAK")
        reads += _verify_leaf_memory_controls(
            leaf_fd=leaf_fd,
            memory_max_bytes=memory_max_bytes,
        )
        record_lifecycle("MEMORY_CONTROLS_VERIFIED")
        # K7CgroupAttemptLeaseV1.close performs one final four-control empty
        # proof before removing the leaf.
        reads += 4
        lease.close()
        lease_closed = True
        bootstrap.close()
        assert waited is not None
        outcome, exit_code, terminating_signal = _status(waited, forced_reason)
        if (
            setup_failure_stage is not None
            and exit_code in {126, 127}
            and terminating_signal is None
        ):
            outcome = K7AtomicPidfdOutcomeV1.SETUP_FAILED
        elif (
            not setup_succeeded
            and setup_failure_stage is None
            and forced_reason is None
        ):
            _fail("child terminated before producing native setup evidence")
        counters = K7AtomicPidfdCountersV1(
            1,
            1,
            signal_count,
            socket_reads,
            total_output_bytes,
            len(output),
            reads,
        )
        lifecycle_sequence = {
            role: index
            for index, role in enumerate(lifecycle_roles, start=1)
        }
        supervisor_evidence = K7AtomicSupervisorResourceEvidenceV1(
            _SUPERVISOR_EVIDENCE_ISSUER,
            lease_id,
            child_pid,
            lifecycle_sequence["PROCESS_LAUNCH"],
            lifecycle_sequence["OUTPUT_EOF"],
            lifecycle_sequence["PROCESS_REAP"],
            lifecycle_sequence["CGROUP_EMPTY"],
            lifecycle_sequence["DESCENDANT_SCAN"],
            lifecycle_sequence["FINAL_MEMORY_PEAK"],
            lifecycle_sequence["MEMORY_CONTROLS_VERIFIED"],
            counters.process_launches,
            memory_peak,
            memory_max_bytes,
            socket_eof_before_reap,
            True,
            no_descendants,
        )
        return K7AtomicPidfdRunResultV1(
            _RESULT_ISSUER,
            lease_id,
            child_pid,
            outcome,
            exit_code,
            terminating_signal,
            setup_succeeded,
            setup_failure_stage,
            setup_errno,
            bytes(output),
            total_output_bytes > len(output),
            socket_eof_before_reap,
            deadline_milliseconds,
            output_cap_bytes,
            memory_max_bytes,
            memory_peak,
            True,
            no_descendants,
            supervisor_evidence,
            time.monotonic_ns() - start_ns,
            counters,
        )
    except BaseException:
        fatal_cleanup_errors: list[BaseException] = []
        child_reaped = waited is not None
        if child_pid > 0 and not child_reaped and pidfd >= 0:
            try:
                _send_pidfd_signal(numbers, pidfd, signal.SIGKILL)
            except BaseException:
                # Whole-leaf kill below is the independent containment path.
                pass
            try:
                waited = _wait_pidfd(pidfd)
                child_reaped = True
            except BaseException:
                # Retry after cgroup.kill; an empty leaf is not a reap proof.
                pass
        elif child_pid > 0 and not child_reaped:
            try:
                _kill_and_reap_direct_child(child_pid)
                child_reaped = True
            except BaseException:
                pass
        if child_pid > 0:
            try:
                _kill_leaf_and_wait_empty(leaf_fd)
            except BaseException as cleanup:
                fatal_cleanup_errors.append(cleanup)
        if child_pid > 0 and not child_reaped and pidfd >= 0:
            try:
                waited = _wait_pidfd(pidfd)
                child_reaped = True
            except BaseException:
                pass
        if child_pid > 0 and not child_reaped:
            try:
                _kill_and_reap_direct_child(child_pid)
                child_reaped = True
            except BaseException as cleanup:
                fatal_cleanup_errors.append(cleanup)
        if child_pid > 0 and not child_reaped:
            fatal_cleanup_errors.append(
                V075K7AtomicPidfdCleanupV1Error(
                    "direct child could not be proven reaped"
                )
            )
        if not lease_closed:
            try:
                lease.close()
            except BaseException as cleanup:
                fatal_cleanup_errors.append(cleanup)
            finally:
                lease_closed = True
        if fatal_cleanup_errors:
            raise V075K7AtomicPidfdCleanupV1Error(
                "atomic runtime cleanup did not close every child/cgroup obligation"
            ) from fatal_cleanup_errors[0]
        raise
    finally:
        if claimed_lease_key is not None:
            with _CONSUMED_LOCK:
                _CONSUMED_LEASES.discard(claimed_lease_key)
        final_cleanup_errors: list[BaseException] = []
        signal_restore_error: BaseException | None = None
        for owned_socket in (child_socket, parent_socket):
            if owned_socket is not None:
                try:
                    owned_socket.close()
                except BaseException as cleanup:
                    final_cleanup_errors.append(cleanup)
        for descriptor in (
            pidfd,
            setup_status_read_fd,
            setup_status_write_fd,
            null_fd,
            landlock_ruleset_fd,
        ):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except BaseException as cleanup:
                    final_cleanup_errors.append(cleanup)
        try:
            if not bootstrap.closed:
                bootstrap.close()
        except BaseException as cleanup:
            final_cleanup_errors.append(cleanup)
        if signals_blocked and previous_signal_mask is not None:
            try:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_signal_mask)
            except BaseException as restore:
                signal_restore_error = restore
            finally:
                signals_blocked = False
        if final_cleanup_errors:
            raise V075K7AtomicPidfdCleanupV1Error(
                "atomic runtime descriptor/bootstrap cleanup failed"
            ) from final_cleanup_errors[0]
        if signal_restore_error is not None:
            raise signal_restore_error


attempt_process_sink._register_v075_k7_attempt_process_runtime_callsite_v1(  # noqa: SLF001
    run_v075_k7_atomic_pidfd_runtime_v1
)


__all__ = [
    "ACTUAL_PROJECTION_PROOF_AUTHORIZED",
    "ATTEMPT_TERMINAL_AUTHORIZED",
    "CHANNEL_ENV_KEY",
    "CLONE_CLEAR_SIGHAND",
    "CLONE_INTO_CGROUP",
    "CLONE_PIDFD",
    "COMPARISON_VECTOR_AUTHORIZED",
    "COUNTER_RECORD_AUTHORIZED",
    "CloneArgsV1",
    "K7AtomicPidfdBlockedResultV1",
    "K7AtomicPidfdCapabilityV1",
    "K7AtomicPidfdCountersV1",
    "K7AtomicPidfdOutcomeV1",
    "K7AtomicPidfdSetupStageV1",
    "K7AtomicSupervisorResourceEvidenceV1",
    "K7SealedBootstrapExecV1",
    "MAX_ARGV_COUNT",
    "MAX_ARGV_ENV_BYTES",
    "MAX_CHILD_OUTPUT_BYTES",
    "MAX_SEALED_INPUT_COUNT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROFILE_KEY",
    "REQUIRED_CLONE_FLAGS",
    "SCHEMA_VERSION",
    "SUCCESS_PATH_CGROUP_CONTROL_READS",
    "V075K7AtomicPidfdCleanupV1Error",
    "V075K7AtomicPidfdRuntimeV1Error",
    "WORK_VECTOR_AUTHORIZED",
    "create_v075_k7_sealed_memfd_from_bytes_v1",
    "freeze_v075_k7_sealed_bootstrap_exec_v1",
    "probe_v075_k7_atomic_pidfd_capability_v1",
    "run_v075_k7_atomic_pidfd_runtime_v1",
]
