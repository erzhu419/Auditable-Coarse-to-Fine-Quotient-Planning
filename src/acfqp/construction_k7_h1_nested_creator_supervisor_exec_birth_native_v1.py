"""Audited clone3/release/execveat primitive for a nested-creator SUPERVISOR.

The exact relocation-free x86-64 text image creates one cgroup-placed blocked
child, withdraws both PID-cell writers, waits for the guardian release, echoes
it, and execveat-enters the exact sealed freestanding supervisor role.  This
module exposes ABI and image verification only; it launches no process.
"""

from __future__ import annotations

import ctypes
import hashlib
import mmap
from pathlib import Path
import platform
from typing import Any, NoReturn

from acfqp import construction_k7_h1_nested_creator_supervisor_native_v1 as role_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-B2-D-EXEC-NATIVE"
PROFILE_KEY = "construction_k7_h1_nested_creator_supervisor_exec_birth_native_v1"
READINESS = "AUDITED_NATIVE_EXEC_BIRTH_PRIMITIVE_ONLY"

AUDITED_NATIVE_TRAMPOLINE_SOURCE_PRESENT = True
RELOCATION_FREE_TEXT_IMAGE_PRESENT = True
PYFUNCTYPE_GIL_RETAINING_ENTRY_PRESENT = True
W_X_MAPPING_PRESENT = True
PARENT_WITHDRAWAL_AND_EXEC_FD_CLOSE_ABI_PRESENT = True
CHILD_RAW_GATE_THEN_EXACT_EXECVEAT_PRESENT = True

CLONE_SYSCALL_PERFORMED = False
ACTUAL_PROCESS_BIRTH_PRESENT = False
ACTUAL_SUPERVISOR_EXEC_PRESENT = False
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

CLONE_PIDFD = 0x00001000
CLONE_PARENT_SETTID = 0x00100000
CLONE_CLEAR_SIGHAND = 0x100000000
CLONE_INTO_CGROUP = 0x200000000
REQUIRED_CLONE_FLAGS = (
    CLONE_PIDFD | CLONE_PARENT_SETTID | CLONE_CLEAR_SIGHAND | CLONE_INTO_CGROUP
)
CLONE_ARGS_SIZE = 88
MAX_RELEASE_FRAME_BYTES = 64
CHILD_GATE_SOURCE_FD_MINIMUM = 5
EXECUTABLE_SOURCE_FD_MINIMUM = 5
RELEASE_ENDPOINT_SO_PASSCRED = False
RELEASE_ANCILLARY_GRAMMAR = "NONE"
RELEASE_RECVMSG_CONTROL_CAP_BYTES = 64
RELEASE_RECVMSG_CALL_FLAGS = 0x40000000
RELEASE_ALLOWED_MSG_FLAGS_MASK = 0x40000080
RELEASE_REJECTED_TRUNCATION_FLAGS_MASK = 0x28

PARENT_EDGE_CLONE_ATTEMPTED = 1
PARENT_EDGE_CLONE_SUCCEEDED = 2
PARENT_EDGE_CLONE_REJECTED = 4
PARENT_EDGE_CREATOR_MAPPING_WITHDRAWN = 8
PARENT_EDGE_CREATOR_FD_CLOSED = 16
PARENT_EDGE_CGROUP_GRANT_FD_CLOSED = 32
PARENT_EDGE_EXECUTABLE_FD_CLOSED = 64
PARENT_EDGE_REQUIRED_SUCCESS_BITS = (
    PARENT_EDGE_CLONE_ATTEMPTED
    | PARENT_EDGE_CLONE_SUCCEEDED
    | PARENT_EDGE_CREATOR_MAPPING_WITHDRAWN
    | PARENT_EDGE_CREATOR_FD_CLOSED
    | PARENT_EDGE_CGROUP_GRANT_FD_CLOSED
    | PARENT_EDGE_EXECUTABLE_FD_CLOSED
)
PARENT_EDGE_REQUIRED_REJECTION_BITS = (
    PARENT_EDGE_CLONE_ATTEMPTED
    | PARENT_EDGE_CLONE_REJECTED
    | PARENT_EDGE_CREATOR_MAPPING_WITHDRAWN
    | PARENT_EDGE_CREATOR_FD_CLOSED
    | PARENT_EDGE_CGROUP_GRANT_FD_CLOSED
    | PARENT_EDGE_EXECUTABLE_FD_CLOSED
)

SOURCE_PATH = (
    Path(__file__).resolve(strict=True).parent
    / "native"
    / "h1_nested_creator_supervisor_exec_birth_x86_64_v1.S"
).resolve(strict=True)
SOURCE_SHA256 = "cb7b665a024d9d92821a706e5c68d5e24fcbcb3ef6d2faac401936265ba4803b"
X86_64_TEXT_BYTE_COUNT = 1050
X86_64_TEXT_SHA256 = "4c7c0e802d40f708e4727deb24ca0160f768fd9b3e068934ff0524c97a2e40d6"
X86_64_TEXT_BYTES = bytes.fromhex(
    "41544155415641574989fc4d8b7c243049c7470801000000498b3c2448c7c65800000048c7c0b30100000f054885c00f84d10000004989c549890749c7c60000"
    "00004885c0780749834f0802eb0549834f080448c7c00b000000498b7c2408498b7424100f054885c0780749834f0808eb074989c64989471048c7c003000000"
    "498b7c24180f054885c0780749834f0810eb0c4d85f675074989c64989471048c7c003000000498b7c24200f054885c0780749834f0820eb0c4d85f675074989"
    "c64989471048c7c003000000498b7c24680f054885c0780749834f0840eb0c4d85f675074989c6498947104d85f6740e4c89f0482d30750000e9130300004c89"
    "e8e90b03000048c7c00b000000498b7c2408498b7424100f054885c00f888a02000048c7c003000000498b7c24180f054885c00f887c02000048c7c024010000"
    "498b7c242848c7c6030000004831d20f054885c00f886402000048c7c024010000498b7c246848c7c60400000048c7c2000008000f054885c00f884802000048"
    "c7c0b401000048c7c70500000048beffffffff000000004831d20f054885c00f882b02000048c7c02c00000048c7c703000000498b742438498b54244049c7c2"
    "004000004d31c04d31c90f054885c00f8804020000493b4424400f85f901000048c7c02c00000048c7c703000000498b742448498b54245049c7c2004000004d"
    "31c04d31c90f054885c00f88d2010000493b4424500f85c7010000498b4424604883f8400f87c101000048ffc04881ecd00000004989c5488d3c244831c048c7"
    "c11a000000f348ab488d042448894424484c896c2450488d442448488944246848c744247001000000488d842490000000488944247848c78424800000004000"
    "000048c7c02f00000048c7c703000000488d74245848c7c2000000400f054885c00f88ea000000493b4424600f85df000000837c2460000f85d40000004883bc"
    "2480000000000f85c50000008b84248800000089c283e2280f85b3000000257fffffbf0f85a80000004831c9493b4c2460741d480fb6040c498b742458480fb6"
    "140e4839d00f858f00000048ffc1ebdc48c7c02c00000048c7c7030000004889e6498b54246049c7c2004000004d31c04d31c90f054885c07869493b44246075"
    "624881c4d00000004883ec0848c704240000000048c7c04201000048c7c7040000004889e6498b5424704d8b54247849c7c0001000004d31c90f054883c40848"
    "c7c78100000048c7c0e70000000f050f0b4881c4d0000000eb514881c4d0000000eb514881c4d0000000eb5148c7c778000000eb5148c7c779000000eb4848c7"
    "c77a000000eb3f48c7c77b000000eb3648c7c77c000000eb2d48c7c77d000000eb2448c7c77e000000eb1b48c7c77f000000eb1248c7c780000000eb0948c7c7"
    "81000000eb0048c7c0e70000000f050f0b415f415e415d415cc3"
)


class ConstructionK7H1NestedCreatorSupervisorExecBirthNativeV1Error(ValueError):
    """The exact exec-birth source, text image, role, or ABI changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1NestedCreatorSupervisorExecBirthNativeV1Error(message)


class CloneArgsV1(ctypes.Structure):
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


class NativeParentEdgeV1(ctypes.Structure):
    _fields_ = [
        ("clone_result", ctypes.c_int64),
        ("status_bits", ctypes.c_uint64),
        ("first_cleanup_error", ctypes.c_int64),
        ("reserved_zero", ctypes.c_uint64),
    ]


class NativeExecLaunchArgsV1(ctypes.Structure):
    _fields_ = [
        ("clone_args", ctypes.c_void_p),
        ("creator_pid_cell_mapping", ctypes.c_void_p),
        ("pid_cell_mapping_bytes", ctypes.c_uint64),
        ("creator_pid_cell_fd", ctypes.c_int64),
        ("one_shot_cgroup_grant_fd", ctypes.c_int64),
        ("child_gate_fd", ctypes.c_int64),
        ("parent_edge", ctypes.c_void_p),
        ("cell_withdrawn_frame", ctypes.c_void_p),
        ("cell_withdrawn_frame_bytes", ctypes.c_uint64),
        ("gate_ready_frame", ctypes.c_void_p),
        ("gate_ready_frame_bytes", ctypes.c_uint64),
        ("release_frame", ctypes.c_void_p),
        ("release_frame_bytes", ctypes.c_uint64),
        ("supervisor_executable_fd", ctypes.c_int64),
        ("supervisor_argv", ctypes.c_void_p),
        ("supervisor_envp", ctypes.c_void_p),
    ]


_LIBC = ctypes.CDLL(None, use_errno=True)
_TRAMPOLINE_MEMORY: mmap.mmap | None = None
_TRAMPOLINE_FUNCTION: Any = None


def verify_nested_creator_supervisor_exec_birth_native_image_v1() -> dict[str, Any]:
    """Replay checked-in source, text, role image, and the exact launch ABI."""

    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        _fail("nested-creator exec-birth is registered only for Linux x86-64")
    try:
        source = SOURCE_PATH.read_bytes()
    except OSError as error:
        raise ConstructionK7H1NestedCreatorSupervisorExecBirthNativeV1Error(
            "nested-creator exec-birth source is unavailable"
        ) from error
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        _fail("nested-creator exec-birth source digest changed")
    if (
        len(X86_64_TEXT_BYTES) != X86_64_TEXT_BYTE_COUNT
        or hashlib.sha256(X86_64_TEXT_BYTES).hexdigest() != X86_64_TEXT_SHA256
    ):
        _fail("nested-creator exec-birth text image changed")
    role = role_v1.verify_nested_creator_supervisor_native_image_v1()
    if (
        role["elf_sha256"] != role_v1.ELF_SHA256
        or role["elf_byte_count"] != role_v1.ELF_BYTE_COUNT
    ):
        _fail("nested-creator exec-birth role image changed")
    if ctypes.sizeof(CloneArgsV1) != CLONE_ARGS_SIZE:
        _fail("nested-creator exec-birth clone_args ABI changed")
    if ctypes.sizeof(NativeParentEdgeV1) != 32:
        _fail("nested-creator exec-birth parent edge ABI changed")
    if ctypes.sizeof(NativeExecLaunchArgsV1) != 128:
        _fail("nested-creator exec-birth launch ABI changed")
    offsets = {
        name: getattr(NativeExecLaunchArgsV1, name).offset
        for name, _ctype in NativeExecLaunchArgsV1._fields_
    }
    if offsets != {
        "clone_args": 0,
        "creator_pid_cell_mapping": 8,
        "pid_cell_mapping_bytes": 16,
        "creator_pid_cell_fd": 24,
        "one_shot_cgroup_grant_fd": 32,
        "child_gate_fd": 40,
        "parent_edge": 48,
        "cell_withdrawn_frame": 56,
        "cell_withdrawn_frame_bytes": 64,
        "gate_ready_frame": 72,
        "gate_ready_frame_bytes": 80,
        "release_frame": 88,
        "release_frame_bytes": 96,
        "supervisor_executable_fd": 104,
        "supervisor_argv": 112,
        "supervisor_envp": 120,
    }:
        _fail("nested-creator exec-birth launch offsets changed")
    return {
        "source_sha256": SOURCE_SHA256,
        "text_sha256": X86_64_TEXT_SHA256,
        "text_byte_count": X86_64_TEXT_BYTE_COUNT,
        "clone_args_size": CLONE_ARGS_SIZE,
        "clone_flags": REQUIRED_CLONE_FLAGS,
        "launch_args_size": ctypes.sizeof(NativeExecLaunchArgsV1),
        "parent_edge_size": ctypes.sizeof(NativeParentEdgeV1),
        "parent_required_success_bits": PARENT_EDGE_REQUIRED_SUCCESS_BITS,
        "role_elf_sha256": role_v1.ELF_SHA256,
        "role_elf_byte_count": role_v1.ELF_BYTE_COUNT,
        "release_frame_max_bytes": MAX_RELEASE_FRAME_BYTES,
        "child_gate_source_fd_minimum": CHILD_GATE_SOURCE_FD_MINIMUM,
        "executable_source_fd_minimum": EXECUTABLE_SOURCE_FD_MINIMUM,
        "runtime_toolchain_invocation_present": False,
        "actual_process_birth_present": False,
        "two_birth_prefix_authority_present": False,
    }


def load_nested_creator_supervisor_exec_birth_entry_v1() -> Any:
    """Return the sole verified GIL-retaining W^X entry; invoke nothing here."""

    global _TRAMPOLINE_FUNCTION, _TRAMPOLINE_MEMORY
    verify_nested_creator_supervisor_exec_birth_native_image_v1()
    if _TRAMPOLINE_FUNCTION is not None:
        if _TRAMPOLINE_MEMORY is None or _TRAMPOLINE_MEMORY[:] != X86_64_TEXT_BYTES:
            _fail("nested-creator exec-birth mapped image changed")
        return _TRAMPOLINE_FUNCTION
    memory = mmap.mmap(
        -1,
        len(X86_64_TEXT_BYTES),
        flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
        prot=mmap.PROT_READ | mmap.PROT_WRITE,
    )
    memory.write(X86_64_TEXT_BYTES)
    address = ctypes.addressof(ctypes.c_char.from_buffer(memory))
    _LIBC.mprotect.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int)
    _LIBC.mprotect.restype = ctypes.c_int
    if _LIBC.mprotect(
        ctypes.c_void_p(address),
        ctypes.c_size_t(len(X86_64_TEXT_BYTES)),
        mmap.PROT_READ | mmap.PROT_EXEC,
    ) != 0:
        error = ctypes.get_errno()
        memory.close()
        raise ConstructionK7H1NestedCreatorSupervisorExecBirthNativeV1Error(
            f"nested-creator exec-birth W^X transition failed with errno {error}"
        )
    function_type = ctypes.PYFUNCTYPE(
        ctypes.c_long, ctypes.POINTER(NativeExecLaunchArgsV1)
    )
    _TRAMPOLINE_MEMORY = memory
    _TRAMPOLINE_FUNCTION = function_type(address)
    return _TRAMPOLINE_FUNCTION


__all__ = (
    "CHILD_GATE_SOURCE_FD_MINIMUM",
    "CLONE_ARGS_SIZE",
    "CloneArgsV1",
    "ConstructionK7H1NestedCreatorSupervisorExecBirthNativeV1Error",
    "EXECUTABLE_SOURCE_FD_MINIMUM",
    "MAX_RELEASE_FRAME_BYTES",
    "NativeExecLaunchArgsV1",
    "NativeParentEdgeV1",
    "PARENT_EDGE_REQUIRED_REJECTION_BITS",
    "PARENT_EDGE_REQUIRED_SUCCESS_BITS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS",
    "REQUIRED_CLONE_FLAGS",
    "SCHEMA_VERSION",
    "SOURCE_PATH",
    "SOURCE_SHA256",
    "X86_64_TEXT_BYTE_COUNT",
    "X86_64_TEXT_BYTES",
    "X86_64_TEXT_SHA256",
    "load_nested_creator_supervisor_exec_birth_entry_v1",
    "verify_nested_creator_supervisor_exec_birth_native_image_v1",
)
