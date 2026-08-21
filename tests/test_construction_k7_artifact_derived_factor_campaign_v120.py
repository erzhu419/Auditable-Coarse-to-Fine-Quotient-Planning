from pathlib import Path

import pytest

from acfqp import construction_k7_artifact_derived_factor_campaign_v120 as campaign


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"
FILES = {
    "V117": FREEZE / "v117_dependency_derived_program_branch_campaign.json",
    "V118": FREEZE / "v118_fourth_family_inventory_campaign.json",
    "V119": FREEZE / "v119_source_unseen_residual_campaign.json",
}
V119_VERIFICATION = FREEZE / "v119_source_unseen_residual_verification.json"
V120_CAMPAIGN = FREEZE / "v120_artifact_derived_factor_campaign.json"


def _sources():
    return {key: path.read_bytes() for key, path in FILES.items()}


def test_v120_campaign_rejects_changed_v119_predecessor():
    sources = _sources()
    raw = bytearray(sources["V119"])
    raw[len(raw) // 2] ^= 1
    sources["V119"] = bytes(raw)
    with pytest.raises(campaign.ConstructionK7ArtifactDerivedFactorCampaignV120Error):
        campaign.run_artifact_derived_factor_campaign_v120(
            sources, V119_VERIFICATION.read_bytes()
        )


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not V120_CAMPAIGN.exists(),
    reason="V120 registered campaign has not been frozen",
)
def test_v120_exact_campaign_is_preserved():
    raw = V120_CAMPAIGN.read_bytes()
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    document = campaign.loads_canonical_json(raw)
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["artifact_factor_library"]["hand_written_factor_template_count"] == 0
    assert document["complete_ground_world_model_synthesized"] is False
    assert document["official_scalar_cost"] is None
