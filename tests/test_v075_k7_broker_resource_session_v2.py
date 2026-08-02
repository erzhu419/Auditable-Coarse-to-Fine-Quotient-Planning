from __future__ import annotations

import fcntl
import os
from pathlib import Path
import pickle
import socket
import stat
from typing import Iterator

import pytest

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_broker_resource_session_v2 as session_v2
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_production_role_bootstrap_v2 as bootstrap_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _id, _successor_request


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def frozen_manifest(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[object, manifest_v2.K7ProductionRoleManifestV2]]:
    root = tmp_path_factory.mktemp("broker-resource-session-v2")
    private_root = (root / "private").resolve()
    private_root.mkdir(mode=0o700)
    private_key = (private_root / "observer-key.json").resolve()
    private_key.write_bytes(b"broker-resource-session-v2-static-key")
    private_key.chmod(0o600)
    request = _successor_request("broker-resource-session-v2-base")
    manifest = manifest_v2.freeze_v075_k7_production_role_manifest_v2(
        request=request,
        repository_root=REPOSITORY_ROOT,
        signer_private_root=private_root,
        signer_private_key_path=private_key,
    )
    yield request, manifest


def _contexts(
    request: object,
    manifest: manifest_v2.K7ProductionRoleManifestV2,
    label: str,
    *,
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1 | None = None,
) -> tuple[
    ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    manifest_v2.K7ProductionRoleLaunchContextV2,
    manifest_v2.K7ProductionRoleLaunchContextV2,
]:
    exact_binding = binding or ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
        request.request_id,
        request.route_identity.route_identity_id,
        _id(f"broker-resource-spec-{label}"),
        _id(f"broker-resource-nonce-{label}"),
    )
    worker = manifest_v2.freeze_v075_k7_production_role_launch_context_v2(
        manifest=manifest,
        binding=exact_binding,
        role=manifest_v2.K7ProductionBrokerRoleV2.WORKER,
    )
    business = manifest_v2.freeze_v075_k7_production_role_launch_context_v2(
        manifest=manifest,
        binding=exact_binding,
        role=manifest_v2.K7ProductionBrokerRoleV2.BUSINESS,
    )
    return exact_binding, worker, business


def _prepare(
    tmp_path: Path,
    frozen_manifest: tuple[object, manifest_v2.K7ProductionRoleManifestV2],
    label: str,
) -> tuple[session_v2.K7BrokerResourceSessionV2, Path]:
    request, manifest = frozen_manifest
    _binding, worker, business = _contexts(request, manifest, label)
    output_parent = (tmp_path / f"output-parent-{label}").resolve()
    output_parent.mkdir(mode=0o700)
    parent_fd = os.open(
        output_parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        session = session_v2.prepare_v075_k7_broker_resource_session_v2(
            manifest=manifest,
            worker_context=worker,
            business_context=business,
            output_parent_fd=parent_fd,
        )
    finally:
        os.close(parent_fd)
    return session, output_parent


def _socket_option(descriptor: int, option: int) -> int:
    duplicate = fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, 3)
    endpoint = socket.socket(fileno=duplicate)
    try:
        return endpoint.getsockopt(socket.SOL_SOCKET, option)
    finally:
        endpoint.close()


def _set_socket_option(descriptor: int, option: int, value: int) -> None:
    duplicate = fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, 3)
    endpoint = socket.socket(fileno=duplicate)
    try:
        endpoint.setsockopt(socket.SOL_SOCKET, option, value)
    finally:
        endpoint.close()


def test_preparation_issues_exact_role_bundles_without_launch_or_receipts(
    tmp_path: Path,
    frozen_manifest: tuple[object, manifest_v2.K7ProductionRoleManifestV2],
) -> None:
    assert set(session_v2.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
    assert (
        session_v2.official_v075_k7_broker_resource_session_profile_v2()
        .to_document()["central_domain_registration_pending_merge"]
        is False
    )
    session, output_parent = _prepare(tmp_path, frozen_manifest, "happy")
    try:
        session.assert_current()
        worker = session.worker_capabilities
        business = session.business_capabilities
        assert worker.descriptor_roles == bootstrap_v2.WORKER_CAPABILITY_ROLES
        assert business.descriptor_roles == bootstrap_v2.BUSINESS_CAPABILITY_ROLES
        role_descriptors = tuple(
            worker.descriptor(role) for role in worker.descriptor_roles
        ) + tuple(business.descriptor(role) for role in business.descriptor_roles)
        assert len(role_descriptors) == len(set(role_descriptors)) == 5
        assert set(session_v2.BROKER_DESCRIPTOR_ROLES) == {
            "WORKER_CHANNEL",
            "BUSINESS_CHANNEL",
            "BUSINESS_RESULT_READONLY",
            "OUTPUT_DIRECTORY",
        }
        broker_descriptors = tuple(
            session.broker_descriptor(role)
            for role in session_v2.BROKER_DESCRIPTOR_ROLES
        )
        assert len(broker_descriptors) == len(set(broker_descriptors)) == 4
        assert not set(role_descriptors).intersection(broker_descriptors)

        document = session.to_document()
        assert document["processes_launched"] == 0
        assert document["protocol_frames_sent"] == 0
        assert document["post_reap_envelope"] is None
        assert document["shared_resource_receipts"] is None
        assert all(value is False for value in document["formal_locks"].values())
        for bundle in (worker, business):
            bundle_document = bundle.to_document()
            assert bundle_document["raw_descriptor_numbers_serialized"] is False
            assert set(bundle_document) == {
                "schema",
                "schema_version",
                "proposed_contract_version",
                "profile_key",
                "broker_resource_session_profile_id",
                "role",
                "production_role_manifest_id",
                "production_role_launch_context_id",
                "request_id",
                "route_identity_id",
                "broker_execution_spec_id",
                "session_nonce",
                "capability_fd_roles",
                "descriptor_identities",
                "raw_descriptor_numbers_serialized",
                "sealed_input_fd_lane_included",
                "caller_selected_fd_roles",
                "construction_only",
                "formal_locks",
                "broker_role_capability_bundle_id",
            }
    finally:
        session.close()
    assert session.guardian.state is session_v2.K7BrokerResourceSessionStateV2.CLOSED
    assert list(output_parent.iterdir()) == []


def test_kernel_topology_is_seqpacket_passcred_rw_ro_and_worker_only_output(
    tmp_path: Path,
    frozen_manifest: tuple[object, manifest_v2.K7ProductionRoleManifestV2],
) -> None:
    session, _output_parent = _prepare(tmp_path, frozen_manifest, "topology")
    try:
        worker_channel = session.worker_capabilities.descriptor("BROKER_CHANNEL")
        business_channel = session.business_capabilities.descriptor("BROKER_CHANNEL")
        broker_worker_channel = session.broker_descriptor("WORKER_CHANNEL")
        broker_business_channel = session.broker_descriptor("BUSINESS_CHANNEL")
        for descriptor in (
            worker_channel,
            business_channel,
            broker_worker_channel,
            broker_business_channel,
        ):
            assert _socket_option(descriptor, socket.SO_DOMAIN) == socket.AF_UNIX
            assert _socket_option(descriptor, socket.SO_TYPE) == socket.SOCK_SEQPACKET
            assert os.get_inheritable(descriptor) is False
            assert fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_NONBLOCK == 0
        assert _socket_option(worker_channel, socket.SO_PASSCRED) == 0
        assert _socket_option(business_channel, socket.SO_PASSCRED) == 0
        assert _socket_option(broker_worker_channel, socket.SO_PASSCRED) == 1
        assert _socket_option(broker_business_channel, socket.SO_PASSCRED) == 1

        writable = session.business_capabilities.descriptor(
            "BUSINESS_RESULT_WRITABLE"
        )
        worker_readonly = session.worker_capabilities.descriptor(
            "BUSINESS_RESULT_READONLY"
        )
        broker_readonly = session.broker_descriptor("BUSINESS_RESULT_READONLY")
        assert {
            os.fstat(descriptor).st_ino
            for descriptor in (writable, worker_readonly, broker_readonly)
        } == {os.fstat(writable).st_ino}
        assert fcntl.fcntl(writable, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDWR
        assert fcntl.fcntl(worker_readonly, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY
        assert fcntl.fcntl(broker_readonly, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY
        assert fcntl.fcntl(writable, runtime_v1.F_GET_SEALS) == 0

        worker_output = session.worker_capabilities.descriptor("OUTPUT_DIRECTORY")
        broker_output = session.broker_descriptor("OUTPUT_DIRECTORY")
        assert stat.S_ISDIR(os.fstat(worker_output).st_mode)
        assert (os.fstat(worker_output).st_dev, os.fstat(worker_output).st_ino) == (
            os.fstat(broker_output).st_dev,
            os.fstat(broker_output).st_ino,
        )
        assert worker_output != broker_output
        with pytest.raises(session_v2.V075K7BrokerResourceSessionV2Error):
            session.business_capabilities.descriptor("OUTPUT_DIRECTORY")
    finally:
        session.close()


def test_crossed_contexts_and_duplicate_preparation_fail_closed(
    tmp_path: Path,
    frozen_manifest: tuple[object, manifest_v2.K7ProductionRoleManifestV2],
) -> None:
    request, manifest = frozen_manifest
    binding, worker, business = _contexts(request, manifest, "binding-attacks")
    output_parent = (tmp_path / "binding-output-parent").resolve()
    output_parent.mkdir(mode=0o700)
    parent_fd = os.open(
        output_parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        with pytest.raises(session_v2.V075K7BrokerResourceSessionV2Error):
            session_v2.prepare_v075_k7_broker_resource_session_v2(
                manifest=manifest,
                worker_context=business,
                business_context=worker,
                output_parent_fd=parent_fd,
            )

        equal_but_distinct_binding = ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
            binding.request_id,
            binding.route_identity_id,
            binding.broker_execution_spec_id,
            binding.session_nonce,
        )
        foreign_business = manifest_v2.freeze_v075_k7_production_role_launch_context_v2(
            manifest=manifest,
            binding=equal_but_distinct_binding,
            role=manifest_v2.K7ProductionBrokerRoleV2.BUSINESS,
        )
        with pytest.raises(session_v2.V075K7BrokerResourceSessionV2Error):
            session_v2.prepare_v075_k7_broker_resource_session_v2(
                manifest=manifest,
                worker_context=worker,
                business_context=foreign_business,
                output_parent_fd=parent_fd,
            )

        session = session_v2.prepare_v075_k7_broker_resource_session_v2(
            manifest=manifest,
            worker_context=worker,
            business_context=business,
            output_parent_fd=parent_fd,
        )
        try:
            with pytest.raises(
                session_v2.V075K7BrokerResourceSessionV2Error,
                match="already own",
            ):
                session_v2.prepare_v075_k7_broker_resource_session_v2(
                    manifest=manifest,
                    worker_context=worker,
                    business_context=business,
                    output_parent_fd=parent_fd,
                )
        finally:
            session.close()
    finally:
        os.close(parent_fd)
    assert list(output_parent.iterdir()) == []


def test_socket_queue_passcred_and_output_contamination_are_detected(
    tmp_path: Path,
    frozen_manifest: tuple[object, manifest_v2.K7ProductionRoleManifestV2],
) -> None:
    session, _output_parent = _prepare(tmp_path, frozen_manifest, "tamper")
    broker_channel = session.broker_descriptor("WORKER_CHANNEL")
    child_channel = session.worker_capabilities.descriptor("BROKER_CHANNEL")
    output_directory = session.worker_capabilities.descriptor("OUTPUT_DIRECTORY")
    try:
        _set_socket_option(broker_channel, socket.SO_PASSCRED, 0)
        with pytest.raises(session_v2.V075K7BrokerResourceSessionV2Error):
            session.assert_current()
        _set_socket_option(broker_channel, socket.SO_PASSCRED, 1)
        session.assert_current()

        assert os.write(child_channel, b"x") == 1
        with pytest.raises(
            session_v2.V075K7BrokerResourceSessionV2Error,
            match="not empty",
        ):
            session.assert_current()
        assert os.read(broker_channel, 1) == b"x"
        session.assert_current()

        contaminant = os.open(
            "contaminant",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o600,
            dir_fd=output_directory,
        )
        os.close(contaminant)
        with pytest.raises(session_v2.V075K7BrokerResourceSessionV2Error):
            session.assert_current()
        os.unlink("contaminant", dir_fd=output_directory)
        session.assert_current()
    finally:
        session.close()


def test_parent_fd_and_caller_mint_attacks_fail_without_output_side_effects(
    tmp_path: Path,
    frozen_manifest: tuple[object, manifest_v2.K7ProductionRoleManifestV2],
) -> None:
    request, manifest = frozen_manifest
    _binding, worker, business = _contexts(request, manifest, "parent-attacks")
    output_parent = (tmp_path / "parent-attacks").resolve()
    output_parent.mkdir(mode=0o700)
    path_fd = os.open(
        output_parent,
        getattr(os, "O_PATH", os.O_RDONLY) | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        if hasattr(os, "O_PATH"):
            with pytest.raises(session_v2.V075K7BrokerResourceSessionV2Error):
                session_v2.prepare_v075_k7_broker_resource_session_v2(
                    manifest=manifest,
                    worker_context=worker,
                    business_context=business,
                    output_parent_fd=path_fd,
                )
    finally:
        os.close(path_fd)
    assert list(output_parent.iterdir()) == []

    inherited_fd = os.open(
        output_parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    os.set_inheritable(inherited_fd, True)
    try:
        with pytest.raises(session_v2.V075K7BrokerResourceSessionV2Error):
            session_v2.prepare_v075_k7_broker_resource_session_v2(
                manifest=manifest,
                worker_context=worker,
                business_context=business,
                output_parent_fd=inherited_fd,
            )
    finally:
        os.close(inherited_fd)
    assert list(output_parent.iterdir()) == []
    with pytest.raises(
        session_v2.V075K7BrokerResourceSessionV2Error,
        match="issuer-owned",
    ):
        session_v2.K7BrokerResourceSessionProfileV2(object())


def test_process_local_authorities_are_unpickleable(
    tmp_path: Path,
    frozen_manifest: tuple[object, manifest_v2.K7ProductionRoleManifestV2],
) -> None:
    session, _output_parent = _prepare(tmp_path, frozen_manifest, "pickle")
    try:
        for authority in (
            session,
            session.guardian,
            session.worker_capabilities,
            session.business_capabilities,
        ):
            with pytest.raises(TypeError, match="process-local"):
                pickle.dumps(authority)
    finally:
        session.close()


def test_runtime_transfer_atomically_replays_revokes_session_and_binds_fds(
    tmp_path: Path,
    frozen_manifest: tuple[object, manifest_v2.K7ProductionRoleManifestV2],
) -> None:
    session, output_parent = _prepare(
        tmp_path,
        frozen_manifest,
        "runtime-transfer",
    )
    transfer: session_v2.K7BrokerRuntimeTransferAuthorityV2 | None = None
    worker_child = session.worker_capabilities.descriptor("BROKER_CHANNEL")
    broker_worker = session.broker_descriptor("WORKER_CHANNEL")
    assert os.write(worker_child, b"queued-before-transfer") == len(
        b"queued-before-transfer"
    )
    with pytest.raises(
        session_v2.V075K7BrokerResourceSessionV2Error,
        match="not empty",
    ):
        session.consume_for_runtime_v2()
    assert (
        session.guardian.state
        is session_v2.K7BrokerResourceSessionStateV2.PREPARED
    )
    assert os.read(broker_worker, 64) == b"queued-before-transfer"
    resource_session_id = session.session_id

    try:
        transfer = session.consume_for_runtime_v2()
        assert (
            session.guardian.state
            is session_v2.K7BrokerResourceSessionStateV2.RUNTIME_TRANSFERRED
        )
        assert transfer.resource_session_id == resource_session_id
        assert transfer.broker_descriptor_roles == session_v2.BROKER_DESCRIPTOR_ROLES
        assert (
            transfer.worker_descriptor_roles
            == session_v2.WORKER_RUNTIME_DESCRIPTOR_ROLES
        )
        assert (
            transfer.business_descriptor_roles
            == session_v2.BUSINESS_RUNTIME_DESCRIPTOR_ROLES
        )
        for role in transfer.broker_descriptor_roles:
            os.fstat(transfer.broker_descriptor(role))
        for role in transfer.worker_descriptor_roles:
            os.fstat(transfer.worker_descriptor(role))
        for role in transfer.business_descriptor_roles:
            os.fstat(transfer.business_descriptor(role))
        transfer.assert_current()

        for operation in (
            session.assert_current,
            session.to_document,
            session.close,
            session.consume_for_runtime_v2,
            lambda: session.broker_descriptor("WORKER_CHANNEL"),
            lambda: session.role_capabilities(
                manifest_v2.K7ProductionBrokerRoleV2.WORKER
            ),
            lambda: session.worker_capabilities.descriptor("BROKER_CHANNEL"),
        ):
            with pytest.raises(session_v2.V075K7BrokerResourceSessionV2Error):
                operation()
        with pytest.raises(TypeError, match="process-local"):
            pickle.dumps(transfer)

        target = transfer.broker_descriptor("WORKER_CHANNEL")
        backup = fcntl.fcntl(target, fcntl.F_DUPFD_CLOEXEC, 3)
        replacement = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        try:
            os.dup2(replacement, target, inheritable=False)
            with pytest.raises(
                session_v2.V075K7BrokerResourceSessionV2Error,
                match="descriptor identity changed",
            ):
                transfer.broker_descriptor("WORKER_CHANNEL")
            os.dup2(backup, target, inheritable=False)
        finally:
            os.close(backup)
            os.close(replacement)
        transfer.assert_current()
        transfer.close()
        assert transfer.closed is True
        transfer = None
    finally:
        if transfer is not None and not transfer.closed:
            transfer.close()
    assert list(output_parent.iterdir()) == []


def test_runtime_retirement_is_monotone_and_nonempty_output_is_preserved(
    tmp_path: Path,
    frozen_manifest: tuple[object, manifest_v2.K7ProductionRoleManifestV2],
) -> None:
    session, output_parent = _prepare(
        tmp_path,
        frozen_manifest,
        "runtime-retirement",
    )
    transfer = session.consume_for_runtime_v2()
    worker_fds = tuple(
        transfer.worker_descriptor(role)
        for role in transfer.worker_descriptor_roles
    )
    business_fds = tuple(
        transfer.business_descriptor(role)
        for role in transfer.business_descriptor_roles
    )

    transfer.retire_parent_side_descriptors_after_clone_v2(
        manifest_v2.K7ProductionBrokerRoleV2.WORKER
    )
    for descriptor in worker_fds:
        with pytest.raises(OSError):
            os.fstat(descriptor)
    with pytest.raises(
        session_v2.V075K7BrokerResourceSessionV2Error,
        match="permanently retired",
    ):
        transfer.worker_descriptor("BROKER_CHANNEL")
    with pytest.raises(
        session_v2.V075K7BrokerResourceSessionV2Error,
        match="already retired",
    ):
        transfer.retire_parent_side_descriptors_after_clone_v2("WORKER")

    transfer.retire_parent_side_descriptors_after_clone_v2("BUSINESS")
    for descriptor in business_fds:
        with pytest.raises(OSError):
            os.fstat(descriptor)
    transfer.assert_current()
    output_fd = transfer.broker_descriptor("OUTPUT_DIRECTORY")
    contaminant = os.open(
        "must-survive.txt",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
        dir_fd=output_fd,
    )
    os.write(contaminant, b"must not be silently deleted")
    os.close(contaminant)
    output_directory = next(output_parent.iterdir())

    with pytest.raises(
        session_v2.V075K7BrokerResourceSessionCleanupV2Error,
        match="cleanup is partial",
    ):
        transfer.close()
    assert output_directory.is_dir()
    assert (output_directory / "must-survive.txt").read_bytes() == (
        b"must not be silently deleted"
    )
    assert (
        session.guardian.state
        is session_v2.K7BrokerResourceSessionStateV2.CLEANUP_PARTIAL
    )

    recovery_output_fd = transfer.broker_descriptor("OUTPUT_DIRECTORY")
    assert recovery_output_fd == output_fd
    os.unlink("must-survive.txt", dir_fd=recovery_output_fd)
    transfer.close()
    assert transfer.closed is True
    assert list(output_parent.iterdir()) == []


def test_runtime_cleanup_retries_parent_fsync_after_successful_unlink(
    tmp_path: Path,
    frozen_manifest: tuple[object, manifest_v2.K7ProductionRoleManifestV2],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, output_parent = _prepare(
        tmp_path,
        frozen_manifest,
        "runtime-fsync-retry",
    )
    transfer = session.consume_for_runtime_v2()
    original_fsync = os.fsync
    calls = 0

    def fail_once(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected parent fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fail_once)
    with pytest.raises(
        session_v2.V075K7BrokerResourceSessionCleanupV2Error,
        match="cleanup is partial",
    ):
        transfer.close()
    assert list(output_parent.iterdir()) == []
    assert session.guardian._output_unlinked is True  # noqa: SLF001
    assert session.guardian._output_parent_synced is False  # noqa: SLF001

    transfer.close()
    assert transfer.closed is True
    assert calls == 2
