from __future__ import annotations

import ctypes
import errno
import hashlib
import mmap
import os
from pathlib import Path
import shutil
import signal
import subprocess

import pytest

from acfqp import construction_k7_h1_supervisor_birth_native_v1 as native_v1


def test_native_claims_stop_before_prebinding_or_birth() -> None:
    for name in (
        "AUDITED_NATIVE_TRAMPOLINE_SOURCE_PRESENT",
        "RELOCATION_FREE_TEXT_IMAGE_PRESENT",
        "PYFUNCTYPE_GIL_RETAINING_ENTRY_PRESENT",
        "W_X_MAPPING_PRESENT",
        "PARENT_WITHDRAWAL_EDGE_ABI_PRESENT",
        "CHILD_RAW_SYSCALL_ONLY_PROTOCOL_PRESENT",
        "PARENT_GATE_COPY_WRAPPER_OBLIGATION_FROZEN",
    ):
        assert getattr(native_v1, name) is True
    for name in (
        "PRE_RUNNING_SOURCE_PREBINDING_PRESENT",
        "PERMIT_CONSUMPTION_PRESENT",
        "CLONE_SYSCALL_PERFORMED",
        "ACTUAL_PROCESS_BIRTH_PRESENT",
        "SHARED_PID_CELL_AUTHORITY_PRESENT",
        "PIDFD_ESCROW_PRESENT",
        "CGROUP_MEMBERSHIP_OBSERVATION_PRESENT",
        "PROCESS_DEATH_OR_REAP_PRESENT",
        "PEAK_READ_PRESENT",
        "ACTUAL_OBSERVED_E3_V2_IMPLEMENTATION_SLICE1_PRESENT",
        "ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT",
        "PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT",
        "FQ11_COUNTER_COMPLETENESS_PRESENT",
        "FORMAL_COUNTER_RECORDS_ISSUED",
        "FORMAL_WORK_VECTOR_ISSUED",
        "FORMAL_COMPARISON_VECTOR_ISSUED",
        "FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED",
        "CURRENT_ACCESS_AUTHORITY_PRESENT",
        "FORMAL_V7_AUTHORITY_PRESENT",
        "OFFICIAL_EXECUTION_ALLOWED",
    ):
        assert getattr(native_v1, name) is False
    assert native_v1.OFFICIAL_SCALAR_COST is None
    assert native_v1.OFFICIAL_N_BREAK_EVEN is None
    assert native_v1.COUNTER_COMPLETENESS_GATE == "NOT_RUN"
    assert native_v1.WORKLOAD_ECONOMICS_GATE == "NOT_RUN"


def test_frozen_source_text_hash_and_abi_are_exact() -> None:
    document = native_v1.verify_supervisor_birth_native_image_v1()
    assert document == {
        "source_sha256": native_v1.SOURCE_SHA256,
        "text_sha256": native_v1.X86_64_TEXT_SHA256,
        "text_byte_count": 891,
        "clone_args_size": 88,
        "clone_flags": 0x300101000,
        "launch_args_size": 104,
        "parent_edge_size": 32,
        "release_frame_max_bytes": 64,
        "release_endpoint_so_passcred": False,
        "release_ancillary_grammar": "NONE",
        "release_recvmsg_control_cap_bytes": 64,
        "release_recvmsg_call_flags": 0x40000000,
        "release_allowed_msg_flags_mask": 0x40000080,
        "release_rejected_truncation_flags_mask": 0x28,
        "future_wrapper_parent_gate_copy_required": True,
        "future_wrapper_parent_gate_copy_present": False,
        "future_wrapper_child_gate_source_close_required": True,
        "future_wrapper_child_gate_source_fd_minimum": 4,
        "runtime_toolchain_invocation_present": False,
        "actual_process_birth_present": False,
    }
    assert native_v1.CloneArgsV1.parent_tid.offset == 24
    assert native_v1.CloneArgsV1.cgroup.offset == 80
    assert native_v1.NativeLaunchArgsV1.parent_edge.offset == 48
    assert native_v1.NativeLaunchArgsV1.release_frame_bytes.offset == 96
    assert not hasattr(native_v1.NativeLaunchArgsV1, "child_escrow_fd")
    assert native_v1.PARENT_EDGE_REQUIRED_SUCCESS_BITS == 59
    assert native_v1.PARENT_EDGE_REQUIRED_REJECTION_BITS == 61
    assert native_v1.FUTURE_WRAPPER_PARENT_GATE_COPY_REQUIRED is True
    assert native_v1.FUTURE_WRAPPER_PARENT_GATE_COPY_PRESENT is False


def test_checked_in_source_has_only_child_gate_and_parent_withdrawal_edges() -> None:
    source = native_v1._SOURCE_PATH.read_bytes()  # noqa: SLF001
    assert hashlib.sha256(source).hexdigest() == native_v1.SOURCE_SHA256
    # No child pidfd_open/sendmsg/SCM path remains.  The only child descriptor
    # normalization is gate -> FD3 followed by close_range(4, UINT_MAX, 0).
    assert b"pidfd_open" not in source
    assert b"sendmsg" not in source
    assert b"$434" not in source
    assert b"$46" not in source
    assert b"dup3(child_gate_fd, 3, 0)" in source
    assert b"close_range(4, UINT_MAX, 0)" in source
    assert b"SOCK_SEQPACKET" in source
    assert b"recvmsg" in source
    assert b"MSG_CMSG_CLOEXEC" in source
    assert b"MSG_EOR" in source
    assert b"MSG_TRUNC" in source
    assert b"MSG_CTRUNC" in source
    assert b"SO_PASSCRED disabled" in source
    assert b"SCM_RIGHTS" in source
    assert b"SCM_CREDENTIALS" in source
    assert b"msg_controllen" in source
    assert b"one-shot cgroup grant canonical FD closed" in source


def test_private_mapping_is_wx_and_uses_pyfunctype_without_executing_clone() -> None:
    entry = native_v1._native_supervisor_birth_entry_v1()  # noqa: SLF001
    assert entry is native_v1._native_supervisor_birth_entry_v1()  # noqa: SLF001
    assert native_v1._TRAMPOLINE_MEMORY is not None  # noqa: SLF001
    assert native_v1._TRAMPOLINE_MEMORY[:] == native_v1.X86_64_TEXT_BYTES  # noqa: SLF001
    assert isinstance(entry, ctypes._CFuncPtr)  # noqa: SLF001
    # No public entry can invoke the machine image.
    assert "_native_supervisor_birth_entry_v1" not in native_v1.__all__


def _invoke_guaranteed_clone_rejection(
    *, creator_mapping: int, creator_fd: int, grant_fd: int, gate_fd: int
) -> tuple[int, native_v1.NativeParentEdgeV1]:
    edge = native_v1.NativeParentEdgeV1()
    launch = native_v1.NativeLaunchArgsV1(
        clone_args=0,  # clone3(NULL, 88) is guaranteed not to create a child.
        creator_pid_cell_mapping=creator_mapping,
        pid_cell_mapping_bytes=mmap.PAGESIZE,
        creator_pid_cell_fd=creator_fd,
        one_shot_cgroup_grant_fd=grant_fd,
        child_gate_fd=gate_fd,
        parent_edge=ctypes.addressof(edge),
        cell_withdrawn_frame=0,
        cell_withdrawn_frame_bytes=0,
        gate_ready_frame=0,
        gate_ready_frame_bytes=0,
        release_frame=0,
        release_frame_bytes=0,
    )
    blocked = set(signal.valid_signals()) - {signal.SIGKILL, signal.SIGSTOP}
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
    try:
        result = int(
            native_v1._native_supervisor_birth_entry_v1()(  # noqa: SLF001
                ctypes.byref(launch)
            )
        )
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)
    return result, edge


@pytest.mark.skipif(
    not callable(getattr(os, "memfd_create", None)),
    reason="memfd_create is unavailable",
)
def test_guaranteed_clone_rejection_withdraws_mapping_cell_fd_and_grant() -> None:
    sealer_fd = os.memfd_create(
        "acfqp-b2c-native-reject",
        os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
    )
    os.ftruncate(sealer_fd, mmap.PAGESIZE)
    creator_fd = os.dup(sealer_fd)
    grant_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    gate_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    libc = native_v1._LIBC  # noqa: SLF001
    libc.mmap.argtypes = (
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_long,
    )
    libc.mmap.restype = ctypes.c_void_p
    address = int(
        libc.mmap(
            None,
            mmap.PAGESIZE,
            mmap.PROT_READ | mmap.PROT_WRITE,
            mmap.MAP_SHARED,
            creator_fd,
            0,
        )
    )
    assert address != ctypes.c_void_p(-1).value
    try:
        result, edge = _invoke_guaranteed_clone_rejection(
            creator_mapping=address,
            creator_fd=creator_fd,
            grant_fd=grant_fd,
            gate_fd=gate_fd,
        )
        assert result == edge.clone_result < 0
        assert edge.status_bits == native_v1.PARENT_EDGE_REQUIRED_REJECTION_BITS
        assert edge.first_cleanup_error == 0
        assert edge.reserved_zero == 0
        for descriptor in (creator_fd, grant_fd):
            with pytest.raises(OSError) as caught:
                os.fstat(descriptor)
            assert caught.value.errno == errno.EBADF
        libc.mincore.argtypes = (
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_ubyte),
        )
        libc.mincore.restype = ctypes.c_int
        vector = (ctypes.c_ubyte * 1)()
        ctypes.set_errno(0)
        assert libc.mincore(address, mmap.PAGESIZE, vector) == -1
        assert ctypes.get_errno() == errno.ENOMEM
    finally:
        os.close(gate_fd)
        os.close(sealer_fd)


def test_guaranteed_clone_rejection_preserves_cleanup_error_separately() -> None:
    creator_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    grant_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    gate_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    try:
        result, edge = _invoke_guaranteed_clone_rejection(
            creator_mapping=1,  # guaranteed unaligned munmap EINVAL
            creator_fd=creator_fd,
            grant_fd=grant_fd,
            gate_fd=gate_fd,
        )
        assert edge.clone_result < 0
        assert result < -30000 and result != edge.clone_result
        assert edge.first_cleanup_error == -errno.EINVAL
        assert edge.status_bits == (
            native_v1.PARENT_EDGE_CLONE_ATTEMPTED
            | native_v1.PARENT_EDGE_CLONE_REJECTED
            | native_v1.PARENT_EDGE_CREATOR_FD_CLOSED
            | native_v1.PARENT_EDGE_CGROUP_GRANT_FD_CLOSED
        )
        for descriptor in (creator_fd, grant_fd):
            with pytest.raises(OSError) as caught:
                os.fstat(descriptor)
            assert caught.value.errno == errno.EBADF
    finally:
        os.close(gate_fd)


@pytest.mark.skipif(
    any(
        shutil.which(tool) is None
        for tool in ("cc", "objcopy", "readelf", "objdump")
    ),
    reason="static native reassembly toolchain is unavailable",
)
def test_checked_in_source_reassembles_to_exact_relocation_free_text(
    tmp_path: Path,
) -> None:
    object_path = tmp_path / "supervisor-birth.o"
    text_path = tmp_path / "supervisor-birth.text"
    subprocess.run(
        ["cc", "-c", str(native_v1._SOURCE_PATH), "-o", str(object_path)],  # noqa: SLF001
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    relocations = subprocess.run(
        ["readelf", "-r", str(object_path)],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    assert b"There are no relocations in this file." in relocations
    disassembly = subprocess.run(
        ["objdump", "-d", str(object_path)],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    assert disassembly.count(b"\tsyscall") == 14
    assert b"\tcall" not in disassembly
    assert b"\tsysenter" not in disassembly
    assert b"\tint " not in disassembly
    subprocess.run(
        [
            "objcopy",
            "-O",
            "binary",
            "--only-section=.text",
            str(object_path),
            str(text_path),
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    rebuilt = text_path.read_bytes()
    assert rebuilt == native_v1.X86_64_TEXT_BYTES
    assert len(rebuilt) == native_v1.X86_64_TEXT_BYTE_COUNT
    assert hashlib.sha256(rebuilt).hexdigest() == native_v1.X86_64_TEXT_SHA256
