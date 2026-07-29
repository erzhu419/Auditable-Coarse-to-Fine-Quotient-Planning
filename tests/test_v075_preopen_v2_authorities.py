from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_preopen_target_authorization_v1 as preopen_v1
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_production_campaign_profile_v2 as campaign_profile
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_remote_main_anchor_verifier_v1 as remote_v1
from acfqp import v075_remote_main_anchor_verifier_v2 as remote
from acfqp import v075_reveal_verifying_attestation_authority_v2 as issuer
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-preopen-v2-authorities-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _registry() -> public.V075TrustedSignerRegistryV1:
    return public.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )


def _environment(
    marker: bytes = b"environment",
) -> private_env.V075PrivateGeneratedEnvironmentV1:
    return private_env.generate_v075_private_environment_v1(
        profile=(
            private_env
            .freeze_v075_private_environment_generation_profile_v1()
        ),
        secret_generation_seed=hashlib.sha256(marker).digest(),
    )


def _salt(marker: bytes = b"salt") -> bytes:
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
) -> remote.V075RemoteMainAnchorAttestationV2:
    prefix = hashlib.sha1(marker.encode("utf-8")).hexdigest()
    return remote.V075RemoteMainAnchorAttestationV2(
        remote._ANCHOR_ISSUER,  # type: ignore[attr-defined]
        prefix,
        hashlib.sha1((marker + "-tree").encode("utf-8")).hexdigest(),
        (
            hashlib.sha1(
                (marker + "-parent").encode("utf-8")
            ).hexdigest(),
        ),
        hashlib.sha1(
            (marker + "-manifest-blob").encode("utf-8")
        ).hexdigest(),
        hashlib.sha1(
            (marker + "-final-blob").encode("utf-8")
        ).hexdigest(),
        _id(marker + "-manifest"),
        _id(marker + "-final"),
        _id(marker + "-component-registry"),
        _id(marker + "-semantic-registry-binding"),
        _id(marker + "-semantic-artifact-replay"),
        _id(marker + "-workload"),
        campaign_profile.freeze_v075_production_campaign_profile_v2().profile_id,
        commitment.family.generation_id,
        commitment.commitment_id,
        registry,
    )


def _v1_anchor(
    *,
    commitment: public.V075OpaqueEnvironmentCommitmentV1,
    registry: public.V075TrustedSignerRegistryV1,
) -> remote_v1.V075RemoteMainAnchorAttestationV1:
    return remote_v1.V075RemoteMainAnchorAttestationV1(
        remote_v1._ISSUER,  # type: ignore[attr-defined]
        "1" * 40,
        "2" * 40,
        ("3" * 40,),
        "4" * 40,
        "5" * 40,
        _id("v1-manifest"),
        _id("v1-final"),
        commitment.family.generation_id,
        commitment.commitment_id,
        _id("v1-observer-profile"),
        registry,
        _id("v1-component-registry"),
        _id("v1-authority-registry"),
    )


class _CountingSigner:
    def __init__(self, key_role: str = "OBSERVER_EVIDENCE") -> None:
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


def _issue():
    environment, salt, commitment, registry, anchor, signer = _fixture()
    attestation = issuer.issue_v075_reveal_verified_private_attestation_v2(
        anchor=anchor,
        commitment=commitment,
        generated_environment=environment,
        secret_salt=salt,
        signer_registry=registry,
        observer_signer=signer,
    )
    return (
        environment,
        salt,
        commitment,
        registry,
        anchor,
        signer,
        attestation,
    )


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


def test_exact_v2_reveal_is_recomputed_signed_once_and_law_free() -> None:
    (
        environment,
        salt,
        commitment,
        registry,
        anchor,
        signer,
        attestation,
    ) = _issue()
    reveal = public.verify_opaque_environment_reveal_v1(
        commitment=commitment,
        secret_salt=salt,
        secret_laws=environment.secret_laws_for_commitment(),
    )
    assert reveal.matched is True
    assert len(signer.messages) == 1
    assert signer.messages[0] == (
        preopen.private_reveal_attestation_signing_bytes_v2(
            anchor=anchor,
            private_verification_external_id=reveal.verification_id,
        )
    )
    replayed = (
        issuer.load_and_verify_v075_reveal_verified_attestation_v2(
            raw=attestation.canonical_bytes,
            anchor=anchor,
            commitment=commitment,
            signer_registry=registry,
        )
    )
    assert replayed == attestation
    document = attestation.to_document()
    assert document["schema"].endswith(".v2")
    assert document["verification_result"] == "MATCH"
    assert document["observer_open_performed"] is False
    assert document["observer_session_created"] is False
    assert document["target_accessed"] is False
    assert issuer.TARGET_EXECUTION_OPENED is False
    forbidden_keys = {
        "secret_salt",
        "secret_laws",
        "private_environment",
        "rank_probabilities",
        "signing_key",
        "private_key",
        "random_tape",
        "target_bytes",
    }
    assert forbidden_keys.isdisjoint(_all_keys(document))
    encoded = json.dumps(document, sort_keys=True)
    assert salt.hex() not in encoded
    assert repr(environment.secret_laws_for_commitment()) not in encoded


def test_wrong_reveal_fails_before_signing() -> None:
    environment, _correct, commitment, registry, anchor, signer = _fixture()
    with pytest.raises(
        issuer.V075RevealVerifyingAttestationV2InvariantViolation,
        match="did not match",
    ):
        issuer.issue_v075_reveal_verified_private_attestation_v2(
            anchor=anchor,
            commitment=commitment,
            generated_environment=environment,
            secret_salt=_salt(b"wrong"),
            signer_registry=registry,
            observer_signer=signer,
        )
    assert signer.messages == []


@pytest.mark.parametrize(
    "attack",
    ("anchor", "commitment", "registry", "signer"),
)
def test_wrong_anchor_commitment_registry_or_signer_fails_closed(
    attack: str,
) -> None:
    environment, salt, commitment, registry, anchor, signer = _fixture()
    if attack == "anchor":
        foreign_commitment = _commitment(
            environment,
            _salt(b"foreign-anchor"),
        )
        anchor = _anchor(
            commitment=foreign_commitment,
            registry=registry,
            marker="foreign",
        )
    elif attack == "commitment":
        commitment = _commitment(environment, _salt(b"foreign"))
    elif attack == "registry":
        registry = public.V075TrustedSignerRegistryV1(
            make_public_key("CAMPAIGN_AUTHORITY"),
            public.V075RSAPublicVerificationKeyV1(
                "OBSERVER_EVIDENCE",
                make_public_key("OBSERVER_EVIDENCE").modulus + 2,
            ),
        )
    else:
        signer = _CountingSigner("CAMPAIGN_AUTHORITY")
    with pytest.raises(
        issuer.V075RevealVerifyingAttestationV2InvariantViolation,
        match="foreign|stale|registry-bound|identity graph",
    ):
        issuer.issue_v075_reveal_verified_private_attestation_v2(
            anchor=anchor,
            commitment=commitment,
            generated_environment=environment,
            secret_salt=salt,
            signer_registry=registry,
            observer_signer=signer,
        )
    assert signer.messages == []


def test_v1_v2_cross_role_reuse_is_rejected() -> None:
    (
        _environment_value,
        _salt_value,
        commitment,
        registry,
        anchor,
        _signer,
        v2_attestation,
    ) = _issue()
    v1_anchor = _v1_anchor(commitment=commitment, registry=registry)
    external_id = _id("v1-external-verification")
    v1_message = preopen_v1.private_reveal_attestation_signing_bytes_v1(
        anchor=v1_anchor,
        private_verification_external_id=external_id,
    )
    v1_attestation = (
        preopen_v1
        .verify_and_bind_v075_signed_private_reveal_attestation_v1(
            anchor=v1_anchor,
            private_verification_external_id=external_id,
            observer_signature_hex=sign_test_message(
                v1_message,
                key_role="OBSERVER_EVIDENCE",
            ),
        )
    )
    with pytest.raises(
        preopen.V075PreopenAuthorizationV2InvariantViolation,
        match="exact V2|field set|role",
    ):
        preopen.private_reveal_attestation_signing_bytes_v2(
            anchor=v1_anchor,  # type: ignore[arg-type]
            private_verification_external_id=external_id,
        )
    with pytest.raises(
        preopen.V075PreopenAuthorizationV2InvariantViolation,
        match="field set",
    ):
        preopen.load_and_verify_v075_private_reveal_attestation_v2(
            raw=v1_attestation.canonical_bytes,
            anchor=anchor,
        )
    with pytest.raises(
        preopen_v1.V075PreopenAuthorizationInvariantViolation,
        match="field set",
    ):
        preopen_v1.load_and_verify_v075_private_reveal_attestation_v1(
            raw=v2_attestation.canonical_bytes,
            anchor=v1_anchor,
        )
    assert not isinstance(
        v2_attestation,
        preopen_v1.V075PrivateRevealAttestationV1,
    )


def test_tampered_v2_reveal_and_foreign_anchor_are_rejected() -> None:
    (
        _environment_value,
        _salt_value,
        commitment,
        registry,
        anchor,
        _signer,
        attestation,
    ) = _issue()
    tampered = json.loads(attestation.canonical_bytes)
    tampered["private_verification_external_id"] = _id("tampered")
    with pytest.raises(
        preopen.V075PreopenAuthorizationV2InvariantViolation,
        match="transplanted|signature|identity",
    ):
        preopen.load_and_verify_v075_private_reveal_attestation_v2(
            raw=canonical_json_bytes(tampered),
            anchor=anchor,
        )
    foreign_anchor = _anchor(
        commitment=commitment,
        registry=registry,
        marker="foreign",
    )
    with pytest.raises(
        issuer.V075RevealVerifyingAttestationV2InvariantViolation,
        match="replay failed",
    ):
        issuer.load_and_verify_v075_reveal_verified_attestation_v2(
            raw=attestation.canonical_bytes,
            anchor=foreign_anchor,
            commitment=commitment,
            signer_registry=registry,
        )


def test_synthetic_authorization_is_v2_only_and_never_opens_target() -> None:
    (
        environment,
        salt,
        commitment,
        registry,
        anchor,
        _signer,
        attestation,
    ) = _issue()
    closure = preopen.V075TrackedPreopenBlobClosureV2(
        preopen._BLOB_CLOSURE_ISSUER,  # type: ignore[attr-defined]
        anchor,
        _id("manifest-bytes"),
        _id("final-bytes"),
    )
    authorization = preopen.V075ObserverOpenAuthorizationV2(
        preopen._AUTHORIZATION_ISSUER,  # type: ignore[attr-defined]
        anchor,
        closure,
        registry,
        commitment,
        attestation,
    )
    document = authorization.to_document()
    assert document["schema"].endswith(".v2")
    assert document["authorization_ready"] is True
    assert document["legacy_v1_projection_issued"] is False
    assert document["observer_open_performed"] is False
    assert document["observer_session_created"] is False
    assert document["target_law_read"] is False
    assert document["target_tape_read"] is False
    assert document["target_accessed"] is False
    assert document["sentinel_created"] is False
    encoded = json.dumps(document, sort_keys=True)
    assert salt.hex() not in encoded
    assert repr(environment.secret_laws_for_commitment()) not in encoded
    with pytest.raises(
        preopen.V075PreopenAuthorizationV2InvariantViolation,
        match="graph",
    ):
        preopen.V075ObserverOpenAuthorizationV2(
            object(),
            anchor,
            closure,
            registry,
            commitment,
            attestation,
        )


def test_stale_origin_main_replay_fails_before_blob_or_target_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        _environment_value,
        _salt_value,
        commitment,
        registry,
        anchor,
        _signer,
    ) = _fixture()
    stale = _anchor(
        commitment=commitment,
        registry=registry,
        marker="stale",
    )
    monkeypatch.setattr(
        preopen.remote,
        "verify_v075_remote_main_anchor_independently_v2",
        lambda _root: stale,
    )
    monkeypatch.setattr(
        preopen,
        "_git_blob",
        lambda *_args, **_kwargs: pytest.fail(
            "blob access must not follow a stale anchor"
        ),
    )
    with pytest.raises(
        preopen.V075PreopenAuthorizationV2InvariantViolation,
        match="stale|changed",
    ):
        preopen._verify_tracked_blob_closure_v2(  # type: ignore[attr-defined]
            repository_root=PROJECT_ROOT,
            anchor=anchor,
        )


def test_current_signed_v2_not_ready_declaration_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        _environment_value,
        _salt_value,
        _commitment_value,
        _registry_value,
        anchor,
        _signer,
        attestation,
    ) = _issue()
    monkeypatch.setattr(
        preopen.remote,
        "verify_v075_remote_main_anchor_independently_v2",
        lambda _root: anchor,
    )
    monkeypatch.setattr(
        preopen,
        "_verify_tracked_blob_closure_v2",
        lambda **_kwargs: pytest.fail(
            "NOT_READY anchor must stop before blob closure"
        ),
    )
    readiness = preopen.assess_v075_preopen_target_authorization_v2(
        repository_root=PROJECT_ROOT,
        private_reveal_attestation_bytes=attestation.canonical_bytes,
    )
    assert readiness.ready is False
    assert readiness.blockers == (
        "PREOPEN_V2_SIGNED_DECLARATION_NOT_READY",
    )
    document = readiness.to_document()
    assert document["registered_target_execution_allowed"] is False
    assert document["official_execution_allowed"] is False
    assert document["observer_open_performed"] is False
    assert document["target_accessed"] is False
    with pytest.raises(preopen.V075PreopenAuthorizationV2NotReady):
        preopen.require_ready_v075_preopen_target_authorization_v2(
            readiness
        )


def test_synthetic_ready_v2_chain_authorizes_without_opening_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        _environment_value,
        _salt_value,
        commitment,
        registry,
        anchor,
        _signer,
        attestation,
    ) = _issue()
    closure = preopen.V075TrackedPreopenBlobClosureV2(
        preopen._BLOB_CLOSURE_ISSUER,  # type: ignore[attr-defined]
        anchor,
        _id("synthetic-ready-manifest-bytes"),
        _id("synthetic-ready-final-bytes"),
    )
    original_to_document = (
        remote.V075RemoteMainAnchorAttestationV2.to_document
    )

    def ready_document(
        self: remote.V075RemoteMainAnchorAttestationV2,
    ) -> dict:
        document = original_to_document(self)
        document["preopen_v2_migration_status"] = "READY"
        return document

    monkeypatch.setattr(
        remote.V075RemoteMainAnchorAttestationV2,
        "to_document",
        ready_document,
    )
    monkeypatch.setattr(
        preopen.remote,
        "verify_v075_remote_main_anchor_independently_v2",
        lambda _root: anchor,
    )
    monkeypatch.setattr(
        preopen,
        "_verify_tracked_blob_closure_v2",
        lambda **_kwargs: (closure, commitment),
    )
    readiness = preopen.assess_v075_preopen_target_authorization_v2(
        repository_root=PROJECT_ROOT,
        private_reveal_attestation_bytes=attestation.canonical_bytes,
    )
    authorization = (
        preopen.require_ready_v075_preopen_target_authorization_v2(
            readiness
        )
    )
    assert readiness.ready is True
    assert authorization.anchor is anchor
    assert authorization.signer_registry == registry
    document = authorization.to_document()
    assert document["authorization_ready"] is True
    assert document["legacy_v1_projection_issued"] is False
    assert document["observer_open_performed"] is False
    assert document["observer_session_created"] is False
    assert document["target_law_read"] is False
    assert document["target_tape_read"] is False
    assert document["target_accessed"] is False
    assert document["sentinel_created"] is False


def test_public_assessor_and_issuer_do_not_accept_target_or_claim_inputs() -> None:
    assessor_parameters = inspect.signature(
        preopen.assess_v075_preopen_target_authorization_v2
    ).parameters
    assert tuple(assessor_parameters) == (
        "repository_root",
        "private_reveal_attestation_bytes",
    )
    issue_parameters = inspect.signature(
        issuer.issue_v075_reveal_verified_private_attestation_v2
    ).parameters
    assert {
        "verification_result",
        "matched",
        "private_verification_external_id",
        "observer_signature_hex",
        "target_law",
        "target_tape",
        "kernel",
        "observer",
    }.isdisjoint(issue_parameters)
    source = Path(preopen.__file__).read_text(encoding="utf-8")
    assert "v075_preopen_target_authorization_v1" not in source
    assert "v075_remote_main_anchor_verifier_v1" not in source
    assert "v075_private_observer_boundary" not in source
    assert "open_private_observer" not in source
    assert preopen.TARGET_EXECUTION_OPENED is False
