from __future__ import annotations

from contextvars import copy_context
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import hashlib
import inspect
import threading
from types import FunctionType

import pytest

from acfqp import construction_accounting_owned_runtime_v1 as runtime
from acfqp import construction_accounting_partial_native_v1 as partial
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import sequential_bernoulli_acquisition_v1 as sequential
from acfqp import v075_batch_native_planning_backend_v2 as planning_backend
from acfqp.v075_k7_root_cap_operation_boundary_manifest_v3 import (
    official_k7_root_cap_operation_boundary_manifest_v3,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:partial-native-runtime-test\x00" + label.encode("utf-8")
    ).hexdigest()


def _authorities():
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    boundary = official_k7_root_cap_operation_boundary_manifest_v3()
    return registry, stage, boundary


def _activation(label: str):
    registry, stage, boundary = _authorities()
    return runtime.activate_owned_construction_accounting_v1(
        occurrence_id=_id(label),
        recorder_id="trusted-partial-native-test-recorder-v1",
        counter_registry=registry,
        stage_profile=stage,
        boundary_profile=boundary,
        _allow_low_level_test_api=True,
    )


def _complete_stage(
    stage: partial.PartialNativeStageV1,
    *,
    site: str | None = None,
    path: str | None = None,
    amount: int = 1,
    output_role: str,
) -> None:
    runtime.enter_owned_stage_v1(stage)
    if site is not None:
        assert path is not None
        runtime.emit_owned_sum_v1(site, path, amount)
    runtime.exit_owned_stage_v1(
        stage,
        output_bindings=((output_role, _id(f"output-{output_role}")),),
    )


def _enter_initial_model_stage() -> None:
    for stage in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1:
        runtime.enter_owned_stage_v1(stage)
        if stage is partial.PartialNativeStageV1.INITIAL_MODEL_BUILD:
            return
        runtime.exit_owned_stage_v1(stage)
    raise AssertionError("initial model stage is absent")


def test_inactive_source_api_is_a_true_noop() -> None:
    assert runtime.emit_owned_operation_v1(object(), False) is None
    assert runtime.emit_owned_sum_v1(object(), object(), False) is None
    assert runtime.enter_owned_stage_v1(object()) is None
    assert runtime.exit_owned_stage_v1(
        object(), output_bindings=object()
    ) is None
    assert runtime.complete_owned_occurrence_v1() is None
    assert runtime.abort_owned_occurrence_v1("IGNORED") is None


def test_exact_five_stage_chain_is_partial_typed_and_content_addressed() -> None:
    with _activation("complete") as session:
        _complete_stage(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX,
            output_role="preopen",
        )
        _complete_stage(
            partial.PartialNativeStageV1.INITIAL_ACQUISITION,
            site="v6.acquisition-initial-engine-ground-draws",
            path="acquisition.initial_engine_ground_draws",
            amount=4,
            output_role="initial_acquisition",
        )
        _complete_stage(
            partial.PartialNativeStageV1.INITIAL_MODEL_BUILD,
            site="v6.build-initial-batch-v2-option-metric-evaluations",
            path="build.initial_batch_v2_option_metric_evaluations",
            amount=7,
            output_role="initial_model",
        )
        _complete_stage(
            partial.PartialNativeStageV1.FAILED_ABSTRACT_PREFIX,
            site="v5.audit-dynamic-root-rows-scanned",
            path="audit.dynamic_root_rows_scanned",
            amount=2,
            output_role="failed_prefix",
        )
        _complete_stage(
            (
                partial.PartialNativeStageV1
                .CLOSED_RECONCILIATION_AND_TERMINALIZATION
            ),
            site=(
                "v6.closure-reconciliation-batch-v2-"
                "option-metric-evaluations"
            ),
            path=(
                "closure.reconciliation_batch_v2_"
                "option_metric_evaluations"
            ),
            amount=5,
            output_role="closed",
        )
        transcript = runtime.complete_owned_occurrence_v1()

    assert transcript is not None
    assert transcript.terminal_kind is partial.PartialNativeTerminalKindV1.COMPLETED
    assert transcript.coverage_state == "PARTIAL_NATIVE_ONLY"
    assert transcript.official_execution_allowed is False
    document = transcript.to_document()
    expected_null = {
        "kind": "NOT_AVAILABLE_INCOMPLETE_SITE_COVERAGE",
        "reason": (
            "operation-site coverage is incomplete; absent native work is unknown"
        ),
    }
    assert document["counter_records"] == expected_null
    assert document["work_vector"] == expected_null
    assert document["comparison_vector"] == expected_null
    assert document["actual_projection"] == expected_null
    assert document["absent_native_events_inferred_zero"] is False
    events = [
        row
        for row in transcript.nodes
        if type(row) is partial.PartialNativeOperationEventV1
    ]
    assert [row.amount for row in events] == [4, 7, 2, 5]
    terminal = transcript.nodes[-1]
    assert terminal.emitted_event_ids == tuple(row.event_id for row in events)
    completions = [
        row
        for row in transcript.nodes
        if type(row) is partial.PartialNativeStageCompletionV1
    ]
    assert [row.output_bindings[0].role for row in completions] == [
        "preopen",
        "initial_acquisition",
        "initial_model",
        "failed_prefix",
        "closed",
    ]
    partial.verify_partial_native_occurrence_transcript_v1(transcript)
    assert transcript.transcript_id == transcript.transcript_id
    with pytest.raises(FrozenInstanceError):
        transcript.coverage_state = "COMPLETE"  # type: ignore[misc]


def test_chain_replay_rejects_event_tampering_and_output_reordering() -> None:
    with _activation("tamper") as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        runtime.exit_owned_stage_v1(
            output_bindings=(("a", _id("a")), ("b", _id("b")))
        )
        for stage in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1[1:]:
            runtime.enter_owned_stage_v1(stage)
            runtime.exit_owned_stage_v1()
        transcript = runtime.complete_owned_occurrence_v1()
    assert transcript is not None

    completion_index = next(
        index
        for index, row in enumerate(transcript.nodes)
        if type(row) is partial.PartialNativeStageCompletionV1
    )
    completion = transcript.nodes[completion_index]
    with pytest.raises(
        partial.PartialNativeAccountingV1Error, match="canonical order"
    ):
        replace(completion, output_bindings=tuple(reversed(completion.output_bindings)))

    duplicate_roles = tuple(
        sorted(
            (
                partial.PartialNativeOutputBindingV1("same_role", _id("same-a")),
                partial.PartialNativeOutputBindingV1("same_role", _id("same-b")),
            )
        )
    )
    with pytest.raises(
        partial.PartialNativeAccountingV1Error, match="unique and in canonical order"
    ):
        replace(completion, output_bindings=duplicate_roles)

    # Add one real event, then alter it without changing its successor link.
    with _activation("tamper-event"):
        _complete_stage(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX,
            output_role="preopen_event_case",
        )
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.INITIAL_ACQUISITION
        )
        runtime.emit_owned_sum_v1(
            "v6.acquisition-initial-engine-ground-draws",
            "acquisition.initial_engine_ground_draws",
            3,
        )
        runtime.exit_owned_stage_v1()
        for stage in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1[2:]:
            runtime.enter_owned_stage_v1(stage)
            runtime.exit_owned_stage_v1()
        event_transcript = runtime.complete_owned_occurrence_v1()
    nodes = list(event_transcript.nodes)
    event_index = next(
        index
        for index, row in enumerate(nodes)
        if type(row) is partial.PartialNativeOperationEventV1
    )
    nodes[event_index] = replace(nodes[event_index], amount=99)
    with pytest.raises(
        partial.PartialNativeAccountingV1Error, match="reordered"
    ):
        partial.PartialNativeOccurrenceTranscriptV1(
            event_transcript.start, tuple(nodes)
        )


@pytest.mark.parametrize(
    ("site", "path", "amount", "reason"),
    (
        (
            "unknown.site",
            "acquisition.initial_engine_ground_draws",
            1,
            "UNKNOWN_OPERATION_SITE",
        ),
        (
            "v6.acquisition-initial-engine-ground-draws",
            "acquisition.initial_engine_random_word_calls",
            1,
            "SITE_PATH_MISMATCH",
        ),
        (
            "v6.acquisition-initial-engine-ground-draws",
            "acquisition.initial_engine_ground_draws",
            False,
            "NONPOSITIVE_OR_INEXACT_AMOUNT",
        ),
    ),
)
def test_active_site_path_and_amount_violations_abort(
    site: str, path: str, amount: object, reason: str
) -> None:
    with _activation(f"abort-{reason}") as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        runtime.exit_owned_stage_v1()
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.INITIAL_ACQUISITION
        )
        with pytest.raises(runtime.OwnedConstructionAccountingRuntimeV1Error):
            runtime.emit_owned_sum_v1(site, path, amount)
        transcript = session.transcript

    terminal = transcript.nodes[-1]
    assert type(terminal) is partial.PartialNativeOccurrenceAbortV1
    assert terminal.reason == reason
    assert terminal.aborted_stage_index == 2
    assert terminal.aborted_stage_kind is (
        partial.PartialNativeStageV1.INITIAL_ACQUISITION
    )
    assert terminal.exception_module == runtime.__name__
    assert terminal.exception_qualname == "OwnedConstructionAccountingRuntimeV1Error"
    with pytest.raises(runtime.OwnedConstructionAccountingRuntimeV1Error):
        session.enter_stage(partial.PartialNativeStageV1.INITIAL_MODEL_BUILD)


def test_active_stage_abort_preserves_prior_event_ids_without_private_error_bytes() -> None:
    with _activation("active-stage-abort") as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        runtime.exit_owned_stage_v1()
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.INITIAL_ACQUISITION
        )
        runtime.emit_owned_sum_v1(
            "v6.acquisition-initial-engine-ground-draws",
            "acquisition.initial_engine_ground_draws",
            11,
        )
        transcript = runtime.abort_owned_occurrence_v1("TEST_REQUESTED_ABORT")

    event = next(
        row
        for row in transcript.nodes
        if type(row) is partial.PartialNativeOperationEventV1
    )
    terminal = transcript.nodes[-1]
    assert terminal.emitted_event_ids == (event.event_id,)
    assert terminal.total_event_count == 1
    assert terminal.aborted_stage_index == 2
    assert terminal.aborted_stage_kind is partial.PartialNativeStageV1.INITIAL_ACQUISITION
    assert isinstance(
        terminal.exception_module, partial.PartialNativeNotApplicableV1
    )
    abort_document = terminal.to_document()
    assert "message" not in abort_document
    assert "stack" not in abort_document
    assert "traceback" not in abort_document
    with pytest.raises(runtime.OwnedConstructionAccountingRuntimeV1Error):
        session.emit_sum(
            "v6.acquisition-initial-engine-ground-draws",
            "acquisition.initial_engine_ground_draws",
        )


def test_wrong_stage_nested_scope_and_exact_identity_fail_closed() -> None:
    with _activation("wrong-stage") as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="outside the active stage",
        ):
            runtime.emit_owned_sum_v1(
                "v6.acquisition-initial-engine-ground-draws",
                "acquisition.initial_engine_ground_draws",
            )
        assert session.transcript.nodes[-1].reason == "SITE_STAGE_MISMATCH"

    with _activation("outer") as outer:
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="cannot be nested",
        ):
            with _activation("inner"):
                pass
        assert outer.transcript.nodes[-1].reason == "NESTED_ACTIVE_SCOPE"

    registry, stage, boundary = _authorities()
    mismatched = replace(boundary, stage_profile_id=_id("foreign-stage-profile"))
    with pytest.raises(
        runtime.OwnedConstructionAccountingRuntimeV1Error,
        match="different stage profile",
    ):
        with runtime.activate_owned_construction_accounting_v1(
            occurrence_id=_id("identity-mismatch"),
            recorder_id="identity-mismatch-recorder-v1",
            counter_registry=registry,
            stage_profile=stage,
            boundary_profile=mismatched,
        ):
            pass


def test_context_copied_to_another_thread_aborts_owner_scope() -> None:
    errors: list[BaseException] = []
    with _activation("cross-thread") as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        copied = copy_context()

        def target() -> None:
            try:
                copied.run(
                    runtime.emit_owned_sum_v1,
                    "v6.acquisition-initial-engine-ground-draws",
                    "acquisition.initial_engine_ground_draws",
                    1,
                )
            except BaseException as error:
                errors.append(error)

        worker = threading.Thread(target=target)
        worker.start()
        worker.join()
        assert len(errors) == 1
        assert isinstance(
            errors[0], runtime.OwnedConstructionAccountingRuntimeV1Error
        )
        transcript = session.transcript

    terminal = transcript.nodes[-1]
    assert terminal.reason == "CROSS_THREAD_ACTIVE_SCOPE"
    assert terminal.aborted_stage_index == 1
    assert terminal.aborted_stage_kind is (
        partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
    )


def test_normal_scope_exit_without_terminalization_aborts_and_raises() -> None:
    holder: list[runtime.OwnedConstructionAccountingSessionV1] = []
    with pytest.raises(
        runtime.OwnedConstructionAccountingRuntimeV1Error,
        match="without terminalization",
    ):
        with _activation("incomplete-exit") as session:
            holder.append(session)
    terminal = holder[0].transcript.nodes[-1]
    assert terminal.reason == "INCOMPLETE_SCOPE_EXIT"
    assert isinstance(
        terminal.aborted_stage_index, partial.PartialNativeNotApplicableV1
    )


def test_low_level_verifier_api_routes_explicit_sites_by_stage() -> None:
    _registry, _stage, boundary = _authorities()

    def selected(stage, path):
        return next(
            row
            for row in boundary.boundaries
            if row.stage.value == stage.value and row.target_path == path
        )

    initial = selected(
        partial.PartialNativeStageV1.INITIAL_ACQUISITION,
        "acquisition.initial_engine_ground_draws",
    )
    closed = selected(
        (
            partial.PartialNativeStageV1
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        ),
        "closure.reconciliation_engine_ground_draws",
    )

    with _activation("stage-neutral-dispatch"):
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        runtime.exit_owned_stage_v1()
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.INITIAL_ACQUISITION
        )
        runtime.emit_owned_sum_v1(
            initial.boundary_key,
            initial.target_path,
            3,
        )
        runtime.exit_owned_stage_v1()
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.INITIAL_MODEL_BUILD
        )
        runtime.exit_owned_stage_v1()
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.FAILED_ABSTRACT_PREFIX
        )
        runtime.exit_owned_stage_v1()
        runtime.enter_owned_stage_v1(
            (
                partial.PartialNativeStageV1
                .CLOSED_RECONCILIATION_AND_TERMINALIZATION
            )
        )
        runtime.emit_owned_sum_v1(
            closed.boundary_key,
            closed.target_path,
            5,
        )
        runtime.exit_owned_stage_v1()
        transcript = runtime.complete_owned_occurrence_v1()

    events = [
        row
        for row in transcript.nodes
        if type(row) is partial.PartialNativeOperationEventV1
    ]
    assert [(row.stage_kind, row.path, row.amount) for row in events] == [
        (
            partial.PartialNativeStageV1.INITIAL_ACQUISITION,
            "acquisition.initial_engine_ground_draws",
            3,
        ),
        (
            (
                partial.PartialNativeStageV1
                .CLOSED_RECONCILIATION_AND_TERMINALIZATION
            ),
            "closure.reconciliation_engine_ground_draws",
            5,
        ),
    ]
    assert tuple(inspect.signature(runtime.emit_owned_operation_v1).parameters) == (
        "dispatch_key",
        "amount",
    )


def test_public_dispatch_key_cannot_be_minted_by_a_nonowner_callback() -> None:
    with _activation("nonowner-dispatch") as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        runtime.exit_owned_stage_v1()
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.INITIAL_ACQUISITION
        )
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="registered operation owner",
        ):
            runtime.emit_owned_operation_v1(
                "engine.draw.ground-sample",
                1,
            )
        transcript = session.transcript

    assert transcript.nodes[-1].reason == "OPERATION_OWNER_MISMATCH"
    assert not any(
        type(row) is partial.PartialNativeOperationEventV1
        for row in transcript.nodes
    )


def test_cloned_owner_code_with_forged_globals_fails_closed() -> None:
    with _activation("cloned-owner-code") as session:
        _enter_initial_model_stage()
        exact = sequential._ExactGridRejectionV1(  # noqa: SLF001
            1,
            0,
            Fraction(1, 2),
            2,
        )
        clone = FunctionType(
            sequential._ExactGridRejectionV1.rejects.__code__,  # noqa: SLF001
            dict(sequential.__dict__),
        )
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="registered operation owner",
        ):
            clone(exact, 0)
        transcript = session.transcript

    assert transcript.nodes[-1].reason == "OPERATION_OWNER_MISMATCH"
    assert not any(
        type(row) is partial.PartialNativeOperationEventV1
        for row in transcript.nodes
    )


def test_post_activation_same_globals_replacement_code_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _activation("same-globals-replacement-code") as session:
        _enter_initial_model_stage()
        exec(
            "def _redteam_replacement():\n"
            "    accounting_runtime.emit_owned_operation_v1(\n"
            "        'batch-planning.option-metric', amount=1)\n",
            planning_backend.__dict__,
        )
        forged = planning_backend.__dict__.pop("_redteam_replacement")
        monkeypatch.setattr(planning_backend, "_option_metric", forged)
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="registered operation owner",
        ):
            planning_backend._option_metric()  # noqa: SLF001
        transcript = session.transcript

    assert transcript.nodes[-1].reason == "OPERATION_OWNER_MISMATCH"
    assert not any(
        type(row) is partial.PartialNativeOperationEventV1
        for row in transcript.nodes
    )


def test_production_dispatch_rejects_nonunit_event_amount() -> None:
    with _activation("nonunit-production-dispatch") as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        runtime.exit_owned_stage_v1()
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.INITIAL_ACQUISITION
        )
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="one primitive",
        ):
            runtime.emit_owned_operation_v1(
                "engine.draw.ground-sample",
                2,
            )
        transcript = session.transcript

    assert transcript.nodes[-1].reason == "PRODUCTION_AMOUNT_NOT_UNIT"
    assert not any(
        type(row) is partial.PartialNativeOperationEventV1
        for row in transcript.nodes
    )


def test_unrepresentable_exception_type_is_sanitized_in_abort_metadata() -> None:
    class HostileMetadataError(RuntimeError):
        pass

    HostileMetadataError.__module__ = "private\nmodule"
    holder: list[runtime.OwnedConstructionAccountingSessionV1] = []
    with pytest.raises(HostileMetadataError):
        with _activation("hostile-exception-metadata") as session:
            holder.append(session)
            runtime.enter_owned_stage_v1(
                partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
            )
            raise HostileMetadataError("private error bytes")

    terminal = holder[0].transcript.nodes[-1]
    assert terminal.reason == "ACTIVE_SCOPE_EXCEPTION"
    for value in (terminal.exception_module, terminal.exception_qualname):
        assert type(value) is partial.PartialNativeNotApplicableV1
        assert value.reason == partial.UNREPRESENTABLE_EXCEPTION_REASON
    document = terminal.to_document()
    assert "private error bytes" not in repr(document)
    partial.verify_partial_native_occurrence_transcript_v1(holder[0].transcript)


def test_low_level_explicit_site_api_is_disabled_in_production_scope() -> None:
    registry, stage, boundary = _authorities()
    with runtime.activate_owned_construction_accounting_v1(
        occurrence_id=_id("low-level-production-forbidden"),
        recorder_id="production-shaped-recorder-v1",
        counter_registry=registry,
        stage_profile=stage,
        boundary_profile=boundary,
    ) as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="disabled in production scopes",
        ):
            runtime.emit_owned_sum_v1(
                "v6.acquisition-initial-engine-ground-draws",
                "acquisition.initial_engine_ground_draws",
                1,
            )
        transcript = session.transcript

    assert transcript.nodes[-1].reason == "LOW_LEVEL_API_FORBIDDEN"


def test_open_stage_is_rejected_by_five_stage_runtime() -> None:
    with _activation("open-stage-rejected") as session:
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="outside the exact five-stage profile",
        ):
            runtime.enter_owned_stage_v1(
                registry_v6.ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION
            )
        transcript = session.transcript

    terminal = transcript.nodes[-1]
    assert terminal.reason == "STAGE_OUTSIDE_FIVE_STAGE_PROFILE"
    assert isinstance(
        terminal.aborted_stage_index, partial.PartialNativeNotApplicableV1
    )


def test_unknown_dispatch_fails_closed_without_stage_or_path_inference() -> None:
    with _activation("unknown-dispatch") as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        runtime.exit_owned_stage_v1()
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.INITIAL_ACQUISITION
        )
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="no emittable boundary",
        ):
            runtime.emit_owned_operation_v1("unknown.physical-operation")
        transcript = session.transcript

    assert transcript.nodes[-1].reason == "UNKNOWN_OR_STAGE_UNBOUND_DISPATCH"
    assert not any(
        type(row) is partial.PartialNativeOperationEventV1
        for row in transcript.nodes
    )


def test_ambiguous_stage_dispatch_fails_closed() -> None:
    registry, stage, official = _authorities()
    selected = next(
        row
        for row in official.boundaries
        if row.stage.value == "INITIAL_ACQUISITION"
        and row.dispatch_key == "engine.draw.ground-sample"
    )
    duplicate = replace(
        selected,
        boundary_key="test.ambiguous-engine-ground-sample",
    )

    class AmbiguousBoundaryProfile:
        counter_registry_id = official.counter_registry_id
        stage_profile_id = official.stage_profile_id
        manifest_id = _id("synthetic-ambiguous-boundary-profile")
        boundaries = tuple(
            sorted((*official.boundaries, duplicate), key=lambda row: row.boundary_key)
        )
        by_key = {row.boundary_key: row for row in boundaries}

        def validate_official(self) -> None:
            # Synthetic negative control: the runtime must remain fail-closed
            # even if an upstream profile verifier were defective.
            return None

        def to_document(self) -> dict[str, str]:
            return {"manifest_id": self.manifest_id}

    with runtime.activate_owned_construction_accounting_v1(
        occurrence_id=_id("ambiguous-dispatch"),
        recorder_id="ambiguous-dispatch-recorder-v1",
        counter_registry=registry,
        stage_profile=stage,
        boundary_profile=AmbiguousBoundaryProfile(),
    ) as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        runtime.exit_owned_stage_v1()
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.INITIAL_ACQUISITION
        )
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="multiple emittable boundaries",
        ):
            runtime.emit_owned_operation_v1("engine.draw.ground-sample")
        transcript = session.transcript

    assert transcript.nodes[-1].reason == "AMBIGUOUS_STAGE_DISPATCH"
    assert not any(
        type(row) is partial.PartialNativeOperationEventV1
        for row in transcript.nodes
    )
