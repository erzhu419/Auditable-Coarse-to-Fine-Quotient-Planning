import pytest

from acfqp import construction_k7_total_label_meta_prior_campaign_v94 as campaign


def test_v94_producer_is_staged_before_registered_execution():
    assert campaign.CAMPAIGN_ID == "0" * 64
    with pytest.raises(campaign.ConstructionK7TotalLabelMetaPriorCampaignV94Error):
        campaign.run_total_label_meta_prior_campaign_v94(b"", b"", b"", b"")
