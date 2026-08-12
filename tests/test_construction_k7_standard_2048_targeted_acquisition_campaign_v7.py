from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_targeted_acquisition_campaign_v7 as subject
from acfqp.phase3e_ids import canonical_json_bytes


@pytest.fixture(scope="module")
def campaign():
    return subject.run_standard_2048_targeted_acquisition_campaign_v7()


def _decisions(document: dict, arm: str) -> list[dict]:
    return [
        decision
        for episode in document[arm]["episodes"]
        for decision in episode["decisions"]
    ]


def test_fresh_streams_and_preregistration_are_bound(campaign) -> None:
    document = campaign.to_document()
    assert document["targeted_acquisition_preregistration"][
        "targeted_acquisition_preregistration_id"
    ] == subject.PREREGISTRATION_ID
    assert document["preregistration_git_commit"] == subject.PREREGISTRATION_COMMIT
    assert document["targeted_source_archive"]["record_count"] == 131072
    assert document["targeted_validation_archive"]["record_count"] == 16384
    assert document["targeted_source_archive"]["physical_iid_randomness_claimed"] is False


def test_targeted_acquisition_reduces_unique_offline_sample_tax(campaign) -> None:
    document = campaign.to_document()
    targeted = document["frontier_conditioned_arm"]
    control = document["global_prefix_control_arm"]
    assert targeted["unique_offline_transition_observation_count"] == 55788
    assert control["unique_offline_transition_observation_count"] == 147456
    assert document["targeted_offline_observation_saving"] == 91668
    assert document["targeted_offline_sample_tax_reduced"] is True
    assert document["all_required_preregistered_conditions_passed"] is True


def test_route_quality_is_matched_exactly(campaign) -> None:
    document = campaign.to_document()
    targeted = document["frontier_conditioned_arm"]
    control = document["global_prefix_control_arm"]
    assert (targeted["abstract_route_count"], targeted["fallback_route_count"]) == (65, 63)
    assert (control["abstract_route_count"], control["fallback_route_count"]) == (65, 63)
    rows = _decisions(document, "frontier_conditioned_arm") + _decisions(
        document, "global_prefix_control_arm"
    )
    assert len(rows) == 256
    assert all(row["selected_action_exact_value_and_loss_equivalent"] for row in rows)
    assert all(row["selected_action_label_identical"] for row in rows)
    assert document["all_256_selected_actions_exact_value_and_loss_equivalent"] is True


def test_only_frontier_cardinalities_are_upgraded(campaign) -> None:
    targeted = campaign.to_document()["frontier_conditioned_arm"]
    assert targeted["final_source_counts_by_cardinality"] == [
        8, 8, 8, 8, 8, 8, 8, 8, 256, 8192, 8192, 8192, 8192, 8192, 8192, 8
    ]
    assert targeted["acquisition_round_count"] == 37
    for row in _decisions(campaign.to_document(), "frontier_conditioned_arm"):
        attempts = row["certificate_attempts"]
        for left, right in zip(attempts, attempts[1:]):
            frontier = set(left["failed_pairwise_frontier_cardinalities"])
            old = left["acquisition_evidence"]["source_counts_by_cardinality"]
            new = right["acquisition_evidence"]["source_counts_by_cardinality"]
            changed = {index + 1 for index, (a, b) in enumerate(zip(old, new, strict=True)) if a != b}
            assert changed <= frontier


def test_fallback_and_evaluation_lanes_are_separate(campaign) -> None:
    document = campaign.to_document()
    for arm in ("frontier_conditioned_arm", "global_prefix_control_arm"):
        for row in _decisions(document, arm):
            route = row["route_decision"]
            assert route["matched_direct_used_for_certificate_acquisition_or_route"] is False
            assert row["matched_direct_lane"] == (
                "OPERATIONAL_FALLBACK"
                if route["route"] == "COLD_GROUND_FALLBACK"
                else "EVALUATION_ONLY"
            )
            assert all(
                certificate["ground_transition_kernel_accessed"] is False
                and certificate["cold_direct_accessed"] is False
                for certificate in row["certificate_attempts"]
            )


def test_claim_boundaries_remain_closed(campaign) -> None:
    document = campaign.to_document()
    assert document["conditional_family_only"] is True
    assert document["physical_iid_randomness_claimed"] is False
    assert document["formal_confirmatory_gate_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["full_standard_2048_game_completed"] is False
    assert document["tile_2048_reached"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_is_rejected(campaign) -> None:
    original = campaign.canonical_bytes
    attacked = campaign.to_document()
    attacked["targeted_offline_observation_saving"] += 1
    object.__setattr__(campaign, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(subject.ConstructionK7Standard2048TargetedAcquisitionCampaignV7Error):
        campaign.__post_init__()
    object.__setattr__(campaign, "canonical_bytes", original)
    campaign.__post_init__()
