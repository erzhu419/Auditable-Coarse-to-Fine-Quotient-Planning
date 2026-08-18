import hashlib

import pytest

from acfqp import construction_k7_true_bit_symmetric_campaign_v59 as producer


@pytest.fixture(scope="module")
def campaign():
    value = producer.run_true_bit_symmetric_campaign_v59()
    assert producer.verify_true_bit_symmetric_campaign_v59(value) is value
    return value


def test_v59_campaign_identity_and_sample_tax(campaign):
    assert campaign.campaign_id == producer.CAMPAIGN_ID
    assert len(campaign.canonical_bytes) == producer.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(campaign.canonical_bytes).hexdigest() == producer.EXPECTED_CANONICAL_SHA256
    sample = campaign.to_document()["sample_tax"]
    assert sample["online_label_reduction_including_recovery"] > 0
    assert sample["lifetime_label_reduction_after_offline_tax"] > 0
    assert all(row["incremental_acquisition_label_reduction"] > 0 for row in sample["family_projections"].values())


def test_v59_campaign_planning_and_claim_locks(campaign):
    document = campaign.to_document()
    assert all(row["success"] for rows in document["episodes"].values() for row in rows)
    assert document["symmetric_minimum_common_prefix_post_audit"] is True
    assert document["reachable_frontier_exhaustion_stop_consumed"] is False
    assert document["heuristic_mdl_information_units_consumed"] is False
    assert document["predictive_evidence_to_mdl_credit_consumed"] is False
    assert document["partial_model_executed_without_residual_safety_certificate"] is False
    assert document["query_locality_minimality_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
