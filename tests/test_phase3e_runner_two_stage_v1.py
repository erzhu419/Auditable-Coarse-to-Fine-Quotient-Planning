from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
from types import SimpleNamespace

import pytest

import acfqp.phase3e_occurrence_runner_v1 as occurrence_runner
import acfqp.phase3e_runner_v1 as runner_module
from acfqp.access_protocol_v1 import (
    AccessOperation,
    AccessRouteScope,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    official_actual_projection_profile_v1,
)
from acfqp.core import Outcome, QuerySpec
from acfqp.native_recorder_v1 import derive_recorded_work_v1
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackExecutionV1,
    _seal_trusted_ground_fallback_execution_v1,
    run_ground_fallback_search_v1,
)
from acfqp.phase3e_occurrence_accounting_v1 import (
    OccurrenceRawEvidenceKind,
    RunnerCommonAccountingEvidenceV1,
)
from acfqp.phase3e_occurrence_runner_v1 import (
    OccurrenceClosureCodeV1,
    run_phase3e_occurrence_v1,
)
from acfqp.phase3e_runner_v1 import (
    ContinuationWorkVectorAuthorityV1,
    Phase3ERouteExecutionV1,
    Phase3ERouteExecutionFailedV1,
    Phase3ERunResultV1,
    Phase3ERunnerV1Error,
    PreparedPhase3ERunV1,
    _require_route_semantic_context_v1,
    _verify_continuation_work_vector_authority_v1,
    continuation_work_vector_authority_v1,
    run_phase3e,
)
from acfqp.phase3e_two_stage_accounting_v1 import (
    AccountingCoreStage,
    VerificationChargeObligationV1,
    VerificationChargePlanV1,
    derive_two_stage_accounting_v1,
    seal_accounting_core_v1,
)
from acfqp.routing_v1 import TypedNotApplicable
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    verify_ground_fallback_semantics_v1,
)
from tests.test_phase3e_partial_failure_evidence_v1 import (
    _forbidden_local,
    _prepared,
)


@dataclass(frozen=True)
class _State:
    name: str


class _OneStepKernel:
    horizon = 1
    registered_reward_features = ("reward",)
    registered_goals = ("default",)

    def __init__(self) -> None:
        self.start = _State("start")
        self.end = _State("terminal")

    def reward_upper_bound(self, horizon, raw_weights, goal):
        return Fraction(horizon * raw_weights.get("reward", 0))

    def initial_distribution(self):
        return ((Fraction(1), self.start),)

    def actions(self, state):
        return ("advance",) if state == self.start else ()

    def step(self, state, action):
        assert state == self.start and action == "advance"
        return (
            Outcome(
                Fraction(1),
                self.end,
                (("reward", Fraction(1)),),
                failure=False,
                terminal=True,
            ),
        )

    def is_terminal(self, state):
        return state == self.end


def _cap() -> GroundFallbackCapProfileV1:
    return GroundFallbackCapProfileV1(
        max_states_expanded=10,
        max_actions_evaluated=10,
        max_ground_steps=10,
        max_outcome_rows=10,
        max_bellman_backups=10,
        max_composed_candidates=10,
        max_cap_checks=100,
        max_positive_outcomes_per_step=1,
    )


def _accounted_prepared(monkeypatch: pytest.MonkeyPatch):
    prepared, registry, profile = _prepared(monkeypatch)
    decision, upper = prepared.validate(registry, profile)
    actual = official_actual_projection_profile_v1(registry, profile)
    charged_results = prepared.authorization.charged_verification_results
    freeze_step = min(
        result.binding.verified_at_protocol_step for result in charged_results
    ) - 1
    binding = AttestationContextV1(
        prepared.context,
        prepared.decision_point.decision_point_id,
        TypedNotApplicable("common prefix has no local transaction"),
        freeze_step,
    )
    core = seal_accounting_core_v1(
        recorded_work=prepared.common_prefix_work,
        binding=binding,
        core_stage=AccountingCoreStage.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    )
    obligations = tuple(
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
    )
    plan = VerificationChargePlanV1.for_core(
        core,
        plan_frozen_at_protocol_step=freeze_step,
        obligations=obligations,
    )
    closure = derive_two_stage_accounting_v1(
        core=core,
        core_work=prepared.common_prefix_work,
        plan=plan,
        semantic_results=charged_results,
        route_context=prepared.context,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    )
    accounted = replace(
        prepared,
        two_stage_accounting_profile=True,
        common_accounting_core=core,
        common_verification_charge_plan=plan,
    )

    def validated(_self, _registry, _profile):
        return decision, upper, closure

    monkeypatch.setattr(PreparedPhase3ERunV1, "validate", validated)
    return accounted, decision, upper, registry, profile


def _fallback_execution(prepared, decision, upper, registry, profile):
    cap = _cap()
    kernel = _OneStepKernel()
    query = QuerySpec.from_state(
        kernel.start,
        horizon=1,
        reward_weights=(("reward", Fraction(1)),),
        delta=Fraction(1, 20),
    )
    raw = run_ground_fallback_search_v1(
        kernel,
        query,
        route_decision_context_id=prepared.context.route_decision_context_id,
        decision_point_id=prepared.decision_point.decision_point_id,
        route_decision_id=decision.route_decision_id,
        selected_upper_id=upper.route_upper_bound_envelope_id,
        route_attempt_id=prepared.context.route_attempt_id,
        query_id=prepared.context.query_id,
        cap_profile=cap,
    )
    sealed = _seal_trusted_ground_fallback_execution_v1(
        raw,
        constraint_delta=Fraction(1, 20),
    )
    native = derive_recorded_work_v1(
        sealed.work_vector,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
    )
    execution = Phase3ERouteExecutionV1(
        sealed.result.ground_fallback_result_id,
        True,
        False,
        native,
        sealed,
        sealed.result.outcome.value,
        (),
        semantic_verification_deferred=True,
    )
    return cap, execution


def _executor_for(execution: Phase3ERouteExecutionV1):
    def executor(_prepared, controller, _recorder):
        controller.record(
            AccessOperation.FALLBACK_SOLVER_INVOCATION,
            AccessRouteScope.FALLBACK,
        )
        steps = execution.native_execution_work.work_vector.value(
            "fallback.ground_steps"
        )
        for _ in range(steps):
            controller.record(
                AccessOperation.KERNEL_STEP,
                AccessRouteScope.FALLBACK,
            )
            controller.record(
                AccessOperation.GROUND_OUTCOME_ENUMERATION,
                AccessRouteScope.FALLBACK,
            )
        controller.record(
            AccessOperation.FALLBACK_RESULT_ARTIFACT,
            AccessRouteScope.FALLBACK,
            artifact_id=execution.artifact_id,
        )
        return execution

    return executor


def _successful_run(monkeypatch: pytest.MonkeyPatch):
    prepared, decision, upper, registry, profile = _accounted_prepared(monkeypatch)
    cap, execution = _fallback_execution(
        prepared, decision, upper, registry, profile
    )
    chronology: list[str] = []
    fallback_executor = _executor_for(execution)

    def selected_executor(*args):
        chronology.append("execute")
        return fallback_executor(*args)

    def deferred_verifier(route_execution, binding, records):
        chronology.append("verify")
        assert len(records) == 1
        assert isinstance(route_execution.semantic_execution, GroundFallbackExecutionV1)
        return (
            verify_ground_fallback_semantics_v1(
                route_execution.semantic_execution,
                cap_profile=cap,
                binding=binding,
                verification_work_record=records[0],
                registry=registry,
            ),
        )

    result = run_phase3e(
        prepared,
        local_executor=_forbidden_local,
        fallback_executor=selected_executor,
        deferred_route_verifier=deferred_verifier,
        registry=registry,
        comparison_profile=profile,
    )
    return result, prepared, chronology


def test_run_phase3e_closes_exact_common_and_selected_two_stage_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _prepared_run, chronology = _successful_run(monkeypatch)

    assert chronology == ["execute", "verify"]
    assert result.two_stage_accounting_profile is True
    assert result.accounted_common_work == result.common_two_stage_accounting.aggregate_work
    assert result.accounted_common_work != result.common_prefix_work
    charged: dict[str, int] = {}
    for semantic_result in result.common_verification_results:
        record = semantic_result.verification_work_record
        charged[record.path] = charged.get(record.path, 0) + record.value
    for path, exact_charge in charged.items():
        assert result.common_two_stage_accounting.verification_suffix.work_vector.value(
            path
        ) == exact_charge
        assert result.accounted_common_work.work_vector.value(path) == (
            result.common_prefix_work.work_vector.value(path) + exact_charge
        )
    assert result.selected_two_stage_accounting.aggregate_work.work_vector == (
        result.aggregate_marginal_work.aggregate_work_vector
    )
    assert len(result.selected_two_stage_accounting.manifest.entries) == 2
    assert len(result.selected_two_stage_accounting.manifest.nonsemantic_entries) == 4
    assert result.selected_two_stage_accounting.verification_suffix == (
        result.verification_suffix_work
    )


def test_occurrence_aggregates_genuine_two_stage_runner_closures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, prepared, _chronology = _successful_run(monkeypatch)
    assert type(run) is Phase3ERunResultV1
    monkeypatch.setattr(
        occurrence_runner,
        "run_phase3e",
        lambda *_args, **_kwargs: run,
    )

    occurrence = run_phase3e_occurrence_v1(
        prepared,
        local_executor=_forbidden_local,
        fallback_executor=lambda *_args: None,
    )

    assert occurrence.closure_code is OccurrenceClosureCodeV1.FULL_GROUND_FALLBACK
    common = occurrence.work_components[0].raw_work[0]
    assert type(common) is RunnerCommonAccountingEvidenceV1
    assert common.core == run.common_prefix_work
    assert common.closure == run.common_two_stage_accounting
    common_ref = occurrence.occurrence_work.component_refs[0].raw_work_refs[0]
    assert common_ref.evidence_kind is (
        OccurrenceRawEvidenceKind.TWO_STAGE_ACCOUNTED_COMMON
    )
    assert prepared.decision_point.common_prefix_work_id == (
        run.common_prefix_work.work_vector.work_vector_id
    )
    assert common_ref.work_vector_id == (
        run.common_two_stage_accounting.aggregate_work.work_vector.work_vector_id
    )


def test_continuation_authority_allows_changed_plan_but_rejects_source_splice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, prepared, _chronology = _successful_run(monkeypatch)
    authority = continuation_work_vector_authority_v1(result)
    changed_plan_context = replace(
        prepared.context,
        selected_plan_id=hashlib.sha256(b"stitched-plan-for-tx2").hexdigest(),
    )
    evidence = _verify_continuation_work_vector_authority_v1(
        authority,
        current_context=changed_plan_context,
    )
    assert authority.prior_run_identity_id in evidence

    spliced = ContinuationWorkVectorAuthorityV1(
        hashlib.sha256(b"foreign-prior-run").hexdigest(),
        result,
    )
    with pytest.raises(Phase3ERunnerV1Error, match="stale"):
        _verify_continuation_work_vector_authority_v1(
            spliced,
            current_context=changed_plan_context,
        )


def test_run_phase3e_deferred_semantic_omission_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared, decision, upper, registry, profile = _accounted_prepared(monkeypatch)
    _cap_profile, execution = _fallback_execution(
        prepared, decision, upper, registry, profile
    )
    with pytest.raises(
        Phase3ERouteExecutionFailedV1,
        match="omitted or padded",
    ) as caught:
        run_phase3e(
            prepared,
            local_executor=_forbidden_local,
            fallback_executor=_executor_for(execution),
            deferred_route_verifier=lambda *_: (),
            registry=registry,
            comparison_profile=profile,
        )
    assert caught.value.evidence.common_two_stage_accounting is not None
    assert caught.value.evidence.accounted_common_work == (
        caught.value.evidence.common_two_stage_accounting.aggregate_work
    )


@pytest.mark.parametrize(
    ("check_name", "charged_nonsemantic_count"),
    (
        ("access", 1),
        ("integrity", 2),
        ("aggregate", 3),
        ("upper", 4),
    ),
)
def test_selected_runner_checks_charge_only_the_executed_prefix_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    check_name: str,
    charged_nonsemantic_count: int,
) -> None:
    prepared, decision, upper, registry, profile = _accounted_prepared(monkeypatch)
    _cap_profile, execution = _fallback_execution(
        prepared, decision, upper, registry, profile
    )

    if check_name == "access":
        monkeypatch.setattr(
            runner_module,
            "_require_selected_access_trace",
            lambda **_kwargs: (_ for _ in ()).throw(
                Phase3ERunnerV1Error("injected access check failure")
            ),
        )
    elif check_name == "integrity":
        original = runner_module.verify_recorded_work_v1
        calls = 0

        def fail_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise Phase3ERunnerV1Error("injected integrity check failure")
            return original(*args, **kwargs)

        monkeypatch.setattr(runner_module, "verify_recorded_work_v1", fail_second)
    elif check_name == "aggregate":
        original = runner_module.derive_marginal_work_aggregate_v1
        calls = 0

        def fail_first(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise Phase3ERunnerV1Error("injected aggregate check failure")
            return original(*args, **kwargs)

        monkeypatch.setattr(
            runner_module, "derive_marginal_work_aggregate_v1", fail_first
        )
    else:
        monkeypatch.setattr(
            runner_module,
            "_check_authoritative_upper",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                Phase3ERunnerV1Error("injected upper check failure")
            ),
        )

    with pytest.raises(Phase3ERouteExecutionFailedV1) as caught:
        run_phase3e(
            prepared,
            local_executor=_forbidden_local,
            fallback_executor=_executor_for(execution),
            deferred_route_verifier=lambda route_execution, binding, records: (
                verify_ground_fallback_semantics_v1(
                    route_execution.semantic_execution,
                    cap_profile=_cap_profile,
                    binding=binding,
                    verification_work_record=records[0],
                    registry=registry,
                ),
            ),
            registry=registry,
            comparison_profile=profile,
        )
    verification = caught.value.evidence.partial_verification_work.work_vector
    # One WORK_VECTOR integrity verification and one route-semantic protocol
    # verification always precede the runner-owned four-check suffix.
    assert verification.value("common.integrity_checks") == 1
    assert verification.value("common.protocol_checks") == (
        1 + charged_nonsemantic_count
    )


def test_route_semantic_context_rejects_typed_null_reason_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, prepared, _chronology = _successful_run(monkeypatch)
    semantic_result = result.route_execution.semantic_verification_results[0]
    attacked_execution = SimpleNamespace(
        semantic_verification_results=(
            SimpleNamespace(
                binding=replace(
                    semantic_result.binding,
                    transaction_id=TypedNotApplicable(
                        "substituted fallback reason"
                    ),
                )
            ),
        )
    )
    with pytest.raises(Phase3ERunnerV1Error, match="another transaction"):
        _require_route_semantic_context_v1(
            prepared=prepared,
            selected_upper=result.selected_upper,
            execution=attacked_execution,
            selected=result.selected_route,
            freeze_after_sequence=(
                result.freeze_attestation.last_preselection_sequence
            ),
            final_access_sequence=len(result.access_log.events),
        )
