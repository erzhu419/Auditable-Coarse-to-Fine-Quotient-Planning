from __future__ import annotations

import copy
from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import v072_confidence_row_projection_independent_verifier_v1 as verifier
from acfqp import v072_confidence_row_projection_v1 as projection
from acfqp import v072_synthetic_row_observation_adapter_v1 as adapter
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg


def _unsafe_field(value: object, field_name: str, replacement: object) -> object:
    attacked = copy.copy(value)
    object.__setattr__(attacked, field_name, replacement)
    return attacked


@pytest.fixture(scope="module")
def cold() -> adapter.DevelopmentSyntheticRowAcquisitionV2:
    return adapter.acquire_development_synthetic_initial_row_v2()


@pytest.fixture(scope="module")
def artifact(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> projection.ConfidenceIntervalSimplexRowProjectionV1:
    binding = projection.development_synthetic_projection_row_binding_v1(
        cold
    )
    return projection.project_confidence_snapshot_to_interval_row_v1(
        cold.confidence_snapshot,
        binding,
    )


def test_independent_verifier_recomputes_snapshot_registry_and_row(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    result = verifier.verify_v072_confidence_row_projection_v1(artifact)
    assert result.projection_id == artifact.projection_id
    assert result.interval_row_id == artifact.interval_row.row_id
    assert result.support_mass_count == len(
        artifact.observed_destinations
    )
    assert result.other_mass_count == 1
    assert result.exact_row_reward == Fraction(1, 16)
    assert result.registered_target_evidence_count == 0


def test_independent_verifier_accepts_prefix_extension_and_promotion(
    cold: adapter.DevelopmentSyntheticRowAcquisitionV2,
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    extended = adapter.extend_development_synthetic_row_prefix_v2(
        cold,
        validation_checkpoint=4_096,
    )
    extended_artifact = (
        projection.project_confidence_snapshot_to_interval_row_v1(
            extended.confidence_snapshot,
            artifact.row_binding,
        )
    )
    promoted = adapter.promote_development_synthetic_row_support_v2(cold)
    promoted_artifact = (
        projection.project_confidence_snapshot_to_interval_row_v1(
            promoted.confidence_snapshot,
            artifact.row_binding,
        )
    )
    assert verifier.verify_v072_confidence_row_projection_v1(
        extended_artifact
    ).confidence_snapshot_id == extended.confidence_snapshot.snapshot_id
    assert verifier.verify_v072_confidence_row_projection_v1(
        promoted_artifact
    ).support_mass_count > len(artifact.observed_destinations)


def test_probability_endpoint_tamper_is_rejected(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    event = artifact.event_projections[0]
    attacked_event = _unsafe_field(
        event,
        "lower_probability",
        Fraction(0),
    )
    attacked = _unsafe_field(
        artifact,
        "event_projections",
        (attacked_event,) + artifact.event_projections[1:],
    )
    with pytest.raises(
        verifier.V072ConfidenceRowProjectionIndependentVerificationFailure
    ):
        verifier.verify_v072_confidence_row_projection_v1(attacked)


@pytest.mark.parametrize("mode", ("missing", "duplicate"))
def test_missing_or_duplicate_event_is_rejected(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
    mode: str,
) -> None:
    events = artifact.event_projections
    attacked_events = (
        events[:-1]
        if mode == "missing"
        else (events[0],) + events
    )
    attacked = _unsafe_field(
        artifact, "event_projections", attacked_events
    )
    with pytest.raises(
        verifier.V072ConfidenceRowProjectionIndependentVerificationFailure
    ):
        verifier.verify_v072_confidence_row_projection_v1(attacked)


@pytest.mark.parametrize("mode", ("missing", "duplicate"))
def test_missing_or_duplicate_destination_is_rejected(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
    mode: str,
) -> None:
    destinations = artifact.observed_destinations
    attacked_destinations = (
        destinations[:-1]
        if mode == "missing"
        else (destinations[0],) + destinations
    )
    attacked = _unsafe_field(
        artifact, "observed_destinations", attacked_destinations
    )
    with pytest.raises(
        verifier.V072ConfidenceRowProjectionIndependentVerificationFailure
    ):
        verifier.verify_v072_confidence_row_projection_v1(attacked)


def test_reward_attack_is_rejected(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    row = _unsafe_field(
        artifact.interval_row,
        "reward_upper",
        artifact.interval_row.reward_upper + Fraction(1, 100),
    )
    attacked = _unsafe_field(artifact, "interval_row", row)
    with pytest.raises(
        verifier.V072ConfidenceRowProjectionIndependentVerificationFailure
    ):
        verifier.verify_v072_confidence_row_projection_v1(attacked)


def test_horizon_attack_is_rejected(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    binding = _unsafe_field(
        artifact.row_binding,
        "remaining_horizon",
        1,
    )
    attacked = _unsafe_field(artifact, "row_binding", binding)
    with pytest.raises(
        verifier.V072ConfidenceRowProjectionIndependentVerificationFailure
    ):
        verifier.verify_v072_confidence_row_projection_v1(attacked)


def test_destination_category_attack_is_rejected(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    destination = _unsafe_field(
        artifact.observed_destinations[0],
        "category",
        robust.DestinationCategory.FAILURE,
    )
    attacked = _unsafe_field(
        artifact,
        "observed_destinations",
        (destination,) + artifact.observed_destinations[1:],
    )
    with pytest.raises(
        verifier.V072ConfidenceRowProjectionIndependentVerificationFailure
    ):
        verifier.verify_v072_confidence_row_projection_v1(attacked)


def test_other_destination_attack_is_rejected(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    other = _unsafe_field(
        artifact.other_destination,
        "failure_value",
        Fraction(0),
    )
    attacked = _unsafe_field(artifact, "other_destination", other)
    with pytest.raises(
        verifier.V072ConfidenceRowProjectionIndependentVerificationFailure
    ):
        verifier.verify_v072_confidence_row_projection_v1(attacked)


def test_other_mass_duplicate_attack_is_rejected(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    other_mass = artifact.interval_row.other_mass
    row = _unsafe_field(
        artifact.interval_row,
        "masses",
        artifact.interval_row.masses + (other_mass,),
    )
    attacked = _unsafe_field(artifact, "interval_row", row)
    with pytest.raises(
        verifier.V072ConfidenceRowProjectionIndependentVerificationFailure
    ):
        verifier.verify_v072_confidence_row_projection_v1(attacked)


def test_snapshot_cross_arm_transplant_is_rejected(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    other = adapter.acquire_development_synthetic_initial_row_v2(
        arm="SOURCE_CONSENSUS_PRIOR"
    )
    attacked = _unsafe_field(
        artifact,
        "confidence_snapshot",
        other.confidence_snapshot,
    )
    with pytest.raises(
        verifier.V072ConfidenceRowProjectionIndependentVerificationFailure
    ):
        verifier.verify_v072_confidence_row_projection_v1(attacked)


def test_novel_descriptor_cannot_be_added_as_support_mass_pre_promotion(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    novel = artifact.confidence_snapshot.novel_descriptors[0]
    destination = _unsafe_field(
        artifact.observed_destinations[0],
        "descriptor",
        novel,
    )
    attacked = _unsafe_field(
        artifact,
        "observed_destinations",
        (destination,) + artifact.observed_destinations[1:],
    )
    with pytest.raises(
        verifier.V072ConfidenceRowProjectionIndependentVerificationFailure
    ):
        verifier.verify_v072_confidence_row_projection_v1(attacked)


def test_independent_verifier_does_not_call_production_projector() -> None:
    source = inspect.getsource(verifier)
    forbidden = (
        "project_confidence_snapshot_to_interval_row_v1(",
        "development_synthetic_projection_row_binding_v1(",
        "_descriptor_semantics(",
        "_expected_components(",
        "_validate_projection(",
    )
    assert not any(item in source for item in forbidden)


def test_projection_and_verification_do_not_rebuild_hidden_law(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("projection attempted hidden-law/prereg rebuild")

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
    binding = projection.PublicStateActionRowBindingV1(
        artifact.row_binding.preregistration_id,
        artifact.row_binding.context_id,
        artifact.row_binding.arm,
        artifact.row_binding.physical_row_id,
        artifact.row_binding.confidence_row_binding_id,
        artifact.row_binding.state_ranks,
        artifact.row_binding.remaining_horizon,
        artifact.row_binding.action,
    )
    rebuilt = projection.project_confidence_snapshot_to_interval_row_v1(
        artifact.confidence_snapshot,
        binding,
    )
    result = verifier.verify_v072_confidence_row_projection_v1(rebuilt)
    assert result.projection_id == rebuilt.projection_id
