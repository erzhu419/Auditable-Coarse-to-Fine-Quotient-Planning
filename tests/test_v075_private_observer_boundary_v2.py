from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect
import json
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_confirmatory_manifest_preregistration_v2 as manifest
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_private_observer_boundary_v1 as observer_v1
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_production_campaign_profile_v2 as campaign_profile
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_remote_main_anchor_verifier_v2 as remote
from acfqp import v075_reveal_verifying_attestation_authority_v2 as reveal
from tests import test_v075_private_observer_boundary_v1 as v1_fixture
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-private-observer-v2-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _oid(label: str) -> str:
    return hashlib.sha1(
        b"acfqp:v075-private-observer-v2-test-git:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


class _ObserverSigner:
    def __init__(
        self,
        key_role: str = "OBSERVER_EVIDENCE",
        *,
        use_campaign_test_key: bool = False,
    ) -> None:
        self.key_role = key_role
        self.use_campaign_test_key = use_campaign_test_key
        self.messages: list[bytes] = []

    def public_verification_key_v1(
        self,
    ) -> public.V075RSAPublicVerificationKeyV1:
        if self.use_campaign_test_key:
            return public.V075RSAPublicVerificationKeyV1(
                self.key_role,
                make_public_key("CAMPAIGN_AUTHORITY").modulus,
            )
        return make_public_key(self.key_role)

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        self.messages.append(message)
        return sign_test_message(
            message,
            key_role=(
                "CAMPAIGN_AUTHORITY"
                if self.use_campaign_test_key
                else self.key_role
            ),
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


def _fixture(
    marker: str = "one",
    *,
    swapped_registry: bool = False,
):
    generated = private_env.generate_v075_private_environment_v1(
        profile=(
            private_env
            .freeze_v075_private_environment_generation_profile_v1()
        ),
        secret_generation_seed=hashlib.sha256(
            ("generated-" + marker).encode("utf-8")
        ).digest(),
    )
    salt = hashlib.sha512(
        ("salt-" + marker).encode("utf-8")
    ).digest()
    commitment = (
        private_env.seal_v075_generated_private_environment_commitment_v1(
            generated_environment=generated,
            secret_salt=salt,
        )
    )
    signer = _ObserverSigner(
        use_campaign_test_key=swapped_registry,
    )
    registry = public.V075TrustedSignerRegistryV1(
        (
            public.V075RSAPublicVerificationKeyV1(
                "CAMPAIGN_AUTHORITY",
                make_public_key("OBSERVER_EVIDENCE").modulus,
            )
            if swapped_registry
            else make_public_key("CAMPAIGN_AUTHORITY")
        ),
        signer.public_verification_key_v1(),
    )
    workload = manifest.freeze_v075_confirmatory_public_workload_v2()
    runner_profile = (
        campaign_profile.freeze_v075_production_campaign_profile_v2()
    )
    anchor = remote.V075RemoteMainAnchorAttestationV2(
        remote._ANCHOR_ISSUER,  # type: ignore[attr-defined]
        _oid(marker + "-commit"),
        _oid(marker + "-tree"),
        (_oid(marker + "-parent"),),
        _oid(marker + "-manifest-blob"),
        _oid(marker + "-final-blob"),
        _id(marker + "-manifest"),
        _id(marker + "-final"),
        _id(marker + "-component-registry"),
        _id(marker + "-semantic-registry-binding"),
        _id(marker + "-semantic-artifact-replay"),
        workload.workload_id,
        runner_profile.profile_id,
        commitment.family.generation_id,
        commitment.commitment_id,
        registry,
    )
    namespace = namespace_v2.V075PublicTargetTapeNamespaceV2(
        namespace_v2._NAMESPACE_ISSUER,  # type: ignore[attr-defined]
        anchor,
        workload,
        commitment.family,
        runner_profile,
        commitment,
        registry,
    )
    attestation = (
        reveal.issue_v075_reveal_verified_private_attestation_v2(
            anchor=anchor,
            commitment=commitment,
            generated_environment=generated,
            secret_salt=salt,
            signer_registry=registry,
            observer_signer=signer,
        )
    )
    tracked = preopen.V075TrackedPreopenBlobClosureV2(
        preopen._BLOB_CLOSURE_ISSUER,  # type: ignore[attr-defined]
        anchor,
        _id(marker + "-manifest-bytes"),
        _id(marker + "-final-bytes"),
    )
    authorization = preopen.V075ObserverOpenAuthorizationV2(
        preopen._AUTHORIZATION_ISSUER,  # type: ignore[attr-defined]
        anchor,
        tracked,
        registry,
        commitment,
        attestation,
    )
    return (
        generated,
        salt,
        namespace,
        authorization,
        signer,
    )


def _streams(
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    *,
    context_index: int = 0,
) -> graph.V075FiveArmStreamSetV1:
    assert graph.validate_v075_public_graph_namespace_v2(namespace) is namespace
    context = namespace.family.replicate_contexts[context_index]
    catalogue = graph.root_catalogue_v1(context)
    row = graph.observation_row_binding_v1(
        context,
        catalogue,
        catalogue.actions[0],
    )
    epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return graph.freeze_five_arm_stream_set_v1(pairing)


def _open(marker: str = "one"):
    generated, salt, namespace, authorization, signer = _fixture(marker)
    binding = observer._require_exact_v2_binding(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
    )
    session = observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
        binding=binding,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id(marker + "-session"),
    )
    return (
        generated,
        salt,
        namespace,
        authorization,
        signer,
        session,
    )


def _replay_synthetic_closure(
    *,
    closure: observer.V075ObserverJournalClosureV2,
    authorization: preopen.V075ObserverOpenAuthorizationV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    private_salt: bytes,
    private_environment,
) -> observer.V075ObserverClosureVerificationV2:
    binding = observer._require_exact_v2_binding(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
    )
    streams = tuple(
        {
            entry.record.stream_identity.stream_id: (
                entry.record.stream_identity
            )
            for entry in closure.entries
        }.values()
    )
    replayed = observer._load_and_replay_observer_journal_closure_v2(  # noqa: SLF001
        raw=closure.canonical_bytes,
        binding=binding,
        known_stream_identities=streams,
    )
    return (
        observer
        ._verify_private_observer_journal_closure_from_verified_gate_v2(  # noqa: SLF001
            closure=replayed,
            authority=authorization,
            namespace=namespace,
            binding=binding,
            private_salt=private_salt,
            private_environment=private_environment,
        )
    )


def _replay_synthetic_batch_closure(
    *,
    closure: observer.V075ObserverBatchJournalClosureV2,
    authorization: preopen.V075ObserverOpenAuthorizationV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    private_salt: bytes,
    private_environment,
) -> observer.V075ObserverBatchClosureVerificationV2:
    binding = observer._require_exact_v2_binding(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
    )
    streams = tuple(
        {
            entry.batch.request.stream_identity.stream_id: (
                entry.batch.request.stream_identity
            )
            for entry in closure.entries
        }.values()
    )
    replayed = observer.load_observer_batch_journal_closure_bytes_v2(
        raw=closure.canonical_bytes,
        authority_binding=binding,
        known_stream_identities=streams,
    )
    return observer.verify_loaded_private_observer_batch_closure_v2(
        closure=replayed,
        authority=authorization,
        namespace=namespace,
        authority_binding=binding,
        private_salt=private_salt,
        private_environment=private_environment,
    )


def test_exact_v2_open_observe_close_and_private_replay() -> None:
    (
        generated,
        salt,
        namespace,
        authorization,
        _signer,
        session,
    ) = _open()
    streams = _streams(namespace)
    capabilities = (
        session.observe_v2(streams.streams[0]),
        session.observe_v2(streams.streams[0]),
        session.observe_v2(streams.streams[1]),
    )
    closure = session.close_v2()
    verification = _replay_synthetic_closure(
        closure=closure,
        authorization=authorization,
        namespace=namespace,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )

    assert type(session) is observer.V075PrivateObserverSessionV2
    assert type(closure) is observer.V075ObserverJournalClosureV2
    assert all(
        type(item) is observer.V075ObservationCapabilityV2
        for item in capabilities
    )
    assert tuple(
        item.record.sample.accepted_draw_index for item in capabilities
    ) == (1, 2, 1)
    assert all(
        item.record.stream_identity.namespace is namespace
        for item in capabilities
    )
    assert closure.authority_binding.namespace is namespace
    assert (
        closure.authority_binding.authorization_id
        == authorization.authorization_id
    )
    assert (
        closure.authority_binding.private_reveal_attestation_id
        == authorization.private_reveal_attestation.attestation_id
    )
    assert verification.replayed_record_count == 3
    assert verification.replayed_stream_count == 2
    assert (
        verification.target_tape_namespace_id
        == namespace.target_tape_namespace_id
    )
    assert (
        verification.to_document()["verification_result"]
        == "EXACT_V2_REPLAY_VERIFIED"
    )

    documents = (
        session.public_session_document_v2(),
        *(item.to_document() for item in capabilities),
        closure.to_document(),
        verification.to_document(),
    )
    forbidden = {
        "secret_salt",
        "secret_laws",
        "private_environment",
        "rank_probabilities",
        "private_key",
        "signing_key",
    }
    for document in documents:
        assert forbidden.isdisjoint(_walk_keys(document))
        encoded = json.dumps(document, sort_keys=True)
        assert salt.hex() not in encoded
        assert (
            repr(generated.secret_laws_for_commitment()) not in encoded
        )
        assert document.get("legacy_v1_projection_issued", False) is False


def test_v1_and_v2_authority_namespace_and_closure_roles_do_not_cross() -> None:
    generated, salt, namespace, authorization, signer, session = _open()
    closure_v2 = session.close_v2()
    namespace_v1 = v1_fixture._namespace("v2-cross")
    fixture_v1 = v1_fixture._fixture(namespace_v1, "v2-cross")

    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="exact V2",
    ):
        observer._require_exact_v2_binding(  # noqa: SLF001
            authority=fixture_v1,  # type: ignore[arg-type]
            namespace=namespace_v1,  # type: ignore[arg-type]
        )
    with pytest.raises(
        observer_v1.V075PrivateObserverBoundaryInvariantViolation,
        match="exact independently issued",
    ):
        observer_v1.open_private_observer_v1(
            authority=authorization,  # type: ignore[arg-type]
            namespace=namespace,  # type: ignore[arg-type]
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
            session_external_id=_id("cross-v2-into-v1"),
        )
    closure_v1 = v1_fixture._open(
        namespace_v1,
        marker="v2-cross",
    ).close_v1()
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="closure V2|signature",
    ):
        observer._load_and_replay_observer_journal_closure_v2(  # noqa: SLF001
            raw=canonical_json_bytes(closure_v1.to_document()),
            binding=closure_v2.authority_binding,
            known_stream_identities=(),
        )

    assert closure_v2.to_document()["schema"].endswith(".v2")
    assert closure_v1.to_document()["schema"].endswith(".v1")
    assert set(observer.DOMAIN_TAGS.values()).isdisjoint(
        observer_v1.DOMAIN_TAGS.values()
    )


def test_namespace_anchor_commitment_and_registry_transplants_fail() -> None:
    (
        generated_a,
        salt_a,
        namespace_a,
        authorization_a,
        signer_a,
    ) = _fixture("a")
    (
        generated_b,
        salt_b,
        namespace_b,
        authorization_b,
        signer_b,
    ) = _fixture("b", swapped_registry=True)

    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="transplanted|signature",
    ):
        observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
            authority=authorization_a,
            namespace=namespace_b,
            binding=observer._require_exact_v2_binding(  # noqa: SLF001
                authority=authorization_a,
                namespace=namespace_a,
            ),
            private_salt=salt_a,
            private_environment=generated_a.secret_laws_for_commitment(),
            observer_signer=signer_a,
            session_external_id=_id("foreign-namespace"),
        )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="reveal attestation",
    ):
        observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
            authority=authorization_a,
            namespace=namespace_a,
            binding=observer._require_exact_v2_binding(  # noqa: SLF001
                authority=authorization_a,
                namespace=namespace_a,
            ),
            private_salt=salt_b,
            private_environment=generated_b.secret_laws_for_commitment(),
            observer_signer=signer_a,
            session_external_id=_id("foreign-commitment"),
        )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="signer",
    ):
        observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
            authority=authorization_a,
            namespace=namespace_a,
            binding=observer._require_exact_v2_binding(  # noqa: SLF001
                authority=authorization_a,
                namespace=namespace_a,
            ),
            private_salt=salt_a,
            private_environment=generated_a.secret_laws_for_commitment(),
            observer_signer=_ObserverSigner("CAMPAIGN_AUTHORITY"),
            session_external_id=_id("foreign-signer-role"),
        )

    # The independently valid B graph cannot replay an A closure.
    session_a = observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
        authority=authorization_a,
        namespace=namespace_a,
        binding=observer._require_exact_v2_binding(  # noqa: SLF001
            authority=authorization_a,
            namespace=namespace_a,
        ),
        private_salt=salt_a,
        private_environment=generated_a.secret_laws_for_commitment(),
        observer_signer=signer_a,
        session_external_id=_id("closure-a"),
    )
    closure_a = session_a.close_v2()
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="transplanted|signature",
    ):
        _replay_synthetic_closure(
            closure=closure_a,
            authorization=authorization_b,
            namespace=namespace_b,
            private_salt=salt_b,
            private_environment=generated_b.secret_laws_for_commitment(),
        )
    assert signer_b.public_verification_key_v1() == (
        namespace_b.signer_registry.observer_evidence_key
    )


def test_v2_journal_reorder_signature_and_stream_transplants_fail() -> None:
    (
        generated,
        salt,
        namespace,
        authorization,
        _signer,
        session,
    ) = _open("journal")
    streams = _streams(namespace)
    first = session.observe_v2(streams.streams[0])
    session.observe_v2(streams.streams[1])
    closure = session.close_v2()

    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="reordered|signature",
    ):
        replace(closure, entries=tuple(reversed(closure.entries)))
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="signature",
    ):
        replace(
            first.record,
            stream_identity=streams.streams[1],
        )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="reveal attestation",
    ):
        _replay_synthetic_closure(
            closure=closure,
            authorization=authorization,
            namespace=namespace,
            private_salt=hashlib.sha512(b"wrong-salt").digest(),
            private_environment=generated.secret_laws_for_commitment(),
        )

    verified = _replay_synthetic_closure(
        closure=closure,
        authorization=authorization,
        namespace=namespace,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    assert verified.replayed_record_count == 2


def test_production_entrypoint_replays_public_bytes_before_private_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, bytes, bytes]] = []

    def reject_before_open(
        *,
        repository_root,
        private_reveal_attestation_bytes,
        claimed_authorization_bytes,
    ):
        calls.append(
            (
                repository_root,
                private_reveal_attestation_bytes,
                claimed_authorization_bytes,
            )
        )
        raise preopen.V075PreopenAuthorizationV2NotReady("closed")

    class PrivateMaterialMustNotBeRead:
        def __iter__(self):
            raise AssertionError(
                "private environment read before public authority replay"
            )

    monkeypatch.setattr(
        preopen,
        "verify_v075_observer_open_authorization_v2",
        reject_before_open,
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="production authority replay failed",
    ):
        observer.open_private_observer_v2(
            repository_root="/tmp/non-authority",
            private_reveal_attestation_bytes=b"reveal",
            claimed_authorization_bytes=b"authorization",
            namespace_bytes=b"namespace",
            private_salt=b"must-not-be-read",
            private_environment=PrivateMaterialMustNotBeRead(),
            observer_signer=object(),  # type: ignore[arg-type]
            session_external_id=_id("must-not-open"),
        )
    assert calls == [
        ("/tmp/non-authority", b"reveal", b"authorization")
    ]
    signature = inspect.signature(observer.open_private_observer_v2)
    assert {
        "repository_root",
        "private_reveal_attestation_bytes",
        "claimed_authorization_bytes",
        "namespace_bytes",
    } <= set(signature.parameters)
    assert "authority" not in signature.parameters
    assert "namespace" not in signature.parameters


def test_canonical_loader_rejects_rehashed_bytes_and_clears_signer() -> None:
    (
        _generated,
        _salt,
        namespace,
        _authorization,
        _signer,
        session,
    ) = _open("canonical")
    stream = _streams(namespace).streams[0]
    capability = session.observe_v2(stream)
    closure = session.close_v2()
    assert getattr(session, "_signer") is None
    assert (
        capability.to_document()["record"]
        == capability.record.to_document()
    )
    assert (
        observer.DOMAIN_TAGS["observation_signature"]
        != observer.DOMAIN_TAGS["observation_artifact"]
    )
    assert (
        observer.DOMAIN_TAGS["journal_closure_signature"]
        != observer.DOMAIN_TAGS["journal_closure_artifact"]
    )

    document = loads_canonical_json(closure.canonical_bytes)
    document["entries"][0]["record"]["record_id"] = _id(
        "forged-record-id"
    )
    forged_raw = canonical_json_bytes(document)
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="record fields|content ID",
    ):
        observer._load_and_replay_observer_journal_closure_v2(  # noqa: SLF001
            raw=forged_raw,
            binding=closure.authority_binding,
            known_stream_identities=(stream,),
        )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="exact used stream set|prereplayed stream",
    ):
        observer._load_and_replay_observer_journal_closure_v2(  # noqa: SLF001
            raw=closure.canonical_bytes,
            binding=closure.authority_binding,
            known_stream_identities=(),
        )
    closure_signature = inspect.signature(
        observer.verify_private_observer_journal_closure_v2
    )
    assert "closure_bytes" in closure_signature.parameters
    assert "closure" not in closure_signature.parameters


def test_full_stream_replay_occurs_once_per_session_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        _generated,
        _salt,
        namespace,
        _authorization,
        _signer,
        session,
    ) = _open("replay-count")
    stream = _streams(namespace).streams[0]
    original = observer._replay_v2_stream_identity  # noqa: SLF001
    calls = 0

    def counted(value):
        nonlocal calls
        calls += 1
        return original(value)

    monkeypatch.setattr(
        observer,
        "_replay_v2_stream_identity",
        counted,
    )
    for _ in range(8):
        session.observe_v2(stream)
    assert calls == 1
    closure = session.close_v2()
    observer._load_and_replay_observer_journal_closure_v2(  # noqa: SLF001
        raw=closure.canonical_bytes,
        binding=closure.authority_binding,
        known_stream_identities=(stream,),
    )
    assert calls == 2


def test_v1_construction_observer_regression_remains_byte_stable() -> None:
    namespace = v1_fixture._namespace("regression")
    streams = v1_fixture._streams(namespace)
    session = v1_fixture._open(namespace, marker="regression")
    capability = session.observe_v1(streams.streams[0])
    closure = session.close_v1()
    verification = (
        observer_v1
        .verify_construction_private_observer_journal_closure_v1(
            closure=closure,
            authority=v1_fixture._fixture(namespace, "regression"),
            private_salt=v1_fixture._salt("regression"),
            private_environment=v1_fixture._synthetic_environment(),
        )
    )
    assert capability.to_document()["schema"].endswith(".v1")
    assert closure.to_document()["schema"].endswith(".v1")
    assert verification.to_document()["schema"].endswith(".v1")


def test_batch_native_streams_exact_aggregates_without_per_draw_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        generated,
        salt,
        namespace,
        authorization,
        signer,
        session,
    ) = _open("batch-native")
    stream = _streams(namespace).streams[0]
    original = observer._replay_v2_stream_identity  # noqa: SLF001
    replay_calls = 0

    def counted(value):
        nonlocal replay_calls
        replay_calls += 1
        return original(value)

    monkeypatch.setattr(
        observer,
        "_replay_v2_stream_identity",
        counted,
    )
    baseline_signatures = len(signer.messages)
    first = session.observe_batch_v2(
        occurrence_id=_id("batch-native-occurrence"),
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=37,
        accepted_draw_cap=1_000,
    )
    second = session.observe_batch_v2(
        occurrence_id=_id("batch-native-occurrence"),
        stream_identity=stream,
        accepted_draw_start=38,
        accepted_draw_count=963,
        accepted_draw_cap=1_000,
    )
    assert replay_calls == 1
    assert len(signer.messages) == baseline_signatures + 2
    assert session.journal_entries == ()
    assert len(session.batch_journal_entries) == 2
    assert sum(item.count for item in first.outcomes) == 37
    assert sum(item.count for item in second.outcomes) == 963
    assert first.random_word_count == 37 + first.rejection_count
    assert second.random_word_count == 963 + second.rejection_count
    assert first.reward_sum == sum(
        (item.reward_sum for item in first.outcomes),
        start=Fraction(0),
    )

    batch_document = second.to_document()
    keys = set(_walk_keys(batch_document))
    assert "records" not in keys
    assert "record" not in keys
    assert "random_words" not in keys
    assert "samples" not in keys
    assert batch_document["per_draw_records_created"] is False
    assert batch_document["individual_random_words_retained"] is False
    assert len(second.canonical_bytes) < 64 * 1024

    projected_closure_size = (
        observer._projected_observer_batch_journal_closure_size_v2(  # noqa: SLF001
            occurrence_id=_id("batch-native-occurrence"),
            session_public_id=session.session_public_id,
            authority_binding=session.authority_binding,
            entries=session.batch_journal_entries,
        )
    )
    closure = session.close_batch_v2()
    assert projected_closure_size == len(closure.canonical_bytes)
    assert len(signer.messages) == baseline_signatures + 3
    assert getattr(session, "_signer") is None
    assert getattr(session, "_kernels") == {}
    assert closure.to_document()["per_draw_journal_entries"] == 0
    assert closure.to_document()["accepted_draw_count"] == 1_000
    replayed = observer.load_observer_batch_journal_closure_bytes_v2(
        raw=closure.canonical_bytes,
        authority_binding=closure.authority_binding,
        known_stream_identities=(stream,),
    )
    assert replayed == closure
    assert replay_calls == 2
    verification = _replay_synthetic_batch_closure(
        closure=closure,
        authorization=authorization,
        namespace=namespace,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    assert verification.closure_id == closure.closure_id
    assert verification.occurrence_id == _id("batch-native-occurrence")
    assert verification.batch_ids == (
        first.batch_id,
        second.batch_id,
    )
    assert verification.replayed_batch_count == 2
    assert verification.replayed_draw_count == 1_000
    assert verification.replayed_stream_count == 1


def test_batch_signature_commits_each_outcome_count_and_reward_sum() -> None:
    _, _, namespace, _, signer, session = _open("batch-count-attack")
    stream = _streams(namespace).streams[0]
    batch = session.observe_batch_v2(
        occurrence_id=_id("batch-count-attack-occurrence"),
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=4_096,
        accepted_draw_cap=4_096,
    )
    outcomes = list(batch.outcomes)
    pair: tuple[int, int] | None = None
    for donor_index, donor in enumerate(outcomes):
        if donor.count <= 1:
            continue
        for recipient_index, recipient in enumerate(outcomes):
            if (
                donor_index != recipient_index
                and donor.failure == recipient.failure
                and donor.terminal == recipient.terminal
                and donor.realized_row_reward
                == recipient.realized_row_reward
            ):
                pair = donor_index, recipient_index
                break
        if pair is not None:
            break
    assert pair is not None
    donor_index, recipient_index = pair
    donor = outcomes[donor_index]
    recipient = outcomes[recipient_index]
    outcomes[donor_index] = replace(
        donor,
        count=donor.count - 1,
        reward_sum=donor.realized_row_reward * (donor.count - 1),
    )
    outcomes[recipient_index] = replace(
        recipient,
        count=recipient.count + 1,
        reward_sum=(
            recipient.realized_row_reward * (recipient.count + 1)
        ),
    )
    mutated_outcomes = tuple(outcomes)
    mutated_facts = observer._V075BatchFactsV2(  # noqa: SLF001
        mutated_outcomes,
        batch.reward_sum,
        batch.failure_count,
        batch.terminal_count,
        batch.random_word_count,
        batch.rejection_count,
        batch.first_random_word_index,
        batch.next_random_word_index,
        batch.transcript_commitment,
    )
    assert sum(item.count for item in mutated_outcomes) == 4_096
    assert mutated_facts.reward_sum == batch.reward_sum
    assert mutated_facts.failure_count == batch.failure_count
    assert mutated_facts.terminal_count == batch.terminal_count
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="signature",
    ):
        observer.V075SignedObservationBatchV2(
            batch.request,
            mutated_outcomes,
            batch.reward_sum,
            batch.failure_count,
            batch.terminal_count,
            batch.random_word_count,
            batch.rejection_count,
            batch.first_random_word_index,
            batch.next_random_word_index,
            batch.transcript_commitment,
            batch.observer_signature_hex,
        )
    mutated_signature = signer.sign_observer_evidence_v1(
        observer.batch_observation_signing_bytes_v2(
            request=batch.request,
            facts=mutated_facts,
        )
    )
    resigned = observer.V075SignedObservationBatchV2(
        batch.request,
        mutated_outcomes,
        batch.reward_sum,
        batch.failure_count,
        batch.terminal_count,
        batch.random_word_count,
        batch.rejection_count,
        batch.first_random_word_index,
        batch.next_random_word_index,
        batch.transcript_commitment,
        mutated_signature,
    )
    assert resigned.batch_id != batch.batch_id
    assert (
        resigned.to_document()["outcome_aggregate_commitments"]
        != batch.to_document()["outcome_aggregate_commitments"]
    )


def test_batch_native_mode_caps_and_failure_poisoning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, namespace, _, _, per_draw_session = _open("mode-per-draw")
    stream = _streams(namespace).streams[0]
    eligibility = per_draw_session.batch_open_eligibility_v2
    assert type(eligibility) is observer.V075BatchOpenEligibilityV2
    assert eligibility.eligible is True
    assert eligibility.status == "ELIGIBLE"
    per_draw_session.observe_v2(stream)
    assert (
        per_draw_session.batch_open_eligibility_v2.status
        == "INELIGIBLE_PER_DRAW_MODE"
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="cannot mix",
    ):
        per_draw_session.observe_batch_v2(
            occurrence_id=_id("mode-occurrence"),
            stream_identity=stream,
            accepted_draw_start=2,
            accepted_draw_count=1,
            accepted_draw_cap=2,
        )

    _, _, namespace, _, _, batch_session = _open("mode-batch")
    stream = _streams(namespace).streams[0]
    batch_session.observe_batch_v2(
        occurrence_id=_id("mode-batch-occurrence"),
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=1,
        accepted_draw_cap=2,
    )
    assert batch_session.batch_open_eligibility_v2.eligible is True
    assert (
        batch_session.batch_open_eligibility_v2.occurrence_id
        == _id("mode-batch-occurrence")
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="cannot mix",
    ):
        batch_session.observe_v2(stream)
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="frozen draw cap",
    ):
        batch_session.observe_batch_v2(
            occurrence_id=_id("mode-batch-occurrence"),
            stream_identity=stream,
            accepted_draw_start=2,
            accepted_draw_count=1,
            accepted_draw_cap=3,
        )

    _, _, namespace, _, _, count_capped = _open("batch-count-cap")
    stream = _streams(namespace).streams[0]
    count_capped.observe_batch_v2(
        occurrence_id=_id("batch-count-cap-occurrence"),
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=1,
        accepted_draw_cap=2,
    )
    private_stream = getattr(count_capped, "_streams")[stream.stream_id]
    assert private_stream.accepted_draw_count == 1
    monkeypatch.setattr(observer, "MAX_BATCHES_PER_SESSION", 1)
    assert (
        count_capped.batch_open_eligibility_v2.status
        == "INELIGIBLE_BATCH_COUNT_CAP"
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="batch-count cap",
    ):
        count_capped.observe_batch_v2(
            occurrence_id=_id("batch-count-cap-occurrence"),
            stream_identity=stream,
            accepted_draw_start=2,
            accepted_draw_count=1,
            accepted_draw_cap=2,
        )
    assert private_stream.accepted_draw_count == 1
    assert len(count_capped.close_batch_v2().entries) == 1
    assert (
        count_capped.batch_open_eligibility_v2.status
        == "INELIGIBLE_CLOSED"
    )

    _, _, namespace, _, _, poisoned = _open("batch-poison")
    stream = _streams(namespace).streams[0]

    def explode(_self, _sample):
        raise RuntimeError("injected batch failure")

    monkeypatch.setattr(
        observer._StreamingBatchAccumulatorV2,  # noqa: SLF001
        "append",
        explode,
    )
    with pytest.raises(RuntimeError, match="injected batch failure"):
        poisoned.observe_batch_v2(
            occurrence_id=_id("batch-poison-occurrence"),
            stream_identity=stream,
            accepted_draw_start=1,
            accepted_draw_count=2,
            accepted_draw_cap=2,
        )
    assert getattr(poisoned, "_closed") is True
    assert getattr(poisoned, "_poisoned") is True
    assert getattr(poisoned, "_signer") is None
    assert getattr(poisoned, "_kernels") == {}
    assert (
        poisoned.batch_open_eligibility_v2.status
        == "INELIGIBLE_POISONED"
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="closed",
    ):
        poisoned.close_batch_v2()


def test_batch_cumulative_closure_cap_poisons_before_unverifiable_append(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, namespace, _, _, session = _open("batch-cumulative-cap")
    stream = _streams(namespace).streams[0]
    occurrence_id = _id("batch-cumulative-cap-occurrence")
    first = session.observe_batch_v2(
        occurrence_id=occurrence_id,
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=1,
        accepted_draw_cap=2,
    )
    first_entry = session.batch_journal_entries[0]
    projected_one = (
        observer._projected_observer_batch_journal_closure_size_v2(  # noqa: SLF001
            occurrence_id=occurrence_id,
            session_public_id=session.session_public_id,
            authority_binding=session.authority_binding,
            entries=(first_entry,),
        )
    )
    size_only_second_entry = observer.V075ObserverBatchJournalEntryV2(
        2,
        first_entry.entry_id,
        first,
    )
    projected_two = (
        observer._projected_observer_batch_journal_closure_size_v2(  # noqa: SLF001
            occurrence_id=occurrence_id,
            session_public_id=session.session_public_id,
            authority_binding=session.authority_binding,
            entries=(first_entry, size_only_second_entry),
        )
    )
    assert projected_two > projected_one > len(first.canonical_bytes)
    monkeypatch.setattr(
        observer,
        "MAX_CANONICAL_CLOSURE_BYTES",
        (projected_one + projected_two) // 2,
    )
    private_stream = getattr(session, "_streams")[stream.stream_id]
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="cumulative closure byte cap",
    ):
        session.observe_batch_v2(
            occurrence_id=occurrence_id,
            stream_identity=stream,
            accepted_draw_start=2,
            accepted_draw_count=1,
            accepted_draw_cap=2,
        )
    # The draw crossed the irreversible target boundary, so failure poisons
    # the session and the oversized second entry is never appended or closed.
    assert private_stream.accepted_draw_count == 2
    assert len(session.batch_journal_entries) == 1
    assert getattr(session, "_closed") is True
    assert getattr(session, "_poisoned") is True
    assert getattr(session, "_signer") is None
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="closed",
    ):
        session.close_batch_v2()


def test_batch_count_cap_is_replayed_by_closure_loader_and_verifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        generated,
        salt,
        namespace,
        authorization,
        _signer,
        session,
    ) = _open("batch-count-cap-replay")
    stream = _streams(namespace).streams[0]
    occurrence_id = _id("batch-count-cap-replay-occurrence")
    session.observe_batch_v2(
        occurrence_id=occurrence_id,
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=1,
        accepted_draw_cap=2,
    )
    session.observe_batch_v2(
        occurrence_id=occurrence_id,
        stream_identity=stream,
        accepted_draw_start=2,
        accepted_draw_count=1,
        accepted_draw_cap=2,
    )
    closure = session.close_batch_v2()
    assert len(closure.entries) == 2

    monkeypatch.setattr(observer, "MAX_BATCHES_PER_SESSION", 1)
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="batch-count cap",
    ):
        observer.V075ObserverBatchJournalClosureV2(
            closure.occurrence_id,
            closure.session_public_id,
            closure.authority_binding,
            closure.entries,
            closure.observer_signature_hex,
        )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="batch-count cap",
    ):
        observer.load_observer_batch_journal_closure_bytes_v2(
            raw=closure.canonical_bytes,
            authority_binding=closure.authority_binding,
            known_stream_identities=(stream,),
        )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="batch-count cap",
    ):
        observer.verify_loaded_private_observer_batch_closure_v2(
            closure=closure,
            authority=authorization,
            namespace=namespace,
            authority_binding=closure.authority_binding,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
        )


def test_batch_canonical_replay_rejects_mutation_and_wrong_private_reveal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        generated,
        salt,
        namespace,
        authorization,
        _signer,
        session,
    ) = _open("batch-replay")
    stream = _streams(namespace).streams[0]
    session.observe_batch_v2(
        occurrence_id=_id("batch-replay-occurrence"),
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=19,
        accepted_draw_cap=19,
    )
    closure = session.close_batch_v2()
    document = loads_canonical_json(closure.canonical_bytes)
    document["entries"][0]["batch"]["transcript_commitment"] = _id(
        "forged-transcript"
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="signature|fields",
    ):
        observer.load_observer_batch_journal_closure_bytes_v2(
            raw=canonical_json_bytes(document),
            authority_binding=closure.authority_binding,
            known_stream_identities=(stream,),
        )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="reveal attestation",
    ):
        _replay_synthetic_batch_closure(
            closure=closure,
            authorization=authorization,
            namespace=namespace,
            private_salt=hashlib.sha512(b"wrong-batch-salt").digest(),
            private_environment=generated.secret_laws_for_commitment(),
        )
    verification = _replay_synthetic_batch_closure(
        closure=closure,
        authorization=authorization,
        namespace=namespace,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    assert (
        verification.to_document()["verification_result"]
        == "EXACT_BATCH_NATIVE_V2_REPLAY_VERIFIED"
    )
    binding = observer._require_exact_v2_binding(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
    )
    monkeypatch.setattr(
        observer,
        "_replay_exact_v2_authority_namespace",
        lambda **_kwargs: (authorization, namespace, binding),
    )
    canonical_closure, production_verification = (
        observer
        .replay_and_verify_private_observer_batch_journal_closure_v2(
            repository_root="/synthetic-production-authority",
            private_reveal_attestation_bytes=b"reveal",
            claimed_authorization_bytes=b"authorization",
            namespace_bytes=b"namespace",
            batch_closure_bytes=closure.canonical_bytes,
            known_stream_identities=(stream,),
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
        )
    )
    assert canonical_closure == closure
    assert canonical_closure is not closure
    assert production_verification.closure_id == canonical_closure.closure_id


def test_capability_replays_object_new_forgery_and_per_draw_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, namespace, _, _, session = _open("capability-forgery")
    stream = _streams(namespace).streams[0]
    capability = session.observe_v2(stream)
    forged = object.__new__(observer.V075SignedObservationRecordV2)
    for field_name in (
        "session_public_id",
        "authority_binding",
        "stream_identity",
        "sample",
    ):
        object.__setattr__(
            forged,
            field_name,
            getattr(capability.record, field_name),
        )
    object.__setattr__(
        forged,
        "observer_signature_hex",
        "00" * 256,
    )
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="signature|forged",
    ):
        observer.V075ObservationCapabilityV2(forged)

    _, _, namespace, _, _, capped = _open("per-draw-cap")
    stream = _streams(namespace).streams[0]
    monkeypatch.setattr(observer, "MAX_PER_DRAW_RECORDS_PER_SESSION", 1)
    capped.observe_v2(stream)
    private_stream = getattr(capped, "_streams")[stream.stream_id]
    assert private_stream.accepted_draw_count == 1
    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation,
        match="record cap",
    ):
        capped.observe_v2(stream)
    assert private_stream.accepted_draw_count == 1
