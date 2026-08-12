from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp import construction_k7_standard_2048_affine_meta_prior_v4 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def campaign():
    return subject.run_standard_2048_affine_meta_prior_campaign_v4()


def test_prior_and_rank_evidence_costs_are_explicit(campaign) -> None:
    document = campaign.to_document()
    prior = document["affine_meta_prior"]
    assert set(subject.DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    assert prior["offline_prior_training_observation_count"] == 0
    assert prior["rank_evidence"]["offline_transition_observation_count"] == 192
    assert prior["uniform_position_law_observation_derived"] is False
    assert prior["uniform_position_law_is_registered_prior"] is True
    assert prior["exact_rank_probability_accessed"] is False


def test_fresh_initial_board_campaign_uses_47_abstract_and_one_fallback(campaign) -> None:
    document = campaign.to_document()
    assert document["episode_count"] == 4
    assert document["decision_count"] == 48
    assert document["abstract_route_count"] == 47
    assert document["cold_ground_fallback_route_count"] == 1
    assert document["matched_cold_direct_operational_route_count_control"] == 48
    assert document["ground_fallback_route_count_saving_vs_direct"] == 47
    assert document["abstract_route_fraction"] == Fraction(47, 48)
    assert document["additional_model_acquisition_observation_count_during_episodes"] == 0
    assert document["all_48_selected_actions_exact_value_and_loss_equivalent"] is True
    assert document["all_48_action_labels_identical_to_cold_direct"] is True


def test_endpoint_certificates_do_not_use_ground_or_direct(campaign) -> None:
    document = campaign.to_document()
    certificates = [
        decision["affine_certificate"]
        for episode in document["episodes"]
        for decision in episode["decisions"]
    ]
    assert len(certificates) == 48
    assert all(row["ground_transition_kernel_accessed"] is False for row in certificates)
    assert all(row["cold_direct_accessed"] is False for row in certificates)
    assert all(row["exact_rank_probability_accessed"] is False for row in certificates)
    assert all(row["endpoint_dominance_sufficient_for_affine_interval"] is True for row in certificates)


def test_only_certificate_failure_has_operational_fallback(campaign) -> None:
    document = campaign.to_document()
    rows = [
        decision
        for episode in document["episodes"]
        for decision in episode["decisions"]
    ]
    fallback = [row for row in rows if row["route_decision"]["route"] == "COLD_GROUND_FALLBACK"]
    assert len(fallback) == 1
    assert fallback[0]["affine_certificate"]["status"] == "FAILED_AFFINE_ENDPOINT_DOMINANCE"
    assert fallback[0]["route_decision"]["fallback_triggered_only_by_certificate_failure"] is True
    assert fallback[0]["route_decision"]["fallback_plan_id"] is not None
    assert all(
        row["route_decision"]["fallback_plan_id"] is None
        for row in rows
        if row not in fallback
    )


def test_evaluation_work_is_separate_from_operational_fallback(campaign) -> None:
    document = campaign.to_document()
    assert document["operational_fallback_ground_state_action_row_count"] == 182
    assert document["operational_fallback_ground_outcome_count"] == 4412
    assert document["evaluation_cold_direct_ground_state_action_row_count"] == 16714
    assert document["evaluation_cold_direct_ground_outcome_count"] == 398164
    assert document["matched_direct_has_route_authority"] is False
    assert document["total_operational_work_saving_claimed"] is False


def test_claim_boundaries_remain_closed(campaign) -> None:
    document = campaign.to_document()
    assert document["offline_sample_tax_below_v3_192_claimed"] is False
    assert document["uniform_position_prior_learned_from_observations"] is False
    assert document["full_standard_2048_game_completed"] is False
    assert document["tile_2048_reached"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["externally_preregistered_before_algorithm_design"] is False
    assert document["fresh_fixture_is_formal_confirmatory_gate"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_campaign_tamper_is_rejected(campaign) -> None:
    original = campaign.canonical_bytes
    attacked = campaign.to_document()
    attacked["abstract_route_count"] = 48
    object.__setattr__(campaign, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(subject.ConstructionK7Standard2048AffineMetaPriorV4Error):
        campaign.__post_init__()
    object.__setattr__(campaign, "canonical_bytes", original)
    campaign.__post_init__()
