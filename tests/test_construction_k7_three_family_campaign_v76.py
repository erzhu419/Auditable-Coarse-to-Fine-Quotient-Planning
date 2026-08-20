import os

import pytest

from acfqp.construction_k7_three_family_campaign_v76 import (
    ConstructionK7ThreeFamilyCampaignV76Error,
    run_three_family_campaign_v76,
    verify_three_family_campaign_v76,
)


def test_v76_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7ThreeFamilyCampaignV76Error):
        verify_three_family_campaign_v76(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V76") != "1",
    reason="explicit preregistered V76 three-family campaign execution",
)
def test_v76_registered_three_family_gate():
    document = run_three_family_campaign_v76().to_document()
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"]["source_family_count"] == 3
    assert document["registered_gate"]["fresh_target_occurrence_count"] == 6
    assert document["sample_tax_comparison"][
        "three_family_cross_occurrence_noninferiority_observed"
    ] is True
    assert document["cross_family_model_transfer_claimed"] is False
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
