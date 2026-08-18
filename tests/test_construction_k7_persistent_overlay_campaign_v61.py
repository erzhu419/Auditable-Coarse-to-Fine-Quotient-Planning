import hashlib

import pytest

from acfqp import construction_k7_persistent_overlay_campaign_v61 as producer


@pytest.fixture(scope="module")
def campaign():
    value = producer.run_persistent_overlay_campaign_v61()
    assert producer.verify_persistent_overlay_campaign_v61(value) is value
    return value


def test_v61_registered_campaign_closes_matched_overlay_gate(campaign):
    document = campaign.to_document()
    assert len(document["occurrences"]) == 12
    assert all(row["run"]["success"] for row in document["occurrences"])
    assert all(
        row["run"]["later_episode_ground_query_count"] == 0
        for row in document["occurrences"]
    )
    sample = document["sample_tax"]
    assert sample["cold_restart_local_labels"] > sample["persistent_overlay_local_labels"]
    assert sample["amortized_query_label_reduction"] > 0
    assert all(
        row["amortized_query_label_reduction"] > 0
        for row in sample["family_projections"].values()
    )


def test_v61_campaign_identity_accounting_and_claim_locks(campaign):
    raw = campaign.canonical_bytes
    if producer.CAMPAIGN_ID != "0" * 64:
        assert campaign.campaign_id == producer.CAMPAIGN_ID
        assert len(raw) == producer.EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == producer.EXPECTED_CANONICAL_SHA256
    document = campaign.to_document()
    assert document["accounting"]["all_axes_separate"] is True
    assert document["occurrence_bound_persistent_overlay_used"] is True
    assert document["cross_occurrence_ground_fact_reuse_allowed"] is False
    assert document["complete_residual_world_model_synthesized"] is False
    assert document["reachable_frontier_exhaustion_stop_consumed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
