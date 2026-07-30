from __future__ import annotations

import inspect
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_observer_signed_private_replay_attestation_v2 as subject
from acfqp import v075_private_observer_boundary_v2 as observer
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


def _walk_items(value: Any):
    if type(value) is dict:
        for key, child in value.items():
            yield key, child
            yield from _walk_items(child)
    elif type(value) is list:
        for child in value:
            yield from _walk_items(child)


def _build(marker: str):
    (
        generated,
        salt,
        namespace,
        authorization,
        signer,
        session,
    ) = observer_fixture._open(marker)
    streams = observer_fixture._streams(namespace).streams[:2]
    occurrence_id = observer_fixture._id(marker + "-occurrence")
    session.observe_batch_v2(
        occurrence_id=occurrence_id,
        stream_identity=streams[0],
        accepted_draw_start=1,
        accepted_draw_count=5,
        accepted_draw_cap=5,
    )
    session.observe_batch_v2(
        occurrence_id=occurrence_id,
        stream_identity=streams[1],
        accepted_draw_start=1,
        accepted_draw_count=7,
        accepted_draw_cap=7,
    )
    closure = session.close_batch_v2()
    attestation = (
        subject.freeze_v075_observer_signed_private_replay_attestation_v2(
            authority=authorization,
            namespace=namespace,
            closure=closure,
            authority_binding=closure.authority_binding,
            used_stream_identities=streams,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
        )
    )
    return {
        "generated": generated,
        "salt": salt,
        "namespace": namespace,
        "authorization": authorization,
        "signer": signer,
        "streams": streams,
        "closure": closure,
        "attestation": attestation,
    }


@pytest.fixture(scope="module")
def honest():
    return _build("observer-signed-private-replay-honest")


@pytest.fixture(scope="module")
def foreign():
    return _build("observer-signed-private-replay-foreign")


def _rehash(document: dict[str, Any]) -> bytes:
    payload = {
        key: value
        for key, value in document.items()
        if key != "attestation_id"
    }
    document["attestation_id"] = subject._hash(  # noqa: SLF001
        "attestation",
        payload,
    )
    return canonical_json_bytes(document)


def _flip_hex(value: str) -> str:
    return ("0" if value[0] != "0" else "1") + value[1:]


def _verify(raw: bytes, fixture):
    return (
        subject
        .verify_v075_observer_signed_private_replay_attestation_bytes_v2(
            raw=raw,
            closure=fixture["closure"],
            authority_binding=fixture["closure"].authority_binding,
            used_stream_identities=fixture["streams"],
        )
    )


def _freeze_kwargs(fixture) -> dict[str, Any]:
    return {
        "authority": fixture["authorization"],
        "namespace": fixture["namespace"],
        "closure": fixture["closure"],
        "authority_binding": fixture["closure"].authority_binding,
        "used_stream_identities": fixture["streams"],
        "private_salt": fixture["salt"],
        "private_environment": (
            fixture["generated"].secret_laws_for_commitment()
        ),
        "observer_signer": fixture["signer"],
    }


def test_honest_post_private_replay_attestation_and_public_replay(
    honest,
) -> None:
    attestation = honest["attestation"]
    replayed = _verify(attestation.canonical_bytes, honest)
    document = replayed.to_document()

    assert replayed == attestation
    assert replayed.replayed_batch_count == 2
    assert replayed.replayed_draw_count == 12
    assert replayed.replayed_stream_count == 2
    assert replayed.ordered_entry_ids == tuple(
        item.entry_id for item in honest["closure"].entries
    )
    assert replayed.ordered_batch_ids == tuple(
        item.batch.batch_id for item in honest["closure"].entries
    )
    assert replayed.ordered_stream_ids == tuple(
        sorted(item.stream_id for item in honest["streams"])
    )
    assert len(replayed.source_private_replay_verification_id) == 64
    assert (
        document["private_replay_profile_id"]
        == subject.PRIVATE_REPLAY_PROFILE_ID
    )
    assert (
        document["private_replay_status"]
        == subject.PRIVATE_REPLAY_STATUS
    )
    assert document["private_replay_claim_observer_signed"] is True
    assert document["private_replay_independently_recomputed"] is False
    assert document["public_closure_and_stream_graph_recomputed"] is True
    assert document["private_verifier_invoked_inside_atomic_freeze"] is True
    assert (
        document["caller_supplied_source_verification_accepted"] is False
    )
    assert document["observer_signature_created_after_private_replay"] is True
    assert (
        document["observer_signature_after_private_replay_scope"]
        == "TRUSTED_ATOMIC_FREEZE_EXECUTION"
    )
    assert (
        document["public_verifier_proves_private_replay_execution_order"]
        is False
    )
    assert (
        document[
            "execution_order_is_trusted_api_discipline_not_cryptographic_proof"
        ]
        is True
    )
    assert (
        document["production_requires_signer_owning_sealed_observer_boundary"]
        is True
    )
    assert document["observer_signature_verified"] is True
    assert honest["signer"].messages[-1].startswith(
        subject.DOMAIN_TAGS["signature"].encode("utf-8") + b"\x00"
    )


def test_generic_signer_can_satisfy_public_crypto_but_never_unlocks_claims(
    honest,
) -> None:
    """Public signature validity is not execution-order cryptographic proof."""

    projection = subject._public_projection(  # noqa: SLF001
        closure=honest["closure"],
        authority_binding=honest["closure"].authority_binding,
        used_stream_identities=honest["streams"],
    )
    verification_id, _ = subject._expected_source_private_replay(  # noqa: SLF001
        projection
    )
    payload = subject._attestation_payload(  # noqa: SLF001
        source_private_replay_verification_id=verification_id,
        projection=projection,
    )
    generic_signer = observer_fixture._ObserverSigner()
    signature = generic_signer.sign_observer_evidence_v1(
        subject._signing_bytes(payload)  # noqa: SLF001
    )
    unsigned_document = {
        **payload,
        "observer_signature_hex": signature,
        "observer_signature_verified": True,
    }
    raw_document = {
        **unsigned_document,
        "attestation_id": subject._hash(  # noqa: SLF001
            "attestation",
            unsigned_document,
        ),
    }
    replayed = _verify(canonical_json_bytes(raw_document), honest)
    document = replayed.to_document()

    assert replayed.attestation_id == raw_document["attestation_id"]
    assert document["private_replay_claim_observer_signed"] is True
    assert document["private_replay_independently_recomputed"] is False
    assert (
        document["public_verifier_proves_private_replay_execution_order"]
        is False
    )
    assert (
        document[
            "execution_order_is_trusted_api_discipline_not_cryptographic_proof"
        ]
        is True
    )
    for field_name in (
        "official_execution_allowed",
        "production_authorizing",
        "scientific_endpoint_credit_allowed",
        "source_authority_complete",
        "code_provenance_complete",
        "portable_semantic_registry_complete",
        "fresh_heldout_access_allowed",
        "plan_certificate_issuance_allowed",
        "infeasibility_certificate_issuance_allowed",
    ):
        assert document[field_name] is False
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationProductionV2NotReady
    ):
        subject.open_v075_observer_signed_private_replay_production_v2()


def test_real_private_verifier_completes_before_atomic_signature(
    honest,
    monkeypatch,
) -> None:
    events: list[str] = []
    real_private_verifier = (
        observer.verify_loaded_private_observer_batch_closure_v2
    )

    def spy_private_verifier(**kwargs):
        events.append("private_verifier_started")
        result = real_private_verifier(**kwargs)
        events.append("private_verifier_completed")
        return result

    class OrderingSigner:
        def public_verification_key_v1(self):
            return honest["signer"].public_verification_key_v1()

        def sign_observer_evidence_v1(self, message: bytes) -> str:
            events.append("observer_sign")
            return honest["signer"].sign_observer_evidence_v1(message)

    monkeypatch.setattr(
        observer,
        "verify_loaded_private_observer_batch_closure_v2",
        spy_private_verifier,
    )
    kwargs = _freeze_kwargs(honest)
    kwargs["observer_signer"] = OrderingSigner()
    attestation = (
        subject.freeze_v075_observer_signed_private_replay_attestation_v2(
            **kwargs
        )
    )
    assert attestation == honest["attestation"]
    assert events == [
        "private_verifier_started",
        "private_verifier_completed",
        "observer_sign",
    ]


def test_private_verifier_failure_prevents_observer_signature(
    honest,
    monkeypatch,
) -> None:
    def fail_private_verifier(**_kwargs):
        raise observer.V075PrivateObserverBoundaryV2InvariantViolation(
            "injected private replay failure"
        )

    monkeypatch.setattr(
        observer,
        "verify_loaded_private_observer_batch_closure_v2",
        fail_private_verifier,
    )
    signer = observer_fixture._ObserverSigner()
    kwargs = _freeze_kwargs(honest)
    kwargs["observer_signer"] = signer
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation,
        match="private replay failed",
    ):
        subject.freeze_v075_observer_signed_private_replay_attestation_v2(
            **kwargs
        )
    assert signer.messages == []


def test_exact_clone_and_legacy_verification_have_no_upgrade_channel(
    honest,
) -> None:
    document = honest["attestation"].to_document()
    exact_clone = observer.V075ObserverBatchClosureVerificationV2(
        observer._BATCH_CLOSURE_VERIFICATION_ISSUER,  # noqa: SLF001
        document["closure_id"],
        document["occurrence_id"],
        tuple(document["ordered_batch_ids"]),
        document["observer_open_binding_id"],
        document["observer_open_authorization_id"],
        document["private_reveal_attestation_id"],
        document["remote_main_anchor_id"],
        document["target_tape_namespace_id"],
        document["replayed_batch_count"],
        document["replayed_draw_count"],
        document["replayed_stream_count"],
    )
    assert (
        exact_clone.verification_id
        == honest["attestation"].source_private_replay_verification_id
    )
    message_count = len(honest["signer"].messages)
    assert "verification" not in inspect.signature(
        subject.freeze_v075_observer_signed_private_replay_attestation_v2
    ).parameters
    with pytest.raises(TypeError, match="verification"):
        subject.freeze_v075_observer_signed_private_replay_attestation_v2(
            **_freeze_kwargs(honest),
            verification=exact_clone,
        )
    assert len(honest["signer"].messages) == message_count

    with pytest.raises(TypeError, match="verification"):
        subject.freeze_v075_observer_signed_private_replay_attestation_v2(
            **_freeze_kwargs(honest),
            verification=exact_clone.to_document(),
        )
    assert len(honest["signer"].messages) == message_count


def test_wrong_private_salt_and_environment_prevent_signing(
    honest,
    foreign,
) -> None:
    signer = observer_fixture._ObserverSigner()
    wrong_salt = _freeze_kwargs(honest)
    wrong_salt["private_salt"] = b"not-the-committed-private-salt"
    wrong_salt["observer_signer"] = signer
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
    ):
        subject.freeze_v075_observer_signed_private_replay_attestation_v2(
            **wrong_salt
        )
    assert signer.messages == []

    wrong_environment = _freeze_kwargs(honest)
    wrong_environment["private_environment"] = (
        foreign["generated"].secret_laws_for_commitment()
    )
    wrong_environment["observer_signer"] = signer
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
    ):
        subject.freeze_v075_observer_signed_private_replay_attestation_v2(
            **wrong_environment
        )
    assert signer.messages == []


def test_foreign_closure_and_inexact_stream_graph_fail_closed(
    honest,
    foreign,
) -> None:
    raw = honest["attestation"].canonical_bytes
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
    ):
        subject.verify_v075_observer_signed_private_replay_attestation_bytes_v2(
            raw=raw,
            closure=foreign["closure"],
            authority_binding=foreign["closure"].authority_binding,
            used_stream_identities=foreign["streams"],
        )
    for streams in (
        honest["streams"][:1],
        (honest["streams"][0], honest["streams"][0]),
        (*honest["streams"], observer_fixture._streams(
            honest["namespace"]
        ).streams[2]),
    ):
        with pytest.raises(
            subject
            .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
        ):
            subject.verify_v075_observer_signed_private_replay_attestation_bytes_v2(
                raw=raw,
                closure=honest["closure"],
                authority_binding=honest["closure"].authority_binding,
                used_stream_identities=streams,
            )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("replayed_draw_count", 13),
        (
            "private_replay_profile_id",
            observer_fixture._id("foreign-private-replay-profile"),
        ),
        (
            "private_replay_status",
            "CALLER_ASSERTED_PRIVATE_REPLAY",
        ),
        (
            "observer_evidence_key_id",
            observer_fixture._id("foreign-private-replay-key"),
        ),
        (
            "used_stream_graph_digest",
            observer_fixture._id("foreign-stream-graph"),
        ),
    ),
)
def test_public_count_profile_status_key_and_stream_rehash_attacks_fail(
    honest,
    field: str,
    replacement: Any,
) -> None:
    document = honest["attestation"].to_document()
    document[field] = replacement
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
    ):
        _verify(_rehash(document), honest)


def test_signature_and_private_claim_full_rehash_attacks_fail(
    honest,
) -> None:
    signature_attack = honest["attestation"].to_document()
    signature_attack["observer_signature_hex"] = _flip_hex(
        signature_attack["observer_signature_hex"]
    )
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
    ):
        _verify(_rehash(signature_attack), honest)

    private_claim_attack = honest["attestation"].to_document()
    private_claim_attack["source_private_replay_verification_id"] = (
        observer_fixture._id("caller-private-replay-verification")
    )
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
    ):
        _verify(_rehash(private_claim_attack), honest)

    foreign_signer = observer_fixture._ObserverSigner(
        use_campaign_test_key=True,
    )
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
    ):
        kwargs = _freeze_kwargs(honest)
        kwargs["observer_signer"] = foreign_signer
        subject.freeze_v075_observer_signed_private_replay_attestation_v2(
            **kwargs
        )
    assert foreign_signer.messages == []


def test_raw_canonical_keyset_and_byte_cap_are_strict(honest) -> None:
    raw = honest["attestation"].canonical_bytes
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
    ):
        _verify(raw + b" ", honest)

    unknown = honest["attestation"].to_document()
    unknown["caller_claim"] = True
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
    ):
        _verify(_rehash(unknown), honest)

    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationV2InvariantViolation
    ):
        _verify(b"x" * (subject.MAX_ATTESTATION_BYTES + 1), honest)


def test_atomic_private_channels_public_boundary_and_locks(
    honest,
) -> None:
    private_parameters = {
        "private_salt",
        "private_environment",
    }
    forbidden_public_parameters = {
        *private_parameters,
        "salt",
        "environment",
        "target",
        "target_law",
        "kernel",
        "random_tape",
        "observer_session",
    }
    freeze_parameters = inspect.signature(
        subject.freeze_v075_observer_signed_private_replay_attestation_v2
    ).parameters
    assert private_parameters.issubset(freeze_parameters)
    assert "verification" not in freeze_parameters
    public_verify_parameters = inspect.signature(
        subject
        .verify_v075_observer_signed_private_replay_attestation_bytes_v2
    ).parameters
    assert forbidden_public_parameters.isdisjoint(public_verify_parameters)

    with pytest.raises(TypeError):
        subject.verify_v075_observer_signed_private_replay_attestation_bytes_v2(
            raw=honest["attestation"].canonical_bytes,
            closure=honest["closure"],
            authority_binding=honest["closure"].authority_binding,
            used_stream_identities=honest["streams"],
            private_salt=b"forbidden",
        )

    document = honest["attestation"].to_document()
    values = dict(_walk_items(document))
    assert values["private_salt_serialized"] is False
    assert values["private_environment_serialized"] is False
    assert values["transition_law_serialized"] is False
    assert values["random_tape_serialized"] is False
    assert values["target_access_performed_by_attestation"] is False
    assert values["official_execution_allowed"] is False
    assert values["production_authorizing"] is False
    assert values["scientific_endpoint_credit_allowed"] is False
    assert values["source_authority_complete"] is False
    assert values["code_provenance_complete"] is False
    assert values["portable_semantic_registry_complete"] is False
    assert values["fresh_heldout_access_allowed"] is False
    assert values["raw_source_verification_accepted"] is False
    assert values["legacy_source_verification_upgrade_allowed"] is False
    assert values["trusted_atomic_freeze_private_inputs_required"] is True
    assert values["public_verifier_private_inputs_allowed"] is False
    assert (
        values["caller_supplied_source_verification_accepted"] is False
    )
    assert values["plan_certificate_issuance_allowed"] is False
    assert values["infeasibility_certificate_issuance_allowed"] is False

    assert subject.OFFICIAL_EXECUTION_ALLOWED is False
    assert subject.PRODUCTION_AUTHORIZING is False
    assert subject.SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED is False
    assert subject.SOURCE_AUTHORITY_COMPLETE is False
    assert subject.CODE_PROVENANCE_COMPLETE is False
    assert subject.PORTABLE_SEMANTIC_REGISTRY_COMPLETE is False
    assert subject.FRESH_HELDOUT_ACCESS_ALLOWED is False
    assert subject.TRUSTED_ATOMIC_FREEZE_PRIVATE_INPUTS_REQUIRED is True
    assert subject.PUBLIC_VERIFIER_PRIVATE_INPUTS_ALLOWED is False
    assert (
        subject.CALLER_SUPPLIED_PRIVATE_REPLAY_VERIFICATION_ALLOWED
        is False
    )
    assert subject.RAW_SOURCE_VERIFICATION_ACCEPTED is False
    assert (
        subject.LEGACY_PRIVATE_REPLAY_VERIFICATION_UPGRADE_ALLOWED is False
    )
    with pytest.raises(
        subject
        .V075ObserverSignedPrivateReplayAttestationProductionV2NotReady
    ):
        subject.open_v075_observer_signed_private_replay_production_v2()
