from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import builtins
import hashlib

import pytest

from acfqp.access_protocol_v1 import (
    AccessOperation,
    AccessRouteScope,
    PRESELECTION_READ_OPERATIONS,
)
from acfqp.accounting_v1 import (
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import (
    NativeCounterRecorderV1,
    derive_recorded_work_v1,
)
from acfqp.phase3e_dependent_frontier_v1 import (
    DependentFrontierDerivationV1,
    DependentFrontierV1Error,
    DependentPostAuditObligationV1,
    DependentTransactionBenchmarkProfileV1,
    FailedAuditObligationKind,
    derive_dependent_frontier_from_failed_postaudit_v1,
)
from acfqp.phase3e_local_semantics_v1 import (
    FrozenThresholdProfileV1,
    LocalSolverOutcome,
    PostAuditCertificateV1,
    PostAuditOutcome,
    _seal_trusted_execution_v1,
)
from acfqp.phase3e_occurrence_runner_v1 import (
    OccurrenceClosureCodeV1,
    Phase3EOccurrenceRunnerV1Error,
    _observe_local_failure,
    _prepare_second_run,
    run_phase3e_occurrence_v1,
)
from acfqp.phase3e_runner_v1 import (
    Phase3EDecisionAuthorizationV1,
    Phase3EPreselectionReadV1,
    Phase3ERouteExecutionV1,
    PreparedPhase3ERunV1,
    _preselection_reference_id_v1,
)
from acfqp.routing_v1 import (
    CausalEvidenceV1,
    CausalOutcome,
    DecisionPointV1,
    FrontierSnapshotV1,
    MarginalRouteDecisionV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    TransactionV1,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    semantic_verifier_spec_v1,
    verify_local_transaction_result_semantics_v1,
    verify_post_audit_semantics_v1,
)
from tests.test_phase3e_occurrence_runner_v1 import (
    _fallback_package,
    _semantic_authority,
)
from tests.test_phase3e_transactions_v1 import _cardinality, _upper


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:dependent-transaction-benchmark-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _context(
    *,
    selected_plan_id: str,
    registry,
    profile,
) -> RouteDecisionContextV1:
    query_id = _id("query")
    threshold = FrozenThresholdProfileV1(
        query_id, Fraction(1, 20), Fraction(1, 20)
    )
    return RouteDecisionContextV1(
        _id("preregistration"),
        _id("protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        _id("structural"),
        query_id,
        selected_plan_id,
        threshold.threshold_profile_id,
        _id("build-epoch"),
        _id("logical-occurrence"),
        _id("route-attempt"),
    )


def _common_work(context, registry, profile, *, checks: int, label: str):
    recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        recorder_id=f"dependent-{label}-common-v1",
    )
    recorder.add("common.protocol_checks", checks)
    return recorder.seal()


def _local_work(transaction: TransactionV1, registry, *, certified: bool):
    values = {path: 0 for path in registry.required_paths}
    values.update(
        {
            "local.solver_policy_assignments": 1,
            "control.cap_checks": 1,
            "process.launches": 1,
            "route.attempts": 1,
            "route.successes": 1 if certified else 0,
            "route.failures": 0 if certified else 1,
            "solver.attempts": 1,
            "solver.successes": 1,
            "solver.failures": 0,
            "process.exit_successes": 1,
            "process.exit_failures": 0,
        }
    )
    return registry.materialize(
        subject_id=transaction.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        records=explicit_records_v1(
            registry,
            values,
            recorder_id=(
                "dependent-certified-local-v1"
                if certified
                else "dependent-failed-local-v1"
            ),
        ),
    )


def _verification_record(role: SemanticRole, registry, label: str):
    from acfqp.accounting_v1 import CounterRecordV1

    return CounterRecordV1.observe(
        registry,
        semantic_verifier_spec_v1(role).verification_counter_path,
        1,
        recorder_id=f"dependent-{label}-{role.value.lower()}-verifier-v1",
    )


def _trusted_local_execution(
    *,
    context: RouteDecisionContextV1,
    point: DecisionPointV1,
    transaction: TransactionV1,
    cap: RouteCapProfileV1,
    selected_upper_id: str,
    work_vector,
    stitched_plan_id: str,
    certified: bool,
    registry,
    profile,
    label: str,
):
    from acfqp.phase3e_local_semantics_v1 import LocalTransactionResultV1

    threshold = FrozenThresholdProfileV1(
        context.query_id, Fraction(1, 20), Fraction(1, 20)
    )
    local_result = LocalTransactionResultV1(
        context.route_decision_context_id,
        point.decision_point_id,
        transaction.transaction_id,
        context.route_attempt_id,
        context.query_id,
        context.selected_plan_id,
        cap.route_cap_profile_id,
        selected_upper_id,
        work_vector.work_vector_id,
        _id(f"{label}-capability"),
        _id(f"{label}-worker-result"),
        _id(f"{label}-runtime-attestation"),
        _id(f"{label}-overlay"),
        stitched_plan_id,
        LocalSolverOutcome.CANDIDATE_FOUND,
        True,
        None,
    )
    post = PostAuditCertificateV1(
        context.route_decision_context_id,
        point.decision_point_id,
        transaction.transaction_id,
        context.route_attempt_id,
        context.query_id,
        context.selected_plan_id,
        context.threshold_profile_id,
        local_result.local_transaction_result_id,
        work_vector.work_vector_id,
        local_result.candidate_overlay_binding_id,
        stitched_plan_id,
        _id(f"{label}-audit-issue-set"),
        PostAuditOutcome.CERTIFIED if certified else PostAuditOutcome.FAILED,
        Fraction(1) if certified else Fraction(0),
        Fraction(0) if certified else Fraction(1, 10),
        Fraction(0) if certified else Fraction(1, 10),
        0,
        0,
    )
    semantic = _seal_trusted_execution_v1(
        local_result=local_result,
        post_audit=post,
        work_vector=work_vector,
        threshold_profile=threshold,
    )
    binding = AttestationContextV1(
        context,
        point.decision_point_id,
        transaction.transaction_id,
        20,
    )
    local_authority = verify_local_transaction_result_semantics_v1(
        semantic,
        context=context,
        decision_point=point,
        transaction=transaction,
        cap_profile=cap,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.LOCAL_SOLVER_RESULT, registry, label
        ),
        registry=registry,
    )
    post_authority = verify_post_audit_semantics_v1(
        semantic,
        local_solver_result=local_authority,
        context=context,
        decision_point=point,
        transaction=transaction,
        cap_profile=cap,
        binding=binding,
        verification_work_record=_verification_record(
            SemanticRole.POST_AUDIT, registry, label
        ),
        registry=registry,
    )
    recorded = derive_recorded_work_v1(
        work_vector,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
    )
    return Phase3ERouteExecutionV1(
        post.post_audit_certificate_id,
        certified,
        not certified,
        recorded,
        semantic,
        post.outcome.value,
        (local_authority, post_authority),
    )


def _executor(execution: Phase3ERouteExecutionV1):
    def execute(_prepared, controller, _recorder):
        semantic = execution.semantic_execution
        controller.record(
            AccessOperation.LOCAL_SLICE_MATERIALIZATION,
            AccessRouteScope.LOCAL,
        )
        controller.record(
            AccessOperation.LOCAL_CAPABILITY_COMPILATION,
            AccessRouteScope.LOCAL,
        )
        controller.record(
            AccessOperation.LOCAL_CAPABILITY_ARTIFACT,
            AccessRouteScope.LOCAL,
            artifact_id=semantic.local_result.capability_binding_id,
        )
        controller.record(
            AccessOperation.LOCAL_WORKER_LAUNCH,
            AccessRouteScope.LOCAL,
        )
        controller.record(
            AccessOperation.LOCAL_WORKER_RESULT_ARTIFACT,
            AccessRouteScope.LOCAL,
            artifact_id=semantic.local_result.worker_result_binding_id,
        )
        controller.record(
            AccessOperation.LOCAL_PATCH_STITCH,
            AccessRouteScope.LOCAL,
        )
        controller.record(
            AccessOperation.LOCAL_STITCH_ARTIFACT,
            AccessRouteScope.LOCAL,
            artifact_id=semantic.local_result.stitched_plan_binding_id,
        )
        controller.record(
            AccessOperation.LOCAL_POSTAUDIT,
            AccessRouteScope.LOCAL,
        )
        controller.record(
            AccessOperation.LOCAL_POSTAUDIT_ARTIFACT,
            AccessRouteScope.LOCAL,
            artifact_id=execution.artifact_id,
        )
        return execution

    return execute


def _route_authorities(
    *,
    context,
    point,
    transaction,
    causal,
    local_cardinality,
    fallback_cardinality,
    local_upper,
    fallback_upper,
    decision,
    registry,
    label,
):
    # Deliberately test-only: generic synthetic cardinality profiles have no
    # production FQ7 handlers.  These opaque seals let this benchmark exercise
    # the real runner/state-machine boundary; they are not evidence that the
    # remaining production semantic-authority obligation is closed.
    local_binding = AttestationContextV1(
        context, point.decision_point_id, transaction.transaction_id, 10
    )
    fallback_binding = AttestationContextV1(
        context,
        point.decision_point_id,
        TypedNotApplicable("direct fallback has no local transaction"),
        10,
    )
    causal_result = _semantic_authority(
        role=SemanticRole.CAUSAL_SEARCH,
        artifact=causal,
        artifact_id=causal.causal_evidence_id,
        outcome=CausalOutcome.FOUND.value,
        binding=local_binding,
        label=f"{label}-causal",
    )
    local_cardinality_result = _semantic_authority(
        role=SemanticRole.CARDINALITY_EVIDENCE,
        artifact=local_cardinality,
        artifact_id=local_cardinality.cardinality_evidence_id,
        outcome="VALID",
        binding=local_binding,
        label=f"{label}-local-cardinality",
    )
    fallback_cardinality_result = _semantic_authority(
        role=SemanticRole.CARDINALITY_EVIDENCE,
        artifact=fallback_cardinality,
        artifact_id=fallback_cardinality.cardinality_evidence_id,
        outcome="VALID",
        binding=fallback_binding,
        label=f"{label}-fallback-cardinality",
    )
    local_upper_result = _semantic_authority(
        role=SemanticRole.ROUTE_UPPER,
        artifact=local_upper,
        artifact_id=local_upper.route_upper_bound_envelope_id,
        outcome="VALID",
        binding=local_binding,
        label=f"{label}-local-upper",
        dependencies=(
            local_cardinality_result.attestation.verification_attestation_id,
            _id(f"{label}-local-formula-proof"),
        ),
    )
    fallback_upper_result = _semantic_authority(
        role=SemanticRole.ROUTE_UPPER,
        artifact=fallback_upper,
        artifact_id=fallback_upper.route_upper_bound_envelope_id,
        outcome="VALID",
        binding=fallback_binding,
        label=f"{label}-fallback-upper",
        dependencies=(
            fallback_cardinality_result.attestation.verification_attestation_id,
            _id(f"{label}-fallback-formula-proof"),
        ),
    )
    decision_result = _semantic_authority(
        role=SemanticRole.ROUTE_DECISION,
        artifact=decision,
        artifact_id=decision.route_decision_id,
        outcome=RouteSelection.LOCAL.value,
        binding=local_binding,
        label=f"{label}-decision",
        dependencies=(
            causal_result.attestation.verification_attestation_id,
            local_upper_result.attestation.verification_attestation_id,
            fallback_upper_result.attestation.verification_attestation_id,
        ),
    )
    return (
        causal_result,
        local_cardinality_result,
        fallback_cardinality_result,
        local_upper_result,
        fallback_upper_result,
        decision_result,
    )


def _reads(
    *,
    context,
    point,
    upper,
    reusable_rapm_id,
    failed_certificate_id,
    action_catalogue_id,
):
    bound = {
        AccessOperation.READ_FROZEN_RAPM: reusable_rapm_id,
        AccessOperation.READ_FROZEN_BUILD_EPOCH: context.build_epoch_id,
        AccessOperation.READ_FAILED_CERTIFICATE: failed_certificate_id,
        AccessOperation.READ_SELECTED_PLAN: context.selected_plan_id,
        AccessOperation.READ_ACTION_CATALOGUE: action_catalogue_id,
        AccessOperation.READ_FRONTIER_IDENTITIES: (
            _preselection_reference_id_v1(
                AccessOperation.READ_FRONTIER_IDENTITIES,
                point.frontier_snapshot_id,
            )
        ),
        AccessOperation.READ_PROOF_CIRCUIT_METADATA: (
            _preselection_reference_id_v1(
                AccessOperation.READ_PROOF_CIRCUIT_METADATA,
                point.causal_evidence_id,
            )
        ),
        AccessOperation.READ_PREREGISTERED_CARDINALITIES: (
            upper.cardinality_evidence_id
        ),
        AccessOperation.READ_CAP_REGISTRY: upper.route_cap_profile_id,
        AccessOperation.READ_FORMULA_REGISTRY: upper.formula_id,
        AccessOperation.READ_PROFILE_REGISTRY: context.comparison_profile_id,
    }
    return tuple(
        Phase3EPreselectionReadV1(operation, bound[operation])
        for operation in PRESELECTION_READ_OPERATIONS
    )


def _benchmark_world():
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    cap = RouteCapProfileV1()
    reusable_rapm_id = _id("reusable-synthetic-rapm")
    first_failed_certificate_id = _id("first-failed-certificate")
    first_action_catalogue_id = _id("first-action-catalogue")
    first_context = _context(
        selected_plan_id=_id("first-selected-plan"),
        registry=registry,
        profile=comparison,
    )
    first_common = _common_work(
        first_context, registry, comparison, checks=6, label="first"
    )
    first_obligation = _id("first-abstract-proof-obligation")
    first_frontier = FrontierSnapshotV1(
        first_context.route_decision_context_id, 1, (first_obligation,)
    )
    first_causal = CausalEvidenceV1(
        first_frontier.frontier_snapshot_id,
        CausalOutcome.FOUND,
        True,
        None,
        1,
        cap.route_cap_profile_id,
        (first_obligation,),
    )
    first_point = DecisionPointV1(
        first_context.route_decision_context_id,
        1,
        first_frontier.frontier_snapshot_id,
        first_causal.causal_evidence_id,
        first_common.work_vector.work_vector_id,
    )
    first_transaction = TransactionV1(
        first_context.logical_occurrence_id,
        first_context.route_attempt_id,
        first_point.decision_point_id,
        1,
        first_frontier.frontier_snapshot_id,
        cap.route_cap_profile_id,
    )
    first_local_cardinality = _cardinality(
        first_context,
        RouteKind.LOCAL_ATTEMPT,
        cap.route_cap_profile_id,
        first_frontier,
        "dependent-first-local",
    )
    first_fallback_cardinality = _cardinality(
        first_context,
        RouteKind.DIRECT_FALLBACK,
        _id("first-fallback-cap"),
        first_frontier,
        "dependent-first-fallback",
    )
    first_local_upper = _upper(
        context=first_context,
        decision=first_point,
        cardinality=first_local_cardinality,
        route=RouteKind.LOCAL_ATTEMPT,
        bound=1_000,
        transaction=first_transaction,
        causal=first_causal,
        label="dependent-first-local",
    )
    first_fallback_upper = _upper(
        context=first_context,
        decision=first_point,
        cardinality=first_fallback_cardinality,
        route=RouteKind.DIRECT_FALLBACK,
        bound=1_001,
        label="dependent-first-fallback",
    )
    first_decision = MarginalRouteDecisionV1.select(
        first_point,
        first_fallback_upper,
        causal=first_causal,
        local_upper=first_local_upper,
    )
    assert first_decision.selected_route is RouteSelection.LOCAL
    first_work = _local_work(first_transaction, registry, certified=False)
    second_selected_plan_id = _id("first-stitched-plan")
    first_execution = _trusted_local_execution(
        context=first_context,
        point=first_point,
        transaction=first_transaction,
        cap=cap,
        selected_upper_id=first_local_upper.route_upper_bound_envelope_id,
        work_vector=first_work,
        stitched_plan_id=second_selected_plan_id,
        certified=False,
        registry=registry,
        profile=comparison,
        label="first",
    )
    first_authorities = _route_authorities(
        context=first_context,
        point=first_point,
        transaction=first_transaction,
        causal=first_causal,
        local_cardinality=first_local_cardinality,
        fallback_cardinality=first_fallback_cardinality,
        local_upper=first_local_upper,
        fallback_upper=first_fallback_upper,
        decision=first_decision,
        registry=registry,
        label="first",
    )
    first_prepared = PreparedPhase3ERunV1(
        first_context,
        first_point,
        reusable_rapm_id,
        first_failed_certificate_id,
        first_action_catalogue_id,
        _reads(
            context=first_context,
            point=first_point,
            upper=first_local_upper,
            reusable_rapm_id=reusable_rapm_id,
            failed_certificate_id=first_failed_certificate_id,
            action_catalogue_id=first_action_catalogue_id,
        ),
        first_common,
        Phase3EDecisionAuthorizationV1(
            first_authorities[-1],
            first_authorities[3],
            first_authorities,
        ),
    )

    second_context = _context(
        selected_plan_id=second_selected_plan_id,
        registry=registry,
        profile=comparison,
    )
    derived = derive_dependent_frontier_from_failed_postaudit_v1(
        first_context=first_context,
        first_frontier=first_frontier,
        first_causal=first_causal,
        first_transaction=first_transaction,
        post_audit_failure_result=next(
            row
            for row in first_execution.semantic_verification_results
            if row.role is SemanticRole.POST_AUDIT
        ),
        threshold_profile=first_execution.semantic_execution.threshold_profile,
        second_context=second_context,
        cap_profile=cap,
    )
    second_common = _common_work(
        second_context, registry, comparison, checks=7, label="second"
    )
    second_point = DecisionPointV1(
        second_context.route_decision_context_id,
        2,
        derived.frontier.frontier_snapshot_id,
        derived.causal.causal_evidence_id,
        second_common.work_vector.work_vector_id,
    )
    second_transaction = TransactionV1(
        second_context.logical_occurrence_id,
        second_context.route_attempt_id,
        second_point.decision_point_id,
        2,
        derived.frontier.frontier_snapshot_id,
        cap.route_cap_profile_id,
    )
    second_local_cardinality = _cardinality(
        second_context,
        RouteKind.LOCAL_ATTEMPT,
        cap.route_cap_profile_id,
        derived.frontier,
        "dependent-second-local",
    )
    second_fallback_cardinality = _cardinality(
        second_context,
        RouteKind.DIRECT_FALLBACK,
        _id("second-fallback-cap"),
        derived.frontier,
        "dependent-second-fallback",
    )
    second_local_upper = _upper(
        context=second_context,
        decision=second_point,
        cardinality=second_local_cardinality,
        route=RouteKind.LOCAL_ATTEMPT,
        bound=900,
        transaction=second_transaction,
        causal=derived.causal,
        label="dependent-second-local",
    )
    second_fallback_upper = _upper(
        context=second_context,
        decision=second_point,
        cardinality=second_fallback_cardinality,
        route=RouteKind.DIRECT_FALLBACK,
        bound=1_000,
        label="dependent-second-fallback",
    )
    second_decision = MarginalRouteDecisionV1.select(
        second_point,
        second_fallback_upper,
        causal=derived.causal,
        local_upper=second_local_upper,
    )
    assert second_decision.selected_route is RouteSelection.LOCAL
    second_work = _local_work(second_transaction, registry, certified=True)
    second_execution = _trusted_local_execution(
        context=second_context,
        point=second_point,
        transaction=second_transaction,
        cap=cap,
        selected_upper_id=second_local_upper.route_upper_bound_envelope_id,
        work_vector=second_work,
        stitched_plan_id=_id("second-stitched-plan"),
        certified=True,
        registry=registry,
        profile=comparison,
        label="second",
    )
    world = {
        "registry": registry,
        "cap": cap,
        "first_context": first_context,
        "first_frontier": first_frontier,
        "first_causal": first_causal,
        "first_decision_point": first_point,
        "first_transaction": first_transaction,
        "first_local_upper": first_local_upper,
        "first_local_upper_id": first_local_upper.route_upper_bound_envelope_id,
        "first_fallback_upper_id": (
            first_fallback_upper.route_upper_bound_envelope_id
        ),
        "second_context": second_context,
        "second_frontier": derived.frontier,
        "second_causal": derived.causal,
        "second_decision_point": second_point,
        "second_transaction": second_transaction,
        "second_local_cardinality": second_local_cardinality,
        "second_fallback_cardinality": second_fallback_cardinality,
        "second_local_upper": second_local_upper,
        "second_fallback_upper": second_fallback_upper,
        "second_route_decision": second_decision,
        "second_common_prefix_work": second_common,
        "first_execution": first_execution.semantic_execution,
    }
    return {
        "world": world,
        "first_prepared": first_prepared,
        "first_execution": first_execution,
        "first_fallback_upper": first_fallback_upper,
        "second_execution": second_execution,
        "derived": derived,
        "reusable_rapm_id": reusable_rapm_id,
    }


def test_failed_postaudit_deterministically_derives_oracle_free_fresh_stage_two_obligation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    benchmark = _benchmark_world()
    world = benchmark["world"]
    derived = benchmark["derived"]

    # The selector is proof-artifact-only.  Fail immediately if a later edit
    # tries to import a ground domain/J0 while recomputing the frontier.
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith("acfqp.domains") or "j0" in name.lower():
            raise AssertionError(f"ground/J0 oracle accessed by selector: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    post_authority = next(
        row
        for row in benchmark["first_execution"].semantic_verification_results
        if row.role is SemanticRole.POST_AUDIT
    )
    replay = derive_dependent_frontier_from_failed_postaudit_v1(
        first_context=world["first_context"],
        first_frontier=world["first_frontier"],
        first_causal=world["first_causal"],
        first_transaction=world["first_transaction"],
        post_audit_failure_result=post_authority,
        threshold_profile=(
            benchmark["first_execution"].semantic_execution.threshold_profile
        ),
        second_context=world["second_context"],
        cap_profile=world["cap"],
    )
    assert replay == derived
    assert replay.profile.selector_uses_ground_kernel is False
    assert replay.profile.selector_uses_j0 is False
    assert replay.profile.synthetic_fresh_stage_two_obligation is True
    assert replay.profile.proves_deeper_ground_distinction is False
    assert replay.frontier.frontier_stage == 2
    assert replay.frontier.frontier_snapshot_id != (
        world["first_frontier"].frontier_snapshot_id
    )
    assert replay.causal.causal_evidence_id != (
        world["first_causal"].causal_evidence_id
    )
    assert {row.kind for row in replay.obligations} == {
        FailedAuditObligationKind.RISK_EXCEEDS_THRESHOLD,
        FailedAuditObligationKind.REGRET_EXCEEDS_THRESHOLD,
    }
    assert all(
        row.post_audit_certificate_id
        == benchmark["first_execution"].artifact_id
        for row in replay.obligations
    )
    assert all(
        row.post_audit_verification_attestation_id
        == post_authority.attestation.verification_attestation_id
        for row in replay.obligations
    )
    assert replay.derivation.failed_post_audit_verification_attestation_id == (
        post_authority.attestation.verification_attestation_id
    )
    profile = replay.profile
    assert DependentTransactionBenchmarkProfileV1.from_dict(
        profile.to_dict()
    ) == profile
    assert all(
        DependentPostAuditObligationV1.from_dict(row.to_dict()) == row
        for row in replay.obligations
    )
    assert DependentFrontierDerivationV1.from_dict(
        replay.derivation.to_dict()
    ) == replay.derivation


def test_transaction_two_rejects_raw_hash_attestation_and_certified_authority() -> None:
    benchmark = _benchmark_world()
    world = benchmark["world"]
    failed_authority = next(
        row
        for row in benchmark["first_execution"].semantic_verification_results
        if row.role is SemanticRole.POST_AUDIT
    )
    certified_authority = next(
        row
        for row in benchmark["second_execution"].semantic_verification_results
        if row.role is SemanticRole.POST_AUDIT
    )
    kwargs = {
        "first_context": world["first_context"],
        "first_frontier": world["first_frontier"],
        "first_causal": world["first_causal"],
        "first_transaction": world["first_transaction"],
        "threshold_profile": (
            benchmark["first_execution"].semantic_execution.threshold_profile
        ),
        "second_context": world["second_context"],
        "cap_profile": world["cap"],
    }
    for unauthoritative in (
        failed_authority.artifact,
        failed_authority.artifact.to_dict(),
        failed_authority.artifact.post_audit_certificate_id,
        failed_authority.attestation,
    ):
        with pytest.raises(
            DependentFrontierV1Error,
            match="retained POST_AUDIT=FAILED authority",
        ):
            derive_dependent_frontier_from_failed_postaudit_v1(
                post_audit_failure_result=unauthoritative,  # type: ignore[arg-type]
                **kwargs,
            )
    with pytest.raises(
        DependentFrontierV1Error,
        match="POST_AUDIT=FAILED authority|another context",
    ):
        derive_dependent_frontier_from_failed_postaudit_v1(
            post_audit_failure_result=certified_authority,
            **kwargs,
        )


def test_real_occurrence_executes_dependent_transactions_one_and_two() -> None:
    """Exercise real runners/executors, not production synthetic FQ7 handlers."""
    benchmark = _benchmark_world()
    world = benchmark["world"]
    calls = {"first": 0, "second": 0}
    first_delegate = _executor(benchmark["first_execution"])
    second_delegate = _executor(benchmark["second_execution"])

    def first_executor(*args):
        calls["first"] += 1
        return first_delegate(*args)

    def second_executor(*args):
        calls["second"] += 1
        return second_delegate(*args)

    package = _fallback_package(
        world,
        None,
        local_executor=second_executor,
        fallback_executor=lambda *_: (_ for _ in ()).throw(
            AssertionError("dependent transaction 2 selected fallback")
        ),
    )
    package = replace(
        package,
        reusable_rapm_id=benchmark["reusable_rapm_id"],
        failed_certificate_id=_id("second-failed-certificate"),
        action_catalogue_id=_id("second-action-catalogue"),
        preselection_reads=_reads(
            context=world["second_context"],
            point=world["second_decision_point"],
            upper=world["second_local_upper"],
            reusable_rapm_id=benchmark["reusable_rapm_id"],
            failed_certificate_id=_id("second-failed-certificate"),
            action_catalogue_id=_id("second-action-catalogue"),
        ),
    )
    occurrence = run_phase3e_occurrence_v1(
        benchmark["first_prepared"],
        local_executor=first_executor,
        fallback_executor=lambda *_: (_ for _ in ()).throw(
            AssertionError("transaction 1 selected fallback")
        ),
        second_transaction_planner=lambda observation: package,
    )

    assert calls == {"first": 1, "second": 1}
    assert occurrence.closure_code is (
        OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY
    )
    assert tuple(row.transaction_index for row in occurrence.transactions) == (1, 2)
    assert occurrence.transactions == (
        world["first_transaction"],
        world["second_transaction"],
    )
    assert tuple(row.selected_route for row in occurrence.decision_runs) == (
        RouteSelection.LOCAL,
        RouteSelection.LOCAL,
    )
    first_work = occurrence.decision_runs[0].selected_route_work.work_vector
    second_work = occurrence.decision_runs[1].selected_route_work.work_vector
    assert first_work.work_vector_id != second_work.work_vector_id
    local_refs = tuple(
        component.raw_work[0].execution.work_vector.work_vector_id
        for component in occurrence.work_components
        if component.component_kind.value == "LOCAL_TRANSACTION"
    )
    assert local_refs == (first_work.work_vector_id, second_work.work_vector_id)
    aggregate = dict(occurrence.occurrence_work.aggregate_values)
    assert aggregate["process_launches"] == 2
    # Derived route reconciliation leaves remain in the two native vectors;
    # the occurrence ComparisonVector intentionally excludes them.
    assert first_work.value("route.attempts") + second_work.value(
        "route.attempts"
    ) == 2
    assert first_work.value("route.failures") == 1
    assert second_work.value("route.successes") == 1
    assert occurrence.official_execution_allowed is False
    assert occurrence.official_scalar_cost is None
    assert occurrence.official_N_break_even is None


def test_transaction_two_rejects_old_frontier_upper_and_decision_reuse() -> None:
    benchmark = _benchmark_world()
    world = benchmark["world"]
    package = _fallback_package(
        world,
        None,
        local_executor=_executor(benchmark["second_execution"]),
        fallback_executor=lambda *_: None,
    )
    # Produce transaction 1 with the real one-decision runner, then ask the
    # continuation boundary to validate attacked transaction-2 packages.
    from acfqp.phase3e_runner_v1 import run_phase3e

    first_run = run_phase3e(
        benchmark["first_prepared"],
        local_executor=_executor(benchmark["first_execution"]),
        fallback_executor=lambda *_: None,
    )
    observation = _observe_local_failure(
        prepared=benchmark["first_prepared"],
        result=first_run,
        transaction=world["first_transaction"],
        transactions=(world["first_transaction"],),
        local_runs=(first_run,),
    )
    assert observation is not None

    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="frontier|context",
    ):
        _prepare_second_run(
            observation,
            replace(package, second_frontier=world["first_frontier"]),
        )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="upper|context|binding",
    ):
        _prepare_second_run(
            observation,
            replace(
                package,
                second_local_upper=world["first_local_upper"],
            ),
        )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="decision point|context|index",
    ):
        _prepare_second_run(
            observation,
            replace(
                package,
                second_decision_point=world["first_decision_point"],
            ),
        )

    failed = next(
        row
        for row in benchmark["first_execution"].semantic_verification_results
        if row.role is SemanticRole.POST_AUDIT
    )
    with pytest.raises(DependentFrontierV1Error, match="stitched plan"):
        derive_dependent_frontier_from_failed_postaudit_v1(
            first_context=world["first_context"],
            first_frontier=world["first_frontier"],
            first_causal=world["first_causal"],
            first_transaction=world["first_transaction"],
            post_audit_failure_result=failed,
            threshold_profile=(
                benchmark["first_execution"].semantic_execution.threshold_profile
            ),
            second_context=replace(
                world["second_context"],
                selected_plan_id=_id("foreign-second-plan"),
            ),
            cap_profile=world["cap"],
        )
