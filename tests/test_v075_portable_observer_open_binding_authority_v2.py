from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import (
    v075_portable_observer_open_binding_authority_v2 as authority,
)
from acfqp import v075_portable_public_context_closure_v2 as context
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_remote_main_anchor_verifier_v2 as remote
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-portable-observer-open-binding-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _source_manifest() -> (
    context.V075PortablePublicContextSourceManifestV2
):
    return context.V075PortablePublicContextSourceManifestV2(
        (
            context.V075PortablePublicContextSourceManifestEntryV2(
                "acfqp.phase3e_ids",
                "acfqp/phase3e_ids.py",
                _id("phase3e-source"),
                10_001,
            ),
            context.V075PortablePublicContextSourceManifestEntryV2(
                "acfqp.v075_portable_occurrence_evidence_bundle_v2",
                "acfqp/v075_portable_occurrence_evidence_bundle_v2.py",
                _id("portable-source"),
                20_002,
            ),
            context.V075PortablePublicContextSourceManifestEntryV2(
                "acfqp.v075_private_observer_boundary_v2",
                "acfqp/v075_private_observer_boundary_v2.py",
                _id("observer-source"),
                30_003,
            ),
        )
    )


def _binding_document(namespace, authorization) -> dict:
    anchor = namespace.anchor
    payload = {
        "schema": "acfqp.v075_observer_open_authority_binding.v2",
        "schema_version": observer.SCHEMA_VERSION,
        "proposed_contract_version": observer.PROPOSED_CONTRACT_VERSION,
        "profile_key": observer.PROFILE_KEY,
        "observer_open_authorization_id": authorization.authorization_id,
        "private_reveal_attestation_id": (
            authorization.private_reveal_attestation.attestation_id
        ),
        "remote_main_anchor_id": anchor.anchor_id,
        "anchor_commit_id": anchor.commit_id,
        "anchor_tree_id": anchor.tree_id,
        "manifest_id": anchor.manifest_id,
        "final_preregistration_id": anchor.final_preregistration_id,
        "component_registry_id": anchor.component_registry_id,
        "semantic_registry_binding_id": (
            anchor.semantic_registry_binding_id
        ),
        "semantic_artifact_replay_id": (
            anchor.semantic_artifact_replay_id
        ),
        "workload_id": namespace.workload.workload_id,
        "runner_profile_id": namespace.runner_profile.profile_id,
        "family_generation_id": namespace.family.generation_id,
        "target_tape_namespace_id": namespace.target_tape_namespace_id,
        "opaque_environment_commitment_id": (
            namespace.environment_commitment.commitment_id
        ),
        "signer_registry_id": namespace.signer_registry.registry_id,
        "observer_evidence_key_id": (
            namespace.signer_registry.observer_evidence_key.key_id
        ),
        "authority_version": "V2",
        "namespace_version": "V2",
        "legacy_v1_authority_projection_issued": False,
        "legacy_v1_namespace_projection_issued": False,
        "independent_final_authority_verified": True,
        "observer_open_authorized": True,
        "private_material_serialized": False,
    }
    return {
        **payload,
        "binding_id": hashlib.sha256(
            observer.DOMAIN_TAGS["open_binding"].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _rehash_binding(document: dict) -> bytes:
    payload = dict(document)
    payload.pop("binding_id", None)
    document["binding_id"] = hashlib.sha256(
        observer.DOMAIN_TAGS["open_binding"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return canonical_json_bytes(document)


@pytest.fixture
def raw_b1(monkeypatch: pytest.MonkeyPatch):
    (
        _environment,
        _salt,
        namespace,
        authorization,
        _signer,
    ) = observer_fixture._fixture("portable-observer-open-binding-b1")
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
    closure = context.freeze_v075_portable_public_context_evidence_closure_v2(
        repository_root=PROJECT_ROOT,
        source_manifest_bytes=_source_manifest().canonical_bytes,
        namespace_bytes=namespace.canonical_bytes,
        observer_open_authorization_bytes=authorization.canonical_bytes,
        private_reveal_verification_attestation_bytes=(
            authorization.private_reveal_attestation.canonical_bytes
        ),
    )
    binding_bytes = canonical_json_bytes(
        _binding_document(namespace, authorization)
    )
    return {
        "namespace": namespace,
        "authorization": authorization,
        "closure": closure,
        "binding_bytes": binding_bytes,
    }


def _replay(raw_b1):
    return authority.replay_v075_portable_observer_open_binding_v2(
        repository_root=PROJECT_ROOT,
        public_context_closure_bytes=raw_b1["closure"].canonical_bytes,
        observer_open_binding_bytes=raw_b1["binding_bytes"],
    )


def test_honest_raw_b1_reconstructs_issuer_binding_and_keeps_locks_closed(
    raw_b1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("B1 touched one forbidden private channel")

    monkeypatch.setattr(observer, "open_private_observer_v2", forbidden)
    monkeypatch.setattr(observer, "_canonical_private_environment", forbidden)
    result = _replay(raw_b1)
    document = result.to_document()
    assert (
        type(result.observer_open_binding)
        is observer.V075ObserverOpenAuthorityBindingV2
    )
    assert result.observer_open_binding.to_document() == loads_canonical_json(
        raw_b1["binding_bytes"]
    )
    assert document["observer_open_binding_semantics_complete"] is True
    assert document["public_context_closure_raw_replayed"] is True
    assert document["authorization_signature_graph_replayed"] is True
    assert document["session_identity"]["kind"] == "NOT_APPLICABLE"
    assert document["occurrence_context_identity"]["kind"] == (
        "NOT_APPLICABLE"
    )
    for key in (
        "source_authority_complete",
        "code_provenance_complete",
        "m1_role_semantics_complete",
        "portable_semantic_registry_complete",
        "observer_opened",
        "private_input_channels_allowed",
        "fresh_heldout_accessed",
        "official_execution_allowed",
        "production_authorizing",
        "scientific_endpoint_credit_allowed",
        "plan_certificate",
        "infeasibility_certificate",
        "private_material_serialized",
    ):
        assert document[key] is False
    payload = dict(document)
    result_id = payload.pop("result_id")
    assert result_id == hashlib.sha256(
        authority.DOMAIN_TAGS["result"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


def test_binding_raw_parser_rejects_shape_duplicate_and_byte_cap_attacks(
    raw_b1,
) -> None:
    baseline = loads_canonical_json(raw_b1["binding_bytes"])
    attacks = []
    missing = dict(baseline)
    missing.pop("workload_id")
    attacks.append(canonical_json_bytes(missing))
    extra = dict(baseline)
    extra["unexpected"] = False
    attacks.append(canonical_json_bytes(extra))
    for field in ("observer_session_public_id", "context_id"):
        transplanted = dict(baseline)
        transplanted[field] = _id(f"foreign-{field}")
        attacks.append(_rehash_binding(transplanted))
    schema = baseline["schema"]
    attacks.append(
        (
            '{"schema":"'
            + schema
            + '",'
            + raw_b1["binding_bytes"].decode("utf-8")[1:]
        ).encode("utf-8")
    )
    attacks.append(
        b"x" * (observer.MAX_OBSERVER_OPEN_BINDING_BYTES + 1)
    )
    for attacked in attacks:
        with pytest.raises(
            authority.V075PortableObserverOpenBindingV2InvariantViolation
        ):
            authority.replay_v075_portable_observer_open_binding_v2(
                repository_root=PROJECT_ROOT,
                public_context_closure_bytes=(
                    raw_b1["closure"].canonical_bytes
                ),
                observer_open_binding_bytes=attacked,
            )


def test_namespace_key_and_fully_rehashed_binding_transplants_fail(
    raw_b1,
) -> None:
    baseline = loads_canonical_json(raw_b1["binding_bytes"])
    for field in (
        "target_tape_namespace_id",
        "observer_evidence_key_id",
        "observer_open_authorization_id",
        "private_reveal_attestation_id",
        "remote_main_anchor_id",
        "opaque_environment_commitment_id",
        "signer_registry_id",
    ):
        attacked = dict(baseline)
        attacked[field] = _id(f"foreign-{field}")
        with pytest.raises(
            authority.V075PortableObserverOpenBindingV2InvariantViolation
        ):
            authority.replay_v075_portable_observer_open_binding_v2(
                repository_root=PROJECT_ROOT,
                public_context_closure_bytes=(
                    raw_b1["closure"].canonical_bytes
                ),
                observer_open_binding_bytes=_rehash_binding(attacked),
            )

    (
        _environment,
        _salt,
        foreign_namespace,
        foreign_authorization,
        _signer,
    ) = observer_fixture._fixture("portable-observer-open-binding-foreign")
    foreign_bytes = canonical_json_bytes(
        _binding_document(foreign_namespace, foreign_authorization)
    )
    with pytest.raises(
        authority.V075PortableObserverOpenBindingV2InvariantViolation
    ):
        authority.replay_v075_portable_observer_open_binding_v2(
            repository_root=PROJECT_ROOT,
            public_context_closure_bytes=raw_b1["closure"].canonical_bytes,
            observer_open_binding_bytes=foreign_bytes,
        )


def test_invalid_reveal_signature_and_caller_typed_bypass_fail(
    raw_b1,
) -> None:
    records = {
        item.role: item for item in raw_b1["closure"].dependency_records
    }
    roles = tuple(context.V075PortablePublicContextDependencyRoleV2)
    reveal_document = loads_canonical_json(
        records[roles[2]].canonical_artifact_bytes
    )
    reveal_document["observer_signature_hex"] = "00"
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation
    ):
        observer.replay_v075_observer_open_authority_binding_bytes_v2(
            repository_root=PROJECT_ROOT,
            namespace_bytes=records[roles[0]].canonical_artifact_bytes,
            claimed_authorization_bytes=(
                records[roles[1]].canonical_artifact_bytes
            ),
            private_reveal_attestation_bytes=canonical_json_bytes(
                reveal_document
            ),
            observer_open_binding_bytes=raw_b1["binding_bytes"],
        )

    result = _replay(raw_b1)
    for closure_value, binding_value in (
        (raw_b1["closure"], raw_b1["binding_bytes"]),
        (
            raw_b1["closure"].canonical_bytes,
            result.observer_open_binding,
        ),
    ):
        with pytest.raises(
            authority.V075PortableObserverOpenBindingV2InvariantViolation
        ):
            authority.replay_v075_portable_observer_open_binding_v2(
                repository_root=PROJECT_ROOT,
                public_context_closure_bytes=closure_value,
                observer_open_binding_bytes=binding_value,
            )
    with pytest.raises(
        authority.V075PortableObserverOpenBindingProductionV2NotReady
    ):
        authority.open_v075_production_from_portable_observer_open_binding_v2()
    parameters = inspect.signature(
        observer.replay_v075_observer_open_authority_binding_bytes_v2
    ).parameters
    assert not {
        "private_salt",
        "private_environment",
        "observer_signer",
        "session_external_id",
    } & set(parameters)
