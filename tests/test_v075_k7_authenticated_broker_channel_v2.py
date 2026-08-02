from __future__ import annotations

from array import array
import hashlib
import os
import socket

import pytest

from acfqp import v075_k7_authenticated_broker_channel_v2 as channel_v2
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:test:authenticated-broker-channel:v2\x00" + label.encode()
    ).hexdigest()


def _binding(label: str) -> ipc_v1.K7OuterAttemptBrokerIPCBindingV1:
    return ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
        _id(f"request-{label}"),
        _id(f"route-{label}"),
        _id(f"spec-{label}"),
        _id(f"nonce-{label}"),
    )


def _ready(binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1) -> bytes:
    return ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
        binding=binding,
        role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
        payload={"worker_replay_id": _id("replay")},
    )


def _pair() -> tuple[socket.socket, socket.socket]:
    broker, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    broker.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    broker.set_inheritable(False)
    child.set_inheritable(False)
    return broker, child


def _fork_sender(
    broker: socket.socket,
    child: socket.socket,
    raw: bytes,
    *,
    send_rights: bool = False,
) -> tuple[int, int]:
    if not hasattr(os, "pidfd_open"):
        pytest.skip("pidfd_open is unavailable")
    pid = os.fork()
    if pid == 0:  # pragma: no cover - child has only fixed syscalls
        try:
            broker.close()
            if send_rights:
                descriptor = os.memfd_create("acfqp-channel-rights", os.MFD_CLOEXEC)
                try:
                    sent = child.sendmsg(
                        [raw],
                        [
                            (
                                socket.SOL_SOCKET,
                                socket.SCM_RIGHTS,
                                array("i", [descriptor]),
                            )
                        ],
                    )
                finally:
                    os.close(descriptor)
            else:
                sent = child.send(raw)
            os._exit(0 if sent == len(raw) else 91)
        except BaseException:
            os._exit(92)
    return pid, os.pidfd_open(pid, 0)


def _reap(pid: int, pidfd: int) -> None:
    try:
        waited, status = os.waitpid(pid, 0)
        assert waited == pid
        assert os.waitstatus_to_exitcode(status) == 0
    finally:
        os.close(pidfd)


def test_single_scm_credentials_joins_native_pid_pidfd_and_canonical_role() -> None:
    binding = _binding("happy")
    raw = _ready(binding)
    broker, child = _pair()
    pid = pidfd = -1
    try:
        pid, pidfd = _fork_sender(broker, child, raw)
        child.close()
        observation = channel_v2.receive_v075_k7_authenticated_broker_frame_v2(
            endpoint=broker,
            expected_pid=pid,
            expected_pidfd=pidfd,
            expected_binding=binding,
            expected_role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
        )
        document = observation.to_document()
        assert document["sender_pid"] == pid
        assert document["sender_uid"] == os.geteuid()
        assert document["sender_gid"] == os.getegid()
        assert document["frame_role"] == "WORKER_READY"
        assert document["raw_sha256"] == hashlib.sha256(raw).hexdigest()
        assert document["pid_pidfd_scm_join_verified"] is True
        assert all(value is False for value in document["formal_locks"].values())
        _reap(pid, pidfd)
        pid = pidfd = -1
    finally:
        broker.close()
        child.close()
        if pid > 0:
            try:
                os.kill(pid, 9)
            except OSError:
                pass
            os.waitpid(pid, 0)
        if pidfd >= 0:
            os.close(pidfd)


def test_endpoint_passcred_and_pidfd_mismatch_fail_before_packet_consumption() -> None:
    binding = _binding("prechecks")
    raw = _ready(binding)
    broker, child = _pair()
    self_pidfd = -1
    try:
        if not hasattr(os, "pidfd_open"):
            pytest.skip("pidfd_open is unavailable")
        self_pidfd = os.pidfd_open(os.getpid(), 0)
        broker.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 0)
        with pytest.raises(
            channel_v2.V075K7AuthenticatedBrokerChannelV2Error,
            match="SO_PASSCRED",
        ):
            channel_v2.receive_v075_k7_authenticated_broker_frame_v2(
                endpoint=broker,
                expected_pid=os.getpid(),
                expected_pidfd=self_pidfd,
                expected_binding=binding,
                expected_role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
            )
    finally:
        broker.close()
        child.close()
        if self_pidfd >= 0:
            os.close(self_pidfd)

    broker, child = _pair()
    pid = pidfd = -1
    try:
        pid, pidfd = _fork_sender(broker, child, raw)
        child.close()
        with pytest.raises(
            channel_v2.V075K7AuthenticatedBrokerChannelV2Error,
            match="does not match",
        ):
            channel_v2.receive_v075_k7_authenticated_broker_frame_v2(
                endpoint=broker,
                expected_pid=pid + 1,
                expected_pidfd=pidfd,
                expected_binding=binding,
                expected_role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
            )
        observation = channel_v2.receive_v075_k7_authenticated_broker_frame_v2(
            endpoint=broker,
            expected_pid=pid,
            expected_pidfd=pidfd,
            expected_binding=binding,
            expected_role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
        )
        assert observation.sender_pid == pid
        _reap(pid, pidfd)
        pid = pidfd = -1
    finally:
        broker.close()
        child.close()
        if pid > 0:
            try:
                os.kill(pid, 9)
            except OSError:
                pass
            os.waitpid(pid, 0)
        if pidfd >= 0:
            os.close(pidfd)


def test_injected_ancillary_fd_and_wrong_canonical_role_fail_closed() -> None:
    binding = _binding("attacks")
    raw = _ready(binding)
    broker, child = _pair()
    pid = pidfd = -1
    try:
        pid, pidfd = _fork_sender(broker, child, raw, send_rights=True)
        child.close()
        with pytest.raises(
            channel_v2.V075K7AuthenticatedBrokerChannelV2Error,
            match="truncated or injected",
        ):
            channel_v2.receive_v075_k7_authenticated_broker_frame_v2(
                endpoint=broker,
                expected_pid=pid,
                expected_pidfd=pidfd,
                expected_binding=binding,
                expected_role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
            )
        _reap(pid, pidfd)
        pid = pidfd = -1
    finally:
        broker.close()
        child.close()
        if pid > 0:
            try:
                os.kill(pid, 9)
            except OSError:
                pass
            os.waitpid(pid, 0)
        if pidfd >= 0:
            os.close(pidfd)

    broker, child = _pair()
    try:
        pid, pidfd = _fork_sender(broker, child, raw)
        child.close()
        with pytest.raises(
            channel_v2.V075K7AuthenticatedBrokerChannelV2Error,
            match="canonical role",
        ):
            channel_v2.receive_v075_k7_authenticated_broker_frame_v2(
                endpoint=broker,
                expected_pid=pid,
                expected_pidfd=pidfd,
                expected_binding=binding,
                expected_role=(
                    ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_REQUEST
                ),
            )
        _reap(pid, pidfd)
        pid = pidfd = -1
    finally:
        broker.close()
        child.close()
        if pid > 0:
            try:
                os.kill(pid, 9)
            except OSError:
                pass
            os.waitpid(pid, 0)
        if pidfd >= 0:
            os.close(pidfd)
