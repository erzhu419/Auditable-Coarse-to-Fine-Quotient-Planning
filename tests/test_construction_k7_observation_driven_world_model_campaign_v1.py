from __future__ import annotations

import os
from pathlib import Path
import shutil

import pytest

from acfqp import construction_k7_observation_driven_world_model_campaign_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


@pytest.fixture(scope="session")
def campaign(tmp_path_factory):
    directory = tmp_path_factory.mktemp("world-model-campaign") / "campaign"
    original = subject.synthesis_v1.run_observation_driven_world_model_synthesis_v1
    preregistration_seen: list[bool] = []

    def guarded(*args, **kwargs):
        preregistration_seen.append(
            (directory / subject.PREREGISTRATION_FILENAME).is_file()
        )
        return original(*args, **kwargs)

    subject.synthesis_v1.run_observation_driven_world_model_synthesis_v1 = guarded
    try:
        result = subject.run_observation_driven_world_model_campaign_v1(
            campaign_directory=directory
        )
    finally:
        subject.synthesis_v1.run_observation_driven_world_model_synthesis_v1 = original
    return result, directory, tuple(preregistration_seen)


def test_domains_and_public_surface_are_exact() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 4
    assert set(subject.__all__) == {
        "ConstructionK7ObservationDrivenWorldModelCampaignV1Error",
        "EXPECTED_FILENAMES",
        "LOCAL_DOMAINS",
        "ObservationDrivenCampaignClosureV1",
        "ObservationDrivenCampaignFileCommitV1",
        "ObservationDrivenCampaignOccurrenceSpecV1",
        "ObservationDrivenCampaignOccurrenceV1",
        "ObservationDrivenCampaignPreregistrationV1",
        "ObservationDrivenCampaignResultV1",
        "run_observation_driven_world_model_campaign_v1",
        "verify_observation_driven_world_model_campaign_v1",
    }


def test_preregistration_precedes_every_constructor_or_route(campaign) -> None:
    _result, _directory, preregistration_seen = campaign
    assert preregistration_seen == (True, True, True, True, True)


def test_campaign_learns_each_family_once_and_reuses_it(campaign) -> None:
    result, _directory, _seen = campaign
    outcomes = tuple(row.result.to_document()["result_outcome"] for row in result.rows)
    assert outcomes == (
        "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED",
        "EXISTING_MODEL_REUSED",
        "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED",
        "EXISTING_MODEL_REUSED",
        "NO_CERTIFIABLE_CONSTRUCTOR",
    )
    assert result.rows[0].result.promotion is not None
    assert result.rows[1].result.promotion is None
    assert result.rows[2].result.promotion is not None
    assert result.rows[3].result.promotion is None
    assert result.rows[4].result.unsupported is not None


def test_catalogue_epochs_are_immutable_and_only_promotions_change_identity(
    campaign,
) -> None:
    result, _directory, _seen = campaign
    epochs = result.closure.to_document()["ordered_catalogue_epoch_ids"]
    assert len(epochs) == 6
    assert epochs[0] != epochs[1]
    assert epochs[1] == epochs[2]
    assert epochs[2] != epochs[3]
    assert epochs[3] == epochs[4] == epochs[5]
    assert tuple(item.family_key for item in result.rows[-1].result.final_catalogue.entries) == (
        "W5",
        "K6",
    )


def test_local_ground_is_bounded_to_failed_certificate_frontiers(campaign) -> None:
    result, _directory, _seen = campaign
    rows = [row.to_document() for row in result.rows]
    assert [row["incremental_local_ground_draw_count"] for row in rows] == [
        4_096,
        0,
        8_192,
        0,
        0,
    ]
    assert all(row["postconstruction_ground_draw_count"] == 0 for row in rows)
    assert result.rows[0].result.promotion is not None
    assert result.rows[0].result.promotion.dispatch.selection_outcome == "MODEL_MISS"
    assert result.rows[2].result.promotion is not None
    assert result.rows[2].result.promotion.dispatch.selection_outcome == "MODEL_MISS"
    unsupported = result.rows[4].result.unsupported
    assert unsupported is not None
    assert unsupported.to_document()["ground_access_count"] == 0
    assert unsupported.to_document()["nearby_model_transfer_attempted"] is False


def test_campaign_closes_all_denominators_without_hiding_negative_control(
    campaign,
) -> None:
    result, _directory, _seen = campaign
    closure = result.closure.to_document()
    assert closure["registered_logical_occurrence_count"] == 5
    assert closure["closed_logical_occurrence_count"] == 5
    assert closure["plan_certificate_count"] == 4
    assert closure["noncertificate_count"] == 1
    assert closure["model_construction_count"] == 2
    assert closure["exact_model_reuse_count"] == 2
    assert closure["unsupported_no_access_count"] == 1
    assert closure["cumulative_incremental_local_ground_draw_count"] == 12_288
    assert closure["nearby_model_transfer_attempt_count"] == 0


def test_seven_physical_artifacts_and_owner_verifier_close(campaign) -> None:
    result, directory, _seen = campaign
    verified = subject.verify_observation_driven_world_model_campaign_v1(
        result, campaign_directory=directory
    )
    assert verified is result
    assert tuple(path.name for path in sorted(directory.iterdir())) == subject.EXPECTED_FILENAMES
    assert tuple(item.filename for item in result.file_commits) == subject.EXPECTED_FILENAMES
    assert all(path.stat().st_size > 0 for path in directory.iterdir())


def test_physical_byte_tamper_is_rejected(campaign, tmp_path: Path) -> None:
    result, directory, _seen = campaign
    copied = tmp_path / "tampered-campaign"
    shutil.copytree(directory, copied)
    target = copied / subject.OCCURRENCE_FILENAMES[2]
    os.chmod(target, 0o600)
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(subject.ConstructionK7ObservationDrivenWorldModelCampaignV1Error):
        subject.verify_observation_driven_world_model_campaign_v1(
            result, campaign_directory=copied
        )


def test_scientific_and_official_claim_boundaries_remain_locked(campaign) -> None:
    result, _directory, _seen = campaign
    preregistration = result.preregistration.to_document()
    closure = result.closure.to_document()
    document = result.to_document()
    assert preregistration["fixed_human_constructor_registry"] is True
    assert preregistration["automatic_coordinate_primitive_invention_claimed"] is False
    assert preregistration["nearby_model_transfer_allowed"] is False
    assert closure["official_scalar_cost"] is None
    assert closure["official_N_break_even"] is None
    assert closure["scalar_gate_status"] == "NOT_RUN"
    assert closure["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["independent_campaign_verification_present"] is False
    assert document["automatic_coordinate_primitive_invention_claimed"] is False
    assert document["broad_cross_domain_generalization_claimed"] is False
    assert document["official_execution_allowed"] is False
