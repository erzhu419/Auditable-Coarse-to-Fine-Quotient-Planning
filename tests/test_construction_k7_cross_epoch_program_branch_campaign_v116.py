from pathlib import Path

import pytest

from acfqp import construction_k7_cross_epoch_program_branch_campaign_v116 as campaign


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / ".tmp/exact-freeze/v116_cross_epoch_program_branch_campaign.json"


def test_v116_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(campaign.ConstructionK7CrossEpochProgramBranchCampaignV116Error):
        campaign.run_cross_epoch_program_branch_campaign_v116(b"", b"")


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN.exists(),
    reason="V116 fresh campaign has not been frozen",
)
def test_v116_exact_campaign_is_preserved():
    raw = CAMPAIGN.read_bytes()
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    document = campaign.loads_canonical_json(raw)
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "aggregate_planning_compute_below_v115"
    ] is True
    assert document["official_scalar_cost"] is None
