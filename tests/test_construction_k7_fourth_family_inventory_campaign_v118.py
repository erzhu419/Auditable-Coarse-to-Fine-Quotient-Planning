from pathlib import Path

import pytest

from acfqp import construction_k7_fourth_family_inventory_campaign_v118 as campaign


ROOT = Path(__file__).resolve().parents[1]
V117_CAMPAIGN = ROOT / ".tmp/exact-freeze/v117_dependency_derived_program_branch_campaign.json"
V117_VERIFICATION = ROOT / ".tmp/exact-freeze/v117_dependency_derived_program_branch_verification.json"
V118_CAMPAIGN = ROOT / ".tmp/exact-freeze/v118_fourth_family_inventory_campaign.json"


def test_v118_campaign_rejects_changed_v117_predecessor():
    raw = bytearray(V117_CAMPAIGN.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        campaign.ConstructionK7FourthFamilyInventoryCampaignV118Error
    ):
        campaign.run_fourth_family_inventory_campaign_v118(
            bytes(raw), V117_VERIFICATION.read_bytes()
        )


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not V118_CAMPAIGN.exists(),
    reason="V118 registered campaign has not been frozen",
)
def test_v118_exact_campaign_is_preserved():
    raw = V118_CAMPAIGN.read_bytes()
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    document = campaign.loads_canonical_json(raw)
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["sample_efficiency_improvement_claimed"] is False
    assert document["official_scalar_cost"] is None
