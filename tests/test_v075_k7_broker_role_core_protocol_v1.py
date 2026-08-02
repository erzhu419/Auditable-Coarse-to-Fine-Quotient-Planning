from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import queue
import socket
import threading

import pytest

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as atomic_runtime
from acfqp import v075_k7_broker_worker_entry_v1 as worker_core
from acfqp import v075_k7_business_entry_core_v1 as business_core
from acfqp import v075_k7_child_business_bundle_v1 as child_business
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc
from acfqp.phase3e_ids import canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-broker-role-core-protocol-test:v1\x00"
        + label.encode("ascii")
    ).hexdigest()


class _Request:
    request_id = _id("request")
    route_identity = type("Route", (), {"route_identity_id": _id("route")})()

    def _assert_current(self) -> None:
        return None


class _Replay:
    def __init__(self) -> None:
        self.request = _Request()
        self.replay_id = _id("replay")
        self.profile_closure = type(
            "Closure", (), {"_assert_current": lambda self: None}
        )()


class _Bundle:
    def __init__(self, replay: _Replay) -> None:
        self.bundle_id = _id("business-bundle")
        self._document = {
            "schema": "acfqp.test_integrated_business_bundle.v1",
            "portable_request_replay_id": replay.replay_id,
            "request_id": replay.request.request_id,
            "route_identity_id": replay.request.route_identity.route_identity_id,
            "payload": {"result": "integrated-core"},
            "child_business_bundle_id": self.bundle_id,
        }
        self.canonical_bytes = canonical_json_bytes(self._document)

    def to_document(self) -> dict:
        return deepcopy(self._document)


def _recv_packet(endpoint: socket.socket) -> bytes:
    raw = endpoint.recv(ipc.FRAME_WIDTH + ipc.MAX_FRAME_BYTES + 1)
    assert raw
    return raw


def test_two_channels_relay_real_memfd_and_complete_structural_transcript(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay = _Replay()
    bundle = _Bundle(replay)
    binding = ipc.K7OuterAttemptBrokerIPCBindingV1(
        replay.request.request_id,
        replay.request.route_identity.route_identity_id,
        _id("broker-spec"),
        _id("session-nonce"),
    )

    monkeypatch.setattr(
        business_core.business_v1.portable_replay,
        "V075K7SuccessorPortableRequestReplayV1",
        _Replay,
    )
    monkeypatch.setattr(
        worker_core.portable_replay,
        "V075K7SuccessorPortableRequestReplayV1",
        _Replay,
    )
    monkeypatch.setattr(child_business, "V075K7ChildBusinessBundleV1", _Bundle)

    def execute_business(**kwargs):
        assert kwargs["request_replay"] is replay
        return bundle

    def verify_business(*, raw: bytes, expected_request_replay: _Replay):
        if raw != bundle.canonical_bytes or expected_request_replay is not replay:
            raise ValueError("crossed integrated business bundle")
        return bundle

    monkeypatch.setattr(
        child_business,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        execute_business,
    )
    monkeypatch.setattr(
        child_business,
        "verify_v075_k7_child_business_bundle_public_bytes_v1",
        verify_business,
    )

    result_writable = atomic_runtime._new_sealable_memfd(  # noqa: SLF001
        "acfqp-integrated-role-core-result"
    )
    result_readonly = os.open(
        f"/proc/self/fd/{result_writable}",
        os.O_RDONLY | os.O_CLOEXEC,
    )
    source_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
    secret_fd = os.open("/dev/zero", os.O_RDONLY | os.O_CLOEXEC)
    output_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    broker_worker, worker_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    broker_business, business_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    broker_worker.settimeout(10)
    broker_business.settimeout(10)
    outcomes: queue.Queue[object] = queue.Queue()

    def run_worker() -> None:
        try:
            outcomes.put(
                worker_core.execute_v075_k7_broker_worker_core_v1(
                    expected_request_replay=replay,
                    binding=binding,
                    endpoint=worker_endpoint,
                    sealed_business_result_fd=result_readonly,
                    output_directory_fd=output_fd,
                )
            )
        except BaseException as error:  # pragma: no cover - surfaced below
            outcomes.put(error)

    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()
    try:
        ready_raw = _recv_packet(broker_worker)
        request_raw = _recv_packet(broker_worker)
        emission = business_core.execute_v075_k7_business_entry_core_v1(
            request_replay=replay,
            source_archive_fd=source_fd,
            sealed_secret_fd=secret_fd,
            repository_root=Path("/unused/repository"),
            signer_private_root=Path("/unused/private"),
            signer_private_key_path=Path("/unused/private/key.json"),
            output_memfd=result_writable,
            business_result_endpoint=business_endpoint,
            binding=binding,
        )
        result_raw = _recv_packet(broker_business)
        result_frame = ipc.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
            raw=result_raw,
            expected_binding=binding,
            expected_role=ipc.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT,
        )
        assert result_frame.frame_id == emission.business_result_frame.frame_id
        assert result_frame.payload == {"business_result_id": bundle.bundle_id}

        assert broker_worker.send(result_raw) == len(result_raw)
        broker_worker.shutdown(socket.SHUT_WR)
        parent_raw = _recv_packet(broker_worker)
        eof_raw = _recv_packet(broker_worker)
        thread.join(10)
        assert not thread.is_alive()
        outcome = outcomes.get_nowait()
        if isinstance(outcome, BaseException):
            raise outcome
        completion = outcome

        transcript = ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
            raw=b"".join(
                (ready_raw, request_raw, result_raw, parent_raw, eof_raw)
            ),
            expected_binding=binding,
        )
        assert completion.frame_ids == tuple(
            frame.frame_id for frame in transcript.frames
        )
        assert transcript.frames[0].payload == {"worker_replay_id": replay.replay_id}
        assert transcript.frames[1].payload == {"request_ordinal": 0}
        committed = (tmp_path / worker_core.OUTPUT_NAME).read_bytes()
        replayed_output = (
            worker_core.verify_v075_k7_broker_operational_output_bytes_v1(
                raw=committed,
                expected_request_replay=replay,
                expected_binding=binding,
            )
        )
        assert replayed_output.output_id == completion.operational_output_id
        assert transcript.frames[3].payload == {
            "output_byte_count": len(committed),
            "output_sha256": hashlib.sha256(committed).hexdigest(),
        }
        assert transcript.to_document()["payload_semantics_verified"] is False
    finally:
        if thread.is_alive():
            try:
                broker_worker.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            thread.join(2)
        broker_worker.close()
        worker_endpoint.close()
        broker_business.close()
        business_endpoint.close()
        os.close(output_fd)
        os.close(secret_fd)
        os.close(source_fd)
        os.close(result_readonly)
        os.close(result_writable)
