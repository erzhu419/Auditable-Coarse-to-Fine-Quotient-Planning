from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp import construction_k7_standard_2048_exchangeability_campaign_v5 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def campaign():
    return subject.run_standard_2048_exchangeability_campaign_v5()


def _decisions(document: dict, arm: str) -> list[dict]:
    return [
        decision
        for episode in document[arm]["episodes"]
        for decision in episode["decisions"]
    ]


def test_preregistered_identity_and_domains_are_bound(campaign) -> None:
    document = campaign.to_document()
    assert document["exchangeability_preregistration"][
        "exchangeability_preregistration_id"
    ] == subject.PREREGISTRATION_ID
    assert document["preregistration_git_commit"] == subject.PREREGISTRATION_COMMIT
    assert set(subject.DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    assert document["external_timestamp_authority_present"] is False


def test_meta_prior_reduces_fallback_but_not_offline_sample_tax(campaign) -> None:
    document = campaign.to_document()
    meta = document["structural_meta_prior_arm"]
    control = document["strict_no_prior_arm"]
    assert (meta["abstract_route_count"], meta["fallback_route_count"]) == (48, 48)
    assert (control["abstract_route_count"], control["fallback_route_count"]) == (42, 54)
    assert document["structural_meta_prior_fallback_route_saving"] == 6
    assert meta["offline_transition_observation_count"] == 147456
    assert control["offline_transition_observation_count"] == 147456
    assert document["shared_unique_offline_transition_observation_count"] == 147456
    assert document["offline_sample_tax_reduced_below_v156_fixed_budget"] is False
    assert document["meta_prior_improves_offline_sample_count"] is False


def test_all_matched_decisions_remain_exact(campaign) -> None:
    document = campaign.to_document()
    rows = _decisions(document, "structural_meta_prior_arm") + _decisions(
        document, "strict_no_prior_arm"
    )
    assert len(rows) == 192
    assert all(row["selected_action_exact_value_and_loss_equivalent"] for row in rows)
    assert all(row["selected_action_label_identical"] for row in rows)
    assert document["all_192_selected_actions_exact_value_and_loss_equivalent"] is True
    assert document["all_192_selected_action_labels_identical"] is True


def test_fallback_occurs_only_after_registered_cap_failure(campaign) -> None:
    document = campaign.to_document()
    for arm in ("structural_meta_prior_arm", "strict_no_prior_arm"):
        for row in _decisions(document, arm):
            route = row["route_decision"]
            attempts = row["certificate_attempts"]
            assert route["matched_direct_used_for_certificate_or_checkpoint_choice"] is False
            if route["route"] == "COLD_GROUND_FALLBACK":
                assert attempts[-1]["checkpoint_evidence"][
                    "source_checkpoint_per_cardinality"
                ] == 8192
                assert attempts[-1]["status"] == "FAILED_PAIRWISE_DOMINANCE"
                assert route["fallback_triggered_only_after_registered_cap_failure"] is True
                assert row["matched_direct_lane"] == "OPERATIONAL_FALLBACK"
            else:
                assert route["fallback_plan_id"] is None
                assert row["matched_direct_lane"] == "EVALUATION_ONLY"


def test_work_lanes_and_claim_boundaries_are_explicit(campaign) -> None:
    document = campaign.to_document()
    meta = document["structural_meta_prior_arm"]
    control = document["strict_no_prior_arm"]
    assert meta["operational_fallback_ground_state_action_row_count"] == 16756
    assert control["operational_fallback_ground_state_action_row_count"] == 18388
    assert meta["evaluation_cold_direct_ground_state_action_row_count"] == 15311
    assert control["evaluation_cold_direct_ground_state_action_row_count"] == 13679
    assert document["total_operational_work_saving_claimed"] is False
    assert document["formal_confirmatory_gate_claimed"] is False
    assert document["full_standard_2048_game_completed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_each_checkpoint_uses_frozen_radii(campaign) -> None:
    document = campaign.to_document()
    prereg = document["exchangeability_preregistration"]
    position = {
        row["checkpoint"]: Fraction(row["radius"])
        for row in prereg["position_radii"]
    }
    for arm in ("structural_meta_prior_arm", "strict_no_prior_arm"):
        for decision in _decisions(document, arm):
            for certificate in decision["certificate_attempts"]:
                evidence = certificate["checkpoint_evidence"]
                assert Fraction(evidence["position_radius"]) == position[
                    evidence["source_checkpoint_per_cardinality"]
                ]
                assert certificate["ground_transition_kernel_accessed"] is False
                assert certificate["cold_direct_accessed"] is False


def test_campaign_tamper_is_rejected(campaign) -> None:
    original = campaign.canonical_bytes
    attacked = campaign.to_document()
    attacked["offline_sample_tax_reduced_below_v156_fixed_budget"] = True
    object.__setattr__(campaign, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(subject.ConstructionK7Standard2048ExchangeabilityCampaignV5Error):
        campaign.__post_init__()
    object.__setattr__(campaign, "canonical_bytes", original)
    campaign.__post_init__()
