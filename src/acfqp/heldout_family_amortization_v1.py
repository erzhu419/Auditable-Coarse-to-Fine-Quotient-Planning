"""V0-049 preregistered held-out family reuse and vector amortization.

The complete V0-047 model is promoted once, through the verified V0-048
singleton promotion component, into a separate three-state V5 family scope.
Ten logical occurrences over three pre-source H1 queries are then executed in
a frozen order.  Every warm occurrence plans and certifies without a kernel;
every matched cold occurrence runs a complete exact H1 ground planner whose
API receives neither the promoted model nor the source result.

The resulting prefix curve is vector-valued.  Exact-kernel calls are not
relabeled as environment samples, no scalar break-even is frozen, and no
sample-tax operator or statistical-generalization claim is made.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import inspect
from itertools import product
from typing import Any, Mapping

from acfqp.cross_query_promotion_v1 import (
    CrossQueryReuseProtocolV1,
    HeldOutPlanAuditV1,
    HeldOutPlanProposalV1,
    HeldOutThresholdBindingV1,
    PromotedReusableModelBuildV1,
    preregister_lmb_cross_query_reuse_v1,
    promote_lmb_multistep_overlay_v1,
)
from acfqp.domains.matching_buffer import LMBAction, LMBKernel, LMBState, LMBStatus
from acfqp.multistep_query_refinement_v1 import (
    MultiStepQueryRefinementResultV1,
    _lmb_state,
    _selection_numeric_key,
    _semantic_plan_key,
    _state_observation,
    _validate_canonical_kernel,
    run_lmb_h2_multistep_query_refinement_v1,
)
from acfqp.observation_partial_rapm_v1 import (
    CanonicalGroundActionV1,
    CanonicalStateObservationV1,
    DeterministicObservationProfileV1,
    ObservationLogManifestV1,
    PlanningKind,
    PreregisteredObservationAuthorityV1,
    PreregisteredReusablePartialRAPMV5,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    ObservedTypedPartialRAPMResultV1,
)
from acfqp.partial_model_planner_v1 import (
    PartialModelPlannerSelectionMode,
    PartialPlannerCandidateSummaryV1,
    PartialPlannerCellActionDomainV1,
    TypedPartialModelPlanProposalResultV2,
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
    RewardWeightV1,
    TypedPartialSoundAuditResultV2,
    _audit_verified_partial_model_v1,
    canonical_lmb_n6_return_bound_proof_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.query_local_refinement_v1 import (
    canonical_lmb_query_kernel_authority_v1,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "lmb_preregistered_h1_heldout_family_amortization_v0"
SUCCESS_STATUS = "CERTIFIED_HELD_OUT_FAMILY_MATCHED_REUSE"
SOURCE_GROUND_STATE = LMBState(3, (1, 1), LMBStatus.ACTIVE)
FAMILY_TARGET_STATES = (
    LMBState(11, (1, 2), LMBStatus.ACTIVE),
    LMBState(19, (1, 2), LMBStatus.ACTIVE),
    LMBState(35, (2, 1), LMBStatus.ACTIVE),
)
OCCURRENCE_QUERY_INDICES = (1, 2, 3, 1, 2, 3, 1, 2, 3, 1)
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
    "query": "acfqp:held-out-family-query-spec:v1",
    "occurrence": "acfqp:held-out-family-logical-occurrence:v1",
    "protocol": "acfqp:held-out-family-reuse-protocol:v1",
    "target_coverage": "acfqp:held-out-family-target-coverage:v1",
    "eligibility": "acfqp:held-out-family-promotion-eligibility:v1",
    "promotion": "acfqp:held-out-family-promotion-build:v1",
    "cold_catalogue": "acfqp:held-out-family-cold-catalogue:v1",
    "cold_outcome": "acfqp:held-out-family-cold-outcome:v1",
    "cold_result": "acfqp:held-out-family-cold-direct-result:v1",
    "work": "acfqp:held-out-family-native-work-vector:v1",
    "matched": "acfqp:held-out-family-matched-occurrence:v1",
    "prefix": "acfqp:held-out-family-prefix-accounting:v1",
    "telemetry": "acfqp:held-out-family-amortization-telemetry:v1",
    "result": "acfqp:held-out-family-amortization-result:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-049 content-ID domains must be unique")


class HeldOutFamilyInvariantViolation(ValueError):
    """The family preregistration, matched run, or accounting is invalid."""


class ComponentwiseRelation(str, Enum):
    WARM_STRICT_COMPONENTWISE = "WARM_STRICT_COMPONENTWISE"
    COLD_STRICT_COMPONENTWISE = "COLD_STRICT_COMPONENTWISE"
    EQUAL = "EQUAL"
    INCOMPARABLE = "INCOMPARABLE"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise HeldOutFamilyInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise HeldOutFamilyInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise HeldOutFamilyInvariantViolation(
            f"{field} must be an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field: str) -> Fraction:
    try:
        result = Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError) as error:
        raise HeldOutFamilyInvariantViolation(f"{field} must be rational") from error
    return result


def _fraction_document(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _sorted_ids(
    values: tuple[str, ...], field: str, expected_count: int | None = None
) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or not values
        or any(type(item) is not str for item in values)
        or values != tuple(sorted(set(values)))
    ):
        raise HeldOutFamilyInvariantViolation(
            f"{field} must be a nonempty unique sorted tuple"
        )
    for value in values:
        _cid(value, field)
    if expected_count is not None and len(values) != expected_count:
        raise HeldOutFamilyInvariantViolation(
            f"{field} must contain exactly {expected_count} IDs"
        )
    return values


@dataclass(frozen=True, slots=True)
class FamilyHeldOutQuerySpecV1:
    query_index: int
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
    registration_phase: str = "BEFORE_SOURCE_REFINEMENT_ACQUISITION"
    query_role: str = "PREREGISTERED_HELD_OUT_FAMILY_TARGET"

    def __post_init__(self) -> None:
        _integer(self.query_index, "family query index", 1)
        for field in (
            "structural_id",
            "environment_instance_id",
            "observation_log_id",
            "semantics_profile_id",
            "base_model_id",
            "return_bound_proof_id",
        ):
            _cid(getattr(self, field), f"family query {field}")
        if type(self.initial_state) is not CanonicalStateObservationV1:
            raise HeldOutFamilyInvariantViolation(
                "family query rejects substituted state observations"
            )
        if (
            self.query_index > len(FAMILY_TARGET_STATES)
            or self.initial_state.to_document()
            != _state_observation(
                FAMILY_TARGET_STATES[self.query_index - 1]
            ).to_document()
            or self.reward_weights
            != (
                RewardWeightV1("match", Fraction(1)),
                RewardWeightV1("terminal_clear", Fraction(1)),
            )
        ):
            raise HeldOutFamilyInvariantViolation(
                "family query state or reward basis differs from the frozen workload"
            )
        object.__setattr__(
            self,
            "normalized_regret_tolerance",
            _fraction(self.normalized_regret_tolerance, "family regret tolerance"),
        )
        object.__setattr__(
            self,
            "risk_tolerance",
            _fraction(self.risk_tolerance, "family risk tolerance"),
        )
        if (
            self.horizon != 1
            or self.normalized_regret_tolerance != 0
            or self.risk_tolerance != 0
            or self.initial_state.planning_kind is not PlanningKind.ACTIVE
            or self.registration_phase
            != "BEFORE_SOURCE_REFINEMENT_ACQUISITION"
            or self.query_role != "PREREGISTERED_HELD_OUT_FAMILY_TARGET"
        ):
            raise HeldOutFamilyInvariantViolation(
                "family query parameters or registration phase changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_query_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "query_index": self.query_index,
            "structural_id": self.structural_id,
            "environment_instance_id": self.environment_instance_id,
            "observation_log_id": self.observation_log_id,
            "semantics_profile_id": self.semantics_profile_id,
            "base_model_id": self.base_model_id,
            "initial_state": self.initial_state.to_document(),
            "reward_weights": [item.to_document() for item in self.reward_weights],
            "return_bound_proof_id": self.return_bound_proof_id,
            "horizon": self.horizon,
            "normalized_regret_tolerance": _fraction_document(
                self.normalized_regret_tolerance
            ),
            "risk_tolerance": _fraction_document(self.risk_tolerance),
            "registration_phase": self.registration_phase,
            "query_role": self.query_role,
        }

    @property
    def query_id(self) -> str:
        return _content_id("query", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_id": self.query_id}


@dataclass(frozen=True, slots=True)
class FamilyLogicalOccurrenceV1:
    occurrence_index: int
    query_id: str
    repetition_index: int
    registration_phase: str = "BEFORE_SOURCE_REFINEMENT_ACQUISITION"

    def __post_init__(self) -> None:
        _integer(self.occurrence_index, "family occurrence index", 1)
        _integer(self.repetition_index, "family repetition index", 1)
        _cid(self.query_id, "family occurrence query")
        if self.registration_phase != "BEFORE_SOURCE_REFINEMENT_ACQUISITION":
            raise HeldOutFamilyInvariantViolation(
                "family occurrence was not preregistered before source acquisition"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_logical_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_index": self.occurrence_index,
            "query_id": self.query_id,
            "repetition_index": self.repetition_index,
            "registration_phase": self.registration_phase,
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("occurrence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


@dataclass(frozen=True, slots=True)
class HeldOutFamilyProtocolV1:
    singleton_protocol: CrossQueryReuseProtocolV1
    target_queries: tuple[FamilyHeldOutQuerySpecV1, ...]
    logical_occurrences: tuple[FamilyLogicalOccurrenceV1, ...]
    source_runner_parameter_names: tuple[str, ...]
    unique_target_count: int = 3
    logical_occurrence_count: int = 10
    repeated_occurrence_count: int = 7
    source_query_target_input_count: int = 0
    complete_source_final_model_promotion_required: bool = True
    target_filtered_row_selection_forbidden: bool = True
    occurrence_order_preregistered: bool = True
    matched_cold_direct_required: bool = True

    def __post_init__(self) -> None:
        if type(self.singleton_protocol) is not CrossQueryReuseProtocolV1:
            raise HeldOutFamilyInvariantViolation(
                "family protocol rejects substituted singleton protocols"
            )
        if (
            type(self.target_queries) is not tuple
            or len(self.target_queries) != 3
            or any(
                type(item) is not FamilyHeldOutQuerySpecV1
                for item in self.target_queries
            )
            or tuple(item.query_index for item in self.target_queries) != (1, 2, 3)
            or len({item.query_id for item in self.target_queries}) != 3
            or len({item.initial_state.state_id for item in self.target_queries}) != 3
        ):
            raise HeldOutFamilyInvariantViolation(
                "family protocol requires three ordered unique target queries"
            )
        if (
            self.target_queries[0].initial_state.state_id
            != self.singleton_protocol.target_query.initial_state.state_id
            or any(
                item.base_model_id != self.singleton_protocol.base_model_id
                for item in self.target_queries
            )
            or self.source_runner_parameter_names != SOURCE_RUNNER_PARAMETERS
        ):
            raise HeldOutFamilyInvariantViolation(
                "family protocol ancestry or source target-blind API changed"
            )
        if (
            type(self.logical_occurrences) is not tuple
            or len(self.logical_occurrences) != 10
            or any(
                type(item) is not FamilyLogicalOccurrenceV1
                for item in self.logical_occurrences
            )
        ):
            raise HeldOutFamilyInvariantViolation(
                "family protocol requires ten typed logical occurrences"
            )
        query_ids = {item.query_index: item.query_id for item in self.target_queries}
        repetitions = {1: 0, 2: 0, 3: 0}
        for occurrence, query_index in zip(
            self.logical_occurrences, OCCURRENCE_QUERY_INDICES
        ):
            repetitions[query_index] += 1
            if (
                occurrence.occurrence_index
                != self.logical_occurrences.index(occurrence) + 1
                or occurrence.query_id != query_ids[query_index]
                or occurrence.repetition_index != repetitions[query_index]
            ):
                raise HeldOutFamilyInvariantViolation(
                    "family occurrence order or repetition indices changed"
                )
        for field, expected in (
            ("unique_target_count", 3),
            ("logical_occurrence_count", 10),
            ("repeated_occurrence_count", 7),
            ("source_query_target_input_count", 0),
        ):
            _integer(getattr(self, field), f"family protocol {field}")
            if getattr(self, field) != expected:
                raise HeldOutFamilyInvariantViolation(
                    f"family protocol {field} changed"
                )
        if (
            self.complete_source_final_model_promotion_required is not True
            or self.target_filtered_row_selection_forbidden is not True
            or self.occurrence_order_preregistered is not True
            or self.matched_cold_direct_required is not True
        ):
            raise HeldOutFamilyInvariantViolation(
                "family promotion or matched-baseline requirement was weakened"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_reuse_protocol.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "singleton_protocol": self.singleton_protocol.to_document(),
            "target_queries": [item.to_document() for item in self.target_queries],
            "logical_occurrences": [
                item.to_document() for item in self.logical_occurrences
            ],
            "source_runner_parameter_names": list(
                self.source_runner_parameter_names
            ),
            "unique_target_count": self.unique_target_count,
            "logical_occurrence_count": self.logical_occurrence_count,
            "repeated_occurrence_count": self.repeated_occurrence_count,
            "source_query_target_input_count": self.source_query_target_input_count,
            "complete_source_final_model_promotion_required": (
                self.complete_source_final_model_promotion_required
            ),
            "target_filtered_row_selection_forbidden": (
                self.target_filtered_row_selection_forbidden
            ),
            "occurrence_order_preregistered": self.occurrence_order_preregistered,
            "matched_cold_direct_required": self.matched_cold_direct_required,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("protocol", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


@dataclass(frozen=True, slots=True)
class FamilyTargetCoverageV1:
    query_id: str
    state_id: str
    ground_row_ids: tuple[str, ...]
    source_evidence_ids: tuple[str, ...]
    source_catalogue_id: str

    def __post_init__(self) -> None:
        _cid(self.query_id, "family target coverage query")
        _cid(self.state_id, "family target coverage state")
        _cid(self.source_catalogue_id, "family target coverage catalogue")
        _sorted_ids(self.ground_row_ids, "family target ground rows", 3)
        _sorted_ids(self.source_evidence_ids, "family target evidence", 3)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_target_coverage.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "query_id": self.query_id,
            "state_id": self.state_id,
            "ground_row_ids": list(self.ground_row_ids),
            "source_evidence_ids": list(self.source_evidence_ids),
            "source_catalogue_id": self.source_catalogue_id,
        }

    @property
    def coverage_id(self) -> str:
        return _content_id("target_coverage", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "coverage_id": self.coverage_id}


@dataclass(frozen=True, slots=True)
class FamilyPromotionEligibilityV1:
    family_protocol_id: str
    parent_promotion_result_id: str
    parent_promoted_model_id: str
    source_refinement_result_id: str
    source_final_model_id: str
    complete_promoted_ground_row_ids: tuple[str, ...]
    source_exact_evidence_ids: tuple[str, ...]
    source_boundary_catalogue_ids: tuple[str, ...]
    target_coverages: tuple[FamilyTargetCoverageV1, ...]
    target_filtered_row_count: int = 0
    complete_promoted_row_count: int = 20
    source_exact_evidence_count: int = 13
    target_ground_row_count: int = 9

    def __post_init__(self) -> None:
        for field in (
            "family_protocol_id",
            "parent_promotion_result_id",
            "parent_promoted_model_id",
            "source_refinement_result_id",
            "source_final_model_id",
        ):
            _cid(getattr(self, field), f"family eligibility {field}")
        _sorted_ids(
            self.complete_promoted_ground_row_ids,
            "family complete promoted rows",
            20,
        )
        _sorted_ids(
            self.source_exact_evidence_ids,
            "family source exact evidence",
            13,
        )
        _sorted_ids(
            self.source_boundary_catalogue_ids,
            "family source boundary catalogues",
            3,
        )
        if (
            type(self.target_coverages) is not tuple
            or len(self.target_coverages) != 3
            or any(type(item) is not FamilyTargetCoverageV1 for item in self.target_coverages)
            or len({item.query_id for item in self.target_coverages}) != 3
            or len({item.state_id for item in self.target_coverages}) != 3
            or set(
                row_id
                for item in self.target_coverages
                for row_id in item.ground_row_ids
            )
            - set(self.complete_promoted_ground_row_ids)
        ):
            raise HeldOutFamilyInvariantViolation(
                "family target coverage is incomplete or outside the promoted model"
            )
        for field, expected in (
            ("target_filtered_row_count", 0),
            ("complete_promoted_row_count", 20),
            ("source_exact_evidence_count", 13),
            ("target_ground_row_count", 9),
        ):
            _integer(getattr(self, field), f"family eligibility {field}")
            if getattr(self, field) != expected:
                raise HeldOutFamilyInvariantViolation(
                    f"family eligibility {field} changed"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_promotion_eligibility.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "family_protocol_id": self.family_protocol_id,
            "parent_promotion_result_id": self.parent_promotion_result_id,
            "parent_promoted_model_id": self.parent_promoted_model_id,
            "source_refinement_result_id": self.source_refinement_result_id,
            "source_final_model_id": self.source_final_model_id,
            "complete_promoted_ground_row_ids": list(
                self.complete_promoted_ground_row_ids
            ),
            "source_exact_evidence_ids": list(self.source_exact_evidence_ids),
            "source_boundary_catalogue_ids": list(
                self.source_boundary_catalogue_ids
            ),
            "target_coverages": [item.to_document() for item in self.target_coverages],
            "target_filtered_row_count": self.target_filtered_row_count,
            "complete_promoted_row_count": self.complete_promoted_row_count,
            "source_exact_evidence_count": self.source_exact_evidence_count,
            "target_ground_row_count": self.target_ground_row_count,
        }

    @property
    def proof_id(self) -> str:
        return _content_id("eligibility", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


@dataclass(frozen=True, slots=True)
class HeldOutFamilyPromotionBuildV1:
    protocol: HeldOutFamilyProtocolV1
    parent_promotion: PromotedReusableModelBuildV1
    eligibility_proof: FamilyPromotionEligibilityV1
    model: PreregisteredReusablePartialRAPMV5
    source_refinement_result_id: str
    complete_model_promoted: bool = True
    target_filtered_promotion: bool = False
    base_model_mutated: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.protocol) is not HeldOutFamilyProtocolV1
            or type(self.parent_promotion) is not PromotedReusableModelBuildV1
            or type(self.eligibility_proof) is not FamilyPromotionEligibilityV1
            or type(self.model) is not PreregisteredReusablePartialRAPMV5
        ):
            raise HeldOutFamilyInvariantViolation(
                "family promotion rejects substituted artifacts"
            )
        _cid(self.source_refinement_result_id, "family promotion source result")
        if (
            self.parent_promotion.protocol.protocol_id
            != self.protocol.singleton_protocol.protocol_id
            or self.eligibility_proof.family_protocol_id != self.protocol.protocol_id
            or self.eligibility_proof.parent_promotion_result_id
            != self.parent_promotion.result_id
            or self.model.parent_scoped_model.to_document()
            != self.parent_promotion.model.to_document()
            or self.model.family_protocol_id != self.protocol.protocol_id
            or self.model.family_eligibility_proof_id
            != self.eligibility_proof.proof_id
            or self.source_refinement_result_id
            != self.eligibility_proof.source_refinement_result_id
            or self.complete_model_promoted is not True
            or self.target_filtered_promotion is not False
            or self.base_model_mutated is not False
        ):
            raise HeldOutFamilyInvariantViolation(
                "family promotion identity or immutability chain changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_promotion_build.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol": self.protocol.to_document(),
            "parent_promotion": self.parent_promotion.to_document(),
            "eligibility_proof": self.eligibility_proof.to_document(),
            "model": self.model.to_document(),
            "source_refinement_result_id": self.source_refinement_result_id,
            "complete_model_promoted": self.complete_model_promoted,
            "target_filtered_promotion": self.target_filtered_promotion,
            "base_model_mutated": self.base_model_mutated,
        }

    @property
    def result_id(self) -> str:
        return _content_id("promotion", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class ColdDirectActionCatalogueV1:
    occurrence_id: str
    query_id: str
    state: CanonicalStateObservationV1
    actions: tuple[CanonicalGroundActionV1, ...]

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "cold catalogue occurrence")
        _cid(self.query_id, "cold catalogue query")
        if (
            type(self.state) is not CanonicalStateObservationV1
            or type(self.actions) is not tuple
            or len(self.actions) != 3
            or any(type(item) is not CanonicalGroundActionV1 for item in self.actions)
            or tuple(item.action_id for item in self.actions)
            != tuple(sorted(set(item.action_id for item in self.actions)))
            or any(item.state_id != self.state.state_id for item in self.actions)
        ):
            raise HeldOutFamilyInvariantViolation(
                "cold direct catalogue is incomplete, duplicate, or substituted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_cold_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "query_id": self.query_id,
            "state": self.state.to_document(),
            "actions": [item.to_document() for item in self.actions],
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("cold_catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_id": self.catalogue_id}


@dataclass(frozen=True, slots=True)
class ColdDirectOutcomeV1:
    sequence: int
    catalogue_id: str
    action: CanonicalGroundActionV1
    successor_state: CanonicalStateObservationV1
    reward_features: tuple[tuple[str, Fraction], ...]
    weighted_reward: Fraction
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        _integer(self.sequence, "cold outcome sequence", 1)
        _cid(self.catalogue_id, "cold outcome catalogue")
        if (
            type(self.action) is not CanonicalGroundActionV1
            or type(self.successor_state) is not CanonicalStateObservationV1
            or type(self.reward_features) is not tuple
            or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or type(item[1]) is not Fraction
                for item in self.reward_features
            )
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
        ):
            raise HeldOutFamilyInvariantViolation(
                "cold direct outcome is substituted or noncanonical"
            )
        object.__setattr__(
            self,
            "weighted_reward",
            _fraction(self.weighted_reward, "cold weighted reward"),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_cold_outcome.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence": self.sequence,
            "catalogue_id": self.catalogue_id,
            "action": self.action.to_document(),
            "successor_state": self.successor_state.to_document(),
            "reward_features": [
                {"name": name, "value": _fraction_document(value)}
                for name, value in self.reward_features
            ],
            "weighted_reward": _fraction_document(self.weighted_reward),
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def outcome_id(self) -> str:
        return _content_id("cold_outcome", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_id": self.outcome_id}


@dataclass(frozen=True, slots=True)
class ColdDirectPlanResultV1:
    occurrence: FamilyLogicalOccurrenceV1
    query: FamilyHeldOutQuerySpecV1
    catalogue: ColdDirectActionCatalogueV1
    outcomes: tuple[ColdDirectOutcomeV1, ...]
    selected_action_id: str
    optimal_reward: Fraction
    failure_probability: Fraction
    normalized_regret: Fraction
    exact_transition_calls: int = 3
    direct_catalogue_calls: int = 1
    step_internal_legality_checks: int = 3
    ground_action_candidates: int = 3
    direct_ground_optimizer_calls: int = 1
    promotion_input_count: int = 0
    source_result_input_count: int = 0
    complete_action_coverage: bool = True
    exact_h1_ground_certificate: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.occurrence) is not FamilyLogicalOccurrenceV1
            or type(self.query) is not FamilyHeldOutQuerySpecV1
            or type(self.catalogue) is not ColdDirectActionCatalogueV1
            or type(self.outcomes) is not tuple
            or len(self.outcomes) != 3
            or any(type(item) is not ColdDirectOutcomeV1 for item in self.outcomes)
        ):
            raise HeldOutFamilyInvariantViolation(
                "cold direct result rejects substituted artifacts"
            )
        _cid(self.selected_action_id, "cold selected action")
        for field in ("optimal_reward", "failure_probability", "normalized_regret"):
            object.__setattr__(self, field, _fraction(getattr(self, field), field))
        selected = tuple(
            item for item in self.outcomes if item.action.action_id == self.selected_action_id
        )
        feasible = tuple(item for item in self.outcomes if not item.failure)
        if (
            self.occurrence.query_id != self.query.query_id
            or self.catalogue.occurrence_id != self.occurrence.occurrence_id
            or self.catalogue.query_id != self.query.query_id
            or self.catalogue.state.state_id != self.query.initial_state.state_id
            or tuple(item.sequence for item in self.outcomes) != (1, 2, 3)
            or tuple(item.catalogue_id for item in self.outcomes)
            != (self.catalogue.catalogue_id,) * 3
            or tuple(item.action.action_id for item in self.outcomes)
            != tuple(item.action_id for item in self.catalogue.actions)
            or any(
                item.weighted_reward
                != sum((value for _, value in item.reward_features), Fraction(0))
                for item in self.outcomes
            )
            or len(selected) != 1
            or len(feasible) != 1
            or selected[0] is not feasible[0]
            or self.optimal_reward != 1
            or selected[0].weighted_reward != self.optimal_reward
            or self.failure_probability != 0
            or self.normalized_regret != 0
        ):
            raise HeldOutFamilyInvariantViolation(
                "cold direct planner did not prove the exact H1 1/0/0 optimum"
            )
        for field, expected in (
            ("exact_transition_calls", 3),
            ("direct_catalogue_calls", 1),
            ("step_internal_legality_checks", 3),
            ("ground_action_candidates", 3),
            ("direct_ground_optimizer_calls", 1),
            ("promotion_input_count", 0),
            ("source_result_input_count", 0),
        ):
            _integer(getattr(self, field), f"cold direct {field}")
            if getattr(self, field) != expected:
                raise HeldOutFamilyInvariantViolation(
                    f"cold direct {field} changed"
                )
        if (
            self.complete_action_coverage is not True
            or self.exact_h1_ground_certificate is not True
        ):
            raise HeldOutFamilyInvariantViolation(
                "cold direct planner lost complete exact certification"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_cold_direct_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence": self.occurrence.to_document(),
            "query": self.query.to_document(),
            "catalogue": self.catalogue.to_document(),
            "outcomes": [item.to_document() for item in self.outcomes],
            "selected_action_id": self.selected_action_id,
            "optimal_reward": _fraction_document(self.optimal_reward),
            "failure_probability": _fraction_document(self.failure_probability),
            "normalized_regret": _fraction_document(self.normalized_regret),
            "exact_transition_calls": self.exact_transition_calls,
            "direct_catalogue_calls": self.direct_catalogue_calls,
            "step_internal_legality_checks": self.step_internal_legality_checks,
            "ground_action_candidates": self.ground_action_candidates,
            "direct_ground_optimizer_calls": self.direct_ground_optimizer_calls,
            "promotion_input_count": self.promotion_input_count,
            "source_result_input_count": self.source_result_input_count,
            "complete_action_coverage": self.complete_action_coverage,
            "exact_h1_ground_certificate": self.exact_h1_ground_certificate,
        }

    @property
    def result_id(self) -> str:
        return _content_id("cold_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class FamilyNativeWorkVectorV1:
    lane: str
    occurrence_id: str | None
    exact_transition_calls: int
    direct_catalogue_calls: int
    step_internal_legality_checks: int
    model_plan_candidates: int
    model_fixed_plan_audits: int
    ground_action_candidates: int
    direct_ground_optimizer_calls: int

    def __post_init__(self) -> None:
        if self.lane not in {
            "SOURCE_ACQUISITION_OPERATIONAL",
            "PROMOTION_REPLAY_EVALUATION",
            "WARM_TARGET_OPERATIONAL",
            "COLD_DIRECT_OPERATIONAL",
        }:
            raise HeldOutFamilyInvariantViolation("unknown family work lane")
        if self.occurrence_id is not None:
            _cid(self.occurrence_id, "family work occurrence")
        for field in (
            "exact_transition_calls",
            "direct_catalogue_calls",
            "step_internal_legality_checks",
            "model_plan_candidates",
            "model_fixed_plan_audits",
            "ground_action_candidates",
            "direct_ground_optimizer_calls",
        ):
            _integer(getattr(self, field), f"family work {field}")
        if (
            self.lane in {
                "SOURCE_ACQUISITION_OPERATIONAL",
                "PROMOTION_REPLAY_EVALUATION",
            }
            and self.occurrence_id is not None
        ) or (
            self.lane in {"WARM_TARGET_OPERATIONAL", "COLD_DIRECT_OPERATIONAL"}
            and self.occurrence_id is None
        ):
            raise HeldOutFamilyInvariantViolation(
                "family work lane has the wrong occurrence scope"
            )
        expected_by_lane = {
            "SOURCE_ACQUISITION_OPERATIONAL": (13, 3, 13, 0, 0, 0, 0),
            "PROMOTION_REPLAY_EVALUATION": (13, 3, 13, 0, 0, 0, 0),
            "WARM_TARGET_OPERATIONAL": (0, 0, 0, 2, 3, 0, 0),
            "COLD_DIRECT_OPERATIONAL": (3, 1, 3, 0, 0, 3, 1),
        }
        actual = (
            self.exact_transition_calls,
            self.direct_catalogue_calls,
            self.step_internal_legality_checks,
            self.model_plan_candidates,
            self.model_fixed_plan_audits,
            self.ground_action_candidates,
            self.direct_ground_optimizer_calls,
        )
        if actual != expected_by_lane[self.lane]:
            raise HeldOutFamilyInvariantViolation(
                "family work vector violates its native lane accounting"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_native_work_vector.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "lane": self.lane,
            "occurrence_id": self.occurrence_id,
            "exact_transition_calls": self.exact_transition_calls,
            "direct_catalogue_calls": self.direct_catalogue_calls,
            "step_internal_legality_checks": self.step_internal_legality_checks,
            "model_plan_candidates": self.model_plan_candidates,
            "model_fixed_plan_audits": self.model_fixed_plan_audits,
            "ground_action_candidates": self.ground_action_candidates,
            "direct_ground_optimizer_calls": self.direct_ground_optimizer_calls,
        }

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class MatchedHeldOutOccurrenceV1:
    occurrence: FamilyLogicalOccurrenceV1
    query: FamilyHeldOutQuerySpecV1
    threshold_binding: HeldOutThresholdBindingV1
    warm_plan: HeldOutPlanProposalV1
    warm_audit: HeldOutPlanAuditV1
    cold_direct: ColdDirectPlanResultV1
    matching_source_catalogue_id: str
    matching_source_evidence_ids: tuple[str, ...]
    warm_work: FamilyNativeWorkVectorV1
    cold_work: FamilyNativeWorkVectorV1
    exact_reward_match: bool = True
    exact_failure_match: bool = True
    exact_regret_match: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.occurrence) is not FamilyLogicalOccurrenceV1
            or type(self.query) is not FamilyHeldOutQuerySpecV1
            or type(self.threshold_binding) is not HeldOutThresholdBindingV1
            or type(self.warm_plan) is not HeldOutPlanProposalV1
            or type(self.warm_audit) is not HeldOutPlanAuditV1
            or type(self.cold_direct) is not ColdDirectPlanResultV1
            or type(self.warm_work) is not FamilyNativeWorkVectorV1
            or type(self.cold_work) is not FamilyNativeWorkVectorV1
        ):
            raise HeldOutFamilyInvariantViolation(
                "matched occurrence rejects substituted artifacts"
            )
        _cid(self.matching_source_catalogue_id, "matched source catalogue")
        _sorted_ids(
            self.matching_source_evidence_ids,
            "matched source evidence",
            3,
        )
        bounds = self.warm_audit.audit_result.robust_bounds
        if (
            self.occurrence.query_id != self.query.query_id
            or self.cold_direct.occurrence.occurrence_id
            != self.occurrence.occurrence_id
            or self.threshold_binding.target_query_id != self.query.query_id
            or self.warm_plan.target_query_id != self.query.query_id
            or self.warm_audit.target_query_id != self.query.query_id
            or self.warm_work.occurrence_id != self.occurrence.occurrence_id
            or self.cold_work.occurrence_id != self.occurrence.occurrence_id
            or self.warm_work.lane != "WARM_TARGET_OPERATIONAL"
            or self.cold_work.lane != "COLD_DIRECT_OPERATIONAL"
            or bounds.policy_reward_lower != self.cold_direct.optimal_reward
            or bounds.policy_failure_upper
            != self.cold_direct.failure_probability
            or bounds.normalized_distribution_regret
            != self.cold_direct.normalized_regret
            or self.exact_reward_match is not True
            or self.exact_failure_match is not True
            or self.exact_regret_match is not True
        ):
            raise HeldOutFamilyInvariantViolation(
                "warm and cold occurrence certificates do not match exactly"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_matched_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence": self.occurrence.to_document(),
            "query": self.query.to_document(),
            "threshold_binding": self.threshold_binding.to_document(),
            "warm_plan": self.warm_plan.to_document(),
            "warm_audit": self.warm_audit.to_document(),
            "cold_direct": self.cold_direct.to_document(),
            "matching_source_catalogue_id": self.matching_source_catalogue_id,
            "matching_source_evidence_ids": list(self.matching_source_evidence_ids),
            "warm_work": self.warm_work.to_document(),
            "cold_work": self.cold_work.to_document(),
            "exact_reward_match": self.exact_reward_match,
            "exact_failure_match": self.exact_failure_match,
            "exact_regret_match": self.exact_regret_match,
        }

    @property
    def result_id(self) -> str:
        return _content_id("matched", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _relation(
    warm_transition: int,
    warm_catalogue: int,
    cold_transition: int,
    cold_catalogue: int,
) -> ComponentwiseRelation:
    warm_le = warm_transition <= cold_transition and warm_catalogue <= cold_catalogue
    cold_le = cold_transition <= warm_transition and cold_catalogue <= warm_catalogue
    if warm_le and cold_le:
        return ComponentwiseRelation.EQUAL
    if warm_le:
        return ComponentwiseRelation.WARM_STRICT_COMPONENTWISE
    if cold_le:
        return ComponentwiseRelation.COLD_STRICT_COMPONENTWISE
    return ComponentwiseRelation.INCOMPARABLE


@dataclass(frozen=True, slots=True)
class FamilyPrefixAccountingV1:
    prefix_length: int
    occurrence_ids: tuple[str, ...]
    source_inclusive_warm_transition_calls: int
    source_inclusive_warm_catalogue_calls: int
    verification_inclusive_warm_transition_calls: int
    verification_inclusive_warm_catalogue_calls: int
    cold_transition_calls: int
    cold_catalogue_calls: int
    warm_model_plan_candidates: int
    warm_model_fixed_plan_audits: int
    cold_ground_action_candidates: int
    cold_direct_ground_optimizer_calls: int
    source_inclusive_relation: ComponentwiseRelation
    verification_inclusive_relation: ComponentwiseRelation
    official_scalar_cost: None = None
    official_N_break_even: None = None
    scalar_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        _integer(self.prefix_length, "family prefix length", 1)
        if (
            type(self.occurrence_ids) is not tuple
            or len(self.occurrence_ids) != self.prefix_length
            or len(set(self.occurrence_ids)) != self.prefix_length
        ):
            raise HeldOutFamilyInvariantViolation(
                "family prefix occurrence chain is incomplete or duplicate"
            )
        for occurrence_id in self.occurrence_ids:
            _cid(occurrence_id, "family prefix occurrence")
        for field in (
            "source_inclusive_warm_transition_calls",
            "source_inclusive_warm_catalogue_calls",
            "verification_inclusive_warm_transition_calls",
            "verification_inclusive_warm_catalogue_calls",
            "cold_transition_calls",
            "cold_catalogue_calls",
            "warm_model_plan_candidates",
            "warm_model_fixed_plan_audits",
            "cold_ground_action_candidates",
            "cold_direct_ground_optimizer_calls",
        ):
            _integer(getattr(self, field), f"family prefix {field}")
        if (
            type(self.source_inclusive_relation) is not ComponentwiseRelation
            or type(self.verification_inclusive_relation) is not ComponentwiseRelation
            or self.source_inclusive_relation
            is not _relation(
                self.source_inclusive_warm_transition_calls,
                self.source_inclusive_warm_catalogue_calls,
                self.cold_transition_calls,
                self.cold_catalogue_calls,
            )
            or self.verification_inclusive_relation
            is not _relation(
                self.verification_inclusive_warm_transition_calls,
                self.verification_inclusive_warm_catalogue_calls,
                self.cold_transition_calls,
                self.cold_catalogue_calls,
            )
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.scalar_gate_status != "NOT_RUN"
        ):
            raise HeldOutFamilyInvariantViolation(
                "family prefix relation or scalar lock changed"
            )
        expected = (
            13,
            3,
            26,
            6,
            3 * self.prefix_length,
            self.prefix_length,
            2 * self.prefix_length,
            3 * self.prefix_length,
            3 * self.prefix_length,
            self.prefix_length,
        )
        actual = tuple(
            getattr(self, field)
            for field in (
                "source_inclusive_warm_transition_calls",
                "source_inclusive_warm_catalogue_calls",
                "verification_inclusive_warm_transition_calls",
                "verification_inclusive_warm_catalogue_calls",
                "cold_transition_calls",
                "cold_catalogue_calls",
                "warm_model_plan_candidates",
                "warm_model_fixed_plan_audits",
                "cold_ground_action_candidates",
                "cold_direct_ground_optimizer_calls",
            )
        )
        if actual != expected:
            raise HeldOutFamilyInvariantViolation(
                "family prefix does not equal exact cumulative native work"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_prefix_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "prefix_length": self.prefix_length,
            "occurrence_ids": list(self.occurrence_ids),
            "source_inclusive_warm_transition_calls": self.source_inclusive_warm_transition_calls,
            "source_inclusive_warm_catalogue_calls": self.source_inclusive_warm_catalogue_calls,
            "verification_inclusive_warm_transition_calls": self.verification_inclusive_warm_transition_calls,
            "verification_inclusive_warm_catalogue_calls": self.verification_inclusive_warm_catalogue_calls,
            "cold_transition_calls": self.cold_transition_calls,
            "cold_catalogue_calls": self.cold_catalogue_calls,
            "warm_model_plan_candidates": self.warm_model_plan_candidates,
            "warm_model_fixed_plan_audits": self.warm_model_fixed_plan_audits,
            "cold_ground_action_candidates": self.cold_ground_action_candidates,
            "cold_direct_ground_optimizer_calls": self.cold_direct_ground_optimizer_calls,
            "source_inclusive_relation": self.source_inclusive_relation.value,
            "verification_inclusive_relation": self.verification_inclusive_relation.value,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "scalar_gate_status": self.scalar_gate_status,
        }

    @property
    def prefix_id(self) -> str:
        return _content_id("prefix", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prefix_id": self.prefix_id}


@dataclass(frozen=True, slots=True)
class HeldOutFamilyTelemetryV1:
    unique_query_count: int
    logical_occurrence_count: int
    repeated_occurrence_count: int
    source_transition_calls: int
    source_catalogue_calls: int
    promotion_replay_transition_calls: int
    promotion_replay_catalogue_calls: int
    warm_target_transition_calls: int
    warm_target_catalogue_calls: int
    cold_target_transition_calls: int
    cold_target_catalogue_calls: int
    warm_model_plan_candidates: int
    warm_model_fixed_plan_audits: int
    cold_ground_action_candidates: int
    cold_direct_ground_optimizer_calls: int
    first_source_inclusive_warm_dominance_prefix: int
    first_verification_inclusive_warm_dominance_prefix: int
    source_cost_amortization_included: bool = True
    cold_end_to_end_planner_claimed: bool = True
    matched_certificate_count: int = 10
    exact_kernel_calls_are_samples: bool = False
    sample_efficiency_claimed: bool = False
    statistical_generalization_claimed: bool = False
    tax_operator_selected: bool = False
    dominant_tax_axis: None = None
    official_scalar_cost: None = None
    official_N_break_even: None = None
    sample_efficiency_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        expected = {
            "unique_query_count": 3,
            "logical_occurrence_count": 10,
            "repeated_occurrence_count": 7,
            "source_transition_calls": 13,
            "source_catalogue_calls": 3,
            "promotion_replay_transition_calls": 13,
            "promotion_replay_catalogue_calls": 3,
            "warm_target_transition_calls": 0,
            "warm_target_catalogue_calls": 0,
            "cold_target_transition_calls": 30,
            "cold_target_catalogue_calls": 10,
            "warm_model_plan_candidates": 20,
            "warm_model_fixed_plan_audits": 30,
            "cold_ground_action_candidates": 30,
            "cold_direct_ground_optimizer_calls": 10,
            "first_source_inclusive_warm_dominance_prefix": 5,
            "first_verification_inclusive_warm_dominance_prefix": 9,
            "matched_certificate_count": 10,
        }
        for field, value in expected.items():
            _integer(getattr(self, field), f"family telemetry {field}")
            if getattr(self, field) != value:
                raise HeldOutFamilyInvariantViolation(
                    f"family telemetry {field} changed"
                )
        if (
            self.source_cost_amortization_included is not True
            or self.cold_end_to_end_planner_claimed is not True
            or self.exact_kernel_calls_are_samples is not False
            or self.sample_efficiency_claimed is not False
            or self.statistical_generalization_claimed is not False
            or self.tax_operator_selected is not False
            or self.dominant_tax_axis is not None
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            raise HeldOutFamilyInvariantViolation(
                "family telemetry crossed its evidence or Gate boundary"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_amortization_telemetry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field: getattr(self, field)
                for field in self.__dataclass_fields__
            },
        }

    @property
    def telemetry_id(self) -> str:
        return _content_id("telemetry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "telemetry_id": self.telemetry_id}


@dataclass(frozen=True, slots=True)
class HeldOutFamilyAmortizationResultV1:
    source_refinement_result_id: str
    promotion_build: HeldOutFamilyPromotionBuildV1
    source_work: FamilyNativeWorkVectorV1
    promotion_replay_work: FamilyNativeWorkVectorV1
    matched_occurrences: tuple[MatchedHeldOutOccurrenceV1, ...]
    prefixes: tuple[FamilyPrefixAccountingV1, ...]
    telemetry: HeldOutFamilyTelemetryV1
    status: str = SUCCESS_STATUS
    unrestricted_reuse_claimed: bool = False
    statistical_generalization_claimed: bool = False
    sample_efficiency_claimed: bool = False
    sample_tax_operator_claimed: bool = False

    def __post_init__(self) -> None:
        _cid(self.source_refinement_result_id, "family result source")
        if (
            type(self.promotion_build) is not HeldOutFamilyPromotionBuildV1
            or type(self.source_work) is not FamilyNativeWorkVectorV1
            or type(self.promotion_replay_work) is not FamilyNativeWorkVectorV1
            or type(self.telemetry) is not HeldOutFamilyTelemetryV1
            or type(self.matched_occurrences) is not tuple
            or len(self.matched_occurrences) != 10
            or any(
                type(item) is not MatchedHeldOutOccurrenceV1
                for item in self.matched_occurrences
            )
            or type(self.prefixes) is not tuple
            or len(self.prefixes) != 10
            or any(type(item) is not FamilyPrefixAccountingV1 for item in self.prefixes)
        ):
            raise HeldOutFamilyInvariantViolation(
                "family result rejects substituted or incomplete artifacts"
            )
        if (
            self.source_refinement_result_id
            != self.promotion_build.source_refinement_result_id
            or self.source_work.lane != "SOURCE_ACQUISITION_OPERATIONAL"
            or self.promotion_replay_work.lane != "PROMOTION_REPLAY_EVALUATION"
            or tuple(
                item.occurrence.occurrence_id for item in self.matched_occurrences
            )
            != tuple(
                item.occurrence_id
                for item in self.promotion_build.protocol.logical_occurrences
            )
            or tuple(item.prefix_length for item in self.prefixes)
            != tuple(range(1, 11))
            or self.status != SUCCESS_STATUS
            or self.unrestricted_reuse_claimed is not False
            or self.statistical_generalization_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.sample_tax_operator_claimed is not False
        ):
            raise HeldOutFamilyInvariantViolation(
                "family result ordering, status, or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.held_out_family_amortization_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_refinement_result_id": self.source_refinement_result_id,
            "promotion_build": self.promotion_build.to_document(),
            "source_work": self.source_work.to_document(),
            "promotion_replay_work": self.promotion_replay_work.to_document(),
            "matched_occurrences": [
                item.to_document() for item in self.matched_occurrences
            ],
            "prefixes": [item.to_document() for item in self.prefixes],
            "telemetry": self.telemetry.to_document(),
            "status": self.status,
            "unrestricted_reuse_claimed": self.unrestricted_reuse_claimed,
            "statistical_generalization_claimed": self.statistical_generalization_claimed,
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "sample_tax_operator_claimed": self.sample_tax_operator_claimed,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def preregister_lmb_heldout_family_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
) -> HeldOutFamilyProtocolV1:
    """Freeze all queries and occurrence order without a source result or kernel."""

    singleton = preregister_lmb_cross_query_reuse_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        source_thresholds,
    )
    if tuple(inspect.signature(run_lmb_h2_multistep_query_refinement_v1).parameters) != SOURCE_RUNNER_PARAMETERS:
        raise HeldOutFamilyInvariantViolation("source runner API changed")
    proof = canonical_lmb_n6_return_bound_proof_v1()
    queries = tuple(
        FamilyHeldOutQuerySpecV1(
            index,
            observation_log.structural_id,
            observation_log.environment_instance_id,
            observation_log.log_id,
            semantics_profile.profile_id,
            observed_synthesis_result.partial_build_result.model.model_id,
            _state_observation(state),
            source_thresholds.reward_weights,
            proof.proof_id,
        )
        for index, state in enumerate(FAMILY_TARGET_STATES, start=1)
    )
    base_state_ids = {item.state_id for item in observation_log.states}
    if (
        any(item.initial_state.state_id in base_state_ids for item in queries)
        or any(
            item.initial_state.state_id == singleton.source_initial_state_id
            for item in queries
        )
    ):
        raise HeldOutFamilyInvariantViolation(
            "family target is not held out from the base/source initial state"
        )
    repetitions = {1: 0, 2: 0, 3: 0}
    occurrences: list[FamilyLogicalOccurrenceV1] = []
    for occurrence_index, query_index in enumerate(
        OCCURRENCE_QUERY_INDICES, start=1
    ):
        repetitions[query_index] += 1
        occurrences.append(
            FamilyLogicalOccurrenceV1(
                occurrence_index,
                queries[query_index - 1].query_id,
                repetitions[query_index],
            )
        )
    return HeldOutFamilyProtocolV1(
        singleton,
        queries,
        tuple(occurrences),
        SOURCE_RUNNER_PARAMETERS,
    )


def promote_lmb_heldout_family_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    protocol: HeldOutFamilyProtocolV1,
    source_result: MultiStepQueryRefinementResultV1,
    kernel: LMBKernel,
) -> HeldOutFamilyPromotionBuildV1:
    """Replay the complete source once and create the immutable V5 family epoch."""

    if type(protocol) is not HeldOutFamilyProtocolV1:
        raise HeldOutFamilyInvariantViolation(
            "family promotion rejects substituted protocols"
        )
    expected_protocol = preregister_lmb_heldout_family_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        source_thresholds,
    )
    if protocol.to_document() != expected_protocol.to_document():
        raise HeldOutFamilyInvariantViolation(
            "family protocol differs from pre-source reconstruction"
        )
    parent = promote_lmb_multistep_overlay_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        source_thresholds,
        source_base_plan_proposal,
        source_failed_audit,
        protocol.singleton_protocol,
        source_result,
        kernel,
    )
    model = parent.model
    evidence_by_row = {
        item.ground_row_id: item.evidence_id
        for bundle in (source_result.round_one_bundle, source_result.round_two_bundle)
        for item in bundle.evidence
    }
    catalogues_by_state = {
        item.state.state_id: item
        for item in source_result.boundary_expansion.catalogues
    }
    coverages: list[FamilyTargetCoverageV1] = []
    for query in protocol.target_queries:
        rows = tuple(
            sorted(
                item.ground_row_id
                for item in model.ground_rows
                if item.state_id == query.initial_state.state_id
            )
        )
        catalogue = catalogues_by_state.get(query.initial_state.state_id)
        if (
            catalogue is None
            or len(rows) != 3
            or set(rows) != {item.ground_row_id for item in catalogue.actions}
            or any(row_id not in evidence_by_row for row_id in rows)
        ):
            raise HeldOutFamilyInvariantViolation(
                "source final model lacks complete exact family target coverage"
            )
        coverages.append(
            FamilyTargetCoverageV1(
                query.query_id,
                query.initial_state.state_id,
                rows,
                tuple(sorted(evidence_by_row[row_id] for row_id in rows)),
                catalogue.catalogue_id,
            )
        )
    proof = FamilyPromotionEligibilityV1(
        protocol.protocol_id,
        parent.result_id,
        parent.model.model_id,
        source_result.result_id,
        source_result.final_overlay_build.model.model_id,
        parent.eligibility_proof.complete_promoted_ground_row_ids,
        parent.eligibility_proof.source_exact_evidence_ids,
        parent.eligibility_proof.source_boundary_catalogue_ids,
        tuple(coverages),
    )
    family_model = PreregisteredReusablePartialRAPMV5(
        parent.model,
        protocol.protocol_id,
        proof.proof_id,
        tuple(sorted(item.initial_state.state_id for item in protocol.target_queries)),
    )
    return HeldOutFamilyPromotionBuildV1(
        protocol,
        parent,
        proof,
        family_model,
        source_result.result_id,
    )


def _query_for_occurrence(
    protocol: HeldOutFamilyProtocolV1,
    occurrence: FamilyLogicalOccurrenceV1,
) -> FamilyHeldOutQuerySpecV1:
    registered = {
        item.occurrence_id: item for item in protocol.logical_occurrences
    }
    if (
        occurrence.occurrence_id not in registered
        or registered[occurrence.occurrence_id].to_document()
        != occurrence.to_document()
    ):
        raise HeldOutFamilyInvariantViolation(
            "occurrence is not a member of the preregistered family"
        )
    return next(item for item in protocol.target_queries if item.query_id == occurrence.query_id)


def _run_warm_occurrence(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: HeldOutFamilyPromotionBuildV1,
    occurrence: FamilyLogicalOccurrenceV1,
) -> tuple[HeldOutThresholdBindingV1, HeldOutPlanProposalV1, HeldOutPlanAuditV1]:
    query = _query_for_occurrence(promotion.protocol, occurrence)
    if query.initial_state.state_id not in promotion.model.authorized_initial_state_ids:
        raise HeldOutFamilyInvariantViolation(
            "warm occurrence lies outside the V5 family scope"
        )
    proof = canonical_lmb_n6_return_bound_proof_v1()
    thresholds = FrozenPartialAuditThresholdsV1(
        promotion.model.model_id,
        query.horizon,
        (InitialStateMassV1(query.initial_state.state_id, Fraction(1)),),
        query.reward_weights,
        query.normalized_regret_tolerance,
        query.risk_tolerance,
        proof,
    )
    binding = HeldOutThresholdBindingV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        query.query_id,
        promotion.model.model_id,
        thresholds,
    )
    _, domains = _planner_context(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion.model,
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
            promotion.model.model_id,
            thresholds.horizon,
            tuple(
                ContingentPlanStageV1(time_index, assignments)
                for time_index, assignments in enumerate(schedule)
            ),
        )
        audit_result = _audit_verified_partial_model_v1(
            promotion.model,
            observation_log,
            semantics_profile,
            observation_authority,
            thresholds,
            plan,
        )
        plans[plan.plan_id] = plan
        summaries.append(_candidate_summary(thresholds, plan, audit_result))
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
            _semantic_plan_key(
                promotion.model, plans[item.contingent_plan_id]
            ),
            item.contingent_plan_id,
        ),
    )
    selected_plan = plans[selected.contingent_plan_id]
    proposal = HeldOutPlanProposalV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        query.query_id,
        promotion.model.model_id,
        binding.binding_id,
        thresholds.thresholds_id,
        domains,
        stage_count,
        stage_count,
        summaries_tuple,
        mode,
        selected_plan,
        _semantic_plan_key(promotion.model, selected_plan),
        len(summaries_tuple),
    )
    independent = _audit_verified_partial_model_v1(
        promotion.model,
        observation_log,
        semantics_profile,
        observation_authority,
        thresholds,
        selected_plan,
    )
    audit = HeldOutPlanAuditV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        query.query_id,
        promotion.model.model_id,
        binding.binding_id,
        proposal.result_id,
        selected_plan.plan_id,
        independent,
    )
    return binding, proposal, audit


def run_preregistered_heldout_family_occurrence_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: HeldOutFamilyPromotionBuildV1,
    occurrence: FamilyLogicalOccurrenceV1,
) -> tuple[HeldOutThresholdBindingV1, HeldOutPlanProposalV1, HeldOutPlanAuditV1]:
    """Kernel-free model planning and certification for one frozen occurrence."""

    if type(promotion) is not HeldOutFamilyPromotionBuildV1:
        raise HeldOutFamilyInvariantViolation(
            "warm family consumer rejects substituted promotions"
        )
    if type(occurrence) is not FamilyLogicalOccurrenceV1:
        raise HeldOutFamilyInvariantViolation(
            "warm family consumer rejects substituted occurrences"
        )
    return _run_warm_occurrence(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion,
        occurrence,
    )


def run_cold_direct_h1_baseline_v1(
    observation_log: ObservationLogManifestV1,
    query: FamilyHeldOutQuerySpecV1,
    occurrence: FamilyLogicalOccurrenceV1,
    kernel: LMBKernel,
) -> ColdDirectPlanResultV1:
    """Complete exact H1 ground planning with no promoted/source input."""

    if type(query) is not FamilyHeldOutQuerySpecV1:
        raise HeldOutFamilyInvariantViolation(
            "cold direct planner rejects substituted query specs"
        )
    if type(occurrence) is not FamilyLogicalOccurrenceV1:
        raise HeldOutFamilyInvariantViolation(
            "cold direct planner rejects substituted occurrences"
        )
    if occurrence.query_id != query.query_id:
        raise HeldOutFamilyInvariantViolation(
            "cold direct occurrence/query identity mismatch"
        )
    authority = canonical_lmb_query_kernel_authority_v1()
    _validate_canonical_kernel(kernel, observation_log, authority)
    ground_state = _lmb_state(query.initial_state)
    actions = tuple(
        sorted(
            (
                CanonicalGroundActionV1(
                    query.initial_state.state_id,
                    f"tile={action.tile}",
                    kernel.tile_types[action.tile],
                )
                for action in kernel.actions(ground_state)
            ),
            key=lambda item: item.action_id,
        )
    )
    catalogue = ColdDirectActionCatalogueV1(
        occurrence.occurrence_id,
        query.query_id,
        query.initial_state,
        actions,
    )
    weights = {item.name: item.weight for item in query.reward_weights}
    outcomes: list[ColdDirectOutcomeV1] = []
    for sequence, action in enumerate(actions, start=1):
        tile = int(action.action_key.split("=", 1)[1])
        exact_outcomes = kernel.step(ground_state, LMBAction(tile))
        if len(exact_outcomes) != 1:
            raise HeldOutFamilyInvariantViolation(
                "cold direct canonical transition must be deterministic"
            )
        exact = exact_outcomes[0]
        reward_features = tuple(exact.reward_features)
        weighted_reward = sum(
            (weights[name] * value for name, value in reward_features),
            Fraction(0),
        )
        outcomes.append(
            ColdDirectOutcomeV1(
                sequence,
                catalogue.catalogue_id,
                action,
                _state_observation(exact.next_state),
                reward_features,
                weighted_reward,
                exact.failure,
                exact.terminal,
            )
        )
    feasible = tuple(item for item in outcomes if not item.failure)
    if not feasible:
        raise HeldOutFamilyInvariantViolation(
            "cold direct fixture unexpectedly has no zero-risk action"
        )
    selected = min(
        feasible,
        key=lambda item: (-item.weighted_reward, item.action.action_id),
    )
    optimal = max(item.weighted_reward for item in feasible)
    normalized_regret = (optimal - selected.weighted_reward) / Fraction(4)
    return ColdDirectPlanResultV1(
        occurrence,
        query,
        catalogue,
        tuple(outcomes),
        selected.action.action_id,
        selected.weighted_reward,
        Fraction(int(selected.failure)),
        normalized_regret,
    )


def _match_occurrence(
    promotion: HeldOutFamilyPromotionBuildV1,
    source_result: MultiStepQueryRefinementResultV1,
    occurrence: FamilyLogicalOccurrenceV1,
    query: FamilyHeldOutQuerySpecV1,
    binding: HeldOutThresholdBindingV1,
    proposal: HeldOutPlanProposalV1,
    audit: HeldOutPlanAuditV1,
    cold: ColdDirectPlanResultV1,
) -> MatchedHeldOutOccurrenceV1:
    coverage = next(
        item
        for item in promotion.eligibility_proof.target_coverages
        if item.query_id == query.query_id
    )
    source_catalogue = next(
        item
        for item in source_result.boundary_expansion.catalogues
        if item.state.state_id == query.initial_state.state_id
    )
    if tuple(item.to_document() for item in cold.catalogue.actions) != tuple(
        item.to_document() for item in source_catalogue.actions
    ):
        raise HeldOutFamilyInvariantViolation(
            "cold direct catalogue differs from complete source evidence"
        )
    evidence_by_row = {
        item.ground_row_id: item
        for bundle in (source_result.round_one_bundle, source_result.round_two_bundle)
        for item in bundle.evidence
    }
    matched_evidence: list[str] = []
    for outcome in cold.outcomes:
        evidence = evidence_by_row[outcome.action.ground_row_id]
        if (
            evidence.successor_state.to_document()
            != outcome.successor_state.to_document()
            or evidence.reward_features != outcome.reward_features
            or evidence.failure is not outcome.failure
            or evidence.terminal is not outcome.terminal
        ):
            raise HeldOutFamilyInvariantViolation(
                "cold direct transition differs from promoted exact evidence"
            )
        matched_evidence.append(evidence.evidence_id)
    if tuple(sorted(matched_evidence)) != coverage.source_evidence_ids:
        raise HeldOutFamilyInvariantViolation(
            "matched source evidence differs from the family eligibility proof"
        )
    warm_work = FamilyNativeWorkVectorV1(
        "WARM_TARGET_OPERATIONAL",
        occurrence.occurrence_id,
        0,
        0,
        0,
        proposal.candidate_count,
        proposal.fixed_plan_audit_count + 1,
        0,
        0,
    )
    cold_work = FamilyNativeWorkVectorV1(
        "COLD_DIRECT_OPERATIONAL",
        occurrence.occurrence_id,
        cold.exact_transition_calls,
        cold.direct_catalogue_calls,
        cold.step_internal_legality_checks,
        0,
        0,
        cold.ground_action_candidates,
        cold.direct_ground_optimizer_calls,
    )
    return MatchedHeldOutOccurrenceV1(
        occurrence,
        query,
        binding,
        proposal,
        audit,
        cold,
        coverage.source_catalogue_id,
        tuple(sorted(matched_evidence)),
        warm_work,
        cold_work,
    )


def _prefixes(
    matched: tuple[MatchedHeldOutOccurrenceV1, ...],
    source_work: FamilyNativeWorkVectorV1,
    promotion_work: FamilyNativeWorkVectorV1,
) -> tuple[FamilyPrefixAccountingV1, ...]:
    result: list[FamilyPrefixAccountingV1] = []
    for length in range(1, len(matched) + 1):
        prefix = matched[:length]
        source_warm_transitions = source_work.exact_transition_calls
        source_warm_catalogues = source_work.direct_catalogue_calls
        verification_warm_transitions = (
            source_warm_transitions + promotion_work.exact_transition_calls
        )
        verification_warm_catalogues = (
            source_warm_catalogues + promotion_work.direct_catalogue_calls
        )
        cold_transitions = sum(
            item.cold_work.exact_transition_calls for item in prefix
        )
        cold_catalogues = sum(
            item.cold_work.direct_catalogue_calls for item in prefix
        )
        result.append(
            FamilyPrefixAccountingV1(
                length,
                tuple(item.occurrence.occurrence_id for item in prefix),
                source_warm_transitions,
                source_warm_catalogues,
                verification_warm_transitions,
                verification_warm_catalogues,
                cold_transitions,
                cold_catalogues,
                sum(item.warm_work.model_plan_candidates for item in prefix),
                sum(item.warm_work.model_fixed_plan_audits for item in prefix),
                sum(item.cold_work.ground_action_candidates for item in prefix),
                sum(
                    item.cold_work.direct_ground_optimizer_calls for item in prefix
                ),
                _relation(
                    source_warm_transitions,
                    source_warm_catalogues,
                    cold_transitions,
                    cold_catalogues,
                ),
                _relation(
                    verification_warm_transitions,
                    verification_warm_catalogues,
                    cold_transitions,
                    cold_catalogues,
                ),
            )
        )
    return tuple(result)


def run_lmb_heldout_family_amortization_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    protocol: HeldOutFamilyProtocolV1,
    source_result: MultiStepQueryRefinementResultV1,
    kernel: LMBKernel,
) -> HeldOutFamilyAmortizationResultV1:
    """Run one promotion, ten warm/cold pairs, and exact prefix accounting."""

    promotion = promote_lmb_heldout_family_v1(
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
    matched: list[MatchedHeldOutOccurrenceV1] = []
    for occurrence in protocol.logical_occurrences:
        query = _query_for_occurrence(protocol, occurrence)
        binding, proposal, audit = run_preregistered_heldout_family_occurrence_v1(
            observation_log,
            semantics_profile,
            observation_authority,
            promotion,
            occurrence,
        )
        cold = run_cold_direct_h1_baseline_v1(
            observation_log,
            query,
            occurrence,
            kernel,
        )
        matched.append(
            _match_occurrence(
                promotion,
                source_result,
                occurrence,
                query,
                binding,
                proposal,
                audit,
                cold,
            )
        )
    matched_tuple = tuple(matched)
    source_transition_calls = (
        source_result.telemetry.cumulative_exact_kernel_queries
    )
    source_catalogue_calls = (
        source_result.telemetry.boundary_action_catalogue_queries
    )
    source_work = FamilyNativeWorkVectorV1(
        "SOURCE_ACQUISITION_OPERATIONAL",
        None,
        source_transition_calls,
        source_catalogue_calls,
        source_transition_calls,
        0,
        0,
        0,
        0,
    )
    replay_proof = promotion.parent_promotion.eligibility_proof
    promotion_work = FamilyNativeWorkVectorV1(
        "PROMOTION_REPLAY_EVALUATION",
        None,
        replay_proof.independent_replay_transition_calls,
        replay_proof.independent_replay_direct_catalogue_calls,
        replay_proof.independent_replay_transition_calls,
        0,
        0,
        0,
        0,
    )
    prefix_values = _prefixes(matched_tuple, source_work, promotion_work)
    telemetry = HeldOutFamilyTelemetryV1(
        len(protocol.target_queries),
        len(protocol.logical_occurrences),
        len(protocol.logical_occurrences) - len(protocol.target_queries),
        source_work.exact_transition_calls,
        source_work.direct_catalogue_calls,
        promotion_work.exact_transition_calls,
        promotion_work.direct_catalogue_calls,
        sum(item.warm_work.exact_transition_calls for item in matched_tuple),
        sum(item.warm_work.direct_catalogue_calls for item in matched_tuple),
        sum(item.cold_work.exact_transition_calls for item in matched_tuple),
        sum(item.cold_work.direct_catalogue_calls for item in matched_tuple),
        sum(item.warm_work.model_plan_candidates for item in matched_tuple),
        sum(item.warm_work.model_fixed_plan_audits for item in matched_tuple),
        sum(item.cold_work.ground_action_candidates for item in matched_tuple),
        sum(
            item.cold_work.direct_ground_optimizer_calls
            for item in matched_tuple
        ),
        next(
            item.prefix_length
            for item in prefix_values
            if item.source_inclusive_relation
            is ComponentwiseRelation.WARM_STRICT_COMPONENTWISE
        ),
        next(
            item.prefix_length
            for item in prefix_values
            if item.verification_inclusive_relation
            is ComponentwiseRelation.WARM_STRICT_COMPONENTWISE
        ),
    )
    return HeldOutFamilyAmortizationResultV1(
        source_result.result_id,
        promotion,
        source_work,
        promotion_work,
        matched_tuple,
        prefix_values,
        telemetry,
    )


def verify_lmb_heldout_family_amortization_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    protocol: HeldOutFamilyProtocolV1,
    source_result: MultiStepQueryRefinementResultV1,
    kernel: LMBKernel,
    claimed_result: HeldOutFamilyAmortizationResultV1,
) -> HeldOutFamilyAmortizationResultV1:
    """Independently rebuild the promotion, every pair, and every prefix."""

    if type(claimed_result) is not HeldOutFamilyAmortizationResultV1:
        raise HeldOutFamilyInvariantViolation(
            "family verifier rejects substituted results"
        )
    expected = run_lmb_heldout_family_amortization_v1(
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
    if expected.to_document() != claimed_result.to_document():
        raise HeldOutFamilyInvariantViolation(
            "family independent replay differs from the claimed result"
        )
    return expected


__all__ = [
    "ColdDirectPlanResultV1",
    "ComponentwiseRelation",
    "FAMILY_TARGET_STATES",
    "FamilyHeldOutQuerySpecV1",
    "FamilyLogicalOccurrenceV1",
    "FamilyNativeWorkVectorV1",
    "FamilyPrefixAccountingV1",
    "HeldOutFamilyAmortizationResultV1",
    "HeldOutFamilyInvariantViolation",
    "HeldOutFamilyPromotionBuildV1",
    "HeldOutFamilyProtocolV1",
    "HeldOutFamilyTelemetryV1",
    "MatchedHeldOutOccurrenceV1",
    "OCCURRENCE_QUERY_INDICES",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "SUCCESS_STATUS",
    "preregister_lmb_heldout_family_v1",
    "promote_lmb_heldout_family_v1",
    "run_cold_direct_h1_baseline_v1",
    "run_lmb_heldout_family_amortization_v1",
    "run_preregistered_heldout_family_occurrence_v1",
    "verify_lmb_heldout_family_amortization_v1",
]
