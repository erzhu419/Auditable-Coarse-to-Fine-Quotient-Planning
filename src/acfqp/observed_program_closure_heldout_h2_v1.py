"""Preregistered held-out H2 consumption of an observed program closure.

This module is intentionally a new authority boundary.  It consumes a fully
replayed :mod:`observed_program_closure_synthesis_v1` result, applies its frozen
programs to one preregistered state that was absent from the source log, and
keeps all target dynamics vacuous until a selected fixed-plan proof fails.

The embedded :class:`PortablePartialRAPMV1` objects are structural planning
views only.  They are never accepted as stand-alone certificate authority:
every proposal, audit, authorization, evidence bundle, and final certificate
is bound to an enclosing :class:`ProgramClosureHeldOutEpochV1` and the complete
source/synthesis/preregistration chain.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
import hashlib
import importlib
import inspect
from itertools import product
from typing import Any, Mapping

from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
)
from acfqp.multistep_query_refinement_v1 import (
    canonical_lmb_query_kernel_authority_v1,
)
from acfqp.observation_partial_rapm_v1 import (
    AmbiguityRowStatus,
    CanonicalGroundActionV1,
    CanonicalStateObservationV1,
    ConcretizerRowV1,
    ObservationCoverageV1,
    ObservationLogManifestV1,
    PartialCellV1,
    PartialGroundRowV1,
    PartialSemanticActionV1,
    PartialSemanticRealizationV1,
    PlanningKind,
    PortablePartialRAPMV1,
    PreregisteredObservationAuthorityV1,
    DeterministicObservationProfileV1,
    TrustedCompleteActionCatalogueV1,
    TypedActionAtomKind,
    _ambiguity_payload,
    validate_preregistered_observation_source_graph_v1,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import _eval_expression
from acfqp.partial_model_planner_v1 import (
    PRODUCTION_CANDIDATE_CAP,
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
    FailedProofReason,
    FrozenContingentAbstractPlanV1,
    FrozenPartialAuditThresholdsV1,
    InitialStateMassV1,
    PartialAuditOutcome,
    PartialSoundAuditResultV1,
    RewardWeightV1,
    _audit_verified_partial_model_v1,
    canonical_lmb_n6_return_bound_proof_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.query_local_refinement_v1 import _kernel_source_digest


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "lmb_observed_program_closure_heldout_h2_v0"
SUCCESS_STATUS = "CERTIFIED_OBSERVED_PROGRAM_CLOSURE_HELDOUT_H2_RECOVERY"

TARGET_GROUND_STATE = LMBState(35, (2, 1), LMBStatus.ACTIVE)
TARGET_ACTION_TILES = (2, 3, 4)
SOURCE_REFERENCE_GROUND_STATE = LMBState(7, (2, 1), LMBStatus.ACTIVE)
SOURCE_SUCCESSOR_GROUND_STATE = LMBState(39, (0, 1), LMBStatus.ACTIVE)
HORIZON = 2

# Frozen after the complete implementation below is assembled.  The digest
# covers the chronology-sensitive builders, not comments or formatting.
HELDOUT_IMPLEMENTATION_SHA256 = (
    "9bda243287c2bea3db70d822cd027451e7b6f2e34dffd99beb5a7a726e6c1c94"
)

DOMAIN_TAGS = {
    "query": "acfqp:program-closure-heldout-h2-query:v1",
    "preregistration": "acfqp:program-closure-heldout-h2-preregistration:v1",
    "catalogue": "acfqp:program-closure-heldout-h2-catalogue:v1",
    "evidence": "acfqp:program-closure-heldout-h2-transition-evidence:v1",
    "bundle": "acfqp:program-closure-heldout-h2-evidence-bundle:v1",
    "epoch": "acfqp:program-closure-heldout-h2-epoch:v1",
    "proposal": "acfqp:program-closure-heldout-h2-plan-proposal:v1",
    "audit": "acfqp:program-closure-heldout-h2-selected-audit:v1",
    "row_cause": "acfqp:program-closure-heldout-h2-row-cause:v1",
    "authorization": "acfqp:program-closure-heldout-h2-authorization:v1",
    "transfer": "acfqp:program-closure-heldout-h2-coordinate-transfer:v1",
    "ledger": "acfqp:program-closure-heldout-h2-evidence-ledger:v1",
    "result": "acfqp:program-closure-heldout-h2-result:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-058 held-out H2 content domains must be unique")


class ProgramClosureHeldOutH2InvariantViolation(ValueError):
    """The held-out construction or its authority chain is inconsistent."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ProgramClosureHeldOutH2InvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ProgramClosureHeldOutH2InvariantViolation(
            f"{field} is not a content ID"
        ) from error


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ProgramClosureHeldOutH2InvariantViolation(
            f"{field} must be an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field: str) -> Fraction:
    if type(value) not in (int, Fraction):
        raise ProgramClosureHeldOutH2InvariantViolation(
            f"{field} must be an exact rational"
        )
    return Fraction(value)


def _fraction_document(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _sorted_ids(
    values: Any, field: str, *, expected_count: int | None = None
) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or any(type(item) is not str for item in values)
        or values != tuple(sorted(set(values)))
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            f"{field} must contain sorted unique content IDs"
        )
    if expected_count is not None and len(values) != expected_count:
        raise ProgramClosureHeldOutH2InvariantViolation(
            f"{field} must contain exactly {expected_count} IDs"
        )
    for item in values:
        _cid(item, field)
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
    try:
        status = LMBStatus(state.status)
    except ValueError as error:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out state has an unregistered LMB status"
        ) from error
    return LMBState(state.removed_mask, state.buffer_counts, status)


def _tile(action: CanonicalGroundActionV1) -> int:
    if not action.action_key.startswith("tile="):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out ground action is not a canonical tile action"
        )
    try:
        tile = int(action.action_key.removeprefix("tile="))
    except ValueError as error:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out ground action tile is malformed"
        ) from error
    return tile


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutH2QueryV1:
    structural_id: str
    environment_instance_id: str
    observation_log_id: str
    semantics_profile_id: str
    observation_authority_id: str
    target_state: CanonicalStateObservationV1
    reward_weights: tuple[RewardWeightV1, ...]
    return_bound_proof_id: str
    horizon: int = HORIZON
    normalized_regret_tolerance: Fraction = Fraction(0)
    risk_tolerance: Fraction = Fraction(0)
    policy_class: str = "DETERMINISTIC_FINITE_HORIZON_ABSTRACT_CONTINGENT_PLAN"
    role: str = "PREREGISTERED_HELD_OUT_H2_QUERY"

    def __post_init__(self) -> None:
        for field in (
            "structural_id",
            "environment_instance_id",
            "observation_log_id",
            "semantics_profile_id",
            "observation_authority_id",
            "return_bound_proof_id",
        ):
            _cid(getattr(self, field), f"held-out query {field}")
        if (
            type(self.target_state) is not CanonicalStateObservationV1
            or self.target_state.to_document()
            != _state_observation(TARGET_GROUND_STATE).to_document()
            or self.reward_weights
            != (
                RewardWeightV1("match", Fraction(1)),
                RewardWeightV1("terminal_clear", Fraction(1)),
            )
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out query target or reward basis changed"
            )
        object.__setattr__(
            self,
            "normalized_regret_tolerance",
            _fraction(
                self.normalized_regret_tolerance,
                "held-out normalized-regret tolerance",
            ),
        )
        object.__setattr__(
            self,
            "risk_tolerance",
            _fraction(self.risk_tolerance, "held-out risk tolerance"),
        )
        if (
            self.horizon != HORIZON
            or self.normalized_regret_tolerance != 0
            or self.risk_tolerance != 0
            or self.policy_class
            != "DETERMINISTIC_FINITE_HORIZON_ABSTRACT_CONTINGENT_PLAN"
            or self.role != "PREREGISTERED_HELD_OUT_H2_QUERY"
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out H2 query semantics changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_query.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "structural_id": self.structural_id,
            "environment_instance_id": self.environment_instance_id,
            "observation_log_id": self.observation_log_id,
            "semantics_profile_id": self.semantics_profile_id,
            "observation_authority_id": self.observation_authority_id,
            "target_state": self.target_state.to_document(),
            "reward_weights": [item.to_document() for item in self.reward_weights],
            "return_bound_proof_id": self.return_bound_proof_id,
            "horizon": self.horizon,
            "normalized_regret_tolerance": _fraction_document(
                self.normalized_regret_tolerance
            ),
            "risk_tolerance": _fraction_document(self.risk_tolerance),
            "policy_class": self.policy_class,
            "role": self.role,
        }

    @property
    def query_id(self) -> str:
        return _content_id("query", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_id": self.query_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutH2PreregistrationV1:
    query: ProgramClosureHeldOutH2QueryV1
    source_state_ids: tuple[str, ...]
    source_ground_row_ids: tuple[str, ...]
    source_observed_ground_row_ids: tuple[str, ...]
    source_missing_ground_row_ids: tuple[str, ...]
    source_action_catalogue_ids: tuple[str, ...]
    source_observation_ids: tuple[str, ...]
    synthesis_inputs: tuple[str, ...] = (
        "observation_log",
        "semantics_profile",
        "observation_authority",
    )
    registered_before_synthesis: bool = True
    target_absent_from_source_states: bool = True
    target_rows_absent_from_source_rows: bool = True
    prospective_synthesis_or_epoch_ids_absent: bool = True
    kernel_input_count: int = 0

    def __post_init__(self) -> None:
        if type(self.query) is not ProgramClosureHeldOutH2QueryV1:
            raise ProgramClosureHeldOutH2InvariantViolation(
                "preregistration rejects substituted queries"
            )
        _sorted_ids(self.source_state_ids, "preregistered source states", expected_count=8)
        _sorted_ids(
            self.source_ground_row_ids,
            "preregistered source rows",
            expected_count=11,
        )
        _sorted_ids(
            self.source_observed_ground_row_ids,
            "preregistered observed rows",
            expected_count=7,
        )
        _sorted_ids(
            self.source_missing_ground_row_ids,
            "preregistered missing rows",
            expected_count=4,
        )
        _sorted_ids(
            self.source_action_catalogue_ids,
            "preregistered source catalogues",
            expected_count=8,
        )
        _sorted_ids(
            self.source_observation_ids,
            "preregistered source observations",
            expected_count=7,
        )
        if (
            tuple(sorted((*self.source_observed_ground_row_ids, *self.source_missing_ground_row_ids)))
            != self.source_ground_row_ids
            or self.query.target_state.state_id in self.source_state_ids
            or self.synthesis_inputs
            != ("observation_log", "semantics_profile", "observation_authority")
            or self.registered_before_synthesis is not True
            or self.target_absent_from_source_states is not True
            or self.target_rows_absent_from_source_rows is not True
            or self.prospective_synthesis_or_epoch_ids_absent is not True
            or self.kernel_input_count != 0
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "preregistration leaked target/synthesis work or changed source scope"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "query": self.query.to_document(),
            "source_state_ids": list(self.source_state_ids),
            "source_ground_row_ids": list(self.source_ground_row_ids),
            "source_observed_ground_row_ids": list(
                self.source_observed_ground_row_ids
            ),
            "source_missing_ground_row_ids": list(
                self.source_missing_ground_row_ids
            ),
            "source_action_catalogue_ids": list(
                self.source_action_catalogue_ids
            ),
            "source_observation_ids": list(self.source_observation_ids),
            "synthesis_inputs": list(self.synthesis_inputs),
            "registered_before_synthesis": self.registered_before_synthesis,
            "target_absent_from_source_states": (
                self.target_absent_from_source_states
            ),
            "target_rows_absent_from_source_rows": (
                self.target_rows_absent_from_source_rows
            ),
            "prospective_synthesis_or_epoch_ids_absent": (
                self.prospective_synthesis_or_epoch_ids_absent
            ),
            "kernel_input_count": self.kernel_input_count,
        }

    @property
    def preregistration_id(self) -> str:
        return _content_id("preregistration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "preregistration_id": self.preregistration_id,
        }


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutCatalogueV1:
    preregistration_id: str
    synthesis_result_id: str
    kernel_authority_id: str
    state: CanonicalStateObservationV1
    actions: tuple[CanonicalGroundActionV1, ...]
    source_synthesis_frozen_before_catalogue: bool = True
    action_catalogue_query_count: int = 1
    exact_transition_query_count: int = 0
    ground_search_count: int = 0

    def __post_init__(self) -> None:
        for field in (
            "preregistration_id",
            "synthesis_result_id",
            "kernel_authority_id",
        ):
            _cid(getattr(self, field), f"held-out catalogue {field}")
        if (
            type(self.state) is not CanonicalStateObservationV1
            or self.state.to_document()
            != _state_observation(TARGET_GROUND_STATE).to_document()
            or type(self.actions) is not tuple
            or any(type(item) is not CanonicalGroundActionV1 for item in self.actions)
            or tuple(_tile(item) for item in self.actions) != TARGET_ACTION_TILES
            or any(item.state_id != self.state.state_id for item in self.actions)
            or self.source_synthesis_frozen_before_catalogue is not True
            or self.action_catalogue_query_count != 1
            or self.exact_transition_query_count != 0
            or self.ground_search_count != 0
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out catalogue scope, order, or access accounting changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "synthesis_result_id": self.synthesis_result_id,
            "kernel_authority_id": self.kernel_authority_id,
            "state": self.state.to_document(),
            "actions": [item.to_document() for item in self.actions],
            "source_synthesis_frozen_before_catalogue": (
                self.source_synthesis_frozen_before_catalogue
            ),
            "action_catalogue_query_count": self.action_catalogue_query_count,
            "exact_transition_query_count": self.exact_transition_query_count,
            "ground_search_count": self.ground_search_count,
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_id": self.catalogue_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutTransitionEvidenceV1:
    sequence_number: int
    authorization_id: str
    kernel_authority_id: str
    ground_row_id: str
    state_id: str
    ground_action_id: str
    successor_state: CanonicalStateObservationV1
    reward_features: tuple[tuple[str, Fraction], ...]
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        _integer(self.sequence_number, "transition sequence", 1)
        for field in (
            "authorization_id",
            "kernel_authority_id",
            "ground_row_id",
            "state_id",
            "ground_action_id",
        ):
            _cid(getattr(self, field), f"transition evidence {field}")
        if type(self.successor_state) is not CanonicalStateObservationV1:
            raise ProgramClosureHeldOutH2InvariantViolation(
                "transition evidence rejects substituted successors"
            )
        if (
            type(self.reward_features) is not tuple
            or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or type(item[1]) not in (int, Fraction)
                for item in self.reward_features
            )
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "transition rewards must be exact feature pairs"
            )
        normalized = tuple(
            sorted((name, Fraction(value)) for name, value in self.reward_features)
        )
        if len(normalized) != len({name for name, _ in normalized}):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "transition rewards repeat a feature"
            )
        object.__setattr__(self, "reward_features", normalized)
        if (
            type(self.failure) is not bool
            or type(self.terminal) is not bool
            or (self.failure and not self.terminal)
            or self.failure
            != (self.successor_state.planning_kind is PlanningKind.FAILURE)
            or self.terminal
            != (self.successor_state.planning_kind is not PlanningKind.ACTIVE)
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "transition terminal/failure semantics changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_transition_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence_number": self.sequence_number,
            "authorization_id": self.authorization_id,
            "kernel_authority_id": self.kernel_authority_id,
            "ground_row_id": self.ground_row_id,
            "state_id": self.state_id,
            "ground_action_id": self.ground_action_id,
            "successor_state": self.successor_state.to_document(),
            "reward_features": [
                {"name": name, "value": _fraction_document(value)}
                for name, value in self.reward_features
            ],
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutEvidenceBundleV1:
    authorization_id: str
    kernel_authority_id: str
    requested_ground_row_ids: tuple[str, ...]
    evidence: tuple[ProgramClosureHeldOutTransitionEvidenceV1, ...]
    exact_transition_query_count: int = 3
    step_internal_legality_check_count: int = 3
    successor_catalogue_query_count: int = 0
    extra_ground_row_access_count: int = 0
    ground_search_count: int = 0

    def __post_init__(self) -> None:
        _cid(self.authorization_id, "evidence bundle authorization")
        _cid(self.kernel_authority_id, "evidence bundle kernel authority")
        requested = _sorted_ids(
            self.requested_ground_row_ids,
            "evidence bundle requested rows",
            expected_count=3,
        )
        if (
            type(self.evidence) is not tuple
            or any(
                type(item) is not ProgramClosureHeldOutTransitionEvidenceV1
                for item in self.evidence
            )
            or tuple(item.sequence_number for item in self.evidence) != (1, 2, 3)
            or tuple(sorted(item.ground_row_id for item in self.evidence)) != requested
            or any(
                item.authorization_id != self.authorization_id
                or item.kernel_authority_id != self.kernel_authority_id
                for item in self.evidence
            )
            or self.exact_transition_query_count != 3
            or self.step_internal_legality_check_count != 3
            or self.successor_catalogue_query_count != 0
            or self.extra_ground_row_access_count != 0
            or self.ground_search_count != 0
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "evidence bundle access, sequence, or row scope changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_evidence_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "authorization_id": self.authorization_id,
            "kernel_authority_id": self.kernel_authority_id,
            "requested_ground_row_ids": list(self.requested_ground_row_ids),
            "evidence": [item.to_document() for item in self.evidence],
            "exact_transition_query_count": self.exact_transition_query_count,
            "step_internal_legality_check_count": (
                self.step_internal_legality_check_count
            ),
            "successor_catalogue_query_count": (
                self.successor_catalogue_query_count
            ),
            "extra_ground_row_access_count": self.extra_ground_row_access_count,
            "ground_search_count": self.ground_search_count,
        }

    @property
    def bundle_id(self) -> str:
        return _content_id("bundle", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bundle_id": self.bundle_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutEpochV1:
    epoch_index: int
    epoch_kind: str
    preregistration_id: str
    synthesis_result_id: str
    base_partial_model_id: str
    previous_epoch_id: str | None
    catalogue_id: str
    evidence_bundle_id: str | None
    planning_view: PortablePartialRAPMV1
    source_state_ids: tuple[str, ...]
    source_ground_row_ids: tuple[str, ...]
    source_observed_ground_row_ids: tuple[str, ...]
    source_missing_ground_row_ids: tuple[str, ...]
    target_state_id: str
    target_ground_row_ids: tuple[str, ...]
    target_evidence_ids: tuple[str, ...]
    observed_ground_row_count: int
    missing_ground_row_count: int
    target_coordinate_values: tuple[int, ...]
    target_action_labels: tuple[tuple[bool, ...], ...]
    exact_transition_query_count: int
    structural_planning_view_only: bool = True
    bare_planning_view_certificate_authority: bool = False
    query_neutral: bool = False
    acquisition_query_neutral_attested: bool = False
    transition_closure_claimed: bool = False
    exact_quotient_claimed: bool = False
    promotion_authorized: bool = False
    learned_dynamics_claimed: bool = False

    def __post_init__(self) -> None:
        _integer(self.epoch_index, "held-out epoch index")
        if self.epoch_index not in (0, 1):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out epoch lies outside INITIAL/FINAL"
            )
        expected_kind = "INITIAL" if self.epoch_index == 0 else "FINAL"
        if self.epoch_kind != expected_kind:
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out epoch kind/index mismatch"
            )
        for field in (
            "preregistration_id",
            "synthesis_result_id",
            "base_partial_model_id",
            "catalogue_id",
            "target_state_id",
        ):
            _cid(getattr(self, field), f"held-out epoch {field}")
        if self.epoch_index == 0:
            if self.previous_epoch_id is not None or self.evidence_bundle_id is not None:
                raise ProgramClosureHeldOutH2InvariantViolation(
                    "INITIAL epoch cannot contain prospective evidence lineage"
                )
        else:
            _cid(self.previous_epoch_id, "FINAL previous epoch")
            _cid(self.evidence_bundle_id, "FINAL evidence bundle")
        if type(self.planning_view) is not PortablePartialRAPMV1:
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out epoch rejects substituted planning views"
            )
        _sorted_ids(self.source_state_ids, "epoch source states", expected_count=8)
        _sorted_ids(self.source_ground_row_ids, "epoch source rows", expected_count=11)
        _sorted_ids(
            self.source_observed_ground_row_ids,
            "epoch source observed rows",
            expected_count=7,
        )
        _sorted_ids(
            self.source_missing_ground_row_ids,
            "epoch source missing rows",
            expected_count=4,
        )
        _sorted_ids(
            self.target_ground_row_ids, "epoch target rows", expected_count=3
        )
        _sorted_ids(
            self.target_evidence_ids,
            "epoch target evidence",
            expected_count=(0 if self.epoch_index == 0 else 3),
        )
        if (
            self.target_state_id
            != _state_observation(TARGET_GROUND_STATE).state_id
            or self.target_state_id in self.source_state_ids
            or set(self.target_ground_row_ids) & set(self.source_ground_row_ids)
            or tuple(sorted((*self.source_observed_ground_row_ids, *self.source_missing_ground_row_ids)))
            != self.source_ground_row_ids
            or self.planning_view.coverage.registered_state_ids
            != tuple(sorted((*self.source_state_ids, self.target_state_id)))
            or self.planning_view.coverage.registered_ground_row_ids
            != tuple(sorted((*self.source_ground_row_ids, *self.target_ground_row_ids)))
            or len(self.planning_view.cells) != 6
            or len(
                tuple(
                    item
                    for item in self.planning_view.cells
                    if item.planning_kind is PlanningKind.ACTIVE
                )
            )
            != 4
            or len(self.planning_view.semantic_actions) != 5
            or len(self.planning_view.concretizer_rows) != 8
            or len(self.planning_view.semantic_realizations) != 8
            or self.target_coordinate_values != (3,)
            or self.target_action_labels != ((False,), (True,), (True,))
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out epoch structural shape or target coordinate changed"
            )
        expected_observed = 7 if self.epoch_index == 0 else 10
        expected_missing = 7 if self.epoch_index == 0 else 4
        expected_queries = 0 if self.epoch_index == 0 else 3
        target_rows = {
            item.ground_row_id: item
            for item in self.planning_view.ground_rows
            if item.ground_row_id in set(self.target_ground_row_ids)
        }
        source_rows = {
            item.ground_row_id: item
            for item in self.planning_view.ground_rows
            if item.ground_row_id in set(self.source_ground_row_ids)
        }
        if (
            len(target_rows) != 3
            or len(source_rows) != 11
            or self.observed_ground_row_count != expected_observed
            or self.missing_ground_row_count != expected_missing
            or len(self.planning_view.coverage.observed_ground_row_ids)
            != expected_observed
            or len(self.planning_view.coverage.missing_ground_row_ids)
            != expected_missing
            or self.exact_transition_query_count != expected_queries
            or any(
                source_rows[row_id].status is not AmbiguityRowStatus.OBSERVED_SINGLETON
                for row_id in self.source_observed_ground_row_ids
            )
            or any(
                source_rows[row_id].status is not AmbiguityRowStatus.MISSING_VACUOUS
                for row_id in self.source_missing_ground_row_ids
            )
            or any(
                row.status
                is not (
                    AmbiguityRowStatus.MISSING_VACUOUS
                    if self.epoch_index == 0
                    else AmbiguityRowStatus.OBSERVED_SINGLETON
                )
                for row in target_rows.values()
            )
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out epoch coverage or source-row preservation changed"
            )
        if (
            self.structural_planning_view_only is not True
            or self.bare_planning_view_certificate_authority is not False
            or self.query_neutral is not False
            or self.acquisition_query_neutral_attested is not False
            or self.transition_closure_claimed is not False
            or self.exact_quotient_claimed is not False
            or self.promotion_authorized is not False
            or self.learned_dynamics_claimed is not False
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out epoch crossed its query-local claim boundary"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch_index": self.epoch_index,
            "epoch_kind": self.epoch_kind,
            "preregistration_id": self.preregistration_id,
            "synthesis_result_id": self.synthesis_result_id,
            "base_partial_model_id": self.base_partial_model_id,
            "previous_epoch_id": self.previous_epoch_id,
            "catalogue_id": self.catalogue_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "planning_view": self.planning_view.to_document(),
            "source_state_ids": list(self.source_state_ids),
            "source_ground_row_ids": list(self.source_ground_row_ids),
            "source_observed_ground_row_ids": list(
                self.source_observed_ground_row_ids
            ),
            "source_missing_ground_row_ids": list(
                self.source_missing_ground_row_ids
            ),
            "target_state_id": self.target_state_id,
            "target_ground_row_ids": list(self.target_ground_row_ids),
            "target_evidence_ids": list(self.target_evidence_ids),
            "observed_ground_row_count": self.observed_ground_row_count,
            "missing_ground_row_count": self.missing_ground_row_count,
            "target_coordinate_values": list(self.target_coordinate_values),
            "target_action_labels": [
                list(item) for item in self.target_action_labels
            ],
            "exact_transition_query_count": self.exact_transition_query_count,
            "structural_planning_view_only": self.structural_planning_view_only,
            "bare_planning_view_certificate_authority": (
                self.bare_planning_view_certificate_authority
            ),
            "query_neutral": self.query_neutral,
            "acquisition_query_neutral_attested": (
                self.acquisition_query_neutral_attested
            ),
            "transition_closure_claimed": self.transition_closure_claimed,
            "exact_quotient_claimed": self.exact_quotient_claimed,
            "promotion_authorized": self.promotion_authorized,
            "learned_dynamics_claimed": self.learned_dynamics_claimed,
        }

    @property
    def epoch_id(self) -> str:
        return _content_id("epoch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "epoch_id": self.epoch_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutPlanProposalV1:
    epoch_id: str
    planning_view_id: str
    thresholds: FrozenPartialAuditThresholdsV1
    action_domains: tuple[PartialPlannerCellActionDomainV1, ...]
    candidate_summaries: tuple[PartialPlannerCandidateSummaryV1, ...]
    selection_mode: PartialModelPlannerSelectionMode
    selected_plan: FrozenContingentAbstractPlanV1
    selected_semantic_key: tuple[int, ...]
    per_stage_assignment_count: int = 2
    candidate_count: int = 4
    candidate_audit_count: int = 4
    exact_transition_calls_during_planning: int = 0
    proposal_is_certificate_authority: bool = False

    def __post_init__(self) -> None:
        _cid(self.epoch_id, "held-out proposal epoch")
        _cid(self.planning_view_id, "held-out proposal planning view")
        if type(self.thresholds) is not FrozenPartialAuditThresholdsV1:
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out proposal rejects substituted thresholds"
            )
        if (
            type(self.action_domains) is not tuple
            or any(
                type(item) is not PartialPlannerCellActionDomainV1
                for item in self.action_domains
            )
            or type(self.candidate_summaries) is not tuple
            or any(
                type(item) is not PartialPlannerCandidateSummaryV1
                for item in self.candidate_summaries
            )
            or type(self.selection_mode) is not PartialModelPlannerSelectionMode
            or type(self.selected_plan) is not FrozenContingentAbstractPlanV1
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out proposal contains substituted planner artifacts"
            )
        selected_ids = {
            item.contingent_plan_id for item in self.candidate_summaries
        }
        if (
            self.thresholds.partial_model_id != self.planning_view_id
            or self.selected_plan.partial_model_id != self.planning_view_id
            or self.selected_plan.plan_id not in selected_ids
            or len(self.action_domains) != 4
            or len(self.candidate_summaries) != 4
            or self.per_stage_assignment_count != 2
            or self.candidate_count != 4
            or self.candidate_audit_count != 4
            or self.exact_transition_calls_during_planning != 0
            or self.proposal_is_certificate_authority is not False
            or self.selected_semantic_key
            != (0, 1, 0, 1, 0, 1, 0, 1)
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out proposal enumeration, selection, or authority changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_plan_proposal.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch_id": self.epoch_id,
            "planning_view_id": self.planning_view_id,
            "thresholds": self.thresholds.to_document(),
            "action_domains": [item.to_document() for item in self.action_domains],
            "candidate_summaries": [
                item.to_document() for item in self.candidate_summaries
            ],
            "selection_mode": self.selection_mode.value,
            "selected_plan": self.selected_plan.to_document(),
            "selected_semantic_key": list(self.selected_semantic_key),
            "per_stage_assignment_count": self.per_stage_assignment_count,
            "candidate_count": self.candidate_count,
            "candidate_audit_count": self.candidate_audit_count,
            "exact_transition_calls_during_planning": (
                self.exact_transition_calls_during_planning
            ),
            "proposal_is_certificate_authority": (
                self.proposal_is_certificate_authority
            ),
        }

    @property
    def proposal_id(self) -> str:
        return _content_id("proposal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_id": self.proposal_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutSelectedAuditV1:
    epoch_id: str
    planning_view_id: str
    proposal_id: str
    selected_plan_id: str
    audit_result: PartialSoundAuditResultV1
    audit_role: str = "INDEPENDENT_SELECTED_FIXED_PLAN_AUDIT"
    independent_from_candidate_ranking: bool = True
    exact_transition_calls_during_audit: int = 0
    bare_inner_audit_certificate_authority: bool = False
    enclosing_epoch_authority_required: bool = True

    def __post_init__(self) -> None:
        for field in (
            "epoch_id",
            "planning_view_id",
            "proposal_id",
            "selected_plan_id",
        ):
            _cid(getattr(self, field), f"held-out selected audit {field}")
        if (
            type(self.audit_result) is not PartialSoundAuditResultV1
            or self.audit_result.partial_model_id != self.planning_view_id
            or self.audit_result.contingent_plan_id != self.selected_plan_id
            or self.audit_role != "INDEPENDENT_SELECTED_FIXED_PLAN_AUDIT"
            or self.independent_from_candidate_ranking is not True
            or self.exact_transition_calls_during_audit != 0
            or self.bare_inner_audit_certificate_authority is not False
            or self.enclosing_epoch_authority_required is not True
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out independent audit authority or binding changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_selected_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch_id": self.epoch_id,
            "planning_view_id": self.planning_view_id,
            "proposal_id": self.proposal_id,
            "selected_plan_id": self.selected_plan_id,
            "audit_result": self.audit_result.to_document(),
            "audit_role": self.audit_role,
            "independent_from_candidate_ranking": (
                self.independent_from_candidate_ranking
            ),
            "exact_transition_calls_during_audit": (
                self.exact_transition_calls_during_audit
            ),
            "bare_inner_audit_certificate_authority": (
                self.bare_inner_audit_certificate_authority
            ),
            "enclosing_epoch_authority_required": (
                self.enclosing_epoch_authority_required
            ),
        }

    @property
    def audit_id(self) -> str:
        return _content_id("audit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutRowCauseV1:
    ground_row_id: str
    ground_action_id: str
    selected_plan_risk_support: bool
    unrestricted_value_challenger: bool
    current_epoch_missing: bool = True
    earliest_time_index: int = 0
    remaining_horizon: int = HORIZON

    def __post_init__(self) -> None:
        _cid(self.ground_row_id, "held-out row cause ground row")
        _cid(self.ground_action_id, "held-out row cause ground action")
        if (
            type(self.selected_plan_risk_support) is not bool
            or type(self.unrestricted_value_challenger) is not bool
            or not (
                self.selected_plan_risk_support
                or self.unrestricted_value_challenger
            )
            or self.current_epoch_missing is not True
            or self.earliest_time_index != 0
            or self.remaining_horizon != HORIZON
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out row cause lacks a current frontier-local obligation"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_row_cause.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "ground_row_id": self.ground_row_id,
            "ground_action_id": self.ground_action_id,
            "selected_plan_risk_support": self.selected_plan_risk_support,
            "unrestricted_value_challenger": (
                self.unrestricted_value_challenger
            ),
            "current_epoch_missing": self.current_epoch_missing,
            "earliest_time_index": self.earliest_time_index,
            "remaining_horizon": self.remaining_horizon,
        }

    @property
    def cause_id(self) -> str:
        return _content_id("row_cause", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cause_id": self.cause_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutEvidenceAuthorizationV1:
    preregistration_id: str
    synthesis_result_id: str
    initial_epoch_id: str
    initial_proposal_id: str
    initial_selected_audit_id: str
    failed_frontier_id: str
    target_state_id: str
    requested_ground_row_ids: tuple[str, ...]
    row_causes: tuple[ProgramClosureHeldOutRowCauseV1, ...]
    selected_plan_risk_row_count: int
    unrestricted_value_challenger_row_count: int
    distinct_requested_row_count: int
    request_preparation_kernel_calls: int = 0
    request_preparation_ground_searches: int = 0
    single_use: bool = True
    selected_failure_required: bool = True
    global_minimum_claimed: bool = False

    def __post_init__(self) -> None:
        for field in (
            "preregistration_id",
            "synthesis_result_id",
            "initial_epoch_id",
            "initial_proposal_id",
            "initial_selected_audit_id",
            "failed_frontier_id",
            "target_state_id",
        ):
            _cid(getattr(self, field), f"held-out authorization {field}")
        requested = _sorted_ids(
            self.requested_ground_row_ids,
            "held-out authorized rows",
            expected_count=3,
        )
        if (
            type(self.row_causes) is not tuple
            or any(
                type(item) is not ProgramClosureHeldOutRowCauseV1
                for item in self.row_causes
            )
            or tuple(item.ground_row_id for item in self.row_causes) != requested
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out authorization causes do not cover its rows"
            )
        risk_count = sum(item.selected_plan_risk_support for item in self.row_causes)
        value_count = sum(
            item.unrestricted_value_challenger for item in self.row_causes
        )
        if (
            self.target_state_id != _state_observation(TARGET_GROUND_STATE).state_id
            or self.selected_plan_risk_row_count != 1
            or self.unrestricted_value_challenger_row_count != 3
            or self.distinct_requested_row_count != 3
            or risk_count != 1
            or value_count != 3
            or self.request_preparation_kernel_calls != 0
            or self.request_preparation_ground_searches != 0
            or self.single_use is not True
            or self.selected_failure_required is not True
            or self.global_minimum_claimed is not False
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out 1/3/3 authorization or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "synthesis_result_id": self.synthesis_result_id,
            "initial_epoch_id": self.initial_epoch_id,
            "initial_proposal_id": self.initial_proposal_id,
            "initial_selected_audit_id": self.initial_selected_audit_id,
            "failed_frontier_id": self.failed_frontier_id,
            "target_state_id": self.target_state_id,
            "requested_ground_row_ids": list(self.requested_ground_row_ids),
            "row_causes": [item.to_document() for item in self.row_causes],
            "selected_plan_risk_row_count": self.selected_plan_risk_row_count,
            "unrestricted_value_challenger_row_count": (
                self.unrestricted_value_challenger_row_count
            ),
            "distinct_requested_row_count": self.distinct_requested_row_count,
            "request_preparation_kernel_calls": (
                self.request_preparation_kernel_calls
            ),
            "request_preparation_ground_searches": (
                self.request_preparation_ground_searches
            ),
            "single_use": self.single_use,
            "selected_failure_required": self.selected_failure_required,
            "global_minimum_claimed": self.global_minimum_claimed,
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authorization_id": self.authorization_id,
        }


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutCoordinateTransferV1:
    final_epoch_id: str
    synthesis_result_id: str
    source_state_id: str
    heldout_state_id: str
    shared_coordinate_values: tuple[int, ...]
    semantic_labels: tuple[tuple[bool, ...], ...]
    source_support_cardinalities: tuple[int, ...]
    heldout_support_cardinalities: tuple[int, ...]
    abstract_realizations_equal: tuple[bool, ...]
    compared_after_target_evidence: bool = True
    used_to_fill_missing_target_rows: bool = False
    coordinate_invention_claimed: bool = False
    statistical_generalization_claimed: bool = False

    def __post_init__(self) -> None:
        for field in (
            "final_epoch_id",
            "synthesis_result_id",
            "source_state_id",
            "heldout_state_id",
        ):
            _cid(getattr(self, field), f"coordinate transfer {field}")
        if (
            self.source_state_id
            != _state_observation(SOURCE_REFERENCE_GROUND_STATE).state_id
            or self.heldout_state_id
            != _state_observation(TARGET_GROUND_STATE).state_id
            or self.shared_coordinate_values != (3,)
            or self.semantic_labels != ((False,), (True,))
            or self.source_support_cardinalities != (1, 2)
            or self.heldout_support_cardinalities != (1, 2)
            or self.abstract_realizations_equal != (True, True)
            or self.compared_after_target_evidence is not True
            or self.used_to_fill_missing_target_rows is not False
            or self.coordinate_invention_claimed is not False
            or self.statistical_generalization_claimed is not False
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out coordinate-transfer witness overclaims or changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_coordinate_transfer.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "final_epoch_id": self.final_epoch_id,
            "synthesis_result_id": self.synthesis_result_id,
            "source_state_id": self.source_state_id,
            "heldout_state_id": self.heldout_state_id,
            "shared_coordinate_values": list(self.shared_coordinate_values),
            "semantic_labels": [list(item) for item in self.semantic_labels],
            "source_support_cardinalities": list(
                self.source_support_cardinalities
            ),
            "heldout_support_cardinalities": list(
                self.heldout_support_cardinalities
            ),
            "abstract_realizations_equal": list(
                self.abstract_realizations_equal
            ),
            "compared_after_target_evidence": self.compared_after_target_evidence,
            "used_to_fill_missing_target_rows": (
                self.used_to_fill_missing_target_rows
            ),
            "coordinate_invention_claimed": self.coordinate_invention_claimed,
            "statistical_generalization_claimed": (
                self.statistical_generalization_claimed
            ),
        }

    @property
    def transfer_id(self) -> str:
        return _content_id("transfer", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "transfer_id": self.transfer_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureHeldOutH2ResultV1:
    preregistration: ProgramClosureHeldOutH2PreregistrationV1
    synthesis_result_id: str
    catalogue: ProgramClosureHeldOutCatalogueV1
    initial_epoch: ProgramClosureHeldOutEpochV1
    initial_proposal: ProgramClosureHeldOutPlanProposalV1
    initial_selected_audit: ProgramClosureHeldOutSelectedAuditV1
    authorization: ProgramClosureHeldOutEvidenceAuthorizationV1
    evidence_bundle: ProgramClosureHeldOutEvidenceBundleV1
    final_epoch: ProgramClosureHeldOutEpochV1
    final_proposal: ProgramClosureHeldOutPlanProposalV1
    final_selected_audit: ProgramClosureHeldOutSelectedAuditV1
    coordinate_transfer: ProgramClosureHeldOutCoordinateTransferV1
    status: str = SUCCESS_STATUS
    source_synthesis_full_replay_count: int = 1
    target_catalogue_query_count: int = 1
    exact_target_transition_query_count: int = 3
    successor_catalogue_query_count: int = 0
    successor_transition_query_count: int = 0
    candidate_plan_count: int = 8
    candidate_audit_count: int = 8
    independent_selected_audit_count: int = 2
    query_local_model_only: bool = True
    automatic_program_proposal_within_frozen_grammar_claimed: bool = True
    coordinate_invention_claimed: bool = False
    learned_dynamics_claimed: bool = False
    statistical_generalization_claimed: bool = False
    sample_efficiency_claimed: bool = False
    workload_economics_claimed: bool = False
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        exact_types = (
            (
                self.preregistration,
                ProgramClosureHeldOutH2PreregistrationV1,
                "preregistration",
            ),
            (self.catalogue, ProgramClosureHeldOutCatalogueV1, "catalogue"),
            (self.initial_epoch, ProgramClosureHeldOutEpochV1, "initial epoch"),
            (
                self.initial_proposal,
                ProgramClosureHeldOutPlanProposalV1,
                "initial proposal",
            ),
            (
                self.initial_selected_audit,
                ProgramClosureHeldOutSelectedAuditV1,
                "initial selected audit",
            ),
            (
                self.authorization,
                ProgramClosureHeldOutEvidenceAuthorizationV1,
                "authorization",
            ),
            (
                self.evidence_bundle,
                ProgramClosureHeldOutEvidenceBundleV1,
                "evidence bundle",
            ),
            (self.final_epoch, ProgramClosureHeldOutEpochV1, "final epoch"),
            (
                self.final_proposal,
                ProgramClosureHeldOutPlanProposalV1,
                "final proposal",
            ),
            (
                self.final_selected_audit,
                ProgramClosureHeldOutSelectedAuditV1,
                "final selected audit",
            ),
            (
                self.coordinate_transfer,
                ProgramClosureHeldOutCoordinateTransferV1,
                "coordinate transfer",
            ),
        )
        if any(type(value) is not expected for value, expected, _ in exact_types):
            bad = next(
                label
                for value, expected, label in exact_types
                if type(value) is not expected
            )
            raise ProgramClosureHeldOutH2InvariantViolation(
                f"held-out result rejects substituted {bad}"
            )
        _cid(self.synthesis_result_id, "held-out result synthesis")
        initial_bounds = self.initial_selected_audit.audit_result.robust_bounds
        final_audit = self.final_selected_audit.audit_result
        final_bounds = final_audit.robust_bounds
        preregistration_id = self.preregistration.preregistration_id
        target_ground_row_ids = tuple(
            sorted(item.ground_row_id for item in self.catalogue.actions)
        )
        initial_frontier = (
            self.initial_selected_audit.audit_result.failed_proof_frontier
        )
        if (
            self.initial_epoch.epoch_index != 0
            or self.final_epoch.epoch_index != 1
            or self.final_epoch.previous_epoch_id != self.initial_epoch.epoch_id
            or self.catalogue.preregistration_id != preregistration_id
            or self.catalogue.synthesis_result_id != self.synthesis_result_id
            or self.initial_epoch.preregistration_id != preregistration_id
            or self.final_epoch.preregistration_id != preregistration_id
            or self.initial_epoch.synthesis_result_id != self.synthesis_result_id
            or self.final_epoch.synthesis_result_id != self.synthesis_result_id
            or self.initial_epoch.catalogue_id != self.catalogue.catalogue_id
            or self.final_epoch.catalogue_id != self.catalogue.catalogue_id
            or self.initial_epoch.base_partial_model_id
            != self.final_epoch.base_partial_model_id
            or self.initial_epoch.source_state_ids
            != self.preregistration.source_state_ids
            or self.final_epoch.source_state_ids
            != self.preregistration.source_state_ids
            or self.initial_epoch.source_ground_row_ids
            != self.preregistration.source_ground_row_ids
            or self.final_epoch.source_ground_row_ids
            != self.preregistration.source_ground_row_ids
            or self.initial_epoch.source_observed_ground_row_ids
            != self.preregistration.source_observed_ground_row_ids
            or self.final_epoch.source_observed_ground_row_ids
            != self.preregistration.source_observed_ground_row_ids
            or self.initial_epoch.source_missing_ground_row_ids
            != self.preregistration.source_missing_ground_row_ids
            or self.final_epoch.source_missing_ground_row_ids
            != self.preregistration.source_missing_ground_row_ids
            or self.initial_epoch.target_ground_row_ids
            != target_ground_row_ids
            or self.final_epoch.target_ground_row_ids
            != target_ground_row_ids
            or self.initial_proposal.epoch_id != self.initial_epoch.epoch_id
            or self.initial_proposal.planning_view_id
            != self.initial_epoch.planning_view.model_id
            or self.final_proposal.epoch_id != self.final_epoch.epoch_id
            or self.final_proposal.planning_view_id
            != self.final_epoch.planning_view.model_id
            or self.initial_selected_audit.epoch_id
            != self.initial_epoch.epoch_id
            or self.initial_selected_audit.proposal_id
            != self.initial_proposal.proposal_id
            or self.initial_selected_audit.selected_plan_id
            != self.initial_proposal.selected_plan.plan_id
            or self.final_selected_audit.epoch_id != self.final_epoch.epoch_id
            or self.final_selected_audit.proposal_id
            != self.final_proposal.proposal_id
            or self.final_selected_audit.selected_plan_id
            != self.final_proposal.selected_plan.plan_id
            or self.authorization.preregistration_id != preregistration_id
            or self.authorization.synthesis_result_id
            != self.synthesis_result_id
            or self.authorization.initial_epoch_id != self.initial_epoch.epoch_id
            or self.authorization.initial_proposal_id
            != self.initial_proposal.proposal_id
            or self.authorization.initial_selected_audit_id
            != self.initial_selected_audit.audit_id
            or initial_frontier is None
            or self.authorization.failed_frontier_id
            != initial_frontier.frontier_id
            or self.authorization.requested_ground_row_ids
            != target_ground_row_ids
            or self.evidence_bundle.authorization_id
            != self.authorization.authorization_id
            or self.evidence_bundle.kernel_authority_id
            != self.catalogue.kernel_authority_id
            or self.evidence_bundle.requested_ground_row_ids
            != target_ground_row_ids
            or self.final_epoch.evidence_bundle_id != self.evidence_bundle.bundle_id
            or self.final_epoch.target_evidence_ids
            != tuple(
                sorted(
                    item.evidence_id
                    for item in self.evidence_bundle.evidence
                )
            )
            or self.coordinate_transfer.final_epoch_id != self.final_epoch.epoch_id
            or self.coordinate_transfer.synthesis_result_id
            != self.synthesis_result_id
            or self.initial_proposal.thresholds.initial_state_distribution
            != (
                InitialStateMassV1(
                    self.preregistration.query.target_state.state_id,
                    Fraction(1),
                ),
            )
            or self.final_proposal.thresholds.initial_state_distribution
            != self.initial_proposal.thresholds.initial_state_distribution
            or self.initial_proposal.thresholds.reward_weights
            != self.preregistration.query.reward_weights
            or self.final_proposal.thresholds.reward_weights
            != self.preregistration.query.reward_weights
            or self.initial_selected_audit.audit_result.outcome
            is not PartialAuditOutcome.FAILED_PROOF_FRONTIER
            or (
                initial_bounds.policy_reward_lower,
                initial_bounds.policy_reward_upper,
                initial_bounds.policy_failure_lower,
                initial_bounds.policy_failure_upper,
                initial_bounds.unrestricted_reward_upper,
                initial_bounds.normalized_distribution_regret,
                initial_bounds.external_coverage_certified,
            )
            != (
                Fraction(0),
                Fraction(4),
                Fraction(0),
                Fraction(1),
                Fraction(4),
                Fraction(1),
                False,
            )
            or final_audit.outcome is not PartialAuditOutcome.CERTIFIED_FIXED_PLAN
            or final_audit.certificate is None
            or (
                final_bounds.policy_reward_lower,
                final_bounds.policy_reward_upper,
                final_bounds.policy_failure_lower,
                final_bounds.policy_failure_upper,
                final_bounds.unrestricted_reward_upper,
                final_bounds.normalized_distribution_regret,
                final_bounds.external_coverage_certified,
            )
            != (
                Fraction(1),
                Fraction(1),
                Fraction(0),
                Fraction(0),
                Fraction(1),
                Fraction(0),
                True,
            )
            or self.status != SUCCESS_STATUS
            or (
                self.source_synthesis_full_replay_count,
                self.target_catalogue_query_count,
                self.exact_target_transition_query_count,
                self.successor_catalogue_query_count,
                self.successor_transition_query_count,
                self.candidate_plan_count,
                self.candidate_audit_count,
                self.independent_selected_audit_count,
            )
            != (1, 1, 3, 0, 0, 8, 8, 2)
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out result lineage, bounds, or work trace changed"
            )
        if (
            self.query_local_model_only is not True
            or self.automatic_program_proposal_within_frozen_grammar_claimed
            is not True
            or self.coordinate_invention_claimed is not False
            or self.learned_dynamics_claimed is not False
            or self.statistical_generalization_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.workload_economics_claimed is not False
            or self.official_execution_allowed is not False
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out result crossed a locked aggregate claim"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.program_closure_heldout_h2_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration": self.preregistration.to_document(),
            "synthesis_result_id": self.synthesis_result_id,
            "catalogue": self.catalogue.to_document(),
            "initial_epoch": self.initial_epoch.to_document(),
            "initial_proposal": self.initial_proposal.to_document(),
            "initial_selected_audit": self.initial_selected_audit.to_document(),
            "authorization": self.authorization.to_document(),
            "evidence_bundle": self.evidence_bundle.to_document(),
            "final_epoch": self.final_epoch.to_document(),
            "final_proposal": self.final_proposal.to_document(),
            "final_selected_audit": self.final_selected_audit.to_document(),
            "coordinate_transfer": self.coordinate_transfer.to_document(),
            "status": self.status,
            "source_synthesis_full_replay_count": (
                self.source_synthesis_full_replay_count
            ),
            "target_catalogue_query_count": self.target_catalogue_query_count,
            "exact_target_transition_query_count": (
                self.exact_target_transition_query_count
            ),
            "successor_catalogue_query_count": (
                self.successor_catalogue_query_count
            ),
            "successor_transition_query_count": (
                self.successor_transition_query_count
            ),
            "candidate_plan_count": self.candidate_plan_count,
            "candidate_audit_count": self.candidate_audit_count,
            "independent_selected_audit_count": (
                self.independent_selected_audit_count
            ),
            "query_local_model_only": self.query_local_model_only,
            "automatic_program_proposal_within_frozen_grammar_claimed": (
                self.automatic_program_proposal_within_frozen_grammar_claimed
            ),
            "coordinate_invention_claimed": self.coordinate_invention_claimed,
            "learned_dynamics_claimed": self.learned_dynamics_claimed,
            "statistical_generalization_claimed": (
                self.statistical_generalization_claimed
            ),
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "workload_economics_claimed": self.workload_economics_claimed,
            "official_execution_allowed": self.official_execution_allowed,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _validate_source_inputs(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
) -> None:
    if type(observation_log) is not ObservationLogManifestV1:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out protocol rejects substituted observation logs"
        )
    if type(semantics_profile) is not DeterministicObservationProfileV1:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out protocol rejects substituted semantics profiles"
        )
    if type(observation_authority) is not PreregisteredObservationAuthorityV1:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out protocol rejects substituted observation authorities"
        )
    try:
        validate_preregistered_observation_source_graph_v1(
            observation_log,
            semantics_profile,
            observation_authority,
        )
    except ValueError as error:
        raise ProgramClosureHeldOutH2InvariantViolation(str(error)) from error
    row_count = sum(
        len(catalogue.actions)
        for catalogue in observation_log.action_catalogues
    )
    if (
        len(observation_log.states),
        row_count,
        len(observation_log.observations),
        semantics_profile.horizon_cap,
    ) != (8, 11, 7, 6):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out protocol requires the frozen 8/11/7 H2 source graph"
        )


def _source_identity_sets(
    observation_log: ObservationLogManifestV1,
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    state_ids = tuple(item.state_id for item in observation_log.states)
    ground_row_ids = tuple(
        sorted(
            action.ground_row_id
            for catalogue in observation_log.action_catalogues
            for action in catalogue.actions
        )
    )
    observed_row_ids = tuple(
        sorted(item.ground_row_id for item in observation_log.observations)
    )
    missing_row_ids = tuple(
        sorted(set(ground_row_ids) - set(observed_row_ids))
    )
    catalogue_ids = tuple(
        sorted(item.catalogue_id for item in observation_log.action_catalogues)
    )
    observation_ids = tuple(
        sorted(item.observation_id for item in observation_log.observations)
    )
    return (
        state_ids,
        ground_row_ids,
        observed_row_ids,
        missing_row_ids,
        catalogue_ids,
        observation_ids,
    )


def preregister_lmb_program_closure_heldout_h2_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
) -> ProgramClosureHeldOutH2PreregistrationV1:
    """Freeze the held-out query before any program closure or target access."""

    _validate_source_inputs(
        observation_log, semantics_profile, observation_authority
    )
    proof = canonical_lmb_n6_return_bound_proof_v1()
    query = ProgramClosureHeldOutH2QueryV1(
        observation_log.structural_id,
        observation_log.environment_instance_id,
        observation_log.log_id,
        semantics_profile.profile_id,
        observation_authority.authority_id,
        _state_observation(TARGET_GROUND_STATE),
        proof.reward_weights,
        proof.proof_id,
    )
    if (
        proof.structural_id != query.structural_id
        or proof.environment_instance_id != query.environment_instance_id
        or proof.observation_log_id != query.observation_log_id
        or proof.semantics_profile_id != query.semantics_profile_id
        or proof.observation_authority_id != query.observation_authority_id
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out query differs from the registered return-bound authority"
        )
    return ProgramClosureHeldOutH2PreregistrationV1(
        query,
        *_source_identity_sets(observation_log),
    )


def _validate_canonical_kernel(
    kernel: LMBKernel,
    observation_log: ObservationLogManifestV1,
) -> Any:
    if type(kernel) is not LMBKernel:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out acquisition rejects substituted kernels"
        )
    authority = canonical_lmb_query_kernel_authority_v1()
    if (
        observation_log.structural_id != authority.structural_id
        or kernel.tile_types != authority.tile_types
        or kernel.blockers != authority.blockers
        or kernel.type_count != authority.type_count
        or kernel.capacity != authority.capacity
        or kernel.max_layers != authority.max_layers
        or _kernel_source_digest() != authority.implementation_sha256
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out exact-kernel/source authority mismatch"
        )
    return authority


def _target_catalogue(
    preregistration: ProgramClosureHeldOutH2PreregistrationV1,
    synthesis_result_id: str,
    semantics_profile: DeterministicObservationProfileV1,
    authority: Any,
    kernel: LMBKernel,
) -> tuple[
    ProgramClosureHeldOutCatalogueV1,
    TrustedCompleteActionCatalogueV1,
]:
    target_state = preregistration.query.target_state
    actions = tuple(
        CanonicalGroundActionV1(
            target_state.state_id,
            f"tile={action.tile}",
            kernel.tile_types[action.tile],
        )
        for action in kernel.actions(TARGET_GROUND_STATE)
    )
    catalogue = ProgramClosureHeldOutCatalogueV1(
        preregistration.preregistration_id,
        synthesis_result_id,
        authority.authority_id,
        target_state,
        actions,
    )
    trusted = TrustedCompleteActionCatalogueV1(
        target_state.state_id,
        tuple(sorted(actions, key=lambda item: item.action_id)),
        semantics_profile.trusted_observer_id,
    )
    return catalogue, trusted


def _evaluate_selected_coordinates(
    synthesis_result: Any,
    states: Mapping[str, CanonicalStateObservationV1],
    catalogues: Mapping[str, TrustedCompleteActionCatalogueV1],
) -> tuple[dict[str, tuple[int, ...]], dict[str, tuple[bool, ...]]]:
    proposal = synthesis_result.coordinate_proposal
    expression_by_id = {
        item.expression.expression_id: item.expression
        for item in synthesis_result.program_registry.semantic_representatives
    }
    state_values: dict[str, tuple[int, ...]] = {}
    action_labels: dict[str, tuple[bool, ...]] = {}
    for state_id in sorted(states):
        state = states[state_id]
        catalogue = catalogues[state_id]
        if state.planning_kind is PlanningKind.ACTIVE:
            compiled: list[int] = []
            for expression_id in proposal.state_expression_ids:
                value = _eval_expression(
                    expression_by_id[expression_id],
                    state,
                    catalogue,
                    None,
                    synthesis_result.structural_binding,
                )
                if type(value) is bool:
                    compiled.append(int(value))
                elif type(value) is int:
                    compiled.append(value)
                else:
                    raise ProgramClosureHeldOutH2InvariantViolation(
                        "held-out state program produced a nonscalar value"
                    )
            state_values[state_id] = tuple(compiled)
        else:
            state_values[state_id] = ()
        for action in catalogue.actions:
            raw = {
                expression_id: _eval_expression(
                    expression_by_id[expression_id],
                    state,
                    catalogue,
                    action,
                    synthesis_result.structural_binding,
                )
                for expression_id in proposal.action_expression_ids
            }
            labels: list[bool] = []
            for atom in proposal.action_atoms:
                if atom.kind is TypedActionAtomKind.UNIVERSAL_TRUE:
                    labels.append(True)
                elif atom.kind is TypedActionAtomKind.BOOLEAN_IDENTITY:
                    value = raw[atom.source_expression_id]
                    if type(value) is not bool:
                        raise ProgramClosureHeldOutH2InvariantViolation(
                            "held-out boolean atom received a nonboolean value"
                        )
                    labels.append(value)
                else:
                    value = raw[atom.source_expression_id]
                    if type(value) is not int:
                        raise ProgramClosureHeldOutH2InvariantViolation(
                            "held-out integer atom received a noninteger value"
                        )
                    labels.append(Fraction(value) <= atom.threshold)
            action_labels[action.ground_row_id] = tuple(labels)
    return state_values, action_labels


def _view_ledger_id(
    preregistration_id: str,
    synthesis_result_id: str,
    source_ledger_id: str,
    catalogue_id: str,
    evidence_bundle_id: str | None,
    evidence_ids: tuple[str, ...],
) -> str:
    return _content_id(
        "ledger",
        {
            "schema": "acfqp.program_closure_heldout_h2_evidence_ledger.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": preregistration_id,
            "synthesis_result_id": synthesis_result_id,
            "source_evidence_ledger_id": source_ledger_id,
            "catalogue_id": catalogue_id,
            "evidence_bundle_id": evidence_bundle_id,
            "target_evidence_ids": list(evidence_ids),
        },
    )


def _assemble_planning_view(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    preregistration: ProgramClosureHeldOutH2PreregistrationV1,
    synthesis_result: Any,
    catalogue: ProgramClosureHeldOutCatalogueV1,
    trusted_target_catalogue: TrustedCompleteActionCatalogueV1,
    evidence_bundle: ProgramClosureHeldOutEvidenceBundleV1 | None,
) -> PortablePartialRAPMV1:
    base = synthesis_result.partial_build_result.model
    states = {item.state_id: item for item in observation_log.states}
    states[catalogue.state.state_id] = catalogue.state
    catalogues = {
        item.state_id: item for item in observation_log.action_catalogues
    }
    catalogues[trusted_target_catalogue.state_id] = trusted_target_catalogue
    actions = {
        action.ground_row_id: action
        for item in catalogues.values()
        for action in item.actions
    }
    state_values, action_labels = _evaluate_selected_coordinates(
        synthesis_result, states, catalogues
    )

    grouped: dict[
        tuple[PlanningKind, tuple[int, ...]], list[str]
    ] = {}
    for state_id, state in states.items():
        grouped.setdefault(
            (state.planning_kind, state_values[state_id]), []
        ).append(state_id)
    cells = tuple(
        sorted(
            (
                PartialCellV1(tuple(sorted(members)), kind, values)
                for (kind, values), members in grouped.items()
            ),
            key=lambda item: item.cell_id,
        )
    )
    cell_by_state = {
        state_id: cell
        for cell in cells
        for state_id in cell.member_state_ids
    }
    active_cell_ids = tuple(
        sorted(
            item.cell_id
            for item in cells
            if item.planning_kind is PlanningKind.ACTIVE
        )
    )
    destinations = tuple(
        sorted((*active_cell_ids, base.external_boundary_id))
    )
    source_observations = {
        item.ground_row_id: item for item in observation_log.observations
    }
    target_evidence = (
        {}
        if evidence_bundle is None
        else {item.ground_row_id: item for item in evidence_bundle.evidence}
    )

    ground_rows: list[PartialGroundRowV1] = []
    ground_by_id: dict[str, PartialGroundRowV1] = {}
    for ground_row_id in sorted(actions):
        action = actions[ground_row_id]
        observed = target_evidence.get(ground_row_id)
        source_observed = source_observations.get(ground_row_id)
        if observed is None and source_observed is None:
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
                ground_row_id,
                action.state_id,
                action.action_id,
                AmbiguityRowStatus.MISSING_VACUOUS,
                (),
                ambiguity,
            )
        else:
            evidence = observed if observed is not None else source_observed
            terminal = evidence.terminal
            if observed is not None:
                successor_id = observed.successor_state.state_id
                evidence_id = observed.evidence_id
            else:
                successor_id = source_observed.successor.reference
                evidence_id = source_observed.observation_id
            known_successor: dict[str, Fraction] = {}
            if not terminal:
                destination = (
                    cell_by_state[successor_id].cell_id
                    if successor_id in cell_by_state
                    else base.external_boundary_id
                )
                known_successor[destination] = Fraction(1)
            ambiguity = _ambiguity_payload(
                known_reward=dict(evidence.reward_features),
                known_successor=known_successor,
                known_failure=Fraction(int(evidence.failure)),
                known_terminal=Fraction(int(terminal)),
                unknown_mass=Fraction(0),
                destinations=destinations,
                external_boundary_id=base.external_boundary_id,
                caps=semantics_profile.reward_feature_caps,
            )
            row = PartialGroundRowV1(
                ground_row_id,
                action.state_id,
                action.action_id,
                AmbiguityRowStatus.OBSERVED_SINGLETON,
                (evidence_id,),
                ambiguity,
            )
        ground_rows.append(row)
        ground_by_id[ground_row_id] = row

    semantic_actions: list[PartialSemanticActionV1] = []
    concretizers: list[ConcretizerRowV1] = []
    realizations: list[PartialSemanticRealizationV1] = []
    for cell in cells:
        if cell.planning_kind is not PlanningKind.ACTIVE:
            continue
        actions_by_state_label: dict[
            str, dict[tuple[bool, ...], list[CanonicalGroundActionV1]]
        ] = {}
        common_labels: set[tuple[bool, ...]] | None = None
        for state_id in cell.member_state_ids:
            by_label: dict[
                tuple[bool, ...], list[CanonicalGroundActionV1]
            ] = {}
            for action in catalogues[state_id].actions:
                by_label.setdefault(
                    action_labels[action.ground_row_id], []
                ).append(action)
            actions_by_state_label[state_id] = by_label
            labels = set(by_label)
            common_labels = (
                labels
                if common_labels is None
                else common_labels & labels
            )
        if (
            not common_labels
            or any(
                set(actions_by_state_label[state_id]) != common_labels
                for state_id in cell.member_state_ids
            )
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "selected coordinate aliases states with unequal action labels"
            )
        for label in sorted(common_labels):
            semantic = PartialSemanticActionV1(cell.cell_id, label)
            semantic_actions.append(semantic)
            for state_id in cell.member_state_ids:
                support_actions = tuple(
                    sorted(
                        actions_by_state_label[state_id][label],
                        key=lambda item: item.action_id,
                    )
                )
                weight = Fraction(1, len(support_actions))
                concretizers.append(
                    ConcretizerRowV1(
                        state_id,
                        cell.cell_id,
                        semantic.semantic_action_id,
                        tuple(
                            (item.action_id, weight)
                            for item in support_actions
                        ),
                    )
                )
                support_rows = tuple(
                    ground_by_id[item.ground_row_id]
                    for item in support_actions
                )
                observed_ids = tuple(
                    sorted(
                        item.ground_row_id
                        for item in support_rows
                        if item.status
                        is AmbiguityRowStatus.OBSERVED_SINGLETON
                    )
                )
                missing_ids = tuple(
                    sorted(
                        item.ground_row_id
                        for item in support_rows
                        if item.status
                        is AmbiguityRowStatus.MISSING_VACUOUS
                    )
                )
                known_reward: dict[str, Fraction] = {}
                known_successor: dict[str, Fraction] = {}
                known_failure = Fraction(0)
                known_terminal = Fraction(0)
                for row in support_rows:
                    if (
                        row.status
                        is not AmbiguityRowStatus.OBSERVED_SINGLETON
                    ):
                        continue
                    for name, value in row.ambiguity.known_reward_features:
                        known_reward[name] = (
                            known_reward.get(name, Fraction(0))
                            + weight * value
                        )
                    for destination, mass in (
                        row.ambiguity.known_successor_masses
                    ):
                        known_successor[destination] = (
                            known_successor.get(destination, Fraction(0))
                            + weight * mass
                        )
                    known_failure += (
                        weight * row.ambiguity.known_failure_mass
                    )
                    known_terminal += (
                        weight * row.ambiguity.known_terminal_mass
                    )
                realizations.append(
                    PartialSemanticRealizationV1(
                        state_id,
                        cell.cell_id,
                        semantic.semantic_action_id,
                        tuple(
                            sorted(
                                item.ground_row_id for item in support_rows
                            )
                        ),
                        observed_ids,
                        missing_ids,
                        _ambiguity_payload(
                            known_reward=known_reward,
                            known_successor=known_successor,
                            known_failure=known_failure,
                            known_terminal=known_terminal,
                            unknown_mass=Fraction(
                                len(missing_ids), len(support_rows)
                            ),
                            destinations=destinations,
                            external_boundary_id=base.external_boundary_id,
                            caps=semantics_profile.reward_feature_caps,
                        ),
                    )
                )

    ground_rows_tuple = tuple(ground_rows)
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
    evidence_ids = (
        ()
        if evidence_bundle is None
        else tuple(sorted(item.evidence_id for item in evidence_bundle.evidence))
    )
    evidence_bundle_id = (
        None if evidence_bundle is None else evidence_bundle.bundle_id
    )
    return PortablePartialRAPMV1(
        semantics_profile.profile_id,
        semantics_profile.horizon_cap,
        observation_log.log_id,
        synthesis_result.coordinate_proposal.proposal_id,
        observation_authority.authority_id,
        observation_authority.acquisition_manifest.manifest_id,
        coverage.coverage_id,
        _view_ledger_id(
            preregistration.preregistration_id,
            synthesis_result.result_id,
            observation_log.evidence_ledger.ledger_id,
            catalogue.catalogue_id,
            evidence_bundle_id,
            evidence_ids,
        ),
        coverage,
        base.external_boundary_id,
        cells,
        tuple(
            sorted(
                semantic_actions,
                key=lambda item: item.semantic_action_id,
            )
        ),
        tuple(
            sorted(
                concretizers,
                key=lambda item: (item.state_id, item.semantic_action_id),
            )
        ),
        ground_rows_tuple,
        tuple(
            sorted(
                realizations,
                key=lambda item: (item.state_id, item.semantic_action_id),
            )
        ),
        semantics_profile.reward_feature_caps,
    )


def _epoch(
    epoch_index: int,
    preregistration: ProgramClosureHeldOutH2PreregistrationV1,
    synthesis_result: Any,
    catalogue: ProgramClosureHeldOutCatalogueV1,
    planning_view: PortablePartialRAPMV1,
    evidence_bundle: ProgramClosureHeldOutEvidenceBundleV1 | None,
    previous_epoch_id: str | None,
    target_action_labels: tuple[tuple[bool, ...], ...],
) -> ProgramClosureHeldOutEpochV1:
    target_ground_row_ids = tuple(
        sorted(item.ground_row_id for item in catalogue.actions)
    )
    target_evidence_ids = (
        ()
        if evidence_bundle is None
        else tuple(
            sorted(item.evidence_id for item in evidence_bundle.evidence)
        )
    )
    return ProgramClosureHeldOutEpochV1(
        epoch_index,
        "INITIAL" if epoch_index == 0 else "FINAL",
        preregistration.preregistration_id,
        synthesis_result.result_id,
        synthesis_result.partial_build_result.model.model_id,
        previous_epoch_id,
        catalogue.catalogue_id,
        None if evidence_bundle is None else evidence_bundle.bundle_id,
        planning_view,
        preregistration.source_state_ids,
        preregistration.source_ground_row_ids,
        preregistration.source_observed_ground_row_ids,
        preregistration.source_missing_ground_row_ids,
        preregistration.query.target_state.state_id,
        target_ground_row_ids,
        target_evidence_ids,
        len(planning_view.coverage.observed_ground_row_ids),
        len(planning_view.coverage.missing_ground_row_ids),
        (3,),
        target_action_labels,
        0 if evidence_bundle is None else 3,
    )


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
    raise ProgramClosureHeldOutH2InvariantViolation(
        "held-out planner received an inapplicable selection mode"
    )


def _semantic_plan_key(
    model: PortablePartialRAPMV1,
    plan: FrozenContingentAbstractPlanV1,
) -> tuple[int, ...]:
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
            key=lambda cell: (
                cell.coordinate_values,
                cell.member_state_ids,
            ),
        )
    )
    result: list[int] = []
    for stage in plan.stages:
        assignment_by_cell = {
            item.cell_id: item.semantic_action_id
            for item in stage.assignments
        }
        if set(assignment_by_cell) != set(ordered_cell_ids):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out semantic tie-break received an incomplete stage"
            )
        for cell_id in ordered_cell_ids:
            action = action_by_id[assignment_by_cell[cell_id]]
            if action.cell_id != cell_id:
                raise ProgramClosureHeldOutH2InvariantViolation(
                    "held-out semantic tie-break action/cell mismatch"
                )
            result.extend(int(value) for value in action.label_values)
    return tuple(result)


def _thresholds(
    preregistration: ProgramClosureHeldOutH2PreregistrationV1,
    planning_view: PortablePartialRAPMV1,
) -> FrozenPartialAuditThresholdsV1:
    query = preregistration.query
    proof = canonical_lmb_n6_return_bound_proof_v1()
    if (
        query.return_bound_proof_id != proof.proof_id
        or query.reward_weights != proof.reward_weights
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out threshold authority differs from preregistration"
        )
    return FrozenPartialAuditThresholdsV1(
        planning_view.model_id,
        query.horizon,
        (InitialStateMassV1(query.target_state.state_id, Fraction(1)),),
        query.reward_weights,
        query.normalized_regret_tolerance,
        query.risk_tolerance,
        proof,
    )


def _propose(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    preregistration: ProgramClosureHeldOutH2PreregistrationV1,
    epoch: ProgramClosureHeldOutEpochV1,
) -> ProgramClosureHeldOutPlanProposalV1:
    model = epoch.planning_view
    thresholds = _thresholds(preregistration, model)
    _, domains = _planner_context(
        observation_log,
        semantics_profile,
        observation_authority,
        model,
        thresholds,
    )
    assignments = _stage_assignments(domains)
    per_stage_count = 1
    for domain in domains:
        per_stage_count *= len(domain.semantic_action_ids)
    candidate_count = per_stage_count**thresholds.horizon
    if (
        candidate_count > PRODUCTION_CANDIDATE_CAP
        or (per_stage_count, candidate_count) != (2, 4)
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out complete H2 plan enumeration changed"
        )
    plans: dict[str, FrozenContingentAbstractPlanV1] = {}
    summaries: list[PartialPlannerCandidateSummaryV1] = []
    for schedule in product(assignments, repeat=thresholds.horizon):
        plan = FrozenContingentAbstractPlanV1(
            model.model_id,
            thresholds.horizon,
            tuple(
                ContingentPlanStageV1(time_index, stage)
                for time_index, stage in enumerate(schedule)
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
    candidate_summaries = tuple(
        sorted(summaries, key=lambda item: item.contingent_plan_id)
    )
    mode, provisional = _selected_summary(candidate_summaries)
    numeric_key = _selection_numeric_key(mode, provisional)
    tied = tuple(
        item
        for item in candidate_summaries
        if _selection_numeric_key(mode, item) == numeric_key
    )
    selected_summary = min(
        tied,
        key=lambda item: (
            _semantic_plan_key(
                model, plans[item.contingent_plan_id]
            ),
            item.contingent_plan_id,
        ),
    )
    selected_plan = plans[selected_summary.contingent_plan_id]
    return ProgramClosureHeldOutPlanProposalV1(
        epoch.epoch_id,
        model.model_id,
        thresholds,
        domains,
        candidate_summaries,
        mode,
        selected_plan,
        _semantic_plan_key(model, selected_plan),
    )


def _independent_selected_audit(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    epoch: ProgramClosureHeldOutEpochV1,
    proposal: ProgramClosureHeldOutPlanProposalV1,
) -> ProgramClosureHeldOutSelectedAuditV1:
    audit = _audit_verified_partial_model_v1(
        epoch.planning_view,
        observation_log,
        semantics_profile,
        observation_authority,
        proposal.thresholds,
        proposal.selected_plan,
    )
    return ProgramClosureHeldOutSelectedAuditV1(
        epoch.epoch_id,
        epoch.planning_view.model_id,
        proposal.proposal_id,
        proposal.selected_plan.plan_id,
        audit,
    )


def _authorize_target_rows(
    preregistration: ProgramClosureHeldOutH2PreregistrationV1,
    synthesis_result: Any,
    catalogue: ProgramClosureHeldOutCatalogueV1,
    initial_epoch: ProgramClosureHeldOutEpochV1,
    initial_proposal: ProgramClosureHeldOutPlanProposalV1,
    initial_audit: ProgramClosureHeldOutSelectedAuditV1,
) -> ProgramClosureHeldOutEvidenceAuthorizationV1:
    audit = initial_audit.audit_result
    frontier = audit.failed_proof_frontier
    if (
        audit.outcome is not PartialAuditOutcome.FAILED_PROOF_FRONTIER
        or frontier is None
        or frontier.reason is not FailedProofReason.EXTERNAL_COVERAGE_ESCAPE
        or frontier.earliest_time_index != 0
        or frontier.remaining_horizon != HORIZON
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "target evidence requires the frozen initial failed-proof frontier"
        )
    target_state_id = preregistration.query.target_state.state_id
    target_cell = next(
        item
        for item in initial_epoch.planning_view.cells
        if target_state_id in item.member_state_ids
    )
    stage_zero = initial_proposal.selected_plan.stages[0]
    selected_semantic_action_id = next(
        item.semantic_action_id
        for item in stage_zero.assignments
        if item.cell_id == target_cell.cell_id
    )
    concretizer = next(
        item
        for item in initial_epoch.planning_view.concretizer_rows
        if item.state_id == target_state_id
        and item.semantic_action_id == selected_semantic_action_id
    )
    selected_action_ids = {item[0] for item in concretizer.support}
    row_by_action_id = {
        item.action_id: item.ground_row_id for item in catalogue.actions
    }
    selected_risk_rows = {
        row_by_action_id[action_id] for action_id in selected_action_ids
    }
    if len(selected_risk_rows) != 1:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "initial selected plan no longer has one target risk-support row"
        )
    requested = tuple(
        sorted(item.ground_row_id for item in catalogue.actions)
    )
    action_by_row = {
        item.ground_row_id: item for item in catalogue.actions
    }
    causes = tuple(
        ProgramClosureHeldOutRowCauseV1(
            row_id,
            action_by_row[row_id].action_id,
            row_id in selected_risk_rows,
            True,
        )
        for row_id in requested
    )
    return ProgramClosureHeldOutEvidenceAuthorizationV1(
        preregistration.preregistration_id,
        synthesis_result.result_id,
        initial_epoch.epoch_id,
        initial_proposal.proposal_id,
        initial_audit.audit_id,
        frontier.frontier_id,
        target_state_id,
        requested,
        causes,
        1,
        3,
        3,
    )


def _acquire_target_rows(
    authorization: ProgramClosureHeldOutEvidenceAuthorizationV1,
    catalogue: ProgramClosureHeldOutCatalogueV1,
    kernel_authority: Any,
    kernel: LMBKernel,
) -> ProgramClosureHeldOutEvidenceBundleV1:
    action_by_row = {
        item.ground_row_id: item for item in catalogue.actions
    }
    if set(authorization.requested_ground_row_ids) != set(action_by_row):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "target acquisition request differs from the frozen catalogue"
        )
    evidence: list[ProgramClosureHeldOutTransitionEvidenceV1] = []
    for sequence, row_id in enumerate(
        authorization.requested_ground_row_ids, start=1
    ):
        action = action_by_row[row_id]
        outcomes = kernel.step(
            TARGET_GROUND_STATE, LMBAction(_tile(action))
        )
        if (
            type(outcomes) is not tuple
            or len(outcomes) != 1
            or outcomes[0].probability != 1
        ):
            raise ProgramClosureHeldOutH2InvariantViolation(
                "held-out profile requires deterministic singleton rows"
            )
        outcome = outcomes[0]
        evidence.append(
            ProgramClosureHeldOutTransitionEvidenceV1(
                sequence,
                authorization.authorization_id,
                kernel_authority.authority_id,
                row_id,
                catalogue.state.state_id,
                action.action_id,
                _state_observation(outcome.next_state),
                outcome.reward_features,
                outcome.failure,
                outcome.terminal,
            )
        )
    return ProgramClosureHeldOutEvidenceBundleV1(
        authorization.authorization_id,
        kernel_authority.authority_id,
        authorization.requested_ground_row_ids,
        tuple(evidence),
    )


def _coordinate_transfer(
    synthesis_result: Any,
    final_epoch: ProgramClosureHeldOutEpochV1,
) -> ProgramClosureHeldOutCoordinateTransferV1:
    model = final_epoch.planning_view
    source_state_id = _state_observation(
        SOURCE_REFERENCE_GROUND_STATE
    ).state_id
    target_state_id = _state_observation(TARGET_GROUND_STATE).state_id
    source_cell = next(
        item for item in model.cells if source_state_id in item.member_state_ids
    )
    target_cell = next(
        item for item in model.cells if target_state_id in item.member_state_ids
    )
    if (
        source_cell.cell_id != target_cell.cell_id
        or source_cell.coordinate_values != (3,)
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out target did not transfer into the expected source cell"
        )
    actions = tuple(
        sorted(
            (
                item
                for item in model.semantic_actions
                if item.cell_id == source_cell.cell_id
            ),
            key=lambda item: item.label_values,
        )
    )
    if tuple(item.label_values for item in actions) != (
        (False,),
        (True,),
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out source/target semantic labels changed"
        )
    realization_by_pair = {
        (item.state_id, item.semantic_action_id): item
        for item in model.semantic_realizations
    }
    source_cardinalities: list[int] = []
    target_cardinalities: list[int] = []
    equal: list[bool] = []
    for action in actions:
        source = realization_by_pair[
            (source_state_id, action.semantic_action_id)
        ]
        target = realization_by_pair[
            (target_state_id, action.semantic_action_id)
        ]
        source_cardinalities.append(len(source.support_ground_row_ids))
        target_cardinalities.append(len(target.support_ground_row_ids))
        equal.append(
            source.ambiguity.to_document()
            == target.ambiguity.to_document()
        )
    successor_state_id = _state_observation(
        SOURCE_SUCCESSOR_GROUND_STATE
    ).state_id
    if successor_state_id not in final_epoch.source_state_ids:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out nonterminal continuation was not present in source"
        )
    return ProgramClosureHeldOutCoordinateTransferV1(
        final_epoch.epoch_id,
        synthesis_result.result_id,
        source_state_id,
        target_state_id,
        source_cell.coordinate_values,
        tuple(item.label_values for item in actions),
        tuple(source_cardinalities),
        tuple(target_cardinalities),
        tuple(equal),
    )


def _implementation_digest(functions: tuple[Any, ...]) -> str:
    return hashlib.sha256(
        "\n\x00\n".join(
            inspect.getsource(function) for function in functions
        ).encode("utf-8")
    ).hexdigest()


def _heldout_implementation_functions() -> tuple[Any, ...]:
    return (
        _validate_source_inputs,
        _source_identity_sets,
        _validate_canonical_kernel,
        _target_catalogue,
        _evaluate_selected_coordinates,
        _view_ledger_id,
        _assemble_planning_view,
        _epoch,
        _selection_numeric_key,
        _semantic_plan_key,
        _thresholds,
        _propose,
        _independent_selected_audit,
        _authorize_target_rows,
        _acquire_target_rows,
        _coordinate_transfer,
    )


def _validate_heldout_implementation_authority() -> None:
    if (
        _implementation_digest(_heldout_implementation_functions())
        != HELDOUT_IMPLEMENTATION_SHA256
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "runtime held-out H2 implementation differs from frozen authority"
        )


def run_lmb_program_closure_heldout_h2_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    preregistration: ProgramClosureHeldOutH2PreregistrationV1,
    synthesis_result: Any,
    kernel: LMBKernel,
) -> ProgramClosureHeldOutH2ResultV1:
    """Run the preregistered certificate-triggered held-out H2 recovery."""

    _validate_heldout_implementation_authority()
    _validate_source_inputs(
        observation_log, semantics_profile, observation_authority
    )
    if type(preregistration) is not ProgramClosureHeldOutH2PreregistrationV1:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out runner rejects substituted preregistrations"
        )
    expected_preregistration = (
        preregister_lmb_program_closure_heldout_h2_v1(
            observation_log, semantics_profile, observation_authority
        )
    )
    if (
        preregistration.to_document()
        != expected_preregistration.to_document()
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out preregistration differs from pre-synthesis replay"
        )

    closure_module = importlib.import_module(
        "acfqp.observed_program_closure_synthesis_v1"
    )
    if type(synthesis_result) is not closure_module.ObservedProgramClosureResultV1:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out runner rejects substituted program-closure results"
        )
    synthesis_failures = (
        closure_module.verify_observed_lmb_program_closure_partial_rapm_v1(
            observation_log,
            semantics_profile,
            observation_authority,
            synthesis_result,
        )
    )
    if synthesis_failures:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "program closure failed full retained replay: "
            + ",".join(synthesis_failures)
        )
    if (
        synthesis_result.certificate.plan_certificate_claimed is not False
        or synthesis_result.certificate.held_out_generalization_claimed
        is not False
        or synthesis_result.partial_build_result.model.coverage.registered_state_ids
        != preregistration.source_state_ids
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "source closure crossed its source-only claim boundary"
        )

    kernel_authority = _validate_canonical_kernel(
        kernel, observation_log
    )
    catalogue, trusted_target_catalogue = _target_catalogue(
        preregistration,
        synthesis_result.result_id,
        semantics_profile,
        kernel_authority,
        kernel,
    )
    states = {item.state_id: item for item in observation_log.states}
    states[catalogue.state.state_id] = catalogue.state
    catalogues = {
        item.state_id: item for item in observation_log.action_catalogues
    }
    catalogues[trusted_target_catalogue.state_id] = trusted_target_catalogue
    state_values, action_labels = _evaluate_selected_coordinates(
        synthesis_result, states, catalogues
    )
    target_action_labels = tuple(
        action_labels[item.ground_row_id] for item in catalogue.actions
    )
    if (
        state_values[catalogue.state.state_id] != (3,)
        or target_action_labels != ((False,), (True,), (True,))
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "automatically selected program changed its held-out coordinates"
        )

    initial_view = _assemble_planning_view(
        observation_log,
        semantics_profile,
        observation_authority,
        preregistration,
        synthesis_result,
        catalogue,
        trusted_target_catalogue,
        None,
    )
    initial_epoch = _epoch(
        0,
        preregistration,
        synthesis_result,
        catalogue,
        initial_view,
        None,
        None,
        target_action_labels,
    )
    initial_proposal = _propose(
        observation_log,
        semantics_profile,
        observation_authority,
        preregistration,
        initial_epoch,
    )
    initial_selected_audit = _independent_selected_audit(
        observation_log,
        semantics_profile,
        observation_authority,
        initial_epoch,
        initial_proposal,
    )
    authorization = _authorize_target_rows(
        preregistration,
        synthesis_result,
        catalogue,
        initial_epoch,
        initial_proposal,
        initial_selected_audit,
    )
    evidence_bundle = _acquire_target_rows(
        authorization,
        catalogue,
        kernel_authority,
        kernel,
    )
    final_view = _assemble_planning_view(
        observation_log,
        semantics_profile,
        observation_authority,
        preregistration,
        synthesis_result,
        catalogue,
        trusted_target_catalogue,
        evidence_bundle,
    )
    final_epoch = _epoch(
        1,
        preregistration,
        synthesis_result,
        catalogue,
        final_view,
        evidence_bundle,
        initial_epoch.epoch_id,
        target_action_labels,
    )
    final_proposal = _propose(
        observation_log,
        semantics_profile,
        observation_authority,
        preregistration,
        final_epoch,
    )
    final_selected_audit = _independent_selected_audit(
        observation_log,
        semantics_profile,
        observation_authority,
        final_epoch,
        final_proposal,
    )
    if (
        final_selected_audit.audit_result.outcome
        is not PartialAuditOutcome.CERTIFIED_FIXED_PLAN
        or final_selected_audit.audit_result.certificate is None
    ):
        raise ProgramClosureHeldOutH2InvariantViolation(
            "three authorized rows did not close the held-out H2 proof"
        )
    transfer = _coordinate_transfer(synthesis_result, final_epoch)
    return ProgramClosureHeldOutH2ResultV1(
        preregistration,
        synthesis_result.result_id,
        catalogue,
        initial_epoch,
        initial_proposal,
        initial_selected_audit,
        authorization,
        evidence_bundle,
        final_epoch,
        final_proposal,
        final_selected_audit,
        transfer,
    )


def _validate_claimed_runtime_shape(
    claimed: Any,
    expected: Any,
    path: str,
) -> None:
    if type(claimed) is not type(expected):
        raise ProgramClosureHeldOutH2InvariantViolation(
            f"{path} contains a nested runtime-type substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise ProgramClosureHeldOutH2InvariantViolation(
                f"{path} tuple shape differs from replay"
            )
        for index, (claimed_item, expected_item) in enumerate(
            zip(claimed, expected)
        ):
            _validate_claimed_runtime_shape(
                claimed_item, expected_item, f"{path}[{index}]"
            )
        return
    if is_dataclass(expected):
        for field in fields(type(expected)):
            _validate_claimed_runtime_shape(
                object.__getattribute__(claimed, field.name),
                object.__getattribute__(expected, field.name),
                f"{path}.{field.name}",
            )


def verify_lmb_program_closure_heldout_h2_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    preregistration: ProgramClosureHeldOutH2PreregistrationV1,
    synthesis_result: Any,
    kernel: LMBKernel,
    claimed_result: ProgramClosureHeldOutH2ResultV1,
) -> tuple[str, ...]:
    """Replay synthesis, chronology, exact rows, both epochs and both audits."""

    if type(claimed_result) is not ProgramClosureHeldOutH2ResultV1:
        raise ProgramClosureHeldOutH2InvariantViolation(
            "held-out verifier rejects substituted results"
        )
    expected = run_lmb_program_closure_heldout_h2_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        preregistration,
        synthesis_result,
        kernel,
    )
    _validate_claimed_runtime_shape(
        claimed_result, expected, "claimed held-out result"
    )
    failures: list[str] = []
    if claimed_result.initial_epoch.epoch_id != expected.initial_epoch.epoch_id:
        failures.append("INITIAL_EPOCH_RECONSTRUCTION_MISMATCH")
    if (
        claimed_result.authorization.authorization_id
        != expected.authorization.authorization_id
    ):
        failures.append("AUTHORIZATION_RECONSTRUCTION_MISMATCH")
    if (
        claimed_result.evidence_bundle.bundle_id
        != expected.evidence_bundle.bundle_id
    ):
        failures.append("EVIDENCE_RECONSTRUCTION_MISMATCH")
    if claimed_result.final_epoch.epoch_id != expected.final_epoch.epoch_id:
        failures.append("FINAL_EPOCH_RECONSTRUCTION_MISMATCH")
    if (
        claimed_result.final_selected_audit.audit_id
        != expected.final_selected_audit.audit_id
    ):
        failures.append("FINAL_CERTIFICATE_RECONSTRUCTION_MISMATCH")
    if claimed_result.to_document() != expected.to_document():
        failures.append("RESULT_RECONSTRUCTION_MISMATCH")
    return tuple(failures)


__all__ = [
    "HELDOUT_IMPLEMENTATION_SHA256",
    "PROFILE_KEY",
    "ProgramClosureHeldOutCatalogueV1",
    "ProgramClosureHeldOutCoordinateTransferV1",
    "ProgramClosureHeldOutEpochV1",
    "ProgramClosureHeldOutEvidenceAuthorizationV1",
    "ProgramClosureHeldOutEvidenceBundleV1",
    "ProgramClosureHeldOutH2InvariantViolation",
    "ProgramClosureHeldOutH2PreregistrationV1",
    "ProgramClosureHeldOutH2QueryV1",
    "ProgramClosureHeldOutH2ResultV1",
    "ProgramClosureHeldOutPlanProposalV1",
    "ProgramClosureHeldOutRowCauseV1",
    "ProgramClosureHeldOutSelectedAuditV1",
    "ProgramClosureHeldOutTransitionEvidenceV1",
    "SUCCESS_STATUS",
    "TARGET_GROUND_STATE",
    "preregister_lmb_program_closure_heldout_h2_v1",
    "run_lmb_program_closure_heldout_h2_v1",
    "verify_lmb_program_closure_heldout_h2_v1",
]
