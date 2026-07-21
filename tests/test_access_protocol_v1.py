from __future__ import annotations

import copy
import hashlib
from types import SimpleNamespace

import pytest

from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    AccessEventV1,
    AccessOperation,
    AccessProtocolV1Error,
    AccessProtocolViolation,
    AccessRouteScope,
    AccessViolationReason,
    FailClosedAccessController,
    ForbiddenAccessViolationV1,
    ProtocolSequenceProfileV1,
    decide_then_execute,
    local_execution_order_violation_v1,
    local_execution_stages_v1,
    replay_access_protocol,
)
from acfqp.phase3e_ids import ACCESS_EVENT_LOG_DOMAIN, content_id
from acfqp.routing_v1 import (
    MarginalRouteDecisionV1,
    RouteComparison,
    RouteSelection,
    TypedNotApplicable,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _controller(label: str = "base") -> FailClosedAccessController:
    return FailClosedAccessController(
        _id(f"{label}-route-attempt"),
        _id(f"{label}-decision-point"),
    )


def _raw_decision(point: str, selected: RouteSelection) -> MarginalRouteDecisionV1:
    fallback = _id("fallback-upper")
    if selected is RouteSelection.LOCAL:
        local = _id("local-upper")
        return MarginalRouteDecisionV1(
            point,
            _id("causal"),
            local,
            fallback,
            selected,
            RouteComparison.LOCAL_STRICTLY_DOMINATES,
            local,
        )
    return MarginalRouteDecisionV1(
        point,
        TypedNotApplicable("no causal authority"),
        TypedNotApplicable("no local upper authority"),
        fallback,
        selected,
        RouteComparison.MISSING_LOCAL_UPPER,
        fallback,
    )


def _local_events(operations: tuple[AccessOperation, ...]) -> tuple[AccessEventV1, ...]:
    return tuple(
        AccessEventV1(
            index,
            _id("attempt"),
            _id("point"),
            operation,
            AccessRouteScope.LOCAL,
            _id(f"artifact-{index}")
            if operation.value.endswith("_ARTIFACT")
            else None,
        )
        for index, operation in enumerate(operations, start=1)
    )


def test_preselection_forbidden_access_fails_closed_and_replays() -> None:
    controller = _controller("preselection")
    with pytest.raises(AccessProtocolViolation) as caught:
        controller.record(AccessOperation.KERNEL_STEP, AccessRouteScope.LOCAL)
    violation = caught.value.violation
    assert violation.reason is AccessViolationReason.PRESELECTION_FORBIDDEN_ACCESS
    assert violation.terminal_code == "PROTOCOL_FAILURE"
    assert ForbiddenAccessViolationV1.from_dict(violation.to_dict()) == violation
    with pytest.raises(AccessProtocolViolation):
        replay_access_protocol(controller.snapshot(), controller.profile)


@pytest.mark.parametrize(
    "operation",
    (
        AccessOperation.RESOLVE_RUNTIME_CAS,
        AccessOperation.OPEN_RUNTIME_PRIVATE_LEASE,
        AccessOperation.CONSTRUCT_SELECTED_EXECUTOR,
    ),
)
def test_runtime_construction_access_is_forbidden_before_route_freeze(
    operation: AccessOperation,
) -> None:
    controller = _controller(f"prefreeze-{operation.value}")
    with pytest.raises(AccessProtocolViolation) as caught:
        controller.record(
            operation,
            AccessRouteScope.FALLBACK,
            artifact_id=_id(operation.value),
        )
    assert (
        caught.value.violation.reason
        is AccessViolationReason.PRESELECTION_FORBIDDEN_ACCESS
    )


@pytest.mark.parametrize("selected", tuple(RouteSelection))
def test_self_hashed_route_decision_cannot_freeze_execution(
    selected: RouteSelection,
) -> None:
    controller = _controller(f"raw-{selected.value}")
    raw = _raw_decision(controller.decision_point_id, selected)
    with pytest.raises(
        AccessProtocolV1Error, match="authority-bearing ROUTE_DECISION"
    ):
        controller.freeze_route_decision(raw)
    assert controller.freeze_attestation is None


def test_local_stage_order_accepts_repeated_events_without_regression() -> None:
    events = _local_events(
        (
            AccessOperation.LOCAL_SLICE_MATERIALIZATION,
            AccessOperation.KERNEL_STEP,
            AccessOperation.LOCAL_SLICE_MATERIALIZATION,
            AccessOperation.LOCAL_CAPABILITY_COMPILATION,
            AccessOperation.LOCAL_CAPABILITY_ARTIFACT,
            AccessOperation.LOCAL_WORKER_LAUNCH,
            AccessOperation.LOCAL_WORKER_RESULT_ARTIFACT,
            AccessOperation.LOCAL_PATCH_STITCH,
            AccessOperation.LOCAL_STITCH_ARTIFACT,
            AccessOperation.LOCAL_POSTAUDIT,
            AccessOperation.KERNEL_STEP,
            AccessOperation.LOCAL_POSTAUDIT_ARTIFACT,
        )
    )
    assert local_execution_order_violation_v1(
        events, freeze_after_sequence=0
    ) is None
    assert local_execution_stages_v1(
        events, freeze_after_sequence=0
    ) == (1, 2, 3, 4, 5)


def test_local_solver_no_candidate_may_close_at_worker_stage() -> None:
    """Cap/no-feasible outcomes must reach the fresh-fallback state machine."""

    class ControllerStub:
        def __init__(self) -> None:
            self._decision = None
            self.freeze_attestation = None
            self._events = _local_events(
                (
                    AccessOperation.LOCAL_SLICE_MATERIALIZATION,
                    AccessOperation.LOCAL_CAPABILITY_COMPILATION,
                    AccessOperation.LOCAL_WORKER_LAUNCH,
                )
            )

        def freeze_route_decision(self, _result):
            self._decision = _raw_decision(_id("point"), RouteSelection.LOCAL)
            self.freeze_attestation = SimpleNamespace(last_preselection_sequence=0)

        def verify(self) -> None:
            return None

        def snapshot(self):
            return SimpleNamespace(events=self._events)

    controller = ControllerStub()
    marker = object()
    assert decide_then_execute(
        controller,  # type: ignore[arg-type]
        object(),
        local_callback=lambda _controller: marker,
        fallback_callback=lambda _controller: None,
    ) is marker


@pytest.mark.parametrize(
    "operations",
    (
        (
            AccessOperation.LOCAL_SLICE_MATERIALIZATION,
            AccessOperation.LOCAL_WORKER_LAUNCH,
        ),
        (
            AccessOperation.LOCAL_SLICE_MATERIALIZATION,
            AccessOperation.LOCAL_CAPABILITY_COMPILATION,
            AccessOperation.LOCAL_SLICE_MATERIALIZATION,
        ),
        (AccessOperation.LOCAL_POSTAUDIT,),
        (AccessOperation.LOCAL_CAPABILITY_ARTIFACT,),
        (
            AccessOperation.LOCAL_SLICE_MATERIALIZATION,
            AccessOperation.LOCAL_CAPABILITY_COMPILATION,
            AccessOperation.KERNEL_STEP,
        ),
    ),
)
def test_local_stage_skip_reverse_artifact_and_misplaced_kernel_are_rejected(
    operations: tuple[AccessOperation, ...],
) -> None:
    events = _local_events(operations)
    assert local_execution_order_violation_v1(
        events, freeze_after_sequence=0
    ) is not None


def test_unfrozen_access_log_tamper_is_detected() -> None:
    controller = _controller("tamper")
    controller.record(
        AccessOperation.READ_FROZEN_RAPM,
        AccessRouteScope.COMMON,
        artifact_id=_id("tamper-rapm"),
    )
    log = controller.snapshot()
    assert AccessEventLogV1.from_dict(log.to_dict()) == log
    tampered = copy.deepcopy(log.to_dict())
    tampered["events"][0]["operation"] = AccessOperation.READ_CAP_REGISTRY.value
    with pytest.raises(AccessProtocolV1Error, match="content ID mismatch"):
        AccessEventLogV1.from_dict(tampered)

    resigned = copy.deepcopy(tampered)
    payload = dict(resigned)
    payload.pop("access_event_log_id")
    resigned["access_event_log_id"] = content_id(ACCESS_EVENT_LOG_DOMAIN, payload)
    # A malicious producer can re-sign bytes; semantic replay still constrains
    # the operation to the preselection whitelist.
    assert AccessEventLogV1.from_dict(resigned).events[0].operation is (
        AccessOperation.READ_CAP_REGISTRY
    )


def test_preselection_reads_require_and_hash_the_exact_artifact_identity() -> None:
    controller = _controller("identity-bearing-read")
    with pytest.raises(AccessProtocolV1Error, match="full Phase-3E content ID"):
        controller.record(
            AccessOperation.READ_SELECTED_PLAN,
            AccessRouteScope.COMMON,
        )
    first = _controller("identity-bearing-read-first")
    second = _controller("identity-bearing-read-first")
    first.record(
        AccessOperation.READ_SELECTED_PLAN,
        AccessRouteScope.COMMON,
        artifact_id=_id("selected-plan-a"),
    )
    second.record(
        AccessOperation.READ_SELECTED_PLAN,
        AccessRouteScope.COMMON,
        artifact_id=_id("selected-plan-b"),
    )
    assert first.snapshot().access_event_log_id != second.snapshot().access_event_log_id
