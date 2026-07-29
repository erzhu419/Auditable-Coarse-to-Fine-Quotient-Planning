"""Typed V0-072 bridge from exact lazy planning to independent proof replay.

This component does not add a second planning semantics.  It accepts only the
standard planner model used by the existing robust authority, runs the exact
lazy H=2 solver once, and, for a solved result, requires the separately
implemented prefix-cover verifier before exposing an operational result.
Resource exhaustion remains a typed noncertificate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import exact_lazy_h2_independent_verifier_v1 as independent
from . import exact_lazy_h2_robust_planner_v1 as lazy
from . import partial_support_robust_planner_v1 as robust


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_exact_lazy_planner_independent_verifier_component_v1"

DOMAIN_TAGS = {
    "solve": "acfqp:v072-exact-lazy-solve-result-commitment:v1",
    "component": "acfqp:v072-exact-lazy-planner-component-result:v1",
}


class V072ExactLazyPlannerComponentInvariantViolation(ValueError):
    """The model, solve result, or independent attestation is inconsistent."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        DOMAIN_TAGS[role].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072ExactLazyPlannerComponentInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _counter_document(
    value: lazy.ExactLazyH2SearchCountersV1,
) -> dict[str, int]:
    return {
        "branch_nodes": value.branch_nodes,
        "complete_policies": value.complete_policies,
        "root_bound_evaluations": value.root_bound_evaluations,
        "pruned_branches": value.pruned_branches,
        "root_actions_considered": value.root_actions_considered,
        "relevant_decision_units": value.relevant_decision_units,
        "irrelevant_decision_units": value.irrelevant_decision_units,
    }


def _solve_result_document(
    value: lazy.ExactLazyH2SolveResultV1,
) -> dict[str, Any]:
    if value.status is lazy.ExactLazyH2SolveStatus.SOLVED:
        if value.audit is None or value.trace is None:
            raise V072ExactLazyPlannerComponentInvariantViolation(
                "solved result lacks its audit or proof trace"
            )
        return {
            "status": value.status.value,
            "solver_kind": value.solver_kind.value,
            "audit_id": value.audit.audit_id,
            "original_proof_id": value.trace.original_proof.proof_id,
            "zero_other_proof_id": (
                None
                if value.trace.zero_other_counterfactual_proof is None
                else value.trace.zero_other_counterfactual_proof.proof_id
            ),
            "original_counters": _counter_document(value.trace.original),
            "zero_other_counters": (
                None
                if value.trace.zero_other_counterfactual is None
                else _counter_document(
                    value.trace.zero_other_counterfactual
                )
            ),
        }
    exhaustion = value.exhaustion
    if exhaustion is None:
        raise V072ExactLazyPlannerComponentInvariantViolation(
            "resource result lacks typed exhaustion"
        )
    return {
        "status": value.status.value,
        "solver_kind": value.solver_kind.value,
        "exhaustion": {
            "phase": exhaustion.phase.value,
            "code": exhaustion.code.value,
            "observed": exhaustion.observed,
            "limit": exhaustion.limit,
            "counters": _counter_document(exhaustion.counters),
            "terminal_code": exhaustion.terminal_code,
            "approximate_audit_emitted": False,
        },
    }


def _solve_result_id(value: lazy.ExactLazyH2SolveResultV1) -> str:
    return _content_id("solve", _solve_result_document(value))


@dataclass(frozen=True, slots=True)
class V072ExactLazyPlannerComponentResultV1:
    """One exact solve plus the mandatory independent proof result."""

    model_id: str
    threshold_profile_id: str
    solver_kind: robust.RobustSolverKind
    solve_result: lazy.ExactLazyH2SolveResultV1
    independent_verification: (
        independent.ExactLazyH2IndependentVerificationV1 | None
    )
    _component_result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.model_id, "component model")
        _cid(self.threshold_profile_id, "component threshold")
        solved = (
            self.solve_result.status
            is lazy.ExactLazyH2SolveStatus.SOLVED
        )
        verification = self.independent_verification
        if (
            type(self.solver_kind) is not robust.RobustSolverKind
            or type(self.solve_result) is not lazy.ExactLazyH2SolveResultV1
            or self.solve_result.solver_kind is not self.solver_kind
            or (
                solved
                and (
                    type(verification)
                    is not independent.ExactLazyH2IndependentVerificationV1
                    or self.solve_result.audit is None
                    or verification.model_id != self.model_id
                    or verification.threshold_profile_id
                    != self.threshold_profile_id
                    or verification.audit_id
                    != self.solve_result.audit.audit_id
                    or verification.solver_kind is not self.solver_kind
                )
            )
            or (
                not solved
                and (
                    verification is not None
                    or self.solve_result.status
                    is not (
                        lazy.ExactLazyH2SolveStatus
                        .EXACT_DP_RESOURCE_EXHAUSTED
                    )
                    or self.solve_result.exhaustion is None
                )
            )
        ):
            raise V072ExactLazyPlannerComponentInvariantViolation(
                "exact solve and independent verification do not form one "
                "typed operational result"
            )
        object.__setattr__(
            self,
            "_component_result_id",
            _content_id("component", self._payload()),
        )

    @property
    def independent_proof_replay_complete(self) -> bool:
        return (
            self.solve_result.status
            is lazy.ExactLazyH2SolveStatus.SOLVED
            and self.independent_verification is not None
        )

    @property
    def plan_certificate_authority(self) -> bool:
        audit = self.solve_result.audit
        return (
            self.independent_proof_replay_complete
            and audit is not None
            and audit.status is robust.RobustAuditStatus.CERTIFIED
        )

    def _payload(self) -> dict[str, Any]:
        verification = self.independent_verification
        return {
            "schema": (
                "acfqp.v072_exact_lazy_planner_component_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "model_id": self.model_id,
            "threshold_profile_id": self.threshold_profile_id,
            "solver_kind": self.solver_kind.value,
            "solve_result_id": _solve_result_id(self.solve_result),
            "solve_status": self.solve_result.status.value,
            "independent_verification_id": (
                None
                if verification is None
                else verification.verification_id
            ),
            "independent_proof_replay_complete": (
                self.independent_proof_replay_complete
            ),
            "plan_certificate_authority": (
                self.plan_certificate_authority
            ),
            "approximation_used": False,
            "fallback_used": False,
            "ground_kernel_calls": 0,
        }

    @property
    def component_result_id(self) -> str:
        return self._component_result_id

    def to_document(self) -> dict[str, Any]:
        verification = self.independent_verification
        return {
            **self._payload(),
            "solve_result": _solve_result_document(self.solve_result),
            "independent_verification": (
                None if verification is None else verification.to_document()
            ),
            "component_result_id": self.component_result_id,
        }


def solve_and_verify_v072_exact_lazy_h2_v1(
    *,
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    limits: lazy.ExactLazyH2ResourceLimitsV1 = (
        lazy.ExactLazyH2ResourceLimitsV1()
    ),
) -> V072ExactLazyPlannerComponentResultV1:
    """Run one exact operational solve and independently replay its proof."""

    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(solver_kind) is not robust.RobustSolverKind
        or type(limits) is not lazy.ExactLazyH2ResourceLimitsV1
        or model.context_id != threshold.context_id
    ):
        raise V072ExactLazyPlannerComponentInvariantViolation(
            "component inputs must be one exact standard model request"
        )
    result = lazy.solve_exact_lazy_robust_h2_v1(
        model,
        threshold,
        solver_kind,
        limits=limits,
    )
    verification = (
        independent.verify_exact_lazy_h2_solve_result_v1(
            model,
            threshold,
            result,
        )
        if result.status is lazy.ExactLazyH2SolveStatus.SOLVED
        else None
    )
    return V072ExactLazyPlannerComponentResultV1(
        model.model_id,
        threshold.threshold_profile_id,
        solver_kind,
        result,
        verification,
    )


__all__ = [
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V072ExactLazyPlannerComponentInvariantViolation",
    "V072ExactLazyPlannerComponentResultV1",
    "solve_and_verify_v072_exact_lazy_h2_v1",
]
