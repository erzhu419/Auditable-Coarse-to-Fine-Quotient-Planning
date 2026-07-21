"""Historical in-process adapter and shared fallback-result adaptation.

The adapter is deliberately a post-freeze object.  It cannot be used to probe
the kernel while estimating routes: before invoking
``execute_authorized_ground_fallback_v1`` it requires a frozen FALLBACK route,
an untouched runner recorder, and exact prepared-context bindings.  The ground
fallback owns its native ledger, so its ``WorkVectorV1`` is adapted directly;
native counters are never copied into the runner recorder.

The callable in this module is retained only so historical objects have an
explicit fail-closed migration point.  The registered fallback cardinality
profile now prices one isolated process and finite I/O/peak capacity, so an
in-process execution may not consume that upper.  New executions use
``AuthorizedIsolatedGroundFallbackExecutorV1``.  The pure adaptation helper is
shared by that isolated supervisor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acfqp.access_protocol_v1 import (
    FailClosedAccessController,
)
from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRegistryV1,
    RouteKindEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import (
    NativeCounterRecorderV1,
    derive_recorded_work_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
)
from acfqp.phase3e_runner_v1 import (
    Phase3ERouteExecutionV1,
    Phase3ERunnerV1Error,
    PreparedPhase3ERunV1,
)
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    DecisionPointV1,
    RouteDecisionContextV1,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
)


class Phase3EFallbackAdapterV1Error(Phase3ERunnerV1Error):
    """Fallback adapter was invoked before authority/freeze or with mixed work."""


@dataclass(frozen=True, slots=True)
class GroundFallbackExecutorInputsV1:
    """All frozen and runtime authority inputs required by the fallback."""

    kernel: Any
    query: Any
    context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    fallback_upper: RouteUpperBoundEnvelopeV1
    cardinality: CardinalityEvidenceV1
    cardinality_bound: GroundFallbackCardinalityBoundV1
    cap_profile: GroundFallbackCapProfileV1
    route_decision_result: object
    fallback_upper_result: object
    cardinality_result: object


def adapt_ground_fallback_execution_v1(
    execution: GroundFallbackExecutionV1,
    *,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
    semantic_verification_results: tuple[object, ...] = (),
    semantic_verification_deferred: bool = False,
) -> Phase3ERouteExecutionV1:
    """Preserve the fallback-owned native vector in the runner result."""

    if not isinstance(execution, GroundFallbackExecutionV1):
        raise Phase3EFallbackAdapterV1Error(
            "fallback adapter requires GroundFallbackExecutionV1"
        )
    registry = registry or official_counter_registry_v1()
    profile = comparison_profile or official_comparison_profile_v1(registry)
    native = derive_recorded_work_v1(
        execution.work_vector,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
    )
    # CAP_EXHAUSTED closes this attempt without a certificate.  It is not an
    # infeasibility result and cannot request a local transaction by itself.
    completed = execution.result.outcome is not GroundFallbackOutcome.CAP_EXHAUSTED
    sealed = execution.trusted_provenance is not None
    if not sealed:
        raise Phase3EFallbackAdapterV1Error(
            "raw fallback search output lacks selected-route semantic authority"
        )
    return Phase3ERouteExecutionV1(
        execution.result.ground_fallback_result_id,
        completed,
        False,
        native,
        execution,
        execution.result.outcome.value,
        semantic_verification_results,
        semantic_verification_deferred=semantic_verification_deferred,
    )


@dataclass(frozen=True, slots=True)
class AuthorizedGroundFallbackExecutorV1:
    """Historical callable that fails closed under the isolated V1 profile."""

    inputs: GroundFallbackExecutorInputsV1
    registry: CounterRegistryV1 | None = None
    comparison_profile: ComparisonProfileV1 | None = None

    def __call__(
        self,
        prepared: PreparedPhase3ERunV1,
        controller: FailClosedAccessController,
        recorder: NativeCounterRecorderV1,
    ) -> Phase3ERouteExecutionV1:
        if not isinstance(recorder, NativeCounterRecorderV1):
            raise Phase3EFallbackAdapterV1Error(
                "fallback executor requires the runner native recorder"
            )
        if (
            recorder.route_kind is not RouteKindEnum.DIRECT_FALLBACK
            or recorder.work_scope
            is not ActualWorkScope.MARGINAL_ROUTE_EXECUTION
        ):
            raise Phase3EFallbackAdapterV1Error(
                "fallback executor received another route recorder"
            )
        if any(recorder.values.values()):
            raise Phase3EFallbackAdapterV1Error(
                "fallback-owned native work cannot be mixed into the runner recorder"
            )
        if not isinstance(controller, FailClosedAccessController):
            raise Phase3EFallbackAdapterV1Error(
                "fallback executor requires FailClosedAccessController"
            )
        freeze = controller.freeze_attestation
        if freeze is None or freeze.selected_route is not RouteSelection.FALLBACK:
            raise Phase3EFallbackAdapterV1Error(
                "ground fallback cannot execute before a frozen FALLBACK decision"
            )
        raise Phase3EFallbackAdapterV1Error(
            "the in-process fallback executor is not registered for the isolated "
            "resource upper; use AuthorizedIsolatedGroundFallbackExecutorV1"
        )


__all__ = [
    "AuthorizedGroundFallbackExecutorV1",
    "GroundFallbackExecutorInputsV1",
    "Phase3EFallbackAdapterV1Error",
    "adapt_ground_fallback_execution_v1",
]
