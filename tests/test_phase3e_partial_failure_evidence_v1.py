from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp.access_protocol_v1 import (
    AccessOperation,
    AccessRouteScope,
    PRESELECTION_READ_OPERATIONS,
)
from acfqp.accounting_v1 import (
    RouteKindEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import (
    NativeCounterRecorderV1,
    verify_recorded_work_v1,
)
from acfqp.phase3e_occurrence_runner_v1 import run_phase3e_occurrence_v1
from acfqp.phase3e_fallback_v1 import GroundFallbackProtocolError
from acfqp.phase3e_runner_v1 import (
    AccessNativeReconciliationStatusV1,
    FailedRouteErrorClassV1,
    Phase3EDecisionAuthorizationV1,
    Phase3EPreselectionReadV1,
    Phase3ERouteExecutionFailedV1,
    Phase3ERunnerV1Error,
    PreparedPhase3ERunV1,
    run_phase3e,
    verify_failed_route_evidence_v1,
)
from tests.test_phase3e_fallback_cap_min_v1 import _authority_chain


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:phase3e-partial-failure-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def _prepared(monkeypatch: pytest.MonkeyPatch):
    """Use a real semantic decision while isolating failure-retention tests."""

    chain = _authority_chain()
    registry = chain["registry"]
    profile = chain["profile"]
    context = chain["context"]
    point = chain["point"]
    common_recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-partial-failure-common-v1",
    )
    common = common_recorder.seal()
    reads = tuple(
        Phase3EPreselectionReadV1(operation, _id(f"read-{operation.value}"))
        for operation in PRESELECTION_READ_OPERATIONS
    )
    prepared = PreparedPhase3ERunV1(
        context,
        point,
        _id("reusable-rapm"),
        _id("failed-certificate"),
        _id("action-catalogue"),
        reads,
        common,
        Phase3EDecisionAuthorizationV1(
            chain["decision_result"],
            chain["upper_result"],
            (chain["upper_result"], chain["decision_result"]),
        ),
    )

    # The full preparation-binding checks are exercised by integration tests.
    # Here the point's historical placeholder common-work ID is intentionally
    # bypassed so the test can focus on a post-freeze failure with a genuine
    # semantic ROUTE_DECISION handle.
    def validated(_self, _registry, _profile):
        return chain["decision_result"].artifact, chain["upper_result"].artifact

    monkeypatch.setattr(PreparedPhase3ERunV1, "validate", validated)
    return prepared, registry, profile


def _forbidden_local(*_args):
    raise AssertionError("fallback authority executed the local route")


def _record_one_ground_step(controller, recorder) -> None:
    controller.record(
        AccessOperation.FALLBACK_SOLVER_INVOCATION,
        AccessRouteScope.FALLBACK,
    )
    controller.record(AccessOperation.KERNEL_STEP, AccessRouteScope.FALLBACK)
    recorder.add("fallback.ground_steps", 1)
    controller.record(
        AccessOperation.GROUND_OUTCOME_ENUMERATION,
        AccessRouteScope.FALLBACK,
    )


def test_executor_exception_preserves_exact_failed_route_work_and_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared, registry, profile = _prepared(monkeypatch)

    def failed_executor(_prepared, controller, recorder):
        _record_one_ground_step(controller, recorder)
        raise RuntimeError("injected selected-route crash")

    with pytest.raises(Phase3ERouteExecutionFailedV1) as caught:
        run_phase3e(
            prepared,
            local_executor=_forbidden_local,
            fallback_executor=failed_executor,
            registry=registry,
            comparison_profile=profile,
        )
    failure = caught.value
    evidence = verify_failed_route_evidence_v1(
        failure.evidence,
        registry=registry,
        comparison_profile=profile,
    )
    values = evidence.partial_route_work.work_vector.values
    assert values["fallback.ground_steps"] == 1
    assert (
        values["route.attempts"],
        values["route.successes"],
        values["route.failures"],
    ) == (1, 0, 1)
    assert evidence.access_native_reconciliation_status is (
        AccessNativeReconciliationStatusV1.RECONCILED
    )
    assert evidence.original_error_classification is (
        FailedRouteErrorClassV1.SELECTED_ROUTE_EXECUTOR_FAILURE
    )
    assert evidence.original_error_type.endswith(".RuntimeError")
    assert failure.original_error.args == ("injected selected-route crash",)
    assert evidence.freeze_attestation.selected_route.value == "FALLBACK"
    assert evidence.closure_class == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert evidence.closure_code == "PROTOCOL_FAILURE"

    forged = replace(evidence, decision_result=object())
    with pytest.raises(
        Phase3ERunnerV1Error,
        match="lacks route-decision semantic authority",
    ):
        verify_failed_route_evidence_v1(
            forged,
            registry=registry,
            comparison_profile=profile,
        )


def test_forbidden_access_retains_violation_and_reconciled_native_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared, registry, profile = _prepared(monkeypatch)

    def violating_executor(_prepared, controller, recorder):
        _record_one_ground_step(controller, recorder)
        controller.record(
            AccessOperation.LOCAL_SLICE_MATERIALIZATION,
            AccessRouteScope.LOCAL,
        )
        raise AssertionError("controller must raise before this line")

    with pytest.raises(Phase3ERouteExecutionFailedV1) as caught:
        run_phase3e(
            prepared,
            local_executor=_forbidden_local,
            fallback_executor=violating_executor,
            registry=registry,
            comparison_profile=profile,
        )
    evidence = caught.value.evidence
    assert evidence.original_error_classification is (
        FailedRouteErrorClassV1.ACCESS_PROTOCOL_FAILURE
    )
    assert evidence.forbidden_access_violation is not None
    assert evidence.forbidden_access_violation.access_event_log_id == (
        evidence.access_log.access_event_log_id
    )
    assert evidence.access_native_reconciliation_status is (
        AccessNativeReconciliationStatusV1.RECONCILED
    )
    assert evidence.partial_route_work.work_vector.value(
        "fallback.ground_steps"
    ) == 1
    verify_failed_route_evidence_v1(
        evidence,
        registry=registry,
        comparison_profile=profile,
    )


def test_fallback_protocol_error_preserves_executor_owned_partial_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared, registry, profile = _prepared(monkeypatch)

    def owned_failure(_prepared, controller, _injected_recorder):
        controller.record(
            AccessOperation.FALLBACK_SOLVER_INVOCATION,
            AccessRouteScope.FALLBACK,
        )
        controller.record(
            AccessOperation.KERNEL_STEP,
            AccessRouteScope.FALLBACK,
        )
        controller.record(
            AccessOperation.GROUND_OUTCOME_ENUMERATION,
            AccessRouteScope.FALLBACK,
        )
        owned = NativeCounterRecorderV1(
            subject_id=prepared.context.route_attempt_id,
            route_kind=RouteKindEnum.DIRECT_FALLBACK,
            work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            registry=registry,
            comparison_profile=profile,
            recorder_id="phase3e-owned-fallback-partial-v1",
        )
        owned.add("fallback.ground_steps", 1)
        owned.record_solver_completion(success=False)
        owned.record_route_completion(success=False)
        protocol_error = GroundFallbackProtocolError(
            "injected authoritative-kernel protocol failure"
        )
        protocol_error.partial_work_vector = owned.seal().work_vector
        raise protocol_error

    with pytest.raises(Phase3ERouteExecutionFailedV1) as caught:
        run_phase3e(
            prepared,
            local_executor=_forbidden_local,
            fallback_executor=owned_failure,
            registry=registry,
            comparison_profile=profile,
        )
    evidence = caught.value.evidence
    assert evidence.partial_route_work.work_vector.value(
        "fallback.ground_steps"
    ) == 1
    assert evidence.partial_route_work.work_vector.value("route.attempts") == 1
    assert evidence.partial_route_work.work_vector.value("route.failures") == 1
    assert evidence.partial_route_work.work_vector.records[0].recorder_id == (
        "phase3e-owned-fallback-partial-v1"
    )
    assert evidence.access_native_reconciliation_status is (
        AccessNativeReconciliationStatusV1.RECONCILED
    )


def test_reconciliation_mismatch_is_retained_not_silently_repaired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared, registry, profile = _prepared(monkeypatch)

    def interrupted_between_access_and_counter(_prepared, controller, _recorder):
        controller.record(
            AccessOperation.FALLBACK_SOLVER_INVOCATION,
            AccessRouteScope.FALLBACK,
        )
        controller.record(
            AccessOperation.KERNEL_STEP,
            AccessRouteScope.FALLBACK,
        )
        raise RuntimeError("crash before native ground-step observation")

    with pytest.raises(Phase3ERouteExecutionFailedV1) as caught:
        run_phase3e(
            prepared,
            local_executor=_forbidden_local,
            fallback_executor=interrupted_between_access_and_counter,
            registry=registry,
            comparison_profile=profile,
        )
    evidence = caught.value.evidence
    assert evidence.access_native_reconciliation_status is (
        AccessNativeReconciliationStatusV1.MISMATCH
    )
    assert "ground-step counters disagree" in (
        evidence.access_native_reconciliation_error or ""
    )
    assert evidence.partial_route_work.work_vector.value(
        "fallback.ground_steps"
    ) == 0
    verify_failed_route_evidence_v1(
        evidence,
        registry=registry,
        comparison_profile=profile,
    )


def test_failure_evidence_remains_visible_through_occurrence_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared, registry, profile = _prepared(monkeypatch)

    def failed_executor(_prepared, controller, recorder):
        _record_one_ground_step(controller, recorder)
        raise RuntimeError("occurrence-visible crash")

    with pytest.raises(Phase3ERouteExecutionFailedV1) as caught:
        run_phase3e_occurrence_v1(
            prepared,
            local_executor=_forbidden_local,
            fallback_executor=failed_executor,
            registry=registry,
            comparison_profile=profile,
        )
    assert caught.value.evidence.partial_route_work.work_vector.value(
        "fallback.ground_steps"
    ) == 1
    assert caught.value.evidence.context.logical_occurrence_id == (
        prepared.context.logical_occurrence_id
    )


def test_native_recorder_rewrites_only_route_closure_without_double_attempt() -> None:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    recorder = NativeCounterRecorderV1(
        subject_id=_id("attempt-subject"),
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="phase3e-failed-closure-test-v1",
    )
    recorder.add("fallback.ground_steps", 3)
    recorder.record_route_completion(success=True)
    successful = recorder.seal()
    failed = recorder.seal_route_failure()
    assert failed.work_vector.value("fallback.ground_steps") == 3
    assert (
        failed.work_vector.value("route.attempts"),
        failed.work_vector.value("route.successes"),
        failed.work_vector.value("route.failures"),
    ) == (1, 0, 1)
    for old, new in zip(
        successful.work_vector.records,
        failed.work_vector.records,
        strict=True,
    ):
        if old.path not in {"route.attempts", "route.successes", "route.failures"}:
            assert new == old
    verify_recorded_work_v1(
        failed,
        expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
    )


def test_failed_evidence_replay_rejects_route_success_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared, registry, profile = _prepared(monkeypatch)

    def failed_executor(_prepared, controller, recorder):
        _record_one_ground_step(controller, recorder)
        raise RuntimeError("tamper target")

    with pytest.raises(Phase3ERouteExecutionFailedV1) as caught:
        run_phase3e(
            prepared,
            local_executor=_forbidden_local,
            fallback_executor=failed_executor,
            registry=registry,
            comparison_profile=profile,
        )
    evidence = caught.value.evidence
    # Swapping in the pre-failure common prefix is an exact typed object, but
    # it has the wrong route/scope/subject and therefore cannot authorize this
    # failure's accounting.
    attacked = replace(
        evidence,
        partial_route_work=prepared.common_prefix_work,
    )
    with pytest.raises(Exception):
        verify_failed_route_evidence_v1(
            attacked,
            registry=registry,
            comparison_profile=profile,
        )
