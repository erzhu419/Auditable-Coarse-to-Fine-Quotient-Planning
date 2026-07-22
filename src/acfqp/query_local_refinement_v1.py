"""Certificate-triggered query-local evidence and immutable RAPM refinement.

V0-046 is deliberately narrow.  It handles the registered LMB H1 control in
which the selected typed V0-044 plan fails independent typed V0-043 audit only
because one reachable semantic realization contains four missing ground rows.
The request authority proves row-by-row necessity under the frozen H1,
zero-risk, fixed-plan, fixed-concretizer uncertainty semantics.  A separate
executor then performs exactly the authorized kernel calls, constructs a
query-owned V2 model without mutating the reusable V0-045 base, replans in that
model, and independently audits the selected plan.

This module does not claim general causal minimality, promotion into the base
model, sample efficiency, or an unknown-domain acquisition strategy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import inspect
from itertools import product
from typing import Any, Mapping

from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
)
from acfqp.observation_partial_rapm_v1 import (
    AmbiguityRowStatus,
    CanonicalGroundActionV1,
    CanonicalStateObservationV1,
    DeterministicObservationProfileV1,
    EvidenceClass,
    EvidenceLane,
    ObservationCoverageV1,
    ObservationLogManifestV1,
    ObservedSuccessorRefV1,
    PartialGroundRowV1,
    PartialSemanticRealizationV1,
    PlanningKind,
    PreregisteredObservationAuthorityV1,
    QueryScopedPartialRAPMV2,
    SuccessorKind,
    _ambiguity_payload,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    ObservedTypedPartialRAPMResultV1,
)
from acfqp.partial_model_planner_v1 import (
    PRODUCTION_CANDIDATE_CAP,
    PRODUCTION_CAP_PROFILE_ID,
    PartialModelPlannerOutcome,
    PartialModelPlannerSelectionMode,
    PartialPlannerCandidateSummaryV1,
    PartialPlannerCellActionDomainV1,
    TypedPartialModelPlanProposalResultV2,
    _candidate_summary,
    _planner_context,
    _selected_summary,
    _stage_assignments,
    verify_partial_model_plan_from_observed_synthesis_v2,
)
from acfqp.partial_sound_audit_v1 import (
    ContingentPlanStageV1,
    FailedProofReason,
    FrozenContingentAbstractPlanV1,
    FrozenPartialAuditThresholdsV1,
    PartialAuditOutcome,
    PartialSoundAuditResultV1,
    TypedPartialSoundAuditResultV2,
    _audit_verified_partial_model_v1,
    verify_partial_fixed_plan_audit_from_observed_synthesis_v2,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "lmb_h1_query_local_exact_row_refinement_v0"
CANONICAL_STRUCTURAL_ID = (
    "eb4d4562d979fe6312fe8c7876176b6a8c6e99ee859e5da67e53ea2fac7a76e8"
)
KERNEL_IMPLEMENTATION_SHA256 = (
    "fa38ca4724420cc9834a50ee83b57a97721434404a9e76f0994b1aecb22b5323"
)
EXPECTED_TILE_TYPES = (0, 1, 0, 1, 1, 0)
EXPECTED_BLOCKERS = (
    frozenset(),
    frozenset(),
    frozenset((0, 1)),
    frozenset((0, 1)),
    frozenset((0, 1)),
    frozenset((0, 1)),
)
EXPECTED_TYPE_COUNT = 2
EXPECTED_CAPACITY = 3
EXPECTED_MAX_LAYERS = 2

DOMAIN_TAGS = {
    "kernel_spec": "acfqp:lmb-query-local-kernel-spec:v1",
    "kernel_authority": "acfqp:lmb-query-local-kernel-authority:v1",
    "row_proof": "acfqp:query-local-row-necessity-proof:v1",
    "request": "acfqp:query-local-evidence-request:v1",
    "receipt": "acfqp:query-local-evidence-receipt:v1",
    "evidence": "acfqp:query-local-transition-evidence:v1",
    "ledger": "acfqp:query-local-evidence-ledger:v1",
    "bundle": "acfqp:query-local-evidence-bundle:v1",
    "overlay_context": "acfqp:query-local-overlay-context:v1",
    "build_epoch": "acfqp:query-local-build-epoch:v1",
    "build": "acfqp:query-local-overlay-build:v1",
    "threshold_rebase": "acfqp:query-local-threshold-rebase:v1",
    "planner": "acfqp:query-local-plan-proposal:v1",
    "audit": "acfqp:query-local-plan-audit:v1",
    "promotion": "acfqp:query-local-promotion-disposition:v1",
    "result": "acfqp:query-local-refinement-result:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("query-local refinement content domains must be unique")


class QueryLocalRefinementInvariantViolation(ValueError):
    """The failed-certificate, evidence, overlay, or replay chain is invalid."""


class QueryLocalRefinementStatus(str, Enum):
    QUERY_LOCAL_PLAN_CERTIFIED = "QUERY_LOCAL_PLAN_CERTIFIED"
    QUERY_LOCAL_PLAN_NOT_CERTIFIED = "QUERY_LOCAL_PLAN_NOT_CERTIFIED"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, TypeError, ValueError) as error:
        raise QueryLocalRefinementInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise QueryLocalRefinementInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise QueryLocalRefinementInvariantViolation(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field: str) -> Fraction:
    if type(value) not in (int, Fraction):
        raise QueryLocalRefinementInvariantViolation(f"{field} must be exact")
    return Fraction(value)


def _fraction_document(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _sorted_ids(values: Any, field: str, *, nonempty: bool = True) -> tuple[str, ...]:
    if type(values) is not tuple or any(type(item) is not str for item in values):
        raise QueryLocalRefinementInvariantViolation(
            f"{field} must be an exact tuple of content IDs"
        )
    for item in values:
        _cid(item, field)
    if values != tuple(sorted(set(values))) or (nonempty and not values):
        raise QueryLocalRefinementInvariantViolation(
            f"{field} must be unique, sorted, and appropriately nonempty"
        )
    return values


def _kernel_source_digest() -> str:
    return hashlib.sha256(
        "\n\x00\n".join(
            inspect.getsource(function)
            for function in (
                LMBKernel._validate_state,
                LMBKernel.actions,
                LMBKernel.step,
            )
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class LMBQueryKernelAuthorityV1:
    structural_id: str
    tile_types: tuple[int, ...]
    blockers: tuple[frozenset[int], ...]
    type_count: int
    capacity: int
    max_layers: int
    implementation_sha256: str = KERNEL_IMPLEMENTATION_SHA256
    authority_kind: str = "IN_MEMORY_EXACT_LMB_KERNEL_AUTHORITY_V1"
    transport_authority_claimed: bool = False

    def __post_init__(self) -> None:
        _cid(self.structural_id, "kernel authority structural ID")
        if (
            self.structural_id != CANONICAL_STRUCTURAL_ID
            or self.tile_types != EXPECTED_TILE_TYPES
            or self.blockers != EXPECTED_BLOCKERS
            or self.type_count != EXPECTED_TYPE_COUNT
            or self.capacity != EXPECTED_CAPACITY
            or self.max_layers != EXPECTED_MAX_LAYERS
            or self.implementation_sha256 != KERNEL_IMPLEMENTATION_SHA256
            or self.authority_kind != "IN_MEMORY_EXACT_LMB_KERNEL_AUTHORITY_V1"
            or self.transport_authority_claimed is not False
        ):
            raise QueryLocalRefinementInvariantViolation(
                "query-local kernel authority differs from the frozen LMB control"
            )
        _cid(self.implementation_sha256, "kernel implementation digest")

    def _kernel_spec_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.lmb_query_local_kernel_spec.v1",
            "tile_types": list(self.tile_types),
            "blockers": [sorted(item) for item in self.blockers],
            "type_count": self.type_count,
            "capacity": self.capacity,
            "max_layers": self.max_layers,
        }

    @property
    def kernel_spec_id(self) -> str:
        return _content_id("kernel_spec", self._kernel_spec_payload())

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.lmb_query_local_kernel_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "structural_id": self.structural_id,
            "kernel_spec_id": self.kernel_spec_id,
            "implementation_sha256": self.implementation_sha256,
            "authority_kind": self.authority_kind,
            "transport_authority_claimed": self.transport_authority_claimed,
        }

    @property
    def authority_id(self) -> str:
        return _content_id("kernel_authority", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "authority_id": self.authority_id}


def canonical_lmb_query_kernel_v1() -> LMBKernel:
    return LMBKernel(
        EXPECTED_TILE_TYPES,
        EXPECTED_BLOCKERS,
        EXPECTED_TYPE_COUNT,
        EXPECTED_CAPACITY,
        EXPECTED_MAX_LAYERS,
    )


def canonical_lmb_query_kernel_authority_v1() -> LMBQueryKernelAuthorityV1:
    if _kernel_source_digest() != KERNEL_IMPLEMENTATION_SHA256:
        raise QueryLocalRefinementInvariantViolation(
            "runtime LMB kernel implementation differs from the frozen authority"
        )
    return LMBQueryKernelAuthorityV1(
        CANONICAL_STRUCTURAL_ID,
        EXPECTED_TILE_TYPES,
        EXPECTED_BLOCKERS,
        EXPECTED_TYPE_COUNT,
        EXPECTED_CAPACITY,
        EXPECTED_MAX_LAYERS,
    )


@dataclass(frozen=True, slots=True)
class QueryLocalRowNecessityProofV1:
    obligation_id: str
    state_id: str
    cell_id: str
    semantic_action_id: str
    ground_row_id: str
    ground_action_id: str
    concretizer_probability: Fraction
    reachable_state_mass_upper: Fraction
    unresolved_failure_exposure: Fraction
    leave_one_out_failure_upper: Fraction
    risk_tolerance: Fraction
    individually_required: bool = True
    proof_rule: str = "H1_ZERO_RISK_POSITIVE_CONCRETIZER_WEIGHT_NECESSITY_V1"

    def __post_init__(self) -> None:
        for field in (
            "obligation_id",
            "state_id",
            "cell_id",
            "semantic_action_id",
            "ground_row_id",
            "ground_action_id",
        ):
            _cid(getattr(self, field), f"row necessity {field}")
        for field in (
            "concretizer_probability",
            "reachable_state_mass_upper",
            "unresolved_failure_exposure",
            "leave_one_out_failure_upper",
            "risk_tolerance",
        ):
            value = _fraction(getattr(self, field), f"row necessity {field}")
            object.__setattr__(self, field, value)
            if not 0 <= value <= 1:
                raise QueryLocalRefinementInvariantViolation(
                    f"row necessity {field} lies outside [0,1]"
                )
        expected = self.concretizer_probability * self.reachable_state_mass_upper
        if (
            self.concretizer_probability <= 0
            or self.unresolved_failure_exposure != expected
            or self.leave_one_out_failure_upper != expected
            or self.leave_one_out_failure_upper <= self.risk_tolerance
            or self.individually_required is not True
            or self.proof_rule
            != "H1_ZERO_RISK_POSITIVE_CONCRETIZER_WEIGHT_NECESSITY_V1"
        ):
            raise QueryLocalRefinementInvariantViolation(
                "row necessity proof does not establish exact H1 zero-risk need"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_row_necessity_proof.v1",
            "obligation_id": self.obligation_id,
            "state_id": self.state_id,
            "cell_id": self.cell_id,
            "semantic_action_id": self.semantic_action_id,
            "ground_row_id": self.ground_row_id,
            "ground_action_id": self.ground_action_id,
            "concretizer_probability": _fraction_document(
                self.concretizer_probability
            ),
            "reachable_state_mass_upper": _fraction_document(
                self.reachable_state_mass_upper
            ),
            "unresolved_failure_exposure": _fraction_document(
                self.unresolved_failure_exposure
            ),
            "leave_one_out_failure_upper": _fraction_document(
                self.leave_one_out_failure_upper
            ),
            "risk_tolerance": _fraction_document(self.risk_tolerance),
            "individually_required": self.individually_required,
            "proof_rule": self.proof_rule,
        }

    @property
    def proof_id(self) -> str:
        return _content_id("row_proof", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


@dataclass(frozen=True, slots=True)
class QueryLocalEvidenceRequestV1:
    observed_synthesis_result_id: str
    base_model_id: str
    source_thresholds_id: str
    base_plan_proposal_result_id: str
    source_plan_id: str
    failed_typed_audit_result_id: str
    failed_inner_audit_result_id: str
    failed_frontier_id: str
    row_proofs: tuple[QueryLocalRowNecessityProofV1, ...]
    requested_ground_row_ids: tuple[str, ...]
    maximum_exact_kernel_queries: int
    frontier_obligation_count: int
    request_preparation_kernel_calls: int = 0
    request_preparation_ground_search_calls: int = 0
    local_access_authorized: bool = True
    global_minimum_claimed: bool = False
    minimality_scope: str = (
        "FIXED_H1_PLAN_CONCRETIZER_ROW_COMPLETION_FOR_ZERO_RISK_V1"
    )

    def __post_init__(self) -> None:
        for field in (
            "observed_synthesis_result_id",
            "base_model_id",
            "source_thresholds_id",
            "base_plan_proposal_result_id",
            "source_plan_id",
            "failed_typed_audit_result_id",
            "failed_inner_audit_result_id",
            "failed_frontier_id",
        ):
            _cid(getattr(self, field), f"evidence request {field}")
        if type(self.row_proofs) is not tuple or any(
            type(item) is not QueryLocalRowNecessityProofV1
            for item in self.row_proofs
        ):
            raise QueryLocalRefinementInvariantViolation(
                "evidence request rejects substituted row proofs"
            )
        proof_keys = tuple(
            (item.ground_row_id, item.obligation_id) for item in self.row_proofs
        )
        if not proof_keys or proof_keys != tuple(sorted(set(proof_keys))):
            raise QueryLocalRefinementInvariantViolation(
                "row necessity proofs must be nonempty, unique, and sorted"
            )
        requested = _sorted_ids(
            self.requested_ground_row_ids, "requested ground rows"
        )
        if requested != tuple(sorted({item.ground_row_id for item in self.row_proofs})):
            raise QueryLocalRefinementInvariantViolation(
                "requested rows differ from exact row-necessity support"
            )
        _integer(self.maximum_exact_kernel_queries, "maximum exact kernel queries", 1)
        _integer(self.frontier_obligation_count, "frontier obligation count", 1)
        if (
            self.maximum_exact_kernel_queries != len(requested)
            or self.request_preparation_kernel_calls != 0
            or self.request_preparation_ground_search_calls != 0
            or self.local_access_authorized is not True
            or self.global_minimum_claimed is not False
            or self.minimality_scope
            != "FIXED_H1_PLAN_CONCRETIZER_ROW_COMPLETION_FOR_ZERO_RISK_V1"
        ):
            raise QueryLocalRefinementInvariantViolation(
                "evidence request crossed its scoped authorization boundary"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_evidence_request.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "observed_synthesis_result_id": self.observed_synthesis_result_id,
            "base_model_id": self.base_model_id,
            "source_thresholds_id": self.source_thresholds_id,
            "base_plan_proposal_result_id": self.base_plan_proposal_result_id,
            "source_plan_id": self.source_plan_id,
            "failed_typed_audit_result_id": self.failed_typed_audit_result_id,
            "failed_inner_audit_result_id": self.failed_inner_audit_result_id,
            "failed_frontier_id": self.failed_frontier_id,
            "row_proofs": [item.to_document() for item in self.row_proofs],
            "requested_ground_row_ids": list(self.requested_ground_row_ids),
            "maximum_exact_kernel_queries": self.maximum_exact_kernel_queries,
            "frontier_obligation_count": self.frontier_obligation_count,
            "request_preparation_kernel_calls": self.request_preparation_kernel_calls,
            "request_preparation_ground_search_calls": (
                self.request_preparation_ground_search_calls
            ),
            "local_access_authorized": self.local_access_authorized,
            "global_minimum_claimed": self.global_minimum_claimed,
            "minimality_scope": self.minimality_scope,
        }

    @property
    def request_id(self) -> str:
        return _content_id("request", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


def _verified_failure_chain(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    failed_audit: TypedPartialSoundAuditResultV2,
):
    if type(base_plan_proposal) is not TypedPartialModelPlanProposalResultV2:
        raise QueryLocalRefinementInvariantViolation(
            "failure chain requires the exact typed V0-044 proposal result"
        )
    if type(failed_audit) is not TypedPartialSoundAuditResultV2:
        raise QueryLocalRefinementInvariantViolation(
            "failure chain requires the exact typed V0-043 audit result"
        )
    try:
        verified_plan = verify_partial_model_plan_from_observed_synthesis_v2(
            observation_log,
            semantics_profile,
            observation_authority,
            observed_synthesis_result,
            thresholds,
            base_plan_proposal,
        )
    except ValueError as error:
        raise QueryLocalRefinementInvariantViolation(str(error)) from error
    if verified_plan.trace.outcome is not PartialModelPlannerOutcome.PLAN_PROPOSED:
        raise QueryLocalRefinementInvariantViolation(
            "query-local refinement requires a selected base plan"
        )
    plan = verified_plan.selected_plan
    if type(plan) is not FrozenContingentAbstractPlanV1:
        raise QueryLocalRefinementInvariantViolation(
            "verified base proposal contains no exact selected plan"
        )
    try:
        verified_audit = verify_partial_fixed_plan_audit_from_observed_synthesis_v2(
            observation_log,
            semantics_profile,
            observation_authority,
            observed_synthesis_result,
            thresholds,
            plan,
            failed_audit,
        )
    except ValueError as error:
        raise QueryLocalRefinementInvariantViolation(str(error)) from error
    inner = verified_audit.audit_result
    if (
        inner.outcome is not PartialAuditOutcome.FAILED_PROOF_FRONTIER
        or inner.failed_proof_frontier is None
        or inner.failed_proof_frontier.reason
        is not FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION
    ):
        raise QueryLocalRefinementInvariantViolation(
            "query-local evidence requires an unresolved failed-proof frontier"
        )
    return (
        observed_synthesis_result.partial_build_result.model,
        verified_plan,
        plan,
        verified_audit,
        inner.failed_proof_frontier,
    )


def _authorize_from_verified(
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    plan_proposal: TypedPartialModelPlanProposalResultV2,
    plan: FrozenContingentAbstractPlanV1,
    failed_audit: TypedPartialSoundAuditResultV2,
    frontier,
) -> QueryLocalEvidenceRequestV1:
    model = observed_synthesis_result.partial_build_result.model
    if (
        thresholds.horizon != 1
        or thresholds.risk_tolerance != 0
        or frontier.earliest_time_index != 0
        or frontier.remaining_horizon != 1
        or frontier.risk_obligation_failed is not True
        or frontier.external_coverage_failed is not False
    ):
        raise QueryLocalRefinementInvariantViolation(
            "V0-046 authorizes only the registered H1 zero-risk frontier"
        )
    ground_by_id = {item.ground_row_id: item for item in model.ground_rows}
    concretizer_by_pair = {
        (item.state_id, item.semantic_action_id): item
        for item in model.concretizer_rows
    }
    proofs: list[QueryLocalRowNecessityProofV1] = []
    for obligation in frontier.obligations:
        if (
            obligation.remaining_horizon != 1
            or not obligation.missing_ground_row_ids
            or obligation.known_external_successor_mass != 0
        ):
            raise QueryLocalRefinementInvariantViolation(
                "frontier contains an unsupported non-H1 or nonmissing obligation"
            )
        concretizer = concretizer_by_pair.get(
            (obligation.state_id, obligation.semantic_action_id)
        )
        if concretizer is None:
            raise QueryLocalRefinementInvariantViolation(
                "frontier obligation lacks a bound concretizer row"
            )
        probability_by_action = dict(concretizer.support)
        if not set(obligation.support_ground_row_ids) <= set(ground_by_id):
            raise QueryLocalRefinementInvariantViolation(
                "frontier support contains an unknown ground row"
            )
        for ground_row_id in obligation.missing_ground_row_ids:
            ground_row = ground_by_id[ground_row_id]
            probability = probability_by_action.get(ground_row.ground_action_id)
            if probability is None:
                raise QueryLocalRefinementInvariantViolation(
                    "missing frontier row is absent from the fixed concretizer"
                )
            exposure = obligation.reachable_cell_mass_upper * probability
            proofs.append(
                QueryLocalRowNecessityProofV1(
                    obligation.obligation_id,
                    obligation.state_id,
                    obligation.cell_id,
                    obligation.semantic_action_id,
                    ground_row_id,
                    ground_row.ground_action_id,
                    probability,
                    obligation.reachable_cell_mass_upper,
                    exposure,
                    exposure,
                    thresholds.risk_tolerance,
                )
            )
    proofs_tuple = tuple(
        sorted(proofs, key=lambda item: (item.ground_row_id, item.obligation_id))
    )
    requested = tuple(sorted({item.ground_row_id for item in proofs_tuple}))
    if len(requested) != 4 or len(proofs_tuple) != 4:
        raise QueryLocalRefinementInvariantViolation(
            "registered H1 control must require exactly four distinct missing rows"
        )
    return QueryLocalEvidenceRequestV1(
        observed_synthesis_result.result_id,
        model.model_id,
        thresholds.thresholds_id,
        plan_proposal.result_id,
        plan.plan_id,
        failed_audit.result_id,
        failed_audit.audit_result.result_id,
        frontier.frontier_id,
        proofs_tuple,
        requested,
        len(requested),
        len(frontier.obligations),
    )


def authorize_minimal_query_local_evidence_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    failed_audit: TypedPartialSoundAuditResultV2,
) -> QueryLocalEvidenceRequestV1:
    """Verify the full failed chain, then authorize exactly necessary H1 rows."""

    model, proposal, plan, audit, frontier = _verified_failure_chain(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        thresholds,
        base_plan_proposal,
        failed_audit,
    )
    if model.model_id != observed_synthesis_result.partial_build_result.model.model_id:
        raise QueryLocalRefinementInvariantViolation("verified base model changed")
    return _authorize_from_verified(
        observed_synthesis_result,
        thresholds,
        proposal,
        plan,
        audit,
        frontier,
    )


@dataclass(frozen=True, slots=True)
class QueryLocalTransitionEvidenceV1:
    sequence_number: int
    request_id: str
    kernel_authority_id: str
    ground_row_id: str
    state_id: str
    ground_action_id: str
    successor: ObservedSuccessorRefV1
    reward_features: tuple[tuple[str, Fraction], ...]
    failure: bool
    terminal: bool
    event_receipt_id: str
    evidence_class: EvidenceClass = EvidenceClass.EXACT_KERNEL_QUERY
    evidence_lane: EvidenceLane = EvidenceLane.OPERATIONAL_QUERY

    def __post_init__(self) -> None:
        _integer(self.sequence_number, "query-local evidence sequence", 1)
        for field in (
            "request_id",
            "kernel_authority_id",
            "ground_row_id",
            "state_id",
            "ground_action_id",
            "event_receipt_id",
        ):
            _cid(getattr(self, field), f"query-local evidence {field}")
        if type(self.successor) is not ObservedSuccessorRefV1:
            raise QueryLocalRefinementInvariantViolation(
                "query-local evidence rejects substituted successor references"
            )
        if type(self.reward_features) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) not in (int, Fraction)
            for item in self.reward_features
        ):
            raise QueryLocalRefinementInvariantViolation(
                "query-local reward features must be exact typed pairs"
            )
        normalized = tuple(
            (name, Fraction(value)) for name, value in self.reward_features
        )
        if normalized != tuple(sorted(set(normalized))):
            raise QueryLocalRefinementInvariantViolation(
                "query-local reward features must be unique and sorted"
            )
        object.__setattr__(self, "reward_features", normalized)
        if (
            type(self.failure) is not bool
            or type(self.terminal) is not bool
            or (self.failure and not self.terminal)
            or self.evidence_class is not EvidenceClass.EXACT_KERNEL_QUERY
            or self.evidence_lane is not EvidenceLane.OPERATIONAL_QUERY
        ):
            raise QueryLocalRefinementInvariantViolation(
                "query-local evidence markers differ from the exact operational lane"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_transition_evidence.v1",
            "sequence_number": self.sequence_number,
            "request_id": self.request_id,
            "kernel_authority_id": self.kernel_authority_id,
            "ground_row_id": self.ground_row_id,
            "state_id": self.state_id,
            "ground_action_id": self.ground_action_id,
            "successor": self.successor.to_document(),
            "reward_features": [
                {"name": name, "value": _fraction_document(value)}
                for name, value in self.reward_features
            ],
            "failure": self.failure,
            "terminal": self.terminal,
            "event_receipt_id": self.event_receipt_id,
            "evidence_class": self.evidence_class.value,
            "evidence_lane": self.evidence_lane.value,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class QueryLocalEvidenceBundleV1:
    request_id: str
    kernel_authority_id: str
    evidence: tuple[QueryLocalTransitionEvidenceV1, ...]
    requested_ground_row_ids: tuple[str, ...]
    exact_kernel_query_count: int
    positive_outcome_row_count: int
    environment_interaction_count: int = 0
    generative_sample_count: int = 0
    synthetic_rollout_count: int = 0
    extra_ground_row_access_count: int = 0
    operational_lane: bool = True
    observer_honesty_claimed: bool = False

    def __post_init__(self) -> None:
        _cid(self.request_id, "evidence bundle request")
        _cid(self.kernel_authority_id, "evidence bundle kernel authority")
        if type(self.evidence) is not tuple or any(
            type(item) is not QueryLocalTransitionEvidenceV1
            for item in self.evidence
        ):
            raise QueryLocalRefinementInvariantViolation(
                "evidence bundle rejects substituted evidence rows"
            )
        if tuple(item.sequence_number for item in self.evidence) != tuple(
            range(1, len(self.evidence) + 1)
        ):
            raise QueryLocalRefinementInvariantViolation(
                "evidence sequence must be contiguous from one"
            )
        requested = _sorted_ids(
            self.requested_ground_row_ids, "bundle requested rows"
        )
        if (
            tuple(sorted(item.ground_row_id for item in self.evidence)) != requested
            or any(item.request_id != self.request_id for item in self.evidence)
            or any(
                item.kernel_authority_id != self.kernel_authority_id
                for item in self.evidence
            )
        ):
            raise QueryLocalRefinementInvariantViolation(
                "evidence bundle differs from its request/authority scope"
            )
        for field in (
            "exact_kernel_query_count",
            "positive_outcome_row_count",
            "environment_interaction_count",
            "generative_sample_count",
            "synthetic_rollout_count",
            "extra_ground_row_access_count",
        ):
            _integer(getattr(self, field), f"evidence bundle {field}")
        if (
            self.exact_kernel_query_count != len(requested)
            or self.positive_outcome_row_count != len(requested)
            or self.environment_interaction_count != 0
            or self.generative_sample_count != 0
            or self.synthetic_rollout_count != 0
            or self.extra_ground_row_access_count != 0
            or self.operational_lane is not True
            or self.observer_honesty_claimed is not False
        ):
            raise QueryLocalRefinementInvariantViolation(
                "evidence bundle accounting or authority boundary is inconsistent"
            )

    @property
    def evidence_ledger_id(self) -> str:
        return _content_id(
            "ledger",
            {
                "schema": "acfqp.query_local_evidence_ledger.v1",
                "request_id": self.request_id,
                "kernel_authority_id": self.kernel_authority_id,
                "exact_kernel_query_count": self.exact_kernel_query_count,
                "positive_outcome_row_count": self.positive_outcome_row_count,
                "environment_interaction_count": self.environment_interaction_count,
                "generative_sample_count": self.generative_sample_count,
                "synthetic_rollout_count": self.synthetic_rollout_count,
                "extra_ground_row_access_count": self.extra_ground_row_access_count,
            },
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_evidence_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self.request_id,
            "kernel_authority_id": self.kernel_authority_id,
            "evidence": [item.to_document() for item in self.evidence],
            "requested_ground_row_ids": list(self.requested_ground_row_ids),
            "evidence_ledger_id": self.evidence_ledger_id,
            "exact_kernel_query_count": self.exact_kernel_query_count,
            "positive_outcome_row_count": self.positive_outcome_row_count,
            "environment_interaction_count": self.environment_interaction_count,
            "generative_sample_count": self.generative_sample_count,
            "synthetic_rollout_count": self.synthetic_rollout_count,
            "extra_ground_row_access_count": self.extra_ground_row_access_count,
            "operational_lane": self.operational_lane,
            "observer_honesty_claimed": self.observer_honesty_claimed,
        }

    @property
    def bundle_id(self) -> str:
        return _content_id("bundle", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bundle_id": self.bundle_id}


def _planning_kind(status: LMBStatus) -> PlanningKind:
    return {
        LMBStatus.ACTIVE: PlanningKind.ACTIVE,
        LMBStatus.SUCCESS: PlanningKind.SUCCESS,
        LMBStatus.FAILURE: PlanningKind.FAILURE,
    }[status]


def _lmb_state(state: CanonicalStateObservationV1) -> LMBState:
    return LMBState(
        state.removed_mask,
        state.buffer_counts,
        LMBStatus(state.status),
    )


def _tile(action: CanonicalGroundActionV1) -> int:
    prefix = "tile="
    if not action.action_key.startswith(prefix):
        raise QueryLocalRefinementInvariantViolation(
            "registered LMB action key is not a canonical tile selector"
        )
    try:
        tile = int(action.action_key[len(prefix) :])
    except ValueError as error:
        raise QueryLocalRefinementInvariantViolation(
            "registered LMB action key contains a noninteger tile"
        ) from error
    return tile


def _validate_kernel_and_catalogue(
    kernel: LMBKernel,
    observation_log: ObservationLogManifestV1,
    authority: LMBQueryKernelAuthorityV1,
) -> None:
    if type(kernel) is not LMBKernel:
        raise QueryLocalRefinementInvariantViolation(
            "query-local acquisition rejects substituted kernels"
        )
    if (
        kernel.tile_types != authority.tile_types
        or kernel.blockers != authority.blockers
        or kernel.type_count != authority.type_count
        or kernel.capacity != authority.capacity
        or kernel.max_layers != authority.max_layers
        or observation_log.structural_id != authority.structural_id
    ):
        raise QueryLocalRefinementInvariantViolation(
            "runtime kernel differs from its frozen structural authority"
        )
    if _kernel_source_digest() != authority.implementation_sha256:
        raise QueryLocalRefinementInvariantViolation(
            "runtime kernel implementation differs from the authority digest"
        )
    catalogue_by_state = {item.state_id: item for item in observation_log.action_catalogues}
    for state in observation_log.states:
        expected_tiles = tuple(item.tile for item in kernel.actions(_lmb_state(state)))
        catalogue = catalogue_by_state[state.state_id]
        actual_tiles = tuple(sorted(_tile(item) for item in catalogue.actions))
        if actual_tiles != tuple(sorted(expected_tiles)) or any(
            item.selected_type != kernel.tile_types[_tile(item)]
            for item in catalogue.actions
        ):
            raise QueryLocalRefinementInvariantViolation(
                "runtime kernel legal actions differ from the trusted catalogue"
            )


def _acquire_from_authorized(
    observation_log: ObservationLogManifestV1,
    request: QueryLocalEvidenceRequestV1,
    kernel: LMBKernel,
) -> QueryLocalEvidenceBundleV1:
    authority = canonical_lmb_query_kernel_authority_v1()
    _validate_kernel_and_catalogue(kernel, observation_log, authority)
    state_by_id = {item.state_id: item for item in observation_log.states}
    action_by_row = {
        item.ground_row_id: item
        for catalogue in observation_log.action_catalogues
        for item in catalogue.actions
    }
    registered_successors = {
        (item.removed_mask, item.buffer_counts, item.status): item.state_id
        for item in observation_log.states
    }
    evidence: list[QueryLocalTransitionEvidenceV1] = []
    for sequence, ground_row_id in enumerate(
        request.requested_ground_row_ids, start=1
    ):
        action = action_by_row[ground_row_id]
        state = state_by_id[action.state_id]
        outcomes = kernel.step(_lmb_state(state), LMBAction(_tile(action)))
        if (
            type(outcomes) is not tuple
            or len(outcomes) != 1
            or outcomes[0].probability != 1
        ):
            raise QueryLocalRefinementInvariantViolation(
                "V0-046 requires a deterministic singleton kernel outcome"
            )
        outcome = outcomes[0]
        successor_key = (
            outcome.next_state.removed_mask,
            outcome.next_state.buffer,
            outcome.next_state.status.value,
        )
        registered_id = registered_successors.get(successor_key)
        if registered_id is None:
            observed_successor = CanonicalStateObservationV1(
                (
                    f"removed={outcome.next_state.removed_mask};"
                    f"buffer={outcome.next_state.buffer};"
                    f"status={outcome.next_state.status.value}"
                ),
                outcome.next_state.removed_mask,
                outcome.next_state.buffer,
                outcome.next_state.status.value,
                _planning_kind(outcome.next_state.status),
            )
            successor = ObservedSuccessorRefV1(
                SuccessorKind.EXTERNAL_STATE, observed_successor.state_id
            )
        else:
            successor = ObservedSuccessorRefV1(
                SuccessorKind.REGISTERED_STATE, registered_id
            )
        receipt = _content_id(
            "receipt",
            {
                "schema": "acfqp.query_local_evidence_receipt.v1",
                "request_id": request.request_id,
                "kernel_authority_id": authority.authority_id,
                "sequence_number": sequence,
                "ground_row_id": ground_row_id,
                "successor": successor.to_document(),
                "reward_features": [
                    {"name": name, "value": _fraction_document(value)}
                    for name, value in outcome.reward_features
                ],
                "failure": outcome.failure,
                "terminal": outcome.terminal,
            },
        )
        evidence.append(
            QueryLocalTransitionEvidenceV1(
                sequence,
                request.request_id,
                authority.authority_id,
                ground_row_id,
                state.state_id,
                action.action_id,
                successor,
                outcome.reward_features,
                outcome.failure,
                outcome.terminal,
                receipt,
            )
        )
    return QueryLocalEvidenceBundleV1(
        request.request_id,
        authority.authority_id,
        tuple(evidence),
        request.requested_ground_row_ids,
        len(evidence),
        len(evidence),
    )


def acquire_lmb_query_local_evidence_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    failed_audit: TypedPartialSoundAuditResultV2,
    request: QueryLocalEvidenceRequestV1,
    kernel: LMBKernel,
) -> QueryLocalEvidenceBundleV1:
    expected = authorize_minimal_query_local_evidence_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        thresholds,
        base_plan_proposal,
        failed_audit,
    )
    if type(request) is not QueryLocalEvidenceRequestV1 or (
        request.to_document() != expected.to_document()
    ):
        raise QueryLocalRefinementInvariantViolation(
            "query-local acquisition request differs from full failure-chain replay"
        )
    return _acquire_from_authorized(observation_log, expected, kernel)


@dataclass(frozen=True, slots=True)
class QueryLocalOverlayContextV1:
    base_model_id: str
    observed_synthesis_result_id: str
    source_thresholds_id: str
    source_plan_id: str
    failed_typed_audit_result_id: str
    evidence_request_id: str
    evidence_bundle_id: str
    parent_overlay_version: int = 0
    overlay_version: int = 1

    def __post_init__(self) -> None:
        for field in (
            "base_model_id",
            "observed_synthesis_result_id",
            "source_thresholds_id",
            "source_plan_id",
            "failed_typed_audit_result_id",
            "evidence_request_id",
            "evidence_bundle_id",
        ):
            _cid(getattr(self, field), f"overlay context {field}")
        if self.parent_overlay_version != 0 or self.overlay_version != 1:
            raise QueryLocalRefinementInvariantViolation(
                "V0-046 permits exactly one immutable overlay generation"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_overlay_context.v1",
            "base_model_id": self.base_model_id,
            "observed_synthesis_result_id": self.observed_synthesis_result_id,
            "source_thresholds_id": self.source_thresholds_id,
            "source_plan_id": self.source_plan_id,
            "failed_typed_audit_result_id": self.failed_typed_audit_result_id,
            "evidence_request_id": self.evidence_request_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "parent_overlay_version": self.parent_overlay_version,
            "overlay_version": self.overlay_version,
        }

    @property
    def context_id(self) -> str:
        return _content_id("overlay_context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


@dataclass(frozen=True, slots=True)
class QueryLocalBuildEpochV1:
    overlay_context_id: str
    parent_model_id: str
    child_model_id: str
    evidence_bundle_id: str
    overlay_version: int = 1
    base_model_mutated: bool = False
    promotion_authorized: bool = False

    def __post_init__(self) -> None:
        for field in (
            "overlay_context_id",
            "parent_model_id",
            "child_model_id",
            "evidence_bundle_id",
        ):
            _cid(getattr(self, field), f"build epoch {field}")
        if (
            self.parent_model_id == self.child_model_id
            or self.overlay_version != 1
            or self.base_model_mutated is not False
            or self.promotion_authorized is not False
        ):
            raise QueryLocalRefinementInvariantViolation(
                "query-local build epoch violates immutable parent/child semantics"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_build_epoch.v1",
            "overlay_context_id": self.overlay_context_id,
            "parent_model_id": self.parent_model_id,
            "child_model_id": self.child_model_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "overlay_version": self.overlay_version,
            "base_model_mutated": self.base_model_mutated,
            "promotion_authorized": self.promotion_authorized,
        }

    @property
    def build_epoch_id(self) -> str:
        return _content_id("build_epoch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "build_epoch_id": self.build_epoch_id}


@dataclass(frozen=True, slots=True)
class QueryLocalOverlayBuildResultV1:
    context: QueryLocalOverlayContextV1
    build_epoch: QueryLocalBuildEpochV1
    model: QueryScopedPartialRAPMV2
    replaced_ground_row_ids: tuple[str, ...]
    remaining_missing_ground_row_ids: tuple[str, ...]
    build_kernel_calls: int = 0
    base_model_mutated: bool = False
    promotion_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.context) is not QueryLocalOverlayContextV1
            or type(self.build_epoch) is not QueryLocalBuildEpochV1
            or type(self.model) is not QueryScopedPartialRAPMV2
        ):
            raise QueryLocalRefinementInvariantViolation(
                "overlay build rejects substituted nested artifacts"
            )
        replaced = _sorted_ids(
            self.replaced_ground_row_ids, "overlay replaced rows"
        )
        remaining = _sorted_ids(
            self.remaining_missing_ground_row_ids,
            "overlay remaining missing rows",
            nonempty=False,
        )
        if (
            self.context.base_model_id != self.model.base_model_id
            or self.context.observed_synthesis_result_id
            != self.model.observed_synthesis_result_id
            or self.context.source_thresholds_id != self.model.source_thresholds_id
            or self.context.source_plan_id != self.model.source_plan_id
            or self.context.failed_typed_audit_result_id
            != self.model.failed_typed_audit_result_id
            or self.context.evidence_request_id != self.model.evidence_request_id
            or self.context.evidence_bundle_id != self.model.evidence_bundle_id
            or self.context.context_id != self.model.overlay_context_id
            or self.build_epoch.overlay_context_id != self.context.context_id
            or self.build_epoch.parent_model_id != self.model.base_model_id
            or self.build_epoch.child_model_id != self.model.model_id
            or self.build_epoch.evidence_bundle_id != self.model.evidence_bundle_id
            or not set(replaced) <= set(self.model.coverage.observed_ground_row_ids)
            or remaining != self.model.coverage.missing_ground_row_ids
            or self.build_kernel_calls != 0
            or self.base_model_mutated is not False
            or self.promotion_authorized is not False
        ):
            raise QueryLocalRefinementInvariantViolation(
                "overlay build identity, coverage, or claim boundary mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_overlay_build_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context": self.context.to_document(),
            "build_epoch": self.build_epoch.to_document(),
            "model": self.model.to_document(),
            "replaced_ground_row_ids": list(self.replaced_ground_row_ids),
            "remaining_missing_ground_row_ids": list(
                self.remaining_missing_ground_row_ids
            ),
            "build_kernel_calls": self.build_kernel_calls,
            "base_model_mutated": self.base_model_mutated,
            "promotion_authorized": self.promotion_authorized,
        }

    @property
    def result_id(self) -> str:
        return _content_id("build", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _build_overlay_from_verified(
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    plan: FrozenContingentAbstractPlanV1,
    failed_audit: TypedPartialSoundAuditResultV2,
    request: QueryLocalEvidenceRequestV1,
    bundle: QueryLocalEvidenceBundleV1,
) -> QueryLocalOverlayBuildResultV1:
    base = observed_synthesis_result.partial_build_result.model
    if (
        bundle.request_id != request.request_id
        or bundle.requested_ground_row_ids != request.requested_ground_row_ids
        or bundle.exact_kernel_query_count != request.maximum_exact_kernel_queries
        or bundle.kernel_authority_id
        != canonical_lmb_query_kernel_authority_v1().authority_id
    ):
        raise QueryLocalRefinementInvariantViolation(
            "query-local evidence bundle differs from the authorized request"
        )
    evidence_by_row = {item.ground_row_id: item for item in bundle.evidence}
    active_cell_ids = tuple(
        sorted(
            item.cell_id
            for item in base.cells
            if item.planning_kind is PlanningKind.ACTIVE
        )
    )
    destinations = tuple(sorted((*active_cell_ids, base.external_boundary_id)))
    state_to_cell = {
        state_id: cell.cell_id
        for cell in base.cells
        for state_id in cell.member_state_ids
    }
    ground_rows: list[PartialGroundRowV1] = []
    for row in base.ground_rows:
        evidence = evidence_by_row.get(row.ground_row_id)
        if evidence is None:
            ground_rows.append(row)
            continue
        if (
            row.status is not AmbiguityRowStatus.MISSING_VACUOUS
            or row.state_id != evidence.state_id
            or row.ground_action_id != evidence.ground_action_id
        ):
            raise QueryLocalRefinementInvariantViolation(
                "overlay evidence does not replace an authorized missing base row"
            )
        known_successor: dict[str, Fraction] = {}
        if not evidence.terminal:
            destination = (
                state_to_cell[evidence.successor.reference]
                if evidence.successor.kind is SuccessorKind.REGISTERED_STATE
                else base.external_boundary_id
            )
            known_successor[destination] = Fraction(1)
        ground_rows.append(
            PartialGroundRowV1(
                row.ground_row_id,
                row.state_id,
                row.ground_action_id,
                AmbiguityRowStatus.OBSERVED_SINGLETON,
                (evidence.evidence_id,),
                _ambiguity_payload(
                    known_reward=dict(evidence.reward_features),
                    known_successor=known_successor,
                    known_failure=Fraction(int(evidence.failure)),
                    known_terminal=Fraction(int(evidence.terminal)),
                    unknown_mass=Fraction(0),
                    destinations=destinations,
                    external_boundary_id=base.external_boundary_id,
                    caps=base.reward_feature_caps,
                ),
            )
        )
    ground_rows_tuple = tuple(sorted(ground_rows, key=lambda item: item.ground_row_id))
    ground_by_state_action = {
        (item.state_id, item.ground_action_id): item for item in ground_rows_tuple
    }
    realizations: list[PartialSemanticRealizationV1] = []
    for concretizer in base.concretizer_rows:
        support = tuple(
            (
                ground_by_state_action[(concretizer.state_id, action_id)],
                probability,
            )
            for action_id, probability in concretizer.support
        )
        observed_ids = tuple(
            sorted(
                row.ground_row_id
                for row, _ in support
                if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
            )
        )
        missing_ids = tuple(
            sorted(
                row.ground_row_id
                for row, _ in support
                if row.status is AmbiguityRowStatus.MISSING_VACUOUS
            )
        )
        known_reward: dict[str, Fraction] = {}
        known_successor: dict[str, Fraction] = {}
        known_failure = Fraction(0)
        known_terminal = Fraction(0)
        unknown_mass = Fraction(0)
        for row, probability in support:
            if row.status is AmbiguityRowStatus.MISSING_VACUOUS:
                unknown_mass += probability
                continue
            for name, value in row.ambiguity.known_reward_features:
                known_reward[name] = known_reward.get(name, Fraction(0)) + (
                    probability * value
                )
            for destination, mass in row.ambiguity.known_successor_masses:
                known_successor[destination] = known_successor.get(
                    destination, Fraction(0)
                ) + probability * mass
            known_failure += probability * row.ambiguity.known_failure_mass
            known_terminal += probability * row.ambiguity.known_terminal_mass
        realizations.append(
            PartialSemanticRealizationV1(
                concretizer.state_id,
                concretizer.cell_id,
                concretizer.semantic_action_id,
                tuple(sorted(row.ground_row_id for row, _ in support)),
                observed_ids,
                missing_ids,
                _ambiguity_payload(
                    known_reward=known_reward,
                    known_successor=known_successor,
                    known_failure=known_failure,
                    known_terminal=known_terminal,
                    unknown_mass=unknown_mass,
                    destinations=destinations,
                    external_boundary_id=base.external_boundary_id,
                    caps=base.reward_feature_caps,
                ),
            )
        )
    realizations_tuple = tuple(
        sorted(realizations, key=lambda item: (item.state_id, item.semantic_action_id))
    )
    observed_ids = tuple(
        item.ground_row_id
        for item in ground_rows_tuple
        if item.status is AmbiguityRowStatus.OBSERVED_SINGLETON
    )
    missing_ids = tuple(
        item.ground_row_id
        for item in ground_rows_tuple
        if item.status is AmbiguityRowStatus.MISSING_VACUOUS
    )
    coverage = ObservationCoverageV1(
        base.coverage.registered_state_ids,
        base.coverage.registered_ground_row_ids,
        observed_ids,
        missing_ids,
        base.external_boundary_id,
    )
    context = QueryLocalOverlayContextV1(
        base.model_id,
        observed_synthesis_result.result_id,
        thresholds.thresholds_id,
        plan.plan_id,
        failed_audit.result_id,
        request.request_id,
        bundle.bundle_id,
    )
    model = QueryScopedPartialRAPMV2(
        base.semantics_profile_id,
        base.semantics_horizon_cap,
        base.observation_log_id,
        base.coordinate_proposal_id,
        base.observation_authority_id,
        base.acquisition_manifest_id,
        coverage.coverage_id,
        bundle.evidence_ledger_id,
        coverage,
        base.external_boundary_id,
        base.cells,
        base.semantic_actions,
        base.concretizer_rows,
        ground_rows_tuple,
        realizations_tuple,
        base.reward_feature_caps,
        base.model_id,
        observed_synthesis_result.result_id,
        thresholds.thresholds_id,
        plan.plan_id,
        failed_audit.result_id,
        request.request_id,
        bundle.bundle_id,
        context.context_id,
    )
    epoch = QueryLocalBuildEpochV1(
        context.context_id,
        base.model_id,
        model.model_id,
        bundle.bundle_id,
    )
    return QueryLocalOverlayBuildResultV1(
        context,
        epoch,
        model,
        request.requested_ground_row_ids,
        missing_ids,
    )


@dataclass(frozen=True, slots=True)
class QueryLocalThresholdRebaseV1:
    source_thresholds_id: str
    source_model_id: str
    target_model_id: str
    rebased_thresholds: FrozenPartialAuditThresholdsV1

    def __post_init__(self) -> None:
        for field in ("source_thresholds_id", "source_model_id", "target_model_id"):
            _cid(getattr(self, field), f"threshold rebase {field}")
        if type(self.rebased_thresholds) is not FrozenPartialAuditThresholdsV1:
            raise QueryLocalRefinementInvariantViolation(
                "threshold rebase rejects substituted thresholds"
            )
        if self.rebased_thresholds.partial_model_id != self.target_model_id:
            raise QueryLocalRefinementInvariantViolation(
                "rebased thresholds do not bind the query-scoped model"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_threshold_rebase.v1",
            "source_thresholds_id": self.source_thresholds_id,
            "source_model_id": self.source_model_id,
            "target_model_id": self.target_model_id,
            "rebased_thresholds": self.rebased_thresholds.to_document(),
            "semantics": "IDENTICAL_QUERY_FIELDS_NEW_QUERY_SCOPED_MODEL_ID_V1",
        }

    @property
    def rebase_id(self) -> str:
        return _content_id("threshold_rebase", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "rebase_id": self.rebase_id}


def _rebase_thresholds(
    source: FrozenPartialAuditThresholdsV1,
    source_model_id: str,
    target_model: QueryScopedPartialRAPMV2,
) -> QueryLocalThresholdRebaseV1:
    rebased = FrozenPartialAuditThresholdsV1(
        target_model.model_id,
        source.horizon,
        source.initial_state_distribution,
        source.reward_weights,
        source.normalized_regret_tolerance,
        source.risk_tolerance,
        source.return_bound_proof,
        source.unrestricted_upper_formula_id,
        source.goal_id,
    )
    return QueryLocalThresholdRebaseV1(
        source.thresholds_id,
        source_model_id,
        target_model.model_id,
        rebased,
    )


@dataclass(frozen=True, slots=True)
class QueryScopedPlanProposalV1:
    overlay_build_result_id: str
    query_scoped_model_id: str
    threshold_rebase_id: str
    thresholds_id: str
    action_domains: tuple[PartialPlannerCellActionDomainV1, ...]
    per_stage_assignment_count: int
    candidate_count: int
    candidate_summaries: tuple[PartialPlannerCandidateSummaryV1, ...]
    selection_mode: PartialModelPlannerSelectionMode
    selected_plan: FrozenContingentAbstractPlanV1
    candidate_cap: int = PRODUCTION_CANDIDATE_CAP
    cap_profile_id: str = PRODUCTION_CAP_PROFILE_ID
    fixed_plan_audit_count: int = 0
    overlay_reconstruction_count: int = 1
    planner_kernel_calls: int = 0
    proposal_is_certificate_authority: bool = False

    def __post_init__(self) -> None:
        for field in (
            "overlay_build_result_id",
            "query_scoped_model_id",
            "threshold_rebase_id",
            "thresholds_id",
            "cap_profile_id",
        ):
            _cid(getattr(self, field), f"query-scoped planner {field}")
        if type(self.action_domains) is not tuple or any(
            type(item) is not PartialPlannerCellActionDomainV1
            for item in self.action_domains
        ):
            raise QueryLocalRefinementInvariantViolation(
                "query-scoped planner rejects substituted action domains"
            )
        domain_keys = tuple(item.cell_id for item in self.action_domains)
        if not domain_keys or domain_keys != tuple(sorted(set(domain_keys))):
            raise QueryLocalRefinementInvariantViolation(
                "query-scoped planner action domains must be nonempty and sorted"
            )
        expected_stage_count = 1
        for domain in self.action_domains:
            expected_stage_count *= len(domain.semantic_action_ids)
        if type(self.candidate_summaries) is not tuple or any(
            type(item) is not PartialPlannerCandidateSummaryV1
            for item in self.candidate_summaries
        ):
            raise QueryLocalRefinementInvariantViolation(
                "query-scoped planner rejects substituted summaries"
            )
        summary_keys = tuple(
            item.contingent_plan_id for item in self.candidate_summaries
        )
        if not summary_keys or summary_keys != tuple(sorted(set(summary_keys))):
            raise QueryLocalRefinementInvariantViolation(
                "query-scoped planner summaries must be nonempty, unique, and sorted"
            )
        expected_selection_mode, expected_selected = _selected_summary(
            self.candidate_summaries
        )
        if type(self.selected_plan) is not FrozenContingentAbstractPlanV1:
            raise QueryLocalRefinementInvariantViolation(
                "query-scoped planner requires an exact selected plan"
            )
        for field in (
            "per_stage_assignment_count",
            "candidate_count",
            "candidate_cap",
            "fixed_plan_audit_count",
            "overlay_reconstruction_count",
            "planner_kernel_calls",
        ):
            _integer(getattr(self, field), f"query-scoped planner {field}")
        if (
            self.candidate_cap != PRODUCTION_CANDIDATE_CAP
            or self.cap_profile_id != PRODUCTION_CAP_PROFILE_ID
            or self.per_stage_assignment_count != expected_stage_count
            or self.candidate_count
            != expected_stage_count**self.selected_plan.horizon
            or self.candidate_count != len(self.candidate_summaries)
            or self.fixed_plan_audit_count != self.candidate_count
            or self.overlay_reconstruction_count != 1
            or self.planner_kernel_calls != 0
            or self.selected_plan.partial_model_id != self.query_scoped_model_id
            or any(
                item.partial_model_id != self.query_scoped_model_id
                or item.thresholds_id != self.thresholds_id
                for item in self.candidate_summaries
            )
            or self.selection_mode is not expected_selection_mode
            or self.selected_plan.plan_id != expected_selected.contingent_plan_id
            or self.proposal_is_certificate_authority is not False
            or type(self.selection_mode) is not PartialModelPlannerSelectionMode
        ):
            raise QueryLocalRefinementInvariantViolation(
                "query-scoped planner counts, selection, or authority mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_scoped_plan_proposal.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "overlay_build_result_id": self.overlay_build_result_id,
            "query_scoped_model_id": self.query_scoped_model_id,
            "threshold_rebase_id": self.threshold_rebase_id,
            "thresholds_id": self.thresholds_id,
            "action_domains": [item.to_document() for item in self.action_domains],
            "per_stage_assignment_count": self.per_stage_assignment_count,
            "candidate_count": self.candidate_count,
            "candidate_summaries": [
                item.to_document() for item in self.candidate_summaries
            ],
            "selection_mode": self.selection_mode.value,
            "selected_plan": self.selected_plan.to_document(),
            "candidate_cap": self.candidate_cap,
            "cap_profile_id": self.cap_profile_id,
            "fixed_plan_audit_count": self.fixed_plan_audit_count,
            "overlay_reconstruction_count": self.overlay_reconstruction_count,
            "planner_kernel_calls": self.planner_kernel_calls,
            "proposal_is_certificate_authority": self.proposal_is_certificate_authority,
        }

    @property
    def result_id(self) -> str:
        return _content_id("planner", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _propose_on_overlay(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    build: QueryLocalOverlayBuildResultV1,
    rebase: QueryLocalThresholdRebaseV1,
) -> QueryScopedPlanProposalV1:
    model = build.model
    thresholds = rebase.rebased_thresholds
    _, domains = _planner_context(
        observation_log,
        semantics_profile,
        observation_authority,
        model,
        thresholds,
    )
    stage_count = 1
    for domain in domains:
        stage_count *= len(domain.semantic_action_ids)
    candidate_count = stage_count**thresholds.horizon
    if candidate_count > PRODUCTION_CANDIDATE_CAP:
        raise QueryLocalRefinementInvariantViolation(
            "V0-046 query-scoped plan enumeration exceeds the production cap"
        )
    stages = _stage_assignments(domains)
    plans: dict[str, FrozenContingentAbstractPlanV1] = {}
    summaries: list[PartialPlannerCandidateSummaryV1] = []
    for schedule in product(stages, repeat=thresholds.horizon):
        plan = FrozenContingentAbstractPlanV1(
            model.model_id,
            thresholds.horizon,
            tuple(
                ContingentPlanStageV1(index, assignments)
                for index, assignments in enumerate(schedule)
            ),
        )
        audit = _audit_verified_partial_model_v1(
            model,
            observation_log,
            semantics_profile,
            observation_authority,
            thresholds,
            plan,
        )
        plans[plan.plan_id] = plan
        summaries.append(_candidate_summary(thresholds, plan, audit))
    summaries_tuple = tuple(
        sorted(summaries, key=lambda item: item.contingent_plan_id)
    )
    selection_mode, selected = _selected_summary(summaries_tuple)
    return QueryScopedPlanProposalV1(
        build.result_id,
        model.model_id,
        rebase.rebase_id,
        thresholds.thresholds_id,
        domains,
        stage_count,
        candidate_count,
        summaries_tuple,
        selection_mode,
        plans[selected.contingent_plan_id],
        fixed_plan_audit_count=candidate_count,
    )


@dataclass(frozen=True, slots=True)
class QueryScopedPlanAuditV1:
    overlay_build_result_id: str
    query_scoped_model_id: str
    evidence_request_id: str
    evidence_bundle_id: str
    threshold_rebase_id: str
    planner_result_id: str
    selected_plan_id: str
    audit_result: PartialSoundAuditResultV1
    independent_kernel_replay_required: bool = True

    def __post_init__(self) -> None:
        for field in (
            "overlay_build_result_id",
            "query_scoped_model_id",
            "evidence_request_id",
            "evidence_bundle_id",
            "threshold_rebase_id",
            "planner_result_id",
            "selected_plan_id",
        ):
            _cid(getattr(self, field), f"query-scoped audit {field}")
        if type(self.audit_result) is not PartialSoundAuditResultV1:
            raise QueryLocalRefinementInvariantViolation(
                "query-scoped audit rejects substituted inner audits"
            )
        if (
            self.audit_result.partial_model_id != self.query_scoped_model_id
            or self.audit_result.contingent_plan_id != self.selected_plan_id
            or self.independent_kernel_replay_required is not True
        ):
            raise QueryLocalRefinementInvariantViolation(
                "query-scoped audit does not bind its model, plan, or replay rule"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_scoped_plan_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "overlay_build_result_id": self.overlay_build_result_id,
            "query_scoped_model_id": self.query_scoped_model_id,
            "evidence_request_id": self.evidence_request_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "threshold_rebase_id": self.threshold_rebase_id,
            "planner_result_id": self.planner_result_id,
            "selected_plan_id": self.selected_plan_id,
            "audit_result": self.audit_result.to_document(),
            "independent_kernel_replay_required": (
                self.independent_kernel_replay_required
            ),
        }

    @property
    def result_id(self) -> str:
        return _content_id("audit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _audit_overlay_plan(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    request: QueryLocalEvidenceRequestV1,
    bundle: QueryLocalEvidenceBundleV1,
    build: QueryLocalOverlayBuildResultV1,
    rebase: QueryLocalThresholdRebaseV1,
    proposal: QueryScopedPlanProposalV1,
) -> QueryScopedPlanAuditV1:
    audit = _audit_verified_partial_model_v1(
        build.model,
        observation_log,
        semantics_profile,
        observation_authority,
        rebase.rebased_thresholds,
        proposal.selected_plan,
    )
    return QueryScopedPlanAuditV1(
        build.result_id,
        build.model.model_id,
        request.request_id,
        bundle.bundle_id,
        rebase.rebase_id,
        proposal.result_id,
        proposal.selected_plan.plan_id,
        audit,
    )


@dataclass(frozen=True, slots=True)
class QueryLocalPromotionDispositionV1:
    query_scoped_model_id: str
    build_epoch_id: str
    local_reuse_allowed: bool = True
    base_promotion_authorized: bool = False
    preregistered_multi_query_gate_run: bool = False
    preregistered_held_out_gate_run: bool = False
    disposition: str = "RETAIN_QUERY_LOCAL_OVERLAY_ONLY"

    def __post_init__(self) -> None:
        _cid(self.query_scoped_model_id, "promotion query-scoped model")
        _cid(self.build_epoch_id, "promotion build epoch")
        if (
            self.local_reuse_allowed is not True
            or self.base_promotion_authorized is not False
            or self.preregistered_multi_query_gate_run is not False
            or self.preregistered_held_out_gate_run is not False
            or self.disposition != "RETAIN_QUERY_LOCAL_OVERLAY_ONLY"
        ):
            raise QueryLocalRefinementInvariantViolation(
                "V0-046 cannot promote a query-local overlay into the reusable base"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_promotion_disposition.v1",
            "query_scoped_model_id": self.query_scoped_model_id,
            "build_epoch_id": self.build_epoch_id,
            "local_reuse_allowed": self.local_reuse_allowed,
            "base_promotion_authorized": self.base_promotion_authorized,
            "preregistered_multi_query_gate_run": (
                self.preregistered_multi_query_gate_run
            ),
            "preregistered_held_out_gate_run": (
                self.preregistered_held_out_gate_run
            ),
            "disposition": self.disposition,
        }

    @property
    def disposition_id(self) -> str:
        return _content_id("promotion", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "disposition_id": self.disposition_id}


@dataclass(frozen=True, slots=True)
class QueryLocalRefinementResultV1:
    request: QueryLocalEvidenceRequestV1
    evidence_bundle: QueryLocalEvidenceBundleV1
    overlay_build: QueryLocalOverlayBuildResultV1
    threshold_rebase: QueryLocalThresholdRebaseV1
    plan_proposal: QueryScopedPlanProposalV1
    independent_audit: QueryScopedPlanAuditV1
    promotion: QueryLocalPromotionDispositionV1
    base_model_id_before: str
    base_model_id_after: str
    operational_exact_kernel_queries: int
    status: QueryLocalRefinementStatus
    sample_efficiency_claimed: bool = False
    official_execution_claimed: bool = False

    def __post_init__(self) -> None:
        expected_types = (
            (self.request, QueryLocalEvidenceRequestV1),
            (self.evidence_bundle, QueryLocalEvidenceBundleV1),
            (self.overlay_build, QueryLocalOverlayBuildResultV1),
            (self.threshold_rebase, QueryLocalThresholdRebaseV1),
            (self.plan_proposal, QueryScopedPlanProposalV1),
            (self.independent_audit, QueryScopedPlanAuditV1),
            (self.promotion, QueryLocalPromotionDispositionV1),
        )
        if any(type(value) is not exact for value, exact in expected_types):
            raise QueryLocalRefinementInvariantViolation(
                "query-local result rejects substituted nested artifacts"
            )
        _cid(self.base_model_id_before, "result base model before")
        _cid(self.base_model_id_after, "result base model after")
        _integer(
            self.operational_exact_kernel_queries,
            "result operational exact kernel queries",
        )
        expected_status = (
            QueryLocalRefinementStatus.QUERY_LOCAL_PLAN_CERTIFIED
            if self.independent_audit.audit_result.outcome
            is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
            else QueryLocalRefinementStatus.QUERY_LOCAL_PLAN_NOT_CERTIFIED
        )
        context = self.overlay_build.context
        model = self.overlay_build.model
        rebase = self.threshold_rebase
        proposal = self.plan_proposal
        audit = self.independent_audit
        if (
            self.base_model_id_before != self.base_model_id_after
            or self.base_model_id_before != model.base_model_id
            or self.request.base_model_id != self.base_model_id_before
            or self.evidence_bundle.request_id != self.request.request_id
            or context.base_model_id != self.request.base_model_id
            or context.observed_synthesis_result_id
            != self.request.observed_synthesis_result_id
            or context.source_thresholds_id != self.request.source_thresholds_id
            or context.source_plan_id != self.request.source_plan_id
            or context.failed_typed_audit_result_id
            != self.request.failed_typed_audit_result_id
            or context.evidence_request_id != self.request.request_id
            or context.evidence_bundle_id != self.evidence_bundle.bundle_id
            or model.evidence_request_id != self.request.request_id
            or model.evidence_bundle_id != self.evidence_bundle.bundle_id
            or rebase.source_thresholds_id != self.request.source_thresholds_id
            or rebase.source_model_id != self.base_model_id_before
            or rebase.target_model_id != model.model_id
            or proposal.overlay_build_result_id != self.overlay_build.result_id
            or proposal.query_scoped_model_id != model.model_id
            or proposal.threshold_rebase_id != rebase.rebase_id
            or proposal.thresholds_id != rebase.rebased_thresholds.thresholds_id
            or audit.overlay_build_result_id != self.overlay_build.result_id
            or audit.query_scoped_model_id != model.model_id
            or audit.evidence_request_id != self.request.request_id
            or audit.evidence_bundle_id != self.evidence_bundle.bundle_id
            or audit.threshold_rebase_id != rebase.rebase_id
            or audit.planner_result_id != proposal.result_id
            or audit.selected_plan_id != proposal.selected_plan.plan_id
            or self.promotion.query_scoped_model_id != model.model_id
            or self.promotion.build_epoch_id
            != self.overlay_build.build_epoch.build_epoch_id
            or self.operational_exact_kernel_queries
            != self.evidence_bundle.exact_kernel_query_count
            or self.status is not expected_status
            or self.sample_efficiency_claimed is not False
            or self.official_execution_claimed is not False
            or self.promotion.base_promotion_authorized is not False
        ):
            raise QueryLocalRefinementInvariantViolation(
                "query-local result status, work, base immutability, or claims mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_refinement_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "request": self.request.to_document(),
            "evidence_bundle": self.evidence_bundle.to_document(),
            "overlay_build": self.overlay_build.to_document(),
            "threshold_rebase": self.threshold_rebase.to_document(),
            "plan_proposal": self.plan_proposal.to_document(),
            "independent_audit": self.independent_audit.to_document(),
            "promotion": self.promotion.to_document(),
            "base_model_id_before": self.base_model_id_before,
            "base_model_id_after": self.base_model_id_after,
            "operational_exact_kernel_queries": (
                self.operational_exact_kernel_queries
            ),
            "status": self.status.value,
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "official_execution_claimed": self.official_execution_claimed,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _run_from_verified_failure(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    verified_plan_proposal: TypedPartialModelPlanProposalResultV2,
    selected_plan: FrozenContingentAbstractPlanV1,
    verified_failed_audit: TypedPartialSoundAuditResultV2,
    frontier,
    kernel: LMBKernel,
) -> QueryLocalRefinementResultV1:
    request = _authorize_from_verified(
        observed_synthesis_result,
        thresholds,
        verified_plan_proposal,
        selected_plan,
        verified_failed_audit,
        frontier,
    )
    bundle = _acquire_from_authorized(observation_log, request, kernel)
    build = _build_overlay_from_verified(
        observed_synthesis_result,
        thresholds,
        selected_plan,
        verified_failed_audit,
        request,
        bundle,
    )
    rebase = _rebase_thresholds(
        thresholds,
        observed_synthesis_result.partial_build_result.model.model_id,
        build.model,
    )
    proposal = _propose_on_overlay(
        observation_log,
        semantics_profile,
        observation_authority,
        build,
        rebase,
    )
    audit = _audit_overlay_plan(
        observation_log,
        semantics_profile,
        observation_authority,
        request,
        bundle,
        build,
        rebase,
        proposal,
    )
    promotion = QueryLocalPromotionDispositionV1(
        build.model.model_id, build.build_epoch.build_epoch_id
    )
    base_id = observed_synthesis_result.partial_build_result.model.model_id
    status = (
        QueryLocalRefinementStatus.QUERY_LOCAL_PLAN_CERTIFIED
        if audit.audit_result.outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
        else QueryLocalRefinementStatus.QUERY_LOCAL_PLAN_NOT_CERTIFIED
    )
    return QueryLocalRefinementResultV1(
        request,
        bundle,
        build,
        rebase,
        proposal,
        audit,
        promotion,
        base_id,
        base_id,
        bundle.exact_kernel_query_count,
        status,
    )


def run_lmb_h1_query_local_refinement_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    failed_audit: TypedPartialSoundAuditResultV2,
    kernel: LMBKernel,
) -> QueryLocalRefinementResultV1:
    """Run the complete V0-046 H1 evidence/refinement/replanning slice."""

    _, proposal, plan, audit, frontier = _verified_failure_chain(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        thresholds,
        base_plan_proposal,
        failed_audit,
    )
    return _run_from_verified_failure(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        thresholds,
        proposal,
        plan,
        audit,
        frontier,
        kernel,
    )


def verify_lmb_h1_query_local_refinement_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    failed_audit: TypedPartialSoundAuditResultV2,
    kernel: LMBKernel,
    claimed_result: QueryLocalRefinementResultV1,
) -> QueryLocalRefinementResultV1:
    """Independently replay source, exact evidence, overlay, planning, and audit."""

    if type(claimed_result) is not QueryLocalRefinementResultV1:
        raise QueryLocalRefinementInvariantViolation(
            "query-local verifier rejects substituted result artifacts"
        )
    replayed = run_lmb_h1_query_local_refinement_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        thresholds,
        base_plan_proposal,
        failed_audit,
        kernel,
    )
    if claimed_result.to_document() != replayed.to_document():
        raise QueryLocalRefinementInvariantViolation(
            "claimed query-local refinement differs from full exact replay"
        )
    return replayed


__all__ = [
    "KERNEL_IMPLEMENTATION_SHA256",
    "LMBQueryKernelAuthorityV1",
    "PROFILE_KEY",
    "QueryLocalBuildEpochV1",
    "QueryLocalEvidenceBundleV1",
    "QueryLocalEvidenceRequestV1",
    "QueryLocalOverlayBuildResultV1",
    "QueryLocalOverlayContextV1",
    "QueryLocalPromotionDispositionV1",
    "QueryLocalRefinementInvariantViolation",
    "QueryLocalRefinementResultV1",
    "QueryLocalRefinementStatus",
    "QueryLocalRowNecessityProofV1",
    "QueryLocalThresholdRebaseV1",
    "QueryLocalTransitionEvidenceV1",
    "QueryScopedPlanAuditV1",
    "QueryScopedPlanProposalV1",
    "acquire_lmb_query_local_evidence_v1",
    "authorize_minimal_query_local_evidence_v1",
    "canonical_lmb_query_kernel_authority_v1",
    "canonical_lmb_query_kernel_v1",
    "run_lmb_h1_query_local_refinement_v1",
    "verify_lmb_h1_query_local_refinement_v1",
]
