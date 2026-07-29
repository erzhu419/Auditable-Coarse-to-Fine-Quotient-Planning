"""Development-only V0-073 VOI-to-materialization adaptive control.

Three arms consume prefixes of the same immutable target streams under the
same target-local anytime confidence contract:

* a preregistered fixed H1-then-H2 order;
* target-only certificate-boundary VOI; and
* the same target-only VOI multiplied only at the final proposal layer by the
  frozen source-disjoint prior.

Every decision freezes before its selected raw suffix is read.  Confidence
rows are rebuilt from exact target-prefix counts with the existing
time-uniform Bernoulli authority.  Unexecuted blocks consume and charge zero
draws.  This module is a development control, not registered evidence and not
a sample-saving claim.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import hashlib
import math
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import sequential_bernoulli_acquisition_v1 as sequential
from acfqp import v073_certificate_boundary_voi_v1 as voi


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.38.0"
PROFILE_KEY = "v073_development_anytime_voi_adaptive_acquisition_v1"

REGISTERED_EXECUTION_ALLOWED = False
REGISTERED_TARGET_EVIDENCE = False
SAMPLE_SAVING_CLAIMED = False
SAMPLE_EFFICIENCY_GATE_STATUS = "NOT_RUN"
INDEPENDENT_VERIFIER_SCOPE = (
    "CONTROLLER_STREAM_ACCOUNTING_IDENTITY_AND_STOPPING_REIMPLEMENTATION"
)
PLANNER_REPLAY_BOUNDARY = (
    "REUSES_PARTIAL_SUPPORT_ROBUST_PLANNER_V1_AS_MATHEMATICAL_AUTHORITY"
)

INITIAL_DRAWS_PER_ROW = 128
BLOCK_SIZE = 2
MAX_EXECUTED_BLOCKS = 2
MAX_BLOCKS_PER_ROW = 1
COMMON_INITIAL_ACCEPTED_DRAWS = 2 * INITIAL_DRAWS_PER_ROW
FAMILY_ALPHA = Fraction(1, 100)
ROW_ALPHA = Fraction(1, 200)
RISK_TOLERANCE = Fraction(87_433_963, 536_870_912)

DOMAIN_TAGS = {
    "stream": "acfqp:v073-development-shared-target-row-stream:v1",
    "schedule": "acfqp:v073-anytime-block-schedule-profile:v1",
    "prefix": "acfqp:v073-target-row-prefix-checkpoint:v1",
    "epoch": "acfqp:v073-anytime-adaptive-model-epoch:v1",
    "decision": "acfqp:v073-pre-materialization-voi-decision:v1",
    "block": "acfqp:v073-executed-anytime-target-block:v1",
    "run": "acfqp:v073-anytime-adaptive-arm-run:v1",
    "control": "acfqp:v073-anytime-three-arm-control:v1",
}


class V073AnytimeAdaptiveAcquisitionInvariantViolation(ValueError):
    """A stream, decision, block, epoch, or stopping claim is invalid."""


class RegisteredV073AnytimeAdaptiveAcquisitionLocked(RuntimeError):
    """Registered execution remains unavailable."""


class DevelopmentAnytimeArmV1(str, Enum):
    FIXED_H1_THEN_H2 = "FIXED_H1_THEN_H2"
    TARGET_ONLY_VOI = "TARGET_ONLY_VOI"
    SOURCE_WEIGHTED_VOI = "SOURCE_WEIGHTED_VOI"


class DevelopmentBlockStopReasonV1(str, Enum):
    CONTINUE_FAILED_PROOF = "CONTINUE_FAILED_PROOF"
    CERTIFIED_AFTER_BLOCK = "CERTIFIED_AFTER_BLOCK"


class DevelopmentRunTerminalCodeV1(str, Enum):
    PLAN_CERTIFIED = "PLAN_CERTIFIED"
    BLOCK_BUDGET_EXHAUSTED_NONCERTIFICATE = (
        "BLOCK_BUDGET_EXHAUSTED_NONCERTIFICATE"
    )


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
            "development arithmetic must remain exact"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _pack_bool(values: tuple[bool, ...]) -> bytes:
    output = bytearray(math.ceil(len(values) / 8))
    for index, value in enumerate(values):
        if type(value) is not bool:
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "raw target stream contains a non-boolean outcome"
            )
        if value:
            output[index // 8] |= 1 << (index % 8)
    return bytes(output)


@dataclass(frozen=True, slots=True)
class DevelopmentSharedTargetRowStreamV1:
    context_id: str
    remaining_horizon: int
    outcomes: tuple[bool, ...]
    initial_draw_count: int = INITIAL_DRAWS_PER_ROW
    source_inputs: tuple[str, ...] = ()
    registered_target_evidence: bool = False

    def __post_init__(self) -> None:
        _cid(self.context_id, "shared stream context")
        if (
            self.remaining_horizon not in (1, 2)
            or type(self.outcomes) is not tuple
            or len(self.outcomes)
            != INITIAL_DRAWS_PER_ROW + BLOCK_SIZE
            or any(type(item) is not bool for item in self.outcomes)
            or self.initial_draw_count != INITIAL_DRAWS_PER_ROW
            or self.source_inputs != ()
            or self.registered_target_evidence is not False
        ):
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "shared target stream shape or evidence scope is invalid"
            )

    @property
    def packed_outcomes(self) -> bytes:
        return _pack_bool(self.outcomes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_development_shared_target_row_stream.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "remaining_horizon": self.remaining_horizon,
            "outcome_count": len(self.outcomes),
            "initial_draw_count": self.initial_draw_count,
            "packed_outcomes_sha256": hashlib.sha256(
                self.packed_outcomes
            ).hexdigest(),
            "packed_outcomes_byte_count": len(self.packed_outcomes),
            "source_inputs": [],
            "development_only": True,
            "registered_target_evidence": False,
        }

    @property
    def stream_id(self) -> str:
        return _content_id("stream", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "packed_outcomes_hex": self.packed_outcomes.hex(),
            "stream_id": self.stream_id,
        }


@dataclass(frozen=True, slots=True)
class DevelopmentAnytimeBlockScheduleProfileV1:
    sequential_profile: sequential.SequentialBernoulliProfileV1
    family_alpha: Fraction = FAMILY_ALPHA
    row_alpha: Fraction = ROW_ALPHA
    row_obligation_count: int = 2
    initial_draws_per_row: int = INITIAL_DRAWS_PER_ROW
    block_size: int = BLOCK_SIZE
    max_executed_blocks: int = MAX_EXECUTED_BLOCKS
    max_blocks_per_row: int = MAX_BLOCKS_PER_ROW
    confidence_accounting: str = (
        "ROW_FAMILY_ALPHA_PREALLOCATION_AND_ONE_ALPHA_VILLE_"
        "TIME_UNIFORM_NO_CHECKPOINT_SPENDING"
    )
    stopping_rule: str = (
        "STOP_AT_FIRST_POSTBLOCK_ROBUST_PLAN_CERTIFICATE_ELSE_HARD_CAP"
    )

    def __post_init__(self) -> None:
        if (
            type(self.sequential_profile)
            is not sequential.SequentialBernoulliProfileV1
            or self.family_alpha != FAMILY_ALPHA
            or self.row_alpha != ROW_ALPHA
            or self.row_obligation_count != 2
            or self.row_alpha * self.row_obligation_count
            != self.family_alpha
            or self.sequential_profile.confidence_alpha != self.row_alpha
            or self.sequential_profile.checkpoints
            != (INITIAL_DRAWS_PER_ROW, INITIAL_DRAWS_PER_ROW + BLOCK_SIZE)
            or self.sequential_profile.target_half_width
            != Fraction(1, 1000)
            or self.sequential_profile.boundary_grid_bits != 16
            or self.initial_draws_per_row != INITIAL_DRAWS_PER_ROW
            or self.block_size != BLOCK_SIZE
            or self.max_executed_blocks != MAX_EXECUTED_BLOCKS
            or self.max_blocks_per_row != MAX_BLOCKS_PER_ROW
            or self.confidence_accounting
            != (
                "ROW_FAMILY_ALPHA_PREALLOCATION_AND_ONE_ALPHA_VILLE_"
                "TIME_UNIFORM_NO_CHECKPOINT_SPENDING"
            )
            or self.stopping_rule
            != (
                "STOP_AT_FIRST_POSTBLOCK_ROBUST_PLAN_CERTIFICATE_"
                "ELSE_HARD_CAP"
            )
        ):
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "anytime block schedule or alpha allocation changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_anytime_block_schedule_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "sequential_profile_id": self.sequential_profile.profile_id,
            "family_alpha": _fdoc(self.family_alpha),
            "row_alpha": _fdoc(self.row_alpha),
            "row_obligation_count": self.row_obligation_count,
            "initial_draws_per_row": self.initial_draws_per_row,
            "block_size": self.block_size,
            "max_executed_blocks": self.max_executed_blocks,
            "max_blocks_per_row": self.max_blocks_per_row,
            "confidence_accounting": self.confidence_accounting,
            "stopping_rule": self.stopping_rule,
            "unexecuted_blocks_charge_zero_draws": True,
        }

    @property
    def schedule_profile_id(self) -> str:
        return _content_id("schedule", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "sequential_profile": self.sequential_profile.to_document(),
            "schedule_profile_id": self.schedule_profile_id,
        }


@dataclass(frozen=True, slots=True)
class DevelopmentTargetRowPrefixV1:
    stream_id: str
    remaining_horizon: int
    prefix_draw_count: int
    success_count: int
    raw_prefix_sha256: str
    checkpoint: sequential.AnytimeBernoulliCheckpointV1
    source_inputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _cid(self.stream_id, "row prefix stream")
        if (
            self.remaining_horizon not in (1, 2)
            or self.prefix_draw_count
            not in (
                INITIAL_DRAWS_PER_ROW,
                INITIAL_DRAWS_PER_ROW + BLOCK_SIZE,
            )
            or type(self.success_count) is not int
            or not 0 <= self.success_count <= self.prefix_draw_count
            or type(self.raw_prefix_sha256) is not str
            or len(self.raw_prefix_sha256) != 64
            or type(self.checkpoint)
            is not sequential.AnytimeBernoulliCheckpointV1
            or self.checkpoint.draw_count != self.prefix_draw_count
            or self.checkpoint.success_count != self.success_count
            or self.source_inputs != ()
        ):
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "target prefix/checkpoint is malformed or source-contaminated"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_target_row_prefix_checkpoint.v1",
            "schema_version": SCHEMA_VERSION,
            "stream_id": self.stream_id,
            "remaining_horizon": self.remaining_horizon,
            "prefix_draw_count": self.prefix_draw_count,
            "success_count": self.success_count,
            "raw_prefix_sha256": self.raw_prefix_sha256,
            "checkpoint": self.checkpoint.to_document(),
            "source_inputs": [],
            "target_local_counts_only": True,
        }

    @property
    def prefix_id(self) -> str:
        return _content_id("prefix", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prefix_id": self.prefix_id}


@dataclass(frozen=True, slots=True)
class DevelopmentAnytimeAdaptiveEpochV1:
    epoch_index: int
    row_prefixes: tuple[DevelopmentTargetRowPrefixV1, ...]
    model: robust.PartialSupportIntervalModelV1
    audit: robust.RobustPlanAuditV1
    proof_dag: voi.DevelopmentFailedProofDAGV1 | None
    row_evidence: tuple[voi.CurrentRowCountEvidenceV1, ...]
    source_inputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.epoch_index) is not int
            or not 0 <= self.epoch_index <= MAX_EXECUTED_BLOCKS
            or type(self.row_prefixes) is not tuple
            or tuple(item.remaining_horizon for item in self.row_prefixes)
            != (1, 2)
            or any(
                type(item) is not DevelopmentTargetRowPrefixV1
                for item in self.row_prefixes
            )
            or type(self.model)
            is not robust.PartialSupportIntervalModelV1
            or type(self.audit) is not robust.RobustPlanAuditV1
            or self.audit.model_id != self.model.model_id
            or type(self.row_evidence) is not tuple
            or self.source_inputs != ()
        ):
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "adaptive epoch shape or model/audit binding is invalid"
            )
        if self.audit.status is robust.RobustAuditStatus.CERTIFIED:
            if self.proof_dag is not None or self.row_evidence != ():
                raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                    "certified epoch retained a failed-proof acquisition DAG"
                )
        elif (
            self.audit.status
            is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
            or type(self.proof_dag) is not voi.DevelopmentFailedProofDAGV1
            or len(self.row_evidence) != 2
            or self.proof_dag.model_id != self.model.model_id
            or self.proof_dag.audit_id != self.audit.audit_id
        ):
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "failed epoch lacks its exact current proof DAG/evidence"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_anytime_adaptive_model_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "epoch_index": self.epoch_index,
            "row_prefix_ids": [
                item.prefix_id for item in self.row_prefixes
            ],
            "model_id": self.model.model_id,
            "audit_id": self.audit.audit_id,
            "audit_status": self.audit.status.value,
            "proof_dag_id": (
                None if self.proof_dag is None else self.proof_dag.dag_id
            ),
            "row_evidence_ids": [
                item.evidence_id for item in self.row_evidence
            ],
            "source_inputs": [],
            "confidence_authority": (
                sequential.METHOD_ID
            ),
        }

    @property
    def epoch_id(self) -> str:
        return _content_id("epoch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "epoch_id": self.epoch_id}


FIXED_DECISION_EVENTS = (
    "PRE_EPOCH_BOUND",
    "FAILED_DAG_BOUND",
    "FIXED_ORDER_EVALUATED",
    "DECISION_FROZEN",
)
VOI_DECISION_EVENTS = (
    "PRE_EPOCH_BOUND",
    "FAILED_DAG_BOUND",
    "VOI_SCORE_REPLAYABLE",
    "DECISION_FROZEN",
)
POST_DECISION_EVENTS = (
    "SELECTED_RAW_SUFFIX_READ",
    "ANYTIME_CHECKPOINT_BUILT",
    "CONFIDENCE_MODEL_REBUILT",
    "ROBUST_AUDIT_REPLAYED",
)


@dataclass(frozen=True, slots=True)
class DevelopmentPreMaterializationDecisionV1:
    arm: DevelopmentAnytimeArmV1
    round_index: int
    pre_epoch_id: str
    proof_dag_id: str
    eligible_horizons: tuple[int, ...]
    exhausted_horizons: tuple[int, ...]
    selected_horizon: int
    selected_row_id: str
    selected_candidate_id: str | None
    voi_result: voi.DevelopmentCertificateBoundaryVOIResultV1 | None
    source_prior_id: str | None
    access_events: tuple[str, ...]
    target_reads_before_freeze: int = 0
    future_outcome_fields_used: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, name in (
            (self.pre_epoch_id, "decision pre-epoch"),
            (self.proof_dag_id, "decision proof DAG"),
            (self.selected_row_id, "decision selected row"),
        ):
            _cid(value, name)
        if self.selected_candidate_id is not None:
            _cid(self.selected_candidate_id, "decision selected candidate")
        if self.source_prior_id is not None:
            _cid(self.source_prior_id, "decision source prior")
        if (
            type(self.arm) is not DevelopmentAnytimeArmV1
            or type(self.round_index) is not int
            or not 1 <= self.round_index <= MAX_EXECUTED_BLOCKS
            or self.eligible_horizons
            != tuple(sorted(set(self.eligible_horizons)))
            or self.exhausted_horizons
            != tuple(sorted(set(self.exhausted_horizons)))
            or set(self.eligible_horizons) & set(self.exhausted_horizons)
            or set(self.eligible_horizons) | set(self.exhausted_horizons)
            != {1, 2}
            or self.selected_horizon not in self.eligible_horizons
            or self.target_reads_before_freeze != 0
            or self.future_outcome_fields_used != ()
        ):
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "pre-materialization decision used an invalid budget or future"
            )
        if self.arm is DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2:
            if (
                self.voi_result is not None
                or self.selected_candidate_id is not None
                or self.source_prior_id is not None
                or self.access_events != FIXED_DECISION_EVENTS
            ):
                raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                    "fixed arm contains VOI/source inputs"
                )
        else:
            if (
                type(self.voi_result)
                is not voi.DevelopmentCertificateBoundaryVOIResultV1
                or self.selected_candidate_id is None
                or self.access_events != VOI_DECISION_EVENTS
            ):
                raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                    "VOI arm lacks a frozen pre-materialization score"
                )
            if self.arm is DevelopmentAnytimeArmV1.TARGET_ONLY_VOI:
                if (
                    self.voi_result.arm
                    is not voi.DevelopmentVOIArmV1.NO_PRIOR
                    or self.source_prior_id is not None
                ):
                    raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                        "target-only arm contains source evidence"
                    )
            elif (
                self.voi_result.arm
                is not voi.DevelopmentVOIArmV1.SOURCE_META_PRIOR
                or self.source_prior_id is None
                or self.voi_result.source_prior_id
                != self.source_prior_id
            ):
                raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                    "source arm does not isolate its proposal-only prior"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_pre_materialization_voi_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "arm": self.arm.value,
            "round_index": self.round_index,
            "pre_epoch_id": self.pre_epoch_id,
            "proof_dag_id": self.proof_dag_id,
            "eligible_horizons": list(self.eligible_horizons),
            "exhausted_horizons": list(self.exhausted_horizons),
            "selected_horizon": self.selected_horizon,
            "selected_row_id": self.selected_row_id,
            "selected_candidate_id": self.selected_candidate_id,
            "voi_result_id": (
                None if self.voi_result is None else self.voi_result.result_id
            ),
            "source_prior_id": self.source_prior_id,
            "selection_rule": (
                "FIRST_FIXED_HORIZON_WITH_REMAINING_BLOCK_BUDGET"
                if self.arm
                is DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2
                else (
                    "FIRST_VOI_RANKED_CANDIDATE_WITH_REMAINING_"
                    "BLOCK_BUDGET"
                )
            ),
            "access_events": list(self.access_events),
            "target_reads_before_freeze": 0,
            "future_outcome_fields_used": [],
            "decision_frozen_before_materialization": True,
        }

    @property
    def decision_id(self) -> str:
        return _content_id("decision", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


@dataclass(frozen=True, slots=True)
class DevelopmentExecutedAnytimeBlockV1:
    decision: DevelopmentPreMaterializationDecisionV1
    pre_epoch_id: str
    post_epoch_id: str
    stream_id: str
    slice_start: int
    slice_end: int
    accepted_draws: int
    accepted_successes: int
    raw_slice_sha256: str
    stop_reason: DevelopmentBlockStopReasonV1
    access_events: tuple[str, ...]
    unexecuted_draws_charged: int = 0

    def __post_init__(self) -> None:
        for value, name in (
            (self.pre_epoch_id, "block pre-epoch"),
            (self.post_epoch_id, "block post-epoch"),
            (self.stream_id, "block stream"),
        ):
            _cid(value, name)
        if (
            type(self.decision)
            is not DevelopmentPreMaterializationDecisionV1
            or self.pre_epoch_id != self.decision.pre_epoch_id
            or self.slice_start not in (
                INITIAL_DRAWS_PER_ROW,
            )
            or self.slice_end != self.slice_start + BLOCK_SIZE
            or self.accepted_draws != BLOCK_SIZE
            or type(self.accepted_successes) is not int
            or not 0 <= self.accepted_successes <= self.accepted_draws
            or type(self.raw_slice_sha256) is not str
            or len(self.raw_slice_sha256) != 64
            or type(self.stop_reason) is not DevelopmentBlockStopReasonV1
            or self.access_events
            != self.decision.access_events + POST_DECISION_EVENTS
            or self.unexecuted_draws_charged != 0
        ):
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "executed block chronology or accepted-draw accounting failed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_executed_anytime_target_block.v1",
            "schema_version": SCHEMA_VERSION,
            "decision_id": self.decision.decision_id,
            "pre_epoch_id": self.pre_epoch_id,
            "post_epoch_id": self.post_epoch_id,
            "stream_id": self.stream_id,
            "slice_start": self.slice_start,
            "slice_end": self.slice_end,
            "accepted_draws": self.accepted_draws,
            "accepted_successes": self.accepted_successes,
            "raw_slice_sha256": self.raw_slice_sha256,
            "stop_reason": self.stop_reason.value,
            "access_events": list(self.access_events),
            "decision_frozen_event_index": (
                self.access_events.index("DECISION_FROZEN")
            ),
            "first_target_read_event_index": (
                self.access_events.index("SELECTED_RAW_SUFFIX_READ")
            ),
            "unexecuted_draws_charged": 0,
        }

    @property
    def block_id(self) -> str:
        return _content_id("block", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "block_id": self.block_id}


@dataclass(frozen=True, slots=True)
class DevelopmentAnytimeAdaptiveArmRunV1:
    arm: DevelopmentAnytimeArmV1
    schedule_profile_id: str
    stream_ids: tuple[str, ...]
    threshold_profile_id: str
    epochs: tuple[DevelopmentAnytimeAdaptiveEpochV1, ...]
    decisions: tuple[DevelopmentPreMaterializationDecisionV1, ...]
    blocks: tuple[DevelopmentExecutedAnytimeBlockV1, ...]
    source_prior_id: str | None
    terminal_code: DevelopmentRunTerminalCodeV1
    common_initial_accepted_draws: int
    incremental_accepted_draws: int
    total_accepted_draws: int
    unexecuted_blocks_charged_draws: int = 0
    registered_execution_allowed: bool = False
    sample_saving_claimed: bool = False
    sample_efficiency_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        _cid(self.schedule_profile_id, "run schedule")
        _cid(self.threshold_profile_id, "run threshold")
        if self.source_prior_id is not None:
            _cid(self.source_prior_id, "run source prior")
        if (
            type(self.arm) is not DevelopmentAnytimeArmV1
            or tuple(sorted(set(self.stream_ids))) != self.stream_ids
            or len(self.stream_ids) != 2
            or type(self.epochs) is not tuple
            or type(self.decisions) is not tuple
            or type(self.blocks) is not tuple
            or len(self.blocks) not in (1, 2)
            or len(self.decisions) != len(self.blocks)
            or len(self.epochs) != len(self.blocks) + 1
            or any(
                type(item) is not DevelopmentAnytimeAdaptiveEpochV1
                for item in self.epochs
            )
            or any(
                type(item)
                is not DevelopmentPreMaterializationDecisionV1
                for item in self.decisions
            )
            or any(
                type(item) is not DevelopmentExecutedAnytimeBlockV1
                for item in self.blocks
            )
            or tuple(item.epoch_index for item in self.epochs)
            != tuple(range(len(self.epochs)))
            or any(
                decision.arm is not self.arm
                or decision.round_index != index
                or block.decision != decision
                or block.pre_epoch_id != self.epochs[index - 1].epoch_id
                or block.post_epoch_id != self.epochs[index].epoch_id
                for index, (decision, block) in enumerate(
                    zip(self.decisions, self.blocks, strict=True),
                    start=1,
                )
            )
            or self.common_initial_accepted_draws
            != COMMON_INITIAL_ACCEPTED_DRAWS
            or self.incremental_accepted_draws
            != sum(item.accepted_draws for item in self.blocks)
            or self.incremental_accepted_draws
            != BLOCK_SIZE * len(self.blocks)
            or self.total_accepted_draws
            != (
                self.common_initial_accepted_draws
                + self.incremental_accepted_draws
            )
            or self.unexecuted_blocks_charged_draws != 0
            or self.registered_execution_allowed is not False
            or self.sample_saving_claimed is not False
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "adaptive arm run lineage or draw accounting is invalid"
            )
        final = self.epochs[-1]
        if self.terminal_code is DevelopmentRunTerminalCodeV1.PLAN_CERTIFIED:
            if (
                final.audit.status is not robust.RobustAuditStatus.CERTIFIED
                or self.blocks[-1].stop_reason
                is not DevelopmentBlockStopReasonV1.CERTIFIED_AFTER_BLOCK
                or any(
                    item.stop_reason
                    is DevelopmentBlockStopReasonV1.CERTIFIED_AFTER_BLOCK
                    for item in self.blocks[:-1]
                )
            ):
                raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                    "run did not stop at its first robust certificate"
                )
        elif (
            len(self.blocks) != MAX_EXECUTED_BLOCKS
            or final.audit.status is robust.RobustAuditStatus.CERTIFIED
        ):
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "noncertificate closure did not exhaust the block budget"
            )
        if self.arm is DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI:
            if self.source_prior_id is None:
                raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                    "source run lacks proposal prior"
                )
        elif self.source_prior_id is not None:
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "non-source run binds source prior"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_anytime_adaptive_arm_run.v1",
            "schema_version": SCHEMA_VERSION,
            "arm": self.arm.value,
            "schedule_profile_id": self.schedule_profile_id,
            "stream_ids": list(self.stream_ids),
            "threshold_profile_id": self.threshold_profile_id,
            "epoch_ids": [item.epoch_id for item in self.epochs],
            "decision_ids": [item.decision_id for item in self.decisions],
            "block_ids": [item.block_id for item in self.blocks],
            "source_prior_id": self.source_prior_id,
            "terminal_code": self.terminal_code.value,
            "common_initial_accepted_draws": (
                self.common_initial_accepted_draws
            ),
            "incremental_accepted_draws": self.incremental_accepted_draws,
            "total_accepted_draws": self.total_accepted_draws,
            "executed_block_count": len(self.blocks),
            "unexecuted_blocks_charged_draws": 0,
            "same_raw_stream_contract": True,
            "source_enters_counts_or_cs": False,
            "source_enters_fantasy_or_certificate": False,
            "registered_execution_allowed": False,
            "sample_saving_claimed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
        }

    @property
    def run_id(self) -> str:
        return _content_id("run", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "run_id": self.run_id}


@dataclass(frozen=True, slots=True)
class DevelopmentAnytimeThreeArmControlV1:
    structural_template_model: robust.PartialSupportIntervalModelV1
    streams: tuple[DevelopmentSharedTargetRowStreamV1, ...]
    schedule_profile: DevelopmentAnytimeBlockScheduleProfileV1
    threshold: robust.RobustThresholdProfileV1
    source_trials: tuple[voi.DevelopmentSourceVOITrialV1, ...]
    source_prior: voi.DevelopmentSourceVOIPriorV1
    runs: tuple[DevelopmentAnytimeAdaptiveArmRunV1, ...]
    incremental_accepted_draw_result: tuple[tuple[str, int], ...]
    total_accepted_draw_result: tuple[tuple[str, int], ...]
    registered_execution_allowed: bool = False
    registered_target_evidence: bool = False
    sample_saving_claimed: bool = False
    sample_efficiency_gate_status: str = "NOT_RUN"
    independent_verifier_scope: str = INDEPENDENT_VERIFIER_SCOPE
    planner_replay_boundary: str = PLANNER_REPLAY_BOUNDARY
    planner_algorithm_independence_claimed: bool = False

    def __post_init__(self) -> None:
        expected_arms = tuple(item.value for item in DevelopmentAnytimeArmV1)
        if (
            type(self.structural_template_model)
            is not robust.PartialSupportIntervalModelV1
            or type(self.streams) is not tuple
            or tuple(item.remaining_horizon for item in self.streams)
            != (1, 2)
            or type(self.schedule_profile)
            is not DevelopmentAnytimeBlockScheduleProfileV1
            or type(self.threshold) is not robust.RobustThresholdProfileV1
            or self.threshold.context_id
            != self.structural_template_model.context_id
            or self.threshold.risk_tolerance != RISK_TOLERANCE
            or type(self.source_trials) is not tuple
            or type(self.source_prior) is not voi.DevelopmentSourceVOIPriorV1
            or type(self.runs) is not tuple
            or tuple(item.arm.value for item in self.runs) != expected_arms
            or any(
                item.schedule_profile_id
                != self.schedule_profile.schedule_profile_id
                or item.stream_ids
                != tuple(sorted(stream.stream_id for stream in self.streams))
                or item.threshold_profile_id
                != self.threshold.threshold_profile_id
                or item.epochs[0] != self.runs[0].epochs[0]
                for item in self.runs
            )
            or self.incremental_accepted_draw_result
            != (
                (
                    DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2.value,
                    4,
                ),
                (
                    DevelopmentAnytimeArmV1.TARGET_ONLY_VOI.value,
                    2,
                ),
                (
                    DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI.value,
                    4,
                ),
            )
            or tuple(
                (item.arm.value, item.incremental_accepted_draws)
                for item in self.runs
            )
            != self.incremental_accepted_draw_result
            or self.total_accepted_draw_result
            != (
                (
                    DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2.value,
                    260,
                ),
                (
                    DevelopmentAnytimeArmV1.TARGET_ONLY_VOI.value,
                    258,
                ),
                (
                    DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI.value,
                    260,
                ),
            )
            or tuple(
                (item.arm.value, item.total_accepted_draws)
                for item in self.runs
            )
            != self.total_accepted_draw_result
            or self.runs[0].epochs[-1] != self.runs[2].epochs[-1]
            or self.runs[0].decisions[0].selected_horizon != 1
            or self.runs[1].decisions[0].selected_horizon != 2
            or self.runs[2].decisions[0].selected_horizon != 1
            or self.registered_execution_allowed is not False
            or self.registered_target_evidence is not False
            or self.sample_saving_claimed is not False
            or self.sample_efficiency_gate_status != "NOT_RUN"
            or self.independent_verifier_scope
            != INDEPENDENT_VERIFIER_SCOPE
            or self.planner_replay_boundary != PLANNER_REPLAY_BOUNDARY
            or self.planner_algorithm_independence_claimed is not False
        ):
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "three-arm control is unmatched, incomplete, or overclaims"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_anytime_three_arm_control.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "structural_template_model_id": (
                self.structural_template_model.model_id
            ),
            "stream_ids": [item.stream_id for item in self.streams],
            "schedule_profile_id": (
                self.schedule_profile.schedule_profile_id
            ),
            "threshold_profile_id": self.threshold.threshold_profile_id,
            "source_trial_ids": [
                item.trial_id for item in self.source_trials
            ],
            "source_prior_id": self.source_prior.prior_id,
            "run_ids": [item.run_id for item in self.runs],
            "common_initial_accepted_draws_per_arm": (
                COMMON_INITIAL_ACCEPTED_DRAWS
            ),
            "incremental_accepted_draw_result": [
                {"arm": arm, "accepted_draws": draws}
                for arm, draws in self.incremental_accepted_draw_result
            ],
            "total_accepted_draw_result": [
                {"arm": arm, "accepted_draws": draws}
                for arm, draws in self.total_accepted_draw_result
            ],
            "shared_raw_streams": True,
            "shared_confidence_contract": True,
            "source_enters_only_proposal_rank": True,
            "unexecuted_blocks_charge_zero_draws": True,
            "development_only": True,
            "registered_execution_allowed": False,
            "registered_target_evidence": False,
            "sample_saving_claimed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
            "independent_verifier_scope": INDEPENDENT_VERIFIER_SCOPE,
            "planner_replay_boundary": PLANNER_REPLAY_BOUNDARY,
            "planner_algorithm_independence_claimed": False,
        }

    @property
    def control_id(self) -> str:
        return _content_id("control", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


def _make_prefix(
    stream: DevelopmentSharedTargetRowStreamV1,
    prefix_draw_count: int,
    schedule: DevelopmentAnytimeBlockScheduleProfileV1,
) -> DevelopmentTargetRowPrefixV1:
    prefix = stream.outcomes[:prefix_draw_count]
    checkpoint = sequential.build_anytime_bernoulli_checkpoint_v1(
        prefix_draw_count,
        sum(prefix),
        schedule.sequential_profile,
    )
    return DevelopmentTargetRowPrefixV1(
        stream_id=stream.stream_id,
        remaining_horizon=stream.remaining_horizon,
        prefix_draw_count=prefix_draw_count,
        success_count=sum(prefix),
        raw_prefix_sha256=hashlib.sha256(_pack_bool(prefix)).hexdigest(),
        checkpoint=checkpoint,
    )


def _build_epoch(
    *,
    epoch_index: int,
    prefixes: tuple[DevelopmentTargetRowPrefixV1, ...],
    template: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
) -> DevelopmentAnytimeAdaptiveEpochV1:
    prefix_by_horizon = {
        item.remaining_horizon: item for item in prefixes
    }
    rows = []
    for template_row in template.rows:
        prefix = prefix_by_horizon[template_row.remaining_horizon]
        checkpoint = prefix.checkpoint
        masses = []
        for mass in template_row.masses:
            if mass.destination_id == template_row.other_destination_id:
                lower = 1 - checkpoint.upper_probability
                upper = 1 - checkpoint.lower_probability
            else:
                lower = checkpoint.lower_probability
                upper = checkpoint.upper_probability
            masses.append(
                robust.IntervalDestinationMassV1(
                    mass.destination_id,
                    lower,
                    upper,
                )
            )
        rows.append(replace(template_row, masses=tuple(masses)))
    model = robust.build_partial_support_model_v1(
        context_id=template.context_id,
        root_state_id=template.root_state_id,
        catalogues=template.catalogues,
        destinations=template.destinations,
        rows=rows,
        concretizer_entries=template.concretizer_entries,
    )
    audit = robust.solve_ground_direct_robust_h2_v1(model, threshold)
    if audit.status is robust.RobustAuditStatus.CERTIFIED:
        proof_dag = None
        evidence: tuple[voi.CurrentRowCountEvidenceV1, ...] = ()
    else:
        proof_dag = voi.freeze_development_failed_proof_dag_v1(
            model, threshold, audit
        )
        prefix_by_horizon = {
            item.remaining_horizon: item for item in prefixes
        }
        evidence_items = []
        for row in model.rows:
            prefix = prefix_by_horizon[row.remaining_horizon]
            destination_ids = tuple(
                item.destination_id for item in row.masses
            )
            failure_count = (
                prefix.prefix_draw_count - prefix.success_count
            )
            evidence_items.append(
                voi.CurrentRowCountEvidenceV1(
                    context_id=model.context_id,
                    model_id=model.model_id,
                    row_id=row.row_id,
                    evidence_epoch_id=prefix.prefix_id,
                    destination_ids=destination_ids,
                    counts=tuple(
                        (
                            failure_count
                            if destination_id == row.other_destination_id
                            else prefix.success_count
                        )
                        for destination_id in destination_ids
                    ),
                    other_destination_id=row.other_destination_id,
                )
            )
        evidence = tuple(
            sorted(evidence_items, key=lambda item: item.evidence_id)
        )
    return DevelopmentAnytimeAdaptiveEpochV1(
        epoch_index=epoch_index,
        row_prefixes=tuple(
            sorted(prefixes, key=lambda item: item.remaining_horizon)
        ),
        model=model,
        audit=audit,
        proof_dag=proof_dag,
        row_evidence=evidence,
    )


def _prepare_decision(
    *,
    arm: DevelopmentAnytimeArmV1,
    round_index: int,
    pre_epoch: DevelopmentAnytimeAdaptiveEpochV1,
    exhausted_horizons: tuple[int, ...],
    source_prior: voi.DevelopmentSourceVOIPriorV1,
) -> DevelopmentPreMaterializationDecisionV1:
    if pre_epoch.proof_dag is None:
        raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
            "cannot acquire after a plan certificate"
        )
    eligible = tuple(
        item for item in (1, 2) if item not in exhausted_horizons
    )
    row_by_horizon = {
        item.remaining_horizon: item for item in pre_epoch.model.rows
    }
    if arm is DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2:
        selected_horizon = next(
            item for item in (1, 2) if item in eligible
        )
        result = None
        candidate_id = None
        source_prior_id = None
        access_events = FIXED_DECISION_EVENTS
    else:
        scorer_arm = (
            voi.DevelopmentVOIArmV1.NO_PRIOR
            if arm is DevelopmentAnytimeArmV1.TARGET_ONLY_VOI
            else voi.DevelopmentVOIArmV1.SOURCE_META_PRIOR
        )
        result = voi.score_development_certificate_boundary_voi_v1(
            model=pre_epoch.model,
            threshold=robust.RobustThresholdProfileV1(
                pre_epoch.model.context_id,
                RISK_TOLERANCE,
                Fraction(1),
            ),
            failed_audit=pre_epoch.audit,
            proof_dag=pre_epoch.proof_dag,
            row_evidence=pre_epoch.row_evidence,
            next_block_size=BLOCK_SIZE,
            arm=scorer_arm,
            source_prior=(
                source_prior
                if scorer_arm
                is voi.DevelopmentVOIArmV1.SOURCE_META_PRIOR
                else None
            ),
        )
        base_by_candidate = {
            item.candidate.candidate_id: item for item in result.base_vois
        }
        selected_candidate = next(
            candidate_id
            for candidate_id in result.schedule.ordered_candidate_ids
            if base_by_candidate[
                candidate_id
            ].candidate.remaining_horizon in eligible
        )
        selected_horizon = base_by_candidate[
            selected_candidate
        ].candidate.remaining_horizon
        candidate_id = selected_candidate
        source_prior_id = (
            source_prior.prior_id
            if arm is DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI
            else None
        )
        access_events = VOI_DECISION_EVENTS
    return DevelopmentPreMaterializationDecisionV1(
        arm=arm,
        round_index=round_index,
        pre_epoch_id=pre_epoch.epoch_id,
        proof_dag_id=pre_epoch.proof_dag.dag_id,
        eligible_horizons=eligible,
        exhausted_horizons=tuple(sorted(exhausted_horizons)),
        selected_horizon=selected_horizon,
        selected_row_id=row_by_horizon[selected_horizon].row_id,
        selected_candidate_id=candidate_id,
        voi_result=result,
        source_prior_id=source_prior_id,
        access_events=access_events,
    )


def _run_arm(
    *,
    arm: DevelopmentAnytimeArmV1,
    streams: tuple[DevelopmentSharedTargetRowStreamV1, ...],
    schedule: DevelopmentAnytimeBlockScheduleProfileV1,
    template: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    initial_epoch: DevelopmentAnytimeAdaptiveEpochV1,
    source_prior: voi.DevelopmentSourceVOIPriorV1,
) -> DevelopmentAnytimeAdaptiveArmRunV1:
    stream_by_horizon = {
        item.remaining_horizon: item for item in streams
    }
    epochs = [initial_epoch]
    decisions = []
    blocks = []
    exhausted: tuple[int, ...] = ()
    for round_index in range(1, MAX_EXECUTED_BLOCKS + 1):
        pre_epoch = epochs[-1]
        if pre_epoch.audit.status is robust.RobustAuditStatus.CERTIFIED:
            break
        decision = _prepare_decision(
            arm=arm,
            round_index=round_index,
            pre_epoch=pre_epoch,
            exhausted_horizons=exhausted,
            source_prior=source_prior,
        )
        # No raw suffix is selected or read until the decision above exists.
        stream = stream_by_horizon[decision.selected_horizon]
        prefix_by_horizon = {
            item.remaining_horizon: item
            for item in pre_epoch.row_prefixes
        }
        selected_prefix = prefix_by_horizon[decision.selected_horizon]
        start = selected_prefix.prefix_draw_count
        end = start + BLOCK_SIZE
        raw_slice = stream.outcomes[start:end]
        if len(raw_slice) != BLOCK_SIZE:
            raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
                "selected target stream lacks its preregistered block"
            )
        prefix_by_horizon[decision.selected_horizon] = _make_prefix(
            stream, end, schedule
        )
        post_epoch = _build_epoch(
            epoch_index=round_index,
            prefixes=tuple(prefix_by_horizon.values()),
            template=template,
            threshold=threshold,
        )
        stop_reason = (
            DevelopmentBlockStopReasonV1.CERTIFIED_AFTER_BLOCK
            if post_epoch.audit.status
            is robust.RobustAuditStatus.CERTIFIED
            else DevelopmentBlockStopReasonV1.CONTINUE_FAILED_PROOF
        )
        block = DevelopmentExecutedAnytimeBlockV1(
            decision=decision,
            pre_epoch_id=pre_epoch.epoch_id,
            post_epoch_id=post_epoch.epoch_id,
            stream_id=stream.stream_id,
            slice_start=start,
            slice_end=end,
            accepted_draws=BLOCK_SIZE,
            accepted_successes=sum(raw_slice),
            raw_slice_sha256=hashlib.sha256(
                _pack_bool(raw_slice)
            ).hexdigest(),
            stop_reason=stop_reason,
            access_events=decision.access_events + POST_DECISION_EVENTS,
        )
        decisions.append(decision)
        blocks.append(block)
        epochs.append(post_epoch)
        exhausted = tuple(
            sorted((*exhausted, decision.selected_horizon))
        )
        if stop_reason is DevelopmentBlockStopReasonV1.CERTIFIED_AFTER_BLOCK:
            break
    terminal = (
        DevelopmentRunTerminalCodeV1.PLAN_CERTIFIED
        if epochs[-1].audit.status is robust.RobustAuditStatus.CERTIFIED
        else (
            DevelopmentRunTerminalCodeV1
            .BLOCK_BUDGET_EXHAUSTED_NONCERTIFICATE
        )
    )
    return DevelopmentAnytimeAdaptiveArmRunV1(
        arm=arm,
        schedule_profile_id=schedule.schedule_profile_id,
        stream_ids=tuple(
            sorted(item.stream_id for item in streams)
        ),
        threshold_profile_id=threshold.threshold_profile_id,
        epochs=tuple(epochs),
        decisions=tuple(decisions),
        blocks=tuple(blocks),
        source_prior_id=(
            source_prior.prior_id
            if arm is DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI
            else None
        ),
        terminal_code=terminal,
        common_initial_accepted_draws=COMMON_INITIAL_ACCEPTED_DRAWS,
        incremental_accepted_draws=sum(
            item.accepted_draws for item in blocks
        ),
        total_accepted_draws=(
            COMMON_INITIAL_ACCEPTED_DRAWS
            + sum(item.accepted_draws for item in blocks)
        ),
    )


def build_development_anytime_three_arm_control_v1(
) -> DevelopmentAnytimeThreeArmControlV1:
    """Run the deterministic shared-stream, three-arm development control."""

    base_control = voi.build_development_voi_opportunity_control_v1()
    template = base_control.target_model
    streams = (
        DevelopmentSharedTargetRowStreamV1(
            context_id=template.context_id,
            remaining_horizon=1,
            outcomes=(True,) * (INITIAL_DRAWS_PER_ROW + BLOCK_SIZE),
        ),
        DevelopmentSharedTargetRowStreamV1(
            context_id=template.context_id,
            remaining_horizon=2,
            outcomes=(
                (True,) * (INITIAL_DRAWS_PER_ROW - 1)
                + (False,)
                + (True,) * BLOCK_SIZE
            ),
        ),
    )
    schedule = DevelopmentAnytimeBlockScheduleProfileV1(
        sequential_profile=sequential.SequentialBernoulliProfileV1(
            confidence_alpha=ROW_ALPHA,
            target_half_width=Fraction(1, 1000),
            checkpoints=(
                INITIAL_DRAWS_PER_ROW,
                INITIAL_DRAWS_PER_ROW + BLOCK_SIZE,
            ),
            boundary_grid_bits=16,
        )
    )
    threshold = robust.RobustThresholdProfileV1(
        context_id=template.context_id,
        risk_tolerance=RISK_TOLERANCE,
        reward_ceiling=Fraction(1),
    )
    initial_prefixes = tuple(
        _make_prefix(stream, INITIAL_DRAWS_PER_ROW, schedule)
        for stream in streams
    )
    initial_epoch = _build_epoch(
        epoch_index=0,
        prefixes=initial_prefixes,
        template=template,
        threshold=threshold,
    )
    if (
        initial_epoch.audit.status
        is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    ):
        raise V073AnytimeAdaptiveAcquisitionInvariantViolation(
            "development control no longer starts at a failed proof boundary"
        )
    runs = tuple(
        _run_arm(
            arm=arm,
            streams=streams,
            schedule=schedule,
            template=template,
            threshold=threshold,
            initial_epoch=initial_epoch,
            source_prior=base_control.source_prior,
        )
        for arm in DevelopmentAnytimeArmV1
    )
    return DevelopmentAnytimeThreeArmControlV1(
        structural_template_model=template,
        streams=streams,
        schedule_profile=schedule,
        threshold=threshold,
        source_trials=base_control.source_trials,
        source_prior=base_control.source_prior,
        runs=runs,
        incremental_accepted_draw_result=tuple(
            (item.arm.value, item.incremental_accepted_draws)
            for item in runs
        ),
        total_accepted_draw_result=tuple(
            (item.arm.value, item.total_accepted_draws)
            for item in runs
        ),
    )


def run_registered_v073_anytime_adaptive_acquisition_v1(
    *_args: object,
    **_kwargs: object,
) -> None:
    raise RegisteredV073AnytimeAdaptiveAcquisitionLocked(
        "V0-073 anytime adaptive acquisition remains development-only; "
        "registered execution and the sample-efficiency Gate are locked"
    )


__all__ = [
    "BLOCK_SIZE",
    "COMMON_INITIAL_ACCEPTED_DRAWS",
    "build_development_anytime_three_arm_control_v1",
    "DevelopmentAnytimeAdaptiveArmRunV1",
    "DevelopmentAnytimeAdaptiveEpochV1",
    "DevelopmentAnytimeArmV1",
    "DevelopmentAnytimeBlockScheduleProfileV1",
    "DevelopmentAnytimeThreeArmControlV1",
    "DevelopmentBlockStopReasonV1",
    "DevelopmentExecutedAnytimeBlockV1",
    "DevelopmentPreMaterializationDecisionV1",
    "DevelopmentRunTerminalCodeV1",
    "DevelopmentSharedTargetRowStreamV1",
    "DevelopmentTargetRowPrefixV1",
    "FAMILY_ALPHA",
    "INITIAL_DRAWS_PER_ROW",
    "INDEPENDENT_VERIFIER_SCOPE",
    "MAX_EXECUTED_BLOCKS",
    "REGISTERED_EXECUTION_ALLOWED",
    "RISK_TOLERANCE",
    "ROW_ALPHA",
    "PLANNER_REPLAY_BOUNDARY",
    "run_registered_v073_anytime_adaptive_acquisition_v1",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SAMPLE_SAVING_CLAIMED",
    "V073AnytimeAdaptiveAcquisitionInvariantViolation",
]
