from acfqp import construction_k7_persistent_second_domain_campaign_v95 as campaign


def test_v95_campaign_is_staged_without_executing_registered_outcomes():
    assert campaign.CAMPAIGN_ID == "0" * 64
    assert campaign.EXPECTED_CANONICAL_BYTE_COUNT == 0
    assert campaign.EXPECTED_CANONICAL_SHA256 == "0" * 64
