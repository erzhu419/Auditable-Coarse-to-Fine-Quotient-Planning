from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib

import pytest

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    OUTPUT_BYTES,
    PEAK_MOUNTED_BYTES,
    PEAK_WORKING_BYTES,
    PROCESS_LAUNCHES,
    READ_BYTES,
    SHARED_AXES,
    STAGED_BYTES,
    ComparisonProfileV1,
    ComparisonVectorV1,
    LaneEnum,
    ProjectionTermV1,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    PROTOCOL_FAILURE,
    UPPER_BOUND_VIOLATION,
    WITHIN_SELECTED_UPPER,
    ActualAccountingProtocolError,
    ActualAccountingV1Error,
    ActualProjectionProfileV1,
    ActualProjectionProofV1,
    ActualResultRefsV1,
    ActualWorkScope,
    OccurrenceWorkSumV1,
    UpperBoundViolationError,
    derive_actual_projection_v1,
    derive_occurrence_work_sum_v1,
    official_actual_projection_profile_v1,
    verify_actual_projection_v1,
    verify_actual_result_refs_v1,
    verify_occurrence_work_sum_v1,
    verify_selected_upper_compliance_v1,
)
from acfqp.route_upper_formula_v1 import (
    RouteUpperDerivationProofV1,
    RouteUpperFormulaV1,
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    CausalOutcome,
    DecisionPointV1,
    FrontierSnapshotV1,
    MarginalRouteDecisionV1,
    RouteComparison,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TransactionV1,
    TypedNotApplicable,
)


def _cid(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _environment() -> tuple[object, ComparisonProfileV1, ActualProjectionProfileV1]:
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    return registry, comparison, actual


def _work(
    route_kind: RouteKindEnum,
    subject: str,
    **overrides: int,
) -> WorkVectorV1:
    registry = official_counter_registry_v1()
    values = {path: 0 for path in registry.required_paths}
    for encoded_path, value in overrides.items():
        path = encoded_path.replace("__", ".")
        assert path in values
        values[path] = value
    records = explicit_records_v1(
        registry, values, recorder_id="actual-recorder-v1"
    )
    return registry.materialize(
        subject_id=subject,
        route_kind=route_kind,
        records=records,
    )


def _project(
    work: WorkVectorV1, scope: ActualWorkScope
) -> tuple[ComparisonVectorV1, ActualProjectionProofV1]:
    registry, comparison, actual = _environment()
    return derive_actual_projection_v1(
        work,
        registry,
        comparison,
        actual,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=scope,
    )


def _occurrence_inputs(
    label: str,
    *,
    prefix_values: dict[str, int] | None = None,
    local_values: dict[str, int] | None = None,
    fallback_values: dict[str, int] | None = None,
):
    registry, comparison, actual = _environment()
    logical_occurrence_id = _cid(f"{label}-logical-occurrence")
    context = RouteDecisionContextV1(
        _cid(f"{label}-preregistration"),
        _cid(f"{label}-protocol"),
        comparison.comparison_profile_id,
        registry.registry_id,
        _cid(f"{label}-structural"),
        _cid(f"{label}-query"),
        _cid(f"{label}-plan"),
        _cid(f"{label}-threshold"),
        _cid(f"{label}-epoch"),
        logical_occurrence_id,
        _cid(f"{label}-route-attempt"),
    )
    prefix_work = _work(
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        context.route_decision_context_id,
        **(prefix_values or {}),
    )
    prefix = (
        prefix_work,
        *_project(prefix_work, ActualWorkScope.COMMON_PREFIX),
    )
    decision_point = DecisionPointV1(
        context.route_decision_context_id,
        1,
        _cid(f"{label}-frontier"),
        _cid(f"{label}-causal"),
        prefix_work.work_vector_id,
    )
    transaction = TransactionV1(
        logical_occurrence_id,
        context.route_attempt_id,
        decision_point.decision_point_id,
        1,
        decision_point.frontier_snapshot_id,
        _cid(f"{label}-cap-profile"),
    )
    local_work = _work(
        RouteKindEnum.LOCAL_ATTEMPT,
        transaction.transaction_id,
        **(local_values or {}),
    )
    fallback_work = _work(
        RouteKindEnum.DIRECT_FALLBACK,
        context.route_attempt_id,
        **(fallback_values or {}),
    )
    local = (
        local_work,
        *_project(local_work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION),
    )
    fallback = (
        fallback_work,
        *_project(fallback_work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION),
    )
    return (
        logical_occurrence_id,
        context,
        decision_point,
        transaction,
        prefix,
        local,
        fallback,
    )


def _refs(
    work: WorkVectorV1,
    comparison: ComparisonVectorV1,
    proof: ActualProjectionProofV1,
) -> ActualResultRefsV1:
    return ActualResultRefsV1(
        work.work_vector_id,
        comparison.comparison_vector_id,
        proof.actual_projection_proof_id,
    )


@dataclass(frozen=True)
class _UpperEvidence:
    upper: RouteUpperBoundEnvelopeV1
    context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    decision: MarginalRouteDecisionV1
    proof: RouteUpperDerivationProofV1
    cardinality: CardinalityEvidenceV1
    cap: RouteCapProfileV1
    formula: RouteUpperFormulaV1
    transaction: TransactionV1
    causal: CausalEvidenceV1


def _upper(
    leaf_overrides: dict[str, int], *, label: str = "authoritative-upper"
) -> _UpperEvidence:
    """Build a real local upper and a dominating fallback comparison.

    Compliance tests must not manufacture envelopes/proofs and then bless them
    with a test callback; this helper goes through the production formula
    derivation path and returns every replay input.
    """

    registry, comparison, _ = _environment()
    cap = RouteCapProfileV1()
    context = RouteDecisionContextV1(
        _cid(f"{label}-preregistration"),
        _cid(f"{label}-protocol"),
        comparison.comparison_profile_id,
        registry.registry_id,
        _cid(f"{label}-structural"),
        _cid(f"{label}-query"),
        _cid(f"{label}-plan"),
        _cid(f"{label}-threshold"),
        _cid(f"{label}-epoch"),
        _cid(f"{label}-occurrence"),
        _cid(f"{label}-attempt"),
    )
    frontier = FrontierSnapshotV1(
        context.route_decision_context_id,
        1,
        (_cid(f"{label}-failed-obligation"),),
    )
    causal = CausalEvidenceV1(
        frontier.frontier_snapshot_id,
        CausalOutcome.FOUND,
        True,
        None,
        1,
        cap.route_cap_profile_id,
        (_cid(f"{label}-failed-obligation"),),
    )
    decision_point = DecisionPointV1(
        context.route_decision_context_id,
        1,
        frontier.frontier_snapshot_id,
        causal.causal_evidence_id,
        _cid(f"{label}-common-prefix-work"),
    )
    transaction = TransactionV1(
        context.logical_occurrence_id,
        context.route_attempt_id,
        decision_point.decision_point_id,
        1,
        frontier.frontier_snapshot_id,
        cap.route_cap_profile_id,
    )
    formula = official_route_upper_formula_v1(
        RouteKind.LOCAL_ATTEMPT,
        registry=registry,
        profile=comparison,
        cap_profile=cap,
    )
    counts = {name: 0 for name in formula.required_count_names}
    counts.update(leaf_overrides)
    cardinality = CardinalityEvidenceV1(
        context.route_decision_context_id,
        RouteKind.LOCAL_ATTEMPT,
        cap.route_cap_profile_id,
        frontier.frontier_snapshot_id,
        tuple(sorted(counts.items())),
        (_cid(f"{label}-local-cardinality-source"),),
    )
    upper, proof = derive_route_upper_v1(
        context=context,
        decision_point=decision_point,
        cardinality=cardinality,
        cap_profile=cap,
        registry=registry,
        profile=comparison,
        formula=formula,
        transaction=transaction,
        causal=causal,
    )

    fallback_formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=comparison,
        cap_profile=cap,
    )
    fallback_counts = {name: 0 for name in fallback_formula.required_count_names}
    for name in fallback_counts:
        if name.startswith(("fallback.", "control.", "process.", "io.", "memory.")):
            fallback_counts[name] = 1_000_000
    fallback_cardinality = CardinalityEvidenceV1(
        context.route_decision_context_id,
        RouteKind.DIRECT_FALLBACK,
        cap.route_cap_profile_id,
        TypedNotApplicable("fallback cardinality is attempt-scoped"),
        tuple(sorted(fallback_counts.items())),
        (_cid(f"{label}-fallback-cardinality-source"),),
    )
    fallback_upper, _ = derive_route_upper_v1(
        context=context,
        decision_point=decision_point,
        cardinality=fallback_cardinality,
        cap_profile=cap,
        registry=registry,
        profile=comparison,
        formula=fallback_formula,
    )
    decision = MarginalRouteDecisionV1.select(
        decision_point,
        fallback_upper,
        causal=causal,
        local_upper=upper,
    )
    assert decision.selected_route is RouteSelection.LOCAL
    return _UpperEvidence(
        upper,
        context,
        decision_point,
        decision,
        proof,
        cardinality,
        cap,
        formula,
        transaction,
        causal,
    )


def _upper_replay_kwargs(evidence: _UpperEvidence) -> dict[str, object]:
    return {
        "selected_upper_id": evidence.upper.route_upper_bound_envelope_id,
        "selected_upper": evidence.upper,
        "route_decision": evidence.decision,
        "route_context": evidence.context,
        "decision_point": evidence.decision_point,
        "upper_derivation_proof": evidence.proof,
        "upper_cardinality": evidence.cardinality,
        "upper_cap_profile": evidence.cap,
        "upper_formula": evidence.formula,
        "upper_transaction": evidence.transaction,
        "upper_causal": evidence.causal,
    }


def test_actual_profile_is_separate_content_addressed_exact_mapping() -> None:
    registry, comparison, actual = _environment()

    assert actual.actual_projection_profile_id not in {
        registry.registry_id,
        comparison.comparison_profile_id,
    }
    assert actual.counter_registry_id == registry.registry_id
    assert actual.comparison_profile_id == comparison.comparison_profile_id
    assert actual.terms == comparison.terms
    assert ActualProjectionProfileV1.from_dict(
        actual.to_dict(), registry, comparison
    ) == actual


def test_actual_profile_rejects_missing_duplicate_unknown_and_changed_terms() -> None:
    registry, comparison, actual = _environment()

    missing = replace(actual, terms=actual.terms[1:])
    with pytest.raises(ActualAccountingV1Error, match="exact official mapping"):
        missing.validate(registry, comparison)

    with pytest.raises(ActualAccountingV1Error, match="repeats"):
        replace(
            actual,
            terms=tuple(
                sorted(
                    actual.terms + (actual.terms[0],),
                    key=lambda term: term.source_leaf,
                )
            ),
        )

    unknown = ProjectionTermV1(
        "unknown.hidden_work",
        NONKERNEL_COMPUTE_EVENTS,
        1,
        LaneEnum.OPERATIONAL,
        "unknown-work-v1",
        ReducerEnum.SUM,
    )
    unknown_profile = replace(
        actual,
        terms=tuple(
            sorted(actual.terms + (unknown,), key=lambda term: term.source_leaf)
        ),
    )
    with pytest.raises(ActualAccountingV1Error, match="unknown"):
        unknown_profile.validate(registry, comparison)

    changed_terms = list(actual.terms)
    changed_terms[0] = replace(changed_terms[0], coefficient=2)
    changed = replace(actual, terms=tuple(changed_terms))
    with pytest.raises(ActualAccountingV1Error, match="exact official mapping"):
        changed.validate(registry, comparison)


def test_actual_profile_rejects_registry_profile_and_evaluation_lane_mismatch() -> None:
    registry, comparison, actual = _environment()

    with pytest.raises(ActualAccountingV1Error, match="registry mismatch"):
        replace(actual, counter_registry_id=_cid("another-registry")).validate(
            registry, comparison
        )
    with pytest.raises(ActualAccountingV1Error, match="comparison-profile mismatch"):
        replace(actual, comparison_profile_id=_cid("another-profile")).validate(
            registry, comparison
        )
    with pytest.raises(ActualAccountingV1Error, match="operational work only"):
        replace(actual, source_lane=LaneEnum.EVALUATION)


def test_actual_projection_recomputes_and_result_refs_are_exact() -> None:
    registry, comparison_profile, actual_profile = _environment()
    work = _work(
        RouteKindEnum.LOCAL_ATTEMPT,
        "local-marginal",
        local__causal_candidate_evaluations=3,
        local__materialization_ground_steps=5,
        io__output_bytes=7,
    )
    comparison, proof = _project(work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION)
    refs = _refs(work, comparison, proof)

    assert ActualResultRefsV1.from_dict(refs.to_dict()) == refs
    assert verify_actual_result_refs_v1(
        refs,
        proof,
        work,
        comparison,
        registry,
        comparison_profile,
        actual_profile,
    ) == comparison
    assert ActualProjectionProofV1.from_dict(proof.to_dict()) == proof


def test_forged_actual_comparison_and_swapped_work_reference_fail() -> None:
    registry, comparison_profile, actual_profile = _environment()
    work = _work(
        RouteKindEnum.LOCAL_ATTEMPT,
        "local-real",
        local__materialization_ground_steps=5,
    )
    comparison, proof = _project(work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION)

    forged_values = dict(comparison.values)
    forged_values[KERNEL_TRANSITION_CALLS] = 0
    forged = ComparisonVectorV1(
        comparison.comparison_profile_id,
        work.work_vector_id,
        comparison.subject_id,
        comparison.route_kind,
        tuple(sorted(forged_values.items())),
    )
    with pytest.raises(ActualAccountingV1Error, match="does not match exact"):
        verify_actual_projection_v1(
            proof,
            work,
            forged,
            registry,
            comparison_profile,
            actual_profile,
        )

    other_work = _work(
        RouteKindEnum.LOCAL_ATTEMPT,
        "local-other",
        local__materialization_ground_steps=5,
    )
    swapped_refs = ActualResultRefsV1(
        other_work.work_vector_id,
        comparison.comparison_vector_id,
        proof.actual_projection_proof_id,
    )
    with pytest.raises(ActualAccountingV1Error, match="actual_work reference mismatch"):
        verify_actual_result_refs_v1(
            swapped_refs,
            proof,
            work,
            comparison,
            registry,
            comparison_profile,
            actual_profile,
        )

    arbitrary_ref_comparison = ComparisonVectorV1(
        comparison.comparison_profile_id,
        _cid("invented-work"),
        comparison.subject_id,
        comparison.route_kind,
        comparison.values,
    )
    with pytest.raises(ActualAccountingV1Error):
        verify_actual_projection_v1(
            proof,
            work,
            arbitrary_ref_comparison,
            registry,
            comparison_profile,
            actual_profile,
        )


def test_post_result_actual_profile_change_invalidates_projection_proof() -> None:
    registry, comparison_profile, actual_profile = _environment()
    work = _work(RouteKindEnum.LOCAL_ATTEMPT, "profile-bound-work")
    comparison, proof = _project(work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION)
    changed_terms = list(actual_profile.terms)
    changed_terms[0] = replace(changed_terms[0], coefficient=2)
    changed_profile = replace(actual_profile, terms=tuple(changed_terms))

    with pytest.raises(ActualAccountingV1Error):
        verify_actual_projection_v1(
            proof,
            work,
            comparison,
            registry,
            comparison_profile,
            changed_profile,
        )


def test_re_signed_projection_proof_cannot_replace_recomputed_proof() -> None:
    registry, comparison_profile, actual_profile = _environment()
    work = _work(RouteKindEnum.LOCAL_ATTEMPT, "proof-source")
    comparison, proof = _project(work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION)
    forged = replace(proof, projection_term_count=proof.projection_term_count - 1)
    assert forged.actual_projection_proof_id != proof.actual_projection_proof_id
    with pytest.raises(ActualAccountingV1Error, match="does not match recomputation"):
        verify_actual_projection_v1(
            forged,
            work,
            comparison,
            registry,
            comparison_profile,
            actual_profile,
        )


def test_evaluation_work_is_rejected_by_operational_actual_projection() -> None:
    registry, comparison_profile, actual_profile = _environment()
    work = _work(RouteKindEnum.LOCAL_ATTEMPT, "evaluation-replay")
    with pytest.raises(ActualAccountingV1Error, match="evaluation/provenance"):
        derive_actual_projection_v1(
            work,
            registry,
            comparison_profile,
            actual_profile,
            source_lane=LaneEnum.EVALUATION,
            work_scope=ActualWorkScope.EVALUATION_REPLAY,
        )


def test_common_prefix_and_marginal_work_are_explicitly_separate() -> None:
    registry, comparison_profile, actual_profile = _environment()
    prefix = _work(
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        "common-prefix",
        common__abstract_bellman_backups=4,
        common__protocol_checks=2,
    )
    prefix_comparison, prefix_proof = derive_actual_projection_v1(
        prefix,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.COMMON_PREFIX,
    )
    assert prefix_comparison.value(NONKERNEL_COMPUTE_EVENTS) == 6
    assert prefix_proof.work_scope is ActualWorkScope.COMMON_PREFIX

    with pytest.raises(ActualAccountingV1Error, match="marginal work"):
        derive_actual_projection_v1(
            prefix,
            registry,
            comparison_profile,
            actual_profile,
            source_lane=LaneEnum.OPERATIONAL,
            work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        )

    contaminated = _work(
        RouteKindEnum.LOCAL_ATTEMPT,
        "contaminated-marginal",
        common__protocol_checks=1,
        local__causal_candidate_evaluations=1,
    )
    with pytest.raises(ActualAccountingV1Error, match="forbidden work"):
        derive_actual_projection_v1(
            contaminated,
            registry,
            comparison_profile,
            actual_profile,
            source_lane=LaneEnum.OPERATIONAL,
            work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        )


def test_selected_upper_compliance_passes_only_for_marginal_exact_actual() -> None:
    registry, comparison_profile, actual_profile = _environment()
    evidence = _upper(
        {
            "local.causal_candidate_evaluations": 4,
            "local.materialization_ground_steps": 6,
            "io.output_bytes": 8,
        }
    )
    work = _work(
        RouteKindEnum.LOCAL_ATTEMPT,
        evidence.transaction.transaction_id,
        local__causal_candidate_evaluations=3,
        local__materialization_ground_steps=5,
        io__output_bytes=7,
    )
    comparison, proof = _project(work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION)

    assert verify_selected_upper_compliance_v1(
        **_upper_replay_kwargs(evidence),
        refs=_refs(work, comparison, proof),
        proof=proof,
        vector=work,
        claimed_comparison=comparison,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    ) == WITHIN_SELECTED_UPPER

    with pytest.raises(ActualAccountingProtocolError, match="selected upper reference"):
        verify_selected_upper_compliance_v1(
            selected_upper_id=_cid("wrong-upper"),
            selected_upper=evidence.upper,
            route_decision=evidence.decision,
            route_context=evidence.context,
            decision_point=evidence.decision_point,
            upper_derivation_proof=evidence.proof,
            upper_cardinality=evidence.cardinality,
            upper_cap_profile=evidence.cap,
            upper_formula=evidence.formula,
            upper_transaction=evidence.transaction,
            upper_causal=evidence.causal,
            refs=_refs(work, comparison, proof),
            proof=proof,
            vector=work,
            claimed_comparison=comparison,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )


def test_upper_excess_is_typed_upper_bound_violation_and_protocol_failure() -> None:
    registry, comparison_profile, actual_profile = _environment()
    evidence = _upper({"local.materialization_ground_steps": 4})
    work = _work(
        RouteKindEnum.LOCAL_ATTEMPT,
        evidence.transaction.transaction_id,
        local__materialization_ground_steps=5,
    )
    comparison, proof = _project(work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION)

    with pytest.raises(UpperBoundViolationError) as captured:
        verify_selected_upper_compliance_v1(
            **_upper_replay_kwargs(evidence),
            refs=_refs(work, comparison, proof),
            proof=proof,
            vector=work,
            claimed_comparison=comparison,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )
    assert captured.value.violation_code == UPPER_BOUND_VIOLATION
    assert captured.value.terminal_code == PROTOCOL_FAILURE
    assert captured.value.violated_axes == (KERNEL_TRANSITION_CALLS,)


def test_common_prefix_cannot_be_compared_to_marginal_selected_upper() -> None:
    registry, comparison_profile, actual_profile = _environment()
    evidence = _upper({})
    work = _work(
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        "prefix-not-route",
        common__protocol_checks=3,
    )
    comparison, proof = _project(work, ActualWorkScope.COMMON_PREFIX)
    with pytest.raises(ActualAccountingProtocolError, match="marginal upper"):
        verify_selected_upper_compliance_v1(
            **_upper_replay_kwargs(evidence),
            refs=_refs(work, comparison, proof),
            proof=proof,
            vector=work,
            claimed_comparison=comparison,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )


def test_occurrence_sum_retains_refs_and_replays_sum_and_max_reducers() -> None:
    registry, comparison_profile, actual_profile = _environment()
    (
        occurrence_id,
        context,
        decision_point,
        transaction,
        prefix,
        local,
        fallback,
    ) = _occurrence_inputs(
        "aggregate",
        prefix_values={
            "common__protocol_checks": 2,
            "io__read_bytes": 11,
            "io__mounted_bytes_peak": 100,
            "memory__working_bytes_peak": 60,
        },
        local_values={
            "local__causal_candidate_evaluations": 3,
            "local__materialization_ground_steps": 5,
            "io__output_bytes": 17,
            "io__mounted_bytes_peak": 80,
            "memory__working_bytes_peak": 90,
        },
        fallback_values={
            "fallback__states_expanded": 7,
            "fallback__ground_steps": 13,
            "io__output_bytes": 19,
            "io__mounted_bytes_peak": 120,
            "memory__working_bytes_peak": 70,
        },
    )
    prefix_work, _, _ = prefix
    local_work, _, _ = local
    fallback_work, _, _ = fallback
    occurrence = derive_occurrence_work_sum_v1(
        logical_occurrence_id=occurrence_id,
        route_context=context,
        decision_point=decision_point,
        local_transaction=transaction,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
        common_prefix=prefix,
        local_attempt=local,
        fallback=fallback,
    )
    aggregate = dict(occurrence.aggregate_values)

    assert occurrence.common_prefix_work_id == prefix_work.work_vector_id
    assert occurrence.local_attempt_work_id == local_work.work_vector_id
    assert occurrence.fallback_work_id == fallback_work.work_vector_id
    assert aggregate[KERNEL_TRANSITION_CALLS] == 18
    assert aggregate[NONKERNEL_COMPUTE_EVENTS] == 12
    assert aggregate[READ_BYTES] == 11
    assert aggregate[OUTPUT_BYTES] == 36
    assert aggregate[PEAK_MOUNTED_BYTES] == 120
    assert aggregate[PEAK_WORKING_BYTES] == 90
    assert aggregate[PROCESS_LAUNCHES] == 0
    assert aggregate[STAGED_BYTES] == 0
    assert OccurrenceWorkSumV1.from_dict(occurrence.to_dict()) == occurrence
    verify_occurrence_work_sum_v1(
        occurrence,
        logical_occurrence_id=occurrence_id,
        route_context=context,
        decision_point=decision_point,
        local_transaction=transaction,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
        common_prefix=prefix,
        local_attempt=local,
        fallback=fallback,
    )


def test_occurrence_sum_rejects_tampered_aggregate_and_swapped_route_inputs() -> None:
    registry, comparison_profile, actual_profile = _environment()
    (
        occurrence_id,
        context,
        decision_point,
        transaction,
        prefix,
        local,
        fallback,
    ) = _occurrence_inputs("tamper")
    occurrence = derive_occurrence_work_sum_v1(
        logical_occurrence_id=occurrence_id,
        route_context=context,
        decision_point=decision_point,
        local_transaction=transaction,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
        common_prefix=prefix,
        local_attempt=local,
        fallback=fallback,
    )
    values = dict(occurrence.aggregate_values)
    values[OUTPUT_BYTES] = 1
    forged = replace(occurrence, aggregate_values=tuple(sorted(values.items())))
    with pytest.raises(ActualAccountingV1Error, match="does not match"):
        verify_occurrence_work_sum_v1(
            forged,
            logical_occurrence_id=occurrence_id,
            route_context=context,
            decision_point=decision_point,
            local_transaction=transaction,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
            common_prefix=prefix,
            local_attempt=local,
            fallback=fallback,
        )

    with pytest.raises(ActualAccountingV1Error):
        derive_occurrence_work_sum_v1(
            logical_occurrence_id=occurrence_id,
            route_context=context,
            decision_point=decision_point,
            local_transaction=transaction,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
            common_prefix=prefix,
            local_attempt=fallback,
            fallback=local,
        )


def test_occurrence_sum_rejects_cross_occurrence_workvector_splicing() -> None:
    registry, comparison_profile, actual_profile = _environment()
    first = _occurrence_inputs("first-occurrence")
    second = _occurrence_inputs("second-occurrence")
    occurrence_id, context, decision_point, transaction, prefix, _, fallback = first
    foreign_local = second[5]

    with pytest.raises(ActualAccountingV1Error, match="subject mismatch"):
        derive_occurrence_work_sum_v1(
            logical_occurrence_id=occurrence_id,
            route_context=context,
            decision_point=decision_point,
            local_transaction=transaction,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
            common_prefix=prefix,
            local_attempt=foreign_local,
            fallback=fallback,
        )


def test_upper_compliance_rejects_foreign_decision_and_unverified_derivation() -> None:
    registry, comparison_profile, actual_profile = _environment()
    evidence = _upper({"local.causal_candidate_evaluations": 1}, label="selected")
    foreign = _upper(
        {"local.causal_candidate_evaluations": 2}, label="foreign"
    )
    work = _work(
        RouteKindEnum.LOCAL_ATTEMPT, evidence.transaction.transaction_id
    )
    comparison, proof = _project(work, ActualWorkScope.MARGINAL_ROUTE_EXECUTION)

    with pytest.raises(ActualAccountingProtocolError, match="does not bind"):
        verify_selected_upper_compliance_v1(
            selected_upper_id=foreign.upper.route_upper_bound_envelope_id,
            selected_upper=foreign.upper,
            route_decision=evidence.decision,
            route_context=foreign.context,
            decision_point=foreign.decision_point,
            upper_derivation_proof=foreign.proof,
            upper_cardinality=foreign.cardinality,
            upper_cap_profile=foreign.cap,
            upper_formula=foreign.formula,
            upper_transaction=foreign.transaction,
            upper_causal=foreign.causal,
            refs=_refs(work, comparison, proof),
            proof=proof,
            vector=work,
            claimed_comparison=comparison,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )

    forged_leaves = dict(evidence.proof.leaf_upper_bounds)
    first_leaf = next(iter(forged_leaves))
    forged_leaves[first_leaf] += 1
    self_signed_proof = replace(
        evidence.proof, leaf_upper_bounds=tuple(sorted(forged_leaves.items()))
    )
    with pytest.raises(ActualAccountingProtocolError, match="derivation replay failed"):
        verify_selected_upper_compliance_v1(
            **{
                **_upper_replay_kwargs(evidence),
                "upper_derivation_proof": self_signed_proof,
            },
            refs=_refs(work, comparison, proof),
            proof=proof,
            vector=work,
            claimed_comparison=comparison,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )

    with pytest.raises(TypeError, match="upper_derivation_verifier"):
        verify_selected_upper_compliance_v1(
            **_upper_replay_kwargs(evidence),
            upper_derivation_verifier=lambda _upper, _proof: True,
            refs=_refs(work, comparison, proof),
            proof=proof,
            vector=work,
            claimed_comparison=comparison,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )
