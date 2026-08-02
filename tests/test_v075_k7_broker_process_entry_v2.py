from __future__ import annotations

import fcntl
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

import pytest

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_broker_business_process_entry_v2 as business_entry
from acfqp import v075_k7_broker_process_entry_common_v2 as common_v2
from acfqp import v075_k7_broker_worker_process_entry_v2 as worker_entry
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_production_role_bootstrap_v2 as bootstrap_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp.phase3e_ids import canonical_json_bytes
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _id, _successor_request


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _sealed(raw: bytes, label: str) -> int:
    return runtime_v1.create_v075_k7_sealed_memfd_from_bytes_v1(
        raw=raw, name=f"acfqp-{label}"
    )


def _substrate(tmp_path: Path, label: str):
    request = _successor_request(label)
    private_root = (tmp_path / "private").resolve()
    private_root.mkdir(mode=0o700)
    private_key = private_root / "observer-key.json"
    private_key.write_bytes(b"entry-v2-static-key")
    private_key.chmod(0o600)
    manifest = manifest_v2.freeze_v075_k7_production_role_manifest_v2(
        request=request,
        repository_root=REPOSITORY_ROOT,
        signer_private_root=private_root,
        signer_private_key_path=private_key.resolve(),
    )
    binding = ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
        request.request_id,
        request.route_identity.route_identity_id,
        _id(f"entry-v2-spec-{label}"),
        _id(f"entry-v2-nonce-{label}"),
    )
    transport = request.profile.accounted_profile.transport_profile
    lifecycle = request.profile.accounted_profile.private_replay_profile
    common_rows = (
        transport._archive_bytes,  # noqa: SLF001
        canonical_json_bytes(transport.to_document()),
        canonical_json_bytes(lifecycle.to_document()),
        canonical_json_bytes(request.profile.to_document()),
        request.canonical_bytes,
        manifest.canonical_bytes,
    )
    return request, private_root, private_key.resolve(), manifest, binding, common_rows


@pytest.mark.parametrize("role", tuple(manifest_v2.K7ProductionBrokerRoleV2))
def test_common_entry_reconstructs_fresh_request_manifest_context_and_fd_lanes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: manifest_v2.K7ProductionBrokerRoleV2,
) -> None:
    worker = role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
    request, private_root, private_key, manifest, binding, common_rows = _substrate(
        tmp_path, f"entry-v2-{role.value.lower()}"
    )
    context = manifest_v2.freeze_v075_k7_production_role_launch_context_v2(
        manifest=manifest,
        binding=binding,
        role=role,
    )
    rows = (*common_rows, context.canonical_bytes)
    if not worker:
        rows = (*rows, b"sealed-lifecycle-secret-placeholder")
    sealed = [_sealed(raw, f"entry-{role.value.lower()}-{index}") for index, raw in enumerate(rows)]
    secret_fd = None if worker else sealed[-1]
    original_pread = os.pread
    secret_pread_calls = 0

    def guarded_pread(
        descriptor: int, byte_count: int, offset: int
    ) -> bytes:
        nonlocal secret_pread_calls
        if descriptor == secret_fd:
            secret_pread_calls += 1
            raise AssertionError("common loader read private lifecycle bytes")
        return original_pread(descriptor, byte_count, offset)

    if not worker:
        monkeypatch.setattr(common_v2.os, "pread", guarded_pread)
    rw_result = runtime_v1._new_sealable_memfd(  # noqa: SLF001
        "acfqp-entry-v2-result"
    )
    result_fd = (
        os.open(f"/proc/self/fd/{rw_result}", os.O_RDONLY | os.O_CLOEXEC)
        if worker
        else rw_result
    )
    output_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    endpoint, broker = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    role_spec = manifest.role_spec(role)
    argv = [
        f"acfqp-k7-{role.value.lower()}-v2",
        os.fspath(REPOSITORY_ROOT),
        "NOT_APPLICABLE" if worker else os.fspath(private_root),
        "NOT_APPLICABLE" if worker else os.fspath(private_key),
        manifest.manifest_id,
        role_spec.role_spec_id,
        context.context_id,
    ]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setenv(bootstrap_v2.ROLE_ENV, role.value)
    monkeypatch.setenv(
        bootstrap_v2.SEALED_FD_ENV, ",".join(str(value) for value in sealed)
    )
    monkeypatch.setenv(bootstrap_v2.CHANNEL_FD_ENV, str(endpoint.fileno()))
    monkeypatch.setenv(bootstrap_v2.RESULT_FD_ENV, str(result_fd))
    if worker:
        monkeypatch.setenv(bootstrap_v2.OUTPUT_DIRECTORY_FD_ENV, str(output_fd))
    try:
        loaded = common_v2.load_v075_k7_broker_process_inputs_v2(role=role)
        assert loaded.request_replay.request.request_id == request.request_id
        assert loaded.manifest_replay.manifest_id == manifest.manifest_id
        assert loaded.binding.to_document() == binding.to_document()
        assert loaded.result_fd == result_fd
        assert bool(loaded.output_directory_fd is not None) is worker
        assert bool(loaded.sealed_secret_fd is not None) is (not worker)
        assert secret_pread_calls == 0
        for descriptor in (*sealed, result_fd, output_fd):
            assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        loaded.close_endpoint()
        endpoint = None
    finally:
        if endpoint is not None:
            endpoint.close()
        broker.close()
        for descriptor in sealed:
            os.close(descriptor)
        if worker:
            os.close(result_fd)
            os.close(rw_result)
        else:
            os.close(rw_result)
        os.close(output_fd)


def test_sealed_and_nonsealed_fd_lanes_cannot_overlap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _request, _private_root, _private_key, manifest, binding, common_rows = _substrate(
        tmp_path, "entry-v2-overlap"
    )
    role = manifest_v2.K7ProductionBrokerRoleV2.WORKER
    context = manifest_v2.freeze_v075_k7_production_role_launch_context_v2(
        manifest=manifest, binding=binding, role=role
    )
    sealed = [
        _sealed(raw, f"entry-overlap-{index}")
        for index, raw in enumerate((*common_rows, context.canonical_bytes))
    ]
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "acfqp-k7-worker-v2",
            os.fspath(REPOSITORY_ROOT),
            "NOT_APPLICABLE",
            "NOT_APPLICABLE",
            manifest.manifest_id,
            manifest.worker_role.role_spec_id,
            context.context_id,
        ],
    )
    monkeypatch.setenv(bootstrap_v2.ROLE_ENV, role.value)
    monkeypatch.setenv(bootstrap_v2.SEALED_FD_ENV, ",".join(map(str, sealed)))
    monkeypatch.setenv(bootstrap_v2.CHANNEL_FD_ENV, str(sealed[0]))
    monkeypatch.setenv(bootstrap_v2.RESULT_FD_ENV, str(sealed[1]))
    monkeypatch.setenv(bootstrap_v2.OUTPUT_DIRECTORY_FD_ENV, str(sealed[2]))
    try:
        with pytest.raises(
            common_v2.V075K7BrokerProcessEntryCommonV2Error,
            match="overlap",
        ):
            common_v2.load_v075_k7_broker_process_inputs_v2(role=role)
    finally:
        for descriptor in sealed:
            os.close(descriptor)


def test_process_entries_return_typed_exit_without_protocol_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(**_kwargs):
        raise common_v2.V075K7BrokerProcessEntryCommonV2Error("injected")

    monkeypatch.setattr(common_v2, "load_v075_k7_broker_process_inputs_v2", fail)
    assert worker_entry.run_v075_k7_broker_worker_process_entry_v2() == (
        worker_entry.INPUT_FAILURE_EXIT
    )
    assert business_entry.run_v075_k7_broker_business_process_entry_v2() == (
        business_entry.INPUT_FAILURE_EXIT
    )


def test_worker_entry_consumes_attestation_before_common_and_core_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    attestation = object()
    archive_fd = 73
    inputs = SimpleNamespace(
        request_replay=object(),
        binding=object(),
        endpoint=object(),
        result_fd=74,
        output_directory_fd=75,
        close_endpoint=lambda: events.append("close"),
    )

    def consume(value, *, role, source_archive_fd):
        assert value is attestation
        assert role is worker_entry.sandbox_v2.K7ProductionSandboxRoleV2.WORKER
        assert source_archive_fd == archive_fd
        events.append("consume")

    def load(*, role):
        assert role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
        events.append("load")
        return inputs

    def execute(**kwargs):
        assert kwargs["endpoint"] is inputs.endpoint
        events.append("core")

    modules = {
        "acfqp.v075_k7_production_role_manifest_v2": manifest_v2,
        "acfqp.v075_k7_broker_process_entry_common_v2": SimpleNamespace(
            load_v075_k7_broker_process_inputs_v2=load
        ),
        "acfqp.v075_k7_broker_worker_entry_v1": SimpleNamespace(
            execute_v075_k7_broker_worker_core_v1=execute
        ),
    }

    def import_module(name):
        events.append(f"import:{name}")
        return modules[name]

    monkeypatch.setattr(
        worker_entry.sandbox_v2,
        "consume_v075_k7_production_role_postexec_entry_attestation_v2",
        consume,
    )
    monkeypatch.setattr(worker_entry.importlib, "import_module", import_module)
    monkeypatch.setattr(worker_entry.os, "umask", lambda _mode: 0o022)
    assert worker_entry.run_v075_k7_broker_worker_process_entry_v2(
        attestation, archive_fd
    ) == worker_entry.SUCCESS_EXIT
    assert events == [
        "consume",
        "import:acfqp.v075_k7_production_role_manifest_v2",
        "import:acfqp.v075_k7_broker_process_entry_common_v2",
        "import:acfqp.v075_k7_broker_worker_entry_v1",
        "load",
        "core",
        "close",
    ]


def test_business_entry_consumes_attestation_before_common_and_core_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    attestation = object()
    archive_fd = 83
    inputs = SimpleNamespace(
        request_replay=object(),
        source_archive_fd=archive_fd,
        sealed_secret_fd=84,
        repository_root=Path("/repository"),
        signer_private_root=Path("/private"),
        signer_private_key_path=Path("/private/key"),
        result_fd=85,
        endpoint=object(),
        binding=object(),
        close_endpoint=lambda: events.append("close"),
    )

    def consume(value, *, role, source_archive_fd):
        assert value is attestation
        assert role is worker_entry.sandbox_v2.K7ProductionSandboxRoleV2.BUSINESS
        assert source_archive_fd == archive_fd
        events.append("consume")

    def load(*, role):
        assert role is manifest_v2.K7ProductionBrokerRoleV2.BUSINESS
        events.append("load")
        return inputs

    def execute(**kwargs):
        assert kwargs["business_result_endpoint"] is inputs.endpoint
        events.append("core")

    modules = {
        "acfqp.v075_k7_production_role_manifest_v2": manifest_v2,
        "acfqp.v075_k7_broker_process_entry_common_v2": SimpleNamespace(
            load_v075_k7_broker_process_inputs_v2=load
        ),
        "acfqp.v075_k7_business_entry_core_v1": SimpleNamespace(
            execute_v075_k7_business_entry_core_v1=execute
        ),
    }

    def import_module(name):
        events.append(f"import:{name}")
        return modules[name]

    monkeypatch.setattr(
        business_entry.sandbox_v2,
        "consume_v075_k7_production_role_postexec_entry_attestation_v2",
        consume,
    )
    monkeypatch.setattr(business_entry.importlib, "import_module", import_module)
    assert business_entry.run_v075_k7_broker_business_process_entry_v2(
        attestation, archive_fd
    ) == business_entry.SUCCESS_EXIT
    assert events == [
        "consume",
        "import:acfqp.v075_k7_production_role_manifest_v2",
        "import:acfqp.v075_k7_broker_process_entry_common_v2",
        "import:acfqp.v075_k7_business_entry_core_v1",
        "load",
        "core",
        "close",
    ]
