"""Fail-closed dynamic-routing mechanics for Phase 3E preconstruction.

The state machine is deliberately non-official: it validates precedence,
componentwise candidate estimates, cap exhaustion, and hash-chained work traces,
but it cannot authorize the frozen Phase-3E workload before the normative
preregistration fields are resolved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from acfqp.artifacts import object_id
from acfqp.phase3e_accounting import ECONOMICS_NOT_RUN, ROUTING_MECHANICS_ONLY
from acfqp.work_accounting import (
    EQUAL,
    INCOMPARABLE,
    LEFT_DOMINATES,
    RIGHT_DOMINATES,
    CounterRegistry,
    CounterValidationError,
    WorkVector,
    componentwise_cost_relation,
    sum_work_vectors,
)


ABSTRACT_CERTIFIED = "ABSTRACT_CERTIFIED"
LOCAL_GROUND_RECOVERY = "LOCAL_GROUND_RECOVERY"
FULL_GROUND_FALLBACK = "FULL_GROUND_FALLBACK"
INFEASIBLE_QUERY = "INFEASIBLE_QUERY"
REBUILD_REQUIRED = "REBUILD_REQUIRED"

ABSTRACT_AUDIT_REQUIRED = "ABSTRACT_AUDIT_REQUIRED"
RECOVERY_DECISION_REQUIRED = "RECOVERY_DECISION_REQUIRED"
NEXT_LOCAL_TRANSACTION_REQUIRED = "NEXT_LOCAL_TRANSACTION_REQUIRED"
FULL_GROUND_FALLBACK_REQUIRED = "FULL_GROUND_FALLBACK_REQUIRED"
FALLBACK_CAP_EXHAUSTED_NO_CERTIFICATE = "FALLBACK_CAP_EXHAUSTED_NO_CERTIFICATE"

LOCAL_ATTEMPT = "LOCAL_ATTEMPT"
DIRECT_FALLBACK = "DIRECT_FALLBACK"
LOCAL_ATTEMPT_SELECTED = "LOCAL_ATTEMPT_SELECTED"
FALLBACK_ATTEMPT_SELECTED = "FALLBACK_ATTEMPT_SELECTED"

CAUSAL_FAMILY_FOUND = "CAUSAL_FAMILY_FOUND"
CAUSAL_CAP_EXHAUSTED = "CAUSAL_CAP_EXHAUSTED"
NO_SOUND_CAUSAL_COVER = "NO_SOUND_CAUSAL_COVER"

LOCAL_ESTIMATE_SEMANTICS = "MARGINAL_LOCAL_ATTEMPT_CANDIDATE_PREDECISION"
FALLBACK_ESTIMATE_SEMANTICS = "DIRECT_FALLBACK_CANDIDATE_PREDECISION"

_TERMINAL_ROUTES = frozenset(
    {
        ABSTRACT_CERTIFIED,
        LOCAL_GROUND_RECOVERY,
        FULL_GROUND_FALLBACK,
        INFEASIBLE_QUERY,
        REBUILD_REQUIRED,
    }
)
_CAUSAL_STATUSES = frozenset(
    {CAUSAL_FAMILY_FOUND, CAUSAL_CAP_EXHAUSTED, NO_SOUND_CAUSAL_COVER}
)


class RouterProtocolError(ValueError):
    """Routing evidence is incomplete, inconsistent, or post-result dependent."""


class ArtifactIntegrityError(RouterProtocolError):
    """Artifact integrity failure is a protocol failure, never a query route."""


def _identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RouterProtocolError(f"{field} must be a nonempty identifier")
    return value


def _boolean(value: Any, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise RouterProtocolError(f"{field} must be boolean")
    return value


@dataclass(frozen=True, slots=True)
class PreflightEvidence:
    """Evidence available before any local materialization or fallback solve."""

    protocol_candidate_id: str
    epoch_id: str
    logical_occurrence_id: str
    artifact_integrity_valid: bool
    identity_compatible: bool
    coverage_compatible: bool
    semantics_compatible: bool
    matching_exact_infeasibility_proof: bool
    abstract_audit_complete: bool
    abstract_certificate_passed: bool

    def __post_init__(self) -> None:
        _identifier(self.protocol_candidate_id, field="protocol_candidate_id")
        _identifier(self.epoch_id, field="epoch_id")
        _identifier(self.logical_occurrence_id, field="logical_occurrence_id")
        for field in (
            "artifact_integrity_valid",
            "identity_compatible",
            "coverage_compatible",
            "semantics_compatible",
            "matching_exact_infeasibility_proof",
            "abstract_audit_complete",
            "abstract_certificate_passed",
        ):
            _boolean(getattr(self, field), field=field)
        if self.abstract_certificate_passed and not self.abstract_audit_complete:
            raise RouterProtocolError(
                "an abstract certificate cannot pass before its audit is complete"
            )

    @property
    def evidence_id(self) -> str:
        return object_id(
            {
                "schema": "acfqp.phase3e_preflight_evidence.v1",
                "protocol_candidate_id": self.protocol_candidate_id,
                "epoch_id": self.epoch_id,
                "logical_occurrence_id": self.logical_occurrence_id,
                "artifact_integrity_valid": self.artifact_integrity_valid,
                "identity_compatible": self.identity_compatible,
                "coverage_compatible": self.coverage_compatible,
                "semantics_compatible": self.semantics_compatible,
                "matching_exact_infeasibility_proof": (
                    self.matching_exact_infeasibility_proof
                ),
                "abstract_audit_complete": self.abstract_audit_complete,
                "abstract_certificate_passed": self.abstract_certificate_passed,
            },
            "phase3e-preflight-evidence",
        )


@dataclass(frozen=True, slots=True)
class PreflightDecision:
    status: str
    reason: str
    terminal: bool
    evidence_id: str
    official: bool = False

    def __post_init__(self) -> None:
        _identifier(self.status, field="preflight status")
        _identifier(self.reason, field="preflight reason")
        _identifier(self.evidence_id, field="preflight evidence_id")
        _boolean(self.terminal, field="preflight terminal")
        if self.official:
            raise RouterProtocolError("preconstruction decisions cannot be official")
        if self.terminal != (self.status in _TERMINAL_ROUTES):
            raise RouterProtocolError("preflight terminal flag disagrees with status")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": "acfqp.phase3e_preflight_decision.v1",
            "status": self.status,
            "reason": self.reason,
            "terminal": self.terminal,
            "evidence_id": self.evidence_id,
            "official": False,
            "routing_protocol_status": ROUTING_MECHANICS_ONLY,
            "economics_gate_status": ECONOMICS_NOT_RUN,
        }
        return {**payload, "decision_id": object_id(payload, "preflight-decision")}


def decide_preflight(evidence: PreflightEvidence) -> PreflightDecision:
    """Apply fixed precedence without turning integrity failures into routes."""

    if not evidence.artifact_integrity_valid:
        raise ArtifactIntegrityError(
            "artifact hash/schema integrity failure cannot become REBUILD_REQUIRED"
        )
    if not (
        evidence.identity_compatible
        and evidence.coverage_compatible
        and evidence.semantics_compatible
    ):
        return PreflightDecision(
            REBUILD_REQUIRED,
            "VALID_ARTIFACT_IDENTITY_COVERAGE_OR_SEMANTICS_MISMATCH",
            True,
            evidence.evidence_id,
        )
    if evidence.matching_exact_infeasibility_proof:
        return PreflightDecision(
            INFEASIBLE_QUERY,
            "IDENTICAL_QUERY_EXACT_INFEASIBILITY_PROOF_MATCH",
            True,
            evidence.evidence_id,
        )
    if not evidence.abstract_audit_complete:
        return PreflightDecision(
            ABSTRACT_AUDIT_REQUIRED,
            "ABSTRACT_AUDIT_NOT_COMPLETE",
            False,
            evidence.evidence_id,
        )
    if evidence.abstract_certificate_passed:
        return PreflightDecision(
            ABSTRACT_CERTIFIED,
            "COMPLETE_ABSTRACT_CERTIFICATE_PASS",
            True,
            evidence.evidence_id,
        )
    return PreflightDecision(
        RECOVERY_DECISION_REQUIRED,
        "COMPLETE_ABSTRACT_CERTIFICATE_FAILED",
        False,
        evidence.evidence_id,
    )


@dataclass(frozen=True, slots=True)
class RouteEstimate:
    """A cap-derived upper vector frozen before selected-route execution."""

    route_candidate: str
    estimate_semantics: str
    protocol_candidate_id: str
    epoch_id: str
    logical_occurrence_id: str
    decision_point_id: str
    cap_profile_candidate_id: str
    derivation_id: str
    input_cardinality_id: str
    vector: WorkVector
    derived_before_execution: bool = True
    depends_on_actual_selected_route_counters: bool = False

    def __post_init__(self) -> None:
        if self.route_candidate not in {LOCAL_ATTEMPT, DIRECT_FALLBACK}:
            raise RouterProtocolError("unknown route-estimate candidate")
        expected_semantics = (
            LOCAL_ESTIMATE_SEMANTICS
            if self.route_candidate == LOCAL_ATTEMPT
            else FALLBACK_ESTIMATE_SEMANTICS
        )
        if self.estimate_semantics != expected_semantics:
            raise RouterProtocolError("route estimate uses the wrong semantics")
        for field in (
            "protocol_candidate_id",
            "epoch_id",
            "logical_occurrence_id",
            "decision_point_id",
            "cap_profile_candidate_id",
            "derivation_id",
            "input_cardinality_id",
        ):
            _identifier(getattr(self, field), field=field)
        if not self.derived_before_execution:
            raise RouterProtocolError("route estimate was not frozen before execution")
        if self.depends_on_actual_selected_route_counters:
            raise RouterProtocolError("route estimate depends on post-run actual work")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_route_estimate_candidate.v1",
            "route_candidate": self.route_candidate,
            "estimate_semantics": self.estimate_semantics,
            "protocol_candidate_id": self.protocol_candidate_id,
            "epoch_id": self.epoch_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "decision_point_id": self.decision_point_id,
            "cap_profile_candidate_id": self.cap_profile_candidate_id,
            "derivation_id": self.derivation_id,
            "input_cardinality_id": self.input_cardinality_id,
            "derived_before_execution": True,
            "depends_on_actual_selected_route_counters": False,
            "work_vector": self.vector.to_dict(),
            "official": False,
        }

    @property
    def estimate_id(self) -> str:
        return object_id(self._payload(), "route-estimate-candidate")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "estimate_id": self.estimate_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RouteEstimate":
        expected = {
            "schema",
            "route_candidate",
            "estimate_semantics",
            "protocol_candidate_id",
            "epoch_id",
            "logical_occurrence_id",
            "decision_point_id",
            "cap_profile_candidate_id",
            "derivation_id",
            "input_cardinality_id",
            "derived_before_execution",
            "depends_on_actual_selected_route_counters",
            "work_vector",
            "official",
            "estimate_id",
        }
        if set(document) != expected:
            raise RouterProtocolError("route-estimate field set mismatch")
        if document["schema"] != "acfqp.phase3e_route_estimate_candidate.v1":
            raise RouterProtocolError("route-estimate schema mismatch")
        if document["official"] is not False:
            raise RouterProtocolError("preconstruction estimate claims official status")
        vector_doc = document["work_vector"]
        if not isinstance(vector_doc, Mapping):
            raise RouterProtocolError("route-estimate WorkVector is malformed")
        estimate = cls(
            route_candidate=document["route_candidate"],
            estimate_semantics=document["estimate_semantics"],
            protocol_candidate_id=document["protocol_candidate_id"],
            epoch_id=document["epoch_id"],
            logical_occurrence_id=document["logical_occurrence_id"],
            decision_point_id=document["decision_point_id"],
            cap_profile_candidate_id=document["cap_profile_candidate_id"],
            derivation_id=document["derivation_id"],
            input_cardinality_id=document["input_cardinality_id"],
            vector=WorkVector.from_dict(vector_doc),
            derived_before_execution=document["derived_before_execution"],
            depends_on_actual_selected_route_counters=document[
                "depends_on_actual_selected_route_counters"
            ],
        )
        if document["estimate_id"] != estimate.estimate_id:
            raise RouterProtocolError("route-estimate content ID mismatch")
        return estimate


@dataclass(frozen=True, slots=True)
class RecoverySelection:
    selected_attempt: str
    reason: str
    cost_relation: str
    local_estimate_id: str | None
    fallback_estimate_id: str
    official: bool = False

    def __post_init__(self) -> None:
        if self.selected_attempt not in {
            LOCAL_ATTEMPT_SELECTED,
            FALLBACK_ATTEMPT_SELECTED,
        }:
            raise RouterProtocolError("unknown recovery selection")
        _identifier(self.reason, field="recovery-selection reason")
        _identifier(self.cost_relation, field="cost relation")
        if self.local_estimate_id is not None:
            _identifier(self.local_estimate_id, field="local_estimate_id")
        _identifier(self.fallback_estimate_id, field="fallback_estimate_id")
        if self.official:
            raise RouterProtocolError("preconstruction selection cannot be official")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": "acfqp.phase3e_recovery_selection_candidate.v1",
            "selected_attempt": self.selected_attempt,
            "reason": self.reason,
            "cost_relation": self.cost_relation,
            "local_estimate_id": self.local_estimate_id,
            "fallback_estimate_id": self.fallback_estimate_id,
            "official": False,
            "routing_protocol_status": ROUTING_MECHANICS_ONLY,
            "economics_gate_status": ECONOMICS_NOT_RUN,
        }
        return {**payload, "selection_id": object_id(payload, "recovery-selection")}


def _validate_estimate(
    estimate: RouteEstimate, registry: CounterRegistry, *, candidate: str
) -> None:
    if estimate.route_candidate != candidate:
        raise RouterProtocolError("route estimate is bound to a different candidate")
    try:
        registry.validate_vector(estimate.vector)
    except CounterValidationError as error:
        raise RouterProtocolError(str(error)) from error


def select_recovery_attempt(
    *,
    preflight: PreflightDecision,
    causal_status: str,
    local_estimate: RouteEstimate | None,
    fallback_estimate: RouteEstimate,
    registry: CounterRegistry,
) -> RecoverySelection:
    """Exercise conservative candidate routing after a failed exact certificate."""

    if preflight.status != RECOVERY_DECISION_REQUIRED or preflight.terminal:
        raise RouterProtocolError("recovery selection requires failed-certificate preflight")
    if causal_status not in _CAUSAL_STATUSES:
        raise RouterProtocolError("unknown causal-search status")
    _validate_estimate(fallback_estimate, registry, candidate=DIRECT_FALLBACK)
    if causal_status != CAUSAL_FAMILY_FOUND:
        reason = (
            "CAUSAL_CAP_EXHAUSTED_DIRECT_FALLBACK"
            if causal_status == CAUSAL_CAP_EXHAUSTED
            else "NO_SOUND_CAUSAL_COVER_DIRECT_FALLBACK"
        )
        return RecoverySelection(
            FALLBACK_ATTEMPT_SELECTED,
            reason,
            "NOT_COMPARED_NO_AUTHORIZED_LOCAL_ATTEMPT",
            None,
            fallback_estimate.estimate_id,
        )
    if local_estimate is None:
        raise RouterProtocolError("causal-family success requires a local estimate")
    _validate_estimate(local_estimate, registry, candidate=LOCAL_ATTEMPT)
    bindings = (
        "protocol_candidate_id",
        "epoch_id",
        "logical_occurrence_id",
        "decision_point_id",
        "cap_profile_candidate_id",
    )
    if any(
        getattr(local_estimate, field) != getattr(fallback_estimate, field)
        for field in bindings
    ):
        raise RouterProtocolError("local and fallback estimates bind different decisions")
    relation = componentwise_cost_relation(
        local_estimate.vector, fallback_estimate.vector, registry
    )
    if relation == LEFT_DOMINATES:
        return RecoverySelection(
            LOCAL_ATTEMPT_SELECTED,
            "LOCAL_ATTEMPT_STRICT_COMPONENTWISE_DOMINANCE_CANDIDATE",
            relation,
            local_estimate.estimate_id,
            fallback_estimate.estimate_id,
        )
    reasons = {
        RIGHT_DOMINATES: "FALLBACK_STRICT_COMPONENTWISE_DOMINANCE_CANDIDATE",
        EQUAL: "COST_VECTOR_EQUAL_CONSERVATIVE_FALLBACK",
        INCOMPARABLE: "COST_VECTOR_INCOMPARABLE_CONSERVATIVE_FALLBACK",
    }
    return RecoverySelection(
        FALLBACK_ATTEMPT_SELECTED,
        reasons[relation],
        relation,
        local_estimate.estimate_id,
        fallback_estimate.estimate_id,
    )


def verify_actual_within_estimate(
    actual: WorkVector, estimate: RouteEstimate, registry: CounterRegistry
) -> None:
    """Require every charged operational actual component to stay below its cap."""

    registry.validate_vector(actual)
    registry.validate_vector(estimate.vector)
    actual_values = dict(actual.values)
    upper_values = dict(estimate.vector.values)
    exceeded = tuple(
        path
        for path in registry.operational_cost_paths
        if actual_values[path] > upper_values[path]
    )
    if exceeded:
        raise RouterProtocolError(f"actual route work exceeds estimate: {exceeded!r}")


def resolve_local_attempt(
    *,
    post_audit_certified: bool,
    deeper_failed_frontier_exists: bool,
    transaction_budget_remaining: bool,
) -> str:
    """Resolve one charged local transaction without hiding failed work."""

    for field, value in (
        ("post_audit_certified", post_audit_certified),
        ("deeper_failed_frontier_exists", deeper_failed_frontier_exists),
        ("transaction_budget_remaining", transaction_budget_remaining),
    ):
        _boolean(value, field=field)
    if post_audit_certified:
        return LOCAL_GROUND_RECOVERY
    if deeper_failed_frontier_exists and transaction_budget_remaining:
        return NEXT_LOCAL_TRANSACTION_REQUIRED
    return FULL_GROUND_FALLBACK_REQUIRED


def resolve_fallback(
    *, complete: bool, feasible: bool, cap_exhausted: bool
) -> str:
    """Only a complete fallback solve may emit feasibility or infeasibility."""

    for field, value in (
        ("complete", complete),
        ("feasible", feasible),
        ("cap_exhausted", cap_exhausted),
    ):
        _boolean(value, field=field)
    if cap_exhausted:
        if complete:
            raise RouterProtocolError("fallback cannot be complete and cap-exhausted")
        return FALLBACK_CAP_EXHAUSTED_NO_CERTIFICATE
    if not complete:
        raise RouterProtocolError("incomplete fallback without cap status is invalid")
    return FULL_GROUND_FALLBACK if feasible else INFEASIBLE_QUERY


@dataclass(frozen=True, slots=True)
class RouteTraceEvent:
    """One hash-chained state-machine event with a full WorkVector delta."""

    protocol_candidate_id: str
    epoch_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    transaction_id: str | None
    sequence: int
    stage: str
    decision_code: str
    evidence_ids: tuple[str, ...]
    work_delta: WorkVector
    prev_event_id: str | None

    def __post_init__(self) -> None:
        for field in (
            "protocol_candidate_id",
            "epoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "stage",
            "decision_code",
        ):
            _identifier(getattr(self, field), field=field)
        if self.transaction_id is not None:
            _identifier(self.transaction_id, field="transaction_id")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise RouterProtocolError("trace sequence must be an integer")
        if self.sequence < 0:
            raise RouterProtocolError("trace sequence must be nonnegative")
        if not isinstance(self.evidence_ids, tuple):
            raise RouterProtocolError("trace evidence_ids must be a tuple")
        for evidence_id in self.evidence_ids:
            _identifier(evidence_id, field="trace evidence_id")
        if self.prev_event_id is not None:
            _identifier(self.prev_event_id, field="prev_event_id")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_route_trace_event.v1",
            "protocol_candidate_id": self.protocol_candidate_id,
            "epoch_id": self.epoch_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "transaction_id": self.transaction_id,
            "sequence": self.sequence,
            "stage": self.stage,
            "decision_code": self.decision_code,
            "evidence_ids": list(self.evidence_ids),
            "work_delta": self.work_delta.to_dict(),
            "prev_event_id": self.prev_event_id,
            "official": False,
        }

    @property
    def event_id(self) -> str:
        return object_id(self._payload(), "route-trace-event")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "event_id": self.event_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RouteTraceEvent":
        expected = {
            "schema",
            "protocol_candidate_id",
            "epoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "transaction_id",
            "sequence",
            "stage",
            "decision_code",
            "evidence_ids",
            "work_delta",
            "prev_event_id",
            "official",
            "event_id",
        }
        if set(document) != expected:
            raise RouterProtocolError("route-trace event field set mismatch")
        if document["schema"] != "acfqp.phase3e_route_trace_event.v1":
            raise RouterProtocolError("route-trace event schema mismatch")
        if document["official"] is not False:
            raise RouterProtocolError("preconstruction trace claims official status")
        evidence_ids = document["evidence_ids"]
        work_delta = document["work_delta"]
        if not isinstance(evidence_ids, list) or not isinstance(work_delta, Mapping):
            raise RouterProtocolError("route-trace nested field is malformed")
        event = cls(
            protocol_candidate_id=document["protocol_candidate_id"],
            epoch_id=document["epoch_id"],
            logical_occurrence_id=document["logical_occurrence_id"],
            route_attempt_id=document["route_attempt_id"],
            transaction_id=document["transaction_id"],
            sequence=document["sequence"],
            stage=document["stage"],
            decision_code=document["decision_code"],
            evidence_ids=tuple(evidence_ids),
            work_delta=WorkVector.from_dict(work_delta),
            prev_event_id=document["prev_event_id"],
        )
        if document["event_id"] != event.event_id:
            raise RouterProtocolError("route-trace event content ID mismatch")
        return event


def append_route_trace_event(
    events: Sequence[RouteTraceEvent],
    *,
    protocol_candidate_id: str,
    epoch_id: str,
    logical_occurrence_id: str,
    route_attempt_id: str,
    transaction_id: str | None,
    stage: str,
    decision_code: str,
    evidence_ids: Iterable[str],
    work_delta: WorkVector,
) -> RouteTraceEvent:
    previous = events[-1] if events else None
    return RouteTraceEvent(
        protocol_candidate_id=protocol_candidate_id,
        epoch_id=epoch_id,
        logical_occurrence_id=logical_occurrence_id,
        route_attempt_id=route_attempt_id,
        transaction_id=transaction_id,
        sequence=len(events),
        stage=stage,
        decision_code=decision_code,
        evidence_ids=tuple(evidence_ids),
        work_delta=work_delta,
        prev_event_id=previous.event_id if previous is not None else None,
    )


def verify_route_trace(
    events: Sequence[RouteTraceEvent], registry: CounterRegistry
) -> WorkVector:
    """Verify the chain and return exact accumulated work."""

    if not events:
        raise RouterProtocolError("route trace cannot be empty")
    first = events[0]
    binding = (
        first.protocol_candidate_id,
        first.epoch_id,
        first.logical_occurrence_id,
        first.route_attempt_id,
    )
    for index, event in enumerate(events):
        if event.sequence != index:
            raise RouterProtocolError("route-trace sequence is not contiguous")
        expected_prev = events[index - 1].event_id if index else None
        if event.prev_event_id != expected_prev:
            raise RouterProtocolError("route-trace hash chain is broken")
        if (
            event.protocol_candidate_id,
            event.epoch_id,
            event.logical_occurrence_id,
            event.route_attempt_id,
        ) != binding:
            raise RouterProtocolError("route-trace binding changed within an attempt")
        try:
            registry.validate_vector(event.work_delta)
        except CounterValidationError as error:
            raise RouterProtocolError(str(error)) from error
    return sum_work_vectors(
        (event.work_delta for event in events),
        subject_id=f"route-attempt:{first.route_attempt_id}",
    )


def verify_route_trace_documents(
    documents: Sequence[Mapping[str, Any]], registry: CounterRegistry
) -> tuple[tuple[RouteTraceEvent, ...], WorkVector]:
    events = tuple(RouteTraceEvent.from_dict(document) for document in documents)
    return events, verify_route_trace(events, registry)


__all__ = [
    "ABSTRACT_AUDIT_REQUIRED",
    "ABSTRACT_CERTIFIED",
    "ArtifactIntegrityError",
    "CAUSAL_CAP_EXHAUSTED",
    "CAUSAL_FAMILY_FOUND",
    "DIRECT_FALLBACK",
    "FALLBACK_ATTEMPT_SELECTED",
    "FALLBACK_CAP_EXHAUSTED_NO_CERTIFICATE",
    "FALLBACK_ESTIMATE_SEMANTICS",
    "FULL_GROUND_FALLBACK",
    "FULL_GROUND_FALLBACK_REQUIRED",
    "INFEASIBLE_QUERY",
    "LOCAL_ATTEMPT",
    "LOCAL_ATTEMPT_SELECTED",
    "LOCAL_ESTIMATE_SEMANTICS",
    "LOCAL_GROUND_RECOVERY",
    "NEXT_LOCAL_TRANSACTION_REQUIRED",
    "NO_SOUND_CAUSAL_COVER",
    "PreflightDecision",
    "PreflightEvidence",
    "REBUILD_REQUIRED",
    "RECOVERY_DECISION_REQUIRED",
    "RecoverySelection",
    "RouteEstimate",
    "RouteTraceEvent",
    "RouterProtocolError",
    "append_route_trace_event",
    "decide_preflight",
    "resolve_fallback",
    "resolve_local_attempt",
    "select_recovery_attempt",
    "verify_actual_within_estimate",
    "verify_route_trace",
    "verify_route_trace_documents",
]
