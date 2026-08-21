from pathlib import Path

import pytest

from acfqp import construction_k7_receipted_utilization_campaign_v103 as campaign


def test_v103_producer_rejects_missing_frozen_predecessors_before_outcomes():
    if campaign.CAMPAIGN_ID != "0" * 64:
        pytest.skip("V103 campaign has been frozen")
    with pytest.raises(campaign.ConstructionK7ReceiptedUtilizationCampaignV103Error):
        campaign.run_receipted_utilization_campaign_v103(b"", b"", b"", b"")


def test_v103_campaign_artifact_is_not_present_before_registered_execution():
    if campaign.CAMPAIGN_ID != "0" * 64:
        pytest.skip("V103 campaign has been frozen")
    assert not Path(".tmp/exact-freeze/v103_receipted_utilization_campaign.json").exists()
