"""Trusted v3 evidence mechanics for construction-accounting registries.

Contract 1.86 froze only the additive v3 registry and profiles.  This module
adds the evidence mechanics needed by a later, scoped live execution without
changing any v2 or v3 registry bytes:

* a one-way, stage-planned lifecycle;
* issuer-owned stage starts, operation events, and completions;
* event replay into one observed record for every required leaf, including
  native zeroes;
* reducer- and reconciliation-aware work-vector validation; and
* exact projection onto the unchanged eight shared axes.

The evidence schema may bind the exact v3 registry or an additive successor
whose stage vocabulary and profile interfaces remain compatible. It does not
weaken or reinterpret either registry.

The module does not instrument an execution site by itself.  In particular,
the generic ``operation_site_id`` carried by an event is not proof that every
reachable site in a runner emitted an event.  A scoped operation-site manifest
and runner integration remain separate obligations.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import re
from typing import Any, Mapping, Sequence

from acfqp.accounting_v1 import (
    LaneEnum,
    ReducerEnum,
    SHARED_AXES,
)
from acfqp.construction_accounting_registry_v3 import (
    ActualProjectionProfileV3,
    ComparisonProfileV3,
    ConstructionAccountingRegistryV3Error,
    ConstructionStageKindV3,
    CounterRegistryV3,
    StageProfileV3,
    official_actual_projection_profile_v3,
    official_comparison_profile_v3,
    official_counter_registry_v3,
    official_stage_profile_v3,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACCOUNTING_LIFECYCLE_V3_DOMAIN,
    CONSTRUCTION_ACTUAL_PROJECTION_PROOF_V3_DOMAIN,
    CONSTRUCTION_COMPARISON_VECTOR_V3_DOMAIN,
    CONSTRUCTION_COUNTER_RECORD_V3_DOMAIN,
    CONSTRUCTION_OPERATION_EVENT_V3_DOMAIN,
    CONSTRUCTION_STAGE_COMPLETION_ATTESTATION_V3_DOMAIN,
    CONSTRUCTION_STAGE_EVENT_TRANSCRIPT_V3_DOMAIN,
    CONSTRUCTION_STAGE_INSTANCE_V3_DOMAIN,
    CONSTRUCTION_STAGE_START_ATTESTATION_V3_DOMAIN,
    CONSTRUCTION_WORK_VECTOR_V3_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "3.0.0"

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_LIFECYCLE_ISSUER = object()
_START_ISSUER = object()
_EVENT_ISSUER = object()
_COMPLETION_ISSUER = object()
_ACTIVE_STAGE_ISSUER = object()

_DERIVED_TOTAL_PATHS = frozenset(
    {
        "route.attempts",
        "solver.attempts",
    }
)


class ConstructionAccountingLiveV3Error(ValueError):
    """A live lifecycle, native event, or projected artifact is invalid."""


class StageCompletionOutcomeV3(str, Enum):
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


def _identifier(value: Any, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ConstructionAccountingLiveV3Error(
            f"{field_name} must be a canonical identifier"
        )
    return value


def _nonnegative(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ConstructionAccountingLiveV3Error(
            f"{field_name} must be a nonnegative exact integer"
        )
    return value


def _positive(value: Any, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ConstructionAccountingLiveV3Error(
            f"{field_name} must be a positive exact integer"
        )
    return value


def _stage(value: Any) -> ConstructionStageKindV3:
    try:
        return ConstructionStageKindV3(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingLiveV3Error(
            f"unknown construction stage {value!r}"
        ) from error


def _outcome(value: Any) -> StageCompletionOutcomeV3:
    try:
        return StageCompletionOutcomeV3(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingLiveV3Error(
            f"unknown stage-completion outcome {value!r}"
        ) from error


def _canonical_ids(
    values: Sequence[str], *, field_name: str
) -> tuple[str, ...]:
    result = tuple(values)
    if tuple(sorted(result)) != result or len(set(result)) != len(result):
        raise ConstructionAccountingLiveV3Error(
            f"{field_name} must be unique and sorted"
        )
    for value in result:
        parse_content_id(value)
    return result


def _allowed_nonzero_paths(
    stage_profile: Any, stage_kind: ConstructionStageKindV3
) -> tuple[str, ...]:
    """Read one exact stage rule without requiring its enum implementation.

    The contract-1.87 evidence vocabulary remains v3.  Looking up a rule by
    its string value keeps this mechanics layer separable from a future
    additive registry/profile adapter whose enum class may differ.
    """

    for key, rule in stage_profile.by_stage.items():
        if getattr(key, "value", key) == stage_kind.value:
            return tuple(rule.allowed_nonzero_paths)
    raise ConstructionAccountingLiveV3Error(
        f"stage profile omits {stage_kind.value}"
    )


def _lifecycle_id(
    *,
    counter_registry_id: str,
    stage_profile_id: str,
    subject_id: str,
    recorder_id: str,
    stage_plan: tuple[ConstructionStageKindV3, ...],
) -> str:
    return content_id(
        CONSTRUCTION_ACCOUNTING_LIFECYCLE_V3_DOMAIN,
        {
            "schema": "acfqp.construction_accounting_lifecycle.v3",
            "schema_version": SCHEMA_VERSION,
            "counter_registry_id": counter_registry_id,
            "stage_profile_id": stage_profile_id,
            "subject_id": subject_id,
            "recorder_id": recorder_id,
            "stage_plan": [item.value for item in stage_plan],
        },
    )


def _stage_instance_id(
    *,
    lifecycle_id: str,
    subject_id: str,
    stage_index: int,
    stage_kind: ConstructionStageKindV3,
    predecessor_completion_attestation_id: str | None,
) -> str:
    return content_id(
        CONSTRUCTION_STAGE_INSTANCE_V3_DOMAIN,
        {
            "schema": "acfqp.construction_stage_instance.v3",
            "schema_version": SCHEMA_VERSION,
            "lifecycle_id": lifecycle_id,
            "subject_id": subject_id,
            "stage_index": stage_index,
            "stage_kind": stage_kind.value,
            "predecessor_completion_attestation_id": (
                predecessor_completion_attestation_id
            ),
        },
    )


@dataclass(frozen=True, slots=True)
class StageStartAttestationV3:
    _issuer: InitVar[object]
    lifecycle_id: str
    counter_registry_id: str
    stage_profile_id: str
    subject_id: str
    stage_instance_id: str
    stage_index: int
    stage_kind: ConstructionStageKindV3
    predecessor_completion_attestation_id: str | None
    recorder_id: str

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _START_ISSUER:
            raise ConstructionAccountingLiveV3Error(
                "stage-start attestation is caller-minted"
            )
        for value in (
            self.lifecycle_id,
            self.counter_registry_id,
            self.stage_profile_id,
            self.subject_id,
            self.stage_instance_id,
        ):
            parse_content_id(value)
        _positive(self.stage_index, "stage_index")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        _identifier(self.recorder_id, "recorder_id")
        predecessor = self.predecessor_completion_attestation_id
        if predecessor is not None:
            parse_content_id(predecessor)
        if (self.stage_index == 1) != (predecessor is None):
            raise ConstructionAccountingLiveV3Error(
                "only the first stage may lack a predecessor completion"
            )
        expected = _stage_instance_id(
            lifecycle_id=self.lifecycle_id,
            subject_id=self.subject_id,
            stage_index=self.stage_index,
            stage_kind=self.stage_kind,
            predecessor_completion_attestation_id=predecessor,
        )
        if self.stage_instance_id != expected:
            raise ConstructionAccountingLiveV3Error(
                "stage-instance identity differs from its lifecycle position"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_stage_start_attestation.v3",
            "schema_version": SCHEMA_VERSION,
            "lifecycle_id": self.lifecycle_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "subject_id": self.subject_id,
            "stage_instance_id": self.stage_instance_id,
            "stage_index": self.stage_index,
            "stage_kind": self.stage_kind.value,
            "predecessor_completion_attestation_id": (
                self.predecessor_completion_attestation_id
            ),
            "recorder_id": self.recorder_id,
            "issued_before_first_operation_event": True,
        }

    @property
    def start_attestation_id(self) -> str:
        return content_id(
            CONSTRUCTION_STAGE_START_ATTESTATION_V3_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "stage_start_attestation_id": self.start_attestation_id,
        }


@dataclass(frozen=True, slots=True)
class ConstructionOperationEventV3:
    _issuer: InitVar[object]
    lifecycle_id: str
    counter_registry_id: str
    subject_id: str
    stage_instance_id: str
    stage_start_attestation_id: str
    stage_index: int
    stage_kind: ConstructionStageKindV3
    event_sequence: int
    operation_site_id: str
    path: str
    value: int
    recorder_id: str
    semantics_id: str
    owner: str
    unit: str
    lane: LaneEnum
    scope: str
    reducer: ReducerEnum

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _EVENT_ISSUER:
            raise ConstructionAccountingLiveV3Error(
                "construction operation event is caller-minted"
            )
        for value in (
            self.lifecycle_id,
            self.counter_registry_id,
            self.subject_id,
            self.stage_instance_id,
            self.stage_start_attestation_id,
        ):
            parse_content_id(value)
        _positive(self.stage_index, "stage_index")
        _positive(self.event_sequence, "event_sequence")
        _identifier(self.operation_site_id, "operation_site_id")
        _identifier(self.path, "counter path")
        _positive(self.value, self.path)
        _identifier(self.recorder_id, "recorder_id")
        _identifier(self.semantics_id, "semantics_id")
        _identifier(self.owner, "owner")
        _identifier(self.unit, "unit")
        _identifier(self.scope, "scope")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        try:
            object.__setattr__(self, "lane", LaneEnum(self.lane))
            object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingLiveV3Error(
                "operation-event lane or reducer is invalid"
            ) from error

    def verify_against(self, leaf: Any) -> None:
        if (
            self.path,
            self.semantics_id,
            self.owner,
            self.unit,
            self.lane,
            self.scope,
            self.reducer,
        ) != (
            leaf.path,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        ):
            raise ConstructionAccountingLiveV3Error(
                f"operation-event metadata mismatch for {self.path!r}"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_operation_event.v3",
            "schema_version": SCHEMA_VERSION,
            "lifecycle_id": self.lifecycle_id,
            "counter_registry_id": self.counter_registry_id,
            "subject_id": self.subject_id,
            "stage_instance_id": self.stage_instance_id,
            "stage_start_attestation_id": (
                self.stage_start_attestation_id
            ),
            "stage_index": self.stage_index,
            "stage_kind": self.stage_kind.value,
            "event_sequence": self.event_sequence,
            "operation_site_id": self.operation_site_id,
            "path": self.path,
            "value": self.value,
            "recorder_id": self.recorder_id,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "lane": self.lane.value,
            "scope": self.scope,
            "reducer": self.reducer.value,
        }

    @property
    def event_id(self) -> str:
        return content_id(
            CONSTRUCTION_OPERATION_EVENT_V3_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operation_event_id": self.event_id}


def _event_transcript_id(
    start: StageStartAttestationV3,
    events: Sequence[ConstructionOperationEventV3],
) -> str:
    rows = tuple(events)
    return content_id(
        CONSTRUCTION_STAGE_EVENT_TRANSCRIPT_V3_DOMAIN,
        {
            "schema": "acfqp.construction_stage_event_transcript.v3",
            "schema_version": SCHEMA_VERSION,
            "lifecycle_id": start.lifecycle_id,
            "subject_id": start.subject_id,
            "stage_instance_id": start.stage_instance_id,
            "stage_start_attestation_id": start.start_attestation_id,
            "stage_index": start.stage_index,
            "stage_kind": start.stage_kind.value,
            "operation_event_ids": [item.event_id for item in rows],
            "event_count": len(rows),
        },
    )


@dataclass(frozen=True, slots=True)
class StageCompletionAttestationV3:
    _issuer: InitVar[object]
    lifecycle_id: str
    counter_registry_id: str
    stage_profile_id: str
    subject_id: str
    stage_instance_id: str
    stage_start_attestation_id: str
    stage_index: int
    stage_kind: ConstructionStageKindV3
    event_transcript_id: str
    event_count: int
    outcome: StageCompletionOutcomeV3
    output_artifact_ids: tuple[str, ...]
    failure_evidence_ids: tuple[str, ...]

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _COMPLETION_ISSUER:
            raise ConstructionAccountingLiveV3Error(
                "stage-completion attestation is caller-minted"
            )
        for value in (
            self.lifecycle_id,
            self.counter_registry_id,
            self.stage_profile_id,
            self.subject_id,
            self.stage_instance_id,
            self.stage_start_attestation_id,
            self.event_transcript_id,
        ):
            parse_content_id(value)
        _positive(self.stage_index, "stage_index")
        _nonnegative(self.event_count, "event_count")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        object.__setattr__(self, "outcome", _outcome(self.outcome))
        _canonical_ids(
            self.output_artifact_ids, field_name="output_artifact_ids"
        )
        _canonical_ids(
            self.failure_evidence_ids,
            field_name="failure_evidence_ids",
        )
        if (
            self.outcome is StageCompletionOutcomeV3.COMPLETED
            and self.failure_evidence_ids
        ) or (
            self.outcome is StageCompletionOutcomeV3.ABORTED
            and not self.failure_evidence_ids
        ):
            raise ConstructionAccountingLiveV3Error(
                "stage completion outcome and failure evidence disagree"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_stage_completion_attestation.v3",
            "schema_version": SCHEMA_VERSION,
            "lifecycle_id": self.lifecycle_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "subject_id": self.subject_id,
            "stage_instance_id": self.stage_instance_id,
            "stage_start_attestation_id": (
                self.stage_start_attestation_id
            ),
            "stage_index": self.stage_index,
            "stage_kind": self.stage_kind.value,
            "event_transcript_id": self.event_transcript_id,
            "event_count": self.event_count,
            "outcome": self.outcome.value,
            "output_artifact_ids": list(self.output_artifact_ids),
            "failure_evidence_ids": list(self.failure_evidence_ids),
            "issued_after_last_operation_event": True,
        }

    @property
    def completion_attestation_id(self) -> str:
        return content_id(
            CONSTRUCTION_STAGE_COMPLETION_ATTESTATION_V3_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "stage_completion_attestation_id": (
                self.completion_attestation_id
            ),
        }


@dataclass(frozen=True, slots=True)
class CounterRecordV3:
    counter_registry_id: str
    lifecycle_id: str
    subject_id: str
    stage_instance_id: str
    stage_start_attestation_id: str
    stage_index: int
    stage_kind: ConstructionStageKindV3
    path: str
    value: int
    observed: bool
    recorder_id: str
    semantics_id: str
    owner: str
    unit: str
    lane: LaneEnum
    scope: str
    reducer: ReducerEnum

    def __post_init__(self) -> None:
        for value in (
            self.counter_registry_id,
            self.lifecycle_id,
            self.subject_id,
            self.stage_instance_id,
            self.stage_start_attestation_id,
        ):
            parse_content_id(value)
        _positive(self.stage_index, "stage_index")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        _identifier(self.path, "counter path")
        _nonnegative(self.value, self.path)
        if self.observed is not True:
            raise ConstructionAccountingLiveV3Error(
                "missing or unobserved records cannot be native zero"
            )
        _identifier(self.recorder_id, "recorder_id")
        _identifier(self.semantics_id, "semantics_id")
        _identifier(self.owner, "owner")
        _identifier(self.unit, "unit")
        _identifier(self.scope, "scope")
        try:
            object.__setattr__(self, "lane", LaneEnum(self.lane))
            object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingLiveV3Error(
                "counter-record lane or reducer is invalid"
            ) from error

    @classmethod
    def observe(
        cls,
        registry: CounterRegistryV3,
        start: StageStartAttestationV3,
        path: str,
        value: int,
    ) -> "CounterRecordV3":
        try:
            leaf = registry.by_path[path]
        except KeyError as error:
            raise ConstructionAccountingLiveV3Error(
                f"unknown v3 counter path {path!r}"
            ) from error
        return cls(
            registry.registry_id,
            start.lifecycle_id,
            start.subject_id,
            start.stage_instance_id,
            start.start_attestation_id,
            start.stage_index,
            start.stage_kind,
            path,
            value,
            True,
            start.recorder_id,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        )

    def verify_against(self, leaf: Any) -> None:
        if (
            self.semantics_id,
            self.owner,
            self.unit,
            self.lane,
            self.scope,
            self.reducer,
        ) != (
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        ):
            raise ConstructionAccountingLiveV3Error(
                f"counter metadata mismatch for {self.path!r}"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.counter_record.v3",
            "schema_version": SCHEMA_VERSION,
            "counter_registry_id": self.counter_registry_id,
            "lifecycle_id": self.lifecycle_id,
            "subject_id": self.subject_id,
            "stage_instance_id": self.stage_instance_id,
            "stage_start_attestation_id": (
                self.stage_start_attestation_id
            ),
            "stage_index": self.stage_index,
            "stage_kind": self.stage_kind.value,
            "path": self.path,
            "value": self.value,
            "observed": self.observed,
            "recorder_id": self.recorder_id,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "lane": self.lane.value,
            "scope": self.scope,
            "reducer": self.reducer.value,
        }

    @property
    def record_id(self) -> str:
        return content_id(
            CONSTRUCTION_COUNTER_RECORD_V3_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_record_id": self.record_id}

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "CounterRecordV3":
        expected = {
            "schema",
            "schema_version",
            "counter_registry_id",
            "lifecycle_id",
            "subject_id",
            "stage_instance_id",
            "stage_start_attestation_id",
            "stage_index",
            "stage_kind",
            "path",
            "value",
            "observed",
            "recorder_id",
            "semantics_id",
            "owner",
            "unit",
            "lane",
            "scope",
            "reducer",
            "counter_record_id",
        }
        if (
            type(document) is not dict
            or set(document) != expected
            or document["schema"] != "acfqp.counter_record.v3"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise ConstructionAccountingLiveV3Error(
                "counter-record field set mismatch"
            )
        result = cls(
            document["counter_registry_id"],
            document["lifecycle_id"],
            document["subject_id"],
            document["stage_instance_id"],
            document["stage_start_attestation_id"],
            document["stage_index"],
            document["stage_kind"],
            document["path"],
            document["value"],
            document["observed"],
            document["recorder_id"],
            document["semantics_id"],
            document["owner"],
            document["unit"],
            document["lane"],
            document["scope"],
            document["reducer"],
        )
        if document["counter_record_id"] != result.record_id:
            raise ConstructionAccountingLiveV3Error(
                "counter-record content ID mismatch"
            )
        return result


def _validate_reconciliation(values: Mapping[str, int]) -> None:
    for total, success, failure in (
        ("route.attempts", "route.successes", "route.failures"),
        ("solver.attempts", "solver.successes", "solver.failures"),
    ):
        if values[total] != values[success] + values[failure]:
            raise ConstructionAccountingLiveV3Error(
                f"reconciliation failed for {total}"
            )
    if values["process.launches"] != (
        values["process.exit_successes"]
        + values["process.exit_failures"]
    ):
        raise ConstructionAccountingLiveV3Error(
            "process launch and exit reconciliation failed"
        )


def _replay_values(
    *,
    start: StageStartAttestationV3,
    events: Sequence[ConstructionOperationEventV3],
    registry: CounterRegistryV3,
    stage_profile: StageProfileV3,
) -> dict[str, int]:
    values = {path: 0 for path in registry.required_paths}
    allowed = set(_allowed_nonzero_paths(stage_profile, start.stage_kind))
    rows = tuple(events)
    for sequence, event in enumerate(rows, 1):
        if type(event) is not ConstructionOperationEventV3:
            raise ConstructionAccountingLiveV3Error(
                "event transcript contains a foreign value"
            )
        if (
            event.lifecycle_id != start.lifecycle_id
            or event.counter_registry_id != registry.registry_id
            or event.subject_id != start.subject_id
            or event.stage_instance_id != start.stage_instance_id
            or event.stage_start_attestation_id
            != start.start_attestation_id
            or event.stage_index != start.stage_index
            or event.stage_kind is not start.stage_kind
            or event.event_sequence != sequence
            or event.recorder_id != start.recorder_id
        ):
            raise ConstructionAccountingLiveV3Error(
                "operation event is reordered or belongs to another stage"
            )
        if event.path not in values or event.path not in allowed:
            raise ConstructionAccountingLiveV3Error(
                f"operation event path {event.path!r} is not stage-owned"
            )
        leaf = registry.by_path[event.path]
        event.verify_against(leaf)
        if event.path in _DERIVED_TOTAL_PATHS:
            raise ConstructionAccountingLiveV3Error(
                f"{event.path!r} must be derived from outcome events"
            )
        if event.reducer is ReducerEnum.SUM:
            values[event.path] += event.value
        else:
            values[event.path] = max(values[event.path], event.value)
    values["route.attempts"] = (
        values["route.successes"] + values["route.failures"]
    )
    values["solver.attempts"] = (
        values["solver.successes"] + values["solver.failures"]
    )
    _validate_reconciliation(values)
    return values


@dataclass(frozen=True, slots=True)
class WorkVectorV3:
    counter_registry_id: str
    stage_profile_id: str
    lifecycle_id: str
    subject_id: str
    stage_instance_id: str
    stage_start_attestation_id: str
    stage_completion_attestation_id: str
    event_transcript_id: str
    stage_index: int
    stage_kind: ConstructionStageKindV3
    operation_event_ids: tuple[str, ...]
    records: tuple[CounterRecordV3, ...]

    def __post_init__(self) -> None:
        for value in (
            self.counter_registry_id,
            self.stage_profile_id,
            self.lifecycle_id,
            self.subject_id,
            self.stage_instance_id,
            self.stage_start_attestation_id,
            self.stage_completion_attestation_id,
            self.event_transcript_id,
        ):
            parse_content_id(value)
        _positive(self.stage_index, "stage_index")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        for event_id in self.operation_event_ids:
            parse_content_id(event_id)
        if len(set(self.operation_event_ids)) != len(
            self.operation_event_ids
        ):
            raise ConstructionAccountingLiveV3Error(
                "work vector repeats an operation-event ID"
            )
        if (
            not self.records
            or tuple(sorted(self.records, key=lambda row: row.path))
            != self.records
            or len({row.path for row in self.records}) != len(self.records)
        ):
            raise ConstructionAccountingLiveV3Error(
                "work-vector records must be nonempty, unique, and sorted"
            )

    @property
    def values(self) -> dict[str, int]:
        return {row.path: row.value for row in self.records}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.work_vector.v3",
            "schema_version": SCHEMA_VERSION,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "lifecycle_id": self.lifecycle_id,
            "subject_id": self.subject_id,
            "stage_instance_id": self.stage_instance_id,
            "stage_start_attestation_id": (
                self.stage_start_attestation_id
            ),
            "stage_completion_attestation_id": (
                self.stage_completion_attestation_id
            ),
            "event_transcript_id": self.event_transcript_id,
            "stage_index": self.stage_index,
            "stage_kind": self.stage_kind.value,
            "operation_event_ids": list(self.operation_event_ids),
            "counter_record_ids": [row.record_id for row in self.records],
        }

    @property
    def work_vector_id(self) -> str:
        return content_id(
            CONSTRUCTION_WORK_VECTOR_V3_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "records": [row.to_document() for row in self.records],
            "work_vector_id": self.work_vector_id,
        }

    @classmethod
    def from_document(
        cls,
        document: Mapping[str, Any],
        registry: CounterRegistryV3,
        stage_profile: StageProfileV3,
    ) -> "WorkVectorV3":
        expected = {
            "schema",
            "schema_version",
            "counter_registry_id",
            "stage_profile_id",
            "lifecycle_id",
            "subject_id",
            "stage_instance_id",
            "stage_start_attestation_id",
            "stage_completion_attestation_id",
            "event_transcript_id",
            "stage_index",
            "stage_kind",
            "operation_event_ids",
            "counter_record_ids",
            "records",
            "work_vector_id",
        }
        if (
            type(document) is not dict
            or set(document) != expected
            or document["schema"] != "acfqp.work_vector.v3"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["operation_event_ids"]) is not list
            or type(document["counter_record_ids"]) is not list
            or type(document["records"]) is not list
        ):
            raise ConstructionAccountingLiveV3Error(
                "work-vector field set mismatch"
            )
        records = tuple(
            CounterRecordV3.from_document(row)
            for row in document["records"]
        )
        if document["counter_record_ids"] != [
            row.record_id for row in records
        ]:
            raise ConstructionAccountingLiveV3Error(
                "work-vector record-ID list mismatch"
            )
        result = cls(
            document["counter_registry_id"],
            document["stage_profile_id"],
            document["lifecycle_id"],
            document["subject_id"],
            document["stage_instance_id"],
            document["stage_start_attestation_id"],
            document["stage_completion_attestation_id"],
            document["event_transcript_id"],
            document["stage_index"],
            document["stage_kind"],
            tuple(document["operation_event_ids"]),
            records,
        )
        validate_work_vector_v3(result, registry, stage_profile)
        if document["work_vector_id"] != result.work_vector_id:
            raise ConstructionAccountingLiveV3Error(
                "work-vector content ID mismatch"
            )
        return result


def validate_work_vector_v3(
    vector: WorkVectorV3,
    registry: CounterRegistryV3,
    stage_profile: StageProfileV3,
) -> None:
    try:
        registry.validate_official_catalogue()
        stage_profile.validate(registry)
    except ConstructionAccountingRegistryV3Error as error:
        raise ConstructionAccountingLiveV3Error(str(error)) from error
    if (
        vector.counter_registry_id != registry.registry_id
        or vector.stage_profile_id != stage_profile.stage_profile_id
    ):
        raise ConstructionAccountingLiveV3Error(
            "work-vector registry or stage-profile identity mismatch"
        )
    expected_paths = set(registry.required_paths)
    if {row.path for row in vector.records} != expected_paths:
        raise ConstructionAccountingLiveV3Error(
            "work vector must contain every required leaf exactly once"
        )
    for row in vector.records:
        if (
            row.counter_registry_id != registry.registry_id
            or row.lifecycle_id != vector.lifecycle_id
            or row.subject_id != vector.subject_id
            or row.stage_instance_id != vector.stage_instance_id
            or row.stage_start_attestation_id
            != vector.stage_start_attestation_id
            or row.stage_index != vector.stage_index
            or row.stage_kind is not vector.stage_kind
        ):
            raise ConstructionAccountingLiveV3Error(
                "work vector contains a foreign counter record"
            )
        row.verify_against(registry.by_path[row.path])
    _validate_reconciliation(vector.values)
    allowed = set(_allowed_nonzero_paths(stage_profile, vector.stage_kind))
    forbidden = sorted(
        path
        for path, value in vector.values.items()
        if value and path not in allowed
    )
    if forbidden:
        raise ConstructionAccountingLiveV3Error(
            f"stage-family exclusivity violation: {forbidden!r}"
        )


@dataclass(frozen=True, slots=True)
class ComparisonVectorV3:
    comparison_profile_id: str
    work_vector_id: str
    lifecycle_id: str
    subject_id: str
    stage_instance_id: str
    stage_index: int
    stage_kind: ConstructionStageKindV3
    values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for value in (
            self.comparison_profile_id,
            self.work_vector_id,
            self.lifecycle_id,
            self.subject_id,
            self.stage_instance_id,
        ):
            parse_content_id(value)
        _positive(self.stage_index, "stage_index")
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        if (
            tuple(sorted(self.values)) != self.values
            or len(dict(self.values)) != len(self.values)
            or tuple(name for name, _value in self.values) != SHARED_AXES
        ):
            raise ConstructionAccountingLiveV3Error(
                "comparison vector must contain the exact eight axes"
            )
        for name, value in self.values:
            _identifier(name, "comparison axis")
            _nonnegative(value, name)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_vector.v3",
            "schema_version": SCHEMA_VERSION,
            "comparison_profile_id": self.comparison_profile_id,
            "work_vector_id": self.work_vector_id,
            "lifecycle_id": self.lifecycle_id,
            "subject_id": self.subject_id,
            "stage_instance_id": self.stage_instance_id,
            "stage_index": self.stage_index,
            "stage_kind": self.stage_kind.value,
            "values": [
                {"axis": name, "value": value}
                for name, value in self.values
            ],
        }

    @property
    def comparison_vector_id(self) -> str:
        return content_id(
            CONSTRUCTION_COMPARISON_VECTOR_V3_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "comparison_vector_id": self.comparison_vector_id,
        }


@dataclass(frozen=True, slots=True)
class ActualProjectionProofV3:
    actual_projection_profile_id: str
    work_vector_id: str
    comparison_vector_id: str
    counter_record_ids: tuple[str, ...]
    operation_event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (
            self.actual_projection_profile_id,
            self.work_vector_id,
            self.comparison_vector_id,
            *self.counter_record_ids,
            *self.operation_event_ids,
        ):
            parse_content_id(value)
        if (
            len(set(self.counter_record_ids)) != len(self.counter_record_ids)
            or len(set(self.operation_event_ids))
            != len(self.operation_event_ids)
        ):
            raise ConstructionAccountingLiveV3Error(
                "actual projection repeats a source identity"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_proof.v3",
            "schema_version": SCHEMA_VERSION,
            "actual_projection_profile_id": (
                self.actual_projection_profile_id
            ),
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "counter_record_ids": list(self.counter_record_ids),
            "operation_event_ids": list(self.operation_event_ids),
            "all_operational_leaves_projected_exactly_once": True,
            "nonoperational_leaves_projected": False,
            "values_derived_from_event_replay": True,
            "scalar_cost_defined": False,
        }

    @property
    def actual_projection_proof_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACTUAL_PROJECTION_PROOF_V3_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actual_projection_proof_id": (
                self.actual_projection_proof_id
            ),
        }


def derive_actual_projection_v3(
    vector: WorkVectorV3,
    registry: CounterRegistryV3,
    stage_profile: StageProfileV3,
    comparison: ComparisonProfileV3,
    actual_profile: ActualProjectionProfileV3,
) -> tuple[ComparisonVectorV3, ActualProjectionProofV3]:
    validate_work_vector_v3(vector, registry, stage_profile)
    try:
        comparison.validate(registry)
        actual_profile.validate(registry, comparison)
    except ConstructionAccountingRegistryV3Error as error:
        raise ConstructionAccountingLiveV3Error(str(error)) from error
    source = vector.values
    values = {row.name: 0 for row in comparison.axes}
    for term in actual_profile.terms:
        contribution = source[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            values[term.target_axis] += contribution
        else:
            values[term.target_axis] = max(
                values[term.target_axis], contribution
            )
    projected = ComparisonVectorV3(
        comparison.comparison_profile_id,
        vector.work_vector_id,
        vector.lifecycle_id,
        vector.subject_id,
        vector.stage_instance_id,
        vector.stage_index,
        vector.stage_kind,
        tuple(sorted(values.items())),
    )
    proof = ActualProjectionProofV3(
        actual_profile.actual_projection_profile_id,
        vector.work_vector_id,
        projected.comparison_vector_id,
        tuple(row.record_id for row in vector.records),
        vector.operation_event_ids,
    )
    return projected, proof


@dataclass(frozen=True, slots=True)
class RecordedStageWorkV3:
    stage_start: StageStartAttestationV3
    operation_events: tuple[ConstructionOperationEventV3, ...]
    stage_completion: StageCompletionAttestationV3
    work_vector: WorkVectorV3
    comparison_vector: ComparisonVectorV3
    actual_projection_proof: ActualProjectionProofV3

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.recorded_stage_work.v3",
            "schema_version": SCHEMA_VERSION,
            "stage_start": self.stage_start.to_document(),
            "operation_events": [
                item.to_document() for item in self.operation_events
            ],
            "stage_completion": self.stage_completion.to_document(),
            "work_vector": self.work_vector.to_document(),
            "comparison_vector": self.comparison_vector.to_document(),
            "actual_projection_proof": (
                self.actual_projection_proof.to_document()
            ),
        }


def verify_recorded_stage_work_v3(
    recorded: RecordedStageWorkV3,
    registry: CounterRegistryV3,
    stage_profile: StageProfileV3,
    comparison: ComparisonProfileV3,
    actual_profile: ActualProjectionProfileV3,
) -> None:
    if type(recorded) is not RecordedStageWorkV3:
        raise ConstructionAccountingLiveV3Error(
            "recorded stage work has a foreign type"
        )
    start = recorded.stage_start
    completion = recorded.stage_completion
    events = recorded.operation_events
    if (
        type(start) is not StageStartAttestationV3
        or type(completion) is not StageCompletionAttestationV3
        or type(events) is not tuple
    ):
        raise ConstructionAccountingLiveV3Error(
            "recorded stage evidence has a foreign type"
        )
    if (
        start.counter_registry_id != registry.registry_id
        or start.stage_profile_id != stage_profile.stage_profile_id
        or completion.lifecycle_id != start.lifecycle_id
        or completion.counter_registry_id != start.counter_registry_id
        or completion.stage_profile_id != start.stage_profile_id
        or completion.subject_id != start.subject_id
        or completion.stage_instance_id != start.stage_instance_id
        or completion.stage_start_attestation_id
        != start.start_attestation_id
        or completion.stage_index != start.stage_index
        or completion.stage_kind is not start.stage_kind
        or completion.event_count != len(events)
        or completion.event_transcript_id
        != _event_transcript_id(start, events)
    ):
        raise ConstructionAccountingLiveV3Error(
            "stage start, transcript, and completion do not form one chain"
        )
    values = _replay_values(
        start=start,
        events=events,
        registry=registry,
        stage_profile=stage_profile,
    )
    expected_records = tuple(
        CounterRecordV3.observe(registry, start, path, values[path])
        for path in sorted(registry.required_paths)
    )
    vector = recorded.work_vector
    expected_vector = WorkVectorV3(
        registry.registry_id,
        stage_profile.stage_profile_id,
        start.lifecycle_id,
        start.subject_id,
        start.stage_instance_id,
        start.start_attestation_id,
        completion.completion_attestation_id,
        completion.event_transcript_id,
        start.stage_index,
        start.stage_kind,
        tuple(item.event_id for item in events),
        expected_records,
    )
    if vector != expected_vector:
        raise ConstructionAccountingLiveV3Error(
            "work vector differs from exact operation-event replay"
        )
    expected_comparison, expected_proof = derive_actual_projection_v3(
        expected_vector,
        registry,
        stage_profile,
        comparison,
        actual_profile,
    )
    if (
        recorded.comparison_vector != expected_comparison
        or recorded.actual_projection_proof != expected_proof
    ):
        raise ConstructionAccountingLiveV3Error(
            "comparison vector or actual projection differs from replay"
        )


class ConstructionActiveStageV3:
    """Single-use handle for one stage owned by a trusted lifecycle."""

    def __init__(
        self,
        _issuer: object,
        lifecycle: "ConstructionAccountingLifecycleV3",
        start: StageStartAttestationV3,
    ) -> None:
        if _issuer is not _ACTIVE_STAGE_ISSUER:
            raise ConstructionAccountingLiveV3Error(
                "active construction stage is caller-minted"
            )
        self._lifecycle = lifecycle
        self.start = start
        self._events: list[ConstructionOperationEventV3] = []
        self._sealed = False

    def _leaf(self, path: str, *, expect_peak: bool) -> Any:
        if self._sealed:
            raise ConstructionAccountingLiveV3Error(
                "construction stage is already sealed"
            )
        try:
            leaf = self._lifecycle.registry.by_path[path]
        except KeyError as error:
            raise ConstructionAccountingLiveV3Error(
                f"unknown v3 counter path {path!r}"
            ) from error
        if not leaf.required:
            raise ConstructionAccountingLiveV3Error(
                "optional leaves cannot enter a live stage WorkVector"
            )
        allowed = _allowed_nonzero_paths(
            self._lifecycle.stage_profile, self.start.stage_kind
        )
        if path not in allowed:
            raise ConstructionAccountingLiveV3Error(
                f"{path!r} is outside {self.start.stage_kind.value}"
            )
        if path in _DERIVED_TOTAL_PATHS:
            raise ConstructionAccountingLiveV3Error(
                f"{path!r} is derived from success and failure events"
            )
        is_peak = leaf.reducer is ReducerEnum.MAX
        if is_peak != expect_peak:
            operation = "observe_peak" if is_peak else "add"
            raise ConstructionAccountingLiveV3Error(
                f"{path!r} must use {operation}"
            )
        return leaf

    def _emit(
        self,
        *,
        path: str,
        value: int,
        operation_site_id: str,
        expect_peak: bool,
    ) -> ConstructionOperationEventV3:
        leaf = self._leaf(path, expect_peak=expect_peak)
        event = ConstructionOperationEventV3(
            _EVENT_ISSUER,
            self.start.lifecycle_id,
            self._lifecycle.registry.registry_id,
            self.start.subject_id,
            self.start.stage_instance_id,
            self.start.start_attestation_id,
            self.start.stage_index,
            self.start.stage_kind,
            len(self._events) + 1,
            operation_site_id,
            path,
            _positive(value, path),
            self.start.recorder_id,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        )
        self._events.append(event)
        return event

    def add(
        self,
        path: str,
        amount: int = 1,
        *,
        operation_site_id: str,
    ) -> ConstructionOperationEventV3:
        return self._emit(
            path=path,
            value=amount,
            operation_site_id=operation_site_id,
            expect_peak=False,
        )

    def observe_peak(
        self,
        path: str,
        value: int,
        *,
        operation_site_id: str,
    ) -> ConstructionOperationEventV3:
        return self._emit(
            path=path,
            value=value,
            operation_site_id=operation_site_id,
            expect_peak=True,
        )

    def _seal(
        self,
        *,
        outcome: StageCompletionOutcomeV3,
        output_artifact_ids: Sequence[str],
        failure_evidence_ids: Sequence[str],
    ) -> RecordedStageWorkV3:
        if self._sealed:
            raise ConstructionAccountingLiveV3Error(
                "construction stage is already sealed"
            )
        outputs = tuple(sorted(output_artifact_ids))
        failures = tuple(sorted(failure_evidence_ids))
        _canonical_ids(outputs, field_name="output_artifact_ids")
        _canonical_ids(failures, field_name="failure_evidence_ids")
        events = tuple(self._events)
        transcript_id = _event_transcript_id(self.start, events)
        completion = StageCompletionAttestationV3(
            _COMPLETION_ISSUER,
            self.start.lifecycle_id,
            self._lifecycle.registry.registry_id,
            self._lifecycle.stage_profile.stage_profile_id,
            self.start.subject_id,
            self.start.stage_instance_id,
            self.start.start_attestation_id,
            self.start.stage_index,
            self.start.stage_kind,
            transcript_id,
            len(events),
            outcome,
            outputs,
            failures,
        )
        values = _replay_values(
            start=self.start,
            events=events,
            registry=self._lifecycle.registry,
            stage_profile=self._lifecycle.stage_profile,
        )
        records = tuple(
            CounterRecordV3.observe(
                self._lifecycle.registry,
                self.start,
                path,
                values[path],
            )
            for path in sorted(self._lifecycle.registry.required_paths)
        )
        vector = WorkVectorV3(
            self._lifecycle.registry.registry_id,
            self._lifecycle.stage_profile.stage_profile_id,
            self.start.lifecycle_id,
            self.start.subject_id,
            self.start.stage_instance_id,
            self.start.start_attestation_id,
            completion.completion_attestation_id,
            transcript_id,
            self.start.stage_index,
            self.start.stage_kind,
            tuple(item.event_id for item in events),
            records,
        )
        projected, proof = derive_actual_projection_v3(
            vector,
            self._lifecycle.registry,
            self._lifecycle.stage_profile,
            self._lifecycle.comparison_profile,
            self._lifecycle.actual_projection_profile,
        )
        recorded = RecordedStageWorkV3(
            self.start,
            events,
            completion,
            vector,
            projected,
            proof,
        )
        verify_recorded_stage_work_v3(
            recorded,
            self._lifecycle.registry,
            self._lifecycle.stage_profile,
            self._lifecycle.comparison_profile,
            self._lifecycle.actual_projection_profile,
        )
        self._sealed = True
        self._lifecycle._accept_stage(self, recorded)  # noqa: SLF001
        return recorded

    def complete(
        self, *, output_artifact_ids: Sequence[str] = ()
    ) -> RecordedStageWorkV3:
        return self._seal(
            outcome=StageCompletionOutcomeV3.COMPLETED,
            output_artifact_ids=output_artifact_ids,
            failure_evidence_ids=(),
        )

    def abort(
        self,
        *,
        failure_evidence_ids: Sequence[str],
        output_artifact_ids: Sequence[str] = (),
    ) -> RecordedStageWorkV3:
        return self._seal(
            outcome=StageCompletionOutcomeV3.ABORTED,
            output_artifact_ids=output_artifact_ids,
            failure_evidence_ids=failure_evidence_ids,
        )


class ConstructionAccountingLifecycleV3:
    """Mutable one-way owner of a preregistered construction stage plan."""

    def __init__(
        self,
        _issuer: object,
        *,
        subject_id: str,
        recorder_id: str,
        stage_plan: tuple[ConstructionStageKindV3, ...],
        registry: CounterRegistryV3,
        stage_profile: StageProfileV3,
        comparison_profile: ComparisonProfileV3,
        actual_projection_profile: ActualProjectionProfileV3,
    ) -> None:
        if _issuer is not _LIFECYCLE_ISSUER:
            raise ConstructionAccountingLiveV3Error(
                "construction accounting lifecycle is caller-minted"
            )
        parse_content_id(subject_id)
        _identifier(recorder_id, "recorder_id")
        if not stage_plan or any(
            type(item) is not ConstructionStageKindV3
            for item in stage_plan
        ):
            raise ConstructionAccountingLiveV3Error(
                "stage plan must be a nonempty exact enum tuple"
            )
        try:
            registry.validate_official_catalogue()
            stage_profile.validate(registry)
            comparison_profile.validate(registry)
            actual_projection_profile.validate(
                registry, comparison_profile
            )
        except ConstructionAccountingRegistryV3Error as error:
            raise ConstructionAccountingLiveV3Error(str(error)) from error
        self.subject_id = subject_id
        self.recorder_id = recorder_id
        self.stage_plan = stage_plan
        self.registry = registry
        self.stage_profile = stage_profile
        self.comparison_profile = comparison_profile
        self.actual_projection_profile = actual_projection_profile
        self.lifecycle_id = _lifecycle_id(
            counter_registry_id=registry.registry_id,
            stage_profile_id=stage_profile.stage_profile_id,
            subject_id=subject_id,
            recorder_id=recorder_id,
            stage_plan=stage_plan,
        )
        self._active: ConstructionActiveStageV3 | None = None
        self._recorded: list[RecordedStageWorkV3] = []
        self._ended = False
        self._aborted = False

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_lifecycle.v3",
            "schema_version": SCHEMA_VERSION,
            "counter_registry_id": self.registry.registry_id,
            "stage_profile_id": self.stage_profile.stage_profile_id,
            "subject_id": self.subject_id,
            "recorder_id": self.recorder_id,
            "stage_plan": [item.value for item in self.stage_plan],
        }

    def to_document(self) -> dict[str, Any]:
        if self.lifecycle_id != content_id(
            CONSTRUCTION_ACCOUNTING_LIFECYCLE_V3_DOMAIN,
            self._payload(),
        ):
            raise ConstructionAccountingLiveV3Error(
                "construction lifecycle identity is stale"
            )
        return {**self._payload(), "lifecycle_id": self.lifecycle_id}

    @property
    def recorded_stages(self) -> tuple[RecordedStageWorkV3, ...]:
        return tuple(self._recorded)

    @property
    def aborted(self) -> bool:
        return self._aborted

    def begin_stage(
        self, stage_kind: ConstructionStageKindV3 | str
    ) -> ConstructionActiveStageV3:
        if self._ended or self._active is not None:
            raise ConstructionAccountingLiveV3Error(
                "lifecycle is closed or already has an active stage"
            )
        index = len(self._recorded) + 1
        if index > len(self.stage_plan):
            raise ConstructionAccountingLiveV3Error(
                "lifecycle stage plan is already exhausted"
            )
        kind = _stage(stage_kind)
        if kind is not self.stage_plan[index - 1]:
            raise ConstructionAccountingLiveV3Error(
                "stage kind differs from the preregistered stage plan"
            )
        predecessor = (
            None
            if not self._recorded
            else (
                self._recorded[-1]
                .stage_completion.completion_attestation_id
            )
        )
        instance_id = _stage_instance_id(
            lifecycle_id=self.lifecycle_id,
            subject_id=self.subject_id,
            stage_index=index,
            stage_kind=kind,
            predecessor_completion_attestation_id=predecessor,
        )
        start = StageStartAttestationV3(
            _START_ISSUER,
            self.lifecycle_id,
            self.registry.registry_id,
            self.stage_profile.stage_profile_id,
            self.subject_id,
            instance_id,
            index,
            kind,
            predecessor,
            self.recorder_id,
        )
        active = ConstructionActiveStageV3(
            _ACTIVE_STAGE_ISSUER, self, start
        )
        self._active = active
        return active

    def _accept_stage(
        self,
        active: ConstructionActiveStageV3,
        recorded: RecordedStageWorkV3,
    ) -> None:
        if self._active is not active:
            raise ConstructionAccountingLiveV3Error(
                "lifecycle received a foreign active stage"
            )
        self._recorded.append(recorded)
        self._active = None
        if (
            recorded.stage_completion.outcome
            is StageCompletionOutcomeV3.ABORTED
        ):
            self._aborted = True
            self._ended = True

    def finish(self) -> tuple[RecordedStageWorkV3, ...]:
        if self._active is not None:
            raise ConstructionAccountingLiveV3Error(
                "cannot finish a lifecycle with an active stage"
            )
        if self._ended:
            return self.recorded_stages
        if len(self._recorded) != len(self.stage_plan):
            raise ConstructionAccountingLiveV3Error(
                "cannot finish before every preregistered stage completes"
            )
        self._ended = True
        return self.recorded_stages


def open_construction_accounting_lifecycle_v3(
    *,
    subject_id: str,
    recorder_id: str,
    stage_plan: Sequence[ConstructionStageKindV3 | str],
    registry: CounterRegistryV3 | None = None,
    stage_profile: StageProfileV3 | None = None,
    comparison_profile: ComparisonProfileV3 | None = None,
    actual_projection_profile: ActualProjectionProfileV3 | None = None,
) -> ConstructionAccountingLifecycleV3:
    selected_registry = registry or official_counter_registry_v3()
    selected_stage = stage_profile or official_stage_profile_v3(
        selected_registry
    )
    selected_comparison = (
        comparison_profile
        or official_comparison_profile_v3(selected_registry)
    )
    selected_actual = (
        actual_projection_profile
        or official_actual_projection_profile_v3(
            selected_registry, selected_comparison
        )
    )
    plan = tuple(_stage(item) for item in stage_plan)
    return ConstructionAccountingLifecycleV3(
        _LIFECYCLE_ISSUER,
        subject_id=subject_id,
        recorder_id=recorder_id,
        stage_plan=plan,
        registry=selected_registry,
        stage_profile=selected_stage,
        comparison_profile=selected_comparison,
        actual_projection_profile=selected_actual,
    )


__all__ = [
    "ActualProjectionProofV3",
    "ComparisonVectorV3",
    "ConstructionAccountingLifecycleV3",
    "ConstructionAccountingLiveV3Error",
    "ConstructionActiveStageV3",
    "ConstructionOperationEventV3",
    "CounterRecordV3",
    "RecordedStageWorkV3",
    "SCHEMA_VERSION",
    "StageCompletionAttestationV3",
    "StageCompletionOutcomeV3",
    "StageStartAttestationV3",
    "WorkVectorV3",
    "derive_actual_projection_v3",
    "open_construction_accounting_lifecycle_v3",
    "validate_work_vector_v3",
    "verify_recorded_stage_work_v3",
]
