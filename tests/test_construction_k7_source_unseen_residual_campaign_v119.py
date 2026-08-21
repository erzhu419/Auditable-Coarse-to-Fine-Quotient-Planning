from pathlib import Path

import pytest

from acfqp import construction_k7_source_unseen_residual_campaign_v119 as campaign


ROOT = Path(__file__).resolve().parents[1]
V118_CAMPAIGN = ROOT / ".tmp/exact-freeze/v118_fourth_family_inventory_campaign.json"
V118_VERIFICATION = ROOT / ".tmp/exact-freeze/v118_fourth_family_inventory_verification.json"
V119_CAMPAIGN = ROOT / ".tmp/exact-freeze/v119_source_unseen_residual_campaign.json"


def test_v119_campaign_rejects_changed_v118_predecessor():
    raw = bytearray(V118_CAMPAIGN.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        campaign.ConstructionK7SourceUnseenResidualCampaignV119Error
    ):
        campaign.run_source_unseen_residual_campaign_v119(
            bytes(raw), V118_VERIFICATION.read_bytes()
        )


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not V119_CAMPAIGN.exists(),
    reason="V119 registered campaign has not been frozen",
)
def test_v119_exact_campaign_is_preserved():
    raw = V119_CAMPAIGN.read_bytes()
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    document = campaign.loads_canonical_json(raw)
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["complete_ground_world_model_synthesized"] is False
    assert document["official_scalar_cost"] is None
