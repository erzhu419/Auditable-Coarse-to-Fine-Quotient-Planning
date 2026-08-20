import os

import pytest

from acfqp.construction_k7_structural_rank_campaign_v75r4 import (
    ConstructionK7StructuralRankCampaignV75R4Error,
    run_structural_rank_campaign_v75r4,
    verify_structural_rank_campaign_v75r4,
)


def test_v75r4_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7StructuralRankCampaignV75R4Error):
        verify_structural_rank_campaign_v75r4(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V75R4") != "1",
    reason="explicit preregistered V75r4 structural-rank campaign execution",
)
def test_v75r4_registered_campaign_gate_and_claim_boundary():
    document = run_structural_rank_campaign_v75r4().to_document()
    assert document["registered_gate"]["passed"] is False
    assert document["typed_target_arm_failures"] == []
    sample = document["sample_tax_comparison"]
    assert sample["cross_occurrence_reduction_observed"] is False
    assert sample["target_occurrences_using_structural_rank_priority_count"] == 4
    assert sample["reduced_target_occurrence_count"] == 1
    assert sample["derived_minus_strict_target_labels"] == 16
    assert document["target_transition_outcomes_used_to_translate_priority"] is False
    assert document["all_ground_queries_followed_failed_certificates"] is True
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["producer_free_verification_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
