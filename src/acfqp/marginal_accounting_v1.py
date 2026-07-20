"""Native aggregation of selected-route execution and verification suffix work.

Operational result verification happens after a route has executed, so charging it
to the already-frozen common prefix would falsify the access order.  It also cannot
be inserted into the result's execution WorkVector without a content-ID cycle.  This
module resolves that boundary explicitly:

``execution WorkVector + verification-suffix WorkVector -> aggregate WorkVector``.

The aggregation is reducer aware, retains both source vectors in a content-addressed
proof, and produces the one comparison vector that is checked against the selected
pre-execution upper.  It never introduces a scalar cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    ComparisonVectorV1,
    CounterRecordV1,
    CounterRegistryV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualProjectionProfileV1,
    ActualWorkScope,
    derive_actual_projection_v1,
    verify_actual_projection_v1,
)
from acfqp.phase3e_ids import (
    MARGINAL_WORK_AGGREGATION_PROOF_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "1.0.0"
AGGREGATION_RECORDER_ID = "phase3e-marginal-native-aggregation-v1"


class MarginalAccountingV1Error(ValueError):
    """A component, reducer, subject, or aggregation proof is invalid."""


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise MarginalAccountingV1Error(
            f"{field} must be a full Phase-3E content ID"
        ) from error


def _fields(document: Mapping[str, Any], expected: set[str], context: str) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise MarginalAccountingV1Error(str(error)) from error


@dataclass(frozen=True, slots=True)
class MarginalWorkAggregationProofV1:
    """Replay binding for a two-stage native marginal route aggregate."""

    subject_id: str
    route_kind: RouteKindEnum
    counter_registry_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    execution_work_vector_id: str
    execution_comparison_vector_id: str
    execution_projection_proof_id: str
    verification_work_vector_id: str
    verification_comparison_vector_id: str
    verification_projection_proof_id: str
    aggregate_work_vector_id: str
    aggregate_comparison_vector_id: str
    aggregate_projection_proof_id: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "subject_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "execution_work_vector_id",
            "execution_comparison_vector_id",
            "execution_projection_proof_id",
            "verification_work_vector_id",
            "verification_comparison_vector_id",
            "verification_projection_proof_id",
            "aggregate_work_vector_id",
            "aggregate_comparison_vector_id",
            "aggregate_projection_proof_id",
        ):
            _cid(getattr(self, field), field)
        try:
            object.__setattr__(self, "route_kind", RouteKindEnum(self.route_kind))
        except (TypeError, ValueError) as error:
            raise MarginalAccountingV1Error("invalid marginal route kind") from error
        if self.route_kind not in {
            RouteKindEnum.LOCAL_ATTEMPT,
            RouteKindEnum.DIRECT_FALLBACK,
        }:
            raise MarginalAccountingV1Error(
                "marginal aggregation requires local or direct-fallback work"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise MarginalAccountingV1Error("aggregation proof version mismatch")
        if self.execution_work_vector_id == self.verification_work_vector_id:
            raise MarginalAccountingV1Error(
                "execution and verification suffix must be distinct WorkVectors"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.marginal_work_aggregation_proof.v1",
            "schema_version": self.schema_version,
            "subject_id": self.subject_id,
            "route_kind": self.route_kind.value,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "execution_work_vector_id": self.execution_work_vector_id,
            "execution_comparison_vector_id": self.execution_comparison_vector_id,
            "execution_projection_proof_id": self.execution_projection_proof_id,
            "verification_work_vector_id": self.verification_work_vector_id,
            "verification_comparison_vector_id": self.verification_comparison_vector_id,
            "verification_projection_proof_id": self.verification_projection_proof_id,
            "aggregate_work_vector_id": self.aggregate_work_vector_id,
            "aggregate_comparison_vector_id": self.aggregate_comparison_vector_id,
            "aggregate_projection_proof_id": self.aggregate_projection_proof_id,
        }

    @property
    def marginal_work_aggregation_proof_id(self) -> str:
        return content_id(MARGINAL_WORK_AGGREGATION_PROOF_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "marginal_work_aggregation_proof_id": (
                self.marginal_work_aggregation_proof_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "MarginalWorkAggregationProofV1":
        expected = {
            "schema",
            "schema_version",
            "subject_id",
            "route_kind",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "execution_work_vector_id",
            "execution_comparison_vector_id",
            "execution_projection_proof_id",
            "verification_work_vector_id",
            "verification_comparison_vector_id",
            "verification_projection_proof_id",
            "aggregate_work_vector_id",
            "aggregate_comparison_vector_id",
            "aggregate_projection_proof_id",
            "marginal_work_aggregation_proof_id",
        }
        _fields(document, expected, "marginal work aggregation proof")
        if document["schema"] != "acfqp.marginal_work_aggregation_proof.v1":
            raise MarginalAccountingV1Error("aggregation proof schema mismatch")
        result = cls(
            document["subject_id"],
            document["route_kind"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["actual_projection_profile_id"],
            document["execution_work_vector_id"],
            document["execution_comparison_vector_id"],
            document["execution_projection_proof_id"],
            document["verification_work_vector_id"],
            document["verification_comparison_vector_id"],
            document["verification_projection_proof_id"],
            document["aggregate_work_vector_id"],
            document["aggregate_comparison_vector_id"],
            document["aggregate_projection_proof_id"],
            document["schema_version"],
        )
        if (
            document["marginal_work_aggregation_proof_id"]
            != result.marginal_work_aggregation_proof_id
        ):
            raise MarginalAccountingV1Error("aggregation proof content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class AggregatedMarginalWorkV1:
    aggregate_work_vector: WorkVectorV1
    aggregate_comparison_vector: ComparisonVectorV1
    aggregate_projection_proof: ActualProjectionProofV1
    aggregation_proof: MarginalWorkAggregationProofV1


def _validate_component(
    component: tuple[WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1],
    *,
    expected_scope: ActualWorkScope,
    subject_id: str,
    route_kind: RouteKindEnum,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> tuple[WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1]:
    work, comparison, proof = component
    if (
        work.subject_id != subject_id
        or work.route_kind is not route_kind
        or comparison.subject_id != subject_id
        or comparison.route_kind is not route_kind
        or proof.work_scope is not expected_scope
    ):
        raise MarginalAccountingV1Error(
            f"{expected_scope.value} component has wrong subject, route, or scope"
        )
    try:
        verify_actual_projection_v1(
            proof,
            work,
            comparison,
            registry,
            comparison_profile,
            actual_profile,
        )
    except ValueError as error:
        raise MarginalAccountingV1Error(
            f"invalid {expected_scope.value} component: {error}"
        ) from error
    return component


def derive_marginal_work_aggregate_v1(
    *,
    subject_id: str,
    route_kind: RouteKindEnum | str,
    execution: tuple[
        WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
    ],
    verification_suffix: tuple[
        WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
    ],
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> AggregatedMarginalWorkV1:
    """Derive the reducer-aware aggregate checked against a selected upper."""

    subject = _cid(subject_id, "subject_id")
    try:
        route = RouteKindEnum(route_kind)
        registry.validate_official_catalogue()
        comparison_profile.validate(registry)
        actual_profile.validate(registry, comparison_profile)
    except ValueError as error:
        raise MarginalAccountingV1Error(str(error)) from error
    if route not in {
        RouteKindEnum.LOCAL_ATTEMPT,
        RouteKindEnum.DIRECT_FALLBACK,
    }:
        raise MarginalAccountingV1Error("aggregate route is not marginal")

    execution = _validate_component(
        execution,
        expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        subject_id=subject,
        route_kind=route,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    verification_suffix = _validate_component(
        verification_suffix,
        expected_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        subject_id=subject,
        route_kind=route,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    component_work = (execution[0], verification_suffix[0])
    paths = sorted({row.path for vector in component_work for row in vector.records})
    values: dict[str, int] = {}
    for path in paths:
        leaf = registry.by_path[path]
        observed = [vector.values.get(path, 0) for vector in component_work]
        values[path] = (
            sum(observed)
            if leaf.reducer is ReducerEnum.SUM
            else max(observed, default=0)
        )
    try:
        records = tuple(
            CounterRecordV1.observe(
                registry,
                path,
                values[path],
                recorder_id=AGGREGATION_RECORDER_ID,
            )
            for path in paths
        )
        aggregate_work = registry.materialize(
            subject_id=subject,
            route_kind=route,
            records=records,
        )
        aggregate_comparison, aggregate_projection = derive_actual_projection_v1(
            aggregate_work,
            registry,
            comparison_profile,
            actual_profile,
            source_lane=LaneEnum.OPERATIONAL,
            work_scope=ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
        )
    except ValueError as error:
        raise MarginalAccountingV1Error(
            f"cannot materialize marginal aggregate: {error}"
        ) from error

    proof = MarginalWorkAggregationProofV1(
        subject,
        route,
        registry.registry_id,
        comparison_profile.comparison_profile_id,
        actual_profile.actual_projection_profile_id,
        execution[0].work_vector_id,
        execution[1].comparison_vector_id,
        execution[2].actual_projection_proof_id,
        verification_suffix[0].work_vector_id,
        verification_suffix[1].comparison_vector_id,
        verification_suffix[2].actual_projection_proof_id,
        aggregate_work.work_vector_id,
        aggregate_comparison.comparison_vector_id,
        aggregate_projection.actual_projection_proof_id,
    )
    return AggregatedMarginalWorkV1(
        aggregate_work,
        aggregate_comparison,
        aggregate_projection,
        proof,
    )


def verify_marginal_work_aggregate_v1(
    claimed: AggregatedMarginalWorkV1,
    *,
    subject_id: str,
    route_kind: RouteKindEnum | str,
    execution: tuple[
        WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
    ],
    verification_suffix: tuple[
        WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
    ],
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> AggregatedMarginalWorkV1:
    replayed = derive_marginal_work_aggregate_v1(
        subject_id=subject_id,
        route_kind=route_kind,
        execution=execution,
        verification_suffix=verification_suffix,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    if claimed != replayed:
        raise MarginalAccountingV1Error(
            "claimed marginal aggregate differs from native reducer replay"
        )
    return replayed


__all__ = [
    "AGGREGATION_RECORDER_ID",
    "AggregatedMarginalWorkV1",
    "MarginalAccountingV1Error",
    "MarginalWorkAggregationProofV1",
    "derive_marginal_work_aggregate_v1",
    "verify_marginal_work_aggregate_v1",
]
