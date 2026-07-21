from __future__ import annotations

from dataclasses import replace
import hashlib
from types import SimpleNamespace

import pytest

from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    AccessEventV1,
    AccessOperation,
    AccessRouteScope,
    PRESELECTION_READ_OPERATIONS,
    ProtocolSequenceProfileV1,
)
from acfqp.accounting_v1 import (
    RouteKindEnum,
    SHARED_AXES,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import NativeCounterRecorderV1
from acfqp.phase3e_runner_v1 import (
    COUNTER_COMPLETENESS_GATE_STATUS,
    OFFICIAL_EXECUTION_ALLOWED,
    OFFICIAL_N_BREAK_EVEN,
    OFFICIAL_SCALAR_COST,
    Phase3EDecisionAuthorizationV1,
    Phase3EPreselectionReadV1,
    Phase3ERouteExecutionV1,
    Phase3ERunnerV1Error,
    PreparedPhase3ERunV1,
    UNASSIGNED_POSTFREEZE_OPERATIONAL_LEAVES,
    UNRESOLVED_OFFICIAL_EXECUTION_OBLIGATIONS,
    WORKLOAD_ECONOMICS_GATE_STATUS,
    _preselection_reference_id_v1,
    _require_selected_access_trace,
    run_phase3e,
)
from acfqp.phase3e_local_semantics_v1 import (
    LocalSolverOutcome,
    LocalTransactionResultV1,
    _seal_trusted_execution_v1,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteComparison,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TIGHT_PREEXECUTION_UPPER,
    TypedNotApplicable,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _raw_prepared() -> PreparedPhase3ERunV1:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    context = RouteDecisionContextV1(
        _id("preregistration"),
        _id("protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        _id("structural"),
        _id("query"),
        _id("selected-plan"),
        _id("threshold"),
        _id("epoch"),
        _id("occurrence"),
        _id("attempt"),
    )
    common_recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
    )
    common_recorder.add("common.abstract_bellman_backups", 4)
    common_recorder.add("common.abstract_audit_obligations", 1)
    common = common_recorder.seal()
    not_applicable = TypedNotApplicable(
        "local authority is unavailable in the partial semantic profile"
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        not_applicable,
        not_applicable,
        not_applicable,
        common.work_vector.work_vector_id,
    )
    upper = RouteUpperBoundEnvelopeV1(
        context.preregistration_id,
        context.protocol_id,
        context.comparison_profile_id,
        context.counter_registry_id,
        context.structural_id,
        context.query_id,
        context.selected_plan_id,
        context.threshold_profile_id,
        context.build_epoch_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        TypedNotApplicable("fallback has no local transaction"),
        TypedNotApplicable("fallback has no local transaction index"),
        TypedNotApplicable("fallback is attempt-scoped"),
        TypedNotApplicable("fallback has no causal evidence"),
        _id("caps"),
        _id("cardinality"),
        _id("formula"),
        RouteKind.DIRECT_FALLBACK,
        TIGHT_PREEXECUTION_UPPER,
        tuple((axis, 100) for axis in SHARED_AXES),
    )
    decision = MarginalRouteDecisionV1(
        point.decision_point_id,
        TypedNotApplicable("no authoritative causal search"),
        TypedNotApplicable("no authoritative local upper"),
        upper.route_upper_bound_envelope_id,
        RouteSelection.FALLBACK,
        RouteComparison.MISSING_LOCAL_UPPER,
        upper.route_upper_bound_envelope_id,
    )
    reusable_rapm_id = _id("reusable-rapm")
    failed_certificate_id = _id("failed-certificate")
    action_catalogue_id = _id("action-catalogue")
    bound_reads = {
        AccessOperation.READ_FROZEN_RAPM: reusable_rapm_id,
        AccessOperation.READ_FROZEN_BUILD_EPOCH: context.build_epoch_id,
        AccessOperation.READ_FAILED_CERTIFICATE: failed_certificate_id,
        AccessOperation.READ_SELECTED_PLAN: context.selected_plan_id,
        AccessOperation.READ_ACTION_CATALOGUE: action_catalogue_id,
        AccessOperation.READ_FRONTIER_IDENTITIES: _preselection_reference_id_v1(
            AccessOperation.READ_FRONTIER_IDENTITIES,
            point.frontier_snapshot_id,
        ),
        AccessOperation.READ_PROOF_CIRCUIT_METADATA: _preselection_reference_id_v1(
            AccessOperation.READ_PROOF_CIRCUIT_METADATA,
            point.causal_evidence_id,
        ),
        AccessOperation.READ_PREREGISTERED_CARDINALITIES: upper.cardinality_evidence_id,
        AccessOperation.READ_CAP_REGISTRY: upper.route_cap_profile_id,
        AccessOperation.READ_FORMULA_REGISTRY: upper.formula_id,
        AccessOperation.READ_PROFILE_REGISTRY: context.comparison_profile_id,
    }
    reads = tuple(
        Phase3EPreselectionReadV1(operation, bound_reads[operation])
        for operation in PRESELECTION_READ_OPERATIONS
    )
    return PreparedPhase3ERunV1(
        context,
        point,
        reusable_rapm_id,
        failed_certificate_id,
        action_catalogue_id,
        reads,
        common,
        # These are deliberately raw, self-hashed transport objects.  The
        # runner must refuse them before either executor can be invoked.
        Phase3EDecisionAuthorizationV1(decision, upper, ()),
    )


def test_run_phase3e_fails_closed_before_execution_without_semantic_authority() -> None:
    prepared = _raw_prepared()
    calls = {"local": 0, "fallback": 0}

    def local(*_args):
        calls["local"] += 1
        return Phase3ERouteExecutionV1(_id("local-result"), True)

    def fallback(*_args):
        calls["fallback"] += 1
        return Phase3ERouteExecutionV1(_id("fallback-result"), True)

    with pytest.raises(
        Phase3ERunnerV1Error,
        match="requires semantic route-decision and selected-upper authority",
    ):
        run_phase3e(
            prepared,
            local_executor=local,
            fallback_executor=fallback,
        )
    assert calls == {"local": 0, "fallback": 0}


def test_preselection_read_registry_is_complete_before_authority_check() -> None:
    prepared = _raw_prepared()
    missing = replace(prepared, preselection_reads=prepared.preselection_reads[:-1])
    with pytest.raises(Phase3ERunnerV1Error, match="every allowed preselection"):
        run_phase3e(
            missing,
            local_executor=lambda *_: None,
            fallback_executor=lambda *_: None,
        )

    mutable = replace(
        prepared,
        preselection_reads=list(prepared.preselection_reads),  # type: ignore[arg-type]
    )
    with pytest.raises(Phase3ERunnerV1Error, match="immutable typed tuple"):
        run_phase3e(
            mutable,
            local_executor=lambda *_: None,
            fallback_executor=lambda *_: None,
        )


@pytest.mark.parametrize(
    "operation",
    (
        AccessOperation.READ_FAILED_CERTIFICATE,
        AccessOperation.READ_ACTION_CATALOGUE,
    ),
)
def test_preselection_certificate_and_action_catalogue_reads_bind_exact_ids(
    operation: AccessOperation,
) -> None:
    prepared = _raw_prepared()
    attacked_reads = tuple(
        replace(row, artifact_id=_id(f"foreign-{operation.value}"))
        if row.operation is operation
        else row
        for row in prepared.preselection_reads
    )
    attacked = replace(prepared, preselection_reads=attacked_reads)
    with pytest.raises(
        Phase3ERunnerV1Error,
        match=f"preselection read {operation.value} is not bound",
    ):
        run_phase3e(
            attacked,
            local_executor=lambda *_: None,
            fallback_executor=lambda *_: None,
        )


def test_prepared_common_work_must_be_the_decision_point_reference() -> None:
    prepared = _raw_prepared()
    changed_point = replace(
        prepared.decision_point,
        common_prefix_work_id=_id("unrelated-common-prefix"),
    )
    changed = replace(prepared, decision_point=changed_point)
    with pytest.raises(Phase3ERunnerV1Error, match="common-prefix native work"):
        run_phase3e(
            changed,
            local_executor=lambda *_: None,
            fallback_executor=lambda *_: None,
        )


def test_prepared_common_projection_bundle_must_replay_exactly() -> None:
    prepared = _raw_prepared()
    forged_comparison = replace(
        prepared.common_prefix_work.comparison_vector,
        subject_id=_id("foreign-common-subject"),
    )
    forged_work = replace(
        prepared.common_prefix_work,
        comparison_vector=forged_comparison,
    )
    forged = replace(prepared, common_prefix_work=forged_work)
    with pytest.raises(Phase3ERunnerV1Error):
        run_phase3e(
            forged,
            local_executor=lambda *_: None,
            fallback_executor=lambda *_: None,
        )


def test_vertical_slice_constants_cannot_be_mistaken_for_official_gate() -> None:
    assert OFFICIAL_EXECUTION_ALLOWED is False
    assert OFFICIAL_SCALAR_COST is None
    assert OFFICIAL_N_BREAK_EVEN is None
    assert WORKLOAD_ECONOMICS_GATE_STATUS.endswith("NOT_RUN")
    assert COUNTER_COMPLETENESS_GATE_STATUS.endswith("NOT_RUN")
    assert UNASSIGNED_POSTFREEZE_OPERATIONAL_LEAVES == (
        "common.hash_invocations",
    )
    assert UNRESOLVED_OFFICIAL_EXECUTION_OBLIGATIONS == (
        "ALL_PATH_NATIVE_HASH_IO_AND_RUNTIME_INSTRUMENTATION",
        "SEALED_MODEL_ONLY_RUNTIME_CAP_AND_TRACE_AUTHORITY",
        "MODEL_FAILURE_PREPARATION_OCCURRENCE_CHARGING_AND_EXCLUDED_WORK",
        "REGISTERED_DEPENDENT_HORIZON_FIXTURE_AND_PRODUCTION_TRANSACTION_TWO",
        "PRODUCTION_REBUILD_SOURCE_AND_SEALED_RETRY_INTEGRATION",
        "REMAINING_TERMINAL_BRANCH_AND_CAMPAIGN_COVERAGE",
        "DURABLE_EXACT_INFEASIBILITY_PROOF_PAYLOAD_AND_VERIFIER",
        "SELECTED_ROUTE_GROUND_INPUTS_AND_INDEPENDENT_SEMANTIC_BUNDLE_VERIFIER",
        "ALL_PATH_BUNDLE_AND_REGISTERED_WORKLOAD_GATE",
    )


def test_unregistered_preselection_operation_cannot_enter_prepared_input() -> None:
    with pytest.raises(Phase3ERunnerV1Error, match="not an allowed"):
        Phase3EPreselectionReadV1(
            AccessOperation.KERNEL_STEP,
            _id("forbidden-ground-step"),
        )


def test_route_completion_transport_without_semantic_authority_is_rejected() -> None:
    with pytest.raises(Phase3ERunnerV1Error, match="route-specific trusted"):
        Phase3ERouteExecutionV1(_id("plausible-result"), True)


def test_no_candidate_local_trace_binds_worker_and_omits_postaudit() -> None:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    transaction_id = _id("negative-local-transaction")
    recorder = NativeCounterRecorderV1(
        subject_id=transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
    )
    recorder.record_route_completion(success=False)
    work = recorder.seal().work_vector
    worker_binding_id = _id("negative-local-worker-result")
    local_result = LocalTransactionResultV1(
        route_decision_context_id=_id("negative-local-context"),
        decision_point_id=_id("negative-local-point"),
        transaction_id=transaction_id,
        route_attempt_id=_id("negative-local-attempt"),
        query_id=_id("negative-local-query"),
        selected_plan_id=_id("negative-local-plan"),
        route_cap_profile_id=_id("negative-local-cap"),
        selected_upper_id=_id("negative-local-upper"),
        work_vector_id=work.work_vector_id,
        capability_binding_id=_id("negative-local-capability"),
        worker_result_binding_id=worker_binding_id,
        runtime_attestation_binding_id=_id("negative-local-runtime"),
        candidate_overlay_binding_id=TypedNotApplicable("no candidate"),
        stitched_plan_binding_id=TypedNotApplicable("no candidate"),
        outcome=LocalSolverOutcome.SEARCH_CAP_EXHAUSTED,
        search_complete=False,
        cap_reason="max_policy_assignments",
    )
    semantic = _seal_trusted_execution_v1(
        local_result=local_result,
        post_audit=None,
        work_vector=work,
    )
    execution = SimpleNamespace(
        semantic_execution=semantic,
        artifact_id=local_result.local_transaction_result_id,
    )
    operations = (
        (AccessOperation.LOCAL_SLICE_MATERIALIZATION, None),
        (AccessOperation.LOCAL_CAPABILITY_COMPILATION, None),
        (
            AccessOperation.LOCAL_CAPABILITY_ARTIFACT,
            local_result.capability_binding_id,
        ),
        (AccessOperation.LOCAL_WORKER_LAUNCH, None),
        (AccessOperation.LOCAL_WORKER_RESULT_ARTIFACT, worker_binding_id),
    )
    events = tuple(
        AccessEventV1(
            index,
            local_result.route_attempt_id,
            local_result.decision_point_id,
            operation,
            AccessRouteScope.LOCAL,
            artifact_id,
        )
        for index, (operation, artifact_id) in enumerate(operations, start=1)
    )
    log = AccessEventLogV1(
        local_result.route_attempt_id,
        local_result.decision_point_id,
        ProtocolSequenceProfileV1().protocol_sequence_profile_id,
        events,
    )
    _require_selected_access_trace(
        selected=RouteSelection.LOCAL,
        execution=execution,  # type: ignore[arg-type]
        log=log,
        freeze_after_sequence=0,
    )

    wrong_worker = replace(
        events[-1], artifact_id=_id("another-worker-result")
    )
    attacked = replace(log, events=events[:-1] + (wrong_worker,))
    with pytest.raises(Phase3ERunnerV1Error, match="isolated worker result"):
        _require_selected_access_trace(
            selected=RouteSelection.LOCAL,
            execution=execution,  # type: ignore[arg-type]
            log=attacked,
            freeze_after_sequence=0,
        )
