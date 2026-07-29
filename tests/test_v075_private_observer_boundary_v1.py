from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
from typing import Any

import pytest

from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_campaign_authority_v1 as authority
from acfqp import v075_public_graph_semantics_v1 as public
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _synthetic_environment(
) -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    # Construction-only unit-test material.  These are not production laws.
    return (
        ((1, Fraction(2, 3)), (2, Fraction(1, 3))),
        ((1, Fraction(3, 4)), (2, Fraction(1, 4))),
        ((1, Fraction(4, 5)), (2, Fraction(1, 5))),
    )


def _salt(marker: str = "one") -> bytes:
    return hashlib.sha512(
        ("v075-observer-test-salt-" + marker).encode("utf-8")
    ).digest()


def _namespace(
    marker: str = "one",
) -> authority.V075PublicTargetTapeNamespaceV1:
    family = authority.freeze_v075_public_family_generation_v1()
    commitment = authority.seal_opaque_environment_commitment_v1(
        family=family,
        secret_salt=_salt(marker),
        secret_laws=_synthetic_environment(),
    )
    registry = authority.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )

    def claim(
        role: authority.V075ExternalAuthorityRoleV1,
        subject: str,
    ) -> authority.V075SignedExternalAuthorityClaimV1:
        message = authority.external_authority_claim_signing_bytes_v1(
            signer_registry=registry,
            role=role,
            external_id=subject,
        )
        return authority.V075SignedExternalAuthorityClaimV1(
            registry,
            role,
            subject,
            sign_test_message(message),
        )

    role = authority.V075ExternalAuthorityRoleV1
    return authority.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=commitment,
        signer_registry=registry,
        claimed_final_preregistration_registry_id=registry.registry_id,
        remote_main_anchor=claim(
            role.REMOTE_MAIN_ANCHOR,
            _id("observer-test-anchor-" + marker),
        ),
        final_preregistration=claim(
            role.FINAL_PREREGISTRATION,
            _id("observer-test-prereg-" + marker),
        ),
        observer_profile=claim(
            role.OBSERVER_PROFILE,
            _id("observer-test-profile-" + marker),
        ),
    )


class _ConstructionSigner:
    def public_verification_key_v1(
        self,
    ) -> authority.V075RSAPublicVerificationKeyV1:
        return make_public_key("OBSERVER_EVIDENCE")

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        return sign_test_message(
            message,
            key_role="OBSERVER_EVIDENCE",
        )


def _fixture(
    namespace: authority.V075PublicTargetTapeNamespaceV1,
    marker: str = "one",
) -> observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1:
    return observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1(
        namespace,
        _id("observer-construction-registration-" + marker),
    )


def _streams(
    namespace: authority.V075PublicTargetTapeNamespaceV1,
    *,
    context_index: int = 0,
) -> public.V075FiveArmStreamSetV1:
    context = namespace.family.replicate_contexts[context_index]
    catalogue = public.root_catalogue_v1(context)
    row = public.observation_row_binding_v1(
        context,
        catalogue,
        catalogue.actions[0],
    )
    epoch = public.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    chain = public.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(epoch,),
    )
    pairing = public.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return public.freeze_five_arm_stream_set_v1(pairing)


def _open(
    namespace: authority.V075PublicTargetTapeNamespaceV1,
    *,
    marker: str = "one",
) -> observer.V075PrivateObserverSessionV1:
    return observer.open_construction_private_observer_fixture_v1(
        authority=_fixture(namespace, marker),
        private_salt=_salt(marker),
        private_environment=_synthetic_environment(),
        observer_signer=_ConstructionSigner(),
        session_external_id=_id("observer-session-" + marker),
    )


def _walk_keys(value: Any) -> tuple[str, ...]:
    if isinstance(value, dict):
        return tuple(value) + tuple(
            key
            for child in value.values()
            for key in _walk_keys(child)
        )
    if isinstance(value, list):
        return tuple(
            key for child in value for key in _walk_keys(child)
        )
    return ()


def test_production_constructor_rejects_construction_and_forged_binding() -> None:
    namespace = _namespace()
    construction = _fixture(namespace)
    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="exact independently issued",
    ):
        observer.open_private_observer_v1(
            authority=construction,  # type: ignore[arg-type]
            namespace=namespace,
            private_salt=_salt(),
            private_environment=_synthetic_environment(),
            observer_signer=_ConstructionSigner(),
            session_external_id=_id("cannot-open-production"),
        )

    forged_binding = observer.V075ObserverOpenAuthorityBindingV1(
        namespace=namespace,
        upstream_authority_id=_id("forged-production-authority"),
        verification_attestation_id=_id("forged-verification"),
        scope=observer.V075ObserverOpenAuthorityScopeV1.PRODUCTION_OPEN,
        independent_final_authority_verified=True,
        observer_open_authorized=True,
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="exact independently issued",
    ):
        observer.open_private_observer_v1(
            authority=forged_binding,  # type: ignore[arg-type]
            namespace=namespace,
            private_salt=_salt(),
            private_environment=_synthetic_environment(),
            observer_signer=_ConstructionSigner(),
            session_external_id=_id("forged-binding-cannot-open"),
        )
    assert observer.PRODUCTION_OPEN_AUTHORITY_INCLUDED is False


def test_construction_authority_is_explicitly_nonproduction_and_separate() -> None:
    namespace = _namespace()
    fixture = _fixture(namespace)
    document = fixture.to_document()
    assert document["scope"] == "CONSTRUCTION_ONLY"
    assert document["production_claim_allowed"] is False
    assert document["observer_open_authorized"] is False
    assert fixture.fixture_authority_id != fixture.fixture_registration_id

    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="exact domain-separated fixture",
    ):
        observer.open_construction_private_observer_fixture_v1(
            authority=namespace,  # type: ignore[arg-type]
            private_salt=_salt(),
            private_environment=_synthetic_environment(),
            observer_signer=_ConstructionSigner(),
            session_external_id=_id("unopened-public-namespace"),
        )


def test_reveal_mismatch_fails_before_any_observation() -> None:
    namespace = _namespace()
    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="does not match",
    ):
        observer.open_construction_private_observer_fixture_v1(
            authority=_fixture(namespace),
            private_salt=_salt("wrong"),
            private_environment=_synthetic_environment(),
            observer_signer=_ConstructionSigner(),
            session_external_id=_id("mismatched-reveal"),
        )

    changed = (
        ((1, Fraction(1)),),
        *_synthetic_environment()[1:],
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="does not match",
    ):
        observer.open_construction_private_observer_fixture_v1(
            authority=_fixture(namespace),
            private_salt=_salt(),
            private_environment=changed,
            observer_signer=_ConstructionSigner(),
            session_external_id=_id("mismatched-environment"),
        )


def test_five_arms_share_raw_crn_but_keep_distinct_signed_streams() -> None:
    namespace = _namespace()
    stream_set = _streams(namespace)
    session = _open(namespace)
    capabilities = tuple(
        session.observe_v1(stream)
        for stream in stream_set.streams
    )
    samples = tuple(item.record.sample for item in capabilities)
    assert len(set(samples)) == 1
    assert len(
        {item.record.stream_identity.stream_id for item in capabilities}
    ) == len(authority.ARM_ORDER)
    assert len(
        {
            item.record.stream_identity.pairing_group_id
            for item in capabilities
        }
    ) == 1
    assert tuple(item.record.stream_identity.arm for item in capabilities) == (
        authority.ARM_ORDER
    )
    assert tuple(
        entry.sequence_number for entry in session.journal_entries
    ) == (1, 2, 3, 4, 5)

    closure = session.close_v1()
    verification = (
        observer
        .verify_construction_private_observer_journal_closure_v1(
            closure=closure,
            authority=_fixture(namespace),
            private_salt=_salt(),
            private_environment=_synthetic_environment(),
        )
    )
    assert verification.replayed_record_count == 5
    assert verification.replayed_stream_count == 5


def test_signature_context_and_stream_transplantation_are_rejected() -> None:
    namespace = _namespace()
    root_streams = _streams(namespace)
    session = _open(namespace)
    record = session.observe_v1(root_streams.streams[0]).record

    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="signature",
    ):
        replace(record, observer_signature_hex="00" * 256)

    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="signature",
    ):
        replace(record, stream_identity=root_streams.streams[1])

    other_context_stream = _streams(
        namespace,
        context_index=1,
    ).streams[0]
    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="signature",
    ):
        replace(record, stream_identity=other_context_stream)


def test_sample_tamper_is_detected_by_exact_closure_replay_even_if_resigned() -> None:
    namespace = _namespace()
    fixture = _fixture(namespace)
    session = _open(namespace)
    record = session.observe_v1(_streams(namespace).streams[0]).record
    session.close_v1()

    sample = replace(
        record.sample,
        random_words=(
            record.sample.random_words[0] ^ 1,
            *record.sample.random_words[1:],
        ),
    )
    signer = _ConstructionSigner()
    message = observer.observation_record_signing_bytes_v1(
        session_public_id=record.session_public_id,
        authority_binding=record.authority_binding,
        stream_identity=record.stream_identity,
        sample=sample,
    )
    tampered_record = observer.V075SignedObservationRecordV1(
        record.session_public_id,
        record.authority_binding,
        record.stream_identity,
        sample,
        signer.sign_observer_evidence_v1(message),
    )
    entry = observer.V075ObserverJournalEntryV1(
        1,
        None,
        tampered_record,
    )
    closure_message = observer.observer_journal_closure_signing_bytes_v1(
        session_public_id=record.session_public_id,
        authority_binding=record.authority_binding,
        entries=(entry,),
    )
    malicious_closure = observer.V075ObserverJournalClosureV1(
        record.session_public_id,
        record.authority_binding,
        (entry,),
        signer.sign_observer_evidence_v1(closure_message),
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="do not replay",
    ):
        observer.verify_construction_private_observer_journal_closure_v1(
            closure=malicious_closure,
            authority=fixture,
            private_salt=_salt(),
            private_environment=_synthetic_environment(),
        )


def test_journal_reorder_and_postclosure_append_are_rejected() -> None:
    namespace = _namespace()
    session = _open(namespace)
    stream = _streams(namespace).streams[0]
    session.observe_v1(stream)
    session.observe_v1(stream)
    closure = session.close_v1()

    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="gapped, reordered, or transplanted",
    ):
        replace(closure, entries=tuple(reversed(closure.entries)))
    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="closed",
    ):
        session.observe_v1(stream)
    with pytest.raises(
        observer.V075PrivateObserverBoundaryInvariantViolation,
        match="already closed",
    ):
        session.close_v1()


def test_capabilities_and_journal_contain_no_private_environment_material() -> None:
    namespace = _namespace()
    session = _open(namespace)
    capability = session.observe_v1(_streams(namespace).streams[0])
    closure = session.close_v1()

    capability_document = capability.to_document()
    record_document = capability.record.to_document()
    closure_document = closure.to_document()
    forbidden_keys = {
        "law",
        "laws",
        "spawn_law",
        "secret_law",
        "secret_laws",
        "salt",
        "secret_salt",
        "reveal",
        "private_reveal",
    }
    for document in (
        capability_document,
        record_document,
        closure_document,
    ):
        assert forbidden_keys.isdisjoint(_walk_keys(document))
        serialized = repr(document)
        assert _salt().hex() not in serialized
        assert "Fraction(" not in serialized

    # A planner/worker receives only this capability, not the private session.
    assert set(capability_document).isdisjoint(forbidden_keys)
    assert "random_words" not in capability_document
    assert observer.PRODUCTION_ENVIRONMENT_INCLUDED is False
    assert observer.PRODUCTION_PRIVATE_SIGNER_INCLUDED is False
