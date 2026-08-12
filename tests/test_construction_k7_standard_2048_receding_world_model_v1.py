from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_receding_world_model_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def campaign():
    return subject.run_standard_2048_receding_world_model_campaign_v1()


def test_preregistration_is_standard_4x4_and_frozen_before_models(campaign) -> None:
    assert set(subject.DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    row = campaign.to_document()["preregistration"]
    assert row["environment_semantics"] == (
        "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_SPAWN_V1"
    )
    assert len(row["source_root_state"]["board_ranks"]) == 16
    assert len(row["heldout_root_state"]["board_ranks"]) == 16
    assert row["planning_horizon"] == 3
    assert row["receding_decision_count"] == 2
    assert row["query_and_seed_frozen_before_model_construction"] is True
    assert row["matched_direct_control_frozen_before_model_construction"] is True


def test_empty_model_fails_before_any_ground_row_is_materialized(campaign) -> None:
    document = campaign.to_document()
    audit = document["initial_empty_model_audit"]
    assert audit["status"] == "FAILED_PROOF_FRONTIER"
    assert audit["missing_frontier_count"] == 2
    assert audit["abstract_plan_id"] is None
    transactions = document["first_decision_recovery_transactions"]
    assert transactions
    assert all(row["ground_access_before_failed_audit"] is False for row in transactions)
    assert all(row["failed_status"] == "FAILED_PROOF_FRONTIER" for row in transactions)


def test_h3_plan_matches_cold_direct_and_second_decision_is_incremental(campaign) -> None:
    document = campaign.to_document()
    first = document["first_decision_plan"]
    direct_first = document["matched_direct_baseline"]["first_decision"]
    assert first["status"] == "CERTIFIED"
    assert first["horizon"] == 3
    assert first["abstract_plan_id"] is not None
    assert first["selected_action"] == direct_first["selected_action"]
    assert first["expected_merge_score"] == direct_first["expected_merge_score"]
    assert first["loss_probability_within_horizon"] == direct_first[
        "loss_probability_within_horizon"
    ]

    assert document["successor_base_audit"]["status"] == "FAILED_PROOF_FRONTIER"
    assert document["second_decision_incremental_ground_row_count"] > 0
    second = document["second_decision_plan"]
    direct_second = document["matched_direct_baseline"]["second_decision"]
    assert second["status"] == "CERTIFIED"
    assert second["selected_action"] == direct_second["selected_action"]
    assert second["expected_merge_score"] == direct_second["expected_merge_score"]


def test_d4_heldout_query_reuses_final_model_with_zero_ground(campaign) -> None:
    document = campaign.to_document()
    heldout = document["heldout_d4_reuse_audit"]
    assert heldout["status"] == "CERTIFIED"
    assert heldout["horizon"] == 3
    assert document["heldout_reuse_incremental_ground_row_count"] == 0
    assert document["heldout_d4_model_reuse_without_ground"] is True
    assert heldout["world_model_id"] == document["final_world_model"]["world_model_id"]


def test_world_model_is_reused_but_full_game_and_sample_claims_stay_locked(campaign) -> None:
    document = campaign.to_document()
    assert document["standard_4x4_swipe_spawn_semantics_executed"] is True
    assert document["reusable_d4_quotient_world_model_synthesized"] is True
    assert document["ground_rows_materialized_only_after_failed_proof"] is True
    assert document["multi_step_planning_mainly_completed_in_abstract_model"] is True
    assert document["matched_cold_direct_baseline_present"] is True
    assert document["full_standard_2048_game_completed"] is False
    assert document["real_game_ui_adapter_present"] is False
    assert document["spawn_law_learned_from_observations"] is False
    assert document["unknown_support_learning_claimed"] is False
    assert document["formal_exact_iid_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_N_break_even"] is None
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_campaign_replays_exactly_and_rejects_tampering(campaign) -> None:
    subject.verify_standard_2048_receding_world_model_campaign_v1(campaign)
    original = campaign.canonical_bytes
    attacked = campaign.to_document()
    attacked["heldout_reuse_incremental_ground_row_count"] = 1
    object.__setattr__(campaign, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(subject.ConstructionK7Standard2048RecedingWorldModelV1Error):
        subject.verify_standard_2048_receding_world_model_campaign_v1(campaign)
    object.__setattr__(campaign, "canonical_bytes", original)
    subject.verify_standard_2048_receding_world_model_campaign_v1(campaign)
