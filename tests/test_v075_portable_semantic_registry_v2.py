from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_semantic_registry_v2 as semantics
from acfqp import v075_production_semantic_authority_registry_v2 as surface
from acfqp import v075_registered_occurrence_worker_v1 as worker


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-portable-semantic-registry-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


BUNDLE_ID = _id("portable-bundle")
BUNDLE_SHA256 = _id("portable-bundle-bytes")
SOURCE_MANIFEST_ID = _id("source-manifest")


def _record_document(
    *,
    role: str,
    artifact_document: dict,
    index: int = 0,
) -> dict:
    registry = semantics.freeze_v075_portable_semantic_registry_v2()
    declaration = registry.by_role[role]
    raw = canonical_json_bytes(artifact_document)
    if declaration.record_identity_field is None:
        semantic_id = semantics._hash_raw_domain(  # noqa: SLF001
            declaration.semantic_hash_domain_tag,
            raw,
        )
    else:
        semantic_id = artifact_document[declaration.record_identity_field]
    payload = {
        "schema": "acfqp.v075_portable_evidence_artifact_record.v2",
        "schema_version": "2.0.0",
        "profile_key": portable.PROFILE_KEY,
        "index": index,
        "role": role,
        "artifact_schema": declaration.artifact_schema,
        "artifact_domain_tag": declaration.record_domain_tag,
        "semantic_artifact_id": semantic_id,
        "dependency_record_ids": [],
        "canonical_artifact_bytes_hex": raw.hex(),
        "raw_bytes_complete": True,
        "private_material_serialized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "record_id": semantics._hash_domain(  # noqa: SLF001
            declaration.record_domain_tag,
            payload,
        ),
    }


def _occurrence_record() -> dict:
    occurrence = backend.V075BatchNativeOccurrenceIdentityV1(
        backend._OCCURRENCE_IDENTITY_ISSUER,  # noqa: SLF001
        _id("namespace"),
        _id("context"),
        worker.V075WorkerArmV1.NO_PRIOR,
        7,
        _id("threshold"),
        _id("cap"),
        None,
    )
    return _record_document(
        role="OCCURRENCE_IDENTITY",
        artifact_document=occurrence.to_document(),
    )


def _root_semantic_authority_record(*, role: str) -> dict:
    binding = control.freeze_v075_controlled_batch_semantic_authority_v2(
        role=(
            control.V075ControlledBatchSemanticAuthorityRoleV2
            .INITIAL_SCHEDULE_ROW_INTENT
        ),
        schema=(
            control.V075ControlledBatchSemanticAuthoritySchemaV2
            .INITIAL_SCHEDULE_ROW_INTENT
        ),
        semantic_artifact_id=_id("root-semantic-artifact"),
        semantic_verification_id=_id("root-semantic-verification"),
        stage=control.V075ControlledBatchStageV2.ROOT_DISCOVERY,
        round_index=0,
        support_freeze_id=None,
    )
    return _record_document(
        role=role,
        artifact_document=binding.to_document(),
    )


def _signed_batch_outcome_record(*, bad_reward_sum: bool = False) -> dict:
    identity_payload = {
        "schema": "acfqp.v075_batch_outcome_aggregate.v2",
        "schema_version": "2.0.0",
        "next_ranks": [1, 2, 3],
        "failure": False,
        "terminal": False,
        "spawn_cell": 4,
        "spawn_rank": 1,
        "realized_row_reward": {"numerator": 3, "denominator": 2},
    }
    document = {
        **identity_payload,
        "outcome_id": semantics._hash_domain(  # noqa: SLF001
            "acfqp:v075-batch-outcome-aggregate:v2",
            identity_payload,
        ),
        "count": 4,
        "reward_sum": (
            {"numerator": 5, "denominator": 1}
            if bad_reward_sum
            else {"numerator": 6, "denominator": 1}
        ),
    }
    return _record_document(
        role="SIGNED_BATCH_OUTCOME",
        artifact_document=document,
    )


def _rehash_registry(document: dict) -> bytes:
    document["registry_id"] = semantics._hash(  # noqa: SLF001
        "registry",
        {
            key: value
            for key, value in document.items()
            if key not in {"declarations", "registry_id"}
        },
    )
    return canonical_json_bytes(document)


def test_independent_registry_covers_all_67_roles_and_stays_incomplete() -> None:
    registry = semantics.freeze_v075_portable_semantic_registry_v2()
    replayed = semantics.verify_v075_portable_semantic_registry_bytes_v2(
        registry.canonical_bytes
    )
    static_registry = (
        surface.freeze_v075_production_semantic_authority_registry_v2()
    )
    assert replayed == registry
    assert len(registry.declarations) == 67
    assert {item.role for item in registry.declarations} == set(
        portable.ROLE_SCHEMA_REGISTRY
    )
    assert {
        item.role: item.artifact_schema for item in registry.declarations
    } == dict(portable.ROLE_SCHEMA_REGISTRY)
    assert registry.static_surface_registry_id == static_registry.registry_id
    assert surface.ARTIFACT_SEMANTIC_ATTESTATION_ALLOWED is False
    assert registry.to_document()["complete_role_count"] == 2
    assert registry.to_document()["incomplete_role_count"] == 65
    assert (
        registry.to_document()["semantic_registry_replay_complete"] is False
    )
    assert {
        item.role
        for item in registry.declarations
        if item.to_document()["semantic_replay_status"] == "COMPLETE"
    } == {"OCCURRENCE_IDENTITY", "SIGNED_BATCH_OUTCOME"}


@pytest.mark.parametrize("attack", ["delete-role", "change-verifier"])
def test_registry_rejects_deleted_role_or_changed_verifier(attack: str) -> None:
    registry = semantics.freeze_v075_portable_semantic_registry_v2()
    document = deepcopy(registry.to_document())
    if attack == "delete-role":
        removed = document["declarations"].pop()
        document["role_order"].pop()
        document["declaration_ids"].pop()
        document["role_count"] -= 1
        document["incomplete_role_count"] -= 1
        assert removed["role"] not in document["role_order"]
    else:
        declaration = document["declarations"][0]
        declaration["semantic_verifier_authority"] = (
            "attacker:foreign-verifier"
        )
        declaration["declaration_id"] = semantics._hash(  # noqa: SLF001
            "declaration",
            {
                key: value
                for key, value in declaration.items()
                if key != "declaration_id"
            },
        )
        document["declaration_ids"][0] = declaration["declaration_id"]
    with pytest.raises(
        semantics.V075PortableSemanticRegistryV2InvariantViolation,
        match="differs from independent declarations",
    ):
        semantics.verify_v075_portable_semantic_registry_bytes_v2(
            _rehash_registry(document)
        )


def test_record_attestation_replays_shape_ids_and_binds_context() -> None:
    record = _occurrence_record()
    attestation = (
        semantics.attest_v075_portable_evidence_record_document_v2(
            record_document=record,
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        )
    )
    replayed = (
        semantics.verify_v075_portable_record_semantic_attestation_bytes_v2(
            attestation_bytes=attestation.canonical_bytes,
            record_document=record,
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        )
    )
    document = replayed.to_document()
    assert replayed == attestation
    assert document["role"] == "OCCURRENCE_IDENTITY"
    assert document["canonical_shape_recomputed"] is True
    assert document["record_content_id_recomputed"] is True
    assert document["semantic_content_id_recomputed"] is True
    assert document["embedded_content_id_replay_status"] == "RECOMPUTED"
    assert document["semantic_replay_status"] == "COMPLETE"
    assert document["independent_semantic_replay_complete"] is True
    assert document["producer_typed_object_reconstructed"] is False
    assert (
        document["source_manifest_reference_status"]
        == "OPAQUE_CONTENT_ID_BOUND_UNVERIFIED_BY_THIS_MODULE"
    )
    assert (
        document["source_manifest_semantically_verified_by_this_module"]
        is False
    )
    assert (
        document[
            "portable_bundle_membership_verified_by_this_attestation"
        ]
        is False
    )

    for changed in (
        {"portable_bundle_id": _id("other-bundle")},
        {"portable_bundle_sha256": _id("other-bundle-bytes")},
        {"source_manifest_id": _id("other-source-manifest")},
    ):
        arguments = {
            "portable_bundle_id": BUNDLE_ID,
            "portable_bundle_sha256": BUNDLE_SHA256,
            "source_manifest_id": SOURCE_MANIFEST_ID,
            **changed,
        }
        with pytest.raises(
            semantics.V075PortableSemanticRegistryV2InvariantViolation,
            match="stale, transplanted",
        ):
            (
                semantics
                .verify_v075_portable_record_semantic_attestation_bytes_v2(
                    attestation_bytes=attestation.canonical_bytes,
                    record_document=record,
                    **arguments,
                )
            )


def test_cached_semantic_id_edit_is_rejected_after_wrapper_rehash() -> None:
    record = _occurrence_record()
    artifact = json_document = deepcopy(
        portable._strict_json_document(  # noqa: SLF001
            bytes.fromhex(record["canonical_artifact_bytes_hex"]),
            label="test occurrence",
        )
    )
    artifact["context_id"] = _id("mutated-context")
    forged = _record_document(
        role="OCCURRENCE_IDENTITY",
        artifact_document=json_document,
    )
    # Keep the stale cached semantic ID while fully rehashing the wrapper.
    assert forged["semantic_artifact_id"] == artifact["occurrence_id"]
    with pytest.raises(
        semantics.V075PortableSemanticRegistryV2InvariantViolation,
        match="cached semantic content ID changed",
    ):
        semantics.attest_v075_portable_evidence_record_document_v2(
            record_document=forged,
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        )


def test_same_schema_controlled_role_transplant_is_rejected() -> None:
    valid = _root_semantic_authority_record(
        role="CONTROLLED_ROOT_SEMANTIC_AUTHORITY"
    )
    assert (
        semantics.attest_v075_portable_evidence_record_document_v2(
            record_document=valid,
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        ).role
        == "CONTROLLED_ROOT_SEMANTIC_AUTHORITY"
    )
    transplanted = _root_semantic_authority_record(
        role="CONTROLLED_CHILD_SEMANTIC_AUTHORITY"
    )
    with pytest.raises(
        semantics.V075PortableSemanticRegistryV2InvariantViolation,
        match="differs from embedded semantic authority",
    ):
        semantics.attest_v075_portable_evidence_record_document_v2(
            record_document=transplanted,
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        )


def test_self_contained_outcome_semantics_reconcile_exact_rationals() -> None:
    valid = _signed_batch_outcome_record()
    attestation = (
        semantics.attest_v075_portable_evidence_record_document_v2(
            record_document=valid,
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        )
    )
    assert attestation.semantic_replay_status is (
        semantics.V075PortableSemanticReplayStatusV2.COMPLETE
    )
    assert (
        attestation.to_document()["embedded_content_id_replay_status"]
        == "RECOMPUTED"
    )
    with pytest.raises(
        semantics.V075PortableSemanticRegistryV2InvariantViolation,
        match="self-contained semantics changed",
    ):
        semantics.attest_v075_portable_evidence_record_document_v2(
            record_document=_signed_batch_outcome_record(
                bad_reward_sum=True
            ),
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        )


def test_complete_claim_is_rejected_even_after_attestation_rehash() -> None:
    record = _occurrence_record()
    attestation = (
        semantics.attest_v075_portable_evidence_record_document_v2(
            record_document=record,
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        )
    )
    forged = deepcopy(attestation.to_document())
    forged["semantic_replay_status"] = "COMPLETE"
    forged["independent_semantic_replay_complete"] = True
    forged["semantic_registry_replay_complete"] = True
    forged["attestation_id"] = semantics._hash(  # noqa: SLF001
        "attestation",
        {
            key: value
            for key, value in forged.items()
            if key != "attestation_id"
        },
    )
    with pytest.raises(
        semantics.V075PortableSemanticRegistryV2InvariantViolation,
        match="attempts to claim completion",
    ):
        semantics.verify_v075_portable_record_semantic_attestation_bytes_v2(
            attestation_bytes=canonical_json_bytes(forged),
            record_document=record,
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        )

    attestation_set = semantics.V075PortableSemanticAttestationSetV2(
        semantics._ATTESTATION_SET_ISSUER,  # noqa: SLF001
        attestation.registry_id,
        attestation.static_surface_registry_id,
        BUNDLE_ID,
        BUNDLE_SHA256,
        SOURCE_MANIFEST_ID,
        (attestation,),
    )
    assert (
        attestation_set.to_document()[
            "portable_bundle_membership_verified_by_aggregate"
        ]
        is True
    )
    forged_set = deepcopy(attestation_set.to_document())
    forged_set["aggregate_semantic_replay_complete"] = True
    forged_set["semantic_registry_replay_complete"] = True
    forged_set["complete_record_count"] = 1
    forged_set["attestation_set_id"] = semantics._hash(  # noqa: SLF001
        "attestation_set",
        {
            key: value
            for key, value in forged_set.items()
            if key not in {"attestations", "attestation_set_id"}
        },
    )
    with pytest.raises(
        semantics.V075PortableSemanticRegistryV2InvariantViolation,
        match="claims false completion",
    ):
        semantics.verify_v075_portable_semantic_attestation_set_bytes_v2(
            attestation_set_bytes=canonical_json_bytes(forged_set),
            bundle_bytes=b"{}",
            source_manifest_id=SOURCE_MANIFEST_ID,
        )


def test_incomplete_role_cannot_be_upgraded_after_complete_rehash() -> None:
    registry = semantics.freeze_v075_portable_semantic_registry_v2()
    forged_registry = deepcopy(registry.to_document())
    declaration = next(
        item
        for item in forged_registry["declarations"]
        if item["role"] == "CONTROLLED_ROOT_SEMANTIC_AUTHORITY"
    )
    declaration["semantic_replay_status"] = "COMPLETE"
    declaration["independent_role_semantics_complete"] = True
    declaration["typed_object_reconstruction_required"] = False
    declaration["semantic_verifier_authority"] = (
        f"{semantics.PROFILE_KEY}:ROLE_DISPATCH:"
        "CONTROLLED_ROOT_SEMANTIC_AUTHORITY:"
        "SELF_CONTAINED_SEMANTIC_REPLAY"
    )
    declaration["declaration_id"] = semantics._hash(  # noqa: SLF001
        "declaration",
        {
            key: value
            for key, value in declaration.items()
            if key != "declaration_id"
        },
    )
    declaration_index = forged_registry["role_order"].index(
        "CONTROLLED_ROOT_SEMANTIC_AUTHORITY"
    )
    forged_registry["declaration_ids"][declaration_index] = (
        declaration["declaration_id"]
    )
    forged_registry["complete_role_count"] += 1
    forged_registry["incomplete_role_count"] -= 1
    with pytest.raises(
        semantics.V075PortableSemanticRegistryV2InvariantViolation,
        match="differs from independent declarations",
    ):
        semantics.verify_v075_portable_semantic_registry_bytes_v2(
            _rehash_registry(forged_registry)
        )

    record = _root_semantic_authority_record(
        role="CONTROLLED_ROOT_SEMANTIC_AUTHORITY"
    )
    attestation = (
        semantics.attest_v075_portable_evidence_record_document_v2(
            record_document=record,
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        )
    )
    assert attestation.semantic_replay_status is (
        semantics.V075PortableSemanticReplayStatusV2.INCOMPLETE
    )
    forged_attestation = deepcopy(attestation.to_document())
    forged_attestation["semantic_replay_status"] = "COMPLETE"
    forged_attestation["independent_semantic_replay_complete"] = True
    forged_attestation["incomplete_reason"] = {
        "kind": "NOT_APPLICABLE",
        "reason": "ATTACKER_CLAIMED_SELF_CONTAINED_REPLAY",
    }
    forged_attestation["semantic_verifier_authority"] = (
        f"{semantics.PROFILE_KEY}:ROLE_DISPATCH:"
        "CONTROLLED_ROOT_SEMANTIC_AUTHORITY:"
        "SELF_CONTAINED_SEMANTIC_REPLAY"
    )
    forged_attestation["attestation_id"] = semantics._hash(  # noqa: SLF001
        "attestation",
        {
            key: value
            for key, value in forged_attestation.items()
            if key != "attestation_id"
        },
    )
    with pytest.raises(
        semantics.V075PortableSemanticRegistryV2InvariantViolation,
        match="stale, transplanted, or caller-authored",
    ):
        semantics.verify_v075_portable_record_semantic_attestation_bytes_v2(
            attestation_bytes=canonical_json_bytes(forged_attestation),
            record_document=record,
            portable_bundle_id=BUNDLE_ID,
            portable_bundle_sha256=BUNDLE_SHA256,
            source_manifest_id=SOURCE_MANIFEST_ID,
        )


def test_production_and_heldout_locks_remain_closed() -> None:
    assert semantics.OFFICIAL_EXECUTION_ALLOWED is False
    assert semantics.PRODUCTION_AUTHORIZING is False
    assert semantics.FRESH_HELDOUT_ACCESS_ALLOWED is False
    assert semantics.SEMANTIC_REGISTRY_REPLAY_COMPLETE is False
    with pytest.raises(
        semantics.V075PortableSemanticRegistryProductionV2NotReady,
        match="dependency-aware typed-object semantic replay",
    ):
        semantics.open_v075_production_portable_semantic_registry_v2()
