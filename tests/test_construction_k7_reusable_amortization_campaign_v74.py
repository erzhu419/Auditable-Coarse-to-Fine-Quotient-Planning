import os

import pytest

from acfqp.construction_k7_reusable_amortization_campaign_v74 import (
    ConstructionK7ReusableAmortizationCampaignV74Error,
    run_reusable_amortization_campaign_v74,
    verify_reusable_amortization_campaign_v74,
)


def test_v74_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7ReusableAmortizationCampaignV74Error):
        verify_reusable_amortization_campaign_v74(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V74") != "1",
    reason="explicit preregistered V74 multi-episode campaign execution",
)
def test_v74_registered_campaign_gate_and_claim_boundary():
    value = verify_reusable_amortization_campaign_v74(
        run_reusable_amortization_campaign_v74()
    )
    document = value.to_document()
    assert document["registered_gate"]["passed"] is True
    amortization = document["incremental_sample_amortization"]
    assert amortization["every_target_episode_has_positive_aggregate_savings"] is True
    assert amortization[
        "incremental_break_even_observed_within_registered_horizon"
    ] is True
    assert amortization["official_N_break_even_claimed"] is False
    assert document["producer_free_verification_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
