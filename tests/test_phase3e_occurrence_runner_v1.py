from __future__ import annotations

import hashlib
from types import SimpleNamespace
from unittest.mock import Mock
from dataclasses import replace

import pytest

import acfqp.phase3e_occurrence_runner_v1 as occurrence_runner
import acfqp.phase3e_local_semantics_v1 as local_semantics
from acfqp.accounting_v1 import (
    CounterRecordV1,
    ReducerEnum,
    RouteKindEnum,
    SHARED_AXES,
    official_comparison_profile_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope, official_actual_projection_profile_v1
from acfqp.marginal_accounting_v1 import derive_marginal_work_aggregate_v1
from acfqp.native_recorder_v1 import NativeCounterRecorderV1
from acfqp.phase3e_occurrence_runner_v1 import (
    OccurrenceClosureCodeV1,
    Phase3EOccurrenceRunnerV1Error,
    SecondTransactionAuthorityPackageV1,
    run_phase3e_occurrence_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
)
from acfqp.phase3e_runner_v1 import (
    Phase3EDecisionAuthorizationV1,
    Phase3ERunResultV1,
    PreparedPhase3ERunV1,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteSelection,
    TransactionV1,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    semantic_verifier_spec_v1,
)
import acfqp.semantic_verification_v1 as semantic_verification
from tests.test_phase3e_transactions_v1 import _world


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


def _mock_failed_local_run(world) -> Phase3ERunResultV1:
    """Typed mock for glue testing; all authority checks remain real."""

    registry = world["registry"]
    profile = official_comparison_profile_v1(registry)
    execution_recorder = NativeCounterRecorderV1(
        subject_id=world["first_transaction"].transaction_id,
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
        decision_point_id=world["first_decision_point"].decision_point_id,
        transaction_id=world["first_transaction"].transaction_id,
        work_vector_id=execution_work.work_vector.work_vector_id,
    )
    post_audit = replace(
        old_execution.post_audit,
        decision_point_id=world["first_decision_point"].decision_point_id,
        transaction_id=world["first_transaction"].transaction_id,
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
        subject_id=world["first_transaction"].transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-occurrence-runner-verification-fake-v1",
    )
    verification_recorder.add("common.protocol_checks", 1)
    verification_work = verification_recorder.seal()
    actual_profile = official_actual_projection_profile_v1(registry, profile)
    aggregate = derive_marginal_work_aggregate_v1(
        subject_id=world["first_transaction"].transaction_id,
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
    result = Mock(spec=Phase3ERunResultV1)
    result.selected_route = RouteSelection.LOCAL
    result.selected_upper = SimpleNamespace(
        route_upper_bound_envelope_id=world["first_local_upper_id"],
        transaction_id=world["first_transaction"].transaction_id,
        transaction_index=1,
        frontier_snapshot_id=world["first_frontier"].frontier_snapshot_id,
        route_cap_profile_id=world["cap"].route_cap_profile_id,
    )
    result.route_execution = SimpleNamespace(
        semantic_execution=semantic_execution
    )
    result.selected_route_work = execution_work
    # These fields are retained into occurrence accounting, but the tested
    # fail-closed path never reaches aggregate derivation.
    result.common_prefix_work = world.get(
        "first_common_prefix_work", world["second_common_prefix_work"]
    )
    result.verification_suffix_work = verification_work
    result.aggregate_marginal_work = aggregate
    return result


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
    world["second_local_upper"] = replace(
        world["second_local_upper"],
        upper_bounds=tuple((axis, 3) for axis in SHARED_AXES),
    )
    world["second_route_decision"] = MarginalRouteDecisionV1.select(
        world["second_decision_point"],
        world["second_fallback_upper"],
        causal=world["second_causal"],
        local_upper=world["second_local_upper"],
    )
    assert world["second_route_decision"].selected_route is RouteSelection.FALLBACK
    return world


def _fallback_package(world, failed_run, *, local_executor, fallback_executor):
    first_execution = failed_run.route_execution.semantic_execution
    first_binding = AttestationContextV1(
        world["first_context"],
        world["first_decision_point"].decision_point_id,
        world["first_transaction"].transaction_id,
        20,
    )
    first_work = _semantic_authority(
        role=SemanticRole.WORK_VECTOR,
        artifact=failed_run.selected_route_work.work_vector,
        artifact_id=failed_run.selected_route_work.work_vector.work_vector_id,
        outcome="VALID",
        binding=first_binding,
        label="first-work",
    )
    first_local = _semantic_authority(
        role=SemanticRole.LOCAL_SOLVER_RESULT,
        artifact=first_execution.local_result,
        artifact_id=first_execution.local_result.local_transaction_result_id,
        outcome=first_execution.local_result.outcome.value,
        binding=first_binding,
        label="first-local",
    )
    first_post = _semantic_authority(
        role=SemanticRole.POST_AUDIT,
        artifact=first_execution.post_audit,
        artifact_id=first_execution.post_audit.post_audit_certificate_id,
        outcome=first_execution.post_audit.outcome.value,
        binding=first_binding,
        label="first-postaudit",
    )

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
        outcome=RouteSelection.FALLBACK.value,
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
        first_work,
        first_local,
        first_post,
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


def _mock_fallback_run(world) -> Phase3ERunResultV1:
    registry = world["registry"]
    profile = official_comparison_profile_v1(registry)
    execution_recorder = NativeCounterRecorderV1(
        subject_id=world["second_context"].route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-occurrence-runner-fallback-fake-v1",
    )
    execution_recorder.add("fallback.states_expanded", 1)
    execution_recorder.add("fallback.actions_evaluated", 1)
    execution_recorder.record_solver_completion(success=True)
    execution_recorder.record_route_completion(success=True)
    execution_work = execution_recorder.seal()
    verification_recorder = NativeCounterRecorderV1(
        subject_id=world["second_context"].route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-occurrence-runner-fallback-verification-fake-v1",
    )
    verification_recorder.add("common.protocol_checks", 1)
    verification_work = verification_recorder.seal()
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
    semantic_execution = Mock(spec=GroundFallbackExecutionV1)
    semantic_execution.result = SimpleNamespace(
        outcome=GroundFallbackOutcome.FEASIBLE_CERTIFIED
    )
    result = Mock(spec=Phase3ERunResultV1)
    result.selected_route = RouteSelection.FALLBACK
    result.selected_upper = world["second_fallback_upper"]
    result.route_execution = SimpleNamespace(
        semantic_execution=semantic_execution
    )
    result.selected_route_work = execution_work
    result.common_prefix_work = world["second_common_prefix_work"]
    result.verification_suffix_work = verification_work
    result.aggregate_marginal_work = aggregate
    return result


def test_missing_semantic_authority_stops_before_transaction_two_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete structural tx2 package cannot replace semantic replay."""

    world = _world()
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
        world["second_common_prefix_work"],
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

    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error,
        match="transaction-2 authority failed closed",
    ):
        run_phase3e_occurrence_v1(
            prepared,
            local_executor=lambda *_: None,
            fallback_executor=lambda *_: None,
            second_transaction_planner=plan,
        )
    assert calls == {"one_decision": 1, "tx2_executor": 0}


def test_untyped_transaction_two_package_is_rejected_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _world()
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
        world["second_common_prefix_work"],
        Phase3EDecisionAuthorizationV1(object(), object(), ()),
    )
    with pytest.raises(
        Phase3EOccurrenceRunnerV1Error, match="untyped package"
    ):
        run_phase3e_occurrence_v1(
            prepared,
            local_executor=lambda *_: None,
            fallback_executor=lambda *_: None,
            second_transaction_planner=lambda _observation: object(),
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
        match="authorized second-decision fallback executed another route",
    ):
        run_phase3e_occurrence_v1(
            prepared,
            local_executor=lambda *_: None,
            fallback_executor=lambda *_: None,
            second_transaction_planner=lambda _observation: package,
        )
