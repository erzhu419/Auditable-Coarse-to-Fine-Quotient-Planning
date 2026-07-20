"""Scalar-free FQ12 workload ordering and prefix-frontier mechanics.

This module deliberately does not define a scalar cost, a break-even index, or
a single scalar "worst order".  It enumerates the finite registered order set,
derives reducer-aware vector prefix totals, and reports every componentwise
Pareto-maximal (larger-is-worse) prefix vector together with all witness orders.

Additive axes are accumulated with ``sum``.  Peak-capacity axes are accumulated
with ``max``.  Exact enumeration is fail-closed: if the number of permutations
exceeds the preregistered finite cap, no partial frontier artifact is emitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations
import math
from typing import Any, Mapping, Sequence

from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    ComparisonVectorV1,
    CounterRegistryV1,
    ReducerEnum,
    SHARED_AXES,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProfileV1,
    ActualProjectionProofV1,
    OccurrenceWorkSumV1,
    verify_occurrence_work_sum_v1,
)
from acfqp.phase3e_ids import (
    WORKLOAD_VECTOR_ANALYSIS_DOMAIN,
    WORKLOAD_VECTOR_PREFIX_DOMAIN,
    WORKLOAD_VECTOR_SPEC_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    RouteDecisionContextV1,
    TransactionV1,
)


SCHEMA_VERSION = "1.0.0"
SCALAR_GATE_NOT_RUN = "NOT_RUN"
VECTOR_ONLY_COMPLETE_ENUMERATION = "VECTOR_ONLY_COMPLETE_ENUMERATION"
MAX_EXPLICIT_PERMUTATIONS = 100_000


_WORKLOAD_ANALYSIS_AUTHORITY = object()


class WorkloadVectorV1Error(ValueError):
    """A scalar-free workload artifact is incomplete or semantically invalid."""


class PermutationCapExceededError(WorkloadVectorV1Error):
    """Exact order enumeration cannot run within the preregistered cap."""

    def __init__(self, *, required: int, cap: int) -> None:
        super().__init__(
            f"exact order enumeration requires {required} permutations, cap is {cap}"
        )
        self.required_permutations = required
        self.permutation_cap = cap


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise WorkloadVectorV1Error(
            f"{field} must be a full Phase-3E content ID"
        ) from error


def _positive(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise WorkloadVectorV1Error(f"{field} must be a positive exact integer")
    return value


def _nonnegative(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise WorkloadVectorV1Error(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _fields(
    document: Mapping[str, Any], expected: set[str], context: str
) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise WorkloadVectorV1Error(str(error)) from error


def _validate_scalar_lock(
    official_scalar_cost: Any,
    official_N_break_even: Any,
    scalar_gate_status: Any,
) -> None:
    if official_scalar_cost is not None:
        raise WorkloadVectorV1Error(
            "official_scalar_cost must be null; zero or a legacy scalar is forbidden"
        )
    if official_N_break_even is not None:
        raise WorkloadVectorV1Error(
            "official_N_break_even must be null; zero or a crossing claim is forbidden"
        )
    if scalar_gate_status != SCALAR_GATE_NOT_RUN:
        raise WorkloadVectorV1Error("scalar_gate_status must remain NOT_RUN")


def _axis_values(values: Sequence[tuple[str, int]], context: str) -> tuple[tuple[str, int], ...]:
    result = tuple(values)
    if (
        tuple(sorted(result)) != result
        or len(dict(result)) != len(result)
        or tuple(axis for axis, _ in result) != SHARED_AXES
    ):
        raise WorkloadVectorV1Error(
            f"{context} must contain the exact sorted shared-axis set"
        )
    for axis, value in result:
        _nonnegative(value, f"{context}.{axis}")
    return result


def _parse_axis_rows(rows: Any, context: str) -> tuple[tuple[str, int], ...]:
    if type(rows) is not list:
        raise WorkloadVectorV1Error(f"{context} must be a list")
    values: list[tuple[str, int]] = []
    for row in rows:
        _fields(row, {"axis", "value"}, f"{context} row")
        values.append((row["axis"], row["value"]))
    return _axis_values(values, context)


def _axis_rows(values: Sequence[tuple[str, int]]) -> list[dict[str, Any]]:
    return [{"axis": axis, "value": value} for axis, value in values]


@dataclass(frozen=True, slots=True)
class OccurrenceVectorRefV1:
    logical_occurrence_id: str
    occurrence_work_sum_id: str

    def __post_init__(self) -> None:
        _cid(self.logical_occurrence_id, "logical_occurrence_id")
        _cid(self.occurrence_work_sum_id, "occurrence_work_sum_id")

    def to_dict(self) -> dict[str, str]:
        return {
            "logical_occurrence_id": self.logical_occurrence_id,
            "occurrence_work_sum_id": self.occurrence_work_sum_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "OccurrenceVectorRefV1":
        _fields(
            document,
            {"logical_occurrence_id", "occurrence_work_sum_id"},
            "occurrence-vector reference",
        )
        return cls(
            document["logical_occurrence_id"], document["occurrence_work_sum_id"]
        )


ActualTripleV1 = tuple[
    WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
]


@dataclass(frozen=True, slots=True)
class ReplayableOccurrenceAccountingV1:
    """All native evidence needed to replay one logical-occurrence vector.

    ``OccurrenceWorkSumV1`` is not accepted as a self-signed total.  The three
    native WorkVectors, exact actual-projection proofs, and route identity chain
    remain attached so workload analysis can independently reproduce it.
    """

    occurrence_sum: OccurrenceWorkSumV1
    route_context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    local_transaction: TransactionV1
    common_prefix: ActualTripleV1
    local_attempt: ActualTripleV1
    fallback: ActualTripleV1

    @property
    def logical_occurrence_id(self) -> str:
        return self.occurrence_sum.logical_occurrence_id

    @property
    def occurrence_work_sum_id(self) -> str:
        return self.occurrence_sum.logical_occurrence_work_sum_id

    def verify(
        self,
        registry: CounterRegistryV1,
        comparison_profile: ComparisonProfileV1,
        actual_profile: ActualProjectionProfileV1,
    ) -> tuple[tuple[str, int], ...]:
        verify_occurrence_work_sum_v1(
            self.occurrence_sum,
            logical_occurrence_id=self.logical_occurrence_id,
            route_context=self.route_context,
            decision_point=self.decision_point,
            local_transaction=self.local_transaction,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
            common_prefix=self.common_prefix,
            local_attempt=self.local_attempt,
            fallback=self.fallback,
        )
        return self.occurrence_sum.aggregate_values


@dataclass(frozen=True, slots=True)
class WorkloadVectorSpecV1:
    comparison_profile_id: str
    occurrence_vectors: tuple[OccurrenceVectorRefV1, ...]
    permutation_cap: int
    official_scalar_cost: None = None
    official_N_break_even: None = None
    scalar_gate_status: str = SCALAR_GATE_NOT_RUN

    def __post_init__(self) -> None:
        _cid(self.comparison_profile_id, "comparison_profile_id")
        if not self.occurrence_vectors:
            raise WorkloadVectorV1Error("workload must register at least one occurrence")
        occurrence_ids = tuple(
            ref.logical_occurrence_id for ref in self.occurrence_vectors
        )
        vector_ids = tuple(ref.occurrence_work_sum_id for ref in self.occurrence_vectors)
        if len(set(occurrence_ids)) != len(occurrence_ids):
            raise WorkloadVectorV1Error("workload repeats a logical occurrence")
        if len(set(vector_ids)) != len(vector_ids):
            raise WorkloadVectorV1Error("workload repeats an occurrence work sum")
        _positive(self.permutation_cap, "permutation_cap")
        if self.permutation_cap > MAX_EXPLICIT_PERMUTATIONS:
            raise WorkloadVectorV1Error(
                f"permutation_cap exceeds implementation safety limit "
                f"{MAX_EXPLICIT_PERMUTATIONS}"
            )
        _validate_scalar_lock(
            self.official_scalar_cost,
            self.official_N_break_even,
            self.scalar_gate_status,
        )

    @property
    def ordered_logical_occurrence_ids(self) -> tuple[str, ...]:
        return tuple(ref.logical_occurrence_id for ref in self.occurrence_vectors)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.workload_vector_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "comparison_profile_id": self.comparison_profile_id,
            "occurrence_vectors": [
                ref.to_dict() for ref in self.occurrence_vectors
            ],
            "permutation_cap": self.permutation_cap,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "scalar_gate_status": self.scalar_gate_status,
        }

    @property
    def workload_vector_spec_id(self) -> str:
        return content_id(WORKLOAD_VECTOR_SPEC_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "workload_vector_spec_id": self.workload_vector_spec_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "WorkloadVectorSpecV1":
        expected = {
            "schema",
            "schema_version",
            "comparison_profile_id",
            "occurrence_vectors",
            "permutation_cap",
            "official_scalar_cost",
            "official_N_break_even",
            "scalar_gate_status",
            "workload_vector_spec_id",
        }
        _fields(document, expected, "workload vector spec")
        if (
            document["schema"] != "acfqp.workload_vector_spec.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["occurrence_vectors"]) is not list
        ):
            raise WorkloadVectorV1Error("workload vector spec schema mismatch")
        result = cls(
            document["comparison_profile_id"],
            tuple(
                OccurrenceVectorRefV1.from_dict(row)
                for row in document["occurrence_vectors"]
            ),
            document["permutation_cap"],
            document["official_scalar_cost"],
            document["official_N_break_even"],
            document["scalar_gate_status"],
        )
        if document["workload_vector_spec_id"] != result.workload_vector_spec_id:
            raise WorkloadVectorV1Error("workload vector spec content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class VectorPrefixTotalV1:
    workload_vector_spec_id: str
    comparison_profile_id: str
    full_order: tuple[str, ...]
    prefix_length: int
    prefix_occurrence_ids: tuple[str, ...]
    values: tuple[tuple[str, int], ...]
    official_scalar_cost: None = None
    official_N_break_even: None = None
    scalar_gate_status: str = SCALAR_GATE_NOT_RUN

    def __post_init__(self) -> None:
        _cid(self.workload_vector_spec_id, "workload_vector_spec_id")
        _cid(self.comparison_profile_id, "comparison_profile_id")
        if not self.full_order or len(set(self.full_order)) != len(self.full_order):
            raise WorkloadVectorV1Error("prefix full order must be nonempty and unique")
        for occurrence_id in self.full_order:
            _cid(occurrence_id, "full_order occurrence ID")
        _positive(self.prefix_length, "prefix_length")
        if self.prefix_length > len(self.full_order):
            raise WorkloadVectorV1Error("prefix length exceeds full order")
        if self.prefix_occurrence_ids != self.full_order[: self.prefix_length]:
            raise WorkloadVectorV1Error(
                "prefix occurrence IDs are not the declared order prefix"
            )
        object.__setattr__(
            self, "values", _axis_values(self.values, "vector prefix total")
        )
        _validate_scalar_lock(
            self.official_scalar_cost,
            self.official_N_break_even,
            self.scalar_gate_status,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.workload_vector_prefix.v1",
            "schema_version": SCHEMA_VERSION,
            "workload_vector_spec_id": self.workload_vector_spec_id,
            "comparison_profile_id": self.comparison_profile_id,
            "full_order": list(self.full_order),
            "prefix_length": self.prefix_length,
            "prefix_occurrence_ids": list(self.prefix_occurrence_ids),
            "values": _axis_rows(self.values),
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "scalar_gate_status": self.scalar_gate_status,
        }

    @property
    def workload_vector_prefix_id(self) -> str:
        return content_id(WORKLOAD_VECTOR_PREFIX_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "workload_vector_prefix_id": self.workload_vector_prefix_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "VectorPrefixTotalV1":
        expected = {
            "schema",
            "schema_version",
            "workload_vector_spec_id",
            "comparison_profile_id",
            "full_order",
            "prefix_length",
            "prefix_occurrence_ids",
            "values",
            "official_scalar_cost",
            "official_N_break_even",
            "scalar_gate_status",
            "workload_vector_prefix_id",
        }
        _fields(document, expected, "workload vector prefix")
        if (
            document["schema"] != "acfqp.workload_vector_prefix.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["full_order"]) is not list
            or type(document["prefix_occurrence_ids"]) is not list
        ):
            raise WorkloadVectorV1Error("workload vector prefix schema mismatch")
        result = cls(
            document["workload_vector_spec_id"],
            document["comparison_profile_id"],
            tuple(document["full_order"]),
            document["prefix_length"],
            tuple(document["prefix_occurrence_ids"]),
            _parse_axis_rows(document["values"], "vector prefix total"),
            document["official_scalar_cost"],
            document["official_N_break_even"],
            document["scalar_gate_status"],
        )
        if document["workload_vector_prefix_id"] != result.workload_vector_prefix_id:
            raise WorkloadVectorV1Error("workload vector prefix content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class WorstFrontierPointV1:
    values: tuple[tuple[str, int], ...]
    witness_orders: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "values", _axis_values(self.values, "worst-frontier point")
        )
        if (
            not self.witness_orders
            or tuple(sorted(self.witness_orders)) != self.witness_orders
            or len(set(self.witness_orders)) != len(self.witness_orders)
        ):
            raise WorkloadVectorV1Error(
                "frontier witness orders must be nonempty, unique, and sorted"
            )
        width = len(self.witness_orders[0])
        for order in self.witness_orders:
            if len(order) != width or len(set(order)) != width:
                raise WorkloadVectorV1Error("frontier witness order shape mismatch")
            for occurrence_id in order:
                _cid(occurrence_id, "frontier witness occurrence ID")

    def to_dict(self) -> dict[str, Any]:
        return {
            "values": _axis_rows(self.values),
            "witness_orders": [list(order) for order in self.witness_orders],
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "WorstFrontierPointV1":
        _fields(document, {"values", "witness_orders"}, "worst-frontier point")
        if type(document["witness_orders"]) is not list or any(
            type(order) is not list for order in document["witness_orders"]
        ):
            raise WorkloadVectorV1Error("frontier witness orders must be lists")
        return cls(
            _parse_axis_rows(document["values"], "worst-frontier point"),
            tuple(tuple(order) for order in document["witness_orders"]),
        )


@dataclass(frozen=True, slots=True)
class PrefixWorstFrontierV1:
    prefix_length: int
    points: tuple[WorstFrontierPointV1, ...]

    def __post_init__(self) -> None:
        _positive(self.prefix_length, "frontier prefix_length")
        if not self.points:
            raise WorkloadVectorV1Error("prefix worst frontier cannot be empty")
        if tuple(sorted(self.points, key=lambda point: point.values)) != self.points:
            raise WorkloadVectorV1Error("prefix frontier points must be vector-sorted")
        if len({point.values for point in self.points}) != len(self.points):
            raise WorkloadVectorV1Error("prefix frontier repeats a vector")
        for point in self.points:
            if any(len(order) < self.prefix_length for order in point.witness_orders):
                raise WorkloadVectorV1Error("frontier witness is shorter than its prefix")

    def to_dict(self) -> dict[str, Any]:
        return {
            "prefix_length": self.prefix_length,
            "points": [point.to_dict() for point in self.points],
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "PrefixWorstFrontierV1":
        _fields(document, {"prefix_length", "points"}, "prefix worst frontier")
        if type(document["points"]) is not list:
            raise WorkloadVectorV1Error("prefix frontier points must be a list")
        return cls(
            document["prefix_length"],
            tuple(WorstFrontierPointV1.from_dict(row) for row in document["points"]),
        )


@dataclass(frozen=True, slots=True)
class WorkloadVectorAnalysisV1:
    workload_vector_spec_id: str
    comparison_profile_id: str
    ordered_logical_occurrence_ids: tuple[str, ...]
    enumerated_order_count: int
    order_enumeration_complete: bool
    vector_prefix_totals: tuple[VectorPrefixTotalV1, ...]
    prefix_worst_frontiers: tuple[PrefixWorstFrontierV1, ...]
    analysis_status: str = VECTOR_ONLY_COMPLETE_ENUMERATION
    official_scalar_cost: None = None
    official_N_break_even: None = None
    scalar_gate_status: str = SCALAR_GATE_NOT_RUN
    _authority: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._authority is not _WORKLOAD_ANALYSIS_AUTHORITY:
            raise WorkloadVectorV1Error(
                "workload analysis requires native occurrence replay"
            )
        _cid(self.workload_vector_spec_id, "workload_vector_spec_id")
        _cid(self.comparison_profile_id, "comparison_profile_id")
        if (
            not self.ordered_logical_occurrence_ids
            or len(set(self.ordered_logical_occurrence_ids))
            != len(self.ordered_logical_occurrence_ids)
        ):
            raise WorkloadVectorV1Error(
                "analysis occurrence order must be nonempty and unique"
            )
        for occurrence_id in self.ordered_logical_occurrence_ids:
            _cid(occurrence_id, "analysis occurrence ID")
        _positive(self.enumerated_order_count, "enumerated_order_count")
        if self.order_enumeration_complete is not True:
            raise WorkloadVectorV1Error("partial order enumeration is non-authoritative")
        expected_prefix_rows = (
            self.enumerated_order_count * len(self.ordered_logical_occurrence_ids)
        )
        if len(self.vector_prefix_totals) != expected_prefix_rows:
            raise WorkloadVectorV1Error("analysis prefix-total cardinality mismatch")
        prefix_key = lambda row: (row.prefix_length, row.full_order)
        if tuple(sorted(self.vector_prefix_totals, key=prefix_key)) != self.vector_prefix_totals:
            raise WorkloadVectorV1Error(
                "analysis prefix totals must be prefix/order-sorted"
            )
        expected_lengths = tuple(range(1, len(self.ordered_logical_occurrence_ids) + 1))
        if tuple(frontier.prefix_length for frontier in self.prefix_worst_frontiers) != expected_lengths:
            raise WorkloadVectorV1Error("analysis must contain one frontier per prefix length")
        if self.analysis_status != VECTOR_ONLY_COMPLETE_ENUMERATION:
            raise WorkloadVectorV1Error("analysis status must remain vector-only")
        _validate_scalar_lock(
            self.official_scalar_cost,
            self.official_N_break_even,
            self.scalar_gate_status,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.workload_vector_analysis.v1",
            "schema_version": SCHEMA_VERSION,
            "workload_vector_spec_id": self.workload_vector_spec_id,
            "comparison_profile_id": self.comparison_profile_id,
            "ordered_logical_occurrence_ids": list(
                self.ordered_logical_occurrence_ids
            ),
            "enumerated_order_count": self.enumerated_order_count,
            "order_enumeration_complete": self.order_enumeration_complete,
            "vector_prefix_totals": [
                prefix.to_dict() for prefix in self.vector_prefix_totals
            ],
            "prefix_worst_frontiers": [
                frontier.to_dict() for frontier in self.prefix_worst_frontiers
            ],
            "analysis_status": self.analysis_status,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "scalar_gate_status": self.scalar_gate_status,
        }

    @property
    def workload_vector_analysis_id(self) -> str:
        return content_id(WORKLOAD_VECTOR_ANALYSIS_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "workload_vector_analysis_id": self.workload_vector_analysis_id,
        }

    @classmethod
    def from_dict(
        cls,
        document: Mapping[str, Any],
        *,
        spec: WorkloadVectorSpecV1 | None = None,
        occurrence_vectors: Mapping[
            str, ReplayableOccurrenceAccountingV1
        ] | None = None,
        registry: CounterRegistryV1 | None = None,
        comparison_profile: ComparisonProfileV1 | None = None,
        actual_profile: ActualProjectionProfileV1 | None = None,
    ) -> "WorkloadVectorAnalysisV1":
        expected = {
            "schema",
            "schema_version",
            "workload_vector_spec_id",
            "comparison_profile_id",
            "ordered_logical_occurrence_ids",
            "enumerated_order_count",
            "order_enumeration_complete",
            "vector_prefix_totals",
            "prefix_worst_frontiers",
            "analysis_status",
            "official_scalar_cost",
            "official_N_break_even",
            "scalar_gate_status",
            "workload_vector_analysis_id",
        }
        _fields(document, expected, "workload vector analysis")
        if (
            document["schema"] != "acfqp.workload_vector_analysis.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["ordered_logical_occurrence_ids"]) is not list
            or type(document["vector_prefix_totals"]) is not list
            or type(document["prefix_worst_frontiers"]) is not list
        ):
            raise WorkloadVectorV1Error("workload vector analysis schema mismatch")
        supplied_id = _cid(
            document["workload_vector_analysis_id"],
            "workload_vector_analysis_id",
        )
        raw_payload = {
            key: value
            for key, value in document.items()
            if key != "workload_vector_analysis_id"
        }
        if supplied_id != content_id(WORKLOAD_VECTOR_ANALYSIS_DOMAIN, raw_payload):
            raise WorkloadVectorV1Error("workload vector analysis content ID mismatch")
        if (
            spec is None
            or occurrence_vectors is None
            or registry is None
            or comparison_profile is None
            or actual_profile is None
        ):
            raise WorkloadVectorV1Error(
                "workload-analysis transport requires native occurrence replay inputs"
            )
        result = analyze_workload_vectors_v1(
            spec,
            occurrence_vectors,
            registry,
            comparison_profile,
            actual_profile,
        )
        if result.to_dict() != dict(document):
            raise WorkloadVectorV1Error(
                "workload vector analysis does not match native occurrence replay"
            )
        return result


def _validate_inputs(
    spec: WorkloadVectorSpecV1,
    occurrence_vectors: Mapping[str, ReplayableOccurrenceAccountingV1],
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> dict[str, tuple[tuple[str, int], ...]]:
    registry.validate_official_catalogue()
    comparison_profile.validate(registry)
    actual_profile.validate(registry, comparison_profile)
    if spec.comparison_profile_id != comparison_profile.comparison_profile_id:
        raise WorkloadVectorV1Error("workload spec comparison-profile mismatch")
    expected_ids = set(spec.ordered_logical_occurrence_ids)
    if set(occurrence_vectors) != expected_ids:
        raise WorkloadVectorV1Error(
            "occurrence vector input set differs from frozen workload order"
        )
    by_ref = {ref.logical_occurrence_id: ref for ref in spec.occurrence_vectors}
    result: dict[str, tuple[tuple[str, int], ...]] = {}
    for occurrence_id in spec.ordered_logical_occurrence_ids:
        accounting = occurrence_vectors[occurrence_id]
        if not isinstance(accounting, ReplayableOccurrenceAccountingV1):
            raise WorkloadVectorV1Error(
                "workload input must be ReplayableOccurrenceAccountingV1, not a "
                "self-signed ComparisonVectorV1"
            )
        if accounting.logical_occurrence_id != occurrence_id:
            raise WorkloadVectorV1Error(
                "occurrence accounting/logical-occurrence identity mismatch"
            )
        if (
            accounting.occurrence_work_sum_id
            != by_ref[occurrence_id].occurrence_work_sum_id
        ):
            raise WorkloadVectorV1Error("occurrence work-sum reference mismatch")
        occurrence_sum = accounting.occurrence_sum
        if occurrence_sum.counter_registry_id != registry.registry_id:
            raise WorkloadVectorV1Error("occurrence work-sum registry mismatch")
        if occurrence_sum.comparison_profile_id != comparison_profile.comparison_profile_id:
            raise WorkloadVectorV1Error(
                "occurrence work-sum comparison-profile mismatch"
            )
        if occurrence_sum.actual_projection_profile_id != actual_profile.actual_projection_profile_id:
            raise WorkloadVectorV1Error(
                "occurrence work-sum actual-projection-profile mismatch"
            )
        try:
            values = accounting.verify(registry, comparison_profile, actual_profile)
        except ValueError as error:
            raise WorkloadVectorV1Error(
                f"occurrence native accounting replay failed: {error}"
            ) from error
        result[occurrence_id] = _axis_values(
            values, "replayed occurrence work sum"
        )
    return result


def _accumulate(
    current: Mapping[str, int],
    values: Sequence[tuple[str, int]],
    reducers: Mapping[str, ReducerEnum],
) -> dict[str, int]:
    result = dict(current)
    for axis, value in values:
        if reducers[axis] is ReducerEnum.SUM:
            result[axis] += value
        else:
            result[axis] = max(result[axis], value)
    return result


def _strictly_worse_or_equal(
    possible_worst: tuple[tuple[str, int], ...],
    other: tuple[tuple[str, int], ...],
) -> bool:
    left = dict(possible_worst)
    right = dict(other)
    return all(left[axis] >= right[axis] for axis in SHARED_AXES) and any(
        left[axis] > right[axis] for axis in SHARED_AXES
    )


def _frontier_for_prefix(
    prefix_length: int,
    rows: Sequence[VectorPrefixTotalV1],
) -> PrefixWorstFrontierV1:
    grouped: dict[tuple[tuple[str, int], ...], list[tuple[str, ...]]] = {}
    for row in rows:
        grouped.setdefault(row.values, []).append(row.full_order)
    nondominated = tuple(
        values
        for values in sorted(grouped)
        if not any(
            _strictly_worse_or_equal(candidate, values)
            for candidate in grouped
            if candidate != values
        )
    )
    points = tuple(
        WorstFrontierPointV1(
            values,
            tuple(sorted(grouped[values])),
        )
        for values in nondominated
    )
    return PrefixWorstFrontierV1(prefix_length, points)


def analyze_workload_vectors_v1(
    spec: WorkloadVectorSpecV1,
    occurrence_vectors: Mapping[str, ReplayableOccurrenceAccountingV1],
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> WorkloadVectorAnalysisV1:
    """Enumerate all registered orders and return vector worst frontiers."""

    vectors = _validate_inputs(
        spec, occurrence_vectors, registry, comparison_profile, actual_profile
    )
    count = math.factorial(len(spec.ordered_logical_occurrence_ids))
    if count > spec.permutation_cap:
        raise PermutationCapExceededError(required=count, cap=spec.permutation_cap)
    reducers = {axis.name: axis.reducer for axis in comparison_profile.axes}
    orders = tuple(permutations(spec.ordered_logical_occurrence_ids))
    prefix_rows: list[VectorPrefixTotalV1] = []
    for order in orders:
        cumulative = {axis: 0 for axis in SHARED_AXES}
        for prefix_length, occurrence_id in enumerate(order, start=1):
            cumulative = _accumulate(
                cumulative, vectors[occurrence_id], reducers
            )
            prefix_rows.append(
                VectorPrefixTotalV1(
                    spec.workload_vector_spec_id,
                    comparison_profile.comparison_profile_id,
                    order,
                    prefix_length,
                    order[:prefix_length],
                    tuple(sorted(cumulative.items())),
                )
            )
    prefix_totals = tuple(
        sorted(prefix_rows, key=lambda row: (row.prefix_length, row.full_order))
    )
    frontiers = tuple(
        _frontier_for_prefix(
            prefix_length,
            tuple(
                row
                for row in prefix_totals
                if row.prefix_length == prefix_length
            ),
        )
        for prefix_length in range(1, len(spec.ordered_logical_occurrence_ids) + 1)
    )
    return WorkloadVectorAnalysisV1(
        spec.workload_vector_spec_id,
        comparison_profile.comparison_profile_id,
        spec.ordered_logical_occurrence_ids,
        count,
        True,
        prefix_totals,
        frontiers,
        _authority=_WORKLOAD_ANALYSIS_AUTHORITY,
    )


def verify_workload_vector_analysis_v1(
    analysis: WorkloadVectorAnalysisV1,
    spec: WorkloadVectorSpecV1,
    occurrence_vectors: Mapping[str, ReplayableOccurrenceAccountingV1],
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> None:
    if analysis._authority is not _WORKLOAD_ANALYSIS_AUTHORITY:
        raise WorkloadVectorV1Error(
            "workload vector analysis lacks native replay authority"
        )
    expected = analyze_workload_vectors_v1(
        spec,
        occurrence_vectors,
        registry,
        comparison_profile,
        actual_profile,
    )
    if analysis != expected:
        raise WorkloadVectorV1Error(
            "workload vector analysis does not match exact permutation replay"
        )


__all__ = [
    "MAX_EXPLICIT_PERMUTATIONS",
    "OccurrenceVectorRefV1",
    "PermutationCapExceededError",
    "PrefixWorstFrontierV1",
    "ReplayableOccurrenceAccountingV1",
    "SCALAR_GATE_NOT_RUN",
    "VECTOR_ONLY_COMPLETE_ENUMERATION",
    "VectorPrefixTotalV1",
    "WorkloadVectorAnalysisV1",
    "WorkloadVectorSpecV1",
    "WorkloadVectorV1Error",
    "WorstFrontierPointV1",
    "analyze_workload_vectors_v1",
    "verify_workload_vector_analysis_v1",
]
