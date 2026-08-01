"""Live collection boundary for the nine construction shared resources.

The receipt schemas in :mod:`construction_shared_resource_receipts_v1`
describe what evidence must eventually look like.  This module supplies the
missing event-side boundary: registered owners can append primitive events to
one identity-bound measurement window and freeze a deterministic measurement
snapshot after an explicit cutoff.

The boundary is deliberately narrower than a semantic verifier:

* absence is never converted to zero; an unobserved path needs either an
  explicit complete-window zero attestation or a typed unavailable record;
* SUM paths accept positive primitive events and MAX paths accept positive
  peak observations through different methods;
* hashes require a registered purpose, and accounting/provenance purposes are
  retained as excluded events rather than charged recursively;
* integrity and protocol counters count named predicate evaluations on both
  PASS and FAIL; and
* mounted/working peaks only accept exact supervisor evidence kinds.
  Process-local ``/proc`` self reports and frozen caps are not exact evidence
  kinds in this contract; without a cgroup peak the row stays unavailable.

Snapshots are structurally replayable source claims.  V1 does not read or
semantically verify the referenced source artifacts, so it cannot issue a
formal ``CounterRecord``, ``WorkVector``, or ``ComparisonVector``.  All content
domains are registered centrally, but registration alone gives no semantic
authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import cache
import re
from threading import get_ident
from typing import Any, Mapping

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_SHARED_RESOURCE_LIVE_COMPLETE_WINDOW_ZERO_CLAIM_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_EVENT_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_ROW_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_SNAPSHOT_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_LIVE_TYPED_UNAVAILABLE_RESOLUTION_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_shared_resource_live_meter_v1"

LIVE_MEASUREMENT_EVENT_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_EVENT_V1_DOMAIN
)
LIVE_COMPLETE_WINDOW_ZERO_CLAIM_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_LIVE_COMPLETE_WINDOW_ZERO_CLAIM_V1_DOMAIN
)
LIVE_TYPED_UNAVAILABLE_RESOLUTION_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_LIVE_TYPED_UNAVAILABLE_RESOLUTION_V1_DOMAIN
)
LIVE_MEASUREMENT_ROW_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_ROW_V1_DOMAIN
)
LIVE_MEASUREMENT_SNAPSHOT_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_SNAPSHOT_V1_DOMAIN
)

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    LIVE_COMPLETE_WINDOW_ZERO_CLAIM_V1_DOMAIN,
    LIVE_MEASUREMENT_EVENT_V1_DOMAIN,
    LIVE_MEASUREMENT_ROW_V1_DOMAIN,
    LIVE_MEASUREMENT_SNAPSHOT_V1_DOMAIN,
    LIVE_TYPED_UNAVAILABLE_RESOLUTION_V1_DOMAIN,
)
LOCAL_DOMAIN_TAGS = frozenset(REQUESTED_PHASE3E_DOMAIN_TAGS)

SHARED_RESOURCE_PATHS = receipts_v1.SHARED_RESOURCE_PATHS
SUM_SHARED_RESOURCE_PATHS = receipts_v1.SUM_SHARED_RESOURCE_PATHS
MAX_SHARED_RESOURCE_PATHS = receipts_v1.MAX_SHARED_RESOURCE_PATHS

_BYTE_PATHS = frozenset({"io.read_bytes", "io.staged_bytes", "io.output_bytes"})
# A snapshot is itself part of the operational result/counter/manifest suffix.
# This V1 collector cannot both serialize that suffix and place its final byte
# total inside the same immutable snapshot.  Preserve prefix events, but force
# this path to typed unavailability until a later external suffix supervisor is
# registered and independently verified.
_SELF_REFERENTIAL_SUFFIX_PATHS = frozenset({"io.output_bytes"})
_REASON = re.compile(r"^[A-Z][A-Z0-9_]*$")


class ConstructionSharedResourceLiveMeterV1Error(ValueError):
    """The live-meter call order or supplied evidence is invalid."""


class LiveMeterStateV1(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FROZEN = "FROZEN"


class LiveMeasurementEventKindV1(str, Enum):
    HASH_FINALIZATION = "HASH_FINALIZATION"
    NAMED_OBLIGATION_EVALUATION = "NAMED_OBLIGATION_EVALUATION"
    BYTE_TRANSFER = "BYTE_TRANSFER"
    PROCESS_LAUNCH = "PROCESS_LAUNCH"
    PEAK_OBSERVATION = "PEAK_OBSERVATION"


class LiveSourceEvidenceKindV1(str, Enum):
    HASH_FACADE_EVENT = "HASH_FACADE_EVENT"
    NAMED_OBLIGATION_EVENT = "NAMED_OBLIGATION_EVENT"
    IO_WRAPPER_TRANSFER = "IO_WRAPPER_TRANSFER"
    SANDBOX_STAGER_TRANSFER = "SANDBOX_STAGER_TRANSFER"
    ARTIFACT_WRITER_TRANSFER = "ARTIFACT_WRITER_TRANSFER"
    PROCESS_SUPERVISOR_LAUNCH = "PROCESS_SUPERVISOR_LAUNCH"
    SUPERVISOR_MOUNT_MANIFEST = "SUPERVISOR_MOUNT_MANIFEST"
    CGROUP_MEMORY_PEAK = "CGROUP_MEMORY_PEAK"


class ObligationOutcomeV1(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


_BYTE_SOURCE_KIND = {
    "io.read_bytes": LiveSourceEvidenceKindV1.IO_WRAPPER_TRANSFER,
    "io.staged_bytes": LiveSourceEvidenceKindV1.SANDBOX_STAGER_TRANSFER,
    "io.output_bytes": LiveSourceEvidenceKindV1.ARTIFACT_WRITER_TRANSFER,
}
_PEAK_SOURCE_KINDS = {
    "io.mounted_bytes_peak": frozenset(
        {LiveSourceEvidenceKindV1.SUPERVISOR_MOUNT_MANIFEST}
    ),
    "memory.working_bytes_peak": frozenset(
        {LiveSourceEvidenceKindV1.CGROUP_MEMORY_PEAK}
    ),
}


def _content_id(domain_tag: str, payload: Mapping[str, Any]) -> str:
    if domain_tag not in LOCAL_DOMAIN_TAGS:
        raise ConstructionSharedResourceLiveMeterV1Error(
            "live-meter content ID used an undeclared domain"
        )
    return content_id(domain_tag, dict(payload))


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionSharedResourceLiveMeterV1Error(
            f"{field_name} must be one full content ID"
        ) from error


def _positive(value: Any, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ConstructionSharedResourceLiveMeterV1Error(
            f"{field_name} must be a positive exact integer; zero needs an explicit cutoff attestation"
        )
    return value


def _enum(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceLiveMeterV1Error(
            f"unknown {field_name} {value!r}"
        ) from error


def _reason(value: Any) -> str:
    if type(value) is not str or _REASON.fullmatch(value) is None:
        raise ConstructionSharedResourceLiveMeterV1Error(
            "unavailability reason must be one canonical public code"
        )
    return value


@cache
def _official_reducer(path: str) -> ReducerEnum:
    if path not in SHARED_RESOURCE_PATHS:
        raise ConstructionSharedResourceLiveMeterV1Error(
            f"unknown shared-resource path {path!r}"
        )
    leaf = registry_v6.official_counter_registry_v6().by_path[path]
    expected = (
        ReducerEnum.SUM
        if path in SUM_SHARED_RESOURCE_PATHS
        else ReducerEnum.MAX
    )
    if (
        not leaf.required
        or leaf.lane.value != "operational"
        or leaf.reducer is not expected
    ):
        raise ConstructionSharedResourceLiveMeterV1Error(
            "shared-resource path no longer matches registry V6"
        )
    return expected


@cache
def _official_registry_and_stage_ids() -> tuple[str, str]:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    return registry.registry_id, stage.stage_profile_id


@dataclass(frozen=True, slots=True)
class LiveMeasurementEventV1:
    identity_binding_id: str
    window_key: str
    sequence: int
    path: str
    event_kind: LiveMeasurementEventKindV1
    source_kind: LiveSourceEvidenceKindV1
    source_evidence_id: str
    observed_value: int
    charged: bool
    purpose_key: str | None = None
    obligation_key: str | None = None
    obligation_outcome: ObligationOutcomeV1 | None = None

    def __post_init__(self) -> None:
        _cid(self.identity_binding_id, "event identity binding")
        _cid(self.source_evidence_id, "event source evidence")
        if type(self.window_key) is not str or not self.window_key:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "event window key must be nonempty"
            )
        _positive(self.sequence, "event sequence")
        _positive(self.observed_value, "observed value")
        _official_reducer(self.path)
        kind = _enum(LiveMeasurementEventKindV1, self.event_kind, "event kind")
        source = _enum(LiveSourceEvidenceKindV1, self.source_kind, "source kind")
        object.__setattr__(self, "event_kind", kind)
        object.__setattr__(self, "source_kind", source)
        if type(self.charged) is not bool:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "charged must be an exact bool"
            )

        if kind is LiveMeasurementEventKindV1.HASH_FINALIZATION:
            valid = (
                self.path == "common.hash_invocations"
                and source is LiveSourceEvidenceKindV1.HASH_FACADE_EVENT
                and type(self.purpose_key) is str
                and bool(self.purpose_key)
                and self.observed_value == 1
                and self.obligation_key is None
                and self.obligation_outcome is None
            )
        elif kind is LiveMeasurementEventKindV1.NAMED_OBLIGATION_EVALUATION:
            outcome = _enum(
                ObligationOutcomeV1,
                self.obligation_outcome,
                "obligation outcome",
            )
            object.__setattr__(self, "obligation_outcome", outcome)
            valid = (
                self.path
                in {"common.integrity_checks", "common.protocol_checks"}
                and source is LiveSourceEvidenceKindV1.NAMED_OBLIGATION_EVENT
                and self.purpose_key is None
                and type(self.obligation_key) is str
                and bool(self.obligation_key)
                and self.observed_value == 1
                and self.charged is True
            )
        elif kind is LiveMeasurementEventKindV1.BYTE_TRANSFER:
            valid = (
                self.path in _BYTE_PATHS
                and source is _BYTE_SOURCE_KIND[self.path]
                and self.purpose_key is None
                and self.obligation_key is None
                and self.obligation_outcome is None
                and self.charged is True
            )
        elif kind is LiveMeasurementEventKindV1.PROCESS_LAUNCH:
            valid = (
                self.path == "process.launches"
                and source is LiveSourceEvidenceKindV1.PROCESS_SUPERVISOR_LAUNCH
                and self.observed_value == 1
                and self.purpose_key is None
                and self.obligation_key is None
                and self.obligation_outcome is None
                and self.charged is True
            )
        else:
            valid = (
                self.path in MAX_SHARED_RESOURCE_PATHS
                and source in _PEAK_SOURCE_KINDS[self.path]
                and self.purpose_key is None
                and self.obligation_key is None
                and self.obligation_outcome is None
                and self.charged is True
            )
        if not valid:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "live event kind/path/source/detail combination is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_live_measurement_event.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "identity_binding_id": self.identity_binding_id,
            "window_key": self.window_key,
            "sequence": self.sequence,
            "path": self.path,
            "event_kind": self.event_kind.value,
            "source_kind": self.source_kind.value,
            "source_evidence_id": self.source_evidence_id,
            "observed_value": self.observed_value,
            "charged": self.charged,
            "purpose_key": self.purpose_key,
            "obligation_key": self.obligation_key,
            "obligation_outcome": (
                None
                if self.obligation_outcome is None
                else self.obligation_outcome.value
            ),
            "central_domain_registered": True,
        }

    @property
    def event_id(self) -> str:
        return _content_id(LIVE_MEASUREMENT_EVENT_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "live_measurement_event_id": self.event_id}


@dataclass(frozen=True, slots=True)
class LiveCompleteWindowZeroClaimV1:
    identity_binding_id: str
    measurement_window_id: str
    path: str
    source_evidence_id: str

    def __post_init__(self) -> None:
        _cid(self.identity_binding_id, "zero-claim identity binding")
        _cid(self.measurement_window_id, "zero-claim window")
        _cid(self.source_evidence_id, "zero-claim source evidence")
        _official_reducer(self.path)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_live_complete_window_zero_claim.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "identity_binding_id": self.identity_binding_id,
            "measurement_window_id": self.measurement_window_id,
            "path": self.path,
            "source_evidence_id": self.source_evidence_id,
            "reported_value": 0,
            "observed_event_count": 0,
            "complete_through_cutoff": True,
            "immutable_at_cutoff": True,
            "source_claim_only": True,
            "source_evidence_semantics_verified": False,
            "central_domain_registered": True,
        }

    @property
    def zero_claim_id(self) -> str:
        return _content_id(
            LIVE_COMPLETE_WINDOW_ZERO_CLAIM_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "complete_window_zero_claim_id": self.zero_claim_id}


@dataclass(frozen=True, slots=True)
class LiveTypedUnavailableResolutionV1:
    identity_binding_id: str
    measurement_window_id: str
    path: str
    status: receipts_v1.MeasurementStatusV1
    reason_code: str

    def __post_init__(self) -> None:
        _cid(self.identity_binding_id, "unavailable identity binding")
        _cid(self.measurement_window_id, "unavailable window")
        _official_reducer(self.path)
        status = _enum(
            receipts_v1.MeasurementStatusV1,
            self.status,
            "measurement status",
        )
        object.__setattr__(self, "status", status)
        if status is receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "typed unavailability cannot use RECORDED_UNVERIFIED"
            )
        _reason(self.reason_code)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_live_typed_unavailable_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "identity_binding_id": self.identity_binding_id,
            "measurement_window_id": self.measurement_window_id,
            "path": self.path,
            "value": {
                "kind": self.status.value,
                "reason": self.reason_code,
            },
            "numeric_value_present": False,
            "central_domain_registered": True,
        }

    @property
    def resolution_id(self) -> str:
        return _content_id(
            LIVE_TYPED_UNAVAILABLE_RESOLUTION_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "typed_unavailable_resolution_id": self.resolution_id}


@dataclass(frozen=True, slots=True)
class LiveMeasurementRowV1:
    identity_binding_id: str
    measurement_window_id: str
    path: str
    reducer: ReducerEnum
    status: receipts_v1.MeasurementStatusV1
    value: int | None
    charged_event_ids: tuple[str, ...]
    observed_event_count: int
    zero_claim_id: str | None
    unavailable_resolution_id: str | None

    def __post_init__(self) -> None:
        _cid(self.identity_binding_id, "row identity binding")
        _cid(self.measurement_window_id, "row window")
        expected_reducer = _official_reducer(self.path)
        reducer = _enum(ReducerEnum, self.reducer, "row reducer")
        status = _enum(
            receipts_v1.MeasurementStatusV1,
            self.status,
            "row measurement status",
        )
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "status", status)
        if reducer is not expected_reducer:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "measurement row changed its registry reducer"
            )
        if (
            type(self.charged_event_ids) is not tuple
            or len(set(self.charged_event_ids)) != len(self.charged_event_ids)
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "row event IDs must be one unique tuple"
            )
        for event_id in self.charged_event_ids:
            _cid(event_id, "row event")
        if type(self.observed_event_count) is not int or self.observed_event_count < 0:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "row observed event count must be nonnegative"
            )
        if self.observed_event_count != len(self.charged_event_ids):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "row event count differs from its event IDs"
            )

        if status is receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED:
            if type(self.value) is not int or self.value < 0:
                raise ConstructionSharedResourceLiveMeterV1Error(
                    "recorded row needs a nonnegative exact source claim"
                )
            if self.value == 0:
                if (
                    self.charged_event_ids
                    or self.observed_event_count != 0
                    or self.zero_claim_id is None
                    or self.unavailable_resolution_id is not None
                ):
                    raise ConstructionSharedResourceLiveMeterV1Error(
                        "zero row requires only an explicit complete-window claim"
                    )
                _cid(self.zero_claim_id, "row zero claim")
            elif (
                not self.charged_event_ids
                or self.zero_claim_id is not None
                or self.unavailable_resolution_id is not None
            ):
                raise ConstructionSharedResourceLiveMeterV1Error(
                    "positive row requires charged events and no alternate resolution"
                )
        else:
            if (
                self.value is not None
                or self.charged_event_ids
                or self.observed_event_count != 0
                or self.zero_claim_id is not None
                or self.unavailable_resolution_id is None
            ):
                raise ConstructionSharedResourceLiveMeterV1Error(
                    "unavailable row must remain nonnumeric and reference its typed resolution"
                )
            _cid(self.unavailable_resolution_id, "row unavailable resolution")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_live_measurement_row.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "identity_binding_id": self.identity_binding_id,
            "measurement_window_id": self.measurement_window_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "status": self.status.value,
            "value": self.value,
            "charged_event_ids": list(self.charged_event_ids),
            "observed_event_count": self.observed_event_count,
            "complete_window_zero_claim_id": self.zero_claim_id,
            "typed_unavailable_resolution_id": self.unavailable_resolution_id,
            "source_evidence_semantics_verified": False,
            "numeric_projection_authorized": False,
            "central_domain_registered": True,
        }

    @property
    def row_id(self) -> str:
        return _content_id(LIVE_MEASUREMENT_ROW_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "live_measurement_row_id": self.row_id}


_SNAPSHOT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SharedResourceMeasurementSnapshotV1:
    measurement_registry_id: str
    hash_meter_profile_id: str
    obligation_registry_id: str
    identity_binding_id: str
    window: receipts_v1.SharedResourceMeasurementWindowV1 = field(repr=False)
    events: tuple[LiveMeasurementEventV1, ...] = field(repr=False)
    zero_claims: tuple[LiveCompleteWindowZeroClaimV1, ...] = field(repr=False)
    unavailable_resolutions: tuple[LiveTypedUnavailableResolutionV1, ...] = field(
        repr=False
    )
    rows: tuple[LiveMeasurementRowV1, ...] = field(repr=False)
    _issuer: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer is not _SNAPSHOT_ISSUER:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "measurement snapshots may only be issued by the live meter"
            )
        for value, name in (
            (self.measurement_registry_id, "snapshot measurement registry"),
            (self.hash_meter_profile_id, "snapshot hash profile"),
            (self.obligation_registry_id, "snapshot obligation registry"),
            (self.identity_binding_id, "snapshot identity binding"),
        ):
            _cid(value, name)
        if (
            type(self.window) is not receipts_v1.SharedResourceMeasurementWindowV1
            or self.window.state is not receipts_v1.MeasurementWindowStateV1.CLOSED
            or self.window.identity_binding_id != self.identity_binding_id
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "snapshot requires its exact closed measurement window"
            )
        if (
            type(self.events) is not tuple
            or any(type(item) is not LiveMeasurementEventV1 for item in self.events)
            or tuple(item.sequence for item in self.events)
            != tuple(sorted(item.sequence for item in self.events))
            or len({item.sequence for item in self.events}) != len(self.events)
            or len({item.event_id for item in self.events}) != len(self.events)
            or len({item.source_evidence_id for item in self.events})
            != len(self.events)
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "snapshot events must be sequence sorted and evidence unique"
            )
        if any(
            item.identity_binding_id != self.identity_binding_id
            or item.window_key != self.window.window_key
            or not (
                self.window.start_sequence
                < item.sequence
                <= self.window.cutoff_sequence
            )
            for item in self.events
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "snapshot contains an event outside its identity/window"
            )
        if (
            type(self.zero_claims) is not tuple
            or tuple(item.path for item in self.zero_claims)
            != tuple(sorted(item.path for item in self.zero_claims))
            or len({item.path for item in self.zero_claims}) != len(self.zero_claims)
            or type(self.unavailable_resolutions) is not tuple
            or tuple(item.path for item in self.unavailable_resolutions)
            != tuple(sorted(item.path for item in self.unavailable_resolutions))
            or len({item.path for item in self.unavailable_resolutions})
            != len(self.unavailable_resolutions)
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "post-cutoff resolutions must be path sorted and unique"
            )
        if any(
            item.identity_binding_id != self.identity_binding_id
            or item.measurement_window_id != self.window.window_id
            for item in (*self.zero_claims, *self.unavailable_resolutions)
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "snapshot contains a transplanted post-cutoff resolution"
            )
        if (
            type(self.rows) is not tuple
            or tuple(item.path for item in self.rows) != SHARED_RESOURCE_PATHS
            or any(
                type(item) is not LiveMeasurementRowV1
                or item.identity_binding_id != self.identity_binding_id
                or item.measurement_window_id != self.window.window_id
                for item in self.rows
            )
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "snapshot must contain exactly the nine canonical rows"
            )
        self._verify_rows()

    def _verify_rows(self) -> None:
        zero_by_path = {item.path: item for item in self.zero_claims}
        unavailable_by_path = {
            item.path: item for item in self.unavailable_resolutions
        }
        for row in self.rows:
            events = tuple(
                item
                for item in self.events
                if item.path == row.path and item.charged
            )
            if row.path in unavailable_by_path:
                resolution = unavailable_by_path[row.path]
                expected = (
                    resolution.status,
                    None,
                    (),
                    0,
                    None,
                    resolution.resolution_id,
                )
            elif events:
                expected_value = (
                    sum(item.observed_value for item in events)
                    if row.reducer is ReducerEnum.SUM
                    else max(item.observed_value for item in events)
                )
                expected = (
                    receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED,
                    expected_value,
                    tuple(item.event_id for item in events),
                    len(events),
                    None,
                    None,
                )
            elif row.path in zero_by_path:
                expected = (
                    receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED,
                    0,
                    (),
                    0,
                    zero_by_path[row.path].zero_claim_id,
                    None,
                )
            else:
                raise ConstructionSharedResourceLiveMeterV1Error(
                    "snapshot inferred a missing shared-resource value"
                )
            actual = (
                row.status,
                row.value,
                row.charged_event_ids,
                row.observed_event_count,
                row.zero_claim_id,
                row.unavailable_resolution_id,
            )
            if actual != expected:
                raise ConstructionSharedResourceLiveMeterV1Error(
                    "snapshot row differs from a reducer replay"
                )

    @property
    def all_paths_structurally_recorded(self) -> bool:
        return all(
            row.status is receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED
            for row in self.rows
        )

    @property
    def unverified_reported_values(self) -> dict[str, int]:
        if not self.all_paths_structurally_recorded:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "typed unavailable paths prevent a complete numeric source claim"
            )
        return {
            row.path: row.value
            for row in self.rows
            if type(row.value) is int
        }

    @property
    def observed_prefix_values(self) -> dict[str, int]:
        """Replay observed events, including an explicitly incomplete suffix."""

        result: dict[str, int] = {}
        for path in SHARED_RESOURCE_PATHS:
            events = tuple(
                item
                for item in self.events
                if item.path == path and item.charged
            )
            if events:
                reducer = _official_reducer(path)
                result[path] = (
                    sum(item.observed_value for item in events)
                    if reducer is ReducerEnum.SUM
                    else max(item.observed_value for item in events)
                )
        return result

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_live_measurement_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "measurement_registry_id": self.measurement_registry_id,
            "hash_meter_profile_id": self.hash_meter_profile_id,
            "named_obligation_registry_id": self.obligation_registry_id,
            "identity_binding_id": self.identity_binding_id,
            "measurement_window_id": self.window.window_id,
            "live_measurement_event_ids": [item.event_id for item in self.events],
            "complete_window_zero_claim_ids": [
                item.zero_claim_id for item in self.zero_claims
            ],
            "typed_unavailable_resolution_ids": [
                item.resolution_id for item in self.unavailable_resolutions
            ],
            "live_measurement_row_ids": [item.row_id for item in self.rows],
            "shared_resource_paths": list(SHARED_RESOURCE_PATHS),
            "coverage_state": (
                "ALL_SOURCE_CLAIMS_STRUCTURALLY_RECORDED_UNVERIFIED"
                if self.all_paths_structurally_recorded
                else "INCOMPLETE_TYPED"
            ),
            "sum_and_max_reducers_replayed_separately": True,
            "absence_inferred_as_zero": False,
            "proc_self_report_accepted_as_peak_proof": False,
            "accounting_provenance_hash_finalizations_recursion_excluded": True,
            "accounting_suffix_io_and_obligations_blanket_excluded": False,
            "output_prefix_observations_preserved": True,
            "output_suffix_coverage_complete": False,
            "source_evidence_semantics_verified": False,
            "numeric_projection_allowed": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_authorized": False,
            "formal_comparison_vector_authorized": False,
            "central_domain_registered": True,
        }

    @property
    def snapshot_id(self) -> str:
        return _content_id(
            LIVE_MEASUREMENT_SNAPSHOT_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "live_measurement_snapshot_id": self.snapshot_id,
        }


class TrustedSharedResourceLiveMeterV1:
    """Single-thread, one-window trusted primitive-event collector."""

    __slots__ = (
        "_registry",
        "_hash_profile",
        "_obligation_registry",
        "_identity",
        "_window_key",
        "_start_marker_id",
        "_start_sequence",
        "_sequence",
        "_state",
        "_owner_thread",
        "_events",
        "_used_source_evidence_ids",
        "_zero_claims",
        "_unavailable",
        "_cutoff_marker_id",
        "_window",
    )

    def __init__(
        self,
        *,
        measurement_registry: receipts_v1.SharedResourceMeasurementRegistryV1,
        hash_profile: receipts_v1.RecursionSafeHashMeterProfileV1,
        obligation_registry: receipts_v1.NamedObligationRegistryV1,
        identity: receipts_v1.SharedResourceIdentityBindingV1,
        window_key: str,
        start_marker_id: str,
        start_sequence: int,
    ) -> None:
        if (
            type(measurement_registry)
            is not receipts_v1.SharedResourceMeasurementRegistryV1
            or type(hash_profile) is not receipts_v1.RecursionSafeHashMeterProfileV1
            or type(obligation_registry)
            is not receipts_v1.NamedObligationRegistryV1
            or type(identity) is not receipts_v1.SharedResourceIdentityBindingV1
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "live meter authorities have the wrong runtime type"
            )
        if (
            hash_profile.registry is not measurement_registry
            or obligation_registry.registry is not measurement_registry
            or identity.counter_registry_id
            != measurement_registry.counter_registry_id
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "live meter authorities do not share one exact registry/identity"
            )
        if type(window_key) is not str or not window_key:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "window key must be nonempty"
            )
        _cid(start_marker_id, "window start marker")
        if type(start_sequence) is not int or start_sequence < 0:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "window start sequence must be nonnegative"
            )
        official_registry_id, official_stage_profile_id = (
            _official_registry_and_stage_ids()
        )
        if (
            measurement_registry.counter_registry_id != official_registry_id
            or identity.counter_registry_id != official_registry_id
            or identity.stage_profile_id != official_stage_profile_id
            or tuple(measurement_registry.method_by_path) != SHARED_RESOURCE_PATHS
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "live meter is stale against registry/stage V6"
            )
        if any(
            method.value_kind is not receipts_v1.MeasurementValueKindV1.EXACT
            for method in measurement_registry.methods
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "V1 live meter accepts exact event methods, not caller-supplied upper bounds"
            )
        self._registry = measurement_registry
        self._hash_profile = hash_profile
        self._obligation_registry = obligation_registry
        self._identity = identity
        self._window_key = window_key
        self._start_marker_id = start_marker_id
        self._start_sequence = start_sequence
        self._sequence = start_sequence
        self._state = LiveMeterStateV1.OPEN
        self._owner_thread = get_ident()
        self._events: list[LiveMeasurementEventV1] = []
        self._used_source_evidence_ids: set[str] = set()
        self._zero_claims: dict[str, LiveCompleteWindowZeroClaimV1] = {}
        self._unavailable: dict[str, LiveTypedUnavailableResolutionV1] = {}
        self._cutoff_marker_id: str | None = None
        self._window: receipts_v1.SharedResourceMeasurementWindowV1 | None = None

    @property
    def state(self) -> LiveMeterStateV1:
        return self._state

    @property
    def identity(self) -> receipts_v1.SharedResourceIdentityBindingV1:
        return self._identity

    @property
    def unresolved_paths(self) -> tuple[str, ...]:
        self._require_owner()
        if self._state is LiveMeterStateV1.OPEN:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "unresolved paths are only defined after cutoff"
            )
        charged_paths = {item.path for item in self._events if item.charged}
        return tuple(
            path
            for path in SHARED_RESOURCE_PATHS
            if path not in self._unavailable
            and (
                path in _SELF_REFERENTIAL_SUFFIX_PATHS
                or (
                    path not in charged_paths
                    and path not in self._zero_claims
                )
            )
        )

    def _require_owner(self) -> None:
        if get_ident() != self._owner_thread:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "live meter cannot be mutated or frozen from another thread"
            )

    def _require_open(self) -> None:
        self._require_owner()
        if self._state is not LiveMeterStateV1.OPEN:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "operational event arrived after the measurement cutoff"
            )

    def _require_closed(self) -> None:
        self._require_owner()
        if self._state is not LiveMeterStateV1.CLOSED:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "post-cutoff resolution requires one closed, unfrozen window"
            )

    def _claim_source(self, source_evidence_id: str) -> str:
        value = _cid(source_evidence_id, "source evidence")
        if value in self._used_source_evidence_ids:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "source evidence cannot be charged or resolved twice"
            )
        self._used_source_evidence_ids.add(value)
        return value

    def _append_event(
        self,
        *,
        path: str,
        event_kind: LiveMeasurementEventKindV1,
        source_kind: LiveSourceEvidenceKindV1,
        source_evidence_id: str,
        observed_value: int,
        charged: bool,
        purpose_key: str | None = None,
        obligation_key: str | None = None,
        obligation_outcome: ObligationOutcomeV1 | None = None,
    ) -> int:
        self._require_open()
        evidence_id = self._claim_source(source_evidence_id)
        self._sequence += 1
        event = LiveMeasurementEventV1(
            identity_binding_id=self._identity.identity_binding_id,
            window_key=self._window_key,
            sequence=self._sequence,
            path=path,
            event_kind=event_kind,
            source_kind=source_kind,
            source_evidence_id=evidence_id,
            observed_value=observed_value,
            charged=charged,
            purpose_key=purpose_key,
            obligation_key=obligation_key,
            obligation_outcome=obligation_outcome,
        )
        self._events.append(event)
        return event.sequence

    def record_hash_invocation(
        self,
        *,
        purpose_key: str,
        source_evidence_id: str,
    ) -> int:
        """Record one digest finalization through an explicit purpose registry."""

        purposes = {
            item.purpose_key: item for item in self._hash_profile.purposes
        }
        purpose = purposes.get(purpose_key)
        if purpose is None:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "hash invocation used an unregistered purpose"
            )
        charged = (
            purpose.disposition
            is receipts_v1.HashPurposeDispositionV1.BUSINESS_CHARGEABLE
        )
        return self._append_event(
            path="common.hash_invocations",
            event_kind=LiveMeasurementEventKindV1.HASH_FINALIZATION,
            source_kind=LiveSourceEvidenceKindV1.HASH_FACADE_EVENT,
            source_evidence_id=source_evidence_id,
            observed_value=1,
            charged=charged,
            purpose_key=purpose_key,
        )

    def record_named_obligation(
        self,
        *,
        obligation_key: str,
        outcome: ObligationOutcomeV1,
        source_evidence_id: str,
    ) -> int:
        """Count one named PASS/FAIL predicate evaluation before caller raise."""

        obligations = {
            item.obligation_key: item
            for item in self._obligation_registry.obligations
        }
        obligation = obligations.get(obligation_key)
        if obligation is None:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "predicate evaluation used an unregistered obligation"
            )
        resolved_outcome = _enum(
            ObligationOutcomeV1,
            outcome,
            "obligation outcome",
        )
        return self._append_event(
            path=obligation.counter_path,
            event_kind=LiveMeasurementEventKindV1.NAMED_OBLIGATION_EVALUATION,
            source_kind=LiveSourceEvidenceKindV1.NAMED_OBLIGATION_EVENT,
            source_evidence_id=source_evidence_id,
            observed_value=1,
            charged=True,
            obligation_key=obligation_key,
            obligation_outcome=resolved_outcome,
        )

    def record_byte_transfer(
        self,
        *,
        path: str,
        byte_count: int,
        source_evidence_id: str,
    ) -> int:
        """Record one exact positive transfer at the registered I/O owner."""

        if path not in _BYTE_PATHS:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "byte transfer accepts only read/staged/output SUM paths"
            )
        return self._append_event(
            path=path,
            event_kind=LiveMeasurementEventKindV1.BYTE_TRANSFER,
            source_kind=_BYTE_SOURCE_KIND[path],
            source_evidence_id=source_evidence_id,
            observed_value=_positive(byte_count, "byte_count"),
            charged=True,
        )

    def record_successful_process_launch(self, *, source_evidence_id: str) -> int:
        """Record one successful OS/isolated-worker launch, never an attempt total."""

        return self._append_event(
            path="process.launches",
            event_kind=LiveMeasurementEventKindV1.PROCESS_LAUNCH,
            source_kind=LiveSourceEvidenceKindV1.PROCESS_SUPERVISOR_LAUNCH,
            source_evidence_id=source_evidence_id,
            observed_value=1,
            charged=True,
        )

    def record_peak_observation(
        self,
        *,
        path: str,
        observed_bytes: int,
        source_kind: LiveSourceEvidenceKindV1,
        source_evidence_id: str,
    ) -> int:
        """Record a supervisor/cgroup peak observation for one MAX path."""

        if path not in MAX_SHARED_RESOURCE_PATHS:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "peak observation accepts only mounted/working MAX paths"
            )
        resolved_source = _enum(
            LiveSourceEvidenceKindV1,
            source_kind,
            "peak source kind",
        )
        if resolved_source not in _PEAK_SOURCE_KINDS[path]:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "peak source is not the registered supervisor evidence kind"
            )
        return self._append_event(
            path=path,
            event_kind=LiveMeasurementEventKindV1.PEAK_OBSERVATION,
            source_kind=resolved_source,
            source_evidence_id=source_evidence_id,
            observed_value=_positive(observed_bytes, "observed_bytes"),
            charged=True,
        )

    def close_operational_window(self, *, cutoff_marker_id: str) -> None:
        self._require_open()
        marker = _cid(cutoff_marker_id, "window cutoff marker")
        self._cutoff_marker_id = marker
        self._window = receipts_v1.SharedResourceMeasurementWindowV1(
            identity_binding_id=self._identity.identity_binding_id,
            window_key=self._window_key,
            start_marker_id=self._start_marker_id,
            cutoff_marker_id=marker,
            start_sequence=self._start_sequence,
            cutoff_sequence=self._sequence,
            state=receipts_v1.MeasurementWindowStateV1.CLOSED,
        )
        self._state = LiveMeterStateV1.CLOSED

    def attest_complete_window_zero(
        self,
        *,
        path: str,
        source_evidence_id: str,
    ) -> None:
        """Resolve an empty path with an explicit registered monitor claim."""

        self._require_closed()
        _official_reducer(path)
        if path in _SELF_REFERENTIAL_SUFFIX_PATHS:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "self-referential output suffix cannot claim complete-window zero in V1"
            )
        if any(item.path == path and item.charged for item in self._events):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "a path with charged events cannot also claim zero"
            )
        if path in self._zero_claims or path in self._unavailable:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "shared-resource path already has a post-cutoff resolution"
            )
        method = self._registry.method_by_path[path]
        monitor = self._registry.monitor_by_method_id[method.method_id]
        if (
            path not in monitor.zero_attestable_paths
            or monitor.observes_complete_window is not True
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "path lacks registered complete-window zero authority"
            )
        assert self._window is not None
        evidence_id = self._claim_source(source_evidence_id)
        self._zero_claims[path] = LiveCompleteWindowZeroClaimV1(
            identity_binding_id=self._identity.identity_binding_id,
            measurement_window_id=self._window.window_id,
            path=path,
            source_evidence_id=evidence_id,
        )

    def mark_unavailable(
        self,
        *,
        path: str,
        status: receipts_v1.MeasurementStatusV1,
        reason_code: str,
    ) -> None:
        """Explicitly preserve an unmeasured path as UNKNOWN/NOT_AVAILABLE."""

        self._require_closed()
        _official_reducer(path)
        if (
            path not in _SELF_REFERENTIAL_SUFFIX_PATHS
            and any(item.path == path and item.charged for item in self._events)
        ):
            raise ConstructionSharedResourceLiveMeterV1Error(
                "a path with charged events cannot be marked unavailable"
            )
        if path in self._zero_claims or path in self._unavailable:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "shared-resource path already has a post-cutoff resolution"
            )
        assert self._window is not None
        self._unavailable[path] = LiveTypedUnavailableResolutionV1(
            identity_binding_id=self._identity.identity_binding_id,
            measurement_window_id=self._window.window_id,
            path=path,
            status=status,
            reason_code=_reason(reason_code),
        )

    def freeze_snapshot(self) -> SharedResourceMeasurementSnapshotV1:
        """Replay reducers and seal one snapshot; never synthesize missing zeros."""

        self._require_closed()
        unresolved = self.unresolved_paths
        if unresolved:
            raise ConstructionSharedResourceLiveMeterV1Error(
                "cannot freeze unresolved shared-resource paths: "
                + ", ".join(unresolved)
            )
        assert self._window is not None
        rows: list[LiveMeasurementRowV1] = []
        for path in SHARED_RESOURCE_PATHS:
            reducer = _official_reducer(path)
            events = tuple(
                item
                for item in self._events
                if item.path == path and item.charged
            )
            if path in self._unavailable:
                resolution = self._unavailable[path]
                row = LiveMeasurementRowV1(
                    self._identity.identity_binding_id,
                    self._window.window_id,
                    path,
                    reducer,
                    resolution.status,
                    None,
                    (),
                    0,
                    None,
                    resolution.resolution_id,
                )
            elif events:
                value = (
                    sum(item.observed_value for item in events)
                    if reducer is ReducerEnum.SUM
                    else max(item.observed_value for item in events)
                )
                row = LiveMeasurementRowV1(
                    self._identity.identity_binding_id,
                    self._window.window_id,
                    path,
                    reducer,
                    receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED,
                    value,
                    tuple(item.event_id for item in events),
                    len(events),
                    None,
                    None,
                )
            elif path in self._zero_claims:
                claim = self._zero_claims[path]
                row = LiveMeasurementRowV1(
                    self._identity.identity_binding_id,
                    self._window.window_id,
                    path,
                    reducer,
                    receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED,
                    0,
                    (),
                    0,
                    claim.zero_claim_id,
                    None,
                )
            else:
                raise AssertionError("unresolved path passed the freeze guard")
            rows.append(row)

        snapshot = SharedResourceMeasurementSnapshotV1(
            measurement_registry_id=self._registry.measurement_registry_id,
            hash_meter_profile_id=self._hash_profile.hash_meter_profile_id,
            obligation_registry_id=(
                self._obligation_registry.obligation_registry_id
            ),
            identity_binding_id=self._identity.identity_binding_id,
            window=self._window,
            events=tuple(self._events),
            zero_claims=tuple(
                self._zero_claims[path] for path in sorted(self._zero_claims)
            ),
            unavailable_resolutions=tuple(
                self._unavailable[path] for path in sorted(self._unavailable)
            ),
            rows=tuple(rows),
            _issuer=_SNAPSHOT_ISSUER,
        )
        self._state = LiveMeterStateV1.FROZEN
        return snapshot


def open_trusted_shared_resource_live_meter_v1(
    *,
    measurement_registry: receipts_v1.SharedResourceMeasurementRegistryV1,
    hash_profile: receipts_v1.RecursionSafeHashMeterProfileV1,
    obligation_registry: receipts_v1.NamedObligationRegistryV1,
    identity: receipts_v1.SharedResourceIdentityBindingV1,
    window_key: str,
    start_marker_id: str,
    start_sequence: int = 0,
) -> TrustedSharedResourceLiveMeterV1:
    """Open one identity-bound live window after all authorities are frozen."""

    return TrustedSharedResourceLiveMeterV1(
        measurement_registry=measurement_registry,
        hash_profile=hash_profile,
        obligation_registry=obligation_registry,
        identity=identity,
        window_key=window_key,
        start_marker_id=start_marker_id,
        start_sequence=start_sequence,
    )


def replay_live_measurement_snapshot_structure_v1(
    snapshot: SharedResourceMeasurementSnapshotV1,
) -> SharedResourceMeasurementSnapshotV1:
    """Re-run structural/reducer checks without verifying source semantics."""

    if type(snapshot) is not SharedResourceMeasurementSnapshotV1:
        raise ConstructionSharedResourceLiveMeterV1Error(
            "live measurement snapshot has the wrong runtime type"
        )
    replayed = SharedResourceMeasurementSnapshotV1(
        snapshot.measurement_registry_id,
        snapshot.hash_meter_profile_id,
        snapshot.obligation_registry_id,
        snapshot.identity_binding_id,
        snapshot.window,
        snapshot.events,
        snapshot.zero_claims,
        snapshot.unavailable_resolutions,
        snapshot.rows,
        _SNAPSHOT_ISSUER,
    )
    if replayed.snapshot_id != snapshot.snapshot_id:
        raise ConstructionSharedResourceLiveMeterV1Error(
            "live measurement snapshot content changed during replay"
        )
    return replayed


__all__ = [
    "ConstructionSharedResourceLiveMeterV1Error",
    "LIVE_COMPLETE_WINDOW_ZERO_CLAIM_V1_DOMAIN",
    "LIVE_MEASUREMENT_EVENT_V1_DOMAIN",
    "LIVE_MEASUREMENT_ROW_V1_DOMAIN",
    "LIVE_MEASUREMENT_SNAPSHOT_V1_DOMAIN",
    "LIVE_TYPED_UNAVAILABLE_RESOLUTION_V1_DOMAIN",
    "LiveCompleteWindowZeroClaimV1",
    "LiveMeasurementEventKindV1",
    "LiveMeasurementEventV1",
    "LiveMeasurementRowV1",
    "LiveMeterStateV1",
    "LiveSourceEvidenceKindV1",
    "LiveTypedUnavailableResolutionV1",
    "MAX_SHARED_RESOURCE_PATHS",
    "ObligationOutcomeV1",
    "PROFILE_KEY",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "SHARED_RESOURCE_PATHS",
    "SUM_SHARED_RESOURCE_PATHS",
    "SharedResourceMeasurementSnapshotV1",
    "TrustedSharedResourceLiveMeterV1",
    "open_trusted_shared_resource_live_meter_v1",
    "replay_live_measurement_snapshot_structure_v1",
]
