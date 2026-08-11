"""Fresh abstract-only planning from the held-out recovered overlay.

The source occurrence pays for two local checkpoint extensions and freezes a
query-neutral W5 quotient model.  This module binds a new logical occurrence
to that model and invokes the robust H=2 quotient planner once.  No transition
observer, ground acquisition, exact evaluator, or ground solver is reachable
from the fresh planning path.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as source_v1
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_OVERLAY_QUERY_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.120"
PROFILE_KEY = "construction_k7_heldout_overlay_abstract_reuse_v1"

QUERY_DOMAIN = CONSTRUCTION_K7_HELDOUT_OVERLAY_QUERY_V1_DOMAIN
PLAN_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset({QUERY_DOMAIN, PLAN_DOMAIN, RESULT_DOMAIN})
if len(LOCAL_DOMAINS) != 3 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out abstract-reuse domains are not central")

OFFICIAL_EXECUTION_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"

_QUERY_ISSUER = object()
_PLAN_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7HeldoutOverlayAbstractReuseV1Error(ValueError):
    """The fresh query, abstract plan, or source overlay changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutOverlayAbstractReuseV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutOverlayAbstractReuseV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class HeldoutOverlayQueryV1:
    _issuer: InitVar[object]
    logical_occurrence_id: str
    occurrence_ordinal: int
    source_result_id: str
    source_overlay_id: str
    context_id: str
    quotient_model_id: str
    threshold_profile_id: str
    query_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _QUERY_ISSUER:
            _fail("held-out overlay query is caller-minted")
        for value, label in (
            (self.logical_occurrence_id, "logical occurrence"),
            (self.source_result_id, "source result"),
            (self.source_overlay_id, "source overlay"),
            (self.context_id, "query context"),
            (self.quotient_model_id, "query quotient model"),
            (self.threshold_profile_id, "query threshold"),
        ):
            _cid(value, label)
        if type(self.occurrence_ordinal) is not int or self.occurrence_ordinal <= 0:
            _fail("fresh occurrence ordinal must be positive")
        object.__setattr__(self, "query_id", content_id(QUERY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_overlay_query.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": self.logical_occurrence_id,
            "occurrence_ordinal": self.occurrence_ordinal,
            "source_result_id": self.source_result_id,
            "source_overlay_id": self.source_overlay_id,
            "context_id": self.context_id,
            "quotient_model_id": self.quotient_model_id,
            "threshold_profile_id": self.threshold_profile_id,
            "horizon": 2,
            "query_frozen_before_planner_invocation": True,
            "observer_or_ground_input_present": False,
            "exact_evaluation_input_present": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_id": self.query_id}


@dataclass(frozen=True, slots=True)
class HeldoutOverlayAbstractPlanV1:
    _issuer: InitVar[object]
    query: HeldoutOverlayQueryV1
    source_audit_id: str
    audit: robust.RobustPlanAuditV1 = field(repr=False)
    plan_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PLAN_ISSUER:
            _fail("held-out overlay plan is caller-minted")
        _cid(self.source_audit_id, "source certified audit")
        if (
            type(self.query) is not HeldoutOverlayQueryV1
            or type(self.audit) is not robust.RobustPlanAuditV1
            or self.audit.status is not robust.RobustAuditStatus.CERTIFIED
            or self.audit.solver_kind is not robust.RobustSolverKind.QUOTIENT
            or self.audit.model_id != self.query.quotient_model_id
            or self.audit.threshold_profile_id != self.query.threshold_profile_id
            or self.audit.audit_id != self.source_audit_id
        ):
            _fail("fresh abstract plan does not replay the certified source model")
        object.__setattr__(self, "plan_id", content_id(PLAN_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "query_id": self.query.query_id,
            "source_audit_id": self.source_audit_id,
            "replanned_audit_id": self.audit.audit_id,
            "quotient_model_id": self.audit.model_id,
            "threshold_profile_id": self.audit.threshold_profile_id,
            "audit_status": self.audit.status.value,
            "fresh_query_identity_outside_model_proof": True,
            "abstract_planner_invocations": 1,
            "model_build_invocations": 0,
            "new_ground_draw_count": 0,
            "observer_call_count": 0,
            "ground_solver_invocations": 0,
            "evaluation_exact_kernel_calls": 0,
            "multi_step_plan_formed_in_abstract_model": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "audit": self.audit.to_document(),
            "plan_id": self.plan_id,
        }


@dataclass(frozen=True, slots=True)
class HeldoutOverlayAbstractReuseResultV1:
    _issuer: InitVar[object]
    source: source_v1.HeldoutCheckpointRecertificationResultV1 = field(repr=False)
    query: HeldoutOverlayQueryV1
    plan: HeldoutOverlayAbstractPlanV1
    result_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("held-out abstract-reuse result is caller-minted")
        if (
            type(self.source) is not source_v1.HeldoutCheckpointRecertificationResultV1
            or type(self.query) is not HeldoutOverlayQueryV1
            or type(self.plan) is not HeldoutOverlayAbstractPlanV1
            or self.query.source_result_id != self.source.result_id
            or self.query.source_overlay_id != self.source.final_overlay.overlay_id
            or self.query.context_id != self.source.context.context_id
            or self.query.quotient_model_id
            != self.source.final_overlay.bridge.quotient_model.model_id
            or self.query.threshold_profile_id != self.source.threshold.threshold_profile_id
            or self.plan.query != self.query
            or self.plan.source_audit_id != self.source.final_overlay.audit.audit_id
        ):
            _fail("fresh abstract-reuse identity chain is incomplete")
        object.__setattr__(self, "result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_reuse_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_result_id": self.source.result_id,
            "source_overlay_id": self.source.final_overlay.overlay_id,
            "source_final_audit_id": self.source.final_overlay.audit.audit_id,
            "query_id": self.query.query_id,
            "plan_id": self.plan.plan_id,
            "replanned_audit_id": self.plan.audit.audit_id,
            "fresh_occurrence_new_ground_draw_count": 0,
            "fresh_occurrence_observer_call_count": 0,
            "fresh_occurrence_ground_solver_invocations": 0,
            "fresh_occurrence_evaluation_exact_kernel_calls": 0,
            "fresh_occurrence_abstract_planner_invocations": 1,
            "fresh_occurrence_directly_abstract_certified": True,
            "certificate_failure_triggered_local_recovery": False,
            "source_local_recovery_reused_as_query_neutral_overlay": True,
            "construction_certificate_status": (
                "CONDITIONAL_STATISTICAL_ABSTRACT_PLAN_CERTIFIED"
            ),
            "formal_exact_iid_plan_certificate": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_result": self.source.to_document(),
            "query": self.query.to_document(),
            "plan": self.plan.to_document(),
            "final_quotient_model": (
                self.source.final_overlay.bridge.quotient_model.to_document()
            ),
            "threshold": self.source.threshold.to_document(),
            "result_id": self.result_id,
        }


def run_heldout_overlay_abstract_reuse_v1(
    source: source_v1.HeldoutCheckpointRecertificationResultV1,
    *,
    logical_occurrence_id: str,
    occurrence_ordinal: int,
) -> HeldoutOverlayAbstractReuseResultV1:
    """Freeze a fresh query, then plan only on the promoted quotient model."""

    query = freeze_heldout_overlay_query_v1(
        source,
        logical_occurrence_id=logical_occurrence_id,
        occurrence_ordinal=occurrence_ordinal,
    )
    audit = robust.solve_quotient_robust_h2_v1(
        source.final_overlay.bridge.quotient_model,
        source.threshold,
    )
    robust.verify_robust_plan_audit_v1(
        source.final_overlay.bridge.quotient_model,
        source.threshold,
        audit,
    )
    return complete_heldout_overlay_abstract_reuse_v1(source, query, audit)


def freeze_heldout_overlay_query_v1(
    source: source_v1.HeldoutCheckpointRecertificationResultV1,
    *,
    logical_occurrence_id: str,
    occurrence_ordinal: int,
) -> HeldoutOverlayQueryV1:
    """Verify the reusable source and freeze a query before planner access."""

    source_v1.verify_heldout_checkpoint_recertification_v1(source)
    return HeldoutOverlayQueryV1(
        _QUERY_ISSUER,
        logical_occurrence_id,
        occurrence_ordinal,
        source.result_id,
        source.final_overlay.overlay_id,
        source.context.context_id,
        source.final_overlay.bridge.quotient_model.model_id,
        source.threshold.threshold_profile_id,
    )


def complete_heldout_overlay_abstract_reuse_v1(
    source: source_v1.HeldoutCheckpointRecertificationResultV1,
    query: HeldoutOverlayQueryV1,
    audit: robust.RobustPlanAuditV1,
) -> HeldoutOverlayAbstractReuseResultV1:
    """Bind one already executed quotient audit to its frozen fresh query.

    This boundary intentionally does not replay the planner.  It is used by
    owner-bound accounting, where the single planner execution has already
    emitted all operation events.  Portable semantic replay remains the job
    of the independent bytes verifier.
    """

    if (
        type(source) is not source_v1.HeldoutCheckpointRecertificationResultV1
        or type(query) is not HeldoutOverlayQueryV1
        or type(audit) is not robust.RobustPlanAuditV1
        or query.source_result_id != source.result_id
        or query.source_overlay_id != source.final_overlay.overlay_id
        or query.context_id != source.context.context_id
        or query.quotient_model_id
        != source.final_overlay.bridge.quotient_model.model_id
        or query.threshold_profile_id != source.threshold.threshold_profile_id
    ):
        _fail("completed held-out reuse crossed its frozen source/query")
    plan = HeldoutOverlayAbstractPlanV1(
        _PLAN_ISSUER,
        query,
        source.final_overlay.audit.audit_id,
        audit,
    )
    return HeldoutOverlayAbstractReuseResultV1(
        _RESULT_ISSUER,
        source,
        query,
        plan,
    )


def verify_heldout_overlay_abstract_reuse_v1(
    claimed: HeldoutOverlayAbstractReuseResultV1,
) -> Mapping[str, Any]:
    """Replay the source binding and fresh quotient audit without ground work."""

    if type(claimed) is not HeldoutOverlayAbstractReuseResultV1:
        _fail("claimed held-out abstract reuse has the wrong concrete type")
    source_v1.verify_heldout_checkpoint_recertification_v1(claimed.source)
    if content_id(RESULT_DOMAIN, claimed._payload()) != claimed.result_id:
        _fail("held-out abstract-reuse result content ID changed")
    verification = robust.verify_robust_plan_audit_v1(
        claimed.source.final_overlay.bridge.quotient_model,
        claimed.source.threshold,
        claimed.plan.audit,
    )
    if verification.audit_id != claimed.plan.audit.audit_id:
        _fail("fresh abstract audit replay changed")
    return {
        "schema": "acfqp.construction_k7_heldout_abstract_reuse_verification.v1",
        "result_id": claimed.result_id,
        "source_result_id": claimed.source.result_id,
        "query_id": claimed.query.query_id,
        "plan_id": claimed.plan.plan_id,
        "audit_id": claimed.plan.audit.audit_id,
        "new_ground_draw_count": 0,
        "observer_call_count": 0,
        "ground_solver_invocations": 0,
        "evaluation_exact_kernel_calls": 0,
        "valid": True,
        "independent_implementation_claimed": False,
    }


__all__ = [
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7HeldoutOverlayAbstractReuseV1Error",
    "HeldoutOverlayAbstractPlanV1",
    "HeldoutOverlayAbstractReuseResultV1",
    "HeldoutOverlayQueryV1",
    "LOCAL_DOMAINS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "complete_heldout_overlay_abstract_reuse_v1",
    "freeze_heldout_overlay_query_v1",
    "run_heldout_overlay_abstract_reuse_v1",
    "verify_heldout_overlay_abstract_reuse_v1",
]
