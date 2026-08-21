from pathlib import Path

import pytest

from acfqp import construction_k7_projected_program_memo_campaign_v115 as campaign


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / ".tmp/exact-freeze/v115_projected_program_memo_campaign.json"


def test_v115_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(campaign.ConstructionK7ProjectedProgramMemoCampaignV115Error):
        campaign.run_projected_program_memo_campaign_v115(b"", b"")


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN.exists(),
    reason="V115 fresh campaign has not been frozen",
)
def test_v115_exact_campaign_is_preserved():
    raw = CAMPAIGN.read_bytes()
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    document = campaign.loads_canonical_json(raw)
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "every_occurrence_planning_compute_below_v113"
    ] is True
    assert document["official_scalar_cost"] is None
