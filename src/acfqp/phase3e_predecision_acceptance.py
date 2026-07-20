"""Public fail-closed entry for non-official Phase-3E predecision mechanics."""

from __future__ import annotations

from typing import Sequence

from acfqp import _phase3e_predecision_acceptance_impl as _impl
from acfqp.auditable_router import (
    NEXT_LOCAL_TRANSACTION_REQUIRED,
    RouteDecisionContext,
    RouteTraceEnvelope,
)
from acfqp.route_comparison import DIRECT_FALLBACK, LOCAL_ATTEMPT
from acfqp.route_envelope_verifier import VerifiedRouteInputCatalog
from acfqp.route_protocol_guard import (
    ActualProjectionCandidate,
    DecisionPointBinding,
    RouteCapProfileCandidate,
)
from acfqp.work_accounting import CounterRegistry


# Bind the transition constant used by the implementation's replay validator.
_impl.NEXT_LOCAL_TRANSACTION_REQUIRED = NEXT_LOCAL_TRANSACTION_REQUIRED

ACCEPTANCE_STATUS = _impl.ACCEPTANCE_STATUS
EvidenceSemanticVerification = _impl.EvidenceSemanticVerification
GuardProfileCommitment = _impl.GuardProfileCommitment
Phase3EPredecisionAcceptanceError = _impl.Phase3EPredecisionAcceptanceError
Phase3EPredecisionOutcome = _impl.Phase3EPredecisionOutcome


def _validate_public_route_inputs(
    *,
    context: RouteDecisionContext,
    catalog: VerifiedRouteInputCatalog,
    cap_profile: RouteCapProfileCandidate,
    local_projection: ActualProjectionCandidate,
    fallback_projection: ActualProjectionCandidate,
) -> None:
    if cap_profile.context_id != context.context_id:
        raise Phase3EPredecisionAcceptanceError(
            "cap profile uses a different route context"
        )
    expected_routes = (
        (local_projection, LOCAL_ATTEMPT, "local"),
        (fallback_projection, DIRECT_FALLBACK, "fallback"),
    )
    required_axes = set(catalog.profile.axes)
    for projection, expected_route, label in expected_routes:
        if projection.route_candidate != expected_route:
            raise Phase3EPredecisionAcceptanceError(
                f"{label} projection has the wrong route candidate"
            )
        observed_axes = {term.axis for term in projection.terms}
        if observed_axes != required_axes:
            raise Phase3EPredecisionAcceptanceError(
                f"{label} projection does not cover exactly the shared axes"
            )


def accept_phase3e_predecision_mechanics(
    *,
    envelope: RouteTraceEnvelope,
    context: RouteDecisionContext,
    registry: CounterRegistry,
    catalog: VerifiedRouteInputCatalog,
    cap_profile: RouteCapProfileCandidate,
    decision_points: Sequence[DecisionPointBinding],
    local_projection: ActualProjectionCandidate,
    fallback_projection: ActualProjectionCandidate,
    guard_commitment: GuardProfileCommitment,
    semantic_results: Sequence[EvidenceSemanticVerification],
) -> Phase3EPredecisionOutcome:
    """Validate route-independent inputs before either replay branch executes."""

    _validate_public_route_inputs(
        context=context,
        catalog=catalog,
        cap_profile=cap_profile,
        local_projection=local_projection,
        fallback_projection=fallback_projection,
    )
    return _impl.accept_phase3e_predecision_mechanics(
        envelope=envelope,
        context=context,
        registry=registry,
        catalog=catalog,
        cap_profile=cap_profile,
        decision_points=decision_points,
        local_projection=local_projection,
        fallback_projection=fallback_projection,
        guard_commitment=guard_commitment,
        semantic_results=semantic_results,
    )


__all__ = [
    "ACCEPTANCE_STATUS",
    "EvidenceSemanticVerification",
    "GuardProfileCommitment",
    "Phase3EPredecisionAcceptanceError",
    "Phase3EPredecisionOutcome",
    "accept_phase3e_predecision_mechanics",
]
