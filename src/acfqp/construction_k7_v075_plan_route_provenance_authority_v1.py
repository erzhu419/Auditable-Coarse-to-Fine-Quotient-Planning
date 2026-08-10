"""Exact V075 planner-route provenance for conditional FQ9 normalization.

The V075 occurrence authority already proves an exact positive total lift, but
its historical terminal string does not say whether the certified policy came
from the reusable observation-driven quotient or from matched direct-ground
planning.  Contract 2.0.70 binds that missing fact to the exact occurrence,
planner, policy, envelope, lifecycle, and total-lift chain.

This module only supplies route-provenance evidence to the existing
conditional-normalization profile:

* ``ADAPTIVE_QUOTIENT`` selects ``ABSTRACT_ONLY_CERTIFICATE``;
* ``MATCHED_DIRECT_GROUND`` selects ``DIRECT_FALLBACK``.

It never turns a construction fixture into production evidence, never mints a
terminal artifact, and emits no accounting vector or campaign closure.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_conditional_terminal_normalization_profile_v1 as normalization_v1
from acfqp import v075_batch_native_total_lift_authority_v1 as total_lift_v1
from acfqp import v075_learned_support_quotient_planners_v1 as planners_v1
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle_v1
from acfqp import v075_production_occurrence_authority_v1 as occurrence_v1
from acfqp import v075_public_campaign_authority_v1 as public_v1
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_V075_PLAN_ROUTE_NORMALIZATION_BINDING_V1_DOMAIN,
    CONSTRUCTION_K7_V075_PLAN_ROUTE_PROVENANCE_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_V075_PLAN_ROUTE_PROVENANCE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.routing_v1 import TerminalClass, TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.70"
PROFILE_KEY = "construction_k7_v075_plan_route_provenance_authority_v1"

PROVENANCE_DOMAIN = CONSTRUCTION_K7_V075_PLAN_ROUTE_PROVENANCE_V1_DOMAIN
BINDING_DOMAIN = (
    CONSTRUCTION_K7_V075_PLAN_ROUTE_NORMALIZATION_BINDING_V1_DOMAIN
)
REPLAY_DOMAIN = CONSTRUCTION_K7_V075_PLAN_ROUTE_PROVENANCE_REPLAY_V1_DOMAIN
LOCAL_DOMAINS = frozenset({PROVENANCE_DOMAIN, BINDING_DOMAIN, REPLAY_DOMAIN})
if len(LOCAL_DOMAINS) != 3 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("V075 plan-route provenance domains are not central")

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
_REPLAY_ISSUER = object()


class ConstructionK7V075PlanRouteProvenanceV1Error(ValueError):
    """One positive occurrence or its exact route lineage changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V075PlanRouteProvenanceV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7V075PlanRouteProvenanceV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _verification_id(
    result: occurrence_v1.V075ProductionOccurrenceAuthorityResultV1,
) -> str:
    verified = result.total_lift_verification
    if type(verified) is total_lift_v1.V075BatchNativeConstructionTotalLiftVerificationV1:
        return verified.verification_id
    if type(verified) is total_lift_v1.V075BatchNativeProductionTotalLiftResultV1:
        return verified.result_id
    _fail("positive occurrence lacks one exact total-lift verification")


def _expected_route(
    planner_route: planners_v1.V075PlannerRouteV1,
) -> RouteKindEnum:
    if planner_route is planners_v1.V075PlannerRouteV1.ADAPTIVE_QUOTIENT:
        return RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
    if planner_route is planners_v1.V075PlannerRouteV1.MATCHED_DIRECT_GROUND:
        return RouteKindEnum.DIRECT_FALLBACK
    _fail("planner route has no explicit FQ9 provenance mapping")


def _expected_terminal(route: RouteKindEnum) -> TerminalCode:
    if route is RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE:
        return TerminalCode.ABSTRACT_CERTIFIED
    if route is RouteKindEnum.DIRECT_FALLBACK:
        return TerminalCode.FULL_GROUND_FALLBACK
    _fail("route provenance selected an unsupported FQ9 plan code")


@dataclass(frozen=True, slots=True)
class V075PlanRouteProvenanceV1:
    """Exact route identity extracted from one independently replayed plan."""

    _issuer: InitVar[object]
    authority_scope: lifecycle_v1.V075LifecycleAuthorityScopeV1
    occurrence_result_id: str
    occurrence_verification_id: str
    occurrence_id: str
    plan_id: str
    plan_entry_id: str
    ipc_result_id: str
    ipc_actual_work_id: str
    lifecycle_closure_id: str
    learned_support_graph_id: str
    planner_result_id: str
    planner_work_id: str
    policy_id: str
    envelope_id: str
    quotient_id: str | None
    lineage_id: str
    exact_replay_id: str
    total_lift_candidate_id: str
    total_lift_verification_id: str
    exact_total_lift_status: str
    planner_route: planners_v1.V075PlannerRouteV1
    route_kind: RouteKindEnum
    construction_fixture: bool
    production_evidence: bool
    _provenance_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROVENANCE_ISSUER:
            _fail("plan-route provenance is caller-minted")
        for value, label in (
            (self.occurrence_result_id, "occurrence result"),
            (self.occurrence_verification_id, "occurrence verification"),
            (self.occurrence_id, "occurrence"),
            (self.plan_id, "occurrence plan"),
            (self.plan_entry_id, "plan entry"),
            (self.ipc_result_id, "IPC result"),
            (self.ipc_actual_work_id, "IPC actual work"),
            (self.lifecycle_closure_id, "lifecycle closure"),
            (self.learned_support_graph_id, "learned support graph"),
            (self.planner_result_id, "planner result"),
            (self.planner_work_id, "planner work"),
            (self.policy_id, "planner policy"),
            (self.envelope_id, "planner envelope"),
            (self.lineage_id, "total-lift lineage"),
            (self.exact_replay_id, "exact replay"),
            (self.total_lift_candidate_id, "total-lift candidate"),
            (self.total_lift_verification_id, "total-lift verification"),
        ):
            _cid(value, label)
        if self.quotient_id is not None:
            _cid(self.quotient_id, "observation-driven quotient")
        try:
            scope = lifecycle_v1.V075LifecycleAuthorityScopeV1(
                self.authority_scope
            )
            planner_route = planners_v1.V075PlannerRouteV1(self.planner_route)
            route_kind = RouteKindEnum(self.route_kind)
        except (TypeError, ValueError) as error:
            raise ConstructionK7V075PlanRouteProvenanceV1Error(
                "plan-route provenance enum changed"
            ) from error
        object.__setattr__(self, "authority_scope", scope)
        object.__setattr__(self, "planner_route", planner_route)
        object.__setattr__(self, "route_kind", route_kind)
        if (
            route_kind is not _expected_route(planner_route)
            or self.construction_fixture
            is not (scope is lifecycle_v1.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY)
            or self.production_evidence
            is not (scope is lifecycle_v1.V075LifecycleAuthorityScopeV1.PRODUCTION)
            or self.construction_fixture == self.production_evidence
            or type(self.exact_total_lift_status) is not str
            or self.exact_total_lift_status
            not in {
                "EXACT_POSITIVE_CONSTRUCTION_CONTROL",
                "EXACT_POSITIVE_PRODUCTION_CANDIDATE",
            }
            or (
                self.construction_fixture
                and self.exact_total_lift_status
                != "EXACT_POSITIVE_CONSTRUCTION_CONTROL"
            )
            or (
                self.production_evidence
                and self.exact_total_lift_status
                != "EXACT_POSITIVE_PRODUCTION_CANDIDATE"
            )
            or (
                route_kind is RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
                and self.quotient_id is None
            )
            or (
                route_kind is RouteKindEnum.DIRECT_FALLBACK
                and self.quotient_id is not None
            )
        ):
            _fail("positive route provenance is inconsistent")
        object.__setattr__(
            self,
            "_provenance_id",
            content_id(PROVENANCE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_v075_plan_route_provenance.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_scope": self.authority_scope.value,
            "occurrence_result_id": self.occurrence_result_id,
            "occurrence_verification_id": self.occurrence_verification_id,
            "occurrence_id": self.occurrence_id,
            "plan_id": self.plan_id,
            "plan_entry_id": self.plan_entry_id,
            "ipc_result_id": self.ipc_result_id,
            "ipc_actual_work_id": self.ipc_actual_work_id,
            "lifecycle_closure_id": self.lifecycle_closure_id,
            "learned_support_graph_id": self.learned_support_graph_id,
            "planner_result_id": self.planner_result_id,
            "planner_work_id": self.planner_work_id,
            "policy_id": self.policy_id,
            "envelope_id": self.envelope_id,
            "quotient_id": self.quotient_id,
            "lineage_id": self.lineage_id,
            "exact_replay_id": self.exact_replay_id,
            "total_lift_candidate_id": self.total_lift_candidate_id,
            "total_lift_verification_id": self.total_lift_verification_id,
            "exact_total_lift_status": self.exact_total_lift_status,
            "source_terminal_class": "PLAN_CERTIFICATE",
            "source_terminal_code": SOURCE_MEMBER_VALUE,
            "planner_route": self.planner_route.value,
            "fq9_route_kind": self.route_kind.value,
            "construction_fixture": self.construction_fixture,
            "production_evidence": self.production_evidence,
            "observation_driven_quotient_present": self.quotient_id is not None,
            "matched_direct_ground_present": (
                self.route_kind is RouteKindEnum.DIRECT_FALLBACK
            ),
            "host_operational_planner_replays": 0,
            "exact_total_lift_chain_present": True,
            "route_provenance_only": True,
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
        return self._provenance_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_provenance_id": self.provenance_id}


@dataclass(frozen=True, slots=True)
class V075PlanRouteNormalizationBindingV1:
    """One exact route-provenance artifact and its conditional target."""

    _issuer: InitVar[object]
    provenance: V075PlanRouteProvenanceV1
    normalization_evidence: normalization_v1.ConditionalNormalizationEvidenceV1
    normalization_result: normalization_v1.ConditionalNormalizationResultV1
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BINDING_ISSUER
            or type(self.provenance) is not V075PlanRouteProvenanceV1
            or type(self.normalization_evidence)
            is not normalization_v1.ConditionalNormalizationEvidenceV1
            or type(self.normalization_result)
            is not normalization_v1.ConditionalNormalizationResultV1
        ):
            _fail("route-normalization binding is caller-minted")
        evidence = self.normalization_evidence
        result = self.normalization_result
        expected_terminal = _expected_terminal(self.provenance.route_kind)
        if (
            evidence.kind
            is not normalization_v1.NormalizationEvidenceKindV1.PLAN_ROUTE_PROVENANCE
            or evidence.route_kind is not self.provenance.route_kind
            or evidence.route_provenance_evidence_id
            != self.provenance.provenance_id
            or result.source_key != SOURCE_KEY
            or result.member_value != SOURCE_MEMBER_VALUE
            or result.evidence_id != evidence.evidence_id
            or result.outcome
            is not normalization_v1.ConditionalNormalizationOutcomeV1
            .FQ9_TARGET_SELECTED_REQUIRES_TERMINAL_AUTHORITY
            or result.fq9_terminal_class is not TerminalClass.PLAN_CERTIFICATE
            or result.fq9_terminal_code is not expected_terminal
            or result.terminal_artifact_issued is not False
            or result.downstream_semantic_terminal_authority_required is not True
        ):
            _fail("conditional normalization was not bound to the exact route")
        object.__setattr__(
            self,
            "_binding_id",
            content_id(BINDING_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.construction_k7_v075_plan_route_normalization_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "route_provenance_id": self.provenance.provenance_id,
            "conditional_normalization_evidence_id": (
                self.normalization_evidence.evidence_id
            ),
            "conditional_normalization_result_id": (
                self.normalization_result.result_id
            ),
            "conditional_normalization_profile_id": (
                self.normalization_result.profile_id
            ),
            "conditional_normalization_rule_id": (
                self.normalization_result.rule_id
            ),
            "source_key": SOURCE_KEY,
            "source_member_value": SOURCE_MEMBER_VALUE,
            "fq9_route_kind": self.provenance.route_kind.value,
            "selected_fq9_terminal_class": TerminalClass.PLAN_CERTIFICATE.value,
            "selected_fq9_terminal_code": (
                self.normalization_result.fq9_terminal_code.value
            ),
            "normalization_only": True,
            "downstream_semantic_terminal_authority_required": True,
            "terminal_artifact_issued": False,
            "construction_fixture": self.provenance.construction_fixture,
            "production_evidence": self.provenance.production_evidence,
            "counter_records_issued": 0,
            "official_execution_allowed": False,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "route_provenance": self.provenance.to_document(),
            "conditional_normalization_evidence": (
                self.normalization_evidence.to_document()
            ),
            "conditional_normalization_result": (
                self.normalization_result.to_document()
            ),
            "route_normalization_binding_id": self.binding_id,
        }


def issue_v075_plan_route_provenance_v1(
    *,
    repository_root: str | Path,
    namespace: public_v1.V075PublicTargetTapeNamespaceV1,
    occurrence_result: occurrence_v1.V075ProductionOccurrenceAuthorityResultV1,
) -> V075PlanRouteNormalizationBindingV1:
    """Replay one positive occurrence and bind its exact planner route."""

    if (
        type(namespace) is not public_v1.V075PublicTargetTapeNamespaceV1
        or type(occurrence_result)
        is not occurrence_v1.V075ProductionOccurrenceAuthorityResultV1
    ):
        _fail("route provenance requires exact namespace and occurrence types")
    verification = occurrence_v1.verify_v075_production_occurrence_authority_result_v1(
        repository_root=repository_root,
        namespace=namespace,
        claimed=occurrence_result,
    )
    loaded = occurrence_result.operational_load
    lifecycle = occurrence_result.sealed_lifecycle
    lineage = occurrence_result.lineage
    exact_replay = occurrence_result.exact_replay
    candidate = occurrence_result.total_lift_candidate
    if (
        occurrence_result.terminal_class
        is not occurrence_v1.V075ProductionOccurrenceTerminalClassV1.PLAN_CERTIFICATE
        or occurrence_result.terminal_code
        is not occurrence_v1.V075ProductionOccurrenceTerminalCodeV1
        .EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE
        or occurrence_result.exact_valid_total_lift_plan is not True
        or verification.exact_chain_present is not True
        or verification.operational_transport_present is not True
        or verification.host_operational_planner_replay_count != 0
        or loaded is None
        or lifecycle is None
        or lineage is None
        or exact_replay is None
        or candidate is None
    ):
        _fail("route provenance requires one independently verified positive lift")
    planner = loaded.planner_result
    if (
        type(planner) is not planners_v1.V075SupportPlannerResultV1
        or planner.ready_for_exact_total_lift is not True
        or planner.policy is None
        or planner.envelope is None
        or occurrence_result.ipc_result.route != planner.route.value
        or lineage.envelope.policy.planner_result != planner
    ):
        _fail("positive occurrence planner route or policy lineage changed")
    route_kind = _expected_route(planner.route)
    arm = occurrence_result.plan_entry.arm
    if (
        route_kind is RouteKindEnum.DIRECT_FALLBACK
        and arm is not worker_v1.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    ) or (
        route_kind is RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        and arm is worker_v1.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    ):
        _fail("planner route disagrees with the preregistered occurrence arm")
    quotient_id = None if planner.quotient is None else planner.quotient.quotient_id
    provenance = V075PlanRouteProvenanceV1(
        _PROVENANCE_ISSUER,
        occurrence_result.authority_scope,
        occurrence_result.result_id,
        verification.verification_id,
        occurrence_result.occurrence_id,
        occurrence_result.plan.plan_id,
        occurrence_result.plan_entry.entry_id,
        occurrence_result.ipc_result.result_id,
        occurrence_result.ipc_result.actual_work.work_id,
        lifecycle.closure.closure_id,
        planner.graph.graph_id,
        planner.result_id,
        planner.work.work_id,
        planner.policy.policy_id,
        planner.envelope.envelope_id,
        quotient_id,
        lineage.lineage_id,
        exact_replay.replay_id,
        candidate.candidate_id,
        _verification_id(occurrence_result),
        candidate.status.value,
        planner.route,
        route_kind,
        occurrence_result.authority_scope
        is lifecycle_v1.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY,
        occurrence_result.authority_scope
        is lifecycle_v1.V075LifecycleAuthorityScopeV1.PRODUCTION,
    )
    profile = (
        normalization_v1.freeze_construction_k7_conditional_terminal_normalization_profile_v1()
    )
    evidence = normalization_v1.ConditionalNormalizationEvidenceV1.plan_route(
        route_kind,
        provenance.provenance_id,
    )
    normalized = normalization_v1.normalize_v075_profile_extension_status_v1(
        profile=profile,
        source_key=SOURCE_KEY,
        member_value=SOURCE_MEMBER_VALUE,
        evidence=evidence,
    )
    return V075PlanRouteNormalizationBindingV1(
        _BINDING_ISSUER,
        provenance,
        evidence,
        normalized,
    )


class V075PlanRouteProvenanceReplayOutcomeV1(str, Enum):
    VERIFIED = "EXACT_PLAN_ROUTE_PROVENANCE_VERIFIED"
    DOCUMENT_BLOCKED = "PLAN_ROUTE_PROVENANCE_DOCUMENT_BLOCKED"


@dataclass(frozen=True, slots=True)
class V075PlanRouteProvenanceReplayV1:
    _issuer: InitVar[object]
    raw_sha256: str
    occurrence_result_id: str
    outcome: V075PlanRouteProvenanceReplayOutcomeV1
    route_normalization_binding_id: str | None
    fq9_route_kind: RouteKindEnum | None
    selected_fq9_terminal_code: TerminalCode | None
    blocker_codes: tuple[str, ...]
    _replay_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPLAY_ISSUER:
            _fail("plan-route provenance replay is caller-minted")
        _cid(self.raw_sha256, "route-provenance document digest")
        _cid(self.occurrence_result_id, "occurrence result")
        try:
            outcome = V075PlanRouteProvenanceReplayOutcomeV1(self.outcome)
        except (TypeError, ValueError) as error:
            raise ConstructionK7V075PlanRouteProvenanceV1Error(
                "route-provenance replay outcome changed"
            ) from error
        object.__setattr__(self, "outcome", outcome)
        blockers = tuple(self.blocker_codes)
        object.__setattr__(self, "blocker_codes", blockers)
        if outcome is V075PlanRouteProvenanceReplayOutcomeV1.VERIFIED:
            _cid(self.route_normalization_binding_id, "route-normalization binding")
            if (
                type(self.fq9_route_kind) is not RouteKindEnum
                or type(self.selected_fq9_terminal_code) is not TerminalCode
                or blockers
            ):
                _fail("verified route-provenance replay is incomplete")
        elif (
            self.route_normalization_binding_id is not None
            or self.fq9_route_kind is not None
            or self.selected_fq9_terminal_code is not None
            or not blockers
        ):
            _fail("blocked route-provenance replay retained authority")
        object.__setattr__(
            self,
            "_replay_id",
            content_id(REPLAY_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_v075_plan_route_provenance_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "raw_sha256": self.raw_sha256,
            "occurrence_result_id": self.occurrence_result_id,
            "outcome": self.outcome.value,
            "route_normalization_binding_id": self.route_normalization_binding_id,
            "fq9_route_kind": (
                None if self.fq9_route_kind is None else self.fq9_route_kind.value
            ),
            "selected_fq9_terminal_code": (
                None
                if self.selected_fq9_terminal_code is None
                else self.selected_fq9_terminal_code.value
            ),
            "blocker_codes": list(self.blocker_codes),
            "semantic_occurrence_replay_performed": True,
            "terminal_artifact_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def replay_id(self) -> str:
        return self._replay_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "replay_id": self.replay_id}


def verify_v075_plan_route_provenance_bytes_v1(
    raw: bytes,
    *,
    repository_root: str | Path,
    namespace: public_v1.V075PublicTargetTapeNamespaceV1,
    occurrence_result: occurrence_v1.V075ProductionOccurrenceAuthorityResultV1,
) -> V075PlanRouteProvenanceReplayV1:
    """Regenerate the full binding; reject altered or noncanonical bytes."""

    raw_sha256 = hashlib.sha256(raw if type(raw) is bytes else b"").hexdigest()
    try:
        if type(raw) is not bytes or not raw:
            _fail("route-provenance document bytes are empty or mistyped")
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            _fail("route-provenance document is not exact canonical JSON")
        expected = issue_v075_plan_route_provenance_v1(
            repository_root=repository_root,
            namespace=namespace,
            occurrence_result=occurrence_result,
        )
        if expected.canonical_bytes != raw:
            _fail("route-provenance document differs from semantic replay")
    except (TypeError, ValueError, ConstructionK7V075PlanRouteProvenanceV1Error):
        return V075PlanRouteProvenanceReplayV1(
            _REPLAY_ISSUER,
            raw_sha256,
            occurrence_result.result_id,
            V075PlanRouteProvenanceReplayOutcomeV1.DOCUMENT_BLOCKED,
            None,
            None,
            None,
            ("SEMANTIC_REPLAY_OR_CANONICAL_DOCUMENT_MISMATCH",),
        )
    return V075PlanRouteProvenanceReplayV1(
        _REPLAY_ISSUER,
        raw_sha256,
        occurrence_result.result_id,
        V075PlanRouteProvenanceReplayOutcomeV1.VERIFIED,
        expected.binding_id,
        expected.provenance.route_kind,
        expected.normalization_result.fq9_terminal_code,
        (),
    )


__all__ = [
    "BINDING_DOMAIN",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7V075PlanRouteProvenanceV1Error",
    "LOCAL_DOMAINS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "PROVENANCE_DOMAIN",
    "REPLAY_DOMAIN",
    "SCHEMA_VERSION",
    "SOURCE_KEY",
    "SOURCE_MEMBER_VALUE",
    "V075PlanRouteNormalizationBindingV1",
    "V075PlanRouteProvenanceReplayOutcomeV1",
    "V075PlanRouteProvenanceReplayV1",
    "V075PlanRouteProvenanceV1",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "issue_v075_plan_route_provenance_v1",
    "verify_v075_plan_route_provenance_bytes_v1",
]
