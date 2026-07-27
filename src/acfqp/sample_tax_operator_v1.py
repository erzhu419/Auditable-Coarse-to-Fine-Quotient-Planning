"""Source-frozen, certificate-guarded sample-tax intervention.

V0-062 learns only an acquisition proposal from three source contexts.  The
proposal identifies a two-row boundary capability inside V0-061's three-row
failed-proof frontier.  Held-out target certificates use target observations
only; the source prior never narrows an interval or certifies a plan.  A
registered wrong-prior control must fail before its broad-tail row is acquired.

The positive result is deliberately narrow: it measures online target draws on
the unchanged V0-061 contexts and controls.  Offline source draws remain a
separate charged lane and exceed the observed target saving in this finite
campaign, so broad or offline-inclusive sample efficiency remains unclaimed.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
import hashlib
import inspect
import math
from itertools import combinations, product
from typing import Any, Mapping

from acfqp.domains.semantic import G2048RelativeSurvivorLabel
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
import acfqp.matched_end_to_end_workload_v1 as matched
import acfqp.raw_multicontext_acquisition_v1 as raw


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.26.0"
PROFILE_KEY = "g2048_source_frozen_boundary_capability_operator_v0"
SUCCESS_STATUS = (
    "CERTIFIED_REGISTERED_HELDOUT_SAMPLE_TAX_INTERVENTION"
)
WRONG_PRIOR_STATUS = "CERTIFIED_WRONG_PRIOR_FAIL_CLOSED_FALLBACK_CONTROL"

SAMPLE_COUNT_PER_ROW = raw.SAMPLE_COUNT_PER_ROW
DRAW_BLOCK_SIZE = raw.DRAW_BLOCK_SIZE
BLOCKS_PER_ROW = raw.BLOCKS_PER_ROW
HOEFFDING_RADIUS = raw.HOEFFDING_RADIUS
PER_COORDINATE_TAIL_UPPER = raw.PER_COORDINATE_TAIL_UPPER

SOURCE_CONTEXT_SPECS = (
    ("g2048_safe_chain_source_p497_500_v0", Fraction(497, 500)),
    ("g2048_safe_chain_source_p399_400_v0", Fraction(399, 400)),
    ("g2048_safe_chain_source_p1999_2000_v0", Fraction(1999, 2000)),
)
SOURCE_ROW_KEYS = raw.ADAPTIVE_ROW_KEYS
SOURCE_CONTEXT_COUNT = len(SOURCE_CONTEXT_SPECS)
TARGET_CONTEXT_COUNT = raw.CONTEXT_COUNT
TARGET_OCCURRENCE_COUNT = raw.OCCURRENCE_COUNT
PROPOSAL_PREFIX = ("ROOT_TOWARD", "CHAIN_A_AWAY")
BROAD_TAIL = ("CHAIN_B_AWAY",)
WRONG_PREFIX = ("ROOT_TOWARD", "CHAIN_B_AWAY")
WRONG_FALLBACK = ("CHAIN_A_AWAY",)

SOURCE_TOTAL_ROWS = SOURCE_CONTEXT_COUNT * len(SOURCE_ROW_KEYS)
SOURCE_TOTAL_DRAWS = SOURCE_TOTAL_ROWS * SAMPLE_COUNT_PER_ROW
TARGET_OPERATOR_ROWS = TARGET_CONTEXT_COUNT * len(PROPOSAL_PREFIX)
TARGET_OPERATOR_DRAWS = TARGET_OPERATOR_ROWS * SAMPLE_COUNT_PER_ROW
TARGET_CONTROL_ROWS = TARGET_CONTEXT_COUNT * len(SOURCE_ROW_KEYS)
TARGET_CONTROL_DRAWS = TARGET_CONTROL_ROWS * SAMPLE_COUNT_PER_ROW
TARGET_ONLINE_DRAW_SAVING = TARGET_CONTROL_DRAWS - TARGET_OPERATOR_DRAWS
TARGET_ONLINE_REDUCTION = Fraction(
    TARGET_ONLINE_DRAW_SAVING, TARGET_CONTROL_DRAWS
)
OFFLINE_INCLUSIVE_OPERATOR_DRAWS = (
    SOURCE_TOTAL_DRAWS + TARGET_OPERATOR_DRAWS
)
DIAGNOSTIC_SOURCE_AMORTIZATION_CONTEXTS = (
    SOURCE_TOTAL_DRAWS
    // (len(BROAD_TAIL) * SAMPLE_COUNT_PER_ROW)
)
TARGET_OPERATOR_OBLIGATIONS = 2 * TARGET_OPERATOR_ROWS
TARGET_OPERATOR_FAMILY_TAIL_UPPER = (
    TARGET_OPERATOR_OBLIGATIONS * PER_COORDINATE_TAIL_UPPER
)
TARGET_OPERATOR_CONFIDENCE_LOWER = (
    1 - TARGET_OPERATOR_FAMILY_TAIL_UPPER
)

IMPLEMENTATION_SHA256 = (
    "decc1f2f34d08cdec9eefe72d5c645ef8a50af5c8692ec9beecd82d48b21b2da"
)

DOMAIN_TAGS = {
    "profile": "acfqp:sample-tax-operator-profile:v1",
    "source_context": "acfqp:sample-tax-source-context:v1",
    "preregistration": "acfqp:sample-tax-preregistration:v1",
    "source_block": "acfqp:sample-tax-source-block:v1",
    "source_log": "acfqp:sample-tax-source-log:v1",
    "source_evidence": "acfqp:sample-tax-source-evidence:v1",
    "source_assessment": "acfqp:sample-tax-source-assessment:v1",
    "source_prior": "acfqp:sample-tax-source-frozen-prior:v1",
    "target_subset_log": "acfqp:sample-tax-target-subset-log:v1",
    "target_context_evidence": "acfqp:sample-tax-target-context-evidence:v1",
    "target_evidence": "acfqp:sample-tax-target-evidence:v1",
    "wrong_context_evidence": "acfqp:sample-tax-wrong-context-evidence:v1",
    "wrong_evidence": "acfqp:sample-tax-wrong-evidence:v1",
    "row": "acfqp:sample-tax-statistical-row:v1",
    "model": "acfqp:sample-tax-partial-model:v1",
    "policy": "acfqp:sample-tax-policy:v1",
    "proof": "acfqp:sample-tax-plan-proof:v1",
    "context_result": "acfqp:sample-tax-context-result:v1",
    "occurrence_result": "acfqp:sample-tax-occurrence-result:v1",
    "work": "acfqp:sample-tax-work:v1",
    "campaign": "acfqp:sample-tax-campaign:v1",
    "wrong_context_result": "acfqp:sample-tax-wrong-context-result:v1",
    "wrong_result": "acfqp:sample-tax-wrong-result:v1",
    "comparator": "acfqp:sample-tax-exact-comparator:v1",
    "verification": "acfqp:sample-tax-verification:v1",
}


class SampleTaxOperatorInvariantViolation(ValueError):
    """A V0-062 authority, trace, proposal, or certificate is inconsistent."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise SampleTaxOperatorInvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise SampleTaxOperatorInvariantViolation(
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
        raise SampleTaxOperatorInvariantViolation(
            f"{field_name} rejects nested runtime substitutions"
        )
    return value


def _runtime_shape(claimed: Any, expected: Any, path: str) -> None:
    if type(claimed) is not type(expected):
        raise SampleTaxOperatorInvariantViolation(
            f"{path} contains a nested runtime substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise SampleTaxOperatorInvariantViolation(
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


@dataclass(frozen=True, slots=True)
class SampleTaxOperatorProfileV1:
    source_row_keys: tuple[str, ...] = SOURCE_ROW_KEYS
    candidate_prefix_size: int = 2
    sample_count_per_row: int = SAMPLE_COUNT_PER_ROW
    draw_block_size: int = DRAW_BLOCK_SIZE
    radius: Fraction = HOEFFDING_RADIUS
    per_coordinate_tail_upper: Fraction = PER_COORDINATE_TAIL_UPPER
    target_operator_obligations: int = TARGET_OPERATOR_OBLIGATIONS
    target_family_tail_upper: Fraction = (
        TARGET_OPERATOR_FAMILY_TAIL_UPPER
    )
    target_confidence_lower: Fraction = (
        TARGET_OPERATOR_CONFIDENCE_LOWER
    )
    source_seed: str = "acfqp-v0062-offline-source-seed-v1"
    source_counter_protocol: str = "sha256_counter_uint256_ceil_cdf_v1"
    proposal_semantics: str = (
        "source_unanimous_minimal_boundary_capability_then_broad_tail"
    )

    def __post_init__(self) -> None:
        if (
            self.source_row_keys != SOURCE_ROW_KEYS
            or self.candidate_prefix_size != 2
            or self.sample_count_per_row != 16_384
            or self.draw_block_size != 4_096
            or self.sample_count_per_row % self.draw_block_size
            or self.radius != Fraction(1, 64)
            or self.per_coordinate_tail_upper != Fraction(1, 1400)
            or self.target_operator_obligations != 12
            or self.target_family_tail_upper != Fraction(3, 350)
            or self.target_confidence_lower != Fraction(347, 350)
            or self.source_seed
            != "acfqp-v0062-offline-source-seed-v1"
            or self.source_counter_protocol
            != "sha256_counter_uint256_ceil_cdf_v1"
            or self.proposal_semantics
            != (
                "source_unanimous_minimal_boundary_capability_then_"
                "broad_tail"
            )
        ):
            raise SampleTaxOperatorInvariantViolation(
                "sample-tax operator profile changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_operator_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "source_row_keys": list(self.source_row_keys),
            "candidate_prefix_size": self.candidate_prefix_size,
            "sample_count_per_row": self.sample_count_per_row,
            "draw_block_size": self.draw_block_size,
            "radius": _fdoc(self.radius),
            "per_coordinate_tail_upper": _fdoc(
                self.per_coordinate_tail_upper
            ),
            "target_operator_obligations": (
                self.target_operator_obligations
            ),
            "target_family_tail_upper": _fdoc(
                self.target_family_tail_upper
            ),
            "target_confidence_lower": _fdoc(
                self.target_confidence_lower
            ),
            "source_seed": self.source_seed,
            "source_counter_protocol": self.source_counter_protocol,
            "proposal_semantics": self.proposal_semantics,
            "source_prior_may_only_propose": True,
            "target_only_certificate_required": True,
            "broad_tail_required": True,
        }

    @property
    def profile_id(self) -> str:
        return _content_id("profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


@dataclass(frozen=True, slots=True)
class SourceSafeChainContextV1:
    context_key: str
    rank_one_probability: Fraction
    catalogue_id: str
    board_size: int = 2
    rank_cap: int = 6
    horizon: int = 2
    delta: Fraction = Fraction(1, 20)
    offline_source_only: bool = True

    def __post_init__(self) -> None:
        _cid(self.catalogue_id, "source context catalogue")
        expected = dict(SOURCE_CONTEXT_SPECS).get(self.context_key)
        if (
            expected is None
            or type(self.rank_one_probability) is not Fraction
            or self.rank_one_probability != expected
            or self.board_size != 2
            or self.rank_cap != 6
            or self.horizon != 2
            or self.delta != Fraction(1, 20)
            or self.offline_source_only is not True
        ):
            raise SampleTaxOperatorInvariantViolation(
                "offline source context changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_source_context.v1",
            "schema_version": SCHEMA_VERSION,
            "context_key": self.context_key,
            "rank_one_probability": _fdoc(self.rank_one_probability),
            "rank_two_probability": _fdoc(
                1 - self.rank_one_probability
            ),
            "catalogue_id": self.catalogue_id,
            "board_size": self.board_size,
            "rank_cap": self.rank_cap,
            "horizon": self.horizon,
            "delta": _fdoc(self.delta),
            "offline_source_only": self.offline_source_only,
        }

    @property
    def context_id(self) -> str:
        return _content_id("source_context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


def registered_source_contexts_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
) -> tuple[SourceSafeChainContextV1, ...]:
    if type(catalogue) is not raw.G2048StatisticalCatalogueV1:
        raise SampleTaxOperatorInvariantViolation(
            "source registry rejects substituted catalogues"
        )
    expected = raw.registered_g2048_d4_statistical_catalogue_v1()
    if catalogue.to_document() != expected.to_document():
        raise SampleTaxOperatorInvariantViolation(
            "source registry requires the frozen probability-free catalogue"
        )
    return tuple(
        SourceSafeChainContextV1(key, probability, catalogue.catalogue_id)
        for key, probability in SOURCE_CONTEXT_SPECS
    )


def registered_source_kernels_v1(
) -> tuple[raw.RawSafeChainContextKernelV1, ...]:
    return tuple(
        raw.RawSafeChainContextKernelV1(
            size=2,
            context_key=key,
            rank_one_probability=probability,
        )
        for key, probability in SOURCE_CONTEXT_SPECS
    )


@dataclass(frozen=True, slots=True)
class SampleTaxPreregistrationV1:
    matched_preregistration: matched.MatchedWorkloadPreregistrationV1
    profile: SampleTaxOperatorProfileV1
    source_contexts: tuple[SourceSafeChainContextV1, ...]
    target_context_ids: tuple[str, ...]
    target_occurrence_ids: tuple[str, ...]
    source_target_context_ids_disjoint: bool = True
    prospective_source_evidence_ids_absent: bool = True
    prospective_target_evidence_ids_absent: bool = True
    prospective_prior_id_absent: bool = True
    prospective_result_ids_absent: bool = True
    offline_and_online_lanes_separate: bool = True
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.matched_preregistration)
            is not matched.MatchedWorkloadPreregistrationV1
            or type(self.profile) is not SampleTaxOperatorProfileV1
        ):
            raise SampleTaxOperatorInvariantViolation(
                "sample-tax preregistration rejects substituted authorities"
            )
        _exact_tuple(
            self.source_contexts,
            SourceSafeChainContextV1,
            "sample-tax source contexts",
        )
        baseline = matched.preregister_matched_end_to_end_workload_v1(
            raw.registered_g2048_d4_statistical_catalogue_v1()
        )
        expected_sources = registered_source_contexts_v1(
            raw.registered_g2048_d4_statistical_catalogue_v1()
        )
        expected_targets = tuple(
            item.context_id
            for item in baseline.source_preregistration.contexts
        )
        expected_occurrences = tuple(
            item.occurrence_id
            for item in baseline.source_preregistration.occurrences
        )
        source_ids = {item.context_id for item in self.source_contexts}
        if (
            self.matched_preregistration.to_document()
            != baseline.to_document()
            or self.profile != SampleTaxOperatorProfileV1()
            or self.source_contexts != expected_sources
            or self.target_context_ids != expected_targets
            or self.target_occurrence_ids != expected_occurrences
            or not source_ids.isdisjoint(self.target_context_ids)
            or self.source_target_context_ids_disjoint is not True
            or self.prospective_source_evidence_ids_absent is not True
            or self.prospective_target_evidence_ids_absent is not True
            or self.prospective_prior_id_absent is not True
            or self.prospective_result_ids_absent is not True
            or self.offline_and_online_lanes_separate is not True
            or self.official_execution_allowed is not False
        ):
            raise SampleTaxOperatorInvariantViolation(
                "sample-tax split, chronology, or claim scope changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "implementation_sha256": IMPLEMENTATION_SHA256,
            "matched_preregistration": (
                self.matched_preregistration.to_document()
            ),
            "profile": self.profile.to_document(),
            "source_contexts": [
                item.to_document() for item in self.source_contexts
            ],
            "target_context_ids": list(self.target_context_ids),
            "target_occurrence_ids": list(self.target_occurrence_ids),
            "source_target_context_ids_disjoint": (
                self.source_target_context_ids_disjoint
            ),
            "prospective_source_evidence_ids_absent": (
                self.prospective_source_evidence_ids_absent
            ),
            "prospective_target_evidence_ids_absent": (
                self.prospective_target_evidence_ids_absent
            ),
            "prospective_prior_id_absent": self.prospective_prior_id_absent,
            "prospective_result_ids_absent": (
                self.prospective_result_ids_absent
            ),
            "offline_and_online_lanes_separate": (
                self.offline_and_online_lanes_separate
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


def preregister_sample_tax_operator_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
) -> SampleTaxPreregistrationV1:
    baseline = matched.preregister_matched_end_to_end_workload_v1(catalogue)
    return SampleTaxPreregistrationV1(
        baseline,
        SampleTaxOperatorProfileV1(),
        registered_source_contexts_v1(catalogue),
        tuple(
            item.context_id
            for item in baseline.source_preregistration.contexts
        ),
        tuple(
            item.occurrence_id
            for item in baseline.source_preregistration.occurrences
        ),
    )


@dataclass(frozen=True, slots=True)
class SourcePackedDrawBlockV1:
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
            (self.context_id, "source block context"),
            (self.catalogue_row_id, "source block row"),
            (self.codebook_id, "source block codebook"),
        ):
            _cid(value, field_name)
        if self.previous_block_id is not None:
            _cid(self.previous_block_id, "source block predecessor")
        if (
            self.seed != SampleTaxOperatorProfileV1().source_seed
            or type(self.block_index) is not int
            or not 0 <= self.block_index < BLOCKS_PER_ROW
            or self.start_index != self.block_index * DRAW_BLOCK_SIZE
            or self.draw_count != DRAW_BLOCK_SIZE
            or type(self.outcome_nibbles_hex) is not str
            or len(self.outcome_nibbles_hex) != DRAW_BLOCK_SIZE
            or any(character not in "0123" for character in self.outcome_nibbles_hex)
            or (self.block_index == 0)
            != (self.previous_block_id is None)
        ):
            raise SampleTaxOperatorInvariantViolation(
                "offline source block changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_source_block.v1",
            "schema_version": SCHEMA_VERSION,
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
        return _content_id("source_block", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "block_id": self.block_id}


@dataclass(frozen=True, slots=True)
class SourceContextLogV1:
    preregistration_id: str
    context: SourceSafeChainContextV1
    codebooks: tuple[raw.RawRowCodebookV1, ...]
    blocks: tuple[SourcePackedDrawBlockV1, ...]
    row_keys: tuple[str, ...] = SOURCE_ROW_KEYS
    sample_count_per_row: int = SAMPLE_COUNT_PER_ROW
    total_draw_count: int = len(SOURCE_ROW_KEYS) * SAMPLE_COUNT_PER_ROW
    lane: str = "offline_source"
    exact_probabilities_embedded: bool = False

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "source log preregistration")
        if type(self.context) is not SourceSafeChainContextV1:
            raise SampleTaxOperatorInvariantViolation(
                "source log rejects substituted contexts"
            )
        _exact_tuple(self.codebooks, raw.RawRowCodebookV1, "source codebooks")
        _exact_tuple(self.blocks, SourcePackedDrawBlockV1, "source blocks")
        if (
            self.row_keys != SOURCE_ROW_KEYS
            or tuple(item.row_key for item in self.codebooks)
            != SOURCE_ROW_KEYS
            or any(
                item.context_id != self.context.context_id
                for item in self.codebooks
            )
            or len(self.blocks) != len(SOURCE_ROW_KEYS) * BLOCKS_PER_ROW
            or self.sample_count_per_row != SAMPLE_COUNT_PER_ROW
            or self.total_draw_count
            != len(SOURCE_ROW_KEYS) * SAMPLE_COUNT_PER_ROW
            or self.lane != "offline_source"
            or self.exact_probabilities_embedded is not False
        ):
            raise SampleTaxOperatorInvariantViolation(
                "source log coverage or lane changed"
            )
        codebook_by_row = {
            item.catalogue_row_id: item for item in self.codebooks
        }
        expected_order: list[tuple[str, int]] = []
        for codebook in self.codebooks:
            previous: str | None = None
            row_blocks = tuple(
                item
                for item in self.blocks
                if item.catalogue_row_id == codebook.catalogue_row_id
            )
            if len(row_blocks) != BLOCKS_PER_ROW:
                raise SampleTaxOperatorInvariantViolation(
                    "source row block coverage changed"
                )
            for index, block in enumerate(row_blocks):
                if (
                    block.context_id != self.context.context_id
                    or block.codebook_id != codebook.codebook_id
                    or block.block_index != index
                    or block.previous_block_id != previous
                    or any(
                        int(character, 16) >= len(codebook.outcomes)
                        for character in block.outcome_nibbles_hex
                    )
                ):
                    raise SampleTaxOperatorInvariantViolation(
                        "source block chain/codebook binding changed"
                    )
                previous = block.block_id
                expected_order.append(
                    (codebook.catalogue_row_id, index)
                )
        if (
            set(codebook_by_row) != {
                item.catalogue_row_id for item in self.blocks
            }
            or tuple(
                (item.catalogue_row_id, item.block_index)
                for item in self.blocks
            )
            != tuple(expected_order)
        ):
            raise SampleTaxOperatorInvariantViolation(
                "source block order changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_source_log.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "context": self.context.to_document(),
            "codebooks": [item.to_document() for item in self.codebooks],
            "blocks": [item.to_document() for item in self.blocks],
            "row_keys": list(self.row_keys),
            "sample_count_per_row": self.sample_count_per_row,
            "total_draw_count": self.total_draw_count,
            "lane": self.lane,
            "exact_probabilities_embedded": (
                self.exact_probabilities_embedded
            ),
        }

    @property
    def log_id(self) -> str:
        return _content_id("source_log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "log_id": self.log_id}


@dataclass(frozen=True, slots=True)
class SourceEvidenceBundleV1:
    preregistration_id: str
    logs: tuple[SourceContextLogV1, ...]
    source_rows: int = SOURCE_TOTAL_ROWS
    source_individual_draws: int = SOURCE_TOTAL_DRAWS
    target_evidence_ids_used: tuple[str, ...] = ()
    target_kernel_access: int = 0

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "source evidence preregistration")
        _exact_tuple(self.logs, SourceContextLogV1, "source evidence logs")
        if (
            len(self.logs) != SOURCE_CONTEXT_COUNT
            or len({item.context.context_id for item in self.logs})
            != SOURCE_CONTEXT_COUNT
            or any(
                item.preregistration_id != self.preregistration_id
                for item in self.logs
            )
            or self.source_rows != SOURCE_TOTAL_ROWS
            or self.source_individual_draws != SOURCE_TOTAL_DRAWS
            or self.source_individual_draws
            != sum(item.total_draw_count for item in self.logs)
            or self.target_evidence_ids_used != ()
            or self.target_kernel_access != 0
        ):
            raise SampleTaxOperatorInvariantViolation(
                "source evidence count or isolation changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_source_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "logs": [item.to_document() for item in self.logs],
            "source_rows": self.source_rows,
            "source_individual_draws": self.source_individual_draws,
            "target_evidence_ids_used": list(
                self.target_evidence_ids_used
            ),
            "target_kernel_access": self.target_kernel_access,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("source_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


def _source_uniform_v1(
    seed: str,
    context_id: str,
    row_id: str,
    sample_index: int,
) -> int:
    payload = {
        "schema": "acfqp.sample_tax_source_counter_uniform.v1",
        "seed": seed,
        "context_id": context_id,
        "catalogue_row_id": row_id,
        "sample_index": sample_index,
    }
    digest = hashlib.sha256(
        b"acfqp:sample-tax-source-counter-uniform:v1\x00"
        + canonical_json_bytes(payload)
    ).digest()
    return int.from_bytes(digest, "big")


def _integer_thresholds_v1(
    probabilities: tuple[Fraction, ...],
) -> tuple[int, ...]:
    if (
        not probabilities
        or any(type(item) is not Fraction or item < 0 for item in probabilities)
        or sum(probabilities, Fraction(0)) != 1
    ):
        raise SampleTaxOperatorInvariantViolation(
            "source sampling probabilities are invalid"
        )
    denominator = 1 << 256
    cumulative = Fraction(0)
    thresholds: list[int] = []
    for probability in probabilities:
        cumulative += probability
        numerator = cumulative.numerator * denominator
        thresholds.append(
            (numerator + cumulative.denominator - 1)
            // cumulative.denominator
        )
    thresholds[-1] = denominator
    return tuple(thresholds)


def _sample_index_v1(
    thresholds: tuple[int, ...], uniform: int
) -> int:
    for index, threshold in enumerate(thresholds):
        if uniform < threshold:
            return index
    raise SampleTaxOperatorInvariantViolation(
        "source uniform variate escaped the exact CDF"
    )


def acquire_source_evidence_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: SampleTaxPreregistrationV1,
    kernels: tuple[raw.RawSafeChainContextKernelV1, ...],
) -> SourceEvidenceBundleV1:
    """Acquire offline source logs. Exact kernels never enter prior fitting."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration) is not SampleTaxPreregistrationV1
    ):
        raise SampleTaxOperatorInvariantViolation(
            "source acquisition rejects substituted inputs"
        )
    _exact_tuple(
        kernels,
        raw.RawSafeChainContextKernelV1,
        "offline source kernels",
    )
    expected = preregister_sample_tax_operator_v1(catalogue)
    _runtime_shape(preregistration, expected, "sample-tax preregistration")
    if preregistration.to_document() != expected.to_document():
        raise SampleTaxOperatorInvariantViolation(
            "source acquisition preregistration mismatch"
        )
    if len(kernels) != SOURCE_CONTEXT_COUNT:
        raise SampleTaxOperatorInvariantViolation(
            "source acquisition requires three source kernels"
        )
    row_by_key = {item.key: item for item in catalogue.rows}
    logs: list[SourceContextLogV1] = []
    for context, kernel in zip(preregistration.source_contexts, kernels):
        if (
            kernel.context_key != context.context_key
            or kernel.rank_one_probability
            != context.rank_one_probability
        ):
            raise SampleTaxOperatorInvariantViolation(
                "source kernel/context mismatch"
            )
        codebooks: list[raw.RawRowCodebookV1] = []
        blocks: list[SourcePackedDrawBlockV1] = []
        for row_key in SOURCE_ROW_KEYS:
            row = row_by_key[row_key]
            codebook, weighted = raw._row_outcomes(
                catalogue, context, kernel, row
            )
            probabilities = tuple(item[0] for item in weighted)
            thresholds = _integer_thresholds_v1(probabilities)
            codebooks.append(codebook)
            previous: str | None = None
            for block_index in range(BLOCKS_PER_ROW):
                start = block_index * DRAW_BLOCK_SIZE
                nibbles = "".join(
                    format(
                        _sample_index_v1(
                            thresholds,
                            _source_uniform_v1(
                                preregistration.profile.source_seed,
                                context.context_id,
                                row.row_id,
                                sample_index,
                            ),
                        ),
                        "x",
                    )
                    for sample_index in range(
                        start, start + DRAW_BLOCK_SIZE
                    )
                )
                block = SourcePackedDrawBlockV1(
                    context.context_id,
                    row.row_id,
                    codebook.codebook_id,
                    preregistration.profile.source_seed,
                    block_index,
                    start,
                    DRAW_BLOCK_SIZE,
                    nibbles,
                    previous,
                )
                blocks.append(block)
                previous = block.block_id
        logs.append(
            SourceContextLogV1(
                preregistration.preregistration_id,
                context,
                tuple(codebooks),
                tuple(blocks),
            )
        )
    return SourceEvidenceBundleV1(
        preregistration.preregistration_id, tuple(logs)
    )


@dataclass(frozen=True, slots=True)
class StatisticalRowV1:
    catalogue_row_id: str
    row_key: str
    lower: Fraction
    upper: Fraction
    empirical_probability: Fraction | None
    sample_count: int
    evidence_log_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.catalogue_row_id, "statistical row catalogue")
        if type(self.evidence_log_ids) is not tuple:
            raise SampleTaxOperatorInvariantViolation(
                "statistical row evidence IDs must be a tuple"
            )
        for item in self.evidence_log_ids:
            _cid(item, "statistical row evidence")
        if (
            self.row_key not in raw.ALL_ROW_KEYS
            or type(self.lower) is not Fraction
            or type(self.upper) is not Fraction
            or not 0 <= self.lower <= self.upper <= 1
        ):
            raise SampleTaxOperatorInvariantViolation(
                "statistical row bounds changed"
            )
        if self.empirical_probability is None:
            if (
                self.lower != 0
                or self.upper != 1
                or self.sample_count != 0
                or self.evidence_log_ids
            ):
                raise SampleTaxOperatorInvariantViolation(
                    "missing statistical row must remain vacuous"
                )
        elif (
            type(self.empirical_probability) is not Fraction
            or not self.lower
            <= self.empirical_probability
            <= self.upper
            or self.sample_count != SAMPLE_COUNT_PER_ROW
            or not self.evidence_log_ids
        ):
            raise SampleTaxOperatorInvariantViolation(
                "observed statistical row is incomplete"
            )

    @property
    def observed(self) -> bool:
        return self.empirical_probability is not None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_statistical_row.v1",
            "schema_version": SCHEMA_VERSION,
            "catalogue_row_id": self.catalogue_row_id,
            "row_key": self.row_key,
            "lower": _fdoc(self.lower),
            "upper": _fdoc(self.upper),
            "empirical_probability": (
                None
                if self.empirical_probability is None
                else _fdoc(self.empirical_probability)
            ),
            "sample_count": self.sample_count,
            "evidence_log_ids": list(self.evidence_log_ids),
        }

    @property
    def row_id(self) -> str:
        return _content_id("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_id": self.row_id}


def _decode_observed_row_v1(
    catalogue_row: raw.StatisticalRowCatalogueV1,
    codebook: raw.RawRowCodebookV1,
    blocks: tuple[Any, ...],
    evidence_log_id: str,
) -> StatisticalRowV1:
    if (
        codebook.catalogue_row_id != catalogue_row.row_id
        or codebook.row_key != catalogue_row.key
        or len(blocks) != BLOCKS_PER_ROW
    ):
        raise SampleTaxOperatorInvariantViolation(
            "observed row/codebook coverage changed"
        )
    first_destination = catalogue_row.destination_cell_ids[0]
    count = 0
    total = 0
    for block in blocks:
        for character in block.outcome_nibbles_hex:
            atom = codebook.outcomes[int(character, 16)]
            count += atom.destination_cell_id == first_destination
            total += 1
    if total != SAMPLE_COUNT_PER_ROW:
        raise SampleTaxOperatorInvariantViolation(
            "observed row draw count changed"
        )
    empirical = Fraction(count, total)
    return StatisticalRowV1(
        catalogue_row.row_id,
        catalogue_row.key,
        max(Fraction(0), empirical - HOEFFDING_RADIUS),
        min(Fraction(1), empirical + HOEFFDING_RADIUS),
        empirical,
        total,
        (evidence_log_id,),
    )


def _selected_schedule_failure_upper_v1(
    rows: Mapping[str, StatisticalRowV1],
) -> Fraction:
    q = rows["ROOT_TOWARD"]
    a = rows["CHAIN_A_AWAY"]
    b = rows["CHAIN_B_AWAY"]
    return max(
        root * chain_a + (1 - root) * chain_b
        for root in (q.lower, q.upper)
        for chain_a in (a.lower, a.upper)
        for chain_b in (b.lower, b.upper)
    )


@dataclass(frozen=True, slots=True)
class SourceSubsetAssessmentV1:
    source_context_id: str
    source_log_id: str
    observed_row_keys: tuple[str, str]
    failure_upper: Fraction
    delta: Fraction
    certifies: bool

    def __post_init__(self) -> None:
        _cid(self.source_context_id, "source assessment context")
        _cid(self.source_log_id, "source assessment log")
        allowed = tuple(combinations(SOURCE_ROW_KEYS, 2))
        if (
            self.observed_row_keys not in allowed
            or type(self.failure_upper) is not Fraction
            or not 0 <= self.failure_upper <= 1
            or self.delta != Fraction(1, 20)
            or self.certifies
            != (self.failure_upper <= self.delta)
        ):
            raise SampleTaxOperatorInvariantViolation(
                "source subset assessment changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_source_assessment.v1",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.source_context_id,
            "source_log_id": self.source_log_id,
            "observed_row_keys": list(self.observed_row_keys),
            "failure_upper": _fdoc(self.failure_upper),
            "delta": _fdoc(self.delta),
            "certifies": self.certifies,
            "proposal_only_not_target_certificate": True,
        }

    @property
    def assessment_id(self) -> str:
        return _content_id("source_assessment", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "assessment_id": self.assessment_id,
        }


@dataclass(frozen=True, slots=True)
class SourceFrozenPriorV1:
    preregistration_id: str
    source_evidence_id: str
    source_context_ids: tuple[str, ...]
    assessments: tuple[SourceSubsetAssessmentV1, ...]
    proposed_prefix: tuple[str, str]
    broad_tail: tuple[str, ...]
    target_context_ids_seen: tuple[str, ...] = ()
    target_evidence_ids_seen: tuple[str, ...] = ()
    target_kernel_access: int = 0
    may_narrow_target_envelopes: bool = False
    may_certify_target_plans: bool = False
    frozen_before_target_evidence: bool = True

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "source prior preregistration")
        _cid(self.source_evidence_id, "source prior evidence")
        for item in self.source_context_ids:
            _cid(item, "source prior context")
        _exact_tuple(
            self.assessments,
            SourceSubsetAssessmentV1,
            "source prior assessments",
        )
        contexts = tuple(
            sorted(set(item.source_context_id for item in self.assessments))
        )
        unanimous = tuple(
            subset
            for subset in combinations(SOURCE_ROW_KEYS, 2)
            if all(
                any(
                    item.source_context_id == context_id
                    and item.observed_row_keys == subset
                    and item.certifies
                    for item in self.assessments
                )
                for context_id in self.source_context_ids
            )
        )
        if (
            len(self.source_context_ids) != SOURCE_CONTEXT_COUNT
            or tuple(sorted(self.source_context_ids)) != contexts
            or len(self.assessments)
            != SOURCE_CONTEXT_COUNT
            * math.comb(len(SOURCE_ROW_KEYS), 2)
            or unanimous != (PROPOSAL_PREFIX,)
            or self.proposed_prefix != PROPOSAL_PREFIX
            or self.broad_tail != BROAD_TAIL
            or tuple(
                key
                for key in SOURCE_ROW_KEYS
                if key not in self.proposed_prefix
            )
            != self.broad_tail
            or self.target_context_ids_seen != ()
            or self.target_evidence_ids_seen != ()
            or self.target_kernel_access != 0
            or self.may_narrow_target_envelopes is not False
            or self.may_certify_target_plans is not False
            or self.frozen_before_target_evidence is not True
        ):
            raise SampleTaxOperatorInvariantViolation(
                "source prior proposal, isolation, or authority changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_source_frozen_prior.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "source_evidence_id": self.source_evidence_id,
            "source_context_ids": list(self.source_context_ids),
            "assessments": [
                item.to_document() for item in self.assessments
            ],
            "proposed_prefix": list(self.proposed_prefix),
            "broad_tail": list(self.broad_tail),
            "target_context_ids_seen": list(
                self.target_context_ids_seen
            ),
            "target_evidence_ids_seen": list(
                self.target_evidence_ids_seen
            ),
            "target_kernel_access": self.target_kernel_access,
            "may_narrow_target_envelopes": (
                self.may_narrow_target_envelopes
            ),
            "may_certify_target_plans": self.may_certify_target_plans,
            "frozen_before_target_evidence": (
                self.frozen_before_target_evidence
            ),
        }

    @property
    def prior_id(self) -> str:
        return _content_id("source_prior", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prior_id": self.prior_id}


def _rows_from_source_log_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    log: SourceContextLogV1,
) -> dict[str, StatisticalRowV1]:
    row_by_key = {item.key: item for item in catalogue.rows}
    codebook_by_key = {item.row_key: item for item in log.codebooks}
    result: dict[str, StatisticalRowV1] = {}
    for key in SOURCE_ROW_KEYS:
        codebook = codebook_by_key[key]
        blocks = tuple(
            item
            for item in log.blocks
            if item.catalogue_row_id == codebook.catalogue_row_id
        )
        result[key] = _decode_observed_row_v1(
            row_by_key[key], codebook, blocks, log.log_id
        )
    return result


def build_source_frozen_prior_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: SampleTaxPreregistrationV1,
    source_evidence: SourceEvidenceBundleV1,
) -> SourceFrozenPriorV1:
    """Fit a proposal from source logs only. No target input is accepted."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration) is not SampleTaxPreregistrationV1
        or type(source_evidence) is not SourceEvidenceBundleV1
        or source_evidence.preregistration_id
        != preregistration.preregistration_id
    ):
        raise SampleTaxOperatorInvariantViolation(
            "source prior builder rejects substituted or stale inputs"
        )
    row_by_key = {item.key: item for item in catalogue.rows}
    assessments: list[SourceSubsetAssessmentV1] = []
    for log in source_evidence.logs:
        observed = _rows_from_source_log_v1(catalogue, log)
        for subset in combinations(SOURCE_ROW_KEYS, 2):
            rows = {
                key: (
                    observed[key]
                    if key in subset
                    else StatisticalRowV1(
                        row_by_key[key].row_id,
                        key,
                        Fraction(0),
                        Fraction(1),
                        None,
                        0,
                        (),
                    )
                )
                for key in SOURCE_ROW_KEYS
            }
            upper = _selected_schedule_failure_upper_v1(rows)
            assessments.append(
                SourceSubsetAssessmentV1(
                    log.context.context_id,
                    log.log_id,
                    subset,
                    upper,
                    Fraction(1, 20),
                    upper <= Fraction(1, 20),
                )
            )
    return SourceFrozenPriorV1(
        preregistration.preregistration_id,
        source_evidence.evidence_id,
        tuple(item.context.context_id for item in source_evidence.logs),
        tuple(assessments),
        PROPOSAL_PREFIX,
        BROAD_TAIL,
    )


@dataclass(frozen=True, slots=True)
class TargetSubsetLogV1:
    preregistration_id: str
    context: raw.RawSafeChainStructuralContextV1
    parent_adaptive_evidence_id: str
    parent_log_id: str
    role: str
    row_keys: tuple[str, ...]
    codebooks: tuple[raw.RawRowCodebookV1, ...]
    blocks: tuple[raw.PackedRawDrawBlockV1, ...]
    sample_count_per_row: int = SAMPLE_COUNT_PER_ROW
    exact_probabilities_embedded: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.preregistration_id, "target subset preregistration"),
            (
                self.parent_adaptive_evidence_id,
                "target subset parent evidence",
            ),
            (self.parent_log_id, "target subset parent log"),
        ):
            _cid(value, field_name)
        if type(self.context) is not raw.RawSafeChainStructuralContextV1:
            raise SampleTaxOperatorInvariantViolation(
                "target subset rejects substituted contexts"
            )
        _exact_tuple(
            self.codebooks, raw.RawRowCodebookV1, "target subset codebooks"
        )
        _exact_tuple(
            self.blocks, raw.PackedRawDrawBlockV1, "target subset blocks"
        )
        expected_by_role = {
            "operator_prefix": PROPOSAL_PREFIX,
            "wrong_prefix": WRONG_PREFIX,
            "wrong_fallback": WRONG_FALLBACK,
        }
        expected_rows = expected_by_role.get(self.role)
        if (
            expected_rows is None
            or self.row_keys != expected_rows
            or tuple(item.row_key for item in self.codebooks)
            != self.row_keys
            or any(
                item.context_id != self.context.context_id
                for item in self.codebooks
            )
            or len(self.blocks) != len(self.row_keys) * BLOCKS_PER_ROW
            or self.sample_count_per_row != SAMPLE_COUNT_PER_ROW
            or self.exact_probabilities_embedded is not False
        ):
            raise SampleTaxOperatorInvariantViolation(
                "target subset role or coverage changed"
            )
        expected_order: list[tuple[str, int]] = []
        for codebook in self.codebooks:
            previous: str | None = None
            row_blocks = tuple(
                item
                for item in self.blocks
                if item.catalogue_row_id == codebook.catalogue_row_id
            )
            if len(row_blocks) != BLOCKS_PER_ROW:
                raise SampleTaxOperatorInvariantViolation(
                    "target subset row block coverage changed"
                )
            for index, block in enumerate(row_blocks):
                if (
                    block.context_id != self.context.context_id
                    or block.codebook_id != codebook.codebook_id
                    or block.block_index != index
                    or block.previous_block_id != previous
                ):
                    raise SampleTaxOperatorInvariantViolation(
                        "target subset block chain changed"
                    )
                previous = block.block_id
                expected_order.append(
                    (codebook.catalogue_row_id, index)
                )
        if tuple(
            (item.catalogue_row_id, item.block_index)
            for item in self.blocks
        ) != tuple(expected_order):
            raise SampleTaxOperatorInvariantViolation(
                "target subset canonical block order changed"
            )

    @property
    def total_draw_count(self) -> int:
        return len(self.row_keys) * self.sample_count_per_row

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_target_subset_log.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "context": self.context.to_document(),
            "parent_adaptive_evidence_id": (
                self.parent_adaptive_evidence_id
            ),
            "parent_log_id": self.parent_log_id,
            "role": self.role,
            "row_keys": list(self.row_keys),
            "codebooks": [item.to_document() for item in self.codebooks],
            "blocks": [item.to_document() for item in self.blocks],
            "sample_count_per_row": self.sample_count_per_row,
            "total_draw_count": self.total_draw_count,
            "exact_probabilities_embedded": (
                self.exact_probabilities_embedded
            ),
        }

    @property
    def log_id(self) -> str:
        return _content_id("target_subset_log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "log_id": self.log_id}


def _extract_target_subset_log_v1(
    preregistration: SampleTaxPreregistrationV1,
    item: matched.MatchedAdaptiveContextEvidenceV1,
    role: str,
    row_keys: tuple[str, ...],
) -> TargetSubsetLogV1:
    codebook_by_key = {
        codebook.row_key: codebook
        for codebook in item.adaptive_log.codebooks
    }
    codebooks = tuple(codebook_by_key[key] for key in row_keys)
    blocks = tuple(
        block
        for codebook in codebooks
        for block in item.adaptive_log.blocks
        if block.catalogue_row_id == codebook.catalogue_row_id
    )
    return TargetSubsetLogV1(
        preregistration.preregistration_id,
        item.context,
        item.evidence_id,
        item.adaptive_log.log_id,
        role,
        row_keys,
        codebooks,
        blocks,
    )


@dataclass(frozen=True, slots=True)
class TargetOperatorContextEvidenceV1:
    preregistration_id: str
    context: raw.RawSafeChainStructuralContextV1
    initial_failed_proof_id: str
    source_prior_id: str
    prefix_log: TargetSubsetLogV1

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.preregistration_id, "target context preregistration"),
            (self.initial_failed_proof_id, "target failed proof"),
            (self.source_prior_id, "target source prior"),
        ):
            _cid(value, field_name)
        if (
            type(self.context) is not raw.RawSafeChainStructuralContextV1
            or type(self.prefix_log) is not TargetSubsetLogV1
            or self.prefix_log.context.context_id != self.context.context_id
            or self.prefix_log.role != "operator_prefix"
            or self.prefix_log.row_keys != PROPOSAL_PREFIX
        ):
            raise SampleTaxOperatorInvariantViolation(
                "target operator evidence changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_target_context_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "context": self.context.to_document(),
            "initial_failed_proof_id": self.initial_failed_proof_id,
            "source_prior_id": self.source_prior_id,
            "prefix_log": self.prefix_log.to_document(),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("target_context_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class TargetOperatorEvidenceBundleV1:
    preregistration_id: str
    source_prior_id: str
    contexts: tuple[TargetOperatorContextEvidenceV1, ...]
    observed_rows: int = TARGET_OPERATOR_ROWS
    individual_draws: int = TARGET_OPERATOR_DRAWS
    broad_tail_rows_accessed: int = 0
    exact_probabilities_exported: bool = False

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "target evidence preregistration")
        _cid(self.source_prior_id, "target evidence source prior")
        _exact_tuple(
            self.contexts,
            TargetOperatorContextEvidenceV1,
            "target operator contexts",
        )
        if (
            len(self.contexts) != TARGET_CONTEXT_COUNT
            or len({item.context.context_id for item in self.contexts})
            != TARGET_CONTEXT_COUNT
            or any(
                item.preregistration_id != self.preregistration_id
                or item.source_prior_id != self.source_prior_id
                for item in self.contexts
            )
            or self.observed_rows != TARGET_OPERATOR_ROWS
            or self.individual_draws != TARGET_OPERATOR_DRAWS
            or self.individual_draws
            != sum(item.prefix_log.total_draw_count for item in self.contexts)
            or self.broad_tail_rows_accessed != 0
            or self.exact_probabilities_exported is not False
        ):
            raise SampleTaxOperatorInvariantViolation(
                "target operator evidence totals or access changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_target_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "source_prior_id": self.source_prior_id,
            "contexts": [item.to_document() for item in self.contexts],
            "observed_rows": self.observed_rows,
            "individual_draws": self.individual_draws,
            "broad_tail_rows_accessed": self.broad_tail_rows_accessed,
            "exact_probabilities_exported": (
                self.exact_probabilities_exported
            ),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("target_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class WrongPriorContextEvidenceV1:
    preregistration_id: str
    context: raw.RawSafeChainStructuralContextV1
    prefix_log: TargetSubsetLogV1
    fallback_log: TargetSubsetLogV1

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "wrong evidence preregistration")
        if (
            type(self.context) is not raw.RawSafeChainStructuralContextV1
            or type(self.prefix_log) is not TargetSubsetLogV1
            or type(self.fallback_log) is not TargetSubsetLogV1
            or self.prefix_log.context.context_id != self.context.context_id
            or self.fallback_log.context.context_id
            != self.context.context_id
            or self.prefix_log.role != "wrong_prefix"
            or self.prefix_log.row_keys != WRONG_PREFIX
            or self.fallback_log.role != "wrong_fallback"
            or self.fallback_log.row_keys != WRONG_FALLBACK
            or set(self.prefix_log.row_keys)
            & set(self.fallback_log.row_keys)
        ):
            raise SampleTaxOperatorInvariantViolation(
                "wrong-prior evidence/fallback split changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_wrong_context_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "context": self.context.to_document(),
            "prefix_log": self.prefix_log.to_document(),
            "fallback_log": self.fallback_log.to_document(),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("wrong_context_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class WrongPriorEvidenceBundleV1:
    preregistration_id: str
    contexts: tuple[WrongPriorContextEvidenceV1, ...]
    prefix_rows: int = TARGET_CONTEXT_COUNT * len(WRONG_PREFIX)
    fallback_rows: int = TARGET_CONTEXT_COUNT * len(WRONG_FALLBACK)
    total_individual_draws: int = TARGET_CONTROL_DRAWS

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "wrong bundle preregistration")
        _exact_tuple(
            self.contexts,
            WrongPriorContextEvidenceV1,
            "wrong-prior contexts",
        )
        if (
            len(self.contexts) != TARGET_CONTEXT_COUNT
            or self.prefix_rows != 6
            or self.fallback_rows != 3
            or self.total_individual_draws != TARGET_CONTROL_DRAWS
            or self.total_individual_draws
            != sum(
                item.prefix_log.total_draw_count
                + item.fallback_log.total_draw_count
                for item in self.contexts
            )
        ):
            raise SampleTaxOperatorInvariantViolation(
                "wrong-prior bundle counts changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_wrong_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "contexts": [item.to_document() for item in self.contexts],
            "prefix_rows": self.prefix_rows,
            "fallback_rows": self.fallback_rows,
            "total_individual_draws": self.total_individual_draws,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("wrong_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


def acquire_target_operator_evidence_v1(
    preregistration: SampleTaxPreregistrationV1,
    source_prior: SourceFrozenPriorV1,
    baseline_evidence: matched.MatchedEvidenceBundleV1,
) -> tuple[TargetOperatorEvidenceBundleV1, WrongPriorEvidenceBundleV1]:
    """Restrict paired V0-061 target traces before production planning."""

    if (
        type(preregistration) is not SampleTaxPreregistrationV1
        or type(source_prior) is not SourceFrozenPriorV1
        or type(baseline_evidence) is not matched.MatchedEvidenceBundleV1
        or source_prior.preregistration_id
        != preregistration.preregistration_id
        or baseline_evidence.preregistration_id
        != preregistration.matched_preregistration.preregistration_id
    ):
        raise SampleTaxOperatorInvariantViolation(
            "target evidence acquisition rejects stale authorities"
        )
    target_contexts: list[TargetOperatorContextEvidenceV1] = []
    wrong_contexts: list[WrongPriorContextEvidenceV1] = []
    for item in baseline_evidence.adaptive_contexts:
        prefix = _extract_target_subset_log_v1(
            preregistration,
            item,
            "operator_prefix",
            source_prior.proposed_prefix,
        )
        target_contexts.append(
            TargetOperatorContextEvidenceV1(
                preregistration.preregistration_id,
                item.context,
                item.failed_proof.proof_id,
                source_prior.prior_id,
                prefix,
            )
        )
        wrong_contexts.append(
            WrongPriorContextEvidenceV1(
                preregistration.preregistration_id,
                item.context,
                _extract_target_subset_log_v1(
                    preregistration,
                    item,
                    "wrong_prefix",
                    WRONG_PREFIX,
                ),
                _extract_target_subset_log_v1(
                    preregistration,
                    item,
                    "wrong_fallback",
                    WRONG_FALLBACK,
                ),
            )
        )
    return (
        TargetOperatorEvidenceBundleV1(
            preregistration.preregistration_id,
            source_prior.prior_id,
            tuple(target_contexts),
        ),
        WrongPriorEvidenceBundleV1(
            preregistration.preregistration_id,
            tuple(wrong_contexts),
        ),
    )


@dataclass(frozen=True, slots=True)
class OperatorPartialModelV1:
    context: raw.RawSafeChainStructuralContextV1
    catalogue_id: str
    rows: tuple[StatisticalRowV1, ...]
    observed_row_keys: tuple[str, ...]
    evidence_log_ids: tuple[str, ...]
    exact_probabilities_used: bool = False

    def __post_init__(self) -> None:
        if type(self.context) is not raw.RawSafeChainStructuralContextV1:
            raise SampleTaxOperatorInvariantViolation(
                "operator model rejects substituted contexts"
            )
        _cid(self.catalogue_id, "operator model catalogue")
        _exact_tuple(self.rows, StatisticalRowV1, "operator model rows")
        for item in self.evidence_log_ids:
            _cid(item, "operator model evidence")
        if (
            self.catalogue_id != self.context.catalogue_id
            or tuple(item.row_key for item in self.rows)
            != raw.ALL_ROW_KEYS
            or tuple(
                item.row_key for item in self.rows if item.observed
            )
            != self.observed_row_keys
            or not set(self.observed_row_keys).issubset(SOURCE_ROW_KEYS)
            or len(self.observed_row_keys) not in (2, 3)
            or len(self.evidence_log_ids) not in (1, 2)
            or self.exact_probabilities_used is not False
        ):
            raise SampleTaxOperatorInvariantViolation(
                "operator partial-model coverage changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_partial_model.v1",
            "schema_version": SCHEMA_VERSION,
            "context": self.context.to_document(),
            "catalogue_id": self.catalogue_id,
            "rows": [item.to_document() for item in self.rows],
            "observed_row_keys": list(self.observed_row_keys),
            "evidence_log_ids": list(self.evidence_log_ids),
            "exact_probabilities_used": self.exact_probabilities_used,
            "missing_rows_explicit": True,
        }

    @property
    def model_id(self) -> str:
        return _content_id("model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}


def build_operator_partial_model_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    context: raw.RawSafeChainStructuralContextV1,
    logs: tuple[TargetSubsetLogV1, ...],
) -> OperatorPartialModelV1:
    """Build an honest target-only model. This interface has no kernel."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(context) is not raw.RawSafeChainStructuralContextV1
    ):
        raise SampleTaxOperatorInvariantViolation(
            "operator model builder rejects substituted inputs"
        )
    _exact_tuple(logs, TargetSubsetLogV1, "operator model logs")
    if (
        len(logs) not in (1, 2)
        or any(item.context.context_id != context.context_id for item in logs)
    ):
        raise SampleTaxOperatorInvariantViolation(
            "operator model log/context split changed"
        )
    observed_keys = tuple(
        key for key in SOURCE_ROW_KEYS if any(key in item.row_keys for item in logs)
    )
    if len(observed_keys) not in (2, 3):
        raise SampleTaxOperatorInvariantViolation(
            "operator model must contain a registered prefix or fallback"
        )
    row_by_key = {item.key: item for item in catalogue.rows}
    codebook_by_key: dict[str, raw.RawRowCodebookV1] = {}
    blocks_by_key: dict[str, tuple[raw.PackedRawDrawBlockV1, ...]] = {}
    log_id_by_key: dict[str, str] = {}
    for log in logs:
        for codebook in log.codebooks:
            if codebook.row_key in codebook_by_key:
                raise SampleTaxOperatorInvariantViolation(
                    "operator evidence rows overlap"
                )
            raw._validate_codebook_without_kernel(
                catalogue, context, codebook
            )
            codebook_by_key[codebook.row_key] = codebook
            blocks_by_key[codebook.row_key] = tuple(
                item
                for item in log.blocks
                if item.catalogue_row_id == codebook.catalogue_row_id
            )
            log_id_by_key[codebook.row_key] = log.log_id
    rows: list[StatisticalRowV1] = []
    for key in raw.ALL_ROW_KEYS:
        catalogue_row = row_by_key[key]
        if key in codebook_by_key:
            rows.append(
                _decode_observed_row_v1(
                    catalogue_row,
                    codebook_by_key[key],
                    blocks_by_key[key],
                    log_id_by_key[key],
                )
            )
        else:
            rows.append(
                StatisticalRowV1(
                    catalogue_row.row_id,
                    key,
                    Fraction(0),
                    Fraction(1),
                    None,
                    0,
                    (),
                )
            )
    return OperatorPartialModelV1(
        context,
        catalogue.catalogue_id,
        tuple(rows),
        observed_keys,
        tuple(item.log_id for item in logs),
    )


@dataclass(frozen=True, slots=True)
class OperatorPolicyV1:
    model_id: str
    schedule: tuple[str, str, str]
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction
    missing_row_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.model_id, "operator policy model")
        labels = {
            G2048RelativeSurvivorLabel.AWAY.value,
            G2048RelativeSurvivorLabel.TOWARD.value,
        }
        if (
            type(self.schedule) is not tuple
            or len(self.schedule) != 3
            or any(item not in labels for item in self.schedule)
            or any(
                type(item) is not Fraction
                for item in (
                    self.reward_lower,
                    self.reward_upper,
                    self.failure_lower,
                    self.failure_upper,
                )
            )
            or not 0 <= self.reward_lower <= self.reward_upper <= 1
            or not 0 <= self.failure_lower <= self.failure_upper <= 1
            or self.missing_row_keys
            != tuple(sorted(set(self.missing_row_keys)))
        ):
            raise SampleTaxOperatorInvariantViolation(
                "operator policy bounds changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_policy.v1",
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


def _extreme_v1(
    row: StatisticalRowV1,
    first_value: Fraction,
    second_value: Fraction,
    *,
    maximize: bool,
) -> Fraction:
    values = (
        row.lower * first_value + (1 - row.lower) * second_value,
        row.upper * first_value + (1 - row.upper) * second_value,
    )
    return max(values) if maximize else min(values)


def _operator_policy_bounds_v1(
    model: OperatorPartialModelV1,
    schedule: tuple[str, str, str],
) -> OperatorPolicyV1:
    rows = {item.row_key: item for item in model.rows}
    away = G2048RelativeSurvivorLabel.AWAY.value
    root_action, chain_a_action, chain_b_action = schedule
    root_key = "ROOT_AWAY" if root_action == away else "ROOT_TOWARD"
    chain_a_key = "CHAIN_A_AWAY" if chain_a_action == away else "CHAIN_A_TOWARD"
    chain_b_key = "CHAIN_B_AWAY" if chain_b_action == away else "CHAIN_B_TOWARD"
    root = rows[root_key]
    chain_a = rows[chain_a_key]
    chain_b = rows[chain_b_key]
    a_lower, a_upper = chain_a.lower, chain_a.upper
    b_lower, b_upper = chain_b.lower, chain_b.upper
    if root_key == "ROOT_AWAY":
        failure_lower = _extreme_v1(
            root, Fraction(1), b_lower, maximize=False
        )
        failure_upper = _extreme_v1(
            root, Fraction(1), b_upper, maximize=True
        )
        reward_lower = Fraction(1, 64) + _extreme_v1(
            root, Fraction(0), Fraction(1, 32), maximize=False
        )
        reward_upper = Fraction(1, 64) + _extreme_v1(
            root, Fraction(0), Fraction(1, 32), maximize=True
        )
    else:
        failure_lower = min(
            q * a + (1 - q) * b
            for q in (root.lower, root.upper)
            for a in (a_lower, a_upper)
            for b in (b_lower, b_upper)
        )
        failure_upper = max(
            q * a + (1 - q) * b
            for q in (root.lower, root.upper)
            for a in (a_lower, a_upper)
            for b in (b_lower, b_upper)
        )
        reward_lower = reward_upper = Fraction(3, 64)
    missing = tuple(
        sorted(
            item.row_key
            for item in (root, chain_a, chain_b)
            if not item.observed
        )
    )
    return OperatorPolicyV1(
        model.model_id,
        schedule,
        reward_lower,
        reward_upper,
        failure_lower,
        failure_upper,
        missing,
    )


@dataclass(frozen=True, slots=True)
class OperatorPlanProofV1:
    model_id: str
    candidate_policies: tuple[OperatorPolicyV1, ...]
    selected_policy: OperatorPolicyV1
    status: str
    delta: Fraction
    normalized_regret_upper: Fraction
    required_tail_row_keys: tuple[str, ...]
    target_confidence_lower: Fraction

    def __post_init__(self) -> None:
        _cid(self.model_id, "operator proof model")
        _exact_tuple(
            self.candidate_policies,
            OperatorPolicyV1,
            "operator proof candidates",
        )
        if type(self.selected_policy) is not OperatorPolicyV1:
            raise SampleTaxOperatorInvariantViolation(
                "operator proof rejects substituted policies"
            )
        expected_schedule = (
            G2048RelativeSurvivorLabel.TOWARD.value,
            G2048RelativeSurvivorLabel.AWAY.value,
            G2048RelativeSurvivorLabel.AWAY.value,
        )
        if (
            len(self.candidate_policies) != 8
            or tuple(item.policy_id for item in self.candidate_policies)
            != tuple(
                sorted(item.policy_id for item in self.candidate_policies)
            )
            or self.selected_policy.policy_id
            not in {item.policy_id for item in self.candidate_policies}
            or self.selected_policy.schedule != expected_schedule
            or self.delta != Fraction(1, 20)
            or self.normalized_regret_upper
            != Fraction(3, 64) - self.selected_policy.reward_lower
            or self.normalized_regret_upper != 0
            or self.target_confidence_lower
            != TARGET_OPERATOR_CONFIDENCE_LOWER
        ):
            raise SampleTaxOperatorInvariantViolation(
                "operator proof selection or calibration changed"
            )
        if self.status == raw.CERTIFIED_STATUS:
            if (
                self.selected_policy.failure_upper > self.delta
                or self.required_tail_row_keys
            ):
                raise SampleTaxOperatorInvariantViolation(
                    "operator certificate is not robust"
                )
        elif self.status == raw.FAILED_STATUS:
            if (
                self.selected_policy.failure_upper <= self.delta
                or self.required_tail_row_keys != WRONG_FALLBACK
            ):
                raise SampleTaxOperatorInvariantViolation(
                    "wrong-prior failed proof did not authorize the tail"
                )
        else:
            raise SampleTaxOperatorInvariantViolation(
                "operator proof status is unregistered"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_plan_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model_id,
            "candidate_policies": [
                item.to_document() for item in self.candidate_policies
            ],
            "selected_policy": self.selected_policy.to_document(),
            "status": self.status,
            "delta": _fdoc(self.delta),
            "normalized_regret_upper": _fdoc(
                self.normalized_regret_upper
            ),
            "required_tail_row_keys": list(
                self.required_tail_row_keys
            ),
            "target_confidence_lower": _fdoc(
                self.target_confidence_lower
            ),
            "source_prior_used_in_bounds": False,
            "target_observations_only": True,
        }

    @property
    def proof_id(self) -> str:
        return _content_id("proof", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


def solve_operator_partial_model_v1(
    model: OperatorPartialModelV1,
) -> OperatorPlanProofV1:
    if type(model) is not OperatorPartialModelV1:
        raise SampleTaxOperatorInvariantViolation(
            "operator planner rejects substituted models"
        )
    labels = (
        G2048RelativeSurvivorLabel.AWAY.value,
        G2048RelativeSurvivorLabel.TOWARD.value,
    )
    candidates = tuple(
        sorted(
            (
                _operator_policy_bounds_v1(model, schedule)
                for schedule in product(labels, repeat=3)
            ),
            key=lambda item: item.policy_id,
        )
    )
    feasible = tuple(
        item
        for item in candidates
        if item.failure_upper <= Fraction(1, 20)
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
    status = raw.CERTIFIED_STATUS if feasible else raw.FAILED_STATUS
    required = (
        ()
        if feasible
        else tuple(
            key
            for key in WRONG_FALLBACK
            if key in selected.missing_row_keys
        )
    )
    return OperatorPlanProofV1(
        model.model_id,
        candidates,
        selected,
        status,
        Fraction(1, 20),
        Fraction(3, 64) - selected.reward_lower,
        required,
        TARGET_OPERATOR_CONFIDENCE_LOWER,
    )


@dataclass(frozen=True, slots=True)
class OperatorContextResultV1:
    context: raw.RawSafeChainStructuralContextV1
    source_prior_id: str
    target_evidence_id: str
    model: OperatorPartialModelV1
    proof: OperatorPlanProofV1
    online_observed_rows: int = len(PROPOSAL_PREFIX)
    online_individual_draws: int = len(PROPOSAL_PREFIX) * SAMPLE_COUNT_PER_ROW
    fallback_rows: int = 0

    def __post_init__(self) -> None:
        _cid(self.source_prior_id, "operator context source prior")
        _cid(self.target_evidence_id, "operator context evidence")
        if (
            type(self.context) is not raw.RawSafeChainStructuralContextV1
            or type(self.model) is not OperatorPartialModelV1
            or type(self.proof) is not OperatorPlanProofV1
            or self.model.context.context_id != self.context.context_id
            or self.model.observed_row_keys != PROPOSAL_PREFIX
            or self.proof.model_id != self.model.model_id
            or self.proof.status != raw.CERTIFIED_STATUS
            or self.online_observed_rows != 2
            or self.online_individual_draws != 32_768
            or self.fallback_rows != 0
        ):
            raise SampleTaxOperatorInvariantViolation(
                "operator context result changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_context_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context": self.context.to_document(),
            "source_prior_id": self.source_prior_id,
            "target_evidence_id": self.target_evidence_id,
            "model": self.model.to_document(),
            "proof": self.proof.to_document(),
            "online_observed_rows": self.online_observed_rows,
            "online_individual_draws": self.online_individual_draws,
            "fallback_rows": self.fallback_rows,
        }

    @property
    def result_id(self) -> str:
        return _content_id("context_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class OperatorOccurrenceResultV1:
    occurrence: raw.RawContextOccurrenceV1
    context_result_id: str
    operator_model_id: str
    operator_proof_id: str
    baseline_adaptive_proof_id: str
    baseline_direct_proof_id: str
    operator_failure_upper: Fraction
    baseline_adaptive_failure_upper: Fraction
    baseline_direct_failure_upper: Fraction
    new_online_draws: int
    reused_operator_model: bool

    def __post_init__(self) -> None:
        if type(self.occurrence) is not raw.RawContextOccurrenceV1:
            raise SampleTaxOperatorInvariantViolation(
                "operator occurrence rejects substituted occurrences"
            )
        for value, field_name in (
            (self.context_result_id, "operator occurrence context result"),
            (self.operator_model_id, "operator occurrence model"),
            (self.operator_proof_id, "operator occurrence proof"),
            (
                self.baseline_adaptive_proof_id,
                "operator occurrence adaptive control",
            ),
            (
                self.baseline_direct_proof_id,
                "operator occurrence direct control",
            ),
        ):
            _cid(value, field_name)
        expected_new = (
            2 * SAMPLE_COUNT_PER_ROW
            if self.occurrence.ordinal < TARGET_CONTEXT_COUNT
            else 0
        )
        if (
            any(
                type(item) is not Fraction
                for item in (
                    self.operator_failure_upper,
                    self.baseline_adaptive_failure_upper,
                    self.baseline_direct_failure_upper,
                )
            )
            or not (
                0
                <= self.operator_failure_upper
                <= self.occurrence.delta
                and 0
                <= self.baseline_adaptive_failure_upper
                <= self.occurrence.delta
                and 0
                <= self.baseline_direct_failure_upper
                <= self.occurrence.delta
            )
            or self.new_online_draws != expected_new
            or self.reused_operator_model
            != (self.occurrence.ordinal >= TARGET_CONTEXT_COUNT)
        ):
            raise SampleTaxOperatorInvariantViolation(
                "operator occurrence bounds or reuse changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_occurrence_result.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence": self.occurrence.to_document(),
            "context_result_id": self.context_result_id,
            "operator_model_id": self.operator_model_id,
            "operator_proof_id": self.operator_proof_id,
            "baseline_adaptive_proof_id": (
                self.baseline_adaptive_proof_id
            ),
            "baseline_direct_proof_id": self.baseline_direct_proof_id,
            "operator_failure_upper": _fdoc(
                self.operator_failure_upper
            ),
            "baseline_adaptive_failure_upper": _fdoc(
                self.baseline_adaptive_failure_upper
            ),
            "baseline_direct_failure_upper": _fdoc(
                self.baseline_direct_failure_upper
            ),
            "new_online_draws": self.new_online_draws,
            "reused_operator_model": self.reused_operator_model,
        }

    @property
    def result_id(self) -> str:
        return _content_id("occurrence_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class SampleTaxWorkV1:
    offline_source_rows: int = SOURCE_TOTAL_ROWS
    offline_source_individual_draws: int = SOURCE_TOTAL_DRAWS
    offline_source_environment_interactions: int = 0
    offline_source_generative_oracle_samples: int = SOURCE_TOTAL_DRAWS
    offline_source_exact_kernel_queries: int = SOURCE_TOTAL_ROWS
    offline_source_logged_observations: int = 0
    offline_source_synthetic_model_rollouts: int = 0
    online_operator_rows: int = TARGET_OPERATOR_ROWS
    online_operator_individual_draws: int = TARGET_OPERATOR_DRAWS
    online_operator_environment_interactions: int = 0
    online_operator_generative_oracle_samples: int = TARGET_OPERATOR_DRAWS
    online_operator_exact_kernel_queries: int = TARGET_OPERATOR_ROWS
    online_operator_logged_observations: int = 0
    online_operator_synthetic_model_rollouts: int = 0
    online_no_operator_control_rows: int = TARGET_CONTROL_ROWS
    online_no_operator_control_individual_draws: int = TARGET_CONTROL_DRAWS
    no_operator_control_generative_oracle_samples: int = TARGET_CONTROL_DRAWS
    no_operator_control_exact_kernel_queries: int = TARGET_CONTROL_ROWS
    cold_direct_ground_rows: int = matched.DIRECT_TOTAL_ACTION_ROWS
    cold_direct_ground_individual_draws: int = matched.DIRECT_TOTAL_DRAWS
    cold_direct_ground_generative_oracle_samples: int = (
        matched.DIRECT_TOTAL_DRAWS
    )
    cold_direct_ground_exact_kernel_queries: int = (
        matched.DIRECT_TOTAL_ACTION_ROWS
    )
    operator_online_draw_saving: int = TARGET_ONLINE_DRAW_SAVING
    operator_online_reduction: Fraction = TARGET_ONLINE_REDUCTION
    offline_inclusive_operator_draws: int = (
        OFFLINE_INCLUSIVE_OPERATOR_DRAWS
    )
    offline_inclusive_draw_saving_observed: bool = False
    diagnostic_source_amortization_contexts: int = (
        DIAGNOSTIC_SOURCE_AMORTIZATION_CONTEXTS
    )
    target_model_reuses: int = TARGET_CONTEXT_COUNT
    operator_fallback_calls: int = 0
    registered_heldout_online_draw_reduction_observed: bool = True
    evidence_event_taxonomy_complete: bool = True
    broad_sample_efficiency_claimed: bool = False
    official_scalar_cost: None = None
    official_n_break_even: None = None

    def __post_init__(self) -> None:
        observed = tuple(
            object.__getattribute__(self, field.name)
            for field in fields(type(self))
        )
        expected = (
            9,
            147_456,
            0,
            147_456,
            9,
            0,
            0,
            6,
            98_304,
            0,
            98_304,
            6,
            0,
            0,
            9,
            147_456,
            147_456,
            9,
            198,
            4_866_048,
            4_866_048,
            198,
            49_152,
            Fraction(1, 3),
            245_760,
            False,
            9,
            3,
            0,
            True,
            True,
            False,
            None,
            None,
        )
        if observed != expected:
            raise SampleTaxOperatorInvariantViolation(
                "sample-tax work or claim locks changed"
            )

    def _payload(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema": "acfqp.sample_tax_work.v1",
            "schema_version": SCHEMA_VERSION,
        }
        for field in fields(type(self)):
            value = object.__getattribute__(self, field.name)
            document[field.name] = (
                _fdoc(value) if type(value) is Fraction else value
            )
        document.update(
            {
                "offline_source_lane": "offline_source",
                "online_target_lane": "online_target",
                "standalone_evaluation_excluded": True,
                "heterogeneous_work_not_scalarized": True,
                "diagnostic_amortization_is_not_official_break_even": True,
            }
        )
        return document

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class SampleTaxCampaignResultV1:
    preregistration: SampleTaxPreregistrationV1
    source_evidence_id: str
    source_prior: SourceFrozenPriorV1
    target_evidence_id: str
    baseline_result_id: str
    contexts: tuple[OperatorContextResultV1, ...]
    occurrences: tuple[OperatorOccurrenceResultV1, ...]
    work: SampleTaxWorkV1
    status: str = SUCCESS_STATUS
    target_confidence_lower: Fraction = TARGET_OPERATOR_CONFIDENCE_LOWER
    source_prior_only_proposes: bool = True
    target_only_certificate: bool = True
    broad_tail_available: bool = True
    registered_sample_tax_operator_claimed: bool = True
    offline_inclusive_sample_reduction_claimed: bool = False
    broad_sample_efficiency_claimed: bool = False
    automatic_coordinate_discovery_claimed: bool = False
    official_execution_allowed: bool = False
    sample_efficiency_gate_status: str = (
        "REGISTERED_INTERVENTION_GATE_PASSED_BROAD_GATE_NOT_RUN"
    )

    def __post_init__(self) -> None:
        if (
            type(self.preregistration) is not SampleTaxPreregistrationV1
            or type(self.source_prior) is not SourceFrozenPriorV1
            or type(self.work) is not SampleTaxWorkV1
        ):
            raise SampleTaxOperatorInvariantViolation(
                "sample-tax campaign rejects substituted authorities"
            )
        for value, field_name in (
            (self.source_evidence_id, "campaign source evidence"),
            (self.target_evidence_id, "campaign target evidence"),
            (self.baseline_result_id, "campaign baseline result"),
        ):
            _cid(value, field_name)
        _exact_tuple(
            self.contexts,
            OperatorContextResultV1,
            "campaign context results",
        )
        _exact_tuple(
            self.occurrences,
            OperatorOccurrenceResultV1,
            "campaign occurrence results",
        )
        context_by_id = {
            item.context.context_id: item for item in self.contexts
        }
        if (
            len(self.contexts) != TARGET_CONTEXT_COUNT
            or len(self.occurrences) != TARGET_OCCURRENCE_COUNT
            or tuple(
                item.context.context_id for item in self.contexts
            )
            != self.preregistration.target_context_ids
            or tuple(
                item.occurrence.occurrence_id
                for item in self.occurrences
            )
            != self.preregistration.target_occurrence_ids
            or any(
                item.context_result_id
                != context_by_id[item.occurrence.context_id].result_id
                or item.operator_model_id
                != context_by_id[
                    item.occurrence.context_id
                ].model.model_id
                for item in self.occurrences
            )
            or self.status != SUCCESS_STATUS
            or self.target_confidence_lower
            != TARGET_OPERATOR_CONFIDENCE_LOWER
            or self.source_prior_only_proposes is not True
            or self.target_only_certificate is not True
            or self.broad_tail_available is not True
            or self.registered_sample_tax_operator_claimed is not True
            or self.offline_inclusive_sample_reduction_claimed is not False
            or self.broad_sample_efficiency_claimed is not False
            or self.automatic_coordinate_discovery_claimed is not False
            or self.official_execution_allowed is not False
            or self.sample_efficiency_gate_status
            != "REGISTERED_INTERVENTION_GATE_PASSED_BROAD_GATE_NOT_RUN"
        ):
            raise SampleTaxOperatorInvariantViolation(
                "sample-tax campaign identity or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration": self.preregistration.to_document(),
            "source_evidence_id": self.source_evidence_id,
            "source_prior": self.source_prior.to_document(),
            "target_evidence_id": self.target_evidence_id,
            "baseline_result_id": self.baseline_result_id,
            "contexts": [item.to_document() for item in self.contexts],
            "occurrences": [
                item.to_document() for item in self.occurrences
            ],
            "work": self.work.to_document(),
            "status": self.status,
            "target_confidence_lower": _fdoc(
                self.target_confidence_lower
            ),
            "source_prior_only_proposes": self.source_prior_only_proposes,
            "target_only_certificate": self.target_only_certificate,
            "broad_tail_available": self.broad_tail_available,
            "registered_sample_tax_operator_claimed": (
                self.registered_sample_tax_operator_claimed
            ),
            "offline_inclusive_sample_reduction_claimed": (
                self.offline_inclusive_sample_reduction_claimed
            ),
            "broad_sample_efficiency_claimed": (
                self.broad_sample_efficiency_claimed
            ),
            "automatic_coordinate_discovery_claimed": (
                self.automatic_coordinate_discovery_claimed
            ),
            "official_execution_allowed": self.official_execution_allowed,
            "sample_efficiency_gate_status": (
                self.sample_efficiency_gate_status
            ),
        }

    @property
    def result_id(self) -> str:
        return _content_id("campaign", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def run_sample_tax_operator_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: SampleTaxPreregistrationV1,
    source_prior: SourceFrozenPriorV1,
    target_evidence: TargetOperatorEvidenceBundleV1,
    baseline_result: matched.MatchedEndToEndCampaignResultV1,
) -> SampleTaxCampaignResultV1:
    """Run held-out production planning without any exact kernel."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration) is not SampleTaxPreregistrationV1
        or type(source_prior) is not SourceFrozenPriorV1
        or type(target_evidence) is not TargetOperatorEvidenceBundleV1
        or type(baseline_result)
        is not matched.MatchedEndToEndCampaignResultV1
    ):
        raise SampleTaxOperatorInvariantViolation(
            "sample-tax runner rejects substituted inputs"
        )
    _validate_implementation_authority()
    expected = preregister_sample_tax_operator_v1(catalogue)
    _runtime_shape(preregistration, expected, "sample-tax preregistration")
    if preregistration.to_document() != expected.to_document():
        raise SampleTaxOperatorInvariantViolation(
            "sample-tax production preregistration mismatch"
        )
    if (
        source_prior.preregistration_id
        != preregistration.preregistration_id
        or target_evidence.preregistration_id
        != preregistration.preregistration_id
        or target_evidence.source_prior_id != source_prior.prior_id
        or baseline_result.preregistration.preregistration_id
        != preregistration.matched_preregistration.preregistration_id
    ):
        raise SampleTaxOperatorInvariantViolation(
            "sample-tax production identity chain mismatch"
        )
    contexts: list[OperatorContextResultV1] = []
    evidence_by_context = {
        item.context.context_id: item for item in target_evidence.contexts
    }
    for context in preregistration.matched_preregistration.source_preregistration.contexts:
        evidence = evidence_by_context[context.context_id]
        model = build_operator_partial_model_v1(
            catalogue, context, (evidence.prefix_log,)
        )
        proof = solve_operator_partial_model_v1(model)
        if proof.status != raw.CERTIFIED_STATUS:
            raise SampleTaxOperatorInvariantViolation(
                "registered source proposal required an unexpected fallback"
            )
        contexts.append(
            OperatorContextResultV1(
                context,
                source_prior.prior_id,
                evidence.evidence_id,
                model,
                proof,
            )
        )
    context_by_id = {
        item.context.context_id: item for item in contexts
    }
    baseline_by_occurrence = {
        item.occurrence.occurrence_id: item
        for item in baseline_result.occurrences
    }
    occurrences: list[OperatorOccurrenceResultV1] = []
    for occurrence in preregistration.matched_preregistration.source_preregistration.occurrences:
        context_result = context_by_id[occurrence.context_id]
        baseline = baseline_by_occurrence[occurrence.occurrence_id]
        occurrences.append(
            OperatorOccurrenceResultV1(
                occurrence,
                context_result.result_id,
                context_result.model.model_id,
                context_result.proof.proof_id,
                baseline.adaptive.adaptive_proof_id,
                baseline.direct.proof_id,
                context_result.proof.selected_policy.failure_upper,
                baseline.adaptive.failure_upper,
                baseline.direct.selected_policy.failure_upper,
                (
                    2 * SAMPLE_COUNT_PER_ROW
                    if occurrence.ordinal < TARGET_CONTEXT_COUNT
                    else 0
                ),
                occurrence.ordinal >= TARGET_CONTEXT_COUNT,
            )
        )
    return SampleTaxCampaignResultV1(
        preregistration,
        source_prior.source_evidence_id,
        source_prior,
        target_evidence.evidence_id,
        baseline_result.result_id,
        tuple(contexts),
        tuple(occurrences),
        SampleTaxWorkV1(),
    )


@dataclass(frozen=True, slots=True)
class WrongPriorContextResultV1:
    context: raw.RawSafeChainStructuralContextV1
    prefix_model: OperatorPartialModelV1
    failed_prefix_proof: OperatorPlanProofV1
    final_model: OperatorPartialModelV1
    final_proof: OperatorPlanProofV1
    prefix_draws: int = len(WRONG_PREFIX) * SAMPLE_COUNT_PER_ROW
    fallback_draws: int = len(WRONG_FALLBACK) * SAMPLE_COUNT_PER_ROW
    false_certificate_emitted: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.context) is not raw.RawSafeChainStructuralContextV1
            or type(self.prefix_model) is not OperatorPartialModelV1
            or type(self.failed_prefix_proof) is not OperatorPlanProofV1
            or type(self.final_model) is not OperatorPartialModelV1
            or type(self.final_proof) is not OperatorPlanProofV1
            or self.prefix_model.context.context_id
            != self.context.context_id
            or self.prefix_model.observed_row_keys != WRONG_PREFIX
            or self.failed_prefix_proof.model_id
            != self.prefix_model.model_id
            or self.failed_prefix_proof.status != raw.FAILED_STATUS
            or self.failed_prefix_proof.required_tail_row_keys
            != WRONG_FALLBACK
            or self.final_model.observed_row_keys != SOURCE_ROW_KEYS
            or self.final_proof.model_id != self.final_model.model_id
            or self.final_proof.status != raw.CERTIFIED_STATUS
            or self.prefix_draws != 32_768
            or self.fallback_draws != 16_384
            or self.false_certificate_emitted is not False
        ):
            raise SampleTaxOperatorInvariantViolation(
                "wrong-prior fail-closed path changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_wrong_context_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context": self.context.to_document(),
            "prefix_model": self.prefix_model.to_document(),
            "failed_prefix_proof": self.failed_prefix_proof.to_document(),
            "final_model": self.final_model.to_document(),
            "final_proof": self.final_proof.to_document(),
            "prefix_draws": self.prefix_draws,
            "fallback_draws": self.fallback_draws,
            "false_certificate_emitted": self.false_certificate_emitted,
        }

    @property
    def result_id(self) -> str:
        return _content_id("wrong_context_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class WrongPriorControlResultV1:
    preregistration_id: str
    evidence_id: str
    contexts: tuple[WrongPriorContextResultV1, ...]
    prefix_failures: int = TARGET_CONTEXT_COUNT
    fallback_calls: int = TARGET_CONTEXT_COUNT
    final_certificates: int = TARGET_CONTEXT_COUNT
    total_individual_draws: int = TARGET_CONTROL_DRAWS
    false_certificates: int = 0
    status: str = WRONG_PRIOR_STATUS

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "wrong result preregistration")
        _cid(self.evidence_id, "wrong result evidence")
        _exact_tuple(
            self.contexts,
            WrongPriorContextResultV1,
            "wrong-prior context results",
        )
        if (
            len(self.contexts) != TARGET_CONTEXT_COUNT
            or self.prefix_failures != 3
            or self.fallback_calls != 3
            or self.final_certificates != 3
            or self.total_individual_draws != TARGET_CONTROL_DRAWS
            or self.false_certificates != 0
            or self.status != WRONG_PRIOR_STATUS
        ):
            raise SampleTaxOperatorInvariantViolation(
                "wrong-prior control totals changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_wrong_result.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "evidence_id": self.evidence_id,
            "contexts": [item.to_document() for item in self.contexts],
            "prefix_failures": self.prefix_failures,
            "fallback_calls": self.fallback_calls,
            "final_certificates": self.final_certificates,
            "total_individual_draws": self.total_individual_draws,
            "false_certificates": self.false_certificates,
            "status": self.status,
        }

    @property
    def result_id(self) -> str:
        return _content_id("wrong_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def run_wrong_prior_control_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: SampleTaxPreregistrationV1,
    evidence: WrongPriorEvidenceBundleV1,
) -> WrongPriorControlResultV1:
    """Prove that a bad proposal cannot bypass the target certificate."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration) is not SampleTaxPreregistrationV1
        or type(evidence) is not WrongPriorEvidenceBundleV1
        or evidence.preregistration_id
        != preregistration.preregistration_id
    ):
        raise SampleTaxOperatorInvariantViolation(
            "wrong-prior runner rejects substituted inputs"
        )
    contexts: list[WrongPriorContextResultV1] = []
    for item in evidence.contexts:
        prefix_model = build_operator_partial_model_v1(
            catalogue, item.context, (item.prefix_log,)
        )
        failed = solve_operator_partial_model_v1(prefix_model)
        if failed.status != raw.FAILED_STATUS:
            raise SampleTaxOperatorInvariantViolation(
                "wrong prior unexpectedly certified before fallback"
            )
        final_model = build_operator_partial_model_v1(
            catalogue,
            item.context,
            (item.prefix_log, item.fallback_log),
        )
        final = solve_operator_partial_model_v1(final_model)
        if final.status != raw.CERTIFIED_STATUS:
            raise SampleTaxOperatorInvariantViolation(
                "wrong-prior fallback failed to recover the control"
            )
        contexts.append(
            WrongPriorContextResultV1(
                item.context,
                prefix_model,
                failed,
                final_model,
                final,
            )
        )
    return WrongPriorControlResultV1(
        preregistration.preregistration_id,
        evidence.evidence_id,
        tuple(contexts),
    )


@dataclass(frozen=True, slots=True)
class SampleTaxExactComparatorV1:
    occurrence_id: str
    context_id: str
    operator_exact_reward: Fraction
    operator_exact_failure: Fraction
    j0_exact_reward: Fraction
    j0_exact_failure: Fraction
    operator_failure_upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "sample-tax comparator occurrence")
        _cid(self.context_id, "sample-tax comparator context")
        if (
            any(
                type(item) is not Fraction
                for item in (
                    self.operator_exact_reward,
                    self.operator_exact_failure,
                    self.j0_exact_reward,
                    self.j0_exact_failure,
                    self.operator_failure_upper,
                )
            )
            or self.operator_exact_reward != self.j0_exact_reward
            or self.operator_exact_failure != self.j0_exact_failure
            or self.operator_exact_reward != Fraction(3, 64)
            or not (
                self.operator_exact_failure
                <= self.operator_failure_upper
                <= Fraction(1, 20)
            )
        ):
            raise SampleTaxOperatorInvariantViolation(
                "sample-tax exact comparator changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_exact_comparator.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "operator_exact_reward": _fdoc(
                self.operator_exact_reward
            ),
            "operator_exact_failure": _fdoc(
                self.operator_exact_failure
            ),
            "j0_exact_reward": _fdoc(self.j0_exact_reward),
            "j0_exact_failure": _fdoc(self.j0_exact_failure),
            "operator_failure_upper": _fdoc(
                self.operator_failure_upper
            ),
        }

    @property
    def comparator_id(self) -> str:
        return _content_id("comparator", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "comparator_id": self.comparator_id}


def _independent_source_uniform_v1(
    seed: str,
    context_id: str,
    row_id: str,
    sample_index: int,
) -> int:
    document = {
        "schema": "acfqp.sample_tax_source_counter_uniform.v1",
        "seed": seed,
        "context_id": context_id,
        "catalogue_row_id": row_id,
        "sample_index": sample_index,
    }
    material = (
        b"acfqp:sample-tax-source-counter-uniform:v1\x00"
        + canonical_json_bytes(document)
    )
    return int.from_bytes(hashlib.sha256(material).digest(), "big")


def _independently_replay_source_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    source_evidence: SourceEvidenceBundleV1,
    kernels: tuple[raw.RawSafeChainContextKernelV1, ...],
) -> tuple[tuple[str, ...], int]:
    failures: list[str] = []
    replayed = 0
    row_by_key = {item.key: item for item in catalogue.rows}
    kernel_by_key = {item.context_key: item for item in kernels}
    for log in source_evidence.logs:
        kernel = kernel_by_key[log.context.context_key]
        codebook_by_key = {item.row_key: item for item in log.codebooks}
        for key in SOURCE_ROW_KEYS:
            row = row_by_key[key]
            expected_codebook, weighted = raw._row_outcomes(
                catalogue, log.context, kernel, row
            )
            claimed = codebook_by_key[key]
            if claimed.to_document() != expected_codebook.to_document():
                failures.append(
                    f"SOURCE_CODEBOOK_MISMATCH:{log.context.context_key}:{key}"
                )
            probabilities = tuple(item[0] for item in weighted)
            thresholds = _integer_thresholds_v1(probabilities)
            row_blocks = tuple(
                item
                for item in log.blocks
                if item.catalogue_row_id == row.row_id
            )
            for block in row_blocks:
                expected_nibbles = "".join(
                    format(
                        _sample_index_v1(
                            thresholds,
                            _independent_source_uniform_v1(
                                block.seed,
                                log.context.context_id,
                                row.row_id,
                                sample_index,
                            ),
                        ),
                        "x",
                    )
                    for sample_index in range(
                        block.start_index,
                        block.start_index + block.draw_count,
                    )
                )
                if block.outcome_nibbles_hex != expected_nibbles:
                    failures.append(
                        f"SOURCE_DRAW_REPLAY_MISMATCH:"
                        f"{log.context.context_key}:{key}"
                    )
                replayed += block.draw_count
    if replayed != SOURCE_TOTAL_DRAWS:
        failures.append("SOURCE_DRAW_COUNT_MISMATCH")
    return tuple(sorted(set(failures))), replayed


@dataclass(frozen=True, slots=True)
class SampleTaxVerificationV1:
    claimed_result_id: str
    replay_result_id: str
    wrong_claimed_result_id: str
    wrong_replay_result_id: str
    source_evidence_id: str
    target_evidence_id: str
    baseline_verification_id: str
    failures: tuple[str, ...]
    comparators: tuple[SampleTaxExactComparatorV1, ...]
    source_draws_replayed: int
    operator_visible_target_draws: int
    unique_target_draws_replayed_by_baseline: int
    wrong_control_visible_target_draws: int
    verification_lane: str = "standalone_evaluation"
    production_kernel_access: int = 0
    broad_sample_efficiency_promotion_authorized: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.claimed_result_id, "verification claimed result"),
            (self.replay_result_id, "verification replay result"),
            (
                self.wrong_claimed_result_id,
                "verification wrong claimed result",
            ),
            (
                self.wrong_replay_result_id,
                "verification wrong replay result",
            ),
            (self.source_evidence_id, "verification source evidence"),
            (self.target_evidence_id, "verification target evidence"),
            (
                self.baseline_verification_id,
                "verification baseline verification",
            ),
        ):
            _cid(value, field_name)
        _exact_tuple(
            self.comparators,
            SampleTaxExactComparatorV1,
            "sample-tax comparators",
        )
        if (
            self.failures != tuple(sorted(set(self.failures)))
            or len(self.comparators) != TARGET_OCCURRENCE_COUNT
            or self.source_draws_replayed != SOURCE_TOTAL_DRAWS
            or self.operator_visible_target_draws != TARGET_OPERATOR_DRAWS
            or self.unique_target_draws_replayed_by_baseline
            != TARGET_CONTROL_DRAWS
            or self.wrong_control_visible_target_draws
            != TARGET_CONTROL_DRAWS
            or self.verification_lane != "standalone_evaluation"
            or self.production_kernel_access != 0
            or self.broad_sample_efficiency_promotion_authorized is not False
        ):
            raise SampleTaxOperatorInvariantViolation(
                "sample-tax verification counts or claim changed"
            )

    @property
    def verified(self) -> bool:
        return (
            not self.failures
            and self.claimed_result_id == self.replay_result_id
            and self.wrong_claimed_result_id
            == self.wrong_replay_result_id
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sample_tax_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "claimed_result_id": self.claimed_result_id,
            "replay_result_id": self.replay_result_id,
            "wrong_claimed_result_id": self.wrong_claimed_result_id,
            "wrong_replay_result_id": self.wrong_replay_result_id,
            "source_evidence_id": self.source_evidence_id,
            "target_evidence_id": self.target_evidence_id,
            "baseline_verification_id": self.baseline_verification_id,
            "failures": list(self.failures),
            "verified": self.verified,
            "comparators": [
                item.to_document() for item in self.comparators
            ],
            "source_draws_replayed": self.source_draws_replayed,
            "operator_visible_target_draws": (
                self.operator_visible_target_draws
            ),
            "unique_target_draws_replayed_by_baseline": (
                self.unique_target_draws_replayed_by_baseline
            ),
            "wrong_control_visible_target_draws": (
                self.wrong_control_visible_target_draws
            ),
            "verification_lane": self.verification_lane,
            "production_kernel_access": self.production_kernel_access,
            "broad_sample_efficiency_promotion_authorized": (
                self.broad_sample_efficiency_promotion_authorized
            ),
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_sample_tax_operator_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: SampleTaxPreregistrationV1,
    source_evidence: SourceEvidenceBundleV1,
    source_kernels: tuple[raw.RawSafeChainContextKernelV1, ...],
    target_evidence: TargetOperatorEvidenceBundleV1,
    wrong_evidence: WrongPriorEvidenceBundleV1,
    baseline_evidence: matched.MatchedEvidenceBundleV1,
    target_kernels: tuple[raw.RawSafeChainContextKernelV1, ...],
    baseline_result: matched.MatchedEndToEndCampaignResultV1,
    claimed_result: SampleTaxCampaignResultV1,
    wrong_claimed_result: WrongPriorControlResultV1,
) -> SampleTaxVerificationV1:
    """Independently replay source, paired targets, controls, exact values."""

    expected_prior = build_source_frozen_prior_v1(
        catalogue, preregistration, source_evidence
    )
    expected_target, expected_wrong_evidence = (
        acquire_target_operator_evidence_v1(
            preregistration, expected_prior, baseline_evidence
        )
    )
    expected_result = run_sample_tax_operator_v1(
        catalogue,
        preregistration,
        expected_prior,
        expected_target,
        baseline_result,
    )
    expected_wrong_result = run_wrong_prior_control_v1(
        catalogue, preregistration, expected_wrong_evidence
    )
    _runtime_shape(claimed_result, expected_result, "claimed sample-tax result")
    _runtime_shape(
        wrong_claimed_result,
        expected_wrong_result,
        "claimed wrong-prior result",
    )
    failures: list[str] = []
    if source_evidence.preregistration_id != preregistration.preregistration_id:
        failures.append("SOURCE_EVIDENCE_PREREGISTRATION_MISMATCH")
    if target_evidence.to_document() != expected_target.to_document():
        failures.append("TARGET_EVIDENCE_RECONSTRUCTION_MISMATCH")
    if wrong_evidence.to_document() != expected_wrong_evidence.to_document():
        failures.append("WRONG_EVIDENCE_RECONSTRUCTION_MISMATCH")
    if claimed_result.to_document() != expected_result.to_document():
        failures.append("SAMPLE_TAX_RESULT_RECONSTRUCTION_MISMATCH")
    if (
        wrong_claimed_result.to_document()
        != expected_wrong_result.to_document()
    ):
        failures.append("WRONG_PRIOR_RESULT_RECONSTRUCTION_MISMATCH")
    source_failures, source_draws = _independently_replay_source_v1(
        catalogue, source_evidence, source_kernels
    )
    failures.extend(source_failures)
    baseline_verification = matched.verify_matched_end_to_end_workload_v1(
        catalogue,
        preregistration.matched_preregistration,
        baseline_evidence,
        target_kernels,
        baseline_result,
    )
    if not baseline_verification.verified:
        failures.append("V0061_BASELINE_VERIFICATION_FAILED")
    result_by_occurrence = {
        item.occurrence.occurrence_id: item
        for item in claimed_result.occurrences
    }
    kernel_by_context = {
        context.context_id: kernel
        for context, kernel in zip(
            preregistration.matched_preregistration.source_preregistration.contexts,
            target_kernels,
        )
    }
    baseline_comparator_by_occurrence = {
        item.occurrence_id: item
        for item in baseline_verification.exact_comparators
    }
    comparators: list[SampleTaxExactComparatorV1] = []
    for occurrence in preregistration.matched_preregistration.source_preregistration.occurrences:
        result = result_by_occurrence[occurrence.occurrence_id]
        reward, failure = matched._evaluate_adaptive_semantic_schedule_v1(
            kernel_by_context[occurrence.context_id],
            occurrence,
            (
                G2048RelativeSurvivorLabel.TOWARD.value,
                G2048RelativeSurvivorLabel.AWAY.value,
                G2048RelativeSurvivorLabel.AWAY.value,
            ),
        )
        baseline_comparator = baseline_comparator_by_occurrence[
            occurrence.occurrence_id
        ]
        comparators.append(
            SampleTaxExactComparatorV1(
                occurrence.occurrence_id,
                occurrence.context_id,
                reward,
                failure,
                baseline_comparator.j0_exact_reward,
                baseline_comparator.j0_exact_failure,
                result.operator_failure_upper,
            )
        )
    return SampleTaxVerificationV1(
        claimed_result.result_id,
        expected_result.result_id,
        wrong_claimed_result.result_id,
        expected_wrong_result.result_id,
        source_evidence.evidence_id,
        target_evidence.evidence_id,
        baseline_verification.verification_id,
        tuple(sorted(set(failures))),
        tuple(comparators),
        source_draws,
        target_evidence.individual_draws,
        baseline_evidence.adaptive_total_draws,
        wrong_evidence.total_individual_draws,
    )


def _implementation_functions() -> tuple[Any, ...]:
    return (
        SampleTaxOperatorProfileV1,
        SourceSafeChainContextV1,
        SampleTaxPreregistrationV1,
        SourcePackedDrawBlockV1,
        SourceContextLogV1,
        SourceEvidenceBundleV1,
        StatisticalRowV1,
        SourceSubsetAssessmentV1,
        SourceFrozenPriorV1,
        TargetSubsetLogV1,
        TargetOperatorContextEvidenceV1,
        TargetOperatorEvidenceBundleV1,
        WrongPriorContextEvidenceV1,
        WrongPriorEvidenceBundleV1,
        OperatorPartialModelV1,
        OperatorPolicyV1,
        OperatorPlanProofV1,
        OperatorContextResultV1,
        OperatorOccurrenceResultV1,
        SampleTaxWorkV1,
        SampleTaxCampaignResultV1,
        WrongPriorContextResultV1,
        WrongPriorControlResultV1,
        SampleTaxExactComparatorV1,
        SampleTaxVerificationV1,
        registered_source_contexts_v1,
        registered_source_kernels_v1,
        preregister_sample_tax_operator_v1,
        _source_uniform_v1,
        _integer_thresholds_v1,
        _sample_index_v1,
        acquire_source_evidence_v1,
        _decode_observed_row_v1,
        _selected_schedule_failure_upper_v1,
        _rows_from_source_log_v1,
        build_source_frozen_prior_v1,
        _extract_target_subset_log_v1,
        acquire_target_operator_evidence_v1,
        build_operator_partial_model_v1,
        _extreme_v1,
        _operator_policy_bounds_v1,
        solve_operator_partial_model_v1,
        run_sample_tax_operator_v1,
        run_wrong_prior_control_v1,
        _independent_source_uniform_v1,
        _independently_replay_source_v1,
        verify_sample_tax_operator_v1,
    )


def _observed_implementation_sha256() -> str:
    source = "\n\n".join(
        inspect.getsource(item) for item in _implementation_functions()
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _validate_implementation_authority() -> None:
    if _observed_implementation_sha256() != IMPLEMENTATION_SHA256:
        raise SampleTaxOperatorInvariantViolation(
            "V0-062 implementation differs from its frozen authority"
        )
