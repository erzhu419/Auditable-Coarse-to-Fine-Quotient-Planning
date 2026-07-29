from __future__ import annotations

from dataclasses import dataclass
import hashlib
import inspect
from pathlib import Path
import subprocess

import pytest

from acfqp import v075_confirmatory_manifest_preregistration_v1 as manifest
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_remote_main_anchor_verifier_v1 as independent
from tests.v075_signature_test_support import make_public_key


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _id(marker: str) -> str:
    return hashlib.sha256(marker.encode("utf-8")).hexdigest()


def _registry() -> public_authority.V075TrustedSignerRegistryV1:
    return public_authority.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )


def _git(root: Path, *arguments: str) -> str:
    process = subprocess.run(
        ("git", "-C", str(root), *arguments),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return process.stdout.decode("utf-8").strip()


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "V075 Test")
    return root


def _commit_all(root: Path, message: str) -> str:
    _git(root, "add", ".")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def test_current_manifest_is_honestly_not_ready_and_target_free() -> None:
    readiness = manifest.current_v075_pretarget_readiness_v1(PROJECT_ROOT)
    document = readiness.to_document()
    assert readiness.manifest is None
    assert document["ready"] is False
    assert document["registered_target_execution_allowed"] is False
    assert document["official_execution_allowed"] is False
    assert document["registered_observer_calls"] == 0
    assert document["target_accessed"] is False
    required = {
        "OBSERVER_PROFILE_PRODUCTION_AUTHORITY_NOT_CONCRETE",
        "TOTAL_LIFT_PRODUCTION_AUTHORITY_NOT_CONCRETE",
        "CAMPAIGN_RECONCILIATION_PRODUCTION_AUTHORITY_NOT_CONCRETE",
        "COMPLETE_BUNDLE_ENDPOINT_PRODUCTION_AUTHORITY_NOT_CONCRETE",
        "PRODUCTION_WORKER_REGISTRY_PRODUCTION_AUTHORITY_NOT_CONCRETE",
        "DEPENDENCY_LOCK_PRODUCTION_AUTHORITY_NOT_CONCRETE",
        "SOURCE_PRIOR_ADAPTER_PRODUCTION_AUTHORITY_NOT_CONCRETE",
        (
            "SOURCE_PRIOR_ADAPTER_VERIFICATION_"
            "PRODUCTION_AUTHORITY_NOT_CONCRETE"
        ),
    }
    assert required <= set(readiness.blockers)
    with pytest.raises(manifest.V075ConfirmatoryAuthorityNotReady):
        manifest.require_ready_v075_manifest_v1(readiness)
    with pytest.raises(manifest.V075ConfirmatoryAuthorityNotReady):
        manifest.finalize_v075_preregistration_v1(readiness)


def test_component_registry_covers_full_pretarget_dependency_surface() -> None:
    roles = dict(manifest.REQUIRED_COMPONENT_SPECS)
    assert roles["PRIVATE_OBSERVER_BOUNDARY"] == (
        "src/acfqp/v075_private_observer_boundary_v1.py"
    )
    assert roles["PRIVATE_ENVIRONMENT_GENERATION_PROFILE"] == (
        "src/acfqp/v075_private_environment_generation_profile_v1.py"
    )
    assert roles["FROZEN_SOURCE_PROPOSAL_ARCHIVE"] == (
        "src/acfqp/v075_frozen_source_proposal_archive_v1.py"
    )
    assert roles["SOURCE_OFFLINE_WORK_MATERIALIZER"] == (
        "src/acfqp/v075_source_offline_work_materializer_v1.py"
    )
    assert roles["SOURCE_REPLAY_AND_MATERIALIZATION_CONTROLLER"] == (
        "scripts/replay_and_materialize_v075_source_work.py"
    )
    assert roles["REGISTERED_OCCURRENCE_WORKER"] == (
        "src/acfqp/v075_registered_occurrence_worker_v1.py"
    )
    assert roles["PREOPEN_TARGET_AUTHORIZATION"] == (
        "src/acfqp/v075_preopen_target_authorization_v1.py"
    )
    assert {
        "EXACT_H2_TRANSITION_ENGINE",
        "OCCURRENCE_CAS_TRANSPORT",
        "TOTAL_LIFT_AUTHORITY",
        "CAMPAIGN_RECONCILIATION_AUTHORITY",
        "COMPLETE_BUNDLE_ENDPOINT_VERIFIER",
        "PRODUCTION_WORKER_REGISTRY",
        "DEPENDENCY_LOCK",
    } <= set(roles)
    assert manifest.REQUIRED_COMPONENT_SPECS == (
        independent.REQUIRED_COMPONENT_SPECS
    )


def test_caller_cannot_self_attest_a_concrete_authority_binding() -> None:
    role = manifest.V075ManifestAuthorityRoleV1.TOTAL_LIFT
    with pytest.raises(
        manifest.V075ConfirmatoryAuthorityInvariantViolation,
        match="semantic-verifier-issued",
    ):
        manifest.V075ConcreteAuthorityBindingV1(
            object(),
            role,
            _id("authority"),
            _id("verification"),
            _id("digest"),
        )

    @dataclass(frozen=True)
    class DuckBinding:
        role: object
        authority_id: str
        independent_verification_id: str
        canonical_artifact_sha256: str

    readiness = manifest.assess_v075_manifest_readiness_v1(
        PROJECT_ROOT,
        authority_inputs=(
            DuckBinding(
                role,
                _id("authority"),
                _id("verification"),
                _id("digest"),
            ),
        ),  # type: ignore[arg-type]
    )
    assert "AUTHORITY_INPUT_DUCK_TYPE_REJECTED" in readiness.blockers
    assert readiness.manifest is None


def test_dependency_lock_is_recomputed_and_semantically_bound() -> None:
    document, verification, binding = (
        manifest.verify_and_bind_v075_dependency_lock_v1(PROJECT_ROOT)
    )
    assert document["runtime_dependency_lock_id"] == (
        verification.dependency_lock_id
    )
    assert binding.role is (
        manifest.V075ManifestAuthorityRoleV1.DEPENDENCY_LOCK
    )
    assert binding.authority_id == verification.dependency_lock_id
    assert binding.independent_verification_id == (
        verification.verification_id
    )
    assert binding.canonical_artifact_sha256 == (
        verification.canonical_artifact_sha256
    )
    assert verification.to_document()["target_accessed"] is False
    assert document["network_access_required"] is False
    with pytest.raises(
        manifest.V075ConfirmatoryAuthorityInvariantViolation,
        match="independently issued",
    ):
        manifest.V075DependencyLockVerificationV1(
            object(),
            _id("lock"),
            _id("digest"),
            _id("component"),
        )


def test_dependency_lock_mutation_is_not_self_authorizing(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    lock_path = repository / manifest.DEPENDENCY_LOCK_REPOSITORY_PATH
    lock_path.parent.mkdir(parents=True)
    raw = (
        PROJECT_ROOT
        .joinpath(manifest.DEPENDENCY_LOCK_REPOSITORY_PATH)
        .read_text(encoding="utf-8")
    )
    lock_path.write_text(
        raw.replace('"version": "9.0.3"', '"version": "9.0.2"'),
        encoding="utf-8",
    )
    (repository / "pyproject.toml").write_bytes(
        (PROJECT_ROOT / "pyproject.toml").read_bytes()
    )
    _commit_all(repository, "tampered dependency lock")
    with pytest.raises(
        manifest.V075ConfirmatoryAuthorityInvariantViolation,
        match="contract or identity",
    ):
        manifest.verify_and_bind_v075_dependency_lock_v1(repository)


def test_remote_verifier_independently_replays_dependency_lock(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    lock_path = repository / manifest.DEPENDENCY_LOCK_REPOSITORY_PATH
    lock_path.parent.mkdir(parents=True)
    lock_path.write_bytes(
        PROJECT_ROOT
        .joinpath(manifest.DEPENDENCY_LOCK_REPOSITORY_PATH)
        .read_bytes()
    )
    (repository / "pyproject.toml").write_bytes(
        (PROJECT_ROOT / "pyproject.toml").read_bytes()
    )
    commit_id = _commit_all(repository, "exact dependency lock")
    _document, verification, binding = (
        manifest.verify_and_bind_v075_dependency_lock_v1(PROJECT_ROOT)
    )
    assert independent._verify_dependency_lock_at_commit(  # type: ignore[attr-defined]
        repository,
        commit_id,
    ) == (
        binding.authority_id,
        verification.verification_id,
        verification.canonical_artifact_sha256,
    )


def test_manifest_and_final_preregistration_reject_duck_types() -> None:
    with pytest.raises(
        manifest.V075ConfirmatoryAuthorityInvariantViolation,
        match="factory-issued",
    ):
        manifest.V075ConfirmatoryExecutionManifestV1(
            object(),
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            (),
            (),
        )
    with pytest.raises(
        manifest.V075ConfirmatoryAuthorityInvariantViolation,
        match="factory-issued",
    ):
        manifest.V075FinalPreregistrationV1(
            object(),
            object(),  # type: ignore[arg-type]
        )
    with pytest.raises(
        independent.V075RemoteMainAnchorInvariantViolation,
        match="verifier-issued",
    ):
        independent.V075RemoteMainAnchorAttestationV1(
            object(),
            "a" * 40,
            "b" * 40,
            (),
            "c" * 40,
            "d" * 40,
            _id("manifest"),
            _id("final"),
            _id("family"),
            _id("environment"),
            _id("observer-profile"),
            _registry(),
            _id("components"),
            _id("authorities"),
        )
    with pytest.raises(
        independent.V075RemoteMainAnchorInvariantViolation,
        match="verifier-issued",
    ):
        independent.V075ProductionOpenAuthorityV1(
            object(),
            object(),  # type: ignore[arg-type]
        )


def test_independent_api_accepts_no_claim_expected_id_or_registry() -> None:
    verify_signature = inspect.signature(
        independent.verify_v075_remote_main_anchor_independently_v1
    )
    open_signature = inspect.signature(
        independent.verify_and_mint_v075_production_open_authority_v1
    )
    assert tuple(verify_signature.parameters) == ("repository_root",)
    assert tuple(open_signature.parameters) == ("repository_root",)
    forbidden = {
        "claim",
        "expected_id",
        "manifest_id",
        "final_preregistration_id",
        "registry",
        "signer_registry",
        "commit_id",
        "status",
        "target_execution_allowed",
    }
    assert forbidden.isdisjoint(verify_signature.parameters)
    assert forbidden.isdisjoint(open_signature.parameters)

    # A valid caller-owned registry remains nonauthorizing because there is no
    # API path through which it can influence Git-object replay.
    self_signed = _registry()
    with pytest.raises(TypeError):
        independent.verify_and_mint_v075_production_open_authority_v1(
            PROJECT_ROOT,
            signer_registry=self_signed,  # type: ignore[call-arg]
        )


def test_no_remote_main_or_incomplete_remote_cannot_mint_open_authority(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    (repository / "README.md").write_text("no authority\n", encoding="utf-8")
    _commit_all(repository, "base")
    _git(
        repository,
        "remote",
        "add",
        "origin",
        independent.REPOSITORY_URL,
    )
    _git(
        repository,
        "update-ref",
        independent.REMOTE_TRACKING_REF,
        _git(repository, "rev-parse", "HEAD"),
    )
    with pytest.raises(
        independent.V075ProductionOpenAuthorityNotReady,
        match="no complete qualifying",
    ):
        independent.verify_and_mint_v075_production_open_authority_v1(
            repository
        )


def test_stale_component_tree_blob_is_rejected(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    role, relative = manifest.REQUIRED_COMPONENT_SPECS[0]
    component_path = repository / relative
    component_path.parent.mkdir(parents=True)
    component_path.write_text("first authority bytes\n", encoding="utf-8")
    first_commit = _commit_all(repository, "first")
    component = manifest.collect_v075_component_blob_v1(
        repository,
        role=role,
    )
    independent._verify_component_document(  # type: ignore[attr-defined]
        repository,
        first_commit,
        component.to_document(),
        role,
        relative,
    )

    component_path.write_text("stale replacement bytes\n", encoding="utf-8")
    second_commit = _commit_all(repository, "replace")
    with pytest.raises(
        independent.V075RemoteMainAnchorInvariantViolation,
        match="blob closure",
    ):
        independent._verify_component_document(  # type: ignore[attr-defined]
            repository,
            second_commit,
            component.to_document(),
            role,
            relative,
        )


def test_wrong_ancestry_with_either_sentinel_is_detected(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    family_sentinel = _id("family generation sentinel")
    final_sentinel = _id("final preregistration sentinel")
    (repository / "old.txt").write_text(
        f"previous family={family_sentinel}\n",
        encoding="utf-8",
    )
    ancestor = _commit_all(repository, "ancestor leaked family")
    (repository / "old.txt").unlink()
    (repository / "new.txt").write_text("candidate\n", encoding="utf-8")
    candidate = _commit_all(repository, "candidate")
    ancestors = independent._all_ancestors(  # type: ignore[attr-defined]
        repository,
        candidate,
    )
    assert ancestor in ancestors
    assert any(
        independent._tree_contains_any_sentinel(  # type: ignore[attr-defined]
            repository,
            commit,
            (
                final_sentinel.encode("ascii"),
                family_sentinel.encode("ascii"),
            ),
        )
        for commit in ancestors
    )


def test_per_role_semantic_verifiers_remain_fail_closed() -> None:
    assert independent._ROLE_SEMANTIC_VERIFIER_IMPLEMENTED == {  # type: ignore[attr-defined]
        role: role == "DEPENDENCY_LOCK"
        for role in independent.REQUIRED_AUTHORITY_ROLE_ORDER
    }
    assert (
        independent.V075ProductionOpenAuthorityV1.__doc__
        == (
            "Legacy remote-main preauthorization; never an "
            "observer-open input."
        )
    )
    source = inspect.getsource(
        independent.verify_and_mint_v075_production_open_authority_v1
    )
    assert "verify_v075_remote_main_anchor_independently_v1" in source
    assert "V075ProductionOpenAuthorityV1(_ISSUER, anchor)" in source


def test_manifest_binding_direction_is_forward_only_by_schema() -> None:
    manifest_source = inspect.getsource(
        manifest.V075ConfirmatoryExecutionManifestV1._payload
    )
    final_source = inspect.getsource(
        manifest.V075FinalPreregistrationV1._payload
    )
    assert '"final_preregistration_id_embedded": False' in manifest_source
    assert (
        "MANIFEST_THEN_FINAL_PREREGISTRATION_THEN_REMOTE_MAIN"
        in manifest_source
    )
    assert '"confirmatory_execution_manifest_id"' in final_source
    assert '"signer_registry"' in final_source
    assert '"campaign_authority_public_key_bytes"' in final_source
    assert '"observer_evidence_public_key_bytes"' in final_source
