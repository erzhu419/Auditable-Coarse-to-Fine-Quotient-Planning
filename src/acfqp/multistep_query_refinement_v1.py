"""V0-047 multi-step certificate-triggered query-local RAPM evolution.

The frozen positive control starts from the V0-045 observation-only partial
model at the canonical LMB ``extra`` state with horizon two.  It performs two
transition-acquisition rounds separated by model-only replanning:

* round one resolves the four time-zero concretizer rows and registers the
  three newly exposed nonterminal boundary states plus their exact legal-action
  catalogues without another transition call;
* round two resolves the complete nine-row time-one value/risk proof scope.

The reusable V0-045 base is never mutated.  Both overlays are query owned,
non-promotable and non-closed.  This module is a deterministic finite positive
control, not a general causal-minimality, learning, promotion or sample-saving
claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import product
from typing import Any, Mapping

from acfqp.domains.matching_buffer import LMBAction, LMBKernel, LMBState, LMBStatus
from acfqp.observation_partial_rapm_v1 import (
    AmbiguityRowStatus,
    CanonicalGroundActionV1,
    CanonicalStateObservationV1,
    ConcretizerRowV1,
    DeterministicObservationProfileV1,
    EvidenceClass,
    EvidenceLane,
    ObservationCoverageV1,
    ObservationLogManifestV1,
    ObservedSuccessorRefV1,
    PartialCellV1,
    PartialGroundRowV1,
    PartialSemanticActionV1,
    PartialSemanticRealizationV1,
    PlanningKind,
    PreregisteredObservationAuthorityV1,
    QueryScopedPartialRAPMV3,
    SuccessorKind,
    TypedActionAtomKind,
    _ambiguity_payload,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    ObservedTypedPartialRAPMResultV1,
    _eval_expression,
)
from acfqp.partial_model_planner_v1 import (
    PRODUCTION_CANDIDATE_CAP,
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
    PartialFailedProofFrontierV1,
    PartialSoundAuditResultV1,
    TypedPartialSoundAuditResultV2,
    _audit_verified_partial_model_v1,
    verify_partial_fixed_plan_audit_from_observed_synthesis_v2,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.query_local_refinement_v1 import (
    _kernel_source_digest,
    canonical_lmb_query_kernel_authority_v1,
    canonical_lmb_query_kernel_v1,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "lmb_h2_multistep_query_local_exact_refinement_v0"
SUCCESS_STATUS = "CERTIFIED_MULTISTEP_QUERY_LOCAL_PLAN"

DOMAIN_TAGS = {
    "row_proof": "acfqp:multistep-row-necessity-proof:v1",
    "request": "acfqp:multistep-evidence-request:v1",
    "receipt": "acfqp:multistep-exact-transition-receipt:v1",
    "evidence": "acfqp:multistep-exact-transition-evidence:v1",
    "bundle": "acfqp:multistep-exact-transition-bundle:v1",
    "evidence_ledger": "acfqp:multistep-evidence-ledger:v1",
    "catalogue": "acfqp:query-local-complete-action-catalogue:v1",
    "boundary": "acfqp:multistep-boundary-expansion:v1",
    "overlay_ledger": "acfqp:multistep-overlay-ledger:v1",
    "build": "acfqp:multistep-overlay-build:v1",
    "rebase": "acfqp:multistep-threshold-rebase:v1",
    "planner": "acfqp:multistep-query-plan-proposal:v1",
    "audit": "acfqp:multistep-query-plan-audit:v1",
    "telemetry": "acfqp:multistep-refinement-telemetry:v1",
    "result": "acfqp:multistep-query-refinement-result:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-047 content-ID domains must be unique")


class MultiStepRefinementInvariantViolation(ValueError):
    """The V0-047 authority, evidence, overlay, or certificate chain is invalid."""


class MultiStepEvidencePhase(str, Enum):
    INITIAL_FRONTIER_ROWS = "INITIAL_FRONTIER_ROWS"
    DOWNSTREAM_VALUE_RISK_ROWS = "DOWNSTREAM_VALUE_RISK_ROWS"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, TypeError, ValueError) as error:
        raise MultiStepRefinementInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise MultiStepRefinementInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise MultiStepRefinementInvariantViolation(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field: str) -> Fraction:
    if type(value) not in (int, Fraction):
        raise MultiStepRefinementInvariantViolation(f"{field} must be exact")
    return Fraction(value)


def _fraction_document(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _sorted_ids(
    values: Any, field: str, *, nonempty: bool = True
) -> tuple[str, ...]:
    if type(values) is not tuple or any(type(item) is not str for item in values):
        raise MultiStepRefinementInvariantViolation(
            f"{field} must be an exact tuple of content IDs"
        )
    for item in values:
        _cid(item, field)
    if values != tuple(sorted(set(values))) or (nonempty and not values):
        raise MultiStepRefinementInvariantViolation(
            f"{field} must be unique, sorted, and appropriately nonempty"
        )
    return values


def _planning_kind(status: LMBStatus) -> PlanningKind:
    return {
        LMBStatus.ACTIVE: PlanningKind.ACTIVE,
        LMBStatus.SUCCESS: PlanningKind.SUCCESS,
        LMBStatus.FAILURE: PlanningKind.FAILURE,
    }[status]


def _state_observation(state: LMBState) -> CanonicalStateObservationV1:
    return CanonicalStateObservationV1(
        (
            f"removed={state.removed_mask};buffer={state.buffer};"
            f"status={state.status.value}"
        ),
        state.removed_mask,
        state.buffer,
        state.status.value,
        _planning_kind(state.status),
    )


def _lmb_state(state: CanonicalStateObservationV1) -> LMBState:
    return LMBState(
        state.removed_mask,
        state.buffer_counts,
        LMBStatus(state.status),
    )


def _tile(action: CanonicalGroundActionV1) -> int:
    prefix = "tile="
    if not action.action_key.startswith(prefix):
        raise MultiStepRefinementInvariantViolation(
            "canonical LMB action key is not a tile selector"
        )
    try:
        return int(action.action_key[len(prefix) :])
    except ValueError as error:
        raise MultiStepRefinementInvariantViolation(
            "canonical LMB action key contains a noninteger tile"
        ) from error


@dataclass(frozen=True, slots=True)
class MultiStepRowNecessityProofV1:
    round_index: int
    source_model_id: str
    source_thresholds_id: str
    source_plan_id: str
    source_audit_result_id: str
    frontier_id: str
    ground_row_id: str
    state_id: str
    cell_id: str
    semantic_action_id: str
    concretizer_probability: Fraction
    reachable_state_mass_upper: Fraction
    row_exposure_upper: Fraction
    unrestricted_reward_upper: Fraction
    policy_reward_lower: Fraction
    risk_tolerance: Fraction
    normalized_regret_tolerance: Fraction
    selected_plan_support: bool
    required_for_risk: bool
    required_for_value: bool
    current_model_missing: bool = True
    proof_rule: str = "CURRENT_FRONTIER_LOCAL_VALUE_RISK_SCOPE_V1"

    def __post_init__(self) -> None:
        _integer(self.round_index, "row proof round", 1)
        if self.round_index not in (1, 2):
            raise MultiStepRefinementInvariantViolation(
                "row proof round lies outside the two-round profile"
            )
        for field in (
            "source_model_id",
            "source_thresholds_id",
            "source_plan_id",
            "source_audit_result_id",
            "frontier_id",
            "ground_row_id",
            "state_id",
            "cell_id",
            "semantic_action_id",
        ):
            _cid(getattr(self, field), f"row proof {field}")
        for field in (
            "concretizer_probability",
            "reachable_state_mass_upper",
            "row_exposure_upper",
            "unrestricted_reward_upper",
            "policy_reward_lower",
            "risk_tolerance",
            "normalized_regret_tolerance",
        ):
            value = _fraction(getattr(self, field), f"row proof {field}")
            object.__setattr__(self, field, value)
            if value < 0:
                raise MultiStepRefinementInvariantViolation(
                    f"row proof {field} cannot be negative"
                )
        if not 0 < self.concretizer_probability <= 1:
            raise MultiStepRefinementInvariantViolation(
                "row proof concretizer probability lies outside (0,1]"
            )
        if not 0 < self.reachable_state_mass_upper <= 1:
            raise MultiStepRefinementInvariantViolation(
                "row proof reachable mass lies outside (0,1]"
            )
        if self.row_exposure_upper != (
            self.concretizer_probability * self.reachable_state_mass_upper
        ):
            raise MultiStepRefinementInvariantViolation(
                "row proof risk exposure does not equal reach times concretizer mass"
            )
        if (
            type(self.selected_plan_support) is not bool
            or type(self.required_for_risk) is not bool
            or type(self.required_for_value) is not bool
            or type(self.current_model_missing) is not bool
            or not (self.required_for_risk or self.required_for_value)
            or self.current_model_missing is not True
            or self.proof_rule != "CURRENT_FRONTIER_LOCAL_VALUE_RISK_SCOPE_V1"
        ):
            raise MultiStepRefinementInvariantViolation(
                "row proof flags overclaim or omit the local value/risk cause"
            )
        if self.required_for_risk and not self.selected_plan_support:
            raise MultiStepRefinementInvariantViolation(
                "risk-required row must lie in the selected-plan support"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multistep_row_necessity_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "round_index": self.round_index,
            "source_model_id": self.source_model_id,
            "source_thresholds_id": self.source_thresholds_id,
            "source_plan_id": self.source_plan_id,
            "source_audit_result_id": self.source_audit_result_id,
            "frontier_id": self.frontier_id,
            "ground_row_id": self.ground_row_id,
            "state_id": self.state_id,
            "cell_id": self.cell_id,
            "semantic_action_id": self.semantic_action_id,
            "concretizer_probability": _fraction_document(
                self.concretizer_probability
            ),
            "reachable_state_mass_upper": _fraction_document(
                self.reachable_state_mass_upper
            ),
            "row_exposure_upper": _fraction_document(
                self.row_exposure_upper
            ),
            "unrestricted_reward_upper": _fraction_document(
                self.unrestricted_reward_upper
            ),
            "policy_reward_lower": _fraction_document(self.policy_reward_lower),
            "risk_tolerance": _fraction_document(self.risk_tolerance),
            "normalized_regret_tolerance": _fraction_document(
                self.normalized_regret_tolerance
            ),
            "selected_plan_support": self.selected_plan_support,
            "required_for_risk": self.required_for_risk,
            "required_for_value": self.required_for_value,
            "current_model_missing": self.current_model_missing,
            "proof_rule": self.proof_rule,
        }

    @property
    def proof_id(self) -> str:
        return _content_id("row_proof", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


@dataclass(frozen=True, slots=True)
class MultiStepEvidenceRequestV1:
    round_index: int
    phase: MultiStepEvidencePhase
    source_model_id: str
    source_thresholds_id: str
    source_plan_id: str
    source_planner_result_id: str
    source_audit_result_id: str
    frontier_id: str
    requested_ground_row_ids: tuple[str, ...]
    row_proofs: tuple[MultiStepRowNecessityProofV1, ...]
    selected_plan_risk_row_count: int
    unrestricted_value_challenger_row_count: int
    maximum_exact_kernel_queries: int
    request_preparation_kernel_calls: int = 0
    request_preparation_ground_search_calls: int = 0
    local_access_authorized: bool = True
    frontier_local_scope_complete: bool = True
    global_minimum_claimed: bool = False

    def __post_init__(self) -> None:
        _integer(self.round_index, "evidence request round", 1)
        if self.round_index not in (1, 2) or type(self.phase) is not MultiStepEvidencePhase:
            raise MultiStepRefinementInvariantViolation(
                "evidence request has an invalid round or phase"
            )
        expected_phase = (
            MultiStepEvidencePhase.INITIAL_FRONTIER_ROWS
            if self.round_index == 1
            else MultiStepEvidencePhase.DOWNSTREAM_VALUE_RISK_ROWS
        )
        if self.phase is not expected_phase:
            raise MultiStepRefinementInvariantViolation(
                "evidence request phase disagrees with its round"
            )
        for field in (
            "source_model_id",
            "source_thresholds_id",
            "source_plan_id",
            "source_planner_result_id",
            "source_audit_result_id",
            "frontier_id",
        ):
            _cid(getattr(self, field), f"evidence request {field}")
        requested = _sorted_ids(
            self.requested_ground_row_ids, "evidence request rows"
        )
        if type(self.row_proofs) is not tuple or any(
            type(item) is not MultiStepRowNecessityProofV1
            for item in self.row_proofs
        ):
            raise MultiStepRefinementInvariantViolation(
                "evidence request rejects substituted row proofs"
            )
        if tuple(item.ground_row_id for item in self.row_proofs) != requested:
            raise MultiStepRefinementInvariantViolation(
                "evidence request proofs do not exactly cover requested rows"
            )
        if any(
            item.round_index != self.round_index
            or item.source_model_id != self.source_model_id
            or item.source_thresholds_id != self.source_thresholds_id
            or item.source_plan_id != self.source_plan_id
            or item.source_audit_result_id != self.source_audit_result_id
            or item.frontier_id != self.frontier_id
            for item in self.row_proofs
        ):
            raise MultiStepRefinementInvariantViolation(
                "evidence request row proofs disagree with the frozen context"
            )
        for field in (
            "selected_plan_risk_row_count",
            "unrestricted_value_challenger_row_count",
            "maximum_exact_kernel_queries",
            "request_preparation_kernel_calls",
            "request_preparation_ground_search_calls",
        ):
            _integer(getattr(self, field), f"evidence request {field}")
        risk_count = sum(item.required_for_risk for item in self.row_proofs)
        value_count = sum(item.required_for_value for item in self.row_proofs)
        if (
            self.selected_plan_risk_row_count != risk_count
            or self.unrestricted_value_challenger_row_count != value_count
            or self.maximum_exact_kernel_queries != len(requested)
            or self.request_preparation_kernel_calls != 0
            or self.request_preparation_ground_search_calls != 0
            or self.local_access_authorized is not True
            or self.frontier_local_scope_complete is not True
            or self.global_minimum_claimed is not False
        ):
            raise MultiStepRefinementInvariantViolation(
                "evidence request accounting or claim boundary is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multistep_evidence_request.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "round_index": self.round_index,
            "phase": self.phase.value,
            "source_model_id": self.source_model_id,
            "source_thresholds_id": self.source_thresholds_id,
            "source_plan_id": self.source_plan_id,
            "source_planner_result_id": self.source_planner_result_id,
            "source_audit_result_id": self.source_audit_result_id,
            "frontier_id": self.frontier_id,
            "requested_ground_row_ids": list(self.requested_ground_row_ids),
            "row_proofs": [item.to_document() for item in self.row_proofs],
            "selected_plan_risk_row_count": self.selected_plan_risk_row_count,
            "unrestricted_value_challenger_row_count": (
                self.unrestricted_value_challenger_row_count
            ),
            "maximum_exact_kernel_queries": self.maximum_exact_kernel_queries,
            "request_preparation_kernel_calls": (
                self.request_preparation_kernel_calls
            ),
            "request_preparation_ground_search_calls": (
                self.request_preparation_ground_search_calls
            ),
            "local_access_authorized": self.local_access_authorized,
            "frontier_local_scope_complete": self.frontier_local_scope_complete,
            "global_minimum_claimed": self.global_minimum_claimed,
        }

    @property
    def request_id(self) -> str:
        return _content_id("request", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


@dataclass(frozen=True, slots=True)
class MultiStepTransitionEvidenceV1:
    round_index: int
    sequence_number: int
    request_id: str
    kernel_authority_id: str
    ground_row_id: str
    state_id: str
    ground_action_id: str
    successor: ObservedSuccessorRefV1
    successor_state: CanonicalStateObservationV1
    reward_features: tuple[tuple[str, Fraction], ...]
    failure: bool
    terminal: bool
    event_receipt_id: str
    evidence_class: EvidenceClass = EvidenceClass.EXACT_KERNEL_QUERY
    evidence_lane: EvidenceLane = EvidenceLane.OPERATIONAL_QUERY

    def __post_init__(self) -> None:
        _integer(self.round_index, "transition evidence round", 1)
        _integer(self.sequence_number, "transition evidence sequence", 1)
        if self.round_index not in (1, 2):
            raise MultiStepRefinementInvariantViolation(
                "transition evidence round lies outside the frozen profile"
            )
        for field in (
            "request_id",
            "kernel_authority_id",
            "ground_row_id",
            "state_id",
            "ground_action_id",
            "event_receipt_id",
        ):
            _cid(getattr(self, field), f"transition evidence {field}")
        if (
            type(self.successor) is not ObservedSuccessorRefV1
            or type(self.successor_state) is not CanonicalStateObservationV1
            or self.successor.reference != self.successor_state.state_id
        ):
            raise MultiStepRefinementInvariantViolation(
                "transition evidence successor reference/state mismatch"
            )
        if type(self.reward_features) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) not in (int, Fraction)
            for item in self.reward_features
        ):
            raise MultiStepRefinementInvariantViolation(
                "transition evidence reward features must be exact pairs"
            )
        normalized = tuple(
            (name, Fraction(value)) for name, value in self.reward_features
        )
        if normalized != tuple(sorted(set(normalized))):
            raise MultiStepRefinementInvariantViolation(
                "transition evidence rewards must be unique and sorted"
            )
        object.__setattr__(self, "reward_features", normalized)
        if (
            type(self.failure) is not bool
            or type(self.terminal) is not bool
            or (self.failure and not self.terminal)
            or (
                self.terminal
                and self.successor_state.planning_kind is PlanningKind.ACTIVE
            )
            or (
                not self.terminal
                and self.successor_state.planning_kind is not PlanningKind.ACTIVE
            )
            or self.failure
            != (self.successor_state.planning_kind is PlanningKind.FAILURE)
            or self.evidence_class is not EvidenceClass.EXACT_KERNEL_QUERY
            or self.evidence_lane is not EvidenceLane.OPERATIONAL_QUERY
        ):
            raise MultiStepRefinementInvariantViolation(
                "transition evidence terminal/failure/lane markers are invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multistep_exact_transition_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "round_index": self.round_index,
            "sequence_number": self.sequence_number,
            "request_id": self.request_id,
            "kernel_authority_id": self.kernel_authority_id,
            "ground_row_id": self.ground_row_id,
            "state_id": self.state_id,
            "ground_action_id": self.ground_action_id,
            "successor": self.successor.to_document(),
            "successor_state": self.successor_state.to_document(),
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
class MultiStepEvidenceBundleV1:
    round_index: int
    request_id: str
    kernel_authority_id: str
    evidence: tuple[MultiStepTransitionEvidenceV1, ...]
    requested_ground_row_ids: tuple[str, ...]
    exact_kernel_query_count: int
    positive_outcome_row_count: int
    environment_interaction_count: int = 0
    generative_sample_count: int = 0
    synthetic_rollout_count: int = 0
    extra_ground_row_access_count: int = 0

    def __post_init__(self) -> None:
        _integer(self.round_index, "evidence bundle round", 1)
        _cid(self.request_id, "evidence bundle request")
        _cid(self.kernel_authority_id, "evidence bundle kernel authority")
        if type(self.evidence) is not tuple or any(
            type(item) is not MultiStepTransitionEvidenceV1
            for item in self.evidence
        ):
            raise MultiStepRefinementInvariantViolation(
                "evidence bundle rejects substituted evidence"
            )
        requested = _sorted_ids(
            self.requested_ground_row_ids, "evidence bundle requested rows"
        )
        if (
            tuple(item.sequence_number for item in self.evidence)
            != tuple(range(1, len(self.evidence) + 1))
            or tuple(sorted(item.ground_row_id for item in self.evidence))
            != requested
            or any(
                item.round_index != self.round_index
                or item.request_id != self.request_id
                or item.kernel_authority_id != self.kernel_authority_id
                for item in self.evidence
            )
        ):
            raise MultiStepRefinementInvariantViolation(
                "evidence bundle sequence or context binding is invalid"
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
        ):
            raise MultiStepRefinementInvariantViolation(
                "evidence bundle accounting is inconsistent"
            )

    @property
    def evidence_ledger_id(self) -> str:
        return _content_id(
            "evidence_ledger",
            {
                "schema": "acfqp.multistep_evidence_ledger.v1",
                "profile_key": PROFILE_KEY,
                "round_index": self.round_index,
                "request_id": self.request_id,
                "kernel_authority_id": self.kernel_authority_id,
                "evidence_ids": [item.evidence_id for item in self.evidence],
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
            "schema": "acfqp.multistep_exact_transition_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "round_index": self.round_index,
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
        }

    @property
    def bundle_id(self) -> str:
        return _content_id("bundle", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bundle_id": self.bundle_id}


@dataclass(frozen=True, slots=True)
class QueryLocalCompleteActionCatalogueV1:
    sequence_number: int
    state: CanonicalStateObservationV1
    actions: tuple[CanonicalGroundActionV1, ...]
    source_transition_evidence_ids: tuple[str, ...]
    kernel_authority_id: str
    action_catalogue_query_count: int = 1
    exact_transition_query_count: int = 0

    def __post_init__(self) -> None:
        _integer(self.sequence_number, "boundary catalogue sequence", 1)
        if type(self.state) is not CanonicalStateObservationV1:
            raise MultiStepRefinementInvariantViolation(
                "boundary catalogue rejects substituted states"
            )
        if self.state.planning_kind is not PlanningKind.ACTIVE:
            raise MultiStepRefinementInvariantViolation(
                "boundary catalogue may only register active states"
            )
        if type(self.actions) is not tuple or any(
            type(item) is not CanonicalGroundActionV1 for item in self.actions
        ):
            raise MultiStepRefinementInvariantViolation(
                "boundary catalogue rejects substituted actions"
            )
        if (
            not self.actions
            or self.actions
            != tuple(sorted({item.action_id: item for item in self.actions}.values(), key=lambda item: item.action_id))
            or any(item.state_id != self.state.state_id for item in self.actions)
        ):
            raise MultiStepRefinementInvariantViolation(
                "boundary catalogue actions must be complete, unique, sorted, and state-bound"
            )
        _sorted_ids(
            self.source_transition_evidence_ids,
            "boundary catalogue source evidence",
        )
        _cid(self.kernel_authority_id, "boundary catalogue kernel authority")
        if self.action_catalogue_query_count != 1 or self.exact_transition_query_count != 0:
            raise MultiStepRefinementInvariantViolation(
                "boundary catalogue accounting must contain one catalogue and zero transition calls"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_local_complete_action_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence_number": self.sequence_number,
            "state": self.state.to_document(),
            "actions": [item.to_document() for item in self.actions],
            "source_transition_evidence_ids": list(
                self.source_transition_evidence_ids
            ),
            "kernel_authority_id": self.kernel_authority_id,
            "action_catalogue_query_count": self.action_catalogue_query_count,
            "exact_transition_query_count": self.exact_transition_query_count,
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_id": self.catalogue_id}


@dataclass(frozen=True, slots=True)
class MultiStepBoundaryExpansionV1:
    base_model_id: str
    round_one_request_id: str
    round_one_bundle_id: str
    kernel_authority_id: str
    coordinate_proposal_id: str
    dsl_registry_id: str
    structural_binding_id: str
    catalogues: tuple[QueryLocalCompleteActionCatalogueV1, ...]
    registered_boundary_state_ids: tuple[str, ...]
    registered_boundary_ground_row_ids: tuple[str, ...]
    action_catalogue_query_count: int
    exact_transition_query_count: int = 0
    ground_search_call_count: int = 0
    caller_selected_state_scope: bool = False

    def __post_init__(self) -> None:
        for field in (
            "base_model_id",
            "round_one_request_id",
            "round_one_bundle_id",
            "kernel_authority_id",
            "coordinate_proposal_id",
            "dsl_registry_id",
            "structural_binding_id",
        ):
            _cid(getattr(self, field), f"boundary expansion {field}")
        if type(self.catalogues) is not tuple or any(
            type(item) is not QueryLocalCompleteActionCatalogueV1
            for item in self.catalogues
        ):
            raise MultiStepRefinementInvariantViolation(
                "boundary expansion rejects substituted catalogues"
            )
        if tuple(item.sequence_number for item in self.catalogues) != tuple(
            range(1, len(self.catalogues) + 1)
        ):
            raise MultiStepRefinementInvariantViolation(
                "boundary catalogue sequence must be contiguous"
            )
        states = _sorted_ids(
            self.registered_boundary_state_ids,
            "boundary expansion state IDs",
        )
        rows = _sorted_ids(
            self.registered_boundary_ground_row_ids,
            "boundary expansion ground-row IDs",
        )
        if (
            tuple(sorted(item.state.state_id for item in self.catalogues)) != states
            or tuple(
                sorted(
                    action.ground_row_id
                    for item in self.catalogues
                    for action in item.actions
                )
            )
            != rows
            or any(
                item.kernel_authority_id != self.kernel_authority_id
                for item in self.catalogues
            )
        ):
            raise MultiStepRefinementInvariantViolation(
                "boundary expansion coverage differs from its catalogues"
            )
        for field in (
            "action_catalogue_query_count",
            "exact_transition_query_count",
            "ground_search_call_count",
        ):
            _integer(getattr(self, field), f"boundary expansion {field}")
        if (
            self.action_catalogue_query_count != len(self.catalogues)
            or self.exact_transition_query_count != 0
            or self.ground_search_call_count != 0
            or self.caller_selected_state_scope is not False
        ):
            raise MultiStepRefinementInvariantViolation(
                "boundary expansion accounting or authority scope is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multistep_boundary_expansion.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "base_model_id": self.base_model_id,
            "round_one_request_id": self.round_one_request_id,
            "round_one_bundle_id": self.round_one_bundle_id,
            "kernel_authority_id": self.kernel_authority_id,
            "coordinate_proposal_id": self.coordinate_proposal_id,
            "dsl_registry_id": self.dsl_registry_id,
            "structural_binding_id": self.structural_binding_id,
            "catalogues": [item.to_document() for item in self.catalogues],
            "registered_boundary_state_ids": list(
                self.registered_boundary_state_ids
            ),
            "registered_boundary_ground_row_ids": list(
                self.registered_boundary_ground_row_ids
            ),
            "action_catalogue_query_count": self.action_catalogue_query_count,
            "exact_transition_query_count": self.exact_transition_query_count,
            "ground_search_call_count": self.ground_search_call_count,
            "caller_selected_state_scope": self.caller_selected_state_scope,
        }

    @property
    def expansion_id(self) -> str:
        return _content_id("boundary", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "expansion_id": self.expansion_id}


@dataclass(frozen=True, slots=True)
class MultiStepOverlayBuildV1:
    round_index: int
    base_model_id: str
    previous_model_id: str
    source_thresholds_id: str
    source_plan_id: str
    source_failed_typed_audit_result_id: str
    evidence_request_id: str
    evidence_bundle_id: str
    boundary_expansion_id: str
    overlay_ledger_id: str
    model: QueryScopedPartialRAPMV3
    observed_ground_row_count: int
    missing_ground_row_count: int
    registered_boundary_state_count: int
    registered_boundary_action_count: int
    newly_observed_ground_row_count: int
    cumulative_exact_kernel_query_count: int
    base_model_mutated: bool = False
    transition_closure_claimed: bool = False
    promotion_authorized: bool = False

    def __post_init__(self) -> None:
        _integer(self.round_index, "overlay build round", 1)
        if self.round_index not in (1, 2):
            raise MultiStepRefinementInvariantViolation(
                "overlay build round lies outside the frozen profile"
            )
        for field in (
            "base_model_id",
            "previous_model_id",
            "source_thresholds_id",
            "source_plan_id",
            "source_failed_typed_audit_result_id",
            "evidence_request_id",
            "evidence_bundle_id",
            "boundary_expansion_id",
            "overlay_ledger_id",
        ):
            _cid(getattr(self, field), f"overlay build {field}")
        if type(self.model) is not QueryScopedPartialRAPMV3:
            raise MultiStepRefinementInvariantViolation(
                "overlay build rejects substituted models"
            )
        for field in (
            "observed_ground_row_count",
            "missing_ground_row_count",
            "registered_boundary_state_count",
            "registered_boundary_action_count",
            "newly_observed_ground_row_count",
            "cumulative_exact_kernel_query_count",
        ):
            _integer(getattr(self, field), f"overlay build {field}")
        if (
            self.model.base_model_id != self.base_model_id
            or self.model.previous_model_id != self.previous_model_id
            or self.model.source_thresholds_id != self.source_thresholds_id
            or self.model.source_plan_id != self.source_plan_id
            or self.model.source_failed_typed_audit_result_id
            != self.source_failed_typed_audit_result_id
            or self.model.evidence_request_id != self.evidence_request_id
            or self.model.evidence_bundle_id != self.evidence_bundle_id
            or self.model.boundary_expansion_id != self.boundary_expansion_id
            or self.model.overlay_ledger_id != self.overlay_ledger_id
            or self.model.overlay_version != self.round_index
            or self.model.cumulative_exact_kernel_query_count
            != self.cumulative_exact_kernel_query_count
            or self.model.registered_query_local_state_count
            != self.registered_boundary_state_count
            or self.observed_ground_row_count
            != len(self.model.coverage.observed_ground_row_ids)
            or self.missing_ground_row_count
            != len(self.model.coverage.missing_ground_row_ids)
            or self.base_model_mutated is not False
            or self.transition_closure_claimed is not False
            or self.promotion_authorized is not False
        ):
            raise MultiStepRefinementInvariantViolation(
                "overlay build/model identity, counts, or claim boundary mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multistep_overlay_build.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "round_index": self.round_index,
            "base_model_id": self.base_model_id,
            "previous_model_id": self.previous_model_id,
            "source_thresholds_id": self.source_thresholds_id,
            "source_plan_id": self.source_plan_id,
            "source_failed_typed_audit_result_id": (
                self.source_failed_typed_audit_result_id
            ),
            "evidence_request_id": self.evidence_request_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "boundary_expansion_id": self.boundary_expansion_id,
            "overlay_ledger_id": self.overlay_ledger_id,
            "model": self.model.to_document(),
            "observed_ground_row_count": self.observed_ground_row_count,
            "missing_ground_row_count": self.missing_ground_row_count,
            "registered_boundary_state_count": self.registered_boundary_state_count,
            "registered_boundary_action_count": self.registered_boundary_action_count,
            "newly_observed_ground_row_count": self.newly_observed_ground_row_count,
            "cumulative_exact_kernel_query_count": (
                self.cumulative_exact_kernel_query_count
            ),
            "base_model_mutated": self.base_model_mutated,
            "transition_closure_claimed": self.transition_closure_claimed,
            "promotion_authorized": self.promotion_authorized,
        }

    @property
    def result_id(self) -> str:
        return _content_id("build", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class MultiStepThresholdRebaseV1:
    overlay_build_result_id: str
    source_thresholds_id: str
    source_partial_model_id: str
    query_scoped_model_id: str
    rebased_thresholds: FrozenPartialAuditThresholdsV1

    def __post_init__(self) -> None:
        for field in (
            "overlay_build_result_id",
            "source_thresholds_id",
            "source_partial_model_id",
            "query_scoped_model_id",
        ):
            _cid(getattr(self, field), f"threshold rebase {field}")
        if type(self.rebased_thresholds) is not FrozenPartialAuditThresholdsV1:
            raise MultiStepRefinementInvariantViolation(
                "threshold rebase rejects substituted thresholds"
            )
        if self.rebased_thresholds.partial_model_id != self.query_scoped_model_id:
            raise MultiStepRefinementInvariantViolation(
                "rebased thresholds do not bind the query-scoped model"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multistep_threshold_rebase.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "overlay_build_result_id": self.overlay_build_result_id,
            "source_thresholds_id": self.source_thresholds_id,
            "source_partial_model_id": self.source_partial_model_id,
            "query_scoped_model_id": self.query_scoped_model_id,
            "rebased_thresholds": self.rebased_thresholds.to_document(),
        }

    @property
    def rebase_id(self) -> str:
        return _content_id("rebase", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "rebase_id": self.rebase_id}


def _selection_numeric_key(
    mode: PartialModelPlannerSelectionMode,
    summary: PartialPlannerCandidateSummaryV1,
) -> tuple[Fraction, Fraction]:
    if mode in (
        PartialModelPlannerSelectionMode.INTERNAL_V0043_AUDIT_PASS_REWARD_MAX,
        PartialModelPlannerSelectionMode.RISK_FEASIBLE_REWARD_MAX,
    ):
        return (-summary.policy_reward_lower, summary.policy_failure_upper)
    if mode is PartialModelPlannerSelectionMode.MIN_FAILURE_RISK_FALLBACK:
        return (summary.policy_failure_upper, -summary.policy_reward_lower)
    raise MultiStepRefinementInvariantViolation(
        "multi-step selection received an inapplicable selection mode"
    )


@dataclass(frozen=True, slots=True)
class MultiStepPlanProposalV1:
    overlay_build_result_id: str
    query_scoped_model_id: str
    threshold_rebase_id: str
    thresholds_id: str
    cell_action_domains: tuple[PartialPlannerCellActionDomainV1, ...]
    per_stage_assignment_count: int
    candidate_count: int
    candidate_summaries: tuple[PartialPlannerCandidateSummaryV1, ...]
    selection_mode: PartialModelPlannerSelectionMode
    selected_plan: FrozenContingentAbstractPlanV1
    semantic_tie_break_rule: str
    selected_semantic_tie_break_key: tuple[int, ...]
    fixed_plan_audit_count: int
    exact_kernel_calls_during_planning: int = 0
    source_synthesis_replay_count: int = 0

    def __post_init__(self) -> None:
        for field in (
            "overlay_build_result_id",
            "query_scoped_model_id",
            "threshold_rebase_id",
            "thresholds_id",
        ):
            _cid(getattr(self, field), f"multi-step planner {field}")
        if type(self.cell_action_domains) is not tuple or any(
            type(item) is not PartialPlannerCellActionDomainV1
            for item in self.cell_action_domains
        ):
            raise MultiStepRefinementInvariantViolation(
                "multi-step planner rejects substituted action domains"
            )
        if tuple(item.cell_id for item in self.cell_action_domains) != tuple(
            sorted(set(item.cell_id for item in self.cell_action_domains))
        ):
            raise MultiStepRefinementInvariantViolation(
                "multi-step planner domains must be unique and sorted"
            )
        if type(self.candidate_summaries) is not tuple or any(
            type(item) is not PartialPlannerCandidateSummaryV1
            for item in self.candidate_summaries
        ):
            raise MultiStepRefinementInvariantViolation(
                "multi-step planner rejects substituted candidate summaries"
            )
        if tuple(item.contingent_plan_id for item in self.candidate_summaries) != tuple(
            sorted(set(item.contingent_plan_id for item in self.candidate_summaries))
        ):
            raise MultiStepRefinementInvariantViolation(
                "multi-step candidate summaries must be unique and sorted"
            )
        if type(self.selection_mode) is not PartialModelPlannerSelectionMode or type(
            self.selected_plan
        ) is not FrozenContingentAbstractPlanV1:
            raise MultiStepRefinementInvariantViolation(
                "multi-step planner selection uses a substituted enum or plan"
            )
        if (
            self.semantic_tie_break_rule
            != "NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1"
            or type(self.selected_semantic_tie_break_key) is not tuple
            or not self.selected_semantic_tie_break_key
            or any(
                type(item) is not int or item not in (0, 1)
                for item in self.selected_semantic_tie_break_key
            )
        ):
            raise MultiStepRefinementInvariantViolation(
                "multi-step semantic tie-break rule/key is invalid"
            )
        for field in (
            "per_stage_assignment_count",
            "candidate_count",
            "fixed_plan_audit_count",
            "exact_kernel_calls_during_planning",
            "source_synthesis_replay_count",
        ):
            _integer(getattr(self, field), f"multi-step planner {field}")
        expected_stage_count = 1
        for domain in self.cell_action_domains:
            expected_stage_count *= len(domain.semantic_action_ids)
        expected_candidates = expected_stage_count ** self.selected_plan.horizon
        mode, selected = _selected_summary(self.candidate_summaries)
        selected_summary = next(
            item
            for item in self.candidate_summaries
            if item.contingent_plan_id == self.selected_plan.plan_id
        )
        if (
            self.selected_plan.partial_model_id != self.query_scoped_model_id
            or self.per_stage_assignment_count != expected_stage_count
            or self.candidate_count != expected_candidates
            or self.candidate_count != len(self.candidate_summaries)
            or self.fixed_plan_audit_count != self.candidate_count
            or any(
                item.partial_model_id != self.query_scoped_model_id
                or item.thresholds_id != self.thresholds_id
                for item in self.candidate_summaries
            )
            or mode is not self.selection_mode
            or _selection_numeric_key(mode, selected_summary)
            != _selection_numeric_key(mode, selected)
            or self.exact_kernel_calls_during_planning != 0
            or self.source_synthesis_replay_count != 0
        ):
            raise MultiStepRefinementInvariantViolation(
                "multi-step planner counts, bindings, or deterministic selection mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multistep_query_plan_proposal.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "overlay_build_result_id": self.overlay_build_result_id,
            "query_scoped_model_id": self.query_scoped_model_id,
            "threshold_rebase_id": self.threshold_rebase_id,
            "thresholds_id": self.thresholds_id,
            "cell_action_domains": [
                item.to_document() for item in self.cell_action_domains
            ],
            "per_stage_assignment_count": self.per_stage_assignment_count,
            "candidate_count": self.candidate_count,
            "candidate_summaries": [
                item.to_document() for item in self.candidate_summaries
            ],
            "selection_mode": self.selection_mode.value,
            "selected_plan": self.selected_plan.to_document(),
            "semantic_tie_break_rule": self.semantic_tie_break_rule,
            "selected_semantic_tie_break_key": list(
                self.selected_semantic_tie_break_key
            ),
            "fixed_plan_audit_count": self.fixed_plan_audit_count,
            "exact_kernel_calls_during_planning": (
                self.exact_kernel_calls_during_planning
            ),
            "source_synthesis_replay_count": self.source_synthesis_replay_count,
        }

    @property
    def result_id(self) -> str:
        return _content_id("planner", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class MultiStepPlanAuditV1:
    overlay_build_result_id: str
    query_scoped_model_id: str
    evidence_request_id: str
    evidence_bundle_id: str
    threshold_rebase_id: str
    planner_result_id: str
    selected_plan_id: str
    audit_result: PartialSoundAuditResultV1
    exact_kernel_calls_during_audit: int = 0
    independent_from_planner_selection: bool = True

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
            _cid(getattr(self, field), f"multi-step audit {field}")
        if type(self.audit_result) is not PartialSoundAuditResultV1:
            raise MultiStepRefinementInvariantViolation(
                "multi-step audit rejects substituted inner results"
            )
        if (
            self.audit_result.partial_model_id != self.query_scoped_model_id
            or self.audit_result.contingent_plan_id != self.selected_plan_id
            or self.exact_kernel_calls_during_audit != 0
            or self.independent_from_planner_selection is not True
        ):
            raise MultiStepRefinementInvariantViolation(
                "multi-step audit model/plan/no-kernel boundary mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multistep_query_plan_audit.v1",
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
            "exact_kernel_calls_during_audit": self.exact_kernel_calls_during_audit,
            "independent_from_planner_selection": (
                self.independent_from_planner_selection
            ),
        }

    @property
    def result_id(self) -> str:
        return _content_id("audit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class MultiStepRefinementTelemetryV1:
    base_observed_ground_rows: int
    base_missing_ground_rows: int
    round_one_exact_kernel_queries: int
    boundary_action_catalogue_queries: int
    first_overlay_observed_ground_rows: int
    first_overlay_missing_ground_rows: int
    round_two_exact_kernel_queries: int
    final_overlay_observed_ground_rows: int
    final_overlay_missing_ground_rows: int
    cumulative_exact_kernel_queries: int
    new_boundary_state_count: int
    new_boundary_action_count: int
    replanning_pass_count: int
    total_candidate_plan_audits: int
    reused_existing_coordinate_signature_count: int
    exact_kernel_calls_during_planning_and_audit: int = 0
    direct_ground_optimization_calls: int = 0
    sample_efficiency_claimed: bool = False

    def __post_init__(self) -> None:
        for field in (
            "base_observed_ground_rows",
            "base_missing_ground_rows",
            "round_one_exact_kernel_queries",
            "boundary_action_catalogue_queries",
            "first_overlay_observed_ground_rows",
            "first_overlay_missing_ground_rows",
            "round_two_exact_kernel_queries",
            "final_overlay_observed_ground_rows",
            "final_overlay_missing_ground_rows",
            "cumulative_exact_kernel_queries",
            "new_boundary_state_count",
            "new_boundary_action_count",
            "replanning_pass_count",
            "total_candidate_plan_audits",
            "reused_existing_coordinate_signature_count",
            "exact_kernel_calls_during_planning_and_audit",
            "direct_ground_optimization_calls",
        ):
            _integer(getattr(self, field), f"telemetry {field}")
        if (
            self.cumulative_exact_kernel_queries
            != self.round_one_exact_kernel_queries
            + self.round_two_exact_kernel_queries
            or self.exact_kernel_calls_during_planning_and_audit != 0
            or self.direct_ground_optimization_calls != 0
            or self.sample_efficiency_claimed is not False
        ):
            raise MultiStepRefinementInvariantViolation(
                "telemetry overclaims sample efficiency or miscounts kernel calls"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multistep_refinement_telemetry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field: getattr(self, field)
                for field in (
                    "base_observed_ground_rows",
                    "base_missing_ground_rows",
                    "round_one_exact_kernel_queries",
                    "boundary_action_catalogue_queries",
                    "first_overlay_observed_ground_rows",
                    "first_overlay_missing_ground_rows",
                    "round_two_exact_kernel_queries",
                    "final_overlay_observed_ground_rows",
                    "final_overlay_missing_ground_rows",
                    "cumulative_exact_kernel_queries",
                    "new_boundary_state_count",
                    "new_boundary_action_count",
                    "replanning_pass_count",
                    "total_candidate_plan_audits",
                    "reused_existing_coordinate_signature_count",
                    "exact_kernel_calls_during_planning_and_audit",
                    "direct_ground_optimization_calls",
                    "sample_efficiency_claimed",
                )
            },
        }

    @property
    def telemetry_id(self) -> str:
        return _content_id("telemetry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "telemetry_id": self.telemetry_id}


@dataclass(frozen=True, slots=True)
class MultiStepQueryRefinementResultV1:
    source_observed_synthesis_result_id: str
    source_thresholds_id: str
    source_plan_proposal_result_id: str
    source_plan_id: str
    source_failed_typed_audit_result_id: str
    round_one_request: MultiStepEvidenceRequestV1
    round_one_bundle: MultiStepEvidenceBundleV1
    boundary_expansion: MultiStepBoundaryExpansionV1
    first_overlay_build: MultiStepOverlayBuildV1
    first_threshold_rebase: MultiStepThresholdRebaseV1
    first_plan_proposal: MultiStepPlanProposalV1
    first_plan_audit: MultiStepPlanAuditV1
    round_two_request: MultiStepEvidenceRequestV1
    round_two_bundle: MultiStepEvidenceBundleV1
    final_overlay_build: MultiStepOverlayBuildV1
    final_threshold_rebase: MultiStepThresholdRebaseV1
    final_plan_proposal: MultiStepPlanProposalV1
    final_plan_audit: MultiStepPlanAuditV1
    telemetry: MultiStepRefinementTelemetryV1
    status: str = SUCCESS_STATUS
    promotion_disposition: str = "RETAIN_QUERY_LOCAL_OVERLAY_ONLY"
    reusable_base_mutated: bool = False
    general_causal_minimality_claimed: bool = False
    sample_saving_claimed: bool = False

    def __post_init__(self) -> None:
        for field in (
            "source_observed_synthesis_result_id",
            "source_thresholds_id",
            "source_plan_proposal_result_id",
            "source_plan_id",
            "source_failed_typed_audit_result_id",
        ):
            _cid(getattr(self, field), f"multi-step result {field}")
        exact_types = (
            (self.round_one_request, MultiStepEvidenceRequestV1),
            (self.round_one_bundle, MultiStepEvidenceBundleV1),
            (self.boundary_expansion, MultiStepBoundaryExpansionV1),
            (self.first_overlay_build, MultiStepOverlayBuildV1),
            (self.first_threshold_rebase, MultiStepThresholdRebaseV1),
            (self.first_plan_proposal, MultiStepPlanProposalV1),
            (self.first_plan_audit, MultiStepPlanAuditV1),
            (self.round_two_request, MultiStepEvidenceRequestV1),
            (self.round_two_bundle, MultiStepEvidenceBundleV1),
            (self.final_overlay_build, MultiStepOverlayBuildV1),
            (self.final_threshold_rebase, MultiStepThresholdRebaseV1),
            (self.final_plan_proposal, MultiStepPlanProposalV1),
            (self.final_plan_audit, MultiStepPlanAuditV1),
            (self.telemetry, MultiStepRefinementTelemetryV1),
        )
        if any(type(value) is not expected for value, expected in exact_types):
            raise MultiStepRefinementInvariantViolation(
                "multi-step result rejects nested runtime-type substitutions"
            )
        final = self.final_plan_audit.audit_result
        if (
            self.round_one_request.round_index != 1
            or self.round_one_bundle.request_id != self.round_one_request.request_id
            or self.first_overlay_build.evidence_bundle_id
            != self.round_one_bundle.bundle_id
            or self.first_plan_audit.audit_result.outcome
            is not PartialAuditOutcome.FAILED_PROOF_FRONTIER
            or self.round_two_request.round_index != 2
            or self.round_two_bundle.request_id != self.round_two_request.request_id
            or self.final_overlay_build.previous_model_id
            != self.first_overlay_build.model.model_id
            or self.final_overlay_build.evidence_bundle_id
            != self.round_two_bundle.bundle_id
            or final.outcome is not PartialAuditOutcome.CERTIFIED_FIXED_PLAN
            or final.certificate is None
            or final.robust_bounds.policy_reward_lower != 1
            or final.robust_bounds.policy_reward_upper != 1
            or final.robust_bounds.policy_failure_lower != 0
            or final.robust_bounds.policy_failure_upper != 0
            or final.robust_bounds.normalized_distribution_regret != 0
            or self.status != SUCCESS_STATUS
            or self.promotion_disposition != "RETAIN_QUERY_LOCAL_OVERLAY_ONLY"
            or self.reusable_base_mutated is not False
            or self.general_causal_minimality_claimed is not False
            or self.sample_saving_claimed is not False
        ):
            raise MultiStepRefinementInvariantViolation(
                "multi-step result does not close the frozen H2 value/risk chain"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.multistep_query_refinement_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_observed_synthesis_result_id": (
                self.source_observed_synthesis_result_id
            ),
            "source_thresholds_id": self.source_thresholds_id,
            "source_plan_proposal_result_id": (
                self.source_plan_proposal_result_id
            ),
            "source_plan_id": self.source_plan_id,
            "source_failed_typed_audit_result_id": (
                self.source_failed_typed_audit_result_id
            ),
            "round_one_request": self.round_one_request.to_document(),
            "round_one_bundle": self.round_one_bundle.to_document(),
            "boundary_expansion": self.boundary_expansion.to_document(),
            "first_overlay_build": self.first_overlay_build.to_document(),
            "first_threshold_rebase": self.first_threshold_rebase.to_document(),
            "first_plan_proposal": self.first_plan_proposal.to_document(),
            "first_plan_audit": self.first_plan_audit.to_document(),
            "round_two_request": self.round_two_request.to_document(),
            "round_two_bundle": self.round_two_bundle.to_document(),
            "final_overlay_build": self.final_overlay_build.to_document(),
            "final_threshold_rebase": self.final_threshold_rebase.to_document(),
            "final_plan_proposal": self.final_plan_proposal.to_document(),
            "final_plan_audit": self.final_plan_audit.to_document(),
            "telemetry": self.telemetry.to_document(),
            "status": self.status,
            "promotion_disposition": self.promotion_disposition,
            "reusable_base_mutated": self.reusable_base_mutated,
            "general_causal_minimality_claimed": (
                self.general_causal_minimality_claimed
            ),
            "sample_saving_claimed": self.sample_saving_claimed,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _verified_h2_failure_chain(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    failed_audit: TypedPartialSoundAuditResultV2,
):
    if type(observed_synthesis_result) is not ObservedTypedPartialRAPMResultV1:
        raise MultiStepRefinementInvariantViolation(
            "V0-047 requires the exact V0-045 synthesis result"
        )
    if type(base_plan_proposal) is not TypedPartialModelPlanProposalResultV2:
        raise MultiStepRefinementInvariantViolation(
            "V0-047 requires the exact typed V0-044 proposal"
        )
    if type(failed_audit) is not TypedPartialSoundAuditResultV2:
        raise MultiStepRefinementInvariantViolation(
            "V0-047 requires the exact typed V0-043 failed audit"
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
        raise MultiStepRefinementInvariantViolation(str(error)) from error
    if verified_plan.trace.outcome is not PartialModelPlannerOutcome.PLAN_PROPOSED:
        raise MultiStepRefinementInvariantViolation(
            "V0-047 requires a selected base plan"
        )
    plan = verified_plan.selected_plan
    if type(plan) is not FrozenContingentAbstractPlanV1:
        raise MultiStepRefinementInvariantViolation(
            "verified base proposal contains no exact plan"
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
        raise MultiStepRefinementInvariantViolation(str(error)) from error
    inner = verified_audit.audit_result
    frontier = inner.failed_proof_frontier
    model = observed_synthesis_result.partial_build_result.model
    if (
        thresholds.horizon != 2
        or thresholds.risk_tolerance != 0
        or thresholds.normalized_regret_tolerance != 0
        or len(thresholds.initial_state_distribution) != 1
        or inner.outcome is not PartialAuditOutcome.FAILED_PROOF_FRONTIER
        or type(frontier) is not PartialFailedProofFrontierV1
        or frontier.earliest_time_index != 0
        or frontier.remaining_horizon != 2
        or frontier.risk_obligation_failed is not True
        or frontier.value_obligation_failed is not True
        or frontier.reason
        not in (
            FailedProofReason.EXTERNAL_COVERAGE_ESCAPE,
            FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION,
        )
    ):
        raise MultiStepRefinementInvariantViolation(
            "V0-047 accepts only the canonical H2 zero-risk/zero-regret failed frontier"
        )
    initial_state_id = thresholds.initial_state_distribution[0].state_id
    missing_sources = {
        row.state_id
        for row in model.ground_rows
        if row.status is AmbiguityRowStatus.MISSING_VACUOUS
    }
    if missing_sources != {initial_state_id}:
        raise MultiStepRefinementInvariantViolation(
            "canonical H2 source must start at the sole all-missing active state"
        )
    return model, verified_plan, plan, verified_audit, frontier


def _ground_row_maps(model):
    ground_by_id = {item.ground_row_id: item for item in model.ground_rows}
    concretizer_by_pair = {
        (item.state_id, item.semantic_action_id): item
        for item in model.concretizer_rows
    }
    return ground_by_id, concretizer_by_pair


def _round_one_request(
    model,
    thresholds: FrozenPartialAuditThresholdsV1,
    plan_proposal: TypedPartialModelPlanProposalResultV2,
    plan: FrozenContingentAbstractPlanV1,
    failed_audit: TypedPartialSoundAuditResultV2,
    frontier: PartialFailedProofFrontierV1,
) -> MultiStepEvidenceRequestV1:
    ground_by_id, concretizer_by_pair = _ground_row_maps(model)
    if len(frontier.obligations) != 1:
        raise MultiStepRefinementInvariantViolation(
            "canonical H2 time-zero frontier must contain one realization obligation"
        )
    obligation = frontier.obligations[0]
    if (
        obligation.time_index != 0
        or obligation.remaining_horizon != 2
        or len(obligation.missing_ground_row_ids) != 4
        or obligation.observed_ground_row_ids
    ):
        raise MultiStepRefinementInvariantViolation(
            "canonical H2 time-zero obligation must be the four-row missing realization"
        )
    concretizer = concretizer_by_pair[(
        obligation.state_id,
        obligation.semantic_action_id,
    )]
    probability_by_row = {
        ground_by_id[
            next(
                row_id
                for row_id in obligation.support_ground_row_ids
                if ground_by_id[row_id].ground_action_id == action_id
            )
        ].ground_row_id: probability
        for action_id, probability in concretizer.support
    }
    unrestricted = {
        item.ground_row_id: item.reward_upper
        for item in failed_audit.audit_result.robust_bounds.unrestricted_rows
        if item.time_index == 0
    }
    proofs = tuple(
        MultiStepRowNecessityProofV1(
            1,
            model.model_id,
            thresholds.thresholds_id,
            plan.plan_id,
            failed_audit.result_id,
            frontier.frontier_id,
            row_id,
            obligation.state_id,
            obligation.cell_id,
            obligation.semantic_action_id,
            probability_by_row[row_id],
            obligation.reachable_cell_mass_upper,
            probability_by_row[row_id]
            * obligation.reachable_cell_mass_upper,
            unrestricted[row_id],
            failed_audit.audit_result.robust_bounds.policy_reward_lower,
            thresholds.risk_tolerance,
            thresholds.normalized_regret_tolerance,
            True,
            True,
            False,
        )
        for row_id in obligation.missing_ground_row_ids
    )
    return MultiStepEvidenceRequestV1(
        1,
        MultiStepEvidencePhase.INITIAL_FRONTIER_ROWS,
        model.model_id,
        thresholds.thresholds_id,
        plan.plan_id,
        plan_proposal.result_id,
        failed_audit.result_id,
        frontier.frontier_id,
        tuple(item.ground_row_id for item in proofs),
        proofs,
        len(proofs),
        0,
        len(proofs),
    )


def _action_and_state_maps(
    observation_log: ObservationLogManifestV1,
    boundary: MultiStepBoundaryExpansionV1 | None,
):
    states = {item.state_id: item for item in observation_log.states}
    catalogues: dict[str, Any] = {
        item.state_id: item for item in observation_log.action_catalogues
    }
    if boundary is not None:
        for catalogue in boundary.catalogues:
            states[catalogue.state.state_id] = catalogue.state
            catalogues[catalogue.state.state_id] = catalogue
    actions = {
        action.ground_row_id: action
        for catalogue in catalogues.values()
        for action in catalogue.actions
    }
    return states, catalogues, actions


def _validate_canonical_kernel(
    kernel: LMBKernel,
    observation_log: ObservationLogManifestV1,
    authority,
) -> None:
    if type(kernel) is not LMBKernel:
        raise MultiStepRefinementInvariantViolation(
            "V0-047 exact acquisition rejects substituted kernels"
        )
    if (
        kernel.tile_types != authority.tile_types
        or kernel.blockers != authority.blockers
        or kernel.type_count != authority.type_count
        or kernel.capacity != authority.capacity
        or kernel.max_layers != authority.max_layers
        or observation_log.structural_id != authority.structural_id
        or _kernel_source_digest() != authority.implementation_sha256
    ):
        raise MultiStepRefinementInvariantViolation(
            "V0-047 exact-kernel/source structural authority mismatch"
        )


def _acquire(
    round_index: int,
    request: MultiStepEvidenceRequestV1,
    observation_log: ObservationLogManifestV1,
    boundary: MultiStepBoundaryExpansionV1 | None,
    kernel: LMBKernel,
) -> MultiStepEvidenceBundleV1:
    authority = canonical_lmb_query_kernel_authority_v1()
    _validate_canonical_kernel(kernel, observation_log, authority)
    states, _, actions = _action_and_state_maps(observation_log, boundary)
    registered_state_ids = set(states)
    evidence: list[MultiStepTransitionEvidenceV1] = []
    for sequence, row_id in enumerate(request.requested_ground_row_ids, start=1):
        action = actions.get(row_id)
        if action is None:
            raise MultiStepRefinementInvariantViolation(
                "authorized row is absent from the complete current action catalogues"
            )
        state = states[action.state_id]
        outcomes = kernel.step(_lmb_state(state), LMBAction(_tile(action)))
        if type(outcomes) is not tuple or len(outcomes) != 1 or outcomes[0].probability != 1:
            raise MultiStepRefinementInvariantViolation(
                "V0-047 requires deterministic singleton transition evidence"
            )
        outcome = outcomes[0]
        successor_state = _state_observation(outcome.next_state)
        successor = ObservedSuccessorRefV1(
            (
                SuccessorKind.REGISTERED_STATE
                if successor_state.state_id in registered_state_ids
                else SuccessorKind.EXTERNAL_STATE
            ),
            successor_state.state_id,
        )
        receipt = _content_id(
            "receipt",
            {
                "schema": "acfqp.multistep_exact_transition_receipt.v1",
                "profile_key": PROFILE_KEY,
                "round_index": round_index,
                "sequence_number": sequence,
                "request_id": request.request_id,
                "kernel_authority_id": authority.authority_id,
                "ground_row_id": row_id,
                "successor": successor.to_document(),
                "successor_state": successor_state.to_document(),
                "reward_features": [
                    {"name": name, "value": _fraction_document(value)}
                    for name, value in outcome.reward_features
                ],
                "failure": outcome.failure,
                "terminal": outcome.terminal,
            },
        )
        evidence.append(
            MultiStepTransitionEvidenceV1(
                round_index,
                sequence,
                request.request_id,
                authority.authority_id,
                row_id,
                state.state_id,
                action.action_id,
                successor,
                successor_state,
                outcome.reward_features,
                outcome.failure,
                outcome.terminal,
                receipt,
            )
        )
    return MultiStepEvidenceBundleV1(
        round_index,
        request.request_id,
        authority.authority_id,
        tuple(evidence),
        request.requested_ground_row_ids,
        len(evidence),
        len(evidence),
    )


def _expand_boundary(
    observation_log: ObservationLogManifestV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    request: MultiStepEvidenceRequestV1,
    bundle: MultiStepEvidenceBundleV1,
    kernel: LMBKernel,
) -> MultiStepBoundaryExpansionV1:
    authority = canonical_lmb_query_kernel_authority_v1()
    _validate_canonical_kernel(kernel, observation_log, authority)
    base_state_ids = {item.state_id for item in observation_log.states}
    evidence_by_state: dict[str, list[str]] = {}
    successor_by_state: dict[str, CanonicalStateObservationV1] = {}
    for item in bundle.evidence:
        if item.terminal or item.successor_state.state_id in base_state_ids:
            continue
        evidence_by_state.setdefault(item.successor_state.state_id, []).append(
            item.evidence_id
        )
        successor_by_state[item.successor_state.state_id] = item.successor_state
    catalogues: list[QueryLocalCompleteActionCatalogueV1] = []
    for sequence, state_id in enumerate(sorted(successor_by_state), start=1):
        state = successor_by_state[state_id]
        ground_state = _lmb_state(state)
        actions = tuple(
            sorted(
                (
                    CanonicalGroundActionV1(
                        state.state_id,
                        f"tile={action.tile}",
                        kernel.tile_types[action.tile],
                    )
                    for action in kernel.actions(ground_state)
                ),
                key=lambda item: item.action_id,
            )
        )
        catalogues.append(
            QueryLocalCompleteActionCatalogueV1(
                sequence,
                state,
                actions,
                tuple(sorted(evidence_by_state[state_id])),
                authority.authority_id,
            )
        )
    catalogues_tuple = tuple(catalogues)
    expansion = MultiStepBoundaryExpansionV1(
        observed_synthesis_result.partial_build_result.model.model_id,
        request.request_id,
        bundle.bundle_id,
        authority.authority_id,
        observed_synthesis_result.coordinate_proposal.proposal_id,
        observed_synthesis_result.dsl_registry.registry_id,
        observed_synthesis_result.structural_binding.binding_id,
        catalogues_tuple,
        tuple(sorted(item.state.state_id for item in catalogues_tuple)),
        tuple(
            sorted(
                action.ground_row_id
                for item in catalogues_tuple
                for action in item.actions
            )
        ),
        len(catalogues_tuple),
    )
    if (
        len(expansion.catalogues) != 3
        or len(expansion.registered_boundary_ground_row_ids) != 9
    ):
        raise MultiStepRefinementInvariantViolation(
            "canonical H2 boundary expansion must expose three states and nine rows"
        )
    return expansion


def _evaluate_coordinates(
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    states: Mapping[str, CanonicalStateObservationV1],
    catalogues: Mapping[str, Any],
):
    proposal = observed_synthesis_result.coordinate_proposal
    structural = observed_synthesis_result.structural_binding
    state_programs = {
        item.expression_id: item
        for item in observed_synthesis_result.dsl_registry.state_programs
    }
    action_programs = {
        item.expression_id: item
        for item in observed_synthesis_result.dsl_registry.action_programs
    }
    state_values: dict[str, tuple[int, ...]] = {}
    action_labels: dict[str, tuple[bool, ...]] = {}
    for state_id in sorted(states):
        state = states[state_id]
        catalogue = catalogues[state_id]
        if state.planning_kind is PlanningKind.ACTIVE:
            values = tuple(
                _eval_expression(
                    state_programs[expression_id],
                    state,
                    catalogue,
                    None,
                    structural,
                )
                for expression_id in proposal.state_expression_ids
            )
            if any(type(value) is not int for value in values):
                raise MultiStepRefinementInvariantViolation(
                    "selected state coordinates returned nonintegers on a boundary state"
                )
            state_values[state_id] = values
        else:
            state_values[state_id] = ()
        for action in catalogue.actions:
            raw_values = {
                expression_id: _eval_expression(
                    action_programs[expression_id],
                    state,
                    catalogue,
                    action,
                    structural,
                )
                for expression_id in proposal.action_expression_ids
            }
            labels: list[bool] = []
            for atom in proposal.action_atoms:
                if atom.kind is TypedActionAtomKind.UNIVERSAL_TRUE:
                    labels.append(True)
                elif atom.kind is TypedActionAtomKind.BOOLEAN_IDENTITY:
                    value = raw_values[atom.source_expression_id]
                    if type(value) is not bool:
                        raise MultiStepRefinementInvariantViolation(
                            "boolean action atom received a nonboolean boundary value"
                        )
                    labels.append(value)
                else:
                    value = raw_values[atom.source_expression_id]
                    if type(value) is not int:
                        raise MultiStepRefinementInvariantViolation(
                            "integer action atom received a noninteger boundary value"
                        )
                    labels.append(Fraction(value) <= atom.threshold)
            action_labels[action.ground_row_id] = tuple(labels)
    return state_values, action_labels


def _overlay_ledger_id(
    base_ledger_id: str,
    previous_model_id: str,
    bundles: tuple[MultiStepEvidenceBundleV1, ...],
    boundary: MultiStepBoundaryExpansionV1,
) -> str:
    return _content_id(
        "overlay_ledger",
        {
            "schema": "acfqp.multistep_overlay_ledger.v1",
            "profile_key": PROFILE_KEY,
            "base_evidence_ledger_id": base_ledger_id,
            "previous_model_id": previous_model_id,
            "bundle_ids": [item.bundle_id for item in bundles],
            "evidence_ledger_ids": [item.evidence_ledger_id for item in bundles],
            "boundary_expansion_id": boundary.expansion_id,
        },
    )


def _assemble_overlay(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_plan: FrozenContingentAbstractPlanV1,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    request: MultiStepEvidenceRequestV1,
    current_bundle: MultiStepEvidenceBundleV1,
    all_bundles: tuple[MultiStepEvidenceBundleV1, ...],
    boundary: MultiStepBoundaryExpansionV1,
    previous_model_id: str,
) -> QueryScopedPartialRAPMV3:
    base = observed_synthesis_result.partial_build_result.model
    states, catalogues, actions = _action_and_state_maps(observation_log, boundary)
    state_values, action_labels = _evaluate_coordinates(
        observed_synthesis_result, states, catalogues
    )

    grouped: dict[tuple[PlanningKind, tuple[int, ...]], list[str]] = {}
    for state_id, state in states.items():
        grouped.setdefault((state.planning_kind, state_values[state_id]), []).append(
            state_id
        )
    cells = tuple(
        sorted(
            (
                PartialCellV1(tuple(sorted(member_ids)), planning_kind, coordinates)
                for (planning_kind, coordinates), member_ids in grouped.items()
            ),
            key=lambda item: item.cell_id,
        )
    )
    cell_by_state = {
        state_id: cell for cell in cells for state_id in cell.member_state_ids
    }
    active_cell_ids = tuple(
        sorted(
            item.cell_id for item in cells if item.planning_kind is PlanningKind.ACTIVE
        )
    )
    destinations = tuple(sorted((*active_cell_ids, base.external_boundary_id)))

    base_observations = {item.ground_row_id: item for item in observation_log.observations}
    query_evidence = {
        item.ground_row_id: item
        for bundle in all_bundles
        for item in bundle.evidence
    }
    ground_rows: list[PartialGroundRowV1] = []
    ground_by_id: dict[str, PartialGroundRowV1] = {}
    for row_id in sorted(actions):
        action = actions[row_id]
        source = query_evidence.get(row_id) or base_observations.get(row_id)
        if source is None:
            ambiguity = _ambiguity_payload(
                known_reward={},
                known_successor={},
                known_failure=Fraction(0),
                known_terminal=Fraction(0),
                unknown_mass=Fraction(1),
                destinations=destinations,
                external_boundary_id=base.external_boundary_id,
                caps=semantics_profile.reward_feature_caps,
            )
            row = PartialGroundRowV1(
                row_id,
                action.state_id,
                action.action_id,
                AmbiguityRowStatus.MISSING_VACUOUS,
                (),
                ambiguity,
            )
        else:
            successor = source.successor
            known_successor: dict[str, Fraction] = {}
            if not source.terminal:
                destination = (
                    cell_by_state[successor.reference].cell_id
                    if successor.reference in cell_by_state
                    else base.external_boundary_id
                )
                known_successor[destination] = Fraction(1)
            ambiguity = _ambiguity_payload(
                known_reward=dict(source.reward_features),
                known_successor=known_successor,
                known_failure=Fraction(int(source.failure)),
                known_terminal=Fraction(int(source.terminal)),
                unknown_mass=Fraction(0),
                destinations=destinations,
                external_boundary_id=base.external_boundary_id,
                caps=semantics_profile.reward_feature_caps,
            )
            evidence_id = (
                source.evidence_id
                if type(source) is MultiStepTransitionEvidenceV1
                else source.observation_id
            )
            row = PartialGroundRowV1(
                row_id,
                action.state_id,
                action.action_id,
                AmbiguityRowStatus.OBSERVED_SINGLETON,
                (evidence_id,),
                ambiguity,
            )
        ground_rows.append(row)
        ground_by_id[row_id] = row
    ground_rows_tuple = tuple(ground_rows)

    semantic_actions: list[PartialSemanticActionV1] = []
    concretizers: list[ConcretizerRowV1] = []
    realizations: list[PartialSemanticRealizationV1] = []
    for cell in cells:
        if cell.planning_kind is not PlanningKind.ACTIVE:
            continue
        labels_by_state: dict[
            str, dict[tuple[bool, ...], list[CanonicalGroundActionV1]]
        ] = {}
        common_labels: set[tuple[bool, ...]] | None = None
        for state_id in cell.member_state_ids:
            by_label: dict[tuple[bool, ...], list[CanonicalGroundActionV1]] = {}
            for action in catalogues[state_id].actions:
                by_label.setdefault(action_labels[action.ground_row_id], []).append(
                    action
                )
            labels_by_state[state_id] = by_label
            labels = set(by_label)
            common_labels = labels if common_labels is None else common_labels & labels
        if not common_labels or any(
            set(labels_by_state[state_id]) != common_labels
            for state_id in cell.member_state_ids
        ):
            raise MultiStepRefinementInvariantViolation(
                "reused typed coordinate cell lacks an exact common semantic-action label set"
            )
        for label in sorted(common_labels):
            semantic_action = PartialSemanticActionV1(cell.cell_id, label)
            semantic_actions.append(semantic_action)
            for state_id in cell.member_state_ids:
                support_actions = tuple(
                    sorted(
                        labels_by_state[state_id][label],
                        key=lambda item: item.action_id,
                    )
                )
                weight = Fraction(1, len(support_actions))
                concretizers.append(
                    ConcretizerRowV1(
                        state_id,
                        cell.cell_id,
                        semantic_action.semantic_action_id,
                        tuple((item.action_id, weight) for item in support_actions),
                    )
                )
                support_rows = tuple(
                    ground_by_id[item.ground_row_id] for item in support_actions
                )
                observed_ids = tuple(
                    sorted(
                        item.ground_row_id
                        for item in support_rows
                        if item.status is AmbiguityRowStatus.OBSERVED_SINGLETON
                    )
                )
                missing_ids = tuple(
                    sorted(
                        item.ground_row_id
                        for item in support_rows
                        if item.status is AmbiguityRowStatus.MISSING_VACUOUS
                    )
                )
                known_reward: dict[str, Fraction] = {}
                known_successor: dict[str, Fraction] = {}
                known_failure = Fraction(0)
                known_terminal = Fraction(0)
                for row in support_rows:
                    if row.status is not AmbiguityRowStatus.OBSERVED_SINGLETON:
                        continue
                    for name, value in row.ambiguity.known_reward_features:
                        known_reward[name] = known_reward.get(name, Fraction(0)) + weight * value
                    for destination, mass in row.ambiguity.known_successor_masses:
                        known_successor[destination] = known_successor.get(destination, Fraction(0)) + weight * mass
                    known_failure += weight * row.ambiguity.known_failure_mass
                    known_terminal += weight * row.ambiguity.known_terminal_mass
                realizations.append(
                    PartialSemanticRealizationV1(
                        state_id,
                        cell.cell_id,
                        semantic_action.semantic_action_id,
                        tuple(sorted(item.ground_row_id for item in support_rows)),
                        observed_ids,
                        missing_ids,
                        _ambiguity_payload(
                            known_reward=known_reward,
                            known_successor=known_successor,
                            known_failure=known_failure,
                            known_terminal=known_terminal,
                            unknown_mass=Fraction(len(missing_ids), len(support_rows)),
                            destinations=destinations,
                            external_boundary_id=base.external_boundary_id,
                            caps=semantics_profile.reward_feature_caps,
                        ),
                    )
                )
    semantic_actions_tuple = tuple(
        sorted(semantic_actions, key=lambda item: item.semantic_action_id)
    )
    concretizers_tuple = tuple(
        sorted(concretizers, key=lambda item: (item.state_id, item.semantic_action_id))
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
        tuple(sorted(states)),
        tuple(item.ground_row_id for item in ground_rows_tuple),
        observed_ids,
        missing_ids,
        base.external_boundary_id,
    )
    ledger_id = _overlay_ledger_id(
        base.evidence_ledger_id, previous_model_id, all_bundles, boundary
    )
    return QueryScopedPartialRAPMV3(
        semantics_profile.profile_id,
        semantics_profile.horizon_cap,
        observation_log.log_id,
        observed_synthesis_result.coordinate_proposal.proposal_id,
        base.observation_authority_id,
        base.acquisition_manifest_id,
        base.acquisition_coverage_id,
        ledger_id,
        coverage,
        base.external_boundary_id,
        cells,
        semantic_actions_tuple,
        concretizers_tuple,
        ground_rows_tuple,
        realizations_tuple,
        semantics_profile.reward_feature_caps,
        base.model_id,
        previous_model_id,
        observed_synthesis_result.result_id,
        source_thresholds.thresholds_id,
        source_plan.plan_id,
        source_failed_audit.result_id,
        request.request_id,
        current_bundle.bundle_id,
        boundary.expansion_id,
        ledger_id,
        request.round_index,
        sum(item.exact_kernel_query_count for item in all_bundles),
        len(boundary.registered_boundary_state_ids),
    )


def _build_result(
    round_index: int,
    model: QueryScopedPartialRAPMV3,
    base_model_id: str,
    previous_model_id: str,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_plan: FrozenContingentAbstractPlanV1,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    request: MultiStepEvidenceRequestV1,
    bundle: MultiStepEvidenceBundleV1,
    boundary: MultiStepBoundaryExpansionV1,
) -> MultiStepOverlayBuildV1:
    return MultiStepOverlayBuildV1(
        round_index,
        base_model_id,
        previous_model_id,
        source_thresholds.thresholds_id,
        source_plan.plan_id,
        source_failed_audit.result_id,
        request.request_id,
        bundle.bundle_id,
        boundary.expansion_id,
        model.overlay_ledger_id,
        model,
        len(model.coverage.observed_ground_row_ids),
        len(model.coverage.missing_ground_row_ids),
        len(boundary.registered_boundary_state_ids),
        len(boundary.registered_boundary_ground_row_ids),
        bundle.exact_kernel_query_count,
        model.cumulative_exact_kernel_query_count,
    )


def _rebase(
    build: MultiStepOverlayBuildV1,
    source: FrozenPartialAuditThresholdsV1,
) -> MultiStepThresholdRebaseV1:
    rebased = FrozenPartialAuditThresholdsV1(
        build.model.model_id,
        source.horizon,
        source.initial_state_distribution,
        source.reward_weights,
        source.normalized_regret_tolerance,
        source.risk_tolerance,
        source.return_bound_proof,
    )
    return MultiStepThresholdRebaseV1(
        build.result_id,
        source.thresholds_id,
        source.partial_model_id,
        build.model.model_id,
        rebased,
    )


def _semantic_plan_key(
    model: QueryScopedPartialRAPMV3,
    plan: FrozenContingentAbstractPlanV1,
) -> tuple[int, ...]:
    cell_by_id = {item.cell_id: item for item in model.cells}
    action_by_id = {
        item.semantic_action_id: item for item in model.semantic_actions
    }
    ordered_cell_ids = tuple(
        item.cell_id
        for item in sorted(
            (
                cell
                for cell in model.cells
                if cell.planning_kind is PlanningKind.ACTIVE
            ),
            key=lambda cell: (cell.coordinate_values, cell.member_state_ids),
        )
    )
    result: list[int] = []
    for stage in plan.stages:
        assignment_by_cell = {
            item.cell_id: item.semantic_action_id for item in stage.assignments
        }
        if set(assignment_by_cell) != set(ordered_cell_ids):
            raise MultiStepRefinementInvariantViolation(
                "semantic tie-break received an incomplete plan stage"
            )
        for cell_id in ordered_cell_ids:
            action = action_by_id[assignment_by_cell[cell_id]]
            if action.cell_id != cell_by_id[cell_id].cell_id:
                raise MultiStepRefinementInvariantViolation(
                    "semantic tie-break action/cell binding mismatch"
                )
            result.extend(int(value) for value in action.label_values)
    return tuple(result)


def _select_with_semantic_tie_break(
    model: QueryScopedPartialRAPMV3,
    summaries: tuple[PartialPlannerCandidateSummaryV1, ...],
    plans: Mapping[str, FrozenContingentAbstractPlanV1],
):
    mode, provisional = _selected_summary(summaries)
    best_numeric = _selection_numeric_key(mode, provisional)
    tied = tuple(
        item
        for item in summaries
        if _selection_numeric_key(mode, item) == best_numeric
    )
    selected = min(
        tied,
        key=lambda item: (
            _semantic_plan_key(model, plans[item.contingent_plan_id]),
            item.contingent_plan_id,
        ),
    )
    return mode, selected, _semantic_plan_key(
        model, plans[selected.contingent_plan_id]
    )


def _propose(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    build: MultiStepOverlayBuildV1,
    rebase: MultiStepThresholdRebaseV1,
) -> MultiStepPlanProposalV1:
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
        raise MultiStepRefinementInvariantViolation(
            "V0-047 candidate enumeration exceeds the frozen production cap"
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
    selection_mode, selected, semantic_key = _select_with_semantic_tie_break(
        model, summaries_tuple, plans
    )
    return MultiStepPlanProposalV1(
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
        "NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1",
        semantic_key,
        candidate_count,
    )


def _audit(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    request: MultiStepEvidenceRequestV1,
    bundle: MultiStepEvidenceBundleV1,
    build: MultiStepOverlayBuildV1,
    rebase: MultiStepThresholdRebaseV1,
    proposal: MultiStepPlanProposalV1,
) -> MultiStepPlanAuditV1:
    audit = _audit_verified_partial_model_v1(
        build.model,
        observation_log,
        semantics_profile,
        observation_authority,
        rebase.rebased_thresholds,
        proposal.selected_plan,
    )
    return MultiStepPlanAuditV1(
        build.result_id,
        build.model.model_id,
        request.request_id,
        bundle.bundle_id,
        rebase.rebase_id,
        proposal.result_id,
        proposal.selected_plan.plan_id,
        audit,
    )


def _round_two_request(
    build: MultiStepOverlayBuildV1,
    rebase: MultiStepThresholdRebaseV1,
    proposal: MultiStepPlanProposalV1,
    audit: MultiStepPlanAuditV1,
    boundary: MultiStepBoundaryExpansionV1,
) -> MultiStepEvidenceRequestV1:
    inner = audit.audit_result
    frontier = inner.failed_proof_frontier
    if (
        inner.outcome is not PartialAuditOutcome.FAILED_PROOF_FRONTIER
        or type(frontier) is not PartialFailedProofFrontierV1
        or frontier.earliest_time_index != 1
        or frontier.remaining_horizon != 1
        or frontier.reason
        is not FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION
        or frontier.risk_obligation_failed is not True
        or frontier.value_obligation_failed is not True
        or frontier.external_coverage_failed is not False
    ):
        raise MultiStepRefinementInvariantViolation(
            "first overlay must move the failed proof frontier from time zero to time one"
        )
    model = build.model
    ground_by_id, concretizer_by_pair = _ground_row_maps(model)
    new_state_ids = set(boundary.registered_boundary_state_ids)
    candidate_rows = tuple(
        sorted(
            item.ground_row_id
            for item in model.ground_rows
            if item.state_id in new_state_ids
            and item.status is AmbiguityRowStatus.MISSING_VACUOUS
        )
    )
    selected_support_rows = {
        row_id for item in frontier.obligations for row_id in item.missing_ground_row_ids
    }
    obligation_by_row = {
        row_id: item
        for item in frontier.obligations
        for row_id in item.support_ground_row_ids
    }
    stage_one_assignments = {
        item.cell_id: item.semantic_action_id
        for item in proposal.selected_plan.stages[1].assignments
    }
    unrestricted = {
        item.ground_row_id: item
        for item in inner.robust_bounds.unrestricted_rows
        if item.time_index == 1 and item.state_id in new_state_ids
    }
    proofs: list[MultiStepRowNecessityProofV1] = []
    for row_id in candidate_rows:
        row = ground_by_id[row_id]
        cell = next(
            item for item in model.cells if row.state_id in item.member_state_ids
        )
        selected_semantic_action_id = stage_one_assignments[cell.cell_id]
        selected = row_id in selected_support_rows
        semantic_action_id = selected_semantic_action_id
        probability = Fraction(1)
        if selected:
            concretizer = concretizer_by_pair[(row.state_id, semantic_action_id)]
            probability = next(
                value
                for action_id, value in concretizer.support
                if action_id == row.ground_action_id
            )
            obligation = obligation_by_row[row_id]
            reach = obligation.reachable_cell_mass_upper
        else:
            matching = tuple(
                item
                for (state_id, _), item in concretizer_by_pair.items()
                if state_id == row.state_id
                and any(
                    action_id == row.ground_action_id
                    for action_id, _ in item.support
                )
            )
            if len(matching) != 1:
                raise MultiStepRefinementInvariantViolation(
                    "each downstream ground row must belong to one semantic action"
                )
            semantic_action_id = matching[0].semantic_action_id
            probability = next(
                value
                for action_id, value in matching[0].support
                if action_id == row.ground_action_id
            )
            reach = Fraction(1)
        unrestricted_row = unrestricted[row_id]
        required_for_value = (
            unrestricted_row.reward_upper
            > inner.robust_bounds.policy_reward_lower
        )
        proofs.append(
            MultiStepRowNecessityProofV1(
                2,
                model.model_id,
                rebase.rebased_thresholds.thresholds_id,
                proposal.selected_plan.plan_id,
                audit.result_id,
                frontier.frontier_id,
                row_id,
                row.state_id,
                cell.cell_id,
                semantic_action_id,
                probability,
                reach,
                probability * reach,
                unrestricted_row.reward_upper,
                inner.robust_bounds.policy_reward_lower,
                rebase.rebased_thresholds.risk_tolerance,
                rebase.rebased_thresholds.normalized_regret_tolerance,
                selected,
                selected,
                required_for_value,
            )
        )
    proofs_tuple = tuple(sorted(proofs, key=lambda item: item.ground_row_id))
    if (
        len(proofs_tuple) != 9
        or sum(item.required_for_risk for item in proofs_tuple) != 3
        or sum(item.required_for_value for item in proofs_tuple) != 9
    ):
        raise MultiStepRefinementInvariantViolation(
            "canonical downstream proof scope must contain 3 risk and 9 value rows"
        )
    return MultiStepEvidenceRequestV1(
        2,
        MultiStepEvidencePhase.DOWNSTREAM_VALUE_RISK_ROWS,
        model.model_id,
        rebase.rebased_thresholds.thresholds_id,
        proposal.selected_plan.plan_id,
        proposal.result_id,
        audit.result_id,
        frontier.frontier_id,
        tuple(item.ground_row_id for item in proofs_tuple),
        proofs_tuple,
        3,
        9,
        9,
    )


def _coordinate_reuse_count(base_model, expanded_model) -> int:
    base_counts = {
        (item.planning_kind, item.coordinate_values): len(item.member_state_ids)
        for item in base_model.cells
        if item.planning_kind is PlanningKind.ACTIVE
    }
    expanded_counts = {
        (item.planning_kind, item.coordinate_values): len(item.member_state_ids)
        for item in expanded_model.cells
        if item.planning_kind is PlanningKind.ACTIVE
    }
    return sum(
        1
        for signature, base_count in base_counts.items()
        if expanded_counts.get(signature, 0) > base_count
    )


def run_lmb_h2_multistep_query_refinement_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    failed_audit: TypedPartialSoundAuditResultV2,
    kernel: LMBKernel,
) -> MultiStepQueryRefinementResultV1:
    """Run the complete V0-047 H2 multi-step refinement positive control."""

    model, verified_plan, source_plan, verified_audit, frontier = (
        _verified_h2_failure_chain(
            observation_log,
            semantics_profile,
            observation_authority,
            observed_synthesis_result,
            thresholds,
            base_plan_proposal,
            failed_audit,
        )
    )
    base_document = model.to_document()
    request_one = _round_one_request(
        model,
        thresholds,
        verified_plan,
        source_plan,
        verified_audit,
        frontier,
    )
    bundle_one = _acquire(1, request_one, observation_log, None, kernel)
    boundary = _expand_boundary(
        observation_log,
        observed_synthesis_result,
        request_one,
        bundle_one,
        kernel,
    )
    model_one = _assemble_overlay(
        observation_log,
        semantics_profile,
        observed_synthesis_result,
        thresholds,
        source_plan,
        verified_audit,
        request_one,
        bundle_one,
        (bundle_one,),
        boundary,
        model.model_id,
    )
    build_one = _build_result(
        1,
        model_one,
        model.model_id,
        model.model_id,
        thresholds,
        source_plan,
        verified_audit,
        request_one,
        bundle_one,
        boundary,
    )
    rebase_one = _rebase(build_one, thresholds)
    proposal_one = _propose(
        observation_log,
        semantics_profile,
        observation_authority,
        build_one,
        rebase_one,
    )
    audit_one = _audit(
        observation_log,
        semantics_profile,
        observation_authority,
        request_one,
        bundle_one,
        build_one,
        rebase_one,
        proposal_one,
    )
    request_two = _round_two_request(
        build_one, rebase_one, proposal_one, audit_one, boundary
    )
    bundle_two = _acquire(2, request_two, observation_log, boundary, kernel)
    model_two = _assemble_overlay(
        observation_log,
        semantics_profile,
        observed_synthesis_result,
        thresholds,
        source_plan,
        verified_audit,
        request_two,
        bundle_two,
        (bundle_one, bundle_two),
        boundary,
        model_one.model_id,
    )
    build_two = _build_result(
        2,
        model_two,
        model.model_id,
        model_one.model_id,
        thresholds,
        source_plan,
        verified_audit,
        request_two,
        bundle_two,
        boundary,
    )
    rebase_two = _rebase(build_two, thresholds)
    proposal_two = _propose(
        observation_log,
        semantics_profile,
        observation_authority,
        build_two,
        rebase_two,
    )
    audit_two = _audit(
        observation_log,
        semantics_profile,
        observation_authority,
        request_two,
        bundle_two,
        build_two,
        rebase_two,
        proposal_two,
    )
    telemetry = MultiStepRefinementTelemetryV1(
        len(model.coverage.observed_ground_row_ids),
        len(model.coverage.missing_ground_row_ids),
        bundle_one.exact_kernel_query_count,
        boundary.action_catalogue_query_count,
        len(model_one.coverage.observed_ground_row_ids),
        len(model_one.coverage.missing_ground_row_ids),
        bundle_two.exact_kernel_query_count,
        len(model_two.coverage.observed_ground_row_ids),
        len(model_two.coverage.missing_ground_row_ids),
        bundle_one.exact_kernel_query_count + bundle_two.exact_kernel_query_count,
        len(boundary.registered_boundary_state_ids),
        len(boundary.registered_boundary_ground_row_ids),
        2,
        proposal_one.fixed_plan_audit_count + proposal_two.fixed_plan_audit_count,
        _coordinate_reuse_count(model, model_two),
    )
    if (
        model.to_document() != base_document
        or (
            telemetry.base_observed_ground_rows,
            telemetry.base_missing_ground_rows,
            telemetry.round_one_exact_kernel_queries,
            telemetry.boundary_action_catalogue_queries,
            telemetry.first_overlay_observed_ground_rows,
            telemetry.first_overlay_missing_ground_rows,
            telemetry.round_two_exact_kernel_queries,
            telemetry.final_overlay_observed_ground_rows,
            telemetry.final_overlay_missing_ground_rows,
            telemetry.cumulative_exact_kernel_queries,
            telemetry.new_boundary_state_count,
            telemetry.new_boundary_action_count,
            telemetry.replanning_pass_count,
            telemetry.total_candidate_plan_audits,
            telemetry.reused_existing_coordinate_signature_count,
        )
        != (7, 4, 4, 3, 11, 9, 9, 20, 0, 13, 3, 9, 2, 8, 1)
    ):
        raise MultiStepRefinementInvariantViolation(
            "canonical H2 telemetry or base immutability changed"
        )
    return MultiStepQueryRefinementResultV1(
        observed_synthesis_result.result_id,
        thresholds.thresholds_id,
        verified_plan.result_id,
        source_plan.plan_id,
        verified_audit.result_id,
        request_one,
        bundle_one,
        boundary,
        build_one,
        rebase_one,
        proposal_one,
        audit_one,
        request_two,
        bundle_two,
        build_two,
        rebase_two,
        proposal_two,
        audit_two,
        telemetry,
    )


def verify_lmb_h2_multistep_query_refinement_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    failed_audit: TypedPartialSoundAuditResultV2,
    kernel: LMBKernel,
    claimed_result: MultiStepQueryRefinementResultV1,
) -> MultiStepQueryRefinementResultV1:
    """Independently replay every source, evidence, overlay and audit artifact."""

    if type(claimed_result) is not MultiStepQueryRefinementResultV1:
        raise MultiStepRefinementInvariantViolation(
            "V0-047 verifier rejects substituted result artifacts"
        )
    expected = run_lmb_h2_multistep_query_refinement_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        thresholds,
        base_plan_proposal,
        failed_audit,
        kernel,
    )
    if claimed_result.to_document() != expected.to_document():
        raise MultiStepRefinementInvariantViolation(
            "V0-047 independent replay differs from the claimed result"
        )
    return expected


__all__ = [
    "MultiStepBoundaryExpansionV1",
    "MultiStepEvidenceBundleV1",
    "MultiStepEvidencePhase",
    "MultiStepEvidenceRequestV1",
    "MultiStepOverlayBuildV1",
    "MultiStepPlanAuditV1",
    "MultiStepPlanProposalV1",
    "MultiStepQueryRefinementResultV1",
    "MultiStepRefinementInvariantViolation",
    "MultiStepRefinementTelemetryV1",
    "MultiStepRowNecessityProofV1",
    "MultiStepThresholdRebaseV1",
    "MultiStepTransitionEvidenceV1",
    "PROFILE_KEY",
    "QueryLocalCompleteActionCatalogueV1",
    "SCHEMA_VERSION",
    "SUCCESS_STATUS",
    "canonical_lmb_query_kernel_authority_v1",
    "canonical_lmb_query_kernel_v1",
    "run_lmb_h2_multistep_query_refinement_v1",
    "verify_lmb_h2_multistep_query_refinement_v1",
]
