from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_occurrence_failure_lifecycle_authority_v1 as failure
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_batched_observer_authority_v1 as batch_test


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-occurrence-failure-lifecycle-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _open(marker: str, *, arm_index: int = 0):
    (
        namespace,
        construction_authority,
        _observer_session,
        batched_session,
        stream,
        private_fixture,
    ) = batch_test._setup(
        "failure-lifecycle-" + marker,
        arm_index=arm_index,
    )
    controller = lifecycle.open_v075_parent_owned_multistage_lifecycle_v1(
        batched_session=batched_session,
        occurrence_id=_id("occurrence-" + marker),
        context_id=stream.context_id,
        arm=worker.V075WorkerArmV1(stream.arm),
        route_cap_profile=worker.V075WorkerCapProfileV1(),
    )
    authority = (
        failure.open_v075_occurrence_failure_lifecycle_authority_v1(
            controller
        )
    )
    return (
        namespace,
        construction_authority,
        private_fixture,
        stream,
        controller,
        authority,
    )


def _work(
    controller,
    *,
    child_exit_code: int | None,
    process_messages_extra: int = 0,
) -> failure.V075OccurrenceFailureActualWorkV1:
    batches = controller.batches
    support_events = sum(
        item.kind
        in {
            lifecycle.V075LifecycleEventKindV1.SUPPORT_FREEZE,
            lifecycle.V075LifecycleEventKindV1.ADAPTIVE_SUPPORT_FREEZE,
        }
        for item in controller.events
    )
    maximum_round = max(
        (item.adaptive_round_index for item in controller.events),
        default=0,
    )
    return failure.V075OccurrenceFailureActualWorkV1(
        process_launches=1,
        child_messages=len(batches) + process_messages_extra,
        parent_messages=len(batches),
        batch_intents=len(batches),
        support_freeze_intents=support_events,
        round_begin_intents=maximum_round,
        accepted_draws=sum(
            item.request.accepted_draw_count for item in batches
        ),
        outcome_aggregates=sum(len(item.outcomes) for item in batches),
        child_bytes_read=128 * (len(batches) + process_messages_extra),
        parent_bytes_written=96 * len(batches),
        protocol_checks=1 + 3 * len(batches),
        host_operational_planner_replays=0,
        child_exit_code=child_exit_code,
    )


def _execution(
    controller,
    terminal_code: failure.V075OccurrenceFailureTerminalCodeV1,
    *,
    child_exit_code: int | None,
    process_messages_extra: int = 0,
):
    return failure.issue_v075_construction_failure_execution_fixture_v1(
        open_lifecycle_binding=controller.open_binding,
        terminal_code=terminal_code,
        actual_work=_work(
            controller,
            child_exit_code=child_exit_code,
            process_messages_extra=process_messages_extra,
        ),
    )


def test_root_only_direct_physical_cap_closes_and_replays_every_batch() -> None:
    (
        _namespace,
        construction_authority,
        private_fixture,
        root_stream,
        controller,
        abort_authority,
    ) = _open("direct-root-cap", arm_index=4)
    assert (
        controller.open_binding.arm
        is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    )
    root_batch = controller.execute_batch_v1(
        stream_identity=root_stream,
        accepted_draw_start=1,
        accepted_draw_count=32,
        accepted_draw_cap=32,
    )
    execution = _execution(
        controller,
        (
            failure.V075OccurrenceFailureTerminalCodeV1
            .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED
        ),
        child_exit_code=0,
        process_messages_extra=1,
    )
    sealed = abort_authority.close_construction_v1(
        authority=construction_authority,
        private_environment=private_fixture,
        execution_evidence=execution,
        abort_stage="DIRECT_ROOT_DISCOVERY",
    )
    closure = sealed.closure
    assert closure.batches == (root_batch,)
    assert closure.events == controller.events
    assert closure.aggregate_support_evidence == ()
    assert len(closure.public_verifications) == 1
    assert len(closure.sequence_verifications) == 1
    assert len(closure.private_replay_verifications) == 1
    assert closure.underlying_closure.entries == ()
    assert (
        closure.terminal_code
        is failure.V075OccurrenceFailureTerminalCodeV1
        .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED
    )
    document = closure.to_document()
    assert document["terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert document["scientific_plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert document["missing_work_inferred_as_zero"] is False
    assert document["all_emitted_public_batches_retained"] is True
    assert document["all_work_and_result_references_retained"] is True
    assert len(execution.references) == 2
    replayed = (
        failure.verify_v075_construction_occurrence_failure_lifecycle_v1(
            closure=closure,
            authority=construction_authority,
            private_environment=private_fixture,
        )
    )
    assert replayed == sealed.verification
    assert replayed.accepted_draw_count == 32
    assert batch_test._SHARED_SALT.hex() not in (
        closure.canonical_bytes.decode("utf-8")
    )


@pytest.mark.parametrize(
    ("terminal_code", "abort_stage", "exit_code"),
    (
        (
            failure.V075OccurrenceFailureTerminalCodeV1.PROTOCOL_FAILURE,
            "PROTOCOL_HANDSHAKE",
            None,
        ),
        (
            failure.V075OccurrenceFailureTerminalCodeV1.PROCESS_FAILURE,
            "PROCESS_SUPERVISION",
            17,
        ),
        (
            failure.V075OccurrenceFailureTerminalCodeV1.TIMEOUT,
            "PROCESS_WAIT",
            None,
        ),
    ),
)
def test_zero_observation_failures_close_as_distinct_noncertificates(
    terminal_code,
    abort_stage,
    exit_code,
) -> None:
    marker = terminal_code.value.lower()
    (
        _namespace,
        construction_authority,
        private_fixture,
        _stream,
        controller,
        abort_authority,
    ) = _open(marker)
    execution = _execution(
        controller,
        terminal_code,
        child_exit_code=exit_code,
        process_messages_extra=1,
    )
    sealed = abort_authority.close_construction_v1(
        authority=construction_authority,
        private_environment=private_fixture,
        execution_evidence=execution,
        abort_stage=abort_stage,
    )
    assert sealed.closure.batches == ()
    assert sealed.closure.events == ()
    assert sealed.closure.public_verifications == ()
    assert sealed.closure.sequence_verifications == ()
    assert sealed.closure.private_replay_verifications == ()
    assert sealed.closure.terminal_code is terminal_code
    assert sealed.verification.terminal_code is terminal_code
    replayed = (
        failure.verify_v075_construction_occurrence_failure_lifecycle_v1(
            closure=sealed.closure,
            authority=construction_authority,
            private_environment=private_fixture,
        )
    )
    assert replayed == sealed.verification


def test_frozen_support_and_every_completed_batch_survive_protocol_abort() -> None:
    (
        _namespace,
        construction_authority,
        private_fixture,
        stream,
        controller,
        abort_authority,
    ) = _open("support-prefix")
    first = controller.execute_batch_v1(
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=16,
        accepted_draw_cap=32,
    )
    second = controller.execute_batch_v1(
        stream_identity=stream,
        accepted_draw_start=17,
        accepted_draw_count=16,
        accepted_draw_cap=32,
    )
    selected = min(second.outcomes, key=lambda item: item.outcome_id)
    evidence = controller.freeze_aggregate_support_evidence_v1(
        discovery_batch=second,
        selected_outcome_ids=(selected.outcome_id,),
    )
    execution = _execution(
        controller,
        failure.V075OccurrenceFailureTerminalCodeV1.PROTOCOL_FAILURE,
        child_exit_code=None,
        process_messages_extra=1,
    )
    sealed = abort_authority.close_construction_v1(
        authority=construction_authority,
        private_environment=private_fixture,
        execution_evidence=execution,
        abort_stage="SUPPORT_REGISTRATION",
    )
    assert sealed.closure.batches == (first, second)
    assert sealed.closure.aggregate_support_evidence == evidence
    assert len(sealed.closure.sequence_verifications) == 1
    assert (
        sealed.closure.sequence_verifications[0].accepted_draw_count == 32
    )
    assert len(sealed.closure.private_replay_verifications) == 2
    assert (
        failure.verify_v075_construction_occurrence_failure_lifecycle_v1(
            closure=sealed.closure,
            authority=construction_authority,
            private_environment=private_fixture,
        )
        == sealed.verification
    )


def test_double_close_and_success_close_after_abort_fail_closed() -> None:
    (
        _namespace,
        construction_authority,
        private_fixture,
        _stream,
        controller,
        abort_authority,
    ) = _open("double-close")
    execution = _execution(
        controller,
        failure.V075OccurrenceFailureTerminalCodeV1.PROTOCOL_FAILURE,
        child_exit_code=None,
    )
    abort_authority.close_construction_v1(
        authority=construction_authority,
        private_environment=private_fixture,
        execution_evidence=execution,
        abort_stage="PROTOCOL_HANDSHAKE",
    )
    with pytest.raises(
        failure.V075OccurrenceFailureLifecycleInvariantViolation,
        match="closed",
    ):
        abort_authority.close_construction_v1(
            authority=construction_authority,
            private_environment=private_fixture,
            execution_evidence=execution,
            abort_stage="PROTOCOL_HANDSHAKE",
        )
    with pytest.raises(ValueError, match="closed"):
        controller.close_construction_v1(
            authority=construction_authority,
            private_environment=private_fixture,
            process_launches=1,
            child_intent_count=0,
            terminal_code=(
                lifecycle.V075LifecycleTerminalCodeV1
                .NONCERTIFICATE_PROTOCOL_CLOSED
            ),
        )
    with pytest.raises(
        failure.V075OccurrenceFailureLifecycleInvariantViolation,
        match="open controller",
    ):
        failure.open_v075_occurrence_failure_lifecycle_authority_v1(
            controller
        )


def test_transplant_tamper_and_underreported_work_are_rejected() -> None:
    (
        _namespace_a,
        authority_a,
        private_a,
        stream_a,
        controller_a,
        abort_a,
    ) = _open("attack-a", arm_index=4)
    controller_a.execute_batch_v1(
        stream_identity=stream_a,
        accepted_draw_start=1,
        accepted_draw_count=8,
        accepted_draw_cap=8,
    )
    execution_a = _execution(
        controller_a,
        (
            failure.V075OccurrenceFailureTerminalCodeV1
            .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED
        ),
        child_exit_code=0,
    )
    sealed_a = abort_a.close_construction_v1(
        authority=authority_a,
        private_environment=private_a,
        execution_evidence=execution_a,
        abort_stage="DIRECT_ROOT_DISCOVERY",
    )
    (
        _namespace_b,
        authority_b,
        private_b,
        _stream_b,
        _controller_b,
        _abort_b,
    ) = _open("attack-b", arm_index=4)
    with pytest.raises(Exception):
        failure.verify_v075_construction_occurrence_failure_lifecycle_v1(
            closure=sealed_a.closure,
            authority=authority_b,
            private_environment=private_b,
        )
    with pytest.raises(
        failure.V075OccurrenceFailureLifecycleInvariantViolation,
        match="signature",
    ):
        replace(sealed_a.closure, abort_stage="DIRECT_ROOT_ATTACK")

    (
        _namespace_c,
        authority_c,
        private_c,
        stream_c,
        controller_c,
        abort_c,
    ) = _open("underreported", arm_index=4)
    controller_c.execute_batch_v1(
        stream_identity=stream_c,
        accepted_draw_start=1,
        accepted_draw_count=8,
        accepted_draw_cap=8,
    )
    incomplete_work = failure.V075OccurrenceFailureActualWorkV1(
        process_launches=1,
        child_messages=1,
        parent_messages=1,
        batch_intents=1,
        support_freeze_intents=0,
        round_begin_intents=0,
        accepted_draws=0,
        outcome_aggregates=0,
        child_bytes_read=64,
        parent_bytes_written=64,
        protocol_checks=1,
        host_operational_planner_replays=0,
        child_exit_code=0,
    )
    incomplete_execution = (
        failure.issue_v075_construction_failure_execution_fixture_v1(
            open_lifecycle_binding=controller_c.open_binding,
            terminal_code=(
                failure.V075OccurrenceFailureTerminalCodeV1
                .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED
            ),
            actual_work=incomplete_work,
        )
    )
    with pytest.raises(
        failure.V075OccurrenceFailureLifecycleInvariantViolation,
        match="omits",
    ):
        abort_c.close_construction_v1(
            authority=authority_c,
            private_environment=private_c,
            execution_evidence=incomplete_execution,
            abort_stage="DIRECT_ROOT_DISCOVERY",
        )


def test_production_entrypoints_exist_but_construction_does_not_open_target() -> None:
    assert failure.TARGET_EXECUTION_OPENED is False
    assert failure.PLAN_CERTIFICATE_ALLOWED is False
    assert failure.INFEASIBILITY_CERTIFICATE_ALLOWED is False
    (
        namespace,
        _construction_authority,
        _private_fixture,
        _stream,
        controller,
        abort_authority,
    ) = _open("production-separation")
    with pytest.raises(
        failure.V075OccurrenceFailureLifecycleInvariantViolation,
        match="production IPC",
    ):
        failure.freeze_v075_production_failure_execution_evidence_v1(
            ipc_result=object(),
            controller=controller,
        )
    execution = _execution(
        controller,
        failure.V075OccurrenceFailureTerminalCodeV1.PROTOCOL_FAILURE,
        child_exit_code=None,
    )
    with pytest.raises(
        failure.V075OccurrenceFailureLifecycleInvariantViolation,
        match="production failure close",
    ):
        abort_authority.close_production_v1(
            authority=object(),
            namespace=namespace,
            private_salt=b"x" * 32,
            private_environment=object(),
            execution_evidence=execution,
            abort_stage="PROTOCOL_HANDSHAKE",
        )
