from __future__ import annotations

from dataclasses import fields, replace
import hashlib

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_open_session_support_authority_v2 as support_v2
from acfqp import v075_private_observer_boundary_v2 as observer_v2
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_private_observer_boundary_v2 as fixture


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-open-session-support-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


@pytest.fixture(scope="module")
def exact_v2_graph():
    return fixture._fixture("open-session-support")


def _identity(values, *, ordinal: int = 0):
    _generated, _salt, namespace, _authorization, _signer = values
    context = namespace.family.replicate_contexts[0]
    return backend.freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
        namespace=namespace,
        context=context,
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        occurrence_ordinal=ordinal,
        threshold_profile=namespace.workload.threshold_profile,
        cap_profile=namespace.workload.cap_profile,
        source_prior_transport=None,
    )


def _open_adapter(values, marker: str, *, ordinal: int = 0):
    generated, salt, namespace, authorization, signer = values
    binding = observer_v2._require_exact_v2_binding(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
    )
    session = observer_v2._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
        binding=binding,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id(marker),
    )
    adapter = batched_v2.bind_v075_construction_occurrence_batched_observer_v2(
        session=session,
        occurrence_identity=_identity(values, ordinal=ordinal),
    )
    return session, adapter


def _discovery_stream(values):
    _generated, _salt, namespace, _authorization, _signer = values
    return next(
        item
        for item in fixture._streams(namespace).streams
        if item.arm == worker.V075WorkerArmV1.NO_PRIOR.value
    )


def _controller(values, marker: str, *, ordinal: int = 0):
    session, adapter = _open_adapter(values, marker, ordinal=ordinal)
    controller = (
        support_v2.bind_v075_construction_open_session_support_controller_v2(
            adapter=adapter,
        )
    )
    return session, adapter, controller


def _discover_and_freeze(values, marker: str, *, ordinal: int = 0):
    session, adapter, controller = _controller(
        values,
        marker,
        ordinal=ordinal,
    )
    discovery = controller.observe_discovery_batch_v2(
        stream_identity=_discovery_stream(values),
        accepted_draw_count=64,
        accepted_draw_cap=64,
    )
    frozen = controller.freeze_complete_support_v2()
    return session, adapter, controller, discovery, frozen


def test_complete_support_and_validation_are_same_session_causal(
    exact_v2_graph,
) -> None:
    session, _adapter, controller, discovery, frozen = _discover_and_freeze(
        exact_v2_graph,
        "happy",
    )
    expected = {}
    for outcome in discovery.outcomes:
        state_id = graph.V075SymbolicGraphStateV1(
            discovery.request.stream_identity.row_binding.context,
            outcome.next_ranks,
            outcome.failure,
        ).state_id
        expected[state_id] = min(
            outcome.outcome_id,
            expected.get(state_id, outcome.outcome_id),
        )
    assert frozen.observed_state_ids == tuple(sorted(expected))
    assert {
        item.observed_state.state_id: item.discovery_outcome_id
        for item in frozen.evidence
    } == expected
    assert frozen.to_document()["caller_selected_support"] is False
    assert len(session.journal_entries) == 0

    stream = (
        support_v2.derive_v075_validation_stream_from_support_freeze_v2(
            support_freeze=frozen,
        )
    )
    assert stream.observer_epoch_index == 1
    assert stream.lane.value == "VALIDATION"
    first = controller.observe_validation_batch_v2(
        support_freeze=frozen,
        accepted_draw_count=16,
        accepted_draw_cap=32,
    )
    second = controller.observe_validation_batch_v2(
        support_freeze=frozen,
        accepted_draw_count=16,
        accepted_draw_cap=32,
    )
    assert first.request.accepted_draw_start == 1
    assert second.request.accepted_draw_start == 17
    assert first.request.stream_identity == second.request.stream_identity
    result = controller.close_and_reconcile_v2()
    assert len(result.receipts) == 3
    result_document = result.to_document()
    assert result_document[
        "all_batches_have_matching_trusted_receipt_records"
    ] is True
    assert result_document[
        "controller_execution_causality_cryptographically_proven"
    ] is False
    assert result_document["observer_signed_journal_heads_present"] is False
    assert result_document[
        "trusted_in_process_construction_control_flow"
    ] is True
    assert result_document["python_reference_exclusivity_relied_upon"] is True
    assert result.to_document()["per_draw_records_read"] == 0
    assert result.to_document()["private_law_access"] is False
    assert result.to_document()["official_execution_allowed"] is False
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation,
        match="identity differs from exact replay",
    ):
        replace(result, controller_id=_id("forged-controller"))


def test_freeze_verifier_rejects_omission_and_never_resigns(
    exact_v2_graph,
) -> None:
    _session, _adapter, _controller, discovery, frozen = (
        _discover_and_freeze(exact_v2_graph, "omit")
    )
    signer = exact_v2_graph[-1]
    signed_before = len(signer.messages)
    replayed = (
        support_v2.verify_v075_complete_aggregate_support_freeze_bytes_v2(
            discovery_batch=discovery,
            claimed_evidence=frozen.evidence,
            claimed_bytes=frozen.canonical_bytes,
        )
    )
    assert replayed.freeze_id == frozen.freeze_id
    assert len(signer.messages) == signed_before
    assert len(frozen.evidence) > 1
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation
    ):
        support_v2.verify_v075_complete_aggregate_support_freeze_bytes_v2(
            discovery_batch=discovery,
            claimed_evidence=frozen.evidence[:-1],
            claimed_bytes=frozen.canonical_bytes,
        )


def test_foreign_support_and_cross_session_freeze_are_rejected(
    exact_v2_graph,
) -> None:
    _s1, _a1, first, discovery1, frozen1 = _discover_and_freeze(
        exact_v2_graph,
        "cross-a",
        ordinal=1,
    )
    _s2, _a2, second, discovery2, frozen2 = _discover_and_freeze(
        exact_v2_graph,
        "cross-b",
        ordinal=1,
    )
    assert frozen1.freeze_id != frozen2.freeze_id
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation
    ):
        first.observe_validation_batch_v2(
            support_freeze=frozen2,
            accepted_draw_count=8,
            accepted_draw_cap=8,
        )
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation
    ):
        support_v2.verify_v075_complete_aggregate_support_freeze_bytes_v2(
            discovery_batch=discovery1,
            claimed_evidence=frozen2.evidence,
            claimed_bytes=frozen2.canonical_bytes,
        )
    second.observe_validation_batch_v2(
        support_freeze=frozen2,
        accepted_draw_count=8,
        accepted_draw_cap=8,
    )


def test_support_cannot_refreeze_after_validation(
    exact_v2_graph,
) -> None:
    _session, _adapter, controller, _discovery, frozen = (
        _discover_and_freeze(exact_v2_graph, "refreeze", ordinal=2)
    )
    controller.observe_validation_batch_v2(
        support_freeze=frozen,
        accepted_draw_count=8,
        accepted_draw_cap=16,
    )
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation
    ):
        controller.freeze_complete_support_v2()


def test_validation_cap_is_frozen_and_prefix_is_contiguous(
    exact_v2_graph,
) -> None:
    _session, _adapter, controller, _discovery, frozen = (
        _discover_and_freeze(exact_v2_graph, "continuation", ordinal=3)
    )
    first = controller.observe_validation_batch_v2(
        support_freeze=frozen,
        accepted_draw_count=5,
        accepted_draw_cap=20,
    )
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation
    ):
        controller.observe_validation_batch_v2(
            support_freeze=frozen,
            accepted_draw_count=5,
            accepted_draw_cap=21,
        )
    second = controller.observe_validation_batch_v2(
        support_freeze=frozen,
        accepted_draw_count=5,
        accepted_draw_cap=20,
    )
    assert first.request.accepted_draw_end == 5
    assert second.request.accepted_draw_start == 6


def test_stale_freeze_bytes_and_mutated_evidence_are_rejected(
    exact_v2_graph,
) -> None:
    _session, _adapter, _controller, discovery, frozen = (
        _discover_and_freeze(exact_v2_graph, "stale", ordinal=4)
    )
    document = loads_canonical_json(frozen.canonical_bytes)
    document["freeze_id"] = _id("wrong-freeze")
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation
    ):
        support_v2.verify_v075_complete_aggregate_support_freeze_bytes_v2(
            discovery_batch=discovery,
            claimed_evidence=frozen.evidence,
            claimed_bytes=canonical_json_bytes(document),
        )
    original = frozen.evidence[0]
    changed = object.__new__(type(original))
    for item in fields(type(original)):
        object.__setattr__(
            changed,
            item.name,
            (
                original.discovery_outcome_count + 1
                if item.name == "discovery_outcome_count"
                else getattr(original, item.name)
            ),
        )
    with pytest.raises(Exception):
        support_v2.verify_v075_complete_aggregate_support_freeze_bytes_v2(
            discovery_batch=discovery,
            claimed_evidence=(changed, *frozen.evidence[1:]),
            claimed_bytes=frozen.canonical_bytes,
        )


def test_direct_underlying_adapter_use_poisoned_receipt_reconciliation(
    exact_v2_graph,
) -> None:
    _session, adapter, controller, _discovery, frozen = (
        _discover_and_freeze(exact_v2_graph, "direct", ordinal=5)
    )
    validation = (
        support_v2.derive_v075_validation_stream_from_support_freeze_v2(
            support_freeze=frozen,
        )
    )
    adapter.observe_batch_v2(
        stream_identity=validation,
        accepted_draw_start=1,
        accepted_draw_count=4,
        accepted_draw_cap=8,
    )
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation,
        match="outside the controller",
    ):
        controller.observe_validation_batch_v2(
            support_freeze=frozen,
            accepted_draw_count=4,
            accepted_draw_cap=8,
        )
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation
    ):
        controller.close_and_reconcile_v2()


def test_controller_rejects_rebinding_and_nonunused_underlying_state(
    exact_v2_graph,
) -> None:
    _session, adapter = _open_adapter(
        exact_v2_graph,
        "rebind",
        ordinal=6,
    )
    support_v2.bind_v075_construction_open_session_support_controller_v2(
        adapter=adapter,
    )
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation
    ):
        support_v2.bind_v075_construction_open_session_support_controller_v2(
            adapter=adapter,
        )

    _session2, adapter2 = _open_adapter(
        exact_v2_graph,
        "already-used",
        ordinal=7,
    )
    adapter2.observe_batch_v2(
        stream_identity=_discovery_stream(exact_v2_graph),
        accepted_draw_start=1,
        accepted_draw_count=4,
        accepted_draw_cap=4,
    )
    with pytest.raises(
        support_v2.V075OpenSessionSupportV2InvariantViolation
    ):
        support_v2.bind_v075_construction_open_session_support_controller_v2(
            adapter=adapter2,
        )


def test_production_entry_and_claims_remain_hard_locked() -> None:
    with pytest.raises(
        support_v2.V075OpenSessionSupportProductionV2NotReady
    ):
        support_v2.open_v075_production_open_session_support_controller_v2(
            repository_root="not-read"
        )
    assert support_v2.PROPOSED_CONTRACT_VERSION == "1.53.0"
    assert support_v2.OFFICIAL_EXECUTION_ALLOWED is False
    assert support_v2.PRODUCTION_AUTHORIZING is False
    assert support_v2.PER_DRAW_REPLAY_ALLOWED is False
    assert support_v2.PRIVATE_LAW_ACCESS_ALLOWED is False
    assert support_v2.TERMINAL_CLASS == "ATTEMPT_CLOSURE_NONCERTIFICATE"
