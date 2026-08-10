from __future__ import annotations

import array
import fcntl
import json
import os
import signal
import socket
import struct
import sys

from acfqp import construction_k7_h1_nested_creator_broker_native_v2 as role


def _receive(endpoint: socket.socket) -> tuple[role.BrokerRoleFrameV2, tuple[int, int, int]]:
    raw, ancillary, flags, address = endpoint.recvmsg(
        role.FRAME_BYTES + 1,
        socket.CMSG_SPACE(struct.calcsize("3i")) + socket.CMSG_SPACE(4 * 4),
    )
    if flags != 0 or len(raw) != role.FRAME_BYTES:
        raise RuntimeError(
            f"BROKER V2 packet boundary changed: flags={flags} "
            f"address={address!r} bytes={len(raw)}"
        )
    credentials: list[tuple[int, int, int]] = []
    received_rights: list[int] = []
    for level, kind, payload in ancillary:
        if level != socket.SOL_SOCKET:
            raise RuntimeError("BROKER V2 emitted non-SOL_SOCKET ancillary data")
        if kind == socket.SCM_CREDENTIALS:
            if len(payload) != struct.calcsize("3i"):
                raise RuntimeError("BROKER V2 credential width changed")
            credentials.append(struct.unpack("3i", payload))
        elif kind == socket.SCM_RIGHTS:
            values = array.array("i")
            values.frombytes(payload[: len(payload) - len(payload) % values.itemsize])
            received_rights.extend(values)
        else:
            raise RuntimeError("BROKER V2 emitted unknown ancillary data")
    for descriptor in received_rights:
        os.close(descriptor)
    if len(credentials) != 1 or received_rights:
        raise RuntimeError("BROKER V2 direct lifecycle ancillary data changed")
    return role.BrokerRoleFrameV2.from_bytes(raw), credentials[0]


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) == 2 else "SUCCESS"
    if mode not in {"SUCCESS", "WRONG_CREDENTIAL"}:
        raise ValueError("unknown BROKER V2 subprocess mode")
    guardian, broker_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    guardian.settimeout(10)
    guardian.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    image_fd = role.create_sealed_nested_creator_broker_memfd_v2()
    broker_pid = os.fork()
    if broker_pid == 0:  # pragma: no cover - facts are asserted by the parent
        try:
            executable_fd = fcntl.fcntl(image_fd, fcntl.F_DUPFD, 100)
            os.set_inheritable(executable_fd, True)
            guardian_fd = guardian.detach()
            child_fd = broker_endpoint.detach()
            if child_fd != role.CONTROL_FD:
                os.dup2(child_fd, role.CONTROL_FD, inheritable=True)
                os.close(child_fd)
            else:
                os.set_inheritable(role.CONTROL_FD, True)
            if guardian_fd != role.CONTROL_FD:
                os.close(guardian_fd)
            os.execve(
                f"/proc/self/fd/{executable_fd}",
                ["acfqp-h1-nested-creator-broker-v2"],
                {},
            )
        except BaseException:
            os._exit(127)
    broker_endpoint.close()
    os.close(image_fd)
    reaped = False
    try:
        ready, ready_credential = _receive(guardian)
        if ready != role.BrokerRoleFrameV2(
            role.OPCODES["BROKER_READY"],
            0,
            bytes(16),
            broker_pid,
            fact_a=os.getpid(),
        ):
            raise RuntimeError("BROKER V2 READY changed")
        go_nonce = bytes(range(16))
        go = role.BrokerRoleFrameV2(
            role.OPCODES["BROKER_GO"], 1, go_nonce, broker_pid
        )
        if mode == "WRONG_CREDENTIAL":
            sibling_pid = os.fork()
            if sibling_pid == 0:  # pragma: no cover - asserted by parent
                try:
                    sent = guardian.send(go.to_bytes())
                    os._exit(0 if sent == role.FRAME_BYTES else 2)
                except BaseException:
                    os._exit(3)
            waited_sibling, sibling_status = os.waitpid(sibling_pid, 0)
            if (
                waited_sibling != sibling_pid
                or not os.WIFEXITED(sibling_status)
                or os.WEXITSTATUS(sibling_status) != 0
            ):
                raise RuntimeError("wrong-credential sibling send failed")
            failure, failure_credential = _receive(guardian)
            waited_pid, wait_status = os.waitpid(broker_pid, 0)
            reaped = True
            if (
                waited_pid != broker_pid
                or not os.WIFEXITED(wait_status)
                or failure.opcode != role.OPCODES["PROTOCOL_FAILURE"]
                or failure.sequence != 1
                or failure.pid != broker_pid
                or failure_credential[0] != broker_pid
            ):
                raise RuntimeError("BROKER V2 accepted sibling credentials")
            print(
                json.dumps(
                    {
                        "broker_pid": broker_pid,
                        "guardian_pid": os.getpid(),
                        "sibling_pid": sibling_pid,
                        "failure_opcode": failure.opcode,
                        "failure_sequence": failure.sequence,
                        "failure_status": failure.status,
                        "broker_exit_status": os.WEXITSTATUS(wait_status),
                        "wrong_credential_rejected": True,
                    },
                    sort_keys=True,
                )
            )
            return
        if guardian.send(go.to_bytes()) != role.FRAME_BYTES:
            raise RuntimeError("BROKER V2 GO short write")
        echo, echo_credential = _receive(guardian)
        if echo != role.BrokerRoleFrameV2(
            role.OPCODES["BROKER_GO_ECHO"], 1, go_nonce, broker_pid
        ):
            raise RuntimeError("BROKER V2 GO echo changed")
        shutdown_nonce = bytes(reversed(range(16)))
        shutdown = role.BrokerRoleFrameV2(
            role.OPCODES["BROKER_SHUTDOWN"],
            role.SHUTDOWN_SEQUENCE,
            shutdown_nonce,
            broker_pid,
        )
        if guardian.send(shutdown.to_bytes()) != role.FRAME_BYTES:
            raise RuntimeError("BROKER V2 SHUTDOWN short write")
        bye, bye_credential = _receive(guardian)
        if bye != role.BrokerRoleFrameV2(
            role.OPCODES["BROKER_BYE"],
            role.SHUTDOWN_SEQUENCE,
            shutdown_nonce,
            broker_pid,
        ):
            raise RuntimeError("BROKER V2 BYE changed")
        waited_pid, wait_status = os.waitpid(broker_pid, 0)
        reaped = True
        if waited_pid != broker_pid or not os.WIFEXITED(wait_status):
            raise RuntimeError("BROKER V2 did not exit normally")
        print(
            json.dumps(
                {
                    "broker_pid": broker_pid,
                    "guardian_pid": os.getpid(),
                    "ready_opcode": ready.opcode,
                    "go_echo_opcode": echo.opcode,
                    "bye_opcode": bye.opcode,
                    "sequences": [ready.sequence, echo.sequence, bye.sequence],
                    "credential_pids": [
                        ready_credential[0],
                        echo_credential[0],
                        bye_credential[0],
                    ],
                    "exit_status": os.WEXITSTATUS(wait_status),
                    "direct_exec_ready_go_shutdown_observed": True,
                    "create_role_branch_exercised": False,
                    "broker_created_by_supervisor_observed": False,
                    "channel_independence_authority_present": False,
                    "role_image_slot_identity_authority_present": False,
                    "one_shot_leaf_authority_present": False,
                    "failure_closure_authority_present": False,
                    "three_birth_prefix_authority_present": False,
                    "five_birth_process_authority_present": False,
                },
                sort_keys=True,
            )
        )
    finally:
        guardian.close()
        if not reaped:
            try:
                os.kill(broker_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(broker_pid, 0)
            except ChildProcessError:
                pass


if __name__ == "__main__":
    main()
