from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_lmb_witness_blind_campaign_v43 as campaign
from acfqp import construction_k7_lmb_witness_blind_preregistration_v43 as pre


@pytest.fixture(scope="module")
def frozen():
    return campaign.run_lmb_witness_blind_campaign_v43()


def test_v43_campaign_identity_and_witness_blind_source_synthesis(frozen) -> None:
    assert frozen.campaign_id == campaign.EXPECTED_CAMPAIGN_ID
    assert len(frozen.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        campaign.EXPECTED_CANONICAL_SHA256
    )
    proposal = frozen.to_document()["proposal"]
    assert proposal["selected_candidate"] == [2, 0]
    assert proposal["offline_source_transition_label_count"] == 6
    assert proposal["source_generation_witness_access_count"] == 0
    assert proposal["target_generation_witness_access_count"] == 0
    assert len(proposal["source_episode_closures"]) == 1
    assert proposal["source_episode_closures"][0]["terminal_status"] == "failure"
    assert proposal["source_episode_closures"][0]["candidate_count_at_close"] == 1
    assert all(
        row["source_generation_witness_accessed"] is False
        for row in proposal["source_observation_rows"]
    )


def test_v43_reuses_program_across_changed_cardinality_and_depth(frozen) -> None:
    document = frozen.to_document()
    assert document["v42_campaign_id"] == pre.V42_CAMPAIGN_ID
    assert document["v42_verification_id"] == pre.V42_VERIFICATION_ID
    assert pre.SOURCE_SPEC == {
        "tile_count": 12,
        "type_count": 4,
        "capacity": 5,
        "max_layers": 3,
    }
    assert pre.TARGET_SPEC == {
        "tile_count": 15,
        "type_count": 5,
        "capacity": 5,
        "max_layers": 4,
    }
    assert len(document["episodes"]) == 2 * len(pre.HELDOUT_SEEDS)
    for episode in document["episodes"]:
        assert episode["instance_specification"] == pre.TARGET_SPEC
        assert episode["terminal_state"]["status"] == "success"
        assert episode["full_board_cleared"] is True
        assert episode["execution_environment_step_count"] == pre.TARGET_SPEC["tile_count"]
        assert episode["source_generation_witness_access_count"] == 0
        assert episode["target_generation_witness_access_count"] == 0


def test_v43_local_ground_rows_only_follow_failed_certificates(frozen) -> None:
    for episode in frozen.to_document()["episodes"]:
        for decision in episode["decisions"]:
            distinction = decision["local_distinction"]
            if distinction is None:
                assert decision["initial_certificate"]["status"] == (
                    "CERTIFIED_MODEL_SUPPORT"
                )
                assert decision["replanned_after_local_distinction"] is False
            else:
                assert decision["initial_certificate"]["status"] == (
                    "FAILED_MISSING_SUPPORT"
                )
                assert distinction["failed_certificate_id"] == (
                    decision["initial_certificate"]["certificate_id"]
                )
                assert distinction["acquired_after_failed_certificate"] is True
                assert decision["final_certificate"]["status"] == (
                    "CERTIFIED_AFTER_LOCAL_DISTINCTION"
                )
                assert decision["replanned_after_local_distinction"] is True
            assert decision["model_matches_execution"] is True


def test_v43_matched_sample_tax_and_claim_boundaries(frozen) -> None:
    document = frozen.to_document()
    summary = document["summary"]
    assert summary["structural_meta_prior_target_label_count"] == 33
    assert summary["strict_no_prior_target_label_count"] == 90
    assert summary["target_label_fraction"].numerator == 11
    assert summary["target_label_fraction"].denominator == 30
    assert summary["execution_environment_step_count_per_arm"] == 90
    assert summary["structural_abstract_compute_events"] == 5005
    assert summary["control_abstract_compute_events"] == 7114
    assert summary["planning_kernel_step_count"] == 0
    assert summary["labels_steps_and_compute_separate"] is True
    assert document["open_ended_operator_invention_claimed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
