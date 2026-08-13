from __future__ import annotations

import copy
from fractions import Fraction
import hashlib

import pytest

from acfqp import construction_k7_standard_2048_context_program_campaign_v20 as campaign


@pytest.fixture(scope="module")
def result() -> campaign.Standard2048ContextProgramCampaignV20:
    return campaign.run_standard_2048_context_program_campaign_v20()


def test_frozen_campaign_identity_and_semantic_replay(result) -> None:
    assert campaign.verify_standard_2048_context_program_campaign_v20(result) is result
    assert result.campaign_id == campaign.EXPECTED_CAMPAIGN_ID
    assert len(result.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(result.canonical_bytes).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256


def test_raw_contexts_generate_one_unique_program_after_observation(result) -> None:
    document = result.to_document()
    archive = document["context_observation_archive"]
    assert archive["observation_count"] == 4
    assert archive["unique_probability_query_count"] == 4
    assert [row["feature_values"]["POST_SWIPE_EMPTY_COUNT"] for row in archive["rows"]] == [
        2,
        5,
        3,
        4,
    ]
    assert [row["observed_rank_two_probability"] for row in archive["rows"]] == [
        Fraction(1, 5),
        Fraction(1, 10),
        Fraction(1, 5),
        Fraction(1, 5),
    ]
    proposal = document["context_program_proposal"]
    assert proposal["candidate_count"] == 12
    assert proposal["candidates_generated_after_source_archive_freeze"] is True
    assert proposal["preenumerated_feature_threshold_candidate_list_used"] is False
    assert sum(row["source_mismatch_count"] == 0 for row in proposal["candidate_artifacts"]) == 1
    assert proposal["selected_feature_name"] == "POST_SWIPE_EMPTY_COUNT"
    assert proposal["selected_threshold"] == 4
    assert proposal["selected_base_rank_two_probability"] == Fraction(1, 10)
    assert proposal["selected_override_rank_two_probability"] == Fraction(1, 5)


def test_postproposal_exact_proof_issues_reusable_world_model(result) -> None:
    document = result.to_document()
    proof = document["context_program_proof"]
    assert proof["proposal_frozen_before_target_kernel_semantics_access"] is True
    assert proof["proof_row_count"] == 16
    assert proof["proof_mismatch_count"] == 0
    assert [row["post_swipe_empty_count"] for row in proof["proof_rows"]] == list(range(1, 17))
    assert all(row["exact_match"] is True for row in proof["proof_rows"])
    model = document["context_world_model"]
    assert model["context_program_proof_id"] == proof["context_program_proof_id"]
    assert model["exact_over_registered_target_kernel"] is True
    assert model["reusable_across_fresh_states_actions_and_episodes"] is True
    assert model["serialized_full_state_action_table_present"] is False


def test_all_fresh_h3_plans_are_abstract_and_exact(result) -> None:
    document = result.to_document()
    assert document["episode_count"] == 3
    assert document["decision_count"] == 12
    decisions = [row for episode in document["episodes"] for row in episode["decisions"]]
    assert len(decisions) == 12
    assert all(row["route"] == "EXACT_CONTEXT_PROGRAM_WORLD_MODEL_CERTIFIED" for row in decisions)
    assert all(row["all_root_action_values_exactly_equal"] is True for row in decisions)
    assert all(
        row["selected_action_exact_value_and_loss_equivalent"] is True for row in decisions
    )
    assert all(
        row["certificate"]["operational_ground_distinction_query_count"] == 0
        and row["certificate"]["operational_ground_state_action_row_count"] == 0
        for row in decisions
    )
    assert all(
        row["matched_cold_target_ground"]["lane"] == "STANDALONE_EVALUATION_ONLY"
        and row["matched_cold_target_ground"]["route_or_certificate_authority"] is False
        for row in decisions
    )


def test_sample_tax_axes_and_claim_boundaries_remain_honest(result) -> None:
    document = result.to_document()
    assert document["source_context_probability_observation_count"] == 4
    assert document["v19_strict_no_prior_query_count"] == 10
    assert document["retained_query_reduction_against_no_prior"] == 6
    assert document["context_program_query_fraction_of_no_prior"] == Fraction(2, 5)
    assert document["postproposal_exact_formula_proof_row_count"] == 16
    assert document["conditional_on_finite_human_primitive_feature_basis"] is True
    assert document["conditional_on_normalized_one_change_program_schema"] is True
    assert document["open_ended_coordinate_invention_completed"] is False
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
    with pytest.raises(campaign.ConstructionK7Standard2048ContextProgramCampaignV20Error):
        campaign.verify_standard_2048_context_program_campaign_v20(tampered)
    with pytest.raises(campaign.ConstructionK7Standard2048ContextProgramCampaignV20Error):
        campaign.Standard2048ContextProgramCampaignV20(
            object(), result.canonical_bytes, result.campaign_id
        )
