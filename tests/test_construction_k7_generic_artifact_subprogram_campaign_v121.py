from pathlib import Path

import pytest

from acfqp import construction_k7_generic_artifact_subprogram_campaign_v121 as campaign


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
FILES = {
    "V117": ROOT / "v117_dependency_derived_program_branch_campaign.json",
    "V118": ROOT / "v118_fourth_family_inventory_campaign.json",
    "V119": ROOT / "v119_source_unseen_residual_campaign.json",
}
V120_CAMPAIGN = ROOT / "v120_artifact_derived_factor_campaign.json"
V120_VERIFICATION = ROOT / "v120_artifact_derived_factor_verification.json"
V121_CAMPAIGN = ROOT / "v121_generic_artifact_subprogram_campaign.json"


def _sources():
    return {key: path.read_bytes() for key, path in FILES.items()}


def test_v121_campaign_rejects_changed_v120_predecessor():
    raw = bytearray(V120_CAMPAIGN.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(campaign.ConstructionK7GenericArtifactSubprogramCampaignV121Error):
        campaign.run_generic_artifact_subprogram_campaign_v121(
            _sources(), bytes(raw), V120_VERIFICATION.read_bytes()
        )


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not V121_CAMPAIGN.exists(),
    reason="V121 registered campaign has not been frozen",
)
def test_v121_exact_campaign_is_preserved():
    raw = V121_CAMPAIGN.read_bytes()
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    document = campaign.loads_canonical_json(raw)
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["generic_planner_execution_adapter_verified"] is False
    assert document["complete_ground_world_model_synthesized"] is False
    assert document["official_scalar_cost"] is None
