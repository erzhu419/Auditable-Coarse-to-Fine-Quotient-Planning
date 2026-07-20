"""Final non-official acceptance guard for Phase-3E predecision mechanics.

The acceptance guard commits cap/projection/verifier profiles before routing,
binds every later selection/result to its decision point, derives transaction
ordering from the event sequence, and permits zero decision points for abstract,
cached-infeasible, rebuild, and protocol-failure attempts.  It emits only a
preconstruction candidate outcome; no official economics or routing Gate is run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from acfqp.artifacts import object_id
from acfqp.auditable_router import (
    ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
    CAUSAL_SEARCH,
    FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL,
    FALLBACK_RESULT,
    FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
    INFEASIBLE_QUERY_ATTEMPT_TERMINAL,
    INTEGRITY,
    LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL,
    LOCAL_RESULT,
    PROTOCOL_FAILURE_ATTEMPT_TERMINAL,
    REBUILD_REQUIRED_ATTEMPT_TERMINAL,
    ROUTE_SELECTION,
    RouteDecisionContext,
    RouteTraceEnvelope,
)
from acfqp.phase3e_accounting import (
    COUNTER_COMPLETENESS_NOT_RUN,
    ECONOMICS_NOT_RUN,
    ROUTING_MECHANICS_ONLY,
)
from acfqp.route_envelope_verifier import (
    RouteEnvelopeVerificationError,
    VerifiedRouteInputCatalog,
    replay_strict_route_envelope,
)
from acfqp.route_protocol_guard import (
    ATTEMPT_CLOSURE_NONCERTIFICATE,
    INFEASIBILITY_CERTIFICATE_CANDIDATE,
    PLAN_CERTIFICATE_CANDIDATE,
    ActualProjectionCandidate,
    DecisionPointBinding,
    RouteCapProfileCandidate,
    RouteProtocolGuardError,
    guard_route_protocol,
)
from acfqp.work_accounting import CounterRegistry, WorkVector


ACCEPTANCE_STATUS = "PHASE3E_PRECONSTRUCTION_MECHANICS_PASS"

_EVIDENCE_ROLES = frozenset(
    {
        "INTEGRITY",
        "COMPATIBILITY",
        "CACHE_PROOF",
        "ABSTRACT_AUDIT",
        "CAUSAL_SEARCH",
        "ROUTE_SELECTION",
        "LOCAL_RESULT",
        "FALLBACK_RESULT",
    }
)
_PLAN_STATES = frozenset(
    {
        ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
        LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL,
        FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
    }
)
_NONCERTIFICATE_STATES = frozenset(
    {
        PROTOCOL_FAILURE_ATTEMPT_TERMINAL,
        REBUILD_REQUIRED_ATTEMPT_TERMINAL,
        FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL,
    }
)


class Phase3EPredecisionAcceptanceError(RouteProtocolGuardError):
    """The candidate mechanics do not satisfy the predecision acceptance guard."""


def _identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise Phase3EPredecisionAcceptanceError(f"{field} must be nonempty")
    return value


@dataclass(frozen=True, slots=True)
class GuardProfileCommitment:
    context_id: str
    preregistration_skeleton_id: str
    counter_registry_id: str
    comparison_profile_id: str
    cap_profile_id: str
    local_projection_id: str
    fallback_projection_id: str
    semantic_verifier_profiles: tuple[tuple[str, str], ...]
    official: bool = False

    def __post_init__(self) -> None:
        for field in (
            "context_id",
            "preregistration_skeleton_id",
            "counter_registry_id",
            "comparison_profile_id",
            "cap_profile_id",
            "local_projection_id",
            "fallback_projection_id",
        ):
            _identifier(getattr(self, field), field=field)
        if tuple(sorted(self.semantic_verifier_profiles)) != self.semantic_verifier_profiles:
            raise Phase3EPredecisionAcceptanceError(
                "semantic verifier profiles must be sorted"
            )
        profiles = dict(self.semantic_verifier_profiles)
        if len(profiles) != len(self.semantic_verifier_profiles):
            raise Phase3EPredecisionAcceptanceError(
                "semantic verifier profile repeats an evidence role"
            )
        if set(profiles) != set(_EVIDENCE_ROLES):
            raise Phase3EPredecisionAcceptanceError(
                "semantic verifier profiles do not cover every evidence role"
            )
        for role, profile_id in self.semantic_verifier_profiles:
            _identifier(role, field="semantic verifier role")
            _identifier(profile_id, field="semantic verifier profile ID")
        if self.official:
            raise Phase3EPredecisionAcceptanceError(
                "predecision guard commitment cannot be official"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.guard_profile_commitment.phase3e_candidate.v1",
            "context_id": self.context_id,
            "preregistration_skeleton_id": self.preregistration_skeleton_id,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "cap_profile_id": self.cap_profile_id,
            "local_projection_id": self.local_projection_id,
            "fallback_projection_id": self.fallback_projection_id,
            "semantic_verifier_profiles": [
                {"role": role, "profile_id": profile_id}
                for role, profile_id in self.semantic_verifier_profiles
            ],
            "official": False,
        }

    @property
    def commitment_id(self) -> str:
        return object_id(self._payload(), "guard-profile-commitment")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "commitment_id": self.commitment_id}


@dataclass(frozen=True, slots=True)
class EvidenceSemanticVerification:
    context_id: str
    evidence_id: str
    evidence_role: str
    verified_outcome: str
    verifier_profile_id: str
    source_artifact_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in (
            "context_id",
            "evidence_id",
            "evidence_role",
            "verified_outcome",
            "verifier_profile_id",
        ):
            _identifier(getattr(self, field), field=field)
        if self.evidence_role not in _EVIDENCE_ROLES:
            raise Phase3EPredecisionAcceptanceError(
                "semantic verification uses an unknown evidence role"
            )
        if (
            not self.source_artifact_ids
            or tuple(sorted(self.source_artifact_ids)) != self.source_artifact_ids
            or len(set(self.source_artifact_ids)) != len(self.source_artifact_ids)
        ):
            raise Phase3EPredecisionAcceptanceError(
                "semantic verification source IDs must be nonempty, unique, and sorted"
            )
        for artifact_id in self.source_artifact_ids:
            _identifier(artifact_id, field="semantic verification source artifact")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.evidence_semantic_verification.phase3e_candidate.v1",
            "context_id": self.context_id,
            "evidence_id": self.evidence_id,
            "evidence_role": self.evidence_role,
            "verified_outcome": self.verified_outcome,
            "verifier_profile_id": self.verifier_profile_id,
            "source_artifact_ids": list(self.source_artifact_ids),
            "official": False,
        }

    @property
    def verification_id(self) -> str:
        return object_id(self._payload(), "evidence-semantic-verification")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "verification_id": self.verification_id}


def _validate_projection_coverage(
    *,
    projection: ActualProjectionCandidate,
    registry: CounterRegistry,
    profile_id: str,
) -> None:
    if projection.counter_registry_id != registry.registry_id:
        raise Phase3EPredecisionAcceptanceError(
            "actual projection uses a different counter registry"
        )
    if projection.comparison_profile_id != profile_id:
        raise Phase3EPredecisionAcceptanceError(
            "actual projection uses a different comparison profile"
        )
    paths = [term.work_path for term in projection.terms]
    if any(term.multiplier <= 0 for term in projection.terms):
        raise Phase3EPredecisionAcceptanceError(
            "actual projection multiplier must be strictly positive"
        )
    if len(paths) != len(set(paths)):
        raise Phase3EPredecisionAcceptanceError(
            "actual projection maps a charged leaf more than once"
        )
    expected = set(registry.operational_cost_paths)
    observed = set(paths)
    if observed != expected:
        raise Phase3EPredecisionAcceptanceError(
            "actual projection must cover every operational charged leaf exactly once; "
            f"missing={sorted(expected - observed)!r}, "
            f"extra={sorted(observed - expected)!r}"
        )


def _validate_commitment(
    *,
    commitment: GuardProfileCommitment,
    context: RouteDecisionContext,
    registry: CounterRegistry,
    catalog: VerifiedRouteInputCatalog,
    cap_profile: RouteCapProfileCandidate,
    local_projection: ActualProjectionCandidate,
    fallback_projection: ActualProjectionCandidate,
) -> None:
    expected = {
        "context_id": context.context_id,
        "preregistration_skeleton_id": context.preregistration_skeleton_id,
        "counter_registry_id": registry.registry_id,
        "comparison_profile_id": catalog.profile.profile_id,
        "cap_profile_id": cap_profile.profile_id,
        "local_projection_id": local_projection.projection_id,
        "fallback_projection_id": fallback_projection.projection_id,
    }
    for field, value in expected.items():
        if getattr(commitment, field) != value:
            raise Phase3EPredecisionAcceptanceError(
                f"guard commitment field differs from execution input: {field}"
            )
    _validate_projection_coverage(
        projection=local_projection,
        registry=registry,
        profile_id=catalog.profile.profile_id,
    )
    _validate_projection_coverage(
        projection=fallback_projection,
        registry=registry,
        profile_id=catalog.profile.profile_id,
    )


def _validate_semantic_results(
    *,
    envelope: RouteTraceEnvelope,
    commitment: GuardProfileCommitment,
    results: Sequence[EvidenceSemanticVerification],
) -> None:
    by_evidence = {result.evidence_id: result for result in results}
    if len(by_evidence) != len(results):
        raise Phase3EPredecisionAcceptanceError(
            "semantic results repeat an evidence ID"
        )
    expected_profiles = dict(commitment.semantic_verifier_profiles)
    if set(by_evidence) != {event.evidence.evidence_id for event in envelope.events}:
        raise Phase3EPredecisionAcceptanceError(
            "semantic results do not cover every route event exactly once"
        )
    for event in envelope.events:
        evidence = event.evidence
        result = by_evidence[evidence.evidence_id]
        source_ids = tuple(sorted(artifact_id for _, artifact_id in evidence.artifact_refs))
        if (
            result.context_id != evidence.context_id
            or result.evidence_role != evidence.role
            or result.verified_outcome != evidence.outcome
            or result.verifier_profile_id != expected_profiles[evidence.role]
            or result.source_artifact_ids != source_ids
        ):
            raise Phase3EPredecisionAcceptanceError(
                "semantic verifier result disagrees with transition evidence"
            )


def _validate_decision_order_and_refs(
    *, envelope: RouteTraceEnvelope, decision_points: Sequence[DecisionPointBinding]
) -> None:
    points = {point.causal_evidence_id: point for point in decision_points}
    if len(points) != len(decision_points):
        raise Phase3EPredecisionAcceptanceError(
            "decision bindings repeat causal evidence"
        )
    ordered_causal = [
        event.evidence
        for event in envelope.events
        if event.evidence.role == CAUSAL_SEARCH
    ]
    if len(ordered_causal) != len(decision_points):
        raise Phase3EPredecisionAcceptanceError(
            "decision bindings do not match causal event count"
        )
    active: DecisionPointBinding | None = None
    for index, evidence in enumerate(ordered_causal, start=1):
        point = points.get(evidence.evidence_id)
        if point is None or point.transaction_index != index:
            raise Phase3EPredecisionAcceptanceError(
                "transaction index differs from causal event order"
            )
    for event in envelope.events:
        evidence = event.evidence
        refs = dict(evidence.artifact_refs)
        if evidence.role == CAUSAL_SEARCH:
            active = points[evidence.evidence_id]
        elif evidence.role in {ROUTE_SELECTION, LOCAL_RESULT, FALLBACK_RESULT}:
            if active is None:
                raise Phase3EPredecisionAcceptanceError(
                    "decision-dependent event has no active causal binding"
                )
            if refs.get("decision_point_binding") != active.binding_id:
                raise Phase3EPredecisionAcceptanceError(
                    "event does not commit its active decision-point binding"
                )
            if evidence.transaction_id != active.transaction_id:
                raise Phase3EPredecisionAcceptanceError(
                    "event transaction differs from decision-point binding"
                )
            if evidence.role == LOCAL_RESULT and event.state_after == NEXT_LOCAL_TRANSACTION_REQUIRED:
                active = None


@dataclass(frozen=True, slots=True)
class Phase3EPredecisionOutcome:
    context_id: str
    envelope_id: str
    catalog_id: str
    guard_commitment_id: str
    semantic_verification_ids: tuple[str, ...]
    decision_binding_ids: tuple[str, ...]
    final_state: str
    accumulated_work_vector_id: str
    outcome_kind: str
    status: str = ACCEPTANCE_STATUS
    official: bool = False

    def __post_init__(self) -> None:
        for field in (
            "context_id",
            "envelope_id",
            "catalog_id",
            "guard_commitment_id",
            "final_state",
            "accumulated_work_vector_id",
            "outcome_kind",
        ):
            _identifier(getattr(self, field), field=field)
        if tuple(sorted(self.semantic_verification_ids)) != self.semantic_verification_ids:
            raise Phase3EPredecisionAcceptanceError(
                "semantic verification IDs must be sorted"
            )
        if tuple(sorted(self.decision_binding_ids)) != self.decision_binding_ids:
            raise Phase3EPredecisionAcceptanceError(
                "decision binding IDs must be sorted"
            )
        if self.status != ACCEPTANCE_STATUS:
            raise Phase3EPredecisionAcceptanceError("predecision status mismatch")
        if self.official:
            raise Phase3EPredecisionAcceptanceError(
                "predecision outcome cannot claim official status"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_predecision_outcome.v1",
            "context_id": self.context_id,
            "envelope_id": self.envelope_id,
            "catalog_id": self.catalog_id,
            "guard_commitment_id": self.guard_commitment_id,
            "semantic_verification_ids": list(self.semantic_verification_ids),
            "decision_binding_ids": list(self.decision_binding_ids),
            "final_state": self.final_state,
            "accumulated_work_vector_id": self.accumulated_work_vector_id,
            "outcome_kind": self.outcome_kind,
            "status": ACCEPTANCE_STATUS,
            "official": False,
            "routing_protocol_status": ROUTING_MECHANICS_ONLY,
            "economics_gate_status": ECONOMICS_NOT_RUN,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_NOT_RUN,
            "official_scalar_cost": None,
            "official_n_break_even": None,
        }

    @property
    def outcome_id(self) -> str:
        return object_id(self._payload(), "phase3e-predecision-outcome")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "outcome_id": self.outcome_id}


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
    """Return a non-official outcome only after every predecision guard passes."""

    _validate_commitment(
        commitment=guard_commitment,
        context=context,
        registry=registry,
        catalog=catalog,
        cap_profile=cap_profile,
        local_projection=local_projection,
        fallback_projection=fallback_projection,
    )
    first = envelope.events[0] if envelope.events else None
    if first is None or first.evidence.role != INTEGRITY:
        raise Phase3EPredecisionAcceptanceError(
            "guard commitment requires an initial integrity event"
        )
    if dict(first.evidence.artifact_refs).get("guard_profile_commitment") != guard_commitment.commitment_id:
        raise Phase3EPredecisionAcceptanceError(
            "initial integrity event does not commit the guard profile"
        )
    _validate_semantic_results(
        envelope=envelope,
        commitment=guard_commitment,
        results=semantic_results,
    )
    _validate_decision_order_and_refs(
        envelope=envelope,
        decision_points=decision_points,
    )

    has_causal = any(
        event.evidence.role == CAUSAL_SEARCH for event in envelope.events
    )
    if has_causal:
        state, accumulated = guard_route_protocol(
            envelope=envelope,
            context=context,
            registry=registry,
            catalog=catalog,
            cap_profile=cap_profile,
            decision_points=decision_points,
            local_projection=local_projection,
            fallback_projection=fallback_projection,
        )
    else:
        if decision_points:
            raise Phase3EPredecisionAcceptanceError(
                "non-recovery route carries decision-point bindings"
            )
        try:
            state, accumulated = replay_strict_route_envelope(
                envelope=envelope,
                context=context,
                registry=registry,
                catalog=catalog,
            )
        except RouteEnvelopeVerificationError as error:
            raise Phase3EPredecisionAcceptanceError(str(error)) from error

    if state in _PLAN_STATES:
        outcome_kind = PLAN_CERTIFICATE_CANDIDATE
    elif state == INFEASIBLE_QUERY_ATTEMPT_TERMINAL:
        outcome_kind = INFEASIBILITY_CERTIFICATE_CANDIDATE
    elif state in _NONCERTIFICATE_STATES:
        outcome_kind = ATTEMPT_CLOSURE_NONCERTIFICATE
    else:
        raise Phase3EPredecisionAcceptanceError(
            f"unclassified terminal state {state!r}"
        )
    return Phase3EPredecisionOutcome(
        context.context_id,
        envelope.envelope_id,
        catalog.catalog_id,
        guard_commitment.commitment_id,
        tuple(sorted(result.verification_id for result in semantic_results)),
        tuple(sorted(point.binding_id for point in decision_points)),
        state,
        accumulated.vector_id,
        outcome_kind,
    )


__all__ = [
    "ACCEPTANCE_STATUS",
    "EvidenceSemanticVerification",
    "GuardProfileCommitment",
    "Phase3EPredecisionAcceptanceError",
    "Phase3EPredecisionOutcome",
    "accept_phase3e_predecision_mechanics",
]
