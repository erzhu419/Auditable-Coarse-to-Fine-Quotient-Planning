"""Route provenance for a positive batched-causal V0-075 construction run.

This authority closes the positive-control chain introduced by the batched
causal acquisition successor:

``failed abstract proof -> cap-aware child-catalogue union -> learned quotient
-> contingent H=2 policy -> closed observer lifecycle -> exact total lift``.

The result selects the existing conditional FQ9 target
``ABSTRACT_CERTIFIED`` because the planner route is exactly
``ADAPTIVE_QUOTIENT``.  It remains construction-only: no semantic terminal,
CounterRecord, WorkVector, ComparisonVector, campaign closure, or official
Gate is issued.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_conditional_terminal_normalization_profile_v1 as normalization
from acfqp import v075_batch_native_total_lift_authority_v1 as total_lift
from acfqp import v075_batched_causal_occurrence_successor_v1 as successor
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_production_occurrence_plan_v1 as plan_v1
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_V075_BATCHED_CAUSAL_ROUTE_NORMALIZATION_BINDING_V1_DOMAIN,
    CONSTRUCTION_K7_V075_BATCHED_CAUSAL_ROUTE_PROVENANCE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)
from acfqp.routing_v1 import TerminalClass, TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.71"
PROFILE_KEY = "construction_k7_v075_batched_causal_route_provenance_v1"

PROVENANCE_DOMAIN = (
    CONSTRUCTION_K7_V075_BATCHED_CAUSAL_ROUTE_PROVENANCE_V1_DOMAIN
)
BINDING_DOMAIN = (
    CONSTRUCTION_K7_V075_BATCHED_CAUSAL_ROUTE_NORMALIZATION_BINDING_V1_DOMAIN
)
if {PROVENANCE_DOMAIN, BINDING_DOMAIN} - PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("batched-causal provenance domains are not central")

SOURCE_KEY = (
    "v075_production_occurrence_authority_v1:"
    "V075ProductionOccurrenceTerminalCodeV1:"
    "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE"
)
SOURCE_MEMBER_VALUE = "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE"

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

_PROVENANCE_ISSUER = object()
_BINDING_ISSUER = object()


class ConstructionK7V075BatchedCausalRouteProvenanceV1Error(ValueError):
    """The plan, batched successor, lifecycle, or exact lift changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V075BatchedCausalRouteProvenanceV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7V075BatchedCausalRouteProvenanceV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class V075BatchedCausalRouteProvenanceV1:
    _issuer: InitVar[object]
    plan_id: str
    plan_verification_id: str
    plan_entry_id: str
    occurrence_id: str
    successor_result_id: str
    successor_verification_id: str
    lifecycle_closure_id: str
    lifecycle_closure_verification_id: str
    operator_profile_id: str
    frontier_id: str
    authorization_id: str
    execution_id: str
    learned_support_graph_id: str
    quotient_id: str
    planner_result_id: str
    planner_work_id: str
    policy_id: str
    envelope_id: str
    lineage_id: str
    exact_replay_id: str
    total_lift_candidate_id: str
    total_lift_verification_id: str
    selected_causal_candidate_count: int
    materialized_child_row_count: int
    incremental_draw_count: int
    _provenance_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROVENANCE_ISSUER:
            _fail("batched-causal route provenance is caller-minted")
        for value, label in (
            (self.plan_id, "production occurrence plan"),
            (self.plan_verification_id, "production plan verification"),
            (self.plan_entry_id, "production plan entry"),
            (self.occurrence_id, "scientific occurrence"),
            (self.successor_result_id, "batched successor"),
            (self.successor_verification_id, "successor verification"),
            (self.lifecycle_closure_id, "observer lifecycle closure"),
            (self.lifecycle_closure_verification_id, "lifecycle verification"),
            (self.operator_profile_id, "batched operator profile"),
            (self.frontier_id, "failed proof frontier"),
            (self.authorization_id, "batched authorization"),
            (self.execution_id, "batched execution"),
            (self.learned_support_graph_id, "learned support graph"),
            (self.quotient_id, "observation-driven quotient"),
            (self.planner_result_id, "contingent planner result"),
            (self.planner_work_id, "planner work"),
            (self.policy_id, "contingent policy"),
            (self.envelope_id, "planner envelope"),
            (self.lineage_id, "total-lift lineage"),
            (self.exact_replay_id, "exact replay"),
            (self.total_lift_candidate_id, "total-lift candidate"),
            (self.total_lift_verification_id, "total-lift verification"),
        ):
            _cid(value, label)
        if (
            type(self.selected_causal_candidate_count) is not int
            or self.selected_causal_candidate_count <= 1
            or type(self.materialized_child_row_count) is not int
            or self.materialized_child_row_count <= 0
            or type(self.incremental_draw_count) is not int
            or self.incremental_draw_count <= 0
            or self.materialized_child_row_count > 19
            or self.incremental_draw_count > 160_960
        ):
            _fail("batched-causal provenance counts are invalid")
        object.__setattr__(
            self,
            "_provenance_id",
            content_id(PROVENANCE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_v075_batched_causal_route_provenance.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "plan_id": self.plan_id,
            "plan_verification_id": self.plan_verification_id,
            "plan_entry_id": self.plan_entry_id,
            "occurrence_id": self.occurrence_id,
            "successor_result_id": self.successor_result_id,
            "successor_verification_id": self.successor_verification_id,
            "lifecycle_closure_id": self.lifecycle_closure_id,
            "lifecycle_closure_verification_id": self.lifecycle_closure_verification_id,
            "operator_profile_id": self.operator_profile_id,
            "frontier_id": self.frontier_id,
            "authorization_id": self.authorization_id,
            "execution_id": self.execution_id,
            "learned_support_graph_id": self.learned_support_graph_id,
            "quotient_id": self.quotient_id,
            "planner_result_id": self.planner_result_id,
            "planner_work_id": self.planner_work_id,
            "policy_id": self.policy_id,
            "envelope_id": self.envelope_id,
            "lineage_id": self.lineage_id,
            "exact_replay_id": self.exact_replay_id,
            "total_lift_candidate_id": self.total_lift_candidate_id,
            "total_lift_verification_id": self.total_lift_verification_id,
            "exact_total_lift_status": "EXACT_POSITIVE_CONSTRUCTION_CONTROL",
            "planner_route": planners.V075PlannerRouteV1.ADAPTIVE_QUOTIENT.value,
            "fq9_route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
            "selected_causal_candidate_count": self.selected_causal_candidate_count,
            "materialized_child_row_count": self.materialized_child_row_count,
            "incremental_draw_count": self.incremental_draw_count,
            "failed_proof_frontier_after_operator_count": 0,
            "v1_single_candidate_no_operator_control_retained": True,
            "observation_driven_quotient_present": True,
            "multi_step_contingent_policy_present": True,
            "exact_total_lift_chain_present": True,
            "construction_fixture": True,
            "production_evidence": False,
            "scientific_endpoint_credit_allowed": False,
            "terminal_artifact_issued": False,
            "counter_records_issued": 0,
            "work_vector_id": None,
            "comparison_vector_id": None,
            "campaign_occurrence_closure_id": None,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_n_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        }

    @property
    def provenance_id(self) -> str:
        if content_id(PROVENANCE_DOMAIN, self._payload()) != self._provenance_id:
            _fail("batched-causal route provenance changed after issuance")
        return self._provenance_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_provenance_id": self.provenance_id}


@dataclass(frozen=True, slots=True)
class V075BatchedCausalRouteNormalizationBindingV1:
    _issuer: InitVar[object]
    provenance: V075BatchedCausalRouteProvenanceV1
    normalization_evidence: normalization.ConditionalNormalizationEvidenceV1
    normalization_result: normalization.ConditionalNormalizationResultV1
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BINDING_ISSUER
            or type(self.provenance) is not V075BatchedCausalRouteProvenanceV1
            or type(self.normalization_evidence)
            is not normalization.ConditionalNormalizationEvidenceV1
            or type(self.normalization_result)
            is not normalization.ConditionalNormalizationResultV1
        ):
            _fail("batched-causal normalization binding is caller-minted")
        evidence = self.normalization_evidence
        result = self.normalization_result
        if (
            evidence.kind
            is not normalization.NormalizationEvidenceKindV1.PLAN_ROUTE_PROVENANCE
            or evidence.route_kind is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
            or evidence.route_provenance_evidence_id != self.provenance.provenance_id
            or result.source_key != SOURCE_KEY
            or result.member_value != SOURCE_MEMBER_VALUE
            or result.evidence_id != evidence.evidence_id
            or result.outcome
            is not normalization.ConditionalNormalizationOutcomeV1
            .FQ9_TARGET_SELECTED_REQUIRES_TERMINAL_AUTHORITY
            or result.fq9_terminal_class is not TerminalClass.PLAN_CERTIFICATE
            or result.fq9_terminal_code is not TerminalCode.ABSTRACT_CERTIFIED
            or result.terminal_artifact_issued is not False
            or result.downstream_semantic_terminal_authority_required is not True
        ):
            _fail("batched-causal route did not select the exact abstract target")
        object.__setattr__(
            self,
            "_binding_id",
            content_id(BINDING_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_v075_batched_causal_route_normalization_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "route_provenance_id": self.provenance.provenance_id,
            "conditional_normalization_evidence_id": self.normalization_evidence.evidence_id,
            "conditional_normalization_result_id": self.normalization_result.result_id,
            "fq9_route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
            "selected_fq9_terminal_class": TerminalClass.PLAN_CERTIFICATE.value,
            "selected_fq9_terminal_code": TerminalCode.ABSTRACT_CERTIFIED.value,
            "downstream_semantic_terminal_authority_required": True,
            "terminal_artifact_issued": False,
            "counter_records_issued": 0,
            "official_execution_allowed": False,
        }

    @property
    def binding_id(self) -> str:
        if content_id(BINDING_DOMAIN, self._payload()) != self._binding_id:
            _fail("batched-causal normalization binding changed")
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "route_provenance": self.provenance.to_document(),
            "conditional_normalization_evidence": self.normalization_evidence.to_document(),
            "conditional_normalization_result": self.normalization_result.to_document(),
            "route_normalization_binding_id": self.binding_id,
        }


def issue_v075_batched_causal_route_provenance_v1(
    *,
    repository_root: str | Path,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    plan: plan_v1.V075ProductionOccurrencePlanV1,
    plan_entry: plan_v1.V075ProductionOccurrencePlanEntryV1,
    occurrence_result: successor.V075BatchedCausalOccurrencePrecloseResultV1,
    sealed_lifecycle: lifecycle.V075SealedMultistageOccurrenceLifecycleV1,
    lineage: total_lift.V075BatchNativeLineageBindingV1,
    exact_replay: total_lift.V075BatchNativeConstructionExactReplayV1,
    total_lift_verification: total_lift.V075BatchNativeConstructionTotalLiftVerificationV1,
) -> V075BatchedCausalRouteNormalizationBindingV1:
    """Independently replay a positive construction chain and select FQ9."""

    if (
        type(namespace) is not public.V075PublicTargetTapeNamespaceV1
        or type(plan) is not plan_v1.V075ProductionOccurrencePlanV1
        or type(plan_entry) is not plan_v1.V075ProductionOccurrencePlanEntryV1
        or type(occurrence_result)
        is not successor.V075BatchedCausalOccurrencePrecloseResultV1
        or type(sealed_lifecycle)
        is not lifecycle.V075SealedMultistageOccurrenceLifecycleV1
        or type(lineage) is not total_lift.V075BatchNativeLineageBindingV1
        or type(exact_replay)
        is not total_lift.V075BatchNativeConstructionExactReplayV1
        or type(total_lift_verification)
        is not total_lift.V075BatchNativeConstructionTotalLiftVerificationV1
    ):
        _fail("batched-causal provenance inputs are not exact typed authorities")
    expected_plan, plan_verification = plan_v1.verify_v075_production_occurrence_plan_bytes_v1(
        repository_root=repository_root,
        namespace=namespace,
        raw=plan.canonical_bytes,
    )
    occurrence_verification = successor.verify_v075_batched_causal_occurrence_successor_v1(
        occurrence_result
    )
    expected_lineage = total_lift.freeze_v075_batch_native_total_lift_lineage_v1(
        backend_result=occurrence_result.final_backend_result,
        planner_result=occurrence_result.final_planner_result,
        sealed_lifecycle=sealed_lifecycle,
    )
    exact_verification = total_lift.verify_v075_batch_native_construction_total_lift_candidate_v1(
        lineage=lineage,
        exact_replay=exact_replay,
        claimed=total_lift_verification.candidate,
    )
    planner = occurrence_result.final_planner_result
    if (
        expected_plan != plan
        or plan_entry not in plan.entries
        or plan_entry.occurrence_identity != occurrence_result.occurrence_identity
        or plan_entry.occurrence_id != occurrence_result.occurrence_identity.occurrence_id
        or plan_entry.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        or occurrence_verification.outcome
        is not successor.V075BatchedCausalOccurrenceOutcomeV1
        .CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT
        or expected_lineage != lineage
        or exact_replay.lineage_id != lineage.lineage_id
        or exact_verification.candidate.candidate_id
        != total_lift_verification.candidate.candidate_id
        or total_lift_verification.candidate.status
        is not total_lift.V075BatchTotalLiftConstructionStatusV1
        .EXACT_POSITIVE_CONSTRUCTION_CONTROL
        or planner.route is not planners.V075PlannerRouteV1.ADAPTIVE_QUOTIENT
        or planner.quotient is None
        or planner.policy is None
        or planner.envelope is None
        or planner.ready_for_exact_total_lift is not True
        or planner.diagnostic_failed_frontier_row_ids
        or lineage.envelope.policy.planner_result != planner
        or sealed_lifecycle.closure.occurrence_id
        != occurrence_result.occurrence_identity.occurrence_id
    ):
        _fail("batched-causal positive route chain failed exact replay")
    provenance = V075BatchedCausalRouteProvenanceV1(
        _PROVENANCE_ISSUER,
        plan.plan_id,
        plan_verification.verification_id,
        plan_entry.entry_id,
        occurrence_result.occurrence_identity.occurrence_id,
        occurrence_result.result_id,
        occurrence_verification.verification_id,
        sealed_lifecycle.closure.closure_id,
        sealed_lifecycle.verification.verification_id,
        occurrence_result.authorization.profile.profile_id,
        occurrence_result.frontier.frontier_id,
        occurrence_result.authorization.authorization_id,
        occurrence_result.execution.execution_id,
        planner.graph.graph_id,
        planner.quotient.quotient_id,
        planner.result_id,
        planner.work.work_id,
        planner.policy.policy_id,
        planner.envelope.envelope_id,
        lineage.lineage_id,
        exact_replay.replay_id,
        total_lift_verification.candidate.candidate_id,
        total_lift_verification.verification_id,
        len(occurrence_result.authorization.selected_candidate_ids),
        len(occurrence_result.authorization.selected_child_row_ids),
        occurrence_result.authorization.incremental_draw_count,
    )
    profile = normalization.freeze_construction_k7_conditional_terminal_normalization_profile_v1()
    evidence = normalization.ConditionalNormalizationEvidenceV1.plan_route(
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        provenance.provenance_id,
    )
    result = normalization.normalize_v075_profile_extension_status_v1(
        profile=profile,
        source_key=SOURCE_KEY,
        member_value=SOURCE_MEMBER_VALUE,
        evidence=evidence,
    )
    return V075BatchedCausalRouteNormalizationBindingV1(
        _BINDING_ISSUER,
        provenance,
        evidence,
        result,
    )


__all__ = [
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "PROFILE_KEY",
    "V075BatchedCausalRouteNormalizationBindingV1",
    "V075BatchedCausalRouteProvenanceV1",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "issue_v075_batched_causal_route_provenance_v1",
]
