from __future__ import annotations

import copy
from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

from acfqp import heldout_graph_transition_observer_v2 as target_observer
from acfqp import partial_support_confidence_v2 as confidence
from acfqp import public_novel_child_cardinality_authority_v2 as cardinality
from acfqp import row_bound_observation_core_v2 as core
from acfqp import v072_synthetic_row_observation_adapter_v1 as adapter
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def cold() -> adapter.DevelopmentSyntheticRowAcquisitionV2:
    return adapter.acquire_development_synthetic_initial_row_v2()


@pytest.fixture(scope="module")
def extended(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> adapter.DevelopmentSyntheticRowAcquisitionV2:
    current = cold
    for checkpoint in (4_096, 8_192, 16_384):
        current = adapter.extend_development_synthetic_row_prefix_v2(
            current,
            validation_checkpoint=checkpoint,
        )
    return current


def test_cold_row_has_exact_chunked_raw_transcripts_and_confidence(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    assert cold.discovery_transcript.selected_checkpoint_draw_count == 64
    assert len(cold.discovery_transcript.chunks) == 1
    assert cold.validation_transcript.selected_checkpoint_draw_count == 2_048
    assert len(cold.validation_transcript.chunks) == 8
    assert cold.validation_transcript.work.newly_observed_draws == 2_048
    assert cold.validation_transcript.work.reused_prefix_draws == 0
    assert cold.support_epoch.excluded_probability_sample_ids == tuple(
        sorted(
            item.sample_id
            for item in cold.discovery_transcript.observations
        )
    )
    assert cold.confidence_snapshot.novel_descriptors
    assert all(
        observation.source_document["registered_target_evidence"] is False
        for observation in cold.validation_transcript.observations
    )


def test_validation_checkpoints_extend_one_immutable_prefix(
    extended: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    history = extended.validation_history
    assert tuple(
        item.selected_checkpoint_draw_count for item in history
    ) == (2_048, 4_096, 8_192, 16_384)
    for previous, current in zip(history, history[1:]):
        assert current.previous_transcript_id == previous.transcript_id
        assert current.previous_draw_count == previous.selected_checkpoint_draw_count
        assert current.chunks[: len(previous.chunks)] == previous.chunks
        assert current.observations[: len(previous.observations)] == (
            previous.observations
        )
        assert current.work.newly_observed_draws == (
            current.selected_checkpoint_draw_count
            - previous.selected_checkpoint_draw_count
        )
        assert current.work.reused_prefix_draws == (
            previous.selected_checkpoint_draw_count
        )
    assert len(extended.validation_transcript.chunks) == 64


def test_core_rejects_gap_and_cross_stream_suffix(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    previous = cold.validation_transcript
    wrong = cold.discovery_transcript.observations[0]
    with pytest.raises(core.RowBoundObservationV2InvariantViolation):
        core.build_or_extend_row_observation_transcript_v2(
            stream_identity=previous.stream_identity,
            selected_checkpoint_draw_count=4_096,
            new_observations=(wrong,),
            previous=previous,
        )


def test_arm_free_pairing_keeps_words_semantics_but_not_evidence_ids() -> None:
    source = adapter.acquire_development_synthetic_initial_row_v2(
        arm="SOURCE_CONSENSUS_PRIOR"
    )
    direct = adapter.acquire_development_synthetic_initial_row_v2(
        arm="MATCHED_DIRECT_GROUND"
    )
    for left, right in (
        (source.discovery_transcript, direct.discovery_transcript),
        (source.validation_transcript, direct.validation_transcript),
    ):
        assert (
            left.stream_identity.arm_free_support_semantics_id
            == right.stream_identity.arm_free_support_semantics_id
        )
        assert (
            left.stream_identity.seed_identity_id
            == right.stream_identity.seed_identity_id
        )
        assert tuple(item.raw_digest for item in left.observations) == tuple(
            item.raw_digest for item in right.observations
        )
        assert tuple(
            item.outcome_descriptor_id for item in left.observations
        ) == tuple(item.outcome_descriptor_id for item in right.observations)
        assert tuple(item.source_commitment_id for item in left.observations) != tuple(
            item.source_commitment_id for item in right.observations
        )
        assert tuple(item.observation_id for item in left.observations) != tuple(
            item.observation_id for item in right.observations
        )
        assert left.work.work_id != right.work.work_id


def test_support_semantic_fork_changes_seed_identity(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    stream = cold.validation_transcript.stream_identity
    forked_semantics = _id("development-support-semantic-fork")
    forked_material = tuple(
        sorted(
            (
                (key, forked_semantics)
                if key == "arm_free_support_semantics_id"
                else (key, value)
            )
            for key, value in stream.seed_material
        )
    )
    forked = core.RowObservationStreamIdentityV2(
        stream.preregistration_id,
        stream.backend_domain_id,
        stream.context_id,
        stream.arm,
        stream.physical_row_id,
        stream.arm_free_row_id,
        _id("development-arm-bound-forked-chain"),
        forked_semantics,
        stream.lane,
        stream.confidence_epoch_index,
        forked_material,
        _id("development-forked-source-stream"),
        stream.evidence_class,
        stream.role,
        False,
    )
    assert forked.seed_identity_id != stream.seed_identity_id
    assert forked.stream_binding_id != stream.stream_binding_id


def test_promotion_uses_all_novel_descriptors_no_discovery_or_old_samples(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    promoted = adapter.promote_development_synthetic_row_support_v2(cold)
    expected = set(cold.support_epoch.support_descriptor_ids) | set(
        cold.confidence_snapshot.novel_descriptor_ids
    )
    assert set(promoted.promoted_support_epoch.support_descriptor_ids) == expected
    assert promoted.fresh_discovery_draw_count == 0
    assert promoted.fresh_validation_transcript.selected_checkpoint_draw_count == 2_048
    assert promoted.fresh_validation_transcript.previous_transcript_id is None
    assert not (
        set(cold.confidence_snapshot.validation_prefix.sample_ids)
        & {
            item.sample_id
            for item in promoted.fresh_validation_transcript.observations
        }
    )


def test_registered_target_constructor_and_entrypoint_fail_closed(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    stream = cold.validation_transcript.stream_identity
    with pytest.raises(core.RowBoundObservationV2InvariantViolation):
        core.RowObservationStreamIdentityV2(
            stream.preregistration_id,
            stream.backend_domain_id,
            stream.context_id,
            stream.arm,
            stream.physical_row_id,
            stream.arm_free_row_id,
            stream.support_epoch_chain_id,
            stream.arm_free_support_semantics_id,
            stream.lane,
            stream.confidence_epoch_index,
            stream.seed_material,
            stream.source_stream_id,
            core.RowObservationEvidenceClassV2.REGISTERED_TARGET,
            "REGISTERED_TARGET",
            True,
        )
    with pytest.raises(adapter.RegisteredTargetRowAcquisitionLockedV2):
        adapter.acquire_registered_target_row_v2(object())


def test_duck_typed_registered_authority_cannot_open_core(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    class _FakeAnchor:
        registered_target_evidence = True
        verification_result = "VALID"

    stream = cold.validation_transcript.stream_identity
    with pytest.raises(core.RowBoundObservationV2InvariantViolation):
        core.RowObservationStreamIdentityV2(
            stream.preregistration_id,
            stream.backend_domain_id,
            stream.context_id,
            stream.arm,
            stream.physical_row_id,
            stream.arm_free_row_id,
            stream.support_epoch_chain_id,
            stream.arm_free_support_semantics_id,
            stream.lane,
            stream.confidence_epoch_index,
            stream.seed_material
            + (("caller_anchor", _id(str(_FakeAnchor()))),),
            stream.source_stream_id,
            core.RowObservationEvidenceClassV2.REGISTERED_TARGET,
            "REGISTERED_TARGET",
            True,
        )


def test_target_semantic_descriptor_reuses_cardinality_authority_domain() -> None:
    context = prereg.registered_heldout_public_contexts_v2()[0]
    root = target_observer.root_state_v2(context)
    catalogue = target_observer.legal_action_catalogue_v2(context, root, 2)
    descriptor = cardinality.RecordedTransitionDescriptorV2(
        target_observer.HeldoutSymbolicGraphStateV2(
            (2, 0, 2, 1, 0, 0, 0)
        ),
        Fraction(1, 16),
        False,
        False,
    )
    descriptor_id, document = (
        core.recorded_transition_descriptor_document_v2(descriptor)
    )
    assert catalogue.actions
    assert descriptor_id == descriptor.descriptor_id
    assert document == descriptor.to_document()
    with pytest.raises(core.RowBoundObservationV2InvariantViolation):
        core.recorded_transition_descriptor_document_v2(
            type(
                "_DuckDescriptor",
                (),
                {
                    "descriptor_id": descriptor.descriptor_id,
                    "to_document": descriptor.to_document,
                },
            )()
        )


def test_v2_control_does_not_change_v1_observer_or_confidence_claims(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    assert cold.row.to_document()["registered_target_evidence"] is False
    frozen = prereg.freeze_transfer_guided_acquisition_preregistration_v1()
    assert frozen.target_execution_allowed is False
    assert frozen.confirmatory_profile_finalized is False
    assert frozen.confirmatory_execution_manifest_id is None


def test_confidence_and_row_identity_validation_do_not_rebuild_hidden_law(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("hidden-law/preregistration freeze was called")

    monkeypatch.setattr(
        prereg,
        "freeze_transfer_guided_acquisition_preregistration_v1",
        forbidden,
    )
    monkeypatch.setattr(
        prereg,
        "frozen_heldout_environment_manifest_v1",
        forbidden,
    )
    profile = confidence.v0072_partial_support_confidence_profile_v2()
    assert profile.preregistration_id == prereg.DRAFT_PREREGISTRATION_ID

    stream = cold.validation_transcript.stream_identity
    rebuilt = core.RowObservationStreamIdentityV2(
        stream.preregistration_id,
        stream.backend_domain_id,
        stream.context_id,
        stream.arm,
        stream.physical_row_id,
        stream.arm_free_row_id,
        stream.support_epoch_chain_id,
        stream.arm_free_support_semantics_id,
        stream.lane,
        stream.confidence_epoch_index,
        stream.seed_material,
        stream.source_stream_id,
        stream.evidence_class,
        stream.role,
        stream.registered_target_evidence,
    )
    assert rebuilt.stream_binding_id == stream.stream_binding_id
    with pytest.raises(adapter.RegisteredTargetRowAcquisitionLockedV2):
        adapter.acquire_registered_target_row_v2()
