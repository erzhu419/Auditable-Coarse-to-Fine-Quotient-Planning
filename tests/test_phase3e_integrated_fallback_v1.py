from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

import acfqp.phase3e_isolated_fallback_v1 as isolated_fallback_module

from acfqp.access_protocol_v1 import (
    AccessOperation,
    PRESELECTION_READ_OPERATIONS,
    ProtocolSequenceProfileV1,
)
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    RouteKindEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    official_actual_projection_profile_v1,
)
from acfqp.frozen_phase3c import load_frozen_phase3c_world
from acfqp.native_recorder_v1 import NativeCounterRecorderV1
from acfqp.marginal_accounting_v1 import derive_marginal_work_aggregate_v1
from acfqp.phase3e_isolated_fallback_v1 import (
    ISOLATED_FALLBACK_EXECUTOR_SEMANTICS_ID,
    ISOLATED_FALLBACK_RUNTIME_ENTRYPOINT,
    IsolatedGroundFallbackExecutorInputsV1,
    IsolatedFallbackPostFreezeConstructorV1,
    Phase3EIsolatedFallbackV1Error,
    isolated_ground_fallback_executor_configuration_id_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackOutcome,
    SEALED_ROUTE_CAP_PROFILE_KEY,
    build_ground_fallback_cardinality_evidence_v1,
    derive_safe_chain_fallback_cardinality_bound_v1,
    derive_safe_chain_fallback_cardinality_source_v1,
    safe_chain_fallback_context_identity_v1,
)
from acfqp.phase3e_runner_v1 import (
    Phase3EDecisionAuthorizationV1,
    Phase3EPreselectionReadV1,
    Phase3ERouteExecutionFailedV1,
    PreparedPhase3ERunV1,
    _preselection_reference_id_v1,
    verify_failed_route_evidence_v1,
)
from acfqp.phase3e_sealed_executor_v1 import (
    ExecutorRecipeV1,
    RuntimeFactoryCardinalityV1,
    RuntimeTreeCASV1,
    MergedSealedRouteExecutionWorkV1,
    SealedExecutorConstructionAccountingV1,
    SealedExecutorConstructionReceiptV1,
    SealedExecutorExecutionMergeProofV1,
    SealedPostFreezeExecutorFactoryV1,
    verify_sealed_factory_execution_merge_v1,
)
from acfqp.phase3e_two_stage_accounting_v1 import (
    AccessTraceReconciliationEvidenceV1,
    AccountingCoreStage,
    VerificationChargeObligationV1,
    VerificationChargePlanV1,
    seal_accounting_core_v1,
)
from acfqp.phase3e_occurrence_runner_v1 import (
    OccurrenceClosureCodeV1,
    run_phase3e_occurrence_v1,
)
from acfqp.route_upper_formula_v1 import (
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationV1Error,
    TerminalRouteEvidenceBundleV1,
    derive_guarded_marginal_route_decision_v1,
    semantic_verifier_spec_v1,
    verify_actual_projection_semantics_v1,
    verify_ground_fallback_semantics_v1,
    verify_marginal_route_decision_semantics_v1,
    verify_route_upper_semantics_v1,
    verify_safe_chain_fallback_cardinality_semantics_v1,
    verify_terminal_classification_semantics_v1,
    verify_work_vector_semantics_v1,
)


ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:phase3e-integrated-fallback-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def _verification_record(
    role: SemanticRole,
    lane: LaneEnum = LaneEnum.OPERATIONAL,
) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(role)
    return CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(lane),
        1,
        recorder_id=(
            "phase3e-integrated-"
            f"{role.value.lower()}-{lane.value.lower()}-v1"
        ),
    )


def _exact_safe_chain_cap() -> GroundFallbackCapProfileV1:
    return GroundFallbackCapProfileV1(
        max_states_expanded=20,
        max_actions_evaluated=48,
        max_ground_steps=48,
        max_outcome_rows=192,
        max_bellman_backups=5_696,
        max_composed_candidates=5_696,
        max_cap_checks=5_815,
        max_positive_outcomes_per_step=4,
        reserved_route_cap_checks=3,
        profile_key=SEALED_ROUTE_CAP_PROFILE_KEY,
    )


def test_run_phase3e_executes_authorized_exact_fallback_after_freeze(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Close the cardinality -> upper -> decision -> real fallback slice."""

    world = load_frozen_phase3c_world(ROOT / "artifacts" / "phase3c")
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    identities = safe_chain_fallback_context_identity_v1(world)
    context = RouteDecisionContextV1(
        _id("preregistration"),
        _id("protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        identities["structural_id"],
        identities["query_id"],
        _id("failed-selected-plan"),
        _id("threshold-profile"),
        identities["build_epoch_id"],
        _id("logical-occurrence"),
        _id("route-attempt"),
    )

    # The decision-point schema binds the final common WorkVector ID.  Reserve
    # that deterministic ID, perform the three semantic checks, then require
    # the operation recorder to materialize exactly the reserved vector.
    reserved = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-integrated-common-v1",
    )
    reserved_common = reserved.seal()
    na = TypedNotApplicable(
        "transaction does not apply to the direct-fallback marginal upper"
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        na,
        TypedNotApplicable("direct fallback has no local frontier"),
        TypedNotApplicable("no authoritative local causal search"),
        reserved_common.work_vector.work_vector_id,
    )
    binding = AttestationContextV1(context, point.decision_point_id, na, 10)
    cap = _exact_safe_chain_cap()
    source = derive_safe_chain_fallback_cardinality_source_v1(
        world=world,
        context=context,
        decision_point=point,
        cap_profile=cap,
        frozen_at_protocol_step=1,
    )
    runtime_cas = RuntimeTreeCASV1((tmp_path / "runtime-cas").resolve())
    runtime_manifest = runtime_cas.snapshot_build_tree(ROOT / "src")
    runtime_cardinality = RuntimeFactoryCardinalityV1.from_manifest(
        runtime_manifest
    )
    bound = derive_safe_chain_fallback_cardinality_bound_v1(
        source=source,
        cap_profile=cap,
        runtime_factory_cardinality=runtime_cardinality,
    )
    cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=point,
        cap_profile=cap,
        bound=bound,
    )

    cardinality_result = verify_safe_chain_fallback_cardinality_semantics_v1(
        cardinality,
        source=source,
        bound=bound,
        frozen_world=world,
        context=context,
        decision_point=point,
        cap_profile=cap,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.CARDINALITY_EVIDENCE
        ),
        registry=registry,
        runtime_factory_cardinality=runtime_cardinality,
        runtime_manifest=runtime_manifest,
    )

    formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=cap,
    )
    upper, proof = derive_route_upper_v1(
        context=context,
        decision_point=point,
        cardinality=cardinality,
        cap_profile=cap,
        registry=registry,
        profile=profile,
        formula=formula,
    )
    upper_result = verify_route_upper_semantics_v1(
        upper,
        derivation_proof=proof,
        cardinality_result=cardinality_result,
        context=context,
        decision_point=point,
        cap_profile=cap,
        formula=formula,
        transaction=None,
        causal=None,
        binding=binding,
        verification_work_record=_verification_record(SemanticRole.ROUTE_UPPER),
        registry=registry,
    )

    decision = derive_guarded_marginal_route_decision_v1(
        context=context,
        decision_point=point,
        fallback_upper_result=upper_result,
        local_upper_result=None,
        causal_result=None,
        binding=binding,
    )
    assert decision.selected_route is RouteSelection.FALLBACK
    decision_result = verify_marginal_route_decision_semantics_v1(
        decision,
        context=context,
        decision_point=point,
        fallback_upper_result=upper_result,
        causal_result=None,
        local_upper_result=None,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.ROUTE_DECISION
        ),
        registry=registry,
    )
    charged_results = (cardinality_result, upper_result, decision_result)
    common = reserved_common
    common_freeze_step = min(
        result.binding.verified_at_protocol_step for result in charged_results
    ) - 1
    common_core = seal_accounting_core_v1(
        recorded_work=common,
        binding=AttestationContextV1(
            context,
            point.decision_point_id,
            na,
            common_freeze_step,
        ),
        core_stage=AccountingCoreStage.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        actual_profile=official_actual_projection_profile_v1(registry, profile),
    )
    common_plan = VerificationChargePlanV1.for_core(
        common_core,
        plan_frozen_at_protocol_step=common_freeze_step,
        obligations=tuple(
            VerificationChargeObligationV1.for_role(
                ordinal=index,
                artifact_id=result.attestation.artifact_id,
                role=result.role,
                expected_result=result.outcome,
                verified_at_protocol_step=result.binding.verified_at_protocol_step,
                verification_work_record=result.verification_work_record,
                binding=result.binding,
            )
            for index, result in enumerate(charged_results)
        ),
    )

    failed_certificate_id = _id("failed-abstract-certificate")
    action_catalogue_id = identities["bound_ground_action_catalogue_id"]
    bound_read_ids = {
        AccessOperation.READ_FROZEN_RAPM: identities["portable_rapm_id"],
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
        AccessOperation.READ_PREREGISTERED_CARDINALITIES: (
            upper.cardinality_evidence_id
        ),
        AccessOperation.READ_CAP_REGISTRY: upper.route_cap_profile_id,
        AccessOperation.READ_FORMULA_REGISTRY: upper.formula_id,
        AccessOperation.READ_PROFILE_REGISTRY: context.comparison_profile_id,
    }
    reads = tuple(
        Phase3EPreselectionReadV1(
            operation,
            bound_read_ids.get(operation, _id(f"read-{operation.value}")),
        )
        for operation in PRESELECTION_READ_OPERATIONS
    )
    prepared = PreparedPhase3ERunV1(
        context,
        point,
        identities["portable_rapm_id"],
        failed_certificate_id,
        action_catalogue_id,
        reads,
        common,
        Phase3EDecisionAuthorizationV1(
            decision_result,
            upper_result,
            (cardinality_result, upper_result, decision_result),
        ),
        two_stage_accounting_profile=True,
        common_accounting_core=common_core,
        common_verification_charge_plan=common_plan,
    )
    fallback_inputs = IsolatedGroundFallbackExecutorInputsV1(
        world,
        context,
        point,
        upper,
        cardinality,
        bound,
        cap,
        decision_result,
        upper_result,
        cardinality_result,
        runtime_cardinality,
    )
    fallback_recipe = ExecutorRecipeV1(
        runtime_manifest.runtime_tree_id,
        RouteSelection.FALLBACK,
        ISOLATED_FALLBACK_EXECUTOR_SEMANTICS_ID,
        ISOLATED_FALLBACK_RUNTIME_ENTRYPOINT,
        isolated_ground_fallback_executor_configuration_id_v1(fallback_inputs),
    )
    prepared = replace(
        prepared,
        runtime_tree_id=fallback_recipe.runtime_tree_id,
        executor_recipe_id=fallback_recipe.executor_recipe_id,
        sealed_executor_profile=True,
    )
    fallback_constructor = IsolatedFallbackPostFreezeConstructorV1(
        fallback_inputs,
        registry,
        profile,
    )

    def sealed_fallback_factory():
        return SealedPostFreezeExecutorFactoryV1(
            fallback_recipe,
            runtime_cas,
            fallback_constructor,
        )

    fallback_executor = sealed_fallback_factory()

    def forbidden_local(*_args):
        raise AssertionError("FALLBACK decision executed the local route")

    try:
        occurrence = run_phase3e_occurrence_v1(
            prepared,
            local_executor=forbidden_local,
            fallback_executor=fallback_executor,
            registry=registry,
            comparison_profile=profile,
        )
    except Phase3ERouteExecutionFailedV1 as error:
        original = error.original_error
        if isinstance(original, Phase3EIsolatedFallbackV1Error) and (
            "bwrap:" in str(original) or "requires bubblewrap" in str(original)
        ):
            pytest.skip(f"bubblewrap namespace unavailable: {original}")
        raise
    if occurrence.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE:
        evidence = occurrence.failed_route_evidence
        assert evidence is not None
        message = evidence.original_error_message
        if any(
            marker in message
            for marker in ("bwrap:", "requires bubblewrap", "NETLINK_ROUTE")
        ):
            pytest.skip(f"bubblewrap namespace unavailable: {message}")
        pytest.fail(f"unexpected fallback protocol closure: {message}")
    result = occurrence.decision_runs[0]
    execution = fallback_inputs
    assert occurrence.closure_code is OccurrenceClosureCodeV1.FULL_GROUND_FALLBACK
    assert len(occurrence.work_components) == 2
    assert occurrence.transactions == ()
    assert dict(occurrence.occurrence_work.aggregate_values)[
        "kernel_transition_calls"
    ] == 48
    assert occurrence.official_execution_allowed is False
    assert occurrence.official_scalar_cost is None
    assert occurrence.official_N_break_even is None
    assert result.selected_route is RouteSelection.FALLBACK
    selected_accounting = result.selected_two_stage_accounting
    assert selected_accounting is not None
    access_evidence = selected_accounting.nonsemantic_evidence[0]
    assert type(access_evidence) is AccessTraceReconciliationEvidenceV1
    assert access_evidence.selected_route is RouteSelection.FALLBACK
    assert selected_accounting.core.route_kind is RouteKindEnum.DIRECT_FALLBACK
    assert result.upper_compliance == "WITHIN_SELECTED_UPPER"
    assert result.route_execution.completed is True
    assert result.route_execution.native_execution_work is not None
    assert result.route_execution.semantic_execution is not None
    assert result.route_execution.semantic_outcome == "FEASIBLE_CERTIFIED"
    construction = fallback_executor.construction_accounting
    assert construction is not None
    assert result.sealed_executor_profile is True
    assert result.two_stage_accounting_profile is True
    receipt = result.sealed_executor_construction_receipt
    merge_proof = result.sealed_executor_execution_merge_proof
    assert type(receipt) is SealedExecutorConstructionReceiptV1
    assert type(merge_proof) is SealedExecutorExecutionMergeProofV1
    assert receipt.postconstruction_access_event_log_id == (
        result.access_log.access_event_log_id
    )
    verify_sealed_factory_execution_merge_v1(
        MergedSealedRouteExecutionWorkV1(
            result.selected_route_work,
            merge_proof,
        ),
        factory_accounting=construction,
        delegate_work=result.route_execution.delegate_execution_work,
        registry=registry,
        comparison_profile=profile,
    )
    native = result.route_execution.native_execution_work.work_vector
    delegate_native = result.route_execution.delegate_execution_work.work_vector
    selected_native = result.selected_route_work.work_vector
    factory_native = construction.recorded_work.work_vector
    assert selected_native.value("io.staged_bytes") >= factory_native.value(
        "io.staged_bytes"
    )
    assert selected_native.value("common.hash_invocations") == factory_native.value(
        "common.hash_invocations"
    )
    assert native.value("fallback.ground_steps") == 48
    assert native.value("fallback.outcome_rows") == 192
    assert native.value("fallback.bellman_backups") == 5_696
    assert native.value("process.launches") == 1
    assert native.value("io.read_bytes") > 0
    assert native.value("io.staged_bytes") > 0
    assert native.value("io.output_bytes") > 0
    assert native.value("io.mounted_bytes_peak") > 0
    assert 0 < delegate_native.value("memory.working_bytes_peak") <= 256 * 1024 * 1024
    # Factory verification and the selected worker are simultaneously live,
    # so their independently capped working sets add in the sealed route.
    assert native.value("memory.working_bytes_peak") == (
        factory_native.value("memory.working_bytes_peak")
        + delegate_native.value("memory.working_bytes_peak")
    )
    assert result.aggregate_marginal_work.aggregate_work_vector.value(
        "common.protocol_checks"
    ) == 15
    assert result.official_execution_allowed is False
    assert result.freeze_attestation.last_preselection_sequence == len(
        PRESELECTION_READ_OPERATIONS
    )
    prefreeze = result.access_log.events[
        : result.freeze_attestation.last_preselection_sequence
    ]
    postfreeze = result.access_log.events[
        result.freeze_attestation.last_preselection_sequence :
    ]
    assert tuple(event.operation for event in prefreeze) == tuple(
        row.operation for row in prepared.preselection_reads
    )
    assert tuple(event.artifact_id for event in prefreeze) == tuple(
        row.artifact_id for row in prepared.preselection_reads
    )
    operations = tuple(event.operation for event in result.access_log.events)
    assert operations.count(AccessOperation.RESOLVE_RUNTIME_CAS) == 1
    assert operations.count(AccessOperation.OPEN_RUNTIME_PRIVATE_LEASE) == 1
    assert operations.count(AccessOperation.CONSTRUCT_SELECTED_EXECUTOR) == 1
    assert operations.count(AccessOperation.FALLBACK_SOLVER_INVOCATION) == 0
    assert operations.count(AccessOperation.FALLBACK_WORKER_LAUNCH) == 1
    assert operations.count(AccessOperation.FALLBACK_RESULT_ARTIFACT) == 1
    assert operations.count(AccessOperation.KERNEL_STEP) == 48
    assert operations.count(AccessOperation.GROUND_OUTCOME_ENUMERATION) == 48
    assert all(
        event.operation
        not in {
            AccessOperation.KERNEL_STEP,
            AccessOperation.GROUND_OUTCOME_ENUMERATION,
        }
        for event in prefreeze
    )
    assert all(
        event.sequence_number
        > result.freeze_attestation.last_preselection_sequence
        for event in postfreeze
    )
    # The adapter preserves the opaque execution provenance, so the downstream
    # semantic check does not rerun the ground solver.  This separate check is
    # not yet folded into the runner's five-check verification suffix and does
    # not automatically mint a terminal or relax an official Gate.
    fallback_result = verify_ground_fallback_semantics_v1(
        result.route_execution.semantic_execution,
        cap_profile=cap,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.GROUND_FALLBACK
        ),
        registry=registry,
    )
    assert fallback_result.outcome == "FEASIBLE_CERTIFIED"
    assert fallback_result.artifact.ground_fallback_result_id == (
        result.route_execution.artifact_id
    )
    assert execution.cardinality_result is cardinality_result
    assert GroundFallbackOutcome.FEASIBLE_CERTIFIED.value not in {
        result.status
    }

    # A plan terminal is admitted only after the runner aggregate, selected
    # upper, semantic fallback result, and successful frozen access trace are
    # joined.  The execution WorkVector alone is intentionally insufficient.
    terminal_transaction_id = result.selected_upper.transaction_id
    terminal_binding = AttestationContextV1(
        context,
        point.decision_point_id,
        terminal_transaction_id,
        len(result.access_log.events) + 1,
        LaneEnum.EVALUATION,
    )
    aggregate = result.aggregate_marginal_work
    work_result = verify_work_vector_semantics_v1(
        aggregate.aggregate_work_vector,
        binding=terminal_binding,
        verification_work_record=_verification_record(
            SemanticRole.WORK_VECTOR, LaneEnum.EVALUATION
        ),
        registry=registry,
    )
    actual_result = verify_actual_projection_semantics_v1(
        vector=aggregate.aggregate_work_vector,
        claimed_comparison=aggregate.aggregate_comparison_vector,
        projection_proof=aggregate.aggregate_projection_proof,
        binding=terminal_binding,
        verification_work_record=_verification_record(
            SemanticRole.ACTUAL_PROJECTION, LaneEnum.EVALUATION
        ),
        registry=registry,
    )
    terminal_evidence = (
        work_result,
        actual_result,
        upper_result,
        decision_result,
        fallback_result,
    )

    def terminal_route_bundle(
        execution_work,
        verification_work,
        marginal_work,
        access_log=result.access_log,
        freeze=result.freeze_attestation,
    ):
        return TerminalRouteEvidenceBundleV1(
            execution_work,
            verification_work,
            marginal_work,
            access_log,
            freeze,
            ProtocolSequenceProfileV1(),
            result.selected_work_result,
            sealed_executor_profile=True,
            sealed_executor_construction_accounting=(
                result.route_execution.sealed_executor_construction_accounting
            ),
            sealed_delegate_execution_work=(
                result.route_execution.delegate_execution_work
            ),
            sealed_executor_execution_merge_proof=(
                result.route_execution.sealed_executor_execution_merge_proof
            ),
        )
    terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.FULL_GROUND_FALLBACK,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        terminal_transaction_id,
        aggregate.aggregate_work_vector.work_vector_id,
        tuple(
            sorted(
                row.attestation.verification_attestation_id
                for row in terminal_evidence
            )
        ),
        aggregate.aggregate_comparison_vector.comparison_vector_id,
        aggregate.aggregate_projection_proof.actual_projection_proof_id,
        aggregate.aggregation_proof.marginal_work_aggregation_proof_id,
        result.freeze_attestation.route_decision_freeze_attestation_id,
        result.access_log.access_event_log_id,
    )
    valid_terminal_bundle = terminal_route_bundle(
        result.selected_route_work,
        result.verification_suffix_work,
        aggregate,
    )
    terminal_result = verify_terminal_classification_semantics_v1(
        terminal,
        evidence_results=terminal_evidence,
        route_evidence=valid_terminal_bundle,
        binding=terminal_binding,
        verification_work_record=_verification_record(
            SemanticRole.TERMINAL_CLASSIFICATION, LaneEnum.EVALUATION
        ),
        registry=registry,
    )
    assert terminal_result.outcome == TerminalClass.PLAN_CERTIFICATE.value

    with pytest.raises(ValueError, match="construction receipt differs"):
        replace(
            construction,
            recorded_work=result.route_execution.delegate_execution_work,
        )
    with pytest.raises(SemanticVerificationV1Error, match="merge does not replay"):
        replace(
            valid_terminal_bundle,
            sealed_delegate_execution_work=construction.recorded_work,
        )
    proof_attack = replace(
        merge_proof,
        delegate_work_vector_id=_id("foreign-terminal-fallback-delegate"),
    )
    with pytest.raises(SemanticVerificationV1Error, match="merge does not replay"):
        replace(
            valid_terminal_bundle,
            sealed_executor_execution_merge_proof=proof_attack,
        )
    foreign_receipt = replace(
        receipt,
        postconstruction_access_event_log_id=_id("foreign-fallback-access-log"),
    )
    foreign_construction = SealedExecutorConstructionAccountingV1(
        foreign_receipt,
        construction.recorded_work,
    )
    foreign_proof = replace(
        merge_proof,
        construction_receipt_id=(
            foreign_receipt.sealed_executor_construction_receipt_id
        ),
    )
    with pytest.raises(SemanticVerificationV1Error, match="access/freeze"):
        replace(
            valid_terminal_bundle,
            sealed_executor_construction_accounting=foreign_construction,
            sealed_executor_execution_merge_proof=foreign_proof,
        )

    # A self-consistent lower-cost aggregate cannot omit the runner's fixed
    # verification checks or the selected route's semantic-verifier work.
    # This attack preserves the genuine execution, result authority, decision,
    # access log, and upper; only its verification suffix is silently zeroed.
    zero_suffix_recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-terminal-zero-verification-suffix-v1",
    )
    zero_suffix = zero_suffix_recorder.seal()
    low_aggregate = derive_marginal_work_aggregate_v1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        execution=(
            result.selected_route_work.work_vector,
            result.selected_route_work.comparison_vector,
            result.selected_route_work.actual_projection_proof,
        ),
        verification_suffix=(
            zero_suffix.work_vector,
            zero_suffix.comparison_vector,
            zero_suffix.actual_projection_proof,
        ),
        registry=registry,
        comparison_profile=profile,
        actual_profile=official_actual_projection_profile_v1(registry, profile),
    )
    low_suffix_work_result = verify_work_vector_semantics_v1(
        low_aggregate.aggregate_work_vector,
        binding=terminal_binding,
        verification_work_record=_verification_record(
            SemanticRole.WORK_VECTOR, LaneEnum.EVALUATION
        ),
        registry=registry,
    )
    low_suffix_actual_result = verify_actual_projection_semantics_v1(
        vector=low_aggregate.aggregate_work_vector,
        claimed_comparison=low_aggregate.aggregate_comparison_vector,
        projection_proof=low_aggregate.aggregate_projection_proof,
        binding=terminal_binding,
        verification_work_record=_verification_record(
            SemanticRole.ACTUAL_PROJECTION, LaneEnum.EVALUATION
        ),
        registry=registry,
    )
    low_suffix_evidence = (
        low_suffix_work_result,
        low_suffix_actual_result,
        upper_result,
        decision_result,
        fallback_result,
    )
    low_suffix_terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.FULL_GROUND_FALLBACK,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        terminal_transaction_id,
        low_aggregate.aggregate_work_vector.work_vector_id,
        tuple(
            sorted(
                row.attestation.verification_attestation_id
                for row in low_suffix_evidence
            )
        ),
        low_aggregate.aggregate_comparison_vector.comparison_vector_id,
        low_aggregate.aggregate_projection_proof.actual_projection_proof_id,
        low_aggregate.aggregation_proof.marginal_work_aggregation_proof_id,
        result.freeze_attestation.route_decision_freeze_attestation_id,
        result.access_log.access_event_log_id,
    )
    with pytest.raises(
        SemanticVerificationV1Error, match="terminal verification suffix"
    ):
        verify_terminal_classification_semantics_v1(
            low_suffix_terminal,
            evidence_results=low_suffix_evidence,
            route_evidence=terminal_route_bundle(
                result.selected_route_work,
                zero_suffix,
                low_aggregate,
            ),
            binding=terminal_binding,
            verification_work_record=_verification_record(
                SemanticRole.TERMINAL_CLASSIFICATION, LaneEnum.EVALUATION
            ),
            registry=registry,
        )

    with pytest.raises(
        SemanticVerificationV1Error, match="complete typed runner route evidence"
    ):
        verify_terminal_classification_semantics_v1(
            terminal,
            evidence_results=terminal_evidence,
            binding=terminal_binding,
            verification_work_record=_verification_record(
                SemanticRole.TERMINAL_CLASSIFICATION, LaneEnum.EVALUATION
            ),
            registry=registry,
        )

    stale_freeze_terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.FULL_GROUND_FALLBACK,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        terminal_transaction_id,
        aggregate.aggregate_work_vector.work_vector_id,
        terminal.evidence_attestation_ids,
        aggregate.aggregate_comparison_vector.comparison_vector_id,
        aggregate.aggregate_projection_proof.actual_projection_proof_id,
        aggregate.aggregation_proof.marginal_work_aggregation_proof_id,
        _id("stale-terminal-freeze"),
        result.access_log.access_event_log_id,
    )
    with pytest.raises(
        SemanticVerificationV1Error, match="freeze/access identities"
    ):
        verify_terminal_classification_semantics_v1(
            stale_freeze_terminal,
            evidence_results=terminal_evidence,
            route_evidence=terminal_route_bundle(
                result.selected_route_work,
                result.verification_suffix_work,
                aggregate,
            ),
            binding=terminal_binding,
            verification_work_record=_verification_record(
                SemanticRole.TERMINAL_CLASSIFICATION, LaneEnum.EVALUATION
            ),
            registry=registry,
        )

    # P0 regression: a valid, same-context, lower-cost WorkVector and exact
    # projection cannot be spliced onto the expensive fallback certificate.
    low_recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-terminal-low-cost-splice-v1",
    )
    low = low_recorder.seal()
    low_work_result = verify_work_vector_semantics_v1(
        low.work_vector,
        binding=terminal_binding,
        verification_work_record=_verification_record(
            SemanticRole.WORK_VECTOR, LaneEnum.EVALUATION
        ),
        registry=registry,
    )
    low_actual_result = verify_actual_projection_semantics_v1(
        vector=low.work_vector,
        claimed_comparison=low.comparison_vector,
        projection_proof=low.actual_projection_proof,
        binding=terminal_binding,
        verification_work_record=_verification_record(
            SemanticRole.ACTUAL_PROJECTION, LaneEnum.EVALUATION
        ),
        registry=registry,
    )
    spliced_evidence = (
        low_work_result,
        low_actual_result,
        upper_result,
        decision_result,
        fallback_result,
    )
    spliced_terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.FULL_GROUND_FALLBACK,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        terminal_transaction_id,
        low.work_vector.work_vector_id,
        tuple(
            sorted(
                row.attestation.verification_attestation_id
                for row in spliced_evidence
            )
        ),
        low.comparison_vector.comparison_vector_id,
        low.actual_projection_proof.actual_projection_proof_id,
        aggregate.aggregation_proof.marginal_work_aggregation_proof_id,
        result.freeze_attestation.route_decision_freeze_attestation_id,
        result.access_log.access_event_log_id,
    )
    with pytest.raises(
        SemanticVerificationV1Error,
        match="does not bind the runner aggregate",
    ):
        verify_terminal_classification_semantics_v1(
            spliced_terminal,
            evidence_results=spliced_evidence,
            route_evidence=terminal_route_bundle(
                result.selected_route_work,
                result.verification_suffix_work,
                aggregate,
            ),
            binding=terminal_binding,
            verification_work_record=_verification_record(
                SemanticRole.TERMINAL_CLASSIFICATION, LaneEnum.EVALUATION
            ),
            registry=registry,
        )

    def fail_isolated_launch(*_args, **_kwargs):
        raise RuntimeError("injected isolated fallback launch failure")

    monkeypatch.setattr(
        isolated_fallback_module.subprocess, "run", fail_isolated_launch
    )
    failed_occurrence = run_phase3e_occurrence_v1(
        prepared,
        local_executor=forbidden_local,
        fallback_executor=sealed_fallback_factory(),
        registry=registry,
        comparison_profile=profile,
    )
    assert failed_occurrence.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE
    assert failed_occurrence.decision_runs == ()
    assert failed_occurrence.occurrence_failure_terminal is not None
    assert failed_occurrence.failed_route_evidence is not None
    failed = verify_failed_route_evidence_v1(
        failed_occurrence.failed_route_evidence,
        registry=registry,
        comparison_profile=profile,
    )
    failed_values = failed.partial_route_work.work_vector.values
    assert failed_values["process.launches"] == 1
    assert failed_values["process.exit_failures"] == 1
    assert failed_values["io.read_bytes"] > 0
    assert failed_values["io.staged_bytes"] > 0
    assert failed_values["route.failures"] == 1

    legacy_evidence = (work_result, fallback_result)
    legacy_terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.FULL_GROUND_FALLBACK,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        terminal_transaction_id,
        aggregate.aggregate_work_vector.work_vector_id,
        tuple(
            sorted(
                row.attestation.verification_attestation_id
                for row in legacy_evidence
            )
        ),
        aggregate.aggregate_comparison_vector.comparison_vector_id,
        aggregate.aggregate_projection_proof.actual_projection_proof_id,
        aggregate.aggregation_proof.marginal_work_aggregation_proof_id,
        result.freeze_attestation.route_decision_freeze_attestation_id,
        result.access_log.access_event_log_id,
    )
    with pytest.raises(
        SemanticVerificationV1Error, match="ACTUAL_PROJECTION=VALID"
    ):
        verify_terminal_classification_semantics_v1(
            legacy_terminal,
            evidence_results=legacy_evidence,
            route_evidence=terminal_route_bundle(
                result.selected_route_work,
                result.verification_suffix_work,
                aggregate,
            ),
            binding=terminal_binding,
            verification_work_record=_verification_record(
                SemanticRole.TERMINAL_CLASSIFICATION, LaneEnum.EVALUATION
            ),
            registry=registry,
        )
