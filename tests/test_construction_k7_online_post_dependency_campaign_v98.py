from acfqp import construction_k7_online_post_dependency_campaign_v98 as campaign


def test_v98_campaign_producer_is_staged_after_frozen_preregistration():
    assert campaign.pre.PREREGISTRATION_ID == (
        "81b87ce48c3b4159e4e0e869228dbb34b02d06adf1b5ad7c2359ef2c8fa0e452"
    )
    assert campaign.CAMPAIGN_ID == "0" * 64
