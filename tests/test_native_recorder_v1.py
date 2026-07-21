from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    RouteKindEnum,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import (
    NativeCounterRecorderV1,
    NativeRecorderV1Error,
    derive_recorded_work_v1,
    verify_recorded_work_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_recorder_emits_explicit_native_zeroes_and_exact_projection() -> None:
    recorder = NativeCounterRecorderV1(
        subject_id=_id("fallback-attempt"),
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    )
    recorder.add("fallback.ground_steps", 3)
    recorder.add("fallback.actions_evaluated", 4)
    recorder.observe_peak("memory.working_bytes_peak", 20)
    recorder.observe_peak("memory.working_bytes_peak", 10)
    recorder.record_solver_completion(success=True)
    recorder.record_process_completion(success=True)
    recorder.record_route_completion(success=True)

    work = recorder.seal()
    assert work.work_vector.value("fallback.ground_steps") == 3
    assert work.work_vector.value("local.materialization_ground_steps") == 0
    assert all(record.observed for record in work.work_vector.records)
    assert (
        "local.materialization_ground_steps"
        in work.native_zero_attestation.zero_paths
    )
    assert work.work_vector.value("route.attempts") == 1
    assert work.work_vector.value("route.successes") == 1
    assert work.work_vector.value("process.launches") == 1
    assert work.comparison_vector.value(KERNEL_TRANSITION_CALLS) == 3
    assert work.comparison_vector.value(NONKERNEL_COMPUTE_EVENTS) == 4
    assert work.comparison_vector.value("peak_working_bytes") == 20
    assert (
        work.actual_projection_proof.work_scope
        is ActualWorkScope.MARGINAL_ROUTE_EXECUTION
    )
    with pytest.raises(NativeRecorderV1Error, match="already sealed"):
        recorder.add("fallback.ground_steps")


@pytest.mark.parametrize(
    ("route_kind", "scope", "forbidden"),
    (
        (
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            ActualWorkScope.COMMON_PREFIX,
            "local.causal_candidate_evaluations",
        ),
        (
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            ActualWorkScope.COMMON_PREFIX,
            "fallback.states_expanded",
        ),
        (
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            ActualWorkScope.COMMON_PREFIX,
            "local.materialization_ground_steps",
        ),
        (
            RouteKindEnum.LOCAL_ATTEMPT,
            ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            "common.protocol_checks",
        ),
        (
            RouteKindEnum.LOCAL_ATTEMPT,
            ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            "fallback.states_expanded",
        ),
        (
            RouteKindEnum.DIRECT_FALLBACK,
            ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            "local.solver_policy_assignments",
        ),
        (
            RouteKindEnum.REBUILD,
            ActualWorkScope.REBUILD_EXECUTION,
            "control.cap_checks",
        ),
    ),
)
def test_recorder_rejects_cross_scope_work_at_observation_time(
    route_kind: RouteKindEnum,
    scope: ActualWorkScope,
    forbidden: str,
) -> None:
    recorder = NativeCounterRecorderV1(
        subject_id=_id(f"{route_kind.value}-subject"),
        route_kind=route_kind,
        work_scope=scope,
    )
    with pytest.raises(NativeRecorderV1Error, match="belongs outside"):
        recorder.add(forbidden)


def test_route_scope_and_kind_cannot_be_mixed() -> None:
    with pytest.raises(NativeRecorderV1Error, match="cannot be recorded"):
        NativeCounterRecorderV1(
            subject_id=_id("bad-scope"),
            route_kind=RouteKindEnum.LOCAL_ATTEMPT,
            work_scope=ActualWorkScope.COMMON_PREFIX,
        )


def test_failed_abstract_prefix_is_accounted_without_certificate_route_kind() -> None:
    recorder = NativeCounterRecorderV1(
        subject_id=_id("failed-abstract-attempt"),
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
    )
    recorder.add("common.abstract_bellman_backups", 5)
    recorder.add("common.abstract_audit_obligations", 2)
    recorder.add("local.causal_candidate_evaluations", 4)
    recorder.record_solver_completion(success=True)
    recorder.record_process_completion(success=True)
    recorder.record_route_completion(success=True)
    work = recorder.seal()

    assert work.work_vector.route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
    assert work.actual_projection_proof.work_scope is ActualWorkScope.COMMON_PREFIX
    assert work.work_vector.value("common.abstract_bellman_backups") == 5
    assert work.work_vector.value("local.causal_candidate_evaluations") == 4
    assert all(
        value == 0
        for path, value in work.work_vector.values.items()
        if path.startswith(("local.", "fallback.", "rebuild."))
        and path != "local.causal_candidate_evaluations"
    )


def test_unknown_generic_counter_and_wrong_reducer_fail_closed() -> None:
    recorder = NativeCounterRecorderV1(
        subject_id=_id("local"),
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    )
    with pytest.raises(NativeRecorderV1Error, match="unknown"):
        recorder.add("solver.magic_events")
    with pytest.raises(NativeRecorderV1Error, match="use observe_peak"):
        recorder.add("memory.working_bytes_peak")
    with pytest.raises(NativeRecorderV1Error, match="use add"):
        recorder.observe_peak("local.materialization_ground_steps", 1)


def test_postfreeze_common_verification_uses_its_own_suffix_scope() -> None:
    recorder = NativeCounterRecorderV1(
        subject_id=_id("fallback-suffix"),
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
    )
    recorder.add("common.protocol_checks", 2)
    recorder.add("common.hash_invocations", 1)
    result = recorder.seal()
    assert result.work_vector.value("common.protocol_checks") == 2
    assert result.work_vector.value("fallback.ground_steps") == 0
    assert (
        result.actual_projection_proof.work_scope
        is ActualWorkScope.MARGINAL_ROUTE_VERIFICATION
    )


def test_verification_suffix_cannot_borrow_route_execution_work() -> None:
    recorder = NativeCounterRecorderV1(
        subject_id=_id("fallback-verification"),
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
    )
    with pytest.raises(NativeRecorderV1Error, match="belongs outside"):
        recorder.add("fallback.ground_steps")


def test_aggregate_scope_can_only_be_derived_not_recorded_directly() -> None:
    with pytest.raises(NativeRecorderV1Error, match="cannot be recorded"):
        NativeCounterRecorderV1(
            subject_id=_id("forged-aggregate"),
            route_kind=RouteKindEnum.DIRECT_FALLBACK,
            work_scope=ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
        )


def test_exact_executor_owned_vector_can_be_adapted_without_counter_copy() -> None:
    recorder = NativeCounterRecorderV1(
        subject_id=_id("owned-fallback"),
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    )
    recorder.add("fallback.ground_steps", 2)
    recorder.record_route_completion(success=True)
    owned = recorder.seal()
    replayed = derive_recorded_work_v1(
        owned.work_vector,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    )
    assert replayed == owned
    assert verify_recorded_work_v1(
        replayed,
        expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    ) == replayed

    forged = replace(
        replayed,
        native_zero_attestation=replace(
            replayed.native_zero_attestation,
            work_vector_id=_id("foreign-vector"),
        ),
    )
    with pytest.raises(NativeRecorderV1Error, match="does not replay"):
        verify_recorded_work_v1(
            forged,
            expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        )
