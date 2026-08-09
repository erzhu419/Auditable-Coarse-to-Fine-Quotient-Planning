"""Audited native primitive for the future H1 B2-C SUPERVISOR birth.

This module freezes the checked-in Linux x86-64 assembly source, the exact
relocation-free ``.text`` image derived from it, the clone/launch ABI, and a
private W^X ``PYFUNCTYPE`` mapping.  It deliberately exposes no process-birth
API and performs no clone, cgroup mutation, pidfd escrow, or cleanup.

The build toolchain is test-only.  Importing or using this module never calls
an assembler, compiler, subprocess, or helper process.
"""

from __future__ import annotations

import ctypes
import hashlib
import mmap
from pathlib import Path
import platform
from typing import Any, NoReturn


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-B2-C-NATIVE"
PROFILE_KEY = "construction_k7_h1_supervisor_birth_native_v1"
READINESS = "AUDITED_NATIVE_PRIMITIVE_ONLY"

AUDITED_NATIVE_TRAMPOLINE_SOURCE_PRESENT = True
RELOCATION_FREE_TEXT_IMAGE_PRESENT = True
PYFUNCTYPE_GIL_RETAINING_ENTRY_PRESENT = True
W_X_MAPPING_PRESENT = True
PARENT_WITHDRAWAL_EDGE_ABI_PRESENT = True
CHILD_RAW_SYSCALL_ONLY_PROTOCOL_PRESENT = True
PARENT_GATE_COPY_WRAPPER_OBLIGATION_FROZEN = True

PRE_RUNNING_SOURCE_PREBINDING_PRESENT = False
PERMIT_CONSUMPTION_PRESENT = False
CLONE_SYSCALL_PERFORMED = False
ACTUAL_PROCESS_BIRTH_PRESENT = False
SHARED_PID_CELL_AUTHORITY_PRESENT = False
PIDFD_ESCROW_PRESENT = False
CGROUP_MEMBERSHIP_OBSERVATION_PRESENT = False
PROCESS_DEATH_OR_REAP_PRESENT = False
PEAK_READ_PRESENT = False
ACTUAL_OBSERVED_E3_V2_IMPLEMENTATION_SLICE1_PRESENT = False
ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT = False
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

# The native primitive receives only the child gate source FD.  A later
# reviewed wrapper must create and retain a distinct parent endpoint before
# entry, keep SO_PASSCRED disabled on the child endpoint, prove the child
# source FD is greater than three, and close that source in the parent after
# the native edge returns.  None of that wrapper authority is implemented
# here.
FUTURE_WRAPPER_PARENT_GATE_COPY_REQUIRED = True
FUTURE_WRAPPER_PARENT_GATE_COPY_PRESENT = False
FUTURE_WRAPPER_CHILD_GATE_SOURCE_CLOSE_REQUIRED = True
FUTURE_WRAPPER_CHILD_GATE_SOURCE_FD_MINIMUM = 4

CLONE_PIDFD = 0x00001000
CLONE_PARENT_SETTID = 0x00100000
CLONE_CLEAR_SIGHAND = 0x100000000
CLONE_INTO_CGROUP = 0x200000000
REQUIRED_CLONE_FLAGS = (
    CLONE_PIDFD
    | CLONE_PARENT_SETTID
    | CLONE_CLEAR_SIGHAND
    | CLONE_INTO_CGROUP
)
CLONE_ARGS_SIZE = 88
MAX_RELEASE_FRAME_BYTES = 64
RELEASE_ENDPOINT_SO_PASSCRED = False
RELEASE_ANCILLARY_GRAMMAR = "NONE"
RELEASE_RECVMSG_CONTROL_CAP_BYTES = 64
RELEASE_RECVMSG_CALL_FLAGS = 0x40000000  # MSG_CMSG_CLOEXEC
RELEASE_ALLOWED_MSG_FLAGS_MASK = 0x40000080  # MSG_CMSG_CLOEXEC | MSG_EOR
RELEASE_REJECTED_TRUNCATION_FLAGS_MASK = 0x28  # MSG_TRUNC | MSG_CTRUNC

PARENT_EDGE_CLONE_ATTEMPTED = 1
PARENT_EDGE_CLONE_SUCCEEDED = 2
PARENT_EDGE_CLONE_REJECTED = 4
PARENT_EDGE_CREATOR_MAPPING_WITHDRAWN = 8
PARENT_EDGE_CREATOR_FD_CLOSED = 16
PARENT_EDGE_CGROUP_GRANT_FD_CLOSED = 32
PARENT_EDGE_REQUIRED_SUCCESS_BITS = (
    PARENT_EDGE_CLONE_ATTEMPTED
    | PARENT_EDGE_CLONE_SUCCEEDED
    | PARENT_EDGE_CREATOR_MAPPING_WITHDRAWN
    | PARENT_EDGE_CREATOR_FD_CLOSED
    | PARENT_EDGE_CGROUP_GRANT_FD_CLOSED
)
PARENT_EDGE_REQUIRED_REJECTION_BITS = (
    PARENT_EDGE_CLONE_ATTEMPTED
    | PARENT_EDGE_CLONE_REJECTED
    | PARENT_EDGE_CREATOR_MAPPING_WITHDRAWN
    | PARENT_EDGE_CREATOR_FD_CLOSED
    | PARENT_EDGE_CGROUP_GRANT_FD_CLOSED
)

_SOURCE_PATH = (
    Path(__file__).resolve(strict=True).parent
    / "native"
    / "h1_actual_observed_supervisor_birth_x86_64_v1.S"
).resolve(strict=True)
SOURCE_SHA256 = "f776b3be42854317944e5eb7a5fe569c24232fe48e883d31be8b669ea5265d7a"

# Exact relocation-free .text emitted by GNU as 2.38 from the checked-in
# source.  The acceptance test independently reassembles the source and
# compares the extracted .text byte-for-byte; production import never does.
X86_64_TEXT_BYTES = bytes.fromhex(
    "41544155415641574989fc4d8b7c243049c7470801000000498b3c2448c7c658"
    "00000048c7c0b30100000f054885c00f84ab0000004989c549890749c7c60000"
    "00004885c0780749834f0802eb0549834f080448c7c00b000000498b7c240849"
    "8b7424100f054885c0780749834f0808eb074989c64989471048c7c003000000"
    "498b7c24180f054885c0780749834f0810eb0c4d85f675074989c64989471048"
    "c7c003000000498b7c24200f054885c0780749834f0820eb0c4d85f675074989"
    "c6498947104d85f6740e4c89f0482d30750000e99a0200004c89e8e992020000"
    "48c7c00b000000498b7c2408498b7424100f054885c00f881a02000048c7c003"
    "000000498b7c24180f054885c00f880c02000048c7c024010000498b7c242848"
    "c7c6030000004831d20f054885c00f88f401000048c7c0b401000048c7c70400"
    "000048beffffffff000000004831d20f054885c00f88d701000048c7c02c0000"
    "0048c7c703000000498b742438498b54244049c7c2004000004d31c04d31c90f"
    "054885c00f88b0010000493b4424400f85a501000048c7c02c00000048c7c703"
    "000000498b742448498b54245049c7c2004000004d31c04d31c90f054885c00f"
    "887e010000493b4424500f8573010000498b4424604883f8400f876d01000048"
    "ffc04881ecd00000004989c5488d3c244831c048c7c11a000000f348ab488d04"
    "2448894424484c896c2450488d442448488944246848c744247001000000488d84"
    "2490000000488944247848c78424800000004000000048c7c02f00000048c7c7"
    "03000000488d74245848c7c2000000400f054885c00f889f000000493b442460"
    "0f8594000000837c2460000f85890000004883bc248000000000757e8b842488"
    "00000089c283e2287570257fffffbf75694831c9493b4c24607419480fb6040c"
    "498b742458480fb6140e4839d0755448ffc1ebe048c7c02c00000048c7c70300"
    "00004889e6498b54246049c7c2004000004d31c04d31c90f054885c0782e493b"
    "44246075274881c4d00000004831ff48c7c0e70000000f050f0b4881c4d00000"
    "00eb484881c4d0000000eb484881c4d0000000eb4848c7c778000000eb4848c7"
    "c779000000eb3f48c7c77a000000eb3648c7c77b000000eb2d48c7c77c000000"
    "eb2448c7c77d000000eb1b48c7c77e000000eb1248c7c77f000000eb0948c7"
    "c780000000eb0048c7c0e70000000f"
    "050f0b415f415e415d415cc3"
)
X86_64_TEXT_BYTE_COUNT = 891
X86_64_TEXT_SHA256 = "c88a4c6cfbec2b169cd7d755c5ada80e802343dced9b02911776a6b1a51a6186"


class ConstructionK7H1SupervisorBirthNativeV1Error(ValueError):
    """The frozen source, image, ABI, or private W^X mapping changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1SupervisorBirthNativeV1Error(message)


class CloneArgsV1(ctypes.Structure):
    """Linux ``struct clone_args`` through its cgroup field."""

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


class NativeLaunchArgsV1(ctypes.Structure):
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
    ]


_LIBC = ctypes.CDLL(None, use_errno=True)
_TRAMPOLINE_MEMORY: mmap.mmap | None = None
_TRAMPOLINE_FUNCTION: Any = None


def verify_supervisor_birth_native_image_v1() -> dict[str, Any]:
    """Revalidate only checked-in bytes and the frozen ABI; execute nothing."""

    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        _fail("B2-C native primitive is registered only for Linux x86-64")
    try:
        source = _SOURCE_PATH.read_bytes()
    except OSError as error:
        raise ConstructionK7H1SupervisorBirthNativeV1Error(
            "B2-C native source is unavailable"
        ) from error
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        _fail("B2-C native source digest changed")
    if (
        len(X86_64_TEXT_BYTES) != X86_64_TEXT_BYTE_COUNT
        or hashlib.sha256(X86_64_TEXT_BYTES).hexdigest() != X86_64_TEXT_SHA256
    ):
        _fail("B2-C embedded native text image changed")
    if ctypes.sizeof(CloneArgsV1) != CLONE_ARGS_SIZE:
        _fail("B2-C clone_args ABI changed")
    if ctypes.sizeof(NativeParentEdgeV1) != 32:
        _fail("B2-C native parent-edge ABI changed")
    if ctypes.sizeof(NativeLaunchArgsV1) != 104:
        _fail("B2-C native launch ABI changed")
    offsets = {
        name: getattr(NativeLaunchArgsV1, name).offset
        for name, _ctype in NativeLaunchArgsV1._fields_
    }
    expected_offsets = {
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
    }
    if offsets != expected_offsets:
        _fail("B2-C native launch offsets changed")
    return {
        "source_sha256": SOURCE_SHA256,
        "text_sha256": X86_64_TEXT_SHA256,
        "text_byte_count": X86_64_TEXT_BYTE_COUNT,
        "clone_args_size": CLONE_ARGS_SIZE,
        "clone_flags": REQUIRED_CLONE_FLAGS,
        "launch_args_size": ctypes.sizeof(NativeLaunchArgsV1),
        "parent_edge_size": ctypes.sizeof(NativeParentEdgeV1),
        "release_frame_max_bytes": MAX_RELEASE_FRAME_BYTES,
        "release_endpoint_so_passcred": RELEASE_ENDPOINT_SO_PASSCRED,
        "release_ancillary_grammar": RELEASE_ANCILLARY_GRAMMAR,
        "release_recvmsg_control_cap_bytes": RELEASE_RECVMSG_CONTROL_CAP_BYTES,
        "release_recvmsg_call_flags": RELEASE_RECVMSG_CALL_FLAGS,
        "release_allowed_msg_flags_mask": RELEASE_ALLOWED_MSG_FLAGS_MASK,
        "release_rejected_truncation_flags_mask": (
            RELEASE_REJECTED_TRUNCATION_FLAGS_MASK
        ),
        "future_wrapper_parent_gate_copy_required": (
            FUTURE_WRAPPER_PARENT_GATE_COPY_REQUIRED
        ),
        "future_wrapper_parent_gate_copy_present": (
            FUTURE_WRAPPER_PARENT_GATE_COPY_PRESENT
        ),
        "future_wrapper_child_gate_source_close_required": (
            FUTURE_WRAPPER_CHILD_GATE_SOURCE_CLOSE_REQUIRED
        ),
        "future_wrapper_child_gate_source_fd_minimum": (
            FUTURE_WRAPPER_CHILD_GATE_SOURCE_FD_MINIMUM
        ),
        "runtime_toolchain_invocation_present": False,
        "actual_process_birth_present": False,
    }


def _native_supervisor_birth_entry_v1() -> Any:
    """Return the private GIL-retaining W^X entry; never invoke it here."""

    global _TRAMPOLINE_FUNCTION, _TRAMPOLINE_MEMORY
    verify_supervisor_birth_native_image_v1()
    if _TRAMPOLINE_FUNCTION is not None:
        if _TRAMPOLINE_MEMORY is None or _TRAMPOLINE_MEMORY[:] != X86_64_TEXT_BYTES:
            _fail("B2-C mapped native image changed")
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
        raise ConstructionK7H1SupervisorBirthNativeV1Error(
            f"B2-C W^X transition failed with errno {error}"
        )
    function_type = ctypes.PYFUNCTYPE(
        ctypes.c_long,
        ctypes.POINTER(NativeLaunchArgsV1),
    )
    _TRAMPOLINE_MEMORY = memory
    _TRAMPOLINE_FUNCTION = function_type(address)
    return _TRAMPOLINE_FUNCTION


__all__ = tuple(
    sorted(
        name
        for name in globals()
        if (
            name.isupper()
            or name.startswith("CloneArgs")
            or name.startswith("Native")
            or name.startswith("ConstructionK7")
            or name == "verify_supervisor_birth_native_image_v1"
        )
        and not name.startswith("_")
    )
)
