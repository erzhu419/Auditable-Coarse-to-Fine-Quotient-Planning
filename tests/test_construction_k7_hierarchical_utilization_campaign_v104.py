from pathlib import Path

import pytest

from acfqp import construction_k7_hierarchical_utilization_campaign_v104 as campaign


def test_v104_producer_rejects_missing_predecessors_before_outcomes():
    if campaign.CAMPAIGN_ID != "0" * 64:
        pytest.skip("V104 campaign has been frozen")
    with pytest.raises(campaign.ConstructionK7HierarchicalUtilizationCampaignV104Error):
        campaign.run_hierarchical_utilization_campaign_v104(b"", b"", b"", b"")


def test_v104_campaign_artifact_absent_before_registered_execution():
    if campaign.CAMPAIGN_ID != "0" * 64:
        pytest.skip("V104 campaign has been frozen")
    assert not Path(".tmp/exact-freeze/v104_hierarchical_utilization_campaign.json").exists()
