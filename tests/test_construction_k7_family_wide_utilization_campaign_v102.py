import pytest
from acfqp import construction_k7_family_wide_utilization_campaign_v102 as campaign


def test_v102_producer_is_staged():
    assert campaign.pre.PREREGISTRATION_ID == "961025ca99438c31ecedaf33431f8ec95817f1b1d99fe9edda4886a8e1395ba2"
    assert campaign.CAMPAIGN_ID == "0" * 64


def test_v102_rejects_missing_predecessor_before_outcomes():
    with pytest.raises(campaign.ConstructionK7FamilyWideUtilizationCampaignV102Error): campaign.run_family_wide_utilization_campaign_v102(b"", b"", b"", b"")
