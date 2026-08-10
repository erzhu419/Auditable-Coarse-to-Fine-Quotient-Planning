from __future__ import annotations

import array
import ctypes
import fcntl
import json
import os
import select
import signal
import socket
import struct
import sys
import time

from acfqp import construction_k7_h1_nested_creator_leaf_roles_native_v2 as role


def _receive(endpoint: socket.socket) -> tuple[role.LeafRoleFrameV2, tuple[int, int, int]]:
    raw, ancillary, flags, address = endpoint.recvmsg(
        role.FRAME_BYTES + 1,
        socket.CMSG_SPACE(struct.calcsize("3i")) + socket.CMSG_SPACE(4),
    )
    if flags != 0 or len(raw) != role.FRAME_BYTES:
        raise RuntimeError(
            f"leaf V2 packet boundary changed: flags={flags} "
            f"address={address!r} bytes={len(raw)}"
        )
    credentials: list[tuple[int, int, int]] = []
    rights: list[int] = []
    for level, kind, payload in ancillary:
        if level != socket.SOL_SOCKET:
            raise RuntimeError("leaf V2 emitted non-SOL_SOCKET ancillary data")
        if kind == socket.SCM_CREDENTIALS:
            credentials.append(struct.unpack("3i", payload))
        elif kind == socket.SCM_RIGHTS:
            values = array.array("i")
            values.frombytes(payload[: len(payload) - len(payload) % values.itemsize])
            rights.extend(values)
        else:
            raise RuntimeError("leaf V2 emitted unknown ancillary data")
    for descriptor in rights:
        os.close(descriptor)
    if len(credentials) != 1 or rights:
        raise RuntimeError("leaf V2 lifecycle ancillary data changed")
    return role.LeafRoleFrameV2.from_bytes(raw), credentials[0]


def _exec_leaf(endpoint: socket.socket, image_fd: int, role_name: str) -> None:
    executable_fd = fcntl.fcntl(image_fd, fcntl.F_DUPFD, 100)
    os.set_inheritable(executable_fd, True)
    endpoint_fd = endpoint.detach()
    if endpoint_fd != role.CONTROL_FD:
        os.dup2(endpoint_fd, role.CONTROL_FD, inheritable=True)
        os.close(endpoint_fd)
    else:
        os.set_inheritable(role.CONTROL_FD, True)
    os.execve(
        f"/proc/self/fd/{executable_fd}",
        [f"acfqp-h1-{role_name.lower()}-role-v2"],
        {},
    )


def _spawn_through_parent_surrogate(
    role_name: str, guardian_endpoint: socket.socket, parent_endpoint: socket.socket,
    image_fd: int, *, wait_for_release: bool = False,
) -> tuple[int, int, int | None]:
    pid_read, pid_write = os.pipe()
    release_read, release_write = os.pipe() if wait_for_release else (-1, -1)
    parent_surrogate_pid = os.fork()
    if parent_surrogate_pid == 0:  # pragma: no cover - facts asserted by guardian
        try:
            guardian_endpoint.close()
            os.close(pid_read)
            if wait_for_release:
                os.close(release_write)
            leaf_pid = os.fork()
            if leaf_pid == 0:
                try:
                    os.close(pid_write)
                    if wait_for_release:
                        os.close(release_read)
                    _exec_leaf(parent_endpoint, image_fd, role_name)
                except BaseException:
                    os._exit(127)
            parent_endpoint.close()
            os.close(image_fd)
            os.write(pid_write, struct.pack("<q", leaf_pid))
            os.close(pid_write)
            if wait_for_release:
                if os.read(release_read, 1) != b"x":
                    os._exit(125)
                os.close(release_read)
                os._exit(0)
            waited, status = os.waitpid(leaf_pid, 0)
            os._exit(
                os.WEXITSTATUS(status)
                if waited == leaf_pid and os.WIFEXITED(status)
                else 128 + os.WTERMSIG(status)
                if waited == leaf_pid and os.WIFSIGNALED(status)
                else 126
            )
        except BaseException:
            os._exit(124)
    parent_endpoint.close()
    os.close(image_fd)
    os.close(pid_write)
    if wait_for_release:
        os.close(release_read)
    raw_pid = os.read(pid_read, 8)
    os.close(pid_read)
    if len(raw_pid) != 8:
        raise RuntimeError("parent surrogate did not report leaf pid")
    return (
        parent_surrogate_pid,
        struct.unpack("<q", raw_pid)[0],
        release_write if wait_for_release else None,
    )


def _success_or_command_attack(role_name: str, mode: str) -> dict[str, object]:
    guardian, parent_endpoint = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    guardian.settimeout(10)
    guardian.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    image_fd = role.create_sealed_nested_creator_leaf_role_memfd_v2(role_name)
    parent_surrogate_pid, leaf_pid, _ = _spawn_through_parent_surrogate(
        role_name, guardian, parent_endpoint, image_fd
    )
    parent_surrogate_reaped = False
    try:
        slot = role.ROLE_SLOTS[role_name]
        ready, ready_credential = _receive(guardian)
        expected_ready = role.LeafRoleFrameV2(
            role.OPCODES["ROLE_READY"], 0, bytes(16), leaf_pid, slot,
            parent_surrogate_pid,
        )
        if ready != expected_ready or ready_credential[0] != leaf_pid:
            raise RuntimeError("leaf V2 READY identity changed")
        leaf_open_fds_after_ready = sorted(
            int(name) for name in os.listdir(f"/proc/{leaf_pid}/fd")
        )
        go_nonce = bytes(range(16))
        go = role.LeafRoleFrameV2(
            role.OPCODES["ROLE_GO"], 1, go_nonce, leaf_pid, slot,
            parent_surrogate_pid,
        )
        sibling_pid = 0
        if mode == "WRONG_CREDENTIAL":
            sibling_pid = os.fork()
            if sibling_pid == 0:  # pragma: no cover
                try:
                    os._exit(0 if guardian.send(go.to_bytes()) == role.FRAME_BYTES else 2)
                except BaseException:
                    os._exit(3)
            waited, sibling_status = os.waitpid(sibling_pid, 0)
            if waited != sibling_pid or not os.WIFEXITED(sibling_status) or os.WEXITSTATUS(sibling_status):
                raise RuntimeError("credential attack sender failed")
            failure, failure_credential = _receive(guardian)
            waited_parent, parent_status = os.waitpid(parent_surrogate_pid, 0)
            parent_surrogate_reaped = True
            return {
                "role": role_name,
                "guardian_pid": os.getpid(),
                "parent_surrogate_pid": parent_surrogate_pid,
                "leaf_pid": leaf_pid,
                "sibling_pid": sibling_pid,
                "failure_opcode": failure.opcode,
                "failure_sequence": failure.sequence,
                "failure_status": failure.status,
                "failure_credential_pid": failure_credential[0],
                "parent_surrogate_exit_status": os.WEXITSTATUS(parent_status),
                "wrong_credential_rejected": waited_parent == parent_surrogate_pid,
            }
        if mode == "WRONG_SLOT":
            wrong_slot = (
                role.ROLE_SLOTS["BUSINESS"]
                if role_name == "WORKER"
                else role.ROLE_SLOTS["WORKER"]
            )
            wrong = role.LeafRoleFrameV2(
                role.OPCODES["ROLE_GO"], 1, go_nonce,
                leaf_pid, wrong_slot, parent_surrogate_pid,
            )
            if guardian.send(wrong.to_bytes()) != role.FRAME_BYTES:
                raise RuntimeError("wrong-slot attack short write")
            failure, failure_credential = _receive(guardian)
            waited_parent, parent_status = os.waitpid(parent_surrogate_pid, 0)
            parent_surrogate_reaped = True
            return {
                "role": role_name,
                "parent_surrogate_pid": parent_surrogate_pid,
                "leaf_pid": leaf_pid,
                "wrong_slot": wrong_slot,
                "failure_opcode": failure.opcode,
                "failure_sequence": failure.sequence,
                "failure_status": failure.status,
                "failure_credential_pid": failure_credential[0],
                "parent_surrogate_exit_status": os.WEXITSTATUS(parent_status),
                "wrong_slot_rejected": waited_parent == parent_surrogate_pid,
            }
        if mode in {"SCM_RIGHTS", "ANCILLARY_TRUNCATION"}:
            read_fd, write_fd = os.pipe()
            try:
                descriptor_count = 1 if mode == "SCM_RIGHTS" else 32
                ancillary = [(
                    socket.SOL_SOCKET,
                    socket.SCM_RIGHTS,
                    array.array("i", [read_fd] * descriptor_count),
                )]
                if guardian.sendmsg([go.to_bytes()], ancillary) != role.FRAME_BYTES:
                    raise RuntimeError("ancillary attack short write")
            finally:
                os.close(read_fd)
                os.close(write_fd)
            failure, failure_credential = _receive(guardian)
            waited_parent, parent_status = os.waitpid(parent_surrogate_pid, 0)
            parent_surrogate_reaped = True
            return {
                "role": role_name,
                "parent_surrogate_pid": parent_surrogate_pid,
                "leaf_pid": leaf_pid,
                "attack_mode": mode,
                "sent_rights_count": descriptor_count,
                "failure_opcode": failure.opcode,
                "failure_sequence": failure.sequence,
                "failure_status": failure.status,
                "failure_credential_pid": failure_credential[0],
                "parent_surrogate_exit_status": os.WEXITSTATUS(parent_status),
                "ancillary_rejected": waited_parent == parent_surrogate_pid,
            }
        if guardian.send(go.to_bytes()) != role.FRAME_BYTES:
            raise RuntimeError("leaf V2 GO short write")
        echo, echo_credential = _receive(guardian)
        expected_echo = role.LeafRoleFrameV2(
            role.OPCODES["ROLE_GO_ECHO"], 1, go_nonce, leaf_pid, slot,
            parent_surrogate_pid,
        )
        if echo != expected_echo:
            raise RuntimeError(f"leaf V2 GO echo changed: {echo!r} != {expected_echo!r}")
        shutdown_nonce = bytes(reversed(range(16)))
        shutdown = role.LeafRoleFrameV2(
            role.OPCODES["ROLE_SHUTDOWN"], 2, shutdown_nonce,
            leaf_pid, slot, parent_surrogate_pid,
        )
        if guardian.send(shutdown.to_bytes()) != role.FRAME_BYTES:
            raise RuntimeError("leaf V2 SHUTDOWN short write")
        bye, bye_credential = _receive(guardian)
        expected_bye = role.LeafRoleFrameV2(
            role.OPCODES["ROLE_BYE"], 2, shutdown_nonce, leaf_pid, slot,
            parent_surrogate_pid,
        )
        if bye != expected_bye:
            raise RuntimeError("leaf V2 BYE changed")
        waited_parent, parent_status = os.waitpid(parent_surrogate_pid, 0)
        parent_surrogate_reaped = True
        return {
            "role": role_name,
            "guardian_pid": os.getpid(),
            "parent_surrogate_pid": parent_surrogate_pid,
            "leaf_pid": leaf_pid,
            "ready_parent_pid": ready.parent_pid,
            "ready_role_slot": ready.role_slot,
            "sequences": [ready.sequence, echo.sequence, bye.sequence],
            "credential_pids": [ready_credential[0], echo_credential[0], bye_credential[0]],
            "parent_surrogate_exit_status": os.WEXITSTATUS(parent_status),
            "leaf_open_fds_after_ready": leaf_open_fds_after_ready,
            "direct_lifecycle_observed": waited_parent == parent_surrogate_pid,
            "external_guardian_distinct_from_actual_parent": (
                os.getpid() != parent_surrogate_pid
            ),
            "registered_broker_image_attestation_present": False,
            "worker_resource_semantics_present": False,
            "business_resource_semantics_present": False,
            "actual_observed_e3_v2_completion_present": False,
            "e4_v2_completion_present": False,
            "formal_v7_authority_present": False,
            "official_execution_allowed": False,
        }
    finally:
        guardian.close()
        if not parent_surrogate_reaped:
            try:
                os.kill(parent_surrogate_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(parent_surrogate_pid, 0)
            except ChildProcessError:
                pass


def _collapsed_identity_attack(role_name: str) -> dict[str, object]:
    guardian, leaf_endpoint = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    guardian.settimeout(2)
    guardian.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    image_fd = role.create_sealed_nested_creator_leaf_role_memfd_v2(role_name)
    leaf_pid = os.fork()
    if leaf_pid == 0:  # pragma: no cover
        try:
            guardian.close()
            _exec_leaf(leaf_endpoint, image_fd, role_name)
        except BaseException:
            os._exit(127)
    leaf_endpoint.close()
    os.close(image_fd)
    try:
        raw = guardian.recv(1)
        waited, status = os.waitpid(leaf_pid, 0)
        return {
            "role": role_name,
            "guardian_pid": os.getpid(),
            "leaf_pid": leaf_pid,
            "received_bytes": len(raw),
            "leaf_exit_status": os.WEXITSTATUS(status),
            "collapsed_guardian_parent_identity_rejected": waited == leaf_pid and raw == b"",
        }
    finally:
        guardian.close()


def _parent_death_attack(role_name: str) -> dict[str, object]:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), "PR_SET_CHILD_SUBREAPER failed")
    guardian, parent_endpoint = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    guardian.settimeout(10)
    guardian.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    image_fd = role.create_sealed_nested_creator_leaf_role_memfd_v2(role_name)
    parent_surrogate_pid, leaf_pid, release_write = _spawn_through_parent_surrogate(
        role_name, guardian, parent_endpoint, image_fd, wait_for_release=True
    )
    assert release_write is not None
    pidfd = os.pidfd_open(leaf_pid)
    parent_surrogate_reaped = False
    leaf_reaped = False
    try:
        ready, _credential = _receive(guardian)
        if ready.parent_pid != parent_surrogate_pid:
            raise RuntimeError("leaf V2 did not freeze its actual parent PID")
        os.write(release_write, b"x")
        os.close(release_write)
        release_write = -1
        waited_parent, parent_status = os.waitpid(parent_surrogate_pid, 0)
        parent_surrogate_reaped = True
        poller = select.poll()
        poller.register(pidfd, select.POLLIN)
        events = poller.poll(5000)
        waited_leaf, leaf_status = os.waitpid(leaf_pid, 0)
        leaf_reaped = True
        return {
            "role": role_name,
            "parent_surrogate_pid": parent_surrogate_pid,
            "leaf_pid": leaf_pid,
            "parent_surrogate_exit_status": os.WEXITSTATUS(parent_status),
            "leaf_pidfd_readable_after_parent_exit": bool(events),
            "leaf_waited_pid": waited_leaf,
            "leaf_was_signaled": os.WIFSIGNALED(leaf_status),
            "leaf_term_signal": (
                os.WTERMSIG(leaf_status) if os.WIFSIGNALED(leaf_status) else None
            ),
            "pdeathsig_parent_lifetime_binding_observed": (
                waited_parent == parent_surrogate_pid
                and waited_leaf == leaf_pid
                and bool(events)
                and os.WIFSIGNALED(leaf_status)
                and os.WTERMSIG(leaf_status) == signal.SIGKILL
            ),
        }
    finally:
        os.close(pidfd)
        guardian.close()
        try:
            if release_write >= 0:
                os.close(release_write)
        except OSError:
            pass
        if not parent_surrogate_reaped:
            try:
                os.kill(parent_surrogate_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(parent_surrogate_pid, 0)
            except ChildProcessError:
                pass
        if not leaf_reaped:
            try:
                os.kill(leaf_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(leaf_pid, 0)
            except ChildProcessError:
                pass


def main() -> None:
    if len(sys.argv) != 3:
        raise ValueError("usage: helper ROLE MODE")
    role_name, mode = sys.argv[1:]
    if role_name not in role.ROLE_SLOTS:
        raise ValueError("unknown leaf role")
    if mode in {
        "SUCCESS", "WRONG_CREDENTIAL", "WRONG_SLOT", "SCM_RIGHTS",
        "ANCILLARY_TRUNCATION",
    }:
        result = _success_or_command_attack(role_name, mode)
    elif mode == "COLLAPSED_IDENTITY":
        result = _collapsed_identity_attack(role_name)
    elif mode == "PARENT_DEATH":
        result = _parent_death_attack(role_name)
    else:
        raise ValueError("unknown leaf role mode")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
