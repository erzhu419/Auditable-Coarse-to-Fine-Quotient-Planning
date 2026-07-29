from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect
from pathlib import Path
import re

import pytest

from acfqp import v075_fresh_campaign_authority_v1 as construction
from acfqp import v075_public_campaign_authority_v1 as authority
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _laws(
    first_rank: int = 1,
) -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    return (
        ((first_rank, Fraction(1)),),
        ((1, Fraction(1)),),
        ((1, Fraction(1)),),
    )


def _registry() -> authority.V075TrustedSignerRegistryV1:
    return authority.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )


def _claim(
    registry: authority.V075TrustedSignerRegistryV1,
    role: authority.V075ExternalAuthorityRoleV1,
    marker: str,
) -> authority.V075SignedExternalAuthorityClaimV1:
    external_id = _id(marker)
    message = authority.external_authority_claim_signing_bytes_v1(
        signer_registry=registry,
        role=role,
        external_id=external_id,
    )
    return authority.V075SignedExternalAuthorityClaimV1(
        registry,
        role,
        external_id,
        sign_test_message(message),
    )


def _commitment(
    marker: str = "one",
) -> authority.V075OpaqueEnvironmentCommitmentV1:
    family = authority.freeze_v075_public_family_generation_v1()
    return authority.seal_opaque_environment_commitment_v1(
        family=family,
        secret_salt=hashlib.sha256(
            ("private-unit-test-salt-" + marker).encode("utf-8")
        ).digest(),
        secret_laws=_laws(),
    )


def test_public_family_serializes_structure_but_no_environment_law() -> None:
    family = authority.freeze_v075_public_family_generation_v1()
    document = family.to_document()
    encoded = repr(document)
    assert len(family.replicate_contexts) == 3
    assert all(context.horizon == 2 for context in family.replicate_contexts)
    assert all(
        context.root_ranks == (1, 1, 2, 0, 0, 0, 0)
        for context in family.replicate_contexts
    )
    assert document["production_law_serialized"] is False
    assert "rank_probabilities" not in encoded
    assert "environment_manifest" not in encoded
    assert "law_ids" not in encoded


def test_salted_commitment_is_opaque_and_salt_sensitive() -> None:
    family = authority.freeze_v075_public_family_generation_v1()
    first = _commitment("first")
    repeated = _commitment("first")
    changed_salt = _commitment("second")
    changed_law = authority.seal_opaque_environment_commitment_v1(
        family=family,
        secret_salt=hashlib.sha256(
            b"private-unit-test-salt-first"
        ).digest(),
        secret_laws=_laws(first_rank=2),
    )
    assert first == repeated
    assert first.commitment_id == repeated.commitment_id
    assert first.commitment_digest != changed_salt.commitment_digest
    assert first.commitment_digest != changed_law.commitment_digest
    document = first.to_document()
    assert document["secret_salt_serialized"] is False
    assert document["secret_environment_serialized"] is False
    assert document["production_law_serialized"] is False
    assert "private-unit-test-salt" not in repr(document)
    assert "probability" not in repr(document)
    with pytest.raises(
        authority.V075PublicCampaignAuthorityInvariantViolation
    ):
        authority.seal_opaque_environment_commitment_v1(
            family=family,
            secret_salt=b"too-short",
            secret_laws=_laws(),
        )
    with pytest.raises(
        authority.V075PublicCampaignAuthorityInvariantViolation
    ):
        authority.seal_opaque_environment_commitment_v1(
            family=family,
            secret_salt=b"\x00" * 32,
            secret_laws=_laws(),
        )


def test_private_reveal_verification_does_not_serialize_secret() -> None:
    commitment = _commitment("reveal")
    salt = hashlib.sha256(
        b"private-unit-test-salt-reveal"
    ).digest()
    matched = authority.verify_opaque_environment_reveal_v1(
        commitment=commitment,
        secret_salt=salt,
        secret_laws=_laws(),
    )
    mismatched = authority.verify_opaque_environment_reveal_v1(
        commitment=commitment,
        secret_salt=hashlib.sha256(b"different-salt").digest(),
        secret_laws=_laws(),
    )
    assert matched.matched is True
    assert mismatched.matched is False
    assert matched.to_document()["verification_result"] == "MATCH"
    assert matched.to_document()["secret_salt_serialized"] is False
    assert matched.to_document()["secret_environment_serialized"] is False
    assert "private-unit-test-salt" not in repr(matched.to_document())
    assert "probability" not in repr(matched.to_document())


def test_namespace_requires_complete_typed_authority_graph() -> None:
    family = authority.freeze_v075_public_family_generation_v1()
    role = authority.V075ExternalAuthorityRoleV1
    registry = _registry()
    anchor = _claim(registry, role.REMOTE_MAIN_ANCHOR, "anchor")
    prereg = _claim(registry, role.FINAL_PREREGISTRATION, "prereg")
    observer = _claim(registry, role.OBSERVER_PROFILE, "observer")
    namespace = authority.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=_commitment(),
        signer_registry=registry,
        claimed_final_preregistration_registry_id=registry.registry_id,
        remote_main_anchor=anchor,
        final_preregistration=prereg,
        observer_profile=observer,
    )
    document = namespace.to_document()
    registry_document = registry.to_document()
    assert "final_preregistration_external_id" not in registry_document
    assert registry_document[
        "registry_precedes_final_preregistration"
    ] is True
    assert registry_document[
        "final_preregistration_must_bind_registry_id"
    ] is True
    assert prereg.signer_registry.registry_id == registry.registry_id
    assert document["production_law_serialized"] is False
    assert document["secret_salt_serialized"] is False
    assert document["target_execution_allowed"] is False
    assert document["environment_commitment_id"] == (
        namespace.environment_commitment.commitment_id
    )
    assert document["external_authorities_signature_verified"] is True
    with pytest.raises(
        authority.V075PublicCampaignAuthorityInvariantViolation
    ):
        replace(namespace, observer_profile=anchor)
    with pytest.raises(
        authority.V075PublicCampaignAuthorityInvariantViolation
    ):
        replace(
            namespace,
            claimed_final_preregistration_registry_id=_id(
                "wrong-registry"
            ),
        )


def test_known_v072_identity_cannot_be_typed_as_v075_authority() -> None:
    old_v072_id = (
        "1c123268407d609ea853452c0145d21153e87251dfe8de61802264ccd6203474"
    )
    with pytest.raises(
        authority.V075PublicCampaignAuthorityInvariantViolation
    ):
        authority.external_authority_claim_signing_bytes_v1(
            signer_registry=_registry(),
            role=authority.V075ExternalAuthorityRoleV1.REMOTE_MAIN_ANCHOR,
            external_id=old_v072_id,
        )


def test_frozen_failure_record_denylist_is_complete_and_committed() -> None:
    # This is an evaluation-only source audit.  Production public modules use
    # only the frozen tuple/count/root and never read historical target JSON.
    repository = Path(__file__).resolve().parents[1]
    extracted_by_attempt: list[set[str]] = []
    for relative in (
        "specs/V072_ANCHORED_ATTEMPT_1_FAILURE.json",
        "specs/V072_ANCHORED_ATTEMPT_2_FAILURE.json",
    ):
        extracted_by_attempt.append(
            set(
                re.findall(
                    r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])",
                    (repository / relative).read_text(encoding="utf-8"),
                )
            )
        )
    extracted = set.union(*extracted_by_attempt)
    frozen = authority.FROZEN_V072_FAILURE_RECORD_CONTENT_IDS
    assert len(extracted) == len(frozen) == (
        authority.FROZEN_V072_FAILURE_RECORD_CONTENT_ID_COUNT
    ) == 58
    assert tuple(map(len, extracted_by_attempt)) == (
        authority.FROZEN_V072_ATTEMPT_1_CONTENT_ID_COUNT,
        authority.FROZEN_V072_ATTEMPT_2_CONTENT_ID_COUNT,
    ) == (8, 52)
    assert len(
        extracted_by_attempt[0] & extracted_by_attempt[1]
    ) == authority.FROZEN_V072_ATTEMPT_CONTENT_ID_OVERLAP_COUNT == 2
    assert tuple(sorted(extracted)) == frozen

    def merkle(values: set[str] | tuple[str, ...]) -> str:
        level = [
            hashlib.sha256(
                b"acfqp:v075-v072-failure-record-id-leaf:v1"
                + b"\x00"
                + bytes.fromhex(value)
            ).digest()
            for value in sorted(values)
        ]
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [
                hashlib.sha256(
                    b"acfqp:v075-v072-failure-record-id-node:v1"
                    + b"\x00"
                    + level[index]
                    + level[index + 1]
                ).digest()
                for index in range(0, len(level), 2)
            ]
        return level[0].hex()

    assert merkle(frozen) == (
        authority.FROZEN_V072_FAILURE_RECORD_CONTENT_ID_MERKLE_ROOT
    )
    assert merkle(extracted_by_attempt[0]) == (
        authority.FROZEN_V072_ATTEMPT_1_CONTENT_ID_MERKLE_ROOT
    )
    assert merkle(extracted_by_attempt[1]) == (
        authority.FROZEN_V072_ATTEMPT_2_CONTENT_ID_MERKLE_ROOT
    )
    assert set(frozen) <= authority.FORBIDDEN_HISTORICAL_TARGET_IDS


def test_every_frozen_failure_id_is_rejected_for_every_external_target_role() -> None:
    registry = _registry()
    for historical_id in (
        authority.FROZEN_V072_FAILURE_RECORD_CONTENT_IDS
    ):
        for role in authority.V075ExternalAuthorityRoleV1:
            with pytest.raises(
                authority.V075PublicCampaignAuthorityInvariantViolation
            ):
                authority.external_authority_claim_signing_bytes_v1(
                    signer_registry=registry,
                    role=role,
                    external_id=historical_id,
                )


def test_arbitrary_fresh_cid_without_private_signature_cannot_mint_claim() -> None:
    registry = _registry()
    role = authority.V075ExternalAuthorityRoleV1.REMOTE_MAIN_ANCHOR
    with pytest.raises(
        authority.V075PublicCampaignAuthorityInvariantViolation
    ):
        authority.V075SignedExternalAuthorityClaimV1(
            registry,
            role,
            _id("attacker-chosen-fresh-id"),
            "00" * 256,
        )


def test_campaign_and_observer_roles_require_distinct_key_material() -> None:
    campaign_key = make_public_key("CAMPAIGN_AUTHORITY")
    with pytest.raises(
        authority.V075PublicCampaignAuthorityInvariantViolation
    ):
        authority.V075TrustedSignerRegistryV1(
            campaign_key,
            authority.V075RSAPublicVerificationKeyV1(
                "OBSERVER_EVIDENCE",
                campaign_key.modulus,
                campaign_key.public_exponent,
            ),
        )


def test_attacker_owned_self_signed_registry_is_never_an_open_authority() -> None:
    # This test key is deliberately attacker-controlled.  Its signatures prove
    # only registry-relative consistency, never that this registry was frozen
    # by the independent final-preregistration/Git verifier.
    family = authority.freeze_v075_public_family_generation_v1()
    role = authority.V075ExternalAuthorityRoleV1
    registry = _registry()
    namespace = authority.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=_commitment(),
        signer_registry=registry,
        claimed_final_preregistration_registry_id=registry.registry_id,
        remote_main_anchor=_claim(
            registry,
            role.REMOTE_MAIN_ANCHOR,
            "attacker-anchor",
        ),
        final_preregistration=_claim(
            registry,
            role.FINAL_PREREGISTRATION,
            "prereg",
        ),
        observer_profile=_claim(
            registry,
            role.OBSERVER_PROFILE,
            "attacker-observer",
        ),
    )
    document = namespace.to_document()
    assert document["external_authorities_signature_verified"] is True
    assert document["signature_scope"] == (
        "REGISTRY_RELATIVE_PROVENANCE_ONLY"
    )
    assert document["caller_registry_is_trust_root"] is False
    assert (
        document["independent_final_preregistration_verification"]
        is False
    )
    assert document["tracked_git_registry_recomputation_verified"] is False
    assert document["observer_open_authority"] is False
    assert document["target_execution_allowed"] is False
    assert authority.PRODUCTION_OBSERVER_OPEN_ALLOWED is False
    assert (
        authority.INDEPENDENT_FINAL_AUTHORITY_VERIFIER_IMPLEMENTED
        is False
    )


def test_public_authority_source_contains_no_construction_law_dependency() -> None:
    source = inspect.getsource(authority)
    assert "v075_fresh_campaign_authority_v1" not in source
    assert "_HIDDEN_LAW_SPECS" not in source
    assert "freeze_v075_environment_manifest_v1" not in source
    assert "991, 1_000" not in source
    assert "197, 200" not in source
    assert "393, 400" not in source
    assert "V072_ANCHORED_ATTEMPT_1_FAILURE.json" not in source
    assert "V072_ANCHORED_ATTEMPT_2_FAILURE.json" not in source
    assert "read_text(" not in source


def test_exposed_environment_is_permanently_construction_only() -> None:
    assert construction.AUTHORITY_ROLE == "CONSTRUCTION_FIXTURE_ONLY"
    assert construction.PRODUCTION_HELDOUT_EVIDENCE_ALLOWED is False
    environment = construction.freeze_v075_environment_manifest_v1()
    preregistration = construction.freeze_v075_preregistration_draft_v1()
    namespace = construction.derive_v075_target_tape_namespace_identity_v1(
        remote_main_anchor_id=_id("construction-anchor"),
        final_preregistration_id=_id("construction-prereg"),
        observer_profile_id=_id("construction-observer"),
    )
    for document in (
        environment.to_document(),
        preregistration.to_document(),
        namespace.to_document(),
    ):
        assert document["construction_fixture_only"] is True
        assert document["production_heldout_evidence_allowed"] is False
