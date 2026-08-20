import os

import pytest

from acfqp.construction_k7_cross_occurrence_reuse_campaign_v75 import (
    ConstructionK7CrossOccurrenceReuseCampaignV75Error,
    run_cross_occurrence_reuse_campaign_v75,
    verify_cross_occurrence_reuse_campaign_v75,
)


def test_v75_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7CrossOccurrenceReuseCampaignV75Error):
        verify_cross_occurrence_reuse_campaign_v75(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V75") != "1",
    reason="explicit preregistered V75 cross-occurrence campaign execution",
)
def test_v75_registered_campaign_gate_and_claim_boundary():
    value = verify_cross_occurrence_reuse_campaign_v75(
        run_cross_occurrence_reuse_campaign_v75()
    )
    document = value.to_document()
    assert document["registered_gate"]["passed"] is True
    sample = document["sample_tax_comparison"]
    assert sample["cross_occurrence_actual_target_sample_reduction_observed"] is True
    assert document["source_and_target_seed_identities_disjoint"] is True
    assert document["all_ground_queries_followed_failed_certificates"] is True
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["producer_free_verification_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
