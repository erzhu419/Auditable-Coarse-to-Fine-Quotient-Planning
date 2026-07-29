from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
from types import SimpleNamespace

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_independent_exact_ground_evaluator_v1 as evaluator
from acfqp import (
    v072_registered_campaign_attempt_journal_v1 as attempt_journal,
)
from acfqp import (
    v072_registered_matched_direct_complete_inventory_v1 as inventory,
)
from acfqp import v072_registered_matched_direct_runtime_v1 as runtime


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _placeholder() -> observer.TargetExecutionAnchorPlaceholderV1:
    return observer.bind_target_execution_anchor_placeholder_v1(
        prereg.freeze_transfer_guided_acquisition_preregistration_v1(),
        remote_main_commit_sha="1" * 40,
        remote_main_containment_attestation_id=_id(
            "registered-direct-placeholder"
        ),
    )


def _checkpoint_prefix(
    *,
    checkpoint: int,
    row_keys: tuple[str, ...],
    previous: dict[str, runtime.RegistrationDisjointDirectRowPrefixV1],
) -> tuple[runtime.RegistrationDisjointDirectRowPrefixV1, ...]:
    output = tuple(
        runtime.RegistrationDisjointDirectRowPrefixV1(
            row_key,
            checkpoint,
            (
                None
                if checkpoint == runtime.CHECKPOINTS[0]
                else previous[row_key].prefix_id
            ),
            runtime.DISCOVERY_DRAWS_PER_ROW + checkpoint,
        )
        for row_key in row_keys
    )
    previous.update({item.row_key: item for item in output})
    return output


def _checkpoints(
    statuses: tuple[
        runtime.RegistrationDisjointDirectCheckpointStatusV1,
        ...,
    ],
    *,
    row_keys: tuple[str, ...] = (
        "SYNTHETIC_DISJOINT_ROW_A",
        "SYNTHETIC_DISJOINT_ROW_B",
    ),
) -> tuple[runtime.RegistrationDisjointDirectCheckpointV1, ...]:
    previous: dict[
        str,
        runtime.RegistrationDisjointDirectRowPrefixV1,
    ] = {}
    return tuple(
        runtime.RegistrationDisjointDirectCheckpointV1(
            checkpoint,
            _checkpoint_prefix(
                checkpoint=checkpoint,
                row_keys=row_keys,
                previous=previous,
            ),
            status,
        )
        for checkpoint, status in zip(
            runtime.CHECKPOINTS[: len(statuses)],
            statuses,
            strict=True,
        )
    )


def test_production_entry_accepts_no_injected_evidence_or_outcome() -> None:
    signature = inspect.signature(
        runtime.run_registered_matched_direct_occurrence_v1
    )
    assert tuple(signature.parameters) == (
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "context",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in signature.parameters.values()
    )
    assert {
        "observer",
        "transcript",
        "law",
        "probabilities",
        "outcomes",
        "status",
        "counts",
        "limits",
        "policy",
        "terminal",
        "callback",
    }.isdisjoint(signature.parameters)


def test_missing_production_dependencies_are_exact_and_ordered() -> None:
    dependency = (
        runtime.inspect_registered_matched_direct_dependency_protocol_v1()
    )
    expected_blockers = (
        (runtime.TERMINAL_ADAPTER_DEPENDENCY_BLOCKER,)
        if runtime.DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED
        else (
            runtime.DIRECT_CHECKPOINT_CAP_PREREG_AMENDMENT_BLOCKER,
            runtime.TERMINAL_ADAPTER_DEPENDENCY_BLOCKER,
        )
    )
    assert dependency.blockers == expected_blockers
    assert dependency.target_accumulator_module == (
        "acfqp.v072_registered_matched_direct_complete_inventory_v1"
    )
    assert dependency.target_accumulator_type == (
        "RegisteredMatchedDirectCompleteInventoryAccumulatorV1"
    )
    assert dependency.target_accumulator_entrypoint == (
        "open_registered_matched_direct_complete_inventory_accumulator_v1"
    )
    assert dependency.direct_inventory_type == (
        "RegisteredMatchedDirectCompleteInventoryCheckpointV1"
    )
    assert dependency.cold_direct_builder_entrypoint.endswith(
        "build_registered_matched_direct_cold_snapshot_v1"
    )
    assert dependency.ground_planner_entrypoint.endswith(
        "solve_exact_lazy_ground_direct_h2_v1"
    )
    assert dependency.evaluator_terminal_factory_entrypoint.endswith(
        "derive_registered_operational_terminal_authority_v1"
    )
    assert (
        dependency.dependency_available
        is runtime.DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED
    )
    assert dependency.terminal_adapter_available is False
    assert dependency.to_document()["injected_callback_allowed"] is False
    assert dependency.to_document()["caller_transcript_allowed"] is False
    assert (
        dependency.to_document()["caller_status_policy_or_count_allowed"]
        is False
    )
    assert dependency.to_document()["caller_resource_limits_allowed"] is False
    assert (
        runtime.REGISTERED_RUNTIME_ENABLED
        is runtime.DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED
    )
    assert (
        runtime.RegisteredMatchedDirectTerminalCodeV1
        .CONDITIONAL_PLAN_CERTIFICATE.value
        in prereg.TERMINAL_CODES
    )
    assert (
        runtime.RegisteredMatchedDirectTerminalCodeV1
        .EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE.value
        in prereg.TERMINAL_CODES
    )


def test_invalid_anchor_fails_before_every_observer_or_target_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        calls.append("TARGET_ACCESS")
        raise AssertionError("pre-anchor target access occurred")

    for module, name in (
        (observer, "_environment_law"),
        (observer, "open_heldout_target_transition_stream_v2"),
        (observer, "evaluation_only_exact_atoms_v2"),
        (observer.AnchorGatedHeldoutTransitionStreamV2, "draw"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    for nonanchor in (None, object(), _placeholder()):
        with pytest.raises(
            runtime.RegisteredMatchedDirectRuntimeLockedV1
        ) as captured:
            runtime.run_registered_matched_direct_occurrence_v1(
                authority_chain=object(),  # type: ignore[arg-type]
                anchor=nonanchor,  # type: ignore[arg-type]
                occurrence_plan=object(),  # type: ignore[arg-type]
                context=object(),  # type: ignore[arg-type]
            )
        assert captured.value.access_audit == runtime.ZERO_ACCESS_AUDIT
        assert (
            captured.value.access_audit.observer_or_target_access_started
            is False
        )
    assert calls == []


def test_reached_direct_checkpoints_are_journaled_inside_runtime_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = SimpleNamespace()
    anchor = SimpleNamespace()
    plan = SimpleNamespace()
    context = SimpleNamespace(context_id=_id("journal-context"))
    accumulator = SimpleNamespace()
    calls: list[tuple[str, int]] = []

    monkeypatch.setattr(
        runtime,
        "_require_production_identity_without_observer_access",
        lambda **_kwargs: (chain, anchor, plan, context),
    )
    monkeypatch.setattr(
        runtime,
        "inspect_registered_matched_direct_dependency_protocol_v1",
        lambda: SimpleNamespace(
            dependency_available=True,
            blockers=(),
        ),
    )
    monkeypatch.setattr(runtime, "REGISTERED_RUNTIME_ENABLED", True)
    monkeypatch.setattr(
        inventory,
        "open_registered_matched_direct_complete_inventory_accumulator_v1",
        lambda **_kwargs: accumulator,
    )

    def acquire(*, accumulator: Any, checkpoint: int) -> Any:
        assert accumulator is not None
        calls.append(("ACQUIRE", checkpoint))
        return SimpleNamespace(
            checkpoint=checkpoint,
            direct_snapshot=SimpleNamespace(
                planner_model=object(),
                threshold_profile=object(),
            ),
        )

    monkeypatch.setattr(
        inventory,
        "acquire_registered_matched_direct_complete_inventory_checkpoint_v1",
        acquire,
    )
    monkeypatch.setattr(
        inventory,
        "verify_registered_matched_direct_complete_inventory_checkpoint_v1",
        lambda *, checkpoint_artifact: checkpoint_artifact,
    )
    solver_results = iter(
        (
            SimpleNamespace(
                status=runtime.lazy.ExactLazyH2SolveStatus.SOLVED,
                audit=SimpleNamespace(
                    status=runtime.robust.RobustAuditStatus
                    .FAILED_PROOF_FRONTIER
                ),
            ),
            SimpleNamespace(
                status=(
                    runtime.lazy.ExactLazyH2SolveStatus
                    .EXACT_DP_RESOURCE_EXHAUSTED
                ),
                audit=None,
            ),
        )
    )
    monkeypatch.setattr(
        runtime.lazy,
        "solve_exact_lazy_ground_direct_h2_v1",
        lambda *_args, **_kwargs: next(solver_results),
    )
    monkeypatch.setattr(
        runtime.lazy_independent,
        "verify_exact_lazy_h2_solve_result_v1",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        runtime,
        "_derive_deterministic_policy_v1",
        lambda **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        runtime,
        "RegisteredMatchedDirectCheckpointRecordV1",
        lambda checkpoint_artifact, planner_result, proof, status, policy: (
            SimpleNamespace(
                checkpoint=checkpoint_artifact.checkpoint,
                inventory_checkpoint=checkpoint_artifact,
                planner_result=planner_result,
                proof_verification=proof,
                status=status,
                policy=policy,
            )
        ),
    )

    class ReachedSecondCheckpoint(RuntimeError):
        pass

    class JournalSink:
        def commit_direct_checkpoint(
            self,
            *,
            context_id: str,
            checkpoint_record: Any,
        ) -> None:
            assert context_id == context.context_id
            calls.append(("JOURNAL", checkpoint_record.checkpoint))
            if checkpoint_record.checkpoint == runtime.CHECKPOINTS[1]:
                raise ReachedSecondCheckpoint

    monkeypatch.setattr(
        attempt_journal,
        "active_attempt_journal_v1",
        lambda **_kwargs: JournalSink(),
    )

    with pytest.raises(ReachedSecondCheckpoint):
        runtime.run_registered_matched_direct_occurrence_v1(
            authority_chain=chain,
            anchor=anchor,
            occurrence_plan=plan,
            context=context,
        )

    assert calls == [
        ("ACQUIRE", runtime.CHECKPOINTS[0]),
        ("JOURNAL", runtime.CHECKPOINTS[0]),
        ("ACQUIRE", runtime.CHECKPOINTS[1]),
        ("JOURNAL", runtime.CHECKPOINTS[1]),
    ]


def test_runtime_access_accounting_separates_online_and_replay_draws() -> None:
    audit = runtime.RegisteredMatchedDirectAccessAuditV1(
        inventory_accumulator_open_calls=1,
        acquisition_stream_opens=4,
        acquisition_draw_calls=10,
        independent_replay_stream_opens=4,
        independent_replay_draw_calls=10,
        observer_stream_opens=8,
        observer_draw_calls=20,
        accepted_observations=10,
    )
    document = audit.to_document()
    assert document["online_sample_evidence_draws"] == 10
    assert (
        document["independent_replay_draws_enter_online_sample_evidence"]
        is False
    )
    with pytest.raises(
        runtime.V072RegisteredMatchedDirectRuntimeInvariantViolation,
        match="mixed",
    ):
        runtime.RegisteredMatchedDirectAccessAuditV1(
            acquisition_draw_calls=10,
            independent_replay_draw_calls=10,
            observer_draw_calls=20,
            accepted_observations=20,
        )


def test_production_policy_and_verifier_cannot_be_caller_minted() -> None:
    with pytest.raises(
        runtime.V072RegisteredMatchedDirectRuntimeInvariantViolation,
        match="caller-minted",
    ):
        runtime.RegisteredMatchedDirectDeterministicPolicyV1(
            object(),
            _id("chain"),
            _id("anchor"),
            _id("final"),
            _id("occurrence"),
            _id("context"),
            _id("checkpoint"),
            _id("snapshot"),
            _id("model"),
            _id("threshold"),
            _id("audit"),
            object(),  # type: ignore[arg-type]
            (),
        )
    with pytest.raises(
        runtime.V072RegisteredMatchedDirectRuntimeInvariantViolation,
        match="exact result type",
    ):
        runtime.verify_registered_matched_direct_occurrence_result_v1(
            object(),  # type: ignore[arg-type]
        )


def test_direct_occurrence_identities_cover_exact_schedule_positions() -> None:
    contexts = prereg.registered_heldout_public_contexts_v2()
    arm_ordinal = prereg.ARM_ORDER.index(runtime.ARM)
    plans = tuple(
        runtime.RegisteredMatchedDirectOccurrencePlanV1(
            _id("unopened-runtime-anchor"),
            context.context_id,
            context.context_key,
            context_index,
            arm_ordinal,
            context_index * len(prereg.ARM_ORDER) + arm_ordinal,
        )
        for context_index, context in enumerate(contexts)
    )
    assert tuple(item.occurrence_ordinal for item in plans) == (4, 9, 14)
    assert len({item.plan_id for item in plans}) == 3
    assert all(
        item.to_document()["checkpoint_order"]
        == list(prereg.DIRECT_VALIDATION_CHECKPOINTS)
        and item.to_document()["replacement_allowed"] is False
        and item.to_document()["early_skip_allowed"] is False
        and item.to_document()["crn_draw_discount"] == 0
        for item in plans
    )


def test_disjoint_schedule_certifies_at_first_terminal_checkpoint() -> None:
    checkpoints = _checkpoints(
        (
            runtime.RegistrationDisjointDirectCheckpointStatusV1
            .NOT_CERTIFIED,
            runtime.RegistrationDisjointDirectCheckpointStatusV1.CERTIFIED,
        )
    )
    result = runtime.run_registration_disjoint_direct_schedule_core_v1(
        checkpoints=checkpoints
    )
    assert result.terminal_status is (
        runtime.RegistrationDisjointDirectCheckpointStatusV1.CERTIFIED
    )
    assert result.stopped_checkpoint == 4_096
    assert result.row_count == 2
    assert result.total_accepted_draws == 2 * (64 + 4_096)
    assert tuple(
        record.work.accepted_new_draws for record in result.records
    ) == (
        2 * (64 + 2_048),
        2 * (4_096 - 2_048),
    )
    assert all(
        record.work.cumulative_accepted_draws
        == 2 * (64 + record.work.checkpoint)
        and record.work.source_prior_reads == 0
        and record.work.quotient_model_builds == 0
        and record.work.quotient_planner_calls == 0
        and record.work.local_recovery_calls == 0
        and record.work.crn_draw_discount == 0
        for record in result.records
    )
    document = result.to_document()
    assert document["total_accepted_draws"] == 2 * (64 + 4_096)
    assert document["source_prior_reads"] == 0
    assert document["quotient_planner_calls"] == 0
    assert document["local_recovery_calls"] == 0
    assert document["crn_draw_discount"] == 0


def test_disjoint_schedule_supports_resource_and_frozen_max_closures() -> None:
    resource = runtime.run_registration_disjoint_direct_schedule_core_v1(
        checkpoints=_checkpoints(
            (
                runtime.RegistrationDisjointDirectCheckpointStatusV1
                .SOLVER_RESOURCE_EXHAUSTED,
            )
        )
    )
    assert resource.stopped_checkpoint == 2_048
    assert resource.terminal_status is (
        runtime.RegistrationDisjointDirectCheckpointStatusV1
        .SOLVER_RESOURCE_EXHAUSTED
    )

    maximum = runtime.run_registration_disjoint_direct_schedule_core_v1(
        checkpoints=_checkpoints(
            (
                runtime.RegistrationDisjointDirectCheckpointStatusV1
                .NOT_CERTIFIED,
            )
            * 4
        )
    )
    assert maximum.stopped_checkpoint == 16_384
    assert maximum.terminal_status is (
        runtime.RegistrationDisjointDirectCheckpointStatusV1.NOT_CERTIFIED
    )
    assert maximum.total_accepted_draws == 2 * (64 + 16_384)


def test_skip_replacement_early_stop_and_prefix_rewrite_fail() -> None:
    early = _checkpoints(
        (
            runtime.RegistrationDisjointDirectCheckpointStatusV1
            .NOT_CERTIFIED,
        )
    )
    with pytest.raises(
        runtime.V072RegisteredMatchedDirectRuntimeInvariantViolation,
        match="stopped early|skipped",
    ):
        runtime.run_registration_disjoint_direct_schedule_core_v1(
            checkpoints=early
        )

    certified_then_extra = _checkpoints(
        (
            runtime.RegistrationDisjointDirectCheckpointStatusV1.CERTIFIED,
            runtime.RegistrationDisjointDirectCheckpointStatusV1
            .NOT_CERTIFIED,
        )
    )
    with pytest.raises(
        runtime.V072RegisteredMatchedDirectRuntimeInvariantViolation,
        match="stopped early|skipped",
    ):
        runtime.run_registration_disjoint_direct_schedule_core_v1(
            checkpoints=certified_then_extra
        )

    valid = _checkpoints(
        (
            runtime.RegistrationDisjointDirectCheckpointStatusV1
            .NOT_CERTIFIED,
            runtime.RegistrationDisjointDirectCheckpointStatusV1.CERTIFIED,
        )
    )
    replacement_previous = {
        item.row_key: item for item in valid[0].row_prefixes
    }
    replacement = runtime.RegistrationDisjointDirectCheckpointV1(
        4_096,
        _checkpoint_prefix(
            checkpoint=4_096,
            row_keys=(
                "SYNTHETIC_DISJOINT_ROW_A",
                "SYNTHETIC_DISJOINT_ROW_C",
            ),
            previous={
                **replacement_previous,
                "SYNTHETIC_DISJOINT_ROW_C":
                    runtime.RegistrationDisjointDirectRowPrefixV1(
                        "SYNTHETIC_DISJOINT_ROW_C",
                        2_048,
                        None,
                        64 + 2_048,
                    ),
            },
        ),
        runtime.RegistrationDisjointDirectCheckpointStatusV1.CERTIFIED,
    )
    with pytest.raises(
        runtime.V072RegisteredMatchedDirectRuntimeInvariantViolation,
        match="replaced|omitted",
    ):
        runtime.run_registration_disjoint_direct_schedule_core_v1(
            checkpoints=(valid[0], replacement)
        )

    broken_prefix = replace(
        valid[1].row_prefixes[0],
        previous_prefix_id=_id("wrong-parent"),
    )
    broken_checkpoint = replace(
        valid[1],
        row_prefixes=(
            broken_prefix,
            *valid[1].row_prefixes[1:],
        ),
    )
    with pytest.raises(
        runtime.V072RegisteredMatchedDirectRuntimeInvariantViolation,
        match="append-only",
    ):
        runtime.run_registration_disjoint_direct_schedule_core_v1(
            checkpoints=(valid[0], broken_checkpoint)
        )


def test_evaluator_terminal_boundary_cannot_be_faked_pre_anchor() -> None:
    with pytest.raises(
        evaluator.RegisteredIndependentExactGroundEvaluationLocked,
        match=evaluator.REGISTERED_OPERATIONAL_TERMINAL_BLOCKER,
    ):
        evaluator.mint_registered_occurrence_operational_terminal_policy_v1(
            mint_authority=object(),  # type: ignore[arg-type]
        )
    with pytest.raises(
        runtime.V072RegisteredMatchedDirectRuntimeInvariantViolation,
        match="unminted",
    ):
        runtime.RegisteredMatchedDirectEvaluatorTerminalBundleV1(
            _id("occurrence"),
            _id("runtime-result"),
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
        )
