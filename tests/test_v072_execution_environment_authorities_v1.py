from __future__ import annotations

from dataclasses import replace
import inspect
import json
from pathlib import Path
import shutil

import pytest

from acfqp import v072_confirmatory_execution_manifest_v1 as manifest
from acfqp import v072_execution_environment_authority_v1 as authority
from acfqp import (
    v072_execution_environment_independent_verifier_v1
    as independent,
)
from scripts import run_v072_confirmatory_tests as test_runner


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def frozen_pair():
    authorities = (
        authority.freeze_v072_execution_environment_authorities_v1(
            REPOSITORY_ROOT
        )
    )
    attestation = (
        independent
        .verify_execution_environment_authorities_independently_v1(
            REPOSITORY_ROOT,
            authorities,
        )
    )
    return authorities, attestation


def _copy_environment_evidence(tmp_path: Path) -> Path:
    destination = tmp_path / "repo"
    destination.mkdir(parents=True)
    shutil.copy2(
        REPOSITORY_ROOT / "pyproject.toml",
        destination / "pyproject.toml",
    )
    shutil.copytree(
        REPOSITORY_ROOT / "tests",
        destination / "tests",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    for relative in (
        authority.TEST_COMMAND_SPEC_PATH,
        authority.RUNTIME_LOCK_SPEC_PATH,
        *authority.IMPLEMENTATION_PATHS,
    ):
        source = REPOSITORY_ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return destination


def _write_pretty(path: Path, document: dict) -> None:
    path.write_text(
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def test_three_typed_authorities_and_independent_attestation_bind_exact_ids(
    frozen_pair,
) -> None:
    authorities, attestation = frozen_pair
    test_authority = authorities.test_command_manifest
    runtime = authorities.runtime_dependency_lock
    interpreter = authorities.interpreter_build_identity

    assert test_authority.exact_test_command == authority.EXACT_TEST_COMMAND
    invocation = test_authority.to_document()["invocation"]
    assert invocation["inner_argv"] == list(authority.INNER_TEST_COMMAND)
    assert invocation["parallel_module_workers"] == 32
    assert invocation["fresh_content_id_recomputation"] is True
    assert test_authority.deterministic_environment_settings == (
        authority.DETERMINISTIC_ENVIRONMENT_SETTINGS
    )
    assert runtime.interpreter_build_identity is interpreter
    assert attestation.test_command_manifest_id == (
        test_authority.test_command_manifest_id
    )
    assert attestation.runtime_dependency_lock_id == (
        runtime.runtime_dependency_lock_id
    )
    assert attestation.interpreter_build_identity_id == (
        interpreter.interpreter_build_identity_id
    )
    assert attestation.to_document()["production_builder_called"] is False
    assert attestation.to_document()["target_access"] is False


def test_private_temp_policy_overwrites_hostile_host_environment(
    tmp_path: Path,
) -> None:
    private = tmp_path / "private"
    private.mkdir()
    hostile = {
        "TMP": "/mnt/c/host-deletes-pytest-capture",
        "TEMP": "/mnt/c/host-deletes-pytest-capture",
        "TMPDIR": "/mnt/c/host-deletes-pytest-capture",
        "UNCHANGED": "value",
    }
    environment = test_runner.build_confirmatory_environment_v1(
        hostile,
        private.resolve(strict=True),
    )
    assert environment["UNCHANGED"] == "value"
    for name in test_runner.TEMPORARY_VARIABLES:
        assert environment[name] == str(private.resolve(strict=True))
    assert tuple(
        (name, environment[name])
        for name, _ in test_runner.DETERMINISTIC_SETTINGS
    ) == test_runner.DETERMINISTIC_SETTINGS

    document = (
        authority.build_expected_confirmatory_test_command_document_v1(
            REPOSITORY_ROOT
        )
    )
    policy = document["invocation"]["temporary_directory_policy"]
    assert policy == {
        "kind": "PRIVATE_MKDTEMP_UNDER_REPOSITORY_TMP",
        "host_tmp_environment_inherited": False,
        "runtime_random_path_in_content_id": False,
        "overridden_variables": [
            "ACFQP_PARALLEL_TEMP_ROOT",
            "TEMP",
            "TMP",
            "TMPDIR",
        ],
        "cleanup_required": True,
        "module_process_isolation": True,
    }
    assert str(private) not in repr(document)


def test_private_temp_policy_rejects_relative_missing_and_symlink_roots(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="absolute real directory"):
        test_runner.build_confirmatory_environment_v1({}, "relative-temp")
    with pytest.raises(ValueError, match="absolute real directory"):
        test_runner.build_confirmatory_environment_v1(
            {},
            tmp_path / "missing",
        )
    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="absolute real directory"):
        test_runner.build_confirmatory_environment_v1({}, linked)


def test_spec_documents_are_exact_current_replays(frozen_pair) -> None:
    authorities, _ = frozen_pair
    expected_test = (
        authority.build_expected_confirmatory_test_command_document_v1(
            REPOSITORY_ROOT
        )
    )
    expected_runtime = (
        authority.build_expected_runtime_dependency_lock_document_v1(
            REPOSITORY_ROOT
        )
    )
    assert authorities.test_command_manifest.to_document() == expected_test
    assert (
        authorities.runtime_dependency_lock.to_document()
        == expected_runtime
    )
    assert (
        authorities.interpreter_build_identity.to_document()
        == expected_runtime["interpreter_build_identity"]
    )
    assert (
        (REPOSITORY_ROOT / authority.TEST_COMMAND_SPEC_PATH).read_bytes()
        == authority.render_expected_confirmatory_test_command_spec_v1(
            REPOSITORY_ROOT
        )
    )
    assert (
        (REPOSITORY_ROOT / authority.RUNTIME_LOCK_SPEC_PATH).read_bytes()
        == authority.render_expected_runtime_dependency_lock_spec_v1(
            REPOSITORY_ROOT
        )
    )


def test_public_freezer_accepts_no_digest_status_or_document_input() -> None:
    signature = inspect.signature(
        authority.freeze_v072_execution_environment_authorities_v1
    )
    assert tuple(signature.parameters) == ("repository_root",)
    assert all(
        forbidden not in signature.parameters
        for forbidden in (
            "digest",
            "status",
            "valid",
            "manifest_id",
            "runtime_dependency_lock_id",
            "interpreter_build_identity_id",
            "document",
        )
    )
    verifier_signature = inspect.signature(
        independent
        .verify_execution_environment_authorities_independently_v1
    )
    assert tuple(verifier_signature.parameters) == (
        "repository_root",
        "authorities",
    )


def test_direct_unminted_construction_fails_closed(frozen_pair) -> None:
    authorities, _ = frozen_pair
    test = authorities.test_command_manifest
    with pytest.raises(
        authority.V072ExecutionEnvironmentAuthorityInvariantViolation,
        match="internally replay-minted",
    ):
        authority.ConfirmatoryTestCommandManifestV1(
            object(),
            test._document_json,
            test.spec_file_sha256,
            test.spec_file_byte_count,
        )
    with pytest.raises(
        independent
        .V072ExecutionEnvironmentIndependentVerificationFailure,
        match="not replay-minted",
    ):
        independent.IndependentExecutionEnvironmentAttestationV1(
            object(),
            test.test_command_manifest_id,
            authorities.runtime_dependency_lock.runtime_dependency_lock_id,
            (
                authorities.interpreter_build_identity
                .interpreter_build_identity_id
            ),
            test.spec_file_sha256,
            authorities.runtime_dependency_lock.spec_file_sha256,
        )


def test_canonical_spec_tamper_is_rejected(tmp_path: Path) -> None:
    root = _copy_environment_evidence(tmp_path)
    path = root / authority.TEST_COMMAND_SPEC_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    document["invocation"]["argv"][-1] = "cacheprovider"
    _write_pretty(path, document)
    with pytest.raises(
        authority.V072ExecutionEnvironmentAuthorityInvariantViolation,
        match="test-command spec differs",
    ):
        authority.freeze_v072_execution_environment_authorities_v1(root)


def test_noncanonical_duplicate_and_symlink_specs_fail_closed(
    tmp_path: Path,
) -> None:
    root = _copy_environment_evidence(tmp_path)
    path = root / authority.TEST_COMMAND_SPEC_PATH
    data = path.read_text(encoding="utf-8")
    path.write_text(data + "\n", encoding="utf-8")
    with pytest.raises(
        authority.V072ExecutionEnvironmentAuthorityInvariantViolation,
        match="canonical pretty",
    ):
        authority.freeze_v072_execution_environment_authorities_v1(root)

    root = _copy_environment_evidence(tmp_path / "linked")
    path = root / authority.TEST_COMMAND_SPEC_PATH
    outside = tmp_path / "outside.json"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(
        authority.V072ExecutionEnvironmentAuthorityInvariantViolation,
        match="symlink",
    ):
        authority.freeze_v072_execution_environment_authorities_v1(root)


def test_test_tree_and_pyproject_drift_are_rejected(tmp_path: Path) -> None:
    root = _copy_environment_evidence(tmp_path)
    target = root / "tests/test_v072_execution_environment_authorities_v1.py"
    target.write_bytes(target.read_bytes() + b"\n# drift\n")
    with pytest.raises(
        authority.V072ExecutionEnvironmentAuthorityInvariantViolation,
        match="test-command spec differs",
    ):
        authority.freeze_v072_execution_environment_authorities_v1(root)

    root = _copy_environment_evidence(tmp_path / "pyproject")
    pyproject = root / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            'test = ["pytest>=8"]',
            'test = ["pytest>=8", "packaging>=23"]',
        ),
        encoding="utf-8",
    )
    with pytest.raises(
        authority.V072ExecutionEnvironmentAuthorityInvariantViolation,
        match="test-command spec differs",
    ):
        authority.freeze_v072_execution_environment_authorities_v1(root)


def test_runtime_spec_tamper_is_rejected(tmp_path: Path) -> None:
    root = _copy_environment_evidence(tmp_path)
    path = root / authority.RUNTIME_LOCK_SPEC_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    document["interpreter_build_identity"]["hexversion"] += 1
    _write_pretty(path, document)
    with pytest.raises(
        authority.V072ExecutionEnvironmentAuthorityInvariantViolation,
        match="runtime lock differs",
    ):
        authority.freeze_v072_execution_environment_authorities_v1(root)


def test_independent_verifier_does_not_call_production_derivers(
    frozen_pair,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorities, expected = frozen_pair

    def forbidden(*_args, **_kwargs):
        raise AssertionError("production environment derivation was called")

    monkeypatch.setattr(
        authority,
        "build_expected_confirmatory_test_command_document_v1",
        forbidden,
    )
    monkeypatch.setattr(
        authority,
        "build_expected_runtime_dependency_lock_document_v1",
        forbidden,
    )
    monkeypatch.setattr(
        authority,
        "freeze_v072_execution_environment_authorities_v1",
        forbidden,
    )
    replayed = (
        independent
        .verify_execution_environment_authorities_independently_v1(
            REPOSITORY_ROOT,
            authorities,
        )
    )
    assert replayed.to_document() == expected.to_document()


def test_forged_typed_document_is_rejected_by_independent_replay(
    frozen_pair,
) -> None:
    authorities, _ = frozen_pair
    forged_document = authorities.test_command_manifest.to_document()
    forged_document["invocation"]["argv"][-1] = "cacheprovider"
    forged = replace(
        authorities.test_command_manifest,
        _document_json=json.dumps(
            forged_document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    )
    forged_bundle = replace(
        authorities,
        test_command_manifest=forged,
    )
    with pytest.raises(
        independent
        .V072ExecutionEnvironmentIndependentVerificationFailure,
        match="independent replay differs",
    ):
        (
            independent
            .verify_execution_environment_authorities_independently_v1(
            REPOSITORY_ROOT,
            forged_bundle,
            )
        )


def test_ids_are_domain_separated_and_specs_never_execute(frozen_pair) -> None:
    authorities, _ = frozen_pair
    test = authorities.test_command_manifest.to_document()
    runtime = authorities.runtime_dependency_lock.to_document()
    interpreter = authorities.interpreter_build_identity.to_document()
    assert len(
        {
            test["test_command_manifest_id"],
            runtime["runtime_dependency_lock_id"],
            interpreter["interpreter_build_identity_id"],
        }
    ) == 3
    assert test["executes_tests"] is False
    assert test["target_access"] is False
    assert runtime["executes_tests"] is False
    assert runtime["executes_package_installer"] is False
    assert runtime["target_access"] is False
    assert "absolute_path" not in repr(interpreter)


def test_manifest_readiness_uses_independently_replayed_environment_ids(
    frozen_pair,
) -> None:
    authorities, attestation = frozen_pair
    readiness = (
        manifest.inspect_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT
        )
    )
    bindings = readiness.global_bindings
    assert bindings["test_command_manifest_id"] == (
        authorities.test_command_manifest.test_command_manifest_id
    )
    assert bindings["test_command_manifest_id"] == (
        attestation.test_command_manifest_id
    )
    assert bindings["runtime_dependency_lock_id"] == (
        authorities.runtime_dependency_lock.runtime_dependency_lock_id
    )
    assert bindings["runtime_dependency_lock_id"] == (
        attestation.runtime_dependency_lock_id
    )
    assert bindings["interpreter_build_identity_id"] == (
        authorities.interpreter_build_identity
        .interpreter_build_identity_id
    )
    assert bindings["interpreter_build_identity_id"] == (
        attestation.interpreter_build_identity_id
    )
    assert readiness.missing_applicable_bindings == (
        "source_reconstruction_recipe_id",
        "source_archive_id",
        "source_archive_verification_attestation_id",
    )
    assert readiness.target_execution_allowed is False
    assert manifest.FINALIZATION_ENABLED is True
