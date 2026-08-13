from __future__ import annotations

import copy
from fractions import Fraction
import hashlib

import pytest

from acfqp import construction_k7_standard_2048_expression_long_campaign_v23 as campaign


@pytest.fixture(scope="module")
def result() -> campaign.Standard2048ExpressionLongCampaignV23:
    return campaign.run_standard_2048_expression_long_campaign_v23()


def test_frozen_long_campaign_identity_and_replay(result) -> None:
    assert campaign.verify_standard_2048_expression_long_campaign_v23(result) is result
    assert result.campaign_id == campaign.EXPECTED_CAMPAIGN_ID
    assert len(result.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(result.canonical_bytes).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256


def test_all_128_long_real_start_decisions_use_immutable_expression_model(result) -> None:
    document = result.to_document()
    decisions = [row for episode in document["episodes"] for row in episode["decisions"]]
    assert document["episode_count"] == 4
    assert document["decision_count"] == 128
    assert document["model_certificate_count"] == 128
    assert document["local_ground_recovery_count"] == 0
    assert all(episode["decision_count"] == 32 for episode in document["episodes"])
    assert all(
        row["route"] == "PERSISTENT_EXPRESSION_WORLD_MODEL_CERTIFIED"
        and row["certificate"]["operational_target_probability_query_count"] == 0
        and row["certificate"]["operational_ground_state_action_row_count"] == 0
        and row["certificate_frozen_before_cold_checkpoint_and_target_transition"] is True
        for row in decisions
    )


def test_persistent_cache_reuses_exact_subproofs_without_precision_loss(result) -> None:
    document = result.to_document()
    assert document["cross_decision_subproof_cache_hit_count"] == 3_243_300
    assert document["factored_action_row_evaluation_count"] == 712_602
    assert document["factored_support_outcome_evaluation_count"] == 14_357_186
    assert document["persistent_subproof_cache_preserved_exact_values"] is True
    assert all(
        episode["cross_decision_subproof_cache_hit_count"] > 0
        for episode in document["episodes"]
    )


def test_all_registered_cold_checkpoints_match_exact_target_ground(result) -> None:
    document = result.to_document()
    checkpoints = [
        row
        for episode in document["episodes"]
        for row in episode["decisions"]
        if row["cold_target_checkpoint"] is not None
    ]
    assert document["cold_evaluation_checkpoint_count"] == 12
    assert len(checkpoints) == 12
    assert document["all_checkpoint_root_values_and_actions_exactly_equal"] is True
    assert all(row["checkpoint_root_values_and_action_exactly_equal"] is True for row in checkpoints)
    assert all(
        row["cold_target_checkpoint"]["lane"] == "STANDALONE_EVALUATION_ONLY"
        and row["cold_target_checkpoint"]["route_or_certificate_authority"] is False
        for row in checkpoints
    )


def test_sample_tax_is_amortized_on_registered_label_axis(result) -> None:
    document = result.to_document()
    assert document["inherited_target_probability_label_count"] == 4
    assert document["additional_model_acquisition_label_count"] == 0
    assert document["strict_no_prior_context_label_count"] == 8
    assert document["target_label_difference_against_no_prior"] == 4
    assert document["inherited_label_fraction_of_no_prior"] == Fraction(1, 2)
    assert document["certified_decisions_per_acquired_target_label"] == 32
    assert document["sample_tax_outcome"] == (
        "POSITIVE_AMORTIZED_TARGET_LABEL_REUSE_OVER_LONG_REAL_START_WORKLOAD"
    )
    assert document["proof_planning_execution_and_evaluation_axes_reported_separately"] is True


def test_full_game_and_official_claims_remain_locked(result) -> None:
    document = result.to_document()
    assert document["maximum_final_board_tile_rank"] == 6
    assert document["tile_2048_reached"] is False
    assert document["full_standard_2048_game_completed"] is False
    assert document["broad_or_physical_iid_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_tamper_and_caller_mint_are_rejected(result) -> None:
    tampered = copy.copy(result)
    object.__setattr__(tampered, "campaign_id", "f" * 64)
    with pytest.raises(campaign.ConstructionK7Standard2048ExpressionLongCampaignV23Error):
        campaign.verify_standard_2048_expression_long_campaign_v23(tampered)
    with pytest.raises(campaign.ConstructionK7Standard2048ExpressionLongCampaignV23Error):
        campaign.Standard2048ExpressionLongCampaignV23(
            object(), result.canonical_bytes, result.campaign_id
        )
