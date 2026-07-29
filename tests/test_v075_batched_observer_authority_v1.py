from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import copy
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.h2_graph_transition_engine_v1 import (
    DeterministicH2GraphStreamV1,
    H2GraphActionV1,
)
from acfqp import v075_batched_observer_authority_v1 as batch
from acfqp import v075_private_observer_boundary_v1 as observer
from tests.test_v075_private_observer_boundary_v1 import (
    _ConstructionSigner,
    _fixture,
    _id,
    _namespace,
    _salt,
    _streams,
    _synthetic_environment,
)


_SHARED_MARKER = "batched-observer-shared-environment"
_SHARED_NAMESPACE = _namespace(_SHARED_MARKER)
_SHARED_SALT = _salt(_SHARED_MARKER)


def _setup(
    marker: str,
    *,
    context_index: int = 0,
    arm_index: int = 0,
):
    namespace = _SHARED_NAMESPACE
    authority = _fixture(namespace, marker)
    session = observer.open_construction_private_observer_fixture_v1(
        authority=authority,
        private_salt=_SHARED_SALT,
        private_environment=_synthetic_environment(),
        observer_signer=_ConstructionSigner(),
        session_external_id=_id("batched-observer-session-" + marker),
    )
    wrapped = batch.wrap_v075_construction_batched_observer_session_v1(
        session
    )
    stream = _streams(
        namespace,
        context_index=context_index,
    ).streams[arm_index]
    private_fixture = (
        batch.issue_v075_construction_batch_replay_environment_fixture_v1(
            namespace=namespace,
            private_salt=_SHARED_SALT,
            private_environment=_synthetic_environment(),
        )
    )
    return (
        namespace,
        authority,
        session,
        wrapped,
        stream,
        private_fixture,
    )


def _execute(
    marker: str = "batch",
    *,
    count: int = 128,
    cap: int = 512,
):
    values = _setup(marker)
    wrapped = values[3]
    stream = values[4]
    request = wrapped.issue_request_v1(
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=count,
        accepted_draw_cap=cap,
    )
    result = wrapped.execute_request_v1(request)
    return (*values, request, result)


def test_streaming_batch_has_exact_aggregates_one_signature_and_no_records() -> None:
    (
        _namespace_value,
        _authority,
        session,
        _wrapped,
        _stream,
        _private_fixture,
        request,
        result,
    ) = _execute("aggregate", count=512, cap=1_024)
    assert request.accepted_draw_start == 1
    assert request.accepted_draw_end == 512
    assert sum(item.count for item in result.outcomes) == 512
    assert result.reward_sum == sum(
        (item.reward_sum for item in result.outcomes),
        Fraction(0),
    )
    assert result.failure_count == sum(
        item.count for item in result.outcomes if item.failure
    )
    assert result.terminal_count == sum(
        item.count for item in result.outcomes if item.terminal
    )
    assert result.rejection_count == result.random_word_count - 512
    assert result.next_random_word_index == (
        result.first_random_word_index + result.random_word_count
    )
    assert session.journal_entries == ()
    document = result.to_document()
    assert document["per_draw_records_serialized"] is False
    assert document["individual_random_words_serialized"] is False
    assert document["private_law_serialized"] is False
    assert document["private_salt_serialized"] is False
    assert document["private_kernel_serialized"] is False
    verification = batch.verify_v075_signed_batched_observation_v1(result)
    assert verification.batch_id == result.batch_id
    assert verification.accepted_draw_count == 512


def test_batch_is_exactly_the_same_tape_as_per_draw_observer() -> None:
    marker = "same-tape"
    (
        _namespace_value,
        _authority,
        _session,
        _wrapped,
        stream,
        _private_fixture,
        request,
        result,
    ) = _execute(marker, count=96, cap=256)
    kernel = _session._kernels[stream.context_id]
    exact_stream = DeterministicH2GraphStreamV1(
        kernel=kernel,
        state=stream.row_binding.catalogue.state.to_kernel_state(),
        action=H2GraphActionV1(*stream.action),
        remaining_horizon=stream.row_binding.remaining_horizon,
        seed=stream.seed,
    )
    samples = tuple(exact_stream.draw() for _ in range(96))
    accumulator = batch._StreamingBatchAccumulatorV1(request)
    for sample in samples:
        accumulator.append(sample)
    assert accumulator.finish() == result.facts
    assert _session.journal_entries == ()


def test_same_request_recreated_in_fresh_session_is_byte_identical_not_reroll() -> None:
    first = _execute("no-reroll", count=80, cap=160)
    second = _execute("no-reroll", count=80, cap=160)
    assert first[-2] == second[-2]
    assert first[-2].request_id == second[-2].request_id
    assert first[-1] == second[-1]
    assert first[-1].batch_id == second[-1].batch_id
    assert first[-1].canonical_bytes == second[-1].canonical_bytes
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        first[3].execute_request_v1(first[-2])


def test_request_and_batch_canonical_loaders_replay_exactly() -> None:
    values = _setup("loader")
    wrapped = values[3]
    stream = values[4]
    request = wrapped.issue_request_v1(
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=64,
        accepted_draw_cap=128,
    )
    loaded_request = batch.load_v075_batched_observation_request_v1(
        raw=request.canonical_bytes,
        batched_session=wrapped,
        stream_identity=stream,
    )
    assert loaded_request == request
    result = wrapped.execute_request_v1(loaded_request)
    loaded_result = batch.load_v075_signed_batched_observation_v1(
        raw=result.canonical_bytes,
        request=request,
    )
    assert loaded_result == result
    assert loaded_result.canonical_bytes == result.canonical_bytes


def test_loader_rejects_reordered_outcomes_and_forged_aggregate() -> None:
    result = _execute("loader-attacks", count=256, cap=512)[-1]
    assert len(result.outcomes) > 1
    reordered = copy.deepcopy(result.to_document())
    reordered["outcomes"] = list(reversed(reordered["outcomes"]))
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.load_v075_signed_batched_observation_v1(
            raw=canonical_json_bytes(reordered),
            request=result.request,
        )
    tampered = copy.deepcopy(result.to_document())
    tampered["failure_count"] += 1
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.load_v075_signed_batched_observation_v1(
            raw=canonical_json_bytes(tampered),
            request=result.request,
        )


def test_request_gap_overlap_cap_change_and_stale_start_are_rejected() -> None:
    values = _setup("interval-attacks")
    wrapped = values[3]
    stream = values[4]
    first_request = wrapped.issue_request_v1(
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=20,
        accepted_draw_cap=100,
    )
    wrapped.execute_request_v1(first_request)
    for start in (1, 20, 22):
        with pytest.raises(batch.V075BatchedObserverInvariantViolation):
            wrapped.issue_request_v1(
                stream_identity=stream,
                accepted_draw_start=start,
                accepted_draw_count=10,
                accepted_draw_cap=100,
            )
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        wrapped.issue_request_v1(
            stream_identity=stream,
            accepted_draw_start=21,
            accepted_draw_count=10,
            accepted_draw_cap=101,
        )


def test_sequence_verifier_rejects_gap_overlap_reorder_and_arm_transplant() -> None:
    values = _setup("sequence")
    wrapped = values[3]
    stream = values[4]
    first_request = wrapped.issue_request_v1(
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=20,
        accepted_draw_cap=100,
    )
    first = wrapped.execute_request_v1(first_request)
    second_request = wrapped.issue_request_v1(
        stream_identity=stream,
        accepted_draw_start=21,
        accepted_draw_count=30,
        accepted_draw_cap=100,
    )
    second = wrapped.execute_request_v1(second_request)
    verified = batch.verify_v075_batched_observation_sequence_v1(
        (first, second)
    )
    assert verified.accepted_draw_count == 50
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.verify_v075_batched_observation_sequence_v1((second, first))
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.verify_v075_batched_observation_sequence_v1((first, first))

    other_stream = _streams(values[0]).streams[1]
    other_request = wrapped.issue_request_v1(
        stream_identity=other_stream,
        accepted_draw_start=1,
        accepted_draw_count=10,
        accepted_draw_cap=100,
    )
    other = wrapped.execute_request_v1(other_request)
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.verify_v075_batched_observation_sequence_v1((first, other))


def test_context_and_arm_transplant_break_signature_or_sequence() -> None:
    values = _setup("transplant")
    result = _execute("transplant", count=32, cap=64)[-1]
    other_arm = _streams(values[0]).streams[1]
    forged_request = batch._issue_request(
        session=values[2],
        stream_identity=other_arm,
        accepted_draw_start=1,
        accepted_draw_count=32,
        accepted_draw_cap=64,
    )
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        replace(result, request=forged_request)

    other_context = _streams(values[0], context_index=1).streams[0]
    context_request = batch._issue_request(
        session=values[2],
        stream_identity=other_context,
        accepted_draw_start=1,
        accepted_draw_count=32,
        accepted_draw_cap=64,
    )
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        replace(result, request=context_request)


def test_exact_private_replay_accepts_true_batch_and_rejects_resigned_false_one() -> None:
    values = _execute("private-replay", count=128, cap=256)
    authority = values[1]
    private_fixture = values[5]
    result = values[-1]
    verified = (
        batch.verify_v075_construction_batched_observation_private_replay_v1(
            claimed=result,
            authority=authority,
            private_environment=private_fixture,
        )
    )
    assert verified.batch_id == result.batch_id
    assert verified.replayed_draw_count == 128
    assert (
        verified.to_document()["verification_result"]
        == "EXACT_PRIVATE_INTERVAL_REPLAY_MATCH"
    )

    first = result.outcomes[0]
    forged_outcome = replace(
        first,
        next_ranks=(first.next_ranks[0] + 1, *first.next_ranks[1:]),
    )
    forged_outcomes = tuple(
        sorted(
            (forged_outcome, *result.outcomes[1:]),
            key=lambda item: item.outcome_id,
        )
    )
    forged_facts = batch._BatchFactsV1(
        forged_outcomes,
        result.reward_sum,
        result.failure_count,
        result.terminal_count,
        result.random_word_count,
        result.rejection_count,
        result.first_random_word_index,
        result.next_random_word_index,
        result.transcript_commitment,
    )
    signer = _ConstructionSigner()
    forged = batch.V075SignedBatchedObservationV1(
        result.request,
        forged_outcomes,
        forged_facts.reward_sum,
        forged_facts.failure_count,
        forged_facts.terminal_count,
        forged_facts.random_word_count,
        forged_facts.rejection_count,
        forged_facts.first_random_word_index,
        forged_facts.next_random_word_index,
        forged_facts.transcript_commitment,
        signer.sign_observer_evidence_v1(
            batch.batched_observation_signing_bytes_v1(
                request=result.request,
                facts=forged_facts,
            )
        ),
    )
    batch.verify_v075_signed_batched_observation_v1(forged)
    with pytest.raises(
        batch.V075BatchedObserverInvariantViolation,
        match="exact private replay",
    ):
        batch.verify_v075_construction_batched_observation_private_replay_v1(
            claimed=forged,
            authority=authority,
            private_environment=private_fixture,
        )


def test_construction_and_production_authority_paths_cannot_cross() -> None:
    values = _execute("scope-cross", count=16, cap=32)
    session = values[2]
    authority = values[1]
    result = values[-1]
    private_fixture = values[5]
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.wrap_v075_production_batched_observer_session_v1(session)
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.verify_v075_production_batched_observation_private_replay_v1(
            claimed=result,
            authority=authority,
            namespace=values[0],
            private_salt=_salt("scope-cross"),
            private_environment=private_fixture,
        )
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.verify_v075_construction_batched_observation_private_replay_v1(
            claimed=result,
            authority=SimpleNamespace(namespace=values[0]),
            private_environment=private_fixture,
        )


def test_duck_sessions_streams_signers_and_batches_are_rejected() -> None:
    values = _setup("duck")
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.wrap_v075_construction_batched_observer_session_v1(
            SimpleNamespace(authority_binding=values[2].authority_binding)
        )
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.load_v075_batched_observation_request_v1(
            raw=b"{}",
            batched_session=SimpleNamespace(),
            stream_identity=values[4],
        )
    wrapped = values[3]
    request = wrapped.issue_request_v1(
        stream_identity=values[4],
        accepted_draw_start=1,
        accepted_draw_count=8,
        accepted_draw_cap=16,
    )
    values[2]._signer = SimpleNamespace()
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        wrapped.execute_request_v1(request)
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        wrapped.issue_request_v1(
            stream_identity=values[4],
            accepted_draw_start=9,
            accepted_draw_count=1,
            accepted_draw_cap=16,
        )
    with pytest.raises(batch.V075BatchedObserverInvariantViolation):
        batch.verify_v075_signed_batched_observation_v1(SimpleNamespace())


def test_large_batch_stays_compact_and_retains_exact_draw_count() -> None:
    result = _execute("compact", count=5_000, cap=5_000)[-1]
    assert sum(item.count for item in result.outcomes) == 5_000
    assert len(result.canonical_bytes) < 100_000
    assert "random_words" not in result.to_document()
    assert "private_environment" not in repr(result.to_document())
