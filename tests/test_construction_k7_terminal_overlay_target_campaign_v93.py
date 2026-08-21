import pytest

from acfqp import construction_k7_terminal_overlay_target_campaign_v93 as campaign


def test_v93_producer_is_staged_before_registered_execution():
    assert campaign.CAMPAIGN_ID == "0" * 64
    with pytest.raises(campaign.ConstructionK7TerminalOverlayTargetCampaignV93Error):
        campaign.run_terminal_overlay_target_campaign_v93(b"", b"", b"", b"")
