from __future__ import annotations

import phase3e_route_guard_cases as _cases
import pytest

from acfqp.auditable_router import (
    ABSTRACT_AUDIT,
    ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
    CACHE_PROOF,
    COMPATIBILITY,
    INTEGRITY,
    MATCH,
    MISS,
    PASS,
    RouteTraceEvent,
    TransitionEvidence,
    append_route_event,
    build_route_envelope,
)
from acfqp.phase3e_predecision_acceptance import (
    EvidenceSemanticVerification,
    GuardProfileCommitment,
    Phase3EPredecisionAcceptanceError,
    accept_phase3e_predecision_mechanics,
)
from acfqp.route_envelope_verifier import (
    ArtifactVerificationAttestation,
    VerifiedRouteInputCatalog,
)
from acfqp.route_protocol_guard import (
    PLAN_CERTIFICATE_CANDIDATE,
    ActualProjectionCandidate,
    ProjectionTerm,
)


_ROLES = (
    "ABSTRACT_AUDIT",
    "CACHE_PROOF",
    "CAUSAL_SEARCH",
    "COMPATIBILITY",
    "FALLBACK_RESULT",
    "INTEGRITY",
    "LOCAL_RESULT",
    "ROUTE_SELECTION",
)


def _scenario():
    fixture = _cases._fixture()
    verifier_profiles = tuple((role, f"verifier-{role.lower()}") for role in _ROLES)
    commitment = GuardProfileCommitment(
        fixture.context.context_id,
        fixture.context.preregistration_skeleton_id,
        fixture.registry.registry_id,
        fixture.profile.profile_id,
        fixture.cap_profile.profile_id,
        fixture.local_projection.projection_id,
        fixture.fallback_projection.projection_id,
        verifier_profiles,
    )
    extra_attestations = (
        ArtifactVerificationAttestation(
            commitment.commitment_id,
            "guard_profile_commitment",
            fixture.context.context_id,
            "verify-guard-profile",
        ),
        ArtifactVerificationAttestation(
            "policy-graph",
            "policy_graph",
            fixture.context.context_id,
            "verify-policy-graph",
        ),
    )
    catalog = VerifiedRouteInputCatalog(
        fixture.context.context_id,
        fixture.profile,
        fixture.catalog.cardinalities,
        fixture.catalog.formulas,
        fixture.catalog.bounds,
        fixture.catalog.artifact_attestations + extra_attestations,
    )
    evidence = (
        TransitionEvidence(
            fixture.context.context_id,
            INTEGRITY,
            PASS,
            _cases._refs(
                guard_profile_commitment=commitment.commitment_id,
                integrity_attestation="integrity-ok",
            ),
            _cases._work(
                fixture.registry, fixture.context.context_id, INTEGRITY, None
            ),
        ),
        TransitionEvidence(
            fixture.context.context_id,
            COMPATIBILITY,
            MATCH,
            _cases._refs(compatibility_attestation="compatibility-ok"),
            _cases._work(
                fixture.registry, fixture.context.context_id, COMPATIBILITY, None
            ),
        ),
        TransitionEvidence(
            fixture.context.context_id,
            CACHE_PROOF,
            MISS,
            _cases._refs(cache_proof_check="cache-check"),
            _cases._work(
                fixture.registry, fixture.context.context_id, CACHE_PROOF, None
            ),
        ),
        TransitionEvidence(
            fixture.context.context_id,
            ABSTRACT_AUDIT,
            PASS,
            _cases._refs(
                abstract_audit="abstract-audit",
                policy_graph="policy-graph",
                threshold_profile="threshold-1",
            ),
            _cases._work(
                fixture.registry, fixture.context.context_id, ABSTRACT_AUDIT, None
            ),
        ),
    )
    verified = {
        row.artifact_id for row in catalog.artifact_attestations
    } | {
        fixture.profile.profile_id,
        fixture.local_bound.bound_id,
        fixture.fallback_bound.bound_id,
    }
    events: list[RouteTraceEvent] = []
    for row in evidence:
        events.append(
            append_route_event(
                context=fixture.context,
                events=events,
                evidence=row,
                registry=fixture.registry,
                bounds=catalog.bound_map,
                verified_artifact_ids=verified,
            )
        )
    envelope = build_route_envelope(
        context=fixture.context,
        events=events,
        registry=fixture.registry,
        bounds=catalog.bound_map,
        verified_artifact_ids=verified,
        complete=True,
    )
    profile_by_role = dict(verifier_profiles)
    semantic_results = tuple(
        EvidenceSemanticVerification(
            fixture.context.context_id,
            event.evidence.evidence_id,
            event.evidence.role,
            event.evidence.outcome,
            profile_by_role[event.evidence.role],
            tuple(sorted(artifact_id for _, artifact_id in event.evidence.artifact_refs)),
        )
        for event in events
    )
    return fixture, catalog, commitment, envelope, semantic_results


def test_no_causal_abstract_route_accepts_empty_decision_binding_set() -> None:
    fixture, catalog, commitment, envelope, semantic_results = _scenario()
    outcome = accept_phase3e_predecision_mechanics(
        envelope=envelope,
        context=fixture.context,
        registry=fixture.registry,
        catalog=catalog,
        cap_profile=fixture.cap_profile,
        decision_points=(),
        local_projection=fixture.local_projection,
        fallback_projection=fixture.fallback_projection,
        guard_commitment=commitment,
        semantic_results=semantic_results,
    )
    assert outcome.outcome_kind == PLAN_CERTIFICATE_CANDIDATE
    assert outcome.final_state == ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL
    assert outcome.decision_binding_ids == ()
    assert outcome.official is False
    assert outcome.to_dict()["official_n_break_even"] is None


def test_semantic_outcome_forgery_is_rejected() -> None:
    fixture, catalog, commitment, envelope, semantic_results = _scenario()
    first = semantic_results[0]
    forged = (
        EvidenceSemanticVerification(
            first.context_id,
            first.evidence_id,
            first.evidence_role,
            "FAIL",
            first.verifier_profile_id,
            first.source_artifact_ids,
        ),
        *semantic_results[1:],
    )
    with pytest.raises(Phase3EPredecisionAcceptanceError, match="disagrees"):
        accept_phase3e_predecision_mechanics(
            envelope=envelope,
            context=fixture.context,
            registry=fixture.registry,
            catalog=catalog,
            cap_profile=fixture.cap_profile,
            decision_points=(),
            local_projection=fixture.local_projection,
            fallback_projection=fixture.fallback_projection,
            guard_commitment=commitment,
            semantic_results=forged,
        )


def test_posthoc_zero_projection_is_rejected_before_acceptance() -> None:
    fixture, catalog, _, envelope, semantic_results = _scenario()
    bad_projection = ActualProjectionCandidate(
        fixture.registry.registry_id,
        fixture.profile.profile_id,
        "LOCAL_ATTEMPT",
        "zero-byte-projection",
        (
            ProjectionTerm("resource.bytes", "work.bytes", 0),
            ProjectionTerm("resource.operations", "work.operations", 1),
        ),
    )
    commitment = GuardProfileCommitment(
        fixture.context.context_id,
        fixture.context.preregistration_skeleton_id,
        fixture.registry.registry_id,
        fixture.profile.profile_id,
        fixture.cap_profile.profile_id,
        bad_projection.projection_id,
        fixture.fallback_projection.projection_id,
        tuple((role, f"verifier-{role.lower()}") for role in _ROLES),
    )
    with pytest.raises(Phase3EPredecisionAcceptanceError, match="strictly positive"):
        accept_phase3e_predecision_mechanics(
            envelope=envelope,
            context=fixture.context,
            registry=fixture.registry,
            catalog=catalog,
            cap_profile=fixture.cap_profile,
            decision_points=(),
            local_projection=bad_projection,
            fallback_projection=fixture.fallback_projection,
            guard_commitment=commitment,
            semantic_results=semantic_results,
        )
