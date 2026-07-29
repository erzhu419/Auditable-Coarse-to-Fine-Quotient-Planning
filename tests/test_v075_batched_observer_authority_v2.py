from __future__ import annotations

from dataclasses import fields, replace
import hashlib
import inspect
from pathlib import Path
from typing import Any

import pytest

from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batched_observer_authority_v2 as batched
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_private_observer_boundary_v2 as fixture


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-batched-observer-v2-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


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


@pytest.fixture(scope="module")
def exact_v2_graph():
    return fixture._fixture("batched-consumer")


def _open_session(exact_v2_graph, marker: str):
    (
        generated,
        salt,
        namespace,
        authorization,
        signer,
    ) = exact_v2_graph
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
        session_external_id=_id(marker),
    )
    return session


def _identity(exact_v2_graph, *, ordinal: int = 0, context_index: int = 0):
    _generated, _salt, namespace, _authorization, _signer = exact_v2_graph
    return backend.freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
        namespace=namespace,
        context=namespace.family.replicate_contexts[context_index],
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        occurrence_ordinal=ordinal,
        threshold_profile=namespace.workload.threshold_profile,
        cap_profile=namespace.workload.cap_profile,
        source_prior_transport=None,
    )


def _stream(exact_v2_graph, *, context_index: int = 0):
    _generated, _salt, namespace, _authorization, _signer = exact_v2_graph
    streams = fixture._streams(namespace, context_index=context_index)
    return next(item for item in streams.streams if item.arm == "NO_PRIOR")


def _forged_occurrence_identity(
    original: backend.V075BatchNativeOccurrenceIdentityV1,
) -> backend.V075BatchNativeOccurrenceIdentityV1:
    forged = object.__new__(backend.V075BatchNativeOccurrenceIdentityV1)
    object.__setattr__(forged, "_issuer", object())
    object.__setattr__(
        forged,
        "target_tape_namespace_id",
        original.target_tape_namespace_id,
    )
    object.__setattr__(forged, "context_id", original.context_id)
    object.__setattr__(forged, "arm", original.arm)
    object.__setattr__(
        forged,
        "occurrence_ordinal",
        original.occurrence_ordinal + 1,
    )
    object.__setattr__(
        forged,
        "threshold_profile_id",
        original.threshold_profile_id,
    )
    object.__setattr__(
        forged,
        "cap_profile_id",
        original.cap_profile_id,
    )
    object.__setattr__(
        forged,
        "source_transport_id",
        original.source_transport_id,
    )
    object.__setattr__(forged, "_occurrence_id", original.occurrence_id)
    return forged


def _forged_closure_with_noncanonical_object_graph(
    original: observer.V075ObserverBatchJournalClosureV2,
) -> observer.V075ObserverBatchJournalClosureV2:
    forged = object.__new__(observer.V075ObserverBatchJournalClosureV2)
    object.__setattr__(forged, "occurrence_id", original.occurrence_id)
    object.__setattr__(
        forged,
        "session_public_id",
        original.session_public_id,
    )
    object.__setattr__(
        forged,
        "authority_binding",
        original.authority_binding,
    )
    object.__setattr__(forged, "entries", list(original.entries))
    object.__setattr__(
        forged,
        "observer_signature_hex",
        original.observer_signature_hex,
    )
    return forged


def _forged_batch_with_caller_minted_request(
    original: observer.V075SignedObservationBatchV2,
) -> observer.V075SignedObservationBatchV2:
    request_type = observer.V075BatchObservationRequestV2
    forged_request = object.__new__(request_type)
    for item in fields(request_type):
        object.__setattr__(
            forged_request,
            item.name,
            getattr(original.request, item.name),
        )
    object.__setattr__(forged_request, "_issuer", object())
    forged_batch = object.__new__(observer.V075SignedObservationBatchV2)
    for item in fields(observer.V075SignedObservationBatchV2):
        object.__setattr__(
            forged_batch,
            item.name,
            (
                forged_request
                if item.name == "request"
                else getattr(original, item.name)
            ),
        )
    return forged_batch


def _two_batch_closure(exact_v2_graph, marker: str = "two-batch"):
    identity = _identity(exact_v2_graph)
    session = _open_session(exact_v2_graph, marker)
    adapter = batched.bind_v075_construction_occurrence_batched_observer_v2(
        session=session,
        occurrence_identity=identity,
    )
    stream = _stream(exact_v2_graph)
    first = adapter.observe_batch_v2(
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=64,
        accepted_draw_cap=128,
    )
    second = adapter.observe_batch_v2(
        stream_identity=stream,
        accepted_draw_start=65,
        accepted_draw_count=64,
        accepted_draw_cap=128,
    )
    closure = adapter.close_v2()
    return identity, session, stream, first, second, closure


def test_exact_v2_adapter_is_batch_native_and_occurrence_bound(
    exact_v2_graph,
) -> None:
    _generated, _salt, _namespace, _authorization, signer = exact_v2_graph
    signed_before = len(signer.messages)
    identity, session, _stream, first, second, closure = _two_batch_closure(
        exact_v2_graph,
        "adapter",
    )

    assert first.request.occurrence_id == identity.occurrence_id
    assert second.request.accepted_draw_start == 65
    assert len(closure.entries) == 2
    assert len(session.batch_journal_entries) == 2
    assert session.journal_entries == ()
    assert len(signer.messages) - signed_before == 3
    assert closure.to_document()["accepted_draw_count"] == 128
    assert closure.to_document()["per_draw_journal_entries"] == 0
    keys = set(_walk_keys(closure.to_document()))
    assert "random_words" not in keys
    assert "record" not in keys
    assert "sample" not in keys


def test_public_batch_and_stream_sequence_are_independently_replayed(
    exact_v2_graph,
) -> None:
    _identity_value, _session, _stream_value, first, second, _closure = (
        _two_batch_closure(exact_v2_graph, "sequence")
    )
    public = batched.verify_v075_signed_observation_batch_v2(first)
    sequence = batched.verify_v075_observation_batch_sequence_v2(
        (first, second)
    )

    assert public.accepted_draw_count == 64
    assert public.to_document()["rsa_signatures_verified"] == 1
    assert public.to_document()["per_draw_records_verified"] == 0
    assert sequence.accepted_draw_count == 128
    assert sequence.batch_ids == (first.batch_id, second.batch_id)
    with pytest.raises(batched.V075BatchedObserverV2InvariantViolation):
        batched.verify_v075_observation_batch_sequence_v2((second, first))


def test_public_batch_and_sequence_reject_caller_minted_request_graph(
    exact_v2_graph,
) -> None:
    _identity_value, _session, _stream_value, first, second, _closure = (
        _two_batch_closure(exact_v2_graph, "forged-batch-request")
    )
    forged = _forged_batch_with_caller_minted_request(first)
    assert type(forged) is observer.V075SignedObservationBatchV2
    assert forged.canonical_bytes == first.canonical_bytes
    with pytest.raises(
        batched.V075BatchedObserverV2InvariantViolation,
        match="caller-minted",
    ):
        batched.verify_v075_signed_observation_batch_v2(forged)
    with pytest.raises(
        batched.V075BatchedObserverV2InvariantViolation,
        match="caller-minted",
    ):
        batched.verify_v075_observation_batch_sequence_v2(
            (forged, second)
        )


def test_construction_lineage_replays_aggregate_closure_without_promotion(
    exact_v2_graph,
) -> None:
    generated, salt, namespace, authorization, _signer = exact_v2_graph
    identity, _session, stream, _first, _second, closure = (
        _two_batch_closure(exact_v2_graph, "lineage")
    )
    lineage = batched.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=identity,
        closure=closure,
        authority=authorization,
        namespace=namespace,
        known_stream_identities=(stream,),
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    document = lineage.to_document()

    assert (
        lineage.scope
        is batched.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
    )
    assert lineage.accepted_draw_count == 128
    assert len(lineage.public_verifications) == 2
    assert len(lineage.sequence_verifications) == 1
    assert document["batch_count"] == 2
    assert document["occurrence_identity"] == identity.to_document()
    assert (
        document["occurrence_identity"]["threshold_profile_id"]
        == identity.threshold_profile_id
    )
    assert (
        document["occurrence_identity"]["cap_profile_id"]
        == identity.cap_profile_id
    )
    assert document["rsa_batch_signature_count"] == 2
    assert document["per_draw_record_count"] == 0
    assert document["per_draw_signature_count"] == 0
    assert document["production_authority_bytes_replayed"] is False
    assert document["official_execution_unlocked"] is False
    assert document["scientific_endpoint_credit_allowed"] is False
    with pytest.raises(batched.V075BatchedObserverV2InvariantViolation):
        replace(
            lineage,
            scope=(
                batched.V075BatchOccurrenceAuthorityScopeV2
                .PRODUCTION_BYTE_REPLAY
            ),
        )


def test_occurrence_context_and_arm_transplants_fail(exact_v2_graph) -> None:
    identity = _identity(exact_v2_graph)
    session = _open_session(exact_v2_graph, "foreign-stream")
    adapter = batched.bind_v075_construction_occurrence_batched_observer_v2(
        session=session,
        occurrence_identity=identity,
    )
    foreign_context_stream = _stream(exact_v2_graph, context_index=1)
    with pytest.raises(batched.V075BatchedObserverV2InvariantViolation):
        adapter.observe_batch_v2(
            stream_identity=foreign_context_stream,
            accepted_draw_start=1,
            accepted_draw_count=1,
            accepted_draw_cap=1,
        )

    streams = fixture._streams(exact_v2_graph[2])
    foreign_arm_stream = next(
        item for item in streams.streams if item.arm != "NO_PRIOR"
    )
    with pytest.raises(batched.V075BatchedObserverV2InvariantViolation):
        adapter.observe_batch_v2(
            stream_identity=foreign_arm_stream,
            accepted_draw_start=1,
            accepted_draw_count=1,
            accepted_draw_cap=1,
        )


def test_object_new_occurrence_identity_substitution_fails(
    exact_v2_graph,
) -> None:
    identity = _identity(exact_v2_graph)
    forged = _forged_occurrence_identity(identity)
    with pytest.raises(backend.V075BatchNativeBackendInvariantViolation):
        backend.replay_v075_batch_native_occurrence_identity_v1(forged)
    session = _open_session(exact_v2_graph, "forged-occurrence")
    with pytest.raises(batched.V075BatchedObserverV2InvariantViolation):
        batched.bind_v075_construction_occurrence_batched_observer_v2(
            session=session,
            occurrence_identity=forged,
        )


def test_object_new_closure_graph_is_replaced_by_canonical_byte_replay(
    exact_v2_graph,
) -> None:
    generated, salt, namespace, authorization, _signer = exact_v2_graph
    identity, _session, stream, _first, _second, closure = (
        _two_batch_closure(exact_v2_graph, "forged-closure")
    )
    forged = _forged_closure_with_noncanonical_object_graph(closure)
    assert type(forged) is observer.V075ObserverBatchJournalClosureV2
    assert type(forged.entries) is list
    assert forged.canonical_bytes == closure.canonical_bytes

    lineage = batched.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=identity,
        closure=forged,
        authority=authorization,
        namespace=namespace,
        known_stream_identities=(stream,),
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    assert lineage.closure is not forged
    assert type(lineage.closure.entries) is tuple
    assert lineage.closure.canonical_bytes == closure.canonical_bytes


def test_one_large_batch_has_constant_artifact_and_signature_cardinality(
    exact_v2_graph,
) -> None:
    _generated, _salt, _namespace, _authorization, signer = exact_v2_graph
    identity = _identity(exact_v2_graph, ordinal=1)
    session = _open_session(exact_v2_graph, "large-batch")
    adapter = batched.bind_v075_construction_occurrence_batched_observer_v2(
        session=session,
        occurrence_identity=identity,
    )
    signed_before = len(signer.messages)
    batch = adapter.observe_batch_v2(
        stream_identity=_stream(exact_v2_graph),
        accepted_draw_start=1,
        accepted_draw_count=4096,
        accepted_draw_cap=4096,
    )
    closure = adapter.close_v2()

    assert batch.request.accepted_draw_count == 4096
    assert sum(item.count for item in batch.outcomes) == 4096
    assert len(closure.entries) == 1
    assert len(signer.messages) - signed_before == 2
    assert closure.to_document()["per_draw_journal_entries"] == 0
    assert len(batch.canonical_bytes) < 256_000


def test_current_repository_not_ready_cannot_open_production_batch_session(
    exact_v2_graph,
) -> None:
    generated, salt, namespace, authorization, signer = exact_v2_graph
    identity = _identity(exact_v2_graph)
    signed_before = len(signer.messages)

    with pytest.raises(
        observer.V075PrivateObserverBoundaryV2InvariantViolation
    ):
        batched.open_v075_production_occurrence_batched_observer_v2(
            repository_root=Path.cwd(),
            private_reveal_attestation_bytes=(
                authorization.private_reveal_attestation.canonical_bytes
            ),
            claimed_authorization_bytes=authorization.canonical_bytes,
            namespace_bytes=namespace.canonical_bytes,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
            session_external_id=_id("production-not-ready"),
            occurrence_identity=identity,
        )
    assert len(signer.messages) == signed_before


def test_construction_lineage_is_rejected_by_production_verifier(
    exact_v2_graph,
) -> None:
    generated, salt, namespace, authorization, _signer = exact_v2_graph
    identity, _session, stream, _first, _second, closure = (
        _two_batch_closure(exact_v2_graph, "construction-reject")
    )
    lineage = batched.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=identity,
        closure=closure,
        authority=authorization,
        namespace=namespace,
        known_stream_identities=(stream,),
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    with pytest.raises(batched.V075BatchedObserverV2InvariantViolation):
        batched.verify_v075_production_batch_occurrence_lineage_v2(
            claimed_lineage=lineage,
            claimed_verification=object(),  # type: ignore[arg-type]
            repository_root=Path.cwd(),
            private_reveal_attestation_bytes=(
                authorization.private_reveal_attestation.canonical_bytes
            ),
            claimed_authorization_bytes=authorization.canonical_bytes,
            namespace_bytes=namespace.canonical_bytes,
            batch_closure_bytes=closure.canonical_bytes,
            known_stream_identities=(stream,),
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
        )


def test_consumer_has_no_per_draw_or_v1_authority_fallback() -> None:
    source = inspect.getsource(batched)
    assert ".observe_v2(" not in source
    assert "V075SignedObservationRecordV2" not in source
    assert "v075_private_observer_boundary_v1" not in source
    assert "v075_batched_observer_authority_v1" not in source
    assert "derive_public_target_tape_namespace_v1" not in source
    assert batched.PER_DRAW_RECORDS_ALLOWED is False
    assert batched.V1_AUTHORITY_PROJECTION_ALLOWED is False
    assert batched.V1_NAMESPACE_PROJECTION_ALLOWED is False
    assert batched.OFFICIAL_EXECUTION_UNLOCKED is False
    assert observer.MAX_BATCH_ACCEPTED_DRAW_COUNT >= 18_612_224
