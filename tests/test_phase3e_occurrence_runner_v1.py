from __future__ import annotations

import hashlib
from fractions import Fraction
from types import SimpleNamespace
from unittest.mock import Mock
from dataclasses import replace

import pytest

from acfqp.core import QuerySpec
import acfqp.phase3e_occurrence_runner_v1 as occurrence_runner
import acfqp.phase3e_local_semantics_v1 as local_semantics
import acfqp.phase3e_runner_v1 as one_decision_runner
from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    RouteDecisionFreezeAttestationV1,
)
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    SHARED_AXES,
    official_comparison_profile_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope, official_actual_projection_profile_v1
from acfqp.marginal_accounting_v1 import derive_marginal_work_aggregate_v1
from acfqp.native_recorder_v1 import (
    NativeCounterRecorderV1,
    derive_recorded_work_v1,
)
from acfqp.phase3e_occurrence_runner_v1 import (
    FreshFallbackAuthorityPackageV1,
    OccurrenceClosureCodeV1,
    Phase3EOccurrenceRunnerV1Error,
    SecondTransactionAuthorityPackageV1,
    run_phase3e_occurrence_v1,
)
from acfqp.phase3e_occurrence_accounting_v1 import (
    OccurrenceRawEvidenceKind,
    RunnerPartialCommonAccountingEvidenceV1,
    derive_runner_partial_common_accounting_v1,
)
from acfqp.phase3e_failure_continuation_v1 import LocalFailureKind
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
    _seal_trusted_ground_fallback_execution_v1,
    build_ground_fallback_cardinality_evidence_v1,
    run_ground_fallback_search_v1,
)
from acfqp.phase3e_runner_v1 import (
    Phase3EDecisionAuthorizationV1,
    Phase3ERouteExecutionV1,
    Phase3ERunResultV1,
    PreparedPhase3ERunV1,
    VERTICAL_SLICE_STATUS,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteKind,
    RouteSelection,
    TerminalCode,
    TransactionV1,
    TypedNotApplicable,
)
from acfqp.route_upper_formula_v1 import (
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    semantic_verifier_spec_v1,
    verify_ground_fallback_semantics_v1,
)
import acfqp.semantic_verification_v1 as semantic_verification
from tests.test_phase3e_runner_two_stage_v1 import _OneStepKernel
from tests.test_phase3e_transactions_v1 import _cardinality, _upper, _world


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:phase3e-occurrence-runner-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def _semantic_authority(
    *,
    role: SemanticRole,
    artifact: object,
    artifact_id: str,
    outcome: str,
    binding: AttestationContextV1,
    label: str,
    dependencies: tuple[str, ...] = (),
):
    registry = binding.route_context.counter_registry_id
    trusted_registry = occurrence_runner.official_counter_registry_v1()
    assert registry == trusted_registry.registry_id
    record = CounterRecordV1.observe(
        trusted_registry,
        semantic_verifier_spec_v1(role).verification_counter_path,
        1,
        recorder_id=f"phase3e-occurrence-{label}-semantic-v1",
    )
    return semantic_verification._finish(
        artifact=artifact,
        artifact_id=artifact_id,
        spec=semantic_verifier_spec_v1(role),
        outcome=outcome,
        binding=binding,
        work=record,
        recomputed_evidence_ids=dependencies,
    )


def _mock_failed_local_run(
    world, *, second: bool = False
) -> Phase3ERunResultV1:
    """Build a genuine typed failed-local runner result for occurrence tests."""

    registry = world["registry"]
    profile = official_comparison_profile_v1(registry)
    context = world["second_context"] if second else world["first_context"]
    transaction = (
        world["second_transaction"] if second else world["first_transaction"]
    )
    point = (
        world["second_decision_point"]
        if second
        else world["first_decision_point"]
    )
    execution_recorder = NativeCounterRecorderV1(
        subject_id=transaction.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-occurrence-runner-local-fake-v1",
    )
    for path, value in world["first_local_work"].values.items():
        if not value:
            continue
        if registry.by_path[path].reducer is ReducerEnum.MAX:
            execution_recorder.observe_peak(path, value)
        else:
            execution_recorder.add(path, value)
    execution_work = execution_recorder.seal()
    old_execution = world["first_execution"]
    local_result = replace(
        old_execution.local_result,
        route_decision_context_id=context.route_decision_context_id,
        decision_point_id=point.decision_point_id,
        transaction_id=transaction.transaction_id,
        route_attempt_id=context.route_attempt_id,
        query_id=context.query_id,
        selected_plan_id=context.selected_plan_id,
        selected_upper_id=(
            world["second_local_upper"].route_upper_bound_envelope_id
            if second
            else world["first_local_upper_id"]
        ),
        work_vector_id=execution_work.work_vector.work_vector_id,
    )
    post_audit = replace(
        old_execution.post_audit,
        route_decision_context_id=context.route_decision_context_id,
        decision_point_id=point.decision_point_id,
        transaction_id=transaction.transaction_id,
        route_attempt_id=context.route_attempt_id,
        query_id=context.query_id,
        selected_plan_id=context.selected_plan_id,
        threshold_profile_id=context.threshold_profile_id,
        local_transaction_result_id=local_result.local_transaction_result_id,
        work_vector_id=execution_work.work_vector.work_vector_id,
    )
    semantic_execution = local_semantics._seal_trusted_execution_v1(
        local_result=local_result,
        post_audit=post_audit,
        work_vector=execution_work.work_vector,
        threshold_profile=old_execution.threshold_profile,
    )
    verification_recorder = NativeCounterRecorderV1(
        subject_id=transaction.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-occurrence-runner-verification-fake-v1",
    )
    verification_recorder.add("common.protocol_checks", 1)
    verification_recorder.add("common.integrity_checks", 1)
    verification_work = verification_recorder.seal()
    actual_profile = official_actual_projection_profile_v1(registry, profile)
    aggregate = derive_marginal_work_aggregate_v1(
        subject_id=transaction.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        execution=(
            execution_work.work_vector,
            execution_work.comparison_vector,
            execution_work.actual_projection_proof,
        ),
        verification_suffix=(
            verification_work.work_vector,
            verification_work.comparison_vector,
            verification_work.actual_projection_proof,
        ),
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual_profile,
    )
    selected_upper = (
        world["second_local_upper"]
        if second
        else world["first_local_upper"]
    )
    decision = (
        world["second_route_decision"]
        if second
        else world["first_route_decision"]
    )
    runner_binding = AttestationContextV1(
        context,
        point.decision_point_id,
        transaction.transaction_id,
        20,
    )
    local_semantic_result = _semantic_authority(
        role=SemanticRole.LOCAL_SOLVER_RESULT,
        artifact=semantic_execution.local_result,
        artifact_id=semantic_execution.local_result.local_transaction_result_id,
        outcome=semantic_execution.local_result.outcome.value,
        binding=runner_binding,
        label=("second-runner-local" if second else "first-runner-local"),
    )
    post_semantic_result = _semantic_authority(
        role=SemanticRole.POST_AUDIT,
        artifact=semantic_execution.post_audit,
        artifact_id=semantic_execution.post_audit.post_audit_certificate_id,
        outcome=semantic_execution.post_audit.outcome.value,
        binding=runner_binding,
        label=("second-runner-postaudit" if second else "first-runner-postaudit"),
    )
    route_execution = Phase3ERouteExecutionV1(
        semantic_execution.post_audit.post_audit_certificate_id,
        False,
        True,
        execution_work,
        semantic_execution=semantic_execution,
        semantic_verification_results=(
            local_semantic_result,
            post_semantic_result,
        ),
        semantic_outcome=semantic_execution.post_audit.outcome.value,
    )
    selected_work_result = _semantic_authority(
        role=SemanticRole.WORK_VECTOR,
        artifact=execution_work.work_vector,
        artifact_id=execution_work.work_vector.work_vector_id,
        outcome="VALID",
        binding=runner_binding,
        label=("second-runner-work" if second else "first-runner-work"),
    )
    common_prefix_work = world.get(
        "second_common_prefix_work"
        if second
        else "first_common_prefix_work",
        world["second_common_prefix_work"],
    )
    profile_id = _id(
        "second-access-profile" if second else "first-access-profile"
    )
    prefreeze = AccessEventLogV1(
        context.route_attempt_id,
        point.decision_point_id,
        profile_id,
        (),
    )
    freeze = RouteDecisionFreezeAttestationV1(
        context.route_attempt_id,
        point.decision_point_id,
        decision.route_decision_id,
        _id("second-decision-attestation" if second else "first-decision-attestation"),
        RouteSelection.LOCAL,
        profile_id,
        prefreeze.access_event_log_id,
        0,
    )
    access_log = AccessEventLogV1(
        context.route_attempt_id,
        point.decision_point_id,
        profile_id,
        (),
        decision.route_decision_id,
        freeze.route_decision_freeze_attestation_id,
        0,
        prefreeze.access_event_log_id,
    )
    return Phase3ERunResultV1(
        VERTICAL_SLICE_STATUS,
        RouteSelection.LOCAL,
        decision,
        selected_upper,
        route_execution,
        common_prefix_work,
        execution_work,
        selected_work_result,
        verification_work,
        aggregate,
        _id("occurrence-reusable-rapm"),
        (),
        "WITHIN_SELECTED_UPPER",
        access_log,
        freeze,
    )


def _fallback_selected_world():
    world = _world()
    registry = world["registry"]
    profile = official_comparison_profile_v1(registry)
    first_prefix_recorder = NativeCounterRecorderV1(
        subject_id=world["first_context"].route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-occurrence-runner-first-prefix-v1",
    )
    first_prefix_recorder.add("common.protocol_checks", 1)
    world["first_common_prefix_work"] = first_prefix_recorder.seal()
    world["first_decision_point"] = DecisionPointV1(
        world["first_context"].route_decision_context_id,
        1,
        world["first_frontier"].frontier_snapshot_id,
        world["first_causal"].causal_evidence_id,
        world["first_common_prefix_work"].work_vector.work_vector_id,
    )
    world["first_transaction"] = TransactionV1(
        world["first_context"].logical_occurrence_id,
        world["first_context"].route_attempt_id,
        world["first_decision_point"].decision_point_id,
        1,
        world["first_frontier"].frontier_snapshot_id,
        world["cap"].route_cap_profile_id,
    )
    first_local_cardinality = _cardinality(
        world["first_context"],
        RouteKind.LOCAL_ATTEMPT,
        world["cap"].route_cap_profile_id,
        world["first_frontier"],
        "occurrence-first-local",
    )
    first_fallback_cardinality = _cardinality(
        world["first_context"],
        RouteKind.DIRECT_FALLBACK,
        _id("occurrence-first-fallback-cap"),
        world["first_frontier"],
        "occurrence-first-fallback",
    )
    world["first_local_upper"] = _upper(
        context=world["first_context"],
        decision=world["first_decision_point"],
        cardinality=first_local_cardinality,
        route=RouteKind.LOCAL_ATTEMPT,
        bound=1_000,
        transaction=world["first_transaction"],
        causal=world["first_causal"],
        label="occurrence-first-local",
    )
    world["first_fallback_upper"] = _upper(
        context=world["first_context"],
        decision=world["first_decision_point"],
        cardinality=first_fallback_cardinality,
        route=RouteKind.DIRECT_FALLBACK,
        bound=1_001,
        label="occurrence-first-fallback",
    )
    world["first_route_decision"] = MarginalRouteDecisionV1.select(
        world["first_decision_point"],
        world["first_fallback_upper"],
        causal=world["first_causal"],
        local_upper=world["first_local_upper"],
    )
    assert world["first_route_decision"].selected_route is RouteSelection.LOCAL
    world["first_local_upper_id"] = (
        world["first_local_upper"].route_upper_bound_envelope_id
    )
    world["first_fallback_upper_id"] = (
        world["first_fallback_upper"].route_upper_bound_envelope_id
    )
    world["second_fallback_cap"] = GroundFallbackCapProfileV1(
        10,
        10,
        10,
        10,
        10,
        10,
        100,
        1,
    )
    world["second_fallback_cardinality"] = replace(
        world["second_fallback_cardinality"],
        route_cap_profile_id=(
            world["second_fallback_cap"].ground_fallback_cap_profile_id
        ),
    )
    world["second_fallback_upper"] = replace(
        world["second_fallback_upper"],
        route_cap_profile_id=(
            world["second_fallback_cap"].ground_fallback_cap_profile_id
        ),
        cardinality_evidence_id=(
            world["second_fallback_cardinality"].cardinality_evidence_id
        ),
        upper_bounds=tuple((axis, 100_000) for axis in SHARED_AXES),
    )
    world["second_local_upper"] = replace(
        world["second_local_upper"],
        upper_bounds=tuple((axis, 100_001) for axis in SHARED_AXES),
    )
    world["second_route_decision"] = MarginalRouteDecisionV1.select(
        world["second_decision_point"],
        world["second_fallback_upper"],
        causal=world["second_causal"],
        local_upper=world["second_local_upper"],
    )
    assert world["second_route_decision"].selected_route is RouteSelection.FALLBACK
    return world


def _local_selected_world():
    world = _fallback_selected_world()
    world["second_local_upper"] = replace(
        world["second_local_upper"],
        upper_bounds=tuple((axis, 99_999) for axis in SHARED_AXES),
    )
    world["second_route_decision"] = MarginalRouteDecisionV1.select(
        world["second_decision_point"],
        world["second_fallback_upper"],
        causal=world["second_causal"],
        local_upper=world["second_local_upper"],
    )
    assert world["second_route_decision"].selected_route is RouteSelection.LOCAL
    return world


def _fallback_package(world, failed_run, *, local_executor, fallback_executor):
    local_binding = AttestationContextV1(
        world["second_context"],
        world["second_decision_point"].decision_point_id,
        world["second_transaction"].transaction_id,
        20,
    )
    fallback_binding = AttestationContextV1(
        world["second_context"],
        world["second_decision_point"].decision_point_id,
        TypedNotApplicable("direct fallback has no local transaction"),
        20,
    )
    causal = _semantic_authority(
        role=SemanticRole.CAUSAL_SEARCH,
        artifact=world["second_causal"],
        artifact_id=world["second_causal"].causal_evidence_id,
        outcome=world["second_causal"].outcome.value,
        binding=local_binding,
        label="second-causal",
    )
    local_cardinality = _semantic_authority(
        role=SemanticRole.CARDINALITY_EVIDENCE,
        artifact=world["second_local_cardinality"],
        artifact_id=world["second_local_cardinality"].cardinality_evidence_id,
        outcome="VALID",
        binding=local_binding,
        label="second-local-cardinality",
    )
    fallback_cardinality = _semantic_authority(
        role=SemanticRole.CARDINALITY_EVIDENCE,
        artifact=world["second_fallback_cardinality"],
        artifact_id=world["second_fallback_cardinality"].cardinality_evidence_id,
        outcome="VALID",
        binding=fallback_binding,
        label="second-fallback-cardinality",
    )
    local_upper = _semantic_authority(
        role=SemanticRole.ROUTE_UPPER,
        artifact=world["second_local_upper"],
        artifact_id=(
            world["second_local_upper"].route_upper_bound_envelope_id
        ),
        outcome="VALID",
        binding=local_binding,
        label="second-local-upper",
        dependencies=(
            local_cardinality.attestation.verification_attestation_id,
            _id("second-local-formula"),
            _id("second-local-derivation"),
        ),
    )
    fallback_upper = _semantic_authority(
        role=SemanticRole.ROUTE_UPPER,
        artifact=world["second_fallback_upper"],
        artifact_id=(
            world["second_fallback_upper"].route_upper_bound_envelope_id
        ),
        outcome="VALID",
        binding=fallback_binding,
        label="second-fallback-upper",
        dependencies=(
            fallback_cardinality.attestation.verification_attestation_id,
            _id("second-fallback-formula"),
            _id("second-fallback-derivation"),
        ),
    )
    route_decision = _semantic_authority(
        role=SemanticRole.ROUTE_DECISION,
        artifact=world["second_route_decision"],
        artifact_id=world["second_route_decision"].route_decision_id,
        outcome=world["second_route_decision"].selected_route.value,
        binding=local_binding,
        label="second-decision",
        dependencies=(
            causal.attestation.verification_attestation_id,
            local_upper.attestation.verification_attestation_id,
            fallback_upper.attestation.verification_attestation_id,
        ),
    )
    return SecondTransactionAuthorityPackageV1(
        world["first_frontier"],
        world["first_causal"],
        world["first_transaction"],
        world["first_fallback_upper_id"],
        world["second_context"],
        world["second_frontier"],
        world["second_causal"],
        world["second_decision_point"],
        world["second_transaction"],
        world["second_local_cardinality"],
        world["second_fallback_cardinality"],
        world["second_local_upper"],
        world["second_fallback_upper"],
        world["second_route_decision"],
        world["second_common_prefix_work"],
        world["cap"],
        causal,
        local_cardinality,
        fallback_cardinality,
        local_upper,
        fallback_upper,
        route_decision,
        world["first_context"].build_epoch_id,
        _id("second-failed-certificate"),
        _id("second-action-catalogue"),
        (),
        local_executor,
        fallback_executor,
    )


def _mock_fallback_run(
    world,
    *,
    outcome: GroundFallbackOutcome = GroundFallbackOutcome.FEASIBLE_CERTIFIED,
) -> Phase3ERunResultV1:
    """Build a genuine typed fallback result, including semantic replay."""

    registry = world["registry"]
    profile = official_comparison_profile_v1(registry)
    context = world["second_context"]
    point = world["second_decision_point"]
    if outcome is GroundFallbackOutcome.CAP_EXHAUSTED:
        cap = GroundFallbackCapProfileV1(10, 10, 10, 10, 10, 10, 1, 1)
        world["second_fallback_cap"] = cap
        world["second_fallback_cardinality"] = replace(
            world["second_fallback_cardinality"],
            route_cap_profile_id=cap.ground_fallback_cap_profile_id,
        )
        world["second_fallback_upper"] = replace(
            world["second_fallback_upper"],
            route_cap_profile_id=cap.ground_fallback_cap_profile_id,
            cardinality_evidence_id=(
                world["second_fallback_cardinality"].cardinality_evidence_id
            ),
        )
        world["second_route_decision"] = MarginalRouteDecisionV1.select(
            point,
            world["second_fallback_upper"],
            causal=world["second_causal"],
            local_upper=world["second_local_upper"],
        )
    else:
        cap = world["second_fallback_cap"]
    kernel = _OneStepKernel()
    query = QuerySpec.from_state(
        kernel.start,
        horizon=1,
        reward_weights=(("reward", Fraction(1)),),
        delta=Fraction(1, 20),
    )
    raw_execution = run_ground_fallback_search_v1(
        kernel,
        query,
        route_decision_context_id=context.route_decision_context_id,
        decision_point_id=point.decision_point_id,
        route_decision_id=world["second_route_decision"].route_decision_id,
        selected_upper_id=(
            world["second_fallback_upper"].route_upper_bound_envelope_id
        ),
        route_attempt_id=context.route_attempt_id,
        query_id=context.query_id,
        cap_profile=cap,
    )
    semantic_execution = _seal_trusted_ground_fallback_execution_v1(
        raw_execution,
        constraint_delta=Fraction(1, 20),
    )
    assert semantic_execution.result.outcome is outcome
    execution_work = derive_recorded_work_v1(
        semantic_execution.work_vector,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
    )
    verification_recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-occurrence-runner-fallback-verification-fake-v1",
    )
    verification_recorder.add("common.protocol_checks", 1)
    verification_recorder.add("common.integrity_checks", 1)
    verification_work = verification_recorder.seal()
    binding = AttestationContextV1(
        context,
        point.decision_point_id,
        world["second_fallback_upper"].transaction_id,
        20,
    )
    fallback_result = verify_ground_fallback_semantics_v1(
        semantic_execution,
        cap_profile=cap,
        binding=binding,
        verification_work_record=CounterRecordV1.observe(
            registry,
            semantic_verifier_spec_v1(
                SemanticRole.GROUND_FALLBACK
            ).verification_counter_path,
            1,
            recorder_id="phase3e-occurrence-ground-fallback-semantic-v1",
        ),
        registry=registry,
    )
    selected_work_result = _semantic_authority(
        role=SemanticRole.WORK_VECTOR,
        artifact=execution_work.work_vector,
        artifact_id=execution_work.work_vector.work_vector_id,
        outcome="VALID",
        binding=binding,
        label="fallback-runner-work",
    )
    actual_profile = official_actual_projection_profile_v1(registry, profile)
    aggregate = derive_marginal_work_aggregate_v1(
        subject_id=world["second_context"].route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        execution=(
            execution_work.work_vector,
            execution_work.comparison_vector,
            execution_work.actual_projection_proof,
        ),
        verification_suffix=(
            verification_work.work_vector,
            verification_work.comparison_vector,
            verification_work.actual_projection_proof,
        ),
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual_profile,
    )
    route_execution = Phase3ERouteExecutionV1(
        semantic_execution.result.ground_fallback_result_id,
        outcome is not GroundFallbackOutcome.CAP_EXHAUSTED,
        False,
        execution_work,
        semantic_execution=semantic_execution,
        semantic_outcome=outcome.value,
        semantic_verification_results=(fallback_result,),
    )
    profile_id = _id("fallback-access-profile")
    prefreeze = AccessEventLogV1(
        context.route_attempt_id,
        point.decision_point_id,
        profile_id,
        (),
    )
    freeze = RouteDecisionFreezeAttestationV1(
        context.route_attempt_id,
        point.decision_point_id,
        world["second_route_decision"].route_decision_id,
        _id("fallback-decision-attestation"),
        RouteSelection.FALLBACK,
        profile_id,
        prefreeze.access_event_log_id,
        0,
    )
    access_log = AccessEventLogV1(
        context.route_attempt_id,
        point.decision_point_id,
        profile_id,
        (),
        world["second_route_decision"].route_decision_id,
        freeze.route_decision_freeze_attestation_id,
        0,
        prefreeze.access_event_log_id,
    )
    return Phase3ERunResultV1(
        VERTICAL_SLICE_STATUS,
        RouteSelection.FALLBACK,
        world["second_route_decision"],
        world["second_fallback_upper"],
        route_execution,
        world["second_common_prefix_work"],
        execution_work,
        selected_work_result,
        verification_work,
        aggregate,
        _id("occurrence-reusable-rapm"),
        (),
        "WITHIN_SELECTED_UPPER",
        access_log,
        freeze,
    )


def test_missing_semantic_authority_stops_before_transaction_two_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete structural tx2 package cannot replace semantic replay."""

    world = _fallback_selected_world()
    failed_run = _mock_failed_local_run(world)
    calls = {"one_decision": 0, "tx2_executor": 0}

    def fake_one_decision(*_args, **_kwargs):
        calls["one_decision"] += 1
        return failed_run

    monkeypatch.setattr(occurrence_runner, "run_phase3e", fake_one_decision)

    prepared = PreparedPhase3ERunV1(
        world["first_context"],
        world["first_decision_point"],
        world["first_context"].build_epoch_id,
        _id("first-failed-certificate"),
        _id("first-action-catalogue"),
        (),
        world["first_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )

    def forbidden_tx2(*_args, **_kwargs):
        calls["tx2_executor"] += 1
        raise AssertionError("tx2 ran without semantic authority")

    def plan(_observation):
        return SecondTransactionAuthorityPackageV1(
            world["first_frontier"],
            world["first_causal"],
            world["first_transaction"],
            world["first_fallback_upper_id"],
            world["second_context"],
            world["second_frontier"],
            world["second_causal"],
            world["second_decision_point"],
            world["second_transaction"],
            world["second_local_cardinality"],
            world["second_fallback_cardinality"],
            world["second_local_upper"],
            world["second_fallback_upper"],
            world["second_route_decision"],
            world["second_common_prefix_work"],
            world["cap"],
            object(),
            object(),
            object(),
            object(),
            object(),
            object(),
            world["first_context"].build_epoch_id,
            _id("second-failed-certificate"),
            _id("second-action-catalogue"),
            (),
            forbidden_tx2,
            forbidden_tx2,
        )

    result = run_phase3e_occurrence_v1(
        prepared,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
        second_transaction_planner=plan,
    )
    assert result.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE
    assert result.control_failure_evidence is not None
    assert result.occurrence_terminal is not None
    assert result.occurrence_terminal.noncertificate_count == 1
    assert result.occurrence_terminal_result.binding.verification_lane.value == "evaluation"
    assert calls == {"one_decision": 1, "tx2_executor": 0}


def test_untyped_transaction_two_package_is_rejected_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _fallback_selected_world()
    failed_run = _mock_failed_local_run(world)
    monkeypatch.setattr(
        occurrence_runner, "run_phase3e", lambda *_args, **_kwargs: failed_run
    )
    prepared = PreparedPhase3ERunV1(
        world["first_context"],
        world["first_decision_point"],
        world["first_context"].build_epoch_id,
        _id("first-failed-certificate"),
        _id("first-action-catalogue"),
        (),
        world["first_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )
    result = run_phase3e_occurrence_v1(
        prepared,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
        second_transaction_planner=lambda _observation: object(),
    )
    assert result.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE
    assert result.control_failure_evidence.failure_stage == (
        "UNTYPED_SECOND_TRANSACTION_PACKAGE"
    )


def test_rejected_transaction_package_preserves_observed_verifier_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rejected semantic package cannot erase verifier work already done."""

    world = _fallback_selected_world()
    failed_run = _mock_failed_local_run(world)
    package = _fallback_package(
        world,
        failed_run,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
    )
    wrong_causal = replace(
        world["second_causal"],
        evaluated_candidate_count=(
            world["second_causal"].evaluated_candidate_count + 1
        ),
    )
    wrong_causal_result = _semantic_authority(
        role=SemanticRole.CAUSAL_SEARCH,
        artifact=wrong_causal,
        artifact_id=wrong_causal.causal_evidence_id,
        outcome=wrong_causal.outcome.value,
        binding=AttestationContextV1(
            world["second_context"],
            world["second_decision_point"].decision_point_id,
            world["second_transaction"].transaction_id,
            20,
        ),
        label="wrong-second-causal",
    )
    package = replace(package, causal_result=wrong_causal_result)
    monkeypatch.setattr(
        occurrence_runner,
        "run_phase3e",
        lambda *_args, **_kwargs: failed_run,
    )
    prepared = PreparedPhase3ERunV1(
        world["first_context"],
        world["first_decision_point"],
        world["first_context"].build_epoch_id,
        _id("first-failed-certificate"),
        _id("first-action-catalogue"),
        (),
        world["first_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )

    result = run_phase3e_occurrence_v1(
        prepared,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
        second_transaction_planner=lambda _observation: package,
    )
    assert result.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE
    assert result.control_failure_evidence.failure_stage == (
        "SECOND_TRANSACTION_AUTHORITY_REJECTED"
    )
    assert result.occurrence_terminal.noncertificate_count == 1
    partial = result.work_components[-1].raw_work[0]
    assert type(partial) is RunnerPartialCommonAccountingEvidenceV1
    assert partial.aggregate_work != partial.core
    assert len(partial.semantic_results) == 6
    assert result.occurrence_work.component_refs[-1].raw_work_refs[0].evidence_kind is (
        OccurrenceRawEvidenceKind.PARTIAL_ACCOUNTED_COMMON
    )

    # The rejected package prefix is admissible only while it remains the
    # final, unpaired component.  Appending marginal work cannot turn that
    # partial verifier charge into a completed decision.
    attacked_components = (
        *result.work_components,
        result.work_components[1],
    )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="PARTIAL_ACCOUNTED_COMMON.*final unpaired",
    ):
        replace(result, work_components=attacked_components)
    with pytest.raises(
        semantic_verification.SemanticVerificationV1Error,
        match="PARTIAL_ACCOUNTED_COMMON.*final unpaired",
    ):
        semantic_verification.verify_occurrence_terminal_semantics_v1(
            result.occurrence_terminal,
            occurrence_work=result.occurrence_work,
            components=attacked_components,
            decision_runs=result.decision_runs,
            detail_evidence=result.control_failure_evidence,
            binding=result.occurrence_terminal_result.binding,
            verification_work_record=_occurrence_terminal_replay_record(world),
            registry=world["registry"],
        )

    wrong_detail = replace(
        result.control_failure_evidence,
        failure_stage="MISSING_SECOND_TRANSACTION_PLANNER",
    )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="PARTIAL_ACCOUNTED_COMMON.*authority-rejected",
    ):
        replace(result, control_failure_evidence=wrong_detail)
    with pytest.raises(
        semantic_verification.SemanticVerificationV1Error,
        match="PARTIAL_ACCOUNTED_COMMON requires an authority-rejected",
    ):
        semantic_verification.verify_occurrence_terminal_semantics_v1(
            result.occurrence_terminal,
            occurrence_work=result.occurrence_work,
            components=result.work_components,
            decision_runs=result.decision_runs,
            detail_evidence=wrong_detail,
            binding=result.occurrence_terminal_result.binding,
            verification_work_record=_occurrence_terminal_replay_record(world),
            registry=world["registry"],
        )


def test_forged_sealed_metadata_is_rejected_at_occurrence_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _fallback_selected_world()
    failed_run = _mock_failed_local_run(world)
    object.__setattr__(failed_run, "sealed_executor_profile", True)
    object.__setattr__(failed_run, "runtime_tree_id", _id("sealed-runtime-tree"))
    object.__setattr__(
        failed_run, "executor_recipe_id", _id("sealed-executor-recipe")
    )
    package = _fallback_package(
        world,
        failed_run,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
    )
    monkeypatch.setattr(
        occurrence_runner,
        "run_phase3e",
        lambda *_args, **_kwargs: failed_run,
    )
    prepared = PreparedPhase3ERunV1(
        world["first_context"],
        world["first_decision_point"],
        world["first_context"].build_epoch_id,
        _id("first-failed-certificate"),
        _id("first-action-catalogue"),
        (),
        world["first_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )

    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="invalid typed result",
    ):
        run_phase3e_occurrence_v1(
            prepared,
            local_executor=lambda *_: None,
            fallback_executor=lambda *_: None,
            second_transaction_planner=lambda _observation: package,
        )


def test_second_decision_fallback_executes_without_fabricating_transaction_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _fallback_selected_world()
    failed_run = _mock_failed_local_run(world)
    fallback_run = _mock_fallback_run(world)
    calls = {"run": 0, "local": 0, "fallback": 0, "fresh": 0}

    def local_executor(*_args, **_kwargs):
        calls["local"] += 1
        raise AssertionError("fallback-selected second decision ran LOCAL")

    def fallback_executor(*_args, **_kwargs):
        calls["fallback"] += 1

    package = _fallback_package(
        world,
        failed_run,
        local_executor=local_executor,
        fallback_executor=fallback_executor,
    )

    def fake_one_decision(prepared, *, local_executor, fallback_executor, **_kwargs):
        calls["run"] += 1
        if calls["run"] == 1:
            return failed_run
        assert calls["run"] == 2
        decision, selected_upper = prepared.authorization.validate(
            context=prepared.context,
            decision_point=prepared.decision_point,
        )
        assert decision.selected_route is RouteSelection.FALLBACK
        assert selected_upper == world["second_fallback_upper"]
        assert local_executor is occurrence_runner._forbidden_local_executor
        assert fallback_executor is package.fallback_executor
        fallback_executor(prepared, None, None)
        return fallback_run

    monkeypatch.setattr(occurrence_runner, "run_phase3e", fake_one_decision)
    prepared = PreparedPhase3ERunV1(
        world["first_context"],
        world["first_decision_point"],
        world["first_context"].build_epoch_id,
        _id("first-failed-certificate"),
        _id("first-action-catalogue"),
        (),
        world["first_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )

    def forbidden_fresh(_observation):
        calls["fresh"] += 1
        raise AssertionError("an already selected fallback was estimated again")

    result = run_phase3e_occurrence_v1(
        prepared,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
        second_transaction_planner=lambda _observation: package,
        fresh_fallback_planner=forbidden_fresh,
    )

    assert result.closure_code is OccurrenceClosureCodeV1.FULL_GROUND_FALLBACK
    assert result.transactions == (world["first_transaction"],)
    assert len(result.decision_runs) == 2
    assert result.work_components[2].component_kind.value == "COMMON_PREFIX"
    assert result.work_components[3].component_kind.value == "DIRECT_FALLBACK"
    assert calls == {"run": 2, "local": 0, "fallback": 1, "fresh": 0}


def test_second_decision_fallback_rejects_a_local_result_splice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _fallback_selected_world()
    failed_run = _mock_failed_local_run(world)
    package = _fallback_package(
        world,
        failed_run,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
    )
    spliced_local = Mock(spec=Phase3ERunResultV1)
    spliced_local.selected_route = RouteSelection.LOCAL
    spliced_local.selected_upper = world["second_local_upper"]
    spliced_local.common_prefix_work = world["second_common_prefix_work"]
    spliced_local.selected_route_work = failed_run.selected_route_work
    spliced_local.verification_suffix_work = failed_run.verification_suffix_work
    spliced_local.aggregate_marginal_work = failed_run.aggregate_marginal_work
    responses = iter((failed_run, spliced_local))
    monkeypatch.setattr(
        occurrence_runner,
        "run_phase3e",
        lambda *_args, **_kwargs: next(responses),
    )
    prepared = PreparedPhase3ERunV1(
        world["first_context"],
        world["first_decision_point"],
        world["first_context"].build_epoch_id,
        _id("first-failed-certificate"),
        _id("first-action-catalogue"),
        (),
        world["second_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )

    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="one-decision runner returned an untyped result",
    ):
        run_phase3e_occurrence_v1(
            prepared,
            local_executor=lambda *_: None,
            fallback_executor=lambda *_: None,
            second_transaction_planner=lambda _observation: package,
        )


def test_transaction_two_executor_failure_closes_one_noncertificate_occurrence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _local_selected_world()
    first_run = _mock_failed_local_run(world)

    def crash_transaction_two(*_args, **_kwargs):
        raise RuntimeError("injected transaction-two executor failure")

    package = _fallback_package(
        world,
        first_run,
        local_executor=crash_transaction_two,
        fallback_executor=lambda *_: (_ for _ in ()).throw(
            AssertionError("transaction two selected fallback")
        ),
    )
    real_run = one_decision_runner.run_phase3e
    original_validate = PreparedPhase3ERunV1.validate

    def validate(prepared, registry, profile):
        # The transaction authority chain is exercised by
        # ``_prepare_second_run``.  This focused orchestration test then lets
        # the real one-decision runner consume that exact decision/upper while
        # avoiding a second copy of the preselection-binding fixture.
        if prepared.context == world["second_context"]:
            return world["second_route_decision"], world["second_local_upper"]
        return original_validate(prepared, registry, profile)

    monkeypatch.setattr(PreparedPhase3ERunV1, "validate", validate)
    calls = 0

    def one_decision(prepared, *, local_executor, fallback_executor, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return first_run
        return real_run(
            prepared,
            local_executor=local_executor,
            fallback_executor=fallback_executor,
            **kwargs,
        )

    monkeypatch.setattr(occurrence_runner, "run_phase3e", one_decision)
    prepared = PreparedPhase3ERunV1(
        world["first_context"],
        world["first_decision_point"],
        world["first_context"].build_epoch_id,
        _id("first-failed-certificate"),
        _id("first-action-catalogue"),
        (),
        world["first_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )
    result = run_phase3e_occurrence_v1(
        prepared,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
        second_transaction_planner=lambda _observation: package,
    )

    assert result.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE
    assert result.decision_runs == (first_run,)
    assert result.transactions == (
        world["first_transaction"],
        world["second_transaction"],
    )
    assert len(result.work_components) == 4
    assert result.occurrence_failure_terminal is not None
    assert result.occurrence_failure_terminal.failed_decision_ordinal == 2
    assert result.occurrence_failure_terminal.transaction_count == 2
    assert result.occurrence_failure_terminal.noncertificate_count == 1
    assert result.infeasibility_certified is False

    forged_failure = replace(
        result.failed_route_evidence,
        original_error_message="forged transaction-two failure detail",
    )
    forged_failure_authority = replace(
        result.occurrence_failure_terminal_authority,
        failed_route_evidence=forged_failure,
    )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="differs from full evidence replay",
    ):
        replace(
            result,
            failed_route_evidence=forged_failure,
            occurrence_failure_terminal_authority=forged_failure_authority,
        )

    partial = derive_runner_partial_common_accounting_v1(
        core=package.second_common_prefix_work,
        semantic_results=(
            package.causal_result,
            package.local_cardinality_result,
            package.fallback_cardinality_result,
            package.local_upper_result,
            package.fallback_upper_result,
            package.route_decision_result,
        ),
        nonsemantic_records=package.common_nonsemantic_records,
        route_context=package.second_context,
        decision_point_id=package.second_decision_point.decision_point_id,
        registry=world["registry"],
        comparison_profile=official_comparison_profile_v1(world["registry"]),
        actual_profile=official_actual_projection_profile_v1(
            world["registry"],
            official_comparison_profile_v1(world["registry"]),
        ),
    )
    attacked_components = (
        *result.work_components[:-2],
        replace(result.work_components[-2], raw_work=(partial,)),
        result.work_components[-1],
    )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="failed-route terminal cannot pair PARTIAL_ACCOUNTED_COMMON",
    ):
        occurrence_runner.verify_phase3e_occurrence_failure_terminal_v1(
            result.occurrence_failure_terminal,
            failure_evidence=result.failed_route_evidence,
            successful_runs=result.decision_runs,
            transactions=result.transactions,
            components=attacked_components,
            registry=world["registry"],
            comparison_profile=official_comparison_profile_v1(
                world["registry"]
            ),
            actual_profile=official_actual_projection_profile_v1(
                world["registry"],
                official_comparison_profile_v1(world["registry"]),
            ),
        )


def test_fresh_fallback_executor_failure_retains_both_local_transactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A third-decision crash closes, rather than erases, one occurrence."""

    world = _local_selected_world()
    first_run = _mock_failed_local_run(world)
    second_run = _mock_failed_local_run(world, second=True)
    second_package = _fallback_package(
        world,
        first_run,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
    )
    registry = world["registry"]
    profile = official_comparison_profile_v1(registry)
    context = world["second_context"]

    prefix_recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-occurrence-fresh-fallback-prefix-v1",
    )
    prefix_recorder.add("common.protocol_checks", 1)
    fallback_prefix = prefix_recorder.seal()
    fallback_point = DecisionPointV1(
        context.route_decision_context_id,
        TypedNotApplicable("two local transactions are already closed"),
        TypedNotApplicable("fresh direct fallback has no local frontier"),
        TypedNotApplicable("local is forbidden after transaction two"),
        fallback_prefix.work_vector.work_vector_id,
    )
    fallback_cap = GroundFallbackCapProfileV1(
        100,
        100,
        100,
        400,
        100,
        100,
        1_000,
        4,
    )
    fallback_bound = GroundFallbackCardinalityBoundV1(
        context.route_decision_context_id,
        fallback_point.decision_point_id,
            fallback_cap.ground_fallback_cap_profile_id,
            (
                ("common.protocol_checks", 5),
            ("fallback.actions_evaluated", 2),
            ("fallback.bellman_backups", 4),
            ("fallback.composed_candidates", 4),
            ("fallback.ground_steps", 2),
            ("fallback.outcome_rows", 4),
            ("fallback.states_expanded", 2),
            ("control.cap_checks", 10),
        ),
        (_id("fresh-fallback-cardinality-parent"),),
    )
    fallback_cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=fallback_point,
        cap_profile=fallback_cap,
        bound=fallback_bound,
    )
    fallback_formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=fallback_cap,
    )
    fallback_upper, _ = derive_route_upper_v1(
        context=context,
        decision_point=fallback_point,
        cardinality=fallback_cardinality,
        cap_profile=fallback_cap,
        registry=registry,
        profile=profile,
        formula=fallback_formula,
    )
    fallback_decision = MarginalRouteDecisionV1.select(
        fallback_point,
        fallback_upper,
        causal=None,
        local_upper=None,
    )
    assert fallback_decision.selected_route is RouteSelection.FALLBACK
    fallback_binding = AttestationContextV1(
        context,
        fallback_point.decision_point_id,
        TypedNotApplicable("fresh direct fallback has no local transaction"),
        20,
    )
    fallback_decision_result = _semantic_authority(
        role=SemanticRole.ROUTE_DECISION,
        artifact=fallback_decision,
        artifact_id=fallback_decision.route_decision_id,
        outcome=RouteSelection.FALLBACK.value,
        binding=fallback_binding,
        label="fresh-fallback-decision",
    )
    fallback_prepared = PreparedPhase3ERunV1(
        context,
        fallback_point,
        context.build_epoch_id,
        _id("fresh-fallback-failed-certificate"),
        _id("fresh-fallback-action-catalogue"),
        (),
        fallback_prefix,
        Phase3EDecisionAuthorizationV1(
            fallback_decision_result,
            object(),
            (),
        ),
    )

    def crash_fallback(*_args, **_kwargs):
        raise RuntimeError("injected fresh-fallback executor failure")

    fallback_package = FreshFallbackAuthorityPackageV1(
        context,
        LocalFailureKind.POST_AUDIT_FAILED,
        world["cap"],
        (
            world["first_local_upper_id"],
            world["second_local_upper"].route_upper_bound_envelope_id,
        ),
        (_id("prior-fallback-cardinality-bound"),),
        fallback_prefix,
        fallback_point,
        fallback_cap,
        fallback_bound,
        fallback_cardinality,
        fallback_upper,
        fallback_decision,
        object(),
        object(),
        object(),
        fallback_decision_result,
        context.build_epoch_id,
        _id("fresh-fallback-failed-certificate"),
        _id("fresh-fallback-action-catalogue"),
        (),
        crash_fallback,
    )

    real_run = one_decision_runner.run_phase3e
    original_validate = PreparedPhase3ERunV1.validate

    def validate(prepared, accounting_registry, accounting_profile):
        if prepared is fallback_prepared:
            return fallback_decision, fallback_upper
        return original_validate(
            prepared, accounting_registry, accounting_profile
        )

    monkeypatch.setattr(PreparedPhase3ERunV1, "validate", validate)
    calls = 0

    def one_decision(prepared, *, local_executor, fallback_executor, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return first_run
        if calls == 2:
            return second_run
        return real_run(
            prepared,
            local_executor=local_executor,
            fallback_executor=fallback_executor,
            **kwargs,
        )

    monkeypatch.setattr(occurrence_runner, "run_phase3e", one_decision)

    def prepare_fallback(observation, package):
        assert package is fallback_package
        assert observation.completed_transactions == (
            world["first_transaction"],
            world["second_transaction"],
        )
        assert observation.completed_local_runs == (first_run, second_run)
        return fallback_prepared, object(), object()

    monkeypatch.setattr(
        occurrence_runner, "_prepare_fallback_run", prepare_fallback
    )
    initial_prepared = PreparedPhase3ERunV1(
        world["first_context"],
        world["first_decision_point"],
        world["first_context"].build_epoch_id,
        _id("first-failed-certificate"),
        _id("first-action-catalogue"),
        (),
        world["first_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )
    result = run_phase3e_occurrence_v1(
        initial_prepared,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
        second_transaction_planner=lambda _observation: second_package,
        fresh_fallback_planner=lambda _observation: fallback_package,
    )

    assert calls == 3
    assert result.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE
    assert result.decision_runs == (first_run, second_run)
    assert result.transactions == (
        world["first_transaction"],
        world["second_transaction"],
    )
    assert len(result.work_components) == 6
    terminal = result.occurrence_failure_terminal
    assert terminal is not None
    assert terminal.logical_occurrence_id == context.logical_occurrence_id
    assert terminal.failed_decision_ordinal == 3
    assert terminal.successful_decision_run_count == 2
    assert terminal.transaction_count == 2
    assert terminal.plan_certificate_count == 0
    assert terminal.infeasibility_certificate_count == 0
    assert terminal.noncertificate_count == 1
    assert result.infeasibility_certified is False


def _run_missing_second_planner(monkeypatch: pytest.MonkeyPatch):
    world = _fallback_selected_world()
    failed_run = _mock_failed_local_run(world)
    monkeypatch.setattr(
        occurrence_runner,
        "run_phase3e",
        lambda *_args, **_kwargs: failed_run,
    )
    prepared = PreparedPhase3ERunV1(
        world["first_context"],
        world["first_decision_point"],
        world["first_context"].build_epoch_id,
        _id("missing-planner-failed-certificate"),
        _id("missing-planner-action-catalogue"),
        (),
        world["first_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )
    result = run_phase3e_occurrence_v1(
        prepared,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
    )
    return world, result


def _occurrence_terminal_replay_record(world, *, lane: LaneEnum = LaneEnum.EVALUATION):
    spec = semantic_verifier_spec_v1(SemanticRole.OCCURRENCE_TERMINAL)
    return CounterRecordV1.observe(
        world["registry"],
        spec.counter_path_for_lane(lane),
        1,
        recorder_id=f"phase3e-occurrence-terminal-{lane.value}-attack-v1",
    )


def test_missing_second_planner_closes_and_counts_one_noncertificate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _world_state, result = _run_missing_second_planner(monkeypatch)

    assert result.closure_code is OccurrenceClosureCodeV1.PROTOCOL_FAILURE
    assert result.control_failure_evidence.failure_stage == (
        "MISSING_SECOND_TRANSACTION_PLANNER"
    )
    assert result.occurrence_terminal.terminal_code is TerminalCode.PROTOCOL_FAILURE
    assert result.occurrence_terminal.plan_certificate_count == 0
    assert result.occurrence_terminal.infeasibility_certificate_count == 0
    assert result.occurrence_terminal.noncertificate_count == 1
    assert result.infeasibility_certified is False


def test_fallback_cap_exhaustion_is_one_noncertificate_not_infeasibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _fallback_selected_world()
    failed_run = _mock_failed_local_run(world)
    cap_run = _mock_fallback_run(
        world,
        outcome=GroundFallbackOutcome.CAP_EXHAUSTED,
    )
    package = _fallback_package(
        world,
        failed_run,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
    )
    responses = iter((failed_run, cap_run))
    monkeypatch.setattr(
        occurrence_runner,
        "run_phase3e",
        lambda *_args, **_kwargs: next(responses),
    )
    prepared = PreparedPhase3ERunV1(
        world["first_context"],
        world["first_decision_point"],
        world["first_context"].build_epoch_id,
        _id("cap-failed-certificate"),
        _id("cap-action-catalogue"),
        (),
        world["first_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )
    result = run_phase3e_occurrence_v1(
        prepared,
        local_executor=lambda *_: None,
        fallback_executor=lambda *_: None,
        second_transaction_planner=lambda _observation: package,
    )

    assert result.closure_code is OccurrenceClosureCodeV1.FALLBACK_CAP_EXHAUSTED
    assert result.occurrence_terminal.terminal_code is (
        TerminalCode.FALLBACK_CAP_EXHAUSTED
    )
    assert result.occurrence_terminal.noncertificate_count == 1
    assert result.occurrence_terminal.infeasibility_certificate_count == 0
    assert result.infeasibility_certified is False

    swapped = replace(
        result.occurrence_terminal,
        terminal_code=TerminalCode.PROTOCOL_FAILURE,
    )
    with pytest.raises(
        semantic_verification.SemanticVerificationV1Error,
        match="identity chains differ",
    ):
        semantic_verification.verify_occurrence_terminal_semantics_v1(
            swapped,
            occurrence_work=result.occurrence_work,
            components=result.work_components,
            decision_runs=result.decision_runs,
            detail_evidence=cap_run.route_execution.semantic_execution,
            binding=result.occurrence_terminal_result.binding,
            verification_work_record=_occurrence_terminal_replay_record(world),
            registry=world["registry"],
        )


def test_occurrence_terminal_replay_rejects_code_count_lane_and_type_splices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world, result = _run_missing_second_planner(monkeypatch)
    terminal = result.occurrence_terminal
    binding = result.occurrence_terminal_result.binding
    kwargs = {
        "occurrence_work": result.occurrence_work,
        "components": result.work_components,
        "decision_runs": result.decision_runs,
        "detail_evidence": result.control_failure_evidence,
        "binding": binding,
        "verification_work_record": _occurrence_terminal_replay_record(world),
        "registry": world["registry"],
    }

    with pytest.raises(
        semantic_verification.SemanticVerificationV1Error,
        match="identity chains differ",
    ):
        semantic_verification.verify_occurrence_terminal_semantics_v1(
            replace(
                terminal,
                terminal_code=TerminalCode.FALLBACK_CAP_EXHAUSTED,
            ),
            **kwargs,
        )
    with pytest.raises(
        semantic_verification.SemanticVerificationV1Error,
        match="identity chains differ",
    ):
        semantic_verification.verify_occurrence_terminal_semantics_v1(
            replace(terminal, transaction_count=0),
            **kwargs,
        )
    with pytest.raises(
        semantic_verification.SemanticVerificationV1Error,
        match="decision-run evidence",
    ):
        semantic_verification.verify_occurrence_terminal_semantics_v1(
            terminal,
            **{
                **kwargs,
                "decision_runs": (Mock(spec=Phase3ERunResultV1),),
            },
        )
    with pytest.raises(
        semantic_verification.SemanticVerificationV1Error,
        match="extra preparation is untyped",
    ):
        semantic_verification.verify_occurrence_terminal_semantics_v1(
            terminal,
            **kwargs,
            extra_prepared=Mock(spec=PreparedPhase3ERunV1),
        )
    operational_binding = replace(
        binding,
        verification_lane=LaneEnum.OPERATIONAL,
    )
    with pytest.raises(
        semantic_verification.SemanticVerificationV1Error,
        match="evaluation lane",
    ):
        semantic_verification.verify_occurrence_terminal_semantics_v1(
            terminal,
            **{
                **kwargs,
                "binding": operational_binding,
                "verification_work_record": _occurrence_terminal_replay_record(
                    world,
                    lane=LaneEnum.OPERATIONAL,
                ),
            },
        )
    first_axis, first_value = result.occurrence_work.aggregate_values[0]
    foreign_aggregate = replace(
        result.occurrence_work,
        aggregate_values=(
            (first_axis, first_value + 1),
            *result.occurrence_work.aggregate_values[1:],
        ),
    )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="work history does not replay",
    ):
        replace(result, occurrence_work=foreign_aggregate)


def test_occurrence_result_boundary_replays_order_runs_transactions_and_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime replacement cannot preserve stale authority over new history."""

    _world_state, result = _run_missing_second_planner(monkeypatch)

    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="work history does not replay",
    ):
        replace(
            result,
            work_components=tuple(reversed(result.work_components)),
        )

    first_component = result.work_components[0]
    spliced_context = replace(
        first_component.route_context,
        selected_plan_id=_id("spliced-occurrence-selected-plan"),
    )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="work history does not replay",
    ):
        replace(
            result,
            work_components=(
                replace(first_component, route_context=spliced_context),
                *result.work_components[1:],
            ),
        )

    spliced_run = _mock_failed_local_run(_world_state, second=True)
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="splices or reorders a completed run",
    ):
        replace(result, decision_runs=(spliced_run,))

    first_ref, second_ref = result.occurrence_work.component_refs
    rehashed_aggregate = replace(
        result.occurrence_work,
        component_refs=(
            replace(second_ref, sequence_index=1),
            replace(first_ref, sequence_index=2),
        ),
    )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="work history does not replay",
    ):
        replace(result, occurrence_work=rehashed_aggregate)

    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="transaction history differs",
    ):
        replace(result, transactions=())

    forged_terminal = replace(
        result.occurrence_terminal,
        detail_id=_id("forged-occurrence-terminal-detail"),
    )
    forged_terminal_result = replace(
        result.occurrence_terminal_result,
        artifact=forged_terminal,
    )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="terminal authority is stale",
    ):
        replace(
            result,
            occurrence_terminal=forged_terminal,
            occurrence_terminal_result=forged_terminal_result,
        )

    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="local-recovery closure differs",
    ):
        replace(
            result,
            closure_code=OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY,
            occurrence_terminal=None,
            occurrence_terminal_result=None,
            control_failure_evidence=None,
        )
