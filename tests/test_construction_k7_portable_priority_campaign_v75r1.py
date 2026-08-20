import os

import pytest

from acfqp.construction_k7_portable_priority_campaign_v75r1 import (
    ConstructionK7PortablePriorityCampaignV75R1Error,
    run_portable_priority_campaign_v75r1,
    verify_portable_priority_campaign_v75r1,
)


def test_v75r1_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7PortablePriorityCampaignV75R1Error):
        verify_portable_priority_campaign_v75r1(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V75R1") != "1",
    reason="explicit preregistered V75r1 portable-priority campaign execution",
)
def test_v75r1_registered_campaign_gate_and_claim_boundary():
    value = verify_portable_priority_campaign_v75r1(
        run_portable_priority_campaign_v75r1()
    )
    document = value.to_document()
    assert document["registered_gate"]["passed"] is True
    sample = document["sample_tax_comparison"]
    assert sample["portable_priority_cross_occurrence_reduction_observed"] is True
    assert sample["v75_zero_reduction_failure_preserved"] is True
    assert document["source_and_target_seed_identities_disjoint"] is True
    assert document["all_ground_queries_followed_failed_certificates"] is True
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["producer_free_verification_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
