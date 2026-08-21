from pathlib import Path

import pytest

from acfqp import construction_k7_three_family_incremental_successor_campaign_v114 as campaign


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / ".tmp/exact-freeze/v114_three_family_incremental_successor_campaign.json"


def test_v114_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(
        campaign.ConstructionK7ThreeFamilyIncrementalSuccessorCampaignV114Error
    ):
        campaign.run_three_family_incremental_successor_campaign_v114(b"", b"")


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN.exists(),
    reason="V114 fresh campaign has not been frozen",
)
def test_v114_exact_campaign_is_preserved():
    raw = CAMPAIGN.read_bytes()
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    document = campaign.loads_canonical_json(raw)
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "all_three_registered_structural_families_present"
    ] is True
    assert document["registered_three_family_incremental_successor_transfer_verified"] is True
    assert document["official_scalar_cost"] is None
