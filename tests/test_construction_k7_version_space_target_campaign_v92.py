import pytest

from acfqp import construction_k7_version_space_target_campaign_v92 as campaign


def test_v92_frozen_campaign_refuses_reexecution_after_freeze():
    if campaign.CAMPAIGN_ID == "0" * 64:
        pytest.skip("V92 registered target campaign not executed yet")
    with pytest.raises(
        campaign.ConstructionK7VersionSpaceTargetCampaignV92Error,
        match="same identity will not be rerun",
    ):
        campaign.run_version_space_target_campaign_v92(b"", b"")
