import dataclasses

import pytest

from acfqp.construction_k7_joint_factor_residual_campaign_v54r1 import (
    JointFactorResidualCampaignV54R1,
    run_joint_factor_residual_campaign_v54r1,
    verify_joint_factor_residual_campaign_v54r1,
)


@pytest.fixture(scope="module")
def campaign():
    return verify_joint_factor_residual_campaign_v54r1(
        run_joint_factor_residual_campaign_v54r1()
    )


def test_v54r1_campaign_freezes_joint_discovery_without_scaffold(campaign):
    document = campaign.to_document()
    model = document["joint_world_model"]
    assert model["factorable_reusable_count"] == 3
    assert model["factorable_novel_count"] == 1
    assert model["residual_schema_bound_count"] == 2
    assert model["complete_target_program_synthesized_from_raw_observations"] is True
    assert model["shared_residual_scaffold_consumed"] is False
    assert model["predeclared_reusable_factor_slots_consumed"] is False
    assert document["v51_target_program_consumed"] is False
    assert document["v51_reused_factor_slot_inventory_consumed"] is False


def test_v54r1_campaign_has_matched_plans_and_certificate_first_recovery(campaign):
    document = campaign.to_document()
    assert len(document["structural_episodes"]) == 8
    assert [row["action_keys"] for row in document["structural_episodes"]] == [
        row["action_keys"] for row in document["strict_episodes"]
    ]
    assert all(row["success"] for row in document["structural_episodes"])
    assert len(document["failed_certificates"]) == 8
    assert len(document["local_distinctions"]) == 8
    assert all(row["query_after_failed_certificate"] for row in document["local_distinctions"])
    assert all(row["relation_outputs_consumed_for_target_binding"] is False for row in document["target_layout_calibrations"])


def test_v54r1_campaign_rejects_ood_and_keeps_axes_and_gates_locked(campaign):
    document = campaign.to_document()
    assert document["ood_rejection"]["factorable_reusable_count"] == 2
    assert document["ood_rejection"]["outcome"] == "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER"
    assert document["accounting"]["fresh_source_support_labels"] == 121
    assert document["accounting"]["target_layout_support_labels"] == 556
    assert document["accounting"]["local_ground_support_labels"] == 8
    assert document["accounting"]["structural_execution_steps"] == 48
    assert document["accounting"]["strict_execution_steps"] == 48
    assert document["accounting"]["all_axes_separate"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v54r1_campaign_rejects_foreign_values(campaign):
    with pytest.raises(dataclasses.FrozenInstanceError):
        campaign.campaign_id = "f" * 64
    with pytest.raises(Exception):
        JointFactorResidualCampaignV54R1(
            object(), campaign.canonical_bytes, campaign.campaign_id
        )
    with pytest.raises(Exception):
        verify_joint_factor_residual_campaign_v54r1(object())
