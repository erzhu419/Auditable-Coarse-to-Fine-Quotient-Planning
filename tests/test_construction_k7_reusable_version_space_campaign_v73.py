import os

import pytest

from acfqp.construction_k7_reusable_version_space_campaign_v73 import (
    ConstructionK7ReusableVersionSpaceCampaignV73Error,
    run_reusable_version_space_campaign_v73,
    verify_reusable_version_space_campaign_v73,
)


def test_v73_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7ReusableVersionSpaceCampaignV73Error):
        verify_reusable_version_space_campaign_v73(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V73") != "1",
    reason="explicit preregistered V73 source-to-target campaign execution",
)
def test_v73_registered_campaign_gate_and_claim_boundary():
    value = verify_reusable_version_space_campaign_v73(
        run_reusable_version_space_campaign_v73()
    )
    document = value.to_document()
    assert document["registered_gate"]["passed"] is True
    assert document["sample_tax_comparison"][
        "fresh_actual_target_sample_reduction_observed"
    ] is True
    assert document["all_ground_queries_followed_failed_certificates"] is True
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["producer_free_verification_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
