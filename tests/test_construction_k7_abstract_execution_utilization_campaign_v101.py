import pytest

from acfqp import construction_k7_abstract_execution_utilization_campaign_v101 as campaign


def test_v101_campaign_is_staged_after_preregistration():
    assert campaign.pre.PREREGISTRATION_ID == (
        "336139087db95530d912e3a3b027d14eb0e8aa4cbfc350fd979245107cc9ac9e"
    )
    assert campaign.CAMPAIGN_ID == "0" * 64


def test_v101_missing_predecessor_fails_before_outcomes():
    with pytest.raises(
        campaign.ConstructionK7AbstractExecutionUtilizationCampaignV101Error
    ):
        campaign.run_abstract_execution_utilization_campaign_v101(
            b"", b"", b"", b""
        )
    assert campaign._CACHE is None
