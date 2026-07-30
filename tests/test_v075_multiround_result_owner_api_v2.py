from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as runner


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class _Namespace:
    pass


class _Schedule:
    pass


class _ScheduleVerification:
    pass


class _Prefix:
    pass


class _Epoch:
    pass


class _ChildClosure:
    pass


class _ChildClosureVerification:
    pass


class _ChildLedger:
    pass


class _ChildExecutionVerification:
    pass


class _ChildBarrier:
    pass


class _ChildBarrierVerification:
    pass


class _PromotionDecision:
    pass


class _PromotionDecisionVerification:
    pass


class _PromotionBarrier:
    pass


class _PromotionBarrierVerification:
    pass


class _Reconciliation:
    pass


@pytest.fixture
def cap_graph(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    occurrence_id = _id("occurrence")
    context_id = _id("context")
    namespace_id = _id("namespace")
    arm = runner.worker.V075WorkerArmV1.NO_PRIOR
    row_id = _id("row")
    schedule_id = _id("schedule")
    verification_id = _id("schedule-verification")
    prefix_id = _id("root-prefix")
    head_id = _id("root-head")

    namespace = _Namespace()
    namespace.target_tape_namespace_id = namespace_id
    occurrence = SimpleNamespace(
        occurrence_id=occurrence_id,
        context_id=context_id,
        target_tape_namespace_id=namespace_id,
        arm=arm,
    )
    row = SimpleNamespace(row_binding_id=row_id)
    discovery = SimpleNamespace(
        kind=runner.acquisition.V075InitialIntentKindV2.ROOT_DISCOVERY,
        intent_id=_id("discovery"),
        row_binding=row,
        dependency_intent_ids=(),
        accepted_draw_start=1,
        accepted_draw_count=2,
        accepted_draw_cap=2,
    )
    promotion = SimpleNamespace(
        kind=(
            runner.acquisition
            .V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE
        ),
        intent_id=_id("promotion-template"),
        row_binding=row,
        dependency_intent_ids=(discovery.intent_id,),
        accepted_draw_start=None,
        accepted_draw_count=0,
        accepted_draw_cap=0,
    )
    validation = SimpleNamespace(
        kind=runner.acquisition.V075InitialIntentKindV2.ROOT_VALIDATION,
        intent_id=_id("validation"),
        row_binding=row,
        dependency_intent_ids=(promotion.intent_id,),
        accepted_draw_start=1,
        accepted_draw_count=3,
        accepted_draw_cap=3,
    )
    profile = SimpleNamespace(
        occurrence_slot_for=lambda **_kwargs: SimpleNamespace(
            slot_id=_id("slot")
        )
    )
    schedule = _Schedule()
    schedule.schedule_id = schedule_id
    schedule.occurrence = occurrence
    schedule.intents = (discovery, promotion, validation)
    schedule.profile = profile
    schedule.canonical_bytes = b"schedule"
    verification = _ScheduleVerification()
    verification.verification_id = verification_id
    verification.canonical_bytes = b"schedule-verification"

    discovery_stream = SimpleNamespace(name="discovery-stream")
    validation_stream = SimpleNamespace(name="validation-stream")

    def semantic(
        *,
        artifact_id: str,
        stage: object,
        support_freeze_id: str | None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            role=(
                runner.control.V075ControlledBatchSemanticAuthorityRoleV2
                .INITIAL_SCHEDULE_ROW_INTENT
            ),
            schema=(
                runner.control.V075ControlledBatchSemanticAuthoritySchemaV2
                .INITIAL_SCHEDULE_ROW_INTENT
            ),
            semantic_artifact_id=artifact_id,
            semantic_verification_id=verification_id,
            stage=stage,
            round_index=0,
            support_freeze_id=support_freeze_id,
        )

    discovery_append = SimpleNamespace(
        intent=SimpleNamespace(
            semantic_authority=semantic(
                artifact_id=discovery.intent_id,
                stage=(
                    runner.control.V075ControlledBatchStageV2.ROOT_DISCOVERY
                ),
                support_freeze_id=None,
            )
        ),
        batch=SimpleNamespace(
            request=SimpleNamespace(
                stream_identity=discovery_stream,
                accepted_draw_start=discovery.accepted_draw_start,
                accepted_draw_count=discovery.accepted_draw_count,
                accepted_draw_cap=discovery.accepted_draw_cap,
            )
        ),
        receipt=SimpleNamespace(receipt_id=_id("discovery-receipt")),
    )
    support = SimpleNamespace(
        freeze_id=_id("support-freeze"),
        row_binding_id=row_id,
        discovery_append=discovery_append,
    )
    validation_append = SimpleNamespace(
        intent=SimpleNamespace(
            semantic_authority=semantic(
                artifact_id=validation.intent_id,
                stage=(
                    runner.control.V075ControlledBatchStageV2.ROOT_VALIDATION
                ),
                support_freeze_id=support.freeze_id,
            )
        ),
        batch=SimpleNamespace(
            request=SimpleNamespace(
                stream_identity=validation_stream,
                accepted_draw_start=validation.accepted_draw_start,
                accepted_draw_count=validation.accepted_draw_count,
                accepted_draw_cap=validation.accepted_draw_cap,
            )
        ),
        receipt=SimpleNamespace(receipt_id=_id("validation-receipt")),
    )
    prefix = _Prefix()
    prefix.occurrence_id = occurrence_id
    prefix.appends = (discovery_append, validation_append)
    prefix.support_freezes = (support,)
    prefix.current_head_id = head_id
    prefix.verification_id = prefix_id
    prefix.to_document = lambda: {
        "verification_id": prefix_id,
        "head_id": head_id,
    }

    expected_root = runner.V075ObserverSignedRootExecutionV2(
        runner._ROOT_EXECUTION_ISSUER,
        schedule_id,
        verification_id,
        occurrence_id,
        head_id,
        prefix_id,
        (discovery.intent_id,),
        (discovery_append.receipt.receipt_id,),
        (promotion.intent_id,),
        (support.freeze_id,),
        ((promotion.intent_id, support.freeze_id),),
        (validation.intent_id,),
        (validation_append.receipt.receipt_id,),
        (row_id,),
    )

    model = SimpleNamespace(model_id=_id("model"))
    proof = SimpleNamespace(proof_id=_id("proof"))
    root_epoch_claim = _Epoch()
    root_epoch_claim.parent_epoch = None
    root_epoch_claim.epoch_index = 1
    root_epoch_claim.occurrence_identity = occurrence
    root_epoch_claim.context_id = context_id
    root_epoch_claim.arm = arm
    root_epoch_claim.route = (
        runner.planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
    )
    root_epoch_claim.head_id = head_id
    root_epoch_claim.open_prefix_verification = prefix
    root_epoch_claim.model_epoch_id = _id("root-epoch")
    root_epoch_claim.canonical_bytes = b"root-epoch"
    root_epoch_claim.model = model
    root_epoch_claim.proof = proof
    root_epoch_exact = _Epoch()
    root_epoch_exact.__dict__.update(root_epoch_claim.__dict__)

    child = _ChildClosure()
    child.status = (
        runner.dynamic.V075LiveDynamicChildClosureStatusV2
        .CHILD_ACTION_ROW_CAP_EXCEEDED
    )
    child.closure_id = _id("child-closure")
    child.canonical_bytes = b"child-closure"
    child_verification = _ChildClosureVerification()
    child_verification.verification_id = _id("child-verification")
    child_verification.to_document = lambda: {
        "verification_id": child_verification.verification_id
    }

    reconciliation_claim = _Reconciliation()
    reconciliation_claim.reconciliation_id = _id("reconciliation")
    reconciliation_claim.canonical_bytes = b"reconciliation"
    reconciliation_claim.final_epoch = root_epoch_claim
    reconciliation_claim.controlled_closure = object()
    reconciliation_claim.lineage = object()
    reconciliation_claim.lifecycle = object()
    reconciliation_exact = _Reconciliation()
    reconciliation_exact.__dict__.update(reconciliation_claim.__dict__)
    reconciliation_exact.final_epoch = root_epoch_exact

    monkeypatch.setattr(
        runner.namespace_v2,
        "V075PublicTargetTapeNamespaceV2",
        _Namespace,
    )
    monkeypatch.setattr(
        runner.acquisition,
        "V075InitialAcquisitionScheduleV2",
        _Schedule,
    )
    monkeypatch.setattr(
        runner.acquisition,
        "V075InitialAcquisitionVerificationV2",
        _ScheduleVerification,
    )
    monkeypatch.setattr(
        runner.control,
        "V075OpenControlledBatchPrefixVerificationV2",
        _Prefix,
    )
    monkeypatch.setattr(
        runner.live_model,
        "V075LiveIncrementalModelEpochV2",
        _Epoch,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "V075LiveDynamicChildClosureV2",
        _ChildClosure,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "V075LiveDynamicChildClosureVerificationV2",
        _ChildClosureVerification,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "V075LiveDynamicChildExecutionLedgerV2",
        _ChildLedger,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "V075LiveDynamicChildExecutionVerificationV2",
        _ChildExecutionVerification,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "V075LiveDynamicChildReplanningBarrierV2",
        _ChildBarrier,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "V075LiveDynamicChildReplanningBarrierVerificationV2",
        _ChildBarrierVerification,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "V075LivePromotionDecisionV2",
        _PromotionDecision,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "V075LivePromotionDecisionVerificationV2",
        _PromotionDecisionVerification,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "V075LivePromotionReplanningBarrierV2",
        _PromotionBarrier,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "V075LivePromotionReplanningBarrierVerificationV2",
        _PromotionBarrierVerification,
    )
    monkeypatch.setattr(
        runner,
        "V075ObserverSignedClosedReconciliationV2",
        _Reconciliation,
    )

    calls: list[str] = []

    def replay_schedule(**kwargs: object) -> _Schedule:
        assert kwargs["claimed"] is schedule
        calls.append("schedule")
        return schedule

    def replay_verification(**kwargs: object) -> _ScheduleVerification:
        assert kwargs["schedule"] is schedule
        calls.append("schedule-verification")
        return verification

    def replay_prefix(claimed: object) -> _Prefix:
        assert claimed is prefix
        calls.append("prefix")
        return prefix

    def replay_epoch(claimed: object) -> _Epoch:
        assert claimed is root_epoch_claim
        calls.append("epoch")
        return root_epoch_exact

    def replay_child(**kwargs: object) -> tuple[object, object]:
        assert kwargs["source_epoch"] is root_epoch_exact
        assert kwargs["claimed_bytes"] == child.canonical_bytes
        calls.append("child")
        return child, child_verification

    def replay_reconciliation(**kwargs: object) -> _Reconciliation:
        assert kwargs["final_epoch"] is root_epoch_exact
        assert kwargs["schedule"] is schedule
        calls.append("reconciliation")
        return reconciliation_exact

    monkeypatch.setattr(
        runner.acquisition,
        "replay_v075_initial_acquisition_schedule_v2",
        replay_schedule,
    )
    monkeypatch.setattr(
        runner.acquisition,
        "verify_v075_initial_acquisition_verification_bytes_v2",
        replay_verification,
    )
    monkeypatch.setattr(
        runner.control,
        "replay_v075_open_controlled_batch_prefix_verification_v2",
        replay_prefix,
    )
    monkeypatch.setattr(
        runner,
        "_root_discovery_stream",
        lambda **_kwargs: discovery_stream,
    )
    monkeypatch.setattr(
        runner.control,
        "derive_v075_controlled_validation_stream_v2",
        lambda **_kwargs: validation_stream,
    )
    monkeypatch.setattr(
        runner.live_model,
        "replay_v075_live_incremental_model_epoch_v2",
        replay_epoch,
    )
    monkeypatch.setattr(
        runner.dynamic,
        "verify_v075_live_dynamic_child_closure_bytes_v2",
        replay_child,
    )
    monkeypatch.setattr(
        runner,
        "freeze_v075_construction_closed_reconciliation_v2",
        replay_reconciliation,
    )
    return SimpleNamespace(
        namespace=namespace,
        schedule=schedule,
        verification=verification,
        prefix=prefix,
        expected_root=expected_root,
        root_epoch_claim=root_epoch_claim,
        root_epoch_exact=root_epoch_exact,
        child=child,
        child_verification=child_verification,
        reconciliation_claim=reconciliation_claim,
        reconciliation_exact=reconciliation_exact,
        calls=calls,
    )


def _root(case: SimpleNamespace, raw: bytes | None = None) -> object:
    return runner.replay_v075_construction_root_execution_v2(
        repository_root="/repository",
        namespace=case.namespace,
        schedule=case.schedule,
        schedule_verification=case.verification,
        controlled_root_prefix=case.prefix,
        root_execution_bytes=(
            case.expected_root.canonical_bytes if raw is None else raw
        ),
    )


def _result(case: SimpleNamespace, **overrides: object) -> object:
    arguments = {
        "repository_root": "/repository",
        "namespace": case.namespace,
        "schedule": case.schedule,
        "schedule_verification": case.verification,
        "controlled_root_prefix": case.prefix,
        "root_execution_bytes": case.expected_root.canonical_bytes,
        "root_epoch": case.root_epoch_claim,
        "child_closure": case.child,
        "child_closure_verification": case.child_verification,
        "final_epoch": case.root_epoch_claim,
        "reconciliation": case.reconciliation_claim,
    }
    arguments.update(overrides)
    return runner.freeze_v075_construction_multiround_result_v2(
        **arguments
    )


def test_public_root_reconstruction_uses_exact_prefix(
    cap_graph: SimpleNamespace,
) -> None:
    result = _root(cap_graph)

    assert result.canonical_bytes == cap_graph.expected_root.canonical_bytes
    assert cap_graph.calls == [
        "schedule",
        "schedule-verification",
        "prefix",
    ]


def test_public_root_reconstruction_rejects_transplanted_bytes(
    cap_graph: SimpleNamespace,
) -> None:
    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation,
        match="root execution bytes differ",
    ):
        _root(cap_graph, b"transplanted-root")


def test_public_result_derives_registered_cap_terminal(
    cap_graph: SimpleNamespace,
) -> None:
    result = _result(cap_graph)

    assert result.status is (
        runner.V075ObserverSignedMultiroundTerminalStatusV2
        .CHILD_ACTION_ROW_CAP_EXCEEDED
    )
    assert result.root_model_epoch_id == result.final_model_epoch_id
    assert result.child_execution_ledger_id is None
    assert result.promotion_decision_ids == ()
    assert cap_graph.calls == [
        "schedule",
        "schedule-verification",
        "prefix",
        "epoch",
        "epoch",
        "child",
        "reconciliation",
    ]
    parameters = inspect.signature(
        runner.freeze_v075_construction_multiround_result_v2
    ).parameters
    assert "status" not in parameters
    assert "claimed_result" not in parameters


def test_cap_terminal_rejects_any_child_execution_parent(
    cap_graph: SimpleNamespace,
) -> None:
    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation,
        match="quartet requiredness",
    ):
        _result(
            cap_graph,
            child_execution_ledger=_ChildLedger(),
        )


def test_result_rejects_duck_typed_epoch_replay(
    cap_graph: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.live_model,
        "replay_v075_live_incremental_model_epoch_v2",
        lambda claimed: SimpleNamespace(
            model_epoch_id=claimed.model_epoch_id,
            canonical_bytes=claimed.canonical_bytes,
        ),
    )

    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation,
        match="differs from public exact epoch replay",
    ):
        _result(cap_graph)


def test_result_rejects_reconciliation_transplant(
    cap_graph: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    foreign = _Reconciliation()
    foreign.__dict__.update(cap_graph.reconciliation_exact.__dict__)
    foreign.canonical_bytes = b"foreign-reconciliation"
    monkeypatch.setattr(
        runner,
        "freeze_v075_construction_closed_reconciliation_v2",
        lambda **_kwargs: foreign,
    )

    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation,
        match="reconciliation differs",
    ):
        _result(cap_graph)


def test_result_issuer_is_scoped_to_public_producer() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")

    assert source.count("V075ObserverSignedMultiroundResultV2(") == 1
    assert "freeze_v075_construction_multiround_result_v2(" in inspect.getsource(
        runner._closed_result
    )

