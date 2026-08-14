from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp import construction_k7_lmb_reusable_world_model_campaign_v42 as campaign
from acfqp import construction_k7_lmb_reusable_world_model_preregistration_v42 as pre


@pytest.fixture(scope="module")
def frozen():
    return campaign.run_lmb_reusable_world_model_campaign_v42()


def test_v42_campaign_identity_and_matched_sample_tax(frozen) -> None:
    assert frozen.campaign_id == campaign.EXPECTED_CAMPAIGN_ID
    assert len(frozen.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        campaign.EXPECTED_CANONICAL_SHA256
    )
    summary = frozen.to_document()["matched_summary"]
    assert summary["structural_meta_prior_target_label_count"] == 3
    assert summary["strict_no_prior_target_label_count"] == 72
    assert summary["target_label_fraction"].numerator == 1
    assert summary["target_label_fraction"].denominator == 24
    assert summary["all_episodes_completed"] is True
    assert summary["matched_terminal_statuses"] is True


def test_v42_proposal_is_observation_derived_and_reusable(frozen) -> None:
    proposal = frozen.to_document()["primitive_proposal"]
    assert proposal["offline_source_transition_label_count"] == 49
    trace = proposal["candidate_program_trace"]
    assert len(trace["initial_candidates"]) == 9
    assert trace["surviving_after_witness_observations"] == [[2, 0], [2, 1]]
    assert trace["selected_candidate"] == [2, 0]
    assert len(trace["adaptive_disagreement_queries"]) == 1
    assert proposal["source_relations"] == list(pre.GENERIC_SOURCE_RELATIONS)
    assert proposal["meta_operators"] == list(pre.GENERIC_META_OPERATORS)
    assert sorted(
        row["compatibility_name"] for row in proposal["selected_expressions"]
    ) == list(pre.REGISTERED_SHARED_PRIMITIVES)
    assert proposal["all_source_rows_match_proposed_transition_law"] is True
    assert proposal["heldout_generation_witness_accessed"] is False
    assert proposal["query_value_reward_or_target_policy_input_present"] is False


def test_v42_all_ground_distinctions_follow_failed_certificates(frozen) -> None:
    document = frozen.to_document()
    assert len(document["episodes"]) == 12
    for episode in document["episodes"]:
        assert episode["terminal_status"] == "success"
        assert episode["full_board_cleared"] is True
        assert episode["execution_environment_step_count"] == pre.TILE_COUNT
        assert episode["target_generation_witness_access_count"] == 0
        for decision in episode["decisions"]:
            distinction = decision["local_ground_distinction"]
            if distinction is None:
                assert decision["initial_certificate"]["status"] == (
                    "CERTIFIED_MODEL_SUPPORT"
                )
                assert decision["replanned_after_local_distinction"] is False
            else:
                assert decision["initial_certificate"]["status"] == (
                    "FAILED_MISSING_SUPPORT"
                )
                assert distinction["acquired_after_failed_certificate"] is True
                assert distinction["failed_certificate_id"] == (
                    decision["initial_certificate"]["certificate_id"]
                )
                assert decision["final_certificate"]["status"] == (
                    "CERTIFIED_AFTER_LOCAL_DISTINCTION"
                )
                assert decision["replanned_after_local_distinction"] is True
            assert decision["kernel_step_during_planning"] is False
            assert decision["model_matches_execution"] is True


def test_v42_keeps_sample_compute_and_official_claims_separate(frozen) -> None:
    document = frozen.to_document()
    summary = document["matched_summary"]
    assert summary["planning_kernel_step_count"] == 0
    assert summary["labels_and_compute_axes_not_collapsed"] is True
    assert summary["structural_meta_prior_abstract_compute_events"] == 2106
    assert summary["strict_no_prior_abstract_compute_events"] == 3964
    assert document["cross_domain_general_sample_efficiency_claimed"] is False
    assert document["broad_iid_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_v42_campaign_object_rejects_identity_mutation(frozen) -> None:
    forged = copy.copy(frozen)
    object.__setattr__(forged, "campaign_id", "f" * 64)
    with pytest.raises(campaign.ConstructionK7LMBReusableWorldModelCampaignV42Error):
        campaign.verify_lmb_reusable_world_model_campaign_v42(forged)
