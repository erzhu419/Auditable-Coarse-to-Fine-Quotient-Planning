from __future__ import annotations

from dataclasses import dataclass

import pytest

from acfqp.auditable_router import (
    ABSTRACT_AUDIT,
    CACHE_PROOF,
    CAUSAL_SEARCH,
    CERTIFIED,
    CERTIFIED_FEASIBLE,
    COMPATIBILITY,
    FAIL,
    FAILED_NO_SOUND_FRONTIER,
    FALLBACK_RESULT,
    FOUND,
    FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
    INTEGRITY,
    LOCAL_RESULT,
    MATCH,
    MISS,
    NO_SOUND_COVER,
    PASS,
    ROUTE_SELECTION,
    SELECT_LOCAL,
    RouteDecisionContext,
    RouteTraceEnvelope,
    RouteTraceEvent,
    TransitionEvidence,
    append_route_event,
    build_route_envelope,
    evidence_work_subject,
)
from acfqp.phase3e_accounting import phase3e_preregistration_skeleton
from acfqp.route_comparison import (
    DIRECT_FALLBACK,
    LOCAL_ATTEMPT,
    AxisTerm,
    CardinalityEvidence,
    ComparisonFormulaCandidate,
    ComparisonProfileCandidate,
    RouteUpperBoundCandidate,
    derive_route_upper_bound,
)
from acfqp.route_envelope_verifier import (
    ArtifactVerificationAttestation,
    VerifiedRouteInputCatalog,
)
from acfqp.route_protocol_guard import (
    PLAN_CERTIFICATE_CANDIDATE,
    ActualProjectionCandidate,
    DecisionPointBinding,
    ProjectionTerm,
    RouteCapProfileCandidate,
    RouteProtocolGuardError,
    certify_guarded_route_candidate,
    derive_actual_comparison,
)
from acfqp.work_accounting import (
    BYTE,
    CHARGED_BYTE,
    CHARGED_OP,
    OPERATION,
    OPERATIONAL,
    CounterLeaf,
    CounterRegistry,
    WorkVector,
    sum_work_vectors,
)


def _registry() -> CounterRegistry:
    return CounterRegistry(
        "route-guard-test",
        "v1",
        (
            CounterLeaf("work.bytes", CHARGED_BYTE, BYTE, OPERATIONAL, "test"),
            CounterLeaf("work.operations", CHARGED_OP, OPERATION, OPERATIONAL, "test"),
        ),
    )


def _refs(**rows: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(rows.items()))


def _work(
    registry: CounterRegistry,
    context_id: str,
    role: str,
    transaction_id: str | None,
    *,
    operations: int = 1,
    byte_count: int = 0,
) -> WorkVector:
    return WorkVector(
        registry.registry_id,
        evidence_work_subject(context_id, role, transaction_id),
        (("work.bytes", byte_count), ("work.operations", operations)),
    )


@dataclass(frozen=True)
class Fixture:
    registry: CounterRegistry
    profile: ComparisonProfileCandidate
    context: RouteDecisionContext
    local_cardinality: CardinalityEvidence
    fallback_cardinality: CardinalityEvidence
    local_formula: ComparisonFormulaCandidate
    fallback_formula: ComparisonFormulaCandidate
    local_bound: RouteUpperBoundCandidate
    fallback_bound: RouteUpperBoundCandidate
    catalog: VerifiedRouteInputCatalog
    cap_profile: RouteCapProfileCandidate
    local_projection: ActualProjectionCandidate
    fallback_projection: ActualProjectionCandidate


def _fixture() -> Fixture:
    registry = _registry()
    profile = ComparisonProfileCandidate(
        "guard-shared-axes",
        "v0",
        ("resource.bytes", "resource.operations"),
    )
    context = RouteDecisionContext(
        phase3e_preregistration_skeleton()["skeleton_id"],
        "protocol-candidate",
        profile.profile_id,
        registry.registry_id,
        "structural-1",
        "query-1",
        "plan-1",
        "threshold-1",
        "epoch-1",
        "occurrence-1",
        "attempt-1",
    )
    local_cardinality = CardinalityEvidence(
        context.context_id,
        LOCAL_ATTEMPT,
        (("input.bytes", 10), ("input.operations", 1)),
        ("source-local",),
    )
    fallback_cardinality = CardinalityEvidence(
        context.context_id,
        DIRECT_FALLBACK,
        (("input.bytes", 20), ("input.operations", 2)),
        ("source-fallback",),
    )
    terms = (
        AxisTerm("resource.bytes", "input.bytes", 1),
        AxisTerm("resource.operations", "input.operations", 1),
    )
    local_formula = ComparisonFormulaCandidate(
        profile.profile_id, LOCAL_ATTEMPT, "local-formula", terms
    )
    fallback_formula = ComparisonFormulaCandidate(
        profile.profile_id, DIRECT_FALLBACK, "fallback-formula", terms
    )
    local_bound = derive_route_upper_bound(profile, local_cardinality, local_formula)
    fallback_bound = derive_route_upper_bound(
        profile, fallback_cardinality, fallback_formula
    )
    artifacts = {
        "source-local": "cardinality_source",
        "source-fallback": "cardinality_source",
        "integrity-ok": "integrity_attestation",
        "compatibility-ok": "compatibility_attestation",
        "cache-check": "cache_proof_check",
        "abstract-audit": "abstract_audit",
        "failed-proof": "failed_proof_graph",
        "threshold-1": "threshold_profile",
        "causal-certificate": "causal_certificate",
        "local-authorization": "local_authorization",
        "causal-exhaustion": "causal_exhaustion_attestation",
        "frontier-1": "frontier_snapshot",
        "local-cap-1": "local_cap_profile",
        "fallback-cap-1": "fallback_cap_profile",
        "local-result": "local_result",
        "post-audit-pass": "post_audit_certificate",
        "post-audit-fail": "post_audit_failure",
        "fallback-result": "fallback_result",
        "ground-certificate": "ground_certificate",
    }
    attestations = tuple(
        ArtifactVerificationAttestation(
            artifact_id,
            role,
            context.context_id,
            f"verified-{artifact_id}",
        )
        for artifact_id, role in sorted(artifacts.items())
    )
    catalog = VerifiedRouteInputCatalog(
        context.context_id,
        profile,
        (fallback_cardinality, local_cardinality),
        (fallback_formula, local_formula),
        (fallback_bound, local_bound),
        attestations,
    )
    cap_profile = RouteCapProfileCandidate(context.context_id, "one-local-tx", 1)
    projection_terms = (
        ProjectionTerm("resource.bytes", "work.bytes", 1),
        ProjectionTerm("resource.operations", "work.operations", 1),
    )
    local_projection = ActualProjectionCandidate(
        registry.registry_id,
        profile.profile_id,
        LOCAL_ATTEMPT,
        "local-actual-projection",
        projection_terms,
    )
    fallback_projection = ActualProjectionCandidate(
        registry.registry_id,
        profile.profile_id,
        DIRECT_FALLBACK,
        "fallback-actual-projection",
        projection_terms,
    )
    return Fixture(
        registry,
        profile,
        context,
        local_cardinality,
        fallback_cardinality,
        local_formula,
        fallback_formula,
        local_bound,
        fallback_bound,
        catalog,
        cap_profile,
        local_projection,
        fallback_projection,
    )


def _append(
    fixture: Fixture,
    events: list[RouteTraceEvent],
    evidence: TransitionEvidence,
) -> None:
    verified_ids = {
        row.artifact_id for row in fixture.catalog.artifact_attestations
    } | {
        fixture.profile.profile_id,
        fixture.local_bound.bound_id,
        fixture.fallback_bound.bound_id,
        evidence.work_delta.vector_id,
    }
    if evidence.actual_comparison is not None:
        verified_ids.add(evidence.actual_comparison.vector_id)
    events.append(
        append_route_event(
            context=fixture.context,
            events=events,
            evidence=evidence,
            registry=fixture.registry,
            bounds=fixture.catalog.bound_map,
            verified_artifact_ids=verified_ids,
        )
    )


def _base_events(
    fixture: Fixture, *, causal_outcome: str = FOUND
) -> tuple[list[RouteTraceEvent], TransitionEvidence]:
    context = fixture.context
    registry = fixture.registry
    events: list[RouteTraceEvent] = []
    rows = (
        TransitionEvidence(
            context.context_id,
            INTEGRITY,
            PASS,
            _refs(integrity_attestation="integrity-ok"),
            _work(registry, context.context_id, INTEGRITY, None),
        ),
        TransitionEvidence(
            context.context_id,
            COMPATIBILITY,
            MATCH,
            _refs(compatibility_attestation="compatibility-ok"),
            _work(registry, context.context_id, COMPATIBILITY, None),
        ),
        TransitionEvidence(
            context.context_id,
            CACHE_PROOF,
            MISS,
            _refs(cache_proof_check="cache-check"),
            _work(registry, context.context_id, CACHE_PROOF, None),
        ),
        TransitionEvidence(
            context.context_id,
            ABSTRACT_AUDIT,
            FAIL,
            _refs(
                abstract_audit="abstract-audit",
                failed_proof_graph="failed-proof",
                threshold_profile="threshold-1",
            ),
            _work(registry, context.context_id, ABSTRACT_AUDIT, None),
        ),
    )
    for row in rows:
        _append(fixture, events, row)
    causal_refs = (
        _refs(
            causal_certificate="causal-certificate",
            frontier_snapshot="frontier-1",
            local_authorization="local-authorization",
        )
        if causal_outcome == FOUND
        else _refs(
            causal_exhaustion_attestation="causal-exhaustion",
            frontier_snapshot="frontier-1",
        )
    )
    causal = TransitionEvidence(
        context.context_id,
        CAUSAL_SEARCH,
        causal_outcome,
        causal_refs,
        _work(registry, context.context_id, CAUSAL_SEARCH, "transaction-1"),
        transaction_id="transaction-1",
    )
    _append(fixture, events, causal)
    return events, causal


def _selection(fixture: Fixture, *, local: bool) -> TransitionEvidence:
    context = fixture.context
    refs = {
        "comparison_profile": fixture.profile.profile_id,
        "fallback_cap_profile": "fallback-cap-1",
        "fallback_upper_bound": fixture.fallback_bound.bound_id,
    }
    if local:
        refs.update(
            {
                "local_cap_profile": "local-cap-1",
                "local_upper_bound": fixture.local_bound.bound_id,
            }
        )
    return TransitionEvidence(
        context.context_id,
        ROUTE_SELECTION,
        SELECT_LOCAL if local else "SELECT_FALLBACK_NO_LOCAL",
        tuple(sorted(refs.items())),
        _work(fixture.registry, context.context_id, ROUTE_SELECTION, "transaction-1"),
        transaction_id="transaction-1",
        local_bound_id=fixture.local_bound.bound_id if local else None,
        fallback_bound_id=fixture.fallback_bound.bound_id,
    )


def _decision(
    fixture: Fixture,
    causal: TransitionEvidence,
    *,
    local_allowed: bool,
) -> DecisionPointBinding:
    return DecisionPointBinding(
        fixture.context.context_id,
        "transaction-1",
        1,
        "frontier-1",
        causal.evidence_id,
        causal.outcome,
        fixture.local_bound.bound_id if local_allowed else None,
        fixture.fallback_bound.bound_id,
        "local-cap-1" if local_allowed else None,
        "fallback-cap-1",
    )


def _actual_result(
    fixture: Fixture,
    *,
    role: str,
    outcome: str,
    byte_count: int,
    operations: int,
) -> TransitionEvidence:
    route = LOCAL_ATTEMPT if role == LOCAL_RESULT else DIRECT_FALLBACK
    projection = (
        fixture.local_projection if role == LOCAL_RESULT else fixture.fallback_projection
    )
    work = _work(
        fixture.registry,
        fixture.context.context_id,
        role,
        "transaction-1",
        operations=operations,
        byte_count=byte_count,
    )
    actual = derive_actual_comparison(
        work=work,
        context_id=fixture.context.context_id,
        registry=fixture.registry,
        profile=fixture.profile,
        projection=projection,
    )
    if role == LOCAL_RESULT:
        refs = {
            "actual_comparison": actual.vector_id,
            "actual_work": work.vector_id,
            "local_cap_profile": "local-cap-1",
            "local_result": "local-result",
            (
                "post_audit_certificate"
                if outcome == CERTIFIED
                else "post_audit_failure"
            ): "post-audit-pass" if outcome == CERTIFIED else "post-audit-fail",
        }
    else:
        refs = {
            "actual_comparison": actual.vector_id,
            "actual_work": work.vector_id,
            "fallback_cap_profile": "fallback-cap-1",
            "fallback_result": "fallback-result",
            "ground_certificate": "ground-certificate",
        }
    return TransitionEvidence(
        fixture.context.context_id,
        role,
        outcome,
        tuple(sorted(refs.items())),
        work,
        transaction_id="transaction-1",
        actual_comparison=actual,
    )


def _certify(
    fixture: Fixture,
    envelope: RouteTraceEnvelope,
    decision: DecisionPointBinding,
):
    return certify_guarded_route_candidate(
        envelope=envelope,
        context=fixture.context,
        registry=fixture.registry,
        catalog=fixture.catalog,
        cap_profile=fixture.cap_profile,
        decision_points=(decision,),
        local_projection=fixture.local_projection,
        fallback_projection=fixture.fallback_projection,
    )


def test_guarded_local_certificate_recomputes_transaction_actual_work() -> None:
    fixture = _fixture()
    events, causal = _base_events(fixture)
    _append(fixture, events, _selection(fixture, local=True))
    _append(
        fixture,
        events,
        _actual_result(
            fixture,
            role=LOCAL_RESULT,
            outcome=CERTIFIED,
            byte_count=9,
            operations=1,
        ),
    )
    verified = {row.artifact_id for row in fixture.catalog.artifact_attestations} | {
        fixture.profile.profile_id,
        fixture.local_bound.bound_id,
        fixture.fallback_bound.bound_id,
        *(event.evidence.work_delta.vector_id for event in events),
        *(
            event.evidence.actual_comparison.vector_id
            for event in events
            if event.evidence.actual_comparison is not None
        ),
    }
    envelope = build_route_envelope(
        context=fixture.context,
        events=events,
        registry=fixture.registry,
        bounds=fixture.catalog.bound_map,
        verified_artifact_ids=verified,
        complete=True,
    )
    outcome = _certify(fixture, envelope, _decision(fixture, causal, local_allowed=True))
    assert outcome.outcome_kind == PLAN_CERTIFICATE_CANDIDATE
    assert outcome.final_state == LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL


def test_negative_causal_result_cannot_select_local_even_with_cheap_bound() -> None:
    fixture = _fixture()
    events, causal = _base_events(fixture, causal_outcome=NO_SOUND_COVER)
    _append(fixture, events, _selection(fixture, local=True))
    _append(
        fixture,
        events,
        _actual_result(
            fixture,
            role=LOCAL_RESULT,
            outcome=CERTIFIED,
            byte_count=9,
            operations=1,
        ),
    )
    accumulated = sum_work_vectors(
        (event.evidence.work_delta for event in events),
        subject_id=f"route-attempt:{fixture.context.route_attempt_id}",
    )
    envelope = RouteTraceEnvelope(
        fixture.context.context_id,
        tuple(events),
        events[-1].state_after,
        accumulated,
        True,
    )
    with pytest.raises(RouteProtocolGuardError, match="negative causal"):
        _certify(
            fixture,
            envelope,
            _decision(fixture, causal, local_allowed=False),
        )


def test_failed_local_work_is_retained_before_certified_fallback() -> None:
    fixture = _fixture()
    events, causal = _base_events(fixture)
    _append(fixture, events, _selection(fixture, local=True))
    failed_local = _actual_result(
        fixture,
        role=LOCAL_RESULT,
        outcome=FAILED_NO_SOUND_FRONTIER,
        byte_count=9,
        operations=1,
    )
    _append(fixture, events, failed_local)
    fallback = _actual_result(
        fixture,
        role=FALLBACK_RESULT,
        outcome=CERTIFIED_FEASIBLE,
        byte_count=20,
        operations=2,
    )
    fallback_event = RouteTraceEvent(
        fixture.context.context_id,
        len(events),
        events[-1].state_after,
        FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
        fallback,
        events[-1].event_id,
    )
    events.append(fallback_event)
    accumulated = sum_work_vectors(
        (event.evidence.work_delta for event in events),
        subject_id=f"route-attempt:{fixture.context.route_attempt_id}",
    )
    envelope = RouteTraceEnvelope(
        fixture.context.context_id,
        tuple(events),
        FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
        accumulated,
        True,
    )
    outcome = _certify(fixture, envelope, _decision(fixture, causal, local_allowed=True))
    assert outcome.outcome_kind == PLAN_CERTIFICATE_CANDIDATE
    assert outcome.final_state == FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL
    assert accumulated.value("work.operations") == len(events) + 1
    assert accumulated.value("work.bytes") == 29
