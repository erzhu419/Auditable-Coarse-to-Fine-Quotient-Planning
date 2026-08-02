"""Two-stage Linux sandbox construction for the K7 production roles.

The parent freezes an exact executable-FD-bound seccomp program and creates a
Landlock ruleset before entering the native launch critical section.  The
native trampoline consumes those two objects in the freshly cloned child,
installs them before its sole ``execveat`` edge, and never returns to Python.
The pre-exec filter denies every descendant-creation syscall and plain
``execve`` while admitting only ``execveat(executable_fd, ..., AT_EMPTY_PATH)``.

The fresh-exec Python entry adds a second filter which denies both exec calls.
It does not install Landlock and cannot manufacture a from-birth claim.
WORKER's parent-built ruleset has one output-directory PATH_BENEATH rule;
BUSINESS's has none.  This module remains construction-only: it issues no
accounting, attempt-terminal, or official-execution authority.
"""

from __future__ import annotations

import ctypes
from dataclasses import InitVar, dataclass, field
from enum import Enum
import errno
import fcntl
import hashlib
import os
import platform
import stat
import sys
import zipimport
from threading import Lock
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_PRODUCTION_ROLE_POSTEXEC_TIGHTENING_V2_DOMAIN,
    V075_K7_PRODUCTION_ROLE_SANDBOX_PROFILE_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.11"
PROFILE_KEY = "v075_k7_production_role_sandbox_v2"
PROFILE_DOMAIN = V075_K7_PRODUCTION_ROLE_SANDBOX_PROFILE_V2_DOMAIN
POSTEXEC_DOMAIN = V075_K7_PRODUCTION_ROLE_POSTEXEC_TIGHTENING_V2_DOMAIN
REQUESTED_PHASE3E_DOMAIN_TAGS = (PROFILE_DOMAIN, POSTEXEC_DOMAIN)
if not frozenset(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("production role sandbox domains are unregistered")

AUDIT_ARCH_X86_64 = 0xC000003E
X32_SYSCALL_BIT = 0x40000000

LANDLOCK_CREATE_RULESET = 444
LANDLOCK_ADD_RULE = 445
LANDLOCK_RESTRICT_SELF = 446
LANDLOCK_CREATE_RULESET_VERSION = 1
LANDLOCK_RULE_PATH_BENEATH = 1
MINIMUM_LANDLOCK_ABI = 3

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
LANDLOCK_WRITE_MASK = (
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
    | LANDLOCK_ACCESS_FS_REFER
    | LANDLOCK_ACCESS_FS_TRUNCATE
)

SECCOMP_SET_MODE_FILTER = 1
SECCOMP_FILTER_FLAG_TSYNC = 1
PR_SET_NO_NEW_PRIVS = 38
AT_EMPTY_PATH = 0x1000
SECCOMP_SYSCALL_X86_64 = 317
SECCOMP_RET_KILL_PROCESS = 0x80000000
SECCOMP_RET_ERRNO = 0x00050000
SECCOMP_RET_ALLOW = 0x7FFF0000
BPF_LD_W_ABS = 0x20
BPF_JMP_JEQ_K = 0x15
BPF_JMP_JSET_K = 0x45
BPF_RET_K = 0x06
SECCOMP_FCNTL_SYSCALL_X86_64 = 72


class K7ProductionSandboxRoleV2(str, Enum):
    WORKER = "WORKER"
    BUSINESS = "BUSINESS"


class V075K7ProductionRoleSandboxV2Error(RuntimeError):
    """The sandbox profile, FD binding, kernel support, or install failed."""


class V075K7ProductionRoleSandboxV2Unavailable(
    V075K7ProductionRoleSandboxV2Error
):
    """The exact required Linux architecture or Landlock ABI is unavailable."""


def _fail(message: str) -> NoReturn:
    raise V075K7ProductionRoleSandboxV2Error(message)


def _construction_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("production role sandbox used an undeclared domain")
    return content_id(domain, dict(payload))


def _formal_locks() -> dict[str, bool]:
    return {
        "native_role_launcher_joined": False,
        "complete_attempt_memory_window_verified": False,
        "shared_resource_receipts_issued": False,
        "counter_record_authorized": False,
        "work_vector_authorized": False,
        "comparison_vector_authorized": False,
        "attempt_terminal_authorized": False,
        "official_execution_allowed": False,
    }


X86_64_SYSCALL_NUMBERS: Mapping[str, int] = MappingProxyType(
    {
        "ioctl": 16,
        "shmget": 29,
        "shmat": 30,
        "shmctl": 31,
        "socket": 41,
        "connect": 42,
        "accept": 43,
        "bind": 49,
        "listen": 50,
        "socketpair": 53,
        "clone": 56,
        "fork": 57,
        "vfork": 58,
        "execve": 59,
        "kill": 62,
        "semget": 64,
        "semop": 65,
        "semctl": 66,
        "shmdt": 67,
        "msgget": 68,
        "msgsnd": 69,
        "msgrcv": 70,
        "msgctl": 71,
        "truncate": 76,
        "ftruncate": 77,
        "rename": 82,
        "mkdir": 83,
        "rmdir": 84,
        "creat": 85,
        "link": 86,
        "unlink": 87,
        "symlink": 88,
        "chmod": 90,
        "fchmod": 91,
        "chown": 92,
        "fchown": 93,
        "lchown": 94,
        "ptrace": 101,
        "rt_sigqueueinfo": 129,
        "mknod": 133,
        "setpriority": 141,
        "sched_setparam": 142,
        "sched_setscheduler": 144,
        "pivot_root": 155,
        "prctl": 157,
        "chroot": 161,
        "mount": 165,
        "umount2": 166,
        "setxattr": 188,
        "lsetxattr": 189,
        "fsetxattr": 190,
        "removexattr": 197,
        "lremovexattr": 198,
        "fremovexattr": 199,
        "tkill": 200,
        "sched_setaffinity": 203,
        "tgkill": 234,
        "add_key": 248,
        "request_key": 249,
        "keyctl": 250,
        "ioprio_set": 251,
        "migrate_pages": 256,
        "mkdirat": 258,
        "mknodat": 259,
        "fchownat": 260,
        "unlinkat": 263,
        "renameat": 264,
        "linkat": 265,
        "symlinkat": 266,
        "fchmodat": 268,
        "unshare": 272,
        "move_pages": 279,
        "accept4": 288,
        "perf_event_open": 298,
        "fanotify_init": 300,
        "prlimit64": 302,
        "process_vm_readv": 310,
        "process_vm_writev": 311,
        "kcmp": 312,
        "sched_setattr": 314,
        "renameat2": 316,
        "bpf": 321,
        "execveat": 322,
        "userfaultfd": 323,
        "pidfd_send_signal": 424,
        "io_uring_setup": 425,
        "io_uring_enter": 426,
        "io_uring_register": 427,
        "open_tree": 428,
        "move_mount": 429,
        "fsopen": 430,
        "fsmount": 432,
        "fspick": 433,
        "pidfd_open": 434,
        "clone3": 435,
        "pidfd_getfd": 438,
        "process_madvise": 440,
        "fchmodat2": 452,
    }
)

_COMMON_DENIED_NAMES = frozenset(
    {
        "ioctl",
        "shmget",
        "shmat",
        "shmctl",
        "socket",
        "connect",
        "accept",
        "bind",
        "listen",
        "socketpair",
        "clone",
        "fork",
        "vfork",
        "execve",
        "kill",
        "semget",
        "semop",
        "semctl",
        "shmdt",
        "msgget",
        "msgsnd",
        "msgrcv",
        "msgctl",
        "truncate",
        "chmod",
        "chown",
        "fchown",
        "lchown",
        "ptrace",
        "rt_sigqueueinfo",
        "mknod",
        "setpriority",
        "sched_setparam",
        "sched_setscheduler",
        "pivot_root",
        "prctl",
        "chroot",
        "mount",
        "umount2",
        "setxattr",
        "lsetxattr",
        "fsetxattr",
        "removexattr",
        "lremovexattr",
        "fremovexattr",
        "tkill",
        "sched_setaffinity",
        "tgkill",
        "add_key",
        "request_key",
        "keyctl",
        "ioprio_set",
        "migrate_pages",
        "mknodat",
        "fchownat",
        "fchmodat",
        "unshare",
        "move_pages",
        "accept4",
        "perf_event_open",
        "fanotify_init",
        "prlimit64",
        "process_vm_readv",
        "process_vm_writev",
        "kcmp",
        "sched_setattr",
        "bpf",
        "userfaultfd",
        "pidfd_send_signal",
        "io_uring_setup",
        "io_uring_enter",
        "io_uring_register",
        "open_tree",
        "move_mount",
        "fsopen",
        "fsmount",
        "fspick",
        "pidfd_open",
        "clone3",
        "pidfd_getfd",
        "process_madvise",
        "fchmodat2",
    }
)
_BUSINESS_ONLY_DENIED_NAMES = frozenset(
    {
        "rename",
        "mkdir",
        "rmdir",
        "creat",
        "link",
        "unlink",
        "symlink",
        "fchmod",
        "mkdirat",
        "unlinkat",
        "renameat",
        "linkat",
        "symlinkat",
        "renameat2",
    }
)
_WORKER_ONLY_DENIED_NAMES = frozenset({"ftruncate"})

DENIED_FCNTL_COMMANDS = (
    8,     # F_SETOWN
    10,    # F_SETSIG
    15,    # F_SETOWN_EX
    1024,  # F_SETLEASE
    1026,  # F_NOTIFY
)
EXISTING_ENDPOINT_SYSCALLS = (
    "sendto",
    "recvfrom",
    "sendmsg",
    "recvmsg",
)
DESCENDANT_CREATION_SYSCALLS = (
    "clone",
    "fork",
    "vfork",
    "clone3",
)
PREEXEC_DENIED_EXEC_SYSCALLS = (
    "execve",
)
POSTEXEC_DENIED_EXEC_SYSCALLS = ("execve", "execveat")
# Compatibility display name.  The exact pre-exec execveat edge is not a
# process-creation permission: it is FD/flag gated and immediately followed by
# post-exec tightening in the loaded role entry.
PROCESS_CREATION_SYSCALLS = DESCENDANT_CREATION_SYSCALLS


def denied_syscalls_for_role_v2(
    role: K7ProductionSandboxRoleV2 | str,
) -> tuple[tuple[str, int], ...]:
    exact = K7ProductionSandboxRoleV2(role)
    names = set(_COMMON_DENIED_NAMES)
    names.update(
        _WORKER_ONLY_DENIED_NAMES
        if exact is K7ProductionSandboxRoleV2.WORKER
        else _BUSINESS_ONLY_DENIED_NAMES
    )
    return tuple(sorted(((name, X86_64_SYSCALL_NUMBERS[name]) for name in names), key=lambda row: row[1]))


class _LandlockRulesetAttrV2(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _LandlockPathBeneathAttrV2(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
    ]


class _SockFilterV2(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_ushort),
        ("jt", ctypes.c_ubyte),
        ("jf", ctypes.c_ubyte),
        ("k", ctypes.c_uint32),
    ]


class _SockFprogV2(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ushort),
        ("filters", ctypes.POINTER(_SockFilterV2)),
    ]


_LIBC = ctypes.PyDLL(None, use_errno=True)
_LIBC.syscall.restype = ctypes.c_long
_LIBC.prctl.restype = ctypes.c_int


def _raw_syscall(number: int, *arguments: object) -> tuple[int, int]:
    ctypes.set_errno(0)
    result = int(_LIBC.syscall(ctypes.c_long(number), *arguments))
    return result, (ctypes.get_errno() if result == -1 else 0)


def probe_v075_k7_production_landlock_abi_v2() -> int | None:
    if sys.platform != "linux":
        return None
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
    raise V075K7ProductionRoleSandboxV2Error(
        f"Landlock ABI probe failed with unexpected errno {error}"
    )


def _architecture_rows_v2() -> list[_SockFilterV2]:
    """Load a native x86-64 syscall number or kill the process."""

    return [
        _SockFilterV2(BPF_LD_W_ABS, 0, 0, 4),
        _SockFilterV2(BPF_JMP_JEQ_K, 1, 0, AUDIT_ARCH_X86_64),
        _SockFilterV2(BPF_RET_K, 0, 0, SECCOMP_RET_KILL_PROCESS),
        _SockFilterV2(BPF_LD_W_ABS, 0, 0, 0),
        _SockFilterV2(BPF_JMP_JSET_K, 0, 1, X32_SYSCALL_BIT),
        _SockFilterV2(BPF_RET_K, 0, 0, SECCOMP_RET_KILL_PROCESS),
    ]


def _preexec_filter_rows_v2(
    role: K7ProductionSandboxRoleV2,
    executable_fd: int,
) -> tuple[_SockFilterV2, ...]:
    """Build the child-before-exec filter bound to one executable FD.

    ``struct seccomp_data`` stores each 64-bit argument little-endian on the
    only admitted architecture.  Both halves are checked so a forged upper
    word cannot alias the frozen descriptor or ``AT_EMPTY_PATH`` flag.
    """

    if type(executable_fd) is not int or not 3 <= executable_fd <= 0x7FFFFFFF:
        _fail("pre-exec seccomp requires one native executable FD")
    rows = _architecture_rows_v2()

    # A non-execveat syscall jumps over this gate and reloads nr.  A matching
    # syscall reaches ALLOW only for the exact fd and exact AT_EMPTY_PATH flag;
    # every crossed argument reaches the shared EPERM return.
    rows.extend(
        (
            _SockFilterV2(
                BPF_JMP_JEQ_K,
                0,
                10,
                X86_64_SYSCALL_NUMBERS["execveat"],
            ),
            _SockFilterV2(BPF_LD_W_ABS, 0, 0, 16),  # args[0], low word
            _SockFilterV2(BPF_JMP_JEQ_K, 0, 7, executable_fd),
            _SockFilterV2(BPF_LD_W_ABS, 0, 0, 20),  # args[0], high word
            _SockFilterV2(BPF_JMP_JEQ_K, 0, 5, 0),
            _SockFilterV2(BPF_LD_W_ABS, 0, 0, 48),  # args[4], low word
            _SockFilterV2(BPF_JMP_JEQ_K, 0, 3, AT_EMPTY_PATH),
            _SockFilterV2(BPF_LD_W_ABS, 0, 0, 52),  # args[4], high word
            _SockFilterV2(BPF_JMP_JEQ_K, 0, 1, 0),
            _SockFilterV2(BPF_RET_K, 0, 0, SECCOMP_RET_ALLOW),
            _SockFilterV2(
                BPF_RET_K,
                0,
                0,
                SECCOMP_RET_ERRNO | errno.EPERM,
            ),
            _SockFilterV2(BPF_LD_W_ABS, 0, 0, 0),
        )
    )

    rows = [
        *rows,
    ]
    fcntl_rows = [_SockFilterV2(BPF_LD_W_ABS, 0, 0, 24)]
    for command in DENIED_FCNTL_COMMANDS:
        fcntl_rows.extend(
            (
                _SockFilterV2(BPF_JMP_JEQ_K, 0, 1, command),
                _SockFilterV2(
                    BPF_RET_K,
                    0,
                    0,
                    SECCOMP_RET_ERRNO | errno.EPERM,
                ),
            )
        )
    fcntl_rows.append(_SockFilterV2(BPF_LD_W_ABS, 0, 0, 0))
    rows.append(
        _SockFilterV2(
            BPF_JMP_JEQ_K,
            0,
            len(fcntl_rows),
            SECCOMP_FCNTL_SYSCALL_X86_64,
        )
    )
    rows.extend(fcntl_rows)
    for _name, number in denied_syscalls_for_role_v2(role):
        rows.extend(
            (
                _SockFilterV2(BPF_JMP_JEQ_K, 0, 1, number),
                _SockFilterV2(
                    BPF_RET_K,
                    0,
                    0,
                    SECCOMP_RET_ERRNO | errno.EPERM,
                ),
            )
        )
    rows.append(_SockFilterV2(BPF_RET_K, 0, 0, SECCOMP_RET_ALLOW))
    return tuple(rows)


def preexec_seccomp_filter_rows_for_role_v2(
    role: K7ProductionSandboxRoleV2 | str,
    *,
    executable_fd: int,
) -> tuple[tuple[int, int, int, int], ...]:
    exact = K7ProductionSandboxRoleV2(role)
    return tuple(
        (int(row.code), int(row.jt), int(row.jf), int(row.k))
        for row in _preexec_filter_rows_v2(exact, executable_fd)
    )


def _preexec_seccomp_program_v2(
    role: K7ProductionSandboxRoleV2,
    executable_fd: int,
) -> tuple[Any, _SockFprogV2]:
    rows = _preexec_filter_rows_v2(role, executable_fd)
    array_type = _SockFilterV2 * len(rows)
    filters = array_type(*rows)
    return filters, _SockFprogV2(len(rows), filters)


def _postexec_filter_rows_v2() -> tuple[_SockFilterV2, ...]:
    rows = _architecture_rows_v2()
    for name in POSTEXEC_DENIED_EXEC_SYSCALLS:
        rows.extend(
            (
                _SockFilterV2(
                    BPF_JMP_JEQ_K,
                    0,
                    1,
                    X86_64_SYSCALL_NUMBERS[name],
                ),
                _SockFilterV2(
                    BPF_RET_K,
                    0,
                    0,
                    SECCOMP_RET_ERRNO | errno.EPERM,
                ),
            )
        )
    rows.append(_SockFilterV2(BPF_RET_K, 0, 0, SECCOMP_RET_ALLOW))
    return tuple(rows)


def postexec_seccomp_filter_rows_v2() -> tuple[tuple[int, int, int, int], ...]:
    return tuple(
        (int(row.code), int(row.jt), int(row.jf), int(row.k))
        for row in _postexec_filter_rows_v2()
    )


def _postexec_seccomp_program_v2() -> tuple[Any, _SockFprogV2]:
    rows = _postexec_filter_rows_v2()
    array_type = _SockFilterV2 * len(rows)
    filters = array_type(*rows)
    return filters, _SockFprogV2(len(rows), filters)


def _thread_count_v2() -> int | None:
    try:
        names = os.listdir("/proc/self/task")
    except OSError:
        return None
    values = tuple(name for name in names if name.isdigit())
    return len(values) if values else None


def _directory_fd_identity_v2(descriptor: int) -> tuple[int, ...]:
    if type(descriptor) is not int or descriptor < 3:
        _fail("worker output-directory FD is invalid")
    try:
        status = os.fstat(descriptor)
        open_flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        descriptor_flags = fcntl.fcntl(descriptor, fcntl.F_GETFD)
        inheritable = os.get_inheritable(descriptor)
    except OSError as error:
        raise V075K7ProductionRoleSandboxV2Error(
            "worker output-directory FD cannot be inspected"
        ) from error
    if (
        not stat.S_ISDIR(status.st_mode)
        or open_flags & os.O_ACCMODE != os.O_RDONLY
        or open_flags & os.O_APPEND
        or descriptor_flags & fcntl.FD_CLOEXEC == 0
        or inheritable
    ):
        _fail("worker output-directory FD lost its read-only CLOEXEC contract")
    return (
        status.st_dev,
        status.st_ino,
        stat.S_IMODE(status.st_mode),
        status.st_uid,
        status.st_gid,
        status.st_nlink,
        open_flags,
        descriptor_flags,
    )


def _executable_fd_identity_v2(descriptor: int) -> tuple[int, ...]:
    if type(descriptor) is not int or descriptor < 3:
        _fail("executable FD is invalid")
    try:
        status = os.fstat(descriptor)
        open_flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        descriptor_flags = fcntl.fcntl(descriptor, fcntl.F_GETFD)
        inheritable = os.get_inheritable(descriptor)
    except OSError as error:
        raise V075K7ProductionRoleSandboxV2Error(
            "executable FD cannot be inspected"
        ) from error
    if (
        not stat.S_ISREG(status.st_mode)
        or status.st_size <= 0
        or open_flags & os.O_ACCMODE != os.O_RDONLY
        or open_flags & os.O_APPEND
        or descriptor_flags & fcntl.FD_CLOEXEC == 0
        or inheritable
    ):
        _fail("executable FD lost its nonempty read-only CLOEXEC contract")
    return (
        status.st_dev,
        status.st_ino,
        stat.S_IMODE(status.st_mode),
        status.st_uid,
        status.st_gid,
        status.st_nlink,
        status.st_size,
        status.st_mtime_ns,
        open_flags,
        descriptor_flags,
    )


def _ruleset_fd_identity_v2(descriptor: int) -> tuple[int, ...]:
    if type(descriptor) is not int or descriptor < 3:
        _fail("Landlock ruleset FD is invalid")
    try:
        status = os.fstat(descriptor)
        open_flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        descriptor_flags = fcntl.fcntl(descriptor, fcntl.F_GETFD)
        inheritable = os.get_inheritable(descriptor)
    except OSError as error:
        raise V075K7ProductionRoleSandboxV2Error(
            "Landlock ruleset FD cannot be inspected"
        ) from error
    if descriptor_flags & fcntl.FD_CLOEXEC == 0 or inheritable:
        _fail("Landlock ruleset FD lost its CLOEXEC contract")
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
        status.st_nlink,
        open_flags,
        descriptor_flags,
    )


def _output_identity_document(identity: tuple[int, ...] | None) -> Any:
    if identity is None:
        return {"kind": "NOT_APPLICABLE", "reason": "BUSINESS_DENY_ALL_WRITES"}
    return {
        "device": identity[0],
        "inode": identity[1],
        "mode": identity[2],
        "owner_uid": identity[3],
        "owner_gid": identity[4],
        "link_count": identity[5],
        "open_flags": identity[6],
        "descriptor_flags": identity[7],
    }


def _executable_identity_document(identity: tuple[int, ...]) -> dict[str, int]:
    return {
        "device": identity[0],
        "inode": identity[1],
        "mode": identity[2],
        "owner_uid": identity[3],
        "owner_gid": identity[4],
        "link_count": identity[5],
        "size": identity[6],
        "mtime_ns": identity[7],
        "open_flags": identity[8],
        "descriptor_flags": identity[9],
    }


@dataclass(frozen=True, slots=True)
class K7ProductionRoleSandboxProfileV2:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("production role sandbox profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _construction_id(PROFILE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        roles = []
        for role in K7ProductionSandboxRoleV2:
            roles.append(
                {
                    "role": role.value,
                    "preexec_denied_x86_64_syscalls": [
                        {"name": name, "number": number}
                        for name, number in denied_syscalls_for_role_v2(role)
                    ],
                    "preexec_execveat_gate": {
                        "executable_fd": "EXACT_FROZEN_EXECUTABLE_FD",
                        "flags": AT_EMPTY_PATH,
                        "high_words_zero": True,
                        "native_trampoline_single_edge_required": True,
                    },
                    "landlock_allowed_write_root": (
                        "BOUND_OUTPUT_DIRECTORY_SUBTREE"
                        if role is K7ProductionSandboxRoleV2.WORKER
                        else "NONE"
                    ),
                }
            )
        return {
            "schema": "acfqp.v075_k7_production_role_sandbox_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "platform": "linux",
            "machine": "x86_64",
            "audit_arch": AUDIT_ARCH_X86_64,
            "x32_rejected": True,
            "minimum_landlock_abi": MINIMUM_LANDLOCK_ABI,
            "landlock_handled_write_mask": LANDLOCK_WRITE_MASK,
            "landlock_path_beneath_rule_type": LANDLOCK_RULE_PATH_BENEATH,
            "seccomp_default_action": "ALLOW",
            "seccomp_denied_action": "ERRNO_EPERM",
            "architecture_mismatch_action": "KILL_PROCESS",
            "parent_only_prepares_ruleset_and_filter": True,
            "native_trampoline_sets_no_new_privileges": True,
            "native_trampoline_restricts_landlock_before_exec": True,
            "preexec_filter_installed_before_exec": True,
            "preexec_filter_tsync_required": False,
            "fresh_child_single_thread_required": True,
            "descendant_creation_syscalls_denied": list(
                DESCENDANT_CREATION_SYSCALLS
            ),
            "preexec_denied_exec_syscalls": list(
                PREEXEC_DENIED_EXEC_SYSCALLS
            ),
            "preexec_exact_execveat_edge": True,
            "postexec_denied_exec_syscalls": list(
                POSTEXEC_DENIED_EXEC_SYSCALLS
            ),
            "postexec_tsync_required": True,
            "postexec_landlock_installation_forbidden": True,
            "existing_endpoint_syscalls_allowed": list(
                EXISTING_ENDPOINT_SYSCALLS
            ),
            "fcntl_commands_denied": list(DENIED_FCNTL_COMMANDS),
            "role_contracts": roles,
            "construction_only": True,
            "profile_domain_registry_joined": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _construction_id(PROFILE_DOMAIN, self._payload()) != self._profile_id:
            _fail("production role sandbox profile changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "production_role_sandbox_profile_id": self.profile_id,
        }


_PROFILE_ISSUER = object()
_AUTHORITY_ISSUER = object()
_MATERIAL_ISSUER = object()
_POSTEXEC_ISSUER = object()
_POSTEXEC_ENTRY_ATTESTATION_ISSUER = object()
_POSTEXEC_INSTALL_LOCK = Lock()
_POSTEXEC_INSTALLATION: "K7ProductionRolePostexecTighteningV2 | None" = None
_OFFICIAL_PROFILE = K7ProductionRoleSandboxProfileV2(_PROFILE_ISSUER)


def official_v075_k7_production_role_sandbox_profile_v2(
) -> K7ProductionRoleSandboxProfileV2:
    return _OFFICIAL_PROFILE


class K7ProductionRoleSandboxAuthorityV2:
    """Parent-owned, exact-FD authority prepared for the native trampoline."""

    __slots__ = (
        "_closed",
        "_consumed",
        "_executable_fd",
        "_executable_identity",
        "_filter_memory_sha256",
        "_filters",
        "_landlock_ruleset_fd",
        "_landlock_ruleset_identity",
        "_lock",
        "_output_directory_fd",
        "_output_directory_identity",
        "_owner_pid",
        "_program",
        "landlock_abi",
        "role",
    )

    def __init__(
        self,
        issuer: object,
        *,
        role: K7ProductionSandboxRoleV2,
        landlock_abi: int,
        executable_fd: int,
        executable_identity: tuple[int, ...],
        output_directory_fd: int | None,
        output_directory_identity: tuple[int, ...] | None,
        landlock_ruleset_fd: int,
        landlock_ruleset_identity: tuple[int, ...],
        filters: Any,
        program: _SockFprogV2,
    ) -> None:
        if issuer is not _AUTHORITY_ISSUER:
            _fail("production role sandbox authority is caller-minted")
        if (
            type(landlock_abi) is not int
            or landlock_abi < MINIMUM_LANDLOCK_ABI
            or (role is K7ProductionSandboxRoleV2.WORKER)
            != (output_directory_fd is not None)
            or (output_directory_fd is None)
            != (output_directory_identity is None)
            or type(executable_fd) is not int
            or type(executable_identity) is not tuple
            or type(landlock_ruleset_fd) is not int
            or type(landlock_ruleset_identity) is not tuple
            or type(program) is not _SockFprogV2
        ):
            _fail("production role sandbox authority fields are crossed")
        self.role = role
        self.landlock_abi = landlock_abi
        self._executable_fd = executable_fd
        self._executable_identity = executable_identity
        self._output_directory_fd = output_directory_fd
        self._output_directory_identity = output_directory_identity
        self._landlock_ruleset_fd = landlock_ruleset_fd
        self._landlock_ruleset_identity = landlock_ruleset_identity
        self._filters = filters
        self._program = program
        self._filter_memory_sha256 = hashlib.sha256(
            ctypes.string_at(ctypes.addressof(filters), ctypes.sizeof(filters))
        ).hexdigest()
        self._owner_pid = os.getpid()
        self._consumed = False
        self._closed = False
        self._lock = Lock()

    @property
    def executable_fd(self) -> int:
        return self._executable_fd

    @property
    def output_directory_fd(self) -> int | None:
        return self._output_directory_fd

    @property
    def preexec_landlock_ruleset_fd(self) -> int:
        return self._landlock_ruleset_fd

    @property
    def executable_identity(self) -> Mapping[str, int]:
        return MappingProxyType(
            dict(_executable_identity_document(self._executable_identity))
        )

    @property
    def output_directory_identity(self) -> Mapping[str, Any]:
        return MappingProxyType(
            dict(_output_identity_document(self._output_directory_identity))
        )

    def assert_current(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("production role sandbox authority crossed a process")
        if self._closed:
            _fail("production role sandbox authority is closed")
        if self._consumed:
            _fail("production role sandbox authority was already consumed")
        _assert_platform_v2()
        if probe_v075_k7_production_landlock_abi_v2() != self.landlock_abi:
            _fail("Landlock ABI changed after authority issuance")
        if _executable_fd_identity_v2(self._executable_fd) != self._executable_identity:
            _fail("executable FD identity changed")
        if self.role is K7ProductionSandboxRoleV2.WORKER:
            assert self._output_directory_fd is not None
            if (
                _directory_fd_identity_v2(self._output_directory_fd)
                != self._output_directory_identity
            ):
                _fail("worker output-directory FD identity changed")
        elif self._output_directory_fd is not None:
            _fail("business sandbox gained a path-write FD")
        if (
            _ruleset_fd_identity_v2(self._landlock_ruleset_fd)
            != self._landlock_ruleset_identity
        ):
            _fail("Landlock ruleset FD identity changed")
        _assert_filter_storage_v2(
            filters=self._filters,
            program=self._program,
            expected_sha256=self._filter_memory_sha256,
        )

    def _consume(self) -> "K7ProductionRolePreexecSandboxMaterialV2":
        with self._lock:
            self.assert_current()
            self._consumed = True
            material = K7ProductionRolePreexecSandboxMaterialV2(
                _MATERIAL_ISSUER,
                role=self.role,
                landlock_abi=self.landlock_abi,
                executable_fd=self._executable_fd,
                executable_identity=self._executable_identity,
                output_directory_fd=self._output_directory_fd,
                output_directory_identity=self._output_directory_identity,
                landlock_ruleset_fd=self._landlock_ruleset_fd,
                landlock_ruleset_identity=self._landlock_ruleset_identity,
                filters=self._filters,
                program=self._program,
                filter_memory_sha256=self._filter_memory_sha256,
            )
            self._landlock_ruleset_fd = -1
            return material

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            if not self._consumed and self._landlock_ruleset_fd >= 0:
                os.close(self._landlock_ruleset_fd)
                self._landlock_ruleset_fd = -1
            self._closed = True

    def __del__(self) -> None:
        if getattr(self, "_owner_pid", None) == os.getpid():
            try:
                self.close()
            except BaseException:
                pass

    def __reduce__(self) -> NoReturn:
        raise TypeError("production role sandbox authority is process-local")

    def __reduce_ex__(self, _protocol: int) -> NoReturn:
        raise TypeError("production role sandbox authority is process-local")


def _assert_platform_v2() -> None:
    if sys.platform != "linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        raise V075K7ProductionRoleSandboxV2Unavailable(
            "production role sandbox requires Linux x86-64"
        )


def _create_landlock_ruleset_v2() -> int:
    attribute = _LandlockRulesetAttrV2(LANDLOCK_WRITE_MASK)
    descriptor, error = _raw_syscall(
        LANDLOCK_CREATE_RULESET,
        ctypes.byref(attribute),
        ctypes.sizeof(attribute),
        0,
    )
    if descriptor < 0:
        raise V075K7ProductionRoleSandboxV2Error(
            f"role Landlock ruleset creation failed with errno {error}"
        )
    try:
        os.set_inheritable(descriptor, False)
        if not fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC:
            _fail("role Landlock ruleset FD is not CLOEXEC")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _add_worker_output_rule_v2(
    *, ruleset_fd: int, output_directory_fd: int
) -> None:
    attribute = _LandlockPathBeneathAttrV2(
        LANDLOCK_WRITE_MASK,
        output_directory_fd,
    )
    result, error = _raw_syscall(
        LANDLOCK_ADD_RULE,
        ruleset_fd,
        LANDLOCK_RULE_PATH_BENEATH,
        ctypes.byref(attribute),
        0,
    )
    if result != 0:
        raise V075K7ProductionRoleSandboxV2Error(
            f"worker Landlock PATH_BENEATH rule failed with errno {error}"
        )


def _assert_filter_storage_v2(
    *, filters: Any, program: _SockFprogV2, expected_sha256: str
) -> None:
    observed = hashlib.sha256(
        ctypes.string_at(ctypes.addressof(filters), ctypes.sizeof(filters))
    ).hexdigest()
    pointer = ctypes.cast(program.filters, ctypes.c_void_p).value
    if (
        observed != expected_sha256
        or int(program.length) != len(filters)
        or pointer != ctypes.addressof(filters)
    ):
        _fail("pre-exec seccomp storage identity changed")


class K7ProductionRolePreexecSandboxMaterialV2:
    """One-shot native arguments retaining the exact BPF backing storage."""

    __slots__ = (
        "_closed",
        "_executable_fd",
        "_executable_identity",
        "_filter_memory_sha256",
        "_filters",
        "_landlock_ruleset_fd",
        "_landlock_ruleset_identity",
        "_lock",
        "_output_directory_fd",
        "_output_directory_identity",
        "_owner_pid",
        "_program",
        "landlock_abi",
        "role",
    )

    def __init__(
        self,
        issuer: object,
        *,
        role: K7ProductionSandboxRoleV2,
        landlock_abi: int,
        executable_fd: int,
        executable_identity: tuple[int, ...],
        output_directory_fd: int | None,
        output_directory_identity: tuple[int, ...] | None,
        landlock_ruleset_fd: int,
        landlock_ruleset_identity: tuple[int, ...],
        filters: Any,
        program: _SockFprogV2,
        filter_memory_sha256: str,
    ) -> None:
        if issuer is not _MATERIAL_ISSUER:
            _fail("pre-exec sandbox material is caller-minted")
        self.role = role
        self.landlock_abi = landlock_abi
        self._executable_fd = executable_fd
        self._executable_identity = executable_identity
        self._output_directory_fd = output_directory_fd
        self._output_directory_identity = output_directory_identity
        self._landlock_ruleset_fd = landlock_ruleset_fd
        self._landlock_ruleset_identity = landlock_ruleset_identity
        self._filters = filters
        self._program = program
        self._filter_memory_sha256 = filter_memory_sha256
        self._owner_pid = os.getpid()
        self._closed = False
        self._lock = Lock()

    @property
    def executable_fd(self) -> int:
        return self._executable_fd

    @property
    def preexec_landlock_ruleset_fd(self) -> int:
        return self._landlock_ruleset_fd

    @property
    def preexec_seccomp_program_address(self) -> int:
        self.assert_current()
        return ctypes.addressof(self._program)

    @property
    def preexec_seccomp_filter_sha256(self) -> str:
        self.assert_current()
        rows = preexec_seccomp_filter_rows_for_role_v2(
            self.role,
            executable_fd=self._executable_fd,
        )
        return hashlib.sha256(
            canonical_json_bytes([list(row) for row in rows])
        ).hexdigest()

    def assert_current(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("pre-exec sandbox material crossed a process")
        if self._closed:
            _fail("pre-exec sandbox material is closed")
        _assert_platform_v2()
        if probe_v075_k7_production_landlock_abi_v2() != self.landlock_abi:
            _fail("Landlock ABI changed after native material issuance")
        if _executable_fd_identity_v2(self._executable_fd) != self._executable_identity:
            _fail("executable FD identity changed")
        if self.role is K7ProductionSandboxRoleV2.WORKER:
            assert self._output_directory_fd is not None
            if (
                _directory_fd_identity_v2(self._output_directory_fd)
                != self._output_directory_identity
            ):
                _fail("worker output-directory FD identity changed")
        elif self._output_directory_fd is not None:
            _fail("business native material gained a path-write FD")
        if (
            _ruleset_fd_identity_v2(self._landlock_ruleset_fd)
            != self._landlock_ruleset_identity
        ):
            _fail("Landlock ruleset FD identity changed")
        _assert_filter_storage_v2(
            filters=self._filters,
            program=self._program,
            expected_sha256=self._filter_memory_sha256,
        )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            if self._owner_pid == os.getpid() and self._landlock_ruleset_fd >= 0:
                os.close(self._landlock_ruleset_fd)
                self._landlock_ruleset_fd = -1
            self._closed = True

    def __del__(self) -> None:
        try:
            self.close()
        except BaseException:
            pass

    def __reduce__(self) -> NoReturn:
        raise TypeError("pre-exec sandbox material is process-local")

    def __reduce_ex__(self, _protocol: int) -> NoReturn:
        raise TypeError("pre-exec sandbox material is process-local")


def freeze_v075_k7_production_role_preexec_sandbox_authority_v2(
    *,
    role: K7ProductionSandboxRoleV2 | str,
    executable_fd: int,
    output_directory_fd: int | None = None,
) -> K7ProductionRoleSandboxAuthorityV2:
    """Prepare, but do not install, the child sandbox in the parent."""

    _assert_platform_v2()
    exact_role = K7ProductionSandboxRoleV2(role)
    executable_identity = _executable_fd_identity_v2(executable_fd)
    if exact_role is K7ProductionSandboxRoleV2.WORKER:
        if output_directory_fd is None:
            _fail("worker sandbox requires its exact output-directory FD")
        output_identity = _directory_fd_identity_v2(output_directory_fd)
    else:
        if output_directory_fd is not None:
            _fail("business sandbox may not receive a write-root FD")
        output_identity = None
    descriptors = tuple(
        descriptor
        for descriptor in (executable_fd, output_directory_fd)
        if descriptor is not None
    )
    if len(descriptors) != len(set(descriptors)):
        _fail("pre-exec sandbox descriptor roles overlap")
    abi = probe_v075_k7_production_landlock_abi_v2()
    if abi is None or abi < MINIMUM_LANDLOCK_ABI:
        raise V075K7ProductionRoleSandboxV2Unavailable(
            "production role sandbox requires Landlock ABI 3 or newer"
        )
    ruleset_fd = -1
    try:
        ruleset_fd = _create_landlock_ruleset_v2()
        if ruleset_fd in descriptors:
            _fail("Landlock ruleset FD overlaps a frozen role FD")
        if exact_role is K7ProductionSandboxRoleV2.WORKER:
            assert output_directory_fd is not None
            _add_worker_output_rule_v2(
                ruleset_fd=ruleset_fd,
                output_directory_fd=output_directory_fd,
            )
        ruleset_identity = _ruleset_fd_identity_v2(ruleset_fd)
        filters, program = _preexec_seccomp_program_v2(
            exact_role,
            executable_fd,
        )
        authority = K7ProductionRoleSandboxAuthorityV2(
            _AUTHORITY_ISSUER,
            role=exact_role,
            landlock_abi=abi,
            executable_fd=executable_fd,
            executable_identity=executable_identity,
            output_directory_fd=output_directory_fd,
            output_directory_identity=output_identity,
            landlock_ruleset_fd=ruleset_fd,
            landlock_ruleset_identity=ruleset_identity,
            filters=filters,
            program=program,
        )
        ruleset_fd = -1
        return authority
    finally:
        if ruleset_fd >= 0:
            os.close(ruleset_fd)


def consume_v075_k7_production_role_preexec_sandbox_v2(
    authority: K7ProductionRoleSandboxAuthorityV2,
) -> K7ProductionRolePreexecSandboxMaterialV2:
    """Transfer exact native arguments out of one issued parent authority."""

    if type(authority) is not K7ProductionRoleSandboxAuthorityV2:
        _fail("pre-exec sandbox consumption requires the exact issued authority")
    return authority._consume()  # noqa: SLF001 - issuer-owned one-shot boundary


_SANDBOX_MODULE_NAME = "acfqp.v075_k7_production_role_sandbox_v2"
_SANDBOX_ARCHIVE_MEMBER = "acfqp/v075_k7_production_role_sandbox_v2.py"
_REQUIRED_ARCHIVE_SEALS = 0x0008 | 0x0004 | 0x0002 | 0x0001


def _postexec_archive_binding_v2(
    source_archive_fd: int,
) -> tuple[tuple[int, ...], str, str]:
    if type(source_archive_fd) is not int or source_archive_fd < 3:
        _fail("post-exec entry attestation requires one source-archive FD")
    archive_path = f"/proc/self/fd/{source_archive_fd}"
    specification = globals().get("__spec__")
    loader = getattr(specification, "loader", None)
    origin = getattr(specification, "origin", None)
    expected_origin = f"{archive_path}/{_SANDBOX_ARCHIVE_MEMBER}"
    if (
        type(loader) is not zipimport.zipimporter
        or getattr(loader, "archive", None) != archive_path
        or getattr(specification, "name", None) != _SANDBOX_MODULE_NAME
        or origin != expected_origin
        or globals().get("__file__") != expected_origin
        or sys.modules.get(_SANDBOX_MODULE_NAME) is not sys.modules.get(__name__)
    ):
        _fail("sandbox module is not exact-source-archive loaded")
    try:
        status = os.fstat(source_archive_fd)
        seals = fcntl.fcntl(source_archive_fd, 1034)
        descriptor_flags = fcntl.fcntl(source_archive_fd, fcntl.F_GETFD)
        raw = loader.get_data(expected_origin)
    except OSError as error:
        raise V075K7ProductionRoleSandboxV2Error(
            "sandbox source-archive binding cannot be replayed"
        ) from error
    if (
        not stat.S_ISREG(status.st_mode)
        or status.st_size <= 0
        or seals & _REQUIRED_ARCHIVE_SEALS != _REQUIRED_ARCHIVE_SEALS
        or descriptor_flags & fcntl.FD_CLOEXEC == 0
        or type(raw) is not bytes
        or not raw
    ):
        _fail("sandbox source-archive FD lost its sealed CLOEXEC contract")
    return (
        (
            status.st_dev,
            status.st_ino,
            status.st_mode,
            status.st_uid,
            status.st_gid,
            status.st_size,
            status.st_mtime_ns,
            status.st_ctime_ns,
            seals,
            descriptor_flags,
        ),
        expected_origin,
        hashlib.sha256(raw).hexdigest(),
    )


@dataclass(frozen=True, slots=True)
class K7ProductionRolePostexecTighteningV2:
    _issuer: InitVar[object]
    role: K7ProductionSandboxRoleV2
    seccomp_filter_sha256: str
    _tightening_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _POSTEXEC_ISSUER
            or type(self.seccomp_filter_sha256) is not str
            or len(self.seccomp_filter_sha256) != 64
        ):
            _fail("post-exec sandbox tightening is caller-minted")
        object.__setattr__(
            self,
            "_tightening_id",
            _construction_id(POSTEXEC_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_role_postexec_tightening.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_role_sandbox_profile_id": _OFFICIAL_PROFILE.profile_id,
            "role": self.role.value,
            "seccomp_filter_sha256": self.seccomp_filter_sha256,
            "execve_denied": True,
            "execveat_denied": True,
            "seccomp_tsync_completed": True,
            "landlock_installed_by_this_stage": False,
            "landlock_from_birth_required": True,
            "preexec_sandbox_verified_by_this_stage": False,
            "construction_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def tightening_id(self) -> str:
        if _construction_id(POSTEXEC_DOMAIN, self._payload()) != self._tightening_id:
            _fail("post-exec sandbox tightening changed")
        return self._tightening_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "production_role_postexec_tightening_id": self.tightening_id,
        }

    def __reduce__(self) -> NoReturn:
        raise TypeError("post-exec sandbox tightening is process-local")

    def __reduce_ex__(self, _protocol: int) -> NoReturn:
        raise TypeError("post-exec sandbox tightening is process-local")


class K7ProductionRolePostexecEntryAttestationV2:
    """Archive/role-bound one-shot permit consumed before entry imports."""

    __slots__ = (
        "_archive_identity",
        "_consumed",
        "_lock",
        "_owner_pid",
        "_sandbox_origin",
        "_sandbox_source_sha256",
        "_source_archive_fd",
        "_tightening",
        "role",
    )

    def __init__(
        self,
        issuer: object,
        *,
        tightening: K7ProductionRolePostexecTighteningV2,
        source_archive_fd: int,
        archive_identity: tuple[int, ...],
        sandbox_origin: str,
        sandbox_source_sha256: str,
    ) -> None:
        if (
            issuer is not _POSTEXEC_ENTRY_ATTESTATION_ISSUER
            or type(tightening) is not K7ProductionRolePostexecTighteningV2
            or type(source_archive_fd) is not int
            or source_archive_fd < 3
            or type(archive_identity) is not tuple
            or len(archive_identity) != 10
            or type(sandbox_origin) is not str
            or not sandbox_origin
            or type(sandbox_source_sha256) is not str
            or len(sandbox_source_sha256) != 64
        ):
            _fail("post-exec entry attestation is caller-minted")
        self.role = tightening.role
        self._tightening = tightening
        self._source_archive_fd = source_archive_fd
        self._archive_identity = archive_identity
        self._sandbox_origin = sandbox_origin
        self._sandbox_source_sha256 = sandbox_source_sha256
        self._owner_pid = os.getpid()
        self._consumed = False
        self._lock = Lock()

    def _consume(
        self,
        *,
        role: K7ProductionSandboxRoleV2,
        source_archive_fd: int,
    ) -> None:
        with self._lock:
            if os.getpid() != self._owner_pid:
                _fail("post-exec entry attestation crossed a process")
            if self._consumed:
                _fail("post-exec entry attestation was already consumed")
            if role is not self.role:
                _fail("post-exec entry attestation crossed its role")
            if source_archive_fd != self._source_archive_fd:
                _fail("post-exec entry attestation crossed its archive FD")
            if _POSTEXEC_INSTALLATION is not self._tightening:
                _fail("post-exec entry attestation lost its installation")
            identity, origin, source_sha256 = _postexec_archive_binding_v2(
                source_archive_fd
            )
            if (
                identity != self._archive_identity
                or origin != self._sandbox_origin
                or source_sha256 != self._sandbox_source_sha256
                or self._tightening.role is not role
                or len(self._tightening.tightening_id) != 64
            ):
                _fail("post-exec entry attestation replay changed")
            self._consumed = True

    def __reduce__(self) -> NoReturn:
        raise TypeError("post-exec entry attestation is process-local")

    def __reduce_ex__(self, _protocol: int) -> NoReturn:
        raise TypeError("post-exec entry attestation is process-local")


def install_v075_k7_production_role_postexec_tightening_v2(
    *, role: K7ProductionSandboxRoleV2 | str
) -> K7ProductionRolePostexecTighteningV2:
    """Add only the exec-denial filter in the fresh-exec role process."""

    global _POSTEXEC_INSTALLATION
    with _POSTEXEC_INSTALL_LOCK:
        if _POSTEXEC_INSTALLATION is not None:
            _fail("post-exec tightening was already installed")
        _assert_platform_v2()
        exact_role = K7ProductionSandboxRoleV2(role)
        if _thread_count_v2() != 1:
            _fail("post-exec tightening requires one role-process thread")
        rows = postexec_seccomp_filter_rows_v2()
        filter_sha256 = hashlib.sha256(
            canonical_json_bytes([list(row) for row in rows])
        ).hexdigest()
        filters, program = _postexec_seccomp_program_v2()
        result, error = _raw_syscall(
            SECCOMP_SYSCALL_X86_64,
            SECCOMP_SET_MODE_FILTER,
            SECCOMP_FILTER_FLAG_TSYNC,
            ctypes.byref(program),
        )
        del filters
        if result != 0:
            raise V075K7ProductionRoleSandboxV2Error(
                f"post-exec seccomp TSYNC failed with result {result} errno {error}"
            )
        installation = K7ProductionRolePostexecTighteningV2(
            _POSTEXEC_ISSUER,
            exact_role,
            filter_sha256,
        )
        _POSTEXEC_INSTALLATION = installation
        return installation


def install_v075_k7_production_role_archive_postexec_tightening_v2(
    *,
    role: K7ProductionSandboxRoleV2 | str,
    source_archive_fd: int,
) -> K7ProductionRolePostexecEntryAttestationV2:
    """Validate this module's archive origin, install once, and bind entry."""

    exact_role = K7ProductionSandboxRoleV2(role)
    before = _postexec_archive_binding_v2(source_archive_fd)
    tightening = install_v075_k7_production_role_postexec_tightening_v2(
        role=exact_role
    )
    after = _postexec_archive_binding_v2(source_archive_fd)
    if after != before:
        _fail("sandbox source archive changed across post-exec installation")
    return K7ProductionRolePostexecEntryAttestationV2(
        _POSTEXEC_ENTRY_ATTESTATION_ISSUER,
        tightening=tightening,
        source_archive_fd=source_archive_fd,
        archive_identity=before[0],
        sandbox_origin=before[1],
        sandbox_source_sha256=before[2],
    )


def consume_v075_k7_production_role_postexec_entry_attestation_v2(
    attestation: K7ProductionRolePostexecEntryAttestationV2,
    *,
    role: K7ProductionSandboxRoleV2 | str,
    source_archive_fd: int,
) -> None:
    """Replay and consume the exact archive-bound entry permit once."""

    if type(attestation) is not K7ProductionRolePostexecEntryAttestationV2:
        _fail("role entry lacks its exact post-exec attestation")
    attestation._consume(  # noqa: SLF001 - issuer-owned one-shot boundary
        role=K7ProductionSandboxRoleV2(role),
        source_archive_fd=source_archive_fd,
    )


def verify_v075_k7_production_role_postexec_exec_denial_v2() -> None:
    """Live-probe both exec syscalls after the one post-exec installation."""

    if type(_POSTEXEC_INSTALLATION) is not K7ProductionRolePostexecTighteningV2:
        _fail("post-exec exec-denial probe precedes filter installation")
    result, error = _raw_syscall(
        X86_64_SYSCALL_NUMBERS["execve"],
        ctypes.c_void_p(1),
        ctypes.c_void_p(0),
        ctypes.c_void_p(0),
    )
    if result != -1 or error != errno.EPERM:
        _fail("post-exec execve denial did not replay")
    result, error = _raw_syscall(
        X86_64_SYSCALL_NUMBERS["execveat"],
        -1,
        ctypes.c_void_p(1),
        ctypes.c_void_p(0),
        ctypes.c_void_p(0),
        AT_EMPTY_PATH,
    )
    if result != -1 or error != errno.EPERM:
        _fail("post-exec execveat denial did not replay")


__all__ = (
    "AUDIT_ARCH_X86_64",
    "DENIED_FCNTL_COMMANDS",
    "DESCENDANT_CREATION_SYSCALLS",
    "EXISTING_ENDPOINT_SYSCALLS",
    "K7ProductionRoleSandboxAuthorityV2",
    "K7ProductionRolePostexecTighteningV2",
    "K7ProductionRolePostexecEntryAttestationV2",
    "K7ProductionRolePreexecSandboxMaterialV2",
    "K7ProductionRoleSandboxProfileV2",
    "K7ProductionSandboxRoleV2",
    "LANDLOCK_WRITE_MASK",
    "MINIMUM_LANDLOCK_ABI",
    "PROCESS_CREATION_SYSCALLS",
    "POSTEXEC_DENIED_EXEC_SYSCALLS",
    "PREEXEC_DENIED_EXEC_SYSCALLS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075K7ProductionRoleSandboxV2Error",
    "V075K7ProductionRoleSandboxV2Unavailable",
    "consume_v075_k7_production_role_postexec_entry_attestation_v2",
    "consume_v075_k7_production_role_preexec_sandbox_v2",
    "denied_syscalls_for_role_v2",
    "freeze_v075_k7_production_role_preexec_sandbox_authority_v2",
    "install_v075_k7_production_role_archive_postexec_tightening_v2",
    "install_v075_k7_production_role_postexec_tightening_v2",
    "official_v075_k7_production_role_sandbox_profile_v2",
    "postexec_seccomp_filter_rows_v2",
    "preexec_seccomp_filter_rows_for_role_v2",
    "probe_v075_k7_production_landlock_abi_v2",
    "verify_v075_k7_production_role_postexec_exec_denial_v2",
)
