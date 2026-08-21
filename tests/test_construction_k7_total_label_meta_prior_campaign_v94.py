import hashlib
from pathlib import Path

import pytest

from acfqp.phase3e_ids import loads_canonical_json

from acfqp import construction_k7_total_label_meta_prior_campaign_v94 as campaign


def test_v94_frozen_campaign_will_not_be_rerun_under_the_same_identity():
    assert campaign.CAMPAIGN_ID == (
        "8fcb91339c02f818ef9ff829e99ab1ac000fbc6940888d700c31c461fafabde8"
    )
    with pytest.raises(campaign.ConstructionK7TotalLabelMetaPriorCampaignV94Error):
        campaign.run_total_label_meta_prior_campaign_v94(b"", b"", b"", b"")


def test_v94_exact_successful_campaign_is_preserved():
    raw = Path(
        ".tmp/exact-freeze/v94_total_label_meta_prior_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["meta_prior_total_target_labels"] == 18
    assert document["accounting"]["no_prior_total_target_labels"] == 24
    assert document["accounting"]["strict_cold_direct_labels"] == 33
    assert document["sample_tax_reduction_verified_on_registered_target_workload"] is True
    assert document["sample_tax_reduction_generalized_beyond_registered_workload"] is False
    assert document["official_execution_allowed"] is False
