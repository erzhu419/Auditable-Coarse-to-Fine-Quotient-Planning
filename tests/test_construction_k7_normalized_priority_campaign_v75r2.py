import os

import pytest

from acfqp.construction_k7_normalized_priority_campaign_v75r2 import (
    ConstructionK7NormalizedPriorityCampaignV75R2Error,
    run_normalized_priority_campaign_v75r2,
    verify_normalized_priority_campaign_v75r2,
)


def test_v75r2_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7NormalizedPriorityCampaignV75R2Error):
        verify_normalized_priority_campaign_v75r2(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V75R2") != "1",
    reason="explicit preregistered V75r2 normalized-priority campaign execution",
)
def test_v75r2_registered_campaign_gate_and_claim_boundary():
    value = verify_normalized_priority_campaign_v75r2(
        run_normalized_priority_campaign_v75r2()
    )
    document = value.to_document()
    assert document["registered_gate"]["passed"] is True
    sample = document["sample_tax_comparison"]
    assert sample["normalized_portable_priority_reduction_observed"] is True
    assert sample["v75_zero_reduction_failure_preserved"] is True
    assert sample["v75r1_adapter_failure_preserved"] is True
    assert document["flat_action_adapter_applied_before_both_target_arms"] is True
    assert document["source_and_target_seed_identities_disjoint"] is True
    assert document["all_ground_queries_followed_failed_certificates"] is True
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["producer_free_verification_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
