from pathlib import Path

import pytest

from acfqp import construction_k7_generic_subprogram_campaign_v121r1 as campaign


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
FILES = {
    "V117": ROOT / "v117_dependency_derived_program_branch_campaign.json",
    "V118": ROOT / "v118_fourth_family_inventory_campaign.json",
    "V119": ROOT / "v119_source_unseen_residual_campaign.json",
}
FAILED = ROOT / "v121_generic_artifact_subprogram_campaign.json"
SUCCESSOR = ROOT / "v121r1_generic_subprogram_campaign.json"


def _sources():
    return {key: path.read_bytes() for key, path in FILES.items()}


def test_v121r1_campaign_rejects_changed_failed_predecessor():
    raw = bytearray(FAILED.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(campaign.ConstructionK7GenericSubprogramCampaignV121R1Error):
        campaign.run_generic_subprogram_campaign_v121r1(_sources(), bytes(raw))


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not SUCCESSOR.exists(),
    reason="V121r1 registered campaign has not been frozen",
)
def test_v121r1_exact_campaign_is_preserved():
    raw = SUCCESSOR.read_bytes()
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    document = campaign.loads_canonical_json(raw)
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["failed_v121_predecessor_preserved"] is True
    assert document["generic_planner_execution_adapter_verified"] is False
    assert document["official_scalar_cost"] is None
