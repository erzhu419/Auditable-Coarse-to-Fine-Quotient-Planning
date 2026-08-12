from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def campaign():
    return subject.run_standard_2048_fresh_board_support_world_model_campaign_v2()


def test_fresh_roots_and_longer_episode_prefix_are_preregistered(campaign) -> None:
    document = campaign.to_document()
    preregistration = document["support_preregistration"]
    assert set(subject.DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    assert len(preregistration["registered_fresh_root_states"]) == 2
    assert preregistration["fresh_roots_not_equal_to_v1_registered_root"] is True
    assert preregistration["episode_decision_count"] == 4
    assert preregistration["planning_horizon"] == 3
    assert document["episode_count"] == 2
    assert document["total_receding_decision_count"] == 8
    assert all(episode["decision_count"] == 4 for episode in document["episodes"])


def test_row_materializer_executes_learned_support_without_exact_kernel() -> None:
    names = set(subject._materialize_partial_row.__code__.co_names)
    assert "support_ordinals_from_proposal_v2" in names
    assert "swipe_board_v1" in names
    assert "step_v1" not in names
    assert "support_outcomes_v1" not in names


def test_eight_robust_plans_match_cold_direct_and_contain_exact_values(campaign) -> None:
    document = campaign.to_document()
    decisions = [row for episode in document["episodes"] for row in episode["decisions"]]
    assert len(decisions) == 8
    for decision in decisions:
        robust = decision["certified_robust_plan"]
        direct = decision["matched_direct_control"]
        assert robust["status"] == "CERTIFIED_PARTIAL_DYNAMICS_ROBUST"
        assert robust["selected_action"] == direct["selected_action"]
        assert robust["robust_score_lower"] <= direct["expected_merge_score"]
        assert direct["expected_merge_score"] <= robust["robust_score_upper"]
        assert direct["loss_probability_within_horizon"] <= robust[
            "robust_loss_probability_upper"
        ]
        assert decision["selected_action_agrees_with_matched_direct"] is True
        assert decision["exact_direct_value_inside_robust_envelope"] is True


def test_unknown_support_score_cap_uses_only_mass_spawn_cap_and_horizon() -> None:
    state = subject.state_from_board_v1(subject.REGISTERED_FRESH_BOARDS[0])
    mass = sum((1 << rank) for rank in state.board if rank)
    assert subject._unknown_spawn_score_upper(
        state, merge_score=12, remaining=3
    ) == 12 + 2 * (mass + 4) + 4


def test_failed_proof_frontier_is_the_only_row_recovery_authority(campaign) -> None:
    document = campaign.to_document()
    decisions = [row for episode in document["episodes"] for row in episode["decisions"]]
    transactions = [tx for row in decisions for tx in row["recovery_transactions"]]
    assert transactions
    assert all(tx["failed_status"] == "FAILED_PROOF_FRONTIER" for tx in transactions)
    assert all(tx["ground_support_access_before_failed_audit"] is False for tx in transactions)
    assert all(
        tx["exact_spawn_or_position_probability_accessed_by_recovery"] is False
        for tx in transactions
    )
    assert [episode["incremental_partial_row_count"] for episode in document["episodes"]] == [
        349,
        1718,
    ]
    assert document["partial_model_ground_support_row_count"] == 2067
    assert document["matched_direct_total_ground_row_count"] == 2327


def test_sample_tax_and_claim_boundaries_remain_honest(campaign) -> None:
    document = campaign.to_document()
    telemetry = document["sample_tax_telemetry"]
    assert telemetry["offline_source_transition_observation_count"] == 131072
    assert telemetry["offline_validation_transition_observation_count"] == 16384
    assert telemetry["online_target_transition_observation_count"] == 8
    assert telemetry["scalar_crossing_claimed"] is False
    assert document["spawn_support_program_observation_derived"] is True
    assert document["spawn_position_law_observation_derived_partial"] is True
    assert document["unknown_support_mass_bounded_from_observations"] is True
    assert document["unknown_support_score_upper_uses_finite_mass_horizon_cap"] is True
    assert document["unknown_support_complete_learning_claimed"] is False
    assert document["open_ended_support_invention_claimed"] is False
    assert document["formal_exact_iid_claimed"] is False
    assert document["full_standard_2048_game_completed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_N_break_even"] is None


def test_campaign_object_rejects_content_tamper(campaign) -> None:
    original = campaign.canonical_bytes
    attacked = campaign.to_document()
    attacked["full_standard_2048_game_completed"] = True
    object.__setattr__(campaign, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048FreshBoardSupportWorldModelV2Error
    ):
        campaign.__post_init__()
    object.__setattr__(campaign, "canonical_bytes", original)
    campaign.__post_init__()
