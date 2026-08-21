from acfqp import construction_k7_agreement_shielded_campaign_v99 as campaign


def test_v99_campaign_producer_is_staged_after_preregistration():
    assert campaign.pre.PREREGISTRATION_ID == (
        "1fa4860d395dd4c4d869d51c960d92b61565e3f06713c51e3ef40648ab4fcae6"
    )
    assert campaign.CAMPAIGN_ID == "0" * 64
