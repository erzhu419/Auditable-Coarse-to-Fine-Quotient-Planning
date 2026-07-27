"""Raw-replayable multi-context statistical acquisition control.

V0-060 replaces V0-059's trusted aggregate G2048 ledger with compact packed
individual stochastic observations.  Three separately keyed safe-chain
spawn laws are preregistered.  For every context, a model-only failed proof
selects three necessary semantic rows before the adaptive acquisition lane is
allowed to draw them.  A matched nonadaptive control draws all six rows.

The model builder and planner accept no kernel.  Exact kernels are confined
to the scoped acquisition authority and the standalone verifier.  The
adaptive model honestly leaves three legal rows vacuous.  This module proves
only a finite replayable acquisition/control trace; it does not claim an
automatic sample-tax operator, broad structural generalization, automatic D4
discovery, or official execution.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import inspect
import math
from itertools import product
from typing import Any, Iterable, Mapping

from acfqp.core import Outcome, QuerySpec
from acfqp.domains.g2048 import (
    G2048Action,
    G2048Kernel,
    G2048State,
    G2048Status,
    SAFE_CHAIN_BASE_STATE,
    orbit,
)
from acfqp.domains.semantic import (
    G2048RelativeSurvivorAdapter,
    G2048RelativeSurvivorLabel,
)
from acfqp.multidomain_statistical_campaign_v1 import (
    G2048StatisticalCatalogueV1,
    StatisticalCellKind,
    StatisticalRowCatalogueV1,
    registered_g2048_d4_statistical_catalogue_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.planning.ground import solve_ground_pareto


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.24.0"
PROFILE_KEY = "g2048_raw_replayable_multicontext_partial_statistical_v0"
ACQUISITION_PROFILE_KEY = (
    "g2048_certificate_directed_vs_uniform_acquisition_v0"
)
SUCCESS_STATUS = (
    "CERTIFIED_REGISTERED_RAW_REPLAYABLE_MULTICONTEXT_ACQUISITION_CONTROL"
)
FAILED_STATUS = "FAILED_PROOF_MISSING_STATISTICAL_ROWS"
CERTIFIED_STATUS = "CERTIFIED_STATISTICAL_PARTIAL_H2_PLAN"

SAMPLE_COUNT_PER_ROW = 16_384
DRAW_BLOCK_SIZE = 4_096
BLOCKS_PER_ROW = SAMPLE_COUNT_PER_ROW // DRAW_BLOCK_SIZE
HOEFFDING_RADIUS = Fraction(1, 64)
PER_COORDINATE_TAIL_UPPER = Fraction(1, 1400)
ADAPTIVE_ROWS_PER_CONTEXT = 3
DIRECT_ROWS_PER_CONTEXT = 6
CONTEXT_COUNT = 3
OCCURRENCE_COUNT = 6
ADAPTIVE_TOTAL_DRAWS = (
    CONTEXT_COUNT * ADAPTIVE_ROWS_PER_CONTEXT * SAMPLE_COUNT_PER_ROW
)
DIRECT_TOTAL_DRAWS = (
    CONTEXT_COUNT * DIRECT_ROWS_PER_CONTEXT * SAMPLE_COUNT_PER_ROW
)
GLOBAL_COORDINATE_OBLIGATIONS = (
    2
    * CONTEXT_COUNT
    * (ADAPTIVE_ROWS_PER_CONTEXT + DIRECT_ROWS_PER_CONTEXT)
)
GLOBAL_FAMILY_TAIL_UPPER = (
    GLOBAL_COORDINATE_OBLIGATIONS * PER_COORDINATE_TAIL_UPPER
)
GLOBAL_CONFIDENCE_LOWER = 1 - GLOBAL_FAMILY_TAIL_UPPER

ADAPTIVE_ROW_KEYS = (
    "ROOT_TOWARD",
    "CHAIN_A_AWAY",
    "CHAIN_B_AWAY",
)
ALL_ROW_KEYS = (
    "ROOT_AWAY",
    "ROOT_TOWARD",
    "CHAIN_A_AWAY",
    "CHAIN_A_TOWARD",
    "CHAIN_B_AWAY",
    "CHAIN_B_TOWARD",
)

IMPLEMENTATION_SHA256 = (
    "364696557d33f67a5ff96a97684917a822f49beb62ad95d25c4447fbe81544b6"
)

DOMAIN_TAGS = {
    "context": "acfqp:raw-multicontext-structural-context:v1",
    "acquisition_profile": "acfqp:raw-acquisition-profile:v1",
    "occurrence": "acfqp:raw-multicontext-occurrence:v1",
    "preregistration": "acfqp:raw-multicontext-preregistration:v1",
    "interval": "acfqp:raw-statistical-interval:v1",
    "partial_row": "acfqp:raw-partial-statistical-row:v1",
    "partial_model": "acfqp:raw-partial-statistical-model:v1",
    "policy": "acfqp:raw-partial-statistical-policy:v1",
    "proof": "acfqp:raw-partial-statistical-proof:v1",
    "authorization": "acfqp:raw-adaptive-row-authorization:v1",
    "outcome_atom": "acfqp:raw-ground-outcome-atom:v1",
    "codebook": "acfqp:raw-row-codebook:v1",
    "draw_block": "acfqp:packed-raw-draw-block:v1",
    "raw_log": "acfqp:packed-raw-context-log:v1",
    "evidence": "acfqp:raw-multicontext-evidence:v1",
    "evidence_bundle": "acfqp:raw-multicontext-evidence-bundle:v1",
    "context_result": "acfqp:raw-multicontext-context-result:v1",
    "occurrence_result": "acfqp:raw-multicontext-occurrence-result:v1",
    "work": "acfqp:raw-multicontext-work:v1",
    "campaign": "acfqp:raw-multicontext-campaign:v1",
    "exact_comparator": "acfqp:raw-multicontext-exact-comparator:v1",
    "verification": "acfqp:raw-multicontext-verification:v1",
}


class RawMultiContextInvariantViolation(ValueError):
    """A raw log, context, proof, campaign, or replay is inconsistent."""


class AcquisitionLane(str, Enum):
    ADAPTIVE = "certificate_directed_adaptive"
    DIRECT = "uniform_all_rows_direct_control"


class RowEvidence(str, Enum):
    MISSING = "missing"
    RAW_STATISTICAL = "raw_statistical_high_probability"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role].encode("utf-8")
    except (KeyError, TypeError, ValueError) as error:
        raise RawMultiContextInvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise RawMultiContextInvariantViolation(
            f"{field_name} must be a full content ID"
        ) from error


def _fraction(value: Any, field_name: str) -> Fraction:
    if type(value) not in (int, Fraction):
        raise RawMultiContextInvariantViolation(f"{field_name} must be exact")
    return Fraction(value)


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _exact_tuple(value: Any, item_type: type, field_name: str) -> tuple[Any, ...]:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise RawMultiContextInvariantViolation(
            f"{field_name} rejects nested runtime substitutions"
        )
    return value


def _runtime_shape(claimed: Any, expected: Any, path: str) -> None:
    if type(claimed) is not type(expected):
        raise RawMultiContextInvariantViolation(
            f"{path} contains a nested runtime substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise RawMultiContextInvariantViolation(f"{path} length changed")
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


@dataclass(frozen=True, slots=True)
class RawSafeChainStructuralContextV1:
    context_key: str
    rank_one_probability: Fraction
    catalogue_id: str
    board_size: int = 2
    rank_cap: int = 6
    horizon: int = 2
    delta: Fraction = Fraction(1, 20)
    known_d4_prior: bool = True
    automatic_structure_discovery_claimed: bool = False

    def __post_init__(self) -> None:
        _cid(self.catalogue_id, "context catalogue")
        if (
            type(self.context_key) is not str
            or not self.context_key
            or type(self.rank_one_probability) is not Fraction
            or self.rank_one_probability
            not in (
                Fraction(199, 200),
                Fraction(249, 250),
                Fraction(999, 1000),
            )
            or self.board_size != 2
            or self.rank_cap != 6
            or self.horizon != 2
            or self.delta != Fraction(1, 20)
            or self.known_d4_prior is not True
            or self.automatic_structure_discovery_claimed is not False
        ):
            raise RawMultiContextInvariantViolation(
                "raw safe-chain structural context changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_safe_chain_structural_context.v1",
            "schema_version": SCHEMA_VERSION,
            "context_key": self.context_key,
            "rank_one_probability": _fdoc(self.rank_one_probability),
            "rank_two_probability": _fdoc(1 - self.rank_one_probability),
            "catalogue_id": self.catalogue_id,
            "board_size": self.board_size,
            "rank_cap": self.rank_cap,
            "horizon": self.horizon,
            "delta": _fdoc(self.delta),
            "known_d4_prior": self.known_d4_prior,
            "automatic_structure_discovery_claimed": (
                self.automatic_structure_discovery_claimed
            ),
            "base_fixture_mutated": False,
        }

    @property
    def context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


def registered_raw_structural_contexts_v1(
    catalogue: G2048StatisticalCatalogueV1,
) -> tuple[RawSafeChainStructuralContextV1, ...]:
    if type(catalogue) is not G2048StatisticalCatalogueV1:
        raise RawMultiContextInvariantViolation(
            "context registry rejects substituted catalogues"
        )
    probabilities = (
        ("g2048_safe_chain_raw_p199_200_v0", Fraction(199, 200)),
        ("g2048_safe_chain_raw_p249_250_v0", Fraction(249, 250)),
        ("g2048_safe_chain_raw_p999_1000_v0", Fraction(999, 1000)),
    )
    return tuple(
        RawSafeChainStructuralContextV1(key, probability, catalogue.catalogue_id)
        for key, probability in probabilities
    )


@dataclass(frozen=True, slots=True)
class RawSafeChainContextKernelV1(G2048Kernel):
    """Exact acquisition/evaluation kernel for one separately keyed context."""

    context_key: str = "g2048_safe_chain_raw_p199_200_v0"
    rank_one_probability: Fraction = Fraction(199, 200)

    def __post_init__(self) -> None:
        G2048Kernel.__post_init__(self)
        if (
            self.size != 2
            or type(self.context_key) is not str
            or not self.context_key
            or type(self.rank_one_probability) is not Fraction
            or not 0 < self.rank_one_probability < 1
        ):
            raise RawMultiContextInvariantViolation(
                "raw context kernel is structurally invalid"
            )

    @property
    def spawn_distribution(self) -> tuple[tuple[int, Fraction], ...]:
        return (
            (1, self.rank_one_probability),
            (2, 1 - self.rank_one_probability),
        )

    def structural_document(self) -> dict[str, Any]:
        return {
            "context_key": self.context_key,
            "rank_one_probability": _fdoc(self.rank_one_probability),
            "board_size": self.size,
            "rank_cap": self.rank_cap,
            "horizon": 2,
            "known_d4_prior": True,
        }


def registered_raw_context_kernels_v1() -> tuple[RawSafeChainContextKernelV1, ...]:
    catalogue = registered_g2048_d4_statistical_catalogue_v1()
    return tuple(
        RawSafeChainContextKernelV1(
            size=2,
            context_key=context.context_key,
            rank_one_probability=context.rank_one_probability,
        )
        for context in registered_raw_structural_contexts_v1(catalogue)
    )


@dataclass(frozen=True, slots=True)
class RawAcquisitionProfileV1:
    adaptive_row_keys: tuple[str, ...] = ADAPTIVE_ROW_KEYS
    direct_row_keys: tuple[str, ...] = ALL_ROW_KEYS
    sample_count_per_row: int = SAMPLE_COUNT_PER_ROW
    draw_block_size: int = DRAW_BLOCK_SIZE
    radius: Fraction = HOEFFDING_RADIUS
    exponent: Fraction = Fraction(8)
    taylor_degree: int = 13
    exponential_denominator_lower: int = 2800
    per_coordinate_tail_upper: Fraction = PER_COORDINATE_TAIL_UPPER
    global_coordinate_obligations: int = GLOBAL_COORDINATE_OBLIGATIONS
    global_family_tail_upper: Fraction = GLOBAL_FAMILY_TAIL_UPPER
    global_confidence_lower: Fraction = GLOBAL_CONFIDENCE_LOWER
    adaptive_seed: str = "acfqp-v0060-adaptive-seed-v1"
    direct_seed: str = "acfqp-v0060-direct-seed-v1"

    def __post_init__(self) -> None:
        taylor = sum(
            (Fraction(8**index, math.factorial(index)) for index in range(14)),
            Fraction(0),
        )
        if (
            self.adaptive_row_keys != ADAPTIVE_ROW_KEYS
            or self.direct_row_keys != ALL_ROW_KEYS
            or self.sample_count_per_row != SAMPLE_COUNT_PER_ROW
            or self.draw_block_size != DRAW_BLOCK_SIZE
            or self.sample_count_per_row % self.draw_block_size
            or self.radius != HOEFFDING_RADIUS
            or self.exponent
            != 2 * self.sample_count_per_row * self.radius**2
            or self.exponent != 8
            or self.taylor_degree != 13
            or taylor <= self.exponential_denominator_lower
            or self.exponential_denominator_lower != 2800
            or self.per_coordinate_tail_upper
            != Fraction(2, self.exponential_denominator_lower)
            or self.per_coordinate_tail_upper
            != PER_COORDINATE_TAIL_UPPER
            or self.global_coordinate_obligations
            != GLOBAL_COORDINATE_OBLIGATIONS
            or self.global_family_tail_upper
            != self.global_coordinate_obligations
            * self.per_coordinate_tail_upper
            or self.global_family_tail_upper != Fraction(27, 700)
            or self.global_confidence_lower
            != 1 - self.global_family_tail_upper
            or self.global_confidence_lower != Fraction(673, 700)
            or self.global_family_tail_upper >= Fraction(1, 20)
            or self.adaptive_seed != "acfqp-v0060-adaptive-seed-v1"
            or self.direct_seed != "acfqp-v0060-direct-seed-v1"
        ):
            raise RawMultiContextInvariantViolation(
                "raw acquisition/calibration profile changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_acquisition_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": ACQUISITION_PROFILE_KEY,
            "adaptive_row_keys": list(self.adaptive_row_keys),
            "direct_row_keys": list(self.direct_row_keys),
            "sample_count_per_row": self.sample_count_per_row,
            "draw_block_size": self.draw_block_size,
            "radius": _fdoc(self.radius),
            "exponent": _fdoc(self.exponent),
            "taylor_degree": self.taylor_degree,
            "exponential_denominator_lower": (
                self.exponential_denominator_lower
            ),
            "per_coordinate_tail_upper": _fdoc(
                self.per_coordinate_tail_upper
            ),
            "global_coordinate_obligations": (
                self.global_coordinate_obligations
            ),
            "global_family_tail_upper": _fdoc(
                self.global_family_tail_upper
            ),
            "global_confidence_lower": _fdoc(self.global_confidence_lower),
            "adaptive_seed": self.adaptive_seed,
            "direct_seed": self.direct_seed,
            "individual_draws_required": True,
            "aggregate_only_input_forbidden": True,
        }

    @property
    def profile_id(self) -> str:
        return _content_id("acquisition_profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


@dataclass(frozen=True, slots=True)
class RawContextOccurrenceV1:
    ordinal: int
    context_id: str
    context_key: str
    initial_mode: str
    initial_boards: tuple[tuple[int, ...], ...]
    horizon: int = 2
    delta: Fraction = Fraction(1, 20)
    held_out_from_model_construction: bool = True

    def __post_init__(self) -> None:
        _cid(self.context_id, "occurrence context")
        if (
            type(self.ordinal) is not int
            or self.ordinal < 0
            or type(self.context_key) is not str
            or not self.context_key
            or self.initial_mode not in ("D4_POINT", "D4_UNIFORM")
            or type(self.initial_boards) is not tuple
            or any(
                type(board) is not tuple
                or len(board) != 4
                or any(type(rank) is not int for rank in board)
                for board in self.initial_boards
            )
            or self.horizon != 2
            or self.delta != Fraction(1, 20)
            or self.held_out_from_model_construction is not True
        ):
            raise RawMultiContextInvariantViolation(
                "raw context occurrence changed"
            )
        if self.initial_mode == "D4_POINT":
            if len(self.initial_boards) != 1:
                raise RawMultiContextInvariantViolation(
                    "point occurrence must contain one board"
                )
        elif (
            len(self.initial_boards) != 8
            or self.initial_boards != tuple(sorted(set(self.initial_boards)))
        ):
            raise RawMultiContextInvariantViolation(
                "uniform occurrence must contain the complete D4 orbit"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_context_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "context_id": self.context_id,
            "context_key": self.context_key,
            "initial_mode": self.initial_mode,
            "initial_boards": [list(board) for board in self.initial_boards],
            "horizon": self.horizon,
            "delta": _fdoc(self.delta),
            "held_out_from_model_construction": (
                self.held_out_from_model_construction
            ),
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("occurrence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


def _registered_occurrences(
    contexts: tuple[RawSafeChainStructuralContextV1, ...],
) -> tuple[RawContextOccurrenceV1, ...]:
    boards = tuple(state.board for state in orbit(SAFE_CHAIN_BASE_STATE))
    rows: list[RawContextOccurrenceV1] = []
    for context in contexts:
        rows.append(
            RawContextOccurrenceV1(
                len(rows),
                context.context_id,
                context.context_key,
                "D4_POINT",
                (boards[0],),
            )
        )
    for context in contexts:
        rows.append(
            RawContextOccurrenceV1(
                len(rows),
                context.context_id,
                context.context_key,
                "D4_UNIFORM",
                boards,
            )
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class RawMultiContextPreregistrationV1:
    catalogue_id: str
    contexts: tuple[RawSafeChainStructuralContextV1, ...]
    acquisition_profile: RawAcquisitionProfileV1
    occurrences: tuple[RawContextOccurrenceV1, ...]
    prospective_log_ids_absent: bool = True
    prospective_model_ids_absent: bool = True
    prospective_plan_ids_absent: bool = True
    unregistered_context_reuse_forbidden: bool = True
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        _cid(self.catalogue_id, "preregistration catalogue")
        _exact_tuple(
            self.contexts,
            RawSafeChainStructuralContextV1,
            "preregistered contexts",
        )
        _exact_tuple(
            self.occurrences,
            RawContextOccurrenceV1,
            "preregistered occurrences",
        )
        if type(self.acquisition_profile) is not RawAcquisitionProfileV1:
            raise RawMultiContextInvariantViolation(
                "preregistration rejects substituted profiles"
            )
        expected_contexts = registered_raw_structural_contexts_v1(
            registered_g2048_d4_statistical_catalogue_v1()
        )
        if (
            self.contexts != expected_contexts
            or self.catalogue_id
            != registered_g2048_d4_statistical_catalogue_v1().catalogue_id
            or self.occurrences != _registered_occurrences(self.contexts)
            or self.prospective_log_ids_absent is not True
            or self.prospective_model_ids_absent is not True
            or self.prospective_plan_ids_absent is not True
            or self.unregistered_context_reuse_forbidden is not True
            or self.official_execution_allowed is not False
        ):
            raise RawMultiContextInvariantViolation(
                "raw preregistration chronology or scope changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_multicontext_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "implementation_sha256": IMPLEMENTATION_SHA256,
            "catalogue_id": self.catalogue_id,
            "contexts": [item.to_document() for item in self.contexts],
            "acquisition_profile": self.acquisition_profile.to_document(),
            "occurrences": [item.to_document() for item in self.occurrences],
            "prospective_log_ids_absent": self.prospective_log_ids_absent,
            "prospective_model_ids_absent": self.prospective_model_ids_absent,
            "prospective_plan_ids_absent": self.prospective_plan_ids_absent,
            "unregistered_context_reuse_forbidden": (
                self.unregistered_context_reuse_forbidden
            ),
            "official_execution_allowed": self.official_execution_allowed,
        }

    @property
    def preregistration_id(self) -> str:
        return _content_id("preregistration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "preregistration_id": self.preregistration_id}


def preregister_raw_multicontext_campaign_v1(
    catalogue: G2048StatisticalCatalogueV1,
) -> RawMultiContextPreregistrationV1:
    if type(catalogue) is not G2048StatisticalCatalogueV1:
        raise RawMultiContextInvariantViolation(
            "raw preregistration rejects substituted catalogues"
        )
    expected = registered_g2048_d4_statistical_catalogue_v1()
    if catalogue.to_document() != expected.to_document():
        raise RawMultiContextInvariantViolation(
            "raw preregistration requires the registered probability-free catalogue"
        )
    contexts = registered_raw_structural_contexts_v1(catalogue)
    return RawMultiContextPreregistrationV1(
        catalogue.catalogue_id,
        contexts,
        RawAcquisitionProfileV1(),
        _registered_occurrences(contexts),
    )


@dataclass(frozen=True, slots=True)
class RawProbabilityIntervalV1:
    destination_cell_id: str
    lower: Fraction
    upper: Fraction
    empirical_probability: Fraction | None

    def __post_init__(self) -> None:
        _cid(self.destination_cell_id, "probability interval destination")
        if (
            type(self.lower) is not Fraction
            or type(self.upper) is not Fraction
            or not 0 <= self.lower <= self.upper <= 1
            or (
                self.empirical_probability is not None
                and (
                    type(self.empirical_probability) is not Fraction
                    or not self.lower
                    <= self.empirical_probability
                    <= self.upper
                )
            )
        ):
            raise RawMultiContextInvariantViolation(
                "raw probability interval is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_probability_interval.v1",
            "schema_version": SCHEMA_VERSION,
            "destination_cell_id": self.destination_cell_id,
            "lower": _fdoc(self.lower),
            "upper": _fdoc(self.upper),
            "empirical_probability": (
                None
                if self.empirical_probability is None
                else _fdoc(self.empirical_probability)
            ),
        }

    @property
    def interval_id(self) -> str:
        return _content_id("interval", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "interval_id": self.interval_id}


@dataclass(frozen=True, slots=True)
class RawPartialStatisticalRowV1:
    catalogue_row: StatisticalRowCatalogueV1
    evidence: RowEvidence
    intervals: tuple[RawProbabilityIntervalV1, RawProbabilityIntervalV1]
    raw_log_id: str | None
    sample_count: int

    def __post_init__(self) -> None:
        if type(self.catalogue_row) is not StatisticalRowCatalogueV1:
            raise RawMultiContextInvariantViolation(
                "partial row rejects substituted catalogue entries"
            )
        _exact_tuple(
            self.intervals,
            RawProbabilityIntervalV1,
            "partial row intervals",
        )
        if (
            type(self.evidence) is not RowEvidence
            or tuple(item.destination_cell_id for item in self.intervals)
            != self.catalogue_row.destination_cell_ids
            or sum((item.lower for item in self.intervals), Fraction(0)) > 1
            or sum((item.upper for item in self.intervals), Fraction(0)) < 1
        ):
            raise RawMultiContextInvariantViolation(
                "partial row evidence or simplex changed"
            )
        if self.evidence is RowEvidence.MISSING:
            if (
                self.raw_log_id is not None
                or self.sample_count != 0
                or any(
                    item.lower != 0
                    or item.upper != 1
                    or item.empirical_probability is not None
                    for item in self.intervals
                )
            ):
                raise RawMultiContextInvariantViolation(
                    "missing rows must remain vacuous native zeros"
                )
        else:
            _cid(self.raw_log_id, "partial row raw log")
            if (
                self.sample_count != SAMPLE_COUNT_PER_ROW
                or any(item.empirical_probability is None for item in self.intervals)
            ):
                raise RawMultiContextInvariantViolation(
                    "statistical rows require the complete raw sample count"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_partial_statistical_row.v1",
            "schema_version": SCHEMA_VERSION,
            "catalogue_row": self.catalogue_row.to_document(),
            "evidence": self.evidence.value,
            "intervals": [item.to_document() for item in self.intervals],
            "raw_log_id": self.raw_log_id,
            "sample_count": self.sample_count,
            "joint_binary_simplex_enforced": True,
        }

    @property
    def partial_row_id(self) -> str:
        return _content_id("partial_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "partial_row_id": self.partial_row_id}


@dataclass(frozen=True, slots=True)
class RawPartialStatisticalModelV1:
    context: RawSafeChainStructuralContextV1
    catalogue_id: str
    lane: AcquisitionLane
    rows: tuple[RawPartialStatisticalRowV1, ...]
    source_log_id: str | None
    observed_row_count: int
    missing_row_count: int
    exact_sound_claimed: bool = False
    context_reuse_outside_identity_forbidden: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.context) is not RawSafeChainStructuralContextV1
            or type(self.lane) is not AcquisitionLane
        ):
            raise RawMultiContextInvariantViolation(
                "partial model rejects substituted context/lane"
            )
        _cid(self.catalogue_id, "partial model catalogue")
        _exact_tuple(
            self.rows,
            RawPartialStatisticalRowV1,
            "partial model rows",
        )
        evidence_counts = {
            evidence: sum(row.evidence is evidence for row in self.rows)
            for evidence in RowEvidence
        }
        if (
            self.catalogue_id != self.context.catalogue_id
            or len(self.rows) != DIRECT_ROWS_PER_CONTEXT
            or tuple(row.catalogue_row.key for row in self.rows) != ALL_ROW_KEYS
            or evidence_counts[RowEvidence.RAW_STATISTICAL]
            != self.observed_row_count
            or evidence_counts[RowEvidence.MISSING] != self.missing_row_count
            or self.observed_row_count + self.missing_row_count
            != DIRECT_ROWS_PER_CONTEXT
            or self.exact_sound_claimed is not False
            or self.context_reuse_outside_identity_forbidden is not True
        ):
            raise RawMultiContextInvariantViolation(
                "partial model row counts, ordering, or claims changed"
            )
        if self.source_log_id is None:
            if self.observed_row_count != 0 or self.missing_row_count != 6:
                raise RawMultiContextInvariantViolation(
                    "initial model must contain six missing rows"
                )
        else:
            _cid(self.source_log_id, "partial model source log")
            expected = (
                (3, 3)
                if self.lane is AcquisitionLane.ADAPTIVE
                else (6, 0)
            )
            if (self.observed_row_count, self.missing_row_count) != expected:
                raise RawMultiContextInvariantViolation(
                    "lane-specific partial-model coverage changed"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_partial_statistical_model.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context": self.context.to_document(),
            "catalogue_id": self.catalogue_id,
            "lane": self.lane.value,
            "rows": [item.to_document() for item in self.rows],
            "source_log_id": self.source_log_id,
            "observed_row_count": self.observed_row_count,
            "missing_row_count": self.missing_row_count,
            "exact_sound_claimed": self.exact_sound_claimed,
            "context_reuse_outside_identity_forbidden": (
                self.context_reuse_outside_identity_forbidden
            ),
        }

    @property
    def model_id(self) -> str:
        return _content_id("partial_model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}


def _missing_partial_model(
    catalogue: G2048StatisticalCatalogueV1,
    context: RawSafeChainStructuralContextV1,
) -> RawPartialStatisticalModelV1:
    rows = tuple(
        RawPartialStatisticalRowV1(
            row,
            RowEvidence.MISSING,
            tuple(
                RawProbabilityIntervalV1(destination, Fraction(0), Fraction(1), None)
                for destination in row.destination_cell_ids
            ),
            None,
            0,
        )
        for row in catalogue.rows
    )
    row_by_key = {row.catalogue_row.key: row for row in rows}
    return RawPartialStatisticalModelV1(
        context,
        catalogue.catalogue_id,
        AcquisitionLane.ADAPTIVE,
        tuple(row_by_key[key] for key in ALL_ROW_KEYS),
        None,
        0,
        6,
    )


def _binary_bounds(
    row: RawPartialStatisticalRowV1,
) -> tuple[Fraction, Fraction]:
    first, second = row.intervals
    lower = max(first.lower, 1 - second.upper)
    upper = min(first.upper, 1 - second.lower)
    if not 0 <= lower <= upper <= 1:
        raise RawMultiContextInvariantViolation(
            "partial row has an empty binary simplex"
        )
    return lower, upper


def _extreme(
    bounds: tuple[Fraction, Fraction],
    first_value: Fraction,
    second_value: Fraction,
    *,
    maximize: bool,
) -> Fraction:
    lower, upper = bounds
    values = (
        lower * first_value + (1 - lower) * second_value,
        upper * first_value + (1 - upper) * second_value,
    )
    return max(values) if maximize else min(values)


@dataclass(frozen=True, slots=True)
class RawPartialPolicyV1:
    model_id: str
    schedule: tuple[str, str, str]
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction
    missing_row_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.model_id, "partial policy model")
        labels = {
            G2048RelativeSurvivorLabel.AWAY.value,
            G2048RelativeSurvivorLabel.TOWARD.value,
        }
        if (
            type(self.schedule) is not tuple
            or len(self.schedule) != 3
            or any(label not in labels for label in self.schedule)
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
            or type(self.missing_row_keys) is not tuple
            or self.missing_row_keys != tuple(sorted(set(self.missing_row_keys)))
        ):
            raise RawMultiContextInvariantViolation(
                "partial policy schedule or bounds changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_partial_statistical_policy.v1",
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model_id,
            "schedule": list(self.schedule),
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
            "failure_lower": _fdoc(self.failure_lower),
            "failure_upper": _fdoc(self.failure_upper),
            "missing_row_keys": list(self.missing_row_keys),
        }

    @property
    def policy_id(self) -> str:
        return _content_id("policy", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "policy_id": self.policy_id}


def _policy_bounds(
    model: RawPartialStatisticalModelV1,
    schedule: tuple[str, str, str],
) -> RawPartialPolicyV1:
    rows = {row.catalogue_row.key: row for row in model.rows}
    away = G2048RelativeSurvivorLabel.AWAY.value
    root_action, chain_a_action, chain_b_action = schedule
    root_key = "ROOT_AWAY" if root_action == away else "ROOT_TOWARD"
    chain_a_key = "CHAIN_A_AWAY" if chain_a_action == away else "CHAIN_A_TOWARD"
    chain_b_key = "CHAIN_B_AWAY" if chain_b_action == away else "CHAIN_B_TOWARD"
    root_row = rows[root_key]
    chain_a = rows[chain_a_key]
    chain_b = rows[chain_b_key]

    def final_risk(row: RawPartialStatisticalRowV1, maximize: bool) -> Fraction:
        return _extreme(
            _binary_bounds(row),
            Fraction(1),
            Fraction(0),
            maximize=maximize,
        )

    a_lower = final_risk(chain_a, False)
    a_upper = final_risk(chain_a, True)
    b_lower = final_risk(chain_b, False)
    b_upper = final_risk(chain_b, True)
    root_bounds = _binary_bounds(root_row)
    if root_key == "ROOT_AWAY":
        failure_lower = _extreme(
            root_bounds, Fraction(1), b_lower, maximize=False
        )
        failure_upper = _extreme(
            root_bounds, Fraction(1), b_upper, maximize=True
        )
        reward_lower = Fraction(1, 64) + _extreme(
            root_bounds, Fraction(0), Fraction(1, 32), maximize=False
        )
        reward_upper = Fraction(1, 64) + _extreme(
            root_bounds, Fraction(0), Fraction(1, 32), maximize=True
        )
    else:
        failure_lower = min(
            (
                q * a + (1 - q) * b
                for q in root_bounds
                for a in (a_lower, a_upper)
                for b in (b_lower, b_upper)
            )
        )
        failure_upper = max(
            (
                q * a + (1 - q) * b
                for q in root_bounds
                for a in (a_lower, a_upper)
                for b in (b_lower, b_upper)
            )
        )
        reward_lower = reward_upper = Fraction(3, 64)
    missing = tuple(
        sorted(
            row.catalogue_row.key
            for row in (root_row, chain_a, chain_b)
            if row.evidence is RowEvidence.MISSING
        )
    )
    return RawPartialPolicyV1(
        model.model_id,
        schedule,
        reward_lower,
        reward_upper,
        failure_lower,
        failure_upper,
        missing,
    )


@dataclass(frozen=True, slots=True)
class RawPartialPlanProofV1:
    model_id: str
    candidate_policies: tuple[RawPartialPolicyV1, ...]
    selected_policy: RawPartialPolicyV1
    status: str
    delta: Fraction
    unrestricted_reward_upper: Fraction
    normalized_regret_upper: Fraction
    required_missing_row_keys: tuple[str, ...]
    confidence_lower: Fraction | None
    exact_sound_claimed: bool = False

    def __post_init__(self) -> None:
        _cid(self.model_id, "partial proof model")
        _exact_tuple(
            self.candidate_policies,
            RawPartialPolicyV1,
            "partial proof candidates",
        )
        if type(self.selected_policy) is not RawPartialPolicyV1:
            raise RawMultiContextInvariantViolation(
                "partial proof rejects substituted selected policies"
            )
        if (
            len(self.candidate_policies) != 8
            or tuple(item.policy_id for item in self.candidate_policies)
            != tuple(sorted(item.policy_id for item in self.candidate_policies))
            or self.selected_policy.policy_id
            not in {item.policy_id for item in self.candidate_policies}
            or self.selected_policy.schedule
            != (
                G2048RelativeSurvivorLabel.TOWARD.value,
                G2048RelativeSurvivorLabel.AWAY.value,
                G2048RelativeSurvivorLabel.AWAY.value,
            )
            or self.delta != Fraction(1, 20)
            or self.unrestricted_reward_upper != Fraction(3, 64)
            or self.normalized_regret_upper
            != self.unrestricted_reward_upper - self.selected_policy.reward_lower
            or self.normalized_regret_upper != 0
            or self.exact_sound_claimed is not False
        ):
            raise RawMultiContextInvariantViolation(
                "partial proof selection or bounds changed"
            )
        if self.status == FAILED_STATUS:
            if (
                self.selected_policy.failure_upper != 1
                or self.required_missing_row_keys != ADAPTIVE_ROW_KEYS
                or self.confidence_lower is not None
            ):
                raise RawMultiContextInvariantViolation(
                    "initial failed proof/frontier changed"
                )
        elif self.status == CERTIFIED_STATUS:
            if (
                self.selected_policy.failure_upper > self.delta
                or self.required_missing_row_keys
                or self.confidence_lower != GLOBAL_CONFIDENCE_LOWER
            ):
                raise RawMultiContextInvariantViolation(
                    "statistical certificate is not robust"
                )
        else:
            raise RawMultiContextInvariantViolation(
                "unregistered partial proof status"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_partial_statistical_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model_id,
            "candidate_policies": [
                item.to_document() for item in self.candidate_policies
            ],
            "selected_policy": self.selected_policy.to_document(),
            "status": self.status,
            "delta": _fdoc(self.delta),
            "unrestricted_reward_upper": _fdoc(
                self.unrestricted_reward_upper
            ),
            "normalized_regret_upper": _fdoc(self.normalized_regret_upper),
            "required_missing_row_keys": list(self.required_missing_row_keys),
            "confidence_lower": (
                None
                if self.confidence_lower is None
                else _fdoc(self.confidence_lower)
            ),
            "exact_sound_claimed": self.exact_sound_claimed,
        }

    @property
    def proof_id(self) -> str:
        return _content_id("proof", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


def solve_raw_partial_h2_v1(
    model: RawPartialStatisticalModelV1,
) -> RawPartialPlanProofV1:
    if type(model) is not RawPartialStatisticalModelV1:
        raise RawMultiContextInvariantViolation(
            "partial planner rejects substituted models"
        )
    labels = (
        G2048RelativeSurvivorLabel.AWAY.value,
        G2048RelativeSurvivorLabel.TOWARD.value,
    )
    candidates = tuple(
        sorted(
            (
                _policy_bounds(model, schedule)
                for schedule in product(labels, repeat=3)
            ),
            key=lambda item: item.policy_id,
        )
    )
    feasible = tuple(
        item for item in candidates if item.failure_upper <= Fraction(1, 20)
    )
    pool = feasible or candidates
    selected = min(
        pool,
        key=lambda item: (
            -item.reward_lower,
            item.failure_upper,
            item.schedule,
            item.policy_id,
        ),
    )
    if feasible:
        status = CERTIFIED_STATUS
        required = ()
        confidence: Fraction | None = GLOBAL_CONFIDENCE_LOWER
    else:
        status = FAILED_STATUS
        required = tuple(
            key for key in ADAPTIVE_ROW_KEYS if key in selected.missing_row_keys
        )
        confidence = None
    return RawPartialPlanProofV1(
        model.model_id,
        candidates,
        selected,
        status,
        Fraction(1, 20),
        Fraction(3, 64),
        Fraction(3, 64) - selected.reward_lower,
        required,
        confidence,
    )


@dataclass(frozen=True, slots=True)
class RawAdaptiveAuthorizationV1:
    preregistration_id: str
    context_id: str
    failed_proof_id: str
    authorized_row_keys: tuple[str, ...]
    authorization_reason: str = (
        "selected_plan_failed_risk_proof_missing_rows_only"
    )

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.preregistration_id, "authorization preregistration"),
            (self.context_id, "authorization context"),
            (self.failed_proof_id, "authorization failed proof"),
        ):
            _cid(value, field_name)
        if (
            self.authorized_row_keys != ADAPTIVE_ROW_KEYS
            or self.authorization_reason
            != "selected_plan_failed_risk_proof_missing_rows_only"
        ):
            raise RawMultiContextInvariantViolation(
                "adaptive authorization scope changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_adaptive_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "context_id": self.context_id,
            "failed_proof_id": self.failed_proof_id,
            "authorized_row_keys": list(self.authorized_row_keys),
            "authorization_reason": self.authorization_reason,
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "authorization_id": self.authorization_id}


@dataclass(frozen=True, slots=True)
class RawGroundOutcomeAtomV1:
    outcome_index: int
    next_board: tuple[int, ...]
    next_status: str
    normalized_reward: Fraction
    failure: bool
    terminal: bool
    destination_cell_id: str

    def __post_init__(self) -> None:
        _cid(self.destination_cell_id, "raw outcome destination")
        if (
            type(self.outcome_index) is not int
            or not 0 <= self.outcome_index < 16
            or type(self.next_board) is not tuple
            or len(self.next_board) != 4
            or any(type(rank) is not int for rank in self.next_board)
            or self.next_status not in (
                G2048Status.ACTIVE.value,
                G2048Status.FAILURE.value,
            )
            or type(self.normalized_reward) is not Fraction
            or self.normalized_reward not in (Fraction(1, 64), Fraction(1, 32))
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or (self.next_status == G2048Status.FAILURE.value) != self.failure
            or self.terminal != self.failure
        ):
            raise RawMultiContextInvariantViolation(
                "raw ground outcome atom changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_ground_outcome_atom.v1",
            "schema_version": SCHEMA_VERSION,
            "outcome_index": self.outcome_index,
            "next_board": list(self.next_board),
            "next_status": self.next_status,
            "normalized_reward": _fdoc(self.normalized_reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "destination_cell_id": self.destination_cell_id,
        }

    @property
    def atom_id(self) -> str:
        return _content_id("outcome_atom", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


@dataclass(frozen=True, slots=True)
class RawRowCodebookV1:
    context_id: str
    catalogue_row_id: str
    row_key: str
    representative_board: tuple[int, ...]
    ground_action: tuple[int, int, int]
    outcomes: tuple[RawGroundOutcomeAtomV1, ...]
    exact_probabilities_absent: bool = True

    def __post_init__(self) -> None:
        _cid(self.context_id, "codebook context")
        _cid(self.catalogue_row_id, "codebook catalogue row")
        _exact_tuple(self.outcomes, RawGroundOutcomeAtomV1, "codebook outcomes")
        if (
            self.row_key not in ALL_ROW_KEYS
            or type(self.representative_board) is not tuple
            or len(self.representative_board) != 4
            or type(self.ground_action) is not tuple
            or len(self.ground_action) != 3
            or any(type(cell) is not int for cell in self.ground_action)
            or len(self.outcomes) != 4
            or tuple(item.outcome_index for item in self.outcomes)
            != tuple(range(4))
            or self.exact_probabilities_absent is not True
        ):
            raise RawMultiContextInvariantViolation(
                "raw row codebook shape changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_row_codebook.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "catalogue_row_id": self.catalogue_row_id,
            "row_key": self.row_key,
            "representative_board": list(self.representative_board),
            "ground_action": list(self.ground_action),
            "outcomes": [item.to_document() for item in self.outcomes],
            "exact_probabilities_absent": self.exact_probabilities_absent,
        }

    @property
    def codebook_id(self) -> str:
        return _content_id("codebook", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "codebook_id": self.codebook_id}


@dataclass(frozen=True, slots=True)
class PackedRawDrawBlockV1:
    lane: AcquisitionLane
    context_id: str
    catalogue_row_id: str
    codebook_id: str
    seed: str
    block_index: int
    start_index: int
    draw_count: int
    outcome_nibbles_hex: str
    previous_block_id: str | None

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.context_id, "draw-block context"),
            (self.catalogue_row_id, "draw-block row"),
            (self.codebook_id, "draw-block codebook"),
        ):
            _cid(value, field_name)
        if self.previous_block_id is not None:
            _cid(self.previous_block_id, "draw-block predecessor")
        if (
            type(self.lane) is not AcquisitionLane
            or type(self.seed) is not str
            or not self.seed
            or type(self.block_index) is not int
            or not 0 <= self.block_index < BLOCKS_PER_ROW
            or self.start_index != self.block_index * DRAW_BLOCK_SIZE
            or self.draw_count != DRAW_BLOCK_SIZE
            or type(self.outcome_nibbles_hex) is not str
            or len(self.outcome_nibbles_hex) != self.draw_count
            or any(character not in "0123456789abcdef" for character in self.outcome_nibbles_hex)
            or (self.block_index == 0) != (self.previous_block_id is None)
        ):
            raise RawMultiContextInvariantViolation(
                "packed raw draw block or chain changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.packed_raw_draw_block.v1",
            "schema_version": SCHEMA_VERSION,
            "lane": self.lane.value,
            "context_id": self.context_id,
            "catalogue_row_id": self.catalogue_row_id,
            "codebook_id": self.codebook_id,
            "seed": self.seed,
            "block_index": self.block_index,
            "start_index": self.start_index,
            "draw_count": self.draw_count,
            "outcome_nibbles_hex": self.outcome_nibbles_hex,
            "previous_block_id": self.previous_block_id,
        }

    @property
    def block_id(self) -> str:
        return _content_id("draw_block", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "block_id": self.block_id}


@dataclass(frozen=True, slots=True)
class PackedRawContextLogV1:
    preregistration_id: str
    context_id: str
    lane: AcquisitionLane
    authorized_row_keys: tuple[str, ...]
    authorization_id: str | None
    codebooks: tuple[RawRowCodebookV1, ...]
    blocks: tuple[PackedRawDrawBlockV1, ...]
    sample_count_per_row: int
    total_draw_count: int
    individual_draw_trace_embedded: bool = True
    aggregate_only_input: bool = False
    exact_probabilities_embedded: bool = False

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "raw log preregistration")
        _cid(self.context_id, "raw log context")
        if self.authorization_id is not None:
            _cid(self.authorization_id, "raw log authorization")
        _exact_tuple(self.codebooks, RawRowCodebookV1, "raw log codebooks")
        _exact_tuple(self.blocks, PackedRawDrawBlockV1, "raw log blocks")
        expected_rows = (
            ADAPTIVE_ROW_KEYS
            if self.lane is AcquisitionLane.ADAPTIVE
            else ALL_ROW_KEYS
        )
        expected_seed = (
            RawAcquisitionProfileV1().adaptive_seed
            if self.lane is AcquisitionLane.ADAPTIVE
            else RawAcquisitionProfileV1().direct_seed
        )
        if (
            self.authorized_row_keys != expected_rows
            or tuple(item.row_key for item in self.codebooks) != expected_rows
            or any(item.context_id != self.context_id for item in self.codebooks)
            or len(self.blocks) != len(expected_rows) * BLOCKS_PER_ROW
            or self.sample_count_per_row != SAMPLE_COUNT_PER_ROW
            or self.total_draw_count
            != len(expected_rows) * SAMPLE_COUNT_PER_ROW
            or any(
                item.lane is not self.lane
                or item.context_id != self.context_id
                or item.seed != expected_seed
                for item in self.blocks
            )
            or self.individual_draw_trace_embedded is not True
            or self.aggregate_only_input is not False
            or self.exact_probabilities_embedded is not False
        ):
            raise RawMultiContextInvariantViolation(
                "raw context log coverage or claim changed"
            )
        if self.lane is AcquisitionLane.ADAPTIVE:
            if self.authorization_id is None:
                raise RawMultiContextInvariantViolation(
                    "adaptive raw log requires failed-proof authorization"
                )
        elif self.authorization_id is not None:
            raise RawMultiContextInvariantViolation(
                "direct-control log may not borrow adaptive authorization"
            )
        codebook_by_row = {
            item.catalogue_row_id: item for item in self.codebooks
        }
        blocks_by_row: dict[str, list[PackedRawDrawBlockV1]] = {}
        for block in self.blocks:
            blocks_by_row.setdefault(block.catalogue_row_id, []).append(block)
        if set(blocks_by_row) != set(codebook_by_row):
            raise RawMultiContextInvariantViolation(
                "raw log blocks do not cover codebooks exactly"
            )
        for row_id, row_blocks in blocks_by_row.items():
            ordered = sorted(row_blocks, key=lambda item: item.block_index)
            codebook = codebook_by_row[row_id]
            previous: str | None = None
            for index, block in enumerate(ordered):
                if (
                    block.block_index != index
                    or block.start_index != index * DRAW_BLOCK_SIZE
                    or block.codebook_id != codebook.codebook_id
                    or block.previous_block_id != previous
                    or any(
                        int(character, 16) >= len(codebook.outcomes)
                        for character in block.outcome_nibbles_hex
                    )
                ):
                    raise RawMultiContextInvariantViolation(
                        "raw log block sequence/codebook binding changed"
                    )
                previous = block.block_id
        expected_block_order = tuple(
            (codebook.catalogue_row_id, block_index)
            for codebook in self.codebooks
            for block_index in range(BLOCKS_PER_ROW)
        )
        if tuple(
            (block.catalogue_row_id, block.block_index)
            for block in self.blocks
        ) != expected_block_order:
            raise RawMultiContextInvariantViolation(
                "raw log block array is not in canonical row/block order"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.packed_raw_context_log.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "context_id": self.context_id,
            "lane": self.lane.value,
            "authorized_row_keys": list(self.authorized_row_keys),
            "authorization_id": self.authorization_id,
            "codebooks": [item.to_document() for item in self.codebooks],
            "blocks": [item.to_document() for item in self.blocks],
            "sample_count_per_row": self.sample_count_per_row,
            "total_draw_count": self.total_draw_count,
            "individual_draw_trace_embedded": (
                self.individual_draw_trace_embedded
            ),
            "aggregate_only_input": self.aggregate_only_input,
            "exact_probabilities_embedded": self.exact_probabilities_embedded,
        }

    @property
    def log_id(self) -> str:
        return _content_id("raw_log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "log_id": self.log_id}


def _row_source_state(row_key: str) -> G2048State:
    if row_key.startswith("ROOT_"):
        return G2048State((0, 1, 2, 1))
    if row_key.startswith("CHAIN_A_"):
        return G2048State((0, 1, 2, 2))
    if row_key.startswith("CHAIN_B_"):
        return G2048State((0, 2, 2, 2))
    raise RawMultiContextInvariantViolation(f"unknown raw row key: {row_key}")


def _row_action(
    kernel: RawSafeChainContextKernelV1,
    row_key: str,
) -> G2048Action:
    state = _row_source_state(row_key)
    target = (
        G2048RelativeSurvivorLabel.AWAY
        if row_key.endswith("_AWAY")
        else G2048RelativeSurvivorLabel.TOWARD
    )
    adapter = G2048RelativeSurvivorAdapter()
    actions = tuple(
        sorted(
            (
                action
                for action in kernel.actions(state)
                if adapter.label(kernel, state, action) is target
            ),
            key=lambda action: (action.first, action.second, action.survivor),
        )
    )
    if not actions:
        raise RawMultiContextInvariantViolation(
            f"no ground action realizes {row_key}"
        )
    return actions[0]


def _destination_cell_id(
    catalogue: G2048StatisticalCatalogueV1,
    row_key: str,
    outcome: Outcome[G2048State],
) -> str:
    row = next(item for item in catalogue.rows if item.key == row_key)
    cells = {item.cell_id: item for item in catalogue.cells}
    if outcome.failure:
        matches = tuple(
            destination
            for destination in row.destination_cell_ids
            if cells[destination].kind is StatisticalCellKind.FAILURE
        )
    else:
        canonical_board = min(
            state.board for state in orbit(outcome.next_state)
        )
        matches = tuple(
            destination
            for destination in row.destination_cell_ids
            if cells[destination].representative_board == canonical_board
        )
    if len(matches) != 1:
        raise RawMultiContextInvariantViolation(
            f"ground outcome does not map uniquely for {row_key}"
        )
    return matches[0]


def _normalized_reward(outcome: Outcome[G2048State]) -> Fraction:
    return dict(outcome.reward_features)["merge"] / 2


def _row_outcomes(
    catalogue: G2048StatisticalCatalogueV1,
    context: RawSafeChainStructuralContextV1,
    kernel: RawSafeChainContextKernelV1,
    row: StatisticalRowCatalogueV1,
) -> tuple[
    RawRowCodebookV1,
    tuple[tuple[Fraction, Outcome[G2048State]], ...],
]:
    state = _row_source_state(row.key)
    action = _row_action(kernel, row.key)
    outcomes = kernel.step(state, action)
    if len(outcomes) != 4:
        raise RawMultiContextInvariantViolation(
            "raw context kernel no longer emits four ground outcomes"
        )
    atoms = tuple(
        RawGroundOutcomeAtomV1(
            index,
            outcome.next_state.board,
            outcome.next_state.status.value,
            _normalized_reward(outcome),
            outcome.failure,
            outcome.terminal,
            _destination_cell_id(catalogue, row.key, outcome),
        )
        for index, outcome in enumerate(outcomes)
    )
    codebook = RawRowCodebookV1(
        context.context_id,
        row.row_id,
        row.key,
        state.board,
        (action.first, action.second, action.survivor),
        atoms,
    )
    return codebook, tuple((outcome.probability, outcome) for outcome in outcomes)


def _draw_uniform(
    seed: str,
    context_id: str,
    row_id: str,
    sample_index: int,
) -> Fraction:
    payload = {
        "schema": "acfqp.counter_based_uniform.v1",
        "seed": seed,
        "context_id": context_id,
        "catalogue_row_id": row_id,
        "sample_index": sample_index,
    }
    digest = hashlib.sha256(
        b"acfqp:counter-based-uniform:v1\x00"
        + canonical_json_bytes(payload)
    ).digest()
    return Fraction(int.from_bytes(digest, "big"), 1 << 256)


def _sample_outcome_index(
    probabilities: tuple[Fraction, ...],
    uniform: Fraction,
) -> int:
    cumulative = Fraction(0)
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if uniform < cumulative:
            return index
    if cumulative != 1:
        raise RawMultiContextInvariantViolation(
            "raw sampling probabilities do not sum to one"
        )
    return len(probabilities) - 1


def _acquire_context_log(
    catalogue: G2048StatisticalCatalogueV1,
    preregistration: RawMultiContextPreregistrationV1,
    context: RawSafeChainStructuralContextV1,
    kernel: RawSafeChainContextKernelV1,
    lane: AcquisitionLane,
    authorization: RawAdaptiveAuthorizationV1 | None,
) -> PackedRawContextLogV1:
    row_keys = (
        ADAPTIVE_ROW_KEYS if lane is AcquisitionLane.ADAPTIVE else ALL_ROW_KEYS
    )
    seed = (
        preregistration.acquisition_profile.adaptive_seed
        if lane is AcquisitionLane.ADAPTIVE
        else preregistration.acquisition_profile.direct_seed
    )
    row_by_key = {row.key: row for row in catalogue.rows}
    codebooks: list[RawRowCodebookV1] = []
    blocks: list[PackedRawDrawBlockV1] = []
    for row_key in row_keys:
        row = row_by_key[row_key]
        codebook, weighted_outcomes = _row_outcomes(
            catalogue, context, kernel, row
        )
        probabilities = tuple(item[0] for item in weighted_outcomes)
        codebooks.append(codebook)
        previous: str | None = None
        for block_index in range(BLOCKS_PER_ROW):
            start = block_index * DRAW_BLOCK_SIZE
            draws = "".join(
                format(
                    _sample_outcome_index(
                        probabilities,
                        _draw_uniform(
                            seed,
                            context.context_id,
                            row.row_id,
                            sample_index,
                        ),
                    ),
                    "x",
                )
                for sample_index in range(start, start + DRAW_BLOCK_SIZE)
            )
            block = PackedRawDrawBlockV1(
                lane,
                context.context_id,
                row.row_id,
                codebook.codebook_id,
                seed,
                block_index,
                start,
                DRAW_BLOCK_SIZE,
                draws,
                previous,
            )
            blocks.append(block)
            previous = block.block_id
    return PackedRawContextLogV1(
        preregistration.preregistration_id,
        context.context_id,
        lane,
        row_keys,
        None if authorization is None else authorization.authorization_id,
        tuple(codebooks),
        tuple(blocks),
        SAMPLE_COUNT_PER_ROW,
        len(row_keys) * SAMPLE_COUNT_PER_ROW,
    )


def _validate_codebook_without_kernel(
    catalogue: G2048StatisticalCatalogueV1,
    context: RawSafeChainStructuralContextV1,
    codebook: RawRowCodebookV1,
) -> None:
    row_by_id = {row.row_id: row for row in catalogue.rows}
    cells = {item.cell_id: item for item in catalogue.cells}
    row = row_by_id.get(codebook.catalogue_row_id)
    expected_actions = {
        "ROOT_AWAY": (1, 3, 1),
        "ROOT_TOWARD": (1, 3, 3),
        "CHAIN_A_AWAY": (2, 3, 2),
        "CHAIN_A_TOWARD": (2, 3, 3),
        "CHAIN_B_AWAY": (1, 3, 1),
        "CHAIN_B_TOWARD": (1, 3, 3),
    }
    if (
        row is None
        or row.key != codebook.row_key
        or codebook.context_id != context.context_id
        or codebook.representative_board != _row_source_state(row.key).board
        or codebook.ground_action != expected_actions[row.key]
        or any(
            atom.normalized_reward != row.normalized_reward
            or atom.destination_cell_id not in row.destination_cell_ids
            or atom.failure
            != (
                cells[atom.destination_cell_id].kind
                is StatisticalCellKind.FAILURE
            )
            for atom in codebook.outcomes
        )
        or {
            atom.destination_cell_id for atom in codebook.outcomes
        }
        != set(row.destination_cell_ids)
    ):
        raise RawMultiContextInvariantViolation(
            "raw codebook contradicts the probability-free structural catalogue"
        )


def build_raw_partial_statistical_model_v1(
    catalogue: G2048StatisticalCatalogueV1,
    context: RawSafeChainStructuralContextV1,
    raw_log: PackedRawContextLogV1,
) -> RawPartialStatisticalModelV1:
    """Decode every packed observation and build an honest partial model."""

    if (
        type(catalogue) is not G2048StatisticalCatalogueV1
        or type(context) is not RawSafeChainStructuralContextV1
        or type(raw_log) is not PackedRawContextLogV1
    ):
        raise RawMultiContextInvariantViolation(
            "raw model builder rejects substituted inputs"
        )
    if (
        catalogue.catalogue_id != context.catalogue_id
        or raw_log.context_id != context.context_id
    ):
        raise RawMultiContextInvariantViolation(
            "raw model builder rejects out-of-context evidence"
        )
    codebook_by_row = {
        item.catalogue_row_id: item for item in raw_log.codebooks
    }
    blocks_by_row: dict[str, list[PackedRawDrawBlockV1]] = {}
    for block in raw_log.blocks:
        blocks_by_row.setdefault(block.catalogue_row_id, []).append(block)
    catalogue_by_key = {row.key: row for row in catalogue.rows}
    observed_keys = set(raw_log.authorized_row_keys)
    result_rows: list[RawPartialStatisticalRowV1] = []
    for row_key in ALL_ROW_KEYS:
        row = catalogue_by_key[row_key]
        if row_key not in observed_keys:
            result_rows.append(
                RawPartialStatisticalRowV1(
                    row,
                    RowEvidence.MISSING,
                    tuple(
                        RawProbabilityIntervalV1(
                            destination,
                            Fraction(0),
                            Fraction(1),
                            None,
                        )
                        for destination in row.destination_cell_ids
                    ),
                    None,
                    0,
                )
            )
            continue
        codebook = codebook_by_row.get(row.row_id)
        if codebook is None:
            raise RawMultiContextInvariantViolation(
                "raw log omitted an observed-row codebook"
            )
        _validate_codebook_without_kernel(catalogue, context, codebook)
        counts = {destination: 0 for destination in row.destination_cell_ids}
        draw_count = 0
        for block in sorted(
            blocks_by_row[row.row_id],
            key=lambda item: item.block_index,
        ):
            for character in block.outcome_nibbles_hex:
                atom = codebook.outcomes[int(character, 16)]
                counts[atom.destination_cell_id] += 1
                draw_count += 1
        if draw_count != SAMPLE_COUNT_PER_ROW:
            raise RawMultiContextInvariantViolation(
                "decoded raw row has the wrong draw count"
            )
        intervals = tuple(
            RawProbabilityIntervalV1(
                destination,
                max(
                    Fraction(0),
                    Fraction(counts[destination], draw_count)
                    - HOEFFDING_RADIUS,
                ),
                min(
                    Fraction(1),
                    Fraction(counts[destination], draw_count)
                    + HOEFFDING_RADIUS,
                ),
                Fraction(counts[destination], draw_count),
            )
            for destination in row.destination_cell_ids
        )
        result_rows.append(
            RawPartialStatisticalRowV1(
                row,
                RowEvidence.RAW_STATISTICAL,
                intervals,
                raw_log.log_id,
                draw_count,
            )
        )
    return RawPartialStatisticalModelV1(
        context,
        catalogue.catalogue_id,
        raw_log.lane,
        tuple(result_rows),
        raw_log.log_id,
        len(observed_keys),
        DIRECT_ROWS_PER_CONTEXT - len(observed_keys),
    )


@dataclass(frozen=True, slots=True)
class RawContextEvidenceV1:
    context: RawSafeChainStructuralContextV1
    initial_model: RawPartialStatisticalModelV1
    failed_proof: RawPartialPlanProofV1
    authorization: RawAdaptiveAuthorizationV1
    adaptive_log: PackedRawContextLogV1
    direct_log: PackedRawContextLogV1

    def __post_init__(self) -> None:
        if (
            type(self.context) is not RawSafeChainStructuralContextV1
            or type(self.initial_model) is not RawPartialStatisticalModelV1
            or type(self.failed_proof) is not RawPartialPlanProofV1
            or type(self.authorization) is not RawAdaptiveAuthorizationV1
            or type(self.adaptive_log) is not PackedRawContextLogV1
            or type(self.direct_log) is not PackedRawContextLogV1
        ):
            raise RawMultiContextInvariantViolation(
                "raw context evidence rejects substituted artifacts"
            )
        if (
            self.initial_model.context.context_id != self.context.context_id
            or self.initial_model.source_log_id is not None
            or self.failed_proof.model_id != self.initial_model.model_id
            or self.failed_proof.status != FAILED_STATUS
            or self.authorization.context_id != self.context.context_id
            or self.authorization.failed_proof_id != self.failed_proof.proof_id
            or self.authorization.preregistration_id
            != self.adaptive_log.preregistration_id
            or self.adaptive_log.preregistration_id
            != self.direct_log.preregistration_id
            or self.adaptive_log.context_id != self.context.context_id
            or self.adaptive_log.authorization_id
            != self.authorization.authorization_id
            or self.direct_log.context_id != self.context.context_id
            or self.direct_log.authorization_id is not None
        ):
            raise RawMultiContextInvariantViolation(
                "raw evidence chronology or identity chain changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_context_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "context": self.context.to_document(),
            "initial_model": self.initial_model.to_document(),
            "failed_proof": self.failed_proof.to_document(),
            "authorization": self.authorization.to_document(),
            "adaptive_log": self.adaptive_log.to_document(),
            "direct_log": self.direct_log.to_document(),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class RawMultiContextEvidenceBundleV1:
    preregistration_id: str
    contexts: tuple[RawContextEvidenceV1, ...]
    adaptive_total_draws: int = ADAPTIVE_TOTAL_DRAWS
    direct_total_draws: int = DIRECT_TOTAL_DRAWS
    exact_probabilities_exported_to_builder: bool = False

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "evidence-bundle preregistration")
        _exact_tuple(
            self.contexts,
            RawContextEvidenceV1,
            "evidence-bundle contexts",
        )
        if (
            len(self.contexts) != CONTEXT_COUNT
            or len({item.context.context_id for item in self.contexts})
            != CONTEXT_COUNT
            or any(
                item.authorization.preregistration_id
                != self.preregistration_id
                or item.adaptive_log.preregistration_id
                != self.preregistration_id
                or item.direct_log.preregistration_id
                != self.preregistration_id
                for item in self.contexts
            )
            or self.adaptive_total_draws != ADAPTIVE_TOTAL_DRAWS
            or self.direct_total_draws != DIRECT_TOTAL_DRAWS
            or self.exact_probabilities_exported_to_builder is not False
        ):
            raise RawMultiContextInvariantViolation(
                "raw evidence-bundle work or claim changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_multicontext_evidence_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "contexts": [item.to_document() for item in self.contexts],
            "adaptive_total_draws": self.adaptive_total_draws,
            "direct_total_draws": self.direct_total_draws,
            "exact_probabilities_exported_to_builder": (
                self.exact_probabilities_exported_to_builder
            ),
        }

    @property
    def bundle_id(self) -> str:
        return _content_id("evidence_bundle", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bundle_id": self.bundle_id}


def _validate_context_kernel(
    context: RawSafeChainStructuralContextV1,
    kernel: RawSafeChainContextKernelV1,
) -> None:
    if (
        type(kernel) is not RawSafeChainContextKernelV1
        or kernel.size != context.board_size
        or kernel.context_key != context.context_key
        or kernel.rank_one_probability != context.rank_one_probability
        or kernel.rank_cap != context.rank_cap
    ):
        raise RawMultiContextInvariantViolation(
            "unregistered or out-of-support structural context"
        )


def acquire_raw_multicontext_evidence_v1(
    catalogue: G2048StatisticalCatalogueV1,
    preregistration: RawMultiContextPreregistrationV1,
    kernels: tuple[RawSafeChainContextKernelV1, ...],
) -> RawMultiContextEvidenceBundleV1:
    """Run the scoped stochastic acquisition authority after preregistration."""

    if (
        type(catalogue) is not G2048StatisticalCatalogueV1
        or type(preregistration) is not RawMultiContextPreregistrationV1
    ):
        raise RawMultiContextInvariantViolation(
            "raw acquisition rejects substituted inputs"
        )
    _exact_tuple(kernels, RawSafeChainContextKernelV1, "acquisition kernels")
    expected_preregistration = preregister_raw_multicontext_campaign_v1(catalogue)
    _runtime_shape(
        preregistration,
        expected_preregistration,
        "raw preregistration",
    )
    if preregistration.to_document() != expected_preregistration.to_document():
        raise RawMultiContextInvariantViolation(
            "raw preregistration reconstruction mismatch"
        )
    if len(kernels) != CONTEXT_COUNT:
        raise RawMultiContextInvariantViolation(
            "raw acquisition requires exactly three context kernels"
        )
    evidence_rows: list[RawContextEvidenceV1] = []
    for context, kernel in zip(preregistration.contexts, kernels):
        _validate_context_kernel(context, kernel)
        initial_model = _missing_partial_model(catalogue, context)
        failed_proof = solve_raw_partial_h2_v1(initial_model)
        if (
            failed_proof.status != FAILED_STATUS
            or failed_proof.required_missing_row_keys != ADAPTIVE_ROW_KEYS
        ):
            raise RawMultiContextInvariantViolation(
                "model-only failed proof did not identify the registered rows"
            )
        authorization = RawAdaptiveAuthorizationV1(
            preregistration.preregistration_id,
            context.context_id,
            failed_proof.proof_id,
            failed_proof.required_missing_row_keys,
        )
        adaptive_log = _acquire_context_log(
            catalogue,
            preregistration,
            context,
            kernel,
            AcquisitionLane.ADAPTIVE,
            authorization,
        )
        direct_log = _acquire_context_log(
            catalogue,
            preregistration,
            context,
            kernel,
            AcquisitionLane.DIRECT,
            None,
        )
        evidence_rows.append(
            RawContextEvidenceV1(
                context,
                initial_model,
                failed_proof,
                authorization,
                adaptive_log,
                direct_log,
            )
        )
    return RawMultiContextEvidenceBundleV1(
        preregistration.preregistration_id,
        tuple(evidence_rows),
    )


@dataclass(frozen=True, slots=True)
class RawContextPlanningResultV1:
    context: RawSafeChainStructuralContextV1
    evidence_id: str
    initial_failed_proof_id: str
    adaptive_model: RawPartialStatisticalModelV1
    adaptive_proof: RawPartialPlanProofV1
    direct_model: RawPartialStatisticalModelV1
    direct_proof: RawPartialPlanProofV1

    def __post_init__(self) -> None:
        if (
            type(self.context) is not RawSafeChainStructuralContextV1
            or type(self.adaptive_model) is not RawPartialStatisticalModelV1
            or type(self.adaptive_proof) is not RawPartialPlanProofV1
            or type(self.direct_model) is not RawPartialStatisticalModelV1
            or type(self.direct_proof) is not RawPartialPlanProofV1
        ):
            raise RawMultiContextInvariantViolation(
                "context planning result rejects substituted artifacts"
            )
        _cid(self.evidence_id, "context planning evidence")
        _cid(self.initial_failed_proof_id, "context initial failed proof")
        if (
            self.adaptive_model.context.context_id != self.context.context_id
            or self.direct_model.context.context_id != self.context.context_id
            or self.adaptive_model.lane is not AcquisitionLane.ADAPTIVE
            or self.direct_model.lane is not AcquisitionLane.DIRECT
            or (
                self.adaptive_model.observed_row_count,
                self.adaptive_model.missing_row_count,
            )
            != (3, 3)
            or (
                self.direct_model.observed_row_count,
                self.direct_model.missing_row_count,
            )
            != (6, 0)
            or self.adaptive_proof.model_id != self.adaptive_model.model_id
            or self.direct_proof.model_id != self.direct_model.model_id
            or self.adaptive_proof.status != CERTIFIED_STATUS
            or self.direct_proof.status != CERTIFIED_STATUS
            or self.adaptive_proof.selected_policy.schedule
            != self.direct_proof.selected_policy.schedule
            or self.adaptive_proof.selected_policy.schedule
            != (
                G2048RelativeSurvivorLabel.TOWARD.value,
                G2048RelativeSurvivorLabel.AWAY.value,
                G2048RelativeSurvivorLabel.AWAY.value,
            )
        ):
            raise RawMultiContextInvariantViolation(
                "context planning coverage, proof, or policy changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_context_planning_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context": self.context.to_document(),
            "evidence_id": self.evidence_id,
            "initial_failed_proof_id": self.initial_failed_proof_id,
            "adaptive_model": self.adaptive_model.to_document(),
            "adaptive_proof": self.adaptive_proof.to_document(),
            "direct_model": self.direct_model.to_document(),
            "direct_proof": self.direct_proof.to_document(),
        }

    @property
    def result_id(self) -> str:
        return _content_id("context_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class RawOccurrenceResultV1:
    preregistration_id: str
    occurrence: RawContextOccurrenceV1
    context_result_id: str
    adaptive_model_id: str
    adaptive_proof_id: str
    direct_model_id: str
    direct_proof_id: str
    adaptive_failure_lower: Fraction
    adaptive_failure_upper: Fraction
    direct_failure_lower: Fraction
    direct_failure_upper: Fraction
    adaptive_new_draws: int
    direct_new_draws: int
    reused_frozen_models: bool
    adaptive_status: str = CERTIFIED_STATUS
    direct_status: str = CERTIFIED_STATUS

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.preregistration_id, "occurrence-result preregistration"),
            (self.context_result_id, "occurrence-result context result"),
            (self.adaptive_model_id, "occurrence-result adaptive model"),
            (self.adaptive_proof_id, "occurrence-result adaptive proof"),
            (self.direct_model_id, "occurrence-result direct model"),
            (self.direct_proof_id, "occurrence-result direct proof"),
        ):
            _cid(value, field_name)
        if type(self.occurrence) is not RawContextOccurrenceV1:
            raise RawMultiContextInvariantViolation(
                "occurrence result rejects substituted occurrences"
            )
        if any(
            type(value) is not Fraction
            for value in (
                self.adaptive_failure_lower,
                self.adaptive_failure_upper,
                self.direct_failure_lower,
                self.direct_failure_upper,
            )
        ) or not (
            0
            <= self.adaptive_failure_lower
            <= self.adaptive_failure_upper
            <= self.occurrence.delta
            and 0
            <= self.direct_failure_lower
            <= self.direct_failure_upper
            <= self.occurrence.delta
        ):
            raise RawMultiContextInvariantViolation(
                "occurrence statistical risk bounds changed"
            )
        first_context_pass = self.occurrence.ordinal < CONTEXT_COUNT
        expected_draws = (
            (
                ADAPTIVE_ROWS_PER_CONTEXT * SAMPLE_COUNT_PER_ROW,
                DIRECT_ROWS_PER_CONTEXT * SAMPLE_COUNT_PER_ROW,
                False,
            )
            if first_context_pass
            else (0, 0, True)
        )
        if (
            (
                self.adaptive_new_draws,
                self.direct_new_draws,
                self.reused_frozen_models,
            )
            != expected_draws
            or self.adaptive_status != CERTIFIED_STATUS
            or self.direct_status != CERTIFIED_STATUS
        ):
            raise RawMultiContextInvariantViolation(
                "occurrence acquisition, reuse, or status changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_multicontext_occurrence_result.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "occurrence": self.occurrence.to_document(),
            "context_result_id": self.context_result_id,
            "adaptive_model_id": self.adaptive_model_id,
            "adaptive_proof_id": self.adaptive_proof_id,
            "direct_model_id": self.direct_model_id,
            "direct_proof_id": self.direct_proof_id,
            "adaptive_failure_lower": _fdoc(self.adaptive_failure_lower),
            "adaptive_failure_upper": _fdoc(self.adaptive_failure_upper),
            "direct_failure_lower": _fdoc(self.direct_failure_lower),
            "direct_failure_upper": _fdoc(self.direct_failure_upper),
            "adaptive_new_draws": self.adaptive_new_draws,
            "direct_new_draws": self.direct_new_draws,
            "reused_frozen_models": self.reused_frozen_models,
            "adaptive_status": self.adaptive_status,
            "direct_status": self.direct_status,
            "occurrence_bound_certificate": True,
        }

    @property
    def result_id(self) -> str:
        return _content_id("occurrence_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class RawMultiContextWorkV1:
    structural_contexts: int
    logical_occurrences: int
    adaptive_observed_rows: int
    adaptive_explicit_missing_rows: int
    direct_observed_rows: int
    adaptive_individual_draws: int
    direct_individual_draws: int
    acquisition_kernel_row_enumerations: int
    model_only_failed_proofs: int
    adaptive_policy_candidates: int
    direct_policy_candidates: int
    within_context_model_reuses: int
    cross_context_model_reuses: int
    adaptive_statistical_certificates: int
    direct_statistical_certificates: int
    adaptive_draw_reduction_against_control: int
    matched_direct_ground_planning_claimed: bool = False
    sample_efficiency_claimed: bool = False
    sample_tax_operator_claimed: bool = False
    official_scalar_cost: None = None
    official_n_break_even: None = None

    def __post_init__(self) -> None:
        expected = (
            3,
            6,
            9,
            9,
            18,
            ADAPTIVE_TOTAL_DRAWS,
            DIRECT_TOTAL_DRAWS,
            27,
            3,
            48,
            48,
            3,
            0,
            6,
            6,
            DIRECT_TOTAL_DRAWS - ADAPTIVE_TOTAL_DRAWS,
            False,
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
            raise RawMultiContextInvariantViolation(
                "raw multi-context work or locked economics changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_multicontext_work.v1",
            "schema_version": SCHEMA_VERSION,
            **{
                field.name: object.__getattribute__(self, field.name)
                for field in fields(type(self))
            },
            "direct_control_semantics": (
                "independent_uniform_all_six_row_statistical_control"
            ),
            "adaptive_draw_reduction_is_not_efficiency_claim": True,
        }

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class RawMultiContextCampaignResultV1:
    preregistration: RawMultiContextPreregistrationV1
    evidence_bundle_id: str
    context_results: tuple[RawContextPlanningResultV1, ...]
    occurrences: tuple[RawOccurrenceResultV1, ...]
    work: RawMultiContextWorkV1
    status: str = SUCCESS_STATUS
    raw_individual_trace_replayable: bool = True
    partial_missing_rows_explicit: bool = True
    known_d4_prior_used: bool = True
    automatic_coordinate_discovery_claimed: bool = False
    statistical_exact_sound_claimed: bool = False
    broad_structural_generalization_claimed: bool = False
    sample_efficiency_claimed: bool = False
    official_execution_allowed: bool = False
    workload_economics_gate_run: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.preregistration) is not RawMultiContextPreregistrationV1
            or type(self.work) is not RawMultiContextWorkV1
        ):
            raise RawMultiContextInvariantViolation(
                "raw campaign rejects substituted authorities"
            )
        _cid(self.evidence_bundle_id, "raw campaign evidence bundle")
        _exact_tuple(
            self.context_results,
            RawContextPlanningResultV1,
            "raw campaign context results",
        )
        _exact_tuple(
            self.occurrences,
            RawOccurrenceResultV1,
            "raw campaign occurrence results",
        )
        context_ids = tuple(
            item.context.context_id for item in self.context_results
        )
        preregistration_id = self.preregistration.preregistration_id
        result_by_context = {
            item.context.context_id: item for item in self.context_results
        }
        if (
            context_ids
            != tuple(item.context_id for item in self.preregistration.contexts)
            or len(self.occurrences) != OCCURRENCE_COUNT
            or tuple(item.occurrence.occurrence_id for item in self.occurrences)
            != tuple(
                item.occurrence_id for item in self.preregistration.occurrences
            )
            or any(
                item.preregistration_id != preregistration_id
                or item.context_result_id
                != result_by_context[item.occurrence.context_id].result_id
                or item.adaptive_model_id
                != result_by_context[
                    item.occurrence.context_id
                ].adaptive_model.model_id
                or item.direct_model_id
                != result_by_context[
                    item.occurrence.context_id
                ].direct_model.model_id
                or item.adaptive_proof_id
                != result_by_context[
                    item.occurrence.context_id
                ].adaptive_proof.proof_id
                or item.direct_proof_id
                != result_by_context[
                    item.occurrence.context_id
                ].direct_proof.proof_id
                for item in self.occurrences
            )
            or self.status != SUCCESS_STATUS
            or self.raw_individual_trace_replayable is not True
            or self.partial_missing_rows_explicit is not True
            or self.known_d4_prior_used is not True
            or self.automatic_coordinate_discovery_claimed is not False
            or self.statistical_exact_sound_claimed is not False
            or self.broad_structural_generalization_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.official_execution_allowed is not False
            or self.workload_economics_gate_run is not False
        ):
            raise RawMultiContextInvariantViolation(
                "raw campaign identity chain or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_multicontext_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration": self.preregistration.to_document(),
            "evidence_bundle_id": self.evidence_bundle_id,
            "context_results": [
                item.to_document() for item in self.context_results
            ],
            "occurrences": [item.to_document() for item in self.occurrences],
            "work": self.work.to_document(),
            "status": self.status,
            "raw_individual_trace_replayable": (
                self.raw_individual_trace_replayable
            ),
            "partial_missing_rows_explicit": (
                self.partial_missing_rows_explicit
            ),
            "known_d4_prior_used": self.known_d4_prior_used,
            "automatic_coordinate_discovery_claimed": (
                self.automatic_coordinate_discovery_claimed
            ),
            "statistical_exact_sound_claimed": (
                self.statistical_exact_sound_claimed
            ),
            "broad_structural_generalization_claimed": (
                self.broad_structural_generalization_claimed
            ),
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
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


def _build_context_planning_result_v1(
    catalogue: G2048StatisticalCatalogueV1,
    evidence: RawContextEvidenceV1,
) -> RawContextPlanningResultV1:
    adaptive_model = build_raw_partial_statistical_model_v1(
        catalogue, evidence.context, evidence.adaptive_log
    )
    direct_model = build_raw_partial_statistical_model_v1(
        catalogue, evidence.context, evidence.direct_log
    )
    adaptive_proof = solve_raw_partial_h2_v1(adaptive_model)
    direct_proof = solve_raw_partial_h2_v1(direct_model)
    return RawContextPlanningResultV1(
        evidence.context,
        evidence.evidence_id,
        evidence.failed_proof.proof_id,
        adaptive_model,
        adaptive_proof,
        direct_model,
        direct_proof,
    )


def _build_occurrence_result_v1(
    preregistration: RawMultiContextPreregistrationV1,
    occurrence: RawContextOccurrenceV1,
    context_result: RawContextPlanningResultV1,
) -> RawOccurrenceResultV1:
    adaptive = context_result.adaptive_proof.selected_policy
    direct = context_result.direct_proof.selected_policy
    first_context_pass = occurrence.ordinal < CONTEXT_COUNT
    return RawOccurrenceResultV1(
        preregistration.preregistration_id,
        occurrence,
        context_result.result_id,
        context_result.adaptive_model.model_id,
        context_result.adaptive_proof.proof_id,
        context_result.direct_model.model_id,
        context_result.direct_proof.proof_id,
        adaptive.failure_lower,
        adaptive.failure_upper,
        direct.failure_lower,
        direct.failure_upper,
        (
            ADAPTIVE_ROWS_PER_CONTEXT * SAMPLE_COUNT_PER_ROW
            if first_context_pass
            else 0
        ),
        (
            DIRECT_ROWS_PER_CONTEXT * SAMPLE_COUNT_PER_ROW
            if first_context_pass
            else 0
        ),
        not first_context_pass,
    )


def _implementation_functions() -> tuple[Any, ...]:
    return (
        RawSafeChainStructuralContextV1,
        RawAcquisitionProfileV1,
        RawMultiContextPreregistrationV1,
        RawPartialStatisticalRowV1,
        RawPartialStatisticalModelV1,
        RawPartialPlanProofV1,
        PackedRawDrawBlockV1,
        PackedRawContextLogV1,
        RawContextEvidenceV1,
        RawMultiContextEvidenceBundleV1,
        RawContextPlanningResultV1,
        RawOccurrenceResultV1,
        RawMultiContextWorkV1,
        RawMultiContextCampaignResultV1,
        RawExactGroundComparatorV1,
        RawMultiContextVerificationV1,
        registered_raw_structural_contexts_v1,
        preregister_raw_multicontext_campaign_v1,
        _policy_bounds,
        solve_raw_partial_h2_v1,
        _destination_cell_id,
        _row_outcomes,
        _draw_uniform,
        _sample_outcome_index,
        _acquire_context_log,
        acquire_raw_multicontext_evidence_v1,
        _validate_codebook_without_kernel,
        build_raw_partial_statistical_model_v1,
        _build_context_planning_result_v1,
        _build_occurrence_result_v1,
        run_raw_multicontext_campaign_v1,
        _query_for_occurrence_v1,
        _solve_exact_ground_comparator_v1,
        _independently_replay_raw_log_v1,
        verify_raw_multicontext_campaign_v1,
    )


def _observed_implementation_sha256() -> str:
    source = "\n\n".join(
        inspect.getsource(item) for item in _implementation_functions()
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _validate_implementation_authority() -> None:
    if _observed_implementation_sha256() != IMPLEMENTATION_SHA256:
        raise RawMultiContextInvariantViolation(
            "V0-060 implementation differs from its frozen authority"
        )


def run_raw_multicontext_campaign_v1(
    catalogue: G2048StatisticalCatalogueV1,
    preregistration: RawMultiContextPreregistrationV1,
    evidence_bundle: RawMultiContextEvidenceBundleV1,
) -> RawMultiContextCampaignResultV1:
    """Build and plan solely from frozen structural metadata and raw logs."""

    if (
        type(catalogue) is not G2048StatisticalCatalogueV1
        or type(preregistration) is not RawMultiContextPreregistrationV1
        or type(evidence_bundle) is not RawMultiContextEvidenceBundleV1
    ):
        raise RawMultiContextInvariantViolation(
            "raw campaign runner rejects substituted inputs"
        )
    _validate_implementation_authority()
    expected_preregistration = preregister_raw_multicontext_campaign_v1(
        catalogue
    )
    _runtime_shape(
        preregistration,
        expected_preregistration,
        "raw campaign preregistration",
    )
    if preregistration.to_document() != expected_preregistration.to_document():
        raise RawMultiContextInvariantViolation(
            "raw campaign preregistration reconstruction mismatch"
        )
    if (
        evidence_bundle.preregistration_id
        != preregistration.preregistration_id
        or tuple(
            item.context.context_id for item in evidence_bundle.contexts
        )
        != tuple(item.context_id for item in preregistration.contexts)
    ):
        raise RawMultiContextInvariantViolation(
            "raw campaign evidence is stale or out of context"
        )
    context_results = tuple(
        _build_context_planning_result_v1(catalogue, item)
        for item in evidence_bundle.contexts
    )
    result_by_context = {
        item.context.context_id: item for item in context_results
    }
    occurrences = tuple(
        _build_occurrence_result_v1(
            preregistration,
            occurrence,
            result_by_context[occurrence.context_id],
        )
        for occurrence in preregistration.occurrences
    )
    work = RawMultiContextWorkV1(
        3,
        6,
        9,
        9,
        18,
        ADAPTIVE_TOTAL_DRAWS,
        DIRECT_TOTAL_DRAWS,
        27,
        3,
        48,
        48,
        3,
        0,
        6,
        6,
        DIRECT_TOTAL_DRAWS - ADAPTIVE_TOTAL_DRAWS,
    )
    return RawMultiContextCampaignResultV1(
        preregistration,
        evidence_bundle.bundle_id,
        context_results,
        occurrences,
        work,
    )


def _query_for_occurrence_v1(
    occurrence: RawContextOccurrenceV1,
) -> QuerySpec[G2048State]:
    mass = Fraction(1, len(occurrence.initial_boards))
    return QuerySpec(
        initial_distribution=tuple(
            (mass, G2048State(board))
            for board in occurrence.initial_boards
        ),
        horizon=occurrence.horizon,
        reward_weights=(("merge", Fraction(1)),),
        goal="default",
        delta=occurrence.delta,
        normalizer=Fraction(2),
        normalizer_proof_id=(
            "g2048.canonical.merge_le_1_per_step.total_le_h.v1"
        ),
    )


@dataclass(frozen=True, slots=True)
class RawExactGroundComparatorV1:
    context_id: str
    query_occurrence_id: str
    selected_reward: Fraction
    selected_failure: Fraction
    composed_candidate_count: int
    verification_lane: str = "standalone_evaluation"

    def __post_init__(self) -> None:
        _cid(self.context_id, "exact comparator context")
        _cid(self.query_occurrence_id, "exact comparator occurrence")
        if (
            type(self.selected_reward) is not Fraction
            or type(self.selected_failure) is not Fraction
            or self.selected_reward != Fraction(3, 64)
            or not 0 <= self.selected_failure < Fraction(1, 20)
            or self.composed_candidate_count != 5_440
            or self.verification_lane != "standalone_evaluation"
        ):
            raise RawMultiContextInvariantViolation(
                "exact ground comparator result or lane changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_exact_ground_comparator.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "query_occurrence_id": self.query_occurrence_id,
            "selected_reward": _fdoc(self.selected_reward),
            "selected_failure": _fdoc(self.selected_failure),
            "composed_candidate_count": self.composed_candidate_count,
            "verification_lane": self.verification_lane,
        }

    @property
    def comparator_id(self) -> str:
        return _content_id("exact_comparator", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "comparator_id": self.comparator_id}


def _solve_exact_ground_comparator_v1(
    context: RawSafeChainStructuralContextV1,
    occurrence: RawContextOccurrenceV1,
    kernel: RawSafeChainContextKernelV1,
) -> RawExactGroundComparatorV1:
    _validate_context_kernel(context, kernel)
    if (
        occurrence.context_id != context.context_id
        or occurrence.initial_mode != "D4_UNIFORM"
    ):
        raise RawMultiContextInvariantViolation(
            "exact comparator requires the registered uniform occurrence"
        )
    result = solve_ground_pareto(
        kernel,
        _query_for_occurrence_v1(occurrence),
    )
    if result.selected is None:
        raise RawMultiContextInvariantViolation(
            "registered raw context unexpectedly became infeasible"
        )
    return RawExactGroundComparatorV1(
        context.context_id,
        occurrence.occurrence_id,
        result.selected.expected_reward,
        result.selected.failure_probability,
        result.composed_candidate_count,
    )


def _independent_uniform_v1(
    seed: str,
    context_id: str,
    row_id: str,
    sample_index: int,
) -> Fraction:
    document = {
        "schema": "acfqp.counter_based_uniform.v1",
        "seed": seed,
        "context_id": context_id,
        "catalogue_row_id": row_id,
        "sample_index": sample_index,
    }
    digest = hashlib.sha256(
        b"acfqp:counter-based-uniform:v1\x00"
        + canonical_json_bytes(document)
    ).digest()
    return Fraction(int.from_bytes(digest, "big"), 2**256)


def _independently_replay_raw_log_v1(
    catalogue: G2048StatisticalCatalogueV1,
    context: RawSafeChainStructuralContextV1,
    kernel: RawSafeChainContextKernelV1,
    raw_log: PackedRawContextLogV1,
) -> tuple[tuple[str, ...], int]:
    _validate_context_kernel(context, kernel)
    failures: list[str] = []
    row_by_key = {row.key: row for row in catalogue.rows}
    codebook_by_key = {item.row_key: item for item in raw_log.codebooks}
    blocks_by_row: dict[str, list[PackedRawDrawBlockV1]] = {}
    for block in raw_log.blocks:
        blocks_by_row.setdefault(block.catalogue_row_id, []).append(block)
    replayed = 0
    for row_key in raw_log.authorized_row_keys:
        row = row_by_key[row_key]
        claimed_codebook = codebook_by_key[row_key]
        expected_codebook, weighted_outcomes = _row_outcomes(
            catalogue, context, kernel, row
        )
        if claimed_codebook.to_document() != expected_codebook.to_document():
            failures.append(
                f"RAW_CODEBOOK_REPLAY_MISMATCH:{context.context_key}:"
                f"{raw_log.lane.value}:{row_key}"
            )
        probabilities = tuple(
            probability for probability, _ in weighted_outcomes
        )
        if sum(probabilities, Fraction(0)) != 1:
            failures.append(
                f"EXACT_KERNEL_MASS_INVALID:{context.context_key}:{row_key}"
            )
        for block in sorted(
            blocks_by_row.get(row.row_id, ()),
            key=lambda item: item.block_index,
        ):
            for offset, observed_character in enumerate(
                block.outcome_nibbles_hex
            ):
                sample_index = block.start_index + offset
                uniform = _independent_uniform_v1(
                    block.seed,
                    context.context_id,
                    row.row_id,
                    sample_index,
                )
                cumulative = Fraction(0)
                expected_index = len(probabilities) - 1
                for index, probability in enumerate(probabilities):
                    cumulative += probability
                    if uniform < cumulative:
                        expected_index = index
                        break
                if int(observed_character, 16) != expected_index:
                    failures.append(
                        f"RAW_DRAW_REPLAY_MISMATCH:{context.context_key}:"
                        f"{raw_log.lane.value}:{row_key}"
                    )
                replayed += 1
    if replayed != raw_log.total_draw_count:
        failures.append(
            f"RAW_DRAW_COUNT_MISMATCH:{context.context_key}:"
            f"{raw_log.lane.value}"
        )
    return tuple(sorted(set(failures))), replayed


@dataclass(frozen=True, slots=True)
class RawMultiContextVerificationV1:
    claimed_result_id: str
    replay_result_id: str
    evidence_bundle_id: str
    failures: tuple[str, ...]
    exact_comparators: tuple[RawExactGroundComparatorV1, ...]
    raw_individual_draws_replayed: int
    exact_ground_composed_candidates: int
    verification_lane: str = "standalone_evaluation"
    production_kernel_access: int = 0
    statistical_exact_sound_promotion_authorized: bool = False
    sample_efficiency_promotion_authorized: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.claimed_result_id, "verification claimed result"),
            (self.replay_result_id, "verification replay result"),
            (self.evidence_bundle_id, "verification evidence bundle"),
        ):
            _cid(value, field_name)
        _exact_tuple(
            self.exact_comparators,
            RawExactGroundComparatorV1,
            "verification exact comparators",
        )
        if (
            type(self.failures) is not tuple
            or self.failures != tuple(sorted(set(self.failures)))
            or len(self.exact_comparators) != CONTEXT_COUNT
            or tuple(
                item.selected_failure for item in self.exact_comparators
            )
            != (
                Fraction(199, 20_000),
                Fraction(249, 31_250),
                Fraction(999, 500_000),
            )
            or self.raw_individual_draws_replayed
            != ADAPTIVE_TOTAL_DRAWS + DIRECT_TOTAL_DRAWS
            or self.exact_ground_composed_candidates != 3 * 5_440
            or self.verification_lane != "standalone_evaluation"
            or self.production_kernel_access != 0
            or self.statistical_exact_sound_promotion_authorized is not False
            or self.sample_efficiency_promotion_authorized is not False
        ):
            raise RawMultiContextInvariantViolation(
                "raw verification work, result, or claim boundary changed"
            )

    @property
    def verified(self) -> bool:
        return (
            not self.failures
            and self.claimed_result_id == self.replay_result_id
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_multicontext_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "claimed_result_id": self.claimed_result_id,
            "replay_result_id": self.replay_result_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "failures": list(self.failures),
            "verified": self.verified,
            "exact_comparators": [
                item.to_document() for item in self.exact_comparators
            ],
            "raw_individual_draws_replayed": (
                self.raw_individual_draws_replayed
            ),
            "exact_ground_composed_candidates": (
                self.exact_ground_composed_candidates
            ),
            "verification_lane": self.verification_lane,
            "production_kernel_access": self.production_kernel_access,
            "statistical_exact_sound_promotion_authorized": (
                self.statistical_exact_sound_promotion_authorized
            ),
            "sample_efficiency_promotion_authorized": (
                self.sample_efficiency_promotion_authorized
            ),
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_raw_multicontext_campaign_v1(
    catalogue: G2048StatisticalCatalogueV1,
    preregistration: RawMultiContextPreregistrationV1,
    evidence_bundle: RawMultiContextEvidenceBundleV1,
    kernels: tuple[RawSafeChainContextKernelV1, ...],
    claimed_result: RawMultiContextCampaignResultV1,
) -> RawMultiContextVerificationV1:
    """Replay production, every individual draw, and three exact J0 controls."""

    if (
        type(catalogue) is not G2048StatisticalCatalogueV1
        or type(preregistration) is not RawMultiContextPreregistrationV1
        or type(evidence_bundle) is not RawMultiContextEvidenceBundleV1
        or type(claimed_result) is not RawMultiContextCampaignResultV1
    ):
        raise RawMultiContextInvariantViolation(
            "raw campaign verifier rejects substituted inputs"
        )
    _exact_tuple(kernels, RawSafeChainContextKernelV1, "verification kernels")
    if len(kernels) != CONTEXT_COUNT:
        raise RawMultiContextInvariantViolation(
            "raw verifier requires exactly three context kernels"
        )
    expected = run_raw_multicontext_campaign_v1(
        catalogue, preregistration, evidence_bundle
    )
    _runtime_shape(claimed_result, expected, "claimed raw campaign")
    failures: list[str] = []
    if claimed_result.to_document() != expected.to_document():
        failures.append("CAMPAIGN_RESULT_RECONSTRUCTION_MISMATCH")

    replayed_draws = 0
    exact_comparators: list[RawExactGroundComparatorV1] = []
    result_by_context = {
        item.context.context_id: item
        for item in claimed_result.context_results
    }
    uniform_occurrences = {
        item.context_id: item
        for item in preregistration.occurrences
        if item.initial_mode == "D4_UNIFORM"
    }
    for context_evidence, kernel in zip(evidence_bundle.contexts, kernels):
        context = context_evidence.context
        _validate_context_kernel(context, kernel)
        for raw_log in (
            context_evidence.adaptive_log,
            context_evidence.direct_log,
        ):
            replay_failures, replay_count = (
                _independently_replay_raw_log_v1(
                    catalogue, context, kernel, raw_log
                )
            )
            failures.extend(replay_failures)
            replayed_draws += replay_count
        comparator = _solve_exact_ground_comparator_v1(
            context,
            uniform_occurrences[context.context_id],
            kernel,
        )
        exact_comparators.append(comparator)
        context_result = result_by_context[context.context_id]
        for lane, proof in (
            ("adaptive", context_result.adaptive_proof),
            ("direct", context_result.direct_proof),
        ):
            selected = proof.selected_policy
            if not (
                selected.reward_lower
                <= comparator.selected_reward
                <= selected.reward_upper
                and selected.failure_lower
                <= comparator.selected_failure
                <= selected.failure_upper
            ):
                failures.append(
                    f"EXACT_OPTIMUM_OUTSIDE_{lane.upper()}_CERTIFICATE:"
                    f"{context.context_key}"
                )
    return RawMultiContextVerificationV1(
        claimed_result.result_id,
        expected.result_id,
        evidence_bundle.bundle_id,
        tuple(sorted(set(failures))),
        tuple(exact_comparators),
        replayed_draws,
        sum(
            item.composed_candidate_count for item in exact_comparators
        ),
    )


__all__ = [
    "ACQUISITION_PROFILE_KEY",
    "ADAPTIVE_ROW_KEYS",
    "ADAPTIVE_TOTAL_DRAWS",
    "ALL_ROW_KEYS",
    "AcquisitionLane",
    "CERTIFIED_STATUS",
    "CONTRACT_VERSION",
    "DIRECT_TOTAL_DRAWS",
    "FAILED_STATUS",
    "GLOBAL_CONFIDENCE_LOWER",
    "GLOBAL_COORDINATE_OBLIGATIONS",
    "GLOBAL_FAMILY_TAIL_UPPER",
    "HOEFFDING_RADIUS",
    "IMPLEMENTATION_SHA256",
    "PROFILE_KEY",
    "PackedRawContextLogV1",
    "PackedRawDrawBlockV1",
    "RawAcquisitionProfileV1",
    "RawAdaptiveAuthorizationV1",
    "RawContextEvidenceV1",
    "RawContextOccurrenceV1",
    "RawContextPlanningResultV1",
    "RawExactGroundComparatorV1",
    "RawGroundOutcomeAtomV1",
    "RawMultiContextCampaignResultV1",
    "RawMultiContextEvidenceBundleV1",
    "RawMultiContextInvariantViolation",
    "RawMultiContextPreregistrationV1",
    "RawMultiContextVerificationV1",
    "RawMultiContextWorkV1",
    "RawOccurrenceResultV1",
    "RawPartialPlanProofV1",
    "RawPartialPolicyV1",
    "RawPartialStatisticalModelV1",
    "RawPartialStatisticalRowV1",
    "RawProbabilityIntervalV1",
    "RawRowCodebookV1",
    "RawSafeChainContextKernelV1",
    "RawSafeChainStructuralContextV1",
    "RowEvidence",
    "SAMPLE_COUNT_PER_ROW",
    "SUCCESS_STATUS",
    "acquire_raw_multicontext_evidence_v1",
    "build_raw_partial_statistical_model_v1",
    "preregister_raw_multicontext_campaign_v1",
    "registered_g2048_d4_statistical_catalogue_v1",
    "registered_raw_context_kernels_v1",
    "registered_raw_structural_contexts_v1",
    "run_raw_multicontext_campaign_v1",
    "solve_raw_partial_h2_v1",
    "verify_raw_multicontext_campaign_v1",
]
