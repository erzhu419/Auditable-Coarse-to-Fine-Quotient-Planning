from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp import construction_k7_standard_2048_adaptive_sample_tax_v3 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def campaign():
    return subject.run_standard_2048_adaptive_sample_tax_campaign_v3()


def test_domains_profile_and_conditional_confidence_are_frozen(campaign) -> None:
    document = campaign.to_document()
    profile = document["adaptive_profile"]
    assert set(subject.DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    assert profile["source_checkpoints_per_cardinality"] == [
        8,
        32,
        128,
        512,
        2048,
        8192,
    ]
    assert profile["conditional_family_confidence_lower"] == Fraction(9999, 10000)
    assert profile["confidence_is_conditional_on_registered_iid_shared_law"] is True
    assert profile["deterministic_archives_do_not_establish_iid"] is True


def test_adaptive_and_meta_prior_reduce_registered_offline_sample_tax(campaign) -> None:
    document = campaign.to_document()
    meta = document["identity_bound_meta_prior_arm"]
    no_prior = document["strict_no_prior_arm"]
    fixed = document["fixed_budget_control_arm"]
    assert meta["offline_transition_observation_count"] == 192
    assert no_prior["offline_transition_observation_count"] == 192
    assert fixed["offline_transition_observation_count"] == 147456
    assert document["adaptive_meta_offline_saving"] == 147264
    assert document["adaptive_meta_offline_reduction"] == Fraction(767, 768)
    assert document["registered_workload_sample_tax_reduced"] is True
    assert document["accuracy_or_certificate_relaxed"] is False
    assert document[
        "all_positive_arms_preserve_same_cold_direct_value_and_loss"
    ] is True
    assert document["all_positive_arm_action_labels_identical"] is True
    assert document["meta_prior_has_incremental_saving_over_no_prior"] is False
    assert document["sample_tax_reduction_attributed_to"] == (
        "CERTIFICATE_SENSITIVE_SEQUENTIAL_STOPPING_NOT_META_PRIOR"
    )


def test_all_positive_arms_preserve_the_same_eight_decision_control(campaign) -> None:
    document = campaign.to_document()
    for key in (
        "identity_bound_meta_prior_arm",
        "strict_no_prior_arm",
        "fixed_budget_control_arm",
    ):
        workload = document[key]["final_registered_workload"]
        assert workload["decision_count"] == 8
        assert workload["all_registered_decisions_certified"] is True
        assert workload[
            "all_actions_exact_value_and_loss_equivalent_to_cold_direct"
        ] is True
        assert workload["exact_values_inside_robust_envelopes"] is True


def test_meta_prior_is_proposal_only_and_ood_abstains_exactly(campaign) -> None:
    document = campaign.to_document()
    prior = document["identity_bound_meta_prior"]
    assert prior["offline_training_observation_count"] == 0
    assert prior["source_support_proposal_id"] is None
    assert prior["observation_derived_prior"] is False
    assert prior["proposal_only"] is True
    assert prior["interval_narrowing_authority"] is False
    assert prior["certificate_authority"] is False
    assert prior["target_transition_access"] is False
    ood = document["ood_abstention_arm"]
    no_prior = document["strict_no_prior_arm"]
    for field in (
        "selected_source_checkpoint_per_cardinality",
        "selected_validation_checkpoint_per_cardinality",
        "offline_transition_observation_count",
        "final_registered_workload",
    ):
        assert ood[field] == no_prior[field]
    assert document["ood_exactly_abstains_to_no_prior"] is True


def test_initial_board_long_episode_negative_control_is_not_hidden(campaign) -> None:
    control = campaign.to_document()["actual_initial_board_long_episode_control"]
    assert control["adaptive_192_sample_value_equivalent_decisions"] == 14
    assert control["adaptive_192_sample_value_nonequivalent_decisions"] == 2
    assert control["control_status"] == "NEGATIVE_GENERALIZATION_CONTROL"
    assert control["control_not_used_for_stopping_or_saving_claim"] is True
    assert control["long_initial_board_sample_tax_solved"] is False
    fresh = campaign.to_document()["fresh_unselected_midgame_control"]
    assert fresh["adaptive_192_sample_certified_decisions_before_divergence"] == 4
    assert fresh["adaptive_192_sample_control_completed"] is False
    assert fresh["cross_board_family_sample_tax_solved"] is False


def test_claim_boundaries_remain_scoped(campaign) -> None:
    document = campaign.to_document()
    assert document["full_standard_2048_game_completed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["sample_efficiency_gate_status"] == (
        "REGISTERED_WORKLOAD_ONLY_NOT_BROAD_GATE"
    )


def test_campaign_tamper_is_rejected(campaign) -> None:
    original = campaign.canonical_bytes
    attacked = campaign.to_document()
    attacked["broad_sample_efficiency_claimed"] = True
    object.__setattr__(campaign, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(subject.ConstructionK7Standard2048AdaptiveSampleTaxV3Error):
        campaign.__post_init__()
    object.__setattr__(campaign, "canonical_bytes", original)
    campaign.__post_init__()
