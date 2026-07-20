from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    PEAK_WORKING_BYTES,
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualAccountingV1Error,
    ActualWorkScope,
    derive_actual_projection_v1,
    official_actual_projection_profile_v1,
)
from acfqp.marginal_accounting_v1 import (
    AggregatedMarginalWorkV1,
    MarginalAccountingV1Error,
    MarginalWorkAggregationProofV1,
    derive_marginal_work_aggregate_v1,
    verify_marginal_work_aggregate_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _component(
    *,
    subject: str,
    route: RouteKindEnum,
    scope: ActualWorkScope,
    values: dict[str, int],
):
    registry = official_counter_registry_v1()
    comparison_profile = official_comparison_profile_v1(registry)
    actual_profile = official_actual_projection_profile_v1(
        registry, comparison_profile
    )
    native = {path: 0 for path in registry.required_paths}
    native.update(values)
    work = registry.materialize(
        subject_id=subject,
        route_kind=route,
        records=explicit_records_v1(
            registry, native, recorder_id=f"{scope.value.lower()}-test-v1"
        ),
    )
    projected, proof = derive_actual_projection_v1(
        work,
        registry,
        comparison_profile,
        actual_profile,
        source_lane="operational",
        work_scope=scope,
    )
    return work, projected, proof


@pytest.mark.parametrize(
    ("route", "route_values"),
    (
        (
            RouteKindEnum.LOCAL_ATTEMPT,
            {
                "local.materialization_ground_steps": 5,
                "local.solver_policy_assignments": 7,
            },
        ),
        (
            RouteKindEnum.DIRECT_FALLBACK,
            {
                "fallback.ground_steps": 5,
                "fallback.actions_evaluated": 7,
            },
        ),
    ),
)
def test_execution_and_verification_suffix_aggregate_without_prefix_relabel(
    route: RouteKindEnum, route_values: dict[str, int]
) -> None:
    subject = _id(f"{route.value}-subject")
    execution = _component(
        subject=subject,
        route=route,
        scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        values={
            **route_values,
            "memory.working_bytes_peak": 40,
            "route.attempts": 1,
            "route.successes": 1,
            "solver.attempts": 1,
            "solver.successes": 1,
        },
    )
    suffix = _component(
        subject=subject,
        route=route,
        scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        values={
            "common.integrity_checks": 2,
            "common.protocol_checks": 3,
            "common.hash_invocations": 4,
            "memory.working_bytes_peak": 64,
        },
    )
    registry = official_counter_registry_v1()
    comparison_profile = official_comparison_profile_v1(registry)
    actual_profile = official_actual_projection_profile_v1(
        registry, comparison_profile
    )
    aggregate = derive_marginal_work_aggregate_v1(
        subject_id=subject,
        route_kind=route,
        execution=execution,
        verification_suffix=suffix,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    native = aggregate.aggregate_work_vector.values
    projected = dict(aggregate.aggregate_comparison_vector.values)
    assert native["common.protocol_checks"] == 3
    assert native[next(iter(route_values))] == route_values[next(iter(route_values))]
    assert projected[KERNEL_TRANSITION_CALLS] == 5
    assert projected[NONKERNEL_COMPUTE_EVENTS] == 7 + 2 + 3 + 4
    assert projected[PEAK_WORKING_BYTES] == 64
    assert aggregate.aggregate_projection_proof.work_scope is (
        ActualWorkScope.MARGINAL_ROUTE_AGGREGATE
    )
    assert MarginalWorkAggregationProofV1.from_dict(
        aggregate.aggregation_proof.to_dict()
    ) == aggregate.aggregation_proof
    assert verify_marginal_work_aggregate_v1(
        aggregate,
        subject_id=subject,
        route_kind=route,
        execution=execution,
        verification_suffix=suffix,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    ) == aggregate


def test_verification_suffix_cannot_hide_route_execution_work() -> None:
    with pytest.raises(ActualAccountingV1Error, match="forbidden work"):
        _component(
            subject=_id("bad-suffix-subject"),
            route=RouteKindEnum.DIRECT_FALLBACK,
            scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
            values={"fallback.ground_steps": 1},
        )


def test_aggregate_rejects_rebound_suffix_and_forged_proof() -> None:
    subject = _id("aggregate-subject")
    execution = _component(
        subject=subject,
        route=RouteKindEnum.DIRECT_FALLBACK,
        scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        values={"fallback.ground_steps": 1},
    )
    stale_suffix = _component(
        subject=_id("stale-subject"),
        route=RouteKindEnum.DIRECT_FALLBACK,
        scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        values={"common.protocol_checks": 1},
    )
    registry = official_counter_registry_v1()
    comparison_profile = official_comparison_profile_v1(registry)
    actual_profile = official_actual_projection_profile_v1(
        registry, comparison_profile
    )
    with pytest.raises(MarginalAccountingV1Error, match="wrong subject"):
        derive_marginal_work_aggregate_v1(
            subject_id=subject,
            route_kind=RouteKindEnum.DIRECT_FALLBACK,
            execution=execution,
            verification_suffix=stale_suffix,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )

    suffix = _component(
        subject=subject,
        route=RouteKindEnum.DIRECT_FALLBACK,
        scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        values={"common.protocol_checks": 1},
    )
    aggregate = derive_marginal_work_aggregate_v1(
        subject_id=subject,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        execution=execution,
        verification_suffix=suffix,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    forged = AggregatedMarginalWorkV1(
        aggregate.aggregate_work_vector,
        aggregate.aggregate_comparison_vector,
        aggregate.aggregate_projection_proof,
        replace(
            aggregate.aggregation_proof,
            verification_work_vector_id=_id("substituted-work"),
        ),
    )
    with pytest.raises(MarginalAccountingV1Error, match="differs"):
        verify_marginal_work_aggregate_v1(
            forged,
            subject_id=subject,
            route_kind=RouteKindEnum.DIRECT_FALLBACK,
            execution=execution,
            verification_suffix=suffix,
            registry=registry,
            comparison_profile=comparison_profile,
            actual_profile=actual_profile,
        )
