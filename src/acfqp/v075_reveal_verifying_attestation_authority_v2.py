"""Private reveal-verifying issuer for the exact V0-075 V2 chain.

The issuer recomputes the opaque environment commitment before asking the
registry-bound observer-evidence signer to sign one role-separated V2 MATCH
statement.  It accepts only the exact V2 remote-main anchor.  No V1 adapter,
caller-selected verification identity, target-open operation, secret law, or
private key is serialized in the returned attestation.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_remote_main_anchor_verifier_v2 as remote


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.44.0"
PROFILE_KEY = "v075_reveal_verifying_attestation_authority_v2"
TARGET_EXECUTION_OPENED = False


class V075RevealVerifyingAttestationV2InvariantViolation(ValueError):
    """A private reveal or exact V2 public identity graph failed closed."""


def _fail(message: str) -> None:
    raise V075RevealVerifyingAttestationV2InvariantViolation(message)


@runtime_checkable
class V075RevealEvidenceSignerProtocolV2(Protocol):
    """Minimal in-memory signer interface; implementations are not artifacts."""

    def public_verification_key_v1(
        self,
    ) -> public.V075RSAPublicVerificationKeyV1:
        """Return the observer-evidence public key."""

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        """Sign one canonical V2 observer-evidence message."""


def _validate_public_identity_graph(
    *,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
    commitment: public.V075OpaqueEnvironmentCommitmentV1,
    generated_environment: private_env.V075PrivateGeneratedEnvironmentV1,
    signer_registry: public.V075TrustedSignerRegistryV1,
    observer_signer: V075RevealEvidenceSignerProtocolV2,
) -> None:
    if type(anchor) is not remote.V075RemoteMainAnchorAttestationV2:
        _fail("issuer requires the exact V2 remote-main anchor type")
    if type(commitment) is not public.V075OpaqueEnvironmentCommitmentV1:
        _fail("issuer requires the exact opaque commitment type")
    if (
        type(generated_environment)
        is not private_env.V075PrivateGeneratedEnvironmentV1
    ):
        _fail("issuer requires one exact generated private environment")
    if type(signer_registry) is not public.V075TrustedSignerRegistryV1:
        _fail("issuer requires the exact trusted signer registry type")
    if not isinstance(observer_signer, V075RevealEvidenceSignerProtocolV2):
        _fail("observer signer lacks the required private V2 API")
    if (
        commitment.commitment_id
        != anchor.opaque_environment_commitment_id
        or commitment.family.generation_id != anchor.family_generation_id
        or generated_environment.family != commitment.family
        or signer_registry != anchor.signer_registry
    ):
        _fail("V2 reveal identity graph is foreign, stale, or transplanted")
    try:
        signer_key = observer_signer.public_verification_key_v1()
    except Exception as error:
        raise V075RevealVerifyingAttestationV2InvariantViolation(
            "observer signer public-key lookup failed"
        ) from error
    if (
        type(signer_key) is not public.V075RSAPublicVerificationKeyV1
        or signer_key != signer_registry.observer_evidence_key
    ):
        _fail("observer signer is not the V2 registry-bound evidence signer")


def issue_v075_reveal_verified_private_attestation_v2(
    *,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
    commitment: public.V075OpaqueEnvironmentCommitmentV1,
    generated_environment: private_env.V075PrivateGeneratedEnvironmentV1,
    secret_salt: bytes,
    signer_registry: public.V075TrustedSignerRegistryV1,
    observer_signer: V075RevealEvidenceSignerProtocolV2,
) -> preopen.V075PrivateRevealAttestationV2:
    """Recompute reveal identity, then and only then sign exact V2 MATCH."""

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
            secret_laws=generated_environment.secret_laws_for_commitment(),
        )
    except Exception as error:
        raise V075RevealVerifyingAttestationV2InvariantViolation(
            "authoritative opaque reveal verification failed"
        ) from error
    if (
        type(reveal) is not public.V075EnvironmentRevealVerificationV1
        or reveal.commitment != commitment
        or reveal.matched is not True
        or reveal.to_document()["verification_result"] != "MATCH"
    ):
        _fail("opaque environment reveal did not match; V2 signing forbidden")

    verification_id = reveal.verification_id
    signing_bytes = preopen.private_reveal_attestation_signing_bytes_v2(
        anchor=anchor,
        private_verification_external_id=verification_id,
    )
    try:
        signature_hex = observer_signer.sign_observer_evidence_v1(
            signing_bytes
        )
        signer_key_after = observer_signer.public_verification_key_v1()
    except Exception as error:
        raise V075RevealVerifyingAttestationV2InvariantViolation(
            "V2 observer-evidence signing failed"
        ) from error
    if (
        type(signer_key_after) is not public.V075RSAPublicVerificationKeyV1
        or signer_key_after != signer_registry.observer_evidence_key
    ):
        _fail("observer signer key changed during V2 reveal issuance")
    try:
        attestation = (
            preopen
            .verify_and_bind_v075_signed_private_reveal_attestation_v2(
                anchor=anchor,
                private_verification_external_id=verification_id,
                observer_signature_hex=signature_hex,
            )
        )
    except preopen.V075PreopenAuthorizationV2InvariantViolation as error:
        raise V075RevealVerifyingAttestationV2InvariantViolation(
            "issued V2 reveal signature failed public binding"
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
        or document["target_accessed"] is not False
    ):
        _fail("law-free V2 attestation failed post-issuance replay")
    return attestation


def load_and_verify_v075_reveal_verified_attestation_v2(
    *,
    raw: bytes,
    anchor: remote.V075RemoteMainAnchorAttestationV2,
    commitment: public.V075OpaqueEnvironmentCommitmentV1,
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> preopen.V075PrivateRevealAttestationV2:
    """Replay a law-free V2 attestation against its exact public roles."""

    if (
        type(anchor) is not remote.V075RemoteMainAnchorAttestationV2
        or type(commitment) is not public.V075OpaqueEnvironmentCommitmentV1
        or type(signer_registry) is not public.V075TrustedSignerRegistryV1
        or commitment.commitment_id
        != anchor.opaque_environment_commitment_id
        or commitment.family.generation_id != anchor.family_generation_id
        or signer_registry != anchor.signer_registry
    ):
        _fail("replayed V2 reveal graph is foreign, stale, or cross-role")
    try:
        attestation = (
            preopen.load_and_verify_v075_private_reveal_attestation_v2(
                raw=raw,
                anchor=anchor,
            )
        )
    except preopen.V075PreopenAuthorizationV2InvariantViolation as error:
        raise V075RevealVerifyingAttestationV2InvariantViolation(
            "law-free V2 reveal attestation replay failed"
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
        or document["target_accessed"] is not False
    ):
        _fail("replayed V2 reveal was transplanted or did not attest MATCH")
    return attestation


__all__ = [
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_OPENED",
    "V075RevealEvidenceSignerProtocolV2",
    "V075RevealVerifyingAttestationV2InvariantViolation",
    "issue_v075_reveal_verified_private_attestation_v2",
    "load_and_verify_v075_reveal_verified_attestation_v2",
]
