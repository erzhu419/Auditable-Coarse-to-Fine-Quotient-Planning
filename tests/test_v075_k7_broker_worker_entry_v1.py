from __future__ import annotations

from copy import deepcopy
import fcntl
import hashlib
import os
import signal
import socket
import threading
import time

import pytest

from acfqp.exact_frozen_memo_v1 import disable_exact_frozen_memoization_v1
from acfqp import v075_k7_atomic_pidfd_runtime_v1 as atomic_runtime
from acfqp import v075_k7_broker_worker_entry_v1 as worker
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-broker-worker-entry-test:v1\x00" + label.encode("ascii")
    ).hexdigest()


class _Request:
    request_id = _id("request")
    route_identity = type("Route", (), {"route_identity_id": _id("route")})()

    def _assert_current(self) -> None:
        return None


class _Replay:
    def __init__(self) -> None:
        self.request = _Request()
        self.replay_id = _id("request-replay")
        self.profile_closure = type(
            "Closure", (), {"_assert_current": lambda self: None}
        )()


class _Bundle:
    def __init__(self, label: str = "bundle") -> None:
        self.bundle_id = _id(label)
        self._document = {
            "schema": "acfqp.test_business_bundle.v1",
            "child_business_bundle_id": self.bundle_id,
            "payload": {"value": 7},
        }
        self.canonical_bytes = canonical_json_bytes(self._document)

    def to_document(self) -> dict:
        return deepcopy(self._document)


@pytest.fixture
def substrate(monkeypatch: pytest.MonkeyPatch):
    replay = _Replay()
    bundle = _Bundle()
    monkeypatch.setattr(
        worker.portable_replay,
        "V075K7SuccessorPortableRequestReplayV1",
        _Replay,
    )

    def verify(*, raw: bytes, expected_request_replay: _Replay):
        if expected_request_replay is not replay or raw != bundle.canonical_bytes:
            raise ValueError("crossed fake public business bundle")
        return bundle

    monkeypatch.setattr(
        worker.business_bundle,
        "verify_v075_k7_child_business_bundle_public_bytes_v1",
        verify,
    )
    binding = ipc.K7OuterAttemptBrokerIPCBindingV1(
        replay.request.request_id,
        replay.request.route_identity.route_identity_id,
        _id("broker-execution-spec"),
        _id("session-nonce"),
    )
    return replay, bundle, binding


def _sealed_read_only(raw: bytes) -> tuple[int, int]:
    writable = atomic_runtime.create_v075_k7_sealed_memfd_from_bytes_v1(
        raw=raw,
        name="acfqp-worker-test-business-result",
    )
    readonly = os.open(
        f"/proc/self/fd/{writable}",
        os.O_RDONLY | os.O_CLOEXEC,
    )
    return writable, readonly


def _result_frame(binding, bundle_id: str) -> bytes:
    return ipc.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
        binding=binding,
        role=ipc.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT,
        payload={"business_result_id": bundle_id},
    )


def _receive_frame(endpoint: socket.socket, binding, role):
    raw = endpoint.recv(ipc.FRAME_WIDTH + ipc.MAX_FRAME_BYTES + 1)
    return ipc.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
        raw=raw,
        expected_binding=binding,
        expected_role=role,
    )


def test_operational_output_transaction_cache_equal_copy_and_disabled_reference(
    substrate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    raw = output.canonical_bytes
    equal_copy = bytes(bytearray(raw))
    assert equal_copy == raw
    assert equal_copy is not raw
    original = worker._compute_output_validation_facts_v1  # noqa: SLF001
    calls = 0

    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(worker, "_compute_output_validation_facts_v1", counted)
    cached = worker.verify_v075_k7_broker_operational_output_bytes_v1(
        raw=raw,
        expected_request_replay=replay,
        expected_binding=binding,
    )
    assert calls == 1
    copied = worker.verify_v075_k7_broker_operational_output_bytes_v1(
        raw=equal_copy,
        expected_request_replay=replay,
        expected_binding=binding,
    )
    assert calls == 2
    before_disabled = calls
    with disable_exact_frozen_memoization_v1():
        reference = worker.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=raw,
            expected_request_replay=replay,
            expected_binding=binding,
        )
        reference_id = reference.output_id
    assert cached.output_id == copied.output_id == reference_id
    # Disabled construction performs both raw replays, and every issued
    # property access preserves the frozen V1 full-current-validation rule.
    assert calls == before_disabled + 5


def test_operational_output_exact_cache_rejects_one_byte_mutation(
    substrate,
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    raw = output.canonical_bytes
    attacked = bytearray(raw)
    offset = raw.index(binding.request_id.encode("ascii"))
    attacked[offset] = ord("0") if attacked[offset] != ord("0") else ord("1")
    with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error):
        worker.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=bytes(attacked),
            expected_request_replay=replay,
            expected_binding=binding,
        )


def test_operational_output_formula_monkeypatch_invalidates_cache(
    substrate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    raw = output.canonical_bytes
    worker.verify_v075_k7_broker_operational_output_bytes_v1(
        raw=raw,
        expected_request_replay=replay,
        expected_binding=binding,
    )

    def rejected(**kwargs):
        del kwargs
        raise ValueError("broker nested verifier monkeypatch probe")

    monkeypatch.setattr(
        worker.business_bundle,
        "verify_v075_k7_child_business_bundle_public_bytes_v1",
        rejected,
    )
    with pytest.raises(
        worker.V075K7BrokerWorkerEntryV1Error,
        match="nested business replay failed",
    ):
        worker.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=raw,
            expected_request_replay=replay,
            expected_binding=binding,
        )
    with disable_exact_frozen_memoization_v1():
        with pytest.raises(
            worker.V075K7BrokerWorkerEntryV1Error,
            match="nested business replay failed",
        ):
            worker.verify_v075_k7_broker_operational_output_bytes_v1(
                raw=raw,
                expected_request_replay=replay,
                expected_binding=binding,
            )


def test_operational_output_validation_does_not_cross_transaction_boundary(
    substrate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    raw = output.canonical_bytes
    original = worker._compute_output_validation_facts_v1  # noqa: SLF001
    calls = 0

    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(worker, "_compute_output_validation_facts_v1", counted)
    with worker._output_validation_transaction_v1():  # noqa: SLF001
        for _ in range(2):
            worker.verify_v075_k7_broker_operational_output_bytes_v1(
                raw=raw,
                expected_request_replay=replay,
                expected_binding=binding,
            )
    assert calls == 2


def test_operational_output_disabled_path_bypasses_transaction_cache(
    substrate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    raw = output.canonical_bytes
    original = worker._compute_output_validation_facts_v1  # noqa: SLF001
    calls = 0

    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(worker, "_compute_output_validation_facts_v1", counted)
    with disable_exact_frozen_memoization_v1():
        for _ in range(2):
            worker.verify_v075_k7_broker_operational_output_bytes_v1(
                raw=raw,
                expected_request_replay=replay,
                expected_binding=binding,
            )
    assert calls == 4


def test_operational_output_portable_mutations_cross_transaction_boundary(
    substrate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    raw = output.canonical_bytes
    portable = worker.business_bundle.portable_evidence
    nested_registry = portable._SCHEMA_NESTED_PRIMARY_DOCUMENT_IDS  # noqa: SLF001
    expected_roles = portable.ROLE_SCHEMA_REGISTRY
    probe = "acfqp.broker-transaction-schema-mutation-probe.v1"
    original_verifier = (
        worker.business_bundle
        .verify_v075_k7_child_business_bundle_public_bytes_v1
    )

    def state_sensitive_verifier(**kwargs):
        if probe in nested_registry:
            raise ValueError("in-place portable schema mutation observed")
        if portable.ROLE_SCHEMA_REGISTRY is not expected_roles:
            raise ValueError("portable role registry replacement observed")
        return original_verifier(**kwargs)

    monkeypatch.setattr(
        worker.business_bundle,
        "verify_v075_k7_child_business_bundle_public_bytes_v1",
        state_sensitive_verifier,
    )
    worker.verify_v075_k7_broker_operational_output_bytes_v1(
        raw=raw,
        expected_request_replay=replay,
        expected_binding=binding,
    )
    nested_registry[probe] = frozenset({"probe_id"})
    try:
        with pytest.raises(
            worker.V075K7BrokerWorkerEntryV1Error,
            match="nested business replay failed",
        ):
            worker.verify_v075_k7_broker_operational_output_bytes_v1(
                raw=raw,
                expected_request_replay=replay,
                expected_binding=binding,
            )
    finally:
        nested_registry.pop(probe)
    monkeypatch.setattr(portable, "ROLE_SCHEMA_REGISTRY", dict(expected_roles))
    with pytest.raises(
        worker.V075K7BrokerWorkerEntryV1Error,
        match="nested business replay failed",
    ):
        worker.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=raw,
            expected_request_replay=replay,
            expected_binding=binding,
        )


def test_issued_output_rejects_current_validation_authority_mutations(
    substrate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    original_locks = worker._formal_locks  # noqa: SLF001

    def mutate_locks(scoped: pytest.MonkeyPatch) -> None:
        scoped.setattr(
            worker,
            "_formal_locks",
            lambda: {**original_locks(), "authority_mutation_probe": True},
        )

    def mutate_schema(scoped: pytest.MonkeyPatch) -> None:
        scoped.setattr(worker, "SCHEMA_VERSION", "1.0.0-authority-probe")

    for mutate in (mutate_locks, mutate_schema):
        with monkeypatch.context() as scoped:
            mutate(scoped)
            with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error):
                output.output_id
            with disable_exact_frozen_memoization_v1():
                with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error):
                    output.output_id


def test_issued_output_replays_child_validator_internal_authorities(
    substrate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    expected_id = output.output_id
    portable = worker.business_bundle.portable_evidence
    nested_registry = portable._SCHEMA_NESTED_PRIMARY_DOCUMENT_IDS  # noqa: SLF001
    schema_probe = "acfqp.issued-output-schema-mutation-probe.v1"
    original_verifier = (
        worker.business_bundle
        .verify_v075_k7_child_business_bundle_public_bytes_v1
    )
    mutable_roles = dict(portable.ROLE_SCHEMA_REGISTRY)
    original_roles = dict(mutable_roles)

    def state_sensitive_verifier(**kwargs):
        if schema_probe in nested_registry:
            raise ValueError("in-place portable schema mutation observed")
        if mutable_roles != original_roles:
            raise ValueError("in-place portable role mutation observed")
        return original_verifier(**kwargs)

    monkeypatch.setattr(
        worker.business_bundle,
        "verify_v075_k7_child_business_bundle_public_bytes_v1",
        state_sensitive_verifier,
    )
    monkeypatch.setattr(portable, "ROLE_SCHEMA_REGISTRY", mutable_roles)
    assert output.output_id == expected_id

    nested_registry[schema_probe] = frozenset({"probe_id"})
    try:
        with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error):
            output.output_id
        with disable_exact_frozen_memoization_v1():
            with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error):
                output.output_id
    finally:
        nested_registry.pop(schema_probe)

    first_role = next(iter(mutable_roles))
    mutable_roles[first_role] = "acfqp.issued-output-role-probe.v1"
    with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error):
        output.output_id
    with disable_exact_frozen_memoization_v1():
        with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error):
            output.output_id


def test_worker_core_commits_output_and_emits_exact_protocol(
    tmp_path, substrate
) -> None:
    replay, bundle, binding = substrate
    writable, readonly = _sealed_read_only(bundle.canonical_bytes)
    broker_endpoint, worker_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    output_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        broker_endpoint.send(_result_frame(binding, bundle.bundle_id))
        broker_endpoint.shutdown(socket.SHUT_WR)
        completion = worker.execute_v075_k7_broker_worker_core_v1(
            expected_request_replay=replay,
            binding=binding,
            endpoint=worker_endpoint,
            sealed_business_result_fd=readonly,
            output_directory_fd=output_fd,
        )
        roles = ipc.K7OuterAttemptBrokerFrameRoleV1
        observed = (
            _receive_frame(broker_endpoint, binding, roles.WORKER_READY),
            _receive_frame(broker_endpoint, binding, roles.BUSINESS_REQUEST),
            _receive_frame(broker_endpoint, binding, roles.PARENT_OUTPUT),
            _receive_frame(broker_endpoint, binding, roles.WORKER_EOF),
        )
        assert observed[0].payload == {"worker_replay_id": replay.replay_id}
        assert observed[1].payload == {"request_ordinal": 0}
        assert observed[3].payload == {"clean_close": True}
        raw = (tmp_path / worker.OUTPUT_NAME).read_bytes()
        output = worker.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=raw,
            expected_request_replay=replay,
            expected_binding=binding,
        )
        assert output.output_id == completion.operational_output_id
        assert observed[2].payload == {
            "output_byte_count": len(raw),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
        }
        assert completion.business_result_id == bundle.bundle_id
        assert completion.operational_output.output_id == completion.operational_output_id
        assert (
            completion.output_commit_receipt.receipt_id
            == completion.output_commit_receipt_id
        )
        assert completion.output_commit_receipt.canonical_bytes
        assert completion.to_document()["frame_roles"] == [
            role.value for role in ipc.FRAME_ROLES
        ]
        profile_document = (
            worker.official_v075_k7_broker_worker_entry_core_profile_v1()
            .to_document()
        )
        assert {
            profile_document[name] for name in worker._formal_locks()  # noqa: SLF001
        } == {False}
        assert completion.to_document()["formal_locks"]
        assert set(completion.to_document()["formal_locks"].values()) == {False}
        status = (tmp_path / worker.OUTPUT_NAME).stat()
        assert status.st_nlink == 1
        assert stat_mode(status.st_mode) == 0o600
    finally:
        os.close(output_fd)
        broker_endpoint.close()
        worker_endpoint.close()
        os.close(readonly)
        os.close(writable)


def stat_mode(mode: int) -> int:
    return mode & 0o777


def test_worker_rejects_crossed_result_before_output_suffix(
    tmp_path, substrate
) -> None:
    replay, bundle, binding = substrate
    writable, readonly = _sealed_read_only(bundle.canonical_bytes)
    broker_endpoint, worker_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    output_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        broker_endpoint.send(_result_frame(binding, _id("foreign-bundle")))
        broker_endpoint.shutdown(socket.SHUT_WR)
        with pytest.raises(
            worker.V075K7BrokerWorkerEntryV1Error,
            match="crossed its sealed business bundle",
        ):
            worker.execute_v075_k7_broker_worker_core_v1(
                expected_request_replay=replay,
                binding=binding,
                endpoint=worker_endpoint,
                sealed_business_result_fd=readonly,
                output_directory_fd=output_fd,
            )
        roles = ipc.K7OuterAttemptBrokerFrameRoleV1
        _receive_frame(broker_endpoint, binding, roles.WORKER_READY)
        _receive_frame(broker_endpoint, binding, roles.BUSINESS_REQUEST)
        broker_endpoint.setblocking(False)
        with pytest.raises(BlockingIOError):
            broker_endpoint.recv(1)
        assert list(tmp_path.iterdir()) == []
    finally:
        os.close(output_fd)
        broker_endpoint.close()
        worker_endpoint.close()
        os.close(readonly)
        os.close(writable)


def test_writable_result_fd_and_stream_socket_fail_before_frames(
    tmp_path, substrate
) -> None:
    replay, bundle, binding = substrate
    writable, readonly = _sealed_read_only(bundle.canonical_bytes)
    broker_endpoint, worker_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    output_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error, match="read-only"):
            worker.execute_v075_k7_broker_worker_core_v1(
                expected_request_replay=replay,
                binding=binding,
                endpoint=worker_endpoint,
                sealed_business_result_fd=writable,
                output_directory_fd=output_fd,
            )
        broker_endpoint.setblocking(False)
        with pytest.raises(BlockingIOError):
            broker_endpoint.recv(1)
    finally:
        os.close(output_fd)
        broker_endpoint.close()
        worker_endpoint.close()
        os.close(readonly)
        os.close(writable)

    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error, match="SEQPACKET"):
            worker.execute_v075_k7_broker_worker_core_v1(
                expected_request_replay=replay,
                binding=binding,
                endpoint=right,
                sealed_business_result_fd=-1,
                output_directory_fd=-1,
            )
    finally:
        left.close()
        right.close()


def test_existing_output_or_partial_write_fails_without_suffix(
    tmp_path, substrate, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay, bundle, binding = substrate
    (tmp_path / "contaminant").write_bytes(b"x")
    writable, readonly = _sealed_read_only(bundle.canonical_bytes)
    broker_endpoint, worker_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    output_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        broker_endpoint.send(_result_frame(binding, bundle.bundle_id))
        broker_endpoint.shutdown(socket.SHUT_WR)
        with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error, match="empty usable"):
            worker.execute_v075_k7_broker_worker_core_v1(
                expected_request_replay=replay,
                binding=binding,
                endpoint=worker_endpoint,
                sealed_business_result_fd=readonly,
                output_directory_fd=output_fd,
            )
        assert not (tmp_path / worker.OUTPUT_NAME).exists()
    finally:
        os.close(output_fd)
        broker_endpoint.close()
        worker_endpoint.close()
        os.close(readonly)
        os.close(writable)


def test_nested_bundle_change_fails_even_after_outer_rehash(
    tmp_path, substrate
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    document = loads_canonical_json(output.canonical_bytes)
    document["business_result"]["payload"]["value"] = 8
    payload = dict(document)
    payload.pop("broker_operational_output_id")
    document["business_result_byte_count"] = len(
        canonical_json_bytes(document["business_result"])
    )
    document["business_result_sha256"] = hashlib.sha256(
        canonical_json_bytes(document["business_result"])
    ).hexdigest()
    payload = dict(document)
    payload.pop("broker_operational_output_id")
    document["broker_operational_output_id"] = worker._hash(  # noqa: SLF001
        worker.V075_K7_BROKER_OPERATIONAL_OUTPUT_V1_DOMAIN,
        payload,
    )
    with pytest.raises(
        worker.V075K7BrokerWorkerEntryV1Error,
        match="nested business replay failed",
    ):
        worker.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=canonical_json_bytes(document),
            expected_request_replay=replay,
            expected_binding=binding,
        )


def test_commit_refuses_symlink_name_and_rename_collision(
    tmp_path, substrate, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.write_bytes(b"outside")
    (tmp_path / worker.OUTPUT_NAME).symlink_to(outside)
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error, match="empty usable"):
            worker._commit_output(output=output, directory_fd=directory_fd)  # noqa: SLF001
    finally:
        os.close(directory_fd)
    assert outside.read_bytes() == b"outside"


def test_profile_and_issued_types_are_not_caller_mintable(substrate) -> None:
    replay, bundle, binding = substrate
    with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error, match="issuer-owned"):
        worker.V075K7BrokerWorkerEntryCoreProfileV1(object())
    with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error, match="caller-minted"):
        worker.V075K7BrokerOperationalOutputV1(
            object(), b"{}", replay, binding
        )
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error, match="issuer-owned"):
        worker.V075K7BrokerWorkerCommitBoundaryV1Error(
            object(),
            "forged",
            operational_output=output,
            commit_stage="RENAMED_NOREPLACE",
            output_directory_contaminated=True,
            directory_device=1,
            directory_inode=1,
            committed_file_device=1,
            committed_file_inode=2,
            file_fsync_completed=True,
            rename_noreplace_completed=True,
            directory_fsync_completed=False,
        )
    assert worker.LOCAL_DOMAIN_TAGS
    assert fcntl.fcntl


def test_delayed_peer_half_close_is_accepted_without_race(
    tmp_path, substrate
) -> None:
    replay, bundle, binding = substrate
    writable, readonly = _sealed_read_only(bundle.canonical_bytes)
    broker_endpoint, worker_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    output_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    closer: threading.Thread | None = None
    try:
        broker_endpoint.send(_result_frame(binding, bundle.bundle_id))
        closer = threading.Thread(
            target=lambda: (
                time.sleep(0.1),
                broker_endpoint.shutdown(socket.SHUT_WR),
            )
        )
        closer.start()
        completion = worker.execute_v075_k7_broker_worker_core_v1(
            expected_request_replay=replay,
            binding=binding,
            endpoint=worker_endpoint,
            sealed_business_result_fd=readonly,
            output_directory_fd=output_fd,
        )
        closer.join()
        assert completion.operational_output_id
        assert (tmp_path / worker.OUTPUT_NAME).exists()
    finally:
        if closer is not None:
            closer.join()
        os.close(output_fd)
        broker_endpoint.close()
        worker_endpoint.close()
        os.close(readonly)
        os.close(writable)


def test_extra_result_packet_is_rejected_instead_of_half_close(
    tmp_path, substrate
) -> None:
    replay, bundle, binding = substrate
    writable, readonly = _sealed_read_only(bundle.canonical_bytes)
    broker_endpoint, worker_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    output_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        packet = _result_frame(binding, bundle.bundle_id)
        broker_endpoint.send(packet)
        broker_endpoint.send(packet)
        with pytest.raises(
            worker.V075K7BrokerWorkerEntryV1Error,
            match="extra packet",
        ):
            worker.execute_v075_k7_broker_worker_core_v1(
                expected_request_replay=replay,
                binding=binding,
                endpoint=worker_endpoint,
                sealed_business_result_fd=readonly,
                output_directory_fd=output_fd,
            )
        assert list(tmp_path.iterdir()) == []
    finally:
        os.close(output_fd)
        broker_endpoint.close()
        worker_endpoint.close()
        os.close(readonly)
        os.close(writable)


def test_opath_unsealed_regular_and_bad_directory_fail_before_frames(
    tmp_path, substrate
) -> None:
    if not hasattr(os, "O_PATH"):
        pytest.skip("Linux O_PATH is required")
    replay, bundle, binding = substrate
    writable, readonly = _sealed_read_only(bundle.canonical_bytes)
    ordinary_path = tmp_path / "ordinary"
    ordinary_path.write_bytes(b"")
    ordinary = os.open(ordinary_path, os.O_RDONLY | os.O_CLOEXEC)
    opath_result = os.open(f"/proc/self/fd/{writable}", os.O_PATH | os.O_CLOEXEC)
    output_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    opath_directory = os.open(tmp_path, os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for result_fd, directory_fd in (
            (opath_result, output_fd),
            (ordinary, output_fd),
            (readonly, opath_directory),
        ):
            broker_endpoint, worker_endpoint = socket.socketpair(
                socket.AF_UNIX, socket.SOCK_SEQPACKET
            )
            try:
                with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error):
                    worker.execute_v075_k7_broker_worker_core_v1(
                        expected_request_replay=replay,
                        binding=binding,
                        endpoint=worker_endpoint,
                        sealed_business_result_fd=result_fd,
                        output_directory_fd=directory_fd,
                    )
                broker_endpoint.setblocking(False)
                with pytest.raises(BlockingIOError):
                    broker_endpoint.recv(1)
            finally:
                broker_endpoint.close()
                worker_endpoint.close()
    finally:
        os.close(opath_directory)
        os.close(output_fd)
        os.close(opath_result)
        os.close(ordinary)
        os.close(readonly)
        os.close(writable)


def test_nonblocking_endpoint_sealed_empty_memfd_and_unlinked_directory_fail_before_frames(
    tmp_path, substrate
) -> None:
    replay, bundle, binding = substrate
    empty_writable = os.memfd_create(
        "acfqp-worker-test-empty",
        atomic_runtime.MFD_CLOEXEC | atomic_runtime.MFD_ALLOW_SEALING,
    )
    fcntl.fcntl(
        empty_writable,
        atomic_runtime.F_ADD_SEALS,
        atomic_runtime.REQUIRED_MEMFD_SEALS,
    )
    empty_readonly = os.open(
        f"/proc/self/fd/{empty_writable}", os.O_RDONLY | os.O_CLOEXEC
    )
    valid_writable, valid_readonly = _sealed_read_only(bundle.canonical_bytes)
    linked = tmp_path / "linked"
    linked.mkdir()
    unlinked_fd = os.open(
        linked, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    )
    linked.rmdir()
    ordinary_directory_fd = os.open(
        tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    )
    try:
        for mode in ("NONBLOCKING", "SEALED_EMPTY", "UNLINKED_DIRECTORY"):
            broker_endpoint, worker_endpoint = socket.socketpair(
                socket.AF_UNIX, socket.SOCK_SEQPACKET
            )
            try:
                result_fd = (
                    empty_readonly if mode == "SEALED_EMPTY" else valid_readonly
                )
                directory_fd = ordinary_directory_fd
                if mode == "NONBLOCKING":
                    flags = fcntl.fcntl(worker_endpoint.fileno(), fcntl.F_GETFL)
                    fcntl.fcntl(
                        worker_endpoint.fileno(),
                        fcntl.F_SETFL,
                        flags | os.O_NONBLOCK,
                    )
                elif mode == "UNLINKED_DIRECTORY":
                    directory_fd = unlinked_fd
                with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error):
                    worker.execute_v075_k7_broker_worker_core_v1(
                        expected_request_replay=replay,
                        binding=binding,
                        endpoint=worker_endpoint,
                        sealed_business_result_fd=result_fd,
                        output_directory_fd=directory_fd,
                    )
                broker_endpoint.setblocking(False)
                with pytest.raises(BlockingIOError):
                    broker_endpoint.recv(1)
            finally:
                broker_endpoint.close()
                worker_endpoint.close()
    finally:
        os.close(ordinary_directory_fd)
        os.close(unlinked_fd)
        os.close(empty_readonly)
        os.close(empty_writable)
        os.close(valid_readonly)
        os.close(valid_writable)


def test_post_issue_output_mutation_is_rejected_before_commit(
    tmp_path, substrate
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    object.__setattr__(output, "_raw", b"{}")
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        with pytest.raises(worker.V075K7BrokerWorkerEntryV1Error):
            worker._commit_output(output=output, directory_fd=directory_fd)  # noqa: SLF001
        assert list(tmp_path.iterdir()) == []
    finally:
        os.close(directory_fd)


def test_output_external_issuance_seal_rejects_complete_state_transplant(
    substrate,
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    alternate_binding = ipc.K7OuterAttemptBrokerIPCBindingV1(
        binding.request_id,
        binding.route_identity_id,
        _id("transplant-broker-execution-spec"),
        _id("transplant-session-nonce"),
    )
    alternate = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=alternate_binding,
        bundle=bundle,
    )
    for name, value in (
        ("_validated_raw", alternate.canonical_bytes),
        ("_validated_output_id", alternate.output_id),
        ("_validated_expected_identity_primitives", ()),
    ):
        with pytest.raises(AttributeError):
            object.__setattr__(output, name, value)
    object.__setattr__(output, "_raw", alternate.canonical_bytes)
    object.__setattr__(output, "_request_replay", replay)
    object.__setattr__(output, "_binding", alternate_binding)
    with pytest.raises(
        worker.V075K7BrokerWorkerEntryV1Error,
        match="changed after issuance",
    ):
        _ = output.output_id


def test_equal_raw_outputs_keep_original_equality_and_independent_seals(
    substrate,
) -> None:
    replay, bundle, binding = substrate
    first = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    second = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    raw = second.canonical_bytes
    assert first is not second
    assert first == second
    assert hash(first) == hash(second) == hash((raw,))
    first_record = worker._output_issuance_record_v1(first)  # noqa: SLF001
    second_record = worker._output_issuance_record_v1(second)  # noqa: SLF001
    assert first_record is not second_record
    expected_id = second.output_id

    object.__setattr__(first, "_raw", b"{}")
    with pytest.raises(
        worker.V075K7BrokerWorkerEntryV1Error,
        match="changed after issuance",
    ):
        first.output_id
    assert second.output_id == expected_id


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires POSIX fork")
def test_output_issuance_seal_rejects_cross_pid_use(substrate) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    reader, writer = os.pipe()
    child_pid = os.fork()
    if child_pid == 0:  # pragma: no cover - asserted through the pipe
        os.close(reader)
        outcome = b"unexpected-accept"
        try:
            _ = output.output_id
        except worker.V075K7BrokerWorkerEntryV1Error:
            outcome = b"rejected"
        except BaseException:
            outcome = b"wrong-error"
        os.write(writer, outcome)
        os.close(writer)
        os._exit(0)
    os.close(writer)
    try:
        outcome = os.read(reader, 64)
    finally:
        os.close(reader)
    waited_pid, status = os.waitpid(child_pid, 0)
    assert waited_pid == child_pid
    assert os.waitstatus_to_exitcode(status) == 0
    assert outcome == b"rejected"


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires POSIX fork")
def test_output_fork_child_reinitializes_parent_held_issuance_lock(
    substrate,
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    reader, writer = os.pipe()
    parent_lock = worker._OUTPUT_ISSUANCE_LOCK  # noqa: SLF001
    parent_lock.acquire()
    child_pid = os.fork()
    if child_pid == 0:  # pragma: no cover - asserted through the pipe
        os.close(reader)
        signal.alarm(5)
        outcome = b"unexpected-accept"
        try:
            _ = output.output_id
        except worker.V075K7BrokerWorkerEntryV1Error:
            outcome = b"rejected"
        except BaseException:
            outcome = b"wrong-error"
        os.write(writer, outcome)
        signal.alarm(0)
        os.close(writer)
        os._exit(0)
    os.close(writer)
    try:
        outcome = os.read(reader, 64)
    finally:
        parent_lock.release()
        os.close(reader)
    waited_pid, status = os.waitpid(child_pid, 0)
    assert waited_pid == child_pid
    assert os.waitstatus_to_exitcode(status) == 0
    assert outcome == b"rejected"


def test_post_rename_failure_retains_typed_state_and_recovers(
    tmp_path, substrate, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    real_fsync = os.fsync

    def fail_directory_fsync(descriptor: int) -> None:
        if descriptor == directory_fd:
            raise OSError(5, "injected directory fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(worker.os, "fsync", fail_directory_fsync)
    try:
        with pytest.raises(
            worker.V075K7BrokerWorkerCommitBoundaryV1Error
        ) as captured:
            worker._commit_output(output=output, directory_fd=directory_fd)  # noqa: SLF001
        boundary = captured.value
        assert boundary.commit_stage == "RENAMED_NOREPLACE"
        assert boundary.commit_receipt is None
        assert boundary.output_directory_contaminated is True
        assert (tmp_path / worker.OUTPUT_NAME).exists()
        monkeypatch.setattr(worker.os, "fsync", real_fsync)
        foreign_root = tmp_path / "foreign-recovery"
        foreign_root.mkdir()
        (foreign_root / worker.OUTPUT_NAME).write_bytes(output.canonical_bytes)
        foreign_fd = os.open(
            foreign_root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        )
        try:
            with pytest.raises(
                worker.V075K7BrokerWorkerEntryV1Error,
                match="crossed its retained directory",
            ):
                worker.recover_v075_k7_broker_committed_output_v1(
                    boundary_error=boundary,
                    output_directory_fd=foreign_fd,
                    expected_request_replay=replay,
                    expected_binding=binding,
                )
        finally:
            os.close(foreign_fd)
        recovered, receipt = worker.recover_v075_k7_broker_committed_output_v1(
            boundary_error=boundary,
            output_directory_fd=directory_fd,
            expected_request_replay=replay,
            expected_binding=binding,
        )
        assert recovered.output_id == output.output_id
        assert receipt.recovered_after_boundary_failure is True
        with pytest.raises(AttributeError):
            boundary.rename_noreplace_completed = False
    finally:
        os.close(directory_fd)


def test_concurrent_name_replacement_is_detected(
    tmp_path, substrate, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    real_read = worker._read_committed  # noqa: SLF001

    def replace_after_pinned_read(descriptor: int, expected_size: int):
        result = real_read(descriptor, expected_size)
        os.rename(
            worker.OUTPUT_NAME,
            "moved-output",
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        replacement = os.open(
            worker.OUTPUT_NAME,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=directory_fd,
        )
        os.write(replacement, b"replacement")
        os.close(replacement)
        return result

    monkeypatch.setattr(worker, "_read_committed", replace_after_pinned_read)
    try:
        with pytest.raises(worker.V075K7BrokerWorkerCommitBoundaryV1Error):
            worker._commit_output(output=output, directory_fd=directory_fd)  # noqa: SLF001
        assert (tmp_path / worker.OUTPUT_NAME).read_bytes() == b"replacement"
    finally:
        os.close(directory_fd)


def test_short_writes_are_completed_and_rename_collision_is_not_overwritten(
    tmp_path, substrate, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    real_write = os.write

    def short_write(descriptor: int, raw: bytes) -> int:
        return real_write(descriptor, raw[: min(7, len(raw))])

    monkeypatch.setattr(worker.os, "write", short_write)
    try:
        receipt = worker._commit_output(  # noqa: SLF001
            output=output,
            directory_fd=directory_fd,
        )
        assert receipt.output_byte_count == len(output.canonical_bytes)
        assert (tmp_path / worker.OUTPUT_NAME).read_bytes() == output.canonical_bytes
    finally:
        os.close(directory_fd)

    second_root = tmp_path / "collision"
    second_root.mkdir()
    second_fd = os.open(second_root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    real_rename = worker._rename_noreplace  # noqa: SLF001

    def collide(directory: int, old_name: str, new_name: str) -> None:
        collision_fd = os.open(
            new_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=directory,
        )
        real_write(collision_fd, b"collision")
        os.close(collision_fd)
        real_rename(directory, old_name, new_name)

    monkeypatch.setattr(worker.os, "write", real_write)
    monkeypatch.setattr(worker, "_rename_noreplace", collide)
    try:
        with pytest.raises(
            worker.V075K7BrokerWorkerEntryV1Error,
            match="refused an existing name",
        ):
            worker._commit_output(output=output, directory_fd=second_fd)  # noqa: SLF001
        assert (second_root / worker.OUTPUT_NAME).read_bytes() == b"collision"
        assert not any(path.name.endswith(".tmp") for path in second_root.iterdir())
    finally:
        os.close(second_fd)


def test_raced_preexisting_temporary_name_is_never_unlinked(
    tmp_path, substrate, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    temporary_name = f".{output.output_id}.tmp"
    real_open = worker.os.open
    injected = False

    def race_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal injected
        if path == temporary_name and not injected:
            injected = True
            attacker = real_open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                0o600,
                dir_fd=dir_fd,
            )
            os.write(attacker, b"attacker-owned")
            os.close(attacker)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(worker.os, "open", race_open)
    try:
        with pytest.raises(
            worker.V075K7BrokerWorkerEntryV1Error,
            match="refused an existing name",
        ):
            worker._commit_output(output=output, directory_fd=directory_fd)  # noqa: SLF001
        assert (tmp_path / temporary_name).read_bytes() == b"attacker-owned"
    finally:
        os.close(directory_fd)


def test_temporary_name_inode_swap_is_reported_without_deleting_foreign_file(
    tmp_path, substrate, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay, bundle, binding = substrate
    output = worker._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    temporary_name = f".{output.output_id}.tmp"

    def swap_then_fail(_descriptor: int, _raw: bytes) -> None:
        os.rename(
            temporary_name,
            "moved-owned-temp",
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        foreign = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o600,
            dir_fd=directory_fd,
        )
        os.write(foreign, b"foreign")
        os.close(foreign)
        raise OSError(5, "injected post-swap write failure")

    monkeypatch.setattr(worker, "_write_all", swap_then_fail)
    try:
        with pytest.raises(
            worker.V075K7BrokerWorkerCommitBoundaryV1Error
        ) as raised:
            worker._commit_output(output=output, directory_fd=directory_fd)  # noqa: SLF001
        assert raised.value.rename_noreplace_completed is False
        assert raised.value.output_directory_contaminated is True
        assert (tmp_path / temporary_name).read_bytes() == b"foreign"
    finally:
        os.close(directory_fd)


def test_suffix_failure_carries_committed_receipt(
    tmp_path, substrate, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay, bundle, binding = substrate
    writable, readonly = _sealed_read_only(bundle.canonical_bytes)
    broker_endpoint, worker_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET
    )
    output_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    real_send = worker._send_packet  # noqa: SLF001
    calls = 0

    def fail_suffix(endpoint: socket.socket, raw: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError(32, "injected suffix failure")
        real_send(endpoint, raw)

    monkeypatch.setattr(worker, "_send_packet", fail_suffix)
    try:
        broker_endpoint.send(_result_frame(binding, bundle.bundle_id))
        broker_endpoint.shutdown(socket.SHUT_WR)
        with pytest.raises(
            worker.V075K7BrokerWorkerCommitBoundaryV1Error
        ) as captured:
            worker.execute_v075_k7_broker_worker_core_v1(
                expected_request_replay=replay,
                binding=binding,
                endpoint=worker_endpoint,
                sealed_business_result_fd=readonly,
                output_directory_fd=output_fd,
            )
        assert captured.value.commit_stage == "OUTPUT_COMMITTED_SUFFIX_INCOMPLETE"
        assert captured.value.commit_receipt is not None
        assert (tmp_path / worker.OUTPUT_NAME).exists()
    finally:
        os.close(output_fd)
        broker_endpoint.close()
        worker_endpoint.close()
        os.close(readonly)
        os.close(writable)
