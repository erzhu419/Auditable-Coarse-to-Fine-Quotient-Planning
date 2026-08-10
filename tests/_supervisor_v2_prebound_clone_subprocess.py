from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import socket
import sys

from acfqp import construction_k7_h1_nested_creator_supervisor_exec_birth_native_v1 as native_v1
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v2 as role_v2
from acfqp import construction_k7_h1_supervisor_v2_prebound_clone_v1 as binding


def main() -> None:
    pid_cell = os.memfd_create(
        "acfqp-v20-fork-pid-cell", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING
    )
    os.ftruncate(pid_cell, 4096)
    parent, child = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC
    )
    parent.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    child.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    role_fd = role_v2.create_sealed_nested_creator_supervisor_memfd_v2()
    transferred_gate = child.detach()
    handle = binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
        creator_pid_cell_fd=pid_cell,
        child_gate_fd=transferred_gate,
        child_gate_peer_fd=parent.fileno(),
        supervisor_executable_fd=role_fd,
        cell_withdrawn_frame=b"ACFQP:V20:CELL",
        gate_ready_frame=b"ACFQP:V20:READY",
        release_frame=b"ACFQP:V20:RELEASE",
    )
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    child_pid = os.fork()
    if child_pid == 0:
        os.close(read_fd)
        try:
            binding.verify_h1_supervisor_v2_prebound_native_clone_v1(handle)
        except binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error:
            outcome = b"INVALIDATED"
        else:  # pragma: no cover - attack detector
            outcome = b"FORGED_LIVE"
        os.write(write_fd, outcome)
        os.close(write_fd)
        os._exit(0)
    os.close(write_fd)
    child_outcome = os.read(read_fd, 64).decode("ascii")
    os.close(read_fd)
    waited_pid, status = os.waitpid(child_pid, 0)
    parent_document = binding.verify_h1_supervisor_v2_prebound_native_clone_v1(
        handle
    )
    cancellation = binding.cancel_h1_supervisor_v2_prebound_native_clone_v1(
        handle
    )
    caller_fds_live = []
    for descriptor in (pid_cell, transferred_gate, role_fd):
        try:
            fcntl.fcntl(descriptor, fcntl.F_GETFD)
        except OSError:
            caller_fds_live.append(False)
        else:
            caller_fds_live.append(True)
    for descriptor in (pid_cell, transferred_gate, role_fd):
        os.close(descriptor)
    parent.close()
    print(
        json.dumps(
            {
                "child_outcome": child_outcome,
                "waited_pid_matches": waited_pid == child_pid,
                "child_exit_status": os.waitstatus_to_exitcode(status),
                "parent_state": parent_document["state"],
                "parent_capsule_id": parent_document[
                    "prebound_native_edge_capsule_id"
                ],
                "caller_fds_live_after_cancel": all(caller_fds_live),
                "cancellation_closed": cancellation[
                    "all_capsule_owned_resources_closed"
                ],
            },
            sort_keys=True,
        )
    )


def rejection_main(mode: str) -> None:
    pid_cell = os.memfd_create(
        "acfqp-v20-rejection-pid-cell", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING
    )
    os.ftruncate(pid_cell, 4096)
    parent, child = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC
    )
    parent.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    child.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    role_fd = role_v2.create_sealed_nested_creator_supervisor_memfd_v2()
    if mode == "rx-preload":
        native_v1.load_nested_creator_supervisor_exec_birth_entry_v1()
    elif mode == "source-mutation":
        source = Path(binding.__file__).resolve(strict=True)
        source.write_bytes(source.read_bytes() + b"\n# injected post-import mutation\n")
    else:  # pragma: no cover - helper contract
        raise RuntimeError(f"unknown rejection mode: {mode}")
    try:
        binding.prepare_h1_supervisor_v2_prebound_native_clone_v1(
            creator_pid_cell_fd=pid_cell,
            child_gate_fd=child.fileno(),
            child_gate_peer_fd=parent.fileno(),
            supervisor_executable_fd=role_fd,
            cell_withdrawn_frame=b"A",
            gate_ready_frame=b"B",
            release_frame=b"C",
        )
    except binding.ConstructionK7H1SupervisorV2PreboundCloneV1Error:
        outcome = "REJECTED_BEFORE_CAPSULE"
    else:  # pragma: no cover - attack detector
        outcome = "FORGED_CAPSULE"
    caller_fds_live = []
    for descriptor in (pid_cell, child.fileno(), parent.fileno(), role_fd):
        try:
            fcntl.fcntl(descriptor, fcntl.F_GETFD)
        except OSError:
            caller_fds_live.append(False)
        else:
            caller_fds_live.append(True)
    child.close()
    parent.close()
    os.close(pid_cell)
    os.close(role_fd)
    print(
        json.dumps(
            {
                "outcome": outcome,
                "live_registry_empty": not binding._LIVE,  # noqa: SLF001
                "caller_fds_remained_live": all(caller_fds_live),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    if len(sys.argv) == 2:
        rejection_main(sys.argv[1])
    else:
        main()
