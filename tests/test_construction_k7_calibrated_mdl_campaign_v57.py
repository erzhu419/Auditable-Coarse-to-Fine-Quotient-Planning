from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_calibrated_mdl_campaign_v57 as producer


@pytest.fixture(scope="module")
def campaign():
    value = producer.run_calibrated_mdl_campaign_v57()
    assert producer.verify_calibrated_mdl_campaign_v57(value) is value
    return value


def test_v57_campaign_is_frozen_and_content_addressed(campaign):
    assert campaign.campaign_id == producer.CAMPAIGN_ID
    assert len(campaign.canonical_bytes) == producer.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(campaign.canonical_bytes).hexdigest() == (
        producer.EXPECTED_CANONICAL_SHA256
    )


def test_v57_registered_three_domain_sample_tax(campaign):
    sample = campaign.to_document()["sample_tax"]
    assert sample["factor_prior_on_acquisition_labels"] == 7_630
    assert sample["strict_no_prior_acquisition_labels"] == 9_192
    assert sample["incremental_acquisition_label_reduction"] == 1_562
    assert sample["online_label_reduction_including_local_recovery"] == 1_557
    assert sample["lifetime_label_reduction_after_factor_library_tax"] == 1_187
    assert sample["diagnostic_break_even_occurrence_count"] == 44
    assert {
        key: row["incremental_label_reduction"]
        for key, row in sample["family_projections"].items()
    } == {
        "BALANCED_BATCH_REFINEMENT": 110,
        "COUPLED_EXCHANGE": 716,
        "MAINTENANCE_CASCADE": 736,
    }


def test_v57_registered_calibrated_stop_planning_and_recovery(campaign):
    document = campaign.to_document()
    assert all(
        row["terminal_stop_update"]["calibrated_evalue_threshold_met"]
        and row["terminal_stop_update"][
            "anytime_valid_for_registered_predictive_null"
        ]
        and row["terminal_stop_update"][
            "combined_mdl_predictive_margin_units"
        ]
        >= 0
        for rows in document["acquisitions"].values()
        for row in rows
    )
    prior = document["episodes"]["ANONYMOUS_FACTOR_PRIOR_ON"]
    no_prior = document["episodes"]["STRICT_NO_PRIOR"]
    assert [(row["family"], row["seed"], row["action_keys"]) for row in prior] == [
        (row["family"], row["seed"], row["action_keys"]) for row in no_prior
    ]
    assert all(
        row["success"] for rows in document["episodes"].values() for row in rows
    )
    assert len(document["failed_certificates"]) == 11
    assert len(document["local_distinctions"]) == 11


def test_v57_registered_validation_ood_and_claim_locks(campaign):
    document = campaign.to_document()
    assert len(document["isolated_full_frontier_validations"]) == 12
    assert document["reachable_frontier_exhaustion_stop_consumed"] is False
    assert document["full_frontier_target_layout_calibration_consumed"] is False
    assert document["ood_rejection"]["prior_transfer_attempted"] is False
    assert document["distribution_free_global_dynamics_confidence_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
