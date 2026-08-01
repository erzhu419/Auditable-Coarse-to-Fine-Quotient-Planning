"""Aggregate-only, construction-scoped V0-075 V2 robust planning leaf.

This module is deliberately split from the empirical construction backend and
from the exact total-lift authority.  It consumes signed V2 batch aggregates
only, reconstructs one discovery-frozen support plus ``OTHER`` per row, builds
count-only anytime confidence intervals, and solves either the adaptive
behavioral quotient or the matched direct ground model with exact rationals.

Two continuations are intentionally distinct:

* the selected partial policy maps ``OTHER`` and an unmaterialized positive
  child to absorbing policy-abort failure with zero continuation reward; and
* the unrestricted ground comparator assigns those unresolved events the
  registered optimistic remaining-reward upper.

Conflating the second rule with policy abort can underestimate the ground
optimum and is therefore rejected by construction.

The numerical model and proof contain no arm, proposal, source transport,
occurrence, or acquisition identity.  A separate occurrence wrapper binds the
prior-free proof to verified acquisition evidence.  Nothing in this module is
a plan or infeasibility certificate.  The production byte entry is
structurally locked until the dynamic acquisition terminal and isolated IPC
protocol are implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
import itertools
from pathlib import Path
from typing import Any, Iterable, Mapping, NoReturn

from acfqp import construction_accounting_owned_runtime_v1 as accounting_runtime
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.sequential_bernoulli_acquisition_v1 import (
    METHOD_ID as EXACT_BERNOULLI_METHOD_ID,
    SequentialBernoulliProfileV1,
    build_anytime_bernoulli_checkpoint_v1,
)
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle_v2
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition_v2
from acfqp import v075_private_observer_boundary_v2 as observer_v2
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.49.0"
PROFILE_KEY = "v075_batch_native_planning_backend_v2"

ROW_BETA = Fraction(1, 300_000)
TARGET_HALF_WIDTH = Fraction(1, 64)
BOUNDARY_GRID_BITS = 16
MAX_VALIDATED_ROWS = 21
FAMILYWISE_CONFIDENCE_ERROR_UPPER = Fraction(
    MAX_VALIDATED_ROWS,
    300_000,
)
MAX_EXACT_POLICY_ASSIGNMENTS = 1_000_000
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024

POLICY_ABORT_RULE = (
    "OTHER_OR_UNMATERIALIZED_CHILD_IS_ABSORBING_POLICY_ABORT_FAILURE_"
    "WITH_ZERO_CONTINUATION_REWARD"
)
COMPARATOR_RULE = (
    "OTHER_OR_UNRESOLVED_CHILD_USES_OPTIMISTIC_REGISTERED_"
    "REMAINING_REWARD_UPPER"
)

OFFICIAL_EXECUTION_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
PER_DRAW_RECORDS_ALLOWED = False
PRIVATE_LAW_ACCESS_ALLOWED = False
PRODUCTION_BLOCKER = (
    "V2_DYNAMIC_ACQUISITION_TERMINAL_AND_ISOLATED_IPC_NOT_BOUND"
)

DOMAIN_TAGS = {
    "descriptor": "acfqp:v075-batch-planning-support-descriptor:v2",
    "interval": "acfqp:v075-batch-planning-event-interval:v2",
    "row": "acfqp:v075-batch-planning-numerical-row:v2",
    "model": "acfqp:v075-batch-planning-numerical-model:v2",
    "evidence": "acfqp:v075-batch-planning-row-evidence-binding:v2",
    "input": "acfqp:v075-batch-planning-construction-input:v2",
    "behavior": "acfqp:v075-batch-planning-row-behavior:v2",
    "cell": "acfqp:v075-batch-planning-quotient-cell:v2",
    "quotient": "acfqp:v075-batch-planning-behavioral-quotient:v2",
    "policy": "acfqp:v075-batch-planning-policy:v2",
    "envelope": "acfqp:v075-batch-planning-envelope:v2",
    "frontier": "acfqp:v075-batch-planning-failed-frontier:v2",
    "proof": "acfqp:v075-batch-planning-numerical-proof:v2",
    "result": "acfqp:v075-batch-planning-construction-result:v2",
    "verification": "acfqp:v075-batch-planning-verification:v2",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 V2 planning domains overlap")


class V075BatchNativePlanningV2InvariantViolation(ValueError):
    """An input, confidence row, quotient, proof, or identity was invalid."""


class V075BatchNativePlanningV2NotReady(RuntimeError):
    """Production execution remains structurally unavailable."""


def _fail(message: str) -> None:
    raise V075BatchNativePlanningV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075BatchNativePlanningV2InvariantViolation(str(error)) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075BatchNativePlanningV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("V2 planning arithmetic must use exact Fraction")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _action(value: Any, label: str = "ground action") -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
        or value[0] >= value[1]
        or value[2] not in value[:2]
    ):
        _fail(f"{label} is not one canonical merge/survivor action")
    return value


def _merge_reward(
    row: graph.V075ObservationRowBindingV1,
) -> Fraction:
    rank = row.catalogue.state.ranks[row.action[0]]
    context = row.context
    return (
        Fraction(2 ** (rank + 1), 2 ** (context.rank_cap + 1))
        / context.horizon
    )


def _structural_state(
    row: graph.V075ObservationRowBindingV1,
    *,
    next_ranks: tuple[int, ...],
    failure: bool,
    terminal: bool,
) -> graph.V075SymbolicGraphStateV1:
    if (
        type(row) is not graph.V075ObservationRowBindingV1
        or type(next_ranks) is not tuple
        or type(failure) is not bool
        or type(terminal) is not bool
    ):
        _fail("V2 structural successor input is mistyped")
    source = row.catalogue.state
    first, second, survivor = row.action
    rank = source.ranks[first]
    board = list(source.ranks)
    board[first] = 0
    board[second] = 0
    board[survivor] = min(rank + 1, row.context.rank_cap)
    empty = tuple(index for index, value in enumerate(board) if value == 0)
    changed = tuple(
        index
        for index, (before, after) in enumerate(zip(board, next_ranks))
        if before != after
    )
    if (
        len(next_ranks) != len(board)
        or len(changed) != 1
        or changed[0] not in empty
        or board[changed[0]] != 0
        or not 0 < next_ranks[changed[0]] <= row.context.rank_cap
    ):
        _fail("V2 outcome is not one structurally possible single spawn")
    try:
        state = graph.V075SymbolicGraphStateV1(
            row.context,
            next_ranks,
            failure,
        )
        legal = graph.legal_action_triples_v1(
            row.context,
            state.ranks,
            False,
        )
    except graph.V075PublicGraphSemanticsInvariantViolation as error:
        raise V075BatchNativePlanningV2InvariantViolation(str(error)) from error
    expected_failure = not legal
    expected_terminal = failure or row.remaining_horizon == 1
    if failure != expected_failure or terminal != expected_terminal:
        _fail("V2 successor failure or terminal semantics changed")
    return state


class V075PlanningRouteV2(str, Enum):
    ADAPTIVE_QUOTIENT = "ADAPTIVE_QUOTIENT"
    MATCHED_DIRECT_GROUND = "MATCHED_DIRECT_GROUND"


class V075NumericalOutcomeV2(str, Enum):
    CANDIDATE = "CANDIDATE_READY_FOR_INDEPENDENT_TOTAL_LIFT"
    FAILED_FRONTIER = "FAILED_PROOF_FRONTIER"


class V075FailedProofReasonV2(str, Enum):
    RISK_BOUND_FAILED = "RISK_BOUND_FAILED"
    REGRET_BOUND_FAILED = "REGRET_BOUND_FAILED"
    RISK_AND_REGRET_BOUND_FAILED = "RISK_AND_REGRET_BOUND_FAILED"
    SEARCH_CAP_EXHAUSTED = "SEARCH_CAP_EXHAUSTED"
    GENERIC_CONSTRUCTION_NOT_SCHEDULE_BOUND = (
        "GENERIC_CONSTRUCTION_NOT_SCHEDULE_BOUND"
    )


_DESCRIPTOR_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075SupportDescriptorV2:
    _issuer: object = field(repr=False, compare=False)
    context_id: str
    next_state_id: str
    next_ranks: tuple[int, ...]
    failure: bool
    terminal: bool
    _descriptor_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.context_id, "support descriptor context")
        _cid(self.next_state_id, "support descriptor state")
        if (
            self._issuer is not _DESCRIPTOR_ISSUER
            or type(self.next_ranks) is not tuple
            or not self.next_ranks
            or any(type(item) is not int or item < 0 for item in self.next_ranks)
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or (self.failure and not self.terminal)
        ):
            _fail("V2 support descriptor is malformed or caller-minted")
        object.__setattr__(
            self,
            "_descriptor_id",
            _hash("descriptor", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_support_descriptor.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "next_state_id": self.next_state_id,
            "next_ranks": list(self.next_ranks),
            "failure": self.failure,
            "terminal": self.terminal,
            "support_key": {
                "next_ranks": list(self.next_ranks),
                "failure": self.failure,
                "terminal": self.terminal,
            },
            "spawn_identity_projected_out": True,
        }

    @property
    def descriptor_id(self) -> str:
        return self._descriptor_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "descriptor_id": self.descriptor_id}


_INTERVAL_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075EventIntervalV2:
    _issuer: object = field(repr=False, compare=False)
    event_key: str
    descriptor: V075SupportDescriptorV2 | None
    draw_count: int
    success_count: int
    empirical_probability: Fraction
    lower_probability: Fraction
    upper_probability: Fraction
    event_alpha: Fraction
    exact_likelihood_comparisons: int
    log_search_evaluations: int
    method_id: str
    _interval_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.event_key == "OTHER":
            descriptor_ok = self.descriptor is None
        else:
            descriptor_ok = (
                type(self.descriptor) is V075SupportDescriptorV2
                and self.event_key == self.descriptor.descriptor_id
            )
        if (
            self._issuer is not _INTERVAL_ISSUER
            or not descriptor_ok
            or type(self.draw_count) is not int
            or self.draw_count <= 0
            or type(self.success_count) is not int
            or not 0 <= self.success_count <= self.draw_count
            or type(self.empirical_probability) is not Fraction
            or self.empirical_probability
            != Fraction(self.success_count, self.draw_count)
            or any(
                type(value) is not Fraction
                for value in (
                    self.lower_probability,
                    self.upper_probability,
                    self.event_alpha,
                )
            )
            or not 0 <= self.lower_probability <= self.empirical_probability
            or not self.empirical_probability <= self.upper_probability <= 1
            or not 0 < self.event_alpha < 1
            or type(self.exact_likelihood_comparisons) is not int
            or self.exact_likelihood_comparisons < 0
            or type(self.log_search_evaluations) is not int
            or self.log_search_evaluations < 0
            or self.method_id not in {
                EXACT_BERNOULLI_METHOD_ID,
                "MANUAL_EXACT_INTERVAL_FIXTURE_V2",
            }
        ):
            _fail("V2 event interval is malformed or caller-minted")
        object.__setattr__(
            self,
            "_interval_id",
            _hash("interval", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_event_interval.v2",
            "schema_version": SCHEMA_VERSION,
            "event_key": self.event_key,
            "descriptor_id": (
                None if self.descriptor is None else self.descriptor.descriptor_id
            ),
            "draw_count": self.draw_count,
            "success_count": self.success_count,
            "empirical_probability": _fdoc(self.empirical_probability),
            "lower_probability": _fdoc(self.lower_probability),
            "upper_probability": _fdoc(self.upper_probability),
            "event_alpha": _fdoc(self.event_alpha),
            "exact_likelihood_comparisons": (
                self.exact_likelihood_comparisons
            ),
            "log_search_evaluations": self.log_search_evaluations,
            "method_id": self.method_id,
            "count_only": True,
            "per_draw_records_used": False,
        }

    @property
    def interval_id(self) -> str:
        return self._interval_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "interval_id": self.interval_id}


_ROW_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075NumericalRowV2:
    _issuer: object = field(repr=False, compare=False)
    context_id: str
    row_binding_id: str
    source_state_id: str
    source_ranks: tuple[int, ...]
    remaining_horizon: int
    action: tuple[int, int, int]
    immediate_reward: Fraction
    support: tuple[V075SupportDescriptorV2, ...]
    intervals: tuple[V075EventIntervalV2, ...]
    _row_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.context_id, "numerical row context"),
            (self.row_binding_id, "numerical row binding"),
            (self.source_state_id, "numerical row source"),
        ):
            _cid(value, label)
        _action(self.action)
        if (
            self._issuer is not _ROW_ISSUER
            or type(self.source_ranks) is not tuple
            or not self.source_ranks
            or any(type(item) is not int or item < 0 for item in self.source_ranks)
            or self.remaining_horizon not in (1, 2)
            or type(self.immediate_reward) is not Fraction
            or self.immediate_reward < 0
            or type(self.support) is not tuple
            or not self.support
            or tuple(item.descriptor_id for item in self.support)
            != tuple(sorted({item.descriptor_id for item in self.support}))
            or type(self.intervals) is not tuple
            or tuple(item.event_key for item in self.intervals)
            != tuple(item.descriptor_id for item in self.support) + ("OTHER",)
            or any(
                type(item) is not V075EventIntervalV2
                for item in self.intervals
            )
        ):
            _fail("V2 numerical row is malformed or caller-minted")
        draw_counts = {item.draw_count for item in self.intervals}
        alphas = {item.event_alpha for item in self.intervals}
        if (
            len(draw_counts) != 1
            or sum(item.success_count for item in self.intervals)
            != next(iter(draw_counts))
            or alphas != {ROW_BETA / len(self.intervals)}
            or sum(
                (item.lower_probability for item in self.intervals),
                Fraction(0),
            )
            > 1
            or sum(
                (item.upper_probability for item in self.intervals),
                Fraction(0),
            )
            < 1
        ):
            _fail("V2 row event partition or simplex intersection is invalid")
        object.__setattr__(self, "_row_id", _hash("row", self._payload()))

    @property
    def validation_draw_count(self) -> int:
        return self.intervals[0].draw_count

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_numerical_row.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "source_state_id": self.source_state_id,
            "source_ranks": list(self.source_ranks),
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "immediate_reward": _fdoc(self.immediate_reward),
            "support_descriptor_ids": [
                item.descriptor_id for item in self.support
            ],
            "interval_ids": [item.interval_id for item in self.intervals],
            "validation_draw_count": self.validation_draw_count,
            "support_frozen_before_validation": True,
            "zero_count_support_retained": True,
            "validation_counts_exclude_discovery": True,
            "one_explicit_other_event": True,
            "policy_abort_rule": POLICY_ABORT_RULE,
        }

    @property
    def row_id(self) -> str:
        return self._row_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "support": [item.to_document() for item in self.support],
            "intervals": [item.to_document() for item in self.intervals],
            "row_id": self.row_id,
        }


_MODEL_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075NumericalModelV2:
    _issuer: object = field(repr=False, compare=False)
    context: public_authority.V075PublicReplicateContextV1 = field(repr=False)
    rows: tuple[V075NumericalRowV2, ...]
    evidence_kind: str
    _model_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _MODEL_ISSUER
            or type(self.context)
            is not public_authority.V075PublicReplicateContextV1
            or type(self.rows) is not tuple
            or not self.rows
            or len(self.rows) > MAX_VALIDATED_ROWS
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
            or self.evidence_kind
            not in {"SIGNED_V2_AGGREGATES", "MANUAL_EXACT_INTERVAL_FIXTURE"}
            or any(item.context_id != self.context.context_id for item in self.rows)
        ):
            _fail("V2 numerical model is malformed or caller-minted")
        method_ids = {
            interval.method_id
            for row in self.rows
            for interval in row.intervals
        }
        expected_methods = (
            {EXACT_BERNOULLI_METHOD_ID}
            if self.evidence_kind == "SIGNED_V2_AGGREGATES"
            else {"MANUAL_EXACT_INTERVAL_FIXTURE_V2"}
        )
        if method_ids != expected_methods:
            _fail("V2 model evidence kind differs from its interval authority")
        _validate_model_closure(self.context, self.rows)
        object.__setattr__(self, "_model_id", _hash("model", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_numerical_model.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context.context_id,
            "row_ids": [item.row_id for item in self.rows],
            "evidence_kind": self.evidence_kind,
            "row_beta": _fdoc(ROW_BETA),
            "maximum_validated_rows": MAX_VALIDATED_ROWS,
            "familywise_confidence_error_upper": _fdoc(
                FAMILYWISE_CONFIDENCE_ERROR_UPPER
            ),
            "familywise_bound_uses_preregistered_maximum_not_actual_rows": True,
            "target_half_width": _fdoc(TARGET_HALF_WIDTH),
            "boundary_grid_bits": BOUNDARY_GRID_BITS,
            "prior_or_proposal_fields_present": False,
            "occurrence_or_arm_fields_present": False,
            "private_law_access": False,
        }

    @property
    def model_id(self) -> str:
        return self._model_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "rows": [item.to_document() for item in self.rows],
            "model_id": self.model_id,
        }


_EVIDENCE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075RowEvidenceBindingV2:
    _issuer: object = field(repr=False, compare=False)
    numerical_row_id: str
    row_binding_id: str
    support_freeze_id: str
    discovery_batch_ids: tuple[str, ...]
    latest_validation_batch_ids: tuple[str, ...]
    latest_validation_epoch_index: int
    lifecycle_closure_id: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.numerical_row_id, "row evidence numerical row"),
            (self.row_binding_id, "row evidence row binding"),
            (self.support_freeze_id, "row evidence support freeze"),
            (self.lifecycle_closure_id, "row evidence lifecycle"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _EVIDENCE_ISSUER
            or self.discovery_batch_ids
            != tuple(sorted(set(self.discovery_batch_ids)))
            or not self.discovery_batch_ids
            or self.latest_validation_batch_ids
            != tuple(sorted(set(self.latest_validation_batch_ids)))
            or not self.latest_validation_batch_ids
            or type(self.latest_validation_epoch_index) is not int
            or self.latest_validation_epoch_index != 1
        ):
            _fail("V2 row evidence binding is malformed or caller-minted")
        for value in (
            *self.discovery_batch_ids,
            *self.latest_validation_batch_ids,
        ):
            _cid(value, "row evidence batch")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("evidence", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_row_evidence_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "numerical_row_id": self.numerical_row_id,
            "row_binding_id": self.row_binding_id,
            "support_freeze_id": self.support_freeze_id,
            "discovery_batch_ids": list(self.discovery_batch_ids),
            "latest_validation_batch_ids": list(
                self.latest_validation_batch_ids
            ),
            "latest_validation_epoch_index": (
                self.latest_validation_epoch_index
            ),
            "lifecycle_closure_id": self.lifecycle_closure_id,
            "latest_registered_validation_prefix_only": True,
            "superseded_validation_counts_used": False,
            "aggregate_only": True,
            "per_draw_record_count": 0,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


_INPUT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPlanningInputV2:
    _issuer: object = field(repr=False, compare=False)
    schedule_id: str
    lineage_id: str
    lifecycle_closure_id: str
    lifecycle_verification_id: str
    occurrence_id: str
    target_tape_namespace_id: str
    arm: worker.V075WorkerArmV1
    route: V075PlanningRouteV2
    model: V075NumericalModelV2
    evidence_bindings: tuple[V075RowEvidenceBindingV2, ...]
    _input_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.schedule_id, "planning schedule"),
            (self.lineage_id, "planning lineage"),
            (self.lifecycle_closure_id, "planning lifecycle"),
            (self.lifecycle_verification_id, "planning lifecycle verification"),
            (self.occurrence_id, "planning occurrence"),
            (self.target_tape_namespace_id, "planning namespace"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _INPUT_ISSUER
            or type(self.arm) is not worker.V075WorkerArmV1
            or type(self.route) is not V075PlanningRouteV2
            or type(self.model) is not V075NumericalModelV2
            or self.model.evidence_kind != "SIGNED_V2_AGGREGATES"
            or type(self.evidence_bindings) is not tuple
            or tuple(item.numerical_row_id for item in self.evidence_bindings)
            != tuple(item.row_id for item in self.model.rows)
            or any(
                type(item) is not V075RowEvidenceBindingV2
                or item.lifecycle_closure_id != self.lifecycle_closure_id
                for item in self.evidence_bindings
            )
            or (
                self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            )
            != (self.route is V075PlanningRouteV2.MATCHED_DIRECT_GROUND)
        ):
            _fail("V2 construction planning input is malformed")
        object.__setattr__(self, "_input_id", _hash("input", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_construction_input.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": "CONSTRUCTION_ONLY",
            "schedule_id": self.schedule_id,
            "lineage_id": self.lineage_id,
            "lifecycle_closure_id": self.lifecycle_closure_id,
            "lifecycle_verification_id": self.lifecycle_verification_id,
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "arm": self.arm.value,
            "route": self.route.value,
            "numerical_model_id": self.model.model_id,
            "row_evidence_binding_ids": [
                item.binding_id for item in self.evidence_bindings
            ],
            "prior_free_numerical_model": True,
            "schedule_coverage_status": (
                "GENERIC_CONSTRUCTION_FIXTURE_NOT_SCHEDULE_BOUND"
            ),
            "preregistered_schedule_coverage_verified": False,
            "aggregate_only": True,
            "per_draw_record_count": 0,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def input_id(self) -> str:
        return self._input_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "model": self.model.to_document(),
            "evidence_bindings": [
                item.to_document() for item in self.evidence_bindings
            ],
            "input_id": self.input_id,
        }


def _registered_context(
    context_id: str,
) -> public_authority.V075PublicReplicateContextV1:
    contexts = tuple(
        item
        for item in (
            public_authority.freeze_v075_public_family_generation_v1()
            .replicate_contexts
        )
        if item.context_id == context_id
    )
    if len(contexts) != 1:
        _fail("V2 planning context is not preregistered")
    return contexts[0]


def _replay_support_descriptor(
    claimed: V075SupportDescriptorV2,
) -> V075SupportDescriptorV2:
    if type(claimed) is not V075SupportDescriptorV2:
        _fail("V2 support descriptor replay rejects duck-typed inputs")
    expected = V075SupportDescriptorV2(
        _DESCRIPTOR_ISSUER,
        claimed.context_id,
        claimed.next_state_id,
        claimed.next_ranks,
        claimed.failure,
        claimed.terminal,
    )
    if (
        expected.descriptor_id != claimed.descriptor_id
        or expected.to_document() != claimed.to_document()
    ):
        _fail("V2 support descriptor differs from exact semantic replay")
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.typed-replay.support-descriptor"
    )
    return expected


def _replay_event_interval(
    claimed: V075EventIntervalV2,
) -> V075EventIntervalV2:
    if type(claimed) is not V075EventIntervalV2:
        _fail("V2 event interval replay rejects duck-typed inputs")
    descriptor = (
        None
        if claimed.descriptor is None
        else _replay_support_descriptor(claimed.descriptor)
    )
    if claimed.method_id == EXACT_BERNOULLI_METHOD_ID:
        checkpoint = build_anytime_bernoulli_checkpoint_v1(
            claimed.draw_count,
            claimed.success_count,
            SequentialBernoulliProfileV1(
                confidence_alpha=claimed.event_alpha,
                target_half_width=TARGET_HALF_WIDTH,
                checkpoints=(claimed.draw_count,),
                boundary_grid_bits=BOUNDARY_GRID_BITS,
            ),
        )
        accounting_runtime.emit_owned_operation_v1(
            "batch-planning.replay.checkpoint"
        )
        empirical_probability = checkpoint.empirical_probability
        lower_probability = checkpoint.lower_probability
        upper_probability = checkpoint.upper_probability
        exact_likelihood_comparisons = (
            checkpoint.exact_likelihood_comparisons
        )
        log_search_evaluations = checkpoint.log_search_evaluations
    else:
        empirical_probability = claimed.empirical_probability
        lower_probability = claimed.lower_probability
        upper_probability = claimed.upper_probability
        exact_likelihood_comparisons = (
            claimed.exact_likelihood_comparisons
        )
        log_search_evaluations = claimed.log_search_evaluations
    expected = V075EventIntervalV2(
        _INTERVAL_ISSUER,
        claimed.event_key,
        descriptor,
        claimed.draw_count,
        claimed.success_count,
        empirical_probability,
        lower_probability,
        upper_probability,
        claimed.event_alpha,
        exact_likelihood_comparisons,
        log_search_evaluations,
        claimed.method_id,
    )
    if (
        expected.interval_id != claimed.interval_id
        or expected.to_document() != claimed.to_document()
    ):
        _fail("V2 event interval differs from exact semantic replay")
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.replay.interval-reconstruction"
    )
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.typed-replay.event-interval"
    )
    return expected


def _replay_numerical_row(
    claimed: V075NumericalRowV2,
) -> V075NumericalRowV2:
    if type(claimed) is not V075NumericalRowV2:
        _fail("V2 numerical row replay rejects duck-typed inputs")
    support = tuple(
        _replay_support_descriptor(item) for item in claimed.support
    )
    intervals = tuple(
        _replay_event_interval(item) for item in claimed.intervals
    )
    expected = V075NumericalRowV2(
        _ROW_ISSUER,
        claimed.context_id,
        claimed.row_binding_id,
        claimed.source_state_id,
        claimed.source_ranks,
        claimed.remaining_horizon,
        claimed.action,
        claimed.immediate_reward,
        support,
        intervals,
    )
    if (
        expected.row_id != claimed.row_id
        or expected.to_document() != claimed.to_document()
    ):
        _fail("V2 numerical row differs from exact semantic replay")
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.typed-replay.numerical-row"
    )
    return expected


def _replay_numerical_model(
    claimed: V075NumericalModelV2,
) -> V075NumericalModelV2:
    if type(claimed) is not V075NumericalModelV2:
        _fail("V2 numerical model replay rejects duck-typed inputs")
    context = _registered_context(claimed.context.context_id)
    if canonical_json_bytes(context.to_document()) != canonical_json_bytes(
        claimed.context.to_document()
    ):
        _fail("V2 numerical model context differs from registration")
    expected = V075NumericalModelV2(
        _MODEL_ISSUER,
        context,
        tuple(_replay_numerical_row(item) for item in claimed.rows),
        claimed.evidence_kind,
    )
    if (
        expected.model_id != claimed.model_id
        or expected.to_document() != claimed.to_document()
    ):
        _fail("V2 numerical model differs from exact semantic replay")
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.typed-replay.numerical-model"
    )
    return expected


def _replay_row_evidence_binding(
    claimed: V075RowEvidenceBindingV2,
) -> V075RowEvidenceBindingV2:
    if type(claimed) is not V075RowEvidenceBindingV2:
        _fail("V2 row evidence replay rejects duck-typed inputs")
    expected = V075RowEvidenceBindingV2(
        _EVIDENCE_ISSUER,
        claimed.numerical_row_id,
        claimed.row_binding_id,
        claimed.support_freeze_id,
        claimed.discovery_batch_ids,
        claimed.latest_validation_batch_ids,
        claimed.latest_validation_epoch_index,
        claimed.lifecycle_closure_id,
    )
    if (
        expected.binding_id != claimed.binding_id
        or expected.to_document() != claimed.to_document()
    ):
        _fail("V2 row evidence differs from exact semantic replay")
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.typed-replay.row-evidence-binding"
    )
    return expected


def _replay_construction_planning_input(
    claimed: V075ConstructionPlanningInputV2,
) -> V075ConstructionPlanningInputV2:
    if type(claimed) is not V075ConstructionPlanningInputV2:
        _fail("V2 planning input replay rejects duck-typed inputs")
    expected = V075ConstructionPlanningInputV2(
        _INPUT_ISSUER,
        claimed.schedule_id,
        claimed.lineage_id,
        claimed.lifecycle_closure_id,
        claimed.lifecycle_verification_id,
        claimed.occurrence_id,
        claimed.target_tape_namespace_id,
        claimed.arm,
        claimed.route,
        _replay_numerical_model(claimed.model),
        tuple(
            _replay_row_evidence_binding(item)
            for item in claimed.evidence_bindings
        ),
    )
    if (
        expected.input_id != claimed.input_id
        or expected.to_document() != claimed.to_document()
    ):
        _fail("V2 planning input differs from exact semantic replay")
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.typed-replay.construction-planning-input"
    )
    return expected


def _validate_model_closure(
    context: public_authority.V075PublicReplicateContextV1,
    rows: tuple[V075NumericalRowV2, ...],
) -> None:
    by_state: dict[str, dict[tuple[int, int, int], V075NumericalRowV2]] = {}
    for row in rows:
        if row.action in by_state.setdefault(row.source_state_id, {}):
            _fail("V2 numerical model duplicates one state/action row")
        by_state[row.source_state_id][row.action] = row
        state = graph.V075SymbolicGraphStateV1(
            context,
            row.source_ranks,
            False,
        )
        catalogue = graph.V075LegalActionCatalogueV1(
            context,
            state,
            row.remaining_horizon,
            graph.legal_action_triples_v1(
                context,
                state.ranks,
                state.failure,
            ),
        )
        binding = graph.observation_row_binding_v1(
            context,
            catalogue,
            row.action,
        )
        if (
            state.state_id != row.source_state_id
            or binding.row_binding_id != row.row_binding_id
            or _merge_reward(binding) != row.immediate_reward
        ):
            _fail("V2 numerical row differs from public structural replay")
        for descriptor in row.support:
            state2 = _structural_state(
                binding,
                next_ranks=descriptor.next_ranks,
                failure=descriptor.failure,
                terminal=descriptor.terminal,
            )
            if (
                descriptor.context_id != context.context_id
                or descriptor.next_state_id != state2.state_id
            ):
                _fail("V2 descriptor differs from structural replay")
    root = graph.root_catalogue_v1(context)
    if set(by_state.get(root.state.state_id, {})) != set(root.actions):
        _fail("V2 model lacks the complete root action catalogue")
    observed_children = {
        descriptor.next_state_id: descriptor.next_ranks
        for row in by_state[root.state.state_id].values()
        for descriptor in row.support
        if not descriptor.failure and not descriptor.terminal
    }
    actual_children = set(by_state) - {root.state.state_id}
    if not actual_children <= set(observed_children):
        _fail("V2 model contains an unobserved child state")
    for state_id in actual_children:
        state = graph.V075SymbolicGraphStateV1(
            context,
            observed_children[state_id],
            False,
        )
        catalogue = graph.V075LegalActionCatalogueV1(
            context,
            state,
            1,
            graph.legal_action_triples_v1(
                context,
                state.ranks,
                state.failure,
            ),
        )
        if set(by_state[state_id]) != set(catalogue.actions):
            _fail("V2 materialized child catalogue is incomplete")


def _allowed_checkpoints(
    *,
    arm: worker.V075WorkerArmV1,
    remaining_horizon: int,
    caps: worker.V075WorkerCapProfileV1,
) -> tuple[int, ...]:
    if arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND:
        return caps.direct_validation_checkpoints
    base = (
        caps.initial_validation_draws_per_row
        if remaining_horizon == 2
        else caps.new_child_validation_draws_per_row
    )
    return tuple(
        base + index * caps.promotion_validation_draws_per_round
        for index in range(caps.maximum_adaptive_rounds + 1)
    )


def _checkpoint_interval(
    *,
    descriptor: V075SupportDescriptorV2 | None,
    draw_count: int,
    success_count: int,
    event_count: int,
    checkpoints: tuple[int, ...],
) -> V075EventIntervalV2:
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.confidence-event.evaluate"
    )
    if draw_count not in checkpoints:
        _fail("latest validation prefix is not a registered checkpoint")
    alpha = ROW_BETA / event_count
    profile = SequentialBernoulliProfileV1(
        confidence_alpha=alpha,
        target_half_width=TARGET_HALF_WIDTH,
        checkpoints=checkpoints,
        boundary_grid_bits=BOUNDARY_GRID_BITS,
    )
    checkpoint = build_anytime_bernoulli_checkpoint_v1(
        draw_count,
        success_count,
        profile,
    )
    interval = V075EventIntervalV2(
        _INTERVAL_ISSUER,
        "OTHER" if descriptor is None else descriptor.descriptor_id,
        descriptor,
        draw_count,
        success_count,
        checkpoint.empirical_probability,
        checkpoint.lower_probability,
        checkpoint.upper_probability,
        alpha,
        checkpoint.exact_likelihood_comparisons,
        checkpoint.log_search_evaluations,
        EXACT_BERNOULLI_METHOD_ID,
    )
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.interval-row.construct"
    )
    return interval


def _replay_construction_lineage(
    claimed: batched_v2.V075BatchOccurrenceLineageV2,
) -> batched_v2.V075BatchOccurrenceLineageV2:
    if (
        type(claimed) is not batched_v2.V075BatchOccurrenceLineageV2
        or claimed.scope
        is not batched_v2.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail("V2 planner requires one exact construction lineage")
    try:
        expected = (
            batched_v2.replay_v075_signed_batch_occurrence_lineage_v2(
                claimed
            )
        )
    except Exception as error:
        if type(error) is V075BatchNativePlanningV2InvariantViolation:
            raise
        raise V075BatchNativePlanningV2InvariantViolation(
            "V2 construction lineage exact typed replay failed"
        ) from error
    if (
        expected.lineage_id != claimed.lineage_id
        or expected.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("V2 construction lineage differs from exact typed replay")
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.typed-replay.construction-lineage"
    )
    return expected


def _compile_aggregate_rows(
    *,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    lifecycle: lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2,
) -> tuple[
    tuple[V075NumericalRowV2, ...],
    tuple[V075RowEvidenceBindingV2, ...],
]:
    by_row: dict[str, list[observer_v2.V075SignedObservationBatchV2]] = {}
    for batch in lineage.batches:
        by_row.setdefault(
            batch.request.stream_identity.row_binding_id,
            [],
        ).append(batch)
    freezes_by_row: dict[
        str,
        list[lifecycle_v2.V075BatchSupportFreezeV2],
    ] = {}
    for freeze in lifecycle.support_freezes:
        freezes_by_row.setdefault(freeze.row_binding_id, []).append(freeze)
    evidence_by_id = {
        item.evidence_id: item for item in lifecycle.support_evidence
    }
    rows: list[V075NumericalRowV2] = []
    bindings: list[V075RowEvidenceBindingV2] = []
    caps = worker.V075WorkerCapProfileV1()
    for row_id in sorted(by_row):
        batches = by_row[row_id]
        discoveries = tuple(
            item
            for item in batches
            if item.request.stream_identity.lane.value == "DISCOVERY"
        )
        validations = tuple(
            item
            for item in batches
            if item.request.stream_identity.lane.value == "VALIDATION"
        )
        if not discoveries or not validations:
            _fail("every V2 planning row requires discovery and validation")
        validation_epochs = {
            item.request.stream_identity.observer_epoch_index
            for item in validations
        }
        if validation_epochs != {1}:
            _fail(
                "V2 official profile forbids independent validation epochs; "
                "all prefix extensions must remain on epoch 1"
            )
        latest_epoch = 1
        latest = tuple(
            sorted(
                (
                    item
                    for item in validations
                    if item.request.stream_identity.observer_epoch_index
                    == latest_epoch
                ),
                key=lambda item: item.request.accepted_draw_start,
            )
        )
        if len(
            {item.request.stream_identity.stream_id for item in latest}
        ) != 1:
            _fail("latest V2 validation epoch has multiple streams")
        expected_start = 1
        validation_cap = None
        for batch in latest:
            if batch.request.accepted_draw_start != expected_start:
                _fail("latest V2 validation prefix is gapped or reordered")
            expected_start = batch.request.accepted_draw_end + 1
            if validation_cap is None:
                validation_cap = batch.request.accepted_draw_cap
            elif validation_cap != batch.request.accepted_draw_cap:
                _fail("latest V2 validation prefix changed its cap")
        draw_count = expected_start - 1
        row_binding = latest[0].request.stream_identity.row_binding
        if any(
            item.request.stream_identity.row_binding != row_binding
            for item in (*discoveries, *latest)
        ):
            _fail("V2 row batches mix typed row bindings")
        checkpoints = _allowed_checkpoints(
            arm=lineage.occurrence_identity.arm,
            remaining_horizon=row_binding.remaining_horizon,
            caps=caps,
        )
        if draw_count not in checkpoints:
            _fail("latest validation prefix is not registered")
        freezes = tuple(freezes_by_row.get(row_id, ()))
        if (
            len(freezes) != 1
            or freezes[0].validation_epoch_index != latest_epoch
        ):
            _fail(
                "V2 row must retain exactly one epoch-1 support freeze"
            )
        freeze = freezes[0]
        support_evidence = tuple(
            evidence_by_id[item]
            for item in freeze.support_evidence_ids
        )
        if not support_evidence:
            _fail("V2 frozen support is empty")
        descriptors_by_key: dict[
            tuple[tuple[int, ...], bool, bool],
            V075SupportDescriptorV2,
        ] = {}
        for item in support_evidence:
            state = _structural_state(
                row_binding,
                next_ranks=item.next_ranks,
                failure=item.failure,
                terminal=item.terminal,
            )
            key = (item.next_ranks, item.failure, item.terminal)
            descriptor = V075SupportDescriptorV2(
                _DESCRIPTOR_ISSUER,
                row_binding.context_id,
                state.state_id,
                item.next_ranks,
                item.failure,
                item.terminal,
            )
            descriptors_by_key[key] = descriptor
            accounting_runtime.emit_owned_operation_v1(
                "batch-planning.aggregate.support-descriptor.compile"
            )
        support = tuple(
            sorted(
                descriptors_by_key.values(),
                key=lambda item: item.descriptor_id,
            )
        )
        counts = {item.descriptor_id: 0 for item in support}
        by_key = {
            (item.next_ranks, item.failure, item.terminal): item
            for item in support
        }
        other = 0
        reward = _merge_reward(row_binding)
        for batch in latest:
            for outcome in batch.outcomes:
                if (
                    outcome.realized_row_reward != reward
                    or outcome.reward_sum != reward * outcome.count
                ):
                    _fail("V2 aggregate reward differs from structural reward")
                _structural_state(
                    row_binding,
                    next_ranks=outcome.next_ranks,
                    failure=outcome.failure,
                    terminal=outcome.terminal,
                )
                descriptor = by_key.get(
                    (
                        outcome.next_ranks,
                        outcome.failure,
                        outcome.terminal,
                    )
                )
                if descriptor is None:
                    other += outcome.count
                else:
                    counts[descriptor.descriptor_id] += outcome.count
                accounting_runtime.emit_owned_operation_v1(
                    "batch-planning.aggregate.outcome-projection"
                )
        if sum(counts.values()) + other != draw_count:
            _fail("V2 support-plus-OTHER does not conserve validation draws")
        event_count = len(support) + 1
        intervals = tuple(
            _checkpoint_interval(
                descriptor=descriptor,
                draw_count=draw_count,
                success_count=counts[descriptor.descriptor_id],
                event_count=event_count,
                checkpoints=checkpoints,
            )
            for descriptor in support
        ) + (
            _checkpoint_interval(
                descriptor=None,
                draw_count=draw_count,
                success_count=other,
                event_count=event_count,
                checkpoints=checkpoints,
            ),
        )
        numerical = V075NumericalRowV2(
            _ROW_ISSUER,
            row_binding.context_id,
            row_binding.row_binding_id,
            row_binding.state_id,
            row_binding.catalogue.state.ranks,
            row_binding.remaining_horizon,
            row_binding.action,
            reward,
            support,
            intervals,
        )
        rows.append(numerical)
        accounting_runtime.emit_owned_operation_v1(
            "batch-planning.aggregate.model-row.build"
        )
        binding = V075RowEvidenceBindingV2(
            _EVIDENCE_ISSUER,
            numerical.row_id,
            row_id,
            freeze.freeze_id,
            tuple(sorted(freeze.source_discovery_batch_ids)),
            tuple(sorted(item.batch_id for item in latest)),
            latest_epoch,
            lifecycle.closure_id,
        )
        bindings.append(binding)
        accounting_runtime.emit_owned_operation_v1(
            "batch-planning.aggregate.row-evidence-binding.build"
        )
    canonical_rows = tuple(sorted(rows, key=lambda item: item.row_id))
    binding_by_row = {item.numerical_row_id: item for item in bindings}
    return (
        canonical_rows,
        tuple(binding_by_row[item.row_id] for item in canonical_rows),
    )


def compile_v075_construction_planning_input_v2(
    *,
    repository_root: str | Path,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    lifecycle: lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2,
) -> V075ConstructionPlanningInputV2:
    """Replay schedule, aggregate lineage, and lifecycle before compilation."""

    lineage = _replay_construction_lineage(lineage)
    namespace = lineage.closure.authority_binding.namespace
    try:
        schedule = acquisition_v2.replay_v075_initial_acquisition_schedule_v2(
            repository_root=repository_root,
            namespace=namespace,
            claimed=schedule,
        )
    except Exception as error:
        raise V075BatchNativePlanningV2InvariantViolation(
            "V2 initial schedule exact replay failed"
        ) from error
    streams = tuple(
        sorted(
            {
                item.request.stream_identity.stream_id: (
                    item.request.stream_identity
                )
                for item in lineage.batches
            }.values(),
            key=lambda item: item.stream_id,
        )
    )
    try:
        replayed_lifecycle, verification = (
            lifecycle_v2.verify_v075_batch_occurrence_lifecycle_bytes_v2(
                lifecycle_bytes=lifecycle.canonical_bytes,
                lineage_bytes=lineage.canonical_bytes,
                batch_closure_bytes=lineage.closure.canonical_bytes,
                known_stream_identities=streams,
            )
        )
    except Exception as error:
        raise V075BatchNativePlanningV2InvariantViolation(
            "V2 construction lifecycle exact byte replay failed"
        ) from error
    identity = lineage.occurrence_identity
    root_discovery_rows = tuple(
        sorted(
            item.row_binding.row_binding_id
            for item in schedule.intents
            if item.kind
            is acquisition_v2.V075InitialIntentKindV2.ROOT_DISCOVERY
        )
    )
    required_rows = set(replayed_lifecycle.required_row_binding_ids)
    if (
        schedule.occurrence.occurrence_id != identity.occurrence_id
        or schedule.occurrence.arm is not identity.arm
        or replayed_lifecycle.occurrence_id != identity.occurrence_id
        or replayed_lifecycle.target_tape_namespace_id
        != identity.target_tape_namespace_id
        or replayed_lifecycle.context_id != identity.context_id
        or replayed_lifecycle.arm != identity.arm.value
        or not set(root_discovery_rows) <= required_rows
    ):
        _fail("V2 schedule, lineage, lifecycle, or root rows are transplanted")
    rows, evidence = _compile_aggregate_rows(
        lineage=lineage,
        lifecycle=replayed_lifecycle,
    )
    context = _registered_context(identity.context_id)
    model = V075NumericalModelV2(
        _MODEL_ISSUER,
        context,
        rows,
        "SIGNED_V2_AGGREGATES",
    )
    route = (
        V075PlanningRouteV2.MATCHED_DIRECT_GROUND
        if identity.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        else V075PlanningRouteV2.ADAPTIVE_QUOTIENT
    )
    return V075ConstructionPlanningInputV2(
        _INPUT_ISSUER,
        schedule.schedule_id,
        lineage.lineage_id,
        replayed_lifecycle.closure_id,
        verification.verification_id,
        identity.occurrence_id,
        identity.target_tape_namespace_id,
        identity.arm,
        route,
        model,
        evidence,
    )


class V075DestinationKindV2(str, Enum):
    CHILD_DOMAIN = "CHILD_DOMAIN"
    ENVIRONMENT_FAILURE = "ENVIRONMENT_FAILURE"
    SAFE_HORIZON_END = "SAFE_HORIZON_END"
    POLICY_ABORT_OTHER = "POLICY_ABORT_OTHER"


@dataclass(frozen=True, slots=True)
class V075BehaviorTermV2:
    destination_kind: V075DestinationKindV2
    destination_id: str | None
    immediate_reward: Fraction
    lower_probability: Fraction
    upper_probability: Fraction

    def __post_init__(self) -> None:
        if (
            type(self.destination_kind) is not V075DestinationKindV2
            or type(self.immediate_reward) is not Fraction
            or self.immediate_reward < 0
            or type(self.lower_probability) is not Fraction
            or type(self.upper_probability) is not Fraction
            or not 0 <= self.lower_probability <= self.upper_probability <= 1
            or (
                self.destination_kind is V075DestinationKindV2.CHILD_DOMAIN
            )
            != (self.destination_id is not None)
        ):
            _fail("V2 behavior term is malformed")
        if self.destination_id is not None:
            _cid(self.destination_id, "behavior destination")

    def to_document(self) -> dict[str, Any]:
        return {
            "destination_kind": self.destination_kind.value,
            "destination_id": self.destination_id,
            "immediate_reward": _fdoc(self.immediate_reward),
            "lower_probability": _fdoc(self.lower_probability),
            "upper_probability": _fdoc(self.upper_probability),
        }


_BEHAVIOR_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075RowBehaviorV2:
    _issuer: object = field(repr=False, compare=False)
    row_id: str
    remaining_horizon: int
    terms: tuple[V075BehaviorTermV2, ...]
    _behavior_key: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.row_id, "row behavior row")
        if (
            self._issuer is not _BEHAVIOR_ISSUER
            or self.remaining_horizon not in (1, 2)
            or type(self.terms) is not tuple
            or not self.terms
            or any(type(item) is not V075BehaviorTermV2 for item in self.terms)
            or tuple(
                canonical_json_bytes(item.to_document()) for item in self.terms
            )
            != tuple(
                sorted(
                    canonical_json_bytes(item.to_document())
                    for item in self.terms
                )
            )
            or sum(
                (item.lower_probability for item in self.terms),
                Fraction(0),
            )
            > 1
            or sum(
                (item.upper_probability for item in self.terms),
                Fraction(0),
            )
            < 1
            or sum(
                item.destination_kind
                is V075DestinationKindV2.POLICY_ABORT_OTHER
                for item in self.terms
            )
            != 1
        ):
            _fail("V2 row behavior is malformed or caller-minted")
        object.__setattr__(
            self,
            "_behavior_key",
            _hash("behavior", self._semantic_payload()),
        )

    def _semantic_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_row_behavior.v2",
            "schema_version": SCHEMA_VERSION,
            "remaining_horizon": self.remaining_horizon,
            "terms": [item.to_document() for item in self.terms],
            "selected_policy_other_rule": POLICY_ABORT_RULE,
            "interval_simplex_retained": True,
        }

    @property
    def behavior_key(self) -> str:
        return self._behavior_key

    def to_document(self) -> dict[str, Any]:
        return {
            **self._semantic_payload(),
            "row_id": self.row_id,
            "behavior_key": self.behavior_key,
        }


_CELL_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075QuotientCellV2:
    _issuer: object = field(repr=False, compare=False)
    remaining_horizon: int
    state_ids: tuple[str, ...]
    behavior_keys: tuple[str, ...]
    _cell_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _CELL_ISSUER
            or self.remaining_horizon not in (1, 2)
            or self.state_ids != tuple(sorted(set(self.state_ids)))
            or not self.state_ids
            or self.behavior_keys != tuple(sorted(set(self.behavior_keys)))
            or not self.behavior_keys
        ):
            _fail("V2 quotient cell is malformed or caller-minted")
        for value in (*self.state_ids, *self.behavior_keys):
            _cid(value, "quotient cell member")
        object.__setattr__(self, "_cell_id", _hash("cell", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_quotient_cell.v2",
            "schema_version": SCHEMA_VERSION,
            "remaining_horizon": self.remaining_horizon,
            "state_ids": list(self.state_ids),
            "behavior_keys": list(self.behavior_keys),
            "partition_basis": "EXACT_INTERVAL_BEHAVIOR_SIGNATURE",
        }

    @property
    def cell_id(self) -> str:
        return self._cell_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cell_id": self.cell_id}


_QUOTIENT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BehavioralQuotientV2:
    _issuer: object = field(repr=False, compare=False)
    numerical_model_id: str
    row_behaviors: tuple[V075RowBehaviorV2, ...]
    cells: tuple[V075QuotientCellV2, ...]
    _quotient_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.numerical_model_id, "quotient model")
        if (
            self._issuer is not _QUOTIENT_ISSUER
            or self.row_behaviors
            != tuple(sorted(self.row_behaviors, key=lambda item: item.row_id))
            or self.cells
            != tuple(sorted(self.cells, key=lambda item: item.cell_id))
            or not self.cells
        ):
            _fail("V2 behavioral quotient is malformed")
        object.__setattr__(
            self,
            "_quotient_id",
            _hash("quotient", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_behavioral_quotient.v2",
            "schema_version": SCHEMA_VERSION,
            "numerical_model_id": self.numerical_model_id,
            "row_behavior_bindings": [
                {
                    "row_id": item.row_id,
                    "behavior_key": item.behavior_key,
                }
                for item in self.row_behaviors
            ],
            "cell_ids": [item.cell_id for item in self.cells],
            "compiler": "BOTTOM_UP_H2_EXACT_INTERVAL_BEHAVIOR_V2",
            "fixed_uniform_distinct_action_concretizer": True,
            "known_automorphism_used": False,
            "human_partition_used": False,
            "prior_or_proposal_access": False,
        }

    @property
    def quotient_id(self) -> str:
        return self._quotient_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_behaviors": [
                item.to_document() for item in self.row_behaviors
            ],
            "cells": [item.to_document() for item in self.cells],
            "quotient_id": self.quotient_id,
        }


@dataclass(frozen=True, slots=True)
class V075PolicyStateChoiceV2:
    state_id: str
    ground_actions: tuple[tuple[int, int, int], ...]
    row_ids: tuple[str, ...]
    uniform_weights: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        _cid(self.state_id, "policy state")
        if (
            self.ground_actions
            != tuple(sorted(set(self.ground_actions)))
            or not self.ground_actions
            or len(self.row_ids) != len(self.ground_actions)
            or len(set(self.row_ids)) != len(self.row_ids)
            or self.uniform_weights
            != tuple(
                Fraction(1, len(self.ground_actions))
                for _item in self.ground_actions
            )
        ):
            _fail("V2 policy state choice is not one fixed concretizer")
        for action in self.ground_actions:
            _action(action)
        for row_id in self.row_ids:
            _cid(row_id, "policy row")

    def to_document(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "ground_actions": [list(item) for item in self.ground_actions],
            "row_ids": list(self.row_ids),
            "uniform_weights": [_fdoc(item) for item in self.uniform_weights],
            "distinct_actions_deduplicated_before_weighting": True,
        }


@dataclass(frozen=True, slots=True)
class V075PolicyDecisionV2:
    remaining_horizon: int
    decision_domain_id: str
    selected_option_id: str
    state_choices: tuple[V075PolicyStateChoiceV2, ...]

    def __post_init__(self) -> None:
        _cid(self.decision_domain_id, "policy decision domain")
        _cid(self.selected_option_id, "policy option")
        if (
            self.remaining_horizon not in (1, 2)
            or self.state_choices
            != tuple(sorted(self.state_choices, key=lambda item: item.state_id))
            or not self.state_choices
        ):
            _fail("V2 policy decision is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "remaining_horizon": self.remaining_horizon,
            "decision_domain_id": self.decision_domain_id,
            "selected_option_id": self.selected_option_id,
            "state_choices": [
                item.to_document() for item in self.state_choices
            ],
        }


_POLICY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075DeterministicPolicyV2:
    _issuer: object = field(repr=False, compare=False)
    numerical_model_id: str
    route: V075PlanningRouteV2
    quotient_id: str | None
    decisions: tuple[V075PolicyDecisionV2, ...]
    _policy_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.numerical_model_id, "policy model")
        if self.quotient_id is not None:
            _cid(self.quotient_id, "policy quotient")
        if (
            self._issuer is not _POLICY_ISSUER
            or type(self.route) is not V075PlanningRouteV2
            or (
                self.route is V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            )
            != (self.quotient_id is not None)
            or self.decisions
            != tuple(
                sorted(
                    self.decisions,
                    key=lambda item: (
                        -item.remaining_horizon,
                        item.decision_domain_id,
                    ),
                )
            )
            or sum(item.remaining_horizon == 2 for item in self.decisions) != 1
        ):
            _fail("V2 deterministic policy is malformed")
        if self.route is V075PlanningRouteV2.MATCHED_DIRECT_GROUND and any(
            len(choice.ground_actions) != 1
            for decision in self.decisions
            for choice in decision.state_choices
        ):
            _fail("direct V2 policy is not deterministic ground selection")
        object.__setattr__(self, "_policy_id", _hash("policy", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_policy.v2",
            "schema_version": SCHEMA_VERSION,
            "numerical_model_id": self.numerical_model_id,
            "route": self.route.value,
            "quotient_id": self.quotient_id,
            "decisions": [item.to_document() for item in self.decisions],
            "deterministic_finite_horizon_markov_selector": True,
            "fixed_concretizer_is_not_policy_randomization": True,
            "policy_abort_rule": POLICY_ABORT_RULE,
        }

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "policy_id": self.policy_id}


_ENVELOPE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075RobustEnvelopeV2:
    _issuer: object = field(repr=False, compare=False)
    policy_id: str
    selected_reward_lower: Fraction
    selected_reward_upper: Fraction
    selected_failure_upper: Fraction
    unrestricted_ground_reward_upper: Fraction
    normalized_regret_upper: Fraction
    _envelope_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.policy_id, "envelope policy")
        values = (
            self.selected_reward_lower,
            self.selected_reward_upper,
            self.selected_failure_upper,
            self.unrestricted_ground_reward_upper,
            self.normalized_regret_upper,
        )
        if (
            self._issuer is not _ENVELOPE_ISSUER
            or any(type(item) is not Fraction for item in values)
            or not 0
            <= self.selected_reward_lower
            <= self.selected_reward_upper
            <= self.unrestricted_ground_reward_upper
            or not 0 <= self.selected_failure_upper <= 1
            or self.normalized_regret_upper
            != (
                self.unrestricted_ground_reward_upper
                - self.selected_reward_lower
            )
            / worker.V075WorkerThresholdProfileV1().reward_ceiling
        ):
            _fail("V2 robust envelope is malformed")
        object.__setattr__(
            self,
            "_envelope_id",
            _hash("envelope", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_envelope.v2",
            "schema_version": SCHEMA_VERSION,
            "policy_id": self.policy_id,
            "selected_reward_lower": _fdoc(self.selected_reward_lower),
            "selected_reward_upper": _fdoc(self.selected_reward_upper),
            "selected_failure_upper": _fdoc(self.selected_failure_upper),
            "unrestricted_ground_reward_upper": _fdoc(
                self.unrestricted_ground_reward_upper
            ),
            "normalized_regret_upper": _fdoc(
                self.normalized_regret_upper
            ),
            "familywise_confidence_error_upper": _fdoc(
                FAMILYWISE_CONFIDENCE_ERROR_UPPER
            ),
            "selected_policy_other_rule": POLICY_ABORT_RULE,
            "ground_comparator_unresolved_rule": COMPARATOR_RULE,
            "ground_comparator_is_unconstrained_reward_upper": True,
            "probability_simplex_enforced": True,
        }

    @property
    def envelope_id(self) -> str:
        return self._envelope_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "envelope_id": self.envelope_id}


@dataclass(frozen=True, slots=True)
class V075FrontierObligationV2:
    row_id: str
    interval_width_sum: Fraction
    other_upper: Fraction
    unmaterialized_successor_ids: tuple[str, ...]
    current_validation_draw_count: int
    next_registered_checkpoint: int | None

    def __post_init__(self) -> None:
        _cid(self.row_id, "frontier row")
        for value in self.unmaterialized_successor_ids:
            _cid(value, "frontier successor")
        if (
            type(self.interval_width_sum) is not Fraction
            or self.interval_width_sum < 0
            or type(self.other_upper) is not Fraction
            or not 0 <= self.other_upper <= 1
            or self.unmaterialized_successor_ids
            != tuple(sorted(set(self.unmaterialized_successor_ids)))
            or type(self.current_validation_draw_count) is not int
            or self.current_validation_draw_count <= 0
            or (
                self.next_registered_checkpoint is not None
                and (
                    type(self.next_registered_checkpoint) is not int
                    or self.next_registered_checkpoint
                    <= self.current_validation_draw_count
                )
            )
        ):
            _fail("V2 frontier obligation is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "interval_width_sum": _fdoc(self.interval_width_sum),
            "other_upper": _fdoc(self.other_upper),
            "unmaterialized_successor_ids": list(
                self.unmaterialized_successor_ids
            ),
            "current_validation_draw_count": (
                self.current_validation_draw_count
            ),
            "next_registered_checkpoint": self.next_registered_checkpoint,
        }


_FRONTIER_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075FailedProofFrontierV2:
    _issuer: object = field(repr=False, compare=False)
    numerical_model_id: str
    reason: V075FailedProofReasonV2
    obligations: tuple[V075FrontierObligationV2, ...]
    _frontier_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.numerical_model_id, "frontier model")
        if (
            self._issuer is not _FRONTIER_ISSUER
            or type(self.reason) is not V075FailedProofReasonV2
            or type(self.obligations) is not tuple
            or not self.obligations
            or tuple(item.row_id for item in self.obligations)
            != tuple(sorted({item.row_id for item in self.obligations}))
        ):
            _fail("V2 failed frontier is malformed")
        object.__setattr__(
            self,
            "_frontier_id",
            _hash("frontier", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_failed_frontier.v2",
            "schema_version": SCHEMA_VERSION,
            "numerical_model_id": self.numerical_model_id,
            "reason": self.reason.value,
            "obligations": [
                item.to_document() for item in self.obligations
            ],
            "prior_rank_present": False,
            "infeasibility_certificate": False,
            "plan_certificate": False,
        }

    @property
    def frontier_id(self) -> str:
        return self._frontier_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "frontier_id": self.frontier_id}


_PROOF_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075NumericalPlanningProofV2:
    _issuer: object = field(repr=False, compare=False)
    model: V075NumericalModelV2
    route: V075PlanningRouteV2
    quotient: V075BehavioralQuotientV2 | None
    outcome: V075NumericalOutcomeV2
    policy: V075DeterministicPolicyV2 | None
    envelope: V075RobustEnvelopeV2 | None
    failed_frontier: V075FailedProofFrontierV2 | None
    policy_assignments_evaluated: int
    _proof_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        adaptive = self.route is V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        candidate = self.outcome is V075NumericalOutcomeV2.CANDIDATE
        if (
            self._issuer is not _PROOF_ISSUER
            or type(self.model) is not V075NumericalModelV2
            or type(self.route) is not V075PlanningRouteV2
            or type(self.outcome) is not V075NumericalOutcomeV2
            or adaptive
            != (
                type(self.quotient) is V075BehavioralQuotientV2
                and self.quotient.numerical_model_id == self.model.model_id
            )
            or candidate
            != (
                type(self.policy) is V075DeterministicPolicyV2
                and type(self.envelope) is V075RobustEnvelopeV2
                and self.failed_frontier is None
            )
            or (not candidate)
            != (
                type(self.failed_frontier) is V075FailedProofFrontierV2
            )
            or type(self.policy_assignments_evaluated) is not int
            or not 0
            <= self.policy_assignments_evaluated
            <= MAX_EXACT_POLICY_ASSIGNMENTS
        ):
            _fail("V2 numerical planning proof is malformed")
        if self.policy is not None and (
            self.policy.numerical_model_id != self.model.model_id
            or self.policy.route is not self.route
            or self.envelope is None
            or self.envelope.policy_id != self.policy.policy_id
        ):
            _fail("V2 proof policy/envelope identity graph changed")
        if self.failed_frontier is not None and (
            self.failed_frontier.numerical_model_id != self.model.model_id
        ):
            _fail("V2 proof frontier was transplanted")
        object.__setattr__(self, "_proof_id", _hash("proof", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_numerical_proof.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "numerical_model_id": self.model.model_id,
            "route": self.route.value,
            "quotient_id": (
                None if self.quotient is None else self.quotient.quotient_id
            ),
            "outcome": self.outcome.value,
            "policy_id": None if self.policy is None else self.policy.policy_id,
            "envelope_id": (
                None if self.envelope is None else self.envelope.envelope_id
            ),
            "failed_frontier_id": (
                None
                if self.failed_frontier is None
                else self.failed_frontier.frontier_id
            ),
            "policy_assignments_evaluated": (
                self.policy_assignments_evaluated
            ),
            "search_cap": MAX_EXACT_POLICY_ASSIGNMENTS,
            "arm_field_present": False,
            "proposal_field_present": False,
            "source_provenance_field_present": False,
            "occurrence_field_present": False,
            "private_law_access": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def proof_id(self) -> str:
        return self._proof_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "model": self.model.to_document(),
            "quotient": (
                None if self.quotient is None else self.quotient.to_document()
            ),
            "policy": None if self.policy is None else self.policy.to_document(),
            "envelope": (
                None
                if self.envelope is None
                else self.envelope.to_document()
            ),
            "failed_frontier": (
                None
                if self.failed_frontier is None
                else self.failed_frontier.to_document()
            ),
            "proof_id": self.proof_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPlanningResultV2:
    _issuer: object = field(repr=False, compare=False)
    planning_input: V075ConstructionPlanningInputV2
    numerical_proof: V075NumericalPlanningProofV2
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _RESULT_ISSUER
            or type(self.planning_input) is not V075ConstructionPlanningInputV2
            or type(self.numerical_proof) is not V075NumericalPlanningProofV2
            or self.numerical_proof.model != self.planning_input.model
            or self.numerical_proof.route is not self.planning_input.route
        ):
            _fail("V2 construction planning result is malformed")
        object.__setattr__(self, "_result_id", _hash("result", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_construction_result.v2",
            "schema_version": SCHEMA_VERSION,
            "scope": "CONSTRUCTION_ONLY",
            "planning_input_id": self.planning_input.input_id,
            "occurrence_id": self.planning_input.occurrence_id,
            "target_tape_namespace_id": (
                self.planning_input.target_tape_namespace_id
            ),
            "arm": self.planning_input.arm.value,
            "route": self.planning_input.route.value,
            "schedule_id": self.planning_input.schedule_id,
            "lineage_id": self.planning_input.lineage_id,
            "lifecycle_closure_id": (
                self.planning_input.lifecycle_closure_id
            ),
            "numerical_proof_id": self.numerical_proof.proof_id,
            "numerical_proof_prior_free": True,
            "occurrence_provenance_bound_only_in_wrapper": True,
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "planning_input": self.planning_input.to_document(),
            "numerical_proof": self.numerical_proof.to_document(),
            "result_id": self.result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


@dataclass(frozen=True, slots=True)
class _Metric:
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction


@dataclass(frozen=True, slots=True)
class _Option:
    option_id: str
    domain_id: str
    remaining_horizon: int
    rows_by_state: tuple[tuple[str, tuple[V075NumericalRowV2, ...]], ...]


def _extreme(
    intervals: tuple[V075EventIntervalV2, ...],
    values: tuple[Fraction, ...],
    *,
    maximize: bool,
) -> Fraction:
    if len(intervals) != len(values) or not intervals:
        _fail("V2 interval objective is malformed")
    lower = [item.lower_probability for item in intervals]
    upper = [item.upper_probability for item in intervals]
    residual = Fraction(1) - sum(lower, Fraction(0))
    if residual < 0 or sum(upper, Fraction(0)) < 1:
        _fail("V2 interval simplex is empty")
    order = sorted(
        range(len(intervals)),
        key=lambda index: (
            values[index],
            intervals[index].event_key,
        ),
        reverse=maximize,
    )
    probabilities = list(lower)
    for index in order:
        addition = min(residual, upper[index] - lower[index])
        probabilities[index] += addition
        residual -= addition
        accounting_runtime.emit_owned_operation_v1(
            "batch-planning.interval-greedy.extreme"
        )
        if residual == 0:
            break
    if residual != 0:
        _fail("V2 exact interval extreme failed simplex closure")
    return sum(
        (
            probability * value
            for probability, value in zip(probabilities, values)
        ),
        Fraction(0),
    )


def _row_behavior(
    row: V075NumericalRowV2,
    *,
    child_domain_by_state: Mapping[str, str],
) -> V075RowBehaviorV2:
    terms: list[V075BehaviorTermV2] = []
    interval_by_key = {item.event_key: item for item in row.intervals}
    for descriptor in row.support:
        interval = interval_by_key[descriptor.descriptor_id]
        if descriptor.failure:
            kind = V075DestinationKindV2.ENVIRONMENT_FAILURE
            destination = None
        elif row.remaining_horizon == 1:
            kind = V075DestinationKindV2.SAFE_HORIZON_END
            destination = None
        elif descriptor.next_state_id in child_domain_by_state:
            kind = V075DestinationKindV2.CHILD_DOMAIN
            destination = child_domain_by_state[descriptor.next_state_id]
        else:
            kind = V075DestinationKindV2.POLICY_ABORT_OTHER
            destination = None
        terms.append(
            V075BehaviorTermV2(
                kind,
                destination,
                row.immediate_reward,
                interval.lower_probability,
                interval.upper_probability,
            )
        )
    other = interval_by_key["OTHER"]
    terms.append(
        V075BehaviorTermV2(
            V075DestinationKindV2.POLICY_ABORT_OTHER,
            None,
            row.immediate_reward,
            other.lower_probability,
            other.upper_probability,
        )
    )
    # Multiple abort destinations are one semantic event.
    grouped: dict[
        tuple[V075DestinationKindV2, str | None, Fraction],
        tuple[Fraction, Fraction],
    ] = {}
    for term in terms:
        key = (
            term.destination_kind,
            term.destination_id,
            term.immediate_reward,
        )
        lower, upper = grouped.get(key, (Fraction(0), Fraction(0)))
        grouped[key] = (
            lower + term.lower_probability,
            min(Fraction(1), upper + term.upper_probability),
        )
    canonical = tuple(
        sorted(
            (
                V075BehaviorTermV2(
                    kind,
                    destination,
                    reward,
                    bounds[0],
                    bounds[1],
                )
                for (kind, destination, reward), bounds in grouped.items()
            ),
            key=lambda item: canonical_json_bytes(item.to_document()),
        )
    )
    behavior = V075RowBehaviorV2(
        _BEHAVIOR_ISSUER,
        row.row_id,
        row.remaining_horizon,
        canonical,
    )
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.row-behavior.compile"
    )
    return behavior


def _compile_quotient(
    model: V075NumericalModelV2,
) -> V075BehavioralQuotientV2:
    rows_by_state: dict[str, tuple[V075NumericalRowV2, ...]] = {}
    for row in model.rows:
        rows_by_state.setdefault(row.source_state_id, ())
        rows_by_state[row.source_state_id] = (
            *rows_by_state[row.source_state_id],
            row,
        )
    child_states = tuple(
        sorted(
            state_id
            for state_id, rows in rows_by_state.items()
            if rows[0].remaining_horizon == 1
        )
    )
    child_behaviors = {
        row.row_id: _row_behavior(row, child_domain_by_state={})
        for state_id in child_states
        for row in rows_by_state[state_id]
    }
    signatures: dict[tuple[str, ...], list[str]] = {}
    for state_id in child_states:
        signature = tuple(
            sorted(
                {
                    child_behaviors[row.row_id].behavior_key
                    for row in rows_by_state[state_id]
                }
            )
        )
        signatures.setdefault(signature, []).append(state_id)
    child_cell_values = []
    for signature, states in sorted(signatures.items()):
        cell = V075QuotientCellV2(
            _CELL_ISSUER,
            1,
            tuple(sorted(states)),
            signature,
        )
        child_cell_values.append(cell)
        accounting_runtime.emit_owned_operation_v1(
            "batch-planning.quotient-cell.compile"
        )
    child_cells = tuple(child_cell_values)
    child_cell_by_state = {
        state_id: cell.cell_id
        for cell in child_cells
        for state_id in cell.state_ids
    }
    root_rows = tuple(
        row for row in model.rows if row.remaining_horizon == 2
    )
    root_behaviors = {
        row.row_id: _row_behavior(
            row,
            child_domain_by_state=child_cell_by_state,
        )
        for row in root_rows
    }
    root_state_ids = tuple(sorted({row.source_state_id for row in root_rows}))
    root_cell = V075QuotientCellV2(
        _CELL_ISSUER,
        2,
        root_state_ids,
        tuple(
            sorted({item.behavior_key for item in root_behaviors.values()})
        ),
    )
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.quotient-cell.compile"
    )
    return V075BehavioralQuotientV2(
        _QUOTIENT_ISSUER,
        model.model_id,
        tuple(
            sorted(
                (*child_behaviors.values(), *root_behaviors.values()),
                key=lambda item: item.row_id,
            )
        ),
        tuple(
            sorted((*child_cells, root_cell), key=lambda item: item.cell_id)
        ),
    )


def _direct_behaviors(
    model: V075NumericalModelV2,
) -> tuple[V075RowBehaviorV2, ...]:
    child_states = {
        row.source_state_id
        for row in model.rows
        if row.remaining_horizon == 1
    }
    return tuple(
        sorted(
            (
                _row_behavior(
                    row,
                    child_domain_by_state={
                        state_id: state_id for state_id in child_states
                    },
                )
                for row in model.rows
            ),
            key=lambda item: item.row_id,
        )
    )


def _options(
    *,
    model: V075NumericalModelV2,
    route: V075PlanningRouteV2,
    quotient: V075BehavioralQuotientV2 | None,
    remaining_horizon: int,
) -> tuple[_Option, ...]:
    rows_by_state: dict[str, tuple[V075NumericalRowV2, ...]] = {}
    for row in model.rows:
        if row.remaining_horizon == remaining_horizon:
            rows_by_state.setdefault(row.source_state_id, ())
            rows_by_state[row.source_state_id] = (
                *rows_by_state[row.source_state_id],
                row,
            )
    if route is V075PlanningRouteV2.MATCHED_DIRECT_GROUND:
        direct_options = []
        for state_id, rows in rows_by_state.items():
            for row in rows:
                option = _Option(
                    row.row_id,
                    state_id,
                    remaining_horizon,
                    ((state_id, (row,)),),
                )
                direct_options.append(option)
                accounting_runtime.emit_owned_operation_v1(
                    "batch-planning.semantic-option.compile"
                )
                accounting_runtime.emit_owned_operation_v1(
                    "batch-planning.concretizer-ground-action.bind"
                )
        return tuple(
            sorted(
                direct_options,
                key=lambda item: item.option_id,
            )
        )
    assert quotient is not None
    behaviors = {item.row_id: item for item in quotient.row_behaviors}
    options = []
    for cell in quotient.cells:
        if cell.remaining_horizon != remaining_horizon:
            continue
        for behavior_key in cell.behavior_keys:
            rows_per_state = []
            for state_id in cell.state_ids:
                rows = tuple(
                    sorted(
                        (
                            row
                            for row in rows_by_state[state_id]
                            if behaviors[row.row_id].behavior_key
                            == behavior_key
                        ),
                        key=lambda item: item.action,
                    )
                )
                if not rows:
                    _fail("V2 quotient semantic action is not representative complete")
                rows_per_state.append((state_id, rows))
            option_id = _hash(
                "behavior",
                {
                    "schema": "acfqp.v075_batch_planning_semantic_option.v2",
                    "schema_version": SCHEMA_VERSION,
                    "cell_id": cell.cell_id,
                    "behavior_key": behavior_key,
                },
            )
            option = _Option(
                option_id,
                cell.cell_id,
                remaining_horizon,
                tuple(rows_per_state),
            )
            options.append(option)
            accounting_runtime.emit_owned_operation_v1(
                "batch-planning.semantic-option.compile"
            )
            for _state_id, rows in option.rows_by_state:
                for _row in rows:
                    accounting_runtime.emit_owned_operation_v1(
                        "batch-planning.concretizer-ground-action.bind"
                    )
    return tuple(sorted(options, key=lambda item: item.option_id))


def _option_metric(
    option: _Option,
    *,
    behavior_by_row: Mapping[str, V075RowBehaviorV2],
    child_metrics: Mapping[str, _Metric],
) -> _Metric:
    metrics = []
    for _state_id, rows in option.rows_by_state:
        row_metrics = []
        for row in rows:
            behavior = behavior_by_row[row.row_id]
            lower_values = []
            upper_values = []
            failure_values = []
            for term in behavior.terms:
                if term.destination_kind is V075DestinationKindV2.CHILD_DOMAIN:
                    assert term.destination_id is not None
                    child = child_metrics[term.destination_id]
                    lower = child.reward_lower
                    upper = child.reward_upper
                    failure = child.failure_upper
                elif term.destination_kind in {
                    V075DestinationKindV2.ENVIRONMENT_FAILURE,
                    V075DestinationKindV2.POLICY_ABORT_OTHER,
                }:
                    lower = upper = Fraction(0)
                    failure = Fraction(1)
                else:
                    lower = upper = Fraction(0)
                    failure = Fraction(0)
                lower_values.append(term.immediate_reward + lower)
                upper_values.append(term.immediate_reward + upper)
                failure_values.append(failure)
            # Behavioral terms are already an aggregated interval partition.
            # Use the same exact greedy simplex on their lightweight bounds.
            bounds = tuple(
                (term.lower_probability, term.upper_probability)
                for term in behavior.terms
            )
            row_metrics.append(
                _Metric(
                    _extreme_bounds(bounds, tuple(lower_values), maximize=False),
                    _extreme_bounds(bounds, tuple(upper_values), maximize=True),
                    _extreme_bounds(bounds, tuple(failure_values), maximize=True),
                )
            )
        if any(item != row_metrics[0] for item in row_metrics[1:]):
            _fail("uniform concretizer rows do not have identical metrics")
        metrics.append(row_metrics[0])
    if any(item != metrics[0] for item in metrics[1:]):
        _fail("semantic action is not representative independent")
    metric = metrics[0]
    accounting_runtime.emit_owned_operation_v1(
        "batch-planning.option-metric"
    )
    return metric


def _extreme_bounds(
    bounds: tuple[tuple[Fraction, Fraction], ...],
    values: tuple[Fraction, ...],
    *,
    maximize: bool,
) -> Fraction:
    if len(bounds) != len(values) or not bounds:
        _fail("V2 lightweight interval objective is malformed")
    residual = Fraction(1) - sum(
        (item[0] for item in bounds),
        Fraction(0),
    )
    if residual < 0 or sum((item[1] for item in bounds), Fraction(0)) < 1:
        _fail("V2 lightweight interval simplex is empty")
    probabilities = [item[0] for item in bounds]
    order = sorted(
        range(len(bounds)),
        key=lambda index: (values[index], index),
        reverse=maximize,
    )
    for index in order:
        addition = min(residual, bounds[index][1] - bounds[index][0])
        probabilities[index] += addition
        residual -= addition
        accounting_runtime.emit_owned_operation_v1(
            "batch-planning.interval-greedy.extreme-bounds"
        )
        if residual == 0:
            break
    if residual:
        _fail("V2 lightweight interval extreme failed")
    return sum(
        (
            probability * value
            for probability, value in zip(probabilities, values)
        ),
        Fraction(0),
    )


def _decision(option: _Option) -> V075PolicyDecisionV2:
    choices = tuple(
        V075PolicyStateChoiceV2(
            state_id,
            tuple(row.action for row in rows),
            tuple(row.row_id for row in rows),
            tuple(Fraction(1, len(rows)) for _row in rows),
        )
        for state_id, rows in option.rows_by_state
    )
    return V075PolicyDecisionV2(
        option.remaining_horizon,
        option.domain_id,
        option.option_id,
        tuple(sorted(choices, key=lambda item: item.state_id)),
    )


def _unrestricted_ground_reward_upper(
    model: V075NumericalModelV2,
) -> Fraction:
    rows_by_state: dict[str, list[V075NumericalRowV2]] = {}
    for row in model.rows:
        rows_by_state.setdefault(row.source_state_id, []).append(row)
    child_upper = {
        state_id: max(row.immediate_reward for row in rows)
        for state_id, rows in rows_by_state.items()
        if rows[0].remaining_horizon == 1
    }
    ceiling = worker.V075WorkerThresholdProfileV1().reward_ceiling
    result = Fraction(0)
    for row in model.rows:
        if row.remaining_horizon != 2:
            continue
        values = []
        for descriptor in row.support:
            if descriptor.failure:
                values.append(row.immediate_reward)
            elif descriptor.next_state_id in child_upper:
                values.append(
                    row.immediate_reward
                    + child_upper[descriptor.next_state_id]
                )
            else:
                values.append(ceiling)
        # This is deliberately optimistic, unlike selected-policy abort.
        values.append(ceiling)
        upper = _extreme(
            row.intervals,
            tuple(values),
            maximize=True,
        )
        result = max(result, upper)
    return result


def _next_checkpoint(
    row: V075NumericalRowV2,
    route: V075PlanningRouteV2,
) -> int | None:
    caps = worker.V075WorkerCapProfileV1()
    if route is V075PlanningRouteV2.MATCHED_DIRECT_GROUND:
        checkpoints = caps.direct_validation_checkpoints
    else:
        base = (
            caps.initial_validation_draws_per_row
            if row.remaining_horizon == 2
            else caps.new_child_validation_draws_per_row
        )
        checkpoints = tuple(
            base + index * caps.promotion_validation_draws_per_round
            for index in range(caps.maximum_adaptive_rounds + 1)
        )
    return next(
        (
            value
            for value in checkpoints
            if value > row.validation_draw_count
        ),
        None,
    )


def _frontier(
    *,
    model: V075NumericalModelV2,
    route: V075PlanningRouteV2,
    reason: V075FailedProofReasonV2,
    row_ids: Iterable[str],
) -> V075FailedProofFrontierV2:
    selected = set(row_ids)
    materialized = {
        row.source_state_id
        for row in model.rows
        if row.remaining_horizon == 1
    }
    obligations = []
    for row in model.rows:
        if row.row_id not in selected:
            continue
        other = next(
            item for item in row.intervals if item.event_key == "OTHER"
        )
        unmaterialized = tuple(
            sorted(
                {
                    item.next_state_id
                    for item in row.support
                    if (
                        row.remaining_horizon == 2
                        and not item.failure
                        and not item.terminal
                        and item.next_state_id not in materialized
                    )
                }
            )
        )
        obligation = V075FrontierObligationV2(
            row.row_id,
            sum(
                (
                    item.upper_probability - item.lower_probability
                    for item in row.intervals
                ),
                Fraction(0),
            ),
            other.upper_probability,
            unmaterialized,
            row.validation_draw_count,
            _next_checkpoint(row, route),
        )
        obligations.append(obligation)
        accounting_runtime.emit_owned_operation_v1(
            "batch-planning.frontier-obligation.build"
        )
    if not obligations:
        _fail("V2 failed frontier selected no rows")
    return V075FailedProofFrontierV2(
        _FRONTIER_ISSUER,
        model.model_id,
        reason,
        tuple(sorted(obligations, key=lambda item: item.row_id)),
    )


def plan_v075_construction_numerical_model_v2(
    *,
    model: V075NumericalModelV2,
    route: V075PlanningRouteV2,
) -> V075NumericalPlanningProofV2:
    """Solve one prior-free numerical model with exact robust arithmetic."""

    if (
        type(model) is not V075NumericalModelV2
        or type(route) is not V075PlanningRouteV2
    ):
        _fail("V2 numerical planner rejects duck-typed inputs")
    model = _replay_numerical_model(model)
    quotient = (
        _compile_quotient(model)
        if route is V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        else None
    )
    behaviors = (
        quotient.row_behaviors
        if quotient is not None
        else _direct_behaviors(model)
    )
    behavior_by_row = {item.row_id: item for item in behaviors}
    child_options = _options(
        model=model,
        route=route,
        quotient=quotient,
        remaining_horizon=1,
    )
    root_options = _options(
        model=model,
        route=route,
        quotient=quotient,
        remaining_horizon=2,
    )
    if not root_options:
        _fail("V2 numerical model has no root options")
    child_metric_by_option = {
        option.option_id: _option_metric(
            option,
            behavior_by_row=behavior_by_row,
            child_metrics={},
        )
        for option in child_options
    }
    child_by_domain: dict[str, list[_Option]] = {}
    for option in child_options:
        child_by_domain.setdefault(option.domain_id, []).append(option)
    threshold = worker.V075WorkerThresholdProfileV1()
    best = None
    diagnostic = None
    assignments = 0
    exhausted = False
    for root in root_options:
        root_behavior_rows = tuple(
            row
            for _state, rows in root.rows_by_state
            for row in rows
        )
        relevant = tuple(
            sorted(
                {
                    term.destination_id
                    for row in root_behavior_rows
                    for term in behavior_by_row[row.row_id].terms
                    if term.destination_kind
                    is V075DestinationKindV2.CHILD_DOMAIN
                }
            )
        )
        if any(item not in child_by_domain for item in relevant):
            _fail("V2 root option lacks a materialized child domain")
        products = (
            itertools.product(
                *(tuple(child_by_domain[item]) for item in relevant)
            )
            if relevant
            else ((),)
        )
        for combination in products:
            assignments += 1
            accounting_runtime.emit_owned_operation_v1(
                "batch-planning.policy-assignment-cap-check"
            )
            if assignments > MAX_EXACT_POLICY_ASSIGNMENTS:
                exhausted = True
                break
            chosen = dict(zip(relevant, combination))
            metric = _option_metric(
                root,
                behavior_by_row=behavior_by_row,
                child_metrics={
                    domain: child_metric_by_option[option.option_id]
                    for domain, option in chosen.items()
                },
            )
            key = (
                metric.reward_lower,
                -metric.failure_upper,
                root.option_id,
                tuple(
                    (domain, chosen[domain].option_id)
                    for domain in relevant
                ),
            )
            diagnostic_key = (
                -metric.failure_upper,
                metric.reward_lower,
                root.option_id,
                key[3],
            )
            record = (key, root, chosen, metric)
            accounting_runtime.emit_owned_operation_v1(
                "batch-planning.policy-assignment.success"
            )
            if diagnostic is None:
                diagnostic = (diagnostic_key, root, chosen, metric)
            else:
                accounting_runtime.emit_owned_operation_v1(
                    "batch-planning.policy-order.diagnostic"
                )
                if diagnostic_key > diagnostic[0]:
                    diagnostic = (diagnostic_key, root, chosen, metric)
            if metric.failure_upper <= threshold.risk_tolerance:
                if best is None:
                    best = record
                else:
                    accounting_runtime.emit_owned_operation_v1(
                        "batch-planning.policy-order.feasible-best"
                    )
                    if key > best[0]:
                        best = record
        if exhausted:
            break
    if exhausted:
        frontier = _frontier(
            model=model,
            route=route,
            reason=V075FailedProofReasonV2.SEARCH_CAP_EXHAUSTED,
            row_ids=(
                row.row_id for row in model.rows if row.remaining_horizon == 2
            ),
        )
        return V075NumericalPlanningProofV2(
            _PROOF_ISSUER,
            model,
            route,
            quotient,
            V075NumericalOutcomeV2.FAILED_FRONTIER,
            None,
            None,
            frontier,
            MAX_EXACT_POLICY_ASSIGNMENTS,
        )
    if diagnostic is None:
        _fail("V2 exact search produced no diagnostic policy")
    risk_failed = best is None
    chosen_record = diagnostic[1:] if risk_failed else best[1:]
    root_option, child_assignment, selected_metric = chosen_record
    policy = V075DeterministicPolicyV2(
        _POLICY_ISSUER,
        model.model_id,
        route,
        None if quotient is None else quotient.quotient_id,
        tuple(
            sorted(
                (
                    _decision(root_option),
                    *(
                        _decision(child_assignment[domain])
                        for domain in sorted(child_assignment)
                    ),
                ),
                key=lambda item: (
                    -item.remaining_horizon,
                    item.decision_domain_id,
                ),
            )
        ),
    )
    comparator = _unrestricted_ground_reward_upper(model)
    if comparator < selected_metric.reward_upper:
        _fail("optimistic ground comparator is below selected policy upper")
    envelope = V075RobustEnvelopeV2(
        _ENVELOPE_ISSUER,
        policy.policy_id,
        selected_metric.reward_lower,
        selected_metric.reward_upper,
        selected_metric.failure_upper,
        comparator,
        (comparator - selected_metric.reward_lower)
        / threshold.reward_ceiling,
    )
    regret_failed = (
        envelope.normalized_regret_upper
        > threshold.normalized_regret_tolerance
    )
    if not risk_failed and not regret_failed:
        return V075NumericalPlanningProofV2(
            _PROOF_ISSUER,
            model,
            route,
            quotient,
            V075NumericalOutcomeV2.CANDIDATE,
            policy,
            envelope,
            None,
            assignments,
        )
    if risk_failed and regret_failed:
        reason = V075FailedProofReasonV2.RISK_AND_REGRET_BOUND_FAILED
    elif risk_failed:
        reason = V075FailedProofReasonV2.RISK_BOUND_FAILED
    else:
        reason = V075FailedProofReasonV2.REGRET_BOUND_FAILED
    selected_row_ids = tuple(
        sorted(
            {
                row_id
                for decision in policy.decisions
                for choice in decision.state_choices
                for row_id in choice.row_ids
            }
        )
    )
    frontier = _frontier(
        model=model,
        route=route,
        reason=reason,
        row_ids=selected_row_ids,
    )
    # A failed proof retains its diagnostic policy/envelope only through the
    # frontier obligations; the typed union prevents it being mistaken for a
    # candidate.
    return V075NumericalPlanningProofV2(
        _PROOF_ISSUER,
        model,
        route,
        quotient,
        V075NumericalOutcomeV2.FAILED_FRONTIER,
        None,
        None,
        frontier,
        assignments,
    )


def plan_v075_construction_aggregate_input_v2(
    value: V075ConstructionPlanningInputV2,
) -> V075ConstructionPlanningResultV2:
    if type(value) is not V075ConstructionPlanningInputV2:
        _fail("V2 aggregate planner requires one exact construction input")
    value = _replay_construction_planning_input(value)
    proof = plan_v075_construction_numerical_model_v2(
        model=value.model,
        route=value.route,
    )
    if proof.outcome is V075NumericalOutcomeV2.CANDIDATE:
        # The generic lifecycle authority proves observed row/round coverage,
        # but not yet the exact five-arm schedule order and counts.  Preserve
        # the useful numerical calculation while refusing candidate-ready
        # status at the occurrence boundary.
        frontier = _frontier(
            model=value.model,
            route=value.route,
            reason=(
                V075FailedProofReasonV2
                .GENERIC_CONSTRUCTION_NOT_SCHEDULE_BOUND
            ),
            row_ids=(item.row_id for item in value.model.rows),
        )
        proof = V075NumericalPlanningProofV2(
            _PROOF_ISSUER,
            value.model,
            value.route,
            proof.quotient,
            V075NumericalOutcomeV2.FAILED_FRONTIER,
            None,
            None,
            frontier,
            proof.policy_assignments_evaluated,
        )
    return V075ConstructionPlanningResultV2(
        _RESULT_ISSUER,
        value,
        proof,
    )


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPlanningVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    result_id: str
    planning_input_id: str
    numerical_proof_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_id, "verified planning result"),
            (self.planning_input_id, "verified planning input"),
            (self.numerical_proof_id, "verified numerical proof"),
        ):
            _cid(value, label)
        if self._issuer is not _VERIFICATION_ISSUER:
            _fail("V2 planning verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_planning_verification.v2",
            "schema_version": SCHEMA_VERSION,
            "scope": "CONSTRUCTION_ONLY",
            "result_id": self.result_id,
            "planning_input_id": self.planning_input_id,
            "numerical_proof_id": self.numerical_proof_id,
            "exact_numerical_replay": True,
            "canonical_result_bytes_replayed": True,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_construction_planning_result_bytes_v2(
    *,
    planning_input: V075ConstructionPlanningInputV2,
    claimed_bytes: bytes,
) -> tuple[
    V075ConstructionPlanningResultV2,
    V075ConstructionPlanningVerificationV2,
]:
    expected = plan_v075_construction_aggregate_input_v2(planning_input)
    if (
        type(claimed_bytes) is not bytes
        or not claimed_bytes
        or len(claimed_bytes) > MAX_ARTIFACT_BYTES
        or claimed_bytes != expected.canonical_bytes
    ):
        _fail("claimed V2 planning result differs from exact replay")
    return (
        expected,
        V075ConstructionPlanningVerificationV2(
            _VERIFICATION_ISSUER,
            expected.result_id,
            planning_input.input_id,
            expected.numerical_proof.proof_id,
        ),
    )


def execute_v075_production_planning_bytes_v2(**_kwargs: Any) -> NoReturn:
    """Remain structurally locked even if module constants are monkeypatched."""

    raise V075BatchNativePlanningV2NotReady(PRODUCTION_BLOCKER)


def freeze_v075_manual_construction_row_v2(
    *,
    row_binding: graph.V075ObservationRowBindingV1,
    draw_count: int,
    support_events: tuple[
        tuple[
            tuple[int, ...],
            bool,
            bool,
            int,
            Fraction,
            Fraction,
        ],
        ...,
    ],
    other_count: int,
    other_lower: Fraction,
    other_upper: Fraction,
) -> V075NumericalRowV2:
    """Build a construction-only exact interval row for bounded math tests."""

    if (
        type(row_binding) is not graph.V075ObservationRowBindingV1
        or type(draw_count) is not int
        or draw_count <= 0
        or type(support_events) is not tuple
        or not support_events
        or type(other_count) is not int
        or other_count < 0
    ):
        _fail("manual V2 row fixture input is malformed")
    descriptors = []
    interval_specs = []
    for next_ranks, failure, terminal, count, lower, upper in support_events:
        state = _structural_state(
            row_binding,
            next_ranks=next_ranks,
            failure=failure,
            terminal=terminal,
        )
        descriptor = V075SupportDescriptorV2(
            _DESCRIPTOR_ISSUER,
            row_binding.context_id,
            state.state_id,
            next_ranks,
            failure,
            terminal,
        )
        descriptors.append(descriptor)
        interval_specs.append((descriptor, count, lower, upper))
    ordered = tuple(
        sorted(
            zip(descriptors, interval_specs),
            key=lambda item: item[0].descriptor_id,
        )
    )
    event_count = len(ordered) + 1
    alpha = ROW_BETA / event_count

    def interval(
        descriptor: V075SupportDescriptorV2 | None,
        count: int,
        lower: Fraction,
        upper: Fraction,
    ) -> V075EventIntervalV2:
        return V075EventIntervalV2(
            _INTERVAL_ISSUER,
            "OTHER" if descriptor is None else descriptor.descriptor_id,
            descriptor,
            draw_count,
            count,
            Fraction(count, draw_count),
            lower,
            upper,
            alpha,
            0,
            0,
            "MANUAL_EXACT_INTERVAL_FIXTURE_V2",
        )

    support = tuple(item[0] for item in ordered)
    intervals = tuple(
        interval(item[0], item[1][1], item[1][2], item[1][3])
        for item in ordered
    ) + (interval(None, other_count, other_lower, other_upper),)
    return V075NumericalRowV2(
        _ROW_ISSUER,
        row_binding.context_id,
        row_binding.row_binding_id,
        row_binding.state_id,
        row_binding.catalogue.state.ranks,
        row_binding.remaining_horizon,
        row_binding.action,
        _merge_reward(row_binding),
        support,
        intervals,
    )


def freeze_v075_manual_construction_model_v2(
    *,
    context: public_authority.V075PublicReplicateContextV1,
    rows: tuple[V075NumericalRowV2, ...],
) -> V075NumericalModelV2:
    return V075NumericalModelV2(
        _MODEL_ISSUER,
        context,
        tuple(sorted(rows, key=lambda item: item.row_id)),
        "MANUAL_EXACT_INTERVAL_FIXTURE",
    )


__all__ = [
    "BOUNDARY_GRID_BITS",
    "COMPARATOR_RULE",
    "FAMILYWISE_CONFIDENCE_ERROR_UPPER",
    "MAX_VALIDATED_ROWS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "POLICY_ABORT_RULE",
    "PROPOSED_CONTRACT_VERSION",
    "ROW_BETA",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "TARGET_HALF_WIDTH",
    "V075BatchNativePlanningV2InvariantViolation",
    "V075BatchNativePlanningV2NotReady",
    "V075BehavioralQuotientV2",
    "V075ConstructionPlanningInputV2",
    "V075ConstructionPlanningResultV2",
    "V075ConstructionPlanningVerificationV2",
    "V075FailedProofFrontierV2",
    "V075FailedProofReasonV2",
    "V075NumericalModelV2",
    "V075NumericalOutcomeV2",
    "V075NumericalPlanningProofV2",
    "V075NumericalRowV2",
    "V075PlanningRouteV2",
    "compile_v075_construction_planning_input_v2",
    "execute_v075_production_planning_bytes_v2",
    "freeze_v075_manual_construction_model_v2",
    "freeze_v075_manual_construction_row_v2",
    "plan_v075_construction_aggregate_input_v2",
    "plan_v075_construction_numerical_model_v2",
    "verify_v075_construction_planning_result_bytes_v2",
]
