from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from fractions import Fraction
from hashlib import sha256
from typing import Mapping

import pytest

import acfqp.partial_support_confidence_v1 as confidence_v1
import acfqp.partial_support_confidence_v2 as confidence


def _id(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _SyntheticControlObservation:
    """Domain-separated control implementing only the generic protocol."""

    preregistration_id: str
    context_id: str
    arm: str
    physical_row_id: str
    support_epoch_chain_id: str
    stream_id: str
    lane: confidence.ConfidenceObservationLaneV2
    sequence_index: int
    sample_id: str
    outcome_descriptor_id: str
    outcome_document: Mapping[str, object]


@dataclass(frozen=True)
class _Fixture:
    profile: confidence.PartialSupportConfidenceProfileV2
    row: confidence.ConfidencePhysicalRowBindingV2
    discovery_chain: str
    discovery_stream: str
    validation_chain: str
    validation_stream: str
    epoch: confidence.InitialSupportEpochV2
    discovery: tuple[_SyntheticControlObservation, ...]


def _observations(
    fixture: _Fixture,
    *,
    lane: confidence.ConfidenceObservationLaneV2,
    chain: str,
    stream: str,
    count: int,
    outcome_labels: tuple[str, ...],
    sample_domain: str,
) -> tuple[_SyntheticControlObservation, ...]:
    return tuple(
        _SyntheticControlObservation(
            fixture.profile.preregistration_id,
            fixture.row.context_id,
            fixture.row.arm,
            fixture.row.physical_row_id,
            chain,
            stream,
            lane,
            index,
            _id(f"{sample_domain}:sample:{index}"),
            _id(f"descriptor:{outcome_labels[(index - 1) % len(outcome_labels)]}"),
            {
                "synthetic_control": True,
                "label": outcome_labels[(index - 1) % len(outcome_labels)],
            },
        )
        for index in range(1, count + 1)
    )


@pytest.fixture(scope="module")
def initial_fixture() -> _Fixture:
    profile = confidence.v0072_partial_support_confidence_profile_v2()
    row = confidence.ConfidencePhysicalRowBindingV2(
        profile.preregistration_id,
        _id("synthetic:context"),
        "NO_PRIOR",
        _id("synthetic:physical-row"),
    )
    shell = _Fixture(
        profile,
        row,
        _id("synthetic:discovery-chain"),
        _id("synthetic:discovery-stream"),
        _id("synthetic:validation-chain"),
        _id("synthetic:validation-stream"),
        None,  # type: ignore[arg-type]
        (),
    )
    discovery = _observations(
        shell,
        lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
        chain=shell.discovery_chain,
        stream=shell.discovery_stream,
        count=64,
        outcome_labels=("A", "B"),
        sample_domain="discovery",
    )
    epoch = confidence.freeze_initial_support_epoch_v2(
        row_binding=row,
        purpose=confidence.ConfidenceEpochPurposeV2.INITIAL_SHARED_OR_DIRECT,
        discovery_support_epoch_chain_id=shell.discovery_chain,
        discovery_stream_id=shell.discovery_stream,
        discovery_observations=discovery,
        validation_support_epoch_chain_id=shell.validation_chain,
        validation_stream_id=shell.validation_stream,
        profile=profile,
    )
    return replace(shell, epoch=epoch, discovery=discovery)


@pytest.fixture(scope="module")
def validation_2048(
    initial_fixture: _Fixture,
) -> tuple[_SyntheticControlObservation, ...]:
    return _observations(
        initial_fixture,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
        chain=initial_fixture.validation_chain,
        stream=initial_fixture.validation_stream,
        count=2_048,
        outcome_labels=("A", "B", "C", "D"),
        sample_domain="validation",
    )


@pytest.fixture(scope="module")
def snapshot_2048(
    initial_fixture: _Fixture,
    validation_2048: tuple[_SyntheticControlObservation, ...],
) -> confidence.PartialSupportConfidenceSnapshotV2:
    return confidence.build_partial_support_confidence_snapshot_v2(
        initial_fixture.epoch,
        validation_2048,
        initial_fixture.profile,
    )


def _unsafe_field(value: object, field_name: str, replacement: object) -> object:
    attacked = copy.copy(value)
    object.__setattr__(attacked, field_name, replacement)
    return attacked


def test_profile_is_exact_v072_and_does_not_change_v1_identity() -> None:
    v1_id_before = confidence_v1.v0068_partial_support_confidence_profile_v1().profile_id
    profile = confidence.v0072_partial_support_confidence_profile_v2()

    assert profile.row_epoch_beta == Fraction(1, 300_000)
    assert profile.cold_checkpoints == (2_048,)
    assert profile.direct_checkpoints == (2_048, 4_096, 8_192, 16_384)
    assert profile.new_child_checkpoints == (8_192,)
    assert profile.promotion_checkpoints == (2_048,)
    assert (
        profile.sequential_profile(
            17,
            confidence.ConfidenceEpochPurposeV2.NEW_CHILD,
        ).confidence_alpha
        == Fraction(1, 5_100_000)
    )
    assert (
        confidence_v1.v0068_partial_support_confidence_profile_v1().profile_id
        == v1_id_before
    )
    assert profile.profile_id != v1_id_before


def test_initial_snapshot_replays_exact_counts_other_and_simplex(
    snapshot_2048: confidence.PartialSupportConfidenceSnapshotV2,
) -> None:
    verification = confidence.verify_partial_support_confidence_snapshot_v2(
        snapshot_2048
    )

    assert snapshot_2048.selected_checkpoint_draw_count == 2_048
    assert snapshot_2048.novel_descriptor_ids == (
        _id("descriptor:C"),
        _id("descriptor:D"),
    )
    assert len(snapshot_2048.event_intervals) == 3
    assert sum(item.success_count for item in snapshot_2048.event_intervals) == 2_048
    assert (
        snapshot_2048.event_intervals[-1].event_kind
        is confidence.PartialSupportEventKindV2.OTHER
    )
    assert snapshot_2048.per_event_alpha == Fraction(1, 900_000)
    assert sum(snapshot_2048.joint_simplex.lower_probabilities) <= 1
    assert sum(snapshot_2048.joint_simplex.upper_probabilities) >= 1
    assert verification.snapshot_id == snapshot_2048.snapshot_id


def test_multiple_direct_checkpoints_share_one_row_epoch_authority(
    initial_fixture: _Fixture,
    snapshot_2048: confidence.PartialSupportConfidenceSnapshotV2,
) -> None:
    validation_4096 = _observations(
        initial_fixture,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
        chain=initial_fixture.validation_chain,
        stream=initial_fixture.validation_stream,
        count=4_096,
        outcome_labels=("A", "B", "C", "D"),
        sample_domain="validation",
    )
    snapshot_4096 = confidence.build_partial_support_confidence_snapshot_v2(
        initial_fixture.epoch,
        validation_4096,
        initial_fixture.profile,
    )
    series = confidence.RowConfidenceCheckpointSeriesV2(
        (snapshot_2048, snapshot_4096)
    )

    assert (
        snapshot_2048.row_confidence_epoch_id
        == snapshot_4096.row_confidence_epoch_id
    )
    assert series.row_epoch_authorities_consumed == 1
    assert series.checkpoint_alpha_spending is False
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        replace(series, row_epoch_authorities_consumed=2)


def test_promotion_unions_all_novel_and_uses_fresh_2048_validation(
    initial_fixture: _Fixture,
    snapshot_2048: confidence.PartialSupportConfidenceSnapshotV2,
) -> None:
    next_chain = _id("synthetic:promoted-chain")
    next_stream = _id("synthetic:promoted-validation-stream")
    promoted = confidence.promote_support_epoch_v2(
        snapshot_2048,
        next_support_epoch_chain_id=next_chain,
        next_validation_stream_id=next_stream,
    )
    fresh = _observations(
        initial_fixture,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
        chain=next_chain,
        stream=next_stream,
        count=2_048,
        outcome_labels=("A", "B", "C", "D"),
        sample_domain="promoted-validation",
    )
    promoted_snapshot = confidence.build_partial_support_confidence_snapshot_v2(
        promoted,
        fresh,
        initial_fixture.profile,
    )

    assert promoted.support_descriptor_ids == tuple(
        sorted(
            (
                _id("descriptor:A"),
                _id("descriptor:B"),
                _id("descriptor:C"),
                _id("descriptor:D"),
            )
        )
    )
    assert promoted.promotion_evidence.fresh_discovery_draw_count == 0
    assert set(snapshot_2048.validation_prefix.sample_ids).issubset(
        promoted.excluded_probability_sample_ids
    )
    assert promoted_snapshot.selected_checkpoint_draw_count == 2_048
    assert promoted_snapshot.novel_descriptor_ids == ()
    confidence.verify_partial_support_confidence_snapshot_v2(promoted_snapshot)


def test_wrong_beta_or_alpha_is_rejected(
    initial_fixture: _Fixture,
    snapshot_2048: confidence.PartialSupportConfidenceSnapshotV2,
) -> None:
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        replace(initial_fixture.profile, row_epoch_beta=Fraction(1, 64_000))

    attacked = _unsafe_field(
        snapshot_2048,
        "per_event_alpha",
        snapshot_2048.per_event_alpha * 2,
    )
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        confidence.verify_partial_support_confidence_snapshot_v2(attacked)  # type: ignore[arg-type]


def test_missing_other_is_rejected_by_independent_replay(
    snapshot_2048: confidence.PartialSupportConfidenceSnapshotV2,
) -> None:
    attacked = _unsafe_field(
        snapshot_2048,
        "event_intervals",
        snapshot_2048.event_intervals[:-1],
    )
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        confidence.verify_partial_support_confidence_snapshot_v2(attacked)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("context_id", _id("other-context")),
        ("arm", "SOURCE_CONSENSUS_PRIOR"),
        ("physical_row_id", _id("other-row")),
        ("support_epoch_chain_id", _id("other-chain")),
        ("stream_id", _id("other-stream")),
    ),
)
def test_context_arm_row_chain_and_stream_transplants_fail_closed(
    initial_fixture: _Fixture,
    validation_2048: tuple[_SyntheticControlObservation, ...],
    field_name: str,
    replacement: object,
) -> None:
    attacked = (replace(validation_2048[0], **{field_name: replacement}),) + (
        validation_2048[1:]
    )
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        confidence.build_partial_support_confidence_snapshot_v2(
            initial_fixture.epoch,
            attacked,
            initial_fixture.profile,
        )


def test_sample_transplant_discovery_reuse_fails_closed(
    initial_fixture: _Fixture,
    validation_2048: tuple[_SyntheticControlObservation, ...],
) -> None:
    attacked = (
        replace(validation_2048[0], sample_id=initial_fixture.discovery[0].sample_id),
    ) + validation_2048[1:]
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        confidence.build_partial_support_confidence_snapshot_v2(
            initial_fixture.epoch,
            attacked,
            initial_fixture.profile,
        )


@pytest.mark.parametrize("mode", ("gap", "reorder"))
def test_prefix_gap_or_reorder_is_rejected(
    initial_fixture: _Fixture,
    validation_2048: tuple[_SyntheticControlObservation, ...],
    mode: str,
) -> None:
    if mode == "gap":
        attacked = validation_2048[:100] + validation_2048[101:]
    else:
        attacked_list = list(validation_2048)
        attacked_list[100], attacked_list[101] = (
            attacked_list[101],
            attacked_list[100],
        )
        attacked = tuple(attacked_list)
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        confidence.build_partial_support_confidence_snapshot_v2(
            initial_fixture.epoch,
            attacked,
            initial_fixture.profile,
        )


def test_partial_novel_promotion_and_fresh_discovery_are_rejected(
    snapshot_2048: confidence.PartialSupportConfidenceSnapshotV2,
) -> None:
    promoted = confidence.promote_support_epoch_v2(
        snapshot_2048,
        next_support_epoch_chain_id=_id("attack:promoted-chain"),
        next_validation_stream_id=_id("attack:promoted-stream"),
    )
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        replace(
            promoted.promotion_evidence,
            parent_novel_descriptor_ids=(
                promoted.promotion_evidence.parent_novel_descriptor_ids[:1]
            ),
        )
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        replace(promoted.promotion_evidence, fresh_discovery_draw_count=1)


def test_old_validation_samples_cannot_be_reused_after_promotion(
    initial_fixture: _Fixture,
    snapshot_2048: confidence.PartialSupportConfidenceSnapshotV2,
) -> None:
    next_chain = _id("reuse:promoted-chain")
    next_stream = _id("reuse:promoted-stream")
    promoted = confidence.promote_support_epoch_v2(
        snapshot_2048,
        next_support_epoch_chain_id=next_chain,
        next_validation_stream_id=next_stream,
    )
    old = snapshot_2048.validation_prefix.observations
    rebound = tuple(
        _SyntheticControlObservation(
            item.preregistration_id,
            item.context_id,
            item.arm,
            item.physical_row_id,
            next_chain,
            next_stream,
            confidence.ConfidenceObservationLaneV2.VALIDATION,
            item.sequence_index,
            item.sample_id,
            item.outcome.descriptor_id,
            item.outcome.document,
        )
        for item in old
    )
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        confidence.build_partial_support_confidence_snapshot_v2(
            promoted,
            rebound,
            initial_fixture.profile,
        )


def test_support_cap_above_sixteen_is_rejected(
    initial_fixture: _Fixture,
) -> None:
    discovery = _observations(
        initial_fixture,
        lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
        chain=_id("cap:discovery-chain"),
        stream=_id("cap:discovery-stream"),
        count=17,
        outcome_labels=tuple(f"cap-{index}" for index in range(17)),
        sample_domain="cap-discovery",
    )
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        confidence.freeze_initial_support_epoch_v2(
            row_binding=initial_fixture.row,
            purpose=confidence.ConfidenceEpochPurposeV2.NEW_CHILD,
            discovery_support_epoch_chain_id=_id("cap:discovery-chain"),
            discovery_stream_id=_id("cap:discovery-stream"),
            discovery_observations=discovery,
            validation_support_epoch_chain_id=_id("cap:validation-chain"),
            validation_stream_id=_id("cap:validation-stream"),
            profile=initial_fixture.profile,
        )


def test_simplex_tampering_is_rejected_by_independent_replay(
    snapshot_2048: confidence.PartialSupportConfidenceSnapshotV2,
) -> None:
    simplex = snapshot_2048.joint_simplex
    attacked_simplex = replace(
        simplex,
        lower_probabilities=(Fraction(0),) + simplex.lower_probabilities[1:],
    )
    attacked = _unsafe_field(snapshot_2048, "joint_simplex", attacked_simplex)
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        confidence.verify_partial_support_confidence_snapshot_v2(attacked)  # type: ignore[arg-type]


def test_campaign_allocation_is_exact_union_bound_without_independence() -> None:
    allocation = confidence.v0072_campaign_confidence_allocation_v2()
    verification = (
        confidence.verify_v0072_campaign_confidence_allocation_v2(allocation)
    )

    assert allocation.maximum_row_epoch_authorities_per_arm == 480
    assert allocation.maximum_campaign_row_epoch_authorities == 2_400
    assert allocation.campaign_joint_tail_upper == Fraction(1, 125)
    assert allocation.campaign_confidence_lower == Fraction(124, 125)
    assert allocation.cross_arm_independence_required is False
    assert verification.allocation_id == allocation.allocation_id


def test_preregistration_profile_transplant_fails_closed(
    initial_fixture: _Fixture,
) -> None:
    with pytest.raises(confidence.PartialSupportConfidenceV2InvariantViolation):
        replace(initial_fixture.profile, preregistration_id=_id("wrong-prereg"))
