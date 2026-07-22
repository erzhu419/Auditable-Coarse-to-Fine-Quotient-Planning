"""V0-048 preregistered cross-query promotion and held-out model reuse.

The source is the complete V0-047 H2 refinement result.  Before that source
acquisition is considered, this module freezes a distinct H1 target whose
initial state is absent from the V0-045 observation graph.  Promotion copies
the complete verified final model, never a target-filtered subset, into a new
scope-limited reusable epoch.  The target planner and auditor receive no
kernel.  A separate evaluation lane replays the cold target's one catalogue
and three transitions to provide a matched acquisition trace.

This is a finite exact positive control.  It does not claim unrestricted
query neutrality, statistical generalization, sample efficiency, learned
dynamics, or an official workload/economics Gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import inspect
from itertools import product
from typing import Any, Mapping

from acfqp.domains.matching_buffer import LMBAction, LMBKernel, LMBState, LMBStatus
from acfqp.multistep_query_refinement_v1 import (
    MultiStepQueryRefinementResultV1,
    _lmb_state,
    _selection_numeric_key,
    _semantic_plan_key,
    _state_observation,
    _validate_canonical_kernel,
    run_lmb_h2_multistep_query_refinement_v1,
    verify_lmb_h2_multistep_query_refinement_v1,
)
from acfqp.observation_partial_rapm_v1 import (
    CanonicalGroundActionV1,
    CanonicalStateObservationV1,
    DeterministicObservationProfileV1,
    ObservationLogManifestV1,
    PlanningKind,
    PreregisteredObservationAuthorityV1,
    PreregisteredReusablePartialRAPMV4,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    ObservedTypedPartialRAPMResultV1,
    verify_observed_lmb_partial_rapm_v1,
)
from acfqp.partial_model_planner_v1 import (
    PartialModelPlannerSelectionMode,
    PartialPlannerCandidateSummaryV1,
    PartialPlannerCellActionDomainV1,
    _candidate_summary,
    _planner_context,
    _selected_summary,
    _stage_assignments,
)
from acfqp.partial_sound_audit_v1 import (
    ContingentPlanStageV1,
    FrozenContingentAbstractPlanV1,
    FrozenPartialAuditThresholdsV1,
    InitialStateMassV1,
    PartialAuditOutcome,
    PartialSoundAuditResultV1,
    RewardWeightV1,
    TypedPartialSoundAuditResultV2,
    _audit_verified_partial_model_v1,
    canonical_lmb_n6_return_bound_proof_v1,
)
from acfqp.partial_model_planner_v1 import TypedPartialModelPlanProposalResultV2
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.query_local_refinement_v1 import (
    canonical_lmb_query_kernel_authority_v1,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "lmb_preregistered_h1_cross_query_promotion_v0"
SUCCESS_STATUS = "CERTIFIED_PREREGISTERED_HELD_OUT_REUSE"
TARGET_GROUND_STATE = LMBState(11, (1, 2), LMBStatus.ACTIVE)
SOURCE_GROUND_STATE = LMBState(3, (1, 1), LMBStatus.ACTIVE)
SOURCE_RUNNER_PARAMETERS = (
    "observation_log",
    "semantics_profile",
    "observation_authority",
    "observed_synthesis_result",
    "thresholds",
    "base_plan_proposal",
    "failed_audit",
    "kernel",
)

DOMAIN_TAGS = {
    "target_query": "acfqp:held-out-query-spec:v1",
    "protocol": "acfqp:cross-query-reuse-protocol:v1",
    "eligibility": "acfqp:promotion-eligibility-proof:v1",
    "promotion": "acfqp:promoted-reusable-model-build:v1",
    "threshold_binding": "acfqp:held-out-threshold-binding:v1",
    "planner": "acfqp:held-out-model-only-plan-proposal:v1",
    "audit": "acfqp:held-out-independent-plan-audit:v1",
    "cold_catalogue": "acfqp:cold-target-action-catalogue:v1",
    "cold_outcome": "acfqp:cold-target-transition-outcome:v1",
    "cold_trace": "acfqp:cold-target-acquisition-trace:v1",
    "telemetry": "acfqp:cross-query-reuse-telemetry:v1",
    "result": "acfqp:cross-query-promotion-result:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-048 content-ID domains must be unique")


class CrossQueryPromotionInvariantViolation(ValueError):
    """The preregistration, promotion, reuse, or matched trace is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise CrossQueryPromotionInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise CrossQueryPromotionInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CrossQueryPromotionInvariantViolation(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field: str) -> Fraction:
    if type(value) not in (int, Fraction):
        raise CrossQueryPromotionInvariantViolation(f"{field} must be exact")
    return Fraction(value)


def _fraction_document(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _sorted_ids(
    values: tuple[str, ...], field: str, *, expected_count: int | None = None
) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or not values
        or any(type(item) is not str for item in values)
        or values != tuple(sorted(set(values)))
    ):
        raise CrossQueryPromotionInvariantViolation(
            f"{field} must be a nonempty unique sorted tuple"
        )
    for item in values:
        _cid(item, field)
    if expected_count is not None and len(values) != expected_count:
        raise CrossQueryPromotionInvariantViolation(
            f"{field} must contain exactly {expected_count} IDs"
        )
    return values


@dataclass(frozen=True, slots=True)
class HeldOutQuerySpecV1:
    structural_id: str
    environment_instance_id: str
    observation_log_id: str
    semantics_profile_id: str
    base_model_id: str
    initial_state: CanonicalStateObservationV1
    reward_weights: tuple[RewardWeightV1, ...]
    return_bound_proof_id: str
    horizon: int = 1
    normalized_regret_tolerance: Fraction = Fraction(0)
    risk_tolerance: Fraction = Fraction(0)
    query_role: str = "PREREGISTERED_HELD_OUT_REUSE_TARGET"
    registration_phase: str = "BEFORE_SOURCE_REFINEMENT_ACQUISITION"

    def __post_init__(self) -> None:
        for field in (
            "structural_id",
            "environment_instance_id",
            "observation_log_id",
            "semantics_profile_id",
            "base_model_id",
            "return_bound_proof_id",
        ):
            _cid(getattr(self, field), f"held-out query {field}")
        if type(self.initial_state) is not CanonicalStateObservationV1:
            raise CrossQueryPromotionInvariantViolation(
                "held-out query rejects substituted state observations"
            )
        if self.initial_state.to_document() != _state_observation(
            TARGET_GROUND_STATE
        ).to_document():
            raise CrossQueryPromotionInvariantViolation(
                "held-out query state differs from the frozen source-independent target"
            )
        if (
            type(self.reward_weights) is not tuple
            or any(type(item) is not RewardWeightV1 for item in self.reward_weights)
            or self.reward_weights
            != (
                RewardWeightV1("match", Fraction(1)),
                RewardWeightV1("terminal_clear", Fraction(1)),
            )
        ):
            raise CrossQueryPromotionInvariantViolation(
                "held-out query reward basis differs from the canonical profile"
            )
        object.__setattr__(
            self,
            "normalized_regret_tolerance",
            _fraction(
                self.normalized_regret_tolerance,
                "held-out normalized regret tolerance",
            ),
        )
        object.__setattr__(
            self,
            "risk_tolerance",
            _fraction(self.risk_tolerance, "held-out risk tolerance"),
        )
        if (
            self.horizon != 1
            or self.normalized_regret_tolerance != 0
            or self.risk_tolerance != 0
            or self.initial_state.planning_kind is not PlanningKind.ACTIVE
            or self.query_role != "PREREGISTERED_HELD_OUT_REUSE_TARGET"
            or self.registration_phase
            != "BEFORE_SOURCE_REFINEMENT_ACQUISITION"
        ):
            raise CrossQueryPromotionInvariantViolation(
                "held-out query parameters or preregistration role changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_query_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "structural_id": self.structural_id,
            "environment_instance_id": self.environment_instance_id,
            "observation_log_id": self.observation_log_id,
            "semantics_profile_id": self.semantics_profile_id,
            "base_model_id": self.base_model_id,
            "initial_state": self.initial_state.to_document(),
            "horizon": self.horizon,
            "reward_weights": [item.to_document() for item in self.reward_weights],
            "normalized_regret_tolerance": _fraction_document(
                self.normalized_regret_tolerance
            ),
            "risk_tolerance": _fraction_document(self.risk_tolerance),
            "return_bound_proof_id": self.return_bound_proof_id,
            "query_role": self.query_role,
            "registration_phase": self.registration_phase,
        }

    @property
    def query_id(self) -> str:
        return _content_id("target_query", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_id": self.query_id}


@dataclass(frozen=True, slots=True)
class CrossQueryReuseProtocolV1:
    observed_synthesis_result_id: str
    base_model_id: str
    source_thresholds_id: str
    source_initial_state_id: str
    target_query: HeldOutQuerySpecV1
    source_runner_parameter_names: tuple[str, ...]
    source_horizon: int = 2
    source_query_target_input_count: int = 0
    registered_target_count: int = 1
    target_absent_from_base_registry: bool = True
    source_and_target_initial_states_distinct: bool = True
    complete_source_final_model_promotion_required: bool = True
    target_filtered_row_selection_forbidden: bool = True
    promotion_scope_kind: str = "PREREGISTERED_INITIAL_STATE_AND_HORIZON"

    def __post_init__(self) -> None:
        for field in (
            "observed_synthesis_result_id",
            "base_model_id",
            "source_thresholds_id",
            "source_initial_state_id",
        ):
            _cid(getattr(self, field), f"cross-query protocol {field}")
        if type(self.target_query) is not HeldOutQuerySpecV1:
            raise CrossQueryPromotionInvariantViolation(
                "cross-query protocol rejects substituted target queries"
            )
        if (
            type(self.source_runner_parameter_names) is not tuple
            or self.source_runner_parameter_names != SOURCE_RUNNER_PARAMETERS
            or self.source_initial_state_id == self.target_query.initial_state.state_id
            or self.target_query.base_model_id != self.base_model_id
        ):
            raise CrossQueryPromotionInvariantViolation(
                "source API, model, or source/target separation changed"
            )
        for field, expected in (
            ("source_horizon", 2),
            ("source_query_target_input_count", 0),
            ("registered_target_count", 1),
        ):
            _integer(getattr(self, field), f"cross-query protocol {field}")
            if getattr(self, field) != expected:
                raise CrossQueryPromotionInvariantViolation(
                    f"cross-query protocol {field} changed"
                )
        if (
            self.target_absent_from_base_registry is not True
            or self.source_and_target_initial_states_distinct is not True
            or self.complete_source_final_model_promotion_required is not True
            or self.target_filtered_row_selection_forbidden is not True
            or self.promotion_scope_kind
            != "PREREGISTERED_INITIAL_STATE_AND_HORIZON"
        ):
            raise CrossQueryPromotionInvariantViolation(
                "cross-query protocol weakened its leakage or promotion boundary"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_query_reuse_protocol.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "observed_synthesis_result_id": self.observed_synthesis_result_id,
            "base_model_id": self.base_model_id,
            "source_thresholds_id": self.source_thresholds_id,
            "source_initial_state_id": self.source_initial_state_id,
            "source_horizon": self.source_horizon,
            "target_query": self.target_query.to_document(),
            "source_runner_parameter_names": list(
                self.source_runner_parameter_names
            ),
            "source_query_target_input_count": self.source_query_target_input_count,
            "registered_target_count": self.registered_target_count,
            "target_absent_from_base_registry": self.target_absent_from_base_registry,
            "source_and_target_initial_states_distinct": (
                self.source_and_target_initial_states_distinct
            ),
            "complete_source_final_model_promotion_required": (
                self.complete_source_final_model_promotion_required
            ),
            "target_filtered_row_selection_forbidden": (
                self.target_filtered_row_selection_forbidden
            ),
            "promotion_scope_kind": self.promotion_scope_kind,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("protocol", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


@dataclass(frozen=True, slots=True)
class PromotionEligibilityProofV1:
    protocol_id: str
    target_query_id: str
    source_refinement_result_id: str
    source_base_model_id: str
    source_final_model_id: str
    complete_promoted_ground_row_ids: tuple[str, ...]
    source_exact_evidence_ids: tuple[str, ...]
    source_boundary_catalogue_ids: tuple[str, ...]
    target_ground_row_ids: tuple[str, ...]
    source_base_observed_row_count: int
    source_exact_evidence_row_count: int
    source_final_observed_row_count: int
    source_final_missing_row_count: int
    independent_replay_transition_calls: int
    independent_replay_direct_catalogue_calls: int
    target_filtered_row_count: int = 0
    complete_source_model_selected: bool = True
    source_query_target_input_count: int = 0
    source_acquisition_query_neutral: bool = False
    reusable_only_inside_preregistered_scope: bool = True
    eligibility_outcome: str = "ELIGIBLE_FOR_PREREGISTERED_SCOPED_REUSE"

    def __post_init__(self) -> None:
        for field in (
            "protocol_id",
            "target_query_id",
            "source_refinement_result_id",
            "source_base_model_id",
            "source_final_model_id",
        ):
            _cid(getattr(self, field), f"promotion eligibility {field}")
        _sorted_ids(
            self.complete_promoted_ground_row_ids,
            "promotion complete ground rows",
            expected_count=20,
        )
        _sorted_ids(
            self.source_exact_evidence_ids,
            "promotion source exact evidence",
            expected_count=13,
        )
        _sorted_ids(
            self.source_boundary_catalogue_ids,
            "promotion source boundary catalogues",
            expected_count=3,
        )
        _sorted_ids(
            self.target_ground_row_ids,
            "promotion target rows",
            expected_count=3,
        )
        expected_counts = {
            "source_base_observed_row_count": 7,
            "source_exact_evidence_row_count": 13,
            "source_final_observed_row_count": 20,
            "source_final_missing_row_count": 0,
            "independent_replay_transition_calls": 13,
            "independent_replay_direct_catalogue_calls": 3,
            "target_filtered_row_count": 0,
            "source_query_target_input_count": 0,
        }
        for field, expected in expected_counts.items():
            _integer(getattr(self, field), f"promotion eligibility {field}")
            if getattr(self, field) != expected:
                raise CrossQueryPromotionInvariantViolation(
                    f"promotion eligibility {field} changed"
                )
        if (
            not set(self.target_ground_row_ids)
            <= set(self.complete_promoted_ground_row_ids)
            or self.complete_source_model_selected is not True
            or self.source_acquisition_query_neutral is not False
            or self.reusable_only_inside_preregistered_scope is not True
            or self.eligibility_outcome
            != "ELIGIBLE_FOR_PREREGISTERED_SCOPED_REUSE"
        ):
            raise CrossQueryPromotionInvariantViolation(
                "promotion eligibility overclaims or target-filters the source"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.promotion_eligibility_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field: getattr(self, field)
                for field in (
                    "protocol_id",
                    "target_query_id",
                    "source_refinement_result_id",
                    "source_base_model_id",
                    "source_final_model_id",
                    "source_base_observed_row_count",
                    "source_exact_evidence_row_count",
                    "source_final_observed_row_count",
                    "source_final_missing_row_count",
                    "independent_replay_transition_calls",
                    "independent_replay_direct_catalogue_calls",
                    "target_filtered_row_count",
                    "complete_source_model_selected",
                    "source_query_target_input_count",
                    "source_acquisition_query_neutral",
                    "reusable_only_inside_preregistered_scope",
                    "eligibility_outcome",
                )
            },
            "complete_promoted_ground_row_ids": list(
                self.complete_promoted_ground_row_ids
            ),
            "source_exact_evidence_ids": list(self.source_exact_evidence_ids),
            "source_boundary_catalogue_ids": list(
                self.source_boundary_catalogue_ids
            ),
            "target_ground_row_ids": list(self.target_ground_row_ids),
        }

    @property
    def proof_id(self) -> str:
        return _content_id("eligibility", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


@dataclass(frozen=True, slots=True)
class PromotedReusableModelBuildV1:
    protocol: CrossQueryReuseProtocolV1
    eligibility_proof: PromotionEligibilityProofV1
    model: PreregisteredReusablePartialRAPMV4
    source_base_model_id: str
    source_final_model_id: str
    source_refinement_result_id: str
    promoted_observed_row_count: int = 20
    promoted_missing_row_count: int = 0
    promotion_epoch: int = 1
    base_model_mutated: bool = False
    complete_model_promoted: bool = True
    target_filtered_promotion: bool = False
    unrestricted_reuse_claimed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.protocol) is not CrossQueryReuseProtocolV1
            or type(self.eligibility_proof) is not PromotionEligibilityProofV1
            or type(self.model) is not PreregisteredReusablePartialRAPMV4
        ):
            raise CrossQueryPromotionInvariantViolation(
                "promotion build rejects substituted nested artifacts"
            )
        for field in (
            "source_base_model_id",
            "source_final_model_id",
            "source_refinement_result_id",
        ):
            _cid(getattr(self, field), f"promotion build {field}")
        if (
            self.eligibility_proof.protocol_id != self.protocol.protocol_id
            or self.eligibility_proof.target_query_id
            != self.protocol.target_query.query_id
            or self.model.promotion_protocol_id != self.protocol.protocol_id
            or self.model.promotion_eligibility_proof_id
            != self.eligibility_proof.proof_id
            or self.model.base_model_id != self.source_base_model_id
            or self.model.promoted_from_model_id != self.source_final_model_id
            or self.model.source_refinement_result_id
            != self.source_refinement_result_id
            or self.source_base_model_id != self.protocol.base_model_id
            or self.promoted_observed_row_count != 20
            or self.promoted_missing_row_count != 0
            or self.promotion_epoch != 1
            or self.base_model_mutated is not False
            or self.complete_model_promoted is not True
            or self.target_filtered_promotion is not False
            or self.unrestricted_reuse_claimed is not False
        ):
            raise CrossQueryPromotionInvariantViolation(
                "promotion build identities, counts, or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.promoted_reusable_model_build.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol": self.protocol.to_document(),
            "eligibility_proof": self.eligibility_proof.to_document(),
            "model": self.model.to_document(),
            "source_base_model_id": self.source_base_model_id,
            "source_final_model_id": self.source_final_model_id,
            "source_refinement_result_id": self.source_refinement_result_id,
            "promoted_observed_row_count": self.promoted_observed_row_count,
            "promoted_missing_row_count": self.promoted_missing_row_count,
            "promotion_epoch": self.promotion_epoch,
            "base_model_mutated": self.base_model_mutated,
            "complete_model_promoted": self.complete_model_promoted,
            "target_filtered_promotion": self.target_filtered_promotion,
            "unrestricted_reuse_claimed": self.unrestricted_reuse_claimed,
        }

    @property
    def result_id(self) -> str:
        return _content_id("promotion", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class HeldOutThresholdBindingV1:
    promotion_result_id: str
    protocol_id: str
    target_query_id: str
    promoted_model_id: str
    thresholds: FrozenPartialAuditThresholdsV1
    binding_kind: str = "PREREGISTERED_QUERY_TO_PROMOTED_MODEL_V1"

    def __post_init__(self) -> None:
        for field in (
            "promotion_result_id",
            "protocol_id",
            "target_query_id",
            "promoted_model_id",
        ):
            _cid(getattr(self, field), f"held-out threshold binding {field}")
        if type(self.thresholds) is not FrozenPartialAuditThresholdsV1:
            raise CrossQueryPromotionInvariantViolation(
                "held-out threshold binding rejects substituted thresholds"
            )
        if (
            self.thresholds.partial_model_id != self.promoted_model_id
            or self.thresholds.horizon != 1
            or len(self.thresholds.initial_state_distribution) != 1
            or self.thresholds.initial_state_distribution[0].probability != 1
            or self.thresholds.normalized_regret_tolerance != 0
            or self.thresholds.risk_tolerance != 0
            or self.binding_kind != "PREREGISTERED_QUERY_TO_PROMOTED_MODEL_V1"
        ):
            raise CrossQueryPromotionInvariantViolation(
                "held-out threshold binding changed its model or query semantics"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_threshold_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "promotion_result_id": self.promotion_result_id,
            "protocol_id": self.protocol_id,
            "target_query_id": self.target_query_id,
            "promoted_model_id": self.promoted_model_id,
            "thresholds": self.thresholds.to_document(),
            "binding_kind": self.binding_kind,
        }

    @property
    def binding_id(self) -> str:
        return _content_id("threshold_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class HeldOutPlanProposalV1:
    promotion_result_id: str
    protocol_id: str
    target_query_id: str
    promoted_model_id: str
    threshold_binding_id: str
    thresholds_id: str
    cell_action_domains: tuple[PartialPlannerCellActionDomainV1, ...]
    per_stage_assignment_count: int
    candidate_count: int
    candidate_summaries: tuple[PartialPlannerCandidateSummaryV1, ...]
    selection_mode: PartialModelPlannerSelectionMode
    selected_plan: FrozenContingentAbstractPlanV1
    selected_semantic_tie_break_key: tuple[int, ...]
    fixed_plan_audit_count: int
    semantic_tie_break_rule: str = (
        "NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1"
    )
    exact_kernel_calls_during_planning: int = 0
    direct_ground_optimizer_calls: int = 0

    def __post_init__(self) -> None:
        for field in (
            "promotion_result_id",
            "protocol_id",
            "target_query_id",
            "promoted_model_id",
            "threshold_binding_id",
            "thresholds_id",
        ):
            _cid(getattr(self, field), f"held-out planner {field}")
        if (
            type(self.cell_action_domains) is not tuple
            or any(
                type(item) is not PartialPlannerCellActionDomainV1
                for item in self.cell_action_domains
            )
            or tuple(item.cell_id for item in self.cell_action_domains)
            != tuple(sorted(set(item.cell_id for item in self.cell_action_domains)))
        ):
            raise CrossQueryPromotionInvariantViolation(
                "held-out planner domains are substituted, duplicate, or unsorted"
            )
        if (
            type(self.candidate_summaries) is not tuple
            or any(
                type(item) is not PartialPlannerCandidateSummaryV1
                for item in self.candidate_summaries
            )
            or tuple(
                item.contingent_plan_id for item in self.candidate_summaries
            )
            != tuple(
                sorted(
                    set(
                        item.contingent_plan_id
                        for item in self.candidate_summaries
                    )
                )
            )
        ):
            raise CrossQueryPromotionInvariantViolation(
                "held-out planner candidate summaries are invalid"
            )
        if (
            type(self.selection_mode) is not PartialModelPlannerSelectionMode
            or type(self.selected_plan) is not FrozenContingentAbstractPlanV1
        ):
            raise CrossQueryPromotionInvariantViolation(
                "held-out planner rejects substituted selection artifacts"
            )
        for field in (
            "per_stage_assignment_count",
            "candidate_count",
            "fixed_plan_audit_count",
            "exact_kernel_calls_during_planning",
            "direct_ground_optimizer_calls",
        ):
            _integer(getattr(self, field), f"held-out planner {field}")
        expected_stage_count = 1
        for domain in self.cell_action_domains:
            expected_stage_count *= len(domain.semantic_action_ids)
        mode, selected = _selected_summary(self.candidate_summaries)
        selected_summary = next(
            item
            for item in self.candidate_summaries
            if item.contingent_plan_id == self.selected_plan.plan_id
        )
        if (
            self.selected_plan.partial_model_id != self.promoted_model_id
            or self.selected_plan.horizon != 1
            or self.per_stage_assignment_count != expected_stage_count
            or self.candidate_count != expected_stage_count
            or self.candidate_count != 2
            or self.candidate_count != len(self.candidate_summaries)
            or self.fixed_plan_audit_count != self.candidate_count
            or any(
                item.partial_model_id != self.promoted_model_id
                or item.thresholds_id != self.thresholds_id
                for item in self.candidate_summaries
            )
            or self.selection_mode
            is not PartialModelPlannerSelectionMode.INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
            or mode is not self.selection_mode
            or _selection_numeric_key(mode, selected_summary)
            != _selection_numeric_key(mode, selected)
            or self.semantic_tie_break_rule
            != "NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1"
            or type(self.selected_semantic_tie_break_key) is not tuple
            or not self.selected_semantic_tie_break_key
            or any(
                type(item) is not int or item not in (0, 1)
                for item in self.selected_semantic_tie_break_key
            )
            or self.exact_kernel_calls_during_planning != 0
            or self.direct_ground_optimizer_calls != 0
        ):
            raise CrossQueryPromotionInvariantViolation(
                "held-out planner counts, selection, or no-ground boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_model_only_plan_proposal.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "promotion_result_id": self.promotion_result_id,
            "protocol_id": self.protocol_id,
            "target_query_id": self.target_query_id,
            "promoted_model_id": self.promoted_model_id,
            "threshold_binding_id": self.threshold_binding_id,
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
            "direct_ground_optimizer_calls": self.direct_ground_optimizer_calls,
        }

    @property
    def result_id(self) -> str:
        return _content_id("planner", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class HeldOutPlanAuditV1:
    promotion_result_id: str
    protocol_id: str
    target_query_id: str
    promoted_model_id: str
    threshold_binding_id: str
    planner_result_id: str
    selected_plan_id: str
    audit_result: PartialSoundAuditResultV1
    exact_kernel_calls_during_audit: int = 0
    direct_ground_optimizer_calls: int = 0
    independent_from_planner_selection: bool = True

    def __post_init__(self) -> None:
        for field in (
            "promotion_result_id",
            "protocol_id",
            "target_query_id",
            "promoted_model_id",
            "threshold_binding_id",
            "planner_result_id",
            "selected_plan_id",
        ):
            _cid(getattr(self, field), f"held-out audit {field}")
        if type(self.audit_result) is not PartialSoundAuditResultV1:
            raise CrossQueryPromotionInvariantViolation(
                "held-out audit rejects substituted inner results"
            )
        bounds = self.audit_result.robust_bounds
        if (
            self.audit_result.partial_model_id != self.promoted_model_id
            or self.audit_result.contingent_plan_id != self.selected_plan_id
            or self.audit_result.outcome is not PartialAuditOutcome.CERTIFIED_FIXED_PLAN
            or bounds.policy_reward_lower != 1
            or bounds.policy_reward_upper != 1
            or bounds.unrestricted_reward_upper != 1
            or bounds.policy_failure_lower != 0
            or bounds.policy_failure_upper != 0
            or bounds.normalized_distribution_regret != 0
            or bounds.external_coverage_certified is not True
            or self.exact_kernel_calls_during_audit != 0
            or self.direct_ground_optimizer_calls != 0
            or self.independent_from_planner_selection is not True
        ):
            raise CrossQueryPromotionInvariantViolation(
                "held-out audit did not certify exact 1/0/0 model-only reuse"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_independent_plan_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "promotion_result_id": self.promotion_result_id,
            "protocol_id": self.protocol_id,
            "target_query_id": self.target_query_id,
            "promoted_model_id": self.promoted_model_id,
            "threshold_binding_id": self.threshold_binding_id,
            "planner_result_id": self.planner_result_id,
            "selected_plan_id": self.selected_plan_id,
            "audit_result": self.audit_result.to_document(),
            "exact_kernel_calls_during_audit": self.exact_kernel_calls_during_audit,
            "direct_ground_optimizer_calls": self.direct_ground_optimizer_calls,
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
class ColdTargetActionCatalogueV1:
    protocol_id: str
    target_query_id: str
    promoted_model_id: str
    state: CanonicalStateObservationV1
    actions: tuple[CanonicalGroundActionV1, ...]
    matching_source_catalogue_id: str
    direct_catalogue_call_count: int = 1
    evaluation_lane_only: bool = True

    def __post_init__(self) -> None:
        for field in (
            "protocol_id",
            "target_query_id",
            "promoted_model_id",
            "matching_source_catalogue_id",
        ):
            _cid(getattr(self, field), f"cold catalogue {field}")
        if type(self.state) is not CanonicalStateObservationV1 or (
            type(self.actions) is not tuple
            or any(type(item) is not CanonicalGroundActionV1 for item in self.actions)
        ):
            raise CrossQueryPromotionInvariantViolation(
                "cold target catalogue rejects substituted state/actions"
            )
        if (
            self.state.to_document() != _state_observation(TARGET_GROUND_STATE).to_document()
            or len(self.actions) != 3
            or tuple(item.action_id for item in self.actions)
            != tuple(sorted(set(item.action_id for item in self.actions)))
            or any(item.state_id != self.state.state_id for item in self.actions)
            or self.direct_catalogue_call_count != 1
            or self.evaluation_lane_only is not True
        ):
            raise CrossQueryPromotionInvariantViolation(
                "cold target catalogue scope or count changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cold_target_action_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_id": self.protocol_id,
            "target_query_id": self.target_query_id,
            "promoted_model_id": self.promoted_model_id,
            "state": self.state.to_document(),
            "actions": [item.to_document() for item in self.actions],
            "matching_source_catalogue_id": self.matching_source_catalogue_id,
            "direct_catalogue_call_count": self.direct_catalogue_call_count,
            "evaluation_lane_only": self.evaluation_lane_only,
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("cold_catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_id": self.catalogue_id}


@dataclass(frozen=True, slots=True)
class ColdTargetTransitionOutcomeV1:
    sequence: int
    protocol_id: str
    target_query_id: str
    catalogue_id: str
    state_id: str
    action: CanonicalGroundActionV1
    successor_state: CanonicalStateObservationV1
    reward_features: tuple[tuple[str, Fraction], ...]
    failure: bool
    terminal: bool
    matching_source_evidence_id: str
    exact_transition_call_count: int = 1

    def __post_init__(self) -> None:
        _integer(self.sequence, "cold transition sequence", 1)
        for field in (
            "protocol_id",
            "target_query_id",
            "catalogue_id",
            "state_id",
            "matching_source_evidence_id",
        ):
            _cid(getattr(self, field), f"cold transition {field}")
        if (
            type(self.action) is not CanonicalGroundActionV1
            or type(self.successor_state) is not CanonicalStateObservationV1
            or type(self.reward_features) is not tuple
            or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or type(item[1]) not in (int, Fraction)
                for item in self.reward_features
            )
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or self.action.state_id != self.state_id
            or self.exact_transition_call_count != 1
        ):
            raise CrossQueryPromotionInvariantViolation(
                "cold transition outcome shape or count changed"
            )
        object.__setattr__(
            self,
            "reward_features",
            tuple((name, Fraction(value)) for name, value in self.reward_features),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cold_target_transition_outcome.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence": self.sequence,
            "protocol_id": self.protocol_id,
            "target_query_id": self.target_query_id,
            "catalogue_id": self.catalogue_id,
            "state_id": self.state_id,
            "action": self.action.to_document(),
            "successor_state": self.successor_state.to_document(),
            "reward_features": [
                {"name": name, "value": _fraction_document(value)}
                for name, value in self.reward_features
            ],
            "failure": self.failure,
            "terminal": self.terminal,
            "matching_source_evidence_id": self.matching_source_evidence_id,
            "exact_transition_call_count": self.exact_transition_call_count,
        }

    @property
    def outcome_id(self) -> str:
        return _content_id("cold_outcome", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_id": self.outcome_id}


@dataclass(frozen=True, slots=True)
class ColdTargetAcquisitionTraceV1:
    promotion_result_id: str
    protocol_id: str
    target_query_id: str
    promoted_model_id: str
    catalogue: ColdTargetActionCatalogueV1
    outcomes: tuple[ColdTargetTransitionOutcomeV1, ...]
    matched_source_evidence_ids: tuple[str, ...]
    direct_catalogue_calls: int = 1
    exact_transition_calls: int = 3
    step_internal_legality_checks: int = 3
    ground_search_calls: int = 0
    direct_ground_optimizer_calls: int = 0
    evaluation_lane_only: bool = True
    end_to_end_cold_planner_claimed: bool = False

    def __post_init__(self) -> None:
        for field in (
            "promotion_result_id",
            "protocol_id",
            "target_query_id",
            "promoted_model_id",
        ):
            _cid(getattr(self, field), f"cold trace {field}")
        if type(self.catalogue) is not ColdTargetActionCatalogueV1 or (
            type(self.outcomes) is not tuple
            or any(
                type(item) is not ColdTargetTransitionOutcomeV1
                for item in self.outcomes
            )
        ):
            raise CrossQueryPromotionInvariantViolation(
                "cold trace rejects substituted catalogue/outcomes"
            )
        _sorted_ids(
            self.matched_source_evidence_ids,
            "cold matched source evidence",
            expected_count=3,
        )
        for field, expected in (
            ("direct_catalogue_calls", 1),
            ("exact_transition_calls", 3),
            ("step_internal_legality_checks", 3),
            ("ground_search_calls", 0),
            ("direct_ground_optimizer_calls", 0),
        ):
            _integer(getattr(self, field), f"cold trace {field}")
            if getattr(self, field) != expected:
                raise CrossQueryPromotionInvariantViolation(
                    f"cold trace {field} changed"
                )
        if (
            self.catalogue.protocol_id != self.protocol_id
            or self.catalogue.target_query_id != self.target_query_id
            or self.catalogue.promoted_model_id != self.promoted_model_id
            or tuple(item.sequence for item in self.outcomes) != (1, 2, 3)
            or any(
                item.protocol_id != self.protocol_id
                or item.target_query_id != self.target_query_id
                or item.catalogue_id != self.catalogue.catalogue_id
                for item in self.outcomes
            )
            or tuple(
                sorted(item.matching_source_evidence_id for item in self.outcomes)
            )
            != self.matched_source_evidence_ids
            or self.evaluation_lane_only is not True
            or self.end_to_end_cold_planner_claimed is not False
        ):
            raise CrossQueryPromotionInvariantViolation(
                "cold trace identity, ordering, or evaluation-only scope changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cold_target_acquisition_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "promotion_result_id": self.promotion_result_id,
            "protocol_id": self.protocol_id,
            "target_query_id": self.target_query_id,
            "promoted_model_id": self.promoted_model_id,
            "catalogue": self.catalogue.to_document(),
            "outcomes": [item.to_document() for item in self.outcomes],
            "matched_source_evidence_ids": list(
                self.matched_source_evidence_ids
            ),
            "direct_catalogue_calls": self.direct_catalogue_calls,
            "exact_transition_calls": self.exact_transition_calls,
            "step_internal_legality_checks": self.step_internal_legality_checks,
            "ground_search_calls": self.ground_search_calls,
            "direct_ground_optimizer_calls": self.direct_ground_optimizer_calls,
            "evaluation_lane_only": self.evaluation_lane_only,
            "end_to_end_cold_planner_claimed": (
                self.end_to_end_cold_planner_claimed
            ),
        }

    @property
    def trace_id(self) -> str:
        return _content_id("cold_trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


@dataclass(frozen=True, slots=True)
class CrossQueryReuseTelemetryV1:
    source_refinement_transition_calls: int
    source_refinement_direct_catalogue_calls: int
    promotion_replay_transition_calls: int
    promotion_replay_direct_catalogue_calls: int
    warm_target_transition_calls: int
    warm_target_direct_catalogue_calls: int
    cold_evaluation_transition_calls: int
    cold_evaluation_direct_catalogue_calls: int
    cold_step_internal_legality_checks: int
    warm_model_only_replanning_passes: int
    warm_candidate_plan_audits: int
    promoted_ground_row_count: int
    reused_target_ground_row_count: int
    source_target_query_count: int = 2
    source_cost_amortization_included: bool = False
    cold_end_to_end_planner_claimed: bool = False
    sample_efficiency_claimed: bool = False
    official_scalar_cost: None = None
    official_n_break_even: None = None
    sample_efficiency_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        expected = {
            "source_refinement_transition_calls": 13,
            "source_refinement_direct_catalogue_calls": 3,
            "promotion_replay_transition_calls": 13,
            "promotion_replay_direct_catalogue_calls": 3,
            "warm_target_transition_calls": 0,
            "warm_target_direct_catalogue_calls": 0,
            "cold_evaluation_transition_calls": 3,
            "cold_evaluation_direct_catalogue_calls": 1,
            "cold_step_internal_legality_checks": 3,
            "warm_model_only_replanning_passes": 1,
            "warm_candidate_plan_audits": 2,
            "promoted_ground_row_count": 20,
            "reused_target_ground_row_count": 3,
            "source_target_query_count": 2,
        }
        for field, value in expected.items():
            _integer(getattr(self, field), f"cross-query telemetry {field}")
            if getattr(self, field) != value:
                raise CrossQueryPromotionInvariantViolation(
                    f"cross-query telemetry {field} changed"
                )
        if (
            self.source_cost_amortization_included is not False
            or self.cold_end_to_end_planner_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.official_scalar_cost is not None
            or self.official_n_break_even is not None
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            raise CrossQueryPromotionInvariantViolation(
                "cross-query telemetry overclaims savings or an official Gate"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_query_reuse_telemetry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field: getattr(self, field)
                for field in (
                    "source_refinement_transition_calls",
                    "source_refinement_direct_catalogue_calls",
                    "promotion_replay_transition_calls",
                    "promotion_replay_direct_catalogue_calls",
                    "warm_target_transition_calls",
                    "warm_target_direct_catalogue_calls",
                    "cold_evaluation_transition_calls",
                    "cold_evaluation_direct_catalogue_calls",
                    "cold_step_internal_legality_checks",
                    "warm_model_only_replanning_passes",
                    "warm_candidate_plan_audits",
                    "promoted_ground_row_count",
                    "reused_target_ground_row_count",
                    "source_target_query_count",
                    "source_cost_amortization_included",
                    "cold_end_to_end_planner_claimed",
                    "sample_efficiency_claimed",
                    "official_scalar_cost",
                    "official_n_break_even",
                    "sample_efficiency_gate_status",
                )
            },
        }

    @property
    def telemetry_id(self) -> str:
        return _content_id("telemetry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "telemetry_id": self.telemetry_id}


@dataclass(frozen=True, slots=True)
class CrossQueryPromotionResultV1:
    source_refinement_result_id: str
    promotion_build: PromotedReusableModelBuildV1
    threshold_binding: HeldOutThresholdBindingV1
    plan_proposal: HeldOutPlanProposalV1
    plan_audit: HeldOutPlanAuditV1
    cold_acquisition_trace: ColdTargetAcquisitionTraceV1
    telemetry: CrossQueryReuseTelemetryV1
    status: str = SUCCESS_STATUS
    held_out_reuse_certified: bool = True
    base_model_mutated: bool = False
    unrestricted_reuse_claimed: bool = False
    statistical_generalization_claimed: bool = False
    sample_efficiency_claimed: bool = False

    def __post_init__(self) -> None:
        _cid(self.source_refinement_result_id, "cross-query source result")
        if (
            type(self.promotion_build) is not PromotedReusableModelBuildV1
            or type(self.threshold_binding) is not HeldOutThresholdBindingV1
            or type(self.plan_proposal) is not HeldOutPlanProposalV1
            or type(self.plan_audit) is not HeldOutPlanAuditV1
            or type(self.cold_acquisition_trace)
            is not ColdTargetAcquisitionTraceV1
            or type(self.telemetry) is not CrossQueryReuseTelemetryV1
        ):
            raise CrossQueryPromotionInvariantViolation(
                "cross-query result rejects substituted nested artifacts"
            )
        promotion = self.promotion_build
        protocol = promotion.protocol
        target = protocol.target_query
        model = promotion.model
        if (
            promotion.source_refinement_result_id
            != self.source_refinement_result_id
            or self.threshold_binding.promotion_result_id != promotion.result_id
            or self.threshold_binding.protocol_id != protocol.protocol_id
            or self.threshold_binding.target_query_id != target.query_id
            or self.threshold_binding.promoted_model_id != model.model_id
            or self.threshold_binding.thresholds.initial_state_distribution[0].state_id
            != target.initial_state.state_id
            or self.threshold_binding.thresholds.horizon
            != target.horizon
            or self.plan_proposal.promotion_result_id != promotion.result_id
            or self.plan_proposal.protocol_id != protocol.protocol_id
            or self.plan_proposal.target_query_id != target.query_id
            or self.plan_proposal.promoted_model_id != model.model_id
            or self.plan_proposal.threshold_binding_id
            != self.threshold_binding.binding_id
            or self.plan_audit.promotion_result_id != promotion.result_id
            or self.plan_audit.protocol_id != protocol.protocol_id
            or self.plan_audit.target_query_id != target.query_id
            or self.plan_audit.promoted_model_id != model.model_id
            or self.plan_audit.threshold_binding_id
            != self.threshold_binding.binding_id
            or self.plan_audit.planner_result_id != self.plan_proposal.result_id
            or self.plan_audit.selected_plan_id
            != self.plan_proposal.selected_plan.plan_id
            or self.cold_acquisition_trace.promotion_result_id
            != promotion.result_id
            or self.cold_acquisition_trace.protocol_id != protocol.protocol_id
            or self.cold_acquisition_trace.target_query_id != target.query_id
            or self.cold_acquisition_trace.promoted_model_id != model.model_id
            or self.status != SUCCESS_STATUS
            or self.held_out_reuse_certified is not True
            or self.base_model_mutated is not False
            or self.unrestricted_reuse_claimed is not False
            or self.statistical_generalization_claimed is not False
            or self.sample_efficiency_claimed is not False
        ):
            raise CrossQueryPromotionInvariantViolation(
                "cross-query result identity chain or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_query_promotion_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_refinement_result_id": self.source_refinement_result_id,
            "promotion_build": self.promotion_build.to_document(),
            "threshold_binding": self.threshold_binding.to_document(),
            "plan_proposal": self.plan_proposal.to_document(),
            "plan_audit": self.plan_audit.to_document(),
            "cold_acquisition_trace": (
                self.cold_acquisition_trace.to_document()
            ),
            "telemetry": self.telemetry.to_document(),
            "status": self.status,
            "held_out_reuse_certified": self.held_out_reuse_certified,
            "base_model_mutated": self.base_model_mutated,
            "unrestricted_reuse_claimed": self.unrestricted_reuse_claimed,
            "statistical_generalization_claimed": (
                self.statistical_generalization_claimed
            ),
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def preregister_lmb_cross_query_reuse_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
) -> CrossQueryReuseProtocolV1:
    """Freeze the held-out target without any source-refinement artifact."""

    if type(observation_log) is not ObservationLogManifestV1:
        raise CrossQueryPromotionInvariantViolation(
            "preregistration rejects substituted observation logs"
        )
    if type(semantics_profile) is not DeterministicObservationProfileV1:
        raise CrossQueryPromotionInvariantViolation(
            "preregistration rejects substituted semantics profiles"
        )
    if type(observation_authority) is not PreregisteredObservationAuthorityV1:
        raise CrossQueryPromotionInvariantViolation(
            "preregistration rejects substituted observation authorities"
        )
    if type(observed_synthesis_result) is not ObservedTypedPartialRAPMResultV1:
        raise CrossQueryPromotionInvariantViolation(
            "preregistration rejects substituted synthesis results"
        )
    if type(source_thresholds) is not FrozenPartialAuditThresholdsV1:
        raise CrossQueryPromotionInvariantViolation(
            "preregistration rejects substituted source thresholds"
        )
    failures = verify_observed_lmb_partial_rapm_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
    )
    if failures:
        raise CrossQueryPromotionInvariantViolation(
            "preregistration source synthesis replay failed: " + ",".join(failures)
        )
    base_model = observed_synthesis_result.partial_build_result.model
    source_state = _state_observation(SOURCE_GROUND_STATE)
    target_state = _state_observation(TARGET_GROUND_STATE)
    if (
        source_thresholds.partial_model_id != base_model.model_id
        or source_thresholds.horizon != 2
        or source_thresholds.initial_state_distribution
        != (InitialStateMassV1(source_state.state_id, Fraction(1)),)
        or source_thresholds.reward_weights
        != (
            RewardWeightV1("match", Fraction(1)),
            RewardWeightV1("terminal_clear", Fraction(1)),
        )
        or source_thresholds.normalized_regret_tolerance != 0
        or source_thresholds.risk_tolerance != 0
        or target_state.state_id in {item.state_id for item in observation_log.states}
        or tuple(
            inspect.signature(
                run_lmb_h2_multistep_query_refinement_v1
            ).parameters
        )
        != SOURCE_RUNNER_PARAMETERS
    ):
        raise CrossQueryPromotionInvariantViolation(
            "source H2 context or pre-source target separation changed"
        )
    proof = canonical_lmb_n6_return_bound_proof_v1()
    target_query = HeldOutQuerySpecV1(
        observation_log.structural_id,
        observation_log.environment_instance_id,
        observation_log.log_id,
        semantics_profile.profile_id,
        base_model.model_id,
        target_state,
        source_thresholds.reward_weights,
        proof.proof_id,
    )
    return CrossQueryReuseProtocolV1(
        observed_synthesis_result.result_id,
        base_model.model_id,
        source_thresholds.thresholds_id,
        source_state.state_id,
        target_query,
        SOURCE_RUNNER_PARAMETERS,
    )


def _promotion_eligibility(
    protocol: CrossQueryReuseProtocolV1,
    source_result: MultiStepQueryRefinementResultV1,
) -> PromotionEligibilityProofV1:
    model = source_result.final_overlay_build.model
    target_state_id = protocol.target_query.initial_state.state_id
    complete_rows = tuple(sorted(item.ground_row_id for item in model.ground_rows))
    source_evidence = tuple(
        sorted(
            item.evidence_id
            for bundle in (
                source_result.round_one_bundle,
                source_result.round_two_bundle,
            )
            for item in bundle.evidence
        )
    )
    catalogues = tuple(
        sorted(
            item.catalogue_id
            for item in source_result.boundary_expansion.catalogues
        )
    )
    target_rows = tuple(
        sorted(
            item.ground_row_id
            for item in model.ground_rows
            if item.state_id == target_state_id
        )
    )
    if (
        complete_rows != model.coverage.observed_ground_row_ids
        or model.coverage.missing_ground_row_ids
        or target_state_id not in source_result.boundary_expansion.registered_boundary_state_ids
        or set(target_rows)
        != {
            action.ground_row_id
            for catalogue in source_result.boundary_expansion.catalogues
            if catalogue.state.state_id == target_state_id
            for action in catalogue.actions
        }
    ):
        raise CrossQueryPromotionInvariantViolation(
            "source final model is not complete over the preregistered target"
        )
    return PromotionEligibilityProofV1(
        protocol.protocol_id,
        protocol.target_query.query_id,
        source_result.result_id,
        protocol.base_model_id,
        model.model_id,
        complete_rows,
        source_evidence,
        catalogues,
        target_rows,
        7,
        13,
        20,
        0,
        13,
        3,
    )


def _promoted_model(
    protocol: CrossQueryReuseProtocolV1,
    proof: PromotionEligibilityProofV1,
    source_result: MultiStepQueryRefinementResultV1,
) -> PreregisteredReusablePartialRAPMV4:
    source = source_result.final_overlay_build.model
    return PreregisteredReusablePartialRAPMV4(
        source.semantics_profile_id,
        source.semantics_horizon_cap,
        source.observation_log_id,
        source.coordinate_proposal_id,
        source.observation_authority_id,
        source.acquisition_manifest_id,
        source.acquisition_coverage_id,
        source.evidence_ledger_id,
        source.coverage,
        source.external_boundary_id,
        source.cells,
        source.semantic_actions,
        source.concretizer_rows,
        source.ground_rows,
        source.semantic_realizations,
        source.reward_feature_caps,
        protocol.base_model_id,
        source.model_id,
        source_result.result_id,
        protocol.protocol_id,
        proof.proof_id,
        proof.complete_promoted_ground_row_ids,
        proof.source_exact_evidence_ids,
        (protocol.target_query.initial_state.state_id,),
        protocol.target_query.horizon,
    )


def promote_lmb_multistep_overlay_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    protocol: CrossQueryReuseProtocolV1,
    source_result: MultiStepQueryRefinementResultV1,
    kernel: LMBKernel,
) -> PromotedReusableModelBuildV1:
    """Independently replay V0-047 and promote its complete final model."""

    if type(protocol) is not CrossQueryReuseProtocolV1:
        raise CrossQueryPromotionInvariantViolation(
            "promotion rejects substituted preregistration protocols"
        )
    expected_protocol = preregister_lmb_cross_query_reuse_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        source_thresholds,
    )
    if protocol.to_document() != expected_protocol.to_document():
        raise CrossQueryPromotionInvariantViolation(
            "promotion protocol differs from pre-source reconstruction"
        )
    verified_source = verify_lmb_h2_multistep_query_refinement_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        source_thresholds,
        source_base_plan_proposal,
        source_failed_audit,
        kernel,
        source_result,
    )
    proof = _promotion_eligibility(protocol, verified_source)
    model = _promoted_model(protocol, proof, verified_source)
    return PromotedReusableModelBuildV1(
        protocol,
        proof,
        model,
        protocol.base_model_id,
        verified_source.final_overlay_build.model.model_id,
        verified_source.result_id,
    )


def _bind_target_thresholds(
    promotion: PromotedReusableModelBuildV1,
) -> HeldOutThresholdBindingV1:
    query = promotion.protocol.target_query
    proof = canonical_lmb_n6_return_bound_proof_v1()
    if query.return_bound_proof_id != proof.proof_id:
        raise CrossQueryPromotionInvariantViolation(
            "held-out query return-bound proof changed after preregistration"
        )
    thresholds = FrozenPartialAuditThresholdsV1(
        promotion.model.model_id,
        query.horizon,
        (InitialStateMassV1(query.initial_state.state_id, Fraction(1)),),
        query.reward_weights,
        query.normalized_regret_tolerance,
        query.risk_tolerance,
        proof,
    )
    return HeldOutThresholdBindingV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        query.query_id,
        promotion.model.model_id,
        thresholds,
    )


def _held_out_proposal(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: PromotedReusableModelBuildV1,
    binding: HeldOutThresholdBindingV1,
) -> HeldOutPlanProposalV1:
    model = promotion.model
    thresholds = binding.thresholds
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
    schedules = _stage_assignments(domains)
    plans: dict[str, FrozenContingentAbstractPlanV1] = {}
    summaries: list[PartialPlannerCandidateSummaryV1] = []
    for schedule in product(schedules, repeat=thresholds.horizon):
        plan = FrozenContingentAbstractPlanV1(
            model.model_id,
            thresholds.horizon,
            tuple(
                ContingentPlanStageV1(time_index, assignments)
                for time_index, assignments in enumerate(schedule)
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
    mode, provisional = _selected_summary(summaries_tuple)
    numeric_key = _selection_numeric_key(mode, provisional)
    tied = tuple(
        item
        for item in summaries_tuple
        if _selection_numeric_key(mode, item) == numeric_key
    )
    selected = min(
        tied,
        key=lambda item: (
            _semantic_plan_key(model, plans[item.contingent_plan_id]),
            item.contingent_plan_id,
        ),
    )
    return HeldOutPlanProposalV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        promotion.protocol.target_query.query_id,
        model.model_id,
        binding.binding_id,
        thresholds.thresholds_id,
        domains,
        stage_count,
        stage_count,
        summaries_tuple,
        mode,
        plans[selected.contingent_plan_id],
        _semantic_plan_key(model, plans[selected.contingent_plan_id]),
        len(summaries_tuple),
    )


def run_preregistered_heldout_query_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: PromotedReusableModelBuildV1,
) -> tuple[
    HeldOutThresholdBindingV1,
    HeldOutPlanProposalV1,
    HeldOutPlanAuditV1,
]:
    """Plan and certify the target without accepting a kernel or transition API."""

    if type(promotion) is not PromotedReusableModelBuildV1:
        raise CrossQueryPromotionInvariantViolation(
            "held-out consumer rejects substituted promotion builds"
        )
    target_state_id = promotion.protocol.target_query.initial_state.state_id
    if promotion.model.authorized_initial_state_ids != (target_state_id,):
        raise CrossQueryPromotionInvariantViolation(
            "held-out target lies outside the promoted reuse scope"
        )
    binding = _bind_target_thresholds(promotion)
    proposal = _held_out_proposal(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion,
        binding,
    )
    audit_result = _audit_verified_partial_model_v1(
        promotion.model,
        observation_log,
        semantics_profile,
        observation_authority,
        binding.thresholds,
        proposal.selected_plan,
    )
    audit = HeldOutPlanAuditV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        promotion.protocol.target_query.query_id,
        promotion.model.model_id,
        binding.binding_id,
        proposal.result_id,
        proposal.selected_plan.plan_id,
        audit_result,
    )
    return binding, proposal, audit


def evaluate_cold_heldout_acquisition_v1(
    observation_log: ObservationLogManifestV1,
    promotion: PromotedReusableModelBuildV1,
    source_result: MultiStepQueryRefinementResultV1,
    kernel: LMBKernel,
) -> ColdTargetAcquisitionTraceV1:
    """Replay only the target evidence in a separate evaluation lane."""

    if type(promotion) is not PromotedReusableModelBuildV1:
        raise CrossQueryPromotionInvariantViolation(
            "cold evaluation rejects substituted promotion builds"
        )
    if (
        type(source_result) is not MultiStepQueryRefinementResultV1
        or source_result.result_id != promotion.source_refinement_result_id
    ):
        raise CrossQueryPromotionInvariantViolation(
            "cold evaluation source does not match the promoted source result"
        )
    authority = canonical_lmb_query_kernel_authority_v1()
    _validate_canonical_kernel(kernel, observation_log, authority)
    protocol = promotion.protocol
    target = protocol.target_query
    ground_state = _lmb_state(target.initial_state)
    actions = tuple(
        sorted(
            (
                CanonicalGroundActionV1(
                    target.initial_state.state_id,
                    f"tile={action.tile}",
                    kernel.tile_types[action.tile],
                )
                for action in kernel.actions(ground_state)
            ),
            key=lambda item: item.action_id,
        )
    )
    source_catalogues = tuple(
        item
        for item in source_result.boundary_expansion.catalogues
        if item.state.state_id == target.initial_state.state_id
    )
    if (
        len(source_catalogues) != 1
        or tuple(item.to_document() for item in actions)
        != tuple(item.to_document() for item in source_catalogues[0].actions)
    ):
        raise CrossQueryPromotionInvariantViolation(
            "cold target catalogue differs from the promoted source catalogue"
        )
    catalogue = ColdTargetActionCatalogueV1(
        protocol.protocol_id,
        target.query_id,
        promotion.model.model_id,
        target.initial_state,
        actions,
        source_catalogues[0].catalogue_id,
    )
    evidence_by_row = {
        item.ground_row_id: item
        for bundle in (
            source_result.round_one_bundle,
            source_result.round_two_bundle,
        )
        for item in bundle.evidence
    }
    outcomes: list[ColdTargetTransitionOutcomeV1] = []
    for sequence, action in enumerate(actions, start=1):
        tile = int(action.action_key.split("=", 1)[1])
        exact_outcomes = kernel.step(
            ground_state,
            LMBAction(tile),
        )
        if len(exact_outcomes) != 1:
            raise CrossQueryPromotionInvariantViolation(
                "canonical cold target transition must be deterministic"
            )
        exact = exact_outcomes[0]
        successor = _state_observation(exact.next_state)
        source_evidence = evidence_by_row[action.ground_row_id]
        reward_features = tuple(exact.reward_features)
        if (
            source_evidence.state_id != target.initial_state.state_id
            or source_evidence.ground_action_id != action.action_id
            or source_evidence.successor_state.to_document()
            != successor.to_document()
            or source_evidence.reward_features != reward_features
            or source_evidence.failure is not exact.failure
            or source_evidence.terminal is not exact.terminal
        ):
            raise CrossQueryPromotionInvariantViolation(
                "cold target transition differs from promoted exact evidence"
            )
        outcomes.append(
            ColdTargetTransitionOutcomeV1(
                sequence,
                protocol.protocol_id,
                target.query_id,
                catalogue.catalogue_id,
                target.initial_state.state_id,
                action,
                successor,
                reward_features,
                exact.failure,
                exact.terminal,
                source_evidence.evidence_id,
            )
        )
    outcomes_tuple = tuple(outcomes)
    return ColdTargetAcquisitionTraceV1(
        promotion.result_id,
        protocol.protocol_id,
        target.query_id,
        promotion.model.model_id,
        catalogue,
        outcomes_tuple,
        tuple(sorted(item.matching_source_evidence_id for item in outcomes_tuple)),
    )


def run_lmb_cross_query_promotion_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    protocol: CrossQueryReuseProtocolV1,
    source_result: MultiStepQueryRefinementResultV1,
    kernel: LMBKernel,
) -> CrossQueryPromotionResultV1:
    """Run promotion, zero-ground held-out planning, and cold trace evaluation."""

    promotion = promote_lmb_multistep_overlay_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        source_thresholds,
        source_base_plan_proposal,
        source_failed_audit,
        protocol,
        source_result,
        kernel,
    )
    binding, proposal, audit = run_preregistered_heldout_query_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion,
    )
    cold = evaluate_cold_heldout_acquisition_v1(
        observation_log,
        promotion,
        source_result,
        kernel,
    )
    telemetry = CrossQueryReuseTelemetryV1(
        source_result.telemetry.cumulative_exact_kernel_queries,
        source_result.telemetry.boundary_action_catalogue_queries,
        promotion.eligibility_proof.independent_replay_transition_calls,
        promotion.eligibility_proof.independent_replay_direct_catalogue_calls,
        proposal.exact_kernel_calls_during_planning
        + audit.exact_kernel_calls_during_audit,
        0,
        cold.exact_transition_calls,
        cold.direct_catalogue_calls,
        cold.step_internal_legality_checks,
        1,
        proposal.fixed_plan_audit_count,
        promotion.promoted_observed_row_count,
        len(promotion.eligibility_proof.target_ground_row_ids),
    )
    return CrossQueryPromotionResultV1(
        source_result.result_id,
        promotion,
        binding,
        proposal,
        audit,
        cold,
        telemetry,
    )


def verify_lmb_cross_query_promotion_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    protocol: CrossQueryReuseProtocolV1,
    source_result: MultiStepQueryRefinementResultV1,
    kernel: LMBKernel,
    claimed_result: CrossQueryPromotionResultV1,
) -> CrossQueryPromotionResultV1:
    """Rebuild the full preregistration, source, promotion, target, and trace."""

    if type(claimed_result) is not CrossQueryPromotionResultV1:
        raise CrossQueryPromotionInvariantViolation(
            "cross-query verifier rejects substituted result artifacts"
        )
    expected = run_lmb_cross_query_promotion_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        source_thresholds,
        source_base_plan_proposal,
        source_failed_audit,
        protocol,
        source_result,
        kernel,
    )
    if claimed_result.to_document() != expected.to_document():
        raise CrossQueryPromotionInvariantViolation(
            "cross-query independent replay differs from the claimed result"
        )
    return expected


__all__ = [
    "ColdTargetAcquisitionTraceV1",
    "ColdTargetActionCatalogueV1",
    "ColdTargetTransitionOutcomeV1",
    "CrossQueryPromotionInvariantViolation",
    "CrossQueryPromotionResultV1",
    "CrossQueryReuseProtocolV1",
    "CrossQueryReuseTelemetryV1",
    "HeldOutPlanAuditV1",
    "HeldOutPlanProposalV1",
    "HeldOutQuerySpecV1",
    "HeldOutThresholdBindingV1",
    "PROFILE_KEY",
    "PromotedReusableModelBuildV1",
    "PromotionEligibilityProofV1",
    "SCHEMA_VERSION",
    "SUCCESS_STATUS",
    "TARGET_GROUND_STATE",
    "evaluate_cold_heldout_acquisition_v1",
    "preregister_lmb_cross_query_reuse_v1",
    "promote_lmb_multistep_overlay_v1",
    "run_lmb_cross_query_promotion_v1",
    "run_preregistered_heldout_query_v1",
    "verify_lmb_cross_query_promotion_v1",
]
