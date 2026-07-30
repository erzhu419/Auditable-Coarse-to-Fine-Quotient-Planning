from __future__ import annotations

from dataclasses import fields
import hashlib

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_live_incremental_model_authority_v2 as live
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_private_observer_boundary_v2 as fixture


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-live-incremental-model-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _stream_for_row(namespace, row, arm):
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
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=arm.value,
    )


def _semantic(
    marker: str,
    *,
    child: bool,
    validation: bool,
    support_freeze_id: str | None,
):
    role = (
        control.V075ControlledBatchSemanticAuthorityRoleV2
        .DYNAMIC_CHILD_DISCOVERY_INTENT
        if child
        else control.V075ControlledBatchSemanticAuthorityRoleV2
        .INITIAL_SCHEDULE_ROW_INTENT
    )
    schema = (
        control.V075ControlledBatchSemanticAuthoritySchemaV2
        .DYNAMIC_CHILD_DISCOVERY_INTENT
        if child
        else control.V075ControlledBatchSemanticAuthoritySchemaV2
        .INITIAL_SCHEDULE_ROW_INTENT
    )
    stage = (
        control.V075ControlledBatchStageV2.CHILD_VALIDATION
        if child and validation
        else control.V075ControlledBatchStageV2.CHILD_DISCOVERY
        if child
        else control.V075ControlledBatchStageV2.ROOT_VALIDATION
        if validation
        else control.V075ControlledBatchStageV2.ROOT_DISCOVERY
    )
    return {
        "semantic_authority_role": role,
        "semantic_authority_schema": schema,
        "semantic_artifact_id": _id(f"{marker}-artifact"),
        "semantic_verification_id": _id(f"{marker}-verification"),
        "stage": stage,
        "round_index": 1 if child else 0,
        "support_freeze_id": support_freeze_id,
    }


def _append_new_row(
    *,
    controller,
    stream,
    marker: str,
    child: bool,
):
    discovery_count = 64
    validation_count = 8_192 if child else 2_048
    validation_cap = 12_288 if child else 6_144
    discovery = controller.prepare_batch_intent_v2(
        stream_identity=stream,
        **_semantic(
            f"{marker}-discovery",
            child=child,
            validation=False,
            support_freeze_id=None,
        ),
        accepted_draw_start=1,
        accepted_draw_count=discovery_count,
        accepted_draw_cap=discovery_count,
    )
    discovery_append = controller.execute_batch_intent_v2(discovery)
    support = controller.freeze_complete_support_v2(
        discovery_append=discovery_append,
    )
    validation_stream = control.derive_v075_controlled_validation_stream_v2(
        support_freeze=support,
    )
    validation = controller.prepare_batch_intent_v2(
        stream_identity=validation_stream,
        **_semantic(
            f"{marker}-validation",
            child=child,
            validation=True,
            support_freeze_id=support.freeze_id,
        ),
        accepted_draw_start=1,
        accepted_draw_count=validation_count,
        accepted_draw_cap=validation_cap,
    )
    validation_append = controller.execute_batch_intent_v2(validation)
    return discovery_append, support, validation_append


def _freeze_epoch(controller, identity, *, parent=None):
    prefix = controller.verify_open_prefix_v2()
    return live.freeze_v075_live_incremental_model_epoch_v2(
        occurrence_identity=identity,
        controlled_appends=controller.controlled_appends,
        support_freezes=controller.support_freezes,
        open_prefix_verification=prefix,
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
        parent_epoch=parent,
    )


@pytest.fixture(scope="module")
def live_graph():
    generated, salt, namespace, authorization, signer = fixture._fixture(
        "live-incremental-model"
    )
    context = namespace.family.replicate_contexts[0]
    identity = (
        backend.freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=worker.V075WorkerArmV1.NO_PRIOR,
            occurrence_ordinal=1,
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )
    controller = control.open_v075_construction_controlled_private_observer_v2(
        authority=authorization,
        namespace=namespace,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id("session"),
        occurrence_identity=identity,
    )

    root = graph.root_catalogue_v1(context)
    root_row_ids = []
    for index, action in enumerate(root.actions):
        row = graph.observation_row_binding_v1(context, root, action)
        root_row_ids.append(row.row_binding_id)
        _append_new_row(
            controller=controller,
            stream=_stream_for_row(namespace, row, identity.arm),
            marker=f"root-{index}",
            child=False,
        )
    epoch1 = _freeze_epoch(controller, identity)

    child_descriptor = min(
        (
            descriptor
            for row in epoch1.model.rows
            for descriptor in row.support
            if not descriptor.failure and not descriptor.terminal
        ),
        key=lambda descriptor: len(
            graph.legal_action_triples_v1(
                context,
                descriptor.next_ranks,
                False,
            )
        ),
    )
    child_state = graph.V075SymbolicGraphStateV1(
        context,
        child_descriptor.next_ranks,
        False,
    )
    child_catalogue = graph.V075LegalActionCatalogueV1(
        context,
        child_state,
        1,
        graph.legal_action_triples_v1(
            context,
            child_state.ranks,
            False,
        ),
    )
    assert len(child_catalogue.actions) >= 2
    child_row_ids = []
    partial_rejected = False
    for index, action in enumerate(child_catalogue.actions):
        row = graph.observation_row_binding_v1(
            context,
            child_catalogue,
            action,
        )
        child_row_ids.append(row.row_binding_id)
        _append_new_row(
            controller=controller,
            stream=_stream_for_row(namespace, row, identity.arm),
            marker=f"child-{index}",
            child=True,
        )
        if index == 0:
            with pytest.raises(
                live.V075LiveIncrementalModelV2InvariantViolation
            ):
                _freeze_epoch(controller, identity, parent=epoch1)
            partial_rejected = True
    epoch2 = _freeze_epoch(controller, identity, parent=epoch1)

    promoted_source = epoch2.row_source_for_binding_v2(root_row_ids[0])
    promoted_last = epoch2.controlled_append_by_receipt_id_v2(
        promoted_source.validation_append_receipt_ids[-1]
    )
    promoted_freeze = epoch2.support_freeze_by_id_v2(
        promoted_source.support_freeze_id
    )
    promotion = controller.prepare_batch_intent_v2(
        stream_identity=promoted_last.batch.request.stream_identity,
        **_semantic(
            "root-promotion",
            child=False,
            validation=True,
            support_freeze_id=promoted_freeze.freeze_id,
        ),
        accepted_draw_start=promoted_source.validation_prefix_end + 1,
        accepted_draw_count=2_048,
        accepted_draw_cap=promoted_source.validation_draw_cap,
    )
    controller.execute_batch_intent_v2(promotion)
    epoch3 = _freeze_epoch(controller, identity, parent=epoch2)
    return {
        "identity": identity,
        "controller": controller,
        "root_row_ids": tuple(root_row_ids),
        "child_row_ids": tuple(child_row_ids),
        "epoch1": epoch1,
        "epoch2": epoch2,
        "epoch3": epoch3,
        "partial_rejected": partial_rejected,
    }


def _rows_by_binding(epoch):
    return {item.row_binding_id: item for item in epoch.model.rows}


def test_root_child_and_single_row_promotion_are_incremental(live_graph) -> None:
    epoch1 = live_graph["epoch1"]
    epoch2 = live_graph["epoch2"]
    epoch3 = live_graph["epoch3"]
    roots = set(live_graph["root_row_ids"])
    children = set(live_graph["child_row_ids"])
    assert set(epoch1.changed_row_binding_ids) == roots
    assert epoch1.reused_row_binding_ids == ()
    assert set(epoch2.changed_row_binding_ids) == children
    assert set(epoch2.reused_row_binding_ids) == roots
    assert set(epoch3.changed_row_binding_ids) == {
        live_graph["root_row_ids"][0]
    }
    assert set(epoch3.reused_row_binding_ids) == (
        roots | children
    ) - {live_graph["root_row_ids"][0]}
    assert live_graph["partial_rejected"] is True

    first = _rows_by_binding(epoch1)
    second = _rows_by_binding(epoch2)
    for row_id in roots:
        assert canonical_json_bytes(first[row_id].to_document()) == (
            canonical_json_bytes(second[row_id].to_document())
        )
    assert epoch3.to_document()["compiled_row_count"] == 1
    assert epoch3.to_document()["full_proof_recompute_count"] == 1
    assert epoch3.proof.model.model_id == epoch3.model.model_id


def test_operational_freeze_compiles_only_changed_rows(
    live_graph,
    monkeypatch,
) -> None:
    compiled = []
    original = live._compile_numerical_row

    def counted(**kwargs):
        compiled.append(
            kwargs["discovery"].batch.request.stream_identity.row_binding_id
        )
        return original(**kwargs)

    monkeypatch.setattr(live, "_compile_numerical_row", counted)
    controller = live_graph["controller"]
    replayed_epoch3 = live.freeze_v075_live_incremental_model_epoch_v2(
        occurrence_identity=live_graph["identity"],
        controlled_appends=controller.controlled_appends,
        support_freezes=controller.support_freezes,
        open_prefix_verification=controller.verify_open_prefix_v2(),
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
        parent_epoch=live_graph["epoch2"],
    )
    assert compiled == [live_graph["root_row_ids"][0]]
    assert replayed_epoch3.model_epoch_id == (
        live_graph["epoch3"].model_epoch_id
    )


def test_exact_epoch_bytes_and_complete_parent_replay(live_graph) -> None:
    epoch3 = live_graph["epoch3"]
    registry_size_before = len(live._TRUSTED_SAME_PROCESS_EPOCHS)
    replayed, verification = (
        live.verify_v075_live_incremental_model_epoch_bytes_v2(
            claimed=epoch3,
            claimed_bytes=epoch3.canonical_bytes,
        )
    )
    assert replayed.model_epoch_id == epoch3.model_epoch_id
    assert verification.numerical_proof_id == epoch3.proof.proof_id
    assert verification.parent_epoch_id == epoch3.parent_epoch_id
    assert len(live._TRUSTED_SAME_PROCESS_EPOCHS) == registry_size_before
    with pytest.raises(
        live.V075LiveIncrementalModelV2InvariantViolation
    ):
        live.verify_v075_live_incremental_model_epoch_bytes_v2(
            claimed=epoch3,
            claimed_bytes=epoch3.canonical_bytes + b" ",
        )


def test_missing_recap_stale_and_route_transplants_fail(live_graph) -> None:
    controller = live_graph["controller"]
    identity = live_graph["identity"]
    prefix = controller.verify_open_prefix_v2()
    with pytest.raises(live.V075LiveIncrementalModelV2InvariantViolation):
        live.freeze_v075_live_incremental_model_epoch_v2(
            occurrence_identity=identity,
            controlled_appends=controller.controlled_appends,
            support_freezes=controller.support_freezes[:-1],
            open_prefix_verification=prefix,
            route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
            parent_epoch=live_graph["epoch2"],
        )
    with pytest.raises(live.V075LiveIncrementalModelV2InvariantViolation):
        live.freeze_v075_live_incremental_model_epoch_v2(
            occurrence_identity=identity,
            controlled_appends=controller.controlled_appends,
            support_freezes=(
                *controller.support_freezes,
                controller.support_freezes[-1],
            ),
            open_prefix_verification=prefix,
            route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
            parent_epoch=live_graph["epoch2"],
        )
    with pytest.raises(live.V075LiveIncrementalModelV2InvariantViolation):
        live.freeze_v075_live_incremental_model_epoch_v2(
            occurrence_identity=identity,
            controlled_appends=controller.controlled_appends,
            support_freezes=controller.support_freezes,
            open_prefix_verification=prefix,
            route=planning.V075PlanningRouteV2.MATCHED_DIRECT_GROUND,
            parent_epoch=live_graph["epoch2"],
        )

    epoch1 = live_graph["epoch1"]
    original_prefix_appends = epoch1.open_prefix_verification.appends
    forged_append = object.__new__(control.V075ControlledBatchAppendV2)
    for item in fields(control.V075ControlledBatchAppendV2):
        object.__setattr__(
            forged_append,
            item.name,
            getattr(original_prefix_appends[0], item.name),
        )
    object.__setattr__(
        epoch1.open_prefix_verification,
        "appends",
        (forged_append, *original_prefix_appends[1:]),
    )
    with pytest.raises(live.V075LiveIncrementalModelV2InvariantViolation):
        live.freeze_v075_live_incremental_model_epoch_v2(
            occurrence_identity=identity,
            controlled_appends=controller.controlled_appends,
            support_freezes=controller.support_freezes,
            open_prefix_verification=prefix,
            route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
            parent_epoch=epoch1,
        )
    object.__setattr__(
        epoch1.open_prefix_verification,
        "appends",
        original_prefix_appends,
    )

    epoch2 = live_graph["epoch2"]
    stale_source = object.__new__(live.V075LiveModelRowSourceBindingV2)
    source = epoch2.row_sources[0]
    for item in fields(live.V075LiveModelRowSourceBindingV2):
        object.__setattr__(
            stale_source,
            item.name,
            (
                _id("stale-source")
                if item.name == "source_digest"
                else getattr(source, item.name)
            ),
        )
    forged_parent = object.__new__(live.V075LiveIncrementalModelEpochV2)
    for item in fields(live.V075LiveIncrementalModelEpochV2):
        object.__setattr__(
            forged_parent,
            item.name,
            (
                (stale_source, *epoch2.row_sources[1:])
                if item.name == "row_sources"
                else getattr(epoch2, item.name)
            ),
        )
    with pytest.raises(live.V075LiveIncrementalModelV2InvariantViolation):
        live.replay_v075_live_incremental_model_epoch_v2(forged_parent)

    # A registered factory object is also sealed against hostile in-place
    # object.__setattr__ mutation; cached content IDs alone are insufficient.
    object.__setattr__(
        epoch2,
        "row_sources",
        (stale_source, *epoch2.row_sources[1:]),
    )
    with pytest.raises(live.V075LiveIncrementalModelV2InvariantViolation):
        live.freeze_v075_live_incremental_model_epoch_v2(
            occurrence_identity=identity,
            controlled_appends=controller.controlled_appends,
            support_freezes=controller.support_freezes,
            open_prefix_verification=prefix,
            route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
            parent_epoch=epoch2,
        )

    nested_batch = epoch1.controlled_appends[0].batch
    object.__setattr__(
        nested_batch,
        "reward_sum",
        nested_batch.reward_sum + 1,
    )
    with pytest.raises(live.V075LiveIncrementalModelV2InvariantViolation):
        live.freeze_v075_live_incremental_model_epoch_v2(
            occurrence_identity=identity,
            controlled_appends=controller.controlled_appends,
            support_freezes=controller.support_freezes,
            open_prefix_verification=prefix,
            route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
            parent_epoch=epoch1,
        )

    epoch3 = live_graph["epoch3"]
    with pytest.raises(live.V075LiveIncrementalModelV2InvariantViolation):
        live.V075LiveIncrementalModelEpochV2(
            live._MODEL_EPOCH_ISSUER,
            epoch3.occurrence_identity,
            epoch3.controlled_appends,
            epoch3.support_freezes,
            epoch3.open_prefix_verification,
            epoch3.parent_epoch,
            epoch3.epoch_index,
            epoch3.context_id,
            epoch3.arm,
            epoch3.head_id,
            epoch3.route,
            epoch3.row_sources,
            epoch3.model,
            epoch2.proof,
            epoch3.changed_row_binding_ids,
            epoch3.reused_row_binding_ids,
        )


def test_production_entry_is_unconditionally_locked(monkeypatch) -> None:
    monkeypatch.setattr(live, "OFFICIAL_EXECUTION_ALLOWED", True)
    with pytest.raises(
        live.V075LiveIncrementalModelProductionV2NotReady
    ):
        live.execute_v075_production_live_incremental_model_v2(
            private_environment=object(),
        )
    assert live.PER_DRAW_RECORDS_ALLOWED is False
    assert live.PRIVATE_LAW_ACCESS_ALLOWED is False
