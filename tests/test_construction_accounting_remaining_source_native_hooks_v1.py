from __future__ import annotations

import ast
from collections import Counter
from fractions import Fraction
import hashlib
import inspect
from types import SimpleNamespace

import pytest

from acfqp import construction_accounting_owned_runtime_v1 as accounting_runtime
from acfqp import construction_accounting_partial_native_v1 as partial
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_private_observer_boundary_v2 as private_observer
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp.v075_k7_root_cap_operation_boundary_manifest_v3 import (
    OperationBoundaryClassificationV3,
    official_k7_root_cap_operation_boundary_manifest_v3,
)
from tests import test_v075_batch_native_planning_backend_v2 as planning_fixture
from tests import test_construction_accounting_source_native_hooks_v1 as hook_fixture
from tests import test_v075_observer_signed_batch_control_authority_v2 as control_fixture
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


_MODULES = (
    private_observer,
    control,
    live_model,
    dynamic,
)
_EMITTABLE = {
    OperationBoundaryClassificationV3.V6_NATIVE_BOUNDARY_SCHEMA_ONLY,
    OperationBoundaryClassificationV3.V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY,
    (
        OperationBoundaryClassificationV3
        .V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY
    ),
    (
        OperationBoundaryClassificationV3
        .V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY
    ),
}


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:remaining-source-native-hook-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _source_dispatch_keys(module: object) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    keys: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "accounting_runtime"
            and node.func.attr == "emit_owned_operation_v1"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.add(node.args[0].value)
    return keys


def test_all_active_nonplanning_owner_boundaries_have_exact_source_hooks() -> None:
    manifest = official_k7_root_cap_operation_boundary_manifest_v3()
    for module in _MODULES:
        expected = {
            boundary.dispatch_key
            for boundary in manifest.boundaries
            if boundary.classification in _EMITTABLE
            and boundary.operation_source_module == module.__name__
        }
        assert expected
        assert _source_dispatch_keys(module) == expected


def test_private_observer_and_control_charge_completed_native_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        accounting_runtime,
        "emit_owned_operation_v1",
        lambda key, amount=1: calls.extend([key] * amount),
    )
    values = observer_fixture._fixture("remaining-hook-private-control")
    controller = control_fixture._controller(
        values,
        "remaining-hook-private-control-session",
        ordinal=0,
    )
    stream = control_fixture._stream(values)
    intent = controller.prepare_batch_intent_v2(
        stream_identity=stream,
        **control_fixture._semantic("remaining-hook-private-control"),
        accepted_draw_start=1,
        accepted_draw_count=3,
        accepted_draw_cap=3,
    )
    append = controller.execute_batch_intent_v2(intent)
    support = controller.freeze_complete_support_v2(
        discovery_append=append
    )

    counts = Counter(calls)
    assert counts["private-observer.accumulator.append"] == 3
    assert counts["private-observer.outcome-aggregate.materialize"] == len(
        append.batch.outcomes
    )
    assert counts["private-observer.signed-batch.materialize"] == 1
    assert counts["private-observer.signed-batch.commit"] == 1
    assert counts["observer-control.support-freeze.commit"] == 1
    assert support.discovery_append == append


def test_private_control_hooks_pass_runtime_owner_and_qualname_checks() -> None:
    values = observer_fixture._fixture("remaining-hook-owned-private-control")
    controller = control_fixture._controller(
        values,
        "remaining-hook-owned-private-control-session",
        ordinal=0,
    )
    stream = control_fixture._stream(values)
    intent = controller.prepare_batch_intent_v2(
        stream_identity=stream,
        **control_fixture._semantic("remaining-hook-owned-private-control"),
        accepted_draw_start=1,
        accepted_draw_count=2,
        accepted_draw_cap=2,
    )
    with hook_fixture._activation("remaining-hook-owned-private-control"):
        target = partial.PartialNativeStageV1.INITIAL_ACQUISITION
        hook_fixture._enter_target_stage(target)
        append = controller.execute_batch_intent_v2(intent)
        controller.freeze_complete_support_v2(discovery_append=append)
        transcript = hook_fixture._complete_from_stage(target)

    counts = hook_fixture._event_path_counts(transcript)
    assert counts["acquisition.initial_observer_accumulator_updates"] == 2
    assert counts["acquisition.initial_outcome_aggregate_rows"] == len(
        append.batch.outcomes
    )
    assert counts["acquisition.initial_signed_batches_materialized"] == 1
    assert counts["acquisition.initial_signed_batches_committed"] == 1
    assert counts["acquisition.initial_support_freezes"] == 1


def test_private_observer_retains_completed_work_before_late_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        accounting_runtime,
        "emit_owned_operation_v1",
        lambda key, amount=1: calls.extend([key] * amount),
    )
    values = observer_fixture._fixture("remaining-hook-private-failure")
    controller = control_fixture._controller(
        values,
        "remaining-hook-private-failure-session",
        ordinal=0,
    )
    stream = control_fixture._stream(values)
    intent = controller.prepare_batch_intent_v2(
        stream_identity=stream,
        **control_fixture._semantic("remaining-hook-private-failure"),
        accepted_draw_start=1,
        accepted_draw_count=2,
        accepted_draw_cap=2,
    )
    monkeypatch.setattr(private_observer, "MAX_CANONICAL_CLOSURE_BYTES", 0)
    with pytest.raises(Exception, match="generation byte cap"):
        controller.execute_batch_intent_v2(intent)

    counts = Counter(calls)
    assert counts["private-observer.accumulator.append"] == 2
    assert counts["private-observer.outcome-aggregate.materialize"] > 0
    assert counts["private-observer.signed-batch.materialize"] == 1
    assert counts["private-observer.signed-batch.commit"] == 0
    assert counts["observer-control.support-freeze.commit"] == 0


def test_live_model_hooks_count_primitives_not_returned_cardinalities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptors_created = 0

    def descriptor_factory(
        _issuer: object,
        _context_id: str,
        state_id: str,
        ranks: tuple[int, ...],
        failure: bool,
        terminal: bool,
    ) -> SimpleNamespace:
        nonlocal descriptors_created
        descriptors_created += 1
        return SimpleNamespace(
            descriptor_id=_id(f"descriptor-{descriptors_created}"),
            next_state_id=state_id,
            next_ranks=ranks,
            failure=failure,
            terminal=terminal,
        )

    monkeypatch.setattr(
        live_model.planning,
        "V075SupportDescriptorV2",
        descriptor_factory,
    )
    monkeypatch.setattr(
        live_model.planning, "_merge_reward", lambda _row: Fraction(1)
    )
    monkeypatch.setattr(
        live_model.planning,
        "_allowed_checkpoints",
        lambda **_kwargs: (3,),
    )
    monkeypatch.setattr(
        live_model.planning,
        "_checkpoint_interval",
        lambda **kwargs: (kwargs["success_count"], kwargs["draw_count"]),
    )
    compiled_row = SimpleNamespace(row_id=_id("compiled-row"))
    monkeypatch.setattr(
        live_model.planning,
        "V075NumericalRowV2",
        lambda *_args: compiled_row,
    )
    monkeypatch.setattr(
        live_model.planning,
        "_replay_numerical_row",
        lambda row: row,
    )

    row_binding = SimpleNamespace(
        context_id=_id("context"),
        row_binding_id=_id("compiled-row-binding"),
        state_id=_id("compiled-state"),
        catalogue=SimpleNamespace(state=SimpleNamespace(ranks=(1, 1))),
        remaining_horizon=2,
        action=(0, 1, 0),
    )
    discovery = SimpleNamespace(
        batch=SimpleNamespace(
            request=SimpleNamespace(
                stream_identity=SimpleNamespace(row_binding=row_binding)
            )
        )
    )
    support = SimpleNamespace(
        evidence=(
            SimpleNamespace(
                observed_state=SimpleNamespace(
                    state_id=_id("state-a"),
                    ranks=(1, 2),
                    failure=False,
                )
            ),
            SimpleNamespace(
                observed_state=SimpleNamespace(
                    state_id=_id("state-b"),
                    ranks=(2, 1),
                    failure=False,
                )
            ),
        )
    )
    outcome = SimpleNamespace(
        realized_row_reward=Fraction(1),
        reward_sum=Fraction(3),
        count=3,
        next_ranks=(1, 2),
        failure=False,
        terminal=False,
    )
    validations = (
        SimpleNamespace(
            batch=SimpleNamespace(
                request=SimpleNamespace(
                    accepted_draw_count=3,
                    accepted_draw_end=3,
                ),
                outcomes=(outcome,),
            )
        ),
    )
    with hook_fixture._activation("remaining-hook-owned-live-compile"):
        target = partial.PartialNativeStageV1.INITIAL_MODEL_BUILD
        hook_fixture._enter_target_stage(target)
        result = live_model._compile_numerical_row(  # noqa: SLF001
            occurrence_identity=SimpleNamespace(
                arm=worker.V075WorkerArmV1.NO_PRIOR
            ),
            discovery=discovery,
            support_freeze=support,
            validations=validations,
        )
        transcript = hook_fixture._complete_from_stage(target)
    assert result is compiled_row
    counts = hook_fixture._event_path_counts(transcript)
    assert counts["build.initial_live_model_support_descriptors_compiled"] == 2
    assert counts["build.initial_live_model_outcome_projections"] == 1
    assert counts["build.initial_model_rows_built"] == 1


def test_live_model_source_unit_and_binding_emit_after_each_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row_binding = SimpleNamespace(
        remaining_horizon=2,
        row_binding_id=_id("row-binding"),
    )
    discovery_stream = SimpleNamespace(
        row_binding_id=row_binding.row_binding_id,
        row_binding=row_binding,
        lane=graph.V075ObservationLaneV1.DISCOVERY,
        observer_epoch_index=0,
    )
    discovery = SimpleNamespace(
        intent=SimpleNamespace(
            semantic_authority=SimpleNamespace(
                stage=control.V075ControlledBatchStageV2.ROOT_DISCOVERY
            )
        ),
        batch=SimpleNamespace(
            request=SimpleNamespace(stream_identity=discovery_stream),
            batch_id=_id("discovery-batch"),
        ),
        receipt=SimpleNamespace(receipt_id=_id("discovery-receipt")),
        resulting_head=SimpleNamespace(entry_count=1),
    )
    validation_stream = SimpleNamespace(
        row_binding_id=row_binding.row_binding_id,
        row_binding=row_binding,
        lane=graph.V075ObservationLaneV1.VALIDATION,
        observer_epoch_index=1,
        stream_id=_id("validation-stream"),
    )
    validation_request = SimpleNamespace(
        stream_identity=validation_stream,
        accepted_draw_start=1,
        accepted_draw_end=1,
        accepted_draw_cap=1,
        request_id=_id("validation-request"),
    )
    validation = SimpleNamespace(
        intent=SimpleNamespace(
            semantic_authority=SimpleNamespace(
                stage=control.V075ControlledBatchStageV2.ROOT_VALIDATION,
                support_freeze_id=_id("support-freeze"),
            )
        ),
        batch=SimpleNamespace(
            request=validation_request,
            batch_id=_id("validation-batch"),
        ),
        receipt=SimpleNamespace(receipt_id=_id("validation-receipt")),
        prior_head=SimpleNamespace(entry_count=1),
    )
    freeze = SimpleNamespace(
        row_binding_id=row_binding.row_binding_id,
        discovery_append=discovery,
        frozen_at_head=SimpleNamespace(entry_count=1),
        freeze_id=_id("support-freeze"),
    )
    monkeypatch.setattr(
        live_model.control,
        "_derive_validation_stream_from_owned_support_freeze",
        lambda _freeze: validation_stream,
    )
    monkeypatch.setattr(
        live_model.planning,
        "_allowed_checkpoints",
        lambda **_kwargs: (1,),
    )
    with hook_fixture._activation("remaining-hook-owned-live-source"):
        target = partial.PartialNativeStageV1.INITIAL_MODEL_BUILD
        hook_fixture._enter_target_stage(target)
        collected = live_model._collect_rows(  # noqa: SLF001
            occurrence_identity=SimpleNamespace(
                arm=worker.V075WorkerArmV1.NO_PRIOR
            ),
            appends=(discovery, validation),
            support_freezes=(freeze,),
            portable_replay=False,
        )
        assert len(collected) == 1
        binding = live_model._row_source_binding(  # noqa: SLF001
            collected[0],
            SimpleNamespace(row_id=_id("numerical-row")),
        )
        transcript = hook_fixture._complete_from_stage(target)
    assert binding.row_binding_id == row_binding.row_binding_id
    counts = hook_fixture._event_path_counts(transcript)
    assert counts["build.initial_source_units_compiled"] == 1
    assert counts["build.initial_live_model_row_source_bindings_built"] == 1


def test_dynamic_child_hooks_count_each_entered_or_completed_primitive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = (
        public.freeze_v075_public_family_generation_v1()
        .replicate_contexts[0]
    )
    root = graph.root_catalogue_v1(context)
    root_binding = graph.observation_row_binding_v1(
        context,
        root,
        root.actions[0],
    )
    successor = planning_fixture._safe_successor(root_binding)
    child_state = graph.V075SymbolicGraphStateV1(
        context,
        successor[0],
        False,
    )
    numerical_row_id = _id("dynamic-parent-row")
    descriptor = SimpleNamespace(
        descriptor_id=_id("dynamic-descriptor"),
        next_state_id=child_state.state_id,
        next_ranks=child_state.ranks,
        failure=False,
        terminal=False,
    )
    numerical_row = SimpleNamespace(
        remaining_horizon=2,
        row_binding_id=root_binding.row_binding_id,
        row_id=numerical_row_id,
        support=(descriptor,),
    )
    source = live_model.V075LiveModelRowSourceBindingV2(
        live_model._ROW_SOURCE_ISSUER,  # noqa: SLF001
        root_binding.row_binding_id,
        _id("dynamic-discovery-receipt"),
        _id("dynamic-discovery-batch"),
        _id("dynamic-support-freeze"),
        _id("dynamic-validation-stream"),
        (_id("dynamic-validation-receipt"),),
        (_id("dynamic-validation-batch"),),
        1,
        1,
        _id("dynamic-source-digest"),
        numerical_row_id,
    )

    class FakeEpoch:
        model = SimpleNamespace(rows=(numerical_row,), context=context)

        @staticmethod
        def row_source_for_binding_v2(row_binding_id: str):
            assert row_binding_id == root_binding.row_binding_id
            return source

    with hook_fixture._activation("remaining-hook-owned-dynamic-derive"):
        target = partial.PartialNativeStageV1.FAILED_ABSTRACT_PREFIX
        hook_fixture._enter_target_stage(target)
        children = dynamic._derive_child_states(FakeEpoch())  # noqa: SLF001
        transcript = hook_fixture._complete_from_stage(target)
    assert len(children) == 1
    first_documents = tuple(item.to_document() for item in children)
    counts = hook_fixture._event_path_counts(transcript)
    assert counts["audit.dynamic_root_rows_scanned"] == 1
    assert counts["audit.dynamic_support_descriptors_scanned"] == 1
    assert counts["audit.dynamic_causal_edges_built"] == 1
    assert counts["audit.failed_child_catalogues_built"] == 1
    assert counts["audit.dynamic_child_action_rows_built"] == len(
        children[0].row_bindings
    )

    assert tuple(
        item.to_document()
        for item in dynamic._derive_child_states(FakeEpoch())  # noqa: SLF001
    ) == first_documents


def test_dynamic_cap_and_owned_attestation_hooks_are_invocation_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    epoch = SimpleNamespace(
        proof=SimpleNamespace(
            outcome=dynamic.planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
        )
    )
    unresolved_rows = tuple(
        SimpleNamespace(row_binding_id=_id(f"cap-row-{index}"))
        for index in range(dynamic.MAXIMUM_NEW_CHILD_ACTION_ROWS + 1)
    )
    child = SimpleNamespace(
        modeled_row_binding_ids=(),
        unresolved_row_binding_ids=tuple(
            row.row_binding_id for row in unresolved_rows
        ),
        row_bindings=unresolved_rows,
    )
    monkeypatch.setattr(
        dynamic, "_assert_exact_root_stage_epoch", lambda _epoch: None
    )
    monkeypatch.setattr(
        dynamic, "_replay_namespace", lambda namespace, epoch: namespace
    )
    monkeypatch.setattr(dynamic, "_derive_child_states", lambda _epoch: (child,))
    cap_closure = SimpleNamespace(
        closure_id=_id("cap-closure"),
        status=(
            dynamic.V075LiveDynamicChildClosureStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        ),
        discovery_intents=(),
        validation_templates=(),
    )
    monkeypatch.setattr(
        dynamic,
        "V075LiveDynamicChildClosureV2",
        lambda *_args: cap_closure,
    )
    with hook_fixture._activation("remaining-hook-owned-dynamic-cap"):
        target = partial.PartialNativeStageV1.FAILED_ABSTRACT_PREFIX
        hook_fixture._enter_target_stage(target)
        assert (
            dynamic._freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2(  # noqa: SLF001
                epoch=epoch,
                namespace=object(),
            )
            is cap_closure
        )
        cap_transcript = hook_fixture._complete_from_stage(target)
    cap_counts = hook_fixture._event_path_counts(cap_transcript)
    assert cap_counts["audit.dynamic_row_cap_checks"] == 1

    owned_epoch = SimpleNamespace(
        model_epoch_id=_id("owned-epoch"),
        proof=SimpleNamespace(proof_id=_id("owned-proof")),
        head_id=_id("owned-head"),
    )
    monkeypatch.setattr(
        dynamic.operational_context,
        "operational_no_full_replay_enabled_v3",
        lambda: True,
    )
    monkeypatch.setattr(dynamic, "_operational_epoch", lambda value: value)
    monkeypatch.setattr(
        dynamic,
        "_freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2",
        lambda **_kwargs: cap_closure,
    )
    verification = SimpleNamespace(verification_id=_id("verification"))
    monkeypatch.setattr(
        dynamic,
        "V075LiveDynamicChildClosureVerificationV2",
        lambda *_args: verification,
    )
    with hook_fixture._activation("remaining-hook-owned-dynamic-attest"):
        target = partial.PartialNativeStageV1.FAILED_ABSTRACT_PREFIX
        hook_fixture._enter_target_stage(target)
        closure_result, verification_result = (
            dynamic.freeze_and_attest_v075_live_dynamic_child_closure_owned_v3(
                source_epoch=owned_epoch,
                namespace=object(),
            )
        )
        attest_transcript = hook_fixture._complete_from_stage(target)
    assert closure_result is cap_closure
    assert verification_result is verification
    attest_counts = hook_fixture._event_path_counts(attest_transcript)
    assert attest_counts["audit.dynamic_child_closure_attestations"] == 1
