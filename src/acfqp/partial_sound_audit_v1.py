"""Robust fixed-plan auditing over a query-neutral partial RAPM.

The legacy boundary reconstructs a ``PortablePartialRAPMV1`` from the complete
manual V0-042 source graph.  The typed boundary first replays a complete V0-045
synthesis result.  Each then accepts frozen query thresholds and one
deterministic finite-horizon contingent abstract plan.  Neither receives a
transition API, ground planner, or ground feasibility oracle.  A positive
claim is conditional on the retained observation authority; this module does
not search for a policy or prove optimality or infeasibility.

The V0-042 ambiguity contract is a *joint* simplex.  Consequently each Bellman
row charges ``unknown_atom_mass_sum`` exactly once.  Destination marginal
intervals are useful for upper-reachability only and are never summed as if
their upper endpoints were independent probability mass.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

import acfqp.observed_typed_coordinate_synthesis_v1 as observed_synthesis_v1
from acfqp.observation_partial_rapm_v1 import (
    AmbiguityPayloadV1,
    DeterministicObservationProfileV1,
    FrozenCoordinateProposalV1,
    JointOutcomeKind,
    ObservationLogManifestV1,
    ObservationPartialRAPMInvariantViolation,
    ObservationPartialRAPMBuildV1,
    PREREGISTERED_OBSERVATION_AUTHORITY_IDS,
    PartialCellV1,
    PartialSemanticActionV1,
    PartialSemanticRealizationV1,
    PlanningKind,
    PreregisteredObservationAuthorityV1,
    PortablePartialRAPMV1,
    verify_observation_partial_rapm_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.1.0"
TYPED_AUDIT_SCHEMA_VERSION = "1.2.0"
PROFILE_KEY = "partial_fixed_plan_robust_audit_v0"
ROBUST_BELLMAN_FORMULA_ID = "partial-joint-simplex-fixed-plan-bellman-v1"
UNRESTRICTED_UPPER_FORMULA_ID = "partial-joint-simplex-unrestricted-ground-upper-v1"
RETURN_BOUND_FORMULA_ID = "canonical-lmb-n6-return-upper-v1"

CANONICAL_LMB_N6_STRUCTURAL_ID = (
    "eb4d4562d979fe6312fe8c7876176b6a8c6e99ee859e5da67e53ea2fac7a76e8"
)
CANONICAL_LMB_N6_OBSERVATION_LOG_ID = (
    "1f8e3bd433f5aa55fb4a4edc70079bb023e954d07c6d1ff02be4b11e59a8af9a"
)
CANONICAL_LMB_N6_SEMANTICS_PROFILE_ID = (
    "be95884e6abf81edd59130eb2d4439cca74349ccbdce7090aeff937c9a9d6abb"
)
CANONICAL_LMB_N6_OBSERVATION_AUTHORITY_ID = (
    "5aac3e8f1e7b8b2af4cafe50a8b54c25c21008d2b9fccd4aaaeebc3ab79df825"
)
CANONICAL_LMB_N6_ENVIRONMENT_INSTANCE_ID = (
    "abd7d1dfe9dc4acffa009555c86e7d306bf74e90322ea7a7453fa07a186e7749"
)
CANONICAL_LMB_N6_ACQUISITION_MANIFEST_ID = (
    "5e6e6b71d1e479e193189eb1ce6dc8896329e2ce35fcb2c9282b3b2d7fc279e4"
)
REGISTERED_NORMALIZED_REGRET_TOLERANCES = frozenset(
    (Fraction(0), Fraction(1, 20))
)
REGISTERED_RISK_TOLERANCES = frozenset(
    (Fraction(0), Fraction(1, 20), Fraction(1, 10))
)

DOMAIN_TAGS = {
    "thresholds": "acfqp:partial-audit-thresholds:v1",
    "return_bound_proof": "acfqp:registered-return-bound-proof:v1",
    "support_point_regret": "acfqp:initial-support-point-regret:v1",
    "assignment": "acfqp:partial-contingent-plan-assignment:v1",
    "stage": "acfqp:partial-contingent-plan-stage:v1",
    "plan": "acfqp:frozen-partial-contingent-plan:v1",
    "obligation": "acfqp:partial-state-action-time-obligation:v1",
    "unrestricted_row": "acfqp:partial-unrestricted-ground-upper-row:v1",
    "bound_row": "acfqp:partial-fixed-plan-bound-row:v1",
    "bounds": "acfqp:partial-fixed-plan-robust-bounds:v1",
    "certificate": "acfqp:partial-fixed-plan-certificate:v1",
    "frontier": "acfqp:partial-failed-proof-frontier:v1",
    "result": "acfqp:partial-sound-audit-result:v1",
    "typed_result": "acfqp:typed-partial-sound-audit-result:v2",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("partial-audit content domains must be unique")


class PartialSoundAuditInvariantViolation(ValueError):
    """A partial audit input, proof row, or identity binding is invalid."""


class PartialAuditOutcome(str, Enum):
    CERTIFIED_FIXED_PLAN = "CERTIFIED_FIXED_PLAN"
    FAILED_PROOF_FRONTIER = "FAILED_PROOF_FRONTIER"


class FailedProofReason(str, Enum):
    UNRESOLVED_POLICY_PATH_DISTINCTION = "UNRESOLVED_POLICY_PATH_DISTINCTION"
    KNOWN_FIXED_PLAN_THRESHOLD_FAILURE = "KNOWN_FIXED_PLAN_THRESHOLD_FAILURE"
    EXTERNAL_COVERAGE_ESCAPE = "EXTERNAL_COVERAGE_ESCAPE"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, ValueError) as error:
        raise PartialSoundAuditInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PartialSoundAuditInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fraction(value: Any, field: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise PartialSoundAuditInvariantViolation(f"{field} must be exact")
    return Fraction(value)


def _fraction_document(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise PartialSoundAuditInvariantViolation(
            f"{field} must be an integer >= {minimum}"
        )
    return value


def _sorted_ids(values: Iterable[str], field: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise PartialSoundAuditInvariantViolation(
            f"{field} must be an exact tuple"
        )
    if any(type(value) is not str for value in values):
        raise PartialSoundAuditInvariantViolation(
            f"{field} rejects nested duck IDs before canonical access"
        )
    if values != tuple(sorted(set(values))):
        raise PartialSoundAuditInvariantViolation(
            f"{field} must be unique and sorted"
        )
    for value in values:
        _cid(value, field)
    return values


@dataclass(frozen=True, order=True, slots=True)
class InitialStateMassV1:
    state_id: str
    probability: Fraction

    def __post_init__(self) -> None:
        _cid(self.state_id, "initial state_id")
        object.__setattr__(
            self, "probability", _fraction(self.probability, "initial probability")
        )
        if not 0 < self.probability <= 1:
            raise PartialSoundAuditInvariantViolation(
                "initial probability must lie in (0,1]"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "probability": _fraction_document(self.probability),
        }


@dataclass(frozen=True, order=True, slots=True)
class RewardWeightV1:
    name: str
    weight: Fraction

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise PartialSoundAuditInvariantViolation(
                "reward weight name must be nonempty text"
            )
        object.__setattr__(self, "weight", _fraction(self.weight, "reward weight"))

    def to_document(self) -> dict[str, Any]:
        return {"name": self.name, "weight": _fraction_document(self.weight)}


@dataclass(frozen=True, slots=True)
class RegisteredReturnBoundProofV1:
    structural_id: str
    environment_instance_id: str
    observation_log_id: str
    semantics_profile_id: str
    observation_authority_id: str
    acquisition_manifest_id: str
    reward_weights: tuple[RewardWeightV1, ...]
    item_count: int = 6
    maximum_match_events: int = 2
    terminal_clear_bonus_upper: Fraction = Fraction(2)
    return_upper: Fraction = Fraction(4)
    reward_basis_nonnegative: bool = True
    formula_id: str = RETURN_BOUND_FORMULA_ID
    authority_kind: str = "PREREGISTERED_CANONICAL_LMB_N6_RETURN_BOUND_V1"

    def __post_init__(self) -> None:
        for field in (
            "structural_id",
            "environment_instance_id",
            "observation_log_id",
            "semantics_profile_id",
            "observation_authority_id",
            "acquisition_manifest_id",
        ):
            _cid(getattr(self, field), f"return proof {field}")
        if type(self.reward_weights) is not tuple or any(
            type(item) is not RewardWeightV1 for item in self.reward_weights
        ):
            raise PartialSoundAuditInvariantViolation(
                "return proof rejects duck reward weights"
            )
        if self.reward_weights != (
            RewardWeightV1("match", Fraction(1)),
            RewardWeightV1("terminal_clear", Fraction(1)),
        ):
            raise PartialSoundAuditInvariantViolation(
                "canonical return proof requires the registered reward basis"
            )
        _integer(self.item_count, "return proof item_count", 1)
        _integer(self.maximum_match_events, "maximum_match_events")
        object.__setattr__(
            self,
            "terminal_clear_bonus_upper",
            _fraction(self.terminal_clear_bonus_upper, "terminal bonus upper"),
        )
        object.__setattr__(
            self,
            "return_upper",
            _fraction(self.return_upper, "return upper"),
        )
        if (
            self.item_count != 6
            or self.maximum_match_events != 2
            or self.terminal_clear_bonus_upper != 2
            or self.return_upper != 4
            or self.return_upper
            != self.maximum_match_events + self.terminal_clear_bonus_upper
            or self.reward_basis_nonnegative is not True
            or self.formula_id != RETURN_BOUND_FORMULA_ID
            or self.authority_kind
            != "PREREGISTERED_CANONICAL_LMB_N6_RETURN_BOUND_V1"
        ):
            raise PartialSoundAuditInvariantViolation(
                "return proof is not the canonical nonnegative LMB N=6 bound"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.registered_return_bound_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "structural_id": self.structural_id,
            "environment_instance_id": self.environment_instance_id,
            "observation_log_id": self.observation_log_id,
            "semantics_profile_id": self.semantics_profile_id,
            "observation_authority_id": self.observation_authority_id,
            "acquisition_manifest_id": self.acquisition_manifest_id,
            "reward_weights": [item.to_document() for item in self.reward_weights],
            "item_count": self.item_count,
            "maximum_match_events": self.maximum_match_events,
            "terminal_clear_bonus_upper": _fraction_document(
                self.terminal_clear_bonus_upper
            ),
            "return_upper": _fraction_document(self.return_upper),
            "reward_basis_nonnegative": self.reward_basis_nonnegative,
            "formula_id": self.formula_id,
            "authority_kind": self.authority_kind,
        }

    @property
    def proof_id(self) -> str:
        return _content_id("return_bound_proof", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


def canonical_lmb_n6_return_bound_proof_v1() -> RegisteredReturnBoundProofV1:
    """Return the sole V0-043 registered reward-scale authority."""

    return RegisteredReturnBoundProofV1(
        CANONICAL_LMB_N6_STRUCTURAL_ID,
        CANONICAL_LMB_N6_ENVIRONMENT_INSTANCE_ID,
        CANONICAL_LMB_N6_OBSERVATION_LOG_ID,
        CANONICAL_LMB_N6_SEMANTICS_PROFILE_ID,
        CANONICAL_LMB_N6_OBSERVATION_AUTHORITY_ID,
        CANONICAL_LMB_N6_ACQUISITION_MANIFEST_ID,
        (
            RewardWeightV1("match", Fraction(1)),
            RewardWeightV1("terminal_clear", Fraction(1)),
        ),
    )


REGISTERED_RETURN_BOUND_PROOF_IDS = frozenset(
    (canonical_lmb_n6_return_bound_proof_v1().proof_id,)
)


@dataclass(frozen=True, slots=True)
class FrozenPartialAuditThresholdsV1:
    partial_model_id: str
    horizon: int
    initial_state_distribution: tuple[InitialStateMassV1, ...]
    reward_weights: tuple[RewardWeightV1, ...]
    normalized_regret_tolerance: Fraction
    risk_tolerance: Fraction
    return_bound_proof: RegisteredReturnBoundProofV1
    unrestricted_upper_formula_id: str = UNRESTRICTED_UPPER_FORMULA_ID
    goal_id: str = "default"

    def __post_init__(self) -> None:
        _cid(self.partial_model_id, "threshold partial_model_id")
        _integer(self.horizon, "threshold horizon", 1)
        if type(self.initial_state_distribution) is not tuple or any(
            type(item) is not InitialStateMassV1
            for item in self.initial_state_distribution
        ):
            raise PartialSoundAuditInvariantViolation(
                "thresholds reject duck initial rows"
            )
        if (
            not self.initial_state_distribution
            or self.initial_state_distribution
            != tuple(sorted(self.initial_state_distribution))
            or len({item.state_id for item in self.initial_state_distribution})
            != len(self.initial_state_distribution)
            or sum(
                (
                    item.probability
                    for item in self.initial_state_distribution
                ),
                Fraction(0),
            )
            != 1
        ):
            raise PartialSoundAuditInvariantViolation(
                "initial distribution must be unique, sorted, and unit mass"
            )
        if type(self.reward_weights) is not tuple or any(
            type(item) is not RewardWeightV1 for item in self.reward_weights
        ):
            raise PartialSoundAuditInvariantViolation(
                "thresholds reject duck reward weights"
            )
        if (
            not self.reward_weights
            or self.reward_weights != tuple(sorted(self.reward_weights))
            or len({item.name for item in self.reward_weights})
            != len(self.reward_weights)
        ):
            raise PartialSoundAuditInvariantViolation(
                "reward weights must be nonempty, unique, and sorted"
            )
        object.__setattr__(
            self,
            "normalized_regret_tolerance",
            _fraction(
                self.normalized_regret_tolerance,
                "normalized regret tolerance",
            ),
        )
        object.__setattr__(
            self,
            "risk_tolerance",
            _fraction(self.risk_tolerance, "risk tolerance"),
        )
        if (
            self.normalized_regret_tolerance
            not in REGISTERED_NORMALIZED_REGRET_TOLERANCES
            or self.risk_tolerance not in REGISTERED_RISK_TOLERANCES
        ):
            raise PartialSoundAuditInvariantViolation(
                "threshold tolerances must belong to the V0 registry"
            )
        if type(self.return_bound_proof) is not RegisteredReturnBoundProofV1:
            raise PartialSoundAuditInvariantViolation(
                "thresholds reject duck return-bound proofs"
            )
        if (
            self.return_bound_proof.proof_id
            not in REGISTERED_RETURN_BOUND_PROOF_IDS
            or self.return_bound_proof.reward_weights != self.reward_weights
        ):
            raise PartialSoundAuditInvariantViolation(
                "thresholds require the matching registered return-bound proof"
            )
        if self.unrestricted_upper_formula_id != UNRESTRICTED_UPPER_FORMULA_ID:
            raise PartialSoundAuditInvariantViolation(
                "unsupported unrestricted upper formula"
            )
        if type(self.goal_id) is not str or self.goal_id != "default":
            raise PartialSoundAuditInvariantViolation(
                "V0-043 supports exactly goal_id=default"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_partial_audit_thresholds.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_model_id": self.partial_model_id,
            "horizon": self.horizon,
            "initial_state_distribution": [
                item.to_document() for item in self.initial_state_distribution
            ],
            "reward_weights": [item.to_document() for item in self.reward_weights],
            "normalized_regret_tolerance": _fraction_document(
                self.normalized_regret_tolerance
            ),
            "risk_tolerance": _fraction_document(self.risk_tolerance),
            "return_bound_proof": self.return_bound_proof.to_document(),
            "unrestricted_upper_formula_id": self.unrestricted_upper_formula_id,
            "goal_id": self.goal_id,
        }

    @property
    def thresholds_id(self) -> str:
        return _content_id("thresholds", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "thresholds_id": self.thresholds_id}


@dataclass(frozen=True, order=True, slots=True)
class ContingentPlanAssignmentV1:
    cell_id: str
    semantic_action_id: str

    def __post_init__(self) -> None:
        _cid(self.cell_id, "assignment cell_id")
        _cid(self.semantic_action_id, "assignment semantic_action_id")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_contingent_plan_assignment.v1",
            "cell_id": self.cell_id,
            "semantic_action_id": self.semantic_action_id,
        }

    @property
    def assignment_id(self) -> str:
        return _content_id("assignment", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "assignment_id": self.assignment_id}


@dataclass(frozen=True, slots=True)
class ContingentPlanStageV1:
    time_index: int
    assignments: tuple[ContingentPlanAssignmentV1, ...]

    def __post_init__(self) -> None:
        _integer(self.time_index, "stage time_index")
        if type(self.assignments) is not tuple or any(
            type(item) is not ContingentPlanAssignmentV1
            for item in self.assignments
        ):
            raise PartialSoundAuditInvariantViolation(
                "stage rejects duck assignments"
            )
        if (
            not self.assignments
            or self.assignments != tuple(sorted(self.assignments))
            or len({item.cell_id for item in self.assignments})
            != len(self.assignments)
        ):
            raise PartialSoundAuditInvariantViolation(
                "stage assignments must be nonempty, unique, and sorted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_contingent_plan_stage.v1",
            "time_index": self.time_index,
            "assignments": [item.to_document() for item in self.assignments],
        }

    @property
    def stage_id(self) -> str:
        return _content_id("stage", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_id": self.stage_id}


@dataclass(frozen=True, slots=True)
class FrozenContingentAbstractPlanV1:
    partial_model_id: str
    horizon: int
    stages: tuple[ContingentPlanStageV1, ...]
    selector_kind: str = "deterministic_finite_horizon_contingent_abstract_plan_v1"
    policy_randomization_allowed: bool = False

    def __post_init__(self) -> None:
        _cid(self.partial_model_id, "plan partial_model_id")
        _integer(self.horizon, "plan horizon", 1)
        if type(self.stages) is not tuple or any(
            type(item) is not ContingentPlanStageV1 for item in self.stages
        ):
            raise PartialSoundAuditInvariantViolation("plan rejects duck stages")
        if tuple(item.time_index for item in self.stages) != tuple(
            range(self.horizon)
        ):
            raise PartialSoundAuditInvariantViolation(
                "plan stages must be contiguous and cover 0..H-1"
            )
        if (
            self.selector_kind
            != "deterministic_finite_horizon_contingent_abstract_plan_v1"
            or self.policy_randomization_allowed is not False
        ):
            raise PartialSoundAuditInvariantViolation(
                "V0 accepts only deterministic abstract selectors"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_partial_contingent_abstract_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_model_id": self.partial_model_id,
            "horizon": self.horizon,
            "stages": [item.to_document() for item in self.stages],
            "selector_kind": self.selector_kind,
            "policy_randomization_allowed": self.policy_randomization_allowed,
        }

    @property
    def plan_id(self) -> str:
        return _content_id("plan", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "plan_id": self.plan_id}


@dataclass(frozen=True, slots=True)
class StateActionTimeObligationV1:
    partial_model_id: str
    thresholds_id: str
    contingent_plan_id: str
    time_index: int
    remaining_horizon: int
    state_id: str
    cell_id: str
    semantic_action_id: str
    support_ground_row_ids: tuple[str, ...]
    observed_ground_row_ids: tuple[str, ...]
    missing_ground_row_ids: tuple[str, ...]
    reachable_cell_mass_upper: Fraction
    shared_unknown_mass: Fraction
    known_external_successor_mass: Fraction
    reachable_unknown_mass_upper: Fraction
    reachable_external_continuation_mass_upper: Fraction
    representative_disagreement: bool
    realization_singleton: bool

    def __post_init__(self) -> None:
        for field in (
            "partial_model_id",
            "thresholds_id",
            "contingent_plan_id",
            "state_id",
            "cell_id",
            "semantic_action_id",
        ):
            _cid(getattr(self, field), f"obligation {field}")
        _integer(self.time_index, "obligation time_index")
        _integer(self.remaining_horizon, "obligation remaining_horizon", 1)
        support = _sorted_ids(self.support_ground_row_ids, "obligation support")
        observed = _sorted_ids(self.observed_ground_row_ids, "obligation observed")
        missing = _sorted_ids(self.missing_ground_row_ids, "obligation missing")
        if (
            not support
            or set(observed) & set(missing)
            or tuple(sorted((*observed, *missing))) != support
        ):
            raise PartialSoundAuditInvariantViolation(
                "obligation observed/missing rows must partition support"
            )
        for field in (
            "reachable_cell_mass_upper",
            "shared_unknown_mass",
            "known_external_successor_mass",
            "reachable_unknown_mass_upper",
            "reachable_external_continuation_mass_upper",
        ):
            value = _fraction(getattr(self, field), field)
            object.__setattr__(self, field, value)
            if not 0 <= value <= 1:
                raise PartialSoundAuditInvariantViolation(
                    f"obligation {field} lies outside [0,1]"
                )
        if self.shared_unknown_mass != Fraction(len(missing), len(support)):
            raise PartialSoundAuditInvariantViolation(
                "obligation shared unknown mass differs from missing support"
            )
        if self.reachable_unknown_mass_upper != (
            self.reachable_cell_mass_upper * self.shared_unknown_mass
        ):
            raise PartialSoundAuditInvariantViolation(
                "reachable unknown mass is inconsistent"
            )
        expected_external = (
            self.reachable_cell_mass_upper
            * self.known_external_successor_mass
            if self.remaining_horizon > 1
            else Fraction(0)
        )
        if self.reachable_external_continuation_mass_upper != expected_external:
            raise PartialSoundAuditInvariantViolation(
                "reachable external continuation mass is inconsistent"
            )
        if type(self.representative_disagreement) is not bool or type(
            self.realization_singleton
        ) is not bool:
            raise PartialSoundAuditInvariantViolation(
                "obligation flags must be exact booleans"
            )
        if self.realization_singleton != (self.shared_unknown_mass == 0):
            raise PartialSoundAuditInvariantViolation(
                "obligation singleton flag disagrees with shared unknown mass"
            )

    @property
    def unresolved_mass_upper(self) -> Fraction:
        return (
            self.reachable_unknown_mass_upper
            + self.reachable_external_continuation_mass_upper
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_state_action_time_obligation.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "contingent_plan_id": self.contingent_plan_id,
            "time_index": self.time_index,
            "remaining_horizon": self.remaining_horizon,
            "state_id": self.state_id,
            "cell_id": self.cell_id,
            "semantic_action_id": self.semantic_action_id,
            "support_ground_row_ids": list(self.support_ground_row_ids),
            "observed_ground_row_ids": list(self.observed_ground_row_ids),
            "missing_ground_row_ids": list(self.missing_ground_row_ids),
            "reachable_cell_mass_upper": _fraction_document(
                self.reachable_cell_mass_upper
            ),
            "shared_unknown_mass": _fraction_document(self.shared_unknown_mass),
            "known_external_successor_mass": _fraction_document(
                self.known_external_successor_mass
            ),
            "reachable_unknown_mass_upper": _fraction_document(
                self.reachable_unknown_mass_upper
            ),
            "reachable_external_continuation_mass_upper": _fraction_document(
                self.reachable_external_continuation_mass_upper
            ),
            "unresolved_mass_upper": _fraction_document(
                self.unresolved_mass_upper
            ),
            "representative_disagreement": self.representative_disagreement,
            "realization_singleton": self.realization_singleton,
        }

    @property
    def obligation_id(self) -> str:
        return _content_id("obligation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "obligation_id": self.obligation_id}


@dataclass(frozen=True, slots=True)
class UnrestrictedGroundUpperRowV1:
    partial_model_id: str
    thresholds_id: str
    time_index: int
    remaining_horizon: int
    state_id: str
    cell_id: str
    ground_row_id: str
    ground_action_id: str
    reward_upper: Fraction

    def __post_init__(self) -> None:
        for field in (
            "partial_model_id",
            "thresholds_id",
            "state_id",
            "cell_id",
            "ground_row_id",
            "ground_action_id",
        ):
            _cid(getattr(self, field), f"unrestricted row {field}")
        _integer(self.time_index, "unrestricted row time_index")
        _integer(self.remaining_horizon, "unrestricted row remaining_horizon", 1)
        object.__setattr__(
            self, "reward_upper", _fraction(self.reward_upper, "reward upper")
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_unrestricted_ground_upper_row.v1",
            "schema_version": SCHEMA_VERSION,
            "formula_id": UNRESTRICTED_UPPER_FORMULA_ID,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "time_index": self.time_index,
            "remaining_horizon": self.remaining_horizon,
            "state_id": self.state_id,
            "cell_id": self.cell_id,
            "ground_row_id": self.ground_row_id,
            "ground_action_id": self.ground_action_id,
            "reward_upper": _fraction_document(self.reward_upper),
        }

    @property
    def unrestricted_row_id(self) -> str:
        return _content_id("unrestricted_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "unrestricted_row_id": self.unrestricted_row_id}


@dataclass(frozen=True, slots=True)
class PartialPolicyBoundRowV1:
    partial_model_id: str
    thresholds_id: str
    contingent_plan_id: str
    time_index: int
    remaining_horizon: int
    cell_id: str
    semantic_action_id: str
    representative_state_ids: tuple[str, ...]
    missing_ground_row_ids: tuple[str, ...]
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction
    max_shared_unknown_mass: Fraction
    external_boundary_possible: bool
    representative_disagreement: bool

    def __post_init__(self) -> None:
        for field in (
            "partial_model_id",
            "thresholds_id",
            "contingent_plan_id",
            "cell_id",
            "semantic_action_id",
        ):
            _cid(getattr(self, field), f"bound row {field}")
        _integer(self.time_index, "bound row time_index")
        _integer(self.remaining_horizon, "bound row remaining_horizon", 1)
        if not _sorted_ids(
            self.representative_state_ids, "bound representative states"
        ):
            raise PartialSoundAuditInvariantViolation(
                "bound row needs representative states"
            )
        _sorted_ids(self.missing_ground_row_ids, "bound missing rows")
        for field in (
            "reward_lower",
            "reward_upper",
            "failure_lower",
            "failure_upper",
            "max_shared_unknown_mass",
        ):
            object.__setattr__(self, field, _fraction(getattr(self, field), field))
        if self.reward_lower > self.reward_upper:
            raise PartialSoundAuditInvariantViolation(
                "bound reward lower exceeds upper"
            )
        if not 0 <= self.failure_lower <= self.failure_upper <= 1:
            raise PartialSoundAuditInvariantViolation(
                "bound failure interval lies outside [0,1]"
            )
        if not 0 <= self.max_shared_unknown_mass <= 1:
            raise PartialSoundAuditInvariantViolation(
                "bound shared unknown mass lies outside [0,1]"
            )
        if type(self.external_boundary_possible) is not bool or type(
            self.representative_disagreement
        ) is not bool:
            raise PartialSoundAuditInvariantViolation(
                "bound row flags must be exact booleans"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_fixed_plan_bound_row.v1",
            "schema_version": SCHEMA_VERSION,
            "formula_id": ROBUST_BELLMAN_FORMULA_ID,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "contingent_plan_id": self.contingent_plan_id,
            "time_index": self.time_index,
            "remaining_horizon": self.remaining_horizon,
            "cell_id": self.cell_id,
            "semantic_action_id": self.semantic_action_id,
            "representative_state_ids": list(self.representative_state_ids),
            "missing_ground_row_ids": list(self.missing_ground_row_ids),
            "reward_lower": _fraction_document(self.reward_lower),
            "reward_upper": _fraction_document(self.reward_upper),
            "failure_lower": _fraction_document(self.failure_lower),
            "failure_upper": _fraction_document(self.failure_upper),
            "max_shared_unknown_mass": _fraction_document(
                self.max_shared_unknown_mass
            ),
            "external_boundary_possible": self.external_boundary_possible,
            "representative_disagreement": self.representative_disagreement,
        }

    @property
    def bound_row_id(self) -> str:
        return _content_id("bound_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bound_row_id": self.bound_row_id}


@dataclass(frozen=True, slots=True)
class InitialSupportPointRegretRowV1:
    partial_model_id: str
    thresholds_id: str
    contingent_plan_id: str
    return_bound_proof_id: str
    state_id: str
    cell_id: str
    initial_probability: Fraction
    unrestricted_reward_upper: Fraction
    policy_reward_lower: Fraction
    raw_regret_upper: Fraction
    return_upper: Fraction
    normalized_regret_upper: Fraction
    normalized_regret_tolerance: Fraction
    obligation_certified: bool

    def __post_init__(self) -> None:
        for field in (
            "partial_model_id",
            "thresholds_id",
            "contingent_plan_id",
            "return_bound_proof_id",
            "state_id",
            "cell_id",
        ):
            _cid(getattr(self, field), f"support regret {field}")
        for field in (
            "initial_probability",
            "unrestricted_reward_upper",
            "policy_reward_lower",
            "raw_regret_upper",
            "return_upper",
            "normalized_regret_upper",
            "normalized_regret_tolerance",
        ):
            object.__setattr__(self, field, _fraction(getattr(self, field), field))
        if not 0 < self.initial_probability <= 1 or self.return_upper <= 0:
            raise PartialSoundAuditInvariantViolation(
                "support regret probability/return scale is invalid"
            )
        if not (
            0 <= self.policy_reward_lower
            <= self.unrestricted_reward_upper
            <= self.return_upper
        ):
            raise PartialSoundAuditInvariantViolation(
                "support regret rewards violate the registered return upper"
            )
        if (
            self.raw_regret_upper
            != self.unrestricted_reward_upper - self.policy_reward_lower
            or self.raw_regret_upper < 0
            or self.normalized_regret_upper
            != self.raw_regret_upper / self.return_upper
        ):
            raise PartialSoundAuditInvariantViolation(
                "support regret row is not the exact normalized difference"
            )
        if (
            self.normalized_regret_tolerance
            not in REGISTERED_NORMALIZED_REGRET_TOLERANCES
            or type(self.obligation_certified) is not bool
            or self.obligation_certified
            != (
                self.normalized_regret_upper
                <= self.normalized_regret_tolerance
            )
        ):
            raise PartialSoundAuditInvariantViolation(
                "support regret certification disagrees with the V0 threshold"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.initial_support_point_regret_row.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "contingent_plan_id": self.contingent_plan_id,
            "return_bound_proof_id": self.return_bound_proof_id,
            "state_id": self.state_id,
            "cell_id": self.cell_id,
            "initial_probability": _fraction_document(self.initial_probability),
            "unrestricted_reward_upper": _fraction_document(
                self.unrestricted_reward_upper
            ),
            "policy_reward_lower": _fraction_document(self.policy_reward_lower),
            "raw_regret_upper": _fraction_document(self.raw_regret_upper),
            "return_upper": _fraction_document(self.return_upper),
            "normalized_regret_upper": _fraction_document(
                self.normalized_regret_upper
            ),
            "normalized_regret_tolerance": _fraction_document(
                self.normalized_regret_tolerance
            ),
            "obligation_certified": self.obligation_certified,
        }

    @property
    def support_point_regret_row_id(self) -> str:
        return _content_id("support_point_regret", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "support_point_regret_row_id": self.support_point_regret_row_id,
        }


@dataclass(frozen=True, slots=True)
class PartialFixedPlanRobustBoundsV1:
    partial_model_id: str
    thresholds_id: str
    contingent_plan_id: str
    return_bound_proof_id: str
    rows: tuple[PartialPolicyBoundRowV1, ...]
    unrestricted_rows: tuple[UnrestrictedGroundUpperRowV1, ...]
    support_point_regret_rows: tuple[InitialSupportPointRegretRowV1, ...]
    unrestricted_reward_upper: Fraction
    policy_reward_lower: Fraction
    policy_reward_upper: Fraction
    policy_failure_lower: Fraction
    policy_failure_upper: Fraction
    raw_distribution_regret: Fraction
    normalized_distribution_regret: Fraction
    return_upper: Fraction
    normalized_regret_tolerance: Fraction
    risk_tolerance: Fraction
    reward_obligation_certified: bool
    risk_obligation_certified: bool
    external_coverage_certified: bool
    external_escape_obligation_ids: tuple[str, ...]
    reachable_cell_horizon_pairs: int

    def __post_init__(self) -> None:
        for field in (
            "partial_model_id",
            "thresholds_id",
            "contingent_plan_id",
            "return_bound_proof_id",
        ):
            _cid(getattr(self, field), f"bounds {field}")
        if type(self.rows) is not tuple or any(
            type(item) is not PartialPolicyBoundRowV1 for item in self.rows
        ):
            raise PartialSoundAuditInvariantViolation("bounds reject duck rows")
        if type(self.unrestricted_rows) is not tuple or any(
            type(item) is not UnrestrictedGroundUpperRowV1
            for item in self.unrestricted_rows
        ):
            raise PartialSoundAuditInvariantViolation(
                "bounds reject duck unrestricted rows"
            )
        if type(self.support_point_regret_rows) is not tuple or any(
            type(item) is not InitialSupportPointRegretRowV1
            for item in self.support_point_regret_rows
        ):
            raise PartialSoundAuditInvariantViolation(
                "bounds reject duck support-point regret rows"
            )
        unrestricted_keys = tuple(
            (item.time_index, item.state_id, item.ground_row_id)
            for item in self.unrestricted_rows
        )
        if not self.unrestricted_rows or unrestricted_keys != tuple(
            sorted(set(unrestricted_keys))
        ):
            raise PartialSoundAuditInvariantViolation(
                "unrestricted rows must be complete, unique, and sorted"
            )
        if any(
            item.partial_model_id != self.partial_model_id
            or item.thresholds_id != self.thresholds_id
            for item in self.unrestricted_rows
        ):
            raise PartialSoundAuditInvariantViolation(
                "unrestricted rows do not bind this model and threshold context"
            )
        keys = tuple((item.time_index, item.cell_id) for item in self.rows)
        if not self.rows or keys != tuple(sorted(set(keys))):
            raise PartialSoundAuditInvariantViolation(
                "bound rows must be unique and time/cell sorted"
            )
        if any(
            item.partial_model_id != self.partial_model_id
            or item.thresholds_id != self.thresholds_id
            or item.contingent_plan_id != self.contingent_plan_id
            for item in self.rows
        ):
            raise PartialSoundAuditInvariantViolation(
                "bound rows do not bind this proof context"
            )
        support_keys = tuple(item.state_id for item in self.support_point_regret_rows)
        if not support_keys or support_keys != tuple(sorted(set(support_keys))):
            raise PartialSoundAuditInvariantViolation(
                "support-point regret rows must be nonempty, unique, and sorted"
            )
        if any(
            item.partial_model_id != self.partial_model_id
            or item.thresholds_id != self.thresholds_id
            or item.contingent_plan_id != self.contingent_plan_id
            or item.return_bound_proof_id != self.return_bound_proof_id
            for item in self.support_point_regret_rows
        ):
            raise PartialSoundAuditInvariantViolation(
                "support-point regret rows do not bind this proof context"
            )
        _sorted_ids(
            self.external_escape_obligation_ids,
            "bounds external escape obligations",
        )
        for field in (
            "unrestricted_reward_upper",
            "policy_reward_lower",
            "policy_reward_upper",
            "policy_failure_lower",
            "policy_failure_upper",
            "raw_distribution_regret",
            "normalized_distribution_regret",
            "return_upper",
            "normalized_regret_tolerance",
            "risk_tolerance",
        ):
            object.__setattr__(self, field, _fraction(getattr(self, field), field))
        if any(
            item.return_upper != self.return_upper
            or item.normalized_regret_tolerance
            != self.normalized_regret_tolerance
            for item in self.support_point_regret_rows
        ):
            raise PartialSoundAuditInvariantViolation(
                "support-point regret rows disagree with enclosing scale/tolerance"
            )
        if self.return_upper <= 0 or not (
            0 <= self.policy_reward_lower
            <= self.policy_reward_upper
            <= self.unrestricted_reward_upper
            <= self.return_upper
        ):
            raise PartialSoundAuditInvariantViolation(
                "root rewards violate the registered total-return cap"
            )
        if (
            self.raw_distribution_regret
            != self.unrestricted_reward_upper - self.policy_reward_lower
            or self.raw_distribution_regret < 0
            or self.normalized_distribution_regret
            != self.raw_distribution_regret / self.return_upper
        ):
            raise PartialSoundAuditInvariantViolation(
                "distribution regret diagnostic is inconsistent"
            )
        if sum(
            (item.initial_probability for item in self.support_point_regret_rows),
            Fraction(0),
        ) != 1 or self.unrestricted_reward_upper != sum(
            (
                item.initial_probability * item.unrestricted_reward_upper
                for item in self.support_point_regret_rows
            ),
            Fraction(0),
        ) or self.policy_reward_lower != sum(
            (
                item.initial_probability * item.policy_reward_lower
                for item in self.support_point_regret_rows
            ),
            Fraction(0),
        ):
            raise PartialSoundAuditInvariantViolation(
                "distribution diagnostics do not reconcile support-point rows"
            )
        if self.normalized_regret_tolerance not in (
            REGISTERED_NORMALIZED_REGRET_TOLERANCES
        ) or not (
            0
            <= self.policy_failure_lower
            <= self.policy_failure_upper
            <= 1
            and self.risk_tolerance in REGISTERED_RISK_TOLERANCES
        ):
            raise PartialSoundAuditInvariantViolation(
                "root value/risk quantities are invalid"
            )
        if any(
            type(value) is not bool
            for value in (
                self.reward_obligation_certified,
                self.risk_obligation_certified,
                self.external_coverage_certified,
            )
        ):
            raise PartialSoundAuditInvariantViolation(
                "certification flags must be exact booleans"
            )
        if self.reward_obligation_certified != all(
            item.obligation_certified
            for item in self.support_point_regret_rows
        ) or self.risk_obligation_certified != (
            self.policy_failure_upper <= self.risk_tolerance
        ) or self.external_coverage_certified != (
            not self.external_escape_obligation_ids
        ):
            raise PartialSoundAuditInvariantViolation(
                "certification flags disagree with support/risk/coverage obligations"
            )
        _integer(self.reachable_cell_horizon_pairs, "reachable pairs", 1)

    @property
    def maximum_support_point_normalized_regret(self) -> Fraction:
        return max(
            item.normalized_regret_upper
            for item in self.support_point_regret_rows
        )

    @property
    def certified(self) -> bool:
        return (
            self.reward_obligation_certified
            and self.risk_obligation_certified
            and self.external_coverage_certified
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_fixed_plan_robust_bounds.v1",
            "schema_version": SCHEMA_VERSION,
            "formula_id": ROBUST_BELLMAN_FORMULA_ID,
            "unrestricted_upper_formula_id": UNRESTRICTED_UPPER_FORMULA_ID,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "contingent_plan_id": self.contingent_plan_id,
            "return_bound_proof_id": self.return_bound_proof_id,
            "rows": [item.to_document() for item in self.rows],
            "unrestricted_rows": [
                item.to_document() for item in self.unrestricted_rows
            ],
            "support_point_regret_rows": [
                item.to_document() for item in self.support_point_regret_rows
            ],
            "unrestricted_reward_upper": _fraction_document(
                self.unrestricted_reward_upper
            ),
            "policy_reward_lower": _fraction_document(self.policy_reward_lower),
            "policy_reward_upper": _fraction_document(self.policy_reward_upper),
            "policy_failure_lower": _fraction_document(self.policy_failure_lower),
            "policy_failure_upper": _fraction_document(self.policy_failure_upper),
            "raw_distribution_regret": _fraction_document(
                self.raw_distribution_regret
            ),
            "normalized_distribution_regret": _fraction_document(
                self.normalized_distribution_regret
            ),
            "return_upper": _fraction_document(self.return_upper),
            "maximum_support_point_normalized_regret": _fraction_document(
                self.maximum_support_point_normalized_regret
            ),
            "normalized_regret_tolerance": _fraction_document(
                self.normalized_regret_tolerance
            ),
            "risk_tolerance": _fraction_document(self.risk_tolerance),
            "reward_obligation_certified": self.reward_obligation_certified,
            "risk_obligation_certified": self.risk_obligation_certified,
            "external_coverage_certified": self.external_coverage_certified,
            "external_escape_obligation_ids": list(
                self.external_escape_obligation_ids
            ),
            "reachable_cell_horizon_pairs": self.reachable_cell_horizon_pairs,
        }

    @property
    def bounds_id(self) -> str:
        return _content_id("bounds", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bounds_id": self.bounds_id}


@dataclass(frozen=True, slots=True)
class PartialFixedPlanCertificateV1:
    partial_model_id: str
    thresholds_id: str
    contingent_plan_id: str
    bounds_id: str
    return_bound_proof_id: str
    obligation_ids: tuple[str, ...]
    reachable_bound_row_ids: tuple[str, ...]
    support_point_regret_row_ids: tuple[str, ...]
    maximum_support_point_normalized_regret: Fraction
    normalized_regret_tolerance: Fraction
    policy_failure_upper: Fraction
    risk_tolerance: Fraction
    external_coverage_certified: bool
    certificate_kind: str = "ROBUST_FIXED_CONTINGENT_PLAN_CERTIFICATE_V1"
    optimality_claimed: bool = False
    infeasibility_claimed: bool = False
    planning_claimed: bool = False

    def __post_init__(self) -> None:
        for field in (
            "partial_model_id",
            "thresholds_id",
            "contingent_plan_id",
            "bounds_id",
            "return_bound_proof_id",
        ):
            _cid(getattr(self, field), f"certificate {field}")
        _sorted_ids(self.obligation_ids, "certificate obligations")
        if not _sorted_ids(
            self.reachable_bound_row_ids, "certificate bound rows"
        ) or not _sorted_ids(
            self.support_point_regret_row_ids,
            "certificate support-point regret rows",
        ):
            raise PartialSoundAuditInvariantViolation(
                "certificate needs reachable bound and support-point rows"
            )
        for field in (
            "maximum_support_point_normalized_regret",
            "normalized_regret_tolerance",
            "policy_failure_upper",
            "risk_tolerance",
        ):
            object.__setattr__(self, field, _fraction(getattr(self, field), field))
        if (
            self.maximum_support_point_normalized_regret < 0
            or self.maximum_support_point_normalized_regret
            > self.normalized_regret_tolerance
            or self.normalized_regret_tolerance
            not in REGISTERED_NORMALIZED_REGRET_TOLERANCES
            or not 0 <= self.policy_failure_upper <= self.risk_tolerance <= 1
            or self.risk_tolerance not in REGISTERED_RISK_TOLERANCES
            or self.external_coverage_certified is not True
        ):
            raise PartialSoundAuditInvariantViolation(
                "certificate does not pass value, risk, and coverage obligations"
            )
        if (
            self.certificate_kind
            != "ROBUST_FIXED_CONTINGENT_PLAN_CERTIFICATE_V1"
            or self.optimality_claimed is not False
            or self.infeasibility_claimed is not False
            or self.planning_claimed is not False
        ):
            raise PartialSoundAuditInvariantViolation(
                "fixed-plan certificate overclaims its scope"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_fixed_plan_certificate.v1",
            "schema_version": SCHEMA_VERSION,
            "certificate_kind": self.certificate_kind,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "contingent_plan_id": self.contingent_plan_id,
            "bounds_id": self.bounds_id,
            "return_bound_proof_id": self.return_bound_proof_id,
            "obligation_ids": list(self.obligation_ids),
            "reachable_bound_row_ids": list(self.reachable_bound_row_ids),
            "support_point_regret_row_ids": list(
                self.support_point_regret_row_ids
            ),
            "maximum_support_point_normalized_regret": _fraction_document(
                self.maximum_support_point_normalized_regret
            ),
            "normalized_regret_tolerance": _fraction_document(
                self.normalized_regret_tolerance
            ),
            "policy_failure_upper": _fraction_document(self.policy_failure_upper),
            "risk_tolerance": _fraction_document(self.risk_tolerance),
            "external_coverage_certified": self.external_coverage_certified,
            "optimality_claimed": self.optimality_claimed,
            "infeasibility_claimed": self.infeasibility_claimed,
            "planning_claimed": self.planning_claimed,
        }

    @property
    def certificate_id(self) -> str:
        return _content_id("certificate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "certificate_id": self.certificate_id}


@dataclass(frozen=True, slots=True)
class PartialFailedProofFrontierV1:
    partial_model_id: str
    thresholds_id: str
    contingent_plan_id: str
    bounds_id: str
    earliest_time_index: int
    remaining_horizon: int
    obligations: tuple[StateActionTimeObligationV1, ...]
    unresolved_exposure_sum: Fraction
    value_obligation_failed: bool
    risk_obligation_failed: bool
    external_coverage_failed: bool
    reason: FailedProofReason
    hint_kind: str = "NONAUTHORIZING_PROOF_OBLIGATION_HINT_V1"
    local_recovery_authorized: bool = False
    causal_necessity_claimed: bool = False
    causal_sufficiency_claimed: bool = False
    infeasibility_claimed: bool = False

    def __post_init__(self) -> None:
        for field in (
            "partial_model_id",
            "thresholds_id",
            "contingent_plan_id",
            "bounds_id",
        ):
            _cid(getattr(self, field), f"frontier {field}")
        _integer(self.earliest_time_index, "frontier time_index")
        _integer(self.remaining_horizon, "frontier remaining_horizon", 1)
        if type(self.obligations) is not tuple or any(
            type(item) is not StateActionTimeObligationV1
            for item in self.obligations
        ):
            raise PartialSoundAuditInvariantViolation(
                "frontier rejects duck obligations"
            )
        keys = tuple(
            (item.time_index, item.cell_id, item.state_id, item.semantic_action_id)
            for item in self.obligations
        )
        if not self.obligations or keys != tuple(sorted(set(keys))):
            raise PartialSoundAuditInvariantViolation(
                "frontier obligations must be unique and sorted"
            )
        if any(
            item.partial_model_id != self.partial_model_id
            or item.thresholds_id != self.thresholds_id
            or item.contingent_plan_id != self.contingent_plan_id
            or item.time_index != self.earliest_time_index
            or item.remaining_horizon != self.remaining_horizon
            for item in self.obligations
        ):
            raise PartialSoundAuditInvariantViolation(
                "frontier obligations disagree with context or earliest stage"
            )
        object.__setattr__(
            self,
            "unresolved_exposure_sum",
            _fraction(
                self.unresolved_exposure_sum,
                "frontier unresolved exposure sum",
            ),
        )
        if self.unresolved_exposure_sum != sum(
            (item.unresolved_mass_upper for item in self.obligations), Fraction(0)
        ) or self.unresolved_exposure_sum < 0:
            raise PartialSoundAuditInvariantViolation(
                "frontier unresolved exposure sum does not reconcile"
            )
        if any(
            type(value) is not bool
            for value in (
                self.value_obligation_failed,
                self.risk_obligation_failed,
                self.external_coverage_failed,
            )
        ) or not (
            self.value_obligation_failed
            or self.risk_obligation_failed
            or self.external_coverage_failed
        ):
            raise PartialSoundAuditInvariantViolation(
                "frontier requires a failed value, risk, or coverage obligation"
            )
        if type(self.reason) is not FailedProofReason:
            raise PartialSoundAuditInvariantViolation(
                "frontier reason requires the exact enum"
            )
        if self.reason is FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION and not any(
            item.unresolved_mass_upper > 0 or item.representative_disagreement
            for item in self.obligations
        ):
            raise PartialSoundAuditInvariantViolation(
                "unresolved hint contains no unresolved proof obligation"
            )
        if self.reason is FailedProofReason.EXTERNAL_COVERAGE_ESCAPE and not any(
            item.remaining_horizon > 1
            and (
                item.reachable_external_continuation_mass_upper > 0
                or item.reachable_unknown_mass_upper > 0
            )
            for item in self.obligations
        ):
            raise PartialSoundAuditInvariantViolation(
                "external-escape hint contains no reachable coverage escape"
            )
        if (
            self.hint_kind != "NONAUTHORIZING_PROOF_OBLIGATION_HINT_V1"
            or self.local_recovery_authorized is not False
            or self.causal_necessity_claimed is not False
            or self.causal_sufficiency_claimed is not False
            or self.infeasibility_claimed is not False
        ):
            raise PartialSoundAuditInvariantViolation(
                "a failed-proof hint cannot authorize recovery or claim causality"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_failed_proof_frontier.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "contingent_plan_id": self.contingent_plan_id,
            "bounds_id": self.bounds_id,
            "earliest_time_index": self.earliest_time_index,
            "remaining_horizon": self.remaining_horizon,
            "obligations": [item.to_document() for item in self.obligations],
            "unresolved_exposure_sum": _fraction_document(
                self.unresolved_exposure_sum
            ),
            "unresolved_exposure_semantics": (
                "SUM_OF_REPRESENTATIVE_PROOF_EXPOSURES_NOT_A_PROBABILITY"
            ),
            "value_obligation_failed": self.value_obligation_failed,
            "risk_obligation_failed": self.risk_obligation_failed,
            "external_coverage_failed": self.external_coverage_failed,
            "reason": self.reason.value,
            "hint_kind": self.hint_kind,
            "local_recovery_authorized": self.local_recovery_authorized,
            "causal_necessity_claimed": self.causal_necessity_claimed,
            "causal_sufficiency_claimed": self.causal_sufficiency_claimed,
            "infeasibility_claimed": self.infeasibility_claimed,
        }

    @property
    def frontier_id(self) -> str:
        return _content_id("frontier", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "frontier_id": self.frontier_id}


@dataclass(frozen=True, slots=True)
class PartialSoundAuditResultV1:
    partial_model_id: str
    thresholds_id: str
    contingent_plan_id: str
    robust_bounds: PartialFixedPlanRobustBoundsV1
    proof_obligations: tuple[StateActionTimeObligationV1, ...]
    outcome: PartialAuditOutcome
    certificate: PartialFixedPlanCertificateV1 | None
    failed_proof_frontier: PartialFailedProofFrontierV1 | None
    dynamics_authority: str = "PORTABLE_PARTIAL_RAPM_ONLY"
    external_transition_authority_calls: int = 0
    ground_search_calls: int = 0
    claim_kind: str = "ROBUST_FIXED_PLAN_AUDIT_ONLY"
    failed_hint_authorizes_local_recovery: bool = False
    causal_necessity_claimed: bool = False
    causal_sufficiency_claimed: bool = False
    optimality_claimed: bool = False
    infeasibility_claimed: bool = False

    def __post_init__(self) -> None:
        for field in ("partial_model_id", "thresholds_id", "contingent_plan_id"):
            _cid(getattr(self, field), f"result {field}")
        if type(self.robust_bounds) is not PartialFixedPlanRobustBoundsV1:
            raise PartialSoundAuditInvariantViolation(
                "result rejects duck robust bounds"
            )
        if (
            self.robust_bounds.partial_model_id != self.partial_model_id
            or self.robust_bounds.thresholds_id != self.thresholds_id
            or self.robust_bounds.contingent_plan_id != self.contingent_plan_id
        ):
            raise PartialSoundAuditInvariantViolation(
                "result/bounds context mismatch"
            )
        if type(self.proof_obligations) is not tuple or any(
            type(item) is not StateActionTimeObligationV1
            for item in self.proof_obligations
        ):
            raise PartialSoundAuditInvariantViolation(
                "result rejects duck obligations"
            )
        keys = tuple(
            (item.time_index, item.cell_id, item.state_id, item.semantic_action_id)
            for item in self.proof_obligations
        )
        if not self.proof_obligations or keys != tuple(sorted(set(keys))):
            raise PartialSoundAuditInvariantViolation(
                "result obligations must be nonempty, unique, and sorted"
            )
        if any(
            item.partial_model_id != self.partial_model_id
            or item.thresholds_id != self.thresholds_id
            or item.contingent_plan_id != self.contingent_plan_id
            for item in self.proof_obligations
        ):
            raise PartialSoundAuditInvariantViolation(
                "result obligations do not bind this context"
            )
        expected_external_escape_ids = tuple(
            sorted(
                item.obligation_id
                for item in self.proof_obligations
                if item.remaining_horizon > 1
                and (
                    item.reachable_external_continuation_mass_upper > 0
                    or item.reachable_unknown_mass_upper > 0
                )
            )
        )
        if (
            expected_external_escape_ids
            != self.robust_bounds.external_escape_obligation_ids
        ):
            raise PartialSoundAuditInvariantViolation(
                "bounds external escapes do not match reachable obligations"
            )
        if type(self.outcome) is not PartialAuditOutcome:
            raise PartialSoundAuditInvariantViolation(
                "result outcome requires the exact enum"
            )
        obligation_ids = tuple(
            sorted(item.obligation_id for item in self.proof_obligations)
        )
        reachable_pairs = {
            (item.time_index, item.cell_id) for item in self.proof_obligations
        }
        expected_reachable_bound_ids = tuple(
            sorted(
                item.bound_row_id
                for item in self.robust_bounds.rows
                if (item.time_index, item.cell_id) in reachable_pairs
            )
        )
        expected_support_regret_ids = tuple(
            sorted(
                item.support_point_regret_row_id
                for item in self.robust_bounds.support_point_regret_rows
            )
        )
        if self.outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN:
            if (
                not self.robust_bounds.certified
                or type(self.certificate) is not PartialFixedPlanCertificateV1
                or self.failed_proof_frontier is not None
            ):
                raise PartialSoundAuditInvariantViolation(
                    "certified result requires exactly one certificate"
                )
            certificate = self.certificate
            if (
                certificate.partial_model_id != self.partial_model_id
                or certificate.thresholds_id != self.thresholds_id
                or certificate.contingent_plan_id != self.contingent_plan_id
                or certificate.bounds_id != self.robust_bounds.bounds_id
                or certificate.return_bound_proof_id
                != self.robust_bounds.return_bound_proof_id
                or certificate.obligation_ids != obligation_ids
                or certificate.reachable_bound_row_ids
                != expected_reachable_bound_ids
                or certificate.support_point_regret_row_ids
                != expected_support_regret_ids
                or certificate.maximum_support_point_normalized_regret
                != self.robust_bounds.maximum_support_point_normalized_regret
                or certificate.normalized_regret_tolerance
                != self.robust_bounds.normalized_regret_tolerance
                or certificate.policy_failure_upper
                != self.robust_bounds.policy_failure_upper
                or certificate.risk_tolerance != self.robust_bounds.risk_tolerance
                or certificate.external_coverage_certified
                != self.robust_bounds.external_coverage_certified
            ):
                raise PartialSoundAuditInvariantViolation(
                    "certificate does not bind the exact proof chain"
                )
        else:
            if (
                self.robust_bounds.certified
                or self.certificate is not None
                or type(self.failed_proof_frontier)
                is not PartialFailedProofFrontierV1
            ):
                raise PartialSoundAuditInvariantViolation(
                    "failed result requires exactly one nonauthorizing hint"
                )
            frontier = self.failed_proof_frontier
            if (
                frontier.partial_model_id != self.partial_model_id
                or frontier.thresholds_id != self.thresholds_id
                or frontier.contingent_plan_id != self.contingent_plan_id
                or frontier.bounds_id != self.robust_bounds.bounds_id
                or frontier.value_obligation_failed
                != (not self.robust_bounds.reward_obligation_certified)
                or frontier.risk_obligation_failed
                != (not self.robust_bounds.risk_obligation_certified)
                or frontier.external_coverage_failed
                != (not self.robust_bounds.external_coverage_certified)
                or not set(item.obligation_id for item in frontier.obligations)
                <= set(obligation_ids)
            ):
                raise PartialSoundAuditInvariantViolation(
                    "failed hint does not bind the exact proof chain"
                )
        if (
            self.dynamics_authority != "PORTABLE_PARTIAL_RAPM_ONLY"
            or self.external_transition_authority_calls != 0
            or self.ground_search_calls != 0
            or self.claim_kind != "ROBUST_FIXED_PLAN_AUDIT_ONLY"
            or self.failed_hint_authorizes_local_recovery is not False
            or self.causal_necessity_claimed is not False
            or self.causal_sufficiency_claimed is not False
            or self.optimality_claimed is not False
            or self.infeasibility_claimed is not False
        ):
            raise PartialSoundAuditInvariantViolation(
                "audit leaked authority or overclaimed its fixed-plan result"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_sound_audit_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "contingent_plan_id": self.contingent_plan_id,
            "robust_bounds": self.robust_bounds.to_document(),
            "proof_obligations": [
                item.to_document() for item in self.proof_obligations
            ],
            "outcome": self.outcome.value,
            "certificate": (
                None if self.certificate is None else self.certificate.to_document()
            ),
            "failed_proof_frontier": (
                None
                if self.failed_proof_frontier is None
                else self.failed_proof_frontier.to_document()
            ),
            "dynamics_authority": self.dynamics_authority,
            "external_transition_authority_calls": self.external_transition_authority_calls,
            "ground_search_calls": self.ground_search_calls,
            "claim_kind": self.claim_kind,
            "failed_hint_authorizes_local_recovery": (
                self.failed_hint_authorizes_local_recovery
            ),
            "causal_necessity_claimed": self.causal_necessity_claimed,
            "causal_sufficiency_claimed": self.causal_sufficiency_claimed,
            "optimality_claimed": self.optimality_claimed,
            "infeasibility_claimed": self.infeasibility_claimed,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class TypedPartialSoundAuditResultV2:
    """A source-complete binding around the byte-stable V0-043 result.

    The nested V1 result remains unchanged.  This wrapper makes the retained
    V0-045 synthesis authority, its certificate, coordinate proposal, build,
    and resulting portable model explicit in the audit's content identity.
    """

    observed_synthesis_result_id: str
    observed_synthesis_certificate_id: str
    coordinate_proposal_id: str
    partial_build_result_id: str
    partial_model_id: str
    audit_result: PartialSoundAuditResultV1
    source_authority_kind: str = "RETAINED_V0045_FULL_SYNTHESIS_REPLAY_V1"

    def __post_init__(self) -> None:
        for field in (
            "observed_synthesis_result_id",
            "observed_synthesis_certificate_id",
            "coordinate_proposal_id",
            "partial_build_result_id",
            "partial_model_id",
        ):
            _cid(getattr(self, field), f"typed audit {field}")
        if type(self.audit_result) is not PartialSoundAuditResultV1:
            raise PartialSoundAuditInvariantViolation(
                "typed audit wrapper rejects duck inner results"
            )
        if self.audit_result.partial_model_id != self.partial_model_id:
            raise PartialSoundAuditInvariantViolation(
                "typed audit wrapper/model identity mismatch"
            )
        if self.source_authority_kind != "RETAINED_V0045_FULL_SYNTHESIS_REPLAY_V1":
            raise PartialSoundAuditInvariantViolation(
                "typed audit wrapper relaxed its retained-source authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.typed_partial_sound_audit_result.v2",
            "schema_version": TYPED_AUDIT_SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "observed_synthesis_result_id": self.observed_synthesis_result_id,
            "observed_synthesis_certificate_id": (
                self.observed_synthesis_certificate_id
            ),
            "coordinate_proposal_id": self.coordinate_proposal_id,
            "partial_build_result_id": self.partial_build_result_id,
            "partial_model_id": self.partial_model_id,
            "audit_result": self.audit_result.to_document(),
            "source_authority_kind": self.source_authority_kind,
        }

    @property
    def result_id(self) -> str:
        return _content_id("typed_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class _Bound:
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction


def _cap_interval(
    partial_model: PortablePartialRAPMV1,
    weights: Mapping[str, Fraction],
) -> tuple[Fraction, Fraction]:
    caps = {item.name: item for item in partial_model.reward_feature_caps}
    lower = Fraction(0)
    upper = Fraction(0)
    for name, weight in weights.items():
        cap = caps[name]
        if weight >= 0:
            lower += weight * cap.lower
            upper += weight * cap.upper
        else:
            lower += weight * cap.upper
            upper += weight * cap.lower
    return lower, upper


def _reward_interval(
    ambiguity: AmbiguityPayloadV1,
    weights: Mapping[str, Fraction],
) -> tuple[Fraction, Fraction]:
    intervals = {item.name: item.interval for item in ambiguity.reward_intervals}
    lower = Fraction(0)
    upper = Fraction(0)
    for name, weight in weights.items():
        interval = intervals[name]
        if weight >= 0:
            lower += weight * interval.lower
            upper += weight * interval.upper
        else:
            lower += weight * interval.upper
            upper += weight * interval.lower
    return lower, upper


def _outside_bound(
    remaining: int,
    per_step_lower: Fraction,
    per_step_upper: Fraction,
    return_upper: Fraction,
) -> _Bound:
    lower = Fraction(0)
    upper = Fraction(0)
    for _ in range(remaining):
        lower = per_step_lower + min(Fraction(0), lower)
        upper = min(
            return_upper,
            per_step_upper + max(Fraction(0), upper),
        )
    if lower > return_upper:
        raise PartialSoundAuditInvariantViolation(
            "computed external lower exceeds the registered return upper"
        )
    return _Bound(
        lower,
        upper,
        Fraction(0),
        Fraction(1) if remaining else Fraction(0),
    )


def _validate_joint_simplex(ambiguity: AmbiguityPayloadV1) -> Fraction:
    constraint = ambiguity.joint_simplex_constraint
    if (
        constraint.unknown_atom_mass_sum != ambiguity.unknown_mass
        or constraint.known_continuation_mass
        != sum((mass for _, mass in ambiguity.known_successor_masses), Fraction(0))
        or constraint.known_terminal_mass != ambiguity.known_terminal_mass
        or constraint.total_probability_mass != 1
        or constraint.failure_implies_terminal is not True
        or constraint.independent_marginal_box_forbidden is not True
        or constraint.partition_semantics
        != "continuation_plus_terminal_equals_one_v1"
    ):
        raise PartialSoundAuditInvariantViolation(
            "partial model relaxed its joint simplex coupling"
        )
    kinds = {item.kind for item in ambiguity.joint_outcome_atoms}
    if not {
        JointOutcomeKind.TERMINAL_SUCCESS,
        JointOutcomeKind.TERMINAL_FAILURE,
    } <= kinds:
        raise PartialSoundAuditInvariantViolation(
            "joint simplex omits terminal success/failure atoms"
        )
    return constraint.unknown_atom_mass_sum


def _validate_return_bound_authority(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    partial_model: PortablePartialRAPMV1,
    thresholds: FrozenPartialAuditThresholdsV1,
) -> None:
    proof = thresholds.return_bound_proof
    if proof.proof_id not in REGISTERED_RETURN_BOUND_PROOF_IDS:
        raise PartialSoundAuditInvariantViolation(
            "return bound proof is not registered"
        )
    if (
        proof.structural_id != observation_log.structural_id
        or proof.environment_instance_id != observation_log.environment_instance_id
        or proof.observation_log_id != observation_log.log_id
        or proof.semantics_profile_id != semantics_profile.profile_id
        or proof.observation_authority_id != observation_authority.authority_id
        or proof.acquisition_manifest_id
        != observation_authority.acquisition_manifest.manifest_id
        or partial_model.observation_log_id != proof.observation_log_id
        or partial_model.semantics_profile_id != proof.semantics_profile_id
        or partial_model.observation_authority_id
        != proof.observation_authority_id
        or partial_model.acquisition_manifest_id
        != proof.acquisition_manifest_id
        or thresholds.reward_weights != proof.reward_weights
    ):
        raise PartialSoundAuditInvariantViolation(
            "return bound proof/source/threshold identity mismatch"
        )
    caps = tuple(
        (item.name, item.lower, item.upper)
        for item in semantics_profile.reward_feature_caps
    )
    if caps != (
        ("match", Fraction(0), Fraction(1)),
        ("terminal_clear", Fraction(0), Fraction(2)),
    ) or tuple(
        (item.name, item.lower, item.upper)
        for item in partial_model.reward_feature_caps
    ) != caps:
        raise PartialSoundAuditInvariantViolation(
            "registered return proof requires the canonical nonnegative reward caps"
        )


def _validate_inputs(
    partial_model: PortablePartialRAPMV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    contingent_plan: FrozenContingentAbstractPlanV1,
) -> tuple[
    dict[str, PartialCellV1],
    dict[tuple[str, str], tuple[PartialSemanticRealizationV1, ...]],
    dict[int, dict[str, str]],
    dict[str, str],
]:
    if type(partial_model) is not PortablePartialRAPMV1:
        raise PartialSoundAuditInvariantViolation(
            "audit rejects duck partial models"
        )
    if type(thresholds) is not FrozenPartialAuditThresholdsV1:
        raise PartialSoundAuditInvariantViolation("audit rejects duck thresholds")
    if type(contingent_plan) is not FrozenContingentAbstractPlanV1:
        raise PartialSoundAuditInvariantViolation("audit rejects duck plans")
    if (
        thresholds.partial_model_id != partial_model.model_id
        or contingent_plan.partial_model_id != partial_model.model_id
        or thresholds.horizon != contingent_plan.horizon
        or thresholds.horizon > partial_model.semantics_horizon_cap
    ):
        raise PartialSoundAuditInvariantViolation(
            "model/threshold/plan identity or horizon-scope mismatch"
        )
    if (
        partial_model.query_neutral is not True
        or partial_model.transition_closure_claimed is not False
        or partial_model.plan_certificate_claimed is not False
        or partial_model.infeasibility_claimed is not False
        or partial_model.acquisition_query_neutral_attested is not True
        or partial_model.preregistered_allowlisted_authority_required is not True
        or partial_model.observation_authority_id
        not in PREREGISTERED_OBSERVATION_AUTHORITY_IDS
    ):
        raise PartialSoundAuditInvariantViolation(
            "input does not satisfy the preregistered query-neutral partial-model scope"
        )
    if tuple(item.name for item in thresholds.reward_weights) != tuple(
        item.name for item in partial_model.reward_feature_caps
    ):
        raise PartialSoundAuditInvariantViolation(
            "reward weights must exactly cover registered feature caps"
        )
    active_cells = {
        item.cell_id: item
        for item in partial_model.cells
        if item.planning_kind is PlanningKind.ACTIVE
    }
    active_ids = set(active_cells)
    state_to_cell = {
        state_id: cell_id
        for cell_id, cell in active_cells.items()
        for state_id in cell.member_state_ids
    }
    if any(
        item.state_id not in state_to_cell
        for item in thresholds.initial_state_distribution
    ):
        raise PartialSoundAuditInvariantViolation(
            "initial support contains a non-active or unknown ground state"
        )
    allowed_destinations = active_ids | {partial_model.external_boundary_id}
    actions: dict[str, PartialSemanticActionV1] = {
        item.semantic_action_id: item for item in partial_model.semantic_actions
    }
    for ground_row in partial_model.ground_rows:
        _validate_joint_simplex(ground_row.ambiguity)
        if not {
            destination
            for destination, _ in ground_row.ambiguity.known_successor_masses
        } <= allowed_destinations:
            raise PartialSoundAuditInvariantViolation(
                "ground-row successor lies outside active cells plus external boundary"
            )
    realization_lists: dict[
        tuple[str, str], list[PartialSemanticRealizationV1]
    ] = {}
    for item in partial_model.semantic_realizations:
        _validate_joint_simplex(item.ambiguity)
        if not {
            destination for destination, _ in item.ambiguity.known_successor_masses
        } <= allowed_destinations:
            raise PartialSoundAuditInvariantViolation(
                "known successor lies outside active cells plus external boundary"
            )
        realization_lists.setdefault((item.cell_id, item.semantic_action_id), []).append(
            item
        )
    realizations = {
        key: tuple(sorted(value, key=lambda item: item.state_id))
        for key, value in realization_lists.items()
    }
    stage_maps: dict[int, dict[str, str]] = {}
    for stage in contingent_plan.stages:
        assignments = {item.cell_id: item.semantic_action_id for item in stage.assignments}
        if set(assignments) != active_ids:
            raise PartialSoundAuditInvariantViolation(
                "each plan stage must assign every active abstract cell"
            )
        for cell_id, action_id in assignments.items():
            action = actions.get(action_id)
            if action is None or action.cell_id != cell_id:
                raise PartialSoundAuditInvariantViolation(
                    "plan action lies outside its assigned cell"
                )
            state_rows = realizations.get((cell_id, action_id), ())
            if tuple(item.state_id for item in state_rows) != active_cells[
                cell_id
            ].member_state_ids:
                raise PartialSoundAuditInvariantViolation(
                    "semantic action lacks every cell-member realization"
                )
        stage_maps[stage.time_index] = assignments
    return active_cells, realizations, stage_maps, state_to_cell


def _realization_bound(
    ambiguity: AmbiguityPayloadV1,
    next_bounds: Mapping[str, _Bound],
    active_cell_ids: tuple[str, ...],
    external_boundary_id: str,
    outside: _Bound,
    weights: Mapping[str, Fraction],
    return_upper: Fraction,
) -> _Bound:
    reward_lower, reward_upper = _reward_interval(ambiguity, weights)
    value_lower = reward_lower
    value_upper = reward_upper
    failure_lower = ambiguity.known_failure_mass
    failure_upper = ambiguity.known_failure_mass
    for destination, mass in ambiguity.known_successor_masses:
        successor = (
            outside
            if destination == external_boundary_id
            else next_bounds[destination]
        )
        value_lower += mass * successor.reward_lower
        value_upper += mass * successor.reward_upper
        failure_lower += mass * successor.failure_lower
        failure_upper += mass * successor.failure_upper
    shared_unknown = _validate_joint_simplex(ambiguity)
    if shared_unknown:
        possible = (
            _Bound(Fraction(0), Fraction(0), Fraction(0), Fraction(1)),
            outside,
            *(next_bounds[cell_id] for cell_id in active_cell_ids),
        )
        value_lower += shared_unknown * min(
            item.reward_lower for item in possible
        )
        value_upper += shared_unknown * max(
            item.reward_upper for item in possible
        )
        # The same joint unknown mass chooses exactly one atom.  For the risk
        # upper it may all choose TERMINAL_FAILURE; it is never added again per
        # continuation destination.
        failure_upper += shared_unknown
    if value_lower > return_upper:
        raise PartialSoundAuditInvariantViolation(
            "policy lower exceeds the registered structural return upper"
        )
    return _Bound(
        value_lower,
        min(return_upper, value_upper),
        failure_lower,
        failure_upper,
    )


def _build_unrestricted_ground_upper(
    partial_model: PortablePartialRAPMV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    active_cells: Mapping[str, PartialCellV1],
) -> tuple[
    Fraction,
    dict[str, Fraction],
    tuple[UnrestrictedGroundUpperRowV1, ...],
]:
    """Upper-bound unrestricted ground control using every registered row."""

    weights = {item.name: item.weight for item in thresholds.reward_weights}
    per_step_lower, per_step_upper = _cap_interval(partial_model, weights)
    return_upper = thresholds.return_bound_proof.return_upper
    active_ids = tuple(sorted(active_cells))
    state_to_cell = {
        state_id: cell_id
        for cell_id, cell in active_cells.items()
        for state_id in cell.member_state_ids
    }
    rows_by_state: dict[str, list[Any]] = {state_id: [] for state_id in state_to_cell}
    for ground_row in partial_model.ground_rows:
        if ground_row.state_id in rows_by_state:
            rows_by_state[ground_row.state_id].append(ground_row)
    if any(not rows for rows in rows_by_state.values()):
        raise PartialSoundAuditInvariantViolation(
            "unrestricted upper lacks a complete active-state ground action catalogue"
        )
    cell_upper: dict[tuple[int, str], Fraction] = {}
    proof_rows: list[UnrestrictedGroundUpperRowV1] = []
    initial_state_upper: dict[str, Fraction] = {}
    for time_index in reversed(range(thresholds.horizon)):
        remaining = thresholds.horizon - time_index
        next_upper = {
            cell_id: (
                Fraction(0)
                if remaining == 1
                else cell_upper[(time_index + 1, cell_id)]
            )
            for cell_id in active_ids
        }
        outside = _outside_bound(
            remaining - 1,
            per_step_lower,
            per_step_upper,
            return_upper,
        )
        state_upper: dict[str, Fraction] = {}
        for state_id in sorted(rows_by_state):
            action_values: list[Fraction] = []
            cell_id = state_to_cell[state_id]
            for ground_row in sorted(
                rows_by_state[state_id], key=lambda item: item.ground_row_id
            ):
                ambiguity = ground_row.ambiguity
                _, value_upper = _reward_interval(ambiguity, weights)
                for destination, mass in ambiguity.known_successor_masses:
                    value_upper += mass * (
                        outside.reward_upper
                        if destination == partial_model.external_boundary_id
                        else next_upper[destination]
                    )
                shared_unknown = _validate_joint_simplex(ambiguity)
                if shared_unknown:
                    value_upper += shared_unknown * max(
                        Fraction(0),
                        outside.reward_upper,
                        *(next_upper[destination] for destination in active_ids),
                    )
                value_upper = min(return_upper, value_upper)
                action_values.append(value_upper)
                proof_rows.append(
                    UnrestrictedGroundUpperRowV1(
                        partial_model.model_id,
                        thresholds.thresholds_id,
                        time_index,
                        remaining,
                        state_id,
                        cell_id,
                        ground_row.ground_row_id,
                        ground_row.ground_action_id,
                        value_upper,
                    )
                )
            state_upper[state_id] = max(action_values)
        if time_index == 0:
            initial_state_upper = dict(state_upper)
        for cell_id, cell in active_cells.items():
            cell_upper[(time_index, cell_id)] = max(
                state_upper[state_id] for state_id in cell.member_state_ids
            )
    root_upper = sum(
        (
            item.probability * initial_state_upper[item.state_id]
            for item in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    return root_upper, initial_state_upper, tuple(
        sorted(
            proof_rows,
            key=lambda item: (
                item.time_index,
                item.state_id,
                item.ground_row_id,
            ),
        )
    )


def _build_bound_table(
    partial_model: PortablePartialRAPMV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    contingent_plan: FrozenContingentAbstractPlanV1,
    active_cells: Mapping[str, PartialCellV1],
    realizations: Mapping[
        tuple[str, str], tuple[PartialSemanticRealizationV1, ...]
    ],
    stage_maps: Mapping[int, Mapping[str, str]],
) -> tuple[dict[tuple[int, str], _Bound], tuple[PartialPolicyBoundRowV1, ...]]:
    weights = {item.name: item.weight for item in thresholds.reward_weights}
    per_step_lower, per_step_upper = _cap_interval(partial_model, weights)
    return_upper = thresholds.return_bound_proof.return_upper
    active_ids = tuple(sorted(active_cells))
    table: dict[tuple[int, str], _Bound] = {}
    rows: list[PartialPolicyBoundRowV1] = []
    zero_next = {
        cell_id: _Bound(Fraction(0), Fraction(0), Fraction(0), Fraction(0))
        for cell_id in active_ids
    }
    for time_index in reversed(range(thresholds.horizon)):
        remaining = thresholds.horizon - time_index
        next_by_cell = (
            zero_next
            if remaining == 1
            else {
                cell_id: table[(time_index + 1, cell_id)]
                for cell_id in active_ids
            }
        )
        outside = _outside_bound(
            remaining - 1,
            per_step_lower,
            per_step_upper,
            return_upper,
        )
        for cell_id in active_ids:
            action_id = stage_maps[time_index][cell_id]
            state_rows = realizations[(cell_id, action_id)]
            state_bounds = tuple(
                _realization_bound(
                    item.ambiguity,
                    next_by_cell,
                    active_ids,
                    partial_model.external_boundary_id,
                    outside,
                    weights,
                    return_upper,
                )
                for item in state_rows
            )
            bound = _Bound(
                min(item.reward_lower for item in state_bounds),
                max(item.reward_upper for item in state_bounds),
                min(item.failure_lower for item in state_bounds),
                max(item.failure_upper for item in state_bounds),
            )
            table[(time_index, cell_id)] = bound
            documents = tuple(item.ambiguity.to_document() for item in state_rows)
            rows.append(
                PartialPolicyBoundRowV1(
                    partial_model.model_id,
                    thresholds.thresholds_id,
                    contingent_plan.plan_id,
                    time_index,
                    remaining,
                    cell_id,
                    action_id,
                    tuple(item.state_id for item in state_rows),
                    tuple(
                        sorted(
                            {
                                row_id
                                for item in state_rows
                                for row_id in item.missing_ground_row_ids
                            }
                        )
                    ),
                    bound.reward_lower,
                    bound.reward_upper,
                    bound.failure_lower,
                    bound.failure_upper,
                    max(
                        item.ambiguity.joint_simplex_constraint.unknown_atom_mass_sum
                        for item in state_rows
                    ),
                    any(
                        item.ambiguity.joint_simplex_constraint.unknown_atom_mass_sum
                        > 0
                        or dict(item.ambiguity.known_successor_masses).get(
                            partial_model.external_boundary_id, Fraction(0)
                        )
                        > 0
                        for item in state_rows
                    ),
                    any(document != documents[0] for document in documents[1:]),
                )
            )
    return table, tuple(
        sorted(rows, key=lambda item: (item.time_index, item.cell_id))
    )


def _build_initial_support_bounds(
    partial_model: PortablePartialRAPMV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    active_cells: Mapping[str, PartialCellV1],
    realizations: Mapping[
        tuple[str, str], tuple[PartialSemanticRealizationV1, ...]
    ],
    stage_maps: Mapping[int, Mapping[str, str]],
    state_to_cell: Mapping[str, str],
    table: Mapping[tuple[int, str], _Bound],
) -> dict[str, _Bound]:
    """Evaluate time-zero rows at each exact rho0 ground support point."""

    weights = {item.name: item.weight for item in thresholds.reward_weights}
    per_step_lower, per_step_upper = _cap_interval(partial_model, weights)
    return_upper = thresholds.return_bound_proof.return_upper
    active_ids = tuple(sorted(active_cells))
    remaining = thresholds.horizon
    next_by_cell = {
        cell_id: (
            _Bound(Fraction(0), Fraction(0), Fraction(0), Fraction(0))
            if remaining == 1
            else table[(1, cell_id)]
        )
        for cell_id in active_ids
    }
    outside = _outside_bound(
        remaining - 1,
        per_step_lower,
        per_step_upper,
        return_upper,
    )
    result: dict[str, _Bound] = {}
    for support in thresholds.initial_state_distribution:
        cell_id = state_to_cell[support.state_id]
        action_id = stage_maps[0][cell_id]
        realization = next(
            item
            for item in realizations[(cell_id, action_id)]
            if item.state_id == support.state_id
        )
        result[support.state_id] = _realization_bound(
            realization.ambiguity,
            next_by_cell,
            active_ids,
            partial_model.external_boundary_id,
            outside,
            weights,
            return_upper,
        )
    return result


def _reachable_obligations(
    partial_model: PortablePartialRAPMV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    contingent_plan: FrozenContingentAbstractPlanV1,
    realizations: Mapping[
        tuple[str, str], tuple[PartialSemanticRealizationV1, ...]
    ],
    stage_maps: Mapping[int, Mapping[str, str]],
    state_to_cell: Mapping[str, str],
) -> tuple[
    tuple[StateActionTimeObligationV1, ...], tuple[tuple[int, str], ...]
]:
    active_ids = tuple(
        sorted(
            item.cell_id
            for item in partial_model.cells
            if item.planning_kind is PlanningKind.ACTIVE
        )
    )
    reach_upper: dict[str, Fraction] = {}
    for item in thresholds.initial_state_distribution:
        cell_id = state_to_cell[item.state_id]
        reach_upper[cell_id] = reach_upper.get(cell_id, Fraction(0)) + item.probability
    obligations: list[StateActionTimeObligationV1] = []
    reachable_pairs: list[tuple[int, str]] = []
    for time_index in range(thresholds.horizon):
        remaining = thresholds.horizon - time_index
        next_reach: dict[str, Fraction] = {}
        for cell_id in sorted(reach_upper):
            cell_mass = reach_upper[cell_id]
            if not cell_mass:
                continue
            reachable_pairs.append((time_index, cell_id))
            action_id = stage_maps[time_index][cell_id]
            state_rows = realizations[(cell_id, action_id)]
            documents = tuple(item.ambiguity.to_document() for item in state_rows)
            disagreement = any(
                document != documents[0] for document in documents[1:]
            )
            for item in state_rows:
                unknown = _validate_joint_simplex(item.ambiguity)
                known_external = dict(item.ambiguity.known_successor_masses).get(
                    partial_model.external_boundary_id, Fraction(0)
                )
                obligations.append(
                    StateActionTimeObligationV1(
                        partial_model.model_id,
                        thresholds.thresholds_id,
                        contingent_plan.plan_id,
                        time_index,
                        remaining,
                        item.state_id,
                        cell_id,
                        action_id,
                        item.support_ground_row_ids,
                        item.observed_ground_row_ids,
                        item.missing_ground_row_ids,
                        cell_mass,
                        unknown,
                        known_external,
                        cell_mass * unknown,
                        (
                            cell_mass * known_external
                            if remaining > 1
                            else Fraction(0)
                        ),
                        disagreement,
                        item.ambiguity.is_singleton,
                    )
                )
            if remaining == 1:
                continue
            # These are per-destination *reachability uppers*.  They may share
            # the same unknown mass, so the map is never interpreted as a
            # probability distribution or used in Bellman arithmetic.
            for destination in active_ids:
                destination_upper = max(
                    dict(item.ambiguity.known_successor_masses).get(
                        destination, Fraction(0)
                    )
                    + _validate_joint_simplex(item.ambiguity)
                    for item in state_rows
                )
                if destination_upper:
                    next_reach[destination] = min(
                        Fraction(1),
                        next_reach.get(destination, Fraction(0))
                        + cell_mass * destination_upper,
                    )
        reach_upper = next_reach
        if not reach_upper:
            break
    return (
        tuple(
            sorted(
                obligations,
                key=lambda item: (
                    item.time_index,
                    item.cell_id,
                    item.state_id,
                    item.semantic_action_id,
                ),
            )
        ),
        tuple(sorted(set(reachable_pairs))),
    )


def _verified_partial_model(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    partial_build_result: ObservationPartialRAPMBuildV1,
) -> PortablePartialRAPMV1:
    failures = verify_observation_partial_rapm_v1(
        observation_log,
        coordinate_proposal,
        semantics_profile,
        observation_authority,
        partial_build_result,
    )
    if failures:
        raise PartialSoundAuditInvariantViolation(
            "partial RAPM source graph failed trusted reconstruction: "
            + ",".join(failures)
        )
    return partial_build_result.model


def audit_partial_fixed_plan_v1(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    partial_build_result: ObservationPartialRAPMBuildV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    contingent_plan: FrozenContingentAbstractPlanV1,
) -> PartialSoundAuditResultV1:
    """Verify the source graph, then certify or emit a nonauthorizing hint."""

    # The V0-042 source graph is always reconstructed before any threshold or
    # plan field is used.  Thus a duck query object cannot trigger callbacks
    # before the registered dynamics authority is checked.
    partial_model = _verified_partial_model(
        observation_log,
        coordinate_proposal,
        semantics_profile,
        observation_authority,
        partial_build_result,
    )
    return _audit_verified_partial_model_v1(
        partial_model,
        observation_log,
        semantics_profile,
        observation_authority,
        thresholds,
        contingent_plan,
    )


def _audit_verified_partial_model_v1(
    partial_model: PortablePartialRAPMV1,
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    contingent_plan: FrozenContingentAbstractPlanV1,
) -> PartialSoundAuditResultV1:
    """Run the unchanged V0-043 proof after a public source verifier passes."""

    active_cells, realizations, stage_maps, state_to_cell = _validate_inputs(
        partial_model, thresholds, contingent_plan
    )
    _validate_return_bound_authority(
        observation_log,
        semantics_profile,
        observation_authority,
        partial_model,
        thresholds,
    )
    table, rows = _build_bound_table(
        partial_model,
        thresholds,
        contingent_plan,
        active_cells,
        realizations,
        stage_maps,
    )
    initial_bounds = _build_initial_support_bounds(
        partial_model,
        thresholds,
        active_cells,
        realizations,
        stage_maps,
        state_to_cell,
        table,
    )
    obligations, reachable_pairs = _reachable_obligations(
        partial_model,
        thresholds,
        contingent_plan,
        realizations,
        stage_maps,
        state_to_cell,
    )
    unrestricted_upper, initial_state_unrestricted_upper, unrestricted_rows = (
        _build_unrestricted_ground_upper(
            partial_model, thresholds, active_cells
        )
    )
    return_upper = thresholds.return_bound_proof.return_upper
    support_regret_rows = tuple(
        InitialSupportPointRegretRowV1(
            partial_model.model_id,
            thresholds.thresholds_id,
            contingent_plan.plan_id,
            thresholds.return_bound_proof.proof_id,
            support.state_id,
            state_to_cell[support.state_id],
            support.probability,
            initial_state_unrestricted_upper[support.state_id],
            initial_bounds[support.state_id].reward_lower,
            initial_state_unrestricted_upper[support.state_id]
            - initial_bounds[support.state_id].reward_lower,
            return_upper,
            (
                initial_state_unrestricted_upper[support.state_id]
                - initial_bounds[support.state_id].reward_lower
            )
            / return_upper,
            thresholds.normalized_regret_tolerance,
            (
                initial_state_unrestricted_upper[support.state_id]
                - initial_bounds[support.state_id].reward_lower
            )
            / return_upper
            <= thresholds.normalized_regret_tolerance,
        )
        for support in thresholds.initial_state_distribution
    )
    root_reward_lower = sum(
        (
            support.probability
            * initial_bounds[support.state_id].reward_lower
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_reward_upper = min(
        return_upper,
        sum(
            (
                support.probability
                * initial_bounds[support.state_id].reward_upper
                for support in thresholds.initial_state_distribution
            ),
            Fraction(0),
        ),
    )
    root_failure_lower = sum(
        (
            support.probability
            * initial_bounds[support.state_id].failure_lower
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_failure_upper = sum(
        (
            support.probability
            * initial_bounds[support.state_id].failure_upper
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    raw_distribution_regret = unrestricted_upper - root_reward_lower
    external_escape_obligation_ids = tuple(
        sorted(
            item.obligation_id
            for item in obligations
            if item.remaining_horizon > 1
            and (
                item.reachable_external_continuation_mass_upper > 0
                or item.reachable_unknown_mass_upper > 0
            )
        )
    )
    bounds = PartialFixedPlanRobustBoundsV1(
        partial_model.model_id,
        thresholds.thresholds_id,
        contingent_plan.plan_id,
        thresholds.return_bound_proof.proof_id,
        rows,
        unrestricted_rows,
        support_regret_rows,
        unrestricted_upper,
        root_reward_lower,
        root_reward_upper,
        root_failure_lower,
        root_failure_upper,
        raw_distribution_regret,
        raw_distribution_regret / return_upper,
        return_upper,
        thresholds.normalized_regret_tolerance,
        thresholds.risk_tolerance,
        all(item.obligation_certified for item in support_regret_rows),
        root_failure_upper <= thresholds.risk_tolerance,
        not external_escape_obligation_ids,
        external_escape_obligation_ids,
        len(reachable_pairs),
    )
    if bounds.certified:
        reachable_set = set(reachable_pairs)
        certificate = PartialFixedPlanCertificateV1(
            partial_model.model_id,
            thresholds.thresholds_id,
            contingent_plan.plan_id,
            bounds.bounds_id,
            bounds.return_bound_proof_id,
            tuple(sorted(item.obligation_id for item in obligations)),
            tuple(
                sorted(
                    item.bound_row_id
                    for item in rows
                    if (item.time_index, item.cell_id) in reachable_set
                )
            ),
            tuple(
                sorted(
                    item.support_point_regret_row_id
                    for item in support_regret_rows
                )
            ),
            bounds.maximum_support_point_normalized_regret,
            bounds.normalized_regret_tolerance,
            bounds.policy_failure_upper,
            bounds.risk_tolerance,
            bounds.external_coverage_certified,
        )
        return PartialSoundAuditResultV1(
            partial_model.model_id,
            thresholds.thresholds_id,
            contingent_plan.plan_id,
            bounds,
            obligations,
            PartialAuditOutcome.CERTIFIED_FIXED_PLAN,
            certificate,
            None,
        )
    external_escape = tuple(
        item
        for item in obligations
        if item.obligation_id in set(external_escape_obligation_ids)
    )
    unresolved = tuple(
        item
        for item in obligations
        if item.unresolved_mass_upper > 0 or item.representative_disagreement
    )
    if external_escape:
        earliest = min(item.time_index for item in external_escape)
        frontier_rows = tuple(
            item for item in external_escape if item.time_index == earliest
        )
        reason = FailedProofReason.EXTERNAL_COVERAGE_ESCAPE
    elif unresolved:
        earliest = min(item.time_index for item in unresolved)
        frontier_rows = tuple(
            item for item in unresolved if item.time_index == earliest
        )
        reason = FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION
    else:
        earliest = min(item.time_index for item in obligations)
        frontier_rows = tuple(
            item for item in obligations if item.time_index == earliest
        )
        reason = FailedProofReason.KNOWN_FIXED_PLAN_THRESHOLD_FAILURE
    frontier = PartialFailedProofFrontierV1(
        partial_model.model_id,
        thresholds.thresholds_id,
        contingent_plan.plan_id,
        bounds.bounds_id,
        earliest,
        thresholds.horizon - earliest,
        frontier_rows,
        sum((item.unresolved_mass_upper for item in frontier_rows), Fraction(0)),
        not bounds.reward_obligation_certified,
        not bounds.risk_obligation_certified,
        not bounds.external_coverage_certified,
        reason,
    )
    return PartialSoundAuditResultV1(
        partial_model.model_id,
        thresholds.thresholds_id,
        contingent_plan.plan_id,
        bounds,
        obligations,
        PartialAuditOutcome.FAILED_PROOF_FRONTIER,
        None,
        frontier,
    )


def _verified_observed_typed_model_v2(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: observed_synthesis_v1.ObservedTypedPartialRAPMResultV1,
) -> PortablePartialRAPMV1:
    """Retain and replay the complete V0-045 authority before model access."""

    if (
        type(observed_synthesis_result)
        is not observed_synthesis_v1.ObservedTypedPartialRAPMResultV1
    ):
        raise PartialSoundAuditInvariantViolation(
            "typed audit rejects duck V0-045 synthesis results"
        )
    try:
        failures = observed_synthesis_v1.verify_observed_lmb_partial_rapm_v1(
            observation_log,
            semantics_profile,
            observation_authority,
            observed_synthesis_result,
        )
    except (
        observed_synthesis_v1.ObservedTypedCoordinateInvariantViolation,
        ObservationPartialRAPMInvariantViolation,
    ) as error:
        raise PartialSoundAuditInvariantViolation(
            "typed partial RAPM failed retained V0-045 reconstruction: "
            + str(error)
        ) from error
    if failures:
        raise PartialSoundAuditInvariantViolation(
            "typed partial RAPM failed retained V0-045 reconstruction: "
            + ",".join(failures)
        )

    proposal = observed_synthesis_result.coordinate_proposal
    build = observed_synthesis_result.partial_build_result
    model = build.model
    certificate = observed_synthesis_result.certificate
    if (
        certificate.coordinate_proposal_id != proposal.proposal_id
        or certificate.partial_build_result_id != build.result_id
        or certificate.partial_model_id != model.model_id
        or build.coordinate_proposal_id != proposal.proposal_id
        or build.model.coordinate_proposal_id != proposal.proposal_id
    ):
        raise PartialSoundAuditInvariantViolation(
            "typed V0-045 result/proposal/build/model identity chain mismatch"
        )
    return model


def audit_partial_fixed_plan_from_observed_synthesis_v2(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: observed_synthesis_v1.ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    contingent_plan: FrozenContingentAbstractPlanV1,
) -> TypedPartialSoundAuditResultV2:
    """Audit one plan only after replaying the full retained V0-045 chain."""

    partial_model = _verified_observed_typed_model_v2(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
    )
    audit_result = _audit_verified_partial_model_v1(
        partial_model,
        observation_log,
        semantics_profile,
        observation_authority,
        thresholds,
        contingent_plan,
    )
    return TypedPartialSoundAuditResultV2(
        observed_synthesis_result.result_id,
        observed_synthesis_result.certificate.certificate_id,
        observed_synthesis_result.coordinate_proposal.proposal_id,
        observed_synthesis_result.partial_build_result.result_id,
        partial_model.model_id,
        audit_result,
    )


def verify_partial_fixed_plan_audit_from_observed_synthesis_v2(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: observed_synthesis_v1.ObservedTypedPartialRAPMResultV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    contingent_plan: FrozenContingentAbstractPlanV1,
    claimed_result: TypedPartialSoundAuditResultV2,
) -> TypedPartialSoundAuditResultV2:
    """Replay the complete V0-045-to-V0-043 source and proof chain."""

    if type(claimed_result) is not TypedPartialSoundAuditResultV2:
        raise PartialSoundAuditInvariantViolation(
            "typed audit verifier rejects duck result artifacts"
        )
    replayed = audit_partial_fixed_plan_from_observed_synthesis_v2(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        thresholds,
        contingent_plan,
    )
    if claimed_result.to_document() != replayed.to_document():
        raise PartialSoundAuditInvariantViolation(
            "claimed typed partial audit differs from retained full-chain replay"
        )
    return replayed


def verify_partial_fixed_plan_audit_v1(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    partial_build_result: ObservationPartialRAPMBuildV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    contingent_plan: FrozenContingentAbstractPlanV1,
    claimed_result: PartialSoundAuditResultV1,
) -> PartialSoundAuditResultV1:
    """Recompute every bound and hint, rejecting content-inconsistent evidence."""

    if type(claimed_result) is not PartialSoundAuditResultV1:
        raise PartialSoundAuditInvariantViolation(
            "verifier rejects duck result artifacts"
        )
    replayed = audit_partial_fixed_plan_v1(
        observation_log,
        coordinate_proposal,
        semantics_profile,
        observation_authority,
        partial_build_result,
        thresholds,
        contingent_plan,
    )
    if claimed_result.to_document() != replayed.to_document():
        raise PartialSoundAuditInvariantViolation(
            "claimed partial audit differs from trusted exact replay"
        )
    return replayed


__all__ = [
    "CANONICAL_LMB_N6_ACQUISITION_MANIFEST_ID",
    "CANONICAL_LMB_N6_ENVIRONMENT_INSTANCE_ID",
    "CANONICAL_LMB_N6_OBSERVATION_AUTHORITY_ID",
    "CANONICAL_LMB_N6_OBSERVATION_LOG_ID",
    "CANONICAL_LMB_N6_SEMANTICS_PROFILE_ID",
    "CANONICAL_LMB_N6_STRUCTURAL_ID",
    "ContingentPlanAssignmentV1",
    "ContingentPlanStageV1",
    "FailedProofReason",
    "FrozenContingentAbstractPlanV1",
    "FrozenPartialAuditThresholdsV1",
    "InitialStateMassV1",
    "InitialSupportPointRegretRowV1",
    "PartialAuditOutcome",
    "PartialFailedProofFrontierV1",
    "PartialFixedPlanCertificateV1",
    "PartialFixedPlanRobustBoundsV1",
    "PartialPolicyBoundRowV1",
    "PartialSoundAuditInvariantViolation",
    "PartialSoundAuditResultV1",
    "REGISTERED_NORMALIZED_REGRET_TOLERANCES",
    "REGISTERED_RETURN_BOUND_PROOF_IDS",
    "REGISTERED_RISK_TOLERANCES",
    "RegisteredReturnBoundProofV1",
    "RewardWeightV1",
    "StateActionTimeObligationV1",
    "TYPED_AUDIT_SCHEMA_VERSION",
    "TypedPartialSoundAuditResultV2",
    "UnrestrictedGroundUpperRowV1",
    "audit_partial_fixed_plan_v1",
    "audit_partial_fixed_plan_from_observed_synthesis_v2",
    "canonical_lmb_n6_return_bound_proof_v1",
    "verify_partial_fixed_plan_audit_v1",
    "verify_partial_fixed_plan_audit_from_observed_synthesis_v2",
]
