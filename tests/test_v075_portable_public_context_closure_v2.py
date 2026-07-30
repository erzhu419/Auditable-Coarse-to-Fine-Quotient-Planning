from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_portable_public_context_closure_v2 as closure
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_remote_main_anchor_verifier_v2 as remote
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-portable-public-context-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _source_manifest() -> (
    closure.V075PortablePublicContextSourceManifestV2
):
    return closure.V075PortablePublicContextSourceManifestV2(
        (
            closure.V075PortablePublicContextSourceManifestEntryV2(
                "acfqp.phase3e_ids",
                "acfqp/phase3e_ids.py",
                _id("phase3e-ids-source"),
                10_001,
            ),
            closure.V075PortablePublicContextSourceManifestEntryV2(
                "acfqp.v075_portable_occurrence_evidence_bundle_v2",
                (
                    "acfqp/"
                    "v075_portable_occurrence_evidence_bundle_v2.py"
                ),
                _id("portable-bundle-source"),
                20_002,
            ),
        )
    )


@pytest.fixture
def public_context(monkeypatch: pytest.MonkeyPatch):
    (
        _environment,
        _salt,
        namespace,
        authorization,
        _signer,
    ) = observer_fixture._fixture("portable-public-context")
    anchor = namespace.anchor
    original_to_document = (
        remote.V075RemoteMainAnchorAttestationV2.to_document
    )

    def ready_document(
        self: remote.V075RemoteMainAnchorAttestationV2,
    ) -> dict:
        result = original_to_document(self)
        result["preopen_v2_migration_status"] = "READY"
        return result

    monkeypatch.setattr(
        remote.V075RemoteMainAnchorAttestationV2,
        "to_document",
        ready_document,
    )
    monkeypatch.setattr(
        remote,
        "verify_v075_remote_main_anchor_independently_v2",
        lambda _root: anchor,
    )
    monkeypatch.setattr(
        preopen,
        "_verify_tracked_blob_closure_v2",
        lambda **_kwargs: (
            authorization.tracked_blobs,
            authorization.opaque_environment_commitment,
        ),
    )
    manifest = _source_manifest()
    return {
        "anchor": anchor,
        "namespace": namespace,
        "authorization": authorization,
        "reveal": authorization.private_reveal_attestation,
        "manifest": manifest,
    }


def _freeze(public_context):
    return closure.freeze_v075_portable_public_context_evidence_closure_v2(
        repository_root=PROJECT_ROOT,
        source_manifest_bytes=public_context["manifest"].canonical_bytes,
        namespace_bytes=public_context["namespace"].canonical_bytes,
        observer_open_authorization_bytes=(
            public_context["authorization"].canonical_bytes
        ),
        private_reveal_verification_attestation_bytes=(
            public_context["reveal"].canonical_bytes
        ),
    )


def _all_keys(value) -> tuple[str, ...]:
    if type(value) is dict:
        return tuple(value) + tuple(
            key
            for child in value.values()
            for key in _all_keys(child)
        )
    if type(value) is list:
        return tuple(
            key for child in value for key in _all_keys(child)
        )
    return ()


def test_exact_three_role_public_closure_replays_and_binds_context(
    public_context,
) -> None:
    result = _freeze(public_context)
    replayed = (
        closure
        .verify_v075_portable_public_context_evidence_closure_bytes_v2(
            repository_root=PROJECT_ROOT,
            raw=result.canonical_bytes,
        )
    )
    assert replayed == result
    assert tuple(item.role.value for item in result.dependency_records) == (
        "PUBLIC_TARGET_TAPE_NAMESPACE",
        "OBSERVER_OPEN_AUTHORIZATION",
        "PRIVATE_REVEAL_VERIFICATION_ATTESTATION",
    )
    assert all(
        item.to_document()["dependency_semantic_replay_complete"] is True
        for item in result.dependency_attestations
    )
    assert result.remote_main_anchor_id == public_context["anchor"].anchor_id
    assert (
        result.repository_binding.repository_url
        == remote.REPOSITORY_URL
    )
    assert (
        result.repository_binding.anchor_commit_id
        == public_context["anchor"].commit_id
    )
    assert (
        result.repository_binding.anchor_tree_id
        == public_context["anchor"].tree_id
    )
    assert (
        result.source_manifest.manifest_id
        == public_context["manifest"].manifest_id
    )
    assert (
        result.opaque_environment_commitment_id
        == public_context["namespace"].environment_commitment.commitment_id
    )
    expected_key = (
        public_context["namespace"].signer_registry.observer_evidence_key
    )
    assert result.namespace_public_key_id == expected_key.key_id
    assert result.namespace_public_key_document == expected_key.to_document()
    assert result.to_document()["source_archive_verified_by_this_closure"] is False
    assert result.to_document()["terminal_code"] == (
        "PUBLIC_CONTEXT_RECORDS_REPLAYED_SOURCE_AUTHORITY_INCOMPLETE"
    )
    assert result.to_document()["source_manifest_authority_status"] == (
        "OPAQUE_CONTENT_ID_BOUND_UNVERIFIED_BY_THIS_MODULE"
    )
    assert result.to_document()["ipc_source_snapshot_attestation"] == {
        "kind": "NOT_SUPPLIED",
        "reason": (
            "VERIFIED_IPC_SOURCE_SNAPSHOT_ATTESTATION_NOT_PROVIDED_TO_THIS_"
            "CONSTRUCTION_CLOSURE"
        ),
    }
    assert result.to_document()["source_authority_complete"] is False
    for item in (
        result.repository_binding.to_document(),
        *(record.to_document() for record in result.dependency_records),
        *(
            attestation.to_document()
            for attestation in result.dependency_attestations
        ),
    ):
        assert item["source_manifest_authority_status"] == (
            "OPAQUE_CONTENT_ID_BOUND_UNVERIFIED_BY_THIS_MODULE"
        )
        assert item["ipc_source_snapshot_attestation_status"] == (
            "NOT_SUPPLIED"
        )
        assert item["source_authority_complete"] is False
    assert result.to_document()["observer_opened"] is False
    assert result.to_document()["fresh_heldout_accessed"] is False
    assert result.to_document()["official_execution_allowed"] is False


@pytest.mark.parametrize(
    "attack",
    (
        "namespace-artifact",
        "wrong-role-artifact",
        "record-order",
        "duplicate-role",
        "attestation",
        "source-manifest-cached-id",
        "source-manifest-rehashed",
        "repository",
        "public-key",
        "anchor",
    ),
)
def test_nested_bytes_role_and_context_transplants_fail_closed(
    public_context,
    attack: str,
) -> None:
    result = _freeze(public_context)
    document = loads_canonical_json(result.canonical_bytes)
    if attack == "namespace-artifact":
        document["dependency_records"][0]["artifact_document"][
            "opaque_environment_commitment_id"
        ] = _id("foreign-commitment")
    elif attack == "wrong-role-artifact":
        document["dependency_records"][0]["artifact_document"] = (
            document["dependency_records"][2]["artifact_document"]
        )
    elif attack == "record-order":
        document["dependency_records"][0:2] = reversed(
            document["dependency_records"][0:2]
        )
    elif attack == "duplicate-role":
        document["dependency_records"][1]["role"] = (
            "PUBLIC_TARGET_TAPE_NAMESPACE"
        )
    elif attack == "attestation":
        document["dependency_attestations"][0]["record_id"] = _id(
            "foreign-record"
        )
    elif attack in {
        "source-manifest-cached-id",
        "source-manifest-rehashed",
    }:
        document["source_manifest"]["entries"][0]["source_sha256"] = _id(
            "changed-source"
        )
        if attack == "source-manifest-rehashed":
            payload = dict(document["source_manifest"])
            payload.pop("manifest_id")
            document["source_manifest"]["manifest_id"] = hashlib.sha256(
                closure.SOURCE_MANIFEST_DOMAIN_TAG.encode("utf-8")
                + b"\x00"
                + canonical_json_bytes(payload)
            ).hexdigest()
    elif attack == "repository":
        document["repository_binding"]["repository_url"] = (
            "https://example.invalid/foreign.git"
        )
    elif attack == "public-key":
        document["namespace_public_key"]["key_id"] = _id(
            "foreign-public-key"
        )
    else:
        document["remote_main_anchor_id"] = _id("foreign-anchor")
    with pytest.raises(
        closure.V075PortablePublicContextV2InvariantViolation
    ):
        closure.verify_v075_portable_public_context_evidence_closure_bytes_v2(
            repository_root=PROJECT_ROOT,
            raw=canonical_json_bytes(document),
        )


def test_source_manifest_parser_rejects_unknown_missing_and_duplicate_fields(
) -> None:
    manifest = _source_manifest()
    baseline = loads_canonical_json(manifest.canonical_bytes)
    for mutate in (
        lambda item: item.update({"unknown": False}),
        lambda item: item.pop("root_module"),
        lambda item: item["entries"].append(item["entries"][0]),
    ):
        document = loads_canonical_json(manifest.canonical_bytes)
        mutate(document)
        with pytest.raises(
            closure.V075PortablePublicContextV2InvariantViolation
        ):
            closure.replay_v075_portable_public_context_source_manifest_bytes_v2(
                canonical_json_bytes(document)
            )
    assert (
        closure
        .replay_v075_portable_public_context_source_manifest_bytes_v2(
            canonical_json_bytes(baseline)
        )
        == manifest
    )


def test_every_new_role_uses_its_exact_registered_domain_formula(
    public_context,
) -> None:
    result = _freeze(public_context)
    roles = (
        (
            "repository_binding",
            result.repository_binding.to_document(),
            "binding_id",
        ),
        (
            "dependency_record",
            result.dependency_records[0].to_document(),
            "record_id",
        ),
        (
            "dependency_attestation",
            result.dependency_attestations[0].to_document(),
            "attestation_id",
        ),
        ("closure", result.to_document(), "closure_id"),
    )
    for role, document, identity_field in roles:
        payload = dict(document)
        identity = payload.pop(identity_field)
        expected = hashlib.sha256(
            closure.DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(payload)
        ).hexdigest()
        assert identity == expected
        assert identity != hashlib.sha256(
            role.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(payload)
        ).hexdigest()
    manifest_payload = public_context["manifest"].to_document()
    manifest_id = manifest_payload.pop("manifest_id")
    assert manifest_id == hashlib.sha256(
        closure.SOURCE_MANIFEST_DOMAIN_TAG.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(manifest_payload)
    ).hexdigest()


def test_fully_rehashed_caller_manifest_remains_opaque_and_cannot_unlock_source(
    public_context,
) -> None:
    original = public_context["manifest"]
    changed = closure.V075PortablePublicContextSourceManifestV2(
        (
            closure.V075PortablePublicContextSourceManifestEntryV2(
                "acfqp.phase3e_ids",
                "acfqp/phase3e_ids.py",
                _id("caller-rehashed-phase3e-source"),
                10_001,
            ),
            original.entries[1],
        )
    )
    assert changed.manifest_id != original.manifest_id
    result = (
        closure.freeze_v075_portable_public_context_evidence_closure_v2(
            repository_root=PROJECT_ROOT,
            source_manifest_bytes=changed.canonical_bytes,
            namespace_bytes=public_context["namespace"].canonical_bytes,
            observer_open_authorization_bytes=(
                public_context["authorization"].canonical_bytes
            ),
            private_reveal_verification_attestation_bytes=(
                public_context["reveal"].canonical_bytes
            ),
        )
    )
    document = result.to_document()
    assert document["source_manifest_id"] == changed.manifest_id
    assert document["source_manifest_authority_status"] == (
        closure.SOURCE_MANIFEST_AUTHORITY_STATUS
    )
    assert document["source_authority_complete"] is False
    assert document["ipc_source_snapshot_attestation_status"] == (
        "NOT_SUPPLIED"
    )
    with pytest.raises(
        closure.V075PortablePublicContextProductionV2NotReady,
        match="SOURCE_SNAPSHOT_ATTESTATION_NOT_SUPPLIED",
    ):
        closure.open_v075_production_from_public_context_closure_v2(
            closure=result
        )

    forged = loads_canonical_json(result.canonical_bytes)
    forged["source_authority_complete"] = True
    forged["ipc_source_snapshot_attestation_status"] = "VERIFIED"
    forged["ipc_source_snapshot_attestation"] = {
        "kind": "VERIFIED",
        "attestation_id": _id("caller-minted-snapshot-attestation"),
    }
    closure_payload = dict(forged)
    closure_payload.pop("closure_id")
    forged["closure_id"] = hashlib.sha256(
        closure.DOMAIN_TAGS["closure"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(closure_payload)
    ).hexdigest()
    with pytest.raises(
        closure.V075PortablePublicContextV2InvariantViolation
    ):
        closure.verify_v075_portable_public_context_evidence_closure_bytes_v2(
            repository_root=PROJECT_ROOT,
            raw=canonical_json_bytes(forged),
        )


def test_constructor_is_explicit_bytes_only_and_has_no_private_channels(
    public_context,
) -> None:
    parameters = inspect.signature(
        closure
        .resolve_v075_portable_public_context_raw_dependencies_v2
    ).parameters
    assert tuple(parameters) == (
        "repository_root",
        "source_manifest_bytes",
        "namespace_bytes",
        "observer_open_authorization_bytes",
        "private_reveal_verification_attestation_bytes",
    )
    assert {
        "multiround_result",
        "portable_bundle",
        "private_key",
        "private_salt",
        "private_environment",
        "target_law",
        "target_tape",
        "kernel",
        "observer",
    }.isdisjoint(parameters)
    result = _freeze(public_context)
    forbidden = {
        "private_key",
        "private_salt",
        "private_environment",
        "secret_salt",
        "secret_laws",
        "target_law",
        "target_tape",
        "random_tape",
        "kernel",
    }
    assert forbidden.isdisjoint(_all_keys(result.to_document()))
    assert (
        closure.MULTIROUND_RESULT_CONTAINS_CANONICAL_PUBLIC_CONTEXT_BYTES
        is False
    )
    assert closure.PRIVATE_INPUT_CHANNELS_ALLOWED is False
    assert closure.OBSERVER_OPEN_ALLOWED is False
    assert closure.FRESH_HELDOUT_ACCESS_ALLOWED is False
    assert closure.OFFICIAL_EXECUTION_ALLOWED is False
    assert closure.PRODUCTION_AUTHORIZING is False
    assert closure.SOURCE_AUTHORITY_COMPLETE is False
    assert closure.IPC_SOURCE_SNAPSHOT_ATTESTATION_STATUS == "NOT_SUPPLIED"
    with pytest.raises(
        closure.V075PortablePublicContextProductionV2NotReady,
        match="SOURCE_SNAPSHOT_ATTESTATION_NOT_SUPPLIED",
    ):
        closure.open_v075_production_from_public_context_closure_v2()
