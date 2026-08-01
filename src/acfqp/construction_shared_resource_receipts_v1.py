"""Typed, fail-closed receipts for construction shared resources.

This module closes a schema gap only.  It does not install a process, I/O,
memory, hash, or predicate hook and it does not claim that the current K7
construction path has complete live accounting.  In particular:

* ``UNKNOWN`` and ``NOT_AVAILABLE`` carry typed unavailable values and can
  never be interpreted as zero;
* a structurally recorded zero claim requires a closed measurement window and
  a registered monitor which explicitly supports complete-window zero claims;
* SUM and MAX semantics are inherited exactly from counter registry V6;
* business hashes are separated from hashes used to construct accounting
  evidence, avoiding recursive self-accounting; and
* integrity/protocol work is named at the predicate owner, rather than being
  inferred from a returned summary or from the number of Python ``if`` nodes.

Every schema uses the central domain-tag registry.  Accounting/provenance
hashes are generated after the operational cutoff and are not fed back into
the business-hash meter.  V1 performs no semantic replay of referenced source
bytes, so even a structurally complete set never authorizes numeric projection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import (
    CONSTRUCTION_HASH_PURPOSE_REGISTRATION_V1_DOMAIN,
    CONSTRUCTION_NAMED_OBLIGATION_REGISTRY_V1_DOMAIN,
    CONSTRUCTION_NAMED_OBLIGATION_V1_DOMAIN,
    CONSTRUCTION_RECURSION_SAFE_HASH_METER_PROFILE_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_IDENTITY_BINDING_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_METHOD_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_REGISTRY_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_WINDOW_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_MONITOR_REGISTRATION_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_RECEIPT_SET_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_RECEIPT_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_CHARGE_KEY_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_SOURCE_EVIDENCE_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_shared_resource_receipts_v1"

SHARED_RESOURCE_IDENTITY_BINDING_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_IDENTITY_BINDING_V1_DOMAIN
)
SHARED_RESOURCE_MEASUREMENT_WINDOW_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_WINDOW_V1_DOMAIN
)
SHARED_RESOURCE_MEASUREMENT_METHOD_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_METHOD_V1_DOMAIN
)
SHARED_RESOURCE_MONITOR_REGISTRATION_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_MONITOR_REGISTRATION_V1_DOMAIN
)
SHARED_RESOURCE_MEASUREMENT_REGISTRY_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_REGISTRY_V1_DOMAIN
)
SHARED_RESOURCE_SOURCE_EVIDENCE_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_SOURCE_EVIDENCE_V1_DOMAIN
)
SHARED_RESOURCE_CHARGE_KEY_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_CHARGE_KEY_V1_DOMAIN
)
SHARED_RESOURCE_RECEIPT_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_RECEIPT_V1_DOMAIN
)
SHARED_RESOURCE_RECEIPT_SET_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_RECEIPT_SET_V1_DOMAIN
)
HASH_PURPOSE_REGISTRATION_V1_DOMAIN = (
    CONSTRUCTION_HASH_PURPOSE_REGISTRATION_V1_DOMAIN
)
RECURSION_SAFE_HASH_METER_PROFILE_V1_DOMAIN = (
    CONSTRUCTION_RECURSION_SAFE_HASH_METER_PROFILE_V1_DOMAIN
)
NAMED_OBLIGATION_V1_DOMAIN = CONSTRUCTION_NAMED_OBLIGATION_V1_DOMAIN
NAMED_OBLIGATION_REGISTRY_V1_DOMAIN = (
    CONSTRUCTION_NAMED_OBLIGATION_REGISTRY_V1_DOMAIN
)

LOCAL_DOMAIN_TAGS = frozenset(
    {
        SHARED_RESOURCE_IDENTITY_BINDING_V1_DOMAIN,
        SHARED_RESOURCE_MEASUREMENT_WINDOW_V1_DOMAIN,
        SHARED_RESOURCE_MEASUREMENT_METHOD_V1_DOMAIN,
        SHARED_RESOURCE_MONITOR_REGISTRATION_V1_DOMAIN,
        SHARED_RESOURCE_MEASUREMENT_REGISTRY_V1_DOMAIN,
        SHARED_RESOURCE_SOURCE_EVIDENCE_V1_DOMAIN,
        SHARED_RESOURCE_CHARGE_KEY_V1_DOMAIN,
        SHARED_RESOURCE_RECEIPT_V1_DOMAIN,
        SHARED_RESOURCE_RECEIPT_SET_V1_DOMAIN,
        HASH_PURPOSE_REGISTRATION_V1_DOMAIN,
        RECURSION_SAFE_HASH_METER_PROFILE_V1_DOMAIN,
        NAMED_OBLIGATION_V1_DOMAIN,
        NAMED_OBLIGATION_REGISTRY_V1_DOMAIN,
    }
)

SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)
SUM_SHARED_RESOURCE_PATHS = frozenset(
    {
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.output_bytes",
        "io.read_bytes",
        "io.staged_bytes",
        "process.launches",
    }
)
MAX_SHARED_RESOURCE_PATHS = frozenset(
    {"io.mounted_bytes_peak", "memory.working_bytes_peak"}
)
REQUIRED_ACCOUNTING_HASH_EXCLUSION_PURPOSES = frozenset(
    {
        "accounting_event_content_id",
        "accounting_transcript_content_id",
        "shared_resource_evidence_content_id",
    }
)

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]*$")
_MODULE = re.compile(r"^acfqp(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


class ConstructionSharedResourceReceiptsV1Error(ValueError):
    """One shared-resource schema object is malformed or semantically stale."""


class MeasurementStatusV1(str, Enum):
    # A receipt can establish that a source *claims* a measurement, but V1 has
    # no semantic authority that can validate the source bytes.  Keep that
    # limitation in the status rather than relying on callers to read prose.
    RECORDED_UNVERIFIED = "RECORDED_UNVERIFIED"
    UNKNOWN = "UNKNOWN"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class MeasurementWindowStateV1(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class MeasurementValueKindV1(str, Enum):
    EXACT = "EXACT"
    VERIFIED_UPPER_BOUND = "VERIFIED_UPPER_BOUND"


class MeasurementMethodKindV1(str, Enum):
    RECURSION_SAFE_HASH_METER = "RECURSION_SAFE_HASH_METER"
    NAMED_OBLIGATION_METER = "NAMED_OBLIGATION_METER"
    EXACT_BYTE_TRANSFER_MONITOR = "EXACT_BYTE_TRANSFER_MONITOR"
    PROCESS_SUPERVISOR = "PROCESS_SUPERVISOR"
    MOUNT_MANIFEST_PEAK_MONITOR = "MOUNT_MANIFEST_PEAK_MONITOR"
    WORKING_SET_PEAK_MONITOR = "WORKING_SET_PEAK_MONITOR"
    FROZEN_VERIFIED_UPPER_BOUND = "FROZEN_VERIFIED_UPPER_BOUND"


class SourceEvidenceKindV1(str, Enum):
    EVENT_TRANSCRIPT = "EVENT_TRANSCRIPT"
    BYTE_TRANSFER_LOG = "BYTE_TRANSFER_LOG"
    PROCESS_SUPERVISOR_LOG = "PROCESS_SUPERVISOR_LOG"
    MOUNT_MANIFEST = "MOUNT_MANIFEST"
    WORKING_SET_PEAK = "WORKING_SET_PEAK"
    VERIFIED_UPPER_BOUND = "VERIFIED_UPPER_BOUND"
    COMPLETE_WINDOW_ZERO_ATTESTATION = (
        "COMPLETE_WINDOW_ZERO_ATTESTATION"
    )


class MonitorIsolationKindV1(str, Enum):
    TRUSTED_IN_PROCESS = "TRUSTED_IN_PROCESS"
    OUT_OF_PROCESS_SUPERVISOR = "OUT_OF_PROCESS_SUPERVISOR"
    FROZEN_AUTHORITY = "FROZEN_AUTHORITY"


class HashPurposeDispositionV1(str, Enum):
    BUSINESS_CHARGEABLE = "BUSINESS_CHARGEABLE"
    ACCOUNTING_PROVENANCE_EXCLUDED = "ACCOUNTING_PROVENANCE_EXCLUDED"
    IMPORT_TIME_EXCLUDED = "IMPORT_TIME_EXCLUDED"


class NamedObligationKindV1(str, Enum):
    INTEGRITY = "INTEGRITY"
    PROTOCOL = "PROTOCOL"


def _domain_id(domain: str, payload: Mapping[str, Any]) -> str:
    """Create post-cutoff schema evidence through the central ID authority."""

    if domain not in LOCAL_DOMAIN_TAGS:
        raise ConstructionSharedResourceReceiptsV1Error(
            "shared-resource content ID used an unregistered role domain"
        )
    return content_id(domain, dict(payload))


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionSharedResourceReceiptsV1Error(
            f"{field_name} must be one full content ID"
        ) from error


def _identifier(value: Any, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ConstructionSharedResourceReceiptsV1Error(
            f"{field_name} must be a canonical identifier"
        )
    return value


def _module_symbol(module: Any, symbol: Any) -> tuple[str, str]:
    if (
        type(module) is not str
        or _MODULE.fullmatch(module) is None
        or type(symbol) is not str
        or _SYMBOL.fullmatch(symbol) is None
    ):
        raise ConstructionSharedResourceReceiptsV1Error(
            "monitor/obligation source module or symbol is noncanonical"
        )
    return module, symbol


def _nonnegative(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ConstructionSharedResourceReceiptsV1Error(
            f"{field_name} must be a nonnegative exact integer"
        )
    return value


def _enum(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceReceiptsV1Error(
            f"unknown {field_name} {value!r}"
        ) from error


def _bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise ConstructionSharedResourceReceiptsV1Error(
            f"{field_name} must be an exact bool"
        )
    return value


def _sorted_unique(values: Any, field_name: str) -> tuple[Any, ...]:
    if type(values) is not tuple or tuple(sorted(values)) != values or len(
        set(values)
    ) != len(values):
        raise ConstructionSharedResourceReceiptsV1Error(
            f"{field_name} must be one sorted unique tuple"
        )
    return values


def _official_path_leaf(path: str) -> Any:
    if path not in SHARED_RESOURCE_PATHS:
        raise ConstructionSharedResourceReceiptsV1Error(
            f"unknown shared-resource path {path!r}"
        )
    registry = registry_v6.official_counter_registry_v6()
    leaf = registry.by_path.get(path)
    if leaf is None or not leaf.required or leaf.lane.value != "operational":
        raise ConstructionSharedResourceReceiptsV1Error(
            "shared-resource path differs from required V6 operational leaf"
        )
    expected_reducer = (
        ReducerEnum.SUM
        if path in SUM_SHARED_RESOURCE_PATHS
        else ReducerEnum.MAX
    )
    if leaf.reducer is not expected_reducer:
        raise ConstructionSharedResourceReceiptsV1Error(
            "shared-resource reducer differs from V6"
        )
    return leaf


_ALLOWED_METHOD_KINDS = MappingProxyType(
    {
        "common.hash_invocations": frozenset(
            {MeasurementMethodKindV1.RECURSION_SAFE_HASH_METER}
        ),
        "common.integrity_checks": frozenset(
            {MeasurementMethodKindV1.NAMED_OBLIGATION_METER}
        ),
        "common.protocol_checks": frozenset(
            {MeasurementMethodKindV1.NAMED_OBLIGATION_METER}
        ),
        "io.read_bytes": frozenset(
            {MeasurementMethodKindV1.EXACT_BYTE_TRANSFER_MONITOR}
        ),
        "io.staged_bytes": frozenset(
            {MeasurementMethodKindV1.EXACT_BYTE_TRANSFER_MONITOR}
        ),
        "io.output_bytes": frozenset(
            {MeasurementMethodKindV1.EXACT_BYTE_TRANSFER_MONITOR}
        ),
        "process.launches": frozenset(
            {MeasurementMethodKindV1.PROCESS_SUPERVISOR}
        ),
        "io.mounted_bytes_peak": frozenset(
            {MeasurementMethodKindV1.MOUNT_MANIFEST_PEAK_MONITOR}
        ),
        "memory.working_bytes_peak": frozenset(
            {
                MeasurementMethodKindV1.WORKING_SET_PEAK_MONITOR,
                MeasurementMethodKindV1.FROZEN_VERIFIED_UPPER_BOUND,
            }
        ),
    }
)

_ALLOWED_EVIDENCE_KINDS = MappingProxyType(
    {
        MeasurementMethodKindV1.RECURSION_SAFE_HASH_METER: frozenset(
            {SourceEvidenceKindV1.EVENT_TRANSCRIPT}
        ),
        MeasurementMethodKindV1.NAMED_OBLIGATION_METER: frozenset(
            {SourceEvidenceKindV1.EVENT_TRANSCRIPT}
        ),
        MeasurementMethodKindV1.EXACT_BYTE_TRANSFER_MONITOR: frozenset(
            {SourceEvidenceKindV1.BYTE_TRANSFER_LOG}
        ),
        MeasurementMethodKindV1.PROCESS_SUPERVISOR: frozenset(
            {SourceEvidenceKindV1.PROCESS_SUPERVISOR_LOG}
        ),
        MeasurementMethodKindV1.MOUNT_MANIFEST_PEAK_MONITOR: frozenset(
            {SourceEvidenceKindV1.MOUNT_MANIFEST}
        ),
        MeasurementMethodKindV1.WORKING_SET_PEAK_MONITOR: frozenset(
            {SourceEvidenceKindV1.WORKING_SET_PEAK}
        ),
        MeasurementMethodKindV1.FROZEN_VERIFIED_UPPER_BOUND: frozenset(
            {SourceEvidenceKindV1.VERIFIED_UPPER_BOUND}
        ),
    }
)


@dataclass(frozen=True, slots=True)
class TypedUnavailableMeasurementV1:
    """Typed missing evidence/value; it is deliberately not numeric."""

    status: MeasurementStatusV1
    reason_code: str

    def __post_init__(self) -> None:
        status = _enum(MeasurementStatusV1, self.status, "measurement status")
        object.__setattr__(self, "status", status)
        if status is MeasurementStatusV1.RECORDED_UNVERIFIED:
            raise ConstructionSharedResourceReceiptsV1Error(
                "a recorded source claim cannot use typed unavailability"
            )
        if type(self.reason_code) is not str or _REASON.fullmatch(
            self.reason_code
        ) is None:
            raise ConstructionSharedResourceReceiptsV1Error(
                "unavailability reason must be a canonical public code"
            )

    def to_document(self) -> dict[str, str]:
        return {"kind": self.status.value, "reason": self.reason_code}


@dataclass(frozen=True, slots=True)
class SharedResourceIdentityBindingV1:
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    execution_profile_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str

    def __post_init__(self) -> None:
        for name in (
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
            "execution_profile_id",
            "occurrence_id",
            "route_attempt_id",
            "decision_point_id",
        ):
            _cid(getattr(self, name), name)
        registry = registry_v6.official_counter_registry_v6()
        stage_profile = registry_v6.official_stage_profile_v6(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage_profile.stage_profile_id
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "identity binding is not attached to the V6 registry/stage profile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_identity_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "execution_profile_id": self.execution_profile_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
        }

    @property
    def identity_binding_id(self) -> str:
        return _domain_id(
            SHARED_RESOURCE_IDENTITY_BINDING_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "identity_binding_id": self.identity_binding_id}


@dataclass(frozen=True, slots=True)
class SharedResourceMeasurementWindowV1:
    identity_binding_id: str
    window_key: str
    start_marker_id: str
    cutoff_marker_id: str
    start_sequence: int
    cutoff_sequence: int
    state: MeasurementWindowStateV1
    cutoff_is_inclusive: bool = True

    def __post_init__(self) -> None:
        for value, name in (
            (self.identity_binding_id, "window identity binding"),
            (self.start_marker_id, "window start marker"),
            (self.cutoff_marker_id, "window cutoff marker"),
        ):
            _cid(value, name)
        _identifier(self.window_key, "window_key")
        _nonnegative(self.start_sequence, "start_sequence")
        _nonnegative(self.cutoff_sequence, "cutoff_sequence")
        if self.cutoff_sequence < self.start_sequence:
            raise ConstructionSharedResourceReceiptsV1Error(
                "measurement cutoff precedes its start"
            )
        state = _enum(MeasurementWindowStateV1, self.state, "window state")
        object.__setattr__(self, "state", state)
        _bool(self.cutoff_is_inclusive, "cutoff_is_inclusive")
        if self.cutoff_is_inclusive is not True:
            raise ConstructionSharedResourceReceiptsV1Error(
                "V1 measurement windows require one inclusive cutoff"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_measurement_window.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "identity_binding_id": self.identity_binding_id,
            "window_key": self.window_key,
            "start_marker_id": self.start_marker_id,
            "cutoff_marker_id": self.cutoff_marker_id,
            "start_sequence": self.start_sequence,
            "cutoff_sequence": self.cutoff_sequence,
            "state": self.state.value,
            "cutoff_is_inclusive": self.cutoff_is_inclusive,
        }

    @property
    def window_id(self) -> str:
        return _domain_id(
            SHARED_RESOURCE_MEASUREMENT_WINDOW_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "measurement_window_id": self.window_id}


@dataclass(frozen=True, slots=True)
class SharedResourceMeasurementMethodV1:
    counter_registry_id: str
    path: str
    method_kind: MeasurementMethodKindV1
    value_kind: MeasurementValueKindV1
    owner: str
    semantics_id: str
    unit: str
    reducer: ReducerEnum
    primitive: str
    complete_window_required: bool = True

    def __post_init__(self) -> None:
        leaf = _official_path_leaf(self.path)
        _cid(self.counter_registry_id, "method counter registry")
        if self.counter_registry_id != registry_v6.official_counter_registry_v6().registry_id:
            raise ConstructionSharedResourceReceiptsV1Error(
                "measurement method is not bound to V6"
            )
        kind = _enum(MeasurementMethodKindV1, self.method_kind, "method kind")
        value_kind = _enum(MeasurementValueKindV1, self.value_kind, "value kind")
        reducer = _enum(ReducerEnum, self.reducer, "reducer")
        object.__setattr__(self, "method_kind", kind)
        object.__setattr__(self, "value_kind", value_kind)
        object.__setattr__(self, "reducer", reducer)
        if kind not in _ALLOWED_METHOD_KINDS[self.path]:
            raise ConstructionSharedResourceReceiptsV1Error(
                "measurement method kind is invalid for its path"
            )
        if (
            self.owner != leaf.owner
            or self.semantics_id != leaf.semantics_id
            or self.unit != leaf.unit
            or reducer is not leaf.reducer
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "measurement method metadata differs from V6"
            )
        _identifier(self.primitive, "measurement primitive")
        _bool(self.complete_window_required, "complete_window_required")
        if self.complete_window_required is not True:
            raise ConstructionSharedResourceReceiptsV1Error(
                "V1 methods require complete-window evidence"
            )
        if (
            kind is MeasurementMethodKindV1.FROZEN_VERIFIED_UPPER_BOUND
        ) != (value_kind is MeasurementValueKindV1.VERIFIED_UPPER_BOUND):
            raise ConstructionSharedResourceReceiptsV1Error(
                "only the frozen-cap method may report an upper bound"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_measurement_method.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "path": self.path,
            "method_kind": self.method_kind.value,
            "value_kind": self.value_kind.value,
            "owner": self.owner,
            "semantics_id": self.semantics_id,
            "unit": self.unit,
            "reducer": self.reducer.value,
            "primitive": self.primitive,
            "complete_window_required": self.complete_window_required,
        }

    @property
    def method_id(self) -> str:
        return _domain_id(
            SHARED_RESOURCE_MEASUREMENT_METHOD_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "measurement_method_id": self.method_id}


@dataclass(frozen=True, slots=True)
class SharedResourceMonitorRegistrationV1:
    registration_authority_id: str
    monitor_key: str
    monitor_code_id: str
    source_module: str
    source_symbol: str
    isolation_kind: MonitorIsolationKindV1
    measurement_method_ids: tuple[str, ...]
    zero_attestable_paths: tuple[str, ...]
    observes_complete_window: bool

    def __post_init__(self) -> None:
        _cid(self.registration_authority_id, "monitor registration authority")
        _cid(self.monitor_code_id, "monitor code")
        _identifier(self.monitor_key, "monitor_key")
        _module_symbol(self.source_module, self.source_symbol)
        isolation = _enum(MonitorIsolationKindV1, self.isolation_kind, "monitor isolation")
        object.__setattr__(self, "isolation_kind", isolation)
        _sorted_unique(self.measurement_method_ids, "measurement_method_ids")
        for value in self.measurement_method_ids:
            _cid(value, "registered measurement method")
        _sorted_unique(self.zero_attestable_paths, "zero_attestable_paths")
        if any(path not in SHARED_RESOURCE_PATHS for path in self.zero_attestable_paths):
            raise ConstructionSharedResourceReceiptsV1Error(
                "monitor claims zero authority for an unknown path"
            )
        _bool(self.observes_complete_window, "observes_complete_window")
        if self.zero_attestable_paths and self.observes_complete_window is not True:
            raise ConstructionSharedResourceReceiptsV1Error(
                "zero authority requires complete-window observation"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_monitor_registration.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "registration_authority_id": self.registration_authority_id,
            "monitor_key": self.monitor_key,
            "monitor_code_id": self.monitor_code_id,
            "source_module": self.source_module,
            "source_symbol": self.source_symbol,
            "isolation_kind": self.isolation_kind.value,
            "measurement_method_ids": list(self.measurement_method_ids),
            "zero_attestable_paths": list(self.zero_attestable_paths),
            "observes_complete_window": self.observes_complete_window,
            "registration_only": True,
            "current_live_measurement_claimed": False,
        }

    @property
    def monitor_registration_id(self) -> str:
        return _domain_id(
            SHARED_RESOURCE_MONITOR_REGISTRATION_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "monitor_registration_id": self.monitor_registration_id,
        }


@dataclass(frozen=True, slots=True)
class SharedResourceMeasurementRegistryV1:
    counter_registry_id: str
    registration_authority_id: str
    methods: tuple[SharedResourceMeasurementMethodV1, ...] = field(repr=False)
    monitors: tuple[SharedResourceMonitorRegistrationV1, ...] = field(repr=False)

    def __post_init__(self) -> None:
        _cid(self.counter_registry_id, "measurement registry counter registry")
        _cid(self.registration_authority_id, "measurement registration authority")
        if self.counter_registry_id != registry_v6.official_counter_registry_v6().registry_id:
            raise ConstructionSharedResourceReceiptsV1Error(
                "measurement registry is not bound to V6"
            )
        if (
            type(self.methods) is not tuple
            or any(type(item) is not SharedResourceMeasurementMethodV1 for item in self.methods)
            or tuple(sorted(self.methods, key=lambda item: item.path)) != self.methods
            or tuple(item.path for item in self.methods) != SHARED_RESOURCE_PATHS
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "measurement registry requires exactly one sorted method per shared path"
            )
        if (
            type(self.monitors) is not tuple
            or not self.monitors
            or any(type(item) is not SharedResourceMonitorRegistrationV1 for item in self.monitors)
            or tuple(sorted(self.monitors, key=lambda item: item.monitor_registration_id))
            != self.monitors
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "measurement monitors must be nonempty and content-ID sorted"
            )
        method_ids = {item.method_id for item in self.methods}
        claimed: list[str] = []
        method_by_id = {item.method_id: item for item in self.methods}
        for monitor in self.monitors:
            if monitor.registration_authority_id != self.registration_authority_id:
                raise ConstructionSharedResourceReceiptsV1Error(
                    "monitor is registered by another authority"
                )
            claimed.extend(monitor.measurement_method_ids)
            supported_paths = {
                method_by_id[item].path
                for item in monitor.measurement_method_ids
                if item in method_by_id
            }
            if (
                not set(monitor.measurement_method_ids) <= method_ids
                or not set(monitor.zero_attestable_paths) <= supported_paths
            ):
                raise ConstructionSharedResourceReceiptsV1Error(
                    "monitor references a foreign method or zero path"
                )
        if len(claimed) != len(set(claimed)) or set(claimed) != method_ids:
            raise ConstructionSharedResourceReceiptsV1Error(
                "each shared-resource method must have exactly one registered monitor"
            )

    @property
    def method_by_path(self) -> dict[str, SharedResourceMeasurementMethodV1]:
        return {item.path: item for item in self.methods}

    @property
    def monitor_by_method_id(self) -> dict[str, SharedResourceMonitorRegistrationV1]:
        return {
            method_id: monitor
            for monitor in self.monitors
            for method_id in monitor.measurement_method_ids
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_measurement_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "registration_authority_id": self.registration_authority_id,
            "measurement_method_ids": [item.method_id for item in self.methods],
            "monitor_registration_ids": [
                item.monitor_registration_id for item in self.monitors
            ],
            "shared_resource_paths": list(SHARED_RESOURCE_PATHS),
            "schema_only": True,
            "current_live_accounting_closed": False,
        }

    @property
    def measurement_registry_id(self) -> str:
        return _domain_id(
            SHARED_RESOURCE_MEASUREMENT_REGISTRY_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "measurement_registry_id": self.measurement_registry_id,
        }


@dataclass(frozen=True, slots=True)
class SharedResourceSourceEvidenceV1:
    measurement_registry_id: str
    method_id: str
    monitor_registration_id: str
    identity_binding_id: str
    window_id: str
    evidence_kind: SourceEvidenceKindV1
    source_schema_id: str
    source_artifact_id: str
    evidence_bytes_sha256: str
    charge_key: str
    covered_start_sequence: int
    covered_cutoff_sequence: int
    reported_value: int
    observed_event_count: int
    complete_through_cutoff: bool
    immutable_at_cutoff: bool

    def _charge_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_charge_key.v1",
            "schema_version": SCHEMA_VERSION,
            "measurement_registry_id": self.measurement_registry_id,
            "method_id": self.method_id,
            "monitor_registration_id": self.monitor_registration_id,
            "identity_binding_id": self.identity_binding_id,
            "window_id": self.window_id,
            "source_schema_id": self.source_schema_id,
            "source_artifact_id": self.source_artifact_id,
            "covered_start_sequence": self.covered_start_sequence,
            "covered_cutoff_sequence": self.covered_cutoff_sequence,
        }

    @property
    def expected_charge_key(self) -> str:
        return _domain_id(
            SHARED_RESOURCE_CHARGE_KEY_V1_DOMAIN,
            self._charge_payload(),
        )

    def __post_init__(self) -> None:
        for value, name in (
            (self.measurement_registry_id, "source measurement registry"),
            (self.method_id, "source method"),
            (self.monitor_registration_id, "source monitor"),
            (self.identity_binding_id, "source identity"),
            (self.window_id, "source window"),
            (self.source_artifact_id, "source artifact"),
            (self.evidence_bytes_sha256, "source evidence digest"),
            (self.charge_key, "source charge key"),
        ):
            _cid(value, name)
        _identifier(self.source_schema_id, "source_schema_id")
        kind = _enum(SourceEvidenceKindV1, self.evidence_kind, "source evidence kind")
        object.__setattr__(self, "evidence_kind", kind)
        _nonnegative(self.covered_start_sequence, "covered_start_sequence")
        _nonnegative(self.covered_cutoff_sequence, "covered_cutoff_sequence")
        _nonnegative(self.reported_value, "reported_value")
        _nonnegative(self.observed_event_count, "observed_event_count")
        _bool(self.complete_through_cutoff, "complete_through_cutoff")
        _bool(self.immutable_at_cutoff, "immutable_at_cutoff")
        if self.covered_cutoff_sequence < self.covered_start_sequence:
            raise ConstructionSharedResourceReceiptsV1Error(
                "source evidence cutoff precedes its start"
            )
        if self.charge_key != self.expected_charge_key:
            raise ConstructionSharedResourceReceiptsV1Error(
                "source evidence charge key is not content-bound"
            )
        if kind is SourceEvidenceKindV1.COMPLETE_WINDOW_ZERO_ATTESTATION:
            if (
                self.reported_value != 0
                or self.observed_event_count != 0
                or self.complete_through_cutoff is not True
                or self.immutable_at_cutoff is not True
            ):
                raise ConstructionSharedResourceReceiptsV1Error(
                    "zero evidence must attest an empty complete immutable window"
                )
        elif self.reported_value == 0:
            raise ConstructionSharedResourceReceiptsV1Error(
                "zero source evidence requires the explicit zero kind"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_source_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "measurement_registry_id": self.measurement_registry_id,
            "method_id": self.method_id,
            "monitor_registration_id": self.monitor_registration_id,
            "identity_binding_id": self.identity_binding_id,
            "window_id": self.window_id,
            "evidence_kind": self.evidence_kind.value,
            "source_schema_id": self.source_schema_id,
            "source_artifact_id": self.source_artifact_id,
            "evidence_bytes_sha256": self.evidence_bytes_sha256,
            "charge_key": self.charge_key,
            "covered_start_sequence": self.covered_start_sequence,
            "covered_cutoff_sequence": self.covered_cutoff_sequence,
            "reported_value": self.reported_value,
            "observed_event_count": self.observed_event_count,
            "complete_through_cutoff": self.complete_through_cutoff,
            "immutable_at_cutoff": self.immutable_at_cutoff,
            "source_claim_only": True,
            "source_evidence_semantics_verified": False,
            "numeric_value_authorized": False,
        }

    @property
    def source_evidence_id(self) -> str:
        return _domain_id(
            SHARED_RESOURCE_SOURCE_EVIDENCE_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "source_evidence_id": self.source_evidence_id}


MeasurementValueV1 = int | TypedUnavailableMeasurementV1
SourceEvidenceRefV1 = (
    SharedResourceSourceEvidenceV1 | TypedUnavailableMeasurementV1
)


@dataclass(frozen=True, slots=True)
class SharedResourceReceiptV1:
    registry: SharedResourceMeasurementRegistryV1 = field(repr=False)
    identity: SharedResourceIdentityBindingV1 = field(repr=False)
    window: SharedResourceMeasurementWindowV1 = field(repr=False)
    path: str
    status: MeasurementStatusV1
    source_claim_present: bool
    value: MeasurementValueV1
    method_id: str
    monitor_registration_id: str
    source_evidence: SourceEvidenceRefV1 = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.registry) is not SharedResourceMeasurementRegistryV1
            or type(self.identity) is not SharedResourceIdentityBindingV1
            or type(self.window) is not SharedResourceMeasurementWindowV1
            or self.identity.counter_registry_id != self.registry.counter_registry_id
            or self.window.identity_binding_id != self.identity.identity_binding_id
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "receipt registry/identity/window binding changed"
            )
        status = _enum(MeasurementStatusV1, self.status, "receipt status")
        object.__setattr__(self, "status", status)
        _bool(self.source_claim_present, "source_claim_present")
        method = self.registry.method_by_path.get(self.path)
        monitor = self.registry.monitor_by_method_id.get(self.method_id)
        if (
            method is None
            or method.method_id != self.method_id
            or monitor is None
            or monitor.monitor_registration_id != self.monitor_registration_id
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "receipt method or monitor is absent from its registry"
            )
        if status is MeasurementStatusV1.RECORDED_UNVERIFIED:
            if (
                self.source_claim_present is not True
                or type(self.value) is not int
                or self.value < 0
                or type(self.source_evidence) is not SharedResourceSourceEvidenceV1
                or self.window.state is not MeasurementWindowStateV1.CLOSED
            ):
                raise ConstructionSharedResourceReceiptsV1Error(
                    "RECORDED_UNVERIFIED requires a nonnegative source claim and closed-window structure"
                )
            evidence = self.source_evidence
            if (
                evidence.measurement_registry_id != self.registry.measurement_registry_id
                or evidence.method_id != method.method_id
                or evidence.monitor_registration_id != monitor.monitor_registration_id
                or evidence.identity_binding_id != self.identity.identity_binding_id
                or evidence.window_id != self.window.window_id
                or evidence.covered_start_sequence != self.window.start_sequence
                or evidence.covered_cutoff_sequence != self.window.cutoff_sequence
                or evidence.reported_value != self.value
                or evidence.complete_through_cutoff is not True
                or evidence.immutable_at_cutoff is not True
            ):
                raise ConstructionSharedResourceReceiptsV1Error(
                    "recorded source claim is stale or structurally incomplete"
                )
            if method.value_kind is MeasurementValueKindV1.VERIFIED_UPPER_BOUND:
                if evidence.evidence_kind is not SourceEvidenceKindV1.VERIFIED_UPPER_BOUND:
                    raise ConstructionSharedResourceReceiptsV1Error(
                        "upper-bound method requires upper-bound evidence"
                    )
            elif evidence.evidence_kind is SourceEvidenceKindV1.VERIFIED_UPPER_BOUND:
                raise ConstructionSharedResourceReceiptsV1Error(
                    "exact method cannot consume upper-bound evidence"
                )
            allowed_evidence = _ALLOWED_EVIDENCE_KINDS[method.method_kind]
            if self.value != 0 and evidence.evidence_kind not in allowed_evidence:
                raise ConstructionSharedResourceReceiptsV1Error(
                    "source evidence kind is invalid for the measurement method"
                )
            if self.value == 0 and (
                self.path not in monitor.zero_attestable_paths
                or monitor.observes_complete_window is not True
                or evidence.evidence_kind
                is not SourceEvidenceKindV1.COMPLETE_WINDOW_ZERO_ATTESTATION
            ):
                raise ConstructionSharedResourceReceiptsV1Error(
                    "zero receipt lacks a registered complete-window monitor"
                )
        else:
            if (
                self.source_claim_present is not False
                or type(self.value) is not TypedUnavailableMeasurementV1
                or type(self.source_evidence) is not TypedUnavailableMeasurementV1
                or self.value.status is not status
                or self.source_evidence.status is not status
            ):
                raise ConstructionSharedResourceReceiptsV1Error(
                    "UNKNOWN/NOT_AVAILABLE must remain typed with no source claim"
                )

    def _payload(self) -> dict[str, Any]:
        source = (
            self.source_evidence.to_document()
            if type(self.source_evidence) is TypedUnavailableMeasurementV1
            else self.source_evidence.source_evidence_id
        )
        value = (
            self.value
            if type(self.value) is int
            else self.value.to_document()
        )
        return {
            "schema": "acfqp.construction_shared_resource_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "measurement_registry_id": self.registry.measurement_registry_id,
            "identity_binding_id": self.identity.identity_binding_id,
            "measurement_window_id": self.window.window_id,
            "path": self.path,
            "status": self.status.value,
            "source_claim_present": self.source_claim_present,
            "value": value,
            "measurement_method_id": self.method_id,
            "monitor_registration_id": self.monitor_registration_id,
            "source_evidence": source,
            "reducer": self.registry.method_by_path[self.path].reducer.value,
            "source_evidence_semantics_verified": False,
            "numeric_value_authorized": False,
        }

    @property
    def receipt_id(self) -> str:
        return _domain_id(SHARED_RESOURCE_RECEIPT_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_resource_receipt_id": self.receipt_id}


@dataclass(frozen=True, slots=True)
class SharedResourceReceiptSetV1:
    registry: SharedResourceMeasurementRegistryV1 = field(repr=False)
    identity: SharedResourceIdentityBindingV1 = field(repr=False)
    window: SharedResourceMeasurementWindowV1 = field(repr=False)
    receipts: tuple[SharedResourceReceiptV1, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.registry) is not SharedResourceMeasurementRegistryV1
            or type(self.identity) is not SharedResourceIdentityBindingV1
            or type(self.window) is not SharedResourceMeasurementWindowV1
            or type(self.receipts) is not tuple
            or any(type(item) is not SharedResourceReceiptV1 for item in self.receipts)
            or tuple(item.path for item in self.receipts) != SHARED_RESOURCE_PATHS
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "receipt set requires exactly the nine canonical shared paths"
            )
        if any(
            item.registry is not self.registry
            or item.identity is not self.identity
            or item.window is not self.window
            for item in self.receipts
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "receipt set contains a transplanted registry/identity/window"
            )
        observed_evidence = tuple(
            item.source_evidence
            for item in self.receipts
            if type(item.source_evidence) is SharedResourceSourceEvidenceV1
        )
        evidence_ids = tuple(item.source_evidence_id for item in observed_evidence)
        charge_keys = tuple(item.charge_key for item in observed_evidence)
        if (
            len(evidence_ids) != len(set(evidence_ids))
            or len(charge_keys) != len(set(charge_keys))
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "receipt set reuses source evidence or a charge key across paths"
            )

    @property
    def all_receipts_structurally_recorded(self) -> bool:
        return all(
            item.status is MeasurementStatusV1.RECORDED_UNVERIFIED
            for item in self.receipts
        )

    @property
    def unverified_reported_values(self) -> dict[str, int]:
        """Return source claims for semantic replay, never formal projection."""

        if not self.all_receipts_structurally_recorded:
            raise ConstructionSharedResourceReceiptsV1Error(
                "incomplete shared-resource receipts cannot expose all source claims"
            )
        return {item.path: item.value for item in self.receipts if type(item.value) is int}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_receipt_set.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "measurement_registry_id": self.registry.measurement_registry_id,
            "identity_binding_id": self.identity.identity_binding_id,
            "measurement_window_id": self.window.window_id,
            "receipt_ids": [item.receipt_id for item in self.receipts],
            "coverage_state": (
                "ALL_SOURCE_CLAIMS_STRUCTURALLY_RECORDED_UNVERIFIED"
                if self.all_receipts_structurally_recorded
                else "INCOMPLETE_TYPED"
            ),
            "source_evidence_semantics_verified": False,
            "numeric_projection_allowed": False,
            "formal_vector_authorized": False,
            "current_live_accounting_closed": False,
        }

    @property
    def receipt_set_id(self) -> str:
        return _domain_id(SHARED_RESOURCE_RECEIPT_SET_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_resource_receipt_set_id": self.receipt_set_id}


@dataclass(frozen=True, slots=True)
class HashPurposeRegistrationV1:
    purpose_key: str
    disposition: HashPurposeDispositionV1
    source_module: str
    source_symbol: str

    def __post_init__(self) -> None:
        _identifier(self.purpose_key, "hash purpose")
        disposition = _enum(HashPurposeDispositionV1, self.disposition, "hash disposition")
        object.__setattr__(self, "disposition", disposition)
        _module_symbol(self.source_module, self.source_symbol)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_hash_purpose_registration.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "purpose_key": self.purpose_key,
            "disposition": self.disposition.value,
            "source_module": self.source_module,
            "source_symbol": self.source_symbol,
        }

    @property
    def purpose_id(self) -> str:
        return _domain_id(HASH_PURPOSE_REGISTRATION_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "hash_purpose_id": self.purpose_id}


@dataclass(frozen=True, slots=True)
class RecursionSafeHashMeterProfileV1:
    registry: SharedResourceMeasurementRegistryV1 = field(repr=False)
    method_id: str
    monitor_registration_id: str
    purposes: tuple[HashPurposeRegistrationV1, ...] = field(repr=False)
    suppression_context_key: str
    primitive: str = "sha256_digest_finalization"
    counter_update_is_non_hashing: bool = True
    accounting_evidence_hashes_excluded: bool = True
    global_monkeypatch_forbidden: bool = True
    live_hook_installed: bool = False

    def __post_init__(self) -> None:
        if type(self.registry) is not SharedResourceMeasurementRegistryV1:
            raise ConstructionSharedResourceReceiptsV1Error(
                "hash meter requires one exact measurement registry"
            )
        for value, name in (
            (self.method_id, "hash method"),
            (self.monitor_registration_id, "hash monitor"),
        ):
            _cid(value, name)
        method = self.registry.method_by_path["common.hash_invocations"]
        monitor = self.registry.monitor_by_method_id.get(self.method_id)
        if (
            method.method_id != self.method_id
            or method.method_kind
            is not MeasurementMethodKindV1.RECURSION_SAFE_HASH_METER
            or monitor is None
            or monitor.monitor_registration_id != self.monitor_registration_id
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "hash meter method/monitor differs from its registry"
            )
        if (
            type(self.purposes) is not tuple
            or not self.purposes
            or any(type(item) is not HashPurposeRegistrationV1 for item in self.purposes)
            or tuple(sorted(self.purposes, key=lambda item: item.purpose_key)) != self.purposes
            or len({item.purpose_key for item in self.purposes}) != len(self.purposes)
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "hash purposes must be nonempty, sorted, and unique"
            )
        dispositions = {item.disposition for item in self.purposes}
        if not {
            HashPurposeDispositionV1.BUSINESS_CHARGEABLE,
            HashPurposeDispositionV1.ACCOUNTING_PROVENANCE_EXCLUDED,
        } <= dispositions:
            raise ConstructionSharedResourceReceiptsV1Error(
                "hash profile must separate business and accounting hashes"
            )
        excluded_keys = {
            item.purpose_key
            for item in self.purposes
            if item.disposition
            is HashPurposeDispositionV1.ACCOUNTING_PROVENANCE_EXCLUDED
        }
        if not REQUIRED_ACCOUNTING_HASH_EXCLUSION_PURPOSES <= excluded_keys:
            raise ConstructionSharedResourceReceiptsV1Error(
                "hash profile omits a required accounting-recursion exclusion"
            )
        _identifier(self.suppression_context_key, "hash suppression context")
        _identifier(self.primitive, "hash primitive")
        for name in (
            "counter_update_is_non_hashing",
            "accounting_evidence_hashes_excluded",
            "global_monkeypatch_forbidden",
            "live_hook_installed",
        ):
            _bool(getattr(self, name), name)
        if (
            self.counter_update_is_non_hashing is not True
            or self.accounting_evidence_hashes_excluded is not True
            or self.global_monkeypatch_forbidden is not True
            or self.live_hook_installed is not False
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "V1 hash meter must be recursion-safe schema-only evidence"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_recursion_safe_hash_meter_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "measurement_registry_id": self.registry.measurement_registry_id,
            "method_id": self.method_id,
            "monitor_registration_id": self.monitor_registration_id,
            "hash_purpose_ids": [item.purpose_id for item in self.purposes],
            "suppression_context_key": self.suppression_context_key,
            "primitive": self.primitive,
            "counter_update_is_non_hashing": self.counter_update_is_non_hashing,
            "accounting_evidence_hashes_excluded": self.accounting_evidence_hashes_excluded,
            "global_monkeypatch_forbidden": self.global_monkeypatch_forbidden,
            "live_hook_installed": self.live_hook_installed,
            "current_live_accounting_closed": False,
        }

    @property
    def hash_meter_profile_id(self) -> str:
        return _domain_id(
            RECURSION_SAFE_HASH_METER_PROFILE_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "hash_meter_profile_id": self.hash_meter_profile_id}


@dataclass(frozen=True, slots=True)
class NamedObligationV1:
    obligation_key: str
    kind: NamedObligationKindV1
    source_module: str
    source_symbol: str
    stage_kind: str
    counter_path: str
    count_on_pass: bool = True
    count_on_fail: bool = True
    record_before_raise: bool = True
    accounting_self_check: bool = False

    def __post_init__(self) -> None:
        _identifier(self.obligation_key, "obligation_key")
        kind = _enum(NamedObligationKindV1, self.kind, "obligation kind")
        object.__setattr__(self, "kind", kind)
        _module_symbol(self.source_module, self.source_symbol)
        _identifier(self.stage_kind, "stage_kind")
        registered_stages = {
            item.value for item in registry_v6.ConstructionStageKindV6
        }
        if self.stage_kind not in registered_stages:
            raise ConstructionSharedResourceReceiptsV1Error(
                "named obligation stage is outside registry V6"
            )
        expected = (
            "common.integrity_checks"
            if kind is NamedObligationKindV1.INTEGRITY
            else "common.protocol_checks"
        )
        if self.counter_path != expected:
            raise ConstructionSharedResourceReceiptsV1Error(
                "named obligation kind and counter path disagree"
            )
        for name in (
            "count_on_pass",
            "count_on_fail",
            "record_before_raise",
            "accounting_self_check",
        ):
            _bool(getattr(self, name), name)
        if (
            self.count_on_pass is not True
            or self.count_on_fail is not True
            or self.record_before_raise is not True
            or self.accounting_self_check is not False
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "V1 obligation must count PASS/FAIL before raise and exclude self-checks"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_named_obligation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "obligation_key": self.obligation_key,
            "kind": self.kind.value,
            "source_module": self.source_module,
            "source_symbol": self.source_symbol,
            "stage_kind": self.stage_kind,
            "counter_path": self.counter_path,
            "count_on_pass": self.count_on_pass,
            "count_on_fail": self.count_on_fail,
            "record_before_raise": self.record_before_raise,
            "accounting_self_check": self.accounting_self_check,
            "primitive": "named_predicate_evaluation",
        }

    @property
    def obligation_id(self) -> str:
        return _domain_id(NAMED_OBLIGATION_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "named_obligation_id": self.obligation_id}


@dataclass(frozen=True, slots=True)
class NamedObligationRegistryV1:
    registry: SharedResourceMeasurementRegistryV1 = field(repr=False)
    integrity_method_id: str
    protocol_method_id: str
    registration_authority_id: str
    obligations: tuple[NamedObligationV1, ...] = field(repr=False)
    live_hook_installed: bool = False

    def __post_init__(self) -> None:
        if type(self.registry) is not SharedResourceMeasurementRegistryV1:
            raise ConstructionSharedResourceReceiptsV1Error(
                "obligation registry requires one exact measurement registry"
            )
        for value, name in (
            (self.integrity_method_id, "integrity method"),
            (self.protocol_method_id, "protocol method"),
            (self.registration_authority_id, "obligation registration authority"),
        ):
            _cid(value, name)
        integrity = self.registry.method_by_path["common.integrity_checks"]
        protocol = self.registry.method_by_path["common.protocol_checks"]
        if (
            self.registration_authority_id
            != self.registry.registration_authority_id
            or self.integrity_method_id != integrity.method_id
            or self.protocol_method_id != protocol.method_id
            or integrity.method_kind
            is not MeasurementMethodKindV1.NAMED_OBLIGATION_METER
            or protocol.method_kind
            is not MeasurementMethodKindV1.NAMED_OBLIGATION_METER
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "obligation registry methods/authority differ from measurement registry"
            )
        if (
            type(self.obligations) is not tuple
            or not self.obligations
            or any(type(item) is not NamedObligationV1 for item in self.obligations)
            or tuple(sorted(self.obligations, key=lambda item: item.obligation_key))
            != self.obligations
            or len({item.obligation_key for item in self.obligations})
            != len(self.obligations)
            or len({item.obligation_id for item in self.obligations})
            != len(self.obligations)
        ):
            raise ConstructionSharedResourceReceiptsV1Error(
                "named obligations must be nonempty, sorted, and unique"
            )
        if {item.kind for item in self.obligations} != {
            NamedObligationKindV1.INTEGRITY,
            NamedObligationKindV1.PROTOCOL,
        }:
            raise ConstructionSharedResourceReceiptsV1Error(
                "obligation registry must include integrity and protocol predicates"
            )
        _bool(self.live_hook_installed, "live_hook_installed")
        if self.live_hook_installed is not False:
            raise ConstructionSharedResourceReceiptsV1Error(
                "V1 obligation registry is schema-only"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_named_obligation_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "measurement_registry_id": self.registry.measurement_registry_id,
            "integrity_method_id": self.integrity_method_id,
            "protocol_method_id": self.protocol_method_id,
            "registration_authority_id": self.registration_authority_id,
            "named_obligation_ids": [item.obligation_id for item in self.obligations],
            "unit": "one_named_predicate_evaluation",
            "accounting_runtime_self_checks_excluded": True,
            "live_hook_installed": self.live_hook_installed,
            "current_live_accounting_closed": False,
        }

    @property
    def obligation_registry_id(self) -> str:
        return _domain_id(NAMED_OBLIGATION_REGISTRY_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "named_obligation_registry_id": self.obligation_registry_id,
        }


def freeze_shared_resource_measurement_method_v1(
    *,
    path: str,
    method_kind: MeasurementMethodKindV1,
    primitive: str,
    value_kind: MeasurementValueKindV1 = MeasurementValueKindV1.EXACT,
) -> SharedResourceMeasurementMethodV1:
    """Freeze one method from the exact V6 path metadata."""

    leaf = _official_path_leaf(path)
    return SharedResourceMeasurementMethodV1(
        registry_v6.official_counter_registry_v6().registry_id,
        path,
        method_kind,
        value_kind,
        leaf.owner,
        leaf.semantics_id,
        leaf.unit,
        leaf.reducer,
        primitive,
    )


def shared_resource_charge_key_v1(
    *,
    measurement_registry_id: str,
    method_id: str,
    monitor_registration_id: str,
    identity_binding_id: str,
    window_id: str,
    source_schema_id: str,
    source_artifact_id: str,
    covered_start_sequence: int,
    covered_cutoff_sequence: int,
) -> str:
    """Derive the unique charge key independently of a reported value."""

    for value, name in (
        (measurement_registry_id, "charge measurement registry"),
        (method_id, "charge method"),
        (monitor_registration_id, "charge monitor"),
        (identity_binding_id, "charge identity"),
        (window_id, "charge window"),
        (source_artifact_id, "charge source artifact"),
    ):
        _cid(value, name)
    _identifier(source_schema_id, "charge source schema")
    _nonnegative(covered_start_sequence, "charge start sequence")
    _nonnegative(covered_cutoff_sequence, "charge cutoff sequence")
    if covered_cutoff_sequence < covered_start_sequence:
        raise ConstructionSharedResourceReceiptsV1Error(
            "charge cutoff precedes its start"
        )
    return _domain_id(
        SHARED_RESOURCE_CHARGE_KEY_V1_DOMAIN,
        {
            "schema": "acfqp.construction_shared_resource_charge_key.v1",
            "schema_version": SCHEMA_VERSION,
            "measurement_registry_id": measurement_registry_id,
            "method_id": method_id,
            "monitor_registration_id": monitor_registration_id,
            "identity_binding_id": identity_binding_id,
            "window_id": window_id,
            "source_schema_id": source_schema_id,
            "source_artifact_id": source_artifact_id,
            "covered_start_sequence": covered_start_sequence,
            "covered_cutoff_sequence": covered_cutoff_sequence,
        },
    )


def replay_shared_resource_receipt_set_structure_v1(
    value: SharedResourceReceiptSetV1,
    *,
    require_all_structurally_recorded: bool = False,
) -> SharedResourceReceiptSetV1:
    """Re-run structural validation without converting missing work to zero."""

    if type(value) is not SharedResourceReceiptSetV1:
        raise ConstructionSharedResourceReceiptsV1Error(
            "shared-resource receipt set has the wrong runtime type"
        )
    replayed = SharedResourceReceiptSetV1(
        value.registry,
        value.identity,
        value.window,
        value.receipts,
    )
    if replayed.receipt_set_id != value.receipt_set_id:
        raise ConstructionSharedResourceReceiptsV1Error(
            "shared-resource receipt set content ID changed"
        )
    if (
        require_all_structurally_recorded
        and not replayed.all_receipts_structurally_recorded
    ):
        raise ConstructionSharedResourceReceiptsV1Error(
            "shared-resource receipt set remains UNKNOWN/NOT_AVAILABLE"
        )
    return replayed


__all__ = [
    "HASH_PURPOSE_REGISTRATION_V1_DOMAIN",
    "HashPurposeDispositionV1",
    "HashPurposeRegistrationV1",
    "LOCAL_DOMAIN_TAGS",
    "MAX_SHARED_RESOURCE_PATHS",
    "MeasurementMethodKindV1",
    "MeasurementStatusV1",
    "MeasurementValueKindV1",
    "MeasurementWindowStateV1",
    "MonitorIsolationKindV1",
    "NAMED_OBLIGATION_REGISTRY_V1_DOMAIN",
    "NAMED_OBLIGATION_V1_DOMAIN",
    "NamedObligationKindV1",
    "NamedObligationRegistryV1",
    "NamedObligationV1",
    "PROFILE_KEY",
    "RECURSION_SAFE_HASH_METER_PROFILE_V1_DOMAIN",
    "RecursionSafeHashMeterProfileV1",
    "SCHEMA_VERSION",
    "SHARED_RESOURCE_IDENTITY_BINDING_V1_DOMAIN",
    "SHARED_RESOURCE_MEASUREMENT_METHOD_V1_DOMAIN",
    "SHARED_RESOURCE_MEASUREMENT_REGISTRY_V1_DOMAIN",
    "SHARED_RESOURCE_MEASUREMENT_WINDOW_V1_DOMAIN",
    "SHARED_RESOURCE_MONITOR_REGISTRATION_V1_DOMAIN",
    "SHARED_RESOURCE_PATHS",
    "SHARED_RESOURCE_RECEIPT_SET_V1_DOMAIN",
    "SHARED_RESOURCE_RECEIPT_V1_DOMAIN",
    "SHARED_RESOURCE_SOURCE_EVIDENCE_V1_DOMAIN",
    "SHARED_RESOURCE_CHARGE_KEY_V1_DOMAIN",
    "SUM_SHARED_RESOURCE_PATHS",
    "SharedResourceIdentityBindingV1",
    "SharedResourceMeasurementMethodV1",
    "SharedResourceMeasurementRegistryV1",
    "SharedResourceMeasurementWindowV1",
    "SharedResourceMonitorRegistrationV1",
    "SharedResourceReceiptSetV1",
    "SharedResourceReceiptV1",
    "SharedResourceSourceEvidenceV1",
    "SourceEvidenceKindV1",
    "TypedUnavailableMeasurementV1",
    "ConstructionSharedResourceReceiptsV1Error",
    "freeze_shared_resource_measurement_method_v1",
    "shared_resource_charge_key_v1",
    "replay_shared_resource_receipt_set_structure_v1",
]
