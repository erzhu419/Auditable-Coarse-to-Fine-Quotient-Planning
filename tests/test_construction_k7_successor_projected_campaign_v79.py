import pytest

from acfqp.construction_k7_successor_projected_campaign_v79 import (
    ConstructionK7SuccessorProjectedCampaignV79Error,
    freeze_successor_projected_failure_v79,
    run_successor_projected_campaign_v79,
    verify_successor_projected_campaign_v79,
)


def test_v79_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7SuccessorProjectedCampaignV79Error):
        verify_successor_projected_campaign_v79(object())


def test_v79_preserves_structural_incompatibility_failure():
    document = freeze_successor_projected_failure_v79().to_document()
    assert document["failure_phase"] == "CANONICAL_SOURCE_POOL_COMPATIBILITY_CHECK"
    assert document["exception_message"] == (
        "V48 source members are not structurally compatible"
    )
    assert document["campaign_document_emitted"] is False
    assert document["fresh_target_outcome_count"] == 0
    assert document["same_identity_rerun_forbidden"] is True
    assert document["typed_noncertificate"] is True
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v79_same_identity_cannot_be_rerun():
    with pytest.raises(
        ConstructionK7SuccessorProjectedCampaignV79Error,
        match="same identity will not be rerun",
    ):
        run_successor_projected_campaign_v79()
