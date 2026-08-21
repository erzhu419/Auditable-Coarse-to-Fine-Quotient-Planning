from pathlib import Path

import pytest

from acfqp import construction_k7_sequence_wide_agreement_shielded_campaign_v100 as campaign


def test_v100_producer_is_staged_after_fresh_preregistration():
    assert campaign.pre.PREREGISTRATION_ID == (
        "414e2cc6cd9170d4228097d756dbc7106eccbf07bc198366fc2fcd968b5ea9ea"
    )
    assert campaign.CAMPAIGN_ID == "0" * 64
    assert Path(
        ".tmp/exact-freeze/v99_agreement_shielded_campaign.json"
    ).is_file()
    assert Path(
        ".tmp/exact-freeze/v99_agreement_shielded_verification.json"
    ).is_file()


def test_v100_producer_rejects_missing_frozen_predecessor_before_outcomes():
    with pytest.raises(
        campaign.ConstructionK7SequenceWideAgreementShieldedCampaignV100Error
    ):
        campaign.run_sequence_wide_agreement_shielded_campaign_v100(
            b"", b"", b"", b""
        )
    assert campaign._CACHE is None
