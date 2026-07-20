"""Shared-axis route-bound candidates for Phase 3E preconstruction.

Accounting ``WorkVector`` leaves retain route-specific provenance and therefore
are not a valid comparison basis by themselves.  This module keeps a separate,
weight-agnostic candidate vector over shared resource axes.  Each upper bound is
recomputed from preregistered cardinalities and integer formula terms; it remains
non-official until the Phase-3E comparison profile is normatively frozen.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from acfqp.artifacts import object_id
from acfqp.work_accounting import (
    EQUAL,
    INCOMPARABLE,
    LEFT_DOMINATES,
    RIGHT_DOMINATES,
)


LOCAL_ATTEMPT = "LOCAL_ATTEMPT"
DIRECT_FALLBACK = "DIRECT_FALLBACK"
PROFILE_STATUS = "UNRESOLVED_COMPARISON_PROFILE_CANDIDATE"

_ROUTES = frozenset({LOCAL_ATTEMPT, DIRECT_FALLBACK})
_PATH = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")


class ComparisonValidationError(ValueError):
    """A comparison profile, derivation, or vector is not exact and bound."""


def _identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ComparisonValidationError(f"{field} must be nonempty")
    return value


def _path(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or _PATH.fullmatch(value) is None:
        raise ComparisonValidationError(f"invalid {field} {value!r}")
    return value


def _integer(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ComparisonValidationError(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _route(value: Any) -> str:
    if value not in _ROUTES:
        raise ComparisonValidationError(f"unknown route candidate {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class ComparisonProfileCandidate:
    profile_key: str
    version: str
    axes: tuple[str, ...]
    official: bool = False

    def __post_init__(self) -> None:
        _identifier(self.profile_key, field="profile_key")
        _identifier(self.version, field="profile version")
        if not self.axes or tuple(sorted(self.axes)) != self.axes:
            raise ComparisonValidationError("comparison axes must be nonempty and sorted")
        if len(set(self.axes)) != len(self.axes):
            raise ComparisonValidationError("comparison profile repeats an axis")
        for axis in self.axes:
            _path(axis, field="comparison axis")
        if self.official:
            raise ComparisonValidationError("candidate comparison profile cannot be official")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_comparison_profile_candidate.v1",
            "profile_key": self.profile_key,
            "version": self.version,
            "axes": list(self.axes),
            "status": PROFILE_STATUS,
            "official": False,
        }

    @property
    def profile_id(self) -> str:
        return object_id(self._payload(), "route-comparison-profile")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "profile_id": self.profile_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ComparisonProfileCandidate":
        expected = {
            "schema",
            "profile_key",
            "version",
            "axes",
            "status",
            "official",
            "profile_id",
        }
        if set(document) != expected:
            raise ComparisonValidationError("comparison profile field set mismatch")
        if (
            document["schema"] != "acfqp.route_comparison_profile_candidate.v1"
            or document["status"] != PROFILE_STATUS
            or document["official"] is not False
        ):
            raise ComparisonValidationError("comparison profile metadata mismatch")
        axes = document["axes"]
        if not isinstance(axes, list):
            raise ComparisonValidationError("comparison axes must be a list")
        profile = cls(document["profile_key"], document["version"], tuple(axes))
        if document["profile_id"] != profile.profile_id:
            raise ComparisonValidationError("comparison profile content ID mismatch")
        return profile


@dataclass(frozen=True, slots=True)
class CardinalityEvidence:
    context_id: str
    route_candidate: str
    counts: tuple[tuple[str, int], ...]
    source_artifact_ids: tuple[str, ...]
    measured_before_execution: bool = True
    depends_on_actual_route_work: bool = False

    def __post_init__(self) -> None:
        _identifier(self.context_id, field="context_id")
        _route(self.route_candidate)
        if not self.counts or tuple(sorted(self.counts)) != self.counts:
            raise ComparisonValidationError("cardinality counts must be nonempty and sorted")
        if len(dict(self.counts)) != len(self.counts):
            raise ComparisonValidationError("cardinality evidence repeats an input")
        for name, value in self.counts:
            _path(name, field="cardinality input")
            _integer(value, field=name)
        if (
            not self.source_artifact_ids
            or tuple(sorted(self.source_artifact_ids)) != self.source_artifact_ids
            or len(set(self.source_artifact_ids)) != len(self.source_artifact_ids)
        ):
            raise ComparisonValidationError(
                "cardinality source artifact IDs must be nonempty, unique, and sorted"
            )
        for artifact_id in self.source_artifact_ids:
            _identifier(artifact_id, field="source artifact ID")
        if self.measured_before_execution is not True:
            raise ComparisonValidationError("cardinalities were not frozen pre-execution")
        if self.depends_on_actual_route_work is not False:
            raise ComparisonValidationError("cardinalities depend on selected-route work")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_cardinality_evidence_candidate.v1",
            "context_id": self.context_id,
            "route_candidate": self.route_candidate,
            "counts": [
                {"name": name, "value": value} for name, value in self.counts
            ],
            "source_artifact_ids": list(self.source_artifact_ids),
            "measured_before_execution": True,
            "depends_on_actual_route_work": False,
            "official": False,
        }

    @property
    def evidence_id(self) -> str:
        return object_id(self._payload(), "route-cardinality-evidence")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class AxisTerm:
    axis: str
    input_name: str
    multiplier: int

    def __post_init__(self) -> None:
        _path(self.axis, field="formula axis")
        _path(self.input_name, field="formula input")
        _integer(self.multiplier, field="formula multiplier")

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis": self.axis,
            "input_name": self.input_name,
            "multiplier": self.multiplier,
        }


@dataclass(frozen=True, slots=True)
class ComparisonFormulaCandidate:
    profile_id: str
    route_candidate: str
    formula_key: str
    terms: tuple[AxisTerm, ...]
    official: bool = False

    def __post_init__(self) -> None:
        _identifier(self.profile_id, field="profile_id")
        _route(self.route_candidate)
        _identifier(self.formula_key, field="formula_key")
        if not self.terms:
            raise ComparisonValidationError("comparison formula cannot be empty")
        key = lambda term: (term.axis, term.input_name, term.multiplier)
        if tuple(sorted(self.terms, key=key)) != self.terms:
            raise ComparisonValidationError("comparison formula terms must be sorted")
        if self.official:
            raise ComparisonValidationError("candidate formula cannot be official")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_comparison_formula_candidate.v1",
            "profile_id": self.profile_id,
            "route_candidate": self.route_candidate,
            "formula_key": self.formula_key,
            "terms": [term.to_dict() for term in self.terms],
            "official": False,
        }

    @property
    def formula_id(self) -> str:
        return object_id(self._payload(), "route-comparison-formula")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "formula_id": self.formula_id}


@dataclass(frozen=True, slots=True)
class ComparisonVector:
    profile_id: str
    context_id: str
    route_candidate: str
    values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        _identifier(self.profile_id, field="profile_id")
        _identifier(self.context_id, field="context_id")
        _route(self.route_candidate)
        if not self.values or tuple(sorted(self.values)) != self.values:
            raise ComparisonValidationError("comparison values must be nonempty and sorted")
        if len(dict(self.values)) != len(self.values):
            raise ComparisonValidationError("comparison vector repeats an axis")
        for axis, value in self.values:
            _path(axis, field="comparison axis")
            _integer(value, field=axis)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_comparison_vector_candidate.v1",
            "profile_id": self.profile_id,
            "context_id": self.context_id,
            "route_candidate": self.route_candidate,
            "values": [
                {"axis": axis, "value": value} for axis, value in self.values
            ],
            "official": False,
        }

    @property
    def vector_id(self) -> str:
        return object_id(self._payload(), "route-comparison-vector")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "vector_id": self.vector_id}


@dataclass(frozen=True, slots=True)
class RouteUpperBoundCandidate:
    context_id: str
    route_candidate: str
    profile_id: str
    cardinality_evidence_id: str
    formula_id: str
    vector: ComparisonVector

    def __post_init__(self) -> None:
        _identifier(self.context_id, field="context_id")
        _route(self.route_candidate)
        _identifier(self.profile_id, field="profile_id")
        _identifier(self.cardinality_evidence_id, field="cardinality_evidence_id")
        _identifier(self.formula_id, field="formula_id")
        if (
            self.vector.context_id != self.context_id
            or self.vector.route_candidate != self.route_candidate
            or self.vector.profile_id != self.profile_id
        ):
            raise ComparisonValidationError("upper-bound vector binding mismatch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_upper_bound_candidate.v1",
            "context_id": self.context_id,
            "route_candidate": self.route_candidate,
            "profile_id": self.profile_id,
            "cardinality_evidence_id": self.cardinality_evidence_id,
            "formula_id": self.formula_id,
            "comparison_vector": self.vector.to_dict(),
            "status": PROFILE_STATUS,
            "official": False,
        }

    @property
    def bound_id(self) -> str:
        return object_id(self._payload(), "route-upper-bound")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "bound_id": self.bound_id}


def derive_route_upper_bound(
    profile: ComparisonProfileCandidate,
    cardinality: CardinalityEvidence,
    formula: ComparisonFormulaCandidate,
) -> RouteUpperBoundCandidate:
    """Deterministically project declared cap inputs onto shared axes."""

    if formula.profile_id != profile.profile_id:
        raise ComparisonValidationError("formula uses a different profile")
    if formula.route_candidate != cardinality.route_candidate:
        raise ComparisonValidationError("formula and cardinality route differ")
    counts = dict(cardinality.counts)
    values = {axis: 0 for axis in profile.axes}
    used_axes: set[str] = set()
    for term in formula.terms:
        if term.axis not in values:
            raise ComparisonValidationError("formula names an unregistered axis")
        if term.input_name not in counts:
            raise ComparisonValidationError("formula names an absent cardinality input")
        values[term.axis] += counts[term.input_name] * term.multiplier
        used_axes.add(term.axis)
    if used_axes != set(profile.axes):
        raise ComparisonValidationError("formula does not derive every profile axis")
    vector = ComparisonVector(
        profile.profile_id,
        cardinality.context_id,
        cardinality.route_candidate,
        tuple(sorted(values.items())),
    )
    return RouteUpperBoundCandidate(
        cardinality.context_id,
        cardinality.route_candidate,
        profile.profile_id,
        cardinality.evidence_id,
        formula.formula_id,
        vector,
    )


def verify_route_upper_bound(
    bound: RouteUpperBoundCandidate,
    profile: ComparisonProfileCandidate,
    cardinality: CardinalityEvidence,
    formula: ComparisonFormulaCandidate,
) -> None:
    recomputed = derive_route_upper_bound(profile, cardinality, formula)
    if bound != recomputed or bound.bound_id != recomputed.bound_id:
        raise ComparisonValidationError("route upper bound does not recompute exactly")


def compare_route_upper_bounds(
    left: RouteUpperBoundCandidate, right: RouteUpperBoundCandidate
) -> str:
    if left.context_id != right.context_id or left.profile_id != right.profile_id:
        raise ComparisonValidationError("route bounds bind different contexts/profiles")
    if left.route_candidate == right.route_candidate:
        raise ComparisonValidationError("route comparison requires distinct candidates")
    left_values = dict(left.vector.values)
    right_values = dict(right.vector.values)
    if set(left_values) != set(right_values):
        raise ComparisonValidationError("route bounds use different shared axes")
    left_le = all(left_values[axis] <= right_values[axis] for axis in left_values)
    right_le = all(right_values[axis] <= left_values[axis] for axis in left_values)
    if left_le and right_le:
        return EQUAL
    if left_le:
        return LEFT_DOMINATES
    if right_le:
        return RIGHT_DOMINATES
    return INCOMPARABLE


__all__ = [
    "AxisTerm",
    "CardinalityEvidence",
    "ComparisonFormulaCandidate",
    "ComparisonProfileCandidate",
    "ComparisonValidationError",
    "ComparisonVector",
    "DIRECT_FALLBACK",
    "LOCAL_ATTEMPT",
    "PROFILE_STATUS",
    "RouteUpperBoundCandidate",
    "compare_route_upper_bounds",
    "derive_route_upper_bound",
    "verify_route_upper_bound",
]
