"""Strict verifier for Phase-3E auditable route envelopes.

This layer closes the intentionally loose mechanics beneath it: verified
artifacts are role/context-bound attestations, every route upper bound is
recomputed from its profile/cardinality/formula chain, actual accounting and
comparison vectors are content-bound, local failure retains the already-frozen
fallback upper bound, and only a complete terminal envelope can receive a
candidate certificate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from acfqp.artifacts import object_id
from acfqp.auditable_router import (
    ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
    FALLBACK_EXECUTION_REQUIRED,
    FALLBACK_RESULT,
    INFEASIBLE_QUERY_ATTEMPT_TERMINAL,
    LOCAL_RESULT,
    NEXT_LOCAL_TRANSACTION_REQUIRED,
    ROUTE_SELECTION,
    SELECT_LOCAL,
    AuditableRouterError,
    RouteDecisionContext,
    RouteTraceEnvelope,
    RouteTraceEvent,
    _actual_within_bound,
    _next_state,
)
from acfqp.phase3e_accounting import ECONOMICS_NOT_RUN, ROUTING_MECHANICS_ONLY
from acfqp.route_comparison import (
    DIRECT_FALLBACK,
    LOCAL_ATTEMPT,
    CardinalityEvidence,
    ComparisonFormulaCandidate,
    ComparisonProfileCandidate,
    RouteUpperBoundCandidate,
    compare_route_upper_bounds,
    verify_route_upper_bound,
)
from acfqp.work_accounting import (
    EQUAL,
    INCOMPARABLE,
    LEFT_DOMINATES,
    RIGHT_DOMINATES,
    CounterRegistry,
    CounterValidationError,
    WorkVector,
    sum_work_vectors,
)


_TERMINAL_STATES = frozenset(
    {
        "PROTOCOL_FAILURE_ATTEMPT_TERMINAL",
        "REBUILD_REQUIRED_ATTEMPT_TERMINAL",
        ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
        "LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL",
        "FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL",
        INFEASIBLE_QUERY_ATTEMPT_TERMINAL,
        "FALLBACK_CAP_EXHAUSTED_NO_CERTIFICATE_ATTEMPT_TERMINAL",
    }
)
_DERIVED_ROLES = frozenset(
    {
        "comparison_profile",
        "local_upper_bound",
        "fallback_upper_bound",
        "actual_work",
        "actual_comparison",
    }
)


class RouteEnvelopeVerificationError(AuditableRouterError):
    """A complete candidate route envelope cannot be independently replayed."""


def _identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RouteEnvelopeVerificationError(f"{field} must be nonempty")
    return value


@dataclass(frozen=True, slots=True)
class ArtifactVerificationAttestation:
    artifact_id: str
    role: str
    context_id: str
    verification_id: str

    def __post_init__(self) -> None:
        _identifier(self.artifact_id, field="artifact_id")
        _identifier(self.role, field="artifact role")
        _identifier(self.context_id, field="artifact context_id")
        _identifier(self.verification_id, field="artifact verification_id")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.artifact_verification_attestation.phase3e_candidate.v1",
            "artifact_id": self.artifact_id,
            "role": self.role,
            "context_id": self.context_id,
            "verification_id": self.verification_id,
            "official": False,
        }

    @property
    def attestation_id(self) -> str:
        return object_id(self._payload(), "artifact-verification-attestation")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "attestation_id": self.attestation_id}


@dataclass(frozen=True, slots=True)
class VerifiedRouteInputCatalog:
    context_id: str
    profile: ComparisonProfileCandidate
    cardinalities: tuple[CardinalityEvidence, ...]
    formulas: tuple[ComparisonFormulaCandidate, ...]
    bounds: tuple[RouteUpperBoundCandidate, ...]
    artifact_attestations: tuple[ArtifactVerificationAttestation, ...]

    def __post_init__(self) -> None:
        _identifier(self.context_id, field="catalog context_id")
        if not self.cardinalities or not self.formulas or not self.bounds:
            raise RouteEnvelopeVerificationError(
                "route input catalog must contain derivation inputs and bounds"
            )
        cardinalities = {row.evidence_id: row for row in self.cardinalities}
        formulas = {row.formula_id: row for row in self.formulas}
        bounds = {row.bound_id: row for row in self.bounds}
        attestations = {row.artifact_id: row for row in self.artifact_attestations}
        if len(cardinalities) != len(self.cardinalities):
            raise RouteEnvelopeVerificationError("catalog repeats cardinality evidence")
        if len(formulas) != len(self.formulas):
            raise RouteEnvelopeVerificationError("catalog repeats a formula")
        if len(bounds) != len(self.bounds):
            raise RouteEnvelopeVerificationError("catalog repeats a bound")
        if len(attestations) != len(self.artifact_attestations):
            raise RouteEnvelopeVerificationError("catalog repeats an artifact ID")
        for row in self.cardinalities:
            if row.context_id != self.context_id:
                raise RouteEnvelopeVerificationError(
                    "cardinality evidence uses a different context"
                )
            missing_sources = set(row.source_artifact_ids) - set(attestations)
            if missing_sources:
                raise RouteEnvelopeVerificationError(
                    f"cardinality sources lack attestations: {sorted(missing_sources)!r}"
                )
        for attestation in self.artifact_attestations:
            if attestation.context_id != self.context_id:
                raise RouteEnvelopeVerificationError(
                    "artifact attestation uses a different context"
                )
        for bound in self.bounds:
            cardinality = cardinalities.get(bound.cardinality_evidence_id)
            formula = formulas.get(bound.formula_id)
            if cardinality is None or formula is None:
                raise RouteEnvelopeVerificationError(
                    "bound derivation input is absent from the catalog"
                )
            try:
                verify_route_upper_bound(bound, self.profile, cardinality, formula)
            except ValueError as error:
                raise RouteEnvelopeVerificationError(str(error)) from error

    @property
    def bound_map(self) -> dict[str, RouteUpperBoundCandidate]:
        return {bound.bound_id: bound for bound in self.bounds}

    @property
    def attestation_map(self) -> dict[str, ArtifactVerificationAttestation]:
        return {
            attestation.artifact_id: attestation
            for attestation in self.artifact_attestations
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verified_route_input_catalog.phase3e_candidate.v1",
            "context_id": self.context_id,
            "profile": self.profile.to_dict(),
            "cardinality_evidence_ids": sorted(
                row.evidence_id for row in self.cardinalities
            ),
            "formula_ids": sorted(row.formula_id for row in self.formulas),
            "bound_ids": sorted(row.bound_id for row in self.bounds),
            "artifact_attestation_ids": sorted(
                row.attestation_id for row in self.artifact_attestations
            ),
            "official": False,
        }

    @property
    def catalog_id(self) -> str:
        return object_id(self._payload(), "verified-route-input-catalog")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "catalog_id": self.catalog_id}


def _validate_artifact_refs(
    *,
    event: RouteTraceEvent,
    context: RouteDecisionContext,
    catalog: VerifiedRouteInputCatalog,
) -> None:
    refs = dict(event.evidence.artifact_refs)
    attestations = catalog.attestation_map
    for role, artifact_id in event.evidence.artifact_refs:
        if role in _DERIVED_ROLES:
            continue
        attestation = attestations.get(artifact_id)
        if (
            attestation is None
            or attestation.role != role
            or attestation.context_id != context.context_id
        ):
            raise RouteEnvelopeVerificationError(
                f"artifact reference lacks matching role/context attestation: {role}"
            )
    if "threshold_profile" in refs and refs["threshold_profile"] != context.threshold_profile_id:
        raise RouteEnvelopeVerificationError("threshold artifact differs from route context")
    if event.evidence.role == ROUTE_SELECTION:
        if refs.get("comparison_profile") != context.comparison_profile_candidate_id:
            raise RouteEnvelopeVerificationError(
                "selection profile artifact differs from route context"
            )
        if refs.get("fallback_upper_bound") != event.evidence.fallback_bound_id:
            raise RouteEnvelopeVerificationError("fallback-bound artifact reference mismatch")
        if event.evidence.local_bound_id is None:
            if "local_upper_bound" in refs:
                raise RouteEnvelopeVerificationError("no-local selection references a local bound")
        elif refs.get("local_upper_bound") != event.evidence.local_bound_id:
            raise RouteEnvelopeVerificationError("local-bound artifact reference mismatch")
    if event.evidence.role in {LOCAL_RESULT, FALLBACK_RESULT}:
        assert event.evidence.actual_comparison is not None
        if refs.get("actual_work") != event.evidence.work_delta.vector_id:
            raise RouteEnvelopeVerificationError("actual WorkVector artifact ID mismatch")
        if refs.get("actual_comparison") != event.evidence.actual_comparison.vector_id:
            raise RouteEnvelopeVerificationError(
                "actual comparison-vector artifact ID mismatch"
            )


def _validate_selection(
    event: RouteTraceEvent,
    context: RouteDecisionContext,
    catalog: VerifiedRouteInputCatalog,
) -> tuple[RouteUpperBoundCandidate | None, RouteUpperBoundCandidate]:
    bounds = catalog.bound_map
    fallback = bounds.get(event.evidence.fallback_bound_id or "")
    if (
        fallback is None
        or fallback.context_id != context.context_id
        or fallback.profile_id != context.comparison_profile_candidate_id
        or fallback.route_candidate != DIRECT_FALLBACK
    ):
        raise RouteEnvelopeVerificationError("verified fallback bound is absent or misbound")
    if event.evidence.local_bound_id is None:
        if event.evidence.outcome != "SELECT_FALLBACK_NO_LOCAL":
            raise RouteEnvelopeVerificationError("selection omits a required local bound")
        return None, fallback
    local = bounds.get(event.evidence.local_bound_id)
    if (
        local is None
        or local.context_id != context.context_id
        or local.profile_id != context.comparison_profile_candidate_id
        or local.route_candidate != LOCAL_ATTEMPT
    ):
        raise RouteEnvelopeVerificationError("verified local bound is absent or misbound")
    relation = compare_route_upper_bounds(local, fallback)
    expected = {
        LEFT_DOMINATES: SELECT_LOCAL,
        RIGHT_DOMINATES: "SELECT_FALLBACK_DOMINATES",
        EQUAL: "SELECT_FALLBACK_EQUAL",
        INCOMPARABLE: "SELECT_FALLBACK_INCOMPARABLE",
    }[relation]
    if event.evidence.outcome != expected:
        raise RouteEnvelopeVerificationError(
            "selection outcome disagrees with recomputed upper bounds"
        )
    return local, fallback


def replay_strict_route_envelope(
    *,
    envelope: RouteTraceEnvelope,
    context: RouteDecisionContext,
    registry: CounterRegistry,
    catalog: VerifiedRouteInputCatalog,
) -> tuple[str, WorkVector]:
    """Replay a complete route with exact derivation and evidence binding."""

    if envelope.complete is not True:
        raise RouteEnvelopeVerificationError(
            "incomplete route prefix cannot be a route certificate"
        )
    if envelope.context_id != context.context_id or catalog.context_id != context.context_id:
        raise RouteEnvelopeVerificationError("envelope/catalog/context identity mismatch")
    if context.counter_registry_id != registry.registry_id:
        raise RouteEnvelopeVerificationError("counter registry differs from route context")
    if catalog.profile.profile_id != context.comparison_profile_candidate_id:
        raise RouteEnvelopeVerificationError("comparison profile differs from route context")
    if not envelope.events:
        raise RouteEnvelopeVerificationError("route envelope has no events")

    state = "START"
    selected_bound: RouteUpperBoundCandidate | None = None
    frozen_fallback_bound: RouteUpperBoundCandidate | None = None
    for index, event in enumerate(envelope.events):
        if event.context_id != context.context_id:
            raise RouteEnvelopeVerificationError("event uses a different route context")
        if event.sequence != index:
            raise RouteEnvelopeVerificationError("event sequence is not contiguous")
        expected_prev = envelope.events[index - 1].event_id if index else None
        if event.prev_event_id != expected_prev:
            raise RouteEnvelopeVerificationError("event hash chain is broken")
        if event.state_before != state:
            raise RouteEnvelopeVerificationError("event state_before differs from replay")
        if state in _TERMINAL_STATES:
            raise RouteEnvelopeVerificationError("event appears after terminal state")
        if event.evidence.context_id != context.context_id:
            raise RouteEnvelopeVerificationError("transition evidence context mismatch")
        try:
            registry.validate_vector(event.evidence.work_delta)
        except CounterValidationError as error:
            raise RouteEnvelopeVerificationError(str(error)) from error
        _validate_artifact_refs(event=event, context=context, catalog=catalog)

        if event.evidence.role == ROUTE_SELECTION:
            local, fallback = _validate_selection(event, context, catalog)
            frozen_fallback_bound = fallback
            selected_bound = local if event.evidence.outcome == SELECT_LOCAL else fallback
        elif event.evidence.role in {LOCAL_RESULT, FALLBACK_RESULT}:
            if selected_bound is None:
                raise RouteEnvelopeVerificationError(
                    "execution result has no verified selected upper bound"
                )
            expected_route = (
                LOCAL_ATTEMPT
                if event.evidence.role == LOCAL_RESULT
                else DIRECT_FALLBACK
            )
            if selected_bound.route_candidate != expected_route:
                raise RouteEnvelopeVerificationError(
                    "execution result differs from selected route"
                )
            assert event.evidence.actual_comparison is not None
            try:
                _actual_within_bound(event.evidence.actual_comparison, selected_bound)
            except AuditableRouterError as error:
                raise RouteEnvelopeVerificationError(str(error)) from error

        try:
            next_state = _next_state(state, event.evidence)
        except AuditableRouterError as error:
            raise RouteEnvelopeVerificationError(str(error)) from error
        if event.state_after != next_state:
            raise RouteEnvelopeVerificationError("event state_after differs from replay")
        state = next_state
        if state == NEXT_LOCAL_TRANSACTION_REQUIRED:
            selected_bound = None
            frozen_fallback_bound = None
        elif state == FALLBACK_EXECUTION_REQUIRED and event.evidence.role == LOCAL_RESULT:
            if frozen_fallback_bound is None:
                raise RouteEnvelopeVerificationError(
                    "failed local transaction did not retain a fallback upper bound"
                )
            selected_bound = frozen_fallback_bound

    if state not in _TERMINAL_STATES:
        raise RouteEnvelopeVerificationError("complete envelope ends on a nonterminal state")
    accumulated = sum_work_vectors(
        (event.evidence.work_delta for event in envelope.events),
        subject_id=f"route-attempt:{context.route_attempt_id}",
    )
    if envelope.final_state != state or envelope.accumulated_work != accumulated:
        raise RouteEnvelopeVerificationError("envelope final state/work reconciliation mismatch")
    return state, accumulated


@dataclass(frozen=True, slots=True)
class StrictRouteCertificateCandidate:
    context_id: str
    envelope_id: str
    catalog_id: str
    final_state: str
    accumulated_work_vector_id: str
    current_attempt_terminal: bool = True
    campaign_retry_policy: None = None
    official: bool = False

    def __post_init__(self) -> None:
        for field in (
            "context_id",
            "envelope_id",
            "catalog_id",
            "final_state",
            "accumulated_work_vector_id",
        ):
            _identifier(getattr(self, field), field=field)
        if self.current_attempt_terminal is not True:
            raise RouteEnvelopeVerificationError("strict route certificate is not terminal")
        if self.campaign_retry_policy is not None:
            raise RouteEnvelopeVerificationError("campaign retry policy remains unresolved")
        if self.official:
            raise RouteEnvelopeVerificationError("candidate route certificate cannot be official")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.strict_route_certificate.phase3e_candidate.v1",
            "context_id": self.context_id,
            "envelope_id": self.envelope_id,
            "catalog_id": self.catalog_id,
            "final_state": self.final_state,
            "accumulated_work_vector_id": self.accumulated_work_vector_id,
            "current_attempt_terminal": True,
            "campaign_retry_policy": None,
            "official": False,
            "routing_protocol_status": ROUTING_MECHANICS_ONLY,
            "economics_gate_status": ECONOMICS_NOT_RUN,
        }

    @property
    def certificate_id(self) -> str:
        return object_id(self._payload(), "strict-route-certificate")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "certificate_id": self.certificate_id}


def certify_route_envelope_candidate(
    *,
    envelope: RouteTraceEnvelope,
    context: RouteDecisionContext,
    registry: CounterRegistry,
    catalog: VerifiedRouteInputCatalog,
) -> StrictRouteCertificateCandidate:
    state, accumulated = replay_strict_route_envelope(
        envelope=envelope,
        context=context,
        registry=registry,
        catalog=catalog,
    )
    return StrictRouteCertificateCandidate(
        context.context_id,
        envelope.envelope_id,
        catalog.catalog_id,
        state,
        accumulated.vector_id,
    )


__all__ = [
    "ArtifactVerificationAttestation",
    "RouteEnvelopeVerificationError",
    "StrictRouteCertificateCandidate",
    "VerifiedRouteInputCatalog",
    "certify_route_envelope_candidate",
    "replay_strict_route_envelope",
]
