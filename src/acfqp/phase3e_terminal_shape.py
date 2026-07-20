"""Fail-closed terminal-shape boundary for Phase-3E preconstruction.

Role-specific domain semantic verifiers, a combined route-cap contract, and a
typed cardinality/frontier binding do not yet exist.  This module therefore
classifies replay terminal *shape* only.  It cannot emit a plan certificate, an
infeasibility certificate, an official routing decision, or workload economics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from acfqp.artifacts import object_id
from acfqp.auditable_router import (
    ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
    FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL,
    FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
    INFEASIBLE_QUERY_ATTEMPT_TERMINAL,
    LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL,
    PROTOCOL_FAILURE_ATTEMPT_TERMINAL,
    REBUILD_REQUIRED_ATTEMPT_TERMINAL,
    RouteDecisionContext,
    RouteTraceEnvelope,
)
from acfqp.phase3e_accounting import (
    COUNTER_COMPLETENESS_NOT_RUN,
    ECONOMICS_NOT_RUN,
    ROUTING_MECHANICS_ONLY,
)
from acfqp.phase3e_predecision_acceptance import (
    ACCEPTANCE_STATUS as _PREDECISION_STATUS,
    EvidenceSemanticVerification,
    GuardProfileCommitment,
    Phase3EPredecisionOutcome as _Phase3EPredecisionOutcome,
    accept_phase3e_predecision_mechanics as _accept_predecision_mechanics,
)
from acfqp.route_envelope_verifier import VerifiedRouteInputCatalog
from acfqp.route_protocol_guard import (
    ATTEMPT_CLOSURE_NONCERTIFICATE as _SOURCE_NONCERTIFICATE_KIND,
    INFEASIBILITY_CERTIFICATE_CANDIDATE as _SOURCE_INFEASIBILITY_KIND,
    PLAN_CERTIFICATE_CANDIDATE as _SOURCE_PLAN_KIND,
    ActualProjectionCandidate,
    DecisionPointBinding,
    RouteCapProfileCandidate,
)
from acfqp.work_accounting import CounterRegistry


SEMANTIC_EVIDENCE_GATE_NOT_RUN = "SEMANTIC_EVIDENCE_GATE_NOT_RUN"
COMBINED_CAP_PROFILE_NOT_FROZEN = "COMBINED_CAP_PROFILE_NOT_FROZEN"
CARDINALITY_FRONTIER_BINDING_NOT_FROZEN = (
    "CARDINALITY_FRONTIER_BINDING_NOT_FROZEN"
)

PLAN_TERMINAL_SHAPE_ONLY = "PLAN_TERMINAL_SHAPE_ONLY"
INFEASIBILITY_TERMINAL_SHAPE_ONLY = "INFEASIBILITY_TERMINAL_SHAPE_ONLY"
NONCERTIFICATE_ATTEMPT_CLOSURE_SHAPE = "NONCERTIFICATE_ATTEMPT_CLOSURE_SHAPE"

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
_CLASSIFICATIONS = {
    **{state: PLAN_TERMINAL_SHAPE_ONLY for state in _PLAN_STATES},
    INFEASIBLE_QUERY_ATTEMPT_TERMINAL: INFEASIBILITY_TERMINAL_SHAPE_ONLY,
    **{
        state: NONCERTIFICATE_ATTEMPT_CLOSURE_SHAPE
        for state in _NONCERTIFICATE_STATES
    },
}
_SOURCE_KINDS = {
    **{state: _SOURCE_PLAN_KIND for state in _PLAN_STATES},
    INFEASIBLE_QUERY_ATTEMPT_TERMINAL: _SOURCE_INFEASIBILITY_KIND,
    **{state: _SOURCE_NONCERTIFICATE_KIND for state in _NONCERTIFICATE_STATES},
}


class TerminalShapeError(ValueError):
    """A terminal-shape artifact or its immediate source is inconsistent."""


def _identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise TerminalShapeError(f"{field} must be nonempty")
    return value


@dataclass(frozen=True, slots=True)
class Phase3ETerminalShapeClassification:
    source_predecision_outcome_id: str
    context_id: str
    envelope_id: str
    final_state: str
    classification: str
    semantic_evidence_gate_status: str = SEMANTIC_EVIDENCE_GATE_NOT_RUN
    combined_cap_profile_status: str = COMBINED_CAP_PROFILE_NOT_FROZEN
    cardinality_frontier_binding_status: str = (
        CARDINALITY_FRONTIER_BINDING_NOT_FROZEN
    )
    official: bool = False

    def __post_init__(self) -> None:
        for field in (
            "source_predecision_outcome_id",
            "context_id",
            "envelope_id",
            "final_state",
            "classification",
        ):
            _identifier(getattr(self, field), field=field)
        expected = _CLASSIFICATIONS.get(self.final_state)
        if expected is None or self.classification != expected:
            raise TerminalShapeError(
                "terminal state and shape classification disagree"
            )
        if self.semantic_evidence_gate_status != SEMANTIC_EVIDENCE_GATE_NOT_RUN:
            raise TerminalShapeError("semantic evidence Gate status mismatch")
        if self.combined_cap_profile_status != COMBINED_CAP_PROFILE_NOT_FROZEN:
            raise TerminalShapeError("combined cap status mismatch")
        if (
            self.cardinality_frontier_binding_status
            != CARDINALITY_FRONTIER_BINDING_NOT_FROZEN
        ):
            raise TerminalShapeError("cardinality/frontier status mismatch")
        if self.official is not False:
            raise TerminalShapeError("terminal-shape classification cannot be official")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_terminal_shape_classification.v2",
            "source_predecision_outcome_id": self.source_predecision_outcome_id,
            "context_id": self.context_id,
            "envelope_id": self.envelope_id,
            "final_state": self.final_state,
            "classification": self.classification,
            "semantic_evidence_gate_status": SEMANTIC_EVIDENCE_GATE_NOT_RUN,
            "combined_cap_profile_status": COMBINED_CAP_PROFILE_NOT_FROZEN,
            "cardinality_frontier_binding_status": (
                CARDINALITY_FRONTIER_BINDING_NOT_FROZEN
            ),
            "official": False,
            "routing_protocol_status": ROUTING_MECHANICS_ONLY,
            "economics_gate_status": ECONOMICS_NOT_RUN,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_NOT_RUN,
            "official_scalar_cost": None,
            "official_n_break_even": None,
        }

    @property
    def classification_id(self) -> str:
        return object_id(self._payload(), "phase3e-terminal-shape")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "classification_id": self.classification_id}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "Phase3ETerminalShapeClassification":
        if not isinstance(payload, Mapping):
            raise TerminalShapeError("terminal-shape payload must be a mapping")
        expected_fields = {
            "schema",
            "source_predecision_outcome_id",
            "context_id",
            "envelope_id",
            "final_state",
            "classification",
            "semantic_evidence_gate_status",
            "combined_cap_profile_status",
            "cardinality_frontier_binding_status",
            "official",
            "routing_protocol_status",
            "economics_gate_status",
            "counter_completeness_gate_status",
            "official_scalar_cost",
            "official_n_break_even",
            "classification_id",
        }
        if set(payload) != expected_fields:
            raise TerminalShapeError("terminal-shape payload fields differ from schema")
        fixed = {
            "schema": "acfqp.phase3e_terminal_shape_classification.v2",
            "semantic_evidence_gate_status": SEMANTIC_EVIDENCE_GATE_NOT_RUN,
            "combined_cap_profile_status": COMBINED_CAP_PROFILE_NOT_FROZEN,
            "cardinality_frontier_binding_status": (
                CARDINALITY_FRONTIER_BINDING_NOT_FROZEN
            ),
            "routing_protocol_status": ROUTING_MECHANICS_ONLY,
            "economics_gate_status": ECONOMICS_NOT_RUN,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_NOT_RUN,
        }
        for field, expected in fixed.items():
            if payload[field] != expected:
                raise TerminalShapeError(f"terminal-shape {field} mismatch")
        if payload["official"] is not False:
            raise TerminalShapeError("terminal-shape official must be false")
        if payload["official_scalar_cost"] is not None:
            raise TerminalShapeError("official scalar cost must remain null")
        if payload["official_n_break_even"] is not None:
            raise TerminalShapeError("official break-even must remain null")
        result = cls(
            source_predecision_outcome_id=payload[
                "source_predecision_outcome_id"
            ],
            context_id=payload["context_id"],
            envelope_id=payload["envelope_id"],
            final_state=payload["final_state"],
            classification=payload["classification"],
            semantic_evidence_gate_status=payload[
                "semantic_evidence_gate_status"
            ],
            combined_cap_profile_status=payload["combined_cap_profile_status"],
            cardinality_frontier_binding_status=payload[
                "cardinality_frontier_binding_status"
            ],
            official=payload["official"],
        )
        if payload["classification_id"] != result.classification_id:
            raise TerminalShapeError("terminal-shape content ID mismatch")
        return result


def _classify_verified_predecision_outcome(
    outcome: _Phase3EPredecisionOutcome,
) -> Phase3ETerminalShapeClassification:
    if not isinstance(outcome, _Phase3EPredecisionOutcome):
        raise TerminalShapeError("source must be a Phase3EPredecisionOutcome")
    expected_kind = _SOURCE_KINDS.get(outcome.final_state)
    if expected_kind is None or outcome.outcome_kind != expected_kind:
        raise TerminalShapeError("source terminal state and outcome kind disagree")
    if outcome.status != _PREDECISION_STATUS or outcome.official is not False:
        raise TerminalShapeError("source predecision status is invalid")
    return Phase3ETerminalShapeClassification(
        outcome.outcome_id,
        outcome.context_id,
        outcome.envelope_id,
        outcome.final_state,
        _CLASSIFICATIONS[outcome.final_state],
    )


def evaluate_phase3e_terminal_shape(
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
) -> Phase3ETerminalShapeClassification:
    """Replay full guarded inputs and return only a non-official shape artifact."""

    outcome = _accept_predecision_mechanics(
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
    return _classify_verified_predecision_outcome(outcome)


__all__ = [
    "CARDINALITY_FRONTIER_BINDING_NOT_FROZEN",
    "COMBINED_CAP_PROFILE_NOT_FROZEN",
    "INFEASIBILITY_TERMINAL_SHAPE_ONLY",
    "NONCERTIFICATE_ATTEMPT_CLOSURE_SHAPE",
    "PLAN_TERMINAL_SHAPE_ONLY",
    "Phase3ETerminalShapeClassification",
    "SEMANTIC_EVIDENCE_GATE_NOT_RUN",
    "TerminalShapeError",
    "evaluate_phase3e_terminal_shape",
]
