from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import inspect
from typing import Mapping

import pytest

from acfqp import partial_support_confidence_v2 as confidence
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import v072_confidence_row_projection_v1 as projection
from acfqp import v072_synthetic_row_observation_adapter_v1 as adapter
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def cold() -> adapter.DevelopmentSyntheticRowAcquisitionV2:
    return adapter.acquire_development_synthetic_initial_row_v2()


@pytest.fixture(scope="module")
def initial_projection(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> projection.ConfidenceIntervalSimplexRowProjectionV1:
    binding = projection.development_synthetic_projection_row_binding_v1(
        cold
    )
    return projection.project_confidence_snapshot_to_interval_row_v1(
        cold.confidence_snapshot,
        binding,
    )


def test_initial_projection_preserves_exact_events_and_unique_other(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
    initial_projection: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    artifact = initial_projection
    events = cold.confidence_snapshot.event_intervals
    by_destination = {
        item.destination_id: item for item in artifact.interval_row.masses
    }
    assert len(artifact.observed_destinations) == len(events) - 1
    assert len(artifact.event_projections) == len(events)
    assert len(artifact.registered_destinations) == len(events)
    assert sum(
        item.category is robust.DestinationCategory.OTHER
        for item in artifact.registered_destinations
    ) == 1
    for event, event_projection in zip(events, artifact.event_projections):
        mass = by_destination[event_projection.destination_id]
        assert mass.lower == event.lower_probability
        assert mass.upper == event.upper_probability
    assert artifact.interval_row.reward_lower == Fraction(1, 16)
    assert artifact.interval_row.reward_upper == Fraction(1, 16)
    assert artifact.exact_row_reward == Fraction(1, 16)
    assert artifact.row_binding.rank_cap == 4
    assert (
        artifact.row_binding.rank_profile
        == projection.DEVELOPMENT_RANK_PROFILE
    )
    assert (
        sum(item.lower for item in artifact.interval_row.masses)
        <= 1
        <= sum(item.upper for item in artifact.interval_row.masses)
    )


def test_validation_novel_descriptors_remain_only_in_other_until_promotion(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
    initial_projection: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    novel = set(cold.confidence_snapshot.novel_descriptor_ids)
    assert novel
    assert novel == set(
        initial_projection.validation_novel_descriptor_ids
    )
    assert not novel & {
        item.descriptor.descriptor_id
        for item in initial_projection.observed_destinations
    }
    assert initial_projection.event_projections[-1].event_key == "OTHER"
    assert initial_projection.event_projections[-1].descriptor_id is None

    promoted = adapter.promote_development_synthetic_row_support_v2(cold)
    promoted_projection = (
        projection.project_confidence_snapshot_to_interval_row_v1(
            promoted.confidence_snapshot,
            initial_projection.row_binding,
        )
    )
    assert novel <= {
        item.descriptor.descriptor_id
        for item in promoted_projection.observed_destinations
    }
    assert len(promoted_projection.observed_destinations) > len(
        initial_projection.observed_destinations
    )


def test_prefix_extension_reuses_destination_registry_but_updates_intervals(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
    initial_projection: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    extended = adapter.extend_development_synthetic_row_prefix_v2(
        cold,
        validation_checkpoint=4_096,
    )
    extended_projection = (
        projection.project_confidence_snapshot_to_interval_row_v1(
            extended.confidence_snapshot,
            initial_projection.row_binding,
        )
    )
    assert tuple(
        item.destination_id for item in extended_projection.observed_destinations
    ) == tuple(
        item.destination_id for item in initial_projection.observed_destinations
    )
    assert (
        extended_projection.other_destination.destination_id
        == initial_projection.other_destination.destination_id
    )
    assert extended_projection.interval_row.row_id != (
        initial_projection.interval_row.row_id
    )
    assert extended_projection.projection_id != initial_projection.projection_id


@dataclass(frozen=True)
class _Observation:
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


def _h1_projection(
) -> projection.ConfidenceIntervalSimplexRowProjectionV1:
    preregistration_id = (
        prereg.freeze_transfer_guided_acquisition_preregistration_v1()
        .preregistration_id
    )
    context_id = _id("v072-h1-synthetic-projection-context")
    physical_row_id = _id("v072-h1-synthetic-physical-row")
    arm = "NO_PRIOR"
    confidence_row = confidence.ConfidencePhysicalRowBindingV2(
        preregistration_id,
        context_id,
        arm,
        physical_row_id,
    )
    binding = projection.PublicStateActionRowBindingV1(
        preregistration_id,
        context_id,
        arm,
        physical_row_id,
        confidence_row.row_binding_id,
        (1, 1, 2, 0),
        1,
        (0, 1, 0),
    )
    discovery_chain = _id("v072-h1-discovery-chain")
    discovery_stream = _id("v072-h1-discovery-stream")
    validation_chain = _id("v072-h1-validation-chain")
    validation_stream = _id("v072-h1-validation-stream")
    reward = Fraction(1, 16)
    outcomes = (
        (
            _id("v072-h1-success-descriptor"),
            {
                "next_state": {
                    "ranks": [2, 0, 2, 1],
                    "failure": False,
                },
                "realized_row_reward": reward,
                "failure": False,
                "terminal": True,
                "synthetic_control": True,
            },
        ),
        (
            _id("v072-h1-failure-descriptor"),
            {
                "next_state": {
                    "ranks": [2, 0, 2, 2],
                    "failure": True,
                },
                "realized_row_reward": reward,
                "failure": True,
                "terminal": True,
                "synthetic_control": True,
            },
        ),
    )

    def observations(
        lane: confidence.ConfidenceObservationLaneV2,
        chain: str,
        stream: str,
        count: int,
        prefix: str,
    ) -> tuple[_Observation, ...]:
        return tuple(
            _Observation(
                preregistration_id,
                context_id,
                arm,
                physical_row_id,
                chain,
                stream,
                lane,
                index,
                _id(f"{prefix}:sample:{index}"),
                outcomes[(index - 1) % 2][0],
                outcomes[(index - 1) % 2][1],
            )
            for index in range(1, count + 1)
        )

    discovery = observations(
        confidence.ConfidenceObservationLaneV2.DISCOVERY,
        discovery_chain,
        discovery_stream,
        64,
        "h1-discovery",
    )
    epoch = confidence.freeze_initial_support_epoch_v2(
        row_binding=confidence_row,
        purpose=confidence.ConfidenceEpochPurposeV2.INITIAL_SHARED_OR_DIRECT,
        discovery_support_epoch_chain_id=discovery_chain,
        discovery_stream_id=discovery_stream,
        discovery_observations=discovery,
        validation_support_epoch_chain_id=validation_chain,
        validation_stream_id=validation_stream,
    )
    validation = observations(
        confidence.ConfidenceObservationLaneV2.VALIDATION,
        validation_chain,
        validation_stream,
        2_048,
        "h1-validation",
    )
    snapshot = confidence.build_partial_support_confidence_snapshot_v2(
        epoch, validation
    )
    return projection.project_confidence_snapshot_to_interval_row_v1(
        snapshot, binding
    )


def test_root_active_h1_success_and_failure_destination_semantics(
    initial_projection: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    assert {
        item.category for item in initial_projection.observed_destinations
    } == {robust.DestinationCategory.ACTIVE_STATE}
    assert all(
        item.state_id is not None
        for item in initial_projection.observed_destinations
    )

    h1 = _h1_projection()
    categories = {item.category for item in h1.observed_destinations}
    assert categories == {
        robust.DestinationCategory.SUCCESS_TERMINAL,
        robust.DestinationCategory.FAILURE,
    }
    assert all(item.state_id is None for item in h1.observed_destinations)
    assert h1.interval_row.remaining_horizon == 1


def test_projector_accepts_no_probability_reward_or_count_endpoints() -> None:
    parameters = inspect.signature(
        projection.project_confidence_snapshot_to_interval_row_v1
    ).parameters
    assert tuple(parameters) == ("snapshot", "row_binding")


def test_registered_target_projection_requires_independent_replay_mint() -> None:
    support = projection.RegisteredConfidenceEventIntervalV1(
        _id("future-registered-support-event"),
        0,
        projection.RegisteredConfidenceEventKindV1.SUPPORT,
        _id("future-registered-support-descriptor"),
        Fraction(1, 4),
        Fraction(3, 4),
    )
    other = projection.RegisteredConfidenceEventIntervalV1(
        _id("future-registered-other-event"),
        1,
        projection.RegisteredConfidenceEventKindV1.OTHER,
        None,
        Fraction(1, 4),
        Fraction(3, 4),
    )
    assert support.event_id != other.event_id
    assert projection.REGISTERED_TARGET_CONFIDENCE_AUTHORITY_ENABLED is True
    assert projection.REGISTERED_TARGET_PROJECTION_STATUS == (
        "ENABLED_ONLY_BY_EXACT_ANCHOR_AND_INDEPENDENT_TRANSCRIPT_REPLAY"
    )
    with pytest.raises(
        projection.V072ConfidenceRowProjectionInvariantViolation
    ):
        projection.RegisteredTargetConfidenceProjectionAuthorityV1(
            object(),
            _id("future-anchor"),
            _id("future-final-preregistration"),
            object(),  # type: ignore[arg-type]
            (support, other),
            _id("future-discovery-transcript"),
            _id("future-validation-transcript"),
            _id("future-validation-prefix"),
            _id("future-confidence-verification"),
            2_048,
        )
    with pytest.raises(
        projection.RegisteredTargetConfidenceProjectionLockedV1
    ):
        projection.project_registered_target_confidence_row_v1(
            anchor=object(),  # type: ignore[arg-type]
            confidence_authority=object(),  # type: ignore[arg-type]
        )
