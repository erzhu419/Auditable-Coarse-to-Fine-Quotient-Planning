from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_signer_owning_sealed_observer_ipc_v1 as ipc
from tests.test_v075_production_private_signer_runtime_v1 import (
    REPOSITORY_ROOT,
    _key_document,
    _registry,
    _write_private_key,
)


@pytest.fixture
def tmp_path() -> Path:
    if os.name != "posix":
        pytest.skip("signer-owning child requires POSIX secure-open")
    value = Path(
        tempfile.mkdtemp(
            prefix="acfqp-v075-signer-owning-test-",
            dir="/tmp",
        )
    )
    try:
        yield value
    finally:
        shutil.rmtree(value)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-signer-owning-stage-a-test:v1"
        + b"\x00"
        + label.encode()
    ).hexdigest()


@pytest.fixture(scope="module")
def profile():
    return (
        ipc.freeze_v075_signer_owning_sealed_observer_service_profile_v1(
            timeout_milliseconds=10_000
        )
    )


def _material(marker: str) -> bytes:
    return ipc._private_material_raw_for_testing(  # noqa: SLF001
        private_salt_hex=hashlib.sha512(marker.encode()).hexdigest(),
        private_environment=[
            [[1, 1, 2], [2, 1, 2]],
            [[1, 3, 4], [3, 1, 4]],
        ],
    )


def _request(profile, marker: str, material: bytes):
    registry = _registry()
    return ipc.freeze_v075_sealed_observer_finalize_request_v1(
        profile=profile,
        request_nonce=_id(marker + "-nonce"),
        session_external_id=_id(marker + "-session"),
        private_material_commitment_id=(
            ipc._private_material_commitment(material)  # noqa: SLF001
        ),
        signer_registry=registry,
        ordered_stream_ids=tuple(
            sorted((_id(marker + "-stream-a"), _id(marker + "-stream-b")))
        ),
    )


def _private_key(tmp_path: Path, *, mutate=None):
    registry = _registry()
    document = _key_document(registry)
    if mutate is not None:
        mutate(document)
    return (
        registry,
        *_write_private_key(tmp_path, document),
    )


def _execute(
    *,
    profile,
    request,
    material: bytes,
    private_root: Path,
    key_path: Path,
    service=None,
):
    fd = ipc._stage_sealed_private_material_bytes_for_testing(  # noqa: SLF001
        material
    )
    try:
        return ipc.execute_v075_signer_owning_sealed_observer_finalize_v1(
            service=(
                service
                if service is not None
                else ipc.start_v075_signer_owning_sealed_observer_service_v1(
                    profile=profile
                )
            ),
            request_bytes=request.canonical_bytes,
            repository_root=REPOSITORY_ROOT.resolve(),
            signer_private_root=private_root,
            signer_private_key_path=key_path,
            sealed_private_material_fd=fd,
        )
    finally:
        os.close(fd)


def _walk_keys(value: Any):
    if type(value) is dict:
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif type(value) is list:
        for child in value:
            yield from _walk_keys(child)


def _rehash_result(document: dict[str, Any]) -> bytes:
    payload = {
        key: value for key, value in document.items() if key != "result_id"
    }
    document["result_id"] = ipc._hash("result", payload)  # noqa: SLF001
    return canonical_json_bytes(document)


def _rehash_nested(
    document: dict[str, Any],
    *,
    key: str,
    role: str,
    id_key: str,
) -> None:
    payload = {
        name: value
        for name, value in document[key].items()
        if name != id_key
    }
    document[key][id_key] = ipc._hash(role, payload)  # noqa: SLF001
    document[id_key] = document[key][id_key]


def _rehash_journal(document: dict[str, Any]) -> None:
    journal = document["journal"]
    prior = hashlib.sha256(
        b"acfqp:v075-signer-owning-observer-journal-initial:v1"
    ).hexdigest()
    for entry in journal["entries"]:
        entry["prior_entry_id"] = prior
        payload = {
            key: value
            for key, value in entry.items()
            if key != "journal_entry_id"
        }
        entry["journal_entry_id"] = ipc._hash(  # noqa: SLF001
            "journal_entry",
            payload,
        )
        prior = entry["journal_entry_id"]
    journal["entry_count"] = len(journal["entries"])
    journal["head_id"] = prior
    payload = {
        key: value
        for key, value in journal.items()
        if key != "journal_id"
    }
    journal["journal_id"] = ipc._hash("journal", payload)  # noqa: SLF001
    document["journal_id"] = journal["journal_id"]


def _execute_fd(
    *,
    profile,
    request,
    private_root: Path,
    key_path: Path,
    fd: int,
    service,
    repository_root: Path = REPOSITORY_ROOT.resolve(),
):
    return ipc.execute_v075_signer_owning_sealed_observer_finalize_v1(
        service=service,
        request_bytes=request.canonical_bytes,
        repository_root=repository_root,
        signer_private_root=private_root,
        signer_private_key_path=key_path,
        sealed_private_material_fd=fd,
    )


def test_request_has_no_signer_verification_private_or_posthoc_entry(
    profile,
) -> None:
    request = _request(profile, "surface", _material("surface"))
    parameters = inspect.signature(
        ipc.freeze_v075_sealed_observer_finalize_request_v1
    ).parameters
    for forbidden in (
        "observer_signer",
        "verification",
        "private_salt",
        "private_environment",
        "closure",
        "b3_attestation",
    ):
        assert forbidden not in parameters
    document = request.to_document()
    assert document["caller_supplied_signer"] is False
    assert document["caller_supplied_verification"] is False
    assert document["caller_supplied_private_material"] is False
    assert document["caller_supplied_prior_closure"] is False
    assert document["caller_supplied_prior_b3"] is False
    assert not {
        "observer_signer",
        "verification",
        "private_salt",
        "private_environment",
        "signed_batch_journal_closure",
        "b3_attestation",
    } & set(_walk_keys(document))

    with pytest.raises(TypeError):
        ipc.freeze_v075_sealed_observer_finalize_request_v1(
            profile=profile,
            request_nonce=_id("foreign-nonce"),
            session_external_id=_id("foreign-session"),
            private_material_commitment_id=_id("foreign-material"),
            signer_registry=_registry(),
            ordered_stream_ids=(_id("foreign-stream"),),
            closure_bytes=b"old closure",
        )
    with pytest.raises(TypeError):
        ipc.freeze_v075_sealed_observer_finalize_request_v1(
            profile=profile,
            request_nonce=_id("foreign-nonce-2"),
            session_external_id=_id("foreign-session-2"),
            private_material_commitment_id=_id("foreign-material-2"),
            signer_registry=_registry(),
            ordered_stream_ids=(_id("foreign-stream-2"),),
            b3_attestation=b"old B3",
        )

    for injected_key in (
        "signed_batch_journal_closure",
        "b3_attestation",
        "source_private_replay_verification",
    ):
        attacked = request.to_document()
        attacked[injected_key] = {"forbidden": True}
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            ipc.verify_v075_sealed_observer_finalize_request_bytes_v1(
                canonical_json_bytes(attacked)
            )


def test_honest_child_loads_production_signer_but_refuses_b3(
    profile,
    tmp_path: Path,
) -> None:
    material = _material("honest")
    request = _request(profile, "honest", material)
    _registry_value, private_root, key_path = _private_key(tmp_path)
    result = _execute(
        profile=profile,
        request=request,
        material=material,
        private_root=private_root,
        key_path=key_path,
    )
    document = result.to_document()

    assert result.terminal_code == "SESSION_OWNERSHIP_NOT_YET_COMPLETE"
    assert document["child_result"][
        "sealed_private_material_commitment_verified"
    ] is True
    assert document["child_result"][
        "sealed_child_signer_loader_completed"
    ] is True
    assert document["observer_session_owned_from_open"] is False
    assert document["private_replay_performed"] is False
    assert document["b3_sign_performed"] is False
    assert document["b3_attestation"]["kind"] == "NOT_APPLICABLE"
    assert document["signed_batch_journal_closure"][
        "kind"
    ] == "NOT_APPLICABLE"
    assert document["child_result"]["child_work"]["private_replay_calls"] == 0
    assert document["child_result"]["child_work"]["b3_sign_calls"] == 0
    assert document["work"]["process_launches"] == 1
    assert document["work"]["supervisor_checks"] == 1
    assert document["journal"]["entry_count"] == 2
    assert document["process"]["leader_reaped"] is True

    replayed = (
        ipc.verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
            raw=result.canonical_bytes,
            request_bytes=request.canonical_bytes,
            profile=profile,
        )
    )
    assert replayed.result_id == result.result_id
    serialized = result.canonical_bytes.decode()
    assert os.fspath(private_root) not in serialized
    assert os.fspath(key_path) not in serialized
    assert material.hex() not in serialized
    for key in ipc._locks():  # noqa: SLF001
        assert document[key] is False


def test_wrong_private_material_never_reaches_signer_or_b3(
    profile,
    tmp_path: Path,
) -> None:
    expected = _material("expected")
    wrong = _material("wrong")
    request = _request(profile, "wrong-material", expected)
    _registry_value, private_root, key_path = _private_key(tmp_path)
    result = _execute(
        profile=profile,
        request=request,
        material=wrong,
        private_root=private_root,
        key_path=key_path,
    )
    child = result.to_document()["child_result"]
    assert result.terminal_code == "PRIVATE_MATERIAL_COMMITMENT_MISMATCH"
    assert child["sealed_private_material_commitment_verified"] is False
    assert child["sealed_child_signer_loader_completed"] is False
    assert child["child_work"]["production_signer_load_attempts"] == 0
    assert child["child_work"]["private_replay_calls"] == 0
    assert child["child_work"]["b3_sign_calls"] == 0
    assert child["b3_attestation"]["kind"] == "NOT_APPLICABLE"


def test_wrong_signer_secret_fails_before_any_b3(
    profile,
    tmp_path: Path,
) -> None:
    material = _material("wrong-signer")
    request = _request(profile, "wrong-signer", material)

    def mutate(document):
        document["registered_public_key_id"] = "0" * 64

    _registry_value, private_root, key_path = _private_key(
        tmp_path,
        mutate=mutate,
    )
    result = _execute(
        profile=profile,
        request=request,
        material=material,
        private_root=private_root,
        key_path=key_path,
    )
    child = result.to_document()["child_result"]
    assert result.terminal_code == "SIGNER_LOAD_FAILED"
    assert child["sealed_private_material_commitment_verified"] is True
    assert child["sealed_child_signer_loader_completed"] is False
    assert child["child_work"]["production_signer_load_attempts"] == 1
    assert child["child_work"]["production_signer_load_successes"] == 0
    assert child["child_work"]["private_replay_calls"] == 0
    assert child["child_work"]["b3_sign_calls"] == 0


def test_double_finalize_is_nonce_rejected_without_second_launch(
    profile,
    tmp_path: Path,
) -> None:
    material = _material("double")
    request = _request(profile, "double", material)
    _registry_value, private_root, key_path = _private_key(tmp_path)
    service = ipc.start_v075_signer_owning_sealed_observer_service_v1(
        profile=profile
    )
    first = _execute(
        profile=profile,
        request=request,
        material=material,
        private_root=private_root,
        key_path=key_path,
        service=service,
    )
    second = _execute(
        profile=profile,
        request=request,
        material=material,
        private_root=private_root,
        key_path=key_path,
        service=service,
    )
    assert first.terminal_code == "SESSION_OWNERSHIP_NOT_YET_COMPLETE"
    assert second.terminal_code == "NONCE_REPLAY_REJECTED"
    document = second.to_document()
    assert document["work"]["process_launches"] == 0
    assert document["work"]["nonce_rejections"] == 1
    assert document["process"]["launched"] is False
    assert document["journal"]["entry_count"] == 1
    assert document["b3_attestation"]["kind"] == "NOT_APPLICABLE"
    ipc.verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
        raw=second.canonical_bytes,
        request_bytes=request.canonical_bytes,
        profile=profile,
    )


def test_nonce_request_profile_and_nested_transplants_are_rejected(
    profile,
    tmp_path: Path,
) -> None:
    material = _material("transplant")
    request = _request(profile, "transplant", material)
    _registry_value, private_root, key_path = _private_key(tmp_path)
    result = _execute(
        profile=profile,
        request=request,
        material=material,
        private_root=private_root,
        key_path=key_path,
    )
    foreign_request = _request(profile, "foreign", material)
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
    ):
        ipc.verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
            raw=result.canonical_bytes,
            request_bytes=foreign_request.canonical_bytes,
            profile=profile,
        )

    attacked = result.to_document()
    attacked["request_nonce"] = _id("attacked-nonce")
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
    ):
        ipc.verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
            raw=_rehash_result(attacked),
            request_bytes=request.canonical_bytes,
            profile=profile,
        )

    nested = result.to_document()
    nested["supervisor"]["request_id"] = _id("foreign-request")
    supervisor_payload = {
        key: value
        for key, value in nested["supervisor"].items()
        if key != "supervisor_id"
    }
    nested["supervisor"]["supervisor_id"] = ipc._hash(  # noqa: SLF001
        "supervisor",
        supervisor_payload,
    )
    nested["supervisor_id"] = nested["supervisor"]["supervisor_id"]
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
    ):
        ipc.V075SignerOwningSealedObserverIPCResultV1(
            ipc._load(  # noqa: SLF001
                _rehash_result(nested),
                label="attack",
                cap=ipc.MAX_FINAL_RESULT_BYTES,
            )
        )


def test_frame_double_finalize_and_cap_attacks_fail_closed() -> None:
    payload = b"{}"
    framed = ipc._frame(payload, cap=32)  # noqa: SLF001
    assert ipc._decode_single_frame(framed, cap=32) == payload  # noqa: SLF001
    for header in (
        b"0000000A",
        b"0000000",
        b"00000000",
        b"ffffffff",
    ):
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            ipc._parse_frame_header(header, cap=32)  # noqa: SLF001
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
    ):
        ipc._decode_single_frame(framed + framed, cap=32)  # noqa: SLF001
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation,
        match="double-finalize",
    ):
        ipc._read_child_frame(  # noqa: SLF001
            io.BytesIO(framed + framed),
            cap=32,
        )


def test_child_crash_and_timeout_are_typed_and_fully_accounted(
    profile,
    tmp_path: Path,
    monkeypatch,
) -> None:
    material = _material("transport-failure")
    _registry_value, private_root, key_path = _private_key(tmp_path)

    def crash_argv(**_kwargs):
        return [
            sys.executable,
            "-I",
            "-S",
            "-c",
            "import os; os._exit(17)",
        ]

    monkeypatch.setattr(ipc, "_child_argv", crash_argv)
    crash_request = _request(profile, "crash", material)
    crashed = _execute(
        profile=profile,
        request=crash_request,
        material=material,
        private_root=private_root,
        key_path=key_path,
    )
    crash_document = crashed.to_document()
    assert crashed.terminal_code == "CHILD_CRASH"
    assert crash_document["work"]["process_launches"] == 1
    assert crash_document["work"]["process_exit_failures"] == 1
    assert crash_document["work"]["crash_events"] == 1
    assert crash_document["child_result"]["kind"] == "NOT_APPLICABLE"
    assert crash_document["b3_attestation"]["kind"] == "NOT_APPLICABLE"
    ipc.verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
        raw=crashed.canonical_bytes,
        request_bytes=crash_request.canonical_bytes,
        profile=profile,
    )

    timeout_profile = (
        ipc.freeze_v075_signer_owning_sealed_observer_service_profile_v1(
            timeout_milliseconds=100
        )
    )

    def timeout_argv(**_kwargs):
        return [
            sys.executable,
            "-I",
            "-S",
            "-c",
            "import time; time.sleep(5)",
        ]

    monkeypatch.setattr(ipc, "_child_argv", timeout_argv)
    timeout_request = _request(timeout_profile, "timeout", material)
    timed_out = _execute(
        profile=timeout_profile,
        request=timeout_request,
        material=material,
        private_root=private_root,
        key_path=key_path,
    )
    timeout_document = timed_out.to_document()
    assert timed_out.terminal_code == "CHILD_TIMEOUT"
    assert timeout_document["work"]["timeout_events"] == 1
    assert timeout_document["work"]["process_launches"] == 1
    assert timeout_document["process"]["leader_reaped"] is True
    assert timeout_document["b3_attestation"]["kind"] == "NOT_APPLICABLE"
    ipc.verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
        raw=timed_out.canonical_bytes,
        request_bytes=timeout_request.canonical_bytes,
        profile=timeout_profile,
    )


def test_source_runtime_frame_result_and_work_rehash_attacks_fail(
    profile,
    tmp_path: Path,
) -> None:
    material = _material("rehash")
    request = _request(profile, "rehash", material)
    _registry_value, private_root, key_path = _private_key(tmp_path)
    result = _execute(
        profile=profile,
        request=request,
        material=material,
        private_root=private_root,
        key_path=key_path,
    )
    detached = result.to_document()
    detached["work"]["process_launches"] = 999
    assert result.to_document()["work"]["process_launches"] == 1

    original_archive = profile._archive_bytes  # noqa: SLF001
    object.__setattr__(
        profile,
        "_archive_bytes",
        original_archive[:-1]
        + (b"0" if original_archive[-1:] != b"0" else b"1"),
    )
    try:
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            profile.to_document()
    finally:
        object.__setattr__(profile, "_archive_bytes", original_archive)
    profile.to_document()

    runtime = profile.runtime_document
    original_size = runtime["executable_byte_count"]
    runtime["executable_byte_count"] = original_size + 1
    try:
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            profile.to_document()
    finally:
        runtime["executable_byte_count"] = original_size
    profile.to_document()

    attacked = result.to_document()
    del attacked["work"]["supervisor_checks"]
    work_payload = {
        key: value
        for key, value in attacked["work"].items()
        if key != "work_id"
    }
    attacked["work"]["work_id"] = ipc._hash(  # noqa: SLF001
        "work",
        work_payload,
    )
    attacked["work_id"] = attacked["work"]["work_id"]
    with pytest.raises(
        (
            KeyError,
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation,
        )
    ):
        ipc.verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
            raw=_rehash_result(attacked),
            request_bytes=request.canonical_bytes,
            profile=profile,
        )

    b3_attack = result.to_document()
    b3_attack["b3_attestation"] = {"forged": True}
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
    ):
        ipc.V075SignerOwningSealedObserverIPCResultV1(
            ipc._load(  # noqa: SLF001
                _rehash_result(b3_attack),
                label="B3 attack",
                cap=ipc.MAX_FINAL_RESULT_BYTES,
            )
        )


def test_invalid_path_and_unsealed_fd_do_not_consume_nonce(
    profile,
    tmp_path: Path,
) -> None:
    material = _material("preflight-retry")
    request = _request(profile, "preflight-retry", material)
    _registry_value, private_root, key_path = _private_key(tmp_path)
    service = ipc.start_v075_signer_owning_sealed_observer_service_v1(
        profile=profile
    )
    valid_fd = ipc._stage_sealed_private_material_bytes_for_testing(  # noqa: SLF001
        material
    )
    try:
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            _execute_fd(
                profile=profile,
                request=request,
                private_root=private_root,
                key_path=key_path,
                fd=valid_fd,
                service=service,
                repository_root=Path("relative"),
            )
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            _execute_fd(
                profile=profile,
                request=request,
                private_root=private_root,
                key_path=key_path,
                fd=-1,
                service=service,
            )

        unsealed_fd = ipc._memfd_create(  # noqa: SLF001
            "acfqp-v075-unsealed-test"
        )
        try:
            os.write(unsealed_fd, material)
            with pytest.raises(
                ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
            ):
                _execute_fd(
                    profile=profile,
                    request=request,
                    private_root=private_root,
                    key_path=key_path,
                    fd=unsealed_fd,
                    service=service,
                )
        finally:
            os.close(unsealed_fd)

        result = _execute_fd(
            profile=profile,
            request=request,
            private_root=private_root,
            key_path=key_path,
            fd=valid_fd,
            service=service,
        )
    finally:
        os.close(valid_fd)
    assert result.terminal_code == "SESSION_OWNERSHIP_NOT_YET_COMPLETE"
    assert result.to_document()["work"]["nonce_rejections"] == 0


def test_post_nonce_setup_failures_are_typed_and_replayable(
    profile,
    tmp_path: Path,
    monkeypatch,
) -> None:
    material = _material("typed-parent-failures")
    _registry_value, private_root, key_path = _private_key(tmp_path)

    def run_failure(marker: str, patch_name: str, replacement):
        request = _request(profile, marker, material)
        service = ipc.start_v075_signer_owning_sealed_observer_service_v1(
            profile=profile
        )
        fd = ipc._stage_sealed_private_material_bytes_for_testing(  # noqa: SLF001
            material
        )
        try:
            with monkeypatch.context() as patch:
                if patch_name == "Popen":
                    patch.setattr(ipc.subprocess, patch_name, replacement)
                else:
                    patch.setattr(ipc, patch_name, replacement)
                result = _execute_fd(
                    profile=profile,
                    request=request,
                    private_root=private_root,
                    key_path=key_path,
                    fd=fd,
                    service=service,
                )
        finally:
            os.close(fd)
        ipc.verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
            raw=result.canonical_bytes,
            request_bytes=request.canonical_bytes,
            profile=profile,
        )
        return result.to_document()

    def fail_stage(*_args, **_kwargs):
        raise OSError("injected staging failure")

    staged = run_failure("stage-failure", "_stage_sealed_bytes", fail_stage)
    assert staged["terminal_code"] == "SOURCE_ARCHIVE_STAGING_FAILED"
    assert staged["process"]["launched"] is False
    assert staged["work"]["source_archive_stage_attempts"] == 1
    assert staged["work"]["source_archive_staging_failure_events"] == 1

    def fail_launch(*_args, **_kwargs):
        raise OSError("injected Popen failure")

    launched = run_failure("launch-failure", "Popen", fail_launch)
    assert launched["terminal_code"] == "PROCESS_LAUNCH_FAILED"
    assert launched["process"]["launched"] is False
    assert launched["work"]["process_launch_attempts"] == 1
    assert launched["work"]["process_launch_failure_events"] == 1

    def fail_capture(*_args, **_kwargs):
        raise ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation(
            "injected capture failure"
        )

    captured = run_failure(
        "capture-failure",
        "_capture_start",
        fail_capture,
    )
    assert captured["terminal_code"] == "PROCESS_IDENTITY_CAPTURE_FAILED"
    assert captured["process"]["launched"] is True
    assert captured["process"]["identity_capture_complete"] is False
    assert captured["process"]["executable_sha256"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "PROCESS_IDENTITY_CAPTURE_FAILED",
    }
    assert (
        captured["work"]["process_identity_capture_failure_events"] == 1
    )


def test_invalid_child_raw_metadata_is_journaled_and_attack_checked(
    profile,
    tmp_path: Path,
    monkeypatch,
) -> None:
    material = _material("invalid-child-metadata")
    request = _request(profile, "invalid-child-metadata", material)
    _registry_value, private_root, key_path = _private_key(tmp_path)
    service = ipc.start_v075_signer_owning_sealed_observer_service_v1(
        profile=profile
    )
    fd = ipc._stage_sealed_private_material_bytes_for_testing(  # noqa: SLF001
        material
    )

    def reject_child(*_args, **_kwargs):
        raise ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation(
            "injected child semantic rejection"
        )

    try:
        with monkeypatch.context() as patch:
            patch.setattr(ipc, "_validate_child_result", reject_child)
            result = _execute_fd(
                profile=profile,
                request=request,
                private_root=private_root,
                key_path=key_path,
                fd=fd,
                service=service,
            )
    finally:
        os.close(fd)

    document = result.to_document()
    assert document["terminal_code"] == "CHILD_RESULT_VALIDATION_FAILED"
    assert document["child_result"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "NO_VALID_CHILD_RESULT",
    }
    assert document["journal"]["entry_count"] == 2
    invalid_entry = document["journal"]["entries"][1]
    assert invalid_entry["message_kind"] == "UNTYPED_INVALID_CHILD_RESULT"
    assert invalid_entry["payload_byte_count"] == document["work"][
        "child_to_parent_payload_bytes"
    ]
    assert invalid_entry["message_id"] == ipc._invalid_child_payload_id(  # noqa: SLF001
        payload_sha256=invalid_entry["payload_sha256"],
        payload_byte_count=invalid_entry["payload_byte_count"],
    )
    ipc.verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
        raw=result.canonical_bytes,
        request_bytes=request.canonical_bytes,
        profile=profile,
    )

    for field, value in (
        ("payload_sha256", _id("wrong-invalid-child-digest")),
        (
            "payload_byte_count",
            invalid_entry["payload_byte_count"] + 1,
        ),
        ("message_kind", "TYPED_NONCERTIFICATE_RESULT"),
    ):
        attacked = result.to_document()
        attacked["journal"]["entries"][1][field] = value
        _rehash_journal(attacked)
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            ipc.verify_v075_signer_owning_sealed_observer_ipc_result_bytes_v1(
                raw=_rehash_result(attacked),
                request_bytes=request.canonical_bytes,
                profile=profile,
            )


def test_child_schema_profile_null_and_work_rehash_attacks_fail(
    profile,
    tmp_path: Path,
) -> None:
    material = _material("child-hardening")
    request = _request(profile, "child-hardening", material)
    _registry_value, private_root, key_path = _private_key(tmp_path)
    result = _execute(
        profile=profile,
        request=request,
        material=material,
        private_root=private_root,
        key_path=key_path,
    )
    original = result.to_document()["child_result"]
    request_projection = {
        key: request.to_document()[key]
        for key in (
            "profile_id",
            "service_program_id",
            "source_snapshot_id",
            "runtime_id",
            "request_id",
            "request_nonce",
            "session_external_id",
            "private_material_commitment_id",
            "signer_registry_id",
            "observer_evidence_key_id",
            "ordered_stream_ids",
        )
    }

    mutations = (
        ("schema_version", "9.9.9"),
        ("proposed_contract_version", "9.9.9"),
        ("profile_key", "foreign_profile"),
        ("terminal_code", "SIGNER_LOAD_FAILED"),
    )
    for key, value in mutations:
        attacked = deepcopy(original)
        attacked[key] = value
        payload = {
            name: child
            for name, child in attacked.items()
            if name != "child_result_id"
        }
        attacked["child_result_id"] = ipc._hash(  # noqa: SLF001
            "child_result",
            payload,
        )
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            ipc._validate_child_result(  # noqa: SLF001
                canonical_json_bytes(attacked),
                request=request_projection,
            )

    for key in (
        "observer_session_public_id",
        "signed_batch_journal_closure",
        "signed_batch_journal_closure_id",
        "b3_attestation",
        "b3_attestation_id",
    ):
        attacked = deepcopy(original)
        attacked[key]["hidden"] = True
        payload = {
            name: child
            for name, child in attacked.items()
            if name != "child_result_id"
        }
        attacked["child_result_id"] = ipc._hash(  # noqa: SLF001
            "child_result",
            payload,
        )
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            ipc._validate_child_result(  # noqa: SLF001
                canonical_json_bytes(attacked),
                request=request_projection,
            )

    attacked = deepcopy(original)
    attacked["child_work"]["observer_session_open_attempts"] = 1
    payload = {
        name: child
        for name, child in attacked.items()
        if name != "child_result_id"
    }
    attacked["child_result_id"] = ipc._hash(  # noqa: SLF001
        "child_result",
        payload,
    )
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
    ):
        ipc._validate_child_result(  # noqa: SLF001
            canonical_json_bytes(attacked),
            request=request_projection,
        )


def test_final_nested_profile_outcome_runtime_and_null_attacks_fail(
    profile,
    tmp_path: Path,
) -> None:
    material = _material("final-hardening")
    request = _request(profile, "final-hardening", material)
    _registry_value, private_root, key_path = _private_key(tmp_path)
    result = _execute(
        profile=profile,
        request=request,
        material=material,
        private_root=private_root,
        key_path=key_path,
    )

    for key, value in (
        ("schema_version", "9.9.9"),
        ("proposed_contract_version", "9.9.9"),
        ("profile_key", "foreign_profile"),
    ):
        attacked = result.to_document()
        attacked[key] = value
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            ipc.V075SignerOwningSealedObserverIPCResultV1(
                ipc._load(  # noqa: SLF001
                    _rehash_result(attacked),
                    label="final version attack",
                    cap=ipc.MAX_FINAL_RESULT_BYTES,
                )
            )

    for nested_key, field, value, role, id_key in (
        (
            "supervisor",
            "profile_id",
            _id("foreign-profile"),
            "supervisor",
            "supervisor_id",
        ),
        (
            "supervisor",
            "outcome",
            "SIGNER_LOAD_FAILED",
            "supervisor",
            "supervisor_id",
        ),
        (
            "work",
            "profile_id",
            _id("foreign-work-profile"),
            "work",
            "work_id",
        ),
    ):
        attacked = result.to_document()
        attacked[nested_key][field] = value
        _rehash_nested(
            attacked,
            key=nested_key,
            role=role,
            id_key=id_key,
        )
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            ipc.V075SignerOwningSealedObserverIPCResultV1(
                ipc._load(  # noqa: SLF001
                    _rehash_result(attacked),
                    label="nested binding attack",
                    cap=ipc.MAX_FINAL_RESULT_BYTES,
                )
            )

    attacked = result.to_document()
    attacked["process"]["executable_sha256"] = _id("foreign-executable")
    _rehash_nested(
        attacked,
        key="process",
        role="process",
        id_key="process_id",
    )
    attacked["supervisor"]["process_id"] = attacked["process_id"]
    _rehash_nested(
        attacked,
        key="supervisor",
        role="supervisor",
        id_key="supervisor_id",
    )
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
    ):
        ipc.V075SignerOwningSealedObserverIPCResultV1(
            ipc._load(  # noqa: SLF001
                _rehash_result(attacked),
                label="runtime executable attack",
                cap=ipc.MAX_FINAL_RESULT_BYTES,
            )
        )

    for key in (
        "observer_session_public_id",
        "signed_batch_journal_closure",
        "signed_batch_journal_closure_id",
        "b3_attestation",
        "b3_attestation_id",
    ):
        attacked = result.to_document()
        attacked[key]["hidden"] = True
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            ipc.V075SignerOwningSealedObserverIPCResultV1(
                ipc._load(  # noqa: SLF001
                    _rehash_result(attacked),
                    label="hidden final null attack",
                    cap=ipc.MAX_FINAL_RESULT_BYTES,
                )
            )


def test_child_process_supervisor_typed_nulls_are_exact(profile) -> None:
    material = _material("typed-null")
    request = _request(profile, "typed-null", material)
    result = ipc._prelaunch_nonce_result(  # noqa: SLF001
        profile=profile,
        request=request.to_document(),
        request_raw=request.canonical_bytes,
    )
    original = result.to_document()

    for key in ("child_result", "child_result_id"):
        attacked = deepcopy(original)
        attacked[key]["hidden"] = True
        with pytest.raises(
            ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
        ):
            ipc.V075SignerOwningSealedObserverIPCResultV1(
                ipc._load(  # noqa: SLF001
                    _rehash_result(attacked),
                    label="hidden child null attack",
                    cap=ipc.MAX_FINAL_RESULT_BYTES,
                )
            )

    attacked = deepcopy(original)
    attacked["process"]["pid"]["hidden"] = True
    _rehash_nested(
        attacked,
        key="process",
        role="process",
        id_key="process_id",
    )
    attacked["supervisor"]["process_id"] = attacked["process_id"]
    _rehash_nested(
        attacked,
        key="supervisor",
        role="supervisor",
        id_key="supervisor_id",
    )
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
    ):
        ipc.V075SignerOwningSealedObserverIPCResultV1(
            ipc._load(  # noqa: SLF001
                _rehash_result(attacked),
                label="hidden process null attack",
                cap=ipc.MAX_FINAL_RESULT_BYTES,
            )
        )

    attacked = deepcopy(original)
    attacked["supervisor"]["child_result_id"]["hidden"] = True
    _rehash_nested(
        attacked,
        key="supervisor",
        role="supervisor",
        id_key="supervisor_id",
    )
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
    ):
        ipc.V075SignerOwningSealedObserverIPCResultV1(
            ipc._load(  # noqa: SLF001
                _rehash_result(attacked),
                label="hidden supervisor null attack",
                cap=ipc.MAX_FINAL_RESULT_BYTES,
            )
        )

    attacked = deepcopy(original)
    attacked["supervisor"]["child_result_id"] = _id(
        "forged-no-valid-child-result"
    )
    _rehash_nested(
        attacked,
        key="supervisor",
        role="supervisor",
        id_key="supervisor_id",
    )
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverIPCV1InvariantViolation
    ):
        ipc.V075SignerOwningSealedObserverIPCResultV1(
            ipc._load(  # noqa: SLF001
                _rehash_result(attacked),
                label="supervisor null-to-CID attack",
                cap=ipc.MAX_FINAL_RESULT_BYTES,
            )
        )


def test_profile_to_document_is_a_deep_copy(profile) -> None:
    detached = profile.to_document()
    detached["runtime"]["required_flags"]["isolated"] = 999
    detached["source_snapshot"]["entries"][0]["path"] = "forged.py"
    current = profile.to_document()
    assert current["runtime"]["required_flags"]["isolated"] == 1
    assert current["source_snapshot"]["entries"][0]["path"] != "forged.py"


def test_all_claim_locks_and_production_opener_remain_closed(profile) -> None:
    document = profile.to_document()
    assert ipc.PROPOSED_CONTRACT_VERSION == "1.69.0"
    assert document["observer_session_ownership_complete"] is False
    assert document["b3_issuance_allowed"] is False
    assert ipc.OBSERVER_SESSION_OWNERSHIP_COMPLETE is False
    assert ipc.B3_ISSUANCE_ALLOWED is False
    for key in ipc._locks():  # noqa: SLF001
        assert document[key] is False
    with pytest.raises(
        ipc.V075SignerOwningSealedObserverProductionV1NotReady
    ):
        ipc.open_v075_signer_owning_sealed_observer_production_v1()
