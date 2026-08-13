from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_spawn_program_v16 as program


@pytest.fixture(scope="module")
def campaign() -> program.Standard2048SpawnProgramCampaignV16:
    return program.run_standard_2048_spawn_program_campaign_v16()


def test_fresh_observations_select_one_heldout_valid_program(campaign) -> None:
    assert program.verify_standard_2048_spawn_program_campaign_v16(campaign) is campaign
    assert campaign.campaign_id == program.EXPECTED_CAMPAIGN_ID
    document = campaign.to_document()
    proposal = document["spawn_program_proposal"]
    assert proposal["selected_candidate_key"] == program.SELECTED_CANDIDATE_KEY
    assert proposal["minimum_source_mismatch_count"] == 0
    assert proposal["unique_source_selection"] is True
    assert proposal["heldout_validation_evaluation"]["mismatch_count"] == 0
    assert proposal["heldout_validation_accepted"] is True
    assert proposal["validation_read_after_source_selection"] is True
    assert proposal["source_rule_or_target_policy_accessed"] is False


def test_exact_support_proof_closes_every_registered_subset(campaign) -> None:
    proof = campaign.to_document()["spawn_program_support_proof"]
    assert proof["nonempty_proper_empty_cell_subset_count"] == 65534
    assert proof["support_row_evaluation_count"] == 1048544
    assert proof["mismatch_count"] == 0
    assert proof["exact_rational_probability_equality"] is True
    assert proof["source_access_after_proposal_freeze"] is True
    assert proof["transition_observation_count"] == 0


def test_composed_world_model_has_two_observation_proposed_components(campaign) -> None:
    model = campaign.to_document()["synthesized_world_model"]
    assert model["deterministic_swipe_component"] == (
        "OBSERVATION_PROPOSED_EXACT_PROVED_PROGRAM"
    )
    assert model["stochastic_spawn_component"] == (
        "OBSERVATION_PROPOSED_EXACT_PROVED_PROGRAM"
    )
    assert model["successors_generated_by_composed_factored_programs"] is True
    assert model["full_state_action_rows_materialized"] is False
    assert model["exact_multistep_planning_semantics_available"] is True
    assert model["ground_access_before_certificate_failure"] is False


def test_sample_tax_claim_is_positive_but_strictly_scoped(campaign) -> None:
    document = campaign.to_document()
    assert document["joint_swipe_and_spawn_observation_count"] == 1152
    assert document["matched_fixed_observation_control_count"] == 8192
    assert document["registered_observation_difference"] == 7040
    assert document["sample_tax_reduced_on_registered_observation_axis"] is True
    assert document["conditional_on_frozen_candidate_grammar_and_source_closed_proof"] is True
    assert document["total_operational_work_saving_claimed"] is False
    assert document["broad_or_physical_iid_sample_efficiency_claimed"] is False


def test_target_and_official_claims_remain_locked(campaign) -> None:
    document = campaign.to_document()
    assert document["target_transition_observation_count"] == 0
    assert document["target_planning_or_execution_performed"] is False
    assert document["full_standard_2048_game_completed"] is False
    assert document["tile_2048_reached"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_campaign_tamper_and_caller_mint_are_rejected(campaign) -> None:
    forged = copy.copy(campaign)
    object.__setattr__(forged, "campaign_id", "f" * 64)
    with pytest.raises(program.ConstructionK7Standard2048SpawnProgramV16Error):
        program.verify_standard_2048_spawn_program_campaign_v16(forged)
    with pytest.raises(program.ConstructionK7Standard2048SpawnProgramV16Error):
        program.Standard2048SpawnProgramCampaignV16(
            object(),
            campaign.canonical_bytes,
            campaign.campaign_id,
            campaign.synthesized_world_model_id,
        )
