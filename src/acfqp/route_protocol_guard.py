"""Transaction, cap, and actual-projection guard for Phase-3E route traces.

The guard is the acceptance boundary for the preconstruction router candidate.
It augments strict envelope replay with transaction/frontier/cap bindings,
derives budget state from a candidate cap profile, forbids local routing after a
negative causal result, and recomputes actual shared-axis work from the exact
event WorkVector.  All profiles remain explicitly non-official.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from acfqp.artifacts import object_id
from acfqp.auditable_router import (
    ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
    CAP_EXHAUSTED,
    CAUSAL_SEARCH,
    CERTIFIED_FEASIBLE,
    CERTIFIED_INFEASIBLE,
    FAILED_DEEPER_BUDGET_EXHAUSTED,
    FAILED_DEEPER_BUDGET_REMAINS,
    FALLBACK_RESULT,
    FOUND,
    FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
    INCOMPLETE_DUE_TO_CAP,
    INFEASIBLE_QUERY_ATTEMPT_TERMINAL,
    LOCAL_CAP_IMPOSSIBLE,
    LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL,
    LOCAL_RESULT,
    NEXT_LOCAL_TRANSACTION_REQUIRED,
    NO_SOUND_COVER,
    ROUTE_SELECTION,
    SELECT_FALLBACK_NO_LOCAL,
    SELECT_LOCAL,
    RouteDecisionContext,
    RouteTraceEnvelope,
)
from acfqp.phase3e_accounting import ECONOMICS_NOT_RUN, ROUTING_MECHANICS_ONLY
from acfqp.route_comparison import (
    DIRECT_FALLBACK,
    LOCAL_ATTEMPT,
    ComparisonProfileCandidate,
    ComparisonVector,
)
from acfqp.route_envelope_verifier import (
    RouteEnvelopeVerificationError,
    VerifiedRouteInputCatalog,
    replay_strict_route_envelope,
)
from acfqp.work_accounting import CounterRegistry, WorkVector


CAP_PROFILE_STATUS = "UNRESOLVED_ROUTE_CAP_PROFILE_CANDIDATE"
PROJECTION_STATUS = "UNRESOLVED_ACTUAL_COMPARISON_PROJECTION_CANDIDATE"

PLAN_CERTIFICATE_CANDIDATE = "PLAN_CERTIFICATE_CANDIDATE"
INFEASIBILITY_CERTIFICATE_CANDIDATE = "INFEASIBILITY_CERTIFICATE_CANDIDATE"
ATTEMPT_CLOSURE_NONCERTIFICATE = "ATTEMPT_CLOSURE_NONCERTIFICATE"

_NEGATIVE_CAUSAL = frozenset({CAP_EXHAUSTED, NO_SOUND_COVER, LOCAL_CAP_IMPOSSIBLE})


class RouteProtocolGuardError(RouteEnvelopeVerificationError):
    """A strict trace violates transaction, cap, or projection semantics."""


def _identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RouteProtocolGuardError(f"{field} must be nonempty")
    return value


def _integer(value: Any, *, field: str, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RouteProtocolGuardError(f"{field} must be an exact integer")
    if value < (1 if positive else 0):
        qualifier = "positive" if positive else "nonnegative"
        raise RouteProtocolGuardError(f"{field} must be {qualifier}")
    return value


@dataclass(frozen=True, slots=True)
class RouteCapProfileCandidate:
    context_id: str
    profile_key: str
    max_local_transactions: int
    official: bool = False

    def __post_init__(self) -> None:
        _identifier(self.context_id, field="cap-profile context_id")
        _identifier(self.profile_key, field="cap-profile key")
        _integer(
            self.max_local_transactions,
            field="max_local_transactions",
            positive=True,
        )
        if self.official:
            raise RouteProtocolGuardError("candidate cap profile cannot be official")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_cap_profile.phase3e_candidate.v1",
            "context_id": self.context_id,
            "profile_key": self.profile_key,
            "max_local_transactions": self.max_local_transactions,
            "status": CAP_PROFILE_STATUS,
            "official": False,
        }

    @property
    def profile_id(self) -> str:
        return object_id(self._payload(), "route-cap-profile")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "profile_id": self.profile_id}


@dataclass(frozen=True, slots=True)
class DecisionPointBinding:
    context_id: str
    transaction_id: str
    transaction_index: int
    frontier_snapshot_id: str
    causal_evidence_id: str
    causal_outcome: str
    local_bound_id: str | None
    fallback_bound_id: str
    local_cap_id: str | None
    fallback_cap_id: str

    def __post_init__(self) -> None:
        _identifier(self.context_id, field="decision context_id")
        _identifier(self.transaction_id, field="transaction_id")
        _integer(self.transaction_index, field="transaction_index", positive=True)
        _identifier(self.frontier_snapshot_id, field="frontier_snapshot_id")
        _identifier(self.causal_evidence_id, field="causal_evidence_id")
        if self.causal_outcome not in {FOUND, *_NEGATIVE_CAUSAL}:
            raise RouteProtocolGuardError("unknown causal outcome in decision binding")
        _identifier(self.fallback_bound_id, field="fallback_bound_id")
        _identifier(self.fallback_cap_id, field="fallback_cap_id")
        if self.causal_outcome == FOUND:
            _identifier(self.local_bound_id, field="local_bound_id")
            _identifier(self.local_cap_id, field="local_cap_id")
        elif self.local_bound_id is not None or self.local_cap_id is not None:
            raise RouteProtocolGuardError(
                "negative causal decision cannot carry local bound/cap"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_decision_point_binding.phase3e_candidate.v1",
            "context_id": self.context_id,
            "transaction_id": self.transaction_id,
            "transaction_index": self.transaction_index,
            "frontier_snapshot_id": self.frontier_snapshot_id,
            "causal_evidence_id": self.causal_evidence_id,
            "causal_outcome": self.causal_outcome,
            "local_bound_id": self.local_bound_id,
            "fallback_bound_id": self.fallback_bound_id,
            "local_cap_id": self.local_cap_id,
            "fallback_cap_id": self.fallback_cap_id,
            "official": False,
        }

    @property
    def binding_id(self) -> str:
        return object_id(self._payload(), "route-decision-point-binding")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class ProjectionTerm:
    axis: str
    work_path: str
    multiplier: int

    def __post_init__(self) -> None:
        _identifier(self.axis, field="projection axis")
        _identifier(self.work_path, field="projection work path")
        _integer(self.multiplier, field="projection multiplier")

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis": self.axis,
            "work_path": self.work_path,
            "multiplier": self.multiplier,
        }


@dataclass(frozen=True, slots=True)
class ActualProjectionCandidate:
    counter_registry_id: str
    comparison_profile_id: str
    route_candidate: str
    projection_key: str
    terms: tuple[ProjectionTerm, ...]
    official: bool = False

    def __post_init__(self) -> None:
        _identifier(self.counter_registry_id, field="counter_registry_id")
        _identifier(self.comparison_profile_id, field="comparison_profile_id")
        if self.route_candidate not in {LOCAL_ATTEMPT, DIRECT_FALLBACK}:
            raise RouteProtocolGuardError("unknown projection route candidate")
        _identifier(self.projection_key, field="projection_key")
        key = lambda term: (term.axis, term.work_path, term.multiplier)
        if not self.terms or tuple(sorted(self.terms, key=key)) != self.terms:
            raise RouteProtocolGuardError("projection terms must be nonempty and sorted")
        pairs = {(term.axis, term.work_path) for term in self.terms}
        if len(pairs) != len(self.terms):
            raise RouteProtocolGuardError("projection repeats an axis/work-path term")
        if self.official:
            raise RouteProtocolGuardError("candidate projection cannot be official")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_work_projection.phase3e_candidate.v1",
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "route_candidate": self.route_candidate,
            "projection_key": self.projection_key,
            "terms": [term.to_dict() for term in self.terms],
            "status": PROJECTION_STATUS,
            "official": False,
        }

    @property
    def projection_id(self) -> str:
        return object_id(self._payload(), "actual-work-projection")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "projection_id": self.projection_id}


def derive_actual_comparison(
    *,
    work: WorkVector,
    context_id: str,
    registry: CounterRegistry,
    profile: ComparisonProfileCandidate,
    projection: ActualProjectionCandidate,
) -> ComparisonVector:
    registry.validate_vector(work)
    if projection.counter_registry_id != registry.registry_id:
        raise RouteProtocolGuardError("actual projection uses a different registry")
    if projection.comparison_profile_id != profile.profile_id:
        raise RouteProtocolGuardError("actual projection uses a different profile")
    values = {axis: 0 for axis in profile.axes}
    work_values = dict(work.values)
    used_axes = set()
    for term in projection.terms:
        if term.axis not in values:
            raise RouteProtocolGuardError("actual projection names an unknown axis")
        if term.work_path not in work_values:
            raise RouteProtocolGuardError("actual projection names an unknown WorkVector leaf")
        values[term.axis] += work_values[term.work_path] * term.multiplier
        used_axes.add(term.axis)
    if used_axes != set(profile.axes):
        raise RouteProtocolGuardError("actual projection does not cover every shared axis")
    return ComparisonVector(
        profile.profile_id,
        context_id,
        projection.route_candidate,
        tuple(sorted(values.items())),
    )


def guard_route_protocol(
    *,
    envelope: RouteTraceEnvelope,
    context: RouteDecisionContext,
    registry: CounterRegistry,
    catalog: VerifiedRouteInputCatalog,
    cap_profile: RouteCapProfileCandidate,
    decision_points: Sequence[DecisionPointBinding],
    local_projection: ActualProjectionCandidate,
    fallback_projection: ActualProjectionCandidate,
) -> tuple[str, WorkVector]:
    """Verify transaction lifecycle after strict envelope replay."""

    state, accumulated = replay_strict_route_envelope(
        envelope=envelope,
        context=context,
        registry=registry,
        catalog=catalog,
    )
    if cap_profile.context_id != context.context_id:
        raise RouteProtocolGuardError("cap profile uses a different route context")
    if local_projection.route_candidate != LOCAL_ATTEMPT:
        raise RouteProtocolGuardError("local actual projection has the wrong route")
    if fallback_projection.route_candidate != DIRECT_FALLBACK:
        raise RouteProtocolGuardError("fallback actual projection has the wrong route")
    points_by_causal = {point.causal_evidence_id: point for point in decision_points}
    if len(points_by_causal) != len(decision_points):
        raise RouteProtocolGuardError("decision-point bindings repeat causal evidence")
    transaction_ids = {point.transaction_id for point in decision_points}
    if len(transaction_ids) != len(decision_points):
        raise RouteProtocolGuardError("decision-point bindings reuse a transaction ID")
    indices = sorted(point.transaction_index for point in decision_points)
    if indices != list(range(1, len(indices) + 1)):
        raise RouteProtocolGuardError("decision-point transaction indices are not contiguous")
    for point in decision_points:
        if point.context_id != context.context_id:
            raise RouteProtocolGuardError("decision point uses a different context")
        if point.transaction_index > cap_profile.max_local_transactions:
            raise RouteProtocolGuardError("decision point exceeds local transaction cap")

    active: DecisionPointBinding | None = None
    seen_causal: set[str] = set()
    for event in envelope.events:
        evidence = event.evidence
        refs = dict(evidence.artifact_refs)
        if evidence.role == CAUSAL_SEARCH:
            point = points_by_causal.get(evidence.evidence_id)
            if point is None:
                raise RouteProtocolGuardError("causal evidence lacks a decision-point binding")
            if evidence.evidence_id in seen_causal:
                raise RouteProtocolGuardError("causal evidence is replayed twice")
            seen_causal.add(evidence.evidence_id)
            if evidence.transaction_id != point.transaction_id:
                raise RouteProtocolGuardError("causal transaction ID differs from binding")
            if evidence.outcome != point.causal_outcome:
                raise RouteProtocolGuardError("causal outcome differs from binding")
            if refs.get("frontier_snapshot") != point.frontier_snapshot_id:
                raise RouteProtocolGuardError("causal frontier snapshot differs from binding")
            active = point
        elif evidence.role == ROUTE_SELECTION:
            if active is None:
                raise RouteProtocolGuardError("route selection has no active decision point")
            if evidence.transaction_id != active.transaction_id:
                raise RouteProtocolGuardError("selection transaction differs from decision point")
            if evidence.fallback_bound_id != active.fallback_bound_id:
                raise RouteProtocolGuardError("selection fallback bound is stale/misbound")
            if active.causal_outcome in _NEGATIVE_CAUSAL:
                if evidence.outcome != SELECT_FALLBACK_NO_LOCAL:
                    raise RouteProtocolGuardError("negative causal result selected local work")
                if evidence.local_bound_id is not None:
                    raise RouteProtocolGuardError("negative causal selection carries local bound")
            else:
                if evidence.local_bound_id != active.local_bound_id:
                    raise RouteProtocolGuardError("selection local bound is stale/misbound")
            if refs.get("fallback_cap_profile") != active.fallback_cap_id:
                raise RouteProtocolGuardError("selection fallback cap differs from binding")
            if active.local_cap_id is not None and refs.get("local_cap_profile") != active.local_cap_id:
                raise RouteProtocolGuardError("selection local cap differs from binding")
        elif evidence.role == LOCAL_RESULT:
            if active is None or evidence.transaction_id != active.transaction_id:
                raise RouteProtocolGuardError("local result has no matching decision point")
            if active.causal_outcome != FOUND:
                raise RouteProtocolGuardError("local result follows a negative causal outcome")
            if refs.get("local_cap_profile") != active.local_cap_id:
                raise RouteProtocolGuardError("local result uses a different cap")
            recomputed = derive_actual_comparison(
                work=evidence.work_delta,
                context_id=context.context_id,
                registry=registry,
                profile=catalog.profile,
                projection=local_projection,
            )
            if evidence.actual_comparison != recomputed:
                raise RouteProtocolGuardError("local actual comparison does not recompute")
            if evidence.outcome == FAILED_DEEPER_BUDGET_REMAINS:
                if active.transaction_index >= cap_profile.max_local_transactions:
                    raise RouteProtocolGuardError("worker claims budget remains at the cap")
                active = None
            elif evidence.outcome == FAILED_DEEPER_BUDGET_EXHAUSTED:
                if active.transaction_index < cap_profile.max_local_transactions:
                    raise RouteProtocolGuardError("worker claims budget exhausted before the cap")
        elif evidence.role == FALLBACK_RESULT:
            if active is None or evidence.transaction_id != active.transaction_id:
                raise RouteProtocolGuardError("fallback result has no matching decision point")
            if refs.get("fallback_cap_profile") != active.fallback_cap_id:
                raise RouteProtocolGuardError("fallback result uses a different cap")
            recomputed = derive_actual_comparison(
                work=evidence.work_delta,
                context_id=context.context_id,
                registry=registry,
                profile=catalog.profile,
                projection=fallback_projection,
            )
            if evidence.actual_comparison != recomputed:
                raise RouteProtocolGuardError("fallback actual comparison does not recompute")
            active = None
    if seen_causal != set(points_by_causal):
        raise RouteProtocolGuardError("unused or missing decision-point binding")
    return state, accumulated


@dataclass(frozen=True, slots=True)
class GuardedRouteOutcomeCandidate:
    context_id: str
    envelope_id: str
    catalog_id: str
    cap_profile_id: str
    decision_binding_ids: tuple[str, ...]
    local_projection_id: str
    fallback_projection_id: str
    final_state: str
    accumulated_work_vector_id: str
    outcome_kind: str
    official: bool = False

    def __post_init__(self) -> None:
        for field in (
            "context_id",
            "envelope_id",
            "catalog_id",
            "cap_profile_id",
            "local_projection_id",
            "fallback_projection_id",
            "final_state",
            "accumulated_work_vector_id",
        ):
            _identifier(getattr(self, field), field=field)
        if not self.decision_binding_ids or tuple(sorted(self.decision_binding_ids)) != self.decision_binding_ids:
            raise RouteProtocolGuardError("decision binding IDs must be nonempty and sorted")
        if self.outcome_kind not in {
            PLAN_CERTIFICATE_CANDIDATE,
            INFEASIBILITY_CERTIFICATE_CANDIDATE,
            ATTEMPT_CLOSURE_NONCERTIFICATE,
        }:
            raise RouteProtocolGuardError("unknown guarded outcome kind")
        if self.official:
            raise RouteProtocolGuardError("guarded preconstruction outcome cannot be official")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.guarded_route_outcome.phase3e_candidate.v1",
            "context_id": self.context_id,
            "envelope_id": self.envelope_id,
            "catalog_id": self.catalog_id,
            "cap_profile_id": self.cap_profile_id,
            "decision_binding_ids": list(self.decision_binding_ids),
            "local_projection_id": self.local_projection_id,
            "fallback_projection_id": self.fallback_projection_id,
            "final_state": self.final_state,
            "accumulated_work_vector_id": self.accumulated_work_vector_id,
            "outcome_kind": self.outcome_kind,
            "official": False,
            "routing_protocol_status": ROUTING_MECHANICS_ONLY,
            "economics_gate_status": ECONOMICS_NOT_RUN,
        }

    @property
    def outcome_id(self) -> str:
        return object_id(self._payload(), "guarded-route-outcome")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "outcome_id": self.outcome_id}


def certify_guarded_route_candidate(
    *,
    envelope: RouteTraceEnvelope,
    context: RouteDecisionContext,
    registry: CounterRegistry,
    catalog: VerifiedRouteInputCatalog,
    cap_profile: RouteCapProfileCandidate,
    decision_points: Sequence[DecisionPointBinding],
    local_projection: ActualProjectionCandidate,
    fallback_projection: ActualProjectionCandidate,
) -> GuardedRouteOutcomeCandidate:
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
    if state in {
        ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
        LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL,
        FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
    }:
        kind = PLAN_CERTIFICATE_CANDIDATE
    elif state == INFEASIBLE_QUERY_ATTEMPT_TERMINAL:
        kind = INFEASIBILITY_CERTIFICATE_CANDIDATE
    else:
        kind = ATTEMPT_CLOSURE_NONCERTIFICATE
    return GuardedRouteOutcomeCandidate(
        context.context_id,
        envelope.envelope_id,
        catalog.catalog_id,
        cap_profile.profile_id,
        tuple(sorted(point.binding_id for point in decision_points)),
        local_projection.projection_id,
        fallback_projection.projection_id,
        state,
        accumulated.vector_id,
        kind,
    )


__all__ = [
    "ATTEMPT_CLOSURE_NONCERTIFICATE",
    "ActualProjectionCandidate",
    "CAP_PROFILE_STATUS",
    "DecisionPointBinding",
    "GuardedRouteOutcomeCandidate",
    "INFEASIBILITY_CERTIFICATE_CANDIDATE",
    "PLAN_CERTIFICATE_CANDIDATE",
    "PROJECTION_STATUS",
    "ProjectionTerm",
    "RouteCapProfileCandidate",
    "RouteProtocolGuardError",
    "certify_guarded_route_candidate",
    "derive_actual_comparison",
    "guard_route_protocol",
]
