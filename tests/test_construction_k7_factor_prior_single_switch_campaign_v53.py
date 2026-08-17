from __future__ import annotations

import hashlib

from acfqp import construction_k7_factor_prior_single_switch_campaign_v53 as campaign


def test_v53_campaign_identity_is_frozen() -> None:
    assert campaign.CAMPAIGN_ID == "f99f19fb95af81fe25a8a3229bd0dbc35187e1e3cf9a9f97b824dbc31993d169"
    assert campaign.EXPECTED_CANONICAL_BYTE_COUNT == 33_058_905
    assert campaign.EXPECTED_CANONICAL_SHA256 == "6a435b190a2f5fefb4ede21b3483f90dfa199c93c555a6c6faf30aa3f5990234"
    assert campaign.REGISTERED_FAILURE_ID == ""


def test_v53_campaign_wrapper_rejects_caller_minting() -> None:
    raw = b"{}"
    try:
        campaign.FactorPriorSingleSwitchCampaignV53(object(), raw, hashlib.sha256(raw).hexdigest())
    except campaign.ConstructionK7FactorPriorSingleSwitchCampaignV53Error:
        pass
    else:  # pragma: no cover
        raise AssertionError("caller-minted V53 campaign was accepted")
