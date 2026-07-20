"""Exact, weight-agnostic work-accounting primitives for Phase 3E.

The registry owns canonical observations and compatibility aliases.  Every
canonical leaf is required: missing operational work is never inferred as zero.
The optional ``unit_work_v1`` projection is diagnostic and does not freeze an
official scalar cost functional.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re
from typing import Any, Iterable, Mapping

from acfqp.artifacts import object_id


CHARGED_OP = "charged_op"
CHARGED_BYTE = "charged_byte"
DIAGNOSTIC_CARDINALITY = "diagnostic_cardinality"
DERIVED_ALIAS = "derived_alias"

OPERATIONAL = "operational"
EVALUATION_ONLY = "evaluation_only"
PROVENANCE_ONLY = "provenance_only"

OPERATION = "operation"
BYTE = "byte"
COUNT = "count"

LEFT_DOMINATES = "LEFT_COMPONENTWISE_DOMINATES"
RIGHT_DOMINATES = "RIGHT_COMPONENTWISE_DOMINATES"
EQUAL = "COMPONENTWISE_EQUAL"
INCOMPARABLE = "COMPONENTWISE_INCOMPARABLE"

_KINDS = frozenset(
    {CHARGED_OP, CHARGED_BYTE, DIAGNOSTIC_CARDINALITY, DERIVED_ALIAS}
)
_SCOPES = frozenset({OPERATIONAL, EVALUATION_ONLY, PROVENANCE_ONLY})
_UNITS = frozenset({OPERATION, BYTE, COUNT})
_PATH = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")


class CounterValidationError(ValueError):
    """A registry, record, alias, or vector is not exact and complete."""


def _nonnegative_integer(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CounterValidationError(f"{field} must be a nonnegative exact integer")
    return value


def _validate_path(path: Any, *, label: str) -> str:
    if not isinstance(path, str) or _PATH.fullmatch(path) is None:
        raise CounterValidationError(f"invalid {label} {path!r}")
    return path


@dataclass(frozen=True, slots=True)
class CounterLeaf:
    """One uniquely owned leaf in a counter registry."""

    path: str
    kind: str
    unit: str
    scope: str
    owner: str
    required: bool = True
    alias_of: str | None = None

    def __post_init__(self) -> None:
        _validate_path(self.path, label="canonical counter path")
        if self.kind not in _KINDS:
            raise CounterValidationError(f"unknown counter kind {self.kind!r}")
        if self.unit not in _UNITS:
            raise CounterValidationError(f"unknown counter unit {self.unit!r}")
        if self.scope not in _SCOPES:
            raise CounterValidationError(f"unknown counter scope {self.scope!r}")
        if not isinstance(self.owner, str) or not self.owner:
            raise CounterValidationError("counter owner must be nonempty")
        if not isinstance(self.required, bool):
            raise CounterValidationError("counter required flag must be boolean")
        if self.kind == DERIVED_ALIAS:
            _validate_path(self.alias_of, label="alias target")
            if self.alias_of == self.path:
                raise CounterValidationError("a counter alias cannot target itself")
        elif self.alias_of is not None:
            raise CounterValidationError("only derived_alias leaves may name alias_of")
        elif not self.required:
            raise CounterValidationError(
                "canonical counter leaves must be explicitly required and observed"
            )
        if self.kind == CHARGED_OP and self.unit != OPERATION:
            raise CounterValidationError("charged_op leaves must use operation units")
        if self.kind == CHARGED_BYTE and self.unit != BYTE:
            raise CounterValidationError("charged_byte leaves must use byte units")
        if self.kind == DIAGNOSTIC_CARDINALITY and self.unit != COUNT:
            raise CounterValidationError(
                "diagnostic_cardinality leaves must use count units"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "unit": self.unit,
            "scope": self.scope,
            "owner": self.owner,
            "required": self.required,
            "alias_of": self.alias_of,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "CounterLeaf":
        expected = {
            "path",
            "kind",
            "unit",
            "scope",
            "owner",
            "required",
            "alias_of",
        }
        if set(document) != expected:
            raise CounterValidationError("counter leaf field set mismatch")
        return cls(**{field: document[field] for field in expected})


@dataclass(frozen=True, slots=True)
class CounterRegistry:
    """Canonical names, ownership, units, scope, and alias rules."""

    registry_key: str
    version: str
    leaves: tuple[CounterLeaf, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.registry_key, str) or not self.registry_key:
            raise CounterValidationError("registry_key must be nonempty")
        if not isinstance(self.version, str) or not self.version:
            raise CounterValidationError("registry version must be nonempty")
        if not self.leaves:
            raise CounterValidationError("counter registry cannot be empty")
        if tuple(sorted(self.leaves, key=lambda leaf: leaf.path)) != self.leaves:
            raise CounterValidationError("counter leaves must be path-sorted")
        by_path = {leaf.path: leaf for leaf in self.leaves}
        if len(by_path) != len(self.leaves):
            raise CounterValidationError("counter registry repeats a leaf path")
        for leaf in self.leaves:
            if leaf.kind != DERIVED_ALIAS:
                continue
            target = by_path.get(leaf.alias_of or "")
            if target is None or target.kind == DERIVED_ALIAS:
                raise CounterValidationError(
                    f"alias target is absent or noncanonical: {leaf.path}"
                )
            if leaf.unit != target.unit or leaf.scope != target.scope:
                raise CounterValidationError(
                    f"alias unit/scope differs from target: {leaf.path}"
                )

    @property
    def registry_id(self) -> str:
        return object_id(self._payload(), "counter-registry")

    @property
    def by_path(self) -> dict[str, CounterLeaf]:
        return {leaf.path: leaf for leaf in self.leaves}

    @property
    def canonical_leaves(self) -> tuple[CounterLeaf, ...]:
        return tuple(leaf for leaf in self.leaves if leaf.kind != DERIVED_ALIAS)

    @property
    def operational_cost_paths(self) -> tuple[str, ...]:
        return tuple(
            leaf.path
            for leaf in self.canonical_leaves
            if leaf.scope == OPERATIONAL and leaf.kind in {CHARGED_OP, CHARGED_BYTE}
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.counter_registry.v1",
            "registry_key": self.registry_key,
            "version": self.version,
            "leaves": [leaf.to_dict() for leaf in self.leaves],
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "registry_id": self.registry_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "CounterRegistry":
        expected = {"schema", "registry_key", "version", "leaves", "registry_id"}
        if set(document) != expected:
            raise CounterValidationError("counter registry field set mismatch")
        if document["schema"] != "acfqp.counter_registry.v1":
            raise CounterValidationError("counter registry schema mismatch")
        rows = document["leaves"]
        if not isinstance(rows, list):
            raise CounterValidationError("counter registry leaves must be a list")
        registry = cls(
            document["registry_key"],
            document["version"],
            tuple(CounterLeaf.from_dict(row) for row in rows),
        )
        if document["registry_id"] != registry.registry_id:
            raise CounterValidationError("counter registry content ID mismatch")
        return registry

    def validate_vector(self, vector: "WorkVector") -> None:
        if vector.registry_id != self.registry_id:
            raise CounterValidationError("work vector uses a different registry")
        expected = {leaf.path for leaf in self.canonical_leaves}
        observed = {path for path, _ in vector.values}
        if observed != expected:
            raise CounterValidationError(
                "work vector component set mismatch; "
                f"missing={sorted(expected - observed)!r}, "
                f"extra={sorted(observed - expected)!r}"
            )

    def reconcile(self, record: "CounterRecord") -> "WorkVector":
        if record.registry_id != self.registry_id:
            raise CounterValidationError("counter record uses a different registry")
        values = dict(record.values)
        known = self.by_path
        unknown = sorted(set(values) - set(known))
        if unknown:
            raise CounterValidationError(f"unknown counter leaves: {unknown!r}")
        missing = sorted(
            leaf.path for leaf in self.leaves if leaf.required and leaf.path not in values
        )
        if missing:
            raise CounterValidationError(f"missing required counter leaves: {missing!r}")
        for leaf in self.leaves:
            if leaf.kind != DERIVED_ALIAS or leaf.path not in values:
                continue
            target = leaf.alias_of or ""
            if target not in values:
                raise CounterValidationError(
                    f"counter alias is present but canonical target is missing: {leaf.path}"
                )
            if values[leaf.path] != values[target]:
                raise CounterValidationError(
                    f"counter alias differs from canonical owner: {leaf.path}"
                )
        vector = WorkVector(
            self.registry_id,
            record.subject_id,
            tuple((leaf.path, values[leaf.path]) for leaf in self.canonical_leaves),
        )
        self.validate_vector(vector)
        return vector


@dataclass(frozen=True, slots=True)
class CounterRecord:
    """One explicit observation set; no invocation is inferred."""

    registry_id: str
    subject_id: str
    values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.registry_id, str) or not self.registry_id:
            raise CounterValidationError("counter record registry_id must be nonempty")
        if not isinstance(self.subject_id, str) or not self.subject_id:
            raise CounterValidationError("counter record subject_id must be nonempty")
        if tuple(sorted(self.values)) != self.values:
            raise CounterValidationError("counter record values must be path-sorted")
        if len(dict(self.values)) != len(self.values):
            raise CounterValidationError("counter record repeats a leaf path")
        for path, value in self.values:
            _validate_path(path, label="observed counter path")
            _nonnegative_integer(value, field=path)

    @classmethod
    def create(
        cls, registry_id: str, subject_id: str, values: Mapping[str, int]
    ) -> "CounterRecord":
        return cls(registry_id, subject_id, tuple(sorted(values.items())))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.counter_record.v1",
            "registry_id": self.registry_id,
            "subject_id": self.subject_id,
            "values": [{"path": path, "value": value} for path, value in self.values],
        }

    @property
    def record_id(self) -> str:
        return object_id(self._payload(), "counter-record")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "record_id": self.record_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "CounterRecord":
        expected = {"schema", "registry_id", "subject_id", "values", "record_id"}
        if set(document) != expected:
            raise CounterValidationError("counter record field set mismatch")
        if document["schema"] != "acfqp.counter_record.v1":
            raise CounterValidationError("counter record schema mismatch")
        rows = document["values"]
        if not isinstance(rows, list):
            raise CounterValidationError("counter record values must be a list")
        values: list[tuple[str, int]] = []
        for row in rows:
            if not isinstance(row, Mapping) or set(row) != {"path", "value"}:
                raise CounterValidationError("counter value row field set mismatch")
            values.append((row["path"], row["value"]))
        record = cls(document["registry_id"], document["subject_id"], tuple(values))
        if document["record_id"] != record.record_id:
            raise CounterValidationError("counter record content ID mismatch")
        return record


@dataclass(frozen=True, slots=True)
class WorkVector:
    """Exact nonnegative canonical counter vector for one subject."""

    registry_id: str
    subject_id: str
    values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.registry_id, str) or not self.registry_id:
            raise CounterValidationError("work vector registry_id must be nonempty")
        if not isinstance(self.subject_id, str) or not self.subject_id:
            raise CounterValidationError("work vector subject_id must be nonempty")
        if tuple(sorted(self.values)) != self.values:
            raise CounterValidationError("work vector values must be path-sorted")
        if len(dict(self.values)) != len(self.values):
            raise CounterValidationError("work vector repeats a component")
        for path, value in self.values:
            _validate_path(path, label="work-vector path")
            _nonnegative_integer(value, field=path)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.work_vector.v1",
            "registry_id": self.registry_id,
            "subject_id": self.subject_id,
            "values": [{"path": path, "value": value} for path, value in self.values],
        }

    @property
    def vector_id(self) -> str:
        return object_id(self._payload(), "work-vector")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "vector_id": self.vector_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "WorkVector":
        expected = {"schema", "registry_id", "subject_id", "values", "vector_id"}
        if set(document) != expected:
            raise CounterValidationError("work vector field set mismatch")
        if document["schema"] != "acfqp.work_vector.v1":
            raise CounterValidationError("work vector schema mismatch")
        rows = document["values"]
        if not isinstance(rows, list):
            raise CounterValidationError("work vector values must be a list")
        values: list[tuple[str, int]] = []
        for row in rows:
            if not isinstance(row, Mapping) or set(row) != {"path", "value"}:
                raise CounterValidationError("work-vector value row field set mismatch")
            values.append((row["path"], row["value"]))
        vector = cls(document["registry_id"], document["subject_id"], tuple(values))
        if document["vector_id"] != vector.vector_id:
            raise CounterValidationError("work vector content ID mismatch")
        return vector

    def value(self, path: str) -> int:
        try:
            return dict(self.values)[path]
        except KeyError as error:
            raise CounterValidationError(f"work vector has no component {path!r}") from error

    def add(self, other: "WorkVector", *, subject_id: str) -> "WorkVector":
        if self.registry_id != other.registry_id:
            raise CounterValidationError("cannot add vectors from different registries")
        left = dict(self.values)
        right = dict(other.values)
        if set(left) != set(right):
            raise CounterValidationError("cannot add vectors with different components")
        return WorkVector(
            self.registry_id,
            subject_id,
            tuple((path, left[path] + right[path]) for path in sorted(left)),
        )


def diagnostic_unit_work_v1(vector: WorkVector, registry: CounterRegistry) -> Fraction:
    """Return the nonnormative ``ops + bytes/4096`` projection."""

    registry.validate_vector(vector)
    values = dict(vector.values)
    operations = sum(
        values[leaf.path]
        for leaf in registry.canonical_leaves
        if leaf.scope == OPERATIONAL and leaf.kind == CHARGED_OP
    )
    byte_count = sum(
        values[leaf.path]
        for leaf in registry.canonical_leaves
        if leaf.scope == OPERATIONAL and leaf.kind == CHARGED_BYTE
    )
    return Fraction(operations) + Fraction(byte_count, 4096)


def componentwise_cost_relation(
    left: WorkVector, right: WorkVector, registry: CounterRegistry
) -> str:
    """Compare lower-is-better operational charged components exactly."""

    registry.validate_vector(left)
    registry.validate_vector(right)
    left_values = dict(left.values)
    right_values = dict(right.values)
    paths = registry.operational_cost_paths
    if not paths:
        raise CounterValidationError("registry has no operational cost components")
    left_le = all(left_values[path] <= right_values[path] for path in paths)
    right_le = all(right_values[path] <= left_values[path] for path in paths)
    if left_le and right_le:
        return EQUAL
    if left_le:
        return LEFT_DOMINATES
    if right_le:
        return RIGHT_DOMINATES
    return INCOMPARABLE


def sum_work_vectors(
    vectors: Iterable[WorkVector], *, subject_id: str
) -> WorkVector:
    ordered = tuple(vectors)
    if not ordered:
        raise CounterValidationError("cannot sum an empty work-vector collection")
    result = ordered[0]
    for vector in ordered[1:]:
        result = result.add(vector, subject_id=subject_id)
    if len(ordered) == 1 and result.subject_id != subject_id:
        result = WorkVector(result.registry_id, subject_id, result.values)
    return result


__all__ = [
    "BYTE",
    "CHARGED_BYTE",
    "CHARGED_OP",
    "COUNT",
    "CounterLeaf",
    "CounterRecord",
    "CounterRegistry",
    "CounterValidationError",
    "DERIVED_ALIAS",
    "DIAGNOSTIC_CARDINALITY",
    "EQUAL",
    "EVALUATION_ONLY",
    "INCOMPARABLE",
    "LEFT_DOMINATES",
    "OPERATION",
    "OPERATIONAL",
    "PROVENANCE_ONLY",
    "RIGHT_DOMINATES",
    "WorkVector",
    "componentwise_cost_relation",
    "diagnostic_unit_work_v1",
    "sum_work_vectors",
]
