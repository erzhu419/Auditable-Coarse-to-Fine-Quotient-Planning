"""Matched end-to-end adaptive-model versus cold direct-ground workload.

V0-061 replaces V0-060's six-row abstract control with a genuine direct
ground planning arm.  Both arms receive the same three structural contexts
and six query occurrences.  The adaptive arm pays once per context to repair
an initially uncertifiable partial RAPM, then reuses that immutable model for
the second query.  The direct arm starts cold for every occurrence, samples
every reachable ground state-action row, plans in ground coordinates, and
discards its occurrence-local statistical model.

Every stochastic draw is embedded in a packed replayable trace.  Exact
probabilities are available only to the acquisition authority and standalone
verifier.  Production model building and planning accept no kernel.  The
result measures a finite registered workload; it does not claim automatic
coordinate discovery, a general sample-efficiency theorem, or a sample-tax
reduction operator.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
import hashlib
import inspect
import math
from itertools import product
from typing import Any, Mapping

from acfqp.core import Outcome
from acfqp.domains.g2048 import (
    G2048Action,
    G2048State,
    G2048Status,
)
from acfqp.domains.semantic import (
    G2048RelativeSurvivorAdapter,
    G2048RelativeSurvivorLabel,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.planning.ground import evaluate_ground_policy, solve_ground_pareto
from acfqp.planning.policy import FiniteHorizonPolicy
import acfqp.raw_multicontext_acquisition_v1 as raw


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.25.0"
PROFILE_KEY = "g2048_matched_adaptive_vs_cold_direct_ground_v0"
SUCCESS_STATUS = (
    "CERTIFIED_REGISTERED_MATCHED_END_TO_END_ACQUISITION_WORKLOAD_CONTROL"
)
DIRECT_CERTIFIED_STATUS = "CERTIFIED_COLD_DIRECT_GROUND_STATISTICAL_PLAN"

DIRECT_SAMPLE_COUNT_PER_ROW = 24_576
DIRECT_DRAW_BLOCK_SIZE = 4_096
DIRECT_BLOCKS_PER_ROW = (
    DIRECT_SAMPLE_COUNT_PER_ROW // DIRECT_DRAW_BLOCK_SIZE
)
DIRECT_HOEFFDING_RADIUS = Fraction(1, 64)
DIRECT_PER_OBLIGATION_TAIL_UPPER = Fraction(1, 50_000)
DIRECT_POINT_STATE_TIME_PAIRS = 6
DIRECT_POINT_ACTION_ROWS = 18
DIRECT_POINT_H1_ACTION_ROWS = 16
DIRECT_POINT_ROOT_ACTION_ROWS = 2
DIRECT_POINT_ROOT_CANDIDATES = 2
DIRECT_POINT_OBLIGATIONS = 20
DIRECT_UNIFORM_STATE_TIME_PAIRS = 20
DIRECT_UNIFORM_ACTION_ROWS = 48
DIRECT_UNIFORM_H1_ACTION_ROWS = 32
DIRECT_UNIFORM_ROOT_ACTION_ROWS = 16
DIRECT_UNIFORM_ROOT_CANDIDATES = 256
DIRECT_UNIFORM_OBLIGATIONS = 64
DIRECT_TOTAL_STATE_TIME_PAIRS = 3 * (
    DIRECT_POINT_STATE_TIME_PAIRS + DIRECT_UNIFORM_STATE_TIME_PAIRS
)
DIRECT_TOTAL_ACTION_ROWS = 3 * (
    DIRECT_POINT_ACTION_ROWS + DIRECT_UNIFORM_ACTION_ROWS
)
DIRECT_TOTAL_H1_ACTION_ROWS = 3 * (
    DIRECT_POINT_H1_ACTION_ROWS + DIRECT_UNIFORM_H1_ACTION_ROWS
)
DIRECT_TOTAL_ROOT_ACTION_ROWS = 3 * (
    DIRECT_POINT_ROOT_ACTION_ROWS + DIRECT_UNIFORM_ROOT_ACTION_ROWS
)
DIRECT_TOTAL_ROOT_CANDIDATES = 3 * (
    DIRECT_POINT_ROOT_CANDIDATES + DIRECT_UNIFORM_ROOT_CANDIDATES
)
DIRECT_TOTAL_OBLIGATIONS = 3 * (
    DIRECT_POINT_OBLIGATIONS + DIRECT_UNIFORM_OBLIGATIONS
)
DIRECT_TOTAL_DRAWS = (
    DIRECT_TOTAL_ACTION_ROWS * DIRECT_SAMPLE_COUNT_PER_ROW
)
ADAPTIVE_TOTAL_DRAWS = raw.ADAPTIVE_TOTAL_DRAWS
ADAPTIVE_TOTAL_OBLIGATIONS = (
    2 * raw.CONTEXT_COUNT * raw.ADAPTIVE_ROWS_PER_CONTEXT
)
COMBINED_FAMILY_TAIL_UPPER = (
    ADAPTIVE_TOTAL_OBLIGATIONS * raw.PER_COORDINATE_TAIL_UPPER
    + DIRECT_TOTAL_OBLIGATIONS * DIRECT_PER_OBLIGATION_TAIL_UPPER
)
COMBINED_CONFIDENCE_LOWER = 1 - COMBINED_FAMILY_TAIL_UPPER
REGISTERED_DRAW_RATIO = Fraction(
    DIRECT_TOTAL_DRAWS, ADAPTIVE_TOTAL_DRAWS
)

IMPLEMENTATION_SHA256 = (
    "625cfed523999c64e8d2e10901a4d371a4671f8efec49b9d8416d9af560b0394"
)

DOMAIN_TAGS = {
    "profile": "acfqp:matched-end-to-end-profile:v1",
    "preregistration": "acfqp:matched-end-to-end-preregistration:v1",
    "adaptive_context": "acfqp:matched-adaptive-context-evidence:v1",
    "direct_atom": "acfqp:direct-ground-outcome-atom:v1",
    "direct_codebook": "acfqp:direct-ground-row-codebook:v1",
    "direct_block": "acfqp:direct-ground-draw-block:v1",
    "direct_row_log": "acfqp:direct-ground-row-log:v1",
    "direct_occurrence_evidence": (
        "acfqp:direct-ground-occurrence-evidence:v1"
    ),
    "evidence_bundle": "acfqp:matched-end-to-end-evidence-bundle:v1",
    "h1_estimate": "acfqp:direct-ground-h1-estimate:v1",
    "h1_decision": "acfqp:direct-ground-h1-decision:v1",
    "root_estimate": "acfqp:direct-ground-root-estimate:v1",
    "root_candidate": "acfqp:direct-ground-root-candidate:v1",
    "ground_decision": "acfqp:direct-ground-policy-decision:v1",
    "ground_policy": "acfqp:direct-ground-statistical-policy:v1",
    "direct_proof": "acfqp:direct-ground-statistical-proof:v1",
    "adaptive_model_result": "acfqp:matched-adaptive-model-result:v1",
    "adaptive_result": "acfqp:matched-adaptive-occurrence-result:v1",
    "occurrence_result": "acfqp:matched-end-to-end-occurrence-result:v1",
    "work": "acfqp:matched-end-to-end-work:v1",
    "campaign": "acfqp:matched-end-to-end-campaign:v1",
    "exact_comparator": "acfqp:matched-end-to-end-exact-comparator:v1",
    "verification": "acfqp:matched-end-to-end-verification:v1",
}


class MatchedEndToEndInvariantViolation(ValueError):
    """A V0-061 authority, trace, plan, or certificate is inconsistent."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role].encode("utf-8")
    except (KeyError, TypeError, ValueError) as error:
        raise MatchedEndToEndInvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise MatchedEndToEndInvariantViolation(
            f"{field_name} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _exact_tuple(
    value: Any, item_type: type, field_name: str
) -> tuple[Any, ...]:
    if type(value) is not tuple or any(
        type(item) is not item_type for item in value
    ):
        raise MatchedEndToEndInvariantViolation(
            f"{field_name} rejects nested runtime substitutions"
        )
    return value


def _runtime_shape(claimed: Any, expected: Any, path: str) -> None:
    if type(claimed) is not type(expected):
        raise MatchedEndToEndInvariantViolation(
            f"{path} contains a nested runtime substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise MatchedEndToEndInvariantViolation(
                f"{path} length changed"
            )
        for index, (left, right) in enumerate(zip(claimed, expected)):
            _runtime_shape(left, right, f"{path}[{index}]")
        return
    if is_dataclass(expected):
        for field in fields(type(expected)):
            _runtime_shape(
                object.__getattribute__(claimed, field.name),
                object.__getattribute__(expected, field.name),
                f"{path}.{field.name}",
            )


def _state_key(
    remaining: int, board: tuple[int, ...], status: str
) -> tuple[int, tuple[int, ...], str]:
    return (remaining, board, status)


def _action_tuple(action: G2048Action) -> tuple[int, int, int]:
    return (action.first, action.second, action.survivor)


def _action_from_tuple(value: tuple[int, int, int]) -> G2048Action:
    return G2048Action(value[0], value[1], value[2])


def _normalized_reward(outcome: Outcome[G2048State]) -> Fraction:
    return dict(outcome.reward_features)["merge"] / 2


@dataclass(frozen=True, slots=True)
class MatchedAcquisitionProfileV1:
    adaptive_profile_id: str
    direct_sample_count_per_row: int = DIRECT_SAMPLE_COUNT_PER_ROW
    direct_draw_block_size: int = DIRECT_DRAW_BLOCK_SIZE
    direct_radius: Fraction = DIRECT_HOEFFDING_RADIUS
    direct_exponent: Fraction = Fraction(12)
    direct_taylor_degree: int = 13
    direct_exponential_denominator_lower: int = 100_000
    direct_per_obligation_tail_upper: Fraction = (
        DIRECT_PER_OBLIGATION_TAIL_UPPER
    )
    adaptive_obligations: int = ADAPTIVE_TOTAL_OBLIGATIONS
    direct_obligations: int = DIRECT_TOTAL_OBLIGATIONS
    combined_family_tail_upper: Fraction = COMBINED_FAMILY_TAIL_UPPER
    combined_confidence_lower: Fraction = COMBINED_CONFIDENCE_LOWER
    direct_seed: str = "acfqp-v0061-cold-direct-ground-seed-v1"
    direct_counter_uniform_protocol: str = (
        "sha256_counter_uint256_ceil_cdf_v1"
    )

    def __post_init__(self) -> None:
        _cid(self.adaptive_profile_id, "matched adaptive profile")
        taylor = sum(
            (
                Fraction(12**index, math.factorial(index))
                for index in range(self.direct_taylor_degree + 1)
            ),
            Fraction(0),
        )
        if (
            self.adaptive_profile_id
            != raw.RawAcquisitionProfileV1().profile_id
            or self.direct_sample_count_per_row
            != DIRECT_SAMPLE_COUNT_PER_ROW
            or self.direct_draw_block_size != DIRECT_DRAW_BLOCK_SIZE
            or self.direct_sample_count_per_row
            % self.direct_draw_block_size
            or self.direct_radius != Fraction(1, 64)
            or self.direct_exponent
            != 2
            * self.direct_sample_count_per_row
            * self.direct_radius**2
            or self.direct_exponent != 12
            or self.direct_taylor_degree != 13
            or taylor <= self.direct_exponential_denominator_lower
            or self.direct_exponential_denominator_lower != 100_000
            or self.direct_per_obligation_tail_upper
            != Fraction(2, self.direct_exponential_denominator_lower)
            or self.direct_per_obligation_tail_upper
            != DIRECT_PER_OBLIGATION_TAIL_UPPER
            or self.adaptive_obligations != 18
            or self.direct_obligations != 252
            or self.combined_family_tail_upper
            != self.adaptive_obligations
            * raw.PER_COORDINATE_TAIL_UPPER
            + self.direct_obligations
            * self.direct_per_obligation_tail_upper
            or self.combined_family_tail_upper
            != Fraction(783, 43_750)
            or self.combined_confidence_lower
            != 1 - self.combined_family_tail_upper
            or self.combined_confidence_lower
            != Fraction(42_967, 43_750)
            or self.combined_confidence_lower <= Fraction(49, 50)
            or self.direct_seed
            != "acfqp-v0061-cold-direct-ground-seed-v1"
            or self.direct_counter_uniform_protocol
            != "sha256_counter_uint256_ceil_cdf_v1"
        ):
            raise MatchedEndToEndInvariantViolation(
                "matched acquisition/calibration profile changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_end_to_end_acquisition_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "adaptive_profile_id": self.adaptive_profile_id,
            "direct_sample_count_per_row": (
                self.direct_sample_count_per_row
            ),
            "direct_draw_block_size": self.direct_draw_block_size,
            "direct_radius": _fdoc(self.direct_radius),
            "direct_exponent": _fdoc(self.direct_exponent),
            "direct_taylor_degree": self.direct_taylor_degree,
            "direct_exponential_denominator_lower": (
                self.direct_exponential_denominator_lower
            ),
            "direct_per_obligation_tail_upper": _fdoc(
                self.direct_per_obligation_tail_upper
            ),
            "adaptive_obligations": self.adaptive_obligations,
            "direct_obligations": self.direct_obligations,
            "combined_family_tail_upper": _fdoc(
                self.combined_family_tail_upper
            ),
            "combined_confidence_lower": _fdoc(
                self.combined_confidence_lower
            ),
            "direct_seed": self.direct_seed,
            "direct_counter_uniform_protocol": (
                self.direct_counter_uniform_protocol
            ),
            "same_error_radius": True,
            "family_multiplicity_adjusted_sample_counts": True,
            "individual_draws_required": True,
        }

    @property
    def profile_id(self) -> str:
        return _content_id("profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


@dataclass(frozen=True, slots=True)
class MatchedWorkloadPreregistrationV1:
    source_preregistration: raw.RawMultiContextPreregistrationV1
    acquisition_profile: MatchedAcquisitionProfileV1
    direct_route_semantics: str = (
        "cold_occurrence_local_ground_statistical_planning"
    )
    direct_known_finite_support_and_action_catalogue: bool = True
    direct_cross_occurrence_model_reuse_forbidden: bool = True
    adaptive_context_model_reuse_registered: bool = True
    prospective_evidence_ids_absent: bool = True
    prospective_plan_ids_absent: bool = True
    automatic_coordinate_discovery_claimed: bool = False
    sample_tax_operator_registered: bool = False
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.source_preregistration)
            is not raw.RawMultiContextPreregistrationV1
            or type(self.acquisition_profile)
            is not MatchedAcquisitionProfileV1
        ):
            raise MatchedEndToEndInvariantViolation(
                "matched preregistration rejects substituted authorities"
            )
        expected_source = raw.preregister_raw_multicontext_campaign_v1(
            raw.registered_g2048_d4_statistical_catalogue_v1()
        )
        if (
            self.source_preregistration.to_document()
            != expected_source.to_document()
            or self.acquisition_profile
            != MatchedAcquisitionProfileV1(
                expected_source.acquisition_profile.profile_id
            )
            or self.direct_route_semantics
            != "cold_occurrence_local_ground_statistical_planning"
            or self.direct_known_finite_support_and_action_catalogue is not True
            or self.direct_cross_occurrence_model_reuse_forbidden is not True
            or self.adaptive_context_model_reuse_registered is not True
            or self.prospective_evidence_ids_absent is not True
            or self.prospective_plan_ids_absent is not True
            or self.automatic_coordinate_discovery_claimed is not False
            or self.sample_tax_operator_registered is not False
            or self.official_execution_allowed is not False
        ):
            raise MatchedEndToEndInvariantViolation(
                "matched preregistration scope or chronology changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_end_to_end_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "implementation_sha256": IMPLEMENTATION_SHA256,
            "source_preregistration": (
                self.source_preregistration.to_document()
            ),
            "acquisition_profile": self.acquisition_profile.to_document(),
            "direct_route_semantics": self.direct_route_semantics,
            "direct_known_finite_support_and_action_catalogue": (
                self.direct_known_finite_support_and_action_catalogue
            ),
            "direct_cross_occurrence_model_reuse_forbidden": (
                self.direct_cross_occurrence_model_reuse_forbidden
            ),
            "adaptive_context_model_reuse_registered": (
                self.adaptive_context_model_reuse_registered
            ),
            "prospective_evidence_ids_absent": (
                self.prospective_evidence_ids_absent
            ),
            "prospective_plan_ids_absent": (
                self.prospective_plan_ids_absent
            ),
            "automatic_coordinate_discovery_claimed": (
                self.automatic_coordinate_discovery_claimed
            ),
            "sample_tax_operator_registered": (
                self.sample_tax_operator_registered
            ),
            "official_execution_allowed": self.official_execution_allowed,
        }

    @property
    def preregistration_id(self) -> str:
        return _content_id("preregistration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "preregistration_id": self.preregistration_id,
        }


def preregister_matched_end_to_end_workload_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
) -> MatchedWorkloadPreregistrationV1:
    source = raw.preregister_raw_multicontext_campaign_v1(catalogue)
    return MatchedWorkloadPreregistrationV1(
        source,
        MatchedAcquisitionProfileV1(
            source.acquisition_profile.profile_id
        ),
    )


@dataclass(frozen=True, slots=True)
class MatchedAdaptiveContextEvidenceV1:
    matched_preregistration_id: str
    context: raw.RawSafeChainStructuralContextV1
    initial_model: raw.RawPartialStatisticalModelV1
    failed_proof: raw.RawPartialPlanProofV1
    authorization: raw.RawAdaptiveAuthorizationV1
    adaptive_log: raw.PackedRawContextLogV1

    def __post_init__(self) -> None:
        _cid(
            self.matched_preregistration_id,
            "adaptive context matched preregistration",
        )
        if (
            type(self.context)
            is not raw.RawSafeChainStructuralContextV1
            or type(self.initial_model)
            is not raw.RawPartialStatisticalModelV1
            or type(self.failed_proof) is not raw.RawPartialPlanProofV1
            or type(self.authorization)
            is not raw.RawAdaptiveAuthorizationV1
            or type(self.adaptive_log) is not raw.PackedRawContextLogV1
            or self.initial_model.context.context_id
            != self.context.context_id
            or self.initial_model.source_log_id is not None
            or self.failed_proof.model_id != self.initial_model.model_id
            or self.failed_proof.status != raw.FAILED_STATUS
            or self.failed_proof.required_missing_row_keys
            != raw.ADAPTIVE_ROW_KEYS
            or self.authorization.context_id != self.context.context_id
            or self.authorization.failed_proof_id
            != self.failed_proof.proof_id
            or self.authorization.authorized_row_keys
            != raw.ADAPTIVE_ROW_KEYS
            or self.adaptive_log.context_id != self.context.context_id
            or self.adaptive_log.lane is not raw.AcquisitionLane.ADAPTIVE
            or self.adaptive_log.authorization_id
            != self.authorization.authorization_id
            or self.adaptive_log.total_draw_count
            != raw.ADAPTIVE_ROWS_PER_CONTEXT * raw.SAMPLE_COUNT_PER_ROW
        ):
            raise MatchedEndToEndInvariantViolation(
                "adaptive evidence chronology or coverage changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_adaptive_context_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "matched_preregistration_id": (
                self.matched_preregistration_id
            ),
            "context": self.context.to_document(),
            "initial_model": self.initial_model.to_document(),
            "failed_proof": self.failed_proof.to_document(),
            "authorization": self.authorization.to_document(),
            "adaptive_log": self.adaptive_log.to_document(),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("adaptive_context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class DirectGroundOutcomeAtomV1:
    outcome_index: int
    next_board: tuple[int, ...]
    next_status: str
    normalized_reward: Fraction
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        if (
            type(self.outcome_index) is not int
            or not 0 <= self.outcome_index < 4
            or type(self.next_board) is not tuple
            or len(self.next_board) != 4
            or any(type(rank) is not int for rank in self.next_board)
            or self.next_status
            not in (
                G2048Status.ACTIVE.value,
                G2048Status.FAILURE.value,
            )
            or type(self.normalized_reward) is not Fraction
            or self.normalized_reward
            not in (Fraction(1, 64), Fraction(1, 32))
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or (self.next_status == G2048Status.FAILURE.value)
            != self.failure
            or self.terminal != self.failure
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct ground outcome atom changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_ground_outcome_atom.v1",
            "schema_version": SCHEMA_VERSION,
            "outcome_index": self.outcome_index,
            "next_board": list(self.next_board),
            "next_status": self.next_status,
            "normalized_reward": _fdoc(self.normalized_reward),
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def atom_id(self) -> str:
        return _content_id("direct_atom", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


@dataclass(frozen=True, slots=True)
class DirectGroundRowCodebookV1:
    occurrence_id: str
    context_id: str
    remaining: int
    source_board: tuple[int, ...]
    source_status: str
    ground_action: tuple[int, int, int]
    outcomes: tuple[DirectGroundOutcomeAtomV1, ...]
    exact_probabilities_absent: bool = True

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "direct codebook occurrence")
        _cid(self.context_id, "direct codebook context")
        _exact_tuple(
            self.outcomes,
            DirectGroundOutcomeAtomV1,
            "direct codebook outcomes",
        )
        if (
            self.remaining not in (1, 2)
            or type(self.source_board) is not tuple
            or len(self.source_board) != 4
            or any(type(rank) is not int for rank in self.source_board)
            or self.source_status != G2048Status.ACTIVE.value
            or type(self.ground_action) is not tuple
            or len(self.ground_action) != 3
            or any(type(cell) is not int for cell in self.ground_action)
            or len(self.outcomes) != 4
            or tuple(item.outcome_index for item in self.outcomes)
            != tuple(range(4))
            or len({item.atom_id for item in self.outcomes}) != 4
            or self.exact_probabilities_absent is not True
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct row codebook shape changed"
            )
        first, second, survivor = self.ground_action
        first_row, first_column = divmod(first, 2)
        second_row, second_column = divmod(second, 2)
        if (
            not 0 <= first < second < 4
            or survivor not in (first, second)
            or abs(first_row - second_row)
            + abs(first_column - second_column)
            != 1
            or self.source_board[first] == 0
            or self.source_board[first] != self.source_board[second]
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct codebook action contradicts structural metadata"
            )
        expected_reward = (
            Fraction(1, 64)
            if self.source_board[first] == 1
            else Fraction(1, 32)
        )
        if any(
            item.normalized_reward != expected_reward
            for item in self.outcomes
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct codebook reward contradicts source ranks"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_ground_row_codebook.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "remaining": self.remaining,
            "source_board": list(self.source_board),
            "source_status": self.source_status,
            "ground_action": list(self.ground_action),
            "outcomes": [item.to_document() for item in self.outcomes],
            "exact_probabilities_absent": self.exact_probabilities_absent,
        }

    @property
    def row_id(self) -> str:
        return _content_id("direct_codebook", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class DirectPackedDrawBlockV1:
    occurrence_id: str
    context_id: str
    row_id: str
    seed: str
    block_index: int
    start_index: int
    draw_count: int
    outcome_nibbles_hex: str
    previous_block_id: str | None

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.occurrence_id, "direct block occurrence"),
            (self.context_id, "direct block context"),
            (self.row_id, "direct block row"),
        ):
            _cid(value, field_name)
        if self.previous_block_id is not None:
            _cid(self.previous_block_id, "direct block predecessor")
        if (
            type(self.seed) is not str
            or not self.seed
            or type(self.block_index) is not int
            or not 0 <= self.block_index < DIRECT_BLOCKS_PER_ROW
            or self.start_index
            != self.block_index * DIRECT_DRAW_BLOCK_SIZE
            or self.draw_count != DIRECT_DRAW_BLOCK_SIZE
            or type(self.outcome_nibbles_hex) is not str
            or len(self.outcome_nibbles_hex) != self.draw_count
            or any(
                character not in "0123"
                for character in self.outcome_nibbles_hex
            )
            or (self.block_index == 0)
            != (self.previous_block_id is None)
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct packed draw block changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_ground_packed_draw_block.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "row_id": self.row_id,
            "seed": self.seed,
            "block_index": self.block_index,
            "start_index": self.start_index,
            "draw_count": self.draw_count,
            "outcome_nibbles_hex": self.outcome_nibbles_hex,
            "previous_block_id": self.previous_block_id,
        }

    @property
    def block_id(self) -> str:
        return _content_id("direct_block", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "block_id": self.block_id}


@dataclass(frozen=True, slots=True)
class DirectGroundRowLogV1:
    codebook: DirectGroundRowCodebookV1
    blocks: tuple[DirectPackedDrawBlockV1, ...]
    sample_count: int = DIRECT_SAMPLE_COUNT_PER_ROW
    individual_draw_trace_embedded: bool = True
    exact_probabilities_embedded: bool = False

    def __post_init__(self) -> None:
        if type(self.codebook) is not DirectGroundRowCodebookV1:
            raise MatchedEndToEndInvariantViolation(
                "direct row log rejects substituted codebooks"
            )
        _exact_tuple(
            self.blocks,
            DirectPackedDrawBlockV1,
            "direct row-log blocks",
        )
        expected_previous: str | None = None
        for index, block in enumerate(self.blocks):
            if (
                block.occurrence_id != self.codebook.occurrence_id
                or block.context_id != self.codebook.context_id
                or block.row_id != self.codebook.row_id
                or block.block_index != index
                or block.previous_block_id != expected_previous
            ):
                raise MatchedEndToEndInvariantViolation(
                    "direct row-log block chain changed"
                )
            expected_previous = block.block_id
        if (
            len(self.blocks) != DIRECT_BLOCKS_PER_ROW
            or self.sample_count != DIRECT_SAMPLE_COUNT_PER_ROW
            or sum(item.draw_count for item in self.blocks)
            != self.sample_count
            or self.individual_draw_trace_embedded is not True
            or self.exact_probabilities_embedded is not False
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct row-log coverage or claim changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_ground_row_log.v1",
            "schema_version": SCHEMA_VERSION,
            "codebook": self.codebook.to_document(),
            "blocks": [item.to_document() for item in self.blocks],
            "sample_count": self.sample_count,
            "individual_draw_trace_embedded": (
                self.individual_draw_trace_embedded
            ),
            "exact_probabilities_embedded": (
                self.exact_probabilities_embedded
            ),
        }

    @property
    def log_id(self) -> str:
        return _content_id("direct_row_log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "log_id": self.log_id}


def _expected_direct_occurrence_shape(
    occurrence: raw.RawContextOccurrenceV1,
) -> tuple[int, int, int, int, int]:
    if occurrence.initial_mode == "D4_POINT":
        return (
            DIRECT_POINT_STATE_TIME_PAIRS,
            DIRECT_POINT_ACTION_ROWS,
            DIRECT_POINT_H1_ACTION_ROWS,
            DIRECT_POINT_ROOT_ACTION_ROWS,
            DIRECT_POINT_OBLIGATIONS,
        )
    return (
        DIRECT_UNIFORM_STATE_TIME_PAIRS,
        DIRECT_UNIFORM_ACTION_ROWS,
        DIRECT_UNIFORM_H1_ACTION_ROWS,
        DIRECT_UNIFORM_ROOT_ACTION_ROWS,
        DIRECT_UNIFORM_OBLIGATIONS,
    )


@dataclass(frozen=True, slots=True)
class DirectOccurrenceEvidenceV1:
    matched_preregistration_id: str
    occurrence: raw.RawContextOccurrenceV1
    rows: tuple[DirectGroundRowLogV1, ...]
    reachable_state_time_pairs: int
    action_rows: int
    h1_action_rows: int
    root_action_rows: int
    statistical_obligations: int
    state_action_catalogue_calls: int
    transition_row_enumerations: int
    total_draw_count: int
    occurrence_local_cold_model: bool = True
    cross_occurrence_reuse: bool = False

    def __post_init__(self) -> None:
        _cid(
            self.matched_preregistration_id,
            "direct occurrence matched preregistration",
        )
        if type(self.occurrence) is not raw.RawContextOccurrenceV1:
            raise MatchedEndToEndInvariantViolation(
                "direct occurrence evidence rejects substituted occurrences"
            )
        _exact_tuple(
            self.rows,
            DirectGroundRowLogV1,
            "direct occurrence rows",
        )
        expected = _expected_direct_occurrence_shape(self.occurrence)
        row_order = tuple(
            (
                -item.codebook.remaining,
                item.codebook.source_board,
                item.codebook.source_status,
                item.codebook.ground_action,
            )
            for item in self.rows
        )
        if (
            row_order != tuple(sorted(row_order))
            or len({item.codebook.row_id for item in self.rows})
            != len(self.rows)
            or any(
                item.codebook.occurrence_id
                != self.occurrence.occurrence_id
                or item.codebook.context_id != self.occurrence.context_id
                for item in self.rows
            )
            or (
                self.reachable_state_time_pairs,
                self.action_rows,
                self.h1_action_rows,
                self.root_action_rows,
                self.statistical_obligations,
            )
            != expected
            or len(self.rows) != self.action_rows
            or sum(
                item.codebook.remaining == 1 for item in self.rows
            )
            != self.h1_action_rows
            or sum(
                item.codebook.remaining == 2 for item in self.rows
            )
            != self.root_action_rows
            or self.state_action_catalogue_calls
            != self.reachable_state_time_pairs
            or self.transition_row_enumerations != self.action_rows
            or self.total_draw_count
            != self.action_rows * DIRECT_SAMPLE_COUNT_PER_ROW
            or self.total_draw_count
            != sum(item.sample_count for item in self.rows)
            or self.occurrence_local_cold_model is not True
            or self.cross_occurrence_reuse is not False
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct occurrence coverage, ordering, or cold semantics changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_occurrence_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "matched_preregistration_id": (
                self.matched_preregistration_id
            ),
            "occurrence": self.occurrence.to_document(),
            "rows": [item.to_document() for item in self.rows],
            "reachable_state_time_pairs": (
                self.reachable_state_time_pairs
            ),
            "action_rows": self.action_rows,
            "h1_action_rows": self.h1_action_rows,
            "root_action_rows": self.root_action_rows,
            "statistical_obligations": self.statistical_obligations,
            "state_action_catalogue_calls": (
                self.state_action_catalogue_calls
            ),
            "transition_row_enumerations": (
                self.transition_row_enumerations
            ),
            "total_draw_count": self.total_draw_count,
            "occurrence_local_cold_model": (
                self.occurrence_local_cold_model
            ),
            "cross_occurrence_reuse": self.cross_occurrence_reuse,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("direct_occurrence_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class MatchedEvidenceBundleV1:
    preregistration_id: str
    adaptive_contexts: tuple[MatchedAdaptiveContextEvidenceV1, ...]
    direct_occurrences: tuple[DirectOccurrenceEvidenceV1, ...]
    adaptive_total_draws: int = ADAPTIVE_TOTAL_DRAWS
    direct_total_draws: int = DIRECT_TOTAL_DRAWS
    exact_probabilities_exported_to_production: bool = False

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "matched evidence preregistration")
        _exact_tuple(
            self.adaptive_contexts,
            MatchedAdaptiveContextEvidenceV1,
            "matched adaptive contexts",
        )
        _exact_tuple(
            self.direct_occurrences,
            DirectOccurrenceEvidenceV1,
            "matched direct occurrences",
        )
        if (
            len(self.adaptive_contexts) != raw.CONTEXT_COUNT
            or len(self.direct_occurrences) != raw.OCCURRENCE_COUNT
            or any(
                item.matched_preregistration_id
                != self.preregistration_id
                for item in self.adaptive_contexts
            )
            or any(
                item.matched_preregistration_id
                != self.preregistration_id
                for item in self.direct_occurrences
            )
            or self.adaptive_total_draws != ADAPTIVE_TOTAL_DRAWS
            or self.adaptive_total_draws
            != sum(
                item.adaptive_log.total_draw_count
                for item in self.adaptive_contexts
            )
            or self.direct_total_draws != DIRECT_TOTAL_DRAWS
            or self.direct_total_draws
            != sum(
                item.total_draw_count
                for item in self.direct_occurrences
            )
            or self.exact_probabilities_exported_to_production is not False
        ):
            raise MatchedEndToEndInvariantViolation(
                "matched evidence coverage or probability boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_end_to_end_evidence_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "adaptive_contexts": [
                item.to_document() for item in self.adaptive_contexts
            ],
            "direct_occurrences": [
                item.to_document() for item in self.direct_occurrences
            ],
            "adaptive_total_draws": self.adaptive_total_draws,
            "direct_total_draws": self.direct_total_draws,
            "exact_probabilities_exported_to_production": (
                self.exact_probabilities_exported_to_production
            ),
        }

    @property
    def bundle_id(self) -> str:
        return _content_id("evidence_bundle", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bundle_id": self.bundle_id}


def _direct_uniform_v1(
    seed: str,
    context_id: str,
    occurrence_id: str,
    row_id: str,
    sample_index: int,
) -> int:
    if sample_index < 0:
        raise MatchedEndToEndInvariantViolation(
            "direct sample index must be nonnegative"
        )
    digest = hashlib.sha256(
        b"acfqp:direct-counter-uniform:v1\x00"
        + seed.encode("utf-8")
        + b"\x00"
        + context_id.encode("ascii")
        + b"\x00"
        + occurrence_id.encode("ascii")
        + b"\x00"
        + row_id.encode("ascii")
        + b"\x00"
        + sample_index.to_bytes(8, "big")
    ).digest()
    return int.from_bytes(digest, "big")


def _integer_cumulative_thresholds_v1(
    probabilities: tuple[Fraction, ...],
) -> tuple[int, ...]:
    cumulative = Fraction(0)
    thresholds: list[int] = []
    scale = 1 << 256
    for probability in probabilities:
        if type(probability) is not Fraction or probability <= 0:
            raise MatchedEndToEndInvariantViolation(
                "direct acquisition probabilities must be positive exact rationals"
            )
        cumulative += probability
        thresholds.append(
            (
                cumulative.numerator * scale
                + cumulative.denominator
                - 1
            )
            // cumulative.denominator
        )
    if cumulative != 1 or thresholds[-1] != scale:
        raise MatchedEndToEndInvariantViolation(
            "direct acquisition row mass is not one"
        )
    return tuple(thresholds)


def _sample_outcome_index(
    cumulative_thresholds: tuple[int, ...], uniform_uint256: int
) -> int:
    if (
        type(uniform_uint256) is not int
        or not 0 <= uniform_uint256 < 1 << 256
    ):
        raise MatchedEndToEndInvariantViolation(
            "direct counter uniform is not uint256"
        )
    index = bisect_right(cumulative_thresholds, uniform_uint256)
    if index < len(cumulative_thresholds):
        return index
    raise MatchedEndToEndInvariantViolation(
        "direct cumulative thresholds omit uint256 support"
    )


def _direct_draw_block_nibbles_v1(
    seed: str,
    context_id: str,
    occurrence_id: str,
    row_id: str,
    cumulative_thresholds: tuple[int, ...],
    start_index: int,
    draw_count: int,
) -> str:
    if start_index < 0 or draw_count <= 0:
        raise MatchedEndToEndInvariantViolation(
            "direct draw block bounds are invalid"
        )
    if len(cumulative_thresholds) > 16:
        raise MatchedEndToEndInvariantViolation(
            "direct draw codebook exceeds one hexadecimal nibble"
        )
    prefix = (
        b"acfqp:direct-counter-uniform:v1\x00"
        + seed.encode("utf-8")
        + b"\x00"
        + context_id.encode("ascii")
        + b"\x00"
        + occurrence_id.encode("ascii")
        + b"\x00"
        + row_id.encode("ascii")
        + b"\x00"
    )
    base_hasher = hashlib.sha256(prefix)
    hexadecimal = b"0123456789abcdef"
    encoded = bytearray(draw_count)
    for offset in range(draw_count):
        hasher = base_hasher.copy()
        hasher.update((start_index + offset).to_bytes(8, "big"))
        uniform = int.from_bytes(hasher.digest(), "big")
        outcome_index = bisect_right(
            cumulative_thresholds, uniform
        )
        if outcome_index >= len(cumulative_thresholds):
            raise MatchedEndToEndInvariantViolation(
                "direct cumulative thresholds omit uint256 support"
            )
        encoded[offset] = hexadecimal[outcome_index]
    return encoded.decode("ascii")


def _enumerate_direct_support_v1(
    kernel: raw.RawSafeChainContextKernelV1,
    occurrence: raw.RawContextOccurrenceV1,
) -> tuple[
    tuple[
        tuple[
            int,
            G2048State,
            G2048Action,
            tuple[Outcome[G2048State], ...],
        ],
        ...,
    ],
    int,
]:
    query = raw._query_for_occurrence_v1(occurrence)
    pending = [
        (query.horizon, state)
        for probability, state in query.initial_distribution
        if probability > 0
    ]
    visited: set[tuple[int, G2048State]] = set()
    rows: list[
        tuple[
            int,
            G2048State,
            G2048Action,
            tuple[Outcome[G2048State], ...],
        ]
    ] = []
    state_action_catalogue_calls = 0
    while pending:
        remaining, state = pending.pop()
        marker = (remaining, state)
        if marker in visited:
            continue
        visited.add(marker)
        if remaining <= 0 or kernel.is_terminal(state):
            continue
        actions = tuple(sorted(kernel.actions(state)))
        if not actions:
            continue
        state_action_catalogue_calls += 1
        for action in actions:
            outcomes = kernel.step(state, action)
            rows.append((remaining, state, action, outcomes))
            if remaining > 1:
                for outcome in outcomes:
                    if (
                        not outcome.failure
                        and not outcome.terminal
                        and not kernel.is_terminal(outcome.next_state)
                    ):
                        pending.append(
                            (remaining - 1, outcome.next_state)
                        )
    rows.sort(
        key=lambda item: (
            -item[0],
            item[1].board,
            item[1].status.value,
            _action_tuple(item[2]),
        )
    )
    return tuple(rows), state_action_catalogue_calls


def _direct_codebook_v1(
    occurrence: raw.RawContextOccurrenceV1,
    remaining: int,
    state: G2048State,
    action: G2048Action,
    outcomes: tuple[Outcome[G2048State], ...],
) -> DirectGroundRowCodebookV1:
    return DirectGroundRowCodebookV1(
        occurrence.occurrence_id,
        occurrence.context_id,
        remaining,
        state.board,
        state.status.value,
        _action_tuple(action),
        tuple(
            DirectGroundOutcomeAtomV1(
                index,
                outcome.next_state.board,
                outcome.next_state.status.value,
                _normalized_reward(outcome),
                outcome.failure,
                outcome.terminal,
            )
            for index, outcome in enumerate(outcomes)
        ),
    )


def _acquire_direct_occurrence_v1(
    preregistration: MatchedWorkloadPreregistrationV1,
    occurrence: raw.RawContextOccurrenceV1,
    kernel: raw.RawSafeChainContextKernelV1,
) -> DirectOccurrenceEvidenceV1:
    context_by_id = {
        item.context_id: item
        for item in preregistration.source_preregistration.contexts
    }
    context = context_by_id[occurrence.context_id]
    raw._validate_context_kernel(context, kernel)
    rows, catalogue_calls = _enumerate_direct_support_v1(
        kernel, occurrence
    )
    row_logs: list[DirectGroundRowLogV1] = []
    for remaining, state, action, outcomes in rows:
        codebook = _direct_codebook_v1(
            occurrence, remaining, state, action, outcomes
        )
        row_id = codebook.row_id
        probabilities = tuple(item.probability for item in outcomes)
        cumulative_thresholds = _integer_cumulative_thresholds_v1(
            probabilities
        )
        blocks: list[DirectPackedDrawBlockV1] = []
        previous: str | None = None
        for block_index in range(DIRECT_BLOCKS_PER_ROW):
            start = block_index * DIRECT_DRAW_BLOCK_SIZE
            draws = _direct_draw_block_nibbles_v1(
                preregistration.acquisition_profile.direct_seed,
                occurrence.context_id,
                occurrence.occurrence_id,
                row_id,
                cumulative_thresholds,
                start,
                DIRECT_DRAW_BLOCK_SIZE,
            )
            block = DirectPackedDrawBlockV1(
                occurrence.occurrence_id,
                occurrence.context_id,
                row_id,
                preregistration.acquisition_profile.direct_seed,
                block_index,
                start,
                DIRECT_DRAW_BLOCK_SIZE,
                draws,
                previous,
            )
            blocks.append(block)
            previous = block.block_id
        row_logs.append(
            DirectGroundRowLogV1(codebook, tuple(blocks))
        )
    shape = _expected_direct_occurrence_shape(occurrence)
    return DirectOccurrenceEvidenceV1(
        preregistration.preregistration_id,
        occurrence,
        tuple(row_logs),
        shape[0],
        len(row_logs),
        sum(item.codebook.remaining == 1 for item in row_logs),
        sum(item.codebook.remaining == 2 for item in row_logs),
        shape[4],
        catalogue_calls,
        len(row_logs),
        len(row_logs) * DIRECT_SAMPLE_COUNT_PER_ROW,
    )


def acquire_matched_end_to_end_evidence_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: MatchedWorkloadPreregistrationV1,
    kernels: tuple[raw.RawSafeChainContextKernelV1, ...],
) -> MatchedEvidenceBundleV1:
    """Acquire both arms after preregistration; exact kernels stay scoped here."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration)
        is not MatchedWorkloadPreregistrationV1
    ):
        raise MatchedEndToEndInvariantViolation(
            "matched acquisition rejects substituted inputs"
        )
    _exact_tuple(
        kernels,
        raw.RawSafeChainContextKernelV1,
        "matched acquisition kernels",
    )
    expected = preregister_matched_end_to_end_workload_v1(catalogue)
    _runtime_shape(preregistration, expected, "matched preregistration")
    if preregistration.to_document() != expected.to_document():
        raise MatchedEndToEndInvariantViolation(
            "matched preregistration reconstruction mismatch"
        )
    if len(kernels) != raw.CONTEXT_COUNT:
        raise MatchedEndToEndInvariantViolation(
            "matched acquisition requires exactly three kernels"
        )
    adaptive: list[MatchedAdaptiveContextEvidenceV1] = []
    kernel_by_context: dict[
        str, raw.RawSafeChainContextKernelV1
    ] = {}
    for context, kernel in zip(
        preregistration.source_preregistration.contexts, kernels
    ):
        raw._validate_context_kernel(context, kernel)
        kernel_by_context[context.context_id] = kernel
        initial_model = raw._missing_partial_model(catalogue, context)
        failed_proof = raw.solve_raw_partial_h2_v1(initial_model)
        if (
            failed_proof.status != raw.FAILED_STATUS
            or failed_proof.required_missing_row_keys
            != raw.ADAPTIVE_ROW_KEYS
        ):
            raise MatchedEndToEndInvariantViolation(
                "adaptive failed proof frontier changed"
            )
        authorization = raw.RawAdaptiveAuthorizationV1(
            preregistration.source_preregistration.preregistration_id,
            context.context_id,
            failed_proof.proof_id,
            failed_proof.required_missing_row_keys,
        )
        adaptive_log = raw._acquire_context_log(
            catalogue,
            preregistration.source_preregistration,
            context,
            kernel,
            raw.AcquisitionLane.ADAPTIVE,
            authorization,
        )
        adaptive.append(
            MatchedAdaptiveContextEvidenceV1(
                preregistration.preregistration_id,
                context,
                initial_model,
                failed_proof,
                authorization,
                adaptive_log,
            )
        )
    direct = tuple(
        _acquire_direct_occurrence_v1(
            preregistration,
            occurrence,
            kernel_by_context[occurrence.context_id],
        )
        for occurrence in preregistration.source_preregistration.occurrences
    )
    return MatchedEvidenceBundleV1(
        preregistration.preregistration_id,
        tuple(adaptive),
        direct,
    )


def _interval(
    empirical: Fraction, radius: Fraction = DIRECT_HOEFFDING_RADIUS
) -> tuple[Fraction, Fraction]:
    return max(Fraction(0), empirical - radius), min(
        Fraction(1), empirical + radius
    )


def _row_counts(
    row_log: DirectGroundRowLogV1,
) -> tuple[int, int, int, int]:
    counts = [0, 0, 0, 0]
    for block in row_log.blocks:
        for character in block.outcome_nibbles_hex:
            counts[int(character, 16)] += 1
    if sum(counts) != row_log.sample_count:
        raise MatchedEndToEndInvariantViolation(
            "direct row log decoded to the wrong sample count"
        )
    return tuple(counts)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class DirectH1ActionEstimateV1:
    occurrence_id: str
    row_log_id: str
    source_board: tuple[int, ...]
    source_status: str
    ground_action: tuple[int, int, int]
    empirical_failure: Fraction
    failure_lower: Fraction
    failure_upper: Fraction
    normalized_reward: Fraction = Fraction(1, 32)

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "H1 estimate occurrence")
        _cid(self.row_log_id, "H1 estimate row log")
        if (
            type(self.source_board) is not tuple
            or len(self.source_board) != 4
            or self.source_status != G2048Status.ACTIVE.value
            or type(self.ground_action) is not tuple
            or len(self.ground_action) != 3
            or any(
                type(value) is not Fraction
                for value in (
                    self.empirical_failure,
                    self.failure_lower,
                    self.failure_upper,
                    self.normalized_reward,
                )
            )
            or not 0
            <= self.failure_lower
            <= self.empirical_failure
            <= self.failure_upper
            <= 1
            or (self.failure_lower, self.failure_upper)
            != _interval(self.empirical_failure)
            or self.normalized_reward != Fraction(1, 32)
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct H1 estimate changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_h1_action_estimate.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "row_log_id": self.row_log_id,
            "source_board": list(self.source_board),
            "source_status": self.source_status,
            "ground_action": list(self.ground_action),
            "empirical_failure": _fdoc(self.empirical_failure),
            "failure_lower": _fdoc(self.failure_lower),
            "failure_upper": _fdoc(self.failure_upper),
            "normalized_reward": _fdoc(self.normalized_reward),
        }

    @property
    def estimate_id(self) -> str:
        return _content_id("h1_estimate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "estimate_id": self.estimate_id}


@dataclass(frozen=True, slots=True)
class DirectH1DecisionV1:
    occurrence_id: str
    source_board: tuple[int, ...]
    source_status: str
    selected_estimate_id: str
    ground_action: tuple[int, int, int]

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "H1 decision occurrence")
        _cid(self.selected_estimate_id, "H1 decision estimate")
        if (
            type(self.source_board) is not tuple
            or len(self.source_board) != 4
            or self.source_status != G2048Status.ACTIVE.value
            or type(self.ground_action) is not tuple
            or len(self.ground_action) != 3
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct H1 decision changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_h1_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "source_board": list(self.source_board),
            "source_status": self.source_status,
            "selected_estimate_id": self.selected_estimate_id,
            "ground_action": list(self.ground_action),
        }

    @property
    def decision_id(self) -> str:
        return _content_id("h1_decision", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


@dataclass(frozen=True, slots=True)
class DirectRootActionEstimateV1:
    occurrence_id: str
    row_log_id: str
    source_board: tuple[int, ...]
    source_status: str
    ground_action: tuple[int, int, int]
    continuation_h1_decision_ids: tuple[str, ...]
    empirical_risk_lower_function: Fraction
    empirical_risk_upper_function: Fraction
    failure_lower: Fraction
    failure_upper: Fraction
    empirical_reward: Fraction
    reward_lower: Fraction
    reward_upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "root estimate occurrence")
        _cid(self.row_log_id, "root estimate row log")
        if type(self.continuation_h1_decision_ids) is not tuple:
            raise MatchedEndToEndInvariantViolation(
                "root continuation IDs must be a tuple"
            )
        for item in self.continuation_h1_decision_ids:
            _cid(item, "root continuation H1 decision")
        if (
            self.continuation_h1_decision_ids
            != tuple(sorted(set(self.continuation_h1_decision_ids)))
            or type(self.source_board) is not tuple
            or len(self.source_board) != 4
            or self.source_status != G2048Status.ACTIVE.value
            or type(self.ground_action) is not tuple
            or len(self.ground_action) != 3
            or any(
                type(value) is not Fraction
                for value in (
                    self.empirical_risk_lower_function,
                    self.empirical_risk_upper_function,
                    self.failure_lower,
                    self.failure_upper,
                    self.empirical_reward,
                    self.reward_lower,
                    self.reward_upper,
                )
            )
            or not 0
            <= self.empirical_risk_lower_function
            <= self.empirical_risk_upper_function
            <= 1
            or self.failure_lower
            != max(
                Fraction(0),
                self.empirical_risk_lower_function
                - DIRECT_HOEFFDING_RADIUS,
            )
            or self.failure_upper
            != min(
                Fraction(1),
                self.empirical_risk_upper_function
                + DIRECT_HOEFFDING_RADIUS,
            )
            or not 0 <= self.failure_lower <= self.failure_upper <= 1
            or not 0 <= self.empirical_reward <= 1
            or (self.reward_lower, self.reward_upper)
            != _interval(self.empirical_reward)
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct root estimate changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_root_action_estimate.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "row_log_id": self.row_log_id,
            "source_board": list(self.source_board),
            "source_status": self.source_status,
            "ground_action": list(self.ground_action),
            "continuation_h1_decision_ids": list(
                self.continuation_h1_decision_ids
            ),
            "empirical_risk_lower_function": _fdoc(
                self.empirical_risk_lower_function
            ),
            "empirical_risk_upper_function": _fdoc(
                self.empirical_risk_upper_function
            ),
            "failure_lower": _fdoc(self.failure_lower),
            "failure_upper": _fdoc(self.failure_upper),
            "empirical_reward": _fdoc(self.empirical_reward),
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
        }

    @property
    def estimate_id(self) -> str:
        return _content_id("root_estimate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "estimate_id": self.estimate_id}


@dataclass(frozen=True, slots=True)
class DirectGroundPolicyDecisionV1:
    remaining: int
    source_board: tuple[int, ...]
    source_status: str
    ground_action: tuple[int, int, int]

    def __post_init__(self) -> None:
        if (
            self.remaining not in (1, 2)
            or type(self.source_board) is not tuple
            or len(self.source_board) != 4
            or self.source_status != G2048Status.ACTIVE.value
            or type(self.ground_action) is not tuple
            or len(self.ground_action) != 3
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct policy decision changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_ground_policy_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "remaining": self.remaining,
            "source_board": list(self.source_board),
            "source_status": self.source_status,
            "ground_action": list(self.ground_action),
        }

    @property
    def decision_id(self) -> str:
        return _content_id("ground_decision", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


@dataclass(frozen=True, slots=True)
class DirectRootCandidateV1:
    occurrence_id: str
    root_decisions: tuple[DirectGroundPolicyDecisionV1, ...]
    root_estimate_ids: tuple[str, ...]
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "root candidate occurrence")
        _exact_tuple(
            self.root_decisions,
            DirectGroundPolicyDecisionV1,
            "root candidate decisions",
        )
        if type(self.root_estimate_ids) is not tuple:
            raise MatchedEndToEndInvariantViolation(
                "root candidate estimate IDs must be a tuple"
            )
        for item in self.root_estimate_ids:
            _cid(item, "root candidate estimate")
        order = tuple(
            (item.source_board, item.source_status)
            for item in self.root_decisions
        )
        if (
            order != tuple(sorted(order))
            or any(item.remaining != 2 for item in self.root_decisions)
            or len(self.root_estimate_ids) != len(self.root_decisions)
            or any(
                type(value) is not Fraction
                for value in (
                    self.reward_lower,
                    self.reward_upper,
                    self.failure_lower,
                    self.failure_upper,
                )
            )
            or not 0 <= self.reward_lower <= self.reward_upper <= 1
            or not 0 <= self.failure_lower <= self.failure_upper <= 1
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct root candidate changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_root_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "root_decisions": [
                item.to_document() for item in self.root_decisions
            ],
            "root_estimate_ids": list(self.root_estimate_ids),
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
            "failure_lower": _fdoc(self.failure_lower),
            "failure_upper": _fdoc(self.failure_upper),
        }

    @property
    def candidate_id(self) -> str:
        return _content_id("root_candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class DirectGroundStatisticalPolicyV1:
    occurrence_id: str
    decisions: tuple[DirectGroundPolicyDecisionV1, ...]
    selected_candidate_id: str
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "direct policy occurrence")
        _cid(self.selected_candidate_id, "direct policy candidate")
        _exact_tuple(
            self.decisions,
            DirectGroundPolicyDecisionV1,
            "direct policy decisions",
        )
        order = tuple(
            (
                -item.remaining,
                item.source_board,
                item.source_status,
                item.ground_action,
            )
            for item in self.decisions
        )
        if (
            order != tuple(sorted(order))
            or len(
                {
                    (
                        item.remaining,
                        item.source_board,
                        item.source_status,
                    )
                    for item in self.decisions
                }
            )
            != len(self.decisions)
            or any(
                type(value) is not Fraction
                for value in (
                    self.reward_lower,
                    self.reward_upper,
                    self.failure_lower,
                    self.failure_upper,
                )
            )
            or not 0 <= self.reward_lower <= self.reward_upper <= 1
            or not 0 <= self.failure_lower <= self.failure_upper <= 1
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct statistical policy changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_ground_statistical_policy.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "decisions": [item.to_document() for item in self.decisions],
            "selected_candidate_id": self.selected_candidate_id,
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
            "failure_lower": _fdoc(self.failure_lower),
            "failure_upper": _fdoc(self.failure_upper),
        }

    @property
    def policy_id(self) -> str:
        return _content_id("ground_policy", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "policy_id": self.policy_id}


@dataclass(frozen=True, slots=True)
class DirectGroundPlanProofV1:
    occurrence: raw.RawContextOccurrenceV1
    evidence_id: str
    h1_estimates: tuple[DirectH1ActionEstimateV1, ...]
    h1_decisions: tuple[DirectH1DecisionV1, ...]
    root_estimates: tuple[DirectRootActionEstimateV1, ...]
    root_candidates: tuple[DirectRootCandidateV1, ...]
    selected_policy: DirectGroundStatisticalPolicyV1
    unrestricted_reward_upper: Fraction
    normalized_regret_upper: Fraction
    confidence_lower: Fraction
    statistical_obligations: int
    status: str = DIRECT_CERTIFIED_STATUS

    def __post_init__(self) -> None:
        if type(self.occurrence) is not raw.RawContextOccurrenceV1:
            raise MatchedEndToEndInvariantViolation(
                "direct proof rejects substituted occurrence"
            )
        _cid(self.evidence_id, "direct proof evidence")
        _exact_tuple(
            self.h1_estimates,
            DirectH1ActionEstimateV1,
            "direct proof H1 estimates",
        )
        _exact_tuple(
            self.h1_decisions,
            DirectH1DecisionV1,
            "direct proof H1 decisions",
        )
        _exact_tuple(
            self.root_estimates,
            DirectRootActionEstimateV1,
            "direct proof root estimates",
        )
        _exact_tuple(
            self.root_candidates,
            DirectRootCandidateV1,
            "direct proof root candidates",
        )
        if type(self.selected_policy) is not DirectGroundStatisticalPolicyV1:
            raise MatchedEndToEndInvariantViolation(
                "direct proof rejects substituted policy"
            )
        shape = _expected_direct_occurrence_shape(self.occurrence)
        expected_h1_states = (
            DIRECT_POINT_STATE_TIME_PAIRS - 1
            if self.occurrence.initial_mode == "D4_POINT"
            else DIRECT_UNIFORM_STATE_TIME_PAIRS - 8
        )
        expected_root_candidates = (
            DIRECT_POINT_ROOT_CANDIDATES
            if self.occurrence.initial_mode == "D4_POINT"
            else DIRECT_UNIFORM_ROOT_CANDIDATES
        )
        selected_candidates = {
            item.candidate_id: item for item in self.root_candidates
        }
        selected = selected_candidates.get(
            self.selected_policy.selected_candidate_id
        )
        if (
            len(self.h1_estimates) != shape[2]
            or len(self.h1_decisions) != expected_h1_states
            or len(self.root_estimates) != shape[3]
            or len(self.root_candidates) != expected_root_candidates
            or tuple(item.estimate_id for item in self.h1_estimates)
            != tuple(sorted(item.estimate_id for item in self.h1_estimates))
            or tuple(item.decision_id for item in self.h1_decisions)
            != tuple(sorted(item.decision_id for item in self.h1_decisions))
            or tuple(item.estimate_id for item in self.root_estimates)
            != tuple(sorted(item.estimate_id for item in self.root_estimates))
            or tuple(item.candidate_id for item in self.root_candidates)
            != tuple(
                sorted(item.candidate_id for item in self.root_candidates)
            )
            or selected is None
            or (
                self.selected_policy.reward_lower,
                self.selected_policy.reward_upper,
                self.selected_policy.failure_lower,
                self.selected_policy.failure_upper,
            )
            != (
                selected.reward_lower,
                selected.reward_upper,
                selected.failure_lower,
                selected.failure_upper,
            )
            or self.selected_policy.occurrence_id
            != self.occurrence.occurrence_id
            or self.selected_policy.failure_upper > self.occurrence.delta
            or self.unrestricted_reward_upper
            != max(item.reward_upper for item in self.root_candidates)
            or self.normalized_regret_upper
            != self.unrestricted_reward_upper
            - self.selected_policy.reward_lower
            or self.normalized_regret_upper > Fraction(1, 20)
            or self.statistical_obligations != shape[4]
            or self.confidence_lower
            != 1
            - self.statistical_obligations
            * DIRECT_PER_OBLIGATION_TAIL_UPPER
            or self.status != DIRECT_CERTIFIED_STATUS
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct ground proof coverage, selection, or certificate changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_ground_statistical_plan_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence": self.occurrence.to_document(),
            "evidence_id": self.evidence_id,
            "h1_estimates": [
                item.to_document() for item in self.h1_estimates
            ],
            "h1_decisions": [
                item.to_document() for item in self.h1_decisions
            ],
            "root_estimates": [
                item.to_document() for item in self.root_estimates
            ],
            "root_candidates": [
                item.to_document() for item in self.root_candidates
            ],
            "selected_policy": self.selected_policy.to_document(),
            "unrestricted_reward_upper": _fdoc(
                self.unrestricted_reward_upper
            ),
            "normalized_regret_upper": _fdoc(
                self.normalized_regret_upper
            ),
            "confidence_lower": _fdoc(self.confidence_lower),
            "statistical_obligations": self.statistical_obligations,
            "status": self.status,
            "deterministic_ground_policy": True,
            "cross_occurrence_model_reuse": False,
        }

    @property
    def proof_id(self) -> str:
        return _content_id("direct_proof", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


def _build_h1_estimates_v1(
    evidence: DirectOccurrenceEvidenceV1,
) -> tuple[
    tuple[DirectH1ActionEstimateV1, ...],
    tuple[DirectH1DecisionV1, ...],
]:
    estimates: list[DirectH1ActionEstimateV1] = []
    by_state: dict[
        tuple[int, tuple[int, ...], str],
        list[DirectH1ActionEstimateV1],
    ] = {}
    for row_log in evidence.rows:
        codebook = row_log.codebook
        if codebook.remaining != 1:
            continue
        counts = _row_counts(row_log)
        failure_count = sum(
            counts[atom.outcome_index]
            for atom in codebook.outcomes
            if atom.failure
        )
        empirical = Fraction(failure_count, row_log.sample_count)
        lower, upper = _interval(empirical)
        if any(
            atom.normalized_reward != Fraction(1, 32)
            for atom in codebook.outcomes
        ):
            raise MatchedEndToEndInvariantViolation(
                "direct H1 row reward changed"
            )
        estimate = DirectH1ActionEstimateV1(
            evidence.occurrence.occurrence_id,
            row_log.log_id,
            codebook.source_board,
            codebook.source_status,
            codebook.ground_action,
            empirical,
            lower,
            upper,
        )
        estimates.append(estimate)
        by_state.setdefault(
            _state_key(
                1, codebook.source_board, codebook.source_status
            ),
            [],
        ).append(estimate)
    decisions: list[DirectH1DecisionV1] = []
    for state_key in sorted(by_state):
        selected = min(
            by_state[state_key],
            key=lambda item: (
                item.failure_upper,
                item.ground_action,
                item.estimate_id,
            ),
        )
        decisions.append(
            DirectH1DecisionV1(
                evidence.occurrence.occurrence_id,
                selected.source_board,
                selected.source_status,
                selected.estimate_id,
                selected.ground_action,
            )
        )
    return (
        tuple(sorted(estimates, key=lambda item: item.estimate_id)),
        tuple(sorted(decisions, key=lambda item: item.decision_id)),
    )


def _build_root_estimates_v1(
    evidence: DirectOccurrenceEvidenceV1,
    h1_estimates: tuple[DirectH1ActionEstimateV1, ...],
    h1_decisions: tuple[DirectH1DecisionV1, ...],
) -> tuple[DirectRootActionEstimateV1, ...]:
    estimate_by_id = {item.estimate_id: item for item in h1_estimates}
    selected_by_state = {
        _state_key(1, item.source_board, item.source_status): (
            item,
            estimate_by_id[item.selected_estimate_id],
        )
        for item in h1_decisions
    }
    result: list[DirectRootActionEstimateV1] = []
    for row_log in evidence.rows:
        codebook = row_log.codebook
        if codebook.remaining != 2:
            continue
        counts = _row_counts(row_log)
        risk_lower_sum = Fraction(0)
        risk_upper_sum = Fraction(0)
        reward_sum = Fraction(0)
        continuation_ids: set[str] = set()
        for atom in codebook.outcomes:
            count = counts[atom.outcome_index]
            if atom.failure:
                branch_lower = branch_upper = Fraction(1)
                branch_reward = atom.normalized_reward
            else:
                marker = _state_key(
                    1, atom.next_board, atom.next_status
                )
                try:
                    decision, estimate = selected_by_state[marker]
                except KeyError as error:
                    raise MatchedEndToEndInvariantViolation(
                        "root outcome omitted a required H1 decision"
                    ) from error
                continuation_ids.add(decision.decision_id)
                branch_lower = estimate.failure_lower
                branch_upper = estimate.failure_upper
                branch_reward = (
                    atom.normalized_reward
                    + estimate.normalized_reward
                )
            risk_lower_sum += count * branch_lower
            risk_upper_sum += count * branch_upper
            reward_sum += count * branch_reward
        empirical_lower = risk_lower_sum / row_log.sample_count
        empirical_upper = risk_upper_sum / row_log.sample_count
        empirical_reward = reward_sum / row_log.sample_count
        result.append(
            DirectRootActionEstimateV1(
                evidence.occurrence.occurrence_id,
                row_log.log_id,
                codebook.source_board,
                codebook.source_status,
                codebook.ground_action,
                tuple(sorted(continuation_ids)),
                empirical_lower,
                empirical_upper,
                max(
                    Fraction(0),
                    empirical_lower - DIRECT_HOEFFDING_RADIUS,
                ),
                min(
                    Fraction(1),
                    empirical_upper + DIRECT_HOEFFDING_RADIUS,
                ),
                empirical_reward,
                *_interval(empirical_reward),
            )
        )
    return tuple(sorted(result, key=lambda item: item.estimate_id))


def _build_root_candidates_v1(
    evidence: DirectOccurrenceEvidenceV1,
    root_estimates: tuple[DirectRootActionEstimateV1, ...],
) -> tuple[DirectRootCandidateV1, ...]:
    by_state: dict[
        tuple[int, ...], list[DirectRootActionEstimateV1]
    ] = {}
    for estimate in root_estimates:
        by_state.setdefault(estimate.source_board, []).append(estimate)
    expected_boards = tuple(evidence.occurrence.initial_boards)
    if tuple(sorted(by_state)) != expected_boards:
        raise MatchedEndToEndInvariantViolation(
            "direct root estimates do not cover the query distribution"
        )
    mass = Fraction(1, len(expected_boards))
    candidates: list[DirectRootCandidateV1] = []
    for assignment in product(
        *(tuple(sorted(by_state[board], key=lambda item: item.ground_action))
          for board in expected_boards)
    ):
        decisions = tuple(
            DirectGroundPolicyDecisionV1(
                2,
                item.source_board,
                item.source_status,
                item.ground_action,
            )
            for item in assignment
        )
        candidates.append(
            DirectRootCandidateV1(
                evidence.occurrence.occurrence_id,
                decisions,
                tuple(item.estimate_id for item in assignment),
                sum(
                    (mass * item.reward_lower for item in assignment),
                    Fraction(0),
                ),
                sum(
                    (mass * item.reward_upper for item in assignment),
                    Fraction(0),
                ),
                sum(
                    (mass * item.failure_lower for item in assignment),
                    Fraction(0),
                ),
                sum(
                    (mass * item.failure_upper for item in assignment),
                    Fraction(0),
                ),
            )
        )
    return tuple(sorted(candidates, key=lambda item: item.candidate_id))


def plan_cold_direct_ground_v1(
    evidence: DirectOccurrenceEvidenceV1,
) -> DirectGroundPlanProofV1:
    """Plan from occurrence-local packed ground observations, without a kernel."""

    if type(evidence) is not DirectOccurrenceEvidenceV1:
        raise MatchedEndToEndInvariantViolation(
            "direct planner rejects substituted evidence"
        )
    h1_estimates, h1_decisions = _build_h1_estimates_v1(evidence)
    root_estimates = _build_root_estimates_v1(
        evidence, h1_estimates, h1_decisions
    )
    candidates = _build_root_candidates_v1(evidence, root_estimates)
    feasible = tuple(
        item
        for item in candidates
        if item.failure_upper <= evidence.occurrence.delta
    )
    if not feasible:
        raise MatchedEndToEndInvariantViolation(
            "registered direct occurrence lost robust feasibility"
        )
    selected = min(
        feasible,
        key=lambda item: (
            -item.reward_lower,
            item.failure_upper,
            item.candidate_id,
        ),
    )
    h1_policy_decisions = tuple(
        DirectGroundPolicyDecisionV1(
            1,
            item.source_board,
            item.source_status,
            item.ground_action,
        )
        for item in h1_decisions
    )
    all_decisions = tuple(
        sorted(
            h1_policy_decisions + selected.root_decisions,
            key=lambda item: (
                -item.remaining,
                item.source_board,
                item.source_status,
                item.ground_action,
            ),
        )
    )
    policy = DirectGroundStatisticalPolicyV1(
        evidence.occurrence.occurrence_id,
        all_decisions,
        selected.candidate_id,
        selected.reward_lower,
        selected.reward_upper,
        selected.failure_lower,
        selected.failure_upper,
    )
    unrestricted_reward_upper = max(
        item.reward_upper for item in candidates
    )
    return DirectGroundPlanProofV1(
        evidence.occurrence,
        evidence.evidence_id,
        h1_estimates,
        h1_decisions,
        root_estimates,
        candidates,
        policy,
        unrestricted_reward_upper,
        unrestricted_reward_upper - policy.reward_lower,
        1
        - evidence.statistical_obligations
        * DIRECT_PER_OBLIGATION_TAIL_UPPER,
        evidence.statistical_obligations,
    )


@dataclass(frozen=True, slots=True)
class MatchedAdaptiveModelResultV1:
    context: raw.RawSafeChainStructuralContextV1
    evidence_id: str
    initial_failed_proof_id: str
    adaptive_model: raw.RawPartialStatisticalModelV1

    def __post_init__(self) -> None:
        if (
            type(self.context)
            is not raw.RawSafeChainStructuralContextV1
            or type(self.adaptive_model)
            is not raw.RawPartialStatisticalModelV1
        ):
            raise MatchedEndToEndInvariantViolation(
                "adaptive model result rejects substituted artifacts"
            )
        _cid(self.evidence_id, "adaptive model result evidence")
        _cid(
            self.initial_failed_proof_id,
            "adaptive model initial failed proof",
        )
        if (
            self.adaptive_model.context.context_id
            != self.context.context_id
            or self.adaptive_model.lane
            is not raw.AcquisitionLane.ADAPTIVE
            or (
                self.adaptive_model.observed_row_count,
                self.adaptive_model.missing_row_count,
            )
            != (3, 3)
        ):
            raise MatchedEndToEndInvariantViolation(
                "adaptive partial RAPM coverage changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_adaptive_model_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context": self.context.to_document(),
            "evidence_id": self.evidence_id,
            "initial_failed_proof_id": self.initial_failed_proof_id,
            "adaptive_model": self.adaptive_model.to_document(),
        }

    @property
    def result_id(self) -> str:
        return _content_id("adaptive_model_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class MatchedAdaptiveOccurrenceResultV1:
    occurrence: raw.RawContextOccurrenceV1
    context_model_result_id: str
    adaptive_model_id: str
    adaptive_proof_id: str
    selected_schedule: tuple[str, str, str]
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction
    new_individual_draws: int
    reused_frozen_context_model: bool
    candidate_policies_evaluated: int = 8
    status: str = raw.CERTIFIED_STATUS

    def __post_init__(self) -> None:
        if type(self.occurrence) is not raw.RawContextOccurrenceV1:
            raise MatchedEndToEndInvariantViolation(
                "adaptive occurrence result rejects substituted occurrence"
            )
        for value, field_name in (
            (
                self.context_model_result_id,
                "adaptive occurrence context model",
            ),
            (self.adaptive_model_id, "adaptive occurrence model"),
            (self.adaptive_proof_id, "adaptive occurrence proof"),
        ):
            _cid(value, field_name)
        first_context_pass = self.occurrence.ordinal < raw.CONTEXT_COUNT
        expected_draws = (
            raw.ADAPTIVE_ROWS_PER_CONTEXT * raw.SAMPLE_COUNT_PER_ROW
            if first_context_pass
            else 0
        )
        if (
            self.selected_schedule
            != (
                G2048RelativeSurvivorLabel.TOWARD.value,
                G2048RelativeSurvivorLabel.AWAY.value,
                G2048RelativeSurvivorLabel.AWAY.value,
            )
            or any(
                type(value) is not Fraction
                for value in (
                    self.reward_lower,
                    self.reward_upper,
                    self.failure_lower,
                    self.failure_upper,
                )
            )
            or not 0 <= self.reward_lower <= self.reward_upper <= 1
            or not 0
            <= self.failure_lower
            <= self.failure_upper
            <= self.occurrence.delta
            or self.new_individual_draws != expected_draws
            or self.reused_frozen_context_model
            is not (not first_context_pass)
            or self.candidate_policies_evaluated != 8
            or self.status != raw.CERTIFIED_STATUS
        ):
            raise MatchedEndToEndInvariantViolation(
                "adaptive occurrence plan, reuse, or certificate changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_adaptive_occurrence_result.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence": self.occurrence.to_document(),
            "context_model_result_id": self.context_model_result_id,
            "adaptive_model_id": self.adaptive_model_id,
            "adaptive_proof_id": self.adaptive_proof_id,
            "selected_schedule": list(self.selected_schedule),
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
            "failure_lower": _fdoc(self.failure_lower),
            "failure_upper": _fdoc(self.failure_upper),
            "new_individual_draws": self.new_individual_draws,
            "reused_frozen_context_model": (
                self.reused_frozen_context_model
            ),
            "candidate_policies_evaluated": (
                self.candidate_policies_evaluated
            ),
            "status": self.status,
        }

    @property
    def result_id(self) -> str:
        return _content_id("adaptive_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class MatchedOccurrenceResultV1:
    occurrence: raw.RawContextOccurrenceV1
    adaptive: MatchedAdaptiveOccurrenceResultV1
    direct: DirectGroundPlanProofV1
    arms_share_context_and_query_identity: bool = True
    direct_model_reused: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.occurrence) is not raw.RawContextOccurrenceV1
            or type(self.adaptive)
            is not MatchedAdaptiveOccurrenceResultV1
            or type(self.direct) is not DirectGroundPlanProofV1
            or self.adaptive.occurrence.occurrence_id
            != self.occurrence.occurrence_id
            or self.direct.occurrence.occurrence_id
            != self.occurrence.occurrence_id
            or self.arms_share_context_and_query_identity is not True
            or self.direct_model_reused is not False
        ):
            raise MatchedEndToEndInvariantViolation(
                "matched occurrence identity or route semantics changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_end_to_end_occurrence_result.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence": self.occurrence.to_document(),
            "adaptive": self.adaptive.to_document(),
            "direct": self.direct.to_document(),
            "arms_share_context_and_query_identity": (
                self.arms_share_context_and_query_identity
            ),
            "direct_model_reused": self.direct_model_reused,
        }

    @property
    def result_id(self) -> str:
        return _content_id("occurrence_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class MatchedEndToEndWorkV1:
    structural_contexts: int = 3
    logical_occurrences: int = 6
    adaptive_initial_failed_proofs: int = 3
    adaptive_failed_proof_candidate_evaluations: int = 24
    adaptive_acquisition_kernel_row_enumerations: int = 9
    adaptive_individual_draws: int = ADAPTIVE_TOTAL_DRAWS
    adaptive_partial_model_builds: int = 3
    adaptive_occurrence_candidate_evaluations: int = 48
    adaptive_statistical_certificates: int = 6
    adaptive_within_context_model_reuses: int = 3
    direct_cold_model_builds: int = 6
    direct_state_action_catalogue_calls: int = DIRECT_TOTAL_STATE_TIME_PAIRS
    direct_transition_row_enumerations: int = DIRECT_TOTAL_ACTION_ROWS
    direct_individual_draws: int = DIRECT_TOTAL_DRAWS
    direct_h1_action_estimates: int = DIRECT_TOTAL_H1_ACTION_ROWS
    direct_root_action_estimates: int = DIRECT_TOTAL_ROOT_ACTION_ROWS
    direct_statistical_obligations: int = DIRECT_TOTAL_OBLIGATIONS
    direct_root_candidate_evaluations: int = DIRECT_TOTAL_ROOT_CANDIDATES
    direct_statistical_certificates: int = 6
    direct_cross_occurrence_model_reuses: int = 0
    adaptive_fallback_calls: int = 0
    direct_fallback_calls: int = 0
    noncertificate_occurrence_closures: int = 0
    adaptive_draw_reduction_against_cold_direct: int = (
        DIRECT_TOTAL_DRAWS - ADAPTIVE_TOTAL_DRAWS
    )
    registered_direct_to_adaptive_draw_ratio: Fraction = REGISTERED_DRAW_RATIO
    matched_direct_ground_planning_control: bool = True
    registered_workload_draw_advantage_observed: bool = True
    broad_sample_efficiency_claimed: bool = False
    sample_tax_operator_claimed: bool = False
    official_scalar_cost: None = None
    official_n_break_even: None = None

    def __post_init__(self) -> None:
        expected = (
            3,
            6,
            3,
            24,
            9,
            ADAPTIVE_TOTAL_DRAWS,
            3,
            48,
            6,
            3,
            6,
            DIRECT_TOTAL_STATE_TIME_PAIRS,
            DIRECT_TOTAL_ACTION_ROWS,
            DIRECT_TOTAL_DRAWS,
            DIRECT_TOTAL_H1_ACTION_ROWS,
            DIRECT_TOTAL_ROOT_ACTION_ROWS,
            DIRECT_TOTAL_OBLIGATIONS,
            DIRECT_TOTAL_ROOT_CANDIDATES,
            6,
            0,
            0,
            0,
            0,
            DIRECT_TOTAL_DRAWS - ADAPTIVE_TOTAL_DRAWS,
            Fraction(33),
            True,
            True,
            False,
            False,
            None,
            None,
        )
        observed = tuple(
            object.__getattribute__(self, field.name)
            for field in fields(type(self))
        )
        if observed != expected:
            raise MatchedEndToEndInvariantViolation(
                "matched workload accounting or claim locks changed"
            )

    def _payload(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema": "acfqp.matched_end_to_end_work.v1",
            "schema_version": SCHEMA_VERSION,
        }
        for field in fields(type(self)):
            value = object.__getattribute__(self, field.name)
            document[field.name] = (
                _fdoc(value) if type(value) is Fraction else value
            )
        document.update(
            {
                "adaptive_route_semantics": (
                    "context_reusable_partial_rapm_after_failed_proof"
                ),
                "direct_route_semantics": (
                    "cold_occurrence_local_full_ground_statistical_planning"
                ),
                "heterogeneous_work_axes_not_scalarized": True,
            }
        )
        return document

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class MatchedEndToEndCampaignResultV1:
    preregistration: MatchedWorkloadPreregistrationV1
    evidence_bundle_id: str
    adaptive_models: tuple[MatchedAdaptiveModelResultV1, ...]
    occurrences: tuple[MatchedOccurrenceResultV1, ...]
    work: MatchedEndToEndWorkV1
    status: str = SUCCESS_STATUS
    combined_confidence_lower: Fraction = COMBINED_CONFIDENCE_LOWER
    exact_probabilities_used_by_production: bool = False
    known_d4_prior_used_by_adaptive_arm: bool = True
    automatic_coordinate_discovery_claimed: bool = False
    broad_structural_generalization_claimed: bool = False
    broad_sample_efficiency_claimed: bool = False
    sample_tax_operator_claimed: bool = False
    official_execution_allowed: bool = False
    workload_economics_gate_run: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.preregistration)
            is not MatchedWorkloadPreregistrationV1
            or type(self.work) is not MatchedEndToEndWorkV1
        ):
            raise MatchedEndToEndInvariantViolation(
                "matched campaign rejects substituted authorities"
            )
        _cid(self.evidence_bundle_id, "matched campaign evidence")
        _exact_tuple(
            self.adaptive_models,
            MatchedAdaptiveModelResultV1,
            "matched campaign adaptive models",
        )
        _exact_tuple(
            self.occurrences,
            MatchedOccurrenceResultV1,
            "matched campaign occurrences",
        )
        model_by_context = {
            item.context.context_id: item for item in self.adaptive_models
        }
        expected_occurrences = (
            self.preregistration.source_preregistration.occurrences
        )
        if (
            len(self.adaptive_models) != raw.CONTEXT_COUNT
            or tuple(
                item.context.context_id for item in self.adaptive_models
            )
            != tuple(
                item.context_id
                for item in self.preregistration.source_preregistration.contexts
            )
            or len(self.occurrences) != raw.OCCURRENCE_COUNT
            or tuple(
                item.occurrence.occurrence_id for item in self.occurrences
            )
            != tuple(item.occurrence_id for item in expected_occurrences)
            or any(
                item.adaptive.context_model_result_id
                != model_by_context[
                    item.occurrence.context_id
                ].result_id
                or item.adaptive.adaptive_model_id
                != model_by_context[
                    item.occurrence.context_id
                ].adaptive_model.model_id
                for item in self.occurrences
            )
            or self.status != SUCCESS_STATUS
            or self.combined_confidence_lower
            != COMBINED_CONFIDENCE_LOWER
            or self.exact_probabilities_used_by_production is not False
            or self.known_d4_prior_used_by_adaptive_arm is not True
            or self.automatic_coordinate_discovery_claimed is not False
            or self.broad_structural_generalization_claimed is not False
            or self.broad_sample_efficiency_claimed is not False
            or self.sample_tax_operator_claimed is not False
            or self.official_execution_allowed is not False
            or self.workload_economics_gate_run is not False
        ):
            raise MatchedEndToEndInvariantViolation(
                "matched campaign identity, confidence, or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_end_to_end_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration": self.preregistration.to_document(),
            "evidence_bundle_id": self.evidence_bundle_id,
            "adaptive_models": [
                item.to_document() for item in self.adaptive_models
            ],
            "occurrences": [
                item.to_document() for item in self.occurrences
            ],
            "work": self.work.to_document(),
            "status": self.status,
            "combined_confidence_lower": _fdoc(
                self.combined_confidence_lower
            ),
            "exact_probabilities_used_by_production": (
                self.exact_probabilities_used_by_production
            ),
            "known_d4_prior_used_by_adaptive_arm": (
                self.known_d4_prior_used_by_adaptive_arm
            ),
            "automatic_coordinate_discovery_claimed": (
                self.automatic_coordinate_discovery_claimed
            ),
            "broad_structural_generalization_claimed": (
                self.broad_structural_generalization_claimed
            ),
            "broad_sample_efficiency_claimed": (
                self.broad_sample_efficiency_claimed
            ),
            "sample_tax_operator_claimed": (
                self.sample_tax_operator_claimed
            ),
            "official_execution_allowed": self.official_execution_allowed,
            "workload_economics_gate_run": (
                self.workload_economics_gate_run
            ),
        }

    @property
    def result_id(self) -> str:
        return _content_id("campaign", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _implementation_functions() -> tuple[Any, ...]:
    return (
        MatchedAcquisitionProfileV1,
        MatchedWorkloadPreregistrationV1,
        MatchedAdaptiveContextEvidenceV1,
        DirectGroundOutcomeAtomV1,
        DirectGroundRowCodebookV1,
        DirectPackedDrawBlockV1,
        DirectGroundRowLogV1,
        DirectOccurrenceEvidenceV1,
        MatchedEvidenceBundleV1,
        DirectH1ActionEstimateV1,
        DirectH1DecisionV1,
        DirectRootActionEstimateV1,
        DirectGroundPolicyDecisionV1,
        DirectRootCandidateV1,
        DirectGroundStatisticalPolicyV1,
        DirectGroundPlanProofV1,
        MatchedAdaptiveModelResultV1,
        MatchedAdaptiveOccurrenceResultV1,
        MatchedOccurrenceResultV1,
        MatchedEndToEndWorkV1,
        MatchedEndToEndCampaignResultV1,
        MatchedExactComparatorV1,
        MatchedEndToEndVerificationV1,
        preregister_matched_end_to_end_workload_v1,
        _state_key,
        _action_tuple,
        _action_from_tuple,
        _normalized_reward,
        _expected_direct_occurrence_shape,
        _interval,
        _direct_uniform_v1,
        _integer_cumulative_thresholds_v1,
        _sample_outcome_index,
        _direct_draw_block_nibbles_v1,
        _enumerate_direct_support_v1,
        _direct_codebook_v1,
        _acquire_direct_occurrence_v1,
        acquire_matched_end_to_end_evidence_v1,
        _row_counts,
        _build_h1_estimates_v1,
        _build_root_estimates_v1,
        _build_root_candidates_v1,
        plan_cold_direct_ground_v1,
        run_matched_end_to_end_workload_v1,
        _independent_direct_uniform_v1,
        _independent_direct_draw_block_nibbles_v1,
        _independently_replay_direct_occurrence_v1,
        _finite_policy_from_direct_v1,
        _evaluate_adaptive_semantic_schedule_v1,
        verify_matched_end_to_end_workload_v1,
    )


def _observed_implementation_sha256() -> str:
    source = "\n\n".join(
        inspect.getsource(item) for item in _implementation_functions()
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _validate_implementation_authority() -> None:
    if _observed_implementation_sha256() != IMPLEMENTATION_SHA256:
        raise MatchedEndToEndInvariantViolation(
            "V0-061 implementation differs from its frozen authority"
        )


def run_matched_end_to_end_workload_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: MatchedWorkloadPreregistrationV1,
    evidence_bundle: MatchedEvidenceBundleV1,
) -> MatchedEndToEndCampaignResultV1:
    """Build, plan, and certify both arms without exact-kernel access."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration)
        is not MatchedWorkloadPreregistrationV1
        or type(evidence_bundle) is not MatchedEvidenceBundleV1
    ):
        raise MatchedEndToEndInvariantViolation(
            "matched production runner rejects substituted inputs"
        )
    _validate_implementation_authority()
    expected = preregister_matched_end_to_end_workload_v1(catalogue)
    _runtime_shape(preregistration, expected, "matched preregistration")
    if preregistration.to_document() != expected.to_document():
        raise MatchedEndToEndInvariantViolation(
            "matched production preregistration mismatch"
        )
    if evidence_bundle.preregistration_id != preregistration.preregistration_id:
        raise MatchedEndToEndInvariantViolation(
            "matched evidence is stale or out of context"
        )
    adaptive_models: list[MatchedAdaptiveModelResultV1] = []
    adaptive_evidence_by_context = {
        item.context.context_id: item
        for item in evidence_bundle.adaptive_contexts
    }
    for context in preregistration.source_preregistration.contexts:
        context_evidence = adaptive_evidence_by_context[context.context_id]
        model = raw.build_raw_partial_statistical_model_v1(
            catalogue, context, context_evidence.adaptive_log
        )
        adaptive_models.append(
            MatchedAdaptiveModelResultV1(
                context,
                context_evidence.evidence_id,
                context_evidence.failed_proof.proof_id,
                model,
            )
        )
    model_by_context = {
        item.context.context_id: item for item in adaptive_models
    }
    direct_by_occurrence = {
        item.occurrence.occurrence_id: item
        for item in evidence_bundle.direct_occurrences
    }
    occurrence_results: list[MatchedOccurrenceResultV1] = []
    for occurrence in preregistration.source_preregistration.occurrences:
        model_result = model_by_context[occurrence.context_id]
        adaptive_proof = raw.solve_raw_partial_h2_v1(
            model_result.adaptive_model
        )
        if adaptive_proof.status != raw.CERTIFIED_STATUS:
            raise MatchedEndToEndInvariantViolation(
                "registered adaptive occurrence lost certification"
            )
        selected = adaptive_proof.selected_policy
        first_context_pass = occurrence.ordinal < raw.CONTEXT_COUNT
        adaptive_result = MatchedAdaptiveOccurrenceResultV1(
            occurrence,
            model_result.result_id,
            model_result.adaptive_model.model_id,
            adaptive_proof.proof_id,
            selected.schedule,
            selected.reward_lower,
            selected.reward_upper,
            selected.failure_lower,
            selected.failure_upper,
            (
                raw.ADAPTIVE_ROWS_PER_CONTEXT
                * raw.SAMPLE_COUNT_PER_ROW
                if first_context_pass
                else 0
            ),
            not first_context_pass,
        )
        direct_proof = plan_cold_direct_ground_v1(
            direct_by_occurrence[occurrence.occurrence_id]
        )
        occurrence_results.append(
            MatchedOccurrenceResultV1(
                occurrence, adaptive_result, direct_proof
            )
        )
    return MatchedEndToEndCampaignResultV1(
        preregistration,
        evidence_bundle.bundle_id,
        tuple(adaptive_models),
        tuple(occurrence_results),
        MatchedEndToEndWorkV1(),
    )


def _independent_direct_uniform_v1(
    seed: str,
    context_id: str,
    occurrence_id: str,
    row_id: str,
    sample_index: int,
) -> int:
    # Deliberately restate the counter protocol in the standalone lane.
    prefix = b"acfqp:direct-counter-uniform:v1\x00"
    material = (
        prefix
        + bytes(seed, "utf-8")
        + b"\x00"
        + bytes(context_id, "ascii")
        + b"\x00"
        + bytes(occurrence_id, "ascii")
        + b"\x00"
        + bytes(row_id, "ascii")
        + b"\x00"
        + int(sample_index).to_bytes(8, byteorder="big", signed=False)
    )
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest, "big")


def _independent_direct_draw_block_nibbles_v1(
    seed: str,
    context_id: str,
    occurrence_id: str,
    row_id: str,
    cumulative_thresholds: tuple[int, ...],
    start_index: int,
    draw_count: int,
) -> str:
    # Deliberately restate the counter protocol in the standalone lane.
    prefix = (
        b"acfqp:direct-counter-uniform:v1\x00"
        + bytes(seed, "utf-8")
        + b"\x00"
        + bytes(context_id, "ascii")
        + b"\x00"
        + bytes(occurrence_id, "ascii")
        + b"\x00"
        + bytes(row_id, "ascii")
        + b"\x00"
    )
    base_hasher = hashlib.sha256()
    base_hasher.update(prefix)
    hexadecimal = b"0123456789abcdef"
    encoded = bytearray(draw_count)
    for offset in range(draw_count):
        hasher = base_hasher.copy()
        hasher.update(
            int(start_index + offset).to_bytes(
                8, byteorder="big", signed=False
            )
        )
        uniform = int.from_bytes(
            hasher.digest(), byteorder="big", signed=False
        )
        outcome_index = bisect_right(
            cumulative_thresholds, uniform
        )
        if outcome_index >= len(cumulative_thresholds):
            raise MatchedEndToEndInvariantViolation(
                "independent direct thresholds omit uint256 support"
            )
        encoded[offset] = hexadecimal[outcome_index]
    return encoded.decode("ascii")


def _independently_replay_direct_occurrence_v1(
    evidence: DirectOccurrenceEvidenceV1,
    kernel: raw.RawSafeChainContextKernelV1,
) -> tuple[tuple[str, ...], int, int]:
    failures: list[str] = []
    expected_rows, catalogue_calls = _enumerate_direct_support_v1(
        kernel, evidence.occurrence
    )
    claimed_by_key = {
        (
            item.codebook.remaining,
            item.codebook.source_board,
            item.codebook.source_status,
            item.codebook.ground_action,
        ): item
        for item in evidence.rows
    }
    replayed_draws = 0
    replayed_rows = 0
    for remaining, state, action, outcomes in expected_rows:
        key = (
            remaining,
            state.board,
            state.status.value,
            _action_tuple(action),
        )
        claimed = claimed_by_key.get(key)
        if claimed is None:
            failures.append(
                f"DIRECT_ROW_MISSING:{evidence.occurrence.occurrence_id}"
            )
            continue
        expected_codebook = _direct_codebook_v1(
            evidence.occurrence,
            remaining,
            state,
            action,
            outcomes,
        )
        if (
            claimed.codebook.to_document()
            != expected_codebook.to_document()
        ):
            failures.append(
                f"DIRECT_CODEBOOK_REPLAY_MISMATCH:"
                f"{evidence.occurrence.occurrence_id}:{claimed.codebook.row_id}"
            )
        probabilities = tuple(item.probability for item in outcomes)
        cumulative_thresholds = _integer_cumulative_thresholds_v1(
            probabilities
        )
        claimed_row_id = claimed.codebook.row_id
        for block in claimed.blocks:
            expected_nibbles = (
                _independent_direct_draw_block_nibbles_v1(
                    block.seed,
                    evidence.occurrence.context_id,
                    evidence.occurrence.occurrence_id,
                    claimed_row_id,
                    cumulative_thresholds,
                    block.start_index,
                    block.draw_count,
                )
            )
            if block.outcome_nibbles_hex != expected_nibbles:
                failures.append(
                    f"DIRECT_DRAW_REPLAY_MISMATCH:"
                    f"{evidence.occurrence.occurrence_id}:"
                    f"{claimed_row_id}"
                )
            replayed_draws += block.draw_count
        replayed_rows += 1
    if (
        replayed_rows != evidence.transition_row_enumerations
        or len(expected_rows) != evidence.transition_row_enumerations
        or catalogue_calls != evidence.state_action_catalogue_calls
    ):
        failures.append(
            f"DIRECT_SUPPORT_COUNT_MISMATCH:"
            f"{evidence.occurrence.occurrence_id}"
        )
    if replayed_draws != evidence.total_draw_count:
        failures.append(
            f"DIRECT_DRAW_COUNT_MISMATCH:"
            f"{evidence.occurrence.occurrence_id}"
        )
    return tuple(sorted(set(failures))), replayed_draws, replayed_rows


def _finite_policy_from_direct_v1(
    policy: DirectGroundStatisticalPolicyV1,
) -> FiniteHorizonPolicy[G2048State, G2048Action]:
    return FiniteHorizonPolicy.from_mapping(
        {
            (
                item.remaining,
                G2048State(
                    item.source_board,
                    G2048Status(item.source_status),
                ),
            ): _action_from_tuple(item.ground_action)
            for item in policy.decisions
        }
    )


def _evaluate_adaptive_semantic_schedule_v1(
    kernel: raw.RawSafeChainContextKernelV1,
    occurrence: raw.RawContextOccurrenceV1,
    schedule: tuple[str, str, str],
) -> tuple[Fraction, Fraction]:
    if schedule != (
        G2048RelativeSurvivorLabel.TOWARD.value,
        G2048RelativeSurvivorLabel.AWAY.value,
        G2048RelativeSurvivorLabel.AWAY.value,
    ):
        raise MatchedEndToEndInvariantViolation(
            "standalone adaptive evaluator received an unregistered schedule"
        )
    adapter = G2048RelativeSurvivorAdapter()
    query = raw._query_for_occurrence_v1(occurrence)
    memo: dict[tuple[int, G2048State], tuple[Fraction, Fraction]] = {}

    def evaluate_state(
        remaining: int, state: G2048State
    ) -> tuple[Fraction, Fraction]:
        marker = (remaining, state)
        if marker in memo:
            return memo[marker]
        if remaining <= 0 or kernel.is_terminal(state):
            memo[marker] = (Fraction(0), Fraction(0))
            return memo[marker]
        label = (
            G2048RelativeSurvivorLabel.TOWARD
            if remaining == 2
            else G2048RelativeSurvivorLabel.AWAY
        )
        action_distribution = adapter.concretize(
            kernel, state, label
        )
        reward = Fraction(0)
        failure = Fraction(0)
        for action_probability, action in action_distribution:
            for outcome in kernel.step(state, action):
                branch_probability = (
                    action_probability * outcome.probability
                )
                branch_reward = _normalized_reward(outcome)
                if outcome.failure:
                    branch_failure = Fraction(1)
                elif outcome.terminal:
                    branch_failure = Fraction(0)
                else:
                    continuation_reward, branch_failure = evaluate_state(
                        remaining - 1, outcome.next_state
                    )
                    branch_reward += continuation_reward
                reward += branch_probability * branch_reward
                failure += branch_probability * branch_failure
        memo[marker] = (reward, failure)
        return memo[marker]

    total_reward = Fraction(0)
    total_failure = Fraction(0)
    for probability, state in query.initial_distribution:
        reward, failure = evaluate_state(query.horizon, state)
        total_reward += probability * reward
        total_failure += probability * failure
    return total_reward, total_failure


@dataclass(frozen=True, slots=True)
class MatchedExactComparatorV1:
    context_id: str
    occurrence_id: str
    adaptive_exact_reward: Fraction
    adaptive_exact_failure: Fraction
    direct_exact_reward: Fraction
    direct_exact_failure: Fraction
    j0_exact_reward: Fraction
    j0_exact_failure: Fraction
    j0_composed_candidate_count: int
    verification_lane: str = "standalone_evaluation"

    def __post_init__(self) -> None:
        _cid(self.context_id, "matched comparator context")
        _cid(self.occurrence_id, "matched comparator occurrence")
        if (
            any(
                type(value) is not Fraction
                for value in (
                    self.adaptive_exact_reward,
                    self.adaptive_exact_failure,
                    self.direct_exact_reward,
                    self.direct_exact_failure,
                    self.j0_exact_reward,
                    self.j0_exact_failure,
                )
            )
            or self.adaptive_exact_reward
            != self.direct_exact_reward
            or self.direct_exact_reward != self.j0_exact_reward
            or self.j0_exact_reward != Fraction(3, 64)
            or self.adaptive_exact_failure
            != self.j0_exact_failure
            or not 0
            <= self.j0_exact_failure
            <= self.direct_exact_failure
            < Fraction(1, 20)
            or self.direct_failure_gap_from_j0 > Fraction(1, 1000)
            or not 0 <= self.j0_exact_failure < Fraction(1, 20)
            or type(self.j0_composed_candidate_count) is not int
            or self.j0_composed_candidate_count <= 0
            or self.verification_lane != "standalone_evaluation"
        ):
            raise MatchedEndToEndInvariantViolation(
                "matched exact comparator changed"
            )

    @property
    def direct_failure_gap_from_j0(self) -> Fraction:
        return self.direct_exact_failure - self.j0_exact_failure

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_end_to_end_exact_comparator.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "occurrence_id": self.occurrence_id,
            "adaptive_exact_reward": _fdoc(
                self.adaptive_exact_reward
            ),
            "adaptive_exact_failure": _fdoc(
                self.adaptive_exact_failure
            ),
            "direct_exact_reward": _fdoc(self.direct_exact_reward),
            "direct_exact_failure": _fdoc(self.direct_exact_failure),
            "j0_exact_reward": _fdoc(self.j0_exact_reward),
            "j0_exact_failure": _fdoc(self.j0_exact_failure),
            "direct_failure_gap_from_j0": _fdoc(
                self.direct_failure_gap_from_j0
            ),
            "j0_composed_candidate_count": (
                self.j0_composed_candidate_count
            ),
            "verification_lane": self.verification_lane,
        }

    @property
    def comparator_id(self) -> str:
        return _content_id("exact_comparator", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "comparator_id": self.comparator_id}


@dataclass(frozen=True, slots=True)
class MatchedEndToEndVerificationV1:
    claimed_result_id: str
    replay_result_id: str
    evidence_bundle_id: str
    failures: tuple[str, ...]
    exact_comparators: tuple[MatchedExactComparatorV1, ...]
    adaptive_individual_draws_replayed: int
    direct_individual_draws_replayed: int
    direct_transition_rows_replayed: int
    exact_ground_composed_candidates: int
    verification_lane: str = "standalone_evaluation"
    production_kernel_access: int = 0
    broad_sample_efficiency_promotion_authorized: bool = False
    sample_tax_operator_promotion_authorized: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.claimed_result_id, "matched verification claimed result"),
            (self.replay_result_id, "matched verification replay result"),
            (self.evidence_bundle_id, "matched verification evidence"),
        ):
            _cid(value, field_name)
        _exact_tuple(
            self.exact_comparators,
            MatchedExactComparatorV1,
            "matched verification comparators",
        )
        if (
            type(self.failures) is not tuple
            or self.failures != tuple(sorted(set(self.failures)))
            or len(self.exact_comparators) != raw.OCCURRENCE_COUNT
            or self.adaptive_individual_draws_replayed
            != ADAPTIVE_TOTAL_DRAWS
            or self.direct_individual_draws_replayed
            != DIRECT_TOTAL_DRAWS
            or self.direct_transition_rows_replayed
            != DIRECT_TOTAL_ACTION_ROWS
            or self.exact_ground_composed_candidates
            != sum(
                item.j0_composed_candidate_count
                for item in self.exact_comparators
            )
            or self.verification_lane != "standalone_evaluation"
            or self.production_kernel_access != 0
            or self.broad_sample_efficiency_promotion_authorized
            is not False
            or self.sample_tax_operator_promotion_authorized is not False
        ):
            raise MatchedEndToEndInvariantViolation(
                "matched verification work or claim boundary changed"
            )

    @property
    def verified(self) -> bool:
        return (
            not self.failures
            and self.claimed_result_id == self.replay_result_id
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_end_to_end_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "claimed_result_id": self.claimed_result_id,
            "replay_result_id": self.replay_result_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "failures": list(self.failures),
            "verified": self.verified,
            "exact_comparators": [
                item.to_document() for item in self.exact_comparators
            ],
            "adaptive_individual_draws_replayed": (
                self.adaptive_individual_draws_replayed
            ),
            "direct_individual_draws_replayed": (
                self.direct_individual_draws_replayed
            ),
            "direct_transition_rows_replayed": (
                self.direct_transition_rows_replayed
            ),
            "exact_ground_composed_candidates": (
                self.exact_ground_composed_candidates
            ),
            "verification_lane": self.verification_lane,
            "production_kernel_access": self.production_kernel_access,
            "broad_sample_efficiency_promotion_authorized": (
                self.broad_sample_efficiency_promotion_authorized
            ),
            "sample_tax_operator_promotion_authorized": (
                self.sample_tax_operator_promotion_authorized
            ),
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_matched_end_to_end_workload_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: MatchedWorkloadPreregistrationV1,
    evidence_bundle: MatchedEvidenceBundleV1,
    kernels: tuple[raw.RawSafeChainContextKernelV1, ...],
    claimed_result: MatchedEndToEndCampaignResultV1,
) -> MatchedEndToEndVerificationV1:
    """Replay production, every raw draw, all support rows, and exact J0."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration)
        is not MatchedWorkloadPreregistrationV1
        or type(evidence_bundle) is not MatchedEvidenceBundleV1
        or type(claimed_result)
        is not MatchedEndToEndCampaignResultV1
    ):
        raise MatchedEndToEndInvariantViolation(
            "matched verifier rejects substituted inputs"
        )
    _exact_tuple(
        kernels,
        raw.RawSafeChainContextKernelV1,
        "matched verification kernels",
    )
    if len(kernels) != raw.CONTEXT_COUNT:
        raise MatchedEndToEndInvariantViolation(
            "matched verifier requires exactly three kernels"
        )
    expected = run_matched_end_to_end_workload_v1(
        catalogue, preregistration, evidence_bundle
    )
    _runtime_shape(claimed_result, expected, "claimed matched campaign")
    failures: list[str] = []
    if claimed_result.to_document() != expected.to_document():
        failures.append("MATCHED_CAMPAIGN_RECONSTRUCTION_MISMATCH")
    kernel_by_context = {
        context.context_id: kernel
        for context, kernel in zip(
            preregistration.source_preregistration.contexts, kernels
        )
    }
    context_by_id = {
        item.context_id: item
        for item in preregistration.source_preregistration.contexts
    }
    adaptive_draws = 0
    for item in evidence_bundle.adaptive_contexts:
        kernel = kernel_by_context[item.context.context_id]
        replay_failures, replay_count = (
            raw._independently_replay_raw_log_v1(
                catalogue,
                item.context,
                kernel,
                item.adaptive_log,
            )
        )
        failures.extend(replay_failures)
        adaptive_draws += replay_count
    direct_draws = 0
    direct_rows = 0
    for item in evidence_bundle.direct_occurrences:
        replay_failures, replay_count, row_count = (
            _independently_replay_direct_occurrence_v1(
                item, kernel_by_context[item.occurrence.context_id]
            )
        )
        failures.extend(replay_failures)
        direct_draws += replay_count
        direct_rows += row_count
    result_by_occurrence = {
        item.occurrence.occurrence_id: item
        for item in claimed_result.occurrences
    }
    comparators: list[MatchedExactComparatorV1] = []
    for occurrence in preregistration.source_preregistration.occurrences:
        result = result_by_occurrence[occurrence.occurrence_id]
        kernel = kernel_by_context[occurrence.context_id]
        query = raw._query_for_occurrence_v1(occurrence)
        direct_evaluation = evaluate_ground_policy(
            kernel,
            query,
            _finite_policy_from_direct_v1(
                result.direct.selected_policy
            ),
        )
        adaptive_reward, adaptive_failure = (
            _evaluate_adaptive_semantic_schedule_v1(
                kernel,
                occurrence,
                result.adaptive.selected_schedule,
            )
        )
        j0 = solve_ground_pareto(kernel, query)
        if j0.selected is None:
            failures.append(
                f"EXACT_J0_INFEASIBLE:{occurrence.occurrence_id}"
            )
            continue
        comparator = MatchedExactComparatorV1(
            occurrence.context_id,
            occurrence.occurrence_id,
            adaptive_reward,
            adaptive_failure,
            direct_evaluation.expected_reward,
            direct_evaluation.failure_probability,
            j0.selected.expected_reward,
            j0.selected.failure_probability,
            j0.composed_candidate_count,
        )
        comparators.append(comparator)
        if not (
            result.adaptive.reward_lower
            <= adaptive_reward
            <= result.adaptive.reward_upper
            and result.adaptive.failure_lower
            <= adaptive_failure
            <= result.adaptive.failure_upper
        ):
            failures.append(
                f"ADAPTIVE_EXACT_VALUE_OUTSIDE_CERTIFICATE:"
                f"{occurrence.occurrence_id}"
            )
        selected_direct = result.direct.selected_policy
        if not (
            selected_direct.reward_lower
            <= direct_evaluation.expected_reward
            <= selected_direct.reward_upper
            and selected_direct.failure_lower
            <= direct_evaluation.failure_probability
            <= selected_direct.failure_upper
        ):
            failures.append(
                f"DIRECT_EXACT_VALUE_OUTSIDE_CERTIFICATE:"
                f"{occurrence.occurrence_id}"
            )
        if context_by_id[occurrence.context_id].context_id != (
            comparator.context_id
        ):
            failures.append(
                f"COMPARATOR_CONTEXT_MISMATCH:{occurrence.occurrence_id}"
            )
    return MatchedEndToEndVerificationV1(
        claimed_result.result_id,
        expected.result_id,
        evidence_bundle.bundle_id,
        tuple(sorted(set(failures))),
        tuple(comparators),
        adaptive_draws,
        direct_draws,
        direct_rows,
        sum(item.j0_composed_candidate_count for item in comparators),
    )


__all__ = [
    "ADAPTIVE_TOTAL_DRAWS",
    "COMBINED_CONFIDENCE_LOWER",
    "COMBINED_FAMILY_TAIL_UPPER",
    "CONTRACT_VERSION",
    "DIRECT_CERTIFIED_STATUS",
    "DIRECT_HOEFFDING_RADIUS",
    "DIRECT_SAMPLE_COUNT_PER_ROW",
    "DIRECT_TOTAL_ACTION_ROWS",
    "DIRECT_TOTAL_DRAWS",
    "IMPLEMENTATION_SHA256",
    "MatchedAcquisitionProfileV1",
    "MatchedAdaptiveContextEvidenceV1",
    "MatchedAdaptiveModelResultV1",
    "MatchedAdaptiveOccurrenceResultV1",
    "MatchedEndToEndCampaignResultV1",
    "MatchedEndToEndInvariantViolation",
    "MatchedEndToEndVerificationV1",
    "MatchedEndToEndWorkV1",
    "MatchedEvidenceBundleV1",
    "MatchedExactComparatorV1",
    "MatchedOccurrenceResultV1",
    "MatchedWorkloadPreregistrationV1",
    "PROFILE_KEY",
    "REGISTERED_DRAW_RATIO",
    "SUCCESS_STATUS",
    "DirectGroundPlanProofV1",
    "DirectGroundRowLogV1",
    "DirectGroundStatisticalPolicyV1",
    "DirectOccurrenceEvidenceV1",
    "acquire_matched_end_to_end_evidence_v1",
    "plan_cold_direct_ground_v1",
    "preregister_matched_end_to_end_workload_v1",
    "run_matched_end_to_end_workload_v1",
    "verify_matched_end_to_end_workload_v1",
]
