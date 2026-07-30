from __future__ import annotations

from dataclasses import fields, replace
import hashlib

import pytest

from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_public_graph_semantics_v1 as graph
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


def _streams(values):
    _generated, _salt, namespace, _authorization, _signer = values
    context = namespace.family.replicate_contexts[0]
    catalogue = graph.root_catalogue_v1(context)
    result = []
    for action in catalogue.actions:
        row = graph.observation_row_binding_v1(
            context,
            catalogue,
            action,
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
        result.append(
            next(
                item
                for item in graph.freeze_five_arm_stream_set_v1(
                    pairing
                ).streams
                if item.arm == worker.V075WorkerArmV1.NO_PRIOR.value
            )
        )
    return tuple(result)


def _stream(values):
    return _streams(values)[0]


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


def _semantic(
    marker: str,
    *,
    stage: control.V075ControlledBatchStageV2 = (
        control.V075ControlledBatchStageV2.ROOT_DISCOVERY
    ),
    support_freeze_id: str | None = None,
):
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
        "stage": stage,
        "round_index": 0,
        "support_freeze_id": support_freeze_id,
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
        accepted_draw_cap=5,
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

    support = controller.freeze_complete_support_v2(
        discovery_append=first,
    )
    validation_stream = controller.derive_validation_stream_v2(
        support_freeze=support,
    )
    second_intent = controller.prepare_batch_intent_v2(
        stream_identity=validation_stream,
        **_semantic(
            "happy-validation",
            stage=control.V075ControlledBatchStageV2.ROOT_VALIDATION,
            support_freeze_id=support.freeze_id,
        ),
        accepted_draw_start=1,
        accepted_draw_count=7,
        accepted_draw_cap=7,
    )
    second = controller.execute_batch_intent_v2(second_intent)
    assert second.resulting_head.entry_count == 2
    assert second.resulting_head.tail_entry_id == (
        second.receipt.journal_entry_id
    )
    assert second.resulting_head.total_accepted_draw_count == 12
    by_stream = {
        item.stream_id: item
        for item in second.resulting_head.stream_frontiers
    }
    assert by_stream[stream.stream_id].accepted_draw_end == 5
    assert by_stream[validation_stream.stream_id].accepted_draw_end == 7
    assert all(item.batch_count == 1 for item in by_stream.values())

    closed = controller.close_and_reconcile_v2()
    assert closed.batch_closure.closure_id == (
        closed.control_closure.batch_closure_id
    )
    assert closed.control_closure.head_ids == tuple(
        item.head_id for item in closed.heads
    )
    assert len(set(closed.control_closure.semantic_authority_binding_ids)) == 2
    assert closed.reconciliation.append_count == 2
    assert closed.reconciliation.total_accepted_draw_count == 12
    assert (
        control.verify_v075_controlled_batch_journal_closure_v2(
            batch_closure=closed.batch_closure,
            heads=closed.heads,
            appends=closed.appends,
            control_closure=closed.control_closure,
            support_freezes=closed.support_freezes,
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
        accepted_draw_cap=3,
    )
    controller.execute_batch_intent_v2(intent)
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="stale, reused, or unregistered",
    ):
        controller.execute_batch_intent_v2(intent)
    support = controller.freeze_complete_support_v2(
        discovery_append=controller.controlled_appends[0],
    )
    validation_stream = controller.derive_validation_stream_v2(
        support_freeze=support,
    )
    validation_semantic = _semantic(
        "stale-validation",
        stage=control.V075ControlledBatchStageV2.ROOT_VALIDATION,
        support_freeze_id=support.freeze_id,
    )
    validation_intent = controller.prepare_batch_intent_v2(
        stream_identity=validation_stream,
        **validation_semantic,
        accepted_draw_start=1,
        accepted_draw_count=3,
        accepted_draw_cap=9,
    )
    controller.execute_batch_intent_v2(validation_intent)
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="gapped or overlaps",
    ):
        controller.prepare_batch_intent_v2(
            stream_identity=validation_stream,
            **validation_semantic,
            accepted_draw_start=5,
            accepted_draw_count=2,
            accepted_draw_cap=9,
        )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="changes a frozen stream cap",
    ):
        controller.prepare_batch_intent_v2(
            stream_identity=validation_stream,
            **validation_semantic,
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


def test_multi_row_support_freeze_open_prefix_and_validation(
    exact_v2_graph,
) -> None:
    controller = _controller(exact_v2_graph, "multi-row", ordinal=7)
    signer = exact_v2_graph[-1]
    streams_by_row = {}
    for stream in _streams(exact_v2_graph):
        streams_by_row.setdefault(stream.row_binding_id, stream)
    discovery_streams = tuple(streams_by_row.values())[:2]
    assert len(discovery_streams) == 2

    freezes = []
    for index, stream in enumerate(discovery_streams):
        intent = controller.prepare_batch_intent_v2(
            stream_identity=stream,
            **_semantic(f"multi-discovery-{index}"),
            accepted_draw_start=1,
            accepted_draw_count=4,
            accepted_draw_cap=4,
        )
        append = controller.execute_batch_intent_v2(intent)
        support = controller.freeze_complete_support_v2(
            discovery_append=append,
        )
        assert support.discovery_append_receipt_id == (
            append.receipt.receipt_id
        )
        assert support.frozen_at_head == controller.current_signed_head
        freezes.append(support)

    signed_before = len(signer.messages)
    prefix = control.verify_v075_open_controlled_batch_prefix_v2(
        heads=controller.signed_heads,
        appends=controller.controlled_appends,
        support_freezes=controller.support_freezes,
    )
    assert len(signer.messages) == signed_before
    assert prefix.append_count == 2
    assert prefix.support_freeze_ids == tuple(
        item.freeze_id for item in controller.support_freezes
    )
    assert prefix.to_document()["verifier_closed_session"] is False
    assert prefix.to_document()["verifier_resigned_artifacts"] is False
    assert prefix.to_document()["session_open_state_verified"] is False

    for index, support in enumerate(freezes):
        validation = controller.derive_validation_stream_v2(
            support_freeze=support,
        )
        intent = controller.prepare_batch_intent_v2(
            stream_identity=validation,
            **_semantic(
                f"multi-validation-{index}",
                stage=control.V075ControlledBatchStageV2.ROOT_VALIDATION,
                support_freeze_id=support.freeze_id,
            ),
            accepted_draw_start=1,
            accepted_draw_count=3,
            accepted_draw_cap=3,
        )
        controller.execute_batch_intent_v2(intent)

    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="duplicate, foreign, non-discovery, or after validation",
    ):
        controller.freeze_complete_support_v2(
            discovery_append=freezes[0].discovery_append,
        )
    closed = controller.close_and_reconcile_v2()
    assert closed.reconciliation.append_count == 4
    assert closed.reconciliation.total_accepted_draw_count == 14
    assert closed.control_closure.support_freeze_ids == tuple(
        item.freeze_id for item in closed.support_freezes
    )
    assert closed.to_document()["support_freeze_count"] == 2


def test_support_freeze_rejects_foreign_duplicate_and_forged_prefix(
    exact_v2_graph,
) -> None:
    first = _controller(exact_v2_graph, "freeze-a", ordinal=8)
    second = _controller(exact_v2_graph, "freeze-b", ordinal=9)
    stream = _stream(exact_v2_graph)
    first_intent = first.prepare_batch_intent_v2(
        stream_identity=stream,
        **_semantic("freeze-a"),
        accepted_draw_start=1,
        accepted_draw_count=4,
        accepted_draw_cap=4,
    )
    first_append = first.execute_batch_intent_v2(first_intent)
    support = first.freeze_complete_support_v2(
        discovery_append=first_append,
    )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="duplicate, foreign, non-discovery, or after validation",
    ):
        first.freeze_complete_support_v2(
            discovery_append=first_append,
        )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="duplicate, foreign, non-discovery, or after validation",
    ):
        second.freeze_complete_support_v2(
            discovery_append=first_append,
        )

    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation
    ):
        replace(
            support,
            evidence=support.evidence[:-1],
        )

    forged_head = object.__new__(type(first.current_signed_head))
    for item in fields(type(first.current_signed_head)):
        object.__setattr__(
            forged_head,
            item.name,
            (
                first.current_signed_head.entry_count + 1
                if item.name == "entry_count"
                else getattr(first.current_signed_head, item.name)
            ),
        )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation
    ):
        control.verify_v075_open_controlled_batch_prefix_v2(
            heads=(first.signed_heads[0], forged_head),
            appends=first.controlled_appends,
            support_freezes=first.support_freezes,
        )


def test_same_row_discovery_is_single_before_and_after_support_freeze(
    exact_v2_graph,
) -> None:
    controller = _controller(exact_v2_graph, "single-discovery", ordinal=10)
    stream = _stream(exact_v2_graph)
    first_intent = controller.prepare_batch_intent_v2(
        stream_identity=stream,
        **_semantic("single-discovery-first"),
        accepted_draw_start=1,
        accepted_draw_count=1,
        accepted_draw_cap=2,
    )
    first_append = controller.execute_batch_intent_v2(first_intent)

    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="sole discovery append",
    ):
        controller.prepare_batch_intent_v2(
            stream_identity=stream,
            **_semantic("single-discovery-before-freeze"),
            accepted_draw_start=2,
            accepted_draw_count=1,
            accepted_draw_cap=2,
        )

    support = controller.freeze_complete_support_v2(
        discovery_append=first_append,
    )
    assert support.discovery_append_receipt_id == first_append.receipt.receipt_id
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="cannot continue after row freeze",
    ):
        controller.prepare_batch_intent_v2(
            stream_identity=stream,
            **_semantic("single-discovery-after-freeze"),
            accepted_draw_start=2,
            accepted_draw_count=1,
            accepted_draw_cap=2,
        )
    prefix = controller.verify_open_prefix_v2()
    assert prefix.append_count == 1
    assert prefix.support_freeze_ids == (support.freeze_id,)


def test_owned_artifact_copy_cannot_bypass_exact_replay(
    exact_v2_graph,
) -> None:
    controller = _controller(exact_v2_graph, "copy-tamper", ordinal=11)
    stream = _stream(exact_v2_graph)
    discovery_intent = controller.prepare_batch_intent_v2(
        stream_identity=stream,
        **_semantic("copy-tamper-discovery"),
        accepted_draw_start=1,
        accepted_draw_count=2,
        accepted_draw_cap=2,
    )
    discovery_append = controller.execute_batch_intent_v2(discovery_intent)

    forged_batch = object.__new__(type(discovery_append.batch))
    signature = discovery_append.batch.observer_signature_hex
    bad_signature = (
        ("0" if signature[0] != "0" else "1") + signature[1:]
    )
    for item in fields(type(discovery_append.batch)):
        object.__setattr__(
            forged_batch,
            item.name,
            (
                bad_signature
                if item.name == "observer_signature_hex"
                else getattr(discovery_append.batch, item.name)
            ),
        )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation
    ):
        replace(discovery_append, batch=forged_batch)

    support = controller.freeze_complete_support_v2(
        discovery_append=discovery_append,
    )
    validation_stream = controller.derive_validation_stream_v2(
        support_freeze=support,
    )
    validation_intent = controller.prepare_batch_intent_v2(
        stream_identity=validation_stream,
        **_semantic(
            "copy-tamper-validation",
            stage=control.V075ControlledBatchStageV2.ROOT_VALIDATION,
            support_freeze_id=support.freeze_id,
        ),
        accepted_draw_start=1,
        accepted_draw_count=2,
        accepted_draw_cap=2,
    )
    controller.execute_batch_intent_v2(validation_intent)
    prefix = controller.verify_open_prefix_v2()
    with pytest.raises((TypeError, ValueError)):
        replace(
            prefix,
            support_freezes=(),
            support_freeze_ids=(),
        )

    closed = controller.close_and_reconcile_v2()
    forged_reconciliation = replace(
        closed.reconciliation,
        append_count=999,
        total_accepted_draw_count=999,
    )
    with pytest.raises(
        control.V075ObserverSignedBatchControlV2InvariantViolation,
        match="differs from replay",
    ):
        replace(
            closed,
            reconciliation=forged_reconciliation,
        )
