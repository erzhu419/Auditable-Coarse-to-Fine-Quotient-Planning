from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp import construction_k7_standard_2048_multiseed_partial_world_model_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def campaign():
    return subject.run_standard_2048_multiseed_partial_world_model_campaign_v1()


def test_multiseed_preregistration_separates_source_and_targets(campaign) -> None:
    document = campaign.to_document()
    preregistration = document["statistical_preregistration"]
    assert set(subject.DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    assert preregistration["planning_horizon"] == 3
    assert preregistration["episode_decision_count"] == 3
    assert preregistration["heldout_episode_seeds"] == list(subject.HELDOUT_EPISODE_SEEDS)
    assert preregistration["source_and_target_identities_disjoint"] is True
    assert preregistration[
        "episode_seeds_and_matched_controls_frozen_before_model_construction"
    ] is True


def test_nine_receding_decisions_match_cold_direct_and_respect_envelopes(campaign) -> None:
    document = campaign.to_document()
    decisions = [row for episode in document["episodes"] for row in episode["decisions"]]
    assert document["episode_count"] == 3
    assert document["total_receding_decision_count"] == len(decisions) == 9
    assert all(row["selected_action_agrees_with_matched_direct"] is True for row in decisions)
    assert all(row["exact_direct_value_inside_robust_envelope"] is True for row in decisions)
    for row in decisions:
        robust = row["certified_robust_plan"]
        direct = row["matched_direct_control"]
        assert robust["status"] == "CERTIFIED_INTERVAL_ROBUST"
        assert robust["selected_action"] == direct["selected_action"]
        assert robust["robust_score_lower"] <= direct["expected_merge_score"]
        assert direct["expected_merge_score"] <= robust["robust_score_upper"]
        assert direct["loss_probability_within_horizon"] <= robust[
            "robust_loss_probability_upper"
        ]


def test_recovery_is_failure_triggered_and_model_reuses_across_episodes(campaign) -> None:
    document = campaign.to_document()
    decisions = [row for episode in document["episodes"] for row in episode["decisions"]]
    transactions = [tx for decision in decisions for tx in decision["recovery_transactions"]]
    assert transactions
    assert all(tx["failed_status"] == "FAILED_PROOF_FRONTIER" for tx in transactions)
    assert all(tx["ground_support_access_before_failed_audit"] is False for tx in transactions)
    assert all(tx["exact_spawn_probability_accessed_by_recovery"] is False for tx in transactions)
    assert document["episodes"][0]["incremental_partial_row_count"] == 419
    assert document["episodes"][1]["decisions"][0]["incremental_partial_row_count"] == 0
    assert document["episodes"][2]["decisions"][0]["incremental_partial_row_count"] == 0
    assert document["partial_model_ground_support_row_count"] == 980
    assert document["matched_direct_total_ground_row_count"] == 1313


def test_partial_row_materializer_cannot_read_exact_spawn_probabilities() -> None:
    names = set(subject._materialize_partial_row.__code__.co_names)
    assert "support_outcomes_v1" in names
    assert "step_v1" not in names


def test_spawn_rank_is_observation_derived_but_support_and_iid_claims_stay_honest(campaign) -> None:
    document = campaign.to_document()
    interval = document["source_observation_evidence"]["interval"]
    assert interval["rank_two_probability_lower"] == Fraction(37, 512)
    assert interval["rank_two_probability_upper"] == Fraction(69, 512)
    assert document["spawn_rank_law_observation_derived_partial"] is True
    assert document["spawn_position_law_known_structural"] is True
    assert document["formal_exact_iid_claimed"] is False
    assert document["unknown_support_learning_claimed"] is False
    assert document["full_standard_2048_game_completed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_N_break_even"] is None


def test_campaign_bytes_reject_tampering_without_semantic_replay(campaign) -> None:
    original = campaign.canonical_bytes
    attacked = campaign.to_document()
    attacked["broad_sample_efficiency_claimed"] = True
    object.__setattr__(campaign, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048MultiseedPartialWorldModelV1Error
    ):
        campaign.__post_init__()
    object.__setattr__(campaign, "canonical_bytes", original)
    campaign.__post_init__()
