from __future__ import annotations

import copy
from fractions import Fraction
import hashlib

import pytest

from acfqp import construction_k7_standard_2048_expression_program_campaign_v21 as campaign


@pytest.fixture(scope="module")
def result() -> campaign.Standard2048ExpressionProgramCampaignV21:
    return campaign.run_standard_2048_expression_program_campaign_v21()


def test_frozen_expression_campaign_identity_and_replay(result) -> None:
    assert campaign.verify_standard_2048_expression_program_campaign_v21(result) is result
    assert result.campaign_id == campaign.EXPECTED_CAMPAIGN_ID
    assert len(result.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(result.canonical_bytes).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256


def test_raw_context_pool_generates_primitive_expressions_without_labels(result) -> None:
    document = result.to_document()
    pool = document["structural_context_pool"]
    assert pool["context_count"] == 8
    assert pool["expression_count_per_context"] == 26
    assert pool["observed_raw_rank_constants"] == list(range(8))
    assert pool["all_expression_values_frozen_before_first_target_probability_query"] is True
    assert pool["target_probability_or_formula_present"] is False
    assert pool["named_empty_count_or_v20_feature_basis_present"] is False
    assert all(
        "observed_rank_two_probability" not in row and len(row["expression_values"]) == 26
        for row in pool["rows"]
    )


def test_four_active_queries_reduce_78_candidates_to_one(result) -> None:
    document = result.to_document()
    assert document["generated_expression_program_candidate_count"] == 78
    assert document["target_probability_query_count"] == 4
    assert document["queried_pool_ordinals"] == [0, 2, 1, 3]
    assert document["version_space_counts_after_queries"] == [31, 14, 7, 1]
    acquisitions = document["expression_acquisitions"]
    assert acquisitions[0]["candidate_count_before"] is None
    assert acquisitions[0]["candidates_generated_after_this_query"] is True
    assert all(row["full_state_action_outcome_row_materialized"] is False for row in acquisitions)
    assert [row["observed_rank_two_probability"] for row in acquisitions] == [
        Fraction(1, 5),
        Fraction(1, 10),
        Fraction(1, 5),
        Fraction(1, 10),
    ]


def test_expression_is_synthesized_then_exactly_proved(result) -> None:
    document = result.to_document()
    proposal = document["expression_proposal"]
    assert proposal["selected_expression_key"] == "COUNT_EQ(POST_SWIPE_BOARD_RANKS,0)"
    assert proposal["selected_expression_ast"] == {
        "operator": "COUNT_EQ",
        "vector_source": "POST_SWIPE_BOARD_RANKS",
        "constant": 0,
    }
    assert proposal["selected_threshold"] == 4
    assert proposal["named_empty_count_feature_supplied_to_synthesizer"] is False
    assert proposal["unique_program_consistent_with_all_queried_contexts"] is True
    proof = document["expression_proof"]
    assert proof["normalization_rewrite"] == (
        "COUNT_EQ(POST_SWIPE_BOARD_RANKS,0)=POST_SWIPE_EMPTY_COUNT"
    )
    assert proof["proof_row_count"] == 16
    assert proof["proof_mismatch_count"] == 0
    assert all(row["exact_match"] is True for row in proof["proof_rows"])


def test_all_fresh_plans_use_the_expression_model_and_match_target(result) -> None:
    document = result.to_document()
    decisions = [row for episode in document["episodes"] for row in episode["decisions"]]
    assert document["episode_count"] == 3
    assert document["decision_count"] == 12
    assert len(decisions) == 12
    assert all(row["route"] == "EXACT_RAW_CONTEXT_EXPRESSION_MODEL_CERTIFIED" for row in decisions)
    assert all(row["all_root_action_values_exactly_equal"] is True for row in decisions)
    assert all(
        row["certificate"]["operational_target_probability_query_count"] == 0
        and row["certificate"]["operational_ground_state_action_row_count"] == 0
        for row in decisions
    )
    assert all(
        row["matched_cold_target_ground"]["lane"] == "STANDALONE_EVALUATION_ONLY"
        and row["matched_cold_target_ground"]["route_or_certificate_authority"] is False
        for row in decisions
    )


def test_sample_tax_and_scientific_claims_remain_bounded(result) -> None:
    document = result.to_document()
    assert document["retained_query_reduction_against_no_prior"] == 6
    assert document["expression_query_fraction_of_no_prior"] == Fraction(2, 5)
    assert document["named_empty_count_or_v20_feature_basis_supplied_to_synthesizer"] is False
    assert document["v20_result_used_during_v21_grammar_and_fixture_design"] is True
    assert document["blind_new_target_discovery_claimed"] is False
    assert document["conditional_on_registered_depth_one_reducer_grammar"] is True
    assert document["open_ended_expression_or_coordinate_invention_completed"] is False
    assert document["broad_or_physical_iid_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["full_standard_2048_game_completed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_and_caller_mint_are_rejected(result) -> None:
    tampered = copy.copy(result)
    object.__setattr__(tampered, "campaign_id", "f" * 64)
    with pytest.raises(campaign.ConstructionK7Standard2048ExpressionProgramCampaignV21Error):
        campaign.verify_standard_2048_expression_program_campaign_v21(tampered)
    with pytest.raises(campaign.ConstructionK7Standard2048ExpressionProgramCampaignV21Error):
        campaign.Standard2048ExpressionProgramCampaignV21(
            object(), result.canonical_bytes, result.campaign_id
        )
