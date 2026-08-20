import os

import pytest

from acfqp.construction_k7_three_family_campaign_v77 import (
    ConstructionK7ThreeFamilyCampaignV77Error,
    run_three_family_campaign_v77,
    verify_three_family_campaign_v77,
)


def test_v77_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7ThreeFamilyCampaignV77Error):
        verify_three_family_campaign_v77(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V77") != "1",
    reason="explicit preregistered V77 three-family campaign execution",
)
def test_v77_registered_three_family_gate_and_claim_boundary():
    document = run_three_family_campaign_v77().to_document()
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"]["usable_source_family_count"] == 2
    assert document["typed_source_abstention_count"] == 1
    balanced = next(
        row for row in document["sources"]
        if row["family"] == "BALANCED_BATCH_REFINEMENT"
    )
    assert balanced["source_status"] == "SOURCE_MODEL_ABSTAINED_NONCERTIFICATE"
    assert document["sample_tax_comparison"][
        "three_family_cross_occurrence_noninferiority_observed"
    ] is False
    assert document["sample_tax_comparison"]["filtered_minus_strict_labels"] == 0
    assert document["cross_family_model_transfer_claimed"] is False
    assert document["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
