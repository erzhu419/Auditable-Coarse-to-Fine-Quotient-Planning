from __future__ import annotations

import copy
from fractions import Fraction
import hashlib

import pytest

from acfqp import construction_k7_standard_2048_blind_expression_campaign_v22 as campaign


@pytest.fixture(scope="module")
def result() -> campaign.Standard2048BlindExpressionCampaignV22:
    return campaign.run_standard_2048_blind_expression_campaign_v22()


def test_frozen_campaign_identity_and_semantic_replay(result) -> None:
    assert campaign.verify_standard_2048_blind_expression_campaign_v22(result) is result
    assert result.campaign_id == campaign.EXPECTED_CAMPAIGN_ID
    assert len(result.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(result.canonical_bytes).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256


def test_commit_reveal_order_and_blind_proposal_boundary(result) -> None:
    document = result.to_document()
    assert document["git_ordered_commit_reveal_protocol_satisfied"] is True
    assert document["preregistration_commit_abbreviated_sha"] == "24194ad"
    assert document["target_reveal_commit_abbreviated_sha"] == "42b45b4"
    assert document["target_semantics_absent_from_preregistration_artifact"] is True
    assert document["proposal"]["target_formula_used_to_select_program"] is False
    assert document["experimenter_cognitive_blinding_claimed"] is False
    assert document["runtime_target_source_access_isolation_enforced"] is False


def test_raw_context_grammar_generates_and_selects_fresh_expression(result) -> None:
    document = result.to_document()
    pool = document["structural_pool"]
    assert pool["context_count"] == 8
    assert pool["expression_count_per_context"] == 28
    assert pool["observed_raw_rank_constants"] == list(range(9))
    assert document["generated_expression_program_candidate_count"] == 80
    assert document["queried_pool_ordinals"] == [0, 2, 4, 1]
    assert document["version_space_counts_after_queries"] == [35, 19, 8, 1]
    assert document["selected_expression_key"] == "COUNT_EQ(POST_SWIPE_BOARD_RANKS,1)"
    assert document["selected_expression_ast"] == {
        "operator": "COUNT_EQ",
        "vector_source": "POST_SWIPE_BOARD_RANKS",
        "constant": 1,
    }
    assert document["selected_threshold"] == 2


def test_four_queries_prove_exact_revealed_law(result) -> None:
    document = result.to_document()
    assert document["target_probability_query_count"] == 4
    assert [row["observed_rank_two_probability"] for row in document["acquisitions"]] == [
        Fraction(3, 20), Fraction(3, 20), Fraction(1, 10), Fraction(1, 10)
    ]
    assert document["strict_no_prior_context_query_count"] == 8
    assert document["query_reduction_against_no_prior"] == 4
    assert document["query_fraction_of_no_prior"] == Fraction(1, 2)
    assert document["proof"]["proof_row_count"] == 17
    assert document["proof"]["proof_mismatch_count"] == 0
    assert all(row["exact_match"] is True for row in document["proof"]["proof_rows"])


def test_all_fresh_h3_plans_match_cold_target_without_planning_ground_access(result) -> None:
    document = result.to_document()
    decisions = [row for episode in document["episodes"] for row in episode["decisions"]]
    assert len(decisions) == 12
    assert document["all_12_root_action_values_exactly_match_cold_target_ground"] is True
    assert document["all_12_selected_actions_exactly_match_cold_target_ground"] is True
    assert all(row["route"] == "EXACT_COMMIT_REVEAL_EXPRESSION_MODEL_CERTIFIED" for row in decisions)
    assert all(
        row["certificate"]["operational_target_probability_query_count"] == 0
        and row["certificate"]["operational_ground_state_action_row_count"] == 0
        and row["certificate_frozen_before_cold_evaluation_and_target_transition"] is True
        for row in decisions
    )


def test_scientific_and_official_claims_remain_bounded(result) -> None:
    document = result.to_document()
    assert document["conditional_on_registered_depth_one_expression_grammar"] is True
    assert document["open_ended_expression_or_coordinate_invention_completed"] is False
    assert document["broad_or_physical_iid_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["full_standard_2048_game_completed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_tamper_and_caller_mint_are_rejected(result) -> None:
    tampered = copy.copy(result)
    object.__setattr__(tampered, "campaign_id", "f" * 64)
    with pytest.raises(campaign.ConstructionK7Standard2048BlindExpressionCampaignV22Error):
        campaign.verify_standard_2048_blind_expression_campaign_v22(tampered)
    with pytest.raises(campaign.ConstructionK7Standard2048BlindExpressionCampaignV22Error):
        campaign.Standard2048BlindExpressionCampaignV22(
            object(), result.canonical_bytes, result.campaign_id
        )
