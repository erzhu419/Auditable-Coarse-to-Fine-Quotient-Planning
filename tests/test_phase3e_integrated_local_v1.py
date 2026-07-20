from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

import acfqp.phase3e_local_adapter_v1 as local_adapter_module

from acfqp.access_protocol_v1 import (
    AccessOperation,
    PRESELECTION_READ_OPERATIONS,
    ProtocolSequenceProfileV1,
)
from acfqp.accounting_v1 import (
    CounterRecordV1,
    RouteKindEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.frozen_phase3c import load_frozen_phase3c_world
from acfqp.native_recorder_v1 import NativeCounterRecorderV1
from acfqp.phase3d import prepare_safe_chain_estimate_context
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    build_ground_fallback_cardinality_evidence_v1,
    derive_safe_chain_fallback_cardinality_bound_v1,
    derive_safe_chain_fallback_cardinality_source_v1,
)
from acfqp.phase3e_local_adapter_v1 import (
    AuthorizedSafeChainLocalExecutorV1,
    SafeChainLocalExecutorInputsV1,
)
from acfqp.phase3e_local_preselection_v1 import (
    build_safe_chain_local_cardinality_evidence_v1,
    derive_safe_chain_local_cardinality_bound_v1,
    derive_safe_chain_local_frontier_and_causal_v1,
    derive_safe_chain_local_preselection_source_v1,
    safe_chain_local_context_identity_v1,
    safe_chain_local_selected_plan_id_v1,
    safe_chain_local_threshold_profile_id_v1,
)
from acfqp.phase3e_local_semantics_v1 import (
    FrozenThresholdProfileV1,
    LocalSolverOutcome,
    PostAuditOutcome,
)
from acfqp.phase3e_runner_v1 import (
    Phase3EDecisionAuthorizationV1,
    Phase3EPreselectionReadV1,
    Phase3ERunnerV1Error,
    Phase3ERouteExecutionFailedV1,
    PreparedPhase3ERunV1,
    run_phase3e,
    verify_failed_route_evidence_v1,
)
from acfqp.route_upper_formula_v1 import (
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    RouteCapProfileV1,
    RouteComparison,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TransactionV1,
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
    verify_marginal_route_decision_semantics_v1,
    verify_route_upper_semantics_v1,
    verify_safe_chain_fallback_cardinality_semantics_v1,
    verify_safe_chain_local_cardinality_semantics_v1,
    verify_safe_chain_local_causal_semantics_v1,
    verify_terminal_classification_semantics_v1,
    verify_work_vector_semantics_v1,
)


ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:phase3e-integrated-local-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def _verification_record(role: SemanticRole, instance: str) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(role)
    return CounterRecordV1.observe(
        registry,
        spec.verification_counter_path,
        1,
        recorder_id=(
            "phase3e-integrated-local-"
            f"{role.value.lower()}-{instance}-verifier-v1"
        ),
    )


def _fallback_cap() -> GroundFallbackCapProfileV1:
    return GroundFallbackCapProfileV1(
        max_states_expanded=20,
        max_actions_evaluated=48,
        max_ground_steps=48,
        max_outcome_rows=192,
        max_bellman_backups=5_696,
        max_composed_candidates=5_696,
        max_cap_checks=5_812,
        max_positive_outcomes_per_step=4,
    )


def test_run_phase3e_executes_genuine_safe_chain_local_only_after_freeze(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Close the real RAPM-failure -> LOCAL worker -> post-audit slice."""

    world = load_frozen_phase3c_world(ROOT / "artifacts" / "phase3c")
    prepared_local = prepare_safe_chain_estimate_context(world)
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    identities = safe_chain_local_context_identity_v1(world)
    context = RouteDecisionContextV1(
        _id("preregistration"),
        _id("protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        identities["structural_id"],
        identities["query_id"],
        safe_chain_local_selected_plan_id_v1(prepared_local),
        safe_chain_local_threshold_profile_id_v1(prepared_local),
        identities["build_epoch_id"],
        _id("logical-occurrence"),
        _id("route-attempt"),
    )

    # Six preselection semantic authorities are genuinely replayed below:
    # causal, two cardinalities, two route uppers, and the route decision.
    # Reserve their deterministic common-prefix vector so DecisionPointV1 can
    # bind it before its own content ID enters those authorities.
    reserved = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-integrated-local-common-v1",
    )
    reserved.add("common.protocol_checks", 6)
    reserved_common = reserved.seal()

    local_cap = RouteCapProfileV1()
    frontier, causal = derive_safe_chain_local_frontier_and_causal_v1(
        prepared=prepared_local,
        context=context,
        cap_profile=local_cap,
        frontier_stage=1,
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        1,
        frontier.frontier_snapshot_id,
        causal.causal_evidence_id,
        reserved_common.work_vector.work_vector_id,
    )
    transaction = TransactionV1(
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        1,
        frontier.frontier_snapshot_id,
        local_cap.route_cap_profile_id,
    )
    local_source = derive_safe_chain_local_preselection_source_v1(
        prepared=prepared_local,
        context=context,
        frontier=frontier,
        causal=causal,
        decision_point=point,
        transaction=transaction,
        cap_profile=local_cap,
        frozen_at_protocol_step=1,
    )
    local_bound = derive_safe_chain_local_cardinality_bound_v1(
        source=local_source,
        cap_profile=local_cap,
        registry=registry,
    )
    local_cardinality = build_safe_chain_local_cardinality_evidence_v1(
        context=context,
        decision_point=point,
        transaction=transaction,
        cap_profile=local_cap,
        bound=local_bound,
    )
    local_binding = AttestationContextV1(
        context, point.decision_point_id, transaction.transaction_id, 10
    )
    causal_result = verify_safe_chain_local_causal_semantics_v1(
        causal,
        source=local_source,
        frozen_world=world,
        context=context,
        frontier=frontier,
        decision_point=point,
        transaction=transaction,
        cap_profile=local_cap,
        binding=local_binding,
        verification_work_record=_verification_record(
            SemanticRole.CAUSAL_SEARCH, "local"
        ),
        registry=registry,
    )
    local_cardinality_result = verify_safe_chain_local_cardinality_semantics_v1(
        local_cardinality,
        source=local_source,
        bound=local_bound,
        causal_result=causal_result,
        frozen_world=world,
        context=context,
        frontier=frontier,
        decision_point=point,
        transaction=transaction,
        cap_profile=local_cap,
        binding=local_binding,
        verification_work_record=_verification_record(
            SemanticRole.CARDINALITY_EVIDENCE, "local"
        ),
        registry=registry,
    )
    local_formula = official_route_upper_formula_v1(
        RouteKind.LOCAL_ATTEMPT,
        registry=registry,
        profile=profile,
        cap_profile=local_cap,
    )
    local_upper, local_proof = derive_route_upper_v1(
        context=context,
        decision_point=point,
        cardinality=local_cardinality,
        cap_profile=local_cap,
        registry=registry,
        profile=profile,
        formula=local_formula,
        transaction=transaction,
        causal=causal,
    )
    local_upper_result = verify_route_upper_semantics_v1(
        local_upper,
        derivation_proof=local_proof,
        cardinality_result=local_cardinality_result,
        context=context,
        decision_point=point,
        cap_profile=local_cap,
        formula=local_formula,
        transaction=transaction,
        causal=causal,
        binding=local_binding,
        verification_work_record=_verification_record(
            SemanticRole.ROUTE_UPPER, "local"
        ),
        registry=registry,
    )

    fallback_cap = _fallback_cap()
    fallback_source = derive_safe_chain_fallback_cardinality_source_v1(
        world=world,
        context=context,
        decision_point=point,
        cap_profile=fallback_cap,
        frozen_at_protocol_step=1,
    )
    fallback_bound = derive_safe_chain_fallback_cardinality_bound_v1(
        source=fallback_source,
        cap_profile=fallback_cap,
    )
    fallback_cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=point,
        cap_profile=fallback_cap,
        bound=fallback_bound,
    )
    no_fallback_transaction = TypedNotApplicable(
        "direct fallback has no local transaction"
    )
    fallback_binding = AttestationContextV1(
        context,
        point.decision_point_id,
        no_fallback_transaction,
        10,
    )
    fallback_cardinality_result = (
        verify_safe_chain_fallback_cardinality_semantics_v1(
            fallback_cardinality,
            source=fallback_source,
            bound=fallback_bound,
            frozen_world=world,
            context=context,
            decision_point=point,
            cap_profile=fallback_cap,
            binding=fallback_binding,
            verification_work_record=_verification_record(
                SemanticRole.CARDINALITY_EVIDENCE, "fallback"
            ),
            registry=registry,
        )
    )
    fallback_formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=fallback_cap,
    )
    fallback_upper, fallback_proof = derive_route_upper_v1(
        context=context,
        decision_point=point,
        cardinality=fallback_cardinality,
        cap_profile=fallback_cap,
        registry=registry,
        profile=profile,
        formula=fallback_formula,
    )
    fallback_upper_result = verify_route_upper_semantics_v1(
        fallback_upper,
        derivation_proof=fallback_proof,
        cardinality_result=fallback_cardinality_result,
        context=context,
        decision_point=point,
        cap_profile=fallback_cap,
        formula=fallback_formula,
        transaction=None,
        causal=None,
        binding=fallback_binding,
        verification_work_record=_verification_record(
            SemanticRole.ROUTE_UPPER, "fallback"
        ),
        registry=registry,
    )

    decision = derive_guarded_marginal_route_decision_v1(
        context=context,
        decision_point=point,
        fallback_upper_result=fallback_upper_result,
        local_upper_result=local_upper_result,
        causal_result=causal_result,
        binding=local_binding,
    )
    assert decision.selected_route is RouteSelection.LOCAL
    assert decision.comparison is RouteComparison.LOCAL_STRICTLY_DOMINATES
    assert all(
        local_value <= dict(fallback_upper.upper_bounds)[axis]
        for axis, local_value in local_upper.upper_bounds
    )
    decision_result = verify_marginal_route_decision_semantics_v1(
        decision,
        context=context,
        decision_point=point,
        fallback_upper_result=fallback_upper_result,
        causal_result=causal_result,
        local_upper_result=local_upper_result,
        binding=local_binding,
        verification_work_record=_verification_record(
            SemanticRole.ROUTE_DECISION, "local"
        ),
        registry=registry,
    )

    charged_results = (
        causal_result,
        local_cardinality_result,
        local_upper_result,
        fallback_cardinality_result,
        fallback_upper_result,
        decision_result,
    )
    actual_common_recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-integrated-local-common-v1",
    )
    for semantic_result in charged_results:
        actual_common_recorder.charge_verified_record(
            semantic_result.verification_work_record
        )
    common = actual_common_recorder.seal()
    assert common.work_vector.work_vector_id == (
        reserved_common.work_vector.work_vector_id
    )

    failed_certificate_id = _id("failed-abstract-certificate")
    action_catalogue_id = identities["bound_ground_action_catalogue_id"]
    bound_read_ids = {
        AccessOperation.READ_FROZEN_RAPM: identities["portable_rapm_id"],
        AccessOperation.READ_FROZEN_BUILD_EPOCH: context.build_epoch_id,
        AccessOperation.READ_FAILED_CERTIFICATE: failed_certificate_id,
        AccessOperation.READ_SELECTED_PLAN: context.selected_plan_id,
        AccessOperation.READ_ACTION_CATALOGUE: action_catalogue_id,
        AccessOperation.READ_FRONTIER_IDENTITIES: frontier.frontier_snapshot_id,
        AccessOperation.READ_PROOF_CIRCUIT_METADATA: causal.causal_evidence_id,
        AccessOperation.READ_PREREGISTERED_CARDINALITIES: (
            local_cardinality.cardinality_evidence_id
        ),
        AccessOperation.READ_CAP_REGISTRY: local_cap.route_cap_profile_id,
        AccessOperation.READ_FORMULA_REGISTRY: local_formula.formula_id,
        AccessOperation.READ_PROFILE_REGISTRY: profile.comparison_profile_id,
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
            local_upper_result,
            charged_results,
        ),
    )
    with pytest.raises(
        Phase3ERunnerV1Error,
        match="route-decision semantic dependency work is uncharged",
    ):
        Phase3EDecisionAuthorizationV1(
            decision_result,
            local_upper_result,
            charged_results[1:],  # omit the causal verifier work
        ).validate(context=context, decision_point=point)
    threshold_profile = FrozenThresholdProfileV1(
        context.query_id,
        prepared_local.pre_audit.regret_tolerance,
        prepared_local.pre_audit.risk_tolerance,
    )
    authorized_local = AuthorizedSafeChainLocalExecutorV1(
        SafeChainLocalExecutorInputsV1(
            prepared_local,
            context,
            point,
            transaction,
            local_upper,
            local_cardinality,
            local_bound,
            local_cap,
            threshold_profile,
            decision_result,
            local_upper_result,
            causal_result,
            local_cardinality_result,
        ),
        registry,
        profile,
    )

    saw_frozen_clean_prefix = False

    def guarded_local(prepared_run, controller, recorder):
        nonlocal saw_frozen_clean_prefix
        freeze = controller.freeze_attestation
        assert freeze is not None
        assert freeze.selected_route is RouteSelection.LOCAL
        assert len(controller.snapshot().events) == len(PRESELECTION_READ_OPERATIONS)
        assert all(
            event.operation in PRESELECTION_READ_OPERATIONS
            for event in controller.snapshot().events
        )
        saw_frozen_clean_prefix = True
        try:
            return authorized_local(prepared_run, controller, recorder)
        except RuntimeError as error:
            if "bwrap:" in str(error) or "bubblewrap" in str(error).lower():
                pytest.skip(f"bubblewrap namespace unavailable: {error}")
            raise

    def forbidden_fallback(*_args):
        raise AssertionError("LOCAL decision executed the fallback route")

    result = run_phase3e(
        prepared,
        local_executor=guarded_local,
        fallback_executor=forbidden_fallback,
        registry=registry,
        comparison_profile=profile,
    )
    assert saw_frozen_clean_prefix is True
    assert result.selected_route is RouteSelection.LOCAL
    assert result.decision.comparison is RouteComparison.LOCAL_STRICTLY_DOMINATES
    assert result.upper_compliance == "WITHIN_SELECTED_UPPER"
    assert result.route_execution.completed is True
    assert result.route_execution.requires_next_transaction is False
    assert result.route_execution.semantic_outcome == PostAuditOutcome.CERTIFIED.value

    semantic_execution = result.route_execution.semantic_execution
    assert semantic_execution.local_result.outcome is LocalSolverOutcome.CANDIDATE_FOUND
    assert semantic_execution.post_audit is not None
    assert semantic_execution.post_audit.outcome is PostAuditOutcome.CERTIFIED
    assert tuple(
        row.role for row in result.route_execution.semantic_verification_results
    ) == (SemanticRole.LOCAL_SOLVER_RESULT, SemanticRole.POST_AUDIT)

    native = result.selected_route_work.work_vector
    assert native.value("local.materialization_ground_steps") == 16
    assert native.value("local.materialization_outcome_rows") == 64
    assert native.value("local.postaudit_ground_steps") == 8
    assert native.value("local.postaudit_outcome_rows") == 32
    assert native.value("local.compiler_input_records") == 49
    # The preregistered cardinality reserves seven forms; this concrete
    # capability eliminates one form before the trusted compiler expands it.
    assert native.value("local.compiler_expanded_forms") == 6
    assert native.value("local.compiler_domain_assignments") == 3
    assert native.value("local.solver_subset_evaluations") == 2
    assert native.value("local.solver_policy_assignments") == 257
    assert native.value("local.solver_frontier_points") == 1
    assert native.value("local.solver_dominance_comparisons") == 255
    assert native.value("local.solver_affine_term_evaluations") == 257
    assert native.value("process.launches") == 1
    assert native.value("route.attempts") == 1
    assert native.value("route.successes") == 1
    assert native.value("route.failures") == 0
    assert all(
        native.value(path) == 0
        for path in native.values
        if path.startswith("fallback.") or path.startswith("rebuild.")
    )
    assert result.verification_suffix_work.work_vector.value(
        "common.protocol_checks"
    ) == 6

    selected_upper = dict(result.selected_upper.upper_bounds)
    actual = dict(result.aggregate_marginal_work.aggregate_comparison_vector.values)
    assert set(actual) == set(selected_upper)
    assert all(actual[axis] <= selected_upper[axis] for axis in actual)

    prefreeze = result.access_log.events[
        : result.freeze_attestation.last_preselection_sequence
    ]
    postfreeze = result.access_log.events[
        result.freeze_attestation.last_preselection_sequence :
    ]
    assert all(event.operation in PRESELECTION_READ_OPERATIONS for event in prefreeze)
    assert all(
        event.operation
        not in {
            AccessOperation.KERNEL_STEP,
            AccessOperation.GROUND_OUTCOME_ENUMERATION,
            AccessOperation.LOCAL_WORKER_LAUNCH,
        }
        for event in prefreeze
    )
    operations = tuple(event.operation for event in postfreeze)
    assert operations.count(AccessOperation.LOCAL_WORKER_LAUNCH) == 1
    assert operations.count(AccessOperation.KERNEL_STEP) == 24
    assert operations.count(AccessOperation.GROUND_OUTCOME_ENUMERATION) == 24
    assert operations.count(AccessOperation.LOCAL_POSTAUDIT_ARTIFACT) == 1
    assert all(
        event.sequence_number
        > result.freeze_attestation.last_preselection_sequence
        for event in postfreeze
    )

    def fail_after_staging(*_args, **_kwargs):
        raise RuntimeError("injected isolated local launch failure")

    monkeypatch.setattr(
        local_adapter_module, "_run_fresh_general_solver", fail_after_staging
    )
    with pytest.raises(Phase3ERouteExecutionFailedV1) as caught:
        run_phase3e(
            prepared,
            local_executor=guarded_local,
            fallback_executor=forbidden_fallback,
            registry=registry,
            comparison_profile=profile,
        )
    failed = verify_failed_route_evidence_v1(
        caught.value.evidence,
        registry=registry,
        comparison_profile=profile,
    )
    failed_values = failed.partial_route_work.work_vector.values
    assert failed_values["local.materialization_ground_steps"] == 16
    assert failed_values["local.materialization_outcome_rows"] == 64
    assert failed_values["local.compiler_input_records"] == 49
    assert failed_values["process.launches"] == 1
    assert failed_values["process.exit_failures"] == 1
    assert failed_values["solver.attempts"] == 1
    assert failed_values["solver.failures"] == 1
    assert failed_values["io.staged_bytes"] > 0
    assert failed_values["route.failures"] == 1

    # Terminal admission binds the access trace to the three distinct local
    # runtime artifacts.  The local result transport ID is not the isolated
    # worker-result binding, and a stitch marker without its stitched-plan
    # artifact cannot authorize a plan certificate.
    terminal_binding = AttestationContextV1(
        context,
        point.decision_point_id,
        transaction.transaction_id,
        len(result.access_log.events) + 1,
    )
    aggregate = result.aggregate_marginal_work
    work_result = verify_work_vector_semantics_v1(
        aggregate.aggregate_work_vector,
        binding=terminal_binding,
        verification_work_record=_verification_record(
            SemanticRole.WORK_VECTOR, "terminal"
        ),
        registry=registry,
    )
    actual_result = verify_actual_projection_semantics_v1(
        vector=aggregate.aggregate_work_vector,
        claimed_comparison=aggregate.aggregate_comparison_vector,
        projection_proof=aggregate.aggregate_projection_proof,
        binding=terminal_binding,
        verification_work_record=_verification_record(
            SemanticRole.ACTUAL_PROJECTION, "terminal"
        ),
        registry=registry,
    )
    local_result, post_result = (
        result.route_execution.semantic_verification_results
    )
    terminal_evidence = (
        work_result,
        actual_result,
        local_upper_result,
        decision_result,
        local_result,
        post_result,
    )

    def terminal_for_log(access_log):
        return TerminalArtifactV1(
            "ROUTE_ATTEMPT",
            TerminalClass.PLAN_CERTIFICATE,
            TerminalCode.LOCAL_GROUND_RECOVERY,
            context.route_decision_context_id,
            context.logical_occurrence_id,
            context.route_attempt_id,
            point.decision_point_id,
            transaction.transaction_id,
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
            access_log.access_event_log_id,
        )

    def route_bundle(access_log):
        return TerminalRouteEvidenceBundleV1(
            result.selected_route_work,
            result.verification_suffix_work,
            aggregate,
            access_log,
            result.freeze_attestation,
            ProtocolSequenceProfileV1(),
        )

    terminal = terminal_for_log(result.access_log)
    verified_terminal = verify_terminal_classification_semantics_v1(
        terminal,
        evidence_results=terminal_evidence,
        route_evidence=route_bundle(result.access_log),
        binding=terminal_binding,
        verification_work_record=_verification_record(
            SemanticRole.TERMINAL_CLASSIFICATION, "terminal"
        ),
        registry=registry,
    )
    assert verified_terminal.outcome == TerminalClass.PLAN_CERTIFICATE.value

    local_transport_id = semantic_execution.local_result.local_transaction_result_id
    worker_relabel_events = tuple(
        replace(row, artifact_id=local_transport_id)
        if row.operation is AccessOperation.LOCAL_WORKER_RESULT_ARTIFACT
        else row
        for row in result.access_log.events
    )
    worker_relabel_log = replace(
        result.access_log, events=worker_relabel_events
    )
    with pytest.raises(
        SemanticVerificationV1Error, match="local access trace"
    ):
        verify_terminal_classification_semantics_v1(
            terminal_for_log(worker_relabel_log),
            evidence_results=terminal_evidence,
            route_evidence=route_bundle(worker_relabel_log),
            binding=terminal_binding,
            verification_work_record=_verification_record(
                SemanticRole.TERMINAL_CLASSIFICATION, "worker-relabel"
            ),
            registry=registry,
        )

    wrong_capability_events = tuple(
        replace(row, artifact_id=_id("foreign-capability-binding"))
        if row.operation is AccessOperation.LOCAL_CAPABILITY_ARTIFACT
        else row
        for row in result.access_log.events
    )
    wrong_capability_log = replace(
        result.access_log, events=wrong_capability_events
    )
    with pytest.raises(
        SemanticVerificationV1Error, match="local access trace"
    ):
        verify_terminal_classification_semantics_v1(
            terminal_for_log(wrong_capability_log),
            evidence_results=terminal_evidence,
            route_evidence=route_bundle(wrong_capability_log),
            binding=terminal_binding,
            verification_work_record=_verification_record(
                SemanticRole.TERMINAL_CLASSIFICATION, "capability-relabel"
            ),
            registry=registry,
        )

    without_stitch = tuple(
        row
        for row in result.access_log.events
        if row.operation is not AccessOperation.LOCAL_STITCH_ARTIFACT
    )
    without_stitch = tuple(
        replace(row, sequence_number=index)
        for index, row in enumerate(without_stitch, start=1)
    )
    missing_stitch_log = replace(result.access_log, events=without_stitch)
    with pytest.raises(
        SemanticVerificationV1Error, match="local access trace"
    ):
        verify_terminal_classification_semantics_v1(
            terminal_for_log(missing_stitch_log),
            evidence_results=terminal_evidence,
            route_evidence=route_bundle(missing_stitch_log),
            binding=terminal_binding,
            verification_work_record=_verification_record(
                SemanticRole.TERMINAL_CLASSIFICATION, "missing-stitch"
            ),
            registry=registry,
        )
