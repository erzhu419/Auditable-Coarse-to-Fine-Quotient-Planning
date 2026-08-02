from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import socket
import sys

import pytest

from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_production_role_bootstrap_v2 as bootstrap_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp import v075_k7_successor_portable_replay_v1 as replay_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _id, _successor_request


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _private_paths(tmp_path: Path) -> tuple[Path, Path]:
    root = (tmp_path / "private").resolve()
    root.mkdir(mode=0o700)
    key = root / "observer-key.json"
    key.write_bytes(b"manifest-v2-static-key")
    key.chmod(0o600)
    return root, key.resolve()


def _replay(request):
    transport = request.profile.accounted_profile.transport_profile
    lifecycle = request.profile.accounted_profile.private_replay_profile
    closure = replay_v1.reconstruct_v075_k7_successor_portable_profile_closure_v1(
        source_archive_raw=transport._archive_bytes,  # noqa: SLF001
        transport_profile_raw=canonical_json_bytes(transport.to_document()),
        lifecycle_profile_raw=canonical_json_bytes(lifecycle.to_document()),
        successor_profile_raw=canonical_json_bytes(request.profile.to_document()),
    )
    return replay_v1.replay_v075_k7_successor_request_bytes_portable_v1(
        raw=request.canonical_bytes,
        profile_closure=closure,
    )


def _manifest(tmp_path: Path, label: str):
    request = _successor_request(label)
    private_root, private_key = _private_paths(tmp_path)
    value = manifest_v2.freeze_v075_k7_production_role_manifest_v2(
        request=request,
        repository_root=REPOSITORY_ROOT,
        signer_private_root=private_root,
        signer_private_key_path=private_key,
    )
    return request, private_root, private_key, value


def test_fresh_manifest_binds_present_entries_bootstraps_and_new_source_identity(
    tmp_path: Path,
) -> None:
    request, _private_root, _private_key, value = _manifest(
        tmp_path, "role-manifest-v2-main"
    )
    value.assert_current()
    document = value.to_document()
    assert manifest_v2.PROPOSED_CONTRACT_VERSION == "2.0.8"
    assert document["request_id"] == request.request_id
    assert document["fresh_archive_required"] is True
    assert document["historical_manifest_v1_relabelled"] is False
    assert document["private_locator_serialized"] is False
    assert all(flag is False for flag in document["formal_locks"].values())
    assert document["worker_role"]["entry_source_present"] is True
    assert document["business_role"]["entry_source_present"] is True
    assert document["worker_role"]["bootstrap_sha256"] == (
        bootstrap_v2.WORKER_BOOTSTRAP_SHA256
    )
    assert document["business_role"]["bootstrap_sha256"] == (
        bootstrap_v2.BUSINESS_BOOTSTRAP_SHA256
    )
    assert document["worker_role"]["capability_fd_roles"] == list(
        bootstrap_v2.WORKER_CAPABILITY_ROLES
    )
    assert document["business_role"]["capability_fd_roles"] == list(
        bootstrap_v2.BUSINESS_CAPABILITY_ROLES
    )
    assert tuple(row["path"] for row in document["support_source_entries"]) == (
        manifest_v2.COMMON_ENTRY_SOURCE_PATH,
        manifest_v2.BOOTSTRAP_SOURCE_PATH,
    )
    archived = {
        path: (digest, size)
        for path, digest, size in (
            request.profile.accounted_profile.transport_profile.source_entries
        )
    }
    for role_key in ("worker_role", "business_role"):
        row = document[role_key]
        assert archived[row["entry_source_path"]] == (
            row["entry_source_sha256"],
            row["entry_source_byte_count"],
        )
    assert canonical_json_bytes(loads_canonical_json(value.canonical_bytes)) == (
        value.canonical_bytes
    )


def test_public_replay_and_role_context_bind_exact_request_manifest_and_role(
    tmp_path: Path,
) -> None:
    request, _private_root, _private_key, value = _manifest(
        tmp_path, "role-manifest-v2-public"
    )
    replay = _replay(request)
    public = manifest_v2.verify_v075_k7_production_role_manifest_public_bytes_v2(
        raw=value.canonical_bytes,
        expected_request_replay=replay,
    )
    binding = ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
        request.request_id,
        request.route_identity.route_identity_id,
        _id("manifest-v2-broker-spec"),
        _id("manifest-v2-session-nonce"),
    )
    contexts = {
        role: manifest_v2.freeze_v075_k7_production_role_launch_context_v2(
            manifest=value,
            binding=binding,
            role=role,
        )
        for role in manifest_v2.K7ProductionBrokerRoleV2
    }
    for role, context in contexts.items():
        replayed_binding = (
            manifest_v2
            .verify_v075_k7_production_role_launch_context_public_bytes_v2(
                raw=context.canonical_bytes,
                expected_manifest=public,
                expected_role=role,
            )
        )
        assert replayed_binding.to_document() == binding.to_document()
        assert context.to_document()["role"] == role.value
        assert context.to_document()["live_v2_session_authority_joined"] is False
    with pytest.raises(manifest_v2.V075K7ProductionRoleManifestV2Error):
        manifest_v2.verify_v075_k7_production_role_launch_context_public_bytes_v2(
            raw=contexts[manifest_v2.K7ProductionBrokerRoleV2.WORKER].canonical_bytes,
            expected_manifest=public,
            expected_role=manifest_v2.K7ProductionBrokerRoleV2.BUSINESS,
        )


def test_manifest_public_bytes_tamper_and_foreign_request_fail_closed(
    tmp_path: Path,
) -> None:
    request, _private_root, _private_key, value = _manifest(
        tmp_path, "role-manifest-v2-attack"
    )
    replay = _replay(request)
    document = loads_canonical_json(value.canonical_bytes)
    document["worker_role"]["entry_source_sha256"] = "0" * 64
    with pytest.raises(manifest_v2.V075K7ProductionRoleManifestV2Error):
        manifest_v2.verify_v075_k7_production_role_manifest_public_bytes_v2(
            raw=canonical_json_bytes(document),
            expected_request_replay=replay,
        )
    foreign = _successor_request("role-manifest-v2-foreign")
    with pytest.raises(manifest_v2.V075K7ProductionRoleManifestV2Error):
        manifest_v2.verify_v075_k7_production_role_manifest_public_bytes_v2(
            raw=value.canonical_bytes,
            expected_request_replay=_replay(foreign),
        )


def test_manifest_does_not_serialize_private_locator_strings(tmp_path: Path) -> None:
    _request, private_root, private_key, value = _manifest(
        tmp_path, "role-manifest-v2-private"
    )
    raw = value.canonical_bytes
    assert os.fsencode(private_root) not in raw
    assert os.fsencode(private_key) not in raw
    assert hashlib.sha256(os.fsencode(REPOSITORY_ROOT)).hexdigest().encode() in raw


def test_profile_and_bootstrap_sources_are_frozen_and_non_authorizing() -> None:
    profile = manifest_v2.official_v075_k7_production_role_manifest_profile_v2()
    bootstrap_profile = (
        bootstrap_v2.official_v075_k7_production_role_bootstrap_profile_v2()
    )
    assert tuple(frame for frame, _author in manifest_v2.FRAME_AUTHOR_VECTOR) == tuple(
        role.value for role in ipc_v1.FRAME_ROLES
    )
    assert all(value is False for value in profile.to_document()["formal_locks"].values())
    assert bootstrap_profile.to_document()["live_broker_execution_authorized"] is False
    assert bootstrap_profile.to_document()["sealed_and_capability_fd_lanes_distinct"] is True
    for role in bootstrap_v2.ROLE_ORDER:
        source = bootstrap_v2.bootstrap_source_for_role_v2(role)
        compile(source, f"<{role.lower()}-bootstrap>", "exec")
        assert hashlib.sha256(source.encode()).hexdigest() == (
            bootstrap_v2.bootstrap_sha256_for_role_v2(role)
        )
        assert "sys.path.insert(0, archive_path)" in source
        assert "os._exit" in source


def test_worker_bootstrap_loads_entry_from_sealed_archive_before_typed_input_failure(
    tmp_path: Path,
) -> None:
    request = _successor_request("role-bootstrap-v2-fresh-exec")
    transport = request.profile.accounted_profile.transport_profile
    sealed = [
        runtime_v1.create_v075_k7_sealed_memfd_from_bytes_v1(
            raw=(transport._archive_bytes if index == 0 else b"invalid-public-input"),  # noqa: SLF001
            name=f"acfqp-bootstrap-v2-input-{index}",
        )
        for index in range(len(bootstrap_v2.WORKER_SEALED_INPUT_ROLES))
    ]
    rw_result = runtime_v1._new_sealable_memfd(  # noqa: SLF001
        "acfqp-bootstrap-v2-result"
    )
    ro_result = os.open(
        f"/proc/self/fd/{rw_result}", os.O_RDONLY | os.O_CLOEXEC
    )
    output_directory = tmp_path / "worker-output"
    output_directory.mkdir(mode=0o700)
    output_fd = os.open(
        output_directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    )
    worker_endpoint, broker_endpoint = socket.socketpair(
        socket.AF_UNIX,
        socket.SOCK_SEQPACKET,
    )
    executable_path = Path(sys.executable).resolve(strict=True)
    executable_raw = executable_path.read_bytes()
    executable_identity_fd = os.open(executable_path, os.O_RDONLY | os.O_CLOEXEC)
    environment = {
        **bootstrap_v2.BASE_ENVIRONMENT,
        bootstrap_v2.ROLE_ENV: bootstrap_v2.WORKER_ROLE,
        bootstrap_v2.SEALED_FD_ENV: ",".join(str(value) for value in sealed),
        bootstrap_v2.CHANNEL_FD_ENV: str(worker_endpoint.fileno()),
        bootstrap_v2.RESULT_FD_ENV: str(ro_result),
        bootstrap_v2.OUTPUT_DIRECTORY_FD_ENV: str(output_fd),
    }
    argv = [
        os.fspath(executable_path),
        "-I",
        "-S",
        "-B",
        "-c",
        bootstrap_v2.WORKER_BOOTSTRAP_SOURCE,
        transport.source_archive_sha256,
        str(transport.source_archive_byte_count),
        hashlib.sha256(executable_raw).hexdigest(),
        str(len(executable_raw)),
        os.fspath(REPOSITORY_ROOT),
        "NOT_APPLICABLE",
        "NOT_APPLICABLE",
        _id("bootstrap-v2-manifest"),
        _id("bootstrap-v2-role"),
        _id("bootstrap-v2-context"),
    ]
    process = None
    try:
        process = subprocess.run(
            argv,
            env=environment,
            pass_fds=(
                *sealed,
                worker_endpoint.fileno(),
                ro_result,
                output_fd,
                executable_identity_fd,
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        # 111 is issued only by the imported worker entry.  Bootstrap-local
        # failures use 81..95, so this proves sealed-archive zipimport reached
        # the fixed wrapper without consulting PYTHONPATH or the workspace.
        assert process.returncode == 111
        assert process.stdout == b""
        assert process.stderr == b""
    finally:
        worker_endpoint.close()
        broker_endpoint.close()
        os.close(ro_result)
        os.close(rw_result)
        os.close(output_fd)
        os.close(executable_identity_fd)
        for descriptor in sealed:
            os.close(descriptor)
