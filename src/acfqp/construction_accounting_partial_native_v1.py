"""Incomplete-site native construction traces without accounting claims.

This module deliberately stops before ``CounterRecord``, ``WorkVector`` and
``ComparisonVector`` construction.  It records only positive native events
whose operation boundaries were actually observed.  Uncovered sites remain
unknown: they are never materialized as zero.

The transcript is an immutable content-addressed chain::

    occurrence start
      -> stage start -> native events -> stage completion
      -> ... exactly five registered stages ...
      -> occurrence completion | occurrence abort

It is therefore useful while operation-site coverage is incomplete, but it
is not official accounting evidence and cannot authorize execution or a
certificate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Mapping, TypeAlias

from acfqp.accounting_v1 import ReducerEnum
from acfqp.phase3e_ids import (
    CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_ABORT_V1_DOMAIN,
    CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_COMPLETION_V1_DOMAIN,
    CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_START_V1_DOMAIN,
    CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_TRANSCRIPT_V1_DOMAIN,
    CONSTRUCTION_PARTIAL_NATIVE_OPERATION_EVENT_V1_DOMAIN,
    CONSTRUCTION_PARTIAL_NATIVE_STAGE_COMPLETION_V1_DOMAIN,
    CONSTRUCTION_PARTIAL_NATIVE_STAGE_START_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
COVERAGE_STATE = "PARTIAL_NATIVE_ONLY"
UNAVAILABLE_KIND = "NOT_AVAILABLE_INCOMPLETE_SITE_COVERAGE"
UNAVAILABLE_REASON = (
    "operation-site coverage is incomplete; absent native work is unknown"
)
NOT_APPLICABLE_KIND = "NOT_APPLICABLE"
CHAIN_GENESIS_REASON = "CHAIN_GENESIS"
NO_ACTIVE_STAGE_REASON = "NO_ACTIVE_STAGE_AT_ABORT"
NO_EXCEPTION_REASON = "NO_EXCEPTION_TYPE"
UNREPRESENTABLE_EXCEPTION_REASON = "UNREPRESENTABLE_EXCEPTION_TYPE"
NO_ABORT_REASON = "OCCURRENCE_COMPLETED_WITHOUT_ABORT"
NO_COMPLETION_REASON = "OCCURRENCE_ABORTED_WITHOUT_COMPLETION"

# Public aliases retain the artifact module's concise names while the domain
# registry remains the single authority for every Phase-3E tag.
PARTIAL_NATIVE_OCCURRENCE_START_V1_DOMAIN = (
    CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_START_V1_DOMAIN
)
PARTIAL_NATIVE_STAGE_START_V1_DOMAIN = (
    CONSTRUCTION_PARTIAL_NATIVE_STAGE_START_V1_DOMAIN
)
PARTIAL_NATIVE_OPERATION_EVENT_V1_DOMAIN = (
    CONSTRUCTION_PARTIAL_NATIVE_OPERATION_EVENT_V1_DOMAIN
)
PARTIAL_NATIVE_STAGE_COMPLETION_V1_DOMAIN = (
    CONSTRUCTION_PARTIAL_NATIVE_STAGE_COMPLETION_V1_DOMAIN
)
PARTIAL_NATIVE_OCCURRENCE_COMPLETION_V1_DOMAIN = (
    CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_COMPLETION_V1_DOMAIN
)
PARTIAL_NATIVE_OCCURRENCE_ABORT_V1_DOMAIN = (
    CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_ABORT_V1_DOMAIN
)
PARTIAL_NATIVE_OCCURRENCE_TRANSCRIPT_V1_DOMAIN = (
    CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_TRANSCRIPT_V1_DOMAIN
)

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")


class PartialNativeAccountingV1Error(ValueError):
    """A partial-native node or chain is malformed."""


class PartialNativeStageV1(str, Enum):
    PREOPEN_COMMON_PREFIX = "PREOPEN_COMMON_PREFIX"
    INITIAL_ACQUISITION = "INITIAL_ACQUISITION"
    INITIAL_MODEL_BUILD = "INITIAL_MODEL_BUILD"
    FAILED_ABSTRACT_PREFIX = "FAILED_ABSTRACT_PREFIX"
    CLOSED_RECONCILIATION_AND_TERMINALIZATION = (
        "CLOSED_RECONCILIATION_AND_TERMINALIZATION"
    )


ROOT_CAP_FIVE_STAGE_PLAN_V1 = tuple(PartialNativeStageV1)


class PartialNativeTerminalKindV1(str, Enum):
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


def _content_id(domain: str, value: Any) -> str:
    return content_id(domain, value)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PartialNativeAccountingV1Error(
            f"{field_name} must be a full content ID"
        ) from error


def _identifier(value: Any, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise PartialNativeAccountingV1Error(
            f"{field_name} must be a canonical identifier"
        )
    return value


def _exception_identifier(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 512
        or any(ord(character) < 33 or ord(character) > 126 for character in value)
    ):
        raise PartialNativeAccountingV1Error(
            f"{field_name} must be a bounded printable type identifier"
        )
    return value


def _positive(value: Any, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise PartialNativeAccountingV1Error(
            f"{field_name} must be a positive exact integer"
        )
    return value


def _nonnegative(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise PartialNativeAccountingV1Error(
            f"{field_name} must be a nonnegative exact integer"
        )
    return value


def _stage(value: Any) -> PartialNativeStageV1:
    try:
        return PartialNativeStageV1(value)
    except (TypeError, ValueError) as error:
        raise PartialNativeAccountingV1Error(
            f"unknown partial-native stage {value!r}"
        ) from error


@dataclass(frozen=True, slots=True)
class IncompleteSiteCoverageRefV1:
    """A typed absence; neither ordinary ``null`` nor a native zero."""

    reason: str = UNAVAILABLE_REASON
    kind: str = UNAVAILABLE_KIND

    def __post_init__(self) -> None:
        if self.kind != UNAVAILABLE_KIND or self.reason != UNAVAILABLE_REASON:
            raise PartialNativeAccountingV1Error(
                "incomplete-coverage typed null changed"
            )

    def to_document(self) -> dict[str, str]:
        return {"kind": self.kind, "reason": self.reason}


def _unavailable() -> IncompleteSiteCoverageRefV1:
    return IncompleteSiteCoverageRefV1()


@dataclass(frozen=True, slots=True)
class PartialNativeNotApplicableV1:
    """A typed null for a field that is semantically inapplicable."""

    reason: str
    kind: str = NOT_APPLICABLE_KIND

    def __post_init__(self) -> None:
        if self.kind != NOT_APPLICABLE_KIND or self.reason not in {
            CHAIN_GENESIS_REASON,
            NO_ACTIVE_STAGE_REASON,
            NO_EXCEPTION_REASON,
            UNREPRESENTABLE_EXCEPTION_REASON,
            NO_ABORT_REASON,
            NO_COMPLETION_REASON,
        }:
            raise PartialNativeAccountingV1Error(
                "partial-native NOT_APPLICABLE value changed"
            )

    def to_document(self) -> dict[str, str]:
        return {"kind": self.kind, "reason": self.reason}


def _not_applicable(reason: str) -> PartialNativeNotApplicableV1:
    return PartialNativeNotApplicableV1(reason)


def _ref_document(value: Any) -> Any:
    return value.to_document() if isinstance(value, PartialNativeNotApplicableV1) else value


@dataclass(frozen=True, slots=True)
class PartialNativeOccurrenceStartV1:
    occurrence_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    recorder_id: str
    stage_plan: tuple[PartialNativeStageV1, ...] = (
        ROOT_CAP_FIVE_STAGE_PLAN_V1
    )
    predecessor_chain_id: PartialNativeNotApplicableV1 = field(
        default_factory=lambda: _not_applicable(CHAIN_GENESIS_REASON)
    )
    chain_sequence: int = 0

    def __post_init__(self) -> None:
        for name in (
            "occurrence_id",
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
        ):
            _cid(getattr(self, name), name)
        _identifier(self.recorder_id, "recorder_id")
        normalized = tuple(_stage(item) for item in self.stage_plan)
        object.__setattr__(self, "stage_plan", normalized)
        if normalized != ROOT_CAP_FIVE_STAGE_PLAN_V1:
            raise PartialNativeAccountingV1Error(
                "partial-native occurrence must use the exact five-stage plan"
            )
        if (
            type(self.predecessor_chain_id) is not PartialNativeNotApplicableV1
            or self.predecessor_chain_id.reason != CHAIN_GENESIS_REASON
        ):
            raise PartialNativeAccountingV1Error(
                "occurrence genesis must carry its exact typed null"
            )
        if self.chain_sequence != 0:
            raise PartialNativeAccountingV1Error(
                "occurrence-start chain sequence must be zero"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_partial_native_occurrence_start.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "recorder_id": self.recorder_id,
            "stage_plan": [item.value for item in self.stage_plan],
            "predecessor_chain_id": self.predecessor_chain_id.to_document(),
            "chain_sequence": self.chain_sequence,
            "coverage_state": COVERAGE_STATE,
        }

    @property
    def start_id(self) -> str:
        return _content_id(PARTIAL_NATIVE_OCCURRENCE_START_V1_DOMAIN, self._payload())

    @property
    def chain_id(self) -> str:
        return self.start_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_start_id": self.start_id}


@dataclass(frozen=True, slots=True)
class PartialNativeStageStartV1:
    occurrence_start_id: str
    occurrence_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    chain_sequence: int
    predecessor_chain_id: str
    stage_index: int
    stage_kind: PartialNativeStageV1

    def __post_init__(self) -> None:
        for name in (
            "occurrence_start_id",
            "occurrence_id",
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
            "predecessor_chain_id",
        ):
            _cid(getattr(self, name), name)
        _positive(self.chain_sequence, "chain_sequence")
        _positive(self.stage_index, "stage_index")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        if (
            self.stage_index > len(ROOT_CAP_FIVE_STAGE_PLAN_V1)
            or ROOT_CAP_FIVE_STAGE_PLAN_V1[self.stage_index - 1]
            is not self.stage_kind
        ):
            raise PartialNativeAccountingV1Error(
                "stage start differs from the exact five-stage plan"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_partial_native_stage_start.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_start_id": self.occurrence_start_id,
            "occurrence_id": self.occurrence_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "chain_sequence": self.chain_sequence,
            "predecessor_chain_id": self.predecessor_chain_id,
            "stage_index": self.stage_index,
            "stage_kind": self.stage_kind.value,
        }

    @property
    def chain_id(self) -> str:
        return _content_id(PARTIAL_NATIVE_STAGE_START_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_start_id": self.chain_id}


@dataclass(frozen=True, slots=True)
class PartialNativeOperationEventV1:
    occurrence_start_id: str
    occurrence_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    chain_sequence: int
    predecessor_chain_id: str
    stage_index: int
    stage_kind: PartialNativeStageV1
    stage_event_sequence: int
    site_id: str
    path: str
    reducer: ReducerEnum
    amount: int

    def __post_init__(self) -> None:
        for name in (
            "occurrence_start_id",
            "occurrence_id",
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
            "predecessor_chain_id",
        ):
            _cid(getattr(self, name), name)
        _positive(self.chain_sequence, "chain_sequence")
        _positive(self.stage_index, "stage_index")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        _positive(self.stage_event_sequence, "stage_event_sequence")
        _identifier(self.site_id, "site_id")
        _identifier(self.path, "path")
        try:
            reducer = ReducerEnum(self.reducer)
        except (TypeError, ValueError) as error:
            raise PartialNativeAccountingV1Error(
                "operation reducer is invalid"
            ) from error
        object.__setattr__(self, "reducer", reducer)
        if reducer is not ReducerEnum.SUM:
            raise PartialNativeAccountingV1Error(
                "partial native v1 accepts only exact positive SUM events"
            )
        _positive(self.amount, "amount")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_partial_native_operation_event.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_start_id": self.occurrence_start_id,
            "occurrence_id": self.occurrence_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "chain_sequence": self.chain_sequence,
            "predecessor_chain_id": self.predecessor_chain_id,
            "stage_index": self.stage_index,
            "stage_kind": self.stage_kind.value,
            "stage_event_sequence": self.stage_event_sequence,
            "site_id": self.site_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "amount": self.amount,
        }

    @property
    def chain_id(self) -> str:
        return _content_id(PARTIAL_NATIVE_OPERATION_EVENT_V1_DOMAIN, self._payload())

    @property
    def event_id(self) -> str:
        return self.chain_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operation_event_id": self.event_id}


@dataclass(frozen=True, slots=True, order=True)
class PartialNativeOutputBindingV1:
    """A stage-output role bound to one exact content artifact."""

    role: str
    artifact_id: str

    def __post_init__(self) -> None:
        _identifier(self.role, "output role")
        _cid(self.artifact_id, "output artifact_id")

    def to_document(self) -> dict[str, str]:
        return {"role": self.role, "artifact_id": self.artifact_id}


@dataclass(frozen=True, slots=True)
class PartialNativeStageCompletionV1:
    occurrence_start_id: str
    occurrence_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    chain_sequence: int
    predecessor_chain_id: str
    stage_index: int
    stage_kind: PartialNativeStageV1
    stage_event_count: int
    total_event_count: int
    output_bindings: tuple[PartialNativeOutputBindingV1, ...]

    def __post_init__(self) -> None:
        for name in (
            "occurrence_start_id",
            "occurrence_id",
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
            "predecessor_chain_id",
        ):
            _cid(getattr(self, name), name)
        _positive(self.chain_sequence, "chain_sequence")
        _positive(self.stage_index, "stage_index")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        _nonnegative(self.stage_event_count, "stage_event_count")
        _nonnegative(self.total_event_count, "total_event_count")
        if self.stage_event_count > self.total_event_count:
            raise PartialNativeAccountingV1Error(
                "stage event count exceeds occurrence event count"
            )
        outputs = tuple(self.output_bindings)
        object.__setattr__(self, "output_bindings", outputs)
        if (
            any(type(row) is not PartialNativeOutputBindingV1 for row in outputs)
            or tuple(sorted(outputs)) != outputs
            or len(set(outputs)) != len(outputs)
            or len({row.role for row in outputs}) != len(outputs)
        ):
            raise PartialNativeAccountingV1Error(
                "stage output bindings must be unique and in canonical order"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_partial_native_stage_completion.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_start_id": self.occurrence_start_id,
            "occurrence_id": self.occurrence_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "chain_sequence": self.chain_sequence,
            "predecessor_chain_id": self.predecessor_chain_id,
            "stage_index": self.stage_index,
            "stage_kind": self.stage_kind.value,
            "stage_event_count": self.stage_event_count,
            "total_event_count": self.total_event_count,
            "output_bindings": [row.to_document() for row in self.output_bindings],
        }

    @property
    def chain_id(self) -> str:
        return _content_id(
            PARTIAL_NATIVE_STAGE_COMPLETION_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_completion_id": self.chain_id}


@dataclass(frozen=True, slots=True)
class PartialNativeOccurrenceCompletionV1:
    occurrence_start_id: str
    occurrence_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    chain_sequence: int
    predecessor_chain_id: str
    completed_stage_count: int
    total_event_count: int
    emitted_event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "occurrence_start_id",
            "occurrence_id",
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
            "predecessor_chain_id",
        ):
            _cid(getattr(self, name), name)
        _positive(self.chain_sequence, "chain_sequence")
        if self.completed_stage_count != len(ROOT_CAP_FIVE_STAGE_PLAN_V1):
            raise PartialNativeAccountingV1Error(
                "occurrence completion requires all five stages"
            )
        _nonnegative(self.total_event_count, "total_event_count")
        event_ids = tuple(self.emitted_event_ids)
        object.__setattr__(self, "emitted_event_ids", event_ids)
        if len(event_ids) != self.total_event_count:
            raise PartialNativeAccountingV1Error(
                "completion event IDs differ from its event count"
            )
        for event_id in event_ids:
            _cid(event_id, "emitted_event_id")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_partial_native_occurrence_completion.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_start_id": self.occurrence_start_id,
            "occurrence_id": self.occurrence_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "chain_sequence": self.chain_sequence,
            "predecessor_chain_id": self.predecessor_chain_id,
            "completed_stage_count": self.completed_stage_count,
            "total_event_count": self.total_event_count,
            "emitted_event_ids": list(self.emitted_event_ids),
        }

    @property
    def chain_id(self) -> str:
        return _content_id(
            PARTIAL_NATIVE_OCCURRENCE_COMPLETION_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_completion_id": self.chain_id}


@dataclass(frozen=True, slots=True)
class PartialNativeOccurrenceAbortV1:
    occurrence_start_id: str
    occurrence_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    chain_sequence: int
    predecessor_chain_id: str
    completed_stage_count: int
    total_event_count: int
    emitted_event_ids: tuple[str, ...]
    aborted_stage_index: int | PartialNativeNotApplicableV1
    aborted_stage_kind: PartialNativeStageV1 | PartialNativeNotApplicableV1
    exception_module: str | PartialNativeNotApplicableV1
    exception_qualname: str | PartialNativeNotApplicableV1
    reason: str

    def __post_init__(self) -> None:
        for name in (
            "occurrence_start_id",
            "occurrence_id",
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
            "predecessor_chain_id",
        ):
            _cid(getattr(self, name), name)
        _positive(self.chain_sequence, "chain_sequence")
        completed = _nonnegative(
            self.completed_stage_count, "completed_stage_count"
        )
        if completed > len(ROOT_CAP_FIVE_STAGE_PLAN_V1):
            raise PartialNativeAccountingV1Error(
                "abort completed-stage count exceeds the stage plan"
            )
        _nonnegative(self.total_event_count, "total_event_count")
        event_ids = tuple(self.emitted_event_ids)
        object.__setattr__(self, "emitted_event_ids", event_ids)
        if len(event_ids) != self.total_event_count:
            raise PartialNativeAccountingV1Error(
                "abort event IDs differ from its event count"
            )
        for event_id in event_ids:
            _cid(event_id, "emitted_event_id")
        index = self.aborted_stage_index
        stage_kind = self.aborted_stage_kind
        if isinstance(index, PartialNativeNotApplicableV1):
            if (
                index.reason != NO_ACTIVE_STAGE_REASON
                or not isinstance(stage_kind, PartialNativeNotApplicableV1)
                or stage_kind.reason != NO_ACTIVE_STAGE_REASON
            ):
                raise PartialNativeAccountingV1Error(
                    "abort stage index and kind typed nulls must agree"
                )
        else:
            _positive(index, "aborted_stage_index")
            normalized = _stage(stage_kind)
            object.__setattr__(self, "aborted_stage_kind", normalized)
            if (
                index != completed + 1
                or index > len(ROOT_CAP_FIVE_STAGE_PLAN_V1)
                or ROOT_CAP_FIVE_STAGE_PLAN_V1[index - 1] is not normalized
            ):
                raise PartialNativeAccountingV1Error(
                    "abort active-stage identity differs from lifecycle state"
                )
        module = self.exception_module
        qualname = self.exception_qualname
        if isinstance(module, PartialNativeNotApplicableV1):
            if (
                module.reason
                not in {
                    NO_EXCEPTION_REASON,
                    UNREPRESENTABLE_EXCEPTION_REASON,
                }
                or not isinstance(qualname, PartialNativeNotApplicableV1)
                or qualname.reason != module.reason
            ):
                raise PartialNativeAccountingV1Error(
                    "exception module and qualname typed nulls must agree"
                )
        else:
            _exception_identifier(module, "exception_module")
            _exception_identifier(qualname, "exception_qualname")
        _identifier(self.reason, "abort reason")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_partial_native_occurrence_abort.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_start_id": self.occurrence_start_id,
            "occurrence_id": self.occurrence_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "chain_sequence": self.chain_sequence,
            "predecessor_chain_id": self.predecessor_chain_id,
            "completed_stage_count": self.completed_stage_count,
            "total_event_count": self.total_event_count,
            "emitted_event_ids": list(self.emitted_event_ids),
            "aborted_stage_index": _ref_document(self.aborted_stage_index),
            "aborted_stage_kind": (
                self.aborted_stage_kind.value
                if isinstance(self.aborted_stage_kind, PartialNativeStageV1)
                else self.aborted_stage_kind.to_document()
            ),
            "exception_module": _ref_document(self.exception_module),
            "exception_qualname": _ref_document(self.exception_qualname),
            "reason": self.reason,
        }

    @property
    def chain_id(self) -> str:
        return _content_id(PARTIAL_NATIVE_OCCURRENCE_ABORT_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_abort_id": self.chain_id}


PartialNativeChainNodeV1: TypeAlias = (
    PartialNativeStageStartV1
    | PartialNativeOperationEventV1
    | PartialNativeStageCompletionV1
    | PartialNativeOccurrenceCompletionV1
    | PartialNativeOccurrenceAbortV1
)


def _node_document(node: PartialNativeChainNodeV1) -> dict[str, Any]:
    if type(node) not in {
        PartialNativeStageStartV1,
        PartialNativeOperationEventV1,
        PartialNativeStageCompletionV1,
        PartialNativeOccurrenceCompletionV1,
        PartialNativeOccurrenceAbortV1,
    }:
        raise PartialNativeAccountingV1Error(
            "partial-native transcript contains a foreign chain node"
        )
    return node.to_document()


@dataclass(frozen=True, slots=True)
class PartialNativeOccurrenceTranscriptV1:
    start: PartialNativeOccurrenceStartV1
    nodes: tuple[PartialNativeChainNodeV1, ...]
    counter_records: IncompleteSiteCoverageRefV1 = field(
        default_factory=_unavailable
    )
    work_vector: IncompleteSiteCoverageRefV1 = field(
        default_factory=_unavailable
    )
    comparison_vector: IncompleteSiteCoverageRefV1 = field(
        default_factory=_unavailable
    )
    actual_projection: IncompleteSiteCoverageRefV1 = field(
        default_factory=_unavailable
    )
    coverage_state: str = COVERAGE_STATE
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        if type(self.start) is not PartialNativeOccurrenceStartV1:
            raise PartialNativeAccountingV1Error(
                "partial-native transcript start is foreign"
            )
        nodes = tuple(self.nodes)
        object.__setattr__(self, "nodes", nodes)
        if not nodes:
            raise PartialNativeAccountingV1Error(
                "partial-native transcript has no terminal chain"
            )
        for value in (
            self.counter_records,
            self.work_vector,
            self.comparison_vector,
            self.actual_projection,
        ):
            if type(value) is not IncompleteSiteCoverageRefV1:
                raise PartialNativeAccountingV1Error(
                    "incomplete accounting reference is not the typed null"
                )
        if (
            self.coverage_state != COVERAGE_STATE
            or self.official_execution_allowed is not False
        ):
            raise PartialNativeAccountingV1Error(
                "partial transcript cannot authorize official execution"
            )
        self._verify_chain()

    @property
    def terminal_kind(self) -> PartialNativeTerminalKindV1:
        if type(self.nodes[-1]) is PartialNativeOccurrenceCompletionV1:
            return PartialNativeTerminalKindV1.COMPLETED
        return PartialNativeTerminalKindV1.ABORTED

    def _verify_chain(self) -> None:
        predecessor = self.start.chain_id
        active_stage: PartialNativeStageV1 | None = None
        completed = 0
        stage_events = 0
        total_events = 0
        terminal_seen = False
        event_ids: list[str] = []
        for sequence, node in enumerate(self.nodes, 1):
            _node_document(node)
            if terminal_seen:
                raise PartialNativeAccountingV1Error(
                    "partial-native terminal node is not final"
                )
            if (
                node.chain_sequence != sequence
                or node.predecessor_chain_id != predecessor
                or node.occurrence_start_id != self.start.start_id
                or node.occurrence_id != self.start.occurrence_id
                or node.counter_registry_id != self.start.counter_registry_id
                or node.stage_profile_id != self.start.stage_profile_id
                or node.boundary_profile_id != self.start.boundary_profile_id
            ):
                raise PartialNativeAccountingV1Error(
                    "partial-native chain is reordered or identity-mismatched"
                )
            if type(node) is PartialNativeStageStartV1:
                if active_stage is not None or node.stage_index != completed + 1:
                    raise PartialNativeAccountingV1Error(
                        "stage start violates the exact sequential lifecycle"
                    )
                active_stage = node.stage_kind
                stage_events = 0
            elif type(node) is PartialNativeOperationEventV1:
                if (
                    active_stage is None
                    or node.stage_kind is not active_stage
                    or node.stage_index != completed + 1
                    or node.stage_event_sequence != stage_events + 1
                ):
                    raise PartialNativeAccountingV1Error(
                        "operation event is outside its active stage"
                    )
                stage_events += 1
                total_events += 1
                event_ids.append(node.event_id)
            elif type(node) is PartialNativeStageCompletionV1:
                if (
                    active_stage is None
                    or node.stage_kind is not active_stage
                    or node.stage_index != completed + 1
                    or node.stage_event_count != stage_events
                    or node.total_event_count != total_events
                ):
                    raise PartialNativeAccountingV1Error(
                        "stage completion does not replay its native events"
                    )
                completed += 1
                active_stage = None
                stage_events = 0
            elif type(node) is PartialNativeOccurrenceCompletionV1:
                if (
                    active_stage is not None
                    or completed != len(ROOT_CAP_FIVE_STAGE_PLAN_V1)
                    or node.completed_stage_count != completed
                    or node.total_event_count != total_events
                    or node.emitted_event_ids != tuple(event_ids)
                ):
                    raise PartialNativeAccountingV1Error(
                        "occurrence completion precedes exact stage closure"
                    )
                terminal_seen = True
            elif type(node) is PartialNativeOccurrenceAbortV1:
                if (
                    node.completed_stage_count != completed
                    or node.total_event_count != total_events
                    or node.emitted_event_ids != tuple(event_ids)
                ):
                    raise PartialNativeAccountingV1Error(
                        "occurrence abort does not preserve partial progress"
                    )
                if active_stage is None:
                    if (
                        not isinstance(
                            node.aborted_stage_index,
                            PartialNativeNotApplicableV1,
                        )
                        or not isinstance(
                            node.aborted_stage_kind,
                            PartialNativeNotApplicableV1,
                        )
                    ):
                        raise PartialNativeAccountingV1Error(
                            "between-stage abort must use typed-null stage fields"
                        )
                elif (
                    node.aborted_stage_index != completed + 1
                    or node.aborted_stage_kind is not active_stage
                ):
                    raise PartialNativeAccountingV1Error(
                        "active-stage abort identity differs from chain state"
                    )
                terminal_seen = True
            predecessor = node.chain_id
        if not terminal_seen:
            raise PartialNativeAccountingV1Error(
                "partial-native transcript lacks completion or abort"
            )

    def _payload(self) -> dict[str, Any]:
        terminal = self.nodes[-1]
        completed = (
            terminal.chain_id
            if type(terminal) is PartialNativeOccurrenceCompletionV1
            else _not_applicable(NO_COMPLETION_REASON).to_document()
        )
        aborted = (
            terminal.chain_id
            if type(terminal) is PartialNativeOccurrenceAbortV1
            else _not_applicable(NO_ABORT_REASON).to_document()
        )
        return {
            "schema": "acfqp.construction_partial_native_occurrence_transcript.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_start": self.start.to_document(),
            "chain_nodes": [_node_document(node) for node in self.nodes],
            "terminal_kind": self.terminal_kind.value,
            "occurrence_completion_id": completed,
            "occurrence_abort_id": aborted,
            "counter_records": self.counter_records.to_document(),
            "work_vector": self.work_vector.to_document(),
            "comparison_vector": self.comparison_vector.to_document(),
            "actual_projection": self.actual_projection.to_document(),
            "coverage_state": self.coverage_state,
            "absent_native_events_inferred_zero": False,
            "official_execution_allowed": self.official_execution_allowed,
        }

    @property
    def transcript_id(self) -> str:
        return _content_id(
            PARTIAL_NATIVE_OCCURRENCE_TRANSCRIPT_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "partial_native_transcript_id": self.transcript_id}


def verify_partial_native_occurrence_transcript_v1(
    transcript: PartialNativeOccurrenceTranscriptV1,
) -> None:
    """Replay all identities and lifecycle transitions without deriving zeros."""

    if type(transcript) is not PartialNativeOccurrenceTranscriptV1:
        raise PartialNativeAccountingV1Error(
            "partial-native verifier received a foreign artifact"
        )
    transcript._verify_chain()
    parse_content_id(transcript.transcript_id)


__all__ = [
    "COVERAGE_STATE",
    "CHAIN_GENESIS_REASON",
    "IncompleteSiteCoverageRefV1",
    "NO_ACTIVE_STAGE_REASON",
    "NO_ABORT_REASON",
    "NO_COMPLETION_REASON",
    "NO_EXCEPTION_REASON",
    "UNREPRESENTABLE_EXCEPTION_REASON",
    "NOT_APPLICABLE_KIND",
    "PARTIAL_NATIVE_OCCURRENCE_ABORT_V1_DOMAIN",
    "PARTIAL_NATIVE_OCCURRENCE_COMPLETION_V1_DOMAIN",
    "PARTIAL_NATIVE_OCCURRENCE_START_V1_DOMAIN",
    "PARTIAL_NATIVE_OCCURRENCE_TRANSCRIPT_V1_DOMAIN",
    "PARTIAL_NATIVE_OPERATION_EVENT_V1_DOMAIN",
    "PARTIAL_NATIVE_STAGE_COMPLETION_V1_DOMAIN",
    "PARTIAL_NATIVE_STAGE_START_V1_DOMAIN",
    "PartialNativeAccountingV1Error",
    "PartialNativeOccurrenceAbortV1",
    "PartialNativeOccurrenceCompletionV1",
    "PartialNativeOccurrenceStartV1",
    "PartialNativeOccurrenceTranscriptV1",
    "PartialNativeOperationEventV1",
    "PartialNativeNotApplicableV1",
    "PartialNativeOutputBindingV1",
    "PartialNativeStageCompletionV1",
    "PartialNativeStageStartV1",
    "PartialNativeStageV1",
    "PartialNativeTerminalKindV1",
    "ROOT_CAP_FIVE_STAGE_PLAN_V1",
    "SCHEMA_VERSION",
    "UNAVAILABLE_KIND",
    "UNAVAILABLE_REASON",
    "verify_partial_native_occurrence_transcript_v1",
]
