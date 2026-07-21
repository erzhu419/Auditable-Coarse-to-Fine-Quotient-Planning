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
    LaneEnum,
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
from acfqp.route_upper_formula_v1 import (
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.phase3e_fallback_v1 import GroundFallbackCapProfileV1
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    CardinalitySourceKind,
    DecisionPointV1,
    FrozenCardinalityCollectionV1,
    FrozenCardinalitySourceV1,
    MarginalRouteDecisionV1,
    RouteComparison,
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
    SemanticVerifierNotImplementedError,
    reject_unimplemented_semantic_claim_v1,
    semantic_verifier_spec_v1,
    verify_actual_projection_semantics_v1,
    verify_forbidden_access_violation_semantics_v1,
    verify_marginal_route_decision_semantics_v1,
    verify_route_upper_semantics_v1,
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
    lane: LaneEnum = LaneEnum.OPERATIONAL,
) -> AttestationContextV1:
    return AttestationContextV1(
        context,
        decision or TypedNotApplicable("no decision"),
        transaction or TypedNotApplicable("no transaction"),
        step,
        lane,
    )


def _record(
    role: SemanticRole,
    value: int = 1,
    *,
    lane: LaneEnum = LaneEnum.OPERATIONAL,
) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(role)
    return CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(lane),
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


def test_semantic_replay_lane_is_invocation_typed_and_evaluation_is_noncosted() -> None:
    context = _context("evaluation-work")
    vector = _work(
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        context.route_attempt_id,
    )
    evaluation_binding = _binding(context, lane=LaneEnum.EVALUATION)
    result = verify_work_vector_semantics_v1(
        vector,
        binding=evaluation_binding,
        verification_work_record=_record(
            SemanticRole.WORK_VECTOR,
            lane=LaneEnum.EVALUATION,
        ),
    )
    assert result.attestation.verification_lane is LaneEnum.EVALUATION
    assert result.verification_work_record.path == (
        "evaluation.semantic_integrity_checks"
    )
    assert result.verification_work_record.lane is LaneEnum.EVALUATION

    with pytest.raises(SemanticVerificationV1Error, match="lane differs"):
        verify_work_vector_semantics_v1(
            vector,
            binding=evaluation_binding,
            verification_work_record=_record(SemanticRole.WORK_VECTOR),
        )

    with pytest.raises(SemanticVerificationV1Error, match="lane differs"):
        verify_work_vector_semantics_v1(
            vector,
            binding=_binding(context),
            verification_work_record=_record(
                SemanticRole.WORK_VECTOR,
                lane=LaneEnum.EVALUATION,
            ),
        )


@pytest.mark.parametrize("ref_field", ("decision_point_id", "transaction_id"))
def test_semantic_result_rejects_typed_null_reason_substitution(
    ref_field: str,
) -> None:
    context = _context(f"typed-null-{ref_field}")
    vector = _work(
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        context.route_attempt_id,
    )
    result = verify_work_vector_semantics_v1(
        vector,
        binding=_binding(context),
        verification_work_record=_record(SemanticRole.WORK_VECTOR),
    )
    substituted_binding = replace(
        result.binding,
        **{ref_field: TypedNotApplicable(f"substituted {ref_field} reason")},
    )

    with pytest.raises(
        SemanticVerificationV1Error,
        match="attestation context mismatch",
    ):
        replace(result, binding=substituted_binding)


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
    context = _context("route")
    point = DecisionPointV1(
        context.route_decision_context_id,
        TypedNotApplicable("no local transaction"),
        TypedNotApplicable("no frontier"),
        TypedNotApplicable("no causal search"),
        _id("raw-common-prefix"),
    )
    fallback = _id("raw-fallback")
    raw = MarginalRouteDecisionV1(
        point.decision_point_id,
        TypedNotApplicable("raw"),
        TypedNotApplicable("raw"),
        fallback,
        RouteSelection.FALLBACK,
        RouteComparison.MISSING_LOCAL_UPPER,
        fallback,
    )
    wrong_role = verify_work_vector_semantics_v1(
        _work(RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE, context.route_attempt_id),
        binding=_binding(context, decision=point.decision_point_id),
        verification_work_record=_record(SemanticRole.WORK_VECTOR),
    )
    with pytest.raises(SemanticVerificationV1Error, match="expected verified ROUTE_UPPER"):
        verify_marginal_route_decision_semantics_v1(
            raw,
            context=context,
            decision_point=point,
            fallback_upper_result=wrong_role,
            causal_result=None,
            local_upper_result=None,
            binding=_binding(context, decision=point.decision_point_id),
            verification_work_record=_record(SemanticRole.ROUTE_DECISION),
        )


def test_cardinality_member_deletion_and_rehash_is_not_semantic_authority() -> None:
    """A self-consistent source transport cannot prove catalogue completeness."""

    context = _context("cardinality-source")
    source = FrozenCardinalitySourceV1(
        context.route_decision_context_id,
        RouteKind.DIRECT_FALLBACK,
        _id("route-cap-profile"),
        TypedNotApplicable("fallback source is attempt-scoped"),
        CardinalitySourceKind.FALLBACK_SEARCH_BOUND,
        "fallback-bound-catalogue",
        _id("authoritative-parent"),
        "GroundFallbackSearchSpaceV1",
        SemanticRole.GROUND_FALLBACK.value,
        _id("registered-extraction-profile"),
        (
            FrozenCardinalityCollectionV1(
                "fallback.actions_evaluated",
                tuple(sorted((_id("action-1"), _id("action-2")))),
            ),
        ),
        2,
    )
    assert FrozenCardinalitySourceV1.from_dict(source.to_dict()) == source

    # Deleting a member and recomputing the transport hash produces another
    # well-formed source.  Therefore neither hash can authorize a count until
    # the registered extractor replays an authority-bearing parent artifact.
    omitted = replace(
        source,
        collections=(
            FrozenCardinalityCollectionV1(
                "fallback.actions_evaluated", (_id("action-1"),)
            ),
        ),
    )
    assert omitted.source_artifact_id != source.source_artifact_id
    assert FrozenCardinalitySourceV1.from_dict(omitted.to_dict()) == omitted
    # CARDINALITY_EVIDENCE now has one registered safe-chain fallback
    # handler; this generic member-list transport is outside that profile and
    # still cannot mint a result.
    assert semantic_verifier_spec_v1(
        SemanticRole.CARDINALITY_EVIDENCE
    ).implemented
    with pytest.raises(
        SemanticVerificationV1Error, match="implemented"
    ):
        reject_unimplemented_semantic_claim_v1(
            SemanticRole.CARDINALITY_EVIDENCE, claimed_outcome="VALID"
        )


def test_formula_valid_upper_cannot_use_self_hashed_cardinality_as_authority() -> None:
    """Exact upper arithmetic does not elevate its raw count input to evidence."""

    context = _context("raw-cardinality-upper")
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    cap = GroundFallbackCapProfileV1(
        max_states_expanded=100,
        max_actions_evaluated=200,
        max_ground_steps=200,
        max_outcome_rows=800,
        max_bellman_backups=10_000,
        max_composed_candidates=10_000,
        max_cap_checks=20_000,
        max_positive_outcomes_per_step=4,
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        TypedNotApplicable("fallback has no local transaction"),
        TypedNotApplicable("fallback has no local frontier"),
        TypedNotApplicable("fallback has no causal evidence"),
        _id("raw-cardinality-common-prefix"),
    )
    formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=cap,
    )
    cardinality = CardinalityEvidenceV1(
        context.route_decision_context_id,
        RouteKind.DIRECT_FALLBACK,
        cap.route_cap_profile_id,
        TypedNotApplicable("fallback is attempt-scoped"),
        tuple((name, 0) for name in formula.required_count_names),
        (_id("self-hashed-cardinality-source"),),
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
    with pytest.raises(
        SemanticVerificationV1Error, match="semantic replay"
    ):
        verify_route_upper_semantics_v1(
            upper,
            derivation_proof=proof,
            cardinality_result=cardinality,  # type: ignore[arg-type]
            context=context,
            decision_point=point,
            cap_profile=cap,
            formula=formula,
            transaction=None,
            causal=None,
            binding=_binding(context, decision=point.decision_point_id),
            verification_work_record=_record(SemanticRole.ROUTE_UPPER),
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
    no_transaction = TypedNotApplicable(
        "preselection violation has no transaction"
    )
    operational_binding = _binding(
        context,
        decision=point,
        transaction=no_transaction,
        step=1,
    )
    binding = _binding(
        context,
        decision=point,
        transaction=no_transaction,
        step=1,
        lane=LaneEnum.EVALUATION,
    )
    controller = FailClosedAccessController(context.route_attempt_id, point)
    with pytest.raises(AccessProtocolViolation) as caught:
        controller.record(AccessOperation.KERNEL_STEP, AccessRouteScope.LOCAL)
    protocol_result = verify_forbidden_access_violation_semantics_v1(
        caught.value.violation,
        access_log=controller.snapshot(),
        profile=controller.profile,
        binding=operational_binding,
        verification_work_record=_record(SemanticRole.PROTOCOL_ACCESS),
    )
    work_result = verify_work_vector_semantics_v1(
        _work(RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE, context.route_attempt_id),
        binding=binding,
        verification_work_record=_record(
            SemanticRole.WORK_VECTOR,
            lane=LaneEnum.EVALUATION,
        ),
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
        no_transaction,
        work_result.attestation.artifact_id,
        evidence_ids,
    )
    terminal_result = verify_terminal_classification_semantics_v1(
        terminal,
        evidence_results=(work_result, protocol_result),
        binding=binding,
        verification_work_record=_record(
            SemanticRole.TERMINAL_CLASSIFICATION,
            lane=LaneEnum.EVALUATION,
        ),
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
            verification_work_record=_record(
                SemanticRole.TERMINAL_CLASSIFICATION,
                lane=LaneEnum.EVALUATION,
            ),
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
    second.record(
        AccessOperation.READ_FROZEN_RAPM,
        AccessRouteScope.COMMON,
        artifact_id=_id("wrong-log-rapm"),
    )
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
    binding = _binding(context, lane=LaneEnum.EVALUATION)
    work = verify_work_vector_semantics_v1(
        _work(RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE, context.route_attempt_id),
        binding=binding,
        verification_work_record=_record(
            SemanticRole.WORK_VECTOR,
            lane=LaneEnum.EVALUATION,
        ),
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
            verification_work_record=_record(
                SemanticRole.TERMINAL_CLASSIFICATION,
                lane=LaneEnum.EVALUATION,
            ),
        )
