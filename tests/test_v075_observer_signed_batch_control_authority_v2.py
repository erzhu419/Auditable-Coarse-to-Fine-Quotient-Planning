from __future__ import annotations

from dataclasses import fields, replace
import hashlib

import pytest

from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_private_observer_boundary_v2 as fixture


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-signed-batch-control-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


@pytest.fixture(scope="module")
def exact_v2_graph():
    return fixture._fixture("observer-signed-batch-control")


def _identity(values, *, ordinal: int):
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


def _stream(values):
    _generated, _salt, namespace, _authorization, _signer = values
    return next(
        item
        for item in fixture._streams(namespace).streams
        if item.arm == worker.V075WorkerArmV1.NO_PRIOR.value
    )


def _controller(values, marker: str, *, ordinal: int):
    generated, salt, namespace, authorization, signer = values
    return control.open_v075_construction_controlled_private_observer_v2(
        authority=authorization,
        namespace=namespace,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id(marker),
        occurrence_identity=_identity(values, ordinal=ordinal),
    )


def _semantic(marker: str):
    return {
        "semantic_authority_role": (
            control.V075ControlledBatchSemanticAuthorityRoleV2
            .INITIAL_SCHEDULE_ROW_INTENT
        ),
        "semantic_authority_schema": (
            control.V075ControlledBatchSemanticAuthoritySchemaV2
            .INITIAL_SCHEDULE_ROW_INTENT
        ),
        "semantic_artifact_id": _id(f"{marker}-semantic-artifact"),
        "semantic_verification_id": _id(
            f"{marker}-semantic-verification"
        ),
        "stage": control.V075ControlledBatchStageV2.ROOT_DISCOVERY,
        "round_index": 0,
        "support_freeze_id": None,
    }


def test_signed_zero_head_controlled_appends_and_closure_reconcile(
    exact_v2_graph,
) -> None:
    controller = _controller(exact_v2_graph, "happy", ordinal=0)
    zero = controller.current_signed_head
    assert zero.entry_count == 0
    assert zero.tail_entry_id is None
    assert zero.stream_frontiers == ()
    assert zero.to_document()["zero_head"] is True

    stream = _stream(exact_v2_graph)
    shared_semantic_authority = _semantic("happy-shared")
    first_intent = controller.prepare_batch_intent_v2(
        stream_identity=stream,
        **shared_semantic_authority,
        accepted_draw_start=1,
        accepted_draw_count=5,
        accepted_draw_cap=12,
    )
    assert controller.current_signed_head == zero
    first = controller.execute_batch_intent_v2(first_intent)
    assert first.receipt.prior_head_id == zero.head_id
    assert first.receipt.intent_id == first_intent.intent_id
    assert first.receipt.semantic_authority_binding_id == (
        first_intent.semantic_authority.binding_id
    )
    assert first.receipt.batch_id == first.batch.batch_id
    assert first.receipt.resulting_head_id == first.resulting_head.head_id
    assert first.resulting_head.stream_frontiers[0].accepted_draw_end == 5

    second_intent = controller.prepare_batch_intent_v2(
        stream_identity=stream,
        **shared_semantic_authority,
        accepted_draw_start=6,
        accepted_draw_count=7,
        accepted_draw_cap=12,
    )
    second = controller.execute_batch_intent_v2(second_intent)
    assert second.resulting_head.entry_count == 2
    assert second.resulting_head.tail_entry_id == (
        second.receipt.journal_entry_id
    )
    assert second.resulting_head.total_accepted_draw_count == 12
    assert second.resulting_head.stream_frontiers[0].accepted_draw_end == 12
    assert second.resulting_head.stream_frontiers[0].batch_count == 2

    closed = controller.close_and_reconcile_v2()
    assert closed.batch_closure.closure_id == (
        closed.control_closure.batch_closure_id
    )
    assert closed.control_closure.head_ids == tuple(
        item.head_id for item in closed.heads
    )
    assert len(set(closed.control_closure.semantic_authority_binding_ids)) == 1
    assert closed.reconciliation.append_count == 2
    assert closed.reconciliation.total_accepted_draw_count == 12
    assert (
        control.verify_v075_controlled_batch_journal_closure_v2(
            batch_closure=closed.batch_closure,
            heads=closed.heads,
            appends=closed.appends,
            control_closure=closed.control_closure,
        )
        == closed.reconciliation
    )
    document = closed.to_document()
    assert document["official_execution_allowed"] is False
    assert document["process_isolation_provided"] is False
    assert document["python_wrapper_is_not_process_isolation"] is True

    forged_head = object.__new__(type(closed.heads[1]))
    for item in fields(type(closed.heads[1])):
        object.__setattr__(
            forged_head,
            item.name,
            (
                closed.heads[1].entry_count + 1
                if item.name == "entry_count"
                else getattr(closed.heads[1], item.name)
            ),
        )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation
    ):
        control.verify_v075_controlled_batch_journal_closure_v2(
            batch_closure=closed.batch_closure,
            heads=(closed.heads[0], forged_head, closed.heads[2]),
            appends=closed.appends,
            control_closure=closed.control_closure,
        )


def test_stale_reused_gapped_and_cap_changed_intents_are_rejected(
    exact_v2_graph,
) -> None:
    controller = _controller(exact_v2_graph, "stale", ordinal=1)
    stream = _stream(exact_v2_graph)
    intent = controller.prepare_batch_intent_v2(
        stream_identity=stream,
        **_semantic("stale-first"),
        accepted_draw_start=1,
        accepted_draw_count=3,
        accepted_draw_cap=9,
    )
    controller.execute_batch_intent_v2(intent)
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="stale, reused, or unregistered",
    ):
        controller.execute_batch_intent_v2(intent)
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="gapped or overlaps",
    ):
        controller.prepare_batch_intent_v2(
            stream_identity=stream,
            **_semantic("stale-gap"),
            accepted_draw_start=5,
            accepted_draw_count=2,
            accepted_draw_cap=9,
        )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="changes a frozen stream cap",
    ):
        controller.prepare_batch_intent_v2(
            stream_identity=stream,
            **_semantic("stale-cap"),
            accepted_draw_start=4,
            accepted_draw_count=2,
            accepted_draw_cap=10,
        )


def test_cross_occurrence_intent_transplant_is_rejected(
    exact_v2_graph,
) -> None:
    first = _controller(exact_v2_graph, "cross-a", ordinal=2)
    second = _controller(exact_v2_graph, "cross-b", ordinal=3)
    intent = first.prepare_batch_intent_v2(
        stream_identity=_stream(exact_v2_graph),
        **_semantic("cross"),
        accepted_draw_start=1,
        accepted_draw_count=2,
        accepted_draw_cap=2,
    )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="stale, reused, or unregistered",
    ):
        second.execute_batch_intent_v2(intent)


def test_out_of_band_raw_append_is_detected_before_controlled_draw(
    exact_v2_graph,
) -> None:
    controller = _controller(exact_v2_graph, "raw", ordinal=4)
    raw_adapter = getattr(
        controller,
        "_V075ConstructionControlledPrivateObserverV2__adapter",
    )
    raw_adapter.observe_batch_v2(
        stream_identity=_stream(exact_v2_graph),
        accepted_draw_start=1,
        accepted_draw_count=2,
        accepted_draw_cap=2,
    )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="raw or out-of-band",
    ):
        controller.prepare_batch_intent_v2(
            stream_identity=_stream(exact_v2_graph),
            **_semantic("raw"),
            accepted_draw_start=1,
            accepted_draw_count=1,
            accepted_draw_cap=1,
        )


def test_signature_tampering_and_production_use_remain_rejected(
    exact_v2_graph,
) -> None:
    controller = _controller(exact_v2_graph, "tamper", ordinal=5)
    intent = controller.prepare_batch_intent_v2(
        stream_identity=_stream(exact_v2_graph),
        **_semantic("tamper"),
        accepted_draw_start=1,
        accepted_draw_count=2,
        accepted_draw_cap=2,
    )
    append = controller.execute_batch_intent_v2(intent)
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="signature is invalid",
    ):
        replace(
            append.receipt,
            resulting_head_id=_id("forged-resulting-head"),
        )
    with pytest.raises(
        control.V075ObserverSignedBatchControlProductionV2NotReady
    ):
        control.open_v075_production_controlled_private_observer_v2()
    assert not hasattr(controller, "observe_batch_v2")
    assert control.PROPOSED_CONTRACT_VERSION == "1.54.0"
    assert control.OFFICIAL_EXECUTION_ALLOWED is False
    assert control.PRODUCTION_AUTHORIZING is False
    assert control.PROCESS_ISOLATION_PROVIDED is False
    assert control.PUBLIC_PRIVATE_SESSION_API_EXPOSED is False
    assert control.TERMINAL_CLASS == "ATTEMPT_CLOSURE_NONCERTIFICATE"


def test_semantic_role_stage_round_and_support_binding_is_typed(
    exact_v2_graph,
) -> None:
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="role, schema, stage, round, or support-freeze",
    ):
        control.freeze_v075_controlled_batch_semantic_authority_v2(
            role=(
                control.V075ControlledBatchSemanticAuthorityRoleV2
                .DYNAMIC_CHILD_DISCOVERY_INTENT
            ),
            schema=(
                control.V075ControlledBatchSemanticAuthoritySchemaV2
                .DYNAMIC_CHILD_DISCOVERY_INTENT
            ),
            semantic_artifact_id=_id("child-artifact"),
            semantic_verification_id=_id("child-verification"),
            stage=control.V075ControlledBatchStageV2.CHILD_DISCOVERY,
            round_index=0,
            support_freeze_id=None,
        )
    controller = _controller(exact_v2_graph, "lane", ordinal=6)
    invalid_lane = _semantic("lane")
    invalid_lane.update(
        stage=control.V075ControlledBatchStageV2.ROOT_VALIDATION,
        support_freeze_id=_id("lane-support-freeze"),
    )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="stage and stream lane disagree",
    ):
        controller.prepare_batch_intent_v2(
            stream_identity=_stream(exact_v2_graph),
            **invalid_lane,
            accepted_draw_start=1,
            accepted_draw_count=1,
            accepted_draw_cap=1,
        )
