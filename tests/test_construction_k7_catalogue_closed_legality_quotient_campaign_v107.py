import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_catalogue_closed_legality_quotient_campaign_v107 as campaign


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v107_catalogue_closed_legality_quotient_campaign.json"
)


def test_v107_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(
        campaign.ConstructionK7CatalogueClosedLegalityQuotientCampaignV107Error
    ):
        campaign.run_catalogue_closed_legality_quotient_campaign_v107(b"", b"")


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN_PATH.exists(),
    reason="V107 fresh campaign has not been frozen",
)
def test_v107_exact_campaign_is_preserved():
    raw = CAMPAIGN_PATH.read_bytes()
    document = campaign.loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"]["passed_target_occurrence_count"] == 4
    assert document["registered_gate"]["every_occurrence_catalogue_closed"] is True
    assert document[
        "registered_catalogue_closed_legality_conditioned_quotient_verified"
    ] is True
    assert document["complete_ground_world_model_synthesized"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
