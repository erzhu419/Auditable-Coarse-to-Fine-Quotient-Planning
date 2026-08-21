import pytest

from acfqp.construction_k7_reference_aligned_source_campaign_v91 import (
    CAMPAIGN_ID,
    ConstructionK7ReferenceAlignedSourceCampaignV91Error,
    run_reference_aligned_source_campaign_v91,
)


def test_v91_failed_campaign_identity_is_frozen_without_rerun():
    assert CAMPAIGN_ID == (
        "e9d6fd70a8cdf0d023dfaa5a3dfa60423a777632baef7b610b28da11024d7373"
    )
    with pytest.raises(ConstructionK7ReferenceAlignedSourceCampaignV91Error):
        run_reference_aligned_source_campaign_v91()
