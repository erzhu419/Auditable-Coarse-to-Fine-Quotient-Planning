from __future__ import annotations

import copy
import hashlib
from dataclasses import replace

import pytest

from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    RouteKindEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.campaign_v1 import (
    COUNTER_COMPLETENESS_GATE_NOT_RUN,
    WORKLOAD_ECONOMICS_GATE_NOT_RUN,
    LogicalOccurrenceV1,
    RebuildPolicyV1,
    RouteAttemptV1,
)
from acfqp.native_recorder_v1 import NativeCounterRecorderV1, RecordedWorkV1
from acfqp.phase3e_rebuild_runner_v1 import (
    BOUNDED_REBUILD_RUNNER_BLOCKERS,
    BOUNDED_REBUILD_RUNNER_STATUS,
    AttemptExecutionReceiptV1,
    BoundedRebuildOccurrenceRunV1,
    BoundedRebuildOccurrenceWorkSumV1,
    Phase3EBoundedRebuildRunnerV1Error,
    RebuildExecutionReceiptV1,
    RegisteredRebuildCallbackV1,
    run_bounded_rebuild_retry_v1,
)
from acfqp.routing_v1 import (
    RouteDecisionContextV1,
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    semantic_verifier_spec_v1,
)
import acfqp.semantic_verification_v1 as semantic_verification


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:bounded-rebuild-runner-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def _occurrence(policy: RebuildPolicyV1, label: str = "main") -> LogicalOccurrenceV1:
    return LogicalOccurrenceV1(
        _id(f"workload-{label}"),
        _id("protocol"),
        1,
        _id(f"structural-{label}"),
        _id(f"query-{label}"),
        _id(f"plan-{label}"),
        _id("threshold"),
        _id(f"epoch-{label}-1"),
        policy.rebuild_policy_id,
    )


def _attempt_work(
    attempt: RouteAttemptV1,
    *,
    code: TerminalCode,
    label: str,
) -> RecordedWorkV1:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    if code is TerminalCode.REBUILD_REQUIRED:
        recorder = NativeCounterRecorderV1(
            subject_id=_id(f"transaction-{label}"),
            route_kind=RouteKindEnum.LOCAL_ATTEMPT,
            work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            registry=registry,
            comparison_profile=profile,
            recorder_id=f"bounded-attempt-{label}-native-v1",
        )
        recorder.add("local.postaudit_ground_steps", 1)
    else:
        recorder = NativeCounterRecorderV1(
            subject_id=attempt.route_attempt_id,
            route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            work_scope=ActualWorkScope.COMMON_PREFIX,
            registry=registry,
            comparison_profile=profile,
            recorder_id=f"bounded-attempt-{label}-native-v1",
        )
        recorder.add("common.protocol_checks", 1)
    return recorder.seal()


def _terminal_result(
    occurrence: LogicalOccurrenceV1,
    attempt: RouteAttemptV1,
    work: RecordedWorkV1,
    *,
    code: TerminalCode,
    label: str,
):
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    context = RouteDecisionContextV1(
        _id(f"preregister-{label}"),
        occurrence.protocol_id,
        profile.comparison_profile_id,
        registry.registry_id,
        occurrence.structural_id,
        occurrence.query_id,
        occurrence.selected_plan_id,
        occurrence.threshold_profile_id,
        attempt.build_epoch_id,
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
    )
    decision = _id(f"decision-{label}")
    transaction = (
        _id(f"transaction-{label}")
        if code is TerminalCode.REBUILD_REQUIRED
        else TypedNotApplicable("attempt terminal has no local transaction")
    )
    binding = AttestationContextV1(
        context,
        decision,
        transaction,
        30,
        LaneEnum.EVALUATION,
    )
    class_by_code = {
        TerminalCode.REBUILD_REQUIRED: (
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
        TerminalCode.PROTOCOL_FAILURE: (
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: (
            TerminalClass.INFEASIBILITY_CERTIFICATE
        ),
    }
    evidence = (_id(f"evidence-{label}"),)
    terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        class_by_code[code],
        code,
        context.route_decision_context_id,
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        decision,
        transaction,
        work.work_vector.work_vector_id,
        evidence,
    )
    spec = semantic_verifier_spec_v1(SemanticRole.TERMINAL_CLASSIFICATION)
    record = CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(LaneEnum.EVALUATION),
        1,
        recorder_id=f"bounded-terminal-{label}-semantic-v1",
    )
    # The fixture mints the same live opaque authority returned by the public
    # terminal verifier.  Tests here target orchestration, not the already
    # covered terminal evidence matrix.
    return semantic_verification._finish(
        artifact=terminal,
        artifact_id=terminal.terminal_artifact_id,
        spec=spec,
        outcome=terminal.terminal_class.value,
        binding=binding,
        work=record,
        recomputed_evidence_ids=evidence,
    )


def _rebuild_work(epoch_id: str, label: str = "rebuild") -> RecordedWorkV1:
    recorder = NativeCounterRecorderV1(
        subject_id=epoch_id,
        route_kind=RouteKindEnum.REBUILD,
        work_scope=ActualWorkScope.REBUILD_EXECUTION,
        recorder_id=f"bounded-{label}-native-v1",
    )
    recorder.add("rebuild.ground_steps", 2)
    recorder.add("rebuild.outcome_rows", 3)
    recorder.add("rebuild.partition_candidate_evaluations", 1)
    recorder.add("io.output_bytes", 128)
    return recorder.seal()


def _initial(
    occurrence: LogicalOccurrenceV1,
    *,
    code: TerminalCode = TerminalCode.REBUILD_REQUIRED,
    label: str = "first",
):
    attempt = RouteAttemptV1.initial(occurrence)
    work = _attempt_work(attempt, code=code, label=label)
    terminal = _terminal_result(
        occurrence, attempt, work, code=code, label=label
    )
    return attempt, work, terminal


def test_authorized_rebuild_runs_once_and_retains_one_occurrence_denominator() -> None:
    recipe = _id("recipe")
    policy = RebuildPolicyV1.allowing_one(recipe)
    occurrence = _occurrence(policy)
    _, first_work, first_terminal = _initial(occurrence)
    calls = {"rebuild": 0, "retry": 0}

    def rebuild(invocation):
        calls["rebuild"] += 1
        assert invocation.rebuild_recipe_id == recipe
        assert invocation.source_attempt.route_attempt_index == 1
        epoch = _id("epoch-main-2")
        return RebuildExecutionReceiptV1(epoch, _rebuild_work(epoch))

    def retry(attempt):
        calls["retry"] += 1
        assert attempt.route_attempt_index == 2
        assert attempt.build_epoch_id == _id("epoch-main-2")
        work = _attempt_work(
            attempt, code=TerminalCode.PROTOCOL_FAILURE, label="second"
        )
        terminal = _terminal_result(
            occurrence,
            attempt,
            work,
            code=TerminalCode.PROTOCOL_FAILURE,
            label="second",
        )
        return AttemptExecutionReceiptV1(terminal, (work,))

    result = run_bounded_rebuild_retry_v1(
        occurrence,
        policy,
        first_terminal,
        (first_work,),
        rebuild_callback=RegisteredRebuildCallbackV1(recipe, rebuild),
        retry_callback=retry,
    )

    assert calls == {"rebuild": 1, "retry": 1}
    assert len(result.attempts) == 2
    assert result.attempts[0].route_attempt_index == 1
    assert result.attempts[1].route_attempt_index == 2
    assert result.attempts[1].predecessor_route_attempt_id == (
        result.attempts[0].route_attempt_id
    )
    assert result.rebuild_event.rebuild_attempt_index == 1
    assert result.closure.closure_denominator_included is True
    assert result.closure.certification_denominator_included is True
    assert result.closure.economics_denominator_included is True
    assert len(result.closure.attempts) == 2
    assert result.closure.final_terminal_code is TerminalCode.PROTOCOL_FAILURE
    assert result.closure.certificate_covered is False
    assert result.closure.rebuild_work_vector_ids == (
        result.rebuild_receipt.work.work_vector.work_vector_id,
    )
    assert tuple(row.component_kind for row in result.occurrence_work_sum.components) == (
        "ATTEMPT",
        "REBUILD",
        "ATTEMPT",
    )
    assert BoundedRebuildOccurrenceWorkSumV1.from_dict(
        result.occurrence_work_sum.to_dict()
    ) == result.occurrence_work_sum
    assert result.status == BOUNDED_REBUILD_RUNNER_STATUS
    assert result.blockers == BOUNDED_REBUILD_RUNNER_BLOCKERS
    assert result.official_execution_allowed is False
    assert result.official_scalar_cost is None
    assert result.official_N_break_even is None
    assert result.workload_economics_gate_status == WORKLOAD_ECONOMICS_GATE_NOT_RUN
    assert (
        result.counter_completeness_gate_status
        == COUNTER_COMPLETENESS_GATE_NOT_RUN
    )


def test_disabled_rebuild_closes_required_terminal_without_calling_callbacks() -> None:
    policy = RebuildPolicyV1()
    occurrence = _occurrence(policy, "disabled")
    _, work, terminal = _initial(occurrence, label="disabled-first")
    calls = 0

    def forbidden(_):
        nonlocal calls
        calls += 1
        raise AssertionError("disabled rebuild callback must not run")

    result = run_bounded_rebuild_retry_v1(
        occurrence,
        policy,
        terminal,
        (work,),
        rebuild_callback=None,
        retry_callback=forbidden,
    )
    assert calls == 0
    assert len(result.attempts) == 1
    assert result.rebuild_event is None
    assert result.closure.final_terminal_code is TerminalCode.REBUILD_REQUIRED
    assert result.closure.certificate_covered is False
    assert result.closure.closure_denominator_included is True


def test_non_rebuild_terminal_never_invokes_registered_rebuild() -> None:
    recipe = _id("non-rebuild-recipe")
    policy = RebuildPolicyV1.allowing_one(recipe)
    occurrence = _occurrence(policy, "non-rebuild")
    _, work, terminal = _initial(
        occurrence,
        code=TerminalCode.PROTOCOL_FAILURE,
        label="non-rebuild-first",
    )
    calls = 0

    def forbidden(_):
        nonlocal calls
        calls += 1
        raise AssertionError("non-REBUILD terminal must not run callback")

    result = run_bounded_rebuild_retry_v1(
        occurrence,
        policy,
        terminal,
        (work,),
        rebuild_callback=RegisteredRebuildCallbackV1(recipe, forbidden),
        retry_callback=forbidden,
    )
    assert calls == 0
    assert len(result.attempts) == 1
    assert result.closure.final_terminal_code is TerminalCode.PROTOCOL_FAILURE


def test_foreign_recipe_is_rejected_before_callback() -> None:
    recipe = _id("registered-recipe")
    policy = RebuildPolicyV1.allowing_one(recipe)
    occurrence = _occurrence(policy, "foreign-recipe")
    _, work, terminal = _initial(occurrence, label="foreign-recipe-first")
    calls = 0

    def rebuild(_):
        nonlocal calls
        calls += 1
        raise AssertionError("foreign recipe callback must not run")

    with pytest.raises(
        Phase3EBoundedRebuildRunnerV1Error, match="foreign recipe"
    ):
        run_bounded_rebuild_retry_v1(
            occurrence,
            policy,
            terminal,
            (work,),
            rebuild_callback=RegisteredRebuildCallbackV1(
                _id("foreign-recipe"), rebuild
            ),
            retry_callback=lambda _: None,
        )
    assert calls == 0


def test_stale_epoch_and_malformed_rebuild_work_fail_before_retry() -> None:
    recipe = _id("stale-recipe")
    policy = RebuildPolicyV1.allowing_one(recipe)
    occurrence = _occurrence(policy, "stale")
    first, work, terminal = _initial(occurrence, label="stale-first")
    retry_calls = 0

    def retry(_):
        nonlocal retry_calls
        retry_calls += 1
        raise AssertionError("invalid rebuild must not run retry")

    stale_work = _rebuild_work(first.build_epoch_id, "stale")
    with pytest.raises(
        Phase3EBoundedRebuildRunnerV1Error, match="stale BuildEpoch"
    ):
        run_bounded_rebuild_retry_v1(
            occurrence,
            policy,
            terminal,
            (work,),
            rebuild_callback=RegisteredRebuildCallbackV1(
                recipe,
                lambda _: RebuildExecutionReceiptV1(
                    first.build_epoch_id, stale_work
                ),
            ),
            retry_callback=retry,
        )

    new_epoch = _id("stale-epoch-2")
    wrong_subject_work = _rebuild_work(_id("foreign-epoch"), "foreign-subject")
    with pytest.raises(
        Phase3EBoundedRebuildRunnerV1Error, match="does not bind the new BuildEpoch"
    ):
        run_bounded_rebuild_retry_v1(
            occurrence,
            policy,
            terminal,
            (work,),
            rebuild_callback=RegisteredRebuildCallbackV1(
                recipe,
                lambda _: RebuildExecutionReceiptV1(
                    new_epoch, wrong_subject_work
                ),
            ),
            retry_callback=retry,
        )
    assert retry_calls == 0


def test_foreign_terminal_and_missing_actual_work_fail_before_rebuild() -> None:
    recipe = _id("foreign-terminal-recipe")
    policy = RebuildPolicyV1.allowing_one(recipe)
    occurrence = _occurrence(policy, "target")
    foreign = _occurrence(policy, "foreign")
    _, foreign_work, foreign_terminal = _initial(
        foreign, label="foreign-terminal-first"
    )
    callback_calls = 0

    def rebuild(_):
        nonlocal callback_calls
        callback_calls += 1
        raise AssertionError("foreign terminal must not run rebuild")

    with pytest.raises(
        Phase3EBoundedRebuildRunnerV1Error, match="foreign or stale"
    ):
        run_bounded_rebuild_retry_v1(
            occurrence,
            policy,
            foreign_terminal,
            (foreign_work,),
            rebuild_callback=RegisteredRebuildCallbackV1(recipe, rebuild),
            retry_callback=lambda _: None,
        )
    assert callback_calls == 0

    _, actual_work, terminal = _initial(occurrence, label="target-first")
    other_attempt = RouteAttemptV1.initial(occurrence)
    other_work = _attempt_work(
        other_attempt, code=TerminalCode.PROTOCOL_FAILURE, label="unrelated-work"
    )
    with pytest.raises(
        Phase3EBoundedRebuildRunnerV1Error, match="omitted the terminal actual"
    ):
        run_bounded_rebuild_retry_v1(
            occurrence,
            policy,
            terminal,
            (other_work,),
            rebuild_callback=RegisteredRebuildCallbackV1(recipe, rebuild),
            retry_callback=lambda _: None,
        )
    assert actual_work.work_vector.work_vector_id != other_work.work_vector.work_vector_id
    assert callback_calls == 0


def test_retry_rebuild_required_exhausts_budget_as_noncertificate_not_infeasible() -> None:
    recipe = _id("exhaust-recipe")
    policy = RebuildPolicyV1.allowing_one(recipe)
    occurrence = _occurrence(policy, "exhaust")
    _, first_work, first_terminal = _initial(occurrence, label="exhaust-first")
    retry_calls = 0

    def rebuild(_):
        epoch = _id("epoch-exhaust-2")
        return RebuildExecutionReceiptV1(epoch, _rebuild_work(epoch, "exhaust"))

    def retry(attempt):
        nonlocal retry_calls
        retry_calls += 1
        work = _attempt_work(
            attempt, code=TerminalCode.REBUILD_REQUIRED, label="exhaust-second"
        )
        terminal = _terminal_result(
            occurrence,
            attempt,
            work,
            code=TerminalCode.REBUILD_REQUIRED,
            label="exhaust-second",
        )
        return AttemptExecutionReceiptV1(terminal, (work,))

    result = run_bounded_rebuild_retry_v1(
        occurrence,
        policy,
        first_terminal,
        (first_work,),
        rebuild_callback=RegisteredRebuildCallbackV1(recipe, rebuild),
        retry_callback=retry,
    )
    assert retry_calls == 1
    assert len(result.attempts) == 2
    assert result.closure.final_terminal_code is TerminalCode.REBUILD_REQUIRED
    assert result.closure.final_terminal_class is (
        TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
    )
    assert result.closure.certificate_covered is False


def test_result_cannot_hide_gate_blockers_or_relabel_noncertificate() -> None:
    policy = RebuildPolicyV1()
    occurrence = _occurrence(policy, "gate-lock")
    _, work, terminal = _initial(occurrence, label="gate-lock-first")
    result = run_bounded_rebuild_retry_v1(
        occurrence, policy, terminal, (work,)
    )
    with pytest.raises(
        Phase3EBoundedRebuildRunnerV1Error, match="cannot hide"
    ):
        replace(result, blockers=())
    with pytest.raises(
        Phase3EBoundedRebuildRunnerV1Error, match="cannot hide"
    ):
        replace(result, official_execution_allowed=True)
    tampered = copy.deepcopy(result.occurrence_work_sum.to_dict())
    tampered["bounded_rebuild_occurrence_work_sum_id"] = "0" * 64
    with pytest.raises(
        Phase3EBoundedRebuildRunnerV1Error, match="content ID mismatch"
    ):
        BoundedRebuildOccurrenceWorkSumV1.from_dict(tampered)

    extra_axis_field = copy.deepcopy(result.occurrence_work_sum.to_dict())
    extra_axis_field["aggregate_values"][0]["forged"] = 0
    with pytest.raises(
        Phase3EBoundedRebuildRunnerV1Error, match="aggregate axis"
    ):
        BoundedRebuildOccurrenceWorkSumV1.from_dict(extra_axis_field)

    mixed_component = copy.deepcopy(result.occurrence_work_sum.to_dict())
    mixed_component["components"][0]["work_scope"] = (
        ActualWorkScope.REBUILD_EXECUTION.value
    )
    with pytest.raises(
        Phase3EBoundedRebuildRunnerV1Error, match="kind, route kind, and work scope"
    ):
        BoundedRebuildOccurrenceWorkSumV1.from_dict(mixed_component)
