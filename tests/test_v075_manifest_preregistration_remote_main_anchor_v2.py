from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_confirmatory_manifest_preregistration_v2 as manifest
from acfqp import (
    v075_campaign_authority_private_signer_runtime_v1 as signer_runtime,
)
from acfqp import v075_production_campaign_profile_v2 as campaign_profile
from acfqp import v075_production_semantic_authority_registry_v2 as semantic
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_remote_main_anchor_verifier_v2 as independent
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)
from tests.test_v075_campaign_authority_private_signer_runtime_v1 import (
    _key_document as _campaign_key_document,
    _write_private_key as _write_campaign_private_key,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _id(marker: str) -> str:
    return hashlib.sha256(marker.encode("utf-8")).hexdigest()


def _git(root: Path, *arguments: str) -> str:
    process = subprocess.run(
        ("git", "-C", str(root), *arguments),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return process.stdout.decode("utf-8").strip()


def _repository(
    tmp_path: Path,
    *,
    omitted_role: str | None = None,
) -> Path:
    root = tmp_path / "repository"
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "v075@example.invalid")
    _git(root, "config", "user.name", "V075 V2 Test")
    _git(root, "remote", "add", "origin", manifest.REPOSITORY_URL)
    for role, relative in manifest.REQUIRED_COMPONENT_SPECS:
        if role == omitted_role:
            continue
        source = PROJECT_ROOT / relative
        assert source.is_file(), (role, relative)
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    _git(root, "add", ".")
    _git(root, "commit", "-m", "freeze complete implementation closure")
    return root


def _registry() -> public.V075TrustedSignerRegistryV1:
    return public.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )


def _freeze_authority(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    commitment = public.V075OpaqueEnvironmentCommitmentV1(
        public.freeze_v075_public_family_generation_v1(),
        _id("opaque-v075-v2-test-commitment"),
    )
    execution_manifest = (
        manifest.freeze_v075_confirmatory_execution_manifest_v2(
            repository_root=root,
            signer_registry=_registry(),
            opaque_environment_commitment=commitment,
        )
    )
    assert (
        b'"final_preregistration_id"'
        not in execution_manifest.canonical_bytes
    )
    signature = sign_test_message(
        manifest.final_preregistration_signing_bytes_v2(
            execution_manifest
        )
    )
    final = manifest.finalize_v075_preregistration_v2(
        manifest=execution_manifest,
        campaign_authority_signature_hex=signature,
    )
    manifest_path = root / manifest.MANIFEST_REPOSITORY_PATH
    final_path = root / manifest.FINAL_PREREGISTRATION_REPOSITORY_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(execution_manifest.canonical_bytes)
    final_path.write_bytes(final.canonical_bytes)
    _git(root, "add", ".")
    _git(root, "commit", "-m", "first complete signed authority")
    head = _git(root, "rev-parse", "HEAD")
    _git(root, "update-ref", "refs/remotes/origin/main", head)
    return execution_manifest.to_document(), final.to_document()


def _ready_repository(tmp_path: Path) -> Path:
    root = _repository(tmp_path)
    _freeze_authority(root)
    return root


def _domain_hash(domain: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


def _rewrite_signed_authority(
    root: Path,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    manifest_path = root / manifest.MANIFEST_REPOSITORY_PATH
    final_path = root / manifest.FINAL_PREREGISTRATION_REPOSITORY_PATH
    manifest_document = json.loads(manifest_path.read_text("utf-8"))
    mutate(manifest_document)

    # Recompute all nested semantic identities when an attack changes them.
    semantic = manifest_document["semantic_registry_binding"]
    for binding in semantic["role_bindings"]:
        payload = dict(binding)
        payload.pop("binding_id")
        binding["binding_id"] = _domain_hash(
            manifest.DOMAIN_TAGS["semantic_binding"],
            payload,
        )
    semantic_payload = dict(semantic)
    semantic_payload.pop("binding_id")
    semantic["binding_id"] = _domain_hash(
        manifest.DOMAIN_TAGS["semantic_registry"],
        semantic_payload,
    )
    manifest_document["semantic_registry_binding_id"] = semantic[
        "binding_id"
    ]
    manifest_payload = dict(manifest_document)
    manifest_payload.pop("manifest_id")
    manifest_document["manifest_id"] = _domain_hash(
        manifest.DOMAIN_TAGS["manifest"],
        manifest_payload,
    )
    manifest_bytes = canonical_json_bytes(manifest_document)

    final_document = json.loads(final_path.read_text("utf-8"))
    final_document["confirmatory_execution_manifest_id"] = (
        manifest_document["manifest_id"]
    )
    final_document[
        "confirmatory_execution_manifest_bytes_sha256"
    ] = hashlib.sha256(manifest_bytes).hexdigest()
    final_document["semantic_registry_binding_id"] = manifest_document[
        "semantic_registry_binding_id"
    ]
    final_document["semantic_artifact_replay_id"] = manifest_document[
        "semantic_artifact_replay_id"
    ]
    final_document["component_registry_id"] = manifest_document[
        "component_registry_id"
    ]
    final_document["workload_id"] = manifest_document["workload_id"]
    unsigned = dict(final_document)
    unsigned.pop("final_preregistration_id")
    unsigned.pop("campaign_authority_signature_hex")
    unsigned.pop("campaign_authority_signature_verified")
    signature = sign_test_message(
        independent.FINAL_SIGNING_DOMAIN
        + b"\x00"
        + canonical_json_bytes(unsigned)
    )
    final_payload = {
        **unsigned,
        "campaign_authority_signature_hex": signature,
        "campaign_authority_signature_verified": True,
    }
    final_document = {
        **final_payload,
        "final_preregistration_id": _domain_hash(
            manifest.DOMAIN_TAGS["final_preregistration"],
            final_payload,
        ),
    }
    manifest_path.write_bytes(manifest_bytes)
    final_path.write_bytes(canonical_json_bytes(final_document))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "signed adversarial authority rewrite")
    _git(
        root,
        "update-ref",
        "refs/remotes/origin/main",
        _git(root, "rev-parse", "HEAD"),
    )


def test_v2_registry_is_independently_duplicated_and_target_closed() -> None:
    assert manifest.REQUIRED_COMPONENT_SPECS == (
        independent.REQUIRED_COMPONENT_SPECS
    )
    assert "v075_confirmatory_manifest_preregistration_v2" not in (
        "\n".join(
            line
            for line in inspect.getsource(independent).splitlines()
            if line.startswith(("from ", "import "))
        )
    )
    readiness = manifest.current_v075_pretarget_readiness_v2(PROJECT_ROOT)
    assert readiness.manifest_prerequisites_ready is False
    assert {
        "OPAQUE_ENVIRONMENT_COMMITMENT_NOT_SUPPLIED",
        "PUBLIC_SIGNER_REGISTRY_NOT_SUPPLIED",
    } <= set(readiness.manifest_blockers)
    assert readiness.production_open_ready is False
    assert readiness.production_open_blockers == (
        "PREOPEN_V2_MIGRATION_NOT_READY",
    )
    assert readiness.to_document()["target_accessed"] is False
    assert not (PROJECT_ROOT / manifest.MANIFEST_REPOSITORY_PATH).exists()
    assert not (
        PROJECT_ROOT / manifest.FINAL_PREREGISTRATION_REPOSITORY_PATH
    ).exists()


def test_remote_replays_v2_profile_without_importing_any_runner() -> None:
    exact = campaign_profile.freeze_v075_production_campaign_profile_v2()
    replayed_workload = independent._expected_workload()  # noqa: SLF001
    assert replayed_workload["runner_profile"] == exact.to_document()
    assert replayed_workload["runner_profile_id"] == exact.profile_id

    import_lines = "\n".join(
        line
        for line in inspect.getsource(independent).splitlines()
        if line.startswith(("from ", "import "))
    )
    assert "v075_production_campaign_runner" not in import_lines
    assert "v075_production_campaign_profile_v2" not in import_lines


def test_complete_first_qualifying_remote_main_chain_replays(
    tmp_path: Path,
) -> None:
    root = _ready_repository(tmp_path)
    anchor = independent.verify_v075_remote_main_anchor_independently_v2(
        root
    )
    document = anchor.to_document()
    assert document["first_qualifying_commit_verified"] is True
    assert (
        document["every_registered_role_static_verifier_dispatched"]
        is True
    )
    assert document["serialized_artifact_semantic_replay_complete"] is True
    assert document["final_signature_verified"] is True
    assert document["runner_profile_id"] == (
        campaign_profile.freeze_v075_production_campaign_profile_v2().profile_id
    )
    assert document["preopen_v2_migration_status"] == "NOT_READY"
    assert document["observer_open_allowed"] is False
    blocked = (
        independent.verify_v075_preopen_authority_v2_migration_blocked(root)
    )
    assert blocked.to_document()["legacy_v1_projection_issued"] is False


def test_every_semantic_role_binds_its_exact_producer_component(
    tmp_path: Path,
) -> None:
    root = _ready_repository(tmp_path)
    document = json.loads(
        (root / manifest.MANIFEST_REPOSITORY_PATH).read_text("utf-8")
    )
    components = {
        item["repository_path"]: item
        for item in document["component_blobs"]
    }
    bindings = document["semantic_registry_binding"]["role_bindings"]
    specs = semantic.canonical_v075_production_semantic_role_specs_v2()
    assert len(bindings) == len(specs)
    for binding, spec in zip(bindings, specs, strict=True):
        producer = components[spec.implementation_path]
        assert binding["producer_module"] == spec.producer_module
        assert binding["producer_component_id"] == producer["component_id"]
        assert (
            binding["producer_component_id"]
            != binding["verifier_component_id"]
        )


@pytest.mark.parametrize(
    "attack",
    ("omitted", "rehashed", "transplanted"),
)
def test_signed_producer_binding_attacks_cannot_qualify(
    tmp_path: Path,
    attack: str,
) -> None:
    root = _ready_repository(tmp_path)

    def mutate(document: dict[str, Any]) -> None:
        bindings = document["semantic_registry_binding"]["role_bindings"]
        if attack == "omitted":
            bindings[0].pop("producer_component_id")
        elif attack == "rehashed":
            bindings[0]["producer_component_id"] = _id(
                "attacker-rehashed-producer"
            )
        else:
            bindings[0]["producer_module"] = bindings[1][
                "producer_module"
            ]
            bindings[0]["producer_component_id"] = bindings[1][
                "producer_component_id"
            ]

    _rewrite_signed_authority(root, mutate)
    with pytest.raises(
        (
            independent.V075RemoteMainAnchorV2InvariantViolation,
            independent.V075RemoteMainAnchorV2NotReady,
        )
    ):
        independent.verify_v075_remote_main_anchor_independently_v2(root)


def test_real_private_signer_driven_finalizer_and_foreign_rejection(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    registry = _registry()
    execution_manifest = (
        manifest.freeze_v075_confirmatory_execution_manifest_v2(
            repository_root=root,
            signer_registry=registry,
            opaque_environment_commitment=(
                public.V075OpaqueEnvironmentCommitmentV1(
                    public.freeze_v075_public_family_generation_v1(),
                    _id("signer-driven-final"),
                )
            ),
        )
    )
    private_root, key_path = _write_campaign_private_key(
        tmp_path / "private",
        _campaign_key_document(registry),
    )
    signer = (
        signer_runtime.load_v075_production_campaign_authority_signer_v1(
            repository_root=PROJECT_ROOT,
            private_root=private_root,
            private_key_path=key_path,
            signer_registry=registry,
        )
    )
    final = manifest.finalize_v075_preregistration_with_signer_v2(
        manifest=execution_manifest,
        private_signer=signer,
    )
    assert (
        final.to_document()["campaign_authority_signature_verified"]
        is True
    )
    assert b"private_exponent" not in final.canonical_bytes
    assert "private_signer" not in final.to_document()

    class ForeignSigner:
        def public_verification_key_v1(
            self,
        ) -> public.V075RSAPublicVerificationKeyV1:
            return registry.observer_evidence_key

        def sign_final_preregistration_v2(self, message: bytes) -> str:
            return sign_test_message(message)

    with pytest.raises(
        manifest.V075ManifestV2InvariantViolation,
        match="foreign",
    ):
        manifest.finalize_v075_preregistration_with_signer_v2(
            manifest=execution_manifest,
            private_signer=ForeignSigner(),
        )


def test_omitted_component_cannot_freeze_manifest(tmp_path: Path) -> None:
    root = _repository(
        tmp_path,
        omitted_role="PRODUCTION_OCCURRENCE_AUTHORITY",
    )
    with pytest.raises((OSError, manifest.V075ManifestV2InvariantViolation)):
        manifest.freeze_v075_confirmatory_execution_manifest_v2(
            repository_root=root,
            signer_registry=_registry(),
            opaque_environment_commitment=(
                public.V075OpaqueEnvironmentCommitmentV1(
                    public.freeze_v075_public_family_generation_v1(),
                    _id("omitted"),
                )
            ),
        )


@pytest.mark.parametrize("attack", ["role_reuse", "string_only"])
def test_semantic_role_reuse_and_string_only_attacks_fail(
    tmp_path: Path,
    attack: str,
) -> None:
    root = _ready_repository(tmp_path)

    def mutate(document: dict[str, Any]) -> None:
        bindings = document["semantic_registry_binding"]["role_bindings"]
        if attack == "role_reuse":
            bindings[1]["role"] = bindings[0]["role"]
        else:
            bindings[1]["verifier_function"] = (
                "verify_v075_claimed_status_only_v2"
            )

    _rewrite_signed_authority(root, mutate)
    with pytest.raises(
        (
            independent.V075RemoteMainAnchorV2InvariantViolation,
            independent.V075RemoteMainAnchorV2NotReady,
        )
    ):
        independent.verify_v075_remote_main_anchor_independently_v2(root)


def test_rehashed_semantically_invalid_source_artifact_cannot_qualify(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    commitment = public.V075OpaqueEnvironmentCommitmentV1(
        public.freeze_v075_public_family_generation_v1(),
        _id("semantic-source-attack"),
    )
    typed_manifest = manifest.freeze_v075_confirmatory_execution_manifest_v2(
        repository_root=root,
        signer_registry=_registry(),
        opaque_environment_commitment=commitment,
    )
    manifest_document = typed_manifest.to_document()

    adapter_path = root / "specs/V075_SOURCE_PRIOR_ADAPTER.json"
    verification_path = (
        root / "specs/V075_SOURCE_PRIOR_ADAPTER_VERIFICATION.json"
    )
    adapter = json.loads(adapter_path.read_text("utf-8"))
    adapter["target_execution_allowed"] = True
    adapter_payload = dict(adapter)
    adapter_payload.pop("catalogue")
    adapter_payload.pop("adapter_id")
    adapter["adapter_id"] = _domain_hash(
        "acfqp:v075-source-prior-adapter:v1",
        adapter_payload,
    )
    adapter_bytes = canonical_json_bytes(adapter)
    adapter_path.write_bytes(adapter_bytes)

    verification = json.loads(verification_path.read_text("utf-8"))
    verification["adapter_id"] = adapter["adapter_id"]
    verification["recomputed_adapter_id"] = adapter["adapter_id"]
    verification["adapter_bytes_sha256"] = hashlib.sha256(
        adapter_bytes
    ).hexdigest()
    verification_payload = dict(verification)
    verification_payload.pop("verification_id")
    verification["verification_id"] = _domain_hash(
        "acfqp:v075-source-prior-adapter-verification:v1",
        verification_payload,
    )
    verification_path.write_bytes(canonical_json_bytes(verification))

    component_by_path = {
        item["repository_path"]: item
        for item in manifest_document["component_blobs"]
    }
    for relative in (
        "specs/V075_SOURCE_PRIOR_ADAPTER.json",
        "specs/V075_SOURCE_PRIOR_ADAPTER_VERIFICATION.json",
    ):
        raw = (root / relative).read_bytes()
        component = component_by_path[relative]
        component["git_blob_id"] = _git(
            root,
            "hash-object",
            "--",
            relative,
        )
        component["bytes_sha256"] = hashlib.sha256(raw).hexdigest()
        component["byte_count"] = len(raw)
        component_payload = dict(component)
        component_payload.pop("component_id")
        component["component_id"] = _domain_hash(
            manifest.DOMAIN_TAGS["component_blob"],
            component_payload,
        )
    manifest_document["component_registry_id"] = _domain_hash(
        manifest.DOMAIN_TAGS["component_registry"],
        {"component_blobs": manifest_document["component_blobs"]},
    )
    manifest_payload = dict(manifest_document)
    manifest_payload.pop("manifest_id")
    manifest_document["manifest_id"] = _domain_hash(
        manifest.DOMAIN_TAGS["manifest"],
        manifest_payload,
    )
    manifest_bytes = canonical_json_bytes(manifest_document)

    unsigned = manifest._final_unsigned_payload(typed_manifest)  # noqa: SLF001
    unsigned["confirmatory_execution_manifest_id"] = manifest_document[
        "manifest_id"
    ]
    unsigned[
        "confirmatory_execution_manifest_bytes_sha256"
    ] = hashlib.sha256(manifest_bytes).hexdigest()
    unsigned["component_registry_id"] = manifest_document[
        "component_registry_id"
    ]
    signature = sign_test_message(
        independent.FINAL_SIGNING_DOMAIN
        + b"\x00"
        + canonical_json_bytes(unsigned)
    )
    final_payload = {
        **unsigned,
        "campaign_authority_signature_hex": signature,
        "campaign_authority_signature_verified": True,
    }
    final_document = {
        **final_payload,
        "final_preregistration_id": _domain_hash(
            manifest.DOMAIN_TAGS["final_preregistration"],
            final_payload,
        ),
    }
    manifest_path = root / manifest.MANIFEST_REPOSITORY_PATH
    final_path = root / manifest.FINAL_PREREGISTRATION_REPOSITORY_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_bytes)
    final_path.write_bytes(canonical_json_bytes(final_document))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "fully rehashed semantic source attack")
    _git(
        root,
        "update-ref",
        "refs/remotes/origin/main",
        _git(root, "rev-parse", "HEAD"),
    )
    with pytest.raises(independent.V075RemoteMainAnchorV2NotReady):
        independent.verify_v075_remote_main_anchor_independently_v2(root)


def test_manifest_final_cycle_and_cross_domain_identity_fail(
    tmp_path: Path,
) -> None:
    root = _ready_repository(tmp_path)

    def mutate(document: dict[str, Any]) -> None:
        document["final_preregistration_id"] = _id("forbidden-cycle")

    _rewrite_signed_authority(root, mutate)
    with pytest.raises(
        (
            independent.V075RemoteMainAnchorV2InvariantViolation,
            independent.V075RemoteMainAnchorV2NotReady,
        )
    ):
        independent.verify_v075_remote_main_anchor_independently_v2(root)

    # A separate repository tests a validly rehashed but cross-domain ID.
    other = _ready_repository(tmp_path / "cross-domain")

    def cross_domain(document: dict[str, Any]) -> None:
        document["workload_id"] = document["component_blobs"][0][
            "component_id"
        ]

    _rewrite_signed_authority(other, cross_domain)
    with pytest.raises(
        (
            independent.V075RemoteMainAnchorV2InvariantViolation,
            independent.V075RemoteMainAnchorV2NotReady,
        )
    ):
        independent.verify_v075_remote_main_anchor_independently_v2(other)


def test_changed_component_and_stale_descendant_fail(
    tmp_path: Path,
) -> None:
    root = _ready_repository(tmp_path)
    target = root / "pyproject.toml"
    target.write_bytes(target.read_bytes() + b"\n# stale descendant\n")
    _git(root, "add", "pyproject.toml")
    _git(root, "commit", "-m", "change a bound component after qualification")
    _git(
        root,
        "update-ref",
        "refs/remotes/origin/main",
        _git(root, "rev-parse", "HEAD"),
    )
    with pytest.raises(independent.V075RemoteMainAnchorV2InvariantViolation):
        independent.verify_v075_remote_main_anchor_independently_v2(root)


def test_remote_head_mismatch_and_signature_mutation_fail(
    tmp_path: Path,
) -> None:
    root = _ready_repository(tmp_path)
    (root / "unrelated.txt").write_text("descendant", encoding="utf-8")
    _git(root, "add", "unrelated.txt")
    _git(root, "commit", "-m", "local-only descendant")
    with pytest.raises(independent.V075RemoteMainAnchorV2NotReady):
        independent.verify_v075_remote_main_anchor_independently_v2(root)

    signed = _ready_repository(tmp_path / "signature")
    final_path = signed / manifest.FINAL_PREREGISTRATION_REPOSITORY_PATH
    final = json.loads(final_path.read_text("utf-8"))
    signature = final["campaign_authority_signature_hex"]
    final["campaign_authority_signature_hex"] = (
        ("0" if signature[0] != "0" else "1") + signature[1:]
    )
    final_path.write_bytes(canonical_json_bytes(final))
    _git(signed, "add", ".")
    _git(signed, "commit", "-m", "mutate final signature")
    _git(
        signed,
        "update-ref",
        "refs/remotes/origin/main",
        _git(signed, "rev-parse", "HEAD"),
    )
    with pytest.raises(
        (
            independent.V075RemoteMainAnchorV2InvariantViolation,
            independent.V075RemoteMainAnchorV2NotReady,
        )
    ):
        independent.verify_v075_remote_main_anchor_independently_v2(signed)
