from __future__ import annotations

import copy
import inspect

import pytest

from acfqp import row_bound_observation_independent_verifier_v2 as verifier
from acfqp import v072_synthetic_row_observation_adapter_v1 as adapter


def _unsafe_field(value: object, field_name: str, replacement: object) -> object:
    attacked = copy.copy(value)
    object.__setattr__(attacked, field_name, replacement)
    return attacked


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


def test_independent_verifier_replays_every_initial_raw_commitment(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    result = verifier.verify_development_synthetic_row_acquisition_v2(cold)
    assert result.replayed_raw_observations == 64 + 2_048
    assert result.replayed_chunks == 1 + 8
    assert result.final_checkpoint_draw_count == 2_048
    assert result.incremental_new_draws == 2_048
    assert result.registered_target_draws == 0


def test_independent_verifier_replays_incremental_history_once(
    extended: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    result = verifier.verify_development_synthetic_row_acquisition_v2(
        extended
    )
    assert result.replayed_raw_observations == 64 + 16_384
    assert result.replayed_chunks == 1 + 64
    assert result.final_checkpoint_draw_count == 16_384
    assert result.incremental_new_draws == 8_192


def test_raw_digest_tamper_is_rejected(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    transcript = cold.validation_transcript
    chunk = transcript.chunks[0]
    observation = _unsafe_field(
        chunk.observations[0],
        "raw_digest",
        "0" * 64,
    )
    attacked_chunk = _unsafe_field(
        chunk,
        "observations",
        (observation,) + chunk.observations[1:],
    )
    attacked_transcript = _unsafe_field(
        transcript,
        "chunks",
        (attacked_chunk,) + transcript.chunks[1:],
    )
    attacked = _unsafe_field(
        cold,
        "validation_history",
        (attacked_transcript,),
    )
    with pytest.raises(
        verifier.RowObservationIndependentVerificationV2Failure
    ):
        verifier.verify_development_synthetic_row_acquisition_v2(attacked)


def test_chunk_commitment_tamper_is_rejected(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    chunk = _unsafe_field(
        cold.validation_transcript.chunks[1],
        "_chunk_id",
        "f" * 64,
    )
    transcript = _unsafe_field(
        cold.validation_transcript,
        "chunks",
        (
            cold.validation_transcript.chunks[0],
            chunk,
            *cold.validation_transcript.chunks[2:],
        ),
    )
    attacked = _unsafe_field(cold, "validation_history", (transcript,))
    with pytest.raises(
        verifier.RowObservationIndependentVerificationV2Failure
    ):
        verifier.verify_development_synthetic_row_acquisition_v2(attacked)


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("arm", "SOURCE_CONSENSUS_PRIOR"),
        ("confidence_epoch_index", 2),
        ("backend_domain_id", "e" * 64),
        ("support_epoch_chain_id", "d" * 64),
    ),
)
def test_cross_arm_epoch_domain_or_chain_transplant_is_rejected(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
    field_name: str,
    replacement: object,
) -> None:
    stream = _unsafe_field(
        cold.validation_transcript.stream_identity,
        field_name,
        replacement,
    )
    transcript = _unsafe_field(
        cold.validation_transcript,
        "stream_identity",
        stream,
    )
    attacked = _unsafe_field(cold, "validation_history", (transcript,))
    with pytest.raises(
        verifier.RowObservationIndependentVerificationV2Failure
    ):
        verifier.verify_development_synthetic_row_acquisition_v2(attacked)


def test_confidence_snapshot_transplant_is_rejected(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    other = adapter.acquire_development_synthetic_initial_row_v2(
        arm="SOURCE_CONSENSUS_PRIOR"
    )
    attacked = _unsafe_field(
        cold,
        "confidence_snapshot",
        other.confidence_snapshot,
    )
    with pytest.raises(
        verifier.RowObservationIndependentVerificationV2Failure
    ):
        verifier.verify_development_synthetic_row_acquisition_v2(attacked)


def test_promotion_replay_verifies_no_discovery_and_fresh_samples(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    promoted = adapter.promote_development_synthetic_row_support_v2(cold)
    result = verifier.verify_development_synthetic_row_promotion_v2(promoted)
    assert result.artifact_kind == "PROMOTION"
    assert result.replayed_raw_observations == 64 + 2_048 + 2_048
    assert result.final_checkpoint_draw_count == 2_048
    assert result.registered_target_draws == 0


def test_promotion_old_validation_reuse_is_rejected(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    promoted = adapter.promote_development_synthetic_row_support_v2(cold)
    attacked = _unsafe_field(
        promoted,
        "fresh_validation_transcript",
        cold.validation_transcript,
    )
    with pytest.raises(
        verifier.RowObservationIndependentVerificationV2Failure
    ):
        verifier.verify_development_synthetic_row_promotion_v2(attacked)


def test_promotion_novel_omission_is_rejected(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> None:
    promoted = adapter.promote_development_synthetic_row_support_v2(cold)
    epoch = _unsafe_field(
        promoted.promoted_support_epoch,
        "support_descriptors",
        cold.support_epoch.support_descriptors,
    )
    attacked = _unsafe_field(promoted, "promoted_support_epoch", epoch)
    with pytest.raises(
        verifier.RowObservationIndependentVerificationV2Failure
    ):
        verifier.verify_development_synthetic_row_promotion_v2(attacked)


def test_independent_verifier_does_not_call_production_builders() -> None:
    source = inspect.getsource(verifier)
    forbidden = (
        "build_or_extend_row_observation_transcript_v2(",
        "freeze_source_observation_v2(",
        "acquire_development_synthetic_initial_row_v2(",
        "extend_development_synthetic_row_prefix_v2(",
        "promote_development_synthetic_row_support_v2(",
        "build_partial_support_confidence_snapshot_v2(",
    )
    assert not any(item in source for item in forbidden)
