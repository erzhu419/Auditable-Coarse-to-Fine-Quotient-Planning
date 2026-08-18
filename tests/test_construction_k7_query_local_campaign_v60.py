import hashlib

import pytest

from acfqp import construction_k7_query_local_campaign_v60 as producer


@pytest.fixture(scope="module")
def campaign():
    value = producer.run_query_local_campaign_v60()
    assert producer.verify_query_local_campaign_v60(value) is value
    return value


def test_v60_campaign_identity_raw_evidence_and_sample_tax(campaign):
    assert campaign.campaign_id == producer.CAMPAIGN_ID
    assert len(campaign.canonical_bytes) == producer.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(campaign.canonical_bytes).hexdigest() == producer.EXPECTED_CANONICAL_SHA256
    document = campaign.to_document()
    assert len(document["raw_evidence"]) == 36
    assert document["raw_transition_bytes_embedded_for_producer_free_replay"] is True
    sample = document["sample_tax"]
    assert sample["online_label_reduction_including_local_queries"] > 0
    assert sample["lifetime_label_reduction_after_offline_tax"] > 0


def test_v60_query_local_planning_and_claim_locks(campaign):
    document = campaign.to_document()
    assert all(row["success"] for rows in document["episodes"].values() for row in rows)
    assert all(row["all_ground_queries_followed_failed_certificates"] for row in document["episodes"]["ANONYMOUS_FACTOR_PRIOR_ON"])
    assert document["stream_prefix_residual_recovery_consumed"] is False
    assert document["query_local_exact_overlay_used"] is True
    assert document["complete_residual_world_model_synthesized"] is False
    assert document["reachable_frontier_exhaustion_stop_consumed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
