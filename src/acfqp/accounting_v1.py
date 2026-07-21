"""Normative Phase-3E native accounting and shared-resource projection.

This module implements the FQ1/FQ11 accounting substrate.  A native
``WorkVectorV1`` preserves route-specific counter leaves and their provenance;
it is never flattened merely to make local and fallback work comparable.  A
separate, content-addressed ``ComparisonProfileV1`` performs the frozen
projection onto eight shared resource axes.

The registry is deliberately strict:

* every operational leaf is present exactly once, including native zeroes;
* zero is an observation, not a default for a missing record;
* record metadata must exactly match the registry;
* derived/diagnostic records are retained but cannot enter route comparison;
* local and fallback attempts are separate vectors with mutually exclusive
  operational families.

No scalar cost or break-even functional is defined here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import (
    COMPARISON_PROFILE_DOMAIN,
    COMPARISON_VECTOR_DOMAIN,
    COUNTER_RECORD_DOMAIN,
    COUNTER_REGISTRY_DOMAIN,
    NATIVE_ZERO_ATTESTATION_DOMAIN,
    RECONCILIATION_PROOF_DOMAIN,
    WORK_VECTOR_DOMAIN,
    content_id as phase3e_content_id,
)


COUNTER_REGISTRY_KEY = "acfqp_counter_registry_v1"
COMPARISON_PROFILE_KEY = "comparison_profile_shared_resources_v1"
SCHEMA_VERSION = "1.0.0"


class AccountingV1Error(ValueError):
    """An accounting artifact is incomplete, inconsistent, or forged."""


class LaneEnum(str, Enum):
    OPERATIONAL = "operational"
    EVALUATION = "evaluation"
    PROVENANCE = "provenance"
    DIAGNOSTIC = "diagnostic"
    DERIVED_ONLY = "derived_only"


class ReducerEnum(str, Enum):
    SUM = "sum"
    MAX = "max"


class RouteKindEnum(str, Enum):
    ABSTRACT_ONLY_CERTIFICATE = "ABSTRACT_ONLY_CERTIFICATE"
    LOCAL_ATTEMPT = "LOCAL_ATTEMPT"
    DIRECT_FALLBACK = "DIRECT_FALLBACK"
    REBUILD = "REBUILD"


KERNEL_TRANSITION_CALLS = "kernel_transition_calls"
NONKERNEL_COMPUTE_EVENTS = "nonkernel_compute_events"
PROCESS_LAUNCHES = "process_launches"
READ_BYTES = "read_bytes"
STAGED_BYTES = "staged_bytes"
OUTPUT_BYTES = "output_bytes"
PEAK_MOUNTED_BYTES = "peak_mounted_bytes"
PEAK_WORKING_BYTES = "peak_working_bytes"

SHARED_AXES = (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    OUTPUT_BYTES,
    PEAK_MOUNTED_BYTES,
    PEAK_WORKING_BYTES,
    PROCESS_LAUNCHES,
    READ_BYTES,
    STAGED_BYTES,
)

_PATH = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")


def _strict_nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AccountingV1Error(f"{field} must be a nonnegative exact integer")
    return value


def _strict_positive_int(value: Any, field: str) -> int:
    value = _strict_nonnegative_int(value, field)
    if value == 0:
        raise AccountingV1Error(f"{field} must be positive")
    return value


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise AccountingV1Error(f"{field} must be a nonempty canonical identifier")
    return value


def _path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _PATH.fullmatch(value):
        raise AccountingV1Error(f"invalid {field}: {value!r}")
    return value


def _enum(value: Any, enum_type: type[Enum], field: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise AccountingV1Error(f"invalid {field}: {value!r}") from error


@dataclass(frozen=True, slots=True)
class CounterSemanticsV1:
    path: str
    semantics_id: str
    owner: str
    unit: str
    lane: LaneEnum
    scope: str
    reducer: ReducerEnum
    comparison_axis: str | None
    required: bool

    def __post_init__(self) -> None:
        _path(self.path, "counter path")
        _identifier(self.semantics_id, "semantics_id")
        _identifier(self.owner, "owner")
        _identifier(self.unit, "unit")
        object.__setattr__(self, "lane", _enum(self.lane, LaneEnum, "lane"))
        _identifier(self.scope, "scope")
        object.__setattr__(self, "reducer", _enum(self.reducer, ReducerEnum, "reducer"))
        if self.comparison_axis is not None:
            _identifier(self.comparison_axis, "comparison_axis")
        if not isinstance(self.required, bool):
            raise AccountingV1Error("required must be boolean")
        if self.lane is LaneEnum.OPERATIONAL:
            if not self.required:
                raise AccountingV1Error("every operational leaf must be required")
            if self.comparison_axis not in SHARED_AXES:
                raise AccountingV1Error(
                    "every operational leaf must name one shared comparison axis"
                )
        elif self.comparison_axis is not None:
            raise AccountingV1Error("non-operational leaves cannot name a comparison axis")

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "lane": self.lane.value,
            "scope": self.scope,
            "reducer": self.reducer.value,
            "comparison_axis": self.comparison_axis,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "CounterSemanticsV1":
        expected = {
            "path",
            "semantics_id",
            "owner",
            "unit",
            "lane",
            "scope",
            "reducer",
            "comparison_axis",
            "required",
        }
        if not isinstance(document, Mapping) or set(document) != expected:
            raise AccountingV1Error("counter semantics field set mismatch")
        return cls(
            path=document["path"],
            semantics_id=document["semantics_id"],
            owner=document["owner"],
            unit=document["unit"],
            lane=document["lane"],
            scope=document["scope"],
            reducer=document["reducer"],
            comparison_axis=document["comparison_axis"],
            required=document["required"],
        )


@dataclass(frozen=True, slots=True)
class CounterRegistryV1:
    registry_key: str
    schema_version: str
    leaves: tuple[CounterSemanticsV1, ...]

    def __post_init__(self) -> None:
        _identifier(self.registry_key, "registry_key")
        _identifier(self.schema_version, "schema_version")
        if not self.leaves or tuple(sorted(self.leaves, key=lambda leaf: leaf.path)) != self.leaves:
            raise AccountingV1Error("registry leaves must be nonempty and path-sorted")
        if len({leaf.path for leaf in self.leaves}) != len(self.leaves):
            raise AccountingV1Error("registry repeats a counter path")

    @property
    def by_path(self) -> dict[str, CounterSemanticsV1]:
        return {leaf.path: leaf for leaf in self.leaves}

    @property
    def operational_leaves(self) -> tuple[CounterSemanticsV1, ...]:
        return tuple(leaf for leaf in self.leaves if leaf.lane is LaneEnum.OPERATIONAL)

    @property
    def required_paths(self) -> tuple[str, ...]:
        return tuple(leaf.path for leaf in self.leaves if leaf.required)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.counter_registry.v1",
            "registry_key": self.registry_key,
            "schema_version": self.schema_version,
            "leaves": [leaf.to_dict() for leaf in self.leaves],
        }

    @property
    def registry_id(self) -> str:
        return phase3e_content_id(COUNTER_REGISTRY_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "counter_registry_id": self.registry_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "CounterRegistryV1":
        expected = {
            "schema",
            "registry_key",
            "schema_version",
            "leaves",
            "counter_registry_id",
        }
        if not isinstance(document, Mapping) or set(document) != expected:
            raise AccountingV1Error("counter registry field set mismatch")
        if document["schema"] != "acfqp.counter_registry.v1":
            raise AccountingV1Error("counter registry schema mismatch")
        rows = document["leaves"]
        if not isinstance(rows, list):
            raise AccountingV1Error("counter registry leaves must be a list")
        registry = cls(
            document["registry_key"],
            document["schema_version"],
            tuple(CounterSemanticsV1.from_dict(row) for row in rows),
        )
        if document["counter_registry_id"] != registry.registry_id:
            raise AccountingV1Error("counter registry content ID mismatch")
        registry.validate_official_catalogue()
        return registry

    def validate_official_catalogue(self) -> None:
        expected = official_counter_registry_v1()
        if self.registry_key != COUNTER_REGISTRY_KEY or self.schema_version != SCHEMA_VERSION:
            raise AccountingV1Error("official registry key/version mismatch")
        if self.leaves != expected.leaves:
            raise AccountingV1Error("official counter catalogue metadata mismatch")

    def materialize(
        self,
        *,
        subject_id: str,
        route_kind: RouteKindEnum | str,
        records: Iterable["CounterRecordV1"],
    ) -> "WorkVectorV1":
        self.validate_official_catalogue()
        route = _enum(route_kind, RouteKindEnum, "route_kind")
        rows = tuple(records)
        if tuple(sorted(rows, key=lambda row: row.path)) != rows:
            raise AccountingV1Error("counter records must be path-sorted")
        if len({row.path for row in rows}) != len(rows):
            raise AccountingV1Error("counter records repeat a path")
        by_path = self.by_path
        for record in rows:
            if record.counter_registry_id != self.registry_id:
                raise AccountingV1Error("counter record registry ID mismatch")
            leaf = by_path.get(record.path)
            if leaf is None:
                raise AccountingV1Error(f"unknown counter path {record.path!r}")
            record.verify_against(leaf)
        observed = {record.path for record in rows}
        required = set(self.required_paths)
        missing = sorted(required - observed)
        if missing:
            raise AccountingV1Error(f"missing required counter records: {missing!r}")
        self._validate_reconciliation({row.path: row.value for row in rows})
        vector = WorkVectorV1(
            counter_registry_id=self.registry_id,
            subject_id=_identifier(subject_id, "subject_id"),
            route_kind=route,
            records=rows,
        )
        self.validate_vector(vector)
        return vector

    def validate_vector(self, vector: "WorkVectorV1") -> None:
        if vector.counter_registry_id != self.registry_id:
            raise AccountingV1Error("work vector registry ID mismatch")
        if tuple(sorted(vector.records, key=lambda row: row.path)) != vector.records:
            raise AccountingV1Error("work vector records are not path-sorted")
        if len({row.path for row in vector.records}) != len(vector.records):
            raise AccountingV1Error("work vector repeats a path")
        by_path = self.by_path
        for row in vector.records:
            leaf = by_path.get(row.path)
            if leaf is None:
                raise AccountingV1Error(f"unknown work-vector path {row.path!r}")
            if row.counter_registry_id != self.registry_id:
                raise AccountingV1Error("embedded record registry ID mismatch")
            row.verify_against(leaf)
        observed = {row.path for row in vector.records}
        missing = sorted(set(self.required_paths) - observed)
        if missing:
            raise AccountingV1Error(f"work vector missing required records: {missing!r}")
        values = {row.path: row.value for row in vector.records}
        self._validate_reconciliation(values)
        self._validate_route_exclusivity(vector.route_kind, values)

    @staticmethod
    def _validate_reconciliation(values: Mapping[str, int]) -> None:
        groups = (
            ("route.attempts", "route.successes", "route.failures"),
            ("solver.attempts", "solver.successes", "solver.failures"),
        )
        for total, successes, failures in groups:
            present = {path for path in (total, successes, failures) if path in values}
            if present and len(present) != 3:
                raise AccountingV1Error(
                    f"partial reconciliation group for {total!r} is forbidden"
                )
            if present and values[total] != values[successes] + values[failures]:
                raise AccountingV1Error(f"reconciliation failed for {total!r}")
        exits = {"process.exit_successes", "process.exit_failures"}
        present_exits = exits & set(values)
        if present_exits and present_exits != exits:
            raise AccountingV1Error("partial process-exit reconciliation is forbidden")
        if present_exits and values["process.launches"] != (
            values["process.exit_successes"] + values["process.exit_failures"]
        ):
            raise AccountingV1Error("process launch/exit reconciliation failed")
        output = values["io.output_bytes"]
        for path in (
            "epoch.serialized_bytes",
            "model.serialized_bytes",
            "capability.serialized_bytes",
        ):
            if path in values and values[path] > output:
                raise AccountingV1Error(f"{path} cannot exceed io.output_bytes")
        if values.get("branch.evaluations", 0) != 0:
            raise AccountingV1Error(
                "branch.evaluations is generic derived-only volume and must be "
                "reclassified as a registered Bellman/action/solver event"
            )

    @staticmethod
    def _validate_route_exclusivity(
        route_kind: RouteKindEnum, values: Mapping[str, int]
    ) -> None:
        families: tuple[str, ...]
        if route_kind is RouteKindEnum.LOCAL_ATTEMPT:
            families = ("fallback.", "rebuild.")
        elif route_kind is RouteKindEnum.DIRECT_FALLBACK:
            families = ("local.", "rebuild.")
        elif route_kind is RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE:
            families = ("local.", "fallback.", "rebuild.")
        elif route_kind is RouteKindEnum.REBUILD:
            families = ("common.", "local.", "fallback.", "control.")
        else:  # pragma: no cover - enum exhaustiveness
            raise AccountingV1Error("unknown route kind")
        nonzero = sorted(
            path
            for path, value in values.items()
            if value and any(path.startswith(prefix) for prefix in families)
        )
        if nonzero:
            raise AccountingV1Error(
                f"route-family exclusivity violation for {route_kind.value}: {nonzero!r}"
            )


@dataclass(frozen=True, slots=True)
class CounterRecordV1:
    counter_registry_id: str
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
        _identifier(self.counter_registry_id, "counter_registry_id")
        _path(self.path, "counter path")
        _strict_nonnegative_int(self.value, self.path)
        if not isinstance(self.observed, bool):
            raise AccountingV1Error("observed must be boolean")
        _identifier(self.recorder_id, "recorder_id")
        _identifier(self.semantics_id, "semantics_id")
        _identifier(self.owner, "owner")
        _identifier(self.unit, "unit")
        object.__setattr__(self, "lane", _enum(self.lane, LaneEnum, "lane"))
        _identifier(self.scope, "scope")
        object.__setattr__(self, "reducer", _enum(self.reducer, ReducerEnum, "reducer"))

    @classmethod
    def observe(
        cls,
        registry: CounterRegistryV1,
        path: str,
        value: int,
        *,
        recorder_id: str,
    ) -> "CounterRecordV1":
        try:
            leaf = registry.by_path[path]
        except KeyError as error:
            raise AccountingV1Error(f"unknown counter path {path!r}") from error
        return cls(
            registry.registry_id,
            path,
            value,
            True,
            recorder_id,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        )

    def verify_against(self, leaf: CounterSemanticsV1) -> None:
        if self.observed is not True:
            raise AccountingV1Error(
                f"{self.path} is unobserved; missing cannot be inferred as native zero"
            )
        expected = (
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        )
        actual = (
            self.semantics_id,
            self.owner,
            self.unit,
            self.lane,
            self.scope,
            self.reducer,
        )
        if actual != expected:
            raise AccountingV1Error(f"counter metadata mismatch for {self.path!r}")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.counter_record.v1",
            "counter_registry_id": self.counter_registry_id,
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
        return phase3e_content_id(COUNTER_RECORD_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "counter_record_id": self.record_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "CounterRecordV1":
        expected = {
            "schema",
            "counter_registry_id",
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
        if not isinstance(document, Mapping) or set(document) != expected:
            raise AccountingV1Error("counter record field set mismatch")
        if document["schema"] != "acfqp.counter_record.v1":
            raise AccountingV1Error("counter record schema mismatch")
        record = cls(
            counter_registry_id=document["counter_registry_id"],
            path=document["path"],
            value=document["value"],
            observed=document["observed"],
            recorder_id=document["recorder_id"],
            semantics_id=document["semantics_id"],
            owner=document["owner"],
            unit=document["unit"],
            lane=document["lane"],
            scope=document["scope"],
            reducer=document["reducer"],
        )
        if document["counter_record_id"] != record.record_id:
            raise AccountingV1Error("counter record content ID mismatch")
        return record


@dataclass(frozen=True, slots=True)
class WorkVectorV1:
    counter_registry_id: str
    subject_id: str
    route_kind: RouteKindEnum
    records: tuple[CounterRecordV1, ...]

    def __post_init__(self) -> None:
        _identifier(self.counter_registry_id, "counter_registry_id")
        _identifier(self.subject_id, "subject_id")
        object.__setattr__(self, "route_kind", _enum(self.route_kind, RouteKindEnum, "route_kind"))
        if not self.records:
            raise AccountingV1Error("work vector cannot be empty")
        if tuple(sorted(self.records, key=lambda row: row.path)) != self.records:
            raise AccountingV1Error("work-vector records must be path-sorted")
        if len({row.path for row in self.records}) != len(self.records):
            raise AccountingV1Error("work vector repeats a path")

    @property
    def values(self) -> dict[str, int]:
        return {row.path: row.value for row in self.records}

    def value(self, path: str) -> int:
        try:
            return self.values[path]
        except KeyError as error:
            raise AccountingV1Error(f"work vector has no record {path!r}") from error

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.work_vector.v1",
            "counter_registry_id": self.counter_registry_id,
            "subject_id": self.subject_id,
            "route_kind": self.route_kind.value,
            "counter_record_ids": [row.record_id for row in self.records],
        }

    @property
    def work_vector_id(self) -> str:
        return phase3e_content_id(WORK_VECTOR_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "records": [row.to_dict() for row in self.records],
            "work_vector_id": self.work_vector_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any], registry: CounterRegistryV1
    ) -> "WorkVectorV1":
        expected = {
            "schema",
            "counter_registry_id",
            "subject_id",
            "route_kind",
            "counter_record_ids",
            "records",
            "work_vector_id",
        }
        if not isinstance(document, Mapping) or set(document) != expected:
            raise AccountingV1Error("work vector field set mismatch")
        if document["schema"] != "acfqp.work_vector.v1":
            raise AccountingV1Error("work vector schema mismatch")
        rows = document["records"]
        ids = document["counter_record_ids"]
        if not isinstance(rows, list) or not isinstance(ids, list):
            raise AccountingV1Error("work-vector rows and IDs must be lists")
        records = tuple(CounterRecordV1.from_dict(row) for row in rows)
        if ids != [row.record_id for row in records]:
            raise AccountingV1Error("work-vector counter record IDs mismatch")
        vector = cls(
            document["counter_registry_id"],
            document["subject_id"],
            document["route_kind"],
            records,
        )
        registry.validate_vector(vector)
        if document["work_vector_id"] != vector.work_vector_id:
            raise AccountingV1Error("work vector content ID mismatch")
        return vector


@dataclass(frozen=True, slots=True)
class NativeZeroAttestationV1:
    work_vector_id: str
    zero_paths: tuple[str, ...]
    recorder_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _identifier(self.work_vector_id, "work_vector_id")
        if tuple(sorted(self.zero_paths)) != self.zero_paths or len(set(self.zero_paths)) != len(self.zero_paths):
            raise AccountingV1Error("native-zero paths must be unique and sorted")
        if len(self.zero_paths) != len(self.recorder_ids):
            raise AccountingV1Error("native-zero recorder alignment mismatch")
        for path in self.zero_paths:
            _path(path, "native-zero path")
        for recorder_id in self.recorder_ids:
            _identifier(recorder_id, "native-zero recorder_id")

    @classmethod
    def derive(
        cls, vector: WorkVectorV1, registry: CounterRegistryV1
    ) -> "NativeZeroAttestationV1":
        registry.validate_vector(vector)
        zeros = tuple(
            row for row in vector.records
            if registry.by_path[row.path].required and row.value == 0
        )
        return cls(
            vector.work_vector_id,
            tuple(row.path for row in zeros),
            tuple(row.recorder_id for row in zeros),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.native_zero_attestation.v1",
            "work_vector_id": self.work_vector_id,
            "zero_paths": list(self.zero_paths),
            "recorder_ids": list(self.recorder_ids),
        }

    @property
    def native_zero_attestation_id(self) -> str:
        return phase3e_content_id(NATIVE_ZERO_ATTESTATION_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "native_zero_attestation_id": self.native_zero_attestation_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "NativeZeroAttestationV1":
        expected = {
            "schema",
            "work_vector_id",
            "zero_paths",
            "recorder_ids",
            "native_zero_attestation_id",
        }
        if not isinstance(document, Mapping) or set(document) != expected:
            raise AccountingV1Error("native-zero attestation field set mismatch")
        if document["schema"] != "acfqp.native_zero_attestation.v1":
            raise AccountingV1Error("native-zero attestation schema mismatch")
        if not isinstance(document["zero_paths"], list) or not isinstance(
            document["recorder_ids"], list
        ):
            raise AccountingV1Error("native-zero paths/recorders must be lists")
        result = cls(
            document["work_vector_id"],
            tuple(document["zero_paths"]),
            tuple(document["recorder_ids"]),
        )
        if document["native_zero_attestation_id"] != result.native_zero_attestation_id:
            raise AccountingV1Error("native-zero attestation content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class ReconciliationProofV1:
    """Replayable declaration of the reconciliation rules actually checked."""

    work_vector_id: str
    equations: tuple[str, ...]
    output_byte_subset_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        _identifier(self.work_vector_id, "work_vector_id")
        if tuple(sorted(self.equations)) != self.equations or len(set(self.equations)) != len(self.equations):
            raise AccountingV1Error("reconciliation equations must be unique and sorted")
        if tuple(sorted(self.output_byte_subset_paths)) != self.output_byte_subset_paths or len(set(self.output_byte_subset_paths)) != len(self.output_byte_subset_paths):
            raise AccountingV1Error("byte-subset paths must be unique and sorted")
        for equation in self.equations:
            _identifier(equation, "reconciliation equation")
        for path in self.output_byte_subset_paths:
            _path(path, "output-byte subset path")

    @classmethod
    def derive(
        cls, vector: WorkVectorV1, registry: CounterRegistryV1
    ) -> "ReconciliationProofV1":
        registry.validate_vector(vector)
        values = vector.values
        equations: list[str] = []
        if all(path in values for path in ("route.attempts", "route.successes", "route.failures")):
            equations.append("route_attempts_equals_successes_plus_failures")
        if all(path in values for path in ("solver.attempts", "solver.successes", "solver.failures")):
            equations.append("solver_attempts_equals_successes_plus_failures")
        if all(path in values for path in ("process.exit_successes", "process.exit_failures")):
            equations.append("process_launches_equals_exit_successes_plus_failures")
        subset_paths = tuple(
            path
            for path in (
                "capability.serialized_bytes",
                "epoch.serialized_bytes",
                "model.serialized_bytes",
            )
            if path in values
        )
        return cls(vector.work_vector_id, tuple(sorted(equations)), subset_paths)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.reconciliation_proof.v1",
            "work_vector_id": self.work_vector_id,
            "equations": list(self.equations),
            "output_byte_subset_paths": list(self.output_byte_subset_paths),
        }

    @property
    def reconciliation_proof_id(self) -> str:
        return phase3e_content_id(RECONCILIATION_PROOF_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reconciliation_proof_id": self.reconciliation_proof_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ReconciliationProofV1":
        expected = {
            "schema",
            "work_vector_id",
            "equations",
            "output_byte_subset_paths",
            "reconciliation_proof_id",
        }
        if not isinstance(document, Mapping) or set(document) != expected:
            raise AccountingV1Error("reconciliation proof field set mismatch")
        if document["schema"] != "acfqp.reconciliation_proof.v1":
            raise AccountingV1Error("reconciliation proof schema mismatch")
        if not isinstance(document["equations"], list) or not isinstance(
            document["output_byte_subset_paths"], list
        ):
            raise AccountingV1Error("reconciliation proof rows must be lists")
        result = cls(
            document["work_vector_id"],
            tuple(document["equations"]),
            tuple(document["output_byte_subset_paths"]),
        )
        if document["reconciliation_proof_id"] != result.reconciliation_proof_id:
            raise AccountingV1Error("reconciliation proof content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class ComparisonAxisV1:
    name: str
    unit: str
    reducer: ReducerEnum
    semantics: str

    def __post_init__(self) -> None:
        _identifier(self.name, "comparison axis")
        _identifier(self.unit, "axis unit")
        object.__setattr__(self, "reducer", _enum(self.reducer, ReducerEnum, "axis reducer"))
        if not isinstance(self.semantics, str) or not self.semantics:
            raise AccountingV1Error("axis semantics must be nonempty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "unit": self.unit,
            "reducer": self.reducer.value,
            "semantics": self.semantics,
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "ComparisonAxisV1":
        if not isinstance(row, Mapping) or set(row) != {"name", "unit", "reducer", "semantics"}:
            raise AccountingV1Error("comparison axis field set mismatch")
        return cls(row["name"], row["unit"], row["reducer"], row["semantics"])


@dataclass(frozen=True, slots=True)
class ProjectionTermV1:
    source_leaf: str
    target_axis: str
    coefficient: int
    source_lane: LaneEnum
    source_semantics_id: str
    reducer: ReducerEnum

    def __post_init__(self) -> None:
        _path(self.source_leaf, "projection source leaf")
        _identifier(self.target_axis, "projection target axis")
        _strict_positive_int(self.coefficient, "projection coefficient")
        object.__setattr__(self, "source_lane", _enum(self.source_lane, LaneEnum, "source_lane"))
        _identifier(self.source_semantics_id, "source_semantics_id")
        object.__setattr__(self, "reducer", _enum(self.reducer, ReducerEnum, "projection reducer"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_leaf": self.source_leaf,
            "target_axis": self.target_axis,
            "coefficient": self.coefficient,
            "source_lane": self.source_lane.value,
            "source_semantics_id": self.source_semantics_id,
            "reducer": self.reducer.value,
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "ProjectionTermV1":
        expected = {
            "source_leaf",
            "target_axis",
            "coefficient",
            "source_lane",
            "source_semantics_id",
            "reducer",
        }
        if not isinstance(row, Mapping) or set(row) != expected:
            raise AccountingV1Error("projection term field set mismatch")
        return cls(**{field: row[field] for field in expected})


@dataclass(frozen=True, slots=True)
class ComparisonProfileV1:
    profile_key: str
    schema_version: str
    counter_registry_id: str
    axes: tuple[ComparisonAxisV1, ...]
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        _identifier(self.profile_key, "profile_key")
        _identifier(self.schema_version, "schema_version")
        _identifier(self.counter_registry_id, "counter_registry_id")
        if tuple(sorted(self.axes, key=lambda axis: axis.name)) != self.axes:
            raise AccountingV1Error("comparison axes must be name-sorted")
        if len({axis.name for axis in self.axes}) != len(self.axes):
            raise AccountingV1Error("comparison profile repeats an axis")
        if tuple(sorted(self.terms, key=lambda term: term.source_leaf)) != self.terms:
            raise AccountingV1Error("projection terms must be source-sorted")
        if len({term.source_leaf for term in self.terms}) != len(self.terms):
            raise AccountingV1Error("an operational leaf may project only once")

    def validate(self, registry: CounterRegistryV1) -> None:
        registry.validate_official_catalogue()
        if self.profile_key != COMPARISON_PROFILE_KEY or self.schema_version != SCHEMA_VERSION:
            raise AccountingV1Error("comparison profile key/version mismatch")
        if self.counter_registry_id != registry.registry_id:
            raise AccountingV1Error("comparison profile registry ID mismatch")
        expected_axes = official_shared_axes_v1()
        if self.axes != expected_axes:
            raise AccountingV1Error("shared-axis catalogue metadata mismatch")
        by_axis = {axis.name: axis for axis in self.axes}
        expected_paths = {leaf.path for leaf in registry.operational_leaves}
        actual_paths = {term.source_leaf for term in self.terms}
        if actual_paths != expected_paths:
            raise AccountingV1Error(
                "operational projection coverage mismatch; "
                f"missing={sorted(expected_paths - actual_paths)!r}, "
                f"extra={sorted(actual_paths - expected_paths)!r}"
            )
        for term in self.terms:
            leaf = registry.by_path[term.source_leaf]
            if leaf.lane is not LaneEnum.OPERATIONAL:
                raise AccountingV1Error("non-operational leaf entered route comparison")
            if term.source_lane is not LaneEnum.OPERATIONAL:
                raise AccountingV1Error("projection source lane is not operational")
            if term.source_semantics_id != leaf.semantics_id:
                raise AccountingV1Error("projection semantics ID mismatch")
            if term.coefficient != 1:
                raise AccountingV1Error("V1 registered event coefficients are exactly one")
            if term.target_axis != leaf.comparison_axis:
                raise AccountingV1Error("projection target does not match registry")
            axis = by_axis.get(term.target_axis)
            if axis is None or term.reducer is not axis.reducer or leaf.reducer is not axis.reducer:
                raise AccountingV1Error("projection reducer mismatch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_profile.v1",
            "profile_key": self.profile_key,
            "schema_version": self.schema_version,
            "counter_registry_id": self.counter_registry_id,
            "axes": [axis.to_dict() for axis in self.axes],
            "terms": [term.to_dict() for term in self.terms],
        }

    @property
    def comparison_profile_id(self) -> str:
        return phase3e_content_id(COMPARISON_PROFILE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "comparison_profile_id": self.comparison_profile_id}

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any], registry: CounterRegistryV1
    ) -> "ComparisonProfileV1":
        expected = {
            "schema",
            "profile_key",
            "schema_version",
            "counter_registry_id",
            "axes",
            "terms",
            "comparison_profile_id",
        }
        if not isinstance(document, Mapping) or set(document) != expected:
            raise AccountingV1Error("comparison profile field set mismatch")
        if document["schema"] != "acfqp.comparison_profile.v1":
            raise AccountingV1Error("comparison profile schema mismatch")
        if not isinstance(document["axes"], list) or not isinstance(document["terms"], list):
            raise AccountingV1Error("comparison axes/terms must be lists")
        profile = cls(
            document["profile_key"],
            document["schema_version"],
            document["counter_registry_id"],
            tuple(ComparisonAxisV1.from_dict(row) for row in document["axes"]),
            tuple(ProjectionTermV1.from_dict(row) for row in document["terms"]),
        )
        profile.validate(registry)
        if document["comparison_profile_id"] != profile.comparison_profile_id:
            raise AccountingV1Error("comparison profile content ID mismatch")
        return profile


@dataclass(frozen=True, slots=True)
class ComparisonVectorV1:
    comparison_profile_id: str
    work_vector_id: str
    subject_id: str
    route_kind: RouteKindEnum
    values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        _identifier(self.comparison_profile_id, "comparison_profile_id")
        _identifier(self.work_vector_id, "work_vector_id")
        _identifier(self.subject_id, "subject_id")
        object.__setattr__(self, "route_kind", _enum(self.route_kind, RouteKindEnum, "route_kind"))
        if tuple(sorted(self.values)) != self.values or len(dict(self.values)) != len(self.values):
            raise AccountingV1Error("comparison values must be unique and axis-sorted")
        if tuple(axis for axis, _ in self.values) != SHARED_AXES:
            raise AccountingV1Error("comparison vector must contain the exact eight axes")
        for axis, value in self.values:
            _identifier(axis, "comparison axis")
            _strict_nonnegative_int(value, axis)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_vector.v1",
            "comparison_profile_id": self.comparison_profile_id,
            "work_vector_id": self.work_vector_id,
            "subject_id": self.subject_id,
            "route_kind": self.route_kind.value,
            "values": [{"axis": axis, "value": value} for axis, value in self.values],
        }

    @property
    def comparison_vector_id(self) -> str:
        return phase3e_content_id(COMPARISON_VECTOR_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "comparison_vector_id": self.comparison_vector_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ComparisonVectorV1":
        expected = {
            "schema",
            "comparison_profile_id",
            "work_vector_id",
            "subject_id",
            "route_kind",
            "values",
            "comparison_vector_id",
        }
        if not isinstance(document, Mapping) or set(document) != expected:
            raise AccountingV1Error("comparison vector field set mismatch")
        if document["schema"] != "acfqp.comparison_vector.v1":
            raise AccountingV1Error("comparison vector schema mismatch")
        rows = document["values"]
        if not isinstance(rows, list):
            raise AccountingV1Error("comparison vector values must be a list")
        values: list[tuple[str, int]] = []
        for row in rows:
            if not isinstance(row, Mapping) or set(row) != {"axis", "value"}:
                raise AccountingV1Error("comparison-vector value row mismatch")
            values.append((row["axis"], row["value"]))
        vector = cls(
            document["comparison_profile_id"],
            document["work_vector_id"],
            document["subject_id"],
            document["route_kind"],
            tuple(values),
        )
        if document["comparison_vector_id"] != vector.comparison_vector_id:
            raise AccountingV1Error("comparison vector content ID mismatch")
        return vector

    def value(self, axis: str) -> int:
        try:
            return dict(self.values)[axis]
        except KeyError as error:
            raise AccountingV1Error(f"unknown comparison axis {axis!r}") from error


def derive_comparison_vector_v1(
    vector: WorkVectorV1,
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
) -> ComparisonVectorV1:
    """Recompute the exact shared-axis vector from native records."""

    registry.validate_vector(vector)
    profile.validate(registry)
    source = vector.values
    axes = {axis.name: 0 for axis in profile.axes}
    for term in profile.terms:
        contribution = source[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axes[term.target_axis] += contribution
        else:
            axes[term.target_axis] = max(axes[term.target_axis], contribution)
    return ComparisonVectorV1(
        profile.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        vector.route_kind,
        tuple(sorted(axes.items())),
    )


def _op(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    scope: str,
    axis: str = NONKERNEL_COMPUTE_EVENTS,
    reducer: ReducerEnum = ReducerEnum.SUM,
) -> CounterSemanticsV1:
    return CounterSemanticsV1(
        path,
        semantics_id,
        owner,
        unit,
        LaneEnum.OPERATIONAL,
        scope,
        reducer,
        axis,
        True,
    )


def _noncost(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    scope: str,
    lane: LaneEnum = LaneEnum.DERIVED_ONLY,
) -> CounterSemanticsV1:
    return CounterSemanticsV1(
        path,
        semantics_id,
        owner,
        unit,
        lane,
        scope,
        ReducerEnum.SUM,
        None,
        False,
    )


def _reconciled(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    scope: str,
) -> CounterSemanticsV1:
    """Required native closure record that is excluded from comparison cost."""

    return CounterSemanticsV1(
        path,
        semantics_id,
        owner,
        unit,
        LaneEnum.DERIVED_ONLY,
        scope,
        ReducerEnum.SUM,
        None,
        True,
    )


def official_counter_registry_v1() -> CounterRegistryV1:
    """Return the exact FQ11 ``acfqp_counter_registry_v1`` catalogue."""

    leaves = (
        _noncost("branch.evaluations", "generic-branch-eval-v1", "legacy_adapter", "evaluations", "transaction_or_attempt"),
        _noncost("capability.serialized_bytes", "capability-serialized-byte-v1", "artifact_writer", "bytes", "transaction"),
        _op("common.abstract_audit_obligations", "audit-obligation-v1", "abstract_auditor", "obligations", "decision_point"),
        _op("common.abstract_bellman_backups", "bellman-backup-v1", "abstract_planner", "backups", "occurrence"),
        _op("common.hash_invocations", "hash-invocation-v1", "content_id_layer", "invocations", "attempt"),
        _op("common.integrity_checks", "integrity-check-v1", "artifact_verifier", "checks", "attempt"),
        _op("common.protocol_checks", "protocol-check-v1", "state_machine_verifier", "checks", "attempt"),
        _op("control.cap_checks", "cap-check-v1", "trusted_replay", "checks", "transaction_or_attempt"),
        _op("control.cap_rejections", "cap-rejection-v1", "trusted_replay", "rejections", "transaction_or_attempt"),
        _noncost("epoch.serialized_bytes", "epoch-serialized-byte-v1", "artifact_writer", "bytes", "build_epoch"),
        _noncost(
            "evaluation.semantic_integrity_checks",
            "evaluation-semantic-integrity-check-v1",
            "standalone_semantic_verifier",
            "checks",
            "evaluation_replay",
            LaneEnum.EVALUATION,
        ),
        _noncost(
            "evaluation.semantic_protocol_checks",
            "evaluation-semantic-protocol-check-v1",
            "standalone_semantic_verifier",
            "checks",
            "evaluation_replay",
            LaneEnum.EVALUATION,
        ),
        _op("fallback.actions_evaluated", "fallback-action-eval-v1", "ground_solver", "actions", "attempt"),
        _op("fallback.bellman_backups", "bellman-backup-v1", "ground_solver", "backups", "attempt"),
        _op("fallback.ground_steps", "ground-transition-call-v1", "ground_solver", "calls", "attempt", KERNEL_TRANSITION_CALLS),
        _op("fallback.outcome_rows", "positive-outcome-row-v1", "ground_solver", "rows", "attempt"),
        _op("fallback.states_expanded", "fallback-state-expand-v1", "ground_solver", "states", "attempt"),
        _noncost("integrity.bytes_hashed", "integrity-byte-hashed-v1", "artifact_verifier", "bytes", "attempt", LaneEnum.DIAGNOSTIC),
        _op("io.mounted_bytes_peak", "mounted-byte-peak-v1", "sandbox_supervisor", "bytes", "decision_point", PEAK_MOUNTED_BYTES, ReducerEnum.MAX),
        _op("io.output_bytes", "io-output-byte-v1", "artifact_writer", "bytes", "attempt", OUTPUT_BYTES),
        _op("io.read_bytes", "io-read-byte-v1", "io_wrapper", "bytes", "attempt", READ_BYTES),
        _op("io.staged_bytes", "io-staged-byte-v1", "sandbox_stager", "bytes", "attempt", STAGED_BYTES),
        _op("local.causal_candidate_evaluations", "causal-candidate-eval-v1", "causal_search", "evaluations", "transaction"),
        _op("local.compiler_domain_assignments", "compiler-domain-assignment-v1", "trusted_compiler", "assignments", "transaction"),
        _op("local.compiler_expanded_forms", "compiler-expanded-form-v1", "trusted_compiler", "forms", "transaction"),
        _op("local.compiler_input_records", "compiler-input-record-v1", "trusted_compiler", "records", "transaction"),
        _op("local.materialization_ground_steps", "ground-transition-call-v1", "slice_materializer", "calls", "transaction", KERNEL_TRANSITION_CALLS),
        _op("local.materialization_outcome_rows", "positive-outcome-row-v1", "slice_materializer", "rows", "transaction"),
        _op("local.postaudit_ground_steps", "ground-transition-call-v1", "post_auditor", "calls", "transaction", KERNEL_TRANSITION_CALLS),
        _op("local.postaudit_outcome_rows", "positive-outcome-row-v1", "post_auditor", "rows", "transaction"),
        _op("local.solver_affine_term_evaluations", "solver-affine-term-eval-v1", "isolated_solver", "terms", "transaction"),
        _op("local.solver_dominance_comparisons", "solver-dominance-comparison-v1", "isolated_solver", "comparisons", "transaction"),
        _op("local.solver_frontier_points", "solver-frontier-point-v1", "isolated_solver", "points_generated", "transaction"),
        _op("local.solver_policy_assignments", "solver-policy-assignment-v1", "isolated_solver", "assignments", "transaction"),
        _op("local.solver_subset_evaluations", "solver-subset-eval-v1", "isolated_solver", "evaluations", "transaction"),
        _op("memory.working_bytes_peak", "working-byte-peak-v1", "worker_supervisor_or_frozen_cap", "bytes", "transaction_or_attempt", PEAK_WORKING_BYTES, ReducerEnum.MAX),
        _noncost("model.serialized_bytes", "model-serialized-byte-v1", "artifact_writer", "bytes", "build_epoch"),
        _reconciled("process.exit_failures", "process-exit-failure-v1", "process_supervisor", "exits", "attempt"),
        _reconciled("process.exit_successes", "process-exit-success-v1", "process_supervisor", "exits", "attempt"),
        _op("process.launches", "process-launch-v1", "process_supervisor", "launches", "attempt", PROCESS_LAUNCHES),
        _op("rebuild.ground_steps", "ground-transition-call-v1", "rapm_builder", "calls", "build_epoch", KERNEL_TRANSITION_CALLS),
        _op("rebuild.outcome_rows", "positive-outcome-row-v1", "rapm_builder", "rows", "build_epoch"),
        _op("rebuild.partition_candidate_evaluations", "partition-candidate-eval-v1", "builder", "evaluations", "build_epoch"),
        _reconciled("route.attempts", "route-attempt-count-v1", "route_supervisor", "attempts", "attempt"),
        _reconciled("route.failures", "route-failure-count-v1", "route_supervisor", "failures", "attempt"),
        _reconciled("route.successes", "route-success-count-v1", "route_supervisor", "successes", "attempt"),
        _reconciled("solver.attempts", "solver-attempt-count-v1", "solver_supervisor", "attempts", "transaction_or_attempt"),
        _reconciled("solver.failures", "solver-failure-count-v1", "solver_supervisor", "failures", "transaction_or_attempt"),
        _reconciled("solver.successes", "solver-success-count-v1", "solver_supervisor", "successes", "transaction_or_attempt"),
    )
    return CounterRegistryV1(
        COUNTER_REGISTRY_KEY,
        SCHEMA_VERSION,
        tuple(sorted(leaves, key=lambda leaf: leaf.path)),
    )


def official_shared_axes_v1() -> tuple[ComparisonAxisV1, ...]:
    axes = (
        ComparisonAxisV1(KERNEL_TRANSITION_CALLS, "calls", ReducerEnum.SUM, "Authoritative ground-kernel transition evaluations."),
        ComparisonAxisV1(NONKERNEL_COMPUTE_EVENTS, "registered_events", ReducerEnum.SUM, "Registered non-kernel, non-process compute events."),
        ComparisonAxisV1(OUTPUT_BYTES, "bytes", ReducerEnum.SUM, "New result, trace, certificate, counter, and manifest bytes."),
        ComparisonAxisV1(PEAK_MOUNTED_BYTES, "bytes", ReducerEnum.MAX, "Peak simultaneously mounted payload within a decision point."),
        ComparisonAxisV1(PEAK_WORKING_BYTES, "bytes", ReducerEnum.MAX, "Verified peak or frozen working-set capacity."),
        ComparisonAxisV1(PROCESS_LAUNCHES, "launches", ReducerEnum.SUM, "New OS or isolated worker process launches."),
        ComparisonAxisV1(READ_BYTES, "bytes", ReducerEnum.SUM, "Bytes read from pre-existing artifacts, models, queries, or capabilities."),
        ComparisonAxisV1(STAGED_BYTES, "bytes", ReducerEnum.SUM, "Bytes copied or bound into the execution sandbox."),
    )
    return tuple(sorted(axes, key=lambda axis: axis.name))


def official_comparison_profile_v1(
    registry: CounterRegistryV1 | None = None,
) -> ComparisonProfileV1:
    registry = registry or official_counter_registry_v1()
    registry.validate_official_catalogue()
    axes = official_shared_axes_v1()
    by_axis = {axis.name: axis for axis in axes}
    terms = tuple(
        ProjectionTermV1(
            leaf.path,
            leaf.comparison_axis or "",
            1,
            leaf.lane,
            leaf.semantics_id,
            by_axis[leaf.comparison_axis or ""].reducer,
        )
        for leaf in registry.operational_leaves
    )
    profile = ComparisonProfileV1(
        COMPARISON_PROFILE_KEY,
        SCHEMA_VERSION,
        registry.registry_id,
        axes,
        terms,
    )
    profile.validate(registry)
    return profile


def explicit_records_v1(
    registry: CounterRegistryV1,
    values: Mapping[str, int],
    *,
    recorder_id: str,
    include_optional: bool = False,
) -> tuple[CounterRecordV1, ...]:
    """Build records without ever treating an omitted required leaf as zero.

    This convenience function intentionally requires callers to supply every
    required value.  Tests and runners that want native zeroes must write
    ``path: 0`` explicitly.
    """

    unknown = sorted(set(values) - set(registry.by_path))
    if unknown:
        raise AccountingV1Error(f"unknown counter paths: {unknown!r}")
    expected = set(registry.required_paths)
    missing = sorted(expected - set(values))
    if missing:
        raise AccountingV1Error(f"missing explicit required values: {missing!r}")
    selected = set(expected)
    if include_optional:
        selected |= set(values)
    elif set(values) - expected:
        raise AccountingV1Error(
            "optional records were supplied without include_optional=True"
        )
    return tuple(
        CounterRecordV1.observe(
            registry, path, values[path], recorder_id=recorder_id
        )
        for path in sorted(selected)
    )


__all__ = [
    "AccountingV1Error",
    "COMPARISON_PROFILE_KEY",
    "COUNTER_REGISTRY_KEY",
    "ComparisonAxisV1",
    "ComparisonProfileV1",
    "ComparisonVectorV1",
    "CounterRecordV1",
    "CounterRegistryV1",
    "CounterSemanticsV1",
    "KERNEL_TRANSITION_CALLS",
    "LaneEnum",
    "NONKERNEL_COMPUTE_EVENTS",
    "NativeZeroAttestationV1",
    "OUTPUT_BYTES",
    "PEAK_MOUNTED_BYTES",
    "PEAK_WORKING_BYTES",
    "PROCESS_LAUNCHES",
    "ProjectionTermV1",
    "READ_BYTES",
    "ReconciliationProofV1",
    "ReducerEnum",
    "RouteKindEnum",
    "SCHEMA_VERSION",
    "SHARED_AXES",
    "STAGED_BYTES",
    "WorkVectorV1",
    "derive_comparison_vector_v1",
    "explicit_records_v1",
    "official_comparison_profile_v1",
    "official_counter_registry_v1",
    "official_shared_axes_v1",
]
