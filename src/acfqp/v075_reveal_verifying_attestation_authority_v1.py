"""Private reveal-verifying issuer for the V0-075 pre-open attestation.

This is the only production-facing adapter that may ask the observer-evidence
signer to sign a private-reveal MATCH statement.  It first recomputes the
opaque commitment with the authoritative public reveal verifier and derives
the verification identity from that result.  Callers cannot supply either the
result or its identity.

The returned object is the existing law-free
``V075PrivateRevealAttestationV1`` consumed by the pre-open authorization
chain.  No observer is opened here, and no salt, law, generated environment,
or signing key is retained or serialized.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from acfqp import v075_preopen_target_authorization_v1 as preopen
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_remote_main_anchor_verifier_v1 as remote


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_reveal_verifying_attestation_authority_v1"

# This module has no target-open operation.  The constant is intentionally
# machine-auditable by the final pre-open gate.
TARGET_EXECUTION_OPENED = False


class V075RevealVerifyingAttestationInvariantViolation(ValueError):
    """A private reveal or its public identity graph failed closed."""


def _fail(message: str) -> None:
    raise V075RevealVerifyingAttestationInvariantViolation(message)


@runtime_checkable
class V075RevealEvidenceSignerProtocol(Protocol):
    """Minimal in-memory signer interface; implementations are not artifacts."""

    def public_verification_key_v1(
        self,
    ) -> public.V075RSAPublicVerificationKeyV1:
        """Return the observer-evidence public key."""

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        """Sign one canonical observer-evidence message."""


def _validate_public_identity_graph(
    *,
    anchor: remote.V075RemoteMainAnchorAttestationV1,
    commitment: public.V075OpaqueEnvironmentCommitmentV1,
    generated_environment: (
        private_env.V075PrivateGeneratedEnvironmentV1
    ),
    signer_registry: public.V075TrustedSignerRegistryV1,
    observer_signer: V075RevealEvidenceSignerProtocol,
) -> None:
    if type(anchor) is not remote.V075RemoteMainAnchorAttestationV1:
        _fail("issuer requires the exact remote-main anchor type")
    if type(commitment) is not public.V075OpaqueEnvironmentCommitmentV1:
        _fail("issuer requires the exact opaque commitment type")
    if (
        type(generated_environment)
        is not private_env.V075PrivateGeneratedEnvironmentV1
    ):
        _fail("issuer requires one exact generated private environment")
    if type(signer_registry) is not public.V075TrustedSignerRegistryV1:
        _fail("issuer requires the exact trusted signer registry type")
    if not isinstance(observer_signer, V075RevealEvidenceSignerProtocol):
        _fail("observer signer does not implement the required private API")
    if (
        commitment.commitment_id
        != anchor.opaque_environment_commitment_id
        or commitment.family.generation_id != anchor.family_generation_id
        or generated_environment.family != commitment.family
        or signer_registry != anchor.signer_registry
    ):
        _fail("reveal identity graph is foreign, stale, or transplanted")
    try:
        signer_key = observer_signer.public_verification_key_v1()
    except Exception as error:
        raise V075RevealVerifyingAttestationInvariantViolation(
            "observer signer public-key lookup failed"
        ) from error
    if (
        type(signer_key) is not public.V075RSAPublicVerificationKeyV1
        or signer_key != signer_registry.observer_evidence_key
    ):
        _fail("observer signer is not the registry-bound evidence signer")


def issue_v075_reveal_verified_private_attestation_v1(
    *,
    anchor: remote.V075RemoteMainAnchorAttestationV1,
    commitment: public.V075OpaqueEnvironmentCommitmentV1,
    generated_environment: (
        private_env.V075PrivateGeneratedEnvironmentV1
    ),
    secret_salt: bytes,
    signer_registry: public.V075TrustedSignerRegistryV1,
    observer_signer: V075RevealEvidenceSignerProtocol,
) -> preopen.V075PrivateRevealAttestationV1:
    """Verify the private reveal, derive its ID, then and only then sign MATCH."""

    _validate_public_identity_graph(
        anchor=anchor,
        commitment=commitment,
        generated_environment=generated_environment,
        signer_registry=signer_registry,
        observer_signer=observer_signer,
    )
    try:
        reveal = public.verify_opaque_environment_reveal_v1(
            commitment=commitment,
            secret_salt=secret_salt,
            secret_laws=(
                generated_environment.secret_laws_for_commitment()
            ),
        )
    except Exception as error:
        raise V075RevealVerifyingAttestationInvariantViolation(
            "authoritative opaque reveal verification failed"
        ) from error
    if (
        type(reveal) is not public.V075EnvironmentRevealVerificationV1
        or reveal.commitment != commitment
        or reveal.matched is not True
        or reveal.to_document()["verification_result"] != "MATCH"
    ):
        _fail("opaque environment reveal did not match; signing is forbidden")

    # The external verification ID is derived here.  There is deliberately no
    # caller parameter capable of claiming MATCH or choosing this identity.
    verification_id = reveal.verification_id
    signing_bytes = preopen.private_reveal_attestation_signing_bytes_v1(
        anchor=anchor,
        private_verification_external_id=verification_id,
    )
    try:
        signature_hex = observer_signer.sign_observer_evidence_v1(
            signing_bytes
        )
        signer_key_after = observer_signer.public_verification_key_v1()
    except Exception as error:
        raise V075RevealVerifyingAttestationInvariantViolation(
            "observer-evidence signing failed"
        ) from error
    if (
        type(signer_key_after) is not public.V075RSAPublicVerificationKeyV1
        or signer_key_after != signer_registry.observer_evidence_key
    ):
        _fail("observer signer key changed during reveal issuance")
    try:
        attestation = (
            preopen
            .verify_and_bind_v075_signed_private_reveal_attestation_v1(
                anchor=anchor,
                private_verification_external_id=verification_id,
                observer_signature_hex=signature_hex,
            )
        )
    except preopen.V075PreopenAuthorizationInvariantViolation as error:
        raise V075RevealVerifyingAttestationInvariantViolation(
            "issued reveal signature failed public binding"
        ) from error
    document = attestation.to_document()
    if (
        attestation.anchor != anchor
        or attestation.private_verification_external_id != verification_id
        or document["verification_result"] != "MATCH"
        or document["private_reveal_semantically_verified"] is not True
        or document["secret_salt_serialized"] is not False
        or document["private_environment_serialized"] is not False
        or document["transition_law_serialized"] is not False
        or document["random_tape_serialized"] is not False
        or document["observer_open_performed"] is not False
        or document["observer_session_created"] is not False
    ):
        _fail("law-free issued attestation failed post-issuance replay")
    return attestation


def load_and_verify_v075_reveal_verified_attestation_v1(
    *,
    raw: bytes,
    anchor: remote.V075RemoteMainAnchorAttestationV1,
    commitment: public.V075OpaqueEnvironmentCommitmentV1,
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> preopen.V075PrivateRevealAttestationV1:
    """Replay a law-free issued attestation against its exact public roles."""

    if (
        type(anchor) is not remote.V075RemoteMainAnchorAttestationV1
        or type(commitment) is not public.V075OpaqueEnvironmentCommitmentV1
        or type(signer_registry) is not public.V075TrustedSignerRegistryV1
        or commitment.commitment_id
        != anchor.opaque_environment_commitment_id
        or commitment.family.generation_id != anchor.family_generation_id
        or signer_registry != anchor.signer_registry
    ):
        _fail("replayed reveal identity graph is foreign or stale")
    try:
        attestation = (
            preopen.load_and_verify_v075_private_reveal_attestation_v1(
                raw=raw,
                anchor=anchor,
            )
        )
    except preopen.V075PreopenAuthorizationInvariantViolation as error:
        raise V075RevealVerifyingAttestationInvariantViolation(
            "law-free reveal attestation replay failed"
        ) from error
    document = attestation.to_document()
    if (
        document["opaque_environment_commitment_id"]
        != commitment.commitment_id
        or document["signer_registry_id"] != signer_registry.registry_id
        or document["observer_evidence_key_id"]
        != signer_registry.observer_evidence_key.key_id
        or document["verification_result"] != "MATCH"
        or document["private_reveal_semantically_verified"] is not True
        or document["observer_open_performed"] is not False
        or document["observer_session_created"] is not False
    ):
        _fail("replayed reveal was transplanted or did not attest MATCH")
    return attestation


__all__ = [
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_OPENED",
    "V075RevealEvidenceSignerProtocol",
    "V075RevealVerifyingAttestationInvariantViolation",
    "issue_v075_reveal_verified_private_attestation_v1",
    "load_and_verify_v075_reveal_verified_attestation_v1",
]
