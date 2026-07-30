from __future__ import annotations

from dataclasses import fields, replace
from fractions import Fraction
import hashlib

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_batch_native_planning_backend_v2 as manual_fixture
from tests import test_v075_live_incremental_model_authority_v2 as live_fixture
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-live-dynamic-acquisition-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _root_epoch(
    *,
    generated,
    salt,
    namespace,
    authorization,
    signer,
    context,
    marker: str,
):
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
        session_external_id=_id(f"{marker}-session"),
        occurrence_identity=identity,
    )
    catalogue = graph.root_catalogue_v1(context)
    for ordinal, action in enumerate(catalogue.actions):
        row = graph.observation_row_binding_v1(
            context,
            catalogue,
            action,
        )
        live_fixture._append_new_row(  # noqa: SLF001
            controller=controller,
            stream=live_fixture._stream_for_row(  # noqa: SLF001
                namespace,
                row,
                identity.arm,
            ),
            marker=f"{marker}-root-{ordinal}",
            child=False,
        )
    return {
        "context": context,
        "identity": identity,
        "controller": controller,
        "epoch": live_fixture._freeze_epoch(  # noqa: SLF001
            controller,
            identity,
        ),
    }


@pytest.fixture(scope="module")
def live_root_contexts():
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture(  # noqa: SLF001
            "dynamic-authority-context-probe2"
        )
    )
    contexts = namespace.family.replicate_contexts
    return {
        "namespace": namespace,
        "w7": _root_epoch(
            generated=generated,
            salt=salt,
            namespace=namespace,
            authorization=authorization,
            signer=signer,
            context=contexts[1],
            marker="live-dynamic-w7",
        ),
        "k7": _root_epoch(
            generated=generated,
            salt=salt,
            namespace=namespace,
            authorization=authorization,
            signer=signer,
            context=contexts[0],
            marker="live-dynamic-k7",
        ),
    }


@pytest.fixture(scope="module")
def exact_child_transition(live_root_contexts):
    source = live_root_contexts["w7"]["epoch"]
    controller = live_root_contexts["w7"]["controller"]
    namespace = live_root_contexts["namespace"]
    closure = dynamic.freeze_v075_live_dynamic_child_closure_v2(
        source_epoch=source,
        namespace=namespace,
    )
    closure_verification = (
        dynamic._exact_child_closure_verification(closure)  # noqa: SLF001
    )
    role = (
        control.V075ControlledBatchSemanticAuthorityRoleV2
        .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
    )
    schema = (
        control.V075ControlledBatchSemanticAuthoritySchemaV2
        .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
    )
    intent_pairs = tuple(
        zip(
            closure.discovery_intents,
            closure.validation_templates,
            strict=True,
        )
    )
    pairs_by_child_state = {}
    for pair in intent_pairs:
        state_id = pair[0].row_binding.catalogue.state.state_id
        pairs_by_child_state.setdefault(state_id, []).append(pair)
    smallest_state_id, smallest_complete_catalogue = min(
        pairs_by_child_state.items(),
        key=lambda item: (len(item[1]), item[0]),
    )
    assert len(smallest_complete_catalogue) < len(intent_pairs)
    execution_pairs = tuple(smallest_complete_catalogue) + tuple(
        pair
        for pair in intent_pairs
        if pair[0].row_binding.catalogue.state.state_id
        != smallest_state_id
    )
    partial_prefix = None
    for execution_index, (discovery, template) in enumerate(execution_pairs):
        discovery_intent = controller.prepare_batch_intent_v2(
            stream_identity=discovery.stream_identity,
            semantic_authority_role=role,
            semantic_authority_schema=schema,
            semantic_artifact_id=discovery.intent_id,
            semantic_verification_id=closure_verification.verification_id,
            stage=control.V075ControlledBatchStageV2.CHILD_DISCOVERY,
            round_index=0,
            support_freeze_id=None,
            accepted_draw_start=1,
            accepted_draw_count=dynamic.CHILD_DISCOVERY_DRAWS,
            accepted_draw_cap=dynamic.CHILD_DISCOVERY_DRAWS,
        )
        discovery_append = controller.execute_batch_intent_v2(
            discovery_intent
        )
        support = controller.freeze_complete_support_v2(
            discovery_append=discovery_append,
        )
        validation_stream = controller.derive_validation_stream_v2(
            support_freeze=support,
        )
        validation_intent = controller.prepare_batch_intent_v2(
            stream_identity=validation_stream,
            semantic_authority_role=role,
            semantic_authority_schema=schema,
            semantic_artifact_id=template.template_id,
            semantic_verification_id=closure_verification.verification_id,
            stage=control.V075ControlledBatchStageV2.CHILD_VALIDATION,
            round_index=0,
            support_freeze_id=support.freeze_id,
            accepted_draw_start=1,
            accepted_draw_count=dynamic.CHILD_VALIDATION_DRAWS,
            accepted_draw_cap=12_288,
        )
        controller.execute_batch_intent_v2(validation_intent)
        if execution_index + 1 == len(smallest_complete_catalogue):
            partial_prefix = controller.freeze_owned_open_prefix_v2()
    assert partial_prefix is not None
    prefix = controller.freeze_owned_open_prefix_v2()
    ledger = dynamic.freeze_v075_live_dynamic_child_execution_ledger_v2(
        closure=closure,
        closure_verification=closure_verification,
        open_prefix_verification=prefix,
    )
    execution_verification = (
        dynamic._exact_child_execution_verification(ledger)  # noqa: SLF001
    )
    result = live_model.freeze_v075_live_incremental_model_epoch_v2(
        occurrence_identity=source.occurrence_identity,
        controlled_appends=controller.controlled_appends,
        support_freezes=controller.support_freezes,
        open_prefix_verification=prefix,
        route=source.route,
        parent_epoch=source,
    )
    barrier = (
        dynamic.freeze_v075_live_dynamic_child_replanning_barrier_v2(
            closure=closure,
            closure_verification=closure_verification,
            execution_ledger=ledger,
            execution_verification=execution_verification,
            resulting_epoch=result,
        )
    )
    barrier_verification = (
        dynamic._exact_child_replanning_barrier_verification(  # noqa: SLF001
            barrier
        )
    )
    return {
        "source": source,
        "controller": controller,
        "closure": closure,
        "closure_verification": closure_verification,
        "prefix": prefix,
        "partial_prefix": partial_prefix,
        "ledger": ledger,
        "execution_verification": execution_verification,
        "result": result,
        "barrier": barrier,
        "barrier_verification": barrier_verification,
    }


@pytest.fixture(scope="module")
def exact_round_two_transition(exact_child_transition):
    child = exact_child_transition
    child_lineage = {
        "child_closure": child["closure"],
        "child_closure_verification": child["closure_verification"],
        "child_execution_ledger": child["ledger"],
        "child_execution_verification": child["execution_verification"],
        "child_replanning_barrier": child["barrier"],
        "child_replanning_barrier_verification": (
            child["barrier_verification"]
        ),
    }
    source = child["result"]
    controller = child["controller"]
    first = dynamic.freeze_v075_live_promotion_decision_v2(
        source_epoch=source,
        round_index=1,
        **child_lineage,
    )
    assert first.status is (
        dynamic.V075LivePromotionDecisionStatusV2.AUTHORIZED
    )
    assert first.intent is not None
    first_verification = (
        dynamic._exact_promotion_decision_verification(first)  # noqa: SLF001
    )
    intent = first.intent
    stage = (
        control.V075ControlledBatchStageV2.ROOT_VALIDATION
        if intent.stage == "ROOT_VALIDATION"
        else control.V075ControlledBatchStageV2.CHILD_VALIDATION
    )
    controlled_intent = controller.prepare_batch_intent_v2(
        stream_identity=intent.stream_identity,
        semantic_authority_role=(
            control.V075ControlledBatchSemanticAuthorityRoleV2
            .LIVE_PROMOTION_AUTHORIZATION
        ),
        semantic_authority_schema=(
            control.V075ControlledBatchSemanticAuthoritySchemaV2
            .LIVE_PROMOTION_AUTHORIZATION
        ),
        semantic_artifact_id=intent.intent_id,
        semantic_verification_id=first_verification.verification_id,
        stage=stage,
        round_index=1,
        support_freeze_id=intent.support_freeze_id,
        accepted_draw_start=intent.accepted_draw_start,
        accepted_draw_count=intent.accepted_draw_count,
        accepted_draw_cap=intent.accepted_draw_cap,
    )
    controller.execute_batch_intent_v2(controlled_intent)
    prefix = controller.freeze_owned_open_prefix_v2()
    result = live_model.freeze_v075_live_incremental_model_epoch_v2(
        occurrence_identity=source.occurrence_identity,
        controlled_appends=controller.controlled_appends,
        support_freezes=controller.support_freezes,
        open_prefix_verification=prefix,
        route=source.route,
        parent_epoch=source,
    )
    first_barrier = (
        dynamic.freeze_v075_live_promotion_replanning_barrier_v2(
            decision=first,
            decision_verification=first_verification,
            resulting_epoch=result,
            **child_lineage,
        )
    )
    second = dynamic.freeze_v075_live_promotion_decision_v2(
        source_epoch=result,
        round_index=2,
        **child_lineage,
        previous_decision=first,
        previous_replanning_barrier=first_barrier,
    )
    return {
        "source": source,
        "first": first,
        "first_verification": first_verification,
        "first_barrier": first_barrier,
        "result": result,
        "second": second,
        "child_lineage": child_lineage,
    }


def _clone_epoch(
    source: live_model.V075LiveIncrementalModelEpochV2,
    *,
    model: planning.V075NumericalModelV2,
    proof: planning.V075NumericalPlanningProofV2,
    marker: str,
) -> live_model.V075LiveIncrementalModelEpochV2:
    clone = object.__new__(live_model.V075LiveIncrementalModelEpochV2)
    for item in fields(live_model.V075LiveIncrementalModelEpochV2):
        if not hasattr(source, item.name):
            continue
        replacement = (
            model
            if item.name == "model"
            else proof
            if item.name == "proof"
            else _id(marker)
            if item.name == "_model_epoch_id"
            else getattr(source, item.name)
        )
        object.__setattr__(clone, item.name, replacement)
    return clone


def _failed_selection_epoch(
    source: live_model.V075LiveIncrementalModelEpochV2,
    *,
    widths: tuple[Fraction, Fraction],
    other_uppers: tuple[Fraction, Fraction],
    marker: str,
) -> live_model.V075LiveIncrementalModelEpochV2:
    rows = tuple(sorted(source.model.rows, key=lambda item: item.row_id))
    assert len(rows) == 2
    obligations = tuple(
        planning.V075FrontierObligationV2(
            row.row_id,
            width,
            other_upper,
            (),
            row.validation_draw_count,
            row.validation_draw_count + dynamic.PROMOTION_DRAWS,
        )
        for row, width, other_upper in zip(
            rows,
            widths,
            other_uppers,
            strict=True,
        )
    )
    frontier = planning.V075FailedProofFrontierV2(
        planning._FRONTIER_ISSUER,  # type: ignore[attr-defined]
        source.model.model_id,
        planning.V075FailedProofReasonV2.RISK_AND_REGRET_BOUND_FAILED,
        obligations,
    )
    proof = planning.V075NumericalPlanningProofV2(
        planning._PROOF_ISSUER,  # type: ignore[attr-defined]
        source.model,
        source.route,
        source.proof.quotient,
        planning.V075NumericalOutcomeV2.FAILED_FRONTIER,
        None,
        None,
        frontier,
        source.proof.policy_assignments_evaluated,
    )
    return _clone_epoch(
        source,
        model=source.model,
        proof=proof,
        marker=marker,
    )


def _base_count_exact_row(
    binding: graph.V075ObservationRowBindingV1,
) -> planning.V075NumericalRowV2:
    successor = manual_fixture._safe_successor(binding)  # noqa: SLF001
    draw_count = (
        dynamic.ROOT_VALIDATION_BASE_DRAWS
        if binding.remaining_horizon == 2
        else dynamic.CHILD_VALIDATION_BASE_DRAWS
    )
    return planning.freeze_v075_manual_construction_row_v2(
        row_binding=binding,
        draw_count=draw_count,
        support_events=(
            (
                successor[0],
                successor[1],
                successor[2],
                draw_count,
                Fraction(1),
                Fraction(1),
            ),
        ),
        other_count=0,
        other_lower=Fraction(0),
        other_upper=Fraction(0),
    )


def _candidate_epoch(
    source: live_model.V075LiveIncrementalModelEpochV2,
) -> live_model.V075LiveIncrementalModelEpochV2:
    context = source.model.context
    root = graph.root_catalogue_v1(context)
    root_rows = []
    child_states = {}
    for action in root.actions:
        binding = graph.observation_row_binding_v1(
            context,
            root,
            action,
        )
        row = _base_count_exact_row(binding)
        root_rows.append(row)
        descriptor = row.support[0]
        state = graph.V075SymbolicGraphStateV1(
            context,
            descriptor.next_ranks,
            descriptor.failure,
        )
        child_states[state.state_id] = state
    child_rows = []
    for state_id in sorted(child_states):
        state = child_states[state_id]
        catalogue = graph.V075LegalActionCatalogueV1(
            context,
            state,
            1,
            graph.legal_action_triples_v1(
                context,
                state.ranks,
                state.failure,
            ),
        )
        for action in catalogue.actions:
            child_rows.append(
                _base_count_exact_row(
                    graph.observation_row_binding_v1(
                        context,
                        catalogue,
                        action,
                    )
                )
            )
    model = planning.freeze_v075_manual_construction_model_v2(
        context=context,
        rows=tuple((*root_rows, *child_rows)),
    )
    proof = planning.plan_v075_construction_numerical_model_v2(
        model=model,
        route=planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    assert proof.outcome is planning.V075NumericalOutcomeV2.CANDIDATE
    return _clone_epoch(
        source,
        model=model,
        proof=proof,
        marker="manual-candidate-epoch",
    )


def test_dynamic_child_closure_is_complete_all_or_none_and_replayable(
    live_root_contexts,
    monkeypatch,
) -> None:
    epoch = live_root_contexts["w7"]["epoch"]
    namespace = live_root_contexts["namespace"]
    replay_calls = 0
    original_replay = dynamic._operational_epoch  # noqa: SLF001
    original_portable_replay = dynamic._replay_epoch  # noqa: SLF001

    def counted_replay(value):
        nonlocal replay_calls
        replay_calls += 1
        return original_replay(value)

    monkeypatch.setattr(dynamic, "_operational_epoch", counted_replay)
    closure = dynamic.freeze_v075_live_dynamic_child_closure_v2(
        source_epoch=epoch,
        namespace=namespace,
    )
    assert replay_calls == 1
    assert closure.status is (
        dynamic.V075LiveDynamicChildClosureStatusV2.AUTHORIZED
    )
    assert closure.existing_child_action_row_count == 0
    assert 1 < closure.unresolved_child_action_row_count <= 19
    assert len(closure.discovery_intents) == 18
    assert len(closure.validation_templates) == 18
    assert epoch.proof.failed_frontier is not None
    assert {
        item.source_frontier_id for item in closure.discovery_intents
    } == {epoch.proof.failed_frontier.frontier_id}
    assert len(closure.child_states) == len(
        {item.state.state_id for item in closure.child_states}
    )
    assert {
        row.row_binding_id
        for child in closure.child_states
        for row in child.row_bindings
    } == {
        item.row_binding.row_binding_id
        for item in closure.discovery_intents
    }
    for child in closure.child_states:
        assert set(child.catalogue.actions) == {
            row.action for row in child.row_bindings
        }
        assert not child.modeled_row_binding_ids
        assert child.unresolved_row_binding_ids == tuple(
            row.row_binding_id for row in child.row_bindings
        )
    for intent, template in zip(
        closure.discovery_intents,
        closure.validation_templates,
        strict=True,
    ):
        assert intent.to_document()["stage"] == "CHILD_DISCOVERY"
        assert intent.to_document()["round_index"] == 0
        assert intent.to_document()["accepted_draw_count"] == 64
        assert template.discovery_intent.intent_id == intent.intent_id
        assert template.to_document()["stage"] == "CHILD_VALIDATION"
        assert template.to_document()["round_index"] == 0
        assert template.to_document()["accepted_draw_count"] == 8_192
        assert template.to_document()["accepted_draw_cap"] == 12_288
        assert template.to_document()["observer_execution_ready"] is False
    assert b"OTHER" not in closure.canonical_bytes
    replay_calls = 0

    def counted_portable_replay(value):
        nonlocal replay_calls
        replay_calls += 1
        return original_portable_replay(value)

    monkeypatch.setattr(dynamic, "_replay_epoch", counted_portable_replay)
    replayed, verification = (
        dynamic.verify_v075_live_dynamic_child_closure_bytes_v2(
            source_epoch=epoch,
            namespace=namespace,
            claimed_bytes=closure.canonical_bytes,
        )
    )
    assert replay_calls == 1
    assert replayed.closure_id == closure.closure_id
    assert verification.closure_id == closure.closure_id
    assert len(verification.discovery_intent_ids) == 18
    with pytest.raises(
        dynamic.V075LiveDynamicAcquisitionV2InvariantViolation,
        match="partial or contains extra work",
    ):
        dynamic.freeze_v075_live_dynamic_child_execution_ledger_v2(
            closure=closure,
            closure_verification=verification,
            open_prefix_verification=epoch.open_prefix_verification,
        )
    with pytest.raises(
        dynamic.V075LiveDynamicAcquisitionV2InvariantViolation
    ):
        replace(
            closure,
            validation_templates=closure.validation_templates[:-1],
        )


def test_over_cap_context_emits_typed_closure_and_no_partial_work(
    live_root_contexts,
) -> None:
    closure = dynamic.freeze_v075_live_dynamic_child_closure_v2(
        source_epoch=live_root_contexts["k7"]["epoch"],
        namespace=live_root_contexts["namespace"],
    )
    assert closure.status is (
        dynamic.V075LiveDynamicChildClosureStatusV2
        .CHILD_ACTION_ROW_CAP_EXCEEDED
    )
    assert closure.unresolved_child_action_row_count > 19
    assert closure.discovery_intents == ()
    assert closure.validation_templates == ()
    assert closure.to_document()["all_or_none_child_base_authorization"] is True


def test_exact_all_eighteen_child_rows_cross_typed_replanning_barrier(
    exact_child_transition,
) -> None:
    transition = exact_child_transition
    source = transition["source"]
    result = transition["result"]
    barrier = transition["barrier"]
    closure = transition["closure"]
    assert len(closure.discovery_intents) == 18
    assert len(transition["ledger"].executed_rows) == 18
    expected_changed = tuple(
        sorted(
            item.row_binding.row_binding_id
            for item in closure.discovery_intents
        )
    )
    expected_reused = tuple(
        sorted(item.row_binding_id for item in source.row_sources)
    )
    assert result.changed_row_binding_ids == expected_changed
    assert result.reused_row_binding_ids == expected_reused
    assert barrier.authorized_row_binding_ids == expected_changed
    assert barrier.source_row_binding_ids == expected_reused
    assert barrier.resulting_proof_id == result.proof.proof_id
    assert transition["barrier_verification"].barrier_id == barrier.barrier_id


def test_smallest_complete_child_catalogue_cannot_cross_global_barrier(
    exact_child_transition,
) -> None:
    transition = exact_child_transition
    source = transition["source"]
    partial_prefix = transition["partial_prefix"]
    partial_epoch = live_model.freeze_v075_live_incremental_model_epoch_v2(
        occurrence_identity=source.occurrence_identity,
        controlled_appends=partial_prefix.appends,
        support_freezes=partial_prefix.support_freezes,
        open_prefix_verification=partial_prefix,
        route=source.route,
        parent_epoch=source,
    )
    assert (
        1
        < len(partial_epoch.changed_row_binding_ids)
        < len(transition["closure"].discovery_intents)
    )
    with pytest.raises(
        dynamic.V075LiveDynamicAcquisitionV2InvariantViolation,
        match="execution ledger differs|partial",
    ):
        dynamic.freeze_v075_live_dynamic_child_replanning_barrier_v2(
            closure=transition["closure"],
            closure_verification=transition["closure_verification"],
            execution_ledger=transition["ledger"],
            execution_verification=transition["execution_verification"],
            resulting_epoch=partial_epoch,
        )
    with pytest.raises(
        dynamic.V075LiveDynamicAcquisitionV2InvariantViolation,
        match="root-stage epoch",
    ):
        dynamic.freeze_v075_live_dynamic_child_closure_v2(
            source_epoch=partial_epoch,
            namespace=transition["closure"]
            .discovery_intents[0].stream_identity.namespace,
        )
    with pytest.raises(
        dynamic.V075LiveDynamicAcquisitionV2InvariantViolation
    ):
        dynamic.freeze_v075_live_promotion_decision_v2(
            source_epoch=partial_epoch,
            round_index=1,
            child_closure=transition["closure"],
            child_closure_verification=(
                transition["closure_verification"]
            ),
            child_execution_ledger=transition["ledger"],
            child_execution_verification=(
                transition["execution_verification"]
            ),
            child_replanning_barrier=transition["barrier"],
            child_replanning_barrier_verification=(
                transition["barrier_verification"]
            ),
        )


def test_real_round_two_decision_operational_and_portable_replay(
    exact_round_two_transition,
) -> None:
    transition = exact_round_two_transition
    second = transition["second"]
    assert second.round_index == 2
    assert second.previous_decision is not None
    assert (
        second.previous_replanning_barrier_id
        == transition["first_barrier"].barrier_id
    )
    replayed, verification = (
        dynamic.verify_v075_live_promotion_decision_bytes_v2(
            source_epoch=transition["result"],
            round_index=2,
            **transition["child_lineage"],
            previous_decision=transition["first"],
            previous_replanning_barrier=transition["first_barrier"],
            claimed_bytes=second.canonical_bytes,
        )
    )
    assert replayed.decision_id == second.decision_id
    assert verification.decision_id == second.decision_id


def test_round_two_rejects_mutated_or_transplanted_parent_epoch(
    exact_round_two_transition,
) -> None:
    transition = exact_round_two_transition
    current = transition["result"]
    parent = current.parent_epoch
    assert type(parent) is live_model.V075LiveIncrementalModelEpochV2
    original_sources = parent.row_sources
    object.__setattr__(parent, "row_sources", tuple(reversed(original_sources)))
    try:
        with pytest.raises(
            dynamic.V075LiveDynamicAcquisitionV2InvariantViolation
        ):
            dynamic.freeze_v075_live_promotion_decision_v2(
                source_epoch=current,
                round_index=2,
                **transition["child_lineage"],
                previous_decision=transition["first"],
                previous_replanning_barrier=transition["first_barrier"],
            )
    finally:
        object.__setattr__(parent, "row_sources", original_sources)

    transplanted_parent = object.__new__(
        live_model.V075LiveIncrementalModelEpochV2
    )
    for item in fields(live_model.V075LiveIncrementalModelEpochV2):
        object.__setattr__(
            transplanted_parent,
            item.name,
            getattr(parent, item.name),
        )
    object.__setattr__(current, "parent_epoch", transplanted_parent)
    try:
        with pytest.raises(
            dynamic.V075LiveDynamicAcquisitionV2InvariantViolation
        ):
            dynamic.freeze_v075_live_promotion_decision_v2(
                source_epoch=current,
                round_index=2,
                **transition["child_lineage"],
                previous_decision=transition["first"],
                previous_replanning_barrier=transition["first_barrier"],
            )
    finally:
        object.__setattr__(current, "parent_epoch", parent)


def test_root_epoch_cannot_bypass_child_predecessor_before_promotion(
    live_root_contexts,
) -> None:
    epoch = live_root_contexts["w7"]["epoch"]
    closure = dynamic.freeze_v075_live_dynamic_child_closure_v2(
        source_epoch=epoch,
        namespace=live_root_contexts["namespace"],
    )
    verification = dynamic._exact_child_closure_verification(  # noqa: SLF001
        closure
    )
    assert closure.status is (
        dynamic.V075LiveDynamicChildClosureStatusV2.AUTHORIZED
    )
    with pytest.raises(
        dynamic.V075LiveDynamicAcquisitionV2InvariantViolation,
        match="cannot authorize promotion",
    ):
        dynamic.freeze_v075_live_promotion_decision_v2(
            source_epoch=epoch,
            round_index=1,
            child_closure=closure,
            child_closure_verification=verification,
            child_execution_ledger=None,
            child_execution_verification=None,
            child_replanning_barrier=None,
            child_replanning_barrier_verification=None,
        )


@pytest.mark.parametrize(
    ("widths", "other_uppers", "selected_index"),
    (
        (
            (Fraction(1, 4), Fraction(1, 2)),
            (Fraction(1, 2), Fraction(0)),
            1,
        ),
        (
            (Fraction(1, 2), Fraction(1, 2)),
            (Fraction(1, 4), Fraction(1, 2)),
            1,
        ),
        (
            (Fraction(1, 2), Fraction(1, 2)),
            (Fraction(1, 2), Fraction(1, 2)),
            0,
        ),
    ),
)
def test_promotion_selection_is_width_then_other_then_row_id(
    live_root_contexts,
    widths,
    other_uppers,
    selected_index,
) -> None:
    source = live_root_contexts["w7"]["epoch"]
    epoch = _failed_selection_epoch(
        source,
        widths=widths,
        other_uppers=other_uppers,
        marker=f"selection-{selected_index}-{widths}-{other_uppers}",
    )
    decision = dynamic._freeze_promotion_from_replayed_epoch(  # noqa: SLF001
        epoch=epoch,
        round_index=1,
        previous_decision=None,
        previous_replanning_barrier=None,
        predecessor_ids=(
            _id("selection-child-closure"),
            _id("selection-child-closure-verification"),
            None,
            None,
            None,
            None,
        ),
        portable_replay=False,
    )
    rows = tuple(sorted(epoch.model.rows, key=lambda item: item.row_id))
    assert decision.status is (
        dynamic.V075LivePromotionDecisionStatusV2.AUTHORIZED
    )
    assert decision.intent is not None
    assert decision.intent.numerical_row_id == rows[selected_index].row_id
    assert decision.intent.stage == "ROOT_VALIDATION"
    assert decision.intent.round_index == 1
    assert decision.intent.accepted_draw_start == 2_049
    assert decision.intent.accepted_draw_count == 2_048
    assert decision.intent.accepted_draw_cap == 6_144
    source_binding = epoch.row_source_for_binding_v2(
        decision.intent.row_binding_id
    )
    assert (
        decision.intent.row_source_binding_id
        == source_binding.binding_id
    )
    assert (
        decision.intent.support_freeze_id
        == source_binding.support_freeze_id
    )
    assert (
        decision.intent.stream_identity.stream_id
        == source_binding.validation_stream_id
    )


def test_candidate_is_early_stop_and_round_cap_or_stale_parent_reject(
    live_root_contexts,
    monkeypatch,
) -> None:
    source = live_root_contexts["w7"]["epoch"]
    candidate = _candidate_epoch(source)
    monkeypatch.setattr(dynamic, "_operational_epoch", lambda value: value)
    stopped = dynamic._freeze_promotion_from_replayed_epoch(  # noqa: SLF001
        epoch=candidate,
        round_index=1,
        previous_decision=None,
        previous_replanning_barrier=None,
        predecessor_ids=(
            _id("candidate-child-closure"),
            _id("candidate-child-closure-verification"),
            None,
            None,
            None,
            None,
        ),
        portable_replay=False,
    )
    assert stopped.status is (
        dynamic.V075LivePromotionDecisionStatusV2.CANDIDATE_EARLY_STOP
    )
    assert stopped.intent is None
    assert stopped.eligible_row_ids == ()
    with pytest.raises(
        dynamic.V075LiveDynamicAcquisitionV2InvariantViolation,
        match="root-stage epoch",
    ):
        dynamic.freeze_v075_live_dynamic_child_closure_v2(
            source_epoch=candidate,
            namespace=live_root_contexts["namespace"],
        )
    root_closure = dynamic.freeze_v075_live_dynamic_child_closure_v2(
        source_epoch=source,
        namespace=live_root_contexts["namespace"],
    )
    root_verification = (
        dynamic._exact_child_closure_verification(  # noqa: SLF001
            root_closure
        )
    )
    with pytest.raises(
        dynamic.V075LiveDynamicAcquisitionV2InvariantViolation
    ):
        dynamic.freeze_v075_live_promotion_decision_v2(
            source_epoch=source,
            round_index=3,
            child_closure=root_closure,
            child_closure_verification=root_verification,
            child_execution_ledger=None,
            child_execution_verification=None,
            child_replanning_barrier=None,
            child_replanning_barrier_verification=None,
        )


def test_canonical_byte_tamper_and_production_entry_fail_closed(
    live_root_contexts,
    monkeypatch,
) -> None:
    epoch = live_root_contexts["w7"]["epoch"]
    closure = dynamic.freeze_v075_live_dynamic_child_closure_v2(
        source_epoch=epoch,
        namespace=live_root_contexts["namespace"],
    )
    with pytest.raises(
        dynamic.V075LiveDynamicAcquisitionV2InvariantViolation
    ):
        dynamic.verify_v075_live_dynamic_child_closure_bytes_v2(
            source_epoch=epoch,
            namespace=live_root_contexts["namespace"],
            claimed_bytes=closure.canonical_bytes + b" ",
        )
    assert canonical_json_bytes(closure.to_document()) == closure.canonical_bytes
    monkeypatch.setattr(dynamic, "OFFICIAL_EXECUTION_ALLOWED", True)
    with pytest.raises(
        dynamic.V075LiveDynamicAcquisitionProductionV2NotReady
    ):
        dynamic.open_v075_production_live_dynamic_acquisition_authority_v2()
