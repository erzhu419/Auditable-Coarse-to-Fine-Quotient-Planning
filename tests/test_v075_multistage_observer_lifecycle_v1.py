from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_batched_observer_authority_v1 as batch_test


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-multistage-lifecycle-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _validation_stream(namespace, discovery_stream, evidence):
    row = discovery_stream.row_binding
    root_epoch = discovery_stream.pairing_authority.support_chain.leaf
    validation_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=1,
        evidence=evidence,
        parent=root_epoch,
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(root_epoch, validation_epoch),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=discovery_stream.arm,
    )


def _open(marker: str):
    (
        namespace,
        authority,
        _session,
        wrapped,
        discovery_stream,
        private_fixture,
    ) = batch_test._setup("multistage-" + marker)
    arm = worker.V075WorkerArmV1(discovery_stream.arm)
    value = lifecycle.open_v075_parent_owned_multistage_lifecycle_v1(
        batched_session=wrapped,
        occurrence_id=_id("occurrence-" + marker),
        context_id=discovery_stream.context_id,
        arm=arm,
        route_cap_profile=worker.V075WorkerCapProfileV1(),
    )
    return (
        namespace,
        authority,
        wrapped,
        discovery_stream,
        private_fixture,
        value,
    )


def _freeze_and_register(
    *,
    value,
    namespace,
    discovery_stream,
    discovery,
):
    selected = min(discovery.outcomes, key=lambda item: item.outcome_id)
    evidence = value.freeze_aggregate_support_evidence_v1(
        discovery_batch=discovery,
        selected_outcome_ids=(selected.outcome_id,),
    )
    validation_stream = _validation_stream(
        namespace,
        discovery_stream,
        evidence,
    )
    value.register_validation_support_epoch_v1(
        stream_identity=validation_stream,
    )
    return evidence, validation_stream


def _sealed(marker: str, *, adaptive_extension: bool = False):
    (
        namespace,
        authority,
        _wrapped,
        discovery_stream,
        private_fixture,
        value,
    ) = _open(marker)
    discovery = value.execute_batch_v1(
        stream_identity=discovery_stream,
        accepted_draw_start=1,
        accepted_draw_count=64,
        accepted_draw_cap=64,
    )
    _evidence, validation_stream = _freeze_and_register(
        value=value,
        namespace=namespace,
        discovery_stream=discovery_stream,
        discovery=discovery,
    )
    validation = value.execute_batch_v1(
        stream_identity=validation_stream,
        accepted_draw_start=1,
        accepted_draw_count=128,
        accepted_draw_cap=256,
    )
    if adaptive_extension:
        value.start_adaptive_round_v1(1)
        extension = value.execute_batch_v1(
            stream_identity=validation_stream,
            accepted_draw_start=129,
            accepted_draw_count=64,
            accepted_draw_cap=256,
        )
        assert extension.request.accepted_draw_start == 129
    sealed = value.close_construction_v1(
        authority=authority,
        private_environment=private_fixture,
        process_launches=1,
        child_intent_count=len(value.batches),
        terminal_code=(
            lifecycle.V075LifecycleTerminalCodeV1
            .COMPLETE_REGISTERED_CHECKPOINT_CLOSED
        ),
    )
    assert validation in sealed.batches
    return sealed


def test_multistage_lifecycle_closes_one_signed_aggregate_session() -> None:
    sealed = _sealed("positive")
    closure = sealed.closure
    assert tuple(item.kind for item in closure.events) == (
        lifecycle.V075LifecycleEventKindV1.DISCOVERY_BATCH,
        lifecycle.V075LifecycleEventKindV1.SUPPORT_FREEZE,
        lifecycle.V075LifecycleEventKindV1.VALIDATION_BATCH,
    )
    assert closure.accepted_draw_count == 64 + 128
    assert closure.accepted_draw_cap == 64 + 256
    assert closure.batch_ids == tuple(item.batch_id for item in sealed.batches)
    assert closure.aggregate_support_evidence_ids == tuple(
        item.evidence_id for item in sealed.aggregate_support_evidence
    )
    assert closure.to_document()["per_draw_capability_count"] == 0
    assert closure.to_document()["private_law_serialized"] is False
    assert sealed.underlying_closure.entries == ()
    assert sealed.underlying_closure_verification.replayed_record_count == 0
    replayed = lifecycle.verify_v075_multistage_occurrence_closure_v1(
        closure=closure,
        batches=sealed.batches,
        public_verifications=sealed.public_verifications,
        sequence_verifications=sealed.sequence_verifications,
        private_replay_verifications=sealed.private_replay_verifications,
        aggregate_support_evidence=sealed.aggregate_support_evidence,
        underlying_closure=sealed.underlying_closure,
        underlying_closure_verification=(
            sealed.underlying_closure_verification
        ),
        observer_open_binding=sealed.underlying_closure.authority_binding,
    )
    assert replayed == sealed.verification


def test_open_lifecycle_exposes_exact_public_predraw_binding() -> None:
    (
        namespace,
        _authority,
        wrapped,
        discovery_stream,
        _private_fixture,
        value,
    ) = _open("public-open-binding")
    binding = value.open_binding
    assert type(binding) is lifecycle.V075OpenMultistageLifecycleBindingV1
    assert binding.occurrence_id == _id("occurrence-public-open-binding")
    assert binding.context_id == discovery_stream.context_id
    assert binding.arm is worker.V075WorkerArmV1(discovery_stream.arm)
    assert binding.namespace == namespace
    assert binding.session_public_id == wrapped.session_public_id
    assert binding.observer_open_binding.namespace == namespace
    assert binding.route_cap_profile_id == (
        worker.V075WorkerCapProfileV1().cap_profile_id
    )
    document = binding.to_document()
    assert document["frozen_before_observation"] is True
    assert document["private_material_serialized"] is False
    assert value.batches == ()
    assert value.events == ()


def test_adaptive_validation_extension_reuses_prior_support_before_batch() -> None:
    sealed = _sealed("adaptive", adaptive_extension=True)
    assert tuple(item.kind for item in sealed.closure.events) == (
        lifecycle.V075LifecycleEventKindV1.DISCOVERY_BATCH,
        lifecycle.V075LifecycleEventKindV1.SUPPORT_FREEZE,
        lifecycle.V075LifecycleEventKindV1.VALIDATION_BATCH,
        lifecycle.V075LifecycleEventKindV1.ADAPTIVE_VALIDATION_BATCH,
    )
    assert sealed.closure.accepted_draw_count == 64 + 128 + 64
    assert len(sealed.sequence_verifications) == 2


def test_validation_before_registered_support_freeze_fails_closed() -> None:
    (
        namespace,
        _authority,
        _wrapped,
        discovery_stream,
        _private_fixture,
        value,
    ) = _open("unregistered-support")
    discovery = value.execute_batch_v1(
        stream_identity=discovery_stream,
        accepted_draw_start=1,
        accepted_draw_count=64,
        accepted_draw_cap=64,
    )
    selected = min(discovery.outcomes, key=lambda item: item.outcome_id)
    evidence = value.freeze_aggregate_support_evidence_v1(
        discovery_batch=discovery,
        selected_outcome_ids=(selected.outcome_id,),
    )
    validation_stream = _validation_stream(
        namespace,
        discovery_stream,
        evidence,
    )
    with pytest.raises(
        lifecycle.V075MultistageObserverLifecycleInvariantViolation,
        match="prior lifecycle support freeze",
    ):
        value.execute_batch_v1(
            stream_identity=validation_stream,
            accepted_draw_start=1,
            accepted_draw_count=128,
            accepted_draw_cap=128,
        )


def test_discovery_after_support_freeze_is_rejected() -> None:
    (
        _namespace,
        _authority,
        _wrapped,
        discovery_stream,
        _private_fixture,
        value,
    ) = _open("retrospective-discovery")
    discovery = value.execute_batch_v1(
        stream_identity=discovery_stream,
        accepted_draw_start=1,
        accepted_draw_count=32,
        accepted_draw_cap=64,
    )
    selected = min(discovery.outcomes, key=lambda item: item.outcome_id)
    value.freeze_aggregate_support_evidence_v1(
        discovery_batch=discovery,
        selected_outcome_ids=(selected.outcome_id,),
    )
    with pytest.raises(
        lifecycle.V075MultistageObserverLifecycleInvariantViolation,
        match="after support",
    ):
        value.execute_batch_v1(
            stream_identity=discovery_stream,
            accepted_draw_start=33,
            accepted_draw_count=32,
            accepted_draw_cap=64,
        )


def test_registry_reorder_and_transplant_are_rejected_by_replay() -> None:
    sealed = _sealed("registry-attack")
    forged = replace(
        sealed.closure,
        batch_ids=tuple(reversed(sealed.closure.batch_ids)),
    )
    with pytest.raises(
        lifecycle.V075MultistageObserverLifecycleInvariantViolation,
        match="batch registry",
    ):
        lifecycle.verify_v075_multistage_occurrence_closure_v1(
            closure=forged,
            batches=sealed.batches,
            public_verifications=sealed.public_verifications,
            sequence_verifications=sealed.sequence_verifications,
            private_replay_verifications=(
                sealed.private_replay_verifications
            ),
            aggregate_support_evidence=sealed.aggregate_support_evidence,
            underlying_closure=sealed.underlying_closure,
            underlying_closure_verification=(
                sealed.underlying_closure_verification
            ),
            observer_open_binding=(
                sealed.underlying_closure.authority_binding
            ),
        )
    with pytest.raises(
        lifecycle.V075MultistageObserverLifecycleInvariantViolation,
        match="batch registry",
    ):
        lifecycle.verify_v075_multistage_occurrence_closure_v1(
            closure=sealed.closure,
            batches=tuple(reversed(sealed.batches)),
            public_verifications=sealed.public_verifications,
            sequence_verifications=sealed.sequence_verifications,
            private_replay_verifications=(
                sealed.private_replay_verifications
            ),
            aggregate_support_evidence=sealed.aggregate_support_evidence,
            underlying_closure=sealed.underlying_closure,
            underlying_closure_verification=(
                sealed.underlying_closure_verification
            ),
            observer_open_binding=(
                sealed.underlying_closure.authority_binding
            ),
        )
