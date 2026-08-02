from __future__ import annotations

import fcntl
import os
from pathlib import Path
import pickle
import socket

import pytest

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime
from acfqp import v075_k7_business_entry_core_v1 as core
from acfqp import v075_k7_child_business_bundle_v1 as business
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc
from tests import test_v075_k7_child_business_bundle_v1 as bundle_fixture


def _empty_memfd() -> int:
    if not callable(getattr(os, "memfd_create", None)):
        pytest.skip("memfd_create is unavailable")
    return os.memfd_create(
        "acfqp-k7-business-entry-test",
        runtime.MFD_CLOEXEC | runtime.MFD_ALLOW_SEALING,
    )


def _binding(request) -> ipc.K7OuterAttemptBrokerIPCBindingV1:
    return ipc.K7OuterAttemptBrokerIPCBindingV1(
        request.request_id,
        request.route_identity.route_identity_id,
        bundle_fixture._id("broker-execution-spec"),  # noqa: SLF001
        bundle_fixture._id("broker-session-nonce"),  # noqa: SLF001
    )


def _inputs() -> tuple[int, int]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    return os.open("/dev/null", flags), os.open("/dev/null", flags)


def _socketpair(
    socket_type: int = socket.SOCK_SEQPACKET,
) -> tuple[socket.socket, socket.socket]:
    try:
        return socket.socketpair(socket.AF_UNIX, socket_type)
    except OSError:
        if socket_type == socket.SOCK_SEQPACKET:
            pytest.skip("AF_UNIX SOCK_SEQPACKET is unavailable")
        raise


def _assert_no_packet(peer: socket.socket) -> None:
    peer.setblocking(False)
    with pytest.raises(BlockingIOError):
        peer.recv(ipc.MAX_FRAME_BYTES + ipc.FRAME_WIDTH)


def _execute(
    *,
    replay,
    output_memfd: int,
    endpoint: socket.socket,
    binding: ipc.K7OuterAttemptBrokerIPCBindingV1,
    source_fd: int,
    secret_fd: int,
):
    return core.execute_v075_k7_business_entry_core_v1(
        request_replay=replay,
        source_archive_fd=source_fd,
        sealed_secret_fd=secret_fd,
        repository_root=Path("/unused/repository"),
        signer_private_root=Path("/unused/private"),
        signer_private_key_path=Path("/unused/private/key.json"),
        output_memfd=output_memfd,
        business_result_endpoint=endpoint,
        binding=binding,
    )


def test_business_entry_commits_bundle_and_emits_exactly_one_bound_packet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, _portable, _wrapped, _authority, bundle = (
        bundle_fixture._substrate(monkeypatch)  # noqa: SLF001
    )
    calls: list[dict] = []

    def execute_once(**kwargs):
        calls.append(kwargs)
        return bundle

    monkeypatch.setattr(
        core.business_v1,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        execute_once,
    )
    output_memfd = _empty_memfd()
    endpoint, peer = _socketpair()
    source_fd, secret_fd = _inputs()
    binding = _binding(request)
    try:
        emission = _execute(
            replay=replay,
            output_memfd=output_memfd,
            endpoint=endpoint,
            binding=binding,
            source_fd=source_fd,
            secret_fd=secret_fd,
        )
        assert len(calls) == 1
        assert calls[0]["request_replay"] is replay
        assert calls[0]["source_archive_fd"] == source_fd
        assert calls[0]["sealed_secret_fd"] == secret_fd

        assert os.pread(output_memfd, len(bundle.canonical_bytes), 0) == (
            bundle.canonical_bytes
        )
        assert fcntl.fcntl(output_memfd, runtime.F_GET_SEALS) == (
            runtime.REQUIRED_MEMFD_SEALS
        )
        packet = peer.recv(ipc.MAX_FRAME_BYTES + ipc.FRAME_WIDTH)
        frame = ipc.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
            raw=packet,
            expected_binding=binding,
            expected_role=ipc.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT,
        )
        assert frame.frame_id == emission.business_result_frame.frame_id
        assert dict(frame.payload) == {"business_result_id": bundle.bundle_id}
        _assert_no_packet(peer)

        assert emission.business_bundle is bundle
        assert emission.binding is not binding
        assert emission.binding.to_document() == binding.to_document()
        assert emission.output_memfd == output_memfd
        assert emission.endpoint_fd == endpoint.fileno()
        document = emission.to_document()
        assert document["business_executor_invocations"] == 1
        assert document["business_result_send_calls"] == 1
        assert document["caller_descriptors_closed"] == 0
        assert document["issuer_owned_nonformal_historical_emission"] is True
        assert document["publication_operated_on_owned_duplicates"] is True
        assert document["same_address_space_private_sentinel_is_security_capability"] is False
        assert all(document[key] is False for key in core._formal_locks())  # noqa: SLF001
        profile = core.official_v075_k7_business_entry_core_profile_v1()
        profile_document = profile.to_document()
        assert all(
            profile_document[key] is False for key in core._formal_locks()  # noqa: SLF001
        )
        with pytest.raises(TypeError, match="process-local"):
            pickle.dumps(emission)

        # The core does not consume caller ownership of either descriptor.
        os.fstat(output_memfd)
        os.fstat(endpoint.fileno())
    finally:
        os.close(source_fd)
        os.close(secret_fd)
        endpoint.close()
        peer.close()
        os.close(output_memfd)


def test_crossed_binding_fails_before_execution_or_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, _portable, _wrapped, _authority, bundle = (
        bundle_fixture._substrate(monkeypatch)  # noqa: SLF001
    )
    calls = 0

    def forbidden_execute(**_kwargs):
        nonlocal calls
        calls += 1
        return bundle

    monkeypatch.setattr(
        core.business_v1,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        forbidden_execute,
    )
    crossed = ipc.K7OuterAttemptBrokerIPCBindingV1(
        bundle_fixture._id("crossed-request"),  # noqa: SLF001
        request.route_identity.route_identity_id,
        bundle_fixture._id("broker-execution-spec"),  # noqa: SLF001
        bundle_fixture._id("broker-session-nonce"),  # noqa: SLF001
    )
    output_memfd = _empty_memfd()
    endpoint, peer = _socketpair()
    source_fd, secret_fd = _inputs()
    try:
        with pytest.raises(core.V075K7BusinessEntryCoreV1Error, match="crossed"):
            _execute(
                replay=replay,
                output_memfd=output_memfd,
                endpoint=endpoint,
                binding=crossed,
                source_fd=source_fd,
                secret_fd=secret_fd,
            )
        assert calls == 0
        assert os.fstat(output_memfd).st_size == 0
        assert fcntl.fcntl(output_memfd, runtime.F_GET_SEALS) == 0
        _assert_no_packet(peer)
    finally:
        os.close(source_fd)
        os.close(secret_fd)
        endpoint.close()
        peer.close()
        os.close(output_memfd)


@pytest.mark.parametrize("invalid_output", ("NONEMPTY", "PRESEALED"))
def test_output_must_be_caller_provided_empty_unsealed_memfd_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    invalid_output: str,
) -> None:
    request, replay, _portable, _wrapped, _authority, bundle = (
        bundle_fixture._substrate(monkeypatch)  # noqa: SLF001
    )
    calls = 0

    def forbidden_execute(**_kwargs):
        nonlocal calls
        calls += 1
        return bundle

    monkeypatch.setattr(
        core.business_v1,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        forbidden_execute,
    )
    output_memfd = _empty_memfd()
    if invalid_output == "NONEMPTY":
        os.write(output_memfd, b"forged")
    else:
        fcntl.fcntl(
            output_memfd,
            runtime.F_ADD_SEALS,
            runtime.REQUIRED_MEMFD_SEALS,
        )
    endpoint, peer = _socketpair()
    source_fd, secret_fd = _inputs()
    try:
        with pytest.raises(core.V075K7BusinessEntryCoreV1Error, match="output memfd"):
            _execute(
                replay=replay,
                output_memfd=output_memfd,
                endpoint=endpoint,
                binding=_binding(request),
                source_fd=source_fd,
                secret_fd=secret_fd,
            )
        assert calls == 0
        _assert_no_packet(peer)
    finally:
        os.close(source_fd)
        os.close(secret_fd)
        endpoint.close()
        peer.close()
        os.close(output_memfd)


def test_stream_endpoint_is_rejected_before_business_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, _portable, _wrapped, _authority, bundle = (
        bundle_fixture._substrate(monkeypatch)  # noqa: SLF001
    )
    calls = 0

    def forbidden_execute(**_kwargs):
        nonlocal calls
        calls += 1
        return bundle

    monkeypatch.setattr(
        core.business_v1,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        forbidden_execute,
    )
    output_memfd = _empty_memfd()
    endpoint, peer = _socketpair(socket.SOCK_STREAM)
    source_fd, secret_fd = _inputs()
    try:
        with pytest.raises(core.V075K7BusinessEntryCoreV1Error, match="SEQPACKET"):
            _execute(
                replay=replay,
                output_memfd=output_memfd,
                endpoint=endpoint,
                binding=_binding(request),
                source_fd=source_fd,
                secret_fd=secret_fd,
            )
        assert calls == 0
        assert os.fstat(output_memfd).st_size == 0
    finally:
        os.close(source_fd)
        os.close(secret_fd)
        endpoint.close()
        peer.close()
        os.close(output_memfd)


def test_kernel_nonblocking_endpoint_is_rejected_before_business_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, _portable, _wrapped, _authority, bundle = (
        bundle_fixture._substrate(monkeypatch)  # noqa: SLF001
    )
    calls = 0

    def forbidden_execute(**_kwargs):
        nonlocal calls
        calls += 1
        return bundle

    monkeypatch.setattr(
        core.business_v1,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        forbidden_execute,
    )
    output_memfd = _empty_memfd()
    endpoint, peer = _socketpair()
    source_fd, secret_fd = _inputs()
    old_flags = fcntl.fcntl(endpoint.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(endpoint.fileno(), fcntl.F_SETFL, old_flags | os.O_NONBLOCK)
    assert endpoint.gettimeout() is None
    try:
        with pytest.raises(core.V075K7BusinessEntryCoreV1Error, match="blocking"):
            _execute(
                replay=replay,
                output_memfd=output_memfd,
                endpoint=endpoint,
                binding=_binding(request),
                source_fd=source_fd,
                secret_fd=secret_fd,
            )
        assert calls == 0
        assert os.fstat(output_memfd).st_size == 0
    finally:
        os.close(source_fd)
        os.close(secret_fd)
        endpoint.close()
        peer.close()
        os.close(output_memfd)


def test_kernel_domain_mismatch_is_rejected_even_with_unix_socket_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(socket, "SO_DOMAIN"):
        pytest.skip("Linux SO_DOMAIN is required")
    endpoint, peer = _socketpair()
    try:
        # Redirect the queried kernel option to one whose value cannot equal
        # AF_UNIX.  The Python wrapper still reports family=AF_UNIX; rejection
        # therefore depends on the independent getsockopt result.
        monkeypatch.setattr(core.socket, "SO_DOMAIN", socket.SO_TYPE)
        with pytest.raises(core.V075K7BusinessEntryCoreV1Error, match="AF_UNIX"):
            core._inspect_endpoint(endpoint)  # noqa: SLF001
        assert endpoint.family == socket.AF_UNIX
    finally:
        endpoint.close()
        peer.close()


def test_business_failure_leaves_empty_memfd_and_emits_no_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, _portable, _wrapped, _authority, _bundle = (
        bundle_fixture._substrate(monkeypatch)  # noqa: SLF001
    )

    def fail_once(**_kwargs):
        raise RuntimeError("injected business failure")

    monkeypatch.setattr(
        core.business_v1,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        fail_once,
    )
    output_memfd = _empty_memfd()
    endpoint, peer = _socketpair()
    source_fd, secret_fd = _inputs()
    try:
        with pytest.raises(
            core.V075K7BusinessEntryCoreV1Error,
            match="business execution failed",
        ):
            _execute(
                replay=replay,
                output_memfd=output_memfd,
                endpoint=endpoint,
                binding=_binding(request),
                source_fd=source_fd,
                secret_fd=secret_fd,
            )
        assert os.fstat(output_memfd).st_size == 0
        assert fcntl.fcntl(output_memfd, runtime.F_GET_SEALS) == 0
        _assert_no_packet(peer)
    finally:
        os.close(source_fd)
        os.close(secret_fd)
        endpoint.close()
        peer.close()
        os.close(output_memfd)


def test_binding_mutation_during_business_execution_cannot_redirect_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, _portable, _wrapped, _authority, bundle = (
        bundle_fixture._substrate(monkeypatch)  # noqa: SLF001
    )
    binding = _binding(request)

    def mutate_binding(**_kwargs):
        object.__setattr__(
            binding,
            "broker_execution_spec_id",
            bundle_fixture._id("mutated-broker-execution-spec"),  # noqa: SLF001
        )
        return bundle

    monkeypatch.setattr(
        core.business_v1,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        mutate_binding,
    )
    output_memfd = _empty_memfd()
    endpoint, peer = _socketpair()
    source_fd, secret_fd = _inputs()
    try:
        with pytest.raises(
            core.V075K7BusinessEntryCoreV1Error,
            match="binding changed",
        ):
            _execute(
                replay=replay,
                output_memfd=output_memfd,
                endpoint=endpoint,
                binding=binding,
                source_fd=source_fd,
                secret_fd=secret_fd,
            )
        assert os.fstat(output_memfd).st_size == 0
        assert fcntl.fcntl(output_memfd, runtime.F_GET_SEALS) == 0
        _assert_no_packet(peer)
    finally:
        os.close(source_fd)
        os.close(secret_fd)
        endpoint.close()
        peer.close()
        os.close(output_memfd)


def test_partial_write_failure_is_rolled_back_before_sealing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, _portable, _wrapped, _authority, bundle = (
        bundle_fixture._substrate(monkeypatch)  # noqa: SLF001
    )
    monkeypatch.setattr(
        core.business_v1,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        lambda **_kwargs: bundle,
    )
    original_pwrite = core.os.pwrite
    calls = 0

    def fail_after_prefix(descriptor, raw, offset):
        nonlocal calls
        calls += 1
        if calls == 1:
            prefix = raw[: min(16, len(raw))]
            return original_pwrite(descriptor, prefix, offset)
        raise OSError("injected partial pwrite failure")

    monkeypatch.setattr(core.os, "pwrite", fail_after_prefix)
    output_memfd = _empty_memfd()
    endpoint, peer = _socketpair()
    source_fd, secret_fd = _inputs()
    try:
        with pytest.raises(
            core.V075K7BusinessEntryCoreV1Error,
            match="rolled back",
        ) as raised:
            _execute(
                replay=replay,
                output_memfd=output_memfd,
                endpoint=endpoint,
                binding=_binding(request),
                source_fd=source_fd,
                secret_fd=secret_fd,
            )
        assert not isinstance(
            raised.value, core.V075K7BusinessEntryBoundaryV1Error
        )
        assert os.fstat(output_memfd).st_size == 0
        assert fcntl.fcntl(output_memfd, runtime.F_GET_SEALS) == 0
        _assert_no_packet(peer)
    finally:
        os.close(source_fd)
        os.close(secret_fd)
        endpoint.close()
        peer.close()
        os.close(output_memfd)


def test_second_public_replay_failure_prevents_frame_after_immutable_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, _portable, _wrapped, _authority, bundle = (
        bundle_fixture._substrate(monkeypatch)  # noqa: SLF001
    )
    monkeypatch.setattr(
        core.business_v1,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        lambda **_kwargs: bundle,
    )
    original_verify = (
        business.verify_v075_k7_child_business_bundle_public_bytes_v1
    )
    replay_calls = 0

    def fail_second_replay(**kwargs):
        nonlocal replay_calls
        replay_calls += 1
        if replay_calls == 2:
            raise RuntimeError("injected sealed replay failure")
        return original_verify(**kwargs)

    monkeypatch.setattr(
        core.business_v1,
        "verify_v075_k7_child_business_bundle_public_bytes_v1",
        fail_second_replay,
    )
    output_memfd = _empty_memfd()
    endpoint, peer = _socketpair()
    source_fd, secret_fd = _inputs()
    try:
        with pytest.raises(
            core.V075K7BusinessEntryBoundaryV1Error,
            match="sealed child business bundle failed public replay",
        ) as raised:
            _execute(
                replay=replay,
                output_memfd=output_memfd,
                endpoint=endpoint,
                binding=_binding(request),
                source_fd=source_fd,
                secret_fd=secret_fd,
            )
        assert replay_calls == 2
        assert os.pread(output_memfd, len(bundle.canonical_bytes), 0) == (
            bundle.canonical_bytes
        )
        assert fcntl.fcntl(output_memfd, runtime.F_GET_SEALS) == (
            runtime.REQUIRED_MEMFD_SEALS
        )
        assert raised.value.stage is core.K7BusinessPublicationStageV1.SEALED_UNANNOUNCED
        assert raised.value.packet_delivery_verified is False
        assert raised.value.rollback_complete is False
        assert raised.value.to_document()["formal_accounting_authority"] is False
        _assert_no_packet(peer)
    finally:
        os.close(source_fd)
        os.close(secret_fd)
        endpoint.close()
        peer.close()
        os.close(output_memfd)


def test_failed_send_returns_typed_unknown_boundary_after_sealing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, _portable, _wrapped, _authority, bundle = (
        bundle_fixture._substrate(monkeypatch)  # noqa: SLF001
    )
    monkeypatch.setattr(
        core.business_v1,
        "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
        lambda **_kwargs: bundle,
    )
    output_memfd = _empty_memfd()
    endpoint, peer = _socketpair()
    source_fd, secret_fd = _inputs()
    peer.close()
    try:
        with pytest.raises(
            core.V075K7BusinessEntryBoundaryV1Error,
            match="send outcome is unknown",
        ) as raised:
            _execute(
                replay=replay,
                output_memfd=output_memfd,
                endpoint=endpoint,
                binding=_binding(request),
                source_fd=source_fd,
                secret_fd=secret_fd,
            )
        assert raised.value.stage is core.K7BusinessPublicationStageV1.SEND_OUTCOME_UNKNOWN
        assert raised.value.framed_packet is not None
        assert raised.value.packet_delivery_verified is False
        assert fcntl.fcntl(output_memfd, runtime.F_GET_SEALS) == (
            runtime.REQUIRED_MEMFD_SEALS
        )
    finally:
        os.close(source_fd)
        os.close(secret_fd)
        endpoint.close()
        os.close(output_memfd)
