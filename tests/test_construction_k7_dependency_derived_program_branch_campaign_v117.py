from pathlib import Path

import pytest

from acfqp import construction_k7_dependency_derived_program_branch_campaign_v117 as campaign


ROOT = Path(__file__).resolve().parents[1]
V116_CAMPAIGN = ROOT / ".tmp/exact-freeze/v116_cross_epoch_program_branch_campaign.json"
V116_VERIFICATION = ROOT / ".tmp/exact-freeze/v116_cross_epoch_program_branch_verification.json"
V117_CAMPAIGN = ROOT / ".tmp/exact-freeze/v117_dependency_derived_program_branch_campaign.json"


def test_v117_campaign_rejects_changed_v116_predecessor():
    raw = bytearray(V116_CAMPAIGN.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        campaign.ConstructionK7DependencyDerivedProgramBranchCampaignV117Error
    ):
        campaign.run_dependency_derived_program_branch_campaign_v117(
            bytes(raw), V116_VERIFICATION.read_bytes()
        )


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not V117_CAMPAIGN.exists(),
    reason="V117 registered campaign has not been frozen",
)
def test_v117_exact_campaign_is_preserved():
    assert campaign.run_dependency_derived_program_branch_campaign_v117(
        V116_CAMPAIGN.read_bytes(), V116_VERIFICATION.read_bytes()
    ).canonical_bytes == V117_CAMPAIGN.read_bytes()
