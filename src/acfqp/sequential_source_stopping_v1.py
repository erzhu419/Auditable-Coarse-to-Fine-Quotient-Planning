"""Preregistered sequential stopping for the V0-062 source proposal.

V0-063 keeps the target-side certificate, no-operator baseline, cold direct
baseline, and wrong-prior fallback from V0-062.  It changes only how much
source evidence is acquired before the proposal is frozen.

The source proposal remains nonauthoritative.  A fixed proposal guard band is
evaluated after every complete source-context block.  The acquisition stops
only after at least two ordered, target-disjoint source contexts uniquely and
unanimously select the same two-row capability.  Target intervals and target
plan certificates continue to depend exclusively on target observations.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
import hashlib
import inspect
from itertools import combinations
from typing import Any, Mapping

from acfqp.domains.semantic import G2048RelativeSurvivorLabel
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
import acfqp.matched_end_to_end_workload_v1 as matched
import acfqp.raw_multicontext_acquisition_v1 as raw
import acfqp.sample_tax_operator_v1 as v62


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.27.0"
PROFILE_KEY = "g2048_preregistered_sequential_source_stopping_v0"
SUCCESS_STATUS = (
    "CERTIFIED_REGISTERED_OFFLINE_INCLUSIVE_SAMPLE_TAX_REDUCTION"
)
WRONG_PRIOR_STATUS = v62.WRONG_PRIOR_STATUS

SOURCE_DRAW_BLOCK_SIZE = v62.DRAW_BLOCK_SIZE
SOURCE_DRAWS_PER_ROW = SOURCE_DRAW_BLOCK_SIZE
SOURCE_ROWS_PER_CONTEXT = len(v62.SOURCE_ROW_KEYS)
MIN_SOURCE_CONTEXTS = 2
MAX_SOURCE_CONTEXTS = len(v62.SOURCE_CONTEXT_SPECS)
PROPOSAL_GUARD_RADIUS = Fraction(1, 64)
PROPOSAL_DELTA = Fraction(1, 20)
PROPOSAL_PREFIX = v62.PROPOSAL_PREFIX
BROAD_TAIL = v62.BROAD_TAIL

STOPPED_SOURCE_CONTEXTS = 2
STOPPED_SOURCE_ROWS = STOPPED_SOURCE_CONTEXTS * SOURCE_ROWS_PER_CONTEXT
STOPPED_SOURCE_DRAWS = STOPPED_SOURCE_ROWS * SOURCE_DRAWS_PER_ROW
TARGET_OPERATOR_ROWS = v62.TARGET_OPERATOR_ROWS
TARGET_OPERATOR_DRAWS = v62.TARGET_OPERATOR_DRAWS
TARGET_CONTROL_ROWS = v62.TARGET_CONTROL_ROWS
TARGET_CONTROL_DRAWS = v62.TARGET_CONTROL_DRAWS
COLD_DIRECT_ROWS = matched.DIRECT_TOTAL_ACTION_ROWS
COLD_DIRECT_DRAWS = matched.DIRECT_TOTAL_DRAWS

OFFLINE_INCLUSIVE_OPERATOR_DRAWS = (
    STOPPED_SOURCE_DRAWS + TARGET_OPERATOR_DRAWS
)
OFFLINE_INCLUSIVE_DRAW_SAVING = (
    TARGET_CONTROL_DRAWS - OFFLINE_INCLUSIVE_OPERATOR_DRAWS
)
OFFLINE_INCLUSIVE_REDUCTION = Fraction(
    OFFLINE_INCLUSIVE_DRAW_SAVING, TARGET_CONTROL_DRAWS
)
SOURCE_DRAW_REDUCTION_FROM_V0062 = (
    v62.SOURCE_TOTAL_DRAWS - STOPPED_SOURCE_DRAWS
)
DIAGNOSTIC_CONTEXT_BREAK_EVEN = 2

IMPLEMENTATION_SHA256 = (
    "03384f204c9f468aa447a1c7046cfaad2bfcad8d45bae89790820f876b6574bc"
)

DOMAIN_TAGS = {
    "profile": "acfqp:sequential-source-profile:v1",
    "preregistration": "acfqp:sequential-source-preregistration:v1",
    "source_log": "acfqp:sequential-source-log:v1",
    "source_assessment": "acfqp:sequential-source-assessment:v1",
    "checkpoint": "acfqp:sequential-source-checkpoint:v1",
    "source_evidence": "acfqp:sequential-source-evidence:v1",
    "source_prior": "acfqp:sequential-source-prior:v1",
    "target_evidence": "acfqp:sequential-target-evidence:v1",
    "work": "acfqp:sequential-source-work:v1",
    "campaign": "acfqp:sequential-source-campaign:v1",
    "comparator": "acfqp:sequential-source-comparator:v1",
    "verification": "acfqp:sequential-source-verification:v1",
}


class SequentialSourceStoppingInvariantViolation(ValueError):
    """A V0-063 authority, chronology, trace, or claim is inconsistent."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise SequentialSourceStoppingInvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise SequentialSourceStoppingInvariantViolation(
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
        raise SequentialSourceStoppingInvariantViolation(
            f"{field_name} rejects nested runtime substitutions"
        )
    return value


def _runtime_shape(claimed: Any, expected: Any, path: str) -> None:
    if type(claimed) is not type(expected):
        raise SequentialSourceStoppingInvariantViolation(
            f"{path} contains a nested runtime substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise SequentialSourceStoppingInvariantViolation(
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
class SequentialSourceStoppingProfileV1:
    source_row_keys: tuple[str, ...] = v62.SOURCE_ROW_KEYS
    candidate_prefix_size: int = 2
    draw_block_size: int = SOURCE_DRAW_BLOCK_SIZE
    blocks_per_context_row_before_checkpoint: int = 1
    min_source_contexts: int = MIN_SOURCE_CONTEXTS
    max_source_contexts: int = MAX_SOURCE_CONTEXTS
    proposal_guard_radius: Fraction = PROPOSAL_GUARD_RADIUS
    proposal_delta: Fraction = PROPOSAL_DELTA
    source_seed: str = "acfqp-v0062-offline-source-seed-v1"
    stopping_semantics: str = (
        "ordered_complete_context_unique_unanimous_after_minimum_v1"
    )

    def __post_init__(self) -> None:
        if (
            self.source_row_keys != v62.SOURCE_ROW_KEYS
            or self.candidate_prefix_size != 2
            or self.draw_block_size != 4_096
            or self.blocks_per_context_row_before_checkpoint != 1
            or self.min_source_contexts != 2
            or self.max_source_contexts != 3
            or self.proposal_guard_radius != Fraction(1, 64)
            or self.proposal_delta != Fraction(1, 20)
            or self.source_seed
            != "acfqp-v0062-offline-source-seed-v1"
            or self.stopping_semantics
            != "ordered_complete_context_unique_unanimous_after_minimum_v1"
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential source profile changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_source_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_row_keys": list(self.source_row_keys),
            "candidate_prefix_size": self.candidate_prefix_size,
            "draw_block_size": self.draw_block_size,
            "blocks_per_context_row_before_checkpoint": (
                self.blocks_per_context_row_before_checkpoint
            ),
            "min_source_contexts": self.min_source_contexts,
            "max_source_contexts": self.max_source_contexts,
            "proposal_guard_radius": _fdoc(self.proposal_guard_radius),
            "proposal_delta": _fdoc(self.proposal_delta),
            "source_seed": self.source_seed,
            "stopping_semantics": self.stopping_semantics,
            "guard_is_proposal_only_not_confidence_certificate": True,
            "target_only_certificate_required": True,
            "no_post_stop_source_access": True,
        }

    @property
    def profile_id(self) -> str:
        return _content_id("profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


@dataclass(frozen=True, slots=True)
class SequentialSourcePreregistrationV1:
    base_preregistration: v62.SampleTaxPreregistrationV1
    profile: SequentialSourceStoppingProfileV1
    ordered_source_contexts: tuple[v62.SourceSafeChainContextV1, ...]
    target_context_ids: tuple[str, ...]
    target_occurrence_ids: tuple[str, ...]
    prospective_source_evidence_ids_absent: bool = True
    prospective_prior_id_absent: bool = True
    prospective_target_evidence_ids_absent: bool = True
    prospective_result_ids_absent: bool = True
    offline_and_online_lanes_separate: bool = True
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.base_preregistration)
            is not v62.SampleTaxPreregistrationV1
            or type(self.profile) is not SequentialSourceStoppingProfileV1
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential preregistration rejects substituted authorities"
            )
        _exact_tuple(
            self.ordered_source_contexts,
            v62.SourceSafeChainContextV1,
            "ordered source contexts",
        )
        for value in self.target_context_ids:
            _cid(value, "sequential target context")
        for value in self.target_occurrence_ids:
            _cid(value, "sequential target occurrence")
        source_ids = {
            item.context_id for item in self.ordered_source_contexts
        }
        if (
            self.profile != SequentialSourceStoppingProfileV1()
            or self.ordered_source_contexts
            != self.base_preregistration.source_contexts
            or len(self.ordered_source_contexts) != MAX_SOURCE_CONTEXTS
            or self.target_context_ids
            != self.base_preregistration.target_context_ids
            or self.target_occurrence_ids
            != self.base_preregistration.target_occurrence_ids
            or source_ids & set(self.target_context_ids)
            or self.prospective_source_evidence_ids_absent is not True
            or self.prospective_prior_id_absent is not True
            or self.prospective_target_evidence_ids_absent is not True
            or self.prospective_result_ids_absent is not True
            or self.offline_and_online_lanes_separate is not True
            or self.official_execution_allowed is not False
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential preregistration split or chronology changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_source_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "implementation_sha256": IMPLEMENTATION_SHA256,
            "base_preregistration": (
                self.base_preregistration.to_document()
            ),
            "profile": self.profile.to_document(),
            "ordered_source_contexts": [
                item.to_document() for item in self.ordered_source_contexts
            ],
            "target_context_ids": list(self.target_context_ids),
            "target_occurrence_ids": list(self.target_occurrence_ids),
            "prospective_source_evidence_ids_absent": (
                self.prospective_source_evidence_ids_absent
            ),
            "prospective_prior_id_absent": (
                self.prospective_prior_id_absent
            ),
            "prospective_target_evidence_ids_absent": (
                self.prospective_target_evidence_ids_absent
            ),
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


def preregister_sequential_source_stopping_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
) -> SequentialSourcePreregistrationV1:
    if type(catalogue) is not raw.G2048StatisticalCatalogueV1:
        raise SequentialSourceStoppingInvariantViolation(
            "sequential preregistration rejects substituted catalogue"
        )
    base = v62.preregister_sample_tax_operator_v1(catalogue)
    return SequentialSourcePreregistrationV1(
        base,
        SequentialSourceStoppingProfileV1(),
        base.source_contexts,
        base.target_context_ids,
        base.target_occurrence_ids,
    )


@dataclass(frozen=True, slots=True)
class SequentialSourceContextLogV1:
    preregistration_id: str
    context: v62.SourceSafeChainContextV1
    context_sequence_index: int
    codebooks: tuple[raw.RawRowCodebookV1, ...]
    blocks: tuple[v62.SourcePackedDrawBlockV1, ...]
    row_keys: tuple[str, ...] = v62.SOURCE_ROW_KEYS
    sample_count_per_row: int = SOURCE_DRAWS_PER_ROW
    total_draw_count: int = SOURCE_ROWS_PER_CONTEXT * SOURCE_DRAWS_PER_ROW
    lane: str = "offline_source_sequential"
    exact_probabilities_embedded: bool = False

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "sequential source log preregistration")
        if type(self.context) is not v62.SourceSafeChainContextV1:
            raise SequentialSourceStoppingInvariantViolation(
                "sequential source log rejects substituted context"
            )
        _exact_tuple(
            self.codebooks, raw.RawRowCodebookV1, "sequential codebooks"
        )
        _exact_tuple(
            self.blocks,
            v62.SourcePackedDrawBlockV1,
            "sequential source blocks",
        )
        if (
            type(self.context_sequence_index) is not int
            or not 0 <= self.context_sequence_index < MAX_SOURCE_CONTEXTS
            or self.row_keys != v62.SOURCE_ROW_KEYS
            or tuple(item.row_key for item in self.codebooks)
            != self.row_keys
            or len(self.blocks) != SOURCE_ROWS_PER_CONTEXT
            or self.sample_count_per_row != 4_096
            or self.total_draw_count != 12_288
            or self.lane != "offline_source_sequential"
            or self.exact_probabilities_embedded is not False
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential source log coverage or lane changed"
            )
        expected_rows: list[str] = []
        for codebook, block in zip(self.codebooks, self.blocks):
            if (
                codebook.context_id != self.context.context_id
                or block.context_id != self.context.context_id
                or block.catalogue_row_id != codebook.catalogue_row_id
                or block.codebook_id != codebook.codebook_id
                or block.block_index != 0
                or block.start_index != 0
                or block.draw_count != 4_096
                or block.previous_block_id is not None
            ):
                raise SequentialSourceStoppingInvariantViolation(
                    "sequential source block/codebook binding changed"
                )
            expected_rows.append(codebook.row_key)
        if tuple(expected_rows) != self.row_keys:
            raise SequentialSourceStoppingInvariantViolation(
                "sequential source row order changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_source_log.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "context": self.context.to_document(),
            "context_sequence_index": self.context_sequence_index,
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
class SequentialSourceAssessmentV1:
    source_context_id: str
    source_log_id: str
    observed_row_keys: tuple[str, str]
    failure_upper: Fraction
    delta: Fraction = PROPOSAL_DELTA
    certifies_proposal_guard: bool = False
    proposal_only_not_target_certificate: bool = True

    def __post_init__(self) -> None:
        _cid(self.source_context_id, "sequential assessment context")
        _cid(self.source_log_id, "sequential assessment log")
        if (
            self.observed_row_keys
            not in tuple(combinations(v62.SOURCE_ROW_KEYS, 2))
            or type(self.failure_upper) is not Fraction
            or not 0 <= self.failure_upper <= 1
            or self.delta != Fraction(1, 20)
            or self.certifies_proposal_guard
            != (self.failure_upper <= self.delta)
            or self.proposal_only_not_target_certificate is not True
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential source assessment changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_source_assessment.v1",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.source_context_id,
            "source_log_id": self.source_log_id,
            "observed_row_keys": list(self.observed_row_keys),
            "failure_upper": _fdoc(self.failure_upper),
            "delta": _fdoc(self.delta),
            "certifies_proposal_guard": self.certifies_proposal_guard,
            "proposal_only_not_target_certificate": (
                self.proposal_only_not_target_certificate
            ),
        }

    @property
    def assessment_id(self) -> str:
        return _content_id("source_assessment", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "assessment_id": self.assessment_id,
        }


def _unanimous_prefixes_v1(
    context_ids: tuple[str, ...],
    assessments: tuple[SequentialSourceAssessmentV1, ...],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        subset
        for subset in combinations(v62.SOURCE_ROW_KEYS, 2)
        if all(
            any(
                item.source_context_id == context_id
                and item.observed_row_keys == subset
                and item.certifies_proposal_guard
                for item in assessments
            )
            for context_id in context_ids
        )
    )


@dataclass(frozen=True, slots=True)
class SequentialStopCheckpointV1:
    preregistration_id: str
    checkpoint_index: int
    acquired_context_ids: tuple[str, ...]
    assessments: tuple[SequentialSourceAssessmentV1, ...]
    unanimous_prefixes: tuple[tuple[str, str], ...]
    decision: str
    frozen_prefix: tuple[str, ...]
    target_evidence_ids_seen: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "sequential checkpoint preregistration")
        for value in self.acquired_context_ids:
            _cid(value, "checkpoint acquired context")
        _exact_tuple(
            self.assessments,
            SequentialSourceAssessmentV1,
            "checkpoint assessments",
        )
        if (
            type(self.checkpoint_index) is not int
            or self.checkpoint_index != len(self.acquired_context_ids)
            or self.checkpoint_index < 1
            or self.checkpoint_index > MAX_SOURCE_CONTEXTS
            or len(self.assessments)
            != self.checkpoint_index
            * len(tuple(combinations(v62.SOURCE_ROW_KEYS, 2)))
            or self.unanimous_prefixes
            != _unanimous_prefixes_v1(
                self.acquired_context_ids, self.assessments
            )
            or self.target_evidence_ids_seen != ()
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential checkpoint evidence changed"
            )
        if self.checkpoint_index < MIN_SOURCE_CONTEXTS:
            expected_decision = "CONTINUE_MIN_CONTEXTS"
            expected_prefix: tuple[str, ...] = ()
        elif len(self.unanimous_prefixes) == 1:
            expected_decision = "STOP_UNIQUE_UNANIMOUS"
            expected_prefix = self.unanimous_prefixes[0]
        elif self.checkpoint_index < MAX_SOURCE_CONTEXTS:
            expected_decision = "CONTINUE_NO_UNIQUE_UNANIMOUS"
            expected_prefix = ()
        else:
            expected_decision = "ABSTAIN_MAX_CONTEXTS"
            expected_prefix = ()
        if (
            self.decision != expected_decision
            or self.frozen_prefix != expected_prefix
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential checkpoint decision changed"
            )

    @property
    def stopped(self) -> bool:
        return self.decision == "STOP_UNIQUE_UNANIMOUS"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_source_checkpoint.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "checkpoint_index": self.checkpoint_index,
            "acquired_context_ids": list(self.acquired_context_ids),
            "assessments": [
                item.to_document() for item in self.assessments
            ],
            "unanimous_prefixes": [
                list(item) for item in self.unanimous_prefixes
            ],
            "decision": self.decision,
            "frozen_prefix": list(self.frozen_prefix),
            "target_evidence_ids_seen": list(
                self.target_evidence_ids_seen
            ),
        }

    @property
    def checkpoint_id(self) -> str:
        return _content_id("checkpoint", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "checkpoint_id": self.checkpoint_id}


@dataclass(frozen=True, slots=True)
class SequentialSourceEvidenceV1:
    preregistration_id: str
    logs: tuple[SequentialSourceContextLogV1, ...]
    checkpoints: tuple[SequentialStopCheckpointV1, ...]
    unused_source_context_ids: tuple[str, ...]
    source_rows: int = STOPPED_SOURCE_ROWS
    source_individual_draws: int = STOPPED_SOURCE_DRAWS
    source_exact_kernel_row_queries: int = STOPPED_SOURCE_ROWS
    final_decision: str = "STOP_UNIQUE_UNANIMOUS"
    target_evidence_ids_used: tuple[str, ...] = ()
    target_kernel_access: int = 0

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "sequential source evidence preregistration")
        _exact_tuple(
            self.logs,
            SequentialSourceContextLogV1,
            "sequential source logs",
        )
        _exact_tuple(
            self.checkpoints,
            SequentialStopCheckpointV1,
            "sequential source checkpoints",
        )
        for value in self.unused_source_context_ids:
            _cid(value, "unused source context")
        acquired_ids = tuple(item.context.context_id for item in self.logs)
        registered_contexts = v62.registered_source_contexts_v1(
            raw.registered_g2048_d4_statistical_catalogue_v1()
        )
        log_id_by_context = {
            item.context.context_id: item.log_id for item in self.logs
        }
        if (
            len(self.logs) != STOPPED_SOURCE_CONTEXTS
            or acquired_ids
            != tuple(
                item.context_id
                for item in registered_contexts[:STOPPED_SOURCE_CONTEXTS]
            )
            or tuple(item.context_sequence_index for item in self.logs)
            != tuple(range(STOPPED_SOURCE_CONTEXTS))
            or any(
                item.preregistration_id != self.preregistration_id
                for item in self.logs
            )
            or len(self.checkpoints) != STOPPED_SOURCE_CONTEXTS
            or tuple(item.checkpoint_index for item in self.checkpoints)
            != (1, 2)
            or any(
                item.preregistration_id != self.preregistration_id
                or item.acquired_context_ids != acquired_ids[: item.checkpoint_index]
                or any(
                    assessment.source_context_id
                    not in item.acquired_context_ids
                    or assessment.source_log_id
                    != log_id_by_context.get(
                        assessment.source_context_id
                    )
                    for assessment in item.assessments
                )
                for item in self.checkpoints
            )
            or any(item.stopped for item in self.checkpoints[:-1])
            or not self.checkpoints[-1].stopped
            or self.checkpoints[-1].frozen_prefix != PROPOSAL_PREFIX
            or self.unused_source_context_ids
            != tuple(
                item.context_id
                for item in registered_contexts[STOPPED_SOURCE_CONTEXTS:]
            )
            or self.source_rows != 6
            or self.source_individual_draws != 24_576
            or self.source_individual_draws
            != sum(item.total_draw_count for item in self.logs)
            or self.source_exact_kernel_row_queries != 6
            or self.final_decision != "STOP_UNIQUE_UNANIMOUS"
            or self.target_evidence_ids_used != ()
            or self.target_kernel_access != 0
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential source evidence chronology or totals changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_source_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "logs": [item.to_document() for item in self.logs],
            "checkpoints": [
                item.to_document() for item in self.checkpoints
            ],
            "unused_source_context_ids": list(
                self.unused_source_context_ids
            ),
            "source_rows": self.source_rows,
            "source_individual_draws": self.source_individual_draws,
            "source_exact_kernel_row_queries": (
                self.source_exact_kernel_row_queries
            ),
            "final_decision": self.final_decision,
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


def _source_log_bounds_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    log: SequentialSourceContextLogV1,
) -> dict[str, tuple[Fraction, Fraction, Fraction]]:
    """Decode one source checkpoint without a kernel or target authority."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(log) is not SequentialSourceContextLogV1
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "source checkpoint decoder rejects substituted inputs"
        )
    row_by_key = {item.key: item for item in catalogue.rows}
    result: dict[str, tuple[Fraction, Fraction, Fraction]] = {}
    for codebook, block in zip(log.codebooks, log.blocks):
        row = row_by_key[codebook.row_key]
        if (
            codebook.context_id != log.context.context_id
            or codebook.catalogue_row_id != row.row_id
            or block.codebook_id != codebook.codebook_id
            or any(
                int(character, 16) >= len(codebook.outcomes)
                for character in block.outcome_nibbles_hex
            )
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "source checkpoint codebook changed"
            )
        first_destination = row.destination_cell_ids[0]
        count = sum(
            codebook.outcomes[int(character, 16)].destination_cell_id
            == first_destination
            for character in block.outcome_nibbles_hex
        )
        empirical = Fraction(count, SOURCE_DRAWS_PER_ROW)
        result[codebook.row_key] = (
            max(Fraction(0), empirical - PROPOSAL_GUARD_RADIUS),
            min(Fraction(1), empirical + PROPOSAL_GUARD_RADIUS),
            empirical,
        )
    if tuple(result) != v62.SOURCE_ROW_KEYS:
        raise SequentialSourceStoppingInvariantViolation(
            "source checkpoint row coverage changed"
        )
    return result


def _proposal_failure_upper_v1(
    observed: Mapping[str, tuple[Fraction, Fraction, Fraction]],
    subset: tuple[str, str],
) -> Fraction:
    bounds = {
        key: (
            (observed[key][0], observed[key][1])
            if key in subset
            else (Fraction(0), Fraction(1))
        )
        for key in v62.SOURCE_ROW_KEYS
    }
    root = bounds["ROOT_TOWARD"]
    chain_a = bounds["CHAIN_A_AWAY"]
    chain_b = bounds["CHAIN_B_AWAY"]
    return max(
        root_value * a_value + (1 - root_value) * b_value
        for root_value in root
        for a_value in chain_a
        for b_value in chain_b
    )


def _assess_source_logs_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    logs: tuple[SequentialSourceContextLogV1, ...],
) -> tuple[SequentialSourceAssessmentV1, ...]:
    _exact_tuple(
        logs, SequentialSourceContextLogV1, "source assessment logs"
    )
    assessments: list[SequentialSourceAssessmentV1] = []
    for log in logs:
        observed = _source_log_bounds_v1(catalogue, log)
        for subset in combinations(v62.SOURCE_ROW_KEYS, 2):
            upper = _proposal_failure_upper_v1(observed, subset)
            assessments.append(
                SequentialSourceAssessmentV1(
                    log.context.context_id,
                    log.log_id,
                    subset,
                    upper,
                    PROPOSAL_DELTA,
                    upper <= PROPOSAL_DELTA,
                )
            )
    return tuple(assessments)


def _checkpoint_v1(
    preregistration_id: str,
    catalogue: raw.G2048StatisticalCatalogueV1,
    logs: tuple[SequentialSourceContextLogV1, ...],
) -> SequentialStopCheckpointV1:
    context_ids = tuple(item.context.context_id for item in logs)
    assessments = _assess_source_logs_v1(catalogue, logs)
    unanimous = _unanimous_prefixes_v1(context_ids, assessments)
    if len(logs) < MIN_SOURCE_CONTEXTS:
        decision = "CONTINUE_MIN_CONTEXTS"
        prefix: tuple[str, ...] = ()
    elif len(unanimous) == 1:
        decision = "STOP_UNIQUE_UNANIMOUS"
        prefix = unanimous[0]
    elif len(logs) < MAX_SOURCE_CONTEXTS:
        decision = "CONTINUE_NO_UNIQUE_UNANIMOUS"
        prefix = ()
    else:
        decision = "ABSTAIN_MAX_CONTEXTS"
        prefix = ()
    return SequentialStopCheckpointV1(
        preregistration_id,
        len(logs),
        context_ids,
        assessments,
        unanimous,
        decision,
        prefix,
    )


def acquire_sequential_source_evidence_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: SequentialSourcePreregistrationV1,
    kernels: tuple[raw.RawSafeChainContextKernelV1, ...],
) -> SequentialSourceEvidenceV1:
    """Acquire complete context blocks until the preregistered stop fires."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration) is not SequentialSourcePreregistrationV1
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "sequential source acquisition rejects substituted inputs"
        )
    _exact_tuple(
        kernels,
        raw.RawSafeChainContextKernelV1,
        "sequential source kernels",
    )
    expected = preregister_sequential_source_stopping_v1(catalogue)
    _runtime_shape(
        preregistration, expected, "sequential source preregistration"
    )
    if (
        preregistration.to_document() != expected.to_document()
        or len(kernels) != MAX_SOURCE_CONTEXTS
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "sequential source acquisition preregistration mismatch"
        )
    row_by_key = {item.key: item for item in catalogue.rows}
    logs: list[SequentialSourceContextLogV1] = []
    checkpoints: list[SequentialStopCheckpointV1] = []
    for context_index, (context, kernel) in enumerate(
        zip(preregistration.ordered_source_contexts, kernels)
    ):
        if (
            kernel.context_key != context.context_key
            or kernel.rank_one_probability
            != context.rank_one_probability
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential source kernel/context mismatch"
            )
        codebooks: list[raw.RawRowCodebookV1] = []
        blocks: list[v62.SourcePackedDrawBlockV1] = []
        for row_key in v62.SOURCE_ROW_KEYS:
            row = row_by_key[row_key]
            codebook, weighted = raw._row_outcomes(
                catalogue, context, kernel, row
            )
            thresholds = v62._integer_thresholds_v1(
                tuple(item[0] for item in weighted)
            )
            nibbles = "".join(
                format(
                    v62._sample_index_v1(
                        thresholds,
                        v62._source_uniform_v1(
                            preregistration.profile.source_seed,
                            context.context_id,
                            row.row_id,
                            sample_index,
                        ),
                    ),
                    "x",
                )
                for sample_index in range(SOURCE_DRAWS_PER_ROW)
            )
            codebooks.append(codebook)
            blocks.append(
                v62.SourcePackedDrawBlockV1(
                    context.context_id,
                    row.row_id,
                    codebook.codebook_id,
                    preregistration.profile.source_seed,
                    0,
                    0,
                    SOURCE_DRAWS_PER_ROW,
                    nibbles,
                    None,
                )
            )
        logs.append(
            SequentialSourceContextLogV1(
                preregistration.preregistration_id,
                context,
                context_index,
                tuple(codebooks),
                tuple(blocks),
            )
        )
        checkpoint = _checkpoint_v1(
            preregistration.preregistration_id,
            catalogue,
            tuple(logs),
        )
        checkpoints.append(checkpoint)
        if checkpoint.stopped:
            break
    if not checkpoints or not checkpoints[-1].stopped:
        raise SequentialSourceStoppingInvariantViolation(
            "registered sequential source schedule abstained"
        )
    return SequentialSourceEvidenceV1(
        preregistration.preregistration_id,
        tuple(logs),
        tuple(checkpoints),
        tuple(
            item.context_id
            for item in preregistration.ordered_source_contexts[len(logs):]
        ),
    )


@dataclass(frozen=True, slots=True)
class SequentialSourcePriorV1:
    preregistration_id: str
    source_evidence_id: str
    stopped_checkpoint_id: str
    acquired_source_context_ids: tuple[str, ...]
    unused_source_context_ids: tuple[str, ...]
    proposed_prefix: tuple[str, str]
    broad_tail: tuple[str, ...]
    target_context_ids_seen: tuple[str, ...] = ()
    target_evidence_ids_seen: tuple[str, ...] = ()
    target_kernel_access: int = 0
    may_narrow_target_envelopes: bool = False
    may_certify_target_plans: bool = False
    frozen_before_target_evidence: bool = True
    proposal_guard_is_confidence_certificate: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.preregistration_id, "sequential prior preregistration"),
            (self.source_evidence_id, "sequential prior source evidence"),
            (self.stopped_checkpoint_id, "sequential prior checkpoint"),
        ):
            _cid(value, field_name)
        for value in (
            *self.acquired_source_context_ids,
            *self.unused_source_context_ids,
        ):
            _cid(value, "sequential prior source context")
        if (
            len(self.acquired_source_context_ids) != 2
            or len(self.unused_source_context_ids) != 1
            or set(self.acquired_source_context_ids)
            & set(self.unused_source_context_ids)
            or self.proposed_prefix != PROPOSAL_PREFIX
            or self.broad_tail != BROAD_TAIL
            or tuple(
                key
                for key in v62.SOURCE_ROW_KEYS
                if key not in self.proposed_prefix
            )
            != self.broad_tail
            or self.target_context_ids_seen != ()
            or self.target_evidence_ids_seen != ()
            or self.target_kernel_access != 0
            or self.may_narrow_target_envelopes is not False
            or self.may_certify_target_plans is not False
            or self.frozen_before_target_evidence is not True
            or self.proposal_guard_is_confidence_certificate is not False
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential source prior authority changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_source_prior.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "source_evidence_id": self.source_evidence_id,
            "stopped_checkpoint_id": self.stopped_checkpoint_id,
            "acquired_source_context_ids": list(
                self.acquired_source_context_ids
            ),
            "unused_source_context_ids": list(
                self.unused_source_context_ids
            ),
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
            "proposal_guard_is_confidence_certificate": (
                self.proposal_guard_is_confidence_certificate
            ),
        }

    @property
    def prior_id(self) -> str:
        return _content_id("source_prior", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prior_id": self.prior_id}


def build_sequential_source_prior_v1(
    preregistration: SequentialSourcePreregistrationV1,
    source_evidence: SequentialSourceEvidenceV1,
) -> SequentialSourcePriorV1:
    """Freeze the proposal from source evidence only; no target input exists."""

    if (
        type(preregistration) is not SequentialSourcePreregistrationV1
        or type(source_evidence) is not SequentialSourceEvidenceV1
        or source_evidence.preregistration_id
        != preregistration.preregistration_id
        or source_evidence.final_decision
        != "STOP_UNIQUE_UNANIMOUS"
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "sequential prior builder rejects stale or nonstopped evidence"
        )
    stopped = source_evidence.checkpoints[-1]
    return SequentialSourcePriorV1(
        preregistration.preregistration_id,
        source_evidence.evidence_id,
        stopped.checkpoint_id,
        tuple(item.context.context_id for item in source_evidence.logs),
        source_evidence.unused_source_context_ids,
        PROPOSAL_PREFIX,
        BROAD_TAIL,
    )


def _target_subset_log_v1(
    preregistration_id: str,
    item: matched.MatchedAdaptiveContextEvidenceV1,
    role: str,
    row_keys: tuple[str, ...],
) -> v62.TargetSubsetLogV1:
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
    return v62.TargetSubsetLogV1(
        preregistration_id,
        item.context,
        item.evidence_id,
        item.adaptive_log.log_id,
        role,
        row_keys,
        codebooks,
        blocks,
    )


@dataclass(frozen=True, slots=True)
class SequentialTargetEvidenceV1:
    preregistration_id: str
    source_prior_id: str
    baseline_evidence_bundle_id: str
    operator_evidence: v62.TargetOperatorEvidenceBundleV1
    wrong_prior_evidence: v62.WrongPriorEvidenceBundleV1
    online_operator_rows: int = TARGET_OPERATOR_ROWS
    online_operator_draws: int = TARGET_OPERATOR_DRAWS
    online_no_operator_rows: int = TARGET_CONTROL_ROWS
    online_no_operator_draws: int = TARGET_CONTROL_DRAWS
    exact_probabilities_exported: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.preregistration_id, "sequential target preregistration"),
            (self.source_prior_id, "sequential target prior"),
            (
                self.baseline_evidence_bundle_id,
                "sequential target baseline evidence",
            ),
        ):
            _cid(value, field_name)
        if (
            type(self.operator_evidence)
            is not v62.TargetOperatorEvidenceBundleV1
            or type(self.wrong_prior_evidence)
            is not v62.WrongPriorEvidenceBundleV1
            or self.operator_evidence.preregistration_id
            != self.preregistration_id
            or self.operator_evidence.source_prior_id
            != self.source_prior_id
            or self.wrong_prior_evidence.preregistration_id
            != self.preregistration_id
            or self.online_operator_rows != 6
            or self.online_operator_draws != 98_304
            or self.online_operator_draws
            != self.operator_evidence.individual_draws
            or self.online_no_operator_rows != 9
            or self.online_no_operator_draws != 147_456
            or self.online_no_operator_draws
            != self.wrong_prior_evidence.total_individual_draws
            or self.exact_probabilities_exported is not False
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential target evidence identity or totals changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_target_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "source_prior_id": self.source_prior_id,
            "baseline_evidence_bundle_id": (
                self.baseline_evidence_bundle_id
            ),
            "operator_evidence": self.operator_evidence.to_document(),
            "wrong_prior_evidence": (
                self.wrong_prior_evidence.to_document()
            ),
            "online_operator_rows": self.online_operator_rows,
            "online_operator_draws": self.online_operator_draws,
            "online_no_operator_rows": self.online_no_operator_rows,
            "online_no_operator_draws": self.online_no_operator_draws,
            "exact_probabilities_exported": (
                self.exact_probabilities_exported
            ),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("target_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


def acquire_sequential_target_evidence_v1(
    preregistration: SequentialSourcePreregistrationV1,
    source_prior: SequentialSourcePriorV1,
    baseline_evidence: matched.MatchedEvidenceBundleV1,
) -> SequentialTargetEvidenceV1:
    """Expose target rows selected by the frozen proposal; no kernel input."""

    if (
        type(preregistration) is not SequentialSourcePreregistrationV1
        or type(source_prior) is not SequentialSourcePriorV1
        or type(baseline_evidence) is not matched.MatchedEvidenceBundleV1
        or source_prior.preregistration_id
        != preregistration.preregistration_id
        or baseline_evidence.preregistration_id
        != (
            preregistration.base_preregistration.matched_preregistration
            .preregistration_id
        )
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "sequential target acquisition rejects stale authorities"
        )
    operator_contexts: list[v62.TargetOperatorContextEvidenceV1] = []
    wrong_contexts: list[v62.WrongPriorContextEvidenceV1] = []
    for item in baseline_evidence.adaptive_contexts:
        operator_contexts.append(
            v62.TargetOperatorContextEvidenceV1(
                preregistration.preregistration_id,
                item.context,
                item.failed_proof.proof_id,
                source_prior.prior_id,
                _target_subset_log_v1(
                    preregistration.preregistration_id,
                    item,
                    "operator_prefix",
                    source_prior.proposed_prefix,
                ),
            )
        )
        wrong_contexts.append(
            v62.WrongPriorContextEvidenceV1(
                preregistration.preregistration_id,
                item.context,
                _target_subset_log_v1(
                    preregistration.preregistration_id,
                    item,
                    "wrong_prefix",
                    v62.WRONG_PREFIX,
                ),
                _target_subset_log_v1(
                    preregistration.preregistration_id,
                    item,
                    "wrong_fallback",
                    v62.WRONG_FALLBACK,
                ),
            )
        )
    operator = v62.TargetOperatorEvidenceBundleV1(
        preregistration.preregistration_id,
        source_prior.prior_id,
        tuple(operator_contexts),
    )
    wrong = v62.WrongPriorEvidenceBundleV1(
        preregistration.preregistration_id,
        tuple(wrong_contexts),
    )
    return SequentialTargetEvidenceV1(
        preregistration.preregistration_id,
        source_prior.prior_id,
        baseline_evidence.bundle_id,
        operator,
        wrong,
    )


@dataclass(frozen=True, slots=True)
class SequentialSampleTaxWorkV1:
    offline_source_rows: int = STOPPED_SOURCE_ROWS
    offline_source_individual_draws: int = STOPPED_SOURCE_DRAWS
    offline_source_environment_interactions: int = 0
    offline_source_generative_oracle_samples: int = STOPPED_SOURCE_DRAWS
    offline_source_exact_kernel_queries: int = STOPPED_SOURCE_ROWS
    offline_source_logged_observations: int = 0
    offline_source_synthetic_model_rollouts: int = 0
    unused_source_contexts: int = MAX_SOURCE_CONTEXTS - STOPPED_SOURCE_CONTEXTS
    v0062_fixed_source_draws: int = v62.SOURCE_TOTAL_DRAWS
    source_draw_reduction_from_v0062: int = (
        SOURCE_DRAW_REDUCTION_FROM_V0062
    )
    online_operator_rows: int = TARGET_OPERATOR_ROWS
    online_operator_individual_draws: int = TARGET_OPERATOR_DRAWS
    online_operator_environment_interactions: int = 0
    online_operator_generative_oracle_samples: int = TARGET_OPERATOR_DRAWS
    online_operator_exact_kernel_queries: int = TARGET_OPERATOR_ROWS
    online_operator_logged_observations: int = 0
    online_operator_synthetic_model_rollouts: int = 0
    online_no_operator_control_rows: int = TARGET_CONTROL_ROWS
    online_no_operator_control_individual_draws: int = TARGET_CONTROL_DRAWS
    no_operator_control_generative_oracle_samples: int = (
        TARGET_CONTROL_DRAWS
    )
    no_operator_control_exact_kernel_queries: int = TARGET_CONTROL_ROWS
    cold_direct_ground_rows: int = COLD_DIRECT_ROWS
    cold_direct_ground_individual_draws: int = COLD_DIRECT_DRAWS
    cold_direct_ground_generative_oracle_samples: int = COLD_DIRECT_DRAWS
    cold_direct_ground_exact_kernel_queries: int = COLD_DIRECT_ROWS
    offline_inclusive_operator_draws: int = (
        OFFLINE_INCLUSIVE_OPERATOR_DRAWS
    )
    offline_inclusive_draw_saving: int = OFFLINE_INCLUSIVE_DRAW_SAVING
    offline_inclusive_reduction: Fraction = OFFLINE_INCLUSIVE_REDUCTION
    diagnostic_context_break_even: int = DIAGNOSTIC_CONTEXT_BREAK_EVEN
    source_contexts_acquired: int = STOPPED_SOURCE_CONTEXTS
    target_model_reuses: int = v62.TARGET_CONTEXT_COUNT
    operator_fallback_calls: int = 0
    wrong_prior_fallback_calls: int = v62.TARGET_CONTEXT_COUNT
    evidence_event_taxonomy_complete: bool = True
    registered_offline_inclusive_draw_reduction_observed: bool = True
    broad_sample_efficiency_claimed: bool = False
    official_scalar_cost: None = None
    official_n_break_even: None = None

    def __post_init__(self) -> None:
        expected = (
            6,
            24_576,
            0,
            24_576,
            6,
            0,
            0,
            1,
            147_456,
            122_880,
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
            122_880,
            24_576,
            Fraction(1, 6),
            2,
            2,
            3,
            0,
            3,
            True,
            True,
            False,
            None,
            None,
        )
        observed = tuple(
            object.__getattribute__(self, field.name)
            for field in fields(type(self))
        )
        if observed != expected:
            raise SequentialSourceStoppingInvariantViolation(
                "sequential sample-tax work or locks changed"
            )

    def _payload(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema": "acfqp.sequential_source_work.v1",
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
                "diagnostic_break_even_is_not_official_n_break_even": True,
            }
        )
        return document

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class SequentialSampleTaxCampaignV1:
    preregistration: SequentialSourcePreregistrationV1
    source_evidence_id: str
    source_prior: SequentialSourcePriorV1
    target_evidence_id: str
    baseline_result_id: str
    contexts: tuple[v62.OperatorContextResultV1, ...]
    occurrences: tuple[v62.OperatorOccurrenceResultV1, ...]
    work: SequentialSampleTaxWorkV1
    status: str = SUCCESS_STATUS
    target_confidence_lower: Fraction = (
        v62.TARGET_OPERATOR_CONFIDENCE_LOWER
    )
    source_prior_only_proposes: bool = True
    target_only_certificate: bool = True
    sequential_source_stopping_claimed: bool = True
    registered_offline_inclusive_sample_reduction_claimed: bool = True
    broad_sample_efficiency_claimed: bool = False
    automatic_coordinate_discovery_claimed: bool = False
    official_execution_allowed: bool = False
    sample_efficiency_gate_status: str = (
        "REGISTERED_OFFLINE_INCLUSIVE_INTERVENTION_PASSED_BROAD_GATE_NOT_RUN"
    )

    def __post_init__(self) -> None:
        if (
            type(self.preregistration)
            is not SequentialSourcePreregistrationV1
            or type(self.source_prior) is not SequentialSourcePriorV1
            or type(self.work) is not SequentialSampleTaxWorkV1
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential campaign rejects substituted authorities"
            )
        for value, field_name in (
            (self.source_evidence_id, "sequential campaign source evidence"),
            (self.target_evidence_id, "sequential campaign target evidence"),
            (self.baseline_result_id, "sequential campaign baseline"),
        ):
            _cid(value, field_name)
        _exact_tuple(
            self.contexts,
            v62.OperatorContextResultV1,
            "sequential campaign contexts",
        )
        _exact_tuple(
            self.occurrences,
            v62.OperatorOccurrenceResultV1,
            "sequential campaign occurrences",
        )
        context_by_id = {
            item.context.context_id: item for item in self.contexts
        }
        if (
            self.source_evidence_id
            != self.source_prior.source_evidence_id
            or len(self.contexts) != v62.TARGET_CONTEXT_COUNT
            or tuple(item.context.context_id for item in self.contexts)
            != self.preregistration.target_context_ids
            or len(self.occurrences) != v62.TARGET_OCCURRENCE_COUNT
            or tuple(
                item.occurrence.occurrence_id
                for item in self.occurrences
            )
            != self.preregistration.target_occurrence_ids
            or any(
                item.context_result_id
                != context_by_id[item.occurrence.context_id].result_id
                for item in self.occurrences
            )
            or self.status != SUCCESS_STATUS
            or self.target_confidence_lower
            != v62.TARGET_OPERATOR_CONFIDENCE_LOWER
            or self.source_prior_only_proposes is not True
            or self.target_only_certificate is not True
            or self.sequential_source_stopping_claimed is not True
            or self.registered_offline_inclusive_sample_reduction_claimed
            is not True
            or self.broad_sample_efficiency_claimed is not False
            or self.automatic_coordinate_discovery_claimed is not False
            or self.official_execution_allowed is not False
            or self.sample_efficiency_gate_status
            != (
                "REGISTERED_OFFLINE_INCLUSIVE_INTERVENTION_"
                "PASSED_BROAD_GATE_NOT_RUN"
            )
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential campaign identity or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_source_campaign.v1",
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
            "sequential_source_stopping_claimed": (
                self.sequential_source_stopping_claimed
            ),
            "registered_offline_inclusive_sample_reduction_claimed": (
                self.registered_offline_inclusive_sample_reduction_claimed
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


def run_sequential_sample_tax_campaign_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: SequentialSourcePreregistrationV1,
    source_prior: SequentialSourcePriorV1,
    target_evidence: SequentialTargetEvidenceV1,
    baseline_result: matched.MatchedEndToEndCampaignResultV1,
) -> SequentialSampleTaxCampaignV1:
    """Run target-only planning after a source-side sequential stop."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration) is not SequentialSourcePreregistrationV1
        or type(source_prior) is not SequentialSourcePriorV1
        or type(target_evidence) is not SequentialTargetEvidenceV1
        or type(baseline_result)
        is not matched.MatchedEndToEndCampaignResultV1
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "sequential campaign runner rejects substituted inputs"
        )
    _validate_implementation_authority()
    expected = preregister_sequential_source_stopping_v1(catalogue)
    _runtime_shape(
        preregistration, expected, "sequential campaign preregistration"
    )
    if (
        preregistration.to_document() != expected.to_document()
        or source_prior.preregistration_id
        != preregistration.preregistration_id
        or target_evidence.preregistration_id
        != preregistration.preregistration_id
        or target_evidence.source_prior_id != source_prior.prior_id
        or baseline_result.preregistration.preregistration_id
        != (
            preregistration.base_preregistration.matched_preregistration
            .preregistration_id
        )
        or target_evidence.baseline_evidence_bundle_id
        != baseline_result.evidence_bundle_id
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "sequential campaign identity chain mismatch"
        )
    evidence_by_context = {
        item.context.context_id: item
        for item in target_evidence.operator_evidence.contexts
    }
    contexts: list[v62.OperatorContextResultV1] = []
    for context in (
        preregistration.base_preregistration.matched_preregistration
        .source_preregistration.contexts
    ):
        evidence = evidence_by_context[context.context_id]
        model = v62.build_operator_partial_model_v1(
            catalogue, context, (evidence.prefix_log,)
        )
        proof = v62.solve_operator_partial_model_v1(model)
        if proof.status != raw.CERTIFIED_STATUS:
            raise SequentialSourceStoppingInvariantViolation(
                "sequential proposal required an unexpected target fallback"
            )
        contexts.append(
            v62.OperatorContextResultV1(
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
    occurrences: list[v62.OperatorOccurrenceResultV1] = []
    for occurrence in (
        preregistration.base_preregistration.matched_preregistration
        .source_preregistration.occurrences
    ):
        context_result = context_by_id[occurrence.context_id]
        baseline = baseline_by_occurrence[occurrence.occurrence_id]
        occurrences.append(
            v62.OperatorOccurrenceResultV1(
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
                    2 * v62.SAMPLE_COUNT_PER_ROW
                    if occurrence.ordinal < v62.TARGET_CONTEXT_COUNT
                    else 0
                ),
                occurrence.ordinal >= v62.TARGET_CONTEXT_COUNT,
            )
        )
    return SequentialSampleTaxCampaignV1(
        preregistration,
        source_prior.source_evidence_id,
        source_prior,
        target_evidence.evidence_id,
        baseline_result.result_id,
        tuple(contexts),
        tuple(occurrences),
        SequentialSampleTaxWorkV1(),
    )


def run_sequential_wrong_prior_control_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: SequentialSourcePreregistrationV1,
    target_evidence: SequentialTargetEvidenceV1,
) -> v62.WrongPriorControlResultV1:
    """Re-run the V0-062 bad-prefix/fallback control under V0-063 IDs."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration) is not SequentialSourcePreregistrationV1
        or type(target_evidence) is not SequentialTargetEvidenceV1
        or target_evidence.preregistration_id
        != preregistration.preregistration_id
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "sequential wrong-prior runner rejects substituted inputs"
        )
    contexts: list[v62.WrongPriorContextResultV1] = []
    for item in target_evidence.wrong_prior_evidence.contexts:
        prefix_model = v62.build_operator_partial_model_v1(
            catalogue, item.context, (item.prefix_log,)
        )
        failed = v62.solve_operator_partial_model_v1(prefix_model)
        if failed.status != raw.FAILED_STATUS:
            raise SequentialSourceStoppingInvariantViolation(
                "wrong source prior certified before target fallback"
            )
        final_model = v62.build_operator_partial_model_v1(
            catalogue,
            item.context,
            (item.prefix_log, item.fallback_log),
        )
        final = v62.solve_operator_partial_model_v1(final_model)
        if final.status != raw.CERTIFIED_STATUS:
            raise SequentialSourceStoppingInvariantViolation(
                "wrong source prior fallback did not recover"
            )
        contexts.append(
            v62.WrongPriorContextResultV1(
                item.context,
                prefix_model,
                failed,
                final_model,
                final,
            )
        )
    return v62.WrongPriorControlResultV1(
        preregistration.preregistration_id,
        target_evidence.wrong_prior_evidence.evidence_id,
        tuple(contexts),
    )


@dataclass(frozen=True, slots=True)
class SequentialExactComparatorV1:
    occurrence_id: str
    context_id: str
    operator_exact_reward: Fraction
    operator_exact_failure: Fraction
    j0_exact_reward: Fraction
    j0_exact_failure: Fraction
    operator_failure_upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "sequential comparator occurrence")
        _cid(self.context_id, "sequential comparator context")
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
            raise SequentialSourceStoppingInvariantViolation(
                "sequential exact comparator changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sequential_source_comparator.v1",
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


def _independent_thresholds_v1(
    probabilities: tuple[Fraction, ...],
) -> tuple[int, ...]:
    if (
        not probabilities
        or any(type(item) is not Fraction or item < 0 for item in probabilities)
        or sum(probabilities, Fraction(0)) != 1
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "independent source probabilities are invalid"
        )
    scale = 1 << 256
    cumulative = Fraction(0)
    result: list[int] = []
    for probability in probabilities:
        cumulative += probability
        result.append(
            (
                cumulative.numerator * scale
                + cumulative.denominator
                - 1
            )
            // cumulative.denominator
        )
    result[-1] = scale
    return tuple(result)


def _independent_sample_index_v1(
    thresholds: tuple[int, ...], uniform: int
) -> int:
    for index, threshold in enumerate(thresholds):
        if uniform < threshold:
            return index
    raise SequentialSourceStoppingInvariantViolation(
        "independent source uniform escaped CDF"
    )


def _independently_replay_sequential_source_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    source_evidence: SequentialSourceEvidenceV1,
    kernels: tuple[raw.RawSafeChainContextKernelV1, ...],
) -> tuple[tuple[str, ...], int, int]:
    failures: list[str] = []
    replayed_draws = 0
    replayed_rows = 0
    row_by_key = {item.key: item for item in catalogue.rows}
    kernel_by_key = {item.context_key: item for item in kernels}
    for log in source_evidence.logs:
        kernel = kernel_by_key[log.context.context_key]
        codebook_by_key = {item.row_key: item for item in log.codebooks}
        block_by_row = {
            codebook.row_key: next(
                item
                for item in log.blocks
                if item.catalogue_row_id == codebook.catalogue_row_id
            )
            for codebook in log.codebooks
        }
        for key in v62.SOURCE_ROW_KEYS:
            row = row_by_key[key]
            expected_codebook, weighted = raw._row_outcomes(
                catalogue, log.context, kernel, row
            )
            claimed_codebook = codebook_by_key[key]
            if (
                claimed_codebook.to_document()
                != expected_codebook.to_document()
            ):
                failures.append(
                    f"SOURCE_CODEBOOK_MISMATCH:"
                    f"{log.context.context_key}:{key}"
                )
            thresholds = _independent_thresholds_v1(
                tuple(item[0] for item in weighted)
            )
            block = block_by_row[key]
            expected_nibbles = "".join(
                format(
                    _independent_sample_index_v1(
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
            replayed_draws += block.draw_count
            replayed_rows += 1
    if replayed_draws != STOPPED_SOURCE_DRAWS:
        failures.append("SOURCE_DRAW_COUNT_MISMATCH")
    if replayed_rows != STOPPED_SOURCE_ROWS:
        failures.append("SOURCE_ROW_COUNT_MISMATCH")
    if {
        item.context.context_id for item in source_evidence.logs
    } & set(source_evidence.unused_source_context_ids):
        failures.append("POST_STOP_SOURCE_CONTEXT_REPLAYED")
    return tuple(sorted(set(failures))), replayed_draws, replayed_rows


@dataclass(frozen=True, slots=True)
class SequentialSampleTaxVerificationV1:
    claimed_result_id: str
    replay_result_id: str
    wrong_claimed_result_id: str
    wrong_replay_result_id: str
    source_evidence_id: str
    target_evidence_id: str
    baseline_verification_id: str
    failures: tuple[str, ...]
    comparators: tuple[SequentialExactComparatorV1, ...]
    source_draws_replayed: int
    source_rows_replayed: int
    operator_visible_target_draws: int
    unique_target_draws_replayed_by_baseline: int
    wrong_control_visible_target_draws: int
    verification_lane: str = "standalone_evaluation"
    production_kernel_access: int = 0
    broad_sample_efficiency_promotion_authorized: bool = False
    official_execution_authorized: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.claimed_result_id, "sequential verification claimed result"),
            (self.replay_result_id, "sequential verification replay result"),
            (
                self.wrong_claimed_result_id,
                "sequential verification wrong claimed",
            ),
            (
                self.wrong_replay_result_id,
                "sequential verification wrong replay",
            ),
            (self.source_evidence_id, "sequential verification source"),
            (self.target_evidence_id, "sequential verification target"),
            (
                self.baseline_verification_id,
                "sequential verification baseline",
            ),
        ):
            _cid(value, field_name)
        _exact_tuple(
            self.comparators,
            SequentialExactComparatorV1,
            "sequential verification comparators",
        )
        if (
            self.failures != tuple(sorted(set(self.failures)))
            or len(self.comparators) != v62.TARGET_OCCURRENCE_COUNT
            or self.source_draws_replayed != 24_576
            or self.source_rows_replayed != 6
            or self.operator_visible_target_draws != 98_304
            or self.unique_target_draws_replayed_by_baseline != 147_456
            or self.wrong_control_visible_target_draws != 147_456
            or self.verification_lane != "standalone_evaluation"
            or self.production_kernel_access != 0
            or self.broad_sample_efficiency_promotion_authorized is not False
            or self.official_execution_authorized is not False
        ):
            raise SequentialSourceStoppingInvariantViolation(
                "sequential verification work or claim changed"
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
            "schema": "acfqp.sequential_source_verification.v1",
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
            "source_rows_replayed": self.source_rows_replayed,
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
            "official_execution_authorized": (
                self.official_execution_authorized
            ),
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_sequential_sample_tax_campaign_v1(
    catalogue: raw.G2048StatisticalCatalogueV1,
    preregistration: SequentialSourcePreregistrationV1,
    source_evidence: SequentialSourceEvidenceV1,
    source_kernels: tuple[raw.RawSafeChainContextKernelV1, ...],
    target_evidence: SequentialTargetEvidenceV1,
    baseline_evidence: matched.MatchedEvidenceBundleV1,
    target_kernels: tuple[raw.RawSafeChainContextKernelV1, ...],
    baseline_result: matched.MatchedEndToEndCampaignResultV1,
    claimed_result: SequentialSampleTaxCampaignV1,
    wrong_claimed_result: v62.WrongPriorControlResultV1,
) -> SequentialSampleTaxVerificationV1:
    """Replay source stopping, target production, controls, and exact J0."""

    if (
        type(catalogue) is not raw.G2048StatisticalCatalogueV1
        or type(preregistration) is not SequentialSourcePreregistrationV1
        or type(source_evidence) is not SequentialSourceEvidenceV1
        or type(target_evidence) is not SequentialTargetEvidenceV1
        or type(baseline_evidence) is not matched.MatchedEvidenceBundleV1
        or type(baseline_result)
        is not matched.MatchedEndToEndCampaignResultV1
        or type(claimed_result) is not SequentialSampleTaxCampaignV1
        or type(wrong_claimed_result)
        is not v62.WrongPriorControlResultV1
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "sequential verifier rejects substituted inputs"
        )
    _exact_tuple(
        source_kernels,
        raw.RawSafeChainContextKernelV1,
        "sequential verification source kernels",
    )
    _exact_tuple(
        target_kernels,
        raw.RawSafeChainContextKernelV1,
        "sequential verification target kernels",
    )
    if (
        len(source_kernels) != MAX_SOURCE_CONTEXTS
        or len(target_kernels) != v62.TARGET_CONTEXT_COUNT
    ):
        raise SequentialSourceStoppingInvariantViolation(
            "sequential verifier kernel coverage changed"
        )
    _validate_implementation_authority()
    expected_source = acquire_sequential_source_evidence_v1(
        catalogue, preregistration, source_kernels
    )
    expected_prior = build_sequential_source_prior_v1(
        preregistration, expected_source
    )
    expected_target = acquire_sequential_target_evidence_v1(
        preregistration, expected_prior, baseline_evidence
    )
    expected_result = run_sequential_sample_tax_campaign_v1(
        catalogue,
        preregistration,
        expected_prior,
        expected_target,
        baseline_result,
    )
    expected_wrong = run_sequential_wrong_prior_control_v1(
        catalogue, preregistration, expected_target
    )
    _runtime_shape(
        source_evidence, expected_source, "claimed sequential source evidence"
    )
    _runtime_shape(
        target_evidence, expected_target, "claimed sequential target evidence"
    )
    _runtime_shape(
        claimed_result, expected_result, "claimed sequential campaign"
    )
    _runtime_shape(
        wrong_claimed_result,
        expected_wrong,
        "claimed sequential wrong-prior control",
    )
    failures: list[str] = []
    if source_evidence.to_document() != expected_source.to_document():
        failures.append("SOURCE_STOPPING_RECONSTRUCTION_MISMATCH")
    if target_evidence.to_document() != expected_target.to_document():
        failures.append("TARGET_EVIDENCE_RECONSTRUCTION_MISMATCH")
    if claimed_result.to_document() != expected_result.to_document():
        failures.append("SEQUENTIAL_CAMPAIGN_RECONSTRUCTION_MISMATCH")
    if wrong_claimed_result.to_document() != expected_wrong.to_document():
        failures.append("WRONG_PRIOR_RECONSTRUCTION_MISMATCH")
    source_failures, source_draws, source_rows = (
        _independently_replay_sequential_source_v1(
            catalogue, source_evidence, source_kernels
        )
    )
    failures.extend(source_failures)
    baseline_verification = matched.verify_matched_end_to_end_workload_v1(
        catalogue,
        preregistration.base_preregistration.matched_preregistration,
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
            preregistration.base_preregistration.matched_preregistration
            .source_preregistration.contexts,
            target_kernels,
        )
    }
    baseline_comparator_by_occurrence = {
        item.occurrence_id: item
        for item in baseline_verification.exact_comparators
    }
    comparators: list[SequentialExactComparatorV1] = []
    for occurrence in (
        preregistration.base_preregistration.matched_preregistration
        .source_preregistration.occurrences
    ):
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
            SequentialExactComparatorV1(
                occurrence.occurrence_id,
                occurrence.context_id,
                reward,
                failure,
                baseline_comparator.j0_exact_reward,
                baseline_comparator.j0_exact_failure,
                result.operator_failure_upper,
            )
        )
    return SequentialSampleTaxVerificationV1(
        claimed_result.result_id,
        expected_result.result_id,
        wrong_claimed_result.result_id,
        expected_wrong.result_id,
        source_evidence.evidence_id,
        target_evidence.evidence_id,
        baseline_verification.verification_id,
        tuple(sorted(set(failures))),
        tuple(comparators),
        source_draws,
        source_rows,
        target_evidence.online_operator_draws,
        baseline_evidence.adaptive_total_draws,
        target_evidence.wrong_prior_evidence.total_individual_draws,
    )


def _implementation_functions() -> tuple[Any, ...]:
    return (
        SequentialSourceStoppingProfileV1,
        SequentialSourcePreregistrationV1,
        SequentialSourceContextLogV1,
        SequentialSourceAssessmentV1,
        SequentialStopCheckpointV1,
        SequentialSourceEvidenceV1,
        SequentialSourcePriorV1,
        SequentialTargetEvidenceV1,
        SequentialSampleTaxWorkV1,
        SequentialSampleTaxCampaignV1,
        SequentialExactComparatorV1,
        SequentialSampleTaxVerificationV1,
        preregister_sequential_source_stopping_v1,
        _source_log_bounds_v1,
        _proposal_failure_upper_v1,
        _assess_source_logs_v1,
        _checkpoint_v1,
        acquire_sequential_source_evidence_v1,
        build_sequential_source_prior_v1,
        _target_subset_log_v1,
        acquire_sequential_target_evidence_v1,
        run_sequential_sample_tax_campaign_v1,
        run_sequential_wrong_prior_control_v1,
        _independent_source_uniform_v1,
        _independent_thresholds_v1,
        _independent_sample_index_v1,
        _independently_replay_sequential_source_v1,
        verify_sequential_sample_tax_campaign_v1,
    )


def _observed_implementation_sha256() -> str:
    source = "\n\n".join(
        inspect.getsource(item) for item in _implementation_functions()
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _validate_implementation_authority() -> None:
    if _observed_implementation_sha256() != IMPLEMENTATION_SHA256:
        raise SequentialSourceStoppingInvariantViolation(
            "V0-063 implementation differs from its frozen authority"
        )
