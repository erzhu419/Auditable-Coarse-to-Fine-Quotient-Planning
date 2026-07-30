from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as runner


class _Schedule:
    pass


class _FinalEpoch:
    pass


class _ControlledClosure:
    pass


class _ControlReconciliation:
    def to_document(self) -> dict[str, object]:
        return {"reconciliation_id": "control-reconciliation"}


class _Lineage:
    pass


class _Lifecycle:
    pass


class _LifecycleVerification:
    pass


class _PlanningInput:
    pass


class _PlanningProof:
    pass


class _ClosedReconciliation:
    def __init__(
        self,
        issuer: object,
        final_epoch: object,
        controlled_closure: object,
        lineage: object,
        lifecycle: object,
        planning_input: object,
        proof: object,
    ) -> None:
        assert issuer is runner._CLOSED_RECONCILIATION_ISSUER
        self.final_epoch = final_epoch
        self.controlled_closure = controlled_closure
        self.lineage = lineage
        self.lifecycle = lifecycle
        self.planning_input = planning_input
        self.closed_proof = proof


def _namespace(namespace_id: str) -> SimpleNamespace:
    return SimpleNamespace(target_tape_namespace_id=namespace_id)


def _fixture(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    occurrence_id = "occurrence"
    namespace_id = "namespace"
    context_id = "context"
    arm = runner.worker.V075WorkerArmV1.NO_PRIOR
    route = runner.planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
    occurrence = SimpleNamespace(
        occurrence_id=occurrence_id,
        target_tape_namespace_id=namespace_id,
        context_id=context_id,
        arm=arm,
    )
    schedule = _Schedule()
    schedule.schedule_id = "schedule"
    schedule.occurrence = occurrence

    batch_closure = SimpleNamespace(
        canonical_bytes=b"controlled-batch-closure",
        occurrence_id=occurrence_id,
        closure_id="batch-closure",
        authority_binding=SimpleNamespace(namespace=_namespace(namespace_id)),
    )
    control_closure = SimpleNamespace(
        occurrence_id=occurrence_id,
        final_head_id="head-1",
    )
    heads = (
        SimpleNamespace(head_id="head-0"),
        SimpleNamespace(head_id="head-1"),
    )
    appends = (
        SimpleNamespace(receipt=SimpleNamespace(receipt_id="receipt-1")),
    )
    support_freezes = (SimpleNamespace(freeze_id="freeze-1"),)
    controlled = _ControlledClosure()
    controlled.batch_closure = batch_closure
    controlled.control_closure = control_closure
    controlled.heads = heads
    controlled.appends = appends
    controlled.support_freezes = support_freezes
    controlled.reconciliation = _ControlReconciliation()

    stream = SimpleNamespace(stream_id="stream")
    exact_lineage = _Lineage()
    exact_lineage.scope = (
        runner.lineage_authority
        .V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
    )
    exact_lineage.canonical_bytes = b"lineage"
    exact_lineage.closure = batch_closure
    exact_lineage.batches = (
        SimpleNamespace(
            request=SimpleNamespace(stream_identity=stream),
        ),
    )
    exact_lineage.occurrence_identity = occurrence
    exact_lineage.lineage_id = "lineage"

    exact_lifecycle = _Lifecycle()
    exact_lifecycle.scope = (
        runner.lifecycle_module
        .V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY
    )
    exact_lifecycle.canonical_bytes = b"lifecycle"
    exact_lifecycle.lineage_id = exact_lineage.lineage_id
    exact_lifecycle.batch_closure_id = batch_closure.closure_id
    exact_lifecycle.occurrence_id = occurrence_id
    exact_lifecycle.target_tape_namespace_id = namespace_id
    exact_lifecycle.context_id = context_id
    exact_lifecycle.arm = arm.value
    exact_lifecycle.closure_id = "lifecycle-closure"
    lifecycle_verification = _LifecycleVerification()
    lifecycle_verification.verification_id = "lifecycle-verification"

    model = SimpleNamespace(
        model_id="model",
        to_document=lambda: {"model_id": "model"},
    )
    proof = _PlanningProof()
    proof.proof_id = "proof"
    proof.canonical_bytes = b"proof"
    planning_input = _PlanningInput()
    planning_input.schedule_id = schedule.schedule_id
    planning_input.lineage_id = exact_lineage.lineage_id
    planning_input.lifecycle_closure_id = exact_lifecycle.closure_id
    planning_input.lifecycle_verification_id = (
        lifecycle_verification.verification_id
    )
    planning_input.occurrence_id = occurrence_id
    planning_input.target_tape_namespace_id = namespace_id
    planning_input.arm = arm
    planning_input.route = route
    planning_input.model = model

    prefix = SimpleNamespace(
        heads=heads,
        appends=appends,
        support_freezes=support_freezes,
        head_ids=("head-0", "head-1"),
        receipt_ids=("receipt-1",),
        support_freeze_ids=("freeze-1",),
        current_head_id="head-1",
    )
    final_epoch = _FinalEpoch()
    final_epoch.occurrence_identity = occurrence
    final_epoch.context_id = context_id
    final_epoch.arm = arm
    final_epoch.route = route
    final_epoch.controlled_appends = appends
    final_epoch.support_freezes = support_freezes
    final_epoch.open_prefix_verification = prefix
    final_epoch.head_id = "head-1"
    final_epoch.model = model
    final_epoch.proof = proof
    final_epoch.model_epoch_id = "model-epoch"
    final_epoch.canonical_bytes = b"model-epoch"
    exact_final_epoch = _FinalEpoch()
    exact_final_epoch.__dict__.update(final_epoch.__dict__)

    monkeypatch.setattr(
        runner.acquisition,
        "V075InitialAcquisitionScheduleV2",
        _Schedule,
    )
    monkeypatch.setattr(
        runner.live_model,
        "V075LiveIncrementalModelEpochV2",
        _FinalEpoch,
    )
    monkeypatch.setattr(
        runner.control,
        "V075ControlledBatchJournalClosureV2",
        _ControlledClosure,
    )
    monkeypatch.setattr(
        runner.control,
        "V075SignedBatchControlReconciliationV2",
        _ControlReconciliation,
    )
    monkeypatch.setattr(
        runner.lineage_authority,
        "V075BatchOccurrenceLineageV2",
        _Lineage,
    )
    monkeypatch.setattr(
        runner.lifecycle_module,
        "V075BatchOccurrenceLifecycleClosureV2",
        _Lifecycle,
    )
    monkeypatch.setattr(
        runner.lifecycle_module,
        "V075BatchOccurrenceLifecycleVerificationV2",
        _LifecycleVerification,
    )
    monkeypatch.setattr(
        runner.planning,
        "V075ConstructionPlanningInputV2",
        _PlanningInput,
    )
    monkeypatch.setattr(
        runner.planning,
        "V075NumericalPlanningProofV2",
        _PlanningProof,
    )
    monkeypatch.setattr(
        runner,
        "V075ObserverSignedClosedReconciliationV2",
        _ClosedReconciliation,
    )

    calls: list[str] = []

    def replay_epoch(claimed: object) -> _FinalEpoch:
        assert claimed is final_epoch
        calls.append("epoch")
        return exact_final_epoch

    def replay_control(**kwargs: object) -> _ControlReconciliation:
        assert kwargs == {
            "batch_closure": batch_closure,
            "heads": heads,
            "appends": appends,
            "control_closure": control_closure,
            "support_freezes": support_freezes,
        }
        calls.append("control")
        return controlled.reconciliation

    def replay_lineage(claimed: object) -> _Lineage:
        assert claimed is exact_lineage
        calls.append("lineage")
        return exact_lineage

    def replay_lifecycle(**kwargs: object) -> tuple[object, object]:
        assert kwargs["lifecycle_bytes"] == exact_lifecycle.canonical_bytes
        assert kwargs["lineage_bytes"] == exact_lineage.canonical_bytes
        assert (
            kwargs["batch_closure_bytes"]
            == batch_closure.canonical_bytes
        )
        assert kwargs["known_stream_identities"] == (stream,)
        calls.append("lifecycle")
        return exact_lifecycle, lifecycle_verification

    def compile_input(**kwargs: object) -> _PlanningInput:
        assert kwargs == {
            "repository_root": "/repository",
            "schedule": schedule,
            "lineage": exact_lineage,
            "lifecycle": exact_lifecycle,
        }
        calls.append("compile")
        return planning_input

    def plan(**kwargs: object) -> _PlanningProof:
        assert kwargs == {"model": model, "route": route}
        calls.append("plan")
        return proof

    monkeypatch.setattr(
        runner.live_model,
        "replay_v075_live_incremental_model_epoch_v2",
        replay_epoch,
    )
    monkeypatch.setattr(
        runner.control,
        "verify_v075_controlled_batch_journal_closure_v2",
        replay_control,
    )
    monkeypatch.setattr(
        runner.lineage_authority,
        "replay_v075_signed_batch_occurrence_lineage_v2",
        replay_lineage,
    )
    monkeypatch.setattr(
        runner.lifecycle_module,
        "verify_v075_batch_occurrence_lifecycle_bytes_v2",
        replay_lifecycle,
    )
    monkeypatch.setattr(
        runner.planning,
        "compile_v075_construction_planning_input_v2",
        compile_input,
    )
    monkeypatch.setattr(
        runner.planning,
        "plan_v075_construction_numerical_model_v2",
        plan,
    )
    return SimpleNamespace(
        schedule=schedule,
        final_epoch=final_epoch,
        exact_final_epoch=exact_final_epoch,
        controlled=controlled,
        lineage=exact_lineage,
        lifecycle=exact_lifecycle,
        planning_input=planning_input,
        proof=proof,
        calls=calls,
    )


def _freeze(case: SimpleNamespace) -> object:
    return runner.freeze_v075_construction_closed_reconciliation_v2(
        repository_root="/repository",
        schedule=case.schedule,
        final_epoch=case.final_epoch,
        controlled_closure=case.controlled,
        lineage=case.lineage,
        lifecycle=case.lifecycle,
    )


def test_public_owner_replays_roots_and_rebuilds_input_and_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _fixture(monkeypatch)

    result = _freeze(case)

    assert case.calls == [
        "epoch",
        "control",
        "lineage",
        "lifecycle",
        "compile",
        "plan",
    ]
    assert result.planning_input is case.planning_input
    assert result.closed_proof is case.proof
    assert result.final_epoch is case.exact_final_epoch
    parameters = inspect.signature(
        runner.freeze_v075_construction_closed_reconciliation_v2
    ).parameters
    assert "planning_input" not in parameters
    assert "proof" not in parameters


def test_public_owner_rejects_duck_typed_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _fixture(monkeypatch)

    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation
    ):
        runner.freeze_v075_construction_closed_reconciliation_v2(
            repository_root="/repository",
            schedule=SimpleNamespace(**vars(case.schedule)),
            final_epoch=case.final_epoch,
            controlled_closure=case.controlled,
            lineage=case.lineage,
            lifecycle=case.lifecycle,
        )

    assert case.calls == []


def test_public_owner_rejects_lineage_closure_transplant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _fixture(monkeypatch)
    case.lineage.closure = SimpleNamespace(
        canonical_bytes=b"transplanted-closure",
    )

    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation
    ):
        _freeze(case)

    assert case.calls == ["epoch", "control", "lineage"]


def test_public_owner_rejects_incomplete_final_epoch_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _fixture(monkeypatch)
    case.final_epoch.controlled_appends = ()
    case.exact_final_epoch.controlled_appends = ()

    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation
    ):
        _freeze(case)

    assert case.calls == ["epoch", "control", "lineage", "lifecycle"]


def test_public_owner_rejects_mutated_epoch_after_exact_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _fixture(monkeypatch)
    exact_epoch = _FinalEpoch()
    exact_epoch.__dict__.update(case.final_epoch.__dict__)
    exact_epoch.canonical_bytes = b"exact-model-epoch"

    monkeypatch.setattr(
        runner.live_model,
        "replay_v075_live_incremental_model_epoch_v2",
        lambda claimed: exact_epoch,
    )
    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation,
        match="final live epoch differs from public exact replay",
    ):
        _freeze(case)

    assert case.calls == []


def test_public_owner_rejects_duck_typed_epoch_replay_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _fixture(monkeypatch)
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
        match="final live epoch differs from public exact replay",
    ):
        _freeze(case)

    assert case.calls == []


def test_public_owner_normalizes_upstream_replay_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _fixture(monkeypatch)

    def fail_replay(**_kwargs: object) -> object:
        raise RuntimeError("upstream detail")

    monkeypatch.setattr(
        runner.control,
        "verify_v075_controlled_batch_journal_closure_v2",
        fail_replay,
    )
    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation,
        match="construction closed reconciliation exact replay failed",
    ):
        _freeze(case)
