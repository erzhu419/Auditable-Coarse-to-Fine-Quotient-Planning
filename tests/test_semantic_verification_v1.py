from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp.access_protocol_v1 import (
    AccessOperation,
    AccessProtocolViolation,
    AccessRouteScope,
    FailClosedAccessController,
)
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    CounterRecordV1,
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    derive_actual_projection_v1,
    official_actual_projection_profile_v1,
)
from acfqp.routing_v1 import (
    MarginalRouteDecisionV1,
    RouteComparison,
    RouteDecisionContextV1,
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
    SemanticVerifierNotImplementedError,
    semantic_verifier_spec_v1,
    verify_actual_projection_semantics_v1,
    verify_forbidden_access_violation_semantics_v1,
    verify_marginal_route_decision_semantics_v1,
    verify_terminal_classification_semantics_v1,
    verify_typed_attestation_v1,
    verify_work_vector_semantics_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _context(label: str = "base", **overrides: str) -> RouteDecisionContextV1:
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    values = {
        "preregistration_id": _id(f"preregister-{label}"),
        "protocol_id": _id(f"protocol-{label}"),
        "comparison_profile_id": comparison.comparison_profile_id,
        "counter_registry_id": registry.registry_id,
        "structural_id": _id(f"structural-{label}"),
        "query_id": _id(f"query-{label}"),
        "selected_plan_id": _id(f"plan-{label}"),
        "threshold_profile_id": _id(f"threshold-{label}"),
        "build_epoch_id": _id(f"epoch-{label}"),
        "logical_occurrence_id": _id(f"occurrence-{label}"),
        "route_attempt_id": _id(f"attempt-{label}"),
    }
    values.update(overrides)
    return RouteDecisionContextV1(**values)


def _binding(
    context: RouteDecisionContextV1,
    *,
    decision: str | TypedNotApplicable | None = None,
    transaction: str | TypedNotApplicable | None = None,
    step: int = 7,
) -> AttestationContextV1:
    return AttestationContextV1(
        context,
        decision or TypedNotApplicable("no decision"),
        transaction or TypedNotApplicable("no transaction"),
        step,
    )


def _record(role: SemanticRole, value: int = 1) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    return CounterRecordV1.observe(
        registry,
        semantic_verifier_spec_v1(role).verification_counter_path,
        value,
        recorder_id=f"{role.value.lower()}-verifier-test-v1",
    )


def _work(route: RouteKindEnum, subject: str, **overrides: int):
    registry = official_counter_registry_v1()
    values = {path: 0 for path in registry.required_paths}
    values.update(overrides)
    return registry.materialize(
        subject_id=subject,
        route_kind=route,
        records=explicit_records_v1(
            registry, values, recorder_id="semantic-native-test-v1"
        ),
    )


def test_work_vector_is_bound_to_attested_attempt_subject() -> None:
    context = _context("work")
    vector = _work(RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE, context.route_attempt_id)
    result = verify_work_vector_semantics_v1(
        vector,
        binding=_binding(context),
        verification_work_record=_record(SemanticRole.WORK_VECTOR),
    )
    assert result.attestation.artifact_id == vector.work_vector_id
    assert result.binding.route_context == context

    other = _context("other")
    with pytest.raises(SemanticVerificationV1Error, match="subject"):
        verify_work_vector_semantics_v1(
            vector,
            binding=_binding(other),
            verification_work_record=_record(SemanticRole.WORK_VECTOR),
        )


def test_local_work_and_actual_projection_require_matching_transaction_subject() -> None:
    context = _context("local")
    point = _id("local-point")
    transaction = _id("local-transaction")
    binding = _binding(context, decision=point, transaction=transaction)
    vector = _work(
        RouteKindEnum.LOCAL_ATTEMPT,
        transaction,
        **{"local.materialization_ground_steps": 2},
    )
    registry = official_counter_registry_v1()
    comparison_profile = official_comparison_profile_v1(registry)
    actual_profile = official_actual_projection_profile_v1(
        registry, comparison_profile
    )
    comparison, proof = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane="operational",
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    )
    verified = verify_actual_projection_semantics_v1(
        vector=vector,
        claimed_comparison=comparison,
        projection_proof=proof,
        binding=binding,
        verification_work_record=_record(SemanticRole.ACTUAL_PROJECTION),
    )
    assert isinstance(verified.artifact, ComparisonVectorV1)

    with pytest.raises(SemanticVerificationV1Error, match="subject"):
        verify_actual_projection_semantics_v1(
            vector=vector,
            claimed_comparison=comparison,
            projection_proof=proof,
            binding=_binding(
                context, decision=point, transaction=_id("other-transaction")
            ),
            verification_work_record=_record(SemanticRole.ACTUAL_PROJECTION),
        )


def test_route_decision_semantics_fail_closed_until_route_upper_authorities_exist() -> None:
    point = _id("raw-point")
    fallback = _id("raw-fallback")
    raw = MarginalRouteDecisionV1(
        point,
        TypedNotApplicable("raw"),
        TypedNotApplicable("raw"),
        fallback,
        RouteSelection.FALLBACK,
        RouteComparison.MISSING_LOCAL_UPPER,
        fallback,
    )
    with pytest.raises(SemanticVerifierNotImplementedError, match="ROUTE_DECISION"):
        verify_marginal_route_decision_semantics_v1(
            raw,
            context=_context("route"),
            decision_point={},
            fallback_upper={},
            causal=None,
            local_upper=None,
            binding=_binding(_context("route")),
            verification_work_record=_record(SemanticRole.ROUTE_DECISION),
        )


def test_typed_attestation_transport_requires_authority_result() -> None:
    context = _context("attestation")
    result = verify_work_vector_semantics_v1(
        _work(RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE, context.route_attempt_id),
        binding=_binding(context),
        verification_work_record=_record(SemanticRole.WORK_VECTOR),
    )
    assert verify_typed_attestation_v1(
        result.attestation, authority_result=result
    ) == result.attestation
    forged = replace(result.attestation, query_id=_id("forged-query"))
    with pytest.raises(SemanticVerificationV1Error, match="authority-bearing"):
        verify_typed_attestation_v1(forged, authority_result=result)


def _verified_protocol_terminal(label: str = "protocol"):
    context = _context(label)
    point = _id(f"{label}-point")
    binding = _binding(context, decision=point, step=1)
    controller = FailClosedAccessController(context.route_attempt_id, point)
    with pytest.raises(AccessProtocolViolation) as caught:
        controller.record(AccessOperation.KERNEL_STEP, AccessRouteScope.LOCAL)
    protocol_result = verify_forbidden_access_violation_semantics_v1(
        caught.value.violation,
        access_log=controller.snapshot(),
        profile=controller.profile,
        binding=binding,
        verification_work_record=_record(SemanticRole.PROTOCOL_ACCESS),
    )
    work_result = verify_work_vector_semantics_v1(
        _work(RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE, context.route_attempt_id),
        binding=binding,
        verification_work_record=_record(SemanticRole.WORK_VECTOR),
    )
    evidence_ids = tuple(
        sorted(
            (
                work_result.attestation.verification_attestation_id,
                protocol_result.attestation.verification_attestation_id,
            )
        )
    )
    terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
        TerminalCode.PROTOCOL_FAILURE,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        point,
        TypedNotApplicable("preselection violation has no transaction"),
        work_result.attestation.artifact_id,
        evidence_ids,
    )
    terminal_result = verify_terminal_classification_semantics_v1(
        terminal,
        evidence_results=(work_result, protocol_result),
        binding=binding,
        verification_work_record=_record(SemanticRole.TERMINAL_CLASSIFICATION),
    )
    return context, binding, controller, work_result, protocol_result, terminal_result


def test_protocol_failure_terminal_requires_replayed_forbidden_access() -> None:
    _, binding, _, work_result, protocol_result, terminal_result = (
        _verified_protocol_terminal()
    )
    assert terminal_result.outcome == TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE.value
    terminal = terminal_result.artifact
    with pytest.raises(SemanticVerificationV1Error):
        verify_terminal_classification_semantics_v1(
            terminal,
            evidence_results=(work_result,),
            binding=binding,
            verification_work_record=_record(SemanticRole.TERMINAL_CLASSIFICATION),
        )
    assert protocol_result.outcome == "PROTOCOL_FAILURE"


def test_protocol_evidence_rejects_claimed_violation_from_another_log() -> None:
    context = _context("wrong-log")
    point = _id("wrong-log-point")
    binding = _binding(context, decision=point, step=1)
    first = FailClosedAccessController(context.route_attempt_id, point)
    with pytest.raises(AccessProtocolViolation) as caught:
        first.record(AccessOperation.KERNEL_STEP, AccessRouteScope.LOCAL)
    second = FailClosedAccessController(context.route_attempt_id, point)
    second.record(AccessOperation.READ_FROZEN_RAPM, AccessRouteScope.COMMON)
    with pytest.raises(SemanticVerificationV1Error):
        verify_forbidden_access_violation_semantics_v1(
            caught.value.violation,
            access_log=second.snapshot(),
            profile=second.profile,
            binding=binding,
            verification_work_record=_record(SemanticRole.PROTOCOL_ACCESS),
        )


@pytest.mark.parametrize(
    ("terminal_class", "terminal_code", "missing_role"),
    (
        (
            TerminalClass.PLAN_CERTIFICATE,
            TerminalCode.ABSTRACT_CERTIFIED,
            "ABSTRACT_AUDIT",
        ),
        (
            TerminalClass.INFEASIBILITY_CERTIFICATE,
            TerminalCode.CACHED_EXACT_INFEASIBLE,
            "EXACT_CACHED_INFEASIBILITY",
        ),
    ),
)
def test_positive_and_infeasibility_terminals_remain_fail_closed(
    terminal_class: TerminalClass,
    terminal_code: TerminalCode,
    missing_role: str,
) -> None:
    context = _context(terminal_code.value)
    binding = _binding(context)
    work = verify_work_vector_semantics_v1(
        _work(RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE, context.route_attempt_id),
        binding=binding,
        verification_work_record=_record(SemanticRole.WORK_VECTOR),
    )
    terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        terminal_class,
        terminal_code,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        TypedNotApplicable("no decision"),
        TypedNotApplicable("no transaction"),
        work.attestation.artifact_id,
        (work.attestation.verification_attestation_id,),
    )
    with pytest.raises(SemanticVerifierNotImplementedError, match=missing_role):
        verify_terminal_classification_semantics_v1(
            terminal,
            evidence_results=(work,),
            binding=binding,
            verification_work_record=_record(SemanticRole.TERMINAL_CLASSIFICATION),
        )
