import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_receipted_utilization_campaign_v103 as campaign


def test_v103_producer_rejects_missing_frozen_predecessors_before_outcomes():
    with pytest.raises(campaign.ConstructionK7ReceiptedUtilizationCampaignV103Error):
        campaign.run_receipted_utilization_campaign_v103(b"", b"", b"", b"")


def test_v103_exact_registered_failure_is_preserved():
    raw = Path(".tmp/exact-freeze/v103_receipted_utilization_campaign.json").read_bytes()
    document = campaign.loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"]["passed_target_occurrence_count"] == 0
    assert document["accounting"]["meta_receipted_abstract_execution_match_count"] == 13
    assert document["accounting"]["meta_execution_step_count"] == 71
    assert document["accounting"]["meta_activation"] == 175
    assert document["accounting"]["no_prior_activation"] == 202
    assert document["complete_world_model_synthesized"] is False
