import os

import pytest

from acfqp.construction_k7_agreement_filtered_campaign_v75r5 import (
    ConstructionK7AgreementFilteredCampaignV75R5Error,
    run_agreement_filtered_campaign_v75r5,
    verify_agreement_filtered_campaign_v75r5,
)


def test_v75r5_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7AgreementFilteredCampaignV75R5Error):
        verify_agreement_filtered_campaign_v75r5(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V75R5") != "1",
    reason="explicit preregistered V75r5 agreement-filtered campaign execution",
)
def test_v75r5_registered_sample_tax_operator_gate():
    document = run_agreement_filtered_campaign_v75r5().to_document()
    assert document["registered_gate"]["passed"] is True
    sample = document["sample_tax_comparison"]
    assert sample["operator_controls_priority_sample_tax"] is True
    assert sample["filtered_matches_model_only_per_target"] is True
    assert sample["filtered_minus_unfiltered_labels"] <= 0
    assert sample["filtered_minus_model_only_labels"] == 0
    assert sample["filtered_minus_strict_labels"] < 0
    assert document["target_transition_outcomes_used_to_filter_priority"] is False
    assert document["all_ground_queries_followed_failed_certificates"] is True
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
