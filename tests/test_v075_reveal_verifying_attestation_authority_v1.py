from __future__ import annotations

import hashlib
import inspect
import json

import pytest

from acfqp import v075_preopen_target_authorization_v1 as preopen
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_remote_main_anchor_verifier_v1 as remote
from acfqp import v075_reveal_verifying_attestation_authority_v1 as issuer
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-reveal-issuer-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _registry(
    marker: str = "",
) -> public.V075TrustedSignerRegistryV1:
    observer_key = make_public_key("OBSERVER_EVIDENCE")
    if marker:
        observer_key = public.V075RSAPublicVerificationKeyV1(
            "OBSERVER_EVIDENCE",
            observer_key.modulus + 2,
        )
    return public.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        observer_key,
    )


def _environment(
    marker: bytes = b"environment-one",
) -> private_env.V075PrivateGeneratedEnvironmentV1:
    return private_env.generate_v075_private_environment_v1(
        profile=(
            private_env
            .freeze_v075_private_environment_generation_profile_v1()
        ),
        secret_generation_seed=hashlib.sha256(marker).digest(),
    )


def _salt(marker: bytes = b"salt-one") -> bytes:
    return hashlib.sha256(marker).digest()


def _commitment(
    environment: private_env.V075PrivateGeneratedEnvironmentV1,
    salt: bytes,
) -> public.V075OpaqueEnvironmentCommitmentV1:
    return (
        private_env
        .seal_v075_generated_private_environment_commitment_v1(
            generated_environment=environment,
            secret_salt=salt,
        )
    )


def _anchor(
    *,
    commitment: public.V075OpaqueEnvironmentCommitmentV1,
    registry: public.V075TrustedSignerRegistryV1,
    marker: str = "main",
) -> remote.V075RemoteMainAnchorAttestationV1:
    return remote.V075RemoteMainAnchorAttestationV1(
        remote._ISSUER,  # type: ignore[attr-defined]
        hashlib.sha1(marker.encode("utf-8")).hexdigest(),
        hashlib.sha1((marker + "-manifest").encode("utf-8")).hexdigest(),
        (
            hashlib.sha1(
                (marker + "-final").encode("utf-8")
            ).hexdigest(),
        ),
        hashlib.sha1((marker + "-manifest-blob").encode("utf-8")).hexdigest(),
        hashlib.sha1((marker + "-final-blob").encode("utf-8")).hexdigest(),
        _id(marker + "-manifest"),
        _id(marker + "-final"),
        commitment.family.generation_id,
        commitment.commitment_id,
        _id(marker + "-observer-profile"),
        registry,
        _id(marker + "-component-registry"),
        _id(marker + "-authority-registry"),
    )


class _CountingSigner:
    def __init__(self, *, key_role: str = "OBSERVER_EVIDENCE") -> None:
        self.key_role = key_role
        self.messages: list[bytes] = []

    def public_verification_key_v1(
        self,
    ) -> public.V075RSAPublicVerificationKeyV1:
        return make_public_key(self.key_role)

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        self.messages.append(message)
        return sign_test_message(message, key_role=self.key_role)


def _fixture():
    environment = _environment()
    salt = _salt()
    commitment = _commitment(environment, salt)
    registry = _registry()
    anchor = _anchor(commitment=commitment, registry=registry)
    signer = _CountingSigner()
    return environment, salt, commitment, registry, anchor, signer


def _all_keys(value) -> tuple[str, ...]:
    if isinstance(value, dict):
        return tuple(value) + tuple(
            key
            for child in value.values()
            for key in _all_keys(child)
        )
    if isinstance(value, list):
        return tuple(
            key for child in value for key in _all_keys(child)
        )
    return ()


def test_actual_match_is_recomputed_before_one_signature_and_is_law_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment, salt, commitment, registry, anchor, signer = _fixture()
    original = public.verify_opaque_environment_reveal_v1
    calls = []

    def audited_verify(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(
        issuer.public,
        "verify_opaque_environment_reveal_v1",
        audited_verify,
    )
    attestation = issuer.issue_v075_reveal_verified_private_attestation_v1(
        anchor=anchor,
        commitment=commitment,
        generated_environment=environment,
        secret_salt=salt,
        signer_registry=registry,
        observer_signer=signer,
    )
    assert len(calls) == 1
    assert len(signer.messages) == 1
    reveal = original(
        commitment=commitment,
        secret_salt=salt,
        secret_laws=environment.secret_laws_for_commitment(),
    )
    assert reveal.matched is True
    assert (
        attestation.private_verification_external_id
        == reveal.verification_id
    )
    assert signer.messages[0] == (
        preopen.private_reveal_attestation_signing_bytes_v1(
            anchor=anchor,
            private_verification_external_id=reveal.verification_id,
        )
    )
    replayed = (
        issuer.load_and_verify_v075_reveal_verified_attestation_v1(
            raw=attestation.canonical_bytes,
            anchor=anchor,
            commitment=commitment,
            signer_registry=registry,
        )
    )
    assert replayed == attestation
    document = attestation.to_document()
    assert document["verification_result"] == "MATCH"
    assert document["private_reveal_semantically_verified"] is True
    assert document["observer_open_performed"] is False
    assert document["observer_session_created"] is False
    assert issuer.TARGET_EXECUTION_OPENED is False
    keys = set(_all_keys(document))
    assert {
        "secret_salt",
        "secret_laws",
        "private_environment",
        "rank_probabilities",
        "signing_key",
        "private_key",
        "random_tape",
    }.isdisjoint(keys)
    encoded = json.dumps(document, sort_keys=True)
    assert salt.hex() not in encoded
    assert repr(environment.secret_laws_for_commitment()) not in encoded


def test_mismatch_fails_before_signing() -> None:
    environment, _salt_value, commitment, registry, anchor, signer = (
        _fixture()
    )
    with pytest.raises(
        issuer.V075RevealVerifyingAttestationInvariantViolation,
        match="did not match",
    ):
        issuer.issue_v075_reveal_verified_private_attestation_v1(
            anchor=anchor,
            commitment=commitment,
            generated_environment=environment,
            secret_salt=_salt(b"wrong-salt"),
            signer_registry=registry,
            observer_signer=signer,
        )
    assert signer.messages == []


@pytest.mark.parametrize(
    "attack",
    ("foreign_commitment", "foreign_anchor", "foreign_registry", "wrong_key"),
)
def test_foreign_identity_graphs_fail_before_signing(attack: str) -> None:
    environment, salt, commitment, registry, anchor, signer = _fixture()
    if attack == "foreign_commitment":
        commitment = _commitment(environment, _salt(b"foreign"))
    elif attack == "foreign_anchor":
        foreign_commitment = _commitment(
            environment,
            _salt(b"foreign-anchor"),
        )
        anchor = _anchor(
            commitment=foreign_commitment,
            registry=registry,
            marker="foreign",
        )
    elif attack == "foreign_registry":
        registry = _registry("foreign")
    else:
        signer = _CountingSigner(key_role="CAMPAIGN_AUTHORITY")
    with pytest.raises(
        issuer.V075RevealVerifyingAttestationInvariantViolation,
        match="foreign|registry-bound|identity graph",
    ):
        issuer.issue_v075_reveal_verified_private_attestation_v1(
            anchor=anchor,
            commitment=commitment,
            generated_environment=environment,
            secret_salt=salt,
            signer_registry=registry,
            observer_signer=signer,
        )
    assert signer.messages == []


def test_caller_cannot_claim_match_or_choose_verification_identity() -> None:
    parameters = inspect.signature(
        issuer.issue_v075_reveal_verified_private_attestation_v1
    ).parameters
    assert "verification_result" not in parameters
    assert "matched" not in parameters
    assert "private_verification_external_id" not in parameters
    assert "observer_signature_hex" not in parameters
    environment, salt, commitment, registry, anchor, signer = _fixture()
    with pytest.raises(TypeError):
        issuer.issue_v075_reveal_verified_private_attestation_v1(
            anchor=anchor,
            commitment=commitment,
            generated_environment=environment,
            secret_salt=salt,
            signer_registry=registry,
            observer_signer=signer,
            verification_result="MATCH",  # type: ignore[call-arg]
        )
    assert signer.messages == []


def test_replay_or_transplant_to_foreign_roles_fails_closed() -> None:
    environment, salt, commitment, registry, anchor, signer = _fixture()
    attestation = issuer.issue_v075_reveal_verified_private_attestation_v1(
        anchor=anchor,
        commitment=commitment,
        generated_environment=environment,
        secret_salt=salt,
        signer_registry=registry,
        observer_signer=signer,
    )
    foreign_commitment = _commitment(environment, _salt(b"foreign"))
    with pytest.raises(
        issuer.V075RevealVerifyingAttestationInvariantViolation,
        match="foreign|stale",
    ):
        issuer.load_and_verify_v075_reveal_verified_attestation_v1(
            raw=attestation.canonical_bytes,
            anchor=anchor,
            commitment=foreign_commitment,
            signer_registry=registry,
        )
    foreign_anchor = _anchor(
        commitment=commitment,
        registry=registry,
        marker="foreign",
    )
    with pytest.raises(
        issuer.V075RevealVerifyingAttestationInvariantViolation,
        match="replay failed",
    ):
        issuer.load_and_verify_v075_reveal_verified_attestation_v1(
            raw=attestation.canonical_bytes,
            anchor=foreign_anchor,
            commitment=commitment,
            signer_registry=registry,
        )


def test_module_has_no_target_open_or_observer_dependency() -> None:
    source = inspect.getsource(issuer)
    assert "v075_private_observer_boundary_v1" not in source
    assert "open_private_observer_v1" not in source
    assert "target_execution_opened = True" not in source.lower()
    assert issuer.TARGET_EXECUTION_OPENED is False
